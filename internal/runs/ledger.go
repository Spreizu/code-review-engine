package runs

import (
	"os"
	"path/filepath"
	"slices"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/scope"
)

// Lifecycle statuses.
const (
	Open       = "open"
	Fixed      = "fixed"
	Reopened   = "reopened"
	Suppressed = "suppressed"
)

// Point identifies a run in the ledger.
type Point struct {
	Run    string    `json:"run"`
	Commit string    `json:"commit,omitempty"`
	Time   time.Time `json:"time"`
}

// Event is a status transition.
type Event struct {
	Point
	Status string `json:"status"`
}

// Entry is the lifecycle of one finding fingerprint on a branch.
type Entry struct {
	Fingerprint string  `json:"fingerprint"`
	RuleID      string  `json:"rule_id"`
	Path        string  `json:"path"`
	Line        int     `json:"line"`
	Title       string  `json:"title,omitempty"`
	Message     string  `json:"message,omitempty"`
	Severity    string  `json:"severity"`
	Category    string  `json:"category,omitempty"`
	Symbol      string  `json:"symbol,omitempty"`
	Status      string  `json:"status"`
	FirstSeen   Point   `json:"first_seen"`
	LastSeen    Point   `json:"last_seen"`
	FixedIn     *Point  `json:"fixed_in,omitempty"`
	Reopened    int     `json:"reopened"`
	Events      []Event `json:"events"`
}

// RunPoint is one run on the branch timeline (for trends / "found vs fixed over time").
type RunPoint struct {
	Point
	ScopeMode  string `json:"scope_mode"`
	Open       int    `json:"open"` // open + reopened after this run
	New        int    `json:"new"`
	Fixed      int    `json:"fixed"`
	Reopened   int    `json:"reopened"`
	Suppressed int    `json:"suppressed"`
	Total      int    `json:"total"` // findings reported by the run
}

// Ledger is .crev/runs/<branch>/history.json.
type Ledger struct {
	SchemaVersion int               `json:"schema_version"`
	Branch        string            `json:"branch"`
	Entries       map[string]*Entry `json:"entries"`
	Timeline      []RunPoint        `json:"timeline"`
}

// Delta is the effect of one run on the ledger (stored in metadata.json).
type Delta struct {
	New        []string `json:"new"`
	Fixed      []string `json:"fixed"`
	Reopened   []string `json:"reopened"`
	Suppressed []string `json:"suppressed"`
	// NotEvaluated: open entries the run could not judge (outside a diff scope, or rule inactive).
	NotEvaluated int `json:"not_evaluated"`
}

// LedgerPath is the ledger file of a branch.
func (s Store) LedgerPath(branch string) string {
	return filepath.Join(s.Dir, SanitizeBranch(branch), "history.json")
}

// LoadLedger reads a branch ledger (empty when missing).
func (s Store) LoadLedger(branch string) (*Ledger, error) {
	l := &Ledger{SchemaVersion: 1, Branch: branch, Entries: map[string]*Entry{}}
	err := readJSON(s.LedgerPath(branch), l)
	if os.IsNotExist(err) {
		err = nil
	}
	if l.Entries == nil {
		l.Entries = map[string]*Entry{}
	}
	return l, err
}

// SaveLedger writes a branch ledger.
func (s Store) SaveLedger(l *Ledger) error {
	p := s.LedgerPath(l.Branch)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		return err
	}
	return WriteJSON(p, l)
}

func present(f *findings.Finding) (bool, bool) { // present, suppressed
	// Only review-list findings are open; pending/uncertain/rejected/low-confidence/shadow and
	// suppressed ones are tracked as suppressed (findings.InReview).
	return true, !findings.InReview(f, "")
}

// Apply records a run. Rules:
//   - a review-list finding (findings.InReview) is open (new), reopened (was fixed) or stays open;
//     any other status (suppressed, pending_ai, ai_rejected/uncertain, shadow) moves the entry to suppressed;
//   - an open entry absent from the run becomes fixed only if the run could have reported it:
//     its rule was active and the scope covered it (full scan; or a diff scan where the file was
//     deleted, or diff-context=file and the file changed). A finding merely outside a diff scope
//     is never marked fixed.
func (l *Ledger) Apply(rep *findings.Report, p Point, sc *scope.Scope, active map[string]bool) *Delta {
	d := &Delta{}
	seen := map[string]bool{}
	setStatus := func(e *Entry, st string) {
		if e.Status != st {
			e.Status = st
			e.Events = append(e.Events, Event{Point: p, Status: st})
		}
	}
	for _, f := range rep.Findings {
		_, supp := present(f)
		fp := f.ID
		seen[fp] = true
		e := l.Entries[fp]
		if e == nil {
			e = &Entry{Fingerprint: fp, RuleID: f.RuleID, FirstSeen: p}
			l.Entries[fp] = e
			if supp {
				setStatus(e, Suppressed)
				d.Suppressed = append(d.Suppressed, fp)
			} else {
				setStatus(e, Open)
				d.New = append(d.New, fp)
			}
		} else {
			switch {
			case supp:
				if e.Status != Suppressed {
					d.Suppressed = append(d.Suppressed, fp)
				}
				setStatus(e, Suppressed)
			case e.Status == Fixed:
				e.Reopened++
				e.FixedIn = nil
				setStatus(e, Reopened)
				d.Reopened = append(d.Reopened, fp)
			case e.Status == Suppressed:
				setStatus(e, Open)
			}
		}
		e.Path, e.Line, e.Title, e.Message, e.Severity, e.Category, e.Symbol =
			f.Location.Path, f.Location.StartLine, f.Title, f.Message, f.Severity, f.Category, f.Location.EnclosingSymbol
		e.LastSeen = p
	}
	for fp, e := range l.Entries {
		if seen[fp] || (e.Status != Open && e.Status != Reopened) {
			continue
		}
		if !canJudge(e, sc, active) {
			d.NotEvaluated++
			continue
		}
		pp := p
		e.FixedIn = &pp
		setStatus(e, Fixed)
		d.Fixed = append(d.Fixed, fp)
	}
	slices.Sort(d.New)
	slices.Sort(d.Fixed)
	slices.Sort(d.Reopened)
	slices.Sort(d.Suppressed)
	rp := RunPoint{Point: p, ScopeMode: "full", New: len(d.New), Fixed: len(d.Fixed), Reopened: len(d.Reopened), Total: len(rep.Findings)}
	if sc.IsDiff() {
		rp.ScopeMode = sc.Mode
	}
	for _, e := range l.Entries {
		switch e.Status {
		case Open, Reopened:
			rp.Open++
		case Suppressed:
			rp.Suppressed++
		}
	}
	l.Timeline = append(l.Timeline, rp)
	return d
}

func canJudge(e *Entry, sc *scope.Scope, active map[string]bool) bool {
	if active != nil && !active[e.RuleID] {
		return false // rule disabled/removed in this run: absence proves nothing
	}
	if !sc.IsDiff() {
		return true
	}
	if sc.Deleted[e.Path] {
		return true
	}
	return sc.DiffContext == "file" && sc.FileInScope(e.Path)
}

// MarkRejected moves entries whose findings were AI-rejected after the fact (crev ingest) to suppressed.
func (l *Ledger) MarkRejected(rep *findings.Report, p Point) int {
	n := 0
	for _, f := range rep.Findings {
		if findings.InReview(f, "") {
			continue
		}
		if e := l.Entries[f.ID]; e != nil && e.Status != Suppressed {
			e.Status = Suppressed
			e.Events = append(e.Events, Event{Point: p, Status: Suppressed})
			n++
		}
	}
	return n
}

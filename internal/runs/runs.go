// Package runs stores scan history: one directory per scan under
// .crev/runs/<sanitized-branch>/<UTC timestamp>-<short id>/ with the report files, AI handoff /
// responses and metadata.json, plus .crev/runs/index.json (all runs, latest pointers) and a
// per-branch finding lifecycle ledger .crev/runs/<branch>/history.json (survives retention).
package runs

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/scope"
)

// TimeFormat is the UTC timestamp used in run directory names.
const TimeFormat = "20060102T150405Z"

// Fact is one detected or assumed version.
type Fact struct {
	Version string `json:"version"`
	Assumed bool   `json:"assumed,omitempty"`
}

// Counts summarise a report.
type Counts struct {
	Total      int            `json:"total"`
	BySeverity map[string]int `json:"by_severity"`
	ByCategory map[string]int `json:"by_category"`
	ByStatus   map[string]int `json:"by_status"`
	// Hidden counts findings kept out of the review list per hidden_reason.
	Hidden map[string]int `json:"hidden,omitempty"`
	Gating int            `json:"gating"`
}

// Meta is metadata.json.
type Meta struct {
	ID          string                     `json:"id"`
	Branch      string                     `json:"branch"`
	BranchDir   string                     `json:"branch_dir"`
	Dir         string                     `json:"dir"` // relative to the runs dir
	Commit      string                     `json:"commit,omitempty"`
	Dirty       bool                       `json:"dirty"`
	Timestamp   time.Time                  `json:"timestamp"`
	CrevVersion string                     `json:"crev_version"`
	RulePacks   map[string]string          `json:"rule_packs"`
	Versions    map[string]map[string]Fact `json:"versions"` // unit dir -> dimension -> fact
	ConfigHash  string                     `json:"config_hash"`
	FailOn      string                     `json:"fail_on"`
	Counts      Counts                     `json:"counts"`
	DurationMS  int64                      `json:"duration_ms"`
	ExitCode    int                        `json:"exit_code"`
	Scope       *scope.Scope               `json:"scope"`
	ActiveRules []string                   `json:"active_rules,omitempty"`
	Ledger      *Delta                     `json:"ledger,omitempty"`
	Files       []string                   `json:"files"`
}

// IndexEntry is one run in index.json.
type IndexEntry struct {
	ID        string    `json:"id"`
	Branch    string    `json:"branch"`
	Dir       string    `json:"dir"`
	Timestamp time.Time `json:"timestamp"`
	Commit    string    `json:"commit,omitempty"`
	Dirty     bool      `json:"dirty"`
	ScopeMode string    `json:"scope_mode"`
	Counts    Counts    `json:"counts"`
	ExitCode  int       `json:"exit_code"`
}

// Index is .crev/runs/index.json.
type Index struct {
	Latest   string            `json:"latest"`    // run id
	ByBranch map[string]string `json:"by_branch"` // branch -> latest run id
	Runs     []IndexEntry      `json:"runs"`      // oldest first
}

// Store is a runs directory.
type Store struct{ Dir string }

var unsafe = regexp.MustCompile(`[^A-Za-z0-9._-]+`)

// SanitizeBranch makes a branch name safe as one path segment ("feature/x" -> "feature-x").
func SanitizeBranch(b string) string {
	s := strings.Trim(unsafe.ReplaceAllString(b, "-"), "-.")
	if s == "" {
		return "unknown"
	}
	return s
}

// NewID returns a run id "<UTC timestamp>-<6 hex>".
func NewID(t time.Time) string {
	var b [3]byte
	_, _ = rand.Read(b[:])
	return t.UTC().Format(TimeFormat) + "-" + hex.EncodeToString(b[:])
}

// Create makes the directory for a new run and fills the identity fields of m.
func (s Store) Create(m *Meta) (string, error) {
	if m.Timestamp.IsZero() {
		m.Timestamp = time.Now().UTC()
	}
	m.Timestamp = m.Timestamp.UTC()
	if m.ID == "" {
		m.ID = NewID(m.Timestamp)
	}
	m.BranchDir = SanitizeBranch(m.Branch)
	m.Dir = filepath.ToSlash(filepath.Join(m.BranchDir, m.ID))
	abs := filepath.Join(s.Dir, m.Dir)
	if err := os.MkdirAll(abs, 0o755); err != nil {
		return "", err
	}
	return abs, nil
}

// CountsOf summarises a report (gating computed by the caller).
func CountsOf(rep *findings.Report) Counts {
	c := Counts{BySeverity: map[string]int{}, ByCategory: map[string]int{}, ByStatus: map[string]int{}}
	for _, f := range rep.Findings {
		c.Total++
		c.BySeverity[f.Severity]++
		cat := f.Category
		if cat == "" {
			cat = "uncategorized"
		}
		c.ByCategory[cat]++
		c.ByStatus[f.Status]++
		if f.HiddenReason != "" {
			if c.Hidden == nil {
				c.Hidden = map[string]int{}
			}
			c.Hidden[f.HiddenReason]++
		}
	}
	return c
}

// VersionsOf converts report units ("x (assumed latest)") to facts.
func VersionsOf(rep *findings.Report) map[string]map[string]Fact {
	out := map[string]map[string]Fact{}
	for u, m := range rep.Units {
		o := map[string]Fact{}
		for k, v := range m {
			f := Fact{Version: v}
			if ver, ok := strings.CutSuffix(v, " (assumed latest)"); ok {
				f = Fact{Version: ver, Assumed: true}
			}
			o[k] = f
		}
		out[u] = o
	}
	return out
}

// WriteJSON writes v as indented JSON atomically.
func WriteJSON(path string, v any) error {
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, append(b, '\n'), 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

func readJSON(path string, v any) error {
	b, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return json.Unmarshal(b, v)
}

// Finish writes metadata.json and records the run in index.json (latest pointers + LATEST file).
func (s Store) Finish(m *Meta) error {
	abs := filepath.Join(s.Dir, m.Dir)
	ents, _ := os.ReadDir(abs)
	m.Files = m.Files[:0]
	for _, e := range ents {
		m.Files = append(m.Files, e.Name())
	}
	if err := WriteJSON(filepath.Join(abs, "metadata.json"), m); err != nil {
		return err
	}
	idx, _ := s.Index()
	mode := "full"
	if m.Scope != nil && m.Scope.Mode != "" {
		mode = m.Scope.Mode
	}
	idx.Runs = append(idx.Runs, IndexEntry{ID: m.ID, Branch: m.Branch, Dir: m.Dir, Timestamp: m.Timestamp, Commit: m.Commit, Dirty: m.Dirty,
		ScopeMode: mode, Counts: m.Counts, ExitCode: m.ExitCode})
	idx.Latest = m.ID
	idx.ByBranch[m.Branch] = m.ID
	if err := s.saveIndex(idx); err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(s.Dir, "LATEST"), []byte(m.Dir+"\n"), 0o644)
}

// Index loads index.json (empty when missing).
func (s Store) Index() (*Index, error) {
	idx := &Index{ByBranch: map[string]string{}}
	err := readJSON(filepath.Join(s.Dir, "index.json"), idx)
	if idx.ByBranch == nil {
		idx.ByBranch = map[string]string{}
	}
	if os.IsNotExist(err) {
		err = nil
	}
	return idx, err
}

func (s Store) saveIndex(idx *Index) error {
	if err := os.MkdirAll(s.Dir, 0o755); err != nil {
		return err
	}
	slices.SortStableFunc(idx.Runs, func(a, b IndexEntry) int { return a.Timestamp.Compare(b.Timestamp) })
	return WriteJSON(filepath.Join(s.Dir, "index.json"), idx)
}

// UpdateEntry rewrites a run's index entry (after `crev ingest`).
func (s Store) UpdateEntry(m *Meta) error {
	idx, err := s.Index()
	if err != nil {
		return err
	}
	for i := range idx.Runs {
		if idx.Runs[i].ID == m.ID {
			idx.Runs[i].Counts, idx.Runs[i].ExitCode = m.Counts, m.ExitCode
		}
	}
	if err := WriteJSON(filepath.Join(s.Dir, m.Dir, "metadata.json"), m); err != nil {
		return err
	}
	return s.saveIndex(idx)
}

// Resolve finds a run: "" / "latest", "<branch>:latest", a full id or a unique id prefix.
func (s Store) Resolve(ref string) (*Meta, error) {
	idx, err := s.Index()
	if err != nil {
		return nil, err
	}
	if len(idx.Runs) == 0 {
		return nil, fmt.Errorf("no runs recorded in %s (run `crev scan` first)", s.Dir)
	}
	id := ""
	switch {
	case ref == "" || ref == "latest":
		id = idx.Latest
	case strings.HasSuffix(ref, ":latest"):
		b := strings.TrimSuffix(ref, ":latest")
		if id = idx.ByBranch[b]; id == "" {
			for br, rid := range idx.ByBranch {
				if SanitizeBranch(br) == SanitizeBranch(b) {
					id = rid
				}
			}
		}
		if id == "" {
			return nil, fmt.Errorf("no runs for branch %q", b)
		}
	default:
		var hits []string
		for _, r := range idx.Runs {
			if r.ID == ref {
				hits = []string{r.ID}
				break
			}
			if strings.HasPrefix(r.ID, ref) || strings.HasSuffix(r.ID, "-"+ref) {
				hits = append(hits, r.ID)
			}
		}
		if len(hits) != 1 {
			return nil, fmt.Errorf("run %q: %d matches", ref, len(hits))
		}
		id = hits[0]
	}
	for _, r := range idx.Runs {
		if r.ID == id {
			var m Meta
			if err := readJSON(filepath.Join(s.Dir, r.Dir, "metadata.json"), &m); err != nil {
				return nil, fmt.Errorf("run %s: %w (pruned?)", id, err)
			}
			return &m, nil
		}
	}
	return nil, fmt.Errorf("run %q not in index", ref)
}

// Report loads a run's report.json.
func (s Store) Report(m *Meta) (*findings.Report, error) {
	var rep findings.Report
	if err := readJSON(filepath.Join(s.Dir, m.Dir, "report.json"), &rep); err != nil {
		return nil, err
	}
	return &rep, nil
}

// RunDir is the absolute directory of a run.
func (s Store) RunDir(m *Meta) string { return filepath.Join(s.Dir, m.Dir) }

// Prune applies retention per branch: keep the newest `keep` runs (0 = unlimited) and drop runs
// older than maxAge (0 = unlimited). The latest run of each branch is always kept; history.json
// ledgers are never deleted. Returns the ids removed.
func (s Store) Prune(keep int, maxAge time.Duration, now time.Time) ([]string, error) {
	idx, err := s.Index()
	if err != nil {
		return nil, err
	}
	byBranch := map[string][]IndexEntry{}
	for _, r := range idx.Runs {
		byBranch[r.Branch] = append(byBranch[r.Branch], r)
	}
	drop := map[string]bool{}
	for b, rs := range byBranch {
		slices.SortFunc(rs, func(a, b IndexEntry) int { return b.Timestamp.Compare(a.Timestamp) }) // newest first
		for i, r := range rs {
			if r.ID == idx.ByBranch[b] {
				continue
			}
			if (keep > 0 && i >= keep) || (maxAge > 0 && now.Sub(r.Timestamp) > maxAge) {
				drop[r.ID] = true
			}
		}
	}
	var removed []string
	kept := idx.Runs[:0]
	for _, r := range idx.Runs {
		if drop[r.ID] {
			if err := os.RemoveAll(filepath.Join(s.Dir, r.Dir)); err != nil {
				return removed, err
			}
			removed = append(removed, r.ID)
			continue
		}
		kept = append(kept, r)
	}
	idx.Runs = kept
	if len(removed) == 0 {
		return nil, nil
	}
	return removed, s.saveIndex(idx)
}

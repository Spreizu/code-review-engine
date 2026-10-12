// Package progress renders scan progress on stderr (never stdout, so JSON/SARIF output stays
// clean). It is hand-rolled (no dependencies): a single redrawn line on a TTY, or periodic plain
// log lines for CI.
package progress

import (
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Event is one progress update from the engine or the CLI.
type Event struct {
	Phase    string // discover | versions | index | rules | ai | report
	Done     int
	Total    int // 0 = unknown
	Current  string
	Findings int
}

// Mode selects the renderer.
type Mode int

const (
	Off Mode = iota
	Bar
	Plain
)

// PhaseLabels are the human-readable phase names, in pipeline order.
var PhaseLabels = map[string]string{"discover": "discover", "versions": "version detect", "index": "index",
	"rules": "parse/rules", "ai": "AI confirm", "report": "report"}

var phaseOrder = []string{"discover", "versions", "index", "rules", "ai", "report"}

// Resolve picks a mode from the --progress flag value (auto|bar|plain|off), --quiet/--no-progress
// and the environment. auto = bar on an interactive stderr outside CI, otherwise off.
func Resolve(flag string, quiet bool, w *os.File) Mode {
	if quiet {
		return Off
	}
	switch flag {
	case "off", "none", "false":
		return Off
	case "bar":
		return Bar
	case "plain":
		return Plain
	}
	if inCI() || !isTTY(w) || os.Getenv("TERM") == "dumb" {
		return Off
	}
	return Bar
}

func inCI() bool {
	for _, k := range []string{"CI", "GITHUB_ACTIONS", "GITLAB_CI", "BUILDKITE", "JENKINS_URL", "TF_BUILD", "TEAMCITY_VERSION"} {
		if v := os.Getenv(k); v != "" && v != "false" && v != "0" {
			return true
		}
	}
	return false
}

func isTTY(f *os.File) bool {
	if f == nil {
		return false
	}
	st, err := f.Stat()
	return err == nil && st.Mode()&os.ModeCharDevice != 0
}

// Reporter renders events. The zero value / nil is a no-op, so callers can always call Update.
type Reporter struct {
	mu         sync.Mutex
	w          io.Writer
	mode       Mode
	width      int
	interval   time.Duration
	now        func() time.Time
	start      time.Time
	phase      string
	phaseStart time.Time
	last       time.Time
	lastLen    int
	lastLine   string
	ev         Event
}

// New returns a Reporter (nil when mode is Off).
func New(w io.Writer, mode Mode) *Reporter {
	if mode == Off {
		return nil
	}
	width := 100
	if c, err := strconv.Atoi(os.Getenv("COLUMNS")); err == nil && c > 30 {
		width = c
	}
	iv := 80 * time.Millisecond
	if mode == Plain {
		iv = 5 * time.Second
	}
	r := &Reporter{w: w, mode: mode, width: width, interval: iv, now: time.Now}
	r.start = r.now()
	return r
}

// Update records an event and redraws when due (phase changes are always drawn).
func (r *Reporter) Update(e Event) {
	if r == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	now := r.now()
	changed := e.Phase != r.phase
	if changed {
		if r.phase != "" && r.mode == Plain {
			r.ev.Done = r.ev.Total
			r.draw(now, true)
		}
		r.phase, r.phaseStart = e.Phase, now
	}
	r.ev = e
	if changed || now.Sub(r.last) >= r.interval || (e.Total > 0 && e.Done >= e.Total) {
		r.draw(now, false)
		r.last = now
	}
}

// Finish clears the bar line (TTY) or prints a final summary line (plain).
func (r *Reporter) Finish() {
	if r == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.mode == Bar {
		fmt.Fprintf(r.w, "\r%s\r", strings.Repeat(" ", r.lastLen))
		return
	}
	fmt.Fprintf(r.w, "crev: done in %s, %d findings\n", r.now().Sub(r.start).Round(100*time.Millisecond), r.ev.Findings)
}

// Line formats the status text (exported for tests).
func (r *Reporter) Line(now time.Time) string {
	e := r.ev
	step := 1
	for i, p := range phaseOrder {
		if p == e.Phase {
			step = i + 1
		}
	}
	label := PhaseLabels[e.Phase]
	if label == "" {
		label = e.Phase
	}
	var b strings.Builder
	fmt.Fprintf(&b, "[%d/%d] %-14s", step, len(phaseOrder), label)
	if e.Total > 0 {
		pct := float64(e.Done) / float64(e.Total)
		if pct > 1 {
			pct = 1
		}
		if r.mode == Bar {
			n := 20
			fill := int(pct * float64(n))
			b.WriteString(" " + strings.Repeat("█", fill) + strings.Repeat("░", n-fill))
		}
		fmt.Fprintf(&b, " %3.0f%% %d/%d", pct*100, e.Done, e.Total)
		if el := now.Sub(r.phaseStart); e.Done > 0 && e.Done < e.Total && el > 500*time.Millisecond {
			eta := time.Duration(float64(el) / float64(e.Done) * float64(e.Total-e.Done))
			fmt.Fprintf(&b, " ETA %s", eta.Round(time.Second))
		}
	} else if e.Done > 0 {
		fmt.Fprintf(&b, " %d", e.Done)
	}
	fmt.Fprintf(&b, " | %d findings", e.Findings)
	if e.Current != "" {
		b.WriteString(" | " + e.Current)
	}
	return b.String()
}

func (r *Reporter) draw(now time.Time, final bool) {
	s := r.Line(now)
	if r.mode == Plain {
		if s != r.lastLine {
			fmt.Fprintln(r.w, "crev: "+s)
		}
		r.lastLine = s
		return
	}
	if rs := []rune(s); len(rs) > r.width-1 {
		// keep the tail of the current path visible
		s = string(rs[:r.width-2]) + "…"
	}
	n := len([]rune(s))
	pad := ""
	if r.lastLen > n {
		pad = strings.Repeat(" ", r.lastLen-n)
	}
	fmt.Fprintf(r.w, "\r%s%s", s, pad)
	r.lastLen = n
	_ = final
}

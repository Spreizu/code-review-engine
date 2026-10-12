package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"maps"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	"github.com/elmo/code-review-engine/internal/feedback"
	"github.com/elmo/code-review-engine/internal/findings"
)

func (e *env) feedback() feedback.Store {
	d := e.cfg.StateDir
	if !filepath.IsAbs(d) {
		d = filepath.Join(e.root, d)
	}
	return feedback.Store{Dir: filepath.Join(d, "feedback")}
}

func (e *env) ruleVersion(id string) int {
	if r := e.byID[id]; r != nil {
		return r.RuleVersion
	}
	return 0
}

// feedbackShadow: rules demoted to shadow mode by false-positive feedback.
func (e *env) feedbackShadow() map[string]string {
	if e.cfg.Feedback.FPThreshold < 0 {
		return nil
	}
	recs, err := e.feedback().Load()
	if err != nil {
		fmt.Fprintln(os.Stderr, "crev: feedback:", err)
		return nil
	}
	return feedback.Shadow(recs, e.cfg.Feedback.FPThreshold, e.ruleVersion)
}

func cmdFeedback(args []string) error {
	if len(args) == 0 {
		return fail(2, "usage: crev feedback fp FINGERPRINT [--reason TEXT] | list [--json] | undo FINGERPRINT")
	}
	fs := flag.NewFlagSet("feedback", flag.ContinueOnError)
	root := fs.String("root", ".", "project root")
	cfgPath := fs.String("config", "", "config file")
	reason := fs.String("reason", "", "why this is a false positive (kept in the record and the regression stub)")
	runRef := fs.String("run", "latest", "run holding the finding: latest | <branch>:latest | <run id>")
	asJSON := fs.Bool("json", false, "list: JSON output")
	sub := args[0]
	if err := parseInterspersed(fs, args[1:]); err != nil {
		return fail(2, "%v", err)
	}
	e, err := setup(*root, *cfgPath, "", "")
	if err != nil {
		return err
	}
	st := e.feedback()
	switch sub {
	case "fp":
		if fs.NArg() != 1 {
			return fail(2, "usage: crev feedback fp FINGERPRINT [--reason TEXT]")
		}
		f, runID, err := e.findFinding(*runRef, fs.Arg(0))
		if err != nil {
			return err
		}
		rec, added, err := st.Add(f, *reason, runID, time.Now())
		if err != nil {
			return fail(3, "feedback: %v", err)
		}
		stub, err := st.WriteStub(e.root, rec, 8)
		if err != nil {
			return fail(3, "feedback stub: %v", err)
		}
		if !added {
			fmt.Printf("already recorded: %s %s %s:%d\n", rec.ID, rec.RuleID, rec.Path, rec.Line)
		} else {
			fmt.Printf("recorded false positive %s (%s at %s:%d); the finding is suppressed in future scans\n", rec.ID, rec.RuleID, rec.Path, rec.Line)
		}
		fmt.Printf("regression stub: %s\n", relTo(e.root, stub))
		recs, _ := st.Load()
		n := feedback.Counts(recs, e.ruleVersion)[rec.RuleID]
		th := e.cfg.Feedback.FPThreshold
		if th == 0 {
			th = feedback.DefaultThreshold
		}
		switch {
		case th < 0:
		case n >= th:
			fmt.Printf("rule %s: %d false positive(s) >= threshold %d: demoted to shadow mode (runs, logged, never reported) until the rule is fixed (new rule_version) or records are undone\n", rec.RuleID, n, th)
		default:
			fmt.Printf("rule %s: %d/%d false positive(s) before it is demoted to shadow mode\n", rec.RuleID, n, th)
		}
		return nil
	case "undo":
		if fs.NArg() != 1 {
			return fail(2, "usage: crev feedback undo FINGERPRINT")
		}
		n, err := st.Remove(fs.Arg(0))
		if err != nil {
			return fail(3, "feedback: %v", err)
		}
		fmt.Printf("removed %d record(s)\n", n)
		return nil
	case "list":
		recs, err := st.Load()
		if err != nil {
			return fail(3, "feedback: %v", err)
		}
		shadow := e.feedbackShadow()
		if *asJSON {
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			return enc.Encode(map[string]any{"records": recs, "shadow": shadow})
		}
		for _, r := range recs {
			fmt.Printf("%s  %-28s %s:%d  %s\n", r.ID[:min(12, len(r.ID))], r.RuleID, r.Path, r.Line, r.Reason)
		}
		for _, id := range slices.Sorted(maps.Keys(shadow)) {
			fmt.Printf("shadow: %s (%s)\n", id, shadow[id])
		}
		if len(recs) == 0 {
			fmt.Println("no false-positive feedback recorded")
		}
		return nil
	}
	return fail(2, "unknown feedback command %q (fp | list | undo)", sub)
}

// findFinding resolves a fingerprint (or unique prefix) in a run report (default latest).
func (e *env) findFinding(runRef, id string) (*findings.Finding, string, error) {
	var rep *findings.Report
	runID := ""
	st := e.runStore()
	if m, err := st.Resolve(runRef); err == nil {
		if rep, err = st.Report(m); err != nil {
			return nil, "", fail(2, "run %s: %v", m.ID, err)
		}
		runID = m.ID
	} else if runRef != "latest" {
		return nil, "", fail(2, "%v", err)
	} else if rep, err = e.loadState(); err != nil {
		return nil, "", err
	}
	var hits []*findings.Finding
	for _, f := range rep.Findings {
		if f.ID == id {
			return f, runID, nil
		}
		if strings.HasPrefix(f.ID, id) {
			hits = append(hits, f)
		}
	}
	switch len(hits) {
	case 0:
		return nil, "", fail(2, "no finding with fingerprint %q in run %s", id, runRef)
	case 1:
		return hits[0], runID, nil
	}
	return nil, "", fail(2, "fingerprint prefix %q is ambiguous (%d findings)", id, len(hits))
}

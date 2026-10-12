package feedback

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
)

func TestFeedbackDemotesAndStubs(t *testing.T) {
	root := t.TempDir()
	os.WriteFile(filepath.Join(root, "a.go"), []byte("package a\n\nfunc f() { x() }\n"), 0o644)
	s := Store{Dir: filepath.Join(root, ".state", "feedback")}
	now := time.Unix(0, 0)
	mk := func(id string) *findings.Finding {
		return &findings.Finding{ID: id, RuleID: "R1", RuleVersion: 2, Location: findings.Location{Path: "a.go", StartLine: 3}}
	}
	for _, id := range []string{"aa", "bb", "aa"} { // duplicate is idempotent
		if _, _, err := s.Add(mk(id), "not a bug", "run1", now); err != nil {
			t.Fatal(err)
		}
	}
	recs, err := s.Load()
	if err != nil || len(recs) != 2 {
		t.Fatalf("records: %v %v", recs, err)
	}
	ver := func(string) int { return 2 }
	if sh := Shadow(recs, 3, ver); len(sh) != 0 {
		t.Fatalf("below threshold: %v", sh)
	}
	if sh := Shadow(recs, 2, ver); !strings.Contains(sh["R1"], "2 false positive") {
		t.Fatalf("at threshold the rule is demoted: %v", sh)
	}
	if sh := Shadow(recs, 2, func(string) int { return 3 }); len(sh) != 0 {
		t.Fatalf("a rule_version bump (rule fixed) lifts the demotion: %v", sh)
	}
	rep := &findings.Report{Findings: []*findings.Finding{mk("aa"), mk("cc")}, Stats: map[string]int{}}
	if n := Apply(rep, recs, "fp.jsonl"); n != 1 || rep.Findings[0].Status != "suppressed" || rep.Findings[1].Status == "suppressed" {
		t.Fatalf("apply: %d %+v", n, rep.Findings)
	}
	p, err := s.WriteStub(root, recs[0], 5)
	if err != nil {
		t.Fatal(err)
	}
	b, _ := os.ReadFile(p)
	if !strings.Contains(string(b), "func f() { x() }") || !strings.Contains(string(b), "fingerprint: aa") {
		t.Fatalf("stub: %s", b)
	}
	if n, _ := s.Remove("a"); n != 1 {
		t.Fatalf("undo removed %d", n)
	}
}

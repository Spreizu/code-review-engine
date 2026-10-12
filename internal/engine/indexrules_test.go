package engine

import (
	"testing"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/report"
)

func TestIndexRulesCapAndGate(t *testing.T) {
	root := t.TempDir()
	write(t, root, "go.mod", "module x\n\ngo 1.24\n")
	write(t, root, "p/p.go", "package p\n\nfunc common(a, b []string) []string {\n\tvar out []string\n\tfor _, x := range a {\n\t\tfor _, y := range b {\n\t\t\tif x == y {\n\t\t\t\tout = append(out, x)\n\t\t\t}\n\t\t}\n\t}\n\treturn out\n}\n")
	rs := catalogRules(t, "GO-SIMP-IDX-NESTED-LOOP-NO-LIMIT-NOTE")
	rep, err := Scan(Options{Root: root, Rules: rs, Latest: latest, Severity: map[string]string{"GO-SIMP-IDX-NESTED-LOOP-NO-LIMIT-NOTE": "critical"}})
	if err != nil {
		t.Fatal(err)
	}
	if len(rep.Findings) != 1 {
		t.Fatalf("findings=%d stats=%v errors=%v", len(rep.Findings), rep.Stats, rep.Errors)
	}
	f := rep.Findings[0]
	if f.Severity != "minor" || f.Evidence == "" {
		t.Fatalf("severity %q (want capped minor), evidence %q", f.Severity, f.Evidence)
	}
	f.Severity = "critical" // even if forced, the advisory layer never gates
	if report.Gating(f, report.GateOptions{FailOn: "info"}) {
		t.Fatal("simplification finding must not gate")
	}
	if rep.Stats["index_files"] != 1 {
		t.Fatalf("index stats: %v", rep.Stats)
	}
}

func TestReroute(t *testing.T) {
	rep := &findings.Report{Stats: map[string]int{}, Findings: []*findings.Finding{
		{RuleID: "S", Category: "simplification", Location: findings.Location{Path: "a.go", StartLine: 3, EndLine: 9}},
		{RuleID: "B", Category: "security", Location: findings.Location{Path: "a.go", StartLine: 5, EndLine: 5}},
		{RuleID: "S2", Category: "simplification", Location: findings.Location{Path: "a.go", StartLine: 20, EndLine: 22}},
	}}
	capAndReroute(rep)
	if len(rep.Findings) != 2 || rep.Findings[0].RuleID != "B" || rep.Stats["simplification_rerouted"] != 1 {
		t.Fatalf("got %+v stats %v", rep.Findings, rep.Stats)
	}
}

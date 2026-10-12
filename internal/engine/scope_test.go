package engine

import (
	"testing"

	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/scope"
)

func receiverRule() *rules.Rule {
	r := &rules.Rule{ID: "T-RECV-THIS", Language: "go", Severity: "info", Kind: "best-practice", Message: "m", AppliesTo: map[string]string{}}
	r.Detection.Mode, r.Detection.Engine = "deterministic", "tree-sitter"
	r.Detection.Query = `(method_declaration receiver: (parameter_list (parameter_declaration name: (identifier) @match (#eq? @match "this"))))`
	return r
}

func TestScopeFiltersReportedFindings(t *testing.T) {
	root := t.TempDir()
	write(t, root, "go.mod", "module x\n\ngo 1.25\n")
	write(t, root, "a.go", "package a\n\nfunc (this *S) Old() {}\n\nfunc (this *S) New() {}\n")
	write(t, root, "b.go", "package a\n\nfunc (this *S) Other() {}\n")
	full, err := Scan(Options{Root: root, Rules: []*rules.Rule{receiverRule()}})
	if err != nil {
		t.Fatal(err)
	}
	if len(full.Findings) != 3 {
		t.Fatalf("full scan: %d findings", len(full.Findings))
	}
	sc := &scope.Scope{Mode: "base", DiffContext: "hunk", Files: map[string][]scope.Range{"a.go": {{Start: 5, End: 5}}}}
	diff, err := Scan(Options{Root: root, Rules: []*rules.Rule{receiverRule()}, Scope: sc})
	if err != nil {
		t.Fatal(err)
	}
	if len(diff.Findings) != 1 || diff.Findings[0].Location.StartLine != 5 || diff.Stats["out_of_scope"] != 1 || diff.Scope == nil {
		t.Fatalf("diff scan: %+v stats=%v", diff.Findings, diff.Stats)
	}
	// the fingerprint does not depend on scope: same finding, same id
	for _, f := range full.Findings {
		if f.Location.StartLine == 5 && f.ID != diff.Findings[0].ID {
			t.Fatal("fingerprint differs between full and diff scans")
		}
	}
	sc.DiffContext = "file"
	whole, _ := Scan(Options{Root: root, Rules: []*rules.Rule{receiverRule()}, Scope: sc})
	if len(whole.Findings) != 2 {
		t.Fatalf("diff-context file: %d", len(whole.Findings))
	}
}

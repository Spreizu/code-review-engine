package rulecheck

import (
	"fmt"
	"strings"
	"testing"

	"github.com/elmo/code-review-engine/internal/rules"
)

var n int

// goRule builds a user rule; ids are unique because the engine caches compiled queries per rule id.
func goRule(query, bad, good string) *rules.Rule {
	n++
	r := &rules.Rule{ID: fmt.Sprintf("TEAM-X%d", n), Title: "t", Language: "go", Kind: "anti-pattern", Category: "style", Severity: "minor",
		AppliesTo: map[string]string{"go": "*"}, Message: "m"}
	r.Detection.Mode, r.Detection.Engine, r.Detection.Query = "deterministic", "tree-sitter", query
	r.Examples.Bad, r.Examples.Good = bad, good
	return r
}

func TestCheckUserRule(t *testing.T) {
	ok := goRule(`((var_spec name: (identifier) @match) (#eq? @match "foo"))`, "var foo = 1\n", "var bar = 1\n")
	res := Check(ok, Options{})
	if len(res.Errors) != 0 {
		t.Fatalf("errors: %v", res.Errors)
	}
	if len(res.Warnings) == 0 || !strings.Contains(res.Warnings[0], "source") {
		t.Fatalf("missing-source should be a warning for user rules: %v", res.Warnings)
	}
	if res := Check(ok, Options{RequireSource: true}); len(res.Errors) == 0 {
		t.Fatal("RequireSource should turn the missing citation into an error")
	}
	loose := goRule(`(identifier) @match`, "var foo = 1\n", "var bar = 1\n")
	if res := Check(loose, Options{}); len(res.Errors) == 0 {
		t.Fatal("good example matching must fail")
	}
	broken := goRule(`(no_such_node) @match`, "", "")
	res = Check(broken, Options{SkipExamples: true})
	if len(res.Errors) == 0 {
		t.Fatal("invalid node type must fail even with SkipExamples")
	}
	if !strings.Contains(strings.Join(res.Warnings, " "), "examples") {
		t.Fatalf("missing examples should be a warning with SkipExamples: %v", res.Warnings)
	}
	top := goRule(`(identifier) @match (#eq? @match "foo")`, "var foo = 1\n", "var bar = 1\n")
	if res := Check(top, Options{}); !strings.Contains(strings.Join(res.Errors, " "), "top level") {
		t.Fatalf("top-level predicate not flagged: %v", res.Errors)
	}
}

func TestRegressionsAndPrecisionGate(t *testing.T) {
	r := goRule(`((var_spec name: (identifier) @match) (#eq? @match "foo"))`, "var foo = 1\n", "var bar = 1\n")
	r.Examples.Regressions = []rules.Regression{{Code: "var baz = 1\n"}, {Code: "var foo = 2\n", Note: "former FP"}}
	res := Check(r, Options{})
	if len(res.Errors) != 1 || !strings.Contains(res.Errors[0], "regression[1] (former FP)") {
		t.Fatalf("matching regression must fail with its note: %v", res.Errors)
	}
	// path-bound regression: excluded by detection.files => passes
	r.Examples.Regressions = []rules.Regression{{Code: "var foo = 2\n", Path: "x_test.go"}}
	r.Detection.Files = []string{"!**/*_test.go"}
	if res := Check(r, Options{}); len(res.Errors) != 0 {
		t.Fatalf("path-excluded regression must pass: %v", res.Errors)
	}
	r.Precision = "low"
	if res := Check(r, Options{}); !strings.Contains(strings.Join(res.Errors, " "), "requires detection.mode ai-confirm") {
		t.Fatalf("precision low + deterministic must fail: %v", res.Errors)
	}
	r.Precision, r.Status = "", "shadow"
	if res := Check(r, Options{}); !strings.Contains(strings.Join(res.Errors, " "), "status_reason") {
		t.Fatalf("shadow without reason must fail: %v", res.Errors)
	}
	r.Status, r.Kind = "", "security"
	if res := Check(r, Options{}); !strings.Contains(strings.Join(res.Errors, " "), "cwe") {
		t.Fatalf("security rule without cwe must fail: %v", res.Errors)
	}
}

func TestCaptureFilters(t *testing.T) {
	// cap.lacks_re + {cap:NAME}: loop variable modified in the body
	r := goRule(`(for_statement (for_clause initializer: (short_var_declaration left: (expression_list (identifier) @i))) body: (block) @body) @match`,
		"func f() {\n\tfor i := 0; i < 3; i++ {\n\t\tuse(i)\n\t}\n}\n", "func f() {\n\tfor i := 0; i < 3; i++ {\n\t\ti += 2\n\t}\n}\n")
	r.Detection.Filters = []string{`cap.lacks_re:body:(^|[^\w.]){cap:i}\s*(\+\+|[-+]?=[^=])`}
	if res := Check(r, Options{}); len(res.Errors) != 0 {
		t.Fatalf("cap filter: %v", res.Errors)
	}
	// func.lacks_re: enclosing function text
	f := goRule(`((call_expression function: (identifier) @f) @match (#eq? @f "use"))`, "func f(v int) {\n\tuse(v)\n}\n", "func f(v any) {\n\tuse(v)\n}\n")
	f.Detection.Filters = []string{`func.lacks_re:\bv any\b`}
	if res := Check(f, Options{}); len(res.Errors) != 0 {
		t.Fatalf("func filter: %v", res.Errors)
	}
}

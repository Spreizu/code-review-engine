package engine

import (
	"strings"
	"testing"

	"github.com/elmo/code-review-engine/internal/rules"
)

func TestTypeIsFilter(t *testing.T) {
	r := &rules.Rule{ID: "T", Detection: rules.Detection{
		Grammar: "java",
		Query:   `(method_invocation object: (identifier) @o name: (identifier) @m) @match`,
		Filters: []string{`type.is:o:String`},
	}}
	tr, err := Parse("java", []byte(`class A { void f(String s, StringBuilder b) { s.trim(); b.trim(); } }`))
	if err != nil {
		t.Fatal(err)
	}
	defer tr.Close()
	hits, err := Run(r, tr)
	if err != nil {
		t.Fatal(err)
	}
	if len(hits) != 1 || !strings.Contains(hits[0].Text, "s.trim") {
		t.Fatalf("hits = %v", hits)
	}
}

func TestTypeEqTextFilter(t *testing.T) {
	r := &rules.Rule{ID: "T", Detection: rules.Detection{
		Grammar: "java",
		Query:   `(cast_expression type: (_) @t value: (_) @v) @match`,
		Filters: []string{`type.eq_text:v:t`},
	}}
	tr, err := Parse("java", []byte(`class A { void f(String s, Object o) { String a = (String) s; String b = (String) o; } }`))
	if err != nil {
		t.Fatal(err)
	}
	defer tr.Close()
	hits, err := Run(r, tr)
	if err != nil {
		t.Fatal(err)
	}
	if len(hits) != 1 || !strings.Contains(hits[0].Text, "(String) s") {
		t.Fatalf("hits = %v", hits)
	}
}

func TestFullTypeModeCrossFile(t *testing.T) {
	root := t.TempDir()
	write(t, root, "Repo.java", "class Repo { User find() { return null; } }\n")
	write(t, root, "S.java", "class S { Repo repo; void f() { repo.find().name(); } }\n")
	r := &rules.Rule{ID: "T", Language: "java", Detection: rules.Detection{
		Engine: "tree-sitter", Grammar: "java",
		Query:   `(method_invocation object: (_) @o name: (identifier) @m (#eq? @m "name")) @match`,
		Filters: []string{`type.is:o:User`},
	}}
	scan := func(mode string) int {
		rep, err := Scan(Options{Root: root, Rules: []*rules.Rule{r}, TypeMode: mode, NoGitignore: true, NoDefaultExcludes: true})
		if err != nil {
			t.Fatal(err)
		}
		n := 0
		for _, f := range rep.Findings {
			if f.RuleID == "T" {
				n++
			}
		}
		return n
	}
	if n := scan("basic"); n != 0 {
		t.Fatalf("basic: want 0 hits (find is in another file), got %d", n)
	}
	if n := scan("full"); n != 1 {
		t.Fatalf("full: want 1 hit, got %d", n)
	}
}

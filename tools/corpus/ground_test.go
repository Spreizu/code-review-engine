package main

import (
	"path/filepath"
	"testing"

	"github.com/elmo/code-review-engine/internal/projcfg"
)

func TestAutofixMsg(t *testing.T) {
	ok := []string{
		"chore: eslint --fix",
		"run yarn lint:fix",
		"ruff check --fix on src",
		"gofmt the package",
		"Apply prettier --write",
		"autofix lint errors",
	}
	no := []string{
		"fix bug in parser",
		"security fix for XSS",
		"update eslint to 9",
	}
	for _, s := range ok {
		if !autofixMsg.MatchString(s) {
			t.Errorf("want match: %s", s)
		}
	}
	for _, s := range no {
		if autofixMsg.MatchString(s) {
			t.Errorf("must not match: %s", s)
		}
	}
}

func TestRulesForInline(t *testing.T) {
	byEq := map[string][]string{"eslint:no-eval": {"JS-SEC-EVAL-001"}, "ruff:S307": {"PY-SEC-EVAL"}}
	got := rulesForInline(projcfg.Inline{Tools: []string{"eslint", "oxlint"}, IDs: []string{"no-eval"}}, byEq)
	if len(got) != 1 || got[0] != "JS-SEC-EVAL-001" {
		t.Fatalf("%v", got)
	}
}

func TestSuppressionJoin(t *testing.T) {
	src := []byte("// eslint-disable-next-line no-eval -- legacy\neval(x)\neval(y)\n")
	fi := projcfg.ParseInline("a.js", src)
	sb := fi.Match("a.js", "JS-SEC-EVAL-001", []string{"eslint:no-eval"}, 2, 2)
	if sb == nil || sb.Kind != "inline" || sb.ID != "no-eval" {
		t.Fatalf("line 2: %+v", sb)
	}
	if fi.Match("a.js", "JS-SEC-EVAL-001", []string{"eslint:no-eval"}, 3, 3) != nil {
		t.Fatal("line 3 must not be covered")
	}
}

func TestParseRuffOxlintYamllint(t *testing.T) {
	d := parseRuff([]byte(`[{"code":"S307","filename":"/tmp/a.py","location":{"row":4,"column":1}}]`))
	if len(d) != 1 || d[0].Tool != "ruff" || d[0].ID != "S307" || d[0].Line != 4 {
		t.Fatalf("ruff %+v", d)
	}
	o := parseOxlint([]byte(`{"diagnostics":[{"filename":"a.js","ruleId":"no-eval","start":{"line":2}}]}`))
	if len(o) != 1 || o[0].Tool != "eslint" || o[0].ID != "no-eval" || o[0].Line != 2 {
		t.Fatalf("oxlint %+v", o)
	}
	y, ok := yamllintLine(`foo.yaml:12:5: [warning] truthy value (truthy)`)
	if !ok || y.Tool != "yamllint" || y.ID != "truthy" || y.Line != 12 || y.Path != "foo.yaml" {
		t.Fatalf("yamllint %+v ok=%v", y, ok)
	}
	if _, ok := yamllintLine("other: skip"); ok {
		t.Fatal("non-diagnostic line")
	}
}

func TestGithubName(t *testing.T) {
	if githubName("https://github.com/expressjs/express.git") != "expressjs/express" {
		t.Fatal(githubName("https://github.com/expressjs/express.git"))
	}
}

func TestRelPathAbsVsRelativeRoot(t *testing.T) {
	root := t.TempDir()
	want := "pkg/a.py"
	abs := filepath.Join(root, filepath.FromSlash(want))
	if got := relPath(root, abs); got != want {
		t.Fatalf("abs linter path: got %q want %q", got, want)
	}
	if got := relPath(root, want); got != want {
		t.Fatalf("relative: got %q want %q", got, want)
	}
}

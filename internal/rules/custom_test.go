package rules

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func builtinFixture(t *testing.T) []*Rule {
	t.Helper()
	dir := t.TempDir()
	p := filepath.Join(dir, "base.yaml")
	must(t, os.WriteFile(p, []byte(`pack: base
pack_version: "2026.10.0"
rules:
  - id: BASE-ONE
    title: one
    language: go
    kind: best-practice
    category: style
    severity: minor
    applies_to: {go: ">=1.21"}
    detection: {mode: deterministic, engine: tree-sitter, query: "(identifier) @match", files: ["**/*.go"]}
    message: m1
    source: {url: "https://go.dev/doc/", doc: d, doc_version: "1.21", retrieved: "2026-10-01"}
    examples: {bad: "x", good: "1"}
  - id: BASE-TWO
    title: two
    language: go
    kind: security
    category: security
    severity: major
    applies_to: {go: "*"}
    detection: {mode: deterministic, engine: tree-sitter, query: "(identifier) @match"}
    message: m2
    source: {url: "https://go.dev/doc/", doc: d, doc_version: "1", retrieved: "2026-10-01"}
    examples: {bad: "x", good: "1"}
`), 0o644))
	rs, err := LoadFiles(p)
	must(t, err)
	return rs
}

func must(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}

func byID(rs []*Rule) map[string]*Rule {
	m := map[string]*Rule{}
	for _, r := range rs {
		m[r.ID] = r
	}
	return m
}

func TestApplyCustomPatchReplaceDisableAdd(t *testing.T) {
	base := builtinFixture(t)
	dir := filepath.Join(t.TempDir(), ".crev", "rules")
	must(t, os.MkdirAll(filepath.Join(dir, "team"), 0o755))
	must(t, os.WriteFile(filepath.Join(dir, "a.yaml"), []byte(`rules:
  - id: BASE-ONE
    severity: critical
    applies_to: {go: ">=1.22"}
    detection: {files: ["internal/**/*.go"]}
  - id: BASE-TWO
    disabled: true
`), 0o644))
	must(t, os.WriteFile(filepath.Join(dir, "team", "b.yml"), []byte(`pack: team
rules:
  - id: TEAM-NO-FOO
    title: no foo
    language: go
    kind: anti-pattern
    category: style
    severity: info
    applies_to: {go: "*"}
    detection: {mode: deterministic, engine: tree-sitter, query: "((identifier) @match (#eq? @match \"foo\"))"}
    message: do not name things foo
    examples: {bad: "var foo = 1", good: "var bar = 1"}
`), 0o644))
	files, err := CustomFiles(dir, filepath.Join(t.TempDir(), "missing"))
	must(t, err)
	if len(files) != 2 {
		t.Fatalf("files=%v", files)
	}
	eff, changes, err := ApplyCustom(base, files)
	must(t, err)
	m := byID(eff)
	if m["BASE-TWO"] != nil {
		t.Fatal("BASE-TWO should be disabled")
	}
	one := m["BASE-ONE"]
	if one.Severity != "critical" || one.AppliesTo["go"] != ">=1.22" || one.Detection.Files[0] != "internal/**/*.go" {
		t.Fatalf("patch not applied: %+v", one)
	}
	if one.Detection.Query != "(identifier) @match" || one.Detection.Engine != "tree-sitter" || one.Message != "m1" || one.Pack != "base" {
		t.Fatalf("patch lost base fields: %+v", one)
	}
	if one.Origin != "custom" || !strings.HasSuffix(one.BaseFile, "base.yaml") {
		t.Fatalf("origin/base: %q %q", one.Origin, one.BaseFile)
	}
	nr := m["TEAM-NO-FOO"]
	if nr == nil || nr.Pack != "team" || nr.Origin != "custom" || nr.RuleVersion != 1 {
		t.Fatalf("added rule: %+v", nr)
	}
	acts := []string{}
	for _, c := range changes {
		acts = append(acts, c.Action+":"+c.ID)
	}
	if strings.Join(acts, ",") != "patch:BASE-ONE,disable:BASE-TWO,add:TEAM-NO-FOO" {
		t.Fatalf("changes %v", acts)
	}
}

func TestApplyCustomReplaceAndErrors(t *testing.T) {
	base := builtinFixture(t)
	d := t.TempDir()
	w := func(name, body string) string {
		p := filepath.Join(d, name)
		must(t, os.WriteFile(p, []byte(body), 0o644))
		return p
	}
	rep := w("r.yaml", `rules:
  - id: BASE-ONE
    override: replace
    title: replaced
    language: go
    kind: best-practice
    category: style
    severity: info
    applies_to: {go: "*"}
    detection: {mode: deterministic, engine: tree-sitter, query: "(int_literal) @match"}
    message: new
    examples: {bad: "1", good: "x"}
`)
	eff, _, err := ApplyCustom(base, []string{rep})
	must(t, err)
	one := byID(eff)["BASE-ONE"]
	if one.Title != "replaced" || len(one.Detection.Files) != 0 || one.Source.URL != "" {
		t.Fatalf("replace should not inherit: %+v", one)
	}
	for name, body := range map[string]string{
		"unknown-disable.yaml": "rules:\n  - id: NOPE-X\n    disabled: true\n",
		"unknown-replace.yaml": "rules:\n  - id: NOPE-X\n    override: replace\n    title: t\n",
		"bad-mode.yaml":        "rules:\n  - id: BASE-ONE\n    override: merge\n",
		"typo-field.yaml":      "rules:\n  - id: BASE-ONE\n    severty: info\n",
		"dup.yaml":             "rules:\n  - id: BASE-ONE\n    severity: info\n  - id: BASE-ONE\n    severity: major\n",
		"no-id.yaml":           "rules:\n  - severity: info\n",
	} {
		if _, _, err := ApplyCustom(base, []string{w(name, body)}); err == nil {
			t.Errorf("%s: expected error", name)
		}
	}
}

func TestApplyCustomLaterFileWins(t *testing.T) {
	base := builtinFixture(t)
	d := t.TempDir()
	must(t, os.WriteFile(filepath.Join(d, "10.yaml"), []byte("rules:\n  - id: BASE-ONE\n    severity: info\n"), 0o644))
	must(t, os.WriteFile(filepath.Join(d, "20.yaml"), []byte("rules:\n  - id: BASE-ONE\n    message: later\n"), 0o644))
	files, err := CustomFiles(d)
	must(t, err)
	eff, _, err := ApplyCustom(base, files)
	must(t, err)
	one := byID(eff)["BASE-ONE"]
	if one.Severity != "info" || one.Message != "later" || !strings.HasSuffix(one.BaseFile, "base.yaml") {
		t.Fatalf("%+v", one)
	}
}

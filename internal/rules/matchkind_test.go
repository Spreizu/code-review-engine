package rules

import (
	"testing"
	"testing/fstest"
)

func mkRule(kind, mode, engine, q string, at map[string]string) *Rule {
	return &Rule{ID: "X", Kind: kind, AppliesTo: at, Detection: Detection{Mode: mode, Engine: engine, Query: q}}
}

func TestExactAPIClassifier(t *testing.T) {
	v := map[string]string{"vue": ">=3.0"}
	imp := `((import_specifier name: (identifier) @n) @match (#match? @n "^(createApp|h)$"))`
	cases := []struct {
		name string
		r    *Rule
		want bool
	}{
		{"exact import", mkRule("removal", "deterministic", "tree-sitter", imp, v), true},
		{"eq predicate", mkRule("deprecation", "deterministic", "tree-sitter", `((identifier) @match (#eq? @match "foo"))`, v), true},
		{"case-insensitive literal set", mkRule("removal", "deterministic", "tree-sitter", `((name) @match (#match? @match "(?i)^(each|money_format)$"))`, map[string]string{"php": ">=8.0"}), true},
		{"quoted terraform type", mkRule("removal", "deterministic", "tree-sitter", `((string) @match (#match? @match "^.(aws_s3_bucket).$"))`, map[string]string{"aws": ">=4"}), true},
		{"prefix regex", mkRule("removal", "deterministic", "tree-sitter", `((identifier) @match (#match? @match "^get[A-Z]"))`, v), false},
		{"structural", mkRule("removal", "deterministic", "tree-sitter", `(stream . (document) @match)`, v), false},
		{"alternative without predicate", mkRule("removal", "deterministic", "tree-sitter", imp+` (call_expression) @match`, v), false},
		{"not version gated", mkRule("removal", "deterministic", "tree-sitter", imp, map[string]string{"vue": "*"}), false},
		{"wrong kind", mkRule("security", "deterministic", "tree-sitter", imp, v), false},
		{"ai-confirm", mkRule("removal", "ai-confirm", "tree-sitter", imp, v), false},
		{"index engine", mkRule("removal", "deterministic", "index", "", v), false},
	}
	for _, c := range cases {
		if got, why := ExactAPI(c.r); got != c.want {
			t.Errorf("%s: got %v (%s), want %v", c.name, got, why, c.want)
		}
	}
	cfg := &Rule{Kind: "removal", AppliesTo: map[string]string{"spring-boot": ">=3.0"}, Detection: Detection{Mode: "deterministic", Engine: "config", Config: map[string]any{"key": "a.b", "op": "exists"}}}
	if ok, why := ExactAPI(cfg); !ok {
		t.Errorf("config key: %s", why)
	}
	cfg.Detection.Config = map[string]any{"key_prefix": "a.", "op": "exists"}
	if ok, _ := ExactAPI(cfg); ok {
		t.Error("key_prefix must not be exact-api")
	}
}

func TestExactAPIUnprovenReportsDirectly(t *testing.T) {
	ex := mkRule("removal", "deterministic", "tree-sitter", "", nil)
	ex.ID, ex.MatchKind = "EX", MatchKindExactAPI
	other := mkRule("removal", "deterministic", "tree-sitter", "", nil)
	other.ID = "OT"
	fsys := fstest.MapFS{"data/trust.yaml": {Data: []byte("rules:\n  EX: {level: unproven}\n  OT: {level: unproven}\n")}}
	if err := ApplyTrust([]*Rule{ex, other}, fsys); err != nil {
		t.Fatal(err)
	}
	if ex.Detection.Mode != "deterministic" || ex.Trust.Demoted {
		t.Errorf("exact-api rule demoted: %+v", ex.Trust)
	}
	if other.Detection.Mode != "ai-confirm" {
		t.Errorf("unproven non-exact rule not demoted")
	}
}

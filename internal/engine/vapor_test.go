package engine

import (
	"strings"
	"testing"

	"github.com/elmo/code-review-engine/internal/findings"
)

// The vendored Vue grammar must accept the Vapor markers (a bare `vapor` attribute on <script setup>
// and <template>) without error nodes, and VueScript must still extract the script block.
func TestVueGrammarParsesVaporAttribute(t *testing.T) {
	src := []byte("<script setup vapor lang=\"ts\">\nconst n = ref(0)\n</script>\n<template vapor><button @click=\"n++\">{{ n }}</button></template>\n")
	tr, err := Parse("vue", src)
	if err != nil {
		t.Fatal(err)
	}
	defer tr.Close()
	sx := tr.SExpr()
	if strings.Contains(sx, "ERROR") || strings.Contains(sx, "MISSING") {
		t.Fatalf("vapor attribute did not parse cleanly: %s", sx)
	}
	if strings.Count(sx, "(attribute_name)") < 2 {
		t.Fatalf("vapor attribute not recognised as an attribute: %s", sx)
	}
	script, grammar, lang, ok := VueScript(src)
	if !ok || grammar != "typescript" || lang != "ts" || !strings.Contains(string(script), "ref(0)") {
		t.Fatalf("VueScript: ok=%v grammar=%q lang=%q", ok, grammar, lang)
	}
}

// Vapor rules are gated on Vue >= 3.6, read the SFC marker through sfc.has_re, and ship in shadow.
func TestVaporRulesGatedAndShadowed(t *testing.T) {
	rs := catalogRules(t, "VUE-VAPOR-GET-CURRENT-INSTANCE", "VUE-VAPOR-V-MEMO")
	vapor := "<script setup vapor>\nimport { getCurrentInstance } from 'vue'\nconst i = getCurrentInstance()\n</script>\n<template><div v-memo=\"[a]\">{{ a }}</div></template>\n"
	vdom := strings.Replace(vapor, " vapor>", ">", 1)
	scan := func(vue string) *findings.Report {
		root := t.TempDir()
		write(t, root, "package.json", `{"dependencies":{"vue":"`+vue+`"}}`)
		write(t, root, "src/A.vue", vapor)
		write(t, root, "src/B.vue", vdom)
		rep, _ := Scan(Options{Root: root, Rules: rs, IncludeShadow: true})
		return rep
	}
	rep := scan("^3.6.0")
	got := map[string]string{}
	for _, f := range rep.Findings {
		got[f.RuleID+" "+f.Location.Path] = f.Status
	}
	for _, k := range []string{"VUE-VAPOR-GET-CURRENT-INSTANCE src/A.vue", "VUE-VAPOR-V-MEMO src/A.vue"} {
		if got[k] != "shadow" {
			t.Errorf("%s: want shadow finding, got %q (all: %v)", k, got[k], got)
		}
	}
	for k := range got {
		if strings.HasSuffix(k, "B.vue") {
			t.Errorf("VDOM component flagged: %s", k)
		}
	}
	if rep := scan("^3.5.0"); len(rep.Findings) != 0 {
		t.Errorf("Vue 3.5 project: want no Vapor findings, got %d", len(rep.Findings))
	}
}

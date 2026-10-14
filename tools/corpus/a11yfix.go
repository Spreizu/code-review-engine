package main

// Accessibility linter suites as labelled data (extracted locally, never copied into packs):
// axe-core integration fixtures (HTML fragments + expected violation/pass element ids, scored at
// line level on the labelled elements only), eslint-plugin-jsx-a11y and
// eslint-plugin-vuejs-accessibility RuleTester cases, and stylelint testRule accept/reject cases.

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	ts "github.com/tree-sitter/go-tree-sitter"

	"github.com/elmo/code-review-engine/internal/grammars"
)

func a11yExtract(ruleID, tool, id string) ([]fcase, int, string, bool) {
	// each suite is written in one syntax: score only the rule variant for that syntax
	want := map[string]string{"axe": "HTML-|CSS-", "jsx-a11y": "JS-", "vuejs-accessibility": "VUE-"}[tool]
	if want != "" && !regexp.MustCompile("^("+want+")").MatchString(ruleID) {
		return nil, 0, "suite written for another syntax", true
	}
	switch tool {
	case "axe":
		c, s, w := axeCases(id)
		return c, s, w, true
	case "jsx-a11y":
		c, s, w := codeObjects(filepath.Join(fxRoot, "eslint-plugin-jsx-a11y/__tests__/src/rules", id+"-test.js"), "snippet.jsx", "valid", "invalid", nil)
		return c, s, w, true
	case "vuejs-accessibility":
		c, s, w := codeObjects(filepath.Join(fxRoot, "eslint-plugin-vuejs-accessibility/src/rules/__tests__", id+".test.ts"), "snippet.vue", "valid", "invalid", nil)
		for i := range c {
			c[i].Code, c[i].File = "<template>"+c[i].Code+"</template>\n", "snippet.vue"
		}
		return c, s, w, true
	case "stylelint":
		p := filepath.Join(fxRoot, "stylelint/lib/rules", id, "__tests__/index.mjs")
		if _, err := os.Stat(p); err != nil {
			p = strings.TrimSuffix(p, ".mjs") + ".js"
		}
		c, s, w := codeObjects(p, "snippet.css", "accept", "reject", stylelintDefault)
		for i := range c {
			if strings.Contains(c[i].Code, "stylelint-disable") || strings.Contains(c[i].Code, "stylelint-enable") {
				c[i].Env = "inline stylelint directive"
			}
		}
		return c, s, w, true
	}
	return nil, 0, "", false
}

// stylelintDefault: only testRule({...}) calls with the default `config: [true]` (or true) and no
// custom syntax score a crev rule.
func stylelintDefault(call *ts.Node, src []byte) bool {
	t := call.Utf8Text(src)
	if strings.Contains(t, "customSyntax") || strings.Contains(t, "syntax:") || strings.Contains(t, "plugins:") {
		return false
	}
	m := regexp.MustCompile(`config:\s*(\[\s*true\s*\]|true)\s*,`).FindStringIndex(t)
	return m != nil && !regexp.MustCompile(`config:\s*\[\s*true\s*,`).MatchString(t)
}

// codeObjects collects RuleTester-style cases: under each `valid`/`invalid` (or accept/reject)
// key, every string element and every object with a `code` property, however the array is built
// (parsers.all([].concat(...)).map(...)). gate filters the enclosing call (stylelint testRule).
func codeObjects(path, file, okKey, badKey string, gate func(*ts.Node, []byte) bool) ([]fcase, int, string) {
	src, err := os.ReadFile(path)
	if err != nil {
		return nil, 0, "suite not found"
	}
	lang := "javascript"
	if strings.HasSuffix(path, ".ts") {
		lang = "typescript"
	}
	p := ts.NewParser()
	defer p.Close()
	p.SetLanguage(grammars.Get(lang))
	tree := p.Parse(src, nil)
	defer tree.Close()
	rel, _ := filepath.Rel(fxRoot, path)
	var cases []fcase
	skipped := 0
	var collect func(n *ts.Node, valid bool)
	collect = func(n *ts.Node, valid bool) {
		switch n.Kind() {
		case "object":
			hasCode := false
			for i := uint(0); i < n.NamedChildCount(); i++ {
				if pr := n.NamedChild(i); pr.Kind() == "pair" && strings.Trim(pr.ChildByFieldName("key").Utf8Text(src), `"'`) == "code" {
					hasCode = true
				}
			}
			if hasCode {
				code, f, ok := caseCode(n, src, file)
				if !ok {
					skipped++
					return
				}
				cases = append(cases, fcase{Code: code, File: f, Valid: valid, Origin: fmt.Sprintf("%s:%d", rel, n.StartPosition().Row+1)})
				return
			}
		case "string", "template_string":
			if pa := n.Parent(); pa != nil && pa.Kind() == "array" {
				code, f, ok := caseCode(n, src, file)
				if !ok {
					skipped++
					return
				}
				cases = append(cases, fcase{Code: code, File: f, Valid: valid, Origin: fmt.Sprintf("%s:%d", rel, n.StartPosition().Row+1)})
			}
			return
		}
		for i := uint(0); i < n.NamedChildCount(); i++ {
			collect(n.NamedChild(i), valid)
		}
	}
	var walk func(n *ts.Node)
	walk = func(n *ts.Node) {
		if gate != nil && n.Kind() == "call_expression" {
			if f := n.ChildByFieldName("function"); f != nil && f.Utf8Text(src) == "testRule" && !gate(n, src) {
				return
			}
		}
		if n.Kind() == "pair" {
			k := strings.Trim(n.ChildByFieldName("key").Utf8Text(src), `"'`)
			if k == okKey || k == badKey {
				collect(n.ChildByFieldName("value"), k == okKey)
				return
			}
		}
		for i := uint(0); i < n.NamedChildCount(); i++ {
			walk(n.NamedChild(i))
		}
	}
	walk(tree.RootNode())
	if len(cases) == 0 {
		return nil, skipped, "no static cases"
	}
	return cases, skipped, ""
}

// axeCases: one line-level case per axe integration fixture; only the elements the fixture labels
// (violations / passes, by #id) are scored.
func axeCases(id string) ([]fcase, int, string) {
	d := filepath.Join(fxRoot, "axe-core/test/integration/rules", id)
	html, err := os.ReadFile(filepath.Join(d, id+".html"))
	if err != nil {
		return nil, 0, "suite not found"
	}
	var spec struct {
		Violations [][]string `json:"violations"`
		Passes     [][]string `json:"passes"`
	}
	b, err := os.ReadFile(filepath.Join(d, id+".json"))
	if err != nil || json.Unmarshal(b, &spec) != nil {
		return nil, 0, "bad fixture json"
	}
	head := "<!DOCTYPE html>\n<html lang=\"en\">\n<head><title>Fixture</title></head>\n<body>\n<main>\n"
	code := head + string(html) + "\n</main>\n</body>\n</html>\n"
	off := strings.Count(head, "\n")
	lineOf := func(sel []string) int {
		if len(sel) != 1 || !strings.HasPrefix(sel[0], "#") || strings.ContainsAny(sel[0][1:], " .>[:") {
			return 0
		}
		re := regexp.MustCompile(`\bid\s*=\s*["']?` + regexp.QuoteMeta(sel[0][1:]) + `["'\s/>]`)
		loc := re.FindIndex(html)
		if loc == nil {
			return 0
		}
		return off + strings.Count(string(html[:loc[0]]), "\n") + 1
	}
	c := fcase{Code: code, File: "fixture.html", Line: true, Origin: "axe-core/test/integration/rules/" + id}
	skipped := 0
	for _, v := range spec.Violations {
		if l := lineOf(v); l > 0 {
			c.Lines = append(c.Lines, l)
			c.Scope = append(c.Scope, l)
		} else {
			skipped++
		}
	}
	for _, v := range spec.Passes {
		if l := lineOf(v); l > 0 {
			c.Scope = append(c.Scope, l)
		} else {
			skipped++
		}
	}
	if len(c.Scope) == 0 {
		return nil, skipped, "no id-addressable cases"
	}
	return []fcase{c}, skipped, ""
}

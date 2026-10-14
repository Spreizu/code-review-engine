package projcfg

import (
	"encoding/json"
	"strings"

	ts "github.com/tree-sitter/go-tree-sitter"

	"github.com/elmo/code-review-engine/internal/grammars"
)

func init() {
	register(stylelintData, ".stylelintrc", ".stylelintrc.json", ".stylelintrc.yaml", ".stylelintrc.yml")
	register(stylelintJS, "stylelint.config.js", "stylelint.config.mjs", "stylelint.config.cjs", ".stylelintrc.js", ".stylelintrc.cjs", ".stylelintrc.mjs")
	register(stylelintPackage, "package.json")
}

// stylelintPresets: rules turned on by shared configs a project extends (only the ones crev's
// opt-in CSS rules map to; the recommended set's rules are not opt-in in crev).
var stylelintPresets = map[string][]string{
	"stylelint-config-standard":      {"property-no-vendor-prefix", "value-no-vendor-prefix", "selector-no-vendor-prefix", "at-rule-no-vendor-prefix", "media-feature-name-no-vendor-prefix"},
	"stylelint-config-standard-scss": {"property-no-vendor-prefix", "value-no-vendor-prefix", "selector-no-vendor-prefix", "at-rule-no-vendor-prefix", "media-feature-name-no-vendor-prefix"},
}

// stylelintRule records one rule: null turns it off, anything else (true, options, [true, {...}]) on.
func stylelintRule(s *Set, c ctx, id string, off bool, params map[string]any) {
	d := c.d("stylelint", id, off)
	d.Params = params
	s.add(d)
}

func stylelintObject(s *Set, c ctx, m map[string]any) {
	ext := strList(m["extends"])
	if e, ok := m["extends"].(string); ok {
		ext = append(ext, e)
	}
	for _, e := range ext {
		for _, id := range stylelintPresets[e] {
			stylelintRule(s, c, id, false, nil)
		}
	}
	rules, _ := m["rules"].(map[string]any)
	for id, v := range rules {
		var params map[string]any
		if a, ok := v.([]any); ok && len(a) > 1 {
			if o, ok := a[1].(map[string]any); ok {
				params = o
			}
		}
		if b, ok := v.(bool); ok && !b {
			continue // false is not a valid stylelint value; ignore
		}
		stylelintRule(s, c, id, v == nil, params)
	}
}

func stylelintData(s *Set, c ctx, b []byte) error {
	m, err := loose(b)
	if err != nil {
		return err
	}
	stylelintObject(s, c, m)
	return nil
}

func stylelintPackage(s *Set, c ctx, b []byte) error {
	var m map[string]any
	if json.Unmarshal(b, &m) != nil {
		return nil
	}
	if sc, ok := m["stylelint"].(map[string]any); ok {
		stylelintObject(s, c, sc)
	}
	return nil
}

// stylelintJS statically reads `export default {...}` / `module.exports = {...}` configs: the
// object with a `rules` property (null values turn rules off) and string `extends`.
func stylelintJS(s *Set, c ctx, b []byte) error {
	p := ts.NewParser()
	defer p.Close()
	if err := p.SetLanguage(grammars.Get("javascript")); err != nil {
		return err
	}
	tree := p.Parse(b, nil)
	defer tree.Close()
	var walk func(n *ts.Node)
	walk = func(n *ts.Node) {
		if n.Kind() == "object" {
			props := objectProps(n, b)
			m := map[string]any{"extends": props["extends"]}
			rules := map[string]any{}
			for i := uint(0); i < n.NamedChildCount(); i++ {
				pair := n.NamedChild(i)
				if pair.Kind() != "pair" || strings.Trim(pair.ChildByFieldName("key").Utf8Text(b), `'"`) != "rules" {
					continue
				}
				if obj := pair.ChildByFieldName("value"); obj != nil && obj.Kind() == "object" {
					for j := uint(0); j < obj.NamedChildCount(); j++ {
						rp := obj.NamedChild(j)
						if rp.Kind() != "pair" {
							continue
						}
						k, v := strings.Trim(rp.ChildByFieldName("key").Utf8Text(b), `'"`), rp.ChildByFieldName("value")
						if v.Kind() == "null" {
							rules[k] = nil
						} else {
							rules[k] = true
						}
					}
					m["rules"] = rules
				}
			}
			if m["rules"] != nil || m["extends"] != nil {
				stylelintObject(s, c, m)
				return
			}
		}
		for i := uint(0); i < n.NamedChildCount(); i++ {
			walk(n.NamedChild(i))
		}
	}
	walk(tree.RootNode())
	return nil
}

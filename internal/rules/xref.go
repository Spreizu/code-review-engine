package rules

import (
	"io/fs"
	"strings"

	"gopkg.in/yaml.v3"
)

// ApplyXref fills Rule.Equivalents from "tool:id" entries in each rule's xref list and from the
// shipped mapping (rules/data/xref.yaml: rules: {RULE-ID: [tool:id, ...]}).
func ApplyXref(all []*Rule, fsys fs.FS, path string) error {
	var data struct {
		Rules map[string][]string `yaml:"rules"`
	}
	if fsys != nil {
		b, err := fs.ReadFile(fsys, path)
		if err != nil {
			return err
		}
		if err := yaml.Unmarshal(b, &data); err != nil {
			return err
		}
	}
	for _, r := range all {
		seen := map[string]bool{}
		r.Equivalents = r.Equivalents[:0]
		add := func(e string) {
			if !seen[e] {
				seen[e] = true
				r.Equivalents = append(r.Equivalents, e)
			}
		}
		for _, x := range r.Xref {
			if IsEquivalent(x) {
				add(x)
				if full := eslintFullKey(x); full != "" {
					add(full)
				}
			}
		}
		for _, e := range data.Rules[r.ID] {
			add(e)
			if full := eslintFullKey(e); full != "" {
				add(full)
			}
		}
	}
	return nil
}

// eslintPluginPrefix is the rule-key prefix ESLint configs and disable comments use per plugin family.
var eslintPluginPrefix = map[string]string{
	"typescript-eslint": "@typescript-eslint/",
	"eslint-plugin-vue": "vue/",
	"graphql-eslint":    "@graphql-eslint/",
	"react-hooks":       "react-hooks/",
	"angular-eslint":    "@angular-eslint/",
	"react":             "react/",
}

// eslintFullKey turns a short plugin xref ("typescript-eslint:no-explicit-any") into the key that
// .eslintrc and eslint-disable comments use ("typescript-eslint:@typescript-eslint/no-explicit-any"),
// so project config and inline disables match either spelling. "" when already full or not a plugin.
func eslintFullKey(x string) string {
	tool, id, _ := strings.Cut(x, ":")
	p, ok := eslintPluginPrefix[tool]
	if !ok || strings.HasPrefix(id, p) {
		return ""
	}
	return tool + ":" + p + id
}

// IsEquivalent reports whether an xref entry is a "tool:id" linter reference (not a URL).
func IsEquivalent(x string) bool {
	tool, id, ok := strings.Cut(x, ":")
	return ok && id != "" && !strings.HasPrefix(id, "//") && tool != "" && !strings.ContainsAny(tool, "/ .")
}

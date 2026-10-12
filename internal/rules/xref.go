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
			}
		}
		for _, e := range data.Rules[r.ID] {
			add(e)
		}
	}
	return nil
}

// IsEquivalent reports whether an xref entry is a "tool:id" linter reference (not a URL).
func IsEquivalent(x string) bool {
	tool, id, ok := strings.Cut(x, ":")
	return ok && id != "" && !strings.HasPrefix(id, "//") && tool != "" && !strings.ContainsAny(tool, "/ .")
}

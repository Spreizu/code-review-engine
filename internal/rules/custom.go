package rules

import (
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"slices"
	"strings"

	"gopkg.in/yaml.v3"
)

// User-maintained rules (default dir .crev/rules/, configurable via `custom_rules` in .crev.yaml).
//
// Each *.yaml / *.yml file uses the rule-pack layout (`pack` and `pack_version` optional, default
// pack "custom"). Per entry, keyed by `id`:
//
//   - id not built in                        -> new rule (must be complete, same schema as built-ins)
//   - id built in, no `override` key        -> patch: the given fields are deep-merged onto the
//     built-in (maps merge recursively, scalars and lists replace)
//   - id built in, `override: replace`       -> the entry replaces the built-in entirely
//   - id built in, `disabled: true`          -> the built-in is removed
//
// Later files (lexical order) win over earlier ones; an id may appear only once per file.

// Change records what a user file did to the catalog (for `crev rules validate` / `rules list`).
type Change struct {
	ID     string `json:"id"`
	Action string `json:"action"` // add | patch | replace | disable
	File   string `json:"file"`
	Base   string `json:"base,omitempty"` // built-in pack file that was changed
}

// CustomFiles expands dirs (recursive *.yaml|*.yml) and globs; missing paths are ignored.
func CustomFiles(paths ...string) ([]string, error) {
	var out []string
	seen := map[string]bool{}
	add := func(p string) {
		if !seen[p] {
			seen[p] = true
			out = append(out, p)
		}
	}
	for _, p := range paths {
		if p == "" {
			continue
		}
		st, err := os.Stat(p)
		switch {
		case err == nil && st.IsDir():
			err := filepath.WalkDir(p, func(f string, d fs.DirEntry, err error) error {
				if err != nil {
					return err
				}
				if !d.IsDir() && (strings.HasSuffix(f, ".yaml") || strings.HasSuffix(f, ".yml")) {
					add(f)
				}
				return nil
			})
			if err != nil {
				return nil, err
			}
		case err == nil:
			add(p)
		default:
			m, gerr := filepath.Glob(p)
			if gerr != nil {
				return nil, gerr
			}
			for _, f := range m {
				add(f)
			}
		}
	}
	slices.Sort(out)
	return out, nil
}

// ApplyCustom applies user rule files to the built-in rules and returns the effective set.
func ApplyCustom(builtin []*Rule, files []string) ([]*Rule, []Change, error) {
	idx := map[string]int{}
	eff := make([]*Rule, 0, len(builtin))
	for _, r := range builtin {
		idx[r.ID] = len(eff)
		eff = append(eff, r)
	}
	isBuiltin := map[string]bool{}
	for _, r := range builtin {
		isBuiltin[r.ID] = true
	}
	var changes []Change
	for _, f := range files {
		b, err := os.ReadFile(f)
		if err != nil {
			return nil, nil, err
		}
		var doc struct {
			Pack        string           `yaml:"pack"`
			PackVersion string           `yaml:"pack_version"`
			Rules       []map[string]any `yaml:"rules"`
		}
		if err := yaml.Unmarshal(b, &doc); err != nil {
			return nil, nil, fmt.Errorf("%s: %w", f, err)
		}
		if doc.Pack == "" {
			doc.Pack = "custom"
		}
		if doc.PackVersion == "" {
			doc.PackVersion = "local"
		}
		inFile := map[string]bool{}
		for n, raw := range doc.Rules {
			id, _ := raw["id"].(string)
			if id == "" {
				return nil, nil, fmt.Errorf("%s: rules[%d]: id required", f, n)
			}
			if inFile[id] {
				return nil, nil, fmt.Errorf("%s: duplicate rule id %s", f, id)
			}
			inFile[id] = true
			mode, _ := raw["override"].(string)
			delete(raw, "override")
			disabled, _ := raw["disabled"].(bool)
			delete(raw, "disabled")
			i, exists := idx[id]
			switch {
			case disabled:
				if !exists {
					return nil, nil, fmt.Errorf("%s: %s: disabled: true but no such rule", f, id)
				}
				changes = append(changes, Change{ID: id, Action: "disable", File: f, Base: eff[i].File})
				eff[i] = nil
				delete(idx, id)
			case exists && mode != "replace":
				if mode != "" && mode != "patch" {
					return nil, nil, fmt.Errorf("%s: %s: override must be patch or replace, got %q", f, id, mode)
				}
				r, err := patchRule(eff[i], raw)
				if err != nil {
					return nil, nil, fmt.Errorf("%s: %s: %w", f, id, err)
				}
				r.Origin, r.BaseFile = "custom", eff[i].File
				if eff[i].BaseFile != "" {
					r.BaseFile = eff[i].BaseFile
				}
				r.File = f
				changes = append(changes, Change{ID: id, Action: "patch", File: f, Base: r.BaseFile})
				eff[i] = r
			default:
				if mode == "replace" && !exists {
					if isBuiltin[id] {
						return nil, nil, fmt.Errorf("%s: %s: override: replace of a disabled rule", f, id)
					}
					return nil, nil, fmt.Errorf("%s: %s: override: replace but no built-in rule with this id", f, id)
				}
				r, err := decodeRule(raw)
				if err != nil {
					return nil, nil, fmt.Errorf("%s: %s: %w", f, id, err)
				}
				r.Pack, r.PackVersion, r.File, r.Origin = doc.Pack, doc.PackVersion, f, "custom"
				if r.RuleVersion == 0 {
					r.RuleVersion = 1
				}
				if exists {
					r.BaseFile = eff[i].File
					if eff[i].BaseFile != "" {
						r.BaseFile = eff[i].BaseFile
					}
					changes = append(changes, Change{ID: id, Action: "replace", File: f, Base: r.BaseFile})
					eff[i] = r
				} else {
					changes = append(changes, Change{ID: id, Action: "add", File: f})
					idx[id] = len(eff)
					eff = append(eff, r)
				}
			}
		}
	}
	out := eff[:0]
	for _, r := range eff {
		if r != nil {
			out = append(out, r)
		}
	}
	return out, changes, nil
}

func decodeRule(raw map[string]any) (*Rule, error) {
	b, err := yaml.Marshal(raw)
	if err != nil {
		return nil, err
	}
	var r Rule
	dec := yaml.NewDecoder(strings.NewReader(string(b)))
	dec.KnownFields(true)
	if err := dec.Decode(&r); err != nil {
		return nil, err
	}
	return &r, nil
}

func patchRule(base *Rule, patch map[string]any) (*Rule, error) {
	b, err := yaml.Marshal(base)
	if err != nil {
		return nil, err
	}
	var m map[string]any
	if err := yaml.Unmarshal(b, &m); err != nil {
		return nil, err
	}
	merge(m, patch)
	r, err := decodeRule(m)
	if err != nil {
		return nil, err
	}
	r.Pack, r.PackVersion = base.Pack, base.PackVersion
	return r, nil
}

func merge(dst, src map[string]any) {
	for k, v := range src {
		if sm, ok := v.(map[string]any); ok {
			if dm, ok := dst[k].(map[string]any); ok {
				merge(dm, sm)
				continue
			}
		}
		dst[k] = v
	}
}

package projcfg

import (
	_ "embed"
	"encoding/json"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"sync"
)

// Oxlint (.oxlintrc.json / .oxlintrc.jsonc / oxlint.json): categories, rules (with plugin
// prefixes), plugins, overrides, extends and ignorePatterns. Every configured oxlint rule yields
// two directives: tool "oxlint" with id "<plugin>/<rule>" (xref oxlint:<plugin>/<rule>) and the
// equivalent ESLint-family directive (eslint:no-console, typescript-eslint:@typescript-eslint/x,
// eslint-plugin-vue:vue/x, react-hooks:react-hooks/x, ...), so crev rules mapped to ESLint
// equivalents follow an oxlint-only project too. Docs: https://oxc.rs/docs/guide/usage/linter/config.html

func init() {
	register(oxlintConfig, ".oxlintrc.json", ".oxlintrc.jsonc", "oxlint.json")
}

//go:embed oxlint_rules.json
var oxlintRulesJSON []byte

var (
	oxlintOnce  sync.Once
	oxlintRules map[string]string // "<plugin>/<rule>" -> category
)

func oxlintTable() map[string]string {
	oxlintOnce.Do(func() {
		var t struct {
			Rules map[string]string `json:"rules"`
		}
		_ = json.Unmarshal(oxlintRulesJSON, &t)
		oxlintRules = t.Rules
	})
	return oxlintRules
}

// oxlintDefaultPlugins: plugins enabled when the config has no "plugins" key.
var oxlintDefaultPlugins = []string{"eslint", "typescript", "unicorn", "oxc"}

// oxlintPluginAlias maps config prefixes (and ESLint plugin names) to oxlint's plugin names.
var oxlintPluginAlias = map[string]string{
	"eslint": "eslint", "typescript": "typescript", "@typescript-eslint": "typescript", "unicorn": "unicorn",
	"react": "react", "react-hooks": "react", "react-refresh": "react", "react-perf": "react-perf", "jsx-a11y": "jsx-a11y",
	"import": "import", "import-x": "import", "vue": "vue", "jest": "jest", "vitest": "vitest", "nextjs": "nextjs",
	"@next/next": "nextjs", "next": "nextjs", "promise": "promise", "n": "node", "node": "node", "oxc": "oxc", "jsdoc": "jsdoc",
	"deepscan": "oxc",
}

// OxlintKey normalises an oxlint rule key ("no-console", "eslint/no-console",
// "@typescript-eslint/no-explicit-any", "react-hooks/exhaustive-deps", "n/no-sync") to
// "<plugin>/<rule>" in oxlint's own naming.
func OxlintKey(k string) string {
	i := strings.LastIndexByte(k, '/')
	if i < 0 {
		return "eslint/" + k
	}
	p, r := k[:i], k[i+1:]
	if a, ok := oxlintPluginAlias[p]; ok {
		p = a
	}
	return p + "/" + r
}

// oxlintFamily returns the ESLint-family equivalent (tool, id) of an oxlint "<plugin>/<rule>".
func oxlintFamily(key string) (tool, id string) {
	p, r, _ := strings.Cut(key, "/")
	switch p {
	case "eslint":
		return "eslint", r
	case "typescript":
		return "typescript-eslint", "@typescript-eslint/" + r
	case "vue":
		return "eslint-plugin-vue", "vue/" + r
	case "react":
		if r == "exhaustive-deps" || r == "rules-of-hooks" {
			return "react-hooks", "react-hooks/" + r
		}
		return "react", "react/" + r
	case "nextjs":
		return "nextjs", "@next/next/" + r
	case "node":
		return "node", "n/" + r
	}
	return p, p + "/" + r
}

// oxlintSeverity: "off"/"allow"/0 off; "warn"/1, "error"/"deny"/2 on; [severity, options].
func oxlintSeverity(v any) (off bool, params map[string]any, ok bool) {
	switch x := v.(type) {
	case string:
		switch strings.ToLower(x) {
		case "allow":
			return true, nil, true
		case "deny":
			return false, nil, true
		}
	case []any:
		if len(x) > 0 {
			if s, isStr := x[0].(string); isStr && (strings.EqualFold(s, "allow") || strings.EqualFold(s, "deny")) {
				x = append([]any{map[bool]string{true: "off", false: "error"}[strings.EqualFold(s, "allow")]}, x[1:]...)
			}
			return eslintSeverity(x)
		}
	}
	return eslintSeverity(v)
}

type oxlintLayer struct {
	plugins    []string // nil = unchanged
	categories map[string]any
	rules      map[string]any
	ignores    []string
	overrides  []map[string]any
}

// oxlintLoad reads a config and its extends chain (paths relative to the declaring file; later
// entries override earlier ones, the file itself last).
func oxlintLoad(root, rel string, b []byte, seen map[string]bool) []oxlintLayer {
	if seen[rel] || len(seen) > 20 {
		return nil
	}
	seen[rel] = true
	m, err := loose(b)
	if err != nil {
		return nil
	}
	var out []oxlintLayer
	for _, e := range strList(m["extends"]) {
		if !strings.HasPrefix(e, ".") && !strings.HasPrefix(e, "/") {
			continue // package configs are only supported by oxlint.config.ts
		}
		p := filepath.ToSlash(filepath.Clean(filepath.Join(filepath.Dir(rel), e)))
		if eb, err := os.ReadFile(filepath.Join(root, p)); err == nil {
			out = append(out, oxlintLoad(root, p, eb, seen)...)
		}
	}
	l := oxlintLayer{ignores: strList(m["ignorePatterns"])}
	if _, ok := m["plugins"]; ok {
		l.plugins = append([]string{}, strList(m["plugins"])...)
	}
	l.categories, _ = m["categories"].(map[string]any)
	l.rules, _ = m["rules"].(map[string]any)
	if ovs, ok := m["overrides"].([]any); ok {
		for _, o := range ovs {
			if om, ok := o.(map[string]any); ok {
				l.overrides = append(l.overrides, om)
			}
		}
	}
	return append(out, l)
}

func oxlintConfig(s *Set, c ctx, b []byte) error {
	layers := oxlintLoad(c.root, c.rel, b, map[string]bool{})
	if len(layers) == 0 {
		_, err := loose(b)
		return err
	}
	plugins := slices.Clone(oxlintDefaultPlugins)
	cats := map[string]any{"correctness": "warn"} // oxlint enables correctness by default
	var ignores []string
	for _, l := range layers {
		if l.plugins != nil {
			plugins = append([]string{"eslint"}, l.plugins...) // eslint core rules are always available
			for i, p := range plugins {
				if a, ok := oxlintPluginAlias[p]; ok {
					plugins[i] = a
				}
			}
		}
		for k, v := range l.categories {
			cats[k] = v
		}
		ignores = append(ignores, l.ignores...)
	}
	emit := func(key string, off bool, params map[string]any, files []string) {
		d := c.d("oxlint", key, off)
		d.Params, d.Files, d.Ignore = params, files, ignores
		s.add(d)
		tool, id := oxlintFamily(key)
		f := c.d(tool, id, off)
		f.Params, f.Files, f.Ignore = params, files, ignores
		s.add(f)
	}
	// 1. categories (lowest precedence), restricted to enabled plugins
	table := oxlintTable()
	keys := make([]string, 0, len(table))
	for k := range table {
		keys = append(keys, k)
	}
	slices.Sort(keys)
	for _, k := range keys {
		p, _, _ := strings.Cut(k, "/")
		v, ok := cats[table[k]]
		if !ok || !slices.Contains(plugins, p) {
			continue
		}
		if off, _, ok := oxlintSeverity(v); ok {
			emit(k, off, nil, nil)
		}
	}
	// 2. rules, file by file of the extends chain, then 3. overrides
	for _, l := range layers {
		for _, k := range sortedKeys(l.rules) {
			if off, params, ok := oxlintSeverity(l.rules[k]); ok {
				emit(OxlintKey(k), off, params, nil)
			}
		}
	}
	for _, l := range layers {
		for _, o := range l.overrides {
			files := strList(o["files"])
			r, _ := o["rules"].(map[string]any)
			for _, k := range sortedKeys(r) {
				if off, params, ok := oxlintSeverity(r[k]); ok {
					emit(OxlintKey(k), off, params, files)
				}
			}
		}
	}
	return nil
}

func sortedKeys(m map[string]any) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	slices.Sort(out)
	return out
}

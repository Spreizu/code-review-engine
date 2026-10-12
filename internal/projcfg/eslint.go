package projcfg

import (
	"encoding/json"
	"maps"
	"regexp"
	"strconv"
	"strings"

	ts "github.com/tree-sitter/go-tree-sitter"
	"gopkg.in/yaml.v3"

	"github.com/elmo/code-review-engine/internal/grammars"
)

func init() {
	register(eslintJS, "eslint.config.js", "eslint.config.mjs", "eslint.config.cjs", ".eslintrc.js", ".eslintrc.cjs")
	register(eslintTS, "eslint.config.ts", "eslint.config.mts", "eslint.config.cts")
	register(eslintData, ".eslintrc", ".eslintrc.json", ".eslintrc.yaml", ".eslintrc.yml")
	register(packageJSON, "package.json")
}

// eslintTool maps an ESLint rule key to the crev xref tool family (ids keep the full key).
func eslintTool(key string) string {
	switch {
	case strings.HasPrefix(key, "@typescript-eslint/"):
		return "typescript-eslint"
	case strings.HasPrefix(key, "vue/"):
		return "eslint-plugin-vue"
	case strings.HasPrefix(key, "@graphql-eslint/"):
		return "graphql-eslint"
	case strings.HasPrefix(key, "react-hooks/"):
		return "react-hooks"
	case strings.HasPrefix(key, "@angular-eslint/"):
		return "angular-eslint"
	case strings.HasPrefix(key, "react/"):
		return "react"
	}
	return "eslint"
}

// eslintSeverity decodes "off"/0, "warn"/1, "error"/2 and [severity, ...options].
func eslintSeverity(v any) (off bool, params map[string]any, ok bool) {
	switch x := v.(type) {
	case string:
		return x == "off", nil, x == "off" || x == "warn" || x == "error"
	case float64:
		return x == 0, nil, true
	case int:
		return x == 0, nil, true
	case []any:
		if len(x) == 0 {
			return false, nil, false
		}
		off, _, ok = eslintSeverity(x[0])
		if len(x) > 1 {
			params = map[string]any{}
			switch o := x[1].(type) {
			case map[string]any:
				maps.Copy(params, o)
			default:
				params["value"] = o
			}
		}
		return off, params, ok
	}
	return false, nil, false
}

func addESLintRules(s *Set, c ctx, rules map[string]any, files, ignores []string) {
	for k, v := range rules {
		off, params, ok := eslintSeverity(v)
		if !ok {
			continue
		}
		d := c.d(eslintTool(k), k, off)
		d.Params, d.Files, d.Ignore = params, files, ignores
		s.add(d)
	}
}

// eslintObject handles one legacy config object (rules + overrides[].{files,excludedFiles,rules}).
func eslintObject(s *Set, c ctx, m map[string]any) {
	if r, ok := m["rules"].(map[string]any); ok {
		addESLintRules(s, c, r, nil, nil)
	}
	if ovs, ok := m["overrides"].([]any); ok {
		for _, o := range ovs {
			om, ok := o.(map[string]any)
			if !ok {
				continue
			}
			if r, ok := om["rules"].(map[string]any); ok {
				addESLintRules(s, c, r, strList(om["files"]), strList(om["excludedFiles"]))
			}
		}
	}
}

func strList(v any) []string {
	switch x := v.(type) {
	case string:
		return []string{x}
	case []any:
		var out []string
		for _, e := range x {
			if s, ok := e.(string); ok {
				out = append(out, s)
			}
		}
		return out
	case []string:
		return x
	}
	return nil
}

// stripComments removes // and /* */ comments outside string literals (JSONC).
func stripComments(b []byte) []byte {
	out := make([]byte, 0, len(b))
	inStr := byte(0)
	for i := 0; i < len(b); i++ {
		c := b[i]
		if inStr != 0 {
			out = append(out, c)
			if c == '\\' && i+1 < len(b) {
				i++
				out = append(out, b[i])
			} else if c == inStr {
				inStr = 0
			}
			continue
		}
		switch {
		case c == '"':
			inStr = c
			out = append(out, c)
		case c == '/' && i+1 < len(b) && b[i+1] == '/':
			for i < len(b) && b[i] != '\n' {
				i++
			}
			if i < len(b) {
				out = append(out, '\n')
			}
		case c == '/' && i+1 < len(b) && b[i+1] == '*':
			end := strings.Index(string(b[i+2:]), "*/")
			if end < 0 {
				return out
			}
			i += end + 3
		default:
			out = append(out, c)
		}
	}
	return out
}

var trailingComma = regexp.MustCompile(`,(\s*[}\]])`)

// loose decodes JSON-with-comments or YAML into a generic map.
func loose(b []byte) (map[string]any, error) {
	var m map[string]any
	if err := json.Unmarshal(trailingComma.ReplaceAll(stripComments(b), []byte("$1")), &m); err == nil {
		return m, nil
	}
	if err := yaml.Unmarshal(b, &m); err != nil {
		return nil, err
	}
	return normalize(m).(map[string]any), nil
}

// normalize converts yaml.v3 values (map[string]interface{}, ints) into JSON-like shapes.
func normalize(v any) any {
	switch x := v.(type) {
	case map[string]any:
		for k, e := range x {
			x[k] = normalize(e)
		}
		return x
	case map[any]any:
		m := map[string]any{}
		for k, e := range x {
			m[toString(k)] = normalize(e)
		}
		return m
	case []any:
		for i, e := range x {
			x[i] = normalize(e)
		}
		return x
	case int:
		return float64(x)
	case int64:
		return float64(x)
	}
	return v
}

func toString(v any) string {
	switch x := v.(type) {
	case string:
		return x
	case float64:
		return strconv.FormatFloat(x, 'f', -1, 64)
	case int:
		return strconv.Itoa(x)
	case bool:
		return strconv.FormatBool(x)
	}
	return ""
}

func eslintData(s *Set, c ctx, b []byte) error {
	m, err := loose(b)
	if err != nil {
		return err
	}
	eslintObject(s, c, m)
	return nil
}

func packageJSON(s *Set, c ctx, b []byte) error {
	var m map[string]any
	if json.Unmarshal(b, &m) != nil {
		return nil // not our problem; manifest rules report broken package.json
	}
	if ec, ok := m["eslintConfig"].(map[string]any); ok {
		eslintObject(s, c, ec)
	}
	return nil
}

func eslintJS(s *Set, c ctx, b []byte) error { return eslintSource(s, c, b, "javascript") }
func eslintTS(s *Set, c ctx, b []byte) error { return eslintSource(s, c, b, "typescript") }

// eslintSource statically reads ESLint JS/TS configs (flat or legacy module.exports): every
// object literal with a `rules: {...}` property contributes, scoped by sibling `files` /
// `ignores` / `excludedFiles` string arrays. Computed or imported values are skipped.
func eslintSource(s *Set, c ctx, b []byte, lang string) error {
	p := ts.NewParser()
	defer p.Close()
	if err := p.SetLanguage(grammars.Get(lang)); err != nil {
		return err
	}
	tree := p.Parse(b, nil)
	defer tree.Close()
	var walk func(n *ts.Node)
	walk = func(n *ts.Node) {
		if n.Kind() == "object" {
			props := objectProps(n, b)
			if r, ok := props["rules"].(map[string]any); ok {
				ign := strList(props["ignores"])
				ign = append(ign, strList(props["excludedFiles"])...)
				addESLintRules(s, c, r, strList(props["files"]), ign)
			}
		}
		for i := uint(0); i < n.NamedChildCount(); i++ {
			walk(n.NamedChild(i))
		}
	}
	walk(tree.RootNode())
	return nil
}

func objectProps(n *ts.Node, src []byte) map[string]any {
	m := map[string]any{}
	for i := uint(0); i < n.NamedChildCount(); i++ {
		pair := n.NamedChild(i)
		if pair.Kind() != "pair" {
			continue
		}
		k, v := pair.ChildByFieldName("key"), pair.ChildByFieldName("value")
		if k == nil || v == nil {
			continue
		}
		key := k.Utf8Text(src)
		if k.Kind() == "string" {
			key = strings.Trim(key, `'"`)
		}
		if val := jsValue(v, src); val != nil {
			m[key] = val
		}
	}
	return m
}

func jsValue(n *ts.Node, src []byte) any {
	switch n.Kind() {
	case "string", "template_string":
		t := n.Utf8Text(src)
		if len(t) >= 2 {
			return t[1 : len(t)-1]
		}
	case "number":
		if f, err := strconv.ParseFloat(n.Utf8Text(src), 64); err == nil {
			return f
		}
	case "true":
		return true
	case "false":
		return false
	case "array":
		var out []any
		for i := uint(0); i < n.NamedChildCount(); i++ {
			if v := jsValue(n.NamedChild(i), src); v != nil {
				out = append(out, v)
			}
		}
		if out == nil {
			out = []any{}
		}
		return out
	case "object":
		return objectProps(n, src)
	case "parenthesized_expression", "as_expression", "satisfies_expression":
		if n.NamedChildCount() > 0 {
			return jsValue(n.NamedChild(0), src)
		}
	}
	return nil
}

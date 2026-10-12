package engine

import (
	"bufio"
	"bytes"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"io"
	"maps"
	"path/filepath"
	"regexp"
	"slices"
	"strings"

	"gopkg.in/yaml.v3"

	"github.com/elmo/code-review-engine/internal/rules"
)

// ConfigEntry is one flattened configuration key with its 1-based line (0 if unknown).
type ConfigEntry struct {
	Value any
	Line  int
}

// Config is a flattened config file (dotted keys).
type Config map[string]ConfigEntry

// ParseConfig flattens .properties, YAML (incl. multi-document) and JSON/JSONC files.
// Unknown formats are sniffed: "{" => JSON, "key=value" lines => properties, else YAML.
func ParseConfig(name string, src []byte) (Config, error) {
	ext := strings.ToLower(filepath.Ext(name))
	trim := bytes.TrimSpace(src)
	switch {
	case ext == ".json" || ext == ".jsonc" || (ext == "" && bytes.HasPrefix(trim, []byte("{"))) || bytes.HasPrefix(trim, []byte("{")):
		return parseJSONC(src)
	case ext == ".yml" || ext == ".yaml":
		return parseYAML(src)
	case ext == ".xml":
		return parseXML(src)
	case ext == ".properties" || ext == ".factories" || ext == "":
		return parseProperties(src), nil
	}
	if looksLikeProperties(src) {
		return parseProperties(src), nil
	}
	return parseYAML(src)
}

// parseXML flattens an XML document: an element is its dotted path of local names (a repeated
// sibling gets "#<n>", n counted from 2), an attribute is "<element path>.@<local name>" (namespace
// prefixes dropped: android:exported -> @exported), and the element key itself holds its text plus
// a space-separated "name=value" list of its attributes, so a rule can test several attributes of
// one element with a regex. Lines are the element's start line.
func parseXML(src []byte) (Config, error) {
	c := Config{}
	d := xml.NewDecoder(bytes.NewReader(src))
	d.Strict = false
	type frame struct {
		path  string
		kids  map[string]int
		attrs string
		line  int
		text  strings.Builder
	}
	var stack []*frame
	start := 1 // line where the next token begins (= where the previous one ended)
	for {
		tok, err := d.Token()
		if err == io.EOF {
			break
		}
		if err != nil {
			return c, err
		}
		line := start
		start, _ = d.InputPos()
		switch t := tok.(type) {
		case xml.StartElement:
			name := t.Name.Local
			path := name
			if len(stack) > 0 {
				p := stack[len(stack)-1]
				p.kids[name]++
				if n := p.kids[name]; n > 1 {
					name = fmt.Sprintf("%s#%d", name, n)
				}
				path = p.path + "." + name
			}
			var attrs []string
			for _, a := range t.Attr {
				if a.Name.Space == "xmlns" || a.Name.Local == "xmlns" {
					continue
				}
				c[path+".@"+a.Name.Local] = ConfigEntry{a.Value, line}
				attrs = append(attrs, a.Name.Local+"="+a.Value)
			}
			stack = append(stack, &frame{path: path, kids: map[string]int{}, attrs: strings.Join(attrs, " "), line: line})
		case xml.CharData:
			if len(stack) > 0 {
				stack[len(stack)-1].text.Write(t)
			}
		case xml.EndElement:
			if len(stack) == 0 {
				continue
			}
			f := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			v := strings.TrimSpace(f.text.String())
			if f.attrs != "" {
				v = strings.TrimSpace(v + " " + f.attrs)
			}
			c[f.path] = ConfigEntry{v, f.line}
		}
	}
	return c, nil
}

func looksLikeProperties(src []byte) bool {
	for _, l := range strings.Split(string(src), "\n") {
		l = strings.TrimSpace(l)
		if l == "" || l[0] == '#' || l[0] == '!' {
			continue
		}
		return strings.Contains(l, "=") && !strings.Contains(strings.SplitN(l, "=", 2)[0], ":")
	}
	return true
}

func parseProperties(src []byte) Config {
	c := Config{}
	sc := bufio.NewScanner(bytes.NewReader(src))
	sc.Buffer(make([]byte, 1024*1024), 1024*1024)
	line, cont, key, val, start := 0, false, "", "", 0
	for sc.Scan() {
		line++
		l := sc.Text()
		if cont {
			val += strings.TrimSpace(strings.TrimSuffix(l, "\\"))
			cont = strings.HasSuffix(l, "\\")
			if !cont {
				c[key] = ConfigEntry{val, start}
			}
			continue
		}
		t := strings.TrimSpace(l)
		if t == "" || t[0] == '#' || t[0] == '!' {
			continue
		}
		i := strings.IndexAny(t, "=:")
		if i < 0 {
			c[t] = ConfigEntry{"", line}
			continue
		}
		key, val, start = strings.TrimSpace(t[:i]), strings.TrimSpace(t[i+1:]), line
		if v, ok := strings.CutSuffix(val, "\\"); ok {
			val, cont = v, true
			continue
		}
		c[key] = ConfigEntry{val, line}
	}
	return c
}

func parseYAML(src []byte) (Config, error) {
	c := Config{}
	dec := yaml.NewDecoder(bytes.NewReader(src))
	for {
		var n yaml.Node
		if err := dec.Decode(&n); err != nil {
			if err.Error() == "EOF" {
				break
			}
			return c, err
		}
		if len(n.Content) > 0 {
			flattenYAML("", n.Content[0], c)
		}
	}
	return c, nil
}

func flattenYAML(prefix string, n *yaml.Node, c Config) {
	switch n.Kind {
	case yaml.MappingNode:
		for i := 0; i+1 < len(n.Content); i += 2 {
			k := n.Content[i].Value
			if prefix != "" {
				k = prefix + "." + k
			}
			v := n.Content[i+1]
			if v.Kind == yaml.MappingNode {
				flattenYAML(k, v, c)
				continue
			}
			c[k] = ConfigEntry{yamlValue(v), n.Content[i].Line}
		}
	default:
		if prefix != "" {
			c[prefix] = ConfigEntry{yamlValue(n), n.Line}
		}
	}
}

func yamlValue(n *yaml.Node) any {
	switch n.Kind {
	case yaml.SequenceNode:
		var out []any
		for _, e := range n.Content {
			out = append(out, yamlValue(e))
		}
		return out
	case yaml.ScalarNode:
		return n.Value
	}
	var v any
	_ = n.Decode(&v)
	return v
}

var (
	jsoncComment  = regexp.MustCompile(`(?s)("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/`)
	trailingComma = regexp.MustCompile(`,(\s*[}\]])`)
)

// StripJSONC removes comments and trailing commas (tsconfig.json is JSONC).
func StripJSONC(src []byte) []byte {
	out := jsoncComment.ReplaceAllFunc(src, func(m []byte) []byte {
		if m[0] == '"' {
			return m
		}
		return bytes.Map(func(r rune) rune {
			if r == '\n' {
				return r
			}
			return ' '
		}, m)
	})
	return trailingComma.ReplaceAll(out, []byte("$1"))
}

func parseJSONC(src []byte) (Config, error) {
	clean := StripJSONC(src)
	var v any
	if err := json.Unmarshal(clean, &v); err != nil {
		return nil, err
	}
	c := Config{}
	lines := strings.Split(string(clean), "\n")
	var walk func(string, any)
	walk = func(p string, v any) {
		if m, ok := v.(map[string]any); ok {
			for k, e := range m {
				key := k
				if p != "" {
					key = p + "." + k
				}
				walk(key, e)
			}
			return
		}
		if p != "" {
			c[p] = ConfigEntry{v, lineOf(lines, p)}
		}
	}
	walk("", v)
	return c, nil
}

func lineOf(lines []string, key string) int {
	leaf := key[strings.LastIndex(key, ".")+1:]
	for i, l := range lines {
		if strings.Contains(l, `"`+leaf+`"`) {
			return i + 1
		}
	}
	return 0
}

// ConfigHit is a config-rule finding location.
type ConfigHit struct {
	Key   string
	Line  int
	Value string
}

func str(v any) string {
	switch x := v.(type) {
	case nil:
		return ""
	case string:
		return x
	case []any:
		var s []string
		for _, e := range x {
			s = append(s, str(e))
		}
		return strings.Join(s, ",")
	}
	return fmt.Sprint(v)
}

func eq(a any, b any, ci bool) bool {
	x, y := str(a), str(b)
	if ci {
		return strings.EqualFold(x, y)
	}
	return x == y
}

// EvalConfig evaluates a config-engine rule on a flattened config.
// Supported: key | key_prefix | key_any_of | key_re (optional unless_key, unless_value, unless_child) with op exists | absent | equals | not_equals | contains | in | matches.
func EvalConfig(r *rules.Rule, c Config) ([]ConfigHit, error) {
	spec := r.Detection.Config
	op, _ := spec["op"].(string)
	ci, _ := spec["case_insensitive"].(bool)
	val := spec["value"]
	var keys []string
	if k, ok := spec["key"].(string); ok {
		keys = []string{k}
	}
	if ks, ok := spec["key_any_of"].([]any); ok {
		for _, k := range ks {
			keys = append(keys, str(k))
		}
	}
	// unless_key: keys whose presence makes the rule not apply (e.g. "extends": the setting may
	// be inherited from the base config, so "absent" cannot be decided from this file alone).
	var unless []string
	switch u := spec["unless_key"].(type) {
	case string:
		unless = []string{u}
	case []any:
		for _, k := range u {
			unless = append(unless, str(k))
		}
	}
	for _, k := range unless {
		if _, ok := c[k]; ok {
			return nil, nil
		}
	}
	var unlessVal *regexp.Regexp
	if u, ok := spec["unless_value"].(string); ok && u != "" {
		var err error
		if unlessVal, err = regexp.Compile(u); err != nil {
			return nil, err
		}
	}
	// unless_child: regex tested against "key=value" of every entry nested under the matched key
	// (XML: child elements and their attributes), e.g. a LAUNCHER intent-filter under an activity.
	var unlessChild *regexp.Regexp
	if u, ok := spec["unless_child"].(string); ok && u != "" {
		var err error
		if unlessChild, err = regexp.Compile(u); err != nil {
			return nil, err
		}
	}
	childMatch := func(k string) bool {
		if unlessChild == nil {
			return false
		}
		for ck, ce := range c {
			if strings.HasPrefix(ck, k+".") && unlessChild.MatchString(ck+"="+str(ce.Value)) {
				return true
			}
		}
		return false
	}
	if kre, ok := spec["key_re"].(string); ok && kre != "" {
		re, err := regexp.Compile(kre)
		if err != nil {
			return nil, err
		}
		for _, k := range slices.Sorted(maps.Keys(c)) {
			if re.MatchString(k) {
				keys = append(keys, k)
			}
		}
		if len(keys) == 0 {
			if op == "absent" {
				return []ConfigHit{{Key: kre}}, nil
			}
			return nil, nil
		}
		if op == "absent" {
			return nil, nil
		}
	}
	prefix, _ := spec["key_prefix"].(string)
	if prefix != "" {
		var hits []ConfigHit
		names := slices.Sorted(maps.Keys(c))
		for _, k := range names {
			if strings.HasPrefix(k, prefix) {
				hits = append(hits, ConfigHit{k, c[k].Line, str(c[k].Value)})
			}
		}
		switch op {
		case "exists":
			return hits, nil
		case "absent":
			if len(hits) == 0 {
				return []ConfigHit{{Key: prefix + "*"}}, nil
			}
			return nil, nil
		}
		return nil, fmt.Errorf("op %q not supported with key_prefix", op)
	}
	if len(keys) == 0 {
		return nil, fmt.Errorf("config rule needs key, key_any_of, key_re or key_prefix")
	}
	var hits []ConfigHit
	for _, k := range keys {
		e, present := c[k]
		if present && unlessVal != nil && unlessVal.MatchString(str(e.Value)) {
			continue
		}
		if present && childMatch(k) {
			continue
		}
		h := ConfigHit{k, e.Line, str(e.Value)}
		switch op {
		case "exists":
			if present {
				hits = append(hits, h)
			}
		case "absent":
			if !present {
				hits = append(hits, ConfigHit{Key: k})
			}
		case "equals":
			if present && eq(e.Value, val, ci) {
				hits = append(hits, h)
			}
		case "not_equals":
			if !present || !eq(e.Value, val, ci) {
				hits = append(hits, h)
			}
		case "contains":
			if present {
				for _, part := range strings.Split(str(e.Value), ",") {
					if eq(strings.TrimSpace(part), val, ci) {
						hits = append(hits, h)
						break
					}
				}
			}
		case "in":
			if present {
				if list, ok := val.([]any); ok {
					for _, v := range list {
						if eq(e.Value, v, ci) {
							hits = append(hits, h)
							break
						}
					}
				}
			}
		case "matches":
			if present {
				re, err := regexp.Compile(str(val))
				if err != nil {
					return nil, err
				}
				if re.MatchString(str(e.Value)) {
					hits = append(hits, h)
				}
			}
		default:
			return nil, fmt.Errorf("unknown config op %q", op)
		}
	}
	return hits, nil
}

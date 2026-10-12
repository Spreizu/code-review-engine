package projcfg

import (
	"fmt"
	"strconv"
	"strings"
)

// parseTOML is a small TOML reader sufficient for linter sections of pyproject.toml/ruff.toml:
// tables, dotted/quoted keys, strings (basic, literal, multi-line), numbers, booleans, arrays
// and inline tables. Arrays of tables ([[x]]) are read as lists of maps. Dates are kept as text.
func parseTOML(src string) (map[string]any, error) {
	p := &tomlP{s: src}
	root := map[string]any{}
	cur := root
	for {
		p.skipWS(true)
		if p.eof() {
			return root, nil
		}
		switch {
		case strings.HasPrefix(p.rest(), "[["):
			p.i += 2
			keys, err := p.keys("]]")
			if err != nil {
				return nil, err
			}
			parent := walkTables(root, keys[:len(keys)-1])
			last := keys[len(keys)-1]
			arr, _ := parent[last].([]any)
			m := map[string]any{}
			parent[last] = append(arr, m)
			cur = m
		case p.peek() == '[':
			p.i++
			keys, err := p.keys("]")
			if err != nil {
				return nil, err
			}
			cur = walkTables(root, keys)
		default:
			keys, err := p.keys("=")
			if err != nil {
				return nil, err
			}
			v, err := p.value()
			if err != nil {
				return nil, err
			}
			walkTables(cur, keys[:len(keys)-1])[keys[len(keys)-1]] = v
		}
	}
}

func walkTables(m map[string]any, keys []string) map[string]any {
	for _, k := range keys {
		switch n := m[k].(type) {
		case map[string]any:
			m = n
		case []any:
			if len(n) > 0 {
				if mm, ok := n[len(n)-1].(map[string]any); ok {
					m = mm
					continue
				}
			}
			nm := map[string]any{}
			m[k] = nm
			m = nm
		default:
			nm := map[string]any{}
			m[k] = nm
			m = nm
		}
	}
	return m
}

type tomlP struct {
	s string
	i int
}

func (p *tomlP) eof() bool    { return p.i >= len(p.s) }
func (p *tomlP) peek() byte   { return p.s[p.i] }
func (p *tomlP) rest() string { return p.s[p.i:] }

func (p *tomlP) skipWS(newlines bool) {
	for !p.eof() {
		c := p.peek()
		switch {
		case c == ' ' || c == '\t' || c == '\r':
			p.i++
		case c == '\n' && newlines:
			p.i++
		case c == '#':
			for !p.eof() && p.peek() != '\n' {
				p.i++
			}
		default:
			return
		}
	}
}

// keys reads a dotted key up to the terminator (consumed).
func (p *tomlP) keys(term string) ([]string, error) {
	var out []string
	for {
		p.skipWS(false)
		if p.eof() {
			return nil, fmt.Errorf("toml: unexpected EOF in key")
		}
		var k string
		switch p.peek() {
		case '"', '\'':
			v, err := p.str()
			if err != nil {
				return nil, err
			}
			k = v
		default:
			st := p.i
			for !p.eof() && (isBare(p.peek())) {
				p.i++
			}
			k = p.s[st:p.i]
			if k == "" {
				return nil, fmt.Errorf("toml: bad key at offset %d", p.i)
			}
		}
		out = append(out, k)
		p.skipWS(false)
		if strings.HasPrefix(p.rest(), term) {
			p.i += len(term)
			return out, nil
		}
		if p.eof() || p.peek() != '.' {
			return nil, fmt.Errorf("toml: expected %q at offset %d", term, p.i)
		}
		p.i++
	}
}

func isBare(c byte) bool {
	return c == '_' || c == '-' || c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9'
}

func (p *tomlP) str() (string, error) {
	q := p.peek()
	if strings.HasPrefix(p.rest(), strings.Repeat(string(q), 3)) {
		p.i += 3
		end := strings.Index(p.rest(), strings.Repeat(string(q), 3))
		if end < 0 {
			return "", fmt.Errorf("toml: unterminated multi-line string")
		}
		v := strings.TrimPrefix(p.s[p.i:p.i+end], "\n")
		p.i += end + 3
		return v, nil
	}
	p.i++
	var b strings.Builder
	for !p.eof() {
		c := p.peek()
		if c == q {
			p.i++
			return b.String(), nil
		}
		if c == '\\' && q == '"' && p.i+1 < len(p.s) {
			p.i++
			switch e := p.peek(); e {
			case 'n':
				b.WriteByte('\n')
			case 't':
				b.WriteByte('\t')
			default:
				b.WriteByte(e)
			}
			p.i++
			continue
		}
		if c == '\n' {
			return "", fmt.Errorf("toml: newline in string")
		}
		b.WriteByte(c)
		p.i++
	}
	return "", fmt.Errorf("toml: unterminated string")
}

func (p *tomlP) value() (any, error) {
	p.skipWS(false)
	if p.eof() {
		return nil, fmt.Errorf("toml: missing value")
	}
	switch c := p.peek(); {
	case c == '"' || c == '\'':
		return p.str()
	case c == '[':
		p.i++
		arr := []any{}
		for {
			p.skipWS(true)
			if p.eof() {
				return nil, fmt.Errorf("toml: unterminated array")
			}
			if p.peek() == ']' {
				p.i++
				return arr, nil
			}
			v, err := p.value()
			if err != nil {
				return nil, err
			}
			arr = append(arr, v)
			p.skipWS(true)
			if !p.eof() && p.peek() == ',' {
				p.i++
			}
		}
	case c == '{':
		p.i++
		m := map[string]any{}
		for {
			p.skipWS(false)
			if p.eof() {
				return nil, fmt.Errorf("toml: unterminated inline table")
			}
			if p.peek() == '}' {
				p.i++
				return m, nil
			}
			keys, err := p.keys("=")
			if err != nil {
				return nil, err
			}
			v, err := p.value()
			if err != nil {
				return nil, err
			}
			walkTables(m, keys[:len(keys)-1])[keys[len(keys)-1]] = v
			p.skipWS(false)
			if !p.eof() && p.peek() == ',' {
				p.i++
			}
		}
	default:
		st := p.i
		for !p.eof() && !strings.ContainsRune(",]}\n#", rune(p.peek())) {
			p.i++
		}
		raw := strings.TrimSpace(p.s[st:p.i])
		switch raw {
		case "true":
			return true, nil
		case "false":
			return false, nil
		}
		if f, err := strconv.ParseFloat(strings.ReplaceAll(raw, "_", ""), 64); err == nil {
			return f, nil
		}
		return raw, nil
	}
}

// parseINI reads setup.cfg / tox.ini / .flake8 / .pylintrc / mypy.ini style files:
// section -> key -> value, with indented continuation lines appended.
func parseINI(src string) map[string]map[string]string {
	out := map[string]map[string]string{}
	sec, key := "", ""
	for _, line := range strings.Split(src, "\n") {
		t := strings.TrimSpace(line)
		if t == "" || strings.HasPrefix(t, "#") || strings.HasPrefix(t, ";") {
			continue
		}
		if strings.HasPrefix(t, "[") && strings.HasSuffix(t, "]") {
			sec, key = strings.ToLower(strings.TrimSpace(t[1:len(t)-1])), ""
			if out[sec] == nil {
				out[sec] = map[string]string{}
			}
			continue
		}
		if (line[0] == ' ' || line[0] == '\t') && key != "" {
			out[sec][key] += "\n" + t
			continue
		}
		if i := strings.IndexAny(t, "=:"); i > 0 {
			key = strings.ToLower(strings.TrimSpace(t[:i]))
			if out[sec] == nil {
				out[sec] = map[string]string{}
			}
			out[sec][key] = strings.TrimSpace(t[i+1:])
		}
	}
	return out
}

// splitList splits comma/newline/space separated lists, dropping inline comments.
func splitList(s string) []string {
	var out []string
	for _, line := range strings.Split(s, "\n") {
		if i := strings.Index(line, "#"); i >= 0 {
			line = line[:i]
		}
		for _, f := range strings.FieldsFunc(line, func(r rune) bool { return r == ',' || r == ' ' || r == '\t' }) {
			out = append(out, f)
		}
	}
	return out
}

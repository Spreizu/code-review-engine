package main

// oxc linter rule tests (MIT, https://github.com/oxc-project/oxc) as labelled cases: every rule
// file crates/oxc_linter/src/rules/<plugin>/<rule>.rs ends with `let pass = vec![...]` (must not
// match) and `let fail = vec![...]` (must match). The Rust source is read statically; nothing is
// compiled or executed, and the cases stay in the local corpus cache.

import (
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
)

var oxcPluginDir = map[string]string{"jsx-a11y": "jsx_a11y", "react-perf": "react_perf"}

func oxcSuite(id string) (string, bool) {
	plugin, rule, ok := strings.Cut(id, "/")
	if !ok {
		plugin, rule = "eslint", id
	}
	if d, ok := oxcPluginDir[plugin]; ok {
		plugin = d
	}
	base := filepath.Join(fxRoot, "oxc/crates/oxc_linter/src/rules", plugin, strings.ReplaceAll(rule, "-", "_"))
	for _, p := range []string{base + ".rs", filepath.Join(base, "mod.rs")} {
		if _, err := os.Stat(p); err == nil {
			return p, true
		}
	}
	return "", false
}

var (
	oxcVecRe   = regexp.MustCompile(`let\s+(?:mut\s+)?(pass|fail)\s*=\s*vec!\[`)
	oxcPathRe  = regexp.MustCompile(`PathBuf::from\("([^"]+)"\)`)
	oxcExtRe   = regexp.MustCompile(`change_rule_path_extension\("(\w+)"\)`)
	oxcRPathRe = regexp.MustCompile(`change_rule_path\("([^"]+)"\)`)
)

func oxlintCases(id string) ([]fcase, int, string) {
	p, ok := oxcSuite(id)
	if !ok {
		return nil, 0, "suite not found"
	}
	b, err := os.ReadFile(p)
	if err != nil {
		return nil, 0, err.Error()
	}
	src := string(b)
	def := "snippet.tsx" // the oxc Tester's default fixture path is a .tsx file
	if m := oxcExtRe.FindStringSubmatch(src); m != nil {
		def = "snippet." + m[1]
	} else if m := oxcRPathRe.FindStringSubmatch(src); m != nil {
		def = "snippet" + filepath.Ext(m[1])
	}
	if strings.HasSuffix(def, ".vue") {
		return nil, 0, "vue SFC suites not imported"
	}
	var cases []fcase
	skipped := 0
	rel, _ := filepath.Rel(fxRoot, p)
	for _, loc := range oxcVecRe.FindAllStringSubmatchIndex(src, -1) {
		valid := src[loc[2]:loc[3]] == "pass"
		elems := rustVecElems(src[loc[1]:])
		for i, el := range elems {
			code, ok := firstRustString(el)
			if !ok {
				skipped++
				continue
			}
			c := fcase{Code: code, File: def, Valid: valid, Origin: rel + "#" + src[loc[2]:loc[3]] + "[" + strconv.Itoa(i) + "]"}
			if m := oxcPathRe.FindStringSubmatch(el); m != nil {
				c.File = "snippet" + filepath.Ext(m[1])
			}
			if strings.HasPrefix(strings.TrimSpace(el), "(") && strings.Contains(el, "Some(") && !oxcPathRe.MatchString(el) {
				c.Env = "options" // rule options / settings crev does not model
			}
			if strings.HasSuffix(c.File, ".vue") {
				skipped++
				continue
			}
			cases = append(cases, c)
		}
	}
	if len(cases) == 0 {
		return nil, skipped, "no static cases"
	}
	return cases, skipped, ""
}

// rustVecElems splits the body of a vec![...] (starting after '[') into top-level elements.
func rustVecElems(s string) []string {
	var out []string
	depth, start := 0, 0
	for i := 0; i < len(s); i++ {
		if j, ok := skipRustLiteral(s, i); ok {
			i = j - 1
			continue
		}
		switch s[i] {
		case '/':
			if i+1 < len(s) && s[i+1] == '/' { // line comment
				for i < len(s) && s[i] != '\n' {
					i++
				}
			}
		case '(', '[', '{':
			depth++
		case ')', '}':
			depth--
		case ']':
			if depth == 0 {
				if e := strings.TrimSpace(s[start:i]); e != "" {
					out = append(out, e)
				}
				return out
			}
			depth--
		case ',':
			if depth == 0 {
				if e := strings.TrimSpace(s[start:i]); e != "" {
					out = append(out, e)
				}
				start = i + 1
			}
		}
	}
	return out
}

// skipRustLiteral returns the index after a string/char literal starting at i.
func skipRustLiteral(s string, i int) (int, bool) {
	if _, end, ok := rustString(s, i); ok {
		return end, true
	}
	return 0, false
}

func firstRustString(el string) (string, bool) {
	for i := 0; i < len(el); i++ {
		if v, _, ok := rustString(el, i); ok {
			return v, true
		}
	}
	return "", false
}

// rustString parses "..." or r#"..."# at i: value, end index.
func rustString(s string, i int) (string, int, bool) {
	if i >= len(s) {
		return "", 0, false
	}
	if s[i] == 'r' && (i == 0 || !isIdent(s[i-1])) {
		j := i + 1
		for j < len(s) && s[j] == '#' {
			j++
		}
		if j < len(s) && s[j] == '"' {
			hashes := strings.Repeat("#", j-i-1)
			end := strings.Index(s[j+1:], "\""+hashes)
			if end < 0 {
				return "", 0, false
			}
			return s[j+1 : j+1+end], j + 1 + end + 1 + len(hashes), true
		}
		return "", 0, false
	}
	if s[i] != '"' || (i > 0 && isIdent(s[i-1]) && s[i-1] != 'b') {
		return "", 0, false
	}
	var b strings.Builder
	for j := i + 1; j < len(s); j++ {
		c := s[j]
		switch c {
		case '"':
			return b.String(), j + 1, true
		case '\\':
			if j+1 >= len(s) {
				return "", 0, false
			}
			j++
			switch s[j] {
			case 'n':
				b.WriteByte('\n')
			case 't':
				b.WriteByte('\t')
			case 'r':
				b.WriteByte('\r')
			case '0':
				b.WriteByte(0)
			case '\\', '"', '\'':
				b.WriteByte(s[j])
			case '\n': // line continuation: skip leading whitespace
				for j+1 < len(s) && (s[j+1] == ' ' || s[j+1] == '\t' || s[j+1] == '\n' || s[j+1] == '\r') {
					j++
				}
			case 'u':
				if k := strings.IndexByte(s[j:], '}'); j+1 < len(s) && s[j+1] == '{' && k > 0 {
					if n, err := strconv.ParseUint(s[j+2:j+k], 16, 32); err == nil {
						b.WriteRune(rune(n))
					}
					j += k
				}
			case 'x':
				if j+2 < len(s) {
					if n, err := strconv.ParseUint(s[j+1:j+3], 16, 8); err == nil {
						b.WriteByte(byte(n))
					}
					j += 2
				}
			default:
				b.WriteByte('\\')
				b.WriteByte(s[j])
			}
		default:
			b.WriteByte(c)
		}
	}
	return "", 0, false
}

func isIdent(c byte) bool {
	return c == '_' || c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9'
}

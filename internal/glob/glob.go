// Package glob implements the path globs used across crev: "*" (no slash), "?", "**" (any depth,
// "**/" may match nothing) and "{a,b}" alternatives (as in ESLint/editorconfig globs).
package glob

import (
	"regexp"
	"strings"
	"sync"
)

var cache sync.Map

// Match reports whether the slash-separated path matches pattern (whole-string match).
func Match(pattern, path string) bool {
	v, ok := cache.Load(pattern)
	if !ok {
		v = regexp.MustCompile("^" + translate(pattern) + "$")
		cache.Store(pattern, v)
	}
	return v.(*regexp.Regexp).MatchString(path)
}

func translate(p string) string {
	var b strings.Builder
	depth := 0
	for i := 0; i < len(p); i++ {
		c := p[i]
		switch {
		case c == '*' && i+1 < len(p) && p[i+1] == '*':
			i++
			if i+1 < len(p) && p[i+1] == '/' {
				i++
				b.WriteString("(?:.*/)?")
			} else {
				b.WriteString(".*")
			}
		case c == '*':
			b.WriteString("[^/]*")
		case c == '?':
			b.WriteString("[^/]")
		case c == '{':
			depth++
			b.WriteString("(?:")
		case c == '}' && depth > 0:
			depth--
			b.WriteString(")")
		case c == ',' && depth > 0:
			b.WriteString("|")
		case c == '[':
			if j := strings.IndexByte(p[i:], ']'); j > 1 {
				cls := p[i+1 : i+j]
				if strings.HasPrefix(cls, "!") {
					cls = "^" + cls[1:]
				}
				b.WriteString("[" + strings.ReplaceAll(cls, `\`, `\\`) + "]")
				i += j
				continue
			}
			b.WriteString(`\[`)
		default:
			b.WriteString(regexp.QuoteMeta(string(c)))
		}
	}
	for ; depth > 0; depth-- {
		b.WriteString(")")
	}
	return b.String()
}

package index

import (
	"maps"
	"strings"
	"testing"
)

func TestSplitLoopHeader(t *testing.T) {
	for _, c := range []struct{ h, vars, iter string }{
		{"for i, r := range rs ", "i r", " rs "},
		{"for _, o := range c.X.ByHash[s.BodyHash] ", "_ o", " c.X.ByHash[s.BodyHash] "},
		{"for (const x of items) ", "const x", "items) "},
		{"for x in xs:", "x", "xs:"},
		{"for (String s : names) ", "String s", " names) "},
		{"foreach ($rows as $k => $v) ", "k v", "foreach ($rows"},
		{"for (int i = 0; i < n; i++) ", "int i n", ""},
	} {
		vars, iter := splitLoopHeader(c.h)
		want := map[string]bool{}
		for _, v := range strings.Fields(c.vars) {
			if !loopKw[v] {
				want[v] = true
			}
		}
		if !maps.Equal(vars, want) || iter != c.iter {
			t.Errorf("%q: vars=%v iter=%q, want %v %q", c.h, vars, iter, want, c.iter)
		}
	}
}

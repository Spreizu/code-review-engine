package glob

import "testing"

func TestMatch(t *testing.T) {
	for _, c := range []struct {
		p, s string
		want bool
	}{
		{"**/*.ts", "a/b/c.ts", true}, {"**/*.ts", "c.ts", true}, {"*.ts", "a/c.ts", false},
		{"src/**/*.{ts,tsx}", "src/x/y.tsx", true}, {"src/**/*.{ts,tsx}", "src/x/y.js", false},
		{"test/**", "test/a/b", true}, {"file?.go", "file1.go", true}, {"[ab].go", "a.go", true}, {"[!ab].go", "a.go", false},
	} {
		if got := Match(c.p, c.s); got != c.want {
			t.Errorf("Match(%q,%q)=%v", c.p, c.s, got)
		}
	}
}

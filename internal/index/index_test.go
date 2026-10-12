package index

import (
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
)

func write(t *testing.T, root string, files map[string]string) []string {
	t.Helper()
	var rels []string
	for rel, body := range files {
		p := filepath.Join(root, rel)
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
		rels = append(rels, rel)
	}
	slices.Sort(rels)
	return rels
}

var repo = map[string]string{
	"pkg/util/join.go":      "package util\n\nfunc JoinAll(xs []string) string { return \"\" }\n",
	"pkg/util/join_test.go": "package util\n\nimport \"testing\"\n\nfunc TestJoin(t *testing.T) { _ = JoinAll(nil) }\n",
	"pkg/util/strs.go": `package util

import "strings"

// Contains reports whether xs holds s.
func Contains(xs []string, s string) bool {
	for _, x := range xs {
		if x == s {
			return true
		}
	}
	return false
}

func Normalize(s string) string {
	s = strings.TrimSpace(s)
	s = strings.ToLower(s)
	return s
}

func Unused() {}
`,
	"pkg/other/norm.go": `package other

import "strings"

func Clean(v string) string {
	v = strings.TrimSpace(v)
	v = strings.ToLower(v)
	return v
}

var mu sync.Mutex

func Dedupe(a, b []string) []string {
	var out []string
	for _, x := range a {
		for _, y := range b {
			if x == y {
				out = append(out, x)
			}
		}
	}
	// limit: fine
	for _, x := range a {
		for _, y := range b {
			if x == y {
				out = append(out, x)
			}
		}
	}
	return out
}
`,
	"cmd/app/main.go": `package main

import (
	"flag"
	"example/pkg/util"
)

func main() {
	verbose := flag.Bool("verbose", false, "")
	dry := flag.Bool("dry-run", false, "")
	flag.Parse()
	_ = *verbose
	_ = util.Contains(nil, util.Normalize("x"))
	_ = other.Clean("y")
	_ = other.Dedupe(nil, nil)
}
`,
	"web/src/api.ts": `export function getUser(id: string) { return client.getUser(id) }
export function getPosts(id: string, page: number) { return client.getPosts(id, page) }
`,
	"web/src/page.ts": `import { getUser, getPosts } from './api'
getUser('a'); getPosts('a', 1)
`,
	"web/src/orphan.ts": `export const x = 1
`,
	"web/src/page.test.ts": `import { getUser } from './api'
test('x', () => getUser('a'))
`,
	"py/app/cli.py": `import argparse
p = argparse.ArgumentParser()
p.add_argument("--name")
p.add_argument("--legacy-mode", action="store_true")
args = p.parse_args()
print(args.name)
`,
}

func TestIndexAndChecks(t *testing.T) {
	root := t.TempDir()
	rels := write(t, root, repo)
	x := Build(root, rels, map[string]bool{"lodash": true})
	if x.Stats["files"] != 10 {
		t.Fatalf("files=%d", x.Stats["files"])
	}
	if got := x.ImportedBy["web/src/api.ts"]; len(got) != 2 {
		t.Fatalf("importedBy api.ts = %v", got)
	}
	var contains *Symbol
	for _, s := range x.Defs["Contains"] {
		contains = s
	}
	if contains == nil || !contains.Exported || contains.Complexity < 2 {
		t.Fatalf("Contains symbol = %+v", contains)
	}
	if n := x.Defs["Normalize"][0].BodyHash; n == "" || n != x.Defs["Clean"][0].BodyHash {
		t.Fatalf("alpha-renamed bodies should hash equal: %q vs %q", n, x.Defs["Clean"][0].BodyHash)
	}
	if d := x.Defs["getUser"]; len(d) == 0 || d[0].Delegate != "client.getUser" {
		t.Fatalf("delegate=%+v", d)
	}

	full := &Ctx{X: x}
	added := map[string]bool{"web/src/orphan.ts": true, "pkg/util/strs.go": true}
	diff := &Ctx{X: x, Diff: true, Changed: func(rel string) []Range {
		if added[rel] {
			return nil
		}
		return []Range{}
	}, Added: func(rel string) bool { return added[rel] }}

	// A diff that only edits a line inside an existing nested loop (not a loop header) is not a new loop.
	var loop Loop
	for _, l := range x.Loops {
		if l.File == "pkg/other/norm.go" && loop.Line == 0 {
			loop = l
		}
	}
	inner := &Ctx{X: x, Diff: true, Changed: func(rel string) []Range {
		if rel == "pkg/other/norm.go" {
			return []Range{{loop.InnerLine + 1, loop.InnerLine + 1}}
		}
		return []Range{}
	}, Added: func(string) bool { return false }}
	if h := Run("nested-loop-no-limit-note", inner, "pkg/other/norm.go", nil); loop.Line == 0 || len(h) != 0 {
		t.Fatalf("nested loop reported for an edit inside an unchanged loop: %+v (loop %+v)", h, loop)
	}
	header := &Ctx{X: x, Diff: true, Changed: func(rel string) []Range { return []Range{{loop.InnerLine, loop.InnerLine}} }, Added: func(string) bool { return false }}
	if h := Run("nested-loop-no-limit-note", header, "pkg/other/norm.go", nil); len(h) != 1 {
		t.Fatalf("new inner loop header not reported: %+v %+v", h, loop)
	}

	cases := []struct {
		check string
		ctx   *Ctx
		file  string
		cfg   map[string]any
		want  []string // substrings, one per expected hit
	}{
		{"unused-export", diff, "pkg/util/strs.go", nil, []string{"Unused"}},
		{"unused-export", full, "pkg/util/strs.go", nil, nil},
		{"unused-flag", full, "cmd/app/main.go", nil, []string{"--dry-run"}},
		{"unused-flag", full, "py/app/cli.py", nil, []string{"--legacy-mode"}},
		{"unused-file", diff, "web/src/orphan.ts", nil, []string{"orphan.ts"}},
		{"unused-file", diff, "web/src/api.ts", nil, nil},
		{"middle-man", full, "web/src/api.ts", nil, []string{"getUser -> client.getUser"}},
		{"middle-man", full, "pkg/util/strs.go", nil, nil},
		{"nested-loop-no-limit-note", full, "pkg/other/norm.go", nil, []string{"Nested loop over `a` and `b` compares elements, which is O(n·m)"}},
		{"limit-note-incomplete", full, "pkg/other/norm.go", nil, []string{"limit or its upgrade path"}},
		{"global-lock-no-limit-note", full, "pkg/other/norm.go", nil, []string{"package-level lock"}},
		{"duplicate-helper", full, "pkg/util/strs.go", nil, []string{"Normalize duplicates the existing helper Clean"}},
		{"duplicate-helper", full, "pkg/other/norm.go", nil, nil},
		{"helper-replacement", full, "pkg/util/strs.go", map[string]any{"names": []any{"contains"}, "api": "slices.Contains", "uses": []any{"slices."}, "requires_loop": true}, []string{"re-implements slices.Contains"}},
		{"test-missing", diff, "pkg/util/strs.go", map[string]any{"min_complexity": 2}, []string{"Contains"}},
		{"test-missing", diff, "pkg/other/norm.go", map[string]any{"min_complexity": 0, "min_lines": 1}, nil}, // untested directory
	}
	for _, tc := range cases {
		hits := Run(tc.check, tc.ctx, tc.file, tc.cfg)
		var got []string
		for _, h := range hits {
			got = append(got, h.Text)
		}
		if len(got) != len(tc.want) {
			t.Errorf("%s %s: got %q want %q", tc.check, tc.file, got, tc.want)
			continue
		}
		for i, w := range tc.want {
			if strings.Contains(strings.ToLower(got[i]), "ponytail") {
				t.Errorf("%s: user-facing text mentions ponytail: %q", tc.check, got[i])
			}
			if !strings.Contains(got[i], w) {
				t.Errorf("%s %s: hit %q lacks %q", tc.check, tc.file, got[i], w)
			}
		}
	}
}

func TestCallSitePatches(t *testing.T) {
	root := t.TempDir()
	files := map[string]string{
		"a.go": "package a\n\nfunc Load(p string) string { return p }\n",
		"b.go": "package a\n\nfunc B(p string) {\n\tif p == \"\" || len(p) == 0 {\n\t\treturn\n\t}\n\tLoad(p)\n}\n",
		"c.go": "package a\n\nfunc C(p string) {\n\tif len(p) == 0 {\n\t\treturn\n\t}\n\tLoad(p)\n}\n",
		"d.go": "package a\n\nfunc D(p string) {\n\tif len(p) == 0 {\n\t\treturn\n\t}\n\tLoad(p)\n}\n",
	}
	x := Build(root, write(t, root, files), nil)
	c := &Ctx{X: x, Diff: true, Changed: func(rel string) []Range {
		if rel == "a.go" {
			return []Range{}
		}
		return []Range{{4, 6}}
	}}
	hits := Run("call-site-patches", c, "b.go", nil)
	if len(hits) != 1 || !strings.Contains(hits[0].Text, "3 calls to Load") {
		t.Fatalf("hits=%+v", hits)
	}
	if h := Run("call-site-patches", c, "c.go", nil); len(h) != 0 {
		t.Fatalf("reported twice: %+v", h)
	}
}

func TestLanguages(t *testing.T) {
	root := t.TempDir()
	files := map[string]string{
		"A.java":   "package p;\npublic class A {\n  private final B b;\n  public A(B b) { this.b = b; }\n  public int size(String k) { return b.size(k); }\n  public void put(String k, String v) { b.put(k, v); }\n}\n",
		"K.kt":     "class K(private val m: M) {\n  fun get(k: String) = m.get(k)\n  fun put(k: String, v: String) = m.put(k, v)\n}\n",
		"u.php":    "<?php\nfunction both($a, $b) {\n  foreach ($a as $x) {\n    foreach ($b as $y) { if ($x === $y) { return $x; } }\n  }\n  return null;\n}\n",
		"m/x.py":   "def f(a, b):\n    return g(a, b)\n\ndef h(a):\n    return g2(a)\n",
		"m/use.py": "from .x import f\nfrom m.x import h\n",
	}
	x := Build(root, write(t, root, files), nil)
	full := &Ctx{X: x}
	for _, f := range []string{"A.java", "K.kt", "m/x.py"} {
		if h := Run("middle-man", full, f, nil); len(h) != 1 {
			t.Errorf("middle-man %s: %+v (symbols %+v)", f, h, x.Files[f].Symbols)
		}
	}
	if h := Run("nested-loop-no-limit-note", full, "u.php", nil); len(h) != 1 {
		t.Errorf("php nested loop: %+v", h)
	}
	if got := x.ImportedBy["m/x.py"]; len(got) != 1 {
		t.Errorf("python imports: %v", got)
	}
}

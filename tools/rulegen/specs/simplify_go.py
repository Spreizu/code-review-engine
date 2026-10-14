"""Simplification pack for Go: collapsible loops -> slices/maps/builtins (with the Go
version each needs), hand-written helpers the stdlib replaces, and repo-index checks."""
from specs._simplify import simp, index_rules, helper, loop

P = simp("SIMP-GO", "go", "Go 1.25", {"go": "*"})
SL, MP, SPEC = "https://pkg.go.dev/slices", "https://pkg.go.dev/maps", "https://go.dev/ref/spec"
G121, G123 = {"go": ">=1.21"}, {"go": ">=1.23"}

loop(P, "MAX", "Loop that is slices.Max / slices.Min", SL, "Max returns the maximal value in x",
     '(for_statement (range_clause left: (expression_list (identifier) (identifier) @x)) body: (block (statement_list . (if_statement condition: (binary_expression left: (identifier) @a operator: [">" "<"]) consequence: (block (statement_list . (assignment_statement right: (expression_list (identifier) @v)) .)) !alternative) .)) (#eq? @x @v) (#eq? @a @x)) @match',
     "func top(xs []int) int {\n\tm := xs[0]\n\tfor _, x := range xs {\n\t\tif x > m {\n\t\t\tm = x\n\t\t}\n\t}\n\treturn m\n}\n",
     "func top(xs []int) int {\n\treturn slices.Max(xs)\n}\n", "Use slices.Max / slices.Min (Go 1.21).", applies=G121)
loop(P, "INDEX", "Loop that is slices.Index", SL, "Index returns the index of the first occurrence of v in s",
     '(for_statement (range_clause left: (expression_list (identifier) @i (identifier))) body: (block (statement_list . (if_statement condition: (binary_expression operator: "==") consequence: (block (statement_list . (return_statement (expression_list (identifier) @r)) .)) !alternative) .)) (#eq? @i @r)) @match',
     "func find(s []string, x string) int {\n\tfor i, v := range s {\n\t\tif v == x {\n\t\t\treturn i\n\t\t}\n\t}\n\treturn -1\n}\n",
     "func find(s []string, x string) int {\n\treturn slices.Index(s, x)\n}\n", "Use slices.Index / slices.IndexFunc (Go 1.21).", applies=G121)
loop(P, "REVERSE", "Swap loop that is slices.Reverse", SL, "Reverse reverses the elements of the slice in place",
     '(for_statement (for_clause) body: (block (statement_list . (assignment_statement left: (expression_list (index_expression) (index_expression)) right: (expression_list (index_expression) (index_expression))) .))) @match',
     "func rev(s []int) {\n\tfor i, j := 0, len(s)-1; i < j; i, j = i+1, j-1 {\n\t\ts[i], s[j] = s[j], s[i]\n\t}\n}\n",
     "func rev(s []int) {\n\tslices.Reverse(s)\n}\n", "Use slices.Reverse (Go 1.21).", applies=G121)
loop(P, "MAPKEYS", "Loop collecting map keys", MP, "Keys returns an iterator over keys in m",
     '(for_statement (range_clause left: (expression_list . (identifier) @k .) right: (identifier) @m) body: (block (statement_list . (assignment_statement right: (expression_list (call_expression function: (identifier) @ap arguments: (argument_list (identifier) (identifier) @k2 .)))) .)) (#eq? @ap "append") (#eq? @k @k2)) @match',
     "func names(m map[string]int) []string {\n\tvar keys []string\n\tfor k := range m {\n\t\tkeys = append(keys, k)\n\t}\n\treturn keys\n}\n",
     "func names(m map[string]int) []string {\n\treturn slices.Collect(maps.Keys(m))\n}\n",
     "Use slices.Collect(maps.Keys(m)) or slices.Sorted(maps.Keys(m)) (Go 1.23).", applies=G123,
     filters=[r"type.is:m:map\[.*"],  # a slice yields indices, an iter.Seq values
     fp=["func f(s []string) []int {\n\tvar idx []int\n\tfor i := range s {\n\t\tidx = append(idx, i)\n\t}\n\treturn idx\n}\n"])

helper(P, "CONTAINS", "Hand-written contains helper", SL, "Contains reports whether v is present in s",
       ["contains", "containsString", "stringInSlice", "inSlice", "sliceContains", "containsInt", "includes", "hasItem"], "slices.Contains",
       "func containsString(xs []string, s string) bool {\n\tfor _, x := range xs {\n\t\tif x == s {\n\t\t\treturn true\n\t\t}\n\t}\n\treturn false\n}\n",
       "func hasAdmin(xs []string) bool {\n\treturn slices.Contains(xs, \"admin\")\n}\n", applies=G121, uses=["slices.Contains"])
helper(P, "REVERSE", "Hand-written reverse helper", SL, "Reverse reverses the elements of the slice in place",
       ["reverse", "reverseSlice", "reverseInts", "reverseStrings"], "slices.Reverse",
       "func reverse(s []int) {\n\tfor i, j := 0, len(s)-1; i < j; i, j = i+1, j-1 {\n\t\ts[i], s[j] = s[j], s[i]\n\t}\n}\n",
       "func flip(s []int) {\n\tslices.Reverse(s)\n}\n", applies=G121)
helper(P, "KEYS", "Hand-written map keys helper", MP, "Keys returns an iterator over keys in m",
       ["keys", "mapKeys", "getKeys", "sortedKeys", "keysOf"], "maps.Keys",
       "func sortedKeys(m map[string]int) []string {\n\tvar ks []string\n\tfor k := range m {\n\t\tks = append(ks, k)\n\t}\n\tsort.Strings(ks)\n\treturn ks\n}\n",
       "func names(m map[string]int) []string {\n\treturn slices.Sorted(maps.Keys(m))\n}\n", applies=G123, uses=["maps.Keys"],
       body_re=r"for\s+(\w+)(\s*,\s*_)?\s*:=\s*range\b[^{]*\{[^}]*append\(\w+,\s*\w+\)",
       fp=["type parser struct{ s string }\n\nfunc (p *parser) keys(term string) ([]string, error) {\n\tvar out []string\n\tfor {\n\t\tk, err := p.key()\n\t\tif err != nil {\n\t\t\treturn nil, err\n\t\t}\n\t\tout = append(out, k)\n\t\tif p.at(term) {\n\t\t\treturn out, nil\n\t\t}\n\t}\n}\n",
           "func keys(rows []Row) []string {\n\tvar out []string\n\tfor _, r := range rows {\n\t\tout = append(out, r.Key)\n\t}\n\treturn out\n}\n"])
helper(P, "MINMAX", "Hand-written min/max helper", SPEC, "The built-in functions min and max compute the smallest",
       ["min", "max", "minInt", "maxInt", "minOf", "maxOf", "imin", "imax"], "the min/max builtins",
       "func maxInt(a, b int) int {\n\tif a > b {\n\t\treturn a\n\t}\n\treturn b\n}\n", "func pick(a, b int) int {\n\treturn max(a, b)\n}\n",
       applies=G121, uses=["max(", "min("], loop=False, max_lines=8, doc="Go spec: Min and max")

D = {
    "unused-export": (SPEC, "An identifier may be exported to permit access to it from another package", "Go spec: Exported identifiers"),
    "unused-flag": ("https://pkg.go.dev/flag", "Define flags using flag.String", "package flag"),
    "middle-man": ("https://go.dev/doc/effective_go", "forwarding methods", "Effective Go: Embedding"),
    "nested-loop-no-limit-note": ("https://go.dev/doc/effective_go", "A set can be implemented as a map with value type bool", "Effective Go: Maps"),
    "limit-note-incomplete": ("https://go.dev/doc/effective_go", "A set can be implemented as a map with value type bool", "Effective Go: Maps"),
    "global-lock-no-limit-note": ("https://pkg.go.dev/sync", "A Mutex is a mutual exclusion lock", "package sync"),
    "duplicate-helper": ("https://go.dev/doc/code", "Functions, types, variables, and constants defined in one source file are visible to all other source files within the same package", "How to Write Go Code"),
    "call-site-patches": ("https://go.dev/doc/code", "Functions, types, variables, and constants defined in one source file are visible to all other source files within the same package", "How to Write Go Code"),
    "test-missing": ("https://pkg.go.dev/testing", "Package testing provides support for automated testing of Go packages", "package testing"),
}
NL = "func common(a, b []string) []string {\n\tvar out []string\n%s\tfor _, x := range a {\n\t\tfor _, y := range b {\n\t\t\tif x == y {\n\t\t\t\tout = append(out, x)\n\t\t\t}\n\t\t}\n\t}\n\treturn out\n}\n"
GUARD = "func %s(p string) {\n\tif p == \"\" {\n\t\treturn\n\t}\n\tload(p)\n}\n"
PARSE = "func classify(n int) string {\n\tif n < 0 {\n\t\treturn \"neg\"\n\t} else if n == 0 {\n\t\treturn \"zero\"\n\t}\n\tif n%2 == 0 {\n\t\treturn \"even\"\n\t}\n\tif n > 100 {\n\t\treturn \"big\"\n\t}\n\treturn \"odd\"\n}\n"
index_rules(P, {
    "unused-export": ("// file: text/slug.go\npackage text\n\nfunc Slugify(s string) string { return strings.ToLower(s) }\n",
                      "// file: text/slug.go\npackage text\n\nfunc Slugify(s string) string { return strings.ToLower(s) }\n// file: web/page.go\npackage web\n\nfunc title() string { return text.Slugify(\"A\") }\n"),
    "unused-flag": ("package main\n\nimport \"flag\"\n\nfunc main() {\n\tverbose := flag.Bool(\"verbose\", false, \"log more\")\n\tflag.Parse()\n}\n",
                    "package main\n\nimport \"flag\"\n\nfunc main() {\n\tverbose := flag.Bool(\"verbose\", false, \"log more\")\n\tflag.Parse()\n\tif *verbose {\n\t\tlog.Println(\"verbose\")\n\t}\n}\n"),
    "middle-man": ("// file: store/store.go\npackage store\n\nfunc Get(k string) string { return cache.Get(k) }\n\nfunc Put(k, v string) { cache.Put(k, v) }\n",
                   "// file: store/store.go\npackage store\n\nfunc Get(k string) string { return cache.Get(k) }\n\nfunc Put(k, v string) { cache.Put(k, strings.TrimSpace(v)) }\n"),
    "nested-loop-no-limit-note": ("package p\n\n" + NL % "", "package p\n\n" + NL % "\t// limit: a and b stay under 50 items; switch to a map set if they grow\n"),
    "limit-note-incomplete": ("package p\n\n" + NL % "\t// limit: quadratic but fine\n", "package p\n\n" + NL % "\t// limit: O(n*m), n < 100 here; switch to a map when it grows\n"),
    "global-lock-no-limit-note": ("package cache\n\nvar mu sync.Mutex\n", "package cache\n\n// limit: one lock for the whole cache, fine below ~1k req/s; shard per key beyond that\nvar mu sync.Mutex\n"),
    "duplicate-helper": ("// file: a.go\npackage p\n\nfunc normalize(s string) string {\n\ts = strings.TrimSpace(s)\n\ts = strings.ToLower(s)\n\treturn s\n}\n// file: b.go\npackage p\n\nfunc clean(v string) string {\n\tv = strings.TrimSpace(v)\n\tv = strings.ToLower(v)\n\treturn v\n}\n",
                         "// file: a.go\npackage p\n\nfunc normalize(s string) string {\n\ts = strings.TrimSpace(s)\n\ts = strings.ToLower(s)\n\treturn s\n}\n// file: b.go\npackage p\n\nfunc clean(v string) string {\n\tv = strings.TrimSpace(v)\n\tv = strings.ToUpper(v)\n\treturn v\n}\n"),
    "call-site-patches": ("// file: load.go (existing)\npackage p\n\nfunc load(p string) {}\n// file: use.go\npackage p\n\n" + GUARD % "a" + GUARD % "b" + GUARD % "c",
                          "// file: load.go (existing)\npackage p\n\nfunc load(p string) {}\n// file: use.go\npackage p\n\n" + GUARD % "a" + "func b(p string) { load(p) }\n"),
    "test-missing": ("// file: num/sign.go\npackage num\n\nfunc Sign(n int) int {\n\tif n < 0 {\n\t\treturn -1\n\t}\n\treturn 1\n}\n// file: num/sign_test.go\npackage num\n\nfunc TestSign(t *testing.T) {\n\tif Sign(-2) != -1 {\n\t\tt.Fatal()\n\t}\n}\n" + "// file: num/classify.go\npackage num\n\n" + PARSE.replace("func classify", "func Classify"), "// file: num/sign.go\npackage num\n\nfunc Sign(n int) int {\n\tif n < 0 {\n\t\treturn -1\n\t}\n\treturn 1\n}\n// file: num/sign_test.go\npackage num\n\nfunc TestSign(t *testing.T) {\n\tif Sign(-2) != -1 {\n\t\tt.Fatal()\n\t}\n}\n" + "// file: num/classify.go\npackage num\n\n" + PARSE.replace("func classify", "func Classify") + "// file: num/classify_test.go\npackage num\n\nfunc TestClassify(t *testing.T) {\n\tif Classify(2) != \"even\" {\n\t\tt.Fatal()\n\t}\n}\n"),
}, D)

RULES = P.R

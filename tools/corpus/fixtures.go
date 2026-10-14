package main

// fixtures: linter test suites as labelled data. For every crev rule with an xref to an
// external linter rule, the linter's own test cases are extracted locally (never copied into
// packs or commits) and run through crev:
//
//   - RuleTester suites (ESLint, typescript-eslint, eslint-plugin-vue, react-hooks,
//     graphql-eslint) and hadolint specs: case level, valid -> must-not-match, invalid -> must-match.
//   - ruff fixtures + snapshots, go/analysis and staticcheck `// want` testdata: line level.
//
// Cases that depend on rule options or settings are skipped: crev rules model the linter's
// default configuration.

import (
	"bufio"
	"cmp"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strconv"
	"strings"

	ts "github.com/tree-sitter/go-tree-sitter"

	"github.com/elmo/code-review-engine/internal/engine"
	"github.com/elmo/code-review-engine/internal/grammars"
	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/versions"
)

type fcase struct {
	Code   string `json:"-"`
	File   string `json:"file"` // file name to write the case as
	Valid  bool   `json:"valid"`
	Origin string `json:"origin"`          // fixture file (+ index) for triage
	Lines  []int  `json:"lines,omitempty"` // line-level: expected diagnostic lines (empty = none)
	Line   bool   `json:"line_level,omitempty"`
	Env    string `json:"env,omitempty"` // case depends on an environment crev does not model (old ecmaVersion, globals, inline directives)
	// Scope: line-level cases that label only some elements (axe fixtures): hits elsewhere are not scored.
	Scope []int `json:"scope,omitempty"`
}

type fresult struct {
	Rule        string   `json:"rule"`
	Pack        string   `json:"pack"`
	Mode        string   `json:"mode"`
	Xref        string   `json:"xref"`
	Cases       int      `json:"cases"`
	Skipped     int      `json:"skipped"`
	TP          int      `json:"tp"`
	FN          int      `json:"fn"`
	FP          int      `json:"fp"`
	TN          int      `json:"tn"`
	EnvMiss     int      `json:"env_dependent_mismatch"` // FP/FN on env-dependent cases: not scored
	FPOrigins   []string `json:"fp_origins,omitempty"`
	FPCode      []string `json:"fp_code,omitempty"` // local triage only (raw/, gitignored: third-party test code)
	FNOrigins   []string `json:"fn_origins,omitempty"`
	Unsupported string   `json:"unsupported,omitempty"`
}

func (r fresult) precision() float64 {
	if r.TP+r.FP == 0 {
		return -1
	}
	return float64(r.TP) / float64(r.TP+r.FP)
}

func (r fresult) recall() float64 {
	if r.TP+r.FN == 0 {
		return -1
	}
	return float64(r.TP) / float64(r.TP+r.FN)
}

var fxRoot = filepath.Join(dir, "cache", "fixtures-src")

func fixtures(args []string) {
	fs := flag.NewFlagSet("fixtures", flag.ExitOnError)
	label := fs.String("label", "current", "result label")
	only := fs.String("rule", "", "only this crev rule id (regex)")
	fs.Parse(args)
	rs, err := rules.LoadFS(os.DirFS("rules"), "packs/*/*.yaml")
	die(err)
	die(rules.ApplyData(rs, os.DirFS("rules")))
	latest := versions.Latest("")
	if b, err := os.ReadFile("rules/data/latest-versions.yaml"); err == nil {
		latest = versions.LatestFrom(b)
	}
	var re *regexp.Regexp
	if *only != "" {
		re = regexp.MustCompile(*only)
	}
	var out []fresult
	tmp, err := os.MkdirTemp("", "crev-fixtures-")
	die(err)
	defer os.RemoveAll(tmp)
	for _, r := range rs {
		if re != nil && !re.MatchString(r.ID) {
			continue
		}
		// The first suite with static cases scores the rule; the oxc suites (oxlint:plugin/rule)
		// are the fallback for rules no other suite covers.
		var fallback *fresult
		scored := false
		for _, x := range oxlintLast(r.Equivalents) {
			tool, id, _ := strings.Cut(x, ":")
			var cases []fcase
			var skipped int
			var why string
			if tool == "oxlint" {
				cases, skipped, why = oxlintCases(id)
			} else {
				id = id[strings.LastIndex(id, "/")+1:] // @typescript-eslint/x, vue/x, react-hooks/x
				cases, skipped, why = extract(r.ID, tool, id)
			}
			if why == "no-extractor" {
				continue
			}
			if len(cases) == 0 {
				if fallback == nil {
					fallback = &fresult{Rule: r.ID, Pack: r.Pack, Mode: r.Detection.Mode, Xref: x, Skipped: skipped, Unsupported: why}
				}
				continue
			}
			res := fresult{Rule: r.ID, Pack: r.Pack, Mode: r.Detection.Mode, Xref: x, Skipped: skipped, Unsupported: why}
			if len(cases) > 0 {
				evaluate(r, cases, filepath.Join(tmp, r.ID+"-"+tool), latest, &res)
			}
			out = append(out, res)
			scored = true
			break // one suite per rule
		}
		if !scored && fallback != nil {
			out = append(out, *fallback)
		}
	}
	d := filepath.Join(dir, "results", "fixtures-"+*label)
	os.MkdirAll(filepath.Join(d, "raw"), 0o755)
	b, _ := json.MarshalIndent(out, "", " ")
	die(os.WriteFile(filepath.Join(d, "raw", "fixtures.json"), b, 0o644))
	for i := range out {
		out[i].FPCode = nil
	}
	b, _ = json.MarshalIndent(out, "", " ")
	die(os.WriteFile(filepath.Join(d, "fixtures.json"), b, 0o644))
	die(os.WriteFile(filepath.Join(d, "report.md"), []byte(fixtureReport(out)), 0o644))
	fmt.Println(filepath.Join(d, "report.md"))
}

func fixtureReport(out []fresult) string {
	var b strings.Builder
	var tp, fp, fn, tn, n, low int
	for _, r := range out {
		tp, fp, fn, tn = tp+r.TP, fp+r.FP, fn+r.FN, tn+r.TN
		if r.Cases > 0 {
			n++
		}
		if p := r.precision(); p >= 0 && p < 0.9 {
			low++
		}
	}
	fmt.Fprintf(&b, "# Linter fixture evaluation\n\n%d rules with an equivalent linter suite evaluated (%d listed). Totals: TP %d, FP %d, FN %d, TN %d", n, len(out), tp, fp, fn, tn)
	if tp+fp > 0 {
		fmt.Fprintf(&b, ", precision %.3f", float64(tp)/float64(tp+fp))
	}
	if tp+fn > 0 {
		fmt.Fprintf(&b, ", recall %.3f", float64(tp)/float64(tp+fn))
	}
	var dtp, dfp, dlow int
	for _, r := range out {
		if r.Mode == "deterministic" {
			dtp, dfp = dtp+r.TP, dfp+r.FP
			if p := r.precision(); p >= 0 && p < 0.9 {
				dlow++
			}
		}
	}
	if dtp+dfp > 0 {
		fmt.Fprintf(&b, ". Deterministic rules (reach the review list without AI): TP %d, FP %d, precision %.3f, %d below 0.9", dtp, dfp, float64(dtp)/float64(dtp+dfp), dlow)
	}
	fmt.Fprintf(&b, ". Rules with precision < 0.9: %d.\n\nCase level for RuleTester/hadolint suites (valid = must-not-match); line level for ruff and `// want` testdata. Option-dependent cases skipped; env = FP/FN on cases written for another environment (old ecmaVersion, custom globals, script source, inline directives), not scored.\n\n", low)
	b.WriteString("| rule | mode | xref | cases | skipped | env | TP | FN | FP | TN | precision | recall | note |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
	slices.SortFunc(out, func(a, c fresult) int {
		pa, pc := a.precision(), c.precision()
		if pa != pc {
			if pa < 0 {
				return 1
			}
			if pc < 0 {
				return -1
			}
			if pa < pc {
				return -1
			}
			return 1
		}
		return strings.Compare(a.Rule, c.Rule)
	})
	f := func(v float64) string {
		if v < 0 {
			return "-"
		}
		return fmt.Sprintf("%.2f", v)
	}
	for _, r := range out {
		fmt.Fprintf(&b, "| %s | %s | %s | %d | %d | %d | %d | %d | %d | %d | %s | %s | %s |\n", r.Rule, r.Mode, r.Xref, r.Cases, r.Skipped, r.EnvMiss, r.TP, r.FN, r.FP, r.TN, f(r.precision()), f(r.recall()), r.Unsupported)
	}
	return b.String()
}

// evaluate writes every case into its own directory, scans once and scores per case/line.
func evaluate(r *rules.Rule, cases []fcase, root string, latest map[string]string, res *fresult) {
	for i, c := range cases {
		p := filepath.Join(root, fmt.Sprintf("c%04d", i), c.File)
		os.MkdirAll(filepath.Dir(p), 0o755)
		die(os.WriteFile(p, []byte(c.Code), 0o644))
	}
	rule := *r
	rule.Detection.RequiresConfig = nil // fixtures model a project that runs the linter
	rule.OptIn = false
	rule.Status = "active"
	engine.SkipFixtureData = false // linter suites keep their cases in testdata/
	rep, err := engine.Scan(engine.Options{Root: root, Rules: []*rules.Rule{&rule}, Latest: latest})
	if err != nil {
		res.Unsupported = "scan error: " + err.Error()
		return
	}
	hits := map[int]map[int]bool{} // case -> lines
	for _, f := range rep.Findings {
		if f.Status == "suppressed" {
			continue
		}
		var ci int
		if _, err := fmt.Sscanf(filepath.ToSlash(f.Location.Path), "c%04d/", &ci); err != nil {
			continue
		}
		if hits[ci] == nil {
			hits[ci] = map[int]bool{}
		}
		hits[ci][f.Location.StartLine] = true
	}
	res.Cases = len(cases)
	for i, c := range cases {
		h := hits[i]
		if c.Env != "" && !c.Line && (c.Valid == (len(h) > 0)) {
			res.EnvMiss++
			continue
		}
		if !c.Line {
			switch {
			case c.Valid && len(h) == 0:
				res.TN++
			case c.Valid:
				res.FP++
				res.FPOrigins = append(res.FPOrigins, c.Origin)
				res.FPCode = append(res.FPCode, c.Code[:min(len(c.Code), 300)])
			case len(h) > 0:
				res.TP++
			default:
				res.FN++
				res.FNOrigins = append(res.FNOrigins, c.Origin)
			}
			continue
		}
		want := map[int]bool{}
		for _, l := range c.Lines {
			want[l] = true
		}
		near := func(m map[int]bool, l int) bool { return m[l] || m[l-1] || m[l+1] }
		scope := map[int]bool{}
		for _, l := range c.Scope {
			scope[l] = true
		}
		for l := range h {
			if len(scope) > 0 && !scope[l] {
				continue // unlabelled element
			}
			if near(want, l) {
				res.TP++
			} else {
				res.FP++
				res.FPOrigins = append(res.FPOrigins, fmt.Sprintf("%s:%d", c.Origin, l))
			}
		}
		for l := range want {
			if !near(h, l) {
				res.FN++
				res.FNOrigins = append(res.FNOrigins, fmt.Sprintf("%s:%d", c.Origin, l))
			}
		}
		if len(h) == 0 && len(want) == 0 {
			res.TN++
		}
	}
	if len(res.FPOrigins) > 20 {
		res.FPOrigins = res.FPOrigins[:20]
	}
	if len(res.FPCode) > 20 {
		res.FPCode = res.FPCode[:20]
	}
	if len(res.FNOrigins) > 20 {
		res.FNOrigins = res.FNOrigins[:20]
	}
}

// extract returns labelled cases for tool:id; why is "no-extractor" for tools without one and
// a short reason when the suite was not found.
// oxlintLast orders equivalents so the oxc suites are tried after every other suite.
func oxlintLast(eq []string) []string {
	out := slices.Clone(eq)
	slices.SortStableFunc(out, func(a, b string) int {
		return cmp.Compare(b2i(strings.HasPrefix(a, "oxlint:")), b2i(strings.HasPrefix(b, "oxlint:")))
	})
	return out
}

func b2i(b bool) int {
	if b {
		return 1
	}
	return 0
}

func extract(ruleID, tool, id string) (cases []fcase, skipped int, why string) {
	if c, s, w, ok := a11yExtract(ruleID, tool, id); ok {
		return c, s, w
	}
	switch tool {
	case "eslint":
		return ruleTester(filepath.Join(fxRoot, "eslint/tests/lib/rules", id+".js"), "snippet.js")
	case "eslint-plugin-vue":
		p := filepath.Join(fxRoot, "eslint-plugin-vue/tests/lib/rules", id+".test.ts")
		if _, err := os.Stat(p); err != nil {
			p = strings.TrimSuffix(p, ".test.ts") + ".js"
		}
		return ruleTester(p, "snippet.vue")
	case "typescript-eslint":
		p := filepath.Join(fxRoot, "typescript-eslint/packages/eslint-plugin/tests/rules", id+".test.ts")
		if _, err := os.Stat(p); err != nil {
			if m, _ := filepath.Glob(filepath.Join(fxRoot, "typescript-eslint/packages/eslint-plugin/tests/rules", id, "*.test.ts")); len(m) > 0 {
				p = m[0]
			}
		}
		return ruleTester(p, "snippet.ts")
	case "react-hooks":
		f := map[string]string{"rules-of-hooks": "ESLintRulesOfHooks-test.js", "exhaustive-deps": "ESLintRuleExhaustiveDeps-test.js"}[id]
		if f == "" {
			return nil, 0, "no suite for this rule"
		}
		return ruleTester(filepath.Join(fxRoot, "react/packages/eslint-plugin-react-hooks/__tests__", f), "snippet.jsx")
	case "graphql-eslint":
		m, _ := filepath.Glob(filepath.Join(fxRoot, "graphql-eslint/packages/plugin/src/rules", id, "*.test.ts"))
		if len(m) == 0 {
			m, _ = filepath.Glob(filepath.Join(fxRoot, "graphql-eslint/packages/plugin/src/rules", id+".test.ts"))
		}
		if len(m) == 0 {
			return nil, 0, "suite not found"
		}
		return ruleTester(m[0], "snippet.graphql")
	case "hadolint":
		return hadolint(id)
	case "ruff":
		return ruff(id)
	case "govet":
		td := filepath.Join(fxRoot, "x-tools/go/analysis/passes", id, "testdata")
		if id == "modernize" {
			// one analyzer, one testdata package per sub-check: score each crev rule on its own
			sub := strings.ToLower(strings.ReplaceAll(strings.TrimPrefix(ruleID, "GO-MOD-"), "-", ""))
			sub = cmp.Or(map[string]string{"sortslicefunc": "slicessort", "stringsseq": "splitseq"}[sub], sub)
			td = filepath.Join(td, "src", sub)
			if _, err := os.Stat(td); err != nil {
				return nil, 0, "no modernize testdata for this sub-check"
			}
		}
		return goWant(td)
	case "staticcheck":
		m, _ := filepath.Glob(filepath.Join(fxRoot, "go-tools/*", strings.ToLower(id), "testdata"))
		if len(m) == 0 {
			return nil, 0, "suite not found"
		}
		return goWant(m[0])
	}
	return nil, 0, "no-extractor"
}

// ---- RuleTester (static extraction with tree-sitter; no JS is executed) ----

func ruleTester(path, file string) ([]fcase, int, string) {
	src, err := os.ReadFile(path)
	if err != nil {
		return nil, 0, "suite not found"
	}
	lang := "javascript"
	if strings.HasSuffix(path, ".ts") {
		lang = "typescript"
	}
	p := ts.NewParser()
	defer p.Close()
	p.SetLanguage(grammars.Get(lang))
	tree := p.Parse(src, nil)
	defer tree.Close()
	var cases []fcase
	skipped := 0
	rel, _ := filepath.Rel(fxRoot, path)
	baseEnv := ""
	if m := ctorEnv.FindSubmatch(src); m != nil {
		baseEnv = envOf(string(m[1]))
	}
	var walk func(n *ts.Node)
	walk = func(n *ts.Node) {
		if n.Kind() == "pair" {
			k := n.ChildByFieldName("key")
			v := n.ChildByFieldName("value")
			if k != nil && v != nil && v.Kind() == "array" {
				key := strings.Trim(k.Utf8Text(src), `"'`)
				if key == "valid" || key == "invalid" {
					for i := uint(0); i < v.NamedChildCount(); i++ {
						el := v.NamedChild(i)
						code, f, ok := caseCode(el, src, file)
						if !ok {
							skipped++
							continue
						}
						env := baseEnv
						if el.Kind() == "object" {
							if e := envOf(el.Utf8Text(src)); e != "" || strings.Contains(el.Utf8Text(src), "ecmaVersion") {
								env = e // a per-case languageOptions overrides the constructor default
							}
						}
						if directive.MatchString(code) {
							env = "inline eslint directive"
						}
						cases = append(cases, fcase{Code: code, File: f, Valid: key == "valid", Env: env,
							Origin: fmt.Sprintf("%s:%d", rel, el.StartPosition().Row+1)})
					}
					return
				}
			}
		}
		for i := uint(0); i < n.NamedChildCount(); i++ {
			walk(n.NamedChild(i))
		}
	}
	walk(tree.RootNode())
	if len(cases) == 0 && skipped == 0 {
		return nil, 0, "no static cases"
	}
	return cases, skipped, ""
}

var (
	ctorEnv   = regexp.MustCompile(`(?s)new RuleTester\((\{.*?\})\s*\)`)
	ecmaRe    = regexp.MustCompile(`ecmaVersion:\s*(\d+)`)
	directive = regexp.MustCompile(`/\*\s*(globals?|eslint-env|eslint)\s`)
)

// envOf: crev assumes a current ECMAScript, module code and no extra globals; cases written
// for another environment are not scored when crev disagrees with them.
func envOf(opts string) string {
	if m := ecmaRe.FindStringSubmatch(opts); m != nil {
		if v, _ := strconv.Atoi(m[1]); v < 2020 && v != 0 {
			return "ecmaVersion " + m[1]
		}
	}
	if strings.Contains(opts, "globals") {
		return "custom globals"
	}
	if strings.Contains(opts, `sourceType: "script"`) || strings.Contains(opts, `sourceType: 'script'`) || strings.Contains(opts, `sourceType: "commonjs"`) {
		return "script/commonjs source"
	}
	return ""
}

// caseCode resolves one valid/invalid element to source text.
func caseCode(el *ts.Node, src []byte, file string) (string, string, bool) {
	switch el.Kind() {
	case "string", "template_string":
		s, ok := jsString(el, src)
		return s, pickFile(s, file, ""), ok
	case "call_expression": // noFormat`...`, dedent`...`, normalizeIndent`...`
		if a := el.ChildByFieldName("arguments"); a != nil && a.Kind() == "template_string" {
			s, ok := jsString(a, src)
			return dedent(s), pickFile(s, file, ""), ok
		}
	case "object":
		var code, filename string
		ok := false
		for i := uint(0); i < el.NamedChildCount(); i++ {
			pr := el.NamedChild(i)
			if pr.Kind() != "pair" {
				if pr.Kind() == "spread_element" {
					return "", "", false
				}
				continue
			}
			k := strings.Trim(pr.ChildByFieldName("key").Utf8Text(src), `"'`)
			v := pr.ChildByFieldName("value")
			switch k {
			case "code":
				if v.Kind() == "call_expression" {
					if a := v.ChildByFieldName("arguments"); a != nil && a.Kind() == "template_string" {
						code, ok = jsString(a, src)
						code = dedent(code)
					}
				} else {
					code, ok = jsString(v, src)
				}
			case "filename":
				filename, _ = jsString(v, src)
			case "options", "settings", "parser", "only", "skip":
				if k != "only" {
					return "", "", false // non-default configuration
				}
			case "languageOptions", "parserOptions":
				if t := v.Utf8Text(src); strings.Contains(t, "parser:") || strings.Contains(t, "project") || strings.Contains(t, "graphQLConfig") {
					return "", "", false // custom parser / type info / schema needed
				}
			}
		}
		return code, pickFile(code, file, filename), ok
	}
	return "", "", false
}

func pickFile(code, def, filename string) string {
	if filename != "" {
		ext := filepath.Ext(filename)
		if ext != "" {
			return "snippet" + ext
		}
	}
	if def == "snippet.vue" && !strings.Contains(code, "<template") && !strings.Contains(code, "<script") {
		return "snippet.js"
	}
	return def
}

func jsString(n *ts.Node, src []byte) (string, bool) {
	t := n.Utf8Text(src)
	switch n.Kind() {
	case "template_string":
		if n.NamedChildCount() > 0 {
			for i := uint(0); i < n.NamedChildCount(); i++ {
				if n.NamedChild(i).Kind() == "template_substitution" {
					return "", false
				}
			}
		}
		return unescapeJS(t[1 : len(t)-1]), true
	case "string":
		return unescapeJS(t[1 : len(t)-1]), true
	case "binary_expression": // "a" + "b"
		l, ok1 := jsString(n.ChildByFieldName("left"), src)
		r, ok2 := jsString(n.ChildByFieldName("right"), src)
		return l + r, ok1 && ok2
	}
	return "", false
}

func unescapeJS(s string) string {
	var b strings.Builder
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c != '\\' || i+1 == len(s) {
			b.WriteByte(c)
			continue
		}
		i++
		switch s[i] {
		case 'n':
			b.WriteByte('\n')
		case 't':
			b.WriteByte('\t')
		case 'r':
			b.WriteByte('\r')
		case '\n':
		case 'u':
			if i+4 < len(s) {
				if v, err := strconv.ParseUint(s[i+1:i+5], 16, 32); err == nil {
					b.WriteRune(rune(v))
					i += 4
					continue
				}
			}
			b.WriteString(`\u`)
		default:
			b.WriteByte(s[i])
		}
	}
	return b.String()
}

func dedent(s string) string {
	lines := strings.Split(strings.TrimPrefix(s, "\n"), "\n")
	minIndent := -1
	for _, l := range lines {
		if strings.TrimSpace(l) == "" {
			continue
		}
		n := len(l) - len(strings.TrimLeft(l, " \t"))
		if minIndent < 0 || n < minIndent {
			minIndent = n
		}
	}
	for i, l := range lines {
		if len(l) >= minIndent && minIndent > 0 {
			lines[i] = l[minIndent:]
		}
	}
	return strings.Join(lines, "\n")
}

// ---- hadolint: ruleCatches / ruleCatchesNot "DLxxxx" "<dockerfile>" or Text.unlines [..] ----

var hsCase = regexp.MustCompile(`(?s)ruleCatches(Not)?\s+"(DL\d+|SC\d+)"\s+(?:"((?:[^"\\]|\\.)*)"|\$\s*Text\.unlines\s*\[(.*?)\])`)
var hsStr = regexp.MustCompile(`"((?:[^"\\]|\\.)*)"`)

func hadolint(id string) ([]fcase, int, string) {
	p := filepath.Join(fxRoot, "hadolint/test/Hadolint/Rule", id+"Spec.hs")
	b, err := os.ReadFile(p)
	if err != nil {
		return nil, 0, "suite not found"
	}
	all := strings.Count(string(b), "ruleCatches")
	var cases []fcase
	for _, m := range hsCase.FindAllStringSubmatchIndex(string(b), -1) {
		s := string(b)
		if s[m[4]:m[5]] != id {
			continue
		}
		var code string
		if m[6] >= 0 {
			code = unescapeJS(s[m[6]:m[7]])
		} else {
			var parts []string
			for _, q := range hsStr.FindAllStringSubmatch(s[m[8]:m[9]], -1) {
				parts = append(parts, unescapeJS(q[1]))
			}
			code = strings.Join(parts, "\n")
		}
		line := strings.Count(s[:m[0]], "\n") + 1
		cases = append(cases, fcase{Code: code + "\n", File: "Dockerfile", Valid: m[2] >= 0, Origin: fmt.Sprintf("hadolint/test/Hadolint/Rule/%sSpec.hs:%d", id, line)})
	}
	return cases, all - len(cases), ""
}

// ---- ruff: fixture files + insta snapshots (line level) ----

var snapLoc = regexp.MustCompile(`(?m)^\s*-->\s+(\S+?):(\d+):\d+`)
var snapOld = regexp.MustCompile(`(?m)^(\S+?\.pyi?):(\d+):\d+: ([A-Z]+\d+)`)

type ruffSnap struct{ snap, fixture string }

var ruffIndex map[string][]ruffSnap

// indexRuff maps rule code -> snapshots that contain its diagnostics (snapshot names use the
// rule's kebab name, so the code is read from the diagnostic headers).
func indexRuff() {
	ruffIndex = map[string][]ruffSnap{}
	snaps, _ := filepath.Glob(filepath.Join(fxRoot, "ruff/crates/ruff_linter/src/rules/*/snapshots/*__tests__*.snap"))
	hdr := regexp.MustCompile(`(?m)^([A-Z]+[0-9]+) `)
	for _, sp := range snaps {
		base := filepath.Base(sp)
		rest := base[strings.Index(base, "__tests__")+len("__tests__"):]
		if strings.HasPrefix(rest, "preview__") {
			continue
		}
		i := strings.Index(rest, "_")
		if i < 0 {
			continue
		}
		fix := strings.TrimSuffix(rest[i+1:], ".snap")
		if !strings.HasSuffix(fix, ".py") && !strings.HasSuffix(fix, ".pyi") {
			continue
		}
		b, err := os.ReadFile(sp)
		if err != nil || strings.Contains(string(b), "--- Linter settings ---") {
			continue
		}
		seen := map[string]bool{}
		for _, m := range hdr.FindAllStringSubmatch(string(b), -1) {
			if !seen[m[1]] {
				seen[m[1]] = true
				ruffIndex[m[1]] = append(ruffIndex[m[1]], ruffSnap{sp, fix})
			}
		}
		for _, m := range snapOld.FindAllStringSubmatch(string(b), -1) {
			if !seen[m[3]] {
				seen[m[3]] = true
				ruffIndex[m[3]] = append(ruffIndex[m[3]], ruffSnap{sp, fix})
			}
		}
	}
}

func ruff(code string) ([]fcase, int, string) {
	if ruffIndex == nil {
		indexRuff()
	}
	var cases []fcase
	for _, rs := range ruffIndex[code] {
		b, _ := os.ReadFile(rs.snap)
		linter := filepath.Base(filepath.Dir(filepath.Dir(rs.snap)))
		fp := filepath.Join(fxRoot, "ruff/crates/ruff_linter/resources/test/fixtures", linter, rs.fixture)
		src, err := os.ReadFile(fp)
		if err != nil {
			continue
		}
		var lines []int
		body := string(b)
		for _, m := range snapLoc.FindAllStringSubmatchIndex(body, -1) {
			h := strings.TrimRight(body[:m[0]], "\n")
			h = h[strings.LastIndex(h, "\n")+1:]
			if !strings.HasPrefix(strings.TrimSpace(h), code+" ") {
				continue
			}
			l, _ := strconv.Atoi(body[m[4]:m[5]])
			lines = append(lines, l)
		}
		for _, m := range snapOld.FindAllStringSubmatch(body, -1) {
			if m[3] == code {
				l, _ := strconv.Atoi(m[2])
				lines = append(lines, l)
			}
		}
		rel, _ := filepath.Rel(fxRoot, fp)
		cases = append(cases, fcase{Code: string(src), File: rs.fixture, Lines: dedupe(lines), Line: true, Origin: rel})
	}
	if len(cases) == 0 {
		return nil, 0, "suite not found"
	}
	return cases, 0, ""
}

func dedupe(l []int) []int {
	slices.Sort(l)
	return slices.Compact(l)
}

// ---- go/analysis and staticcheck testdata: `// want` lines ----

var wantOffset = regexp.MustCompile(`// want \+(\d+) `)

func goWant(td string) ([]fcase, int, string) {
	var cases []fcase
	filepath.WalkDir(td, func(p string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() || !strings.HasSuffix(p, ".go") || strings.HasSuffix(p, ".golden") {
			return nil
		}
		f, err := os.Open(p)
		if err != nil {
			return nil
		}
		defer f.Close()
		var b strings.Builder
		var lines []int
		sc := bufio.NewScanner(f)
		sc.Buffer(make([]byte, 1<<20), 1<<20)
		for n := 1; sc.Scan(); n++ {
			t := sc.Text()
			if m := wantOffset.FindStringSubmatch(t); m != nil { // "// want +3 ..." marks a later line
				off, _ := strconv.Atoi(m[1])
				lines = append(lines, n+off)
			} else if strings.Contains(t, "// want ") || strings.Contains(t, "/* want ") || strings.Contains(t, "//@ diag(") {
				lines = append(lines, n)
			}
			b.WriteString(t + "\n")
		}
		rel, _ := filepath.Rel(fxRoot, p)
		cases = append(cases, fcase{Code: b.String(), File: filepath.Base(p), Lines: lines, Line: true, Origin: rel})
		return nil
	})
	if len(cases) == 0 {
		return nil, 0, "suite not found"
	}
	return cases, 0, ""
}

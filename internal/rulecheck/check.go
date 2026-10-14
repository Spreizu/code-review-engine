// Package rulecheck validates rules: schema-level fields and execution of each rule's golden
// examples through the real engine. Shared by tools/rulecheck (catalog CI) and `crev rules validate`
// (user rules in .crev/rules/).
package rulecheck

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"

	"github.com/elmo/code-review-engine/internal/engine"
	"github.com/elmo/code-review-engine/internal/index"
	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/taint"
	"github.com/elmo/code-review-engine/internal/versions"
)

var (
	ValidSeverity = map[string]bool{"info": true, "minor": true, "major": true, "critical": true}
	ValidMode     = map[string]bool{"deterministic": true, "ai-confirm": true}
	ValidEngine   = map[string]bool{"tree-sitter": true, "manifest": true, "config": true, "index": true, "taint": true}
	ValidKind     = map[string]bool{"best-practice": true, "anti-pattern": true, "deprecation": true, "removal": true, "migration": true, "security": true, "modernization": true}
	ValidStatus   = map[string]bool{"": true, "active": true, "shadow": true, "retired": true}
	cweRe         = regexp.MustCompile(`^CWE-[1-9]\d*$`)
	// Top 10 2021/2025, API Security 2023, Mobile 2024, LLM 2025, Docker (D01..D10), Kubernetes 2022,
	// Proactive Controls 2024 and MASVS v2 control ids.
	owaspRe = regexp.MustCompile(`^(A(0[1-9]|10):(2021|2025)|API([1-9]|10):2023|M([1-9]|10):2024|LLM(0[1-9]|10):2025|D(0[1-9]|10)|K(0[1-9]|10):2022|C([1-9]|10):2024|MASVS-(STORAGE|CRYPTO|AUTH|NETWORK|PLATFORM|CODE|RESILIENCE|PRIVACY)-[1-9])$`)
	asvsRe  = regexp.MustCompile(`^V\d+(\.\d+){1,2}$`)
	// KnownConfigTools may appear in detection.requires_config.
	KnownConfigTools = map[string]bool{"yamllint": true, "editorconfig": true, "prettier": true}
	idRe             = regexp.MustCompile(`^[A-Z]+(-[A-Z0-9]+)+$`)
	rangeRe          = regexp.MustCompile(`^(\*|true|false|((>=|<=|>|<|=|\^|~)?\d[\d.]*\s*)+(\s*\|\|\s*((>=|<=|>|<|=|\^|~)?\d[\d.]*\s*)+)*)$`)
)

// Options tune Check for user rules.
type Options struct {
	// SkipExamples: do not execute examples (only compile queries); missing examples become warnings.
	SkipExamples bool
	// RequireSource: source.url/doc_version/retrieved are errors when missing (catalog: true; user rules: warning).
	RequireSource bool
}

// Result is the outcome for one rule.
type Result struct {
	Rule     *rules.Rule
	Errors   []string
	Warnings []string
}

// Check runs every validation for r.
func Check(r *rules.Rule, o Options) Result {
	res := Result{Rule: r}
	r = engine.WithParams(r, nil, "") // examples run with the params' defaults
	for _, e := range Validate(r) {
		soft := (!o.RequireSource && strings.HasPrefix(e, "source.url")) || (o.SkipExamples && strings.HasPrefix(e, "examples."))
		if soft {
			res.Warnings = append(res.Warnings, e)
		} else {
			res.Errors = append(res.Errors, e)
		}
	}
	examples := !o.SkipExamples && r.Examples.Bad != "" && r.Examples.Good != ""
	res.Errors = append(res.Errors, checkExamples(r, examples)...)
	if examples {
		res.Errors = append(res.Errors, CheckRegressions(r)...)
	}
	return res
}

// CheckRegressions runs every examples.regressions entry as a must-not-match example.
func CheckRegressions(r *rules.Rule) []string {
	var errs []string
	for i, reg := range r.Examples.Regressions {
		if reg.Path != "" && !engine.RuleAppliesToPath(r, reg.Path) {
			continue // excluded by path (e.g. test files): that is the regression guard
		}
		c := *r
		c.Examples.Good = reg.Code
		c.Examples.Regressions = nil
		for _, e := range checkExamples(&c, true) {
			if strings.Contains(e, "good") {
				label := fmt.Sprintf("regression[%d]", i)
				if reg.Note != "" {
					label += " (" + reg.Note + ")"
				}
				errs = append(errs, label+": "+strings.Replace(e, "good example", "must-not-match example", 1))
			}
		}
	}
	return errs
}

func checkExamples(r *rules.Rule, examples bool) []string {
	res := Result{}
	switch r.Detection.Engine {
	case "tree-sitter":
		if !examples {
			if _, _, err := engine.CompileQuery(r, r.Grammar()); err != nil {
				res.Errors = append(res.Errors, err.Error())
			}
			break
		}
		res.Errors = append(res.Errors, CheckQuery(r, r.Grammar())...)
		if r.Language == "javascript" && r.Detection.Grammar == "" {
			for _, e := range CheckQuery(r, "typescript") {
				res.Errors = append(res.Errors, "[typescript grammar] "+e)
			}
		}
		if r.Language == "jsx" && r.Detection.Grammar == "" {
			for _, e := range CheckQuery(r, "tsx") {
				res.Errors = append(res.Errors, "[tsx grammar] "+e)
			}
		}
	case "config":
		if examples {
			res.Errors = append(res.Errors, CheckConfig(r)...)
		}
	case "manifest":
		if examples {
			res.Errors = append(res.Errors, CheckManifest(r)...)
		}
	case "index":
		if examples {
			res.Errors = append(res.Errors, CheckIndex(r)...)
		}
	case "taint":
		if examples {
			res.Errors = append(res.Errors, CheckTaint(r, r.Grammar())...)
			if r.Language == "javascript" && r.Detection.Grammar == "" {
				for _, e := range CheckTaint(r, "typescript") {
					res.Errors = append(res.Errors, "[typescript grammar] "+e)
				}
			}
		}
	}
	return res.Errors
}

func Validate(r *rules.Rule) []string {
	var e []string
	if !idRe.MatchString(r.ID) {
		e = append(e, "bad id")
	}
	if r.Title == "" || r.Message == "" || r.Language == "" {
		e = append(e, "missing title/message/language")
	}
	if !ValidSeverity[r.Severity] {
		e = append(e, "bad severity "+r.Severity)
	}
	for _, o := range r.Overrides {
		if o.Severity != "" && !ValidSeverity[o.Severity] {
			e = append(e, "bad override severity "+o.Severity)
		}
	}
	if !ValidKind[r.Kind] {
		e = append(e, "bad kind "+r.Kind)
	}
	if !ValidMode[r.Detection.Mode] {
		e = append(e, "bad mode "+r.Detection.Mode)
	}
	if !ValidEngine[r.Detection.Engine] {
		e = append(e, "bad engine "+r.Detection.Engine)
	}
	if r.Detection.Engine == "index" && !index.ValidCheck(r.Detection.Check) {
		e = append(e, "index rule needs detection.check, one of "+strings.Join(index.Checks, ", "))
	}
	if r.Detection.Engine == "taint" {
		cls, _ := r.Detection.Config["class"].(string)
		if !slices.Contains(taint.Classes, cls) {
			e = append(e, "taint rule needs detection.config.class, one of "+strings.Join(taint.Classes, ", "))
		}
		if taint.Family(r.Grammar()) == "" {
			e = append(e, "taint engine does not support grammar "+r.Grammar())
		}
	}
	if engine.CappedCategories[r.Category] && rules.SeverityRank(r.Severity) > rules.SeverityRank(engine.MaxAdvisorySeverity) {
		e = append(e, "category "+r.Category+" is advisory: severity must be info or minor")
	}
	switch r.Precision {
	case "", "high", "medium":
	case "low":
		if r.Detection.Mode != "ai-confirm" {
			e = append(e, "precision low (known false-positive risk) requires detection.mode ai-confirm")
		}
	default:
		e = append(e, "bad precision "+r.Precision+" (high|medium|low)")
	}
	if !ValidStatus[r.Status] {
		e = append(e, "bad status "+r.Status+" (active|shadow|retired)")
	}
	if (r.Status == "shadow" || r.Status == "retired") && r.StatusReason == "" {
		e = append(e, "status "+r.Status+" needs status_reason")
	}
	for _, t := range r.Detection.RequiresConfig {
		if !KnownConfigTools[t] {
			e = append(e, "requires_config: unknown tool "+t)
		}
	}
	if r.OptIn && len(r.Equivalents) == 0 {
		e = append(e, "opt_in needs a linter equivalent (xref tool:id) the project can enable")
	}
	if r.OptIn && r.Kind == "security" {
		e = append(e, "security rules cannot be opt-in")
	}
	for _, c := range r.CWE {
		if !cweRe.MatchString(c) {
			e = append(e, "bad cwe "+c+" (CWE-<n>)")
		}
	}
	for _, c := range r.OWASP {
		if !owaspRe.MatchString(c) {
			e = append(e, "bad owasp "+c+" (A01:2021, API1:2023, M1:2024, LLM01:2025, D01, K01:2022, C1:2024, MASVS-STORAGE-1)")
		}
	}
	for _, c := range r.ASVS {
		if !asvsRe.MatchString(c) {
			e = append(e, "bad asvs "+c+" (V<chapter>.<section>[.<req>])")
		}
	}
	for _, c := range r.WCAG {
		if w, ok := rules.WCAG[c]; !ok {
			e = append(e, "bad wcag "+c+" (WCAG 2.2 success criterion id, e.g. 1.4.3)")
		} else if w.Obsolete {
			e = append(e, "wcag "+c+" is obsolete in WCAG 2.2")
		}
	}
	if r.Category == "accessibility" && len(r.WCAG) == 0 && !slices.Contains(r.Tags, "a11y-best-practice") {
		e = append(e, "accessibility rule needs wcag success criteria (or tag a11y-best-practice)")
	}
	if r.Kind == "security" && len(r.CWE) == 0 {
		e = append(e, "security rule needs cwe (and owasp) classification")
	}
	if r.Detection.Mode == "ai-confirm" && r.AIQuestion == "" {
		e = append(e, "ai-confirm rule needs ai_question")
	}
	if !strings.HasPrefix(r.Source.URL, "https://") || r.Source.DocVersion == "" || r.Source.Retrieved == "" {
		e = append(e, "source.url/doc_version/retrieved required")
	}
	if len(r.AppliesTo) == 0 {
		e = append(e, "applies_to required")
	}
	for k, v := range r.AppliesTo {
		if !rangeRe.MatchString(strings.TrimSpace(v)) {
			e = append(e, "bad range "+k+": "+v)
		}
	}
	if q := r.Detection.Query; q != "" && TopLevelPredicate(q) {
		e = append(e, "predicate at top level of the query (outside a parenthesised group) is not applied; wrap the pattern and predicate in ( ... )")
	}
	if r.Examples.Bad == "" || r.Examples.Good == "" {
		e = append(e, "examples.bad and examples.good required")
	}
	for _, x := range r.Xref {
		if !strings.HasPrefix(x, "https://") && !rules.IsEquivalent(x) && !idRe.MatchString(x) { // URL, tool:id, or a related crev rule id
			e = append(e, "xref entries must be https:// URLs, tool:id linter equivalents or crev rule ids: "+x)
		}
	}
	text := r.Title + r.Message + strings.Join(r.Detection.Filters, "\n")
	for _, m := range paramRef.FindAllStringSubmatch(text, -1) {
		if _, ok := r.Params[m[1]]; !ok && len(r.Params) > 0 && m[1] != "value" { // ${value}: the measured metric (engine) // rules without params may contain literal ${...} (Kotlin, Maven)
			e = append(e, "undeclared param ${"+m[1]+"}")
		}
	}
	for name, p := range r.Params {
		if p.Default == nil {
			e = append(e, "param "+name+" needs a default")
		}
		for _, f := range p.From {
			if i := strings.LastIndex(f, "."); i < 0 || !rules.IsEquivalent(f[:i]) {
				e = append(e, "param "+name+": from entries are tool:id.option, got "+f)
			}
		}
	}
	return e
}

// vueGlob reports whether a script-language rule targets .vue files only (its examples are SFCs).
func vueGlob(r *rules.Rule) bool {
	if len(r.Detection.Files) == 0 {
		return false
	}
	for _, f := range r.Detection.Files {
		if !strings.HasSuffix(f, ".vue") {
			return false
		}
	}
	return true
}

var paramRef = regexp.MustCompile(`\$\{([a-z_][a-z0-9_]*)\}`)

func CheckQuery(r *rules.Rule, grammar string) []string {
	if _, _, err := engine.CompileQuery(r, grammar); err != nil {
		return []string{err.Error()}
	}
	count := func(src string) (int, error) {
		b := []byte(src)
		g := grammar
		var sfc []byte
		if (r.Language == "vue" || vueGlob(r)) && r.Detection.Target != "template" && strings.Contains(src, "<script") {
			s, _, _, ok := engine.VueScript(b)
			if ok {
				sfc, b = b, s
			}
		}
		t, err := engine.Parse(g, b)
		if err != nil {
			return 0, err
		}
		t.SFC = sfc
		defer t.Close()
		h, err := engine.Run(r, t)
		return len(h), err
	}
	var e []string
	if n, err := count(r.Examples.Bad); err != nil {
		e = append(e, err.Error())
	} else if n == 0 {
		e = append(e, "bad example produced 0 matches")
	}
	if n, err := count(r.Examples.Good); err != nil {
		e = append(e, err.Error())
	} else if n != 0 {
		e = append(e, fmt.Sprintf("good example produced %d matches", n))
	}
	return e
}

// CheckTaint runs a taint rule's examples: the bad example must produce a flow of the rule's
// class, the good example none.
func CheckTaint(r *rules.Rule, grammar string) []string {
	cls, _ := r.Detection.Config["class"].(string)
	count := func(src string) (int, error) {
		t, err := engine.Parse(grammar, []byte(src))
		if err != nil {
			return 0, err
		}
		defer t.Close()
		hs, err := engine.TaintRun(t)
		n := 0
		for _, h := range hs {
			if h.Class == cls {
				n++
			}
		}
		return n, err
	}
	var e []string
	if n, err := count(r.Examples.Bad); err != nil {
		e = append(e, err.Error())
	} else if n == 0 {
		e = append(e, "bad example produced 0 matches")
	}
	if n, err := count(r.Examples.Good); err != nil {
		e = append(e, err.Error())
	} else if n != 0 {
		e = append(e, fmt.Sprintf("good example produced %d matches", n))
	}
	return e
}

func configName(r *rules.Rule) string {
	if len(r.Detection.Files) == 0 {
		return "x.properties"
	}
	f := r.Detection.Files[0]
	return filepath.Base(strings.ReplaceAll(strings.ReplaceAll(f, "**", "x"), "*", "x"))
}

func CheckConfig(r *rules.Rule) []string {
	run := func(src string) (int, error) {
		c, err := engine.ParseConfig(configName(r), []byte(src))
		if err != nil {
			return 0, err
		}
		h, err := engine.EvalConfig(r, c)
		return len(h), err
	}
	var e []string
	if n, err := run(r.Examples.Bad); err != nil {
		e = append(e, "bad: "+err.Error())
	} else if n == 0 {
		e = append(e, "bad example produced 0 config hits")
	}
	if n, err := run(r.Examples.Good); err != nil {
		e = append(e, "good: "+err.Error())
	} else if n != 0 {
		e = append(e, fmt.Sprintf("good example produced %d config hits", n))
	}
	return e
}

// checkManifest materialises an example as a project dir: "<" => pom.xml, "{" => package.json,
// "plugins {"/"dependencies {" => build.gradle(.kts), otherwise one relative path per line.
// Dimensions the example does not mention are treated as satisfying applies_to.
func CheckManifest(r *rules.Rule) []string {
	run := func(src string) (int, error) {
		dir, err := os.MkdirTemp("", "rulecheck")
		if err != nil {
			return 0, err
		}
		defer os.RemoveAll(dir)
		t := strings.TrimSpace(src)
		switch {
		case strings.HasPrefix(t, "<"):
			err = os.WriteFile(filepath.Join(dir, "pom.xml"), []byte(src), 0o644)
		case strings.HasPrefix(t, "{"):
			err = os.WriteFile(filepath.Join(dir, "package.json"), []byte(src), 0o644)
		case strings.Contains(t, "plugins {") || strings.Contains(t, "dependencies {"):
			err = os.WriteFile(filepath.Join(dir, "build.gradle.kts"), []byte(src), 0o644)
		default:
			for _, l := range strings.Split(t, "\n") {
				l = strings.TrimSpace(l)
				if l == "" || strings.HasPrefix(l, "#") {
					continue
				}
				p := filepath.Join(dir, l)
				if strings.HasSuffix(l, "/") {
					err = os.MkdirAll(p, 0o755)
				} else if err = os.MkdirAll(filepath.Dir(p), 0o755); err == nil {
					err = os.WriteFile(p, nil, 0o644)
				}
			}
		}
		if err != nil {
			return 0, err
		}
		u := versions.DetectUnit(dir)
		for k, rng := range r.AppliesTo {
			if f, ok := u.Facts[k]; ok && f.Version != "" && !versions.Satisfies(f.Version, rng) {
				return 0, nil
			}
		}
		h, err := engine.EvalManifest(r, u)
		return len(h), err
	}
	var e []string
	if n, err := run(r.Examples.Bad); err != nil {
		e = append(e, "bad: "+err.Error())
	} else if n == 0 {
		e = append(e, "bad example produced 0 manifest hits")
	}
	if n, err := run(r.Examples.Good); err != nil {
		e = append(e, "good: "+err.Error())
	} else if n != 0 {
		e = append(e, fmt.Sprintf("good example produced %d manifest hits", n))
	}
	return e
}

// topLevelPredicate reports a "(#pred? ...)" that is not nested inside a pattern group:
// tree-sitter then treats it as a separate, predicate-only pattern and the intended filter is lost.
func TopLevelPredicate(q string) bool {
	depth, inStr := 0, false
	for i := 0; i < len(q); i++ {
		c := q[i]
		switch {
		case inStr:
			if c == '\\' {
				i++
			} else if c == '"' {
				inStr = false
			}
		case c == '"':
			inStr = true
		case c == ';':
			for i < len(q) && q[i] != '\n' {
				i++
			}
		case c == '(' || c == '[':
			if c == '(' && depth == 0 && i+1 < len(q) && q[i+1] == '#' {
				return true
			}
			depth++
		case c == ')' || c == ']':
			depth--
		}
	}
	return false
}

var fileMarker = regexp.MustCompile(`^\s*(?://|#|--)\s*file:\s*(\S+)(\s+\(existing\))?\s*$`)

var defaultExampleFile = map[string]string{"go": "x.go", "python": "x.py", "javascript": "x.js", "typescript": "x.ts", "tsx": "x.tsx", "jsx": "x.jsx",
	"java": "X.java", "kotlin": "x.kt", "php": "x.php"}

// SplitFiles splits an index example into files. "// file: path" (or "# file:") lines start a new
// file; "(existing)" marks a file that is not part of the simulated diff. Without markers the
// example is one new file named after the language.
func SplitFiles(lang, src string) (files map[string]string, existing map[string]bool) {
	files, existing = map[string]string{}, map[string]bool{}
	cur := ""
	var b strings.Builder
	flush := func() {
		if cur != "" || strings.TrimSpace(b.String()) != "" {
			if cur == "" {
				cur = defaultExampleFile[lang]
				if cur == "" {
					cur = "x.txt"
				}
			}
			files[cur] += b.String()
		}
		b.Reset()
	}
	for _, l := range strings.SplitAfter(src, "\n") {
		if m := fileMarker.FindStringSubmatch(strings.TrimRight(l, "\n")); m != nil {
			flush()
			cur = m[1]
			if m[2] != "" {
				existing[cur] = true
			}
			continue
		}
		b.WriteString(l)
	}
	flush()
	return files, existing
}

// CheckIndex runs an index rule's examples as a small repo in a simulated diff where every file
// not marked "(existing)" is new.
func CheckIndex(r *rules.Rule) []string {
	run := func(src string) (int, error) {
		dir, err := os.MkdirTemp("", "rulecheck-index")
		if err != nil {
			return 0, err
		}
		defer os.RemoveAll(dir)
		files, existing := SplitFiles(r.Language, src)
		var rels []string
		for rel, body := range files {
			p := filepath.Join(dir, filepath.FromSlash(rel))
			if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
				return 0, err
			}
			if err := os.WriteFile(p, []byte(body), 0o644); err != nil {
				return 0, err
			}
			rels = append(rels, rel)
		}
		x := index.Build(dir, rels, nil)
		ctx := &index.Ctx{X: x, Diff: true,
			InScope: func(rel string, _, _ int) bool { return !existing[rel] },
			Added:   func(rel string) bool { return !existing[rel] },
			Changed: func(rel string) []index.Range {
				if existing[rel] {
					return []index.Range{}
				}
				return []index.Range{{Start: 1, End: 1 << 30}}
			}}
		n := 0
		for _, rel := range rels {
			if x.Files[rel] == nil {
				continue
			}
			n += len(index.Run(r.Detection.Check, ctx, rel, r.Detection.Config))
		}
		return n, nil
	}
	var e []string
	if n, err := run(r.Examples.Bad); err != nil {
		e = append(e, "bad: "+err.Error())
	} else if n == 0 {
		e = append(e, "bad example produced 0 index hits")
	}
	if n, err := run(r.Examples.Good); err != nil {
		e = append(e, "good: "+err.Error())
	} else if n != 0 {
		e = append(e, fmt.Sprintf("good example produced %d index hits", n))
	}
	return e
}

// ExampleErrors runs only the rule's bad/good examples (with param defaults), for harnesses that
// rewrite the examples (tools/trust metamorphic variants).
func ExampleErrors(r *rules.Rule) []string {
	return checkExamples(engine.WithParams(r, nil, ""), true)
}

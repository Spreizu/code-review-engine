package index

import (
	"cmp"
	"fmt"
	"maps"
	"path"
	"regexp"
	"slices"
	"strings"
	"sync"
)

// Hit is one index-check result.
type Hit struct {
	Line, EndLine int
	Text          string // finding message detail
	Symbol        string
	Evidence      string // index evidence (shown and sent to the AI confirmation step)
}

// Range is an inclusive changed line range.
type Range struct{ Start, End int }

// Ctx is the scan context for index checks.
type Ctx struct {
	X *Index
	// InScope, when set, decides whether a hit at rel/lines is reported (the engine passes the scan scope).
	InScope func(rel string, start, end int) bool
	// Diff is true for diff-scoped scans (--base/--staged/--working-tree/--commits).
	Diff bool
	// Changed returns the changed line ranges of rel in a diff scan (nil = whole file in scope).
	Changed func(rel string) []Range
	// Added reports whether rel is a new file in the diff.
	Added func(rel string) bool

	once     sync.Once
	patches  map[string][]Call // guard-patched callee -> sites
	changedT []string
}

func (c *Ctx) inScope(rel string, start, end int) bool {
	if c.InScope != nil {
		return c.InScope(rel, start, end)
	}
	if !c.Diff || c.Changed == nil {
		return true
	}
	rs := c.Changed(rel)
	if rs == nil {
		return c.Added != nil && c.Added(rel)
	}
	for _, r := range rs {
		if r.Start <= end && start <= r.End {
			return true
		}
	}
	return false
}

// Checks lists the index check names (detection.check).
var Checks = []string{"unused-export", "unused-flag", "unused-file", "middle-man", "nested-loop-no-limit-note", "limit-note-incomplete",
	"global-lock-no-limit-note", "duplicate-helper", "helper-replacement", "call-site-patches", "test-missing"}

// ValidCheck reports whether name is a known check.
func ValidCheck(name string) bool {
	return slices.Contains(Checks, name)
}

// Run runs check on file rel with rule configuration cfg.
func Run(check string, c *Ctx, rel string, cfg map[string]any) []Hit {
	f := c.X.Files[rel]
	if f == nil {
		return nil
	}
	switch check {
	case "unused-export":
		return unusedExport(c, rel, f, cfg)
	case "unused-flag":
		return unusedFlag(c, rel, f)
	case "unused-file":
		return unusedFile(c, rel, f)
	case "middle-man":
		return middleMan(c, rel, f, cfg)
	case "nested-loop-no-limit-note", "nested-loop-no-ponytail": // old names kept for custom rules
		return nestedLoops(c, rel)
	case "limit-note-incomplete", "ponytail-incomplete":
		return limitNoteIncomplete(c, rel)
	case "global-lock-no-limit-note", "global-lock-no-ponytail":
		return globalLocks(c, rel)
	case "duplicate-helper":
		return duplicateHelper(c, rel, f, cfg)
	case "helper-replacement":
		return helperReplacement(c, rel, f, cfg)
	case "call-site-patches":
		return callSitePatches(c, rel, cfg)
	case "test-missing":
		return testMissing(c, rel, f, cfg)
	}
	return nil
}

func cfgInt(cfg map[string]any, k string, def int) int {
	switch v := cfg[k].(type) {
	case int:
		return v
	case float64:
		return int(v)
	}
	return def
}

func cfgBool(cfg map[string]any, k string) bool { b, _ := cfg[k].(bool); return b }

func cfgStrings(cfg map[string]any, k string) []string {
	var out []string
	switch v := cfg[k].(type) {
	case []any:
		for _, x := range v {
			if s, ok := x.(string); ok {
				out = append(out, s)
			}
		}
	case []string:
		out = v
	case string:
		out = []string{v}
	}
	return out
}

// sensitive names are never simplification targets: correctness/security code is routed to
// the bug/security categories instead (the simplification layer never relaxes those).
var sensitive = regexp.MustCompile(`(?i)(auth|crypt|hash|sign|verify|token|secret|password|sanitiz|escape|valid|permission|acl|csrf|session|lock|atomic|retry|migrat)`)

// Sensitive reports whether a symbol or snippet belongs to the "not lazy about" set.
func Sensitive(s string) bool { return sensitive.MatchString(s) }

var entryName = regexp.MustCompile(`(?i)^(main|init|setup|teardown|default|handler|run|app|index|__init__|__main__|constructor|__construct|serve|middleware|config|loader|action|load|get|post|put|patch|delete|head|options|generatemetadata|generatestaticparams|getstaticprops|getserversideprops|getstaticpaths)$|^(Test|Benchmark|Example|Fuzz)`)

var entryPath = regexp.MustCompile(`(?i)(^|/)(index|main|app|server|cli|__main__|__init__|setup|manage|conftest|wsgi|asgi|settings|urls|admin|apps|migrations?/.*|.*\.config|.*\.d|vite-env\.d|middleware|instrumentation|routes?/.*|pages/.*|app/.*|bin/.*|scripts?/.*|cmd/.*|tools?/.*|examples?/.*|plugins?/.*|stories/.*|.*\.stories)\.[a-z]+$|(^|/)(pages|app|routes|api|migrations|bin|scripts|cmd)/`)

func unusedExport(c *Ctx, rel string, f *File, cfg map[string]any) []Hit {
	if (!c.Diff && !cfgBool(cfg, "full_scan")) || f.Test || f.Package == "main" || entryPath.MatchString(rel) {
		return nil
	}
	var hits []Hit
	for _, s := range f.Symbols {
		if !s.Exported || !s.TopLevel || entryName.MatchString(s.Name) || len(s.Name) < 3 || !c.inScope(rel, s.Line, s.Line) {
			continue
		}
		if s.Kind == "method" && f.Lang != "go" {
			continue // methods are reached through their type
		}
		if c.X.RefsOutside(s) > 0 {
			continue
		}
		hits = append(hits, Hit{Line: s.Line, EndLine: s.Line, Symbol: s.Name, Text: fmt.Sprintf("new exported %s %s has no references", s.Kind, s.Name),
			Evidence: fmt.Sprintf("0 references to %q in %d indexed source files (templates/configs included)", s.Name, len(c.X.Files))})
	}
	return hits
}

var (
	goFlag  = regexp.MustCompile(`(?m)^\s*(?:var\s+)?(\w+)\s*:?=\s*\w+\.(?:String|Bool|Int|Int64|Uint|Uint64|Float64|Duration|TextVar)\(\s*"([^"]+)"`)
	pyArg   = regexp.MustCompile(`add_argument\(\s*["'](--[\w-]+)["']([^)]*)\)`)
	pyDest  = regexp.MustCompile(`dest\s*=\s*["'](\w+)["']`)
	pyStore = regexp.MustCompile(`action\s*=\s*["'](help|version)["']`)
	jsOpt   = regexp.MustCompile(`\.(?:option|requiredOption)\(\s*['"](?:-\w,?\s*|-\w\|)?--(?:no-)?([\w-]+)`)
)

func lineOf(src []byte, off int) int { return strings.Count(string(src[:off]), "\n") + 1 }

func camel(s string) string {
	parts := strings.Split(s, "-")
	for i := 1; i < len(parts); i++ {
		if parts[i] != "" {
			parts[i] = strings.ToUpper(parts[i][:1]) + parts[i][1:]
		}
	}
	return strings.Join(parts, "")
}

func unusedFlag(c *Ctx, rel string, f *File) []Hit {
	src := c.X.Source(rel)
	var hits []Hit
	add := func(off int, flag, ident string, uses int) {
		l := lineOf(src, off)
		if uses > 0 || !c.inScope(rel, l, l) {
			return
		}
		hits = append(hits, Hit{Line: l, EndLine: l, Symbol: ident, Text: fmt.Sprintf("flag --%s is defined but its value is never read", strings.TrimLeft(flag, "-")),
			Evidence: fmt.Sprintf("%q is not read anywhere in the indexed repo", ident)})
	}
	switch f.Lang {
	case "go":
		for _, m := range goFlag.FindAllSubmatchIndex(src, -1) {
			v := string(src[m[2]:m[3]])
			if v == "_" {
				continue
			}
			add(m[0], string(src[m[4]:m[5]]), v, c.X.RefFiles[v][rel]-1+(c.X.Refs[v]-c.X.RefFiles[v][rel]))
		}
	case "python":
		for _, m := range pyArg.FindAllSubmatchIndex(src, -1) {
			flag, rest := string(src[m[2]:m[3]]), string(src[m[4]:m[5]])
			if pyStore.MatchString(rest) {
				continue
			}
			dest := strings.ReplaceAll(strings.TrimLeft(flag, "-"), "-", "_")
			if d := pyDest.FindStringSubmatch(rest); d != nil {
				dest = d[1]
			}
			uses := c.X.Refs[dest]
			if strings.Contains(string(src), `"`+dest+`"`) || strings.Contains(string(src), `'`+dest+`'`) || strings.Contains(string(src), "vars(") {
				uses++
			}
			add(m[0], flag, dest, uses)
		}
	case "javascript", "typescript", "tsx":
		for _, m := range jsOpt.FindAllSubmatchIndex(src, -1) {
			flag := string(src[m[2]:m[3]])
			id := camel(flag)
			uses := c.X.Refs[id]
			if strings.Contains(string(src), "opts()") && strings.Contains(string(src), "...") {
				uses++
			}
			add(m[0], flag, id, uses)
		}
	}
	return hits
}

func unusedFile(c *Ctx, rel string, f *File) []Hit {
	if !c.Diff || c.Added == nil || !c.Added(rel) || f.Test || entryPath.MatchString(rel) {
		return nil
	}
	switch f.Lang {
	case "javascript", "typescript", "tsx", "python":
	default:
		return nil
	}
	if len(c.X.ImportedBy[rel]) > 0 {
		return nil
	}
	stem := strings.TrimSuffix(path.Base(rel), path.Ext(rel))
	stem = strings.TrimSuffix(stem, ".d")
	for other := range c.X.RefFiles[stem] {
		if other != rel {
			return nil
		}
	}
	src := c.X.Source(rel)
	if strings.HasPrefix(string(src), "#!") || dynamicRegistration.Match(src) {
		return nil
	}
	for _, s := range f.Symbols {
		if s.TopLevel && registerName.MatchString(s.Name) {
			return nil
		}
	}
	return []Hit{{Line: 1, EndLine: 1, Symbol: stem, Text: fmt.Sprintf("new file %s is not imported or referenced anywhere", path.Base(rel)),
		Evidence: fmt.Sprintf("no import resolves to %s and no other file mentions %q", rel, stem)}}
}

// Modules that register themselves (route/plugin modules loaded by a framework, a glob or an
// init(app) call) are reachable without an import; unused-file never reports them.
var (
	dynamicRegistration = regexp.MustCompile(`(?m)(^\s*@\w+\.(route|get|post|put|patch|delete|websocket|task|command|register)\b|\b(app|router|server|bp|blueprint|api)\.(get|post|put|patch|delete|use|route|register|add_url_rule|include_router)\s*\(|\bdefine[A-Z]\w*\s*\(|\bmodule\.exports\s*=\s*(function|\(|async)|\bexport\s+default\s+(async\s+)?(function|\())`)
	registerName        = regexp.MustCompile(`(?i)^(init|register\w*|setup\w*|install|plugin|routes?|mount|bootstrap)$`)
)

func isCtor(s *Symbol) bool {
	return s.Name == "constructor" || s.Name == "__construct" || s.Name == "__init__" || (s.Container != "" && s.Name == s.Container)
}

func middleMan(c *Ctx, rel string, f *File, cfg map[string]any) []Hit {
	if f.Test || entryPath.MatchString(rel) || f.TopLevelOther > cfgInt(cfg, "max_other_statements", 0) {
		return nil
	}
	min := cfgInt(cfg, "min_functions", 2)
	var fns []*Symbol
	targets := map[string]bool{}
	for _, s := range f.Symbols {
		if s.Kind == "type" || isCtor(s) {
			continue
		}
		if s.Delegate == "" {
			return nil
		}
		fns = append(fns, s)
		targets[s.Delegate] = true
	}
	if len(fns) < min || !c.inScope(rel, 1, f.Lines) {
		return nil
	}
	var pairs []string
	for i, s := range fns {
		if i == 4 {
			pairs = append(pairs, "...")
			break
		}
		pairs = append(pairs, s.Name+" -> "+s.Delegate)
	}
	return []Hit{{Line: fns[0].Line, EndLine: fns[len(fns)-1].EndLine, Symbol: path.Base(rel),
		Text:     fmt.Sprintf("every one of the %d functions in this module only forwards its arguments (%s)", len(fns), strings.Join(pairs, ", ")),
		Evidence: fmt.Sprintf("%d/%d definitions are single-statement pass-throughs; %d importer(s)", len(fns), len(fns), len(c.X.ImportedBy[rel]))}}
}

var ceilingRe = regexp.MustCompile(`(?i)(ceiling|limit|up to|<=|≤|<\s*\d|max(imum)?|at most|bounded|\bn\s*[<≤]|\d+\s*(items|rows|entries|elements|users|records|k\b|m\b))`)
var upgradeRe = regexp.MustCompile(`(?i)(upgrade|then|switch to|replace with|use an? |move to|beyond|past that|if it grows|when .* grows|->|→|migrate)`)

func limitNoteNear(c *Ctx, rel string, from, to int) *Comment {
	for i := range c.X.LimitNotes {
		p := &c.X.LimitNotes[i]
		if p.File == rel && p.Line >= from && p.Line <= to {
			return p
		}
	}
	return nil
}

func nestedLoops(c *Ctx, rel string) []Hit {
	var hits []Hit
	for _, l := range c.X.Loops {
		// Only loops whose structure is new or changed: in a diff scan the outer or inner loop header
		// must be on a changed line (a condition edited inside an old loop is not a new O(n·m) loop).
		if l.File != rel || Sensitive(l.Func) || !(c.inScope(rel, l.Line, l.Line) || c.inScope(rel, l.InnerLine, l.InnerLine)) {
			continue
		}
		if limitNoteNear(c, rel, l.Line-3, l.InnerLine+1) != nil {
			continue
		}
		what := "two collections"
		if l.Outer != "" && l.Inner != "" {
			what = "`" + l.Outer + "` and `" + l.Inner + "`"
		}
		hits = append(hits, Hit{Line: l.Line, EndLine: l.EndLine, Symbol: l.Func, Text: "Nested loop over " + what + " compares elements, which is O(n·m)",
			Evidence: fmt.Sprintf("outer loop line %d, inner loop line %d, no `limit:` comment within 3 lines", l.Line, l.InnerLine)})
	}
	return hits
}

var limitMarker = regexp.MustCompile(`(?:limit|ponytail):`)

func limitNoteIncomplete(c *Ctx, rel string) []Hit {
	var hits []Hit
	for _, p := range c.X.LimitNotes {
		if p.File != rel || !c.inScope(rel, p.Line, p.Line) {
			continue
		}
		body := p.Text
		if m := limitMarker.FindStringIndex(body); m != nil {
			body = body[m[1]:]
		}
		var miss []string
		if !ceilingRe.MatchString(body) {
			miss = append(miss, "limit")
		}
		if !upgradeRe.MatchString(body) {
			miss = append(miss, "upgrade path")
		}
		if len(miss) == 0 {
			continue
		}
		hits = append(hits, Hit{Line: p.Line, EndLine: p.Line, Text: "This shortcut comment does not say its " + strings.Join(miss, " or its "),
			Evidence: strings.TrimSpace(body)})
	}
	return hits
}

func globalLocks(c *Ctx, rel string) []Hit {
	var hits []Hit
	for _, l := range c.X.Locks {
		if l.File != rel || !c.inScope(rel, l.Line, l.Line) || limitNoteNear(c, rel, l.Line-3, l.Line+1) != nil {
			continue
		}
		hits = append(hits, Hit{Line: l.Line, EndLine: l.Line, Text: "A package-level lock serialises every caller and has no comment on how far that scales",
			Evidence: l.Text})
	}
	return hits
}

func duplicateHelper(c *Ctx, rel string, f *File, cfg map[string]any) []Hit {
	if f.Test {
		return nil
	}
	minS := cfgInt(cfg, "min_statements", 3)
	var hits []Hit
	for _, s := range f.Symbols {
		if s.Kind == "type" || s.BodyHash == "" || s.Stmts < minS || isCtor(s) || Sensitive(s.Name) || !c.inScope(rel, s.Line, s.EndLine) {
			continue
		}
		var others []*Symbol
		for _, o := range c.X.ByHash[s.BodyHash] {
			if o != s && o.Stmts == s.Stmts && !c.X.Files[o.File].Test && c.X.Files[o.File].Lang == f.Lang {
				others = append(others, o)
			}
		}
		if len(others) == 0 {
			continue
		}
		slices.SortFunc(others, func(a, b *Symbol) int { return cmp.Or(strings.Compare(a.File, b.File), cmp.Compare(a.Line, b.Line)) })
		o := others[0]
		// in full scans report only the later copy
		if !c.Diff && (o.File > s.File || (o.File == s.File && o.Line > s.Line)) {
			continue
		}
		hits = append(hits, Hit{Line: s.Line, EndLine: s.EndLine, Symbol: s.Name,
			Text:     fmt.Sprintf("%s duplicates the existing helper %s (%s:%d)", s.Name, o.Name, o.File, o.Line),
			Evidence: fmt.Sprintf("identical normalized body (%d statements, hash %s) as %s at %s:%d; %d copies total", s.Stmts, s.BodyHash, o.Name, o.File, o.Line, len(others)+1)})
	}
	return hits
}

// helperReplacement: config names (exact, case-insensitive) or name_re, api, uses (strings
// whose presence in the body means it already uses the API), requires_loop.
func helperReplacement(c *Ctx, rel string, f *File, cfg map[string]any) []Hit {
	if f.Test {
		return nil
	}
	names := map[string]bool{}
	for _, n := range cfgStrings(cfg, "names") {
		names[strings.ToLower(n)] = true
	}
	var nameRe *regexp.Regexp
	if r, _ := cfg["name_re"].(string); r != "" {
		nameRe, _ = regexp.Compile(r)
	}
	api, _ := cfg["api"].(string)
	uses := cfgStrings(cfg, "uses")
	loop := cfgBool(cfg, "requires_loop")
	// body_re: the helper body must match (e.g. a keys helper must append range keys);
	// methods are skipped unless include_methods (a method named keys is a type's own API).
	var bodyRe *regexp.Regexp
	if r, _ := cfg["body_re"].(string); r != "" {
		bodyRe, _ = regexp.Compile(r)
	}
	methods := cfgBool(cfg, "include_methods") || f.Lang == "java" // Java helpers are (static) methods
	src := c.X.Source(rel)
	lines := strings.Split(string(src), "\n")
	var hits []Hit
	for _, s := range f.Symbols {
		if s.Kind == "type" || (!names[strings.ToLower(s.Name)] && (nameRe == nil || !nameRe.MatchString(s.Name))) || !c.inScope(rel, s.Line, s.EndLine) {
			continue
		}
		if s.EndLine > len(lines) {
			continue
		}
		body := strings.Join(lines[s.Line-1:s.EndLine], "\n")
		skip := false
		for _, u := range uses {
			if strings.Contains(body, u) {
				skip = true
			}
		}
		if skip || (loop && !loopRe.MatchString(body)) || s.EndLine-s.Line > cfgInt(cfg, "max_lines", 40) ||
			(bodyRe != nil && !bodyRe.MatchString(body)) || (s.Kind == "method" && !methods) {
			continue
		}
		ev := fmt.Sprintf("hand-written %s (%d lines, %d statements)", s.Name, s.EndLine-s.Line+1, s.Stmts)
		if d, _ := cfg["dependency"].(string); d != "" {
			n := 0
			for _, ff := range c.X.Files {
				for _, im := range ff.Imports {
					if im == d || strings.HasPrefix(im, d+"/") || strings.HasPrefix(im, d+".") {
						n++
						break
					}
				}
			}
			ev += fmt.Sprintf("; %s is an installed dependency imported by %d file(s)", d, n)
		}
		hits = append(hits, Hit{Line: s.Line, EndLine: s.EndLine, Symbol: s.Name, Text: fmt.Sprintf("%s re-implements %s", s.Name, api), Evidence: ev})
	}
	return hits
}

var loopRe = regexp.MustCompile(`\b(for|while|foreach|forEach|reduce)\b`)
var guardRe = regexp.MustCompile(`^\s*(?:\}?\s*else\s+)?(?:if|guard|unless|elif)\b.*(?:\bnil\b|\bnull\b|\bNone\b|\bundefined\b|\bempty\(|len\(|\.length\b|\.isEmpty\(|isBlank|== ?0\b|<= ?0\b|\?\.|!\s*\w|==\s*""|==\s*''|\bis None\b|\bnot\s+\w|=== ?""|isset\(|\?\?)`)

func (c *Ctx) computePatches() {
	c.patches = map[string][]Call{}
	if !c.Diff || c.Changed == nil {
		return
	}
	byFile := map[string][]Call{}
	for _, l := range c.X.Calls {
		for _, cl := range l {
			byFile[cl.File] = append(byFile[cl.File], cl)
		}
	}
	for rel := range c.X.Files {
		rs := c.Changed(rel)
		if len(rs) == 0 || c.X.Files[rel].Test {
			continue
		}
		lines := strings.Split(string(c.X.Source(rel)), "\n")
		seen := map[string]bool{}
		for _, r := range rs {
			for ln := max(r.Start, 1); ln <= r.End && ln <= len(lines); ln++ { // deletion-only hunks can start at 0
				if !guardRe.MatchString(lines[ln-1]) {
					continue
				}
				for _, cl := range byFile[rel] {
					k := fmt.Sprintf("%s:%d", cl.Callee, ln)
					if cl.Line > ln && cl.Line <= ln+4 && !seen[k] {
						seen[k] = true
						c.patches[cl.Callee] = append(c.patches[cl.Callee], Call{Callee: cl.Callee, File: rel, Line: ln, Caller: cl.Caller})
					}
				}
			}
		}
	}
}

func callSitePatches(c *Ctx, rel string, cfg map[string]any) []Hit {
	c.once.Do(c.computePatches)
	min := cfgInt(cfg, "min_sites", 3)
	var hits []Hit
	keys := slices.Sorted(maps.Keys(c.patches))
	for _, callee := range keys {
		sites := c.patches[callee]
		if len(sites) < min || len(c.X.Defs[callee]) == 0 || Sensitive(callee) {
			continue
		}
		slices.SortFunc(sites, func(a, b Call) int { return cmp.Or(strings.Compare(a.File, b.File), cmp.Compare(a.Line, b.Line)) })
		if sites[0].File != rel {
			continue
		}
		var at []string
		for _, s := range sites {
			at = append(at, fmt.Sprintf("%s:%d", s.File, s.Line))
		}
		d := c.X.Defs[callee][0]
		hits = append(hits, Hit{Line: sites[0].Line, EndLine: sites[0].Line, Symbol: callee,
			Text:     fmt.Sprintf("the same guard was added before %d calls to %s; fix it once in %s (%s:%d)", len(sites), callee, callee, d.File, d.Line),
			Evidence: "new guards before calls at " + strings.Join(at, ", ")})
	}
	return hits
}

func (c *Ctx) dirTested(rel string) bool {
	dir := path.Dir(rel)
	for other, of := range c.X.Files {
		if other == rel || of.Test || path.Dir(other) != dir {
			continue
		}
		if c.X.TestIdents[strings.TrimSuffix(path.Base(other), path.Ext(other))] {
			return true
		}
		for _, s := range of.Symbols {
			if s.Exported && c.X.TestIdents[s.Name] {
				return true
			}
		}
	}
	return false
}

func testMissing(c *Ctx, rel string, f *File, cfg map[string]any) []Hit {
	if !c.Diff || f.Test || entryPath.MatchString(rel) {
		return nil
	}
	minC, minL := cfgInt(cfg, "min_complexity", 4), cfgInt(cfg, "min_lines", 30)
	stem := strings.TrimSuffix(path.Base(rel), path.Ext(rel))
	stemTested := false
	for name := range c.X.TestIdents {
		if name == stem {
			stemTested = true
		}
	}
	// Only where the project already tests this area: another source file in the same directory
	// is referenced from tests. A directory without any tests is a project choice, not a gap.
	if !c.dirTested(rel) {
		return nil
	}
	// Go: same-package _test.go files exercise unexported code by name.
	var hits []Hit
	for _, s := range f.Symbols {
		if s.Kind == "type" || isCtor(s) || !s.Exported || (s.Complexity < minC && s.EndLine-s.Line+1 < minL) || !c.inScope(rel, s.Line, s.Line) {
			continue
		}
		if c.X.TestIdents[s.Name] || (stemTested && s.Kind == "method") || (s.Container != "" && c.X.TestIdents[s.Container]) {
			continue
		}
		hits = append(hits, Hit{Line: s.Line, EndLine: s.Line, Symbol: s.Name,
			Text:     fmt.Sprintf("new non-trivial %s %s (complexity %d, %d lines) has no runnable check", s.Kind, s.Name, s.Complexity+1, s.EndLine-s.Line+1),
			Evidence: fmt.Sprintf("no test file references %q", s.Name)})
	}
	return hits
}

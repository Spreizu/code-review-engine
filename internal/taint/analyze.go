package taint

import (
	"fmt"
	"regexp"
	"slices"
	"strconv"
	"strings"
)

// Hit is one source -> sink flow.
type Hit struct {
	Class    string
	Node     *N
	Sink     string // normalised sink callee
	Evidence string
}

type summary struct{ withParams, own T }

type analyzer struct {
	sx      *syntax
	l       *Lang
	fam     string
	src     []byte
	file    string
	summ    map[string]summary
	hits    []Hit
	seen    map[[3]uint32]bool
	collect bool
	ret     val
	decor   string
	cur     *N
	budget  int
	// clean-sink bookkeeping (AnalyzeFull): phase 1 re-runs functions with tainted parameters
	// and only records which sinks a parameter reaches.
	phase      int
	srcFn      map[*N]bool
	cands      []cand
	paramReach map[[3]uint32]bool
	// cross-file summaries (project.go): onlyParam >= 0 taints just that parameter
	onlyParam int
	ext       *Index
	path      string
}

type cand struct {
	h  Hit
	fn *N
}

// Result is the full outcome of a file analysis: the tainted flows, and the Clean sinks - calls
// to a known sink of a class inside a function that does read untrusted input (a source, a
// source-typed parameter or a local helper returning one), where neither that input nor any of
// the function's parameters reaches the sink. Pattern rules use Clean to drop a dangerous-API
// match whose argument is provably not request-derived (filter taint.clean:<class>).
type Result struct {
	Hits  []Hit
	Clean []Hit
}

// Analyze runs taint-lite over a parsed file and returns every source -> sink flow found.
func Analyze(root *N, src []byte, family string, l *Lang) []Hit {
	return AnalyzeFull(root, src, family, l).Hits
}

// AnalyzeFull is Analyze plus the clean sinks (see Result).
func AnalyzeFull(root *N, src []byte, family string, l *Lang) Result {
	return AnalyzeFullAt(root, src, family, "", l)
}

// AnalyzeFullAt is AnalyzeFull for the file at path (slash path relative to the scan root), which
// also follows calls into functions of other files of the project index (SetProject).
func AnalyzeFullAt(root *N, src []byte, family, path string, l *Lang) Result {
	sx := langs[family]
	if sx == nil || l == nil || root == nil {
		return Result{}
	}
	a := &analyzer{sx: sx, l: l, fam: family, src: src, file: string(src), summ: map[string]summary{}, seen: map[[3]uint32]bool{},
		srcFn: map[*N]bool{}, paramReach: map[[3]uint32]bool{}, onlyParam: -1, path: path}
	if path != "" {
		a.ext = currentProject()
	}
	var fns []*N
	var collect func(n *N)
	collect = func(n *N) {
		if sx.funcs[n.Kind] {
			fns = append(fns, n)
		}
		for _, k := range n.Kids {
			collect(k)
		}
	}
	collect(root)
	// Same-file summaries: does the return value depend on the parameters / on own sources?
	for _, f := range fns {
		name := a.funcName(f)
		if name == "" {
			continue
		}
		withP := a.run(f, true, false)
		own := a.run(f, false, false)
		s := a.summ[name]
		a.summ[name] = summary{s.withParams | withP.t, s.own | own.t}
	}
	a.collect = true
	a.run(root, false, true)
	for _, f := range fns {
		a.run(f, false, true)
	}
	slices.SortFunc(a.hits, func(x, y Hit) int { return int(x.Node.S) - int(y.Node.S) })
	a.phase = 1
	for _, f := range fns {
		a.run(f, true, true)
	}
	var clean []Hit
	done := map[[3]uint32]bool{}
	for _, c := range a.cands {
		k := [3]uint32{c.h.Node.S, c.h.Node.E, uint32(classBit(c.h.Class))}
		if !a.srcFn[c.fn] || a.paramReach[k] || a.seen[k] || done[k] {
			continue
		}
		done[k] = true
		clean = append(clean, c.h)
	}
	return Result{Hits: a.hits, Clean: clean}
}

func (a *analyzer) funcName(f *N) string {
	if n := f.F("name"); n != nil {
		return n.text(a.src)
	}
	if a.fam == "kotlin" && f.Kind == "function_declaration" {
		if id := f.Child("identifier", "simple_identifier"); id != nil {
			return id.text(a.src)
		}
	}
	return ""
}

// run analyses one function (or the file's top-level code when f is the root).
func (a *analyzer) run(f *N, taintParams, collect bool) val {
	a.collect, a.ret, a.cur, a.budget = collect, val{}, f, 200000
	e := newEnv()
	a.decor = ""
	if p := f.Parent; p != nil && (p.Kind == "decorated_definition") {
		for _, d := range p.Kids {
			if d.Kind == "decorator" {
				a.decor += d.text(a.src) + "\n"
			}
		}
	}
	if !a.sx.funcs[f.Kind] { // top level
		for _, k := range f.Kids {
			a.walk(k, e)
		}
		return a.ret
	}
	route := a.l.routeParams != nil && a.decor != "" && a.l.routeParams.MatchString(a.decor) ||
		a.decor != "" && a.l.guarded(a.l.guardedRoutes, a.decor, a.file)
	for pi, p := range a.params(f) {
		ptxt := p.text(a.src)
		if prev := prevNamed(p); prev != nil && (prev.Kind == "parameter_modifiers" || prev.Kind == "annotation") {
			ptxt = prev.text(a.src) + " " + ptxt
		}
		src := a.l.paramSources != nil && a.l.paramSources.MatchString(ptxt) || a.l.guarded(a.l.guardedParams, ptxt, a.file)
		if route && !regexp.MustCompile(`Depends\(|:\s*(Request|Response|Session|BackgroundTasks)\b|^(self|cls)$`).MatchString(ptxt) {
			src = true
		}
		if src && collect && a.phase == 0 {
			a.srcFn[f] = true
		}
		if taintParams && (a.onlyParam < 0 || pi == a.onlyParam) || src && a.onlyParam < 0 {
			why := fmt.Sprintf("line %d: parameter %s", p.Row+1, strings.TrimSpace(firstLine(ptxt)))
			for _, id := range a.paramNames(p) {
				e.vars[id] = val{all, why}
			}
		}
	}
	body := f.F("body")
	if body == nil {
		for _, k := range f.Kids {
			if k.Kind == "function_body" || k.Kind == "block" || k.Kind == "statements" {
				body = k
			}
		}
	}
	if body == nil {
		return a.ret
	}
	// expression bodies: arrow functions, lambdas, Kotlin `= expr`
	if !a.isBlock(body) {
		inner := body
		if body.Kind == "function_body" {
			if nk := body.NamedKids(); len(nk) == 1 && !a.isBlock(nk[0]) {
				inner = nk[0]
			} else {
				a.walk(body, e)
				return a.ret
			}
		}
		v := a.eval(inner, e)
		a.ret = a.ret.or(v)
		a.checkReturn(inner, v)
		return a.ret
	}
	a.walk(body, e)
	return a.ret
}

func (a *analyzer) isBlock(n *N) bool {
	switch n.Kind {
	case "block", "statement_block", "compound_statement", "constructor_body", "function_body", "statements", "class_body":
		return true
	}
	return false
}

func prevNamed(n *N) *N {
	p := n.Parent
	if p == nil {
		return nil
	}
	var prev *N
	for _, k := range p.Kids {
		if k == n {
			return prev
		}
		if k.Named {
			prev = k
		}
	}
	return nil
}

func firstLine(s string) string {
	if i := strings.IndexByte(s, '\n'); i >= 0 {
		return s[:i]
	}
	if len(s) > 80 {
		return s[:80]
	}
	return s
}

func (a *analyzer) params(f *N) []*N {
	ps := f.F("parameters")
	if ps == nil {
		ps = f.Child("function_value_parameters", "formal_parameters", "parameters", "parameter_list", "lambda_parameters")
	}
	if ps == nil {
		if p := f.F("parameter"); p != nil { // arrow function with a single bare parameter
			return []*N{p}
		}
		return nil
	}
	if a.sx.idents[ps.Kind] {
		return []*N{ps}
	}
	var out []*N
	for _, k := range ps.NamedKids() {
		if k.Kind == "parameter_modifiers" || k.Kind == "annotation" {
			continue
		}
		out = append(out, k)
	}
	return out
}

func (a *analyzer) paramNames(p *N) []string {
	if a.sx.idents[p.Kind] {
		return []string{p.text(a.src)}
	}
	if n := p.F("name"); n != nil {
		if a.sx.idents[n.Kind] || n.Kind == "identifier" {
			return []string{n.text(a.src)}
		}
		return a.patternNames(n)
	}
	if n := p.F("pattern"); n != nil {
		return a.patternNames(n)
	}
	for _, k := range p.Kids {
		if a.sx.idents[k.Kind] || k.Kind == "identifier" {
			return []string{k.text(a.src)}
		}
	}
	return nil
}

func (a *analyzer) patternNames(n *N) []string {
	var out []string
	var rec func(x *N)
	rec = func(x *N) {
		if x.Kind == "pair_pattern" || x.Kind == "pair" {
			if v := x.F("value"); v != nil {
				rec(v)
				return
			}
		}
		if a.sx.idents[x.Kind] || x.Kind == "identifier" {
			out = append(out, x.text(a.src))
			return
		}
		for _, k := range x.Kids {
			if k.Field == "type" || k.Kind == "type_annotation" || k.Kind == "default_value" || k.Field == "value" && x.Kind != "assignment_pattern" {
				continue
			}
			rec(k)
		}
	}
	rec(n)
	return out
}

// ---- statements

func (a *analyzer) walk(n *N, e *env) {
	if n == nil || !n.Named && len(n.Kids) == 0 || e.dead {
		return
	}
	if a.budget--; a.budget < 0 {
		return
	}
	sx := a.sx
	switch {
	case sx.funcs[n.Kind] && n != a.cur:
		return
	case n.Kind == "decorated_definition" && a.cur != nil && a.cur.Parent != n:
		// nested function (analysed separately); walk decorators only
		return
	case n.Kind == "class_declaration" || n.Kind == "class_definition" || n.Kind == "class" || n.Kind == "interface_declaration":
		if a.cur != nil && a.sx.funcs[a.cur.Kind] {
			return // local classes are analysed through their methods
		}
		for _, k := range n.Kids {
			a.walk(k, e)
		}
	case sx.assigns[n.Kind]:
		a.assign(n, e)
	case sx.ifs[n.Kind]:
		a.ifStmt(n, e)
	case sx.loops[n.Kind]:
		a.loop(n, e)
	case sx.switches[n.Kind]:
		a.switchStmt(n, e)
	case n.Kind == "try_statement" || n.Kind == "try_expression":
		base := e.clone()
		var out *env
		for _, k := range n.Kids {
			if k.Kind == "catch_clause" || k.Kind == "except_clause" || k.Kind == "catch_block" {
				c := base.clone()
				a.walk(k, c)
				out = merge(out, c)
				continue
			}
			a.walk(k, e)
		}
		if out != nil {
			*e = *merge(e, out)
		}
	case sx.returns[n.Kind]:
		if a.fam == "kotlin" && !strings.HasPrefix(n.text(a.src), "return") {
			for _, k := range n.Kids {
				a.walk(k, e)
			}
			return
		}
		var v val
		for _, k := range n.NamedKids() {
			v = v.or(a.eval(k, e))
		}
		a.ret = a.ret.or(v)
		if nk := n.NamedKids(); len(nk) > 0 {
			a.checkReturn(nk[0], v)
		}
		e.dead = true
	case n.Kind == "throw_statement" || n.Kind == "raise_statement" || n.Kind == "throw_expression" && a.fam != "javascript":
		for _, k := range n.Kids {
			a.walk(k, e)
		}
		e.dead = true
	case sx.calls[n.Kind] || sx.news[n.Kind] || sx.pseudo[n.Kind] != "":
		a.eval(n, e)
	case n.Kind == "with_item" || n.Kind == "as_pattern":
		a.eval(n, e)
	default:
		for _, k := range n.Kids {
			a.walk(k, e)
		}
	}
}

func (a *analyzer) checkReturn(n *N, v val) {
	if !a.collect || v.t == 0 || a.decor == "" {
		return
	}
	switch n.Kind { // dicts/lists are serialised as JSON by the framework, not rendered as HTML
	case "dictionary", "list", "dictionary_comprehension", "list_comprehension":
		return
	case "tuple":
		if nk := n.NamedKids(); len(nk) > 0 && (nk[0].Kind == "dictionary" || nk[0].Kind == "list") {
			return
		}
	case "identifier":
		// return data, where every assignment to data in this function is a dict/list literal
		if a.cur != nil {
			body := a.cur.text(a.src)
			nm := regexp.QuoteMeta(n.text(a.src))
			asg := regexp.MustCompile(`(?m)^\s*`+nm+`\s*=[^=]`).FindAllStringIndex(body, -1)
			lit := regexp.MustCompile(`(?m)^\s*`+nm+`\s*=\s*[\{\[]`).FindAllStringIndex(body, -1)
			if len(asg) > 0 && len(asg) == len(lit) {
				return
			}
		}
	case "call":
		c, recv, args, kw := a.callParts(n)
		if regexp.MustCompile(`(^|\.)(jsonify|dumps|JSONResponse|JsonResponse)$`).MatchString(c) {
			return
		}
		// return other_handler(): a same-file function called without arguments; its own returns are checked in its body
		if _, ok := a.summ[c]; ok && a.local(recv) && len(args) == 0 && len(kw) == 0 {
			return
		}
	}
	for _, s := range a.l.sinks {
		if s.returnIn == nil || v.t&s.class == 0 || !s.returnIn.MatchString(a.decor) || s.file != nil && !s.file.MatchString(a.file) {
			continue
		}
		a.hit(s, n, "return from "+strings.TrimSpace(firstLine(a.decor)), v)
	}
}

func (a *analyzer) hit(s sink, n *N, name string, v val) {
	k := [3]uint32{n.S, n.E, uint32(s.class)}
	if a.phase == 1 {
		a.paramReach[k] = true
		return
	}
	if a.seen[k] {
		return
	}
	a.seen[k] = true
	ev := v.why
	if ev == "" {
		ev = "tainted value"
	}
	a.hits = append(a.hits, Hit{Class: s.name, Node: n, Sink: name, Evidence: fmt.Sprintf("source %s -> sink %s (line %d)", ev, name, n.Row+1)})
}

type arm struct{ cond, body *N }

func (a *analyzer) ifStmt(n *N, e *env) {
	var arms []arm
	var els *N
	var collectIf func(x *N)
	collectIf = func(x *N) {
		cond := x.F("condition")
		then := x.F("consequence")
		if then == nil {
			then = x.F("body")
		}
		var alts []*N
		if a.fam == "kotlin" {
			var bodies []*N
			for _, k := range x.NamedKids() {
				if k != cond {
					bodies = append(bodies, k)
				}
			}
			if len(bodies) > 0 {
				then = bodies[0]
			}
			if len(bodies) > 1 {
				alts = bodies[1:2]
			}
		} else {
			alts = x.FAll("alternative")
		}
		arms = append(arms, arm{cond, then})
		for _, alt := range alts {
			switch alt.Kind {
			case "elif_clause", "else_if_clause":
				c := alt.F("condition")
				b := alt.F("consequence")
				if b == nil {
					b = alt.F("body")
				}
				arms = append(arms, arm{c, b})
			case "else_clause", "else":
				b := alt.F("body")
				if b == nil {
					nk := alt.NamedKids()
					if len(nk) == 1 && nk[0].Kind == "if_statement" {
						collectIf(nk[0])
						continue
					}
					b = alt
				}
				els = b
			case "if_statement":
				collectIf(alt)
			default:
				els = alt
			}
		}
	}
	collectIf(n)
	base := e
	var out *env
	var guards, allowed []string
	var numeric []numTarget
	decided := false
	for _, ar := range arms {
		if ar.cond != nil {
			a.eval(ar.cond, base)
		}
		c, ok := a.constEval(ar.cond, base)
		if ok && !c.truthy() {
			continue
		}
		b := base.clone()
		if ar.cond != nil {
			for _, g := range a.allowVars(ar.cond, true, b) { // `if host in ALLOWED: fetch(url)`
				b.clearBits(g, urlMask)
			}
			for _, g := range a.numericVars(ar.cond, true, b) { // `if (is_numeric($o[0]) && ...)`
				g.clear(b)
			}
		}
		if ar.body != nil {
			a.walk(ar.body, b)
		}
		if b.dead && ar.cond != nil {
			guards = append(guards, a.guardVars(ar.cond)...)
			allowed = append(allowed, a.allowVars(ar.cond, false, base)...)
			numeric = append(numeric, a.numericVars(ar.cond, false, base)...)
		}
		out = merge(out, b)
		if ok && c.truthy() {
			decided = true
			break
		}
	}
	if !decided {
		b := base.clone()
		if els != nil {
			a.walk(els, b)
		}
		out = merge(out, b)
	}
	if !out.dead {
		for _, g := range guards { // `if '../' in x: return` - x passed a rejecting check on this path
			if _, ok := out.vars[g]; ok {
				out.vars[g] = val{}
			}
		}
		for _, g := range allowed { // `if host not in ALLOWED: abort()` - URL checked against an allow-list
			out.clearBits(g, urlMask)
		}
		for _, g := range numeric { // `if not x.isdigit(): return`
			g.clear(out)
		}
	}
	*e = *out
}

// guardCalls are checks that look for a dangerous fragment inside a value.
var guardCalls = regexp.MustCompile(`(^|\.)(contains|includes|startsWith|endsWith|startswith|endswith|indexOf|strpos|stripos|str_contains|str_starts_with|str_ends_with|Contains|ContainsAny|ContainsRune|HasPrefix|HasSuffix|matches|preg_match|find)$`)

var prefixCalls = regexp.MustCompile(`(^|\.)(startswith|startsWith|HasPrefix|str_starts_with)$`)

// guardMeta: fragments that only a rejecting validation would look for.
var guardMeta = regexp.MustCompile(`\.\.|['"<>;&|$\x60\\]`)

// guardVars returns the variables a rejecting condition validates: a string literal holding an
// injection metacharacter tested for membership (`'../' in x`, x.contains("'"), strings.Contains(x, ";")).
func (a *analyzer) guardVars(cond *N) []string {
	var out []string
	var visit func(n *N)
	idents := func(n *N) {
		var rec func(m *N)
		rec = func(m *N) {
			if a.sx.idents[m.Kind] || m.Kind == "variable_name" {
				out = append(out, norm(m.text(a.src)))
			}
			for _, k := range m.Kids {
				if !a.sx.strings[k.Kind] {
					rec(k)
				}
			}
		}
		rec(n)
	}
	lit := func(n *N) bool {
		if !a.sx.strings[n.Kind] && n.Kind != "encapsed_string" {
			return false
		}
		t := n.text(a.src)
		if len(t) >= 2 {
			t = t[1 : len(t)-1]
		}
		return guardMeta.MatchString(t)
	}
	visit = func(n *N) {
		if n.Kind == "comparison_operator" && a.fam == "python" {
			nk := n.NamedKids()
			if len(nk) == 2 && lit(nk[0]) && strings.Contains(n.op(a.src), "in") && !strings.Contains(n.op(a.src), "not") {
				idents(nk[1])
				return
			}
		}
		if a.sx.calls[n.Kind] {
			callee, recv, args, _ := a.callParts(n)
			// `if not path.startswith(base): return` - containment check after normalising
			if prefixCalls.MatchString(callee) && n.Parent != nil && (n.Parent.Kind == "not_operator" || (n.Parent.Kind == "unary_expression" || n.Parent.Kind == "prefix_expression") && strings.HasPrefix(n.Parent.text(a.src), "!")) {
				if recv != nil {
					idents(recv)
				} else if len(args) > 0 {
					idents(args[0])
				}
				return
			}
			if guardCalls.MatchString(callee) {
				hasLit := false
				for _, x := range args {
					if lit(x) || len(x.NamedKids()) == 1 && lit(x.NamedKids()[0]) {
						hasLit = true
					}
				}
				if hasLit {
					if recv != nil {
						idents(recv)
					}
					for _, x := range args {
						if !lit(x) {
							idents(x)
						}
					}
					return
				}
			}
		}
		for _, k := range n.Kids {
			visit(k)
		}
	}
	visit(cond)
	return out
}

func (a *analyzer) loop(n *N, e *env) {
	b := e.clone()
	// for-each binding
	var target, iter *N
	switch n.Kind {
	case "enhanced_for_statement":
		target, iter = n.F("name"), n.F("value")
	case "for_in_statement":
		target, iter = n.F("left"), n.F("right")
	case "for_statement":
		if a.fam == "python" {
			target, iter = n.F("left"), n.F("right")
		} else if a.fam == "go" {
			if rc := n.Child("range_clause"); rc != nil {
				target, iter = rc.F("left"), rc.F("right")
			}
		} else if a.fam == "kotlin" {
			target = n.Child("variable_declaration", "multi_variable_declaration")
			for _, k := range n.NamedKids() {
				if k != target && k.Kind != "block" && k.Kind != "control_structure_body" && iter == nil && target != nil && k.S > target.E {
					iter = k
				}
			}
		}
	case "foreach_statement":
		nk := n.NamedKids()
		if len(nk) >= 2 {
			iter, target = nk[0], nk[1]
		}
	}
	if iter != nil && target != nil {
		v := a.eval(iter, b)
		if a.sx.idents[iter.Kind] || a.sx.members[iter.Kind] {
			v = v.or(b.container(norm(iter.text(a.src))))
		}
		for _, id := range a.patternNames(target) {
			b.vars[id] = v
		}
	}
	for pass := 0; pass < 2; pass++ {
		for _, k := range n.Kids {
			if k == target || k == iter {
				continue
			}
			a.walk(k, b)
		}
		if b.dead { // a return inside the body ends that path only; the loop may not run
			b = merge(e, nil)
			b = b.clone()
		}
	}
	*e = *merge(e, b)
}

func (a *analyzer) switchStmt(n *N, e *env) {
	subj := n.F("condition")
	if subj == nil {
		subj = n.F("value")
	}
	if subj == nil {
		subj = n.Child("when_subject")
	}
	if subj == nil {
		subj = n.F("subject")
	}
	if subj != nil {
		a.eval(subj, e)
	}
	body := n.F("body")
	if body == nil {
		body = n
	}
	var groups []*N
	hasDefault := false
	for _, k := range body.NamedKids() {
		if strings.Contains(k.Kind, "case") || strings.Contains(k.Kind, "default") || k.Kind == "switch_block_statement_group" || k.Kind == "switch_rule" || k.Kind == "when_entry" {
			groups = append(groups, k)
			t := k.text(a.src)
			if strings.HasPrefix(t, "default") || strings.Contains(k.Kind, "default") || strings.HasPrefix(t, "else") || k.Kind == "case_clause" && regexp.MustCompile(`^case\s+_\s*:`).MatchString(t) {
				hasDefault = true
			}
		}
	}
	// Python match: no fall-through, first matching case (or `case _`) runs
	if c, ok := a.constEval(subj, e); ok && a.fam == "python" {
		for _, g := range groups {
			t := g.text(a.src)
			if a.caseMatches(g, c, e) || regexp.MustCompile(`^case\s+_\s*:`).MatchString(t) {
				a.walk(g.F("consequence"), e)
				return
			}
		}
		return
	}
	// constant subject with break-terminated cases (Java/JS/PHP): walk only the cases that run
	if c, ok := a.constEval(subj, e); ok && (a.fam == "java" || a.fam == "javascript" || a.fam == "php") {
		start := -1
		for i, g := range groups {
			if a.caseMatches(g, c, e) {
				start = i
				break
			}
		}
		if start < 0 {
			for i, g := range groups {
				if strings.HasPrefix(g.text(a.src), "default") || strings.Contains(g.Kind, "default") {
					start = i
				}
			}
		}
		if start < 0 {
			return
		}
		for _, g := range groups[start:] {
			if a.walkCase(g, e) {
				return
			}
		}
		return
	}
	var out *env
	for _, g := range groups {
		b := e.clone()
		a.walkCase(g, b)
		out = merge(out, b)
	}
	if !hasDefault || out == nil {
		out = merge(out, e)
	}
	*e = *out
}

// walkCase walks a case body; it reports whether the case ends with break (no fall-through).
func (a *analyzer) walkCase(g *N, e *env) bool {
	brk := false
	for _, k := range g.Kids {
		if k.Kind == "switch_label" || k.Field == "value" {
			continue
		}
		if k.Kind == "break_statement" {
			brk = true
			break
		}
		a.walk(k, e)
		if k.Kind == "return_statement" || k.Kind == "throw_statement" {
			brk = true
			break
		}
	}
	return brk || g.Kind == "switch_rule"
}

func (a *analyzer) caseMatches(g *N, c cv, e *env) bool {
	var vals []*N
	if lab := g.Child("switch_label"); lab != nil {
		vals = lab.NamedKids()
	}
	for _, k := range g.Kids {
		if k.Kind == "switch_label" && len(vals) == 0 {
			vals = k.NamedKids()
		}
		if k.Field == "value" {
			vals = append(vals, k)
		}
		if k.Kind == "case_pattern" {
			for _, p := range k.NamedKids() {
				if p.Kind == "union_pattern" {
					vals = append(vals, p.NamedKids()...)
				} else {
					vals = append(vals, p)
				}
			}
		}
	}
	for _, v := range vals {
		if x, ok := a.constEval(v, e); ok && x == c {
			return true
		}
	}
	return false
}

// ---- assignment

func (a *analyzer) assign(n *N, e *env) val {
	var targets []*N
	var values []*N
	compound := strings.Contains(n.Kind, "augmented")
	switch n.Kind {
	case "variable_declarator":
		targets, values = []*N{n.F("name")}, []*N{n.F("value")}
	case "assignment_expression", "assignment", "augmented_assignment", "augmented_assignment_expression", "reference_assignment_expression", "assignment_statement":
		l, r := n.F("left"), n.F("right")
		if a.fam == "kotlin" && l == nil {
			nk := n.NamedKids()
			if len(nk) >= 2 {
				l, r = nk[0], nk[len(nk)-1]
			}
		}
		if o := n.F("operator"); o != nil && o.text(a.src) != "=" && o.text(a.src) != ":=" {
			compound = true
		} else if op := n.op(a.src); op != "" && op != "=" && op != ":=" && strings.HasSuffix(op, "=") {
			compound = true
		}
		targets, values = a.split(l), a.split(r)
	case "named_expression":
		targets, values = []*N{n.F("name")}, []*N{n.F("value")}
	case "short_var_declaration", "var_spec":
		l := n.F("left")
		r := n.F("right")
		if n.Kind == "var_spec" {
			targets = n.FAll("name")
			r = n.F("value")
		} else {
			targets = a.split(l)
		}
		values = a.split(r)
	case "property_declaration":
		var decl *N
		for _, k := range n.NamedKids() {
			if k.Kind == "variable_declaration" || k.Kind == "multi_variable_declaration" {
				decl = k
				continue
			}
			if decl != nil && k.S > decl.E && k.Kind != "property_delegate" && k.Kind != "getter" && k.Kind != "setter" && !strings.HasSuffix(k.Kind, "type") {
				values = []*N{k}
				break
			}
		}
		if decl != nil {
			targets = []*N{decl}
		}
	}
	var last val
	vals := make([]val, len(values))
	for i, v := range values {
		if v != nil {
			vals[i] = a.eval(v, e)
		}
	}
	for i, t := range targets {
		if t == nil {
			continue
		}
		var v val
		var vn *N
		switch {
		case len(values) == len(targets):
			v, vn = vals[i], values[i]
		default:
			for _, x := range vals {
				v = v.or(x)
			}
			if i == 0 && len(values) == 1 && values[0] != nil && a.sx.calls[values[0].Kind] && !compound {
				// u, err := url.Parse(raw): the first result is the call's value
				if callee, _, args, _ := a.callParts(values[0]); urlParse.MatchString(callee) && len(args) > 0 {
					a.bind(t, v, nil, e, compound)
					if n := t; a.sx.idents[n.Kind] || n.Kind == "identifier" {
						e.origin[norm(n.text(a.src))] = norm(args[0].text(a.src))
					}
					last = v
					continue
				}
			}
		}
		a.bind(t, v, vn, e, compound)
		last = v
	}
	return last
}

func (a *analyzer) split(n *N) []*N {
	if n == nil {
		return nil
	}
	switch n.Kind {
	case "expression_list", "pattern_list":
		return n.NamedKids()
	}
	return []*N{n}
}

var containerNew = regexp.MustCompile(`^(new(java\.util\.)?(ArrayList|LinkedList|Vector|ArrayDeque|HashMap|LinkedHashMap|TreeMap|Hashtable|ConcurrentHashMap)\b|\[\]$|\{\}$|list\(\)$|dict\(\)$|(mutable)?(listOf|mapOf|arrayListOf|hashMapOf)(<[^>]*>)?\(\)$|array\(\)$|newArray\(\)$|newMap\(\)$|make\(map)`)

func (a *analyzer) bind(t *N, v val, vn *N, e *env, compound bool) {
	switch {
	case t.Kind == "subscript" || t.Kind == "subscript_expression" || t.Kind == "index_expression" || t.Kind == "array_access" || t.Kind == "element_reference":
		obj, key := a.subscriptParts(t)
		if obj == nil {
			return
		}
		name := norm(obj.text(a.src))
		a.setitemSink(t, name, key, v, e)
		if k, ok := a.constEval(key, e); ok {
			m := e.keys[name]
			if m == nil {
				m = map[string]val{}
				e.keys[name] = m
			}
			ks := keyStr(k)
			if l, ok := e.lists[name]; ok && k.kind == 'i' && int(k.i) < len(l) && k.i >= 0 {
				l[k.i] = v
				return
			}
			if compound {
				v = m[ks].or(v)
			}
			m[ks] = v
			return
		}
		e.vars[name] = e.vars[name].or(v)
		return
	case a.sx.idents[t.Kind] || a.sx.members[t.Kind] || t.Kind == "identifier" || t.Kind == "simple_identifier" || t.Kind == "variable_declaration" && len(t.NamedKids()) <= 2:
		x := t
		if t.Kind == "variable_declaration" {
			x = t.NamedKids()[0]
		}
		name := norm(x.text(a.src))
		if compound {
			v = e.vars[name].or(v)
			delete(e.consts, name)
		} else {
			delete(e.keys, name)
			delete(e.lists, name)
			if vn != nil {
				if c, ok := a.constEval(vn, e); ok {
					e.consts[name] = c
				} else {
					delete(e.consts, name)
				}
				delete(e.origin, name)
				if a.sx.calls[vn.Kind] || a.sx.news[vn.Kind] {
					if callee, _, args, _ := a.callParts(vn); urlParse.MatchString(callee) && len(args) > 0 && (a.sx.idents[args[0].Kind] || args[0].Kind == "variable_name") {
						e.origin[name] = norm(args[0].text(a.src))
					}
				}
				if vn.Kind == "dictionary" || vn.Kind == "object" {
					a.dictLiteral(name, vn, e)
				}
				if vt := norm(vn.text(a.src)); containerNew.MatchString(vt) || vn.Kind == "list" && len(vn.NamedKids()) == 0 || vn.Kind == "array" && len(vn.NamedKids()) == 0 {
					e.lists[name] = []val{}
				}
			}
		}
		e.vars[name] = v
	default:
		for _, id := range a.patternNames(t) {
			e.vars[id] = v
			delete(e.consts, id)
		}
	}
}

func keyStr(c cv) string {
	switch c.kind {
	case 'i':
		return strconv.FormatInt(c.i, 10)
	case 's':
		return "s:" + c.s
	}
	return fmt.Sprint(c.b)
}

func (a *analyzer) subscriptParts(t *N) (obj, key *N) {
	switch t.Kind {
	case "subscript":
		return t.F("value"), t.F("subscript")
	case "subscript_expression":
		o := t.F("object")
		k := t.F("index")
		if o == nil {
			nk := t.NamedKids()
			if len(nk) >= 1 {
				o = nk[0]
			}
			if len(nk) >= 2 {
				k = nk[1]
			}
		}
		return o, k
	case "array_access":
		return t.F("array"), t.F("index")
	case "index_expression":
		if o := t.F("operand"); o != nil {
			return o, t.F("index")
		}
		nk := t.NamedKids()
		if len(nk) >= 2 {
			return nk[0], nk[1]
		}
	}
	nk := t.NamedKids()
	if len(nk) >= 2 {
		return nk[0], nk[1]
	}
	return nil, nil
}

// setitemSink treats `obj[key] = value` as a call to the pseudo-callee "obj.__setitem__" with
// arguments (key, value), so sinks such as a web session store can be written in the spec.
func (a *analyzer) setitemSink(t *N, obj string, key *N, v val, e *env) {
	if !a.collect {
		return
	}
	callee := obj + ".__setitem__"
	var kv val
	kdone := false
	for _, s := range a.l.sinks {
		if s.callee == nil || !s.callee.MatchString(callee) || s.file != nil && !s.file.MatchString(a.file) {
			continue
		}
		if !kdone && key != nil {
			kv, kdone = a.eval(key, e), true
		}
		var x val
		for _, i := range s.args {
			switch i {
			case 0:
				x = x.or(kv)
			case 1:
				x = x.or(v)
			}
		}
		if len(s.args) == 0 {
			x = kv.or(v)
		}
		if x.t&s.class != 0 {
			a.hit(s, t, callee, x)
		} else if a.phase == 0 {
			a.cands = append(a.cands, cand{Hit{Class: s.name, Node: t, Sink: callee, Evidence: "sink argument not derived from the function's untrusted input"}, a.cur})
		}
	}
}

// dictLiteral records the per-key taint of a dict/object literal with constant keys, so a later
// d["k"] lookup sees only that entry ({"a": "x", "b": user}["a"] is clean).
func (a *analyzer) dictLiteral(name string, vn *N, e *env) {
	m := map[string]val{}
	for _, p := range vn.NamedKids() {
		if p.Kind != "pair" {
			return // spread / computed entries: keep the whole-object taint only
		}
		k, v := p.F("key"), p.F("value")
		if k == nil || v == nil {
			return
		}
		var ks string
		if k.Kind == "property_identifier" || k.Kind == "identifier" && a.fam == "javascript" {
			ks = keyStr(cv{kind: 's', s: k.text(a.src)})
		} else if c, ok := a.constEval(k, e); ok {
			ks = keyStr(c)
		} else {
			return
		}
		m[ks] = a.eval(v, e)
	}
	e.keys[name] = m
}

// urlParse: calls that parse a URL string; a check on the parsed value (host, scheme) is a check
// on the variable it came from.
var urlParse = regexp.MustCompile(`(^|\.)(urlparse|urlsplit|urllib\.parse\.urlparse|url\.Parse|url\.ParseRequestURI|new URL|new (java\.net\.)?(URL|URI)|URI\.create|toURI|toHttpUrl|parse_url|URL\.parse|URL|Uri\.parse|httpx\.URL)$`)

// urlMask: the classes an allow-list check on a URL/host neutralises.
var urlMask = classBit("ssrf") | classBit("redirect")

// membership calls: collection.contains(x) style allow-list lookups.
var memberCalls = regexp.MustCompile(`(^|\.)(contains|includes|has|containsKey|__contains__|in_array|Contains|ContainsKey|isAllowed|is_allowed|allowed|isTrusted|is_safe_url|url_has_allowed_host_and_scheme)$`)

// safeURLPrefix: a literal an allow-list prefix check compares against (absolute URL with a host
// and a path separator after it, or a site-relative path that is not protocol-relative).
var safeURLPrefix = regexp.MustCompile(`^(https?://[^/'"]+/|/[^/\\])`)

func (e *env) clearBits(name string, mask T) {
	for _, n := range []string{name, e.origin[name]} {
		if n == "" {
			continue
		}
		if v, ok := e.vars[n]; ok {
			v.t &^= mask
			if v.t == 0 {
				v.why = ""
			}
			e.vars[n] = v
		}
	}
}

// allowVars returns the variables an allow-list condition vouches for when it evaluates to want:
// membership in a non-literal collection (x in ALLOWED, ALLOWED.contains(x), allowed[x]), a call
// to a URL-safety helper, equality with a URL literal, or a prefix check against a literal that
// pins the host (x.startswith("https://api.example.com/")). Only && / and chains are followed.
func (a *analyzer) allowVars(cond *N, want bool, e *env) []string {
	var out []string
	names := func(n *N) {
		var rec func(m *N)
		rec = func(m *N) {
			if a.sx.idents[m.Kind] || m.Kind == "variable_name" {
				out = append(out, norm(m.text(a.src)))
			}
			if a.sx.members[m.Kind] { // parsed.hostname -> parsed (and its origin)
				if nk := m.NamedKids(); len(nk) > 0 {
					rec(nk[0])
				}
				return
			}
			for _, k := range m.Kids {
				if !a.sx.strings[k.Kind] {
					rec(k)
				}
			}
		}
		rec(n)
	}
	strLit := func(n *N) (string, bool) {
		if n == nil || !a.sx.strings[n.Kind] && n.Kind != "encapsed_string" && n.Kind != "interpreted_string_literal" && n.Kind != "raw_string_literal" {
			return "", false
		}
		t := n.text(a.src)
		if len(t) >= 2 {
			t = t[1 : len(t)-1]
		}
		return t, true
	}
	var visit func(n *N, pol bool)
	visit = func(n *N, pol bool) {
		txt := n.text(a.src)
		switch {
		case n.Kind == "parenthesized_expression":
			for _, k := range n.NamedKids() {
				visit(k, pol)
			}
			return
		case n.Kind == "not_operator" || (n.Kind == "unary_expression" || n.Kind == "prefix_expression" || n.Kind == "unary_op_expression") && strings.HasPrefix(txt, "!"):
			nk := n.NamedKids()
			if len(nk) > 0 {
				visit(nk[len(nk)-1], !pol)
			}
			return
		case n.Kind == "boolean_operator" || n.Kind == "binary_expression" || n.Kind == "conjunction_expression" || n.Kind == "disjunction_expression" || n.Kind == "binary_op_expression":
			op := n.op(a.src)
			if op == "and" || op == "&&" {
				if pol == want { // known true: every conjunct is true
					for _, k := range n.NamedKids() {
						visit(k, pol)
					}
				}
				return
			}
			if op == "or" || op == "||" {
				if pol != want { // known false: every disjunct is false (`if !ok1 || !ok2 { return }`)
					for _, k := range n.NamedKids() {
						visit(k, pol)
					}
				}
				return
			}
			if op == "==" || op == "===" || op == "!=" || op == "!==" {
				nk := n.NamedKids()
				eq := op == "==" || op == "==="
				if len(nk) == 2 && (eq == (pol == want)) {
					for i, k := range nk {
						if s, ok := strLit(k); ok && strings.Contains(s, "://") {
							names(nk[1-i])
						}
					}
				}
				return
			}
		case n.Kind == "comparison_operator" && a.fam == "python":
			nk := n.NamedKids()
			op := n.op(a.src)
			if len(nk) == 2 && strings.Contains(op, "in") {
				if _, lit := strLit(nk[1]); !lit && (strings.Contains(op, "not") != (pol == want)) {
					names(nk[0])
				}
			} else if len(nk) == 2 && (op == "==") == (pol == want) && (op == "==" || op == "!=") {
				for i, k := range nk {
					if s, ok := strLit(k); ok && strings.Contains(s, "://") {
						names(nk[1-i])
					}
				}
			}
			return
		case a.sx.calls[n.Kind] && pol == want:
			callee, recv, args, _ := a.callParts(n)
			if memberCalls.MatchString(callee) {
				if recv != nil && len(args) > 0 {
					if _, lit := strLit(recv); !lit {
						names(args[0])
					}
				} else if len(args) >= 2 { // in_array($x, $list), slices.Contains(list, x)
					if strings.HasPrefix(callee, "slices.") {
						names(args[1])
					} else {
						names(args[0])
					}
				} else if len(args) == 1 { // is_safe_url(x)
					names(args[0])
				}
				return
			}
			if prefixCalls.MatchString(callee) {
				var subj, lit *N
				if recv != nil && len(args) > 0 {
					subj, lit = recv, args[0]
				} else if len(args) >= 2 {
					subj, lit = args[0], args[1]
				}
				ct := cond.text(a.src)
				if s, ok := strLit(lit); ok && subj != nil && (safeURLPrefix.MatchString(s) || s == "/" && (strings.Contains(ct, `"//"`) || strings.Contains(ct, `'//'`))) {
					names(subj)
				}
				return
			}
		case (n.Kind == "index_expression" || n.Kind == "subscript") && pol == want: // Go: allowed[host]
			if obj, key := a.subscriptParts(n); obj != nil && key != nil {
				names(key)
			}
			return
		}
	}
	visit(cond, true)
	return out
}

// numericCalls test that a value is a number; a value that passed such a check carries no
// injection payload.
var numericCalls = regexp.MustCompile(`^(is_numeric|ctype_digit|is_int|is_float|Number\.isInteger|Number\.isSafeInteger|Number\.isFinite|StringUtils\.isNumeric|NumberUtils\.isDigits|NumberUtils\.isCreatable)$|(^|\.)(isdigit|isnumeric|isdecimal)$`)

type numTarget struct {
	name   string
	key    string
	hasKey bool
}

func (g numTarget) clear(e *env) {
	if !g.hasKey {
		if _, ok := e.vars[g.name]; ok {
			e.vars[g.name] = val{}
		}
		return
	}
	m := e.keys[g.name]
	if m == nil {
		m = map[string]val{}
		e.keys[g.name] = m
	}
	m[g.key] = val{}
}

// numericVars lists the variables / constant-index elements a condition proves numeric when it
// evaluates to want (conjuncts when true, negated disjuncts when false).
func (a *analyzer) numericVars(cond *N, want bool, e *env) []numTarget {
	var out []numTarget
	target := func(x *N) {
		for x != nil && x.Kind == "parenthesized_expression" || x != nil && (x.Kind == "argument" || x.Kind == "value_argument") && len(x.NamedKids()) == 1 {
			x = x.NamedKids()[0]
		}
		if x == nil {
			return
		}
		if a.sx.idents[x.Kind] || x.Kind == "variable_name" {
			out = append(out, numTarget{name: norm(x.text(a.src))})
			return
		}
		if x.Kind == "subscript_expression" || x.Kind == "subscript" || x.Kind == "element_reference" || x.Kind == "index_expression" {
			if obj, key := a.subscriptParts(x); obj != nil && key != nil {
				if k, ok := a.constEval(key, e); ok {
					out = append(out, numTarget{name: norm(obj.text(a.src)), key: keyStr(k), hasKey: true})
				}
			}
		}
	}
	var visit func(n *N, pol bool)
	visit = func(n *N, pol bool) {
		txt := n.text(a.src)
		switch {
		case n.Kind == "parenthesized_expression":
			for _, k := range n.NamedKids() {
				visit(k, pol)
			}
		case n.Kind == "not_operator" || (n.Kind == "unary_expression" || n.Kind == "prefix_expression" || n.Kind == "unary_op_expression") && strings.HasPrefix(txt, "!"):
			if nk := n.NamedKids(); len(nk) > 0 {
				visit(nk[len(nk)-1], !pol)
			}
		case n.Kind == "boolean_operator" || n.Kind == "binary_expression" || n.Kind == "conjunction_expression" || n.Kind == "disjunction_expression":
			op := n.op(a.src)
			if (op == "and" || op == "&&") && pol == want || (op == "or" || op == "||") && pol != want {
				for _, k := range n.NamedKids() {
					visit(k, pol)
				}
			}
		case a.sx.calls[n.Kind] && pol == want:
			callee, recv, args, _ := a.callParts(n)
			if !numericCalls.MatchString(callee) {
				return
			}
			if strings.HasSuffix(callee, "isdigit") || strings.HasSuffix(callee, "isnumeric") || strings.HasSuffix(callee, "isdecimal") {
				if recv != nil && len(args) == 0 {
					target(recv)
				}
				return
			}
			if len(args) == 1 {
				target(args[0])
			}
		}
	}
	visit(cond, true)
	return out
}

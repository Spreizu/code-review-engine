package taint

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// norm strips whitespace, unifies member operators (-> :: ?. ?->) to "." and collapses the
// contents of every parenthesised group to "()" so callees read like `Runtime.getRuntime().exec`.
func norm(s string) string {
	if len(s) > 2000 {
		s = s[:2000]
	}
	var b strings.Builder
	depth := 0
	var quote byte
	for i := 0; i < len(s); i++ {
		c := s[i]
		if quote != 0 {
			if c == '\\' {
				i++
				continue
			}
			if c == quote {
				quote = 0
			}
			if depth == 0 {
				b.WriteByte(c)
			}
			continue
		}
		switch c {
		case '"', '\'', '`':
			quote = c
			if depth == 0 {
				b.WriteByte(c)
			}
			continue
		case '(':
			if depth == 0 {
				b.WriteByte('(')
			}
			depth++
			continue
		case ')':
			if depth > 0 {
				depth--
				if depth == 0 {
					b.WriteByte(')')
				}
			}
			continue
		case ' ', '\t', '\n', '\r':
			continue
		}
		if depth == 0 {
			b.WriteByte(c)
		}
	}
	r := b.String()
	r = strings.ReplaceAll(r, "?->", ".")
	r = strings.ReplaceAll(r, "->", ".")
	r = strings.ReplaceAll(r, "::", ".")
	r = strings.ReplaceAll(r, "?.", ".")
	return r
}

func (a *analyzer) why(n *N) string {
	return fmt.Sprintf("line %d: %s", n.Row+1, firstLine(strings.TrimSpace(n.text(a.src))))
}

func (a *analyzer) isSource(n *N, normed string) bool {
	if a.l.context != nil && a.collect && a.phase == 0 && a.l.context.MatchString(normed) {
		a.srcFn[a.cur] = true
	}
	for _, s := range a.l.sources {
		if s.re.MatchString(normed) && (s.file == nil || s.file.MatchString(a.file)) {
			if a.collect && a.phase == 0 {
				a.srcFn[a.cur] = true
			}
			return true
		}
	}
	return false
}

var cmpOps = map[string]bool{"==": true, "!=": true, "===": true, "!==": true, "<": true, ">": true, "<=": true, ">=": true,
	"&&": true, "||": true, "instanceof": true, "in": true, "not in": true, "is": true, "is not": true, "<>": true, "<=>": true,
	"and": false, "or": false, "!in": true, "!is": true}

func (a *analyzer) eval(n *N, e *env) val {
	if n == nil {
		return val{}
	}
	if a.budget--; a.budget < 0 {
		return val{}
	}
	sx := a.sx
	switch {
	case sx.funcs[n.Kind]:
		return val{}
	case sx.assigns[n.Kind]:
		return a.assign(n, e)
	case sx.calls[n.Kind] || sx.news[n.Kind] || sx.pseudo[n.Kind] != "":
		return a.call(n, e)
	case sx.ternaries[n.Kind] || (sx.ifs[n.Kind] && a.fam == "kotlin"):
		return a.ternary(n, e)
	case sx.compare[n.Kind]:
		a.evalKids(n, e)
		return val{}
	case n.Kind == "binary_expression" || n.Kind == "boolean_operator" || n.Kind == "comparison_expression" || n.Kind == "equality_expression" || n.Kind == "conjunction_expression" || n.Kind == "disjunction_expression":
		op := ""
		if o := n.F("operator"); o != nil {
			op = o.text(a.src)
		} else {
			op = n.op(a.src)
		}
		v := a.evalKids(n, e)
		if cmpOps[op] || n.Kind == "comparison_expression" || n.Kind == "equality_expression" || n.Kind == "conjunction_expression" || n.Kind == "disjunction_expression" {
			return val{}
		}
		return v
	case n.Kind == "unary_expression" || n.Kind == "not_operator" || n.Kind == "prefix_expression" || n.Kind == "unary_op_expression":
		v := a.evalKids(n, e)
		if op := n.op(a.src); op == "!" || op == "not" || op == "-" || op == "+" || op == "~" {
			return val{}
		}
		return v
	case sx.casts[n.Kind]:
		v := a.evalKids(n, e)
		if t := n.F("type"); t != nil && primitive(t.text(a.src)) {
			return val{}
		}
		if a.fam == "php" {
			if strings.Contains(n.text(a.src), "(int") || strings.Contains(n.text(a.src), "(float") || strings.Contains(n.text(a.src), "(bool") {
				return val{}
			}
		}
		if a.fam == "kotlin" {
			nk := n.NamedKids()
			if len(nk) == 2 && primitive(nk[1].text(a.src)) {
				return val{}
			}
		}
		return v
	case sx.idents[n.Kind]:
		name := n.text(a.src)
		if a.isSource(n, name) {
			return val{all, a.why(n)}
		}
		return e.container(name) // a whole list/map used as a value carries every entry
	case n.Kind == "subscript" || n.Kind == "subscript_expression" || n.Kind == "index_expression" || n.Kind == "array_access" || n.Kind == "element_reference":
		normed := norm(n.text(a.src))
		if a.isSource(n, normed) {
			a.evalKids(n, e)
			return val{all, a.why(n)}
		}
		obj, key := a.subscriptParts(n)
		ov := a.eval(obj, e)
		a.eval(key, e)
		if obj == nil {
			return ov
		}
		name := norm(obj.text(a.src))
		if k, ok := a.constEval(key, e); ok {
			if l, ok := e.lists[name]; ok && k.kind == 'i' {
				if k.i >= 0 && int(k.i) < len(l) {
					return l[k.i]
				}
				return val{}
			}
			if m, ok := e.keys[name]; ok {
				if v, ok := m[keyStr(k)]; ok {
					return v
				}
				return e.vars[name]
			}
		}
		return ov.or(e.container(name))
	case sx.members[n.Kind]:
		normed := norm(n.text(a.src))
		if a.isSource(n, normed) {
			return val{all, a.why(n)}
		}
		if v, ok := e.vars[normed]; ok {
			return v
		}
		return a.evalKidsNoField(n, e, "field", "name", "property")
	case sx.strings[n.Kind]:
		v := a.evalKids(n, e)
		if a.fam == "kotlin" { // the Kotlin grammar splits "$name" templates into plain string_content nodes
			for _, m := range ktTemplate.FindAllStringSubmatch(n.text(a.src), -1) {
				if x, ok := e.vars[m[1]]; ok {
					v = v.or(x)
				}
			}
		}
		return v
	case n.Kind == "lambda" || n.Kind == "lambda_expression" || n.Kind == "arrow_function" || n.Kind == "lambda_literal":
		return val{}
	case n.Kind == "as_pattern" || n.Kind == "with_item":
		if n.Kind == "with_item" {
			return a.eval(n.F("value"), e)
		}
		nk := n.NamedKids()
		if len(nk) == 0 {
			return val{}
		}
		v := a.eval(nk[0], e)
		if al := n.F("alias"); al != nil {
			for _, id := range a.patternNames(al) {
				e.vars[id] = v
			}
		}
		return v
	case n.Kind == "keyword_argument" || n.Kind == "pair" || n.Kind == "argument" || n.Kind == "value_argument" || n.Kind == "spread_element":
		if v := n.F("value"); v != nil {
			return a.eval(v, e)
		}
		return a.evalKids(n, e)
	}
	return a.evalKids(n, e)
}

var ktTemplate = regexp.MustCompile(`(?:^|[^\\])\$([A-Za-z_]\w*)`)

func primitive(t string) bool {
	switch strings.TrimSpace(t) {
	case "int", "long", "short", "byte", "double", "float", "boolean", "char", "Int", "Long", "Short", "Byte", "Double", "Float", "Boolean", "Char", "Integer":
		return true
	}
	return false
}

func (a *analyzer) evalKids(n *N, e *env) val {
	var v val
	for _, k := range n.Kids {
		if k.Named {
			v = v.or(a.eval(k, e))
		}
	}
	return v
}

func (a *analyzer) evalKidsNoField(n *N, e *env, skip ...string) val {
	var v val
	for _, k := range n.Kids {
		if !k.Named {
			continue
		}
		s := false
		for _, f := range skip {
			if k.Field == f {
				s = true
			}
		}
		if s {
			continue
		}
		v = v.or(a.eval(k, e))
	}
	return v
}

func (a *analyzer) ternary(n *N, e *env) val {
	cond := n.F("condition")
	var branches []*N
	if n.Kind == "conditional_expression" && a.fam == "python" {
		nk := n.NamedKids()
		if len(nk) == 3 {
			cond = nk[1]
			branches = []*N{nk[0], nk[2]}
		}
	} else {
		for _, k := range n.NamedKids() {
			if k != cond {
				branches = append(branches, k)
			}
		}
	}
	a.eval(cond, e)
	if c, ok := a.constEval(cond, e); ok && len(branches) == 2 {
		if c.truthy() {
			return a.branchVal(branches[0], e)
		}
		return a.branchVal(branches[1], e)
	}
	var v val
	for _, b := range branches {
		v = v.or(a.branchVal(b, e))
	}
	return v
}

func (a *analyzer) branchVal(b *N, e *env) val {
	if a.isBlock(b) || b.Kind == "control_structure_body" {
		nk := b.NamedKids()
		for _, k := range nk[:max(0, len(nk)-1)] {
			a.walk(k, e)
		}
		if len(nk) > 0 {
			return a.branchVal(nk[len(nk)-1], e)
		}
		return val{}
	}
	return a.eval(b, e)
}

// callParts returns the callee text node(s), receiver and arguments of a call node.
func (a *analyzer) callParts(n *N) (callee string, recv *N, args []*N, kwargs []*N) {
	src := a.src
	argList := func(al *N) {
		if al == nil {
			return
		}
		for _, k := range al.NamedKids() {
			switch k.Kind {
			case "keyword_argument":
				kwargs = append(kwargs, k)
			case "value_argument", "argument":
				if k.F("name") != nil {
					kwargs = append(kwargs, k)
				} else {
					args = append(args, k)
				}
			default:
				args = append(args, k)
			}
		}
	}
	if p := a.sx.pseudo[n.Kind]; p != "" {
		for _, k := range n.NamedKids() {
			args = append(args, k)
		}
		return p, nil, args, nil
	}
	switch a.fam {
	case "java":
		if n.Kind == "object_creation_expression" {
			callee = "new " + norm(n.F("type").text(src))
		} else {
			o := n.F("object")
			callee = n.F("name").text(src)
			if o != nil {
				callee = norm(o.text(src)) + "." + callee
				recv = o
			}
		}
		argList(n.F("arguments"))
	case "kotlin":
		nk := n.NamedKids()
		if len(nk) == 0 {
			return
		}
		fn := nk[0]
		callee = norm(fn.text(src))
		if fn.Kind == "navigation_expression" {
			if fk := fn.NamedKids(); len(fk) > 0 {
				recv = fk[0]
			}
		}
		for _, k := range nk[1:] {
			if k.Kind == "value_arguments" {
				argList(k)
			} else if k.Kind == "call_suffix" {
				argList(k.Child("value_arguments"))
			}
		}
	case "python":
		fn := n.F("function")
		callee = norm(fn.text(src))
		if fn.Kind == "attribute" {
			recv = fn.F("object")
		}
		argList(n.F("arguments"))
	case "javascript":
		if n.Kind == "new_expression" {
			callee = "new " + norm(n.F("constructor").text(src))
		} else {
			fn := n.F("function")
			callee = norm(fn.text(src))
			if fn.Kind == "member_expression" {
				recv = fn.F("object")
			}
		}
		argList(n.F("arguments"))
	case "php":
		switch n.Kind {
		case "object_creation_expression":
			for _, k := range n.NamedKids() {
				if k.Kind == "name" || k.Kind == "qualified_name" {
					callee = "new " + norm(k.text(src))
				}
				if k.Kind == "arguments" {
					argList(k)
				}
			}
			return
		case "member_call_expression", "nullsafe_member_call_expression":
			recv = n.F("object")
			callee = norm(recv.text(src)) + "." + n.F("name").text(src)
		case "scoped_call_expression":
			callee = norm(n.F("scope").text(src)) + "." + n.F("name").text(src)
		default:
			callee = norm(n.F("function").text(src))
		}
		argList(n.F("arguments"))
	case "go":
		fn := n.F("function")
		callee = norm(fn.text(src))
		if fn.Kind == "selector_expression" {
			recv = fn.F("operand")
		}
		argList(n.F("arguments"))
	}
	return
}

var indexOnly = map[string]bool{"slice": true, "substring": true, "substr": true, "subSequence": true, "subList": true,
	"at": true, "charAt": true, "charCodeAt": true, "codePointAt": true, "padStart": true, "padEnd": true, "repeat": true}

func lastSeg(callee string) string {
	if i := strings.LastIndexByte(callee, '.'); i >= 0 {
		return callee[i+1:]
	}
	return callee
}

func (a *analyzer) call(n *N, e *env) val {
	callee, recv, args, kwargs := a.callParts(n)
	if callee == "" {
		return a.evalKids(n, e)
	}
	var rv val
	if recv != nil {
		rv = a.eval(recv, e)
	}
	avs := make([]val, len(args))
	var au val
	for i, x := range args {
		avs[i] = a.eval(x, e)
		au = au.or(avs[i])
	}
	var ku val
	for _, x := range kwargs {
		ku = ku.or(a.eval(x, e))
	}
	// trailing lambdas etc. are not evaluated as values
	full := ""
	fullOnce := func() string {
		if full == "" {
			t := n.text(a.src)
			if len(t) > 600 {
				t = t[:600]
			}
			full = strings.Join(strings.Fields(t), "")
		}
		return full
	}
	normed := callee + "()"
	if a.sx.news[n.Kind] {
		normed = callee + "()"
	}
	// 1. sources (request.args.get("n", type=int) converts the value: not a string any more)
	if a.isSource(n, normed) {
		if a.fam == "python" {
			for _, k := range kwargs {
				if nm := k.F("name"); nm != nil && nm.text(a.src) == "type" {
					if v := k.F("value"); v != nil && regexp.MustCompile(`^(int|float|bool)$`).MatchString(v.text(a.src)) {
						return val{}
					}
				}
			}
		}
		return val{all, a.why(n)}
	}
	// 2. sinks
	if a.collect {
		for _, s := range a.l.sinks {
			if s.callee == nil || !s.callee.MatchString(callee) {
				continue
			}
			if s.file != nil && !s.file.MatchString(a.file) || s.unlessFil != nil && s.unlessFil.MatchString(a.file) {
				continue
			}
			if s.when != nil && !s.when.MatchString(fullOnce()) || s.unless != nil && s.unless.MatchString(fullOnce()) {
				continue
			}
			if s.unlessFn != nil && a.cur != nil && s.unlessFn.MatchString(a.cur.text(a.src)) {
				continue
			}
			if s.unlessPar != nil && n.Parent != nil {
				pt := n.Parent.text(a.src)
				if len(pt) > 600 {
					pt = pt[:600]
				}
				if s.unlessPar.MatchString(strings.Join(strings.Fields(pt), "")) {
					continue
				}
			}
			var v val
			if len(s.args) == 0 {
				v = au.or(ku)
				if a.sx.news[n.Kind] || a.sx.pseudo[n.Kind] != "" {
					v = au.or(ku)
				}
			} else {
				for _, i := range s.args {
					if i >= 0 && i < len(avs) && a.fam == "python" && args[i].Kind == "tuple" {
						// make_response((body, headers)): only the body is HTML
						if tk := args[i].NamedKids(); len(tk) > 0 {
							v = v.or(a.eval(tk[0], e))
						}
					} else if i >= 0 && i < len(avs) {
						v = v.or(avs[i])
					} else if i == -1 { // receiver
						v = v.or(rv)
					}
				}
			}
			if v.t&s.class != 0 && s.unlessSrc != nil && s.unlessSrc.MatchString(v.why) {
				continue
			}
			if v.t&s.class != 0 {
				a.hit(s, n, callee, v)
			} else if a.phase == 0 {
				a.cands = append(a.cands, cand{Hit{Class: s.name, Node: n, Sink: callee, Evidence: "sink argument not derived from the function's untrusted input"}, a.cur})
			}
		}
	}
	m := lastSeg(callee)
	// 3a. x.replace("'", ...) / str_replace("<", ...): removing a metacharacter neutralises the
	// contexts that depend on it (quotes: SQL/XPath/LDAP string literals; "<": HTML; "..": paths)
	if (m == "replace" || m == "replaceAll" || m == "ReplaceAll" || m == "str_replace") && len(args) >= 2 {
		lit := args[0]
		if m == "ReplaceAll" && strings.HasPrefix(callee, "strings.") && len(args) == 3 {
			lit = args[1]
		}
		if c, ok := a.constEval(lit, e); ok && c.kind == 's' {
			var mask T
			if strings.ContainsAny(c.s, `'"`) {
				mask |= classBit("sqli") | classBit("xpath") | classBit("ldap")
			}
			if strings.Contains(c.s, "<") {
				mask |= classBit("xss")
			}
			if strings.Contains(c.s, "..") {
				mask |= classBit("path")
			}
			if mask != 0 {
				v := au.or(rv).or(ku)
				v.t &^= mask
				return v
			}
		}
	}
	// 3. sanitizers
	// every matching sanitizer applies (re.escape is both an "escape" and a regex escaper)
	var smask T
	sanitized := false
	for _, s := range a.l.sanitizers {
		if s.re.MatchString(callee) {
			smask |= s.mask
			sanitized = true
		}
	}
	if sanitized {
		v := au.or(rv).or(ku)
		v.t &^= smask
		return v
	}
	// 4. containers with literal keys / indexes
	if recv != nil && (a.sx.idents[recv.Kind] || a.sx.members[recv.Kind] && !strings.Contains(recv.text(a.src), "(")) {
		name := norm(recv.text(a.src))
		lst, isList := e.lists[name]
		var k0 cv
		k0ok := false
		if len(args) > 0 {
			k0, k0ok = a.constEval(args[0], e)
		}
		switch {
		case isList && (m == "add" || m == "append" || m == "push" || m == "addLast" || m == "offer") && len(args) == 1:
			e.lists[name] = append(lst, avs[0])
			return val{}
		case isList && (m == "add" || m == "insert") && len(args) == 2 && k0ok && k0.kind == 'i' && int(k0.i) <= len(lst) && k0.i >= 0:
			l := append(append(append([]val(nil), lst[:k0.i]...), avs[1]), lst[k0.i:]...)
			e.lists[name] = l
			return val{}
		case isList && (m == "remove" || m == "pop" || m == "removeAt") && len(args) == 1 && k0ok && k0.kind == 'i' && k0.i >= 0 && int(k0.i) < len(lst):
			r := lst[k0.i]
			e.lists[name] = append(append([]val(nil), lst[:k0.i]...), lst[k0.i+1:]...)
			return r
		case isList && (m == "get" || m == "elementAt") && len(args) == 1 && k0ok && k0.kind == 'i':
			if k0.i >= 0 && int(k0.i) < len(lst) {
				return lst[k0.i]
			}
			return val{}
		case isList && (m == "size" || m == "isEmpty" || m == "length" || m == "count"):
			return val{}
		case isList && (m == "addAll" || m == "extend" || m == "set" || m == "clear" || m == "remove" || m == "pop" || m == "shift" || m == "poll"):
			u := e.container(name).or(au)
			delete(e.lists, name)
			e.vars[name] = u
			if m == "clear" {
				e.vars[name] = val{}
			}
			return u
		case m == "set" && len(args) == 3 && k0ok: // section + key (configparser and similar)
			if k1, ok := a.constEval(args[1], e); ok {
				mm := e.keys[name]
				if mm == nil {
					mm = map[string]val{}
					e.keys[name] = mm
				}
				mm[keyStr(k0)+"\x00"+keyStr(k1)] = avs[2]
				return val{}
			}
		case m == "get" && len(args) >= 2 && k0ok && e.keys[name] != nil:
			if k1, ok := a.constEval(args[1], e); ok {
				if v, ok := e.keys[name][keyStr(k0)+"\x00"+keyStr(k1)]; ok {
					return v
				}
			}
		case (m == "put" || m == "setdefault" || m == "putIfAbsent" || m == "setAttribute" || m == "set") && len(args) == 2 && k0ok:
			mm := e.keys[name]
			if mm == nil {
				mm = map[string]val{}
				e.keys[name] = mm
			}
			mm[keyStr(k0)] = avs[1]
			return val{}
		case (m == "get" || m == "getOrDefault" || m == "getAttribute" || m == "getProperty" || m == "opt" || m == "optString" || m == "getString") && len(args) >= 1 && k0ok:
			if mm, ok := e.keys[name]; ok {
				if v, ok := mm[keyStr(k0)]; ok {
					return v
				}
				v := e.vars[name]
				if len(args) > 1 {
					v = v.or(avs[1])
				}
				return v
			}
		case isList:
			// iteration helpers and anything else: the list's union
			return e.container(name).or(au)
		}
		if a.l.mutators != nil && a.l.mutators.MatchString(m) && (au.or(ku)).t != 0 {
			e.vars[name] = e.vars[name].or(au).or(ku)
		}
		if _, ok := e.keys[name]; ok && rv.t == 0 {
			rv = e.container(name)
		}
	}
	// 5. same-file summaries
	if s, ok := a.summ[m]; ok && a.local(recv) {
		v := au.or(ku)
		v.t &= s.withParams
		if s.own != 0 {
			v = v.or(val{s.own, a.why(n)})
			if s.own != 0 && a.collect && a.phase == 0 {
				a.srcFn[a.cur] = true
			}
		}
		return v
	}
	// 6a. index/length arguments select part of the receiver; they do not flow into the result
	// (names.slice(from, to) is the receiver's data, whatever from and to are)
	if recv != nil && indexOnly[m] {
		return rv
	}
	// 6. default: the result carries the taint of the receiver and the arguments
	// (Flask make_response((body, headers)): the response body is only the first tuple element)
	if a.fam == "python" && len(args) > 0 && args[0].Kind == "tuple" && regexp.MustCompile(`(^|\.)make_response$`).MatchString(callee) {
		if tk := args[0].NamedKids(); len(tk) > 0 {
			return a.eval(tk[0], e).or(rv)
		}
	}
	return au.or(rv).or(ku)
}

func (a *analyzer) local(recv *N) bool {
	if recv == nil {
		return true
	}
	t := recv.text(a.src)
	switch t {
	case "this", "self", "$this", "static", "super", "cls":
		return true
	}
	if a.sx.news[recv.Kind] {
		return true
	}
	return false
}

// ---- constant folding (conditions, ternaries, switch subjects, keys)

func (a *analyzer) constEval(n *N, e *env) (cv, bool) {
	if n == nil {
		return cv{}, false
	}
	sx := a.sx
	t := n.text(a.src)
	switch {
	case sx.numbers[n.Kind]:
		t = strings.TrimRight(strings.ReplaceAll(t, "_", ""), "lLuU")
		i, err := strconv.ParseInt(t, 0, 64)
		return cv{kind: 'i', i: i}, err == nil
	case sx.trues[n.Kind]:
		if a.fam == "php" {
			return cv{kind: 'b', b: strings.EqualFold(t, "true")}, true
		}
		return cv{kind: 'b', b: true}, true
	case sx.falses[n.Kind]:
		return cv{kind: 'b'}, true
	case sx.strings[n.Kind]:
		for _, k := range n.Kids {
			if k.Named && (strings.Contains(k.Kind, "interpolation") || strings.Contains(k.Kind, "substitution") || sx.idents[k.Kind] || k.Kind == "escape_sequence" && false) {
				return cv{}, false
			}
		}
		s := t
		for _, p := range []string{`"""`, `'''`, `"`, `'`, "`"} {
			if len(s) >= 2*len(p) && strings.HasPrefix(s, p) && strings.HasSuffix(s, p) {
				s = s[len(p) : len(s)-len(p)]
				break
			}
		}
		if strings.ContainsAny(s, `\$`) && a.fam != "python" {
			if a.fam == "php" && strings.HasPrefix(t, "'") {
				return cv{kind: 's', s: s}, true
			}
			if strings.Contains(s, "$") && (a.fam == "php" || a.fam == "kotlin") {
				return cv{}, false
			}
		}
		return cv{kind: 's', s: s}, true
	case n.Kind == "parenthesized_expression" || n.Kind == "parenthesized" || n.Kind == "condition" || n.Kind == "when_subject":
		nk := n.NamedKids()
		if len(nk) == 1 {
			return a.constEval(nk[0], e)
		}
	case sx.idents[n.Kind]:
		c, ok := e.consts[t]
		return c, ok
	case n.Kind == "subscript" || n.Kind == "subscript_expression" || n.Kind == "index_expression" || n.Kind == "element_reference":
		obj, key := a.subscriptParts(n)
		if obj == nil || key == nil {
			return cv{}, false
		}
		oc, ok1 := a.constEval(obj, e)
		kc, ok2 := a.constEval(key, e)
		if ok1 && ok2 && oc.kind == 's' && kc.kind == 'i' && kc.i >= 0 && int(kc.i) < len(oc.s) {
			return cv{kind: 's', s: oc.s[kc.i : kc.i+1]}, true
		}
		return cv{}, false
	case n.Kind == "unary_expression" || n.Kind == "not_operator" || n.Kind == "prefix_expression":
		nk := n.NamedKids()
		if len(nk) != 1 {
			return cv{}, false
		}
		c, ok := a.constEval(nk[0], e)
		if !ok {
			return c, false
		}
		switch n.op(a.src) {
		case "!", "not":
			return cv{kind: 'b', b: !c.truthy()}, true
		case "-":
			if c.kind == 'i' {
				return cv{kind: 'i', i: -c.i}, true
			}
		}
	case n.Kind == "binary_expression" || n.Kind == "binary_operator" || n.Kind == "comparison_operator" || n.Kind == "boolean_operator" || n.Kind == "comparison_expression" || n.Kind == "equality_expression" || n.Kind == "additive_expression" || n.Kind == "multiplicative_expression" || n.Kind == "conjunction_expression" || n.Kind == "disjunction_expression":
		nk := n.NamedKids()
		if len(nk) != 2 {
			return cv{}, false
		}
		op := ""
		if o := n.F("operator"); o != nil {
			op = o.text(a.src)
		} else {
			var parts []string
			for _, k := range n.Kids {
				if !k.Named {
					parts = append(parts, k.text(a.src))
				}
			}
			op = strings.Join(parts, " ")
		}
		l, ok1 := a.constEval(nk[0], e)
		r, ok2 := a.constEval(nk[1], e)
		if !ok1 || !ok2 {
			return cv{}, false
		}
		return binop(op, l, r)
	case n.Kind == "method_invocation" && a.fam == "java":
		// "ABC".charAt(2) and friends on constants
		o := n.F("object")
		name := n.F("name")
		if o == nil || name == nil {
			return cv{}, false
		}
		oc, ok := a.constEval(o, e)
		if !ok || oc.kind != 's' {
			return cv{}, false
		}
		args := n.F("arguments").NamedKids()
		switch name.text(a.src) {
		case "charAt":
			if len(args) == 1 {
				if ic, ok := a.constEval(args[0], e); ok && ic.kind == 'i' && ic.i >= 0 && int(ic.i) < len(oc.s) {
					return cv{kind: 's', s: oc.s[ic.i : ic.i+1]}, true
				}
			}
		case "length":
			return cv{kind: 'i', i: int64(len(oc.s))}, true
		case "contains", "startsWith", "endsWith", "equals":
			if len(args) == 1 {
				if ac, ok := a.constEval(args[0], e); ok && ac.kind == 's' {
					switch name.text(a.src) {
					case "contains":
						return cv{kind: 'b', b: strings.Contains(oc.s, ac.s)}, true
					case "startsWith":
						return cv{kind: 'b', b: strings.HasPrefix(oc.s, ac.s)}, true
					case "endsWith":
						return cv{kind: 'b', b: strings.HasSuffix(oc.s, ac.s)}, true
					default:
						return cv{kind: 'b', b: oc.s == ac.s}, true
					}
				}
			}
		}
	}
	return cv{}, false
}

func binop(op string, l, r cv) (cv, bool) {
	b := func(x bool) (cv, bool) { return cv{kind: 'b', b: x}, true }
	switch op {
	case "&&", "and":
		return b(l.truthy() && r.truthy())
	case "||", "or":
		return b(l.truthy() || r.truthy())
	case "in", "not in":
		if l.kind == 's' && r.kind == 's' {
			return b(strings.Contains(r.s, l.s) == (op == "in"))
		}
		return cv{}, false
	}
	if l.kind == 'i' && r.kind == 'i' {
		x, y := l.i, r.i
		switch op {
		case "+":
			return cv{kind: 'i', i: x + y}, true
		case "-":
			return cv{kind: 'i', i: x - y}, true
		case "*":
			return cv{kind: 'i', i: x * y}, true
		case "/", "//":
			if y == 0 {
				return cv{}, false
			}
			return cv{kind: 'i', i: x / y}, true
		case "%":
			if y == 0 {
				return cv{}, false
			}
			return cv{kind: 'i', i: x % y}, true
		case ">":
			return b(x > y)
		case "<":
			return b(x < y)
		case ">=":
			return b(x >= y)
		case "<=":
			return b(x <= y)
		case "==", "===":
			return b(x == y)
		case "!=", "!==", "<>":
			return b(x != y)
		}
		return cv{}, false
	}
	if l.kind == 's' && r.kind == 's' {
		switch op {
		case "+", ".":
			return cv{kind: 's', s: l.s + r.s}, true
		case "==", "===":
			return b(l.s == r.s)
		case "!=", "!==":
			return b(l.s != r.s)
		}
	}
	if l.kind == 'b' && r.kind == 'b' {
		switch op {
		case "==", "===":
			return b(l.b == r.b)
		case "!=", "!==":
			return b(l.b != r.b)
		}
	}
	return cv{}, false
}

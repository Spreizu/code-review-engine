package types

import (
	"strings"
	"unicode"
)

// stringMethods return a string when called on a string (per language family).
var stringMethods = map[string]map[string]bool{
	"java":   set("substring trim strip stripLeading stripTrailing toUpperCase toLowerCase replace replaceAll replaceFirst concat repeat formatted intern toString indent translateEscapes"),
	"kotlin": set("substring trim trimStart trimEnd uppercase lowercase replace repeat padStart padEnd removePrefix removeSuffix toString reversed"),
	"python": set("strip lstrip rstrip lower upper title capitalize casefold replace format join center ljust rjust zfill swapcase expandtabs removeprefix removesuffix"),
	"js":     set("trim trimStart trimEnd toUpperCase toLowerCase replace replaceAll slice substring substr concat repeat padStart padEnd normalize toString at charAt"),
	"php":    {},
	"go":     {},
}

var pyBuiltinTypes = set("str int float list dict set tuple bytes bytearray bool frozenset complex")

func set(s string) map[string]bool {
	m := map[string]bool{}
	for _, w := range strings.Fields(s) {
		m[w] = true
	}
	return m
}

// At returns the smallest node spanning [s,e).
func (f *File) At(s, e uint32) *N {
	n := f.Root
	for {
		var next *N
		for _, k := range n.Kids {
			if k.S <= s && e <= k.E && (k.E-k.S) <= (n.E-n.S) {
				next = k
				break
			}
		}
		if next == nil || next == n {
			return n
		}
		n = next
	}
}

// TypeAt resolves the type of the expression spanning [s,e).
func (f *File) TypeAt(s, e uint32) string {
	n := f.At(s, e)
	// prefer the outermost node with exactly this span (a call, not its callee)
	for n.Parent != nil && n.Parent.S == n.S && n.Parent.E == n.E {
		n = n.Parent
	}
	return f.TypeOf(n)
}

// TypeOf resolves an expression node; "" = unknown.
func (f *File) TypeOf(n *N) string {
	if n == nil || f.busy[n] {
		return ""
	}
	f.busy[n] = true
	defer delete(f.busy, n)
	c := canon[f.Lang]
	k := n.Kind
	switch k {
	case "parenthesized_expression", "expression_statement", "await_expression", "non_null_expression":
		if kids := n.NamedKids(); len(kids) == 1 {
			return f.TypeOf(kids[0])
		}
		return ""
	case "string_literal", "string", "template_string", "interpreted_string_literal", "raw_string_literal",
		"encapsed_string", "line_string_literal", "multi_line_string_literal", "text_block", "concatenated_string", "heredoc", "nowdoc":
		if f.Lang == "python" && strings.HasPrefix(strings.ToLower(f.text(n)), "b") {
			return "bytes"
		}
		return c[0]
	case "decimal_integer_literal", "hex_integer_literal", "integer", "integer_literal", "int_literal", "number", "number_literal":
		return c[1]
	case "decimal_floating_point_literal", "float", "float_literal", "real_literal":
		return c[2]
	case "true", "false", "boolean", "boolean_literal":
		return c[3]
	case "list", "array", "array_creation_expression", "list_comprehension", "array_initializer":
		return c[4]
	case "dictionary", "dictionary_comprehension":
		return "dict"
	case "set", "set_comprehension":
		return "set"
	case "tuple":
		return "tuple"
	case "object":
		if f.Lang == "js" {
			return "Object"
		}
	case "composite_literal":
		return Norm(f.text(n.F("type")))
	case "unary_expression":
		if f.Lang == "go" && strings.HasPrefix(f.text(n), "&") {
			return f.TypeOf(n.F("operand"))
		}
	case "object_creation_expression":
		if t := n.F("type"); t != nil {
			return Norm(f.text(t))
		}
		if t := n.Child("name", "qualified_name"); t != nil {
			return Norm(f.text(t))
		}
	case "new_expression":
		return Norm(f.text(n.F("constructor")))
	case "cast_expression", "as_expression", "type_assertion", "type_assertion_expression", "type_conversion_expression":
		return f.castType(n)
	case "binary_expression", "additive_expression":
		if f.Lang == "java" || f.Lang == "js" || f.Lang == "kotlin" {
			if strings.Contains(f.text(n)[len(f.text(n.F("left"))):], "+") || k == "additive_expression" {
				l, r := n.F("left"), n.F("right")
				if l == nil || r == nil {
					kids := n.NamedKids()
					if len(kids) == 2 {
						l, r = kids[0], kids[1]
					}
				}
				if f.TypeOf(l) == c[0] || f.TypeOf(r) == c[0] {
					return c[0]
				}
			}
		}
	case "ternary_expression", "conditional_expression":
		kids := n.NamedKids()
		if len(kids) == 3 {
			a, b := f.TypeOf(kids[1]), f.TypeOf(kids[2])
			if f.Lang == "python" {
				a, b = f.TypeOf(kids[0]), f.TypeOf(kids[2])
			}
			if a == b {
				return a
			}
		}
	case "this", "self":
		return f.className(classOf(n))
	case "identifier", "simple_identifier", "variable_name":
		name := f.text(n)
		if (name == "self" || name == "$this") && classOf(n) != nil {
			return f.className(classOf(n))
		}
		return f.lookup(name, n)
	case "field_access", "attribute", "member_expression", "member_access_expression", "selector_expression", "navigation_expression":
		obj, field := f.objField(n)
		return f.fieldType(f.TypeOf(obj), f.text(field), f.text(obj))
	case "method_invocation", "call", "call_expression", "member_call_expression", "function_call_expression":
		return f.callType(n)
	}
	// wrapper nodes (value_argument, expression, argument) with one child of the same span
	if kids := n.NamedKids(); len(kids) == 1 && kids[0].S == n.S && kids[0].E == n.E {
		return f.TypeOf(kids[0])
	}
	return ""
}

// objField splits a member access into receiver and member nodes.
func (f *File) objField(n *N) (*N, *N) {
	switch n.Kind {
	case "field_access":
		return n.F("object"), n.F("field")
	case "attribute":
		return n.F("object"), n.F("attribute")
	case "member_expression":
		return n.F("object"), n.F("property")
	case "member_access_expression", "member_call_expression":
		return n.F("object"), n.F("name")
	case "selector_expression":
		return n.F("operand"), n.F("field")
	case "navigation_expression":
		kids := n.NamedKids()
		if len(kids) == 2 {
			if kids[1].Kind == "identifier" {
				return kids[0], kids[1]
			}
			if s := kids[1].Child("simple_identifier", "identifier"); s != nil {
				return kids[0], s
			}
		}
	}
	return nil, nil
}

func (f *File) fieldType(recv, field, recvText string) string {
	if field == "" {
		return ""
	}
	if f.Lang == "php" && !strings.HasPrefix(field, "$") {
		field = "$" + field
	}
	if field == "length" && f.Lang == "js" && (recv == "Array" || recv == "string") {
		return "number"
	}
	if recv == "" {
		return ""
	}
	if t := f.lookupField(recv, field); t != "" {
		return t
	}
	for _, p := range f.parents(recv) {
		if t := f.lookupField(p, field); t != "" {
			return t
		}
	}
	return ""
}

func (f *File) lookupField(recv, field string) string {
	if ds, ok := f.fields[recv][field]; ok {
		if t := f.agree(ds); t != "" {
			return t
		}
	}
	if f.Project != nil {
		if t := f.Project.fields[recv][field]; t != "" {
			return t
		}
	}
	return ""
}

func (f *File) parents(class string) []string {
	var out []string
	seen := map[string]bool{}
	var walk func(string)
	walk = func(c string) {
		if c == "" || seen[c] {
			return
		}
		seen[c] = true
		for _, p := range f.supers[c] {
			out = append(out, p)
			walk(p)
		}
		if f.Project != nil {
			for _, p := range f.Project.supers[c] {
				out = append(out, p)
				walk(p)
			}
		}
	}
	walk(class)
	return out
}

func (f *File) castType(n *N) string {
	if t := n.F("type"); t != nil {
		return Norm(f.text(t))
	}
	kids := n.NamedKids()
	if len(kids) == 0 {
		return ""
	}
	switch n.Kind {
	case "cast_expression":
		return Norm(f.text(kids[0]))
	default:
		return Norm(f.text(kids[len(kids)-1]))
	}
}

func (f *File) callType(n *N) string {
	c := canon[f.Lang]
	var recv, name *N
	switch n.Kind {
	case "method_invocation":
		recv, name = n.F("object"), n.F("name")
	case "member_call_expression":
		recv, name = n.F("object"), n.F("name")
	case "function_call_expression":
		name = n.F("function")
	case "call", "call_expression":
		fn := n.F("function")
		if fn == nil {
			if kids := n.NamedKids(); len(kids) > 0 {
				fn = kids[0]
			}
		}
		if fn == nil {
			return ""
		}
		switch fn.Kind {
		case "identifier", "simple_identifier":
			name = fn
		default:
			recv, name = f.objField(fn)
		}
	}
	if name == nil {
		return ""
	}
	nm := f.text(name)
	if recv == nil {
		if f.Lang == "python" && pyBuiltinTypes[nm] {
			return nm
		}
		if f.Lang == "go" && (nm == "string") {
			return "string"
		}
		if t, ok := f.funcs[nm]; ok {
			return t
		}
		if c := classOf(n); c != nil && f.Lang != "python" && f.Lang != "js" && f.Lang != "php" {
			cn := f.className(c)
			if t := f.lookupMethod(cn, nm); t != "" { // implicit this.method()
				return t
			}
			for _, p := range f.parents(cn) {
				if t := f.lookupMethod(p, nm); t != "" {
					return t
				}
			}
		}
		if f.Project != nil {
			if t := f.Project.funcs[nm]; t != "" {
				return t
			}
		}
		// Python/Kotlin constructor call: a class defined in this file (or project)
		if (f.Lang == "python" || f.Lang == "kotlin") && nm != "" && unicode.IsUpper(rune(nm[0])) {
			if _, ok := f.fields[nm]; ok {
				return nm
			}
			if _, ok := f.methods[nm]; ok {
				return nm
			}
			if f.Project != nil && (f.Project.fields[nm] != nil || f.Project.methods[nm] != nil) {
				return nm
			}
		}
		return ""
	}
	rt := f.TypeOf(recv)
	if rt == "" {
		return ""
	}
	if rt == c[0] && stringMethods[f.Lang][nm] {
		return c[0]
	}
	if t := f.lookupMethod(rt, nm); t != "" {
		return t
	}
	for _, p := range f.parents(rt) {
		if t := f.lookupMethod(p, nm); t != "" {
			return t
		}
	}
	return knownCall(f.Lang, rt, nm)
}

func (f *File) lookupMethod(recv, name string) string {
	if t, ok := f.methods[recv][name]; ok && t != "" {
		return t
	}
	if f.Project != nil {
		if t := f.Project.methods[recv][name]; t != "" {
			return t
		}
	}
	return ""
}

func knownCall(lang, recv, method string) string {
	switch lang {
	case "java":
		switch recv {
		case "StringBuilder", "StringBuffer":
			switch method {
			case "append", "insert", "delete", "deleteCharAt", "replace", "reverse", "appendCodePoint":
				return recv
			case "toString":
				return "String"
			case "length", "capacity":
				return "int"
			}
		case "Integer", "Long", "Short", "Byte", "Double", "Float", "Boolean", "Character":
			switch method {
			case "toString":
				return "String"
			case "intValue":
				return "int"
			case "longValue":
				return "long"
			case "doubleValue":
				return "double"
			case "floatValue":
				return "float"
			case "booleanValue":
				return "boolean"
			}
		case "Optional":
			switch method {
			case "isPresent", "isEmpty":
				return "boolean"
			}
		case "String":
			if method == "length" {
				return "int"
			}
		}
	case "js":
		if recv == "Array" {
			switch method {
			case "map", "filter", "slice", "concat", "flat", "flatMap", "toSorted", "toReversed", "toSpliced", "with":
				return "Array"
			}
		}
	case "python":
		if method == "copy" && (recv == "list" || recv == "dict" || recv == "set") {
			return recv
		}
	}
	return ""
}

// lookup resolves a variable at a use site: the innermost scope that declares the name wins;
// every declaration of the name in that scope must agree on one type.
func (f *File) lookup(name string, at *N) string {
	ds := f.decls[name]
	if len(ds) == 0 {
		if f.Lang == "java" || f.Lang == "kotlin" {
			if c := classOf(at); c != nil { // implicit this.field
				if t := f.fieldType(f.className(c), name, ""); t != "" {
					return t
				}
			}
		}
		return ""
	}
	for s := scopeOf(at); ; s = scopeOf(s) {
		var in []decl
		for _, d := range ds {
			if d.scope == s {
				in = append(in, d)
			}
		}
		if len(in) > 0 {
			return f.agree(in)
		}
		if s == nil {
			break
		}
		if (f.Lang == "java" || f.Lang == "kotlin") && (s.Kind == "class_body" || s.Kind == "class_declaration") {
			if t := f.fieldType(f.className(classOf(at)), name, ""); t != "" {
				return t
			}
		}
	}
	return ""
}

func (f *File) agree(ds []decl) string {
	t := ""
	for i, d := range ds {
		dt := d.typ
		if dt == "" && d.init != nil {
			dt = d.src.TypeOf(d.init)
		}
		if dt == "" || i > 0 && dt != t {
			return ""
		}
		t = dt
	}
	return t
}

// NewProject collects the class and function facts of files into a cross-file index.
func NewProject(files []*File) *Project {
	p := &Project{fields: map[string]map[string]string{}, methods: map[string]map[string]string{}, funcs: map[string]string{}, supers: map[string][]string{}}
	conflict := map[string]bool{}
	for _, f := range files {
		for cn, fs := range f.fields {
			if p.fields[cn] == nil {
				p.fields[cn] = map[string]string{}
			}
			for fn, ds := range fs {
				t := f.agree(ds)
				if old, ok := p.fields[cn][fn]; ok && old != t {
					t = ""
				}
				p.fields[cn][fn] = t
			}
		}
		for cn, ms := range f.methods {
			if p.methods[cn] == nil {
				p.methods[cn] = map[string]string{}
			}
			for mn, t := range ms {
				if old, ok := p.methods[cn][mn]; ok && old != t {
					t = ""
				}
				p.methods[cn][mn] = t
			}
		}
		for fn, t := range f.funcs {
			if old, ok := p.funcs[fn]; ok && old != t || conflict[fn] {
				conflict[fn], t = true, ""
			}
			p.funcs[fn] = t
		}
		for cn, ps := range f.supers {
			have := map[string]bool{}
			for _, x := range p.supers[cn] {
				have[x] = true
			}
			for _, s := range ps {
				if !have[s] {
					p.supers[cn] = append(p.supers[cn], s)
					have[s] = true
				}
			}
		}
	}
	return p
}

// builtin type groups whose values are never equal to / interchangeable with another group's
var builtinGroups = map[string]map[string]int{
	"python": {"str": 1, "bytes": 2, "bytearray": 2, "int": 3, "float": 3, "bool": 3, "complex": 3, "list": 4, "tuple": 5, "dict": 6, "set": 7, "frozenset": 7},
	"js":     {"string": 1, "number": 2, "boolean": 3, "Array": 4},
	"java":   {"String": 1, "int": 2, "long": 2, "double": 2, "float": 2, "short": 2, "byte": 2, "boolean": 3, "char": 2},
	"kotlin": {"String": 1, "Int": 2, "Long": 2, "Double": 2, "Float": 2, "Boolean": 3},
	"php":    {},
	"go":     {"string": 1, "int": 2, "float64": 2, "bool": 3},
}

// Incompatible: a and b are both known built-in types of different groups.
func Incompatible(lang, a, b string) bool {
	g := builtinGroups[family(lang)]
	ga, gb := g[a], g[b]
	return ga != 0 && gb != 0 && ga != gb
}

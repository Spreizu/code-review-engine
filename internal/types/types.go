// Package types is crev's built-in, syntax-only type resolver. Given an expression node it answers
// "what is this value's declared or obvious type?" from what the file itself says: literals,
// constructor calls, declared types of locals/parameters/fields, annotated or literal-initialised
// Python/TS/Kotlin/Go variables, this/self fields, string methods, and the declared return types
// of functions and methods. Answers are conservative: when declarations disagree or nothing is
// declared, the type is "" (unknown) and rules must treat it as unknown, never as "not X".
//
// Full mode (Project) adds the same facts collected across every file of the language in the
// scanned tree, so obj.method() and imported helpers resolve across files.
package types

import (
	"regexp"
	"strings"

	"github.com/elmo/code-review-engine/internal/taint"
)

// N is the shared Go-side syntax node.
type N = taint.N

type decl struct {
	scope *N
	typ   string // declared or inferred type; "" = unknown
	init  *N     // initializer to type lazily when typ is ""
	src   *File
}

// File is the per-file index.
type File struct {
	Lang    string
	Src     []byte
	Root    *N
	decls   map[string][]decl
	fields  map[string]map[string][]decl // class name -> field -> decls
	methods map[string]map[string]string // class name -> method -> declared return type
	funcs   map[string]string            // top-level function -> declared return type
	supers  map[string][]string          // class -> parent simple names (extends / embeds)
	Project *Project                     // full mode: cross-file facts (nil = file only)
	busy    map[*N]bool
}

// Project merges the class/function facts of many files (full-type mode).
type Project struct {
	fields  map[string]map[string]string
	methods map[string]map[string]string
	funcs   map[string]string
	supers  map[string][]string
}

func family(lang string) string {
	switch lang {
	case "javascript", "typescript", "tsx", "jsx":
		return "js"
	}
	return lang
}

// Supported reports whether the resolver models the grammar.
func Supported(lang string) bool {
	switch family(lang) {
	case "java", "kotlin", "python", "js", "php", "go":
		return true
	}
	return false
}

var canon = map[string][5]string{ // string, int, float, bool, list
	"java":   {"String", "int", "double", "boolean", "array"},
	"kotlin": {"String", "Int", "Double", "Boolean", "List"},
	"python": {"str", "int", "float", "bool", "list"},
	"js":     {"string", "number", "number", "boolean", "Array"},
	"php":    {"string", "int", "float", "bool", "array"},
	"go":     {"string", "int", "float64", "bool", "slice"},
}

var scopeKinds = map[string]bool{
	"method_declaration": true, "constructor_declaration": true, "lambda_expression": true, "class_body": true,
	"function_declaration": true, "function_definition": true, "class_definition": true, "lambda": true,
	"function_expression": true, "arrow_function": true, "method_definition": true, "class_declaration": true,
	"function_literal": true, "anonymous_function": true, "anonymous_function_creation_expression": true,
	"method_declaration_list": false, "func_literal": true, "program": true, "module": true, "source_file": true,
	"compilation_unit": true, "interface_body": true, "enum_body": true, "object_declaration": true, "class": true,
	"secondary_constructor": true, "primary_constructor": false, "anonymous_initializer": true, "arrow_function_expression": true,
}

func (f *File) text(n *N) string {
	if n == nil {
		return ""
	}
	return string(f.Src[n.S:n.E])
}

func scopeOf(n *N) *N {
	for p := n.Parent; p != nil; p = p.Parent {
		if scopeKinds[p.Kind] {
			return p
		}
	}
	return nil
}

func classOf(n *N) *N {
	for p := n.Parent; p != nil; p = p.Parent {
		switch p.Kind {
		case "class_declaration", "class_definition", "class", "object_declaration", "enum_declaration", "record_declaration":
			return p
		}
	}
	return nil
}

func (f *File) className(c *N) string {
	if c == nil {
		return ""
	}
	if nm := c.F("name"); nm != nil {
		return f.text(nm)
	}
	if nm := c.Child("type_identifier", "simple_identifier", "identifier", "name"); nm != nil {
		return f.text(nm)
	}
	return ""
}

var (
	genericRe = regexp.MustCompile(`<.*>|\[.*\]$`)
	qualRe    = regexp.MustCompile(`^.*[.\\]`)
)

// Norm reduces a written type to its simple name: generics, array-ness kept as a suffix-free
// name, qualifiers and nullability removed. Unions and optionals are unknown ("").
func Norm(t string) string {
	t = strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(t), ":"))
	t = strings.Trim(t, "()")
	t = strings.TrimPrefix(t, "final ")
	t = strings.TrimPrefix(t, "?") // PHP nullable
	if t == "" || strings.ContainsAny(t, "|&") || strings.HasPrefix(t, "Optional[") || strings.HasPrefix(t, "Union[") {
		return ""
	}
	if strings.HasSuffix(t, "[]") {
		return "array"
	}
	t = strings.TrimSuffix(strings.TrimPrefix(t, "*"), "?")
	t = strings.Trim(t, "'\"") // Python forward references
	t = genericRe.ReplaceAllString(t, "")
	t = qualRe.ReplaceAllString(t, "")
	if t == "var" || t == "val" || t == "auto" || t == "any" || t == "Any" {
		return ""
	}
	return strings.TrimSpace(t)
}

// Build indexes one file. root must be the Convert()ed tree of src.
func Build(lang string, root *N, src []byte) *File {
	f := &File{Lang: family(lang), Src: src, Root: root, decls: map[string][]decl{},
		fields: map[string]map[string][]decl{}, methods: map[string]map[string]string{}, funcs: map[string]string{},
		supers: map[string][]string{}, busy: map[*N]bool{}}
	var walk func(n *N)
	walk = func(n *N) {
		f.collect(n)
		for _, k := range n.Kids {
			walk(k)
		}
	}
	walk(root)
	return f
}

func (f *File) add(name string, at *N, typ string, init *N) {
	if name == "" {
		return
	}
	f.decls[name] = append(f.decls[name], decl{scope: scopeOf(at), typ: Norm(typ), init: init, src: f})
}

func (f *File) addField(class, name, typ string, init *N) {
	if class == "" || name == "" {
		return
	}
	if f.fields[class] == nil {
		f.fields[class] = map[string][]decl{}
	}
	f.fields[class][name] = append(f.fields[class][name], decl{typ: Norm(typ), init: init, src: f})
}

func (f *File) addSuper(class, super string) {
	super = Norm(super)
	if class == "" || super == "" || super == class {
		return
	}
	for _, p := range f.supers[class] {
		if p == super {
			return
		}
	}
	f.supers[class] = append(f.supers[class], super)
}

func (f *File) addFunc(n *N, name, ret string) {
	if name == "" {
		return
	}
	if c := classOf(n); c != nil && scopeOf(n) != nil && (scopeOf(n) == c || scopeOf(n).Parent == c || scopeOf(n).Kind == "class_body") {
		cn := f.className(c)
		if f.methods[cn] == nil {
			f.methods[cn] = map[string]string{}
		}
		f.methods[cn][name] = Norm(ret)
		return
	}
	f.funcs[name] = Norm(ret)
}

func (f *File) collect(n *N) {
	switch f.Lang {
	case "java":
		switch n.Kind {
		case "local_variable_declaration", "field_declaration", "constant_declaration":
			typ := f.text(n.F("type"))
			for _, d := range n.FAll("declarator") {
				name := f.text(d.F("name"))
				if n.Kind == "local_variable_declaration" {
					f.add(name, n, typ, d.F("value"))
				} else {
					f.addField(f.className(classOf(n)), name, typ, d.F("value"))
				}
			}
		case "formal_parameter", "enhanced_for_statement", "resource":
			f.add(f.text(n.F("name")), n, f.text(n.F("type")), n.F("value"))
			if n.Kind == "formal_parameter" {
				if c := classOf(n); c != nil && c.Kind == "record_declaration" {
					if p := n.Parent; p != nil && p.Kind == "formal_parameters" && p.Parent == c {
						f.addField(f.className(c), f.text(n.F("name")), f.text(n.F("type")), nil)
					}
				}
			}
		case "catch_formal_parameter":
			if t := n.Child("catch_type"); t != nil {
				f.add(f.text(n.F("name")), n, f.text(t), nil)
			}
		case "method_declaration":
			f.addFunc(n, f.text(n.F("name")), f.text(n.F("type")))
		case "class_declaration", "enum_declaration", "record_declaration":
			f.addSupersFrom(n, f.className(n))
		case "instanceof_expression":
			if nm := n.F("name"); nm != nil {
				f.add(f.text(nm), n, f.text(n.F("right")), nil)
			}
		}
	case "kotlin":
		switch n.Kind {
		case "property_declaration":
			vd := n.Child("variable_declaration")
			if vd == nil {
				return
			}
			name := f.text(vd.Child("simple_identifier", "identifier"))
			typ := f.text(vd.Child("user_type", "nullable_type"))
			var init *N
			kids := n.NamedKids()
			if len(kids) > 0 && kids[len(kids)-1] != vd && !strings.HasSuffix(kids[len(kids)-1].Kind, "delegate") {
				init = kids[len(kids)-1]
			}
			if c := classOf(n); c != nil && scopeOf(n) != nil && scopeOf(n).Kind == "class_body" {
				f.addField(f.className(c), name, typ, init)
			} else {
				f.add(name, n, typ, init)
			}
		case "parameter", "class_parameter":
			id := f.text(n.Child("simple_identifier", "identifier"))
			f.add(id, n, f.text(n.Child("user_type", "nullable_type")), nil)
			if n.Kind == "class_parameter" {
				f.addField(f.className(classOf(n)), id, f.text(n.Child("user_type", "nullable_type")), nil)
			}
		case "function_declaration":
			nm := n.F("name")
			if nm == nil {
				nm = n.Child("simple_identifier")
			}
			f.addFunc(n, f.text(nm), f.text(n.Child("user_type", "nullable_type")))
		case "class_declaration", "object_declaration":
			f.addSupersFrom(n, f.className(n))
		}
	case "python":
		switch n.Kind {
		case "assignment":
			l, r, t := n.F("left"), n.F("right"), n.F("type")
			if l == nil {
				return
			}
			if l.Kind == "identifier" {
				if c := classOf(n); c != nil && scopeOf(n) == c {
					f.addField(f.className(c), f.text(l), f.text(t), r)
				}
				f.add(f.text(l), n, f.text(t), r)
			} else if l.Kind == "attribute" && f.text(l.F("object")) == "self" {
				f.addField(f.className(classOf(n)), f.text(l.F("attribute")), f.text(t), r)
			}
		case "typed_parameter":
			if id := n.Child("identifier"); id != nil {
				f.add(f.text(id), n, f.text(n.F("type")), nil)
			}
		case "typed_default_parameter":
			f.add(f.text(n.F("name")), n, f.text(n.F("type")), n.F("value"))
		case "default_parameter":
			f.add(f.text(n.F("name")), n, "", n.F("value"))
		case "identifier":
			// untyped plain parameter: declared, type unknown (shadows outer names)
			if p := n.Parent; p != nil && p.Kind == "parameters" {
				f.add(f.text(n), n, "", nil)
			}
		case "function_definition":
			f.addFunc(n, f.text(n.F("name")), f.text(n.F("return_type")))
		case "class_definition":
			f.addSupersFrom(n, f.className(n))
		}
	case "js":
		switch n.Kind {
		case "variable_declarator":
			if nm := n.F("name"); nm != nil && nm.Kind == "identifier" {
				f.add(f.text(nm), n, f.text(n.F("type")), n.F("value"))
			}
		case "required_parameter", "optional_parameter":
			if p := n.F("pattern"); p != nil && p.Kind == "identifier" {
				f.add(f.text(p), n, f.text(n.F("type")), n.F("value"))
			}
		case "formal_parameters":
			for _, k := range n.NamedKids() {
				if k.Kind == "identifier" {
					f.add(f.text(k), k, "", nil)
				}
			}
		case "public_field_definition", "field_definition":
			name := n.F("name")
			if name == nil {
				name = n.F("property")
			}
			f.addField(f.className(classOf(n)), f.text(name), f.text(n.F("type")), n.F("value"))
		case "assignment_expression":
			if l := n.F("left"); l != nil && l.Kind == "member_expression" && f.text(l.F("object")) == "this" {
				f.addField(f.className(classOf(n)), f.text(l.F("property")), "", n.F("right"))
			}
		case "function_declaration", "method_definition", "function_signature", "method_signature":
			f.addFunc(n, f.text(n.F("name")), f.text(n.F("return_type")))
		case "class_declaration", "class":
			f.addSupersFrom(n, f.className(n))
		}
	case "php":
		switch n.Kind {
		case "simple_parameter", "property_promotion_parameter":
			f.add(f.text(n.F("name")), n, f.text(n.F("type")), n.F("default_value"))
		case "assignment_expression":
			l := n.F("left")
			if l != nil && l.Kind == "variable_name" {
				f.add(f.text(l), n, "", n.F("right"))
			} else if l != nil && l.Kind == "member_access_expression" && f.text(l.F("object")) == "$this" {
				f.addField(f.className(classOf(n)), "$"+f.text(l.F("name")), "", n.F("right"))
			}
		case "property_declaration":
			typ := f.text(n.F("type"))
			for _, e := range n.NamedKids() {
				if e.Kind == "property_element" {
					f.addField(f.className(classOf(n)), f.text(e.Child("variable_name")), typ, e.F("default_value"))
				}
			}
		case "method_declaration", "function_definition":
			f.addFunc(n, f.text(n.F("name")), f.text(n.F("return_type")))
		case "class_declaration":
			f.addSupersFrom(n, f.className(n))
		}
	case "go":
		switch n.Kind {
		case "short_var_declaration":
			ls, rs := n.F("left"), n.F("right")
			if ls == nil || rs == nil {
				return
			}
			lk, rk := ls.NamedKids(), rs.NamedKids()
			if len(lk) == 2 && len(rk) == 1 && (rk[0].Kind == "type_assertion_expression" || rk[0].Kind == "type_assertion") {
				f.add(f.text(lk[0]), n, "", rk[0])
				f.add(f.text(lk[1]), n, "bool", nil)
				return
			}
			for i, l := range lk {
				var init *N
				if len(lk) == len(rk) {
					init = rk[i]
				}
				f.add(f.text(l), n, "", init)
			}
		case "var_spec", "const_spec":
			names := n.FAll("name")
			var vals []*N
			if v := n.F("value"); v != nil {
				vals = v.NamedKids()
			}
			for i, nm := range names {
				var init *N
				if len(vals) == len(names) {
					init = vals[i]
				}
				f.add(f.text(nm), n, f.text(n.F("type")), init)
			}
		case "parameter_declaration":
			for _, nm := range n.FAll("name") {
				f.add(f.text(nm), n, f.text(n.F("type")), nil)
			}
		case "function_declaration":
			f.addFunc(n, f.text(n.F("name")), f.text(n.F("result")))
		case "method_declaration":
			if r := n.F("receiver"); r != nil {
				rt := Norm(strings.Trim(f.text(r), "() "))
				if fs := strings.Fields(rt); len(fs) > 0 {
					rt = Norm(fs[len(fs)-1])
				}
				if f.methods[rt] == nil {
					f.methods[rt] = map[string]string{}
				}
				f.methods[rt][f.text(n.F("name"))] = Norm(f.text(n.F("result")))
			}
		case "type_spec":
			f.collectGoStruct(n)
		}
	}
}

func (f *File) addSupersFrom(n *N, class string) {
	if class == "" || n == nil {
		return
	}
	for _, field := range []string{"superclass", "interfaces", "heritage", "superclasses"} {
		if c := n.F(field); c != nil {
			f.collectTypeNames(c, class)
		}
	}
	for _, k := range n.NamedKids() {
		switch k.Kind {
		case "superclass", "super_interfaces", "class_heritage", "base_clause", "class_interface_clause",
			"delegation_specifiers", "delegation_specifier", "argument_list":
			if k.Field == "superclasses" || k.Kind != "argument_list" {
				f.collectTypeNames(k, class)
			}
		}
	}
}

func (f *File) collectTypeNames(n *N, class string) {
	if n == nil {
		return
	}
	switch n.Kind {
	case "type_identifier", "identifier", "simple_identifier", "name":
		f.addSuper(class, f.text(n))
	case "generic_type", "user_type", "scoped_type_identifier", "type":
		if t := n.F("name"); t != nil {
			f.addSuper(class, f.text(t))
			return
		}
		if t := n.Child("type_identifier", "identifier", "simple_identifier", "name"); t != nil {
			f.addSuper(class, f.text(t))
		}
	case "type_arguments", "type_parameters", "value_arguments":
		return
	case "argument_list":
		if n.Field != "superclasses" {
			return
		}
		fallthrough
	default:
		for _, k := range n.NamedKids() {
			f.collectTypeNames(k, class)
		}
	}
}

func (f *File) collectGoStruct(n *N) {
	name := f.text(n.F("name"))
	st := n.Child("struct_type")
	if name == "" || st == nil {
		return
	}
	var walk func(*N)
	walk = func(x *N) {
		if x.Kind == "field_declaration" {
			typ := f.text(x.F("type"))
			names := x.FAll("name")
			if len(names) == 0 {
				if t := Norm(typ); t != "" {
					f.addField(name, t, typ, nil)
					f.addSuper(name, t)
				}
				return
			}
			for _, nm := range names {
				f.addField(name, f.text(nm), typ, nil)
			}
			return
		}
		for _, k := range x.Kids {
			walk(k)
		}
	}
	walk(st)
}

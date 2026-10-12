package index

import (
	"regexp"
	"strings"
	"unicode"

	ts "github.com/tree-sitter/go-tree-sitter"
)

type spec struct {
	funcs    map[string]string // def node kind -> func|method|type
	idents   map[string]bool
	keepName map[string]bool // property/field identifiers kept verbatim in body fingerprints
	calls    map[string]bool
	loops    map[string]bool
	branches map[string]bool
	comments map[string]bool
	imports  map[string]bool
	block    map[string]bool // statement-list nodes (bodies)
}

func set(s ...string) map[string]bool {
	m := map[string]bool{}
	for _, x := range s {
		m[x] = true
	}
	return m
}

var jsSpec = &spec{
	funcs: map[string]string{"function_declaration": "func", "generator_function_declaration": "func", "method_definition": "method",
		"class_declaration": "type", "interface_declaration": "type", "type_alias_declaration": "type", "enum_declaration": "type", "variable_declarator": "func"},
	idents:   set("identifier", "property_identifier", "type_identifier", "shorthand_property_identifier", "shorthand_property_identifier_pattern"),
	keepName: set("property_identifier"),
	calls:    set("call_expression", "new_expression"),
	loops:    set("for_statement", "for_in_statement", "while_statement", "do_statement"),
	branches: set("if_statement", "switch_case", "ternary_expression", "catch_clause", "for_statement", "for_in_statement", "while_statement", "do_statement"),
	comments: set("comment"),
	imports:  set("import_statement", "export_statement"),
	block:    set("statement_block"),
}

var specs = map[string]*spec{
	"go": {
		funcs:    map[string]string{"function_declaration": "func", "method_declaration": "method", "type_spec": "type"},
		idents:   set("identifier", "field_identifier", "type_identifier", "package_identifier"),
		keepName: set("field_identifier"),
		calls:    set("call_expression"),
		loops:    set("for_statement"),
		branches: set("if_statement", "expression_case", "type_case", "communication_case", "for_statement"),
		comments: set("comment"),
		imports:  set("import_spec"),
		block:    set("block"),
	},
	"python": {
		funcs:    map[string]string{"function_definition": "func", "class_definition": "type"},
		idents:   set("identifier"),
		keepName: set(),
		calls:    set("call"),
		loops:    set("for_statement", "while_statement"),
		branches: set("if_statement", "elif_clause", "for_statement", "while_statement", "except_clause", "conditional_expression", "boolean_operator", "for_in_clause"),
		comments: set("comment"),
		imports:  set("import_statement", "import_from_statement"),
		block:    set("block"),
	},
	"javascript": jsSpec, "typescript": jsSpec, "tsx": jsSpec,
	"java": {
		funcs:    map[string]string{"method_declaration": "method", "constructor_declaration": "method", "class_declaration": "type", "interface_declaration": "type", "record_declaration": "type", "enum_declaration": "type"},
		idents:   set("identifier", "type_identifier"),
		keepName: set(),
		calls:    set("method_invocation", "object_creation_expression"),
		loops:    set("for_statement", "enhanced_for_statement", "while_statement", "do_statement"),
		branches: set("if_statement", "switch_label", "catch_clause", "ternary_expression", "for_statement", "enhanced_for_statement", "while_statement", "do_statement"),
		comments: set("line_comment", "block_comment"),
		imports:  set("import_declaration"),
		block:    set("block", "constructor_body"),
	},
	"kotlin": {
		funcs:    map[string]string{"function_declaration": "func", "class_declaration": "type", "object_declaration": "type"},
		idents:   set("identifier"),
		keepName: set(),
		calls:    set("call_expression"),
		loops:    set("for_statement", "while_statement", "do_while_statement"),
		branches: set("if_expression", "when_entry", "catch_block", "for_statement", "while_statement", "do_while_statement", "elvis_expression"),
		comments: set("line_comment", "block_comment"),
		imports:  set("import"),
		block:    set("block"),
	},
	"php": {
		funcs:    map[string]string{"function_definition": "func", "method_declaration": "method", "class_declaration": "type", "interface_declaration": "type", "trait_declaration": "type"},
		idents:   set("name"),
		keepName: set(),
		calls:    set("function_call_expression", "member_call_expression", "scoped_call_expression", "object_creation_expression"),
		loops:    set("for_statement", "foreach_statement", "while_statement", "do_statement"),
		branches: set("if_statement", "else_if_clause", "case_statement", "catch_clause", "conditional_expression", "for_statement", "foreach_statement", "while_statement"),
		comments: set("comment"),
		imports:  set("namespace_use_clause"),
		block:    set("compound_statement"),
	},
}

type walker struct {
	x     *Index
	rel   string
	f     *File
	src   []byte
	spec  *spec
	loops []*ts.Node // enclosing collection loops
	ptEnd int        // last row of the latest limit note comment (-1: none), to join continuation lines
}

var fixedRange = regexp.MustCompile(`(?:range\s*\(\s*\d+\s*\)|range\s+\d+\b|<\s*=?\s*\d+\s*;|\b\d+\s*\.\.<?\s*\d+|\brepeat\s*\(\s*\d+)`)
var equality = regexp.MustCompile(`===?|!==?|\.equals\(|\bis\b|\.Equal\(|strcmp\(|\bcompareTo\(`)

// loopHeader is the loop text before its body.
func (w *walker) loopHeader(n *ts.Node) string {
	t := w.text(n)
	if b := n.ChildByFieldName("body"); b != nil {
		t = string(w.src[n.StartByte():b.StartByte()])
	}
	if i := strings.IndexByte(t, '{'); i > 0 {
		t = t[:i]
	}
	return t
}

var lastIdent = regexp.MustCompile(`[A-Za-z_$][A-Za-z0-9_$]*`)

func (w *walker) text(n *ts.Node) string { return n.Utf8Text(w.src) }

// iterRe pulls the iterated collection out of a loop header (Go range, Python/Kotlin in, JS of,
// Java/PHP for-each colon / as).
var iterRe = regexp.MustCompile(`(?:\brange|\bin|\bof|:)\s+([A-Za-z_$][\w$.]*(?:\(\))?)\s*\)?\s*:?\s*$|\bforeach\s*\(\s*(\$?[\w$.>-]+)\s+as\b`)

// loopIter is the collection a loop iterates over ("" when it cannot be named).
func (w *walker) loopIter(n *ts.Node) string {
	h := strings.TrimSpace(w.loopHeader(n))
	if m := iterRe.FindStringSubmatch(h); m != nil {
		if m[1] != "" {
			return m[1]
		}
		return m[2]
	}
	return ""
}

func (w *walker) walk(n *ts.Node, fn *Symbol, depth int) {
	k := n.Kind()
	sp := w.spec
	if sp.idents[k] {
		w.x.ref(w.text(n), w.rel, w.f.Test)
	}
	if sp.comments[k] {
		t, row := w.text(n), int(n.StartPosition().Row)
		switch {
		case limitNoteRe.MatchString(t):
			w.x.LimitNotes = append(w.x.LimitNotes, Comment{File: w.rel, Line: row + 1, Text: strings.TrimSpace(t)})
			w.ptEnd = int(n.EndPosition().Row)
		case w.ptEnd >= 0 && row == w.ptEnd+1 && len(w.x.LimitNotes) > 0:
			// a `// limit:` note wrapped over following comment lines is one note
			last := &w.x.LimitNotes[len(w.x.LimitNotes)-1]
			last.Text += " " + strings.TrimSpace(commentMarker.ReplaceAllString(t, ""))
			w.ptEnd = int(n.EndPosition().Row)
		default:
			w.ptEnd = -1
		}
	}
	if k == "package_clause" && w.f.Lang == "go" && n.NamedChildCount() > 0 {
		w.f.Package = w.text(n.NamedChild(0))
	}
	if sp.imports[k] {
		w.imports(n)
	}
	if k == "call_expression" && (w.f.Lang == "javascript" || w.f.Lang == "typescript" || w.f.Lang == "tsx") {
		if fnode := n.ChildByFieldName("function"); fnode != nil && (w.text(fnode) == "require" || fnode.Kind() == "import") {
			if a := n.ChildByFieldName("arguments"); a != nil && a.NamedChildCount() > 0 && a.NamedChild(0).Kind() == "string" {
				w.f.Imports = append(w.f.Imports, strings.Trim(w.text(a.NamedChild(0)), "'\"`"))
			}
		}
	}
	if sp.loops[k] && !fixedRange.MatchString(w.loopHeader(n)) {
		if len(w.loops) > 0 {
			body := n.ChildByFieldName("body")
			if body == nil {
				body = n
			}
			if outer := w.loops[len(w.loops)-1]; w.comparesLoopVars(outer, n, body) {
				fname := ""
				if fn != nil {
					fname = fn.Name
				}
				l := Loop{File: w.rel, Line: int(outer.StartPosition().Row) + 1, EndLine: int(outer.EndPosition().Row) + 1, InnerLine: int(n.StartPosition().Row) + 1, Func: fname,
					Outer: w.loopIter(outer), Inner: w.loopIter(n)}
				if len(w.x.Loops) == 0 || w.x.Loops[len(w.x.Loops)-1].Line != l.Line || w.x.Loops[len(w.x.Loops)-1].File != l.File {
					w.x.Loops = append(w.x.Loops, l)
				}
			}
		}
		w.loops = append(w.loops, n)
		defer func() { w.loops = w.loops[:len(w.loops)-1] }()
	}
	if fn == nil && depth <= 3 && (k == "var_spec" || k == "expression_statement" || k == "assignment") {
		if t := w.text(n); !w.f.Test && lockDecl.MatchString(t) {
			w.x.Locks = append(w.x.Locks, Comment{File: w.rel, Line: int(n.StartPosition().Row) + 1, Text: strings.TrimSpace(t)})
		}
	}
	if sp.calls[k] {
		if c := w.callee(n); c != "" {
			caller := ""
			if fn != nil {
				caller = fn.Name
			}
			w.x.Calls[c] = append(w.x.Calls[c], Call{Callee: c, File: w.rel, Line: int(n.StartPosition().Row) + 1, Caller: caller})
		}
	}
	if kind, ok := sp.funcs[k]; ok {
		if s := w.def(n, kind, fn, depth); s != nil {
			for i := uint(0); i < n.ChildCount(); i++ {
				w.walk(n.Child(i), s, depth+1)
			}
			return
		}
	}
	if depth == 1 && fn == nil && n.IsNamed() && !sp.imports[k] && !sp.comments[k] && k != "package_clause" && k != "import_declaration" && k != "package_declaration" && k != "import_list" && k != "import_header" && k != "shebang_line" && k != "file_annotation" && k != "namespace_use_declaration" && k != "expression_statement" && k != "php_tag" && k != "namespace_definition" && k != "package_header" && k != "lexical_declaration" && k != "export_statement" && k != "future_import_statement" {
		w.f.TopLevelOther++
	}
	for i := uint(0); i < n.ChildCount(); i++ {
		w.walk(n.Child(i), fn, depth+1)
	}
}

func (w *walker) imports(n *ts.Node) {
	switch w.f.Lang {
	case "go":
		if p := n.ChildByFieldName("path"); p != nil {
			w.f.Imports = append(w.f.Imports, strings.Trim(w.text(p), "\"`"))
		}
	case "python":
		if m := n.ChildByFieldName("module_name"); m != nil {
			w.f.Imports = append(w.f.Imports, w.text(m))
			return
		}
		for i := uint(0); i < n.NamedChildCount(); i++ {
			c := n.NamedChild(i)
			if c.Kind() == "dotted_name" {
				w.f.Imports = append(w.f.Imports, w.text(c))
			} else if c.Kind() == "aliased_import" {
				if nm := c.ChildByFieldName("name"); nm != nil {
					w.f.Imports = append(w.f.Imports, w.text(nm))
				}
			}
		}
	case "javascript", "typescript", "tsx":
		if s := n.ChildByFieldName("source"); s != nil {
			w.f.Imports = append(w.f.Imports, strings.Trim(w.text(s), "'\"`"))
		}
	default:
		w.f.Imports = append(w.f.Imports, strings.TrimSpace(strings.TrimPrefix(strings.TrimPrefix(w.text(n), "import"), "use")))
	}
}

func (w *walker) callee(n *ts.Node) string {
	var c *ts.Node
	switch n.Kind() {
	case "method_invocation", "member_call_expression", "scoped_call_expression":
		c = n.ChildByFieldName("name")
	case "new_expression":
		c = n.ChildByFieldName("constructor")
	case "object_creation_expression":
		for i := uint(0); i < n.NamedChildCount(); i++ {
			if k := n.NamedChild(i).Kind(); k == "type_identifier" || k == "name" || k == "qualified_name" || k == "scoped_type_identifier" {
				c = n.NamedChild(i)
				break
			}
		}
	default:
		c = n.ChildByFieldName("function")
		if c == nil && n.NamedChildCount() > 0 {
			c = n.NamedChild(0)
		}
	}
	if c == nil {
		return ""
	}
	m := lastIdent.FindAllString(w.text(c), -1)
	if len(m) == 0 {
		return ""
	}
	return m[len(m)-1]
}

func (w *walker) def(n *ts.Node, kind string, parent *Symbol, depth int) *Symbol {
	name := n.ChildByFieldName("name")
	body := n.ChildByFieldName("body")
	if n.Kind() == "variable_declarator" {
		v := n.ChildByFieldName("value")
		if v == nil || (v.Kind() != "arrow_function" && v.Kind() != "function_expression" && v.Kind() != "function") {
			return nil
		}
		body = v.ChildByFieldName("body")
		n = v
	}
	if name == nil {
		for i := uint(0); i < n.NamedChildCount(); i++ {
			if k := n.NamedChild(i).Kind(); k == "identifier" || k == "simple_identifier" || k == "type_identifier" || k == "name" {
				name = n.NamedChild(i)
				break
			}
		}
	}
	if name == nil {
		return nil
	}
	if kind == "func" && parent != nil && parent.Kind == "type" {
		kind = "method"
	}
	s := &Symbol{Name: w.text(name), Kind: kind, File: w.rel, Line: int(n.StartPosition().Row) + 1, EndLine: int(n.EndPosition().Row) + 1,
		TopLevel: parent == nil}
	if parent != nil {
		s.Container = parent.Name
	}
	if n.Kind() == "method_declaration" && w.f.Lang == "go" {
		if r := n.ChildByFieldName("receiver"); r != nil {
			if m := lastIdent.FindAllString(w.text(r), -1); len(m) > 0 {
				s.Container = m[len(m)-1]
			}
		}
		s.TopLevel = true
	}
	s.Exported = w.exported(n, s)
	if params := n.ChildByFieldName("parameters"); params != nil {
		s.Params = w.paramNames(params)
	} else if w.f.Lang == "kotlin" {
		for i := uint(0); i < n.NamedChildCount(); i++ {
			if n.NamedChild(i).Kind() == "function_value_parameters" {
				s.Params = w.paramNames(n.NamedChild(i))
			}
		}
	}
	if body == nil && w.f.Lang == "kotlin" {
		for i := uint(0); i < n.NamedChildCount(); i++ {
			if n.NamedChild(i).Kind() == "function_body" {
				body = n.NamedChild(i)
			}
		}
	}
	if body != nil && kind != "type" {
		var b strings.Builder
		names := map[string]string{}
		for i, p := range s.Params {
			names[p] = "v" + string(rune('a'+i%26)) + strings.Repeat("'", i/26)
			names["$"+p] = names[p]
		}
		w.fingerprint(body, &b, names, s)
		s.BodyHash = shortHash(b.String())
		s.Stmts = w.stmts(body)
		s.Delegate = w.delegate(body, s)
	}
	w.f.Symbols = append(w.f.Symbols, s)
	w.x.Defs[s.Name] = append(w.x.Defs[s.Name], s)
	return s
}

func (w *walker) exported(n *ts.Node, s *Symbol) bool {
	switch w.f.Lang {
	case "go":
		r := []rune(s.Name)
		return len(r) > 0 && unicode.IsUpper(r[0])
	case "python":
		return s.TopLevel && !strings.HasPrefix(s.Name, "_")
	case "javascript", "typescript", "tsx":
		for p := n.Parent(); p != nil; p = p.Parent() {
			if p.Kind() == "export_statement" {
				return true
			}
			if p.Kind() == "program" {
				break
			}
		}
		return false
	case "java", "php":
		for i := uint(0); i < n.NamedChildCount(); i++ {
			if k := n.NamedChild(i).Kind(); k == "modifiers" || k == "visibility_modifier" {
				return strings.Contains(w.text(n.NamedChild(i)), "public")
			}
		}
		return w.f.Lang == "php" && s.TopLevel
	case "kotlin":
		for i := uint(0); i < n.NamedChildCount(); i++ {
			if n.NamedChild(i).Kind() == "modifiers" {
				t := w.text(n.NamedChild(i))
				return !strings.Contains(t, "private") && !strings.Contains(t, "internal") && !strings.Contains(t, "protected")
			}
		}
		return true
	}
	return false
}

func (w *walker) paramNames(p *ts.Node) []string {
	var out []string
	for i := uint(0); i < p.NamedChildCount(); i++ {
		c := p.NamedChild(i)
		if strings.Contains(c.Kind(), "comment") {
			continue
		}
		var nm *ts.Node
		if f := c.ChildByFieldName("name"); f != nil {
			nm = f
		} else if f := c.ChildByFieldName("pattern"); f != nil {
			nm = f
		} else if c.Kind() == "identifier" {
			nm = c
		}
		if nm == nil && c.NamedChildCount() > 0 {
			nm = c.NamedChild(0)
		}
		if nm != nil {
			// Go parameter_declaration may declare several names: a, b int
			if c.Kind() == "parameter_declaration" {
				for j := uint(0); j < c.NamedChildCount(); j++ {
					if c.NamedChild(j).Kind() == "identifier" {
						out = append(out, w.text(c.NamedChild(j)))
					}
				}
				continue
			}
			out = append(out, strings.TrimPrefix(w.text(nm), "$"))
		}
	}
	return out
}

// fingerprint writes an alpha-renamed token stream of the body (identifiers -> v1, v2, ...;
// properties/fields and literals verbatim) and counts complexity.
func (w *walker) fingerprint(n *ts.Node, b *strings.Builder, names map[string]string, s *Symbol) {
	k := n.Kind()
	if w.spec.branches[k] {
		s.Complexity++
	}
	if k == "binary_expression" {
		if op := n.ChildByFieldName("operator"); op != nil {
			if t := w.text(op); t == "&&" || t == "||" || t == "??" {
				s.Complexity++
			}
		}
	}
	if w.spec.comments[k] {
		return
	}
	if n.ChildCount() == 0 {
		t := w.text(n)
		if w.spec.idents[k] && !w.spec.keepName[k] {
			// Alpha-rename parameters and locally declared names only; callees, fields and
			// package names stay verbatim so different calls never hash equal.
			v, ok := names[t]
			if !ok && declares(n) {
				v = "v" + string(rune('a'+len(names)%26)) + strings.Repeat("'", len(names)/26)
				names[t] = v
				ok = true
			}
			if ok {
				t = v
			}
		}
		b.WriteString(t)
		b.WriteByte(' ')
		return
	}
	for i := uint(0); i < n.ChildCount(); i++ {
		w.fingerprint(n.Child(i), b, names, s)
	}
}

func (w *walker) stmts(body *ts.Node) int {
	if !w.spec.block[body.Kind()] {
		if body.NamedChildCount() == 1 && w.spec.block[body.NamedChild(0).Kind()] {
			return w.stmts(body.NamedChild(0))
		}
		return 1 // expression body (arrow fn, kotlin = expr)
	}
	if body.NamedChildCount() == 1 && strings.HasSuffix(body.NamedChild(0).Kind(), "statement_list") {
		body = body.NamedChild(0)
	}
	n := 0
	for i := uint(0); i < body.NamedChildCount(); i++ {
		if !w.spec.comments[body.NamedChild(i).Kind()] {
			n++
		}
	}
	return n
}

var delegRe = regexp.MustCompile(`^(?:return\s+)?(?:await\s+)?([A-Za-z_$][\w$]*(?:(?:\.|->|::)[A-Za-z_$][\w$]*)*)\s*\(([^()]*)\)\s*;?$`)

// delegate reports the callee when the body is a single statement forwarding the parameters
// unchanged (return other(a, b)).
func (w *walker) delegate(body *ts.Node, s *Symbol) string {
	t := strings.TrimSpace(w.text(body))
	t = strings.TrimSpace(strings.TrimSuffix(strings.TrimPrefix(t, "{"), "}"))
	t = strings.TrimPrefix(t, "=")
	t = strings.TrimSpace(t)
	if strings.Contains(t, "\n") && strings.Count(strings.TrimSpace(t), "\n") > 0 {
		return ""
	}
	m := delegRe.FindStringSubmatch(t)
	if m == nil {
		return ""
	}
	var args []string
	for _, a := range strings.Split(m[2], ",") {
		if a = strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(a), "$")); a != "" {
			args = append(args, strings.TrimPrefix(a, "..."))
		}
	}
	if len(args) != len(s.Params) {
		return ""
	}
	for i := range args {
		if args[i] != strings.TrimPrefix(s.Params[i], "...") {
			return ""
		}
	}
	callee := m[1]
	if parts := lastIdent.FindAllString(callee, -1); len(parts) > 0 && parts[len(parts)-1] == s.Name && !strings.ContainsAny(callee, ".:->") {
		return "" // recursion, not delegation
	}
	return callee
}

// declares reports whether identifier n is being declared (local variable, parameter, pattern
// or the target of a plain assignment).
func declares(n *ts.Node) bool {
	p := n.Parent()
	for i := 0; p != nil && i < 2; i++ {
		k := p.Kind()
		if strings.Contains(k, "declar") || strings.Contains(k, "parameter") || strings.Contains(k, "pattern") {
			return true
		}
		if (k == "assignment" || k == "assignment_expression" || k == "assignment_statement" || k == "augmented_assignment") && p.NamedChildCount() > 0 && p.NamedChild(0).StartByte() == n.StartByte() {
			return true
		}
		if k != "expression_list" && k != "variable_name" {
			break
		}
		p = p.Parent()
	}
	return false
}

var (
	lockDecl      = regexp.MustCompile(`^\w+\s+(?:sync\.(?:RW)?Mutex)\s*$|^\w+\s*=\s*threading\.R?Lock\(\)\s*$`)
	commentMarker = regexp.MustCompile(`^\s*(?://+|#+|/\*+|\*/?|--)\s*`)
	// limitNoteRe: a comment documenting a deliberate shortcut's limit and upgrade path. `limit:` is
	// the documented marker; `ponytail:` is still accepted for existing code.
	limitNoteRe = regexp.MustCompile(`^(?://+|#+|/\*+|\*)\s*(?:limit|ponytail):`)
	identRe       = regexp.MustCompile(`[A-Za-z_$][\w$]*`)
	loopKw        = map[string]bool{"for": true, "range": true, "in": true, "of": true, "const": true, "let": true, "var": true, "val": true,
		"foreach": true, "as": true, "while": true, "do": true, "len": true, "length": true, "size": true, "int": true, "String": true, "auto": true, "final": true}
)

// loopVars are the identifiers introduced or iterated in a loop header (best effort).
func (w *walker) loopVars(n *ts.Node) map[string]bool {
	vars, _ := splitLoopHeader(w.loopHeader(n))
	return vars
}

// loopSplit: the token between a foreach loop's bound variables and its iterable, per syntax
// (Go range, JS/TS of/in, Python/Kotlin in, Java/C# enhanced for). PHP foreach is reversed.
var loopSplit = regexp.MustCompile(`(:?=\s*range\b|\brange\b|\s(?:of|in)\s)|[^:](:)[^:=]`)

// splitLoopHeader returns the variables a loop binds and the text of what it iterates over.
// Headers without a foreach shape (C-style for, while) bind every identifier they mention and
// have no iterable.
func splitLoopHeader(h string) (map[string]bool, string) {
	add := func(m map[string]bool, t string) {
		for _, id := range identRe.FindAllString(t, -1) {
			if !loopKw[id] {
				m[strings.TrimPrefix(id, "$")] = true
			}
		}
	}
	vars := map[string]bool{}
	if i := strings.Index(h, " as "); i > 0 && strings.Contains(h, "foreach") {
		add(vars, h[i+4:])
		return vars, h[:i]
	}
	if strings.Count(h, ";") < 2 {
		if m := loopSplit.FindStringSubmatchIndex(h); m != nil {
			a, b := m[2], m[3] // group 1, else group 2 (Java/C# ':')
			if a < 0 {
				a, b = m[4], m[5]
			}
			add(vars, h[:a])
			return vars, h[b:]
		}
	}
	add(vars, h)
	return vars, ""
}

// comparesLoopVars reports an equality test in the inner body that mentions a variable of each
// loop on the same line (x == y, a.equals(b), $x === $y): the O(n·m) find/dedupe shape.
//
// An inner loop whose iterable is derived from an outer loop variable (for _, x := range
// byKey[o.Key], for _, r := range rs) walks a nested structure or an index lookup, not a
// cross product, and is not reported.
func (w *walker) comparesLoopVars(outer, inner, body *ts.Node) bool {
	ov := w.loopVars(outer)
	iv, iterable := splitLoopHeader(w.loopHeader(inner))
	for _, id := range identRe.FindAllString(iterable, -1) {
		if id = strings.TrimPrefix(id, "$"); ov[id] && !iv[id] {
			return false
		}
	}
	side := func(t string) (o, i bool) {
		for _, id := range identRe.FindAllString(t, -1) {
			id = strings.TrimPrefix(id, "$")
			o = o || (ov[id] && !iv[id])
			i = i || (iv[id] && !ov[id])
		}
		return
	}
	for _, line := range strings.Split(w.text(body), "\n") {
		for _, m := range equality.FindAllStringIndex(line, -1) {
			l := line[:m[0]]
			if k := strings.LastIndexAny(l, "(&|,;{?"); k >= 0 && !strings.HasPrefix(line[m[0]:], ".") {
				l = l[k+1:]
			}
			r := line[m[1]:]
			if k := strings.IndexAny(r, ")&|,;{?"); k >= 0 {
				r = r[:k]
			}
			lo, li := side(l)
			ro, ri := side(r)
			if (lo && ri) || (li && ro) {
				return true
			}
		}
	}
	return false
}

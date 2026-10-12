// Package engine runs rules (tree-sitter queries, config and manifest checks) over sources.
package engine

import (
	"fmt"
	"github.com/elmo/code-review-engine/internal/taint"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"sync"
	"time"

	ts "github.com/tree-sitter/go-tree-sitter"

	"github.com/elmo/code-review-engine/internal/grammars"
	"github.com/elmo/code-review-engine/internal/rules"
)

// Hit is a raw rule match location (0-based rows/cols, byte offsets).
type Hit struct {
	StartByte, EndByte uint
	StartRow, StartCol uint
	EndRow, EndCol     uint
	Text               string
	Symbol             string // enclosing declaration, e.g. UserService#save
	// Value is the measured metric of a metric.* rule (substituted for ${value} in the message);
	// such hits carry only the first line of the node as Text, so the fingerprint survives body edits.
	Value string
}

// qkey includes the query text: a user override (.crev/rules/) may change the query of a built-in id.
type qkey struct{ id, grammar, query string }

var (
	// limit: one process-wide lock around the compiled-query cache; holds while compiles stay
	// at most a few thousand per scan (one per rule and grammar); switch to per-grammar shards or
	// sync.Map if profiles show contention.
	qmu    sync.Mutex
	qcache = map[qkey]*ts.Query{}
)

// CompileQuery returns the (cached) compiled query of a rule for a grammar.
func CompileQuery(r *rules.Rule, grammar string) (*ts.Query, *ts.Language, error) {
	lang := grammars.Get(grammar)
	if lang == nil {
		return nil, nil, fmt.Errorf("no grammar %q", grammar)
	}
	qmu.Lock()
	defer qmu.Unlock()
	k := qkey{r.ID, grammar, r.Detection.Query}
	if q, ok := qcache[k]; ok {
		return q, lang, nil
	}
	q, err := ts.NewQuery(lang, r.Detection.Query)
	if err != nil {
		return nil, nil, fmt.Errorf("query compile (%s): %w", grammar, err)
	}
	if _, ok := q.CaptureIndexForName(r.CaptureName()); !ok {
		q.Close()
		return nil, nil, fmt.Errorf("query lacks @%s capture", r.CaptureName())
	}
	qcache[k] = q
	return q, lang, nil
}

// Tree is a parsed source shared by all rules for one (file, grammar) pair.
type Tree struct {
	Grammar string
	Src     []byte
	// SFC is the whole single-file component when Src is the script block extracted from a .vue
	// file; sfc.has_re / sfc.lacks_re filters test it (falling back to Src).
	SFC []byte
	// Dir and Root (absolute; empty for in-memory sources): dir.has_file / dir.lacks_file look for
	// sibling files in Dir and its parents up to Root.
	Dir, ScanRoot string
	tree          *ts.Tree
	// lazily computed taint-lite result (taintrules.go)
	taint    *taint.Result
	taintErr error
}

// Parse parses src with the grammar.
func Parse(grammar string, src []byte) (*Tree, error) {
	lang := grammars.Get(grammar)
	if lang == nil {
		return nil, fmt.Errorf("no grammar %q", grammar)
	}
	p := ts.NewParser()
	defer p.Close()
	if err := p.SetLanguage(lang); err != nil {
		return nil, err
	}
	t := p.Parse(src, nil)
	if t == nil {
		return nil, fmt.Errorf("parse failed")
	}
	return &Tree{Grammar: grammar, Src: src, tree: t}, nil
}

// Root returns the root node.
func (t *Tree) Root() *ts.Node { return t.tree.RootNode() }

// Close frees the tree.
func (t *Tree) Close() { t.tree.Close() }

// Run executes the rule's query on the tree and applies the rule's post-filters.
func Run(r *rules.Rule, t *Tree) (hits []Hit, err error) {
	// A bug in one rule's filter must not abort the whole scan: report it as that rule's error.
	defer func() {
		if p := recover(); p != nil {
			hits, err = nil, fmt.Errorf("panic: %v", p)
		}
	}()
	q, _, err := CompileQuery(r, t.Grammar)
	if err != nil {
		return nil, err
	}
	if ok, err := fileGate(r, t); err != nil || !ok {
		return nil, err
	}
	idx, _ := q.CaptureIndexForName(r.CaptureName())
	qc := ts.NewQueryCursor()
	defer qc.Close()
	qc.SetTimeoutMicros(uint64(QueryTimeout.Microseconds()))
	start := time.Now()
	ms := qc.Matches(q, t.tree.RootNode(), t.Src)
	var out []Hit
	seen := map[[2]uint]bool{}
	names := q.CaptureNames()
	for m := ms.Next(); m != nil; m = ms.Next() {
		var caps map[string]string
		if needCaps(r) {
			caps = map[string]string{}
			for _, c := range m.Captures {
				caps[names[c.Index]] = c.Node.Utf8Text(t.Src)
			}
		}
		for _, c := range m.Captures {
			if uint(c.Index) != idx {
				continue
			}
			n := c.Node
			k := [2]uint{n.StartByte(), n.EndByte()}
			if seen[k] {
				continue
			}
			ok, err := PassFilters(r, n, t.Src, caps)
			if err != nil {
				return nil, err
			}
			if !ok || cleanByTaint(r, t, n) {
				continue
			}
			seen[k] = true
			sp, ep := n.StartPosition(), n.EndPosition()
			h := Hit{n.StartByte(), n.EndByte(), sp.Row, sp.Column, ep.Row, ep.Column, n.Utf8Text(t.Src), enclosing(n, t.Src), ""}
			if v, ok := metricValue(r, n, t.Src); ok {
				h.Value = v
				h.Text, _, _ = strings.Cut(h.Text, "\n")
				h.Text = strings.TrimSpace(h.Text)
			}
			out = append(out, h)
		}
	}
	if time.Since(start) >= QueryTimeout {
		// pathological pattern/file pair (e.g. sibling-pair patterns on a dict with thousands of
		// entries): keep the partial result and report it instead of hanging the scan
		return out, fmt.Errorf("query timed out after %s (results for this file may be incomplete)", QueryTimeout)
	}
	return out, nil
}

// QueryTimeout bounds one rule's tree-sitter query on one file.
var QueryTimeout = 10 * time.Second

// cleanByTaint implements the taint.clean:<class> filter: drop a dangerous-API match when
// taint-lite proves the call's arguments do not come from the function's untrusted input.
func cleanByTaint(r *rules.Rule, t *Tree, n ts.Node) bool {
	for _, f := range r.Detection.Filters {
		if name, cls, _ := strings.Cut(f, ":"); name == "taint.clean" && t.taintClean(cls, n.StartByte(), n.EndByte()) {
			return true
		}
	}
	return false
}

var filterRe sync.Map

// fileGate evaluates the file-level filters that do not depend on the match (no {text} /
// {cap:} placeholders) before the query runs: a rule gated on e.g. `file.has_re:draft-0[4-7]`
// then costs nothing on other files, however expensive its query is on a large one.
func fileGate(r *rules.Rule, t *Tree) (bool, error) {
	src := t.Src
	for _, f := range r.Detection.Filters {
		name, arg, _ := strings.Cut(f, ":")
		if strings.Contains(arg, "{cap:") || strings.Contains(arg, "{text}") {
			continue
		}
		switch name {
		case "file.has_text", "file.lacks_text":
			if strings.Contains(string(src), arg) != (name == "file.has_text") {
				return false, nil
			}
		case "file.has_re", "file.lacks_re":
			re, err := cachedRe(arg)
			if err != nil {
				return false, fmt.Errorf("filter %s: %w", name, err)
			}
			if re.Match(src) != (name == "file.has_re") {
				return false, nil
			}
		case "dir.has_file", "dir.lacks_file":
			if t.Dir == "" {
				continue // in-memory source (rulecheck examples): no directory to look at
			}
			if dirHasFile(t.Dir, t.ScanRoot, strings.Split(arg, "|")) != (name == "dir.has_file") {
				return false, nil
			}
		case "sfc.has_re", "sfc.lacks_re":
			re, err := cachedRe(arg)
			if err != nil {
				return false, fmt.Errorf("filter %s: %w", name, err)
			}
			whole := t.SFC
			if whole == nil {
				whole = src
			}
			if re.Match(whole) != (name == "sfc.has_re") {
				return false, nil
			}
		}
	}
	return true, nil
}

// dupSiblingKey reports whether key (the key node of a pair/property) repeats the key of an
// earlier member of the same object. Linear per key instead of a pair-pair query, which is
// quadratic inside tree-sitter on large objects (i18n files with thousands of keys).
func dupSiblingKey(key ts.Node, src []byte) bool {
	pair := key.Parent()
	if pair == nil {
		return false
	}
	want := key.Utf8Text(src)
	for p := pair.PrevNamedSibling(); p != nil; p = p.PrevNamedSibling() {
		if p.Kind() != pair.Kind() {
			continue
		}
		if k := p.ChildByFieldName("key"); k != nil && k.Utf8Text(src) == want {
			return true
		}
	}
	return false
}

func attrRe(name string) *regexp.Regexp {
	if v, ok := filterRe.Load(name); ok {
		return v.(*regexp.Regexp)
	}
	re := regexp.MustCompile(`(^|\s)(:|v-bind:)?` + regexp.QuoteMeta(name) + `(\s*=|\s|>|/)`)
	filterRe.Store(name, re)
	return re
}

// FilterNames lists the registered post-filters (rules may only reference these).
var FilterNames = []string{
	"vue.start_tag_lacks_attr", "node.lacks_ancestor", "node.has_ancestor", "file.lacks_text",
	"file.has_text", "node.lacks_descendant_text", "node.has_descendant_text", "node.not_in_try_with_resources",
	"file.has_re", "file.lacks_re", "sfc.has_re", "sfc.lacks_re", "node.has_re", "node.lacks_re", "parent.has_re", "parent.lacks_re",
	"file.count_ge", "file.count_lt", "node.is_root", "func.has_re", "func.lacks_re", "cap.has_re", "cap.lacks_re",
	"ancestor.has_re", "ancestor.lacks_re", "parentkind.has_re", "parentkind.lacks_re", "node.dup_sibling_key", "dir.has_file", "dir.lacks_file",
	"metric.gt", "metric.ge", "branches.dup_body", "branches.all_same", "branches.dup_cond",
	"func.count_lt", "func.count_ge", "func.returns_invariant",
}

// dirHasFile reports whether one of names exists in dir or a parent directory up to root
// (a monorepo keeps one lockfile at the workspace root).
func dirHasFile(dir, root string, names []string) bool {
	for d := dir; ; d = filepath.Dir(d) {
		for _, n := range names {
			if _, err := os.Stat(filepath.Join(d, n)); err == nil {
				return true
			}
		}
		if d == root || !strings.HasPrefix(d, root) || filepath.Dir(d) == d {
			return false
		}
	}
}

// capRef: "{cap:NAME}" in a regex filter is replaced by the quoted text of capture @NAME of the
// same match (e.g. the loop variable), so filters can relate the candidate to its context.
var capRef = regexp.MustCompile(`\{cap:([A-Za-z_][\w.-]*)\}`)

func needCaps(r *rules.Rule) bool {
	for _, f := range r.Detection.Filters {
		if strings.Contains(f, "{cap:") || strings.HasPrefix(f, "cap.") {
			return true
		}
	}
	return false
}

// funcKinds are the function-like nodes that bound "func.*" filters, across grammars.
var funcKinds = map[string]bool{
	"function_declaration": true, "method_declaration": true, "func_literal": true, "function_definition": true,
	"arrow_function": true, "function_expression": true, "method_definition": true, "function": true,
	"lambda_expression": true, "constructor_declaration": true, "anonymous_function": true, "lambda_literal": true,
	"generator_function_declaration": true, "anonymous_function_creation_expression": true, "secondary_constructor": true,
}

// enclosingFunc returns the nearest function-like ancestor (or nil).
func enclosingFunc(n ts.Node) *ts.Node {
	for p := n.Parent(); p != nil; p = p.Parent() {
		if funcKinds[p.Kind()] {
			return p
		}
	}
	return nil
}

// cachedRe compiles filter regexes once.
func cachedRe(expr string) (*regexp.Regexp, error) {
	if v, ok := filterRe.Load("re:" + expr); ok {
		return v.(*regexp.Regexp), nil
	}
	re, err := regexp.Compile(expr)
	if err != nil {
		return nil, err
	}
	filterRe.Store("re:"+expr, re)
	return re, nil
}

// PassFilters implements named Go post-filters for conditions queries cannot express
// (mostly "absence" checks). Unknown filters are an error so packs fail validation.
func PassFilters(r *rules.Rule, n ts.Node, src []byte, caps map[string]string) (bool, error) {
	for _, f := range r.Detection.Filters {
		name, arg, _ := strings.Cut(f, ":")
		dynamic := false
		if caps != nil && strings.Contains(arg, "{cap:") {
			dynamic = true
			arg = capRef.ReplaceAllStringFunc(arg, func(m string) string {
				if v, ok := caps[capRef.FindStringSubmatch(m)[1]]; ok {
					return regexp.QuoteMeta(v)
				}
				return `\x00\x01` // capture absent in this match: matches nothing
			})
		}
		switch name {
		case "taint.clean": // evaluated by Run, which has the tree (cleanByTaint)
		case "vue.start_tag_lacks_attr":
			if attrRe(arg).MatchString(n.Utf8Text(src)) {
				return false, nil
			}
		case "node.lacks_ancestor", "node.has_ancestor":
			found := false
			for _, a := range strings.Split(arg, "|") {
				for p := n.Parent(); p != nil; p = p.Parent() {
					if p.Kind() == a {
						found = true
						break
					}
				}
			}
			if found != (name == "node.has_ancestor") {
				return false, nil
			}
		case "node.not_in_try_with_resources":
			for p := n.Parent(); p != nil; p = p.Parent() {
				if p.Kind() == "resource_specification" {
					return false, nil
				}
				if p.Kind() == "method_declaration" || p.Kind() == "lambda_expression" {
					break
				}
			}
		case "file.lacks_text":
			if strings.Contains(string(src), arg) {
				return false, nil
			}
		case "file.has_text":
			if !strings.Contains(string(src), arg) {
				return false, nil
			}
		case "node.lacks_descendant_text":
			if strings.Contains(n.Utf8Text(src), arg) {
				return false, nil
			}
		case "node.has_descendant_text":
			if !strings.Contains(n.Utf8Text(src), arg) {
				return false, nil
			}
		case "file.has_re", "file.lacks_re", "node.has_re", "node.lacks_re", "parent.has_re", "parent.lacks_re", "func.has_re", "func.lacks_re":
			var re *regexp.Regexp
			var err error
			if dynamic { // match-specific: do not grow the cache
				re, err = regexp.Compile(arg)
			} else {
				re, err = cachedRe(arg)
			}
			if err != nil {
				return false, fmt.Errorf("filter %s: %w", name, err)
			}
			subject := string(src)
			if strings.HasPrefix(name, "func.") {
				if fn := enclosingFunc(n); fn != nil {
					subject = fn.Utf8Text(src)
				}
			} else if strings.HasPrefix(name, "node.") {
				subject = n.Utf8Text(src)
			} else if strings.HasPrefix(name, "parent.") {
				subject = ""
				if p := n.Parent(); p != nil {
					subject = p.Utf8Text(src)
				}
			}
			if re.MatchString(subject) != strings.HasSuffix(name, "has_re") {
				return false, nil
			}
		case "cap.has_re", "cap.lacks_re":
			// cap.has_re:NAME:<regex> - the regex runs on the text of capture @NAME of the same
			// match (e.g. a loop body), so a guard can look at one part of the matched construct.
			cname, expr, ok := strings.Cut(arg, ":")
			if !ok {
				return false, fmt.Errorf("filter %s wants NAME:regex", name)
			}
			var re *regexp.Regexp
			var err error
			if dynamic {
				re, err = regexp.Compile(expr)
			} else {
				re, err = cachedRe(expr)
			}
			if err != nil {
				return false, fmt.Errorf("filter %s: %w", name, err)
			}
			subject, present := caps[cname]
			if !present && name == "cap.has_re" {
				return false, nil
			}
			if present && re.MatchString(subject) != (name == "cap.has_re") {
				return false, nil
			}
		case "ancestor.has_re", "ancestor.lacks_re":
			// ancestor.lacks_re:KIND[|KIND...]:<regex> - the regex runs on the nearest ancestor of
			// one of the kinds (no such ancestor: has_re fails, lacks_re passes).
			kinds, expr, ok := strings.Cut(arg, ":")
			if !ok {
				return false, fmt.Errorf("filter %s wants KIND:regex", name)
			}
			re, err := cachedRe(expr)
			if err != nil {
				return false, fmt.Errorf("filter %s: %w", name, err)
			}
			want := strings.Split(kinds, "|")
			var anc *ts.Node
			for p := n.Parent(); p != nil && anc == nil; p = p.Parent() {
				for _, k := range want {
					if p.Kind() == k {
						anc = p
						break
					}
				}
			}
			has := anc != nil && re.MatchString(anc.Utf8Text(src))
			if has != (name == "ancestor.has_re") {
				return false, nil
			}
		case "parentkind.has_re", "parentkind.lacks_re":
			// parentkind.lacks_re:KIND[|KIND...]:<regex> - the regex runs on the direct parent only
			// when the parent is one of the kinds (e.g. a literal that is a member of an all-literal
			// list/set/tuple, but not of an argument list).
			kinds, expr, ok := strings.Cut(arg, ":")
			if !ok {
				return false, fmt.Errorf("filter %s wants KIND:regex", name)
			}
			re, err := cachedRe(expr)
			if err != nil {
				return false, fmt.Errorf("filter %s: %w", name, err)
			}
			has := false
			if p := n.Parent(); p != nil && slices.Contains(strings.Split(kinds, "|"), p.Kind()) {
				has = re.MatchString(p.Utf8Text(src))
			}
			if has != (name == "parentkind.has_re") {
				return false, nil
			}
		case "func.returns_invariant":
			if !returnsInvariant(&n, src) {
				return false, nil
			}
		case "func.count_lt", "func.count_ge":
			// func.count_lt:N:<regex> - matches of the regex in the enclosing function (the node
			// itself when it is a function); {cap:NAME} references are quoted captures.
			ns, expr, ok := strings.Cut(arg, ":")
			want, err := strconv.Atoi(ns)
			if !ok || err != nil {
				return false, fmt.Errorf("filter %s wants N:regex", name)
			}
			var re *regexp.Regexp
			if dynamic {
				re, err = regexp.Compile(expr)
			} else {
				re, err = cachedRe(expr)
			}
			if err != nil {
				return false, fmt.Errorf("filter %s: %w", name, err)
			}
			scope := &n
			if !funcKinds[n.Kind()] {
				if fn := enclosingFunc(n); fn != nil {
					scope = fn
				}
			}
			c := len(re.FindAllStringIndex(scope.Utf8Text(src), want))
			if (c >= want) != (name == "func.count_ge") {
				return false, nil
			}
		case "metric.gt", "metric.ge":
			ok, err := metricFilter(name, arg, n, src)
			if err != nil || !ok {
				return false, err
			}
		case "branches.dup_body", "branches.all_same", "branches.dup_cond":
			if !branchFilter(name, n, src) {
				return false, nil
			}
		case "node.is_root":
			if n.Parent() != nil {
				return false, nil
			}
		case "node.dup_sibling_key":
			if !dupSiblingKey(n, src) {
				return false, nil
			}
		case "file.count_ge", "file.count_lt":
			// file.count_ge:N:<regex>  - {text} in the regex is replaced by the quoted node text.
			ns, expr, ok := strings.Cut(arg, ":")
			want, err := strconv.Atoi(ns)
			if !ok || err != nil {
				return false, fmt.Errorf("filter %s wants N:regex", name)
			}
			var re *regexp.Regexp
			if strings.Contains(expr, "{text}") { // node-specific: do not grow the cache
				re, err = regexp.Compile(strings.ReplaceAll(expr, "{text}", regexp.QuoteMeta(n.Utf8Text(src))))
			} else {
				re, err = cachedRe(expr)
			}
			if err != nil {
				return false, fmt.Errorf("filter %s: %w", name, err)
			}
			if c := len(re.FindAllIndex(src, want)); (c >= want) != (name == "file.count_ge") {
				return false, nil
			}
		case "sfc.has_re", "sfc.lacks_re", "dir.has_file", "dir.lacks_file": // whole-file gates, evaluated in fileGate
		default:
			return false, fmt.Errorf("unknown filter %q", name)
		}
	}
	return true, nil
}

var (
	scriptRe = regexp.MustCompile(`(?is)<script\b([^>]*)>(.*?)</script>`)
	langRe   = regexp.MustCompile(`(?i)\blang\s*=\s*["']?([a-z]+)`)
)

// VueScript returns the .vue source with everything outside <script> blocks blanked
// (newlines kept), so byte offsets and line numbers map 1:1 to the original file,
// plus the grammar to use (typescript, or tsx for lang="tsx"/"jsx") and the lang attribute.
func VueScript(src []byte) ([]byte, string, string, bool) {
	ms := scriptRe.FindAllSubmatchIndex(src, -1)
	if len(ms) == 0 {
		return nil, "", "", false
	}
	out := make([]byte, len(src))
	for i, c := range src {
		if c == '\n' {
			out[i] = '\n'
		} else {
			out[i] = ' '
		}
	}
	grammar, lang := "typescript", "js"
	for _, m := range ms {
		copy(out[m[4]:m[5]], src[m[4]:m[5]])
		if l := langRe.FindSubmatch(src[m[2]:m[3]]); l != nil {
			lang = strings.ToLower(string(l[1]))
			if lang == "tsx" || lang == "jsx" {
				grammar = "tsx"
			}
		}
	}
	return out, grammar, lang, true
}

var symbolKinds = map[string]string{
	"class_declaration": "#", "interface_declaration": "#", "enum_declaration": "#", "record_declaration": "#",
	"method_declaration": "", "constructor_declaration": "", "function_declaration": "", "method_definition": "",
	"generator_function_declaration": "",
	// python / php / go / kotlin / scala-like declarations
	"function_definition": "", "class_definition": "#", "type_spec": "#", "object_declaration": "#", "trait_declaration": "#",
}

// enclosing builds "Outer#method" from the nearest named declarations.
func enclosing(n ts.Node, src []byte) string {
	var member, typ string
	for p := n.Parent(); p != nil; p = p.Parent() {
		sep, ok := symbolKinds[p.Kind()]
		if !ok {
			continue
		}
		name := p.ChildByFieldName("name")
		if name == nil {
			continue
		}
		if sep == "#" {
			if typ == "" {
				typ = name.Utf8Text(src)
			}
		} else if member == "" {
			member = name.Utf8Text(src)
		}
		if typ != "" {
			break
		}
	}
	if typ != "" && member != "" {
		return typ + "#" + member
	}
	return typ + member
}

// SExpr returns the tree as an S-expression (for `crev ast` / rule authoring).
func (t *Tree) SExpr() string { return t.tree.RootNode().ToSexp() }

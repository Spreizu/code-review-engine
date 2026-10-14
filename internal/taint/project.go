package taint

import (
	"path/filepath"
	"regexp"
	"strings"
	"sync"
)

// FuncSummary is the cross-file summary of one named function: which taint classes its return
// value carries from its parameters / its own sources, and which classes each positional
// parameter delivers to a sink inside it.
type FuncSummary struct {
	Name, Class, Pkg string
	Path             string // slash path of the defining file (relative to the scan root)
	Params           []string
	MinArity         int
	Variadic         bool
	WithParams, Own  T
	ParamSinks       []T
	SinkName         []string
}

// Index holds the function summaries of a project per syntax family. A call in one file uses a
// summary from another file only when the call provably names that function: the caller imports
// its module / class (or shares its package), and exactly one candidate passes that gate.
type Index struct {
	mu  sync.RWMutex
	fns map[string]map[string][]*FuncSummary // family -> name -> summaries
}

func NewIndex() *Index { return &Index{fns: map[string]map[string][]*FuncSummary{}} }

// Add records the summaries of one file.
func (x *Index) Add(family string, s []*FuncSummary) {
	x.mu.Lock()
	defer x.mu.Unlock()
	m := x.fns[family]
	if m == nil {
		m = map[string][]*FuncSummary{}
		x.fns[family] = m
	}
	for _, f := range s {
		if family == "java" && f.Class != "" && f.Class != stem(f.Path) {
			continue // nested/secondary classes are not reachable by their bare name from other files
		}
		m[f.Name] = append(m[f.Name], f)
	}
}

var (
	projMu  sync.RWMutex
	project *Index
)

// SetProject installs the cross-file index used by AnalyzeFullAt (nil disables cross-file flows).
func SetProject(x *Index) {
	projMu.Lock()
	project = x
	projMu.Unlock()
}

func currentProject() *Index {
	projMu.RLock()
	defer projMu.RUnlock()
	return project
}

func enclosingClass(f *N, src []byte) string {
	for p := f.Parent; p != nil; p = p.Parent {
		switch p.Kind {
		case "class_declaration", "class_definition", "object_declaration", "interface_declaration", "class", "enum_declaration":
			if n := p.F("name"); n != nil {
				return n.text(src)
			}
			for _, k := range p.Kids {
				if k.Kind == "type_identifier" || k.Kind == "simple_identifier" || k.Kind == "identifier" || k.Kind == "name" {
					return k.text(src)
				}
			}
			return "?"
		case "function_definition", "function_declaration", "method_declaration", "arrow_function", "function_expression", "lambda_expression":
			return "?" // nested function: not addressable from another file
		}
	}
	return ""
}

var pkgRe = regexp.MustCompile(`(?m)^\s*package\s+([\w.]+)`)

// receiverType is the named type of a Go method receiver (`func (s *pkg.Store) Find`).
func receiverType(f *N, src []byte) string {
	rec := f.F("receiver")
	if rec == nil {
		return ""
	}
	s := strings.TrimSpace(strings.Trim(rec.text(src), "()"))
	if s == "" || strings.ContainsAny(s, "[{]") {
		return ""
	}
	s = strings.ReplaceAll(s, "*", "")
	parts := strings.Fields(s)
	if len(parts) == 0 {
		return ""
	}
	typ := parts[len(parts)-1]
	if i := strings.LastIndexByte(typ, '.'); i >= 0 {
		typ = typ[i+1:]
	}
	if !identOnly.MatchString(typ) {
		return ""
	}
	return typ
}

// Summarize computes the cross-file summaries of the named functions of one file.
func Summarize(root *N, src []byte, family, path string, l *Lang) []*FuncSummary {
	sx := langs[family]
	if sx == nil || l == nil || root == nil {
		return nil
	}
	a := &analyzer{sx: sx, l: l, fam: family, src: src, file: string(src), summ: map[string]summary{}, seen: map[[3]uint32]bool{},
		srcFn: map[*N]bool{}, paramReach: map[[3]uint32]bool{}, onlyParam: -1}
	var fns []*N
	var walk func(n *N)
	walk = func(n *N) {
		if sx.funcs[n.Kind] {
			fns = append(fns, n)
		}
		for _, k := range n.Kids {
			walk(k)
		}
	}
	walk(root)
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
	pkg := ""
	if m := pkgRe.FindSubmatch(src); m != nil {
		pkg = string(m[1])
	}
	var out []*FuncSummary
	count := map[string]int{}
	for _, f := range fns {
		count[a.funcName(f)]++
	}
	for _, f := range fns {
		name := a.funcName(f)
		if name == "" || count[name] > 1 { // overloads: positions do not identify one body
			continue
		}
		cls := enclosingClass(f, src)
		if family == "go" && f.Kind == "method_declaration" {
			cls = receiverType(f, src)
			if cls == "" {
				continue
			}
		}
		if cls == "?" {
			continue
		}
		fs := &FuncSummary{Name: name, Class: cls, Pkg: pkg, Path: filepath.ToSlash(path)}
		ps := a.params(f)
		for _, p := range ps {
			pt := p.text(src)
			names := a.paramNames(p)
			pn := ""
			if len(names) > 0 {
				pn = names[0]
			}
			switch {
			case strings.HasPrefix(pt, "*") || strings.Contains(pt, "...") || p.Kind == "list_splat_pattern" || p.Kind == "dictionary_splat_pattern" || p.Kind == "rest_pattern" || p.Kind == "spread_parameter" || p.Kind == "variadic_parameter":
				fs.Variadic = true
			case strings.Contains(p.Kind, "default") || p.Kind == "optional_parameter" || p.Kind == "assignment_pattern" || strings.Contains(pt, "="):
			default:
				fs.MinArity++
			}
			fs.Params = append(fs.Params, pn)
		}
		if family == "python" && len(fs.Params) > 0 && cls != "" && (fs.Params[0] == "self" || fs.Params[0] == "cls") {
			fs.Params = fs.Params[1:]
			if fs.MinArity > 0 {
				fs.MinArity--
			}
		}
		if fs.Variadic {
			continue
		}
		s := a.summ[name]
		fs.WithParams, fs.Own = s.withParams, s.own
		fs.ParamSinks = make([]T, len(fs.Params))
		fs.SinkName = make([]string, len(fs.Params))
		off := len(ps) - len(fs.Params)
		for i := range fs.Params {
			a.hits, a.seen, a.phase, a.onlyParam = nil, map[[3]uint32]bool{}, 0, i+off
			a.run(f, true, true)
			for _, h := range a.hits {
				if strings.Contains(h.Evidence, ": parameter ") {
					fs.ParamSinks[i] |= classBit(h.Class)
					if fs.SinkName[i] == "" {
						fs.SinkName[i] = h.Sink
					}
				}
			}
		}
		a.onlyParam = -1
		if fs.WithParams == 0 && fs.Own == 0 && !anyT(fs.ParamSinks) && !sanitizesAll(fs) {
			continue
		}
		out = append(out, fs)
	}
	return out
}

func anyT(xs []T) bool {
	for _, x := range xs {
		if x != 0 {
			return true
		}
	}
	return false
}

// sanitizesAll: a function with parameters whose result carries none of them is worth keeping
// (it clears taint at cross-file call sites).
func sanitizesAll(f *FuncSummary) bool { return len(f.Params) > 0 && f.WithParams != all }

var (
	pyFromRe  = regexp.MustCompile(`(?ms)^\s*from\s+\.*([\w.]*?)\s+import\s+(\([^)]*\)|[^\n]*)`)
	pyImpRe   = regexp.MustCompile(`(?m)^\s*import\s+([\w., ]+)$`)
	jsImpRe   = regexp.MustCompile(`(?s)import\s+([^;'"]*?)\s+from\s+['"]([^'"]+)['"]`)
	jsReqRe   = regexp.MustCompile(`(?:const|let|var)\s+([^=;]+?)\s*=\s*require\(\s*['"]([^'"]+)['"]\s*\)`)
	goImpRe   = regexp.MustCompile(`"([^"\s]+)"`)
	wordRe    = regexp.MustCompile(`[\w$]+`)
	identOnly = regexp.MustCompile(`^[\w$]+$`)
)

func stem(p string) string {
	b := filepath.Base(p)
	return strings.TrimSuffix(b, filepath.Ext(b))
}

func hasWord(s, w string) bool {
	for _, x := range wordRe.FindAllString(s, -1) {
		if x == w {
			return true
		}
	}
	return false
}

func lastPart(s string) string {
	if i := strings.LastIndexAny(s, "./\\"); i >= 0 {
		return s[i+1:]
	}
	return s
}

func identRecv(recv string) string {
	s := strings.TrimPrefix(lastPart(strings.ReplaceAll(recv, "->", ".")), "$")
	s = strings.TrimPrefix(s, "*")
	if !identOnly.MatchString(s) {
		return ""
	}
	return s
}

func renamed(bind, name string) bool {
	return regexp.MustCompile(`\b` + regexp.QuoteMeta(name) + `\s+as\b|:\s*\w+\s*[,}]`).MatchString(bind)
}

func pyImportedClass(src, class, modName string) bool {
	for _, m := range pyFromRe.FindAllStringSubmatch(src, -1) {
		mod, names := m[1], m[2]
		if lastPart(mod) == modName && hasWord(names, class) && !strings.Contains(names, " as ") {
			return true
		}
	}
	return false
}

func pyConstructed(src, recv, class string) bool {
	r, c := regexp.QuoteMeta(recv), regexp.QuoteMeta(class)
	return regexp.MustCompile(`\b(?:self\.)?`+r+`\s*:\s*`+c+`\b`).MatchString(src) ||
		regexp.MustCompile(`\b(?:self\.)?`+r+`\s*=\s*`+c+`\s*\(`).MatchString(src)
}

func jsConstructed(src, recv, class string) bool {
	r, c := regexp.QuoteMeta(recv), regexp.QuoteMeta(class)
	return regexp.MustCompile(`\b`+r+`\s*=\s*new\s+`+c+`\s*[\(\.{]`).MatchString(src) ||
		regexp.MustCompile(`\b`+r+`\s*:\s*`+c+`\b`).MatchString(src)
}

func goTyped(src, recv, class string) bool {
	r := identRecv(recv)
	if r == "" {
		return false
	}
	re, c := regexp.QuoteMeta(r), regexp.QuoteMeta(class)
	return regexp.MustCompile(`\b`+re+`\s+\*?(\w+\.)?`+c+`\b`).MatchString(src) ||
		regexp.MustCompile(`\b`+re+`\s*:?=\s*&?(\w+\.)?`+c+`\{`).MatchString(src) ||
		regexp.MustCompile(`\b`+re+`\s*:?=\s*new\(`+c+`\)`).MatchString(src)
}

func goImported(src, fdir string) bool {
	if !strings.Contains(src, "import") {
		return false
	}
	for _, m := range goImpRe.FindAllStringSubmatch(src, -1) {
		if strings.HasSuffix(m[1], "/"+fdir) {
			return true
		}
	}
	return false
}

// gate reports whether a call from callerPath/callerSrc with receiver text recv provably names f.
func gate(family string, f *FuncSummary, recv, callerPath, callerSrc string) bool {
	if f.Path == callerPath {
		return false
	}
	fstem, fdir := stem(f.Path), filepath.Base(filepath.Dir(f.Path))
	modName := fstem
	if fstem == "__init__" || fstem == "index" {
		modName = fdir
	}
	// cheap prefilter: every gate below needs the module (python/js) or class (java/kotlin/php)
	// name in the caller's text; this keeps lookups linear when many files define the same name
	switch family {
	case "python", "javascript":
		if !strings.Contains(callerSrc, modName) {
			return false
		}
		if f.Class != "" && !strings.Contains(callerSrc, f.Class) {
			return false
		}
	case "java", "kotlin", "php":
		if f.Class == "" || !strings.Contains(callerSrc, f.Class) {
			return false
		}
	case "go":
		if f.Class != "" && !strings.Contains(callerSrc, f.Class) {
			return false
		}
	}
	switch family {
	case "python":
		if f.Class != "" {
			if !pyImportedClass(callerSrc, f.Class, modName) {
				return false
			}
			if recv == f.Class {
				return true
			}
			r := identRecv(recv)
			return r != "" && pyConstructed(callerSrc, r, f.Class)
		}
		for _, m := range pyFromRe.FindAllStringSubmatch(callerSrc, -1) {
			mod, names := m[1], m[2]
			if recv == "" && lastPart(mod) == modName && hasWord(names, f.Name) && !strings.Contains(names, " as ") {
				return true
			}
			if recv == modName && hasWord(names, modName) {
				return true
			}
		}
		if recv != "" {
			for _, m := range pyImpRe.FindAllStringSubmatch(callerSrc, -1) {
				for _, part := range strings.Split(m[1], ",") {
					if strings.TrimSpace(part) == recv && lastPart(recv) == modName {
						return true
					}
				}
			}
		}
	case "javascript":
		check := func(bind, path string) bool {
			if !strings.HasPrefix(path, ".") {
				return false
			}
			ps := stem(path)
			if ps != fstem && !(fstem == "index" && filepath.Base(path) == fdir) {
				return false
			}
			if f.Class != "" {
				if !hasWord(bind, f.Class) || renamed(bind, f.Class) {
					return false
				}
				if recv == f.Class {
					return true
				}
				r := identRecv(recv)
				return r != "" && jsConstructed(callerSrc, r, f.Class)
			}
			if recv == "" {
				return hasWord(bind, f.Name) && !renamed(bind, f.Name)
			}
			return hasWord(bind, recv)
		}
		for _, m := range jsImpRe.FindAllStringSubmatch(callerSrc, -1) {
			if check(m[1], m[2]) {
				return true
			}
		}
		for _, m := range jsReqRe.FindAllStringSubmatch(callerSrc, -1) {
			if check(m[1], m[2]) {
				return true
			}
		}
	case "go":
		if f.Class != "" {
			samePkg := filepath.Dir(f.Path) == filepath.Dir(callerPath) && f.Pkg != "" && pkgOf(callerSrc) == f.Pkg
			if !samePkg && !goImported(callerSrc, fdir) {
				return false
			}
			return goTyped(callerSrc, recv, f.Class)
		}
		if recv == "" {
			return filepath.Dir(f.Path) == filepath.Dir(callerPath) && f.Pkg != "" && pkgOf(callerSrc) == f.Pkg
		}
		if recv != f.Pkg {
			return false
		}
		return goImported(callerSrc, fdir)
	case "java", "kotlin":
		if f.Class == "" || recv == "" {
			return false
		}
		samePkg := f.Pkg != "" && pkgOf(callerSrc) == f.Pkg
		imported := regexp.MustCompile(`(?m)^\s*import\s+(static\s+)?[\w.]+\.` + regexp.QuoteMeta(f.Class) + `\s*;?\s*$`).MatchString(callerSrc)
		if !samePkg && !imported {
			return false
		}
		if recv == f.Class {
			return true
		}
		r := lastPart(recv)
		if !regexp.MustCompile(`^\w+$`).MatchString(r) {
			return false
		}
		c := regexp.QuoteMeta(f.Class)
		if family == "java" {
			return regexp.MustCompile(`\b` + c + `\s+` + regexp.QuoteMeta(r) + `\s*[;=,)]`).MatchString(callerSrc)
		}
		return regexp.MustCompile(`\b` + regexp.QuoteMeta(r) + `\s*:\s*` + c + `\b[^?<.]`).MatchString(callerSrc)
	case "php":
		if f.Class == "" || recv == "" {
			return false
		}
		sameDir := filepath.Dir(f.Path) == filepath.Dir(callerPath)
		used := regexp.MustCompile(`(?m)^\s*use\s+[\w\\]+\\` + regexp.QuoteMeta(f.Class) + `\s*;`).MatchString(callerSrc)
		if !sameDir && !used {
			return false
		}
		if recv == f.Class {
			return true
		}
		r := strings.TrimPrefix(lastPart(strings.ReplaceAll(recv, "->", ".")), "$")
		if !regexp.MustCompile(`^\w+$`).MatchString(r) {
			return false
		}
		c := regexp.QuoteMeta(f.Class)
		return regexp.MustCompile(`\b` + c + `\s+\$` + regexp.QuoteMeta(r) + `\b|\$` + regexp.QuoteMeta(r) + `\s*=\s*new\s+` + c + `\b`).MatchString(callerSrc)
	}
	return false
}

func pkgOf(src string) string {
	if m := pkgRe.FindStringSubmatch(src); m != nil {
		return m[1]
	}
	return ""
}

// lookup finds the one summary a call names, if any.
func (x *Index) lookup(family, name, recv, callerPath, callerSrc string, nargs int, kwnames []string) *FuncSummary {
	if x == nil {
		return nil
	}
	x.mu.RLock()
	cands := x.fns[family][name]
	x.mu.RUnlock()
	var hit *FuncSummary
	for _, f := range cands {
		if !gate(family, f, recv, callerPath, callerSrc) {
			continue
		}
		if hit != nil {
			return nil // ambiguous
		}
		hit = f
	}
	if hit == nil || nargs+len(kwnames) < hit.MinArity || nargs+len(kwnames) > len(hit.Params) {
		return nil
	}
	return hit
}

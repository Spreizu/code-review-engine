// Package index builds a repo-wide symbol index from tree-sitter: definitions (with normalised
// body fingerprints, size, complexity and pass-through detection), identifier references,
// call sites, imports (resolved to repo files where relative), manifest dependencies, test
// files and `limit:` notes (documented shortcuts). The simplification layer (checks.go) uses it as evidence:
// "nothing calls this", "this already exists at X", "this dependency is installed".
package index

import (
	"crypto/sha256"
	"encoding/hex"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
	"time"

	ts "github.com/tree-sitter/go-tree-sitter"

	"github.com/elmo/code-review-engine/internal/grammars"
)

// Symbol is one definition.
type Symbol struct {
	Name       string   `json:"name"`
	Kind       string   `json:"kind"` // func | method | type
	File       string   `json:"file"`
	Line       int      `json:"line"`
	EndLine    int      `json:"end_line"`
	Exported   bool     `json:"exported"`
	TopLevel   bool     `json:"top_level"`
	Container  string   `json:"container,omitempty"`
	BodyHash   string   `json:"body_hash,omitempty"`
	Stmts      int      `json:"stmts"`
	Params     []string `json:"params,omitempty"`
	Complexity int      `json:"complexity"`
	Delegate   string   `json:"delegate,omitempty"` // callee when the body only forwards its parameters
}

// Call is one call site.
type Call struct {
	Callee string `json:"callee"`
	File   string `json:"file"`
	Line   int    `json:"line"`
	Caller string `json:"caller,omitempty"`
}

// Loop is a loop over a collection nested inside another one, with an equality test inside
// (the classic O(n^2) find/dedupe shortcut).
type Loop struct {
	File      string `json:"file"`
	Line      int    `json:"line"` // outer loop
	EndLine   int    `json:"end_line"`
	InnerLine int    `json:"inner_line"`
	Func      string `json:"func,omitempty"`
	Outer     string `json:"outer,omitempty"` // iterated collections, when they can be named
	Inner     string `json:"inner,omitempty"`
}

// Comment is a limit note (`limit:` comment) or a lock declaration.
type Comment struct {
	File string `json:"file"`
	Line int    `json:"line"`
	Text string `json:"text"`
}

// File is per-file information.
type File struct {
	Lang    string    `json:"lang"`
	Lines   int       `json:"lines"`
	Test    bool      `json:"test"`
	Package string    `json:"package,omitempty"`
	Symbols []*Symbol `json:"symbols,omitempty"`
	Imports []string  `json:"imports,omitempty"`
	// TopLevelOther counts top-level statements that are not imports or definitions.
	TopLevelOther int `json:"top_level_other"`
}

// Index is the repo-wide index.
type Index struct {
	Root       string                    `json:"root"`
	Files      map[string]*File          `json:"files"`
	Defs       map[string][]*Symbol      `json:"-"`
	ByHash     map[string][]*Symbol      `json:"-"` // normalized body hash -> definitions
	Refs       map[string]int            `json:"-"` // identifier occurrences (all files, incl. text in templates)
	RefFiles   map[string]map[string]int `json:"-"` // name -> file -> occurrences
	Calls      map[string][]Call         `json:"-"` // callee -> sites
	ImportedBy map[string][]string       `json:"-"` // repo file -> importing files
	Deps       map[string]bool           `json:"deps"`
	TestIdents map[string]bool           `json:"-"`
	LimitNotes []Comment                 `json:"limit_notes,omitempty"`
	Loops      []Loop                    `json:"-"` // nested loops over collections
	Locks      []Comment                 `json:"-"` // package/module-level locks
	Stats      map[string]int            `json:"stats"`
	Duration   time.Duration             `json:"-"`
	srcs       map[string][]byte
}

var extLang = map[string]string{
	".go": "go", ".py": "python", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
	".ts": "typescript", ".mts": "typescript", ".cts": "typescript", ".tsx": "tsx", ".java": "java", ".kt": "kotlin", ".kts": "kotlin", ".php": "php",
}

// textExt are files scanned for identifier references only (templates, configs).
var textExt = map[string]bool{".vue": true, ".html": true, ".svelte": true, ".astro": true, ".json": true, ".yaml": true, ".yml": true, ".xml": true, ".toml": true, ".md": false}

// LangOf returns the index language for a path ("" if not indexed).
func LangOf(rel string) string { return extLang[strings.ToLower(filepath.Ext(rel))] }

var testRe = regexp.MustCompile(`(^|/)(tests?|__tests__|spec|testdata|src/test)/|_test\.go$|(^|/)test_[^/]+\.py$|_test\.py$|\.(test|spec)\.[cm]?[jt]sx?$|Tests?\.(java|kt|php)$|(^|/)conftest\.py$`)

// IsTest reports whether rel looks like a test file.
func IsTest(rel string) bool { return testRe.MatchString(rel) }

// Build indexes the given repo-relative files. deps are manifest dependency names.
func Build(root string, files []string, deps map[string]bool) *Index {
	start := time.Now()
	x := &Index{Root: root, Files: map[string]*File{}, Defs: map[string][]*Symbol{}, Refs: map[string]int{}, RefFiles: map[string]map[string]int{},
		Calls: map[string][]Call{}, ImportedBy: map[string][]string{}, Deps: deps, TestIdents: map[string]bool{}, Stats: map[string]int{}, srcs: map[string][]byte{}}
	if x.Deps == nil {
		x.Deps = map[string]bool{}
	}
	parsers := map[string]*ts.Parser{}
	defer func() {
		for _, p := range parsers {
			p.Close()
		}
	}()
	var rawImports = map[string][]string{}
	for _, rel := range files {
		ext := strings.ToLower(filepath.Ext(rel))
		lang := extLang[ext]
		if lang == "" {
			if textExt[ext] {
				if b, err := os.ReadFile(filepath.Join(root, rel)); err == nil && len(b) < 2<<20 {
					x.textRefs(rel, b)
				}
			}
			continue
		}
		b, err := os.ReadFile(filepath.Join(root, rel))
		if err != nil || len(b) > 2<<20 {
			continue
		}
		p := parsers[lang]
		if p == nil {
			p = ts.NewParser()
			if p.SetLanguage(grammars.Get(lang)) != nil {
				continue
			}
			parsers[lang] = p
		}
		tree := p.Parse(b, nil)
		if tree == nil {
			continue
		}
		f := &File{Lang: lang, Lines: strings.Count(string(b), "\n") + 1, Test: IsTest(rel)}
		x.Files[rel] = f
		x.srcs[rel] = b
		w := &walker{x: x, rel: rel, f: f, src: b, spec: specs[lang], ptEnd: -1}
		w.walk(tree.RootNode(), nil, 0)
		rawImports[rel] = f.Imports
		tree.Close()
	}
	for rel, imps := range rawImports {
		seen := map[string]bool{}
		for _, spec := range imps {
			if t := x.resolve(rel, spec); t != "" && t != rel && !seen[t] {
				seen[t] = true
				x.ImportedBy[t] = append(x.ImportedBy[t], rel)
			}
		}
	}
	for _, l := range x.ImportedBy {
		slices.Sort(l)
	}
	x.Duration = time.Since(start)
	x.Stats["files"] = len(x.Files)
	x.ByHash = map[string][]*Symbol{}
	for _, l := range x.Defs {
		x.Stats["symbols"] += len(l)
		for _, s := range l {
			if s.BodyHash != "" {
				x.ByHash[s.BodyHash] = append(x.ByHash[s.BodyHash], s)
			}
		}
	}
	for _, l := range x.Calls {
		x.Stats["calls"] += len(l)
	}
	x.Stats["imports_resolved"] = 0
	for _, l := range x.ImportedBy {
		x.Stats["imports_resolved"] += len(l)
	}
	x.Stats["deps"] = len(x.Deps)
	x.Stats["limit_notes"] = len(x.LimitNotes)
	return x
}

// Source returns the indexed source of rel.
func (x *Index) Source(rel string) []byte { return x.srcs[rel] }

var wordRe = regexp.MustCompile(`[A-Za-z_$][A-Za-z0-9_$]*`)

func (x *Index) textRefs(rel string, b []byte) {
	for _, w := range wordRe.FindAll(b, -1) {
		x.ref(string(w), rel, IsTest(rel))
	}
}

func (x *Index) ref(name, rel string, test bool) {
	x.Refs[name]++
	m := x.RefFiles[name]
	if m == nil {
		m = map[string]int{}
		x.RefFiles[name] = m
	}
	m[rel]++
	if test {
		x.TestIdents[name] = true
	}
}

// RefsOutside counts references to name excluding the definition's own name token.
func (x *Index) RefsOutside(s *Symbol) int {
	n := x.Refs[s.Name] - len(x.Defs[s.Name])
	if n < 0 {
		return 0
	}
	return n
}

var jsExts = []string{"", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".vue", ".d.ts", "/index.ts", "/index.tsx", "/index.js", "/index.jsx", "/index.mjs", "/index.vue"}

// resolve maps an import spec from file rel to a repo file ("" if external/unknown).
func (x *Index) resolve(rel, spec string) string {
	lang := x.Files[rel].Lang
	switch lang {
	case "javascript", "typescript", "tsx":
		if !strings.HasPrefix(spec, ".") && !strings.HasPrefix(spec, "@/") && !strings.HasPrefix(spec, "~/") && !strings.HasPrefix(spec, "src/") {
			return ""
		}
		var base string
		switch {
		case strings.HasPrefix(spec, "@/") || strings.HasPrefix(spec, "~/"):
			base = path.Join("src", spec[2:])
			if t := x.tryExts(base); t != "" {
				return t
			}
			base = spec[2:]
		case strings.HasPrefix(spec, "src/"):
			base = spec
		default:
			base = path.Join(path.Dir(rel), spec)
		}
		// strip .js written for .ts sources (NodeNext style)
		if t := x.tryExts(base); t != "" {
			return t
		}
		return x.tryExts(strings.TrimSuffix(strings.TrimSuffix(base, ".js"), ".mjs"))
	case "python":
		dots := len(spec) - len(strings.TrimLeft(spec, "."))
		mod := strings.ReplaceAll(strings.TrimLeft(spec, "."), ".", "/")
		var cands []string
		if dots > 0 {
			d := path.Dir(rel)
			for i := 1; i < dots; i++ {
				d = path.Dir(d)
			}
			cands = []string{path.Join(d, mod) + ".py", path.Join(d, mod, "__init__.py")}
		} else {
			cands = []string{mod + ".py", mod + "/__init__.py", "src/" + mod + ".py", "src/" + mod + "/__init__.py"}
		}
		for _, c := range cands {
			if _, ok := x.Files[c]; ok {
				return c
			}
		}
	}
	return ""
}

func (x *Index) tryExts(base string) string {
	for _, e := range jsExts {
		if _, ok := x.Files[base+e]; ok {
			return base + e
		}
	}
	return ""
}

func shortHash(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:8])
}

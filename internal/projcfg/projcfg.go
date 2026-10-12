// Package projcfg discovers the project's own linter / compiler configuration and inline
// suppression comments, so crev does not re-report what the team explicitly switched off.
//
// Model: crev rules carry "tool:id" equivalents (rules/data/xref.yaml + rule xref entries).
// Config files produce Directives (tool, id, on/off, options, directory + file-glob scope);
// inline comments produce line-range suppressions. A finding is suppressed-by-config only when
// an explicit user setting turns an equivalent rule off for that file/line: a linter merely
// being installed, or a rule not being enabled, never hides crev findings.
package projcfg

import (
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
	"sync"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/glob"
)

// Directive is one explicit setting from a config file.
type Directive struct {
	Tool   string         `json:"tool"`
	ID     string         `json:"id"` // "*" = every rule of the tool
	Off    bool           `json:"off"`
	Params map[string]any `json:"params,omitempty"`
	Base   string         `json:"base"`             // repo-relative dir the config applies to ("" = root)
	Files  []string       `json:"files,omitempty"`  // globs relative to Base (any match); empty = all files under Base
	Ignore []string       `json:"ignore,omitempty"` // globs relative to Base excluded from this directive
	Paths  []string       `json:"paths,omitempty"`  // regexes on the repo-relative path (golangci exclude-rules)
	Source string         `json:"source"`           // repo-relative config file
	order  int
}

// SuppressedBy explains why a finding is suppressed.
type SuppressedBy = findings.SuppressedBy

// Set is everything discovered for a repo.
type Set struct {
	Root       string
	Directives []Directive
	Sources    []string // config files that produced directives
	Present    []string // every recognised config file found (read or not)
	Errors     []string
	inline     sync.Map // rel -> *FileInline
	// ConfigOff disables config-file directives (respect_project_config: false); inline
	// crev-ignore comments are always honoured, linter inline disables only when ConfigOff is false.
	ConfigOff bool
}

// Check decides whether a finding is suppressed by project configuration or inline comments.
func (s *Set) Check(rel string, src []byte, ruleID string, equivalents []string, start, end int) *SuppressedBy {
	if s == nil {
		return ParseInline(rel, src).crevOnly().Match(rel, ruleID, nil, start, end)
	}
	if !s.ConfigOff {
		if d := s.Decide(equivalents, rel); d != nil {
			return &SuppressedBy{Kind: "config", Tool: d.Tool, ID: d.ID, Source: d.Source}
		}
	}
	v, ok := s.inline.Load(rel)
	if !ok {
		fi := ParseInline(rel, src)
		if s.ConfigOff {
			fi = fi.crevOnly()
		}
		v, _ = s.inline.LoadOrStore(rel, fi)
	}
	return v.(*FileInline).Match(rel, ruleID, equivalents, start, end)
}

// Applies reports whether d covers the repo-relative path rel.
func (d *Directive) Applies(rel string) bool {
	sub := rel
	if d.Base != "" {
		if !strings.HasPrefix(rel, d.Base+"/") {
			return false
		}
		sub = strings.TrimPrefix(rel, d.Base+"/")
	}
	for _, g := range d.Ignore {
		if matchRel(g, sub) {
			return false
		}
	}
	if len(d.Paths) > 0 {
		ok := false
		for _, p := range d.Paths {
			if re, err := regexp.Compile(p); err == nil && re.MatchString(rel) {
				ok = true
			}
		}
		if !ok {
			return false
		}
	}
	if len(d.Files) == 0 {
		return true
	}
	for _, g := range d.Files {
		if matchRel(g, sub) {
			return true
		}
	}
	return false
}

// matchRel matches a config glob: patterns without a slash match the base name at any depth
// (gitignore/editorconfig/ESLint-legacy semantics); "./" prefixes are dropped.
func matchRel(g, rel string) bool {
	g = strings.TrimPrefix(g, "./")
	g = strings.TrimPrefix(g, "/")
	if g == "" {
		return false
	}
	if strings.HasSuffix(g, "/") {
		g += "**"
	}
	if glob.Match(g, rel) {
		return true
	}
	if !strings.Contains(g, "/") && glob.Match(g, filepath.Base(rel)) {
		return true
	}
	return strings.HasSuffix(g, "/**") && glob.Match(strings.TrimSuffix(g, "/**"), rel)
}

func idMatch(dID, want string) bool {
	if dID == "*" || dID == want {
		return true
	}
	// pylint equivalents are "CODE/symbol": either half may be configured
	if i := strings.IndexByte(want, '/'); i > 0 && !strings.Contains(want, "@") && (dID == want[:i] || dID == want[i+1:]) {
		return true
	}
	return false
}

// prefixTools use rule-code prefixes in configuration ("S" ignores every S### rule, "E5" E5xx).
var prefixTools = map[string]bool{"ruff": true, "flake8": true}

func (d *Directive) matches(tool, id string) bool {
	if d.Tool != tool {
		return false
	}
	if idMatch(d.ID, id) {
		return true
	}
	if re, ok := strings.CutPrefix(d.ID, "re:"); ok {
		if r, err := regexp.Compile(re); err == nil && r.MatchString(id) {
			return true
		}
	}
	if p, ok := strings.CutSuffix(d.ID, "*"); ok && p != "" && strings.HasPrefix(id, p) {
		return true
	}
	if prefixTools[tool] && d.ID != "" && strings.HasPrefix(id, d.ID) && (d.ID == "ALL" || isUpperAlpha(d.ID) || len(d.ID) < len(id)) {
		return true
	}
	return tool == "ruff" && d.ID == "ALL"
}

func isUpperAlpha(s string) bool {
	for _, r := range s {
		if r < 'A' || r > 'Z' {
			return false
		}
	}
	return true
}

// Decide returns the directive that turns one of the equivalents off for rel, or nil. Later and
// deeper directives win, so an override that re-enables a rule beats an earlier "off".
func (s *Set) Decide(equivalents []string, rel string) *Directive {
	if s == nil {
		return nil
	}
	for _, eq := range equivalents {
		tool, id, ok := strings.Cut(eq, ":")
		if !ok {
			continue
		}
		var last *Directive
		for i := range s.Directives {
			d := &s.Directives[i]
			if d.matches(tool, id) && d.Applies(rel) {
				if last == nil || len(d.Base) > len(last.Base) || (len(d.Base) == len(last.Base) && d.order >= last.order) {
					last = d
				}
			}
		}
		if last != nil && last.Off {
			return last
		}
	}
	return nil
}

// Enables reports whether the project config turns one of the equivalents on for rel: the most
// specific matching directive naming that rule (not a tool-wide "*") is not "off". Opt-in
// rules only report where this holds.
func (s *Set) Enables(equivalents []string, rel string) bool {
	if s == nil {
		return false
	}
	for _, eq := range equivalents {
		tool, id, ok := strings.Cut(eq, ":")
		if !ok {
			continue
		}
		var last *Directive
		for i := range s.Directives {
			d := &s.Directives[i]
			if d.ID == "*" || !d.matches(tool, id) || !d.Applies(rel) {
				continue
			}
			if last == nil || len(d.Base) > len(last.Base) || (len(d.Base) == len(last.Base) && d.order >= last.order) {
				last = d
			}
		}
		if last != nil && !last.Off {
			return true
		}
	}
	return false
}

// Param returns the most specific option value named key for one of the equivalents.
func (s *Set) Param(equivalents []string, rel, key string) (any, *Directive) {
	if s == nil {
		return nil, nil
	}
	var best *Directive
	var val any
	for _, eq := range equivalents {
		tool, id, _ := strings.Cut(eq, ":")
		for i := range s.Directives {
			d := &s.Directives[i]
			if d.Params == nil || !d.matches(tool, id) || !d.Applies(rel) {
				continue
			}
			if v, ok := d.Params[key]; ok && (best == nil || len(d.Base) > len(best.Base) || d.order >= best.order) {
				best, val = d, v
			}
		}
	}
	return val, best
}

func (s *Set) add(d Directive) {
	d.order = len(s.Directives)
	s.Directives = append(s.Directives, d)
}

// Discover walks the repo for known configuration files (skipping files the walker reports as
// excluded) and parses them. files is the list of repo-relative paths seen by the scanner,
// including excluded ones (configs live in dot-files that review may skip).
func Discover(root string, files []string) *Set {
	s := &Set{Root: root}
	slices.Sort(files)
	for _, rel := range files {
		base := filepath.Base(rel)
		dir := filepath.ToSlash(filepath.Dir(rel))
		if dir == "." {
			dir = ""
		}
		p := parsers[base]
		if p == nil {
			for pat, fn := range globParsers {
				if ok, _ := filepath.Match(pat, base); ok {
					p = fn
				}
			}
		}
		if p == nil {
			continue
		}
		s.Present = append(s.Present, rel)
		b, err := os.ReadFile(filepath.Join(root, rel))
		if err != nil {
			continue
		}
		n := len(s.Directives)
		if err := p(s, ctx{rel: rel, dir: dir, root: root}, b); err != nil {
			s.Errors = append(s.Errors, rel+": "+err.Error())
		}
		if len(s.Directives) > n {
			s.Sources = append(s.Sources, rel)
		}
	}
	return s
}

type ctx struct{ rel, dir, root string }

func (c ctx) d(tool, id string, off bool) Directive {
	return Directive{Tool: tool, ID: id, Off: off, Base: c.dir, Source: c.rel}
}

type parser func(s *Set, c ctx, b []byte) error

var parsers = map[string]parser{}
var globParsers = map[string]parser{}

func register(p parser, names ...string) {
	for _, n := range names {
		if strings.ContainsAny(n, "*?[") {
			globParsers[n] = p
		} else {
			parsers[n] = p
		}
	}
}

// ConfigFileNames lists the files Discover understands (so the scanner can collect them even
// when they are excluded from review).
func IsConfigFile(base string) bool {
	if parsers[base] != nil {
		return true
	}
	for pat := range globParsers {
		if ok, _ := filepath.Match(pat, base); ok {
			return true
		}
	}
	return false
}

// ParamFrom resolves the first available "tool:id.option" source for rel.
func (s *Set) ParamFrom(from []string, rel string) (any, string) {
	if s == nil || s.ConfigOff {
		return nil, ""
	}
	for _, f := range from {
		eq, opt, ok := strings.Cut(f, ".")
		if !ok {
			continue
		}
		if i := strings.LastIndex(f, "."); i > 0 {
			eq, opt = f[:i], f[i+1:]
		}
		if v, d := s.Param([]string{eq}, rel, opt); d != nil && v != nil && toString(v) != "" && toString(v) != "off" {
			return v, d.Source
		}
	}
	return nil, ""
}

// toolFiles: config file names that, by their presence, mean the project adopted a tool.
// (.editorconfig is not listed: it only counts through the properties it sets.)
var toolFiles = map[string][]string{
	"yamllint": {".yamllint", ".yamllint.yaml", ".yamllint.yml"},
	"prettier": {".prettierrc", ".prettierrc.json", ".prettierrc.yaml", ".prettierrc.yml", ".prettierrc.js", ".prettierrc.cjs", ".prettierrc.mjs", "prettier.config.js", "prettier.config.cjs", "prettier.config.mjs"},
}

// Configures reports whether the project configures tool (a config file was read for it or
// it produced directives). Rules with detection.requires_config only run when this holds.
func (s *Set) Configures(tool string) bool {
	if s == nil {
		return false
	}
	if slices.ContainsFunc(s.Directives, func(d Directive) bool { return d.Tool == tool }) {
		return true
	}
	return slices.ContainsFunc(s.Present, func(src string) bool { return slices.Contains(toolFiles[tool], filepath.Base(src)) })
}

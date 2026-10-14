package taint

import (
	"fmt"
	"regexp"
	"sync"

	catalog "github.com/elmo/code-review-engine/rules"
	"gopkg.in/yaml.v3"
)

// Classes are the vulnerability classes, in bit order.
var Classes = []string{"sqli", "cmdi", "path", "ldap", "xss", "ssrf", "redirect", "xpath", "code", "trust", "smtp", "regex"}

func classBit(c string) T {
	for i, x := range Classes {
		if x == c {
			return 1 << i
		}
	}
	return 0
}

// T is a taint mask: bit i set = the value is attacker-controlled and not sanitised for Classes[i].
type T uint16

const all T = 1<<12 - 1

type rawSink struct {
	Callee   string `yaml:"callee"`
	Args     []int  `yaml:"args"`
	When     string `yaml:"when"`
	Unless   string `yaml:"unless"`
	File     string `yaml:"file"`
	ReturnIn string `yaml:"return_in"`
	// UnlessSource skips the flow when its recorded source matches (e.g. http.ServeFile with the
	// request's own r.URL.Path, which ServeFile itself screens for "..").
	UnlessSource string `yaml:"unless_source"`
	// UnlessParent skips the call when the whitespace-free text of the expression directly
	// containing it matches (new File(x).getName() only takes the last path segment).
	UnlessParent string `yaml:"unless_parent"`
	// UnlessFile skips the sink in files whose source matches (e.g. Django REST framework's
	// Response, which renders through content negotiation, not as raw HTML).
	UnlessFile string `yaml:"unless_file"`
	// UnlessFunc skips the sink when the enclosing function's text matches (e.g. a redirect in a
	// function that strips a leading "//" before redirecting to a same-origin path).
	UnlessFunc string `yaml:"unless_func"`
	Note       string `yaml:"note"`
}

type rawLang struct {
	Sources      []rawSource `yaml:"sources"`
	ParamSources []string    `yaml:"param_sources"`
	// ContextSources are request reads that are not treated as attacker data (e.g. a route-matched
	// path) but still mark the function as a request handler for clean-sink decisions.
	ContextSources string               `yaml:"context_sources"`
	RouteParams    string               `yaml:"route_params"`
	Sanitizers     map[string][]string  `yaml:"sanitizers"`
	Sinks          map[string][]rawSink `yaml:"sinks"`
	Mutators       string               `yaml:"mutators"`
	// framework param_sources / route_params, each only in files matching the framework imports
	guardedParams []rawSource
	guardedRoutes []rawSource
}

type rawSource struct {
	Re   string `yaml:"re"`
	File string `yaml:"file"`
}

type rawSpec struct {
	Languages map[string]rawLang `yaml:"languages"`
}

// rawFramework is one framework model from data/frameworks.yaml: request sources, parameter
// binding, sanitizers and sinks of that framework, merged into its language block. Sources and
// sinks without their own file guard only apply in files matching Imports.
type rawFramework struct {
	Name     string `yaml:"name"`
	Language string `yaml:"language"`
	Doc      string `yaml:"doc"`
	Imports  string `yaml:"imports"`
	rawLang  `yaml:",inline"`
}

type rawFrameworks struct {
	Frameworks []rawFramework `yaml:"frameworks"`
}

// mergeFrameworks folds framework models into the language blocks of a spec document.
func mergeFrameworks(raw *rawSpec, fw []byte) error {
	var f rawFrameworks
	if err := yaml.Unmarshal(fw, &f); err != nil {
		return err
	}
	for _, m := range f.Frameworks {
		l, ok := raw.Languages[m.Language]
		if !ok {
			return fmt.Errorf("framework %s: unknown language %q", m.Name, m.Language)
		}
		if m.Imports == "" || m.Doc == "" {
			return fmt.Errorf("framework %s: needs imports and doc", m.Name)
		}
		for _, s := range m.Sources {
			if s.File == "" {
				s.File = m.Imports
			}
			l.Sources = append(l.Sources, s)
		}
		for _, p := range m.ParamSources {
			l.guardedParams = append(l.guardedParams, rawSource{p, m.Imports})
		}
		if m.RouteParams != "" {
			l.guardedRoutes = append(l.guardedRoutes, rawSource{m.RouteParams, m.Imports})
		}
		if m.ContextSources != "" {
			if l.ContextSources != "" {
				l.ContextSources += "|"
			}
			l.ContextSources += m.ContextSources
		}
		for c, xs := range m.Sanitizers {
			if l.Sanitizers == nil {
				l.Sanitizers = map[string][]string{}
			}
			l.Sanitizers[c] = append(l.Sanitizers[c], xs...)
		}
		for c, xs := range m.Sinks {
			if l.Sinks == nil {
				l.Sinks = map[string][]rawSink{}
			}
			for _, k := range xs {
				if k.File == "" {
					k.File = m.Imports
				}
				l.Sinks[c] = append(l.Sinks[c], k)
			}
		}
		raw.Languages[m.Language] = l
	}
	return nil
}

type sink struct {
	class     T
	name      string
	callee    *regexp.Regexp
	args      []int
	when      *regexp.Regexp
	unless    *regexp.Regexp
	file      *regexp.Regexp
	returnIn  *regexp.Regexp
	unlessSrc *regexp.Regexp
	unlessPar *regexp.Regexp
	unlessFil *regexp.Regexp
	unlessFn  *regexp.Regexp
}

type source struct {
	re   *regexp.Regexp
	file *regexp.Regexp
}

type sanitizer struct {
	mask T // bits cleared
	re   *regexp.Regexp
}

// Lang is the compiled spec of one syntax family.
type Lang struct {
	sources      []source
	paramSources *regexp.Regexp
	routeParams  *regexp.Regexp
	sanitizers   []sanitizer
	sinks        []sink
	mutators     *regexp.Regexp
	context      *regexp.Regexp
	// framework-model param sources and route decorators, guarded by file
	guardedParams []source
	guardedRoutes []source
}

func (l *Lang) guarded(xs []source, text, file string) bool {
	for _, s := range xs {
		if s.re.MatchString(text) && (s.file == nil || s.file.MatchString(file)) {
			return true
		}
	}
	return false
}

var (
	specOnce sync.Once
	spec     map[string]*Lang
	specErr  error
)

func re(s string) (*regexp.Regexp, error) {
	if s == "" {
		return nil, nil
	}
	return regexp.Compile(s)
}

// Spec returns the compiled spec of a syntax family (nil when it has none).
func Spec(family string) (*Lang, error) {
	specOnce.Do(func() {
		b, err := catalog.FS.ReadFile("data/taint.yaml")
		if err != nil {
			specErr = err
			return
		}
		fw, err := catalog.FS.ReadFile("data/frameworks.yaml")
		if err != nil {
			specErr = err
			return
		}
		spec, specErr = Compile(b, fw)
	})
	if specErr != nil {
		return nil, specErr
	}
	return spec[family], nil
}

// Compile parses a taint spec document, merged with optional framework model documents.
func Compile(b []byte, frameworks ...[]byte) (map[string]*Lang, error) {
	var raw rawSpec
	if err := yaml.Unmarshal(b, &raw); err != nil {
		return nil, err
	}
	for _, fw := range frameworks {
		if err := mergeFrameworks(&raw, fw); err != nil {
			return nil, err
		}
	}
	out := map[string]*Lang{}
	for name, rl := range raw.Languages {
		l := &Lang{}
		var err error
		bad := func(what string, e error) error { return fmt.Errorf("taint spec %s: %s: %w", name, what, e) }
		for _, s := range rl.Sources {
			r, err := re(s.Re)
			if err != nil {
				return nil, bad("source", err)
			}
			f, err := re(s.File)
			if err != nil {
				return nil, bad("source file", err)
			}
			l.sources = append(l.sources, source{r, f})
		}
		for _, g := range []struct {
			src []rawSource
			dst *[]source
		}{{rl.guardedParams, &l.guardedParams}, {rl.guardedRoutes, &l.guardedRoutes}} {
			for _, x := range g.src {
				r, err := re(x.Re)
				if err != nil {
					return nil, bad("framework param/route", err)
				}
				f, err := re(x.File)
				if err != nil {
					return nil, bad("framework imports", err)
				}
				*g.dst = append(*g.dst, source{r, f})
			}
		}
		if len(rl.ParamSources) > 0 {
			pat := ""
			for i, p := range rl.ParamSources {
				if i > 0 {
					pat += "|"
				}
				pat += p
			}
			if l.paramSources, err = re(pat); err != nil {
				return nil, bad("param_sources", err)
			}
		}
		if l.routeParams, err = re(rl.RouteParams); err != nil {
			return nil, bad("route_params", err)
		}
		if l.context, err = re(rl.ContextSources); err != nil {
			return nil, bad("context_sources", err)
		}
		if l.mutators, err = re(rl.Mutators); err != nil {
			return nil, bad("mutators", err)
		}
		for cls, pats := range rl.Sanitizers {
			mask := all
			if cls != "all" {
				if mask = classBit(cls); mask == 0 {
					return nil, bad("sanitizer class", fmt.Errorf("unknown class %q", cls))
				}
			}
			for _, p := range pats {
				r, err := re(p)
				if err != nil {
					return nil, bad("sanitizer", err)
				}
				l.sanitizers = append(l.sanitizers, sanitizer{mask, r})
			}
		}
		for cls, sinks := range rl.Sinks {
			bit := classBit(cls)
			if bit == 0 {
				return nil, bad("sink class", fmt.Errorf("unknown class %q", cls))
			}
			for _, s := range sinks {
				k := sink{class: bit, name: cls, args: s.Args}
				for _, p := range []struct {
					dst **regexp.Regexp
					src string
				}{{&k.callee, s.Callee}, {&k.when, s.When}, {&k.unless, s.Unless}, {&k.file, s.File}, {&k.returnIn, s.ReturnIn}, {&k.unlessSrc, s.UnlessSource}, {&k.unlessPar, s.UnlessParent}, {&k.unlessFil, s.UnlessFile}, {&k.unlessFn, s.UnlessFunc}} {
					if *p.dst, err = re(p.src); err != nil {
						return nil, bad("sink "+cls, err)
					}
				}
				if k.callee == nil && k.returnIn == nil {
					return nil, bad("sink "+cls, fmt.Errorf("needs callee or return_in"))
				}
				l.sinks = append(l.sinks, k)
			}
		}
		out[name] = l
	}
	return out, nil
}

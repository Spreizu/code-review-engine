// Package sca finds known-vulnerable dependencies: it parses lockfiles / manifests with pinned
// versions and matches the packages against OSV.dev advisories (https://osv.dev), online through
// the querybatch API or offline against the per-ecosystem database exports downloaded by
// `crev vulndb update`.
package sca

import (
	"bufio"
	"bytes"
	"encoding/json"
	"encoding/xml"
	"io/fs"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

// OSV ecosystem names (https://ossf.github.io/osv-schema/#defined-ecosystems).
const (
	EcoNPM       = "npm"
	EcoPackagist = "Packagist"
	EcoGo        = "Go"
	EcoPyPI      = "PyPI"
	EcoMaven     = "Maven"
)

// Ecosystems supported by the lockfile parsers.
var Ecosystems = []string{EcoNPM, EcoPackagist, EcoGo, EcoPyPI, EcoMaven}

// Package is one resolved dependency.
type Package struct {
	Ecosystem string `json:"ecosystem"`
	Name      string `json:"name"`
	Version   string `json:"version"`
	File      string `json:"file"` // lockfile, relative to the root
	Line      int    `json:"line"`
	Dev       bool   `json:"dev,omitempty"`
}

// Key identifies a package version within an ecosystem.
func (p Package) Key() string { return p.Ecosystem + "\x00" + p.Name + "\x00" + p.Version }

type parser func(rel string, b []byte) ([]Package, error)

// lockfiles maps a file name to its parser. go.sum is only read when the directory has no go.mod.
var lockfiles = map[string]parser{
	"package-lock.json":   parseNPMLock,
	"npm-shrinkwrap.json": parseNPMLock,
	"yarn.lock":           parseYarnLock,
	"pnpm-lock.yaml":      parsePNPMLock,
	"composer.lock":       parseComposerLock,
	"go.mod":              parseGoMod,
	"go.sum":              parseGoSum,
	"poetry.lock":         parsePoetryLock,
	"Pipfile.lock":        parsePipfileLock,
	"gradle.lockfile":     parseGradleLock,
	"pom.xml":             parsePom,
}

var requirementsRe = regexp.MustCompile(`^requirements[\w.-]*\.txt$`)

// skipDirs are never searched for lockfiles (dependency trees, VCS, caches).
var skipDirs = map[string]bool{"node_modules": true, "vendor": true, ".git": true, ".venv": true, "venv": true,
	"__pycache__": true, "dist": true, "build": true, "target": true, ".gradle": true, ".crev": true, "testdata": true}

// IsLockfile reports whether a base name is a supported lockfile / manifest.
func IsLockfile(base string) bool {
	_, ok := lockfiles[base]
	return ok || requirementsRe.MatchString(base)
}

// Discover parses every supported lockfile under root. skip(rel, isDir) excludes paths (crev
// ignore globs, .gitignore, default excluded directories: engine.PathFilter); dependency trees
// (node_modules, vendor, ...) are always skipped.
func Discover(root string, skip func(rel string, isDir bool) bool) ([]Package, []string, error) {
	var pkgs []Package
	var errs []string
	err := filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		rel, _ := filepath.Rel(root, p)
		rel = filepath.ToSlash(rel)
		if d.IsDir() {
			if p == root {
				if skip != nil {
					skip(".", true)
				}
				return nil
			}
			if skipDirs[d.Name()] || (skip != nil && skip(rel, true)) {
				return filepath.SkipDir
			}
			return nil
		}
		base := d.Name()
		if !IsLockfile(base) || (skip != nil && skip(rel, false)) {
			return nil
		}
		if base == "go.sum" {
			if _, err := os.Stat(filepath.Join(filepath.Dir(p), "go.mod")); err == nil {
				return nil
			}
		}
		b, err := os.ReadFile(p)
		if err != nil {
			errs = append(errs, rel+": "+err.Error())
			return nil
		}
		ps, err := ParseFile(rel, b)
		if err != nil {
			errs = append(errs, "sca: "+rel+": "+err.Error())
			return nil
		}
		pkgs = append(pkgs, ps...)
		return nil
	})
	return pkgs, errs, err
}

// ParseFile parses one lockfile by its base name.
func ParseFile(rel string, b []byte) ([]Package, error) {
	base := filepath.Base(rel)
	f := lockfiles[base]
	if f == nil && requirementsRe.MatchString(base) {
		f = parseRequirements
	}
	if f == nil {
		return nil, nil
	}
	ps, err := f(rel, b)
	for i := range ps {
		ps[i].File = rel
		if ps[i].Line == 0 {
			ps[i].Line = lineOf(b, ps[i].Name, ps[i].Version)
		}
	}
	return dedup(ps), err
}

func dedup(ps []Package) []Package {
	seen := map[string]bool{}
	out := ps[:0]
	for _, p := range ps {
		if p.Name == "" || p.Version == "" || seen[p.Key()] {
			continue
		}
		seen[p.Key()] = true
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].Line < out[j].Line })
	return out
}

// lineOf finds the first line mentioning the package name (and the version, when on that line or
// within the next few lines); 1 when not found.
func lineOf(b []byte, name, version string) int {
	lines := bytes.Split(b, []byte("\n"))
	short := name
	if i := strings.LastIndex(name, ":"); i >= 0 { // maven group:artifact
		short = name[i+1:]
	}
	first := 0
	for i, l := range lines {
		if !bytes.Contains(l, []byte(short)) {
			continue
		}
		if first == 0 {
			first = i + 1
		}
		for j := i; j < len(lines) && j < i+6; j++ {
			if bytes.Contains(lines[j], []byte(version)) {
				return i + 1
			}
		}
	}
	return max(first, 1)
}

// ---- npm ----

func parseNPMLock(_ string, b []byte) ([]Package, error) {
	var l struct {
		Packages map[string]struct {
			Version string `json:"version"`
			Name    string `json:"name"`
			Dev     bool   `json:"dev"`
			Link    bool   `json:"link"`
		} `json:"packages"`
		Dependencies map[string]json.RawMessage `json:"dependencies"`
	}
	if err := json.Unmarshal(b, &l); err != nil {
		return nil, err
	}
	var out []Package
	if len(l.Packages) > 0 { // lockfileVersion 2/3
		for k, v := range l.Packages {
			i := strings.LastIndex(k, "node_modules/")
			if k == "" || i < 0 || v.Link || v.Version == "" {
				continue
			}
			name := v.Name
			if name == "" {
				name = k[i+len("node_modules/"):]
			}
			out = append(out, Package{Ecosystem: EcoNPM, Name: name, Version: v.Version, Dev: v.Dev})
		}
		return out, nil
	}
	var walk func(deps map[string]json.RawMessage)
	walk = func(deps map[string]json.RawMessage) { // lockfileVersion 1: nested dependencies
		for name, raw := range deps {
			var d struct {
				Version      string                     `json:"version"`
				Dev          bool                       `json:"dev"`
				Dependencies map[string]json.RawMessage `json:"dependencies"`
			}
			if json.Unmarshal(raw, &d) != nil {
				continue
			}
			if d.Version != "" && !strings.Contains(d.Version, ":") { // skip file:, git+ URLs
				out = append(out, Package{Ecosystem: EcoNPM, Name: name, Version: d.Version, Dev: d.Dev})
			}
			walk(d.Dependencies)
		}
	}
	walk(l.Dependencies)
	return out, nil
}

// yarn.lock v1 ("name@range", version "x") and berry ("name@npm:range": version: x).
func parseYarnLock(_ string, b []byte) ([]Package, error) {
	var out []Package
	var names []string
	line := 0
	start := 0
	sc := bufio.NewScanner(bytes.NewReader(b))
	sc.Buffer(make([]byte, 1<<20), 1<<24)
	for sc.Scan() {
		line++
		t := sc.Text()
		if t == "" || strings.HasPrefix(t, "#") {
			continue
		}
		if !strings.HasPrefix(t, " ") && strings.HasSuffix(t, ":") { // entry header
			names, start = nil, line
			for _, spec := range strings.Split(strings.TrimSuffix(t, ":"), ",") {
				spec = strings.Trim(strings.TrimSpace(spec), `"`)
				at := strings.LastIndex(spec, "@")
				if at <= 0 {
					continue
				}
				rng := spec[at+1:]
				if strings.HasPrefix(rng, "workspace:") || strings.HasPrefix(rng, "link:") || strings.HasPrefix(rng, "file:") || strings.HasPrefix(rng, "portal:") || strings.HasPrefix(rng, "patch:") {
					continue
				}
				names = append(names, spec[:at])
			}
			continue
		}
		tt := strings.TrimSpace(t)
		if len(names) > 0 && (strings.HasPrefix(tt, "version ") || strings.HasPrefix(tt, "version:")) && strings.HasPrefix(t, "  ") && !strings.HasPrefix(t, "    ") {
			v := strings.Trim(strings.TrimSpace(strings.TrimPrefix(strings.TrimPrefix(tt, "version:"), "version ")), `"`)
			seen := map[string]bool{}
			for _, n := range names {
				if !seen[n] {
					seen[n] = true
					out = append(out, Package{Ecosystem: EcoNPM, Name: n, Version: v, Line: start})
				}
			}
			names = nil
		}
	}
	return out, sc.Err()
}

var (
	pnpmKeyRe   = regexp.MustCompile(`^  ['"]?/?((?:@[^/@\s]+/)?[^/@\s(]+)[@/]([0-9][^\s('":]*)`)
	pnpmTopRe   = regexp.MustCompile(`^(packages|snapshots):\s*$`)
	pnpmOtherRe = regexp.MustCompile(`^\S`)
)

// pnpm-lock.yaml v5-v9: keys under packages:/snapshots: are /name/1.2.3, /name@1.2.3 or name@1.2.3(peer...).
func parsePNPMLock(_ string, b []byte) ([]Package, error) {
	var out []Package
	in := false
	for i, l := range strings.Split(string(b), "\n") {
		switch {
		case pnpmTopRe.MatchString(l):
			in = true
			continue
		case pnpmOtherRe.MatchString(l):
			in = false
			continue
		}
		if !in {
			continue
		}
		if m := pnpmKeyRe.FindStringSubmatch(l); m != nil {
			out = append(out, Package{Ecosystem: EcoNPM, Name: m[1], Version: m[2], Line: i + 1})
		}
	}
	return out, nil
}

// ---- composer ----

func parseComposerLock(_ string, b []byte) ([]Package, error) {
	var l struct {
		Packages    []struct{ Name, Version string } `json:"packages"`
		PackagesDev []struct{ Name, Version string } `json:"packages-dev"`
	}
	if err := json.Unmarshal(b, &l); err != nil {
		return nil, err
	}
	var out []Package
	add := func(ps []struct{ Name, Version string }, dev bool) {
		for _, p := range ps {
			v := strings.TrimPrefix(p.Version, "v")
			if strings.HasPrefix(v, "dev-") {
				continue
			}
			out = append(out, Package{Ecosystem: EcoPackagist, Name: p.Name, Version: v, Dev: dev})
		}
	}
	add(l.Packages, false)
	add(l.PackagesDev, true)
	return out, nil
}

// ---- Go ----

var goReqRe = regexp.MustCompile(`^\s*(?:require\s+)?([^\s()]+)\s+(v[0-9][^\s]*)`)

func goVersion(v string) string {
	v = strings.TrimSuffix(v, "+incompatible")
	return strings.TrimPrefix(v, "v")
}

func parseGoMod(_ string, b []byte) ([]Package, error) {
	var out []Package
	inReq := false
	for i, l := range strings.Split(string(b), "\n") {
		t := strings.TrimSpace(l)
		if c := strings.Index(t, "//"); c >= 0 && !strings.Contains(t[c:], "indirect") {
			t = strings.TrimSpace(t[:c])
		}
		switch {
		case strings.HasPrefix(t, "require ("):
			inReq = true
			continue
		case t == ")":
			inReq = false
			continue
		}
		if !inReq && !strings.HasPrefix(t, "require ") {
			continue
		}
		if m := goReqRe.FindStringSubmatch(t); m != nil {
			out = append(out, Package{Ecosystem: EcoGo, Name: m[1], Version: goVersion(m[2]), Line: i + 1})
		}
	}
	// The standard library (OSV module "stdlib") only from an explicit toolchain line: the go
	// directive is a minimum language version, not the toolchain that builds the binary.
	for i, l := range strings.Split(string(b), "\n") {
		if f := strings.Fields(l); len(f) == 2 && f[0] == "toolchain" && strings.HasPrefix(f[1], "go") {
			out = append(out, Package{Ecosystem: EcoGo, Name: "stdlib", Version: strings.TrimPrefix(f[1], "go"), Line: i + 1})
			break
		}
	}
	return out, nil
}

func parseGoSum(_ string, b []byte) ([]Package, error) {
	var out []Package
	for i, l := range strings.Split(string(b), "\n") {
		f := strings.Fields(l)
		if len(f) < 2 || strings.HasSuffix(f[1], "/go.mod") {
			continue
		}
		out = append(out, Package{Ecosystem: EcoGo, Name: f[0], Version: goVersion(f[1]), Line: i + 1})
	}
	return out, nil
}

// ---- Python ----

var pyNormRe = regexp.MustCompile(`[-_.]+`)

// PyName normalises a PyPI project name (PEP 503).
func PyName(n string) string { return strings.ToLower(pyNormRe.ReplaceAllString(n, "-")) }

var tomlKVRe = regexp.MustCompile(`^(\w+)\s*=\s*"([^"]*)"`)

func parsePoetryLock(_ string, b []byte) ([]Package, error) {
	var out []Package
	var cur *Package
	for i, l := range strings.Split(string(b), "\n") {
		t := strings.TrimSpace(l)
		if t == "[[package]]" {
			out = append(out, Package{Ecosystem: EcoPyPI, Line: i + 1})
			cur = &out[len(out)-1]
			continue
		}
		if strings.HasPrefix(t, "[") {
			cur = nil
			continue
		}
		if cur == nil {
			continue
		}
		if m := tomlKVRe.FindStringSubmatch(t); m != nil {
			switch m[1] {
			case "name":
				cur.Name = PyName(m[2])
			case "version":
				cur.Version = m[2]
			case "category":
				cur.Dev = m[2] == "dev"
			}
		}
	}
	return out, nil
}

func parsePipfileLock(_ string, b []byte) ([]Package, error) {
	var l map[string]json.RawMessage
	if err := json.Unmarshal(b, &l); err != nil {
		return nil, err
	}
	var out []Package
	for _, sec := range []string{"default", "develop"} {
		var deps map[string]struct {
			Version string `json:"version"`
		}
		if json.Unmarshal(l[sec], &deps) != nil {
			continue
		}
		for n, d := range deps {
			if v, ok := strings.CutPrefix(d.Version, "=="); ok {
				out = append(out, Package{Ecosystem: EcoPyPI, Name: PyName(n), Version: v, Dev: sec == "develop"})
			}
		}
	}
	return out, nil
}

var reqRe = regexp.MustCompile(`^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?\s*===?\s*([0-9][^\s;#,]*)\s*(?:[;#].*)?$`)

// requirements*.txt: only exact pins (name==version) identify a version.
func parseRequirements(_ string, b []byte) ([]Package, error) {
	var out []Package
	for i, l := range strings.Split(string(b), "\n") {
		t := strings.TrimSpace(strings.TrimSuffix(l, "\\"))
		if m := reqRe.FindStringSubmatch(t); m != nil {
			out = append(out, Package{Ecosystem: EcoPyPI, Name: PyName(m[1]), Version: m[2], Line: i + 1})
		}
	}
	return out, nil
}

// ---- Maven / Gradle ----

func parseGradleLock(_ string, b []byte) ([]Package, error) {
	var out []Package
	for i, l := range strings.Split(string(b), "\n") {
		t := strings.TrimSpace(l)
		if t == "" || strings.HasPrefix(t, "#") || strings.HasPrefix(t, "empty=") {
			continue
		}
		coord, _, _ := strings.Cut(t, "=")
		p := strings.Split(coord, ":")
		if len(p) == 3 {
			out = append(out, Package{Ecosystem: EcoMaven, Name: p[0] + ":" + p[1], Version: p[2], Line: i + 1})
		}
	}
	return out, nil
}

var propRefRe = regexp.MustCompile(`\$\{([^}]+)\}`)

// pom.xml: direct dependencies with a literal or ${property} version (no parent/BOM resolution).
func parsePom(_ string, b []byte) ([]Package, error) {
	var pom struct {
		Version    string                   `xml:"version"`
		Parent     struct{ Version string } `xml:"parent"`
		Properties struct {
			Any []struct {
				XMLName xml.Name
				Value   string `xml:",chardata"`
			} `xml:",any"`
		} `xml:"properties"`
		Deps []struct {
			GroupID    string `xml:"groupId"`
			ArtifactID string `xml:"artifactId"`
			Version    string `xml:"version"`
			Scope      string `xml:"scope"`
		} `xml:"dependencies>dependency"`
		Managed []struct {
			GroupID    string `xml:"groupId"`
			ArtifactID string `xml:"artifactId"`
			Version    string `xml:"version"`
			Scope      string `xml:"scope"`
		} `xml:"dependencyManagement>dependencies>dependency"`
	}
	if err := xml.Unmarshal(b, &pom); err != nil {
		return nil, err
	}
	props := map[string]string{"project.version": pom.Version, "project.parent.version": pom.Parent.Version}
	for _, p := range pom.Properties.Any {
		props[p.XMLName.Local] = strings.TrimSpace(p.Value)
	}
	resolve := func(v string) string {
		for i := 0; i < 3 && strings.Contains(v, "${"); i++ {
			v = propRefRe.ReplaceAllStringFunc(v, func(s string) string { return props[s[2:len(s)-1]] })
		}
		return strings.TrimSpace(v)
	}
	var out []Package
	for _, d := range append(pom.Deps, pom.Managed...) {
		v := resolve(d.Version)
		if v == "" || strings.ContainsAny(v, "[]()${},") || d.Scope == "import" {
			continue // ranges, unresolved properties, BOM imports
		}
		out = append(out, Package{Ecosystem: EcoMaven, Name: strings.TrimSpace(d.GroupID) + ":" + strings.TrimSpace(d.ArtifactID), Version: v, Dev: d.Scope == "test"})
	}
	return out, nil
}

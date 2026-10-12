package versions

import (
	"encoding/json"
	"maps"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"

	"gopkg.in/yaml.v3"
)

// Fact is one detected version dimension.
type Fact struct {
	Version string `json:"version"`
	Source  string `json:"source"`
	Assumed bool   `json:"assumed,omitempty"` // true when "assume latest" filled it in
}

// Unit is a build unit (directory with pom.xml/build.gradle/package.json/tsconfig).
type Unit struct {
	Dir   string          `json:"dir"`
	Facts map[string]Fact `json:"facts"`
	Deps  map[string]bool `json:"dependencies"`
}

// Latest loads rules/data/latest-versions.yaml.
func Latest(path string) map[string]string {
	out := map[string]string{"java": "27", "spring-boot": "4.1.1", "spring-framework": "7.0.9", "spring-security": "7.0",
		"vue": "3.5.43", "nuxt": "4.6.0", "typescript": "7.0.2", "ecmascript": "2026"}
	b, err := os.ReadFile(path)
	if err != nil {
		return out
	}
	return mergeLatest(out, b)
}

// LatestFrom parses latest-versions.yaml content (e.g. from the embedded catalog).
func LatestFrom(b []byte) map[string]string { return mergeLatest(Latest(""), b) }

func mergeLatest(out map[string]string, b []byte) map[string]string {
	var f struct {
		Latest map[string]string `yaml:"latest"`
	}
	if yaml.Unmarshal(b, &f) == nil {
		maps.Copy(out, f.Latest)
	}
	return out
}

func (u *Unit) set(k, v, src string) {
	v = Normalize(k, v)
	if v == "" || !regexp.MustCompile(`^\d`).MatchString(v) {
		return
	}
	if _, ok := u.Facts[k]; !ok {
		u.Facts[k] = Fact{Version: v, Source: src}
	}
}

// Get returns a fact version; ok=false when the dimension is absent.
func (u *Unit) Get(k string) (string, bool) {
	f, ok := u.Facts[k]
	return f.Version, ok
}

var (
	pomParent   = regexp.MustCompile(`(?s)<parent>.*?<artifactId>\s*spring-boot-starter-parent\s*</artifactId>.*?<version>\s*([^<\s]+)\s*</version>.*?</parent>`)
	pomBootDeps = regexp.MustCompile(`(?s)<artifactId>\s*spring-boot-dependencies\s*</artifactId>\s*<version>\s*([^<\s]+)`)
	pomProp     = func(n string) *regexp.Regexp {
		return regexp.MustCompile(`<` + regexp.QuoteMeta(n) + `>\s*([^<\s]+)\s*</`)
	}
	pomRelease = regexp.MustCompile(`<(?:release|source)>\s*(\d[^<\s]*)\s*</`)
	pomDep     = regexp.MustCompile(`(?s)<dependency>\s*<groupId>\s*([^<\s]+)\s*</groupId>\s*<artifactId>\s*([^<\s]+)\s*</artifactId>`)
	gradleBoot = regexp.MustCompile(`(?:id\s*\(?\s*["']org\.springframework\.boot["']\s*\)?\s*version\s*["']([^"']+)["'])|(?:spring-boot-gradle-plugin:([0-9][^"')]+))`)
	gradleJava = regexp.MustCompile(`(?:JavaLanguageVersion\.of\(\s*(\d+)\s*\))|(?:(?:sourceCompatibility|targetCompatibility)\s*=\s*(?:JavaVersion\.VERSION_)?["']?(\d+(?:[._]\d+)?))|(?:jvmToolchain\(\s*(\d+)\s*\))`)
	gradleDep  = regexp.MustCompile(`["']([A-Za-z0-9_.\-]+):([A-Za-z0-9_.\-]+)(?::([^"'@]+))?["']`)
	nuxtCompat = regexp.MustCompile(`compatibilityVersion\s*:\s*(\d+)`)
)

func read(p string) string {
	b, err := os.ReadFile(p)
	if err != nil {
		return ""
	}
	return string(b)
}

// bootToFramework / bootToSecurity map a Spring Boot minor to the managed Spring
// Framework / Spring Security generation (Spring Boot dependency-versions appendix).
func bootDerived(boot string) (fw, sec string) {
	p := parts(boot)
	if len(p) < 2 {
		p = append(p, 0)
	}
	switch {
	case p[0] == 2:
		return "5.3", "5." + map[int]string{4: "4", 5: "5", 6: "6", 7: "7"}[p[1]]
	case p[0] == 3:
		fw = map[int]string{0: "6.0", 1: "6.0", 2: "6.1", 3: "6.1", 4: "6.2", 5: "6.2"}[p[1]]
		sec = map[int]string{0: "6.0", 1: "6.1", 2: "6.2", 3: "6.3", 4: "6.4", 5: "6.5"}[p[1]]
		return
	case p[0] == 4:
		return "7.0", "7.0"
	}
	return "", ""
}

// DetectUnit reads build files of one directory. Missing files are fine.
func DetectUnit(dir string) *Unit {
	u := &Unit{Dir: dir, Facts: map[string]Fact{}, Deps: map[string]bool{}}
	if pom := read(filepath.Join(dir, "pom.xml")); pom != "" {
		if m := pomParent.FindStringSubmatch(pom); m != nil {
			u.set("spring-boot", m[1], "pom.xml parent")
		}
		if m := pomBootDeps.FindStringSubmatch(pom); m != nil {
			u.set("spring-boot", m[1], "pom.xml spring-boot-dependencies")
		}
		if m := pomProp("spring-boot.version").FindStringSubmatch(pom); m != nil {
			u.set("spring-boot", m[1], "pom.xml <spring-boot.version>")
		}
		for _, p := range []string{"maven.compiler.release", "java.version", "maven.compiler.source", "maven.compiler.target"} {
			if m := pomProp(p).FindStringSubmatch(pom); m != nil {
				u.set("java", m[1], "pom.xml <"+p+">")
			}
		}
		if m := pomRelease.FindStringSubmatch(pom); m != nil {
			u.set("java", m[1], "pom.xml compiler plugin")
		}
		for _, m := range pomDep.FindAllStringSubmatch(pom, -1) {
			u.Deps[m[1]+":"+m[2]] = true
		}
	}
	for _, g := range []string{"build.gradle", "build.gradle.kts"} {
		s := read(filepath.Join(dir, g))
		if s == "" {
			continue
		}
		if m := gradleBoot.FindStringSubmatch(s); m != nil {
			u.set("spring-boot", m[1]+m[2], g+" plugin")
		}
		if m := gradleJava.FindStringSubmatch(s); m != nil {
			u.set("java", strings.ReplaceAll(m[1]+m[2]+m[3], "_", "."), g)
		}
		for _, m := range gradleDep.FindAllStringSubmatch(s, -1) {
			u.Deps[m[1]+":"+m[2]] = true
			if m[1] == "org.springframework.boot" && m[3] != "" {
				u.set("spring-boot", m[3], g+" dependency")
			}
		}
	}
	if pj := read(filepath.Join(dir, "package.json")); pj != "" {
		var p struct {
			Dependencies, DevDependencies, PeerDependencies map[string]string
			Engines                                         map[string]string
		}
		_ = json.Unmarshal([]byte(pj), &p)
		lock := lockVersions(dir)
		for _, deps := range []map[string]string{p.Dependencies, p.DevDependencies, p.PeerDependencies} {
			for name, spec := range deps {
				u.Deps[name] = true
				key := npmKeys[name]
				if key == "" {
					continue
				}
				if v, ok := lock[name]; ok {
					u.set(key, v, "lockfile")
					continue
				}
				if i := strings.LastIndex(spec, "@"); strings.HasPrefix(spec, "npm:") && i > 0 {
					spec = spec[i+1:]
				}
				u.set(key, firstVersion(spec), "package.json "+name)
			}
		}
	}
	for _, n := range []string{"nuxt.config.ts", "nuxt.config.js", "nuxt.config.mjs"} {
		if s := read(filepath.Join(dir, n)); s != "" {
			if m := nuxtCompat.FindStringSubmatch(s); m != nil {
				u.Facts["nuxt.compatibilityVersion"] = Fact{Version: m[1], Source: n}
			}
			if _, ok := u.Facts["nuxt"]; !ok {
				u.Facts["nuxt"] = Fact{Source: n} // present, version unknown
			}
		}
	}
	if tc := readTSConfig(filepath.Join(dir, "tsconfig.json"), 0); tc != nil {
		for k, v := range tc {
			u.Facts["tsconfig.compilerOptions."+k] = Fact{Version: strings.ToLower(strings.Trim(jsonString(v), `"`)), Source: "tsconfig.json"}
		}
		if t, ok := tc["target"]; ok {
			s := strings.ToLower(strings.Trim(jsonString(t), `"`))
			if s != "esnext" {
				u.set("ecmascript", s, "tsconfig.json target")
			}
		}
		if _, ok := u.Facts["typescript"]; !ok {
			u.Facts["typescript"] = Fact{Source: "tsconfig.json"}
		}
	}
	detectMore(dir, u)
	if u.Facts["spring-boot"].Version != "" {
		fw, sec := bootDerived(u.Facts["spring-boot"].Version)
		if fw != "" {
			u.Facts["spring-framework"] = Fact{Version: fw, Source: "derived from spring-boot"}
		}
		if sec != "" && !strings.HasSuffix(sec, ".") {
			u.Facts["spring-security"] = Fact{Version: sec, Source: "derived from spring-boot"}
		}
	}
	return u
}

func jsonString(v any) string { b, _ := json.Marshal(v); return string(b) }

func firstVersion(spec string) string {
	m := regexp.MustCompile(`\d+(\.\d+){0,2}`).FindString(spec)
	return m
}

func readTSConfig(path string, depth int) map[string]any {
	s := read(path)
	if s == "" || depth > 5 {
		return nil
	}
	var tc struct {
		Extends         any            `json:"extends"`
		CompilerOptions map[string]any `json:"compilerOptions"`
	}
	if json.Unmarshal(stripJSONC([]byte(s)), &tc) != nil {
		return nil
	}
	out := map[string]any{}
	var bases []string
	switch e := tc.Extends.(type) {
	case string:
		bases = []string{e}
	case []any:
		for _, x := range e {
			if s, ok := x.(string); ok {
				bases = append(bases, s)
			}
		}
	}
	for _, b := range bases {
		if strings.HasPrefix(b, ".") { // package-based extends are resolved in a later phase
			if !strings.HasSuffix(b, ".json") {
				b += ".json"
			}
			maps.Copy(out, readTSConfig(filepath.Join(filepath.Dir(path), b), depth+1))
		}
	}
	maps.Copy(out, tc.CompilerOptions)
	return out
}

var (
	jc  = regexp.MustCompile(`(?s)("(?:\\.|[^"\\])*")|//[^\n]*|/\*.*?\*/`)
	tcm = regexp.MustCompile(`,(\s*[}\]])`)
)

func stripJSONC(b []byte) []byte {
	b = jc.ReplaceAllFunc(b, func(m []byte) []byte {
		if m[0] == '"' {
			return m
		}
		return nil
	})
	return tcm.ReplaceAll(b, []byte("$1"))
}

func lockVersions(dir string) map[string]string {
	out := map[string]string{}
	want := slices.Collect(maps.Keys(npmKeys))
	if s := read(filepath.Join(dir, "package-lock.json")); s != "" {
		var l struct {
			Packages map[string]struct{ Version string } `json:"packages"`
		}
		if json.Unmarshal([]byte(s), &l) == nil {
			for _, n := range want {
				if p, ok := l.Packages["node_modules/"+n]; ok && p.Version != "" {
					out[n] = p.Version
				}
			}
		}
	}
	if s := read(filepath.Join(dir, "pnpm-lock.yaml")); s != "" {
		for _, n := range want {
			if _, ok := out[n]; ok {
				continue
			}
			re := regexp.MustCompile(`(?m)^\s+['/]?` + regexp.QuoteMeta(n) + `@(\d+\.\d+\.\d+)`)
			if m := re.FindStringSubmatch(s); m != nil {
				out[n] = m[1]
			}
		}
	}
	if s := read(filepath.Join(dir, "yarn.lock")); s != "" {
		for _, n := range want {
			if _, ok := out[n]; ok {
				continue
			}
			re := regexp.MustCompile(`(?m)^"?` + regexp.QuoteMeta(n) + `@[^\n]*:\n\s+version:?\s+"?(\d+\.\d+\.\d+)`)
			if m := re.FindStringSubmatch(s); m != nil {
				out[n] = m[1]
			}
		}
	}
	return out
}

// Presence lists the file evidence that a dimension exists in a unit even when no
// version is declared (e.g. *.vue files without package.json).
type Presence struct {
	Java, Vue, TS, JS, SpringImport bool
	// Dims marks further dimensions evidenced by files (go, python, php, kotlin, terraform, ...).
	Dims map[string]bool
}

// Finalize applies the "assume latest" policy: a dimension that is present but has no
// detectable version gets the latest known version (Fact.Assumed=true).
func (u *Unit) Finalize(p Presence, latest map[string]string) {
	present := map[string]bool{}
	for k := range u.Facts {
		present[k] = true
	}
	if p.Java {
		present["java"] = true
	}
	for k := range p.Dims {
		present[k] = true
	}
	if p.SpringImport || u.hasDepPrefix("org.springframework.boot:") {
		present["spring-boot"] = true
	}
	if p.Vue || u.Deps["vue"] {
		present["vue"] = true
	}
	if p.TS || u.Deps["typescript"] {
		present["typescript"] = true
	}
	if p.JS || p.TS || p.Vue || present["vue"] || present["nuxt"] || present["typescript"] {
		present["ecmascript"] = true
	}
	if present["nuxt"] {
		present["vue"] = true
	}
	if present["spring-boot"] {
		present["java"], present["spring-framework"], present["spring-security"] = true, true, true
	}
	for k := range present {
		if f := u.Facts[k]; f.Version == "" {
			if l, ok := latest[k]; ok {
				src := "assumed latest (not detectable)"
				if f.Source != "" {
					src = f.Source + "; version not detectable, assumed latest"
				}
				u.Facts[k] = Fact{Version: l, Source: src, Assumed: true}
			}
		}
	}
	if b := u.Facts["spring-boot"]; b.Assumed {
		fw, sec := bootDerived(b.Version)
		if f := u.Facts["spring-framework"]; f.Assumed && fw != "" {
			u.Facts["spring-framework"] = Fact{Version: fw, Source: "derived from assumed spring-boot", Assumed: true}
		}
		if f := u.Facts["spring-security"]; f.Assumed && sec != "" {
			u.Facts["spring-security"] = Fact{Version: sec, Source: "derived from assumed spring-boot", Assumed: true}
		}
	}
}

func (u *Unit) hasDepPrefix(p string) bool {
	for d := range u.Deps {
		if strings.HasPrefix(d, p) {
			return true
		}
	}
	return false
}

// AppliesTo evaluates a rule's applies_to map. A dimension absent from the unit means the
// rule does not apply (e.g. Vue rules in a Java-only repo); flag-style keys (tsconfig.*)
// that are absent compare against "".
func (u *Unit) AppliesTo(a map[string]string) bool {
	for k, rng := range a {
		if k == "any" { // ecosystem-agnostic rules (generic JSON/YAML/Dockerfile...)
			continue
		}
		f, ok := u.Facts[k]
		if !ok {
			if strings.HasPrefix(k, "tsconfig.") || strings.Contains(k, ".") {
				if !Satisfies("", rng) {
					return false
				}
				continue
			}
			return false
		}
		if !Satisfies(f.Version, rng) {
			return false
		}
	}
	return true
}

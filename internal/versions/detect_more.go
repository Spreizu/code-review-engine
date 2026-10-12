package versions

import (
	"encoding/json"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

// npmKeys maps npm package names to version dimensions.
var npmKeys = map[string]string{
	"vue": "vue", "nuxt": "nuxt", "nuxt3": "nuxt", "typescript": "typescript",
	"@angular/core": "angular", "react": "react", "@nuxt/ui": "nuxt-ui", "@nuxt/ui-pro": "nuxt-ui",
	"payload": "payload", "@vueuse/core": "vueuse", "graphql": "graphql",
}

var (
	goModGo        = regexp.MustCompile(`(?m)^go\s+(\d+\.\d+(?:\.\d+)?)\s*$`)
	goModToolchain = regexp.MustCompile(`(?m)^toolchain\s+go(\d+\.\d+(?:\.\d+)?)`)
	goModReq       = regexp.MustCompile(`(?m)^\s*(?:require\s+)?([a-zA-Z0-9.\-]+\.[a-z]{2,}/[^\s]+)\s+v[0-9]`)
	pyRequires     = regexp.MustCompile(`(?m)^\s*requires-python\s*=\s*["']([^"']+)["']`)
	pyPoetry       = regexp.MustCompile(`(?ms)^\[tool\.poetry\.dependencies\].*?^\s*python\s*=\s*["']([^"']+)["']`)
	pySetupCfg     = regexp.MustCompile(`(?m)^\s*python_requires\s*=\s*([^\n]+)`)
	pyPipfile      = regexp.MustCompile(`(?m)^\s*python_(?:full_)?version\s*=\s*["']([^"']+)["']`)
	pyReqLine      = regexp.MustCompile(`(?m)^\s*([A-Za-z0-9][A-Za-z0-9._\-]*)\s*(?:\[[^\]]*\])?\s*(?:[=<>!~]=?|$)`)
	pyProjDeps     = regexp.MustCompile(`(?ms)^dependencies\s*=\s*\[(.*?)\]`)
	pyDepName      = regexp.MustCompile(`["']\s*([A-Za-z0-9][A-Za-z0-9._\-]*)`)
	kotlinPlugin   = regexp.MustCompile(`(?:kotlin\(\s*"[a-z.\-]+"\s*\)|id\s*\(?\s*["']org\.jetbrains\.kotlin\.[a-z.\-]+["']\s*\)?)\s*version\s*["']([0-9][^"']*)["']`)
	kotlinVar      = regexp.MustCompile(`(?m)kotlin(?:_v|V)ersion\s*=\s*["']([0-9][^"']*)["']`)
	gradleDist     = regexp.MustCompile(`gradle-(\d+(?:\.\d+){0,2})(?:-[a-z0-9\-]+)?-(?:bin|all)\.zip`)
	mavenDist      = regexp.MustCompile(`apache-maven/(\d+\.\d+\.\d+)`)
	pomModel       = regexp.MustCompile(`<modelVersion>\s*4\.1\.0\s*</modelVersion>`)
	tfRequired     = regexp.MustCompile(`(?m)^\s*required_version\s*=\s*"([^"]+)"`)
	tfProvider     = regexp.MustCompile(`(?s)source\s*=\s*"(?:registry\.terraform\.io/)?([a-z0-9\-]+/[a-z0-9\-]+)"\s*(?:\n\s*)?version\s*=\s*"([^"]+)"`)
	tfLock         = regexp.MustCompile(`(?s)provider\s+"registry\.terraform\.io/([^"]+)"\s*\{\s*version\s*=\s*"([^"]+)"`)
)

// detectMore adds the ecosystems beyond Java/Spring/Vue/Nuxt/TS.
func detectMore(dir string, u *Unit) {
	detectNode(dir, u)
	// Dockerfile frontend: "# syntax=docker/dockerfile:1.x" parser directive
	for _, f := range []string{"Dockerfile", "Containerfile"} {
		if b, err := os.ReadFile(filepath.Join(dir, f)); err == nil {
			if m := regexp.MustCompile(`(?m)^#\s*syntax\s*=\s*(?:docker\.io/)?docker/dockerfile(?:-upstream)?:(\d+(?:\.\d+)*)`).FindSubmatch(b); m != nil {
				u.set("dockerfile", string(m[1]), f+" syntax directive")
			}
			markPresent(u, "dockerfile", f)
		}
	}
	if s := read(filepath.Join(dir, "go.mod")); s != "" {
		if m := goModGo.FindStringSubmatch(s); m != nil {
			u.set("go", m[1], "go.mod go directive")
		}
		if m := goModToolchain.FindStringSubmatch(s); m != nil {
			u.Facts["go.toolchain"] = Fact{Version: m[1], Source: "go.mod toolchain"}
		}
		for _, m := range goModReq.FindAllStringSubmatch(s, -1) {
			u.Deps[m[1]] = true
		}
		if _, ok := u.Facts["go"]; !ok {
			u.Facts["go"] = Fact{Source: "go.mod"}
		}
	}
	// Python
	if s := read(filepath.Join(dir, "pyproject.toml")); s != "" {
		if m := pyRequires.FindStringSubmatch(s); m != nil {
			u.set("python", firstVersion(m[1]), "pyproject.toml requires-python")
		} else if m := pyPoetry.FindStringSubmatch(s); m != nil {
			u.set("python", firstVersion(m[1]), "pyproject.toml [tool.poetry.dependencies] python")
		}
		if m := pyProjDeps.FindStringSubmatch(s); m != nil {
			for _, d := range pyDepName.FindAllStringSubmatch(m[1], -1) {
				u.Deps["pypi:"+strings.ToLower(d[1])] = true
			}
		}
		markPresent(u, "python", "pyproject.toml")
	}
	if s := strings.TrimSpace(read(filepath.Join(dir, ".python-version"))); s != "" {
		u.set("python", firstVersion(s), ".python-version")
	}
	if s := read(filepath.Join(dir, "runtime.txt")); strings.HasPrefix(strings.TrimSpace(s), "python-") {
		u.set("python", firstVersion(s), "runtime.txt")
	}
	if s := read(filepath.Join(dir, "setup.cfg")); s != "" {
		if m := pySetupCfg.FindStringSubmatch(s); m != nil {
			u.set("python", firstVersion(m[1]), "setup.cfg python_requires")
		}
	}
	if s := read(filepath.Join(dir, "Pipfile")); s != "" {
		if m := pyPipfile.FindStringSubmatch(s); m != nil {
			u.set("python", firstVersion(m[1]), "Pipfile")
		}
		markPresent(u, "python", "Pipfile")
	}
	if s := read(filepath.Join(dir, "requirements.txt")); s != "" {
		for _, m := range pyReqLine.FindAllStringSubmatch(s, -1) {
			if !strings.HasPrefix(m[1], "-") {
				u.Deps["pypi:"+strings.ToLower(m[1])] = true
			}
		}
		markPresent(u, "python", "requirements.txt")
	}
	// PHP / Composer
	if s := read(filepath.Join(dir, "composer.json")); s != "" {
		defer markPresent(u, "composer", "composer.json")
		var c struct {
			Require    map[string]string `json:"require"`
			RequireDev map[string]string `json:"require-dev"`
			Config     struct {
				Platform map[string]string `json:"platform"`
			} `json:"config"`
		}
		_ = json.Unmarshal([]byte(s), &c)
		if v := c.Config.Platform["php"]; v != "" {
			u.set("php", firstVersion(v), "composer.json config.platform.php")
		}
		if v := c.Require["php"]; v != "" {
			u.set("php", firstVersion(v), "composer.json require.php")
		}
		for _, deps := range []map[string]string{c.Require, c.RequireDev} {
			for n, v := range deps {
				u.Deps["composer:"+n] = true
				switch n {
				case "laravel/framework":
					u.set("laravel", firstVersion(v), "composer.json")
				case "symfony/framework-bundle":
					u.set("symfony", firstVersion(v), "composer.json")
				}
			}
		}
		markPresent(u, "php", "composer.json")
		if lock := read(filepath.Join(dir, "composer.lock")); lock != "" {
			u.Facts["composer.lock"] = Fact{Version: "1", Source: "composer.lock"}
			if lb, err := os.ReadFile(filepath.Join(dir, "composer.lock")); err == nil {
				// plugin-api-version tracks the Composer minor that wrote the lock (e.g. "2.6.0")
				if m := regexp.MustCompile(`"plugin-api-version"\s*:\s*"(\d+\.\d+)`).FindSubmatch(lb); m != nil {
					u.set("composer", string(m[1]), "composer.lock plugin-api-version")
				}
			}

		}
	}
	// Gradle / Kotlin
	if s := read(filepath.Join(dir, "gradle", "wrapper", "gradle-wrapper.properties")); s != "" {
		if m := gradleDist.FindStringSubmatch(s); m != nil {
			u.set("gradle", m[1], "gradle-wrapper.properties")
		}
	}
	for _, g := range []string{"build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts"} {
		s := read(filepath.Join(dir, g))
		if s == "" {
			continue
		}
		markPresent(u, "gradle", g)
		if m := kotlinPlugin.FindStringSubmatch(s); m != nil {
			u.set("kotlin", m[1], g+" kotlin plugin")
		} else if m := kotlinVar.FindStringSubmatch(s); m != nil {
			u.set("kotlin", m[1], g+" kotlin version")
		}
	}
	if s := read(filepath.Join(dir, "gradle", "libs.versions.toml")); s != "" {
		if m := regexp.MustCompile(`(?m)^\s*kotlin\s*=\s*"([0-9][^"]*)"`).FindStringSubmatch(s); m != nil {
			u.set("kotlin", m[1], "libs.versions.toml")
		}
	}
	// Maven
	if s := read(filepath.Join(dir, ".mvn", "wrapper", "maven-wrapper.properties")); s != "" {
		if m := mavenDist.FindStringSubmatch(s); m != nil {
			u.set("maven", m[1], "maven-wrapper.properties")
		}
	}
	if pom := read(filepath.Join(dir, "pom.xml")); pom != "" {
		if pomModel.MatchString(pom) {
			u.set("maven", "4.0", "pom.xml modelVersion 4.1.0")
		}
		markPresent(u, "maven", "pom.xml")
	}
	detectYtt(dir, u)
	// Terraform
	tfFiles, _ := filepath.Glob(filepath.Join(dir, "*.tf"))
	for _, f := range tfFiles {
		s := read(f)
		if m := tfRequired.FindStringSubmatch(s); m != nil {
			u.set("terraform", firstVersion(m[1]), filepath.Base(f)+" required_version")
		}
		for _, m := range tfProvider.FindAllStringSubmatch(s, -1) {
			u.Deps["tf:"+m[1]] = true
			u.set("tf-provider."+strings.SplitN(m[1], "/", 2)[1], firstVersion(m[2]), filepath.Base(f)+" required_providers")
		}
	}
	if s := read(filepath.Join(dir, ".terraform.lock.hcl")); s != "" {
		for _, m := range tfLock.FindAllStringSubmatch(s, -1) {
			u.Deps["tf:"+m[1]] = true
			k := "tf-provider." + m[1][strings.LastIndex(m[1], "/")+1:]
			delete(u.Facts, k)
			u.set(k, m[2], ".terraform.lock.hcl")
		}
	}
	if s := strings.TrimSpace(read(filepath.Join(dir, ".terraform-version"))); s != "" {
		u.set("terraform", firstVersion(s), ".terraform-version")
	}
	if len(tfFiles) > 0 {
		markPresent(u, "terraform", "*.tf")
	}
}

// detectNode reads Node.js / package-manager versions: .nvmrc, .node-version, engines, packageManager, lockfileVersion.
func detectNode(dir string, u *Unit) {
	for _, f := range []string{".nvmrc", ".node-version"} {
		if b, err := os.ReadFile(filepath.Join(dir, f)); err == nil {
			u.set("node", firstVersion(strings.TrimPrefix(strings.TrimSpace(string(b)), "v")), f)
		}
	}
	if b, err := os.ReadFile(filepath.Join(dir, "package.json")); err == nil {
		var pj struct {
			Engines        map[string]string `json:"engines"`
			PackageManager string            `json:"packageManager"`
		}
		if json.Unmarshal(b, &pj) == nil {
			if v, ok := pj.Engines["node"]; ok {
				if _, have := u.Facts["node"]; !have {
					u.set("node", firstVersion(v), "package.json engines.node")
				}
			}
			if v, ok := pj.Engines["npm"]; ok {
				u.set("npm", firstVersion(v), "package.json engines.npm")
			}
			if name, v, ok := strings.Cut(pj.PackageManager, "@"); ok {
				u.set(name, firstVersion(v), "package.json packageManager")
			}
		}
	}
	if b, err := os.ReadFile(filepath.Join(dir, "package-lock.json")); err == nil {
		if m := regexp.MustCompile(`"lockfileVersion"\s*:\s*(\d+)`).FindSubmatch(b); m != nil {
			u.Facts["npm.lockfile"] = Fact{Version: string(m[1]), Source: "package-lock.json lockfileVersion"}
			if _, have := u.Facts["npm"]; !have && string(m[1]) == "1" {
				u.set("npm", "6", "package-lock.json lockfileVersion 1 (npm <= 6)")
			}
		}
		markPresent(u, "npm", "package-lock.json")
	}
	if exists(filepath.Join(dir, "pnpm-lock.yaml")) {
		markPresent(u, "pnpm", "pnpm-lock.yaml")
	}
	if exists(filepath.Join(dir, "yarn.lock")) {
		markPresent(u, "yarn", "yarn.lock")
	}
}

func markPresent(u *Unit, k, src string) {
	if _, ok := u.Facts[k]; !ok {
		u.Facts[k] = Fact{Source: src}
	}
}

func exists(p string) bool { _, err := os.Stat(p); return err == nil }

var (
	yttRequire = regexp.MustCompile(`require_at_least\(\s*["']v?(\d+\.\d+(?:\.\d+)?)["']`)
	yttMarker  = regexp.MustCompile(`(?m)^\s*#@\s*(load\(\s*"@ytt:|data/values|overlay/|def\b|for\b|if\b)`)
)

// detectYtt marks Carvel ytt as present (top-level *.yml/*.yaml/*.star with ytt annotations, or a _ytt_lib dir)
// and reads the minimum version from version.require_at_least("x.y.z").
func detectYtt(dir string, u *Unit) {
	var files []string
	for _, g := range []string{"*.star", "*.yml", "*.yaml"} {
		m, _ := filepath.Glob(filepath.Join(dir, g))
		files = append(files, m...)
	}
	found := exists(filepath.Join(dir, "_ytt_lib"))
	for _, f := range files {
		s := read(f)
		if m := yttRequire.FindStringSubmatch(s); m != nil {
			u.set("ytt", m[1], filepath.Base(f)+" version.require_at_least")
			found = true
		}
		if !found && (strings.HasSuffix(f, ".star") || yttMarker.MatchString(s)) {
			found = true
		}
	}
	if found {
		markPresent(u, "ytt", "ytt templates")
	}
}

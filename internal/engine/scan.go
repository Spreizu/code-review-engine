package engine

import (
	"fmt"
	"io/fs"
	"maps"
	"os"
	"path/filepath"
	"slices"
	"sort"
	"strings"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/index"
	"github.com/elmo/code-review-engine/internal/progress"
	"github.com/elmo/code-review-engine/internal/projcfg"
	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/scope"
	"github.com/elmo/code-review-engine/internal/taint"
	"github.com/elmo/code-review-engine/internal/versions"
)

// Options configures a scan.
type Options struct {
	Root      string
	Rules     []*rules.Rule
	Ignore    []string
	Latest    map[string]string
	Only      map[string]bool   // restrict to these repo-relative paths (diff mode); nil = all
	Disabled  map[string]bool   // rule ids turned off in .crev.yaml
	Severity  map[string]string // per-rule severity override from .crev.yaml
	MaxFileKB int
	// Exclusions (all on by default; each can be turned off).
	NoDefaultExcludes bool // do not skip DefaultExcludeDirs / DefaultExcludeFiles (deps, build output, lockfiles, minified/generated)
	NoGitignore       bool // do not honour .gitignore files (nested, with negations) and .git/info/exclude
	IncludeGenerated  bool // review files whose header says they are generated (@generated, "Code generated ... DO NOT EDIT")
	// Scope restricts *reported* findings to changed files/lines (nil = full repo). Files are still
	// parsed whole, and version detection / the repo index always see the full tree.
	Scope *scope.Scope
	// RespectProjectConfig honours the project's linter configuration and inline disable comments
	// (crev-ignore comments are honoured either way).
	RespectProjectConfig bool
	// Progress, when set, receives phase/file updates (the CLI renders them on stderr).
	Progress func(progress.Event)
	// Shadow quarantines extra rule ids (rule id -> reason), e.g. demoted by `crev feedback fp`;
	// rules with status: shadow are quarantined too. Shadow findings are counted in
	// Report.Shadow and never reported.
	Shadow map[string]string
	// IncludeShadow keeps shadow findings in the report with status "shadow" (corpus
	// harness / debugging); they never gate and the review list never shows them.
	IncludeShadow bool
	// Enabled: rules switched on explicitly in .crev.yaml (rules: {ID: {enabled: true}}); for
	// opt-in rules this replaces the project-linter-config requirement.
	Enabled map[string]bool

	project *projcfg.Set
}

var unitMarkers = []string{"pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts", "package.json", "tsconfig.json",
	"nuxt.config.ts", "nuxt.config.js", "nuxt.config.mjs", "go.mod", "pyproject.toml", "setup.cfg", "requirements.txt", "Pipfile", "composer.json",
	"versions.tf", "main.tf", ".terraform.lock.hcl"}

var codeExt = map[string]string{
	".java": "java", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
	".ts": "typescript", ".mts": "typescript", ".cts": "typescript", ".tsx": "tsx", ".vue": "vue",
	".go": "go", ".py": "python", ".pyi": "python", ".php": "php", ".phtml": "php", ".kt": "kotlin", ".kts": "kotlin",
	".gradle": "groovy", ".groovy": "groovy", ".json": "json", ".jsonc": "json", ".yaml": "yaml", ".yml": "yaml",
	".xml": "xml", ".tf": "hcl", ".tfvars": "hcl", ".hcl": "hcl", ".dockerfile": "dockerfile", ".proto": "proto",
	".graphql": "graphql", ".gql": "graphql", ".graphqls": "graphql", ".html": "html", ".htm": "html",
}

// fileKind derives the grammar kind from the extension or well-known file names.
func fileKind(rel string) string {
	base := strings.ToLower(filepath.Base(rel))
	switch {
	case base == "dockerfile" || base == "containerfile" || strings.HasPrefix(base, "dockerfile.") || strings.HasPrefix(base, "containerfile."):
		return "dockerfile"
	case strings.HasSuffix(base, ".tfvars.json"):
		return "json"
	}
	return codeExt[strings.ToLower(filepath.Ext(rel))]
}

// presenceDims maps file kinds to version dimensions evidenced by the file's existence.
var presenceDims = map[string]string{"go": "go", "python": "python", "php": "php", "kotlin": "kotlin", "hcl": "terraform"}

var defaultIgnore = []string{"**/.git/**"}

type file struct {
	rel  string
	unit *versions.Unit
}

// Scan runs all rules over Root and returns the report.
func Scan(o Options) (*findings.Report, error) {
	root, err := filepath.Abs(o.Root)
	if err != nil {
		return nil, err
	}
	if o.MaxFileKB == 0 {
		o.MaxFileKB = 1024
	}
	ignore := append(append([]string{}, defaultIgnore...), o.Ignore...)
	var all, cfgFiles []string
	unitDirs := map[string]bool{".": true}
	prog := func(e progress.Event) {
		if o.Progress != nil {
			o.Progress(e)
		}
	}
	prog(progress.Event{Phase: "discover"})
	var gi *gitIgnore
	if !o.NoGitignore {
		gi = newGitIgnore(root)
	}
	err = filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		rel, _ := filepath.Rel(root, p)
		rel = filepath.ToSlash(rel)
		if d.IsDir() {
			if rel != "." {
				if ignored(ignore, rel+"/") || (!o.NoDefaultExcludes && defaultExcludedDir(p, d.Name())) || (gi != nil && gi.Ignored(rel, true)) {
					return filepath.SkipDir
				}
			}
			if gi != nil {
				gi.load(rel)
			}
			return nil
		}
		// Unit markers are recorded before exclusion: lockfiles and manifests feed version
		// detection even when they are excluded from rule review.
		base := d.Name()
		if projcfg.IsConfigFile(base) {
			cfgFiles = append(cfgFiles, rel)
		}
		for _, m := range unitMarkers {
			if base == m {
				unitDirs[filepath.ToSlash(filepath.Dir(rel))] = true
			}
		}
		if ignored(ignore, rel) || (!o.NoDefaultExcludes && defaultExcludedFile(base)) || (gi != nil && gi.Ignored(rel, false)) {
			return nil
		}
		all = append(all, rel)
		if len(all)%200 == 0 {
			prog(progress.Event{Phase: "discover", Done: len(all), Current: rel})
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	slices.Sort(all)
	// Units, inheriting facts and dependencies from ancestor units (multi-module builds).
	dirs := slices.Collect(maps.Keys(unitDirs))
	sort.Slice(dirs, func(i, j int) bool { return len(dirs[i]) < len(dirs[j]) })
	units := map[string]*versions.Unit{}
	for i, d := range dirs {
		prog(progress.Event{Phase: "versions", Done: i, Total: len(dirs), Current: d})
		u := versions.DetectUnit(filepath.Join(root, d))
		if d != "." {
			if parent := nearest(units, filepath.ToSlash(filepath.Dir(d))); parent != nil {
				for k, f := range parent.Facts {
					// A unit that only evidences a dimension (tsconfig without a typescript
					// dependency, a pnpm catalog: reference) inherits the ancestor's version
					// instead of being assumed latest (corpus FP: TS-MIG-VUE-TS7-001 in vitesse/cypress).
					if own, ok := u.Facts[k]; !ok || own.Version == "" {
						u.Facts[k] = f
					}
				}
				for k := range parent.Deps {
					u.Deps[k] = true
				}
			}
		}
		u.Dir = filepath.Join(root, d)
		units[d] = u
	}
	presence := map[*versions.Unit]*versions.Presence{}
	var files []file
	for _, rel := range all {
		u := nearest(units, filepath.ToSlash(filepath.Dir(rel)))
		files = append(files, file{rel, u})
		p := presence[u]
		if p == nil {
			p = &versions.Presence{}
			presence[u] = p
		}
		k := fileKind(rel)
		if d, ok := presenceDims[k]; ok && (k != "hcl" || strings.HasSuffix(rel, ".tf")) {
			if p.Dims == nil {
				p.Dims = map[string]bool{}
			}
			p.Dims[d] = true
		}
		switch k {
		case "java":
			p.Java = true
			if b, err := os.ReadFile(filepath.Join(root, rel)); err == nil && strings.Contains(string(b), "org.springframework.boot") {
				p.SpringImport = true
			}
		case "vue":
			p.Vue = true
		case "typescript", "tsx":
			p.TS = true
		case "javascript":
			p.JS = true
		}
	}
	for _, d := range dirs {
		p := presence[units[d]]
		if p == nil {
			p = &versions.Presence{}
		}
		units[d].Finalize(*p, o.Latest)
	}

	rep := &findings.Report{SchemaVersion: 1, Tool: "crev", Root: root, Units: map[string]map[string]string{}, Stats: map[string]int{}}
	for d, u := range units {
		m := map[string]string{}
		for k, f := range u.Facts {
			v := f.Version
			if f.Assumed {
				v += " (assumed latest)"
			}
			m[k] = v
		}
		rep.Units[d] = m
	}
	prog(progress.Event{Phase: "index", Current: "project linter configuration"})
	pset := projcfg.Discover(root, cfgFiles)
	pset.ConfigOff = !o.RespectProjectConfig
	rep.ProjectConfig = &findings.ProjectConfig{Respect: o.RespectProjectConfig, Sources: pset.Sources, Directives: len(pset.Directives), Errors: pset.Errors}
	var srcRel string
	var srcBytes []byte
	source := func(rel string) []byte {
		if rel != srcRel {
			srcRel = rel
			srcBytes, _ = os.ReadFile(filepath.Join(root, rel))
		}
		return srcBytes
	}
	ordinal := map[string]int{}
	add := func(r *rules.Rule, u *versions.Unit, rel string, loc findings.Location, snippet, symbol string) *findings.Finding {
		if o.Only != nil && !o.Only[rel] {
			return nil
		}
		if !o.Scope.InScope(rel, loc.StartLine, loc.EndLine) {
			rep.Stats["out_of_scope"]++
			return nil
		}
		sev, msg := r.Severity, r.Message
		for _, ov := range r.Overrides {
			if u.AppliesTo(ov.When) {
				if ov.Severity != "" {
					sev = ov.Severity
				}
				if ov.Message != "" {
					msg = ov.Message
				}
			}
		}
		if s, ok := o.Severity[r.ID]; ok {
			sev = s
		}
		if CappedCategories[r.Category] && rules.SeverityRank(sev) > rules.SeverityRank(MaxAdvisorySeverity) {
			sev = MaxAdvisorySeverity
		}
		if r.OptIn && !o.Enabled[r.ID] && !pset.Enables(r.Equivalents, rel) {
			rep.Stats["opt_in_not_enabled"]++
			return nil
		}
		key := r.ID + rel + snippet + symbol
		ordinal[key]++
		f := &findings.Finding{
			RuleID: r.ID, RuleVersion: r.RuleVersion, PackVersion: r.PackVersion, Severity: sev,
			DetectionMode: r.Detection.Mode, Kind: r.Kind, Category: r.Category, Title: r.Title,
			Location: loc, Snippet: truncate(snippet, 400), Message: msg, Fix: r.Fix,
			Source:          findings.Source{URL: r.Source.URL, Doc: r.Source.Doc, DocVersion: r.Source.DocVersion},
			AppliedVersions: map[string]string{}, Xref: r.Xref,
		}
		f.Location.Path = rel
		f.Location.EnclosingSymbol = symbol
		f.CWE, f.OWASP = r.CWE, r.OWASP
		f.ID = findings.Fingerprint(r.ID, rel, snippet, symbol, ordinal[key])
		for k := range r.AppliesTo {
			if fa, ok := u.Facts[k]; ok {
				f.AppliedVersions[k] = fa.Version
				if fa.Assumed {
					f.AssumedVersions = append(f.AssumedVersions, k)
				}
			}
		}
		if r.Detection.Mode == "ai-confirm" {
			f.Status, f.Confidence = "pending_ai", "low"
		} else {
			f.Status, f.Confidence = "confirmed", "high"
		}
		if sb := pset.Check(rel, source(rel), r.ID, r.Equivalents, loc.StartLine, loc.EndLine); sb != nil {
			f.Status, f.SuppressedBy = "suppressed", sb
			rep.Stats["suppressed_"+strings.ReplaceAll(sb.Kind, "-", "_")]++
		}
		if r.Shadow() || o.Shadow[r.ID] != "" {
			// Quarantine: logged (per-rule counts), never in the review list.
			if rep.Shadow == nil {
				rep.Shadow = map[string]int{}
			}
			rep.Shadow[r.ID]++
			rep.Stats["shadow"]++
			if !o.IncludeShadow {
				return nil
			}
			f.Status, f.HiddenReason = "shadow", "shadow"
			if why := o.Shadow[r.ID]; why != "" {
				f.HiddenDetail = "rule quarantined: " + why
			} else {
				f.HiddenDetail = "rule quarantined (status: shadow in the rule pack): runs and is logged, never gates or lists by default"
			}
		}
		rep.Findings = append(rep.Findings, f)
		return f
	}

	active := make([]*rules.Rule, 0, len(o.Rules))
	for _, r := range o.Rules {
		if o.Disabled[r.ID] || r.Status == "retired" {
			continue
		}
		if !configured(pset, r.Detection.RequiresConfig) {
			rep.Stats["rules_unconfigured"]++
			continue
		}
		active = append(active, r)
	}
	// Manifest rules: once per unit.
	for _, d := range dirs {
		u := units[d]
		for _, r := range active {
			if r.Detection.Engine != "manifest" || !u.AppliesTo(r.AppliesTo) {
				continue
			}
			hits, err := EvalManifest(r, u)
			if err != nil {
				rep.Errors = append(rep.Errors, r.ID+": "+err.Error())
				continue
			}
			for _, h := range hits {
				rel := filepath.ToSlash(filepath.Join(d, h.File))
				line := h.Line
				if line == 0 {
					line = 1
				}
				add(r, u, strings.TrimPrefix(rel, "./"), findings.Location{StartLine: line, StartColumn: 1, EndLine: line, EndColumn: 1}, h.Text, "")
			}
		}
	}
	scanned := 0
	for i, f := range files {
		if !o.Scope.FileInScope(f.rel) {
			continue // per-file rules can only report inside the scope
		}
		prog(progress.Event{Phase: "rules", Done: i, Total: len(files), Current: f.rel, Findings: len(rep.Findings)})
		scanned++
		o.project = pset
		if err := scanFile(root, f, active, o, add); err != nil {
			rep.Errors = append(rep.Errors, f.rel+": "+err.Error())
		}
	}
	prog(progress.Event{Phase: "rules", Done: len(files), Total: len(files), Findings: len(rep.Findings)})
	o.project = pset
	runIndexRules(root, files, active, o, add, rep, prog)
	capAndReroute(rep)
	sort.SliceStable(rep.Findings, func(i, j int) bool {
		a, b := rep.Findings[i], rep.Findings[j]
		if a.Location.Path != b.Location.Path {
			return a.Location.Path < b.Location.Path
		}
		if a.Location.StartLine != b.Location.StartLine {
			return a.Location.StartLine < b.Location.StartLine
		}
		return a.RuleID < b.RuleID
	})
	rep.Stats["files"] = len(files)
	rep.Stats["files_reviewed"] = scanned
	if o.Scope.IsDiff() {
		rep.Scope = o.Scope
	}
	rep.Stats["rules"] = len(active)
	rep.Stats["findings"] = len(rep.Findings)
	return rep, nil
}

// configured: a rule with detection.requires_config runs only when the project configures one
// of the listed tools (opinionated style rules stay silent unless the project adopted them).
func configured(p *projcfg.Set, tools []string) bool {
	if len(tools) == 0 {
		return true
	}
	for _, t := range tools {
		if p.Configures(t) {
			return true
		}
	}
	return false
}

func nearest(units map[string]*versions.Unit, dir string) *versions.Unit {
	for {
		if u, ok := units[dir]; ok {
			return u
		}
		if dir == "." || dir == "/" || dir == "" {
			return units["."]
		}
		dir = filepath.ToSlash(filepath.Dir(dir))
	}
}

func ignored(globs []string, rel string) bool {
	for _, g := range globs {
		if GlobMatch(g, rel) || GlobMatch(g, strings.TrimSuffix(rel, "/")) {
			return true
		}
		if strings.HasSuffix(g, "/**") && GlobMatch(strings.TrimSuffix(g, "/**"), strings.TrimSuffix(rel, "/")) {
			return true
		}
	}
	return false
}

func truncate(s string, n int) string {
	if len(s) > n {
		return s[:n] + "…"
	}
	return s
}

// RuleAppliesToPath reports whether the rule's file globs (detection.files, incl. "!" exclusions)
// let it run on a repo-relative path; used by rulecheck for path-bound regression examples.
func RuleAppliesToPath(r *rules.Rule, rel string) bool {
	if hasPositiveGlob(r) {
		return fileMatches(r, rel, rel)
	}
	return !fileExcluded(r, rel, rel)
}

// fileMatches reports whether rule globs (relative to scan root or unit dir) match.
// Globs prefixed with "!" exclude; a rule with only exclusions falls back to its language.
func fileMatches(r *rules.Rule, rel, unitRel string) bool {
	for _, g := range r.Detection.Files {
		if strings.HasPrefix(g, "!") {
			continue
		}
		if GlobMatch(g, rel) || (unitRel != "" && GlobMatch(g, unitRel)) {
			return true
		}
	}
	return false
}

func hasPositiveGlob(r *rules.Rule) bool {
	for _, g := range r.Detection.Files {
		if !strings.HasPrefix(g, "!") {
			return true
		}
	}
	return false
}

func fileExcluded(r *rules.Rule, rel, unitRel string) bool {
	if r.Detection.ExcludeTests && index.IsTest(rel) {
		return true
	}
	for _, g := range r.Detection.Files {
		if g, ok := strings.CutPrefix(g, "!"); ok && (GlobMatch(g, rel) || (unitRel != "" && GlobMatch(g, unitRel))) {
			return true
		}
	}
	return false
}

// languageFiles maps a rule language to the file kinds it runs on by default.
func languageApplies(lang, kind, vueLang string) bool {
	switch lang {
	case "java":
		return kind == "java"
	case "javascript":
		return kind == "javascript" || kind == "typescript" || kind == "tsx" || kind == "vue"
	case "typescript":
		return kind == "typescript" || kind == "tsx" || (kind == "vue" && (vueLang == "ts" || vueLang == "tsx"))
	case "vue":
		return kind == "vue"
	case "jsx":
		return kind == "javascript" || kind == "tsx"
	}
	return lang == kind
}

func scanFile(root string, f file, active []*rules.Rule, o Options, add addFunc) error {
	abs := filepath.Join(root, f.rel)
	st, err := os.Stat(abs)
	if err != nil || st.Size() > int64(o.MaxFileKB)*1024 {
		return nil
	}
	src, err := os.ReadFile(abs)
	if err != nil {
		return err
	}
	if !o.IncludeGenerated && IsGeneratedSource(src) {
		return nil
	}
	unitRel, _ := filepath.Rel(f.unit.Dir, abs)
	unitRel = filepath.ToSlash(unitRel)
	kind := fileKind(f.rel)
	trees := map[string]*Tree{}
	defer func() {
		for _, t := range trees {
			t.Close()
		}
	}()
	var vueScript []byte
	var vueGrammar, vueLang string
	if kind == "vue" {
		vueScript, vueGrammar, vueLang, _ = VueScript(src)
	}
	tree := func(grammar string, s []byte) (*Tree, error) {
		if t, ok := trees[grammar]; ok {
			return t, nil
		}
		t, err := Parse(grammar, s)
		if err != nil {
			return nil, err
		}
		t.Dir, t.ScanRoot = filepath.Dir(abs), root
		trees[grammar] = t
		return t, nil
	}
	var errs []string
	taintHits := map[string][]taint.Hit{}
	for _, r := range active {
		if !f.unit.AppliesTo(r.AppliesTo) {
			continue
		}
		r = withParams(r, o.project, f.rel)
		switch r.Detection.Engine {
		case "config":
			if !fileMatches(r, f.rel, unitRel) {
				continue
			}
			if dep := r.Detection.RequiresDependency; dep != "" && len(f.unit.Deps) > 0 && !f.unit.Deps[dep] {
				continue
			}
			if g := r.Detection.RequiresDependencyGlob; g != "" && len(f.unit.Deps) > 0 {
				found := false
				for d := range f.unit.Deps {
					if GlobMatch(g, d) {
						found = true
					}
				}
				if !found {
					continue
				}
			}
			c, err := ParseConfig(f.rel, src)
			if err != nil {
				errs = append(errs, r.ID+": "+err.Error())
				continue
			}
			hits, err := EvalConfig(r, c)
			if err != nil {
				errs = append(errs, r.ID+": "+err.Error())
				continue
			}
			for _, h := range hits {
				line := h.Line
				if line == 0 {
					line = 1
				}
				add(r, f.unit, f.rel, findings.Location{StartLine: line, StartColumn: 1, EndLine: line, EndColumn: 1}, strings.TrimSpace(h.Key+" "+h.Value), "")
			}
		case "taint":
			if kind == "" || hasPositiveGlob(r) && !fileMatches(r, f.rel, unitRel) || !hasPositiveGlob(r) && !languageApplies(r.Language, kind, vueLang) || fileExcluded(r, f.rel, unitRel) {
				continue
			}
			grammar, s, block := kind, src, ""
			if kind == "vue" {
				if vueScript == nil {
					continue
				}
				grammar, s, block = vueGrammar, vueScript, "script"
			}
			hits, ok := taintHits[grammar]
			if !ok {
				t, err := tree(grammar, s)
				if err != nil {
					errs = append(errs, err.Error())
					continue
				}
				hits, err = TaintRun(t)
				if err != nil {
					errs = append(errs, r.ID+": "+err.Error())
				}
				taintHits[grammar] = hits
			}
			cls, _ := r.Detection.Config["class"].(string)
			for _, h := range hits {
				if h.Class != cls {
					continue
				}
				n := h.Node
				fd := add(r, f.unit, f.rel, findings.Location{StartLine: int(n.Row) + 1, StartColumn: int(n.Col) + 1, EndLine: int(n.ERow) + 1, EndColumn: int(n.ECol) + 1,
					StartByte: int(n.S), EndByte: int(n.E), SFCBlock: block}, truncate(string(s[n.S:n.E]), 300), taintSymbol(t0(trees, grammar), n))
				if fd != nil {
					fd.Evidence = h.Evidence
				}
			}
		case "tree-sitter":
			if kind == "" {
				continue
			}
			if hasPositiveGlob(r) {
				if !fileMatches(r, f.rel, unitRel) {
					continue
				}
			} else if !languageApplies(r.Language, kind, vueLang) {
				continue
			}
			if fileExcluded(r, f.rel, unitRel) {
				continue
			}
			var grammar string
			var s []byte
			block := ""
			switch {
			case kind == "vue" && r.Detection.Target == "template":
				grammar, s, block = "vue", src, "template"
			case kind == "vue":
				if vueScript == nil {
					continue
				}
				grammar, s, block = vueGrammar, vueScript, "script"
			case r.Language == "vue" && r.Detection.Target == "template":
				continue
			default:
				grammar, s = kind, src
			}
			if r.Detection.Grammar != "" && r.Detection.Grammar != grammar {
				// Query written for another grammar: only run if it compiles here too.
				if _, _, err := CompileQuery(r, grammar); err != nil {
					continue
				}
			}
			t, err := tree(grammar, s)
			if err != nil {
				errs = append(errs, err.Error())
				continue
			}
			if block == "script" {
				t.SFC = src
			}
			hits, err := Run(r, t)
			if err != nil {
				errs = append(errs, r.ID+": "+err.Error())
				continue
			}
			for _, h := range hits {
				fd := add(r, f.unit, f.rel, findings.Location{
					StartLine: int(h.StartRow) + 1, StartColumn: int(h.StartCol) + 1,
					EndLine: int(h.EndRow) + 1, EndColumn: int(h.EndCol) + 1,
					StartByte: int(h.StartByte), EndByte: int(h.EndByte), SFCBlock: block,
				}, h.Text, h.Symbol)
				if fd != nil && h.Value != "" {
					fd.Message = strings.ReplaceAll(fd.Message, "${value}", h.Value)
				}
			}
		}
	}
	if len(errs) > 0 {
		return fmt.Errorf("%s", strings.Join(errs, "; "))
	}
	return nil
}

func relTo(dir, rel string) string {
	r, err := filepath.Rel(dir, rel)
	if err != nil {
		return ""
	}
	return filepath.ToSlash(r)
}

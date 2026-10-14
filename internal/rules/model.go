// Package rules loads and models rule packs (rules are data, see schemas/rule-pack.schema.json).
package rules

import (
	"fmt"
	"io/fs"
	"os"
	"path"
	"path/filepath"
	"slices"
	"strings"

	"gopkg.in/yaml.v3"
)

// Pack is one YAML rule-pack file.
type Pack struct {
	Pack        string `yaml:"pack"`
	PackVersion string `yaml:"pack_version"`
	Rules       []Rule `yaml:"rules"`
}

// Override changes severity/message when its version condition holds.
type Override struct {
	When     map[string]string `yaml:"when"`
	Severity string            `yaml:"severity"`
	Message  string            `yaml:"message"`
}

// Detection describes how a rule finds candidates.
type Detection struct {
	Mode                   string         `yaml:"mode"`
	Engine                 string         `yaml:"engine"`
	Target                 string         `yaml:"target"`
	Grammar                string         `yaml:"grammar"`
	Files                  []string       `yaml:"files"`
	Query                  string         `yaml:"query"`
	Check                  string         `yaml:"check"` // engine index: repo-index check name (see internal/index.Checks)
	Capture                string         `yaml:"capture"`
	Filters                []string       `yaml:"filters"`
	Config                 map[string]any `yaml:"config"`
	Manifest               map[string]any `yaml:"manifest"`
	RequiresDependency     string         `yaml:"requires_dependency"`
	RequiresDependencyGlob string         `yaml:"requires_dependency_glob"`
	// RequiresConfig: the rule only runs when the project configures one of these tools
	// (e.g. yamllint): opinionated style rules stay silent unless the project adopted the style.
	RequiresConfig []string `yaml:"requires_config"`
	// ExcludeTests: skip test files (internal/index.IsTest: tests/, __tests__/, *_test.go,
	// *.spec.ts, *Test.kt, test_*.py, ...). Set in the pack or in data/governance.yaml.
	ExcludeTests bool `yaml:"exclude_tests,omitempty"`
}

// Regression is a must-not-match example recorded from a confirmed false positive
// (self-scan, corpus run or `crev feedback fp`). rulecheck runs every one of them like
// examples.good, so a fixed false positive cannot come back. Path, when set, is the file
// name the code lives in (path-based exclusions such as test files are checked too).
type Regression struct {
	Code string `yaml:"code"`
	Path string `yaml:"path,omitempty"`
	Note string `yaml:"note,omitempty"`
}

// Precision tiers (rule-pack schema "precision"): how often a candidate is a real problem.
// high: the pattern is the problem (deterministic allowed); medium: occasional context
// dependence (deterministic allowed, watched by the corpus harness); low: known false-positive
// risk, must be detection.mode ai-confirm.
var PrecisionTiers = []string{"high", "medium", "low"}

// Source is the official documentation citation.
type Source struct {
	URL        string `yaml:"url" json:"url"`
	Doc        string `yaml:"doc" json:"doc"`
	DocVersion string `yaml:"doc_version" json:"doc_version"`
	Retrieved  string `yaml:"retrieved" json:"retrieved,omitempty"`
	Quote      string `yaml:"quote" json:"quote,omitempty"`
}

// Param is an overridable rule threshold.
type Param struct {
	Default any `yaml:"default"`
	// From lists "tool:id.option" sources in priority order (first found wins), e.g.
	// "yamllint:line-length.max" or "editorconfig:max_line_length.max".
	From []string `yaml:"from"`
}

// Rule is a single rule.
type Rule struct {
	ID        string            `yaml:"id"`
	Title     string            `yaml:"title"`
	Language  string            `yaml:"language"`
	Framework string            `yaml:"framework"`
	Kind      string            `yaml:"kind"`
	Category  string            `yaml:"category"`
	Severity  string            `yaml:"severity"`
	AppliesTo map[string]string `yaml:"applies_to"`
	Overrides []Override        `yaml:"overrides"`
	Detection Detection         `yaml:"detection"`
	Message   string            `yaml:"message"`
	Rationale string            `yaml:"rationale"`
	Fix       string            `yaml:"fix"`
	// OptIn: an opinionated rule (not in its linter's recommended set) that only reports where
	// the project's linter config enables an equivalent rule (rules/data/optin.yaml).
	OptIn       bool   `yaml:"opt_in,omitempty"`
	OptInReason string `yaml:"-"`
	AIQuestion  string `yaml:"ai_question"`
	Source      Source `yaml:"source"`
	Examples    struct {
		Bad  string `yaml:"bad"`
		Good string `yaml:"good"`
		// Regressions are further must-not-match cases (former false positives).
		Regressions []Regression `yaml:"regressions"`
	} `yaml:"examples"`
	// Status: "" / active, shadow (quarantine: runs and is logged, never reported), retired.
	Status string `yaml:"status"`
	// StatusReason explains a shadow/retired status (corpus volume, feedback threshold, ...).
	StatusReason string `yaml:"status_reason"`
	// Precision tier: high | medium | low (see PrecisionTiers); empty = derived (EffectivePrecision).
	Precision string `yaml:"precision"`
	// Trust is the evidence level of the rule (rules/data/trust.yaml, written by tools/trust):
	// proven, measured, unproven or quarantined. Unproven deterministic rules run as ai-confirm.
	Trust *Trust `yaml:"trust,omitempty" json:"trust,omitempty"`
	// MatchKind "exact-api": version-gated deprecation/removal/migration rule matching an exact
	// identifier/import/config key/dependency (rules.ExactAPI; rules/data/matchkind.yaml written by
	// `go run ./tools/trust classify`). Reports directly even when unproven.
	MatchKind string `yaml:"match_kind,omitempty" json:"match_kind,omitempty"`
	// Security taxonomy (security rules): CWE ids ("CWE-89"), OWASP Top 10 categories
	// ("A03:2021", "A05:2025") and OWASP ASVS 5.0 requirement ids ("V1.2.5").
	CWE   []string `yaml:"cwe"`
	OWASP []string `yaml:"owasp"`
	ASVS  []string `yaml:"asvs"`
	// WCAG 2.x success criteria the rule checks ("1.1.1", "2.4.7"); level and version come from
	// the WCAG table (rules.WCAG).
	WCAG        []string `yaml:"wcag"`
	RuleVersion int      `yaml:"rule_version"`
	Tags        []string `yaml:"tags"`
	Xref        []string `yaml:"xref"` // extra doc URLs and/or equivalent linter rules as "tool:id"
	// Params are rule thresholds that project linter configuration may override, referenced in
	// detection filters and the message as ${name}, e.g. a line-length limit read from
	// yamllint/editorconfig.
	Params map[string]Param `yaml:"params"`

	// Equivalents are external linter rules ("tool:id") covering the same ground: "tool:id"
	// entries of Xref plus rules/data/xref.yaml. Used to honour project linter configuration.
	Equivalents []string `yaml:"-"`

	Pack        string `yaml:"-"`
	PackVersion string `yaml:"-"`
	File        string `yaml:"-"`
	// Origin is "custom" for rules added or changed by user rule files (.crev/rules/), "" for built-ins.
	Origin string `yaml:"-"`
	// BaseFile is the built-in pack file a custom patch/replace was applied to.
	BaseFile string `yaml:"-"`
}

// EffectivePrecision is the declared precision tier, or the default for the detection mode:
// deterministic rules are high, ai-confirm rules are low (the AI step is the precision gate).
func (r *Rule) EffectivePrecision() string {
	if r.Precision != "" {
		return r.Precision
	}
	if r.Detection.Mode == "ai-confirm" {
		return "low"
	}
	return "high"
}

// Shadow reports whether the rule is quarantined (runs, findings logged, never reported).
func (r *Rule) Shadow() bool { return r.Status == "shadow" }

// Grammar returns the tree-sitter grammar the rule's query targets.
func (r *Rule) Grammar() string {
	if r.Detection.Grammar != "" {
		return r.Detection.Grammar
	}
	if r.Language == "vue" && r.Detection.Target != "template" {
		return "typescript"
	}
	if r.Language == "jsx" {
		return "javascript"
	}
	return r.Language
}

// CaptureName returns the capture reported as the finding location.
func (r *Rule) CaptureName() string {
	if r.Detection.Capture != "" {
		return r.Detection.Capture
	}
	return "match"
}

// LoadFiles loads packs from files (glob patterns allowed).
func LoadFiles(patterns ...string) ([]*Rule, error) {
	var files []string
	for _, p := range patterns {
		m, err := filepath.Glob(p)
		if err != nil {
			return nil, err
		}
		if len(m) == 0 {
			if st, err := os.Stat(p); err == nil && st.IsDir() {
				m, _ = filepath.Glob(filepath.Join(p, "*.yaml"))
			}
		}
		files = append(files, m...)
	}
	slices.Sort(files)
	return load(files, os.ReadFile)
}

// LoadFS loads every packs/*/*.yaml from an fs.FS (the embedded catalog).
func LoadFS(fsys fs.FS, glob string) ([]*Rule, error) {
	files, err := fs.Glob(fsys, glob)
	if err != nil {
		return nil, err
	}
	slices.Sort(files)
	return load(files, func(n string) ([]byte, error) { return fs.ReadFile(fsys, n) })
}

func load(files []string, read func(string) ([]byte, error)) ([]*Rule, error) {
	var out []*Rule
	seen := map[string]string{}
	for _, f := range files {
		b, err := read(f)
		if err != nil {
			return nil, err
		}
		var p Pack
		if err := yaml.Unmarshal(b, &p); err != nil {
			return nil, fmt.Errorf("%s: %w", f, err)
		}
		// catalog layout rules/packs/<pack>/<topic>.yaml: the directory names the pack
		if dir := path.Dir(filepath.ToSlash(f)); path.Base(path.Dir(dir)) == "packs" && path.Base(dir) != p.Pack {
			return nil, fmt.Errorf("%s: pack %q does not match its directory %q", f, p.Pack, path.Base(dir))
		}
		for i := range p.Rules {
			r := p.Rules[i]
			if prev, ok := seen[r.ID]; ok {
				return nil, fmt.Errorf("duplicate rule id %s in %s and %s", r.ID, prev, f)
			}
			seen[r.ID] = f
			r.Pack, r.PackVersion, r.File = p.Pack, p.PackVersion, f
			if r.RuleVersion == 0 {
				r.RuleVersion = 1
			}
			out = append(out, &r)
		}
	}
	return out, nil
}

// SeverityRank orders severities.
func SeverityRank(s string) int {
	switch strings.ToLower(s) {
	case "info":
		return 1
	case "minor":
		return 2
	case "major":
		return 3
	case "critical":
		return 4
	}
	return 0
}

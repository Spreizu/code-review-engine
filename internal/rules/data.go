package rules

import (
	"errors"
	"io/fs"

	"gopkg.in/yaml.v3"
)

// Governance is one entry of rules/data/governance.yaml: precision tier and quarantine state
// decided from corpus runs and triage (tools/corpus), kept out of the generated packs so the
// harness can update it without regenerating rules. Pack fields win over governance only when
// the governance entry leaves them empty.
type Governance struct {
	Precision    string `yaml:"precision"`
	Status       string `yaml:"status"`
	StatusReason string `yaml:"status_reason"`
	// Mode "ai-confirm" demotes a deterministic rule whose measured precision is too low: its
	// hits then reach the review list only after a high-confidence AI confirmation.
	Mode       string `yaml:"mode,omitempty"`
	AIQuestion string `yaml:"ai_question,omitempty"`
	// Corpus records the evidence (e.g. "corpus 2026-10-10: 41 hits / 6 repos, 9/10 sampled FP").
	Corpus string `yaml:"corpus,omitempty"`
	// ExcludeTests: the rule does not run on test files (index.IsTest), where the pattern is the
	// accepted idiom (fake credentials in fixtures, `!!`/any in assertions, no request timeouts).
	ExcludeTests bool `yaml:"exclude_tests,omitempty"`
}

// ApplyData applies the shipped data files that annotate rules: data/xref.yaml (linter
// equivalents), data/taxonomy.yaml (CWE / OWASP / ASVS of security rules) and
// data/governance.yaml (precision tier, shadow quarantine) and data/optin.yaml (opinionated
// rules that need the project to enable them). Missing taxonomy/governance files
// are not an error (user rule directories).
func ApplyData(all []*Rule, fsys fs.FS) error {
	if err := ApplyBaseData(all, fsys); err != nil {
		return err
	}
	return ApplyTrust(all, fsys)
}

// ApplyBaseData is ApplyData without the trust policy (tools/trust computes trust from it).
func ApplyBaseData(all []*Rule, fsys fs.FS) error {
	if err := ApplyXref(all, fsys, "data/xref.yaml"); err != nil && !errors.Is(err, fs.ErrNotExist) {
		return err
	}
	var tax struct {
		Rules map[string]struct {
			CWE   []string `yaml:"cwe"`
			OWASP []string `yaml:"owasp"`
			ASVS  []string `yaml:"asvs"`
		} `yaml:"rules"`
	}
	if err := readYAML(fsys, "data/taxonomy.yaml", &tax); err != nil {
		return err
	}
	var gov struct {
		Rules map[string]Governance `yaml:"rules"`
	}
	if err := readYAML(fsys, "data/governance.yaml", &gov); err != nil {
		return err
	}
	var optin struct {
		Rules map[string]string `yaml:"rules"`
	}
	if err := readYAML(fsys, "data/optin.yaml", &optin); err != nil {
		return err
	}
	var mk struct {
		Rules map[string]string `yaml:"rules"` // rule id -> classifier reason
	}
	if err := readYAML(fsys, "data/matchkind.yaml", &mk); err != nil {
		return err
	}
	for _, r := range all {
		if _, ok := mk.Rules[r.ID]; ok && r.MatchKind == "" {
			r.MatchKind = MatchKindExactAPI
		}
		if why, ok := optin.Rules[r.ID]; ok {
			r.OptIn, r.OptInReason = true, why
		}
		if t, ok := tax.Rules[r.ID]; ok {
			if len(r.CWE) == 0 {
				r.CWE = t.CWE
			}
			r.OWASP = union(r.OWASP, t.OWASP) // own tags first, then the taxonomy's
			r.ASVS = union(r.ASVS, t.ASVS)
		}
		if g, ok := gov.Rules[r.ID]; ok {
			if g.Mode == "ai-confirm" && r.Detection.Mode == "deterministic" {
				r.Detection.Mode = "ai-confirm"
				if r.Precision == "" || r.Precision == "high" {
					r.Precision = "low"
				}
				if r.AIQuestion == "" {
					r.AIQuestion = g.AIQuestion
				}
				if r.AIQuestion == "" {
					r.AIQuestion = "Is this really a case of \"" + r.Title + "\" in this code, not a look-alike the rule cannot tell apart (different type or binding, guarded, intentional, test or generated code)?"
				}
			}
			if g.Precision != "" {
				r.Precision = g.Precision
			}
			if g.ExcludeTests {
				r.Detection.ExcludeTests = true
			}
			if g.Status != "" && r.Status != "retired" {
				r.Status, r.StatusReason = g.Status, g.StatusReason
			}
		}
	}
	return nil
}

func readYAML(fsys fs.FS, path string, v any) error {
	if fsys == nil {
		return nil
	}
	b, err := fs.ReadFile(fsys, path)
	if errors.Is(err, fs.ErrNotExist) {
		return nil
	}
	if err != nil {
		return err
	}
	return yaml.Unmarshal(b, v)
}

// union appends the entries of b missing from a, keeping a's order.
func union(a, b []string) []string {
	if len(b) == 0 {
		return a
	}
	seen := make(map[string]bool, len(a)+len(b))
	out := make([]string, 0, len(a)+len(b))
	for _, l := range [][]string{a, b} {
		for _, v := range l {
			if !seen[v] {
				seen[v] = true
				out = append(out, v)
			}
		}
	}
	return out
}

package rules

import (
	"errors"
	"fmt"
	"io/fs"
	"math"
	"strings"
)

// Trust levels (rules/data/trust.yaml, computed by `go run ./tools/trust compute`):
//
//	proven       labelled external cases (linter suites, benchmarks): >= TrustProvenTP true
//	             positives at precision >= TrustProvenPrecision, metamorphic-stable, no corpus anomaly
//	measured     some external evidence and nothing against it: labelled precision >= TrustGate, or
//	             corpus hits below every anomaly threshold (only for rules listed in
//	             tools/trust/silence-grandfathered.txt; any other rule needs a sampled review of
//	             its corpus hits in tools/corpus/labels.yaml); metamorphic-stable
//	unproven     only the rule's own examples (or evidence against it: anomaly, unstable variants)
//	quarantined  status: shadow
//
// Policy: an unproven deterministic rule runs as ai-confirm, so its hits reach the review list
// only with a high-confidence AI confirmation. rulecheck fails a deterministic rule whose
// labelled precision is below TrustGate.
const (
	TrustProven      = "proven"
	TrustMeasured    = "measured"
	TrustUnproven    = "unproven"
	TrustQuarantined = "quarantined"

	TrustGate            = 0.90
	TrustProvenPrecision = 0.95
	TrustProvenTP        = 5
	TrustMinLabelled     = 3
	// TrustPromoteLB: an ai-confirm rule reports directly (deterministic) when the 95% Wilson lower
	// bound of its precision over labelled cases, counting unlabelled OSS corpus hits as false
	// positives, reaches this value (tools/trust compute sets Promoted).
	TrustPromoteLB = 0.95
)

// WilsonLower is the lower bound of the 95% Wilson score interval for tp successes in n trials.
func WilsonLower(tp, n int) float64 {
	if n <= 0 {
		return 0
	}
	const z = 1.959963984540054
	p, nf := float64(tp)/float64(n), float64(n)
	den := 1 + z*z/nf
	c := p + z*z/(2*nf)
	m := z * math.Sqrt(p*(1-p)/nf+z*z/(4*nf*nf))
	return (c - m) / den
}

var TrustLevels = []string{TrustProven, TrustMeasured, TrustUnproven, TrustQuarantined}

// Trust is one rules/data/trust.yaml entry.
type Trust struct {
	Level string `yaml:"level" json:"level"`
	// Labelled external cases (must-match / must-not-match), tools/corpus fixtures.
	TP int `yaml:"tp,omitempty" json:"tp,omitempty"`
	FP int `yaml:"fp,omitempty" json:"fp,omitempty"`
	FN int `yaml:"fn,omitempty" json:"fn,omitempty"`
	TN int `yaml:"tn,omitempty" json:"tn,omitempty"`
	// Corpus: hits (reported + pending) and repos on the pinned corpus; anomaly flags.
	CorpusHits  int      `yaml:"corpus_hits,omitempty" json:"corpus_hits,omitempty"`
	CorpusRepos int      `yaml:"corpus_repos,omitempty" json:"corpus_repos,omitempty"`
	Anomalies   []string `yaml:"anomalies,omitempty" json:"anomalies,omitempty"`
	// Metamorphic: stable | unstable | n/a, with the failing variants.
	Metamorphic string   `yaml:"metamorphic,omitempty" json:"metamorphic,omitempty"`
	Unstable    []string `yaml:"unstable,omitempty" json:"unstable,omitempty"`
	// Demoted: the policy turned this deterministic rule into ai-confirm (set at load time).
	Demoted bool `yaml:"-" json:"demoted,omitempty"`
	// declared precision before the demotion (UndoTrustDemotion).
	declaredPrecision string
	Why               string `yaml:"why,omitempty" json:"why,omitempty"`
	// Promoted: the precision Wilson lower bound (WilsonLB) reached TrustPromoteLB, so a declared
	// ai-confirm rule reports directly. FixFixed/FixIntroduced: fix-commit differential counts.
	Promoted      bool    `yaml:"promoted,omitempty" json:"promoted,omitempty"`
	WilsonLB      float64 `yaml:"wilson_lb,omitempty" json:"wilson_lb,omitempty"`
	FixFixed      int     `yaml:"fix_fixed,omitempty" json:"fix_fixed,omitempty"`
	FixIntroduced int     `yaml:"fix_introduced,omitempty" json:"fix_introduced,omitempty"`
}

// Labelled reports whether there are enough labelled external cases to judge precision.
func (t *Trust) Labelled() bool { return t != nil && t.TP+t.FP >= TrustMinLabelled }

// Precision over labelled cases (0 when none).
func (t *Trust) Precision() float64 {
	if t == nil || t.TP+t.FP == 0 {
		return 0
	}
	return float64(t.TP) / float64(t.TP+t.FP)
}

func (t *Trust) String() string {
	if t == nil {
		return "unproven (no trust data)"
	}
	s := t.Level
	if t.TP+t.FP+t.FN+t.TN > 0 {
		s += fmt.Sprintf("; labelled TP %d FP %d FN %d TN %d", t.TP, t.FP, t.FN, t.TN)
	}
	if t.CorpusHits > 0 {
		s += fmt.Sprintf("; corpus %d hits / %d repos", t.CorpusHits, t.CorpusRepos)
	}
	if len(t.Anomalies) > 0 {
		s += fmt.Sprintf("; anomalies %v", t.Anomalies)
	}
	if t.Metamorphic != "" {
		s += "; metamorphic " + t.Metamorphic
	}
	if t.Demoted {
		s += "; runs as ai-confirm (unproven)"
	}
	if t.Promoted {
		s += fmt.Sprintf("; promoted (Wilson LB %.3f)", t.WilsonLB)
	}
	return s
}

// ApplyTrust attaches data/trust.yaml and applies the policy. Without a trust file (user rule
// directories) nothing changes; with one, a rule missing from it is unproven.
func ApplyTrust(all []*Rule, fsys fs.FS) error {
	var tr struct {
		Rules map[string]*Trust `yaml:"rules"`
	}
	if fsys == nil {
		return nil
	}
	if _, err := fs.Stat(fsys, "data/trust.yaml"); errors.Is(err, fs.ErrNotExist) {
		return nil
	}
	if err := readYAML(fsys, "data/trust.yaml", &tr); err != nil {
		return err
	}
	for _, r := range all {
		t := tr.Rules[r.ID]
		if t == nil {
			t = &Trust{Level: TrustUnproven, Why: "not in trust.yaml (new rule)"}
		} else {
			c := *t
			t = &c
		}
		if r.Shadow() {
			t.Level = TrustQuarantined
		}
		r.Trust = t
		if t.Promoted && r.Detection.Mode == "ai-confirm" && r.Origin != "custom" && !r.Shadow() {
			r.Detection.Mode = "deterministic"
			t.Why = strings.TrimPrefix(t.Why+"; ", "; ") + fmt.Sprintf("promoted to deterministic: precision Wilson lower bound %.3f >= %.2f", t.WilsonLB, TrustPromoteLB)
		}
		if t.Level == TrustUnproven && r.MatchKind == MatchKindExactAPI && r.Detection.Mode == "deterministic" {
			t.Why = strings.TrimPrefix(t.Why+"; ", "; ") + "exact-api: reports directly (version-gated exact identifier match)"
		}
		if t.Level == TrustUnproven && IsMetric(r) && r.Detection.Mode == "deterministic" {
			t.Why = strings.TrimPrefix(t.Why+"; ", "; ") + "metric: reports directly (measured value above the configured threshold)"
		}
		if t.Level == TrustUnproven && r.Detection.Mode == "deterministic" && r.Origin != "custom" && !ReportsUnproven(r) {
			r.Detection.Mode = "ai-confirm"
			t.Demoted, t.declaredPrecision = true, r.Precision
			if r.Precision == "" || r.Precision == "high" {
				r.Precision = "medium"
			}
			if r.AIQuestion == "" {
				r.AIQuestion = "Is this really a case of \"" + r.Title + "\" in this code, not a look-alike the rule cannot tell apart (different type or binding, guarded, intentional, test or generated code)?"
			}
		}
	}
	return nil
}

// UndoTrustDemotion restores the declared deterministic mode of rules the trust policy demoted
// (config trust.deterministic_min: unproven).
func UndoTrustDemotion(all []*Rule) int {
	n := 0
	for _, r := range all {
		if t := r.Trust; t != nil && t.Demoted {
			r.Detection.Mode, r.Precision, t.Demoted = "deterministic", t.declaredPrecision, false
			n++
		}
	}
	return n
}

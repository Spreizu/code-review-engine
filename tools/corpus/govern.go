package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"maps"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	"gopkg.in/yaml.v3"

	"github.com/elmo/code-review-engine/internal/rules"
)

const govPath = "rules/data/governance.yaml"

const govHeader = `# Rule governance: precision tier, demotion to ai-confirm and quarantine (status: shadow),
# decided by triage of the self-scan, corpus runs and linter-fixture evaluation (tools/corpus)
# and by ` + "`crev feedback fp`" + `. Applied at load time (internal/rules.ApplyData).
#   mode: ai-confirm  a deterministic rule with measured precision below the gate: its hits reach
#                     the review list only after a high-confidence AI confirmation.
#   status: shadow    the rule runs, its hits are counted in the report's "shadow" map (kept with
#                     --include-shadow) but never reach the review list or the gate.
# Promote a rule by fixing its false positives (adding them as examples.regressions), re-running
# ` + "`go run ./tools/corpus fixtures` / `run`" + ` and ` + "`govern -promote`" + ` (or deleting the entry).
# Entries with a "corpus:" note were written by ` + "`go run ./tools/corpus govern`" + `.
`

func readGov() map[string]rules.Governance {
	var g struct {
		Rules map[string]rules.Governance `yaml:"rules"`
	}
	if b, err := os.ReadFile(govPath); err == nil {
		die(yaml.Unmarshal(b, &g))
	}
	if g.Rules == nil {
		g.Rules = map[string]rules.Governance{}
	}
	return g.Rules
}

func writeGov(m map[string]rules.Governance) {
	var b strings.Builder
	b.WriteString(govHeader)
	if len(m) == 0 {
		b.WriteString("rules: {}\n")
	} else {
		b.WriteString("rules:\n")
		for _, id := range slices.Sorted(maps.Keys(m)) {
			one, err := yaml.Marshal(map[string]rules.Governance{id: m[id]})
			die(err)
			for _, l := range strings.Split(strings.TrimRight(string(one), "\n"), "\n") {
				b.WriteString("  " + l + "\n")
			}
		}
	}
	die(os.WriteFile(govPath, []byte(b.String()), 0o644))
}

// govern turns fixture measurements into governance: deterministic rules whose precision on
// the linter's own labelled cases is below -min-precision (with at least -min-fp scored false
// positives) are demoted to ai-confirm. -promote removes harness-written demotions of rules
// that now measure at or above the gate.
func govern(args []string) {
	fs := flag.NewFlagSet("govern", flag.ExitOnError)
	label := fs.String("fixtures", "after", "fixtures result label")
	minP := fs.Float64("min-precision", 0.9, "precision gate for deterministic rules")
	minFP := fs.Int("min-fp", 2, "minimum scored false positives before demoting")
	promote := fs.Bool("promote", false, "remove harness demotions of rules now above the gate")
	dry := fs.Bool("n", false, "dry run")
	fs.Parse(args)
	var res []fresult
	b, err := os.ReadFile(filepath.Join(dir, "results", "fixtures-"+*label, "fixtures.json"))
	die(err)
	die(json.Unmarshal(b, &res))
	gov := readGov()
	day := time.Now().Format("2006-01-02")
	var demoted, promoted []string
	for _, r := range res {
		p := r.precision()
		g, has := gov[r.Rule]
		harness := has && strings.HasPrefix(g.Corpus, "fixtures")
		switch {
		case p >= 0 && p < *minP && r.FP >= *minFP && r.Mode == "deterministic" && !has:
			gov[r.Rule] = rules.Governance{Mode: "ai-confirm", Precision: "low",
				Corpus: fmt.Sprintf("fixtures %s %s: TP %d FP %d FN %d TN %d, precision %.2f < %.2f", day, r.Xref, r.TP, r.FP, r.FN, r.TN, p, *minP)}
			demoted = append(demoted, fmt.Sprintf("%s (%.2f, %d FP)", r.Rule, p, r.FP))
		case *promote && harness && g.Mode == "ai-confirm" && (p < 0 || p >= *minP):
			// measured on the pack's own mode: the run after a fix reports mode ai-confirm (from
			// governance), so judge by numbers only
			if g.ExcludeTests || g.Status != "" { // keep hand-set scope/quarantine, drop the demotion
				gov[r.Rule] = rules.Governance{ExcludeTests: g.ExcludeTests, Status: g.Status, StatusReason: g.StatusReason}
			} else {
				delete(gov, r.Rule)
			}
			promoted = append(promoted, r.Rule)
		}
	}
	slices.Sort(demoted)
	fmt.Printf("demoted %d:\n  %s\npromoted %d: %s\n", len(demoted), strings.Join(demoted, "\n  "), len(promoted), strings.Join(promoted, ", "))
	if !*dry {
		writeGov(gov)
	}
}

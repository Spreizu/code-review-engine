// Command rulecheck validates rule packs: schema-level fields, unique ids, citation fields,
// and executes every rule's examples through the real engine (internal/engine):
// tree-sitter rules must match examples.bad and not examples.good (JavaScript rules under
// both the javascript and typescript grammars), config rules are evaluated against the
// examples parsed as config files, manifest rules against examples materialised as a
// throw-away project directory. Every source URL must be listed in sources.yaml.
// The checks themselves live in internal/rulecheck (shared with `crev rules validate`).
//
//	go run ./tools/rulecheck [-sources sources.yaml] rules/packs/*/*.yaml
package main

import (
	"flag"
	"fmt"
	"maps"
	"os"
	"path/filepath"
	"slices"
	"strings"

	"gopkg.in/yaml.v3"

	"github.com/elmo/code-review-engine/internal/rulecheck"
	"github.com/elmo/code-review-engine/internal/rules"
)

func main() {
	sourcesPath := flag.String("sources", "sources.yaml", "sources registry every rule URL must appear in (empty to skip)")
	verbose := flag.Bool("v", false, "print every rule")
	flag.String("data", "rules", "directory holding data/{xref,taxonomy,governance}.yaml applied to the packs (empty to skip)")
	flag.Parse()
	dataDir := flag.Lookup("data").Value.String()
	all, err := rules.LoadFiles(flag.Args()...)
	if err != nil {
		fmt.Println("FAIL load:", err)
		os.Exit(1)
	}
	if dataDir != "" {
		if err := rules.ApplyData(all, os.DirFS(dataDir)); err != nil {
			fmt.Println("FAIL data:", err)
			os.Exit(1)
		}
	}
	known := map[string]bool{}
	if *sourcesPath != "" {
		if b, err := os.ReadFile(*sourcesPath); err == nil {
			var s struct {
				Sources []struct {
					URL string `yaml:"url"`
				} `yaml:"sources"`
			}
			if err := yaml.Unmarshal(b, &s); err != nil {
				fmt.Println("FAIL sources.yaml:", err)
				os.Exit(1)
			}
			for _, e := range s.Sources {
				known[e.URL] = true
			}
		}
	}
	failures := layoutCheck(flag.Args())
	type cnt struct{ det, ai, ts, cfg, man, idx int }
	counts := map[string]*cnt{}
	trustDist := map[string]int{}
	exactN := 0
	for _, r := range all {
		c := counts[r.Pack]
		if c == nil {
			c = &cnt{}
			counts[r.Pack] = c
		}
		if r.Detection.Mode == "ai-confirm" {
			c.ai++
		} else {
			c.det++
		}
		res := rulecheck.Check(r, rulecheck.Options{RequireSource: true})
		errs := res.Errors
		if len(known) > 0 && !known[r.Source.URL] {
			errs = append(errs, "source url not in sources.yaml: "+r.Source.URL)
		}
		if t := r.Trust; t != nil {
			trustDist[t.Level]++
			if !slices.Contains(rules.TrustLevels, t.Level) {
				errs = append(errs, "trust: unknown level "+t.Level)
			}
			// Trust gate: a deterministic rule must not ship below the labelled-precision threshold.
			if r.Detection.Mode == "deterministic" && t.Labelled() && t.Precision() < rules.TrustGate {
				errs = append(errs, fmt.Sprintf("trust: deterministic rule with labelled precision %.2f < %.2f (TP %d FP %d); fix it or demote it (governance mode: ai-confirm)", t.Precision(), rules.TrustGate, t.TP, t.FP))
			}
			if r.Detection.Mode == "deterministic" && t.Level == rules.TrustUnproven && !rules.ReportsUnproven(r) {
				errs = append(errs, "trust: unproven rule running deterministic")
			}
		}
		// match_kind must agree with the classifier both ways (declared mode = before trust demotion).
		declared := *r
		if r.Trust != nil && r.Trust.Demoted {
			declared.Detection.Mode = "deterministic"
		}
		exact, why := rules.ExactAPI(&declared)
		switch {
		case r.MatchKind == rules.MatchKindMetric:
			if !rules.IsMetric(r) {
				errs = append(errs, "match_kind: metric needs a metric.gt/metric.ge filter")
			}
		case r.MatchKind != "" && r.MatchKind != rules.MatchKindExactAPI:
			errs = append(errs, "match_kind: unknown value "+r.MatchKind)
		case r.MatchKind == rules.MatchKindExactAPI && !exact:
			errs = append(errs, "match_kind: exact-api but the classifier rejects it ("+why+"); run `go run ./tools/trust classify`")
		case r.MatchKind == "" && exact:
			errs = append(errs, "match_kind: classifier marks this exact-api but rules/data/matchkind.yaml does not; run `go run ./tools/trust classify`")
		}
		if r.MatchKind == rules.MatchKindExactAPI {
			exactN++
		}
		switch r.Detection.Engine {
		case "tree-sitter":
			c.ts++
		case "config":
			c.cfg++
		case "manifest":
			c.man++
		case "index":
			c.idx++
		}
		if len(errs) > 0 {
			failures++
			fmt.Printf("FAIL %s %s\n   - %s\n", r.File, r.ID, strings.Join(errs, "\n   - "))
		} else if *verbose {
			fmt.Printf("ok   %s\n", r.ID)
		}
	}
	keys := slices.Sorted(maps.Keys(counts))
	tot := cnt{}
	fmt.Printf("%-16s %6s %6s %6s %6s %6s %6s %6s\n", "pack", "rules", "determ", "ai", "ts", "config", "manif", "index")
	for _, k := range keys {
		c := counts[k]
		fmt.Printf("%-16s %6d %6d %6d %6d %6d %6d %6d\n", k, c.det+c.ai, c.det, c.ai, c.ts, c.cfg, c.man, c.idx)
		tot.det += c.det
		tot.ai += c.ai
		tot.ts += c.ts
		tot.cfg += c.cfg
		tot.man += c.man
		tot.idx += c.idx
	}
	fmt.Printf("%-16s %6d %6d %6d %6d %6d %6d %6d\n", "TOTAL", tot.det+tot.ai, tot.det, tot.ai, tot.ts, tot.cfg, tot.man, tot.idx)
	if len(trustDist) > 0 {
		fmt.Printf("trust: proven=%d measured=%d unproven=%d quarantined=%d\n", trustDist[rules.TrustProven], trustDist[rules.TrustMeasured], trustDist[rules.TrustUnproven], trustDist[rules.TrustQuarantined])
		fmt.Printf("match_kind: exact-api=%d\n", exactN)
	}
	fmt.Printf("total=%d failures=%d\n", len(all), failures)
	if failures > 0 {
		os.Exit(1)
	}
}

// layoutCheck enforces the catalog layout rules/packs/<pack>/<topic>[.gen].yaml: a generated file
// carries the GENERATED header, a hand-edited file the HAND-EDITED header, and rules are sorted by
// id within a file (stable diffs). Files outside a packs/<pack>/ directory are not checked.
func layoutCheck(files []string) int {
	bad := 0
	for _, f := range files {
		dir := filepath.Dir(f)
		if filepath.Base(filepath.Dir(dir)) != "packs" {
			continue
		}
		b, err := os.ReadFile(f)
		if err != nil {
			continue
		}
		gen := strings.HasSuffix(f, ".gen.yaml")
		want := "# HAND-EDITED"
		if gen {
			want = "# GENERATED"
		}
		if !strings.HasPrefix(string(b), want) {
			fmt.Printf("FAIL layout %s: must start with %q\n", f, want)
			bad++
		}
		var p struct {
			Rules []struct {
				ID string `yaml:"id"`
			} `yaml:"rules"`
		}
		if yaml.Unmarshal(b, &p) == nil {
			for i := 1; i < len(p.Rules); i++ {
				if p.Rules[i-1].ID > p.Rules[i].ID {
					fmt.Printf("FAIL layout %s: rules not sorted by id (%s before %s)\n", f, p.Rules[i-1].ID, p.Rules[i].ID)
					bad++
					break
				}
			}
		}
	}
	return bad
}

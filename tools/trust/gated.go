package main

// gated regenerates tools/trust/gated-triage.md from gated-triage.tsv (per-pack table and
// top-N lists). The tsv is the source of truth; the md is the human-readable summary.
//
//	go run ./tools/trust gated
import (
	"bufio"
	"bytes"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"slices"
	"strconv"
	"strings"
)

const (
	gatedTSV = "tools/trust/gated-triage.tsv"
	gatedMD  = "tools/trust/gated-triage.md"
)

type gatedRow struct {
	ID, Pack, Category, Level, Bucket, Reason, Action string
	hits, repos                                       int
}

var hitsRe = regexp.MustCompile(`(\d+)(?: corpus)? hits?/(\d+) repos`)

func parseGatedTSV(path string) []gatedRow {
	f, err := os.Open(path)
	die(err)
	defer f.Close()
	sc := bufio.NewScanner(f)
	sc.Buffer(nil, 1<<20)
	var out []gatedRow
	first := true
	for sc.Scan() {
		line := sc.Text()
		if first {
			first = false
			continue
		}
		if strings.TrimSpace(line) == "" {
			continue
		}
		p := strings.Split(line, "\t")
		if len(p) < 7 {
			die(fmt.Errorf("%s: expected 7 columns, got %d: %s", path, len(p), line))
		}
		r := gatedRow{ID: p[0], Pack: p[1], Category: p[2], Level: p[3], Bucket: p[4], Reason: p[5], Action: p[6]}
		if m := hitsRe.FindStringSubmatch(r.Reason); m != nil {
			r.hits, _ = strconv.Atoi(m[1])
			r.repos, _ = strconv.Atoi(m[2])
		}
		out = append(out, r)
	}
	die(sc.Err())
	return out
}

func catRank(cat string) int {
	switch cat {
	case "security":
		return 0
	case "correctness":
		return 1
	default:
		return 2
	}
}

func gatedSort(a, b gatedRow) int {
	if d := catRank(a.Category) - catRank(b.Category); d != 0 {
		return d
	}
	if d := b.hits - a.hits; d != 0 {
		return d
	}
	return strings.Compare(a.ID, b.ID)
}

func gitHEAD() string {
	b, err := exec.Command("git", "rev-parse", "--short", "HEAD").Output()
	if err != nil {
		return "unknown"
	}
	return strings.TrimSpace(string(b))
}

func gated(args []string) {
	fs := flag.NewFlagSet("gated", flag.ExitOnError)
	tsv := fs.String("tsv", gatedTSV, "gated triage tsv")
	md := fs.String("md", gatedMD, "markdown summary to rewrite")
	fs.Parse(args)
	rows := parseGatedTSV(*tsv)
	n := map[string]int{}
	per := map[string][3]int{}
	var aRows, bRows []gatedRow
	for _, r := range rows {
		n[r.Bucket]++
		t := per[r.Pack]
		switch r.Bucket {
		case "A":
			t[0]++
			aRows = append(aRows, r)
		case "B":
			t[1]++
			bRows = append(bRows, r)
		case "C":
			t[2]++
		}
		per[r.Pack] = t
	}
	slices.SortFunc(aRows, gatedSort)
	slices.SortFunc(bRows, gatedSort)
	if len(aRows) > 30 {
		aRows = aRows[:30]
	}
	if len(bRows) > 30 {
		bRows = bRows[:30]
	}

	var b strings.Builder
	fmt.Fprintf(&b, "# Gated-rule triage (HEAD %s)\n\n", gitHEAD())
	b.WriteString("Analysis only: no rule, engine or label changes. Scope: every rule that does not report directly\n")
	fmt.Fprintf(&b, "(effective mode ai-confirm after trust policy, or quarantined/shadow): **%d rules**. Generated from `gated-triage.tsv` by `go run ./tools/trust gated`.\n\n", len(rows))
	b.WriteString("Buckets:\n")
	b.WriteString("- **A fixable-by-construction**: tighten query/filters for labelled FPs, type/framework/index gate, exact-api conversion or version gating, generated cases from official docs/linter test suites.\n")
	b.WriteString("- **B needs-data**: logic plausibly precise; missing evidence (no corpus hits, unreviewed volume anomaly, unlabelled hits, taint without labelled cases).\n")
	b.WriteString("- **C inherently-semantic**: intent/context judgement (author-declared AI questions about purpose, production intent, secrets, naming heuristics, `gated.tsv` entries); stays AI.\n\n")
	b.WriteString("## Counts\n\n| bucket | rules |\n|---|---|\n")
	fmt.Fprintf(&b, "| A | %d |\n| B | %d |\n| C | %d |\n\n", n["A"], n["B"], n["C"])
	b.WriteString("## Per pack\n\n| pack | A | B | C | total |\n|---|---|---|---|---|\n")
	packs := make([]string, 0, len(per))
	for p := range per {
		packs = append(packs, p)
	}
	slices.Sort(packs)
	for _, p := range packs {
		t := per[p]
		fmt.Fprintf(&b, "| %s | %d | %d | %d | %d |\n", p, t[0], t[1], t[2], t[0]+t[1]+t[2])
	}
	writeTop := func(title string, rs []gatedRow) {
		fmt.Fprintf(&b, "\n## %s\n\n| rule | pack | category | hits/repos | reason |\n|---|---|---|---|---|\n", title)
		for _, r := range rs {
			reason := r.Reason
			if len(reason) > 90 {
				reason = reason[:90]
			}
			fmt.Fprintf(&b, "| %s | %s | %s | %d/%d | %s |\n", r.ID, r.Pack, r.Category, r.hits, r.repos, reason)
		}
	}
	writeTop("Top 30 A (fixable-by-construction): security/correctness first, then corpus hits", aRows)
	writeTop("Top 30 B (needs-data): security/correctness first, then corpus hits", bRows)
	b.WriteString(`
## User policy: linter suppressions

Linter suppression comments in code (` + "`" + `// eslint-disable-next-line` + "`" + `, ` + "`" + `# noqa` + "`" + `, ` + "`" + `//nolint` + "`" + `, ` + "`" + `@SuppressWarnings` + "`" + `, ` + "`" + `@phpstan-ignore` + "`" + ` etc.) indicate a real underlying problem that someone chose to accept, not a rule mismatch.
- **Measurement:** a crev hit at a suppressed location counts as a **true positive** (corpus labelling, precision, promotion).
- **Reporting:** crev still honors the suppression and does not report the finding when the suppression for the matching rule is set.

## Notes

- Classification is heuristic over metadata; borderline rules lean to A when the AI question is structurally decidable (receiver type, binding, config elsewhere) and to C when it asks about purpose/intent.
- B is dominated by deterministic rules with own examples only (no corpus hits) and below-threshold unlabelled hits; the cheapest wins are the ~180 'awaiting sampled hit review' rules and the volume anomalies (same 20-hit sample procedure already used for Java/Python/Go/JS/Kotlin/PHP).
- A includes linter-linked rules with no hits: importing the upstream linter's own test suite (as done for the 561 labelled rules) is the generated-case route.
- Taint rules are B: the engine path is precise; they need labelled source/sanitizer cases (Benchmark, CVE fix pairs).
- Migration/deprecation rules not yet exact-api are A: convert to anchored predicates + applies_to, or generate cases from the official migration guide.
- Classifier script was a throwaway (not committed); this file is regenerated from the tsv. Sampled hit reviews: ` + "`" + `tools/trust/sampled-review.md` + "`" + `.
`)
	out := []byte(b.String())
	prev, _ := os.ReadFile(*md)
	if bytes.Equal(prev, out) {
		fmt.Printf("gated: %d rules A=%d B=%d C=%d (unchanged) -> %s\n", len(rows), n["A"], n["B"], n["C"], *md)
		return
	}
	die(os.WriteFile(*md, out, 0o644))
	fmt.Printf("gated: %d rules A=%d B=%d C=%d -> %s\n", len(rows), n["A"], n["B"], n["C"], *md)
}

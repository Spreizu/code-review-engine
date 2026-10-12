package main

// bench scores OWASP Benchmark style suites (expectedresults-*.csv: test name, category, real
// vulnerability, CWE) from a corpus run's raw reports. A test counts as flagged when crev reports a
// finding with a matching CWE (or a CWE of the same family) in that test's file. Scored twice:
// review list only (confirmed deterministic findings) and candidates (incl. pending ai-confirm),
// since ai-confirm findings only reach the review list after the AI step.

import (
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strconv"
	"strings"
)

// cweFamily folds CWEs that benchmarks and rules use interchangeably onto one key.
var cweFamily = map[int]int{
	338: 330, 331: 330, 328: 327, 326: 327, 916: 327, 759: 327, 760: 327, 77: 78, 95: 94,
	80: 79, 1004: 614, 611: 611, 776: 611, 917: 94, 1336: 94,
}

func fam(c int) int {
	if f, ok := cweFamily[c]; ok {
		return f
	}
	return c
}

type benchCat struct {
	CWE            int
	TP, FN, FP, TN int // review list
	CandTP, CandFP int // incl. pending ai-confirm
	Rules          map[string]int
}

func cmdBench(args []string) {
	fs := flag.NewFlagSet("bench", flag.ExitOnError)
	label := fs.String("label", "after", "corpus run label")
	fs.Parse(args)
	repos := load().Repos
	var out strings.Builder
	ruleLab := map[string][3]int{} // rule -> {TP, FP, other-category} on labelled benchmark test cases
	fmt.Fprintf(&out, "# OWASP Benchmark scoring (%s)\n\nFlagged = finding with matching CWE family in the test file. TPR = TP/(TP+FN), FPR = FP/(FP+TN). \"Review\" counts confirmed findings only; \"candidates\" adds pending ai-confirm findings (they still need AI confirmation at high confidence).\n", *label)
	for _, r := range repos {
		if r.Kind != "bench" {
			continue
		}
		exp, _ := filepath.Glob(filepath.Join(cacheDir(r), "expectedresults-*.csv"))
		if len(exp) == 0 {
			continue
		}
		raw := filepath.Join("tools/corpus/results", *label, "raw", r.Name+".json")
		b, err := os.ReadFile(raw)
		if err != nil {
			fmt.Fprintf(&out, "\n## %s\n\nno raw results (%v)\n", r.Name, err)
			continue
		}
		var rep struct {
			Findings []struct {
				RuleID   string   `json:"rule_id"`
				Status   string   `json:"status"`
				CWE      []string `json:"cwe"`
				Location struct {
					Path string `json:"path"`
				} `json:"location"`
			} `json:"findings"`
		}
		json.Unmarshal(b, &rep)
		type hit struct {
			fam    int
			review bool
			rule   string
		}
		byTest := map[string][]hit{}
		for _, f := range rep.Findings {
			if f.Status != "confirmed" && f.Status != "pending_ai" && f.Status != "ai_confirmed" {
				continue
			}
			base := filepath.Base(f.Location.Path)
			test := strings.TrimSuffix(base, filepath.Ext(base))
			if !strings.HasPrefix(test, "BenchmarkTest") {
				continue
			}
			for _, cs := range f.CWE {
				c, _ := strconv.Atoi(strings.TrimPrefix(cs, "CWE-"))
				byTest[test] = append(byTest[test], hit{fam(c), f.Status != "pending_ai", f.RuleID})
			}
		}
		fh, _ := os.Open(exp[0])
		cr := csv.NewReader(fh)
		cr.FieldsPerRecord = -1
		rows, _ := cr.ReadAll()
		fh.Close()
		cats := map[string]*benchCat{}
		benchFams := map[int]bool{}
		for _, row := range rows {
			if len(row) >= 4 && !strings.HasPrefix(row[0], "#") {
				c, _ := strconv.Atoi(strings.TrimSpace(row[3]))
				benchFams[fam(c)] = true
			}
		}
		for _, row := range rows {
			if len(row) < 4 || strings.HasPrefix(row[0], "#") {
				continue
			}
			cwe, _ := strconv.Atoi(strings.TrimSpace(row[3]))
			real := strings.TrimSpace(row[2]) == "true"
			c := cats[row[1]]
			if c == nil {
				c = &benchCat{CWE: cwe, Rules: map[string]int{}}
				cats[row[1]] = c
			}
			rev, cand := false, false
			seen := map[string]bool{}
			// A rule whose CWE maps to another benchmark category than this test's, and none to
			// this one: an unlabelled hit, which tools/trust counts against promotion.
			inCat, other := map[string]bool{}, map[string]bool{}
			for _, h := range byTest[row[0]] {
				if h.fam == fam(cwe) {
					inCat[h.rule] = true
				} else if benchFams[h.fam] {
					other[h.rule] = true
				}
			}
			for id := range other {
				if !inCat[id] {
					lr := ruleLab[id]
					lr[2]++
					ruleLab[id] = lr
				}
			}
			for _, h := range byTest[row[0]] {
				if h.fam == fam(cwe) {
					cand = true
					if h.review {
						rev = true
					}
					c.Rules[h.rule]++
					if !seen[h.rule] { // per-rule labelled outcome (tools/trust): one per test case
						seen[h.rule] = true
						lr := ruleLab[h.rule]
						if real {
							lr[0]++
						} else {
							lr[1]++
						}
						ruleLab[h.rule] = lr
					}
				}
			}
			switch {
			case real && rev:
				c.TP++
			case real:
				c.FN++
			case rev:
				c.FP++
			default:
				c.TN++
			}
			if cand && real {
				c.CandTP++
			} else if cand {
				c.CandFP++
			}
		}
		names := make([]string, 0, len(cats))
		for n := range cats {
			names = append(names, n)
		}
		slices.Sort(names)
		fmt.Fprintf(&out, "\n## %s (%s)\n\n| category | CWE | real | TPR review | FPR review | score | TPR cand | FPR cand | rules |\n|---|---|---|---|---|---|---|---|---|\n", r.Name, filepath.Base(exp[0]))
		var t benchCat
		for _, n := range names {
			c := cats[n]
			real, fake := c.TP+c.FN, c.FP+c.TN
			tpr, fpr := ratio(c.TP, real), ratio(c.FP, fake)
			rs := []string{}
			for k, v := range c.Rules {
				rs = append(rs, fmt.Sprintf("%s(%d)", k, v))
			}
			slices.Sort(rs)
			if len(rs) > 4 {
				rs = append(rs[:4], "…")
			}
			fmt.Fprintf(&out, "| %s | %d | %d | %.2f | %.2f | %+.2f | %.2f | %.2f | %s |\n", n, c.CWE, real, tpr, fpr, tpr-fpr, ratio(c.CandTP, real), ratio(c.CandFP, fake), strings.Join(rs, " "))
			t.TP += c.TP
			t.FN += c.FN
			t.FP += c.FP
			t.TN += c.TN
			t.CandTP += c.CandTP
			t.CandFP += c.CandFP
		}
		fmt.Fprintf(&out, "| **all** | | %d | %.2f | %.2f | %+.2f | %.2f | %.2f | |\n", t.TP+t.FN, ratio(t.TP, t.TP+t.FN), ratio(t.FP, t.FP+t.TN), ratio(t.TP, t.TP+t.FN)-ratio(t.FP, t.FP+t.TN), ratio(t.CandTP, t.TP+t.FN), ratio(t.CandFP, t.FP+t.TN))
	}
	vulnApps(&out, repos, *label)
	p := filepath.Join("tools/corpus/results", *label, "bench.md")
	os.WriteFile(p, []byte(out.String()), 0o644)
	type lab struct {
		TP    int `json:"tp"`
		FP    int `json:"fp"`
		Other int `json:"other,omitempty"`
	}
	lr := map[string]lab{}
	for id, v := range ruleLab {
		lr[id] = lab{v[0], v[1], v[2]}
	}
	b, _ := json.MarshalIndent(lr, "", " ")
	os.WriteFile(filepath.Join("tools/corpus/results", *label, "bench-rules.json"), b, 0o644)
	fmt.Println(p)
}

func ratio(a, b int) float64 {
	if b == 0 {
		return 0
	}
	return float64(a) / float64(b)
}

type rawFinding struct {
	RuleID   string   `json:"rule_id"`
	Status   string   `json:"status"`
	Kind     string   `json:"kind"`
	CWE      []string `json:"cwe"`
	OWASP    []string `json:"owasp"`
	Location struct {
		Path      string `json:"path"`
		StartLine int    `json:"start_line"`
		EndLine   int    `json:"end_line"`
	} `json:"location"`
}

func readRaw(label, repo string) ([]rawFinding, error) {
	b, err := os.ReadFile(filepath.Join("tools/corpus/results", label, "raw", repo+".json"))
	if err != nil {
		return nil, err
	}
	var rep struct {
		Findings []rawFinding `json:"findings"`
	}
	return rep.Findings, json.Unmarshal(b, &rep)
}

var vulnLineRe = regexp.MustCompile(`vuln-code-snippet vuln-line ([\w ]+)`)

// vulnApps: deliberately vulnerable apps have no complete ground truth, so report security finding
// counts per OWASP Top 10 category (review list vs candidates) and, where the app marks its
// vulnerable lines (Juice Shop "vuln-code-snippet vuln-line"), the share of marked challenges hit.
func vulnApps(out *strings.Builder, repos []Repo, label string) {
	fmt.Fprintf(out, "\n# Vulnerable apps\n\n| app | security review | security candidates | OWASP categories (review+candidates) |\n|---|---|---|---|\n")
	var marked strings.Builder
	for _, r := range repos {
		if r.Kind != "bench" || strings.HasPrefix(r.Name, "Benchmark") {
			continue
		}
		fs, err := readRaw(label, r.Name)
		if err != nil {
			fmt.Fprintf(out, "| %s | n/a | n/a | %v |\n", r.Name, err)
			continue
		}
		rev, cand := 0, 0
		cats := map[string]int{}
		for _, f := range fs {
			if f.Kind != "security" || (f.Status != "confirmed" && f.Status != "pending_ai" && f.Status != "ai_confirmed") {
				continue
			}
			if f.Status == "pending_ai" {
				cand++
			} else {
				rev++
			}
			n := 0
			for _, o := range f.OWASP {
				if c, ok := strings.CutSuffix(o, ":2025"); ok {
					cats[c]++
					n++
				}
			}
			if n == 0 {
				cats["(no 2025 mapping)"]++
			}
		}
		ks := []string{}
		for k, v := range cats {
			ks = append(ks, fmt.Sprintf("%s=%d", k, v))
		}
		slices.Sort(ks)
		fmt.Fprintf(out, "| %s | %d | %d | %s |\n", r.Name, rev, cand, strings.Join(ks, " "))
		// marked vulnerable lines
		type mark struct {
			file string
			line int
		}
		chal := map[string][]mark{}
		filepath.WalkDir(cacheDir(r), func(p string, d os.DirEntry, err error) error {
			if err != nil || d.IsDir() && (d.Name() == "node_modules" || d.Name() == ".git") {
				if d != nil && d.IsDir() {
					return filepath.SkipDir
				}
				return nil
			}
			if d.IsDir() {
				return nil
			}
			b, _ := os.ReadFile(p)
			if !strings.Contains(string(b), "vuln-code-snippet vuln-line") {
				return nil
			}
			rel, _ := filepath.Rel(cacheDir(r), p)
			for i, ln := range strings.Split(string(b), "\n") {
				if m := vulnLineRe.FindStringSubmatch(ln); m != nil {
					for _, c := range strings.Fields(m[1]) {
						chal[c] = append(chal[c], mark{rel, i + 1})
					}
				}
			}
			return nil
		})
		if len(chal) == 0 {
			continue
		}
		hitRev, hitCand := 0, 0
		missed := []string{}
		for c, ms := range chal {
			hr, hc := false, false
			for _, m := range ms {
				// ponytail: markers x findings of one app (a few thousand pairs); a dev-tool report.
				for _, f := range fs {
					if f.Kind != "security" || f.Location.Path != m.file || m.line < f.Location.StartLine-2 || m.line > f.Location.EndLine+2 {
						continue
					}
					switch f.Status {
					case "confirmed", "ai_confirmed":
						hr, hc = true, true
					case "pending_ai":
						hc = true
					}
				}
			}
			if hr {
				hitRev++
			}
			if hc {
				hitCand++
			} else {
				missed = append(missed, c)
			}
		}
		slices.Sort(missed)
		fmt.Fprintf(&marked, "\n## %s marked challenges\n\n%d challenges with vuln-line markers; hit on the review list %d (%.0f%%), as candidates %d (%.0f%%). Missed: %s\n",
			r.Name, len(chal), hitRev, 100*ratio(hitRev, len(chal)), hitCand, 100*ratio(hitCand, len(chal)), strings.Join(missed, ", "))
	}
	out.WriteString(marked.String())
}

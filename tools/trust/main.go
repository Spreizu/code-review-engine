// Command trust computes the per-rule trust level (rules/data/trust.yaml) from the evidence the
// harnesses produce, and runs the metamorphic stability check. Nothing here ships in the binary;
// crev only reads the resulting data file (internal/rules.ApplyTrust).
//
//	go run ./tools/trust metamorphic [-v]          # rewrite every rule's examples, check stability
//	go run ./tools/trust compute [-label after]    # write rules/data/trust.yaml + tools/trust/report.md
//
// Evidence:
//   - labelled external cases: tools/corpus/results/fixtures-after/fixtures.json (linter test suites
//     imported as must-match / must-not-match cases), per rule TP/FP/FN/TN;
//   - corpus: tools/corpus/results/<label>/*.json (pinned OSS repos and benchmark apps), with the
//     same anomaly thresholds as `corpus summarize` (volume, per-repo concentration, file share),
//     computed on OSS repos only (vulnerable apps are expected to light up);
//   - inline linter suppressions and real-linter agreement (results/<label>/suppressions.json,
//     agree.json): matching locations count as labelled true positives;
//   - lint autofix-commit differential (results/<label>/autofix.json) and security fixdiff.json;
//   - metamorphic variants (semantics-preserving rewrites of examples.bad/good/regressions):
//     blank-line padding, an unrelated leading comment, consistent identifier renaming. A rule is
//     unstable when a variant of a must-match example stops matching or a must-not-match variant
//     starts matching.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"maps"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"

	"gopkg.in/yaml.v3"

	"github.com/elmo/code-review-engine/internal/rulecheck"
	"github.com/elmo/code-review-engine/internal/rules"
)

const (
	metaPath  = "tools/trust/metamorphic.json"
	trustPath = "rules/data/trust.yaml"
	report    = "tools/trust/report.md"
	// silencePath lists the rules that may stay measured on corpus silence alone (grandfathered);
	// any other rule needs a sampled review of its corpus hits (tools/corpus/labels.yaml) first.
	silencePath = "tools/trust/silence-grandfathered.txt"
	// anomaly thresholds (tools/corpus summarize)
	flagTotal   = 15
	flagPerRepo = 10
	flagShare   = 0.25
)

func die(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, "trust:", err)
		os.Exit(1)
	}
}

func load() []*rules.Rule {
	all, err := rules.LoadFiles("rules/packs/*/*.yaml")
	die(err)
	die(rules.ApplyBaseData(all, os.DirFS("rules")))
	return all
}

func main() {
	if len(os.Args) < 2 {
		die(fmt.Errorf("usage: trust classify|metamorphic|compute|gated"))
	}
	switch os.Args[1] {
	case "metamorphic":
		metamorphic(os.Args[2:])
	case "compute":
		compute(os.Args[2:])
	case "classify":
		classify()
	case "gated":
		gated(os.Args[2:])
	default:
		die(fmt.Errorf("unknown subcommand %q", os.Args[1]))
	}
}

// ---- metamorphic ----

type MetaResult struct {
	Status   string   `json:"status"` // stable | unstable | n/a
	Variants int      `json:"variants"`
	Failed   []string `json:"failed,omitempty"`
}

var commentPrefix = map[string]string{
	"javascript": "// ", "typescript": "// ", "jsx": "// ", "tsx": "// ", "java": "// ", "go": "// ", "kotlin": "// ",
	"protobuf": "// ", "groovy": "// ", "gradle": "// ", "python": "# ", "yaml": "# ", "docker": "# ", "terraform": "# ",
	"graphql": "# ", "ytt": "# ",
}

// rename applies only to programming languages: in config/data formats identifiers are keys.
var renameLangs = map[string]bool{"javascript": true, "typescript": true, "jsx": true, "tsx": true, "java": true,
	"go": true, "kotlin": true, "python": true, "php": true}

var identRe = regexp.MustCompile(`\b[A-Za-z_][A-Za-z0-9_]*\b`)

var keywords = map[string]bool{}

func init() {
	for _, k := range strings.Fields(`abstract and arguments async await boolean break byte case catch char class const continue
	debugger default delete do double elif else enum eval except export extends false final finally float for from func function
	global goto if implements import in instanceof int interface lambda let long native new nil None not null object or package
	pass private protected public raise return self short static super switch synchronized this throw throws transient True False
	true try typeof undefined var void volatile while with yield def fun val when is as by init constructor override open data
	sealed internal companion lateinit suspend chan defer go map range select struct type fallthrough string number any unknown
	never readonly declare namespace module require keyof infer satisfies echo print array list dict tuple set len make append
	error println printf main String Object Integer List Map Set Array Promise console window document process exports props
	emit setup template script style`) {
		keywords[k] = true
	}
}

func ruleText(r *rules.Rule) string {
	b, _ := yaml.Marshal(struct {
		D rules.Detection
		P map[string]rules.Param
	}{r.Detection, r.Params})
	return string(b) + " " + r.Title + " " + r.Message + " " + r.AIQuestion
}

// declRe finds identifiers the example itself declares (variables, functions, classes, params
// of a declared function are not needed): renaming those consistently cannot change what an API
// call or a library type means, unlike renaming arbitrary identifiers.
var declRe = regexp.MustCompile(`(?m)(?:\b(?:const|let|var|val|def|function|func|class|fun|interface|enum|record)\s+([A-Za-z_]\w*)|^\s*([A-Za-z_]\w*)\s*:?=[^=]|\$([A-Za-z_]\w*)\s*=[^=])`)

// strRe matches string literals; renaming never touches them (secrets, URLs, import paths).
var strRe = regexp.MustCompile("\"(?:\\\\.|[^\"\\\\\n])*\"|'(?:\\\\.|[^'\\\\\n])*'|`[^`]*`")

func renameMap(r *rules.Rule) map[string]string {
	if !renameLangs[r.Language] || r.Detection.Engine != "tree-sitter" && r.Detection.Engine != "taint" {
		return nil
	}
	txt := ruleText(r)
	m := map[string]string{}
	code := strRe.ReplaceAllString(r.Examples.Bad, `""`)
	for _, g := range declRe.FindAllStringSubmatch(code, -1) {
		id := g[1] + g[2] + g[3]
		// string templates ("$id", "${id}") reference the name inside a literal, which renaming skips
		if strings.Contains(r.Examples.Bad, "$"+id) || strings.Contains(r.Examples.Bad, "${"+id) {
			continue
		}
		if len(id) < 3 || keywords[id] || strings.Contains(txt, id) || m[id] != "" || len(m) >= 3 {
			continue
		}
		// keep the identifier's shape (prefix, case style): append a suffix in the same case.
		suffix := "Zq"
		if strings.ToUpper(id) == id {
			suffix = "_ZQ"
		} else if strings.Contains(id, "_") {
			suffix = "_zq"
		}
		m[id] = id + suffix
	}
	return m
}

func applyRename(src string, m map[string]string) string {
	var b strings.Builder
	last := 0
	sub := func(seg string) string {
		return identRe.ReplaceAllStringFunc(seg, func(s string) string {
			if v, ok := m[s]; ok {
				return v
			}
			return s
		})
	}
	for _, loc := range strRe.FindAllStringIndex(src, -1) {
		b.WriteString(sub(src[last:loc[0]]))
		b.WriteString(src[loc[0]:loc[1]])
		last = loc[1]
	}
	b.WriteString(sub(src[last:]))
	return b.String()
}

// exempt lists variants that do not preserve semantics for a rule's subject (reviewed by hand).
var exempt = map[string]string{
	"JSON-QUAL-BOM":                       "blank-lines leading-comment", // the BOM must be the first byte
	"GRAPHQL-QUAL-NO-HASHTAG-DESCRIPTION": "leading-comment",             // the rule is about # comments
	"YTT-QUAL-UNKNOWN-COMMENT-SYNTAX":     "leading-comment",             // the rule is about comment syntax
	"PY-SEC-HARDCODED-PASSWORD":           "rename",                      // the variable name is the evidence
	"PAYLOAD-QUAL-HOOK-WITHOUT-REQ":       "rename",                      // the hook name (afterChange) is the subject
}

type variant struct {
	name string
	f    func(string) string
}

func variants(r *rules.Rule) []variant {
	vs := []variant{{"blank-lines", func(s string) string { return "\n\n" + s }}}
	if p, ok := commentPrefix[r.Language]; ok && r.Detection.Target != "template" {
		vs = append(vs, variant{"leading-comment", func(s string) string {
			if strings.HasPrefix(strings.TrimSpace(s), "<") || strings.HasPrefix(s, "#!") {
				return s
			}
			return p + "crev metamorphic variant\n" + s
		}})
	}
	if m := renameMap(r); len(m) > 0 {
		vs = append(vs, variant{"rename(" + strings.Join(slices.Sorted(maps.Keys(m)), ",") + ")", func(s string) string { return applyRename(s, m) }})
	}
	var out []variant
	for _, v := range vs {
		if !strings.Contains(exempt[r.ID], strings.SplitN(v.name, "(", 2)[0]) {
			out = append(out, v)
		}
	}
	return out
}

func metaCheck(r *rules.Rule) MetaResult {
	if r.Examples.Bad == "" || r.Examples.Good == "" || r.Detection.Engine == "index" {
		return MetaResult{Status: "n/a"}
	}
	if len(rulecheck.ExampleErrors(r)) > 0 { // base examples already failing: rulecheck reports it
		return MetaResult{Status: "n/a"}
	}
	res := MetaResult{Status: "stable"}
	for _, v := range variants(r) {
		c := *r
		c.Examples.Bad, c.Examples.Good, c.Examples.Regressions = v.f(r.Examples.Bad), v.f(r.Examples.Good), nil
		res.Variants++
		if errs := rulecheck.ExampleErrors(&c); len(errs) > 0 {
			res.Failed = append(res.Failed, v.name+": "+errs[0])
		}
		for i, reg := range r.Examples.Regressions {
			if reg.Path != "" {
				continue // path-scoped regressions are path guards, not content cases
			}
			c := *r
			c.Examples.Good, c.Examples.Regressions = v.f(reg.Code), nil
			c.Examples.Bad = v.f(r.Examples.Bad)
			res.Variants++
			for _, e := range rulecheck.ExampleErrors(&c) {
				if strings.Contains(e, "good example") {
					res.Failed = append(res.Failed, fmt.Sprintf("%s regression[%d]: %s", v.name, i, e))
				}
			}
		}
	}
	if len(res.Failed) > 0 {
		res.Status = "unstable"
	}
	return res
}

func metamorphic(args []string) {
	fs := flag.NewFlagSet("metamorphic", flag.ExitOnError)
	verbose := fs.Bool("v", false, "print unstable rules")
	fs.Parse(args)
	out := map[string]MetaResult{}
	cnt := map[string]int{}
	for _, r := range load() {
		m := metaCheck(r)
		out[r.ID] = m
		cnt[m.Status]++
		if *verbose && m.Status == "unstable" {
			fmt.Printf("%s\n   %s\n", r.ID, strings.Join(m.Failed, "\n   "))
		}
	}
	b, _ := json.MarshalIndent(out, "", " ")
	die(os.WriteFile(metaPath, b, 0o644))
	fmt.Printf("metamorphic: stable=%d unstable=%d n/a=%d -> %s\n", cnt["stable"], cnt["unstable"], cnt["n/a"], metaPath)
}

// ---- compute ----

type hit struct {
	Rule   string `json:"rule"`
	Status string `json:"status"`
	Path   string `json:"path"`
	Line   int    `json:"line"`
}
type repoResult struct {
	Repo  string `json:"repo"`
	Kind  string `json:"kind"`
	Files int    `json:"files"`
	Hits  []hit  `json:"hits"`
}
type fres struct {
	Rule string `json:"rule"`
	TP   int    `json:"tp"`
	FP   int    `json:"fp"`
	FN   int    `json:"fn"`
	TN   int    `json:"tn"`
}

type corpusStat struct {
	hits, repos, oss, maxPer int
	share                    float64
}

// present holds "rule|repo|path|line" of every hit of the current corpus run.
var present = map[string]bool{}

func corpus(label string) (map[string]*corpusStat, int) {
	files, _ := filepath.Glob(filepath.Join("tools/corpus/results", label, "*.json"))
	st := map[string]*corpusStat{}
	n := 0
	for _, f := range files {
		var r repoResult
		b, err := os.ReadFile(f)
		die(err)
		if json.Unmarshal(b, &r) != nil || r.Repo == "" {
			continue
		}
		n++
		per := map[string]int{}
		pf := map[string]map[string]bool{}
		for _, h := range r.Hits {
			present[fmt.Sprintf("%s|%s|%s|%d", h.Rule, r.Repo, h.Path, h.Line)] = true
			if h.Status != "confirmed" && h.Status != "pending_ai" {
				continue
			}
			per[h.Rule]++
			if pf[h.Rule] == nil {
				pf[h.Rule] = map[string]bool{}
			}
			pf[h.Rule][h.Path] = true
		}
		for id, c := range per {
			s := st[id]
			if s == nil {
				s = &corpusStat{}
				st[id] = s
			}
			s.hits += c
			s.repos++
			if r.Kind == "" || r.Kind == "oss" {
				s.oss += c
				s.maxPer = max(s.maxPer, c)
				if r.Files > 20 {
					s.share = max(s.share, float64(len(pf[id]))/float64(r.Files))
				}
			}
		}
	}
	return st, n
}

const matchKindPath = "rules/data/matchkind.yaml"

// classify writes rules/data/matchkind.yaml: every rule rules.ExactAPI accepts (version-gated
// deprecation/removal/migration matched by exact identifier/import/config key/dependency).
// rulecheck fails when the file and the classifier disagree.
func classify() {
	all := load()
	out := map[string]string{}
	for _, r := range all {
		if ok, why := rules.ExactAPI(r); ok {
			out[r.ID] = why
		}
	}
	var buf strings.Builder
	buf.WriteString("# match_kind: exact-api, generated by `go run ./tools/trust classify` (classifier: internal/rules/matchkind.go).\n")
	buf.WriteString("# These version-gated exact-match rules report directly even when their trust level is unproven.\n")
	b, err := yaml.Marshal(map[string]any{"rules": out})
	die(err)
	buf.Write(b)
	die(os.WriteFile(matchKindPath, []byte(buf.String()), 0o644))
	fmt.Printf("classify: %d exact-api rules -> %s\n", len(out), matchKindPath)
}

func compute(args []string) {
	fs := flag.NewFlagSet("compute", flag.ExitOnError)
	label := fs.String("label", "after", "corpus results label")
	fixtures := fs.String("fixtures", "tools/corpus/results/fixtures-after/fixtures.json", "labelled linter-suite results")
	fs.Parse(args)
	all := load()
	var fx []fres
	if b, err := os.ReadFile(*fixtures); err == nil {
		die(json.Unmarshal(b, &fx))
	}
	lab := map[string]fres{}
	for _, f := range fx {
		lab[f.Rule] = f
	}
	// OWASP Benchmark per-rule outcomes (tools/corpus bench): flagged real vs flagged fake cases.
	var bl map[string]struct{ TP, FP, Other int }
	if b, err := os.ReadFile(filepath.Join("tools/corpus/results", *label, "bench-rules.json")); err == nil {
		die(json.Unmarshal(b, &bl))
	}
	for id, v := range bl {
		f := lab[id]
		f.Rule, f.TP, f.FP = id, f.TP+v.TP, f.FP+v.FP
		lab[id] = f
	}
	// Fix-commit differential (tools/corpus fixdiff): findings a security fix removed count as true
	// positives, findings that only appear in the fixed file as false positives.
	var fd map[string]struct{ Fixed, Introduced int }
	if b, err := os.ReadFile(filepath.Join("tools/corpus/results", *label, "fixdiff.json")); err == nil {
		die(json.Unmarshal(b, &fd))
	}
	// Only security rules: a fix commit also refactors, and style-rule churn says nothing about precision.
	sec := map[string]bool{}
	for _, r := range all {
		sec[r.ID] = r.Kind == "security" || strings.HasPrefix(r.ID, "TAINT-")
	}
	for id, v := range fd {
		if !sec[id] {
			delete(fd, id)
			continue
		}
		f := lab[id]
		f.Rule, f.TP, f.FP = id, f.TP+v.Fixed, f.FP+v.Introduced
		lab[id] = f
	}
	// Manually triaged corpus hits (tools/corpus/labels.yaml): tp/fp per rule.
	var lbl struct {
		Rules map[string][]struct {
			Repo, Path, Verdict, Note string
			Line                      int
		} `yaml:"rules"`
	}
	if b, err := os.ReadFile("tools/corpus/labels.yaml"); err == nil {
		die(yaml.Unmarshal(b, &lbl))
	}
	cs, nrepos := corpus(*label)
	// A label counts only while the current run still produces that hit: a false positive fixed
	// at its root (the rule no longer matches; the case is a regression example) stops counting
	// against the rule, and a true positive the rule lost stops counting for it.
	labelled, labelledTP, labelledFP := map[string]int{}, map[string]int{}, map[string]int{}
	stale := 0
	for id, hs := range lbl.Rules {
		f := lab[id]
		f.Rule = id
		for _, h := range hs {
			if !present[fmt.Sprintf("%s|%s|%s|%d", id, h.Repo, h.Path, h.Line)] {
				stale++
				continue
			}
			switch h.Verdict {
			case "tp":
				f.TP++
				labelledTP[id]++
			case "fp":
				f.FP++
				labelledFP[id]++
			default:
				continue
			}
			labelled[id]++
		}
		lab[id] = f
	}
	fmt.Printf("labels: %d no longer produced by the current run (fixed or lost), not counted\n", stale)
	taken := map[string]bool{}
	for id, hs := range lbl.Rules {
		for _, h := range hs {
			taken[fmt.Sprintf("%s|%s|%s|%d", id, h.Repo, h.Path, h.Line)] = true
		}
	}
	// Inline linter suppressions and real-linter agreement (tools/corpus suppressions / agree).
	ingestSpots := func(file, countKey string) {
		b, err := os.ReadFile(filepath.Join("tools/corpus/results", *label, file))
		if err != nil {
			return
		}
		var wrap struct {
			Rules map[string]struct {
				TP    int `json:"tp"`
				Both  int `json:"both"`
				Spots []struct {
					Repo, Path string
					Line       int
				} `json:"spots"`
			} `json:"rules"`
		}
		if json.Unmarshal(b, &wrap) != nil || wrap.Rules == nil {
			return
		}
		n := 0
		for id, v := range wrap.Rules {
			f := lab[id]
			f.Rule = id
			for _, h := range v.Spots {
				k := fmt.Sprintf("%s|%s|%s|%d", id, h.Repo, h.Path, h.Line)
				if taken[k] || !present[k] {
					continue
				}
				taken[k] = true
				f.TP++
				labelledTP[id]++
				labelled[id]++
				n++
			}
			lab[id] = f
		}
		fmt.Printf("%s: %d labelled TPs (deduped against labels.yaml and the other miners)\n", countKey, n)
	}
	ingestSpots("suppressions.json", "suppressions")
	ingestSpots("agree.json", "agree")
	// Lint autofix-commit differential: any rule (not only security). Style churn on an
	// explicit lint-fix commit is evidence, unlike mixed security-fix commits.
	var af map[string]struct{ Fixed, Introduced int }
	if b, err := os.ReadFile(filepath.Join("tools/corpus/results", *label, "autofix.json")); err == nil {
		die(json.Unmarshal(b, &af))
	}
	for id, v := range af {
		f := lab[id]
		f.Rule, f.TP, f.FP = id, f.TP+v.Fixed, f.FP+v.Introduced
		lab[id] = f
		if v.Fixed > 0 {
			labelledTP[id] += v.Fixed
			labelled[id] += v.Fixed
		}
	}
	meta := map[string]MetaResult{}
	if b, err := os.ReadFile(metaPath); err == nil {
		die(json.Unmarshal(b, &meta))
	} else {
		die(fmt.Errorf("run `go run ./tools/trust metamorphic` first: %w", err))
	}
	grandfathered := map[string]bool{}
	if b, err := os.ReadFile(silencePath); err == nil {
		for _, l := range strings.Split(string(b), "\n") {
			if l = strings.TrimSpace(l); l != "" && !strings.HasPrefix(l, "#") {
				grandfathered[l] = true
			}
		}
	}
	held, waived, sampledPromo := 0, 0, 0
	out := map[string]*rules.Trust{}
	for _, r := range all {
		t := &rules.Trust{}
		if f, ok := lab[r.ID]; ok {
			t.TP, t.FP, t.FN, t.TN = f.TP, f.FP, f.FN, f.TN
		}
		if c := cs[r.ID]; c != nil {
			t.CorpusHits, t.CorpusRepos = c.hits, c.repos
			if c.oss >= flagTotal {
				t.Anomalies = append(t.Anomalies, fmt.Sprintf("oss-total>=%d", flagTotal))
			}
			if c.maxPer >= flagPerRepo {
				t.Anomalies = append(t.Anomalies, fmt.Sprintf("repo>=%d", flagPerRepo))
			}
			if c.share >= flagShare {
				t.Anomalies = append(t.Anomalies, fmt.Sprintf("files>=%.0f%%", flagShare*100))
			}
		}
		m := meta[r.ID]
		t.Metamorphic, t.Unstable = m.Status, m.Failed
		if len(t.Unstable) > 3 {
			t.Unstable = t.Unstable[:3]
		}
		stable := m.Status != "unstable"
		labOK := t.Labelled() && t.Precision() >= rules.TrustGate
		// Volume anomalies (oss-total, per-repo, file share) say a pattern is common, not that it is
		// wrong. They stop blocking once a stratified sample of the corpus hits (min(OSS hits, 20),
		// tools/corpus/labels.yaml) has been reviewed with no false positive.
		anomalous := len(t.Anomalies) > 0
		sampled := false
		if c := cs[r.ID]; c != nil && c.oss > 0 && labelled[r.ID] >= min(c.oss, sampleWaive) && labelledFP[r.ID] == 0 && labOK && stable {
			sampled = true
		}
		if anomalous && sampled {
			anomalous = false
			waived++
			for i := range t.Anomalies {
				t.Anomalies[i] += " (waived: sampled review, 0 FP)"
			}
		}
		switch {
		case r.Shadow():
			t.Level, t.Why = rules.TrustQuarantined, "status: shadow"
		case t.TP >= rules.TrustProvenTP && t.Precision() >= rules.TrustProvenPrecision && stable && !anomalous:
			t.Level, t.Why = rules.TrustProven, "labelled external cases"
		case !stable:
			t.Level, t.Why = rules.TrustUnproven, "metamorphic variants change the result"
		case t.Labelled() && !labOK:
			t.Level, t.Why = rules.TrustUnproven, fmt.Sprintf("labelled precision %.2f < %.2f", t.Precision(), rules.TrustGate)
		case labOK && !anomalous:
			t.Level, t.Why = rules.TrustMeasured, "labelled external cases (below proven volume)"
		case t.CorpusHits > 0 && !anomalous && !grandfathered[r.ID]:
			// Guard: silence of the anomaly flags is not evidence of precision on its own. A rule
			// newly reaching this branch stays unproven (ai-confirm) until a sample of its corpus
			// hits is reviewed in tools/corpus/labels.yaml (it then takes the labelled branch).
			held++
			t.Level, t.Why = rules.TrustUnproven, "corpus hits below every anomaly threshold, awaiting a sampled hit review (tools/corpus/labels.yaml)"
		case t.CorpusHits > 0 && !anomalous:
			t.Level, t.Why = rules.TrustMeasured, "corpus hits below every anomaly threshold"
		case anomalous:
			t.Level, t.Why = rules.TrustUnproven, "corpus anomaly"
		default:
			t.Level, t.Why = rules.TrustUnproven, "own examples only"
		}
		// Promotion: declared ai-confirm (or policy-demoted) rules whose precision lower bound, with
		// every unlabelled OSS corpus hit counted as a false positive, reaches TrustPromoteLB.
		if v, ok := fd[r.ID]; ok {
			t.FixFixed, t.FixIntroduced = v.Fixed, v.Introduced
		}
		unl := bl[r.ID].Other
		if c := cs[r.ID]; c != nil {
			unl += max(0, c.oss-labelled[r.ID])
		}
		if n := t.TP + t.FP + unl; n > 0 {
			t.WilsonLB = math.Round(rules.WilsonLower(t.TP, n)*1000) / 1000
		}
		// Benchmark suites are synthetic: a pattern rule also needs real-code true positives (fix
		// commits, triaged corpus hits); a taint rule needs the source-to-sink flow by construction.
		realTP := t.FixFixed + labelledTP[r.ID]
		realOK := r.Detection.Engine == "taint" || realTP >= rules.TrustProvenTP
		if r.Detection.Mode == "ai-confirm" && r.Precision != "low" && !r.Shadow() && stable && !anomalous && realOK && t.WilsonLB >= rules.TrustPromoteLB {
			t.Promoted = true
			t.Level, t.Why = rules.TrustProven, fmt.Sprintf("labelled external cases: TP %d, FP %d, unlabelled hits (OSS, other benchmark category) %d", t.TP, t.FP, unl)
		}
		// A declared precision: low rule keeps its AI confirmation (rulecheck requires it) whatever the labels say.
		// A declared ai-confirm rule whose stratified corpus sample is all true positives (and that
		// has enough real-code TPs) reports directly; unsampled hits are not counted as FPs here.
		if !t.Promoted && r.Detection.Mode == "ai-confirm" && r.Precision != "low" && !r.Shadow() && sampled && realOK && t.Precision() >= rules.TrustProvenPrecision {
			t.Promoted = true
			sampledPromo++
			t.Level, t.Why = rules.TrustProven, fmt.Sprintf("sampled corpus review: %d of %d OSS hits labelled, 0 FP (TP %d)", labelled[r.ID], cs[r.ID].oss, t.TP)
		}
		out[r.ID] = t
	}
	var buf strings.Builder
	buf.WriteString("# Rule trust levels, generated by `go run ./tools/trust compute` from tools/corpus results\n")
	buf.WriteString("# (labelled linter suites, corpus anomaly flags) and tools/trust/metamorphic.json.\n")
	buf.WriteString("# Applied at load time by internal/rules.ApplyTrust: unproven deterministic rules run as ai-confirm.\n")
	b, err := yaml.Marshal(map[string]any{"rules": out})
	die(err)
	buf.Write(b)
	die(os.WriteFile(trustPath, []byte(buf.String()), 0o644))

	// report: distribution per pack, before (declared mode) and the effect of the policy
	type row struct{ proven, measured, unproven, quarantined, det, demoted, exact, exactDirect int }
	per := map[string]*row{}
	tot := &row{}
	for _, r := range all {
		p := per[r.Pack]
		if p == nil {
			p = &row{}
			per[r.Pack] = p
		}
		for _, x := range []*row{p, tot} {
			switch out[r.ID].Level {
			case rules.TrustProven:
				x.proven++
			case rules.TrustMeasured:
				x.measured++
			case rules.TrustUnproven:
				x.unproven++
				if r.Detection.Mode == "deterministic" {
					if r.MatchKind == rules.MatchKindExactAPI {
						x.exactDirect++
					} else {
						x.demoted++
					}
				}
			case rules.TrustQuarantined:
				x.quarantined++
			}
			if r.Detection.Mode == "deterministic" {
				x.det++
			}
			if r.MatchKind == rules.MatchKindExactAPI {
				x.exact++
			}
		}
	}
	var md strings.Builder
	fmt.Fprintf(&md, "# Rule trust distribution\n\nGenerated by `go run ./tools/trust compute -label %s` (corpus: %d repos; labelled linter suites: %d rules; OWASP Benchmark per-rule outcomes: %d rules).\n\n", *label, nrepos, len(fx), len(bl))
	md.WriteString("Policy: unproven deterministic rules run as ai-confirm, except `match_kind: exact-api` rules (version-gated deprecation/removal/migration rules detected by an exact identifier/import/config-key/dependency match; classifier internal/rules/matchkind.go, list rules/data/matchkind.yaml), which report directly. The full exact-api list is at the end of this file.\n\n")
	md.WriteString("| pack | rules | proven | measured | unproven | quarantined | deterministic (declared) | demoted to ai-confirm | exact-api | exact-api unproven, reporting directly |\n|---|---|---|---|---|---|---|---|---|---|\n")
	keys := slices.Sorted(maps.Keys(per))
	slices.Sort(keys)
	for _, k := range append(keys, "TOTAL") {
		x := per[k]
		if k == "TOTAL" {
			x = tot
		}
		fmt.Fprintf(&md, "| %s | %d | %d | %d | %d | %d | %d | %d | %d | %d |\n", k, x.proven+x.measured+x.unproven+x.quarantined, x.proven, x.measured, x.unproven, x.quarantined, x.det, x.demoted, x.exact, x.exactDirect)
	}
	md.WriteString("\n## exact-api rules (audit list)\n\n| rule | pack | kind | applies_to | engine | trust | classifier reason |\n|---|---|---|---|---|---|---|\n")
	ex := []*rules.Rule{}
	for _, r := range all {
		if r.MatchKind == rules.MatchKindExactAPI {
			ex = append(ex, r)
		}
	}
	slices.SortFunc(ex, func(a, b *rules.Rule) int { return strings.Compare(a.Pack+a.ID, b.Pack+b.ID) })
	for _, r := range ex {
		_, why := rules.ExactAPI(r)
		at := []string{}
		for _, k := range slices.Sorted(maps.Keys(r.AppliesTo)) {
			at = append(at, k+" "+r.AppliesTo[k])
		}
		fmt.Fprintf(&md, "| %s | %s | %s | %s | %s | %s | %s |\n", r.ID, r.Pack, r.Kind, strings.ReplaceAll(strings.Join(at, ", "), "|", "\\|"), r.Detection.Engine, out[r.ID].Level, why)
	}
	// Promotions: ai-confirm rules that now report directly, and the closest candidates.
	var prom, near []string
	for _, r := range all {
		t := out[r.ID]
		if r.Detection.Mode != "ai-confirm" || r.Shadow() || t.WilsonLB == 0 {
			continue
		}
		why := "promoted"
		switch {
		case t.Promoted:
		case t.WilsonLB < rules.TrustPromoteLB:
			why = fmt.Sprintf("LB < %.2f", rules.TrustPromoteLB)
		case r.Detection.Engine != "taint" && t.FixFixed+labelledTP[r.ID] < rules.TrustProvenTP:
			why = "benchmark-only evidence: needs >= 5 real-code TP"
		default:
			why = "metamorphic/anomaly"
		}
		line := fmt.Sprintf("| %s | %s | %d | %d | %d/%d | %.3f | %s | %s |", r.ID, r.Pack, t.TP, t.FP, t.FixFixed, t.FixIntroduced, t.WilsonLB, t.Metamorphic, why)
		if t.Promoted {
			prom = append(prom, line)
		} else if t.WilsonLB >= 0.80 || t.WilsonLB >= 0.5 && t.FixFixed > 0 {
			near = append(near, line)
		}
	}
	slices.Sort(prom)
	slices.Sort(near)
	hdr := "| rule | pack | TP | FP (labelled; unlabelled hits also count in the LB) | fix-commit fixed/introduced | Wilson LB | metamorphic | status |\n|---|---|---|---|---|---|---|---|\n"
	fmt.Fprintf(&md, "\n## Promotions (ai-confirm -> deterministic, Wilson LB >= %.2f)\n\n%s%s\n", rules.TrustPromoteLB, hdr, strings.Join(prom, "\n"))
	fmt.Fprintf(&md, "\n\n## Not yet promoted (Wilson LB 0.80-%.2f): more labelled cases needed\n\n%s%s\n", rules.TrustPromoteLB, hdr, strings.Join(near, "\n"))
	die(os.WriteFile(report, []byte(md.String()), 0o644))
	fmt.Printf("promoted: %d\n", len(prom))
	fmt.Printf("guard: %d rules with corpus-silence-only evidence held unproven pending sampled review\n", held)
	fmt.Printf("waiver: %d rules with volume anomalies cleared by a sampled review (0 FP); %d ai-confirm rules promoted on a sampled review\n", waived, sampledPromo)
	fmt.Printf("trust: proven=%d measured=%d unproven=%d quarantined=%d (deterministic demoted: %d; exact-api %d, of which unproven reporting directly %d) -> %s, %s\n",
		tot.proven, tot.measured, tot.unproven, tot.quarantined, tot.demoted, tot.exact, tot.exactDirect, trustPath, report)
}

// sampleWaive: labelled corpus hits that lift a volume anomaly on an exact-match rule.
const sampleWaive = 20

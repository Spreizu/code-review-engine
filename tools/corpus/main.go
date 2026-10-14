// Command corpus is crev's false-positive harness. It scans pinned real-world repositories and
// labelled benchmark suites with a given crev binary and reports per-rule hit volume, so rules
// that fire suspiciously often can be sample-triaged and fixed (or quarantined) before users see
// them. Nothing here is embedded in the crev binary; clones live in tools/corpus/cache/
// (gitignored). Workflow: tools/corpus/README.md.
//
//	go run ./tools/corpus fetch                      # clone/checkout pinned commits
//	go run ./tools/corpus run -label after -crev BIN  # scan every repo -> results/after/
//	go run ./tools/corpus summarize -label after      # results/after/report.md (+ flags)
//	go run ./tools/corpus diff before after           # per-pack and per-rule deltas
//	go run ./tools/corpus sample -label after -rule ID -n 10   # findings to triage
//	go run ./tools/corpus suppressions -label after  # inline linter disables as labelled TPs
//	go run ./tools/corpus autofix -label after -crev BIN  # lint autofix-commit differential
//	go run ./tools/corpus agree -label after         # real linters vs crev on the same files
package main

import (
	"cmp"
	"encoding/json"
	"flag"
	"fmt"
	"maps"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strings"
	"sync"
	"time"

	"gopkg.in/yaml.v3"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/rules"
)

const dir = "tools/corpus"

type Repo struct {
	Name    string   `yaml:"name"`
	URL     string   `yaml:"url"`
	Commit  string   `yaml:"commit"`
	Covers  []string `yaml:"covers"`
	Path    string   `yaml:"path"`   // cache subdir (default: name)
	Subdir  string   `yaml:"subdir"` // scan only this subdirectory
	Kind    string   `yaml:"kind"`   // oss (default) | bench (labelled/vulnerable apps) | fixtures (linter test suites)
	Sparse  []string `yaml:"sparse"` // sparse-checkout paths (cone mode off), when only part of the repo is needed
	License string   `yaml:"license"`
}

type Corpus struct {
	Repos []Repo `yaml:"repos"`
}

func load() Corpus {
	var c Corpus
	b, err := os.ReadFile(filepath.Join(dir, "corpus.yaml"))
	die(err)
	die(yaml.Unmarshal(b, &c))
	for i := range c.Repos {
		if c.Repos[i].Path == "" {
			c.Repos[i].Path = c.Repos[i].Name
		}
		if c.Repos[i].Kind == "" {
			c.Repos[i].Kind = "oss"
		}
	}
	return c
}

func die(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, "corpus:", err)
		os.Exit(1)
	}
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: corpus fetch|run|summarize|diff|sample|fixtures|bench|fixdiff|suppressions|autofix|agree [flags]")
		os.Exit(2)
	}
	switch os.Args[1] {
	case "fetch":
		fetch(os.Args[2:])
	case "run":
		run(os.Args[2:])
	case "summarize":
		summarize(os.Args[2:])
	case "diff":
		diff(os.Args[2:])
	case "sample":
		sample(os.Args[2:])
	case "fixtures":
		fixtures(os.Args[2:])
	case "govern":
		govern(os.Args[2:])
	case "bench":
		cmdBench(os.Args[2:])
	case "fixdiff":
		fixdiff(os.Args[2:])
	case "slow":
		slow(os.Args[2:])
	case "suppressions":
		suppressions(os.Args[2:])
	case "autofix":
		autofix(os.Args[2:])
	case "agree":
		agree(os.Args[2:])
	default:
		die(fmt.Errorf("unknown command %q", os.Args[1]))
	}
}

func cacheDir(r Repo) string { return filepath.Join(dir, "cache", r.Path) }

// fetch clones each repo at its pinned commit (shallow) unless the checkout already matches.
func fetch(args []string) {
	fs := flag.NewFlagSet("fetch", flag.ExitOnError)
	only := fs.String("repos", "", "comma-separated repo names (default all)")
	prune := fs.Bool("prune", true, "delete files crev never scans (media, archives, fonts, files over 1 MB) and git gc the clone")
	fs.Parse(args)
	for _, r := range selected(load(), *only, "") {
		d := cacheDir(r)
		if out, err := exec.Command("git", "-C", d, "rev-parse", "HEAD").Output(); err == nil && strings.TrimSpace(string(out)) == r.Commit {
			fmt.Println("ok      ", r.Name)
			continue
		}
		fmt.Println("fetch   ", r.Name, r.Commit[:12])
		os.MkdirAll(d, 0o755)
		steps := [][]string{{"init", "-q"}, {"remote", "add", "origin", r.URL}}
		if len(r.Sparse) > 0 {
			steps = append(steps, append([]string{"sparse-checkout", "set", "--no-cone"}, r.Sparse...))
		}
		steps = append(steps, []string{"fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", r.Commit}, []string{"checkout", "-q", "FETCH_HEAD"})
		for _, c := range steps {
			cmd := exec.Command("git", append([]string{"-C", d}, c...)...)
			if out, err := cmd.CombinedOutput(); err != nil && c[0] != "remote" {
				die(fmt.Errorf("%s: git %s: %v\n%s", r.Name, c[0], err, out))
			}
		}
		if *prune {
			n, b := pruneClone(d)
			fmt.Printf("pruned   %s: %d files, %.1f MB\n", r.Name, n, float64(b)/1e6)
		}
	}
}

var pruneExt = map[string]bool{".png": true, ".jpg": true, ".jpeg": true, ".gif": true, ".webp": true, ".ico": true, ".bmp": true,
	".mp4": true, ".mov": true, ".webm": true, ".mp3": true, ".wav": true, ".ogg": true, ".pdf": true, ".zip": true, ".gz": true,
	".tgz": true, ".xz": true, ".bz2": true, ".7z": true, ".jar": true, ".war": true, ".woff": true, ".woff2": true, ".ttf": true,
	".otf": true, ".eot": true, ".psd": true, ".so": true, ".dylib": true, ".dll": true, ".exe": true, ".bin": true, ".wasm": true}

// pruneClone deletes worktree files crev never reads (binary media/archives and anything over
// 1 MB, the default -max-file-kb) and compacts the object store; HEAD stays at the pin,
// so `fetch` still sees the clone as current. Deleted files show as removed in `git status`,
// which does not affect a full scan.
func pruneClone(d string) (int, int64) {
	n, b := 0, int64(0)
	filepath.WalkDir(d, func(p string, e os.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if e.IsDir() {
			if e.Name() == ".git" {
				return filepath.SkipDir
			}
			return nil
		}
		info, err := e.Info()
		if err != nil || !info.Mode().IsRegular() {
			return nil
		}
		if pruneExt[strings.ToLower(filepath.Ext(p))] || info.Size() > 1<<20 {
			if os.Remove(p) == nil {
				n++
				b += info.Size()
			}
		}
		return nil
	})
	exec.Command("git", "-C", d, "gc", "-q", "--prune=now").Run()
	return n, b
}

func selected(c Corpus, only, kind string) []Repo {
	var out []Repo
	want := map[string]bool{}
	for _, n := range strings.Split(only, ",") {
		if n != "" {
			want[n] = true
		}
	}
	for _, r := range c.Repos {
		if (len(want) == 0 || want[r.Name]) && (kind == "" || r.Kind == kind) {
			out = append(out, r)
		}
	}
	return out
}

// Hit is the compact per-finding record kept in results (the raw report stays in raw/).
type Hit struct {
	Rule         string                 `json:"rule"`
	Pack         string                 `json:"pack"`
	Status       string                 `json:"status"`
	Severity     string                 `json:"severity"`
	Path         string                 `json:"path"`
	Line         int                    `json:"line"`
	Snippet      string                 `json:"snippet,omitempty"`
	SuppressedBy *findings.SuppressedBy `json:"suppressed_by,omitempty"`
}

type RepoResult struct {
	Repo    string         `json:"repo"`
	Commit  string         `json:"commit"`
	Kind    string         `json:"kind"`
	Files   int            `json:"files"`
	Millis  int64          `json:"ms"`
	Error   string         `json:"error,omitempty"`
	Hits    []Hit          `json:"hits"`
	Shadow  map[string]int `json:"shadow,omitempty"`
	Unconf  int            `json:"rules_unconfigured,omitempty"`
	CrevBin string         `json:"crev"`
}

func packOf() map[string]string {
	rs, err := rules.LoadFiles("rules/packs/*/*.yaml")
	die(err)
	m := map[string]string{}
	for _, r := range rs {
		m[r.ID] = r.Pack
	}
	return m
}

// run scans each repo with the given crev binary (AI off, everything kept: shadow included when
// the binary supports it) and writes results/<label>/<repo>.json plus raw/<repo>.json.
func run(args []string) {
	fs := flag.NewFlagSet("run", flag.ExitOnError)
	label := fs.String("label", "", "result label (e.g. before, after)")
	bin := fs.String("crev", "", "crev binary to run")
	packs := fs.String("packs", "", "packs (default: every pack in rules/packs)")
	only := fs.String("repos", "", "comma-separated repo names")
	kind := fs.String("kind", "", "oss|bench (default both; fixtures are evaluated by `fixtures`, not scanned)")
	jobs := fs.Int("j", 4, "parallel scans")
	fs.Parse(args)
	if *label == "" || *bin == "" {
		die(fmt.Errorf("run needs -label and -crev"))
	}
	if *packs == "" {
		*packs = allPacks()
	}
	abs, _ := filepath.Abs(*bin)
	help, _ := exec.Command(abs, "scan", "--help").CombinedOutput()
	shadowFlag := strings.Contains(string(help), "--include-shadow")
	out := filepath.Join(dir, "results", *label)
	os.MkdirAll(filepath.Join(out, "raw"), 0o755)
	pack := packOf()
	var wg sync.WaitGroup
	sem := make(chan struct{}, *jobs)
	for _, r := range selected(load(), *only, *kind) {
		if r.Kind == "fixtures" {
			continue
		}
		wg.Add(1)
		go func(r Repo) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			res := scanRepo(abs, r, *packs, shadowFlag, filepath.Join(out, "raw", r.Name+".json"), pack)
			b, _ := json.MarshalIndent(res, "", " ")
			die(os.WriteFile(filepath.Join(out, r.Name+".json"), b, 0o644))
			fmt.Printf("%-22s %5d findings %6d ms %s\n", r.Name, len(res.Hits), res.Millis, res.Error)
		}(r)
	}
	wg.Wait()
}

func allPacks() string {
	rs, err := rules.LoadFiles("rules/packs/*/*.yaml")
	die(err)
	set := map[string]bool{}
	for _, r := range rs {
		set[r.Pack] = true
	}
	return strings.Join(slices.Sorted(maps.Keys(set)), ",")
}

func scanRepo(bin string, r Repo, packs string, shadow bool, rawPath string, pack map[string]string) RepoResult {
	root := cacheDir(r)
	if r.Subdir != "" {
		root = filepath.Join(root, r.Subdir)
	}
	res := RepoResult{Repo: r.Name, Commit: r.Commit, Kind: r.Kind, CrevBin: bin}
	args := []string{"scan", "--packs", packs, "--ai", "off", "--vulndb", "off", "--no-run", "--quiet", "--fail-on", "none", "--format", "json", "."}
	if shadow {
		args = append(args[:len(args)-1], "--include-shadow", ".")
	}
	cmd := exec.Command(bin, args...)
	cmd.Dir = root
	t0 := time.Now()
	b, err := cmd.Output()
	res.Millis = time.Since(t0).Milliseconds()
	if err != nil && len(b) == 0 {
		res.Error = err.Error()
		return res
	}
	os.WriteFile(rawPath, b, 0o644)
	var rep struct {
		Findings []struct {
			RuleID       string                 `json:"rule_id"`
			Status       string                 `json:"status"`
			Severity     string                 `json:"severity"`
			Snippet      string                 `json:"snippet"`
			SuppressedBy *findings.SuppressedBy `json:"suppressed_by"`
			Location     struct {
				Path string `json:"path"`
				Line int    `json:"start_line"`
			} `json:"location"`
		} `json:"findings"`
		Stats  map[string]int `json:"stats"`
		Shadow map[string]int `json:"shadow"`
	}
	if err := json.Unmarshal(b, &rep); err != nil {
		res.Error = "bad JSON: " + err.Error()
		return res
	}
	res.Files, res.Shadow, res.Unconf = rep.Stats["files"], rep.Shadow, rep.Stats["rules_unconfigured"]
	for _, f := range rep.Findings {
		sn := f.Snippet
		if len(sn) > 160 {
			sn = sn[:160]
		}
		res.Hits = append(res.Hits, Hit{Rule: f.RuleID, Pack: cmp.Or(pack[f.RuleID], "?"), Status: f.Status, Severity: f.Severity,
			Path: f.Location.Path, Line: f.Location.Line, Snippet: sn, SuppressedBy: f.SuppressedBy})
	}
	return res
}

func loadResults(label string) []RepoResult {
	files, _ := filepath.Glob(filepath.Join(dir, "results", label, "*.json"))
	if len(files) == 0 {
		die(fmt.Errorf("no results for label %q", label))
	}
	var out []RepoResult
	for _, f := range files {
		var r RepoResult
		b, err := os.ReadFile(f)
		die(err)
		if json.Unmarshal(b, &r) != nil || r.Repo == "" {
			continue // suppressions.json, fixdiff.json, agree.json, ...
		}
		out = append(out, r)
	}
	return out
}

// reported: what a user would see in the review list with AI off (deterministic, confirmed).
// pending_ai findings are counted separately: they reach users only after AI confirmation.
func reported(h Hit) bool { return h.Status == "confirmed" }

type ruleStat struct {
	Rule, Pack            string
	Reported, Pending     int
	Shadow, Repos, MaxPer int
	Files                 map[string]bool
	FileShare             float64 // max over repos: files hit / files scanned
	Flags                 []string
}

// Volume thresholds for "suspicious": a rule that fires this often on mature, well-reviewed
// code is more likely imprecise than right. Flagged rules get sample-triaged.
const (
	flagTotal   = 15
	flagPerRepo = 10
	flagShare   = 0.25
)

func stats(rs []RepoResult, kind string) map[string]*ruleStat {
	st := map[string]*ruleStat{}
	for _, r := range rs {
		if kind != "" && r.Kind != kind {
			continue
		}
		per := map[string]int{}
		files := map[string]map[string]bool{}
		for _, h := range r.Hits {
			s := st[h.Rule]
			if s == nil {
				s = &ruleStat{Rule: h.Rule, Pack: h.Pack, Files: map[string]bool{}}
				st[h.Rule] = s
			}
			switch {
			case reported(h):
				s.Reported++
				per[h.Rule]++
				if files[h.Rule] == nil {
					files[h.Rule] = map[string]bool{}
				}
				files[h.Rule][h.Path] = true
				s.Files[r.Repo+"/"+h.Path] = true
			case h.Status == "pending_ai":
				s.Pending++
			case h.Status == "shadow":
				s.Shadow++
			}
		}
		for id, n := range r.Shadow {
			if st[id] == nil {
				st[id] = &ruleStat{Rule: id, Files: map[string]bool{}}
			}
			if st[id].Shadow == 0 {
				st[id].Shadow += n
			}
		}
		for id, n := range per {
			st[id].Repos++
			st[id].MaxPer = max(st[id].MaxPer, n)
			if r.Files > 20 {
				st[id].FileShare = max(st[id].FileShare, float64(len(files[id]))/float64(r.Files))
			}
		}
	}
	for _, s := range st {
		if s.Reported >= flagTotal {
			s.Flags = append(s.Flags, fmt.Sprintf("total>=%d", flagTotal))
		}
		if s.MaxPer >= flagPerRepo {
			s.Flags = append(s.Flags, fmt.Sprintf("repo>=%d", flagPerRepo))
		}
		if s.FileShare >= flagShare {
			s.Flags = append(s.Flags, fmt.Sprintf("files>=%.0f%%", flagShare*100))
		}
	}
	return st
}

func sortedStats(st map[string]*ruleStat) []*ruleStat {
	out := slices.Collect(maps.Values(st))
	slices.SortFunc(out, func(a, b *ruleStat) int {
		return cmp.Or(b.Reported-a.Reported, b.Pending-a.Pending, strings.Compare(a.Rule, b.Rule))
	})
	return out
}

func packTotals(rs []RepoResult, kind string) map[string][3]int {
	m := map[string][3]int{}
	for _, r := range rs {
		if kind != "" && r.Kind != kind {
			continue
		}
		for _, h := range r.Hits {
			t := m[h.Pack]
			switch {
			case reported(h):
				t[0]++
			case h.Status == "pending_ai":
				t[1]++
			case h.Status == "shadow":
				t[2]++
			}
			m[h.Pack] = t
		}
	}
	return m
}

func summarize(args []string) {
	fs := flag.NewFlagSet("summarize", flag.ExitOnError)
	label := fs.String("label", "", "result label")
	kind := fs.String("kind", "oss", "oss|bench|'' (all)")
	fs.Parse(args)
	rs := loadResults(*label)
	var b strings.Builder
	fmt.Fprintf(&b, "# Corpus run %q (%s)\n\n", *label, *kind)
	fmt.Fprintf(&b, "Reported = confirmed (review list with AI off); pending = ai-confirm candidates (shown only after high-confidence AI confirmation); shadow = quarantined rules.\n\n")
	fmt.Fprintf(&b, "| repo | files | reported | pending | ms | error |\n|---|---|---|---|---|---|\n")
	for _, r := range rs {
		if *kind != "" && r.Kind != *kind {
			continue
		}
		n, p := 0, 0
		for _, h := range r.Hits {
			if reported(h) {
				n++
			} else if h.Status == "pending_ai" {
				p++
			}
		}
		fmt.Fprintf(&b, "| %s | %d | %d | %d | %d | %s |\n", r.Repo, r.Files, n, p, r.Millis, r.Error)
	}
	pt := packTotals(rs, *kind)
	fmt.Fprintf(&b, "\n## Per pack\n\n| pack | reported | pending | shadow |\n|---|---|---|---|\n")
	for _, p := range slices.Sorted(maps.Keys(pt)) {
		fmt.Fprintf(&b, "| %s | %d | %d | %d |\n", p, pt[p][0], pt[p][1], pt[p][2])
	}
	st := sortedStats(stats(rs, *kind))
	fmt.Fprintf(&b, "\n## Per rule (flagged first)\n\nFlags: total >= %d, >= %d in one repo, or >= %.0f%% of a repo's files.\n\n| rule | reported | repos | max/repo | file share | pending | shadow | flags |\n|---|---|---|---|---|---|---|---|\n", flagTotal, flagPerRepo, flagShare*100)
	slices.SortStableFunc(st, func(a, b *ruleStat) int { return len(b.Flags) - len(a.Flags) })
	for _, s := range st {
		fmt.Fprintf(&b, "| %s | %d | %d | %d | %.1f%% | %d | %d | %s |\n", s.Rule, s.Reported, s.Repos, s.MaxPer, s.FileShare*100, s.Pending, s.Shadow, strings.Join(s.Flags, " "))
	}
	p := filepath.Join(dir, "results", *label, "report.md")
	die(os.WriteFile(p, []byte(b.String()), 0o644))
	fmt.Println(p)
}

func diff(args []string) {
	fs := flag.NewFlagSet("diff", flag.ExitOnError)
	kind := fs.String("kind", "oss", "oss|bench|'' (all)")
	fs.Parse(args)
	if fs.NArg() != 2 {
		die(fmt.Errorf("diff A B"))
	}
	a, b := loadResults(fs.Arg(0)), loadResults(fs.Arg(1))
	pa, pb := packTotals(a, *kind), packTotals(b, *kind)
	keys := map[string]bool{}
	for k := range pa {
		keys[k] = true
	}
	for k := range pb {
		keys[k] = true
	}
	fmt.Printf("| pack | reported %s | reported %s | pending %s | pending %s | shadow %s |\n|---|---|---|---|---|---|\n", fs.Arg(0), fs.Arg(1), fs.Arg(0), fs.Arg(1), fs.Arg(1))
	var ta, tb, qa, qb, sb int
	for _, k := range slices.Sorted(maps.Keys(keys)) {
		fmt.Printf("| %s | %d | %d | %d | %d | %d |\n", k, pa[k][0], pb[k][0], pa[k][1], pb[k][1], pb[k][2])
		ta, tb, qa, qb, sb = ta+pa[k][0], tb+pb[k][0], qa+pa[k][1], qb+pb[k][1], sb+pb[k][2]
	}
	fmt.Printf("| **total** | %d | %d | %d | %d | %d |\n\n", ta, tb, qa, qb, sb)
	sa, sbb := stats(a, *kind), stats(b, *kind)
	fmt.Println("| rule | reported before | reported after |\n|---|---|---|")
	ids := map[string]bool{}
	for k := range sa {
		ids[k] = true
	}
	for k := range sbb {
		ids[k] = true
	}
	var rows [][3]string
	for id := range ids {
		x, y := 0, 0
		if s := sa[id]; s != nil {
			x = s.Reported
		}
		if s := sbb[id]; s != nil {
			y = s.Reported
		}
		if x != y {
			rows = append(rows, [3]string{id, fmt.Sprint(x), fmt.Sprint(y)})
		}
	}
	slices.SortFunc(rows, func(p, q [3]string) int { return strings.Compare(p[0], q[0]) })
	for _, r := range rows {
		fmt.Printf("| %s | %s | %s |\n", r[0], r[1], r[2])
	}
}

// sample prints findings of one rule spread across repos/files for manual triage.
func sample(args []string) {
	fs := flag.NewFlagSet("sample", flag.ExitOnError)
	label := fs.String("label", "", "result label")
	rule := fs.String("rule", "", "rule id")
	n := fs.Int("n", 10, "max samples")
	ctx := fs.Int("C", 2, "context lines")
	status := fs.String("status", "", "only this status (default all)")
	fs.Parse(args)
	c := load()
	paths := map[string]string{}
	for _, r := range c.Repos {
		paths[r.Name] = filepath.Join(cacheDir(r), r.Subdir)
	}
	var hits []struct {
		repo string
		h    Hit
	}
	for _, r := range loadResults(*label) {
		for _, h := range r.Hits {
			if h.Rule == *rule && (*status == "" || h.Status == *status) {
				hits = append(hits, struct {
					repo string
					h    Hit
				}{r.Repo, h})
			}
		}
	}
	// round-robin over repos so one noisy repo does not fill the sample
	byRepo := map[string][]int{}
	for i, x := range hits {
		byRepo[x.repo] = append(byRepo[x.repo], i)
	}
	var pick []int
	for len(pick) < *n {
		added := false
		for _, repo := range slices.Sorted(maps.Keys(byRepo)) {
			if l := byRepo[repo]; len(l) > 0 && len(pick) < *n {
				pick, byRepo[repo], added = append(pick, l[0]), l[1:], true
			}
		}
		if !added {
			break
		}
	}
	fmt.Printf("%s: %d hits, showing %d\n", *rule, len(hits), len(pick))
	for _, i := range pick {
		x := hits[i]
		fmt.Printf("\n--- %s/%s:%d [%s]\n", x.repo, x.h.Path, x.h.Line, x.h.Status)
		b, err := os.ReadFile(filepath.Join(paths[x.repo], x.h.Path))
		if err != nil {
			continue
		}
		lines := strings.Split(string(b), "\n")
		for l := max(1, x.h.Line-*ctx); l <= min(len(lines), x.h.Line+*ctx); l++ {
			mark := "  "
			if l == x.h.Line {
				mark = "> "
			}
			s := lines[l-1]
			if len(s) > 200 {
				s = s[:200] + "…"
			}
			fmt.Printf("%s%5d %s\n", mark, l, s)
		}
	}
}

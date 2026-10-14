package main

// fixdiff: fix-commit differential. For every security-fix commit in tools/corpus/fixcommits.json
// (public GitHub commits whose message says they fix a vulnerability), the files the commit modified
// are fetched at the parent and at the fix and scanned with crev (all packs, hidden findings kept).
// A finding that disappears in the fixed version is evidence the rule flags what maintainers treat
// as a vulnerability (fixed); a finding that appears only in the fixed version is counted against the
// rule (introduced). Results feed tools/trust compute as labelled cases.
// API responses and file bodies are cached under tools/corpus/cache/fixdiff (gitignored).

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strings"
	"time"
)

type fixCommit struct {
	Repo    string `json:"repo"`
	SHA     string `json:"sha"`
	Bucket  string `json:"bucket"`
	Message string `json:"message"`
}

type FixStat struct {
	Fixed      int      `json:"fixed"`
	Introduced int      `json:"introduced"`
	Commits    []string `json:"commits,omitempty"`
}

var fixExt = map[string]bool{".py": true, ".js": true, ".mjs": true, ".cjs": true, ".ts": true, ".tsx": true, ".jsx": true, ".java": true,
	".kt": true, ".go": true, ".php": true, ".tf": true, ".yml": true, ".yaml": true, ".vue": true}

func ghGet(url, cache string) ([]byte, error) {
	if b, err := os.ReadFile(cache); err == nil {
		return b, nil
	}
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "crev-corpus-fixdiff")
	req.Header.Set("Accept", "application/vnd.github+json")
	if t := os.Getenv("GITHUB_TOKEN"); t != "" && strings.Contains(url, "api.github.com") {
		req.Header.Set("Authorization", "Bearer "+t)
	}
	resp, err := (&http.Client{
		Timeout: 60 * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			if len(via) >= 10 {
				return fmt.Errorf("too many redirects")
			}
			if t := os.Getenv("GITHUB_TOKEN"); t != "" && strings.Contains(req.URL.Host, "api.github.com") {
				req.Header.Set("Authorization", "Bearer "+t)
			}
			return nil
		},
	}).Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(io.LimitReader(resp.Body, 4<<20))
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("%s: HTTP %d", url, resp.StatusCode)
	}
	_ = os.MkdirAll(filepath.Dir(cache), 0o755)
	_ = os.WriteFile(cache, b, 0o644)
	return b, nil
}

func scanDir(bin, d string) map[string]int {
	out, _ := exec.Command(bin, "scan", d, "--format", "json", "--show-hidden", "--ai", "off").Output()
	var r struct {
		Findings []struct {
			RuleID   string `json:"rule_id"`
			Location struct {
				Path string `json:"path"`
			} `json:"location"`
		} `json:"findings"`
	}
	_ = json.Unmarshal(out, &r)
	m := map[string]int{}
	for _, f := range r.Findings {
		m[f.RuleID+"\x00"+f.Location.Path]++
	}
	return m
}

func fixdiff(args []string) {
	fs := flag.NewFlagSet("fixdiff", flag.ExitOnError)
	bin := fs.String("crev", "", "crev binary")
	label := fs.String("label", "after", "results label (writes results/<label>/fixdiff.json)")
	fs.Parse(args)
	if *bin == "" {
		die(fmt.Errorf("-crev is required"))
	}
	var list []fixCommit
	b, err := os.ReadFile(filepath.Join(dir, "fixcommits.json"))
	die(err)
	die(json.Unmarshal(b, &list))
	stats := map[string]*FixStat{}
	used, skipped := 0, 0
	var report strings.Builder
	for _, c := range list {
		cdir := filepath.Join(dir, "cache", "fixdiff", c.SHA)
		meta, err := ghGet("https://api.github.com/repos/"+c.Repo+"/commits/"+c.SHA, filepath.Join(cdir, "commit.json"))
		if err != nil {
			fmt.Fprintln(os.Stderr, "skip", c.Repo, c.SHA[:10], err)
			skipped++
			continue
		}
		var cm struct {
			Parents []struct{ SHA string } `json:"parents"`
			Files   []struct {
				Filename, Status string
				Changes          int
			} `json:"files"`
		}
		die(json.Unmarshal(meta, &cm))
		if len(cm.Parents) != 1 {
			skipped++
			continue
		}
		parent := cm.Parents[0].SHA
		tmp, err := os.MkdirTemp("", "crev-fixdiff-")
		die(err)
		n := 0
		for _, f := range cm.Files {
			ext := strings.ToLower(filepath.Ext(f.Filename))
			if f.Status != "modified" || !fixExt[ext] || n >= 15 || strings.Contains(f.Filename, "..") {
				continue
			}
			ok := true
			for side, ref := range map[string]string{"before": parent, "after": c.SHA} {
				body, err := ghGet("https://raw.githubusercontent.com/"+c.Repo+"/"+ref+"/"+f.Filename, filepath.Join(cdir, side, f.Filename))
				if err != nil {
					ok = false
					break
				}
				p := filepath.Join(tmp, side, f.Filename)
				_ = os.MkdirAll(filepath.Dir(p), 0o755)
				_ = os.WriteFile(p, body, 0o644)
			}
			if ok {
				n++
			}
		}
		if n == 0 {
			os.RemoveAll(tmp)
			skipped++
			continue
		}
		used++
		before, after := scanDir(*bin, filepath.Join(tmp, "before")), scanDir(*bin, filepath.Join(tmp, "after"))
		os.RemoveAll(tmp)
		keys := map[string]bool{}
		for k := range before {
			keys[k] = true
		}
		for k := range after {
			keys[k] = true
		}
		var gone, came []string
		for k := range keys {
			rule := strings.SplitN(k, "\x00", 2)[0]
			d := before[k] - after[k]
			if d == 0 {
				continue
			}
			s := stats[rule]
			if s == nil {
				s = &FixStat{}
				stats[rule] = s
			}
			ref := c.Repo + "@" + c.SHA[:10]
			if d > 0 {
				s.Fixed += d
				gone = append(gone, rule)
			} else {
				s.Introduced -= d
				came = append(came, rule)
			}
			if !slices.Contains(s.Commits, ref) {
				s.Commits = append(s.Commits, ref)
			}
		}
		slices.Sort(gone)
		slices.Sort(came)
		fmt.Fprintf(&report, "| %s@%s | %s | %d | %s | %s |\n", c.Repo, c.SHA[:10], c.Bucket, n, strings.Join(slices.Compact(gone), " "), strings.Join(slices.Compact(came), " "))
	}
	out := filepath.Join(dir, "results", *label)
	die(os.MkdirAll(out, 0o755))
	j, _ := json.MarshalIndent(stats, "", " ")
	die(os.WriteFile(filepath.Join(out, "fixdiff.json"), j, 0o644))
	md := fmt.Sprintf("# Fix-commit differential\n\nGenerated by `go run ./tools/corpus fixdiff -label %s`: %d security-fix commits scanned (%d skipped: API/raw errors, merges or no supported modified files). "+
		"A rule *fixed* a finding when it fired on the parent and not on the fix; *introduced* when it fires only on the fixed file.\n\n"+
		"| commit | kind | files | rules whose findings the fix removed | rules that fire only after the fix |\n|---|---|---|---|---|\n%s", *label, used, skipped, report.String())
	rules := make([]string, 0, len(stats))
	for r := range stats {
		rules = append(rules, r)
	}
	slices.Sort(rules)
	md += "\n## Per rule\n\n| rule | fixed | introduced |\n|---|---|---|\n"
	for _, r := range rules {
		md += fmt.Sprintf("| %s | %d | %d |\n", r, stats[r].Fixed, stats[r].Introduced)
	}
	die(os.WriteFile(filepath.Join(out, "fixdiff.md"), []byte(md), 0o644))
	fmt.Printf("fixdiff: %d commits, %d skipped, %d rules with evidence -> %s\n", used, skipped, len(stats), out)
}

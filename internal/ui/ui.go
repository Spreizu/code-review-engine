// Package ui serves `crev ui`: a small local, read-only web UI over run history (.crev/runs),
// branch ledgers and the rule catalog. Stdlib net/http + one embedded HTML file (vanilla JS,
// inline SVG charts); no build step, no external assets.
package ui

import (
	"cmp"
	"embed"
	"encoding/json"
	"errors"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/runs"
)

//go:embed static/index.html
var static embed.FS

// Server holds what the UI reads. Everything is loaded from disk per request, so runs recorded
// while the UI is open show up on refresh.
type Server struct {
	Root    string // project root (for code snippets)
	Store   runs.Store
	Rules   []*rules.Rule
	Version string
	byID    map[string]*rules.Rule
}

// Handler returns the HTTP handler (GET only; requests with a foreign Host header are refused to
// block DNS-rebinding access to the local server).
func (s *Server) Handler() http.Handler {
	s.byID = map[string]*rules.Rule{}
	for _, r := range s.Rules {
		s.byID[r.ID] = r
	}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /{$}", s.index)
	mux.HandleFunc("GET /api/info", s.info)
	mux.HandleFunc("GET /api/runs", s.listRuns)
	mux.HandleFunc("GET /api/runs/{id}", s.getRun)
	mux.HandleFunc("GET /api/runs/{id}/findings", s.runFindings)
	mux.HandleFunc("GET /api/dashboard", s.dashboard)
	mux.HandleFunc("GET /api/compare", s.compare)
	mux.HandleFunc("GET /api/branches", s.branches)
	mux.HandleFunc("GET /api/ledger", s.ledger)
	mux.HandleFunc("GET /api/rules", s.listRules)
	mux.HandleFunc("GET /api/rules/{id}", s.getRule)
	mux.HandleFunc("GET /api/snippet", s.snippet)
	return localOnly(mux)
}

func localOnly(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		host := r.Host
		if hh, _, err := net.SplitHostPort(host); err == nil {
			host = hh
		}
		host = strings.Trim(host, "[]")
		if host != "localhost" && net.ParseIP(host) == nil {
			http.Error(w, "forbidden host", http.StatusForbidden)
			return
		}
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Referrer-Policy", "no-referrer")
		h.ServeHTTP(w, r)
	})
}

func (s *Server) index(w http.ResponseWriter, _ *http.Request) {
	b, _ := static.ReadFile("static/index.html")
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data:; connect-src 'self'")
	_, _ = w.Write(b)
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(v)
}

func httpErr(w http.ResponseWriter, code int, err error) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
}

func (s *Server) info(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, map[string]any{"root": s.Root, "version": s.Version, "rules": len(s.Rules), "runs_dir": s.Store.Dir})
}

func (s *Server) listRuns(w http.ResponseWriter, r *http.Request) {
	idx, err := s.Store.Index()
	if err != nil {
		httpErr(w, 500, err)
		return
	}
	if b := r.URL.Query().Get("branch"); b != "" {
		var keep []runs.IndexEntry
		for _, e := range idx.Runs {
			if e.Branch == b {
				keep = append(keep, e)
			}
		}
		idx.Runs = keep
	}
	writeJSON(w, idx)
}

type runDetail struct {
	Meta     *runs.Meta          `json:"meta"`
	Findings []*findings.Finding `json:"findings"`
	Stats    map[string]int      `json:"stats"`
	Errors   []string            `json:"errors,omitempty"`
}

func (s *Server) loadRun(ref string) (*runs.Meta, *findings.Report, error) {
	m, err := s.Store.Resolve(ref)
	if err != nil {
		return nil, nil, err
	}
	rep, err := s.Store.Report(m)
	return m, rep, err
}

func (s *Server) getRun(w http.ResponseWriter, r *http.Request) {
	m, rep, err := s.loadRun(r.PathValue("id"))
	if err != nil {
		httpErr(w, 404, err)
		return
	}
	writeJSON(w, runDetail{Meta: m, Findings: rep.Findings, Stats: rep.Stats, Errors: rep.Errors})
}

// Comparison is the result of comparing two runs by finding fingerprint.
type Comparison struct {
	A         *runs.Meta          `json:"a"`
	B         *runs.Meta          `json:"b"`
	New       []*findings.Finding `json:"new"`   // in B, not in A
	Fixed     []*findings.Finding `json:"fixed"` // in A, not in B (see Caveat for diff scopes)
	Unchanged int                 `json:"unchanged"`
	// UnchangedList: findings in both runs (as in B), capped at ?limit (default 1000).
	UnchangedList []*findings.Finding `json:"unchanged_list"`
	Truncated     bool                `json:"truncated,omitempty"`
	Caveat        string              `json:"caveat,omitempty"`
}

// Compare diffs two reports by fingerprint (only review-list findings, findings.InReview).
func Compare(a, b *findings.Report) (newF, fixed []*findings.Finding, same int) {
	ids := func(r *findings.Report) map[string]*findings.Finding {
		m := map[string]*findings.Finding{}
		for _, f := range r.Findings {
			if findings.InReview(f, "") {
				m[f.ID] = f
			}
		}
		return m
	}
	ma, mb := ids(a), ids(b)
	for id, f := range mb {
		if ma[id] == nil {
			newF = append(newF, f)
		} else {
			same++
		}
	}
	for id, f := range ma {
		if mb[id] == nil {
			fixed = append(fixed, f)
		}
	}
	order := func(l []*findings.Finding) {
		slices.SortFunc(l, func(a, b *findings.Finding) int {
			return cmp.Or(strings.Compare(a.Location.Path, b.Location.Path), cmp.Compare(a.Location.StartLine, b.Location.StartLine))
		})
	}
	order(newF)
	order(fixed)
	return
}

func (s *Server) compare(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	ma, ra, err := s.loadRun(q.Get("a"))
	if err != nil {
		httpErr(w, 404, err)
		return
	}
	mb, rb, err := s.loadRun(q.Get("b"))
	if err != nil {
		httpErr(w, 404, err)
		return
	}
	c := Comparison{A: ma, B: mb}
	c.New, c.Fixed, c.Unchanged = Compare(ra, rb)
	_, limit := pageArgs(r, 1000, 5000)
	inA := map[string]bool{}
	for _, f := range ra.Findings {
		if findings.InReview(f, "") {
			inA[f.ID] = true
		}
	}
	for _, f := range rb.Findings {
		if findings.InReview(f, "") && inA[f.ID] {
			c.UnchangedList = append(c.UnchangedList, f)
		}
	}
	slices.SortFunc(c.UnchangedList, func(a, b *findings.Finding) int {
		return cmp.Or(strings.Compare(a.Location.Path, b.Location.Path), cmp.Compare(a.Location.StartLine, b.Location.StartLine))
	})
	for _, l := range []*[]*findings.Finding{&c.New, &c.Fixed, &c.UnchangedList} {
		if len(*l) > limit {
			*l, c.Truncated = (*l)[:limit], true
		}
		if *l == nil {
			*l = []*findings.Finding{}
		}
	}
	if ma.Scope.IsDiff() || mb.Scope.IsDiff() {
		c.Caveat = "at least one run is a diff-scoped scan: findings outside its scope are absent, not fixed (the branch ledger accounts for this)"
	} else if ma.Branch != mb.Branch {
		c.Caveat = "runs are on different branches"
	}
	writeJSON(w, c)
}

func (s *Server) branches(w http.ResponseWriter, _ *http.Request) {
	idx, err := s.Store.Index()
	if err != nil {
		httpErr(w, 500, err)
		return
	}
	type br struct {
		Branch string `json:"branch"`
		Latest string `json:"latest"`
		Runs   int    `json:"runs"`
	}
	m := map[string]*br{}
	for _, e := range idx.Runs {
		if m[e.Branch] == nil {
			m[e.Branch] = &br{Branch: e.Branch, Latest: idx.ByBranch[e.Branch]}
		}
		m[e.Branch].Runs++
	}
	out := []*br{}
	for _, b := range m {
		out = append(out, b)
	}
	slices.SortFunc(out, func(a, b *br) int { return strings.Compare(a.Branch, b.Branch) })
	writeJSON(w, out)
}

func (s *Server) ledger(w http.ResponseWriter, r *http.Request) {
	b := r.URL.Query().Get("branch")
	if b == "" {
		httpErr(w, 400, errors.New("branch required"))
		return
	}
	l, err := s.Store.LoadLedger(b)
	if err != nil {
		httpErr(w, 500, err)
		return
	}
	writeJSON(w, l)
}

// RuleSummary is the list view of a rule.
type RuleSummary struct {
	ID        string            `json:"id"`
	Title     string            `json:"title"`
	Pack      string            `json:"pack"`
	Topic     string            `json:"topic,omitempty"`
	Tags      []string          `json:"tags,omitempty"`
	Language  string            `json:"language"`
	Framework string            `json:"framework,omitempty"`
	Category  string            `json:"category"`
	Severity  string            `json:"severity"`
	Mode      string            `json:"mode"`
	AppliesTo map[string]string `json:"applies_to,omitempty"`
	Origin    string            `json:"origin,omitempty"`
	URL       string            `json:"url"`
	Trust     string            `json:"trust,omitempty"`
	Version   string            `json:"pack_version,omitempty"`
	CWE       []string          `json:"cwe,omitempty"`
	OWASP     []string          `json:"owasp,omitempty"`
	Stats     *hitStats         `json:"stats,omitempty"`
}

func (s *Server) listRules(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	text := strings.ToLower(q.Get("q"))
	ver := strings.ToLower(q.Get("version")) // matches applies_to keys or ranges, e.g. "java" or ">=21"
	out := []RuleSummary{}
	hits, sampled := s.ruleHits()
	facets := map[string]map[string]int{"language": {}, "category": {}, "severity": {}, "pack": {}, "topic": {}, "tag": {}, "mode": {}, "trust": {}}
	for _, ru := range s.Rules {
		rs := RuleSummary{ID: ru.ID, Title: ru.Title, Pack: ru.Pack, Language: ru.Language, Framework: ru.Framework, Category: ru.Category,
			Severity: ru.Severity, Mode: ru.Detection.Mode, AppliesTo: ru.AppliesTo, Origin: ru.Origin, URL: ru.Source.URL,
			Version: ru.PackVersion, CWE: ru.CWE, OWASP: ru.OWASP, Stats: hits[ru.ID], Topic: ruleTopic(ru.File), Tags: ru.Tags}
		if q.Get("fired") == "1" && rs.Stats == nil {
			continue
		}
		if ru.Trust != nil {
			rs.Trust = ru.Trust.Level
		}
		if !match(q.Get("language"), rs.Language) || !match(q.Get("category"), rs.Category) || !match(q.Get("severity"), rs.Severity) ||
			!match(q.Get("pack"), rs.Pack) || !match(q.Get("mode"), rs.Mode) || !match(q.Get("trust"), rs.Trust) ||
			!match(q.Get("topic"), rs.Topic) || q.Get("tag") != "" && !slices.Contains(rs.Tags, q.Get("tag")) {
			continue
		}
		if text != "" && !strings.Contains(strings.ToLower(rs.ID+" "+rs.Title+" "+ru.Message+" "+strings.Join(ru.Tags, " ")), text) {
			continue
		}
		if ver != "" {
			hit := false
			for k, v := range rs.AppliesTo {
				if strings.Contains(strings.ToLower(k+" "+v), ver) {
					hit = true
				}
			}
			if !hit {
				continue
			}
		}
		facets["language"][rs.Language]++
		facets["category"][rs.Category]++
		facets["severity"][rs.Severity]++
		facets["pack"][rs.Pack]++
		if rs.Topic != "" {
			facets["topic"][rs.Topic]++
		}
		for _, t := range rs.Tags {
			facets["tag"][t]++
		}
		facets["mode"][rs.Mode]++
		if rs.Trust != "" {
			facets["trust"][rs.Trust]++
		}
		out = append(out, rs)
	}
	hitsOf := func(r RuleSummary) int {
		if r.Stats == nil {
			return 0
		}
		return r.Stats.Hits
	}
	switch q.Get("sort") {
	case "hits":
		slices.SortFunc(out, func(a, b RuleSummary) int {
			return cmp.Or(cmp.Compare(hitsOf(b), hitsOf(a)), strings.Compare(a.ID, b.ID))
		})
	case "severity":
		slices.SortFunc(out, func(a, b RuleSummary) int {
			return cmp.Or(cmp.Compare(sevRank[a.Severity], sevRank[b.Severity]), strings.Compare(a.ID, b.ID))
		})
	default:
		slices.SortFunc(out, func(a, b RuleSummary) int { return strings.Compare(a.ID, b.ID) })
	}
	total := len(out)
	offset, limit := pageArgs(r, 200, 5000)
	out = out[min(offset, len(out)):min(len(out), offset+limit)]
	writeJSON(w, map[string]any{"total": total, "offset": offset, "limit": limit, "rules": out, "facets": facets, "sampled_runs": sampled})
}

func match(want, have string) bool {
	if want == "" {
		return true
	}
	for _, w := range strings.Split(want, ",") {
		if strings.EqualFold(strings.TrimSpace(w), have) {
			return true
		}
	}
	return false
}

func (s *Server) getRule(w http.ResponseWriter, r *http.Request) {
	ru := s.byID[r.PathValue("id")]
	if ru == nil {
		httpErr(w, 404, errors.New("unknown rule"))
		return
	}
	y, _ := yaml.Marshal(ru)
	hits, sampled := s.ruleHits()
	writeJSON(w, map[string]any{"yaml": string(y), "pack": ru.Pack, "pack_version": ru.PackVersion, "file": filepath.Base(filepath.Dir(ru.File)) + "/" + filepath.Base(ru.File), "topic": ruleTopic(ru.File),
		"stats": hits[ru.ID], "sampled_runs": sampled,
		"rule": map[string]any{"id": ru.ID, "title": ru.Title, "language": ru.Language, "framework": ru.Framework, "category": ru.Category,
			"severity": ru.Severity, "mode": ru.Detection.Mode, "applies_to": ru.AppliesTo, "message": ru.Message, "rationale": ru.Rationale,
			"fix": ru.Fix, "source": ru.Source, "examples": map[string]string{"bad": ru.Examples.Bad, "good": ru.Examples.Good},
			"xref": ru.Xref, "tags": ru.Tags, "origin": ru.Origin, "status": ru.Status, "trust": ru.Trust, "trust_summary": trustSummary(ru),
			"cwe": ru.CWE, "owasp": ru.OWASP, "asvs": ru.ASVS, "precision": ru.Precision, "ai_question": ru.AIQuestion}})
}

func trustSummary(ru *rules.Rule) string {
	if ru.Trust == nil {
		return ""
	}
	return ru.Trust.String()
}

// Snippet is a window of source lines around a finding.
type Snippet struct {
	Path   string   `json:"path"`
	Start  int      `json:"start"`
	Lines  []string `json:"lines"`
	Source string   `json:"source"` // "commit <sha>" or "working tree"
}

func (s *Server) snippet(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	rel := filepath.ToSlash(filepath.Clean(q.Get("path")))
	if rel == "." || filepath.IsAbs(rel) || rel == ".." || strings.HasPrefix(rel, "../") {
		httpErr(w, 400, errors.New("bad path"))
		return
	}
	line, _ := strconv.Atoi(q.Get("line"))
	end, _ := strconv.Atoi(q.Get("end"))
	if end < line {
		end = line
	}
	ctx := 6
	var src []byte
	from := "working tree"
	// Prefer the file as of the run's commit (if the run was clean), so old runs show the code
	// that was actually reviewed.
	if ref := q.Get("run"); ref != "" {
		if m, err := s.Store.Resolve(ref); err == nil && m.Commit != "" && !m.Dirty {
			if b, err := exec.Command("git", "-C", s.Root, "show", m.Commit+":"+rel).Output(); err == nil {
				src, from = b, "commit "+m.Commit[:min(len(m.Commit), 9)]
			}
		}
	}
	if src == nil {
		p := filepath.Join(s.Root, filepath.FromSlash(rel))
		if rp, err := filepath.Rel(s.Root, p); err != nil || strings.HasPrefix(rp, "..") {
			httpErr(w, 400, errors.New("bad path"))
			return
		}
		b, err := os.ReadFile(p)
		if err != nil {
			httpErr(w, 404, err)
			return
		}
		src = b
	}
	all := strings.Split(string(src), "\n")
	lo := max(1, line-ctx)
	hi := min(len(all), end+ctx)
	sn := Snippet{Path: rel, Start: lo, Source: from}
	if lo <= hi {
		sn.Lines = all[lo-1 : hi]
	}
	writeJSON(w, sn)
}

// ruleTopic is the topic of a catalog rule: its file name in rules/packs/<pack>/<topic>[.gen].yaml.
func ruleTopic(file string) string {
	b := filepath.Base(file)
	b = strings.TrimSuffix(strings.TrimSuffix(b, ".yaml"), ".gen")
	return b
}

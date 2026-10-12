package ui

import (
	"cmp"
	"net/http"
	"path"
	"slices"
	"strconv"
	"strings"
	"sync"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/report"
	"github.com/elmo/code-review-engine/internal/runs"
)

// FindingView is a finding plus the fields the UI filters on.
type FindingView struct {
	*findings.Finding
	Lang   string `json:"lang"`
	Pack   string `json:"pack"`
	Trust  string `json:"trust,omitempty"`
	Change string `json:"change"` // new | existing | fixed ("" for hidden findings: not tracked by the ledger)
	Reason string `json:"reason"` // hidden reason ("" = in the review list)
}

var extLang = map[string]string{".go": "go", ".py": "python", ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript", ".jsx": "javascript",
	".ts": "typescript", ".tsx": "typescript", ".vue": "vue", ".java": "java", ".kt": "kotlin", ".kts": "kotlin", ".php": "php",
	".yaml": "yaml", ".yml": "yaml", ".json": "json", ".tf": "terraform", ".xml": "xml", ".graphql": "graphql", ".gql": "graphql", ".proto": "protobuf"}

func (s *Server) view(f *findings.Finding, change string) FindingView {
	v := FindingView{Finding: f, Change: change, Reason: f.HiddenReason}
	if v.Reason == "" && !findings.InReview(f, "") {
		v.Reason = report.HiddenReason(f, report.GateOptions{})
	}
	if ru := s.byID[f.RuleID]; ru != nil {
		v.Lang, v.Pack = ru.Language, ru.Pack
		if ru.Trust != nil {
			v.Trust = ru.Trust.Level
		}
	}
	if l, ok := extLang[strings.ToLower(path.Ext(f.Location.Path))]; ok && (v.Lang == "" || v.Lang == "any") {
		v.Lang = l
	} else if strings.HasPrefix(path.Base(f.Location.Path), "Dockerfile") && v.Lang == "" {
		v.Lang = "dockerfile"
	}
	if v.Lang == "" {
		v.Lang = "other"
	}
	return v
}

// previousRun is the run recorded on the same branch just before m (nil when none).
func (s *Server) previousRun(m *runs.Meta) *runs.Meta {
	idx, err := s.Store.Index()
	if err != nil {
		return nil
	}
	var prev *runs.IndexEntry
	for i := range idx.Runs {
		e := &idx.Runs[i]
		if e.ID == m.ID {
			break
		}
		if e.Branch == m.Branch {
			prev = e
		}
	}
	if prev == nil {
		return nil
	}
	pm, err := s.Store.Resolve(prev.ID)
	if err != nil {
		return nil
	}
	return pm
}

// runViews returns all findings of a run as views, plus the findings fixed since the previous
// run on the branch (change=fixed, taken from that run's report).
func (s *Server) runViews(m *runs.Meta, rep *findings.Report) []FindingView {
	isNew := map[string]bool{}
	var fixed map[string]bool
	if m.Ledger != nil {
		for _, id := range m.Ledger.New {
			isNew[id] = true
		}
		for _, id := range m.Ledger.Reopened {
			isNew[id] = true
		}
		if len(m.Ledger.Fixed) > 0 {
			fixed = map[string]bool{}
			for _, id := range m.Ledger.Fixed {
				fixed[id] = true
			}
		}
	}
	out := make([]FindingView, 0, len(rep.Findings))
	for _, f := range rep.Findings {
		ch := "existing"
		if isNew[f.ID] {
			ch = "new"
		}
		v := s.view(f, ch)
		if v.Reason != "" {
			v.Change = "" // the branch ledger tracks review-list findings only
		}
		out = append(out, v)
	}
	if fixed != nil {
		if pm := s.previousRun(m); pm != nil {
			if prep, err := s.Store.Report(pm); err == nil {
				for _, f := range prep.Findings {
					if fixed[f.ID] {
						out = append(out, s.view(f, "fixed"))
					}
				}
			}
		}
	}
	return out
}

type findingFilter struct {
	q                                                                 string
	sev, cat, lang, pack, rule, cwe, owasp, trust, change, reason, st []string
	file                                                              string
	hidden                                                            string // "" (review list only) | "1" (all) | "only"
}

func split(v string) []string {
	if v == "" {
		return nil
	}
	var out []string
	for _, p := range strings.Split(v, ",") {
		if p = strings.TrimSpace(p); p != "" {
			out = append(out, p)
		}
	}
	return out
}

func parseFilter(r *http.Request) findingFilter {
	q := r.URL.Query()
	return findingFilter{q: strings.ToLower(q.Get("q")), sev: split(q.Get("severity")), cat: split(q.Get("category")), lang: split(q.Get("lang")),
		pack: split(q.Get("pack")), rule: split(q.Get("rule")), cwe: split(q.Get("cwe")), owasp: split(q.Get("owasp")), trust: split(q.Get("trust")),
		change: split(q.Get("change")), reason: split(q.Get("reason")), st: split(q.Get("status")), file: q.Get("file"), hidden: q.Get("hidden")}
}

func in(want []string, have ...string) bool {
	if len(want) == 0 {
		return true
	}
	for _, w := range want {
		for _, h := range have {
			if strings.EqualFold(w, h) {
				return true
			}
		}
	}
	return false
}

// keep applies every filter except the facet named skip (so a facet's counts show what selecting
// another value of it would give).
func (ff findingFilter) keep(v FindingView, skip string) bool {
	switch ff.hidden {
	case "1", "all":
	case "only":
		if v.Reason == "" {
			return false
		}
	default:
		if v.Reason != "" && len(ff.reason) == 0 {
			return false
		}
	}
	if v.Change == "fixed" && skip != "change" && (len(ff.change) == 0 || !in(ff.change, "fixed")) {
		return false // fixed findings (from the previous run) only on request
	}
	chk := func(name string, want []string, have ...string) bool { return name == skip || in(want, have...) }
	if !chk("severity", ff.sev, v.Severity) || !chk("category", ff.cat, v.Category) || !chk("lang", ff.lang, v.Lang) ||
		!chk("pack", ff.pack, v.Pack) || !chk("rule", ff.rule, v.RuleID) || !chk("trust", ff.trust, v.Trust) ||
		!chk("change", ff.change, v.Change) || !chk("reason", ff.reason, v.Reason) || !chk("status", ff.st, v.Status) {
		return false
	}
	if skip != "cwe" && len(ff.cwe) > 0 && !in(ff.cwe, v.CWE...) {
		return false
	}
	if skip != "owasp" && len(ff.owasp) > 0 && !in(ff.owasp, v.OWASP...) {
		return false
	}
	if skip != "file" && ff.file != "" && v.Location.Path != ff.file && !strings.HasPrefix(v.Location.Path, strings.TrimSuffix(ff.file, "/")+"/") {
		return false
	}
	if ff.q != "" && !strings.Contains(strings.ToLower(v.RuleID+" "+v.Title+" "+v.Message+" "+v.Location.Path+" "+v.Snippet+" "+v.HiddenDetail+" "+strings.Join(v.CWE, " ")), ff.q) {
		return false
	}
	return true
}

var sevRank = map[string]int{"critical": 0, "major": 1, "minor": 2, "info": 3}

func sortViews(vs []FindingView, by string) {
	byFile := func(a, b FindingView) int {
		return cmp.Or(strings.Compare(a.Location.Path, b.Location.Path), strings.Compare(a.RuleID, b.RuleID), cmp.Compare(a.Location.StartLine, b.Location.StartLine))
	}
	switch by {
	case "severity":
		slices.SortStableFunc(vs, func(a, b FindingView) int { return cmp.Or(cmp.Compare(sevRank[a.Severity], sevRank[b.Severity]), byFile(a, b)) })
	case "rule":
		slices.SortStableFunc(vs, func(a, b FindingView) int { return cmp.Or(strings.Compare(a.RuleID, b.RuleID), byFile(a, b)) })
	default: // file (grouped file > rule)
		slices.SortStableFunc(vs, byFile)
	}
}

func pageArgs(r *http.Request, def, maxLimit int) (offset, limit int) {
	offset, _ = strconv.Atoi(r.URL.Query().Get("offset"))
	limit, _ = strconv.Atoi(r.URL.Query().Get("limit"))
	if offset < 0 {
		offset = 0
	}
	if limit <= 0 {
		limit = def
	}
	limit = min(limit, maxLimit)
	return
}

// FindingsPage is GET /api/runs/{id}/findings.
type FindingsPage struct {
	Run       *runs.Meta                `json:"run"`
	Total     int                       `json:"total"`
	Offset    int                       `json:"offset"`
	Limit     int                       `json:"limit"`
	Items     []FindingView             `json:"items"`
	Facets    map[string]map[string]int `json:"facets"`
	Files     map[string]int            `json:"files"`   // path -> matching findings (file tree)
	Review    int                       `json:"review"`  // findings in the review list (whole run)
	Hidden    map[string]int            `json:"hidden"`  // hidden findings per reason (whole run)
	Changes   map[string]int            `json:"changes"` // new / existing / fixed (review list)
	Truncated bool                      `json:"truncated,omitempty"`
}

func (s *Server) runFindings(w http.ResponseWriter, r *http.Request) {
	m, rep, err := s.loadRun(r.PathValue("id"))
	if err != nil {
		httpErr(w, 404, err)
		return
	}
	ff := parseFilter(r)
	all := s.runViews(m, rep)
	p := FindingsPage{Run: m, Facets: map[string]map[string]int{}, Files: map[string]int{}, Hidden: map[string]int{}, Changes: map[string]int{}}
	facet := func(name string, vals ...string) {
		if p.Facets[name] == nil {
			p.Facets[name] = map[string]int{}
		}
		for _, v := range vals {
			if v != "" {
				p.Facets[name][v]++
			}
		}
	}
	var keep []FindingView
	for _, v := range all {
		if v.Reason == "" {
			if v.Change != "fixed" {
				p.Review++
			}
			p.Changes[v.Change]++
		} else if v.Change != "fixed" {
			p.Hidden[v.Reason]++
		}
		for _, k := range []struct {
			name string
			vals []string
		}{{"severity", []string{v.Severity}}, {"category", []string{v.Category}}, {"lang", []string{v.Lang}}, {"pack", []string{v.Pack}},
			{"rule", []string{v.RuleID}}, {"cwe", v.CWE}, {"owasp", v.OWASP}, {"trust", []string{v.Trust}}, {"change", []string{v.Change}},
			{"reason", []string{v.Reason}}, {"status", []string{v.Status}}} {
			if ff.keep(v, k.name) {
				facet(k.name, k.vals...)
			}
		}
		if ff.keep(v, "file") {
			p.Files[v.Location.Path]++
		}
		if ff.keep(v, "") {
			keep = append(keep, v)
		}
	}
	sortViews(keep, r.URL.Query().Get("sort"))
	p.Total = len(keep)
	p.Offset, p.Limit = pageArgs(r, 200, 2000)
	if p.Offset < len(keep) {
		p.Items = keep[p.Offset:min(len(keep), p.Offset+p.Limit)]
	}
	if p.Items == nil {
		p.Items = []FindingView{}
	}
	if len(p.Facets["rule"]) > 300 { // keep the payload small on huge runs
		p.Facets["rule"] = topN(p.Facets["rule"], 300)
		p.Truncated = true
	}
	writeJSON(w, p)
}

func topN(m map[string]int, n int) map[string]int {
	type kv struct {
		k string
		v int
	}
	var l []kv
	for k, v := range m {
		l = append(l, kv{k, v})
	}
	slices.SortFunc(l, func(a, b kv) int { return cmp.Or(cmp.Compare(b.v, a.v), strings.Compare(a.k, b.k)) })
	out := map[string]int{}
	for _, e := range l[:min(n, len(l))] {
		out[e.k] = e.v
	}
	return out
}

// BranchSummary is one branch on the dashboard.
type BranchSummary struct {
	Branch   string            `json:"branch"`
	Latest   runs.IndexEntry   `json:"latest"`
	Runs     int               `json:"runs"`
	New      int               `json:"new"`
	Fixed    int               `json:"fixed"`
	Reopened int               `json:"reopened"`
	Trend    []TrendPoint      `json:"trend"`
	Hidden   map[string]int    `json:"hidden,omitempty"`
	Review   int               `json:"review"`
	Category map[string]int    `json:"by_category,omitempty"`
	Severity map[string]int    `json:"by_severity,omitempty"`
	Status   map[string]int    `json:"by_status,omitempty"`
	Extra    map[string]string `json:"extra,omitempty"`
}

// TrendPoint is one run in a branch sparkline.
type TrendPoint struct {
	Run    string `json:"run"`
	Time   string `json:"time"`
	Total  int    `json:"total"`
	Review int    `json:"review"`
	Gating int    `json:"gating"`
}

func reviewCount(c runs.Counts) int {
	h := 0
	for _, n := range c.Hidden {
		h += n
	}
	if c.Hidden == nil { // older runs: confirmed + ai_confirmed approximates the review list
		return c.ByStatus["confirmed"] + c.ByStatus["ai_confirmed"]
	}
	return c.Total - h
}

func (s *Server) dashboard(w http.ResponseWriter, _ *http.Request) {
	idx, err := s.Store.Index()
	if err != nil {
		httpErr(w, 500, err)
		return
	}
	by := map[string]*BranchSummary{}
	var order []string
	for _, e := range idx.Runs {
		b := by[e.Branch]
		if b == nil {
			b = &BranchSummary{Branch: e.Branch}
			by[e.Branch] = b
			order = append(order, e.Branch)
		}
		b.Runs++
		b.Latest = e
		b.Trend = append(b.Trend, TrendPoint{Run: e.ID, Time: e.Timestamp.Format("2006-01-02T15:04:05Z07:00"), Total: e.Counts.Total, Review: reviewCount(e.Counts), Gating: e.Counts.Gating})
	}
	out := []*BranchSummary{}
	for _, name := range order {
		b := by[name]
		if len(b.Trend) > 30 {
			b.Trend = b.Trend[len(b.Trend)-30:]
		}
		c := b.Latest.Counts
		b.Hidden, b.Review, b.Category, b.Severity, b.Status = c.Hidden, reviewCount(c), c.ByCategory, c.BySeverity, c.ByStatus
		if m, err := s.Store.Resolve(b.Latest.ID); err == nil && m.Ledger != nil {
			b.New, b.Fixed, b.Reopened = len(m.Ledger.New), len(m.Ledger.Fixed), len(m.Ledger.Reopened)
		}
		out = append(out, b)
	}
	slices.SortStableFunc(out, func(a, b *BranchSummary) int { return b.Latest.Timestamp.Compare(a.Latest.Timestamp) })
	writeJSON(w, map[string]any{"latest": idx.Latest, "branches": out, "runs": len(idx.Runs)})
}

// ruleHits counts findings per rule over the most recent runs (cached per latest run id).
type hitStats struct {
	Hits    int    `json:"hits"`     // findings across the sampled runs
	Runs    int    `json:"runs"`     // runs where the rule fired
	Latest  int    `json:"latest"`   // findings in the latest run
	Hidden  int    `json:"hidden"`   // of Hits, hidden from the review list
	LastRun string `json:"last_run"` // most recent run where it fired
}

var hitCache struct {
	sync.Mutex
	key  string
	m    map[string]*hitStats
	runs int
}

const hitSample = 50

func (s *Server) ruleHits() (map[string]*hitStats, int) {
	idx, err := s.Store.Index()
	if err != nil || len(idx.Runs) == 0 {
		return map[string]*hitStats{}, 0
	}
	key := idx.Latest + "/" + strconv.Itoa(len(idx.Runs))
	hitCache.Lock()
	defer hitCache.Unlock()
	if hitCache.key == key {
		return hitCache.m, hitCache.runs
	}
	m := map[string]*hitStats{}
	sample := idx.Runs[max(0, len(idx.Runs)-hitSample):]
	for i, e := range sample {
		rm, err := s.Store.Resolve(e.ID)
		if err != nil {
			continue
		}
		rep, err := s.Store.Report(rm)
		if err != nil {
			continue
		}
		seen := map[string]bool{}
		for _, f := range rep.Findings {
			h := m[f.RuleID]
			if h == nil {
				h = &hitStats{}
				m[f.RuleID] = h
			}
			h.Hits++
			if f.HiddenReason != "" || !findings.InReview(f, "") {
				h.Hidden++
			}
			if e.ID == idx.Latest {
				h.Latest++
			}
			if !seen[f.RuleID] {
				seen[f.RuleID] = true
				h.Runs++
				h.LastRun = e.ID
			}
		}
		_ = i
	}
	hitCache.key, hitCache.m, hitCache.runs = key, m, len(sample)
	return m, len(sample)
}

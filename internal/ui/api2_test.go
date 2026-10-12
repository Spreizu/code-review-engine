package ui

import (
	"net/http/httptest"
	"os"
	"path/filepath"
	"strconv"
	"testing"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/report"
	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/runs"
)

// setup2: run 1 has x, y; run 2 has x (existing), z (new), a hidden pending finding p and 250
// findings in big.go for paging; y is fixed in run 2.
func setup2(t *testing.T) (srvURL func(string) string, s *Server, ids []string) {
	root := t.TempDir()
	st := runs.Store{Dir: filepath.Join(root, ".crev", "runs")}
	p := &findings.Finding{ID: "p", RuleID: "R2", Severity: "critical", Status: "pending_ai", Category: "security", CWE: []string{"CWE-89"}, OWASP: []string{"A03:2021"},
		Location: findings.Location{Path: "src/db.java", StartLine: 7}, HiddenReason: "pending_ai", HiddenDetail: "AI step is off"}
	r2 := []*findings.Finding{f("x", "a.go", 4), f("z", "pkg/b.go", 3), p}
	for i := range 250 {
		r2 = append(r2, f("big"+strconv.Itoa(i), "pkg/big.go", i+1))
	}
	reps := []*findings.Report{{Findings: []*findings.Finding{f("x", "a.go", 4), f("y", "a.go", 1)}}, {Findings: r2}}
	l, _ := st.LoadLedger("main")
	for i, rep := range reps {
		m := &runs.Meta{Branch: "main", Timestamp: time.Date(2026, 10, 1+i, 0, 0, 0, 0, time.UTC)}
		dir, err := st.Create(m)
		if err != nil {
			t.Fatal(err)
		}
		report.Annotate(rep, report.GateOptions{})
		fh, _ := os.Create(filepath.Join(dir, "report.json"))
		report.JSON(fh, rep)
		fh.Close()
		m.Ledger = l.Apply(rep, runs.Point{Run: m.ID, Time: m.Timestamp}, nil, nil)
		m.Counts = runs.CountsOf(rep)
		st.Finish(m)
		ids = append(ids, m.ID)
	}
	st.SaveLedger(l)
	ru := &rules.Rule{ID: "R1", Title: "No panic", Language: "go", Category: "bug", Severity: "major", Pack: "go"}
	ru2 := &rules.Rule{ID: "R2", Title: "SQL", Language: "java", Category: "security", Severity: "critical", Pack: "java-security", CWE: []string{"CWE-89"}}
	s = &Server{Root: root, Store: st, Rules: []*rules.Rule{ru, ru2}, Version: "test"}
	return nil, s, ids
}

func TestFindingsAPI(t *testing.T) {
	_, s, ids := setup2(t)
	srv := newSrv(s)
	defer srv.Close()
	var p FindingsPage
	if c := get(t, srv, "/api/runs/latest/findings", &p); c != 200 {
		t.Fatal(c)
	}
	if p.Total != 252 || p.Review != 252 || p.Hidden["pending_ai"] != 1 || len(p.Items) != 200 || p.Changes["new"] != 251 || p.Changes["fixed"] != 1 {
		t.Fatalf("default page: total %d review %d hidden %v items %d changes %v", p.Total, p.Review, p.Hidden, len(p.Items), p.Changes)
	}
	if p.Items[0].Location.Path != "a.go" || p.Items[0].Change != "existing" || p.Items[0].Lang != "go" {
		t.Fatalf("first item %+v", p.Items[0])
	}
	if p.Files["pkg/big.go"] != 250 || p.Facets["severity"]["major"] != 252 {
		t.Fatalf("files %v facets %v", p.Files, p.Facets["severity"])
	}
	get(t, srv, "/api/runs/latest/findings?offset=200&limit=100", &p)
	if len(p.Items) != 52 || p.Offset != 200 {
		t.Fatalf("page 2: %d items at %d", len(p.Items), p.Offset)
	}
	get(t, srv, "/api/runs/latest/findings?hidden=only", &p)
	if p.Total != 1 || p.Items[0].Reason != "pending_ai" || p.Items[0].HiddenDetail == "" || p.Items[0].Change != "" {
		t.Fatalf("hidden only: %+v", p.Items)
	}
	get(t, srv, "/api/runs/latest/findings?reason=pending_ai&cwe=CWE-89", &p) // a reason filter implies hidden
	if p.Total != 1 || p.Items[0].Pack != "java-security" {
		t.Fatalf("reason+cwe: %d", p.Total)
	}
	get(t, srv, "/api/runs/latest/findings?change=fixed", &p)
	if p.Total != 1 || p.Items[0].ID != "y" || p.Items[0].Change != "fixed" {
		t.Fatalf("fixed: %+v", p.Items)
	}
	get(t, srv, "/api/runs/latest/findings?file=pkg&q=big.go&sort=severity&limit=5", &p)
	if p.Total != 250 || len(p.Items) != 5 {
		t.Fatalf("file prefix + search: %d", p.Total)
	}
	get(t, srv, "/api/runs/latest/findings?severity=critical", &p)
	if p.Total != 0 || p.Facets["severity"]["major"] != 252 { // facet ignores its own filter
		t.Fatalf("severity facet: %d %v", p.Total, p.Facets["severity"])
	}
	if c := get(t, srv, "/api/runs/nope/findings", nil); c != 404 {
		t.Fatalf("unknown run: %d", c)
	}
	_ = ids
}

func TestDashboardRulesCompareAPI(t *testing.T) {
	_, s, ids := setup2(t)
	srv := newSrv(s)
	defer srv.Close()
	var d struct {
		Latest   string           `json:"latest"`
		Branches []*BranchSummary `json:"branches"`
	}
	get(t, srv, "/api/dashboard", &d)
	if d.Latest != ids[1] || len(d.Branches) != 1 || d.Branches[0].Runs != 2 || len(d.Branches[0].Trend) != 2 || d.Branches[0].Fixed != 1 || d.Branches[0].Review != 252 {
		t.Fatalf("dashboard %+v", d.Branches[0])
	}
	var rl struct {
		Total int           `json:"total"`
		Rules []RuleSummary `json:"rules"`
	}
	get(t, srv, "/api/rules?sort=hits&limit=1", &rl)
	if rl.Total != 2 || len(rl.Rules) != 1 || rl.Rules[0].ID != "R1" || rl.Rules[0].Stats == nil || rl.Rules[0].Stats.Runs != 2 || rl.Rules[0].Stats.Hits != 254 {
		t.Fatalf("rules by hits %+v", rl.Rules[0])
	}
	get(t, srv, "/api/rules?offset=1&limit=1", &rl)
	if len(rl.Rules) != 1 || rl.Rules[0].ID != "R2" || rl.Rules[0].Stats.Hidden != 1 {
		t.Fatalf("rules page 2 %+v", rl.Rules)
	}
	var c Comparison
	get(t, srv, "/api/compare?a="+ids[0]+"&b="+ids[1], &c)
	if len(c.New) != 251 || len(c.Fixed) != 1 || c.Unchanged != 1 || len(c.UnchangedList) != 1 || c.UnchangedList[0].ID != "x" {
		t.Fatalf("compare new %d fixed %d unchanged %d/%d", len(c.New), len(c.Fixed), c.Unchanged, len(c.UnchangedList))
	}
	get(t, srv, "/api/compare?a="+ids[0]+"&b="+ids[1]+"&limit=10", &c)
	if len(c.New) != 10 || !c.Truncated {
		t.Fatalf("compare limit: %d %v", len(c.New), c.Truncated)
	}
}

func newSrv(s *Server) *httptest.Server { return httptest.NewServer(s.Handler()) }

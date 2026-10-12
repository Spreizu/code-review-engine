package ui

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/report"
	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/runs"
)

func f(id, path string, line int) *findings.Finding {
	return &findings.Finding{ID: id, RuleID: "R1", Severity: "major", Status: "confirmed", Location: findings.Location{Path: path, StartLine: line, EndLine: line}}
}

func setup(t *testing.T) (*httptest.Server, []string) {
	root := t.TempDir()
	os.WriteFile(filepath.Join(root, "a.go"), []byte("package a\n\nfunc A() {\n\tpanic(1)\n}\n"), 0o644)
	st := runs.Store{Dir: filepath.Join(root, ".crev", "runs")}
	var ids []string
	reps := []*findings.Report{{Findings: []*findings.Finding{f("x", "a.go", 4), f("y", "a.go", 1)}}, {Findings: []*findings.Finding{f("x", "a.go", 4), f("z", "a.go", 3)}}}
	l, _ := st.LoadLedger("main")
	for i, rep := range reps {
		m := &runs.Meta{Branch: "main", Timestamp: time.Date(2026, 10, 1+i, 0, 0, 0, 0, time.UTC)}
		dir, err := st.Create(m)
		if err != nil {
			t.Fatal(err)
		}
		fh, _ := os.Create(filepath.Join(dir, "report.json"))
		report.JSON(fh, rep)
		fh.Close()
		m.Ledger = l.Apply(rep, runs.Point{Run: m.ID, Time: m.Timestamp}, nil, nil)
		m.Counts = runs.CountsOf(rep)
		st.Finish(m)
		ids = append(ids, m.ID)
	}
	st.SaveLedger(l)
	r := &rules.Rule{ID: "R1", Title: "No panic", Language: "go", Category: "bug", Severity: "major", Pack: "go", Message: "avoid panic"}
	r.Detection.Mode = "deterministic"
	r.Source.URL = "https://go.dev/doc/effective_go#panic"
	r2 := &rules.Rule{ID: "R2", Title: "Other", Language: "java", Category: "security", Severity: "critical", Pack: "java", AppliesTo: map[string]string{"java": ">=21"}}
	s := &Server{Root: root, Store: st, Rules: []*rules.Rule{r, r2}, Version: "test"}
	return httptest.NewServer(s.Handler()), ids
}

func get(t *testing.T, srv *httptest.Server, path string, v any) int {
	t.Helper()
	res, err := http.Get(srv.URL + path)
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	if v != nil {
		if err := json.NewDecoder(res.Body).Decode(v); err != nil {
			t.Fatalf("%s: %v", path, err)
		}
	}
	return res.StatusCode
}

func TestAPI(t *testing.T) {
	srv, ids := setup(t)
	defer srv.Close()
	res, _ := http.Get(srv.URL + "/")
	res.Body.Close()
	if res.StatusCode != 200 || !strings.HasPrefix(res.Header.Get("Content-Type"), "text/html") {
		t.Fatalf("index: %d", res.StatusCode)
	}
	var idx runs.Index
	if get(t, srv, "/api/runs", &idx); len(idx.Runs) != 2 || idx.Latest != ids[1] {
		t.Fatalf("runs: %+v", idx)
	}
	var rd runDetail
	if code := get(t, srv, "/api/runs/latest", &rd); code != 200 || len(rd.Findings) != 2 || rd.Meta.ID != ids[1] {
		t.Fatalf("run: %d %+v", code, rd)
	}
	var c Comparison
	get(t, srv, "/api/compare?a="+ids[0]+"&b="+ids[1], &c)
	if len(c.New) != 1 || c.New[0].ID != "z" || len(c.Fixed) != 1 || c.Fixed[0].ID != "y" || c.Unchanged != 1 {
		t.Fatalf("compare: %+v", c)
	}
	var l runs.Ledger
	if get(t, srv, "/api/ledger?branch=main", &l); len(l.Timeline) != 2 || l.Entries["y"].Status != runs.Fixed {
		t.Fatalf("ledger: %+v", l)
	}
	var rl struct {
		Total int           `json:"total"`
		Rules []RuleSummary `json:"rules"`
	}
	if get(t, srv, "/api/rules?language=java", &rl); rl.Total != 1 || rl.Rules[0].ID != "R2" {
		t.Fatalf("rules filter: %+v", rl)
	}
	if get(t, srv, "/api/rules?version=%3E%3D21", &rl); rl.Total != 1 {
		t.Fatalf("rules version filter: %+v", rl)
	}
	if get(t, srv, "/api/rules?q=panic", &rl); rl.Total != 1 || rl.Rules[0].ID != "R1" {
		t.Fatalf("rules search: %+v", rl)
	}
	var rule map[string]any
	if get(t, srv, "/api/rules/R1", &rule); !strings.Contains(rule["yaml"].(string), "id: R1") {
		t.Fatalf("rule yaml: %v", rule)
	}
	if get(t, srv, "/api/rules/NOPE", nil) != 404 {
		t.Fatal("unknown rule should 404")
	}
	var sn Snippet
	if get(t, srv, "/api/snippet?path=a.go&line=4", &sn); sn.Start != 1 || len(sn.Lines) != 6 || sn.Lines[3] != "\tpanic(1)" {
		t.Fatalf("snippet: %+v", sn)
	}
	for _, bad := range []string{"../etc/passwd", "/etc/passwd", "a/../../x"} {
		if code := get(t, srv, "/api/snippet?line=1&path="+bad, nil); code != 400 {
			t.Errorf("snippet %q: %d, want 400", bad, code)
		}
	}
	// DNS rebinding guard
	req, _ := http.NewRequest("GET", srv.URL+"/api/runs", nil)
	req.Host = "evil.example"
	if res, _ := http.DefaultClient.Do(req); res.Body.Close() != nil || res.StatusCode != 403 {
		t.Fatalf("foreign host: %d", res.StatusCode)
	}
	// read-only
	if res, _ := http.Post(srv.URL+"/api/runs", "application/json", nil); res.Body.Close() != nil || res.StatusCode != 405 {
		t.Fatalf("POST: %d", res.StatusCode)
	}
}

func TestBundleBudget(t *testing.T) {
	b, err := static.ReadFile("static/index.html")
	if err != nil {
		t.Fatal(err)
	}
	if len(b) > 150*1024 {
		t.Fatalf("UI bundle %d bytes exceeds the 150 KB budget", len(b))
	}
}

// The run view offers the hidden-findings toggle (off by default) and a reason filter for every
// hidden reason the CLI can write.
func TestHiddenToggle(t *testing.T) {
	b, _ := static.ReadFile("static/index.html")
	s := string(b)
	for _, want := range []string{`id="fh"`, "Show hidden", `["reason","Hidden reason"]`, "hidden_detail", "j/k", "crev-ignore-next-line", "aria-current", "pending_ai", "ai_rejected", "ai_uncertain", "ai_low_confidence", "shadow", "suppressed_config", "suppressed_inline", "crev_ignore"} {
		if !strings.Contains(s, want) {
			t.Errorf("index.html lacks %q", want)
		}
	}
}

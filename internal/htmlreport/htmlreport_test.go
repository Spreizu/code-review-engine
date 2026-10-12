package htmlreport

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/report"
	"github.com/elmo/code-review-engine/internal/runs"
)

func TestBuildRender(t *testing.T) {
	st := runs.Store{Dir: t.TempDir()}
	l, _ := st.LoadLedger("main")
	var last *runs.Meta
	for i, fs := range [][]*findings.Finding{
		{{ID: "a", RuleID: "R<1>", Severity: "major", Status: "confirmed", Message: "<script>x</script>", Location: findings.Location{Path: "a.go", StartLine: 1}}},
		{},
	} {
		rep := &findings.Report{Findings: fs}
		m := &runs.Meta{Branch: "main", Timestamp: time.Date(2026, 10, 1+i, 0, 0, 0, 0, time.UTC)}
		dir, _ := st.Create(m)
		f, _ := os.Create(filepath.Join(dir, "report.json"))
		report.JSON(f, rep)
		f.Close()
		m.Ledger = l.Apply(rep, runs.Point{Run: m.ID, Time: m.Timestamp}, nil, nil)
		st.Finish(m)
		last = m
	}
	st.SaveLedger(l)
	d, err := Build(st, "latest")
	if err != nil || d.Run.ID != last.ID || len(d.Fixed) != 1 || len(d.Timeline) != 2 || d.Lifecycle["fixed"] != 1 {
		t.Fatalf("%+v %v", d, err)
	}
	d2, _ := Build(st, "main:latest")
	var sb strings.Builder
	d2.Findings = []*findings.Finding{{RuleID: "R<1>", Severity: "major", Message: "<script>x</script>"}}
	if err := Render(&sb, d2); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(sb.String(), "<script>x") || !strings.Contains(sb.String(), "<svg") {
		t.Fatal("render must escape finding text and include the timeline")
	}
}

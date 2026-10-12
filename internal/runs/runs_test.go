package runs

import (
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/scope"
)

func fnd(id, rule, path string, line int, status string) *findings.Finding {
	return &findings.Finding{ID: id, RuleID: rule, Severity: "major", Category: "security", Status: status,
		Location: findings.Location{Path: path, StartLine: line}}
}

func rep(fs ...*findings.Finding) *findings.Report { return &findings.Report{Findings: fs} }

var t0 = time.Date(2026, 10, 10, 0, 0, 0, 0, time.UTC)

func pt(n int) Point {
	return Point{Run: "r" + string(rune('0'+n)), Commit: "c", Time: t0.Add(time.Duration(n) * time.Hour)}
}

func TestSanitizeBranch(t *testing.T) {
	for in, want := range map[string]string{"feature/x": "feature-x", "a b/../c": "a-b-..-c", "": "unknown", "..": "unknown", "rel-1.2": "rel-1.2"} {
		if got := SanitizeBranch(in); got != want {
			t.Errorf("%q: %q want %q", in, got, want)
		}
	}
}

func TestLedgerLifecycle(t *testing.T) {
	l := &Ledger{Branch: "main", Entries: map[string]*Entry{}}
	active := map[string]bool{"R1": true, "R2": true}
	full := scope.Full()
	// review-list policy: a pending_ai finding is not open (tracked as suppressed)
	lp := &Ledger{Branch: "main", Entries: map[string]*Entry{}}
	if d := lp.Apply(rep(fnd("P", "R2", "p.go", 1, "pending_ai")), pt(1), full, active); len(d.New) != 0 || len(d.Suppressed) != 1 {
		t.Fatalf("pending must not be open: %+v", d)
	}
	d := l.Apply(rep(fnd("A", "R1", "a.go", 3, "confirmed"), fnd("B", "R2", "b.go", 1, "confirmed")), pt(1), full, active)
	if len(d.New) != 2 || l.Entries["A"].Status != Open {
		t.Fatalf("run1 %+v", d)
	}
	// run 2: A moved lines (same fingerprint) and B gone in a full scan -> fixed
	d = l.Apply(rep(fnd("A", "R1", "a.go", 9, "confirmed")), pt(2), full, active)
	if len(d.Fixed) != 1 || l.Entries["B"].Status != Fixed || l.Entries["B"].FixedIn.Run != "r2" || l.Entries["A"].Line != 9 || len(d.New) != 0 {
		t.Fatalf("run2 %+v %+v", d, l.Entries["B"])
	}
	// run 3: B is back -> reopened
	d = l.Apply(rep(fnd("A", "R1", "a.go", 9, "confirmed"), fnd("B", "R2", "b.go", 1, "confirmed")), pt(3), full, active)
	if len(d.Reopened) != 1 || l.Entries["B"].Status != Reopened || l.Entries["B"].Reopened != 1 || l.Entries["B"].FixedIn != nil {
		t.Fatalf("run3 %+v", l.Entries["B"])
	}
	// run 4: diff scan touching neither file reports nothing: nothing may be marked fixed
	diff := &scope.Scope{Mode: "base", DiffContext: "hunk", Files: map[string][]scope.Range{"c.go": {{Start: 1, End: 2}}}, Deleted: map[string]bool{}}
	d = l.Apply(rep(), pt(4), diff, active)
	if len(d.Fixed) != 0 || d.NotEvaluated != 2 || l.Entries["A"].Status != Open {
		t.Fatalf("run4 diff must not fix out-of-scope findings: %+v", d)
	}
	// hunk-only diff on a.go still cannot prove A fixed (the finding may sit outside the hunks)
	diff.Files["a.go"] = []scope.Range{{Start: 1, End: 1}}
	if d = l.Apply(rep(), pt(5), diff, active); len(d.Fixed) != 0 {
		t.Fatalf("run5: %+v", d)
	}
	// diff-context=file on a.go can; a deleted b.go fixes B
	diff.DiffContext = "file"
	diff.Deleted["b.go"] = true
	if d = l.Apply(rep(), pt(6), diff, active); len(d.Fixed) != 2 {
		t.Fatalf("run6: %+v", d)
	}
	// rule disabled: absence proves nothing
	l.Apply(rep(fnd("C", "R3", "c.go", 1, "confirmed")), pt(7), full, map[string]bool{"R3": true})
	if d = l.Apply(rep(), pt(8), full, map[string]bool{"R1": true}); len(d.Fixed) != 0 || l.Entries["C"].Status != Open {
		t.Fatalf("inactive rule: %+v", d)
	}
	// suppression / AI rejection
	if d = l.Apply(rep(fnd("C", "R3", "c.go", 1, "suppressed")), pt(9), full, nil); len(d.Suppressed) != 1 || l.Entries["C"].Status != Suppressed {
		t.Fatalf("suppressed: %+v", l.Entries["C"])
	}
	if n := len(l.Timeline); n != 9 || l.Timeline[0].New != 2 || l.Timeline[1].Fixed != 1 {
		t.Fatalf("timeline: %+v", l.Timeline)
	}
	if ev := l.Entries["B"].Events; len(ev) != 4 || ev[0].Status != Open || ev[1].Status != Fixed || ev[2].Status != Reopened || ev[3].Status != Fixed {
		t.Fatalf("events: %+v", ev)
	}
}

func TestStoreIndexResolvePrune(t *testing.T) {
	st := Store{Dir: filepath.Join(t.TempDir(), "runs")}
	var ids []string
	for i := range 4 {
		m := &Meta{Branch: "feature/x", Timestamp: t0.Add(time.Duration(i) * 24 * time.Hour), Counts: Counts{Total: i}}
		dir, err := st.Create(m)
		if err != nil {
			t.Fatal(err)
		}
		if filepath.Base(filepath.Dir(dir)) != "feature-x" || len(m.ID) != len("20261010T000000Z-abcdef") {
			t.Fatalf("dir layout: %s %s", dir, m.ID)
		}
		_ = os.WriteFile(filepath.Join(dir, "report.json"), []byte(`{"findings":[]}`), 0o644)
		if err := st.Finish(m); err != nil {
			t.Fatal(err)
		}
		ids = append(ids, m.ID)
	}
	other := &Meta{Branch: "main", Timestamp: t0}
	st.Create(other)
	st.Finish(other)
	l, _ := st.LoadLedger("feature/x")
	l.Apply(rep(fnd("A", "R", "a", 1, "confirmed")), pt(1), nil, nil)
	if err := st.SaveLedger(l); err != nil {
		t.Fatal(err)
	}
	if m, err := st.Resolve("latest"); err != nil || m.ID != other.ID {
		t.Fatalf("latest: %v %v", m, err)
	}
	if m, err := st.Resolve("feature/x:latest"); err != nil || m.ID != ids[3] || len(m.Files) == 0 {
		t.Fatalf("branch latest: %+v %v", m, err)
	}
	if m, err := st.Resolve(ids[1][len(ids[1])-6:]); err != nil || m.ID != ids[1] {
		t.Fatalf("short id: %v", err)
	}
	if b, _ := os.ReadFile(filepath.Join(st.Dir, "LATEST")); string(b) != "main/"+other.ID+"\n" {
		t.Fatalf("LATEST: %q", b)
	}
	removed, err := st.Prune(2, 0, t0.Add(10*24*time.Hour))
	if err != nil || len(removed) != 2 || removed[0] != ids[0] {
		t.Fatalf("prune keep=2: %v %v", removed, err)
	}
	// max age prunes everything old except each branch's latest run
	removed, _ = st.Prune(0, 24*time.Hour, t0.Add(10*24*time.Hour))
	if len(removed) != 1 || removed[0] != ids[2] {
		t.Fatalf("prune age: %v", removed)
	}
	if _, err := os.Stat(st.LedgerPath("feature/x")); err != nil {
		t.Fatal("history.json must survive pruning")
	}
	idx, _ := st.Index()
	if len(idx.Runs) != 2 {
		t.Fatalf("index after prune: %+v", idx.Runs)
	}
	if _, err := st.Resolve(ids[0]); err == nil {
		t.Fatal("pruned run should not resolve")
	}
}

func TestCountsOfHidden(t *testing.T) {
	rep := &findings.Report{Findings: []*findings.Finding{{Status: "confirmed"}, {Status: "pending_ai", HiddenReason: "pending_ai"}, {Status: "shadow", HiddenReason: "shadow"}, {Status: "pending_ai", HiddenReason: "pending_ai"}}}
	c := CountsOf(rep)
	if c.Hidden["pending_ai"] != 2 || c.Hidden["shadow"] != 1 || len(c.Hidden) != 2 {
		t.Fatalf("hidden counts = %v", c.Hidden)
	}
}

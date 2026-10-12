package report

import (
	"testing"

	"github.com/elmo/code-review-engine/internal/findings"
)

func TestReviewListPolicy(t *testing.T) {
	o := GateOptions{FailOn: "critical", MinConfidence: "medium", ReviewConfidence: "high"}
	f := func(status, conf string) *findings.Finding {
		return &findings.Finding{Status: status, Confidence: conf, Severity: "critical", Category: "security"}
	}
	for _, c := range []struct {
		f      *findings.Finding
		hidden string
		gates  bool
	}{
		{f("confirmed", "high"), "", true},
		{f("ai_confirmed", "high"), "", true},
		{f("ai_confirmed", "medium"), "rejected", false}, // below review confidence: never listed, never gates
		{f("ai_uncertain", "low"), "rejected", false},
		{f("ai_rejected", "high"), "rejected", false},
		{f("pending_ai", ""), "pending", false},
		{f("shadow", "high"), "shadow", false},
		{f("suppressed", "high"), "suppressed", false},
	} {
		if h := Hidden(c.f, o); h != c.hidden {
			t.Errorf("%s/%s: hidden=%q want %q", c.f.Status, c.f.Confidence, h, c.hidden)
		}
		if g := Gating(c.f, o); g != c.gates {
			t.Errorf("%s/%s: gating=%v want %v", c.f.Status, c.f.Confidence, g, c.gates)
		}
		if Listed(c.f, o) != (c.hidden == "") {
			t.Errorf("%s/%s: listed by default", c.f.Status, c.f.Confidence)
		}
	}
	rep := &findings.Report{Findings: []*findings.Finding{f("ai_rejected", "high"), f("pending_ai", ""), f("shadow", "")}}
	if n := len(Visible(rep, o)); n != 0 {
		t.Fatalf("default review list must hide rejected/pending/shadow, got %d", n)
	}
	o.ShowRejected, o.ShowPending, o.ShowShadow = true, true, true
	if n := len(Visible(rep, o)); n != 3 {
		t.Fatalf("--show-* flags list them, got %d", n)
	}
}

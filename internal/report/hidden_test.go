package report

import (
	"strings"
	"testing"

	"github.com/elmo/code-review-engine/internal/findings"
)

func hiddenFixture() *findings.Report {
	return &findings.Report{Findings: []*findings.Finding{
		{RuleID: "A", Status: "confirmed", Severity: "major", Confidence: "high"},
		{RuleID: "B", Status: "pending_ai", Severity: "major", Confidence: "low"},
		{RuleID: "C", Status: "ai_rejected", Severity: "major", AI: &findings.AI{Verdict: "rejected", Confidence: "high", Rationale: "constant input"}},
		{RuleID: "D", Status: "ai_uncertain", Severity: "minor", AI: &findings.AI{Verdict: "uncertain", Confidence: "low"}},
		{RuleID: "E", Status: "ai_confirmed", Severity: "minor", Confidence: "medium"},
		{RuleID: "F", Status: "shadow", Severity: "minor", HiddenReason: "shadow", HiddenDetail: "rule quarantined: 3 FPs"},
		{RuleID: "G", Status: "suppressed", SuppressedBy: &findings.SuppressedBy{Kind: "config", Tool: "eslint", ID: "no-eval", Source: ".eslintrc"}},
		{RuleID: "H", Status: "suppressed", SuppressedBy: &findings.SuppressedBy{Kind: "inline", Tool: "eslint", ID: "no-eval", Source: "a.js:3"}},
		{RuleID: "I", Status: "suppressed", SuppressedBy: &findings.SuppressedBy{Kind: "crev-ignore", Tool: "crev", ID: "I", Source: "a.js:9"}},
	}}
}

func TestAnnotateHiddenReasons(t *testing.T) {
	rep := hiddenFixture()
	o := GateOptions{FailOn: "critical", PendingDetail: "AI step is off"}
	Annotate(rep, o)
	want := map[string]string{"A": "", "B": HidPending, "C": HidRejected, "D": HidUncertain, "E": HidLowConf, "F": HidShadow,
		"G": HidSupConfig, "H": HidSupInline, "I": HidSupCrevIgnore}
	for _, f := range rep.Findings {
		if f.HiddenReason != want[f.RuleID] {
			t.Errorf("%s: hidden_reason %q, want %q", f.RuleID, f.HiddenReason, want[f.RuleID])
		}
		if f.HiddenReason != "" && f.HiddenDetail == "" {
			t.Errorf("%s: no hidden_detail", f.RuleID)
		}
	}
	if rep.Findings[1].HiddenDetail != "AI step is off" || rep.Findings[5].HiddenDetail != "rule quarantined: 3 FPs" {
		t.Errorf("details: %q / %q", rep.Findings[1].HiddenDetail, rep.Findings[5].HiddenDetail)
	}
	if len(rep.Hidden) != 8 || rep.Hidden[HidPending] != 1 {
		t.Errorf("rep.Hidden = %v", rep.Hidden)
	}
	if l := HiddenLine(rep, o); !strings.Contains(l, "8 finding(s) hidden") || !strings.Contains(l, "1 pending AI confirmation (AI step is off)") {
		t.Errorf("HiddenLine = %q", l)
	}
	// Re-annotating with a lower review confidence lists E again.
	o.ReviewConfidence = "medium"
	Annotate(rep, o)
	if rep.Findings[4].HiddenReason != "" || rep.Findings[4].HiddenDetail != "" {
		t.Errorf("E still hidden: %+v", rep.Findings[4])
	}
}

func TestShowHidden(t *testing.T) {
	rep := hiddenFixture()
	count := func(v string) int {
		m, err := ParseShowHidden(v)
		if err != nil {
			t.Fatal(err)
		}
		return len(Visible(rep, GateOptions{ShowHidden: m}))
	}
	if n := count("false"); n != 1 {
		t.Errorf("default: %d listed", n)
	}
	if n := count(""); n != 9 {
		t.Errorf("--show-hidden: %d listed", n)
	}
	if n := count("pending_ai,crev_ignore"); n != 3 {
		t.Errorf("reasons: %d listed", n)
	}
	if n := count("rejected"); n != 4 {
		t.Errorf("group rejected: %d listed", n)
	}
	if _, err := ParseShowHidden("nope"); err == nil {
		t.Error("unknown reason accepted")
	}
}

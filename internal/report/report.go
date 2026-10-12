// Package report renders findings (text, json, sarif, md) and computes the CI gate.
package report

import (
	"encoding/json"
	"fmt"
	"io"
	"maps"
	"slices"
	"strings"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/rules"
)

// GateOptions mirror .crev.yaml / flags: the CI gate and which findings are listed.
type GateOptions struct {
	FailOn        string // info|minor|major|critical|none (default critical)
	MinConfidence string // ai_confirmed findings need at least this AI confidence to gate
	StrictPending bool   // pending_ai / ai_uncertain also gate
	// ReviewConfidence: ai_confirmed findings need at least this AI confidence to be in the
	// review list (default high). See findings.InReview.
	ReviewConfidence string
	// ShowSuppressed lists suppressed findings (project linter config, inline disables,
	// crev-ignore) in text/Markdown output; JSON always carries them and SARIF as suppressions.
	ShowSuppressed bool
	ShowPending    bool // list pending_ai findings (awaiting AI confirmation)
	ShowRejected   bool // list ai_rejected, ai_uncertain and below-threshold ai_confirmed findings
	ShowShadow     bool // list findings of quarantined (shadow) rules, when the scan kept them
	// ShowHidden lists hidden findings by reason (HiddenReasons), group (pending, rejected,
	// suppressed, shadow) or "all" (--show-hidden[=reason,...]).
	ShowHidden map[string]bool
	// PendingDetail explains why pending_ai findings are still pending (no AI configured,
	// exported for the Cursor skill, ...); copied to hidden_detail.
	PendingDetail string
}

// Hidden reasons (findings.Finding.HiddenReason), in display order.
const (
	HidPending       = "pending_ai"
	HidRejected      = "ai_rejected"
	HidUncertain     = "ai_uncertain"
	HidLowConf       = "ai_low_confidence"
	HidShadow        = "shadow"
	HidSupConfig     = "suppressed_config"
	HidSupInline     = "suppressed_inline"
	HidSupCrevIgnore = "crev_ignore"
)

// HiddenReasons lists every hidden reason in display order.
var HiddenReasons = []string{HidPending, HidRejected, HidUncertain, HidLowConf, HidShadow, HidSupConfig, HidSupInline, HidSupCrevIgnore}

var reasonGroup = map[string]string{HidPending: "pending", HidRejected: "rejected", HidUncertain: "rejected", HidLowConf: "rejected",
	HidShadow: "shadow", HidSupConfig: "suppressed", HidSupInline: "suppressed", HidSupCrevIgnore: "suppressed"}

// ReasonLabel is the short human label of a hidden reason.
var ReasonLabel = map[string]string{HidPending: "pending AI confirmation", HidRejected: "rejected by AI", HidUncertain: "AI uncertain",
	HidLowConf: "AI-confirmed below review confidence", HidShadow: "quarantined rule", HidSupConfig: "suppressed by project linter config",
	HidSupInline: "suppressed by inline disable comment", HidSupCrevIgnore: "suppressed by crev-ignore"}

// HiddenReason returns the fine-grained reason a finding is not in the review list ("" = listed).
func HiddenReason(f *findings.Finding, o GateOptions) string {
	if findings.InReview(f, o.ReviewConfidence) {
		return ""
	}
	switch f.Status {
	case "suppressed":
		if f.SuppressedBy != nil {
			switch f.SuppressedBy.Kind {
			case "inline":
				return HidSupInline
			case "crev-ignore":
				return HidSupCrevIgnore
			}
		}
		return HidSupConfig
	case "pending_ai":
		return HidPending
	case "shadow":
		return HidShadow
	case "ai_rejected":
		return HidRejected
	case "ai_uncertain":
		return HidUncertain
	}
	return HidLowConf
}

// Annotate sets hidden_reason / hidden_detail on every finding and rep.Hidden counts. Call it
// before writing any output or recording a run, so reports carry why each finding was hidden.
func Annotate(rep *findings.Report, o GateOptions) {
	rep.Hidden = nil
	for _, f := range rep.Findings {
		r := HiddenReason(f, o)
		prev := f.HiddenReason
		f.HiddenReason = r
		if r == "" {
			f.HiddenDetail = ""
			continue
		}
		if rep.Hidden == nil {
			rep.Hidden = map[string]int{}
		}
		rep.Hidden[r]++
		switch r {
		case HidPending:
			f.HiddenDetail = o.PendingDetail
			if f.HiddenDetail == "" {
				f.HiddenDetail = "ai-confirm rule: waiting for an AI verdict"
			}
		case HidRejected, HidUncertain:
			if f.AI != nil {
				f.HiddenDetail = fmt.Sprintf("AI verdict %s (confidence %s)", f.AI.Verdict, f.AI.Confidence)
				if f.AI.Rationale != "" {
					f.HiddenDetail += ": " + f.AI.Rationale
				}
			}
		case HidLowConf:
			rc := o.ReviewConfidence
			if rc == "" {
				rc = "high"
			}
			f.HiddenDetail = fmt.Sprintf("AI confirmed with %s confidence; the review list needs %s (ai.review_confidence / --review-confidence)", f.Confidence, rc)
		case HidShadow:
			if prev != HidShadow || f.HiddenDetail == "" {
				f.HiddenDetail = "rule is quarantined (shadow): it runs and is logged but never gates or lists by default"
			}
		default:
			if sb := f.SuppressedBy; sb != nil {
				f.HiddenDetail = fmt.Sprintf("%s:%s (%s)", sb.Tool, sb.ID, sb.Source)
			}
		}
	}
}

// ParseShowHidden parses a --show-hidden value: "" / "true" / "all" = every reason, otherwise a
// comma list of reasons or groups (pending, rejected, suppressed, shadow).
func ParseShowHidden(v string) (map[string]bool, error) {
	out := map[string]bool{}
	v = strings.TrimSpace(v)
	if v == "" || v == "true" || v == "all" {
		out["all"] = true
		return out, nil
	}
	if v == "false" {
		return nil, nil
	}
	for _, p := range strings.Split(v, ",") {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		if _, ok := reasonGroup[p]; !ok && !slices.Contains([]string{"pending", "rejected", "suppressed", "shadow", "all"}, p) {
			return nil, fmt.Errorf("unknown hidden reason %q (want all, pending, rejected, suppressed, shadow or one of %s)", p, strings.Join(HiddenReasons, ", "))
		}
		out[p] = true
	}
	return out, nil
}

// Gating reports whether one finding blocks CI.
func Gating(f *findings.Finding, o GateOptions) bool {
	if f.Category == "simplification" || f.Category == "test" {
		return false // advisory simplification layer: never gates CI
	}
	if o.FailOn == "none" || rules.SeverityRank(f.Severity) < rules.SeverityRank(o.FailOn) {
		return false
	}
	switch f.Status {
	case "confirmed":
		return true
	case "ai_confirmed":
		// Only what the review list shows can gate: both thresholds apply.
		return findings.ConfidenceAtLeast(f.Confidence, o.MinConfidence) && findings.InReview(f, o.ReviewConfidence)
	case "pending_ai", "ai_uncertain":
		return o.StrictPending
	}
	return false
}

// Gate counts gating findings.
func Gate(rep *findings.Report, o GateOptions) int {
	n := 0
	for _, f := range rep.Findings {
		if Gating(f, o) {
			n++
		}
	}
	return n
}

// Hidden classifies a finding that is not in the review list ("" when it is listed by default).
func Hidden(f *findings.Finding, o GateOptions) string {
	if findings.InReview(f, o.ReviewConfidence) {
		return ""
	}
	switch f.Status {
	case "suppressed":
		return "suppressed"
	case "pending_ai":
		return "pending"
	case "shadow":
		return "shadow"
	}
	return "rejected" // ai_rejected, ai_uncertain, ai_confirmed below the review confidence
}

// Listed reports whether a finding is shown in text/Markdown/SARIF output under o.
func Listed(f *findings.Finding, o GateOptions) bool {
	if r := HiddenReason(f, o); r != "" && (o.ShowHidden["all"] || o.ShowHidden[r] || o.ShowHidden[reasonGroup[r]]) {
		return true
	}
	switch Hidden(f, o) {
	case "":
		return true
	case "suppressed":
		return o.ShowSuppressed
	case "pending":
		return o.ShowPending
	case "shadow":
		return o.ShowShadow
	default:
		return o.ShowRejected
	}
}

// Visible returns the listed findings (JSON keeps everything, with status, for audit).
func Visible(rep *findings.Report, o GateOptions) []*findings.Finding {
	var out []*findings.Finding
	for _, f := range rep.Findings {
		if Listed(f, o) {
			out = append(out, f)
		}
	}
	return out
}

// Counts by status and severity.
func Counts(fs []*findings.Finding) (bySev, byStatus map[string]int) {
	bySev, byStatus = map[string]int{}, map[string]int{}
	for _, f := range fs {
		bySev[f.Severity]++
		byStatus[f.Status]++
	}
	return
}

// JSON writes the native report.
func JSON(w io.Writer, rep *findings.Report) error {
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	enc.SetEscapeHTML(false)
	return enc.Encode(rep)
}

// Text writes a human summary (everything is reported; gating findings are marked).
func Text(w io.Writer, rep *findings.Report, o GateOptions) {
	fs := Visible(rep, o)
	for _, f := range fs {
		mark := " "
		if Gating(f, o) {
			mark = "✖"
		}
		fmt.Fprintf(w, "%s %s:%d:%d %s [%s] %s (%s)\n", mark, f.Location.Path, f.Location.StartLine, f.Location.StartColumn, strings.ToUpper(f.Severity), f.RuleID, f.Message, f.Status)
		if r := HiddenReason(f, o); r != "" {
			d := ""
			if f.HiddenDetail != "" && r != HidRejected && r != HidUncertain {
				d = ": " + f.HiddenDetail
			}
			fmt.Fprintf(w, "    hidden (%s)%s\n", r, d)
		}
		if f.AI != nil && f.AI.Rationale != "" {
			fmt.Fprintf(w, "    ai(%s/%s): %s\n", f.AI.Verdict, f.AI.Confidence, f.AI.Rationale)
		}
		if len(f.AssumedVersions) > 0 {
			fmt.Fprintf(w, "    versions assumed latest: %s\n", strings.Join(f.AssumedVersions, ", "))
		}
		if f.SuppressedBy != nil {
			fmt.Fprintf(w, "    suppressed by %s %s:%s (%s)\n", f.SuppressedBy.Kind, f.SuppressedBy.Tool, f.SuppressedBy.ID, f.SuppressedBy.Source)
		}
		fmt.Fprintf(w, "    %s\n", f.Source.URL)
	}
	sev, st := Counts(fs)
	fmt.Fprintf(w, "\n%d findings (critical %d, major %d, minor %d, info %d) | status: %s | gating (fail_on=%s): %d\n",
		len(fs), sev["critical"], sev["major"], sev["minor"], sev["info"], kv(st), o.FailOn, Gate(rep, o))
	if l := ScopeLine(rep); l != "" {
		fmt.Fprintln(w, l)
	}
	if l := HiddenLine(rep, o); l != "" {
		fmt.Fprintln(w, l)
	}
	for _, e := range rep.Errors {
		fmt.Fprintln(w, "error:", e)
	}
}

// HiddenLine summarises findings kept out of the review list and why ("" when none).
func HiddenLine(rep *findings.Report, o GateOptions) string {
	by := map[string]int{}
	for _, f := range rep.Findings {
		if r := HiddenReason(f, o); r != "" && !Listed(f, o) {
			by[r]++
		}
	}
	shadow := 0
	for _, n := range rep.Shadow {
		shadow += n
	}
	if by[HidShadow] == 0 && shadow > 0 && !o.ShowShadow && !o.ShowHidden["all"] && !o.ShowHidden["shadow"] {
		kept := 0
		for _, f := range rep.Findings {
			if f.Status == "shadow" {
				kept++
			}
		}
		if kept == 0 {
			by[HidShadow] = shadow
		}
	}
	if len(by) == 0 {
		return ""
	}
	var parts []string
	total := 0
	for _, r := range HiddenReasons {
		if n := by[r]; n > 0 {
			total += n
			p := fmt.Sprintf("%d %s", n, ReasonLabel[r])
			if r == HidPending && o.PendingDetail != "" {
				p += " (" + o.PendingDetail + ")"
			}
			parts = append(parts, p)
		}
	}
	return fmt.Sprintf("%d finding(s) hidden from the review list: %s; list them with --show-hidden or --show-hidden=<reason,...>", total, strings.Join(parts, "; "))
}

// ScopeLine describes a diff scope ("" for full scans).
func ScopeLine(rep *findings.Report) string {
	s := rep.Scope
	if !s.IsDiff() {
		return ""
	}
	desc := s.Mode
	switch s.Mode {
	case "base":
		desc = fmt.Sprintf("base %s...%s (merge-base %.12s)", s.Base, s.Head, s.MergeBase)
	case "commits":
		desc = fmt.Sprintf("commits %s..%s", s.Base, s.Head)
	}
	return fmt.Sprintf("scope: %s, diff-context %s, %d changed file(s); %d finding(s) outside the diff not reported",
		desc, s.DiffContext, s.ChangedFiles, rep.Stats["out_of_scope"])
}

// Markdown writes a CI job summary.
func Markdown(w io.Writer, rep *findings.Report, o GateOptions) {
	fs := Visible(rep, o)
	sev, st := Counts(fs)
	fmt.Fprintf(w, "## crev\n\n**%d findings** · critical %d · major %d · minor %d · info %d · gating (fail_on=%s): **%d**\n\nStatus: %s\n\n",
		len(fs), sev["critical"], sev["major"], sev["minor"], sev["info"], o.FailOn, Gate(rep, o), kv(st))
	if l := ScopeLine(rep); l != "" {
		fmt.Fprintf(w, "_%s_\n\n", l)
	}
	if l := HiddenLine(rep, o); l != "" {
		fmt.Fprintf(w, "_%s_\n\n", l)
	}
	if len(fs) == 0 {
		return
	}
	fmt.Fprintln(w, "| | Severity | Rule | Location | Message | Status |\n|---|---|---|---|---|---|")
	for _, f := range fs {
		mark := ""
		if Gating(f, o) {
			mark = "✖"
		}
		fmt.Fprintf(w, "| %s | %s | [%s](%s) | `%s:%d` | %s | %s |\n", mark, f.Severity, f.RuleID, f.Source.URL, f.Location.Path, f.Location.StartLine,
			strings.ReplaceAll(f.Message, "|", "\\|"), f.Status)
	}
}

func kv(m map[string]int) string {
	keys := slices.Sorted(maps.Keys(m))
	var parts []string
	for _, k := range keys {
		parts = append(parts, fmt.Sprintf("%s %d", k, m[k]))
	}
	if len(parts) == 0 {
		return "-"
	}
	return strings.Join(parts, ", ")
}

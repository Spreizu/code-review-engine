package report

import (
	"encoding/json"
	"fmt"
	"io"
	"maps"
	"slices"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/rules"
)

var sarifLevel = map[string]string{"critical": "error", "major": "warning", "minor": "warning", "info": "note"}
var securitySeverity = map[string]string{"critical": "9.0", "major": "7.0", "minor": "4.0", "info": "1.0"}

// SARIF writes SARIF 2.1.0 (PLAN.md §9 mapping).
func SARIF(w io.Writer, rep *findings.Report, byID map[string]*rules.Rule, version string, o GateOptions) error {
	// Review list plus suppressed findings (as SARIF suppressions); pending/rejected/shadow
	// findings are only included when explicitly requested.
	so := o
	so.ShowSuppressed = true
	fs := Visible(rep, so)
	used := map[string]bool{}
	for _, f := range fs {
		used[f.RuleID] = true
	}
	ids := slices.Sorted(maps.Keys(used))
	index := map[string]int{}
	var driverRules []map[string]any
	for i, id := range ids {
		index[id] = i
		r := byID[id]
		if r == nil {
			driverRules = append(driverRules, map[string]any{"id": id})
			continue
		}
		props := map[string]any{"tags": tags(r), "docVersion": r.Source.DocVersion, "detectionMode": r.Detection.Mode, "pack": r.Pack}
		if r.Kind == "security" {
			props["security-severity"] = securitySeverity[r.Severity]
		}
		driverRules = append(driverRules, map[string]any{
			"id": id, "name": r.Title, "shortDescription": map[string]string{"text": r.Title},
			"fullDescription": map[string]string{"text": r.Message}, "helpUri": r.Source.URL,
			"defaultConfiguration": map[string]string{"level": sarifLevel[r.Severity]}, "properties": props,
		})
	}
	results := []map[string]any{}
	for _, f := range fs {
		props := map[string]any{"severity": f.Severity, "confidence": f.Confidence, "status": f.Status, "detectionMode": f.DetectionMode,
			"appliedVersions": f.AppliedVersions, "source": f.Source}
		if len(f.AssumedVersions) > 0 {
			props["assumedVersions"] = f.AssumedVersions
		}
		if f.AI != nil {
			props["ai"] = f.AI
		}
		if f.Kind == "security" {
			props["security-severity"] = securitySeverity[f.Severity]
		}
		if v := f.Vuln; v != nil {
			props["vuln"] = v
			if v.CVSSScore > 0 {
				props["security-severity"] = fmt.Sprintf("%.1f", v.CVSSScore)
			}
		}
		endLine, endCol := f.Location.EndLine, f.Location.EndColumn
		if endLine < f.Location.StartLine {
			endLine = f.Location.StartLine
		}
		region := map[string]any{"startLine": max1(f.Location.StartLine), "startColumn": max1(f.Location.StartColumn), "endLine": max1(endLine)}
		if endCol > 0 {
			region["endColumn"] = endCol
		}
		res := map[string]any{
			"ruleId": f.RuleID, "ruleIndex": index[f.RuleID], "level": sarifLevel[f.Severity],
			"message": map[string]string{"text": f.Message},
			"locations": []any{map[string]any{"physicalLocation": map[string]any{
				"artifactLocation": map[string]string{"uri": f.Location.Path, "uriBaseId": "%SRCROOT%"}, "region": region}}},
			"partialFingerprints": map[string]string{"crev/v1": f.ID},
			"properties":          props,
		}
		if f.Status == "suppressed" {
			sup := map[string]string{"kind": "inSource"}
			if sb := f.SuppressedBy; sb != nil {
				if sb.Kind == "config" {
					sup["kind"] = "external"
				}
				sup["justification"] = fmt.Sprintf("%s %s:%s (%s)", sb.Kind, sb.Tool, sb.ID, sb.Source)
			}
			res["suppressions"] = []any{sup}
		}
		results = append(results, res)
	}
	doc := map[string]any{
		"$schema": "https://json.schemastore.org/sarif-2.1.0.json",
		"version": "2.1.0",
		"runs": []any{map[string]any{
			"tool": map[string]any{"driver": map[string]any{"name": "crev", "version": version,
				"informationUri": "https://github.com/elmo/code-review-engine", "rules": driverRules}},
			"originalUriBaseIds": map[string]any{"%SRCROOT%": map[string]string{"uri": "file://" + rep.Root + "/"}},
			"results":            results,
			"properties":         map[string]any{"facts": rep.Units},
		}},
	}
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	enc.SetEscapeHTML(false)
	return enc.Encode(doc)
}

func tags(r *rules.Rule) []string {
	t := []string{r.Kind, r.Category}
	if r.Framework != "" {
		t = append(t, r.Framework)
	}
	if r.Kind == "security" {
		t = append(t, "security")
	}
	var out []string
	for i, x := range t { // distinct, order kept
		if x != "" && !slices.Contains(t[:i], x) {
			out = append(out, x)
		}
	}
	return out
}

func max1(n int) int {
	if n < 1 {
		return 1
	}
	return n
}

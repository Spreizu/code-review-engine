// Package feedback records false-positive reports (`crev feedback fp <fingerprint>`), turns
// them into suppressions of the reported findings, quarantines (shadow mode) rules whose false
// positives reach a threshold, and writes regression-example stubs for fixing the rule.
//
// Layout under <state_dir>/feedback/ (commit it to share verdicts with the team):
//
//	fp.jsonl                 one Record per line (append-only; `undo` rewrites it)
//	regressions/<RULE>.yaml  must-not-match example stubs (examples.regressions format)
//
// Quarantine is keyed by rule id AND rule version: once a rule is fixed (rule_version bumped)
// its old false-positive records no longer count and the rule leaves shadow mode by itself.
package feedback

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	"gopkg.in/yaml.v3"

	"github.com/elmo/code-review-engine/internal/findings"
)

// DefaultThreshold is the number of distinct false-positive findings (same rule version)
// that demotes a rule to shadow mode.
const DefaultThreshold = 3

// Record is one false-positive verdict.
type Record struct {
	ID          string `json:"id"` // finding fingerprint
	RuleID      string `json:"rule_id"`
	RuleVersion int    `json:"rule_version"`
	Path        string `json:"path"`
	Line        int    `json:"line"`
	Snippet     string `json:"snippet,omitempty"`
	Reason      string `json:"reason,omitempty"`
	Run         string `json:"run,omitempty"`
	At          string `json:"at"`
}

// Store is the feedback directory.
type Store struct{ Dir string }

func (s Store) fpPath() string { return filepath.Join(s.Dir, "fp.jsonl") }

// Load returns all records (none when the file does not exist).
func (s Store) Load() ([]Record, error) {
	f, err := os.Open(s.fpPath())
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var out []Record
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1<<20), 1<<20)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		var r Record
		if err := json.Unmarshal([]byte(line), &r); err != nil {
			return nil, fmt.Errorf("%s: %w", s.fpPath(), err)
		}
		out = append(out, r)
	}
	return out, sc.Err()
}

// Add appends a record for f (idempotent per fingerprint) and reports whether it was new.
func (s Store) Add(f *findings.Finding, reason, run string, now time.Time) (Record, bool, error) {
	recs, err := s.Load()
	if err != nil {
		return Record{}, false, err
	}
	for _, r := range recs {
		if r.ID == f.ID {
			return r, false, nil
		}
	}
	r := Record{ID: f.ID, RuleID: f.RuleID, RuleVersion: f.RuleVersion, Path: f.Location.Path, Line: f.Location.StartLine,
		Snippet: f.Snippet, Reason: reason, Run: run, At: now.UTC().Format(time.RFC3339)}
	if err := os.MkdirAll(s.Dir, 0o755); err != nil {
		return r, false, err
	}
	fh, err := os.OpenFile(s.fpPath(), os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return r, false, err
	}
	defer fh.Close()
	b, _ := json.Marshal(r)
	_, err = fh.Write(append(b, '\n'))
	return r, true, err
}

// Remove deletes the records whose fingerprint starts with prefix; returns how many.
func (s Store) Remove(prefix string) (int, error) {
	recs, err := s.Load()
	if err != nil {
		return 0, err
	}
	var keep []string
	n := 0
	for _, r := range recs {
		if strings.HasPrefix(r.ID, prefix) {
			n++
			continue
		}
		b, _ := json.Marshal(r)
		keep = append(keep, string(b))
	}
	if n == 0 {
		return 0, nil
	}
	data := strings.Join(keep, "\n")
	if data != "" {
		data += "\n"
	}
	return n, os.WriteFile(s.fpPath(), []byte(data), 0o644)
}

// Counts returns distinct false-positive findings per rule, counting only records made against
// the rule's current version (ruleVersion lookup; unknown rules count every record).
func Counts(recs []Record, ruleVersion func(string) int) map[string]int {
	out := map[string]int{}
	for _, r := range recs {
		if v := ruleVersion(r.RuleID); v != 0 && r.RuleVersion != v {
			continue
		}
		out[r.RuleID]++
	}
	return out
}

// Shadow returns the rules demoted to shadow mode (rule id -> reason).
func Shadow(recs []Record, threshold int, ruleVersion func(string) int) map[string]string {
	if threshold <= 0 {
		threshold = DefaultThreshold
	}
	out := map[string]string{}
	for id, n := range Counts(recs, ruleVersion) {
		if n >= threshold {
			out[id] = fmt.Sprintf("crev feedback: %d false positive(s) reported (threshold %d)", n, threshold)
		}
	}
	return out
}

// Apply marks findings that were reported as false positives as suppressed (kind "feedback").
func Apply(rep *findings.Report, recs []Record, source string) int {
	ids := map[string]bool{}
	for _, r := range recs {
		ids[r.ID] = true
	}
	n := 0
	for _, f := range rep.Findings {
		if ids[f.ID] && f.Status != "suppressed" {
			f.Status = "suppressed"
			f.SuppressedBy = &findings.SuppressedBy{Kind: "feedback", Tool: "crev", ID: f.RuleID, Source: source}
			rep.Stats["suppressed_feedback"]++
			n++
		}
	}
	return n
}

// Stub is the regressions/<RULE>.yaml file: paste its regressions into the rule
// (tools/rulegen spec fp=..., or examples.regressions of a pack / .crev/rules patch) after
// trimming the code to the smallest snippet that still reproduced the false positive.
type Stub struct {
	Rule        string      `yaml:"rule"`
	RuleVersion int         `yaml:"rule_version"`
	Regressions []StubEntry `yaml:"regressions"`
}

// StubEntry mirrors rules.Regression plus provenance.
type StubEntry struct {
	Code        string `yaml:"code"`
	Path        string `yaml:"path,omitempty"`
	Note        string `yaml:"note,omitempty"`
	Fingerprint string `yaml:"fingerprint"`
}

// WriteStub adds (or keeps) the regression example for r, cutting the code from the file
// under root: the whole file when short, otherwise ±context lines around the finding.
func (s Store) WriteStub(root string, r Record, context int) (string, error) {
	dir := filepath.Join(s.Dir, "regressions")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	p := filepath.Join(dir, r.RuleID+".yaml")
	var st Stub
	if b, err := os.ReadFile(p); err == nil {
		if err := yaml.Unmarshal(b, &st); err != nil {
			return "", fmt.Errorf("%s: %w", p, err)
		}
	}
	st.Rule, st.RuleVersion = r.RuleID, r.RuleVersion
	if slices.ContainsFunc(st.Regressions, func(e StubEntry) bool { return e.Fingerprint == r.ID }) {
		return p, nil
	}
	code := r.Snippet
	if b, err := os.ReadFile(filepath.Join(root, r.Path)); err == nil {
		lines := strings.Split(string(b), "\n")
		if len(lines) > 4*context {
			lo, hi := max(0, r.Line-1-context), min(len(lines), r.Line+context)
			lines = lines[lo:hi]
		}
		code = strings.Join(lines, "\n")
	}
	if !strings.HasSuffix(code, "\n") {
		code += "\n"
	}
	note := "false positive reported with crev feedback fp"
	if r.Reason != "" {
		note += ": " + r.Reason
	}
	st.Regressions = append(st.Regressions, StubEntry{Code: code, Path: r.Path, Note: note, Fingerprint: r.ID})
	var sb strings.Builder
	sb.WriteString("# Regression stub written by `crev feedback fp`. Trim each code block to the smallest snippet that\n")
	sb.WriteString("# still produced the false positive, fix the rule, and move the entries into the rule's\n")
	sb.WriteString("# examples.regressions (tools/rulegen spec fp=[...] or a .crev/rules patch); rulecheck then keeps\n")
	sb.WriteString("# them from matching again.\n")
	enc := yaml.NewEncoder(&sb)
	enc.SetIndent(2)
	if err := enc.Encode(st); err != nil {
		return "", err
	}
	return p, os.WriteFile(p, []byte(sb.String()), 0o644)
}

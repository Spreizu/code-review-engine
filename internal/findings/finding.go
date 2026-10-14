// Package findings defines the native finding model (schemas/finding.schema.json).
package findings

import (
	"crypto/sha256"
	"encoding/hex"
	"regexp"
	"strings"

	"github.com/elmo/code-review-engine/internal/scope"
)

type Location struct {
	Path            string `json:"path"`
	StartLine       int    `json:"start_line"`
	StartColumn     int    `json:"start_column"`
	EndLine         int    `json:"end_line"`
	EndColumn       int    `json:"end_column"`
	StartByte       int    `json:"start_byte,omitempty"`
	EndByte         int    `json:"end_byte,omitempty"`
	SFCBlock        string `json:"sfc_block,omitempty"`
	EnclosingSymbol string `json:"enclosing_symbol,omitempty"`
}

type Source struct {
	URL        string `json:"url"`
	Doc        string `json:"doc,omitempty"`
	DocVersion string `json:"doc_version"`
}

type AI struct {
	Verdict      string `json:"verdict"`
	Confidence   string `json:"confidence"`
	Rationale    string `json:"rationale,omitempty"`
	EvidenceLine []int  `json:"evidence_lines,omitempty"`
	SuggestedFix string `json:"suggested_fix,omitempty"`
	Model        string `json:"model,omitempty"`
	Via          string `json:"via,omitempty"` // "api" | "cursor-skill" | "cache"
}

type Finding struct {
	ID            string   `json:"id"`
	RuleID        string   `json:"rule_id"`
	RuleVersion   int      `json:"rule_version"`
	PackVersion   string   `json:"pack_version"`
	Status        string   `json:"status"`
	Severity      string   `json:"severity"`
	Confidence    string   `json:"confidence"`
	DetectionMode string   `json:"detection_mode"`
	Kind          string   `json:"kind,omitempty"`
	Category      string   `json:"category,omitempty"`
	Title         string   `json:"title,omitempty"`
	Location      Location `json:"location"`
	Snippet       string   `json:"snippet,omitempty"`
	Message       string   `json:"message"`
	Fix           string   `json:"fix,omitempty"`
	// Evidence is repo-index evidence (callers, duplicates, imports) behind index-engine findings;
	// it is passed to the AI confirmation step.
	Evidence        string            `json:"evidence,omitempty"`
	AppliedVersions map[string]string `json:"applied_versions,omitempty"`
	AssumedVersions []string          `json:"assumed_versions,omitempty"`
	Source          Source            `json:"source"`
	AI              *AI               `json:"ai,omitempty"`
	Xref            []string          `json:"xref,omitempty"`
	// CWE / OWASP Top 10 categories of the rule (security rules).
	CWE   []string `json:"cwe,omitempty"`
	OWASP []string `json:"owasp,omitempty"`
	// WCAG success criteria ("1.4.3") and their strictest conformance level (A, AA, AAA).
	WCAG      []string `json:"wcag,omitempty"`
	WCAGLevel string   `json:"wcag_level,omitempty"`
	// SuppressedBy explains status "suppressed": project linter config, an inline disable
	// comment, or crev-ignore.
	SuppressedBy *SuppressedBy `json:"suppressed_by,omitempty"`
	// Vuln: the advisory behind an SCA finding (rule SCA-OSV-VULNERABLE-DEPENDENCY).
	Vuln *Vuln `json:"vuln,omitempty"`
	// HiddenReason says why the finding is not in the review list ("" = listed): pending_ai,
	// ai_rejected, ai_uncertain, ai_low_confidence, shadow, suppressed_config, suppressed_inline,
	// crev_ignore. HiddenDetail is a one-line human explanation (see report.Annotate).
	HiddenReason string `json:"hidden_reason,omitempty"`
	HiddenDetail string `json:"hidden_detail,omitempty"`
}

// Vuln describes a dependency advisory match (OSV.dev).
type Vuln struct {
	ID             string   `json:"id"`                // OSV id (GHSA-..., PYSEC-..., GO-...)
	Aliases        []string `json:"aliases,omitempty"` // all aliases
	CVE            []string `json:"cve,omitempty"`
	GHSA           []string `json:"ghsa,omitempty"`
	Ecosystem      string   `json:"ecosystem"`
	Package        string   `json:"package"`
	Version        string   `json:"version"`
	Affected       []string `json:"affected_ranges,omitempty"`
	Fixed          string   `json:"fixed_version,omitempty"` // first fixed version above Version
	CVSSScore      float64  `json:"cvss_score,omitempty"`
	CVSSVector     string   `json:"cvss_vector,omitempty"`
	SeveritySource string   `json:"severity_source,omitempty"`
	Summary        string   `json:"summary,omitempty"`
	Published      string   `json:"published,omitempty"`
	Modified       string   `json:"modified,omitempty"`
	Dev            bool     `json:"dev,omitempty"` // development/test dependency
}

// SuppressedBy records why a finding was suppressed.
type SuppressedBy struct {
	Kind   string `json:"kind"`   // config | inline | crev-ignore
	Tool   string `json:"tool"`   // eslint, golangci-lint linter, ruff, yamllint, crev, ...
	ID     string `json:"id"`     // matched tool rule id
	Source string `json:"source"` // config file, or file:line + comment for inline
}

var ws = regexp.MustCompile(`\s+`)

// Fingerprint is stable across line moves: rule + path + normalized snippet + symbol + ordinal.
func Fingerprint(rule, path, snippet, symbol string, ordinal int) string {
	h := sha256.New()
	h.Write([]byte(rule + "\x00" + path + "\x00" + ws.ReplaceAllString(strings.TrimSpace(snippet), " ") + "\x00" + symbol + "\x00" + string(rune('0'+ordinal%10))))
	return hex.EncodeToString(h.Sum(nil))[:32]
}

// Report is the native JSON document.
type Report struct {
	SchemaVersion int                          `json:"schema_version"`
	Tool          string                       `json:"tool"`
	ToolVersion   string                       `json:"tool_version"`
	Root          string                       `json:"root"`
	Units         map[string]map[string]string `json:"version_facts"`
	Findings      []*Finding                   `json:"findings"`
	Errors        []string                     `json:"errors,omitempty"`
	Stats         map[string]int               `json:"stats"`
	// Shadow counts findings of quarantined rules per rule id (kept with status shadow, never listed by default).
	Shadow map[string]int `json:"shadow,omitempty"`
	// Hidden counts findings kept out of the review list per hidden_reason.
	Hidden map[string]int `json:"hidden,omitempty"`
	// Scope: what was reported (full repo or a git diff); nil = full.
	Scope *scope.Scope `json:"scope,omitempty"`
	// ProjectConfig summarises the project linter configuration that was honoured.
	ProjectConfig *ProjectConfig `json:"project_config,omitempty"`
}

// ProjectConfig summarises discovered project linter configuration.
type ProjectConfig struct {
	Respect    bool     `json:"respect"`
	Sources    []string `json:"sources,omitempty"`
	Directives int      `json:"directives"`
	Errors     []string `json:"errors,omitempty"`
}

var confRank = map[string]int{"low": 1, "medium": 2, "high": 3}

// ConfidenceAtLeast compares AI confidence levels (low < medium < high).
func ConfidenceAtLeast(c, min string) bool {
	if min == "" {
		min = "high"
	}
	return confRank[c] >= confRank[min]
}

// InReview is the review-list policy: only findings that are confirmed (deterministic rule,
// not suppressed or quarantined) or AI-confirmed with at least minConf (default "high") are
// listed. pending_ai, ai_uncertain, ai_rejected, lower-confidence ai_confirmed, shadow and
// suppressed findings never appear in the review list; they stay in the JSON report for audit
// and can be listed with --show-pending / --show-rejected / --show-shadow / --show-suppressed.
func InReview(f *Finding, minConf string) bool {
	switch f.Status {
	case "confirmed":
		return true
	case "ai_confirmed":
		return ConfidenceAtLeast(f.Confidence, minConf)
	}
	return false
}

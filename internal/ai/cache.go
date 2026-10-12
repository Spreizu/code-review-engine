package ai

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
)

// CacheEntry is one stored verdict (content-addressed; model-independent so verdicts written
// back by the Cursor skill are reused by API runs and vice versa; `via`/`model` record provenance).
type CacheEntry struct {
	Verdict
	Via     string    `json:"via"`
	Model   string    `json:"model,omitempty"`
	RuleID  string    `json:"rule_id"`
	Created time.Time `json:"created"`
}

// Cache is a directory of <key>.json files (safe to persist as a CI cache).
type Cache struct{ Dir string }

func (c Cache) path(key string) string { return filepath.Join(c.Dir, key[:2], key+".json") }

// Get returns a cached verdict.
func (c Cache) Get(key string) (*CacheEntry, bool) {
	if c.Dir == "" {
		return nil, false
	}
	b, err := os.ReadFile(c.path(key))
	if err != nil {
		return nil, false
	}
	var e CacheEntry
	if json.Unmarshal(b, &e) != nil || !validVerdict(e.Verdict.Verdict) {
		return nil, false
	}
	return &e, true
}

// Put stores a verdict.
func (c Cache) Put(key string, e CacheEntry) error {
	if c.Dir == "" {
		return nil
	}
	p := c.path(key)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		return err
	}
	b, _ := json.MarshalIndent(e, "", "  ")
	tmp := p + ".tmp"
	if err := os.WriteFile(tmp, b, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, p)
}

func validVerdict(v string) bool { return v == "confirmed" || v == "rejected" || v == "uncertain" }

func normConfidence(c string) string {
	switch c {
	case "high", "medium", "low":
		return c
	}
	return "low"
}

// Apply writes a verdict onto every finding of the item.
func (it *Item) Apply(e CacheEntry) {
	for _, f := range it.findings {
		ApplyTo(f, e)
	}
}

// ApplyTo sets status/confidence/ai on one finding.
func ApplyTo(f *findings.Finding, e CacheEntry) {
	conf := normConfidence(e.Confidence)
	switch e.Verdict.Verdict {
	case "confirmed":
		f.Status, f.Confidence = "ai_confirmed", conf
	case "rejected":
		f.Status, f.Confidence = "ai_rejected", conf
	default:
		f.Status, f.Confidence = "ai_uncertain", "low"
	}
	f.AI = &findings.AI{Verdict: e.Verdict.Verdict, Confidence: conf, Rationale: e.Rationale, EvidenceLine: e.EvidenceLines,
		SuggestedFix: e.SuggestedFix, Model: e.Model, Via: e.Via}
}

// FromCache applies cached verdicts; returns the items still unresolved.
func FromCache(items []*Item, c Cache) (rest []*Item, hits int) {
	for _, it := range items {
		if e, ok := c.Get(it.key); ok {
			e.Via = "cache:" + e.Via
			it.Apply(*e)
			hits++
			continue
		}
		rest = append(rest, it)
	}
	return rest, hits
}

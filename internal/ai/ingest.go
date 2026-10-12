package ai

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

// Export writes batches as JSONL (one batch per line) for the Cursor-skill fallback.
func Export(dir string, batches []*Batch) (string, error) {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return "", err
	}
	p := filepath.Join(dir, "batches.jsonl")
	f, err := os.Create(p)
	if err != nil {
		return "", err
	}
	defer f.Close()
	w := bufio.NewWriter(f)
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	for _, b := range batches {
		if err := enc.Encode(b); err != nil {
			return "", err
		}
	}
	return p, w.Flush()
}

// IngestStats summarises an ingest.
type IngestStats struct{ Applied, Unknown, Invalid int }

// Ingest applies agent-written verdicts to the pending items and caches them.
// Accepted ids: the short item id or any full/short finding id of the item or its duplicates.
func Ingest(items []*Item, verdicts []Verdict, cache Cache, via string) IngestStats {
	idx := map[string]*Item{}
	for _, it := range items {
		idx[it.ID] = it
		for _, f := range it.findings {
			idx[f.ID] = it
			idx[f.ID[:12]] = it
		}
	}
	var st IngestStats
	for _, v := range verdicts {
		it := idx[v.ID]
		if it == nil {
			st.Unknown++
			continue
		}
		if !validVerdict(v.Verdict) {
			st.Invalid++
			continue
		}
		e := CacheEntry{Verdict: v, Via: via, RuleID: it.Rule, Created: time.Now().UTC()}
		it.Apply(e)
		if err := cache.Put(it.key, e); err != nil {
			fmt.Fprintln(os.Stderr, "crev: cache write:", err)
		}
		st.Applied++
	}
	return st
}

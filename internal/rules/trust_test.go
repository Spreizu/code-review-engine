package rules

import (
	"strings"
	"testing"
	"testing/fstest"
)

func TestApplyTrustPolicy(t *testing.T) {
	fsys := fstest.MapFS{"data/trust.yaml": {Data: []byte(`rules:
  A: {level: proven, tp: 9}
  B: {level: unproven, why: own examples only}
  C: {level: measured, corpus_hits: 3, corpus_repos: 2}
`)}}
	mk := func(id, mode string) *Rule {
		r := &Rule{ID: id, Title: id}
		r.Detection.Mode = mode
		return r
	}
	a, b, c, d, e := mk("A", "deterministic"), mk("B", "deterministic"), mk("C", "deterministic"), mk("D", "deterministic"), mk("E", "deterministic")
	e.Status = "shadow"
	all := []*Rule{a, b, c, d, e}
	if err := ApplyTrust(all, fsys); err != nil {
		t.Fatal(err)
	}
	if a.Detection.Mode != "deterministic" || c.Detection.Mode != "deterministic" {
		t.Error("proven/measured rules must keep deterministic mode")
	}
	if b.Detection.Mode != "ai-confirm" || !b.Trust.Demoted || b.AIQuestion == "" {
		t.Errorf("unproven deterministic rule not demoted: %+v", b.Trust)
	}
	if d.Trust.Level != TrustUnproven || d.Detection.Mode != "ai-confirm" {
		t.Error("rule missing from trust.yaml must be unproven")
	}
	if e.Trust.Level != TrustQuarantined {
		t.Error("shadow rule must be quarantined")
	}
	if n := UndoTrustDemotion(all); n != 2 || b.Detection.Mode != "deterministic" {
		t.Errorf("undo: %d", n)
	}
	// no trust file: no policy
	f := mk("F", "deterministic")
	if err := ApplyTrust([]*Rule{f}, fstest.MapFS{}); err != nil || f.Trust != nil || f.Detection.Mode != "deterministic" {
		t.Error("without trust.yaml nothing may change")
	}
}

func TestWilsonLowerAndPromotion(t *testing.T) {
	for _, c := range []struct {
		tp, n int
		lo    float64
		hi    float64
	}{{0, 0, 0, 0}, {5, 5, 0.56, 0.57}, {72, 72, 0.949, 0.95}, {74, 74, 0.95, 0.96}, {200, 201, 0.97, 0.98}, {90, 100, 0.82, 0.83}} {
		if w := WilsonLower(c.tp, c.n); w < c.lo || w > c.hi {
			t.Errorf("WilsonLower(%d,%d)=%.4f, want [%.2f,%.2f]", c.tp, c.n, w, c.lo, c.hi)
		}
	}
	fsys := fstest.MapFS{"data/trust.yaml": {Data: []byte(`rules:
  P: {level: proven, tp: 120, promoted: true, wilson_lb: 0.969}
  Q: {level: measured, tp: 4}
  S: {level: quarantined, promoted: true}
`)}}
	mk := func(id string) *Rule {
		r := &Rule{ID: id, Title: id}
		r.Detection.Mode = "ai-confirm"
		return r
	}
	p, q, s, c := mk("P"), mk("Q"), mk("S"), mk("P")
	s.Status, c.Origin = "shadow", "custom"
	if err := ApplyTrust([]*Rule{p, q, s, c}, fsys); err != nil {
		t.Fatal(err)
	}
	if p.Detection.Mode != "deterministic" || !strings.Contains(p.Trust.Why, "Wilson") {
		t.Errorf("promoted rule must report directly: %s %+v", p.Detection.Mode, p.Trust)
	}
	if q.Detection.Mode != "ai-confirm" || s.Detection.Mode != "ai-confirm" || c.Detection.Mode != "ai-confirm" {
		t.Error("only promoted, active, built-in rules change mode")
	}
}

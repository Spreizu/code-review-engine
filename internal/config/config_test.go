package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDefaultsAndPolicy(t *testing.T) {
	c, err := Load(filepath.Join(t.TempDir(), "missing.yaml"))
	if err != nil || c.FailOn != "critical" || c.UnknownVersionPolicy != "assume-latest" {
		t.Fatalf("defaults: %+v %v", c, err)
	}
	p := filepath.Join(t.TempDir(), ".crev.yaml")
	_ = os.WriteFile(p, []byte("unknown_version_policy: warn\n"), 0o644)
	if _, err := Load(p); err == nil {
		t.Fatal("warn policy must be rejected")
	}
	_ = os.WriteFile(p, []byte("ai: { budget: 5 }\nbudget: { max_requests: 5 }\n"), 0o644)
	if _, err := Load(p); err == nil {
		t.Fatal("budget must be rejected")
	}
}

func TestProviderResolution(t *testing.T) {
	t.Setenv("CREV_AI_BASE_URL", "https://example.invalid/v1")
	t.Setenv("CREV_AI_MODEL", "m")
	t.Setenv("MY_KEY", "k")
	p := filepath.Join(t.TempDir(), ".crev.yaml")
	_ = os.WriteFile(p, []byte("ai: { api_key_env: MY_KEY }\n"), 0o644)
	c, err := Load(p)
	if err != nil || c.AI.EffectiveProvider() != "api" {
		t.Fatalf("want api: %v %s", err, c.AI.EffectiveProvider())
	}
	t.Setenv("MY_KEY", "")
	t.Setenv("CREV_AI_API_KEY", "")
	if c.AI.EffectiveProvider() != "cursor-skill" {
		t.Fatal("no key => cursor-skill fallback")
	}
}

func TestTrustAndVulnDBConfig(t *testing.T) {
	dir := t.TempDir()
	p := filepath.Join(dir, ".crev.yaml")
	c, err := Load(p)
	if err != nil || c.Trust.DeterministicMin != "measured" || c.VulnDB.Mode != "online" || c.VulnDB.MaxAgeDays != 7 || c.VulnDB.APIURL != "https://api.osv.dev" {
		t.Fatalf("defaults: %v %+v %+v", err, c.Trust, c.VulnDB)
	}
	os.WriteFile(p, []byte("vulndb: {mode: offline, dir: /x, max_age_days: 3}\ntrust: {deterministic_min: unproven}\n"), 0o644)
	if c, err = Load(p); err != nil || c.VulnDB.Mode != "offline" || c.VulnDB.MaxAgeDays != 3 || c.Trust.DeterministicMin != "unproven" {
		t.Fatalf("explicit: %v %+v", err, c.VulnDB)
	}
	for _, bad := range []string{"vulndb: {mode: sometimes}\n", "trust: {deterministic_min: proven}\n"} {
		os.WriteFile(p, []byte(bad), 0o644)
		if _, err := Load(p); err == nil {
			t.Errorf("%q must be rejected", bad)
		}
	}
}

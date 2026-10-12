// Package config loads .crev.yaml and applies environment overrides.
package config

import (
	"fmt"
	"os"
	"slices"
	"strings"

	"gopkg.in/yaml.v3"
)

// RuleSetting is a per-rule override in .crev.yaml.
type RuleSetting struct {
	Enabled  *bool  `yaml:"enabled"`
	Severity string `yaml:"severity"`
}

// AI configures the confirmation step for ai-confirm findings.
//
// There is deliberately no request/token budget: cost is controlled by payload compression
// (rule text deduplicated per batch, minimal code context, batching, caching).
type AI struct {
	// Mode: off = never call a provider (findings stay pending_ai); auto = use the API provider when
	// configured, otherwise the Cursor-skill fallback (export payloads); required = like auto but
	// exit 4 when any ai-confirm finding is left without a verdict.
	Mode string `yaml:"mode"`
	// Provider: auto (api if configured, else cursor-skill) | api | cursor-skill.
	Provider string `yaml:"provider"`
	// OpenAI-compatible endpoint, e.g. https://api.example.com/v1 (".../chat/completions" is appended).
	BaseURL string `yaml:"base_url"`
	Model   string `yaml:"model"`
	// Name of the environment variable holding the API key. The key itself never lives in the file.
	APIKeyEnv     string `yaml:"api_key_env"`
	MinConfidence string `yaml:"min_confidence"`
	// ReviewConfidence: AI-confirmed findings need at least this confidence to appear in the
	// review list at all (default high); lower-confidence, uncertain and rejected verdicts are
	// only listed with --show-rejected.
	ReviewConfidence string  `yaml:"review_confidence"`
	BatchSize        int     `yaml:"batch_size"`
	ContextLines     int     `yaml:"context_lines"`
	MaxSnippetChar   int     `yaml:"max_snippet_chars"`
	Concurrency      int     `yaml:"concurrency"`
	TimeoutSeconds   int     `yaml:"timeout_seconds"`
	Temperature      float64 `yaml:"temperature"`
	JSONMode         *bool   `yaml:"json_mode"`
	CacheDir         string  `yaml:"cache_dir"`
	HandoffDir       string  `yaml:"handoff_dir"`
	// Extra HTTP headers (values may reference env vars as ${NAME}).
	Headers map[string]string `yaml:"headers"`
}

// Runs configures scan history and retention.
type Runs struct {
	Enabled    *bool  `yaml:"enabled"`      // default true
	Dir        string `yaml:"dir"`          // default <state_dir>/runs
	Keep       int    `yaml:"keep"`         // newest runs kept per branch (default 50, 0 = unlimited)
	MaxAgeDays int    `yaml:"max_age_days"` // runs older than this are pruned (default 90, 0 = unlimited)
}

// Feedback configures false-positive feedback.
type Feedback struct {
	// FPThreshold: distinct false positives (same rule version) that demote a rule to shadow
	// mode (default 3, 0 = default, negative = never demote).
	FPThreshold int `yaml:"fp_threshold"`
}

// Config is the parsed .crev.yaml.
type Config struct {
	FailOn string   `yaml:"fail_on"`
	Packs  []string `yaml:"packs"`
	// RulesDir replaces the embedded catalog with packs from this directory (catalog development).
	RulesDir string `yaml:"rules_dir"`
	// CustomRules: user rule files/dirs layered on top of the catalog (add / patch / replace /
	// disable by id, see rules/README.md). Relative to the project root. Default [.crev/rules].
	CustomRules          []string `yaml:"custom_rules"`
	UnknownVersionPolicy string   `yaml:"unknown_version_policy"`
	Baseline             string   `yaml:"baseline"`
	StateDir             string   `yaml:"state_dir"`
	Ignore               []string `yaml:"ignore"`
	// DefaultExcludes skips dependency/build/cache dirs, lockfiles and minified/generated artefacts
	// (engine.DefaultExcludeDirs / DefaultExcludeFiles). Default true.
	DefaultExcludes *bool `yaml:"default_excludes"`
	// Gitignore honours .gitignore files (nested, negations) and .git/info/exclude. Default true.
	Gitignore *bool `yaml:"gitignore"`
	// SkipGenerated skips files whose header marks them generated ("Code generated ... DO NOT EDIT.", @generated). Default true.
	SkipGenerated *bool                  `yaml:"skip_generated"`
	Rules         map[string]RuleSetting `yaml:"rules"`
	// RespectProjectConfig honours the project's own linter configuration (rule turned off in
	// eslint/golangci/ruff/... => crev equivalent suppressed) and inline disable comments.
	// Default true. crev-ignore comments are honoured either way.
	RespectProjectConfig *bool `yaml:"respect_project_config"`
	// Runs: per-scan history under <state_dir>/runs (see internal/runs).
	Runs Runs `yaml:"runs"`
	AI   AI   `yaml:"ai"`
	// Feedback: `crev feedback fp` verdicts under <state_dir>/feedback.
	Feedback Feedback `yaml:"feedback"`
	// Trust: evidence level a deterministic rule needs to report without AI confirmation.
	Trust Trust `yaml:"trust"`
	// VulnDB: dependency vulnerability scanning (SCA) against OSV.dev.
	VulnDB VulnDB `yaml:"vulndb"`
	// Deprecated keys kept only to give a helpful error.
	Budget any `yaml:"budget"`
}

// Trust configures the rule trust policy (rules/data/trust.yaml).
type Trust struct {
	// DeterministicMin: "measured" (default) runs unproven deterministic rules as ai-confirm;
	// "unproven" keeps every rule's declared mode (more findings, more false positives).
	DeterministicMin string `yaml:"deterministic_min"`
}

// VulnDB configures SCA (lockfile dependencies matched against OSV.dev advisories).
type VulnDB struct {
	// Mode: online (OSV.dev querybatch API, default), offline (local database downloaded by
	// `crev vulndb update`) or off.
	Mode string `yaml:"mode"`
	// Dir: offline database cache (default ~/.cache/crev/vulndb, or $XDG_CACHE_HOME/crev/vulndb).
	Dir string `yaml:"dir"`
	// MaxAgeDays: warn when the offline database is older than this (default 7).
	MaxAgeDays int `yaml:"max_age_days"`
	// APIURL: OSV API base (default https://api.osv.dev); for mirrors.
	APIURL string `yaml:"api_url"`
	// TimeoutSeconds for online queries (default 30).
	TimeoutSeconds int `yaml:"timeout_seconds"`
}

// Defaults returns the built-in configuration.
func Defaults() Config {
	t := true
	return Config{
		FailOn:               "critical",
		Packs:                nil, // all packs; applies_to + file kinds decide what runs
		CustomRules:          []string{".crev/rules"},
		UnknownVersionPolicy: "assume-latest",
		StateDir:             ".crev",
		Runs:                 Runs{Keep: 50, MaxAgeDays: 90},
		Ignore:               []string{},
		AI: AI{
			Mode: "auto", Provider: "auto", APIKeyEnv: "CREV_AI_API_KEY", MinConfidence: "medium", ReviewConfidence: "high",
			BatchSize: 20, ContextLines: 6, MaxSnippetChar: 1200, Concurrency: 4, TimeoutSeconds: 120,
			Temperature: 0, JSONMode: &t,
		},
	}
}

// Load reads path (missing file = defaults) and applies CREV_* environment overrides.
func Load(path string) (Config, error) {
	c := Defaults()
	if b, err := os.ReadFile(path); err == nil {
		if err := yaml.Unmarshal(b, &c); err != nil {
			return c, fmt.Errorf("%s: %w", path, err)
		}
	} else if !os.IsNotExist(err) {
		return c, err
	}
	d := Defaults()
	if c.AI.BatchSize <= 0 {
		c.AI.BatchSize = d.AI.BatchSize
	}
	if c.AI.ContextLines < 0 {
		c.AI.ContextLines = d.AI.ContextLines
	}
	if c.AI.MaxSnippetChar <= 0 {
		c.AI.MaxSnippetChar = d.AI.MaxSnippetChar
	}
	if c.AI.Concurrency <= 0 {
		c.AI.Concurrency = d.AI.Concurrency
	}
	if c.AI.TimeoutSeconds <= 0 {
		c.AI.TimeoutSeconds = d.AI.TimeoutSeconds
	}
	if c.AI.APIKeyEnv == "" {
		c.AI.APIKeyEnv = d.AI.APIKeyEnv
	}
	if c.AI.JSONMode == nil {
		c.AI.JSONMode = d.AI.JSONMode
	}
	if c.StateDir == "" {
		c.StateDir = d.StateDir
	}
	switch c.Trust.DeterministicMin {
	case "":
		c.Trust.DeterministicMin = "measured"
	case "measured", "unproven":
	default:
		return c, fmt.Errorf("trust.deterministic_min must be measured or unproven, got %q", c.Trust.DeterministicMin)
	}
	switch c.VulnDB.Mode {
	case "":
		c.VulnDB.Mode = "online"
	case "online", "offline", "off":
	default:
		return c, fmt.Errorf("vulndb.mode must be online, offline or off, got %q", c.VulnDB.Mode)
	}
	if c.VulnDB.MaxAgeDays <= 0 {
		c.VulnDB.MaxAgeDays = 7
	}
	if c.VulnDB.APIURL == "" {
		c.VulnDB.APIURL = "https://api.osv.dev"
	}
	if c.VulnDB.TimeoutSeconds <= 0 {
		c.VulnDB.TimeoutSeconds = 30
	}
	if c.Runs.Dir == "" {
		c.Runs.Dir = c.StateDir + "/runs"
	}
	if c.Runs.Keep < 0 || c.Runs.MaxAgeDays < 0 {
		return c, fmt.Errorf("runs.keep / runs.max_age_days must be >= 0")
	}
	if c.AI.CacheDir == "" {
		c.AI.CacheDir = c.StateDir + "/cache/ai"
	}
	if c.AI.HandoffDir == "" {
		c.AI.HandoffDir = c.StateDir + "/ai-handoff"
	}
	env := func(k string, dst *string) {
		if v := strings.TrimSpace(os.Getenv(k)); v != "" {
			*dst = v
		}
	}
	env("CREV_AI_BASE_URL", &c.AI.BaseURL)
	env("CREV_AI_MODEL", &c.AI.Model)
	env("CREV_AI_MODE", &c.AI.Mode)
	env("CREV_AI_PROVIDER", &c.AI.Provider)
	env("CREV_AI_API_KEY_ENV", &c.AI.APIKeyEnv)
	env("CREV_FAIL_ON", &c.FailOn)
	return c, c.Validate()
}

// APIKey resolves the key from the configured environment variable (falls back to CREV_AI_API_KEY).
func (a AI) APIKey() string {
	if v := os.Getenv(a.APIKeyEnv); v != "" {
		return v
	}
	return os.Getenv("CREV_AI_API_KEY")
}

// APIConfigured reports whether an OpenAI-compatible endpoint can be called.
func (a AI) APIConfigured() bool { return a.BaseURL != "" && a.Model != "" && a.APIKey() != "" }

// EffectiveProvider resolves provider=auto.
func (a AI) EffectiveProvider() string {
	switch a.Provider {
	case "api", "cursor-skill":
		return a.Provider
	}
	if a.APIConfigured() {
		return "api"
	}
	return "cursor-skill"
}

// Validate checks enumerations.
func (c Config) Validate() error {
	in := func(v string, ok ...string) bool { return slices.Contains(ok, v) }
	if !in(c.FailOn, "info", "minor", "major", "critical", "none") {
		return fmt.Errorf("fail_on: %q (want info|minor|major|critical|none)", c.FailOn)
	}
	if !in(c.UnknownVersionPolicy, "assume-latest", "skip") {
		return fmt.Errorf("unknown_version_policy: %q (want assume-latest|skip; 'warn' was removed: undetectable versions are assumed latest)", c.UnknownVersionPolicy)
	}
	if !in(c.AI.Mode, "off", "auto", "required") {
		return fmt.Errorf("ai.mode: %q (want off|auto|required)", c.AI.Mode)
	}
	if !in(c.AI.Provider, "auto", "api", "cursor-skill") {
		return fmt.Errorf("ai.provider: %q (want auto|api|cursor-skill)", c.AI.Provider)
	}
	if c.AI.ReviewConfidence == "" {
		c.AI.ReviewConfidence = "high"
	}
	if !in(c.AI.ReviewConfidence, "low", "medium", "high") {
		return fmt.Errorf("ai.review_confidence: %q", c.AI.ReviewConfidence)
	}
	if !in(c.AI.MinConfidence, "low", "medium", "high") {
		return fmt.Errorf("ai.min_confidence: %q", c.AI.MinConfidence)
	}
	if c.Budget != nil {
		return fmt.Errorf("budget: removed - crev has no AI budget cap; payloads are compressed instead (see PLAN.md §8.5)")
	}
	if strings.HasPrefix(strings.TrimSpace(c.AI.APIKeyEnv), "sk-") {
		return fmt.Errorf("ai.api_key_env must be the NAME of an environment variable, not a key")
	}
	return nil
}

// On reports a default-true flag.
func On(b *bool) bool { return b == nil || *b }

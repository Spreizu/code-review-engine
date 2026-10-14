// Command crev is the version-aware code review CLI (v1: local + CI).
//
//	crev scan [path]            scan, AI-confirm (API or Cursor-skill export), report, exit code
//	crev ai export [path]       write pending ai-confirm payloads (.crev/ai-handoff/batches.jsonl)
//	crev ai run [path]          confirm pending findings through the OpenAI-compatible API
//	crev ai status [path]       show provider resolution (never prints the key)
//	crev ingest [-root path] FILE|-   apply verdicts written by an agent (Cursor skill), re-gate
//	crev versions [path]        detected version facts (assumed-latest marked)
//	crev rules list|show ID
//
// Exit codes: 0 ok · 1 gating findings (default fail_on: critical) · 2 usage/config error ·
// 3 engine error · 4 --ai required and findings left without a verdict.
package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"maps"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"runtime/pprof"
	"slices"
	"strconv"
	"strings"
	"time"

	"github.com/elmo/code-review-engine/internal/sca"

	"github.com/elmo/code-review-engine/internal/ai"
	"github.com/elmo/code-review-engine/internal/config"
	"github.com/elmo/code-review-engine/internal/engine"
	"github.com/elmo/code-review-engine/internal/feedback"
	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/htmlreport"
	"github.com/elmo/code-review-engine/internal/index"
	"github.com/elmo/code-review-engine/internal/progress"
	"github.com/elmo/code-review-engine/internal/report"
	"github.com/elmo/code-review-engine/internal/rulecheck"
	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/runs"
	"github.com/elmo/code-review-engine/internal/scope"
	"github.com/elmo/code-review-engine/internal/ui"
	"github.com/elmo/code-review-engine/internal/versions"
	catalog "github.com/elmo/code-review-engine/rules"
)

const version = "0.1.0"

type exitErr struct {
	code int
	err  error
}

func (e exitErr) Error() string { return e.err.Error() }

func fail(code int, format string, a ...any) error { return exitErr{code, fmt.Errorf(format, a...)} }

func main() {
	// CREV_CPUPROFILE=<file>: write a pprof CPU profile (corpus harness / performance work).
	if p := os.Getenv("CREV_CPUPROFILE"); p != "" {
		if f, err := os.Create(p); err == nil {
			if pprof.StartCPUProfile(f) == nil {
				defer pprof.StopCPUProfile()
			}
		}
	}
	if len(os.Args) < 2 {
		usage()
		os.Exit(2)
	}
	var err error
	switch os.Args[1] {
	case "scan":
		err = cmdScan(os.Args[2:])
	case "ai":
		err = cmdAI(os.Args[2:])
	case "ingest":
		err = cmdIngest(os.Args[2:])
	case "versions":
		err = cmdVersions(os.Args[2:])
	case "rules":
		err = cmdRules(os.Args[2:])
	case "init":
		err = cmdInit(os.Args[2:])
	case "runs":
		err = cmdRuns(os.Args[2:])
	case "report":
		err = cmdReport(os.Args[2:])
	case "ui":
		err = cmdUI(os.Args[2:])
	case "index":
		err = cmdIndex(os.Args[2:])
	case "feedback":
		err = cmdFeedback(os.Args[2:])
	case "vulndb":
		err = cmdVulndb(os.Args[2:])
	case "version", "--version":
		fmt.Println("crev", version)
	case "help", "-h", "--help":
		usage()
	default:
		usage()
		os.Exit(2)
	}
	if err != nil {
		var ee exitErr
		if errors.As(err, &ee) {
			if ee.err != nil && ee.err.Error() != "" {
				fmt.Fprintln(os.Stderr, "crev:", ee.err)
			}
			os.Exit(ee.code)
		}
		fmt.Fprintln(os.Stderr, "crev:", err)
		os.Exit(3)
	}
}

func usage() {
	fmt.Fprint(os.Stderr, `usage: crev <command> [flags]
  scan [path]          full repo by default; diff scopes: --base REF [--head REF] | --staged | --working-tree |
                       --commits A..B|A...B  [--diff-context hunk|file]
                       --format text|json|sarif|md  --output [fmt=]FILE (repeatable)  --fail-on LEVEL
                       --ai off|auto|required  --provider auto|api|cursor-skill  --min-ai-confidence LEVEL
                       --packs a,b  --rules-dir DIR  --config FILE  --strict-pending
                       review list = confirmed + ai_confirmed(high); everything else is kept with a hidden_reason:
                       --show-hidden[=pending_ai,ai_rejected,ai_uncertain,ai_low_confidence,shadow,
                       suppressed_config,suppressed_inline,crev_ignore] (or groups: pending, rejected, suppressed, shadow;
                       aliases --show-pending --show-rejected --show-suppressed --show-shadow)
  ai export [path]     write pending payloads for the Cursor skill (.crev/ai-handoff/batches.jsonl)
  ai run [path]        confirm pending findings via the OpenAI-compatible API
  ai status [path]     show which AI provider would be used
  ingest [-root P] [--run latest|ID] FILE|-   apply agent verdicts to a run (default latest) and re-gate
  index [--json] [--symbol NAME] [--file PATH]  repo index (symbols, callers, imports) used by the simplification rules
  ui [--port 7317] [--addr 127.0.0.1]  local web UI: runs, compare, branch timeline, findings, rules
  runs list [--branch B] [--json] | show [RUN] | prune     scan history in .crev/runs
  report --html [--run RUN] [-o FILE] | --data              static HTML report from run data (layout placeholder)
  versions [path]      detected version facts
  init [path] [--force]  write the default .crev.yaml template (and an empty .crev/rules/)
  rules list [--pack P] [--origin custom] | rules show ID
  rules validate [FILE|DIR ...] [--strict] [--skip-examples] [--json]   check user rules (.crev/rules/)
  vulndb update [--ecosystems npm,PyPI,Go,Packagist,Maven] [--dir DIR] | status   offline OSV.dev databases
                       (scan --vulndb online|offline|off; config vulndb.mode)
`)
}

// ---------------------------------------------------------------- shared setup

type multi []string

// showHidden is --show-hidden[=reason,...]: a bool-style flag that optionally takes a value.
type showHidden struct{ set map[string]bool }

func (s *showHidden) String() string   { return "" }
func (s *showHidden) IsBoolFlag() bool { return true }
func (s *showHidden) Set(v string) error {
	m, err := report.ParseShowHidden(v)
	if err != nil {
		return err
	}
	if s.set == nil {
		s.set = map[string]bool{}
	}
	maps.Copy(s.set, m)
	return nil
}

func (m *multi) String() string     { return strings.Join(*m, ",") }
func (m *multi) Set(v string) error { *m = append(*m, v); return nil }

type env struct {
	root    string
	cfg     config.Config
	all     []*rules.Rule
	byID    map[string]*rules.Rule
	changes []rules.Change // effect of user rule files (.crev/rules/)
	custom  []string       // user rule files that were applied
	cfgPath string
}

func setup(root, cfgPath, rulesDir, packs string) (*env, error) {
	abs, err := filepath.Abs(root)
	if err != nil {
		return nil, fail(2, "%v", err)
	}
	if cfgPath == "" {
		cfgPath = filepath.Join(abs, ".crev.yaml")
	}
	cfg, err := config.Load(cfgPath)
	if err != nil {
		return nil, fail(2, "config: %v", err)
	}
	if rulesDir == "" {
		rulesDir = cfg.RulesDir
	}
	var rs []*rules.Rule
	if rulesDir != "" {
		rs, err = rules.LoadFiles(rulesDir)
	} else {
		rs, err = rules.LoadFS(catalog.FS, "packs/*/*.yaml")
	}
	if err != nil {
		return nil, fail(2, "rules: %v", err)
	}
	if err := rules.ApplyData(rs, catalog.FS); err != nil {
		return nil, fail(2, "rules data: %v", err)
	}
	if cfg.Trust.DeterministicMin == "unproven" {
		rules.UndoTrustDemotion(rs)
	}
	var dirs []string
	for _, d := range cfg.CustomRules {
		if !filepath.IsAbs(d) {
			d = filepath.Join(abs, d)
		}
		dirs = append(dirs, d)
	}
	custom, err := rules.CustomFiles(dirs...)
	if err != nil {
		return nil, fail(2, "custom rules: %v", err)
	}
	var changes []rules.Change
	if rs, changes, err = rules.ApplyCustom(rs, custom); err != nil {
		return nil, fail(2, "custom rules: %v", err)
	}
	if err := rules.ApplyXref(rs, catalog.FS, "data/xref.yaml"); err != nil { // again: custom rules may add tool:id xrefs
		return nil, fail(2, "rules xref: %v", err)
	}
	want := map[string]bool{}
	list := cfg.Packs
	if packs != "" {
		list = strings.Split(packs, ",")
	}
	for _, p := range list {
		want[strings.TrimSpace(p)] = true
	}
	e := &env{root: abs, cfg: cfg, byID: map[string]*rules.Rule{}, changes: changes, custom: custom, cfgPath: cfgPath}
	e.byID[sca.RuleID] = sca.Rule() // dependency findings (vulndb), reported outside the rule engine
	for _, r := range rs {
		e.byID[r.ID] = r
		// --packs / packs: names a pack (language/framework) or a theme tag (taint, llm, cert,
		// appsec, supply-chain, cloud, simplification), so `--packs taint` still selects the taint rules
		if len(want) == 0 || want[r.Pack] || slices.ContainsFunc(r.Tags, func(t string) bool { return want[t] }) || (r.Origin == "custom" && r.BaseFile == "") {
			e.all = append(e.all, r)
		}
	}
	return e, nil
}

func (e *env) latest() map[string]string {
	if e.cfg.UnknownVersionPolicy == "skip" {
		return map[string]string{}
	}
	if b, err := catalog.FS.ReadFile("data/latest-versions.yaml"); err == nil {
		return versions.LatestFrom(b)
	}
	return versions.Latest("")
}

func (e *env) statePath() string {
	d := e.cfg.StateDir
	if !filepath.IsAbs(d) {
		d = filepath.Join(e.root, d)
	}
	return filepath.Join(d, "report.json")
}

func (e *env) abs(p string) string {
	if filepath.IsAbs(p) {
		return p
	}
	return filepath.Join(e.root, p)
}

func (e *env) cache() ai.Cache { return ai.Cache{Dir: e.abs(e.cfg.AI.CacheDir)} }

func (e *env) saveState(rep *findings.Report) error {
	p := e.statePath()
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		return err
	}
	f, err := os.Create(p)
	if err != nil {
		return err
	}
	defer f.Close()
	return report.JSON(f, rep)
}

func (e *env) loadState() (*findings.Report, error) {
	b, err := os.ReadFile(e.statePath())
	if err != nil {
		return nil, fail(2, "no saved report at %s (run `crev scan` first): %v", e.statePath(), err)
	}
	var rep findings.Report
	if err := json.Unmarshal(b, &rep); err != nil {
		return nil, fail(2, "%s: %v", e.statePath(), err)
	}
	return &rep, nil
}

func (e *env) gate(failOn, minConf string, strict bool) report.GateOptions {
	if failOn == "" {
		failOn = e.cfg.FailOn
	}
	if minConf == "" {
		minConf = e.cfg.AI.MinConfidence
	}
	return report.GateOptions{FailOn: failOn, MinConfidence: minConf, StrictPending: strict, ReviewConfidence: e.cfg.AI.ReviewConfidence}
}

func (e *env) buildOpts(skill bool) ai.BuildOptions {
	return ai.BuildOptions{Root: e.root, BatchSize: e.cfg.AI.BatchSize, ContextLines: e.cfg.AI.ContextLines, MaxChars: e.cfg.AI.MaxSnippetChar,
		WithExamples: skill, IncludeSystem: skill}
}

func (e *env) client() *ai.Client {
	a := e.cfg.AI
	return &ai.Client{BaseURL: a.BaseURL, Model: a.Model, APIKey: a.APIKey(), Temperature: a.Temperature, JSONMode: a.JSONMode != nil && *a.JSONMode,
		Headers: a.Headers}
}

func pendingCount(rep *findings.Report) int {
	n := 0
	for _, f := range rep.Findings {
		if f.Status == "pending_ai" {
			n++
		}
	}
	return n
}

// pendingDetail explains why pending_ai findings are still pending after the AI step.
func (e *env) pendingDetail(mode, provider string, rep *findings.Report) string {
	if pendingCount(rep) == 0 {
		return ""
	}
	if mode == "off" {
		return "AI step is off (--ai off / ai.mode: off); run with --ai auto and an API provider, or `crev ai export` for the Cursor skill"
	}
	if provider == "" || provider == "auto" {
		provider = e.cfg.AI.EffectiveProvider()
	}
	if provider == "api" {
		return "the AI API did not return a verdict (see errors); rerun or `crev ai run`"
	}
	if !e.cfg.AI.APIConfigured() {
		return "no AI API configured; exported for the crev-review Cursor skill, answer them and run `crev ingest`"
	}
	return "exported for the crev-review Cursor skill; answer them and run `crev ingest`"
}

// confirm runs the AI step: cache first, then API or Cursor-skill export. Returns a status line.
func (e *env) confirm(rep *findings.Report, provider string) (string, error) {
	items := ai.Pending(rep, e.byID, e.buildOpts(false))
	if len(items) == 0 {
		return "", nil
	}
	rest, hits := ai.FromCache(items, e.cache())
	msg := fmt.Sprintf("ai: %d unique pending item(s), %d from cache", len(items), hits)
	if len(rest) == 0 {
		return msg, nil
	}
	if provider == "" || provider == "auto" {
		provider = e.cfg.AI.EffectiveProvider()
	}
	switch provider {
	case "api":
		if !e.cfg.AI.APIConfigured() {
			return msg, fail(2, "ai.provider=api but base_url/model/key are not all set (CREV_AI_BASE_URL, CREV_AI_MODEL, $%s)", e.cfg.AI.APIKeyEnv)
		}
		batches := ai.Batches(rest, e.byID, rep, e.buildOpts(false))
		ctx, cancel := context.WithTimeout(context.Background(), time.Duration(e.cfg.AI.TimeoutSeconds*len(batches)+60)*time.Second)
		defer cancel()
		st := ai.Run(ctx, e.client(), batches, e.cache(), e.cfg.AI.Concurrency)
		msg += fmt.Sprintf(", %d sent in %d batch(es) to %s, %d resolved, %d failed (tokens in/out %d/%d)",
			st.Sent, st.Batches, e.cfg.AI.Model, st.Resolved, st.Failed, st.PromptTokens, st.CompletionTokens)
		for _, er := range st.Errors {
			rep.Errors = append(rep.Errors, "ai: "+er)
		}
	default:
		batches := ai.Batches(rest, e.byID, rep, e.buildOpts(true))
		p, err := ai.Export(e.abs(e.cfg.AI.HandoffDir), batches)
		if err != nil {
			return msg, err
		}
		msg += fmt.Sprintf(", %d exported in %d batch(es) to %s for the crev-review skill; answer them and run `crev ingest <responses.jsonl>`",
			len(rest), len(batches), relTo(e.root, p))
	}
	return msg, nil
}

func relTo(root, p string) string {
	if r, err := filepath.Rel(root, p); err == nil {
		return r
	}
	return p
}

func writeOutputs(e *env, rep *findings.Report, format string, outputs []string, g report.GateOptions) error {
	render := func(w io.Writer, f string) error {
		switch f {
		case "json":
			return report.JSON(w, rep)
		case "sarif":
			return report.SARIF(w, rep, e.byID, version, g)
		case "md":
			report.Markdown(w, rep, g)
		case "text":
			report.Text(w, rep, g)
		default:
			return fail(2, "unknown format %q", f)
		}
		return nil
	}
	for _, o := range outputs {
		f, path := "", o
		if i := strings.Index(o, "="); i > 0 {
			f, path = o[:i], o[i+1:]
		} else {
			switch strings.ToLower(filepath.Ext(o)) {
			case ".sarif":
				f = "sarif"
			case ".json":
				f = "json"
			case ".md":
				f = "md"
			default:
				f = "text"
			}
		}
		fh, err := os.Create(path)
		if err != nil {
			return fail(2, "%v", err)
		}
		err = render(fh, f)
		fh.Close()
		if err != nil {
			return err
		}
	}
	return render(os.Stdout, format)
}

// ---------------------------------------------------------------- commands

func cmdScan(args []string) error {
	fs := flag.NewFlagSet("scan", flag.ContinueOnError)
	format := fs.String("format", "text", "text|json|sarif|md")
	typeMode := fs.String("types", "", "type resolver: basic (per file, default), full (cross-file index prepass) or off (default from .crev.yaml types)")
	var outputs multi
	fs.Var(&outputs, "output", "[fmt=]FILE, repeatable")
	failOn := fs.String("fail-on", "", "info|minor|major|critical|none (default from .crev.yaml: critical)")
	aiMode := fs.String("ai", "", "off|auto|required (default from .crev.yaml)")
	provider := fs.String("provider", "", "auto|api|cursor-skill")
	minConf := fs.String("min-ai-confidence", "", "low|medium|high")
	packs := fs.String("packs", "", "comma-separated packs or theme tags, e.g. java,taint (default from .crev.yaml)")
	rulesDir := fs.String("rules-dir", "", "load packs from this directory instead of the embedded catalog")
	cfgPath := fs.String("config", "", "config file (default <path>/.crev.yaml)")
	showRejected := fs.Bool("show-rejected", false, "also list ai_rejected, ai_uncertain and below-review-confidence ai_confirmed findings")
	showPending := fs.Bool("show-pending", false, "also list pending_ai findings (ai-confirm candidates without an AI verdict)")
	showShadow := fs.Bool("show-shadow", false, "with --include-shadow: also list findings of quarantined (shadow) rules")
	fs.Bool("include-shadow", true, "deprecated, always on: findings of quarantined (shadow) rules are kept in the report with status shadow (never listed by default, never gate)")
	var hidden showHidden
	fs.Var(&hidden, "show-hidden", "also list hidden findings: --show-hidden (all) or --show-hidden=pending_ai,ai_rejected,ai_uncertain,ai_low_confidence,shadow,suppressed_config,suppressed_inline,crev_ignore (groups: pending, rejected, suppressed, shadow)")
	reviewConf := fs.String("review-confidence", "", "minimum AI confidence for ai_confirmed findings to enter the review list: low|medium|high (default from .crev.yaml: high)")
	showSuppressed := fs.Bool("show-suppressed", false, "also list findings suppressed by project linter config / inline disables / crev-ignore")
	noProjectConfig := fs.Bool("no-project-config", false, "ignore the project's linter configuration and inline linter disables (crev-ignore still applies)")
	strict := fs.Bool("strict-pending", false, "pending_ai/ai_uncertain findings also gate")
	noGitignore := fs.Bool("no-gitignore", false, "do not honour .gitignore / .git/info/exclude")
	noDefaultExcludes := fs.Bool("no-default-excludes", false, "also scan node_modules, vendor, build output, lockfiles, minified files")
	includeGenerated := fs.Bool("include-generated", false, "also review files marked as generated (@generated, Code generated ... DO NOT EDIT)")
	noRun := fs.Bool("no-run", false, "do not record this scan in .crev/runs (history / ledger)")
	progFlag := fs.String("progress", "auto", "progress on stderr: auto (bar on a TTY, off in CI) | bar | plain (periodic log lines) | off")
	noProgress := fs.Bool("no-progress", false, "disable the progress display")
	quiet := fs.Bool("quiet", false, "no progress and no informational stderr lines")
	withUI := fs.Bool("ui", false, "after the scan, serve the web UI (see crev ui)")
	vulndbMode := fs.String("vulndb", "", "dependency vulnerability scan (OSV.dev): online|offline|off (default from .crev.yaml: online)")
	uiPort := fs.Int("ui-port", 7317, "port for --ui")
	var so scope.Options
	fs.StringVar(&so.Base, "base", "", "diff scope: report findings on lines changed in merge-base(BASE, HEAD)..HEAD")
	fs.StringVar(&so.Base, "diff-base", "", "alias of --base")
	fs.StringVar(&so.Head, "head", "", "with --base: head ref (default HEAD)")
	fs.BoolVar(&so.Staged, "staged", false, "diff scope: staged changes (index vs HEAD)")
	fs.BoolVar(&so.WorkingTree, "working-tree", false, "diff scope: all uncommitted changes incl. untracked files")
	fs.StringVar(&so.Commits, "commits", "", "diff scope: A..B (or A...B for merge-base semantics)")
	fs.StringVar(&so.DiffContext, "diff-context", "hunk", "diff scope granularity: hunk (changed lines) | file (whole changed files)")
	if err := parseInterspersed(fs, args); err != nil {
		return fail(2, "%v", err)
	}
	start := time.Now()
	root := "."
	if fs.NArg() > 0 {
		root = fs.Arg(0)
	}
	e, err := setup(root, *cfgPath, *rulesDir, *packs)
	if err != nil {
		return err
	}
	sc, err := scope.Resolve(e.root, so)
	if err != nil {
		return fail(2, "scope: %v", err)
	}
	opts := engine.Options{Scope: sc, Root: e.root, Rules: e.all, Ignore: e.cfg.Ignore, Latest: e.latest(), Disabled: map[string]bool{}, Severity: map[string]string{},
		NoGitignore: *noGitignore || !config.On(e.cfg.Gitignore), NoDefaultExcludes: *noDefaultExcludes || !config.On(e.cfg.DefaultExcludes),
		IncludeGenerated: *includeGenerated || !config.On(e.cfg.SkipGenerated), RespectProjectConfig: !*noProjectConfig && config.On(e.cfg.RespectProjectConfig),
		IncludeShadow: true, Shadow: e.feedbackShadow(), Enabled: map[string]bool{}, TypeMode: e.cfg.Types,
		NoCrossFileTaint: e.cfg.CrossFileTaint != nil && !*e.cfg.CrossFileTaint}
	if *typeMode != "" {
		opts.TypeMode = *typeMode
	}
	switch opts.TypeMode {
	case "", "basic", "full", "off":
	default:
		return fail(2, "--types: want basic, full or off, got %q", opts.TypeMode)
	}
	for id, s := range e.cfg.Rules {
		if s.Enabled != nil && !*s.Enabled {
			opts.Disabled[id] = true
		}
		if s.Enabled != nil && *s.Enabled {
			opts.Enabled[id] = true // also switches on opt-in (opinionated) rules
		}
		if s.Severity != "" {
			opts.Severity[id] = s.Severity
		}
	}
	pm := progress.Resolve(*progFlag, *quiet || *noProgress, os.Stderr)
	if *progFlag == "plain" && !*quiet && !*noProgress {
		pm = progress.Plain
	}
	bar := progress.New(os.Stderr, pm)
	if bar != nil {
		opts.Progress = bar.Update
	}
	rep, err := engine.Scan(opts)
	if err != nil {
		bar.Finish()
		return fail(3, "scan: %v", err)
	}
	rep.ToolVersion = version
	bar.Update(progress.Event{Phase: "sca", Findings: len(rep.Findings), Current: "dependency vulnerabilities (OSV.dev)"})
	e.runSCA(rep, *vulndbMode, sc, *quiet, *noGitignore, *noDefaultExcludes)
	if recs, err := e.feedback().Load(); err == nil && len(recs) > 0 {
		feedback.Apply(rep, recs, relTo(e.root, filepath.Join(e.feedback().Dir, "fp.jsonl")))
	}
	mode := e.cfg.AI.Mode
	if *aiMode != "" {
		mode = *aiMode
	}
	aiMsg := ""
	if mode != "off" {
		bar.Update(progress.Event{Phase: "ai", Done: 0, Total: pendingCount(rep), Findings: len(rep.Findings), Current: "confirming pending_ai findings"})
		if aiMsg, err = e.confirm(rep, *provider); err != nil {
			bar.Finish()
			return err
		}
	}
	bar.Update(progress.Event{Phase: "report", Findings: len(rep.Findings)})
	g := e.gate(*failOn, *minConf, *strict)
	g.ShowSuppressed, g.ShowRejected, g.ShowPending, g.ShowShadow, g.ShowHidden = *showSuppressed, *showRejected, *showPending, *showShadow, hidden.set
	if *reviewConf != "" {
		g.ReviewConfidence = *reviewConf
	}
	g.PendingDetail = e.pendingDetail(mode, *provider, rep)
	report.Annotate(rep, g)
	if err := e.saveState(rep); err != nil {
		bar.Finish()
		return fail(3, "state: %v", err)
	}
	bar.Finish() // clear the bar before anything is printed
	if err := writeOutputs(e, rep, *format, outputs, g); err != nil {
		return err
	}
	if aiMsg != "" && !*quiet {
		fmt.Fprintln(os.Stderr, aiMsg)
	}
	var result error
	code := 0
	if mode == "required" && pendingCount(rep) > 0 {
		code, result = 4, fail(4, "--ai required: %d finding(s) still pending_ai", pendingCount(rep))
	} else if n := report.Gate(rep, g); n > 0 {
		code, result = 1, exitErr{1, fmt.Errorf("%d gating finding(s) at or above %s", n, g.FailOn)}
	}
	if !*noRun && config.On(e.cfg.Runs.Enabled) {
		m, err := e.recordRun(rep, sc, g, start, code, opts.Disabled)
		if err != nil {
			fmt.Fprintln(os.Stderr, "crev: run history:", err)
		} else if m.Ledger != nil && !*quiet {
			fmt.Fprintf(os.Stderr, "run %s (%s): %d new, %d fixed, %d reopened since last run on this branch\n",
				m.ID, m.Branch, len(m.Ledger.New), len(m.Ledger.Fixed), len(m.Ledger.Reopened))
		}
	}
	if *withUI {
		if err := e.serveUI("127.0.0.1", *uiPort); err != nil {
			return err
		}
	}
	return result
}

func (e *env) runStore() runs.Store { return runs.Store{Dir: e.abs(e.cfg.Runs.Dir)} }

// configHash fingerprints everything that changes what a scan reports: config file, user rules, catalog.
func (e *env) configHash() string {
	h := sha256.New()
	if b, err := os.ReadFile(e.cfgPath); err == nil {
		h.Write(b)
	}
	for _, f := range e.custom {
		if b, err := os.ReadFile(f); err == nil {
			h.Write([]byte(f))
			h.Write(b)
		}
	}
	for _, r := range e.all {
		h.Write([]byte(r.ID + r.PackVersion))
	}
	return hex.EncodeToString(h.Sum(nil))[:16]
}

// recordRun writes .crev/runs/<branch>/<ts>-<id>/ (reports, AI handoff, metadata.json), updates the
// branch ledger and index.json, and applies retention.
func (e *env) recordRun(rep *findings.Report, sc *scope.Scope, g report.GateOptions, start time.Time, code int, disabled map[string]bool) (*runs.Meta, error) {
	st := e.runStore()
	gi := runs.DetectGit(e.root)
	m := &runs.Meta{Branch: gi.Branch, Commit: gi.Commit, Dirty: gi.Dirty, CrevVersion: version, RulePacks: map[string]string{},
		Versions: runs.VersionsOf(rep), ConfigHash: e.configHash(), FailOn: g.FailOn, Scope: sc, ExitCode: code}
	active := map[string]bool{}
	for _, r := range e.all {
		m.RulePacks[r.Pack] = r.PackVersion
		if !disabled[r.ID] {
			active[r.ID] = true
			m.ActiveRules = append(m.ActiveRules, r.ID)
		}
	}
	slices.Sort(m.ActiveRules)
	dir, err := st.Create(m)
	if err != nil {
		return nil, err
	}
	write := func(name string, fn func(io.Writer) error) error {
		f, err := os.Create(filepath.Join(dir, name))
		if err != nil {
			return err
		}
		defer f.Close()
		return fn(f)
	}
	if err := write("report.json", func(w io.Writer) error { return report.JSON(w, rep) }); err != nil {
		return nil, err
	}
	_ = write("report.sarif", func(w io.Writer) error { return report.SARIF(w, rep, e.byID, version, g) })
	_ = write("report.md", func(w io.Writer) error { report.Markdown(w, rep, g); return nil })
	if b, err := os.ReadFile(filepath.Join(e.abs(e.cfg.AI.HandoffDir), "batches.jsonl")); err == nil && pendingCount(rep) > 0 {
		_ = os.MkdirAll(filepath.Join(dir, "ai-handoff"), 0o755)
		_ = os.WriteFile(filepath.Join(dir, "ai-handoff", "batches.jsonl"), b, 0o644)
	}
	m.Counts = runs.CountsOf(rep)
	m.Counts.Gating = report.Gate(rep, g)
	m.DurationMS = time.Since(start).Milliseconds()
	l, err := st.LoadLedger(m.Branch)
	if err != nil {
		return nil, err
	}
	m.Ledger = l.Apply(rep, runs.Point{Run: m.ID, Commit: m.Commit, Time: m.Timestamp}, sc, active)
	if err := st.SaveLedger(l); err != nil {
		return nil, err
	}
	if err := st.Finish(m); err != nil {
		return nil, err
	}
	keep, age := e.cfg.Runs.Keep, time.Duration(e.cfg.Runs.MaxAgeDays)*24*time.Hour
	if removed, err := st.Prune(keep, age, time.Now()); err == nil && len(removed) > 0 {
		fmt.Fprintf(os.Stderr, "runs: pruned %d old run(s) (keep %d, max age %dd)\n", len(removed), keep, e.cfg.Runs.MaxAgeDays)
	}
	return m, nil
}

func cmdAI(args []string) error {
	if len(args) == 0 {
		return fail(2, "usage: crev ai export|run|status [path]")
	}
	sub := args[0]
	fs := flag.NewFlagSet("ai "+sub, flag.ContinueOnError)
	cfgPath := fs.String("config", "", "config file")
	rulesDir := fs.String("rules-dir", "", "packs directory")
	if err := parseInterspersed(fs, args[1:]); err != nil {
		return fail(2, "%v", err)
	}
	root := "."
	if fs.NArg() > 0 {
		root = fs.Arg(0)
	}
	e, err := setup(root, *cfgPath, *rulesDir, "")
	if err != nil {
		return err
	}
	switch sub {
	case "status":
		a := e.cfg.AI
		key := "unset"
		if a.APIKey() != "" {
			key = "set"
		}
		fmt.Printf("mode=%s provider=%s effective=%s base_url=%q model=%q api_key_env=%s (%s) batch_size=%d context_lines=%d cache=%s budget=none\n",
			a.Mode, a.Provider, a.EffectiveProvider(), a.BaseURL, a.Model, a.APIKeyEnv, key, a.BatchSize, a.ContextLines, a.CacheDir)
		return nil
	case "export", "run":
		rep, err := e.loadState()
		if err != nil {
			return err
		}
		provider := "cursor-skill"
		if sub == "run" {
			provider = "api"
		}
		msg, err := e.confirm(rep, provider)
		if err != nil {
			return err
		}
		if msg == "" {
			msg = "ai: nothing pending"
		}
		fmt.Println(msg)
		return e.saveState(rep)
	}
	return fail(2, "unknown ai subcommand %q", sub)
}

func cmdIngest(args []string) error {
	fs := flag.NewFlagSet("ingest", flag.ContinueOnError)
	root := fs.String("root", ".", "project root (where .crev/ lives)")
	cfgPath := fs.String("config", "", "config file")
	failOn := fs.String("fail-on", "", "gate threshold")
	runRef := fs.String("run", "latest", "run to update: latest | <branch>:latest | <run id or unique prefix>")
	format := fs.String("format", "text", "text|json|sarif|md for the updated report")
	var outputs multi
	fs.Var(&outputs, "output", "[fmt=]FILE, repeatable")
	if err := parseInterspersed(fs, args); err != nil {
		return fail(2, "%v", err)
	}
	if fs.NArg() == 0 {
		return fail(2, "usage: crev ingest [-root path] [--run latest|ID] responses.jsonl|-")
	}
	e, err := setup(*root, *cfgPath, "", "")
	if err != nil {
		return err
	}
	st := e.runStore()
	var run *runs.Meta
	var rep *findings.Report
	if m, rerr := st.Resolve(*runRef); rerr == nil {
		run = m
		if rep, err = st.Report(m); err != nil {
			return fail(2, "run %s: %v", m.ID, err)
		}
	} else if *runRef != "latest" {
		return fail(2, "%v", rerr)
	} else if rep, err = e.loadState(); err != nil {
		return err
	}
	var verdicts []ai.Verdict
	var raw [][]byte
	for _, p := range fs.Args() {
		var b []byte
		if p == "-" {
			b, err = io.ReadAll(os.Stdin)
		} else {
			b, err = os.ReadFile(p)
		}
		if err != nil {
			return fail(2, "%v", err)
		}
		vs, err := ai.ParseVerdicts(b)
		if err != nil {
			return fail(2, "%s: %v", p, err)
		}
		verdicts = append(verdicts, vs...)
		raw = append(raw, b)
	}
	items := ai.Pending(rep, e.byID, e.buildOpts(false))
	stats := ai.Ingest(items, verdicts, e.cache(), "cursor-skill")
	g := e.gate(*failOn, "", false)
	g.PendingDetail = "no verdict in the ingested responses; answer the remaining items and run `crev ingest` again"
	report.Annotate(rep, g)
	idx, _ := st.Index()
	if run == nil || idx.Latest == run.ID {
		if err := e.saveState(rep); err != nil {
			return err
		}
	}
	code := 0
	if report.Gate(rep, g) > 0 {
		code = 1
	}
	if run != nil {
		dir := st.RunDir(run)
		if err := writeFileFn(filepath.Join(dir, "report.json"), func(w io.Writer) error { return report.JSON(w, rep) }); err != nil {
			return err
		}
		_ = writeFileFn(filepath.Join(dir, "report.sarif"), func(w io.Writer) error { return report.SARIF(w, rep, e.byID, version, g) })
		_ = writeFileFn(filepath.Join(dir, "report.md"), func(w io.Writer) error { report.Markdown(w, rep, g); return nil })
		_ = os.MkdirAll(filepath.Join(dir, "ai-responses"), 0o755)
		for _, b := range raw {
			_ = os.WriteFile(filepath.Join(dir, "ai-responses", time.Now().UTC().Format(runs.TimeFormat)+".jsonl"), b, 0o644)
		}
		run.Counts = runs.CountsOf(rep)
		run.Counts.Gating = report.Gate(rep, g)
		run.ExitCode = code
		if l, err := st.LoadLedger(run.Branch); err == nil {
			if l.MarkRejected(rep, runs.Point{Run: run.ID, Commit: run.Commit, Time: time.Now().UTC()}) > 0 {
				_ = st.SaveLedger(l)
			}
		}
		if err := st.UpdateEntry(run); err != nil {
			return err
		}
	}
	if err := writeOutputs(e, rep, *format, outputs, g); err != nil {
		return err
	}
	target := "saved report"
	if run != nil {
		target = "run " + run.ID
	}
	fmt.Fprintf(os.Stderr, "ingest (%s): %d applied, %d unknown id(s), %d invalid; %d still pending_ai\n", target, stats.Applied, stats.Unknown, stats.Invalid, pendingCount(rep))
	if code > 0 {
		return exitErr{1, fmt.Errorf("%d gating finding(s) at or above %s", report.Gate(rep, g), g.FailOn)}
	}
	return nil
}

func writeFileFn(path string, fn func(io.Writer) error) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	return fn(f)
}

// cmdRuns: crev runs list|show|prune.
func cmdRuns(args []string) error {
	if len(args) == 0 {
		return fail(2, "usage: crev runs list [--branch B] | show [RUN] | prune")
	}
	fs := flag.NewFlagSet("runs", flag.ContinueOnError)
	root := fs.String("root", ".", "project root")
	cfgPath := fs.String("config", "", "config file")
	branch := fs.String("branch", "", "list: only this branch")
	asJSON := fs.Bool("json", false, "JSON output")
	if err := parseInterspersed(fs, args[1:]); err != nil {
		return fail(2, "%v", err)
	}
	e, err := setup(*root, *cfgPath, "", "")
	if err != nil {
		return err
	}
	st := e.runStore()
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	switch args[0] {
	case "list":
		idx, err := st.Index()
		if err != nil {
			return fail(2, "%v", err)
		}
		if *asJSON {
			return enc.Encode(idx)
		}
		for _, r := range idx.Runs {
			if *branch != "" && r.Branch != *branch {
				continue
			}
			c := r.Commit
			if len(c) > 9 {
				c = c[:9]
			}
			dirty := ""
			if r.Dirty {
				dirty = "+dirty"
			}
			fmt.Printf("%s  %-20s %-9s%-6s %-12s findings %-4d critical %-3d gating %-3d exit %d\n", r.ID, r.Branch, c, dirty, r.ScopeMode,
				r.Counts.Total, r.Counts.BySeverity["critical"], r.Counts.Gating, r.ExitCode)
		}
		return nil
	case "show":
		ref := "latest"
		if fs.NArg() > 0 {
			ref = fs.Arg(0)
		}
		m, err := st.Resolve(ref)
		if err != nil {
			return fail(2, "%v", err)
		}
		return enc.Encode(m)
	case "prune":
		removed, err := st.Prune(e.cfg.Runs.Keep, time.Duration(e.cfg.Runs.MaxAgeDays)*24*time.Hour, time.Now())
		if err != nil {
			return fail(3, "%v", err)
		}
		fmt.Printf("pruned %d run(s)\n", len(removed))
		return nil
	}
	return fail(2, "unknown runs subcommand %q", args[0])
}

// cmdUI: crev ui — local read-only web UI over .crev/runs and the rule catalog.
func cmdUI(args []string) error {
	fs := flag.NewFlagSet("ui", flag.ContinueOnError)
	root := fs.String("root", ".", "project root")
	cfgPath := fs.String("config", "", "config file")
	rulesDir := fs.String("rules-dir", "", "load packs from this directory instead of the embedded catalog")
	addr := fs.String("addr", "127.0.0.1", "bind address (keep loopback unless you know what you are doing)")
	port := fs.Int("port", 7317, "port (0 = pick a free one)")
	if err := parseInterspersed(fs, args); err != nil {
		return fail(2, "%v", err)
	}
	if fs.NArg() > 0 {
		*root = fs.Arg(0)
	}
	e, err := setup(*root, *cfgPath, *rulesDir, "")
	if err != nil {
		return err
	}
	return e.serveUI(*addr, *port)
}

func (e *env) serveUI(addr string, port int) error {
	all := make([]*rules.Rule, 0, len(e.byID))
	for _, r := range e.byID {
		all = append(all, r)
	}
	srv := &ui.Server{Root: e.root, Store: e.runStore(), Rules: all, Version: version}
	ln, err := net.Listen("tcp", net.JoinHostPort(addr, strconv.Itoa(port)))
	if err != nil {
		return fail(2, "ui: %v", err)
	}
	if ip := net.ParseIP(addr); addr != "localhost" && (ip == nil || !ip.IsLoopback()) {
		fmt.Fprintf(os.Stderr, "crev ui: WARNING: listening on non-loopback address %s; the UI has no authentication\n", addr)
	}
	fmt.Fprintf(os.Stderr, "crev ui: http://%s/  (Ctrl-C to stop)\n", ln.Addr())
	hs := &http.Server{Handler: srv.Handler(), ReadHeaderTimeout: 10 * time.Second}
	return hs.Serve(ln)
}

// cmdReport: crev report --html (static report from run data; layout is a placeholder until the
// final design/example lands, the data contract is htmlreport.Data).
func cmdReport(args []string) error {
	fs := flag.NewFlagSet("report", flag.ContinueOnError)
	root := fs.String("root", ".", "project root")
	cfgPath := fs.String("config", "", "config file")
	html := fs.Bool("html", false, "write a self-contained static HTML report")
	runRef := fs.String("run", "latest", "run: latest | <branch>:latest | id")
	out := fs.String("o", "crev-report.html", "output file (- = stdout)")
	dataOnly := fs.Bool("data", false, "write the report data model as JSON instead of HTML")
	if err := parseInterspersed(fs, args); err != nil {
		return fail(2, "%v", err)
	}
	if !*html && !*dataOnly {
		return fail(2, "usage: crev report --html [--run latest|ID] [-o FILE] | --data")
	}
	e, err := setup(*root, *cfgPath, "", "")
	if err != nil {
		return err
	}
	d, err := htmlreport.Build(e.runStore(), *runRef)
	if err != nil {
		return fail(2, "%v", err)
	}
	var w io.Writer = os.Stdout
	if *out != "-" {
		f, err := os.Create(*out)
		if err != nil {
			return fail(2, "%v", err)
		}
		defer f.Close()
		w = f
	}
	if *dataOnly {
		enc := json.NewEncoder(w)
		enc.SetIndent("", "  ")
		return enc.Encode(d)
	}
	if err := htmlreport.Render(w, d); err != nil {
		return fail(3, "%v", err)
	}
	if *out != "-" {
		fmt.Fprintln(os.Stderr, "wrote", *out)
	}
	return nil
}

func cmdVersions(args []string) error {
	fs := flag.NewFlagSet("versions", flag.ContinueOnError)
	cfgPath := fs.String("config", "", "config file")
	if err := parseInterspersed(fs, args); err != nil {
		return fail(2, "%v", err)
	}
	root := "."
	if fs.NArg() > 0 {
		root = fs.Arg(0)
	}
	e, err := setup(root, *cfgPath, "", "")
	if err != nil {
		return err
	}
	rep, err := engine.Scan(engine.Options{Root: e.root, Ignore: e.cfg.Ignore, Latest: e.latest(),
		NoGitignore: !config.On(e.cfg.Gitignore), NoDefaultExcludes: !config.On(e.cfg.DefaultExcludes), IncludeGenerated: !config.On(e.cfg.SkipGenerated)})
	if err != nil {
		return fail(3, "%v", err)
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	return enc.Encode(map[string]any{"unknown_version_policy": e.cfg.UnknownVersionPolicy, "units": rep.Units})
}

func cmdRules(args []string) error {
	const use = "usage: crev rules list [--pack P] [--origin custom] | show ID | validate [FILE|DIR ...] [--strict] [--skip-examples] [--json]"
	if len(args) == 0 {
		return fail(2, use)
	}
	fs := flag.NewFlagSet("rules", flag.ContinueOnError)
	pack := fs.String("pack", "", "filter by pack")
	origin := fs.String("origin", "", "list: filter by origin (custom|builtin)")
	rulesDir := fs.String("rules-dir", "", "packs directory (replaces the embedded catalog)")
	root := fs.String("root", ".", "project root (for .crev.yaml and .crev/rules/)")
	cfgPath := fs.String("config", "", "config file (default <root>/.crev.yaml)")
	strict := fs.Bool("strict", false, "validate: warnings (missing source citation, ...) fail too")
	skipExamples := fs.Bool("skip-examples", false, "validate: only compile queries; do not require/execute examples")
	asJSON := fs.Bool("json", false, "validate: JSON output")
	if err := parseInterspersed(fs, args[1:]); err != nil {
		return fail(2, "%v", err)
	}
	if args[0] == "validate" {
		return cmdRulesValidate(*root, *cfgPath, *rulesDir, fs.Args(), *strict, *skipExamples, *asJSON)
	}
	e, err := setup(*root, *cfgPath, *rulesDir, "")
	if err != nil {
		return err
	}
	switch args[0] {
	case "list":
		type c struct{ det, ai int }
		counts := map[string]*c{}
		for _, r := range e.all {
			if *pack != "" && r.Pack != *pack {
				continue
			}
			if (*origin == "custom" && r.Origin != "custom") || (*origin == "builtin" && r.Origin == "custom") {
				continue
			}
			o := ""
			if r.Origin == "custom" {
				o = " [custom: " + relTo(e.root, r.File) + "]"
			}
			tl := "-"
			if r.Trust != nil {
				tl = r.Trust.Level
			}
			fmt.Printf("%-44s %-9s %-12s %-11s %-13s %s%s\n", r.ID, r.Severity, r.Detection.Mode, tl, r.Pack, r.Title, o)
			if counts[r.Pack] == nil {
				counts[r.Pack] = &c{}
			}
			if r.Detection.Mode == "ai-confirm" {
				counts[r.Pack].ai++
			} else {
				counts[r.Pack].det++
			}
		}
		ps := slices.Sorted(maps.Keys(counts))
		for _, p := range ps {
			fmt.Fprintf(os.Stderr, "%s: %d rules (%d deterministic, %d ai-confirm)\n", p, counts[p].det+counts[p].ai, counts[p].det, counts[p].ai)
		}
		for _, ch := range e.changes {
			fmt.Fprintf(os.Stderr, "custom: %-8s %s (%s)\n", ch.Action, ch.ID, relTo(e.root, ch.File))
		}
		return nil
	case "show":
		if fs.NArg() == 0 {
			return fail(2, "usage: crev rules show ID")
		}
		r := e.byID[fs.Arg(0)]
		if r == nil {
			return fail(2, "unknown rule %s", fs.Arg(0))
		}
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.SetEscapeHTML(false)
		return enc.Encode(r)
	}
	return fail(2, "unknown rules subcommand %q\n%s", args[0], use)
}

// cmdRulesValidate checks user rule files: they must load and merge onto the catalog, and every
// added/patched/replaced rule must pass the same checks as built-ins (schema fields, query compiles
// against the real grammar, examples.bad matches and examples.good does not).
func cmdRulesValidate(root, cfgPath, rulesDir string, paths []string, strict, skipExamples, asJSON bool) error {
	abs, err := filepath.Abs(root)
	if err != nil {
		return fail(2, "%v", err)
	}
	if cfgPath == "" {
		cfgPath = filepath.Join(abs, ".crev.yaml")
	}
	cfg, err := config.Load(cfgPath)
	if err != nil {
		return fail(2, "config: %v", err)
	}
	if rulesDir == "" {
		rulesDir = cfg.RulesDir
	}
	var builtin []*rules.Rule
	if rulesDir != "" {
		builtin, err = rules.LoadFiles(rulesDir)
	} else {
		builtin, err = rules.LoadFS(catalog.FS, "packs/*/*.yaml")
	}
	if err != nil {
		return fail(2, "rules: %v", err)
	}
	if len(paths) == 0 {
		for _, d := range cfg.CustomRules {
			if !filepath.IsAbs(d) {
				d = filepath.Join(abs, d)
			}
			paths = append(paths, d)
		}
	}
	files, err := rules.CustomFiles(paths...)
	if err != nil {
		return fail(2, "%v", err)
	}
	type item struct {
		ID       string   `json:"id"`
		Action   string   `json:"action"`
		File     string   `json:"file"`
		Base     string   `json:"base,omitempty"`
		Errors   []string `json:"errors,omitempty"`
		Warnings []string `json:"warnings,omitempty"`
	}
	out := struct {
		Files    []string `json:"files"`
		LoadErr  string   `json:"load_error,omitempty"`
		Rules    []item   `json:"rules"`
		Errors   int      `json:"errors"`
		Warnings int      `json:"warnings"`
	}{Rules: []item{}}
	for _, f := range files {
		out.Files = append(out.Files, relTo(abs, f))
	}
	eff, changes, err := rules.ApplyCustom(builtin, files)
	if err != nil {
		out.LoadErr = err.Error()
		out.Errors++
	}
	byID := map[string]*rules.Rule{}
	for _, r := range eff {
		byID[r.ID] = r
	}
	for _, ch := range changes {
		it := item{ID: ch.ID, Action: ch.Action, File: relTo(abs, ch.File), Base: ch.Base}
		if r := byID[ch.ID]; r != nil && ch.Action != "disable" && r.File == ch.File {
			res := rulecheck.Check(r, rulecheck.Options{SkipExamples: skipExamples})
			it.Errors, it.Warnings = res.Errors, res.Warnings
			if ch.Action == "add" && r.Source.URL == "" {
				it.Warnings = append(it.Warnings, "no source.url: cite the official doc (or internal standard) the rule enforces")
			}
		}
		out.Errors += len(it.Errors)
		out.Warnings += len(it.Warnings)
		out.Rules = append(out.Rules, it)
	}
	if asJSON {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		enc.SetEscapeHTML(false)
		_ = enc.Encode(out)
	} else {
		if len(files) == 0 {
			fmt.Println("no user rule files found (looked in: " + strings.Join(paths, ", ") + ")")
		}
		if out.LoadErr != "" {
			fmt.Println("FAIL load:", out.LoadErr)
		}
		for _, it := range out.Rules {
			st := "ok  "
			if len(it.Errors) > 0 {
				st = "FAIL"
			} else if len(it.Warnings) > 0 {
				st = "warn"
			}
			fmt.Printf("%s %-8s %-40s %s\n", st, it.Action, it.ID, it.File)
			for _, e := range it.Errors {
				fmt.Println("     error:", e)
			}
			for _, w := range it.Warnings {
				fmt.Println("     warning:", w)
			}
		}
		fmt.Printf("files=%d rules=%d errors=%d warnings=%d\n", len(files), len(out.Rules), out.Errors, out.Warnings)
	}
	if out.Errors > 0 || (strict && out.Warnings > 0) {
		return fail(1, "")
	}
	return nil
}

// parseInterspersed allows flags after positional args (crev scan . --format json).
func parseInterspersed(fs *flag.FlagSet, args []string) error {
	fs.SetOutput(io.Discard)
	var pos []string
	for {
		if err := fs.Parse(args); err != nil {
			return err
		}
		args = fs.Args()
		if len(args) == 0 {
			break
		}
		pos = append(pos, args[0])
		args = args[1:]
	}
	return fs.Parse(append([]string{"--"}, pos...))
}

func cmdInit(args []string) error {
	fs := flag.NewFlagSet("init", flag.ContinueOnError)
	force := fs.Bool("force", false, "overwrite an existing .crev.yaml")
	if err := parseInterspersed(fs, args); err != nil {
		return fail(2, "%v", err)
	}
	root := "."
	if fs.NArg() > 0 {
		root = fs.Arg(0)
	}
	p := filepath.Join(root, ".crev.yaml")
	if _, err := os.Stat(p); err == nil && !*force {
		return fail(2, "%s exists (use --force to overwrite)", p)
	}
	if err := os.WriteFile(p, config.Template, 0o644); err != nil {
		return fail(2, "%v", err)
	}
	if err := os.MkdirAll(filepath.Join(root, ".crev", "rules"), 0o755); err != nil {
		return fail(2, "%v", err)
	}
	fmt.Println("wrote", p, "and .crev/rules/ (add .crev/* and !.crev/rules/ to .gitignore)")
	return nil
}

func cmdIndex(args []string) error {
	fs := flag.NewFlagSet("index", flag.ContinueOnError)
	root := fs.String("root", ".", "project root")
	asJSON := fs.Bool("json", false, "print the index (files, symbols, imports, stats) as JSON")
	sym := fs.String("symbol", "", "show definitions, references and call sites of NAME")
	file := fs.String("file", "", "show the indexed symbols and importers of PATH")
	if err := parseInterspersed(fs, args); err != nil {
		return fail(2, "%v", err)
	}
	if fs.NArg() > 0 {
		*root = fs.Arg(0)
	}
	abs, err := filepath.Abs(*root)
	if err != nil {
		return err
	}
	files, err := engine.ListFiles(abs, nil)
	if err != nil {
		return err
	}
	x := index.Build(abs, files, nil)
	out := os.Stdout
	switch {
	case *asJSON:
		enc := json.NewEncoder(out)
		enc.SetIndent("", "  ")
		return enc.Encode(x)
	case *sym != "":
		for _, d := range x.Defs[*sym] {
			fmt.Fprintf(out, "def   %s:%d  %s %s (exported=%v, stmts=%d, complexity=%d, body=%s%s)\n", d.File, d.Line, d.Kind, d.Name, d.Exported, d.Stmts, d.Complexity+1, d.BodyHash,
				map[bool]string{true: ", delegates to " + d.Delegate, false: ""}[d.Delegate != ""])
		}
		for _, c := range x.Calls[*sym] {
			fmt.Fprintf(out, "call  %s:%d  in %s\n", c.File, c.Line, c.Caller)
		}
		refs := x.RefFiles[*sym]
		names := slices.Sorted(maps.Keys(refs))
		for _, f := range names {
			fmt.Fprintf(out, "ref   %s (%d)\n", f, refs[f])
		}
	case *file != "":
		f := x.Files[filepath.ToSlash(*file)]
		if f == nil {
			return fail(1, "%s is not indexed", *file)
		}
		for _, s := range f.Symbols {
			fmt.Fprintf(out, "%5d  %-6s %s  refs=%d\n", s.Line, s.Kind, s.Name, x.RefsOutside(s))
		}
		for _, i := range x.ImportedBy[filepath.ToSlash(*file)] {
			fmt.Fprintf(out, "imported by %s\n", i)
		}
	default:
		keys := slices.Sorted(maps.Keys(x.Stats))
		for _, k := range keys {
			fmt.Fprintf(out, "%-18s %d\n", k, x.Stats[k])
		}
		fmt.Fprintf(out, "%-18s %s\n", "duration", x.Duration.Round(time.Millisecond))
	}
	return nil
}

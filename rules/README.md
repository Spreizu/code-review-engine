# Rule catalog

## Layout: one directory per pack, small files per topic

```
rules/packs/<pack>/<topic>.yaml       hand-edited rules   (first line: "# HAND-EDITED ...")
rules/packs/<pack>/<topic>.gen.yaml   generated rules     (first line: "# GENERATED ..."; never edit)
rules/data/*.yaml                     trust, governance, opt-in, xref, taxonomy, taint, versions
```

* **A pack is one language, framework or file type**: `java`, `kotlin`, `python`, `go`, `php`, `javascript`,
  `typescript`, `spring-boot`, `vue`, `nuxt`, `nuxt-ui`, `angular`, `react`, `payload`, `vueuse`, `android`,
  `gradle`, `maven`, `docker`, `kubernetes`, `terraform`, `github-actions`, `gitlab-ci`, `json`, `yaml`,
  `package-json`, `composer`, `protobuf`, `graphql`, `ytt`, `html`. The `pack:` field of every file equals its directory
  (the loader rejects a mismatch).
* **A topic file groups rules by theme**: `security`, `taint`, `llm`, `cert`, `cloud`, `supply-chain`,
  `simplification`, `migration` (deprecations/removals; split into `migration-v<major>` when a pack has more than
  120 of them, e.g. `spring-boot/migration-v3.gen.yaml`), `modernization`, `quality` (correctness,
  maintainability, style), `vapor`. Cross-cutting themes are **not packs**: a taint rule for Go lives in
  `go/taint.gen.yaml` and carries the tag `taint`. Theme tags: `taint`, `llm`, `cert`, `appsec`,
  `supply-chain`, `cloud`, `simplification`. `crev scan --packs` / `.crev.yaml packs:` accept a pack name or a
  theme tag (`--packs go,taint`); the UI rule browser filters by pack, topic and tag.
* **Single source of truth.** Generated files come only from `tools/rulegen/specs/*.py` (`rulegen.py gen`
  always regenerates every spec, routes each rule with `tools/rulegen/layout.py`, and deletes stale
  `*.gen.yaml` files). Hand-edited files are never touched by any tool. A rule id lives in exactly one file
  (duplicate ids fail loading). Ids are stable forever; moving a rule between files is not a rename.
* **Stable order.** Rules are sorted by id inside every file (rulegen writes them that way; rulecheck fails a
  hand-edited file that is out of order or lacks its header), so diffs stay small.
* **New rules.** Hand-written: add to `rules/packs/<pack>/<topic>.yaml` (create the file with the HAND-EDITED
  header if the topic is new). Generated: add to the pack's spec. `tools/ruleupdate` names the file to edit for
  a citation whose quote disappeared (the hand-edited file, or the spec behind a `.gen.yaml`) and the per-pack
  `migration.yaml` where a rule drafted from a new deprecation line belongs.
* `data/latest-versions.yaml`: latest known releases, used when a version cannot be detected (`unknown_version_policy: assume-latest`).
* Validate everything (schema fields, query compilation against the real grammars, golden examples, citations in
  `sources.yaml`, layout headers and sort order):

  ```sh
  go run ./tools/rulecheck rules/packs/*/*.yaml
  ```
* Regenerate and re-verify the generated files (re-fetches every cited URL and checks each `source.quote` on the
  page), then refresh `sources.yaml`/`sources.md`:

  ```sh
  python3 tools/rulegen/rulegen.py verify   # all specs, or: verify nuxt
  python3 tools/rulegen/rulegen.py gen
  python3 tools/rulegen/sources.py
  ```
* Inspect a tree while writing queries: `go run ./tools/astdump <grammar> FILE ['<query>']` or `go run ./tools/sexp <java|javascript|typescript|tsx|vue> FILE [x]`.
* Authoring rules: cite an official doc (`source.url`, `doc_version`, `retrieved`, plus a short verbatim `quote`), give a `bad` and a `good` example, capture the reported node as `@match`, keep predicates *inside* the pattern's parentheses, and use `ai-confirm` + `ai_question` whenever the syntax alone can't decide. Do not mirror deprecated linter rules.

Unique rule counts (2026-10-10, `rulecheck`: `total=3005 failures=0`; declared modes, before trust levels):

| Pack | Rules | deterministic (declared) | ai-confirm (declared) | topic files (`*` = generated) |
|---|---|---|---|---|
| android | 15 | 9 | 6 | security* |
| angular | 93 | 87 | 6 | migration*, modernization*, quality*, security* |
| composer | 26 | 25 | 1 | migration*, modernization*, quality*, security* |
| docker | 65 | 57 | 8 | migration*, modernization*, quality*, security*, supply-chain* |
| github-actions | 10 | 9 | 1 | security*, supply-chain* |
| gitlab-ci | 4 | 4 | 0 | security*, supply-chain* |
| go | 165 | 123 | 42 | maintainability*, migration*, modernization*, quality*, security*, simplification*, taint* |
| gradle | 82 | 77 | 5 | migration*, modernization*, quality*, security* |
| graphql | 35 | 28 | 7 | migration*, modernization*, quality*, security* |
| html | 13 | 13 | 0 | maintainability* |
| java | 330 | 214 | 116 | cert*, maintainability*, migration, migration*, modernization, modernization*, quality, quality*, security, security*, simplification*, taint* |
| javascript | 294 | 233 | 61 | llm*, maintainability*, migration, migration*, modernization, modernization*, quality, quality*, security, security*, simplification*, taint* |
| json | 36 | 34 | 2 | migration*, modernization*, quality*, security* |
| kotlin | 167 | 120 | 47 | maintainability*, migration*, modernization*, quality*, security*, simplification*, taint* |
| kubernetes | 24 | 16 | 8 | migration*, quality*, security* |
| maven | 31 | 27 | 4 | migration*, modernization*, quality*, security* |
| nuxt-ui | 64 | 58 | 6 | migration*, quality* |
| nuxt | 99 | 87 | 12 | migration, migration*, modernization, quality, quality*, security, security* |
| package-json | 34 | 31 | 3 | migration*, modernization*, quality*, security*, supply-chain* |
| payload | 76 | 64 | 12 | migration*, modernization*, quality*, security* |
| php | 188 | 141 | 47 | maintainability*, migration*, modernization*, quality*, security*, simplification*, taint* |
| protobuf | 46 | 36 | 10 | migration*, modernization*, quality* |
| python | 265 | 202 | 63 | llm*, maintainability*, migration*, modernization*, quality*, security, security*, simplification*, taint* |
| react | 51 | 43 | 8 | migration*, modernization*, quality*, security* |
| spring-boot | 323 | 306 | 17 | migration, migration*, migration-v2*, migration-v3*, migration-v4*, quality, quality*, security, security* |
| terraform | 121 | 109 | 12 | cloud*, migration*, modernization*, quality*, security* |
| typescript | 100 | 85 | 15 | migration, migration*, modernization, quality, quality* |
| vue | 121 | 107 | 14 | migration, migration*, quality, quality*, security, security*, vapor |
| vueuse | 37 | 33 | 4 | migration*, modernization*, quality* |
| yaml | 43 | 40 | 3 | modernization*, quality*, security* |
| ytt | 47 | 42 | 5 | migration*, modernization*, quality* |
| **total** | **3005** | **2460** | **545** | |

## Your own rules: `.crev/rules/` (add, edit, override, disable)

User rules are first-class: they live in the repo, are reviewed like code, and are layered over the
embedded catalog **by rule id** on every `crev scan` / `crev rules list|show`.

* Location: every `*.yaml` / `*.yml` under `.crev/rules/` (recursive). Change or extend with
  `custom_rules:` in `.crev.yaml` (list of dirs, files or globs, relative to the project root):

  ```yaml
  custom_rules: [.crev/rules, tools/lint/crev/*.yaml]
  ```
* File layout = rule-pack layout; `pack` (default `custom`) and `pack_version` (default `local`) are optional.
  Schema: `schemas/custom-rules.schema.json` (entries reuse `rule-pack.schema.json#/$defs/rule`).
* Per entry, keyed by `id`:

  | Entry | Effect |
  |---|---|
  | new id, complete rule | **add** (needs `title, language, kind, category, severity, applies_to, detection, message, examples`; `source` strongly recommended) |
  | built-in id, some fields | **patch**: fields deep-merge onto the built-in (maps merge recursively; scalars and lists replace) |
  | built-in id + `override: replace` | **replace** the built-in entirely (nothing inherited) |
  | built-in id + `disabled: true` | **disable** (remove) the built-in |

  Files are applied in lexical path order, so `20-team.yaml` wins over `10-org.yaml`. Unknown fields,
  unknown ids for `disabled`/`replace`, and duplicate ids in one file are errors (typos never silently no-op).

  ```yaml
  # .crev/rules/team.yaml
  pack: team
  rules:
    - id: GO-QUAL-RECEIVER-NAME-THIS        # patch: escalate + narrow scope
      severity: major
      detection: {files: ["internal/**/*.go"]}
    - id: GO-QUAL-PACKAGE-NAME-GENERIC      # disable
      disabled: true
    - id: TS-ANY                       # patch the version range only
      applies_to: {typescript: ">=5.0"}
    - id: TEAM-NO-FOO                  # add
      title: Do not name variables foo
      language: go
      kind: anti-pattern
      category: style
      severity: minor
      applies_to: {go: "*"}
      detection:
        mode: deterministic
        engine: tree-sitter
        query: '((var_spec name: (identifier) @match) (#eq? @match "foo"))'
      message: Pick a descriptive name.
      source: {url: "https://go.dev/doc/effective_go#names", doc: Effective Go, doc_version: "1.25", retrieved: "2026-10-10"}
      examples: {bad: "var foo = 1\n", good: "var count = 1\n"}
  ```
* Validate before committing (also good as a CI step / pre-commit hook):

  ```sh
  crev rules validate                 # files from custom_rules (default .crev/rules/)
  crev rules validate path/to/x.yaml  # specific files/dirs
  crev rules validate --strict        # warnings (e.g. missing source citation) fail too
  crev rules validate --skip-examples # only compile queries (drafting)
  crev rules validate --json
  ```

  It runs the same checks as the catalog's `rulecheck`: required fields and enums, version-range
  syntax, top-level-predicate detection, the query compiled against the real grammar (JavaScript
  rules also under TypeScript, `jsx` rules under TSX), and the golden examples executed through the
  engine (`bad` must match, `good` must not). Exit 1 on errors.
* Inspect the result: `crev rules list --origin custom` (stderr lists every add/patch/replace/disable)
  and `crev rules show ID` (effective merged rule).
* Simple per-rule switches still work in `.crev.yaml` (`rules: {ID: {enabled: false, severity: info}}`);
  use `.crev/rules/` when you change detection, scope, versions or messages, or add rules.
* `rules_dir:` / `--rules-dir` is different: it *replaces* the embedded catalog (catalog development).
* `.crev/` is excluded from scans (state, runs and user rules are not linted as project files).

## Linter equivalents (`xref`) and params

`xref:` entries can be `https://` links, related crev rule ids, or **linter equivalents** written as `tool:id`, for example `eslint:no-eval`, `typescript-eslint:@typescript-eslint/no-explicit-any`, `ruff:S307`, `govet:lostcancel`, `hadolint:DL3007` or `yamllint:truthy`. When a project switches that linter rule off, in its config or with an inline disable comment, crev suppresses the equivalent finding and records why (see PLAN.md §6.6a). Built-in mappings live in `rules/data/xref.yaml`; regenerate them with `python tools/rulegen/xref.py --ruff <(ruff rule --all --output-format json)`. Custom rules in `.crev/rules/` can add their own `tool:id` entries.

Thresholds that a project may configure are declared as params and referenced as `${name}`:

```yaml
params:
  max:
    default: 80
    from: [yamllint:line-length.max, editorconfig:max_line_length.max]
detection:
  filters: ['file.has_re:(?m)^[^\n]{${max},}$']
message: Line longer than ${max} characters
```

## Simplification rules (`engine: index`) and multi-file examples

`simplify-*.yaml` packs implement the simplification layer (see PLAN §6.6b). They are advisory: `category: simplification` or `test`, severity info/minor only, and they never gate CI. Index rules use `detection.engine: index` plus `detection.check` (one of the checks in `internal/index.Checks`) and optional `detection.config`. Their examples are small repos:

```yaml
examples:
  bad: |
    // file: src/a.js
    export function normalize(s) { ... }
    // file: src/b.js
    export function clean(v) { ... }      # same normalized body -> hit
  good: |
    // file: src/load.js (existing)       # "(existing)" = not part of the simulated diff
    ...
```

A hand-written helper that the stdlib replaces is pure data. For example:

```yaml
detection: {mode: ai-confirm, engine: index, check: helper-replacement,
            config: {names: [unique, dedupe], api: "[...new Set(xs)]", uses: ["new Set"], requires_loop: true}}
```

## False-positive policy

False positives must never reach the review list. The mechanisms, in order:

1. **Review list** = `confirmed` findings plus `ai_confirmed` findings at `ai.review_confidence`
   (default `high`). `pending_ai`, `ai_uncertain`, `ai_rejected`, below-threshold `ai_confirmed`,
   `shadow` and `suppressed` findings are kept in every report and run (for audit) with a
   `hidden_reason` (`pending_ai`, `ai_rejected`, `ai_uncertain`, `ai_low_confidence`, `shadow`,
   `suppressed_config`, `suppressed_inline`, `crev_ignore`) and a one-line `hidden_detail`. They
   are listed only with `--show-hidden[=reason|group,...]` (groups: pending, rejected, suppressed,
   shadow; old aliases `--show-pending` etc. still work) or the **Show hidden** toggle in
   `crev ui`. The CLI summary counts them per reason and says why (e.g. AI step off). Only
   review-list findings can gate CI; SARIF carries the review list plus suppressions.
2. **Precision tier** (`precision: high|medium|low`). The default is `high` for deterministic rules
   and `low` for ai-confirm rules. A rule with known FP risk is `low`, and rulecheck rejects
   `low` + `deterministic`.
3. **Regressions** (`examples.regressions: [{code, path?, note?}]`). Every false positive that was
   fixed (from self-scan, a corpus run, linter fixtures or `crev feedback fp`) is kept as a
   must-not-match example, and rulecheck runs it. A `path` checks the files/exclude globs, for
   example test files.
4. **Context guards**:
   * `detection.requires_config: [yamllint, editorconfig]`: opinionated style rules only run when
     the project adopted the tool.
   * Capture/function/ancestor filters:
     * `cap.has_re:NAME:re` and `cap.lacks_re:NAME:re`;
     * `func.has_re` and `func.lacks_re`;
     * `ancestor.has_re:KIND|KIND:re` and `ancestor.lacks_re:KIND|KIND:re`;
     * `parentkind.has_re:KIND|KIND:re` and `parentkind.lacks_re:KIND|KIND:re` (direct parent of one of the kinds, e.g. a literal inside an all-literal deny-list);
     * `{cap:NAME}` inside any regex filter.
     * `type.is:CAP:regex`, `type.not:CAP:regex`, `type.not_or_unknown:CAP:regex` on the resolved
       type of capture CAP (`internal/types`; unknown never matches `type.is` / `type.not`);
     * `type.differ:A:B` (built-in types that cannot be equal), `type.vs_text:A:T` (value vs written
       annotation), `type.eq:A:B` / `type.eq_text:A:T` (same non-empty type).
5. **Quarantine** (`status: shadow` with `status_reason`). The rule runs and its hits are counted
   in `report.shadow` and kept with status `shadow` / `hidden_reason: shadow`, never listed by
   default and never gating. Set it in a pack, or centrally in `rules/data/governance.yaml`, which also takes
   `precision` overrides.
6. **Feedback**: `crev feedback fp <fingerprint> [--reason ...]`
   * It suppresses that finding from then on.
   * It writes a regression stub to `<state_dir>/feedback/regressions/<RULE>.yaml`.
   * After `feedback.fp_threshold` (default 3) distinct FPs against the current `rule_version`,
     it demotes the rule to shadow.
   * Bumping `rule_version` when the rule is fixed lifts the demotion.
   * `crev feedback list` shows the records and `crev feedback undo <prefix>` removes one.
7. **Opt-in** (`rules/data/optin.yaml`, generated by `tools/rulegen/optin.py`). Opinionated rules that
   are outside their linter's recommended set report only when the project's linter config enables
   an equivalent rule, or when `.crev.yaml` sets `rules: {ID: {enabled: true}}`. Dropped hits are
   counted in `stats.opt_in_not_enabled`. Security rules cannot be opt-in.
8. **Test scoping** (`exclude_tests: true` in governance). Rules whose pattern is the accepted idiom in
   tests (fake credentials, `!!`/`any` in assertions, requests without timeouts) do not run on test
   files.
9. **Trust levels** (`rules/data/trust.yaml`, generated by `go run ./tools/trust classify && go run ./tools/trust metamorphic && go run
   ./tools/trust compute`):
   * levels: `proven`, `measured`, `unproven`, `quarantined` (thresholds in `internal/rules/trust.go`);
   * an unproven deterministic rule runs as ai-confirm, **except** `match_kind: exact-api` rules:
     version-gated (`applies_to` has a real range) deprecation/removal/migration rules whose detection
     is an exact identifier/import/config-key/dependency match (every query pattern carries an
     `#eq?`/`#any-of?` predicate or a `#match?` regex that is anchored and matches a finite literal set;
     config `key`/`key_any_of`; manifest dependency name). These report directly even when unproven.
     Classifier: `internal/rules/matchkind.go`; list: `rules/data/matchkind.yaml`, written by
     `go run ./tools/trust classify` (run it after rulegen); audit table at the end of
     `tools/trust/report.md`. rulecheck fails when the list and the classifier disagree in either
     direction;
   * rulecheck fails deterministic rules whose labelled precision is below 0.90;
   * a new rule starts unproven until the harnesses have evidence for it.
   * Distribution per pack: `tools/trust/report.md`.

Filters: `sfc.has_re:` / `sfc.lacks_re:` test the whole `.vue` single-file component when a script
rule runs on its extracted `<script>` block (e.g. the `<script setup vapor>` marker).

Security rules carry `cwe`, `owasp` (Top 10 2021 and 2025) and `asvs` (5.0). These come from the
rule, or from `rules/data/taxonomy.yaml`, which `tools/rulegen/taxonomy.py` generates. Rulecheck
fails any security rule that has no CWE.

## Rule ids

Ids follow `<PACK>-<CATEGORY>-<NAME>`: PACK is the pack code (`JAVA`, `JS`, `TS`, `PY`, `GO`, `KT`,
`PHP`, `SB` for spring-boot, `TF`, `KUBE`, `GHA`, ...), CATEGORY the topic file code (`SEC`
security, `TAINT`, `QUAL` quality, `MAINT` maintainability, `MIG` migration, `MOD` modernization,
`SIMP` simplification, `CERT`, `SUPPLY` supply-chain, `CLOUD`, `LLM`). Specs may keep emitting
legacy ids; `rulegen.py gen` applies `tools/rulegen/ruleid.py`. `tools/rulegen/renames.yaml` lists
legacy -> current ids for the generator only; crev-ignore comments and `.crev` settings take current ids.

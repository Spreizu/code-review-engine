# AGENTS.md

Guide for coding agents (Cursor) working on crev.

## What this is
crev is a code review engine in Go built on go-tree-sitter. It finds good and bad practices across
32 rule packs (Java, Spring Boot, JS/TS, Vue, Nuxt, React, Angular, Python, Go, PHP, Kotlin, config
and infra files, HTML/CSS and more). Rules cite official, version-aware sources. Findings are reported
directly when a rule is proven precise, otherwise an AI confirms them. Integrations: local CLI, CI,
and `crev ui`. Roadmap and architecture: `PLAN.md`. Usage: `README.md`. Rule authoring: `rules/README.md`.
Queued work: `TASKS.md`.

## Layout
- `cmd/crev`: CLI entry point.
- `internal/`: `engine` (scans), `rules` (loading, trust policy in `trust.go`), `versions`, `scope` (diff
  scans), `index` (repo-wide index), `taint`, `types` (type resolver), `ai`, `config`, `projcfg`
  (project linter configs), `findings`, `runs` (scan history), `ui` (`crev ui`, embedded `static/`),
  `report`, `htmlreport`, `sca` (OSV dependency scan), `feedback`, `grammars` (vendored tree-sitter C), `rulecheck`.
- `rules/packs/<pack>/<topic>.yaml`: hand-edited rules. `<topic>.gen.yaml`: generated, first line
  `# GENERATED ...`, never edit; change `tools/rulegen/specs/*.py` and regenerate.
- `schemas/`: rule pack JSON schema.
- `rules/data/`: trust, governance, opt-in, xref, taxonomy, taint, frameworks, latest versions.
- `tools/rulecheck` (validate rules), `tools/corpus` (false-positive harness on pinned OSS repos,
  `corpus.yaml`, clones cached in `tools/corpus/cache`, not committed), `tools/bench` (benchmarks),
  `tools/trust` (trust computation, gated triage), `tools/gap` (Sonar/Semgrep/Snyk/OWASP/CWE coverage),
  `tools/ruleupdate` (doc drift; never edits rules), `tools/rulegen` (generators), `tools/astdump`, `tools/sexp`.
- `skills/crev-review/SKILL.md`: Cursor skill so the chat agent acts as the AI reviewer.

## Build and test
- Go per `go.mod` (`go 1.23`, toolchain `go1.27.2`). cgo and a C compiler are required.
- Build: `CGO_ENABLED=1 go build -o crev ./cmd/crev`
- Test: `go test ./...`
- Rules: `go run ./tools/rulecheck $(find rules/packs -name '*.yaml')` must report 0 failures.
- Keep the executable small (about 25 MB now; do not grow it without reason). The UI stays
  framework-free and under 5 MB.

## Adding or changing a rule
1. Pick the pack by language, framework or file type. Topics (security, a11y, ...) are tags, not packs.
2. ID format `<PACK>-<CATEGORY>-<NAME>`. Follow `schemas/` and `rules/README.md`.
3. Cite a current official source and quote it. Check the source matches today's language or
   framework versions (old standards such as CERT for Java 6/7 need re-validation).
4. Add good and bad examples, including near-misses that must not fire.
5. Run rulecheck, then `go run ./tools/corpus run` (see `tools/corpus/README.md`) and inspect new hits.
6. Recompute trust: `go run ./tools/trust classify && go run ./tools/trust metamorphic && go run ./tools/trust compute`.
   Levels are `proven`, `measured`, `unproven`, `quarantined`; thresholds live in `internal/rules/trust.go`.
7. Generated rules: edit the spec, run `rulegen.py`, then rulecheck and `go test ./...`.

## Policies
- False positives must never reach the review list.
- A rule reports directly only when proven precise (>=95%, Wilson lower bound) or it is an
  exact-match version/migration rule. Everything else is AI-confirmed.
- Linter suppressions count as true positives when measuring (they usually mark a real problem),
  but crev still honors them when reporting.
- Respect project linter configs (ESLint, Oxlint, tsconfig, ...) and `crev-ignore`,
  `crev-ignore-next-line`, `crev-ignore-file`.
- Report everything, even what other linters cover. CI fails only on critical findings.
- Assume the latest version when none is detected.
- Messages describe the actual issue. No "Ponytail:" wording.
- Greenfield: renaming rule IDs and tags is fine.

## AI confirmation
Configured under `ai:` in `.crev.yaml` (template: `internal/config/template.crev.yaml`): `mode`,
`provider` (`auto` uses the API when `base_url` + `model` + key resolve, else `cursor-skill`),
`base_url`, `model`, `api_key_env` (env var name, default `CREV_AI_API_KEY`; never store a key).
Env `CREV_AI_BASE_URL` / `CREV_AI_MODEL` override. No endpoint is configured yet (this repo's
`.crev.yaml` has `ai.mode: off`); use the `skills/crev-review` skill in Cursor instead.

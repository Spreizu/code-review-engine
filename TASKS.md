# TASKS.md

Queued work. Nothing here is started unless noted.

## Rule validation and promotion
- [x] Resample rules fixed after `ec701a7` (Kotlin, PHP, TS fixes, `PHP-MIG-REFLECTION-GETCLASS`).
- [x] Sampled hit reviews for vue, nuxt, nuxt-ui, angular, react, payload, vueuse, spring-boot,
      terraform and the other config packs, plus `CSS-QUAL-DUPLICATE-SELECTOR` and `JAVA-MOD-MATH-CLAMP-001`.
- [x] Investigate direct-report count drops in css, json, protobuf, vue.
- [x] Write `tools/trust/sampled-review.md`.
- [ ] Act on `tools/trust/gated-triage.tsv`: 779 A (fixable by construction), 782 B (need data),
      427 C (stay behind AI). A first, then B.
      Started: PHP-MIG-REFLECTION-GETCLASS type gate, PY-SEC-RANDOM-SESSION-VALUE jitter/span FPs,
      CSS-QUAL-DUPLICATE-SELECTOR `:root`/`:host` skip, GO-MIG exact-api version gates, NG-MIG-JSONP
      anchored mcall, JAVA File.toURL / ThreadGroup / Thread.stop type gates. Remaining A/B need a
      corpus JSON restore (cache empty locally).
- [x] Regenerate the stale per-pack table in `tools/trust/gated-triage.md` from the tsv.
- [ ] Final promotion pass: bigger corpus, fix-commit differential, near-miss tests.
      Near-miss regressions added for this pass's A-class fixes. Bigger corpus and fixdiff
      blocked: `tools/corpus/cache` is empty and m8 JSON is not on disk.

## Measurement
- [ ] Re-measure Sonar, OWASP Benchmark, DVWA/WebGoat, ASVS and bench A.
- [ ] Re-run bench D (crev + full AI) and E (crev + AI on risky hunks).

## Coverage and engine
- [ ] Implement the 184 doable Sonar rules in `tools/gap/sonar-infeasible.md`.
      The 184 figure is stale. Regenerated from a fresh SonarCloud catalog: tree-sitter
      backlog is 67 keys. Syntactic subset is implemented; leftovers need types,
      frameworks, tests, or are commercial/404.
- [x] Type resolver and full-type mode, then retry type-dependent rules.
      Syntax-only resolver (`internal/types`): inheritance/embeds, casts, Go structs, known
      stdlib returns; `--types full` cross-file prepass. Type-gated retry: boxed toString /
      Boolean condition / redundant cast / boxed parse, JS for-of / call-non-callable, Python
      await / subscript. Remaining Sonar `types` keys need hierarchy, overloads, or a compiler.
- [x] Framework models and inter-procedural/cross-file taint.
      Framework models in `rules/data/frameworks.yaml` (import-guarded sources/sinks). Cross-file
      summaries (`internal/taint/project.go`) follow imported functions and class/instance methods
      when the call provably names one candidate. Remaining: overloads, variadics, nested
      functions, aliasing, and a compiler-grade call graph.
- [x] OWASP expansion: ASVS 5.0, API, Mobile, LLM, Docker and Kubernetes Top 10s, Proactive Controls, Cheat Sheet Series.
      Mapper covers every project (`tools/gap/owasp.py`, `cheatsheets.py`). ASVS 121/121, API/Mobile/MASVS
      code-verifiable items, LLM (scope was `^LLM-`, now `LLM-` so `JS-LLM-*`/`PY-LLM-*` count), Docker,
      Kubernetes and Proactive Controls are at 100% of code-verifiable. Cheat Sheet Series 58/68.
      Added FLAG_SECURE / minSdk Android rules, Gradle CWE/OWASP tags, JS/Java IDOR (API1). Remaining:
      10 code-verifiable cheat sheets with no dedicated rule (gRPC, Web Cache, Node/Java/JS overview
      sheets, FastAPI, Laravel, Symfony, Bean Validation, NodeJS Docker); MASVS AUTH/RESILIENCE/PRIVACY
      and API6/LLM08/LLM09 stay n/a (process/runtime). Full BOLA still needs an authz graph.

## Corpus data
- [x] Mine linter suppressions and autofix commits (suppressed spots count as real hits).
      `tools/corpus suppressions` joins inline disables in clones with `run` hits (TP).
      `tools/corpus autofix` mines lint-fix commits and parent-vs-fix scans (like `fixdiff`).
      Both feed `tools/trust compute`.
- [x] Run real linters on the same code for agreement.
      `tools/corpus agree` runs oxlint/ruff/hadolint/yamllint when present; same-line
      agreement via xref is a labelled TP. Needs `fetch` + `run` locally to produce JSON.
- [ ] Grow the clean corpus to about 1,000 repos.
- [ ] Bring in CVE and bug-fix datasets.

## Bugs
- [ ] Fixed findings don't always land in the Fixed section after a rerun. Check dirty working-tree
      state versus broken cross-run matching (`internal/runs`).

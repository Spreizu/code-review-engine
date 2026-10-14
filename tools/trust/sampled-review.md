# Sampled hit review

Corpus evidence: `tools/trust compute -label m8` (103 OSS repos, 561 labelled linter-suite rules). Compact per-repo JSON for m8 is not in the working tree (gitignored and not present locally), so this pass reviews committed `report.md` summaries, `rules/data/trust.yaml`, `tools/corpus/labels.yaml`, and the gated triage TSV. Construction fixes below are in the specs; a follow-up `corpus run -label m8` will re-measure hit volume.

## Direct-report drops (css, json, protobuf, vue)

Reported = `confirmed` with AI off (deterministic / exact-api / proven-promoted). Pending = demoted or declared ai-confirm.

| pack | before (reported) | after | m3 | m8 (trust.yaml) | why reported count fell |
|---|---|---|---|---|---|
| css | (pack did not exist) | — | — | 10 proven + 5 measured; 12 demoted | First m8 run lit up `CSS-QUAL-DUPLICATE-SELECTOR` (121 hits / 13 repos). Trust treats volume as an anomaly, so the rule was demoted off the review list. Other CSS quality rules that already have linter-suite precision stay proven. |
| json | 46 | 1 | 18 | 0 proven, 5 measured, 30 demoted | `JSON-QUAL-NON-ISO-DATE` was 46 hits on dotted version strings (`21.2.12` in package.json). Query now requires a 19xx/20xx year; remaining json noise is `JSON-QUAL-EXCESS-PRECISION` (2313 pending) and `JSON-SEC-HTTP-URL` (1136 pending), both behind AI. |
| protobuf | 142 | 89 | 67 | 0 proven, 16 measured, 22 demoted | High-volume style rules (`PROTO-MOD-MIGRATE-TO-EDITIONS` 41, `PROTO-QUAL-FIELD-SNAKE-CASE` 33, `PROTO-QUAL-ENUM-ZERO-VALUE-SUFFIX` 23) were demoted. Remaining direct reports are exact naming checks (enum UPPER_SNAKE, language-keyword fields) with no anomaly. |
| vue | 112 | 62 | 42 | 10 proven, 15 measured, 80 demoted | `VUE-QUAL-HTML-BUTTON-HAS-TYPE` (62) and `VUE-QUAL-NO-STATIC-INLINE-STYLES` (17) were volume-demoted. `VUE-MIG-GLOBAL-API-001` (15) still reports as exact-api. Vue pack also grew (121 → 152 rules, including a11y), which added pending rather than confirmed hits. |

None of these drops are a matcher regression that lost true positives of a proven rule. They are the trust policy doing its job: unproven high-volume rules leave the review list until a sampled review or a tighter query.

## Resample after `ec701a7` (Kotlin, PHP, TS, `PHP-MIG-REFLECTION-GETCLASS`)

`PHP-MIG-REFLECTION-GETCLASS` was left `ai-confirm` after a name-heuristic filter (`cap.has_re:o:(?i)param`) because 13 corpus hits (`repo>=10`) were DI/Console `getClass()` / `isArray()` look-alikes. The heuristic is now replaced with `type.is:o:ReflectionParameter`. Unknown receivers do not match, so look-alikes stay off the review list. Mode is deterministic; `go run ./tools/trust classify` now lists it as exact-api (763 exact-api rules).

Kotlin / TypeScript post-`ec701a7` fixes already have regressions in `tools/rulegen/specs/_fp.py` (`KT-DEPRECATED-NO-REPLACEWITH`, `KT-WEAK-HASH`, `TS-NO-REQUIRE-IMPORTS`, `TS-NO-UNSAFE-FUNCTION-TYPE`, `TS-NO-EMPTY-OBJECT-TYPE`). m8 trust shows no remaining volume anomaly on those IDs.

## Pack sampled-hit notes

Flagged rules in the latest committed OSS summaries (m3, after) for the packs listed in TASKS.md. Verdicts use the same policy as `labels.yaml`: a linter suppression at the hit is a TP; a look-alike or generated/test idiom is an FP.

| pack / rule | evidence | sample verdict | action |
|---|---|---|---|
| `CSS-QUAL-DUPLICATE-SELECTOR` | 121 hits / 13 repos (m8). stylelint suite: TP 5 FP 0 FN 23. | Dominant FP: splitting custom properties across repeated `:root` / `:host` blocks. Same selector in two top-level `.card` blocks is a TP. | Filter `css.dup_selector` now skips `:root` and `:host`. Re-measure; if volume falls below 15 with 0 sampled FP, the rule can leave ai-confirm. |
| `JAVA-MOD-MATH-CLAMP-001` | 3 reported in m2/m3 (1 repo); 0 corpus hits in m8 (`own examples only`). | Nested `Math.max`/`Math.min` is an exact identifier pattern (TP when it fires). Hits disappeared because the rule is modernization (not ExactAPI) and was demoted; m8 no longer records them as confirmed. | Keep deterministic in the spec. Needs ≥3 labelled TPs from a rescan of Java 21+ corpus units (commons-lang / jackson-databind are the likely hosts of the old 3). Not exact-api (kind is not deprecation/removal/migration). |
| vue | `VUE-MIG-GLOBAL-API-001` 15/1 repo: Vue 2 `Vue.component` / `new Vue` under assumed-latest Vue 3. | TP (exact-api). | No change. |
| vue | `VUE-SEC-NO-TEMPLATE-TARGET-BLANK` 8/2. | TP when `rel` is missing; near-miss if `rel="noopener"` is bound dynamically. | Stay sampled; already exact enough to report. |
| vue | `VUE-QUAL-SIMPLE-EXPRESSIONS-001` 6/4, `VUE-QUAL-SCOPED-ELEMENT-SELECTOR-001` pending 23. | Template expressions and scoped-selector style are often intentional. | Remain B/C until a 20-hit sample of the scoped-selector rule. |
| nuxt / nuxt-ui | m3: 4 reported each, no volume flag. | Low volume, exact-api migrations dominate. | Label on next run if any rule crosses 10/repo. |
| angular | `NG-QUAL-ON-PUSH` 41, `NG-MOD-INPUT-DECORATOR` 38, `NG-MOD-CONSTRUCTOR-INJECTION` 17 (gated B). | Need a 20-hit sample; constructor injection in library shims is often intentional (C-leaning). | B: sample before tightening. |
| react | `REACT-MIG-TEST-RENDERER-DEPRECATED` 33/1 (`react-router` tests). | TP for the deprecated API; volume is one test tree. | exact-api; no FP fix. |
| payload | 0 proven/measured; 37 exact-api unproven reporting directly. | No OSS payload app in the corpus. | B: add a pinned Payload CMS example app before promotion. |
| vueuse | 13 reported in m3; 25 exact-api unproven reporting directly. | Low volume. | No flagged rule. |
| spring-boot | 9 reported / 14 pending. Almost all 261 exact-api migrations never hit OSS (version-gated). | — | Keep. |
| terraform | `TF-SEC-SENSITIVE-VARIABLE` / `TF-SEC-SENSITIVE-OUTPUT` volume-flagged (B). | Likely TPs on goat/ terragoat; OSS modules may mark `sensitive = true` already (non-match). | Sample 20 on next run. |
| other config (yaml, json, docker, k8s, gha) | json/protobuf covered above. `GHA-SEC-UNPINNED-ACTION` 262/48 and `GHA-SEC-NO-PERMISSIONS` 192/53 are B (need labels, not query tweaks). `HTML-MAINT-REMOTE-SCRIPT-WITHOUT-INTEGRITY` 104/18 likewise. | — | Label, do not promote on silence. |

## A-class actions taken this pass

From `gated-triage.tsv` (A first):

1. **PHP-MIG-REFLECTION-GETCLASS** — type gate (`type.is:o:ReflectionParameter`), deterministic, extra InputOption regression.
2. **PY-SEC-RANDOM-SESSION-VALUE** — labelled FPs (retry jitter, span/trace ids) excluded with `func.lacks_re`; regressions added. Remaining labelled FPs in `labels.yaml` (test fixture, jitter, span id) should go stale on the next compute.
3. **CSS-QUAL-DUPLICATE-SELECTOR** (B by volume, fixable the same way) — skip `:root`/`:host` splits.
4. **JSON-QUAL-NON-ISO-DATE** — already tightened (year must be 19xx/20xx); documents the json drop.
5. **GO-MIG-DSA / HTTP-CLOSENOTIFIER / OS-SEEK-CONSTANTS / X-NET-CONTEXT** — queries were already exact identifiers; `applies_to: go: '*'` blocked ExactAPI. Version-gated (DSA Go 1.16, the rest Go 1.7).
6. **NG-MIG-JSONP** (and other Angular `mcall` rules) — match the last identifier of the callee (`this.http.jsonp`) with anchored `#match?`, so ExactAPI accepts them. Near-miss: `this.client.jsonp`.
7. **JAVA-MIG-DEP-FILE-TOURL-001** — `type.is:o:File`; URI.toURL is a regression. Deterministic.
8. **JAVA-MIG-DEP-THREADGROUP-001** — `type.is:o:ThreadGroup`; Process.destroy is a regression. Deterministic.
9. **JAVA-MIG-THR-001** — already had `type.is:recv:Thread`; switched to deterministic (unknown receivers stay off the list).

Still A, not done here: Java modernization such as `JAVA-MOD-MATH-CLAMP-001` (kind is not deprecation/removal/migration, so not ExactAPI), linter-linked rules with fixture TP &lt; 3, and the remaining version-gated structural queries.

## B-class (need data)

782 rules. Cheapest next step after a corpus JSON restore: 20-hit samples of the volume-anomaly security rules (`GHA-SEC-UNPINNED-ACTION`, `HTML-MAINT-REMOTE-SCRIPT-WITHOUT-INTEGRITY`, taint rules, `TF-SEC-SENSITIVE-*`). Taint stays B until Benchmark/fix-commit labelled cases exist (m8 compute recorded 0 OWASP Benchmark per-rule outcomes).

## C-class

427 rules stay behind AI (`gated.tsv` plus declared questions about purpose, production intent, secrets).

## Follow-up

1. Restore or re-run `tools/corpus run -label m8` (or `promo`) so `sample` can print file:line for the remaining B rules and for `JAVA-MOD-MATH-CLAMP-001`. `tools/corpus/cache` is empty locally.
2. After that JSON exists: `go run ./tools/trust metamorphic && go run ./tools/trust compute -label m8` (classify already re-run this pass; do not compute without corpus JSON).
3. `go run ./tools/trust gated` to refresh the per-pack table after the tsv is reclassified.
4. Grow the corpus and re-run `fixdiff` for the rest of the final promotion pass (`PLAN.md` queue item 3). Near-miss regressions for this pass's construction fixes are already in the specs.

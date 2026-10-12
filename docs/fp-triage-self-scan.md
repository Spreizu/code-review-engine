# Self-scan triage (crev on crev, 2026-10-10)

* **Before:** 143 findings (TP 82 / FP 51 / debatable 10).
* **After:**
  * 0 findings in the review list;
  * 9 `pending_ai` findings, hidden until AI confirmation: 6 PANIC-IN-INIT-ERR debatable,
    TEMPLATE-HTML-CONVERSION, LOOP-MAPKEYS, PY-SEC-HARDCODED-TMP dev-script path.

| Rule | n | Verdict | Reason / action |
|---|---|---|---|
| GO-MOD-SORT-STRINGS | 20 | TP | fixed: slices.Sort |
| PY-QUAL-OPEN-NO-ENCODING | 17 | TP | fixed: encoding="utf-8" |
| GO-SORTSLICE-FUNC | 11 | TP | fixed: slices.SortFunc + cmp/strings.Compare |
| GO-SIMP-LOOP-MAPKEYS | 8 | TP | fixed: slices.Sorted/Collect(maps.Keys) |
| GO-QUAL-ERRORF-NO-WRAP | 7 | TP | fixed: %w |
| GO-RANGEINT | 6 | 2 TP / 4 FP | FP: loop var or bound modified in body → captures + cap.lacks_re guards, 3 regressions |
| GO-STRINGSCUTPREFIX | 5 | 4 TP / 1 FP | FP: Trim of a different arg → `{cap:args}` match, regression |
| GO-MAPSLOOP / SLICESCONTAINS | 9 | TP | fixed: maps.Copy, slices.Contains |
| GO-QUAL-VET-UNREACHABLE | 5 | FP | trailing comment after return/panic treated as code → query skips comments, 2 regressions |
| GO-SEC-UNSAFE-IMPORT | 4 | FP | cgo `import "C"` bindings → filter |
| GO-QUAL-HTTP-DEFAULT-CLIENT | 3 | FP | httptest servers → file guard |
| PY-SEC-HARDCODED-TMP | 3 | 2 FP / 1 debatable | glob reads / env default → ai-confirm, precision low, ancestor guard, regressions |
| SIMP-GO-IDX-NESTED-LOOP | 2+2 | FP | inner loop iterates a value derived from the outer var → loop header split (vars vs iterable), regressions |
| GO-QUAL-PANIC-FOR-ERRORS | 6 | FP | `^package main` regex lacked (?m); Must* helpers; tests → fixed |
| GO-QUAL-PANIC-IN-INIT-ERR | 21 | 1 TP / 6 debatable / 14 FP | FP: json.Marshal of known types, NewRequest const URL, Atoi of regex group, tests → query + filters + 4 regressions; TP fixed (io.ReadAll error) |
| YAML-QUAL-LINE-LENGTH / DOCUMENT-START (+style set) | 6 | FP | style not adopted (no yamllint config) → requires_config |
| YAML-QUAL-TRUTHY | 1 | TP | fixed (quoted "off") |
| GO-QUAL-HTTP-BODY-NOT-CLOSED | 1 | FP | cache `c.Get` → requires http result assignment, regression |
| GO-SIMP-HELPER-KEYS | 1 | FP | method on a type / field-collecting loop → body_re, methods skipped, 2 regressions |
| GO-QUAL-VET-UNMARSHAL | 1 | FP | any/pointer param → func guard |
| PY-SEC-HASH-WEAK | 1 | FP | cache key → precision low (ai-confirm); fixed usedforsecurity=False |
| SIMP-HELPER-CONTAINS / PY-MOD-ITERTOOLS-BATCHED | 2 | TP | fixed |
| SIMP-GO-IDX-GLOBAL-LOCK / PONYTAIL-INCOMPLETE | 1+1 | debatable / FP | added ponytail note; multi-line ponytail notes now joined, regression |
| GO-QUAL-DEFER-IN-LOOP (test) | 1 | debatable | fixed anyway (explicit Close) |
| YAML-SEC-ALIAS-BOMB (taxonomy.yaml) | 1 | FP (pending, never listed) | generator now writes no aliases |

Main FP causes:
1. Rule did not see context: comments, test files, cgo, httptest, aliased types.
2. Opinionated style rules applied without the project adopting them.
3. Regex bugs in filters (missing (?m), a capture group taken as a constant).
4. Shape matches that ignore data flow (loop var mutated, inner iterable derived from the outer).
5. Security heuristics on non-security use (sha1 cache key, /tmp read via glob).

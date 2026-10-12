# Benchmark: crev alone vs plain AI review vs crev + AI

Date: 2026-10-10 (Europe/Tallinn). crev at commit 4dd8981 + the index panic fix found by this benchmark.
Reproduce: see `tools/bench/README.md`. Raw per-case results: `results.json`. Reviewer outputs: `answers/`.

## Read this first: the main caveat

**No AI API endpoint exists in this environment. The "AI" in setups A (ai-confirm answers),
B and C is the same Grok Bot agent that built the benchmark.** That agent:

- wrote the seeded-bug mutation operators and the seeded-case marker comment, so it knows what seeded
  cases look like. Seeded-logic results for B/C (23/23) are therefore an upper bound, not a measurement.
- reviewed B and C in the same context, B first and then C. For batches 2–10 the crev output was read only
  after the B answers were written. For batch 1 both files were opened together by mistake. C is therefore
  not independent of B.
- judged the findings that matched no label. The pool was shuffled and had setup labels and rule ids
  stripped, but the judge still recognises its own wording and crev's template messages, so this is not
  real blinding.
- cannot measure B's run-to-run consistency. Three "runs" inside one context would just be recall from
  memory, so **B consistency is reported as N/A**. crev's determinism was measured.

Treat the AI numbers as "a strong LLM reviewer with generous context" and treat the seeded results as a
smoke test. The **SZZ (real bug-introducing commits) and clean-commit rows are the least biased signal.**
For those, the fix commit stayed hidden until scoring and labels come from git history, not from the
reviewer.

## Setups

- **A: crev alone.** `crev scan --base HEAD~1` on each PR. Review list = deterministic `confirmed` +
  `ai_confirmed` with high confidence. The ai-confirm items were exported with `crev ai export`
  (skill mode), answered by the agent per the skill's rule questions, and applied with `crev ingest`.
- **B: plain AI.** The reviewer sees only the diff (±6 lines of context) and the instruction to report
  bugs, security, API misuse and design problems.
- **C: crev + AI.** C's findings are A's review list plus the AI's own findings. The AI sees the diff and
  crev's output, and is told to report only logic, intent and design problems, without repeating crev or
  reviewing for API/security patterns.

## Dataset (91 PRs)

| type | n | source | labels |
|---|---|---|---|
| szz | 24 (4 per language) | real commits in pinned repos (see below) that a later commit with fix/bug in its message corrected; `git blame` on the fix's parent | lines the fix changed, mapped back into the introducing commit |
| real-clean | 14 | real commits ≥1 year old, not fixes, every added line still unchanged at HEAD | none (any finding is a candidate FP) |
| seeded-logic | 23 | real files at HEAD + one mutation (inverted condition, &&/\|\|, off-by-one, removed guard) + a benign comment hunk | the mutated line |
| seeded-security | 12 | real files + an injected vulnerable function (SQLi, cmd injection, eval, unserialize, pickle, weak hash) | injected lines (only security findings count) |
| seeded-clean | 6 | benign comment hunk only | none |
| owasp | 12 | OWASP Benchmark Java v1.2 / Python v0.1 test files (local cache), 3 vulnerable + 3 safe each | expected results CSV |

Repos (blobless clones, HEAD sha recorded per case in `cases/cases.json`):

- Java: google/gson, apache/commons-lang
- TS/JS/Vue/Nuxt: axios, pinia, express, nuxt/ui
- Python: pallets/flask, psf/requests
- Go: gin-gonic/gin, spf13/cobra
- PHP: guzzle/guzzle, slimphp/Slim
- Kotlin: square/okio, square/kotlinpoet

Size limits:

- Introducing commits are capped at 40 changed source lines (tests excluded) to keep the review input
  bounded.
- Total diff size is 4,099 lines.
- 13–19 PRs per language. Per-language confidence intervals are wide.

**SZZ label hand-check (24/24 checked by reading the fix subject; 8 also by reading the fix diff):**

- 4 of 24 "fixes" are not bug fixes: requests "Fix linting issues", cobra "fix typos", Slim "Fix static
  analysis suppression" and Slim "fix line length".
- On the 20 verified SZZ bugs: **A 0/20, B 11/20 (0.55), C 11/20 (0.55)**.

**Scoring:**

- A finding matches a label when it is in the same file and within ±3 lines of a label line.
- For security labels (OWASP and seeded-security), only security-category findings count. For crev that
  means kind=security or a security rule id.
- Several findings near one label all count as hits for precision.
- Precision = (label hits + findings judged valid) / all findings.
- "Label-only precision" counts only label hits.
- 37 findings matched no label and went to the judging pool. 23 were judged valid and 14 invalid.

## Results

### Overall

| set | setup | cases | labelled bugs | found | recall [95% CI] | findings | precision [95% CI] | label-only precision | invalid findings / PR |
|---|---|---|---|---|---|---|---|---|---|
| all | A | 91 | 65 | 10 | 0.15 [0.09–0.26] | 16 | 0.69 [0.44–0.86] | 0.62 | 0.05 |
| excl. OWASP | A | 79 | 59 | 9 | 0.15 [0.08–0.27] | 15 | 0.67 [0.42–0.85] | 0.60 | 0.06 |
| all | B | 91 | 65 | 52 | 0.80 [0.69–0.88] | 68 | 0.93 [0.84–0.97] | 0.76 | 0.05 |
| excl. OWASP | B | 79 | 59 | 46 | 0.78 [0.66–0.87] | 62 | 0.92 [0.82–0.97] | 0.74 | 0.06 |
| all | C | 91 | 65 | 44 | 0.68 [0.56–0.78] | 66 | 0.86 [0.76–0.93] | 0.67 | 0.10 |
| excl. OWASP | C | 79 | 59 | 43 | 0.73 [0.60–0.83] | 65 | 0.86 [0.76–0.93] | 0.66 | 0.11 |

### By case type

| type | setup | cases | labelled bugs | found | recall [95% CI] | findings | precision [95% CI] | label-only precision | invalid findings / PR |
|---|---|---|---|---|---|---|---|---|---|
| szz | A | 24 | 24 | 0 | 0.00 [0.00–0.14] | 3 | 0.00 [0.00–0.56] | 0.00 | 0.12 |
| szz | B | 24 | 24 | 11 | 0.46 [0.28–0.65] | 18 | 0.89 [0.67–0.97] | 0.61 | 0.08 |
| szz | C | 24 | 24 | 11 | 0.46 [0.28–0.65] | 20 | 0.80 [0.58–0.92] | 0.55 | 0.17 |
| seeded-logic | A | 23 | 23 | 0 | 0.00 [0.00–0.14] | 0 | n/a | n/a | 0.00 |
| seeded-logic | B | 23 | 23 | 23 | 1.00 [0.86–1.00] | 23 | 1.00 [0.86–1.00] | 1.00 | 0.00 |
| seeded-logic | C | 23 | 23 | 23 | 1.00 [0.86–1.00] | 23 | 1.00 [0.86–1.00] | 1.00 | 0.00 |
| seeded-security | A | 12 | 12 | 9 | 0.75 [0.47–0.91] | 10 | 1.00 [0.72–1.00] | 0.90 | 0.00 |
| seeded-security | B | 12 | 12 | 12 | 1.00 [0.76–1.00] | 14 | 1.00 [0.78–1.00] | 0.86 | 0.00 |
| seeded-security | C | 12 | 12 | 9 | 0.75 [0.47–0.91] | 13 | 1.00 [0.77–1.00] | 0.69 | 0.00 |
| owasp-vulnerable | A | 6 | 6 | 1 | 0.17 [0.03–0.56] | 1 | 1.00 [0.21–1.00] | 1.00 | 0.00 |
| owasp-vulnerable | B | 6 | 6 | 6 | 1.00 [0.61–1.00] | 6 | 1.00 [0.61–1.00] | 1.00 | 0.00 |
| owasp-vulnerable | C | 6 | 6 | 1 | 0.17 [0.03–0.56] | 1 | 1.00 [0.21–1.00] | 1.00 | 0.00 |
| owasp-safe | A | 6 | 0 | 0 | n/a | 0 | n/a | n/a | 0.00 |
| owasp-safe | B | 6 | 0 | 0 | n/a | 0 | n/a | n/a | 0.00 |
| owasp-safe | C | 6 | 0 | 0 | n/a | 0 | n/a | n/a | 0.00 |
| real-clean | A | 14 | 0 | 0 | n/a | 2 | 0.00 [0.00–0.66] | 0.00 | 0.14 |
| real-clean | B | 14 | 0 | 0 | n/a | 7 | 0.57 [0.25–0.84] | 0.00 | 0.21 |
| real-clean | C | 14 | 0 | 0 | n/a | 9 | 0.44 [0.19–0.73] | 0.00 | 0.36 |
| seeded-clean | A | 6 | 0 | 0 | n/a | 0 | n/a | n/a | 0.00 |
| seeded-clean | B | 6 | 0 | 0 | n/a | 0 | n/a | n/a | 0.00 |
| seeded-clean | C | 6 | 0 | 0 | n/a | 0 | n/a | n/a | 0.00 |

### By language

| language | setup | cases | labelled bugs | found | recall [95% CI] | findings | precision [95% CI] | label-only precision | invalid findings / PR |
|---|---|---|---|---|---|---|---|---|---|
| java | A | 19 | 13 | 2 | 0.15 [0.04–0.42] | 5 | 0.40 [0.12–0.77] | 0.40 | 0.16 |
| java | B | 19 | 13 | 10 | 0.77 [0.50–0.92] | 18 | 0.94 [0.74–0.99] | 0.56 | 0.05 |
| java | C | 19 | 13 | 7 | 0.54 [0.29–0.77] | 18 | 0.78 [0.55–0.91] | 0.39 | 0.21 |
| ts | A | 14 | 9 | 2 | 0.22 [0.06–0.55] | 3 | 1.00 [0.44–1.00] | 0.67 | 0.00 |
| ts | B | 14 | 9 | 7 | 0.78 [0.45–0.94] | 8 | 1.00 [0.68–1.00] | 0.88 | 0.00 |
| ts | C | 14 | 9 | 7 | 0.78 [0.45–0.94] | 9 | 1.00 [0.70–1.00] | 0.78 | 0.00 |
| python | A | 19 | 13 | 1 | 0.08 [0.01–0.33] | 1 | 1.00 [0.21–1.00] | 1.00 | 0.00 |
| python | B | 19 | 13 | 11 | 0.85 [0.58–0.96] | 13 | 0.85 [0.58–0.96] | 0.85 | 0.11 |
| python | C | 19 | 13 | 7 | 0.54 [0.29–0.77] | 8 | 0.88 [0.53–0.98] | 0.88 | 0.05 |
| go | A | 13 | 10 | 2 | 0.20 [0.06–0.51] | 2 | 1.00 [0.34–1.00] | 1.00 | 0.00 |
| go | B | 13 | 10 | 8 | 0.80 [0.49–0.94] | 8 | 1.00 [0.68–1.00] | 1.00 | 0.00 |
| go | C | 13 | 10 | 8 | 0.80 [0.49–0.94] | 8 | 1.00 [0.68–1.00] | 1.00 | 0.00 |
| php | A | 13 | 10 | 2 | 0.20 [0.06–0.51] | 2 | 1.00 [0.34–1.00] | 1.00 | 0.00 |
| php | B | 13 | 10 | 7 | 0.70 [0.40–0.89] | 9 | 1.00 [0.70–1.00] | 0.78 | 0.00 |
| php | C | 13 | 10 | 7 | 0.70 [0.40–0.89] | 10 | 1.00 [0.72–1.00] | 0.70 | 0.00 |
| kotlin | A | 13 | 10 | 1 | 0.10 [0.02–0.40] | 3 | 0.33 [0.06–0.79] | 0.33 | 0.15 |
| kotlin | B | 13 | 10 | 9 | 0.90 [0.60–0.98] | 12 | 0.83 [0.55–0.95] | 0.75 | 0.15 |
| kotlin | C | 13 | 10 | 8 | 0.80 [0.49–0.94] | 13 | 0.69 [0.42–0.87] | 0.62 | 0.31 |

### OWASP Benchmark cases (a case counts as flagged when a security finding lands in the file)

| setup | lang | TPR (vulnerable flagged) | FPR (safe flagged) |
|---|---|---|---|
| A | java | 1/3 | 0/3 |
| A | python | 0/3 | 0/3 |
| B | java | 3/3 | 0/3 |
| B | python | 3/3 | 0/3 |
| C | java | 1/3 | 0/3 |
| C | python | 0/3 | 0/3 |

### Cost per PR (tokens estimated as characters / 4; AI wall time not measurable in this setup)

| setup | mean input tokens | mean output tokens | total input tokens (91 PRs) | crev wall time / PR |
|---|---|---|---|---|
| A | 285 | 25 | 25891 | 0.59 s (mean of 3 runs) + AI for ai-confirm items only |
| B | 552 | 50 | 50231 | — |
| C | 956 | 54 | 87020 | 0.59 s (mean of 3 runs) + AI |

crev run-to-run consistency: 91/91 PRs produced identical finding sets (rule, path, line, status) in 3 runs. AI items needing an answer in A: 48 over 30 PRs.


Verified SZZ only (n=20): A 0/20, B 11/20, C 11/20.

## What the numbers say

1. **On real bug-introducing commits, crev alone found nothing (0/20 verified SZZ bugs) and its few
   findings there were noise.** Those findings were 3 nested-loop simplification findings on untouched
   loop headers inside a hunk. The SZZ bugs are logic or intent errors: a wrong operator, a missing lock,
   wrong key order, a const reassignment, a removed guard. crev has no rules for these by design, and the
   plain-AI review found about half of them.
2. **crev's value is the security/API slice, at low noise.**
   - Seeded injected vulnerabilities: A found 9/12 with precision 1.00.
   - On 20 clean PRs, A reported 2 findings. Both were `KT-QUAL-DEPRECATED-NO-REPLACEWITH` on `level = HIDDEN`
     deprecations, a real FP pattern to fix.
   - That is 0.10 invalid findings per clean PR, versus B's 3 invalid out of 7 on real-clean PRs.
   - crev is deterministic (91/91 identical over 3 runs) and takes about 0.6 s per PR.
3. **OWASP: crev's review list is conservative.**
   - Java: 1/3 vulnerable flagged, 0/3 safe flagged. Python: 0/3 and 0/3.
   - The ai-confirm XSS items crev raised were correctly rejected on the safe cases (constant-folded
     branches). On the vulnerable cases crev raised no matching candidate: the path-traversal and
     JdbcTemplate SQLi sinks have no rule, and the Python XSS reflection is not modelled.
   - This is the taint-lite work queued next.
4. **C as specified, with the AI told to skip security, is worse than B.**
   - C inherits crev's security misses: seeded-security 9/12 vs 12/12, OWASP vulnerable 1/6 vs 6/6.
   - C gains nothing on logic: same SZZ recall as B.
   - C is about 1.7× B's input tokens (diff + crev output + ai-confirm payloads).
   - The useful combination is "AI full review + crev deterministic findings merged in". crev contributes
     version/API/security facts deterministically at low cost and noise, and should not narrow the AI's
     scope.
5. **Cost.**
   - B: about 550 input tokens per PR (diff + instructions). C: about 960. A's AI part: about 285, spent
     only on the 30/91 PRs with ai-confirm items.
   - Most of A's AI items were noise from the index rules on new files. `SIMP-*-IDX-TEST-MISSING` and
     `UNUSED-FILE` made up 23 of 48 items; all were answered uncertain or rejected.

## crev defects found by this benchmark (fixed or queued)

- **Fixed:** `index.computePatches` panicked (`index out of range [-1]`) on diffs that delete lines at the
  top of a file, because the hunk was `+0,0`. Fixed in internal/scope (clamped to line 1) and
  internal/index, with a regression test.
- **Queued:**
  - AI-payload scrubber redacts `password: String` in a Kotlin signature as a secret, mangling the code
    shown to the confirmer.
  - `JAVA-MOD-REC-001` sends a 27–384 line window (the whole class) to the confirmer.
  - `SIMP-*-IDX-TEST-MISSING` / `IDX-UNUSED-FILE` flood ai-confirm on route modules registered
    dynamically (`init(app)`) and on PRs whose tests live in another commit.
  - `SIMP-JAVA-IDX-NESTED-LOOP-NO-PONYTAIL` reports pre-existing loops when only a condition inside the
    hunk changed.
  - `KT-QUAL-DEPRECATED-NO-REPLACEWITH` should skip `level = HIDDEN`.
- **Coverage gaps:**
  - Kotlin `MessageDigest.getInstance("MD5")` for passwords.
  - `JdbcTemplate.batchUpdate` as a SQL sink.
  - Java/Python path traversal (`FileOutputStream`, `open`, `codecs.open` with request data).
  - Python reflected XSS via string responses.
  - `Runtime.exec` with concatenation is ai-confirm with a shell-centric question, so argument injection
    gets only medium confidence.

## Limitations

- **The self-reviewer bias above is the dominant limitation.** Rerun B/C with an external model via
  `crev ai run` / an API before using these numbers for decisions.
- **Sample sizes are small:** 13–19 PRs per language, 20 verified SZZ bugs, 12 OWASP cases. The 95% Wilson
  intervals in the tables are wide. Differences between A and B on SZZ and seeded-logic are well outside
  them; most per-language differences are not.
- **SZZ labels are noisy.** Fixes can touch lines other than the defect, and the intro commit can be a
  refactor that moved the bug. Matching uses ±3 lines.
- **Line numbers in B/C answers were counted by hand from hunk headers.** At least one was off by one;
  the ±3 tolerance absorbs this.
- **Only diffs were shown**, with no surrounding repo, tests or PR descriptions. Real reviews have more
  context, which helps both the AI and crev's index rules. Tests are excluded from the cases, which
  inflates `TEST-MISSING`.
- **AI time per PR is not measurable here.** Tokens are estimated as characters / 4.

## Rerun 2026-10-10 (crev 8d5f5c4): setups A, B, D, E and input tokens by PR size

Same 91 PRs, same B answers and judge verdicts, crev rescanned at 8d5f5c4 (taint pack, Sonar/Snyk gap rules,
Payload/Nuxt rules). 6 new ai-confirm items were answered for A (all genuine: KT-SEC-WEAK-HASH, PHP-TAINT-SQLI,
JAVA-TAINT-XSS/SQLI, PY-TAINT-PATH/XSS). Script: `tools/bench/setups.py` (results-de.json, sizes.json).

- **D** = A's review list + the full-diff AI review (B), merged (±3 lines on the same file = one finding).
- **E** = A's review list + the AI review of only the hunks crev marks risky: files with any crev finding (confirmed or
  pending), security-sensitive paths, complex hunks (≥25 added lines or ≥4 added branch points). E's AI findings are
  B's findings inside those hunks, i.e. a simulation with the same reviewer. It is an upper bound for a narrower prompt.

**Same AI-as-reviewer caveat as above:** the AI in A/B/D/E is the agent that built the benchmark. No independent model
or API was available.


| setup | cases | found/labelled | recall [95% CI] | findings | precision [95% CI] | invalid findings / clean PR | any findings / clean PR | mean input tokens / PR |
|---|---|---|---|---|---|---|---|---|
| A | 91 | 14/65 | 0.22 [0.13-0.33] | 17 | 1.00 [0.82-1.00] | 0.00 | 0.00 | 71 |
| B | 91 | 52/65 | 0.80 [0.69-0.88] | 68 | 0.93 [0.84-0.97] | 0.21 | 0.50 | 552 |
| D | 91 | 52/65 | 0.80 [0.69-0.88] | 70 | 0.93 [0.84-0.97] | 0.21 | 0.50 | 643 |
| E | 91 | 24/65 | 0.37 [0.26-0.49] | 31 | 0.97 [0.84-0.99] | 0.00 | 0.00 | 297 |

Excluding OWASP files:

| setup | cases | found/labelled | recall [95% CI] | findings | precision [95% CI] | invalid / clean PR | any / clean PR | mean input tokens / PR |
|---|---|---|---|---|---|---|---|---|
| A | 79 | 10/59 | 0.17 [0.09-0.28] | 12 | 1.00 [0.76-1.00] | 0.00 | 0.00 | 43 |
| B | 79 | 46/59 | 0.78 [0.66-0.87] | 62 | 0.92 [0.82-0.97] | 0.21 | 0.50 | 514 |
| D | 79 | 46/59 | 0.78 [0.66-0.87] | 63 | 0.92 [0.83-0.97] | 0.21 | 0.50 | 572 |
| E | 79 | 18/59 | 0.31 [0.20-0.43] | 24 | 0.96 [0.80-0.99] | 0.00 | 0.00 | 191 |

By PR size bucket (changed lines; this dataset is capped at 40 source lines, so only small/medium occur):

| bucket | setup | cases | found/labelled | recall | findings | precision | invalid / clean PR | any / clean PR | mean input tokens |
|---|---|---|---|---|---|---|---|---|---|
| small | A | 79 | 10/59 | 0.17 [0.09-0.28] | 12 | 1.00 [0.76-1.00] | 0.00 | 0.00 | 43 |
| small | B | 79 | 46/59 | 0.78 [0.66-0.87] | 62 | 0.92 [0.82-0.97] | 0.21 | 0.50 | 514 |
| small | D | 79 | 46/59 | 0.78 [0.66-0.87] | 63 | 0.92 [0.83-0.97] | 0.21 | 0.50 | 572 |
| small | E | 79 | 18/59 | 0.31 [0.20-0.43] | 24 | 0.96 [0.80-0.99] | 0.00 | 0.00 | 191 |
| medium | A | 12 | 4/6 | 0.67 [0.30-0.90] | 5 | 1.00 [0.57-1.00] | nan | nan | 257 |
| medium | B | 12 | 6/6 | 1.00 [0.61-1.00] | 6 | 1.00 [0.61-1.00] | nan | nan | 802 |
| medium | D | 12 | 6/6 | 1.00 [0.61-1.00] | 7 | 1.00 [0.65-1.00] | nan | nan | 1112 |
| medium | E | 12 | 6/6 | 1.00 [0.61-1.00] | 7 | 1.00 [0.65-1.00] | nan | nan | 998 |

E selected 62 of 169 hunks; 50/91 PRs had no risky hunk (no AI review beyond ai-confirm).

By case type (found/labelled, findings, invalid):

| type | A | B | D | E |
|---|---|---|---|---|
| szz (24) | 0/24, 0, 0 | 11/24, 18, 2 | 11/24, 18, 2 | 4/24, 7, 1 |
| seeded-logic (23) | 0/23, 0, 0 | 23/23, 23, 0 | 23/23, 23, 0 | 2/23, 2, 0 |
| seeded-security (12) | 10/12, 12, 0 | 12/12, 14, 0 | 12/12, 15, 0 | 12/12, 15, 0 |
| owasp-vulnerable (6) | 4/6, 5, 0 | 6/6, 6, 0 | 6/6, 7, 0 | 6/6, 7, 0 |
| real-clean (14) | 0 findings | 7 findings, 3 invalid | 7, 3 invalid | 0 |

"Clean PR" in the tables means the 14 real-clean commits. Compared with the first run, A went from recall 0.15 →
0.22 and precision 0.69 → 1.00. The two clean-PR false positives (KT-QUAL-DEPRECATED-NO-REPLACEWITH, nested-loop
simplification) are gone.

### Input tokens per PR by size (116 real commits from gin, flask, axios, guzzle, kotlinpoet, gson)

Lock files, dist/vendor, snapshots and binary assets are excluded for every setup. Tokens = characters / 4.
B = instructions + diff (-U6). D = B + crev findings + ai-confirm payload. E = risky hunks + crev findings +
ai-confirm payload. A = ai-confirm payload only (crev itself is free).

| bucket | PRs | median changed lines | A tokens (median / p90) | B tokens (median / p90) | D tokens (median / p90) | E tokens (median / p90) | E share of hunks |
|---|---|---|---|---|---|---|---|
| small | 30 | 6 | 0 / 568 | 371 / 1,590 | 382 / 1,654 | 0 / 773 | 12% |
| medium | 30 | 105 | 0 / 737 | 2,177 / 5,850 | 2,177 / 8,047 | 1,050 / 2,686 | 25% |
| large | 30 | 401 | 0 / 1,105 | 6,097 / 17,995 | 7,421 / 18,094 | 3,448 / 9,403 | 19% |
| huge | 26 | 2,607 | 532 / 8,136 | 36,874 / 403,004 | 40,192 / 408,940 | 25,349 / 102,921 | 36% |

B input ~= 19.4 tokens per changed line (median over 116 commits, -U6 context). 32k tokens ~= 1,649 changed lines. 100k tokens ~= 5,152 changed lines. 200k tokens ~= 10,304 changed lines.

Huge bucket (26 PRs): B is over 32k tokens for 15, over 100k for 7 and over 200k for 4. E is over 32k for 8 and over
100k for 3. Small, medium and large PRs never needed more than 32k (one large PR reached 18k at p90).

**Batching estimate.** Full review (B/D) fits in one prompt up to about 1.6k changed lines at a 32k working budget,
or about 5k changed lines at 100k. Above roughly 1.5k changed lines, plan per-file or per-directory batches; above
roughly 10k lines, even a 200k-context model needs batches. E roughly halves the input for medium and large PRs and
cuts it by about a third for huge ones.

### Takeaways
- crev alone (A) is precise (1.00, 0 FP per clean PR) but finds mostly security/API issues (22% recall overall, 0% on
  logic bugs).
- D keeps B's recall (0.80) at +16% tokens. crev adds 2 findings B missed. It does not remove B's 0.21 invalid
  findings per clean PR.
- E reaches 0 invalid per clean PR at about half of B's tokens, but recall drops to 0.37. Logic bugs in small,
  "boring" hunks (seeded-logic 2/23, SZZ 4/24) are never selected. Risk targeting fits as a cheap security/API pass,
  not as a replacement for a full review.

## Rerun 2026-10-10 (crev b32157d): four-way A / B / D / E after the maintainability, ASVS and HTML batches

Same 91 PRs, B answers and earlier judge verdicts reused; crev rescanned (`build.py scan`), D/E recomputed with
`setups.py score`. Rule renames changed finding fingerprints, so 35 ai-confirm items were answered again for A
(seeded and OWASP security items confirmed; library-export, record and for-in items rejected; accurate maintainability
items confirmed) and 10 new non-label findings were judged (all accurate maintainability findings on OWASP files:
unused private parameter, immediately returned variable, System.out logging, commented-out code, unreachable return,
default-charset getBytes). **Same caveat: the AI in A/B/D/E and the judge is the agent that built the benchmark.**

| setup | cases | found/labelled | recall [95% CI] | findings | precision [95% CI] | invalid / clean PR | any / clean PR | mean input tokens / PR |
|---|---|---|---|---|---|---|---|---|
| A | 91 | 17/65 | 0.26 [0.17-0.38] | 31 | 1.00 [0.89-1.00] | 0.00 | 0.00 | 194 |
| B | 91 | 52/65 | 0.80 [0.69-0.88] | 68 | 0.93 [0.84-0.97] | 0.21 | 0.50 | 552 |
| D | 91 | 53/65 | 0.82 [0.70-0.89] | 82 | 0.94 [0.87-0.97] | 0.21 | 0.50 | 770 |
| E | 91 | 26/65 | 0.40 [0.29-0.52] | 45 | 0.96 [0.85-0.99] | 0.00 | 0.00 | 431 |

By case type (found/labelled, findings, invalid):

| type | A | B | D | E |
|---|---|---|---|---|
| szz (24) | 1/24, 2, 0 | 11/24, 18, 2 | 12/24, 20, 2 | 6/24, 11, 2 |
| seeded-logic (23) | 0/23, 0, 0 | 23/23, 23, 0 | 23/23, 23, 0 | 2/23, 2, 0 |
| seeded-security (12) | 11/12, 13, 0 | 12/12, 14, 0 | 12/12, 15, 0 | 12/12, 15, 0 |
| owasp-vulnerable (6) | 5/6, 14, 0 | 6/6, 6, 0 | 6/6, 15, 0 | 6/6, 15, 0 |
| owasp-safe (6) | 0 security findings (2 maintainability, valid) | 0 | 2, 0 invalid | 2, 0 invalid |
| real-clean (14) | 0 findings | 7, 3 invalid | 7, 3 invalid | 0 |

By size: the dataset is capped at 40 source lines (small 79 PRs, medium 12). Small: A 0.20 / B 0.78 / D 0.80 / E 0.34
recall at 135 / 514 / 666 / 293 mean input tokens. Medium: A 0.83 / B, D, E 1.00 at 582 / 802 / 1,455 / 1,341.
Token cost on larger real PRs is unchanged from the table above (crev-independent except the small ai-confirm payload).

Takeaways: A's recall rose 0.22 -> 0.26 at precision 1.00 and 0 findings on clean PRs; D adds 1 label and 14 valid
findings over B for +40% tokens; E keeps 0 invalid per clean PR at ~0.8x B's tokens but misses logic bugs in
unselected hunks.

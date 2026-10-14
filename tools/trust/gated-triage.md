# Gated-rule triage (HEAD 5a9ca2a)

Analysis only: no rule, engine or label changes. Scope: every rule that does not report directly
(effective mode ai-confirm after trust policy, or quarantined/shadow): **1988 rules**. Generated from `gated-triage.tsv` by `go run ./tools/trust gated`.

Buckets:
- **A fixable-by-construction**: tighten query/filters for labelled FPs, type/framework/index gate, exact-api conversion or version gating, generated cases from official docs/linter test suites.
- **B needs-data**: logic plausibly precise; missing evidence (no corpus hits, unreviewed volume anomaly, unlabelled hits, taint without labelled cases).
- **C inherently-semantic**: intent/context judgement (author-declared AI questions about purpose, production intent, secrets, naming heuristics, `gated.tsv` entries); stays AI.

## Counts

| bucket | rules |
|---|---|
| A | 779 |
| B | 782 |
| C | 427 |

## Per pack

| pack | A | B | C | total |
|---|---|---|---|---|
| android | 2 | 3 | 6 | 11 |
| angular | 15 | 6 | 6 | 27 |
| composer | 4 | 15 | 1 | 20 |
| css | 4 | 9 | 5 | 18 |
| docker | 4 | 31 | 6 | 41 |
| github-actions | 0 | 7 | 1 | 8 |
| gitlab-ci | 0 | 4 | 0 | 4 |
| go | 45 | 37 | 32 | 114 |
| gradle | 5 | 17 | 4 | 26 |
| graphql | 5 | 13 | 7 | 25 |
| html | 13 | 26 | 4 | 43 |
| java | 170 | 76 | 77 | 323 |
| javascript | 101 | 70 | 56 | 227 |
| json | 7 | 23 | 2 | 32 |
| kotlin | 36 | 46 | 35 | 117 |
| kubernetes | 1 | 8 | 7 | 16 |
| maven | 8 | 17 | 1 | 26 |
| nuxt | 8 | 19 | 10 | 37 |
| nuxt-ui | 27 | 2 | 6 | 35 |
| package-json | 2 | 14 | 2 | 18 |
| payload | 16 | 12 | 11 | 39 |
| php | 50 | 41 | 34 | 125 |
| protobuf | 13 | 12 | 7 | 32 |
| python | 115 | 74 | 52 | 241 |
| react | 4 | 14 | 7 | 25 |
| spring-boot | 32 | 7 | 14 | 53 |
| terraform | 11 | 40 | 11 | 62 |
| typescript | 34 | 15 | 4 | 53 |
| vue | 35 | 58 | 12 | 105 |
| vueuse | 2 | 2 | 3 | 7 |
| yaml | 3 | 25 | 3 | 31 |
| ytt | 7 | 39 | 1 | 47 |

## Top 30 A (fixable-by-construction): security/correctness first, then corpus hits

| rule | pack | category | hits/repos | reason |
|---|---|---|---|---|
| ANDROID-SEC-DEBUGGABLE | android | security | 0/0 | exact config/manifest key match, no corpus hits |
| ANDROID-SEC-NSC-USER-CA | android | security | 0/0 | exact config/manifest key match, no corpus hits |
| GO-MIG-DSA | go | security | 0/0 | version/migration rule, no corpus hits; version-gated, not exact-api |
| GO-SEC-ATOI-NARROWING | go | security | 0/0 | AI question is decidable structurally (type/binding/config): Is the converted value derive |
| GO-SEC-TLS-INSECURE-SKIP-VERIFY | go | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref gosec:G402) |
| GRAPHQL-QUAL-INLINE-DYNAMIC-ARGUMENT | graphql | security | 0/0 | AI question is decidable structurally (type/binding/config): Is this argument value dynami |
| JAVA-CERT-FIO03-TEMP-FILE-NOT-REMOVED | java | security | 0/0 | AI question is decidable structurally (type/binding/config): Is the temporary file left be |
| JAVA-SEC-COOKIE-HTTPONLY-001 | java | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:java:S3330,semgrep:java.lang.secu |
| JAVA-SEC-ECB-001 | java | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:java:S5542,semgrep:java.lang.secu |
| JAVA-SEC-HOSTNAME-VERIFIER-001 | java | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:java:S5527,semgrep:java.lang.secu |
| JAVA-SEC-HTTP-URL | java | security | 0/0 | AI question is decidable structurally (type/binding/config): Does this URL carry real traf |
| JAVA-SEC-LDAP-ANON-001 | java | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:java:S4433) |
| JAVA-SEC-POSIX-WORLD-WRITABLE-001 | java | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:java:S2612) |
| JAVA-SEC-SESSION-FIXATION-NONE-001 | java | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:java:S5876) |
| JAVA-SEC-SPRING-SECURITY-DEBUG-001 | java | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:java:S4507) |
| JAVA-SEC-WEAK-TLS-001 | java | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:java:S4423,semgrep:java.lang.secu |
| JS-SEC-CORS-REFLECT-ANY-001 | javascript | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:javascript:S5122) |
| JS-SEC-HELMET-HEADER-OFF | javascript | security | 0/0 | AI question is decidable structurally (type/binding/config): Is the header disabled withou |
| JS-SEC-NO-NEW-FUNC | javascript | security | 0/0 | labelled precision 0.57 < 0.90 (TP 4 FP 3); known FPs are concrete |
| JS-SEC-OAUTH-NO-STATE-PKCE | javascript | security | 0/0 | AI question is decidable structurally (type/binding/config): Is this URL sent as-is (state |
| JS-TAINT-XSS | javascript | security | 0/0 | labelled precision 0.14 < 0.90 (TP 1 FP 6); known FPs are concrete |
| KT-SEC-HTTP-URL | kotlin | security | 0/0 | AI question is decidable structurally (type/binding/config): Does this URL carry real traf |
| KUBE-SEC-IMAGE-UNTAGGED | kubernetes | security | 0/0 | AI question is decidable structurally (type/binding/config): Is this a real registry image |
| NG-MIG-JSONP | angular | security | 0/0 | version/migration rule, no corpus hits; version-gated, not exact-api |
| PHP-SEC-SETCOOKIE-NO-FLAGS | php | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:php:S2092,sonar:php:S3330) |
| PHP-TAINT-TRUST | php | security | 0/0 | labelled precision 0.80 < 0.90 (TP 4 FP 1); known FPs are concrete |
| PY-LLM-TRUST-REMOTE-CODE | python | security | 0/0 | AI question is decidable structurally (type/binding/config): Is the repository id not a fi |
| PY-SEC-ASSERT-FOR-SECURITY | python | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref bandit:B101,ruff:S101) |
| PY-SEC-CHMOD-WORLD-WRITABLE | python | security | 0/0 | syntactic/linter-linked rule, no corpus hits (xref sonar:python:S2612) |
| PY-SEC-OAUTH-NO-STATE-PKCE | python | security | 0/0 | AI question is decidable structurally (type/binding/config): Is this URL sent as-is (state |

## Top 30 B (needs-data): security/correctness first, then corpus hits

| rule | pack | category | hits/repos | reason |
|---|---|---|---|---|
| GHA-SEC-UNPINNED-ACTION | github-actions | security | 262/48 | unreviewed volume anomaly 262 hits/48 repos ['oss-total>=15', 'repo>=10'] |
| JAVA-SEC-RANDOM-SECURITY-CONTEXT | java | security | 203/2 | 203 corpus hits/2 repos, below thresholds, unlabelled |
| GHA-SEC-NO-PERMISSIONS | github-actions | security | 192/53 | unreviewed volume anomaly 192 hits/53 repos ['oss-total>=15', 'repo>=10'] |
| JAVA-SEC-WEAK-HASH-SECURITY-CONTEXT | java | security | 114/2 | 114 corpus hits/2 repos, below thresholds, unlabelled |
| HTML-MAINT-REMOTE-SCRIPT-WITHOUT-INTEGRITY | html | security | 104/18 | unreviewed volume anomaly 104 hits/18 repos ['oss-total>=15', 'repo>=10'] |
| DOCKER-SEC-COMPOSE-ENV-SECRET | docker | security | 41/7 | unreviewed volume anomaly 41 hits/7 repos ['oss-total>=15', 'repo>=10'] |
| PY-SEC-HASH-WEAK-SECURITY-CONTEXT | python | security | 41/4 | 41 corpus hits/4 repos, below thresholds, unlabelled |
| TF-SEC-SENSITIVE-VARIABLE | terraform | security | 32/4 | unreviewed volume anomaly 32 hits/4 repos ['oss-total>=15', 'repo>=10'] |
| KUBE-SEC-ENV-SECRET-LITERAL | kubernetes | security | 25/2 | unreviewed volume anomaly 25 hits/2 repos ['oss-total>=15', 'repo>=10'] |
| TF-SEC-SENSITIVE-OUTPUT | terraform | security | 24/5 | unreviewed volume anomaly 24 hits/5 repos ['oss-total>=15', 'repo>=10'] |
| ANDROID-SEC-CLEARTEXT-URL | android | security | 22/2 | unreviewed volume anomaly 22 hits/2 repos ['oss-total>=15', 'repo>=10'] |
| DOCKER-SEC-COPY-SECRET-FILE | docker | security | 11/2 | unreviewed volume anomaly 11 hits/2 repos ['repo>=10'] |
| JS-SEC-SESSION-NO-MAXAGE | javascript | security | 10/2 | 10 corpus hits/2 repos, below thresholds, unlabelled |
| JS-SEC-NODE-URL-PARSE-001 | javascript | security | 3/1 | 3 corpus hits/1 repos, below thresholds, unlabelled |
| KT-SEC-TRUST-ALL | kotlin | security | 2/1 | 2 corpus hits/1 repos, below thresholds, unlabelled |
| JAVA-SEC-STATIC-DATEFORMAT | java | security | 1/1 | 1 corpus hits/1 repos, below thresholds, unlabelled |
| ANDROID-SEC-FILE-WORLD-PERMISSION | android | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| ANDROID-SEC-WORLD-ACCESSIBLE-MODE | android | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| COMPOSER-SEC-ALLOW-PLUGINS-WILDCARD | composer | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| COMPOSER-SEC-AUTH-IN-COMPOSER-JSON | composer | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| COMPOSER-SEC-BLOCK-INSECURE-OFF | composer | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| COMPOSER-SEC-DISABLE-TLS | composer | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| COMPOSER-SEC-REPO-HTTP | composer | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| COMPOSER-SEC-SCRIPT-REMOTE-EXEC | composer | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| COMPOSER-SEC-SECURE-HTTP-OFF | composer | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| DOCKER-SEC-ADD-REMOTE-NO-CHECKSUM | docker | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| DOCKER-SEC-COMPOSE-BUILD-ARGS-SECRET | docker | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| DOCKER-SEC-COMPOSE-CGROUP-HOST | docker | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| DOCKER-SEC-COMPOSE-IPC-HOST | docker | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |
| DOCKER-SEC-COMPOSE-LOGGING-DRIVER-NONE | docker | security | 0/0 | deterministic query, own examples only (no corpus hits) ; security |

## User policy: linter suppressions

Linter suppression comments in code (`// eslint-disable-next-line`, `# noqa`, `//nolint`, `@SuppressWarnings`, `@phpstan-ignore` etc.) indicate a real underlying problem that someone chose to accept, not a rule mismatch.
- **Measurement:** a crev hit at a suppressed location counts as a **true positive** (corpus labelling, precision, promotion).
- **Reporting:** crev still honors the suppression and does not report the finding when the suppression for the matching rule is set.

## Notes

- Classification is heuristic over metadata; borderline rules lean to A when the AI question is structurally decidable (receiver type, binding, config elsewhere) and to C when it asks about purpose/intent.
- B is dominated by deterministic rules with own examples only (no corpus hits) and below-threshold unlabelled hits; the cheapest wins are the ~180 'awaiting sampled hit review' rules and the volume anomalies (same 20-hit sample procedure already used for Java/Python/Go/JS/Kotlin/PHP).
- A includes linter-linked rules with no hits: importing the upstream linter's own test suite (as done for the 561 labelled rules) is the generated-case route.
- Taint rules are B: the engine path is precise; they need labelled source/sanitizer cases (Benchmark, CVE fix pairs).
- Migration/deprecation rules not yet exact-api are A: convert to anchored predicates + applies_to, or generate cases from the official migration guide.
- Classifier script was a throwaway (not committed); this file is regenerated from the tsv. Sampled hit reviews: `tools/trust/sampled-review.md`.

# tools/corpus: false-positive harness

This directory is not part of the crev binary. The clones live in `cache/` (gitignored). Raw
reports go to `results/<label>/raw/` (gitignored). Compact per-repo hit lists and `report.md`
under `results/<label>/` may be committed as evidence.

## Inputs (`corpus.yaml`, every entry pinned to a commit)

| kind | what | used for |
|---|---|---|
| `oss` | popular, well-reviewed OSS projects per language | FP volume: a rule that fires often on mature code is suspect |
| `bench` | OWASP Benchmark Java/Python, Juice Shop, NodeGoat, WebGoat, DVWA, PyGoat, DVPWA, GoVWA, TerraGoat, Kubernetes Goat, DVGA | recall on labelled/known vulnerabilities; FP rate on the "safe" cases |
| `fixtures` | linter test suites (ESLint, typescript-eslint, eslint-plugin-vue, react-hooks, graphql-eslint, ruff, go/analysis, staticcheck, hadolint, yamllint) | per-rule precision/recall: valid cases are must-not-match, invalid cases must-match |

Licenses are recorded per entry. Everything is read locally to measure crev. No fixture, test
code or rule text is copied into packs, regressions or commits. A regression example taken from
a corpus hit is always rewritten as our own minimal snippet.

## Workflow

```sh
go run ./tools/corpus fetch                                # shallow, pinned (sparse where set)
go build -o /tmp/crev-before <old ref> ; go build -o /tmp/crev-after ./cmd/crev
go run ./tools/corpus run -label before -crev /tmp/crev-before
go run ./tools/corpus run -label after  -crev /tmp/crev-after
go run ./tools/corpus summarize -label after              # results/after/report.md, flags
go run ./tools/corpus diff before after                   # per-pack / per-rule deltas
go run ./tools/corpus sample -label after -rule GO-XYZ -n 12   # triage set, round-robin over repos
go run ./tools/corpus suppressions -label after              # inline disables ∩ crev hits → labelled TPs
go run ./tools/corpus autofix -label after -crev BIN         # lint autofix-commit parent vs fix
go run ./tools/corpus agree -label after                     # oxlint/ruff/hadolint/yamllint vs crev
```

Scans run with `--ai off`, so the counts are:

* **reported**: `confirmed`, i.e. what reaches the review list with no AI involved;
* **pending**: ai-confirm candidates. These are shown only after high-confidence AI confirmation;
* **shadow**: quarantined rules (always kept, `hidden_reason: shadow`).

## Triage loop

1. **Flag.** `summarize` flags rules with ≥15 reported hits overall, ≥10 in one repo, or hits in
   ≥25% of a repo's files.
2. **Sample.** Take ~10 hits per flagged rule with `sample`, and label each one TP / FP / debatable.
3. **Act on FPs:**
   * fix the root cause in the spec: a tighter query, capture/func/ancestor filters,
     `requires_config`, version gating, or test/generated exclusions;
   * add a minimal own-words `fp=` regression (must-not-match), which rulecheck keeps forever;
   * bump `rule_version`.
4. **Choose the outcome** when the rule cannot be made precise:
   * set `precision: low` and move it to ai-confirm; or
   * quarantine it in `rules/data/governance.yaml` (`status: shadow` + `status_reason`).
5. **Validate new or untrusted rules.** They start in shadow and are promoted once a corpus run
   shows no unexplained hits.
6. **Re-run and commit.** Re-run `run` / `diff` and commit the spec, pack and governance changes
   together.

## Extra labelled evidence

Inline linter suppressions (`eslint-disable-next-line`, `# noqa`, `//nolint`, `@SuppressWarnings`,
`@phpstan-ignore`, …) mark a real issue the author chose to keep. `suppressions` joins those comments
in the clones with crev hits from `run`; a matching location is a true positive for trust compute.
Reporting still honours the comment.

`autofix` mines lint auto-fix commits (message matches `eslint --fix`, `ruff --fix`, `gofmt`,
`lint:fix`, …) from clone history and GitHub search, then scans the parent vs the fix like `fixdiff`.
`agree` runs oxlint, ruff, hadolint and yamllint when they are on PATH and counts same-line
agreement (mapped through `xref` `tool:id`) as true positives. crev-only and linter-only spots are
listed, not scored as FP/FN.

#!/usr/bin/env python3
"""Write tools/gap/sonar-infeasible.md: every Sonar way (comprehensive) key crev does not cover,
grouped by the reason it is not (yet) a crev rule.

The Sonar catalog is a checklist only. The classification below reads rule metadata from the
local cache (tools/gap/cache, gitignored) but the output contains rule keys and our own reason
text only: no Sonar titles, descriptions or examples are written.

    uv run -q --with pyyaml python3 tools/gap/sonar_infeasible.py          # write the file
    uv run -q --with pyyaml python3 tools/gap/sonar_infeasible.py --show   # local triage (prints titles, writes nothing)
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sonar  # noqa: E402

# (category id, own-words reason, predicate over (lang, key, type, lowercase name)).
# The first matching category wins; order goes from "cannot" to "could, later".
CATS = [
    # CSS has a grammar and a css pack since 2026-10-10: no language is parser-less any more
    ("no-parser", "No parser in the binary for this file type (none at present).",
     lambda l, k, t, n: False),
    ("py2", "Python 2 only syntax; current grammars and interpreters reject it before review.",
     lambda l, k, t, n: k in ("BackticksUsage", "ExecStatementUsage", "PrintStatementUsage", "InequalityUsage", "S1717")),
    ("compiler", "The compiler or interpreter already rejects this code (syntax/compile error), so it never reaches review.",
     lambda l, k, t, n: (l, k) in {("py", "S1716"), ("py", "S2711"), ("py", "S5549"), ("js", "S1536"), ("ts", "S1536")}),
    ("architecture", "Needs a project-level architecture model (declared layers and allowed dependencies), not a per-file rule.",
     lambda l, k, t, n: re.search(r"architect|tangle|relationships? should", n)),
    ("regex-engine", "Needs a regular-expression parser and engine semantics (backtracking, groups, flags) per language.",
     lambda l, k, t, n: re.search(r"regex|regular expression|back reference|lookahead|possessive|grapheme|character class|\bquantifier", n)),
    ("symbolic", "Needs path-sensitive data-flow / symbolic execution (nullness, value ranges, reachability, resource and stream state).",
     lambda l, k, t, n: l.startswith("javabugs") or k.startswith("javabugs") or re.search(
         r"null|undefined|denominator|infinite|reachable|always (true|false)|should not be accessed|unused|dead store|"
         r"conditionally executed|gratuitous|identical sub-?expressions|consumed|reused|modified while|out ?of ?bounds|"
         r"initiali[sz]ed before|defined before|assigned before|be closed|resources should|leak|tainted", n)),
    ("types", "Needs type resolution across files (receiver/argument types, class hierarchy, overload resolution).",
     lambda l, k, t, n: re.search(
         r"type|incompatible|dissimilar|primitive|boxed|wrapper|inherit|subclass|superclass|override|overrid|interface|"
         r"implement|serializ|generic|cast|instanceof|equals|hashcode|comparable|comparator|collection|iterable|"
         r"callable|awaitable|promise|thenable|void function|return value of|arguments? (passed|count)|number of arguments|"
         r"should be (an|a) |supporting them|non-callable|item operations|operators should be used on|value-based|"
         r"\bclass(es)? (should|must)|abstract|static context|constructor", n)),
    ("framework", "Needs framework runtime or configuration semantics (DI container, ORM, routing, cloud SDK, ML/data libraries).",
     lambda l, k, t, n: re.search(
         r"spring|bean|@|django|flask|fastapi|pydantic|aws|lambda|s3|dynamo|cloudwatch|boto|azure|gcp|vue|react|angular|"
         r"jsx|hibernate|jpa|entity|quarkus|panache|tensorflow|keras|torch|pytorch|scikit|sklearn|pandas|numpy|jax|"
         r"einops|servlet|struts|jakarta|android|compose|coroutine|flow|kotlinx|laravel|symfony|wordpress|drupal|"
         r"express|nestjs|next\.js|node|dom|aria|html|tabindex|label|heading|table|svelte|testing library|jquery|lodash|"
         r"underscore|redux|graphql|mongo|sql|jdbc|database|transaction|http|cookie|session|cors|csrf|header", n)),
    ("tests", "Needs test-framework semantics (runner discovery, assertion libraries, mocking APIs).",
     lambda l, k, t, n: re.search(r"\btests?\b|assert|mock|junit|testng|pytest|unittest|jest|mocha|jasmine|cypress|playwright|phpunit|fixture|spec\b", n)),
    ("security", "Security rule: tracked in the security backlog (taint/config packs and the OWASP/ASVS maps), not as a code-smell rule.",
     lambda l, k, t, n: t in ("VULNERABILITY", "SECURITY_HOTSPOT")),
    ("style", "Formatting, naming or layout convention best left to the project's formatter/linter configuration (crev reads those configs instead of duplicating them).",
     lambda l, k, t, n: re.search(
         r"naming convention|should comply|name|indent|brace|curly|whitespace|semicolon|line|tab|trailing|file|header|"
         r"copyright|length|parenthes|quote|comma|newline|format|order|declar|modifier|keyword|literal|suffix|uppercase|"
         r"lowercase|camel|\bstyle\b|comment|javadoc|docstring|todo|deprecated|nested|too many|too long|complex|"
         r"package|import|wildcard|star|alias|shorthand|syntax|prefer|instead|should be used|redundant|useless|"
         r"unnecessary|simplif|merged|collapsible|explicit", n)),
    ("backlog", "Feasible with tree-sitter but not implemented yet (backlog).", lambda l, k, t, n: True),
]


def gaps():
    crev = sonar.crev_rules()
    by_key = {k for r in crev for k in r["sonar"]}
    out = {}
    for lang, crev_langs in sonar.LANGS.items():
        p = os.path.join(sonar.CACHE, f"sonar-{lang}.json")
        if not os.path.exists(p):
            continue
        rules = json.load(open(p, encoding="utf-8"))
        pool = [r for r in crev if r["lang"] in crev_langs]
        cwes = {sonar.FAMILY.get(c, c) for r in pool for c in r["cwe"]}
        prof = sonar.PROFILES[-1]
        rs = [r for r in rules if prof in r["profiles"]]
        g = [r for r in rs if r["key"] not in by_key and not any(sonar.FAMILY.get(w, w) in cwes for w in r["cwe"])]
        out[lang] = (len(rs), g)
    return out


def classify(lang, r):
    repo, key = r["key"].split(":", 1)
    n = (r.get("name") or "").lower()
    for cid, _, pred in CATS:
        if pred(lang if not repo.startswith("javabugs") else "javabugs", key, r.get("type"), n):
            return cid
    return "backlog"


def main():
    show = "--show" in sys.argv
    data = gaps()
    reasons = {c: why for c, why, _ in CATS}
    lines = ["# Sonar way keys not covered by crev, by reason", "",
             "Generated by `uv run -q --with pyyaml python3 tools/gap/sonar_infeasible.py` from the local Sonar catalog cache",
             "(Sonar way comprehensive profile). The catalog is a checklist only: this file lists rule keys and our own reason",
             "text, never Sonar titles or descriptions. A key leaves this file when a crev rule cites it in `xref`.", "",
             "## Reasons", ""]
    lines += [f"- **{c}**: {why}" for c, why, _ in CATS]
    lines += ["", "## Summary (uncovered keys per language and reason)", "",
              "| language | profile rules | uncovered | " + " | ".join(c for c, _, _ in CATS) + " |",
              "|---|---|---|" + "---|" * len(CATS)]
    detail = []
    tot = {c: 0 for c, _, _ in CATS}
    for lang, (n, g) in data.items():
        groups = {}
        for r in g:
            c = classify(lang, r)
            groups.setdefault(c, []).append(r)
            tot[c] += 1
        lines.append(f"| {lang} | {n} | {len(g)} | " + " | ".join(str(len(groups.get(c, []))) for c, _, _ in CATS) + " |")
        if not g:
            continue
        detail += ["", f"### {lang}", ""]
        for c, _, _ in CATS:
            if c in groups:
                keys = sorted(r["key"] for r in groups[c])
                detail.append(f"- **{c}** ({len(keys)}): " + ", ".join(keys))
                if show:
                    for r in sorted(groups[c], key=lambda r: r["key"]):
                        print(f"{lang:9} {c:12} {r['key']:28} {r.get('type'):16} {r.get('name')}")
    lines.append("| **total** | | **%d** | " % sum(tot.values()) + " | ".join(f"**{tot[c]}**" for c, _, _ in CATS) + " |")
    lines += ["", "## Keys", ""] + detail
    if show:
        return
    with open(os.path.join(sonar.ROOT, "tools/gap/sonar-infeasible.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[: 20 + len(data)]))


if __name__ == "__main__":
    main()

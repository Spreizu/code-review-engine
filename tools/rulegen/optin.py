#!/usr/bin/env python3
"""Generate rules/data/optin.yaml: opinionated rules that only run when the project enables them.

A crev rule mirroring a linter rule that the linter itself leaves out of its recommended/default
set is a style or preference choice, not a defect: reporting it in a repo that never adopted the
rule produces findings nobody agreed to (corpus 2026-10-10: prefer-arrow-callback, no-var, curly,
no-console, require-unicode-regexp... made up most of all hits on mature OSS repos). Such rules
are opt-in: they report only where the project's own linter config turns the equivalent rule on
(projcfg directive, not "off"), or when a .crev/rules override sets opt_in: false.

Opt-in when ALL hold:
  * the rule has an equivalent in eslint / typescript-eslint / eslint-plugin-vue / ruff / yamllint;
  * none of its equivalents is in that linter's recommended/default set:
      eslint: meta.recommended; eslint-plugin-vue: an *essential category;
      typescript-eslint: the flat `recommended` config (data/tseslint-recommended.json);
      ruff: the default selection E4, E7, E9, F; yamllint: enabled in its default config;
  * crev classifies it as preference, not risk: kind is not security, and either the linter
    calls it a suggestion/layout rule (eslint, vue meta.type) or the crev category is
    style / maintainability / modernization.
"""
import glob, json, os, re
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "tools/rulegen/data")
OPINION = {"style", "maintainability", "modernization"}
# yamllint rules disabled in its `default` configuration (yamllint/conf/default.yaml).
YAMLLINT_OFF = {"document-end", "empty-values", "float-values", "key-ordering", "octal-values", "quoted-strings"}
# Judged by corpus triage rather than the criteria above (reason recorded in optin.yaml).
FORCE = {
    "YAML-QUAL-EMPTY-VALUE": "corpus 2026-10-10: implicit null is the idiom in GitHub Actions `on: push:`, compose top-level "
        "`volumes: db:` and compose env passthrough `VAR:` (82 hits, sampled all intentional); yamllint disables empty-values by default",
    "TS-QUAL-NO-UNSAFE-TYPE-ASSERTION": "corpus 2026-10-10: `x as unknown as T` is the deliberate, visible escape hatch "
        "(227 hits, sampled intentional); typescript-eslint keeps no-unsafe-type-assertion out of every shared config",
}
RISK = {"security"}
# Metric thresholds (cognitive complexity, condition size, nesting depth, parameter count): every hit is
# a correct measurement, but on mature repos they flood the review list (corpus m2 2026-10-10: 3.5k
# confirmed hits, up to 26% of a repo's files) with findings about code the PR did not make worse.
# Whether a threshold is policy is the project's call: they run when its linter config enables the
# equivalent check (gocognit, detekt, checkstyle/PMD, ruff C901/PLR, phpmd) or .crev opts in.
METRIC = "corpus m2 2026-10-10: metric threshold, correct but flooding on mature repos ({n} confirmed hits); runs when the project enables an equivalent or .crev opts in"
METRIC_HITS = {"COGNITIVE-COMPLEXITY": {"GO": 752, "PY": 1019, "JAVA": 469, "PHP": 383, "KT": 130},
               "COMPLEX-CONDITION": {"GO": 100, "JAVA": 87, "PHP": 64, "KT": 33},
               "DEEP-NESTING": {"JAVA": 120, "PHP": 82, "GO": 79, "KT": 11},
               "TOO-MANY-PARAMS": {"KT": 108, "JAVA": 20, "PHP": 20, "GO": 8}}
for _m, _by in METRIC_HITS.items():
    for _lang in ("GO", "PY", "JAVA", "PHP", "KT", "JS", "TS"):
        FORCE.setdefault(f"{_lang}-MAINT-{_m}", METRIC.format(n=_by.get(_lang, "same family")))


def main():
    meta = json.load(open(os.path.join(DATA, "lint-meta.json"), encoding="utf-8"))
    tsrec = set(json.load(open(os.path.join(DATA, "tseslint-recommended.json"), encoding="utf-8")))
    xref = yaml.safe_load(open(os.path.join(ROOT, "rules/data/xref.yaml"), encoding="utf-8"))["rules"]
    out, ids = {}, set()
    for f in sorted(glob.glob(os.path.join(ROOT, "rules/packs/*/*.yaml"))):
        for r in yaml.safe_load(open(f, encoding="utf-8"))["rules"]:
            ids.add(r["id"])
            if r.get("kind") == "security" or r.get("category") in RISK:
                continue
            if "opt-in" in (r.get("tags") or []):  # spec-declared (thresholds/naming/style choices)
                eqs = [x for x in (r.get("xref") or []) if ":" in x and "://" not in x and not x.startswith("sonar:")]
                out[r["id"]] = f"opinionated convention or threshold ({', '.join(eqs)}); runs when the project enables an equivalent"
                continue
            eq = list(xref.get(r["id"], [])) + [x for x in (r.get("xref") or []) if ":" in x and "://" not in x]
            judged, recommended, suggestion = [], False, False
            for e in eq:
                tool, rid = e.split(":", 1)
                name = rid.split("/")[-1]
                if tool == "eslint" and name in meta["eslint"]:
                    m = meta["eslint"][name]
                    judged.append(e)
                    recommended |= bool(m.get("recommended"))
                    suggestion |= m.get("type") in ("suggestion", "layout")
                elif tool == "eslint-plugin-vue" and name in meta["eslint-plugin-vue"]:
                    m = meta["eslint-plugin-vue"][name]
                    judged.append(e)
                    recommended |= any("essential" in c for c in (m.get("categories") or []))
                    suggestion |= m.get("type") in ("suggestion", "layout")
                elif tool == "typescript-eslint":
                    judged.append(e)
                    recommended |= name in tsrec
                elif tool == "yamllint":
                    judged.append(e)
                    recommended |= name not in YAMLLINT_OFF
                    # category decides (implicit octal is a real hazard, float spelling is style)
                elif tool == "ruff":
                    judged.append(e)
                    recommended |= bool(re.match(r"^(E4|E7|E9|F)\d", name))
            if not judged or recommended:
                continue
            if suggestion or r.get("category") in OPINION:
                out[r["id"]] = f"not in the linter's recommended set ({', '.join(judged)}); runs when the project enables it"
    out.update({k: v for k, v in FORCE.items() if k in ids})
    with open(os.path.join(ROOT, "rules/data/optin.yaml"), "w", encoding="utf-8") as fh:
        fh.write("# GENERATED by tools/rulegen/optin.py: opinionated rules that only report where the project's linter\n")
        fh.write("# config enables an equivalent rule (see the script for the criteria). Applied by internal/rules.ApplyData.\n")
        yaml.safe_dump({"rules": out}, fh, sort_keys=True, width=200)
    print(f"optin: {len(out)} rules")


if __name__ == "__main__":
    main()

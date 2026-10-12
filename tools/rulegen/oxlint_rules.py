#!/usr/bin/env python3
"""Generate internal/projcfg/oxlint_rules.json: oxlint rule -> category, from the pinned oxc checkout
(tools/corpus/cache/fixtures-src/oxc, `go run ./tools/corpus fetch -repos oxc`; MIT).

Only rule names, plugin and category are recorded (needed to resolve `categories` in .oxlintrc.json
and to map oxlint ids onto crev's eslint-family equivalents); no rule code or docs are copied.
"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "tools/corpus/cache/fixtures-src/oxc/crates/oxc_linter/src/rules")
DECL = re.compile(r"declare_oxc_lint!\(\s*(?:///[^\n]*\n\s*)*([A-Z]\w*)\s*(?:\(tsgolint\))?\s*,\s*(\w+)\s*,\s*(\w+)", re.S)


def kebab(name):
    return re.sub(r"(?<=[a-z0-9])([A-Z])|(?<=[A-Z])([A-Z][a-z])", lambda m: "-" + (m.group(1) or m.group(2)), name).lower()


def main():
    out = {}
    for f in sorted(glob.glob(os.path.join(SRC, "*", "*.rs")) + glob.glob(os.path.join(SRC, "*", "*", "mod.rs"))):
        m = DECL.search(open(f, encoding="utf-8").read())
        if not m:
            continue
        name, plugin, cat = m.groups()
        # file name is the authoritative snake_case rule name (CamelCase loses digits/acronyms)
        stem = os.path.basename(os.path.dirname(f)) if f.endswith("mod.rs") else os.path.splitext(os.path.basename(f))[0]
        out[f"{plugin.replace('_', '-')}/{stem.replace('_', '-')}"] = cat
    commit = "4b756621b65ab54c19dc66fbdcb3cd902d662c20"
    with open(os.path.join(ROOT, "internal/projcfg/oxlint_rules.json"), "w", encoding="utf-8") as fh:
        json.dump({"source": f"oxc-project/oxc@{commit} crates/oxc_linter/src/rules (MIT)", "rules": out}, fh, indent=0, sort_keys=True)
    cats = {}
    for c in out.values():
        cats[c] = cats.get(c, 0) + 1
    print(len(out), cats)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Extract rule metadata (description, deprecated, type, recommended) from the official
linter repositories (ESLint core, typescript-eslint, eslint-plugin-vue) into
data/lint-meta.json. Usage: lintmeta.py <eslint-repo> <typescript-eslint-repo> <eslint-plugin-vue-repo>"""
import json, os, re, sys

def scan(dirpath, ext):
    out = {}
    for f in sorted(os.listdir(dirpath)):
        if not f.endswith(ext) or f.startswith("index"):
            continue
        name = f[: -len(ext)]
        s = open(os.path.join(dirpath, f), encoding="utf-8").read()
        m = re.search(r"description:\s*(?:\n\s*)?(['\"`])(.*?)\1", s, re.S)
        if not m:
            continue
        desc = re.sub(r"\s+", " ", m.group(2).replace("\\'", "'"))
        dep = bool(re.search(r"deprecated:\s*(true|\{)", s))
        typ = re.search(r"type:\s*['\"](problem|suggestion|layout)['\"]", s)
        rec = re.search(r"recommended:\s*(true|['\"]\w+['\"]|\{)", s)
        cats = re.search(r"categories:\s*\[([^\]]*)\]", s)
        out[name] = {"description": desc, "deprecated": dep, "type": typ.group(1) if typ else None,
                     "recommended": bool(rec), "categories": re.findall(r"'([\w-]+)'", cats.group(1)) if cats else None,
                     "requiresTypeChecking": "requiresTypeChecking: true" in s}
    return out

def scan_tse_docs(dirpath):
    out = {}
    for f in sorted(os.listdir(dirpath)):
        if not f.endswith(".mdx"):  # .md files are the removed formatting-rule stubs
            continue
        s = open(os.path.join(dirpath, f), encoding="utf-8").read()
        m = re.search(r"^description:\s*'(.*?)'\s*$", s, re.M)
        if not m:
            continue
        head = s[:3000]
        dep = bool(re.search(r"(?i)(this rule (has been|is) deprecated|:::danger\s*deprecated|deprecated in favor)", head))
        out[f[:-4]] = {"description": m.group(1).replace("''", "'"), "deprecated": dep}
    return out


eslint, tse, epv = sys.argv[1:4]
meta = {"eslint": scan(os.path.join(eslint, "lib/rules"), ".js"),
        "typescript-eslint": scan_tse_docs(os.path.join(tse, "packages/eslint-plugin/docs/rules")),
        "eslint-plugin-vue": scan(os.path.join(epv, "lib/rules"), ".js")}
json.dump(meta, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data/lint-meta.json"), "w", encoding="utf-8"), indent=1, sort_keys=True)
for k, v in meta.items():
    print(k, len(v), "deprecated", sum(x["deprecated"] for x in v.values()))

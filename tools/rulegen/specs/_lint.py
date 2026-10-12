"""Helpers for rules mirrored from official linter rule documentation.

Title/quote come from the rule's own meta.docs.description (data/lint-meta.json, extracted
from the official repositories by lintmeta.py); the description is rendered on the official
rule page, so `rulegen.py verify` checks it verbatim. Deprecated linter rules are refused."""
import json, os, re
from rulegen import rule

_META = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lint-meta.json")))
SRC = {
    "eslint": ("https://eslint.org/docs/latest/rules/{}", "ESLint rule {}", "ESLint v10.12 (docs/latest)"),
    "typescript-eslint": ("https://typescript-eslint.io/rules/{}/", "typescript-eslint rule @typescript-eslint/{}", "typescript-eslint v8.71"),
    "eslint-plugin-vue": ("https://eslint.vuejs.org/rules/{}.html", "eslint-plugin-vue rule vue/{}", "eslint-plugin-vue v10.11"),
}


def desc(src, name):
    m = _META[src].get(name)
    if m is None:
        raise KeyError(f"{src}/{name}: unknown rule")
    if m["deprecated"]:
        raise ValueError(f"{src}/{name} is deprecated upstream; do not mirror it")
    return re.sub(r"`", "", m["description"]).replace("\\\\", "\\").rstrip(".")


def lint(src, name, id, *, language, severity, category, query, bad, good, message, kind=None, applies=None,
         mode="deterministic", ai=None, title=None, framework=None, quote=None, url=None, doc=None, **kw):
    d = desc(src, name)
    u, docname, ver = SRC[src]
    t = title or (d[0].upper() + d[1:])
    return rule(id, t, language=language, framework=framework, kind=kind or ("anti-pattern" if (_META[src][name].get("type") == "problem") else "best-practice"),
                category=category, severity=severity, applies=applies, message=message, url=url or u.format(name),
                doc=doc or docname.format(name), doc_version=ver, quote=quote or d, bad=bad, good=good, query=query, mode=mode, ai=ai,
                tags=kw.pop("tags", None) or [f"{src}:{name}"], **kw)

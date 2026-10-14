#!/usr/bin/env python3
"""rulegen: compact rule specs (specs/*.py) -> rules/packs/<pack>/<topic>.gen.yaml (layout.py).

Every generated rule carries source.quote, a short verbatim excerpt of the cited official
page. `rulegen.py verify` fetches each source URL (HTTP 200 required) and checks the quote
is present, so citations are machine-checked and drift is detected by the weekly docs job.

  python3 tools/rulegen/rulegen.py gen      # write YAML packs
  python3 tools/rulegen/rulegen.py verify   # URL + quote check (network)
"""
import importlib, os, sys
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
RETRIEVED = "2026-10-09"
PACKS = ["java", "spring_boot", "javascript", "typescript", "vue", "nuxt",
         "json", "yaml", "package_json", "composer", "docker", "go", "python", "php", "kotlin", "gradle", "maven",
         "protobuf", "graphql", "terraform", "ytt", "angular", "react", "nuxt_ui", "payload", "vueuse",
         "taint", "simplify_go", "simplify_python", "simplify_javascript", "simplify_java", "simplify_kotlin", "simplify_php", "android", "llm", "kubernetes", "appsec", "ci", "cloud", "cert_java", "supply_chain", "maint", "css", "a11y"]
PACK_NAME = {p: p.replace("_", "-") for p in PACKS}


class Q(str):
    """Marks a multi-line string to be emitted as a YAML block scalar."""


def _repr_str(dumper, data):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.SafeDumper.add_representer(str, _repr_str)
yaml.SafeDumper.add_representer(Q, _repr_str)
yaml.SafeDumper.ignore_aliases = lambda self, data: True


def rule(id, title, *, language, kind, category, severity, applies, message, url, doc, doc_version, quote,
         bad, good, query=None, mode="deterministic", engine="tree-sitter", ai=None, fix=None, rationale=None,
         filters=None, grammar=None, target=None, files=None, config=None, manifest=None, overrides=None,
         tags=None, framework=None, capture=None, requires_dependency=None, xref=None, check=None,
         fp=None, precision=None, requires_config=None, status=None, status_reason=None, cwe=None, owasp=None, asvs=None, wcag=None,
         params=None, match_kind=None):
    """params: {name: {default, from: ["tool:id.option"]}} thresholds the project's linter config may override;
    match_kind: "metric" for measured-threshold rules (see internal/rules/matchkind.go).
    fp: regression examples (former false positives) that must never match - each a code string
    or {"code", "path", "note"}; precision: high|medium|low (low requires mode ai-confirm);
    requires_config: tools the project must configure for the rule to run (e.g. ["yamllint"])."""
    det = {"mode": mode, "engine": engine}
    if target:
        det["target"] = target
    if grammar:
        det["grammar"] = grammar
    if files:
        det["files"] = files
    if requires_dependency:
        det["requires_dependency"] = requires_dependency
    if check:
        det["check"] = check
    if requires_config:
        det["requires_config"] = list(requires_config)
    if query:
        det["query"] = query.strip() + "\n"
    if capture:
        det["capture"] = capture
    if filters:
        det["filters"] = filters
    if config:
        det["config"] = config
    if manifest:
        det["manifest"] = manifest
    r = {"id": id, "title": title, "language": language}
    if framework:
        r["framework"] = framework
    r.update({"kind": kind, "category": category, "severity": severity, "applies_to": applies})
    if overrides:
        r["overrides"] = overrides
    r["detection"] = det
    r["message"] = message
    if rationale:
        r["rationale"] = rationale
    if fix:
        r["fix"] = fix
    if mode == "ai-confirm":
        r["ai_question"] = ai or f"Is this really a case of: {title}? Answer from the code shown."
    r["source"] = {"url": url, "doc": doc, "doc_version": doc_version, "retrieved": RETRIEVED, "quote": quote}
    r["examples"] = {"bad": bad, "good": good}
    if fp:
        r["examples"]["regressions"] = [x if isinstance(x, dict) else {"code": x} for x in fp]
    if tags:
        r["tags"] = tags
    if xref:
        r["xref"] = xref
    if cwe:
        r["cwe"] = cwe
    if owasp:
        r["owasp"] = owasp
    if asvs:
        r["asvs"] = asvs
    if wcag:
        r["wcag"] = list(wcag)
    if precision:
        r["precision"] = precision
    if params:
        r["params"] = params
    if match_kind:
        r["match_kind"] = match_kind
    r["status"] = status or "active"
    if status_reason:
        r["status_reason"] = status_reason
    r["rule_version"] = 1
    return r


def load(name):
    m = importlib.import_module("specs." + name)
    return m.RULES


def amend(rules):
    """Apply specs/_fp.py AMEND entries (false-positive fixes for rules built by helpers that do
    not take the fp/precision/filters keywords): fp (regressions), precision, requires_config, rule_version,
    filters_add, files_add, mode/ai, query (replacement)."""
    try:
        from specs._fp import AMEND
    except ModuleNotFoundError:
        return rules
    for r in rules:
        a = AMEND.get(r["id"])
        if not a:
            continue
        det = r["detection"]
        if "query" in a:
            det["query"] = a["query"].strip() + "\n"
        if a.get("filters_add"):
            det["filters"] = list(det.get("filters") or []) + a["filters_add"]
        if a.get("files_add"):
            det["files"] = list(det.get("files") or []) + a["files_add"]
        if a.get("requires_config"):
            det["requires_config"] = a["requires_config"]
        if a.get("mode"):
            det["mode"] = a["mode"]
            if a["mode"] == "ai-confirm" and "ai_question" not in r:
                r["ai_question"] = a.get("ai") or f"Is this really a case of: {r['title']}? Answer from the code shown."
        if a.get("fp"):
            r["examples"]["regressions"] = list(r["examples"].get("regressions") or []) + [x if isinstance(x, dict) else {"code": x} for x in a["fp"]]
        if a.get("precision"):
            r["precision"] = a["precision"]
        if a.get("rule_version"):
            r["rule_version"] = a["rule_version"]
        # keep key order stable: detection block was mutated in place
    return rules


def generate_all():
    """{(pack, topic): [rules]} for every spec, routed by layout.route (theme tags added)."""
    import layout
    groups = {}
    for p in PACKS:
        try:
            rules = amend(load(p))
        except ModuleNotFoundError as e:
            if e.name != "specs." + p:
                raise
            print("skip (no spec):", p)
            continue
        for r in rules:
            layout.add_theme_tag(r, p)
            groups.setdefault(layout.route(r, p), []).append(r)
    out = {}
    for (pack, topic), rs in groups.items():
        for t, rs2 in layout.split_large(pack, topic, rs).items():
            out.setdefault((pack, t), []).extend(rs2)
    # ids follow <PACK>-<CATEGORY>-<NAME> (ruleid.py); specs may still use legacy ids
    import ruleid
    ren = ruleid.load()
    for (pack, topic), rs in out.items():
        for r in rs:
            r["id"] = ren.get(r["id"]) or ruleid.new_id(r["id"], pack, topic)
    for rs in out.values():
        for r in rs:
            if r.get("xref"):
                r["xref"] = [ren.get(x, x) for x in r["xref"]]
    return out


def gen(only=None):
    """Write rules/packs/<pack>/<topic>.gen.yaml. All specs are always generated (one topic file can
    collect rules from several specs); `only` limits the printed summary. Stale *.gen.yaml files
    (topics that no longer exist) are removed; hand-edited files are never touched."""
    import layout
    groups = generate_all()
    written = set()
    for (pack, topic), rules in sorted(groups.items()):
        out = os.path.join(layout.PACKS_DIR, pack, f"{topic}.gen.yaml")
        layout.dump(out, pack, topic, rules, generated=True)
        written.add(out)
        if not only or pack.replace("-", "_") in only or pack in only:
            print(f"{os.path.relpath(out, ROOT)}: {len(rules)} rules")
    for f in layout.pack_files(generated=True):
        if f not in written:
            os.remove(f)
            print("removed stale", os.path.relpath(f, ROOT))


def verify(only=None):
    import fetch
    bad = 0
    n = 0
    for p in PACKS:
        if only and p not in only:
            continue
        for r in load(p):
            n += 1
            s = r["source"]
            st, text = fetch.fetch(s["url"])
            if st != 200:
                print(f"HTTP {st} {r['id']} {s['url']}")
                bad += 1
            elif not fetch.contains(text, s["quote"]):
                print(f"QUOTE {r['id']} {s['url']}\n      {s['quote']!r}")
                bad += 1
    print(f"verified={n} problems={bad}")
    return bad


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gen"
    if cmd == "gen":
        gen(sys.argv[2:] or None)
    elif cmd == "verify":
        sys.exit(1 if verify(sys.argv[2:] or None) else 0)

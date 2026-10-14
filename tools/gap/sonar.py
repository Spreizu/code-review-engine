#!/usr/bin/env python3
"""Sonar rule catalog as a coverage checklist (catalog metadata only).

Uses only Sonar's public rule catalog metadata - rule key, title, type, severity, CWE/OWASP tags
and membership in the built-in "Sonar way" quality profiles - from the public SonarQube API
(sonarcloud.io; built-in Sonar way profiles). No analyzer code, rule descriptions or test code are fetched or used; crev
implements its own tree-sitter detection, wording and examples, citing official docs, and records
the Sonar key only as `xref: [sonar:<key>]`.

  python tools/gap/sonar.py fetch     # -> tools/gap/cache/sonar-<lang>.json (local, gitignored)
  python tools/gap/sonar.py report    # -> tools/gap/sonar-coverage.md (keys + counts only)

Coverage: a Sonar rule counts as covered when a crev rule carries `sonar:<key>` in xref (data or
pack), or, for security rules, a crev rule of the same language shares a CWE (CWE family match,
marked "cwe" in the report so it can be reviewed).
"""
import glob, json, os, sys, time, urllib.parse, urllib.request
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = os.path.join(ROOT, "tools/gap/cache")

def ensure_cache_module(cache):
    """Fetched sources include .go files; a nested go.mod keeps them out of `go build ./...`."""
    os.makedirs(cache, exist_ok=True)
    p = os.path.join(cache, "go.mod")
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write("module crevcache\n")
API = "https://sonarcloud.io/api"
# SonarCloud requires an organization; built-in profile contents do not vary by org.
# `apache` is public. next.sonarqube.com (the old dogfood host) now 302s to marketing HTML.
ORG = "apache"
# Sonar language key -> crev rule languages
LANGS = {"java": ["java"], "js": ["javascript"], "ts": ["typescript", "javascript"], "py": ["python"], "go": ["go"],
         "kotlin": ["kotlin"], "php": ["php"], "docker": ["dockerfile"], "terraform": ["hcl", "terraform"],
         "yaml": ["yaml"], "json": ["json"], "web": ["html", "vue"], "css": ["css"]}
PROFILES = ("Sonar way core", "Sonar way comprehensive")  # comprehensive keeps the legacy "Sonar way" profile key
FAMILY = {"338": "330", "331": "330", "328": "327", "326": "327", "916": "327", "759": "327", "760": "327",
          "77": "78", "95": "94", "80": "79", "1004": "614", "776": "611",
          "547": "798", "259": "798"}  # 547 = Snyk "Hardcoded Secret" (hard-coded credential family)


def get(path, **q):
    q.setdefault("organization", ORG)
    url = f"{API}/{path}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "crev-sonar-catalog"})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                ctype = r.headers.get("content-type", "")
                if "json" not in ctype:
                    raise RuntimeError(f"expected JSON, got {ctype} from {r.geturl()}")
                return json.load(r)
        except Exception as e:  # noqa: BLE001 - transient network errors are retried
            if i == 3:
                raise
            time.sleep(2 * (i + 1))


def fetch():
    ensure_cache_module(CACHE)
    for lang in LANGS:
        profs = {p["name"]: p["key"] for p in get("qualityprofiles/search", language=lang)["profiles"] if p["isBuiltIn"]}
        rules = {}
        for pname in PROFILES:
            if pname not in profs:
                continue
            page = 1
            while True:
                d = get("rules/search", qprofile=profs[pname], activation="true", ps=500, p=page, f="name,severity,lang,sysTags")
                for r in d["rules"]:
                    e = rules.setdefault(r["key"], {"key": r["key"], "name": r["name"], "type": r.get("type"),
                                                    "severity": r.get("severity"), "profiles": [], "cwe": []})
                    e["profiles"].append(pname)
                if page * 500 >= d["total"]:
                    break
                page += 1
            # CWE tags of the security rules in this profile (facet values, then one query per CWE)
            fac = get("rules/search", qprofile=profs[pname], activation="true", ps=1, facets="cwe")
            for f in fac.get("facets", []):
                for v in f["values"]:
                    if v["val"] == "unknown":
                        continue
                    d = get("rules/search", qprofile=profs[pname], activation="true", cwe=v["val"], ps=500, f="name")
                    for r in d["rules"]:
                        if r["key"] in rules and v["val"] not in rules[r["key"]]["cwe"]:
                            rules[r["key"]]["cwe"].append(v["val"])
        with open(os.path.join(CACHE, f"sonar-{lang}.json"), "w", encoding="utf-8") as fh:
            json.dump(sorted(rules.values(), key=lambda r: r["key"]), fh, indent=0)
        print(lang, len(rules))


def crev_rules():
    xref = yaml.safe_load(open(os.path.join(ROOT, "rules/data/xref.yaml"), encoding="utf-8"))["rules"]
    tax = yaml.safe_load(open(os.path.join(ROOT, "rules/data/taxonomy.yaml"), encoding="utf-8"))["rules"]
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "rules/packs/*/*.yaml"))):
        for r in yaml.safe_load(open(f, encoding="utf-8"))["rules"]:
            eq = list(xref.get(r["id"], [])) + [x for x in (r.get("xref") or []) if isinstance(x, str) and "://" not in x]
            cwe = [str(c).replace("CWE-", "") for c in (r.get("cwe") or tax.get(r["id"], {}).get("cwe") or [])]
            out.append({"id": r["id"], "lang": r.get("language"), "sonar": [e.split(":", 1)[1] for e in eq if e.startswith("sonar:")],
                        "semgrep": [e.split(":", 1)[1] for e in eq if e.startswith("semgrep:")],
                        "snyk": [e.split(":", 1)[1] for e in eq if e.startswith("snyk:")],
                        "cwe": cwe, "status": r.get("status", "active")})
    return out


def report():
    crev = crev_rules()
    by_key = {}
    for r in crev:
        for k in r["sonar"]:
            by_key.setdefault(k, []).append(r["id"])
    lines = ["# Sonar way coverage (checklist: Sonar rule catalog metadata only)", "",
             "Generated by `python tools/gap/sonar.py report` from the local catalog cache. Covered = a crev rule names the Sonar key",
             "in `xref` (`sonar:<key>`), or (security rules only) a crev rule of the same language shares the CWE family (`cwe`).",
             "Only rule keys and counts are written here; titles stay in the local cache.", "",
             "| Sonar language | profile | rules | covered (xref) | covered (cwe) | coverage | security rules | security covered |",
             "|---|---|---|---|---|---|---|---|"]
    gaps = {}
    for lang, crev_langs in LANGS.items():
        p = os.path.join(CACHE, f"sonar-{lang}.json")
        if not os.path.exists(p):
            continue
        rules = json.load(open(p, encoding="utf-8"))
        pool = [r for r in crev if r["lang"] in crev_langs]
        cwes = {FAMILY.get(c, c) for r in pool for c in r["cwe"]}
        for prof in PROFILES:
            rs = [r for r in rules if prof in r["profiles"]]
            if not rs:
                continue
            x = [r for r in rs if r["key"] in by_key]
            c = [r for r in rs if r["key"] not in by_key and any(FAMILY.get(w, w) in cwes for w in r["cwe"])]
            sec = [r for r in rs if r["type"] in ("VULNERABILITY", "SECURITY_HOTSPOT")]
            secc = [r for r in sec if r in x or r in c]
            lines.append(f"| {lang} | {prof} | {len(rs)} | {len(x)} | {len(c)} | {100 * (len(x) + len(c)) / len(rs):.1f}% | {len(sec)} | {len(secc)} |")
            if prof == PROFILES[-1]:
                gaps[lang] = [r for r in rs if r not in x and r not in c]
    lines += ["", "## Uncovered Sonar way (comprehensive) keys by type", ""]
    for lang, g in gaps.items():
        by_type = {}
        for r in g:
            by_type.setdefault(r["type"], []).append(r["key"].split(":")[-1])
        lines.append(f"- **{lang}**: " + "; ".join(f"{t} {len(v)}" for t, v in sorted(by_type.items())))
        sec = by_type.get("VULNERABILITY", []) + by_type.get("SECURITY_HOTSPOT", [])
        if sec:
            lines.append(f"  - security gaps: {', '.join(sorted(sec))}")
    with open(os.path.join(ROOT, "tools/gap/sonar-coverage.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines[:30]))


if __name__ == "__main__":
    {"fetch": fetch, "report": report}[sys.argv[1] if len(sys.argv) > 1 else "report"]()

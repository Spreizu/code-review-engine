#!/usr/bin/env python3
"""OWASP checklists -> crev rule coverage.

ASVS 5.0: the official flat JSON export (https://github.com/OWASP/ASVS, CC BY-SA 4.0) is fetched into
tools/gap/cache/ (gitignored); only requirement ids and chapter names are used. tools/gap/owasp/asvs5_map.py
marks the requirements that static analysis of code/config can verify, each with an own short label,
the CWE ids that express it and optionally a rule-id regex. All other requirements (process,
architecture, runtime-only) are listed as not code-verifiable.

A requirement is covered when an enabled crev security rule (category security or a CWE; for scoped
Top 10 items such as Docker/Kubernetes/mobile, any rule in scope) carries its id in `asvs`, or matches the regex (when
one is given), or otherwise shares a CWE family.

  python tools/gap/owasp.py fetch && python tools/gap/owasp.py   # writes tools/gap/owasp-coverage.md
"""
import glob, json, os, re, shutil, sys, urllib.request
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "owasp"))
from sonar import FAMILY, ROOT  # noqa: E402
from snyk import ensure_cache_module  # noqa: E402
import asvs5_map  # noqa: E402
import top10s  # noqa: E402
import yaml  # noqa: E402

CACHE = os.path.join(ROOT, "tools/gap/cache")
ASVS_URL = "https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.flat.json"
ASVS_FILE = os.path.join(CACHE, "asvs5.flat.json")


def fetch():
    ensure_cache_module(CACHE)
    try:
        req = urllib.request.Request(ASVS_URL, headers={"User-Agent": "curl/8 (crev gap checklist)"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        json.loads(data)
        open(ASVS_FILE, "wb").write(data)
    except Exception as e:  # noqa: BLE001
        if os.path.exists("/tmp/owasp/asvs5.flat.json"):
            shutil.copy("/tmp/owasp/asvs5.flat.json", ASVS_FILE)
            print("fetch failed (%s); used /tmp/owasp copy" % e)
        else:
            raise


def rules():
    tax = yaml.safe_load(open(os.path.join(ROOT, "rules/data/taxonomy.yaml"), encoding="utf-8"))["rules"]
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "rules/packs/*/*.yaml"))):
        for r in yaml.safe_load(open(f, encoding="utf-8"))["rules"]:
            if r.get("status", "active") in ("disabled", "deprecated"):
                continue
            t = tax.get(r["id"], {})
            fam = lambda cs: {FAMILY.get(str(c).replace("CWE-", ""), str(c).replace("CWE-", "")) for c in cs}
            sec = r.get("category") == "security" or bool(r.get("cwe") or t.get("cwe"))
            out.append({"id": r["id"], "sec": sec, "lang": r.get("language"), "cwe": fam(r.get("cwe") or t.get("cwe") or []),
                        "asvs": set(r.get("asvs") or []) | set(t.get("asvs") or []),
                        "owasp": set(r.get("owasp") or []) | set(t.get("owasp") or [])})
    # rules defined in Go rather than in a pack (internal/sca: OSV.dev dependency scan, on by default)
    out.append({"id": "SCA-OSV-VULNERABLE-DEPENDENCY", "sec": True, "lang": "any", "cwe": {"1395"},
                "asvs": {"V3.7.1", "V15.2.1"}, "owasp": {"A06:2021", "A03:2025"}})
    return out


def match(item_id, cwes, rx, rs):
    fam = {FAMILY.get(c.replace("CWE-", ""), c.replace("CWE-", "")) for c in cwes}
    hit = []
    for r in rs:
        if item_id in r["asvs"] or item_id in r["owasp"]:
            hit.append(r["id"])
        elif rx:
            if re.search(rx, r["id"]):
                hit.append(r["id"])
        elif fam & r["cwe"]:
            hit.append(r["id"])
    return hit


def asvs(rs):
    rs = [r for r in rs if r["sec"]]  # ASVS is a security checklist: only security rules count
    reqs = json.load(open(ASVS_FILE, encoding="utf-8"))["requirements"]
    ch = OrderedDict()
    for q in reqs:
        c = ch.setdefault(q["chapter_id"], {"name": q["chapter_name"], "all": 0, "cv": [], "cov": [], "gap": []})
        c["all"] += 1
        m = asvs5_map.M.get(q["req_id"])
        if not m:
            continue
        c["cv"].append(q["req_id"])
        h = match(q["req_id"], m[1], m[2], rs)
        (c["cov"] if h else c["gap"]).append((q["req_id"], m[0], len(h), h[:3]))
    unknown = set(asvs5_map.M) - {q["req_id"] for q in reqs}
    if unknown:
        sys.exit("asvs5_map ids not in ASVS 5.0: %s" % sorted(unknown))
    return ch


def top10(rs):
    out = OrderedDict()
    for name, (url, items) in top10s.PROJECTS.items():
        rows = []
        for iid, it in items.items():
            if it is None:
                rows.append((iid, None, 0, []))
                continue
            label, cwes, rx, scope = it
            # scoped items (Docker, Kubernetes, mobile) count hardening rules of any category in scope
            pool = [r for r in rs if re.search(scope, r["id"])] if scope else [r for r in rs if r["sec"]]
            h = match(iid, cwes, rx, pool)
            rows.append((iid, label, len(h), h[:3]))
        out[name] = (url, rows)
    return out


def report():
    rs = rules()
    ch = asvs(rs)
    tot_all = sum(c["all"] for c in ch.values())
    tot_cv = sum(len(c["cv"]) for c in ch.values())
    tot_cov = sum(len(c["cov"]) for c in ch.values())
    L = ["# OWASP coverage", "",
         "Generated by `python tools/gap/owasp.py`. Checklist ids only; requirement texts stay in the local cache",
         "(OWASP content is CC BY-SA 4.0; see the linked sources). Labels are crev's own short paraphrases.", "",
         "## ASVS 5.0 (https://github.com/OWASP/ASVS/tree/v5.0.0/5.0)", "",
         f"{tot_all} requirements; {tot_cv} judged code-verifiable by static analysis; **{tot_cov} covered "
         f"({100 * tot_cov / max(tot_cv, 1):.0f}% of code-verifiable)**.", "",
         "| chapter | requirements | code-verifiable | covered | coverage |", "|---|---|---|---|---|"]
    for cid, c in ch.items():
        cv = len(c["cv"])
        pct = f"{100 * len(c['cov']) / cv:.0f}%" if cv else "n/a"
        L.append(f"| {cid} {c['name']} | {c['all']} | {cv} | {len(c['cov'])} | {pct} |")
    L += ["", "### Code-verifiable requirements without a rule", ""]
    for cid, c in ch.items():
        for rid, label, _, _ in c["gap"]:
            L.append(f"- {rid} {label}")
    L += ["", "### Covered requirements (rule count, examples)", ""]
    for cid, c in ch.items():
        for rid, label, n, ex in c["cov"]:
            L.append(f"- {rid} {label}: {n} ({', '.join(ex)})")
    t10 = top10(rs)
    L += ["", "## Top 10 projects", "",
          "Items marked n/a cannot be verified from code or config (process, runtime or design).", "",
          "| project | items | code-verifiable | covered | coverage |", "|---|---|---|---|---|"]
    for name, (url, rows) in t10.items():
        cv = [r for r in rows if r[1] is not None]
        cov = [r for r in cv if r[2]]
        L.append(f"| [{name}]({url}) | {len(rows)} | {len(cv)} | {len(cov)} | {100 * len(cov) / max(len(cv), 1):.0f}% |")
        print(f"{name}: {len(cov)}/{len(cv)}")
    for name, (url, rows) in t10.items():
        L += ["", f"### {name}", ""]
        for iid, label, n, ex in rows:
            L.append(f"- {iid} " + ("n/a" if label is None else f"{label}: " + (f"{n} ({', '.join(ex)})" if n else "**no rule**")))
    open(os.path.join(HERE, "owasp-coverage.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"ASVS 5.0: {tot_cov}/{tot_cv} code-verifiable covered")


if __name__ == "__main__":
    if sys.argv[1:] == ["fetch"]:
        fetch()
    else:
        report()

"""Reviewer handoff + scoring for the crev vs AI benchmark (see tools/bench/README.md).

  python tools/bench/review.py prompts   anonymised reviewer inputs in work/review/ (+ crev ai export per case)
  python tools/bench/review.py judge     blinded pool of findings that match no label -> work/review/judge.md
  python tools/bench/review.py score     tools/bench/results.json + tables for report.md
Answers (the AI reviewer's output, committed): tools/bench/answers/{A,B,C,judge}.jsonl
"""
import json, os, random, re, subprocess, sys, collections, math, glob, shutil, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "work")
CASES = os.path.join(WORK, "cases")
REV = os.path.join(WORK, "review")
ANS = os.path.join(ROOT, "answers")
CREV = os.environ.get("CREV", "/tmp/crev")
TOL = 3

B_INSTR = """You are reviewing a pull request. Report the real problems a senior reviewer would raise:
bugs and logic errors, security vulnerabilities, API misuse or deprecated APIs, and design problems that
matter. Skip style nits. For each problem give the file path, the line number in the NEW version of the
file, a category (bug|security|api|design|perf) and a one-sentence explanation. Say "none" if the change
is fine. Answer format (JSONL): {"case":"cNN","path":"...","line":N,"cat":"...","msg":"..."} or
{"case":"cNN","none":true}."""
C_INSTR = """Same pull request, now with the deterministic code review engine's findings (crev) attached.
crev already covers known API/version/security patterns, so do NOT repeat its findings and do not review
for API or security patterns: report only logic, intent and design problems crev cannot see. Same format
(written to C.jsonl)."""

def cases():
    return json.load(open(os.path.join(ROOT, "cases", "cases.json")))

def anon():
    cs = sorted(c["id"] for c in cases())
    rnd = random.Random("crev-bench-2026-10-10")
    rnd.shuffle(cs)
    return {cid: f"c{i+1:02d}" for i, cid in enumerate(cs)}

def crev_report(cid, run=1):
    return json.load(open(os.path.join(CASES, cid, f"crev-{run}.json")))

def export(cid):
    d = os.path.join(CASES, cid)
    p = os.path.join(d, "repo", ".crev", "ai-handoff", "batches.jsonl")
    if os.path.exists(p):  # a run with no pending items writes nothing: never read a stale handoff
        os.remove(p)
    subprocess.run([CREV, "ai", "export", "repo"], cwd=d, capture_output=True)
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []

def cmd_prompts(per=10):
    shutil.rmtree(REV, ignore_errors=True)
    os.makedirs(REV)
    m = anon()
    json.dump(m, open(os.path.join(WORK, "anon-map.json"), "w"), indent=1)  # not in review/: reviewer must not read it
    order = sorted(m, key=lambda k: m[k])
    meta = {c["id"]: c for c in cases()}
    for b in range(0, len(order), per):
        n = b // per + 1
        diffs, crevs = [f"# Batch {n}: diffs\n\n{B_INSTR}\n"], [f"# Batch {n}: crev output (read only after writing B for these cases)\n\n{C_INSTR}\n"]
        for cid in order[b:b + per]:
            a = m[cid]
            diffs.append(f"\n## {a} ({meta[cid]['lang']})\n```diff\n{open(os.path.join(CASES, cid, 'diff.patch')).read()}```\n")
            rep = crev_report(cid)
            crevs.append(f"\n## {a}\n")
            det = [f for f in rep.get("findings") or [] if f["status"] == "confirmed"]
            for f in det:
                crevs.append(f"- crev {f['location']['path']}:{f['location']['start_line']} [{f['rule_id']}] {f.get('message','')[:200]}\n")
            items = []
            for bt in export(cid):
                for it in bt["items"]:
                    r = bt["rules"][it["rule"]]
                    items.append(f"- ai-confirm item {it['id']} [{it['rule']}] {it['path']}:{it['lines'][0]}-{it['lines'][1]} — {r['title']}. Q: {r.get('question','')}\n```\n{it['code']}\n```\n")
            crevs += items
            if not det and not items:
                crevs.append("- (no crev findings)\n")
        open(os.path.join(REV, f"batch-{n:02d}.md"), "w").write("".join(diffs))
        open(os.path.join(REV, f"batch-{n:02d}-crev.md"), "w").write("".join(crevs))
    print(len(order), "cases in", math.ceil(len(order) / per), "batches ->", REV)

# ---------------- scoring ----------------
def load_jsonl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []

SEC_RULE = re.compile(r"SEC|INJ|XSS|SQL|CMD|SSRF|PATH|DESER|CRYPTO|HASH|EVAL|SECRET|PASSWORD|LDAP|XXE|PICKLE|YAML-LOAD|SHELL", re.I)

def ingest_A(cid, a, verdicts):
    d = os.path.join(CASES, cid)
    vs = [v for v in verdicts if v["case"] == a]
    if vs:
        p = os.path.join(d, "repo", ".crev", "ai-handoff", "responses.jsonl")
        with open(p, "w") as f:
            for v in vs:
                f.write(json.dumps({k: v[k] for k in v if k != "case"}) + "\n")
        subprocess.run([CREV, "ingest", "-root", "repo", p], cwd=d, capture_output=True)
        rep = json.load(open(os.path.join(d, "repo", ".crev", "report.json")))
    else:
        rep = crev_report(cid)
    out = []
    for f in rep.get("findings") or []:
        if f["status"] == "confirmed" or (f["status"] == "ai_confirmed" and f.get("ai", {}).get("confidence", f.get("confidence")) == "high"):
            out.append({"path": f["location"]["path"], "line": f["location"]["start_line"], "rule": f["rule_id"],
                        "cat": "security" if (f.get("kind") == "security" or SEC_RULE.search(f["rule_id"])) else "api",
                        "msg": f.get("message", "")})
    return out

def findings_by_setup():
    m = anon()
    A = load_jsonl(os.path.join(ANS, "A.jsonl"))
    B = load_jsonl(os.path.join(ANS, "B.jsonl"))
    C = load_jsonl(os.path.join(ANS, "C.jsonl"))
    res = {}
    for c in cases():
        a = m[c["id"]]
        fa = ingest_A(c["id"], a, A)
        fb = [x for x in B if x["case"] == a and not x.get("none")]
        fc = fa + [dict(x, ai=True) for x in C if x["case"] == a and not x.get("none")]
        res[c["id"]] = {"A": fa, "B": fb, "C": fc}
    return res

def matches(c, f):
    # a security label (OWASP, injected vulnerability) is only hit by a security finding at that spot
    sec = c["source"] == "owasp" or (c["source"] == "seeded" and c["fix_subject"].startswith("injected"))
    if sec and f.get("cat") != "security":
        return False
    for l in c["labels"]:
        if l["path"] != f["path"]:
            continue
        if c["source"] == "owasp":
            if f.get("cat") == "security":
                return True
            continue
        if any(abs(f["line"] - x) <= TOL for x in l["lines"]):
            return True
    return False

def jkey(cid, f):
    return hashlib.sha1(f"{cid}|{f['path']}|{f['line']}|{f['msg']}".encode()).hexdigest()[:10]

def context(cid, f, k=2):
    p = os.path.join(CASES, cid, "repo", f["path"])
    if not os.path.exists(p):
        return ""
    ls = open(p, errors="replace").read().split("\n")
    lo, hi = max(1, f["line"] - k), min(len(ls), f["line"] + k)
    return "\n".join(f"{i}| {ls[i-1]}" for i in range(lo, hi + 1))

def cmd_judge():
    m = anon()
    fs = findings_by_setup()
    meta = {c["id"]: c for c in cases()}
    pool = {}
    for cid, s in fs.items():
        for setup, lst in s.items():
            for f in lst:
                if matches(meta[cid], f):
                    continue
                pool.setdefault(jkey(cid, f), (cid, f))
    keys = sorted(pool)
    random.Random("judge").shuffle(keys)
    out = ["# Blinded judging: is each finding a real problem worth a reviewer comment? (setup hidden, rule ids stripped)\n",
           'Answer in answers/judge.jsonl: {"j":"<key>","valid":true|false,"why":"..."}\n']
    for k in keys:
        cid, f = pool[k]
        msg = re.sub(r"\[[A-Z0-9-]{4,}\]", "", f["msg"])
        out.append(f"\n## {k} — {m[cid]} {f['path']}:{f['line']}\n{msg}\n```\n{context(cid, f)}\n```\n")
    open(os.path.join(REV, "judge.md"), "w").write("".join(out))
    print(len(keys), "findings to judge ->", os.path.join(REV, "judge.md"))

def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0, c - h), min(1, c + h)

def cmd_score():
    m = anon()
    meta = {c["id"]: c for c in cases()}
    fs = findings_by_setup()
    J = {j["j"]: j["valid"] for j in load_jsonl(os.path.join(ANS, "judge.jsonl"))}
    rows = []
    for cid, s in fs.items():
        c = meta[cid]
        labelled = bool(c["labels"])
        for setup, lst in s.items():
            tp_lab = sum(1 for f in lst if matches(c, f))
            extra = [f for f in lst if not matches(c, f)]
            valid = sum(1 for f in extra if J.get(jkey(cid, f)) is True)
            unjudged = sum(1 for f in extra if jkey(cid, f) not in J)
            rows.append({"case": cid, "lang": c["lang"], "source": c["source"], "setup": setup, "labelled": labelled,
                         "found": labelled and tp_lab > 0, "n": len(lst), "tp_label": tp_lab, "valid_extra": valid,
                         "invalid": len(extra) - valid - unjudged, "unjudged": unjudged,
                         "owasp_real": c.get("owasp", {}).get("real")})
    json.dump(rows, open(os.path.join(ROOT, "results.json"), "w"), indent=1)
    print(len(rows), "rows; unjudged", sum(r["unjudged"] for r in rows))

if __name__ == "__main__":
    {"prompts": cmd_prompts, "judge": cmd_judge, "score": cmd_score}[sys.argv[1]]()

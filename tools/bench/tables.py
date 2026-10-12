"""Aggregate tools/bench/results.json (+ cost/consistency data) into markdown tables for report.md."""
import json, os, math, collections, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from review import cases, anon, wilson, load_jsonl, ANS, CASES, B_INSTR, C_INSTR, crev_report  # noqa

ROOT = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(ROOT, "results.json")))
meta = {c["id"]: c for c in cases()}

def group(c):
    s = c["source"]
    if s == "seeded":
        return "seeded-security" if c["fix_subject"].startswith("injected") else "seeded-logic"
    if s == "owasp":
        return "owasp-vulnerable" if c["owasp"]["real"] else "owasp-safe"
    return s

def fmt(p):
    return "n/a" if p != p else f"{p:.2f}"

def ci(k, n):
    p, lo, hi = wilson(k, n)
    return "n/a" if n == 0 else f"{p:.2f} [{lo:.2f}–{hi:.2f}]"

def agg(rs):
    lab = [r for r in rs if r["labelled"]]
    found = sum(r["found"] for r in lab)
    n = sum(r["n"] for r in rs)
    good = sum(r["tp_label"] + r["valid_extra"] for r in rs)
    strict = sum(r["tp_label"] for r in rs)
    inval = sum(r["invalid"] for r in rs)
    return {"cases": len(rs), "bugs": len(lab), "found": found, "recall": ci(found, len(lab)),
            "n": n, "precision": ci(good, n), "strict": fmt(strict / n if n else float("nan")),
            "fp_per_pr": f"{inval / len(rs):.2f}" if rs else "n/a"}

out = []
def table(title, key):
    out.append(f"\n### {title}\n\n| {key} | setup | cases | labelled bugs | found | recall [95% CI] | findings | precision [95% CI] | label-only precision | invalid findings / PR |\n|---|---|---|---|---|---|---|---|---|---|\n")

def emit(name, setup, a):
    out.append(f"| {name} | {setup} | {a['cases']} | {a['bugs']} | {a['found']} | {a['recall']} | {a['n']} | {a['precision']} | {a['strict']} | {a['fp_per_pr']} |\n")

table("Overall", "set")
for s in "ABC":
    emit("all", s, agg([r for r in rows if r["setup"] == s]))
    emit("excl. OWASP", s, agg([r for r in rows if r["setup"] == s and r["source"] != "owasp"]))

table("By case type", "type")
for g in ["szz", "seeded-logic", "seeded-security", "owasp-vulnerable", "owasp-safe", "real-clean", "seeded-clean"]:
    for s in "ABC":
        emit(g, s, agg([r for r in rows if r["setup"] == s and group(meta[r["case"]]) == g]))

table("By language", "language")
for lang in ["java", "ts", "python", "go", "php", "kotlin"]:
    for s in "ABC":
        emit(lang, s, agg([r for r in rows if r["setup"] == s and r["lang"] == lang]))

# OWASP TPR/FPR
out.append("\n### OWASP Benchmark cases (a case counts as flagged when a security finding lands in the file)\n\n| setup | lang | TPR (vulnerable flagged) | FPR (safe flagged) |\n|---|---|---|---|\n")
for s in "ABC":
    for lang in ["java", "python"]:
        rs = [r for r in rows if r["setup"] == s and r["source"] == "owasp" and r["lang"] == lang]
        t = [r for r in rs if r["owasp_real"]]
        f = [r for r in rs if not r["owasp_real"]]
        fp = sum(1 for r in f if r["n"] > 0)
        out.append(f"| {s} | {lang} | {sum(r['found'] for r in t)}/{len(t)} | {fp}/{len(f)} |\n")

# cost + consistency
m = anon()
A = load_jsonl(os.path.join(ANS, "A.jsonl")); B = load_jsonl(os.path.join(ANS, "B.jsonl")); C = load_jsonl(os.path.join(ANS, "C.jsonl"))
tok = collections.defaultdict(list)
times, consistent = [], 0
for cid, c in meta.items():
    a = m[cid]
    diff = open(os.path.join(CASES, cid, "diff.patch")).read()
    bo = sum(len(json.dumps(x)) for x in B if x["case"] == a)
    co = sum(len(json.dumps(x)) for x in C if x["case"] == a)
    ao = sum(len(json.dumps(x)) for x in A if x["case"] == a)
    bp = os.path.join(CASES, cid, "repo", ".crev", "ai-handoff", "batches.jsonl")
    ai_in = os.path.getsize(bp) if os.path.exists(bp) else 0
    reps = [crev_report(cid, k) for k in (1, 2, 3)]
    crev_txt = sum(len(f.get("message", "")) + 80 for f in reps[0].get("findings") or [])
    tok["A"].append((ai_in / 4, ao / 4))
    tok["B"].append(((len(B_INSTR) + len(diff)) / 4, bo / 4))
    tok["C"].append(((len(B_INSTR) + len(C_INSTR) + len(diff) + crev_txt) / 4 + ai_in / 4, (co + ao) / 4))
    times.append(sum(r["_elapsed"] for r in reps) / 3)
    sig = [sorted((f["rule_id"], f["location"]["path"], f["location"]["start_line"], f["status"]) for f in r.get("findings") or []) for r in reps]
    consistent += sig[0] == sig[1] == sig[2]
out.append("\n### Cost per PR (tokens estimated as characters / 4; AI wall time not measurable in this setup)\n\n| setup | mean input tokens | mean output tokens | total input tokens (91 PRs) | crev wall time / PR |\n|---|---|---|---|---|\n")
for s in "ABC":
    i = sum(x for x, _ in tok[s]); o = sum(y for _, y in tok[s])
    t = f"{sum(times)/len(times):.2f} s (mean of 3 runs)" if s != "B" else "—"
    if s == "C":
        t += " + AI"
    if s == "A":
        t += " + AI for ai-confirm items only"
    out.append(f"| {s} | {i/len(tok[s]):.0f} | {o/len(tok[s]):.0f} | {i:.0f} | {t} |\n")
out.append(f"\ncrev run-to-run consistency: {consistent}/{len(meta)} PRs produced identical finding sets (rule, path, line, status) in 3 runs. AI items needing an answer in A: {sum(1 for x in A)} over {len({x['case'] for x in A})} PRs.\n")
print("".join(out))

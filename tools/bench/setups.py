"""Setups D and E for the crev vs AI benchmark, plus input-token cost by PR size (see report.md, "Setups D/E").

  python tools/bench/setups.py score            D/E findings per case from A + B answers -> results-de.json, tables
  python tools/bench/setups.py sizes DIR...     token cost per PR size bucket on real commits of full clones in DIR

D = crev review list (A) + the full-diff AI review (B), merged (a B finding within +-3 lines of an A finding on the
    same file is one finding).
E = crev review list (A) + the AI review restricted to the hunks crev marks risky. Risky = (1) files with any crev
    finding (confirmed or pending ai-confirm), (2) security-sensitive paths, (3) high-complexity hunks
    (>= 25 added lines or >= 4 added branch points). E's AI findings are B's findings that fall in risky hunks:
    this simulates a reviewer that only saw those hunks (same reviewer, same answers), so it is an upper bound on
    what a narrower prompt would find in them.
Tokens are characters / 4 for the reviewer input (instructions + diff/hunks + crev findings text) plus the
ai-confirm payload crev exports (A's AI cost, also paid by D and E).
"""
import json, os, re, subprocess, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from review import (cases, anon, load_jsonl, ingest_A, matches, jkey, wilson, ANS, CASES, B_INSTR, TOL, CREV)  # noqa

ROOT = os.path.dirname(os.path.abspath(__file__))
SEC_PATH = re.compile(r"(?i)(auth|login|logout|session|token|jwt|oauth|passw|secret|crypt|cipher|security|permission|acl|admin|"
                      r"payment|billing|upload|exec|shell|sql|serializ|pickle|cookie|csrf|cors|redirect|sanitiz|escape|privilege)")
BRANCH = re.compile(r"\b(if|elif|else|for|foreach|while|case|catch|except|switch|when)\b|&&|\|\||\?\?|\?[^:]*:")
E_INSTR = ("You are reviewing the risky parts of a pull request selected by a deterministic engine (files with engine "
           "findings, security-sensitive paths, complex hunks). The engine's findings are listed; do not repeat them. "
           "Report bugs, security and design problems in these hunks. Same JSONL answer format.")
# generated / vendored / lock files: excluded from every setup's input (no reviewer reads them line by line)
EXCLUDE = [":(exclude)*.lock", ":(exclude)*-lock.json", ":(exclude)*-lock.yaml", ":(exclude)go.sum", ":(exclude)*.min.js", ":(exclude)*.map",
           ":(exclude)dist/**", ":(exclude)vendor/**", ":(exclude)**/__snapshots__/**", ":(exclude)*.snap", ":(exclude)*.svg",
           ":(exclude)*.png", ":(exclude)*.jpg", ":(exclude)*.ico", ":(exclude)*.woff*", ":(exclude)CHANGELOG*", ":(exclude)*.po"]
BUCKETS = [("small", 0, 50), ("medium", 51, 300), ("large", 301, 1500), ("huge", 1501, 10 ** 9)]


def bucket(n):
    return next(b for b, lo, hi in BUCKETS if lo <= n <= hi)


def parse_diff(text):
    """[{path, new_start, new_end, added, text}] per hunk (new-file line numbers)."""
    hunks, path, cur = [], None, None
    for line in text.split("\n"):
        if line.startswith("+++ "):
            p = line[4:].strip()
            path = None if p == "/dev/null" else re.sub(r"^b/", "", p)
            continue
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
        if m and path:
            s, n = int(m.group(1)), int(m.group(2) or 1)
            cur = {"path": path, "new_start": s, "new_end": s + max(n, 1) - 1, "added": [], "text": [line]}
            hunks.append(cur)
            continue
        if cur is not None and not line.startswith(("diff --git", "index ", "--- ", "new file", "deleted file", "similarity", "rename ")):
            cur["text"].append(line)
            if line.startswith("+"):
                cur["added"].append(line[1:])
    return hunks


def changed_lines(text):
    return sum(1 for l in text.split("\n") if (l.startswith("+") or l.startswith("-")) and not l.startswith(("+++", "---")))


def risky_hunks(hunks, finding_paths):
    out = []
    for h in hunks:
        why = []
        if h["path"] in finding_paths:
            why.append("finding")
        if SEC_PATH.search(h["path"]):
            why.append("sec-path")
        branches = sum(len(BRANCH.findall(a)) for a in h["added"])
        if len(h["added"]) >= 25 or branches >= 4:
            why.append("complex")
        if why:
            out.append(dict(h, why=why))
    return out


def crev_paths(rep):
    return {f["location"]["path"] for f in rep.get("findings") or [] if f.get("status") not in ("suppressed", "ai_rejected")}


def crev_text(rep):
    return sum(len(f.get("message", "")) + 80 for f in rep.get("findings") or [] if f.get("status") in ("confirmed", "pending_ai", "ai_confirmed"))


def in_hunks(f, hs):
    return any(h["path"] == f["path"] and h["new_start"] - TOL <= f["line"] <= h["new_end"] + TOL for h in hs)


def merge(a, b):
    out = list(a)
    for f in b:
        if not any(x["path"] == f["path"] and abs(x["line"] - f["line"]) <= TOL for x in a):
            out.append(f)
    return out


def ci(k, n):
    p, lo, hi = wilson(k, n)
    return "n/a" if n == 0 else f"{p:.2f} [{lo:.2f}-{hi:.2f}]"


def cmd_score():
    m = anon()
    A = load_jsonl(os.path.join(ANS, "A.jsonl"))
    B = load_jsonl(os.path.join(ANS, "B.jsonl"))
    J = {j["j"]: j["valid"] for j in load_jsonl(os.path.join(ANS, "judge.jsonl"))}
    rows, unj = [], []
    for c in cases():
        cid, a = c["id"], m[c["id"]]
        d = os.path.join(CASES, cid)
        rep = json.load(open(os.path.join(d, "crev-1.json")))
        diff = open(os.path.join(d, "diff.patch")).read()
        hs = parse_diff(diff)
        risky = risky_hunks(hs, crev_paths(rep))
        fa = ingest_A(cid, a, A)
        fb = [x for x in B if x["case"] == a and not x.get("none")]
        bp = os.path.join(d, "repo", ".crev", "ai-handoff", "batches.jsonl")
        ai_in = os.path.getsize(bp) if os.path.exists(bp) else 0
        tok = {"A": ai_in / 4, "B": (len(B_INSTR) + len(diff)) / 4}
        tok["D"] = tok["B"] + tok["A"] + crev_text(rep) / 4
        tok["E"] = ((len(E_INSTR) + sum(len("\n".join(h["text"])) for h in risky) + crev_text(rep)) / 4 + tok["A"]) if risky else tok["A"]
        sets = {"A": fa, "B": fb, "D": merge(fa, fb), "E": merge(fa, [f for f in fb if in_hunks(f, risky)])}
        n_changed = changed_lines(diff)
        for s, lst in sets.items():
            tp = sum(1 for f in lst if matches(c, f))
            extra = [f for f in lst if not matches(c, f)]
            valid = sum(1 for f in extra if J.get(jkey(cid, f)) is True)
            un = [f for f in extra if jkey(cid, f) not in J]
            unj += [(cid, s, f) for f in un]
            rows.append({"case": cid, "source": c["source"], "lang": c["lang"], "setup": s, "labelled": bool(c["labels"]),
                         "found": bool(c["labels"]) and tp > 0, "n": len(lst), "tp_label": tp, "valid_extra": valid,
                         "invalid": len(extra) - valid - len(un), "unjudged": len(un), "tokens": tok[s], "changed": n_changed,
                         "bucket": bucket(n_changed), "risky_hunks": len(risky), "hunks": len(hs),
                         "clean": c["source"] in ("real-clean",) or (c["source"] == "seeded" and not c["labels"])})
    json.dump(rows, open(os.path.join(ROOT, "results-de.json"), "w"), indent=1)
    seen = set()
    for cid, s, f in unj:
        k = jkey(cid, f)
        if k not in seen:
            seen.add(k)
            print("UNJUDGED", k, cid, f["path"], f["line"], f.get("rule", ""), f["msg"][:120])
    print(tables(rows))


def agg(rs):
    lab = [r for r in rs if r["labelled"]]
    found = sum(r["found"] for r in lab)
    n = sum(r["n"] for r in rs)
    good = sum(r["tp_label"] + r["valid_extra"] for r in rs)
    clean = [r for r in rs if r["clean"]]
    return (f"{len(rs)} | {found}/{len(lab)} | {ci(found, len(lab))} | {n} | {ci(good, n)} | "
            f"{(sum(r['invalid'] for r in clean) / len(clean)) if clean else float('nan'):.2f} | "
            f"{(sum(r['n'] for r in clean) / len(clean)) if clean else float('nan'):.2f} | "
            f"{sum(r['tokens'] for r in rs) / len(rs):.0f}")


def tables(rows):
    out = ["\n| setup | cases | found/labelled | recall [95% CI] | findings | precision [95% CI] | invalid findings / clean PR | any findings / clean PR | mean input tokens / PR |\n|---|---|---|---|---|---|---|---|---|\n"]
    for s in "ABDE":
        out.append(f"| {s} | {agg([r for r in rows if r['setup'] == s])} |\n")
    out.append("\nExcluding OWASP files:\n\n| setup | cases | found/labelled | recall [95% CI] | findings | precision [95% CI] | invalid / clean PR | any / clean PR | mean input tokens / PR |\n|---|---|---|---|---|---|---|---|---|\n")
    for s in "ABDE":
        out.append(f"| {s} | {agg([r for r in rows if r['setup'] == s and r['source'] != 'owasp'])} |\n")
    out.append("\nBy PR size bucket (changed lines; this dataset is capped at 40 source lines, so only small/medium occur):\n\n| bucket | setup | cases | found/labelled | recall | findings | precision | invalid / clean PR | any / clean PR | mean input tokens |\n|---|---|---|---|---|---|---|---|---|---|\n")
    for b, _, _ in BUCKETS:
        for s in "ABDE":
            rs = [r for r in rows if r["setup"] == s and r["bucket"] == b]
            if rs:
                out.append(f"| {b} | {s} | {agg(rs)} |\n")
    rr = [r for r in rows if r["setup"] == "E"]
    out.append(f"\nE selected {sum(r['risky_hunks'] for r in rr)} of {sum(r['hunks'] for r in rr)} hunks; "
               f"{sum(1 for r in rr if r['risky_hunks'] == 0)}/{len(rr)} PRs had no risky hunk (no AI review beyond ai-confirm).\n")
    return "".join(out)


# ---------------- token cost by PR size on real commits ----------------
def sh(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kw)


def cmd_sizes(dirs, per_bucket=5):
    rows = []
    for repo in dirs:
        log = sh(["git", "log", "--no-merges", "--first-parent", "-n", "3000", "--format=@%H", "--shortstat", "--", "."] + EXCLUDE, repo).stdout
        commits, cur = [], None
        for l in log.split("\n"):
            if l.startswith("@"):
                cur = l[1:]
            elif cur and "changed" in l:
                n = sum(int(x) for x in re.findall(r"(\d+) (?:insertion|deletion)", l))
                commits.append((cur, n))
                cur = None
        by = collections.defaultdict(list)
        for sha, n in commits:
            by[bucket(n)].append((sha, n))
        wt = os.path.join("/tmp", "sizes-wt-" + os.path.basename(repo))
        for b, _, _ in BUCKETS:
            pick = by[b][:: max(1, len(by[b]) // per_bucket)][:per_bucket]
            for sha, n in pick:
                sh(["git", "worktree", "remove", "--force", wt], repo)
                if sh(["git", "worktree", "add", "--detach", "-f", wt, sha], repo).returncode != 0:
                    continue
                diff = sh(["git", "diff", "-U6", f"{sha}~1", sha, "--", "."] + EXCLUDE, wt).stdout
                n = changed_lines(diff)
                r = sh([CREV, "scan", ".", "--base", f"{sha}~1", "--ai", "off", "--vulndb", "off", "--format", "json", "--show-pending", "--quiet"], wt, timeout=900)
                try:
                    rep = json.loads(r.stdout)
                except Exception:
                    rep = {"findings": []}
                sh([CREV, "ai", "export", "."], wt)
                bp = os.path.join(wt, ".crev", "ai-handoff", "batches.jsonl")
                ai_in = os.path.getsize(bp) if os.path.exists(bp) else 0
                hs = parse_diff(diff)
                risky = risky_hunks(hs, crev_paths(rep))
                b_tok = (len(B_INSTR) + len(diff)) / 4
                e_tok = ((len(E_INSTR) + sum(len("\n".join(h["text"])) for h in risky) + crev_text(rep)) / 4) if risky else 0
                rows.append({"repo": os.path.basename(repo), "sha": sha, "changed": n, "bucket": bucket(n), "files": len({h["path"] for h in hs}),
                             "hunks": len(hs), "risky": len(risky), "A": ai_in / 4, "B": b_tok, "D": b_tok + ai_in / 4 + crev_text(rep) / 4,
                             "E": e_tok + ai_in / 4, "findings": len(rep.get("findings") or [])})
                print(rows[-1], flush=True)
        sh(["git", "worktree", "remove", "--force", wt], repo)
    json.dump(rows, open(os.path.join(ROOT, "sizes.json"), "w"), indent=1)
    print(size_table(rows))


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else float("nan")


def size_table(rows):
    out = ["\n| bucket | PRs | median changed lines | A tokens (median / p90) | B tokens (median / p90) | D tokens (median / p90) | E tokens (median / p90) | E share of hunks |\n|---|---|---|---|---|---|---|---|\n"]
    for b, _, _ in BUCKETS:
        rs = [r for r in rows if r["bucket"] == b]
        if not rs:
            continue
        f = lambda k: f"{pct([r[k] for r in rs], .5):,.0f} / {pct([r[k] for r in rs], .9):,.0f}"
        share = sum(r["risky"] for r in rs) / max(1, sum(r["hunks"] for r in rs))
        out.append(f"| {b} | {len(rs)} | {pct([r['changed'] for r in rs], .5):,.0f} | {f('A')} | {f('B')} | {f('D')} | {f('E')} | {share:.0%} |\n")
    # tokens per changed line (B), for the batching estimate
    pts = [(r["changed"], r["B"]) for r in rows if r["changed"]]
    if pts:
        k = sorted(t / n for n, t in pts)
        med = k[len(k) // 2]
        out.append(f"\nB input ~= {med:.1f} tokens per changed line (median over {len(pts)} commits, -U6 context).")
        for lim in (32_000, 100_000, 200_000):
            out.append(f" {lim // 1000}k tokens ~= {lim / med:,.0f} changed lines.")
        out.append("\n")
    return "".join(out)


if __name__ == "__main__":
    if sys.argv[1] == "score":
        cmd_score()
    elif sys.argv[1] == "sizes":
        cmd_sizes(sys.argv[2:])
    elif sys.argv[1] == "sizetable":
        print(size_table(json.load(open(os.path.join(ROOT, "sizes.json")))))

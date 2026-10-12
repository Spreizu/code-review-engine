"""Mine benchmark cases from pinned OSS repos (tools/bench/cache, never committed).

  szz          bug-introducing commits: a later fix commit (message says fix/bug) deletes or changes
               lines; `git blame` on the fix's parent attributes them to the introducing commit; the case
               is the introducing commit, the labels are those lines (in the introducing commit's version).
  real-clean   commits >= 1 year old, not fixes, whose added lines all survive unchanged at HEAD.
Output: tools/bench/cases/mined.json (repo, pinned HEAD sha, commit, fix commit, labels).
"""
import json, os, re, subprocess, sys, collections, time

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "cache")


def fence_go_module(d):
    """Cloned Go repos under cache/ and work/ must not join the crev module (go mod tidy / go test ./...)."""
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "go.mod")
    if not os.path.exists(p):
        with open(p, "w") as fh:
            fh.write("// fence: keeps cloned repos out of the crev module\nmodule crevbench.invalid/fence\n")


fence_go_module(CACHE)
EXT = {"java": (".java",), "ts": (".ts", ".js", ".vue", ".mjs", ".tsx", ".jsx"), "python": (".py",),
       "go": (".go",), "php": (".php",), "kotlin": (".kt",)}
TESTY = re.compile(r"(^|/)(tests?|__tests__|testdata|spec|docs?|examples?|benchmarks?|fixtures?|playgrounds?|e2e|scripts?)/|_test\.go$|Test\.java$|Tests?\.kt$|\.(spec|test)\.|(^|/)test_[^/]*\.py$|\.d\.ts$|(^|/)conftest\.py$")
FIXMSG = re.compile(r"\b(fix(e[sd])?|bug|regression|incorrect|wrong|crash)\b", re.I)
NOTBUG = re.compile(r"\b(typo|docs?|readme|changelog|lint|ci|style|format|test(s|ing)?|deps?|bump|release|chore|spelling|comment|example|build|types?)\b", re.I)
MAX_INTRO = 40   # changed source lines in the introducing commit (keeps the review input small)

def git(repo, *a, check=True):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, errors="replace")
    if check and r.returncode:
        raise RuntimeError(f"git {a}: {r.stderr[:300]}")
    return r.stdout

def src(lang, path):
    return path.endswith(EXT[lang]) and not TESTY.search(path)

def numstat(repo, c):
    out = []
    for l in git(repo, "show", "--no-renames", "--format=", "--numstat", c).splitlines():
        p = l.split("\t")
        if len(p) == 3 and p[0] != "-":
            out.append((int(p[0]), int(p[1]), p[2]))
    return out

def deleted_ranges(repo, c, path):
    """old-side line ranges changed by commit c in path (from a -U0 diff)."""
    rs = []
    for l in git(repo, "show", "--format=", "-U0", c, "--", path).splitlines():
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+", l)
        if m:
            s, n = int(m.group(1)), int(m.group(2) or 1)
            if n > 0:
                rs.append((s, s + n - 1))
    return rs

def blame(repo, rev, path, lo, hi):
    out = git(repo, "blame", "--porcelain", "-L", f"{lo},{hi}", rev, "--", path, check=False)
    res, cur = [], None
    for l in out.splitlines():
        m = re.match(r"^([0-9a-f]{40}) (\d+) (\d+)", l)
        if m:
            cur = [m.group(1), int(m.group(2)), None]
            res.append(cur)
        elif l.startswith("filename ") and cur is not None:
            cur[2] = l[9:]
        elif l.startswith("boundary") and cur is not None:
            cur[0] = None
    # porcelain prints filename only on first occurrence of each commit
    fn = {}
    for c, _, f in res:
        if f:
            fn[c] = f
    return [(c, n, fn.get(c)) for c, n, _ in res if c]

def mine(lang, name, want_szz, want_clean, scan=2500):
    repo = os.path.join(CACHE, name)
    head = git(repo, "rev-parse", "HEAD").strip()
    log = git(repo, "log", "--no-merges", f"-n{scan}", "--format=%H%x09%ct%x09%s").splitlines()
    cases, seen = [], set()
    now = time.time()
    for line in log:
        if sum(1 for c in cases if c["source"] == "szz") >= want_szz:
            break
        h, ts, subj = line.split("\t", 2)
        if not FIXMSG.search(subj) or NOTBUG.search(subj):
            continue
        ns = numstat(repo, h)
        s = [x for x in ns if src(lang, x[2])]
        if len(s) != 1 or len(ns) > 4:  # one source file (tests/changelog may ride along)
            continue
        add, dele, path = s[0]
        if not (1 <= dele <= 8 and add + dele <= 30):
            continue
        votes = collections.Counter()
        lines = collections.defaultdict(set)
        for lo, hi in deleted_ranges(repo, h, path):
            for c, n, f in blame(repo, h + "^", path, lo, hi):
                votes[c] += 1
                lines[(c, f or path)].add(n)
        if not votes:
            continue
        intro = votes.most_common(1)[0][0]
        if intro in seen:
            continue
        ins = [x for x in numstat(repo, intro) if src(lang, x[2])]
        tot = sum(a + d for a, d, _ in ins)
        if not ins or tot > MAX_INTRO or tot < 2 or len(git(repo, "rev-list", "--parents", "-n1", intro).split()) != 2:
            continue
        labels = [{"path": f, "lines": sorted(ls)} for (c, f), ls in lines.items() if c == intro]
        if not any(l["path"] in [p for _, _, p in ins] for l in labels):
            continue
        seen.add(intro)
        cases.append({"source": "szz", "lang": lang, "repo": name, "head": head, "commit": intro,
                      "fix": h, "fix_subject": subj, "labels": labels,
                      "files": [p for _, _, p in ins]})
    # real-clean: older than a year, not a fix, all added source lines still blamed to it at HEAD
    for line in log:
        if sum(1 for c in cases if c["source"] == "real-clean") >= want_clean:
            break
        h, ts, subj = line.split("\t", 2)
        if now - int(ts) < 365 * 86400 or FIXMSG.search(subj) or NOTBUG.search(subj) or h in seen:
            continue
        ns = numstat(repo, h)
        s = [x for x in ns if src(lang, x[2])]
        tot = sum(a + d for a, d, _ in s)
        if not s or len(s) > 2 or not (6 <= tot <= MAX_INTRO) or len(ns) > 4:
            continue
        if len(git(repo, "rev-list", "--parents", "-n1", h).split()) != 2:
            continue
        ok = True
        for a, d, p in s:
            if a == 0:
                continue
            cnt = git(repo, "log", "--format=%H", f"{h}..HEAD", "--", p, check=False).split()
            # every later commit touching the file must not touch the added lines: check via blame at HEAD
            out = git(repo, "blame", "--porcelain", "HEAD", "--", p, check=False)
            survived = len(re.findall(rf"^{h} \d+ \d+", out, re.M))
            if survived < a:
                ok = False
        if ok:
            cases.append({"source": "real-clean", "lang": lang, "repo": name, "head": head, "commit": h,
                          "fix": None, "fix_subject": subj, "labels": [], "files": [p for _, _, p in s]})
    return cases

if __name__ == "__main__":
    plan = [l.split() for l in open(os.path.join(CACHE, "repos.txt")) if l.strip()]
    per_lang = collections.Counter(l for l, _ in plan)
    want_szz = {"java": 4, "ts": 4, "python": 4, "go": 4, "php": 4, "kotlin": 4}
    want_clean = 2
    out = []
    only = sys.argv[1:]
    for lang, r in plan:
        name = r.split("/")[1]
        if name == "ui" or (only and name not in only):
            pass
        if only and name not in only:
            continue
        n = per_lang[lang]
        ws = -(-want_szz[lang] // n)
        wc = -(-want_clean // n)
        try:
            cs = mine(lang, name, ws, wc)
        except Exception as e:
            print("ERR", name, e, file=sys.stderr)
            continue
        print(name, collections.Counter(c["source"] for c in cs), file=sys.stderr)
        out += cs
    os.makedirs(os.path.join(ROOT, "cases"), exist_ok=True)
    p = os.path.join(ROOT, "cases", "mined.json" if not only else "mined-" + "-".join(only) + ".json")
    json.dump(out, open(p, "w"), indent=1)
    print(len(out), "->", p)

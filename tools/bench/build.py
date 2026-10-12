"""Build benchmark cases (work dirs under tools/bench/work, never committed) and run crev on them.

  python tools/bench/build.py cases     mined.json + seeded + OWASP -> work/cases/<id>/ and cases/cases.json
  python tools/bench/build.py scan      crev on every case (3 runs: determinism + wall time) -> work/cases/<id>/crev-N.json
  python tools/bench/build.py prompts   reviewer inputs: work/review/batch-NN.md (diffs, for B and C) and
                                        work/review/batch-NN-crev.md (crev output + ai-confirm items, read after B)
"""
import json, os, random, re, shutil, subprocess, sys, time, hashlib, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(ROOT))
CACHE = os.path.join(ROOT, "cache")
WORK = os.path.join(ROOT, "work")


def fence_go_module(d):
    """Cloned Go repos under cache/ and work/ must not join the crev module (go mod tidy / go test ./...)."""
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "go.mod")
    if not os.path.exists(p):
        with open(p, "w") as fh:
            fh.write("// fence: keeps cloned repos out of the crev module\nmodule crevbench.invalid/fence\n")


for _d in (CACHE, WORK):
    fence_go_module(_d)
CASES = os.path.join(WORK, "cases")
BENCH = os.path.join(REPO, "tools/corpus/cache/bench")
CREV = os.environ.get("CREV", "/tmp/crev")
MANIFESTS = ["package.json", "go.mod", "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
             "settings.gradle.kts", "gradle/libs.versions.toml", "composer.json", "pyproject.toml", "setup.py",
             "setup.cfg", "requirements.txt", "gradle.properties"]
sys.path.insert(0, ROOT)
from mine import EXT, TESTY, git  # noqa: E402


def show(repo, rev, path):
    r = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def write_case(cid, meta, before, after, manifests):
    d = os.path.join(CASES, cid)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    meta = dict(meta, id=cid)
    json.dump(meta, open(os.path.join(d, "meta.json"), "w"), indent=1)
    rd = os.path.join(d, "repo")
    os.makedirs(rd)
    def put(files):
        for p, s in files.items():
            fp = os.path.join(rd, p)
            if s is None:
                if os.path.exists(fp):
                    os.remove(fp)
                continue
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp, "w").write(s)
    g = lambda *a: subprocess.run(["git", "-C", rd, *a], check=True, capture_output=True)
    g("init", "-q")
    put(manifests)
    put(before)
    open(os.path.join(rd, ".gitkeep"), "w").write("")
    g("add", "-A")
    g("-c", "user.name=b", "-c", "user.email=b@b", "commit", "-qm", "base")
    put(after)
    g("add", "-A")
    g("-c", "user.name=b", "-c", "user.email=b@b", "commit", "-qm", "change")
    diff = subprocess.run(["git", "-C", rd, "diff", "-U6", "HEAD~1", "HEAD", "--", ".", ":(exclude).gitkeep"],
                          capture_output=True, text=True).stdout
    open(os.path.join(d, "diff.patch"), "w").write(diff)
    return meta


def manifests_at(repo, rev):
    out = {}
    for m in MANIFESTS:
        s = show(repo, rev, m)
        if s is not None:
            out[m] = s
    return out


def mined_cases():
    out = []
    for c in json.load(open(os.path.join(ROOT, "cases", "mined.json"))):
        repo = os.path.join(CACHE, c["repo"])
        cid = f'{c["lang"]}-{c["source"]}-{c["repo"]}-{c["commit"][:8]}'
        before = {p: show(repo, c["commit"] + "^", p) for p in c["files"]}
        after = {p: show(repo, c["commit"], p) for p in c["files"]}
        meta = {k: c[k] for k in ("source", "lang", "repo", "head", "commit", "fix", "fix_subject", "labels")}
        out.append(write_case(cid, meta, before, after, manifests_at(repo, c["commit"])))
    return out


# ---------------- seeded ----------------
SEC = {
    "java": [("sqli", 'public java.sql.ResultSet findByName(java.sql.Connection conn, String name) throws java.sql.SQLException {\n    return conn.createStatement().executeQuery("SELECT * FROM users WHERE name = \'" + name + "\'");\n}'),
             ("cmdi", 'public Process runTool(String arg) throws java.io.IOException {\n    return Runtime.getRuntime().exec("tool " + arg);\n}')],
    "kotlin": [("cmdi", 'fun runTool(arg: String): Process =\n    Runtime.getRuntime().exec("tool $arg")'),
               ("weak-hash", 'fun hashPassword(password: String): ByteArray =\n    java.security.MessageDigest.getInstance("MD5").digest(password.toByteArray())')],
    "go": [("cmdi", 'func runTool(arg string) ([]byte, error) {\n\treturn exec.Command("sh", "-c", "tool "+arg).Output()\n}', "os/exec"),
           ("sqli", 'func findByName(db *sql.DB, name string) (*sql.Rows, error) {\n\treturn db.Query("SELECT * FROM users WHERE name = \'" + name + "\'")\n}', "database/sql")],
    "python": [("cmdi", 'def run_tool(arg):\n    import subprocess\n    return subprocess.run(f"tool {arg}", shell=True, capture_output=True)'),
               ("deser", 'def load_state(data):\n    import pickle\n    return pickle.loads(data)')],
    "php": [("sqli", 'public function findByName($db)\n{\n    return $db->query("SELECT * FROM users WHERE name = \'" . $_GET[\'name\'] . "\'");\n}'),
            ("deser", 'public function loadState()\n{\n    return unserialize($_COOKIE[\'state\']);\n}')],
    "ts": [("code-injection", 'export function evaluate(expr: string): unknown {\n  return eval(expr)\n}'),
           ("cmdi", 'export function runTool(arg: string): void {\n  require("child_process").exec(`tool ${arg}`)\n}')],
}
COMMENT = {"python": "#", "go": "//", "java": "//", "kotlin": "//", "php": "//", "ts": "//"}


def mutate_logic(lang, lines, op, rnd):
    """returns (new_lines, label_line_1based, description) or None"""
    idx = list(range(10, len(lines) - 5))
    rnd.shuffle(idx)
    for i in idx:
        l = lines[i]
        if re.search(r'["\'`]', l) or l.lstrip().startswith(("//", "#", "*")):
            continue
        if op == "invert":
            if re.match(r"\s*(if|elif|\} else if|else if|while)\b", l):
                for a, b in (("!==", "==="), ("===", "!=="), ("!=", "=="), ("==", "!="), (" is not None", " is None"), (" is None", " is not None")):
                    if a in l:
                        return lines[:i] + [l.replace(a, b, 1)] + lines[i + 1:], i + 1, f"inverted condition ({a} -> {b})"
        if op == "andor":
            if re.match(r"\s*(if|elif|\} else if|else if|return)\b", l):
                for a, b in (("&&", "||"), ("||", "&&"), (" and ", " or "), (" or ", " and ")):
                    if a in l:
                        return lines[:i] + [l.replace(a, b, 1)] + lines[i + 1:], i + 1, f"boolean operator swapped ({a.strip()} -> {b.strip()})"
        if op == "offbyone":
            m = re.search(r"(\w|\))\s<\s(\w)", l)
            if m and re.match(r"\s*(for|while|if)\b", l) and "<<" not in l:
                return lines[:i] + [l[:m.start()] + m.group(1) + " <= " + m.group(2) + l[m.end():]] + lines[i + 1:], i + 1, "off-by-one (< -> <=)"
            m = re.search(r"\brange\(([^()]+)\)", l)
            if lang == "python" and m and l.lstrip().startswith("for "):
                return lines[:i] + [l.replace(m.group(0), f"range({m.group(1)} + 1)", 1)] + lines[i + 1:], i + 1, "off-by-one (range + 1)"
        if op == "dropguard":
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if lang == "go" and re.match(r"\s*if err != nil \{\s*$", l) and re.match(r"\s*return\b", nxt) and lines[i + 2].strip() == "}":
                return lines[:i] + lines[i + 3:], i + 1, "removed error check"
            if lang == "python" and re.match(r"\s*if .*(is None|not \w+).*:\s*$", l) and re.match(r"\s*(return|raise)\b", nxt):
                return lines[:i] + lines[i + 2:], i + 1, "removed None/empty guard"
            if lang in ("java", "kotlin", "ts", "php") and re.match(r"\s*if \(.*(== null|=== null|!\$?\w+\)|== false|isEmpty\(\)|=== undefined).*\)\s*\{?\s*$", l) and re.match(r"\s*(return|throw)\b", nxt):
                end = i + 2 + (1 if l.rstrip().endswith("{") and lines[i + 2].strip() == "}" else 0)
                return lines[:i] + lines[end:], i + 1, "removed null/empty guard"
    return None


def insert_snippet(lang, src, snippet, imp):
    lines = src.split("\n")
    ind = "    "
    if lang in ("java", "php"):
        last = max(i for i, l in enumerate(lines) if l.strip() == "}")
        body = [(ind + s if s else s) for s in snippet.split("\n")]
        new = lines[:last] + [""] + body + lines[last:]
        start = last + 2
    else:
        while lines and lines[-1] == "":
            lines.pop()
        body = snippet.split("\n")
        new = lines + [""] + body + [""]
        start = len(lines) + 2
    if lang == "go" and imp and f'"{imp}"' not in src:
        for i, l in enumerate(new):
            if l.startswith("import ("):
                new.insert(i + 1, f'\t"{imp}"')
                start += 1
                break
            if l.startswith("import \""):
                new[i] = f'import (\n\t"{imp}"\n\t{l[7:]}\n)'
                start += 3
                break
    return "\n".join(new), list(range(start, start + len(body)))


def benign(lang, lines, rnd, avoid):
    """add an explanatory comment line above a declaration away from the mutation (benign hunk)."""
    decl = re.compile(r"\s*(public|private|protected|func |def |fun |function |export |class |static )")
    cands = [i for i, l in enumerate(lines) if decl.match(l) and all(abs(i - a) > 15 for a in avoid)]
    if not cands:
        return lines, None
    i = rnd.choice(cands)
    ind = re.match(r"\s*", lines[i]).group(0)
    return lines[:i] + [f"{ind}{COMMENT[lang]} NOTE: keep this in sync with the documentation."] + lines[i:], i + 1


def pick_files(lang, repo, n, rnd):
    files = [p for p in git(repo, "ls-files").split("\n") if p.endswith(EXT[lang]) and not p.endswith(".vue") and not TESTY.search(p)]
    files.sort()
    rnd.shuffle(files)
    out = []
    for p in files:
        s = show(repo, "HEAD", p)
        if s and 80 <= s.count("\n") <= 600:
            if lang == "java" and not re.search(r"^\}", s, re.M):
                continue
            if lang == "php" and "class " not in s:
                continue
            if lang == "ts" and not p.endswith(".ts"):
                continue
            out.append((p, s))
        if len(out) >= n:
            break
    return out


def seeded_cases():
    repos = {}
    for l in open(os.path.join(CACHE, "repos.txt")):
        if l.strip():
            lang, r = l.split()
            repos.setdefault(lang, []).append(r.split("/")[1])
    out = []
    for lang, names in sorted(repos.items()):
        names = [n for n in names if n != "ui"]
        rnd = random.Random("seed-" + lang)
        plan = [("logic", "invert"), ("logic", "andor"), ("logic", "offbyone"), ("logic", "dropguard"), ("sec", 0), ("sec", 1), ("clean", None)]
        pool = []
        for n in names:
            pool += [(n, p, s) for p, s in pick_files(lang, os.path.join(CACHE, n), 30, rnd)]
        rnd.shuffle(pool)
        used = set()
        for kind, op in plan:
            for name, p, s in pool:
                if (name, p) in used:
                    continue
                lines = s.split("\n")
                repo = os.path.join(CACHE, name)
                labels, desc = [], ""
                if kind == "logic":
                    r = mutate_logic(lang, lines, op, rnd)
                    if not r:
                        continue
                    lines, ln, desc = r
                    labels = [ln]
                elif kind == "sec":
                    tag, snip, *imp = SEC[lang][op]
                    if lang == "kotlin" and not re.search(r"^(fun|class|object|internal|public)", s, re.M):
                        continue
                    news, labels = insert_snippet(lang, s, snip, imp[0] if imp else None)
                    lines, desc = news.split("\n"), "injected " + tag
                lines, bl = benign(lang, lines, rnd, [x - 1 for x in labels])
                if bl is None:
                    continue
                labels = [x + 1 if x >= bl else x for x in labels]
                used.add((name, p))
                cid = f"{lang}-seeded{'-clean' if kind == 'clean' else ''}-{name}-{op if kind != 'sec' else SEC[lang][op][0]}"
                head = git(repo, "rev-parse", "HEAD").strip()
                meta = {"source": "seeded-clean" if kind == "clean" else "seeded", "lang": lang, "repo": name, "head": head,
                        "commit": head, "fix": None, "fix_subject": desc,
                        "labels": [{"path": p, "lines": labels}] if labels else []}
                out.append(write_case(cid, meta, {p: s}, {p: "\n".join(lines)}, manifests_at(repo, "HEAD")))
                break
    return out


def owasp_cases(n_per=6):
    out = []
    rnd = random.Random("owasp")
    for lang, d, csv, sub, ext in (("java", "BenchmarkJava", "expectedresults-1.2.csv", "src/main/java/org/owasp/benchmark/testcode", ".java"),
                                   ("python", "BenchmarkPython", "expectedresults-0.1.csv", "testcode", ".py")):
        rows = [l.strip().split(",") for l in open(os.path.join(BENCH, d, csv)) if l[0] != "#"]
        rows = [r for r in rows if r[1] in ("sqli", "cmdi", "pathtraver", "xss")]
        rnd.shuffle(rows)
        for want in ("true", "false"):
            picked = [r for r in rows if r[2] == want][: n_per // 2]
            for name, cat, real, cwe in picked:
                fp = glob.glob(os.path.join(BENCH, d, sub, name + ext))
                if not fp:
                    continue
                s = open(fp[0]).read()
                rel = f"{sub}/{name}{ext}"
                n = s.count("\n") + 1
                meta = {"source": "owasp", "lang": lang, "repo": d, "head": None, "commit": None, "fix": None,
                        "fix_subject": f"{cat} cwe-{cwe} real={real}", "owasp": {"category": cat, "real": real == "true", "cwe": int(cwe)},
                        "labels": [{"path": rel, "lines": list(range(1, n + 1))}] if real == "true" else []}
                mf = {"requirements.txt": open(os.path.join(BENCH, d, "requirements.txt")).read()} if lang == "python" else {}
                out.append(write_case(f"{lang}-owasp-{name}", meta, {}, {rel: s}, mf))
    return out


def cmd_cases():
    shutil.rmtree(CASES, ignore_errors=True)
    os.makedirs(CASES)
    allc = mined_cases() + seeded_cases() + owasp_cases()
    for c in allc:
        c["diff_lines"] = open(os.path.join(CASES, c["id"], "diff.patch")).read().count("\n")
    json.dump(allc, open(os.path.join(ROOT, "cases", "cases.json"), "w"), indent=1)
    import collections
    print(collections.Counter((c["lang"], c["source"]) for c in allc))
    print(len(allc), "cases")


def cmd_scan(runs=3):
    allc = json.load(open(os.path.join(ROOT, "cases", "cases.json")))
    for c in allc:
        d = os.path.join(CASES, c["id"])
        for k in range(1, runs + 1):
            t = time.time()
            r = subprocess.run([CREV, "scan", "repo", "--base", "HEAD~1", "--ai", "off", "--vulndb", "off", "--format", "json",
                                "--show-pending", "--quiet"], cwd=d, capture_output=True, text=True)
            el = time.time() - t
            try:
                rep = json.loads(r.stdout)
            except Exception:
                print("scan failed", c["id"], r.stderr[:300])
                rep = {"findings": []}
            rep["_elapsed"] = el
            json.dump(rep, open(os.path.join(d, f"crev-{k}.json"), "w"), indent=1)
        print(c["id"], len(rep.get("findings") or []), f"{el:.2f}s")


if __name__ == "__main__":
    {"cases": cmd_cases, "scan": cmd_scan}[sys.argv[1]]()

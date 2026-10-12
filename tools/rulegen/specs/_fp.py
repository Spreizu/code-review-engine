"""False-positive fixes for rules whose spec helpers do not take fp/precision/filters keywords.

Each entry is applied by rulegen.amend() after the pack spec is loaded. Prefer fixing the query
in the spec itself; use this for regression examples (fp), precision tiers, requires_config and
extra guards on helper-built rules. Every fp entry is a former false positive (self-scan, corpus
run, linter fixture or `crev feedback fp`) and is run by rulecheck as a must-not-match example.
"""
AMEND = {
    "JS-NO-SCRIPT-URL": {"rule_version": 2},
    "PY-BIND-ALL-INTERFACES": {"rule_version": 2},
    "PY-HARDCODED-TMP": {"rule_version": 2},
    "KT-DEPRECATED-NO-REPLACEWITH": {"rule_version": 2},
    "JAVA-SEC-CMD-001": {"rule_version": 2},
    "TAINT-PY-XSS": {"rule_version": 2},
    "TAINT-GO-PATH": {"rule_version": 2},
    "KT-WEAK-HASH": {"rule_version": 2, "fp": ["val md = MessageDigest.getInstance(\"SHA-256\")\nval other = Hashing.getInstance(\"MD5\")\n"]},
    # self-scan: inner loop walks a value or index lookup derived from the outer loop variable
    # (grouped-by-key maps), which is not an n*m cross product.
    "SIMP-GO-IDX-NESTED-LOOP-NO-LIMIT-NOTE": {"fp": [
        {"note": "inner loop over the outer loop's value (map of slices)",
         "code": "package p\n\nfunc newest(byBranch map[string][]int, keep map[string]int) int {\n\tn := 0\n\tfor b, rs := range byBranch {\n\t\tfor i, r := range rs {\n\t\t\tif r == keep[b] {\n\t\t\t\tn += i\n\t\t\t}\n\t\t}\n\t}\n\treturn n\n}\n"},
        {"note": "inner loop over an index lookup keyed by the outer element",
         "code": "package p\n\ntype sym struct{ hash string }\n\nfunc dups(syms []*sym, byHash map[string][]*sym) int {\n\tn := 0\n\tfor _, s := range syms {\n\t\tfor _, o := range byHash[s.hash] {\n\t\t\tif o != s {\n\t\t\t\tn++\n\t\t\t}\n\t\t}\n\t}\n\treturn n\n}\n"},
    ]},
    # self-scan: a limit: note wrapped over several // lines was read as its first line only.
    "SIMP-GO-IDX-LIMIT-NOTE-INCOMPLETE": {"fp": [
        {"note": "limit note wrapped over two comment lines",
         "code": "package p\n\nimport \"sync\"\n\n// limit: one lock for the whole cache; fine up to ~1000 lookups/s,\n// switch to a sync.Map or per-key shards beyond that.\nvar mu sync.Mutex\n"},
    ]},
}

# Fixture triage (linter suites): a local binding shadows the global the rule is about.
def _shadow(name):
    return (rf"file.lacks_re:(?m)\b(?:var|let|const|function|class|import)\s+(?:\{{[^}}]*\b)?{name}\b"
            rf"|\bfunction\b[^(]*\([^)]*\b{name}\b[^)]*\)|\([^()]*\b{name}\b[^()]*\)\s*=>|\b{name}\s*=>")

AMEND.update({
    "JS-NO-CONSOLE": {"filters_add": [_shadow("console")],
                      "fp": [{"note": "local console binding", "code": "const console = createLogger()\nconsole.log('ready')\n"}]},
    "JS-USE-ISNAN": {"filters_add": [_shadow("NaN")],
                     "fp": [{"note": "local NaN binding", "code": "function check(x, NaN) {\n  return x === NaN\n}\n"}]},
    "JS-PREFER-NUMERIC-LITERALS": {"filters_add": [_shadow("parseInt")],
                                   "fp": [{"note": "parseInt parameter", "code": "function read(parseInt) {\n  return parseInt('101', 2)\n}\n"}]},
    "TS-NO-REQUIRE-IMPORTS": {"filters_add": [_shadow("require")],
                              "fp": [{"note": "createRequire binding", "code": "import { createRequire } from 'node:module'\nconst require = createRequire(import.meta.url)\nconst cfg = require('./cfg.json')\n"}]},
    "TS-NO-UNSAFE-FUNCTION-TYPE": {"filters_add": [r"file.lacks_re:\b(?:type|interface|class)\s+Function\b"],
                                   "fp": [{"note": "local Function type", "code": "type Function = () => void\nlet cb: Function\n"}]},
    "JS-DEFAULT-CASE": {"filters_add": [r"node.has_re:\bcase\b"],
                        "fp": [{"note": "empty switch", "code": "switch (mode) {}\n"}]},
    "JS-GUARD-FOR-IN": {"filters_add": [r"node.lacks_re:\)\s*\{\s*\}\s*$"],
                        "fp": [{"note": "empty body", "code": "for (const k in obj) {}\n"}]},
})

# Corpus run 2026-10-10 (tools/corpus, label after): sampled high-volume rules.
AMEND.update({
    "GO-MOD-SLICESCONTAINS": {"fp": [
        {"note": "self-scan 2026-10-10: existence probe (os.Stat in an if initializer, returns a pair) is not a membership test",
         "code": 'func find(paths []string) (string, bool) {\n\tfor _, p := range paths {\n\t\tif _, err := os.Stat(p); err == nil {\n\t\t\treturn p, true\n\t\t}\n\t}\n\treturn "", false\n}\n'},
        {"note": "comparison that does not involve the loop variable",
         "code": 'func any(xs []int, a, b int) bool {\n\tfor _, x := range xs {\n\t\tif a == b {\n\t\t\treturn true\n\t\t}\n\t\t_ = x\n\t}\n\treturn false\n}\n'}]},
    "JSON-NON-ISO-DATE": {"fp": [
        {"note": "semver dependency versions (21.2.12) matched the dotted date form",
         "code": '{"dependencies": {"@angular/common": "21.2.12", "vue": "3.5.13", "mocha": "9.2.2"}}'}]},
    "TF-LIST-MAP-FUNCTIONS": {"filters_add": [r"ancestor.lacks_re:attribute:^type\s*="],
        "fp": [{"note": "list(string)/map(string) are type constraints in variable blocks, not the removed functions",
                "code": 'variable "tags" {\n  type    = map(string)\n  default = {}\n}\n\nvariable "subnets" {\n  type = object({\n    cidrs = list(string)\n  })\n}\n'}]},
    "JS-NO-PROMISE-EXECUTOR-RETURN": {
        "filters_add": [r"node.lacks_re:(?s)=>\s*\(?\s*(?:setTimeout|setImmediate|queueMicrotask|process\.nextTick|requestAnimationFrame)\s*\("],
        "fp": [{"note": "sleep helper: the timer id returned by an expression-bodied executor is ignored and harmless",
                "code": "const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))\n"}]},
    "TS-NO-EMPTY-OBJECT-TYPE": {
        "filters_add": [r"ancestor.lacks_re:ambient_declaration|module:^(?:declare\s+)?(?:module|global)\b"],
        "fp": [{"note": "module augmentation: an empty interface extending another merges declarations",
                "code": "declare module 'vitest' {\n  interface Assertion<T = any> extends CustomMatchers<T> {}\n}\n"}]},
})

# Pattern rules for a dangerous API whose argument taint-lite can follow: drop the match when the
# call's arguments are provably not derived from the enclosing function's untrusted input
# (OWASP Benchmark negatives: request read, then the value replaced by a constant / guarded).
_TC = {'GO-EXEC-SHELL': 'cmdi', 'GO-SQL-STRING-BUILD': 'sqli', 'JAVA-SEC-CMD-001': 'cmdi', 'JAVA-SEC-SQL-PREP-CONCAT-002': 'sqli', 'JAVA-SEC-SQLI-001': 'sqli', 'JAVA-SEC-SQLI-FORMAT-002': 'sqli', 'JS-NODE-CHILD-EXEC-INJECTION-001': 'cmdi', 'KT-RUNTIME-EXEC-TEMPLATE': 'cmdi', 'KT-SQL-TEMPLATE': 'sqli', 'PHP-EVAL': 'code', 'PHP-OPEN-REDIRECT': 'redirect', 'PHP-SHELL-INJECTION': 'cmdi', 'PHP-SQL-INJECTION': 'sqli', 'PHP-XSS-ECHO-INPUT': 'xss', 'PY-EVAL': 'code', 'PY-OS-SYSTEM': 'cmdi', 'PY-SQL-STRING-FORMAT': 'sqli', 'PY-SUBPROCESS-SHELL': 'cmdi'}
_TC_FP = {
    "PY-EVAL": {"note": "OWASP Benchmark Python codeinj: value overwritten by a constant before eval", "code": "from flask import Flask, request\napp = Flask(__name__)\n\n@app.post('/c')\ndef c():\n    param = request.form.get('p', '')\n    m = {}\n    m['a'] = \"'ok'\"\n    m['b'] = param\n    bar = m['a']\n    return str(eval(bar))\n"},
    "PY-SUBPROCESS-SHELL": {"note": "OWASP Benchmark Python cmdi 00350: map lookup of a constant key", "code": "import subprocess\nfrom flask import Flask, request\napp = Flask(__name__)\n\n@app.post('/c')\ndef c():\n    param = request.form.get('p', '')\n    m = {}\n    m['keyA'] = 'a-Value'\n    m['keyB'] = param\n    bar = m['keyA']\n    proc = subprocess.run(f'echo {bar}', shell=True, capture_output=True)\n    return proc.stdout\n"},
    "JAVA-SEC-CMD-001": {"note": "OWASP Benchmark Java cmdi: concatenated value is constant on every path", "code": "import javax.servlet.http.*;\nclass C {\n  void p(HttpServletRequest request) throws Exception {\n    String param = request.getParameter(\"p\");\n    String bar = \"safe!\";\n    Runtime.getRuntime().exec(\"echo \" + bar);\n  }\n}\n"},
}
for _id, _cls in _TC.items():
    _a = AMEND.setdefault(_id, {})
    _a["filters_add"] = list(_a.get("filters_add", [])) + ["taint.clean:" + _cls]
    _a["rule_version"] = max(_a.get("rule_version", 1) + 1, 2)
    if _id in _TC_FP:
        _a["fp"] = list(_a.get("fp", [])) + [_TC_FP[_id]]

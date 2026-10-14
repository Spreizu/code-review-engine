"""Maintainability and reliability rules shared by the general-purpose languages (Java, JS/TS,
Python, Go, Kotlin, PHP): complexity metrics with configurable thresholds, duplicated branches,
dead code, empty blocks, boolean simplification, unused declarations, and small bug patterns.

Sources are the languages' own references and the official docs of the linters that check the
same thing (Checkstyle, ESLint, ruff, staticcheck/golangci-lint, detekt, PHPMD). Titles and
messages are crev's own wording. Sonar keys appear only as `sonar:<repo>:<key>` xrefs so the
coverage report can count them; no Sonar text or test is used.

Thresholds are rule params: the default applies unless the project's linter config sets its own
limit (projcfg `from:` keys), so crev reports the same functions the team's linter would.
Opinionated rules (naming, magic numbers, return counts, long functions, cyclomatic complexity)
carry the `opt-in` tag: optin.py turns them off unless the project's linter enables one of the
equivalents."""
import re
from specs._common import Pack
from specs._lint import desc

LANGS = {
    "java": ("JAVA-MAINT", "Java 21", {"java": "*"}),
    "javascript": ("JS-MAINT", "ECMAScript 2025", {"javascript": "*"}),
    "python": ("PY-MAINT", "Python 3.14", {"python": "*"}),
    "go": ("GO-MAINT", "Go 1.25", {"go": "*"}),
    "kotlin": ("KT-MAINT", "Kotlin 2.2", {"kotlin": "*"}),
    "php": ("PHP-MAINT", "PHP 8.4", {"php": "*"}),
}
P = {l: Pack(p, l, v, a) for l, (p, v, a) in LANGS.items()}
SONAR_REPO = {"java": ["java"], "javascript": ["javascript", "typescript"], "python": ["python"], "go": ["go"],
              "kotlin": ["kotlin"], "php": ["php"]}

# ---- documentation -------------------------------------------------------------------------
CS = "https://checkstyle.org/checks/{}.html"
RUFF = "https://docs.astral.sh/ruff/rules/{}/"
DETEKT = "https://detekt.dev/docs/rules/{}"
PHPMD = "https://phpmd.org/rules/{}.html"
GOLANGCI = "https://golangci-lint.run/docs/linters/"
STATICCHECK = "https://staticcheck.dev/docs/checks/"
JLS14 = "https://docs.oracle.com/javase/specs/jls/se21/html/jls-14.html"
PYCOMPOUND = "https://docs.python.org/3/reference/compound_stmts.html"
PYSIMPLE = "https://docs.python.org/3/reference/simple_stmts.html"
GOSPEC = "https://go.dev/ref/spec"
PHPSWITCH = "https://www.php.net/manual/en/control-structures.switch.php"


def es(name):
    return ("https://eslint.org/docs/latest/rules/" + name, desc("eslint", name), "ESLint rule " + name)


def cs(path, needle, name):
    return (CS.format(path), needle, "Checkstyle " + name)


def rf(name, needle, code):
    return (RUFF.format(name), needle, f"ruff {code} ({name})")


def dk(page, needle, name):
    return (DETEKT.format(page), needle, "detekt " + name)


def md(page, needle, name):
    return (PHPMD.format(page), needle, "PHPMD " + name)


def gl(needle, name):
    return (GOLANGCI, needle, "golangci-lint linter " + name)


REVIVE = "https://raw.githubusercontent.com/mgechev/revive/master/RULES_DESCRIPTIONS.md"


def rv(needle, name):
    return (REVIVE, needle, "revive rule " + name)


MDN = "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/"
PHPM = "https://www.php.net/manual/en/"


def sc(needle, code):
    return (STATICCHECK, needle, "staticcheck " + code)


# ---- example builder -----------------------------------------------------------------------
# A tiny neutral syntax rendered per language: statements are strings ("g()", "return 1"),
# blocks are ("if", cond, body) / ("ifelse", cond, then, else) / ("for", body).
VARS = re.compile(r"\b([a-h])\b")


def _expr(lang, e):
    if lang == "python":
        e = e.replace("&&", "and").replace("||", "or").replace("!", "not ")
    if lang == "php":
        e = VARS.sub(r"$\1", e)
    return e


def _stmt(lang, s):
    s = _expr(lang, s)
    return s if lang in ("python", "go", "kotlin") else s + ";"


def _render(lang, nodes, d, out):
    ind = ("\t" if lang == "go" else "    ") * d
    for n in nodes:
        if isinstance(n, str):
            out.append(ind + _stmt(lang, n))
            continue
        kind = n[0]
        if kind in ("if", "ifelse"):
            c = _expr(lang, n[1])
            if lang == "python":
                out.append(f"{ind}if {c}:")
            elif lang == "go":
                out.append(f"{ind}if {c} {{")
            else:
                out.append(f"{ind}if ({c}) {{")
            _render(lang, n[2], d + 1, out)
            if kind == "ifelse":
                out.append(ind + ("else:" if lang == "python" else "} else {"))
                _render(lang, n[3], d + 1, out)
            if lang != "python":
                out.append(ind + "}")
        elif kind == "chain":
            for i, (c, body) in enumerate(n[1]):
                c = _expr(lang, c)
                if lang == "python":
                    out.append(f"{ind}{'if' if i == 0 else 'elif'} {c}:")
                else:
                    kw = "if" if i == 0 else {"php": "} elseif", "python": ""}.get(lang, "} else if")
                    out.append(f"{ind}{kw} {c} {{" if lang == "go" else f"{ind}{kw} ({c}) {{")
                _render(lang, body, d + 1, out)
            if n[2] is not None:
                out.append(ind + ("else:" if lang == "python" else "} else {"))
                _render(lang, n[2], d + 1, out)
            if lang != "python":
                out.append(ind + "}")
        elif kind == "for":
            out.append(ind + {"python": "for x in xs:", "go": "for _, x := range xs {", "kotlin": "for (x in xs) {",
                              "php": "foreach ($xs as $x) {", "java": "for (int x : xs) {", "javascript": "for (const x of xs) {"}[lang])
            _render(lang, n[1], d + 1, out)
            if lang != "python":
                out.append(ind + "}")


TYPES = {"boolean": {"java": "boolean", "go": "bool", "kotlin": "Boolean"}, "int": {"java": "int", "go": "int", "kotlin": "Int"}}


def fn(lang, body, params="abcde", name="f", ret=True, typ="boolean"):
    """Function `name` with params `params` (all of type `typ`) and the neutral `body`."""
    ps = list(params)
    T = TYPES[typ]
    sig = {
        "java": "int %s(%s)" % (name, ", ".join(T["java"] + " " + p for p in ps)),
        "javascript": "function %s(%s)" % (name, ", ".join(ps)),
        "python": "def %s(%s):" % (name, ", ".join(ps)),
        "go": "func %s(%s) int" % (name, (", ".join(ps) + " " + T["go"]) if ps else ""),
        "kotlin": "fun %s(%s): Int" % (name, ", ".join(p + ": " + T["kotlin"] for p in ps)),
        "php": "function %s(%s)" % (name, ", ".join("$" + p for p in ps)),
    }[lang]
    if ret:
        body = list(body) + ["return 0"]
    out = []
    base = 1 if lang == "java" else 0
    if lang == "java":
        out.append("class A {")
    out.append(("    " * base) + sig + ("" if lang == "python" else " {"))
    _render(lang, body, base + 1, out)
    if lang != "python":
        out.append(("    " * base) + "}")
    if lang == "java":
        out.append("}")
    pre = {"go": "package p\n\n", "php": "<?php\n"}.get(lang, "")
    return pre + "\n".join(out) + "\n"


def nested(depth, leaf="g()"):
    node = [leaf]
    for i in reversed(range(depth)):
        node = [("if", "abcdefgh"[i], node)]
    return node


ALL = list(LANGS)
NO_DEFAULT = object()


def sonar(lang, *keys):
    # "repo:Sxxx" names one Sonar repository (e.g. godre, pythonbugs); a bare key expands to the language's repos
    return [f"sonar:{k}" if ":" in k else f"sonar:{repo}:{k}" for k in keys for repo in ([None] if ":" in k else SONAR_REPO[lang])]


def add(lang, id, title, src, query, bad, good, msg, *, keys=(), eq=(), tags=None, optin=False, rlang=None, **kw):
    if rlang:
        kw["lang"] = rlang
    url, needle, docname = src
    t = list(tags or [])
    if optin:
        t.append("opt-in")
    kw.setdefault("cat", "maintainability")
    kw.setdefault("kind", "best-practice")
    return P[lang](id, title, url, needle, query, bad, good, msg, doc=docname, xref=list(eq) + sonar(lang, *keys),
                   tags=t or None, **kw)


# ---- complexity metrics ----------------------------------------------------------------------
FUNC = {
    "java": "[(method_declaration body: (block)) (constructor_declaration)] @match",
    "javascript": "[(function_declaration) (function_expression) (arrow_function) (method_definition) (generator_function_declaration)] @match",
    "python": "(function_definition) @match",
    "go": "[(function_declaration body: (block)) (method_declaration body: (block)) (func_literal)] @match",
    "kotlin": "(function_declaration (function_body)) @match",
    "php": "[(function_definition) (method_declaration body: (compound_statement))] @match",
}
FLAT = [("if", "a", ["g()"]), ("if", "b", ["h()"]), ("if", "c && d", ["k()"])]


def metric(id, title, metric_name, default, docs, msg, bad_body, good_body, *, keys=None, eq=None, frm=None, langs=ALL,
           optin=False, sev="minor", filters=None, query=None, params="abcde", fp=None, cat="maintainability"):
    for lang in langs:
        q = (query or FUNC)[lang]
        fl = [f"metric.gt:{metric_name}:${{max}}"] + list((filters or {}).get(lang, []))
        dflt = default.get(lang, default["*"]) if isinstance(default, dict) else default
        add(lang, id, title, docs[lang], q, fn(lang, bad_body, params), fn(lang, good_body, params[:5]), msg,
            keys=(keys or {}).get(lang, ()), eq=(eq or {}).get(lang, ()), optin=optin, sev=sev, filters=fl,
            params={"max": {"default": dflt, "from": (frm or {}).get(lang, [])}}, match_kind="metric", cat=cat,
            fp=(fp or {}).get(lang))


COG_BAD = nested(5, "g()") + [("if", "a && b", ["h()"])]
metric("COGNITIVE-COMPLEXITY", "Function is hard to follow (cognitive complexity over the limit)", "cognitive", 15, {
    "java": ("https://pmd.github.io/pmd/pmd_rules_java_design.html", "Cognitive complexity is a measure of how difficult it is for humans to read and understand a method", "PMD CognitiveComplexity"),
    "javascript": es("complexity"),
    "python": rf("complex-structure", "Checks for functions with a high McCabe complexity", "C901"),
    "go": gl("Computes and checks the cognitive complexity of functions", "gocognit"),
    "kotlin": dk("complexity", "Complex methods are hard to understand and read", "CognitiveComplexMethod"),
    "php": md("codesize", "Complexity is determined by the number of decision points", "CyclomaticComplexity"),
}, "Cognitive complexity ${value} is above the limit of ${max}: every branch adds a point and nesting adds more, so "
   "split the function or flatten it with early returns.", COG_BAD, FLAT,
    keys={l: ["S3776"] for l in ALL},
    eq={"java": ["pmd:CognitiveComplexity"], "go": ["gocognit:gocognit", "revive:cognitive-complexity"], "kotlin": ["detekt:CognitiveComplexMethod"]},
    frm={"go": ["gocognit:*.min-complexity"], "kotlin": ["detekt:CognitiveComplexMethod.threshold"]})

metric("CYCLOMATIC-COMPLEXITY", "Function has too many independent paths (cyclomatic complexity)", "cyclomatic", 10, {
    "java": cs("metrics/cyclomaticcomplexity", "Checks cyclomatic complexity against a specified limit", "CyclomaticComplexity"),
    "javascript": es("complexity"),
    "python": rf("complex-structure", "Checks for functions with a high McCabe complexity", "C901"),
    "go": gl("cyclomatic complexity of functions", "gocyclo"),
    "kotlin": dk("complexity", "Complex methods are hard to understand and read", "CyclomaticComplexMethod"),
    "php": md("codesize", "Complexity is determined by the number of decision points", "CyclomaticComplexity"),
}, "Cyclomatic complexity ${value} is above the limit of ${max}; each path needs its own test, so split the function.",
    nested(3) + [("if", "a || b", ["h()"]), ("if", "c && d", ["k()"]), ("for", [("if", "e", ["g()"])]), ("if", "a && e", ["h()"])], FLAT,
    eq={"java": ["checkstyle:CyclomaticComplexity"], "javascript": ["eslint:complexity"], "python": ["ruff:C901"],
        "go": ["gocyclo:gocyclo", "cyclop:cyclop"], "kotlin": ["detekt:CyclomaticComplexMethod"], "php": ["phpmd:CyclomaticComplexity"]},
    keys={"python": ["S1541"], "php": ["S1541"], "go": ["S1541"]},
    frm={"java": ["checkstyle:CyclomaticComplexity.max"], "javascript": ["eslint:complexity.max", "eslint:complexity.value"],
         "python": ["ruff:C901.max"], "go": ["gocyclo:*.min-complexity", "cyclop:*.max-complexity"],
         "kotlin": ["detekt:CyclomaticComplexMethod.threshold"], "php": ["phpmd:CyclomaticComplexity.reportLevel"]},
    optin=True)

PARAM_FUNC = dict(FUNC)
PARAM_FUNC["java"] = "(method_declaration body: (block)) @match"
PARAM_FUNC["php"] = "[(function_definition) (method_declaration name: (name) @n body: (compound_statement) (#not-eq? @n \"__construct\"))] @match"
PARAM_FUNC["python"] = "(function_definition) @match"
metric("TOO-MANY-PARAMS", "Function takes too many parameters", "params", 7, {
    "java": cs("sizes/parameternumber", "Checks the number of parameters of a method or constructor", "ParameterNumber"),
    "python": rf("too-many-arguments", "Checks for function definitions that include too many arguments", "PLR0913"),
    "go": rv("Warns when a function receives more parameters than the maximum", "argument-limit"),
    "kotlin": dk("complexity", "Reports functions and constructors which have more parameters than a certain threshold", "LongParameterList"),
    "php": md("codesize", "Long parameter lists can indicate that a new object should be created", "ExcessiveParameterList"),
}, "${value} parameters (limit ${max}): group related ones into a value object or split the function.",
    ["g()"], ["g()"], langs=["java", "python", "go", "kotlin", "php"], params="abcdefgh", query=PARAM_FUNC,
    keys={l: ["S107"] for l in ALL},
    eq={"java": ["checkstyle:ParameterNumber"], "python": ["ruff:PLR0913", "pylint:too-many-arguments"],
        "kotlin": ["detekt:LongParameterList"], "php": ["phpmd:ExcessiveParameterList"]},
    frm={"java": ["checkstyle:ParameterNumber.max"], "python": ["ruff:PLR0913.max", "pylint:too-many-arguments.max"],
         "kotlin": ["detekt:LongParameterList.functionThreshold"], "php": ["phpmd:ExcessiveParameterList.minimum"]},
    filters={
        # the signature is imposed by a supertype or a framework (DI, handlers, JSON creators)
        "java": [r"node.lacks_re:^[^{]*@(Override|Inject|Autowired|Bean|JsonCreator|\w*Mapping|ParameterizedTest|Test)\b"],
        # decorators inject parameters (click/typer options, pytest fixtures, FastAPI endpoints)
        "python": ["parentkind.lacks_re:decorated_definition:."],
        "kotlin": [r"node.lacks_re:^[^{=]*(\boverride\b|@Composable\b|@Inject\b)"],
    })

# python: the ruff PLR1702 / pylint default (5); elsewhere eslint max-depth's 4
metric("DEEP-NESTING", "Control flow nested too deeply", "nesting", {"*": 4, "python": 5}, {
    "java": cs("coding/nestedifdepth", "Restricts nested if-else blocks to a specified depth", "NestedIfDepth"),
    "javascript": es("max-depth"),
    "python": rf("too-many-nested-blocks", "Checks for functions or methods with too many nested blocks", "PLR1702"),
    "go": rv("Warns if nesting level of control structures", "max-control-nesting"),
    "kotlin": dk("complexity", "This rule reports excessive nesting depth in functions", "NestedBlockDepth"),
    "php": (PHPM + "control-structures.if.php", "allows for conditional execution of code fragments", "PHP manual: if"),
}, "Blocks are nested ${value} levels deep (limit ${max}); invert conditions into early returns or extract the inner part.",
    nested(6), FLAT,
    keys={l: ["S134"] for l in ALL},
    eq={"javascript": ["eslint:max-depth"], "python": ["ruff:PLR1702", "pylint:too-many-nested-blocks"], "kotlin": ["detekt:NestedBlockDepth"]},
    frm={"javascript": ["eslint:max-depth.max", "eslint:max-depth.value"], "python": ["ruff:PLR1702.max", "pylint:too-many-nested-blocks.max"],
         "kotlin": ["detekt:NestedBlockDepth.threshold"]})

metric("TOO-MANY-RETURNS", "Function has many return statements", "returns", 5, {
    "java": cs("coding/returncount", "Restricts the number of return statements in methods", "ReturnCount"),
    "javascript": (MDN + "Statements/return", "The return statement ends function execution", "MDN: return"),
    "python": rf("too-many-return-statements", "Checks for functions or methods with too many return statements", "PLR0911"),
    "go": (GOSPEC, "terminates the execution of", "Go spec: Return statements"),
    "kotlin": dk("style", "Restrict the number of returns allowed in methods", "ReturnCount"),
    "php": (PHPM + "function.return.php", "returns program control to the calling module", "PHP manual: return"),
}, "${value} return statements (limit ${max}); fewer exits make the function easier to follow.",
    [("if", c, ["return 1"]) for c in "abcde"] + [("if", "a && b", ["return 2"])], [("if", "a", ["return 1"])],
    keys={l: ["S1142"] for l in ALL},
    eq={"java": ["checkstyle:ReturnCount"], "python": ["ruff:PLR0911", "pylint:too-many-return-statements"], "kotlin": ["detekt:ReturnCount"]},
    frm={"java": ["checkstyle:ReturnCount.max"], "python": ["ruff:PLR0911.max", "pylint:too-many-return-statements.max"],
         "kotlin": ["detekt:ReturnCount.max"]}, optin=True)

metric("LONG-FUNCTION", "Function body is very long", "lines", 80, {
    "java": cs("sizes/methodlength", "Checks for long methods and constructors", "MethodLength"),
    "javascript": es("max-lines-per-function"),
    "python": rf("too-many-statements", "Checks for functions or methods with too many statements", "PLR0915"),
    "go": gl("Checks for long functions", "funlen"),
    "kotlin": dk("complexity", "Complex methods are hard to understand and read", "LongMethod"),
    "php": md("codesize", "Violations of this rule usually indicate that the method is doing too much", "ExcessiveMethodLength"),
}, "The function has ${value} lines of code (limit ${max}); split it into smaller named steps.",
    ["g()"] * 85, ["g()"],
    keys={l: ["S138"] for l in ALL},
    eq={"java": ["checkstyle:MethodLength"], "javascript": ["eslint:max-lines-per-function"], "python": ["ruff:PLR0915"],
        "go": ["funlen:funlen"], "kotlin": ["detekt:LongMethod"], "php": ["phpmd:ExcessiveMethodLength"]},
    frm={"java": ["checkstyle:MethodLength.max"], "javascript": ["eslint:max-lines-per-function.max", "eslint:max-lines-per-function.value"],
         "go": ["funlen:*.lines"], "kotlin": ["detekt:LongMethod.threshold"], "php": ["phpmd:ExcessiveMethodLength.minimum"]}, optin=True)

LOGIC = {
    "java": "(binary_expression operator: [\"&&\" \"||\"]) @match",
    "javascript": "(binary_expression operator: [\"&&\" \"||\" \"??\"]) @match",
    "python": "(boolean_operator) @match",
    "go": "(binary_expression operator: [\"&&\" \"||\"]) @match",
    "kotlin": "(binary_expression) @match",
    "php": "(binary_expression operator: [\"&&\" \"||\" \"and\" \"or\"]) @match",
}
metric("COMPLEX-CONDITION", "Condition chains too many boolean operators", "boolops", 3, {
    "java": cs("metrics/booleanexpressioncomplexity", "Restricts the number of boolean operators", "BooleanExpressionComplexity"),
    "javascript": (MDN + "Operators/Logical_AND", "if and only if all the operands are true", "MDN: Logical AND"),
    "python": rf("too-many-boolean-expressions", "Checks for too many Boolean expressions in an if statement", "PLR0916"),
    "go": (GOSPEC, "Logical operators apply to boolean values", "Go spec: Logical operators"),
    "kotlin": dk("complexity", "Complex conditions make it hard to understand which cases lead to the condition being true or false", "ComplexCondition"),
    "php": (PHPM + "language.operators.logical.php", "Logical Operators", "PHP manual: Logical operators"),
}, "${value} boolean operators in one expression (limit ${max}); name the parts as variables or a helper.",
    [("if", "a && b || c && d && e", ["g()"])], [("if", "a && b", ["g()"])], query=LOGIC,
    keys={l: ["S1067"] for l in ALL},
    eq={"java": ["checkstyle:BooleanExpressionComplexity"], "python": ["ruff:PLR0916", "pylint:too-many-boolean-expressions"],
        "kotlin": ["detekt:ComplexCondition"]},
    frm={"java": ["checkstyle:BooleanExpressionComplexity.max"], "python": ["ruff:PLR0916.max", "pylint:too-many-boolean-expressions.max"]})


def multi(id, title, msg, spec, *, keys=(), cat="maintainability", kind="best-practice", sev="minor", optin=False, mode="deterministic",
          ai=None):
    """spec: {lang: dict(doc=, query=, bad=, good=, filters=, fp=, eq=, keys=, files=)}; keys apply to all languages."""
    for lang, s in spec.items():
        add(lang, id, title, s["doc"], s["query"], s["bad"], s["good"], s.get("msg", msg), keys=s.get("keys", keys), eq=s.get("eq", ()),
            filters=(s.get("filters") or []) + ([NO_SIDE_EFFECT, NOT_LITERAL] if s.get("filters_extra") else []) or None, fp=s.get("fp"), cat=s.get("cat", cat), kind=kind, sev=s.get("sev", sev), optin=optin,
            mode=s.get("mode", mode), ai=s.get("ai", ai), files=s.get("files"))


# operands that may differ between evaluations (calls, ++/--, await) or are plain numbers
NO_SIDE_EFFECT = r"cap.lacks_re:l:[(]|\+\+|--|\bawait\b|^[\d.]+$"


# ---- duplicated branches ----------------------------------------------------------------------
IFSW = {
    "java": "[(if_statement) (switch_expression)] @match",
    "javascript": "[(if_statement) (switch_statement)] @match",
    "python": "[(if_statement) (match_statement)] @match",
    "go": "[(if_statement) (expression_switch_statement) (type_switch_statement)] @match",
    "kotlin": "[(if_expression) (when_expression)] @match",
    "php": "[(if_statement) (switch_statement)] @match",
}
# an `else if` is measured as part of the chain that starts at the first `if`
NOT_ELSEIF = {"java": ["parentkind.lacks_re:if_statement:."], "javascript": ["parentkind.lacks_re:else_clause:."],
              "go": ["parentkind.lacks_re:if_statement:."], "kotlin": ["parentkind.lacks_re:if_expression:."]}


def ifchain(lang, bodies, else_body=None, cond="a == %d"):
    arms = [(cond % (i + 1) if "%d" in cond else cond, b) for i, b in enumerate(bodies)]
    return fn(lang, [("chain", arms, else_body)], "a", typ="int")


B1, B2 = ["log(1)", "count(2)"], ["other(3)", "count(4)"]
SW = {
    "java": "class A {\n    void f(int a) {\n        switch (a) {\n            case 1:\n                %s\n                break;\n            case 2:\n                %s\n                break;\n            default:\n                %s\n        }\n    }\n}\n",
    "javascript": "function f(a) {\n  switch (a) {\n    case 1:\n      %s\n      break;\n    case 2:\n      %s\n      break;\n    default:\n      %s\n  }\n}\n",
    "python": "def f(a):\n    match a:\n        case 1:\n            %s\n        case 2:\n            %s\n        case _:\n            %s\n",
    "go": "package p\n\nfunc f(a int) {\n\tswitch a {\n\tcase 1:\n\t\t%s\n\tcase 2:\n\t\t%s\n\tdefault:\n\t\t%s\n\t}\n}\n",
    "kotlin": "fun f(a: Int) {\n    when (a) {\n        1 -> {\n            %s\n        }\n        2 -> {\n            %s\n        }\n        else -> {\n            %s\n        }\n    }\n}\n",
    "php": "<?php\nfunction f($a) {\n    switch ($a) {\n        case 1:\n            %s\n            break;\n        case 2:\n            %s\n            break;\n        default:\n            %s\n    }\n}\n",
}


def sw(lang, *bodies):
    sep = {"java": "\n                ", "javascript": "\n      ", "python": "\n            ", "go": "\n\t\t", "kotlin": "\n            ",
           "php": "\n            "}[lang]
    return SW[lang] % tuple(sep.join(_stmt(lang, s) for s in b) for b in bodies)


BR_DOCS = {
    "java": (JLS14, "The switch statement transfers control", "JLS 14.11 The switch statement"),
    "javascript": es("no-dupe-else-if"),
    "python": rf("if-with-same-arms", "Checks for if branches with identical arm bodies", "SIM114"),
    "go": rv("chain with identical branches makes maintenance harder", "identical-ifelseif-branches"),
    "kotlin": dk("complexity", "Complex methods are hard to understand and read", "ComplexMethod"),
    "php": (PHPSWITCH, "similar to a series of IF statements", "PHP manual: switch"),
}
multi("DUPLICATE-BRANCH", "Two branches have the same code",
      "This branch repeats the code of an earlier branch of the same if/switch: merge the conditions, or fix the branch that was "
      "meant to differ.",
      {l: dict(doc=BR_DOCS[l], query=IFSW[l], filters=["branches.dup_body"] + NOT_ELSEIF.get(l, []),
               bad=ifchain(l, [B1, B2, B1]), good=ifchain(l, [B1, B2, ["log(5)", "count(6)"]]),
               fp=[sw(l, ["log(1)"], ["log(1)"], ["log(2)"])],
               eq={"python": ["ruff:SIM114"], "go": ["revive:identical-ifelseif-branches", "revive:identical-switch-branches"]}.get(l, ()))
       for l in ALL}, keys=["S1871"], mode="ai-confirm",
      ai="Do the two branches really do the same thing (same variables in scope, no intended difference)?")

# Regressions: char literals whose content is not a child token; identical calls after a smart cast.
KT_SAME_FP = {"kotlin": ["fun f(b: Boolean?) = when (b) {\n    true -> 'Y'\n    false -> 'N'\n    else -> ' '\n}\n",
                         "fun f(r: Any) = if (r is String) g(r) else g(r)\n"]}
multi("ALL-BRANCHES-SAME", "Every branch runs the same code",
      "All branches of this if/switch (including the else/default) do the same thing, so the condition has no effect: drop the "
      "condition or make the branches differ as intended.",
      {l: dict(doc=BR_DOCS[l], query=IFSW[l], filters=["branches.all_same"] + NOT_ELSEIF.get(l, []),
               bad=ifchain(l, [["save(1)"]], ["save(1)"]), good=ifchain(l, [["save(1)"]], ["save(2)"]),
               fp=[ifchain(l, [["save(1)"], ["save(1)"]])] + KT_SAME_FP.get(l, []),
               eq={"go": ["revive:identical-branches"]}.get(l, ()), cat="correctness")
       for l in ALL}, keys=["S3923"], kind="anti-pattern", sev="major")

DC_DOCS = dict(BR_DOCS)
DC_DOCS["go"] = rv("chain with identical conditions can lead to unreachable code", "identical-ifelseif-conditions")
DC_DOCS["python"] = (PYCOMPOUND, "The if statement is used for conditional execution", "Python reference: The if statement")
DC_DOCS["kotlin"] = ("https://kotlinlang.org/docs/control-flow.html", "If expression", "Kotlin docs: Conditions and loops")
DC_DOCS["java"] = (JLS14, "It is a compile-time error if a statement cannot be executed", "JLS 14.22 Unreachable statements")
DC_DOCS["php"] = (PHPM + "control-structures.elseif.php", "elseif, as its name suggests, is a combination of if and else", "PHP manual: elseif")
DC_FP = {"go": ["package p\n\nfunc f() (bool, error) {\n\tvar ok bool\n\tvar err error\n\tif ok, err = a(); ok {\n\t\treturn ok, err\n\t} else if ok, err = b(); ok {\n\t\treturn ok, err\n\t}\n\treturn false, nil\n}\n"],
         "kotlin": ["fun f(c: Char): Int {\n    if (c in 'A'..'Z') {\n        return 1\n    } else if (c in 'a'..'z') {\n        return 2\n    }\n    return 0\n}\n"]}
multi("DUPLICATE-CONDITION", "Repeated condition in an if / else-if chain",
      "This condition repeats an earlier one in the same if / else-if chain, so its branch can never run: fix the condition.",
      {l: dict(doc=DC_DOCS[l], query={"python": "(if_statement) @match"}.get(l, IFSW[l].replace(" (switch_expression)", "").replace(" (switch_statement)", "")
                                         .replace(" (when_expression)", "").replace(" (expression_switch_statement) (type_switch_statement)", "")),
               filters=["branches.dup_cond"] + NOT_ELSEIF.get(l, []),
               bad=ifchain(l, [["a1()"], ["a2()"], ["a3()"]], cond="a == %d").replace("a == 3", "a == 1"),
               good=ifchain(l, [["a1()"], ["a2()"], ["a3()"]]),
               fp=[ifchain(l, [["a1()"], ["a2()"]], cond="next()")] + DC_FP.get(l, []),
               eq={"go": ["revive:identical-ifelseif-conditions"]}.get(l, ()), cat="correctness")
       for l in ["java", "python", "go", "kotlin", "php"]}, keys=["S1862"], kind="anti-pattern", sev="major")

# ---- collapsible if / nested ternary --------------------------------------------------------
multi("COLLAPSIBLE-IF", "Nested if can be merged with its parent",
      "This if is the only statement inside another if and neither has an else: join the two conditions with a logical AND.",
      {
          "java": dict(doc=("https://pmd.github.io/pmd/pmd_rules_java_design.html", "statements that can be merged together by joining their conditions", "PMD CollapsibleIfStatements"),
                       query="(if_statement consequence: (block . (if_statement !alternative) .) !alternative) @match",
                       bad=fn("java", nested(2)), good=fn("java", [("if", "a && b", ["g()"])]),
                       fp=[fn("java", [("if", "a", [("ifelse", "b", ["g()"], ["h()"])])])], eq=["pmd:CollapsibleIfStatements"]),
          "python": dict(doc=rf("collapsible-if", "Checks for nested if statements that can be collapsed into a single if statement", "SIM102"),
                         query="(if_statement consequence: (block . (if_statement !alternative) .) !alternative) @match",
                         bad=fn("python", nested(2)), good=fn("python", [("if", "a && b", ["g()"])]),
                         fp=[fn("python", [("if", "a", [("ifelse", "b", ["g()"], ["h()"])])])], eq=["ruff:SIM102"]),
          "kotlin": dict(doc=dk("style", "This rule detects if statements which can be collapsed", "CollapsibleIfStatements"),
                         query="(if_expression condition: (_) . (block . (if_expression condition: (_) . (block) .) .) .) @match",
                         bad=fn("kotlin", nested(2)), good=fn("kotlin", [("if", "a && b", ["g()"])]),
                         fp=[fn("kotlin", [("if", "a", [("ifelse", "b", ["g()"], ["h()"])])])], eq=["detekt:CollapsibleIfStatements"]),
          "php": dict(doc=(PHPM + "control-structures.if.php", "allows for conditional execution of code fragments", "PHP manual: if"),
                      query="(if_statement body: (compound_statement . (if_statement body: (_) !alternative) .) !alternative) @match",
                      bad=fn("php", nested(2)), good=fn("php", [("if", "a && b", ["g()"])]),
                      fp=[fn("php", [("if", "a", [("ifelse", "b", ["g()"], ["h()"])])])]),
          "javascript": dict(doc=es("no-lonely-if"), keys=(),
                             query="(if_statement consequence: (statement_block . (if_statement !alternative) .) !alternative) @match",
                             bad=fn("javascript", nested(2)), good=fn("javascript", [("if", "a && b", ["g()"])]),
                             fp=[fn("javascript", [("if", "a", [("ifelse", "b", ["g()"], ["h()"])])])]),
          "go": dict(doc=(GOSPEC, '"If" statements specify the conditional execution', "Go spec: If statements"), keys=(),
                     query="(if_statement !initializer consequence: (block (statement_list . (if_statement !initializer !alternative) .)) !alternative) @match",
                     bad=fn("go", nested(2)), good=fn("go", [("if", "a && b", ["g()"])]),
                     fp=[fn("go", [("if", "a", [("ifelse", "b", ["g()"], ["h()"])])])]),
      }, keys=["S1066"])

multi("NESTED-TERNARY", "Conditional expression nested inside another",
      "A conditional expression inside another one is hard to read: use if/else statements or a named helper.",
      {
          "java": dict(doc=("https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html", "The conditional operator ? : uses the boolean value of one expression to decide which of two other expressions should be evaluated", "JLS 15.25 Conditional Operator"),
                       query="(ternary_expression [(ternary_expression) (parenthesized_expression (ternary_expression))]) @match",
                       filters=["node.has_ancestor:method_declaration|constructor_declaration|lambda_expression|field_declaration"],
                       bad="class A {\n    String f(int n) {\n        return n < 0 ? \"neg\" : n == 0 ? \"zero\" : \"pos\";\n    }\n}\n",
                       good="class A {\n    String f(int n) {\n        if (n < 0) {\n            return \"neg\";\n        }\n        return n == 0 ? \"zero\" : \"pos\";\n    }\n}\n"),
          "python": dict(doc=("https://docs.python.org/3/reference/expressions.html", "is an alternative to the if-else statement", "Python reference: Conditional expressions"),
                         query="(conditional_expression [(conditional_expression) (parenthesized_expression (conditional_expression))]) @match",
                         bad="def f(n):\n    return \"neg\" if n < 0 else \"zero\" if n == 0 else \"pos\"\n",
                         good="def f(n):\n    if n < 0:\n        return \"neg\"\n    return \"zero\" if n == 0 else \"pos\"\n"),
          "php": dict(doc=(PHPM + "language.operators.comparison.php", "It is recommended to avoid", "PHP manual: Ternary Operator"),
                      query="(conditional_expression [(conditional_expression) (parenthesized_expression (conditional_expression))]) @match",
                      # PHP manual: "Chaining of short-ternaries (?:), however, is stable and behaves reasonably"
                      filters=[r"node.lacks_re:^[^?]*(\?:[^?]*)+$"], fp=["<?php\n$home = getenv('HOME') ?: getenv('USERPROFILE') ?: '/tmp';\n"],
                      bad="<?php\nfunction f($n) {\n    return $n < 0 ? 'neg' : ($n == 0 ? 'zero' : 'pos');\n}\n",
                      good="<?php\nfunction f($n) {\n    if ($n < 0) {\n        return 'neg';\n    }\n    return $n == 0 ? 'zero' : 'pos';\n}\n"),
      }, keys=["S3358"])

# ---- empty code ---------------------------------------------------------------------------------
EMPTY = r'"^\\{\\s*\\}$"'
multi("EMPTY-BLOCK", "Empty block with no explanation",
      "This block is empty and has no comment saying why: add the missing code, remove the block, or explain the intent in a comment.",
      {
          "java": dict(doc=cs("blocks/emptyblock", "Checks for empty blocks", "EmptyBlock"), eq=["checkstyle:EmptyBlock"],
                       query=f"((block) @match (#match? @match {EMPTY}))",
                       filters=["parentkind.has_re:if_statement|for_statement|enhanced_for_statement|try_statement|finally_clause|synchronized_statement:."],
                       bad="class A {\n    void f(int n) {\n        if (n > 0) {\n        }\n        run();\n    }\n}\n",
                       good="class A {\n    void f(int n) {\n        if (n > 0) {\n            // already handled by the caller\n        }\n        run();\n    }\n}\n",
                       fp=["class A {\n    void spin() {\n        while (!ready()) {\n        }\n    }\n}\n"]),
          "python": dict(doc=(PYSIMPLE, "pass is a null operation", "Python reference: The pass statement"),
                         query="(block . (pass_statement) .) @match",
                         # `for _ in it: pass` drains an iterator, `with open(p): pass` touches a file, and
                         # `if a: pass / else: ...` is a deliberate no-op branch: none of these is an empty block.
                         filters=["parentkind.has_re:if_statement|elif_clause|else_clause|while_statement|finally_clause:.",
                                  "parentkind.lacks_re:if_statement|elif_clause|else_clause|while_statement|finally_clause:#",
                                  r"ancestor.lacks_re:if_statement:(?m)^\s*(elif\b|else\s*:)"],
                         bad="def f(n):\n    if n > 0:\n        pass\n    run()\n",
                         good="def f(n):\n    if n > 0:\n        run()\n",
                         fp=["def f(n):\n    if n > 0:\n        # already handled by the caller\n        pass\n    run()\n",
                             "class Skip(Exception):\n    pass\n",
                             "def consume(it):\n    for _ in it:\n        pass\n",
                             "def f(a):\n    if a == 1:\n        pass\n    elif a == 2:\n        g()\n    else:\n        h()\n"]),
          "go": dict(doc=rv("Empty blocks make code less readable", "empty-block"), eq=["revive:empty-block", "staticcheck:SA9003"],
                     query=f"((block) @match (#match? @match {EMPTY}))", filters=["parentkind.has_re:if_statement:."],
                     bad="package p\n\nfunc f(err error) {\n\tif err != nil {\n\t}\n\trun()\n}\n",
                     good="package p\n\nfunc f(err error) {\n\tif err != nil {\n\t\treturn\n\t}\n\trun()\n}\n",
                     fp=["package p\n\nfunc f() {\n\tfor {\n\t}\n}\n"]),
          "kotlin": dict(doc=dk("empty-blocks", "Reports empty", "EmptyIfBlock"), eq=["detekt:EmptyIfBlock", "detekt:EmptyElseBlock", "detekt:EmptyForBlock", "detekt:EmptyTryBlock", "detekt:EmptyFinallyBlock"],
                         query=f"((block) @match (#match? @match {EMPTY}))",
                         filters=["parentkind.has_re:if_expression|for_statement|try_expression|finally_block:."],
                         bad="fun f(n: Int) {\n    if (n > 0) {\n    }\n    run()\n}\n",
                         good="fun f(n: Int) {\n    if (n > 0) {\n        run()\n    }\n}\n",
                         fp=["fun f(n: Int) {\n    if (n > 0) {\n        // handled upstream\n    }\n}\n"]),
          "php": dict(doc=(PHPM + "control-structures.if.php", "allows for conditional execution of code fragments", "PHP manual: if"),
                      query=f"((compound_statement) @match (#match? @match {EMPTY}))",
                      filters=["parentkind.has_re:if_statement|else_clause|else_if_clause|foreach_statement|for_statement|try_statement|finally_clause:."],
                      bad="<?php\nfunction f($n) {\n    if ($n > 0) {\n    }\n    run();\n}\n",
                      good="<?php\nfunction f($n) {\n    if ($n > 0) {\n        run();\n    }\n}\n",
                      fp=["<?php\nfunction f($n) {\n    if ($n > 0) {\n        // handled upstream\n    }\n}\n"]),
      }, keys=["S108"])

multi("EMPTY-FUNCTION", "Function with an empty body and no comment",
      "This function does nothing and does not say why: implement it, throw an unsupported-operation error, or add a comment explaining "
      "that doing nothing is intended.",
      {
          "java": dict(doc=("https://pmd.github.io/pmd/pmd_rules_java_codestyle.html", "Empty or auto-generated methods in an abstract class should be tagged as abstract", "PMD EmptyMethodInAbstractClassShouldBeAbstract"),
                       query=f"(method_declaration body: (block) @b (#match? @b {EMPTY})) @match",
                       filters=[r"node.lacks_re:^[^{]*\bdefault\b", r"ancestor.lacks_re:class_declaration:^[^{]*\babstract\b"],
                       bad="class Job {\n    void cleanup() {\n    }\n}\n",
                       good="class Job {\n    void cleanup() {\n        // nothing to release: the job holds no resources\n    }\n}\n",
                       fp=["abstract class Base {\n    protected void onStart() {\n    }\n}\n"]),
          "python": dict(doc=(PYSIMPLE, "pass is a null operation", "Python reference: The pass statement"),
                         query="(function_definition body: (block . (pass_statement) .)) @match",
                         filters=["parentkind.lacks_re:decorated_definition:.", "node.lacks_re:#",
                                  r"ancestor.lacks_re:class_definition:^class\s+\w*(Base|Mixin|Interface|Protocol|ABC)\b|^class\s+\w+\([^)]*(ABC|Protocol|Interface|Base)"],
                         bad="def cleanup():\n    pass\n", good="def cleanup():\n    \"\"\"Nothing to release: the job holds no resources.\"\"\"\n",
                         fp=["from abc import ABC\n\nclass Store(ABC):\n    def save(self):\n        pass\n"]),
          "go": dict(doc=rv("Empty blocks make code less readable", "empty-block"), eq=["revive:empty-block"],
                     query=f"(function_declaration name: (identifier) @n body: (block) @b (#match? @b {EMPTY}) (#not-match? @n \"^(main|init)$\")) @match",
                     bad="package p\n\nfunc cleanup() {}\n", good="package p\n\nfunc cleanup() {\n\t// nothing to release: the job holds no resources\n}\n",
                     fp=["package p\n\ntype nop struct{}\n\nfunc (nop) Close() {}\n"]),
          "kotlin": dict(doc=dk("empty-blocks", "Reports empty functions", "EmptyFunctionBlock"), eq=["detekt:EmptyFunctionBlock"],
                         query=f"(function_declaration (function_body (block) @b) (#match? @b {EMPTY})) @match",
                         filters=[r"node.lacks_re:^[^{]*\b(override|open)\b", r"ancestor.lacks_re:class_declaration:^[^{]*\b(abstract|open|interface)\b"],
                         bad="fun cleanup() {}\n", good="fun cleanup() {\n    // nothing to release\n}\n",
                         fp=["class Listener : Callback {\n    override fun onEvent() {}\n}\n"]),
          "php": dict(doc=(PHPM + "functions.user-defined.php", "Any valid PHP code may appear inside the body of a function", "PHP manual: User-defined functions"),
                      query=f"[(function_definition body: (compound_statement) @b) (method_declaration name: (name) @n body: (compound_statement) @b (#not-eq? @n \"__construct\"))] @match",
                      filters=[f"cap.has_re:b:^\\{{\\s*\\}}$", r"ancestor.lacks_re:class_declaration:^[^{]*\babstract\b"],
                      bad="<?php\nfunction cleanup() {\n}\n", good="<?php\nfunction cleanup() {\n    // nothing to release\n}\n",
                      fp=["<?php\nclass A {\n    public function __construct() {\n    }\n}\n"]),
      }, keys=["S1186"], mode="ai-confirm", ai="Is the empty body unintended (not a deliberate no-op such as an optional hook or a null object)?")

multi("EMPTY-CATCH", "Caught exception silently ignored",
      "The catch block is empty, so the failure disappears without a trace: handle it, log it, or rename the variable to `ignored` and "
      "add a comment if swallowing it is intended.",
      {
          "java": dict(doc=cs("blocks/emptycatchblock", "Checks for empty catch blocks", "EmptyCatchBlock"), eq=["checkstyle:EmptyCatchBlock"],
                       query=f"(catch_clause (catch_formal_parameter name: (identifier) @e) body: (block) @b (#match? @b {EMPTY}) (#not-match? @e \"^(ignored?|expected|unused|_)$\")) @match",
                       bad="class A {\n    void f() {\n        try {\n            load();\n        } catch (IOException e) {\n        }\n    }\n}\n",
                       good="class A {\n    void f() {\n        try {\n            load();\n        } catch (IOException e) {\n            log.warn(\"load failed\", e);\n        }\n    }\n}\n",
                       fp=["class A {\n    void f() {\n        try {\n            load();\n        } catch (IOException ignored) {\n        }\n    }\n}\n"],
                       keys=["S108", "S2486"]),
          "php": dict(doc=(PHPM + "class.exception.php", "is the base class for all user exceptions", "PHP manual: Exception"),
                      query=f"(catch_clause body: (compound_statement) @b (#match? @b {EMPTY})) @match",
                      bad="<?php\ntry {\n    load();\n} catch (Exception $e) {\n}\n",
                      good="<?php\ntry {\n    load();\n} catch (Exception $e) {\n    error_log($e->getMessage());\n}\n",
                      fp=["<?php\ntry {\n    load();\n} catch (Exception $e) {\n    // optional cache, a miss is fine\n}\n"], keys=["S108", "S2486"]),
      }, cat="correctness", sev="major", kind="anti-pattern")

# ---- comments -----------------------------------------------------------------------------------
COMMENT = {"java": "[(line_comment) (block_comment)]", "python": "(comment)", "go": "(comment)", "kotlin": "[(line_comment) (block_comment)]",
           "php": "(comment)", "javascript": "(comment)"}
CMT = {"python": "#", "php": "//"}


def _c(lang, text):
    return CMT.get(lang, "//") + " " + text


def todo_rule(id, word, title, msg, key, docs, eqs):
    spec = {}
    for lang, doc in docs.items():
        line = {"java": "class A {\n    %s\n    void f() {}\n}\n", "python": "%s\ndef f():\n    return 1\n", "go": "package p\n\n%s\nfunc f() {}\n",
                "kotlin": "%s\nfun f() {}\n", "php": "<?php\n%s\nfunction f() {}\n", "javascript": "%s\nfunction f() {}\n"}[lang]
        spec[lang] = dict(doc=doc, query=f"({COMMENT[lang]} @match (#match? @match \"\\\\b{word}\\\\b\"))", eq=eqs.get(lang, ()),
                          bad=line % _c(lang, f"{word}: retry on timeout"), good=line % _c(lang, "retries are handled by the client"),
                          fp=[line % _c(lang, f"see {word.lower()}s.md for the plan")])
    multi(id, title, msg, spec, keys=[key], sev="info")


todo_rule("TODO-COMMENT", "TODO", "TODO comment left in the code",
          "A TODO marks unfinished work: finish it in this change or track it in an issue and link the issue here.", "S1135", {
              "java": cs("misc/todocomment", "comments. Actually it is a generic pattern matcher on Java comments", "TodoComment"),
              "python": rf("line-contains-todo", 'Checks for "TODO" comments', "FIX002"),
              "go": gl("Detects usage of FIXME, TODO", "godox"),
              "kotlin": dk("style", "This rule allows to set a list of comments which are forbidden in the codebase", "ForbiddenComment"),
              "php": (PHPM + "language.basic-syntax.comments.php", "PHP supports", "PHP manual: Comments"),
          }, {"java": ["checkstyle:TodoComment"], "python": ["ruff:FIX002"], "go": ["godox:godox"], "kotlin": ["detekt:ForbiddenComment"]})
todo_rule("FIXME-COMMENT", "FIXME", "FIXME comment left in the code",
          "A FIXME marks known broken behaviour: fix it before merging or open an issue that tracks it.", "S1134", {
              "java": cs("misc/todocomment", "comments. Actually it is a generic pattern matcher on Java comments", "TodoComment"),
              "python": rf("line-contains-fixme", 'Checks for "FIXME" comments', "FIX001"),
              "go": gl("Detects usage of FIXME, TODO", "godox"),
              "kotlin": dk("style", "This rule allows to set a list of comments which are forbidden in the codebase", "ForbiddenComment"),
              "php": (PHPM + "language.basic-syntax.comments.php", "PHP supports", "PHP manual: Comments"),
          }, {"python": ["ruff:FIX001"], "go": ["godox:godox"], "kotlin": ["detekt:ForbiddenComment"]})

CODE_LIKE = {
    "java": r"^//\s*([\w.]+(\(.*\))?\s*(=[^=].*)?;|(if|for|while)\s*\(.*\)\s*\{|return\b.*;|import\s+[\w.]+;|\}\s*else\s*\{)\s*$",
    "python": r"^#\s*(print\(.*\)|import\s+\w[\w.]*|from\s+[\w.]+\s+import\s+\w.*|return\b.*|[a-z_][\w.]*\s*=\s*[\w\[{(\"'].*|[a-z_][\w.]*\(.*\))\s*$",
    "kotlin": r"^//\s*((val|var)\s+\w+\s*=.*|fun\s+\w+\(.*|return\b.*|import\s+[\w.]+|[\w.]+\(.*\))\s*$",
    "php": r"^(//|#)\s*(\$\w+\s*(->\w+)*\s*=[^=].*;|[\w$>-]+\(.*\);|return\b.*;|(if|foreach|while)\s*\(.*\)\s*\{)\s*$",
    # gofmt puts spaces around = and :=, so `level=info msg=x` (logfmt output) is not an assignment
    "go": r"^//\s?([\w.]+(,\s*[\w.]+)*\s(:=|=)\s.+|[\w.]+\(.*\)|return\b.*|if\s.+\{|for\s.*\{)\s*$",
}
# Go doc comments: a tab/multi-space indented line is a godoc code block (go.dev/doc/comment "Code blocks"),
# and `return the ...` style sentences are prose.
CC_SKIP_GO = [r"node.lacks_re:^//(\t|\s{2,})", r"node.lacks_re:^//\s*return\s+[a-z]+\s+[a-z]+\s+[a-z]+"]
# Kotlin has no statement terminator, so prose that starts with a keyword ("return -1, then ...") looks like code:
# skip sentence punctuation, a bare comma clause after return, and keyword + three words
# corpus m8: "// return -1 which may trigger ..." is prose; U+2212/U+00D7 math signs mark a derivation, not code
CC_SKIP_KT = [r"node.lacks_re:\w[.!?]\s*$|^//\s*return\s+[^(\n]*,\s+[a-z]|^//\s*return\s+([a-z']+\s+){2}[a-z']+|^//\s*return\s+\S+\s+(which|that|if|when|because|so|and|to|so)\s|[\x{2212}\x{00D7}\x{00F7}]",
              # the rest of a worked derivation whose earlier lines use math signs (okio ZipFiles filetime)
              r"file.lacks_re://[^\n]*[\x{2212}\x{00D7}\x{00F7}][^\n]*\n(?:[ \t]*//[^\n]*\n){0,3}[ \t]*{cap:match}"]
CC_SKIP = r"(?i)^(#|//)\s*(type:|noqa|pragma|nolint|go:|\+build|lint:|eslint|phpcs|@|-\*-|fmt:|isort:|pylint:|mypy:|e\.g\.|example)"
multi("COMMENTED-OUT-CODE", "Commented-out code",
      "This comment is code that was switched off: delete it (version control keeps the history) or restore it.",
      {lang: dict(doc=doc, query=f"{COMMENT[lang]} @match",
                  filters=["node.has_re:" + CODE_LIKE[lang], "node.lacks_re:" + CC_SKIP] + (CC_SKIP_GO if lang == "go" else CC_SKIP_KT if lang == "kotlin" else []), eq=eq,
                  bad=bad, good=good, fp=fp)
       for lang, doc, eq, bad, good, fp in [
           ("java", ("https://docs.oracle.com/javase/specs/jls/se21/html/jls-3.html", "There are two kinds of comments", "JLS 3.7 Comments"), (),
            "class A {\n    void f() {\n        // cache.clear();\n        run();\n    }\n}\n", "class A {\n    void f() {\n        // the cache is cleared by the scheduler\n        run();\n    }\n}\n",
            ["class A {\n    // see Foo.bar() for details\n    void f() {}\n}\n"]),
           ("python", rf("commented-out-code", "Checks for commented-out Python code", "ERA001"), ["ruff:ERA001"],
            "def f():\n    # print(state)\n    return run()\n", "def f():\n    # state is logged by run()\n    return run()\n",
            ["def f():\n    # type: () -> int\n    return run()\n"]),
           ("kotlin", ("https://kotlinlang.org/docs/basic-syntax.html", "Kotlin supports single-line (or end-of-line) and multi-line (block) comments", "Kotlin docs: Comments"), (),
            "fun f() {\n    // val cached = load()\n    run()\n}\n", "fun f() {\n    // loading happens lazily in run()\n    run()\n}\n",
            ["fun f() {\n    // see load() for details\n    run()\n}\n",
             "fun f() {\n    // return -1, then our data finished prematurely!\n    // return is a 'spurious wakeup' because notify() was not called.\n    // return 200, there is a get handler\n    run()\n}\n"]),
           ("php", (PHPM + "language.basic-syntax.comments.php", "PHP supports", "PHP manual: Comments"), (),
            "<?php\nfunction f() {\n    // $cache->clear();\n    run();\n}\n", "<?php\nfunction f() {\n    // the scheduler clears the cache\n    run();\n}\n",
            ["<?php\nfunction f() {\n    // @var Foo $x\n    run();\n}\n"]),
           ("go", (GOSPEC, "Comments serve as program documentation", "Go spec: Comments"), (),
            "package p\n\nfunc f() {\n\t// cache.Clear()\n\trun()\n}\n", "package p\n\nfunc f() {\n\t// the scheduler clears the cache\n\trun()\n}\n",
            ["package p\n\n//go:generate stringer -type=Kind\nfunc f() {}\n",
             "package p\n\n// New returns a router.\n//\n//\tr := mux.NewRouter()\nfunc New() {}\n",
             "package p\n\n// return true on the first found command\nfunc f() {}\n",
             "package p\n\n// Output:\n// level=info msg=\"first log\"\nfunc f() {}\n"]),
       ]}, keys=["S125"], mode="ai-confirm", ai="Is this comment disabled code (not prose, a doc example or a directive)?")



# ---- boolean simplification ------------------------------------------------------------------
multi("BOOLEAN-LITERAL-COMPARISON", "Comparison with a boolean literal",
      "Comparing with true/false adds nothing: use the expression itself, or negate it.",
      {
          "java": dict(doc=cs("coding/simplifybooleanexpression", "Checks for over-complicated boolean expressions", "SimplifyBooleanExpression"),
                       eq=["checkstyle:SimplifyBooleanExpression"],
                       query="[(binary_expression operator: [\"==\" \"!=\"] [left: [(true) (false)] right: [(true) (false)]]) (ternary_expression consequence: [(true) (false)] alternative: [(true) (false)])] @match",
                       bad="class A {\n    void f(boolean done) {\n        if (done == true) {\n            stop();\n        }\n    }\n}\n",
                       good="class A {\n    void f(boolean done) {\n        if (done) {\n            stop();\n        }\n    }\n}\n",
                       mode="ai-confirm", ai="Is the compared value a primitive boolean (a Boolean wrapper may be null, where == true is a null-safe check)?"),
          "go": dict(doc=sc("Omit comparison with boolean constant", "S1002"), eq=["gosimple:S1002", "revive:bool-literal-in-expr"],
                     query="(binary_expression operator: [\"==\" \"!=\"] [left: [(true) (false)] right: [(true) (false)]]) @match",
                     # S1002 needs a bool operand: map lookups and Get/Value/Load accessors usually yield interface{}
                     filters=[r"node.lacks_re:\]\s*[!=]=|\b(Get\w*|Value|Load|Interface|Lookup)\([^()]*\)\s*[!=]=|^\s*(true|false)\s*[!=]=\s*\w+\["],
                     fp=["package p\n\nfunc f(m map[string]any) bool {\n\treturn m[\"x\"] == true\n}\n",
                         "package p\n\nfunc f(ctx C) bool {\n\treturn GetVar(ctx, k) == true\n}\n"],
                     bad="package p\n\nfunc f(done bool) {\n\tif done == true {\n\t\tstop()\n\t}\n}\n",
                     good="package p\n\nfunc f(done bool) {\n\tif done {\n\t\tstop()\n\t}\n}\n"),
          "php": dict(doc=(PHPM + "language.operators.comparison.php", "Comparison operators, as their name implies", "PHP manual: Comparison operators"),
                      query="[(binary_expression operator: [\"==\" \"!=\"] [left: (boolean) right: (boolean)]) (conditional_expression body: (boolean) alternative: (boolean))] @match",
                      bad="<?php\nfunction f($done) {\n    if ($done == true) {\n        stop();\n    }\n}\n",
                      good="<?php\nfunction f($done) {\n    if ($done) {\n        stop();\n    }\n}\n",
                      fp=["<?php\nfunction f($x) {\n    return $x === true;\n}\n"]),
      }, keys=["S1125"])

RET_BOOL = {
    "java": ("class A {\n    boolean f(int n) {\n        if (n > 0) {\n            return true;\n        } else {\n            return false;\n        }\n    }\n}\n",
             "class A {\n    boolean f(int n) {\n        return n > 0;\n    }\n}\n",
             "[(if_statement consequence: [(return_statement [(true) (false)]) (block . (return_statement [(true) (false)]) .)] alternative: [(return_statement [(true) (false)]) (block . (return_statement [(true) (false)]) .)]) @match (block (if_statement consequence: [(return_statement [(true) (false)]) (block . (return_statement [(true) (false)]) .)] !alternative) @match . (return_statement [(true) (false)]))]"),
    "javascript": ("function f(n) {\n  if (n > 0) {\n    return true;\n  } else {\n    return false;\n  }\n}\n", "function f(n) {\n  return n > 0;\n}\n",
                   "(if_statement consequence: [(return_statement [(true) (false)]) (statement_block . (return_statement [(true) (false)]) .)] alternative: (else_clause [(return_statement [(true) (false)]) (statement_block . (return_statement [(true) (false)]) .)])) @match"),
    "php": ("<?php\nfunction f($n) {\n    if ($n > 0) {\n        return true;\n    } else {\n        return false;\n    }\n}\n", "<?php\nfunction f($n) {\n    return $n > 0;\n}\n",
            "(if_statement body: (compound_statement . (return_statement (boolean)) .) alternative: (else_clause body: (compound_statement . (return_statement (boolean)) .))) @match"),
    "python": ("def f(n):\n    if n > 0:\n        return True\n    else:\n        return False\n", "def f(n):\n    return n > 0\n",
               "(if_statement consequence: (block . (return_statement [(true) (false)]) .) alternative: (else_clause body: (block . (return_statement [(true) (false)]) .))) @match"),
}
multi("RETURN-BOOLEAN-IF", "if/else that only returns true or false",
      "Both branches just return a boolean literal: return the condition (or its negation) directly.",
      {l: dict(doc={"java": cs("coding/simplifybooleanreturn", "Checks for over-complicated boolean return", "SimplifyBooleanReturn"),
                    "javascript": (MDN + "Statements/return", "The return statement ends function execution", "MDN: return"),
                    "php": (PHPM + "language.types.boolean.php", "is used to express a truth value", "PHP manual: Booleans"),
                    "python": rf("needless-bool", "Checks for if statements that can be replaced with bool", "SIM103")}[l],
               eq={"java": ["checkstyle:SimplifyBooleanReturn"], "python": ["ruff:SIM103"]}.get(l, ()),
               query=v[2], bad=v[0], good=v[1],
               filters=[r"parent.has_re:(?is)\b(true)\b.*\b(false)\b|\b(false)\b.*\b(true)\b"])
       for l, v in RET_BOOL.items()}, keys=["S1126"])


# ---- obvious mistakes ---------------------------------------------------------------------------
multi("SELF-ASSIGNMENT", "Variable assigned to itself",
      "Assigning a variable to itself does nothing; the intended source (often a parameter or a field) is probably missing.",
      {
          "java": dict(doc=("https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html", "The result of the first operand of an assignment operator must be a variable", "JLS 15.26 Assignment Operators"),
                       query="(assignment_expression left: (_) @l operator: \"=\" right: (_) @r (#eq? @l @r)) @match",
                       bad="class A {\n    int size;\n    void setSize(int newSize) {\n        size = size;\n    }\n}\n",
                       good="class A {\n    int size;\n    void setSize(int size) {\n        this.size = size;\n    }\n}\n"),
          "python": dict(doc=rf("self-assigning-variable", "Checks for self-assignment of variables", "PLW0127"), eq=["ruff:PLW0127"],
                         query="(assignment left: (_) @l right: (_) @r (#eq? @l @r)) @match",
                         filters=["ancestor.has_re:class_definition|function_definition:^(async\\s+)?def\\b"],
                         bad="def f(total):\n    total = total\n    return total\n", good="def f(total):\n    return total\n",
                         fp=["class A:\n    name = name\n"]),
          "kotlin": dict(doc=("https://kotlinlang.org/docs/properties.html", "Declaring properties", "Kotlin docs: Properties"),
                         query="(assignment left: (_) @l right: (_) @r (#eq? @l @r)) @match",
                         bad="class A {\n    var size = 0\n    fun update(newSize: Int) {\n        size = size\n    }\n}\n",
                         good="class A {\n    var size = 0\n    fun update(size: Int) {\n        this.size = size\n    }\n}\n"),
          "php": dict(doc=(PHPM + "language.operators.assignment.php", "The basic assignment operator is", "PHP manual: Assignment operators"),
                      query="(assignment_expression left: (_) @l right: (_) @r (#eq? @l @r)) @match",
                      bad="<?php\nclass A {\n    private $size;\n    function setSize($newSize) {\n        $this->size = $this->size;\n    }\n}\n",
                      good="<?php\nclass A {\n    private $size;\n    function setSize($size) {\n        $this->size = $size;\n    }\n}\n"),
      }, keys=["S1656"], cat="correctness", kind="anti-pattern", sev="major")

NOT_LITERAL = r"cap.lacks_re:l:^(true|false|True|False|null|nil|None|-?\d[\w.]*|'[^']*'|\x22[^\x22]*\x22)$"
IDOPS = '["<" ">" "<=" ">=" "&&" "||" "-" "/" "%" "^" "&" "|"]'
GO_IDOPS = IDOPS.replace(' "^"', '')
PHP_IDOPS = IDOPS.replace("]", ' "and" "or"]')
multi("IDENTICAL-OPERANDS", "Same expression on both sides of an operator",
      "Both operands are the same expression, so the result is constant (or the second operand was meant to be something else).",
      {
          "java": dict(bad="class A {\n    boolean inRange(int lo, int hi, int x) {\n        return x >= lo && x >= lo;\n    }\n}\n", good="class A {\n    boolean inRange(int lo, int hi, int x) {\n        return x >= lo && x <= hi;\n    }\n}\n", fp=["class A {\n    int f() {\n        return next() - next();\n    }\n}\n", "class A {\n    boolean[] t = {true ^ true, false ^ false};\n}\n"], filters_extra=1, doc=("https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html", "The conditional-and operator && is like &", "JLS 15.23 Conditional-And Operator"),
                       query=f"(binary_expression left: (_) @l operator: {IDOPS} right: (_) @r (#eq? @l @r)) @match"),
          "javascript": dict(bad="function inRange(lo, hi, x) {\n  return x >= lo && x >= lo;\n}\n", good="function inRange(lo, hi, x) {\n  return x >= lo && x <= hi;\n}\n", fp=["function f(it) {\n  return it.next() - it.next();\n}\n"], filters_extra=1, doc=es("no-self-compare"), eq=["eslint:no-self-compare"],
                             query=f"(binary_expression left: (_) @l operator: {IDOPS} right: (_) @r (#eq? @l @r)) @match"),
          "python": dict(bad="def in_range(lo, hi, x):\n    return x >= lo and x >= lo\n", good="def in_range(lo, hi, x):\n    return x >= lo and x <= hi\n", fp=["def f(it):\n    return next(it) - next(it)\n"], filters_extra=1, doc=rf("comparison-with-itself", "Checks for operations that compare a name to itself", "PLR0124"), eq=["ruff:PLR0124", "pylint:comparison-with-itself"],
                         filters=[r"cap.lacks_re:l:(^|\.)[A-Z][a-z]\w*$"],
                         query="[(comparison_operator (_) @l [\"<\" \">\" \"<=\" \">=\" \"is\"] (_) @r (#eq? @l @r)) (boolean_operator left: (_) @l right: (_) @r (#eq? @l @r)) (binary_operator left: (_) @l operator: [\"-\" \"/\" \"%\" \"^\" \"&\" \"|\" \"//\"] right: (_) @r (#eq? @l @r))] @match"),
          "go": dict(bad="package p\n\nfunc inRange(lo, hi, x int) bool {\n\treturn x >= lo && x >= lo\n}\n", good="package p\n\nfunc inRange(lo, hi, x int) bool {\n\treturn x >= lo && x <= hi\n}\n", fp=["package p\n\nfunc f() int {\n\treturn next() - next()\n}\n"], filters_extra=1, doc=sc("Binary operator has identical expressions on both sides", "SA4000"), eq=["staticcheck:SA4000"],
                     query=f"(binary_expression left: (_) @l operator: {GO_IDOPS} right: (_) @r (#eq? @l @r)) @match"),
          "kotlin": dict(bad="fun inRange(lo: Int, hi: Int, x: Int): Boolean {\n    return x >= lo && x >= lo\n}\n", good="fun inRange(lo: Int, hi: Int, x: Int): Boolean {\n    return x >= lo && x <= hi\n}\n", fp=["fun f(): Int {\n    return next() - next()\n}\n"], filters_extra=1, doc=("https://kotlinlang.org/docs/operator-overloading.html", "Kotlin allows you to provide custom implementations", "Kotlin docs: Operator overloading"),
                         query="(binary_expression left: (_) @l right: (_) @r (#eq? @l @r)) @match",
                         filters=[r"node.has_re:^{cap:l}\s*(<|>|<=|>=|&&|\|\||-|/|%)\s*{cap:r}$"]),
          "php": dict(bad="<?php\nfunction inRange($lo, $hi, $x) {\n    return $x >= $lo && $x >= $lo;\n}\n", good="<?php\nfunction inRange($lo, $hi, $x) {\n    return $x >= $lo && $x <= $hi;\n}\n", fp=["<?php\nfunction f() {\n    return next() - next();\n}\n"], filters_extra=1, doc=(PHPM + "language.operators.logical.php", "Logical Operators", "PHP manual: Logical operators"),
                      query=f"(binary_expression left: (_) @l operator: {PHP_IDOPS} right: (_) @r (#eq? @l @r)) @match"),
      }, keys=["S1764"], cat="correctness", kind="anti-pattern", sev="major")


# ---- dead code / control flow ---------------------------------------------------------------------
multi("UNREACHABLE-CODE", "Statement after return/throw can never run",
      "This statement follows an unconditional return, raise/throw, break or continue in the same block, so it never runs: remove it or "
      "move it before the jump.",
      {
          "python": dict(doc=(PYSIMPLE, "return leaves the current function call", "Python reference: The return statement"),
                         query="(block [(return_statement) (raise_statement) (break_statement) (continue_statement)] . (_) @match)",
                         # `return` + bare `yield` is the documented idiom for an empty generator, not dead code
                         filters=["node.lacks_re:^#", "node.lacks_re:^yield\\b"], eq=["pylint:unreachable"],
                         bad="def f(x):\n    return x * 2\n    print(x)\n", good="def f(x):\n    print(x)\n    return x * 2\n",
                         fp=["def f(x):\n    return x * 2\n    # trailing note\n", "def empty():\n    return\n    yield  # keeps this a generator\n"]),
          "kotlin": dict(doc=dk("potential-bugs", "Reports unreachable code", "UnreachableCode"), eq=["detekt:UnreachableCode"],
                         query="(block [(return_expression) (throw_expression)] . (_) @match)",
                         filters=["node.lacks_re:^(//|/\\*)"],
                         bad="fun f(x: Int): Int {\n    return x * 2\n    println(x)\n}\n", good="fun f(x: Int): Int {\n    println(x)\n    return x * 2\n}\n",
                         fp=["fun f(x: Int): Int {\n    return x * 2\n    // trailing note\n}\n"]),
          "php": dict(doc=(PHPM + "function.return.php", "returns program control to the calling module", "PHP manual: return"),
                      query="(compound_statement [(return_statement) (break_statement) (continue_statement) (expression_statement (throw_expression))] . (_) @match)",
                      filters=["node.lacks_re:^(//|#|/\\*)", "node.lacks_re:^(function|class|interface|trait|enum)\\b"],
                      bad="<?php\nfunction f($x) {\n    return $x * 2;\n    echo $x;\n}\n", good="<?php\nfunction f($x) {\n    echo $x;\n    return $x * 2;\n}\n",
                      fp=["<?php\nfunction f($x) {\n    return $x * 2;\n    // trailing note\n}\n"]),
      }, keys=["S1763"], cat="correctness", kind="anti-pattern", sev="major")

JUMP_FIN_JAVA = "ancestor.has_re:finally_clause|method_declaration|constructor_declaration|lambda_expression|class_body:^finally\\b"
LOOPS_JAVA = "for_statement|enhanced_for_statement|while_statement|do_statement|switch_block"
multi("JUMP-IN-FINALLY", "return/break/continue inside finally",
      "Leaving a finally block with return/break/continue discards any exception (or earlier return value) from the try block: move "
      "the jump out of finally.",
      {
          "java": dict(doc=(JLS14, "If the finally block completes abruptly for reason S", "JLS 14.20.2 try-finally"),
                       query="[(return_statement) (break_statement) (continue_statement)] @match",
                       filters=[JUMP_FIN_JAVA, f"ancestor.has_re:finally_clause|{LOOPS_JAVA}|lambda_expression|method_declaration:^finally\\b"],
                       bad="class A {\n    int f() {\n        try {\n            return compute();\n        } finally {\n            return -1;\n        }\n    }\n}\n",
                       good="class A {\n    int f() {\n        try {\n            return compute();\n        } finally {\n            cleanup();\n        }\n    }\n}\n",
                       fp=["class A {\n    void f(int[] xs) {\n        try {\n            run();\n        } finally {\n            for (int x : xs) {\n                if (x > 0) {\n                    break;\n                }\n            }\n        }\n    }\n}\n"]),
          "kotlin": dict(doc=dk("exceptions", "Reports all return statements in finally blocks", "ReturnFromFinally"), eq=["detekt:ReturnFromFinally"],
                         query="(finally_block (block (return_expression) @match))",
                         bad="fun f(): Int {\n    try {\n        return compute()\n    } finally {\n        return -1\n    }\n}\n",
                         good="fun f(): Int {\n    try {\n        return compute()\n    } finally {\n        cleanup()\n    }\n}\n"),
      }, keys=["S1143"], cat="correctness", kind="anti-pattern", sev="major")

multi("THROW-IN-FINALLY", "Exception thrown from finally",
      "An exception thrown in finally replaces the one from the try block, which is lost: catch and log inside finally instead.",
      {
          "java": dict(doc=(JLS14, "If the finally block completes abruptly for reason S", "JLS 14.20.2 try-finally"),
                       query="(throw_statement) @match", filters=[JUMP_FIN_JAVA],
                       bad="class A {\n    void f() {\n        try {\n            run();\n        } finally {\n            throw new IllegalStateException(\"cleanup failed\");\n        }\n    }\n}\n",
                       good="class A {\n    void f() {\n        try {\n            run();\n        } finally {\n            cleanup();\n        }\n    }\n}\n",
                       fp=["class A {\n    void f() {\n        try {\n            run();\n        } finally {\n            Runnable r = () -> { throw new IllegalStateException(); };\n        }\n    }\n}\n"]),
          "kotlin": dict(doc=dk("exceptions", "This rule reports all cases where exceptions are thrown from a finally block", "ThrowingExceptionFromFinally"),
                         eq=["detekt:ThrowingExceptionFromFinally"], query="(finally_block (block (throw_expression) @match))",
                         bad="fun f() {\n    try {\n        run()\n    } finally {\n        throw IllegalStateException(\"cleanup failed\")\n    }\n}\n",
                         good="fun f() {\n    try {\n        run()\n    } finally {\n        cleanup()\n    }\n}\n"),
      }, keys=["S1163"], cat="correctness", kind="anti-pattern", sev="major")

ONE_ITER = {
    "java": ("(_ body: (block (_) . [(return_statement) (break_statement) (throw_statement)] .)) @match", "for_statement|enhanced_for_statement|while_statement|do_statement",
             "class A {\n    String first(List<String> xs) {\n        for (String x : xs) {\n            log(x);\n            return x;\n        }\n        return null;\n    }\n}\n",
             "class A {\n    String first(List<String> xs) {\n        for (String x : xs) {\n            if (x.isEmpty()) {\n                continue;\n            }\n            return x;\n        }\n        return null;\n    }\n}\n"),
    "javascript": ("(_ body: (statement_block (_) . [(return_statement) (break_statement) (throw_statement)] .)) @match", "for_statement|for_in_statement|while_statement|do_statement",
                   "function first(xs) {\n  for (const x of xs) {\n    log(x);\n    return x;\n  }\n}\n",
                   "function first(xs) {\n  for (const x of xs) {\n    if (!x) {\n      continue;\n    }\n    return x;\n  }\n}\n"),
    "python": ("(_ body: (block (_) . [(return_statement) (break_statement) (raise_statement)] .)) @match", "for_statement|while_statement",
               "def first(xs):\n    for x in xs:\n        log(x)\n        return x\n", "def first(xs):\n    for x in xs:\n        if not x:\n            continue\n        return x\n"),
    "php": ("(_ body: (compound_statement (_) . [(return_statement) (break_statement) (expression_statement (throw_expression))] .)) @match", "for_statement|foreach_statement|while_statement|do_statement",
            "<?php\nfunction first($xs) {\n    foreach ($xs as $x) {\n        log($x);\n        return $x;\n    }\n}\n",
            "<?php\nfunction first($xs) {\n    foreach ($xs as $x) {\n        if (!$x) {\n            continue;\n        }\n        return $x;\n    }\n}\n"),
}
multi("LOOP-RUNS-ONCE", "Loop body always exits on the first iteration",
      "The loop body ends with an unconditional return/break/throw and never continues, so it runs at most once: use an if, or fix the "
      "misplaced exit.",
      {l: dict(doc={"java": (JLS14, "The enhanced for statement has the form", "JLS 14.14.2 The enhanced for statement"),
                    "javascript": es("no-unreachable-loop"), "python": (PYCOMPOUND, "The for statement is used to iterate over the elements of a sequence", "Python reference: The for statement"),
                    "php": (PHPM + "control-structures.foreach.php", "construct provides an easy way to iterate over", "PHP manual: foreach")}[l],
               eq={"javascript": ["eslint:no-unreachable-loop"]}.get(l, ()),
               query=q.replace("(_ body:", "(_ body:"), filters=["node.has_re:^(for|while|do|foreach)\\b",
                                                                   "node.lacks_re:\\bcontinue\\b"],
               bad=bad, good=good)
       for l, (q, kinds, bad, good) in ONE_ITER.items()}, keys=["S1751"], cat="correctness", kind="anti-pattern", sev="major",
      mode="ai-confirm", ai="Does the loop really never reach a second iteration (no continue, no labelled jump back)?")


ASSIGN = {"java": "assignment_expression", "javascript": "assignment_expression", "python": "assignment", "go": "assignment_statement",
          "kotlin": "assignment", "php": "assignment_expression"}
TYPO_EX = {
    "java": ("class A {\n    void f(int n) {\n        total =+ n;\n    }\n}\n", "class A {\n    void f(int n) {\n        total += n;\n    }\n}\n", "class A {\n    void f(int n) {\n        total = +n;\n    }\n}\n"),
    "javascript": ("function f(n) {\n  total =+ n;\n}\n", "function f(n) {\n  total += n;\n}\n", "function f(n) {\n  total = +n;\n}\n"),
    "python": ("def f(n):\n    total =- n\n", "def f(n):\n    total -= n\n", "def f(n):\n    total = -n\n"),
    "go": ("package p\n\nfunc f(n int) {\n\ttotal =- n\n}\n", "package p\n\nfunc f(n int) {\n\ttotal -= n\n}\n", "package p\n\nfunc f(n int) {\n\ttotal = -n\n}\n"),
    "kotlin": ("fun f(n: Int) {\n    total =+ n\n}\n", "fun f(n: Int) {\n    total += n\n}\n", "fun f(n: Int) {\n    total = +n\n}\n"),
    "php": ("<?php\nfunction f($n) {\n    $total =+ $n;\n}\n", "<?php\nfunction f($n) {\n    $total += $n;\n}\n", "<?php\nfunction f($n) {\n    $total = +$n;\n}\n"),
}
multi("REVERSED-COMPOUND-OPERATOR", "`=+` / `=-` / `=!` looks like a reversed compound assignment",
      "`x =+ y` assigns +y (it is not `x += y`); write the compound operator, or `x = +y` with the space after `=` if a plain "
      "assignment was meant.",
      {l: dict(doc={"java": ("https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html", "Compound Assignment Operators", "JLS 15.26.2 Compound Assignment Operators"),
                    "javascript": (MDN + "Operators/Addition_assignment", "The addition assignment (+=) operator", "MDN: Addition assignment"),
                    "python": ("https://docs.python.org/3/reference/simple_stmts.html", "Augmented assignment is the combination", "Python reference: Augmented assignment statements"),
                    "go": (GOSPEC, "where op is a binary arithmetic operator is equivalent to", "Go spec: Assignment statements"),
                    "kotlin": ("https://kotlinlang.org/docs/operator-overloading.html", "Augmented assignments", "Kotlin docs: Augmented assignments"),
                    "php": (PHPM + "language.operators.assignment.php", "combined operators", "PHP manual: Assignment operators")}[l],
               query=f"({ASSIGN[l]}) @match", filters=[r"node.has_re:^[^=\n]*[\w\])]\s+=[+\-" + ("" if l in ("python", "go") else "!") + r"](\s|[\w($])"],
               bad=v[0], good=v[1], fp=[v[2]])
       for l, v in TYPO_EX.items()}, keys=["S2757"], cat="correctness", kind="anti-pattern", sev="major")

SIZE_NEG = {
    "java": ("(binary_expression left: [(method_invocation name: (identifier) @m arguments: (argument_list) @args) (field_access field: (identifier) @m)] operator: [\"<\" \">=\"] right: (decimal_integer_literal) @z (#match? @m \"^(size|length)$\") (#eq? @z \"0\")) @match",
             "class A {\n    boolean f(List<String> xs) {\n        return xs.size() < 0;\n    }\n}\n", "class A {\n    boolean f(List<String> xs) {\n        return xs.isEmpty();\n    }\n}\n"),
    "javascript": ("(binary_expression left: (member_expression property: (property_identifier) @m) operator: [\"<\" \">=\"] right: (number) @z (#match? @m \"^(length|size)$\") (#eq? @z \"0\")) @match",
                   "function f(xs) {\n  return xs.length < 0;\n}\n", "function f(xs) {\n  return xs.length === 0;\n}\n"),
    "python": ("(comparison_operator (call function: (identifier) @m) [\"<\" \">=\"] (integer) @z (#eq? @m \"len\") (#eq? @z \"0\")) @match",
               "def f(xs):\n    return len(xs) < 0\n", "def f(xs):\n    return len(xs) == 0\n"),
    "kotlin": ("(binary_expression left: (_) @l right: (number_literal) @z (#match? @l \"\\\\.(size|length|count\\\\(\\\\))$\") (#eq? @z \"0\")) @match",
               "fun f(xs: List<String>): Boolean {\n    return xs.size < 0\n}\n", "fun f(xs: List<String>): Boolean {\n    return xs.isEmpty()\n}\n"),
    "php": ("(binary_expression left: (function_call_expression function: (name) @m) operator: [\"<\" \">=\"] right: (integer) @z (#match? @m \"^(count|sizeof|strlen|mb_strlen)$\") (#eq? @z \"0\")) @match",
            "<?php\nfunction f($xs) {\n    return count($xs) < 0;\n}\n", "<?php\nfunction f($xs) {\n    return count($xs) === 0;\n}\n"),
}
multi("SIZE-COMPARED-TO-NEGATIVE", "Size or length compared in a way that is always true or false",
      "A size/length is never negative, so `< 0` is always false and `>= 0` always true: compare with `== 0` / `> 0` or use isEmpty.",
      {l: dict(doc={"java": ("https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Collection.html", "Returns the number of elements in this collection", "Java SE 21 API: Collection.size"),
                    "javascript": (MDN + "Global_Objects/Array/length", "The value is an unsigned, 32-bit integer that is always numerically greater than the highest index in the array", "MDN: Array length"),
                    "python": ("https://docs.python.org/3/library/functions.html", "Return the length (the number of items) of an object", "Python docs: len"),
                    "kotlin": ("https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.collections/-collection/size.html", "Returns the size of the collection", "Kotlin stdlib: Collection.size"),
                    "php": (PHPM + "function.count.php", "Counts all elements in an array", "PHP manual: count")}[l],
               query=v[0], bad=v[1], good=v[2],
               filters=[r"node.has_re:(<|>=)\s*0\s*$"] if l == "kotlin" else None)
       for l, v in SIZE_NEG.items()}, keys=["S3981"], cat="correctness", kind="anti-pattern", sev="major")


# ---- unused declarations ----------------------------------------------------------------------------
# name occurrences are counted textually: a second occurrence anywhere (even in a string or a nested
# scope) counts as a use, so shadowing or reflection can only hide a finding, never create one
multi("UNUSED-LOCAL", "Local variable is never used",
      "This local variable is assigned but never read: remove it, or use it where it was meant to be used.",
      {
          "java": dict(doc=cs("coding/unusedlocalvariable", "Checks that a local variable is declared and/or assigned, but not used", "UnusedLocalVariable"),
                       eq=["checkstyle:UnusedLocalVariable"],
                       query="(local_variable_declaration declarator: (variable_declarator name: (identifier) @name) (#not-match? @name \"^(_|ignored?|unused)\")) @match",
                       filters=["func.count_lt:2:\\b{cap:name}\\b", "node.lacks_re:@SuppressWarnings\\(\\s*\\{?\\s*\"unused\""],
                       bad="class A {\n    int f(int a) {\n        int unusedSum = a + 1;\n        return a * 2;\n    }\n}\n".replace("unusedSum", "sum"),
                       good="class A {\n    int f(int a) {\n        int sum = a + 1;\n        return sum * 2;\n    }\n}\n"),
          "javascript": dict(doc=es("no-unused-vars"), eq=["eslint:no-unused-vars"],
                             query="(lexical_declaration (variable_declarator name: (identifier) @name) (#not-match? @name \"^_\")) @match",
                             filters=["node.has_ancestor:function_declaration|function_expression|arrow_function|method_definition|generator_function_declaration",
                                      "func.count_lt:2:(^|[^\\w$.]){cap:name}($|[^\\w$])", "func.lacks_re:\\beval\\("],
                             bad="function f(a) {\n  const sum = a + 1;\n  return a * 2;\n}\n", good="function f(a) {\n  const sum = a + 1;\n  return sum * 2;\n}\n",
                             fp=["const top = 1;\nexport { top };\n"]),
          "python": dict(doc=rf("unused-variable", "Checks for the presence of unused variables in function scopes", "F841"), eq=["ruff:F841"],
                         query="(expression_statement (assignment left: (identifier) @name) @match (#not-match? @name \"^_\"))",
                         # class bodies (a class declared inside a function) hold attributes, not locals; Python
                         # identifiers may be non-ASCII, so word boundaries are Unicode-aware; `x: int` alone binds nothing
                         filters=["node.has_ancestor:function_definition", r"ancestor.has_re:function_definition|class_definition:^(async\s+)?def\b",
                                  "node.has_re:=", "func.count_lt:2:(^|[^\\p{L}\\p{N}_]){cap:name}($|[^\\p{L}\\p{N}_])",
                                  "func.lacks_re:\\b(locals|vars|eval|exec)\\(|\\b(global|nonlocal)\\b"],
                         fp=["def t():\n    class Meta:\n        model = User\n    return Meta\n",
                             "def f(v):\n    \u00d8 = set()\n    return g(v, parens=\u00d8)\n",
                             "TOTAL = 1\n", "def f(a):\n    total = a + 1\n    return locals()\n"],
                         bad="def f(a):\n    total = a + 1\n    return a * 2\n", good="def f(a):\n    total = a + 1\n    return total * 2\n",
                         ),
          "kotlin": dict(doc=dk("style", "An unused variable can be removed to simplify the source file", "UnusedVariable"), eq=["detekt:UnusedVariable"],
                         query="(property_declaration (variable_declaration (identifier) @name) (#not-match? @name \"^_\")) @match",
                         filters=["node.has_ancestor:function_declaration|anonymous_function|lambda_literal", "func.count_lt:2:\\b{cap:name}\\b",
                                  "node.lacks_re:\\bby\\b",
                                  # members of local/anonymous classes are properties, not locals; `backticked` names defeat \\b
                                  "parentkind.lacks_re:class_body:.", "cap.lacks_re:name:^\x60",
                                  # modifiers locals cannot carry (guards against class members misparsed around ERROR nodes)
                                  r"node.lacks_re:^\s*(@(get|set|field|property|param|delegate)\s*:|(override|private|protected|public|internal|const|open|abstract)\b)"],
                         fp=[{"note": "anonymous object members and backticked names",
                              "code": "fun f() {\n    val t = object : Transformation {\n        override val cacheKey = \"k\"\n    }\n    use(t)\n    val `in` = open()\n    `in`.close()\n}\n"}],
                         bad="fun f(a: Int): Int {\n    val sum = a + 1\n    return a * 2\n}\n", good="fun f(a: Int): Int {\n    val sum = a + 1\n    return sum * 2\n}\n"),
          "php": dict(doc=md("unusedcode", "Detects when a local variable is declared and/or assigned, but not used", "UnusedLocalVariable"),
                      eq=["phpmd:UnusedLocalVariable"],
                      query="(expression_statement (assignment_expression left: (variable_name (name) @name)) @match (#not-match? @name \"^(_|this)$\"))",
                      filters=["node.has_ancestor:function_definition|method_declaration|anonymous_function",
                               "func.count_lt:2:\\${cap:name}\\b|['\"]{cap:name}['\"]",
                               "func.lacks_re:\\b(compact|extract|get_defined_vars|include|include_once|require|require_once|eval)\\b|\\$\\$|\\buse\\s*\\("],
                      bad="<?php\nfunction f($a) {\n    $sum = $a + 1;\n    return $a * 2;\n}\n", good="<?php\nfunction f($a) {\n    $sum = $a + 1;\n    return $sum * 2;\n}\n",
                      fp=["<?php\nfunction f($a) {\n    $sum = $a + 1;\n    return compact('sum');\n}\n"]),
      }, keys=["S1481"], mode="ai-confirm", ai="Is the variable really never read (no reflection, template, or dynamic access)?")

multi("UNUSED-PRIVATE-METHOD", "Private function is never called",
      "This private method is not referenced anywhere in the file: delete it, or call it where it was meant to be used.",
      {
          "java": dict(doc=("https://pmd.github.io/pmd/pmd_rules_java_bestpractices.html", "Unused Private Method detects when a private method is declared but is unused", "PMD UnusedPrivateMethod"),
                       eq=["pmd:UnusedPrivateMethod"],
                       query="(method_declaration (modifiers \"private\") name: (identifier) @name (#not-match? @name \"^(writeObject|readObject|readObjectNoData|writeReplace|readResolve)$\")) @match",
                       filters=["file.count_lt:2:\\b{cap:name}\\b", "node.lacks_re:^[^{(]*@\\w+"],
                       bad="class A {\n    int f() {\n        return 1;\n    }\n\n    private int helper() {\n        return 2;\n    }\n}\n",
                       good="class A {\n    int f() {\n        return helper();\n    }\n\n    private int helper() {\n        return 2;\n    }\n}\n",
                       fp=["class A {\n    @Bean\n    private Foo foo() {\n        return new Foo();\n    }\n}\n",
                           "class A implements Serializable {\n    private void readObject(ObjectInputStream in) {\n    }\n}\n"]),
          "kotlin": dict(doc=dk("style", "Reports unused private functions", "UnusedPrivateFunction"), eq=["detekt:UnusedPrivateFunction"],
                         query="(function_declaration (modifiers (visibility_modifier) @v) name: (identifier) @name (#eq? @v \"private\")) @match",
                         filters=["file.count_lt:2:\\b{cap:name}\\b", "node.lacks_re:^[^{(]*(@\\w+|\\boperator\\b)"],
                         bad="class A {\n    fun f() = 1\n\n    private fun helper() = 2\n}\n", good="class A {\n    fun f() = helper()\n\n    private fun helper() = 2\n}\n"),
          "php": dict(doc=md("unusedcode", "private method is declared but is unused", "UnusedPrivateMethod"), eq=["phpmd:UnusedPrivateMethod"],
                      query="(method_declaration (visibility_modifier) @v name: (name) @name (#eq? @v \"private\") (#not-match? @name \"^__\")) @match",
                      filters=["file.count_lt:2:\\b{cap:name}\\b", "node.lacks_re:#\\["],
                      bad="<?php\nclass A {\n    public function f() {\n        return 1;\n    }\n\n    private function helper() {\n        return 2;\n    }\n}\n",
                      good="<?php\nclass A {\n    public function f() {\n        return $this->helper();\n    }\n\n    private function helper() {\n        return 2;\n    }\n}\n"),
          "python": dict(doc=("https://docs.python.org/3/tutorial/classes.html", "Private Variables", "Python tutorial: Private Variables"),
                         query="(class_definition body: (block (function_definition name: (identifier) @name (#match? @name \"^__[A-Za-z0-9_]*[A-Za-z0-9]_?$\")) @match))",
                         filters=["file.count_lt:2:\\b{cap:name}\\b"],
                         bad="class A:\n    def f(self):\n        return 1\n\n    def __helper(self):\n        return 2\n",
                         good="class A:\n    def f(self):\n        return self.__helper()\n\n    def __helper(self):\n        return 2\n",
                         fp=["class A:\n    def __init__(self):\n        pass\n"]),
      }, keys=["S1144"], mode="ai-confirm", ai="Is the private function unreferenced (no reflection, framework callback, or string reference)?")

multi("UNUSED-PARAMETER", "Parameter of a private function is never used",
      "This parameter is never used inside the function: remove it from the private signature (callers are all in this file).",
      {
          "java": dict(doc=("https://pmd.github.io/pmd/pmd_rules_java_bestpractices.html", "Reports parameters of methods and constructors that are not referenced them in the method body", "PMD UnusedFormalParameter"),
                       eq=["pmd:UnusedFormalParameter"],
                       query="(method_declaration (modifiers \"private\") name: (identifier) @mname parameters: (formal_parameters (formal_parameter name: (identifier) @name) @match) body: (block))",
                       filters=["func.count_lt:2:\\b{cap:name}\\b", "file.count_lt:1:::\\s*{cap:mname}\\b", "ancestor.lacks_re:method_declaration:^[^{(]*@\\w+|\\b(writeObject|readObject)\\s*\\("],
                       bad="class A {\n    private int scale(int value, int factor) {\n        return value * 2;\n    }\n}\n",
                       good="class A {\n    private int scale(int value, int factor) {\n        return value * factor;\n    }\n}\n"),
          "kotlin": dict(doc=dk("style", "An unused parameter can be removed to simplify the signature of the function", "UnusedParameter"), eq=["detekt:UnusedParameter"],
                         query="(function_declaration (modifiers (visibility_modifier) @v) (function_value_parameters (parameter (identifier) @name) @match) (function_body) (#eq? @v \"private\") (#not-match? @name \"^_\"))",
                         filters=["func.count_lt:2:\\b{cap:name}\\b", "ancestor.lacks_re:function_declaration:^[^{(]*(@\\w+|\\boperator\\b)"],
                         bad="private fun scale(value: Int, factor: Int): Int {\n    return value * 2\n}\n",
                         good="private fun scale(value: Int, factor: Int): Int {\n    return value * factor\n}\n"),
          "php": dict(doc=md("unusedcode", "Avoid passing parameters to methods or constructors and then not using those parameters", "UnusedFormalParameter"),
                      eq=["phpmd:UnusedFormalParameter"],
                      query="(method_declaration (visibility_modifier) @v parameters: (formal_parameters (simple_parameter name: (variable_name (name) @name)) @match) body: (compound_statement) (#eq? @v \"private\"))",
                      filters=["func.count_lt:2:\\${cap:name}\\b", "func.lacks_re:\\bfunc_get_args\\b|\\bcompact\\("],
                      bad="<?php\nclass A {\n    private function scale($value, $factor) {\n        return $value * 2;\n    }\n}\n",
                      good="<?php\nclass A {\n    private function scale($value, $factor) {\n        return $value * $factor;\n    }\n}\n"),
      }, keys=["S1172"], mode="ai-confirm", ai="Is the parameter unused and not required by a callback or interface signature?")


KT_OPERATOR_NAMES = ("getValue|setValue|provideDelegate|invoke|plus|minus|times|div|rem|contains|get|set|iterator|next|hasNext|compareTo|"
                     "unaryMinus|unaryPlus|not|inc|dec|rangeTo|rangeUntil|component\\d+|plusAssign|minusAssign|timesAssign|divAssign|remAssign|equals")
multi("UNUSED-IMPORT", "Import is never used",
      "Nothing in this file refers to the imported name: remove the import.",
      {
          "java": dict(doc=cs("imports/unusedimports", "Checks for unused import statements", "UnusedImports"), eq=["checkstyle:UnusedImports"],
                       query="(import_declaration (scoped_identifier name: (identifier) @name)) @match",
                       filters=["node.lacks_re:^import\\s+static\\b", "file.count_lt:2:\\b{cap:name}\\b", "node.lacks_re:\\*\\s*;"],
                       bad="import java.util.List;\nimport java.util.Map;\n\nclass A {\n    List<String> xs;\n}\n",
                       good="import java.util.List;\n\nclass A {\n    List<String> xs;\n}\n",
                       fp=["import java.util.Map;\n\n/** Builds a {@link Map}. */\nclass A {\n}\n", "import java.sql.*;\n\nclass A {\n    Connection c;\n}\n"]),
          "kotlin": dict(doc=dk("style", "This rule reports unused imports", "UnusedImport"), eq=["detekt:UnusedImport"],
                         query="(import (qualified_identifier (identifier) @name .) . ) @match",
                         # star imports and `backticked` names (word boundaries do not apply) are skipped;
                         # Gradle's assignment plugin uses the imported `assign` operator implicitly for =
                         filters=["file.count_lt:2:\\b{cap:name}\\b", f"cap.lacks_re:name:^({KT_OPERATOR_NAMES}|assign)$",
                                  "cap.lacks_re:name:^\x60", "node.lacks_re:\\*\\s*$"],
                         bad="import a.b.Foo\nimport a.b.Bar\n\nval x = Foo()\n", good="import a.b.Foo\n\nval x = Foo()\n",
                         fp=["import a.b.getValue\n\nval x by lazy { 1 }\n",
                             {"note": "star, backtick and Gradle assign imports", "code": "import io.ktor.server.application.*\nimport org.mockito.Mockito.`when`\nimport org.gradle.kotlin.dsl.assign\n\nfun f() { `when`(x) }\n"}]),
          "javascript": dict(doc=es("no-unused-vars"), eq=["eslint:no-unused-vars", "typescript-eslint:no-unused-vars"],
                             query="[(import_specifier alias: (identifier) @name) (import_specifier name: (identifier) @name !alias) (import_clause (identifier) @name) (namespace_import (identifier) @name)] @match",
                             filters=["file.count_lt:2:(^|[^\\w$.]){cap:name}($|[^\\w$])", "cap.lacks_re:name:^(React|h|_)$"],
                             files=["**/*.js", "**/*.mjs", "**/*.cjs", "**/*.jsx", "**/*.ts", "**/*.mts", "**/*.cts", "**/*.tsx"],
                             bad="import { readFile, writeFile } from \"node:fs\";\n\nexport function load(p) {\n  return readFile(p);\n}\n",
                             good="import { readFile } from \"node:fs\";\n\nexport function load(p) {\n  return readFile(p);\n}\n",
                             fp=["import React from \"react\";\n\nexport const A = () => <div />;\n"]),
      }, keys=["S1128"])

multi("UNUSED-PRIVATE-FIELD", "Private field is never read",
      "Nothing in this class reads the private field: remove it, or use it where it was meant to be used.",
      {
          "java": dict(doc=("https://pmd.github.io/pmd/pmd_rules_java_bestpractices.html", "Detects when a private field is declared and/or assigned a value, but not used", "PMD UnusedPrivateField"),
                       eq=["pmd:UnusedPrivateField"],
                       query="(field_declaration (modifiers \"private\") declarator: (variable_declarator name: (identifier) @name) (#not-match? @name \"^(serialVersionUID|serialPersistentFields)$\")) @match",
                       filters=["file.count_lt:2:\\b{cap:name}\\b", "node.lacks_re:@\\w+",
                                "file.lacks_re:\\blombok\\b|@(Getter|Setter|Data|Value|Builder|ToString|EqualsAndHashCode)\\b"],
                       bad="class A {\n    private int retries;\n\n    void run() {\n        call();\n    }\n}\n",
                       good="class A {\n    private int retries;\n\n    void run() {\n        call(retries);\n    }\n}\n",
                       fp=["@Getter\nclass A {\n    private int retries;\n}\n", "class A {\n    @Inject\n    private Service service;\n}\n"]),
          "php": dict(doc=md("unusedcode", "private field is declared and/or assigned a value, but not used", "UnusedPrivateField"), eq=["phpmd:UnusedPrivateField"],
                      query="(property_declaration (visibility_modifier) @v (property_element name: (variable_name (name) @name)) (#eq? @v \"private\")) @match",
                      filters=["file.count_lt:2:\\b{cap:name}\\b", "node.lacks_re:#\\[|@ORM\\\\|@var\\s",
                               "file.lacks_re:function\\s+(__get|__set|__serialize|__sleep|toArray)\\b|ReflectionProperty|get_object_vars"],
                      bad="<?php\nclass A {\n    private $retries;\n\n    public function run() {\n        call();\n    }\n}\n",
                      good="<?php\nclass A {\n    private $retries;\n\n    public function run() {\n        call($this->retries);\n    }\n}\n"),
      }, keys=["S1068"], mode="ai-confirm", ai="Is the field unused (no reflection, serialization or framework injection)?")

# ---- exceptions -----------------------------------------------------------------------------------
multi("GENERIC-EXCEPTION-THROWN", "Generic exception type thrown",
      "Throwing the most generic exception type forces callers to catch everything; throw a specific (or custom) exception type.",
      {
          "java": dict(doc=("https://docs.oracle.com/javase/tutorial/essential/exceptions/creating.html", "You should write your own exception classes", "Java Tutorials: Creating Exception Classes"),
                       query="(throw_statement (object_creation_expression type: (type_identifier) @t (#match? @t \"^(Exception|RuntimeException|Throwable|Error)$\"))) @match",
                       bad="class A {\n    void load(String p) {\n        if (p == null) {\n            throw new RuntimeException(\"no path\");\n        }\n    }\n}\n",
                       good="class A {\n    void load(String p) {\n        if (p == null) {\n            throw new IllegalArgumentException(\"no path\");\n        }\n    }\n}\n",
                       files=["!**/src/test/**", "!**/*Test.java", "!**/*Tests.java"]),
          "python": dict(doc=rf("raise-vanilla-class", "Checks for code that raises Exception or BaseException directly", "TRY002"), eq=["ruff:TRY002"],
                         query="(raise_statement [(call function: (identifier) @t) (identifier) @t] (#match? @t \"^(Exception|BaseException)$\")) @match",
                         bad="def load(p):\n    if not p:\n        raise Exception(\"no path\")\n", good="def load(p):\n    if not p:\n        raise ValueError(\"no path\")\n",
                         files=["!**/tests/**", "!**/test_*.py", "!**/*_test.py"]),
          "php": dict(doc=(PHPM + "class.exception.php", "is the base class for all user exceptions", "PHP manual: Exception"),
                      # an unqualified name resolves in the current namespace (PHPMailer\\PHPMailer\\Exception): only the global
                      # class is generic, so a bare name needs `use Exception;` (or no namespace declaration at all)
                      query="(throw_expression (object_creation_expression (qualified_name) @q (#match? @q \"^\\\\\\\\(Exception|Error)$\"))) @match\n"
                            "(throw_expression (object_creation_expression (name) @u (#match? @u \"^(Exception|Error)$\"))) @match",
                      filters=[r"file.has_re:(?m)^use\s+\\?{cap:u}\s*;|{cap:q}|\A(?s:[^n]|n[^a]|na[^m]|nam[^e])*\z"],
                      fp=["<?php\nnamespace PHPMailer\\PHPMailer;\n\nfunction f() {\n    throw new Exception('smtp failed');\n}\n"],
                      bad="<?php\nfunction load($p) {\n    if (!$p) {\n        throw new \\Exception('no path');\n    }\n}\n",
                      good="<?php\nfunction load($p) {\n    if (!$p) {\n        throw new \\InvalidArgumentException('no path');\n    }\n}\n",
                      files=["!**/tests/**", "!**/Tests/**", "!**/*Test.php"]),
      }, keys=["S112"])

multi("CATCH-THROWABLE", "Catching Throwable or Error",
      "Catching Throwable/Error also traps JVM failures such as OutOfMemoryError that the code cannot recover from: catch Exception "
      "or the specific types instead.",
      {"java": dict(doc=cs("coding/illegalcatch", "Checks that certain exception types do not appear in a", "IllegalCatch"), eq=["checkstyle:IllegalCatch"],
                    query="(catch_clause (catch_formal_parameter (catch_type (type_identifier) @t) (#match? @t \"^(Throwable|Error)$\"))) @match",
                    bad="class A {\n    void f() {\n        try {\n            run();\n        } catch (Throwable t) {\n            log(t);\n        }\n    }\n}\n",
                    good="class A {\n    void f() {\n        try {\n            run();\n        } catch (Exception e) {\n            log(e);\n        }\n    }\n}\n",
                    fp=["class A {\n    void f() {\n        try {\n            run();\n        } catch (Throwable t) {\n            log(t);\n            throw t;\n        }\n    }\n}\n"],
                    filters=["node.lacks_re:\\bthrow\\b"])}, keys=["S1181"], cat="correctness")

multi("CATCH-ONLY-RETHROWS", "catch clause only rethrows the exception",
      "The last catch clause only rethrows what it caught, which is what happens without it: remove the clause (or add the handling it "
      "was meant to have).",
      {
          "java": dict(doc=(JLS14, "If execution of the try block completes abruptly because of a throw of a value V", "JLS 14.20 The try statement"), filters=["cap.has_re:t:^{cap:e}$"],
                       query="[(try_statement (catch_clause (catch_formal_parameter name: (identifier) @e) body: (block . (throw_statement (identifier) @t) .)) @match .) (try_statement (catch_clause (catch_formal_parameter name: (identifier) @e) body: (block . (throw_statement (identifier) @t) .)) @match . (finally_clause) .)]",
                       bad="class A {\n    void f() throws IOException {\n        try {\n            load();\n        } catch (IOException e) {\n            throw e;\n        }\n    }\n}\n",
                       good="class A {\n    void f() throws IOException {\n        load();\n    }\n}\n",
                       fp=["class A {\n    void f() {\n        try {\n            load();\n        } catch (IOException e) {\n            throw e;\n        } catch (Exception e) {\n            log(e);\n        }\n    }\n}\n"]),
          "python": dict(doc=rf("useless-try-except", "Checks for immediate uses of raise within exception handlers", "TRY203"), eq=["ruff:TRY203"],
                         query="[(try_statement (except_clause (block . (raise_statement !cause) .)) @match .) (try_statement (except_clause (block . (raise_statement !cause) .)) @match . (else_clause) .) (try_statement (except_clause (block . (raise_statement !cause) .)) @match . (finally_clause) .) (try_statement (except_clause (block . (raise_statement !cause) .)) @match . (else_clause) . (finally_clause) .)]",
                         filters=["node.has_re:(?s)^except\\b[^:]*:\\s*raise(\\s+\\w+)?\\s*$"],
                         bad="def f():\n    try:\n        load()\n    except OSError:\n        raise\n", good="def f():\n    load()\n",
                         fp=["def f():\n    try:\n        load()\n    except KeyError:\n        raise\n    except Exception:\n        log()\n"]),
          "php": dict(doc=(PHPM + "class.exception.php", "is the base class for all user exceptions", "PHP manual: Exception"),
                      query="[(try_statement (catch_clause name: (variable_name) @e body: (compound_statement . (expression_statement (throw_expression (variable_name) @t)) .)) @match .) (try_statement (catch_clause name: (variable_name) @e body: (compound_statement . (expression_statement (throw_expression (variable_name) @t)) .)) @match . (finally_clause) .)]",
                      filters=["cap.has_re:t:^{cap:e}$"],
                      fp=["<?php\nfunction f() {\n    try {\n        load();\n    } catch (KeyError $e) {\n        throw $e;\n    } catch (Exception $e) {\n        log($e);\n    }\n}\n"],
                      bad="<?php\nfunction f() {\n    try {\n        load();\n    } catch (Exception $e) {\n        throw $e;\n    }\n}\n",
                      good="<?php\nfunction f() {\n    load();\n}\n"),
      }, keys=["S2737"])


# ---- switch hygiene ---------------------------------------------------------------------------
multi("DEFAULT-NOT-LAST", "default clause is not the last one",
      "Put the default clause last: readers expect it there, and a default in the middle hides the cases after it.",
      {
          "java": dict(doc=cs("coding/defaultcomeslast", "Check that the", "DefaultComesLast"), eq=["checkstyle:DefaultComesLast"],
                       query="(switch_block [(switch_block_statement_group . (switch_label) @l) (switch_rule . (switch_label) @l)] @match . [(switch_block_statement_group) (switch_rule)] (#eq? @l \"default\"))",
                       bad="class A {\n    void f(int n) {\n        switch (n) {\n            default:\n                other();\n                break;\n            case 1:\n                one();\n                break;\n        }\n    }\n}\n",
                       good="class A {\n    void f(int n) {\n        switch (n) {\n            case 1:\n                one();\n                break;\n            default:\n                other();\n        }\n    }\n}\n"),
          "php": dict(doc=(PHPSWITCH, "similar to a series of IF statements", "PHP manual: switch"),
                      query="(switch_block (default_statement) @match . (case_statement))",
                      bad="<?php\nswitch ($n) {\n    default:\n        other();\n        break;\n    case 1:\n        one();\n        break;\n}\n",
                      good="<?php\nswitch ($n) {\n    case 1:\n        one();\n        break;\n    default:\n        other();\n}\n"),
      }, keys=["S4524"])

multi("SWITCH-WITHOUT-DEFAULT", "switch statement has no default clause",
      "Without a default clause, unexpected values fall through silently: add one (even if it only throws or logs).",
      {
          "java": dict(doc=cs("coding/missingswitchdefault", "Checks that switch statement has a", "MissingSwitchDefault"), eq=["checkstyle:MissingSwitchDefault"],
                       query="(switch_expression body: (switch_block) @b) @match",
                       filters=["parentkind.has_re:block|switch_block_statement_group:.", "cap.lacks_re:b:\\bdefault\\b", "cap.lacks_re:b:->"],
                       bad="class A {\n    void f(int n) {\n        switch (n) {\n            case 1:\n                one();\n                break;\n        }\n    }\n}\n",
                       good="class A {\n    void f(int n) {\n        switch (n) {\n            case 1:\n                one();\n                break;\n            default:\n                other();\n        }\n    }\n}\n",
                       fp=["class A {\n    int f(int n) {\n        return switch (n) {\n            case 1 -> 1;\n            default -> 0;\n        };\n    }\n}\n"]),
          "php": dict(doc=(PHPSWITCH, "similar to a series of IF statements", "PHP manual: switch"),
                      query="(switch_statement body: (switch_block) @b) @match", filters=["cap.lacks_re:b:\\bdefault\\s*:"],
                      bad="<?php\nswitch ($n) {\n    case 1:\n        one();\n        break;\n}\n",
                      good="<?php\nswitch ($n) {\n    case 1:\n        one();\n        break;\n    default:\n        other();\n}\n"),
      }, keys=["S131"], mode="ai-confirm", ai="Can the switched value take values not covered by the cases (not an exhaustive enum/sealed set)?")

# ---- small simplifications ----------------------------------------------------------------------
multi("RETURNS-SAME-VALUE", "Every return gives the same value",
      "All return statements of this function return the same literal, so callers cannot learn anything from the result: return void "
      "or fix the branch that should differ.",
      {l: dict(doc=d, query=FUNC[l], filters=["func.returns_invariant"],
               bad=fn(l, [("if", "a", ["g()", "return 1"]), "h()", "return 1"], "a", ret=False),
               good=fn(l, [("if", "a", ["g()", "return 1"]), "h()", "return 0"], "a", ret=False))
       for l, d in [("java", (JLS14, "A return statement returns control to the invoker of a method", "JLS 14.17 The return statement")),
                    ("javascript", (MDN + "Statements/return", "The return statement ends function execution", "MDN: return")),
                    ("python", (PYSIMPLE, "return leaves the current function call", "Python reference: The return statement")),
                    ("php", (PHPM + "function.return.php", "returns program control to the calling module", "PHP manual: return"))]},
      keys=["S3516"], cat="correctness", mode="ai-confirm", ai="Is returning the same value on every path a mistake (not a fixed status/hook contract)?")

multi("IMMEDIATELY-RETURNED-VARIABLE", "Local variable is returned right after it is assigned",
      "The variable only carries the value to the next line's return: return the expression directly.",
      {
          "java": dict(doc=(JLS14, "A return statement returns control to the invoker of a method", "JLS 14.17 The return statement"),
                       query="(block (local_variable_declaration declarator: (variable_declarator name: (identifier) @v value: (_))) @match . (return_statement (identifier) @r) (#eq? @v @r))",
                       filters=["node.lacks_re:@\\w+"],
                       bad="class A {\n    int f(int a) {\n        int doubled = a * 2;\n        return doubled;\n    }\n}\n",
                       good="class A {\n    int f(int a) {\n        return a * 2;\n    }\n}\n"),
          "python": dict(doc=rf("unnecessary-assign", "Checks for variable assignments that immediately precede a return of the assigned variable", "RET504"), eq=["ruff:RET504"],
                         query="(block (expression_statement (assignment left: (identifier) @v !type)) @match . (return_statement (identifier) @r) (#eq? @v @r))",
                         filters=["func.lacks_re:\\b(global|nonlocal|locals)\\b"],
                         bad="def f(a):\n    doubled = a * 2\n    return doubled\n", good="def f(a):\n    return a * 2\n"),
          "php": dict(doc=(PHPM + "function.return.php", "returns program control to the calling module", "PHP manual: return"),
                      query="(compound_statement (expression_statement (assignment_expression left: (variable_name) @v)) @match . (return_statement (variable_name) @r) (#eq? @v @r))",
                      # an @var docblock narrows the type for static analysers; return-by-reference (function &f) needs a variable
                      filters=[r"func.lacks_re:@var\s+\S+\s+{cap:v}\b", r"func.lacks_re:^[^{(]*\bfunction\s*&"],
                      fp=["<?php\nfunction f($p) {\n    /** @var resource $r */\n    $r = open($p);\n    return $r;\n}\n",
                          "<?php\nclass A {\n    public function &offsetGet($o) {\n        $copy = $this->level;\n        return $copy;\n    }\n}\n"],
                      bad="<?php\nfunction f($a) {\n    $doubled = $a * 2;\n    return $doubled;\n}\n", good="<?php\nfunction f($a) {\n    return $a * 2;\n}\n"),
      }, keys=["S1488"])

multi("SIZE-INSTEAD-OF-ISEMPTY", "size()/length() compared with zero instead of isEmpty()",
      "Use isEmpty(): it states the intent and is constant-time for every collection.",
      {"java": dict(doc=("https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Collection.html", "Returns true if this collection contains no elements", "Java SE 21 API: Collection.isEmpty"),
                    query="(binary_expression left: (method_invocation object: (_) @recv name: (identifier) @m arguments: (argument_list) @args) operator: [\"==\" \"!=\" \">\"] right: (decimal_integer_literal) @z (#match? @m \"^(size|length)$\") (#match? @args \"^\\\\(\\\\s*\\\\)$\") (#eq? @z \"0\")) @match",
                    bad="class A {\n    boolean f(List<String> xs) {\n        return xs.size() == 0;\n    }\n}\n", good="class A {\n    boolean f(List<String> xs) {\n        return xs.isEmpty();\n    }\n}\n",
                    filters=[r"type.not_or_unknown:recv:.*(StringBuilder|StringBuffer|CharSequence|Builder|Writer|OutputStream)\b.*", r"cap.lacks_re:recv:(?i)(sb|buf|buffer|builder|out|accum)$",
                             # corpus: CharSequence.isEmpty() needs Java 15; a cast or a <T extends CharSequence> receiver is not a String
                             r"cap.lacks_re:recv:\bCharSequence\b", r"func.lacks_re:\bextends\s+CharSequence\b"],
                    fp=["class A {\n    String f(StringBuilder sb) {\n        return sb.length() > 0 ? sb.toString() : null;\n    }\n}\n",
                        # corpus (jsoup, jackson): ByteArrayOutputStream has size() but no isEmpty()
                        "class A {\n    private final ByteArrayOutputStream body = new ByteArrayOutputStream();\n    byte[] f() {\n        ByteArrayOutputStream bytes = new ByteArrayOutputStream();\n        if (bytes.size() == 0 || body.size() > 0) {\n            throw new IllegalStateException();\n        }\n        return bytes.toByteArray();\n    }\n}\n",
                        "class A {\n    boolean f(Object o) {\n        return ((CharSequence) o).length() == 0;\n    }\n    <T extends CharSequence> T g(T chars) {\n        if (chars.length() == 0) {\n            throw new IllegalArgumentException();\n        }\n        return chars;\n    }\n}\n"],
                    mode="ai-confirm", ai="Does the receiver type have an isEmpty() method (Collection, String, Map...)?")}, keys=["S1155"])

PURE = "^(trim|strip|stripLeading|stripTrailing|toUpperCase|toLowerCase|substring|concat|replace|replaceAll|isBlank|isEmpty|equalsIgnoreCase|startsWith|endsWith|matches|repeat)$"
multi("IGNORED-RESULT", "Result of a side-effect-free call is discarded",
      "This call returns a new value and changes nothing; discarding the result means the statement has no effect: assign or use it.",
      {
          "java": dict(doc=("https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/String.html", "Strings are constant; their values cannot be changed after they are created", "Java SE 21 API: String"),
                       query=f"(expression_statement (method_invocation object: (_) @recv name: (identifier) @m (#match? @m \"{PURE}\"))) @match",
                       filters=["file.lacks_re:\\bStringBuilder\\b|\\bStringBuffer\\b", "type.is:recv:String"],
                       fp=["class A {\n    void f(List<String> xs) {\n        assertThat(xs).isEmpty();\n    }\n}\n", "class A {\n    void f(ArrayNode array) {\n        array.replace(100, null);\n    }\n}\n"],
                       bad="class A {\n    void f(String s) {\n        s.trim();\n        use(s);\n    }\n}\n", good="class A {\n    void f(String s) {\n        s = s.trim();\n        use(s);\n    }\n}\n"),
          "javascript": dict(doc=(MDN + "Global_Objects/String/trim", "returns a new string", "MDN: String.prototype.trim"),
                             query="(expression_statement (call_expression function: (member_expression property: (property_identifier) @m (#match? @m \"^(trim|trimStart|trimEnd|toUpperCase|toLowerCase|padStart|padEnd|concat|toSorted|toReversed|toSpliced)$\")))) @match",
                             bad="function f(s) {\n  s.trim();\n  use(s);\n}\n", good="function f(s) {\n  const t = s.trim();\n  use(t);\n}\n"),
          "python": dict(doc=("https://docs.python.org/3/library/stdtypes.html", "Return a copy of the string with the leading and trailing characters removed", "Python docs: str.strip"),
                         query="(expression_statement [(call function: (attribute object: (_) @recv attribute: (identifier) @m)) (call function: (identifier) @m)] (#match? @m \"^(strip|lstrip|rstrip|upper|lower|casefold|title|capitalize|swapcase|removeprefix|removesuffix|zfill|sorted)$\")) @match",
                         filters=[r"type.is:recv:str|bytes"],
                         bad="def f(s: str):\n    s.strip()\n    use(s)\n", good="def f(s: str):\n    s = s.strip()\n    use(s)\n",
                         fp=["from rich.text import Text\n\ndef f():\n    t = Text(\"x \")\n    t.rstrip()\n    return t\n"]),
      }, keys=["S2201"], cat="correctness", kind="anti-pattern", sev="major")

multi("PARAMETER-REASSIGNED", "Parameter is overwritten before it is read",
      "The parameter is assigned a new value before its incoming value is used, so the caller's argument is ignored: use a new local "
      "variable or remove the parameter.",
      {
          "java": dict(doc=cs("coding/parameterassignment", "Disallows assignment of parameters", "ParameterAssignment"), eq=["checkstyle:ParameterAssignment"],
                       query="(method_declaration parameters: (formal_parameters (formal_parameter name: (identifier) @p)) body: (block . (expression_statement (assignment_expression left: (identifier) @l operator: \"=\" right: (_) @r))) (#eq? @p @l)) @match",
                       filters=["cap.lacks_re:r:\\b{cap:p}\\b"],
                       bad="class A {\n    int f(int limit) {\n        limit = 10;\n        return limit * 2;\n    }\n}\n",
                       good="class A {\n    int f(int limit) {\n        int max = Math.min(limit, 10);\n        return max * 2;\n    }\n}\n",
                       fp=["class A {\n    int f(int limit) {\n        limit = Math.min(limit, 10);\n        return limit;\n    }\n}\n"]),
          "python": dict(doc=rf("redefined-argument-from-local", "Checks for variables defined in for, try, with statements that redefine function parameters", "PLR1704"),
                         query="(function_definition parameters: (parameters (identifier) @p) body: (block . (expression_statement (assignment left: (identifier) @l right: (_) @r)) ) (#eq? @p @l)) @match",
                         filters=["cap.lacks_re:r:\\b{cap:p}\\b"],
                         bad="def f(limit):\n    limit = 10\n    return limit * 2\n", good="def f(limit):\n    return min(limit, 10) * 2\n",
                         fp=["def f(limit):\n    limit = min(limit, 10)\n    return limit\n"]),
          "php": dict(doc=(PHPM + "functions.arguments.php", "Information may be passed to functions via the argument list", "PHP manual: Function arguments"),
                      query="[(function_definition parameters: (formal_parameters (simple_parameter !reference_modifier name: (variable_name) @p)) body: (compound_statement . (expression_statement (assignment_expression left: (variable_name) @l right: (_) @r))) (#eq? @p @l)) (method_declaration parameters: (formal_parameters (simple_parameter !reference_modifier name: (variable_name) @p)) body: (compound_statement . (expression_statement (assignment_expression left: (variable_name) @l right: (_) @r))) (#eq? @p @l))] @match",
                      filters=["cap.lacks_re:r:{cap:p}\\b"],
                      bad="<?php\nfunction f($limit) {\n    $limit = 10;\n    return $limit * 2;\n}\n", good="<?php\nfunction f($limit) {\n    return min($limit, 10) * 2;\n}\n",
                      fp=["<?php\nfunction parse(string $v, ?bool &$isFips): ?string {\n    $isFips = false;\n    return $v;\n}\n"]),
      }, keys=["S1226"], cat="correctness", kind="anti-pattern", sev="major")

multi("NEGATED-EQUALITY", "Negated equality check",
      "`!(a == b)` reads worse than `a != b`; use the opposite operator.",
      {
          "java": dict(doc=cs("coding/simplifybooleanexpression", "Checks for over-complicated boolean expressions", "SimplifyBooleanExpression"),
                       query="(unary_expression operator: \"!\" operand: (parenthesized_expression (binary_expression operator: [\"==\" \"!=\"]))) @match",
                       bad="class A {\n    boolean f(int a, int b) {\n        return !(a == b);\n    }\n}\n", good="class A {\n    boolean f(int a, int b) {\n        return a != b;\n    }\n}\n"),
          "javascript": dict(doc=(MDN + "Operators/Inequality", "The inequality (!=) operator checks whether its two operands are not equal", "MDN: Inequality"),
                             query="(unary_expression operator: \"!\" argument: (parenthesized_expression (binary_expression operator: [\"==\" \"!=\" \"===\" \"!==\"]))) @match",
                             bad="function f(a, b) {\n  return !(a === b);\n}\n", good="function f(a, b) {\n  return a !== b;\n}\n"),
          "python": dict(doc=rf("negate-equal-op", "Checks for negated == operators", "SIM201"), eq=["ruff:SIM201", "ruff:SIM202"],
                         query="(not_operator argument: [(comparison_operator [\"==\" \"!=\"]) (parenthesized_expression (comparison_operator [\"==\" \"!=\"]))]) @match",
                         filters=["node.lacks_re:__(eq|ne)__"],
                         bad="def f(a, b):\n    return not a == b\n", good="def f(a, b):\n    return a != b\n"),
          "go": dict(doc=(GOSPEC, "Comparison operators compare two operands and yield an untyped boolean value", "Go spec: Comparison operators"),
                     query="(unary_expression operator: \"!\" operand: (parenthesized_expression (binary_expression operator: [\"==\" \"!=\"]))) @match",
                     bad="package p\n\nfunc f(a, b int) bool {\n\treturn !(a == b)\n}\n", good="package p\n\nfunc f(a, b int) bool {\n\treturn a != b\n}\n"),
          "kotlin": dict(doc=("https://kotlinlang.org/docs/equality.html", "Structural equality", "Kotlin docs: Equality"),
                         query="(unary_expression argument: (parenthesized_expression (binary_expression)) @x) @match",
                         filters=["node.has_re:^!\\s*\\(", "cap.has_re:x:^\\([^()]*[^=!<>]={2,3}[^=]|^\\([^()]*!={1,2}[^=]"],
                         bad="fun f(a: Int, b: Int): Boolean {\n    return !(a == b)\n}\n", good="fun f(a: Int, b: Int): Boolean {\n    return a != b\n}\n"),
          "php": dict(doc=(PHPM + "language.operators.comparison.php", "Comparison operators, as their name implies", "PHP manual: Comparison operators"),
                      query="(unary_op_expression (parenthesized_expression (binary_expression operator: [\"==\" \"!=\" \"===\" \"!==\"]))) @match",
                      filters=["node.has_re:^!"],
                      bad="<?php\nfunction f($a, $b) {\n    return !($a === $b);\n}\n", good="<?php\nfunction f($a, $b) {\n    return $a !== $b;\n}\n"),
      }, keys=["S1940"])

multi("REDUNDANT-PARENTHESES", "Doubled parentheses",
      "The extra pair of parentheses adds nothing: remove it.",
      {l: dict(doc=d, query="(parenthesized_expression . (parenthesized_expression) .) @match", bad=b, good=g,
               filters=["parentkind.lacks_re:parenthesized_expression:."])  # one hit for ((((x)))), on the outermost pair
       for l, d, b, g in [
           ("java", cs("coding/unnecessaryparentheses", "Checks if unnecessary parentheses are used", "UnnecessaryParentheses"),
            "class A {\n    int f(int a) {\n        return ((a + 1)) * 2;\n    }\n}\n", "class A {\n    int f(int a) {\n        return (a + 1) * 2;\n    }\n}\n"),
           ("python", (PYCOMPOUND, "The if statement is used for conditional execution", "Python reference: The if statement"),
            "def f(a):\n    return ((a + 1)) * 2\n", "def f(a):\n    return (a + 1) * 2\n"),
           ("go", (GOSPEC, "Operands may be parenthesized", "Go spec: Operands"),
            "package p\n\nfunc f(a int) int {\n\treturn ((a + 1)) * 2\n}\n", "package p\n\nfunc f(a int) int {\n\treturn (a + 1) * 2\n}\n"),
           ("kotlin", dk("style", "This rule reports unnecessary parentheses around expressions", "UnnecessaryParentheses"),
            "fun f(a: Int): Int {\n    return ((a + 1)) * 2\n}\n", "fun f(a: Int): Int {\n    return (a + 1) * 2\n}\n"),
           ("php", (PHPM + "language.operators.precedence.php", "Use of parentheses, even when not strictly necessary", "PHP manual: Operator precedence"),
            "<?php\nfunction f($a) {\n    return (($a + 1)) * 2;\n}\n", "<?php\nfunction f($a) {\n    return ($a + 1) * 2;\n}\n"),
       ]}, keys=["S1110"], sev="info")

multi("CONSTANT-CONDITION", "if condition is a boolean literal",
      "The condition is always true or always false, so one branch is dead: remove the if, or use a named flag if it is a toggle.",
      {
          "kotlin": dict(doc=("https://kotlinlang.org/docs/control-flow.html", "If expression", "Kotlin docs: If expression"),
                         query="(if_expression condition: (_) @c (#match? @c \"^(true|false)$\")) @match",
                         bad="fun f() {\n    if (true) {\n        run()\n    }\n}\n", good="fun f(enabled: Boolean) {\n    if (enabled) {\n        run()\n    }\n}\n"),
          "php": dict(doc=(PHPM + "control-structures.if.php", "allows for conditional execution of code fragments", "PHP manual: if"),
                      query="(if_statement condition: (parenthesized_expression (boolean))) @match",
                      bad="<?php\nif (true) {\n    run();\n}\n", good="<?php\nif ($enabled) {\n    run();\n}\n"),
          "java": dict(doc=(JLS14, "It is a compile-time error if a statement cannot be executed", "JLS 14.22 Unreachable statements"), keys=(),
                       query="(if_statement condition: (parenthesized_expression [(true) (false)])) @match",
                       bad="class A {\n    void f() {\n        if (false) {\n            debug();\n        }\n    }\n}\n", good="class A {\n    void f() {\n        if (DEBUG) {\n            debug();\n        }\n    }\n}\n"),
          "python": dict(doc=(PYCOMPOUND, "The if statement is used for conditional execution", "Python reference: The if statement"), keys=("S5797",),
                         query="(if_statement condition: [(true) (false) (none) (integer) (string) (list) (dictionary) (tuple)]) @match",
                         # `if 0: yield` / `if False: yield` is the idiom that makes a function a generator
                         filters=[r"node.lacks_re:^if\s+(0|False)\s*:\s*yield\s*$"],
                         fp=["def worker():\n    if 0:\n        yield\n"],
                         bad="def f():\n    if False:\n        debug()\n", good="def f(enabled):\n    if enabled:\n        debug()\n"),
      }, keys=["S1145"])

OVERWRITE = {
    "java": ("(block (expression_statement (method_invocation object: [(identifier) (field_access)] @o name: (identifier) @n arguments: (argument_list . (_) @k))) @match . (expression_statement (method_invocation object: (_) @o2 name: (identifier) @n2 arguments: (argument_list . (_) @k2))) (#eq? @n \"put\") (#eq? @n2 \"put\") (#eq? @o @o2) (#eq? @k @k2) (#match? @k \"^(\\\"[^\\\"]*\\\"|[0-9]+)$\"))",
             "class A {\n    void f(Map<String, Integer> m) {\n        m.put(\"a\", 1);\n        m.put(\"a\", 2);\n    }\n}\n", "class A {\n    void f(Map<String, Integer> m) {\n        m.put(\"a\", 1);\n        m.put(\"b\", 2);\n    }\n}\n"),
    "javascript": ("(statement_block (expression_statement (assignment_expression left: (subscript_expression) @l)) @match . (expression_statement (assignment_expression left: (subscript_expression) @l2 right: (_) @r)) (#eq? @l @l2) (#match? @l \"\\\\[\\\\s*(['\\\"][^'\\\"]*['\\\"]|[0-9]+)\\\\s*\\\\]$\"))",
                   "function f(a) {\n  a[0] = 1;\n  a[0] = 2;\n}\n", "function f(a) {\n  a[0] = 1;\n  a[1] = 2;\n}\n"),
    "python": ("(block (expression_statement (assignment left: (subscript value: (_) @obj) @l)) @match . (expression_statement (assignment left: (subscript) @l2 right: (_) @r)) (#eq? @l @l2) (#match? @l \"\\\\[\\\\s*(['\\\"][^'\\\"]*['\\\"]|[0-9]+)\\\\s*\\\\]$\"))",
               "def f(d: dict):\n    d[\"a\"] = 1\n    d[\"a\"] = 2\n", "def f(d: dict):\n    d[\"a\"] = 1\n    d[\"b\"] = 2\n"),
    "php": ("(compound_statement (expression_statement (assignment_expression left: (subscript_expression) @l)) @match . (expression_statement (assignment_expression left: (subscript_expression) @l2 right: (_) @r)) (#eq? @l @l2) (#match? @l \"\\\\[\\\\s*(['\\\"][^'\\\"]*['\\\"]|[0-9]+)\\\\s*\\\\]$\"))",
            "<?php\nfunction f($a) {\n    $a['k'] = 1;\n    $a['k'] = 2;\n}\n", "<?php\nfunction f($a) {\n    $a['k'] = 1;\n    $a['j'] = 2;\n}\n"),
}
multi("OVERWRITTEN-ELEMENT", "Collection element written twice in a row",
      "The same key/index is assigned twice in consecutive statements, so the first value is lost: fix the key or drop the first write.",
      {l: dict(doc={"java": ("https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Map.html", "the old value is replaced by the specified value", "Java SE 21 API: Map.put"),
                    "javascript": (MDN + "Operators/Property_accessors", "Property accessors provide access to an object's properties", "MDN: Property accessors"),
                    "python": ("https://docs.python.org/3/library/stdtypes.html", "Set d[key] to value", "Python docs: dict"),
                    "php": (PHPM + "language.types.array.php", "An array in PHP is actually an ordered map", "PHP manual: Arrays")}[l],
               query=v[0], bad=v[1], good=v[2],
               filters={"java": [r"type.is:o:\w*Map|Properties|Hashtable"],
                        "python": ["cap.lacks_re:r:{cap:l}", r"type.is:obj:dict|list|OrderedDict|defaultdict|Counter"]}.get(l, ["cap.lacks_re:r:{cap:l}"]),
               fp={"java": ["class A {\n    void f(Node parent) {\n        parent.put(\"a\", 1);\n        parent.put(\"a\", 2);\n    }\n}\n"],
                   "python": ["def f(t):\n    t[\"a\"] = 1\n    t[\"a\"] = 2\n"]}.get(l))
       for l, v in OVERWRITE.items()}, keys=["S4143"], cat="correctness", kind="anti-pattern", sev="major")


# ---- naming and magic numbers (opt-in: conventions differ per team) ---------------------------------
NAMING = {
    # lang: (function query, class query, local query, fn default, class default, local default, docs, eq, from)
    "java": ("(method_declaration name: (identifier) @name) @match", "[(class_declaration name: (identifier) @name) (interface_declaration name: (identifier) @name) (enum_declaration name: (identifier) @name) (record_declaration name: (identifier) @name)] @match",
             "(local_variable_declaration declarator: (variable_declarator name: (identifier) @name)) @match",
             "^[a-z][a-zA-Z0-9]*$", "^[A-Z][a-zA-Z0-9]*$", "^[a-z][a-zA-Z0-9]*$",
             (cs("naming/methodname", "Checks that method names conform to a specified pattern", "MethodName"),
              cs("naming/typename", "Checks that type names conform to a specified pattern", "TypeName"),
              cs("naming/localvariablename", "Checks that local, non-", "LocalVariableName")),
             ("checkstyle:MethodName", "checkstyle:TypeName", "checkstyle:LocalVariableName"),
             (["checkstyle:MethodName.format"], ["checkstyle:TypeName.format"], ["checkstyle:LocalVariableName.format"])),
    "python": ("(function_definition name: (identifier) @name (#not-match? @name \"^(setUp|tearDown|setUpClass|tearDownClass|setUpModule|tearDownModule|asyncSetUp|asyncTearDown|visit_[A-Za-z]+|depart_[A-Za-z]+)$\")) @match",
               "(class_definition name: (identifier) @name) @match",
               "(expression_statement (assignment left: (identifier) @name)) @match",
               "^_{0,2}[a-z][a-z0-9_]*_{0,2}$", "^_?[A-Z][a-zA-Z0-9]*$", "^_{0,2}[a-z][a-z0-9_]*$",
               (rf("invalid-function-name", "Checks for functions names that do not follow the snake_case naming convention", "N802"),
                rf("invalid-class-name", "Checks for class names that do not follow the CamelCase convention", "N801"),
                rf("non-lowercase-variable-in-function", "Checks for the use of non-lowercase variable names in functions", "N806")),
               ("ruff:N802", "ruff:N801", "ruff:N806"), ([], [], [])),
    "php": ("[(method_declaration name: (name) @name (#not-match? @name \"^__\")) (function_definition name: (name) @name)] @match",
            "[(class_declaration name: (name) @name) (interface_declaration name: (name) @name) (trait_declaration name: (name) @name)] @match",
            "(expression_statement (assignment_expression left: (variable_name (name) @name))) @match",
            "^[a-z][a-zA-Z0-9]*$", "^[A-Z][a-zA-Z0-9]*$", "^[a-z_][a-zA-Z0-9_]*$",
            (md("controversial", "CamelCaseMethodName", "CamelCaseMethodName"), md("controversial", "CamelCaseClassName", "CamelCaseClassName"),
             md("controversial", "CamelCaseVariableName", "CamelCaseVariableName")),
            ("phpmd:CamelCaseMethodName", "phpmd:CamelCaseClassName", "phpmd:CamelCaseVariableName"), ([], [], [])),
}
NAME_EX = {
    "java": ("class A {\n    void Do_Work() {\n    }\n}\n", "class A {\n    void doWork() {\n    }\n}\n",
             "class order_line {\n}\n", "class OrderLine {\n}\n",
             "class A {\n    void f() {\n        int Total_Count = 0;\n        use(Total_Count);\n    }\n}\n", "class A {\n    void f() {\n        int totalCount = 0;\n        use(totalCount);\n    }\n}\n"),
    "python": ("def DoWork():\n    pass\n", "def do_work():\n    pass\n", "class order_line:\n    pass\n", "class OrderLine:\n    pass\n",
               "def f():\n    TotalCount = 0\n    use(TotalCount)\n", "def f():\n    total_count = 0\n    use(total_count)\n"),
    "php": ("<?php\nfunction Do_Work() {\n}\n", "<?php\nfunction doWork() {\n}\n", "<?php\nclass order_line {\n}\n", "<?php\nclass OrderLine {\n}\n",
            "<?php\nfunction f() {\n    $Total-Count = 0;\n}\n".replace("$Total-Count", "$TotalCount"), "<?php\nfunction f() {\n    $totalCount = 0;\n}\n"),
}
for lang, (fq, cq, lq, fd, cd, ld, docs, eqs, frm) in NAMING.items():
    ex = NAME_EX[lang]
    for i, (rid, title, q, default, key, scope) in enumerate([
            ("FUNCTION-NAMING", "Function name does not follow the naming convention", fq, fd, "S100", None),
            ("CLASS-NAMING", "Type name does not follow the naming convention", cq, cd, "S101", None),
            ("LOCAL-NAMING", "Local variable name does not follow the naming convention", lq, ld, "S117",
             {"java": "node.has_ancestor:method_declaration|constructor_declaration|lambda_expression", "python": "node.has_ancestor:function_definition",
              "php": "node.has_ancestor:function_definition|method_declaration"}[lang])]):
        fl = ["cap.lacks_re:name:${format}"] + ([scope] if scope else [])
        if rid == "LOCAL-NAMING" and lang == "python":
            fl.append("cap.lacks_re:name:^[A-Z][A-Z0-9_]*$")  # module-style constants inside functions
        add(lang, rid, title, docs[i], q, ex[2 * i], ex[2 * i + 1],
            "The name does not match the project's naming pattern ${format}; rename it so the code reads consistently.",
            keys=[key], eq=[eqs[i]], optin=True, sev="info", filters=fl,
            params={"format": {"default": default, "from": frm[i]}})

MAGIC = {
    "java": ("(decimal_integer_literal) @match", "class A {\n    boolean f(int n) {\n        return n > 42;\n    }\n}\n",
             "class A {\n    static final int LIMIT = 42;\n\n    boolean f(int n) {\n        return n > LIMIT;\n    }\n}\n",
             cs("coding/magicnumber", "Checks that there are no", "MagicNumber"), "checkstyle:MagicNumber",
             ["node.has_ancestor:method_declaration|constructor_declaration|lambda_expression", "ancestor.lacks_re:local_variable_declaration|annotation|element_value_pair:.",
              "func.lacks_re:\\bhashCode\\s*\\("]),
    "python": ("(comparison_operator (integer) @match)", "def f(n):\n    return n > 42\n", "LIMIT = 42\n\n\ndef f(n):\n    return n > LIMIT\n",
               rf("magic-value-comparison", "Checks for the use of unnamed numerical constants", "PLR2004"), "ruff:PLR2004", ["node.has_ancestor:function_definition"]),
    "kotlin": ("(binary_expression (number_literal) @match)", "fun f(n: Int): Boolean {\n    return n > 42\n}\n", "const val LIMIT = 42\n\nfun f(n: Int): Boolean {\n    return n > LIMIT\n}\n",
               dk("style", "This rule detects and reports usages of magic numbers in the code", "MagicNumber"), "detekt:MagicNumber", ["node.has_ancestor:function_declaration"]),
}
for lang, (q, bad, good, doc, eq, fl) in MAGIC.items():
    add(lang, "MAGIC-NUMBER", "Unnamed numeric constant", doc, q, bad, good,
        "Give this number a name (a constant) so readers know what it means and it can change in one place.",
        keys=["S109"], eq=[eq] if eq else ["revive:add-constant"] if lang == "go" else [], optin=True, sev="info",
        filters=fl + [r"node.lacks_re:^(-?[0-2]|10|100|1000)$"])



# ---- Java: small correctness / API-misuse patterns --------------------------------------------------
JAPI = "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/"
JLS15 = "https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html"
JLS8 = "https://docs.oracle.com/javase/specs/jls/se21/html/jls-8.html"
SPRING = "https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/"
SPRING_BOOT_API = "https://docs.spring.io/spring-boot/api/java/org/springframework/boot/"
JPA = "https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2"


def cls(body, pre=""):
    return pre + "class A {\n" + body + "}\n"


def jm(stmts, sig="void f()", pre=""):
    return cls("    " + sig + " {\n" + "".join("        " + s + "\n" for s in stmts) + "    }\n", pre)


def J(id, title, doc, query, bad, good, msg, key, **kw):
    kw.setdefault("cat", "correctness")
    kw.setdefault("kind", "anti-pattern")
    kw.setdefault("sev", "major")
    add("java", id, title, doc, query, bad, good, msg, keys=[key] if isinstance(key, str) else list(key), **kw)


J("FINALIZE-CALLED", "finalize() called explicitly", (JAPI + "lang/Object.html", "Called by the garbage collector on an object when garbage collection determines that there are no more references to the object", "Java SE 21 API: Object.finalize"),
  "(method_invocation name: (identifier) @m arguments: (argument_list) @a (#eq? @m \"finalize\") (#eq? @a \"()\")) @match",
  jm(["res.finalize();"]), jm(["res.close();"]), "finalize() is for the garbage collector; calling it yourself runs cleanup twice or too early. Use close()/a Cleaner.", "S1111",
  filters=["ancestor.lacks_re:method_declaration:^[^{]*\\bfinalize\\s*\\("], fp=[cls("    protected void finalize() throws Throwable {\n        super.finalize();\n    }\n")], eq=["https://openjdk.org/jeps/421"])
J("EQUALS-WRONG-PARAMETER", "equals() overload does not take Object", (JAPI + "lang/Object.html", "Indicates whether some other object is \"equal to\" this one", "Java SE 21 API: Object.equals"),
  "(method_declaration type: (boolean_type) name: (identifier) @n parameters: (formal_parameters . (formal_parameter type: (_) @t) .) (#eq? @n \"equals\") (#not-eq? @t \"Object\")) @match",
  cls("    public boolean equals(A other) {\n        return other != null;\n    }\n"), cls("    @Override\n    public boolean equals(Object other) {\n        return other instanceof A;\n    }\n"),
  "equals(A) overloads instead of overriding equals(Object), so collections never call it: take Object and test the type.", "S1201", filters=[r"ancestor.lacks_re:class_body:\bequals\s*\(\s*(final\s+)?(java\.lang\.)?Object\s+\w+\s*\)", "cap.lacks_re:t:^java\\.lang\\.Object$"])
J("MISSPELLED-OBJECT-METHOD", "Method name mimics an Object method with different case", (JAPI + "lang/Object.html", "Returns a string representation of the object", "Java SE 21 API: Object"),
  "(method_declaration name: (identifier) @n (#match? @n \"^(tostring|toSTring|hashcode|hashCODE|equal|Equals|ToString|HashCode)$\")) @match",
  cls("    public String tostring() {\n        return \"A\";\n    }\n"), cls("    @Override\n    public String toString() {\n        return \"A\";\n    }\n"),
  "This looks like a misspelt toString/hashCode/equals, so the Object method is not overridden: fix the name.", "S1221",
  filters=[r"node.lacks_re:^[^({]*\bstatic\b"], fp=[cls("    private static boolean equal(Object a, Object b) {\n        return Objects.equals(a, b);\n    }\n")])
J("STRINGBUILDER-CHAR-CAPACITY", "StringBuilder created with a char (taken as capacity)", (JAPI + "lang/StringBuilder.html", "Constructs a string builder with no characters in it and an initial capacity specified by the capacity argument", "Java SE 21 API: StringBuilder(int)"),
  "(object_creation_expression type: (type_identifier) @t arguments: (argument_list . (character_literal) .) (#match? @t \"^(StringBuilder|StringBuffer)$\")) @match",
  jm(["StringBuilder sb = new StringBuilder('[');"]), jm(["StringBuilder sb = new StringBuilder(\"[\");"]),
  "A char argument is widened to int and used as the initial capacity, not as content: pass a String.", "S1317")
J("NEW-RANDOM-PER-CALL", "Random created for a single value", (JAPI + "util/Random.html", "An instance of this class is used to generate a stream of pseudorandom numbers", "Java SE 21 API: Random"),
  "(method_invocation object: (object_creation_expression type: (type_identifier) @t) name: (identifier) @m (#eq? @t \"Random\") (#match? @m \"^next\")) @match",
  jm(["int roll = new Random().nextInt(6);"]), jm(["int roll = ThreadLocalRandom.current().nextInt(6);"]),
  "A new Random per value is wasteful and, seeded close in time, can repeat values: reuse one instance or ThreadLocalRandom.current().", "S2119", cat="maintainability", sev="minor")
J("SCHEDULED-POOL-ZERO-CORE", "ScheduledThreadPoolExecutor with zero core threads", (JAPI + "util/concurrent/ScheduledThreadPoolExecutor.html", "it acts as a fixed-sized pool using corePoolSize threads", "Java SE 21 API: ScheduledThreadPoolExecutor"),
  "(object_creation_expression type: (type_identifier) @t arguments: (argument_list . (decimal_integer_literal) @n) (#eq? @t \"ScheduledThreadPoolExecutor\") (#eq? @n \"0\")) @match",
  jm(["ScheduledExecutorService s = new ScheduledThreadPoolExecutor(0);"]), jm(["ScheduledExecutorService s = new ScheduledThreadPoolExecutor(1);"]),
  "The pool size is fixed at corePoolSize, so with 0 no scheduled task ever runs: use at least 1.", "S2122")
J("USELESS-POSTFIX-ASSIGN", "Variable assigned its own post-increment", (JLS15, "The value of the postfix increment expression is the value of the variable before the new value is stored", "JLS 15.14.2 Postfix Increment Operator"),
  "(assignment_expression left: (identifier) @l operator: \"=\" right: (update_expression (identifier) @r) @u (#eq? @l @r) (#match? @u \"(\\\\+\\\\+|--)$\")) @match",
  jm(["count = count++;"], "void f(int count)"), jm(["count++;"], "void f(int count)"),
  "x = x++ stores the old value back, so the increment is lost: write x++ (or x = x + 1).", "S2123")
J("RUN-FINALIZERS-ON-EXIT", "runFinalizersOnExit called", ("https://docs.oracle.com/en/java/javase/11/migrate/index.html", "java.lang.Runtime.runFinalizersOnExit(boolean)", "JDK 11 Migration Guide: APIs removed"),
  "(method_invocation name: (identifier) @m (#eq? @m \"runFinalizersOnExit\")) @match", jm(["System.runFinalizersOnExit(true);"]), jm(["Runtime.getRuntime().addShutdownHook(hook);"]),
  "This method is inherently unsafe and was removed from the JDK: use a shutdown hook.", "S2151",
  # Removed in JDK 11 (JDK-8198249): on 11+ the call no longer compiles, so the rule only matters for older targets.
  applies={"java": "<11"}, eq=["https://docs.oracle.com/javase/8/docs/api/java/lang/Runtime.html#runFinalizersOnExit-boolean-"])
J("TOSTRING-RETURNS-NULL", "toString() or clone() returns null", (JAPI + "lang/Object.html", "Returns a string representation of the object", "Java SE 21 API: Object.toString"),
  "(method_declaration name: (identifier) @n body: (block (return_statement (null_literal)) @match) (#match? @n \"^(toString|clone)$\"))",
  cls("    @Override\n    public String toString() {\n        return null;\n    }\n"), cls("    @Override\n    public String toString() {\n        return \"A\";\n    }\n"),
  "Callers (string concatenation, logging, copies) assume a non-null result: return an empty string or a real copy.", "S2225",
  filters=[r"ancestor.lacks_re:method_declaration:^[^{]*\bstatic\b", r"ancestor.has_re:method_declaration:^[^{]*\(\s*\)"])
J("FOR-UPDATE-WRONG-DIRECTION", "for-loop counter moves away from its bound", (JLS14, "The basic for statement executes some initialization code", "JLS 14.14.1 The basic for statement"),
  "(for_statement condition: (binary_expression left: (identifier) @c) update: (update_expression (identifier) @u) (#eq? @c @u)) @match",
  jm(["for (int i = 0; i < n; i--) {", "    use(i);", "}"], "void f(int n)"), jm(["for (int i = 0; i < n; i++) {", "    use(i);", "}"], "void f(int n)"),
  "The counter moves away from the bound in the condition, so the loop runs until overflow: fix the update.", "S2251",
  filters=[r"node.has_re:^for\s*\([^;]*;\s*\w+\s*<=?[^;]*;\s*(\w+\s*--|--\s*\w+)\s*\)|^for\s*\([^;]*;\s*\w+\s*>=?[^;]*;\s*(\w+\s*\+\+|\+\+\s*\w+)\s*\)"])
J("REPEATED-UNARY", "Unary operator applied twice", (JLS15, "Logical Complement Operator", "JLS 15.15.6 Logical Complement Operator"),
  "[(unary_expression operator: \"!\" operand: (unary_expression operator: \"!\")) (unary_expression operator: \"~\" operand: (unary_expression operator: \"~\"))] @match",
  jm(["boolean b = !!flag;"], "void f(boolean flag)"), jm(["boolean b = flag;"], "void f(boolean flag)"), "Applying ! or ~ twice is a no-op: remove both.", "S2761")
J("CLONE-OVERRIDDEN", "clone() overridden", (JAPI + "lang/Cloneable.html", "A class implements the Cloneable interface", "Java SE 21 API: Cloneable"),
  "(method_declaration name: (identifier) @n parameters: (formal_parameters) @p (#eq? @n \"clone\") (#eq? @p \"()\")) @match",
  cls("    @Override\n    public A clone() {\n        return new A();\n    }\n"), cls("    public A copy() {\n        return new A();\n    }\n"),
  "clone() has a fragile contract (shallow copies, Cloneable, checked exception): prefer a copy constructor or factory.", "S2975", cat="maintainability", sev="minor")
J("THREADGROUP-USED", "ThreadGroup used", (JAPI + "lang/ThreadGroup.html", "A thread group represents a set of threads", "Java SE 21 API: ThreadGroup"),
  "(object_creation_expression type: (type_identifier) @t (#eq? @t \"ThreadGroup\")) @match", jm(["ThreadGroup g = new ThreadGroup(\"workers\");"]),
  jm(["ExecutorService pool = Executors.newFixedThreadPool(4);"]), "ThreadGroup is legacy and mostly degraded: manage threads with an ExecutorService.", "S3014", cat="maintainability", sev="minor")
J("ASSERT-SIDE-EFFECT", "assert expression has a side effect", (JLS14, "The assert Statement", "JLS 14.10 The assert Statement"),
  "(assert_statement . (_) @e) @match", jm(["assert queue.remove(item);"]), jm(["boolean removed = queue.remove(item);", "assert removed;"]),
  "Assertions are disabled in production, so the side effect only happens with -ea: move it out of the assert.", "S3346",
  filters=["cap.has_re:e:\\+\\+|--|[^=!<>]=[^=]|\\.(add|remove|put|poll|offer|push|pop|delete|set|clear|next)\\w*\\("])
J("STREAM-NOT-CONSUMED", "Stream pipeline without a terminal operation", (JAPI + "util/stream/package-summary.html", "Intermediate operations return a new stream. They are always lazy", "Java SE 21 API: java.util.stream"),
  "(expression_statement (method_invocation object: (method_invocation) @o name: (identifier) @m (#match? @m \"^(filter|map|flatMap|peek|sorted|distinct|limit|skip|mapToInt|mapToLong|mapToObj|boxed)$\"))) @match",
  jm(["items.stream().filter(i -> i.isValid());"]), jm(["List<Item> valid = items.stream().filter(i -> i.isValid()).toList();"]),
  "Intermediate stream operations are lazy; without a terminal operation nothing runs: collect, forEach or drop the statement.", "S3958",
  filters=["cap.has_re:o:\\.stream\\(\\)|Stream\\.of\\(|\\.(filter|map|sorted)\\("])
J("EXCEPTION-NOT-THROWN", "Exception created but not thrown", (JAPI + "lang/Throwable.html", "The Throwable class is the superclass of all errors and exceptions", "Java SE 21 API: Throwable"),
  "(expression_statement (object_creation_expression type: (type_identifier) @t (#match? @t \"(Exception|Error)$\"))) @match",
  jm(["if (x < 0) {", "    new IllegalArgumentException(\"negative\");", "}"], "void f(int x)"), jm(["if (x < 0) {", "    throw new IllegalArgumentException(\"negative\");", "}"], "void f(int x)"),
  "The exception is constructed and dropped, so nothing is signalled: add `throw`.", "S3984")
J("WEEK-YEAR-PATTERN", "Week-based year (YYYY) in a date pattern", (JAPI + "time/format/DateTimeFormatter.html", "week-based-year", "Java SE 21 API: DateTimeFormatter"),
  "(method_invocation name: (identifier) @m arguments: (argument_list . (string_literal) @p) (#eq? @m \"ofPattern\")) @match", jm(["DateTimeFormatter f = DateTimeFormatter.ofPattern(\"YYYY-MM-dd\");"]),
  jm(["DateTimeFormatter f = DateTimeFormatter.ofPattern(\"yyyy-MM-dd\");"]), "YYYY is the week-based year, which differs from the calendar year around New Year: use yyyy (or uuuu).", "S3986",
  filters=["cap.has_re:p:YYYY", "cap.lacks_re:p:w"])
J("ITERATOR-RETURNS-THIS", "iterator() returns this", (JAPI + "lang/Iterable.html", "Returns an iterator over elements of type T", "Java SE 21 API: Iterable.iterator"),
  "(method_declaration name: (identifier) @n body: (block (return_statement (this)) @match) (#eq? @n \"iterator\"))",
  cls("    public Iterator<String> iterator() {\n        return this;\n    }\n"), cls("    public Iterator<String> iterator() {\n        return items.iterator();\n    }\n"),
  "Returning this means every caller shares one cursor, so a second loop sees nothing: return a new iterator.", "S4348")
J("COMPARETO-SUBTRACTION", "compare/compareTo implemented with subtraction", (JAPI + "lang/Integer.html", "Compares two int values numerically", "Java SE 21 API: Integer.compare"),
  "(method_declaration name: (identifier) @n parameters: (formal_parameters) @ps body: (block (return_statement (binary_expression operator: \"-\")) @match) (#match? @n \"^(compare|compareTo)$\"))",
  cls("    public int compareTo(A o) {\n        return this.size - o.size;\n    }\n"), cls("    public int compareTo(A o) {\n        return Integer.compare(this.size, o.size);\n    }\n"),
  "Subtraction overflows for large or negative values and flips the order: use Integer.compare / Long.compare.", "S9354",
  filters=[r"cap.lacks_re:ps:\b(char|byte|short|Character|Byte|Short)\s+\w+\s*[,)]"],
  fp=[cls("    public static int compare(final char x, final char y) {\n        return x - y;\n    }\n")])
J("SPLIT-ON-DOT", "Regex \".\" used where a literal dot was meant", (JAPI + "lang/String.html", "Splits this string around matches of the given regular expression", "Java SE 21 API: String.split"),
  "(method_invocation name: (identifier) @m arguments: (argument_list . (string_literal) @p) (#match? @m \"^(split|matches)$\") (#eq? @p \"\\\".\\\"\")) @match\n"
  "(method_invocation name: (identifier) @m arguments: (argument_list . (string_literal) @p . (_) .) (#match? @m \"^(replaceAll|replaceFirst)$\") (#eq? @p \"\\\".\\\"\")) @match",
  jm(["String[] parts = version.split(\".\");"], "void f(String version)"), jm(["String[] parts = version.split(\"\\\\.\");"], "void f(String version)"),
  "\".\" is a regex matching any character, so split returns an empty array: escape it (\"\\\\.\") or use Pattern.quote.", "S9353",
  fp=[jm(["String k = ESCAPED_DOT.matcher(key).replaceAll(\".\");"], "void f(String key)")])
J("COLLECTION-SELF-ARGUMENT", "Collection passed to its own method", (JAPI + "util/Collection.html", "The behavior of this operation is undefined if the specified collection is modified while the operation is in progress", "Java SE 21 API: Collection.addAll"),
  "(method_invocation object: (identifier) @o name: (identifier) @m arguments: (argument_list . (identifier) @a .) (#eq? @o @a) (#match? @m \"^(addAll|removeAll|retainAll|containsAll)$\")) @match",
  jm(["items.addAll(items);"]), jm(["items.addAll(extra);"]), "Passing a collection to its own bulk method is a no-op, undefined, or always true: pass the other collection.", "S2114",
  fp=[jm(["assertTrue(listener.equals(listener));"])])
J("BIT-OP-IDENTITY", "Bit operation with no effect or a constant result", (JLS15, "Integer Bitwise Operators", "JLS 15.22.1 Integer Bitwise Operators"),
  "(binary_expression operator: [\"|\" \"^\" \"&\"] right: [(decimal_integer_literal) (unary_expression)] @n) @match",
  jm(["int flags = mask & 0;"], "void f(int mask)"), jm(["int flags = mask & 0x0F;"], "void f(int mask)"), "x & 0 is always 0 and x | 0, x ^ 0 are just x: use the intended mask.", "S9344",
  filters=["node.has_re:&\\s*0$|[|^]\\s*0$"])
J("READ-RESULT-IGNORED", "Result of read()/readLine() discarded", (JAPI + "io/InputStream.html", "Returns: the next byte of data, or -1 if the end of the stream is reached", "Java SE 21 API: InputStream.read"),
  "(expression_statement (method_invocation object: (identifier) @o name: (identifier) @m arguments: (argument_list) @a (#match? @m \"^(read|readLine)$\") (#eq? @a \"()\") (#match? @o \"(?i)(stream|reader)$|^(in|is|br|input)$\"))) @match",
  jm(["reader.readLine();", "process(reader);"]), jm(["String header = reader.readLine();", "process(header, reader);"]),
  "The value read is thrown away (and end-of-stream goes unnoticed): use the result, or call skip() if skipping was intended.", "S2677",
  fp=[jm(["tokeniser.read();", "emit(tokeniser);"])])
J("SLEEP-HOLDING-LOCK", "Thread.sleep() inside synchronized code", (JAPI + "lang/Thread.html", "The thread does not lose ownership of any monitors", "Java SE 21 API: Thread.sleep"),
  "(method_invocation object: (identifier) @o name: (identifier) @m (#eq? @o \"Thread\") (#eq? @m \"sleep\")) @match",
  jm(["synchronized (lock) {", "    Thread.sleep(100);", "}"], "void f() throws InterruptedException"), jm(["synchronized (lock) {", "    lock.wait(100);", "}"], "void f() throws InterruptedException"),
  "sleep keeps the monitor, blocking every other thread waiting for it: use wait(timeout) on the lock or sleep outside.", "S2276",
  filters=["ancestor.has_re:synchronized_statement|method_declaration|lambda_expression:^(synchronized\\b|[^{]*\\bsynchronized\\b)"])
J("WAIT-NOTIFY-UNSYNCHRONIZED", "wait()/notify() called outside synchronized code", (JAPI + "lang/Object.html", "This method should only be called by a thread that is the owner of this object's monitor", "Java SE 21 API: Object.notify"),
  "(method_invocation name: (identifier) @m (#match? @m \"^(wait|notify|notifyAll)$\")) @match",
  jm(["lock.notifyAll();"]), jm(["synchronized (lock) {", "    lock.notifyAll();", "}"]),
  "Without holding the object's monitor these calls throw IllegalMonitorStateException: wrap them in synchronized on the same object.", "S2273",
  filters=["node.lacks_ancestor:synchronized_statement", "ancestor.lacks_re:method_declaration|lambda_expression:^[^{]*\\bsynchronized\\b", "node.has_re:^[\\w.]*\\b(wait|notify|notifyAll)\\(\\s*\\d*\\s*\\)$"],
  mode="ai-confirm", ai="Is the caller not already holding the monitor (e.g. via a synchronized caller)?")
J("LOCK-WITHOUT-FINALLY-UNLOCK", "Lock acquired without unlock in finally", (JAPI + "util/concurrent/locks/Lock.html", "When locking and unlocking occur in different scopes, care must be taken", "Java SE 21 API: Lock"),
  "(expression_statement (method_invocation name: (identifier) @m arguments: (argument_list) @a (#eq? @m \"lock\") (#eq? @a \"()\"))) @match",
  jm(["lock.lock();", "update();", "lock.unlock();"]), jm(["lock.lock();", "try {", "    update();", "} finally {", "    lock.unlock();", "}"]),
  "If the code after lock() throws, the lock is never released: unlock in a finally block.", "S2222",
  filters=["func.lacks_re:(?s)finally\\s*\\{[^}]*\\.unlock\\(\\)"], mode="ai-confirm", ai="Is the lock released on every path, including exceptions?")
J("VOLATILE-COMPOUND-UPDATE", "Compound update of a volatile field", (JLS8, "A field may be declared volatile", "JLS 8.3.1.4 volatile Fields"),
  "(update_expression (identifier) @v) @match", cls("    private volatile int hits;\n\n    void hit() {\n        hits++;\n    }\n"),
  cls("    private final AtomicInteger hits = new AtomicInteger();\n\n    void hit() {\n        hits.incrementAndGet();\n    }\n"),
  "volatile makes reads and writes visible but ++/-- is read-modify-write, so concurrent updates are lost: use an Atomic* type.", "S3078",
  filters=["file.has_re:\\bvolatile\\s+(int|long|short|byte|double|float|Integer|Long)\\s+{cap:v}\\b"])
J("INFINITE-LOOP", "Loop with no way out", (JLS14, "The while statement executes an Expression and a Statement repeatedly", "JLS 14.12 The while statement"),
  "[(while_statement condition: (parenthesized_expression (true)) body: (block) @b) (for_statement !condition body: (block) @b)] @match",
  jm(["while (true) {", "    poll();", "}"]), jm(["while (running) {", "    poll();", "}"]),
  "Nothing in the body leaves the loop (no break, return, throw or exit): add the exit condition.", "S2189",
  filters=["cap.lacks_re:b:\\b(break|return|throw|exit|halt)\\b"], mode="ai-confirm", ai="Is an endless loop unintended (not a deliberate server/worker loop)?")
J("TEST-CLASS-WITHOUT-TESTS", "Test class without test methods", ("https://docs.junit.org/current/user-guide/", "Test Classes and Methods", "JUnit User Guide"),
  "(program (class_declaration name: (identifier) @n (#match? @n \"Tests?$\")) @match)", "import org.junit.jupiter.api.Test;\n\nclass OrderTest {\n    void checksTotal() {\n    }\n}\n",
  "import org.junit.jupiter.api.Test;\n\nclass OrderTest {\n    @Test\n    void checksTotal() {\n    }\n}\n", "No method in this test class is a test, so it never runs anything: annotate the tests or rename the class.", "S2187",
  filters=["node.lacks_re:@(Test|ParameterizedTest|RepeatedTest|TestFactory|TestTemplate|Nested|Suite|Disabled|Ignore)\\b|\\babstract\\b|\\bextends\\b", "file.has_re:org\\.junit|org\\.testng"],
  cat="maintainability")
J("TEST-WITHOUT-ASSERTION", "Test method without an assertion", ("https://docs.junit.org/current/user-guide/", "Assertions", "JUnit User Guide: Assertions"),
  "(method_declaration (modifiers (marker_annotation name: (identifier) @a)) body: (block) @b (#eq? @a \"Test\")) @match",
  "import org.junit.jupiter.api.Test;\n\nclass OrderTest {\n    @Test\n    void total() {\n        new Order().total();\n    }\n}\n",
  "import org.junit.jupiter.api.Test;\n\nclass OrderTest {\n    @Test\n    void total() {\n        assertEquals(0, new Order().total());\n    }\n}\n",
  "The test never checks anything, so it passes whatever the code does: add assertions (or assertDoesNotThrow if that is the point).", "S2699",
  # A test that delegates to a local helper which asserts (testValidated(...), _testPOJO(...)) asserts.
  filters=["cap.lacks_re:b:(?i)\\b(assert|verify|expect|fail|then|should|check|validate)\\w*\\s*\\(|assertThat|\\.andExpect\\(",
           "cap.lacks_helper_re:b:(?i)\\b(assert|verify|expect|fail|then|should|check|validate)\\w*\\s*\\(|assertThat|\\.andExpect\\("], fp=["import org.junit.jupiter.api.Test;\n\nclass OrderTest {\n    @Test\n    void total() {\n        checkTotal(new Order());\n    }\n\n    private void checkTotal(Order o) {\n        assertEquals(0, o.total());\n    }\n}\n", "import org.junit.jupiter.api.Test;\n\nclass OrderTest {\n    @Test\n    void total() {\n        _testTotal(new Order());\n    }\n\n    private void _testTotal(Order o) {\n        assertEquals(0, o.total());\n    }\n}\n"], cat="maintainability",
  mode="ai-confirm", ai="Does the test lack any check (no helper method that asserts, no expected-exception setup)?")
J("ASSERT-SAME-ARGUMENT", "Assertion compares a value with itself", ("https://docs.junit.org/current/user-guide/", "Assertions", "JUnit User Guide: Assertions"),
  "(method_invocation name: (identifier) @m arguments: (argument_list . (_) @x . (_) @y .) (#match? @m \"^assert(Equals|Same|NotEquals|NotSame)$\") (#eq? @x @y)) @match",
  "class OrderTest {\n    void total() {\n        assertEquals(total, total);\n    }\n}\n", "class OrderTest {\n    void total() {\n        assertEquals(42, order.total());\n    }\n}\n",
  "Comparing a value with itself always passes (or always fails): compare against the expected value.", "S5863", cat="maintainability",
  # Two evaluations (new X(), f()) are distinct values; equals/hashCode/caching tests assert reflexivity on purpose.
  filters=[r"cap.lacks_re:x:\(|\bnew\b", r"ancestor.lacks_re:method_declaration:(?is)^[^{]*\b\w*(equal|hash|reflex|identit|same|cach)\w*\s*\("],
  fp=["class RangeTest {\n    void testEquals() {\n        assertEquals(range1, range1);\n    }\n}\n",
      "class NodeTest {\n    void pojo() {\n        assertEquals(new POJONode(null), new POJONode(null));\n    }\n}\n"])
J("ASSERTJ-INCOMPLETE", "assertThat() without a check", ("https://assertj.github.io/doc/", "AssertJ", "AssertJ documentation"),
  "(expression_statement (method_invocation name: (identifier) @m arguments: (argument_list . (_) .) (#eq? @m \"assertThat\"))) @match",
  "import static org.assertj.core.api.Assertions.assertThat;\n\nclass OrderTest {\n    void total() {\n        assertThat(order.total());\n    }\n}\n", "import static org.assertj.core.api.Assertions.assertThat;\n\nclass OrderTest {\n    void total() {\n        assertThat(order.total()).isEqualTo(42);\n    }\n}\n",
  "assertThat(x) alone checks nothing: chain an assertion such as isEqualTo().", "S2970", cat="maintainability", filters=["file.has_re:org\\.assertj"],
  fp=["import static org.assertj.core.api.Assertions.assertThat;\n\nclass SeedTest {\n    void seeds() {\n        org.hamcrest.MatcherAssert.assertThat(seeds, not(empty()));\n    }\n}\n"])
J("PROD-TEST-ASSERTIONS", "Test-framework assertions in production code", ("https://docs.junit.org/current/user-guide/", "Assertions", "JUnit User Guide: Assertions"),
  "(import_declaration) @match", "import static org.junit.jupiter.api.Assertions.assertTrue;\n\nclass Service {\n}\n", "import java.util.Objects;\n\nclass Service {\n}\n",
  "Test assertion libraries in main code throw AssertionError in production and drag a test dependency in: use explicit checks.", "S5960",
  filters=["node.has_re:org\\.junit\\.(jupiter\\.api\\.)?Assert|org\\.assertj|org\\.hamcrest"], files=["**/src/main/**/*.java"])
SPR = lambda path, needle, name: (SPRING + path, needle, "Spring Framework API: " + name)
J("SPRING-MULTIPLE-AUTOWIRED-CONSTRUCTORS", "@Autowired on several constructors", SPR("beans/factory/annotation/Autowired.html", "Only one constructor of any given bean class may declare this annotation", "@Autowired"),
  "(class_body (constructor_declaration (modifiers (marker_annotation name: (identifier) @a))) . (_)* . (constructor_declaration (modifiers (marker_annotation name: (identifier) @b))) (#eq? @a \"Autowired\") (#eq? @b \"Autowired\")) @match",
  "class Svc {\n    @Autowired\n    Svc(A a) {\n    }\n\n    @Autowired\n    Svc(A a, B b) {\n    }\n}\n", "class Svc {\n    @Autowired\n    Svc(A a, B b) {\n    }\n\n    Svc(A a) {\n        this(a, null);\n    }\n}\n",
  "Only one constructor may be @Autowired (required); Spring fails to start otherwise: keep the annotation on one.", "S6818")
J("SPRING-QUALIFIER-ON-BEAN", "@Qualifier on a @Bean method", SPR("context/annotation/Bean.html", "Indicates that a method produces a bean to be managed by the Spring container", "@Bean"),
  "(method_declaration (modifiers (marker_annotation name: (identifier) @b) (annotation name: (identifier) @q)) (#eq? @b \"Bean\") (#eq? @q \"Qualifier\")) @match",
  "class Cfg {\n    @Bean\n    @Qualifier(\"fast\")\n    Cache cache() {\n        return new Cache();\n    }\n}\n", "class Cfg {\n    @Bean(\"fast\")\n    Cache cache() {\n        return new Cache();\n    }\n}\n",
  "Name the bean with @Bean(\"name\"); @Qualifier on the producer is redundant and confusing.", "S6831", cat="maintainability", sev="minor")
J("SPRING-INITBINDER-NON-VOID", "@InitBinder method does not return void", SPR("web/bind/annotation/InitBinder.html", "methods must not have a return value; they are usually declared as void", "@InitBinder"),
  "(method_declaration (modifiers (marker_annotation name: (identifier) @a)) type: (_) @t (#eq? @a \"InitBinder\")) @match",
  "class C {\n    @InitBinder\n    String init(WebDataBinder b) {\n        return \"x\";\n    }\n}\n", "class C {\n    @InitBinder\n    void init(WebDataBinder b) {\n    }\n}\n",
  "Init-binder methods must be declared void; Spring rejects other return types.", "S7183", filters=["cap.lacks_re:t:^void$"])
J("SPRING-SCHEDULED-WITH-PARAMS", "@Scheduled method takes parameters", SPR("scheduling/annotation/Scheduled.html", "The annotated method must not accept arguments", "@Scheduled"),
  "(method_declaration (modifiers (annotation name: (identifier) @a)) parameters: (formal_parameters (formal_parameter)) (#eq? @a \"Scheduled\")) @match",
  "class Jobs {\n    @Scheduled(fixedRate = 1000)\n    void tick(String name) {\n    }\n}\n", "class Jobs {\n    @Scheduled(fixedRate = 1000)\n    void tick() {\n    }\n}\n",
  "Scheduled methods are called without arguments; a parameter makes startup fail.", "S7184")
J("SPRING-EVENTLISTENER-PARAMS", "@EventListener method takes more than one parameter", SPR("context/event/EventListener.html", "a single parameter that reflects the event type to listen to", "@EventListener"),
  "(method_declaration (modifiers (marker_annotation name: (identifier) @a)) parameters: (formal_parameters (formal_parameter) (formal_parameter)) (#eq? @a \"EventListener\")) @match",
  "class L {\n    @EventListener\n    void on(OrderPlaced e, String extra) {\n    }\n}\n", "class L {\n    @EventListener\n    void on(OrderPlaced e) {\n    }\n}\n",
  "An event listener receives exactly the event; extra parameters make the registration fail.", "S7185")
J("SPRING-VALUE-WITHOUT-PLACEHOLDER", "@Value with a plain literal", ("https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/value-annotations.html", "is typically used to inject externalized properties", "Spring reference: Using @Value"),
  "(annotation name: (identifier) @a arguments: (annotation_argument_list . (string_literal) @v .) (#eq? @a \"Value\")) @match",
  "class C {\n    @Value(\"8080\")\n    int port;\n}\n", "class C {\n    @Value(\"${server.port:8080}\")\n    int port;\n}\n",
  "@Value without ${...} or #{...} just injects the literal: use a property placeholder (or a plain field initializer).", "S6804", cat="maintainability", sev="minor",
  filters=["cap.lacks_re:v:\\$\\{|#\\{"])
J("SPRING-INJECT-STATIC-FIELD", "Injection annotation on a static field", ("https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/autowired.html", "Autowired", "Spring reference: Using @Autowired"),
  "(field_declaration (modifiers [(marker_annotation name: (identifier) @a) (annotation name: (identifier) @a)] \"static\") (#match? @a \"^(Autowired|Inject|Value)$\")) @match",
  "class C {\n    @Autowired\n    static Repo repo;\n}\n", "class C {\n    @Autowired\n    Repo repo;\n}\n", "Spring does not inject static fields; the field stays null. Make it an instance field or use constructor injection.", "S7178")
J("SPRING-CACHEABLE-AND-CACHEPUT", "@Cacheable and @CachePut on the same method", SPR("cache/annotation/CachePut.html", "In contrast to the @Cacheable annotation, this annotation does not cause the advised method to be skipped", "@CachePut"),
  "(method_declaration (modifiers) @m) @match", "class S {\n    @Cacheable(\"users\")\n    @CachePut(\"users\")\n    User load(long id) {\n        return repo.find(id);\n    }\n}\n",
  "class S {\n    @Cacheable(\"users\")\n    User load(long id) {\n        return repo.find(id);\n    }\n}\n", "The two annotations contradict each other (skip vs. always run): keep one.", "S7179",
  filters=["cap.has_re:m:@Cacheable\\b", "cap.has_re:m:@CachePut\\b"])
J("SPRING-ASYNC-IN-CONFIGURATION", "@Async method declared in a @Configuration class", SPR("scheduling/annotation/Async.html", "Annotation that marks a method as a candidate for asynchronous execution", "@Async"),
  "(method_declaration (modifiers (marker_annotation name: (identifier) @a)) (#eq? @a \"Async\")) @match", "@Configuration\nclass Cfg {\n    @Async\n    void warmUp() {\n    }\n}\n",
  "@Service\nclass Warmer {\n    @Async\n    void warmUp() {\n    }\n}\n", "Configuration classes are processed specially and @Async there is unreliable: move the method to a regular bean.", "S6817",
  filters=["ancestor.has_re:class_declaration:^@Configuration\\b|\\n@Configuration\\b|^\\s*@Configuration"])
J("SPRING-BOOT-APP-DEFAULT-PACKAGE", "@SpringBootApplication in the default package", (SPRING_BOOT_API + "autoconfigure/SpringBootApplication.html", "Indicates a configuration class that declares one or more", "Spring Boot API: @SpringBootApplication"),
  "(program (class_declaration (modifiers (marker_annotation name: (identifier) @a)) (#eq? @a \"SpringBootApplication\")) @match)",
  "@SpringBootApplication\nclass App {\n}\n", "package com.example;\n\n@SpringBootApplication\nclass App {\n}\n",
  "Without a package, component scanning covers every jar on the classpath, which is slow and breaks startup: put the class in a package.", "S4602",
  filters=["file.lacks_re:(?m)^\\s*package\\s"])
J("JPA-FINAL-ENTITY", "Final JPA entity", ("https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2.html", "The entity class must be non-final", "Jakarta Persistence 3.2 specification"),
  "(class_declaration (modifiers (marker_annotation name: (identifier) @a) \"final\") (#eq? @a \"Entity\")) @match", "@Entity\npublic final class Order {\n}\n", "@Entity\npublic class Order {\n}\n",
  "Persistence providers proxy entities by subclassing; a final entity breaks lazy loading.", "S8947")
J("SPRING-FINAL-CONFIGURATION", "Final @Configuration class", ("https://docs.spring.io/spring-framework/reference/core/beans/java/configuration-annotation.html", "Configuration", "Spring reference: Using the @Configuration annotation"),
  "(class_declaration (modifiers (marker_annotation name: (identifier) @a) \"final\") (#eq? @a \"Configuration\")) @match", "@Configuration\npublic final class Cfg {\n}\n",
  "@Configuration\npublic class Cfg {\n}\n", "Spring subclasses @Configuration classes (CGLIB) to manage @Bean methods; a final class cannot be proxied.", "S9021")

# ---- Python correctness and library-misuse batch ---------------------------------------------
PYD = "https://docs.python.org/3/"

def Py(id, title, doc, query, bad, good, msg, key, **kw):
    kw.setdefault("cat", "correctness")
    kw.setdefault("kind", "anti-pattern")
    kw.setdefault("sev", "major")
    add("python", id, title, doc, query, bad, good, msg, keys=[key], **kw)

ASYNC_FN = r"ancestor.has_re:function_definition:^async\s"

Py("INIT-RETURNS-VALUE", "__init__ returns a value", (PYD + "reference/datamodel.html", "value may be returned by __init__()", "Python reference: object.__init__"),
   "(class_definition body: (block (function_definition name: (identifier) @n body: (block (return_statement (_)) @match) (#eq? @n \"__init__\"))))",
   "class A:\n    def __init__(self, x):\n        self.x = x\n        return self\n",
   "class A:\n    def __init__(self, x):\n        self.x = x\n",
   "Returning anything other than None from __init__ raises TypeError when the class is instantiated.", "S2734", eq=["ruff:PLE0101"])
Py("EXCEPTION-NOT-RAISED", "Exception object created and discarded", (PYD + "reference/simple_stmts.html", "The raise statement", "Python reference: The raise statement"),
   "(expression_statement (call function: (identifier) @f (#match? @f \"^[A-Z][A-Za-z0-9]*(Error|Exception)$\")) @match)",
   "def check(x):\n    if x < 0:\n        ValueError(\"negative\")\n",
   "def check(x):\n    if x < 0:\n        raise ValueError(\"negative\")\n",
   "The exception is constructed but never raised, so the error path silently continues: add raise.", "S3984", eq=["ruff:PLW0133"])
Py("METHOD-WITHOUT-SELF", "Method declared without any parameter", (PYD + "tutorial/classes.html", "the instance object is passed as the first argument of the function", "Python tutorial: Method Objects"),
   "(class_definition body: (block (function_definition parameters: (parameters) @p) @match))",
   "class A:\n    def size():\n        return 1\n",
   "class A:\n    def size(self):\n        return 1\n",
   "An undecorated method always receives the instance, so calling one with no parameters raises TypeError: add self or mark it @staticmethod.", "S5719",
   fp=["from zope.interface import Interface\n\nclass ISpiderLoader(Interface):\n    def list():\n        pass\n"], eq=["pylint:no-method-argument"],
   filters=[r"cap.has_re:p:^\(\s*\)$", r"ancestor.lacks_re:class_definition:^class\s+\w+\s*\([^)]*\bInterface\b"])
Py("IDENTITY-WITH-NEW-OBJECT", "Identity test against a freshly built object", (PYD + "reference/expressions.html", "Literals and object identity", "Python reference: Literals and object identity"),
   "(comparison_operator) @match",
   "def empty(x):\n    return x is []\n",
   "def empty(x):\n    return x == []\n",
   "A new list, dict, set or tuple display is a distinct object, so 'is' against it is always False (and 'is not' always True): compare with == or test emptiness.", "S5796",
   filters=[r"node.has_re:\bis(\s+not)?\s+(\[[^\]]*\]|\{[^}]*\}|\(\s*\))\s*$"])
Py("OPEN-INVALID-MODE", "open() called with an invalid mode string", (PYD + "library/functions.html", "Character Meaning", "Python docs: open"),
   "(call function: (identifier) @f arguments: (argument_list . (_) . (string) @m) (#eq? @f \"open\")) @match",
   "def read(p):\n    with open(p, \"rw\") as fh:\n        return fh.read()\n",
   "def read(p):\n    with open(p, \"r+\") as fh:\n        return fh.read()\n",
   "This mode string raises ValueError at runtime: use exactly one of r, w, x, a, optionally with + and one of b/t.", "S5828", eq=["ruff:PLW1501"],
   filters=[r"cap.has_re:m:^['\x22]([^'\x22]*[^rwxabt+'\x22]|[^'\x22]*[rwxa][^'\x22]*[rwxa]|[^'\x22]*b[^'\x22]*t|[^'\x22]*t[^'\x22]*b|[^'\x22]*\+[^'\x22]*\+|[bt+]*['\x22]$)"])
Py("ASSERT-SAME-ARGUMENT", "unittest assertion compares an expression with itself", (PYD + "library/unittest.html", "Test that first and second are equal", "Python docs: unittest.TestCase.assertEqual"),
   "(call function: (attribute attribute: (identifier) @m) arguments: (argument_list . (_) @a . (_) @b) (#match? @m \"^assert(Equal|NotEqual|Is|IsNot|AlmostEqual|NotAlmostEqual|Greater|GreaterEqual|Less|LessEqual|CountEqual)$\") (#eq? @a @b)) @match",
   "class T(unittest.TestCase):\n    def test_total(self):\n        total = compute()\n        self.assertEqual(total, total)\n",
   "class T(unittest.TestCase):\n    def test_total(self):\n        total = compute()\n        self.assertEqual(total, 42)\n",
   "Both arguments are the same expression, so the assertion can never fail and tests nothing.", "S5863", cat="testing")
Py("NAN-EQUALITY", "Equality comparison against NaN", ("https://numpy.org/doc/stable/reference/generated/numpy.isnan.html", "Test element-wise for NaN", "NumPy docs: numpy.isnan"),
   "(comparison_operator (attribute object: (identifier) @o attribute: (identifier) @a) (#match? @o \"^(np|numpy|math)$\") (#eq? @a \"nan\")) @match",
   "def missing(x):\n    return x == np.nan\n",
   "def missing(x):\n    return np.isnan(x)\n",
   "NaN is unequal to everything including itself, so == is always False and != always True: use isnan().", "S6725", eq=["ruff:PLW0177"],
   filters=[r"node.has_re:(==|!=)"])
Py("ISCLOSE-TO-ZERO", "math.isclose against zero without abs_tol", (PYD + "library/math.html", "rel_tol is the relative tolerance", "Python docs: math.isclose"),
   "(call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list) @args (#eq? @o \"math\") (#eq? @a \"isclose\")) @match",
   "def done(err):\n    return math.isclose(err, 0)\n",
   "def done(err):\n    return math.isclose(err, 0, abs_tol=1e-9)\n",
   "With only a relative tolerance, closeness to 0 means exact equality: pass abs_tol.", "S6727",
   filters=[r"cap.has_re:args:(^\(\s*0(\.0*)?\s*,|,\s*0(\.0*)?\s*\)$)", r"cap.lacks_re:args:abs_tol"])
Py("BLOCKING-SLEEP-IN-ASYNC", "time.sleep inside async function", (PYD + "library/asyncio-dev.html", "Blocking (CPU-bound) code should not be called directly", "Python docs: Developing with asyncio"),
   "(call function: (attribute object: (identifier) @o attribute: (identifier) @a) (#eq? @o \"time\") (#eq? @a \"sleep\")) @match",
   "async def poll():\n    time.sleep(1)\n",
   "async def poll():\n    await asyncio.sleep(1)\n",
   "time.sleep blocks the whole event loop: await asyncio.sleep instead.", "S7488", eq=["ruff:ASYNC251"], filters=[ASYNC_FN])
Py("BLOCKING-SUBPROCESS-IN-ASYNC", "Synchronous subprocess call inside async function", (PYD + "library/asyncio-dev.html", "Blocking (CPU-bound) code should not be called directly", "Python docs: Developing with asyncio"),
   "(call function: (attribute object: (identifier) @o attribute: (identifier) @a) (#match? @o \"^(subprocess|os)$\") (#match? @a \"^(run|call|check_call|check_output|Popen|system|popen)$\")) @match",
   "async def build():\n    subprocess.run([\"make\"])\n",
   "async def build():\n    proc = await asyncio.create_subprocess_exec(\"make\")\n    await proc.wait()\n",
   "A synchronous process call blocks the event loop until the child exits: use asyncio.create_subprocess_exec.", "S7487", eq=["ruff:ASYNC221"], filters=[ASYNC_FN])
Py("BLOCKING-HTTP-IN-ASYNC", "Synchronous HTTP client call inside async function", (PYD + "library/asyncio-dev.html", "Blocking (CPU-bound) code should not be called directly", "Python docs: Developing with asyncio"),
   "(call function: (attribute object: (identifier) @o attribute: (identifier) @a) (#match? @o \"^(requests|urllib3)$\") (#match? @a \"^(get|post|put|patch|delete|head|request|urlopen)$\")) @match",
   "async def fetch(url):\n    return requests.get(url, timeout=5)\n",
   "async def fetch(url):\n    async with httpx.AsyncClient() as c:\n        return await c.get(url, timeout=5)\n",
   "A blocking HTTP call stalls every task on the loop while it waits: use an async client.", "S7499", eq=["ruff:ASYNC210"], filters=[ASYNC_FN])
Py("INPUT-IN-ASYNC", "input() inside async function", (PYD + "library/asyncio-dev.html", "Blocking (CPU-bound) code should not be called directly", "Python docs: Developing with asyncio"),
   "(call function: (identifier) @f (#eq? @f \"input\")) @match",
   "async def ask():\n    return input(\"name? \")\n",
   "async def ask():\n    return await asyncio.to_thread(input, \"name? \")\n",
   "input() blocks the event loop until the user answers: run it in a thread.", "S7501", filters=[ASYNC_FN])
Py("BLOCKING-OPEN-IN-ASYNC", "Synchronous file open inside async function", (PYD + "library/asyncio-dev.html", "Blocking (CPU-bound) code should not be called directly", "Python docs: Developing with asyncio"),
   "(call function: (identifier) @f (#eq? @f \"open\")) @match",
   "async def load(p):\n    with open(p) as fh:\n        return fh.read()\n",
   "async def load(p):\n    return await asyncio.to_thread(read_file, p)\n",
   "File I/O through open() blocks the event loop: move it to a thread or use an async file library.", "S7493", eq=["ruff:ASYNC230"], filters=[ASYNC_FN], mode="ai-confirm", sev="minor")
Py("TASK-REFERENCE-DROPPED", "asyncio task created without keeping a reference", (PYD + "library/asyncio-task.html", "Save a reference to the result of this function", "Python docs: asyncio.create_task"),
   "(expression_statement (call function: (attribute object: (identifier) @o attribute: (identifier) @a) (#eq? @o \"asyncio\") (#match? @a \"^(create_task|ensure_future)$\")) @match)",
   "async def main():\n    asyncio.create_task(worker())\n",
   "async def main():\n    task = asyncio.create_task(worker())\n    await task\n",
   "The loop keeps only weak references to tasks, so an unreferenced task can be garbage-collected mid-run: keep the returned task.", "S7502", eq=["ruff:RUF006"])
Py("CANCELLED-ERROR-SWALLOWED", "CancelledError caught and not re-raised", (PYD + "library/asyncio-task.html", "should generally be propagated", "Python docs: Task Cancellation"),
   "(except_clause value: [(attribute attribute: (identifier) @e) (identifier) @e] (#eq? @e \"CancelledError\")) @match",
   "async def run():\n    try:\n        await work()\n    except asyncio.CancelledError:\n        cleanup()\n",
   "async def run():\n    try:\n        await work()\n    except asyncio.CancelledError:\n        cleanup()\n        raise\n",
   "Swallowing cancellation breaks timeouts and task groups: re-raise after clean-up.", "S7497", filters=[r"node.lacks_re:\braise\b"])
Py("DICT-COMPREHENSION-STATIC-KEY", "Dict comprehension with a constant key", (PYD + "tutorial/datastructures.html", "dict comprehensions can be used", "Python tutorial: Dictionaries"),
   "(dictionary_comprehension body: (pair key: [(integer) (float) (true) (false) (none)])) @match\n((dictionary_comprehension body: (pair key: (string) @k)) @match (#not-match? @k \"\\\\{[^{]\"))",
   "def index(xs):\n    return {\"k\": x for x in xs}\n",
   "def index(xs):\n    return {x.id: x for x in xs}\n\ndef tag(xs):\n    return {f\"@{x.id}\": x for x in xs}\n",
   "Every iteration writes the same key, so the result holds a single entry: derive the key from the loop variable.", "S7506", eq=["ruff:B035"])
Py("DEFAULTDICT-FACTORY-KEYWORD", "defaultdict given default_factory as keyword", (PYD + "library/collections.html", "The first argument provides the initial value for the default_factory attribute", "Python docs: collections.defaultdict"),
   "(call function: [(identifier) @f (attribute attribute: (identifier) @f)] arguments: (argument_list (keyword_argument name: (identifier) @k)) (#eq? @f \"defaultdict\") (#eq? @k \"default_factory\")) @match",
   "groups = defaultdict(default_factory=list)\n",
   "groups = defaultdict(list)\n",
   "As a keyword it becomes a dict entry named 'default_factory' and the factory stays None: pass it positionally.", "S7507", eq=["ruff:RUF026"])
Py("NOTIMPLEMENTED-AS-BOOL", "NotImplemented used as a truth value", (PYD + "library/constants.html", "NotImplemented", "Python docs: NotImplemented"),
   "([(if_statement condition: (identifier) @i) (not_operator argument: (identifier) @i) (boolean_operator left: (identifier) @i) (while_statement condition: (identifier) @i)] @match (#eq? @i \"NotImplemented\"))",
   "def eq(a, b):\n    r = a.__eq__(b)\n    if NotImplemented:\n        return False\n    return r\n",
   "def eq(a, b):\n    r = a.__eq__(b)\n    if r is NotImplemented:\n        return False\n    return r\n",
   "Truth-testing NotImplemented is deprecated and raises TypeError on 3.14: compare with 'is NotImplemented'.", "S7931",
   fp=["class Abstract:\n    @classmethod\n    def __subclasshook__(cls, C):\n        return (cls is Abstract and hasattr(C, 'run')) or NotImplemented\n"])
Py("STOPITERATION-IN-GENERATOR", "StopIteration raised inside a generator", (PYD + "library/exceptions.html", "it is converted into a RuntimeError", "Python docs: StopIteration"),
   "(raise_statement [(identifier) @e (call function: (identifier) @e)] (#eq? @e \"StopIteration\")) @match",
   "def items(xs):\n    for x in xs:\n        if x is None:\n            raise StopIteration\n        yield x\n",
   "def items(xs):\n    for x in xs:\n        if x is None:\n            return\n        yield x\n",
   "Inside a generator a raised StopIteration becomes RuntimeError: use return to finish.", "S8493", eq=["ruff:PLR1708"],
   filters=[r"func.lacks_re:^\s*(async\s+)?def\s+__next__\b", r"func.has_re:\byield\b"])
Py("MEMBERSHIP-IN-EMPTY", "Membership test against an empty literal", (PYD + "reference/expressions.html", "Membership test operations", "Python reference: Membership test operations"),
   "(comparison_operator) @match",
   "def known(x):\n    return x in []\n",
   "def known(x):\n    return x in KNOWN\n",
   "Nothing is in an empty collection, so this is always False (or True for 'not in').", "S8503",
   filters=[r"node.has_re:\bin\s+(\[\s*\]|\(\s*\)|\{\s*\}|\x22\x22|'')\s*$"])
Py("PROPERTY-WITHOUT-RETURN", "Property getter without return", (PYD + "library/functions.html", "Return a property attribute", "Python docs: property"),
   "(decorated_definition (decorator (identifier) @d) definition: (function_definition body: (block) @b) @match (#eq? @d \"property\"))",
   "class A:\n    @property\n    def size(self):\n        len(self.items)\n",
   "class A:\n    @property\n    def size(self):\n        return len(self.items)\n",
   "The getter never returns, so the property always reads as None.", "S8504",
   filters=[r"node.lacks_re:\b(return|raise|yield)\b", r"node.lacks_re:(?m)^\s*(\.\.\.|pass)\s*$",
            r"cap.lacks_re:b:^\s*(\"\"\"[\s\S]*?\"\"\"|'\'\'[\s\S]*?'\'\'|\"[^\"\n]*\")?\s*(\.\.\.|pass)?\s*(#.*)?$"],
   fp=["class P(Protocol):\n    @property\n    def name(self) -> str: ...\n",
       "class P(Protocol):\n    @property\n    def name(self) -> str:\n        \"\"\"The name.\"\"\"\n"])
Py("FROMKEYS-MUTABLE-VALUE", "dict.fromkeys with a mutable shared value", (PYD + "library/stdtypes.html", "All of the values refer to just a single instance", "Python docs: dict.fromkeys"),
   "(call function: (attribute attribute: (identifier) @a) arguments: (argument_list . (_) . [(list) (dictionary) (set) (call function: (identifier) @c)] @v) (#eq? @a \"fromkeys\")) @match",
   "buckets = dict.fromkeys(names, [])\n",
   "buckets = {n: [] for n in names}\n",
   "Every key shares the same mutable object, so appending to one bucket changes them all: build distinct values with a comprehension.", "S8508", eq=["ruff:RUF024"],
   filters=[r"cap.has_re:v:^(\[|\{|(list|dict|set|bytearray)\()"])
Py("LIST-FOR-FIRST-ITEM", "Whole iterable materialised to take its first element", (PYD + "library/functions.html", "Retrieve the next item from the iterator", "Python docs: next"),
   "(subscript value: (call function: (identifier) @f) subscript: (integer) @i (#match? @f \"^(list|tuple)$\") (#eq? @i \"0\")) @match",
   "first = list(rows)[0]\n",
   "first = next(iter(rows))\n",
   "Building the full list just to read item 0 costs time and memory: use next(iter(...)).", "S8519", eq=["ruff:RUF015"], cat="performance", kind="best-practice", sev="minor")
Py("SUM-CONCATENATES-LISTS", "sum() used to concatenate lists", (PYD + "library/functions.html", "To concatenate a series of iterables, consider using", "Python docs: sum"),
   "(call function: (identifier) @f arguments: (argument_list . (_) . (list) @s .) (#eq? @f \"sum\")) @match",
   "flat = sum(chunks, [])\n",
   "flat = list(itertools.chain.from_iterable(chunks))\n",
   "Summing lists copies the accumulator at every step (quadratic): use itertools.chain.", "S8520", eq=["ruff:RUF017"], cat="performance", kind="best-practice", sev="minor")
Py("NESTED-LOOP-REUSES-VARIABLE", "Nested loop reuses the outer loop variable", (PYD + "reference/compound_stmts.html", "This overwrites all previous assignments", "Python reference: The for statement"),
   "(for_statement left: (identifier) @a body: (block (for_statement left: (identifier) @b) @match) (#eq? @a @b))",
   "def pairs(rows):\n    for r in rows:\n        for r in r.cells:\n            use(r)\n",
   "def pairs(rows):\n    for r in rows:\n        for c in r.cells:\n            use(c)\n",
   "The inner loop rebinds the outer variable, so code after it in the outer body sees the wrong value.", "S8510", eq=["ruff:PLW2901"])
Py("ALL-WITH-NON-STRING", "__all__ lists a non-string entry", (PYD + "reference/simple_stmts.html", "it must be a sequence of strings", "Python reference: The import statement"),
   "(assignment left: (identifier) @n right: [(list (identifier)) (tuple (identifier))] (#eq? @n \"__all__\")) @match",
   "__all__ = [parse, \"dump\"]\n",
   "__all__ = [\"parse\", \"dump\"]\n",
   "Names in __all__ must be strings; an object here makes 'from module import *' raise TypeError.", "S2823", eq=["ruff:PLE0604"])
Py("PREFIX-INCREMENT", "++x or --x used as an increment", (PYD + "reference/expressions.html", "The unary - (minus) operator yields the negation", "Python reference: Unary arithmetic operations"),
   "(unary_operator argument: (unary_operator) @inner) @match",
   "def step(i):\n    return ++i\n",
   "def step(i):\n    return i + 1\n",
   "Python has no ++/-- operators: this applies unary +/- twice and leaves the value unchanged.", "PreIncrementDecrement", eq=["ruff:B002"],
   filters=[r"node.has_re:^(\+\s*\+|-\s*-)"])
Py("EXCEPT-BOOLEAN-EXPRESSION", "except clause uses 'or'/'and' between exception types", (PYD + "reference/compound_stmts.html", "must evaluate to an exception type or a tuple", "Python reference: except clause"),
   "(except_clause value: [(boolean_operator) (parenthesized_expression (boolean_operator))]) @match",
   "try:\n    load()\nexcept (KeyError or ValueError):\n    pass\n",
   "try:\n    load()\nexcept (KeyError, ValueError):\n    pass\n",
   "'A or B' evaluates to A alone, so B is never caught: use a tuple.", "S5714", eq=["ruff:PLW0711"])
Py("FLOAT-EQUALITY", "Exact equality test against a float literal", (PYD + "tutorial/floatingpoint.html", "the math.isclose() function can be useful for comparing inexact values", "Python tutorial: Floating-Point Arithmetic"),
   "(comparison_operator (float) @f) @match",
   "def done(x):\n    return x == 0.3\n",
   "def done(x):\n    return math.isclose(x, 0.3)\n",
   "Most decimal fractions are not exact in binary floating point, so == on computed values is unreliable: compare with a tolerance.", "S1244",
   filters=[r"node.has_re:(==|!=)", r"cap.lacks_re:f:^0*\.0*$|^0\.0$"], mode="ai-confirm", sev="minor")
Py("LRU-CACHE-ON-METHOD", "functools cache decorator on an instance method", ("https://docs.python.org/3/faq/programming.html", "How do I cache method calls", "Python FAQ: How do I cache method calls?"),
   "(class_definition body: (block (decorated_definition (decorator [(attribute attribute: (identifier) @d) (identifier) @d (call function: [(attribute attribute: (identifier) @d) (identifier) @d])]) definition: (function_definition parameters: (parameters . (identifier) @s))) @match) (#match? @d \"^(lru_cache|cache)$\") (#eq? @s \"self\"))",
   "class Repo:\n    @functools.lru_cache\n    def load(self, key):\n        return fetch(key)\n",
   "class Repo:\n    @functools.cached_property\n    def data(self):\n        return fetch_all()\n",
   "The class-level cache keeps every instance alive as part of its keys: cache per instance or use cached_property.", "S9156", eq=["ruff:B019"], cat="performance", sev="minor")
Py("SHALLOW-COPY-ENVIRON", "copy.copy(os.environ)", (PYD + "library/os.html", "This mapping may be used to modify the environment", "Python docs: os.environ"),
   "(call function: (attribute object: (identifier) @c attribute: (identifier) @f) arguments: (argument_list . (attribute object: (identifier) @o attribute: (identifier) @e) .) (#eq? @c \"copy\") (#eq? @f \"copy\") (#eq? @o \"os\") (#eq? @e \"environ\")) @match",
   "env = copy.copy(os.environ)\nenv[\"X\"] = \"1\"\n",
   "env = os.environ.copy()\nenv[\"X\"] = \"1\"\n",
   "A shallow copy of os.environ still writes through to the real process environment: use os.environ.copy() for a plain dict.", "S9158", eq=["ruff:PLW1507"])
Py("CHMOD-DECIMAL-MODE", "File mode written as a decimal literal", (PYD + "library/os.html", "mode may take one of the following values", "Python docs: os.chmod"),
   "(call function: (attribute object: (identifier) @o attribute: (identifier) @f) arguments: (argument_list . (_) . (integer) @n) (#eq? @o \"os\") (#match? @f \"^(chmod|fchmod|lchmod|mkdir|makedirs)$\")) @match",
   "os.chmod(path, 644)\n",
   "os.chmod(path, 0o644)\n",
   "Permission bits are octal; a decimal literal like 644 grants unrelated bits: write 0o644.", "S9160",
   filters=[r"cap.lacks_re:n:^0[oOxXbB]|^0$", r"cap.has_re:n:^[0-7]{3,4}$"])
Py("CONTEXTMANAGER-WITHOUT-FINALLY", "Generator context manager without try/finally", (PYD + "library/contextlib.html", "ensure that some cleanup takes place", "Python docs: contextlib.contextmanager"),
   "(decorated_definition (decorator [(identifier) @d (attribute attribute: (identifier) @d)]) definition: (function_definition) @match (#eq? @d \"contextmanager\"))",
   "@contextmanager\ndef opened(p):\n    fh = open(p)\n    yield fh\n    fh.close()\n",
   "@contextmanager\ndef opened(p):\n    fh = open(p)\n    try:\n        yield fh\n    finally:\n        fh.close()\n",
   "If the with-block raises, the code after yield never runs: wrap the yield in try/finally.", "S9152",
   filters=[r"node.lacks_re:\btry\s*:", r"node.has_re:(?m)\byield\b[^\n]*\n\s+\S"], mode="ai-confirm", sev="minor")
Py("MOCK-MISSPELLED-ASSERT", "Mock assertion name that silently passes", (PYD + "library/unittest.mock.html", "assret", "Python docs: unittest.mock"),
   "((call function: (attribute attribute: (identifier) @a)) @match (#match? @a \"^(called_once_with|called_with|called_once|has_calls|not_called|assert_called_once_with_|assert_has_call|asert_\\\\w+|aseert_\\\\w+|assrt_\\\\w+|assret_\\\\w+)$\"))",
   "def test_send(m):\n    send(m)\n    m.called_once_with(1)\n",
   "def test_send(m):\n    send(m)\n    m.assert_called_once_with(1)\n",
   "On a Mock this name is auto-created and returns a new Mock, so nothing is checked: use the assert_* method.", "S9136", eq=["ruff:PGH005"], cat="testing")
Py("PYTEST-RAISES-NOT-CONTEXT", "pytest.raises called without a with block", ("https://docs.pytest.org/en/stable/how-to/assert.html", "pytest.raises() as a context manager", "pytest docs: Assertions about expected exceptions"),
   "(expression_statement (call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list . (_) .)) @match (#eq? @o \"pytest\") (#eq? @a \"raises\"))",
   "def test_div():\n    pytest.raises(ZeroDivisionError)\n    1 / 0\n",
   "def test_div():\n    with pytest.raises(ZeroDivisionError):\n        1 / 0\n",
   "Called alone it checks nothing and the following code runs unguarded: use it as a context manager.", "S9000", cat="testing")
Py("PYTEST-PARAMETRIZE-EMPTY", "pytest parametrize with an empty parameter list", ("https://docs.pytest.org/en/stable/reference/reference.html", "empty_parameter_set_mark", "pytest docs: empty_parameter_set_mark"),
   "(call function: (attribute attribute: (identifier) @a) arguments: (argument_list . (_) . [(list) (tuple)] @v) (#eq? @a \"parametrize\")) @match",
   "@pytest.mark.parametrize(\"x\", [])\ndef test_x(x):\n    assert x\n",
   "@pytest.mark.parametrize(\"x\", [1, 2])\ndef test_x(x):\n    assert x\n",
   "An empty parameter set means the test is skipped (by default) and never runs.", "S8998", cat="testing",
   filters=[r"cap.has_re:v:^(\[\s*\]|\(\s*\))$"])
Py("PYTEST-FIXTURE-MULTIPLE-YIELDS", "pytest fixture yields more than once", ("https://docs.pytest.org/en/stable/how-to/fixtures.html", "yield", "pytest docs: yield fixtures"),
   "(decorated_definition (decorator) @d definition: (function_definition body: [(block (expression_statement (yield)) (expression_statement (yield))) (block (with_statement body: (block (expression_statement (yield)) (expression_statement (yield)))))]) @match)",
   "@pytest.fixture\ndef db():\n    yield connect()\n    yield connect()\n",
   "@pytest.fixture\ndef db():\n    conn = connect()\n    yield conn\n    conn.close()\n",
   "pytest drives a yield fixture exactly once; a second yield makes teardown fail.", "S8994", cat="testing",
   filters=[r"cap.has_re:d:fixture"],
   fp=["@pytest.fixture\ndef m(request):\n    if request.param:\n        yield 1\n    else:\n        yield 2\n",
       "@pytest.fixture\ndef f():\n    def inner():\n        yield 1\n        yield 2\n    return inner\n",
       "@pytest.fixture\ndef files(p):\n    p.write_text(\"\"\"\nyield\nyield\n\"\"\")\n"])
Py("FLASK-ROUTE-NOT-OUTERMOST", "Route decorator is not the outermost decorator", ("https://flask.palletsprojects.com/en/stable/patterns/viewdecorators/", "outermost", "Flask docs: View Decorators"),
   "(decorated_definition (decorator) (decorator (call function: (attribute attribute: (identifier) @a))) @match (#eq? @a \"route\"))",
   "@login_required\n@app.route(\"/secret\")\ndef secret():\n    return \"s\"\n",
   "@app.route(\"/secret\")\n@login_required\ndef secret():\n    return \"s\"\n",
   "The route registers the function as it is at that point, so decorators above it are never applied to requests (e.g. auth checks are skipped).", "S6552", sev="critical")
Py("BS4-NO-PARSER", "BeautifulSoup without an explicit parser", ("https://www.crummy.com/software/BeautifulSoup/bs4/doc/", "If you don't specify anything", "Beautiful Soup docs: Specifying the parser"),
   "(call function: (identifier) @f arguments: (argument_list . (_) .) (#eq? @f \"BeautifulSoup\")) @match",
   "soup = BeautifulSoup(html)\n",
   "soup = BeautifulSoup(html, \"html.parser\")\n",
   "Without a parser argument the result depends on which parsers happen to be installed: name one.", "S8905", cat="maintainability", kind="best-practice", sev="minor")
Py("PYTZ-IN-DATETIME-CONSTRUCTOR", "pytz zone passed as tzinfo to datetime()", ("https://pythonhosted.org/pytz/", "does not work", "pytz docs"),
   "(call function: [(identifier) @f (attribute attribute: (identifier) @f)] arguments: (argument_list (keyword_argument name: (identifier) @k value: (call function: (attribute object: (identifier) @p attribute: (identifier) @t)))) (#eq? @f \"datetime\") (#eq? @k \"tzinfo\") (#eq? @p \"pytz\") (#eq? @t \"timezone\")) @match",
   "d = datetime(2024, 1, 1, tzinfo=pytz.timezone(\"Europe/Tallinn\"))\n",
   "d = pytz.timezone(\"Europe/Tallinn\").localize(datetime(2024, 1, 1))\n",
   "A pytz zone used as tzinfo picks its first historical offset (often LMT), giving wrong times: use localize() or zoneinfo.", "S6887")
Py("NP-WHERE-SINGLE-ARG", "np.where with only a condition", ("https://numpy.org/doc/stable/reference/generated/numpy.where.html", "nonzero directly should be preferred", "NumPy docs: numpy.where"),
   "(call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list . (_) .) (#match? @o \"^(np|numpy)$\") (#eq? @a \"where\")) @match",
   "idx = np.where(mask)\n",
   "idx = np.nonzero(mask)\n",
   "With one argument np.where is just nonzero(); call nonzero directly, which also handles subclasses correctly.", "S6729", cat="maintainability", kind="best-practice", sev="minor")

# ---- JavaScript/TypeScript correctness, React, test and accessibility batch -------------------
HTMLREF = "https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/"

def Js(id, title, doc, query, bad, good, msg, key, **kw):
    kw.setdefault("cat", "correctness")
    kw.setdefault("kind", "anti-pattern")
    kw.setdefault("sev", "major")
    add("javascript", id, title, doc, query, bad, good, msg, keys=[key], **kw)

def jsx_attr(id, title, doc, attr_re, bad, good, msg, key, filters=None):
    Js(id, title, doc, "(jsx_attribute (property_identifier) @a (#match? @a \"%s\")) @match" % attr_re, bad, good, msg, key,
       cat="accessibility", kind="best-practice", sev="minor", filters=filters, rlang="jsx")

Js("USELESS-POSTFIX-ASSIGN", "Variable assigned its own post-increment", (MDN + "Operators/Increment", "returns the value before incrementing", "MDN: Increment (++)"),
   "(assignment_expression left: (identifier) @l right: (update_expression argument: (identifier) @r) @u (#eq? @l @r)) @match",
   "function next(i) {\n  i = i++;\n  return i;\n}\n", "function next(i) {\n  i++;\n  return i;\n}\n",
   "x = x++ writes the old value back, so the increment is lost.", "S2123", filters=[r"cap.has_re:u:(\+\+|--)$"])
Js("ERROR-NOT-THROWN", "Error object created and discarded", (MDN + "Global_Objects/Error", "Error objects are thrown when runtime errors occur", "MDN: Error"),
   "(expression_statement (new_expression constructor: (identifier) @c (#match? @c \"Error$\")) @match)",
   "function check(x) {\n  if (x < 0) {\n    new RangeError('negative');\n  }\n}\n", "function check(x) {\n  if (x < 0) {\n    throw new RangeError('negative');\n  }\n}\n",
   "The error is constructed but never thrown, so execution silently continues: add throw.", "S3984", eq=["eslint:no-new"])
Js("CASE-WITH-COMMA-OR-OR", "switch case label uses ',' or '||'", (MDN + "Operators/Comma_operator", "returns the value of the last operand", "MDN: Comma operator"),
   "(switch_case value: [(sequence_expression) (binary_expression operator: \"||\")]) @match",
   "switch (x) {\n  case 1, 2:\n    go();\n    break;\n}\n", "switch (x) {\n  case 1:\n  case 2:\n    go();\n    break;\n}\n",
   "The label evaluates to a single value (the last operand, or the first truthy one), so the other values never match: use separate case labels.", "S3616")
Js("FOCUSED-TEST", "Focused test (.only) committed", ("https://jestjs.io/docs/api", "into source control", "Jest docs: test.only"),
   "(call_expression function: [(member_expression object: (identifier) @o property: (property_identifier) @p) (member_expression object: (member_expression object: (identifier) @o property: (property_identifier) @p))] (#match? @o \"^(it|test|describe|context|suite)$\") (#eq? @p \"only\")) @match",
   "it.only('adds', () => {\n  expect(add(1, 2)).toBe(3);\n});\n", "it('adds', () => {\n  expect(add(1, 2)).toBe(3);\n});\n",
   ".only makes the runner skip every other test in the file, so CI silently stops covering them.", "S6426", cat="testing", sev="critical")
Js("NAN-COMPARISON", "Comparison with NaN", (MDN + "Global_Objects/NaN", "compares unequal", "MDN: NaN"),
   "(binary_expression [(identifier) @n (member_expression object: (identifier) @o property: (property_identifier) @n)] (#eq? @n \"NaN\")) @match",
   "function missing(x) {\n  return x === NaN;\n}\n", "function missing(x) {\n  return Number.isNaN(x);\n}\n",
   "NaN is unequal to every value including itself, so this comparison is constant: use Number.isNaN().", "S6679", eq=["eslint:use-isnan"],
   filters=[r"node.has_re:(==|!=)"])
Js("REDUCE-WITHOUT-INITIAL", "reduce() without an initial value", (MDN + "Global_Objects/Array/reduce", "Thrown if the array contains no elements and initialValue is not provided", "MDN: Array.prototype.reduce"),
   "(call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (_) .) (#match? @p \"^reduce(Right)?$\")) @match",
   "const total = prices.reduce((a, b) => a + b);\n", "const total = prices.reduce((a, b) => a + b, 0);\n",
   "Without an initial value reduce() throws TypeError on an empty array: pass the seed value.", "S6959", mode="ai-confirm", sev="minor")
Js("BITWISE-TRUNCATION", "Double bitwise NOT used to truncate a number", (MDN + "Global_Objects/Math/trunc", "Using bitwise no-ops to truncate numbers", "MDN: Math.trunc"),
   "(unary_expression operator: \"~\" argument: (unary_expression operator: \"~\")) @match",
   "const whole = ~~ratio;\n", "const whole = Math.trunc(ratio);\n",
   "~~ converts to a 32-bit integer and silently wraps values outside that range: use Math.trunc().", "S7767", cat="maintainability", kind="best-practice", sev="minor")
Js("GLOBAL-ISNAN", "Global isNaN/isFinite used", (MDN + "Global_Objects/Number/isNaN", "more robust version", "MDN: Number.isNaN"),
   "(call_expression function: (identifier) @f (#match? @f \"^(isNaN|isFinite)$\")) @match",
   "if (isNaN(input)) {\n  reject();\n}\n", "if (Number.isNaN(Number(input))) {\n  reject();\n}\n",
   "The global versions coerce their argument first (isNaN('abc') is true): use Number.isNaN / Number.isFinite.", "S7773", cat="maintainability", kind="best-practice", sev="minor")
Js("MAP-PARSEINT", "parseInt passed directly to map()", (MDN + "Global_Objects/Array/map", "Using parseInt() with map()", "MDN: Array.prototype.map"),
   "(call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (identifier) @f .) (#eq? @p \"map\") (#eq? @f \"parseInt\")) @match",
   "const nums = parts.map(parseInt);\n", "const nums = parts.map((s) => parseInt(s, 10));\n",
   "map passes the index as parseInt's radix, so ['1','2','3'] becomes [1, NaN, NaN]: wrap it in an arrow.", "S7727")
Js("SETSTATE-WITH-OWN-VALUE", "React state setter called with its own state variable", ("https://react.dev/reference/react/useState", "Object.is", "React docs: useState"),
   "(variable_declarator name: (array_pattern . (identifier) @v . (identifier) @s) value: (call_expression function: [(identifier) @h (member_expression property: (property_identifier) @h)]) (#eq? @h \"useState\")) @match",
   "function C() {\n  const [count, setCount] = useState(0);\n  const reset = () => setCount(count);\n  return reset;\n}\n",
   "function C() {\n  const [count, setCount] = useState(0);\n  const inc = () => setCount(count + 1);\n  return inc;\n}\n",
   "Setting state to its current value is a no-op (React compares with Object.is): pass the intended new value.", "S6443",
   filters=[r"func.count_ge:1:\b{cap:s}\(\s*{cap:v}\s*\)"])
Js("RENDER-WITHOUT-RETURN", "Class component render() without return", ("https://react.dev/reference/react/Component", "the render method should return a piece of JSX", "React docs: Component.render"),
   "(class_body (method_definition name: (property_identifier) @n body: (statement_block) @b) @match (#eq? @n \"render\"))",
   "class Card extends React.Component {\n  render() {\n    <div>{this.props.title}</div>;\n  }\n}\n",
   "class Card extends React.Component {\n  render() {\n    return <div>{this.props.title}</div>;\n  }\n}\n",
   "render() returns undefined here, so nothing is rendered.", "S6435", filters=[r"cap.lacks_re:b:\b(return|throw)\b"])
Js("CHILDREN-WITH-INNERHTML", "Element has both children and dangerouslySetInnerHTML", ("https://react.dev/reference/react-dom/components/common", "You cannot pass both children and dangerouslySetInnerHTML at the same time", "React docs: Common components"),
   "(jsx_element open_tag: (jsx_opening_element (jsx_attribute (property_identifier) @a)) [(jsx_element) (jsx_self_closing_element) (jsx_expression)] (#eq? @a \"dangerouslySetInnerHTML\")) @match",
   "const A = ({ html }) => (\n  <div dangerouslySetInnerHTML={{ __html: html }}>\n    <span>x</span>\n  </div>\n);\n",
   "const A = ({ html }) => <div dangerouslySetInnerHTML={{ __html: html }} />;\n",
   "React throws when an element gets both children and dangerouslySetInnerHTML: keep only one.", "S6761", rlang="jsx")
Js("JSX-COMMENT-AS-TEXT", "Comment syntax rendered as JSX text", ("https://react.dev/learn/writing-markup-with-jsx", "JSX", "React docs: Writing Markup with JSX"),
   "(jsx_text) @match",
   "const A = () => <div>// TODO label</div>;\n", "const A = () => <div>{/* TODO label */}</div>;\n",
   "Inside JSX text a // or /* comment is printed to the page: wrap it as {/* ... */}.", "S6438",
   filters=[r"node.has_re:^\s*(//|/\*)"], rlang="jsx")
Js("JSX-NUMBER-AND", "Numeric length on the left of && in JSX", ("https://react.dev/learn/conditional-rendering", "left side of", "React docs: Conditional Rendering"),
   "(jsx_expression (binary_expression left: (member_expression property: (property_identifier) @p) right: [(jsx_element) (jsx_self_closing_element)]) @match (#match? @p \"^(length|size)$\"))",
   "const L = ({ items }) => <div>{items.length && <List items={items} />}</div>;\n",
   "const L = ({ items }) => <div>{items.length > 0 && <List items={items} />}</div>;\n",
   "When the count is 0, React renders the 0 itself: compare explicitly (length > 0).", "S6439",
   filters=[r"node.has_re:&&"], rlang="jsx")
Js("REACT-ISMOUNTED", "isMounted() used in a component", ("https://legacy.reactjs.org/blog/2015/12/16/ismounted-antipattern.html", "isMounted is an Antipattern", "React blog: isMounted is an Antipattern"),
   "(call_expression function: (member_expression object: (this) property: (property_identifier) @p) (#eq? @p \"isMounted\")) @match",
   "class A extends React.Component {\n  done(v) {\n    if (this.isMounted()) {\n      this.setState({ v });\n    }\n  }\n}\n",
   "class A extends React.Component {\n  componentWillUnmount() {\n    this.request.abort();\n  }\n}\n",
   "isMounted is unavailable on ES classes and hides leaks: cancel pending work in componentWillUnmount.", "S6789", cat="maintainability", kind="deprecation", sev="minor")
Js("DUPLICATE-PARAMETER", "Function declares the same parameter twice", es("no-dupe-args"),
   "(formal_parameters (_) @a (_) @b (#eq? @a @b)) @match",
   "function area(w, w) {\n  return w * w;\n}\n", "function area(w, h) {\n  return w * h;\n}\n",
   "The later parameter shadows the earlier one, so one argument is silently ignored (and strict mode rejects it).", "S1536", eq=["eslint:no-dupe-args"])
Js("GETTER-RECURSION", "Getter returns its own property", (MDN + "Functions/get", "binds an object property to a function", "MDN: get"),
   "(method_definition name: (property_identifier) @n body: (statement_block (return_statement (member_expression object: (this) property: (property_identifier) @m))) (#eq? @n @m)) @match",
   "class User {\n  get name() {\n    return this.name;\n  }\n}\n", "class User {\n  get name() {\n    return this._name;\n  }\n}\n",
   "Reading the property calls the getter again, recursing until the stack overflows: back it with a different field.", "S7725",
   filters=[r"node.has_re:^(static\s+)?get\s"])
Js("STRICT-RESERVED-IDENTIFIER", "Strict-mode reserved word used as identifier", (MDN + "Lexical_grammar", "only reserved when", "MDN: Lexical grammar"),
   "(variable_declarator name: (identifier) @n (#match? @n \"^(implements|interface|package|private|protected|public|static)$\")) @match",
   "var package = load();\n", "var pkg = load();\n",
   "This name is reserved in strict mode (modules and classes), so the code breaks when moved there.", "S1527", cat="maintainability", kind="best-practice", sev="minor")
Js("BITWISE-IN-CONDITION", "Bitwise & or | between comparisons", (MDN + "Operators/Bitwise_AND", "returns a number or BigInt", "MDN: Bitwise AND"),
   "(binary_expression left: (binary_expression operator: [\"===\" \"!==\" \"==\" \"!=\" \"<\" \">\" \"<=\" \">=\"]) operator: [\"&\" \"|\"] right: (binary_expression operator: [\"===\" \"!==\" \"==\" \"!=\" \"<\" \">\" \"<=\" \">=\"])) @match",
   "if (a > 0 & b > 0) {\n  go();\n}\n", "if (a > 0 && b > 0) {\n  go();\n}\n",
   "& and | evaluate both sides and yield a number, not a boolean: use && or ||.", "S1529")
Js("MUTABLE-EXPORT", "Exported mutable binding", (MDN + "Statements/export", "The value of an imported binding is subject to change in the module that exports it", "MDN: export"),
   "(export_statement declaration: [(lexical_declaration) (variable_declaration)]) @match",
   "export let current = null;\n", "let current = null;\nexport function getCurrent() {\n  return current;\n}\n",
   "Importers see reassignments as live bindings, which makes state changes hard to follow: export a const or accessor.", "S6861",
   cat="maintainability", kind="best-practice", sev="minor", filters=[r"node.has_re:^export\s+(let|var)\b"])
Js("CYPRESS-DEBUG-COMMAND", "cy.pause()/cy.debug() left in a test", ("https://docs.cypress.io/api/commands/pause", "Stop cy commands from running", "Cypress docs: pause"),
   "(call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments) @args (#match? @p \"^(pause|debug)$\")) @match",
   "it('logs in', () => {\n  cy.visit('/');\n  cy.pause();\n});\n", "it('logs in', () => {\n  cy.visit('/');\n});\n",
   "A pause/debug command halts the run waiting for interaction, so headless CI hangs or the step is meaningless.", "S8959", cat="testing",
   filters=[r"node.has_re:^cy\b", r"cap.has_re:args:^\(\s*\)$"])
Js("ASSERT-SAME-ARGUMENT", "expect() compares a value with itself", ("https://jestjs.io/docs/expect", "The expect function is used every time you want to test a value", "Jest docs: expect"),
   "(call_expression function: (member_expression object: (call_expression function: (identifier) @e arguments: (arguments . (_) @a .)) property: (property_identifier) @m) arguments: (arguments . (_) @b .) (#eq? @e \"expect\") (#match? @m \"^(toBe|toEqual|toStrictEqual)$\") (#eq? @a @b)) @match",
   "test('sum', () => {\n  const s = sum(1, 2);\n  expect(s).toBe(s);\n});\n", "test('sum', () => {\n  const s = sum(1, 2);\n  expect(s).toBe(3);\n});\n",
   "Both sides are the same expression, so the assertion always passes and tests nothing.", "S5863", cat="testing")
Js("FLOAT-EQUALITY", "Exact equality test against a fractional literal", (MDN + "Global_Objects/Number/EPSILON", "Number.EPSILON", "MDN: Number.EPSILON"),
   "(binary_expression (number) @n) @match",
   "const ok = total === 0.3;\n", "const ok = Math.abs(total - 0.3) < 1e-9;\n",
   "Fractions like 0.1 are not exact in binary floating point, so computed values rarely compare equal: use a tolerance.", "S1244",
   filters=[r"node.has_re:(===?|!==?)", r"cap.has_re:n:^\d*\.\d*[1-9]"], mode="ai-confirm", sev="minor")
Js("TEST-WITHOUT-ASSERTION", "Test case without any assertion", ("https://jestjs.io/docs/expect", "The expect function is used every time you want to test a value", "Jest docs: expect"),
   "(call_expression function: (identifier) @t arguments: (arguments . (string) . [(arrow_function body: (statement_block) @b) (function_expression body: (statement_block) @b)]) (#match? @t \"^(it|test)$\")) @match",
   "it('adds', () => {\n  add(1, 2);\n});\n", "it('adds', () => {\n  expect(add(1, 2)).toBe(3);\n});\n",
   "Without an assertion the test passes whatever the code does.", "S2699", cat="testing", mode="ai-confirm", sev="minor",
   filters=[r"cap.lacks_re:b:(?i)(expect|assert|should|verify|check|\bt\.|cy\.|snapshot|toThrow|rejects)"])
Js("INFINITE-LOOP", "Loop with a constant true condition and no exit", (MDN + "Statements/while", "while", "MDN: while"),
   "[(while_statement condition: (parenthesized_expression (true))) (for_statement)] @match",
   "function spin(q) {\n  while (true) {\n    q.poll();\n  }\n}\n", "function spin(q) {\n  while (true) {\n    if (!q.poll()) break;\n  }\n}\n",
   "Nothing in the body leaves the loop, so it never terminates.", "S2189", mode="ai-confirm",
   filters=[r"node.has_re:^(while\s*\(\s*true\s*\)|for\s*\(\s*;\s*;\s*\))", r"node.lacks_re:\b(break|return|throw|yield|exit|await)\b"])
jsx_attr("ACCESSKEY-ATTRIBUTE", "accessKey attribute used", (HTMLREF + "Global_attributes/accesskey", "Accessibility concerns", "MDN: accesskey"),
   "^access[Kk]ey$", "const B = () => <button accessKey=\"s\">Save</button>;\n", "const B = () => <button>Save</button>;\n",
   "Access keys clash with browser and assistive-technology shortcuts: rely on normal focus order instead.", "S6846")
jsx_attr("AUTOFOCUS-ATTRIBUTE", "autoFocus attribute used", (HTMLREF + "Global_attributes/autofocus", "Accessibility concerns", "MDN: autofocus"),
   "^auto[Ff]ocus$", "const F = () => <input autoFocus />;\n", "const F = () => <input />;\n",
   "Moving focus on load can disorient screen-reader and keyboard users.", "S9379", filters=[r"node.lacks_re:\{\s*false\s*\}"])
jsx_attr("POSITIVE-TABINDEX", "tabIndex greater than zero", (HTMLREF + "Global_attributes/tabindex", "greater than 0", "MDN: tabindex"),
   "^tab[Ii]ndex$", "const B = () => <div tabIndex={3}>x</div>;\n", "const B = () => <div tabIndex={0}>x</div>;\n",
   "Positive tabindex values override the natural focus order and confuse keyboard users: use 0 or -1.", "S6841",
   filters=[r"node.has_re:=\s*(\{\s*)?[\x22']?\s*[1-9]"])
Js("SCOPE-ON-NON-TH", "scope attribute on an element other than th", (HTMLREF + "Elements/th", "scope", "MDN: <th>"),
   "([(jsx_opening_element name: (identifier) @e (jsx_attribute (property_identifier) @a)) (jsx_self_closing_element name: (identifier) @e (jsx_attribute (property_identifier) @a))] @match (#eq? @a \"scope\"))",
   "const C = () => <td scope=\"col\">Name</td>;\n", "const C = () => <th scope=\"col\">Name</th>;\n",
   "scope only has meaning on th header cells; elsewhere assistive technology ignores it.", "S9380",
   cat="accessibility", kind="best-practice", sev="minor", filters=[r"cap.has_re:e:^[a-z]", r"cap.lacks_re:e:^th$"], rlang="jsx")

# ---- Go: context, transactions, busy waiting ---------------------------------------------------
def G(id, title, doc, query, bad, good, msg, key, **kw):
    kw.setdefault("cat", "correctness")
    kw.setdefault("kind", "anti-pattern")
    kw.setdefault("sev", "major")
    add("go", id, title, doc, query, bad, good, msg, keys=[key], **kw)

def gof(body, sig="func f(ctx context.Context, db *sql.DB) error"):
    return "package p\n\n" + sig + " {\n" + "".join("\t" + l + "\n" for l in body) + "}\n"

G("BACKGROUND-CONTEXT-WITH-CTX", "New background context where a ctx parameter exists", ("https://pkg.go.dev/context", "It is typically used by the main function", "Go docs: context.Background"),
  "(call_expression function: (selector_expression operand: (identifier) @p field: (field_identifier) @f) (#eq? @p \"context\") (#match? @f \"^(Background|TODO)$\")) @match",
  gof(["return load(context.Background(), db)"]), gof(["return load(ctx, db)"]),
  "The function already receives a ctx; starting from Background drops its cancellation and deadline. Pass ctx (or context.WithoutCancel(ctx) for deliberately detached work).",
  "godre:S8239", mode="ai-confirm", sev="minor",
  # the ctx must be a parameter of the innermost enclosing function, not of some closure in its body
  filters=[r"ancestor.has_re:function_declaration|method_declaration|func_literal:^[^{]*\b\w*[cC]tx\s+context\.Context\b"],
  fp=[gof(["ctx := context.Background()", "h := func(ctx context.Context) error { return nil }", "return h(ctx)"], sig="func f(db *sql.DB) error")])
G("TX-WITHOUT-ROLLBACK", "Transaction committed without a rollback path", ("https://go.dev/doc/database/execute-transactions", "Defer a rollback", "Go docs: Executing transactions"),
  "(short_var_declaration left: (expression_list . (identifier) @v) right: (expression_list (call_expression function: (selector_expression field: (field_identifier) @f))) (#match? @f \"^(Begin|BeginTx)$\")) @match",
  gof(["tx, err := db.BeginTx(ctx, nil)", "if err != nil {", "\treturn err", "}", "if _, err := tx.ExecContext(ctx, q); err != nil {", "\treturn err", "}", "return tx.Commit()"]),
  gof(["tx, err := db.BeginTx(ctx, nil)", "if err != nil {", "\treturn err", "}", "defer tx.Rollback()", "if _, err := tx.ExecContext(ctx, q); err != nil {", "\treturn err", "}", "return tx.Commit()"]),
  "An early return leaves the transaction open, holding its connection and locks: defer tx.Rollback() right after Begin.",
  "godre:S8168", filters=[r"func.has_re:\b{cap:v}\.Commit\(", r"func.lacks_re:\b{cap:v}\.Rollback\("])
G("BUSY-WAIT-LOOP", "Loop that spins with an empty body", ("https://go.dev/ref/mem", "Another incorrect idiom is busy waiting for a value", "The Go Memory Model"),
  "(for_statement body: (block) @b) @match",
  gof(["for !ready {", "}", "return nil"], "func f(ready bool) error"), gof(["<-readyCh", "return nil"], "func f(readyCh chan struct{}) error"),
  "Spinning on a variable burns a CPU and, without synchronisation, may never observe the write: wait on a channel, sync.WaitGroup or sync.Cond.",
  "godre:S8259", filters=[r"node.has_re:^for(\s+[^;{]*)?\s*\{\s*\}$", r"node.lacks_re:^for[^{]*\brange\b"])

# ---- Kotlin: JVM API misuse, sequences/flows, data classes -------------------------------------
KTDOC = "https://kotlinlang.org/docs/"
ARRAY_T = "(Array|IntArray|LongArray|ByteArray|CharArray|ShortArray|DoubleArray|FloatArray|BooleanArray|UIntArray|ULongArray)"

def K(id, title, doc, query, bad, good, msg, key, **kw):
    kw.setdefault("cat", "correctness")
    kw.setdefault("kind", "anti-pattern")
    kw.setdefault("sev", "major")
    add("kotlin", id, title, doc, query, bad, good, msg, keys=[key] if isinstance(key, str) else list(key), **kw)

def kf(body, sig="fun f()"):
    return sig + " {\n" + "".join("    " + l + "\n" for l in body) + "}\n"

K("DATA-CLASS-ARRAY-PROPERTY", "Data class with an array property", (KTDOC + "arrays.html", "Use .contentEquals() instead", "Kotlin docs: Arrays"),
  "(class_declaration (modifiers (class_modifier) @m) (primary_constructor (class_parameters (class_parameter (user_type (identifier) @t)))) (#eq? @m \"data\") (#match? @t \"^%s$\")) @match" % ARRAY_T,
  "data class Packet(val id: Int, val payload: ByteArray)\n", "data class Packet(val id: Int, val payload: List<Byte>)\n",
  "Generated equals/hashCode compare arrays by reference, so equal contents are unequal: use a List or override equals/hashCode with contentEquals.", "S6218")
K("COLLECTION-SELF-ARGUMENT", "Collection passed to its own method", (JAPI + "util/Collection.html", "The behavior of this operation is undefined if the specified collection is modified while the operation is in progress", "Java SE 21 API: Collection.addAll"),
  "(call_expression (navigation_expression (identifier) @r (identifier) @m) (value_arguments . (value_argument (identifier) @a) .) (#eq? @r @a) (#match? @m \"^(addAll|removeAll|retainAll|containsAll)$\")) @match",
  kf(["xs.addAll(xs)"], "fun f(xs: MutableList<Int>)"), kf(["xs.addAll(ys)"], "fun f(xs: MutableList<Int>, ys: List<Int>)"),
  "Passing a collection to its own bulk method is either a no-op, clears it, or is undefined while it is modified: pass a different collection.", "S2114")
K("SCHEDULED-POOL-ZERO-CORE", "ScheduledThreadPoolExecutor with zero core threads", (JAPI + "util/concurrent/ScheduledThreadPoolExecutor.html", "it acts as a fixed-sized pool using corePoolSize threads", "Java SE 21 API: ScheduledThreadPoolExecutor"),
  "(call_expression (identifier) @t (value_arguments . (value_argument (number_literal) @n)) (#eq? @t \"ScheduledThreadPoolExecutor\") (#eq? @n \"0\")) @match",
  kf(["val pool = ScheduledThreadPoolExecutor(0)"]), kf(["val pool = ScheduledThreadPoolExecutor(1)"]),
  "The pool size is fixed at corePoolSize, so with 0 no scheduled task ever runs: use at least 1.", "S2122")
K("USELESS-POSTFIX-ASSIGN", "Variable assigned its own post-increment", (KTDOC + "operator-overloading.html", "Increments and decrements", "Kotlin docs: Increments and decrements"),
  "(assignment left: (identifier) @l right: (unary_expression argument: (identifier) @r) @u (#eq? @l @r)) @match",
  kf(["var i = n", "i = i++", "use(i)"], "fun f(n: Int)"), kf(["var i = n", "i++", "use(i)"], "fun f(n: Int)"),
  "x = x++ stores the old value back, so the increment is lost.", "S2123", filters=[r"cap.has_re:u:(\+\+|--)$"])
K("RUN-FINALIZERS-ON-EXIT", "runFinalizersOnExit called", ("https://docs.oracle.com/en/java/javase/11/migrate/index.html", "java.lang.Runtime.runFinalizersOnExit(boolean)", "JDK 11 Migration Guide: APIs removed"),
  "(call_expression (navigation_expression (_) (identifier) @m) (#eq? @m \"runFinalizersOnExit\")) @match",
  kf(["System.runFinalizersOnExit(true)"]), kf(["Runtime.getRuntime().addShutdownHook(Thread { flush() })"]),
  "runFinalizersOnExit is inherently unsafe and was removed from the JDK: use a shutdown hook.", "S2151",
  eq=["https://docs.oracle.com/javase/8/docs/api/java/lang/Runtime.html#runFinalizersOnExit-boolean-"])
K("JDBC-ZERO-INDEX", "JDBC parameter index 0", ("https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/PreparedStatement.html", "the first parameter is 1", "Java SE 21 API: PreparedStatement"),
  "(call_expression (navigation_expression (identifier) @r (identifier) @m) (value_arguments . (value_argument (number_literal) @n) . (value_argument)) (#match? @m \"^set(String|Int|Long|Short|Byte|Boolean|Double|Float|BigDecimal|Object|Date|Time|Timestamp|Bytes|Null)$\") (#eq? @n \"0\")) @match",
  kf(["ps.setString(0, name)"], "fun f(ps: PreparedStatement, name: String)"), kf(["ps.setString(1, name)"], "fun f(ps: PreparedStatement, name: String)"),
  "JDBC parameter indices start at 1, so index 0 throws SQLException.", "S2695", filters=[r"cap.has_re:r:(?i)(stmt|statement|ps|pst|prepared|query|call)"])
K("SEQUENCE-NOT-CONSUMED", "Lazy sequence or stream pipeline never consumed", (KTDOC + "sequences.html", "Sequence elements can be retrieved only with terminal operations", "Kotlin docs: Sequences"),
  "(block (call_expression (navigation_expression (_) @recv (identifier) @m)) @match)",
  kf(["xs.asSequence().map { audit(it) }"], "fun f(xs: List<Int>)"), kf(["xs.asSequence().map { audit(it) }.toList()"], "fun f(xs: List<Int>)"),
  "Intermediate sequence/stream operations are lazy; without a terminal operation the lambda never runs.", ["S3958"],
  filters=[r"cap.has_re:recv:(asSequence\(\)|\.stream\(\)|sequenceOf\(|generateSequence\(|^sequence\s*\{)", r"cap.has_re:m:^(map|filter|filterNot|flatMap|mapNotNull|onEach|sorted|sortedBy|distinct|take|drop|peek|mapIndexed|filterIsInstance|zip)$"])
K("FLOW-NOT-COLLECTED", "Flow operator chain never collected", ("https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines.flow/-flow/", "This is known as a cold flow property", "kotlinx.coroutines API: Flow"),
  "(block (call_expression (navigation_expression (_) @recv (identifier) @m)) @match)",
  kf(["events.asFlow().onEach { log(it) }"], "suspend fun f(events: List<Int>)"), kf(["events.asFlow().onEach { log(it) }.collect()"], "suspend fun f(events: List<Int>)"),
  "Flows are cold: intermediate operators do nothing until a terminal operator such as collect or launchIn runs.", ["S6314"],
  filters=[r"cap.has_re:recv:(\.asFlow\(\)|flowOf\(|^flow\s*\{|channelFlow\s*\{|callbackFlow\s*\{)", r"cap.has_re:m:^(map|filter|filterNot|onEach|transform|take|drop|distinctUntilChanged|debounce|catch|onStart|onCompletion|flowOn|buffer|conflate|mapLatest|flatMapLatest|flatMapConcat|flatMapMerge)$"])
K("INDEX-NOT-NULL-ASSERTED", "Map lookup forced with !!", (KTDOC + "null-safety.html", "Usage of the not-null assertion operator", "Kotlin docs: Null safety"),
  "(unary_expression argument: (index_expression) @i) @match",
  kf(["val port = cfg[\"port\"]!!", "use(port)"], "fun f(cfg: Map<String, Int>)"), kf(["val port = cfg.getValue(\"port\")", "use(port)"], "fun f(cfg: Map<String, Int>)"),
  "A missing key turns into a bare NullPointerException: use getValue (descriptive error), getOrElse or ?: with a clear failure.", "S6611",
  filters=[r"node.has_re:!!$"], mode="ai-confirm", sev="minor")
K("ARRAY-TOSTRING-HASHCODE", "toString/hashCode called on an array", (JAPI + "lang/Object.html", "Integer.toHexString(hashCode())", "Java SE 21 API: Object.toString"),
  "(call_expression (navigation_expression (identifier) @r (identifier) @m) (value_arguments) (#match? @m \"^(toString|hashCode)$\")) @match",
  kf(["val ids = intArrayOf(1, 2)", "log(ids.toString())"]), kf(["val ids = intArrayOf(1, 2)", "log(ids.contentToString())"]),
  "Arrays inherit identity-based toString/hashCode, giving output like [I@1b6d3586: use contentToString()/contentHashCode().", "S2116",
  filters=[r"node.has_re:\(\s*\)$", r"func.has_re:\b(val|var)\s+{cap:r}\s*(=\s*(arrayOf|intArrayOf|longArrayOf|byteArrayOf|charArrayOf|shortArrayOf|doubleArrayOf|floatArrayOf|booleanArrayOf|arrayOfNulls)\b|:\s*" + ARRAY_T + r"\b)|\b{cap:r}\s*:\s*" + ARRAY_T + r"\b"])

# ---- PHP: correctness and PHPUnit batch --------------------------------------------------------
PHPUNIT = "https://docs.phpunit.de/en/12.4/"
PURE_PHP = ("strtoupper|strtolower|ucfirst|lcfirst|ucwords|trim|ltrim|rtrim|str_replace|str_ireplace|substr|str_pad|str_repeat|sprintf|implode|explode|"
            "array_merge|array_map|array_filter|array_slice|array_reverse|array_keys|array_values|array_unique|array_combine|array_flip|array_column|"
            "htmlspecialchars|json_encode|json_decode|intval|floatval|strval|boolval|abs|round|floor|ceil|max|min|count|strlen|mb_strlen|"
            "mb_strtoupper|mb_strtolower|mb_substr|nl2br|number_format|preg_quote|base64_encode|base64_decode|md5|sha1|hash|urlencode|rawurlencode")

def Ph(id, title, doc, query, bad, good, msg, key, **kw):
    kw.setdefault("cat", "correctness")
    kw.setdefault("kind", "anti-pattern")
    kw.setdefault("sev", "major")
    add("php", id, title, doc, query, bad, good, msg, keys=[key], **kw)

def phf(body, sig="function f($a, $xs)"):
    return "<?php\n" + sig + "\n{\n" + "".join("    " + l + "\n" for l in body) + "}\n"

Ph("OBJECT-CREATED-AND-DROPPED", "Object created and immediately discarded", (PHPM + "language.oop5.basic.php", "the new keyword must be used", "PHP manual: new"),
   "(expression_statement (object_creation_expression) @match)",
   phf(["if ($a < 0) {", "    new InvalidArgumentException('negative');", "}"]), phf(["if ($a < 0) {", "    throw new InvalidArgumentException('negative');", "}"]),
   "The new object is never used; for an exception this means it was meant to be thrown. Throw, assign or remove it.", "S1848",
   # a test that expects the constructor to throw creates the object only for that side effect
   filters=[r"func.lacks_re:expectException|setExpectedException|@expectedException|assertThrows|->toThrow"],
   # corpus: tests construct objects for constructor side effects (creates a directory, rejects input in try/catch)
   files=["!**/tests/**", "!**/Tests/**", "!**/test/**", "!**/*Test.php"],
   fp=["<?php\nclass ATest extends TestCase {\n    public function testRejects(): void {\n        $this->expectException(\\InvalidArgumentException::class);\n        new Adapter('');\n    }\n}\n"])
Ph("EXCEPTION-NOT-THROWN", "Exception object created and discarded", (PHPM + "language.oop5.basic.php", "the new keyword must be used", "PHP manual: new"),
   "(expression_statement (object_creation_expression [(name) @c (qualified_name (name) @c)]) @match (#match? @c \"(Exception|Error)$\"))",
   phf(["if ($a < 0) {", "    new RuntimeException('negative');", "}"]), phf(["if ($a < 0) {", "    throw new RuntimeException('negative');", "}"]),
   "The exception is constructed but never thrown, so execution silently continues: add throw.", "S3984")
Ph("USELESS-POSTFIX-ASSIGN", "Variable assigned its own post-increment", (PHPM + "language.operators.increment.php", "then increments $a by one", "PHP manual: Incrementing/Decrementing Operators"),
   "(assignment_expression left: (variable_name) @l right: (update_expression argument: (variable_name) @r) @u (#eq? @l @r)) @match",
   phf(["$a = $a++;", "return $a;"]), phf(["$a++;", "return $a;"]),
   "$x = $x++ writes the old value back, so the increment is lost.", "S2123", filters=[r"cap.has_re:u:(\+\+|--)$"])
Ph("VARIABLE-VARIABLE", "Variable variable used", (PHPM + "language.variables.variable.php", "variable variable names", "PHP manual: Variable variables"),
   "(dynamic_variable_name) @match",
   phf(["$$a = 1;"]), phf(["$values[$a] = 1;"]),
   "Variable names chosen at runtime hide data flow from readers and tools: use an array keyed by the name.", "S1599", cat="maintainability", kind="best-practice", sev="minor",
   filters=[r"node.lacks_re:^\$\{[A-Za-z_]\w*\}$"], fp=[phf(["echo \"go ${a} now\";"])])
Ph("THIS-IN-STATIC", "$this used inside a static method", (PHPM + "language.oop5.static.php", "is not available inside", "PHP manual: Static Keyword"),
   "(method_declaration (static_modifier) body: (compound_statement) @b) @match",
   "<?php\nclass Counter\n{\n    public static function next()\n    {\n        return $this->n + 1;\n    }\n}\n",
   "<?php\nclass Counter\n{\n    public static function next()\n    {\n        return self::$n + 1;\n    }\n}\n",
   "$this does not exist in a static method, so this throws an Error at runtime.", "S2014",
   filters=[r"cap.has_re:b:\$this\b", r"cap.lacks_re:b:\bfunction\s*\(|\bfn\s*\(|\bnew\s+class\b"],
   fp=["<?php\nclass Factory\n{\n    private static function make(array &$events)\n    {\n        return new class($events) {\n            public function __construct(private array &$events) {}\n            public function get() { return $this->events; }\n        };\n    }\n}\n"])
Ph("FOREACH-REFERENCE-NOT-UNSET", "foreach by reference without unset afterwards", (PHPM + "control-structures.foreach.php", "It is recommended to destroy it using unset()", "PHP manual: foreach"),
   "(foreach_statement (by_ref (variable_name) @v)) @match",
   phf(["foreach ($xs as &$x) {", "    $x *= 2;", "}", "return $xs;"]), phf(["foreach ($xs as &$x) {", "    $x *= 2;", "}", "unset($x);", "return $xs;"]),
   "The reference survives the loop, so a later write to the variable silently overwrites the last element: unset() it after the loop.", "S4824",
   filters=[r"func.count_lt:1:unset\([^)]*{cap:v}"])
Ph("SWITCH-FALLTHROUGH", "switch case falls through to the next case", (PHPSWITCH, "go on executing the statements of the following case", "PHP manual: switch"),
   "(switch_block (case_statement (_) @last .) @c . [(case_statement) (default_statement)]) @match",
   phf(["switch ($a) {", "    case 1:", "        start();", "    case 2:", "        stop();", "        break;", "}"]),
   phf(["switch ($a) {", "    case 1:", "        start();", "        break;", "    case 2:", "        stop();", "        break;", "}"]),
   "Without break the next case's statements run too; add break/return, or comment an intended fall-through.", "S128",
   fp=[phf(["switch ($a) {", "    case Rule::ROOT:", "        return 1;", "    case Rule::FIXED:", "    case Rule::LOCKED:", "        return 3;", "}"]),
       phf(["switch ($a) {", "    case 1:", "        $n = count($xs);", "        log($n);", "        return 'add ' . implode(' and ', array_map(static function ($x) {", "            return $x;", "        }, $xs)) . ' now';", "    case 2:", "        return '';", "}"])],
   filters=[r"cap.has_re:c:^case\s+(?:[^:]|::)+?:\s*[^\s:]", r"cap.lacks_re:c:\b(break|return|throw|continue|exit|die|goto)\b[^;]*;\s*(//[^\n]*|/\*[\s\S]*?\*/|\s)*$", r"cap.lacks_re:c:(?i)fall[s -]?through|no break",
            r"cap.has_re:last:(;|\})\s*$", r"cap.lacks_re:last:^(break|return|throw|continue|exit|die|goto)\b|\b(break|return|throw|continue)\b[^;]*;(\s|\})*$"])
Ph("STATEMENT-WITHOUT-EFFECT", "Expression statement with no effect", (PHPM + "language.expressions.php", "Expressions are the most important building blocks", "PHP manual: Expressions"),
   "(expression_statement [(binary_expression) (variable_name) (integer) (string) (encapsed_string)] @match)",
   phf(["$a == 1;", "return $a;"]), phf(["$a = 1;", "return $a;"]),
   "The value is computed and thrown away; this is usually a mistyped assignment or a leftover.", "S905",
   filters=[r"node.lacks_re:(\?\?|\|\||&&|\bor\b|\band\b)"])
Ph("IGNORED-PURE-RESULT", "Result of a side-effect-free function ignored", (PHPM + "function.strtoupper.php", "Returns the uppercased string", "PHP manual: strtoupper"),
   "(expression_statement (function_call_expression function: (name) @f) @match (#match? @f \"^(%s)$\"))" % PURE_PHP,
   phf(["trim($a);", "return $a;"]), phf(["$a = trim($a);", "return $a;"]),
   "This function returns a new value and changes nothing; ignoring the result makes the call useless.", "S2201")
Ph("FOR-UPDATE-WRONG-DIRECTION", "for loop counter moves away from its bound", (PHPM + "control-structures.for.php", "for", "PHP manual: for"),
   "(for_statement) @match",
   phf(["for ($i = 0; $i < count($xs); $i--) {", "    echo $xs[$i];", "}"]), phf(["for ($i = 0; $i < count($xs); $i++) {", "    echo $xs[$i];", "}"]),
   "The counter moves away from the bound in the condition, so the loop runs until overflow: fix the update.", "S2251",
   filters=[r"node.has_re:^for\s*\([^;]*;\s*(\$\w+)\s*<=?[^;]*;\s*(\$\w+\s*--|--\s*\$\w+)\s*\)|^for\s*\([^;]*;\s*(\$\w+)\s*>=?[^;]*;\s*(\$\w+\s*\+\+|\+\+\s*\$\w+)\s*\)"])
Ph("REPEATED-UNARY", "Unary operator applied twice", (PHPM + "language.operators.arithmetic.php", "Negation", "PHP manual: Arithmetic Operators"),
   "(unary_op_expression (unary_op_expression)) @match",
   phf(["return - -$a;"]), phf(["return $a;"]),
   "Applying the same unary operator twice cancels out (or is a typo).", "S2761", filters=[r"node.has_re:^(-\s*-|~\s*~|\+\s*\+|!\s*!\s*!)"])
Ph("ASSERT-SAME-ARGUMENT", "PHPUnit assertion compares a value with itself", (PHPUNIT + "assertions.html", "assertSame", "PHPUnit docs: Assertions"),
   "(member_call_expression name: (name) @m arguments: (arguments . (argument) @a . (argument) @b) (#match? @m \"^assert(Same|NotSame|Equals|NotEquals|EqualsCanonicalizing|GreaterThan|LessThan)$\") (#eq? @a @b)) @match",
   "<?php\nclass PriceTest extends TestCase\n{\n    public function testTotal(): void\n    {\n        $t = total();\n        $this->assertSame($t, $t);\n    }\n}\n",
   "<?php\nclass PriceTest extends TestCase\n{\n    public function testTotal(): void\n    {\n        $t = total();\n        $this->assertSame(42, $t);\n    }\n}\n",
   "Both arguments are the same expression, so the assertion can never fail.", "S5863", cat="testing")
Ph("TEST-WITHOUT-ASSERTION", "PHPUnit test method without assertions", (PHPUNIT + "risky-tests.html", "tests that do not perform assertions", "PHPUnit docs: Risky Tests"),
   "(method_declaration name: (name) @n body: (compound_statement) @b (#match? @n \"^test\")) @match",
   "<?php\nclass PriceTest extends TestCase\n{\n    public function testTotal(): void\n    {\n        total();\n    }\n}\n",
   "<?php\nclass PriceTest extends TestCase\n{\n    public function testTotal(): void\n    {\n        $this->assertSame(42, total());\n    }\n}\n",
   "Without an assertion or expectation the test passes whatever the code does.", "S2699", cat="testing", mode="ai-confirm", sev="minor",
   # assertion helpers ($this->checkSolverResult), mock expectations (shouldBeCalled) and #[DoesNotPerformAssertions] count
   filters=[r"cap.lacks_re:b:(?i)(assert|expect|verify|markTestSkipped|markTestIncomplete|fail\(|should(Be|Have|Receive)|->(check|ensure)\w*\()",
            r"node.lacks_re:DoesNotPerformAssertions|@doesNotPerformAssertions"])
Ph("TEST-CLASS-NAME", "PHPUnit test class not named *Test", (PHPUNIT + "writing-tests-for-phpunit.html", "go into a class", "PHPUnit docs: Writing Tests"),
   "(class_declaration name: (name) @n (base_clause [(name) @b (qualified_name (name) @b)]) (#eq? @b \"TestCase\")) @match",
   "<?php\nclass PriceChecks extends TestCase\n{\n}\n", "<?php\nclass PriceTest extends TestCase\n{\n}\n",
   "PHPUnit's default discovery only picks up files/classes ending in Test, so these tests may never run.", "S3360", cat="testing", kind="best-practice", sev="minor",
   filters=[r"cap.lacks_re:n:(Test|TestCase)$", r"node.lacks_re:^\s*abstract\b"])

# ---- Java batch 2: language/API contracts, JUnit 5, Spring, Jakarta ---------------------------
JAPISQL = "https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/"
JUNIT_GUIDE = "https://docs.junit.org/current/writing-tests/"
JAVA_ARRAY_T = r"(int|long|short|byte|char|boolean|double|float|String|Object|[A-Z]\w*)\s*\[\]"

J("FINALIZE-WRONG-SIGNATURE", "finalize declared with a non-standard signature", (JAPI + "lang/Object.html", "protected void finalize()", "Java SE 21 API: Object.finalize"),
  "(method_declaration name: (identifier) @n parameters: (formal_parameters) @p (#eq? @n \"finalize\")) @match",
  cls("    protected void finalize(int code) {\n        close();\n    }\n"), cls("    public void close() {\n        release();\n    }\n"),
  "This is an overload, not an override, so the JVM never calls it as a finalizer; rename it (and prefer Cleaner/try-with-resources over finalization).", "S1175",
  filters=[r"cap.has_re:p:^\(\s*[^\s)]"], fp=[cls("    @Override\n    protected void finalize() throws Throwable {\n        close();\n        super.finalize();\n    }\n")], eq=["https://openjdk.org/jeps/421"])
J("LABEL-IN-SWITCH", "Statement label inside a switch", (JLS14, "has no goto statement", "JLS 14.7 Labeled Statements"),
  "(switch_block (switch_block_statement_group (labeled_statement) @match))",
  jm(["switch (k) {", "    case 1:", "        go();", "    other:", "        stop();", "        break;", "}"], "void f(int k)"),
  jm(["switch (k) {", "    case 1:", "        go();", "        break;", "    default:", "        stop();", "        break;", "}"], "void f(int k)"),
  "A label here looks like a case but is not one, so this code only runs by fall-through: it is usually a missing 'case' keyword.", "S1219", cat="maintainability")
J("SWITCH-FALLTHROUGH", "switch case falls through to the next case", (JLS14, "Fall through can be the cause of subtle bugs", "JLS 14.11 The switch Statement"),
  "(switch_block (switch_block_statement_group (_) @last .) @c . (switch_block_statement_group) @n) @match",
  jm(["switch (k) {", "    case 1:", "        start();", "    case 2:", "        stop();", "        break;", "}"], "void f(int k)"),
  jm(["switch (k) {", "    case 1:", "        start();", "        break;", "    case 2:", "        stop();", "        break;", "}"], "void f(int k)"),
  "Without break the next case's statements run too; add break/return, or comment an intended fall-through.", "S128", sev="minor",
  filters=[r"cap.has_re:c:^(case\s[^:]*|default)\s*:\s*[^\s/c]", r"cap.lacks_re:c:\b(break|return|throw|continue|yield|System\.exit)\b[^;]*;\s*(//[^\n]*|/\*[\s\S]*?\*/|\s|\})*$", r"cap.lacks_re:c:(?i)fall[s -]?(through|thru)|no break",
           r"cap.lacks_re:last:^(break|return|throw|continue|yield)\b|^System\.exit\b|\b(break|return|throw|continue|yield)\b[^;]*;(\s|\})*$",
           r"cap.lacks_re:n:^((case\s[^:]*|default)\s*:\s*)+$",
           r"cap.lacks_re:last:^(case\s|default\b)"],  # tree-sitter also yields the label as the anchored last child
  fp=[jm(["switch (k) {", "    case 1:", "        throw new IllegalArgumentException(String.format(", "            \"no mode; %s\", k));", "    case 2:", "        return;", "}"], "void f(int k)"),
      jm(["switch (k) {", "    case 1:", "    case 2:", "        reset();", "    default:", "}"], "void f(int k)")])
J("HASNEXT-CALLS-NEXT", "hasNext() calls next()", (JAPI + "util/Iterator.html", "Returns true if the iteration has more elements", "Java SE 21 API: Iterator"),
  "(method_declaration name: (identifier) @n parameters: (formal_parameters) body: (block) @b (#eq? @n \"hasNext\")) @match",
  cls("    public boolean hasNext() {\n        return next() != null;\n    }\n"), cls("    public boolean hasNext() {\n        return pos < items.length;\n    }\n"),
  "hasNext() must not advance the iterator; calling next() here skips elements.", "S1849", filters=[r"cap.has_re:b:(^|[^.\w])next\(\s*\)|this\.next\(\s*\)"])
J("EXTERNALIZABLE-WITHOUT-NOARG-CONSTRUCTOR", "Externalizable class without a public no-arg constructor", (JAPI + "io/Externalizable.html", "public no-arg constructor", "Java SE 21 API: Externalizable"),
  "(class_declaration name: (identifier) @n interfaces: (super_interfaces (type_list (type_identifier) @i)) (#eq? @i \"Externalizable\")) @match",
  "public class Msg implements Externalizable {\n    public Msg(String s) {\n        this.s = s;\n    }\n}\n", "public class Msg implements Externalizable {\n    public Msg() {\n    }\n    public Msg(String s) {\n        this.s = s;\n    }\n}\n",
  "Deserialisation instantiates the class through its public no-arg constructor; without one readExternal never runs and an exception is thrown.", "S2060",
  filters=[r"node.has_re:\b{cap:n}\s*\(\s*[^)\s]", r"node.lacks_re:public\s+{cap:n}\s*\(\s*\)"])
J("SERIALIZATION-METHOD-SIGNATURE", "Custom serialization method not private", (JAPI + "io/Serializable.html", "private void writeObject(java.io.ObjectOutputStream out)", "Java SE 21 API: Serializable"),
  "(method_declaration name: (identifier) @n parameters: (formal_parameters (formal_parameter type: (type_identifier) @t)) (#match? @n \"^(writeObject|readObject)$\") (#match? @t \"^Object(Output|Input)Stream$\")) @match",
  cls("    public void writeObject(ObjectOutputStream out) throws IOException {\n        out.defaultWriteObject();\n    }\n"),
  cls("    private void writeObject(ObjectOutputStream out) throws IOException {\n        out.defaultWriteObject();\n    }\n"),
  "Serialization only calls these hooks when the signature is exact (private, void); this one is silently ignored.", "S2061",
  filters=[r"node.lacks_re:^(@\w+(\([^)]*\))?\s+)*private\s+void\s"])
J("ARRAY-TOSTRING-HASHCODE", "toString/hashCode called on an array", (JAPI + "lang/Object.html", "Integer.toHexString(hashCode())", "Java SE 21 API: Object.toString"),
  "(method_invocation object: (identifier) @r name: (identifier) @m arguments: (argument_list) @a (#match? @m \"^(toString|hashCode)$\")) @match",
  jm(["int[] ids = {1, 2};", "log(ids.toString());"]), jm(["int[] ids = {1, 2};", "log(Arrays.toString(ids));"]),
  "Arrays inherit identity-based toString/hashCode, giving output like [I@1b6d3586: use Arrays.toString/Arrays.hashCode.", "S2116",
  filters=[r"cap.has_re:a:^\(\s*\)$", r"func.has_re:\b" + JAVA_ARRAY_T + r"\s*{cap:r}\b|\b{cap:r}\s*\[\]"])
J("STRING-OP-NO-EFFECT", "String operation whose result is the input", (JAPI + "lang/String.html", "Returns a string that is a substring of this string", "Java SE 21 API: String.substring"),
  "(method_invocation name: (identifier) @m arguments: (argument_list . (decimal_integer_literal) @z .) (#eq? @m \"substring\") (#eq? @z \"0\")) @match",
  jm(["String t = s.substring(0);"], "void f(String s)"), jm(["String t = s.substring(1);"], "void f(String s)"),
  "This call returns the same string it started from; it is dead code or a wrong argument.", "S2121", sev="minor")
J("THREAD-SUBCLASS-WITHOUT-RUN", "Thread subclass without run()", (JAPI + "lang/Thread.html", "Starting a thread schedules it to execute its run method", "Java SE 21 API: Thread"),
  "(class_declaration superclass: (superclass (type_identifier) @s) body: (class_body) @b (#eq? @s \"Thread\")) @match",
  "class Worker extends Thread {\n    void prepare() {\n        ready = true;\n    }\n}\n", "class Worker extends Thread {\n    @Override\n    public void run() {\n        work();\n    }\n}\n",
  "Without run() (or a Runnable passed to super) the started thread does nothing.", "S2134",
  filters=[r"cap.lacks_re:b:\bvoid\s+run\s*\(\s*\)", r"cap.lacks_re:b:\bsuper\s*\("])
J("NON-SHORT-CIRCUIT-CONDITION", "& or | between boolean comparisons", (JLS15, "evaluates its right-hand operand only if the value of its left-hand operand is true", "JLS 15.23 Conditional-And Operator"),
  "(binary_expression left: (binary_expression operator: [\"==\" \"!=\" \"<\" \">\" \"<=\" \">=\"]) operator: [\"&\" \"|\"] right: (binary_expression operator: [\"==\" \"!=\" \"<\" \">\" \"<=\" \">=\"])) @match",
  jm(["if (s != null & s.length() > 0) {", "    use(s);", "}"], "void f(String s)"), jm(["if (s != null && s.length() > 0) {", "    use(s);", "}"], "void f(String s)"),
  "& and | always evaluate both sides, so the guard on the left does not protect the right (here a NullPointerException): use && or ||.", "S2178")
J("SERVLET-MUTABLE-FIELD", "Servlet with a mutable instance field", ("https://jakarta.ee/specifications/servlet/6.1/apidocs/jakarta.servlet/jakarta/servlet/http/HttpServlet.html", "Servlets typically run on multithreaded servers", "Jakarta Servlet 6.1 API: HttpServlet"),
  "(class_declaration superclass: (superclass (type_identifier) @s) body: (class_body (field_declaration) @f) (#match? @s \"^(HttpServlet|GenericServlet)$\")) @match",
  "public class Hello extends HttpServlet {\n    private String lastUser;\n}\n", "public class Hello extends HttpServlet {\n    private static final String GREETING = \"hi\";\n}\n",
  "One servlet instance serves all requests concurrently, so this field is shared and racy: keep request state in locals.", "S2226",
  filters=[r"cap.lacks_re:f:\b(static|final)\b|@"])
J("LOOP-NEVER-RUNS", "for loop whose condition is false from the start", (JLS14, "has no goto statement", "JLS 14.14 The for Statement"),
  "(for_statement init: (local_variable_declaration declarator: (variable_declarator name: (identifier) @v value: (decimal_integer_literal) @a)) condition: (binary_expression left: (identifier) @w right: (decimal_integer_literal) @b) (#eq? @v @w) (#eq? @a @b)) @match",
  jm(["for (int i = 10; i < 10; i++) {", "    use(i);", "}"]), jm(["for (int i = 0; i < 10; i++) {", "    use(i);", "}"]),
  "The counter starts at the bound, so the body never runs.", "S2252", filters=[r"node.has_re:^for\s*\([^;]*;\s*\w+\s*(<|>)\s*\d"])
J("USELESS-BIT-OPERATION", "Bit operation with an identity operand", (JLS15, "Integer Bitwise Operators", "JLS 15.22.1 Integer Bitwise Operators"),
  "(binary_expression) @match",
  jm(["int y = x | 0;"], "void f(int x)"), jm(["int y = x | 1;"], "void f(int x)"),
  "OR/XOR with 0 or AND with -1 leaves the value unchanged; the operation is dead code or the wrong constant.", "S2437", sev="minor",
  filters=[r"node.has_re:^[^|&^]+(\|\s*0|\^\s*0|&\s*-1)$"])
J("APPEND-OBJECTOUTPUTSTREAM", "ObjectOutputStream over a file opened for append", (JAPI + "io/ObjectOutputStream.html", "writes the serialization stream header", "Java SE 21 API: ObjectOutputStream"),
  "(object_creation_expression type: (type_identifier) @o arguments: (argument_list (object_creation_expression type: (type_identifier) @f arguments: (argument_list . (_) . (true)))) (#eq? @o \"ObjectOutputStream\") (#eq? @f \"FileOutputStream\")) @match",
  jm(["ObjectOutputStream out = new ObjectOutputStream(new FileOutputStream(f, true));"], "void f(File f) throws IOException"),
  jm(["ObjectOutputStream out = new ObjectOutputStream(new FileOutputStream(f));"], "void f(File f) throws IOException"),
  "Each new stream writes a fresh header into the middle of the file, so reading past the first batch fails with StreamCorruptedException.", "S2689")
J("JDBC-ZERO-INDEX", "JDBC parameter or column index 0", (JAPISQL + "PreparedStatement.html", "the first parameter is 1", "Java SE 21 API: PreparedStatement"),
  "(method_invocation object: (identifier) @r name: (identifier) @m arguments: (argument_list . (decimal_integer_literal) @n) (#match? @m \"^(set|get)(String|Int|Long|Short|Byte|Boolean|Double|Float|BigDecimal|Object|Date|Time|Timestamp|Bytes|Null)$\") (#eq? @n \"0\")) @match",
  jm(["ps.setString(0, name);"], "void f(PreparedStatement ps, String name) throws SQLException"), jm(["ps.setString(1, name);"], "void f(PreparedStatement ps, String name) throws SQLException"),
  "JDBC indices start at 1, so index 0 throws SQLException.", "S2695", filters=[r"cap.has_re:r:(?i)^(stmt|statement|ps|pst|pstmt|prepared\w*|rs|resultSet|result|cs|call\w*)$"])
J("INPUTSTREAM-READ-SIGNED-BYTE", "InputStream.read() returns a signed byte", (JAPI + "io/InputStream.html", "in the range 0 to 255", "Java SE 21 API: InputStream.read"),
  "(class_declaration superclass: (superclass (type_identifier) @s) body: (class_body (method_declaration name: (identifier) @n parameters: (formal_parameters) body: (block (return_statement (array_access)) @match))) (#eq? @s \"InputStream\") (#eq? @n \"read\"))",
  "class Bytes extends InputStream {\n    public int read() {\n        return buf[pos++];\n    }\n}\n", "class Bytes extends InputStream {\n    public int read() {\n        return buf[pos++] & 0xFF;\n    }\n}\n",
  "Bytes above 127 come back negative, and 0xFF is read as -1 (end of stream): mask with & 0xFF.", "S4517")
J("JUNIT5-INNER-CLASS-WITHOUT-NESTED", "Inner test class not annotated @Nested", (JUNIT_GUIDE + "nested-tests.html", "Only non-static nested classes", "JUnit User Guide: Nested Tests"),
  "(class_body (class_declaration body: (class_body) @b) @match)",
  "class OuterTest {\n    class WhenEmpty {\n        @Test\n        void isEmpty() {\n            assertTrue(stack.isEmpty());\n        }\n    }\n}\n",
  "class OuterTest {\n    @Nested\n    class WhenEmpty {\n        @Test\n        void isEmpty() {\n            assertTrue(stack.isEmpty());\n        }\n    }\n}\n",
  "JUnit 5 only runs tests in inner classes marked @Nested, so these tests are silently skipped.", "S5790", cat="testing",
  filters=[r"cap.has_re:b:@(Test|ParameterizedTest|RepeatedTest)\b", r"node.lacks_re:^[^{]*(@Nested|\bstatic\b|\babstract\b)"])
J("JUNIT5-IGNORED-TEST-METHOD", "JUnit 5 test method that is never run", (JUNIT_GUIDE + "test-classes-and-methods.html", "must not return a value", "JUnit User Guide: Test Classes and Methods"),
  "(method_declaration (modifiers (marker_annotation name: (identifier) @a)) @mods type: (_) @t (#match? @a \"^(Test|RepeatedTest|ParameterizedTest)$\")) @match",
  "import org.junit.jupiter.api.Test;\nclass CalcTest {\n    @Test\n    private void adds() {\n        assertEquals(2, add(1, 1));\n    }\n}\n",
  "import org.junit.jupiter.api.Test;\nclass CalcTest {\n    @Test\n    void adds() {\n        assertEquals(2, add(1, 1));\n    }\n}\n",
  "JUnit 5 silently skips test methods that are private, static or return a value.", "S5810", cat="testing",
  filters=[r"file.has_re:org\.junit\.jupiter", r"node.has_re:^[^{]*?(\bprivate\s|\bstatic\s|[^@\w.](int|long|boolean|double|float|[A-Z]\w*(<[^>]*>)?)\s+\w+\s*\()"])
J("ASSERTJ-DESCRIPTION-AFTER-ASSERTION", "AssertJ description set after the assertion", ("https://assertj.github.io/doc/", "as() is used to describe the test and will be shown before the error message", "AssertJ docs"),
  "(expression_statement (method_invocation name: (identifier) @m) @match (#match? @m \"^(as|describedAs|withFailMessage|overridingErrorMessage)$\"))",
  jm(["assertThat(age).isEqualTo(33).as(\"age\");"]), jm(["assertThat(age).as(\"age\").isEqualTo(33);"]),
  "Descriptions only apply to assertions that come after them; at the end of the chain this one is never shown.", "S5833", cat="testing",
  filters=[r"node.has_re:^assertThat\("])
J("WEEK-OF-YEAR-WITH-CALENDAR-YEAR", "Week-of-year pattern combined with calendar year", (JAPI + "time/format/DateTimeFormatter.html", "week-based-year", "Java SE 21 API: DateTimeFormatter"),
  "(method_invocation object: (identifier) @o name: (identifier) @m arguments: (argument_list . (string_literal) @s) (#eq? @o \"DateTimeFormatter\") (#eq? @m \"ofPattern\")) @match",
  jm(["DateTimeFormatter f = DateTimeFormatter.ofPattern(\"yyyy-'W'ww\");"]), jm(["DateTimeFormatter f = DateTimeFormatter.ofPattern(\"YYYY-'W'ww\");"]),
  "Week numbers belong to the week-based year (Y); with y/u the last days of December print week 1 of the wrong year.", "S5917",
  filters=[r"cap.has_re:s:^\x22([^']|'[^']*')*w", r"cap.has_re:s:^\x22([^']|'[^']*')*[yu]", r"cap.lacks_re:s:Y"])
J("COMPUTEIFABSENT-NULL", "computeIfAbsent/computeIfPresent mapping returns null", (JAPI + "util/Map.html", "no mapping is recorded", "Java SE 21 API: Map.computeIfAbsent"),
  "(method_invocation name: (identifier) @m arguments: (argument_list . (_) . (lambda_expression body: (null_literal))) (#match? @m \"^compute(IfAbsent|IfPresent)$\")) @match",
  jm(["cache.computeIfAbsent(k, x -> null);"], "void f(Map<String, String> cache, String k)"), jm(["cache.computeIfAbsent(k, x -> load(x));"], "void f(Map<String, String> cache, String k)"),
  "A null result is never stored (and removes an existing entry for computeIfPresent): this call cannot add the value it seems to.", "S6104")
J("SPRING-OPTIONAL-PRIMITIVE-PARAM", "Optional request parameter with a primitive type", ("https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-methods/requestparam.html", "method parameters that use this annotation are required", "Spring Framework docs: @RequestParam"),
  "(formal_parameter (modifiers (annotation name: (identifier) @a arguments: (annotation_argument_list (element_value_pair key: (identifier) @k value: (false))))) type: [(integral_type) (floating_point_type) (boolean_type)] (#match? @a \"^(RequestParam|PathVariable|RequestHeader)$\") (#eq? @k \"required\")) @match",
  cls("    @GetMapping(\"/items\")\n    List<Item> list(@RequestParam(required = false) int page) {\n        return repo.page(page);\n    }\n"),
  cls("    @GetMapping(\"/items\")\n    List<Item> list(@RequestParam(required = false) Integer page) {\n        return repo.page(page == null ? 0 : page);\n    }\n"),
  "When the parameter is absent Spring has to bind null to a primitive and fails the request: use the wrapper type, Optional, or a defaultValue.", "S6814",
  filters=[r"node.lacks_re:defaultValue"])
J("SPRING-CACHE-ON-INTERFACE", "@Cache* annotation on an interface", ("https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html", "only annotate concrete classes", "Spring Framework docs: Cache annotations"),
  "(interface_declaration body: (interface_body) @b) @match",
  "public interface BookRepo {\n    @Cacheable(\"books\")\n    Book find(String isbn);\n}\n", "public class BookService {\n    @Cacheable(\"books\")\n    public Book find(String isbn) {\n        return repo.load(isbn);\n    }\n}\n",
  "With class-based (and AspectJ) proxies, annotations on interfaces are not seen, so caching silently stops: annotate the implementation.", "S7180",
  cat="maintainability", kind="best-practice", sev="minor", filters=[r"node.lacks_re:\bextends\b[^{]*Repository\b", r"node.has_re:@Cach(eable|ePut|eEvict|ing|eConfig)\b"])
J("SPRING-DATA-PAGE-WITHOUT-PAGEABLE", "Repository method returns Page/Slice without a Pageable", ("https://docs.spring.io/spring-data/commons/reference/repositories/query-methods-details.html", "Pageable", "Spring Data docs: Query methods"),
  "(interface_declaration body: (interface_body (method_declaration type: (generic_type (type_identifier) @t) parameters: (formal_parameters) @p) @match) (#match? @t \"^(Page|Slice)$\"))",
  "interface UserRepo extends Repository<User, Long> {\n    Page<User> findByActive(boolean active);\n}\n", "interface UserRepo extends Repository<User, Long> {\n    Page<User> findByActive(boolean active, Pageable pageable);\n}\n",
  "Spring Data needs a Pageable argument to build a Page or Slice; without it the repository fails at startup or ignores paging.", "S7186",
  filters=[r"cap.lacks_re:p:\bPageable\b"])
J("CONSTRAINT-ON-STATIC-FIELD", "Bean Validation constraint on a static field", ("https://jakarta.ee/specifications/bean-validation/3.0/jakarta-bean-validation-spec-3.0.html", "Static fields and static methods are excluded from validation", "Jakarta Bean Validation 3.0 spec"),
  "(field_declaration (modifiers) @m) @match",
  "class Signup {\n    @NotBlank\n    static String defaultName;\n}\n", "class Signup {\n    @NotBlank\n    String name;\n}\n",
  "Validators skip static fields, so this constraint is never checked.", "S8954",
  filters=[r"cap.has_re:m:\bstatic\b", r"cap.has_re:m:@(NotNull|NotBlank|NotEmpty|Size|Min|Max|Pattern|Email|Positive|PositiveOrZero|Negative|NegativeOrZero|Past|Future|PastOrPresent|FutureOrPresent|Digits|DecimalMin|DecimalMax|Valid|AssertTrue|AssertFalse|Null)\b"])
J("MERGE-RESULT-IGNORED", "EntityManager.merge() result ignored", ("https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2.html", "the managed instance that the state was merged to", "Jakarta Persistence 3.2 spec"),
  "(expression_statement (method_invocation object: (identifier) @r name: (identifier) @m (#eq? @m \"merge\") (#match? @r \"(?i)^(em|entityManager|manager|session)$\")) @match)",
  jm(["em.merge(order);", "order.setStatus(DONE);"], "void f(EntityManager em, Order order)"), jm(["Order managed = em.merge(order);", "managed.setStatus(DONE);"], "void f(EntityManager em, Order order)"),
  "merge() returns a new managed copy; changes made afterwards to the original object are not persisted.", "S8975", mode="ai-confirm", sev="minor")
J("READ-CAST-BEFORE-EOF-CHECK", "read() result cast before checking for -1", (JAPI + "io/InputStream.html", "in the range 0 to 255", "Java SE 21 API: InputStream.read"),
  "(cast_expression type: [(integral_type) (type_identifier)] value: (method_invocation name: (identifier) @m arguments: (argument_list) @args) (#eq? @m \"read\")) @match",
  jm(["char c = (char) in.read();"], "void f(Reader in) throws IOException"), jm(["int r = in.read();", "if (r == -1) return;", "char c = (char) r;"], "void f(Reader in) throws IOException"),
  "Casting first turns the -1 end-of-stream marker into a valid char/byte, so the end is never detected.", "S9130",
  filters=[r"node.has_re:^\(\s*(char|byte|short)\s*\)", r"cap.has_re:args:^\(\s*\)$"])
J("SET-OF-DUPLICATES", "Set.of called with duplicate elements", (JAPI + "util/Set.html", "if there are any duplicate elements", "Java SE 21 API: Set.of"),
  "(method_invocation object: (identifier) @o name: (identifier) @m arguments: (argument_list (_) @a (_) @b) (#eq? @o \"Set\") (#eq? @m \"of\") (#eq? @a @b)) @match",
  jm(["Set<String> s = Set.of(\"a\", \"b\", \"a\");"]), jm(["Set<String> s = Set.of(\"a\", \"b\");"]),
  "Set.of throws IllegalArgumentException when an element repeats.", "S9361")
J("DURATION-GET-UNSUPPORTED-UNIT", "Duration/Instant used with an unsupported unit", (JAPI + "time/Duration.html", "SECONDS and NANOS", "Java SE 21 API: Duration"),
  "(method_invocation object: (_) @o name: (identifier) @m arguments: (argument_list (field_access object: (identifier) @c field: (identifier) @u)) (#eq? @c \"ChronoUnit\")) @match",
  jm(["long mins = Duration.ofHours(2).get(ChronoUnit.MINUTES);"]), jm(["long mins = Duration.ofHours(2).toMinutes();"]),
  "Duration.get only accepts SECONDS and NANOS, and Instant arithmetic stops at DAYS; other units throw UnsupportedTemporalTypeException.", ["S9393", "S8218"],
  filters=[r"node.has_re:^(Duration\.\w+\([^)]*\)\.get\(|Instant\.\w+\([^)]*\)\.(plus|minus)\()", r"node.has_re:Duration[\s\S]*\.get\([\s\S]*ChronoUnit\.(?:MINUTES|HOURS|DAYS|MILLIS|MICROS|HALF_DAYS)|Instant[\s\S]*ChronoUnit\.(?:WEEKS|MONTHS|YEARS|DECADES|CENTURIES|MILLENNIA|ERAS|FOREVER)"])
J("IDENTITYHASHMAP-BOXED-KEY", "IdentityHashMap keyed by boxed values or strings", (JAPI + "util/IdentityHashMap.html", "reference-equality in place of object-equality", "Java SE 21 API: IdentityHashMap"),
  "(generic_type (type_identifier) @t (type_arguments . (type_identifier) @k) (#eq? @t \"IdentityHashMap\") (#match? @k \"^(Integer|Long|Short|Byte|Character|Boolean|Double|Float|String)$\")) @match",
  jm(["Map<Integer, String> m = new IdentityHashMap<Integer, String>();"]), jm(["Map<Integer, String> m = new HashMap<Integer, String>();"]),
  "Keys are compared by reference, and equal boxed numbers or strings are often distinct objects, so lookups miss.", "S9401")
J("COMPETING-TEST-ANNOTATIONS", "Test method with competing JUnit annotations", (JUNIT_GUIDE + "test-classes-and-methods.html", "must not return a value", "JUnit User Guide: Test Classes and Methods"),
  "(method_declaration (modifiers) @m) @match",
  "class CalcTest {\n    @Test\n    @ParameterizedTest\n    @ValueSource(ints = {1, 2})\n    void adds(int x) {\n        assertTrue(x > 0);\n    }\n}\n",
  "class CalcTest {\n    @ParameterizedTest\n    @ValueSource(ints = {1, 2})\n    void adds(int x) {\n        assertTrue(x > 0);\n    }\n}\n",
  "Each of these annotations registers the method as a separate kind of test; combined, it runs twice or fails to resolve parameters.", "S5967", cat="testing",
  filters=[r"cap.has_re:m:@(Test|ParameterizedTest|RepeatedTest|TestFactory|TestTemplate)\b[\s\S]*@(Test|ParameterizedTest|RepeatedTest|TestFactory|TestTemplate)\b"])

# ---- HTML documents (Sonar "Web" repository) ---------------------------------------------------
P["html"] = Pack("HTML-MAINT", "html", "HTML Living Standard", {"any": "*"})
SONAR_REPO["html"] = ["Web"]
ELREF = HTMLREF + "Elements/"

def Hm(id, title, doc, query, bad, good, msg, key, **kw):
    kw.setdefault("cat", "accessibility")
    kw.setdefault("kind", "best-practice")
    kw.setdefault("sev", "minor")
    add("html", id, title, doc, query, bad, good, msg, keys=[key], **kw)

def page(body, html_attrs=' lang="en"', head="<title>Orders</title>"):
    return "<!DOCTYPE html>\n<html%s>\n<head>%s</head>\n<body>\n%s\n</body>\n</html>\n" % (html_attrs, head, body)

def hattr(id, title, doc, attr_re, bad, good, msg, key, filters=None):
    Hm(id, title, doc, "((attribute (attribute_name) @a) @match (#match? @a \"%s\"))" % attr_re, page(bad), page(good), msg, key, filters=filters)

Hm("HTML-WITHOUT-LANG", "<html> element without a lang attribute", (ELREF + "html", "Providing a lang attribute", "MDN: <html>"),
   "(element (start_tag (tag_name) @t) @s (#match? @t \"^(?i)html$\")) @match",
   page("<p>Hi</p>", html_attrs=""), page("<p>Hi</p>"),
   "Without lang, screen readers guess the pronunciation language and translation tools mis-detect it.", "S5254", filters=[r"cap.lacks_re:s:(?i)\blang\s*="])
Hm("PAGE-WITHOUT-TITLE", "HTML page without a <title>", (ELREF + "title", "the primary purpose of the page is announced by a screen reader first", "MDN: <title>"),
   "(element (start_tag (tag_name) @t) (#match? @t \"^(?i)head$\")) @match",
   page("<p>Hi</p>", head="<meta charset=\"utf-8\">"), page("<p>Hi</p>"),
   "A page without a title is announced and bookmarked as its URL: add a descriptive <title>.", "PageWithoutTitleCheck",
   filters=[r"node.lacks_re:(?i)<title[\s>]"])
Hm("MISSING-DOCTYPE", "HTML document without a doctype", ("https://developer.mozilla.org/en-US/docs/Glossary/Doctype", "quirks mode", "MDN glossary: Doctype"),
   "(document . (element (start_tag (tag_name) @t) (#match? @t \"^(?i)html$\")) @match)",
   "<html lang=\"en\">\n<head><title>x</title></head>\n<body><p>Hi</p></body>\n</html>\n", page("<p>Hi</p>"),
   "Without <!DOCTYPE html> browsers render in quirks mode, with legacy layout behaviour.", "DoctypePresenceCheck", cat="correctness")
Hm("OBSOLETE-ELEMENT", "Obsolete HTML element used", (ELREF[:-1], "Obsolete and deprecated elements", "MDN: HTML elements reference"),
   "(start_tag (tag_name) @t (#match? @t \"^(?i)(acronym|applet|basefont|bgsound|big|blink|center|dir|font|frame|frameset|isindex|keygen|marquee|menuitem|nobr|noembed|noframes|plaintext|rb|rtc|spacer|strike|tt|xmp)$\")) @match",
   page("<center>Welcome</center>"), page("<p class=\"centered\">Welcome</p>"),
   "This element is obsolete; browsers may drop or change its behaviour. Use semantic markup and CSS.", "UnsupportedTagsInHtml5Check", cat="maintainability", kind="deprecation")
hattr("ACCESSKEY-ATTRIBUTE", "accesskey attribute used", (HTMLREF + "Global_attributes/accesskey", "Accessibility concerns", "MDN: accesskey"),
      "^(?i)accesskey$", "<button accesskey=\"s\">Save</button>", "<button>Save</button>",
      "Access keys clash with browser and assistive-technology shortcuts: rely on normal focus order instead.", "S6846")
hattr("AUTOFOCUS-ATTRIBUTE", "autofocus attribute used", (HTMLREF + "Global_attributes/autofocus", "Accessibility concerns", "MDN: autofocus"),
      "^(?i)autofocus$", "<input name=\"q\" autofocus>", "<input name=\"q\">",
      "Moving focus on load can disorient screen-reader and keyboard users.", "S9379")
hattr("POSITIVE-TABINDEX", "tabindex greater than zero", (HTMLREF + "Global_attributes/tabindex", "greater than 0", "MDN: tabindex"),
      "^(?i)tabindex$", "<div tabindex=\"3\">x</div>", "<div tabindex=\"0\">x</div>",
      "Positive tabindex values override the natural focus order and confuse keyboard users: use 0 or -1.", "S6841",
      filters=[r"node.has_re:=\s*[\x22']?\s*\+?[1-9]"])
hattr("ARIA-ROLE-ATTRIBUTE", "aria-role used instead of role", ("https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles", "role attribute", "MDN: WAI-ARIA roles"),
      "^(?i)aria-role$", "<div aria-role=\"button\">Go</div>", "<div role=\"button\">Go</div>",
      "There is no aria-role attribute, so assistive technology ignores it: use role.", "S8720")
Hm("SCOPE-ON-NON-TH", "scope attribute on an element other than th", (ELREF + "th", "scope", "MDN: <th>"),
   "(start_tag (tag_name) @t (attribute (attribute_name) @a) (#match? @a \"^(?i)scope$\")) @match",
   page("<table><tr><td scope=\"col\">Name</td></tr></table>"), page("<table><tr><th scope=\"col\">Name</th></tr></table>"),
   "scope only has meaning on th header cells; elsewhere assistive technology ignores it.", "S9380", filters=[r"cap.lacks_re:t:(?i)^th$"])
Hm("TH-WITHOUT-SCOPE-OR-ID", "Header cell without scope or id", (ELREF + "th", "scope", "MDN: <th>"),
   "(start_tag (tag_name) @t (#match? @t \"^(?i)th$\")) @match",
   page("<table><tr><th>Name</th></tr></table>"), page("<table><tr><th scope=\"col\">Name</th></tr></table>"),
   "Without scope (or id referenced by headers) screen readers cannot always tell which cells a header labels.", "TableHeaderHasIdOrScopeCheck",
   filters=[r"node.lacks_re:(?i)\b(scope|id)\s*="])
Hm("ARIA-HIDDEN-FOCUSABLE", "aria-hidden on a focusable element", ("https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-hidden", "should not be used on", "MDN: aria-hidden"),
   "(start_tag (tag_name) @t (attribute (attribute_name) @a) (#match? @a \"^(?i)aria-hidden$\")) @match",
   page("<button aria-hidden=\"true\">Close</button>"), page("<span aria-hidden=\"true\">x</span>"),
   "The element can still receive keyboard focus but is hidden from screen readers, so users land on something that is announced as nothing.", "S6825",
   filters=[r"node.has_re:(?i)aria-hidden\s*=\s*[\x22']?true", r"cap.has_re:t:(?i)^(button|input|select|textarea|summary|iframe|a)$", r"node.has_re:(?i)^<(button|input|select|textarea|summary|iframe)\b|\bhref\s*=", r"node.lacks_re:(?i)\b(disabled|tabindex\s*=\s*[\x22']?-1|type\s*=\s*[\x22']?hidden)\b"])
Hm("LEGEND-OUTSIDE-FIELDSET", "<legend> outside a fieldset", (ELREF + "legend", "first child", "MDN: <legend>"),
   "(element (start_tag (tag_name) @p) (element (start_tag (tag_name) @t)) @match (#match? @t \"^(?i)legend$\"))",
   page("<div><legend>Shipping</legend><input name=\"a\"></div>"), page("<fieldset><legend>Shipping</legend><input name=\"a\"></fieldset>"),
   "A legend only captions a fieldset (or optgroup); elsewhere it is not associated with any controls.", "S8732",
   filters=[r"cap.lacks_re:p:(?i)^(fieldset|optgroup)$"])
Hm("REMOTE-SCRIPT-WITHOUT-INTEGRITY", "Remote script or stylesheet without integrity", ("https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Subresource_Integrity", "fetched resource", "MDN: Subresource Integrity"),
   "(start_tag (tag_name) @t (#match? @t \"^(?i)(script|link)$\")) @match",
   page("<script src=\"https://cdn.example.com/lib.js\"></script>"), page("<script src=\"https://cdn.example.com/lib.js\" integrity=\"sha384-abc\" crossorigin=\"anonymous\"></script>"),
   "A compromised CDN can serve altered code that runs with your page's privileges: pin it with an integrity hash.", "S5725",
   cat="security", kind="security", sev="major", cwe=["CWE-353"], owasp=["A08:2021"],
   filters=[r"node.has_re:(?i)\b(src|href)\s*=\s*[\x22']?(https?:)?//", r"node.lacks_re:(?i)\bintegrity\s*=", r"node.has_re:(?i)^<script|\brel\s*=\s*[\x22']?stylesheet"])

# ---- Python batch 2: control flow, special methods, exceptions ---------------------------------
UNARY_DUNDER = "len|bool|hash|str|repr|iter|next|enter|neg|pos|abs|invert|index|int|float|complex|bytes|aiter|anext|aenter|length_hint|reversed"
BINARY_DUNDER = ("eq|ne|lt|le|gt|ge|add|sub|mul|matmul|truediv|floordiv|mod|divmod|lshift|rshift|and|xor|or|radd|rsub|rmul|rmatmul|rtruediv|"
                 "rfloordiv|rmod|rdivmod|rlshift|rrshift|rand|rxor|ror|iadd|isub|imul|imatmul|itruediv|ifloordiv|imod|ilshift|irshift|iand|ixor|ior|"
                 "contains|getitem|delitem|missing|getattr|getattribute|delattr|format|instancecheck|subclasscheck")

Py("DOUBLE-NOT", "Prefix operator applied twice", (PYD + "reference/expressions.html", "The unary - (minus) operator yields the negation", "Python reference: Unary arithmetic operations"),
   "[(not_operator argument: (not_operator)) (unary_operator argument: (unary_operator))] @match",
   "def ok(x):\n    return not not x\n", "def ok(x):\n    return bool(x)\n",
   "Two negations cancel out; write bool(x) (or drop both) so the intent is visible.", "S2761", cat="maintainability", kind="best-practice", sev="minor",
   filters=[r"node.has_re:^(not\s+not\b|~\s*~)"])
Py("NEEDLESS-PASS", "pass in a block that has other statements", (PYD + "reference/simple_stmts.html", "pass is a null operation", "Python reference: The pass statement"),
   "(block (pass_statement) @match)",
   "def f(x):\n    log(x)\n    pass\n", "def f(x):\n    log(x)\n",
   "pass does nothing here because the block already has statements: remove it.", "S2772", cat="maintainability", kind="best-practice", sev="minor",
   filters=[r"ancestor.has_re:block:\S[^\n]*\n\s*\S"])
Py("LOOP-ELSE-WITHOUT-BREAK", "Loop else clause without any break", (PYD + "reference/compound_stmts.html", "terminates the loop without executing the else clause", "Python reference: The for statement"),
   "[(for_statement body: (block) @b alternative: (else_clause)) (while_statement body: (block) @b alternative: (else_clause))] @match",
   "def find(xs, t):\n    for x in xs:\n        if x == t:\n            return x\n    else:\n        return None\n",
   "def find(xs, t):\n    for x in xs:\n        if x == t:\n            return x\n    return None\n",
   "Without a break the else block always runs after the loop, so it is just confusingly indented code.", "S2836", cat="maintainability", kind="best-practice", sev="minor",
   filters=[r"cap.lacks_re:b:\bbreak\b"])
Py("BARE-RAISE-IN-FINALLY", "Bare raise inside finally", (PYD + "reference/simple_stmts.html", "re-raises the exception that is currently being handled", "Python reference: The raise statement"),
   "(finally_clause (block (raise_statement) @match))",
   "def run():\n    try:\n        work()\n    finally:\n        cleanup()\n        raise\n", "def run():\n    try:\n        work()\n    finally:\n        cleanup()\n",
   "When the try block succeeded there is no active exception, so this raise fails with RuntimeError.", "S5704",
   filters=[r"node.has_re:^raise\s*$"])
Py("BARE-RAISE-OUTSIDE-EXCEPT", "Bare raise outside an except block", (PYD + "reference/simple_stmts.html", "re-raises the exception that is currently being handled", "Python reference: The raise statement"),
   "(raise_statement) @match",
   "def check(x):\n    if x < 0:\n        raise\n", "def check(x):\n    if x < 0:\n        raise ValueError(x)\n",
   "With no exception being handled, a bare raise fails with RuntimeError: raise a specific exception.", "S5747",
   filters=[r"node.has_re:^raise\s*$", "node.lacks_ancestor:except_clause|finally_clause|except_group_clause", r"ancestor.lacks_re:function_definition:^def\s+(__exit__|_?re_?raise\w*)\b"])
Py("MUTATED-DEFAULT-ARGUMENT", "Mutable default argument mutated in the body", (PYD + "reference/compound_stmts.html", "Default parameter values are evaluated from left to right", "Python reference: Function definitions"),
   "(function_definition parameters: (parameters (default_parameter name: (identifier) @n value: [(list) (dictionary) (set) (call function: (identifier) @c)]))) @match",
   "def collect(x, acc=[]):\n    acc.append(x)\n    return acc\n", "def collect(x, acc=None):\n    acc = [] if acc is None else acc\n    acc.append(x)\n    return acc\n",
   "The default object is created once and shared by every call, so mutating it leaks state between calls: default to None.", "S5717",
   filters=[r"node.has_re:\b{cap:n}\.(append|extend|insert|add|update|pop|popitem|remove|discard|clear|setdefault|sort|reverse)\(|\b{cap:n}\[[^\]]*\]\s*[-+*/|&]?=", r"node.lacks_re:(?m)^\s+{cap:n}\s*=[^=]"])
Py("METHOD-FIRST-PARAM-NOT-SELF", "Instance method whose first parameter is not self", (PYD + "tutorial/classes.html", "Often, the first argument of a method is called self", "Python tutorial: Random Remarks"),
   "(class_definition body: (block (function_definition name: (identifier) @f parameters: (parameters . (identifier) @p)) @match))",
   "class A:\n    def size(this):\n        return this.n\n", "class A:\n    def size(self):\n        return self.n\n",
   "Readers and tools rely on self naming the instance; a different first name hides that this is an instance method (or a forgotten @staticmethod).", "S5720",
   cat="maintainability", kind="best-practice", sev="minor",
   # zope.interface declarations omit self by convention; graphene resolvers take root (suppressed via N805).
   filters=[r"cap.lacks_re:p:^(self|cls|_\w*|mcs|mcls|metacls|klass|self_\w*)$", r"cap.lacks_re:f:^__(new|init_subclass|class_getitem|prepare)__$", r"ancestor.lacks_re:class_definition:^class\s+\w+\s*\([^)]*\bInterface\b"],
   fp=["from zope.interface import Interface\n\nclass ISpiderLoader(Interface):\n    def load(spider_name):\n        pass\n"], eq=["ruff:N805", "pylint:no-self-argument"])
Py("SPECIAL-METHOD-ARITY", "Special method with the wrong number of parameters", (PYD + "reference/datamodel.html", "the first argument", "Python reference: Data model"),
   "(class_definition body: (block (function_definition) @match))",
   "class V:\n    def __eq__(self):\n        return True\n", "class V:\n    def __eq__(self, other):\n        return self.x == other.x\n",
   "Python calls this method with a fixed number of arguments, so this signature raises TypeError when the operator or builtin is used.", "S5722",
   filters=[r"node.has_re:^(async\s+)?def\s+(__(" + UNARY_DUNDER + r")__\s*\(\s*\w+(\s*:[^,)]*)?\s*,\s*\w|__(" + BINARY_DUNDER + r")__\s*\(\s*\w+(\s*:[^,)]*)?\s*\)|__setitem__\s*\(\s*\w+[^,)]*(,[^,)]*)?\))",
            r"node.lacks_re:^[^\n]*\*"])
Py("PROPERTY-ACCESSOR-ARITY", "Property getter or setter with the wrong parameters", (PYD + "library/functions.html", "Return a property attribute", "Python docs: property"),
   "((decorated_definition (decorator (identifier) @d) definition: (function_definition parameters: (parameters (_) [(identifier) (typed_parameter)]))) @match (#eq? @d \"property\"))\n"
   "((decorated_definition (decorator (attribute attribute: (identifier) @d)) definition: (function_definition parameters: (parameters . (_) .))) @match (#eq? @d \"setter\"))\n"
   "((decorated_definition (decorator (attribute attribute: (identifier) @d)) definition: (function_definition parameters: (parameters (_) (_) [(identifier) (typed_parameter)]))) @match (#eq? @d \"setter\"))",
   "class A:\n    @property\n    def size(self, unit):\n        return self.n\n", "class A:\n    @property\n    def size(self):\n        return self.n\n",
   "Attribute access calls a getter with only self and a setter with exactly one value, so this signature raises TypeError.", "S5724",
   fp=["class A:\n    @property\n    def size(self):\n        return self._size\n\n    @size.setter\n    def size(self, new_size: Tuple[int, int]) -> None:\n        self._size = new_size\n",
       "class A:\n    @property\n    def status(self):\n        return self._s\n\n    @status.setter\n    def status(\n        self,\n        status: \"Union[SpanStatus, str]\",\n    ) -> None:\n        self._s = status\n"])
Py("SYSTEMEXIT-SWALLOWED", "SystemExit or BaseException caught without re-raising", (PYD + "library/exceptions.html", "not accidentally caught by code that catches", "Python docs: SystemExit"),
   "(except_clause value: [(identifier) @e (as_pattern (identifier) @e)]) @match",
   "def main():\n    try:\n        run()\n    except SystemExit:\n        log(\"exit\")\n", "def main():\n    try:\n        run()\n    except SystemExit:\n        log(\"exit\")\n        raise\n",
   "Swallowing SystemExit (or BaseException) stops sys.exit() and Ctrl-C from ending the program: re-raise it.", "S5754",
   filters=[r"cap.has_re:e:^(SystemExit|BaseException)$", r"node.lacks_re:\b(re)?raise\b|sys\.exit|os\._exit|\.code\b|exc_info|ExceptionInfo\("],
   fp=["try:\n    run()\nexcept BaseException:\n    reraise(*capture())\n",
       "try:\n    main()\nexcept SystemExit as e:\n    code = e.code\n"])
Py("IMPLICIT-CONCAT-IN-COLLECTION", "Adjacent string literals inside a collection on one line", (PYD + "reference/lexical_analysis.html", "String literal concatenation", "Python reference: String literal concatenation"),
   "[(list (concatenated_string) @match) (tuple (concatenated_string) @match) (set (concatenated_string) @match) (argument_list (concatenated_string) @match)]",
   "COLORS = [\"red\" \"green\", \"blue\"]\n", "COLORS = [\"red\", \"green\", \"blue\"]\n",
   "Adjacent literals are joined into one string, which in a collection usually means a missing comma.", "S5799",
   filters=[r"node.lacks_re:\n"])
Py("UNHASHABLE-KEY", "Unhashable value used as dict key or set member", ("https://docs.python.org/3/glossary.html", "An object is hashable if", "Python glossary: hashable"),
   "[(dictionary (pair key: [(list) (dictionary) (set) (list_comprehension) (dictionary_comprehension) (set_comprehension)] @k)) (set [(list) (dictionary) (set)] @k)] @match",
   "LOOKUP = {[1, 2]: \"pair\"}\n", "LOOKUP = {(1, 2): \"pair\"}\n",
   "Lists, dicts and sets are unhashable, so building this literal raises TypeError: use a tuple or frozenset.", "S6662")
Py("EXIT-RERAISES-EXCEPTION", "__exit__ re-raises the exception it was given", (PYD + "reference/datamodel.html", "should not reraise the passed-in exception", "Python reference: object.__exit__"),
   "(function_definition name: (identifier) @n parameters: (parameters (_) (_) (identifier) @v (_)) (#eq? @n \"__exit__\")) @match",
   "class Tx:\n    def __exit__(self, kind, exc, tb):\n        self.rollback()\n        raise exc\n", "class Tx:\n    def __exit__(self, kind, exc, tb):\n        self.rollback()\n        return False\n",
   "Returning a false value already propagates the exception; raising it again adds a confusing extra traceback frame.", "S5706", cat="maintainability", sev="minor",
   filters=[r"node.has_re:\braise\s+{cap:v}\s*(\n|$)"])

# ---- Java batch 3: API idioms, loops, logging --------------------------------------------------
JSTR = JAPI + "lang/String.html"

J("SYSTEM-OUT-LOGGING", "System.out/System.err used for output in library code", (JAPI + "lang/System.html", "The \"standard\" output stream", "Java SE 21 API: System.out"),
  "(method_invocation object: (field_access object: (identifier) @s field: (identifier) @f) name: (identifier) @m (#eq? @s \"System\") (#match? @f \"^(out|err)$\") (#match? @m \"^(print|println|printf|format)$\")) @match",
  jm(["System.out.println(\"saved \" + id);"], "void f(long id)"), jm(["log.info(\"saved {}\", id);"], "void f(long id)"),
  "Console output bypasses log levels, routing and formatting: use the project's logger.", "S106", cat="maintainability", kind="best-practice", sev="minor",
  filters=[r"file.lacks_re:\bstatic\s+void\s+main\s*\(", r"file.lacks_re:@(Test|ParameterizedTest)\b"])
J("STRING-VALUEOF-CONCAT", "String.valueOf inside string concatenation", (JSTR, "Returns the string representation of the Object argument", "Java SE 21 API: String.valueOf"),
  "(binary_expression operator: \"+\" [left: (method_invocation object: (identifier) @o name: (identifier) @m) right: (method_invocation object: (identifier) @o name: (identifier) @m)] (#eq? @o \"String\") (#eq? @m \"valueOf\")) @match",
  jm(["String s = \"id=\" + String.valueOf(id);"], "void f(long id)"), jm(["String s = \"id=\" + id;"], "void f(long id)"),
  "Concatenation already converts the value; String.valueOf is noise.", "S1153", cat="maintainability", kind="best-practice", sev="minor",
  filters=[r"node.has_re:\x22"])
J("CASE-CONVERT-TO-COMPARE", "Case conversion just to compare strings", (JSTR, "equalsIgnoreCase", "Java SE 21 API: String.equalsIgnoreCase"),
  "(method_invocation object: (method_invocation name: (identifier) @l) name: (identifier) @m arguments: (argument_list . (method_invocation name: (identifier) @r) .) (#eq? @m \"equals\") (#match? @l \"^to(Lower|Upper)Case$\") (#match? @r \"^to(Lower|Upper)Case$\")) @match",
  jm(["boolean same = a.toLowerCase().equals(b.toLowerCase());"], "void f(String a, String b)"), jm(["boolean same = a.equalsIgnoreCase(b);"], "void f(String a, String b)"),
  "Converting both sides allocates two strings and is locale-sensitive: use equalsIgnoreCase.", "S1157", cat="performance", kind="best-practice", sev="minor")
J("EXPLICIT-GC", "Garbage collection triggered explicitly", (JAPI + "lang/System.html", "Calling the gc method suggests", "Java SE 21 API: System.gc"),
  "[(method_invocation object: (identifier) @o name: (identifier) @m (#eq? @o \"System\") (#eq? @m \"gc\")) (method_invocation object: (method_invocation name: (identifier) @g) name: (identifier) @m2 (#eq? @g \"getRuntime\") (#eq? @m2 \"gc\"))] @match",
  jm(["System.gc();"]), jm(["cache.clear();"]),
  "System.gc() is only a hint that can cause long full-GC pauses (or be ignored): let the JVM decide.", "S1215", cat="performance", kind="anti-pattern", sev="minor")
J("TOSTRING-ON-STRING-LITERAL", "toString() called on a string literal", (JSTR, "This object (which is already a string!) is itself returned", "Java SE 21 API: String.toString"),
  "(method_invocation object: (string_literal) name: (identifier) @m arguments: (argument_list) (#eq? @m \"toString\")) @match",
  jm(["String s = \"ready\".toString();"]), jm(["String s = \"ready\";"]),
  "A String's toString() returns the same object; the call is noise.", "S1858", cat="maintainability", kind="best-practice", sev="minor")
J("NEW-FOR-GETCLASS", "Object created only to call getClass()", (JAPI + "lang/Object.html", "Returns the runtime class of this Object", "Java SE 21 API: Object.getClass"),
  "(method_invocation object: (object_creation_expression) name: (identifier) @m arguments: (argument_list) (#eq? @m \"getClass\")) @match",
  jm(["Class<?> c = new Order().getClass();"]), jm(["Class<?> c = Order.class;"]),
  "Building an instance just to read its class runs a constructor for nothing: use Type.class.", "S2133", cat="performance", kind="best-practice", sev="minor",
  filters=[r"node.lacks_re:\}\s*\.\s*getClass\s*\(\s*\)$"], fp=[jm(["Class<?> anon = new Object() {}.getClass();"])])
J("COMPARETO-MIN-VALUE", "compareTo returns Integer.MIN_VALUE", (JAPI + "lang/Comparable.html", "a negative integer, zero, or a positive integer", "Java SE 21 API: Comparable.compareTo"),
  "(method_declaration name: (identifier) @n body: (block) @b (#match? @n \"^compare(To)?$\")) @match",
  cls("    public int compareTo(A o) {\n        return o == null ? Integer.MIN_VALUE : 1;\n    }\n"), cls("    public int compareTo(A o) {\n        return o == null ? -1 : 1;\n    }\n"),
  "Callers that negate the result (to reverse order) overflow on MIN_VALUE and get MIN_VALUE back: return -1.", "S2167", filters=[r"cap.has_re:b:\bInteger\.MIN_VALUE\b"])
J("SHIFT-OUT-OF-RANGE", "int shifted by 32 or more bits", ("https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html", "only the five lowest-order bits of the right-hand operand are used", "JLS 15.19 Shift Operators"),
  "(binary_expression left: (decimal_integer_literal) @l right: (decimal_integer_literal) @r) @match",
  jm(["long mask = 1 << 40;"]), jm(["long mask = 1L << 40;"]),
  "Only the low five bits of the distance are used for int, so 1 << 40 is 1 << 8: use a long operand (1L).", "S2183",
  filters=[r"node.has_re:^\d+\s*(<<|>>>?)\s*\d+$", r"cap.lacks_re:l:[lL]$", r"cap.has_re:r:^(3[2-9]|[4-9]\d|\d{3,})$"])
J("COMPARETO-SPECIFIC-VALUE", "compareTo result compared with 1 or -1", (JAPI + "lang/Comparable.html", "a negative integer, zero, or a positive integer", "Java SE 21 API: Comparable.compareTo"),
  "(binary_expression left: (method_invocation name: (identifier) @m) right: [(decimal_integer_literal) (unary_expression)] @v (#match? @m \"^compare(To|ToIgnoreCase)?$\")) @match",
  jm(["if (a.compareTo(b) == 1) {", "    swap();", "}"], "void f(String a, String b)"), jm(["if (a.compareTo(b) > 0) {", "    swap();", "}"], "void f(String a, String b)"),
  "compareTo only promises the sign of the result, so == 1 / == -1 misses other positive or negative values.", "S2200",
  filters=[r"node.has_re:(==|!=)\s*-?\s*[1-9]\d*$"])
J("RESULTSET-ISLAST", "ResultSet.isLast() used", ("https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/ResultSet.html", "Calling the method isLast may be expensive", "Java SE 21 API: ResultSet.isLast"),
  "(method_invocation object: (identifier) @r name: (identifier) @m arguments: (argument_list) (#eq? @m \"isLast\") (#match? @r \"(?i)^(rs|resultSet|result|results|cursor)$\")) @match",
  jm(["while (rs.next()) {", "    if (rs.isLast()) {", "        done();", "    }", "}"], "void f(ResultSet rs) throws SQLException"),
  jm(["while (rs.next()) {", "    handle(rs);", "}", "done();"], "void f(ResultSet rs) throws SQLException"),
  "isLast may make the driver fetch ahead and is unsupported for some result-set types: track the end after next() returns false.", "S2232", cat="performance", kind="best-practice", sev="minor")
J("CATCH-ILLEGAL-MONITOR-STATE", "IllegalMonitorStateException caught", (JAPI + "lang/IllegalMonitorStateException.html", "Thrown to indicate that a thread has attempted to wait", "Java SE 21 API: IllegalMonitorStateException"),
  "(catch_clause (catch_formal_parameter (catch_type (type_identifier) @t)) (#eq? @t \"IllegalMonitorStateException\")) @match",
  jm(["try {", "    lock.wait();", "} catch (IllegalMonitorStateException e) {", "    retry();", "}"], "void f() throws InterruptedException"),
  jm(["synchronized (lock) {", "    lock.wait();", "}"], "void f() throws InterruptedException"),
  "This exception signals a missing synchronized block, a programming error: fix the locking instead of catching it.", "S2235")
J("ITERATOR-NEXT-WITHOUT-NOSUCHELEMENT", "Iterator.next() never throws NoSuchElementException", (JAPI + "util/Iterator.html", "if the iteration has no more elements", "Java SE 21 API: Iterator.next"),
  "(class_declaration interfaces: (super_interfaces (type_list (generic_type (type_identifier) @i))) body: (class_body (method_declaration name: (identifier) @n parameters: (formal_parameters) body: (block) @b) @match) (#eq? @i \"Iterator\") (#eq? @n \"next\"))",
  "class Range implements Iterator<Integer> {\n    public Integer next() {\n        return cur++;\n    }\n}\n",
  "class Range implements Iterator<Integer> {\n    public Integer next() {\n        if (!hasNext()) {\n            throw new NoSuchElementException();\n        }\n        return cur++;\n    }\n}\n",
  "Callers rely on NoSuchElementException at the end; without it they get wrong values or a different exception.", "S2272", sev="minor", mode="ai-confirm",
  filters=[r"cap.lacks_re:b:NoSuchElementException|\.next\(\)|hasNext\(\)"])
J("SYNCHRONIZED-READOBJECT", "readObject declared synchronized", (JAPI + "io/Serializable.html", "private void writeObject(java.io.ObjectOutputStream out)", "Java SE 21 API: Serializable"),
  "(method_declaration (modifiers) @mods name: (identifier) @n (#eq? @n \"readObject\")) @match",
  cls("    private synchronized void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {\n        in.defaultReadObject();\n    }\n"),
  cls("    private void readObject(ObjectInputStream in) throws IOException, ClassNotFoundException {\n        in.defaultReadObject();\n    }\n"),
  "The object being deserialised is not visible to other threads yet, so the lock only costs time.", "S2675", cat="performance", kind="best-practice", sev="minor",
  filters=[r"cap.has_re:mods:\bsynchronized\b"])
J("INDEXOF-POSITIVE-CHECK", "indexOf result tested with > 0", (JSTR, "or -1 if there is no such occurrence", "Java SE 21 API: String.indexOf"),
  "(binary_expression left: (method_invocation name: (identifier) @m) right: (decimal_integer_literal) @z (#eq? @m \"indexOf\") (#eq? @z \"0\")) @match",
  jm(["if (s.indexOf(\"a\") > 0) {", "    hit();", "}"], "void f(String s)"), jm(["if (s.indexOf(\"a\") >= 0) {", "    hit();", "}"], "void f(String s)"),
  "Index 0 is a valid match, so > 0 ignores a hit at the start: use >= 0 (or contains).", "S2692", filters=[r"node.has_re:>\s*0$"])
J("LIST-REMOVE-IN-ASCENDING-LOOP", "List.remove(i) inside an ascending index loop", (JAPI + "util/List.html", "Shifts any subsequent elements to the left", "Java SE 21 API: List.remove"),
  "(for_statement init: (local_variable_declaration declarator: (variable_declarator name: (identifier) @i)) update: (update_expression) body: (block) @b) @match",
  jm(["for (int i = 0; i < xs.size(); i++) {", "    if (xs.get(i) < 0) {", "        xs.remove(i);", "    }", "}"], "void f(List<Integer> xs)"),
  jm(["xs.removeIf(x -> x < 0);"], "void f(List<Integer> xs)"),
  "Each removal shifts the next element into the current index, which the loop then skips: iterate backwards or use removeIf.", "S5413",
  filters=[r"cap.has_re:b:\.remove\(\s*{cap:i}\s*\)", r"node.has_re:{cap:i}\s*\+\+|\+\+\s*{cap:i}", r"cap.lacks_re:b:{cap:i}\s*--|--\s*{cap:i}|\bbreak\b|\breturn\b"])
J("FOR-UPDATE-OTHER-VARIABLE", "for loop updates a variable other than the one it tests", (JLS14, "The basic for statement executes some initialization code", "JLS 14.14.1 The basic for Statement"),
  "(for_statement condition: (binary_expression left: (identifier) @c) update: (update_expression (identifier) @u)) @match",
  jm(["for (int i = 0; i < n; j++) {", "    use(i);", "}"], "void f(int n, int j)"), jm(["for (int i = 0; i < n; i++) {", "    use(i);", "}"], "void f(int n, int j)"),
  "The tested counter is never advanced by the update clause, which usually means an infinite loop or a typo.", "S1994",
  filters=[r"cap.lacks_re:u:^{cap:c}$", r"node.lacks_re:^for\s*\([^;]*;[^;]*;[^)]*\b{cap:c}\b"])
J("STRING-CONCAT-IN-LOOP", "String built with += inside a loop", (JAPI + "lang/StringBuilder.html", "append", "Java SE 21 API: StringBuilder"),
  "(assignment_expression left: (identifier) @s operator: \"+=\") @match",
  jm(["String out = \"\";", "for (String p : parts) {", "    out += p;", "}"], "void f(List<String> parts)"),
  jm(["StringBuilder out = new StringBuilder();", "for (String p : parts) {", "    out.append(p);", "}"], "void f(List<String> parts)"),
  "Each += copies the whole string, making the loop quadratic: use a StringBuilder.", "S1643", cat="performance", kind="best-practice", sev="minor",
  filters=["node.has_ancestor:for_statement|enhanced_for_statement|while_statement|do_statement", r"func.has_re:\bString\s+{cap:s}\b"])
J("KEYSET-WITH-GET", "Map iterated by keySet with get() for each key", (JAPI + "util/Map.html", "Returns a Set view of the mappings contained in this map", "Java SE 21 API: Map.entrySet"),
  "(enhanced_for_statement name: (identifier) @k value: (method_invocation object: (identifier) @m name: (identifier) @ks (#eq? @ks \"keySet\")) body: (_) @b) @match",
  jm(["for (String k : prices.keySet()) {", "    total += prices.get(k);", "}"], "void f(Map<String, Integer> prices, int total)"),
  jm(["for (Map.Entry<String, Integer> e : prices.entrySet()) {", "    total += e.getValue();", "}"], "void f(Map<String, Integer> prices, int total)"),
  "Looking each key up again costs a second hash lookup per entry: iterate entrySet().", "S2864", cat="performance", kind="best-practice", sev="minor",
  filters=[r"cap.has_re:b:\b{cap:m}\.get\(\s*{cap:k}\s*\)"])
J("APPEND-WITH-CONCATENATION", "StringBuilder.append given a concatenation", (JAPI + "lang/StringBuilder.html", "append", "Java SE 21 API: StringBuilder"),
  "(method_invocation object: (identifier) @r name: (identifier) @m arguments: (argument_list . (binary_expression operator: \"+\") .) (#eq? @m \"append\")) @match",
  jm(["StringBuilder sb = new StringBuilder();", "sb.append(\"id=\" + id);"], "void f(long id)"), jm(["StringBuilder sb = new StringBuilder();", "sb.append(\"id=\").append(id);"], "void f(long id)"),
  "The concatenation builds a temporary string first: chain append calls instead.", "S3024", cat="performance", kind="best-practice", sev="minor",
  filters=[r"func.has_re:\bString(Builder|Buffer)\s+{cap:r}\b", r"node.has_re:\x22"])
J("MANUAL-ARRAY-COPY", "Array copied element by element in a loop", (JAPI + "lang/System.html", "Copies an array from the specified source array", "Java SE 21 API: System.arraycopy"),
  "(for_statement init: (local_variable_declaration declarator: (variable_declarator name: (identifier) @i)) body: [(expression_statement (assignment_expression left: (array_access index: (identifier) @a) right: (array_access index: (identifier) @b))) (block . (expression_statement (assignment_expression left: (array_access index: (identifier) @a) right: (array_access index: (identifier) @b))) .)] (#eq? @i @a) (#eq? @a @b)) @match",
  jm(["for (int i = 0; i < src.length; i++) {", "    dst[i] = src[i];", "}"], "void f(int[] src, int[] dst)"), jm(["System.arraycopy(src, 0, dst, 0, src.length);"], "void f(int[] src, int[] dst)"),
  "A hand-written copy loop is slower and more error-prone than System.arraycopy / Arrays.copyOf.", "S3012", cat="performance", kind="best-practice", sev="minor")
J("LOG-ARGUMENT-CONCATENATION", "Log message built by concatenation", ("https://www.slf4j.org/faq.html", "Parameterized log messages solve an important problem", "SLF4J FAQ"),
  "(method_invocation object: (identifier) @o name: (identifier) @m arguments: (argument_list . (binary_expression operator: \"+\") @a) (#match? @o \"(?i)^(log|logger|LOG|LOGGER)$\") (#match? @m \"^(trace|debug|info)$\")) @match",
  jm(["log.debug(\"loaded \" + items.size() + \" items\");"], "void f(List<String> items)", "import org.slf4j.Logger;\n"),
  jm(["log.debug(\"loaded {} items\", items.size());"], "void f(List<String> items)", "import org.slf4j.Logger;\n"),
  "The message is concatenated even when the level is disabled: use {} placeholders.", "S2629", cat="performance", kind="best-practice", sev="minor",
  filters=[r"cap.has_re:a:\x22", r"cap.has_re:a:[^\x22\s]\s*\+|\+\s*[^\x22\s]",
           # corpus: only loggers with {} placeholders (SLF4J, Log4j 2, Lombok); commons-logging and MyBatis Log
           # take a single String. A call guarded by isXxxEnabled() does not build the message when disabled.
           r"file.has_re:import\s+(org\.slf4j\.|org\.apache\.logging\.log4j\.|lombok\.extern\.(slf4j|log4j)\.)|@(Slf4j|Log4j2|XSlf4j)\b",
           r"ancestor.lacks_re:if_statement:^if\s*\([^)]*\bis(Trace|Debug|Info)Enabled\(",
           r"ancestor.lacks_re:if_statement:^if\s*\([^)]*\bisLoggable\("],
  fp=[jm(["log.debug(\"If the method is POST \"", "    + \"use @FormParam\");"]),
      "import org.slf4j.Logger;\nclass A {\n  Logger log;\n  void f(int n) {\n    if (log.isDebugEnabled()) {\n      log.debug(\"n=\" + n);\n    }\n  }\n}\n",
      "import org.apache.commons.logging.Log;\nclass A {\n  Log log;\n  void f(int n) {\n    log.info(\"n=\" + n);\n  }\n}\n"])
J("INSTANCE-METHOD-WRITES-STATIC", "Instance method assigns a static field", ("https://docs.oracle.com/javase/specs/jls/se21/html/jls-8.html", "there exists exactly one incarnation of the field", "JLS 8.3.1.1 static Fields"),
  "(assignment_expression left: (identifier) @f) @match",
  "class Counter {\n    private static int total;\n    void add(int n) {\n        total += n;\n    }\n}\n", "class Counter {\n    private int total;\n    void add(int n) {\n        total += n;\n    }\n}\n",
  "Every instance shares the static field, so writes from instance methods race and leak state between objects.", "S2696", sev="minor", mode="ai-confirm",
  filters=["node.has_ancestor:method_declaration", r"ancestor.lacks_re:method_declaration:^[^{(]*\bstatic\b",
           r"file.has_re:\bstatic\s+(volatile\s+)?(int|long|short|byte|char|boolean|double|float|[A-Z]\w*(<[^>]*>)?)\s+{cap:f}\s*[;=]",
           r"func.lacks_re:\b(int|long|short|byte|char|boolean|double|float|var|[A-Z]\w*(<[^>]*>)?)\s+{cap:f}\s*[;=,):]"])

# ---- JavaScript batch 2: array idioms, DOM, JSX accessibility ----------------------------------
ELEMENTS = HTMLREF + "Elements/"

Js("INDEXOF-POSITIVE-CHECK", "indexOf result tested with > 0", (MDN + "Global_Objects/Array/indexOf", "or -1 if it is not present", "MDN: Array.prototype.indexOf"),
   "(binary_expression left: (call_expression function: (member_expression property: (property_identifier) @m)) right: (number) @z (#eq? @m \"indexOf\") (#eq? @z \"0\")) @match",
   "if (tags.indexOf('a') > 0) {\n  hit();\n}\n", "if (tags.includes('a')) {\n  hit();\n}\n",
   "Index 0 is a valid match, so > 0 ignores a hit at the start: use >= 0 or includes().", "S2692", filters=[r"node.has_re:>\s*0$"])
Js("TOP-LEVEL-THIS", "this used at module top level", (MDN + "Operators/this", "globalThis", "MDN: this"),
   "(this) @match",
   "this.config = load();\n", "globalThis.config = load();\n",
   "Outside any function or class, this is undefined in modules and the global object in scripts: name the target explicitly.", "S2990",
   cat="maintainability", kind="best-practice", sev="minor",
   filters=["node.lacks_ancestor:function_declaration|function_expression|function|method_definition|class_body|generator_function_declaration|generator_function|arrow_function|class_declaration|class"])
Js("MUTATING-SORT-ASSIGNED", "Result of in-place sort/reverse assigned to a new name", (MDN + "Global_Objects/Array/sort", "sorts the elements of an array in place", "MDN: Array.prototype.sort"),
   "(variable_declarator name: (identifier) @n value: (call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @m)) (#match? @m \"^(sort|reverse)$\")) @match",
   "const sorted = prices.sort((a, b) => a - b);\n", "const sorted = prices.toSorted((a, b) => a - b);\n",
   "sort()/reverse() mutate the original array and return it, so both names now point at the reordered data: copy first or use toSorted()/toReversed().", "S4043",
   cat="correctness", sev="minor", filters=[r"cap.lacks_re:n:^{cap:o}$"])
Js("MAP-THEN-FLAT", ".map().flat() instead of .flatMap()", (MDN + "Global_Objects/Array/flatMap", "identical to a map() followed by a flat() of depth 1", "MDN: Array.prototype.flatMap"),
   "(call_expression function: (member_expression object: (call_expression function: (member_expression property: (property_identifier) @m)) property: (property_identifier) @f) arguments: (arguments) @a (#eq? @m \"map\") (#eq? @f \"flat\")) @match",
   "const tags = posts.map((p) => p.tags).flat();\n", "const tags = posts.flatMap((p) => p.tags);\n",
   "flatMap does the same in one pass without the intermediate array.", "S7752", cat="maintainability", kind="best-practice", sev="minor",
   filters=[r"cap.has_re:a:^\(\s*(1\s*)?\)$"])
Js("GETATTRIBUTE-DATA", "data-* attribute read via getAttribute", ("https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/dataset", "custom data attributes", "MDN: HTMLElement.dataset"),
   "(call_expression function: (member_expression property: (property_identifier) @m) arguments: (arguments . (string) @s .) (#match? @m \"^(get|set|has|remove)Attribute$\")) @match",
   "const id = el.getAttribute('data-user-id');\n", "const id = el.dataset.userId;\n",
   "dataset gives typed-name access to data-* attributes without string keys.", "S7761", cat="maintainability", kind="best-practice", sev="minor",
   filters=[r"cap.has_re:s:^['\x22`]data-"])
Js("DATE-CLONE-VIA-GETTIME", "Date cloned through getTime()", (MDN + "Global_Objects/Date/Date", "The Date() constructor creates Date objects", "MDN: Date() constructor"),
   "(new_expression constructor: (identifier) @d arguments: (arguments . (call_expression function: (member_expression property: (property_identifier) @g) arguments: (arguments)) .) (#eq? @d \"Date\") (#match? @g \"^(getTime|valueOf)$\")) @match",
   "const copy = new Date(start.getTime());\n", "const copy = new Date(start);\n",
   "new Date(date) already copies the timestamp.", "S7719", cat="maintainability", kind="best-practice", sev="minor")
Js("ERROR-WITHOUT-MESSAGE", "Built-in error created without a message", (MDN + "Global_Objects/Error/Error", "new Error(message)", "MDN: Error() constructor"),
   "(new_expression constructor: (identifier) @c arguments: (arguments) @a (#match? @c \"^(Error|TypeError|RangeError|SyntaxError|ReferenceError|EvalError|URIError|AggregateError)$\")) @match",
   "if (!user) {\n  throw new Error();\n}\n", "if (!user) {\n  throw new Error('user not found');\n}\n",
   "An error without a message gives no clue in logs or reports: say what failed.", "S7722", cat="maintainability", kind="best-practice", sev="minor",
   filters=[r"cap.has_re:a:^\(\s*\)$"])
Js("ARRAY-CALLBACK-THISARG", "thisArg passed to an array callback method", (MDN + "Global_Objects/Array/map", "map(callbackFn, thisArg)", "MDN: Array.prototype.map"),
   "(call_expression function: (member_expression property: (property_identifier) @m) arguments: (arguments . (_) . (this) .) (#match? @m \"^(map|filter|forEach|some|every|find|findIndex|findLast|findLastIndex|flatMap)$\")) @match",
   "const xs = ids.map(function (id) { return this.lookup(id); }, this);\n", "const xs = ids.map((id) => this.lookup(id));\n",
   "Passing this as thisArg is a pre-arrow-function workaround: use an arrow function (thisArg is ignored by arrows anyway).", "S7729", cat="maintainability", kind="best-practice", sev="minor")
Js("FOR-UPDATE-OTHER-VARIABLE", "for loop updates a variable other than the one it tests", (MDN + "Statements/for", "afterthought", "MDN: for"),
   "(for_statement condition: (binary_expression left: (identifier) @c) increment: (update_expression argument: (identifier) @u)) @match",
   "for (let i = 0; i < n; j++) {\n  use(i);\n}\n", "for (let i = 0; i < n; i++) {\n  use(i);\n}\n",
   "The tested counter is never advanced by the update, which usually means an infinite loop or a typo.", "S1994",
   filters=[r"cap.lacks_re:u:^{cap:c}$", r"node.lacks_re:^for\s*\([^;]*;[^;]*;[^)]*\b{cap:c}\b"])
Js("IMG-WITHOUT-ALT", "Image element without alt text", (ELEMENTS + "img", "alt Defines text", "MDN: <img>"),
   "([(jsx_self_closing_element name: (identifier) @t) (jsx_opening_element name: (identifier) @t)] @match (#eq? @t \"img\"))",
   "const Logo = () => <img src=\"/logo.svg\" />;\n", "const Logo = () => <img src=\"/logo.svg\" alt=\"Acme\" />;\n",
   "Screen readers announce an image without alt by its file name: describe it, or use alt=\"\" for decoration.", "S1077",
   cat="accessibility", kind="best-practice", sev="minor", rlang="jsx", filters=[r"node.lacks_re:\b(alt|aria-label|aria-labelledby)\s*=|\{\s*\.\.\.", r"node.lacks_re:\brole\s*=\s*[\x22']?(presentation|none)"])
Js("IFRAME-WITHOUT-TITLE", "iframe without a title", (ELEMENTS + "iframe", "title=\"Inline Frame Example\"", "MDN: <iframe>"),
   "([(jsx_self_closing_element name: (identifier) @t) (jsx_opening_element name: (identifier) @t)] @match (#eq? @t \"iframe\"))",
   "const Map = () => <iframe src=\"https://maps.example.com\" />;\n", "const Map = () => <iframe src=\"https://maps.example.com\" title=\"Store location\" />;\n",
   "Assistive technology uses the title to tell users what the frame contains.", "S1090",
   cat="accessibility", kind="best-practice", sev="minor", rlang="jsx", filters=[r"node.lacks_re:\btitle\s*=|\{\s*\.\.\."])
Js("ANCHOR-AS-BUTTON", "Anchor used as a button", (ELEMENTS + "a", "Anchor elements are often abused as fake buttons", "MDN: <a>"),
   "([(jsx_self_closing_element name: (identifier) @t) (jsx_opening_element name: (identifier) @t)] @match (#eq? @t \"a\"))",
   "const B = ({ go }) => <a href=\"#\" onClick={go}>Save</a>;\n", "const B = ({ go }) => <button type=\"button\" onClick={go}>Save</button>;\n",
   "An anchor without a real destination is announced as a link and breaks keyboard and middle-click behaviour: use a button.", "S6844",
   cat="accessibility", kind="best-practice", sev="minor", rlang="jsx",
   filters=[r"node.has_re:\bonClick\s*=", r"node.lacks_re:\bhref\s*=\s*(\{|[\x22'](/|https?:|mailto:|tel:|\.))"])
Js("ANCHOR-WITHOUT-CONTENT", "Anchor without accessible content", (ELEMENTS + "a", "Anchor elements are often abused as fake buttons", "MDN: <a>"),
   "(jsx_element open_tag: (jsx_opening_element name: (identifier) @t) . close_tag: (jsx_closing_element) (#eq? @t \"a\")) @match",
   "const L = () => <a href=\"/help\"></a>;\n", "const L = () => <a href=\"/help\">Help</a>;\n",
   "An empty link is announced as just 'link': give it text or an aria-label.", "S6827",
   cat="accessibility", kind="best-practice", sev="minor", rlang="jsx", filters=[r"node.lacks_re:\baria-label(ledby)?\s*=|\btitle\s*=|\{\s*\.\.\."])
Js("CLICK-WITHOUT-KEY-HANDLER", "Click handler on a non-interactive element without a keyboard handler", ("https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Keyboard-navigable_JavaScript_widgets", "keyboard", "MDN: Keyboard-navigable JavaScript widgets"),
   "([(jsx_self_closing_element name: (identifier) @t) (jsx_opening_element name: (identifier) @t)] @match (#match? @t \"^(div|span|li|p|td|tr|img|section|article)$\"))",
   "const C = ({ open }) => <div onClick={open}>Open</div>;\n", "const C = ({ open }) => <div role=\"button\" tabIndex={0} onClick={open} onKeyDown={open}>Open</div>;\n",
   "Keyboard users cannot trigger a mouse-only handler: use a button, or add a key handler, role and tabIndex.", "S1082",
   cat="accessibility", kind="best-practice", sev="minor", rlang="jsx",
   filters=[r"node.has_re:\bonClick\s*=", r"node.lacks_re:\bonKey(Down|Up|Press)\s*=|\{\s*\.\.\.", r"node.lacks_re:aria-hidden\s*=\s*[\x22'{]?\s*true"],
   eq=["sonar:javascript:S6847", "sonar:typescript:S6847"])
Js("VIDEO-WITHOUT-CAPTIONS", "video element without a captions track", (ELEMENTS + "video", "track", "MDN: <video>"),
   "(jsx_element open_tag: (jsx_opening_element name: (identifier) @t) (#eq? @t \"video\")) @match",
   "const V = () => (\n  <video src=\"/intro.mp4\" controls>\n    <source src=\"/intro.webm\" />\n  </video>\n);\n",
   "const V = () => (\n  <video src=\"/intro.mp4\" controls>\n    <track kind=\"captions\" src=\"/intro.vtt\" />\n  </video>\n);\n",
   "Without a captions track deaf and hard-of-hearing users miss the audio.", "S4084",
   cat="accessibility", kind="best-practice", sev="minor", rlang="jsx", filters=[r"node.lacks_re:<track\b", r"node.lacks_re:\bmuted\b"])

# ---- Python batch 3: exception semantics, builtins idioms, HTTP 204 -----------------------------
PYCMP = PYD + "reference/compound_stmts.html"
Py("EXCEPT-SHADOWED-BY-BROADER", "except clause after a broader Exception handler", (PYCMP, "inspects the except clauses in turn", "Python reference: The try statement"),
   "(try_statement (except_clause value: (identifier) @a) . (except_clause value: (_) @b) (#match? @a \"^(Exception|BaseException)$\")) @match",
   "try:\n    load()\nexcept Exception:\n    log()\nexcept ValueError:\n    retry()\n",
   "try:\n    load()\nexcept ValueError:\n    retry()\nexcept Exception:\n    log()\n",
   "Handlers are tried in order and the earlier Exception/BaseException clause catches everything, so the later handler never runs: put specific exceptions first.", "S1045",
   filters=[r"node.lacks_re:except\s*\*"])
Py("ITER-RETURNS-NON-ITERATOR", "__iter__ returns a literal that is not an iterator", (PYD + "library/stdtypes.html", "Return an iterator object", "Python docs: container.__iter__"),
   "(function_definition name: (identifier) @n body: (block (return_statement [(list) (dictionary) (tuple) (set) (string) (integer) (none)]) @match) (#eq? @n \"__iter__\"))",
   "class Bag:\n    def __iter__(self):\n        return [1, 2, 3]\n", "class Bag:\n    def __iter__(self):\n        return iter([1, 2, 3])\n",
   "iter() requires __iter__ to return an iterator; a list/tuple/str/None raises TypeError: wrap it in iter() or yield the items.", "S2876",
   filters=[r"func.lacks_re:\byield\b"])
Py("EXCEPT-NON-EXCEPTION-LITERAL", "except clause catching a literal", (PYCMP, "the expression must evaluate to an exception type", "Python reference: except clause"),
   "(except_clause value: [(string) (integer) (float) (none) (true) (false)] @match)",
   "try:\n    run()\nexcept 'timeout':\n    pass\n", "try:\n    run()\nexcept TimeoutError:\n    pass\n",
   "Only exception classes (or tuples of them) can be caught; a literal raises TypeError when an exception reaches this clause.", "S5708")
Py("RAISE-FROM-NON-EXCEPTION", "raise ... from a value that is not an exception", (PYD + "reference/simple_stmts.html", "must be another exception class or instance", "Python reference: The raise statement"),
   "(raise_statement cause: [(string) (integer) (float) (true) (false) (list) (dictionary)] @match)",
   "raise ValueError('bad') from 'parse'\n", "raise ValueError('bad') from err\n",
   "The from clause must be an exception (or None); anything else raises TypeError instead of the intended exception.", "S5707")
Py("EXCEPT-STAR-EXCEPTIONGROUP", "except* catching ExceptionGroup itself", (PYCMP, "A TypeError is raised if a matching type is a subclass of BaseExceptionGroup", "Python reference: except* clause"),
   "(except_clause value: [(identifier) @t (tuple (identifier) @t)] (#match? @t \"^(ExceptionGroup|BaseExceptionGroup)$\")) @match",
   "try:\n    run()\nexcept* ExceptionGroup:\n    pass\n", "try:\n    run()\nexcept* OSError:\n    pass\n",
   "except* matches the exceptions inside a group, so naming ExceptionGroup/BaseExceptionGroup raises TypeError: name the contained exception types.", "S6468",
   filters=[r"node.has_re:^except\s*\*"])
PYFN = PYD + "library/functions.html"
Py("ANY-ALL-LIST-COMPREHENSION", "any()/all() over a list comprehension", (PYFN, "Return True if any element of the iterable is true", "Python docs: any()"),
   "(call function: (identifier) @f arguments: (argument_list . (list_comprehension) .) (#match? @f \"^(any|all)$\")) @match",
   "ok = any([is_valid(x) for x in items])\n", "ok = any(is_valid(x) for x in items)\n",
   "The list comprehension evaluates every element before any()/all() sees one; a generator expression stops at the first decisive item.", "S7492",
   cat="performance", kind="best-practice", sev="minor", eq=["ruff:C419"])
Py("REVERSED-SORTED", "reversed(sorted(...))", (PYFN, "sorted as if each comparison were reversed", "Python docs: sorted()"),
   "(call function: (identifier) @r arguments: (argument_list . (call function: (identifier) @s) .) (#eq? @r \"reversed\") (#eq? @s \"sorted\")) @match",
   "for x in reversed(sorted(scores)):\n    show(x)\n", "for x in sorted(scores, reverse=True):\n    show(x)\n",
   "sorted(..., reverse=True) gives the descending list directly instead of sorting and then wrapping it in a reverse iterator.", "S7510",
   cat="maintainability", kind="best-practice", sev="minor", eq=["ruff:C413"])
Py("SET-OF-SORTED", "set(sorted(...))", (PYD + "library/stdtypes.html", "unordered collection of distinct", "Python docs: set"),
   "(call function: (identifier) @a arguments: (argument_list . (call function: (identifier) @s) .) (#match? @a \"^(set|frozenset)$\") (#eq? @s \"sorted\")) @match",
   "tags = set(sorted(raw_tags))\n", "tags = set(raw_tags)\n",
   "A set does not keep order, so the sort is wasted work: drop sorted() (or sort after building the set).", "S7516",
   cat="performance", kind="best-practice", sev="minor", eq=["ruff:C414"])
Py("DICT-COMPREHENSION-CONSTANT-VALUE", "Dict comprehension mapping every key to the same constant", (PYD + "library/stdtypes.html", "Create a new dictionary with keys from iterable", "Python docs: dict.fromkeys"),
   "(dictionary_comprehension body: (pair key: (identifier) @k value: [(integer) (float) (string) (none) (true) (false)]) (for_in_clause left: (identifier) @v) (#eq? @k @v)) @match",
   "seen = {name: False for name in names}\n", "seen = dict.fromkeys(names, False)\n",
   "dict.fromkeys(keys, value) states the intent directly (safe here because the value is immutable).", "S7519",
   cat="maintainability", kind="best-practice", sev="minor", eq=["ruff:C420"])
Py("SORTED-FOR-MIN-MAX", "sorted(...)[0] / [-1] to get the minimum or maximum", (PYFN, "Return the smallest item in an iterable", "Python docs: min()"),
   "(subscript value: (call function: (identifier) @s) subscript: [(integer) (unary_operator)] @i (#eq? @s \"sorted\") (#match? @i \"^(0|-\\\\s*1)$\")) @match",
   "cheapest = sorted(prices)[0]\n", "cheapest = min(prices)\n",
   "Sorting the whole sequence to read one end is O(n log n) and allocates a list; min()/max() are O(n).", "S8517",
   cat="performance", kind="best-practice", sev="minor")
Py("CLASS-FIELD-REDEFINED", "Class attribute assigned twice in the class body", (PYD + "tutorial/classes.html", "Class variables are for attributes and methods shared by all", "Python tutorial: Classes"),
   "(class_definition body: (block (expression_statement (assignment left: (identifier) @a)) (expression_statement (assignment left: (identifier) @b)) (#eq? @a @b))) @match",
   "class Config:\n    timeout = 10\n    retries = 3\n    timeout = 30\n", "class Config:\n    timeout = 30\n    retries = 3\n",
   "The later assignment silently replaces the earlier one, so one of the two values is dead: keep a single definition.", "S8512",
   cat="maintainability", kind="best-practice", sev="minor", filters=[r"node.lacks_re:(?m)^\s+(if|try|for|while|with)\b"])
Py("REVERSED-UNORDERED", "reversed() of a set, dict view or generator", (PYFN, "method or supports the sequence protocol", "Python docs: reversed()"),
   "(call function: (identifier) @r arguments: (argument_list . [(set) (set_comprehension) (generator_expression) (call function: (identifier) @c)] @a .) (#eq? @r \"reversed\")) @match",
   "for x in reversed({3, 1, 2}):\n    show(x)\n", "for x in reversed(sorted({3, 1, 2})):\n    show(x)\n",
   "Sets, generators and set()/frozenset()/iter()/map()/filter() results have no order to reverse, so reversed() raises TypeError.", "S9405",
   filters=[r"cap.has_re:a:^(\{|\(|set\(|frozenset\(|iter\(|map\(|filter\(|zip\()"])
Py("NONE-RESULT-ASSIGNED", "Result of an in-place list method or print() assigned", (PYD + "library/stdtypes.html", "never return the collection instance itself but None", "Python docs: Sequence types"),
   "((assignment right: (call function: (attribute object: (_) @recv attribute: (identifier) @m))) @match (#match? @m \"^(append|extend|insert|sort|reverse)$\"))\n((assignment right: (call function: (identifier) @m)) @match (#eq? @m \"print\"))",
   "def f(items: list):\n    ordered = items.sort()\n    return ordered\n", "def f(items: list):\n    items.sort()\n    return items\n",
   "These calls work in place (or just write output) and return None, so the variable becomes None: call it as a statement or use sorted()/a copy.", "S3699",
   # Only receivers known to be lists: django's reverse(), client.videos.extend(...) return values.
   filters=[r"node.lacks_re:\b(self|cls)\.\w+\s*=\s*\w+\.(append|extend|insert)\b", "type.is:recv:list(\\[.*\\])?|List(\\[.*\\])?"],
   fp=["from django.urls import reverse\n\ndef f():\n    url = reverse(\"home\")\n    return url\n", "def f(client):\n    video = client.videos.extend(prompt=\"x\")\n    return video\n"])
Py("NO-CONTENT-WITH-BODY", "Endpoint declared 204 No Content returns a body", ("https://www.rfc-editor.org/rfc/rfc9110.html", "it cannot contain content or trailers", "RFC 9110: 204 No Content"),
   "(decorated_definition (decorator) @d definition: (function_definition body: (block (return_statement (_) @v) @match))) ",
   "@app.delete('/items/{id}', status_code=204)\ndef delete(id: int):\n    repo.delete(id)\n    return {'deleted': id}\n",
   "@app.delete('/items/{id}', status_code=204)\ndef delete(id: int):\n    repo.delete(id)\n",
   "A 204 response cannot carry content; the returned value is dropped or makes the server send an invalid response. Return nothing (or use 200 with the body).", "S8400",
   filters=[r"cap.has_re:d:status_code\s*=\s*(204|status\.HTTP_204_NO_CONTENT|HTTPStatus\.NO_CONTENT)", r"cap.lacks_re:v:^(None|Response\(|JSONResponse\(\s*status_code)"])

# ---- Java batch 4: concurrency APIs, JDK idioms, JDBC -------------------------------------------
J("MATH-ABS-OF-HASH", "Math.abs of hashCode()/nextInt() can stay negative", (JAPI + "lang/Math.html", "the result is that same value, which is negative", "Java SE 21 API: Math.abs"),
  "(method_invocation object: (identifier) @m name: (identifier) @a arguments: (argument_list . (method_invocation) .) (#eq? @m \"Math\") (#eq? @a \"abs\")) @match",
  jm(["int bucket = Math.abs(key.hashCode()) % buckets;"]), jm(["int bucket = Math.floorMod(key.hashCode(), buckets);"]),
  "Math.abs(Integer.MIN_VALUE) is still negative, and hashCode()/nextInt() can return it, so the index can be negative: use Math.floorMod or mask the sign bit.", "S2676",
  filters=[r"node.has_re:\.(hashCode\(\s*\)|nextInt\(\s*\)|nextLong\(\s*\))\s*\)$|identityHashCode\("])
J("VARARGS-EXPLICIT-ARRAY", "Array created only to pass it to a varargs method", ("https://docs.oracle.com/javase/specs/jls/se25/html/jls-15.html#jls-15.12.4.2", "variable arity invocation", "JLS SE 25 15.12.4.2 Evaluate Arguments"),
  "(method_invocation name: (identifier) @n arguments: (argument_list (array_creation_expression value: (array_initializer)) .) (#match? @n \"^(format|formatted|printf|asList)$\")) @match",
  jm(["String s = String.format(\"%s=%d\", new Object[] {key, value});"]), jm(["String s = String.format(\"%s=%d\", key, value);"]),
  "The method takes varargs, so the explicit array only adds noise: pass the elements directly.", "S3878", cat="maintainability", kind="best-practice", sev="minor",
  filters=[r"node.lacks_re:\bformat\(\s*new\b", r"node.lacks_re:\basList\(\s*([^n\s]|n[^e]|ne[^w])", r"node.lacks_re:(?s)\basList\(\s*new\b.*\}\s*,"],
  fp=[jm(["String s = messageFormat.format(new Object[] {\"a\", \"b\"});"]), jm(["List<Object[]> rows = Arrays.asList(new Object[] {1}, new Object[] {2});"])])
J("HEX-VIA-TOHEXSTRING", "Byte hex string built with Integer.toHexString", (JAPI + "util/HexFormat.html", "HexFormat converts between bytes and chars and hex-encoded strings", "Java SE 21 API: HexFormat"),
  "(method_invocation object: (identifier) @i name: (identifier) @t arguments: (argument_list . (binary_expression) @b .) (#eq? @i \"Integer\") (#eq? @t \"toHexString\")) @match",
  jm(["for (byte b : digest) {", "    sb.append(Integer.toHexString(b & 0xff));", "}"]), jm(["String hex = HexFormat.of().formatHex(digest);"]),
  "toHexString drops the leading zero for bytes below 0x10, so different digests can render alike: use HexFormat.of().formatHex(bytes) or String.format(\"%02x\").", "S4425",
  sev="minor", filters=[r"cap.has_re:b:&\s*0[xX][fF][fF]$"], applies={"java": ">=17"})
J("RECORD-SERIALVERSIONUID-ZERO", "Record declares serialVersionUID = 0L", ("https://docs.oracle.com/en/java/javase/21/docs/specs/serialization/class.html", "Record classes have a default serialVersionUID value of 0L", "Java Object Serialization Specification: records"),
  "(record_declaration body: (class_body (field_declaration declarator: (variable_declarator name: (identifier) @n value: (_) @v)) @match) (#eq? @n \"serialVersionUID\") (#match? @v \"^0[lL]?$\"))",
  "record Point(int x, int y) implements java.io.Serializable {\n    private static final long serialVersionUID = 0L;\n}\n",
  "record Point(int x, int y) implements java.io.Serializable {\n}\n",
  "0L is already the default for records (and their serialVersionUID is not checked), so the field is noise: remove it.", "S6219", cat="maintainability", kind="best-practice", sev="minor", applies={"java": ">=16"})
J("REVERSE-INDEX-LOOP", "List walked backwards by index instead of reversed()", (JAPI + "util/List.html", "Returns a reverse-ordered view of this collection", "Java SE 21 API: List.reversed"),
  "(for_statement init: (local_variable_declaration declarator: (variable_declarator name: (identifier) @i value: (binary_expression left: (method_invocation object: (identifier) @l name: (identifier) @s)))) body: (_) @body (#eq? @s \"size\")) @match",
  jm(["for (int i = items.size() - 1; i >= 0; i--) {", "    show(items.get(i));", "}"]), jm(["for (Item item : items.reversed()) {", "    show(item);", "}"]),
  "The index only serves to read the list backwards: iterate list.reversed() (Java 21) instead.", "S6876", cat="maintainability", kind="modernization", sev="minor",
  applies={"java": ">=21"}, filters=[r"cap.has_re:body:\b{cap:l}\.get\(\s*{cap:i}\s*\)", r"cap.lacks_re:body:\b{cap:l}\.(remove|add|set)\(|\b{cap:i}\s*[-+]|[-+]\s*{cap:i}\b|\[\s*{cap:i}\s*\]"])
J("VIRTUAL-THREAD-DAEMON-PRIORITY", "Daemon/priority/thread group used on a virtual thread", (JAPI + "lang/Thread.html", "The daemon status of a virtual thread is always true", "Java SE 21 API: Thread"),
  "(method_invocation object: (_) @o name: (identifier) @n (#match? @n \"^(setDaemon|setPriority|getThreadGroup)$\") (#match? @o \"ofVirtual\\\\(|startVirtualThread\\\\(\")) @match",
  jm(["Thread.ofVirtual().unstarted(task).setDaemon(false);"]), jm(["Thread.ofVirtual().start(task);"]),
  "Virtual threads are always daemon, ignore priority and share one placeholder thread group: setDaemon(false) throws, the rest has no effect.", "S6901", applies={"java": ">=21"})
J("NOW-WITHOUT-CLOCK", "java.time now() without a Clock or ZoneId", (JAPI + "time/LocalDate.html", "the clock is hard-coded", "Java SE 21 API: LocalDate.now"),
  "(method_invocation object: (identifier) @c name: (identifier) @n arguments: (argument_list) @a (#match? @c \"^(LocalDate|LocalDateTime|LocalTime|ZonedDateTime|OffsetDateTime|YearMonth|Year)$\") (#eq? @n \"now\") (#eq? @a \"()\")) @match",
  jm(["LocalDate today = LocalDate.now();"]), jm(["LocalDate today = LocalDate.now(clock);"]),
  "now() reads the default clock and time zone, so results depend on the server's zone and cannot be controlled in tests: pass a Clock (or ZoneId).", "S8688",
  cat="maintainability", kind="best-practice", sev="minor", optin=True)
J("TRYLOCK-RESULT-IGNORED", "tryLock() result ignored", (JAPI + "util/concurrent/locks/Lock.html", "A typical usage idiom for this method would be", "Java SE 21 API: Lock.tryLock"),
  "(expression_statement (method_invocation name: (identifier) @n (#eq? @n \"tryLock\")) @match)",
  jm(["lock.tryLock();", "try {", "    update();", "} finally {", "    lock.unlock();", "}"]),
  jm(["if (lock.tryLock()) {", "    try {", "        update();", "    } finally {", "        lock.unlock();", "    }", "}"]),
  "tryLock() reports whether the lock was acquired; ignoring it runs the critical section unlocked (and unlock() then throws).", "S899")
J("SCHEDULED-POOL-SET-MAX", "setMaximumPoolSize on a ScheduledThreadPoolExecutor", (JAPI + "util/concurrent/ScheduledThreadPoolExecutor.html", "adjustments to maximumPoolSize have no useful effect", "Java SE 21 API: ScheduledThreadPoolExecutor"),
  "(method_invocation object: (identifier) @o name: (identifier) @n (#eq? @n \"setMaximumPoolSize\")) @match",
  jm(["ScheduledThreadPoolExecutor pool = new ScheduledThreadPoolExecutor(2);", "pool.setMaximumPoolSize(20);"]),
  jm(["ScheduledThreadPoolExecutor pool = new ScheduledThreadPoolExecutor(20);"]),
  "This executor runs a fixed pool of corePoolSize threads, so the maximum pool size is never used: size it with the core pool size.", "S9132",
  filters=[r"file.has_re:ScheduledThreadPoolExecutor(<[^>]*>)?\s+{cap:o}\b"])
J("PREPARE-STATEMENT-IN-LOOP", "PreparedStatement prepared inside a loop", ("https://docs.oracle.com/javase/tutorial/jdbc/basics/prepared.html", "precompiled", "JDBC tutorial: Using Prepared Statements"),
  "(method_invocation name: (identifier) @n (#eq? @n \"prepareStatement\")) @match",
  jm(["for (User u : users) {", "    try (PreparedStatement ps = conn.prepareStatement(\"UPDATE users SET seen = ? WHERE id = ?\")) {", "        ps.setTimestamp(1, now);", "        ps.setLong(2, u.id());", "        ps.executeUpdate();", "    }", "}"], sig="void f() throws SQLException"),
  jm(["try (PreparedStatement ps = conn.prepareStatement(\"UPDATE users SET seen = ? WHERE id = ?\")) {", "    for (User u : users) {", "        ps.setTimestamp(1, now);", "        ps.setLong(2, u.id());", "        ps.addBatch();", "    }", "    ps.executeBatch();", "}"], sig="void f() throws SQLException"),
  "The statement text does not change between iterations, yet it is re-prepared each time: prepare once before the loop and rebind parameters (or batch).", "S9142",
  cat="performance", kind="best-practice", sev="minor",
  filters=["node.has_ancestor:for_statement|enhanced_for_statement|while_statement|do_statement", r"node.has_re:prepareStatement\(\s*\x22[^\x22]*\x22\s*[,)]"])
J("OCTAL-ESCAPE-THEN-DIGIT", "Octal escape followed by a digit", ("https://docs.oracle.com/javase/specs/jls/se21/html/jls-3.html", "OctalEscape", "JLS 21 §3.10.7 Escape Sequences"),
  "(string_literal) @match",
  jm(["String s = \"\\1234\";"]), jm(["String s = \"\\u00534\";"]),
  "An octal escape takes at most three digits (max \\377), so the next digit becomes a separate character: readers misread the value. Use a \\u escape.", "S9359",
  cat="maintainability", kind="best-practice", sev="minor", filters=[r"node.has_re:(^|[^\\])(\\\\)*\\([0-3][0-7]{2}[0-9]|[0-7]{1,2}[89])"])
J("IDENTICAL-CATCH-BLOCKS", "Adjacent catch blocks with identical bodies", ("https://docs.oracle.com/javase/specs/jls/se25/html/jls-14.html#jls-14.20", "A catch clause whose exception parameter is denoted as a union of types is called a multi-catch clause", "JLS SE 25 14.20 The try statement"),
  "(try_statement (catch_clause body: (block) @a) . (catch_clause body: (block) @b) (#eq? @a @b)) @match",
  jm(["try {", "    load();", "} catch (IOException e) {", "    log.warn(\"load failed\", e);", "} catch (SQLException e) {", "    log.warn(\"load failed\", e);", "}"]),
  jm(["try {", "    load();", "} catch (IOException | SQLException e) {", "    log.warn(\"load failed\", e);", "}"]),
  "Both handlers do the same thing: one multi-catch (A | B e) keeps them in sync.", "S2147", cat="maintainability", kind="best-practice", sev="minor",
  filters=[r"cap.lacks_re:a:^\{\s*\}$"])
J("WAIT-ON-THREAD", "wait/notify called on a Thread object", (JAPI + "lang/Thread.html", "notifyAll on Thread instances", "Java SE 21 API: Thread.join"),
  "(method_invocation object: (method_invocation object: (identifier) @t name: (identifier) @c) name: (identifier) @n (#eq? @t \"Thread\") (#eq? @c \"currentThread\") (#match? @n \"^(wait|notify|notifyAll)$\")) @match",
  jm(["synchronized (Thread.currentThread()) {", "    Thread.currentThread().wait(100);", "}"], sig="void f() throws InterruptedException"),
  jm(["synchronized (lock) {", "    lock.wait(100);", "}"], sig="void f() throws InterruptedException"),
  "Thread uses its own monitor for join(); waiting or notifying on it interferes with join and is notified when threads end.", "S2236")
J("SYNCHRONIZED-ON-LOCK-OBJECT", "synchronized block on a java.util.concurrent object", (JAPI + "util/concurrent/locks/Lock.html", "never use Lock instances in this way", "Java SE 21 API: Lock"),
  "(synchronized_statement (parenthesized_expression [(identifier) @x (field_access field: (identifier) @x)])) @match",
  cls("    private final ReentrantLock lock = new ReentrantLock();\n    void f() {\n        synchronized (lock) {\n            work();\n        }\n    }\n"),
  cls("    private final ReentrantLock lock = new ReentrantLock();\n    void f() {\n        lock.lock();\n        try {\n            work();\n        } finally {\n            lock.unlock();\n        }\n    }\n"),
  "Its monitor is unrelated to the object's own locking (lock()/acquire()/atomic ops), so code mixing both is not mutually exclusive: use the object's API.", "S2442",
  filters=[r"file.has_re:\b(ReentrantLock|ReentrantReadWriteLock|ReadWriteLock|Lock|StampedLock|Semaphore|CountDownLatch|CyclicBarrier|Atomic[A-Z]\w*|Concurrent[A-Z]\w*)(<[^>]*>)?\s+{cap:x}\s*[=;]"])

# ---- Web/HTML batch 2, JS and PHP backlog ------------------------------------------------------
ELM = "https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/"
TAG = "[(start_tag (tag_name) @t) (self_closing_tag (tag_name) @t)] @match"
Hm("META-REFRESH", "<meta http-equiv=\"refresh\"> reload or redirect", ("https://www.w3.org/WAI/WCAG22/Techniques/failures/F41", "using meta refresh", "WCAG 2.2 failure F41"),
   "(start_tag (tag_name) @t (#match? @t \"^(?i)meta$\")) @match",
   page("<p>Moved</p>", head="<title>Orders</title><meta http-equiv=\"refresh\" content=\"5; url=/new\">"), page("<p>Moved: <a href=\"/new\">new page</a></p>"),
   "A timed refresh/redirect moves users before they finish reading and breaks the Back button; redirect on the server (301/302) or let the user follow a link.", "Web:MetaRefreshCheck",
   filters=[r"node.has_re:(?i)http-equiv\s*=\s*[\x22']?refresh"])
Hm("VIEWPORT-BLOCKS-ZOOM", "Viewport meta tag disables zooming", ("https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html", "up to 200 percent", "WCAG 2.2 Understanding 1.4.4 Resize Text"),
   "(start_tag (tag_name) @t (#match? @t \"^(?i)meta$\")) @match",
   page("<p>Hi</p>", head="<title>Orders</title><meta name=\"viewport\" content=\"width=device-width, user-scalable=no\">"),
   page("<p>Hi</p>", head="<title>Orders</title><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"),
   "user-scalable=no / maximum-scale=1 stops low-vision users from pinch-zooming: remove them.", "Web:S7926",
   filters=[r"node.has_re:(?i)name\s*=\s*[\x22']?viewport", r"node.has_re:(?i)user-scalable\s*=\s*(no|0)\b|maximum-scale\s*=\s*1(\.0*)?\b"])
Hm("AUTOPLAY-MEDIA", "Audio/video set to autoplay with sound", (ELM + "video", "can be an unpleasant experience for users", "MDN: <video> autoplay"),
   "(start_tag (tag_name) @t (attribute (attribute_name) @a) (#match? @t \"^(?i)(audio|video)$\") (#match? @a \"^(?i)autoplay$\")) @match",
   page("<video src=\"intro.mp4\" autoplay></video>"), page("<video src=\"intro.mp4\" controls></video>"),
   "Sound that starts on its own talks over screen readers and startles users; let them start playback (or autoplay muted).", "Web:S7929",
   filters=[r"node.lacks_re:(?i)\bmuted\b"])
Hm("IMG-WITHOUT-ALT", "<img> or <area> without alt", (ELM + "img", "Setting this attribute to an empty string", "MDN: <img> alt"),
   "(" + TAG + " (#match? @t \"^(?i)(img|area)$\"))",
   page("<img src=\"logo.png\">"), page("<img src=\"logo.png\" alt=\"Acme\">"),
   "Without alt, screen readers read the file name; describe the image, or use alt=\"\" when it is decorative.", "Web:ImgWithoutAltCheck",
   filters=[r"node.lacks_re:(?i)\s(alt|:alt|v-bind:alt|\[alt\]|\[attr\.alt\])\s*=|\{\{|\{%"])
Hm("FRAME-WITHOUT-TITLE", "<iframe>/<frame> without a title", (ELM + "iframe", "title attribute", "MDN: <iframe> accessibility"),
   "(" + TAG + " (#match? @t \"^(?i)(iframe|frame)$\"))",
   page("<iframe src=\"/map\"></iframe>"), page("<iframe src=\"/map\" title=\"Store locations map\"></iframe>"),
   "Screen readers announce an untitled frame as just \"frame\"; a title says what it contains.", "Web:FrameWithoutTitleCheck",
   filters=[r"node.lacks_re:(?i)\s(:?title|aria-label|aria-labelledby|aria-hidden)\s*="])
Hm("LI-OUTSIDE-LIST", "<li> whose parent is not a list", (ELM + "li", "must be contained in a parent element", "MDN: <li>"),
   "(element (start_tag (tag_name) @p) (element (start_tag (tag_name) @c)) @match (#match? @c \"^(?i)li$\"))",
   page("<div><li>One</li></div>"), page("<ul><li>One</li></ul>"),
   "List items outside ul/ol/menu are not exposed as a list, so assistive technology loses the item count and structure.", "Web:ItemTagNotWithinContainerTagCheck",
   filters=[r"cap.lacks_re:p:(?i)^(ul|ol|menu|template|slot)$"])
Hm("ANCHOR-AS-BUTTON", "<a> used as a button", (ELM + "a", "Anchor elements are often abused as fake buttons", "MDN: <a> onclick events"),
   "(start_tag (tag_name) @t (#match? @t \"^(?i)a$\")) @match",
   page("<a href=\"#\" onclick=\"save()\">Save</a>"), page("<button type=\"button\" onclick=\"save()\">Save</button>"),
   "An anchor with a dummy href and a click handler is announced as a link, is not triggered by Space and pollutes history: use <button>.", "Web:S6844",
   filters=[r"node.has_re:(?i)\son(click|mousedown)\s*=", r"node.has_re:(?i)\shref\s*=\s*[\x22'](#[\x22']|javascript:)|^<a(\s+[^>]*)?>$", r"node.lacks_re:(?i)\shref\s*=\s*[\x22'][^#j\x22']"])
Hm("EMPTY-ANCHOR", "Link without any content", (ELM + "a", "link text", "MDN: <a> accessibility"),
   "(element (start_tag (tag_name) @t) @s . (end_tag) (#match? @t \"^(?i)a$\")) @match",
   page("<a href=\"/cart\"></a>"), page("<a href=\"/cart\">Cart</a>"),
   "The link has no text, so screen readers announce only the URL (or nothing): add text or an aria-label.", "Web:S6827",
   filters=[r"cap.has_re:s:(?i)\shref\s*=", r"cap.lacks_re:s:(?i)\s(aria-label|aria-labelledby|title|v-html|v-text|:aria-label|\[innerHTML\])\s*="])
Hm("OBJECT-WITHOUT-FALLBACK", "<object> without fallback content", (ELM + "object", "fallback", "MDN: <object>"),
   "(element (start_tag (tag_name) @t) . (end_tag) (#match? @t \"^(?i)object$\")) @match",
   page("<object data=\"report.pdf\" type=\"application/pdf\"></object>"),
   page("<object data=\"report.pdf\" type=\"application/pdf\"><a href=\"report.pdf\">Download the report</a></object>"),
   "When the resource cannot be shown (no plugin, blocked, screen reader) the user gets nothing: put a text alternative or link inside.", "Web:S5264")
Hm("SRCSET-WITHOUT-DESCRIPTOR", "srcset candidate without a width or density descriptor", (ELM + "img", "width descriptor", "MDN: <img> srcset"),
   "((attribute (attribute_name) @a) @match (#match? @a \"^(?i)srcset$\"))",
   page("<img src=\"a.jpg\" srcset=\"a.jpg, a-2x.jpg 2x\" alt=\"A\">"), page("<img src=\"a.jpg\" srcset=\"a.jpg 1x, a-2x.jpg 2x\" alt=\"A\">"),
   "With several candidates, one without a w/x descriptor defaults to 1x and can collide with another, so the browser may pick the wrong file: give every entry a descriptor.", "Web:S8697",
   cat="correctness", filters=[r"node.has_re:,", r"node.has_re:[\x22',]\s*[^\s,\x22']+\s*(,|[\x22']\s*$)"])
Hm("CLICK-WITHOUT-KEYBOARD", "Click handler on a non-interactive element without a key handler", ("https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html", "operable through a keyboard interface", "WCAG 2.2 Understanding 2.1.1 Keyboard"),
   "(start_tag (tag_name) @t (attribute (attribute_name) @a) (#match? @a \"^(?i)onclick$\")) @match",
   page("<div onclick=\"openMenu()\">Menu</div>"), page("<div role=\"button\" tabindex=\"0\" onclick=\"openMenu()\" onkeydown=\"menuKey(event)\">Menu</div>"),
   "Keyboard users cannot trigger this element: use a <button>, or add tabindex, a role and a key handler.", "Web:MouseEventWithoutKeyboardEquivalentCheck",
   filters=[r"cap.lacks_re:t:(?i)^(a|button|input|select|textarea|summary|option|label|details|body|form)$", r"node.lacks_re:(?i)\sonkey(down|up|press)\s*="])

Js("DELETE-ARRAY-ELEMENT", "delete on an array element", (MDN + "Operators/delete", "the array length is not affected", "MDN: delete"),
   "(unary_expression operator: \"delete\" argument: (subscript_expression index: (number))) @match",
   "delete queue[0];\n", "queue.splice(0, 1);\n",
   "delete leaves a hole (length unchanged, the slot reads undefined): use splice() or shift()/pop().", "S2870")
Js("IN-ON-ARRAY-LITERAL", "in operator on an array literal", (MDN + "Operators/in", "in operator", "MDN: in"),
   "(binary_expression operator: \"in\" right: (array)) @match",
   "if (status in ['open', 'pending']) {\n  notify();\n}\n", "if (['open', 'pending'].includes(status)) {\n  notify();\n}\n",
   "in tests array indexes (0, 1, ...), not values, so this is almost always false: use includes().", "S4619")
Js("CONCAT-SPREAD-FLATTEN", "[].concat(...arrays) to flatten", (MDN + "Global_Objects/Array/flat", "sub-array elements concatenated into it recursively", "MDN: Array.prototype.flat"),
   "(call_expression function: (member_expression object: (array) @a property: (property_identifier) @c) arguments: (arguments . (spread_element) .) (#eq? @c \"concat\")) @match",
   "const all = [].concat(...groups);\n", "const all = groups.flat();\n",
   "flat() says what is meant and does not hit the argument-count limit of spreading a huge array.", "S7751",
   cat="maintainability", kind="modernization", sev="minor", filters=[r"cap.has_re:a:^\[\s*\]$"])
Js("FORCED-TEST-INTERACTION", "Test interaction forced past actionability checks", ("https://playwright.dev/docs/actionability", "force", "Playwright: Auto-waiting / actionability"),
   "(call_expression function: (member_expression property: (property_identifier) @m) arguments: (arguments (object (pair key: (property_identifier) @k value: (true)))) (#match? @m \"^(click|dblclick|check|uncheck|fill|hover|tap|selectOption|setChecked|dragTo|type|clear|select|trigger|rightclick)$\") (#eq? @k \"force\")) @match",
   "await page.getByRole('button', { name: 'Pay' }).click({ force: true });\n", "await page.getByRole('button', { name: 'Pay' }).click();\n",
   "force skips the visible/enabled/not-covered checks, so the test passes even when a real user could not click: fix the page state or wait instead.", "S8783",
   cat="testing", kind="best-practice", sev="minor", files=["**/*.spec.*", "**/*.test.*", "**/e2e/**", "**/cypress/**", "**/tests/**", "**/test/**"])

Ph("OPTIONAL-BEFORE-REQUIRED-PARAM", "Optional parameter declared before a required one", (PHPM + "functions.arguments.php", "Declaring mandatory", "PHP manual: Function arguments"),
   "(formal_parameters (simple_parameter default_value: (_) @d) (simple_parameter) @b) @match",
   "<?php\nfunction makeYogurt($container = 'bowl', $flavour)\n{\n    return \"$flavour in $container\";\n}\n",
   "<?php\nfunction makeYogurt($flavour, $container = 'bowl')\n{\n    return \"$flavour in $container\";\n}\n",
   "The default can never apply because a required parameter follows it; PHP 8 deprecates this. Move optional parameters last.", "S1788",
   kind="deprecation", cat="maintainability", sev="minor", filters=[r"cap.lacks_re:b:=", r"cap.lacks_re:d:(?i)^null$"])


# ---- Sonar backlog batch A (cross-language and per-language tree-sitter checks) -----------------
TWELVE = ("https://12factor.net/config", "strict separation of config from code", "The Twelve-Factor App: Config")
IPV4 = r"[\x22\x27](?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)[\x22\x27]"
IP_SKIP = r"node.lacks_re:^[\x22\x27](127\.|0\.0\.0\.0|255\.255\.255\.255|192\.0\.2\.|198\.51\.100\.|203\.0\.113\.)"
# corpus: every sampled hit was a test fixture (proxy/remote-address stubs); tests are skipped
multi("HARDCODED-IP", "Hard-coded IP address",
      "A literal IP address ties the code to one network layout: read it from configuration or resolve a host name.",
      {
          "java": dict(files=["!**/src/test/**", "!**/test/**", "!**/*Test.java", "!**/*Tests.java"], doc=TWELVE, query="(string_literal) @match", filters=["node.has_re:^" + IPV4 + "$", IP_SKIP],
                       bad=cls("    String host = \"10.20.30.40\";\n"), good=cls("    String host = System.getenv(\"DB_HOST\");\n"),
                       fp=[cls("    String local = \"127.0.0.1\";\n    String doc = \"192.0.2.10\";\n")]),
          "javascript": dict(files=["!**/*.test.*", "!**/*.spec.*", "!**/__tests__/**", "!**/test/**", "!**/tests/**"], doc=TWELVE, query="(string) @match", filters=["node.has_re:^" + IPV4 + "$", IP_SKIP],
                             bad="const host = '10.20.30.40';\n", good="const host = process.env.DB_HOST;\n", fp=["const local = '127.0.0.1';\n"]),
          "python": dict(files=["!**/tests/**", "!**/test/**", "!**/test_*.py", "!**/*_test.py"], doc=TWELVE, query="(string) @match", filters=["node.has_re:^" + IPV4 + "$", IP_SKIP],
                         bad="HOST = \"10.20.30.40\"\n", good="HOST = os.environ[\"DB_HOST\"]\n", fp=["LOCAL = \"127.0.0.1\"\n"]),
          "go": dict(files=["!**/*_test.go", "!**/testdata/**"], doc=TWELVE, query="(interpreted_string_literal) @match", filters=["node.has_re:^" + IPV4 + "$", IP_SKIP],
                     bad="package p\n\nvar host = \"10.20.30.40\"\n", good="package p\n\nimport \"os\"\n\nvar host = os.Getenv(\"DB_HOST\")\n",
                     fp=["package p\n\nvar local = \"127.0.0.1\"\n"]),
          "kotlin": dict(files=["!**/src/test/**", "!**/test/**", "!**/*Test.kt", "!**/*Tests.kt"], doc=TWELVE, query="(string_literal) @match", filters=["node.has_re:^" + IPV4 + "$", IP_SKIP],
                         bad="val host = \"10.20.30.40\"\n", good="val host = System.getenv(\"DB_HOST\")\n", fp=["val local = \"127.0.0.1\"\n"]),
          "php": dict(files=["!**/tests/**", "!**/Tests/**", "!**/*Test.php"], doc=TWELVE, query="[(string) (encapsed_string)] @match", filters=["node.has_re:^" + IPV4 + "$", IP_SKIP],
                      bad="<?php\n$host = '10.20.30.40';\n", good="<?php\n$host = getenv('DB_HOST');\n", fp=["<?php\n$local = '127.0.0.1';\n"]),
      }, keys=["S1313"], mode="ai-confirm",
      ai="Is this the address of a real host or network (not a version number, a test fixture or a documentation example)?")

Ph("EMPTY-STATEMENT", "Empty statement", (PHPM + "language.basic-syntax.instruction-separation.php", "terminated with a semicolon", "PHP manual: Instruction separation"),
   "(empty_statement) @match", phf(["$a = 1;;"]), phf(["$a = 1;"]),
   "A stray semicolon is an empty statement: remove it (after a control header it silently detaches the body).", "S1116",
   cat="maintainability", kind="best-practice", sev="minor")
G("EMPTY-STATEMENT", "Empty statement", ("https://go.dev/ref/spec", "The empty statement does nothing", "The Go Programming Language Specification"),
  "(empty_statement) @match", "package p\n\nfunc f() {\n\tg();\n\t;\n}\n", "package p\n\nfunc f() {\n\tg()\n}\n",
  "A stray semicolon is an empty statement that gofmt deletes: remove it.", "godre:S1116", cat="maintainability", kind="best-practice", sev="minor")

JLS3 = "https://docs.oracle.com/javase/specs/jls/se21/html/jls-3.html"
J("DANGLING-ELSE", "else of a nested if without braces", (JLS14, "dangling else", "JLS 14.5 Statements"),
  "(if_statement consequence: (if_statement alternative: (_)) !alternative) @match",
  jm(["if (a)", "    if (b) x();", "    else y();"], "void f(boolean a, boolean b)"),
  jm(["if (a) {", "    if (b) x();", "    else y();", "}"], "void f(boolean a, boolean b)"),
  "The else binds to the inner if whatever the indentation says: add braces so the pairing is explicit.", "S5261",
  cat="maintainability", kind="best-practice", sev="minor")
J("RESTRICTED-IDENTIFIER", "Contextual keyword used as an identifier", (JLS3, "contextual keywords", "JLS 3.9 Keywords"),
  "([(variable_declarator name: (identifier) @match) (formal_parameter name: (identifier) @match)] (#match? @match \"^(var|yield|record|sealed|permits|when)$\"))",
  jm(["String record = load();", "use(record);"]), jm(["String entry = load();", "use(entry);"]),
  "var, yield, record, sealed, permits and when are contextual keywords: as names they confuse readers and break in some positions; rename.", "S6213",
  cat="maintainability", kind="best-practice", sev="minor")
J("TEXT-BLOCK-ESCAPE", "Needless escape sequence in a text block", (JLS3, "Text Blocks", "JLS 3.10.6 Text Blocks"),
  "(string_literal) @match", jm(["String q = \"\"\"", "    say \\\"hi\\\"\\n", "    \"\"\";"]), jm(["String q = \"\"\"", "    say \"hi\"", "    \"\"\";"]),
  "Text blocks keep quotes and line breaks literally, so \\n and \\\" only add noise: write the characters directly.", "S5665",
  cat="maintainability", kind="best-practice", sev="minor", filters=[r'node.has_re:^"""[\s\S]*\\(n|"[^"])'])
J("SET-ACCESSIBLE", "Reflection used to bypass access control", (JAPI + "lang/reflect/AccessibleObject.html", "suppress checks for Java language access control", "Java SE 21 API: AccessibleObject"),
  "(method_invocation name: (identifier) @m arguments: (argument_list . (true) .) (#eq? @m \"setAccessible\")) @match",
  jm(["field.setAccessible(true);", "field.set(target, value);"], "void f(java.lang.reflect.Field field, Object target, Object value) throws Exception"),
  jm(["target.setValue(value);"], "void f(Target target, Object value)"),
  "setAccessible(true) breaks encapsulation and fails under strong module encapsulation: use the public API or a MethodHandle granted by the owner.", "S3011",
  cat="maintainability", kind="best-practice", mode="ai-confirm", ai="Is the reflection bypass outside test code and not required by a framework contract?")
J("THREAD-AS-RUNNABLE", "Thread passed where a Runnable is expected", (JAPI + "lang/Runnable.html", "Runnable", "Java SE 21 API: Runnable"),
  "(object_creation_expression type: (type_identifier) @t arguments: (argument_list (object_creation_expression type: (type_identifier) @t2)) (#eq? @t \"Thread\") (#eq? @t2 \"Thread\")) @match\n"
  "(method_invocation name: (identifier) @m arguments: (argument_list (object_creation_expression type: (type_identifier) @t2)) (#match? @m \"^(submit|execute)$\") (#eq? @t2 \"Thread\")) @match",
  jm(["pool.submit(new Thread(task));"], "void f(java.util.concurrent.ExecutorService pool, Runnable task)"),
  jm(["pool.submit(task);"], "void f(java.util.concurrent.ExecutorService pool, Runnable task)"),
  "Only the run() method of the inner Thread is used; its thread is never started. Pass the Runnable itself.", "S2438", sev="minor")
J("EMPTY-ZIP-ENTRY", "Archive entry closed without content", (JAPI + "util/zip/ZipOutputStream.html", "Begins writing a new ZIP file entry", "Java SE 21 API: ZipOutputStream"),
  "(block (expression_statement (method_invocation object: (identifier) @o name: (identifier) @a)) @match . (expression_statement (method_invocation object: (identifier) @o2 name: (identifier) @b)) (#eq? @a \"putNextEntry\") (#eq? @b \"closeEntry\") (#eq? @o @o2))",
  jm(["zip.putNextEntry(new ZipEntry(name));", "zip.closeEntry();"], "void f(java.util.zip.ZipOutputStream zip, String name) throws Exception"),
  jm(["zip.putNextEntry(new ZipEntry(name));", "zip.write(data);", "zip.closeEntry();"], "void f(java.util.zip.ZipOutputStream zip, String name, byte[] data) throws Exception"),
  "The entry is opened and closed with nothing written, so the archive gets an empty file: write the data in between.", "S9342",
  sev="minor", mode="ai-confirm", ai="Is this entry meant to hold data (not a directory entry whose name ends in '/')?")
J("SCOPEDVALUE-WHERE-IGNORED", "ScopedValue.where result discarded", (JAPI + "lang/ScopedValue.html", "where", "Java API: ScopedValue"),
  "(expression_statement (method_invocation object: (identifier) @o name: (identifier) @m (#eq? @o \"ScopedValue\") (#eq? @m \"where\"))) @match",
  jm(["ScopedValue.where(USER, user);", "handle();"], "void f(String user)"), jm(["ScopedValue.where(USER, user).run(this::handle);"], "void f(String user)"),
  "where() only builds a carrier; nothing is bound until run()/call() is invoked on it.", "S8432")
J("MULTIPLE-MAIN", "Several main methods in one class", ("https://docs.oracle.com/javase/specs/jls/se21/html/jls-12.html", "main", "JLS 12.1 Java Virtual Machine Startup"),
  "(class_body (method_declaration name: (identifier) @a) (method_declaration name: (identifier) @b) (#eq? @a \"main\") (#eq? @b \"main\")) @match",
  cls("    public static void main(String[] args) {\n        run();\n    }\n\n    static void main() {\n        run();\n    }\n"),
  cls("    public static void main(String[] args) {\n        run();\n    }\n"),
  "With several main candidates it is unclear which one the launcher picks: keep a single entry point.", "S8446",
  cat="maintainability", sev="minor")
J("LOG-AND-RETHROW", "Exception logged and rethrown", ("https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Throwable.html", "chained exception facility", "Java SE 25 API: Throwable"),
  "(catch_clause (catch_formal_parameter name: (identifier) @e) body: (block (expression_statement (method_invocation object: (identifier) @l arguments: (argument_list (_)* (identifier) @a))) (throw_statement (identifier) @t)) (#match? @l \"(?i)^(log|logger)$\") (#eq? @a @e) (#eq? @t @e)) @match",
  jm(["try {", "    load();", "} catch (IOException e) {", "    log.error(\"load failed\", e);", "    throw e;", "}"], "void f() throws IOException"),
  jm(["try {", "    load();", "} catch (IOException e) {", "    throw new UncheckedIOException(\"load failed\", e);", "}"], "void f()"),
  "Logging and rethrowing reports the same failure twice (once here, once by whoever handles it): do one or the other.", "S2139",
  cat="maintainability", kind="best-practice", sev="minor")
J("ASSERTTHROWS-SEVERAL-CALLS", "assertThrows lambda with several calls", ("https://docs.junit.org/current/api/org.junit.jupiter.api/org/junit/jupiter/api/Assertions.html", "assertThrows", "JUnit 5 API: Assertions"),
  "(method_invocation name: (identifier) @m arguments: (argument_list (_) (lambda_expression body: (_) @b)) (#eq? @m \"assertThrows\")) @match",
  jm(["assertThrows(IllegalStateException.class, () -> service.charge(loadOrder(id)));"], "void t(long id)"),
  jm(["Order order = loadOrder(id);", "assertThrows(IllegalStateException.class, () -> service.charge(order));"], "void t(long id)"),
  "With several calls in the lambda the test passes when any of them throws: prepare arguments first and keep one call inside.", "S5778",
  cat="testing", kind="best-practice", sev="minor", filters=[r"cap.has_re:b:\w\s*\([\s\S]*\w\s*\("])

Py("RAISES-SEVERAL-CALLS", "pytest.raises / pytest.warns block with several calls", ("https://docs.pytest.org/en/stable/how-to/assert.html", "pytest.raises", "pytest: Assertions about expected exceptions"),
   "(with_statement (with_clause (with_item value: (call function: (attribute object: (identifier) @p attribute: (identifier) @r)))) body: (block) @b (#eq? @p \"pytest\") (#match? @r \"^(raises|warns)$\")) @match",
   "def test_charge():\n    with pytest.raises(ValueError):\n        charge(load_order(1))\n",
   "def test_charge():\n    order = load_order(1)\n    with pytest.raises(ValueError):\n        charge(order)\n",
   "With several calls in the block the test passes when any of them raises: prepare arguments first and keep one call inside.", "S5778",
   cat="testing", kind="best-practice", sev="minor", filters=[r"cap.has_re:b:\w\s*\([\s\S]*\w\s*\("])
Py("NONE-COMPARISON-CONSTANT", "Literal compared to None", (PYD + "reference/expressions.html", "is not", "Python reference: Comparisons"),
   "(comparison_operator [(list) (dictionary) (string) (integer) (float) (true) (false) (tuple) (set) (list_comprehension) (dictionary_comprehension)] (none)) @match",
   "def f():\n    if [] is None:\n        return 1\n", "def f(items):\n    if items is None:\n        return 1\n",
   "A literal is never None, so this comparison is constant: compare the variable that was meant.", "S5727",
   filters=[r"node.has_re:\s(is|is\s+not|==|!=)\s+None$"])
Py("DICT-LOOKUP-IN-KEY-LOOP", "Dictionary indexed with the loop key", (PYD + "library/stdtypes.html", "dict.items", "Python docs: Mapping types"),
   "(for_statement left: (identifier) @k right: (identifier) @d body: (block) @b) @match",
   "def f(prices):\n    for name in prices:\n        print(name, prices[name])\n", "def f(prices):\n    for name, price in prices.items():\n        print(name, price)\n",
   "Iterating keys and indexing back looks each value up again: iterate items().", "S7517",
   cat="maintainability", kind="best-practice", sev="minor", filters=[r"cap.has_re:b:\b{cap:d}\[{cap:k}\]"])
Py("ITEMS-HALF-UNUSED", "items() iterated with one half discarded", (PYD + "library/stdtypes.html", "dict.items", "Python docs: Mapping types"),
   "((for_statement left: (pattern_list (identifier) @a (identifier) @b) right: (call function: (attribute attribute: (identifier) @m))) @match (#eq? @m \"items\") (#eq? @a \"_\"))\n"
   "((for_statement left: (pattern_list (identifier) @a (identifier) @b) right: (call function: (attribute attribute: (identifier) @m))) @match (#eq? @m \"items\") (#eq? @b \"_\"))",
   "def f(prices):\n    for _, price in prices.items():\n        print(price)\n", "def f(prices):\n    for price in prices.values():\n        print(price)\n",
   "Only keys or only values are used: iterate keys() / the dict itself, or values().", "S7512",
   cat="maintainability", kind="best-practice", sev="minor")
Py("ASYNC-TIMEOUT-PARAMETER", "async function takes a timeout parameter", (PYD + "library/asyncio-task.html", "asyncio.timeout", "Python docs: Coroutines and Tasks"),
   "(function_definition parameters: (parameters [(identifier) @p (default_parameter name: (identifier) @p) (typed_default_parameter name: (identifier) @p) (typed_parameter (identifier) @p)]) (#eq? @p \"timeout\")) @match",
   "async def fetch(url, timeout=10):\n    return await get(url)\n", "async def fetch(url):\n    return await get(url)\n",
   "Callers of a coroutine can bound it with asyncio.timeout(); a timeout parameter duplicates that and is easy to ignore inside.", "S7483",
   cat="maintainability", kind="best-practice", sev="minor", filters=[r"node.has_re:^async\s+def\b"], mode="ai-confirm",
   ai="Is the timeout parameter only used to bound the coroutine itself (not passed on to an API that needs it)?")
Py("ASYNC-BLOCKING-PROCESS-CALL", "Blocking process call inside async def", (PYD + "library/asyncio-subprocess.html", "create_subprocess_exec", "Python docs: asyncio Subprocesses"),
   "(call function: (attribute object: (identifier) @o attribute: (identifier) @m) (#match? @o \"^(os|subprocess)$\") (#match? @m \"^(system|run|call|check_call|check_output|popen|waitpid)$\")) @match",
   "async def build():\n    subprocess.run([\"make\"])\n", "async def build():\n    proc = await asyncio.create_subprocess_exec(\"make\")\n    await proc.wait()\n",
   "The call blocks the event loop until the process ends: use asyncio.create_subprocess_exec or run it in a thread.", "S7489",
   cat="performance", kind="anti-pattern", sev="major", filters=[r"ancestor.has_re:function_definition:^async\s"])
Py("TF-GATHER-VALIDATE-INDICES", "tf.gather called with validate_indices", ("https://www.tensorflow.org/api_docs/python/tf/gather", "validate_indices", "TensorFlow API: tf.gather"),
   "(call function: (attribute object: (identifier) @o attribute: (identifier) @m) arguments: (argument_list (keyword_argument name: (identifier) @k)) (#eq? @o \"tf\") (#eq? @m \"gather\") (#eq? @k \"validate_indices\")) @match",
   "rows = tf.gather(table, ids, validate_indices=True)\n", "rows = tf.gather(table, ids)\n",
   "validate_indices is deprecated and ignored: indices are always checked on CPU. Drop the argument.", "S6925",
   cat="maintainability", kind="deprecation", sev="minor")

Js("THENABLE-OBJECT", "Object or class defines a then member", (MDN + "Global_Objects/Promise", "thenable", "MDN: Promise (thenables)"),
   "(pair key: (property_identifier) @k (#eq? @k \"then\")) @match\n(method_definition name: (property_identifier) @k (#eq? @k \"then\")) @match",
   "const job = { id: 1, then(next) { next(); } };\n", "const job = { id: 1, next(step) { step(); } };\n",
   "An object with then() is treated as a promise by await and Promise.resolve, which calls it unexpectedly: rename the member.", "S7739",
   mode="ai-confirm", ai="Is the object not meant to be a promise-like (thenable) on purpose?")
Js("FOR-EQUALITY-TERMINATION", "for loop ends on an equality test with a non-unit step", (MDN + "Statements/for", "condition", "MDN: for"),
   "(for_statement condition: (_) @c increment: (_) @u) @match",
   "for (let i = 0; i !== n; i += 2) {\n  use(i);\n}\n", "for (let i = 0; i < n; i += 2) {\n  use(i);\n}\n",
   "With a step other than 1 the counter can jump over the end value and the loop never stops: use < or >.", "S888",
   filters=[r"cap.has_re:c:!==?|[^=!<>]==[^=]|^==", r"cap.lacks_re:u:^\s*\w+\s*(\+\+|--)\s*$|^\s*(\+\+|--)\s*\w+\s*$"])
Js("LOOP-COUNTER-ASSIGNED", "for loop counter changed inside the body", (MDN + "Statements/for", "afterthought", "MDN: for"),
   "(for_statement initializer: (lexical_declaration (variable_declarator name: (identifier) @i)) body: (statement_block) @b) @match",
   "for (let i = 0; i < items.length; i++) {\n  if (items[i] === skip) {\n    i++;\n  }\n  use(items[i]);\n}\n",
   "for (let i = 0; i < items.length; i++) {\n  if (items[i] !== skip) {\n    use(items[i]);\n  }\n}\n",
   "Changing the counter in the body hides the real iteration order: use a while loop or adjust the header.", "S2310",
   cat="maintainability", kind="best-practice", sev="minor", filters=[r"cap.has_re:b:\b{cap:i}\s*([-+*/%]?=[^=>]|\+\+|--)|(\+\+|--)\s*{cap:i}\b"])
Js("THIS-IN-FUNCTION-COMPONENT", "this used in a function component", ("https://react.dev/reference/react/Component", "this.props", "React: Component"),
   "(function_declaration name: (identifier) @n body: (statement_block) @b (#match? @n \"^[A-Z]\")) @match",
   "function Greeting(props) {\n  return <h1>Hello {this.props.name}</h1>;\n}\n", "function Greeting({ name }) {\n  return <h1>Hello {name}</h1>;\n}\n",
   "Function components receive props as an argument and have no this: read the parameter instead.", "S6757",
   rlang="jsx", filters=[r"cap.has_re:b:\bthis\.(props|state|setState)\b", r"cap.has_re:b:return\s*\(?\s*<"])
Js("MODULE-KEYWORD", "module used to declare a namespace", ("https://www.typescriptlang.org/docs/handbook/namespaces.html", "namespace", "TypeScript handbook: Namespaces"),
    "(module name: (identifier)) @match", "module Shapes {\n  export const unit = 1;\n}\n", "namespace Shapes {\n  export const unit = 1;\n}\n",
    "module Name { } is the legacy spelling of namespace and reads like an ES module: write namespace.", "typescript:S4156", rlang="typescript",
    cat="maintainability", kind="modernization", sev="minor")
Js("ENUM-MIXED-INITIALIZERS", "Enum mixes initialized and implicit members", ("https://www.typescriptlang.org/docs/handbook/enums.html", "initialized", "TypeScript handbook: Enums"),
    "(enum_body (enum_assignment) (property_identifier)) @match\n(enum_body (property_identifier) (enum_assignment)) @match",
    "enum Level {\n  Low = 1,\n  Mid,\n  High = 10,\n}\n", "enum Level {\n  Low = 1,\n  Mid = 2,\n  High = 10,\n}\n",
    "Implicit members continue from the previous value, so mixing them with explicit ones makes values easy to misread: initialize all or none.", "typescript:S6572", rlang="typescript",
    cat="maintainability", kind="best-practice", sev="minor")
Js("PUBLIC-STATIC-MUTABLE", "Public static field is not readonly", ("https://www.typescriptlang.org/docs/handbook/2/classes.html", "readonly", "TypeScript handbook: Classes"),
    "(public_field_definition) @match", "class Config {\n  static retries = 3;\n}\n", "class Config {\n  static readonly retries = 3;\n}\n",
    "Any code can reassign a public static field, which turns it into global mutable state: make it readonly or private.", "typescript:S1444", rlang="typescript",
    cat="maintainability", kind="best-practice", sev="minor", filters=[r"node.has_re:^(public\s+)?static\s", r"node.lacks_re:\breadonly\b|^\s*(private|protected)\b|#"])

Ph("SET-ACCESSIBLE", "ReflectionProperty/Method setAccessible(true)", (PHPM + "reflectionproperty.setaccessible.php", "no effect", "PHP manual: ReflectionProperty::setAccessible"),
   "(member_call_expression name: (name) @m arguments: (arguments (argument (boolean))) (#eq? @m \"setAccessible\")) @match",
   phf(["$p = new ReflectionProperty($a, 'secret');", "$p->setAccessible(true);", "return $p->getValue($a);"]),
   phf(["return $a->getSecret();"]),
   "Since PHP 8.1 private members are reflectively accessible without it, so the call is noise; reaching into private state is also fragile.", "S3011",
   cat="maintainability", kind="best-practice", sev="minor")
Ph("CATCH-AFTER-THROWABLE", "catch clause after catch (Throwable)", (PHPM + "class.throwable.php", "base interface", "PHP manual: Throwable"),
   "(try_statement (catch_clause type: (type_list (named_type (name) @t))) (catch_clause) @match (#eq? @t \"Throwable\"))",
   phf(["try {", "    run();", "} catch (Throwable $e) {", "    report($e);", "} catch (RuntimeException $e) {", "    retry();", "}"]),
   phf(["try {", "    run();", "} catch (RuntimeException $e) {", "    retry();", "} catch (Throwable $e) {", "    report($e);", "}"]),
   "Throwable already catches everything, so this later clause never runs: put the specific catch first.", "S1045")

K("FIND-COMPARED-TO-NULL", "find { } compared to null", (KTDOC + "collection-elements.html", "find()", "Kotlin docs: Retrieve single elements"),
  "(binary_expression left: (call_expression (navigation_expression (_) (identifier) @m) (annotated_lambda)) (#eq? @m \"find\")) @match", kf(["if (users.find { it.admin } != null) notify()"], "fun f(users: List<User>)"),
  kf(["if (users.any { it.admin }) notify()"], "fun f(users: List<User>)"),
  "find { } != null only asks whether an element exists: any { } (or none { }) says that directly.", "S6528",
  cat="maintainability", kind="best-practice", sev="minor", filters=[r"node.has_re:\.find\s*\{[\s\S]*\}\s*[!=]=\s*null$"])
K("FILE-STATUS-IGNORED", "File operation status ignored", (KTDOC + "java-interop.html", "Java", "Kotlin docs: Calling Java from Kotlin"),
  "(block (call_expression (navigation_expression (_) (identifier) @m) (value_arguments)) @match (#match? @m \"^(delete|mkdir|mkdirs|createNewFile|renameTo|setReadable|setWritable|setExecutable|setLastModified)$\"))",
  kf(["file.delete()", "log(\"done\")"], "fun f(file: java.io.File)"), kf(["if (!file.delete()) error(\"cannot delete $file\")"], "fun f(file: java.io.File)"),
  "java.io.File reports failure only through the returned boolean, which is ignored here: check it or use java.nio.file.Files.", "S899",
  sev="minor")

Hm("FIXME-COMMENT", "FIXME left in markup", (HTMLREF + "Elements/body", "body", "MDN: HTML reference"),
   "(comment) @match", page("<!-- FIXME: wrong link -->\n<main><a href=\"/a\">A</a></main>"), page("<main><a href=\"/a\">A</a></main>"),
   "A FIXME marks known broken markup: fix it before merging or track it in an issue.", "Web:S1134",
   cat="maintainability", filters=[r"node.has_re:\bFIXME\b"])
Hm("HANDLER-ON-STATIC-ELEMENT", "Event handler on a non-interactive element", ("https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/button_role", "tabindex", "MDN: ARIA button role"),
   "(start_tag (tag_name) @t (attribute (attribute_name) @a) (#match? @t \"^(div|span|p|li|section|article|img|td|tr)$\") (#match? @a \"^on(click|keydown|keyup|keypress|mousedown|mouseup)$\")) @match",
   page("<main><div onclick=\"save()\">Save</div></main>"), page("<main><button type=\"button\" onclick=\"save()\">Save</button></main>"),
   "Keyboard and assistive-technology users cannot reach or identify this element: use a button/link, or add a role and keyboard support.", "Web:S6847",
   filters=[r"node.lacks_re:\brole\s*="])
Hm("ROLE-WITHOUT-TABINDEX", "Interactive role on an element that cannot take focus", ("https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/button_role", "tabindex", "MDN: ARIA button role"),
   "(start_tag (tag_name) @t (#match? @t \"^(div|span|li|p|img|section|td)$\")) @match",
   page("<main><div role=\"button\" onclick=\"save()\" onkeydown=\"save()\">Save</div></main>"),
   page("<main><div role=\"button\" tabindex=\"0\" onclick=\"save()\" onkeydown=\"save()\">Save</div></main>"),
   "An element announced as interactive must be reachable with the keyboard: add tabindex=\"0\" or use the native element.", "Web:S6852",
   filters=[r"node.has_re:\brole\s*=\s*[\x22\x27]?(button|link|checkbox|menuitem|tab|switch|radio|option|slider|textbox|combobox|spinbutton)\b", r"node.lacks_re:\btabindex\s*="])
Hm("IDENTICAL-LINK-TEXT-DIFFERENT-HREF", "Same link text points at different URLs", ("https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html", "The purpose of each link can be determined from the link text alone", "Understanding SC 2.4.4 Link Purpose (In Context)"),
   "(start_tag (tag_name) @t (#match? @t \"^(?i)a$\")) @match",
   page("<p><a href=\"/a\">Details</a> and <a href=\"/b\">Details</a></p>"),
   page("<p><a href=\"/a\">Order details</a> and <a href=\"/b\">Account details</a></p>"),
   "Two links share the same text but go to different places, so a links list cannot tell them apart: make the text describe each destination.",
   "Web:LinksIdenticalTextsDifferentTargetsCheck",
   filters=["markup.dup_link_text"], cat="accessibility", kind="best-practice", sev="minor",
   quote="The purpose of each link can be determined from the link text alone.")
Hm("OBJECT-AND-EMBED", "Flash-style object wrapping embed", ("https://html.spec.whatwg.org/multipage/iframe-embed-object.html", "The embed element provides an integration point for an external application or interactive content", "HTML Living Standard: the embed element"),
   "(element (start_tag (tag_name) @t) (element (start_tag (tag_name) @e)) (#match? @t \"^(?i)object$\") (#match? @e \"^(?i)embed$\")) @match",
   page("<object data=\"app.swf\" type=\"application/x-shockwave-flash\"><embed src=\"app.swf\"></object>"),
   page("<video src=\"app.mp4\" controls></video>"),
   "Nesting embed inside object was the Flash fallback pattern; both elements are the wrong tool for media or apps now: use video/audio or a documented plugin API.",
   "Web:FlashUsesBothObjectAndEmbedCheck", cat="maintainability", kind="deprecation", sev="minor",
   quote="The embed element provides an integration point for an external application or interactive content.")
Js("ROLE-WITHOUT-TABINDEX", "Interactive role on a non-focusable JSX element", ("https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/button_role", "tabindex", "MDN: ARIA button role"),
   "([(jsx_self_closing_element name: (identifier) @t) (jsx_opening_element name: (identifier) @t)] @match (#match? @t \"^(div|span|li|p|img|section|td)$\"))",
   "const C = ({ save }) => <div role=\"button\" onClick={save} onKeyDown={save}>Save</div>;\n",
   "const C = ({ save }) => <div role=\"button\" tabIndex={0} onClick={save} onKeyDown={save}>Save</div>;\n",
   "An element announced as interactive must be reachable with the keyboard: add tabIndex={0} or use a native button/link.", "S6852",
   cat="accessibility", kind="best-practice", sev="minor", rlang="jsx",
   filters=[r"node.has_re:\brole\s*=\s*[\x22'{]?(button|link|checkbox|menuitem|tab|switch|radio|option|slider|textbox|combobox|spinbutton)\b",
            r"node.lacks_re:\btabIndex\s*="])
Js("OBJECT-DEFAULT-PARAM", "Object or array used as a default parameter", (MDN + "Functions/Default_parameters", "Default function parameters allow named parameters to be initialized with default values if no value or undefined is passed", "MDN: Default parameters"),
   "((formal_parameters) @match (#match? @match \"=\\\\s*[\\\\[\\\\{]\"))",
   "function load(opts = {}) {\n  return opts.url;\n}\n",
   "function load(opts) {\n  const url = (opts ?? {}).url;\n  return url;\n}\n",
   "A default {} or [] is a shared mutable value if something ever writes to it; default to undefined and substitute a fresh object in the body.",
   "S7737", cat="correctness", sev="minor",
   quote="Default function parameters allow named parameters to be initialized with default values if no value or undefined is passed.")
Js("INDEXOF-INCLUDES", "indexOf compared with -1 instead of includes()", (MDN + "Global_Objects/Array/includes", "Whether the array contains the value", "MDN: Array.prototype.includes"),
   "(binary_expression left: (call_expression function: (member_expression property: (property_identifier) @m)) right: (unary_expression argument: (number) @n) (#eq? @m \"indexOf\") (#eq? @n \"1\")) @match",
   "if (tags.indexOf('a') !== -1) {\n  hit();\n}\n", "if (tags.includes('a')) {\n  hit();\n}\n",
   "indexOf(...) !== -1 is a membership test: includes() states that and does not confuse 0 with missing.", "S7776",
   cat="maintainability", kind="best-practice", sev="info", quote="The includes() method determines whether an array includes a certain value among its entries, returning true or false as appropriate.")
Js("CONSECUTIVE-PUSH", "Consecutive push() calls on the same array", (MDN + "Global_Objects/Array/push", "The push() method adds the specified elements to the end of an array", "MDN: Array.prototype.push"),
   "((expression_statement (call_expression function: (member_expression object: (identifier) @a property: (property_identifier) @p))) . (expression_statement (call_expression function: (member_expression object: (identifier) @b property: (property_identifier) @q))) @match (#eq? @a @b) (#eq? @p \"push\") (#eq? @q \"push\"))",
   "items.push(a);\nitems.push(b);\n", "items.push(a, b);\n",
   "push accepts any number of arguments: consecutive push calls on the same array can be one call.", "S7778",
   cat="maintainability", kind="best-practice", sev="info", quote="The push() method of Array instances adds the specified elements to the end of an array and returns the new length of the array.")
Js("BOOLEAN-SELECTOR-PARAM", "Leading boolean parameter selects behaviour", (MDN + "Functions", "parameters", "MDN: Functions"),
   "((function_declaration parameters: (formal_parameters) @ps) @match (#match? @ps \"^\\\\(\\\\s*(is|has|should|can|enable|use)[A-Z]\") (#match? @ps \",\"))",
   "function save(isDraft, body) {\n  if (isDraft) queue(body); else publish(body);\n}\n",
   "function saveDraft(body) {\n  queue(body);\n}\nfunction publish(body) {\n  send(body);\n}\n",
   "A boolean flag to pick one of two behaviours hides two functions behind one name: split them, or take an options object.",
   "S2301", cat="maintainability", kind="best-practice", sev="info", mode="ai-confirm",
   ai="Does this boolean choose between two different behaviours (rather than a true/false field that is stored or forwarded)?",
   quote="A JavaScript function can have any number of parameters.")
Js("PROTOTYPE-POLYFILL", "Built-in prototype patched in application code", (MDN + "Global_Objects/Array/prototype", "Warning: Changing the Array prototype", "MDN: Array.prototype"),
   "((assignment_expression left: (member_expression object: (member_expression object: (identifier) @o property: (property_identifier) @p))) @match (#match? @o \"^(Array|String|Object|Number|Promise|Map|Set|Symbol)$\") (#eq? @p \"prototype\"))",
   "Array.prototype.flat = function flat() { return [].concat(...this); };\n",
   "const flat = (xs) => xs.flat();\n",
   "Patching a built-in prototype collides with the platform and with other polyfills: use the native method or a local helper.",
   "S7742", cat="maintainability", kind="best-practice", sev="minor",
   quote="Warning: Changing one of the built-in object prototypes is considered bad practice.")
Js("PROCESS-BINDING", "process.binding() used (Node.js internal)", ("https://nodejs.org/api/process.html#processbindingname", "process.binding(name)", "Node.js process.binding"),
   "((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p)) @match (#eq? @o \"process\") (#eq? @p \"binding\"))",
   "const spawn = process.binding('spawn_sync');\n",
   "import { spawnSync } from 'node:child_process';\n",
   "process.binding loads undocumented internals that change between Node releases: use the public node: API.",
   "S6627", cat="maintainability", kind="deprecation", sev="major",
   quote="The process.binding() method provides access to the internal binding modules of Node.js. Using process.binding() is not recommended.")
Js("INNER-FUNCTION-DECLARATION", "Function declaration inside a block", (MDN + "Statements/function", "Block-level function declarations", "MDN: function statement"),
   "(if_statement consequence: [(function_declaration) (statement_block (function_declaration))] @match)\n(for_statement body: [(function_declaration) (statement_block (function_declaration))] @match)\n(while_statement body: [(function_declaration) (statement_block (function_declaration))] @match)",
   "if (ready) {\n  function run() { go(); }\n  run();\n}\n",
   "if (ready) {\n  const run = () => { go(); };\n  run();\n}\n",
   "A function declaration in a block does not hoist the way a script-level declaration does: use a const function expression.",
   "S7721", cat="maintainability", kind="best-practice", sev="info",
   quote="Starting with ECMAScript 2015, nested function declarations are scoped to the block in which they are defined.")

# WCAG 2.x success criteria checked by the accessibility rules above ("bp" = best practice only:
# no success criterion fails on its own, tagged a11y-best-practice).
WCAG_OF = {
    "ACCESSKEY-ATTRIBUTE": "bp", "AUTOFOCUS-ATTRIBUTE": "bp", "ANCHOR-AS-BUTTON": ["4.1.2"], "ARIA-HIDDEN-FOCUSABLE": ["4.1.2"],
    "ARIA-ROLE-ATTRIBUTE": ["4.1.2"], "AUTOPLAY-MEDIA": ["1.4.2"], "CLICK-WITHOUT-KEYBOARD": ["2.1.1"],
    "CLICK-WITHOUT-KEY-HANDLER": ["2.1.1"], "EMPTY-ANCHOR": ["2.4.4", "4.1.2"], "ANCHOR-WITHOUT-CONTENT": ["2.4.4", "4.1.2"],
    "FRAME-WITHOUT-TITLE": ["4.1.2"], "IFRAME-WITHOUT-TITLE": ["4.1.2"], "HANDLER-ON-STATIC-ELEMENT": ["4.1.2"],
    "IMG-WITHOUT-ALT": ["1.1.1"], "LEGEND-OUTSIDE-FIELDSET": ["1.3.1"], "LI-OUTSIDE-LIST": ["1.3.1"],
    "META-REFRESH": ["2.2.1", "3.2.5"], "OBJECT-WITHOUT-FALLBACK": ["1.1.1"], "PAGE-WITHOUT-TITLE": ["2.4.2"],
    "POSITIVE-TABINDEX": ["2.4.3"], "ROLE-WITHOUT-TABINDEX": ["2.1.1"],
    "IDENTICAL-LINK-TEXT-DIFFERENT-HREF": ["2.4.4"], "OBJECT-AND-EMBED": "bp", "SCOPE-ON-NON-TH": ["1.3.1"],
    "TH-WITHOUT-SCOPE-OR-ID": ["1.3.1"], "VIEWPORT-BLOCKS-ZOOM": ["1.4.4"], "HTML-WITHOUT-LANG": ["3.1.1"], "WITHOUT-LANG": ["3.1.1"],
    "VIDEO-WITHOUT-CAPTIONS": ["1.2.2"],
}
# ---- type-aware rules (built-in resolver: internal/types; type.* filters) ------------------------
# Each fires only when the receiver/operand types are resolved from what the file declares
# (literals, declared locals/params/fields, constructor calls, declared return types); an
# unresolved type never matches, so these are precise but deliberately incomplete.
JATOMIC = JAPI + "util/concurrent/atomic/AtomicInteger.html"
J("ATOMIC-EQUALS", "equals() on an Atomic* value", (JATOMIC, "cannot be used as a replacement for an Integer", "Java SE 21 API: AtomicInteger"),
  "(method_invocation object: (_) @o name: (identifier) @m arguments: (argument_list (_)) (#eq? @m \"equals\")) @match",
  jm(["if (hits.equals(limit)) {", "    stop();", "}"], "void f(AtomicInteger hits, AtomicInteger limit)"),
  jm(["if (hits.get() == limit.get()) {", "    stop();", "}"], "void f(AtomicInteger hits, AtomicInteger limit)"),
  "Atomic* classes do not override equals(), so this compares identities, not values: compare get() results.", "S2204",
  filters=[r"type.is:o:Atomic(Integer|Long|Boolean|Reference)"],
  fp=[jm(["if (hits.equals(limit)) {", "    stop();", "}"], "void f(Counter hits, Counter limit)")])
J("URL-EQUALS-HASHCODE", "URL.equals()/hashCode() called", (JAPI.replace("java.base/java/", "java.base/java/") + "net/URL.html", "Since hosts comparison requires name resolution, this operation is a blocking operation", "Java SE 21 API: URL"),
  "(method_invocation object: (_) @o name: (identifier) @m (#match? @m \"^(equals|hashCode)$\")) @match",
  jm(["return home.equals(other);"], "boolean same(URL home, URL other)").replace("void", "boolean"),
  jm(["return home.toURI().equals(other.toURI());"], "boolean same(URL home, URL other) throws Exception"),
  "URL.equals and hashCode resolve host names over the network (slow, blocking, and different results offline): compare URI objects instead.", "S2112",
  filters=[r"type.is:o:URL"], sev="major", cat="performance",
  fp=[jm(["return home.equals(other);"], "boolean same(URI home, URI other)")])
J("SYNC-ON-VALUE-BASED", "synchronized on a boxed or value-based object", (JAPI + "lang/doc-files/ValueBased.html", "synchronization", "Java SE 21 API: Value-based Classes"),
  "(synchronized_statement (parenthesized_expression (_) @l)) @match",
  cls("    private final Integer lock = 0;\n    void f() {\n        synchronized (lock) {\n            work();\n        }\n    }\n"),
  cls("    private final Object lock = new Object();\n    void f() {\n        synchronized (lock) {\n            work();\n        }\n    }\n"),
  "Boxed numbers, Boolean, Optional and java.time values can be cached and shared, so unrelated code may lock the same instance (deadlocks, contention): lock a private new Object().", ["S1860", "S3436"],
  filters=[r"type.is:l:Integer|Long|Short|Byte|Character|Boolean|Double|Float|Optional|LocalDate|LocalTime|LocalDateTime|Instant|Duration|ZonedDateTime|OffsetDateTime"])
J("STRING-EQUALS-BUILDER", "String.equals() given a StringBuilder/StringBuffer", (JAPI + "lang/String.html", "Compares this string to the specified CharSequence", "Java SE 21 API: String.contentEquals"),
  "(method_invocation object: (_) @o name: (identifier) @m arguments: (argument_list . (_) @a .) (#eq? @m \"equals\")) @match",
  jm(["return name.equals(buf);"], "boolean same(String name, StringBuilder buf)").replace("void", "boolean"),
  jm(["return name.contentEquals(buf);"], "boolean same(String name, StringBuilder buf)"),
  "A String is never equal to a StringBuilder/StringBuffer, so this is always false: use contentEquals() or compare buf.toString().", "S9394",
  filters=[r"type.is:o:String", r"type.is:a:StringBuilder|StringBuffer|CharBuffer"])
J("WAIT-ON-CONDITION", "Object.wait()/notify() on a Condition", (JAPI + "util/concurrent/locks/Condition.html", "Condition instances are just normal objects", "Java SE 21 API: Condition"),
  "(method_invocation object: (_) @o name: (identifier) @m (#match? @m \"^(wait|notify|notifyAll)$\")) @match",
  jm(["ready.wait();"], "void f(Condition ready) throws InterruptedException"), jm(["ready.await();"], "void f(Condition ready) throws InterruptedException"),
  "wait()/notify() use the Condition object's own monitor, not the lock it belongs to: call await()/signal() instead.", "S1844",
  filters=[r"type.is:o:Condition"])
J("BOXED-TOSTRING", "toString() on a boxed primitive", (JAPI + "lang/String.html", "if the argument is null, then a string equal to \"null\"", "Java SE 21 API: String.valueOf"),
  "(method_invocation object: (_) @o name: (identifier) @m arguments: (argument_list) @a (#eq? @m \"toString\") (#eq? @a \"()\")) @match",
  jm(["return n.toString();"], "String id(Integer n)").replace("void", "String"),
  jm(["return String.valueOf(n);"], "String id(Integer n)").replace("void", "String"),
  "toString() on a boxed value throws if the wrapper is null: use String.valueOf, which yields \"null\".", "S1158",
  filters=[r"type.is:o:Integer|Long|Short|Byte|Float|Double|Boolean|Character"],
  fp=[jm(["return n.toString();"], "String id(Name n)").replace("void", "String")])
J("BOXED-BOOLEAN-CONDITION", "Boxed Boolean used as a condition", ("https://docs.oracle.com/javase/specs/jls/se21/html/jls-5.html", "If r is null, unboxing conversion throws a NullPointerException", "JLS 5.1.8 Unboxing Conversion"),
  "[(if_statement condition: (parenthesized_expression (_) @c)) (while_statement condition: (parenthesized_expression (_) @c)) (ternary_expression condition: (_) @c)] @match",
  jm(["if (ready) {", "    run();", "}"], "void f(Boolean ready)"),
  jm(["if (Boolean.TRUE.equals(ready)) {", "    run();", "}"], "void f(Boolean ready)"),
  "Unboxing a null Boolean in a condition throws NullPointerException: compare with Boolean.TRUE or handle null.", "S5411",
  filters=[r"type.is:c:Boolean", r"cap.lacks_re:c:^Boolean\.(TRUE|FALSE)$"],
  fp=[jm(["if (ready) {", "    run();", "}"], "void f(boolean ready)")])
J("REDUNDANT-CAST", "Cast to a type the expression already has", ("https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html", "A cast expression converts, at run time, a value of one numeric type", "JLS 15.16 Cast Expressions"),
  "(cast_expression type: (_) @t value: (_) @v) @match",
  jm(["String t = (String) name;"], "void f(String name)"),
  jm(["String t = name;"], "void f(String name)"),
  "The value is already that type, so the cast does nothing: drop it.", "S1905",
  filters=["type.eq_text:v:t"],
  fp=[jm(["String t = (String) name;"], "void f(Object name)")],
  quote="A cast expression converts, at run time, a value of one numeric type to a similar value of another numeric type")
J("BOXED-PARSE", "valueOf used where a primitive parse is enough", (JAPI + "lang/Integer.html", "Parses the string argument as a signed decimal integer", "Java SE 21 API: Integer.parseInt"),
  "(local_variable_declaration type: [(integral_type) (floating_point_type) (boolean_type)] (variable_declarator value: (method_invocation object: (identifier) @c name: (identifier) @m (#eq? @m \"valueOf\") (#match? @c \"^(Integer|Long|Short|Byte|Double|Float|Boolean)$\")))) @match",
  jm(['int n = Integer.valueOf(s);'], "void f(String s)"),
  jm(['int n = Integer.parseInt(s);'], "void f(String s)"),
  "valueOf boxes the result and then unboxes it into the primitive: parseInt/parseLong/parseBoolean skip the wrapper.", "S2130",
  quote="Parses the string argument as a signed decimal integer")

PYEXPR = PYD + "reference/expressions.html"
PYEXC = (PYD + "library/exceptions.html", "Raised when an operation or function is applied to an object of inappropriate type", "Python docs: TypeError")
Py("IDENTITY-DISSIMILAR-TYPES", "is / is not between values of different built-in types", (PYEXPR, "The operators is and is not test for an object's identity", "Python reference: Identity comparisons"),
   "(comparison_operator . (_) @a . (_) @b .) @match",
   "def f(code: int):\n    label = \"200\"\n    return code is label\n", "def f(code: int):\n    label = \"200\"\n    return str(code) == label\n",
   "Two values of different built-in types are never the same object, so this is constant: compare values with ==, converting first.", "S3403",
   filters=[r"node.has_re:\sis\s", "type.differ:a:b"])
Py("INCOMPATIBLE-ADDITION", "+ between incompatible built-in types", PYEXC,
   "(binary_operator left: (_) @a operator: \"+\" right: (_) @b) @match",
   "def label(count: int):\n    return \"items: \" + count\n", "def label(count: int):\n    return \"items: \" + str(count)\n",
   "Adding these types raises TypeError at run time (for example str + int): convert one side first.", "S5607",
   filters=["type.differ:a:b"])
Py("IN-NON-CONTAINER", "in / not in against a number or bool", (PYEXPR, "For user-defined classes which do not define __contains__()", "Python reference: Membership test operations"),
   "(comparison_operator . (_) . (_) @r .) @match",
   "def f(x, limit: int):\n    return x in limit\n", "def f(x, limit: int):\n    return x < limit\n",
   "Numbers and bools are not containers, so the membership test raises TypeError: test against a collection or use a comparison.", "S5642",
   filters=[r"node.has_re:\sin\s", r"type.is:r:int|float|bool|complex"])
Py("CALL-NON-CALLABLE", "Calling a value of a built-in non-callable type", PYEXC,
   "(call function: (identifier) @f) @match",
   "def f():\n    total = 0\n    return total()\n", "def f():\n    total = 0\n    return total\n",
   "This name holds a str/number/collection, so calling it raises TypeError: drop the parentheses or call the intended function.", "S5756",
   filters=[r"type.is:f:str|int|float|bool|list|dict|tuple|set|bytes|complex|frozenset"])
Py("ANNOTATION-MISMATCH", "Assigned value does not match the variable's annotation", ("https://typing.python.org/en/latest/spec/annotations.html", "type annotation", "Python typing spec: Annotations"),
   "(assignment left: (identifier) type: (type) @t right: (_) @v) @match",
   "retries: int = \"3\"\n", "retries: int = 3\n",
   "The value's type contradicts the annotation, so readers and type checkers are misled and later arithmetic or calls fail: fix the value or the annotation.", "S5890",
   filters=["type.vs_text:v:t"])
Py("RETURN-HINT-MISMATCH", "Returned value does not match the return annotation", ("https://typing.python.org/en/latest/spec/annotations.html", "type annotation", "Python typing spec: Annotations"),
   "(function_definition return_type: (type) @t body: (block (return_statement (_) @v) @match))",
   "def port() -> int:\n    return \"8080\"\n", "def port() -> int:\n    return 8080\n",
   "The returned value's type contradicts the declared return type, so callers relying on the hint break: return the declared type or fix the hint.", "S5886",
   filters=["type.vs_text:v:t"])

Js("STRICT-EQUALITY-DISSIMILAR-TYPES", "=== / !== between values of different types", (MDN + "Operators/Strict_equality", "If the operands are of different types, return false", "MDN: Strict equality (===)"),
   "(binary_expression left: (_) @a operator: [\"===\" \"!==\"] right: (_) @b) @match",
   "function isOk(code) {\n  const expected = 200;\n  const got = String(code);\n  const text = \"200\";\n  return expected === text;\n}\n",
   "function isOk(code) {\n  const expected = 200;\n  return Number(code) === expected;\n}\n",
   "The operands have different types, so === is always false (!== always true): convert one side first.", "S3403",
   filters=["type.differ:a:b"])
Js("IN-ON-PRIMITIVE", "in operator applied to a primitive", (MDN + "Operators/in", "Thrown if object is not an object", "MDN: in"),
   "(binary_expression operator: \"in\" right: (_) @r) @match",
   "function has(key) {\n  const name = \"config\";\n  return key in name;\n}\n", "function has(key) {\n  const config = { a: 1 };\n  return key in config;\n}\n",
   "in on a string, number or boolean throws TypeError: test a property of an object (or use includes() for strings).", "S3785",
   filters=[r"type.is:r:string|number|boolean"])
Js("AWAIT-NON-PROMISE", "await applied to a plain value", (MDN + "Operators/await", "If the value is not a Promise", "MDN: await"),
   "(await_expression (_) @e) @match",
   "async function f() {\n  const n = 3;\n  return await n;\n}\n", "async function f() {\n  const n = 3;\n  return n;\n}\n",
   "The awaited value is not a promise (string/number/boolean), so await only delays the code by a tick: remove it or await the real async call.", "S4123",
   filters=[r"type.is:e:string|number|boolean"], sev="minor", kind="best-practice", cat="maintainability")
Js("VOID-RESULT-USED", "Result of a void function is used", ("https://www.typescriptlang.org/docs/handbook/2/functions.html", "void represents the return value of functions which don't return a value", "TypeScript handbook: Functions"),
   "(variable_declarator value: (call_expression) @c) @match",
   "function log(msg: string): void {\n  console.log(msg);\n}\nconst r = log(\"x\");\n", "function log(msg: string): void {\n  console.log(msg);\n}\nlog(\"x\");\n",
   "The function is declared to return nothing, so this variable is always undefined: call it as a statement.", "S3699",
   filters=[r"type.is:c:void"], rlang="typescript")
Js("FOR-OF-PRIMITIVE", "for...of over a number or boolean", (MDN + "Statements/for...of", "The for...of statement executes a loop that operates on a sequence of values sourced from an iterable object", "MDN: for...of"),
   "(for_in_statement operator: \"of\" right: (_) @r) @match",
   "function f() {\n  const n = 3;\n  for (const x of n) {\n    use(x);\n  }\n}\n", "function f() {\n  const n = [3];\n  for (const x of n) {\n    use(x);\n  }\n}\n",
   "for...of needs an iterable; a number or boolean throws TypeError: iterate an array, string, or other iterable.", "S4138",
   filters=[r"type.is:r:number|boolean"],
   fp=["function f() {\n  const n = \"abc\";\n  for (const x of n) {\n    use(x);\n  }\n}\n"])
Js("CALL-NON-CALLABLE", "Calling a value of a primitive or array type", (MDN + "Global_Objects/TypeError", "The TypeError object represents an error when an operation could not be performed", "MDN: TypeError"),
   "(call_expression function: (identifier) @f) @match",
   "function f() {\n  const total = 0;\n  return total();\n}\n", "function f() {\n  const total = 0;\n  return total;\n}\n",
   "This name holds a string, number, boolean or array, so calling it throws TypeError: drop the parentheses or call the intended function.", "S7757",
   filters=[r"type.is:f:string|number|boolean|Array"])
Py("AWAIT-NON-AWAITABLE", "await applied to a plain value", (PYEXPR, "Suspend the execution of coroutine on an awaitable object", "Python reference: Await expression"),
   "(await (_) @e) @match",
   "async def f():\n    n = 3\n    return await n\n", "async def f():\n    n = 3\n    return n\n",
   "The awaited value is a str/number/collection, not an awaitable, so this raises TypeError: drop await or await a real coroutine.", "S3862",
   filters=[r"type.is:e:str|int|float|bool|list|dict|tuple|set|bytes"],
   fp=["async def f():\n    n = fetch()\n    return await n\n"],
   quote="Suspend the execution of coroutine on an awaitable object.")
Py("SUBSCRIPT-NON-CONTAINER", "Subscript on a number or bool", (PYEXPR, "__getitem__() or __class_getitem__() special method", "Python reference: Subscriptions"),
   "(subscript value: (_) @v) @match",
   "def f(n: int):\n    return n[0]\n", "def f(n: int):\n    return n\n",
   "Numbers and bools are not subscriptable, so this raises TypeError: index a sequence or mapping.", "S5644",
   filters=[r"type.is:v:int|float|bool|complex"],
   fp=["def f(n: list):\n    return n[0]\n", "def f(n: str):\n    return n[0]\n"],
   quote="__getitem__() or __class_getitem__() special method")


# ---- Sonar backlog batch 1 (syntax + built-in types) ----------------------------------------------
JTUT = "https://docs.oracle.com/javase/tutorial/essential/concurrency/"
J("DOUBLE-CHECKED-LOCKING", "Double-checked locking on a non-volatile field", (JTUT + "atomic.html", "Using volatile variables reduces the risk of memory consistency errors", "Java tutorial: Atomic Access"),
  "((if_statement condition: (parenthesized_expression (binary_expression left: (identifier) @f right: (null_literal))) consequence: (block (synchronized_statement body: (block (if_statement condition: (parenthesized_expression (binary_expression left: (identifier) @f2 right: (null_literal)))))))) @match (#eq? @f @f2))",
  cls("    private static Config cfg;\n    static Config get() {\n        if (cfg == null) {\n            synchronized (A.class) {\n                if (cfg == null) {\n                    cfg = load();\n                }\n            }\n        }\n        return cfg;\n    }\n"),
  cls("    private static volatile Config cfg;\n    static Config get() {\n        if (cfg == null) {\n            synchronized (A.class) {\n                if (cfg == null) {\n                    cfg = load();\n                }\n            }\n        }\n        return cfg;\n    }\n"),
  "Without volatile, another thread can see the field set before the object is fully built: make the field volatile or use a holder class / eager init.", "S2168",
  filters=[r"node.has_re:==\s*null", r"ancestor.has_re:class_body:(?m)^\s*(?:(?:private|protected|public|static|transient)\s+)+[\w<>\[\], .?]+\s+{cap:f}\s*[;=]",
           r"ancestor.lacks_re:class_body:\bvolatile\b[^;=(]*\b{cap:f}\s*[;=]"])
J("SYNC-ON-NON-FINAL-FIELD", "synchronized on a non-final field", (JTUT + "locksync.html", "Every object has an intrinsic lock associated with it", "Java tutorial: Intrinsic Locks and Synchronization"),
  "(synchronized_statement (parenthesized_expression [(identifier) @l (field_access object: (this) field: (identifier) @l)])) @match",
  cls("    private Object lock = new Object();\n    void f() {\n        synchronized (lock) {\n            work();\n        }\n    }\n"),
  cls("    private final Object lock = new Object();\n    void f() {\n        synchronized (lock) {\n            work();\n        }\n    }\n"),
  "If the field is reassigned, threads lock different objects and the block is no longer exclusive: lock a private final field.", "S2445",
  filters=[r"ancestor.has_re:class_body:(?m)^\s*(?:(?:private|protected|public|static|transient|volatile)\s+)+[\w<>\[\], .?]+\s+{cap:l}\s*[;=]",
           r"ancestor.lacks_re:class_body:(?m)^\s*(?:\w+\s+)*final\s+(?:\w+\s+)*[\w<>\[\], .?]+\s+{cap:l}\s*[;=]"])
J("PREPARED-STATEMENT-PARAM-SET-TWICE", "PreparedStatement parameter set twice in a row", (JAPISQL + "PreparedStatement.html", "the first parameter is 1, the second is 2", "Java SE 21 API: PreparedStatement"),
  "(block (expression_statement (method_invocation object: (identifier) @o name: (identifier) @n arguments: (argument_list . (decimal_integer_literal) @k))) @match . (expression_statement (method_invocation object: (identifier) @o2 name: (identifier) @n2 arguments: (argument_list . (decimal_integer_literal) @k2))) (#eq? @o @o2) (#eq? @k @k2) (#match? @n \"^set[A-Z]\\\\w*$\") (#match? @n2 \"^set[A-Z]\\\\w*$\"))",
  jm(["ps.setString(1, name);", "ps.setInt(1, age);"], "void f(PreparedStatement ps, String name, int age) throws SQLException"),
  jm(["ps.setString(1, name);", "ps.setInt(2, age);"], "void f(PreparedStatement ps, String name, int age) throws SQLException"),
  "The second call overwrites the first value of the same parameter index, so one bind is lost: check the indexes.", "S6909",
  filters=[r"type.is:o:PreparedStatement|CallableStatement"])
TZ_OK = (r'^"(GMT|UTC|UT|GMT[+-]\d{1,2}(:?\d{2})?|[A-Z][A-Za-z_]*(/[A-Za-z0-9_+-]+){1,2}|EST|MST|HST|ACT|AET|AGT|ART|AST|BET|BST|CAT|CNT|CST|CTT|EAT|ECT|IET|IST|JST|MIT|NET|NST|PLT|PNT|PRT|PST|SST|VST|'
         r'EST5EDT|CST6CDT|MST7MDT|PST8PDT|CET|EET|MET|WET|UCT|Zulu|Universal|Greenwich|GB|GB-Eire|NZ|NZ-CHAT|PRC|ROK|ROC|Japan|Cuba|Egypt|Eire|Iran|Israel|Jamaica|Libya|Navajo|Poland|Portugal|Singapore|Turkey|W-SU|Hongkong|Iceland|Kwajalein|GMT0)"$')
J("TIMEZONE-INVALID-ID", "TimeZone.getTimeZone() with an ID it does not know", (JAPI + "util/TimeZone.html", "or the GMT zone if the given ID cannot be understood", "Java SE 21 API: TimeZone"),
  "(method_invocation object: (identifier) @c name: (identifier) @m arguments: (argument_list . (string_literal) @s .) (#eq? @c \"TimeZone\") (#eq? @m \"getTimeZone\")) @match",
  jm(['TimeZone tz = TimeZone.getTimeZone("UTC+3");']), jm(['TimeZone tz = TimeZone.getTimeZone("GMT+3");', 'TimeZone paris = TimeZone.getTimeZone("Europe/Paris");']),
  "Unknown IDs silently become GMT, so times are off without any error: use a region ID (Europe/Paris), GMT+hh:mm, or ZoneId.of(), which throws.", "S9363",
  filters=["cap.lacks_re:s:" + TZ_OK])
JSTREAMS = "InputStream|FileInputStream|BufferedInputStream|DataInputStream|ObjectInputStream|ByteArrayInputStream|PushbackInputStream|SequenceInputStream|Reader|InputStreamReader|BufferedReader|FileReader|StringReader|CharArrayReader|RandomAccessFile"
J("STREAM-READ-RESULT-IGNORED", "Result of InputStream/Reader read() or skip() ignored", (JAPI + "io/InputStream.html", "the total number of bytes read into the buffer", "Java SE 21 API: InputStream"),
  "(expression_statement (method_invocation object: (_) @o name: (identifier) @m arguments: (argument_list (_))) (#match? @m \"^(read|skip)$\")) @match",
  jm(["in.read(buf);", "use(buf);"], "void f(InputStream in, byte[] buf) throws IOException"),
  jm(["in.readNBytes(buf, 0, buf.length);", "use(buf);"], "void f(InputStream in, byte[] buf) throws IOException"),
  "read()/skip() may process fewer bytes than asked; ignoring the count leaves part of the buffer stale: loop on the return value or use readNBytes()/readFully().", "S2674",
  filters=[r"type.is:o:" + JSTREAMS])
J("WAIT-WITH-SEVERAL-LOCKS", "wait() while holding more than one lock", (JAPI + "lang/Object.html", "remain locked while the thread waits", "Java SE 21 API: Object.wait"),
  "(synchronized_statement body: (block (synchronized_statement body: (block) @inner))) @match",
  cls("    void f(Object a, Object b) throws InterruptedException {\n        synchronized (a) {\n            synchronized (b) {\n                b.wait();\n            }\n        }\n    }\n"),
  cls("    void f(Object b) throws InterruptedException {\n        synchronized (b) {\n            b.wait();\n        }\n    }\n"),
  "wait() releases only the innermost monitor; the outer lock stays held while waiting, which easily deadlocks: wait with a single lock held.", "S3046",
  filters=[r"cap.has_re:inner:\.wait\s*\("])
J("REFLECTION-ON-SOURCE-ANNOTATION", "Reflection looks for an annotation that is not kept at run time", (JAPI + "lang/annotation/RetentionPolicy.html", "Annotations are to be discarded by the compiler", "Java SE 21 API: RetentionPolicy"),
  "(method_invocation name: (identifier) @m arguments: (argument_list . (class_literal (type_identifier) @a) .) (#match? @m \"^(isAnnotationPresent|getAnnotation|getDeclaredAnnotation|getAnnotationsByType)$\") (#match? @a \"^(Override|SuppressWarnings)$\")) @match",
  jm(["boolean o = m.isAnnotationPresent(Override.class);"], "void f(Method m)"), jm(["boolean d = m.isAnnotationPresent(Deprecated.class);"], "void f(Method m)"),
  "@Override and @SuppressWarnings have SOURCE retention, so reflection never sees them and this check is always false.", "S2109")

Js("ARRAY-STRING-INDEX", "Array given a non-numeric string index", (MDN + "Global_Objects/Array", "Array elements are object properties", "MDN: Array"),
   "(assignment_expression left: (subscript_expression object: (_) @o index: (string) @i)) @match",
   "function f() {\n  const list = [];\n  list[\"total\"] = 3;\n  return list;\n}\n", "function f() {\n  const totals = {};\n  totals[\"total\"] = 3;\n  return totals;\n}\n",
   "A string key on an array adds a plain property, not an element: length, iteration and JSON ignore it. Use an object or Map.", "S3579",
   filters=[r"type.is:o:Array", r"cap.lacks_re:i:^[\x22'`]\d+[\x22'`]$"])
Js("ASYNC-WITHOUT-AWAIT", "async function that never awaits", (MDN + "Statements/async_function", "Async functions always return a promise", "MDN: async function"),
   "(program (function_declaration body: (statement_block) @b) @match)",
   "async function total(items: number[]) {\n  return items.reduce((a, b) => a + b, 0);\n}\n", "function total(items: number[]) {\n  return items.reduce((a, b) => a + b, 0);\n}\n",
   "Nothing in this async function awaits, so async only wraps the result in a promise and forces callers to await: drop async or await the real asynchronous work.", "typescript:S7503",
   filters=[r"node.has_re:^async\s+function", r"cap.lacks_re:b:\bawait\b"], rlang="typescript", sev="minor", kind="best-practice", cat="maintainability")
Py("ASYNC-WITHOUT-AWAIT", "async def that never awaits", (PYD + "reference/compound_stmts.html", "Coroutine function definition", "Python reference: Coroutine function definition"),
   "(module (function_definition body: (block) @b) @match)",
   "async def total(items):\n    return sum(items)\n", "def total(items):\n    return sum(items)\n",
   "Nothing in this coroutine awaits, so callers must await a function that never yields to the event loop: make it a plain def or await the real async work.", "S7503",
   filters=[r"node.has_re:^async\s+def", r"cap.lacks_re:b:\bawait\b|\basync\s+(for|with)\b|\byield\b",
            r"cap.lacks_re:b:^\s*((\x22\x22\x22[\s\S]*?\x22\x22\x22|\x27\x27\x27[\s\S]*?\x27\x27\x27)\s*)?(pass|\.\.\.|raise\s+NotImplementedError\b[^\n]*)\s*$"],
   sev="minor", kind="best-practice", cat="maintainability")
Py("DICT-UNPACK-NON-MAPPING", "** unpacking of a value that is not a mapping", (PYEXPR, "denoted with a double asterisk", "Python reference: Expressions"),
   "(dictionary_splat (_) @v) @match",
   "def f(g):\n    opts = [\"a\", \"b\"]\n    return g(**opts)\n", "def f(g):\n    opts = {\"a\": 1}\n    return g(**opts)\n",
   "** needs a mapping; a list/str/number raises TypeError at run time: unpack a dict (or use * for sequences).", "S5633",
   filters=[r"type.is:v:list|tuple|str|int|float|bool|set|bytes|frozenset"])
Py("TEMPLATE-STRING-CONCAT", "t-string concatenated with a plain string", (PYD + "library/string.templatelib.html", "Template", "Python docs: string.templatelib"),
   "(binary_operator left: (string) operator: \"+\" right: (string)) @match",
   "page = t\"<p>{name}</p>\" + \"<hr>\"\n", "page = t\"<p>{name}</p><hr>\"\n",
   "Template (t-string) objects cannot be concatenated with str (TypeError): put the text inside the t-string or process the template first.", "S7943",
   filters=[r"node.has_re:(^|\+\s*)[rR]?[tT][rR]?[\x22']", r"node.has_re:(^|\+\s*)[rRbBfFuU]{0,2}[\x22']"])
K("INDEXED-ACCESS-OPERATOR", "get() call where indexed access reads better", (KTDOC + "operator-overloading.html", "Indexed access operator", "Kotlin docs: Operator overloading"),
  "(call_expression (navigation_expression (_) @o (identifier) @m) (value_arguments . (value_argument) .) (#eq? @m \"get\")) @match",
  "fun f(names: List<String>): String {\n    return names.get(0)\n}\n", "fun f(names: List<String>): String {\n    return names[0]\n}\n",
  "Lists, arrays and maps support the indexing operator: write names[0] / map[key] instead of get().", "S6518",
  filters=[r"type.is:o:List|MutableList|ArrayList|Map|MutableMap|HashMap|LinkedHashMap|Array|IntArray|LongArray"], sev="minor", kind="modernization", cat="maintainability")
add("php", "VOID-RESULT-USED", "Result of a void function is used", (PHPM + "language.types.void.php", "does not return a value", "PHP manual: void"),
    "(assignment_expression right: (function_call_expression) @c) @match",
    "<?php\nfunction logLine(string $m): void {\n    echo $m;\n}\n$r = logLine('x');\n", "<?php\nfunction logLine(string $m): void {\n    echo $m;\n}\nlogLine('x');\n",
    "The function is declared void, so the variable is always null: call it as a statement.", keys=["S3699"],
    filters=[r"type.is:c:void"], cat="correctness", kind="anti-pattern", sev="major")


# ---- Sonar backlog batch 2 -----------------------------------------------------------------------
J("REPEATABLE-ANNOTATION-WRAPPED", "Repeated annotations wrapped in their container", ("https://docs.oracle.com/javase/tutorial/java/annotations/repeating.html", "Repeating Annotations", "Java tutorial: Repeating Annotations"),
  "((annotation name: (identifier) @n arguments: (annotation_argument_list (element_value_array_initializer (annotation name: (identifier) @i)))) @match)",
  "class A {\n    @Schedules({@Schedule(hour = 1), @Schedule(hour = 2)})\n    void run() {}\n}\n", "class A {\n    @Schedule(hour = 1)\n    @Schedule(hour = 2)\n    void run() {}\n}\n",
  "Since Java 8 a @Repeatable annotation can simply be written several times; the container wrapper only adds noise.", "S1710",
  filters=[r"cap.has_re:n:^{cap:i}s$"], cat="maintainability", kind="modernization", sev="minor")
J("BYTE-SIGN-EXTENSION-IN-SHIFT", "byte combined with shifted bits without masking", ("https://docs.oracle.com/javase/tutorial/java/nutsandbolts/datatypes.html", "The byte data type is an 8-bit signed two's complement integer", "Java tutorial: Primitive Data Types"),
  "[(binary_expression left: (parenthesized_expression (binary_expression operator: \"<<\")) operator: \"|\" right: (identifier) @b) (binary_expression left: (parenthesized_expression (binary_expression left: (identifier) @b operator: \"<<\")) operator: \"|\")] @match",
  "class A {\n    int word(byte hi, byte lo) {\n        return (hi << 8) | lo;\n    }\n}\n", "class A {\n    int word(byte hi, byte lo) {\n        return ((hi & 0xff) << 8) | (lo & 0xff);\n    }\n}\n",
  "A byte is sign-extended when widened, so negative values set all the high bits and corrupt the result: mask with & 0xff first.", "S3034",
  filters=[r"type.is:b:byte"])
Py("UNREAD-PRIVATE-ATTRIBUTE", "Private attribute is assigned but never read", (PYD + "tutorial/classes.html", "name mangling", "Python tutorial: Private Variables"),
   "((assignment left: (attribute object: (identifier) @s attribute: (identifier) @a)) @match (#eq? @s \"self\") (#match? @a \"^__[A-Za-z0-9]\") (#not-match? @a \"__$\"))",
   "class Job:\n    def __init__(self, name):\n        self.name = name\n        self.__retries = 3\n", "class Job:\n    def __init__(self, name):\n        self.__retries = 3\n\n    def retry(self):\n        self.__retries -= 1\n        return self.__retries\n",
   "A double-underscore attribute can only be read inside this class, and nothing here reads it: remove it or use it.", "S4487",
   filters=[r"ancestor.lacks_re:class_definition:self\.{cap:a}\b(\s*[^=\s]|\s*==)"], cat="maintainability", kind="best-practice", sev="minor")
add("php", "INCONSISTENT-RETURN", "Function mixes return with and without a value", (PHPM + "functions.returning-values.php", "If the return is omitted the value null will be returned", "PHP manual: Returning values"),
    "[(function_definition body: (compound_statement) @b) (method_declaration body: (compound_statement) @b)] @match",
    "<?php\nfunction find(array $xs, int $k) {\n    if (!isset($xs[$k])) {\n        return;\n    }\n    return $xs[$k];\n}\n",
    "<?php\nfunction find(array $xs, int $k) {\n    if (!isset($xs[$k])) {\n        return null;\n    }\n    return $xs[$k];\n}\n",
    "Some paths return a value and others return nothing (null), which hides whether null is intended: return a value on every path.", keys=["S3801"],
    filters=[r"cap.has_re:b:\breturn\s*;", r"cap.has_re:b:\breturn\s+[^;\s]", r"cap.lacks_re:b:\bfunction\s*\(|\bfn\s*\(|\byield\b"],
    cat="maintainability", kind="best-practice", sev="minor")


# ---- Sonar backlog batch 3 (java) ----------------------------------------------------------------
J("EMPTY-STATEMENT", "Stray empty statement", (JLS14, "An empty statement does nothing", "JLS 14.6 The Empty Statement"),
  "(block \";\" @match)",
  cls("    void run() {\n        start();;\n    }\n"), cls("    void run() {\n        start();\n    }\n"),
  "A lone ';' does nothing; it is usually a typo and can hide a misplaced loop or if body.", "S1116",
  cat="maintainability", kind="best-practice", sev="info")
J("COMPARETO-OVERLOAD", "compareTo overloaded with a type other than the Comparable argument", (JAPI + "lang/Comparable.html", "imposes a total ordering", "Java SE 21 API: Comparable"),
  "((class_declaration interfaces: (super_interfaces (type_list (generic_type (type_identifier) @c (type_arguments . (type_identifier) @t .)))) body: (class_body (method_declaration name: (identifier) @n parameters: (formal_parameters . (formal_parameter type: (_) @pt) .)) @match)) (#eq? @c \"Comparable\") (#eq? @n \"compareTo\"))",
  "class Version implements Comparable<Version> {\n    public int compareTo(Version o) { return 0; }\n    public int compareTo(String s) { return 0; }\n}\n",
  "class Version implements Comparable<Version> {\n    public int compareTo(Version o) { return 0; }\n    public int compareToText(String s) { return 0; }\n}\n",
  "Sorting and collections only call compareTo(T) from Comparable<T>; an overload with another type is never used by them and confuses callers.", "S4351",
  filters=[r"cap.lacks_re:pt:^{cap:t}$"])
J("DATE-FIELD-OUT-OF-RANGE", "java.time factory called with an out-of-range month or day", (JAPI + "time/LocalDate.html", "from 1 (January) to 12 (December)", "Java SE 21 API: LocalDate.of"),
  "((method_invocation object: (identifier) @o name: (identifier) @n arguments: (argument_list . (_) . (decimal_integer_literal) @v)) @match (#match? @o \"^(LocalDate|LocalDateTime|YearMonth)$\") (#eq? @n \"of\") (#match? @v \"^(0+|1[3-9]|[2-9][0-9]|[0-9]{3,})$\"))\n((method_invocation object: (identifier) @o name: (identifier) @n arguments: (argument_list . (_) . (_) . (decimal_integer_literal) @v)) @match (#match? @o \"^(LocalDate|LocalDateTime)$\") (#eq? @n \"of\") (#match? @v \"^(0+|3[2-9]|[4-9][0-9]|[0-9]{3,})$\"))",
  cls("    LocalDate end() {\n        return LocalDate.of(2026, 12, 31);\n    }\n    LocalDate next() {\n        return LocalDate.of(2027, 13, 1);\n    }\n"),
  cls("    LocalDate next() {\n        return LocalDate.of(2027, 1, 1);\n    }\n"),
  "Months run 1-12 and days 1-31: this call always throws DateTimeException.", "S2110",
  filters=[r"cap.lacks_re:v:^0[0-9]"])
J("RECORD-ACCESSOR-IN-COMPACT-CONSTRUCTOR", "Record accessor called inside the compact constructor", (JLS8, "all component fields of the record class are implicitly initialized", "JLS 8.10.4.2 Compact Canonical Constructors"),
  "[((method_invocation !object name: (identifier) @m arguments: (argument_list) @a) @match (#match? @a \"^\\\\(\\\\s*\\\\)$\")) ((method_invocation object: (this) name: (identifier) @m arguments: (argument_list) @a) @match (#match? @a \"^\\\\(\\\\s*\\\\)$\"))]",
  "record Range(int lo, int hi) {\n    Range {\n        if (lo() > hi()) {\n            throw new IllegalArgumentException();\n        }\n    }\n}\n",
  "record Range(int lo, int hi) {\n    Range {\n        if (lo > hi) {\n            throw new IllegalArgumentException();\n        }\n    }\n}\n",
  "Fields are only assigned after the compact constructor body: the accessor still returns 0/null here. Use the parameter instead.", "S3037",
  filters=["ancestor.has_re:compact_constructor_declaration:.", r"ancestor.has_re:record_declaration:^[^{]*?\brecord\s+\w+\s*(<[^>]*>)?\s*\([^)]*\b{cap:m}\s*[,)]",
           r"ancestor.lacks_re:class_body#2:\b{cap:m}\s*\(\s*\)\s*\{"])
J("UNSYNCHRONIZED-GETTER", "Getter not synchronized while its setter is", (JTUT + "syncmeth.html", "not possible for two invocations of synchronized methods on the same object to interleave", "Java tutorial: Synchronized Methods"),
  "((method_declaration name: (identifier) @n body: (block)) @match (#match? @n \"^(get|is)[A-Z]\"))",
  cls("    private int size;\n    public synchronized void setSize(int s) { size = s; }\n    public int getSize() { return size; }\n"),
  cls("    private int size;\n    public synchronized void setSize(int s) { size = s; }\n    public synchronized int getSize() { return size; }\n"),
  "Only the setter holds the lock, so a reader can see a stale value: synchronize the getter too (or make the field volatile).", "S2886",
  filters=[r"node.lacks_re:^[^{]*\bsynchronized\b", r"node.lacks_re:synchronized\s*\(", r"ancestor.has_re:class_body:\bsynchronized\b[^;{()]*\bset{cap:n~prop}\s*\(",
           r"ancestor.lacks_re:class_body:\b(volatile|Atomic\w+)\b"], cat="correctness", sev="major")
J("LOOP-LIST-REPLACE-ALL", "Index loop rewriting every list element", (JAPI + "util/List.html", "Replaces each element of this list with the result of applying the operator to that element", "Java SE 21 API: List.replaceAll"),
  "((for_statement body: [(block . (expression_statement (method_invocation object: (identifier) @l name: (identifier) @s arguments: (argument_list . (identifier) @i . (_) @v .))) .) (expression_statement (method_invocation object: (identifier) @l name: (identifier) @s arguments: (argument_list . (identifier) @i . (_) @v .)))]) @match (#eq? @s \"set\"))",
  cls("    void trim(List<String> names) {\n        for (int i = 0; i < names.size(); i++) {\n            names.set(i, names.get(i).trim());\n        }\n    }\n"),
  cls("    void trim(List<String> names) {\n        names.replaceAll(String::trim);\n    }\n"),
  "This loop maps every element in place; List.replaceAll(op) says it directly.", "S9411",
  filters=[r"cap.has_re:v:\b{cap:l}\.get\(\s*{cap:i}\s*\)", r"node.has_re:^for\s*\(\s*int\s+{cap:i}\s*=\s*0\s*;\s*{cap:i}\s*<\s*{cap:l}\.size\(\)\s*;\s*({cap:i}\+\+|\+\+{cap:i})\s*\)"],
  cat="maintainability", kind="modernization", sev="minor")

# ---- Sonar backlog batch 4 (java) ----------------------------------------------------------------
J("LOOP-MULTIPLE-JUMPS", "Loop body with several break/continue statements", (JLS14, "A break statement transfers control out of an enclosing statement", "JLS 14.15 The break Statement"),
  "[(for_statement body: (block) @b) (enhanced_for_statement body: (block) @b) (while_statement body: (block) @b) (do_statement body: (block) @b)] @match",
  cls("    void scan(int[] xs) {\n        for (int x : xs) {\n            if (x < 0) continue;\n            if (x == 0) break;\n            use(x);\n        }\n    }\n"),
  cls("    void scan(int[] xs) {\n        for (int x : xs) {\n            if (x == 0) break;\n            if (x > 0) use(x);\n        }\n    }\n"),
  "Each extra break or continue adds another exit to follow when reading the loop: fold the conditions or extract the body.", "S135",
  filters=[r"cap.has_re:b:(?s)\b(break|continue)(\s+\w+)?\s*;.*\b(break|continue)(\s+\w+)?\s*;",
           r"cap.lacks_re:b:\b(for|while|do|switch)\s*[({]|->|\bnew\s+\w+(<[^>]*>)?\s*\([^)]*\)\s*\{"],
  cat="maintainability", kind="best-practice", sev="info")
J("SWITCH-TOO-FEW-CASES", "switch statement with fewer than three cases", (JLS14, "The switch statement transfers control to one of several statements", "JLS 14.11 The switch Statement"),
  "(block (switch_expression body: (switch_block . (switch_block_statement_group) . (switch_block_statement_group)? .) @b) @match)",
  cls("    void apply(int mode) {\n        switch (mode) {\n            case 1:\n                start();\n                break;\n            default:\n                stop();\n        }\n    }\n"),
  cls("    void apply(int mode) {\n        if (mode == 1) {\n            start();\n        } else {\n            stop();\n        }\n    }\n"),
  "A switch with one or two branches reads more plainly as an if/else.", "S1301",
  filters=[r"cap.lacks_re:b:(?s)(\bcase\b.*){3}"],
  cat="maintainability", kind="best-practice", sev="info")

add("php", "SWITCH-TOO-FEW-CASES", "switch statement with fewer than three cases", (PHPM + "control-structures.switch.php", "The switch statement is similar to a series of if statements on the same expression", "PHP manual: switch"),
    "(switch_statement body: (switch_block . (_) . (_)? .) @b) @match",
    "<?php\nfunction apply(int $mode) {\n    switch ($mode) {\n        case 1:\n            start();\n            break;\n        default:\n            stop();\n    }\n}\n",
    "<?php\nfunction apply(int $mode) {\n    if ($mode === 1) {\n        start();\n    } else {\n        stop();\n    }\n}\n",
    "A switch with one or two branches reads more plainly as an if/else (and avoids switch's loose == comparison).", keys=["S1301"],
    filters=[r"cap.lacks_re:b:(?s)(\bcase\b.*){3}"], cat="maintainability", kind="best-practice", sev="info")

# Angular ([x], [attr.x], bind-x) and Vue (:x) bindings provide the attribute the text regexes
# looked for: markup.lacks_attr understands every binding syntax (former Angular-template FPs).
BINDING_SAFE = {
    "HTML-MAINT-FRAME-WITHOUT-TITLE": "markup.lacks_attr:title|aria-label|aria-labelledby|aria-hidden",
    "HTML-MAINT-TH-WITHOUT-SCOPE-OR-ID": "markup.lacks_attr:scope|id|headers",
    "HTML-MAINT-ROLE-WITHOUT-TABINDEX": "markup.lacks_attr:tabindex",
    "HTML-MAINT-HANDLER-ON-STATIC-ELEMENT": "markup.lacks_attr:role",
    "HTML-MAINT-HTML-WITHOUT-LANG": "markup.lacks_attr:lang",
    "HTML-MAINT-EMPTY-ANCHOR": "markup.lacks_attr:aria-label|aria-labelledby|title|innerhtml|innertext|textcontent",
    "HTML-MAINT-IMG-WITHOUT-ALT": "markup.lacks_attr:alt|aria-label|aria-labelledby",
}
BINDING_FP = {
    "HTML-MAINT-FRAME-WITHOUT-TITLE": '<iframe [src]="url" [title]="label"></iframe>',
    "HTML-MAINT-TH-WITHOUT-SCOPE-OR-ID": '<table><tr><th [attr.scope]="dir">Item</th></tr></table>',
    "HTML-MAINT-ROLE-WITHOUT-TABINDEX": '<div role="button" [attr.tabindex]="0" (click)="save()" (keydown.enter)="save()">Save</div>',
    "HTML-MAINT-EMPTY-ANCHOR": '<a href="/cart" [attr.aria-label]="cartLabel"><i class="icon-cart"></i></a>',
    "HTML-MAINT-IMG-WITHOUT-ALT": '<img [src]="u" bind-alt="label">',
}
for _r in P["html"].R:
    if _r["id"] in BINDING_SAFE:
        _r["detection"]["filters"] = list(_r["detection"].get("filters") or []) + [BINDING_SAFE[_r["id"]]]
        if _r["id"] in BINDING_FP:
            _r["examples"]["regressions"] = list(_r["examples"].get("regressions") or []) + [
                {"code": page(BINDING_FP[_r["id"]]), "note": "Angular template binding supplies the attribute"}]
        _r["rule_version"] = 2

for _p in P.values():
    for _r in _p.R:
        if _r.get("category") != "accessibility":
            continue
        _w = WCAG_OF.get(_r["id"].split("-", 2)[-1]) or WCAG_OF.get(_r["id"].split("-", 1)[-1])
        if _w == "bp":
            _r["tags"] = list(_r.get("tags") or []) + ["a11y-best-practice"]
        elif _w:
            _r["wcag"] = _w

# keep last: every rule above is registered
RULES = [r for p in P.values() for r in p.R]


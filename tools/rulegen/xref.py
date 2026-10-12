#!/usr/bin/env python3
"""Generate rules/data/xref.yaml: crev rule id -> equivalent external linter rule ids ("tool:id").

Sources, in order:
  1. explicit "tool:id" entries already in a rule's xref list (kept as-is by the loader);
  2. derivation from the rule's official doc URLs (source.url + xref URLs) for linter docs:
     eslint, typescript-eslint, eslint-plugin-vue, @graphql-eslint, react-hooks, ruff (+ the
     upstream flake8/pylint/bandit code ruff re-implements), go vet analyzers, tflint, Docker
     build checks;
  3. MANUAL below: reviewed mappings where the doc URL is not a linter page (hadolint, buf,
     yamllint, tflint README rows, golangci/staticcheck/gosec, detekt/ktlint, PHPStan, Checkstyle,
     PMD, SpotBugs, Error Prone, mypy, tsconfig compiler options, checkov, editorconfig, ...).

Ruff name->code data comes from `ruff rule --all --output-format json` (pass --ruff FILE).
Usage: python tools/rulegen/xref.py [--ruff /tmp/ruff_rules.json]
"""
import glob, json, re, sys, os
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MANUAL = {
    # hadolint (https://github.com/hadolint/hadolint#rules)
    "DOCKER-QUAL-LATEST-TAG": ["hadolint:DL3006", "hadolint:DL3007"],
    "DOCKER-QUAL-APT-NO-INSTALL-RECOMMENDS": ["hadolint:DL3015"],
    "DOCKER-QUAL-APT-LISTS-NOT-REMOVED": ["hadolint:DL3009"],
    "DOCKER-QUAL-PIPE-WITHOUT-PIPEFAIL": ["hadolint:DL4006"],
    "DOCKER-QUAL-ADD-LOCAL-FILE": ["hadolint:DL3020"],
    "DOCKER-QUAL-SUDO": ["hadolint:DL3004"],
    "DOCKER-QUAL-RUN-CD": ["hadolint:DL3003"],
    "DOCKER-QUAL-WORKDIR-RELATIVE-PATH": ["hadolint:DL3000"],
    "DOCKER-QUAL-MULTIPLE-CMD": ["hadolint:DL4003", "hadolint:DL4004"],
    "DOCKER-MIG-MAINTAINER-DEPRECATED": ["hadolint:DL4000"],
    "DOCKER-QUAL-JSON-ARGS-RECOMMENDED": ["hadolint:DL3025"],
    "DOCKER-SEC-USER-ROOT": ["hadolint:DL3002", "checkov:CKV_DOCKER_8"],
    "DOCKER-SEC-NO-USER": ["checkov:CKV_DOCKER_3"],
    "DOCKER-QUAL-HEALTHCHECK-MISSING": ["checkov:CKV_DOCKER_2"],
    "DOCKER-QUAL-COPY-FROM-INDEX": ["hadolint:DL3022"],
    "DOCKER-QUAL-DUPLICATE-STAGE-NAME": ["hadolint:DL3024"],
    "DOCKER-QUAL-EXPOSE-INVALID-FORMAT": ["hadolint:DL3011"],
    "DOCKER-SEC-CURL-PIPE-SHELL": ["hadolint:DL4006"],
    # buf lint (https://buf.build/docs/lint/rules/)
    "PROTO-QUAL-SERVICE-SUFFIX": ["buf:SERVICE_SUFFIX"],
    "PROTO-QUAL-RPC-STANDARD-MESSAGE-NAMES": ["buf:RPC_REQUEST_STANDARD_NAME", "buf:RPC_RESPONSE_STANDARD_NAME", "buf:RPC_REQUEST_RESPONSE_UNIQUE"],
    "PROTO-QUAL-PACKAGE-DEFINED": ["buf:PACKAGE_DEFINED"],
    "PROTO-QUAL-SYNTAX-SPECIFIED": ["buf:SYNTAX_SPECIFIED"],
    "PROTO-QUAL-PACKAGE-VERSION-SUFFIX": ["buf:PACKAGE_VERSION_SUFFIX"],
    "PROTO-QUAL-IMPORT-PUBLIC": ["buf:IMPORT_NO_PUBLIC"],
    "PROTO-MIG-IMPORT-WEAK": ["buf:IMPORT_NO_WEAK"],
    "PROTO-QUAL-ENUM-ALLOW-ALIAS": ["buf:ENUM_NO_ALLOW_ALIAS"],
    # tflint-ruleset-terraform rows cited from the README
    "TF-MIG-DEPRECATED-INTERPOLATION": ["tflint:terraform_deprecated_interpolation"],
    "TF-QUAL-COMMENT-SYNTAX": ["tflint:terraform_comment_syntax"],
    "TF-QUAL-MODULE-VERSION": ["tflint:terraform_module_version"],
    "TF-QUAL-REQUIRED-VERSION": ["tflint:terraform_required_version"],
    "TF-QUAL-WORKSPACE-REMOTE": ["tflint:terraform_workspace_remote"],
    "TF-QUAL-TYPED-VARIABLES": ["tflint:terraform_typed_variables"],
    "TF-QUAL-DOCUMENTED-VARIABLES": ["tflint:terraform_documented_variables"],
    "TF-QUAL-DOCUMENTED-OUTPUTS": ["tflint:terraform_documented_outputs"],
    # yamllint (https://yamllint.readthedocs.io/en/stable/rules.html)
    "YAML-QUAL-DUPLICATE-KEY-FLOW": ["yamllint:key-duplicates"],
    "YAML-QUAL-TRUTHY": ["yamllint:truthy"],
    "YAML-QUAL-TRUTHY-CASE": ["yamllint:truthy"],
    "YAML-QUAL-IMPLICIT-OCTAL": ["yamllint:octal-values"],
    "YAML-QUAL-EXPLICIT-OCTAL": ["yamllint:octal-values"],
    "YAML-QUAL-FLOAT-NO-NUMERAL": ["yamllint:float-values"],
    "YAML-QUAL-FLOAT-SCIENTIFIC": ["yamllint:float-values"],
    "YAML-QUAL-FLOAT-NAN": ["yamllint:float-values"],
    "YAML-QUAL-FLOAT-INF": ["yamllint:float-values"],
    "YAML-QUAL-UNDECLARED-ALIAS": ["yamllint:anchors"],
    "YAML-QUAL-DUPLICATE-ANCHOR": ["yamllint:anchors"],
    "YAML-QUAL-UNUSED-ANCHOR": ["yamllint:anchors"],
    "YAML-QUAL-EMPTY-VALUE": ["yamllint:empty-values"],
    "YAML-QUAL-DOCUMENT-START": ["yamllint:document-start"],
    "YAML-QUAL-COMMENT-SPACE": ["yamllint:comments"],
    "YAML-QUAL-BRACES-SPACES": ["yamllint:braces"],
    "YAML-QUAL-BRACKETS-SPACES": ["yamllint:brackets"],
    "YAML-QUAL-COLON-SPACE-BEFORE": ["yamllint:colons"],
    "YAML-QUAL-COMMA-SPACE-BEFORE": ["yamllint:commas"],
    "YAML-QUAL-TRAILING-SPACES": ["yamllint:trailing-spaces", "editorconfig:trim_trailing_whitespace"],
    "YAML-QUAL-NO-FINAL-NEWLINE": ["yamllint:new-line-at-end-of-file", "editorconfig:insert_final_newline"],
    "YAML-QUAL-CRLF": ["yamllint:new-lines", "editorconfig:end_of_line"],
    "YAML-QUAL-LINE-LENGTH": ["yamllint:line-length", "editorconfig:max_line_length"],
    "YAML-QUAL-EMPTY-LINES": ["yamllint:empty-lines"],
    "YAML-QUAL-DUPLICATE-KEY": ["yamllint:key-duplicates"],
    # Go: staticcheck / gosec / revive (golangci-lint linters)
    "GO-SEC-MATH-RAND-SECURITY": ["gosec:G404"],
    "GO-SEC-WEAK-CRYPTO-MD5": ["gosec:G401", "gosec:G501"],
    "GO-SEC-WEAK-CRYPTO-SHA1": ["gosec:G401", "gosec:G505"],
    "GO-SEC-SQL-STRING-BUILD": ["gosec:G201", "gosec:G202"],
    "GO-MIG-IOUTIL": ["staticcheck:SA1019"],
    "GO-MIG-RAND-SEED": ["staticcheck:SA1019"],
    "GO-SEC-MATH-RAND-READ": ["staticcheck:SA1019"],
    "GO-MOD-ANY": ["revive:use-any"],
    # Java: Error Prone / SpotBugs / PMD / Checkstyle
    "JAVA-QUAL-COR-STRING-EQ-001": ["errorprone:StringEquality", "spotbugs:ES_COMPARING_STRINGS_WITH_EQ", "pmd:UseEqualsToCompareStrings"],
    "JAVA-SEC-PRINTSTACK-001": ["pmd:AvoidPrintStackTrace"],
    "JAVA-MIG-THR-001": ["errorprone:ThreadStop"],
    "JAVA-MIG-FIN-001": ["checkstyle:NoFinalizer", "pmd:AvoidCallingFinalize", "spotbugs:FI_FINALIZER_ONLY_NULLS_FIELDS"],
    "JAVA-SEC-RANDOM-001": ["spotbugs:PREDICTABLE_RANDOM"],
    "JAVA-SEC-MATHRANDOM-001": ["spotbugs:PREDICTABLE_RANDOM"],
    "JAVA-SEC-SQLI-001": ["spotbugs:SQL_INJECTION_JDBC", "pmd:SqlInjection"],
    "JAVA-MOD-UNNAMED-001": ["errorprone:UnusedVariable"],
    # Kotlin: detekt / ktlint
    "KT-QUAL-NOT-NULL-ASSERTION": ["detekt:UnsafeCallOnNullableType"],
    "KT-QUAL-EMPTY-CATCH": ["detekt:EmptyCatchBlock"],
    "KT-QUAL-PRINTLN-LOGGING": ["detekt:PrintStackTrace"],
    "KT-QUAL-GLOBALSCOPE": ["detekt:GlobalCoroutineUsage"],
    "KT-QUAL-RUNBLOCKING-IN-SUSPEND": ["detekt:SuspendFunWithCoroutineScopeReceiver"],
    "KT-SEC-INSECURE-RANDOM": ["detekt:InsecureRandom"],
    # PHP: PHPStan / Psalm / PHP_CodeSniffer
    "PHP-SEC-EVAL": ["psalm:ForbiddenCode", "phpcs:Squiz.PHP.Eval"],
    "PHP-MIG-BACKTICK-OPERATOR": ["phpcs:Generic.PHP.BacktickOperator", "psalm:ForbiddenCode"],
    "PHP-SEC-EXTRACT-INPUT": ["phpcs:Generic.PHP.ForbiddenFunctions"],
    # TypeScript (typescript-eslint and tsconfig equivalents)
    "TS-QUAL-ANY-001": ["typescript-eslint:@typescript-eslint/no-explicit-any"],
    "TS-QUAL-NONNULL-001": ["typescript-eslint:@typescript-eslint/no-non-null-assertion"],
    "TS-QUAL-TSIGNORE-001": ["typescript-eslint:@typescript-eslint/ban-ts-comment"],
    "TS-QUAL-CATCH-ANY-001": ["typescript-eslint:@typescript-eslint/use-unknown-in-catch-callback-variable", "tsconfig:useUnknownInCatchVariables"],
    "TS-QUAL-CFG-ALLOWUNUSEDLABELS-001": ["tsconfig:allowUnusedLabels", "eslint:no-unused-labels"],
    # JavaScript / Python security
    "JS-SEC-EVAL-001": ["eslint:no-eval"],
    "PY-SEC-EVAL": ["ruff:S307", "bandit:B307"],
    "PY-SEC-RANDOM-FOR-SECURITY": ["ruff:S311", "bandit:B311"],
    "PY-SEC-SQL-STRING-FORMAT": ["ruff:S608", "bandit:B608"],
    "PY-SEC-HASH-WEAK": ["ruff:S324", "bandit:B324"],
    "PY-SEC-TARFILE-EXTRACTALL-NO-FILTER": ["ruff:S202", "bandit:B202"],
}

TOOLS = {"eslint", "typescript-eslint", "eslint-plugin-vue", "graphql-eslint", "angular-eslint", "react", "react-hooks", "stylelint",
         "tsconfig", "prettier", "golangci-lint", "govet", "staticcheck", "gosec", "revive", "ktlint", "detekt", "phpstan", "psalm",
         "phpcs", "ruff", "pylint", "flake8", "mypy", "bandit", "checkstyle", "pmd", "spotbugs", "errorprone", "hadolint",
         "docker-build-check", "tflint", "checkov", "yamllint", "buf", "editorconfig", "oxlint", "sonar", "semgrep", "snyk"}

def camel(slug):
    return "".join(p.capitalize() for p in slug.split("-"))

def from_url(u, ruff):
    out = []
    m = re.match(r"https://eslint\.org/docs/latest/rules/([a-z0-9-]+)", u)
    if m: out.append("eslint:" + m.group(1))
    m = re.match(r"https://typescript-eslint\.io/rules/([a-z0-9-]+)", u)
    if m: out.append("typescript-eslint:@typescript-eslint/" + m.group(1))
    m = re.match(r"https://eslint\.vuejs\.org/rules/([a-z0-9-]+)", u)
    if m: out.append("eslint-plugin-vue:vue/" + m.group(1))
    m = re.match(r"https://the-guild\.dev/graphql/eslint/rules/([a-z0-9-]+)", u)
    if m: out.append("graphql-eslint:@graphql-eslint/" + m.group(1))
    m = re.match(r"https://react\.dev/reference/eslint-plugin-react-hooks/lints/([a-z0-9-]+)", u)
    if m: out.append("react-hooks:react-hooks/" + m.group(1))
    m = re.match(r"https://github\.com/angular-eslint/angular-eslint/.*/docs/rules/([a-z0-9-]+)\.md", u)
    if m: out.append("angular-eslint:@angular-eslint/" + m.group(1))
    m = re.match(r"https://pkg\.go\.dev/golang\.org/x/tools/go/analysis/passes/([a-z0-9]+)", u)
    if m: out.append("govet:" + m.group(1))
    m = re.match(r"https://staticcheck\.dev/docs/checks/?#([A-Z]+[0-9]+)", u)
    if m: out.append("staticcheck:" + m.group(1))
    m = re.search(r"tflint-ruleset-terraform/[^/]+/docs/rules/(terraform_[a-z_]+)\.md", u)
    if m: out.append("tflint:" + m.group(1))
    m = re.match(r"https://docs\.docker\.com/reference/build-checks/([a-z-]+)", u)
    if m: out.append("docker-build-check:" + camel(m.group(1)))
    m = re.match(r"https://docs\.astral\.sh/ruff/rules/([a-z0-9-]+)", u)
    if m and m.group(1) in ruff:
        code, linter = ruff[m.group(1)]
        out.append("ruff:" + code)
        if linter in ("Pyflakes", "pycodestyle", "mccabe") or linter.startswith("flake8-") and linter not in ("flake8-bandit",):
            out.append("flake8:" + code)
        elif linter == "Pylint":
            out.append("pylint:" + code[2:] + "/" + m.group(1))
        elif linter == "flake8-bandit":
            out.append("bandit:B" + code[1:])
    return out

def main():
    global SONAR, PREV_ALL
    SONAR = {}
    _pp = os.path.join(ROOT, "rules/data/xref.yaml")
    PREV_ALL = (yaml.safe_load(open(_pp, encoding="utf-8"))["rules"] or {}) if os.path.exists(_pp) else {}
    for name, tool in (("sonar-map.yaml", "sonar"),):
        p = os.path.join(ROOT, "tools/gap", name)
        if os.path.exists(p):
            SONAR = yaml.safe_load(open(p, encoding="utf-8"))["rules"]
    ruff = {}
    args = sys.argv[1:]
    cache = os.path.join(ROOT, "tools/rulegen/data/ruff-rules.json")
    data = None
    if "--ruff" in args:
        data = json.load(open(args[args.index("--ruff") + 1], encoding="utf-8"))
    else:
        import subprocess, shutil
        exe = shutil.which("ruff") or (os.path.exists("/tmp/venv/bin/ruff") and "/tmp/venv/bin/ruff")
        if exe:
            try:
                data = json.loads(subprocess.run([exe, "rule", "--all", "--output-format", "json"], capture_output=True, text=True, check=True).stdout)
            except Exception as e:  # noqa: BLE001
                print("xref: ruff rule --all failed:", e, file=sys.stderr)
        if data is None and os.path.exists(cache):
            data = json.load(open(cache, encoding="utf-8"))
    if data is not None:
        for r in data:
            ruff[r["name"]] = (r["code"], r["linter"])
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump([{"name": r["name"], "code": r["code"], "linter": r["linter"]} for r in data], open(cache, "w", encoding="utf-8"), indent=0)
    # Without ruff data the ruff-derived links cannot be recomputed: keep the previous ones instead of dropping them.
    prev = {}
    prev_path = os.path.join(ROOT, "rules/data/xref.yaml")
    if not ruff and os.path.exists(prev_path):
        print("xref: no ruff data (pass --ruff, install ruff, or keep tools/rulegen/data/ruff-rules.json); keeping previous ruff/flake8/pylint/bandit links", file=sys.stderr)
        prev = yaml.safe_load(open(prev_path, encoding="utf-8"))["rules"] or {}
    ids, out = set(), {}
    for f in sorted(glob.glob(os.path.join(ROOT, "rules/packs/*/*.yaml"))):
        for r in yaml.safe_load(open(f, encoding="utf-8"))["rules"]:
            ids.add(r["id"])
            urls = [r["source"]["url"]] + [x for x in (r.get("xref") or []) if "://" in x]
            # hand-written packs cite MDN etc. and name the linter rule as "rule mirror: <url>"
            urls += re.findall(r"rule mirror: (https://\S+?)\)?(?:\s|$)", r["source"].get("doc", "") or "")
            eq = []
            for u in urls:
                eq += from_url(u, ruff)
            eq += MANUAL.get(r["id"], [])
            if not ruff:
                eq += [e for e in prev.get(r["id"], []) if e.split(":", 1)[0] in ("ruff", "flake8", "pylint", "bandit")]
            # explicit sonar:/semgrep:/snyk: links added by hand to xref.yaml for rules whose specs do not carry them
            eq += [e for e in PREV_ALL.get(r["id"], []) if e.split(":", 1)[0] in ("sonar", "semgrep", "snyk")]
            eq += ["sonar:" + k for k in SONAR.get(r["id"], [])]
            eq = list(dict.fromkeys(eq))
            if eq:
                out[r["id"]] = eq
    # oxlint implements many ESLint-family rules natively: add oxlint:<plugin>/<rule> next to the
    # ESLint-family equivalent when the pinned oxlint rule table has it.
    ox = json.load(open(os.path.join(ROOT, "internal/projcfg/oxlint_rules.json"), encoding="utf-8"))["rules"]
    fam = {"eslint": lambda i: "eslint/" + i, "typescript-eslint": lambda i: "typescript/" + i.split("/")[-1],
           "eslint-plugin-vue": lambda i: "vue/" + i.split("/")[-1], "react-hooks": lambda i: "react/" + i.split("/")[-1],
           "react": lambda i: "react/" + i.split("/")[-1]}
    for k, v in out.items():
        add = []
        for e in v:
            t, i = e.split(":", 1)
            if t in fam and fam[t](i) in ox:
                add.append("oxlint:" + fam[t](i))
        out[k] = list(dict.fromkeys(v + add))
    unknown = [k for k in MANUAL if k not in ids]
    for k in unknown:
        print("xref: MANUAL id not in catalog (skipped):", k, file=sys.stderr)
    for k, v in out.items():
        for e in v:
            assert e.split(":", 1)[0] in TOOLS, (k, e)
    by_tool = {}
    for v in out.values():
        for e in v:
            t = e.split(":", 1)[0]
            by_tool[t] = by_tool.get(t, 0) + 1
    with open(os.path.join(ROOT, "rules/data/xref.yaml"), "w", encoding="utf-8") as fh:
        fh.write("# Generated by tools/rulegen/xref.py: crev rule id -> equivalent external linter rules (tool:id).\n")
        fh.write("# Used to honour project linter configuration (rule turned off => crev equivalent suppressed).\n")
        yaml.safe_dump({"rules": out}, fh, sort_keys=True, width=200)
    print(f"xref: {len(out)} rules mapped, {sum(by_tool.values())} links; by tool: {dict(sorted(by_tool.items()))}; {len(unknown)} manual ids not in catalog")

main()

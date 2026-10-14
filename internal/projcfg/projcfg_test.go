package projcfg

import (
	"os"
	"path/filepath"
	"slices"
	"testing"
)

func write(t *testing.T, root string, files map[string]string) []string {
	t.Helper()
	var rels []string
	for rel, body := range files {
		p := filepath.Join(root, rel)
		os.MkdirAll(filepath.Dir(p), 0o755)
		if err := os.WriteFile(p, []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
		rels = append(rels, rel)
	}
	return rels
}

func TestDiscoverAndDecide(t *testing.T) {
	root := t.TempDir()
	files := write(t, root, map[string]string{
		"eslint.config.mjs": `import js from "@eslint/js";
export default [
  js.configs.recommended,
  { rules: { "no-eval": "off", "max-len": ["error", { code: 120 }], eqeqeq: 2 } },
  { files: ["legacy/**/*.{js,ts}"], rules: { "@typescript-eslint/no-explicit-any": 0 } },
  { files: ["strict/**"], rules: { "no-eval": "error" } },
];`,
		"web/.eslintrc.json": `{ // comment
  "rules": { "vue/valid-v-for": "off" },
  "overrides": [{ "files": ["*.spec.ts"], "excludedFiles": ["keep.spec.ts"], "rules": { "no-console": "off" } }] }`,
		"pkg/package.json": `{"name":"x","eslintConfig":{"rules":{"no-debugger":0}}}`,
		".golangci.yml":    "version: \"2\"\nlinters:\n  disable: [gosec]\n  settings:\n    govet:\n      disable: [lostcancel]\n    staticcheck:\n      checks: [\"all\", \"-SA1019\", \"-ST*\"]\n  exclusions:\n    rules:\n      - path: _test\\.go\n        linters: [revive]\n      - text: \"some message\"\n        linters: [govet]\n",
		"pyproject.toml":   "[tool.ruff]\nline-length = 100\n[tool.ruff.lint]\nselect = [\"ALL\"]\nignore = [\"S307\", \"PLW\"]\n[tool.ruff.lint.per-file-ignores]\n\"tests/**\" = [\"S101\"]\n[tool.mypy]\ndisable_error_code = [\"import-untyped\"]\n[tool.pylint.\"messages control\"]\ndisable = [\"unspecified-encoding\"]\n",
		"setup.cfg":        "[flake8]\nextend-ignore = E203, W503\nper-file-ignores =\n    __init__.py: F401\n",
		"detekt.yml":       "style:\n  WildcardImport:\n    active: false\n  MaxLineLength:\n    maxLineLength: 140\npotential-bugs:\n  active: false\n  UnsafeCallOnNullableType:\n    active: true\n",
		".editorconfig":    "root = true\n[*]\nmax_line_length = 100\n[*.{kt,kts}]\nktlint_standard_no-wildcard-imports = disabled\n[*.md]\ntrim_trailing_whitespace = false\n",
		"config/checkstyle/checkstyle.xml": `<?xml version="1.0"?><!DOCTYPE module PUBLIC "-//Checkstyle//DTD Checkstyle Configuration 1.3//EN" "https://checkstyle.org/dtds/configuration_1_3.dtd">
<module name="Checker"><module name="TreeWalker"><module name="EmptyCatchBlock"><property name="severity" value="ignore"/></module><module name="LineLength"><property name="max" value="150"/></module></module></module>`,
		"pmd.xml":              `<ruleset name="x"><rule ref="category/java/bestpractices.xml"><exclude name="AvoidPrintStackTrace"/></rule></ruleset>`,
		"spotbugs-exclude.xml": `<FindBugsFilter><Match><Bug pattern="PREDICTABLE_RANDOM"/></Match></FindBugsFilter>`,
		"pom.xml":              `<project><build><plugins><plugin><configuration><compilerArgs><arg>-Xplugin:ErrorProne -Xep:StringEquality:OFF -Xep:ThreadStop:ERROR</arg></compilerArgs></configuration></plugin></plugins></build></project>`,
		"phpstan.neon":         "parameters:\n\tignoreErrors:\n\t\t-\n\t\t\tidentifier: missingType.iterableValue\n\t\t\tpath: src/Legacy/*\n",
		"psalm.xml":            `<psalm><issueHandlers><ForbiddenCode errorLevel="suppress"/><MixedAssignment><errorLevel type="suppress"><directory name="src/Old"/></errorLevel></MixedAssignment></issueHandlers></psalm>`,
		"phpcs.xml":            `<ruleset name="x"><rule ref="PSR12"><exclude name="Generic.Files.LineLength"/></rule><rule ref="Squiz.PHP.Eval"><severity>0</severity></rule></ruleset>`,
		".hadolint.yaml":       "ignored:\n  - DL3007\n",
		".tflint.hcl":          "rule \"terraform_typed_variables\" {\n  enabled = false\n}\nrule \"terraform_naming_convention\" {\n  enabled = true\n}\n",
		".yamllint":            "extends: default\nrules:\n  truthy: disable\n  line-length:\n    max: 120\n  document-start:\n    ignore: |\n      charts/\n",
		"proto/buf.yaml":       "version: v2\nlint:\n  use: [STANDARD]\n  except: [PACKAGE_VERSION_SUFFIX]\n  ignore_only:\n    SERVICE_SUFFIX: [legacy]\n",
		"tsconfig.json":        `{"extends": "./tsconfig.base.json", "compilerOptions": {"allowUnusedLabels": true}}`,
		"tsconfig.base.json":   `{"compilerOptions": {"useUnknownInCatchVariables": false, "strict": true}}`,
		".checkov.yaml":        "skip-check:\n  - CKV_DOCKER_2\n",
	})
	s := Discover(root, files)
	if len(s.Errors) > 0 {
		t.Fatalf("errors: %v", s.Errors)
	}
	for _, c := range []struct {
		eq, path string
		off      bool
	}{
		{"eslint:no-eval", "src/a.js", true},
		{"eslint:no-eval", "strict/a.js", false}, // later override re-enables
		{"eslint:eqeqeq", "src/a.js", false},
		{"typescript-eslint:@typescript-eslint/no-explicit-any", "legacy/x/a.ts", true},
		{"typescript-eslint:@typescript-eslint/no-explicit-any", "src/a.ts", false},
		{"eslint-plugin-vue:vue/valid-v-for", "web/App.vue", true},
		{"eslint-plugin-vue:vue/valid-v-for", "other/App.vue", false}, // legacy config only covers its dir
		{"eslint:no-console", "web/src/a.spec.ts", true},
		{"eslint:no-console", "web/src/keep.spec.ts", false},
		{"eslint:no-debugger", "pkg/index.js", true},
		{"gosec:G404", "main.go", true},
		{"govet:lostcancel", "main.go", true},
		{"govet:printf", "main.go", false},
		{"staticcheck:SA1019", "main.go", true},
		{"staticcheck:ST1003", "main.go", true},
		{"staticcheck:SA4006", "main.go", false},
		{"revive:exported", "a_test.go", true},
		{"revive:exported", "a.go", false},
		{"ruff:S307", "app.py", true},
		{"ruff:PLW1514", "app.py", true}, // prefix PLW
		{"ruff:S101", "tests/test_a.py", true},
		{"ruff:S101", "app.py", false},
		{"mypy:import-untyped", "app.py", true},
		{"pylint:W1514/unspecified-encoding", "app.py", true},
		{"flake8:W503", "app.py", true},
		{"flake8:F401", "pkg/__init__.py", true},
		{"flake8:F401", "pkg/mod.py", false},
		{"detekt:WildcardImport", "A.kt", true},
		{"detekt:UnsafeCallOnNullableType", "A.kt", true}, // whole rule set inactive
		{"ktlint:standard:no-wildcard-imports", "src/A.kt", true},
		{"ktlint:standard:no-wildcard-imports", "src/A.java", false},
		{"editorconfig:trim_trailing_whitespace", "docs/a.md", true},
		{"checkstyle:EmptyCatchBlock", "A.java", true},
		{"pmd:AvoidPrintStackTrace", "A.java", true},
		{"spotbugs:PREDICTABLE_RANDOM", "A.java", true},
		{"errorprone:StringEquality", "A.java", true},
		{"errorprone:ThreadStop", "A.java", false},
		{"phpstan:missingType.iterableValue", "src/Legacy/A.php", true},
		{"phpstan:missingType.iterableValue", "src/New/A.php", false},
		{"psalm:ForbiddenCode", "a.php", true},
		{"psalm:MixedAssignment", "src/Old/a.php", true},
		{"psalm:MixedAssignment", "src/New/a.php", false},
		{"phpcs:Generic.Files.LineLength", "a.php", true},
		{"phpcs:Squiz.PHP.Eval", "a.php", true},
		{"hadolint:DL3007", "Dockerfile", true},
		{"hadolint:DL3008", "Dockerfile", false},
		{"tflint:terraform_typed_variables", "main.tf", true},
		{"tflint:terraform_naming_convention", "main.tf", false},
		{"yamllint:truthy", "a.yaml", true},
		{"yamllint:document-start", "charts/x/values.yaml", true},
		{"yamllint:document-start", "a.yaml", false},
		{"yamllint:line-length", "a.yaml", false},
		{"buf:PACKAGE_VERSION_SUFFIX", "proto/a/v1/a.proto", true},
		{"buf:SERVICE_SUFFIX", "proto/legacy/a.proto", true},
		{"buf:SERVICE_SUFFIX", "proto/new/a.proto", false},
		{"buf:PACKAGE_VERSION_SUFFIX", "elsewhere/a.proto", false},
		{"tsconfig:allowUnusedLabels", "src/a.ts", true},
		{"tsconfig:useUnknownInCatchVariables", "src/a.ts", true}, // via extends
		{"tsconfig:strict", "src/a.ts", false},
		{"checkov:CKV_DOCKER_2", "Dockerfile", true},
	} {
		d := s.Decide([]string{c.eq}, c.path)
		if (d != nil) != c.off {
			t.Errorf("%s @ %s: off=%v want %v (%+v)", c.eq, c.path, d != nil, c.off, d)
		}
	}
	if v, d := s.Param([]string{"yamllint:line-length"}, "a.yaml", "max"); d == nil || v.(float64) != 120 {
		t.Errorf("yamllint max: %v", v)
	}
	if v, src := s.ParamFrom([]string{"yamllint:line-length.max", "editorconfig:max_line_length.max"}, "a.yaml"); v == nil || src != ".yamllint" {
		t.Errorf("ParamFrom: %v %s", v, src)
	}
	if v, _ := s.Param([]string{"eslint:max-len"}, "a.js", "code"); v.(float64) != 120 {
		t.Errorf("eslint max-len: %v", v)
	}
	if v, _ := s.Param([]string{"detekt:MaxLineLength"}, "A.kt", "maxLineLength"); v.(float64) != 140 {
		t.Errorf("detekt: %v", v)
	}
	if v, _ := s.Param([]string{"ruff:E501"}, "a.py", "max"); v.(float64) != 100 {
		t.Errorf("ruff line-length: %v", v)
	}
	s.ConfigOff = true
	if v, _ := s.ParamFrom([]string{"yamllint:line-length.max"}, "a.yaml"); v != nil {
		t.Error("ConfigOff must ignore params")
	}
}

func TestInline(t *testing.T) {
	cases := []struct {
		name, path, src, rule string
		eq                    []string
		line                  int
		want                  bool
	}{
		{"eslint next-line", "a.js", "// eslint-disable-next-line no-eval -- legacy\neval(x)\neval(y)", "JS-SEC-EVAL-001", []string{"eslint:no-eval"}, 2, true},
		{"eslint next-line only", "a.js", "// eslint-disable-next-line no-eval\neval(x)\neval(y)", "JS-SEC-EVAL-001", []string{"eslint:no-eval"}, 3, false},
		{"eslint other rule", "a.js", "eval(x) // eslint-disable-line no-console", "JS-SEC-EVAL-001", []string{"eslint:no-eval"}, 1, false},
		{"eslint same line all", "a.js", "eval(x) // eslint-disable-line", "JS-SEC-EVAL-001", []string{"eslint:no-eval"}, 1, true},
		{"eslint block", "a.ts", "/* eslint-disable @typescript-eslint/no-explicit-any */\nlet a: any\n/* eslint-enable */\nlet b: any", "TS-QUAL-ANY-001", []string{"typescript-eslint:@typescript-eslint/no-explicit-any"}, 2, true},
		{"eslint block ended", "a.ts", "/* eslint-disable @typescript-eslint/no-explicit-any */\nlet a: any\n/* eslint-enable */\nlet b: any", "TS-QUAL-ANY-001", []string{"typescript-eslint:@typescript-eslint/no-explicit-any"}, 4, false},
		{"nolint linter", "a.go", "ctx, _ := context.WithCancel(p) //nolint:govet // reason", "GO-QUAL-VET-LOSTCANCEL", []string{"govet:lostcancel"}, 1, true},
		{"nolint other linter", "a.go", "ctx, _ := context.WithCancel(p) //nolint:errcheck", "GO-QUAL-VET-LOSTCANCEL", []string{"govet:lostcancel"}, 1, false},
		{"nolint decl", "a.go", "//nolint:gosec\nfunc f() {\n\tr := rand.Intn(3)\n}\nfunc g() { rand.Intn(1) }", "GO-SEC-MATH-RAND-SECURITY", []string{"gosec:G404"}, 3, true},
		{"nolint decl end", "a.go", "//nolint:gosec\nfunc f() {\n\tr := rand.Intn(3)\n}\nfunc g() { rand.Intn(1) }", "GO-SEC-MATH-RAND-SECURITY", []string{"gosec:G404"}, 5, false},
		{"nosec go", "a.go", "x := rand.Intn(3) // #nosec G404", "GO-SEC-MATH-RAND-SECURITY", []string{"gosec:G404"}, 1, true},
		{"lint:ignore", "a.go", "//lint:ignore SA1019 legacy\nioutil.ReadAll(r)", "GO-MIG-IOUTIL", []string{"staticcheck:SA1019"}, 2, true},
		{"noqa code", "a.py", "eval(x)  # noqa: S307", "PY-SEC-EVAL", []string{"ruff:S307", "bandit:B307"}, 1, true},
		{"noqa other", "a.py", "eval(x)  # noqa: E501", "PY-SEC-EVAL", []string{"ruff:S307"}, 1, false},
		{"noqa bare", "a.py", "eval(x)  # noqa", "PY-SEC-EVAL", []string{"ruff:S307"}, 1, true},
		{"nosec py", "a.py", "eval(x)  # nosec B307", "PY-SEC-EVAL", []string{"bandit:B307"}, 1, true},
		{"ruff file noqa", "a.py", "# ruff: noqa: S307\n\neval(x)", "PY-SEC-EVAL", []string{"ruff:S307"}, 3, true},
		{"pylint block", "a.py", "def f():\n    # pylint: disable=unspecified-encoding\n    open(p)\n    open(q)\ndef g():\n    open(r)", "PY-QUAL-OPEN-NO-ENCODING", []string{"pylint:W1514/unspecified-encoding"}, 4, true},
		{"pylint block ends", "a.py", "def f():\n    # pylint: disable=unspecified-encoding\n    open(p)\ndef g():\n    open(r)", "PY-QUAL-OPEN-NO-ENCODING", []string{"pylint:W1514/unspecified-encoding"}, 5, false},
		{"type ignore", "a.py", "x: int = f()  # type: ignore[assignment]", "PY-X", []string{"mypy:assignment"}, 1, true},
		{"SuppressWarnings method", "A.java", "class A {\n  @SuppressWarnings(\"PMD.AvoidPrintStackTrace\")\n  void f() {\n    e.printStackTrace();\n  }\n  void g() { e.printStackTrace(); }\n}", "JAVA-SEC-PRINTSTACK-001", []string{"pmd:AvoidPrintStackTrace"}, 4, true},
		{"SuppressWarnings scope", "A.java", "class A {\n  @SuppressWarnings(\"PMD.AvoidPrintStackTrace\")\n  void f() {\n    e.printStackTrace();\n  }\n  void g() { e.printStackTrace(); }\n}", "JAVA-SEC-PRINTSTACK-001", []string{"pmd:AvoidPrintStackTrace"}, 6, false},
		{"SuppressWarnings errorprone", "A.java", "@SuppressWarnings({\"StringEquality\", \"unchecked\"})\nboolean f() { return a == \"x\"; }", "JAVA-QUAL-COR-STRING-EQ-001", []string{"errorprone:StringEquality"}, 2, true},
		{"checkstyle annotation", "A.java", "@SuppressWarnings(\"checkstyle:emptycatchblock\")\nvoid f() { try { x(); } catch (E e) {} }", "J", []string{"checkstyle:EmptyCatchBlock"}, 2, true},
		{"kotlin Suppress detekt", "A.kt", "@Suppress(\"UnsafeCallOnNullableType\")\nfun f() {\n  x!!.y\n}", "KT-QUAL-NOT-NULL-ASSERTION", []string{"detekt:UnsafeCallOnNullableType"}, 3, true},
		{"phpcs ignore", "a.php", "<?php\n// phpcs:ignore Squiz.PHP.Eval -- legacy\neval($x);", "PHP-SEC-EVAL", []string{"phpcs:Squiz.PHP.Eval"}, 3, true},
		{"phpcs disable range", "a.php", "<?php\n// phpcs:disable\neval($x);\n// phpcs:enable\neval($y);", "PHP-SEC-EVAL", []string{"phpcs:Squiz.PHP.Eval"}, 5, false},
		{"psalm suppress", "a.php", "<?php\n/** @psalm-suppress ForbiddenCode */\nfunction f() {\n  eval($x);\n}", "PHP-SEC-EVAL", []string{"psalm:ForbiddenCode"}, 4, true},
		{"phpstan next line", "a.php", "<?php\n// @phpstan-ignore-next-line\n$x = f();", "P", []string{"phpstan:argument.type"}, 3, true},
		{"hadolint", "Dockerfile", "# hadolint ignore=DL3006,DL3007\nFROM node:latest\nFROM python:latest", "DOCKER-QUAL-LATEST-TAG", []string{"hadolint:DL3006", "hadolint:DL3007"}, 2, true},
		{"hadolint next only", "Dockerfile", "# hadolint ignore=DL3007\nFROM node:latest\nFROM python:latest", "DOCKER-QUAL-LATEST-TAG", []string{"hadolint:DL3007"}, 3, false},
		{"hadolint global", "Dockerfile", "# hadolint global ignore=DL3007\nFROM node:latest\nFROM python:latest", "DOCKER-QUAL-LATEST-TAG", []string{"hadolint:DL3007"}, 3, true},
		{"docker check skip", "Dockerfile", "# syntax=docker/dockerfile:1\n# check=skip=StageNameCasing\nFROM a AS Build", "DOCKER-QUAL-STAGE-NAME-CASING", []string{"docker-build-check:StageNameCasing"}, 3, true},
		{"tflint block", "main.tf", "# tflint-ignore: terraform_typed_variables\nvariable \"x\" {\n  default = 1\n}\nvariable \"y\" {}", "TF-QUAL-TYPED-VARIABLES", []string{"tflint:terraform_typed_variables"}, 2, true},
		{"tflint block end", "main.tf", "# tflint-ignore: terraform_typed_variables\nvariable \"x\" {\n  default = 1\n}\nvariable \"y\" {}", "TF-QUAL-TYPED-VARIABLES", []string{"tflint:terraform_typed_variables"}, 5, false},
		{"checkov resource", "main.tf", "resource \"aws_s3_bucket\" \"b\" {\n  #checkov:skip=CKV_AWS_18:logging elsewhere\n  bucket = \"x\"\n}", "TF-X", []string{"checkov:CKV_AWS_18"}, 3, true},
		{"yamllint disable-line", "a.yaml", "# yamllint disable-line rule:truthy\non: push\noff: x", "YAML-QUAL-TRUTHY", []string{"yamllint:truthy"}, 2, true},
		{"yamllint range", "a.yaml", "# yamllint disable rule:truthy\non: push\n# yamllint enable rule:truthy\noff: x", "YAML-QUAL-TRUTHY", []string{"yamllint:truthy"}, 4, false},
		{"yamllint file", "a.yaml", "# yamllint disable-file\non: push", "YAML-QUAL-TRUTHY", []string{"yamllint:truthy"}, 2, true},
		{"buf ignore", "a.proto", "// buf:lint:ignore SERVICE_SUFFIX\nservice Foo {\n  rpc A(B) returns (C);\n}", "PROTO-QUAL-SERVICE-SUFFIX", []string{"buf:SERVICE_SUFFIX"}, 2, true},
		{"crev same line", "a.go", "x := 1 // crev-ignore GO-X", "GO-X", nil, 1, true},
		{"crev line above", "a.go", "// crev-ignore GO-X\nx := 1", "GO-X", nil, 2, true},
		{"crev next-line", "a.go", "// crev-ignore-next-line GO-X\nx := 1\ny := 2", "GO-X", nil, 3, false},
		{"crev file", "a.go", "// crev-ignore-file GO-X\n\n\nx := 1", "GO-X", nil, 4, true},
		{"crev other id", "a.go", "x := 1 // crev-ignore GO-Y", "GO-X", nil, 1, false},
	}
	for _, c := range cases {
		got := ParseInline(c.path, []byte(c.src)).Match(c.path, c.rule, c.eq, c.line, c.line)
		if (got != nil) != c.want {
			t.Errorf("%s: suppressed=%v want %v (%+v)", c.name, got != nil, c.want, got)
		}
	}
	all := ParseInline("a.js", []byte("// eslint-disable-next-line no-eval -- legacy\neval(x)\n")).All()
	if len(all) != 1 || all[0].Crev || all[0].From != 2 || all[0].To != 2 || !slices.Contains(all[0].IDs, "no-eval") {
		t.Fatalf("All: %+v", all)
	}
}

func TestCheckRespectsConfigOff(t *testing.T) {
	root := t.TempDir()
	files := write(t, root, map[string]string{".hadolint.yaml": "ignored: [DL3007]\n"})
	s := Discover(root, files)
	src := []byte("FROM node:latest # hadolint ignore=DL3007\n# crev-ignore DOCKER-QUAL-LATEST-TAG\nFROM x:latest\n")
	eq := []string{"hadolint:DL3007"}
	if sb := s.Check("Dockerfile", src, "DOCKER-QUAL-LATEST-TAG", eq, 1, 1); sb == nil || sb.Kind != "config" || sb.Source != ".hadolint.yaml" {
		t.Fatalf("config: %+v", sb)
	}
	off := Discover(root, files)
	off.ConfigOff = true
	if sb := off.Check("Dockerfile", src, "DOCKER-QUAL-LATEST-TAG", eq, 1, 1); sb != nil {
		t.Fatalf("ConfigOff must ignore config and linter inline disables: %+v", sb)
	}
	if sb := off.Check("Dockerfile", src, "DOCKER-QUAL-LATEST-TAG", eq, 3, 3); sb == nil || sb.Kind != "crev-ignore" {
		t.Fatalf("crev-ignore must still apply: %+v", sb)
	}
}

func TestTOML(t *testing.T) {
	m, err := parseTOML("a = 1\n[t.\"x y\"]\nb = [\n  'p', # c\n  \"q\",\n]\nc = { d = true, e.f = \"g\" }\ns = \"\"\"\nmulti\n\"\"\"\n[[arr]]\nn = 1\n[[arr]]\nn = 2\n")
	if err != nil {
		t.Fatal(err)
	}
	tx := m["t"].(map[string]any)["x y"].(map[string]any)
	if m["a"].(float64) != 1 || len(tx["b"].([]any)) != 2 || tx["c"].(map[string]any)["e"].(map[string]any)["f"] != "g" || tx["s"] != "multi\n" || len(m["arr"].([]any)) != 2 {
		t.Fatalf("%#v", m)
	}
}

func TestThresholdParams(t *testing.T) {
	root := t.TempDir()
	files := write(t, root, map[string]string{
		"pyproject.toml": "[tool.ruff.lint.mccabe]\nmax-complexity = 12\n[tool.ruff.lint.pylint]\nmax-args = 7\nmax-returns = 4\n[tool.pylint.design]\nmax-branches = 20\n",
		".golangci.yml":  "version: \"2\"\nlinters:\n  settings:\n    gocognit:\n      min-complexity: 25\n    nestif:\n      min-complexity: 6\n",
	})
	s := Discover(root, files)
	for from, want := range map[string]any{
		"ruff:C901.max":                12,
		"ruff:PLR0913.max":             7,
		"ruff:PLR0911.max":             4,
		"pylint:too-many-branches.max": 20,
		"gocognit:*.min-complexity":    25,
		"nestif:*.min-complexity":      6,
	} {
		v, _ := s.ParamFrom([]string{from}, "a/b.py")
		if toString(v) != toString(want) {
			t.Errorf("%s = %v, want %v (errors %v)", from, v, want, s.Errors)
		}
	}
}

func TestStylelintConfig(t *testing.T) {
	dir := t.TempDir()
	files := write(t, dir, map[string]string{
		"package.json":             `{"name":"x","eslintConfig":{"rules":{"no-var":"error"}},"stylelint":{"rules":{"declaration-no-important":true}}}`,
		"web/stylelint.config.mjs": "export default { extends: 'stylelint-config-standard', rules: { 'block-no-empty': null } };\n",
	})
	s := Discover(dir, files)
	if !s.Enables([]string{"stylelint:declaration-no-important"}, "a.css") || !s.Enables([]string{"eslint:no-var"}, "a.js") {
		t.Fatal("package.json: both tools must be read")
	}
	if !s.Enables([]string{"stylelint:property-no-vendor-prefix"}, "web/a.css") {
		t.Fatal("extends stylelint-config-standard")
	}
	if d := s.Decide([]string{"stylelint:block-no-empty"}, "web/a.css"); d == nil || !d.Off {
		t.Fatal("null turns a rule off")
	}
}

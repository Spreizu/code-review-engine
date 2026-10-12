package engine

import "testing"

func TestShadowRulesAreNotReported(t *testing.T) {
	rs := catalogRules(t, "YAML-QUAL-TRUTHY")
	root := t.TempDir()
	write(t, root, ".yamllint", "extends: default\n")
	write(t, root, "a.yaml", "on: yes\n")
	rep, _ := Scan(Options{Root: root, Rules: rs, Latest: latest})
	if len(rep.Findings) != 1 {
		t.Fatalf("active rule: %d findings", len(rep.Findings))
	}
	sh := map[string]string{"YAML-QUAL-TRUTHY": "quarantined"}
	rep, _ = Scan(Options{Root: root, Rules: rs, Latest: latest, Shadow: sh})
	if len(rep.Findings) != 0 || rep.Shadow["YAML-QUAL-TRUTHY"] != 1 {
		t.Fatalf("shadow rule must be counted, not reported: %d findings, shadow=%v", len(rep.Findings), rep.Shadow)
	}
	rep, _ = Scan(Options{Root: root, Rules: rs, Latest: latest, Shadow: sh, IncludeShadow: true})
	if len(rep.Findings) != 1 || rep.Findings[0].Status != "shadow" {
		t.Fatalf("--include-shadow keeps them with status shadow: %+v", rep.Findings)
	}
}

func TestOptInRulesNeedProjectEnable(t *testing.T) {
	rs := catalogRules(t, "JS-QUAL-CURLY")
	if !rs[0].OptIn {
		t.Fatal("JS-QUAL-CURLY should be opt-in (eslint curly is not in eslint:recommended)")
	}
	root := t.TempDir()
	write(t, root, "a.js", "if (ok) run()\n")
	rep, _ := Scan(Options{Root: root, Rules: rs, Latest: latest, RespectProjectConfig: true})
	if len(rep.Findings) != 0 || rep.Stats["opt_in_not_enabled"] != 1 {
		t.Fatalf("opt-in rule without project enable: %d findings, stats %v", len(rep.Findings), rep.Stats)
	}
	rep, _ = Scan(Options{Root: root, Rules: rs, Latest: latest, Enabled: map[string]bool{"JS-QUAL-CURLY": true}})
	if len(rep.Findings) != 1 {
		t.Fatalf(".crev.yaml enabled: %d findings", len(rep.Findings))
	}
	write(t, root, ".eslintrc.json", `{"rules": {"curly": "error"}}`)
	rep, _ = Scan(Options{Root: root, Rules: rs, Latest: latest, RespectProjectConfig: true})
	if len(rep.Findings) != 1 {
		t.Fatalf("eslint enables curly: %d findings, stats %v", len(rep.Findings), rep.Stats)
	}
	write(t, root, ".eslintrc.json", `{"rules": {"curly": "off"}}`)
	rep, _ = Scan(Options{Root: root, Rules: rs, Latest: latest, RespectProjectConfig: true})
	if len(rep.Findings) != 0 {
		t.Fatalf("eslint curly off: %d", len(rep.Findings))
	}
}

// Corpus FP (vitesse/cypress): a sub-unit that only has a tsconfig must inherit the root's
// TypeScript version, not be assumed latest.
func TestSubUnitInheritsVersionInsteadOfAssumingLatest(t *testing.T) {
	rs := catalogRules(t, "TS-MIG-VUE-TS7-001")
	root := t.TempDir()
	write(t, root, "package.json", `{"devDependencies": {"typescript": "6.0.3", "vue-tsc": "^3.0.0", "vue": "3.5.0"}}`)
	write(t, root, "e2e/tsconfig.json", `{"compilerOptions": {"types": ["cypress"]}}`)
	write(t, root, "e2e/a.ts", "export const a = 1\n")
	rep, _ := Scan(Options{Root: root, Rules: rs, Latest: map[string]string{"typescript": "7.0.2", "vue": "3.5.0", "ecmascript": "2026"}})
	if len(rep.Findings) != 0 {
		t.Fatalf("sub-unit assumed latest TypeScript: %+v units %v", rep.Findings[0], rep.Units)
	}
}

func TestExcludeTestsGovernance(t *testing.T) {
	rs := catalogRules(t, "PY-QUAL-REQUESTS-NO-TIMEOUT")
	if !rs[0].Detection.ExcludeTests {
		t.Fatal("governance exclude_tests not applied")
	}
	root := t.TempDir()
	src := "import requests\n\nr = requests.get(URL)\n"
	write(t, root, "app.py", src)
	write(t, root, "tests/test_api.py", src)
	rep, _ := Scan(Options{Root: root, Rules: rs, Latest: map[string]string{"python": "3.14"}})
	if len(rep.Findings) != 1 || rep.Findings[0].Location.Path != "app.py" {
		t.Fatalf("want only app.py, got %d findings", len(rep.Findings))
	}
}

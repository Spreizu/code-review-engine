package projcfg

import "testing"

func TestOxlintConfig(t *testing.T) {
	root := t.TempDir()
	files := write(t, root, map[string]string{
		"configs/base.json": `{ "rules": { "no-plusplus": "error" }, "ignorePatterns": ["generated/**"] }`,
		".oxlintrc.json": `{
  // jsonc comments are allowed
  "extends": ["./configs/base.json"],
  "plugins": ["typescript", "vue", "react"],
  "categories": { "correctness": "error", "style": "warn", "suspicious": "off" },
  "rules": {
    "no-console": "deny",
    "typescript/no-explicit-any": ["allow"],
    "react-hooks/exhaustive-deps": "error",
    "@typescript-eslint/no-unused-vars": "off",
    "eslint/curly": "off"
  },
  "overrides": [{ "files": ["scripts/*.js"], "rules": { "no-console": "off" } }]
}`,
	})
	s := Discover(root, files)
	if len(s.Errors) > 0 {
		t.Fatal(s.Errors)
	}
	cases := []struct {
		eq   []string
		rel  string
		want bool
	}{
		{[]string{"eslint:no-console"}, "src/a.js", true},
		{[]string{"oxlint:eslint/no-console"}, "src/a.js", true},
		{[]string{"eslint:no-console"}, "scripts/x.js", false},                            // override
		{[]string{"typescript-eslint:@typescript-eslint/no-explicit-any"}, "a.ts", false}, // allow
		{[]string{"react-hooks:react-hooks/exhaustive-deps"}, "a.tsx", true},              // alias to react plugin
		{[]string{"eslint:no-plusplus"}, "a.js", true},                                    // extends
		{[]string{"eslint:no-plusplus"}, "generated/a.js", false},                         // ignorePatterns
		{[]string{"eslint:curly"}, "a.js", false},                                         // style category on, rule off
		{[]string{"eslint:no-debugger"}, "a.js", true},                                    // correctness category
		{[]string{"eslint-plugin-vue:vue/no-export-in-script-setup"}, "a.vue", true},      // vue plugin correctness
		{[]string{"unicorn:unicorn/no-thenable"}, "a.js", false},                          // plugins replaced the defaults (no unicorn)
	}
	for _, c := range cases {
		if got := s.Enables(c.eq, c.rel); got != c.want {
			t.Errorf("Enables(%v, %s) = %v, want %v", c.eq, c.rel, got, c.want)
		}
	}
	if d := s.Decide([]string{"typescript-eslint:@typescript-eslint/no-unused-vars"}, "a.ts"); d == nil || !d.Off {
		t.Errorf("no-unused-vars should be off: %+v", d)
	}
}

func TestOxlintInlineDisable(t *testing.T) {
	src := "// oxlint-disable-next-line typescript/no-explicit-any\nlet a: any\n/* oxlint-disable no-console */\nconsole.log(1)\n"
	fi := ParseInline("a.ts", []byte(src))
	if fi.Match("a.ts", "TS-QUAL-ANY-001", []string{"typescript-eslint:@typescript-eslint/no-explicit-any"}, 2, 2) == nil {
		t.Error("oxlint-disable-next-line typescript/no-explicit-any not honoured for the typescript-eslint equivalent")
	}
	if fi.Match("a.ts", "JS-QUAL-NO-CONSOLE", []string{"oxlint:eslint/no-console"}, 4, 4) == nil {
		t.Error("oxlint-disable no-console not honoured for the oxlint equivalent")
	}
	if fi.Match("a.ts", "JS-QUAL-NO-CONSOLE", []string{"eslint:no-console"}, 2, 2) != nil {
		t.Error("disable must not leak to other lines")
	}
}

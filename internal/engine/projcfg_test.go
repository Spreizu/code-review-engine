package engine

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	catalog "github.com/elmo/code-review-engine/rules"

	"github.com/elmo/code-review-engine/internal/rules"
)

func catalogRules(t *testing.T, ids ...string) []*rules.Rule {
	t.Helper()
	all, err := rules.LoadFS(catalog.FS, "packs/*/*.yaml")
	if err != nil {
		t.Fatal(err)
	}
	if err := rules.ApplyData(all, catalog.FS); err != nil {
		t.Fatal(err)
	}
	want := map[string]bool{}
	for _, id := range ids {
		want[id] = true
	}
	var out []*rules.Rule
	for _, r := range all {
		if want[r.ID] {
			out = append(out, r)
		}
	}
	if len(out) != len(ids) {
		t.Fatalf("rules %v: found %d", ids, len(out))
	}
	return out
}

func TestProjectConfigSuppression(t *testing.T) {
	root := t.TempDir()
	write(t, root, "package.json", `{"name":"x","dependencies":{}}`)
	write(t, root, "eslint.config.js", `export default [{ files: ["legacy/**"], rules: { "no-eval": "off" } }];`)
	write(t, root, "legacy/a.js", "eval(input)\n")
	write(t, root, "src/b.js", "eval(input)\n")
	write(t, root, "src/c.js", "eval(input) // eslint-disable-line no-eval\n")
	write(t, root, "src/d.js", "eval(input) // crev-ignore JS-SEC-EVAL-001\n")
	rs := catalogRules(t, "JS-SEC-EVAL-001")
	if len(rs[0].Equivalents) == 0 {
		t.Fatal("JS-SEC-EVAL-001 should map to eslint:no-eval")
	}
	rep, err := Scan(Options{Root: root, Rules: rs, RespectProjectConfig: true, Latest: latest})
	if err != nil {
		t.Fatal(err)
	}
	if len(rep.Findings) == 0 {
		t.Fatalf("no findings: errors=%v stats=%v units=%v", rep.Errors, rep.Stats, rep.Units)
	}
	got := map[string]string{}
	for _, f := range rep.Findings {
		k := f.Status
		if f.SuppressedBy != nil {
			k += ":" + f.SuppressedBy.Kind + ":" + f.SuppressedBy.Source
		}
		got[f.Location.Path] = k
	}
	if got["legacy/a.js"] != "suppressed:config:eslint.config.js" || !strings.HasPrefix(got["src/b.js"], "confirmed") ||
		!strings.HasPrefix(got["src/c.js"], "suppressed:inline:src/c.js:1") || !strings.HasPrefix(got["src/d.js"], "suppressed:crev-ignore") {
		t.Fatalf("%v", got)
	}
	if rep.ProjectConfig == nil || len(rep.ProjectConfig.Sources) != 1 || rep.Stats["suppressed_config"] != 1 || rep.Stats["suppressed_inline"] != 1 {
		t.Fatalf("project config summary: %+v %v", rep.ProjectConfig, rep.Stats)
	}
	// respect_project_config: false -> only crev-ignore applies; "report everything" otherwise
	rep, _ = Scan(Options{Root: root, Rules: rs, Latest: latest})
	n := 0
	for _, f := range rep.Findings {
		if f.Status == "suppressed" {
			n++
			if f.SuppressedBy.Kind != "crev-ignore" {
				t.Fatalf("unexpected suppression with project config off: %+v", f.SuppressedBy)
			}
		}
	}
	if n != 1 || len(rep.Findings) != 4 {
		t.Fatalf("config off: %d suppressed of %d", n, len(rep.Findings))
	}
}

func TestProjectConfigParams(t *testing.T) {
	long := "description: " + strings.Repeat("word ", 19) + "end\n" // ~ 100 chars
	rs := catalogRules(t, "YAML-QUAL-LINE-LENGTH")
	root := t.TempDir()
	write(t, root, "a.yaml", long)
	rep, _ := Scan(Options{Root: root, Rules: rs, RespectProjectConfig: true, Latest: latest})
	if len(rep.Findings) != 0 || rep.Stats["rules_unconfigured"] != 1 {
		t.Fatalf("style rule must not run without a yamllint/editorconfig config (requires_config): %+v", rep.Findings)
	}
	write(t, root, ".editorconfig", "root = true\n\n[*]\nindent_style = space\n")
	if rep, _ = Scan(Options{Root: root, Rules: rs, RespectProjectConfig: true, Latest: latest}); len(rep.Findings) != 0 {
		t.Fatalf(".editorconfig without max_line_length does not adopt a line limit: %+v", rep.Findings)
	}
	write(t, root, ".editorconfig", "root = true\n\n[*]\nmax_line_length = 80\n")
	rep, _ = Scan(Options{Root: root, Rules: rs, RespectProjectConfig: true, Latest: latest})
	if len(rep.Findings) != 1 || !strings.Contains(rep.Findings[0].Title, "80") {
		t.Fatalf("default max: %+v", rep.Findings)
	}
	os.Remove(filepath.Join(root, ".editorconfig"))
	write(t, root, ".yamllint", "rules:\n  line-length:\n    max: 120\n")
	rep, _ = Scan(Options{Root: root, Rules: rs, RespectProjectConfig: true, Latest: latest})
	if len(rep.Findings) != 0 {
		t.Fatalf("yamllint max 120 should allow a 100 char line: %+v", rep.Findings)
	}
	write(t, root, ".yamllint", "rules:\n  line-length:\n    max: 90\n")
	rep, _ = Scan(Options{Root: root, Rules: rs, RespectProjectConfig: true, Latest: latest})
	if len(rep.Findings) != 1 || !strings.Contains(rep.Findings[0].Message, "longer than 90") {
		t.Fatalf("yamllint max 90: %+v", rep.Findings)
	}
	write(t, root, ".yamllint", "rules:\n  line-length: disable\n")
	rep, _ = Scan(Options{Root: root, Rules: rs, RespectProjectConfig: true, Latest: latest})
	if len(rep.Findings) != 1 || rep.Findings[0].Status != "suppressed" {
		t.Fatalf("line-length disabled: %+v", rep.Findings)
	}
}

var latest = map[string]string{"ecmascript": "2025", "node": "24", "yaml": "1.2"}


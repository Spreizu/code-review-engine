package ai

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/rules"
)

func TestScrub(t *testing.T) {
	in := `password = "hunter2hunter2"` + "\nAKIAABCDEFGHIJKLMNOP\nAuthorization: Bearer abcdefghijklmnopqrstuvwxyz123"
	out := Scrub(in)
	for _, s := range []string{"hunter2", "AKIAABCDEFGHIJKLMNOP", "abcdefghijklmnopqrstuvwxyz123"} {
		if strings.Contains(out, s) {
			t.Fatalf("secret %q not scrubbed: %s", s, out)
		}
	}
}

func TestScrubKeepsCode(t *testing.T) {
	for _, in := range []string{
		"fun login(user: String, password: String): Boolean {",
		"fun f(password: String?)",
		"val token: Map<String, String>",
		"password = req.password",
		"token = os.getenv(\"TOKEN\")",
		"String password = request.getParameter(\"pwd\");",
		"secret := cfg.Secret",
	} {
		if out := Scrub(in); out != in {
			t.Errorf("code mangled: %q -> %q", in, out)
		}
	}
	for _, in := range []string{"password=hunter22", "api_key: ab12cd34ef", `token = 'abcdefgh'`, `secret: "plainword"`} {
		if out := Scrub(in); !strings.Contains(out, "«redacted»") {
			t.Errorf("secret kept: %q", out)
		}
	}
}

func TestParseVerdictShapes(t *testing.T) {
	for _, in := range []string{
		`{"batch_id":"b","results":[{"id":"a","verdict":"confirmed","confidence":"high"}]}`,
		`[{"id":"a","verdict":"confirmed","confidence":"high"}]`,
		"{\"id\":\"a\",\"verdict\":\"confirmed\",\"confidence\":\"high\"}\n",
	} {
		vs, err := ParseVerdicts([]byte(in))
		if err != nil || len(vs) != 1 || vs[0].ID != "a" {
			t.Fatalf("%s: %v %v", in, vs, err)
		}
	}
}

func TestPendingDedupAndBatching(t *testing.T) {
	dir := t.TempDir()
	src := "class A {\n  String f(Optional<String> o) { return o.get(); }\n}\n"
	for _, n := range []string{"A.java", "B.java"} {
		_ = os.WriteFile(filepath.Join(dir, n), []byte(src), 0o644)
	}
	r := &rules.Rule{ID: "JAVA-QUAL-OPT-002", Title: "t", Message: "m", AIQuestion: "q?", RuleVersion: 1}
	rep := &findings.Report{}
	for i, n := range []string{"A.java", "B.java"} {
		rep.Findings = append(rep.Findings, &findings.Finding{ID: strings.Repeat(string(rune('a'+i)), 32), RuleID: r.ID, Status: "pending_ai",
			Location: findings.Location{Path: n, StartLine: 2, EndLine: 2}})
	}
	byID := map[string]*rules.Rule{r.ID: r}
	items := Pending(rep, byID, BuildOptions{Root: dir, ContextLines: 1, MaxChars: 1000})
	if len(items) != 1 || len(items[0].Dups) != 1 {
		t.Fatalf("identical code windows should collapse into one item with one dup: %+v", items)
	}
	bs := Batches(items, byID, rep, BuildOptions{BatchSize: 10})
	if len(bs) != 1 || len(bs[0].Rules) != 1 {
		t.Fatalf("batches: %+v", bs)
	}
	c := Cache{Dir: t.TempDir()}
	st := Ingest(items, []Verdict{{ID: items[0].ID, Verdict: "rejected", Confidence: "high"}}, c, "cursor-skill")
	if st.Applied != 1 || rep.Findings[0].Status != "ai_rejected" || rep.Findings[1].Status != "ai_rejected" {
		t.Fatalf("ingest should fan out to duplicates: %+v %s %s", st, rep.Findings[0].Status, rep.Findings[1].Status)
	}
	for _, f := range rep.Findings {
		f.Status = "pending_ai"
	}
	items = Pending(rep, byID, BuildOptions{Root: dir, ContextLines: 1, MaxChars: 1000})
	if rest, hits := FromCache(items, c); len(rest) != 0 || hits != 1 {
		t.Fatalf("cache miss: rest=%d hits=%d", len(rest), hits)
	}
}

func TestWindowOutlinesLongMatch(t *testing.T) {
	var src []string
	src = append(src, "package p;", "final class Big {", "  private final int a;", "  private final int b;")
	for i := 0; i < 60; i++ {
		src = append(src, "  void m"+strconv.Itoa(i)+"() {", "    work();", "  }")
	}
	src = append(src, "  public int hashCode() { return a; }", "}")
	code, _, _ := window(src, 2, len(src), 6, 100000)
	if strings.Contains(code, "work();") && strings.Count(code, "work();") > 6 {
		t.Fatalf("method bodies not elided:\n%s", code)
	}
	for _, want := range []string{"final class Big {", "private final int b;", "void m59() {", "hashCode"} {
		if !strings.Contains(code, want) {
			t.Fatalf("outline lacks %q:\n%s", want, code)
		}
	}
}

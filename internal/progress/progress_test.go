package progress

import (
	"bytes"
	"os"
	"strings"
	"testing"
	"time"
)

func TestResolve(t *testing.T) {
	t.Setenv("CI", "")
	t.Setenv("GITHUB_ACTIONS", "")
	f, _ := os.CreateTemp(t.TempDir(), "x") // a regular file is not a TTY
	if Resolve("auto", false, f) != Off || Resolve("bar", true, f) != Off || Resolve("plain", false, f) != Plain || Resolve("bar", false, f) != Bar {
		t.Fatal("resolve")
	}
	t.Setenv("CI", "true")
	if Resolve("auto", false, os.Stderr) != Off {
		t.Fatal("CI must disable auto progress")
	}
	if New(f, Off) != nil {
		t.Fatal("off => nil reporter")
	}
	var r *Reporter
	r.Update(Event{Phase: "rules"}) // nil-safe
	r.Finish()
}

func TestLineAndPlain(t *testing.T) {
	var buf bytes.Buffer
	clock := time.Unix(0, 0)
	r := New(&buf, Plain)
	r.now = func() time.Time { return clock }
	r.start = clock
	r.Update(Event{Phase: "rules", Done: 0, Total: 10})
	clock = clock.Add(2 * time.Second)
	r.Update(Event{Phase: "rules", Done: 5, Total: 10, Current: "src/a.go", Findings: 3}) // throttled (5s)
	if got := r.Line(clock); !strings.Contains(got, "[4/6] parse/rules") || !strings.Contains(got, " 50% 5/10 ETA 2s") || !strings.Contains(got, "3 findings | src/a.go") {
		t.Fatalf("line: %q", got)
	}
	r.Update(Event{Phase: "report", Findings: 3})
	r.Finish()
	out := buf.String()
	if strings.Count(out, "\n") != 4 || !strings.Contains(out, "100% 10/10") || strings.Contains(out, "\r") {
		t.Fatalf("plain output:\n%s", out)
	}
}

func TestBarRedraw(t *testing.T) {
	var buf bytes.Buffer
	r := New(&buf, Bar)
	r.Update(Event{Phase: "discover", Done: 120, Current: "a/very/long/path.ts"})
	r.Update(Event{Phase: "rules", Done: 1, Total: 4})
	r.Finish()
	if !strings.Contains(buf.String(), "\r[4/6] parse/rules") || !strings.Contains(buf.String(), "█") || strings.Contains(buf.String(), "\n") {
		t.Fatalf("bar: %q", buf.String())
	}
}

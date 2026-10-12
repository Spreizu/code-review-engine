package scope

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func run(t *testing.T, dir string, args ...string) string {
	t.Helper()
	cmd := exec.Command("git", args...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(), "GIT_AUTHOR_NAME=t", "GIT_AUTHOR_EMAIL=t@t", "GIT_COMMITTER_NAME=t", "GIT_COMMITTER_EMAIL=t@t", "GIT_CONFIG_GLOBAL=/dev/null")
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v: %v %s", args, err, out)
	}
	return strings.TrimSpace(string(out))
}

func write(t *testing.T, dir, name, body string) {
	t.Helper()
	p := filepath.Join(dir, name)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func repo(t *testing.T) string {
	if _, err := exec.LookPath("git"); err != nil {
		t.Skip("git not installed")
	}
	d := t.TempDir()
	run(t, d, "init", "-q", "-b", "main")
	write(t, d, "a.go", "package a\n\nfunc A() {}\n\nfunc B() {}\n")
	write(t, d, "gone.go", "package a\n")
	run(t, d, "add", ".")
	run(t, d, "commit", "-qm", "init")
	run(t, d, "checkout", "-qb", "feature")
	write(t, d, "a.go", "package a\n\nfunc A() {}\n\nfunc B() {}\n\nfunc C() {}\n")
	write(t, d, "b.go", "package a\n\nfunc D() {}\n")
	run(t, d, "rm", "-q", "gone.go")
	run(t, d, "add", ".")
	run(t, d, "commit", "-qm", "feature")
	return d
}

func TestBaseScope(t *testing.T) {
	d := repo(t)
	// main moves on after the branch point: merge-base semantics must ignore it.
	run(t, d, "checkout", "-q", "main")
	write(t, d, "main_only.go", "package a\n")
	run(t, d, "add", ".")
	run(t, d, "commit", "-qm", "main moves")
	run(t, d, "checkout", "-q", "feature")
	s, err := Resolve(d, Options{Base: "main"})
	if err != nil {
		t.Fatal(err)
	}
	if s.Mode != "base" || s.MergeBase == "" || s.HeadSHA == "" {
		t.Fatalf("%+v", s)
	}
	if _, ok := s.Files["main_only.go"]; ok {
		t.Fatal("changes only on main leaked into the scope")
	}
	if !s.Deleted["gone.go"] || s.FileInScope("gone.go") {
		t.Fatalf("deleted file: %+v", s.Deleted)
	}
	if !s.InScope("a.go", 7, 7) || s.InScope("a.go", 3, 3) {
		t.Fatalf("hunk lines wrong: %+v", s.Files["a.go"])
	}
	if !s.InScope("b.go", 1, 3) || s.InScope("other.go", 1, 1) {
		t.Fatal("new file should be in scope, untouched file not")
	}
	s.DiffContext = "file"
	if !s.InScope("a.go", 3, 3) {
		t.Fatal("diff-context file should include whole changed files")
	}
}

func TestStagedWorkingTreeCommits(t *testing.T) {
	d := repo(t)
	write(t, d, "b.go", "package a\n\nfunc D() {}\n\nfunc E() {}\n")
	run(t, d, "add", "b.go")
	write(t, d, "a.go", "package a\n\n// changed\nfunc A() {}\n\nfunc B() {}\n\nfunc C() {}\n")
	write(t, d, "new.go", "package a\n")
	st, err := Resolve(d, Options{Staged: true})
	if err != nil {
		t.Fatal(err)
	}
	if !st.FileInScope("b.go") || st.FileInScope("a.go") || st.FileInScope("new.go") {
		t.Fatalf("staged: %+v", st.Files)
	}
	wt, err := Resolve(d, Options{WorkingTree: true})
	if err != nil {
		t.Fatal(err)
	}
	if !wt.FileInScope("a.go") || !wt.FileInScope("b.go") || !wt.InScope("new.go", 1, 1) {
		t.Fatalf("working tree: %+v", wt.Files)
	}
	c, err := Resolve(d, Options{Commits: "main..feature"})
	if err != nil {
		t.Fatal(err)
	}
	if c.Mode != "commits" || !c.FileInScope("b.go") || c.FileInScope("new.go") {
		t.Fatalf("commits: %+v", c.Files)
	}
	if _, err := Resolve(d, Options{Staged: true, WorkingTree: true}); err == nil {
		t.Fatal("two modes must be rejected")
	}
	if _, err := Resolve(d, Options{Base: "nope"}); err == nil {
		t.Fatal("unknown ref must be rejected")
	}
	if s, _ := Resolve(d, Options{}); s.IsDiff() || !s.InScope("x", 1, 1) {
		t.Fatal("default must be full")
	}
}

func TestParseDiffTopDeletionClamped(t *testing.T) {
	s := &Scope{Files: map[string][]Range{}, Added: map[string]bool{}}
	parseDiff("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1,4 +0,0 @@\n-a\n-b\n", s)
	if len(s.Files["x.py"]) == 0 {
		t.Fatal("no range parsed")
	}
	for _, r := range s.Files["x.py"] {
		if r.Start < 1 {
			t.Fatalf("range starts at %d", r.Start)
		}
	}
}

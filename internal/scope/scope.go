// Package scope computes which files/lines a scan reports on (full repo or a git diff).
//
// The scan always parses whole files (accurate tree-sitter context) and the repo index always
// covers the full tree; the scope only filters which findings are *reported*.
package scope

import (
	"bufio"
	"bytes"
	"fmt"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
)

// Range is an inclusive 1-based line range on the new side of a diff.
type Range struct{ Start, End int }

// Scope describes what a scan reports. Mode "full" reports everything.
type Scope struct {
	Mode        string `json:"mode"` // full | base | staged | working-tree | commits
	Base        string `json:"base,omitempty"`
	Head        string `json:"head,omitempty"`
	BaseSHA     string `json:"base_sha,omitempty"`
	HeadSHA     string `json:"head_sha,omitempty"` // empty = index (staged) or working tree
	MergeBase   string `json:"merge_base,omitempty"`
	DiffContext string `json:"diff_context,omitempty"` // hunk (default) | file
	// Files maps repo-relative changed paths to changed new-side line ranges (nil slice = whole file).
	Files   map[string][]Range `json:"-"`
	Deleted map[string]bool    `json:"-"`
	Added   map[string]bool    `json:"-"` // new files (diff against /dev/null or untracked)
	// ChangedFiles / DeletedFiles are recorded in run metadata.
	ChangedFiles int `json:"changed_files"`
	DeletedFiles int `json:"deleted_files"`
}

// Full is the default scope.
func Full() *Scope { return &Scope{Mode: "full"} }

// IsDiff reports whether findings are restricted to changes.
func (s *Scope) IsDiff() bool { return s != nil && s.Mode != "" && s.Mode != "full" }

// InScope reports whether a finding at path/lines should be reported.
func (s *Scope) InScope(path string, start, end int) bool {
	if !s.IsDiff() {
		return true
	}
	rs, ok := s.Files[path]
	if !ok {
		return false
	}
	if s.DiffContext == "file" || rs == nil {
		return true
	}
	if end < start {
		end = start
	}
	for _, r := range rs {
		if start <= r.End && end >= r.Start {
			return true
		}
	}
	return false
}

// IsAdded reports whether path is a new file in the diff.
func (s *Scope) IsAdded(path string) bool {
	if !s.IsDiff() {
		return false
	}
	if s.Added[path] {
		return true
	}
	rs, ok := s.Files[path]
	return ok && rs == nil
}

// Ranges returns the changed line ranges of path (nil when the whole file is in scope or it is unchanged).
func (s *Scope) Ranges(path string) []Range {
	if !s.IsDiff() {
		return nil
	}
	return s.Files[path]
}

// FileInScope reports whether a path has any change (or the scope is full).
func (s *Scope) FileInScope(path string) bool {
	if !s.IsDiff() {
		return true
	}
	_, ok := s.Files[path]
	return ok
}

// Options select the diff (at most one mode).
type Options struct {
	Base, Head  string // --base REF [--head REF]: merge-base(base, head)..head (head default HEAD)
	Staged      bool   // --staged: index vs HEAD
	WorkingTree bool   // --working-tree: working tree (staged + unstaged + untracked) vs HEAD
	Commits     string // --commits A..B (A...B = merge-base semantics)
	DiffContext string // hunk | file
}

// Resolve builds the scope by calling the git CLI in root.
func Resolve(root string, o Options) (*Scope, error) {
	n := 0
	for _, b := range []bool{o.Base != "", o.Staged, o.WorkingTree, o.Commits != ""} {
		if b {
			n++
		}
	}
	if o.Head != "" && o.Base == "" {
		return nil, fmt.Errorf("--head requires --base")
	}
	if n == 0 {
		return Full(), nil
	}
	if n > 1 {
		return nil, fmt.Errorf("choose one of --base, --staged, --working-tree, --commits")
	}
	if o.DiffContext == "" {
		o.DiffContext = "hunk"
	}
	if o.DiffContext != "hunk" && o.DiffContext != "file" {
		return nil, fmt.Errorf("--diff-context: want hunk|file, got %q", o.DiffContext)
	}
	top, err := git(root, "rev-parse", "--show-toplevel")
	if err != nil {
		return nil, fmt.Errorf("not a git repository: %w", err)
	}
	top = strings.TrimSpace(top)
	s := &Scope{DiffContext: o.DiffContext, Files: map[string][]Range{}, Deleted: map[string]bool{}, Added: map[string]bool{}}
	var args []string
	switch {
	case o.Base != "":
		head := o.Head
		if head == "" {
			head = "HEAD"
		}
		s.Mode, s.Base, s.Head = "base", o.Base, head
		if s.BaseSHA, err = revParse(root, o.Base); err != nil {
			return nil, err
		}
		if s.HeadSHA, err = revParse(root, head); err != nil {
			return nil, err
		}
		mb, err := git(root, "merge-base", s.BaseSHA, s.HeadSHA)
		if err != nil {
			return nil, fmt.Errorf("merge-base %s %s: %w", o.Base, head, err)
		}
		s.MergeBase = strings.TrimSpace(mb)
		args = []string{s.MergeBase, s.HeadSHA}
	case o.Staged:
		s.Mode = "staged"
		s.BaseSHA, _ = revParse(root, "HEAD")
		args = []string{"--cached"}
		if s.BaseSHA != "" {
			args = append(args, s.BaseSHA)
		}
	case o.WorkingTree:
		s.Mode = "working-tree"
		s.BaseSHA, _ = revParse(root, "HEAD")
		if s.BaseSHA != "" {
			args = []string{s.BaseSHA}
		} else { // unborn branch: everything tracked is new
			args = []string{"--cached"}
		}
	default:
		s.Mode = "commits"
		a, b, three := splitRange(o.Commits)
		if a == "" || b == "" {
			return nil, fmt.Errorf("--commits: want A..B or A...B, got %q", o.Commits)
		}
		s.Base, s.Head = a, b
		if s.BaseSHA, err = revParse(root, a); err != nil {
			return nil, err
		}
		if s.HeadSHA, err = revParse(root, b); err != nil {
			return nil, err
		}
		from := s.BaseSHA
		if three {
			mb, err := git(root, "merge-base", s.BaseSHA, s.HeadSHA)
			if err != nil {
				return nil, err
			}
			s.MergeBase = strings.TrimSpace(mb)
			from = s.MergeBase
		}
		args = []string{from, s.HeadSHA}
	}
	out, err := git(root, append([]string{"-c", "core.quotepath=off", "diff", "--no-color", "--no-ext-diff", "--unified=0", "-M", "--relative"}, args...)...)
	if err != nil {
		return nil, err
	}
	parseDiff(out, s)
	if s.Mode == "working-tree" {
		u, err := git(root, "-c", "core.quotepath=off", "ls-files", "--others", "--exclude-standard")
		if err == nil {
			for _, l := range strings.Split(strings.TrimSpace(u), "\n") {
				if l != "" {
					s.Files[filepath.ToSlash(l)] = nil // untracked: whole file is new
				}
			}
		}
	}
	_ = top
	s.ChangedFiles, s.DeletedFiles = len(s.Files), len(s.Deleted)
	return s, nil
}

func splitRange(r string) (a, b string, three bool) {
	if i := strings.Index(r, "..."); i >= 0 {
		return r[:i], r[i+3:], true
	}
	if i := strings.Index(r, ".."); i >= 0 {
		return r[:i], r[i+2:], false
	}
	return "", "", false
}

var hunkRe = regexp.MustCompile(`^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@`)

// parseDiff reads `git diff --unified=0` output into new-side line ranges.
func parseDiff(out string, s *Scope) {
	var cur string
	sc := bufio.NewScanner(strings.NewReader(out))
	sc.Buffer(make([]byte, 1024*1024), 16*1024*1024)
	var minus string
	for sc.Scan() {
		l := sc.Text()
		switch {
		case strings.HasPrefix(l, "diff --git "):
			cur, minus = "", ""
		case strings.HasPrefix(l, "--- "):
			minus = strings.TrimPrefix(strings.TrimPrefix(l, "--- "), "a/")
		case strings.HasPrefix(l, "+++ "):
			p := strings.TrimPrefix(l, "+++ ")
			if p == "/dev/null" {
				if minus != "" && minus != "/dev/null" {
					s.Deleted[minus] = true
				}
				cur = ""
				continue
			}
			cur = strings.TrimPrefix(p, "b/")
			if minus == "/dev/null" && s.Added != nil {
				s.Added[cur] = true
			}
			if _, ok := s.Files[cur]; !ok {
				s.Files[cur] = []Range{}
			}
		case strings.HasPrefix(l, "@@") && cur != "":
			m := hunkRe.FindStringSubmatch(l)
			if m == nil {
				continue
			}
			start, _ := strconv.Atoi(m[1])
			cnt := 1
			if m[2] != "" {
				cnt, _ = strconv.Atoi(m[2])
			}
			if cnt == 0 { // pure deletion: anchor on the following line so findings there count
				// (a deletion at the top of the file is "+0,0": clamp to line 1)
				start = max(start, 1)
				s.Files[cur] = append(s.Files[cur], Range{start, start + 1})
				continue
			}
			s.Files[cur] = append(s.Files[cur], Range{start, start + cnt - 1})
		}
	}
}

func revParse(root, ref string) (string, error) {
	out, err := git(root, "rev-parse", "--verify", "--quiet", ref+"^{commit}")
	if err != nil {
		return "", fmt.Errorf("unknown git ref %q", ref)
	}
	return strings.TrimSpace(out), nil
}

func git(root string, args ...string) (string, error) {
	cmd := exec.Command("git", args...)
	cmd.Dir = root
	var out, errb bytes.Buffer
	cmd.Stdout, cmd.Stderr = &out, &errb
	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("git %s: %w: %s", strings.Join(args, " "), err, strings.TrimSpace(errb.String()))
	}
	return out.String(), nil
}

// Git exposes the helper for run metadata (branch, commit, dirty).
func Git(root string, args ...string) (string, error) { return git(root, args...) }

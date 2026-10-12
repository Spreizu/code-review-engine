package runs

import (
	"os"
	"strings"

	"github.com/elmo/code-review-engine/internal/scope"
)

// GitInfo is the repository state recorded with a run.
type GitInfo struct {
	Branch string
	Commit string
	Dirty  bool
}

// DetectGit reads branch / HEAD / dirty state. CI-provided branch names win over a detached HEAD
// (GITHUB_HEAD_REF, GITHUB_REF_NAME, CI_COMMIT_REF_NAME, BRANCH_NAME, BUILDKITE_BRANCH).
// Outside git the branch is "no-git".
func DetectGit(root string) GitInfo {
	g := GitInfo{}
	if out, err := scope.Git(root, "rev-parse", "HEAD"); err == nil {
		g.Commit = strings.TrimSpace(out)
	}
	if out, err := scope.Git(root, "rev-parse", "--abbrev-ref", "HEAD"); err == nil {
		g.Branch = strings.TrimSpace(out)
	} else if out, err := scope.Git(root, "symbolic-ref", "--short", "HEAD"); err == nil { // unborn branch
		g.Branch = strings.TrimSpace(out)
	}
	if g.Branch == "" || g.Branch == "HEAD" {
		for _, k := range []string{"GITHUB_HEAD_REF", "GITHUB_REF_NAME", "CI_COMMIT_REF_NAME", "BRANCH_NAME", "BUILDKITE_BRANCH"} {
			if v := strings.TrimSpace(os.Getenv(k)); v != "" {
				g.Branch = v
				break
			}
		}
	}
	if g.Branch == "HEAD" && g.Commit != "" {
		g.Branch = "detached-" + g.Commit[:7]
	}
	if g.Branch == "" {
		g.Branch = "no-git"
	}
	// crev's own state dir (.crev/) never makes the tree dirty, even when a team commits it.
	if out, err := scope.Git(root, "status", "--porcelain", "--untracked-files=no", "--", ".", ":(exclude).crev"); err == nil {
		g.Dirty = strings.TrimSpace(out) != ""
	}
	return g
}

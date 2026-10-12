package engine

import "github.com/elmo/code-review-engine/internal/glob"

// GlobMatch matches slash-separated paths: "*", "?", "**" (any depth) and "{a,b}".
func GlobMatch(pattern, path string) bool { return glob.Match(pattern, path) }

package engine

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/versions"
)

// ManifestHit is a manifest-rule finding: file (relative to the unit) and 1-based line.
type ManifestHit struct {
	File string
	Line int
	Text string
}

var manifestFiles = []string{"pom.xml", "build.gradle.kts", "build.gradle", "package.json"}

func findLine(dir, needle string) (string, int, string) {
	for _, f := range manifestFiles {
		b, err := os.ReadFile(filepath.Join(dir, f))
		if err != nil {
			continue
		}
		for i, l := range strings.Split(string(b), "\n") {
			if needle == "" || strings.Contains(l, needle) {
				return f, i + 1, strings.TrimSpace(l)
			}
		}
	}
	return "", 0, ""
}

// EvalManifest evaluates a manifest-engine rule for one unit.
// checks: has_dependency | dependency_version (dependency present; version gate lives in applies_to)
// | java_release_below | path_exists_without (value exists, unless absent).
func EvalManifest(r *rules.Rule, u *versions.Unit) ([]ManifestHit, error) {
	spec := r.Detection.Manifest
	check, _ := spec["check"].(string)
	val, _ := spec["value"].(string)
	switch check {
	case "has_dependency", "dependency_version":
		if !u.Deps[val] {
			return nil, nil
		}
		needle := val
		if i := strings.LastIndex(val, ":"); i >= 0 {
			needle = val[i+1:]
		}
		f, l, t := findLine(u.Dir, `"`+needle+`"`)
		if f == "" {
			f, l, t = findLine(u.Dir, needle)
		}
		return []ManifestHit{{f, l, t}}, nil
	case "java_release_below":
		f, ok := u.Facts["java"]
		if !ok || f.Assumed {
			return nil, nil
		}
		if versions.Compare(f.Version, val) < 0 {
			file, l, t := findLine(u.Dir, f.Version)
			return []ManifestHit{{file, l, t}}, nil
		}
		return nil, nil
	case "path_exists_without":
		unless, _ := spec["unless"].(string)
		if _, err := os.Stat(filepath.Join(u.Dir, val)); err != nil {
			return nil, nil
		}
		if unless != "" {
			if _, err := os.Stat(filepath.Join(u.Dir, unless)); err == nil {
				return nil, nil
			}
		}
		return []ManifestHit{{File: strings.TrimSuffix(val, "/"), Line: 0}}, nil
	}
	return nil, fmt.Errorf("unknown manifest check %q", check)
}

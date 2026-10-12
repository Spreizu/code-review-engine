package engine

import (
	"io/fs"
	"path/filepath"
	"strings"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/index"
	"github.com/elmo/code-review-engine/internal/progress"
	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/scope"
	"github.com/elmo/code-review-engine/internal/versions"
)

// CappedCategories never exceed MaxAdvisorySeverity and never gate CI (simplification layer).
var CappedCategories = map[string]bool{"simplification": true, "test": true}

// MaxAdvisorySeverity is the ceiling for CappedCategories.
const MaxAdvisorySeverity = "minor"

// rerouteCategories are the "not lazy about" categories: a simplification finding overlapping
// one of these is dropped so the correctness/security finding is the one that is reported.
var rerouteCategories = map[string]bool{"security": true, "correctness": true, "concurrency": true, "resource-leak": true,
	"null-handling": true, "error-handling": true, "transactions": true, "reliability": true, "supply-chain": true, "type-safety": true}

type addFunc func(r *rules.Rule, u *versions.Unit, rel string, loc findings.Location, snippet, symbol string) *findings.Finding

// runIndexRules builds the repo index (only when an index rule is active) and runs index checks
// on every in-scope file.
func runIndexRules(root string, files []file, active []*rules.Rule, o Options, add addFunc, rep *findings.Report, prog func(progress.Event)) *index.Index {
	var irules []*rules.Rule
	for _, r := range active {
		if r.Detection.Engine == "index" {
			irules = append(irules, r)
		}
	}
	if len(irules) == 0 {
		return nil
	}
	prog(progress.Event{Phase: "index", Current: "building repo index"})
	rels := make([]string, 0, len(files))
	unitOf := map[string]*versions.Unit{}
	deps := map[string]bool{}
	for _, f := range files {
		rels = append(rels, f.rel)
		unitOf[f.rel] = f.unit
		for d := range f.unit.Deps {
			deps[d] = true
		}
	}
	x := index.Build(root, rels, deps)
	for k, v := range x.Stats {
		rep.Stats["index_"+k] = v
	}
	rep.Stats["index_ms"] = int(x.Duration / time.Millisecond)
	sc := o.Scope
	ctx := &index.Ctx{X: x, Diff: sc.IsDiff(), InScope: sc.InScope,
		Changed: func(rel string) []index.Range { return toRanges(sc, rel) },
		Added:   sc.IsAdded}
	for i, f := range files {
		fi := x.Files[f.rel]
		if fi == nil || fi.Test || !sc.FileInScope(f.rel) || (!o.IncludeGenerated && IsGeneratedSource(x.Source(f.rel))) {
			continue
		}
		if i%50 == 0 {
			prog(progress.Event{Phase: "index", Done: i, Total: len(files), Current: f.rel, Findings: len(rep.Findings)})
		}
		kind := fileKind(f.rel)
		unitRel := unitRelOf(root, f)
		for _, r := range irules {
			if !f.unit.AppliesTo(r.AppliesTo) || !indexLangApplies(r.Language, kind) {
				continue
			}
			if hasPositiveGlob(r) && !fileMatches(r, f.rel, unitRel) || fileExcluded(r, f.rel, unitRel) {
				continue
			}
			if dep := r.Detection.RequiresDependency; dep != "" && !f.unit.Deps[dep] {
				continue
			}
			r := withParams(r, o.project, f.rel)
			for _, h := range index.Run(r.Detection.Check, ctx, f.rel, r.Detection.Config) {
				end := h.EndLine
				if end < h.Line {
					end = h.Line
				}
				fd := add(r, f.unit, f.rel, findings.Location{StartLine: h.Line, StartColumn: 1, EndLine: end, EndColumn: 1}, h.Text, h.Symbol)
				if fd != nil {
					fd.Message = strings.TrimSpace(h.Text + ". " + fd.Message)
					fd.Evidence = h.Evidence
				}
			}
		}
	}
	return x
}

func indexLangApplies(lang, kind string) bool {
	if lang == "" || lang == "any" {
		return index.LangOf("x."+kind) != "" || kind == "typescript" || kind == "tsx" || kind == "javascript"
	}
	return languageApplies(lang, kind, "")
}

func unitRelOf(root string, f file) string {
	if f.unit == nil || f.unit.Dir == "" {
		return ""
	}
	return relTo(f.unit.Dir, filepath.Join(root, f.rel))
}

func toRanges(sc *scope.Scope, rel string) []index.Range {
	rs := sc.Ranges(rel)
	if rs == nil && sc.IsAdded(rel) {
		return []index.Range{{Start: 1, End: 1 << 30}}
	}
	out := make([]index.Range, len(rs))
	for i, r := range rs {
		out[i] = index.Range{Start: r.Start, End: r.End}
	}
	return out
}

// capAndReroute applies the advisory severity ceiling and drops simplification findings that
// overlap a correctness/security finding.
func capAndReroute(rep *findings.Report) {
	type span struct{ s, e int }
	hard := map[string][]span{}
	for _, f := range rep.Findings {
		if rerouteCategories[f.Category] && f.Status != "suppressed" {
			hard[f.Location.Path] = append(hard[f.Location.Path], span{f.Location.StartLine, f.Location.EndLine})
		}
	}
	out := rep.Findings[:0]
	for _, f := range rep.Findings {
		if f.Category == "simplification" {
			drop := false
			for _, s := range hard[f.Location.Path] {
				if s.s <= f.Location.EndLine && f.Location.StartLine <= s.e {
					drop = true
				}
			}
			if drop {
				rep.Stats["simplification_rerouted"]++
				continue
			}
		}
		out = append(out, f)
	}
	rep.Findings = out
}

// ListFiles returns the repo-relative files a scan would review (same exclusions: ignore globs,
// default excludes, .gitignore).
func ListFiles(root string, ignore []string) ([]string, error) {
	var out []string
	ignore = append(append([]string{}, defaultIgnore...), ignore...)
	gi := newGitIgnore(root)
	err := filepath.WalkDir(root, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		rel, _ := filepath.Rel(root, p)
		rel = filepath.ToSlash(rel)
		if d.IsDir() {
			if rel != "." && (ignored(ignore, rel+"/") || defaultExcludedDir(p, d.Name()) || gi.Ignored(rel, true)) {
				return filepath.SkipDir
			}
			gi.load(rel)
			return nil
		}
		if !ignored(ignore, rel) && !defaultExcludedFile(d.Name()) && !gi.Ignored(rel, false) {
			out = append(out, rel)
		}
		return nil
	})
	return out, err
}

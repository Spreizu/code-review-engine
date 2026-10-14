package engine

import (
	"fmt"
	"strings"
	"sync"

	ts "github.com/tree-sitter/go-tree-sitter"

	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/taint"
	"github.com/elmo/code-review-engine/internal/types"
)

// TypeMode selects the type resolver: "basic" (default; per file), "full" (adds facts from every
// file of the language in the scan: method return and field types across files) or "off"
// (type.* filters treat every type as unknown).
var TypeMode = "basic"

var (
	typeProjMu sync.RWMutex
	typeProj   = map[string]*types.Project{} // grammar family -> project index (full mode)
)

// SetTypeProject installs the cross-file index for a grammar (full mode).
func SetTypeProject(grammar string, p *types.Project) {
	typeProjMu.Lock()
	typeProj[typeFamily(grammar)] = p
	typeProjMu.Unlock()
}

// ClearTypeProjects drops the full-mode index (basic/off scans, or before a full rebuild).
func ClearTypeProjects() {
	typeProjMu.Lock()
	typeProj = map[string]*types.Project{}
	typeProjMu.Unlock()
}

func typeFamily(g string) string {
	switch g {
	case "javascript", "typescript", "tsx", "jsx":
		return "js"
	}
	return g
}

// TypeIndex builds the per-file type index of a parsed tree (used for the full-mode prepass).
func TypeIndex(t *Tree) *types.File {
	if !types.Supported(t.Grammar) {
		return nil
	}
	return types.Build(t.Grammar, taint.Convert(t.tree.RootNode()), t.Src)
}

func (t *Tree) typeFile() *types.File {
	if t.types == nil {
		t.types = TypeIndex(t)
		if t.types != nil && TypeMode == "full" {
			typeProjMu.RLock()
			t.types.Project = typeProj[typeFamily(t.Grammar)]
			typeProjMu.RUnlock()
		}
	}
	return t.types
}

func needTypes(r *rules.Rule) bool {
	for _, f := range r.Detection.Filters {
		if strings.HasPrefix(f, "type.") {
			return true
		}
	}
	return false
}

// typeFiltersPass evaluates type.is / type.not / type.not_or_unknown:CAP:regex on the type of
// capture @CAP. type.is needs a resolved type that matches; type.not a resolved type that does
// not; type.not_or_unknown passes on unknown too (use only where unknown is the safe side).
// A capture absent from this match (another branch of an alternation) skips the filter.
func typeFiltersPass(r *rules.Rule, t *Tree, m *ts.QueryMatch, names []string) (bool, error) {
	for _, f := range r.Detection.Filters {
		name, arg, _ := strings.Cut(f, ":")
		if !strings.HasPrefix(name, "type.") {
			continue
		}
		// type.differ:A:B - captures A and B resolve to built-in types that can never be equal /
		// combined (str vs int, string vs number); type.vs_text:A:T - the type of A vs the type
		// written in capture T (an annotation). Unknown or user-defined types never pass.
		// type.eq:A:B / type.eq_text:A:T - both sides resolve to the same non-empty type
		// (eq_text reads B as written text, like vs_text).
		if name == "type.differ" || name == "type.vs_text" || name == "type.eq" || name == "type.eq_text" {
			a, b, ok := strings.Cut(arg, ":")
			if !ok {
				return false, fmt.Errorf("filter %s wants CAP:CAP", name)
			}
			ta, pa := capType(t, m, names, a)
			var tb string
			pb := false
			if name == "type.differ" || name == "type.eq" {
				tb, pb = capType(t, m, names, b)
			} else {
				for _, c := range m.Captures {
					if names[c.Index] == b {
						tb, pb = types.Norm(c.Node.Utf8Text(t.Src)), true
						break
					}
				}
			}
			if !pa || !pb {
				continue
			}
			same := name == "type.eq" || name == "type.eq_text"
			if same {
				if ta == "" || tb == "" || ta != tb {
					return false, nil
				}
			} else if !types.Incompatible(t.Grammar, ta, tb) {
				return false, nil
			}
			continue
		}
		cname, expr, ok := strings.Cut(arg, ":")
		if !ok {
			return false, fmt.Errorf("filter %s wants CAP:regex", name)
		}
		re, err := cachedRe("^(?:" + expr + ")$")
		if err != nil {
			return false, fmt.Errorf("filter %s: %w", name, err)
		}
		typ, present := "", false
		for _, c := range m.Captures {
			if names[c.Index] == cname {
				present = true
				if TypeMode != "off" {
					if tf := t.typeFile(); tf != nil {
						typ = tf.TypeAt(uint32(c.Node.StartByte()), uint32(c.Node.EndByte()))
					}
				}
				break
			}
		}
		if !present {
			continue
		}
		switch name {
		case "type.is":
			if typ == "" || !re.MatchString(typ) {
				return false, nil
			}
		case "type.not":
			if typ == "" || re.MatchString(typ) {
				return false, nil
			}
		case "type.not_or_unknown":
			if typ != "" && re.MatchString(typ) {
				return false, nil
			}
		default:
			return false, fmt.Errorf("unknown filter %s", name)
		}
	}
	return true, nil
}

func capType(t *Tree, m *ts.QueryMatch, names []string, cname string) (string, bool) {
	for _, c := range m.Captures {
		if names[c.Index] == cname {
			if TypeMode == "off" {
				return "", true
			}
			if tf := t.typeFile(); tf != nil {
				return tf.TypeAt(uint32(c.Node.StartByte()), uint32(c.Node.EndByte())), true
			}
			return "", true
		}
	}
	return "", false
}

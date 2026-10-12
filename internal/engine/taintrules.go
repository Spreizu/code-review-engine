package engine

import (
	"github.com/elmo/code-review-engine/internal/taint"
)

// TaintRun runs taint-lite over a parsed tree (all classes at once; rules select their class).
// The result is cached on the tree, so taint rules and taint.clean filters share one analysis.
func TaintRun(t *Tree) ([]taint.Hit, error) {
	r, err := t.taintResult()
	return r.Hits, err
}

func (t *Tree) taintResult() (taint.Result, error) {
	if t.taint != nil {
		return *t.taint, t.taintErr
	}
	t.taint = &taint.Result{}
	fam := taint.Family(t.Grammar)
	if fam == "" {
		return *t.taint, nil
	}
	l, err := taint.Spec(fam)
	if err != nil || l == nil {
		t.taintErr = err
		return *t.taint, err
	}
	*t.taint = taint.AnalyzeFull(taint.Convert(t.Root()), t.Src, fam, l)
	return *t.taint, nil
}

// taintClean reports whether [s,e) contains (or lies inside) a clean sink of the class: a call to
// a known sink whose arguments taint-lite proved are not derived from the enclosing function's
// untrusted input. Languages without a taint spec never report clean.
func (t *Tree) taintClean(class string, s, e uint) bool {
	r, err := t.taintResult()
	if err != nil {
		return false
	}
	for _, c := range r.Clean {
		if c.Class != class {
			continue
		}
		cs, ce := uint(c.Node.S), uint(c.Node.E)
		if cs >= s && ce <= e || s >= cs && e <= ce {
			return true
		}
	}
	return false
}

func t0(trees map[string]*Tree, grammar string) *Tree { return trees[grammar] }

// taintSymbol returns the enclosing symbol of a hit (same format as tree-sitter findings).
func taintSymbol(t *Tree, n *taint.N) string {
	if t == nil {
		return ""
	}
	d := t.Root().NamedDescendantForByteRange(uint(n.S), uint(n.E))
	if d == nil {
		return ""
	}
	return enclosing(*d, t.Src)
}

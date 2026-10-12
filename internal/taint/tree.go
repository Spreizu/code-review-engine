// Package taint is crev's intra-procedural "taint-lite" engine: it follows values from
// attacker-controlled sources (request parameters, headers, cookies, bodies, superglobals) through
// local assignments, string building, containers and same-file helper functions to injection sinks
// (SQL, OS command, file path, LDAP, HTML output, outbound URL, redirect), on the tree-sitter tree.
//
// It is deliberately small: one function at a time, names not types, one pass per loop body, no
// aliasing. Precision aids that are cheap on a syntax tree are implemented: branch merging,
// constant folding of conditions/ternaries/switches, literal-key map and literal-index list
// tracking, class-specific sanitizers and same-file function summaries (does the return value
// depend on the parameters, and which sanitizers does it apply). Sources, sinks and sanitizers
// are data (rules/data/taint.yaml); rules select a vulnerability class (detection.config.class).
// Findings are ai-confirm by default: the AI step sees the flow as evidence.
package taint

import (
	ts "github.com/tree-sitter/go-tree-sitter"
)

// N is a Go-side copy of a tree-sitter node (walking cgo nodes repeatedly is slow).
type N struct {
	Kind     string
	Field    string
	Named    bool
	S, E     uint32
	Row, Col uint32
	ERow     uint32
	ECol     uint32
	Kids     []*N
	Parent   *N
}

// Convert copies the tree rooted at root.
func Convert(root *ts.Node) *N {
	c := root.Walk()
	defer c.Close()
	var build func(parent *N, field string) *N
	build = func(parent *N, field string) *N {
		n := c.Node()
		sp, ep := n.StartPosition(), n.EndPosition()
		x := &N{Kind: n.Kind(), Field: field, Named: n.IsNamed(), S: uint32(n.StartByte()), E: uint32(n.EndByte()),
			Row: uint32(sp.Row), Col: uint32(sp.Column), ERow: uint32(ep.Row), ECol: uint32(ep.Column), Parent: parent}
		if c.GotoFirstChild() {
			for {
				x.Kids = append(x.Kids, build(x, c.FieldName()))
				if !c.GotoNextSibling() {
					break
				}
			}
			c.GotoParent()
		}
		return x
	}
	return build(nil, "")
}

// F returns the first child with the field name.
func (n *N) F(field string) *N {
	if n == nil {
		return nil
	}
	for _, k := range n.Kids {
		if k.Field == field {
			return k
		}
	}
	return nil
}

// FAll returns every child with the field name.
func (n *N) FAll(field string) []*N {
	var out []*N
	for _, k := range n.Kids {
		if k.Field == field {
			out = append(out, k)
		}
	}
	return out
}

// NamedKids returns the named children (comments excluded).
func (n *N) NamedKids() []*N {
	var out []*N
	for _, k := range n.Kids {
		if k.Named && k.Kind != "comment" && k.Kind != "line_comment" && k.Kind != "block_comment" && k.Kind != "multiline_comment" {
			out = append(out, k)
		}
	}
	return out
}

// Child returns the first named child of one of the kinds.
func (n *N) Child(kinds ...string) *N {
	for _, k := range n.Kids {
		for _, want := range kinds {
			if k.Kind == want {
				return k
			}
		}
	}
	return nil
}

func (n *N) text(src []byte) string { return string(src[n.S:n.E]) }

// op returns the first anonymous child token that looks like an operator.
func (n *N) op(src []byte) string {
	for _, k := range n.Kids {
		if !k.Named {
			t := k.text(src)
			if t != "(" && t != ")" {
				return t
			}
		}
	}
	return ""
}

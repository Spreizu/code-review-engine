package main

import (
	"fmt"
	"strings"

	ts "github.com/tree-sitter/go-tree-sitter"
)

// dump prints a named-node outline with field names and short text, for rule authors.
func dump(n *ts.Node, src []byte, depth int, field string) {
	txt := strings.ReplaceAll(n.Utf8Text(src), "\n", "⏎")
	if len(txt) > 40 {
		txt = txt[:40] + "…"
	}
	f := ""
	if field != "" {
		f = field + ": "
	}
	fmt.Printf("%s%s%s  %q\n", strings.Repeat("  ", depth), f, n.Kind(), txt)
	c := n.Walk()
	defer c.Close()
	if c.GotoFirstChild() {
		for {
			if c.Node().IsNamed() {
				dump(c.Node(), src, depth+1, c.FieldName())
			}
			if !c.GotoNextSibling() {
				break
			}
		}
	}
}

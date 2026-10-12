// astdump prints the tree-sitter S-expression of a file, or the matches of a query, to help
// rule authors: astdump <grammar> <file> ['<query>']
package main

import (
	"fmt"
	"os"

	"github.com/elmo/code-review-engine/internal/engine"
	"github.com/elmo/code-review-engine/internal/rules"
)

func main() {
	if len(os.Args) < 3 {
		fmt.Fprintln(os.Stderr, "usage: astdump <grammar> <file> [query]")
		os.Exit(2)
	}
	src, err := os.ReadFile(os.Args[2])
	if err != nil {
		panic(err)
	}
	t, err := engine.Parse(os.Args[1], src)
	if err != nil {
		panic(err)
	}
	defer t.Close()
	if len(os.Args) < 4 {
		fmt.Println(t.SExpr())
		return
	}
	r := &rules.Rule{ID: "ASTDUMP", Detection: rules.Detection{Query: os.Args[3], Grammar: os.Args[1]}}
	hits, err := engine.Run(r, t)
	if err != nil {
		panic(err)
	}
	for _, h := range hits {
		fmt.Printf("%d:%d %q\n", h.StartRow+1, h.StartCol+1, h.Text)
	}
}

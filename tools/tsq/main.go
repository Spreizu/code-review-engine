// Command tsq runs a tree-sitter query against a file and prints every capture (rule-authoring helper).
//
//	go run ./tools/tsq <grammar> <file> '<query>'
package main

import (
	"fmt"
	"os"

	"github.com/elmo/code-review-engine/internal/grammars"
	ts "github.com/tree-sitter/go-tree-sitter"
)

func main() {
	src, err := os.ReadFile(os.Args[2])
	if err != nil {
		panic(err)
	}
	lang := grammars.Get(os.Args[1])
	p := ts.NewParser()
	defer p.Close()
	if err := p.SetLanguage(lang); err != nil {
		panic(err)
	}
	t := p.Parse(src, nil)
	q, qerr := ts.NewQuery(lang, os.Args[3])
	if qerr != nil {
		fmt.Println("query error:", qerr)
		os.Exit(1)
	}
	qc := ts.NewQueryCursor()
	ms := qc.Matches(q, t.RootNode(), src)
	names := q.CaptureNames()
	for m := ms.Next(); m != nil; m = ms.Next() {
		for _, c := range m.Captures {
			fmt.Printf("@%s %s %q\n", names[c.Index], c.Node.Kind(), c.Node.Utf8Text(src))
		}
	}
}

// Command sexp prints the tree-sitter S-expression of a file (debug helper for rule authors).
package main

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/elmo/code-review-engine/internal/grammars"
	ts "github.com/tree-sitter/go-tree-sitter"
)

func main() {
	src, err := os.ReadFile(os.Args[2])
	if err != nil {
		panic(err)
	}
	lang := grammars.Get(os.Args[1])
	if lang == nil {
		fmt.Fprintln(os.Stderr, "unknown language", os.Args[1], filepath.Ext(os.Args[2]))
		os.Exit(2)
	}
	p := ts.NewParser()
	defer p.Close()
	if err := p.SetLanguage(lang); err != nil {
		fmt.Fprintln(os.Stderr, "setlang:", err)
		os.Exit(3)
	}
	t := p.Parse(src, nil)
	defer t.Close()
	if len(os.Args) > 3 {
		dump(t.RootNode(), src, 0, "")
		return
	}
	fmt.Println(t.RootNode().ToSexp())
}

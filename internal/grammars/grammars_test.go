package grammars

import (
	"testing"

	ts "github.com/tree-sitter/go-tree-sitter"
)

func TestAllGrammarsLoad(t *testing.T) {
	src := map[string]string{"go": "package a\nfunc f(){}\n", "python": "def f():\n  pass\n", "php": "<?php echo 1;", "kotlin": "fun f() = 1\n", "groovy": "dependencies { implementation 'a:b:1' }\n", "json": "{\"a\":1}", "yaml": "a: 1\n", "xml": "<a><b/></a>", "hcl": "resource \"a\" \"b\" {\n x = 1\n}\n", "dockerfile": "FROM alpine:3.20\nRUN echo hi\n", "proto": "syntax = \"proto3\";\nmessage A { string a = 1; }\n", "graphql": "type Query { a: String }\n", "java": "class A{}", "javascript": "a()", "typescript": "let a: number", "tsx": "<a/>", "vue": "<template><div/></template>"}
	for _, n := range Names {
		l := Get(n)
		if l == nil {
			t.Fatalf("%s: nil", n)
		}
		p := ts.NewParser()
		if err := p.SetLanguage(l); err != nil {
			p.Close()
			t.Fatalf("%s: %v (abi %d)", n, err, l.AbiVersion())
		}
		tr := p.Parse([]byte(src[n]), nil)
		if tr.RootNode().HasError() {
			t.Errorf("%s: parse error %s", n, tr.RootNode().ToSexp())
		}
		tr.Close()
		p.Close()
	}
}

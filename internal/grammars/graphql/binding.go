// Package graphql vendors bkegley/tree-sitter-graphql at commit
// 5e66e961eee421786bdda8495ed1db045e06b5fe (2021-05-10); no Go binding; ABI 13 (unmaintained since 2021).
package graphql

// #cgo CFLAGS: -std=c11 -fPIC -I${SRCDIR}/src
// #include "src/parser.c"
import "C"

import "unsafe"

// Language returns the tree-sitter Language.
func Language() unsafe.Pointer { return unsafe.Pointer(C.tree_sitter_graphql()) }

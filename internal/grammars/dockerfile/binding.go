// Package dockerfile vendors camdencheek/tree-sitter-dockerfile at commit
// 971acdd908568b4531b0ba28a445bf0bb720aba5 (2025-01-12); the latest tag (v0.2.0) has no Go binding.
package dockerfile

// #cgo CFLAGS: -std=c11 -fPIC -I${SRCDIR}/src
// #include "src/parser.c"
// #include "src/scanner.c"
import "C"

import "unsafe"

// Language returns the tree-sitter Language.
func Language() unsafe.Pointer { return unsafe.Pointer(C.tree_sitter_dockerfile()) }

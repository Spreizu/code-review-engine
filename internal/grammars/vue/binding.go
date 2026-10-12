// Package vue vendors tree-sitter-grammars/tree-sitter-vue (MIT) at commit
// ce8011a414fdf8091f4e4071752efc376f4afb08 (2026-01-24), which ships no Go binding.
package vue

// #cgo CFLAGS: -std=c11 -fPIC -I${SRCDIR}/src
// #include "src/parser.c"
// #include "src/scanner.c"
import "C"

import "unsafe"

// Language returns the tree-sitter Language for Vue SFCs.
func Language() unsafe.Pointer { return unsafe.Pointer(C.tree_sitter_vue()) }

// Package proto vendors coder3101/tree-sitter-proto at commit
// d7d15427321da271cb1c25c12735e180ef981473 (2026-10-07); its go.mod requires Go 1.26, so the C sources are vendored to keep go 1.23.
package proto

// #cgo CFLAGS: -std=c11 -fPIC -I${SRCDIR}/src
// #include "src/parser.c"
import "C"

import "unsafe"

// Language returns the tree-sitter Language.
func Language() unsafe.Pointer { return unsafe.Pointer(C.tree_sitter_proto()) }

package engine

import (
	"strings"
	"testing"

	ts "github.com/tree-sitter/go-tree-sitter"
)

func TestContrastRatio(t *testing.T) {
	w, _ := cssColor("#fff")
	b, _ := cssColor("black")
	if r := ContrastRatio(w, b); r < 20.9 || r > 21.1 {
		t.Fatalf("white/black %v", r)
	}
	g, _ := cssColor("#777")
	if r := ContrastRatio(w, g); r < 4.4 || r > 4.5 {
		t.Fatalf("white/#777 %v", r) // 4.48: the classic just-failing grey
	}
	if _, ok := cssColor("rgba(0,0,0,.5)"); ok {
		t.Fatal("transparent colour must be unknown")
	}
	if c, ok := cssColor("rgb(255 0 0)"); !ok || c[0] != 1 {
		t.Fatal("rgb space syntax")
	}
	if !CSSKnown("property", "grid-gap") || !CSSKnown("descriptor", "font-display") || CSSKnown("property", "colr") {
		t.Fatal("known props")
	}
}

func TestDupSelectorAcrossStyleBlocks(t *testing.T) {
	src := []byte("<template><div/></template>\n<style>\n.a { color: red; }\n</style>\n<style scoped>\n.a { margin: 0; }\n</style>\n")
	view, ok := StyleBlocks(src)
	if !ok || !strings.Contains(string(view), StyleBoundary) {
		t.Fatalf("no boundary in style view: %q", view)
	}
}

func TestDupSelectorSkipsRootHost(t *testing.T) {
	src := []byte(":root { --bg: #fff; }\n.card { color: #333; }\n:root { --fg: #111; }\n:host { --pad: 1rem; }\n:host { --gap: 2rem; }\n")
	tree, err := Parse("css", src)
	if err != nil {
		t.Fatal(err)
	}
	defer tree.Close()
	var n int
	for _, c := range named(tree.Root()) {
		if c.Kind() != "rule_set" {
			continue
		}
		pass, handled := cssFilter("css.dup_selector", "", *c, src)
		if !handled {
			t.Fatal("css.dup_selector not handled")
		}
		if pass {
			n++
		}
	}
	if n != 0 {
		t.Fatalf(":root/:host splits should not match, got %d", n)
	}
}

func TestUnknownMediaAndType(t *testing.T) {
	src := []byte("@media (min-wdth: 40em) { foo { color: red; } div { color: blue; } }\n@media (min-width: 40em) { a { color: red; } }\nmy-el { color: red; }\n")
	tree, err := Parse("css", src)
	if err != nil {
		t.Fatal(err)
	}
	defer tree.Close()
	var media, types int
	var visit func(n *ts.Node)
	visit = func(n *ts.Node) {
		switch n.Kind() {
		case "feature_name":
			if pass, ok := cssFilter("css.unknown_media", "", *n, src); !ok {
				t.Fatal("css.unknown_media not handled")
			} else if pass {
				media++
			}
		case "tag_name":
			if pass, ok := cssFilter("css.unknown_type", "", *n, src); !ok {
				t.Fatal("css.unknown_type not handled")
			} else if pass {
				types++
			}
		}
		for _, c := range named(n) {
			visit(c)
		}
	}
	visit(tree.Root())
	if media != 1 {
		t.Fatalf("unknown media features: got %d want 1", media)
	}
	if types != 1 {
		t.Fatalf("unknown type selectors: got %d want 1 (foo)", types)
	}
	if !cssMediaFeatures["width"] || cssMediaFeatures["wdth"] || !cssTypeSelectors["div"] || cssTypeSelectors["foo"] {
		t.Fatal("media/type tables")
	}
}

func TestDupKeyframe(t *testing.T) {
	src := []byte("@keyframes fade {\n  from { opacity: 0; }\n  from { opacity: 0.1; }\n  to { opacity: 1; }\n}\n@keyframes ok {\n  from { opacity: 0; }\n  to { opacity: 1; }\n}\n")
	tree, err := Parse("css", src)
	if err != nil {
		t.Fatal(err)
	}
	defer tree.Close()
	var n int
	var visit func(nd *ts.Node)
	visit = func(nd *ts.Node) {
		if nd.Kind() == "keyframe_block" {
			pass, ok := cssFilter("css.dup_keyframe", "", *nd, src)
			if !ok {
				t.Fatal("css.dup_keyframe not handled")
			}
			if pass {
				n++
			}
		}
		for _, c := range named(nd) {
			visit(c)
		}
	}
	visit(tree.Root())
	if n != 1 {
		t.Fatalf("dup keyframe selectors: got %d want 1", n)
	}
}

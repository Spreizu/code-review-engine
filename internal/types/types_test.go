package types

import (
	"strings"
	"testing"

	ts "github.com/tree-sitter/go-tree-sitter"

	"github.com/elmo/code-review-engine/internal/grammars"
	"github.com/elmo/code-review-engine/internal/taint"
)

func build(t *testing.T, lang, src string) *File {
	t.Helper()
	p := ts.NewParser()
	defer p.Close()
	if err := p.SetLanguage(grammars.Get(lang)); err != nil {
		t.Fatal(err)
	}
	tr := p.Parse([]byte(src), nil)
	return Build(lang, taint.Convert(tr.RootNode()), []byte(src))
}

// typeOfMarked resolves the text between the first «...» marker pair (markers are removed).
func check(t *testing.T, lang, src string, want map[string]string) {
	t.Helper()
	f := build(t, lang, src)
	for expr, typ := range want {
		i := strings.LastIndex(src, expr)
		if i < 0 {
			t.Fatalf("%s: %q not in source", lang, expr)
		}
		e := strings.TrimSpace(expr)
		i += strings.Index(expr, e)
		if strings.HasSuffix(e, ",") || strings.HasSuffix(e, ")") && !strings.HasSuffix(e, "()") && !strings.HasSuffix(e, "(1)") {
			e = strings.TrimSpace(e[:len(e)-1])
		}
		if strings.HasPrefix(e, "use(") {
			i, e = i+4, e[4:]
		}
		if got := f.TypeAt(uint32(i), uint32(i+len(e))); got != typ {
			t.Errorf("%s: type of %q = %q, want %q", lang, expr, got, typ)
		}
	}
}

func TestJava(t *testing.T) {
	check(t, "java", `class A {
  private StringBuilder sb = new StringBuilder();
  private List<String> names;
  String name() { return null; }
  void f(String s, Map<String, Integer> m) {
    var t = "x";
    Object o = get();
    var u = s.trim();
    int n = 3;
    use(s, 0); use(t); use(o); use(u); use(m); use(sb); use(names); use(this.sb); use(name()); use(unknown);
  }
}`, map[string]string{"s,": "String", "t)": "String", "o)": "Object", "u)": "String", "m)": "Map",
		"sb)": "StringBuilder", "names)": "List", "this.sb": "StringBuilder", "name()": "String", "unknown": ""})
}

func TestPython(t *testing.T) {
	check(t, "python", `from rich.text import Text
class Box:
    def __init__(self):
        self.label = "x"
        self.items = []
    def size(self) -> int:
        return 1
def f(a: str, b, c=3):
    t = Text("hi")
    s = "abc"
    if b:
        r = "x"
    else:
        r = 1
    s2 = s.strip()
    box = Box()
    use(a, b, c, t, s , r, s2, box.label, box.items, box.size())
`, map[string]string{"a,": "str", " b,": "", "c,": "int", "t,": "", "s ,": "str", "r,": "", "s2": "str",
		"box.label": "str", "box.items": "list", "box.size()": "int"})
}

func TestTS(t *testing.T) {
	check(t, "typescript", `class C { private m: Map<string, number> = new Map(); name = "n";
  run(x: string, y: number | undefined) { const z = x.trim(); let q = [1]; use(x, y, z, q, this.m, this.name); } }`,
		map[string]string{"x,": "string", "y,": "", "z,": "string", "q,": "Array", "this.m": "Map", "this.name": "string"})
}

func TestGoKotlinPHP(t *testing.T) {
	check(t, "go", "package p\ntype T struct{}\nfunc (t *T) Name() string { return \"\" }\nfunc f(s string) {\n\tx := &T{}\n\tn := x.Name()\n\tuse(s, x, n)\n}\n",
		map[string]string{"s,": "string", "x,": "T", "n)": "string"})
	check(t, "kotlin", "class K(val label: String) {\n  fun f(p: Int) {\n    val s = \"x\"\n    val k = K(\"a\")\n    use(p, s, k, k.label)\n  }\n}\n",
		map[string]string{"p,": "Int", "s,": "String", "k,": "K", "k.label": "String"})
	check(t, "php", "<?php\nclass P { private Foo $foo; function f(string $s) { $a = new Bar(); $b = 'x'; use($s, $a, $b, $this->foo); } }\n",
		map[string]string{"$s,": "string", "$a,": "Bar", "$b,": "string", "$this->foo": "Foo"})
}

func TestProject(t *testing.T) {
	a := build(t, "java", "class Repo { User find(int id) { return null; } }")
	b := build(t, "java", "class S { Repo repo; void f() { use(repo.find(1)); } }")
	b.Project = NewProject([]*File{a, b})
	i := strings.Index(string(b.Src), "repo.find(1)")
	if got := b.TypeAt(uint32(i), uint32(i+len("repo.find(1)"))); got != "User" {
		t.Fatalf("cross-file return type = %q", got)
	}
}

func TestInheritanceAndCasts(t *testing.T) {
	check(t, "java", `class A { String name; }
class B extends A {
  void f(Object x) {
    String t = (String) x;
    StringBuilder sb = new StringBuilder();
    use(name, t, sb.append("x"));
  }
}`, map[string]string{"name,": "String", " t,": "String", `sb.append("x")`: "StringBuilder"})
	check(t, "go", "package p\ntype T struct {\n\tName string\n}\nfunc f(x any) {\n\tt := x.(T)\n\tuse(t, t.Name)\n}\n",
		map[string]string{"t,": "T", "t.Name": "string"})
}

func TestCrossFileInheritance(t *testing.T) {
	a := build(t, "java", "class A { String name; String label() { return name; } }")
	b := build(t, "java", "class B extends A { void f() { use(name, label()); } }")
	b.Project = NewProject([]*File{a, b})
	src := string(b.Src)
	i := strings.Index(src, "name,")
	if got := b.TypeAt(uint32(i), uint32(i+len("name"))); got != "String" {
		t.Fatalf("inherited field = %q", got)
	}
	j := strings.Index(src, "label()")
	if got := b.TypeAt(uint32(j), uint32(j+len("label()"))); got != "String" {
		t.Fatalf("inherited method = %q", got)
	}
}

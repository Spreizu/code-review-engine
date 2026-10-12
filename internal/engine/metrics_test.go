package engine

import (
	"testing"

	ts "github.com/tree-sitter/go-tree-sitter"
)

func firstFunc(n *ts.Node) *ts.Node {
	if funcKinds[n.Kind()] {
		return n
	}
	for i := uint(0); i < n.NamedChildCount(); i++ {
		if f := firstFunc(n.NamedChild(i)); f != nil {
			return f
		}
	}
	return nil
}

func TestMetrics(t *testing.T) {
	cases := []struct {
		grammar, src string
		want         map[string]int
	}{
		{"java", `class A { int sumOfPrimes(int max) { int total = 0;
  OUT: for (int i = 1; i <= max; ++i) { for (int j = 2; j < i; ++j) { if (i % j == 0) { continue OUT; } } total += i; }
  return total; } }`, map[string]int{"cognitive": 7, "params": 1, "returns": 1, "nesting": 3}},
		{"java", `class A { String getWords(int number) { switch (number) { case 1: return "one"; case 2: return "a couple"; default: return "lots"; } } }`,
			map[string]int{"cognitive": 1, "cyclomatic": 3, "returns": 3}},
		{"java", `class A { void f(boolean a, boolean b) { if (a) { x(); } else if (b) { y(); } else { z(); } } }`,
			map[string]int{"cognitive": 3, "cyclomatic": 3, "nesting": 1, "params": 2}},
		{"python", "def f(self, a, b):\n    if a and b or c:\n        return 1\n    elif b:\n        return 2\n    else:\n        return 3\n    x = 1 if a else 2\n    match a:\n        case 1:\n            pass\n",
			map[string]int{"cognitive": 7, "cyclomatic": 7, "params": 2, "returns": 3}},
		{"python", "def f(x, y, _t, _u: int, _v=1, r=2):\n    pass\n", map[string]int{"params": 3}},
		{"kotlin", "fun f(a: Int, b: Boolean): Int {\n  if (a > 1 && b || a < 0) { return 1 } else if (b) { return 2 } else { return 3 }\n  when (a) { 1 -> println(1)\n else -> {} }\n  for (x in xs) { while (true) {} }\n  try { } catch (e: Exception) { }\n  val y = a ?: 2\n}\n",
			map[string]int{"cognitive": 10, "params": 2, "returns": 3, "nesting": 2}},
		{"php", "<?php\nfunction f($a, $b) {\n  if ($a && $b || $c) { return 1; } elseif ($b) { return 2; } else { return 3; }\n  foreach ($xs as $x) { while (true) {} }\n}\n",
			map[string]int{"cognitive": 8, "params": 2, "returns": 3, "nesting": 2}},
		{"go", "package p\nfunc (r *T) f(a, b int, c string) int {\n\tif a > b {\n\t\treturn 1\n\t} else {\n\t\tfor i := 0; i < 3; i++ {\n\t\t\tif i == b && c != \"\" {\n\t\t\t\treturn 2\n\t\t\t}\n\t\t}\n\t}\n\treturn 0\n}\n",
			map[string]int{"cognitive": 8, "cyclomatic": 5, "params": 3, "returns": 3, "nesting": 3}},
		{"javascript", "function f(a) {\n  if (a) { g(); } else if (b) { h(); } else { k(); }\n  const fn = () => a ? 1 : 2;\n  return a ?? b;\n}\n",
			map[string]int{"cognitive": 6, "params": 1, "returns": 1}},
	}
	for i, c := range cases {
		tr, err := Parse(c.grammar, []byte(c.src))
		if err != nil {
			t.Fatal(err)
		}
		fn := firstFunc(tr.Root())
		if fn == nil {
			t.Fatalf("case %d: no function", i)
		}
		for m, want := range c.want {
			got, err := Metric(m, fn, tr.Src)
			if err != nil {
				t.Fatal(err)
			}
			if got != want {
				t.Errorf("case %d (%s) %s = %d, want %d", i, c.grammar, m, got, want)
			}
		}
		tr.Close()
	}
}

func TestCaseCount(t *testing.T) {
	for g, src := range map[string]string{
		"java":       `class A { void f(int n) { switch (n) { case 1: a(); break; case 2: b(); break; default: c(); } } }`,
		"javascript": `switch (n) { case 1: a(); break; case 2: b(); break; default: c(); }`,
		"go":         "package p\nfunc f() {\n\tswitch n {\n\tcase 1:\n\t\ta()\n\tcase 2:\n\t\tb()\n\tdefault:\n\t}\n}\n",
		"php":        "<?php\nswitch ($n) { case 1: a(); break; case 2: b(); break; default: c(); }\n",
	} {
		tr, _ := Parse(g, []byte(src))
		var sw *ts.Node
		var find func(n *ts.Node)
		find = func(n *ts.Node) {
			if sw == nil && switchKinds[n.Kind()] {
				sw = n
			}
			for j := uint(0); j < n.NamedChildCount(); j++ {
				find(n.NamedChild(j))
			}
		}
		find(tr.Root())
		if got, _ := Metric("cases", sw, tr.Src); got != 2 {
			t.Errorf("%s cases = %d, want 2", g, got)
		}
	}
}

func TestBranchFilters(t *testing.T) {
	cases := []struct {
		grammar, src, filter string
		want                 bool
	}{
		{"java", `class A { void f() { if (a) { log(1); count++; } else if (b) { other(); } else { log(1); count++; } } }`, "branches.dup_body", true},
		{"java", `class A { void f() { if (a) { log(1); count++; } else if (b) { log(2); count++; } } }`, "branches.dup_body", false},
		{"java", `class A { void f() { if (a) { return; } else if (b) { return; } } }`, "branches.dup_body", false}, // trivial
		{"java", `class A { void f() { if (a) { x(); } else { x(); } } }`, "branches.all_same", true},
		{"java", `class A { void f() { if (a) { x(); } else if (b) { x(); } } }`, "branches.all_same", false}, // no else
		{"java", `class A { void f() { if (a == 1) { x(); } else if (a == 1) { y(); } } }`, "branches.dup_cond", true},
		{"java", `class A { void f() { if (next()) { x(); } else if (next()) { y(); } } }`, "branches.dup_cond", false},
		{"javascript", "switch (a) { case 1: foo(); bar(); break; case 2: foo(); bar(); break; default: baz(); }", "branches.dup_body", true},
		{"javascript", "switch (a) { case 1: case 2: foo(); bar(); break; default: baz(); }", "branches.dup_body", false},
		{"javascript", "if (a) { this.#x = 1; y(); } else { this.#z = 2; y(); }", "branches.all_same", false},
		{"python", "if a:\n    x = 1\n    y()\nelif b:\n    x = 1\n    y()\n", "branches.dup_body", true},
		{"python", "if a == 1:\n    x()\nelif a == 1:\n    y()\n", "branches.dup_cond", true},
		{"go", "package p\nfunc f() {\n\tif ok, err = a(); ok {\n\t\treturn\n\t} else if ok, err = b(); ok {\n\t\treturn\n\t}\n}\n", "branches.dup_cond", false},
		{"kotlin", "fun f(b: Boolean?) = when (b) {\n    true -> 'Y'\n    false -> 'N'\n    else -> ' '\n}\n", "branches.all_same", false},
		{"kotlin", "fun f(d: Any) = if (d is H2) ';' else '?'\n", "branches.all_same", false},
		{"kotlin", "fun f(r: Any) = if (r is String) g(r) else g(r)\n", "branches.all_same", false},
		{"kotlin", "fun f(a: Boolean) = if (a) g(1) else g(1)\n", "branches.all_same", true},
		{"go", "package p\nfunc f() {\n\tswitch a {\n\tcase 1:\n\t\tx()\n\tdefault:\n\t\tx()\n\t}\n}\n", "branches.all_same", true},
		{"php", "<?php\nif ($a) { f(); g(); } elseif ($b) { f(); g(); }\n", "branches.dup_body", true},
		{"kotlin", "fun f() { if (a) { x() } else { x() } }", "branches.all_same", true},
		{"go", "package p\nfunc f() {\n\tif a { }\n\tif b {\n\t} else {\n\t}\n}\n", "branches.all_same", false}, // empty bodies must not panic
	}
	for i, c := range cases {
		tr, err := Parse(c.grammar, []byte(c.src))
		if err != nil {
			t.Fatal(err)
		}
		var head *ts.Node
		var find func(n *ts.Node)
		find = func(n *ts.Node) {
			if head != nil {
				return
			}
			if ifKinds[n.Kind()] || switchKinds[n.Kind()] {
				head = n
				return
			}
			for j := uint(0); j < n.NamedChildCount(); j++ {
				find(n.NamedChild(j))
			}
		}
		find(tr.Root())
		if head == nil {
			t.Fatalf("case %d: no branch head", i)
		}
		if got := branchFilter(c.filter, *head, tr.Src); got != c.want {
			t.Errorf("case %d (%s %s) = %v, want %v", i, c.grammar, c.filter, got, c.want)
		}
		tr.Close()
	}
}

func TestBoolOpsAndInvariant(t *testing.T) {
	first := func(grammar, src string, pick func(*ts.Node) bool) (*ts.Node, []byte) {
		tr, err := Parse(grammar, []byte(src))
		if err != nil {
			t.Fatal(err)
		}
		var hit *ts.Node
		var walk func(n *ts.Node)
		walk = func(n *ts.Node) {
			if hit != nil {
				return
			}
			if pick(n) {
				hit = n
				return
			}
			for j := uint(0); j < n.NamedChildCount(); j++ {
				walk(n.NamedChild(j))
			}
		}
		walk(tr.Root())
		if hit == nil {
			t.Fatalf("no node in %q", src)
		}
		return hit, []byte(src)
	}
	isBin := func(n *ts.Node) bool { return n.Kind() == "binary_expression" || n.Kind() == "boolean_operator" }
	for _, c := range []struct {
		grammar, src string
		want         int
	}{
		{"java", "class A { boolean f() { return a && b || c && (d || e); } }", 4},
		{"python", "x = a and b or c\n", 2},
		{"javascript", "x = a + b;", 0},
	} {
		n, src := first(c.grammar, c.src, isBin)
		if got := boolOps(n, src); got != c.want {
			t.Errorf("%s: boolops %d want %d", c.src, got, c.want)
		}
	}
	isFn := func(n *ts.Node) bool { return funcKinds[n.Kind()] }
	for _, c := range []struct {
		grammar, src string
		want         bool
	}{
		{"java", "class A { int f(int a) { if (a > 1) { return 0; } return 0; } }", true},
		{"java", "class A { int f(int a) { if (a > 1) { return 1; } return 0; } }", false},
		{"python", "def f(a):\n    if a:\n        return None\n    return None\n", true},
		{"go", "package p\nfunc f(a int) int {\n\tif a > 1 {\n\t\treturn x\n\t}\n\treturn x\n}\n", false},
	} {
		n, src := first(c.grammar, c.src, isFn)
		if got := returnsInvariant(n, src); got != c.want {
			t.Errorf("%s: invariant %v want %v", c.src, got, c.want)
		}
	}
}

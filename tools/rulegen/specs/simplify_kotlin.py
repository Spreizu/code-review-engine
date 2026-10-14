"""Simplification pack for Kotlin: collapsible loops -> kotlin.collections operations,
hand-written helpers the stdlib replaces, native delegation instead of middle-man classes, and
repo-index checks."""
from specs._simplify import simp, index_rules, helper, loop

P = simp("SIMP-KT", "kotlin", "Kotlin 2.2", {"kotlin": "*"})
DOC = "https://kotlinlang.org/docs/"

loop(P, "ANY", "Loop that is any { }", DOC + "collection-filtering.html", "any() returns true if at least one element matches the given predicate",
     '(for_statement (block . (if_expression (block . (return_expression (identifier) @t) .)) .) (#eq? @t "true")) @match',
     "fun hasAdmin(users: List<User>): Boolean {\n    for (u in users) {\n        if (u.isAdmin) {\n            return true\n        }\n    }\n    return false\n}\n",
     "fun hasAdmin(users: List<User>): Boolean = users.any { it.isAdmin }\n", "Use any { } / all { } / none { }.")
loop(P, "MAX", "Loop that is maxOrNull()/minOrNull()", DOC + "collection-aggregate.html", "minOrNull() and maxOrNull() return the smallest and the largest element respectively",
     '(for_statement (variable_declaration (identifier) @x) (block . (if_expression condition: (binary_expression left: (identifier) @a) (assignment right: (identifier) @v)) .) (#eq? @x @v) (#eq? @a @x)) @match',
     "fun top(xs: List<Int>): Int {\n    var m = xs[0]\n    for (x in xs) { if (x > m) m = x }\n    return m\n}\n",
     "fun top(xs: List<Int>): Int = xs.max()\n", "Use max()/min(), maxOrNull()/minOrNull() or maxBy { }.")
loop(P, "SUMOF", "Accumulator loop that is sumOf { }", DOC + "collection-aggregate.html", "sumOf()",
     '(for_statement (block . (assignment left: (identifier) @acc) @a .) (#match? @a "^\\\\w+\\\\s*\\\\+=")) @match',
     "fun total(items: List<Item>): Int {\n    var t = 0\n    for (i in items) { t += i.price }\n    return t\n}\n",
     "fun total(items: List<Item>): Int = items.sumOf { it.price }\n", "Use sumOf { } (or sum()).",
     # += on a list/set adds elements: the accumulator must be a numeric local
     filters=[r"func.has_re:\bvar\s+{cap:acc}\s*(:\s*(Int|Long|Double|Float|Short|Byte|UInt|ULong)\s*)?=\s*[-+]?(\d|0x)"],
     fp=["fun all(xs: List<P>): List<R> {\n    val result = mutableListOf<R>()\n    for (p in xs) { result += load(p) }\n    return result\n}\n"])

helper(P, "DISTINCT", "Hand-written distinct helper", "https://kotlinlang.org/api/core/kotlin-stdlib/kotlin.collections/distinct.html",
       "Returns a list containing only distinct elements from the given collection", ["unique", "uniq", "dedupe", "removeDuplicates", "distinctItems"], "distinct()",
       "fun unique(xs: List<String>): List<String> {\n    val out = mutableListOf<String>()\n    for (x in xs) { if (x !in out) out.add(x) }\n    return out\n}\n",
       "fun tags(xs: List<String>) = xs.distinct()\n", uses=["distinct", "toSet"])
helper(P, "GROUPBY", "Hand-written groupBy helper", DOC + "collection-grouping.html",
       "The Kotlin standard library provides extension functions for grouping collection elements", ["groupBy", "group", "bucketBy", "partitionBy", "groupItems"], "groupBy { }",
       "fun group(xs: List<User>): Map<String, List<User>> {\n    val out = mutableMapOf<String, MutableList<User>>()\n    for (x in xs) { out.getOrPut(x.team) { mutableListOf() }.add(x) }\n    return out\n}\n",
       "fun byTeam(xs: List<User>) = xs.groupBy { it.team }\n", uses=[".groupBy", "groupingBy"])

DEL = (DOC + "delegation.html", "Kotlin supports it natively requiring zero boilerplate code", "Kotlin: Delegation")
VIS = (DOC + "visibility-modifiers.html", "The default visibility is public", "Kotlin: Visibility modifiers")
AGG = (DOC + "collection-filtering.html", "any() returns true if at least one element matches the given predicate", "Kotlin: Filtering collections")
D = {"unused-export": VIS, "middle-man": DEL, "duplicate-helper": VIS, "call-site-patches": VIS, "nested-loop-no-limit-note": AGG, "limit-note-incomplete": AGG,
     "test-missing": (DOC + "jvm-test-using-junit.html", "you can write tests for Java code using Kotlin", "Kotlin: Test code using JUnit")}
NL = "fun common(a: List<String>, b: List<String>): List<String> {\n    val out = mutableListOf<String>()\n%s    for (x in a) {\n        for (y in b) {\n            if (x == y) out.add(x)\n        }\n    }\n    return out\n}\n"
GUARD = "fun %s(p: String?) {\n    if (p == null) return\n    load(p)\n}\n"
CL = "fun classify(n: Int): String {\n    if (n < 0) return \"neg\"\n    else if (n == 0) return \"zero\"\n    if (n % 2 == 0) return \"even\"\n    if (n > 100) return \"big\"\n    return \"odd\"\n}\n"
index_rules(P, {
    "unused-export": ("// file: src/main/kotlin/Text.kt\nfun slugify(s: String) = s.lowercase()\n",
                      "// file: src/main/kotlin/Text.kt\nfun slugify(s: String) = s.lowercase()\n// file: src/main/kotlin/Page.kt\nfun main() = println(slugify(\"A\"))\n"),
    "middle-man": ("// file: src/main/kotlin/Store.kt\nclass Store(private val m: Cache) {\n    fun get(k: String) = m.get(k)\n    fun put(k: String, v: String) = m.put(k, v)\n}\n",
                   "// file: src/main/kotlin/Store.kt\nclass Store(private val m: Cache) {\n    fun get(k: String) = m.get(k)\n    fun put(k: String, v: String) = m.put(k, v.trim())\n}\n"),
    "nested-loop-no-limit-note": (NL % "", NL % "    // limit: a and b stay under 50 items; switch to toSet() if they grow\n"),
    "limit-note-incomplete": (NL % "    // limit: quadratic but fine\n", NL % "    // limit: O(n*m), n < 100 here; switch to toSet() when it grows\n"),
    "duplicate-helper": ("// file: a.kt\nfun normalize(s: String): String {\n    var x = s.trim()\n    x = x.lowercase()\n    return x\n}\n// file: b.kt\nfun clean(v: String): String {\n    var y = v.trim()\n    y = y.lowercase()\n    return y\n}\n",
                         "// file: a.kt\nfun normalize(s: String): String {\n    var x = s.trim()\n    x = x.lowercase()\n    return x\n}\n// file: b.kt\nfun clean(v: String): String {\n    var y = v.trim()\n    y = y.uppercase()\n    return y\n}\n"),
    "call-site-patches": ("// file: Loader.kt (existing)\nfun load(p: String) {}\n// file: Use.kt\n" + GUARD % "a" + GUARD % "b" + GUARD % "c",
                          "// file: Loader.kt (existing)\nfun load(p: String) {}\n// file: Use.kt\n" + GUARD % "a" + "fun b(p: String) { load(p) }\n"),
    "test-missing": ("// file: src/main/kotlin/Sign.kt\nfun sign(n: Int): Int = if (n < 0) -1 else 1\n// file: src/test/kotlin/SignTest.kt\nclass SignTest {\n    @Test fun neg() = assertEquals(-1, sign(-2))\n}\n" + "// file: src/main/kotlin/Num.kt\n" + CL, "// file: src/main/kotlin/Sign.kt\nfun sign(n: Int): Int = if (n < 0) -1 else 1\n// file: src/test/kotlin/SignTest.kt\nclass SignTest {\n    @Test fun neg() = assertEquals(-1, sign(-2))\n}\n" + "// file: src/main/kotlin/Num.kt\n" + CL + "// file: src/test/kotlin/NumTest.kt\nclass NumTest {\n    @Test fun even() = assertEquals(\"even\", classify(2))\n}\n"),
}, D)

RULES = P.R

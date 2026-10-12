"""Simplification pack for PHP: collapsible loops -> array_* functions (with the PHP
version each needs), hand-written helpers the standard library replaces, and repo-index checks."""
from specs._simplify import simp, index_rules, helper, loop

P = simp("SIMP-PHP", "php", "PHP 8.4", {"php": "*"})
FN = "https://www.php.net/manual/en/function."

loop(P, "INARRAY", "Loop that is in_array", FN + "in-array.php", "Checks if a value exists in an array",
     '(foreach_statement body: (compound_statement . (if_statement condition: (parenthesized_expression (binary_expression operator: "===")) body: (compound_statement . (return_statement (boolean) @t) .)) .) (#match? @t "^(?i:true)$")) @match',
     "<?php\nfunction has($xs, $v) {\n    foreach ($xs as $x) {\n        if ($x === $v) {\n            return true;\n        }\n    }\n    return false;\n}\n",
     "<?php\nfunction has($xs, $v) {\n    return in_array($v, $xs, true);\n}\n", "Use in_array($v, $xs, true).")
loop(P, "ANY", "Loop that is array_any", FN + "array-any.php", "Checks if at least one array element satisfies a callback function",
     '(foreach_statement body: (compound_statement . (if_statement condition: (parenthesized_expression) @c body: (compound_statement . (return_statement (boolean) @t) .)) .) (#match? @t "^(?i:true)$") (#not-match? @c "===")) @match',
     "<?php\nfunction anyAdmin($users) {\n    foreach ($users as $u) {\n        if ($u->isAdmin() && $u->active) {\n            return true;\n        }\n    }\n    return false;\n}\n",
     "<?php\nfunction anyAdmin($users) {\n    return array_any($users, fn($u) => $u->isAdmin() && $u->active);\n}\n", "Use array_any / array_all (PHP 8.4).", applies={"php": ">=8.4"})
loop(P, "SUM", "Accumulator loop that is array_sum", FN + "array-sum.php", "Calculate the sum of values in an array",
     '(foreach_statement (variable_name) @x body: (compound_statement . (expression_statement (augmented_assignment_expression right: (variable_name) @v)) .) (#eq? @x @v)) @match',
     "<?php\nfunction total($xs) {\n    $t = 0;\n    foreach ($xs as $x) { $t += $x; }\n    return $t;\n}\n",
     "<?php\nfunction total($xs) {\n    return array_sum($xs);\n}\n", "Use array_sum($xs).")
loop(P, "COLUMN", "Push loop that is array_column", FN + "array-column.php", "Return the values from a single column in the input array",
     '(foreach_statement (variable_name) @r body: (compound_statement . (expression_statement (assignment_expression left: (subscript_expression . (variable_name) .) right: (subscript_expression (variable_name) @r2 (string)))) .) (#eq? @r @r2)) @match',
     "<?php\nfunction ids($rows) {\n    $out = [];\n    foreach ($rows as $r) { $out[] = $r['id']; }\n    return $out;\n}\n",
     "<?php\nfunction ids($rows) {\n    return array_column($rows, 'id');\n}\n", "Use array_column($rows, 'key').")

helper(P, "STARTSWITH", "Hand-written starts/ends-with helper", FN + "str-starts-with.php", "Checks if a string starts with a given substring",
       ["startsWith", "starts_with", "endsWith", "ends_with", "beginsWith"], "str_starts_with / str_ends_with",
       "<?php\nfunction startsWith($h, $n) {\n    return substr($h, 0, strlen($n)) === $n;\n}\n", "<?php\nfunction isApi($p) {\n    return str_starts_with($p, '/api');\n}\n",
       applies={"php": ">=8.0"}, uses=["str_starts_with", "str_ends_with"], loop=False, max_lines=8)
helper(P, "CONTAINS", "Hand-written string contains helper", FN + "str-contains.php", "Determine if a string contains a given substring",
       ["contains", "str_contains_polyfill", "strContains", "stringContains", "has_substring"], "str_contains",
       "<?php\nfunction strContains($h, $n) {\n    return strpos($h, $n) !== false;\n}\n", "<?php\nfunction isAdmin($r) {\n    return str_contains($r, 'admin');\n}\n",
       applies={"php": ">=8.0"}, uses=["str_contains"], loop=False, max_lines=8)
helper(P, "UNIQUE", "Hand-written array dedupe helper", FN + "array-unique.php", "Removes duplicate values from an array",
       ["unique", "dedupe", "uniq", "remove_duplicates", "distinct"], "array_unique",
       "<?php\nfunction unique($xs) {\n    $out = [];\n    foreach ($xs as $x) {\n        if (!in_array($x, $out, true)) { $out[] = $x; }\n    }\n    return $out;\n}\n",
       "<?php\nfunction tags($xs) {\n    return array_values(array_unique($xs));\n}\n", uses=["array_unique", "array_flip"])

VIS = ("https://www.php.net/manual/en/language.oop5.visibility.php", "Members declared protected can be accessed only within the class itself", "PHP: Visibility")
TR = ("https://www.php.net/manual/en/language.oop5.traits.php", "Traits are a mechanism for code reuse", "PHP: Traits")
FLIP = (FN + "array-flip.php", "Exchanges all keys with their associated values in an array", "array_flip")
D = {"unused-export": VIS, "middle-man": VIS, "duplicate-helper": TR, "call-site-patches": TR, "nested-loop-no-limit-note": FLIP, "limit-note-incomplete": FLIP,
     "test-missing": ("https://docs.phpunit.de/en/11.5/writing-tests-for-phpunit.html", "The tests are public methods that are named test", "PHPUnit: Writing tests")}
NL = "<?php\nfunction common($a, $b) {\n    $out = [];\n%s    foreach ($a as $x) {\n        foreach ($b as $y) {\n            if ($x === $y) { $out[] = $x; }\n        }\n    }\n    return $out;\n}\n"
GUARD = "function %s($p) {\n    if (empty($p)) { return; }\n    load($p);\n}\n"
CL = "function classify($n) {\n    if ($n < 0) { return 'neg'; }\n    elseif ($n === 0) { return 'zero'; }\n    if ($n % 2 === 0) { return 'even'; }\n    if ($n > 100) { return 'big'; }\n    return 'odd';\n}\n"
index_rules(P, {
    "unused-export": ("// file: src/text.php\n<?php\nfunction slugify($s) { return strtolower($s); }\n",
                      "// file: src/text.php\n<?php\nfunction slugify($s) { return strtolower($s); }\n// file: src/page.php\n<?php\necho slugify('A');\n"),
    "middle-man": ("// file: src/UserService.php\n<?php\nclass UserService {\n    public function __construct(private UserRepo $repo) {}\n    public function find($id) { return $this->repo->find($id); }\n    public function save($u) { return $this->repo->save($u); }\n}\n",
                   "// file: src/UserService.php\n<?php\nclass UserService {\n    public function __construct(private UserRepo $repo) {}\n    public function find($id) { return $this->repo->find($id); }\n    public function save($u) { return $this->repo->save(trim($u)); }\n}\n"),
    "nested-loop-no-limit-note": (NL % "", NL % "    // limit: a and b stay under 50 items; switch to array_flip + isset if they grow\n"),
    "limit-note-incomplete": (NL % "    // limit: quadratic but fine\n", NL % "    // limit: O(n*m), n < 100 here; switch to array_flip + isset when it grows\n"),
    "duplicate-helper": ("// file: a.php\n<?php\nfunction normalize($s) {\n    $s = trim($s);\n    $s = strtolower($s);\n    return $s;\n}\n// file: b.php\n<?php\nfunction clean($v) {\n    $v = trim($v);\n    $v = strtolower($v);\n    return $v;\n}\n",
                         "// file: a.php\n<?php\nfunction normalize($s) {\n    $s = trim($s);\n    $s = strtolower($s);\n    return $s;\n}\n// file: b.php\n<?php\nfunction clean($v) {\n    $v = trim($v);\n    $v = strtoupper($v);\n    return $v;\n}\n"),
    "call-site-patches": ("// file: loader.php (existing)\n<?php\nfunction load($p) {}\n// file: use.php\n<?php\n" + GUARD % "a" + GUARD % "b" + GUARD % "c",
                          "// file: loader.php (existing)\n<?php\nfunction load($p) {}\n// file: use.php\n<?php\n" + GUARD % "a" + "function b($p) { load($p); }\n"),
    "test-missing": ("// file: src/sign.php\n<?php\nfunction sign($n) { return $n < 0 ? -1 : 1; }\n// file: tests/SignTest.php\n<?php\nclass SignTest extends TestCase {\n    public function testNeg() { $this->assertSame(-1, sign(-2)); }\n}\n" + "// file: src/num.php\n<?php\n" + CL, "// file: src/sign.php\n<?php\nfunction sign($n) { return $n < 0 ? -1 : 1; }\n// file: tests/SignTest.php\n<?php\nclass SignTest extends TestCase {\n    public function testNeg() { $this->assertSame(-1, sign(-2)); }\n}\n" + "// file: src/num.php\n<?php\n" + CL + "// file: tests/NumTest.php\n<?php\nclass NumTest extends TestCase {\n    public function testEven() { $this->assertSame('even', classify(2)); }\n}\n"),
}, D)

RULES = P.R

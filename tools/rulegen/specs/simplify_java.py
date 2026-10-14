"""Simplification pack for Java: collapsible loops -> Collection/Stream/String APIs
(with the Java version each needs), hand-written helpers the JDK replaces, and repo-index checks."""
from specs._simplify import simp, index_rules, helper, loop

P = simp("SIMP-JAVA", "java", "Java SE 21", {"java": ">=8"})
API = "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/"
RET_TRUE = '[(block . (return_statement (true)) .) (return_statement (true))]'

loop(P, "CONTAINS", "Loop that is Collection.contains", API + "util/Collection.html", "Returns true if this collection contains the specified element",
     '(enhanced_for_statement body: (block . (if_statement condition: (parenthesized_expression (method_invocation name: (identifier) @eq)) consequence: ' + RET_TRUE + ' !alternative) .) (#eq? @eq "equals")) @match',
     "class A {\n  boolean has(List<String> xs, String v) {\n    for (String x : xs) {\n      if (x.equals(v)) {\n        return true;\n      }\n    }\n    return false;\n  }\n}\n",
     "class A {\n  boolean has(List<String> xs, String v) {\n    return xs.contains(v);\n  }\n}\n", "Use collection.contains(v).")
loop(P, "ANYMATCH", "Loop that is Stream.anyMatch", API + "util/stream/Stream.html", "Returns whether any elements of this stream match the provided predicate",
     '(enhanced_for_statement body: (block . (if_statement condition: (parenthesized_expression) @c consequence: ' + RET_TRUE + ' !alternative) .) (#not-match? @c "^\\\\(\\\\s*\\\\w+\\\\.equals\\\\(")) @match',
     "class A {\n  boolean anyAdmin(List<User> users) {\n    for (User u : users) {\n      if (u.isAdmin() && u.isActive()) return true;\n    }\n    return false;\n  }\n}\n",
     "class A {\n  boolean anyAdmin(List<User> users) {\n    return users.stream().anyMatch(u -> u.isAdmin() && u.isActive());\n  }\n}\n",
     "Use stream().anyMatch / allMatch / noneMatch.",
     # char[]/boolean[]/byte[]/short[]/float[] have no Arrays.stream overload
     filters=[r"node.lacks_re:^for\s*\(\s*(final\s+)?(char|boolean|byte|short|float)\s"])
loop(P, "MAX", "Loop that is Collections.max / min", API + "util/Collections.html", "Returns the maximum element of the given collection",
     '(enhanced_for_statement name: (identifier) @x body: (block . (if_statement condition: (parenthesized_expression (binary_expression left: (identifier) @a operator: [">" "<"])) consequence: [(block . (expression_statement (assignment_expression right: (identifier) @v)) .) (expression_statement (assignment_expression right: (identifier) @v))] !alternative) .) (#eq? @x @v) (#eq? @a @x)) @match',
     "class A {\n  int top(List<Integer> xs) {\n    int m = xs.get(0);\n    for (int x : xs) {\n      if (x > m) m = x;\n    }\n    return m;\n  }\n}\n",
     "class A {\n  int top(List<Integer> xs) {\n    return Collections.max(xs);\n  }\n}\n", "Use Collections.max/min (or stream().max(comparator)).")
loop(P, "JOIN", "StringBuilder separator loop that is String.join", API + "lang/String.html",
     "Returns a new String composed of copies of the CharSequence elements joined together",
     '(enhanced_for_statement body: (block)) @match', "class A {\n  String csv(List<String> xs) {\n    StringBuilder sb = new StringBuilder();\n    for (String x : xs) {\n      sb.append(x).append(\",\");\n    }\n    return sb.toString();\n  }\n}\n",
     "class A {\n  String csv(List<String> xs) {\n    return String.join(\",\", xs);\n  }\n}\n", "Use String.join(sep, items) or Collectors.joining(sep).",
     filters=[r'node.has_re:\.append\(\s*"[,;|] ?"\s*\)'])

helper(P, "ISBLANK", "Hand-written isBlank helper", API + "lang/String.html", "Returns true if the string is empty or contains only white space codepoints",
       ["isBlank", "isNullOrEmpty", "isEmptyString", "isNullOrBlank", "isEmptyOrWhitespace"], "String.isBlank",
       "class S {\n  static boolean isNullOrBlank(String s) {\n    return s == null || s.trim().length() == 0;\n  }\n}\n",
       "class S {\n  static boolean missing(String s) {\n    return s == null || s.isBlank();\n  }\n}\n", applies={"java": ">=11"}, uses=["isBlank()"], loop=False, max_lines=10)
helper(P, "CLAMP", "Hand-written clamp helper", API + "lang/Math.html", "Clamps the value to fit between min and max", ["clamp", "bound", "constrain", "limit"],
       "Math.clamp", "class M {\n  static int clamp(int v, int lo, int hi) {\n    return Math.max(lo, Math.min(hi, v));\n  }\n}\n",
       "class M {\n  static int pct(int v) {\n    return Math.clamp(v, 0, 100);\n  }\n}\n", applies={"java": ">=21"}, uses=["Math.clamp"], loop=False, max_lines=10)
helper(P, "JOIN", "Hand-written join helper", API + "lang/String.html", "Returns a new String composed of copies of the CharSequence elements joined together",
       ["join", "joinStrings", "implode", "mkString", "joinWith"], "String.join",
       "class J {\n  static String join(List<String> xs, String sep) {\n    StringBuilder sb = new StringBuilder();\n    for (String x : xs) {\n      if (sb.length() > 0) sb.append(sep);\n      sb.append(x);\n    }\n    return sb.toString();\n  }\n}\n",
       "class J {\n  static String csv(List<String> xs) {\n    return String.join(\",\", xs);\n  }\n}\n", uses=["String.join", "Collectors.joining"])

ACC = ("https://docs.oracle.com/javase/tutorial/java/javaOO/accesscontrol.html", "Use the most restrictive access level that makes sense for a particular member", "Java tutorial: Controlling access")
SET = (API + "util/HashSet.html", "This class offers constant time performance for the basic operations", "java.util.HashSet")
D = {"unused-export": ACC, "middle-man": ACC, "duplicate-helper": ACC, "call-site-patches": ACC, "nested-loop-no-limit-note": SET, "limit-note-incomplete": SET,
     "test-missing": ("https://docs.junit.org/current/user-guide/", "composed of several different modules", "JUnit User Guide")}
NL = "class C {\n  List<String> common(List<String> a, List<String> b) {\n    List<String> out = new ArrayList<>();\n%s    for (String x : a) {\n      for (String y : b) {\n        if (x.equals(y)) out.add(x);\n      }\n    }\n    return out;\n  }\n}\n"
GUARD = "  void %s(String p) {\n    if (p == null) return;\n    load(p);\n  }\n"
CL = "public class Num {\n  public static String classify(int n) {\n    if (n < 0) return \"neg\";\n    else if (n == 0) return \"zero\";\n    if (n % 2 == 0) return \"even\";\n    if (n > 100) return \"big\";\n    return \"odd\";\n  }\n}\n"
J = "src/main/java/p/"
index_rules(P, {
    "unused-export": ("// file: " + J + "Slugger.java\npackage p;\npublic class Slugger {\n  public String slug(String s) { return s.toLowerCase(); }\n}\n",
                      "// file: " + J + "Slugger.java\npackage p;\npublic class Slugger {\n  public String slug(String s) { return s.toLowerCase(); }\n}\n// file: " + J + "Page.java\npackage p;\nclass Page {\n  String t() { return new Slugger().slug(\"A\"); }\n}\n"),
    "middle-man": ("// file: " + J + "UserService.java\npackage p;\npublic class UserService {\n  private final UserRepo repo;\n  public UserService(UserRepo repo) { this.repo = repo; }\n  public User find(String id) { return repo.find(id); }\n  public void save(User u) { repo.save(u); }\n}\n",
                   "// file: " + J + "UserService.java\npackage p;\npublic class UserService {\n  private final UserRepo repo;\n  public UserService(UserRepo repo) { this.repo = repo; }\n  public User find(String id) { return repo.find(id); }\n  public void save(User u) { repo.save(u.normalized()); }\n}\n"),
    "nested-loop-no-limit-note": (NL % "", NL % "    // limit: a and b stay under 50 items; switch to a HashSet if they grow\n"),
    "limit-note-incomplete": (NL % "    // limit: quadratic but fine\n", NL % "    // limit: O(n*m), n < 100 here; switch to a HashSet when it grows\n"),
    "duplicate-helper": ("// file: " + J + "A.java\nclass A {\n  static String normalize(String s) {\n    s = s.trim();\n    s = s.toLowerCase();\n    return s;\n  }\n}\n// file: " + J + "B.java\nclass B {\n  static String clean(String v) {\n    v = v.trim();\n    v = v.toLowerCase();\n    return v;\n  }\n}\n",
                         "// file: " + J + "A.java\nclass A {\n  static String normalize(String s) {\n    s = s.trim();\n    s = s.toLowerCase();\n    return s;\n  }\n}\n// file: " + J + "B.java\nclass B {\n  static String clean(String v) {\n    v = v.trim();\n    v = v.toUpperCase();\n    return v;\n  }\n}\n"),
    "call-site-patches": ("// file: " + J + "Loader.java (existing)\nclass Loader {\n  static void load(String p) {}\n}\n// file: " + J + "Use.java\nclass Use {\n" + GUARD % "a" + GUARD % "b" + GUARD % "c" + "}\n",
                          "// file: " + J + "Loader.java (existing)\nclass Loader {\n  static void load(String p) {}\n}\n// file: " + J + "Use.java\nclass Use {\n" + GUARD % "a" + "  void b(String p) { load(p); }\n}\n"),
    "test-missing": ("// file: " + J + "Sign.java\npackage p;\npublic class Sign {\n  public static int of(int n) { return n < 0 ? -1 : 1; }\n}\n// file: src/test/java/p/SignTest.java\npackage p;\nclass SignTest {\n  @Test void neg() { assertEquals(-1, Sign.of(-2)); }\n}\n" + "// file: " + J + "Num.java\npackage p;\n" + CL, "// file: " + J + "Sign.java\npackage p;\npublic class Sign {\n  public static int of(int n) { return n < 0 ? -1 : 1; }\n}\n// file: src/test/java/p/SignTest.java\npackage p;\nclass SignTest {\n  @Test void neg() { assertEquals(-1, Sign.of(-2)); }\n}\n" + "// file: " + J + "Num.java\npackage p;\n" + CL + "// file: src/test/java/p/NumTest.java\npackage p;\nclass NumTest {\n  @Test void even() { assertEquals(\"even\", Num.classify(2)); }\n}\n"),
}, D)

RULES = P.R

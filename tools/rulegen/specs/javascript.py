"""JavaScript pack (ES2015+; also runs on TypeScript and Vue <script>).

Mirrors non-deprecated ESLint core rules (eslint.org/docs/latest/rules/*), MDN security /
deprecation guidance and Node.js deprecations (nodejs.org/api/deprecations.html)."""
from specs._lint import lint
from rulegen import rule

R = RULES = []
ES = {"ecmascript": ">=3"}


def E(name, sev, cat, query, bad, good, msg, *, id=None, **kw):
    kw.setdefault("applies", ES)
    R.append(lint("eslint", name, id or "JS-" + name.upper(), language="javascript", severity=sev, category=cat,
                  query=query, bad=bad, good=good, message=msg, **kw))


MEMBER_CALL = '((call_expression function: (member_expression object: (_) @o property: (property_identifier) @p)) @match (#match? @p "{p}"))'

# ---------------------------------------------------------------- possible problems
E("array-callback-return", "major", "correctness",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (arrow_function body: (statement_block) @b))) @match (#match? @p "^(map|filter|find|findIndex|findLast|findLastIndex|every|some|reduce|reduceRight|flatMap|sort|toSorted)$") (#not-match? @b "return|throw"))
((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (function_expression body: (statement_block) @b))) @match (#match? @p "^(map|filter|find|findIndex|findLast|findLastIndex|every|some|reduce|reduceRight|flatMap|sort|toSorted)$") (#not-match? @b "return|throw"))''',
  "const doubled = items.map((x) => { x * 2 })\n", "const doubled = items.map((x) => x * 2)\n",
  "The callback of this array method never returns a value, so the result is an array of undefined / an always-false predicate.")
# Fixture triage (ESLint suite): compare the counter itself, on either side of the comparison,
# with the variable the update changes (a different variable or `10 > i` is not wrong).
_FD = '((for_statement condition: (binary_expression {cond}) increment: (update_expression argument: (identifier) @u operator: "{upd}")) @match (#eq? @c @u))'
E("for-direction", "critical", "correctness",
  "\n".join(_FD.format(cond=(f"left: (identifier) @c operator: [{ops}]" if side == "left" else f"operator: [{ops}] right: (identifier) @c"), upd=upd)
            for side, ops, upd in [("left", '"<" "<="', "--"), ("right", '">" ">="', "--"), ("left", '">" ">="', "++"), ("right", '"<" "<="', "++")]),
  "for (let i = 0; i < 10; i--) { work(i) }\n", "for (let i = 0; i < 10; i++) { work(i) }\n",
  "The loop counter moves away from the stop condition, so the loop never terminates (or never runs).",
  fp=[{"note": "bound on the left", "code": "for (let i = 0; 10 > i; i++) { work(i) }\n"},
      {"note": "another variable is updated", "code": "for (let i = 10; i >= 0; j++) { work(i, j) }\n"}])
E("getter-return", "major", "correctness",
  r'''((method_definition "get" body: (statement_block) @b) @match (#not-match? @b "return|throw"))''',
  "class A {\n  get name() { this._name }\n}\n", "class A {\n  get name() { return this._name }\n}\n",
  "A getter without return always yields undefined.")
E("no-class-assign", "major", "correctness",
  r'''((program (class_declaration name: (_) @a) (expression_statement (assignment_expression left: (identifier) @b))) @match (#eq? @a @b))''',
  "class A {}\nA = 0\n", "class A {}\nconst B = 0\n", "Reassigning a class binding is almost always a mistake.")
E("no-compare-neg-zero", "major", "correctness",
  r'''((binary_expression operator: ["==" "===" "!=" "!==" "<" ">" "<=" ">="] right: (unary_expression operator: "-" argument: (number) @n)) @match (#eq? @n "0"))''',
  "if (x === -0) {}\n", "if (Object.is(x, -0)) {}\n", "Comparison with -0 also matches +0; use Object.is(x, -0).")
E("no-cond-assign", "major", "correctness",
  r'''(if_statement condition: (parenthesized_expression (assignment_expression) @match))
(while_statement condition: (parenthesized_expression (assignment_expression) @match))''',
  "if (user = find(id)) { use(user) }\n", "const user = find(id)\nif (user) { use(user) }\n",
  "Assignment inside a condition is usually a mistyped comparison (= instead of ===).")
E("no-const-assign", "critical", "correctness",
  r'''((program (lexical_declaration kind: "const" (variable_declarator name: (identifier) @a)) (expression_statement [(assignment_expression left: (identifier) @b) (augmented_assignment_expression left: (identifier) @b) (update_expression argument: (identifier) @b)])) @match (#eq? @a @b))''',
  "const max = 1\nmax = 2\n", "let max = 1\nmax = 2\n", "Assigning to a const binding throws a TypeError at runtime.")
E("no-constant-binary-expression", "major", "correctness",
  r'''(binary_expression operator: ["==" "===" "!=" "!=="] right: [(array) (object) (arrow_function) (function_expression) (class)] @match)
(binary_expression left: (unary_expression operator: "!") operator: ["==" "===" "!=" "!=="] right: [(null) (undefined)] @match)
(binary_expression left: [(array) (object)] @match operator: ["??" "||"])''',
  "if (list === []) { empty() }\n", "if (list.length === 0) { empty() }\n",
  "This comparison/logical expression always evaluates the same way (fresh object identity, boolean vs null, or non-nullish left side).")
E("no-constant-condition", "major", "correctness",
  r'''(if_statement condition: (parenthesized_expression [(true) (false) (number) (string) (array) (object)] @match))
(ternary_expression condition: [(true) (false) (number) (string)] @match)''',
  "if (true) { run() }\n", "if (enabled) { run() }\n", "The condition is a constant, so one branch is dead code.")
E("no-control-regex", "minor", "correctness",
  r'''((regex pattern: (regex_pattern) @match) (#match? @match "\\\\x[01][0-9a-fA-F]|\\\\u00[01][0-9a-fA-F]"))''',
  "const re = /\\x0c/\n", "const re = /\\x20/\n", "Control characters in a regex are rarely intended and are invisible in source.")
E("no-debugger", "major", "correctness", "(debugger_statement) @match", "function f() {\n  debugger\n}\n", "function f() {\n  return 1\n}\n",
  "debugger statements must not ship to production.")
E("no-dupe-class-members", "major", "correctness",
  r'''((class_body (method_definition name: (property_identifier) @a) @m1 (method_definition name: (property_identifier) @b) @match) (#eq? @a @b) (#not-match? @m1 "^(static\\s+)?(get|set)\\s") (#not-match? @match "^(static\\s+)?(get|set)\\s"))''',
  "class A {\n  run() { return 1 }\n  run() { return 2 }\n}\n", "class A {\n  run() { return 1 }\n  stop() { return 2 }\n}\n",
  "A duplicate class member silently replaces the earlier definition.")
E("no-dupe-else-if", "major", "correctness",
  r'''((if_statement condition: (_) @a alternative: (else_clause (if_statement condition: (_) @b) @match)) (#eq? @a @b))''',
  "if (a) { x() } else if (a) { y() }\n", "if (a) { x() } else if (b) { y() }\n", "The repeated else-if condition can never be true.")
E("no-dupe-keys", "major", "correctness",
  r'''((object (pair key: (property_identifier) @a) (pair key: (property_identifier) @b) @match) (#eq? @a @b))''',
  "const o = { id: 1, name: 'a', id: 2 }\n", "const o = { id: 1, name: 'a' }\n", "Duplicate object keys: the last one wins silently.")
E("no-duplicate-case", "major", "correctness",
  r'''((switch_body (switch_case value: (_) @a) (switch_case value: (_) @b) @match) (#eq? @a @b))''',
  "switch (x) {\n  case 1: a(); break\n  case 1: b(); break\n}\n", "switch (x) {\n  case 1: a(); break\n  case 2: b(); break\n}\n",
  "Duplicate case label: the second case is unreachable.")
E("no-empty-character-class", "major", "correctness",
  r'''((regex pattern: (regex_pattern) @match) (#match? @match "(^|[^\\\\])\\[\\]"))''',
  "const re = /^abc[]/\n", "const re = /^abc[a-z]/\n", "An empty character class [] matches nothing.")
E("no-empty-pattern", "minor", "correctness",
  r'''((variable_declarator name: [(object_pattern) (array_pattern)] @match) (#match? @match "^[\\[{]\\s*[\\]}]$"))''',
  "const {} = props\n", "const { title } = props\n", "An empty destructuring pattern binds nothing (often a typo for a default value).")
E("no-ex-assign", "major", "correctness",
  r'''((catch_clause parameter: (identifier) @a body: (statement_block (expression_statement (assignment_expression left: (identifier) @b) @match))) (#eq? @a @b))''',
  "try { run() } catch (e) {\n  e = 10\n}\n", "try { run() } catch (e) {\n  const code = 10\n}\n", "Reassigning the caught exception loses the original error.")
E("no-fallthrough", "major", "correctness",
  r'''((switch_body (switch_case [(expression_statement) (if_statement) (lexical_declaration) (variable_declaration) (for_statement)] @last .) @match . [(switch_case) (switch_default)]))''',
  "switch (x) {\n  case 1:\n    a()\n  case 2:\n    b()\n    break\n}\n", "switch (x) {\n  case 1:\n    a()\n    break\n  case 2:\n    b()\n    break\n}\n",
  "This case falls through into the next one; add break/return or a // falls through comment.", mode="ai-confirm",
  ai="Is the fall-through into the next case unintended (no deliberate shared handling)?")
E("no-func-assign", "major", "correctness",
  r'''((program (function_declaration name: (identifier) @a) (expression_statement (assignment_expression left: (identifier) @b) @match)) (#eq? @a @b))''',
  "function load() {}\nload = null\n", "function load() {}\nconst loader = null\n", "Reassigning a function declaration is almost always a mistake.")
E("no-import-assign", "critical", "correctness",
  r'''((program (import_statement (import_clause [(identifier) @a (named_imports (import_specifier name: (identifier) @a))])) (expression_statement (assignment_expression left: (identifier) @b) @match)) (#eq? @a @b))''',
  "import config from './config'\nconfig = {}\n", "import config from './config'\nconst local = { ...config }\n", "Imported bindings are read-only; assignment throws.")
E("no-loss-of-precision", "major", "correctness",
  r'''((number) @match (#match? @match "^[0-9]{16,}[13579]$"))''',
  "const id = 12345678901234567\n", "const id = 12345678901234567n\n", "This integer literal cannot be represented exactly as a double; use BigInt or a string.")
E("no-new-native-nonconstructor", "critical", "correctness",
  r'''((new_expression constructor: (identifier) @c) @match (#match? @c "^(Symbol|BigInt)$"))''',
  "const s = new Symbol('id')\n", "const s = Symbol('id')\n", "Symbol and BigInt are not constructors; new throws a TypeError.")
E("no-obj-calls", "critical", "correctness",
  r'''((call_expression function: (identifier) @f) @match (#match? @f "^(Math|JSON|Reflect|Atomics)$"))
((new_expression constructor: (identifier) @f) @match (#match? @f "^(Math|JSON|Reflect|Atomics|Intl)$"))''',
  "const m = Math()\n", "const m = Math.max(1, 2)\n", "Math/JSON/Reflect/Atomics are namespaces, not functions; calling them throws.")
E("no-promise-executor-return", "minor", "async",
  r'''((new_expression constructor: (identifier) @c arguments: (arguments . (arrow_function body: (_) @b))) @match (#eq? @c "Promise") (#not-match? @b "^\\{"))''',
  "const p = new Promise((resolve) => resolve(readConfig()))\n", "const p = new Promise((resolve) => { resolve(readConfig()) })\n",
  "Values returned from a Promise executor are ignored; returning hints at a misunderstanding (or a forgotten resolve).")
E("no-prototype-builtins", "minor", "correctness",
  r'''((call_expression function: (member_expression object: (_) @o property: (property_identifier) @p)) @match (#match? @p "^(hasOwnProperty|isPrototypeOf|propertyIsEnumerable)$") (#not-match? @o "prototype$"))''',
  "if (obj.hasOwnProperty('id')) {}\n", "if (Object.hasOwn(obj, 'id')) {}\n",
  "Calling Object.prototype builtins on the object fails for Object.create(null) objects and can be shadowed by attacker-controlled keys.")
E("no-self-assign", "major", "correctness",
  r'''((assignment_expression left: (_) @a right: (_) @b) @match (#eq? @a @b))''',
  "count = count\n", "count = next\n", "Self-assignment has no effect.")
E("no-self-compare", "major", "correctness",
  r'''((binary_expression left: (_) @a operator: ["==" "===" "!=" "!==" "<" ">" "<=" ">="] right: (_) @b) @match (#eq? @a @b))''',
  "if (x === x) {}\n", "if (!Number.isNaN(x)) {}\n", "Comparing a value with itself is either a bug or an obscure NaN test (use Number.isNaN).")
E("no-setter-return", "minor", "correctness",
  r'''(method_definition "set" body: (statement_block (return_statement (_)) @match))''',
  "class A {\n  set v(x) { return this._v = x }\n}\n", "class A {\n  set v(x) { this._v = x }\n}\n", "Return values from setters are ignored.")
E("no-sparse-arrays", "minor", "correctness",
  r'''((array) @match (#match? @match "^\\[\\s*,|,\\s*,"))''',
  "const a = [1, , 3]\n", "const a = [1, undefined, 3]\n", "Holes in array literals are easy to misread and behave differently from undefined in iteration methods.")
E("no-template-curly-in-string", "major", "correctness",
  r'''((string) @match (#match? @match "\\$\\{[^}]+\\}"))''',
  "const msg = 'Hello ${name}'\n", "const msg = `Hello ${name}`\n", "Template placeholder syntax inside a regular string is printed literally; use a template literal.")
E("no-unreachable", "major", "correctness",
  r'''(statement_block [(return_statement) (throw_statement) (break_statement) (continue_statement)] . [(expression_statement) (lexical_declaration) (variable_declaration) (if_statement) (for_statement) (return_statement) (throw_statement)] @match)''',
  "function f() {\n  return 1\n  cleanup()\n}\n", "function f() {\n  cleanup()\n  return 1\n}\n", "Code after return/throw/break/continue never runs.")
E("no-unsafe-finally", "major", "correctness",
  r'''(finally_clause body: (statement_block [(return_statement) (throw_statement)] @match))''',
  "try { return a() } finally {\n  return 0\n}\n", "try { return a() } finally {\n  cleanup()\n}\n",
  "Control flow in finally overrides the try/catch result and swallows exceptions.")
E("no-unsafe-negation", "major", "correctness",
  r'''(binary_expression left: (unary_expression operator: "!") operator: ["in" "instanceof"]) @match''',
  "if (!key in obj) {}\n", "if (!(key in obj)) {}\n", "! binds tighter than in/instanceof, so this negates the left operand, not the test.")
# Fixture triage (ESLint suite): the paren group must be a bare optional chain (a `??`/`||`
# fallback makes it safe), the call/new must not itself be optional (`(a?.b)?.()`), and only
# array/argument spreads throw (object spread of undefined is fine).
OPT_CHAIN_ONLY = r"^\\(\\s*[\\w$.\\[\\]'\"]*\\?\\.[\\w$.?\\[\\]'\"()]*\\s*\\)$"
E("no-unsafe-optional-chaining", "major", "null-handling",
  r'''((call_expression function: (parenthesized_expression) @p arguments: (arguments)) @match (#match? @p "OPT"))
((call_expression function: (parenthesized_expression) @p arguments: (template_string)) @match (#match? @p "OPT"))
([(array (spread_element (member_expression (optional_chain)) @match)) (arguments (spread_element (member_expression (optional_chain)) @match))])
((new_expression constructor: (parenthesized_expression) @p) @match (#match? @p "OPT"))'''.replace("OPT", OPT_CHAIN_ONLY),
  "(obj?.run)()\n", "obj?.run()\n", "Optional chaining that short-circuits to undefined is then called/spread/constructed, throwing a TypeError.",
  filters=[r"node.lacks_re:^\(.*\)\s*\?\."],
  fp=[{"note": "fallback inside the parens", "code": "(settings?.handler ?? noop)()\n"},
      {"note": "the call is optional too", "code": "(settings?.handler)?.()\n"},
      {"note": "object spread of undefined is allowed", "code": "const merged = { ...defaults?.extra }\n"}])
E("require-atomic-updates", "minor", "concurrency",
  r'''(augmented_assignment_expression right: (await_expression)) @match''',
  "async function add(x) {\n  total += await fetchValue(x)\n}\n", "async function add(x) {\n  const v = await fetchValue(x)\n  total += v\n}\n",
  "The left side is read before the await and written after it, so concurrent calls can lose updates.", mode="ai-confirm",
  ai="Is the updated variable shared state that another async call can modify while this function is suspended?")
E("use-isnan", "critical", "correctness",
  r'''((binary_expression operator: ["==" "===" "!=" "!==" "<" ">" "<=" ">="] right: (identifier) @n) @match (#eq? @n "NaN"))
((binary_expression left: (identifier) @n operator: ["==" "===" "!=" "!==" "<" ">" "<=" ">="]) @match (#eq? @n "NaN"))''',
  "if (value === NaN) {}\n", "if (Number.isNaN(value)) {}\n", "NaN is never equal to anything (including NaN); use Number.isNaN().")
E("valid-typeof", "critical", "correctness",
  r'''((binary_expression left: (unary_expression operator: "typeof") right: (string (string_fragment) @s)) @match (#not-match? @s "^(undefined|object|boolean|number|string|function|symbol|bigint)$"))''',
  "if (typeof x === 'strnig') {}\n", "if (typeof x === 'string') {}\n", "typeof never returns this string, so the comparison is always false.")
E("no-unassigned-vars", "minor", "correctness",
  r'''((program (lexical_declaration kind: "let" (variable_declarator name: (identifier) @a !value)) @match (expression_statement (call_expression arguments: (arguments (identifier) @b)))) (#eq? @a @b))''',
  "let status\nconsole.log(status)\n", "let status = 'ok'\nconsole.log(status)\n",
  "The variable is read but never assigned, so it is always undefined.", mode="ai-confirm",
  ai="Is this variable never assigned anywhere (including in nested functions)?")
E("preserve-caught-error", "minor", "correctness",
  r'''((catch_clause parameter: (identifier) body: (statement_block (throw_statement (new_expression arguments: (arguments) @args)) @match)) (#not-match? @args "cause"))''',
  "try { parse() } catch (err) {\n  throw new Error('parse failed')\n}\n", "try { parse() } catch (err) {\n  throw new Error('parse failed', { cause: err })\n}\n",
  "The re-thrown error drops the original; pass { cause: err } to keep the chain.", applies={"ecmascript": ">=2022"})

# ---------------------------------------------------------------- suggestions / style guide
E("arrow-body-style", "info", "style",
  r'''(arrow_function body: (statement_block . (return_statement (_)) .) @match)''',
  "const sq = (x) => { return x * x }\n", "const sq = (x) => x * x\n", "A block body that only returns can be a concise arrow body.")
E("class-methods-use-this", "info", "style",
  r'''((method_definition name: (property_identifier) @n body: (statement_block) @b) @match (#not-eq? @n "constructor") (#not-match? @b "this|super") (#not-match? @match "^(static|get|set)\\s"))''',
  "class Fmt {\n  pad(s) { return s.padStart(4) }\n}\n", "class Fmt {\n  static pad(s) { return s.padStart(4) }\n}\n",
  "The method does not use this; consider a static method or a plain function.", mode="ai-confirm",
  ai="Is this method part of a polymorphic interface (overridden/implemented) where it must stay an instance method?")
E("curly", "info", "style",
  r'''(if_statement consequence: [(expression_statement) (return_statement) (throw_statement)] @match)''',
  "if (ok) run()\n", "if (ok) {\n  run()\n}\n", "Omitting braces invites bugs when a second statement is added.")
E("default-case", "minor", "correctness",
  r'''((switch_statement body: (switch_body) @b) @match (#not-match? @b "default|(?i)no default"))''',
  "switch (kind) {\n  case 'a': a(); break\n}\n", "switch (kind) {\n  case 'a': a(); break\n  default: unknown(kind)\n}\n",
  "A switch without default silently ignores unexpected values.")
E("default-case-last", "minor", "correctness",
  r'''(switch_body (switch_default) @match . (switch_case))''',
  "switch (x) {\n  default: d(); break\n  case 1: a(); break\n}\n", "switch (x) {\n  case 1: a(); break\n  default: d()\n}\n",
  "A default clause that is not last is easy to misread.")
E("default-param-last", "minor", "correctness",
  r'''(formal_parameters (assignment_pattern) @match . [(identifier) (object_pattern) (array_pattern)])''',
  "function f(a = 1, b) {}\n", "function f(b, a = 1) {}\n", "A defaulted parameter before a required one cannot be omitted by callers.", grammar="javascript")
E("dot-notation", "info", "style",
  r'''((subscript_expression index: (string (string_fragment) @s)) @match (#match? @s "^[A-Za-z_$][A-Za-z0-9_$]*$"))''',
  "const v = obj['name']\n", "const v = obj.name\n", "Use dot notation for identifier-like keys.")
E("guard-for-in", "minor", "correctness",
  r'''((for_in_statement "in" body: (statement_block) @b) @match (#not-match? @b "^\\{\\s*if"))''',
  "for (const k in obj) {\n  use(obj[k])\n}\n", "for (const k in obj) {\n  if (Object.hasOwn(obj, k)) use(obj[k])\n}\n",
  "for...in also iterates inherited enumerable properties; guard with Object.hasOwn or use Object.keys().")
E("logical-assignment-operators", "info", "style",
  r'''((assignment_expression left: (identifier) @a right: (binary_expression left: (identifier) @b operator: ["||" "&&" "??"])) @match (#eq? @a @b))''',
  "opts = opts || {}\n", "opts ||= {}\n", "Use the logical assignment operator (||=, &&=, ??=).", applies={"ecmascript": ">=2021"})
E("new-cap", "minor", "style",
  r'''((new_expression constructor: (identifier) @c) @match (#match? @c "^[a-z]"))''',
  "const w = new widget()\n", "const w = new Widget()\n", "Constructors should start with an upper-case letter so they are not called without new.")
E("no-alert", "minor", "style",
  r'''((call_expression function: (identifier) @f) @match (#match? @f "^(alert|confirm|prompt)$"))
((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @f)) @match (#match? @o "^(window|globalThis)$") (#match? @f "^(alert|confirm|prompt)$"))''',
  "alert('Saved')\n", "toast.show('Saved')\n", "alert/confirm/prompt block the UI thread and are usually leftover debugging.")
E("no-array-constructor", "minor", "style",
  r'''((new_expression constructor: (identifier) @c arguments: (arguments) @a) @match (#eq? @c "Array") (#not-match? @a "^\\(\\s*[^,]*\\s*\\)$"))
((new_expression constructor: (identifier) @c arguments: (arguments) @a) @match (#eq? @c "Array") (#eq? @a "()"))''',
  "const a = new Array(1, 2, 3)\n", "const a = [1, 2, 3]\n", "The Array constructor is ambiguous for a single numeric argument; use an array literal.")
E("no-case-declarations", "major", "correctness",
  r'''(switch_case [(lexical_declaration) (class_declaration) (function_declaration)] @match)''',
  "switch (x) {\n  case 1:\n    let y = 1\n    break\n}\n", "switch (x) {\n  case 1: {\n    let y = 1\n    break\n  }\n}\n",
  "Lexical declarations in a case are visible in the whole switch but only initialised in that case.")
E("no-console", "info", "style",
  r'''((call_expression function: (member_expression object: (identifier) @o)) @match (#eq? @o "console"))''',
  "console.log(user)\n", "logger.debug(user)\n", "console calls usually should not ship; use the application logger.")
E("no-constructor-return", "minor", "correctness",
  r'''((method_definition name: (property_identifier) @n body: (statement_block (return_statement (_)) @match)) (#eq? @n "constructor"))''',
  "class A {\n  constructor() { return {} }\n}\n", "class A {\n  constructor() { this.x = 1 }\n}\n", "Returning a value from a constructor replaces the instance.")
E("no-delete-var", "major", "correctness", r'''(unary_expression operator: "delete" argument: (identifier)) @match''',
  "let x = 1\ndelete x\n", "let x = 1\nx = undefined\n", "delete on a variable does nothing (and is a SyntaxError in strict mode).")
E("no-else-return", "info", "style",
  r'''(if_statement consequence: (statement_block (return_statement) .) alternative: (else_clause) @match)''',
  "function f(a) {\n  if (a) { return 1 } else { return 2 }\n}\n", "function f(a) {\n  if (a) { return 1 }\n  return 2\n}\n",
  "The else is unnecessary after a return.")
E("no-empty", "minor", "correctness",
  r'''((if_statement consequence: (statement_block) @match) (#match? @match "^\\{\\s*\\}$"))
((catch_clause body: (statement_block) @match) (#match? @match "^\\{\\s*\\}$"))
((try_statement body: (statement_block) @match) (#match? @match "^\\{\\s*\\}$"))
((finally_clause body: (statement_block) @match) (#match? @match "^\\{\\s*\\}$"))''',
  "try { run() } catch (e) {}\n", "try { run() } catch (e) {\n  log.warn(e)\n}\n", "Empty block: a silently swallowed error or unfinished code. Add a comment if intended.")
E("no-empty-function", "info", "style",
  r'''((function_declaration body: (statement_block) @b) @match (#match? @b "^\\{\\s*\\}$"))
((method_definition name: (property_identifier) @n body: (statement_block) @b) @match (#match? @b "^\\{\\s*\\}$") (#not-eq? @n "constructor"))''',
  "function noop() {}\n", "function noop() {\n  // intentionally empty: default handler\n}\n", "Empty function without a comment explaining why.")
E("no-empty-static-block", "info", "style",
  r'''((class_static_block body: (statement_block) @b) @match (#match? @b "^\\{\\s*\\}$"))''',
  "class A {\n  static {}\n}\n", "class A {\n  static { init() }\n}\n", "Empty static initialisation block.", applies={"ecmascript": ">=2022"})
E("no-extend-native", "major", "correctness",
  r'''((assignment_expression left: (member_expression object: (member_expression object: (identifier) @o property: (property_identifier) @p))) @match (#match? @o "^(Object|Array|String|Number|Boolean|Function|Date|RegExp|Promise|Map|Set|Error|Symbol)$") (#eq? @p "prototype"))''',
  "Array.prototype.last = function () { return this[this.length - 1] }\n", "const last = (arr) => arr[arr.length - 1]\n",
  "Extending native prototypes can clash with future standard methods and other libraries.")
E("no-extra-bind", "minor", "correctness",
  r'''((call_expression function: (member_expression object: (parenthesized_expression (arrow_function)) property: (property_identifier) @p)) @match (#eq? @p "bind"))''',
  "const f = (() => this.x).bind(this)\n", "const f = () => this.x\n", "Arrow functions cannot be re-bound; .bind() here is useless.")
E("no-extra-boolean-cast", "info", "style",
  r'''(if_statement condition: (parenthesized_expression (unary_expression operator: "!" argument: (unary_expression operator: "!")) @match))
((if_statement condition: (parenthesized_expression (call_expression function: (identifier) @f) @match)) (#eq? @f "Boolean"))''',
  "if (!!user) {}\n", "if (user) {}\n", "The condition is already coerced to boolean.")
E("no-global-assign", "major", "correctness",
  r'''((assignment_expression left: (identifier) @a) @match (#match? @a "^(Object|Array|String|Number|Boolean|Math|JSON|Promise|window|globalThis|document|NaN|Infinity)$"))''',
  "window = {}\n", "const win = {}\n", "Assigning to a native global breaks every other user of it.")
E("no-implicit-coercion", "info", "style",
  r'''((binary_expression left: (string) @s operator: "+") @match (#match? @s "^(''|\"\")$"))
((unary_expression operator: "~" argument: (call_expression function: (member_expression property: (property_identifier) @p))) @match (#eq? @p "indexOf"))''',
  "const s = '' + count\n", "const s = String(count)\n", "Implicit type coercion is hard to read; use String()/Number()/Boolean() or includes().")
E("no-iterator", "minor", "deprecation",
  r'''((member_expression property: (property_identifier) @p) @match (#eq? @p "__iterator__"))''',
  "Foo.prototype.__iterator__ = function () {}\n", "Foo.prototype[Symbol.iterator] = function* () {}\n",
  "__iterator__ is an obsolete SpiderMonkey extension; use Symbol.iterator.", kind="deprecation")
E("no-labels", "info", "style", r'''(labeled_statement) @match''',
  "outer: for (const a of xs) { for (const b of ys) { if (b) break outer } }\n", "for (const a of xs) { if (ys.some(Boolean)) break }\n",
  "Labels make control flow hard to follow.")
E("no-lonely-if", "info", "style",
  r'''(else_clause (statement_block . (if_statement) @match .))''',
  "if (a) { x() } else {\n  if (b) { y() }\n}\n", "if (a) { x() } else if (b) { y() }\n", "A lone if inside else can be else if.")
E("no-loop-func", "minor", "correctness",
  r'''(for_statement initializer: (variable_declaration) body: (statement_block (expression_statement (call_expression arguments: (arguments [(arrow_function) (function_expression)] @match)))))''',
  "for (var i = 0; i < 3; i++) {\n  handlers.push(() => i)\n}\n", "for (let i = 0; i < 3; i++) {\n  const n = i\n  handlers.push(() => n)\n}\n",
  "A function created in a loop captures the loop variable; with var all closures see the final value.", mode="ai-confirm",
  ai="Does the closure capture a var-declared (function-scoped) loop variable or a variable modified later in the loop?")
E("no-multi-assign", "info", "style",
  r'''(assignment_expression right: (assignment_expression)) @match
(variable_declarator value: (assignment_expression) @match)''',
  "a = b = c\n", "a = c\nb = c\n", "Chained assignments are hard to read and can create implicit globals.")
E("no-multi-str", "info", "style",
  r'''((string) @match (#match? @match "\\\\\\n"))''',
  "const s = 'line one \\\nline two'\n", "const s = `line one\nline two`\n", "Line-continuation in string literals is easy to break; use template literals or concatenation.")
E("no-negated-condition", "info", "style",
  r'''(if_statement condition: (parenthesized_expression (unary_expression operator: "!")) alternative: (else_clause) @match)''',
  "if (!ok) { fail() } else { pass() }\n", "if (ok) { pass() } else { fail() }\n", "A negated condition with an else branch reads better inverted.")
E("no-nested-ternary", "info", "style",
  r'''(ternary_expression alternative: (ternary_expression) @match)
(ternary_expression consequence: (ternary_expression) @match)''',
  "const s = a ? 'x' : b ? 'y' : 'z'\n", "const s = pick(a, b)\n", "Nested ternaries are hard to read.")
E("no-new", "minor", "correctness", r'''(expression_statement (new_expression) @match)''',
  "new Widget(el)\n", "const widget = new Widget(el)\n", "Constructing an object only for side effects hides intent (and the instance is discarded).")
E("no-new-func", "critical", "security",
  r'''((new_expression constructor: (identifier) @c) @match (#eq? @c "Function"))
((call_expression function: (identifier) @c) @match (#eq? @c "Function"))''',
  "const add = new Function('a', 'b', 'return a + b')\n", "const add = (a, b) => a + b\n",
  "The Function constructor evaluates strings as code (like eval) - an injection sink and CSP violation.", kind="security")
E("no-nonoctal-decimal-escape", "minor", "correctness",
  r'''((string) @match (#match? @match "\\\\[89]"))''',
  "const s = '\\8'\n", "const s = '8'\n", "\\8 and \\9 are useless legacy escapes.")
E("no-object-constructor", "info", "style",
  r'''((new_expression constructor: (identifier) @c arguments: (arguments) @a) @match (#eq? @c "Object") (#eq? @a "()"))''',
  "const o = new Object()\n", "const o = {}\n", "Use an object literal.")
E("no-octal", "minor", "correctness", r'''((number) @match (#match? @match "^0[0-7]+$"))''',
  "const mode = 0755\n", "const mode = 0o755\n", "Legacy octal literals are confusing and forbidden in strict mode; use 0o.")
E("no-octal-escape", "minor", "correctness",
  r'''((string) @match (#match? @match "\\\\([1-7]|0[0-9])"))''',
  "const s = 'copy \\251'\n", "const s = 'copy \\u00A9'\n", "Octal escapes are deprecated; use \\u or \\x escapes.")
E("no-param-reassign", "minor", "correctness",
  r'''((function_declaration parameters: (formal_parameters (identifier) @p) body: (statement_block (expression_statement (assignment_expression left: (identifier) @a) @match))) (#eq? @p @a))''',
  "function f(opts) {\n  opts = opts || {}\n}\n", "function f(opts) {\n  const o = opts || {}\n}\n", "Reassigning parameters obscures the original value and mutates arguments in sloppy mode.", grammar="javascript")
E("no-regex-spaces", "info", "style", r'''((regex pattern: (regex_pattern) @match) (#match? @match "[^ \\]]  +"))''',
  "const re = /foo   bar/\n", "const re = /foo {3}bar/\n", "Multiple literal spaces in a regex are hard to count; use a quantifier.")
E("no-return-assign", "minor", "correctness",
  r'''(return_statement (assignment_expression) @match)
(arrow_function body: (assignment_expression) @match)''',
  "function f() {\n  return x = 1\n}\n", "function f() {\n  x = 1\n  return x\n}\n", "An assignment in a return is often a mistyped comparison.")
E("no-script-url", "major", "security",
  r'''((string) @match (#match? @match "^['\"]\\s*(?i)javascript:"))''',
  "a.href = 'javascript:void(0)'\n", "a.addEventListener('click', onClick)\n", "javascript: URLs are a form of eval and an XSS vector.", kind="security",
  # corpus 2026-10-10 (react-router): the literal as a member of an all-string deny-list, a
  # comparison operand or a prefix/membership test argument is a sanitizer check, not a script URL
  filters=[r"""parentkind.lacks_re:array:^\[\s*(?:['"][^'"]*['"]\s*,\s*)*['"][^'"]*['"]\s*,?\s*\]$""",
           r"""parent.lacks_re:^(?s).*(===?|!==?)\s*['"]\s*(?i:javascript):[^'"]*['"]\s*$|^\s*['"]\s*(?i:javascript):[^'"]*['"]\s*(===?|!==?)""",
           r"ancestor.lacks_re:call_expression:^[\w$.\[\]()]*\.(startsWith|endsWith|includes|indexOf|test|match|has)\("],
  fp=["const UNSAFE_PROTOCOLS = new Set([\n  'javascript:',\n  'vbscript:',\n  'data:',\n])\n",
      "if (url.protocol === 'javascript:') {\n  throw new Error('blocked')\n}\n",
      "if (href.trim().toLowerCase().startsWith('javascript:')) {\n  return '#'\n}\n"])
E("no-sequences", "minor", "correctness", r'''(expression_statement (sequence_expression) @match)''',
  "a = 1, b = 2\n", "a = 1\nb = 2\n", "The comma operator discards all but the last value and hides mistakes.")
E("no-shadow-restricted-names", "major", "correctness",
  r'''((variable_declarator name: (identifier) @n) @match (#match? @n "^(NaN|Infinity|eval|arguments)$"))''',
  "function f() {\n  const Infinity = 0\n}\n", "function f() {\n  const limit = 0\n}\n", "Shadowing restricted global names is confusing and error-prone.")
E("no-undef-init", "info", "style",
  r'''(lexical_declaration kind: "let" (variable_declarator value: (undefined)) @match)''',
  "let x = undefined\n", "let x\n", "Initialising to undefined is redundant.")
E("no-unneeded-ternary", "info", "style",
  r'''(ternary_expression consequence: (true) alternative: (false)) @match
(ternary_expression consequence: (false) alternative: (true)) @match''',
  "const ok = a > b ? true : false\n", "const ok = a > b\n", "A ternary returning boolean literals is just the condition.")
E("no-unused-expressions", "minor", "correctness",
  r'''(expression_statement [(identifier) (member_expression) (number) (binary_expression operator: ["==" "===" "!=" "!==" "<" ">" "<=" ">=" "+" "-" "*" "/"])] @match)''',
  "a === b\n", "result = a === b\n", "The expression has no effect (likely a missing assignment or call).")
E("no-useless-call", "minor", "performance",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . [(undefined) (null)])) @match (#eq? @p "call"))''',
  "fn.call(undefined, a, b)\n", "fn(a, b)\n", "call() with undefined/null this is a slower plain call.")
E("no-useless-catch", "minor", "correctness",
  r'''((catch_clause parameter: (identifier) @e body: (statement_block . (throw_statement (identifier) @t) .)) @match (#eq? @e @t))''',
  "try { run() } catch (e) {\n  throw e\n}\n", "run()\n", "A catch that only rethrows is redundant.")
E("no-useless-computed-key", "info", "style", r'''(pair key: (computed_property_name (string)) @match)''',
  "const o = { ['a']: 1 }\n", "const o = { a: 1 }\n", "Computed key with a string literal is unnecessary.")
E("no-useless-concat", "info", "style",
  r'''((binary_expression left: (string) operator: "+" right: (string)) @match (#not-match? @match "\\n"))''',
  "const s = 'a' + 'b'\n", "const s = 'ab'\n", "Concatenating two literals on one line is redundant.")
E("no-useless-constructor", "info", "style",
  r'''((class_declaration body: (class_body (method_definition name: (property_identifier) @n parameters: (formal_parameters) @fp body: (statement_block) @b) @inner)) @match (#eq? @n "constructor") (#eq? @fp "()") (#match? @b "^\\{\\s*\\}$") (#not-match? @match "^class\\s+\\w+\\s+extends"))''',
  "class A {\n  constructor() {}\n}\n", "class A {\n  constructor() { this.x = 1 }\n}\n", "An empty constructor is redundant.", capture="inner")
E("no-useless-escape", "info", "style",
  r'''((string (escape_sequence) @match) (#match? @match "^\\\\[dDwWsS.()\\[\\]]$"))''',
  "const re = new RegExp('\\d+')\n", "const re = /\\d+/\n", "This escape has no meaning in a string literal (the backslash is dropped), usually a regex escape mistake.")
E("no-useless-rename", "info", "style",
  r'''((pair_pattern key: (property_identifier) @k value: (identifier) @v) @match (#eq? @k @v))
((import_specifier name: (identifier) @k alias: (identifier) @v) @match (#eq? @k @v))''',
  "const { a: a } = obj\n", "const { a } = obj\n", "Renaming to the same name is redundant.")
E("no-useless-return", "info", "style",
  r'''((function_declaration body: (statement_block (return_statement) @match .)) (#match? @match "^return;?$"))''',
  "function f() {\n  work()\n  return\n}\n", "function f() {\n  work()\n}\n", "A bare return at the end of a function is redundant.")
E("no-void", "info", "style", r'''(unary_expression operator: "void") @match''',
  "const u = void 0\n", "const u = undefined\n", "void is confusing; use undefined (or handle the promise explicitly).")
E("no-warning-comments", "info", "maintainability", r'''((comment) @match (#match? @match "(?i)\\b(todo|fixme|xxx)\\b"))''',
  "// TODO: handle errors\nrun()\n", "// handled by the caller\nrun()\n", "Unresolved TODO/FIXME comment.")
E("object-shorthand", "info", "style",
  r'''((object (pair key: (property_identifier) @k value: (identifier) @v) @match) (#eq? @k @v))
(object (pair value: (function_expression)) @match)''',
  "const o = { name: name }\n", "const o = { name }\n", "Use shorthand properties/methods.", applies={"ecmascript": ">=2015"})
E("operator-assignment", "info", "style",
  r'''((assignment_expression left: (identifier) @a right: (binary_expression left: (identifier) @b operator: ["+" "-" "*" "/" "%" "**"])) @match (#eq? @a @b))''',
  "total = total + n\n", "total += n\n", "Use the compound assignment operator.")
E("prefer-arrow-callback", "info", "style",
  r'''((arguments (function_expression) @match) (#not-match? @match "\\bthis\\b|\\barguments\\b"))''',
  "items.forEach(function (x) { use(x) })\n", "items.forEach((x) => use(x))\n", "Use an arrow function for callbacks that do not need their own this.", applies={"ecmascript": ">=2015"})
E("prefer-exponentiation-operator", "info", "style",
  r'''((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p)) @match (#eq? @o "Math") (#eq? @p "pow"))''',
  "const a = Math.pow(2, 8)\n", "const a = 2 ** 8\n", "Use ** instead of Math.pow.", applies={"ecmascript": ">=2016"})
E("prefer-named-capture-group", "info", "style",
  r'''((regex pattern: (regex_pattern) @match) (#match? @match "(^|[^\\\\])\\(([^?]|$)"))''',
  "const re = /(\\d{4})-(\\d{2})/\n", "const re = /(?<year>\\d{4})-(?<month>\\d{2})/\n", "Use named capture groups for readability.", applies={"ecmascript": ">=2018"})
E("prefer-numeric-literals", "info", "style",
  r'''((call_expression function: (identifier) @f arguments: (arguments (string) (number) @n)) @match (#eq? @f "parseInt") (#match? @n "^(2|8|16)$"))''',
  "const n = parseInt('111110111', 2)\n", "const n = 0b111110111\n", "Use binary/octal/hex literals instead of parseInt on a literal.", applies={"ecmascript": ">=2015"})
E("prefer-object-spread", "info", "style",
  r'''((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p) arguments: (arguments . (object) @first)) @match (#eq? @o "Object") (#eq? @p "assign") (#match? @first "^\\{\\s*\\}$"))''',
  "const c = Object.assign({}, a, b)\n", "const c = { ...a, ...b }\n", "Use object spread instead of Object.assign({}, ...).", applies={"ecmascript": ">=2018"},
  # fixture triage: spread arguments, accessors and __proto__ do not translate to a literal;
  # a local `Object` binding is not the global
  filters=[r"node.lacks_re:\.\.\.|\b(get|set)\s+[\w$\[]|__proto__", r"file.lacks_re:(?m)^\s*(?:(?:const|let|var)\s+)?Object\s*="],
  fp=[{"note": "spread argument", "code": "const c = Object.assign({}, ...parts)\n"},
      {"note": "getter is invoked by assign", "code": "const c = Object.assign({}, { get id() { return next() } })\n"},
      {"note": "local Object binding", "code": "const Object = makeShim()\nconst c = Object.assign({}, a)\n"}])
E("prefer-promise-reject-errors", "minor", "async",
  r'''((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p) arguments: (arguments . [(string) (number) (template_string) (object)])) @match (#eq? @o "Promise") (#eq? @p "reject"))''',
  "return Promise.reject('failed')\n", "return Promise.reject(new Error('failed'))\n", "Reject with Error objects so stack traces survive.")
E("prefer-regex-literals", "info", "style",
  r'''((new_expression constructor: (identifier) @c arguments: (arguments . (string) . (string)? .)) @match (#eq? @c "RegExp"))''',
  "const re = new RegExp('^abc$', 'i')\n", "const re = /^abc$/i\n", "Use a regex literal for static patterns (no double escaping, compiled once).")
E("prefer-rest-params", "info", "style",
  r'''((member_expression object: (identifier) @a) @match (#eq? @a "arguments"))
((subscript_expression object: (identifier) @a) @match (#eq? @a "arguments"))''',
  "function f() {\n  return arguments.length\n}\n", "function f(...args) {\n  return args.length\n}\n", "Use rest parameters instead of arguments.", applies={"ecmascript": ">=2015"})
E("prefer-spread", "info", "style",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . [(undefined) (null)])) @match (#eq? @p "apply"))''',
  "Math.max.apply(null, nums)\n", "Math.max(...nums)\n", "Use spread instead of .apply().", applies={"ecmascript": ">=2015"})
E("prefer-template", "info", "style",
  r'''(binary_expression left: (string) operator: "+" right: [(identifier) (member_expression) (call_expression)]) @match''',
  "const s = 'Hello ' + name\n", "const s = `Hello ${name}`\n", "Use a template literal instead of string concatenation.", applies={"ecmascript": ">=2015"})
E("require-await", "minor", "async",
  r'''((function_declaration "async" body: (statement_block) @b) @match (#not-match? @b "await"))
((arrow_function "async" body: (statement_block) @b) @match (#not-match? @b "await"))
((method_definition "async" body: (statement_block) @b) @match (#not-match? @b "await"))''',
  "async function load() {\n  return cache.get(k)\n}\n", "async function load() {\n  return await db.get(k)\n}\n",
  "async function without await: the async wrapper only adds overhead (or an await is missing).", applies={"ecmascript": ">=2017"})
E("require-yield", "minor", "correctness",
  r'''((generator_function_declaration body: (statement_block) @b) @match (#not-match? @b "yield") (#not-match? @b "^\\{\\s*\\}$"))''',
  "function* gen() {\n  return 1\n}\n", "function* gen() {\n  yield 1\n}\n", "A generator that never yields.")
E("symbol-description", "info", "style",
  r'''((call_expression function: (identifier) @f arguments: (arguments) @a) @match (#eq? @f "Symbol") (#eq? @a "()"))''',
  "const s = Symbol()\n", "const s = Symbol('cache-key')\n", "Give symbols a description for debugging.")
E("yoda", "info", "style",
  r'''(binary_expression left: [(string) (number)] operator: ["===" "==" "!==" "!="] right: (identifier)) @match''',
  "if ('red' === color) {}\n", "if (color === 'red') {}\n", "Put the literal on the right side of the comparison.")
E("no-duplicate-imports", "minor", "correctness",
  r'''((program (import_statement source: (string) @a) (import_statement source: (string) @b) @match) (#eq? @a @b) (#not-match? @match "^import\\s+type"))''',
  "import { a } from 'lib'\nimport { b } from 'lib'\n", "import { a, b } from 'lib'\n", "Merge imports from the same module.")
E("no-lone-blocks", "info", "style",
  r'''((program (statement_block) @match) (#not-match? @match "\\b(let|const|class|function)\\b"))''',
  "{\n  run()\n}\n", "run()\n", "A standalone block without block-scoped declarations is redundant.")
E("camelcase", "info", "style",
  r'''((variable_declarator name: (identifier) @match) (#match? @match "^[a-z][a-z0-9]*_[a-z0-9_]+$"))''',
  "const user_name = 'a'\n", "const userName = 'a'\n", "Use camelCase identifiers.")
E("eqeqeq", "minor", "correctness",
  r'''((binary_expression operator: ["==" "!="] right: (_) @r) @match (#not-match? @r "^(null)$"))''',
  "if (a == b) {}\n", "if (a === b) {}\n", "Use === / !== (null comparisons are allowed by the \"smart\" option).", id="JS-EQEQEQ-SMART")
E("no-eq-null", "info", "style",
  r'''(binary_expression operator: ["==" "!="] right: (null)) @match''',
  "if (x == null) {}\n", "if (x === null || x === undefined) {}\n", "Loose comparison with null also matches undefined; make the intent explicit.")
E("no-underscore-dangle", "info", "style",
  r'''((variable_declarator name: (identifier) @match) (#match? @match "^_[A-Za-z]|[A-Za-z]_$"))''',
  "const _secret = 1\n", "const secret = 1\n", "Dangling underscores do not make things private; use #private fields or module scope.")
E("func-names", "info", "style",
  r'''(variable_declarator value: (function_expression !name) @match)''',
  "const f = function () {}\n", "const f = function load() {}\n", "Named function expressions give better stack traces.")
E("no-bitwise", "info", "correctness",
  r'''(binary_expression operator: ["|" "&"] right: (number)) @match''',
  "const n = x | 0\n", "const n = Math.trunc(x)\n", "Bitwise operators are often typos for || / && or obscure truncation.", mode="ai-confirm",
  ai="Is this bitwise operator a likely typo or obscure coercion rather than intentional bit manipulation?")
E("no-plusplus", "info", "style", r'''(expression_statement (update_expression) @match)''',
  "i++\n", "i += 1\n", "Unary ++/-- are subject to automatic semicolon insertion pitfalls.")
E("prefer-destructuring", "info", "style",
  r'''((variable_declarator name: (identifier) @n value: (member_expression property: (property_identifier) @p)) @match (#eq? @n @p))''',
  "const name = user.name\n", "const { name } = user\n", "Use object destructuring.", applies={"ecmascript": ">=2015"})
E("no-unused-private-class-members", "minor", "correctness",
  r'''((class_body (field_definition property: (private_property_identifier) @f)) @match (#match? @match "^\\{[^#]*#[A-Za-z_$][\\w$]*[^#]*\\}$"))''',
  "class A {\n  #secret = 1\n  get() { return 2 }\n}\n", "class A {\n  #secret = 1\n  get() { return this.#secret }\n}\n",
  "A private field that is never read is dead state.", capture="f", applies={"ecmascript": ">=2022"}, grammar="javascript")
E("require-unicode-regexp", "info", "correctness",
  r'''((regex !flags) @match)
((regex flags: (regex_flags) @f) @match (#not-match? @f "[uv]"))''',
  "const re = /😀+/\n", "const re = /😀+/u\n", "Without the u/v flag, regexes treat surrogate pairs as two characters.", applies={"ecmascript": ">=2015"})

# ---------------------------------------------------------------- Node.js deprecations / removals
NODE = "https://nodejs.org/api/deprecations.html"
NODEV = "Node.js v24 API docs (latest)"


def N(id, title, dep, query, bad, good, msg, sev="minor", kind="deprecation", cat="deprecation", url=NODE, quote=None, **kw):
    R.append(rule("JS-NODE-" + id, title, language="javascript", kind=kind, category=cat, severity=sev, applies=ES, message=msg,
                  url=url, doc=f"Node.js deprecations - {dep}" if url == NODE else "Node.js API docs", doc_version=NODEV,
                  quote=quote or dep, bad=bad, good=good, query=query, tags=["nodejs", dep.split(":")[0]] if url == NODE else ["nodejs"], **kw))


def mcall(obj, prop):
    return f'((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p)) @match (#match? @o "^({obj})$") (#match? @p "^({prop})$"))'


N("BUFFER-CTOR-001", "Buffer() constructor is deprecated (may expose uninitialised memory)", "DEP0005: Buffer() constructor",
  r'''((new_expression constructor: (identifier) @c) @match (#eq? @c "Buffer"))
((call_expression function: (identifier) @c) @match (#eq? @c "Buffer"))''',
  "const b = new Buffer(size)\n", "const b = Buffer.alloc(size)\n",
  "new Buffer()/Buffer() is deprecated (DEP0005); use Buffer.alloc(), Buffer.allocUnsafe() or Buffer.from().", sev="major", kind="security", cat="security")
N("CREATECIPHER-001", "crypto.createCipher/createDecipher were removed (weak key derivation)", "DEP0106: crypto.createCipher and crypto.createDecipher",
  r'''((call_expression function: (member_expression property: (property_identifier) @p)) @match (#match? @p "^(createCipher|createDecipher)$"))''',
  "const c = crypto.createCipher('aes-256-cbc', password)\n", "const c = crypto.createCipheriv('aes-256-gcm', key, iv)\n",
  "createCipher/createDecipher derive keys with MD5 and no salt and are removed in current Node.js; use createCipheriv with a proper KDF.", sev="critical", kind="removal", cat="security")
N("URL-PARSE-001", "url.parse() is insecure; use the WHATWG URL API", "DEP0169: Insecure url.parse()", mcall("url", "parse"),
  "const u = url.parse(req.url)\n", "const u = new URL(req.url, base)\n",
  "url.parse() uses a non-standard algorithm prone to hostname spoofing; use new URL().", sev="major", kind="security", cat="security")
N("UTIL-IS-001", "util.is*() type checks were removed", "DEP0044: util.isArray()", mcall("util", "is(Array|Boolean|Buffer|Date|Error|Function|Null|NullOrUndefined|Number|Object|Primitive|RegExp|String|Symbol|Undefined)"),
  "if (util.isArray(x)) {}\n", "if (Array.isArray(x)) {}\n", "util.is*() helpers are deprecated/removed; use Array.isArray, typeof, instanceof.", sev="major", kind="removal")
N("PROCESS-BINDING-001", "process.binding() is deprecated", "DEP0111: process.binding()", mcall("process", "binding"),
  "const fsb = process.binding('fs')\n", "const fs = require('node:fs')\n", "process.binding() exposes internals and is deprecated; use public modules.")
N("FS-EXISTS-001", "fs.exists() is deprecated", "DEP0034: fs.exists(path, callback)", mcall("fs", "exists"),
  "fs.exists(p, (ok) => {})\n", "fs.access(p, (err) => {})\n", "fs.exists() is deprecated; use fs.access()/fs.stat() (or fs.existsSync).")
N("OS-TMPDIR-001", "os.tmpDir() was removed", "DEP0022: os.tmpDir()", mcall("os", "tmpDir"),
  "const d = os.tmpDir()\n", "const d = os.tmpdir()\n", "os.tmpDir() is removed; use os.tmpdir().", sev="major", kind="removal")
N("SLOWBUFFER-001", "SlowBuffer was removed", "DEP0030: SlowBuffer",
  r'''((new_expression constructor: (identifier) @c) @match (#eq? @c "SlowBuffer"))''', "const b = new SlowBuffer(10)\n", "const b = Buffer.allocUnsafeSlow(10)\n",
  "SlowBuffer is removed; use Buffer.allocUnsafeSlow().", sev="major", kind="removal")
N("FS-MODE-CONST-001", "fs.F_OK/R_OK/W_OK/X_OK are deprecated", "DEP0176: fs.F_OK , fs.R_OK , fs.W_OK , fs.X_OK",
  r'''((member_expression object: (identifier) @o property: (property_identifier) @p) @match (#eq? @o "fs") (#match? @p "^[FRWX]_OK$"))''',
  "fs.accessSync(p, fs.R_OK)\n", "fs.accessSync(p, fs.constants.R_OK)\n", "Use fs.constants.F_OK etc.")
N("SHELL-ARGS-001", "Passing args to spawn/execFile with shell: true is deprecated (and unsafe)", "DEP0190: Passing args to node:child_process execFile / spawn with shell option",
  r'''((call_expression function: [(identifier) @f (member_expression property: (property_identifier) @f)] arguments: (arguments (_) (array) (object) @opt)) @match (#match? @f "^(spawn|spawnSync|execFile|execFileSync)$") (#match? @opt "shell\\s*:\\s*true"))''',
  "spawn('ls', [dir], { shell: true })\n", "spawn('ls', [dir])\n",
  "With shell: true the args are concatenated unescaped into a shell command line (injection risk); drop shell or pass a single vetted command.", sev="major", kind="security", cat="security")
N("PUNYCODE-001", "node:punycode is deprecated", "DEP0040: node:punycode module",
  r'''((call_expression function: (identifier) @f arguments: (arguments (string (string_fragment) @m))) @match (#eq? @f "require") (#match? @m "^(node:)?punycode$"))
((import_statement source: (string (string_fragment) @m)) @match (#match? @m "^(node:)?punycode$"))''',
  "const punycode = require('punycode')\n", "const { domainToASCII } = require('node:url')\n", "Use url.domainToASCII or the userland punycode package.")
N("DOMAIN-001", "node:domain is deprecated", "DEP0032: node:domain module",
  r'''((call_expression function: (identifier) @f arguments: (arguments (string (string_fragment) @m))) @match (#eq? @f "require") (#match? @m "^(node:)?domain$"))
((import_statement source: (string (string_fragment) @m)) @match (#match? @m "^(node:)?domain$"))''',
  "const domain = require('domain')\n", "const { AsyncLocalStorage } = require('node:async_hooks')\n", "The domain module is deprecated; use AsyncLocalStorage / proper error handling.")
N("SYS-001", "require('sys') was removed", "DEP0025: require('node:sys')",
  r'''((call_expression function: (identifier) @f arguments: (arguments (string (string_fragment) @m))) @match (#eq? @f "require") (#match? @m "^(node:)?sys$"))''',
  "const sys = require('sys')\n", "const util = require('node:util')\n", "Use node:util.", sev="major", kind="removal")
N("CREATEREQUIRE-001", "Module.createRequireFromPath() was removed", "DEP0130: Module.createRequireFromPath()", mcall("Module|module", "createRequireFromPath"),
  "const r = Module.createRequireFromPath(file)\n", "const r = Module.createRequire(file)\n", "Use module.createRequire().", sev="major", kind="removal")
N("LISTENERCOUNT-001", "EventEmitter.listenerCount() static is deprecated", "DEP0033: EventEmitter.listenerCount()", mcall("EventEmitter", "listenerCount"),
  "const n = EventEmitter.listenerCount(em, 'data')\n", "const n = em.listenerCount('data')\n", "Use emitter.listenerCount(eventName).")
N("DEFAULT-ENCODING-001", "crypto.DEFAULT_ENCODING was removed", "DEP0091: crypto.DEFAULT_ENCODING",
  r'''((member_expression object: (identifier) @o property: (property_identifier) @p) @match (#eq? @o "crypto") (#eq? @p "DEFAULT_ENCODING"))''',
  "crypto.DEFAULT_ENCODING = 'hex'\n", "const h = hash.digest('hex')\n", "crypto.DEFAULT_ENCODING is removed; pass encodings explicitly.", sev="major", kind="removal")
N("PBKDF2-DIGEST-001", "crypto.pbkdf2Sync without digest", "DEP0009: crypto.pbkdf2 without digest",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (_) . (_) . (_) . (_) .)) @match (#eq? @p "pbkdf2Sync"))''',
  "const k = crypto.pbkdf2Sync(pw, salt, 100000, 64)\n", "const k = crypto.pbkdf2Sync(pw, salt, 600000, 64, 'sha512')\n",
  "pbkdf2 without an explicit digest is no longer supported; pass a digest such as 'sha512'.", sev="major", kind="removal", cat="security")
N("CHILD-EXEC-INJECTION-001", "Shell command built from interpolated input (child_process.exec)", "Never pass unsanitized user input to this function.",
  r'''((call_expression function: [(identifier) @f (member_expression property: (property_identifier) @f)] arguments: (arguments . [(template_string (template_substitution)) (binary_expression)])) @match (#match? @f "^(exec|execSync)$"))''',
  "exec(`git log ${branch}`, cb)\n", "execFile('git', ['log', branch], cb)\n",
  "exec() runs the string through a shell; interpolated input enables command injection. Use execFile/spawn with an argument array.",
  sev="critical", kind="security", cat="security", url="https://nodejs.org/api/child_process.html", mode="ai-confirm",
  ai="Can any interpolated value be influenced by a user or external input?")

# ---------------------------------------------------------------- MDN web platform security / deprecations
MDN = "https://developer.mozilla.org/en-US/docs/"


def W(id, title, path, quote, query, bad, good, msg, sev="minor", kind="deprecation", cat="deprecation", **kw):
    R.append(rule("JS-WEB-" + id, title, language="javascript", kind=kind, category=cat, severity=sev, applies=ES, message=msg,
                  url=MDN + path, doc="MDN " + path.split("/")[-1], doc_version="MDN (living standard)", quote=quote,
                  bad=bad, good=good, query=query, tags=["web-platform"], **kw))


W("POSTMESSAGE-STAR-001", "postMessage with targetOrigin '*'", "Web/API/Window/postMessage",
  "Always provide a specific targetOrigin, not *, if you know where the other window's document should be located.",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments (_) . (string) @s)) @match (#eq? @p "postMessage") (#match? @s "^['\"]\\*['\"]$"))''',
  "frame.contentWindow.postMessage(token, '*')\n", "frame.contentWindow.postMessage(token, 'https://app.example.com')\n",
  "'*' sends the message to whatever origin the window currently has, leaking data to a navigated/hostile frame.", sev="major", kind="security", cat="security")
W("MESSAGE-ORIGIN-001", "message event handler does not check event.origin", "Web/API/Window/postMessage",
  "Always verify the sender's identity using the origin and possibly source properties.",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments (string (string_fragment) @e) [(arrow_function body: (_) @b) (function_expression body: (_) @b)])) @match (#eq? @p "addEventListener") (#eq? @e "message") (#not-match? @b "origin"))''',
  "window.addEventListener('message', (e) => { apply(e.data) })\n", "window.addEventListener('message', (e) => {\n  if (e.origin !== TRUSTED) return\n  apply(e.data)\n})\n",
  "Cross-window messages must be authenticated by origin before their data is used.", sev="major", kind="security", cat="security")
W("DOCUMENT-WRITE-001", "document.write() is strongly discouraged", "Web/API/Document/write",
  "Use of the document.write() method is strongly discouraged.",
  mcall("document", "write|writeln"), "document.write('<p>' + msg + '</p>')\n", "el.textContent = msg\n",
  "document.write is an XSS sink, blocks parsing and wipes the document after load.", sev="major", kind="security", cat="security")
W("OUTERHTML-001", "Assigning untrusted strings to outerHTML / insertAdjacentHTML", "Web/API/Element/insertAdjacentHTML",
  "APIs like this are known as injection sinks",
  r'''((assignment_expression left: (member_expression property: (property_identifier) @p) right: (_) @v) @match (#eq? @p "outerHTML") (#not-match? @v "^['\"`][^$]*['\"`]$"))
((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments (_) . (_) @v)) @match (#eq? @p "insertAdjacentHTML") (#not-match? @v "^['\"`][^$]*['\"`]$"))''',
  "el.insertAdjacentHTML('beforeend', comment.body)\n", "el.insertAdjacentText('beforeend', comment.body)\n",
  "HTML parsing of non-constant strings is an XSS sink; use text APIs, DOM construction or a sanitizer/Trusted Types.", sev="major", kind="security", cat="security",
  mode="ai-confirm", ai="Can the inserted HTML contain user-controlled data that is not sanitized?")
W("MATH-RANDOM-SECURITY-001", "Math.random() used for security-sensitive values", "Web/JavaScript/Reference/Global_Objects/Math/random",
  "Math.random() does not provide cryptographically secure random numbers.",
  r'''((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p)) @match (#eq? @o "Math") (#eq? @p "random"))''',
  "const token = Math.random().toString(36).slice(2)\n", "const token = crypto.randomUUID()\n",
  "Math.random() is predictable; use crypto.getRandomValues()/crypto.randomUUID() for tokens, ids and secrets.", sev="major", kind="security", cat="security",
  mode="ai-confirm", ai="Is the random value used for anything security-relevant (token, id, password, nonce, key)?")
W("SYNC-XHR-001", "Synchronous XMLHttpRequest", "Web/API/XMLHttpRequest/open",
  "Synchronous requests on the main thread can be easily disruptive to the user experience and should be avoided",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments (_) (_) (false))) @match (#eq? @p "open"))''',
  "xhr.open('GET', url, false)\n", "const res = await fetch(url)\n", "Synchronous XHR blocks the main thread and is deprecated on the main thread; use fetch().", sev="major", cat="performance")
W("UNLOAD-001", "unload event listeners are deprecated", "Web/API/Window/unload_event",
  "Developers should avoid using this event.",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (string (string_fragment) @e))) @match (#eq? @p "addEventListener") (#eq? @e "unload"))''',
  "window.addEventListener('unload', save)\n", "document.addEventListener('visibilitychange', save)\n",
  "unload is unreliable and disables the back/forward cache; use visibilitychange or pagehide.", cat="performance")
W("EXECCOMMAND-001", "document.execCommand() is deprecated", "Web/API/Document/execCommand", "Deprecated",
  mcall("document", "execCommand"), "document.execCommand('copy')\n", "await navigator.clipboard.writeText(text)\n",
  "execCommand is deprecated; use the Clipboard API / modern editing APIs.")
W("KEYCODE-001", "KeyboardEvent.keyCode / which / charCode are deprecated", "Web/API/KeyboardEvent/keyCode", "Deprecated",
  r'''((member_expression object: (identifier) @o property: (property_identifier) @p) @match (#match? @o "^(e|ev|evt|event)$") (#match? @p "^(keyCode|which|charCode)$"))''',
  "if (e.keyCode === 13) submit()\n", "if (e.key === 'Enter') submit()\n", "Use KeyboardEvent.key / code.")
W("MUTATION-EVENTS-001", "Mutation events (DOMNodeInserted, DOMSubtreeModified, ...) are deprecated", "Web/API/MutationEvent", "Deprecated",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (string (string_fragment) @e))) @match (#eq? @p "addEventListener") (#match? @e "^DOM(SubtreeModified|NodeInserted|NodeRemoved|NodeInsertedIntoDocument|NodeRemovedFromDocument|AttrModified|CharacterDataModified)$"))''',
  "el.addEventListener('DOMNodeInserted', onAdd)\n", "new MutationObserver(onAdd).observe(el, { childList: true })\n",
  "Mutation events are deprecated and removed from Chromium; use MutationObserver.", sev="major", cat="performance")
W("INITEVENT-001", "Event.initEvent() / document.createEvent are deprecated", "Web/API/Event/initEvent", "Deprecated",
  r'''((call_expression function: (member_expression property: (property_identifier) @p)) @match (#match? @p "^(initEvent|initCustomEvent|initMouseEvent|initKeyboardEvent)$"))''',
  "const ev = document.createEvent('Event')\nev.initEvent('ready', true, true)\n", "const ev = new Event('ready', { bubbles: true, cancelable: true })\n",
  "Use event constructors (new Event / new CustomEvent).")
W("PERFORMANCE-TIMING-001", "performance.timing is deprecated", "Web/API/Performance/timing", "Deprecated",
  r'''((member_expression object: (identifier) @o property: (property_identifier) @p) @match (#eq? @o "performance") (#eq? @p "timing"))''',
  "const t = performance.timing.loadEventEnd\n", "const [nav] = performance.getEntriesByType('navigation')\n", "Use PerformanceNavigationTiming.")
W("DOCUMENT-DOMAIN-001", "Setting document.domain is deprecated", "Web/API/Document/domain", "Deprecated",
  r'''(assignment_expression left: (member_expression object: (identifier) @o property: (property_identifier) @p) @match (#eq? @o "document") (#eq? @p "domain"))''',
  "document.domain = 'example.com'\n", "parent.postMessage(msg, 'https://example.com')\n",
  "Setting document.domain relaxes the same-origin policy and is being removed; use postMessage.", sev="major", kind="security", cat="security")
W("REGEXP-LEGACY-001", "RegExp.$1-$9 legacy static properties are deprecated", "Web/JavaScript/Reference/Global_Objects/RegExp/n", "Deprecated",
  r'''((member_expression object: (identifier) @o property: (property_identifier) @p) @match (#eq? @o "RegExp") (#match? @p "^\\$[1-9]$|^(lastMatch|leftContext|rightContext|input|lastParen)$"))''',
  "re.test(s)\nconst first = RegExp.$1\n", "const m = re.exec(s)\nconst first = m?.[1]\n", "Use the match result instead of global RegExp state.")
W("TOGMTSTRING-001", "Date.prototype.toGMTString() is deprecated", "Web/JavaScript/Reference/Global_Objects/Date/toUTCString", "toGMTString()",
  r'''((call_expression function: (member_expression property: (property_identifier) @p)) @match (#eq? @p "toGMTString"))''',
  "const s = d.toGMTString()\n", "const s = d.toUTCString()\n", "Use toUTCString().")
W("DEFINEGETTER-001", "__defineGetter__/__defineSetter__/__lookupGetter__ are deprecated", "Web/JavaScript/Reference/Global_Objects/Object/__defineGetter__", "Deprecated",
  r'''((call_expression function: (member_expression property: (property_identifier) @p)) @match (#match? @p "^__(define|lookup)(Getter|Setter)__$"))''',
  "obj.__defineGetter__('x', () => 1)\n", "Object.defineProperty(obj, 'x', { get: () => 1 })\n", "Use Object.defineProperty / Object.getOwnPropertyDescriptor.")
W("SORT-DEFAULT-001", "Array.prototype.sort() without a comparator sorts numbers as strings", "Web/JavaScript/Reference/Global_Objects/Array/sort",
  "The default sort order is ascending, built upon converting the elements into strings",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments) @a) @match (#match? @p "^(sort|toSorted)$") (#eq? @a "()"))''',
  "const top = scores.sort()\n", "const top = scores.sort((a, b) => a - b)\n",
  "Without a compare function, [10, 9, 1].sort() yields [1, 10, 9].", sev="minor", kind="anti-pattern", cat="correctness",
  mode="ai-confirm", ai="Does the array contain numbers (or values whose string order differs from the intended order)?")
W("FETCH-OK-001", "fetch() response used without checking response.ok", "Web/API/Fetch_API/Using_Fetch",
  "The fetch() function will reject the promise on some errors, but not if the server responds with an error status like 404",
  r'''((statement_block) @match (#match? @match "^\\{[^{}]*\\bfetch\\(") (#match? @match "\\.(json|text|blob|arrayBuffer)\\(\\)") (#not-match? @match "\\.ok\\b|\\.status\\b"))''',
  "async function load(u) {\n  const res = await fetch(u)\n  return res.json()\n}\n", "async function load(u) {\n  const res = await fetch(u)\n  if (!res.ok) throw new Error(`HTTP ${res.status}`)\n  return res.json()\n}\n",
  "fetch() resolves for HTTP 4xx/5xx; check response.ok/status before reading the body.", kind="anti-pattern", cat="error-handling",
  mode="ai-confirm", ai="Is the HTTP status of this fetch response never checked before use?")
W("DATE-NOW-001", "new Date().getTime() instead of Date.now()", "Web/JavaScript/Reference/Global_Objects/Date/now",
  "returns the number of milliseconds elapsed since the epoch",
  r'''((call_expression function: (member_expression object: (new_expression constructor: (identifier) @c arguments: (arguments) @a) property: (property_identifier) @p)) @match (#eq? @c "Date") (#eq? @a "()") (#eq? @p "getTime"))''',
  "const t = new Date().getTime()\n", "const t = Date.now()\n", "Date.now() avoids allocating a Date.", sev="info", kind="modernization", cat="performance")
W("PASSIVE-LISTENER-001", "Scroll-blocking touch/wheel listeners without { passive: true }", "Web/API/EventTarget/addEventListener",
  "the browser is in general unable to start the default action",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (string (string_fragment) @e) . (_) .)) @match (#eq? @p "addEventListener") (#match? @e "^(touchstart|touchmove|wheel|mousewheel)$"))''',
  "el.addEventListener('touchmove', onMove)\n", "el.addEventListener('touchmove', onMove, { passive: true })\n",
  "Non-passive touch/wheel listeners force the browser to wait before scrolling.", sev="info", kind="best-practice", cat="performance",
  mode="ai-confirm", ai="Does the handler NOT call preventDefault() (so it can be passive)?")

# ---------------------------------------------------------------- Snyk/Semgrep checklist gaps (own detection/wording)
from specs._common import autoquote as _aq
_CORS = "https://expressjs.com/en/resources/middleware/cors.html"
_H5 = "https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html"
R.append(rule("JS-SEC-CORS-REFLECT-ANY-001", "cors() reflects any origin together with credentials", language="javascript", kind="security", category="security",
              severity="critical", applies={"ecmascript": ">=2015"}, url=_CORS, doc="Express cors middleware", doc_version="cors 2.8",
              quote=_aq(_CORS, "Configures the Access-Control-Allow-Origin"),
              query=r'''((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @o value: (true)) (pair key: (property_identifier) @c value: (true))) @match)) (#eq? @f "cors") (#eq? @o "origin") (#eq? @c "credentials"))''',
              bad="app.use(cors({ origin: true, credentials: true }))\n", good="app.use(cors({ origin: ['https://app.example.com'], credentials: true }))\n",
              message="origin: true echoes whatever Origin the browser sends, and credentials: true lets that site read authenticated responses. Use an allow-list of origins.",
              cwe=["CWE-942"], xref=["sonar:javascript:S5122"]))
R.append(rule("JS-SEC-CORS-WILDCARD-HEADER-001", "Access-Control-Allow-Origin: * set by hand", language="javascript", kind="security", category="security",
              severity="major", applies={"ecmascript": ">=2015"}, url=_H5, doc="OWASP HTML5 Security Cheat Sheet", doc_version="current",
              quote=_aq(_H5, "Allow only selected, trusted domains"),
              query=r'''((call_expression function: (member_expression property: (property_identifier) @m) arguments: (arguments . (string (string_fragment) @k) . (string (string_fragment) @v) .)) @match (#match? @m "^(setHeader|header|set|append)$") (#match? @k "(?i)^access-control-allow-origin$") (#eq? @v "*"))''',
              bad="res.setHeader('Access-Control-Allow-Origin', '*')\n", good="res.setHeader('Access-Control-Allow-Origin', 'https://app.example.com')\n",
              message="Any origin may read this response from a browser. Use an allow-list unless the endpoint is deliberately public and carries nothing user-specific.",
              mode="ai-confirm", ai="Does this endpoint serve user-specific or non-public data (so a wildcard origin is a real exposure)?",
              cwe=["CWE-942"], xref=["sonar:javascript:S5122"]))

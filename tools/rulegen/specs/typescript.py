"""TypeScript pack: typescript-eslint rules that are decidable syntactically (typescript-eslint.io),
TSConfig reference options and TypeScript 5.0/6.0/7.0 deprecations/removals."""
from specs._lint import lint
from rulegen import rule

R = RULES = []
TS = {"typescript": ">=3.0"}


def T(name, sev, cat, query, bad, good, msg, *, id=None, **kw):
    kw.setdefault("applies", TS)
    R.append(lint("typescript-eslint", name, id or "TS-" + name.upper(), language="typescript", severity=sev, category=cat,
                  query=query, bad=bad, good=good, message=msg, **kw))


T("array-type", "info", "style",
  r'''((generic_type name: (type_identifier) @n type_arguments: (type_arguments . [(predefined_type) (type_identifier)] .)) @match (#eq? @n "Array"))''',
  "let xs: Array<string> = []\n", "let xs: string[] = []\n", "Use T[] for simple array types (consistent array-type style).")
T("ban-tslint-comment", "info", "maintainability", r'''((comment) @match (#match? @match "^//\\s*tslint:"))''',
  "// tslint:disable-next-line\nlet a = 1\n", "let a = 1\n", "TSLint is deprecated; remove tslint directives.")
# Fixture triage: only a real pragma counts (a `//` or `///` line comment; @ts-nocheck only
# before the first statement, where TypeScript honours it); @ts-check is allowed by default.
T("ban-ts-comment", "minor", "correctness", r'''((comment) @match (#match? @match "^///?\\s*@ts-nocheck\\b|^///?\\s*@ts-expect-error\\s*$"))''',
  "// @ts-nocheck\nexport const a = 1\n", "export const a: number = 1\n",
  "@ts-nocheck disables type checking for the whole file; @ts-expect-error should carry a description.", id="TS-BAN-TS-COMMENT-NOCHECK",
  filters=[r"file.has_re:\A(?:\s*(?://[^\n]*|/\*(?s:.*?)\*/))*?\s*///?\s*@ts-nocheck|(?m)^\s*///?\s*@ts-expect-error\s*$"],
  fp=[{"note": "mentions the pragma in prose", "code": "// docs: never add @ts-nocheck to these files\nexport const a = 1\n"},
      {"note": "block comment is not a pragma", "code": "/* @ts-nocheck */\nexport const a = 1\n"},
      {"note": "after the first statement it has no effect", "code": "export const a = 1\n// @ts-nocheck\nexport const b = 2\n"},
      {"note": "@ts-check is fine", "code": "// @ts-check\nexport const a = 1\n"}])
T("consistent-generic-constructors", "info", "style",
  r'''((variable_declarator type: (type_annotation (generic_type name: (type_identifier) @t)) value: (new_expression constructor: (identifier) @c !type_arguments) @match) (#eq? @t @c) (#not-match? @c "^(Float|Int|Uint|BigInt|BigUint)(8|16|32|64)(Clamped)?Array$"))''',
  "const m: Map<string, number> = new Map()\n", "const m = new Map<string, number>()\n", "Put generic type arguments on the constructor call.",
  fp=[{"note": "annotation names a different (interface) type", "code": "const store: Cache<string> = new LruCache()\n"},
      {"note": "typed array buffer parameter", "code": "const buf: Uint8Array<ArrayBuffer> = new Uint8Array()\n"}])
T("consistent-indexed-object-style", "info", "style",
  r'''(type_alias_declaration value: (object_type . (index_signature) .) @match)''',
  "type Dict = { [key: string]: number }\n", "type Dict = Record<string, number>\n", "Use Record<K, V> for pure index-signature types.")
T("consistent-type-assertions", "minor", "style", r'''(type_assertion) @match''',
  "const el = <HTMLInputElement>document.getElementById('x')\n", "const el = document.getElementById('x') as HTMLInputElement\n",
  "Angle-bracket assertions are ambiguous with JSX/generics; use 'as'.")
T("consistent-type-definitions", "info", "style", r'''(type_alias_declaration value: (object_type) @match)''',
  "type User = { id: string }\n", "interface User { id: string }\n", "Prefer interface for object type definitions (extendable, better error messages).")
T("default-param-last", "minor", "correctness",
  r'''(formal_parameters [(required_parameter value: (_)) (optional_parameter)] @match . (required_parameter !value pattern: [(identifier) (object_pattern) (array_pattern)]))''',
  "function f(a = 1, b: number) {}\n", "function f(b: number, a = 1) {}\n", "A defaulted/optional parameter before a required one cannot be omitted.",
  fp=[{"note": "a rest parameter is not required", "code": "function f(delay = 0, ...args: unknown[]) {}\ntype Cb = (err?: unknown, ...rest: unknown[]) => void\n"}])
T("explicit-function-return-type", "info", "style",
  r'''((export_statement (function_declaration !return_type) @match))''',
  "export function total(items: Item[]) {\n  return items.length\n}\n", "export function total(items: Item[]): number {\n  return items.length\n}\n",
  "Exported functions should declare their return type (stable API, faster type-checking).")
T("method-signature-style", "info", "style", r'''(interface_body (method_signature) @match)''',
  "interface Api {\n  get(id: string): Item\n}\n", "interface Api {\n  get: (id: string) => Item\n}\n",
  "Property-style signatures are checked contravariantly under strictFunctionTypes; method shorthand is bivariant.",
  filters=[r"node.lacks_re:^\s*(get|set)\s+[\w'\x22\[]"])  # accessor signatures have no property form
T("max-params", "info", "maintainability", r'''(formal_parameters (_) (_) (_) (_)) @match''',
  "function f(a: number, b: number, c: number, d: number) {}\n", "function f(o: { a: number; b: number; c: number; d: number }) {}\n",
  "More than 3 parameters: consider an options object.")
T("no-array-delete", "major", "correctness",
  r'''(unary_expression operator: "delete" argument: (subscript_expression object: (_) @o index: [(number) (identifier)])) @match''',
  "const items: string[] = load()\ndelete items[i]\n", "const items: string[] = load()\nitems.splice(i, 1)\n", "delete on an array leaves a hole instead of removing the element.",
  # the rule is type-aware: only when the operand is known to be an array (most deletes are on records)
  filters=[r"type.is:o:array|(Readonly)?Array"],
  fp=[{"note": "record", "code": "const clients: Record<string, C> = {}\ndelete clients[id]\n"}])
T("no-confusing-non-null-assertion", "minor", "correctness",
  r'''(binary_expression left: (non_null_expression) operator: ["==" "==="]) @match''',
  "if (a! == b) {}\n", "if (a !== b) {}\n", "a! == b looks like a !== b.")
T("no-duplicate-enum-values", "major", "correctness",
  r'''((enum_body (enum_assignment value: (_) @a) (enum_assignment value: (_) @b) @match) (#eq? @a @b))''',
  "enum Color { Red = 'r', Blue = 'r' }\n", "enum Color { Red = 'r', Blue = 'b' }\n", "Two enum members share a value, so they are indistinguishable.")
T("no-duplicate-type-constituents", "minor", "correctness",
  r'''((union_type . (_) @a . (_) @b .) @match (#eq? @a @b))
((union_type (union_type . (_) @a) . (_) @b .) @match (#eq? @a @b))
((union_type (union_type (_) @a .) . (_) @b .) @match (#eq? @a @b))
((intersection_type . (_) @a . (_) @b .) @match (#eq? @a @b))''',
  "type T = string | number | string\n", "type T = string | number\n", "Duplicate union/intersection constituent.")
T("no-dynamic-delete", "minor", "correctness",
  r'''(unary_expression operator: "delete" argument: (subscript_expression index: [(identifier) (member_expression) (call_expression) (template_string)])) @match''',
  "delete cache[key]\n", "cache.delete(key)\n", "Deleting computed keys suggests a Map/Set should be used instead.")
T("no-empty-object-type", "minor", "correctness",
  r'''((interface_declaration body: (interface_body) @b) @match (#match? @b "^\\{\\s*\\}$"))
((type_annotation (object_type) @match) (#match? @match "^\\{\\s*\\}$"))''',
  "interface Props {}\n", "type Props = Record<string, never>\n", "The {} type means 'any non-nullish value', not 'empty object'.")
T("no-extra-non-null-assertion", "minor", "correctness", r'''(non_null_expression (non_null_expression)) @match''',
  "const n = value!!.length\n", "const n = value!.length\n", "Repeated non-null assertion.")
T("no-extraneous-class", "info", "style",
  r'''((class_declaration body: (class_body) @b) @match (#match? @b "^\\{\\s*\\}$"))''',
  "class Empty {}\n", "const helpers = {}\n", "An empty class is not useful; use a plain object or module.")
T("no-floating-promises", "major", "async",
  r'''((expression_statement (call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (_) .)) @match) (#eq? @p "then"))
((expression_statement (call_expression function: (identifier) @f) @match) (#match? @f "^(fetch)$"))''',
  "save(user).then(() => notify())\n", "await save(user).then(() => notify())\n",
  "The promise is neither awaited, returned nor given a rejection handler; errors become unhandled rejections.", mode="ai-confirm",
  ai="Is this promise result intentionally fire-and-forget with errors handled elsewhere? (answer reject if so)")
T("no-import-type-side-effects", "info", "correctness",
  r'''((import_statement (import_clause (named_imports) @n)) @match (#match? @n "^\\{\\s*type\\s+\\w+(\\s*,\\s*type\\s+\\w+)*\\s*,?\\s*\\}$") (#not-match? @match "^import\\s+type") (#not-match? @match "^import\\s+[\\w$]+\\s*,"))''',
  "import { type A, type B } from './types'\n", "import type { A, B } from './types'\n",
  "With verbatimModuleSyntax an import with only inline type specifiers is kept as a side-effect import; use import type.",
  fp=[{"note": "a default value import keeps the statement needed", "code": "import NextAuth, { type DefaultSession } from 'next-auth'\n"}])
T("no-inferrable-types", "info", "style",
  r'''((variable_declarator type: (type_annotation (predefined_type) @t) value: [(number) (string) (true) (false)]) @match (#match? @t "^(number|string|boolean)$"))''',
  "const n: number = 5\n", "const n = 5\n", "The type is trivially inferred from the literal.")
T("no-invalid-void-type", "minor", "correctness",
  # match the whole (left-nested) union; void may sit up to 4 levels down
  r'''((union_type (predefined_type) @v) @match (#eq? @v "void"))
((union_type (union_type (predefined_type) @v1)) @match (#eq? @v1 "void"))
((union_type (union_type (union_type (predefined_type) @v2))) @match (#eq? @v2 "void"))
((union_type (union_type (union_type (union_type (predefined_type) @v3)))) @match (#eq? @v3 "void"))''',
  "type R = string | void\n", "type R = string | undefined\n", "void is only meaningful as a return type or generic argument; use undefined in unions.",
  # the rule accepts unions whose members are all void, never or generics with a void argument (Promise<void> | void)
  filters=["parentkind.lacks_re:union_type:.", r"node.lacks_re:^\s*\|?\s*(void|never|[\w.$]+\s*<[^|<>]*\bvoid\b[^|<>]*>)(\s*\|\s*(void|never|[\w.$]+\s*<[^|<>]*\bvoid\b[^|<>]*>))*\s*$"],
  fp=[{"note": "void | Promise<void> is allowed", "code": "type H = (ctx: C) => Promise<void> | void\ntype G = () => void | never\n"}])
T("no-misused-new", "major", "correctness",
  r'''((interface_body (method_signature name: (property_identifier) @n) @match) (#eq? @n "constructor"))''',
  "interface Point {\n  constructor(): Point\n}\n", "interface PointCtor {\n  new (): Point\n}\n", "Interfaces cannot declare constructors; use a construct signature (new ()).")
T("no-mixed-enums", "minor", "correctness",
  r'''(enum_body (enum_assignment value: (number)) (enum_assignment value: (string))) @match
(enum_body (enum_assignment value: (string)) (enum_assignment value: (number))) @match''',
  "enum E { A = 0, B = 'b' }\n", "enum E { A = 'a', B = 'b' }\n", "Mixing number and string members makes enum comparisons error-prone.")
T("no-non-null-asserted-nullish-coalescing", "minor", "null-handling",
  r'''(binary_expression left: (non_null_expression) operator: "??") @match''',
  "const v = maybe! ?? fallback\n", "const v = maybe ?? fallback\n", "Asserting non-null and then defaulting with ?? contradicts itself.")
T("no-non-null-asserted-optional-chain", "major", "null-handling",
  r'''(non_null_expression (member_expression (optional_chain))) @match''',
  "const n = user?.name!\n", "const n = user?.name ?? ''\n", "Optional chain followed by ! hides the undefined it was meant to handle.")
T("no-require-imports", "minor", "modules",
  r'''((call_expression function: (identifier) @f arguments: (arguments . (string))) @match (#eq? @f "require"))''',
  "const fs = require('fs')\n", "import fs from 'node:fs'\n", "Use ES import syntax (typed, tree-shakeable).")
T("no-this-alias", "minor", "style", r'''(variable_declarator name: (identifier) value: (this)) @match''',
  "const self = this\n", "const fn = () => this.run()\n", "Aliasing this is unnecessary with arrow functions.")
T("no-unnecessary-boolean-literal-compare", "info", "style",
  r'''(binary_expression operator: ["===" "!=="] right: [(true) (false)]) @match''',
  "if (isReady === true) {}\n", "if (isReady) {}\n", "Comparing a boolean to a boolean literal is redundant.", mode="ai-confirm",
  ai="Is the left operand typed exactly boolean (not boolean | undefined / null)?")
T("no-unnecessary-parameter-property-assignment", "minor", "correctness",
  r'''((method_definition name: (property_identifier) @c parameters: (formal_parameters (required_parameter (accessibility_modifier) pattern: (identifier) @p)) body: (statement_block (expression_statement (assignment_expression left: (member_expression object: (this) property: (property_identifier) @q) right: (identifier) @r) @match))) (#eq? @c "constructor") (#eq? @p @q) (#eq? @q @r))''',
  "class A {\n  constructor(private name: string) {\n    this.name = name\n  }\n}\n", "class A {\n  constructor(private name: string) {}\n}\n",
  "Parameter properties are assigned automatically.")
# Fixture triage: tagged templates see the parts separately; whitespace-only literals keep
# trailing spaces visible; a comment inside ${} is deliberate documentation.
T("no-unnecessary-template-expression", "info", "style", r'''(template_substitution [(string) (number)]) @match''',
  "const s = `${'hello'} world`\n", "const s = 'hello world'\n", "Interpolating a literal into a template is redundant.",
  filters=[r"node.lacks_re:/[*/]|^\$\{\s*['\"]\s*['\"]\s*\}$", "ancestor.lacks_re:call_expression:^[\\w$.]+\\s*`"],
  fp=[{"note": "tagged template", "code": "const q = sql`${'users'}`\n"},
      {"note": "keeps trailing whitespace visible", "code": "const s = `indent:${'  '}`\n"},
      {"note": "commented literal", "code": "const s = `${/* default */ 'en'}-US`\n"}])
T("no-unnecessary-type-constraint", "info", "style", r'''((type_parameter (constraint [(predefined_type) @t])) @match (#match? @t "^(any|unknown)$"))''',
  "function f<T extends unknown>(x: T) {}\n", "function f<T>(x: T) {}\n", "Every type extends unknown/any; the constraint is redundant.")
T("no-unsafe-declaration-merging", "major", "correctness",
  r'''((program (interface_declaration name: (type_identifier) @a) (class_declaration name: (type_identifier) @b) @match) (#eq? @a @b))
((program (class_declaration name: (type_identifier) @a) (interface_declaration name: (type_identifier) @b) @match) (#eq? @a @b))''',
  "interface Foo { id: string }\nclass Foo {}\n", "interface FooShape { id: string }\nclass Foo implements FooShape { id = '' }\n",
  "Merging an interface into a class declares members the compiler will not check are initialised.")
T("no-unsafe-function-type", "minor", "correctness", r'''((type_annotation (type_identifier) @match) (#eq? @match "Function"))''',
  "let cb: Function\n", "let cb: () => void\n", "Function accepts any callable and returns any; declare the signature.")
T("no-unsafe-type-assertion", "minor", "correctness",
  r'''((as_expression (as_expression (_) [(predefined_type) @u])) @match (#match? @u "^(unknown|any)$"))''',
  "const n = value as unknown as number\n", "const n = Number(value)\n", "A double assertion through unknown/any bypasses type checking.")
T("prefer-as-const", "info", "style",
  r'''((variable_declarator type: (type_annotation (literal_type (string) @a)) value: (string) @b) @match (#eq? @a @b))
((as_expression (string) @a (literal_type (string) @b)) @match (#eq? @a @b))''',
  "let kind: 'user' = 'user'\n", "let kind = 'user' as const\n", "Use as const instead of repeating the literal type.")
T("prefer-enum-initializers", "info", "style", r'''(enum_body (property_identifier) @match)''',
  "enum Status { Open, Closed }\n", "enum Status { Open = 'open', Closed = 'closed' }\n",
  "Implicit enum values shift when members are reordered/inserted (breaking persisted values).")
T("prefer-find", "minor", "performance",
  r'''((subscript_expression object: (call_expression function: (member_expression property: (property_identifier) @p)) index: (number) @n) @match (#eq? @p "filter") (#eq? @n "0"))''',
  "const first = users.filter((u) => u.admin)[0]\n", "const first = users.find((u) => u.admin)\n", "find() stops at the first match instead of filtering the whole array.")
T("prefer-for-of", "info", "style",
  r'''((for_statement condition: (binary_expression right: (member_expression property: (property_identifier) @len)) body: (_) @b) @match (#eq? @len "length") (#match? @b "\\[i\\]"))''',
  "for (let i = 0; i < xs.length; i++) {\n  use(xs[i])\n}\n", "for (const x of xs) {\n  use(x)\n}\n", "Use for-of when the index is only used to read the element.",
  mode="ai-confirm", ai="Is the index used only to read the current element (not for writes, neighbours or output)?")
T("prefer-function-type", "info", "style", r'''(interface_declaration body: (interface_body . (call_signature) .)) @match''',
  "interface Fn {\n  (x: number): string\n}\n", "type Fn = (x: number) => string\n", "An interface with only a call signature is a function type.")
T("prefer-includes", "info", "style",
  r'''((binary_expression left: (call_expression function: (member_expression property: (property_identifier) @p)) right: (unary_expression operator: "-" argument: (number) @n)) @match (#eq? @p "indexOf") (#eq? @n "1"))''',
  "if (tags.indexOf('x') !== -1) {}\n", "if (tags.includes('x')) {}\n", "Use includes() for membership tests.", applies={"ecmascript": ">=2016"})
T("prefer-literal-enum-member", "minor", "correctness",
  r'''(enum_assignment value: [(identifier) (call_expression) (member_expression) (template_string)] @match)''',
  "const base = 1\nenum E { A = base }\n", "enum E { A = 1 }\n", "Enum members should be literal so they can be used as types and are not evaluated at runtime.")
T("prefer-reduce-type-parameter", "info", "style",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments (_) (as_expression) @match)) (#eq? @p "reduce"))''',
  "const ids = xs.reduce((acc, x) => [...acc, x.id], [] as string[])\n", "const ids = xs.reduce<string[]>((acc, x) => [...acc, x.id], [])\n",
  "Use the reduce type parameter instead of asserting the initial value.")
T("prefer-regexp-exec", "info", "performance",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (regex) @r .)) @match (#eq? @p "match") (#not-match? @r "/[a-z]*g[a-z]*$"))''',
  "const m = line.match(/(\\d+)/)\n", "const m = /(\\d+)/.exec(line)\n", "RegExp#exec is equivalent and faster for non-global regexes.",
  # chai/jest-style assertions (expect(x).to.match(/re/)) are not String#match
  filters=[r"node.lacks_re:^\s*expect\s*\(|\.(to|be|been|is|that|which|and|not|deep|also|should)\s*\.\s*match\s*\("],
  fp=[{"note": "chai assertion", "code": "expect(res.text).to.match(/engine\\.io/)\nres.text.should.match(/ok/)\n"}])
T("prefer-string-starts-ends-with", "info", "style",
  r'''((binary_expression left: (call_expression function: (member_expression property: (property_identifier) @p)) operator: ["===" "=="] right: (number) @n) @match (#eq? @p "indexOf") (#eq? @n "0"))
((binary_expression left: (subscript_expression index: (number) @n) operator: ["===" "=="] right: (string)) @match (#eq? @n "0"))''',
  "if (path.indexOf('/api') === 0) {}\n", "if (path.startsWith('/api')) {}\n", "Use startsWith/endsWith.", applies={"ecmascript": ">=2015"})
T("triple-slash-reference", "minor", "modules", r'''((comment) @match (#match? @match "^///\\s*<reference\\s+path="))''',
  "/// <reference path=\"./globals.d.ts\" />\nexport {}\n", "import './globals'\nexport {}\n", "Use import instead of triple-slash path references.")
T("use-unknown-in-catch-callback-variable", "minor", "error-handling",
  r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (arrow_function parameters: (formal_parameters . (required_parameter pattern: (identifier) !type))))) @match (#eq? @p "catch"))
((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (arrow_function parameters: (formal_parameters . (required_parameter type: (type_annotation (predefined_type) @t)))))) @match (#eq? @p "catch") (#eq? @t "any"))''',
  "load().catch((err) => log(err.message))\n", "load().catch((err: unknown) => log(String(err)))\n",
  "Rejection reasons can be anything; type the callback parameter as unknown and narrow it.")
T("no-redundant-type-constituents", "minor", "correctness", r'''((union_type (predefined_type) @t) @match (#match? @t "^(any|unknown|never)$"))''',
  "type T = string | unknown\n", "type T = unknown\n", "any/unknown absorb, and never vanishes from, any union.")
T("prefer-nullish-coalescing", "minor", "null-handling",
  r'''(assignment_expression left: (_) @a right: (binary_expression left: (_) @b operator: "||")) @match''',
  "opts.timeout = opts.timeout || 1000\n", "opts.timeout ??= 1000\n", "|| also replaces 0/''/false; use ?? / ??= when only null/undefined should be defaulted.",
  mode="ai-confirm", ai="Can the left value legitimately be 0, '', or false (so || would wrongly replace it)?", applies={"ecmascript": ">=2020"})
T("only-throw-error", "major", "error-handling", r'''(throw_statement [(string) (template_string) (number) (object)] @match)''',
  "throw `failed: ${id}`\n", "throw new Error(`failed: ${id}`)\n", "Throw Error objects so stack traces and instanceof checks work.", id="TS-ONLY-THROW-ERROR")

# ---------------------------------------------------------------- TypeScript language deprecations (comment directives)
TS6 = "https://www.typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html"
R.append(rule("TS-TS6-NO-DEFAULT-LIB-001", "/// <reference no-default-lib> is no longer supported (TypeScript 6.0)", language="typescript", kind="removal", category="deprecation",
              severity="major", applies={"typescript": ">=6.0"}, message="TypeScript 6.0 dropped the no-default-lib directive; use --noLib or --libReplacement.",
              url=TS6, doc="TypeScript 6.0 - Deprecated: no-default-lib Directives", doc_version="TypeScript 6.0", quote="In TypeScript 6.0, this directive is no longer supported.",
              bad="/// <reference no-default-lib=\"true\"/>\nexport {}\n", good="export {}\n",
              query=r'''((comment) @match (#match? @match "^///\\s*<reference\\s+no-default-lib"))''', tags=["ts6"]))

# ---------------------------------------------------------------- tsconfig
FILES = ["**/tsconfig*.json", "**/jsconfig*.json"]


def C(id, title, key, op, value, quote, msg, *, url, doc, sev="minor", kind="best-practice", applies=None, mode="deterministic", ai=None, bad=None, good=None, overrides=None, docv="TSConfig reference (current)", unless=None):
    c = {"key": "compilerOptions." + key, "op": op}
    if unless:
        c["unless_key"] = unless
    if value is not None:
        c["value"] = value
    R.append(rule("TS-CFG-" + id, title, language="tsconfig", kind=kind, category="configuration", severity=sev, applies=applies or {"typescript": ">=2.0"},
                  message=msg, url=url, doc=doc, doc_version=docv, quote=quote, engine="config", files=FILES, config=c, mode=mode, ai=ai, overrides=overrides,
                  bad=bad or ('{ "compilerOptions": { "%s": %s } }' % (key, "true" if value is True else "false" if value is False else '"x"')),
                  good=good or '{ "compilerOptions": { "strict": true } }'))


def opt(o):
    return f"https://www.typescriptlang.org/tsconfig/{o}.html"


C("OUTFILE-001", "outFile was removed in TypeScript 6.0", "outFile", "exists", None, "The --outFile option has been removed from TypeScript 6.0.",
  "Use a bundler to concatenate output; outFile is gone in TypeScript 6.0/7.0.", url=TS6, doc="TypeScript 6.0 - Deprecated: outFile", sev="major", kind="removal",
  applies={"typescript": ">=6.0"}, overrides=[{"when": {"typescript": ">=7.0"}, "severity": "critical"}], docv="TypeScript 6.0",
  bad='{ "compilerOptions": { "outFile": "dist/app.js" } }')
for k in ("esModuleInterop", "allowSyntheticDefaultImports"):
    C(f"{k.upper()}-FALSE-001", f"{k}: false is no longer allowed (TypeScript 6.0)", k, "equals", False, "The following settings can no longer be set to false",
      f"{k} is always on from TypeScript 6.0; remove the false setting and fix default-import usage.", url=TS6,
      doc="TypeScript 6.0 - Deprecated: --esModuleInterop false and --allowSyntheticDefaultImports false", sev="major", kind="removal", applies={"typescript": ">=6.0"},
      overrides=[{"when": {"typescript": ">=7.0"}, "severity": "critical"}], docv="TypeScript 6.0")
C("ALWAYSSTRICT-FALSE-001", "alwaysStrict: false is deprecated (TypeScript 6.0)", "alwaysStrict", "equals", False,
  "In TypeScript 6.0, all code will be assumed to be in JavaScript strict mode", "All code is treated as strict mode from TypeScript 6.0; fix sloppy-mode code and remove the flag.",
  url=TS6, doc="TypeScript 6.0 - Deprecated: --alwaysStrict false", sev="major", kind="removal", applies={"typescript": ">=6.0"},
  overrides=[{"when": {"typescript": ">=7.0"}, "severity": "critical"}], docv="TypeScript 6.0")
TS5 = "https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-0.html"
for k in ("out", "noImplicitUseStrict", "keyofStringsOnly", "suppressExcessPropertyErrors", "suppressImplicitAnyIndexErrors", "noStrictGenericChecks", "charset"):
    C(f"TS55-{k.upper()}-001", f"{k} was deprecated in TypeScript 5.0 and removed in 5.5", k, "exists", None, f"--{k}",
      f"'{k}' was deprecated in TypeScript 5.0 and removed in 5.5 (ignoreDeprecations no longer helps).", url=TS5,
      doc="TypeScript 5.0 - Deprecations and Default Changes", sev="critical", kind="removal", applies={"typescript": ">=5.5"}, docv="TypeScript 5.0 / 5.5",
      overrides=None, bad='{ "compilerOptions": { "%s": %s } }' % (k, '"dist/a.js"' if k in ("out", "charset") else "true"))
C("NOUNCHECKEDSIDEEFFECT-FALSE-001", "noUncheckedSideEffectImports disabled", "noUncheckedSideEffectImports", "equals", False,
  "TypeScript will error if it can’t find a source file for a side effect import", "Typos in side-effect imports (import './polyfil') go unnoticed; TypeScript 6.0 enables this by default.",
  url=opt("noUncheckedSideEffectImports"), doc="TSConfig noUncheckedSideEffectImports", applies={"typescript": ">=5.6"})
OFF = [
    ("NOIMPLICITANY", "noImplicitAny", "TypeScript will fall back to a type of any for a variable when it cannot infer the type", "major",
     "Implicit any silently disables checking for unannotated parameters."),
    ("STRICTNULLCHECKS", "strictNullChecks", "null and undefined are effectively ignored by the language. This can lead to unexpected errors at runtime.", "major",
     "Without strictNullChecks null/undefined are assignable everywhere - the #1 source of runtime TypeErrors."),
    ("STRICTFUNCTIONTYPES", "strictFunctionTypes", "parameters to be checked more correctly", "minor", "Function parameter bivariance lets unsafe callbacks through."),
    ("STRICTPROPERTYINIT", "strictPropertyInitialization", "TypeScript will raise an error when a class property was declared but not set in the constructor", "minor",
     "Class fields can be read before they are initialised."),
    ("NOIMPLICITTHIS", "noImplicitThis", "'this' implicitly has type 'any' because it does not have a type annotation", "minor", "this of type any is unchecked."),
    ("USEUNKNOWNINCATCH", "useUnknownInCatchVariables", "you do not need the additional syntax ( : unknown ) nor a linter rule to try enforce this behavior", "minor",
     "Catch variables become any, hiding non-Error throwables."),
    ("FORCECASING", "forceConsistentCasingInFileNames", "TypeScript will issue an error if a program tries to include a file by a casing different from the casing on disk", "minor",
     "Imports with wrong casing work on macOS/Windows and break on Linux CI/production."),
]
for id, k, q, sev, msg in OFF:
    C(id + "-FALSE-001", f"{k} explicitly disabled", k, "equals", False, q, msg, url=opt(k), doc=f"TSConfig {k}", sev=sev)
C("ALLOWUNREACHABLE-001", "allowUnreachableCode: true hides dead code", "allowUnreachableCode", "equals", True, "Unreachable code detected",
  "Unreachable code is usually a bug (misplaced return); keep the compiler check on.", url=opt("allowUnreachableCode"), doc="TSConfig allowUnreachableCode")
C("ALLOWUNUSEDLABELS-001", "allowUnusedLabels: true hides likely object-literal mistakes", "allowUnusedLabels", "equals", True,
  "Labels are very rare in JavaScript and typically indicate an attempt to write an object literal", "Keep unused-label errors on.", url=opt("allowUnusedLabels"),
  doc="TSConfig allowUnusedLabels", sev="info")
OPTIN = [
    ("NOUNCHECKEDINDEXED", "noUncheckedIndexedAccess", "noUncheckedIndexedAccess will add undefined to any un-declared field in the type",
     "Index access (arr[i], record[key]) is typed as always present; enable noUncheckedIndexedAccess to surface missing-key bugs.", "minor"),
    ("NOIMPLICITOVERRIDE", "noImplicitOverride", "you can ensure that the sub-classes never go out of sync",
     "Require the override keyword so renamed base methods do not leave silent non-overrides.", "info"),
    ("NOFALLTHROUGH", "noFallthroughCasesInSwitch", "This means you won’t accidentally ship a case fallthrough bug.", "Report switch fall-through at compile time.", "info"),
    ("NOIMPLICITRETURNS", "noImplicitReturns", "TypeScript will check all code paths in a function to ensure they return a value",
     "Functions with a missing return path return undefined silently.", "info"),
    ("EXACTOPTIONAL", "exactOptionalPropertyTypes", "TypeScript applies stricter rules around how it handles properties on type or interfaces which have a ? prefix",
     "Distinguish 'missing' from 'present but undefined' for optional properties.", "info"),
]
for id, k, q, msg, sev in OPTIN:
    # a tsconfig with "extends" may inherit the option: absence cannot be decided from this file
    C(id + "-001", f"{k} not enabled", k, "absent", None, q, msg, url=opt(k), doc=f"TSConfig {k}", sev=sev, unless="extends", bad='{ "compilerOptions": { "strict": true } }',
      good='{ "compilerOptions": { "%s": true } }' % k)

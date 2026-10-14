"""Simplification pack for JavaScript/TypeScript (also Vue <script>): collapsible loops
-> Array/Object built-ins (with the ECMAScript edition each needs), hand-written helpers that the
platform or an installed dependency replaces, and repo-index checks."""
from specs._simplify import simp, index_rules, helper, loop

P = simp("SIMP-JS", "javascript", "MDN (2026)", {"ecmascript": ">=2015"})
MDN = "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/"
ARR = MDN + "Global_Objects/Array/"

loop(P, "INCLUDES", "Loop that is Array.prototype.includes", ARR + "includes",
     "method of Array instances determines whether an array includes a certain value among its entries",
     '(for_in_statement body: (statement_block . (if_statement condition: (parenthesized_expression (binary_expression operator: "===")) consequence: [(statement_block . (return_statement (true)) .) (return_statement (true))] !alternative) .)) @match',
     "function has(xs, v) {\n  for (const x of xs) {\n    if (x === v) {\n      return true\n    }\n  }\n  return false\n}\n",
     "function has(xs, v) {\n  return xs.includes(v)\n}\n", "Use xs.includes(v) (ES2016).", applies={"ecmascript": ">=2016"})
loop(P, "SOME", "Loop that is Array.prototype.some", ARR + "some", "returns true if it finds an element in the array that satisfies the provided testing function",
     '(for_in_statement body: (statement_block . (if_statement condition: (parenthesized_expression) @c consequence: [(statement_block . (return_statement (true)) .) (return_statement (true))] !alternative) .) (#not-match? @c "^\\\\(\\\\s*\\\\w+\\\\s*===")) @match',
     "function anyAdmin(users) {\n  for (const u of users) {\n    if (u.role === 'admin' && u.active) return true\n  }\n  return false\n}\n",
     "function anyAdmin(users) {\n  return users.some((u) => u.role === 'admin' && u.active)\n}\n", "Use xs.some(predicate) / xs.every(predicate).")
loop(P, "FROMENTRIES", "Loop that is Object.fromEntries", MDN + "Global_Objects/Object/fromEntries",
     "static method transforms a list of key-value pairs into an object",
     '(for_in_statement left: (array_pattern) body: (statement_block . (expression_statement (assignment_expression left: (subscript_expression))) .)) @match',
     "function toObj(pairs) {\n  const o = {}\n  for (const [k, v] of pairs) {\n    o[k] = v\n  }\n  return o\n}\n",
     "function toObj(pairs) {\n  return Object.fromEntries(pairs)\n}\n", "Use Object.fromEntries(pairs) (ES2019).", applies={"ecmascript": ">=2019"})
loop(P, "FINDLAST", "Reverse search loop that is findLast", ARR + "findLast", "method of Array instances iterates the array in reverse order",
     '(for_statement increment: (update_expression) @u body: (statement_block . (if_statement consequence: [(statement_block . (return_statement (subscript_expression)) .) (return_statement (subscript_expression))]) .) (#match? @u "--")) @match',
     "function lastError(logs) {\n  for (let i = logs.length - 1; i >= 0; i--) {\n    if (logs[i].level === 'error') return logs[i]\n  }\n}\n",
     "function lastError(logs) {\n  return logs.findLast((l) => l.level === 'error')\n}\n", "Use findLast / findLastIndex (ES2023).", applies={"ecmascript": ">=2023"})

helper(P, "UNIQ", "Hand-written unique/dedupe helper", MDN + "Global_Objects/Set", "The Set object lets you store unique values of any type",
       ["uniq", "unique", "dedupe", "distinct", "removeDuplicates", "uniqueArray"], "[...new Set(xs)]",
       "function unique(xs) {\n  const out = []\n  for (const x of xs) {\n    if (!out.includes(x)) out.push(x)\n  }\n  return out\n}\n",
       "function tags(xs) {\n  return [...new Set(xs)]\n}\n", uses=["new Set"])
helper(P, "GROUPBY", "Hand-written groupBy helper", MDN + "Global_Objects/Object/groupBy", "static method groups the elements of a given iterable",
       ["groupBy", "groupby", "group", "partitionBy", "bucketBy"], "Object.groupBy",
       "function groupBy(xs, key) {\n  const out = {}\n  for (const x of xs) {\n    (out[key(x)] ||= []).push(x)\n  }\n  return out\n}\n",
       "function byStatus(xs) {\n  return Object.groupBy(xs, (x) => x.status)\n}\n", applies={"ecmascript": ">=2024"}, uses=["Object.groupBy", "Map.groupBy"])
helper(P, "DEEPCLONE", "Hand-written deep clone helper", "https://developer.mozilla.org/en-US/docs/Web/API/Window/structuredClone",
       "creates a deep clone of a value using the structured clone algorithm", ["deepClone", "cloneDeep", "deepCopy", "clone"], "structuredClone",
       "function deepClone(o) {\n  return JSON.parse(JSON.stringify(o))\n}\n", "function snapshot(o) {\n  return structuredClone(o)\n}\n",
       uses=["structuredClone"], loop=False, max_lines=30)
# structuredClone throws DataCloneError on Vue reactive/ref proxies, Pinia state and MobX observables
P.R[-1]["ai_question"] += (" In particular, does no caller pass a Vue reactive/ref proxy, Pinia store state or MobX observable"
                           " (structuredClone throws DataCloneError on proxies; they need toRaw first)?")
helper(P, "DEBOUNCE", "Hand-written debounce while lodash is installed", "https://lodash.com/docs/4.17.15",
       "Creates a debounced function that delays invoking func", ["debounce", "throttle"], "lodash debounce/throttle",
       "function debounce(fn, ms) {\n  let t\n  return (...a) => {\n    clearTimeout(t)\n    t = setTimeout(() => fn(...a), ms)\n  }\n}\n",
       "const onResize = debounce(layout, 100)\n", uses=["lodash"], loop=False, max_lines=25, dep="lodash", doc="lodash _.debounce")

D = {
    "unused-export": (MDN + "Statements/export", "The export declaration is used to export values from a JavaScript module", "MDN: export"),
    "unused-flag": ("https://github.com/tj/commander.js", "Options are defined with the .option() method", "Commander.js: Options"),
    "unused-file": (MDN + "Statements/export", "The export declaration is used to export values from a JavaScript module", "MDN: export"),
    "middle-man": (MDN + "Statements/export", "The export declaration is used to export values from a JavaScript module", "MDN: export"),
    "nested-loop-no-limit-note": (MDN + "Global_Objects/Set", "The Set object lets you store unique values of any type", "MDN: Set"),
    "limit-note-incomplete": (MDN + "Global_Objects/Set", "The Set object lets you store unique values of any type", "MDN: Set"),
    "duplicate-helper": (MDN + "Statements/export", "The export declaration is used to export values from a JavaScript module", "MDN: export"),
    "call-site-patches": (MDN + "Statements/export", "The export declaration is used to export values from a JavaScript module", "MDN: export"),
    "test-missing": ("https://nodejs.org/api/test.html", "The node:test module facilitates the creation of JavaScript tests", "Node.js test runner"),
}
NL = "export function common(a, b) {\n  const out = []\n%s  for (const x of a) {\n    for (const y of b) {\n      if (x === y) out.push(x)\n    }\n  }\n  return out\n}\n"
GUARD = "export function %s(p) {\n  if (!p) return\n  load(p)\n}\n"
CL = "export function classify(n) {\n  if (n < 0) return 'neg'\n  else if (n === 0) return 'zero'\n  if (n % 2 === 0) return 'even'\n  if (n > 100) return 'big'\n  return 'odd'\n}\n"
index_rules(P, {
    "unused-export": ("// file: src/text.js\nexport function slugify(s) { return s.toLowerCase() }\n",
                      "// file: src/text.js\nexport function slugify(s) { return s.toLowerCase() }\n// file: src/page.js\nimport { slugify } from './text.js'\nconsole.log(slugify('A'))\n"),
    "unused-flag": ("import { program } from 'commander'\nprogram.option('--dry-run', 'do nothing')\nprogram.parse()\n",
                    "import { program } from 'commander'\nprogram.option('--dry-run', 'do nothing')\nprogram.parse()\nif (program.opts().dryRun) console.log('dry')\n"),
    "unused-file": ("// file: src/old-helpers.js\nexport const pad = (s) => s.padStart(2, '0')\n// file: src/core.js (existing)\nconsole.log(1)\n",
                    "// file: src/old-helpers.js\nexport const pad = (s) => s.padStart(2, '0')\n// file: src/core.js (existing)\nimport { pad } from './old-helpers'\nconsole.log(pad('1'))\n"),
    "middle-man": ("// file: src/users.js\nimport { client } from './client'\nexport function getUser(id) { return client.getUser(id) }\nexport function getPosts(id, page) { return client.getPosts(id, page) }\n",
                   "// file: src/users.js\nimport { client } from './client'\nexport function getUser(id) { return client.getUser(id) }\nexport function getPosts(id, page) { return client.getPosts(id, page ?? 1) }\n"),
    "nested-loop-no-limit-note": (NL % "", NL % "  // limit: a and b stay under 50 items; switch to a Set if they grow\n"),
    "limit-note-incomplete": (NL % "  // limit: quadratic but fine\n", NL % "  // limit: O(n*m), n < 100 here; switch to a Set when it grows\n"),
    "duplicate-helper": ("// file: src/a.js\nexport function normalize(s) {\n  s = s.trim()\n  s = s.toLowerCase()\n  return s\n}\n// file: src/b.js\nexport function clean(v) {\n  v = v.trim()\n  v = v.toLowerCase()\n  return v\n}\n",
                         "// file: src/a.js\nexport function normalize(s) {\n  s = s.trim()\n  s = s.toLowerCase()\n  return s\n}\n// file: src/b.js\nexport function clean(v) {\n  v = v.trim()\n  v = v.toUpperCase()\n  return v\n}\n"),
    "call-site-patches": ("// file: src/load.js (existing)\nexport function load(p) {}\n// file: src/use.js\n" + GUARD % "a" + GUARD % "b" + GUARD % "c",
                          "// file: src/load.js (existing)\nexport function load(p) {}\n// file: src/use.js\n" + GUARD % "a" + "export function b(p) { load(p) }\n"),
    "test-missing": ("// file: src/sign.js\nexport function sign(n) { return n < 0 ? -1 : 1 }\n// file: src/sign.test.js\nimport { sign } from './sign'\ntest('neg', () => expect(sign(-2)).toBe(-1))\n" + "// file: src/classify.js\n" + CL, "// file: src/sign.js\nexport function sign(n) { return n < 0 ? -1 : 1 }\n// file: src/sign.test.js\nimport { sign } from './sign'\ntest('neg', () => expect(sign(-2)).toBe(-1))\n" + "// file: src/classify.js\n" + CL + "// file: src/classify.test.js\nimport { classify } from './classify'\ntest('even', () => expect(classify(2)).toBe('even'))\n"),
}, D)

RULES = P.R

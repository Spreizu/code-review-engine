"""Simplification pack for Python: collapsible loops -> builtins/itertools/collections,
hand-written helpers the stdlib replaces, and repo-index checks."""
from specs._simplify import simp, index_rules, helper, loop

P = simp("SIMP-PY", "python", "Python 3.14", {"python": "*"})
FN, IT, COL, ST = ("https://docs.python.org/3/library/functions.html", "https://docs.python.org/3/library/itertools.html",
                   "https://docs.python.org/3/library/collections.html", "https://docs.python.org/3/library/stdtypes.html")

loop(P, "ANY", "Loop that is any()/all()", FN, "Return True if any element of the iterable is true",
     '(for_statement body: (block . (if_statement consequence: (block . (return_statement (true)) .) !alternative) .)) @match',
     "def has_admin(users):\n    for u in users:\n        if u.is_admin:\n            return True\n    return False\n",
     "def has_admin(users):\n    return any(u.is_admin for u in users)\n", "Use any(...) / all(...) with a generator expression.")
loop(P, "SUM", "Accumulator loop that is sum()", FN, "Sums start and the items of an iterable",
     '((expression_statement (assignment left: (identifier) @t right: (integer) @z)) . (for_statement body: (block . (expression_statement (augmented_assignment left: (identifier) @t2 operator: "+=")) .)) @match (#eq? @t @t2) (#eq? @z "0"))',
     "def total(items):\n    t = 0\n    for i in items:\n        t += i.price\n    return t\n",
     "def total(items):\n    return sum(i.price for i in items)\n", "Use sum(...) with a generator expression.")
loop(P, "MAX", "Loop that is max()/min()", FN, "Return the largest item in an iterable",
     '(for_statement left: (identifier) @x body: (block . (if_statement condition: (comparison_operator (identifier) @a) consequence: (block . (expression_statement (assignment right: (identifier) @v)) .) !alternative) .) (#eq? @x @v) (#eq? @a @x)) @match',
     "def top(xs):\n    m = xs[0]\n    for x in xs:\n        if x > m:\n            m = x\n    return m\n",
     "def top(xs):\n    return max(xs)\n", "Use max(...) / min(...), with key= for a custom ordering.")
loop(P, "COUNTER", "dict.get counting loop that is collections.Counter", COL, "A Counter is a dict subclass for counting hashable objects",
     '(for_statement body: (block . (expression_statement (assignment right: (binary_operator left: (call function: (attribute attribute: (identifier) @g) arguments: (argument_list (_) (integer)))))) .) (#eq? @g "get")) @match',
     "def freq(words):\n    counts = {}\n    for w in words:\n        counts[w] = counts.get(w, 0) + 1\n    return counts\n",
     "def freq(words):\n    return Counter(words)\n", "Use collections.Counter(iterable).")

helper(P, "FLATTEN", "Hand-written flatten helper", IT, "Alternate constructor for chain()", ["flatten", "flat", "flatten_list", "flatten_once"],
       "itertools.chain.from_iterable", "def flatten(xss):\n    out = []\n    for xs in xss:\n        for x in xs:\n            out.append(x)\n    return out\n",
       "def all_tags(posts):\n    return list(chain.from_iterable(p.tags for p in posts))\n", uses=["chain"])
helper(P, "BATCHED", "Hand-written chunking helper", IT, "Batch data from the iterable into tuples of length n",
       ["chunks", "chunked", "batch", "batches", "grouper", "chunk"], "itertools.batched",
       "def chunks(xs, n):\n    out = []\n    for i in range(0, len(xs), n):\n        out.append(xs[i:i + n])\n    return out\n",
       "def pages(xs):\n    return list(batched(xs, 50))\n", applies={"python": ">=3.12"}, uses=["batched"])
helper(P, "DEDUPE", "Hand-written order-preserving dedupe", ST, "dict.fromkeys", ["unique", "dedupe", "uniq", "remove_duplicates", "distinct", "deduplicate"],
       "dict.fromkeys (or set)", "def unique(xs):\n    seen = []\n    for x in xs:\n        if x not in seen:\n            seen.append(x)\n    return seen\n",
       "def tags(xs):\n    return list(dict.fromkeys(xs))\n", uses=["fromkeys", "set("])
helper(P, "COUNT", "Hand-written frequency count helper", COL, "A Counter is a dict subclass for counting hashable objects",
       ["count_items", "frequencies", "count_occurrences", "histogram", "word_count", "counts"], "collections.Counter",
       "def frequencies(xs):\n    d = {}\n    for x in xs:\n        d[x] = d.get(x, 0) + 1\n    return d\n", "def tally(xs):\n    return Counter(xs)\n", uses=["Counter"])

D = {
    "unused-export": ("https://docs.python.org/3/tutorial/classes.html", "a name prefixed with an underscore", "Python tutorial: Private variables"),
    "unused-flag": ("https://docs.python.org/3/library/argparse.html", "dest", "argparse"),
    "unused-file": ("https://docs.python.org/3/tutorial/modules.html", "A module is a file containing Python definitions and statements", "Python tutorial: Modules"),
    "middle-man": ("https://docs.python.org/3/tutorial/modules.html", "A module is a file containing Python definitions and statements", "Python tutorial: Modules"),
    "nested-loop-no-limit-note": (ST, "Common uses include membership testing, removing duplicates from a sequence", "Set types"),
    "limit-note-incomplete": (ST, "Common uses include membership testing, removing duplicates from a sequence", "Set types"),
    "global-lock-no-limit-note": ("https://docs.python.org/3/library/threading.html", "A primitive lock is a synchronization primitive", "threading: Lock objects"),
    "duplicate-helper": ("https://docs.python.org/3/tutorial/modules.html", "A module is a file containing Python definitions and statements", "Python tutorial: Modules"),
    "call-site-patches": ("https://docs.python.org/3/tutorial/modules.html", "A module is a file containing Python definitions and statements", "Python tutorial: Modules"),
    "test-missing": ("https://docs.python.org/3/library/unittest.html", "A test case is the individual unit of testing", "unittest"),
}
NL = "def common(a, b):\n    out = []\n%s    for x in a:\n        for y in b:\n            if x == y:\n                out.append(x)\n    return out\n"
GUARD = "def %s(p):\n    if p is None:\n        return\n    load(p)\n\n"
CL = "def classify(n):\n    if n < 0:\n        return 'neg'\n    elif n == 0:\n        return 'zero'\n    if n % 2 == 0:\n        return 'even'\n    if n > 100:\n        return 'big'\n    return 'odd'\n"
index_rules(P, {
    "unused-export": ("# file: pkg/textutil.py\ndef slugify(s):\n    return s.lower()\n",
                      "# file: pkg/textutil.py\ndef slugify(s):\n    return s.lower()\n# file: pkg/views.py\nfrom pkg.textutil import slugify\n\nprint(slugify('A'))\n"),
    "unused-flag": ("import argparse\np = argparse.ArgumentParser()\np.add_argument('--dry-run', action='store_true')\nargs = p.parse_args()\n",
                    "import argparse\np = argparse.ArgumentParser()\np.add_argument('--dry-run', action='store_true')\nargs = p.parse_args()\nif args.dry_run:\n    print('dry run')\n"),
    "unused-file": ("# file: pkg/old_helpers.py\ndef pad(s):\n    return s.zfill(2)\n# file: pkg/core.py (existing)\nprint(1)\n",
                    "# file: pkg/old_helpers.py\ndef pad(s):\n    return s.zfill(2)\n# file: pkg/core.py (existing)\nfrom pkg.old_helpers import pad\nprint(pad('1'))\n"),
    "middle-man": ("# file: pkg/store.py\nfrom pkg import cache\n\ndef get(k):\n    return cache.get(k)\n\ndef put(k, v):\n    return cache.put(k, v)\n",
                   "# file: pkg/store.py\nfrom pkg import cache\n\ndef get(k):\n    return cache.get(k)\n\ndef put(k, v):\n    return cache.put(k, v.strip())\n"),
    "nested-loop-no-limit-note": (NL % "", NL % "    # limit: a and b stay under 50 items; switch to a set if they grow\n"),
    "limit-note-incomplete": (NL % "    # limit: quadratic but fine\n", NL % "    # limit: O(n*m), n < 100 here; switch to a set when it grows\n"),
    "global-lock-no-limit-note": ("import threading\n\n_lock = threading.Lock()\n",
                                "import threading\n\n# limit: one lock for the whole cache, fine below ~1k req/s; shard per key beyond that\n_lock = threading.Lock()\n"),
    "duplicate-helper": ("# file: a.py\ndef normalize(s):\n    s = s.strip()\n    s = s.lower()\n    return s\n# file: b.py\ndef clean(v):\n    v = v.strip()\n    v = v.lower()\n    return v\n",
                         "# file: a.py\ndef normalize(s):\n    s = s.strip()\n    s = s.lower()\n    return s\n# file: b.py\ndef clean(v):\n    v = v.strip()\n    return v\n"),
    "call-site-patches": ("# file: loader.py (existing)\ndef load(p):\n    pass\n# file: use.py\n" + GUARD % "a" + GUARD % "b" + GUARD % "c",
                          "# file: loader.py (existing)\ndef load(p):\n    pass\n# file: use.py\n" + GUARD % "a" + "def b(p):\n    load(p)\n"),
    "test-missing": ("# file: num/sign.py\ndef sign(n):\n    return -1 if n < 0 else 1\n# file: tests/test_sign.py\nfrom num.sign import sign\n\ndef test_neg():\n    assert sign(-2) == -1\n" + "# file: num/classify.py\n" + CL, "# file: num/sign.py\ndef sign(n):\n    return -1 if n < 0 else 1\n# file: tests/test_sign.py\nfrom num.sign import sign\n\ndef test_neg():\n    assert sign(-2) == -1\n" + "# file: num/classify.py\n" + CL + "# file: tests/test_classify.py\nfrom num.classify import classify\n\ndef test_even():\n    assert classify(2) == 'even'\n"),
}, D)

RULES = P.R

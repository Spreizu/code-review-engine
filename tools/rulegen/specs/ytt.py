"""Carvel ytt pack. No dedicated grammar exists: YAML templates are parsed with the official YAML grammar and ytt
directives/annotations are matched on (comment) nodes (`#@ ...`); Starlark modules (*.star) are parsed with the Python
grammar (ytt Starlark is Python-like but closes blocks with `end`). Version dimension `ytt` comes from
version.require_at_least("x.y.z") or presence of ytt templates / _ytt_lib. Source: carvel.dev ytt docs (v0.52.x)."""
from specs._common import Pack

B = "https://carvel.dev/ytt/docs/v0.52.x/"
YF = ["**/*.yml", "**/*.yaml"]
P = Pack("YTT", "yaml", "ytt v0.52.x", {"ytt": "*"}, files=YF, framework="ytt")
IS_YTT = r"file.has_re:(?m)^\s*#@"
LOAD = '#@ load("@ytt:data", "data")\n'

P("UNKNOWN-COMMENT-SYNTAX", "Plain # comment in a ytt template", B + "faq/",
  "You can, but it is discouraged to avoid tricky errors that can go unchecked. The recommended approach is when writing ytt templated files, use ytt comments",
  r'((comment) @match (#not-match? @match "^#[@!]"))',
  LOAD + "---\n# number of pods\nreplicas: #@ data.values.replicas\n", LOAD + "---\n#! number of pods\nreplicas: #@ data.values.replicas\n",
  "ytt rejects plain YAML comments in templates (\"Unknown comment syntax\") unless --ignore-unknown-comments; use #! — it also catches a forgotten @.",
  sev="major", kind="anti-pattern", cat="correctness", filters=[IS_YTT], xref=[B + "file-marks/"])
P("LOAD-NEEDS-SPACE", "Directive written without a space (#@load / #@if / #@def)", B + "faq/",
  "The space is subtly meaningful, and directly, load needs a space, while overlay/match does not",
  r'((comment) @match (#match? @match "^#@(load|if|for|def|end|else|elif|return)\\b"))',
  '#@load("@ytt:data", "data")\n---\nreplicas: #@ data.values.replicas\n', LOAD + "---\nreplicas: #@ data.values.replicas\n",
  "Without the space ytt reads it as an annotation named 'load'/'if' and fails; code directives are '#@ <code>', annotations are '#@name'.",
  sev="major", kind="anti-pattern", cat="correctness")
P("BLOCK-WITHOUT-END", "#@ def/for/if without a closing #@ end", B + "lang-ref-def/",
  "Note that ytt’s Starlark use requires functions to be closed with an end .",
  r'((comment) @match (#match? @match "^#@ +(def|for|if) .*:\\s*$"))',
  "#@ def labels():\napp: web\n---\nmetadata:\n  labels: #@ labels()\n", "#@ def labels():\napp: web\n#@ end\n---\nmetadata:\n  labels: #@ labels()\n",
  "Every multi-line #@ def/for/if block must be closed with #@ end (ytt Starlark is indentation-insensitive).", sev="major", kind="anti-pattern",
  cat="correctness", filters=[r"file.lacks_re:(?m)^\s*#@ +end\b"], xref=[B + "lang-ref-if/", B + "lang-ref-for/"])
P("ANCHOR-WITH-DIRECTIVE", "YAML anchor on a templated node", B + "known-limitations/",
  "YAML anchors and templating directive for the same YAML node are not supported.",
  r'((block_mapping (block_mapping_pair value: (flow_node (anchor) .)) . (comment) @match) (#match? @match "^#@ "))',
  LOAD + "---\nfirst: &content #@ data.values.port\nsecond: *content\n", LOAD + "---\n#@ port = data.values.port\nfirst: #@ port\nsecond: #@ port\n",
  "Anchors resolve before ytt evaluates, so the alias gets null; use a Starlark variable or function instead.", sev="major", kind="anti-pattern",
  cat="correctness")
P("DATA-VALUES-TO-SCHEMA", "#@data/values defaults file without schema", B + "data-values-schema-migration-guide/",
  "Without Schema, validating the presence of Data Values requires additional ytt configuration containing Starlark assertions.",
  r'((comment) @match (#match? @match "^#@data/values\\s*$"))',
  "#@data/values\n---\nreplicas: 2\nimage: nginx\n", "#@data/values-schema\n---\nreplicas: 2\nimage: nginx\n",
  "Declare defaults with #@data/values-schema to get types, defaults and validation; keep #@data/values for overlays of values.",
  sev="info", kind="modernization", cat="modernization", mode="ai-confirm",
  ai="Is this the file that declares the defaults (not a per-environment values overlay)?")
P("SCHEMA-ARRAY-MULTIPLE-ITEMS", "Schema array with more than one item", B + "lang-ref-ytt-schema/",
  "The schema of an array must contain exactly one (1) item.",
  '(block_sequence (block_sequence_item) (block_sequence_item)) @match\n(flow_sequence (flow_node) "," (flow_node)) @match',
  "#@data/values-schema\n---\ndomains:\n- apps.example.com\n- api.example.com\n",
  '#@data/values-schema\n---\n#@schema/default ["apps.example.com", "api.example.com"]\ndomains:\n- ""\n',
  "Schema arrays describe the item type with exactly one element (default is []); use #@schema/default for default items.", sev="major",
  kind="anti-pattern", cat="correctness", filters=[r"file.has_re:#@data/values-schema", r"node.lacks_re:#@schema/(type|default)"])
P("SCHEMA-DEFAULT-VERSION", "#@schema/default needs ytt >= 0.38.0", B + "lang-ref-ytt-schema/",
  "this value must be of the same type as the value given on the node. (as of v0.38.0)",
  r'((comment) @match (#match? @match "^#@schema/default\\b"))',
  '#@ load("@ytt:version", "version")\n#@ version.require_at_least("0.35.0")\n#@data/values-schema\n---\n#@schema/default ["a"]\ndomains:\n- ""\n',
  '#@data/values-schema\n---\ndomains:\n- ""\n',
  "Raise the minimum ytt version (version.require_at_least) or drop @schema/default.", sev="major", kind="migration", cat="compatibility",
  applies={"ytt": "<0.38.0"}, docv="ytt 0.38.0")
P("SCHEMA-TYPE-ANY", "#@schema/type any=True", B + "lang-ref-ytt-schema/", "The annotated node and its nested children are not checked by schema, and has no schema defaulting behavior.",
  r'((comment) @match (#match? @match "^#@schema/type\\s+any\\s*=\\s*True"))',
  "#@data/values-schema\n---\n#@schema/type any=True\nresources: {}\n", "#@data/values-schema\n---\nresources:\n  cpu: 100m\n  memory: 128Mi\n",
  "any=True disables type checking/defaults for the subtree; declare the shape when it's known.", sev="info", kind="best-practice", cat="maintainability",
  mode="ai-confirm", ai="Is the subtree's shape actually known/stable (so it could be declared)?")
P("ASSERT-FAIL-FOR-REQUIRED", "data.values.x or assert.fail(...) (use schema validation)", B + "how-to-write-validations/", "@schema/validation",
  r'((comment) @match (#match? @match "^#@.*data\\.values\\.[A-Za-z0-9_.]+\\s+or\\s+assert\\.fail\\("))',
  '#@ load("@ytt:data", "data")\n#@ load("@ytt:assert", "assert")\n---\npassword: #@ data.values.db.password or assert.fail("missing db.password")\n',
  '#@ load("@ytt:data", "data")\n---\npassword: #@ data.values.db.password\n',
  "Declare the requirement once in schema (#@schema/validation min_len=1) so it's validated up front and documented.", sev="info", kind="modernization",
  cat="maintainability", mode="ai-confirm", ai="Does the project use a data values schema where a validation could be declared?", xref=[B + "faq/"])
P("TEXT-TEMPLATE-NOT-ENABLED", "(@ ... @) in a string without @yaml/text-templated-strings", B + "ytt-text-templating/",
  "To do so YAML node must be annotated with @yaml/text-templated-strings (v0.17.0+).",
  r'((string_scalar) @match (#match? @match "\\(@[-=]?.*@\\)"))' + "\n" + r'((double_quote_scalar) @match (#match? @match "\\(@[-=]?.*@\\)"))',
  LOAD + '---\nhost: "(@= data.values.name @).example.com"\n', LOAD + '---\nhost: #@ data.values.name + ".example.com"\n',
  "Without the annotation the (@ @) markers are emitted literally.", sev="major", kind="anti-pattern", cat="correctness",
  filters=[r"file.lacks_re:@yaml/text-templated-strings", IS_YTT])
P("OVERLAY-APPEND-REDUNDANT", "#@overlay/append on an array item (default since v0.32.0)", B + "lang-ref-ytt-overlay/",
  "v0.32.0 — omitting @overlay/append annotation implies a merge operation and 0 matches, defaulting to insert after the last item.",
  r'((comment) @match (#match? @match "^#@overlay/append\\s*$"))',
  '#@ load("@ytt:overlay", "overlay")\n#@overlay/match by=overlay.all\n---\nitems:\n#@overlay/append\n- c\n',
  '#@ load("@ytt:overlay", "overlay")\n#@overlay/match by=overlay.all\n---\nitems:\n- c\n',
  "Array items without a matcher are appended by default since v0.32.0.", sev="info", kind="best-practice", cat="maintainability",
  applies={"ytt": ">=0.32.0"}, docv="ytt 0.32.0+")
P("OVERLAY-MISSING-OK-NEW-KEY", "Data value added via --data-value-style override", B + "faq/",
  "As with all data values, those passed through --data-value must be overrides, not new values. Instead, overlays are the intended way to provide new keys.",
  r'((comment) @match (#match? @match "^#@data/values\\s*$"))',
  "#@data/values\n---\nnew_key: 1\n", '#@ load("@ytt:overlay", "overlay")\n#@data/values\n---\n#@overlay/match missing_ok=True\nnew_key: 1\n',
  "Keys that aren't in the base data values/schema need #@overlay/match missing_ok=True (or a schema entry).", sev="minor", kind="anti-pattern",
  cat="correctness", filters=[r"file.lacks_re:missing_ok\s*=\s*True"], mode="ai-confirm",
  ai="Do these keys not exist in the base data values/schema (so the override would fail)?")

# ------------------------------------------------------------------ builtin modules: must be loaded; version availability
MODS = [
    ("data", r"data\\.(values|read|list)\\b", B + "lang-ref-ytt/", 'load( "@ytt:data" , "data" )'),
    ("overlay", r"overlay\\.(subset|all|map_key|index|and_op|or_op|not_op|apply)\\b", B + "lang-ref-ytt-overlay/", '#@ load("@ytt:overlay", "overlay")'),
    ("struct", r"struct\\.(make|make_and_bind|encode|decode)\\(", B + "lang-ref-ytt-struct/", 'load( "@ytt:struct" , "struct" )'),
    ("assert", r"assert\\.(fail|equals|try_to|min|max|min_len|max_len|not_null|one_not_null|one_of|valid_port)\\(", B + "lang-ref-ytt-assert/", '#@ load("@ytt:assert", "assert")'),
    ("template", r"template\\.replace\\(", B + "lang-ref-ytt-template/", '#@ load("@ytt:template", "template")'),
    ("library", r"library\\.get\\(", B + "lang-ref-ytt-library/", '#@ load("@ytt:library", "library")'),
    ("version", r"version\\.require_at_least\\(", B + "lang-ref-ytt-version/", 'load( "@ytt:version" , "version" )'),
    ("json", r"json\\.(encode|decode)\\(", B + "lang-ref-ytt/", 'load( "@ytt:json" , "json" )'),
    ("yaml", r"yaml\\.(encode|decode)\\(", B + "lang-ref-ytt/", 'load( "@ytt:yaml" , "yaml" )'),
    ("base64", r"base64\\.(encode|decode)\\(", B + "lang-ref-ytt/", 'load( "@ytt:base64" , "base64" )'),
    ("regexp", r"regexp\\.(match|replace)\\(", B + "lang-ref-ytt/", 'load( "@ytt:regexp" , "regexp" )'),
    ("url", r"url\\.(parse|path_segment_encode|path_segment_decode|query_param_value_encode|query_param_value_decode|query_params_encode|query_params_decode)\\(", B + "lang-ref-ytt/", 'load( "@ytt:url" , "url" )'),
    ("sha256", r"sha256\\.sum\\(", B + "lang-ref-ytt/", 'load( "@ytt:sha256" , "sha256" )'),
    ("md5", r"md5\\.sum\\(", B + "lang-ref-ytt/", 'load( "@ytt:md5" , "md5" )'),
    ("ip", r"ip\\.(parse_addr|parse_cidr)\\(", B + "lang-ref-ytt/", 'load( "@ytt:ip" , "ip" )'),
    ("toml", r"toml\\.(encode|decode)\\(", B + "lang-ref-ytt/", 'load( "@ytt:toml" , "toml" )'),
]
USE = {"data": "data.values.replicas", "overlay": "overlay.subset({\"kind\": \"Deployment\"})", "struct": 'struct.encode({"a": 1})',
       "assert": 'assert.fail("missing")', "template": "template.replace(lib.eval())", "library": 'library.get("app")',
       "version": 'version.require_at_least("0.50.0")', "json": 'json.encode({"a": 1})', "yaml": 'yaml.encode({"a": 1})',
       "base64": 'base64.encode("x")', "regexp": 'regexp.match("^a", "abc")', "url": 'url.query_param_value_encode("a b")',
       "sha256": 'sha256.sum("x")', "md5": 'md5.sum("x")', "ip": 'ip.parse_addr("192.0.2.1")', "toml": 'toml.encode({"a": 1})'}
for mod, rx, url, needle in MODS:
    use = USE[mod]
    ld = f'#@ load("@ytt:{mod}", "{mod}")\n'
    yb = f"---\nvalue: #@ {use}\n" if mod not in ("overlay",) else f"#@overlay/match by={use}\n---\nspec: {{}}\n"
    P(f"MISSING-LOAD-{mod.upper()}", f"@ytt:{mod} used without load()", url, needle,
      f'((comment) @match (#match? @match "^#@.*\\\\b{rx}"))', yb, ld + yb,
      f"Starlark symbols must be loaded per file: add {ld.strip()}.", sev="major", kind="anti-pattern", cat="correctness",
      filters=[rf'file.lacks_re:load\(\s*"@ytt:{mod}"'], xref=[B + "lang-ref-load/"])
    if mod == "assert":  # `assert` is a Python keyword: the Python grammar can't parse assert.fail() in .star files
        continue
    P(f"STAR-MISSING-LOAD-{mod.upper()}", f"@ytt:{mod} used without load() (.star)", url, needle,
      f'((attribute object: (identifier) @m) @match (#eq? @m "{mod}") (#match? @match "^{rx.replace(chr(92)*2 + "(", chr(92)*2 + "b")}"))',
      f"def v():\n  return {use}\nend\n", f'load("@ytt:{mod}", "{mod}")\n\ndef v():\n  return {use}\nend\n',
      f"Load the module first: load(\"@ytt:{mod}\", \"{mod}\").", sev="major", kind="anti-pattern", cat="correctness", lang="python", files=["**/*.star"],
      filters=[rf'file.lacks_re:load\(\s*"@ytt:{mod}"'], xref=[B + "lang-ref-load/"])

for mod, ver, needle in [("ip", "0.37.0", "Parse and inspect Internet Protocol values. (available in v0.37.0+)"), ("toml", "0.38.0", "As of v0.38.0. load(")]:
    P(f"MODULE-{mod.upper()}-VERSION", f"@ytt:{mod} requires ytt >= {ver}", B + "lang-ref-ytt/", needle,
      f'((comment) @match (#match? @match "^#@ +load\\\\(\\\\s*.@ytt:{mod}."))',
      f'#@ load("@ytt:version", "version")\n#@ version.require_at_least("0.30.0")\n#@ load("@ytt:{mod}", "{mod}")\n---\nv: #@ {USE[mod]}\n',
      f'#@ load("@ytt:version", "version")\n#@ version.require_at_least("{ver}")\n---\nv: 1\n',
      f"Bump version.require_at_least to {ver}+ (older ytt fails to load the module).", sev="major", kind="migration", cat="compatibility",
      applies={"ytt": f"<{ver}"}, docv=f"ytt {ver}")

P("STAR-DEF-WITHOUT-END", "Starlark def without end (.star)", B + "lang-ref-def/", "Note that ytt’s Starlark use requires functions to be closed with an end .",
  "(function_definition) @match", "def labels():\n  return {\"app\": \"web\"}\n", "def labels():\n  return {\"app\": \"web\"}\nend\n",
  "ytt Starlark closes blocks with end.", sev="major", kind="anti-pattern", cat="correctness", lang="python", files=["**/*.star"],
  filters=[r"file.lacks_re:(?m)^\s*end\s*$"])
P("REQUIRE-MIN-VERSION", "Library without version.require_at_least", B + "lang-ref-ytt-version/",
  "Most of the time it’s best to check version first before processing other templates",
  '((comment) @match (#match? @match "^#@data/values-schema"))',
  "#@data/values-schema\n---\nreplicas: 2\n", '#@ load("@ytt:version", "version")\n#@ version.require_at_least("0.50.0")\n#@data/values-schema\n---\nreplicas: 2\n',
  "Declare the minimum ytt version (e.g. in 0-min-version.star) so old binaries fail fast instead of misrendering.", sev="info", kind="best-practice",
  cat="compatibility", filters=[r"file.lacks_re:require_at_least"], mode="ai-confirm",
  ai="Is there no version.require_at_least elsewhere in this library (e.g. a 0-min-version.star file)?")

RULES = P.R

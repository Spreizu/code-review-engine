"""Generic YAML pack: YAML 1.2.2 spec, yamllint rule set, 1.1-vs-1.2 typing gotchas, anchors, unsafe tags, secrets.
Base layer for docker compose, GitHub/GitLab CI, Kubernetes, ytt, etc."""
from specs._common import Pack, secret_rules, OWASP_SECRETS, OWASP_NEEDLE, SECRET_NAME_RE, PLACEHOLDER_RE

SPEC = "https://yaml.org/spec/1.2.2/"
YL = "https://yamllint.readthedocs.io/en/stable/rules.html"
P0 = Pack("YAML", "yaml", "YAML 1.2.2 / yamllint 1.37", {"any": "*"}, files=["!**/templates/**", "!**/*.j2", "!**/*.jinja*"])
ROOT = "[(stream) (ERROR)] @match"


def P(id, title, url, needle, query, *a, **kw):
    if query == ROOT:
        kw["filters"] = ["node.is_root"] + kw.get("filters", [])
    return P0(id, title, url, needle, query, *a, **kw)


P.R = P0.R
STR = "[(string_scalar) (double_quote_scalar) (single_quote_scalar) (block_scalar)]"
VAL = lambda inner: f"(block_mapping_pair value: (flow_node (plain_scalar {inner})))"
SPECV = "YAML 1.2.2"

P("DUPLICATE-KEY", "Duplicate mapping key", SPEC, "with the restriction that each of the keys is unique",
  '(block_mapping (block_mapping_pair key: (_) @match))',
  "image: nginx\nports: [80]\nimage: httpd\n", "image: nginx\nports: [80]\n",
  "Duplicate key: YAML requires unique keys; most loaders silently keep the last value.", sev="major", cat="correctness", docv=SPECV, filters=["node.dup_sibling_key"])
P("DUPLICATE-KEY-FLOW", "Duplicate key in a flow mapping", YL, "Use this rule to prevent multiple entries with the same key",
  '(flow_mapping (flow_pair key: (_) @match))', "a: {x: 1, x: 2}\n", "a: {x: 1, y: 2}\n",
  "Duplicate key inside a flow mapping.", sev="major", cat="correctness", filters=["node.dup_sibling_key"])
P("SYNTAX-ERROR", "YAML syntax error", SPEC, "A version 1.2 YAML processor must also accept documents", '(ERROR) @match',
  "a: [1, 2\nb: 3\n", "a: [1, 2]\nb: 3\n", "The document does not parse as YAML.", sev="major", cat="correctness", docv=SPECV,
  filters=[r"file.lacks_re:\{\{[-~]?\s|\{%"])
P("TAB-INDENT", "Tab characters used for indentation", SPEC, "tab characters must not be used in indentation",
  ROOT, "a:\n\tb: 1\n", "a:\n  b: 1\n", "Tabs are not allowed in YAML indentation.", sev="major", cat="correctness",
  docv=SPECV, filters=[r"file.has_re:(?m)^ *\t+ *[^\s#]"])
P("TRUTHY", "YAML 1.1 boolean-like plain value (yes/no/on/off)", YL, "Use this rule to forbid non-explicitly typed truthy values",
  VAL('(string_scalar) @match (#match? @match "^(yes|Yes|YES|no|No|NO|on|On|ON|off|Off|OFF|y|Y|n|N)$")'),
  "enabled: yes\ncountry: NO\n", "enabled: true\ncountry: \"NO\"\n",
  "YAML 1.1 loaders (PyYAML, SnakeYAML 1.x, Go yaml.v2) turn yes/no/on/off into booleans while YAML 1.2 keeps strings; write true/false or quote.",
  sev="minor", cat="interoperability")
P("TRUTHY-CASE", "Boolean not written as lowercase true/false", YL, "Use this rule to forbid non-explicitly typed truthy values",
  '((boolean_scalar) @match (#not-match? @match "^(true|false)$"))', "debug: True\n", "debug: true\n",
  "Only lowercase true/false are portable booleans (yamllint truthy default allowed-values).", sev="info", cat="style")
P("IMPLICIT-OCTAL", "Number with a leading 0 (implicit octal)", YL, "Use forbid-implicit-octal to prevent numbers starting with 0",
  '((integer_scalar) @match (#match? @match "^[-+]?0[0-9]+$"))', "mode: 0644\nzip: 01234\n", "mode: \"0644\"\nzip: \"01234\"\n",
  "0644 is octal (420) in YAML 1.1 but decimal 644 in 1.2; quote it or use 0o644 explicitly.", sev="minor", cat="interoperability")
P("EXPLICIT-OCTAL", "0o octal literal (YAML 1.2 only)", YL, "Use forbid-explicit-octal to prevent numbers starting with 0o",
  '((integer_scalar) @match (#match? @match "^[-+]?0o[0-7]+$"))', "mode: 0o644\n", "mode: 420\n",
  "0o644 is an integer in YAML 1.2 but the string \"0o644\" for YAML 1.1 loaders.", sev="info", cat="interoperability")
P("FLOAT-NO-NUMERAL", "Float without a leading numeral (.5)", YL, "Use require-numeral-before-decimal to require floats to start with a numeral",
  '((float_scalar) @match (#match? @match "^[-+]?[.][0-9]"))', "ratio: .5\n", "ratio: 0.5\n", "Write 0.5 instead of .5.", sev="info", cat="style")
P("FLOAT-SCIENTIFIC", "Scientific notation float", YL, "Use forbid-scientific-notation to forbid scientific notation",
  '((float_scalar) @match (#match? @match "[eE][-+]?[0-9]"))', "limit: 1e3\n", "limit: 1000\n",
  "1e3 is a float in YAML 1.2 but a string in YAML 1.1 (which requires a dot); prefer plain numbers.", sev="info", cat="interoperability")
P("FLOAT-NAN", "NaN value", YL, "Use forbid-nan to forbid NaN (not a number) values", '((float_scalar) @match (#match? @match "^[.](nan|NaN|NAN)$"))',
  "x: .nan\n", "x: null\n", "NaN values are not representable in JSON and surprise consumers.", sev="info", cat="interoperability")
P("FLOAT-INF", "Infinite value", YL, "Use forbid-inf to forbid infinite values", '((float_scalar) @match (#match? @match "^[-+]?[.](inf|Inf|INF)$"))',
  "max: .inf\n", "max: 1000000\n", "Infinity is not representable in JSON.", sev="info", cat="interoperability")
P("VERSION-AS-FLOAT", "Version-like value parsed as a float (3.10 → 3.1)", SPEC, "Floating Point",
  '(block_mapping_pair key: (flow_node) @k value: (flow_node (plain_scalar (float_scalar) @match (#match? @match "^[0-9]+[.][0-9]*0$"))) (#match? @k "(?i)version|python|node|go|java|php|ruby|terraform"))',
  "python-version: 3.10\n", "python-version: \"3.10\"\n",
  "An unquoted 3.10 is the float 3.1; quote version numbers.", sev="major", cat="correctness", docv=SPECV)
P("VERSION-LIST-AS-FLOAT", "Version-like list item parsed as a float", SPEC, "Floating Point",
  '(block_mapping_pair key: (flow_node) @k value: [(flow_node (flow_sequence (flow_node (plain_scalar (float_scalar) @match)))) (block_node (block_sequence (block_sequence_item (flow_node (plain_scalar (float_scalar) @match)))))] (#match? @k "(?i)version|python|node|go|java|php|ruby") (#match? @match "^[0-9]+[.][0-9]*0$"))',
  "python: [3.9, 3.10]\n", "python: [\"3.9\", \"3.10\"]\n", "3.10 in a version matrix is the float 3.1; quote it.",
  sev="major", cat="correctness", docv=SPECV)
P("MERGE-KEY", "`<<` merge key (YAML 1.1 type, not in 1.2)", "https://yaml.org/type/merge.html", "Merge Key Language-Independent Type for YAML",
  '(block_mapping_pair key: (flow_node (plain_scalar (string_scalar) @match (#eq? @match "<<"))))', "base: &b {a: 1}\nx:\n  <<: *b\n  c: 2\n",
  "base: &b {a: 1}\nx:\n  a: 1\n  c: 2\n", "Merge keys are a YAML 1.1 extension; YAML 1.2 core-schema parsers treat `<<` as a plain key.",
  sev="info", cat="interoperability", docv="YAML 1.1 types")
P("UNDECLARED-ALIAS", "Alias references an undeclared anchor", YL, "Set forbid-undeclared-aliases to true to avoid aliases that reference an anchor",
  '(alias (alias_name) @match)', "a: *missing\n", "x: &missing 1\na: *missing\n", "The alias has no matching &anchor: loading fails.",
  sev="major", cat="correctness", filters=[r"file.count_lt:1:&{text}(\s|$)"])
P("DUPLICATE-ANCHOR", "Anchor name declared twice", YL, "Set forbid-duplicated-anchors to true to avoid duplications of a same anchor",
  '(anchor (anchor_name) @match)', "a: &x 1\nb: &x 2\nc: *x\n", "a: &x 1\nb: &y 2\nc: *x\n",
  "A reused anchor name silently rebinds later aliases.", sev="minor", cat="correctness", filters=[r"file.count_ge:2:&{text}(\s|$)"])
P("UNUSED-ANCHOR", "Anchor declared but never aliased", YL, "Set forbid-unused-anchors to true to avoid anchors being declared but not used",
  '(anchor (anchor_name) @match)', "a: &x 1\n", "a: &x 1\nb: *x\n", "Remove the unused anchor.", sev="info", cat="style",
  filters=[r"file.count_lt:1:\*{text}\b"])
P("ALIAS-BOMB", "Many aliases (possible billion-laughs expansion)", SPEC, "Anchors and Aliases",
  ROOT, "a: &a [x,x,x,x,x,x,x,x,x]\nb: &b [*a,*a,*a,*a,*a,*a,*a,*a,*a]\nc: &c [*b,*b,*b,*b,*b,*b,*b,*b,*b]\nd: &d [*c,*c,*c,*c,*c,*c,*c,*c,*c]\n",
  "a: &a [x]\nb: *a\n", "Nested alias fan-out can expand exponentially when loaded; cap alias expansion in the loader.",
  sev="major", kind="security", cat="security", docv=SPECV, mode="ai-confirm",
  ai="Do the aliases here form nested fan-out (aliases of collections that themselves alias collections) large enough to be an expansion bomb?",
  filters=[r"file.count_ge:25:\*[A-Za-z0-9_-]+"])
P("UNSAFE-TAG", "Language-specific constructor tag (!!python/, !ruby/, !!js/, !!java)", "https://pyyaml.org/wiki/PyYAMLDocumentation",
  "instances of Python classes can be constructed using the !!python/object tag",
  '((tag) @match (#match? @match "^!!?(python/|ruby/|js/|java|perl/|php/)"))', "cmd: !!python/object/apply:os.system [\"id\"]\n", "cmd: id\n",
  "Language tags make unsafe loaders instantiate arbitrary objects (remote code execution).", sev="critical", kind="security", cat="security",
  docv="PyYAML 6")
P("YAML11-DIRECTIVE", "%YAML 1.1 directive", SPEC, "A version 1.2 YAML processor must also accept documents with an explicit",
  ROOT, "%YAML 1.1\n---\na: 1\n", "%YAML 1.2\n---\na: 1\n", "The document pins YAML 1.1 semantics (yes/no booleans, implicit octal).",
  sev="info", kind="modernization", cat="interoperability", docv=SPECV, filters=[r"file.has_re:(?m)^%YAML 1\.1"])
P("EMPTY-VALUE", "Mapping key with empty (implicit null) value", YL, "Use forbid-in-block-mappings to prevent empty values in block mappings",
  '(block_mapping_pair key: (_) @match !value)', "name: app\nreplicas:\n", "name: app\nreplicas: null\n",
  "An empty value is an implicit null; write null or remove the key (often a forgotten value).", sev="minor", cat="correctness")
P("DOCUMENT-START", "Missing document start marker (---)", YL, "Use this rule to require or forbid the use of document start marker",
  '(stream . (document) @match)\n(stream . (comment)+ . (document) @match)', "a: 1\n", "---\na: 1\n", "yamllint requires `---` by default.", sev="info", cat="style",
  filters=[r"file.lacks_re:\A(\s*(#.*|%.*)?\n)*---"])
P("COMMENT-SPACE", "Comment without a space after #", YL, "Use require-starting-space to require a space character right after the",
  '((comment) @match (#match? @match "^#[^ #!@\\n]"))', "#TODO fix\na: 1\n", "# TODO fix\na: 1\n", "Put a space after #.", sev="info", cat="style")
P("BRACES-SPACES", "Spaces inside flow mapping braces", YL, "max-spaces-inside defines the maximal number of spaces allowed inside braces",
  '((flow_mapping) @match (#match? @match "^[{] |[^ ] [}]$"))', "a: { x: 1 }\n", "a: {x: 1}\n", "yamllint default: no spaces inside braces.",
  sev="info", cat="style")
P("BRACKETS-SPACES", "Spaces inside flow sequence brackets", YL, "max-spaces-inside defines the maximal number of spaces allowed inside braces",
  '((flow_sequence) @match (#match? @match "^\\\\[ |[^ ] \\\\]$"))', "a: [ 1, 2 ]\n", "a: [1, 2]\n", "yamllint default: no spaces inside brackets.",
  sev="info", cat="style")
P("COLON-SPACE-BEFORE", "Space before a mapping colon", YL, "max-spaces-before defines the maximal number of spaces allowed before colons",
  '((block_mapping_pair) @match (#match? @match "^[^:\\n\\"\']*[^ ] +:( |$)"))', "name : app\n", "name: app\n", "No space before `:`.",
  sev="info", cat="style")
P("COMMA-SPACE-BEFORE", "Space before a comma in a flow collection", YL, "Use this rule to control the number of spaces before and after commas",
  '([(flow_sequence) (flow_mapping)] @match (#match? @match "[^ ,] +,"))', "a: [1 , 2]\n", "a: [1, 2]\n", "No space before commas.",
  sev="info", cat="style")
P("TRAILING-SPACES", "Trailing whitespace", YL, "Use this rule to forbid trailing spaces at the end of lines",
  ROOT, "a: 1   \nb: 2\n", "a: 1\nb: 2\n", "Trailing spaces (they can change block-scalar content).", sev="info",
  cat="style", filters=[r"file.has_re:[ \t]+\r?\n"])
P("NO-FINAL-NEWLINE", "No newline at end of file", YL, "Use this rule to require a new line character", ROOT, "a: 1", "a: 1\n",
  "End the file with a newline (POSIX).", sev="info", cat="style", filters=[r"file.lacks_re:\n\z", r"file.has_re:\S"])
P("CRLF", "Windows (CRLF) line endings", YL, "Use this rule to force the type of new line characters", ROOT, "a: 1\r\nb: 2\r\n",
  "a: 1\nb: 2\n", "Use LF line endings (yamllint new-lines type: unix).", sev="info", cat="style", filters=[r"file.has_re:\r\n"])
P("LINE-LENGTH", "Line longer than 80 characters", YL, "Use this rule to set a limit to lines length", ROOT,
  "description: this line is deliberately written to be considerably longer than eighty characters in total\n",
  "description: >-\n  this line is wrapped\n  onto two lines\n", "yamllint default max line length is 80 (non-breakable words allowed).",
  sev="info", cat="style", filters=[r"file.has_re:(?m)^[^\n]*\S\s+\S[^\n]{80,}$"])
P("EMPTY-LINES", "More than two consecutive blank lines", YL, "Use this rule to set a maximal number of allowed consecutive blank lines",
  ROOT, "a: 1\n\n\n\nb: 2\n", "a: 1\n\nb: 2\n", "yamllint default allows at most 2 blank lines.", sev="info", cat="style",
  filters=[r"file.has_re:\n[ \t]*\n[ \t]*\n[ \t]*\n[^\n]"])
P("SECRET-FIELD", "Secret-looking key with a literal value", OWASP_SECRETS, OWASP_NEEDLE,
  f'(block_mapping_pair key: (flow_node) @k value: (flow_node [(plain_scalar (string_scalar) @match) (double_quote_scalar) @match (single_quote_scalar) @match]) (#match? @k "{SECRET_NAME_RE}") (#not-match? @match "{PLACEHOLDER_RE}"))',
  "password: S3cr3t!\n", "password: ${DB_PASSWORD}\n", "Key name suggests a credential and the value is a literal; confirm it is not a real secret.",
  sev="major", kind="security", cat="security", mode="ai-confirm",
  ai="Is this value a real credential (not a placeholder, variable reference, test fixture or documented example)?", docv="OWASP cheat sheet (2026)")
P("HTTP-URL", "Plain http:// endpoint", "https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html", "TLS",
  f'({STR} @match (#match? @match "^[\\"\']?http://"))', "api: http://api.example.com/v1\n", "api: https://api.example.com/v1\n",
  "Cleartext http:// endpoint in configuration; use https unless this is a local/dev URL or an identifier.", sev="minor", kind="security",
  cat="security", docv="OWASP cheat sheet (2026)", mode="ai-confirm",
  ai="Is this an actual network endpoint used at runtime over cleartext HTTP (not localhost, a namespace/identifier URI, or a schema id)?",
  filters=[r"node.lacks_re:http://(localhost|127\.|0\.0\.0\.0|\[::1\]|json-schema\.org|www\.w3\.org|schemas?\.|xmlns|[a-z0-9-]+(:[0-9]+)?/?[\"']?$)"])
secret_rules(P, STR, lambda k, v: f"{k}: {v}\n")

# Opinionated layout rules (yamllint's style set) only run when the project adopted the style:
# a yamllint config (or, for whitespace/line-length, an .editorconfig). Self-scan triage: long
# comment lines in a repo without yamllint were reported as findings nobody had agreed to.
EDITORCONFIG_TOO = {"YAML-LINE-LENGTH", "YAML-TRAILING-SPACES", "YAML-NO-FINAL-NEWLINE", "YAML-CRLF"}
for _r in P.R:
    if _r["category"] == "style":
        _r["detection"]["requires_config"] = ["yamllint", "editorconfig"] if _r["id"] in EDITORCONFIG_TOO else ["yamllint"]
# Project-configurable limit (was hand-added to the pack; kept here so regeneration preserves it).
for _r in P.R:
    if _r["id"] == "YAML-LINE-LENGTH":
        _r["title"] = "Line longer than ${max} characters"
        _r["detection"]["filters"] = ["node.is_root", r"file.has_re:(?m)^[^\n]*\S\s+\S[^\n]{${max},}$"]
        _r["message"] = ("Line longer than ${max} characters (yamllint line-length default is 80; non-breakable words allowed). "
                         "The limit follows the project's yamllint `line-length.max` or .editorconfig `max_line_length` when set.")
        _r["params"] = {"max": {"default": 80, "from": ["yamllint:line-length.max", "editorconfig:max_line_length.max"]}}
RULES = P.R

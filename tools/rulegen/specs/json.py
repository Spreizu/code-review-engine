"""Generic JSON pack: syntax (RFC 8259), interoperability (RFC 7493 I-JSON), secrets, JSON Schema drafts.
Base layer for package.json / composer.json / *.tfvars.json etc. (they also get these rules)."""
from specs._common import Pack

RFC = "https://www.rfc-editor.org/rfc/rfc8259"
IJ = "https://www.rfc-editor.org/rfc/rfc7493"
OWASP = "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html"
AWSK = "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html"
GHTOK = "https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github"
PROTO = "https://cheatsheetseries.owasp.org/cheatsheets/Prototype_Pollution_Prevention_Cheat_Sheet.html"
JS = "https://json-schema.org/understanding-json-schema/"
JSONC = ["!**/tsconfig*.json", "!**/jsconfig*.json", "!**/.vscode/**", "!**/devcontainer.json", "!**/.devcontainer/**",
         "!**/*.jsonc", "!**/.eslintrc.json", "!**/.babelrc", "!**/turbo.json", "!**/deno.json", "!**/biome.json", "!**/.swcrc"]
ANY = {"any": "*"}
P = Pack("JSON", "json", "RFC 8259 (2017)", ANY)

def sec(id, title, url, needle, regex, bad, good, msg, sev="critical", **kw):
    P(id, title, url, needle, f'((string_content) @match (#match? @match "{regex}"))', bad, good, msg, sev=sev, kind="security",
      cat="security", **kw)

# --- syntax / RFC 8259 ----------------------------------------------------------------------------------------------
P("DUPLICATE-KEY", "Duplicate object member name", RFC, "The names within an object SHOULD be unique.",
  '(object (pair key: (string) @match))',
  '{"name": "a", "port": 80, "name": "b"}', '{"name": "a", "port": 80}',
  "Duplicate key in the same object: parsers disagree on which value wins (last, first, or error).", sev="major",
  kind="anti-pattern", cat="correctness",
  # the pair-pair query was quadratic inside tree-sitter (30 s on one 134 KB i18n file)
  filters=["node.dup_sibling_key"], fp=[{"note": "same key in sibling objects", "code": '{"a": {"id": 1}, "b": {"id": 2}}'}])
P("TRAILING-COMMA", "Trailing comma is not valid JSON", RFC, "value-separator = ws %x2C ws ; , comma",
  '((ERROR) @match (#eq? @match ","))', '{"a": 1, "b": 2,}', '{"a": 1, "b": 2}',
  "Trailing commas are not part of the JSON grammar; strict parsers (JSON.parse, encoding/json, json.loads) reject the file.",
  sev="major", cat="correctness", files=JSONC)
P("SYNTAX-ERROR", "JSON syntax error", RFC, "A JSON text is a sequence of tokens.",
  '((ERROR) @match (#not-eq? @match ","))', "{'a': 1}", '{"a": 1}',
  "The file does not parse as RFC 8259 JSON (single quotes, unquoted keys, missing commas or brackets?).",
  sev="major", cat="correctness", files=JSONC)
P("COMMENT", "Comments are not valid JSON", RFC, "Insignificant whitespace is allowed before or after any of the six structural characters.",
  '(comment) @match', '// port\n{"port": 80}', '{"port": 80}',
  "Comments are not allowed in JSON (only insignificant whitespace is). Use JSONC/JSON5 tooling explicitly or move the note to documentation.",
  sev="major", cat="correctness", files=JSONC)
P("NAN-INFINITY", "NaN / Infinity are not JSON numbers", RFC, "Numeric values that cannot be represented in the grammar below (such as Infinity and NaN) are not permitted.",
  '(document) @match', '{"ratio": NaN}', '{"ratio": null}',
  "NaN/Infinity are not permitted in JSON; use null or a string sentinel.", sev="major", cat="correctness",
  filters=[r"file.has_re:[:\[,]\s*-?(NaN|Infinity)\s*[,}\]]"])
P("LEADING-ZERO", "Number with a leading zero", RFC, "Leading zeros are not allowed.",
  '(document) @match', '{"mode": 0755}', '{"mode": 493}',
  "Leading zeros are not allowed in JSON numbers (and are not octal).", sev="major", cat="correctness",
  filters=[r"file.has_re:[:\[,]\s*-?0[0-9]+\s*[,}\]]"])
P("NON-DECIMAL-NUMBER", "Hex/octal/binary literal in JSON", RFC, "A number is represented in base 10 using decimal digits.",
  '(document) @match', '{"mask": 0xFF}', '{"mask": 255}',
  "JSON numbers are base-10 only.", sev="major", cat="correctness",
  filters=[r"file.has_re:[:\[,]\s*-?0[xXoObB][0-9a-fA-F_]+\s*[,}\]]"])
P("UNSAFE-INTEGER", "Integer outside the interoperable IEEE-754 range", RFC, "are interoperable in the sense that implementations will agree exactly on their numeric values",
  r'((number) @match (#match? @match "^-?[0-9]{16,}$"))', '{"id": 9007199254740993}', '{"id": "9007199254740993"}',
  "Integers beyond ±(2^53-1) silently lose precision in JavaScript and many other parsers; send large IDs as strings.",
  sev="minor", cat="interoperability")
P("EXCESS-PRECISION", "Decimal with more precision than binary64 can hold", RFC, "IEEE 754 binary64 (double precision) numbers",
  r'((number) @match (#match? @match "[.][0-9]{17,}"))', '{"price": 0.123456789012345678901}', '{"price": "0.123456789012345678901"}',
  "More than ~17 significant digits cannot survive a round-trip through binary64; use a string (or a decimal type) for exact values.",
  sev="minor", cat="interoperability")
P("BOM", "Byte order mark at start of JSON text", RFC, "Implementations MUST NOT add a byte order mark (U+FEFF) to the beginning of a networked-transmitted JSON text.",
  '(document) @match', '\ufeff{"a": 1}', '{"a": 1}', "Remove the UTF-8 BOM; many JSON parsers reject it.",
  sev="minor", cat="interoperability", filters=["file.has_re:^\ufeff"])
P("CONTROL-CHAR", "Unescaped control character inside a string", RFC, "the control characters (U+0000 through U+001F)",
  r'((string_content) @match (#match? @match "[\\x00-\\x08\\x0B\\x0C\\x0E-\\x1F\\t]"))', '{"a": "x\ty"}', '{"a": "x\\ty"}',
  "Control characters (including TAB) must be escaped inside JSON strings.", sev="major", cat="correctness")
P("NOT-UTF8-ESCAPE", "Invalid escape sequence in string", RFC, "The representation of strings is similar to conventions used in the C family of programming languages.",
  '((ERROR) @match (#match? @match "^.[^\\"/bfnrtu\\\\\\\\]"))', r'{"path": "C:\dir"}', r'{"path": "C:\\dir"}',
  "Only \\\" \\\\ \\/ \\b \\f \\n \\r \\t and \\uXXXX escapes exist in JSON.", sev="major", cat="correctness", files=JSONC)
# --- I-JSON (RFC 7493) ---------------------------------------------------------------------------------------------------
P("LONE-SURROGATE", "Unpaired UTF-16 surrogate escape", IJ, "MUST NOT include code points that identify Surrogates or Noncharacters",
  '((string (escape_sequence)) @match)', r'{"s": "\uD800x"}', r'{"s": "\uD83D\uDE00"}',
  "A high surrogate escape must be followed by a low surrogate; lone surrogates are rejected by I-JSON and corrupt UTF-8 output.",
  sev="minor", cat="interoperability", docv="RFC 7493 (I-JSON)", filters=[r"node.has_re:\\u[dD][89abAB][0-9a-fA-F]{2}", r"node.lacks_re:\\u[dD][89abAB][0-9a-fA-F]{2}\\u[dD][c-fC-F]"])
P("TOP-LEVEL-SCALAR", "Top-level value is not an object or array", IJ, "protocol designers SHOULD NOT use top-level JSON texts that are neither objects nor arrays",
  '(document [(string) (number) (true) (false) (null)] @match)', '"ok"', '{"status": "ok"}',
  "Prefer an object (or array) at the top level so the format can evolve without breaking clients.",
  sev="info", kind="best-practice", cat="interoperability", docv="RFC 7493 (I-JSON)")
P("NON-ISO-DATE", "Date not in RFC 3339 / ISO 8601 format", IJ, "expressed as string values in ISO 8601 format",
  r'((string_content) @match (#match? @match "^[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}( |$)|^[0-9]{1,2}-[0-9]{1,2}-(19|20)[0-9]{2}( |$)|^[0-9]{1,2}[.][0-9]{1,2}[.](19|20)[0-9]{2}( |$)"))', '{"created": "12/31/2025"}',
  '{"created": "2025-12-31T00:00:00Z"}', "Use RFC 3339 timestamps (e.g. 2025-12-31T00:00:00Z); locale formats are ambiguous.",
  sev="info", kind="best-practice", cat="interoperability", docv="RFC 7493 (I-JSON)")
P("PROTO-KEY", "__proto__ / constructor.prototype key in JSON data", PROTO, "__proto__",
  r'(pair key: (string (string_content) @match (#match? @match "^(__proto__|prototype|constructor)$")))',
  '{"__proto__": {"isAdmin": true}}', '{"profile": {"isAdmin": false}}',
  "Keys like __proto__/constructor in data enable prototype pollution when merged into JS objects; reject or sanitise them.",
  sev="major", kind="security", cat="security", docv="OWASP cheat sheet (2026)")
# --- secrets -------------------------------------------------------------------------------------------------------------
sec("AWS-ACCESS-KEY", "AWS access key ID committed", AWSK, "AKIAIOSFODNN7EXAMPLE", "^(AKIA|ASIA)[0-9A-Z]{16}$",
    '{"aws_access_key_id": "AKIAIOSFODNN7EXAMPLE"}', '{"aws_profile": "deploy"}',
    "Long-term AWS access key in a JSON file: rotate it and load credentials from the environment/role instead.", docv="AWS IAM User Guide")
sec("PRIVATE-KEY", "PEM private key embedded in JSON", OWASP, "Many organizations have them hardcoded within the source code in plaintext", "-----BEGIN ([A-Z]+ )?PRIVATE KEY-----",
    '{"key": "-----BEGIN RSA PRIVATE KEY-----\\nMIIE..."}', '{"key_file": "/run/secrets/tls.key"}',
    "Private key material committed to the repository: revoke it and mount it from a secret store.", docv="OWASP cheat sheet (2026)")
sec("GITHUB-TOKEN", "GitHub token committed", GHTOK, "ghp_", "^(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})$",
    '{"token": "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"}', '{"token_env": "GITHUB_TOKEN"}',
    "GitHub token (ghp_/gho_/ghu_/ghs_/ghr_/github_pat_) committed: revoke it and use an environment variable/secret.", docv="GitHub Docs")
sec("SLACK-TOKEN", "Slack token committed", "https://docs.slack.dev/authentication/tokens/", "xoxb-", "^xox[abposr]-[0-9A-Za-z-]{10,}",
    '{"slack": "xoxb-1234567890-abcdefghij"}', '{"slack_env": "SLACK_BOT_TOKEN"}', "Slack token committed: revoke and move to a secret store.",
    docv="Slack developer docs")
sec("STRIPE-LIVE-KEY", "Stripe live secret key committed", "https://docs.stripe.com/keys", "for secret keys", "^(sk|rk)_live_[0-9A-Za-z]{10,}",
    '{"stripe": "sk_live_51HxxxxxxxxxxxxxxxXX"}', '{"stripe": "pk_live_51Hxxxxxxxxxxxxxxx"}', "Stripe live secret/restricted key committed: roll it in the dashboard.",
    docv="Stripe docs")
sec("JWT-LITERAL", "Hard-coded JSON Web Token", OWASP, "Many organizations have them hardcoded within the source code in plaintext", "^eyJ[A-Za-z0-9_-]{10,}[.]eyJ[A-Za-z0-9_-]{10,}[.][A-Za-z0-9_-]+$",
    '{"auth": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123"}', '{"auth": "${AUTH_TOKEN}"}',
    "A bearer token is committed; tokens grant access until they expire.", sev="major", docv="OWASP cheat sheet (2026)")
sec("URL-CREDENTIALS", "Credentials embedded in a URL", OWASP, "Many organizations have them hardcoded within the source code in plaintext", "^[a-zA-Z][a-zA-Z0-9+.-]*://[^/:@ ]+:[^@/ ${}<>]+@",
    '{"db": "postgres://admin:hunter2@db:5432/app"}', '{"db": "postgres://db:5432/app"}',
    "user:password@ in a connection URL is a committed secret; inject the password separately.", sev="major", docv="OWASP cheat sheet (2026)")
sec("AZURE-STORAGE-KEY", "Azure storage account key in connection string", "https://learn.microsoft.com/en-us/azure/storage/common/storage-configure-connection-string",
    "AccountKey", "AccountKey=[A-Za-z0-9+/=]{20,}", '{"conn": "DefaultEndpointsProtocol=https;AccountName=x;AccountKey=abcdefghijklmnopqrstuvwxyz0123=="}',
    '{"conn_env": "AZURE_STORAGE_CONNECTION_STRING"}', "Storage account key committed; prefer Microsoft Entra ID / managed identity or a Key Vault reference.",
    docv="Azure Storage docs")
P("GCP-SERVICE-ACCOUNT-KEY", "Google Cloud service account key file committed", "https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys",
  "Service account keys", '((object (pair key: (string (string_content) @k) value: (string (string_content) @v))) @match (#eq? @k "type") (#eq? @v "service_account"))',
  '{"type": "service_account", "private_key_id": "1", "private_key": "-----BEGIN PRIVATE KEY-----\\n..."}', '{"type": "external_account"}',
  "A service account key JSON is in the repo; delete/rotate the key and use workload identity federation or ADC.",
  sev="critical", kind="security", cat="security", docv="Google Cloud IAM docs", filters=["node.has_re:\"private_key\""])
P("SECRET-FIELD", "Secret-looking field with a literal value", OWASP, "Many organizations have them hardcoded within the source code in plaintext",
  r'(pair key: (string (string_content) @k (#match? @k "(?i)^(password|passwd|pwd|secret|client_secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|private[_-]?key|secret[_-]?key)$")) value: (string (string_content) @match (#not-match? @match "^(\\$\\{|<|%|\\{\\{|\\*+$|changeme$|xxx+$|example)")))',
  '{"password": "S3cr3t!"}', '{"password": "${DB_PASSWORD}"}',
  "Field name suggests a credential and the value is a literal; confirm it is not a real secret.", sev="major", kind="security",
  cat="security", mode="ai-confirm", ai="Is this value a real credential (not a placeholder, test fixture, or documented example)? Answer from the snippet.",
  docv="OWASP cheat sheet (2026)")
P("HTTP-URL", "Plain http:// endpoint", "https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html", "TLS",
  r'((string_content) @match (#match? @match "^http://"))', '{"api": "http://api.example.com/v1"}', '{"api": "https://api.example.com/v1"}',
  "Cleartext http:// endpoint in configuration; use https unless this is a local/dev URL or an identifier.", sev="minor", kind="security",
  cat="security", docv="OWASP cheat sheet (2026)", mode="ai-confirm",
  ai="Is this an actual network endpoint used at runtime over cleartext HTTP (not localhost, a namespace/identifier URI, or a schema $id)?",
  filters=[r"node.lacks_re:^http://(localhost|127\.|0\.0\.0\.0|\[::1\]|json-schema\.org|www\.w3\.org|schemas?\.|xmlns)"])
# --- JSON Schema drafts -------------------------------------------------------------------------------------------------
SD = JS + "structuring"
P("SCHEMA-OLD-DRAFT", "JSON Schema uses a pre-2019 draft", JS + "reference/schema", "$schema",
  r'(pair key: (string (string_content) @k (#eq? @k "$schema")) value: (string (string_content) @match (#match? @match "draft-0[3-7]")))',
  '{"$schema": "http://json-schema.org/draft-04/schema#"}', '{"$schema": "https://json-schema.org/draft/2020-12/schema"}',
  "Schema targets draft-04..07; 2020-12 is current (prefixItems, $defs, unevaluatedProperties).", sev="info", kind="modernization",
  cat="json-schema", docv="JSON Schema 2020-12")
P("SCHEMA-DEFINITIONS", "`definitions` instead of `$defs`", SD, "$defs",
  '(pair key: (string (string_content) @match (#eq? @match "definitions")))', '{"$schema": "https://json-schema.org/draft/2020-12/schema", "definitions": {}}',
  '{"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": {}}', "Since 2019-09 the keyword is $defs; `definitions` is legacy.",
  sev="minor", kind="migration", cat="json-schema", docv="JSON Schema 2020-12", filters=[r"file.has_re:json-schema\.org/draft/20(19-09|20-12)"])
P("SCHEMA-ID-NO-DOLLAR", "Draft-4 `id` keyword in a newer schema", SD, "$id",
  '(pair key: (string (string_content) @match (#eq? @match "id")) value: (string))', '{"$schema": "http://json-schema.org/draft-07/schema#", "id": "http://x/y.json"}',
  '{"$schema": "http://json-schema.org/draft-07/schema#", "$id": "http://x/y.json"}', "Draft 6+ uses $id; `id` is treated as an unknown keyword.",
  sev="minor", kind="migration", cat="json-schema", docv="JSON Schema 2020-12", filters=[r"file.has_re:json-schema\.org/(draft-0[67]|draft/20)"])
P("SCHEMA-DEPENDENCIES", "`dependencies` split into dependentRequired/dependentSchemas", JS + "reference/conditionals", "dependentRequired",
  '(pair key: (string (string_content) @match (#eq? @match "dependencies")) value: (object))', '{"$schema": "https://json-schema.org/draft/2020-12/schema", "dependencies": {"a": ["b"]}}',
  '{"$schema": "https://json-schema.org/draft/2020-12/schema", "dependentRequired": {"a": ["b"]}}', "2019-09 replaced `dependencies` with dependentRequired / dependentSchemas.",
  sev="minor", kind="migration", cat="json-schema", docv="JSON Schema 2020-12", filters=[r"file.has_re:json-schema\.org/draft/20(19-09|20-12)"])
P("SCHEMA-ITEMS-ARRAY", "Tuple `items: [...]` in a 2020-12 schema", JS + "reference/array", "prefixItems",
  '(pair key: (string (string_content) @match (#eq? @match "items")) value: (array))', '{"$schema": "https://json-schema.org/draft/2020-12/schema", "items": [{"type": "string"}]}',
  '{"$schema": "https://json-schema.org/draft/2020-12/schema", "prefixItems": [{"type": "string"}]}', "In 2020-12 tuple validation uses prefixItems; array-form items is invalid.",
  sev="major", kind="migration", cat="json-schema", docv="JSON Schema 2020-12", filters=[r"file.has_re:json-schema\.org/draft/2020-12"])
P("SCHEMA-ADDITIONAL-ITEMS", "`additionalItems` in a 2020-12 schema", JS + "reference/array", "additionalItems",
  '(pair key: (string (string_content) @match (#eq? @match "additionalItems")))', '{"$schema": "https://json-schema.org/draft/2020-12/schema", "additionalItems": false}',
  '{"$schema": "https://json-schema.org/draft/2020-12/schema", "items": false}', "2020-12 removed additionalItems; use `items` after prefixItems.",
  sev="major", kind="removal", cat="json-schema", docv="JSON Schema 2020-12", filters=[r"file.has_re:json-schema\.org/draft/2020-12"])
P("SCHEMA-BOOLEAN-EXCLUSIVE", "Boolean exclusiveMinimum/Maximum (draft-4 style)", JS + "reference/numeric", "exclusiveMinimum",
  '(pair key: (string (string_content) @match (#match? @match "^exclusive(Minimum|Maximum)$")) value: [(true) (false)])',
  '{"minimum": 0, "exclusiveMinimum": true}', '{"exclusiveMinimum": 0}', "Since draft 6 exclusiveMinimum/Maximum take numbers; booleans are draft-4 only.",
  sev="minor", kind="migration", cat="json-schema", docv="JSON Schema 2020-12", filters=[r"file.lacks_re:draft-0[34]"])
P("SCHEMA-REF-SIBLINGS", "Keywords next to $ref are ignored (draft ≤ 7)", SD, "$ref",
  '(object (pair key: (string (string_content) @r (#eq? @r "$ref"))) (pair key: (string (string_content) @match (#not-match? @match "^[$](ref|id|comment|schema)$|^(title|description)$"))))',
  '{"$schema": "http://json-schema.org/draft-07/schema#", "properties": {"a": {"$ref": "#/definitions/x", "minLength": 2}}}',
  '{"$schema": "http://json-schema.org/draft-07/schema#", "properties": {"a": {"allOf": [{"$ref": "#/definitions/x"}, {"minLength": 2}]}}}',
  "In draft 4-7 an object with $ref is only a reference; sibling keywords are ignored. Wrap in allOf or move to 2019-09+.",
  sev="major", kind="anti-pattern", cat="json-schema", docv="JSON Schema 2020-12", filters=[r"file.has_re:draft-0[4-7]"])
P("SCHEMA-MISSING-SCHEMA", "JSON Schema document without $schema", JS + "reference/schema", "$schema",
  '(document (object (pair key: (string (string_content) @k (#match? @k "^(properties|\\$defs|definitions)$")))) @match)',
  '{"type": "object", "properties": {"a": {"type": "string"}}}', '{"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "properties": {}}',
  "Declare $schema so validators apply the intended draft.", sev="info", kind="best-practice", cat="json-schema", docv="JSON Schema 2020-12",
  files=["**/*.schema.json", "**/schemas/**/*.json", "**/schema/**/*.json"], filters=['node.lacks_re:"\\$schema"'])
RULES = P.R

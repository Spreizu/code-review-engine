"""Protobuf pack (proto grammar, vendored). Syntax-aware: rules are gated per file on `syntax = "proto2"`,
`syntax = "proto3"` or `edition = "2023"/"2024"` via file-level regex filters (the dialect is a per-file property,
not a project version). Sources: protobuf.dev language guides, style guide, dos & don'ts, editions overview/features,
Go generated-code reference, and Buf lint rules."""
from specs._common import Pack

PB = "https://protobuf.dev/"
STYLE, DD = PB + "programming-guides/style/", PB + "best-practices/dos-donts/"
P3G, P2G = PB + "programming-guides/proto3/", PB + "programming-guides/proto2/"
EDO, EDF = PB + "editions/overview/", PB + "editions/features/"
BUF = "https://buf.build/docs/lint/rules/"
P = Pack("PROTO", "proto", "Protobuf 33 / Editions 2024", {"any": "*"}, files=["**/*.proto"])

H3 = 'syntax = "proto3";\n\npackage acme.user.v1;\n\n{}'
H2 = 'syntax = "proto2";\n\npackage acme.user.v1;\n\n{}'
E23 = 'edition = "2023";\n\npackage acme.user.v1;\n\n{}'
E24 = 'edition = "2024";\n\npackage acme.user.v1;\n\n{}'
F3 = r'file.has_re:(?m)^\s*syntax\s*=\s*"proto3"'
F2 = r'file.has_re:(?m)^\s*syntax\s*=\s*"proto2"'
FED = r'file.has_re:(?m)^\s*edition\s*=\s*"'
FE24 = r'file.has_re:(?m)^\s*edition\s*=\s*"20(2[4-9]|[3-9][0-9])"'
FE23 = r'file.has_re:(?m)^\s*edition\s*=\s*"2023"'
M = lambda body: "message User {\n" + body + "}\n"


def named(node, rx, field=None):
    return f'(({node} (identifier) @match) (#not-match? @match "{rx}"))'


# ------------------------------------------------------------------ naming / style
P("MESSAGE-TITLECASE", "Message name not TitleCase", STYLE, "TitleCase for message names.",
  '((message_name (identifier) @match) (#not-match? @match "^[A-Z][A-Za-z0-9]*$"))',
  H3.format("message user_profile {\n  string name = 1;\n}\n"), H3.format("message UserProfile {\n  string name = 1;\n}\n"),
  "Use TitleCase message names; generated code maps them to class names.", sev="info", kind="best-practice", cat="style")
P("FIELD-SNAKE-CASE", "Field name not lower_snake_case", STYLE, "Use snake_case for field names, including extensions.",
  '((field (identifier) @match) (#not-match? @match "^[a-z][a-z0-9_]*$"))\n((map_field (identifier) @match) (#not-match? @match "^[a-z][a-z0-9_]*$"))\n'
  '((oneof_field (identifier) @match) (#not-match? @match "^[a-z][a-z0-9_]*$"))',
  H3.format(M("  string userName = 1;\n")), H3.format(M("  string user_name = 1;\n")),
  "Use lower_snake_case field names; protoc derives camelCase JSON/accessor names from them.", sev="info", kind="best-practice", cat="style")
P("ONEOF-SNAKE-CASE", "Oneof name not lower_snake_case", STYLE, "Use lower_snake_case for oneof names.",
  '((oneof (identifier) @match) (#not-match? @match "^[a-z][a-z0-9_]*$"))',
  H3.format(M("  oneof SongId {\n    string hrid = 1;\n    int64 mid = 2;\n  }\n")), H3.format(M("  oneof song_id {\n    string hrid = 1;\n    int64 mid = 2;\n  }\n")),
  "Use lower_snake_case oneof names.", sev="info", kind="best-practice", cat="style")
P("ENUM-TITLECASE", "Enum name not TitleCase", STYLE, "Use TitleCase for enum type names",
  '((enum_name (identifier) @match) (#not-match? @match "^[A-Z][A-Za-z0-9]*$"))',
  H3.format("enum song_kind {\n  SONG_KIND_UNSPECIFIED = 0;\n}\n"), H3.format("enum SongKind {\n  SONG_KIND_UNSPECIFIED = 0;\n}\n"),
  "Use TitleCase enum type names.", sev="info", kind="best-practice", cat="style")
P("ENUM-VALUE-UPPER-SNAKE", "Enum value not UPPER_SNAKE_CASE", STYLE, "UPPER_SNAKE_CASE for enum value names",
  '((enum_field (identifier) @match) (#not-match? @match "^[A-Z][A-Z0-9_]*$"))',
  H3.format("enum SongKind {\n  SONG_KIND_UNSPECIFIED = 0;\n  songKindPop = 1;\n}\n"), H3.format("enum SongKind {\n  SONG_KIND_UNSPECIFIED = 0;\n  SONG_KIND_POP = 1;\n}\n"),
  "Use UPPER_SNAKE_CASE enum values (they share the enclosing scope, C++-style).", sev="info", kind="best-practice", cat="style")
P("ENUM-ZERO-VALUE-SUFFIX", "Enum zero value lacks _UNSPECIFIED/_UNKNOWN", STYLE,
  "The first listed value should be a zero value enum and have the suffix of either _UNSPECIFIED or _UNKNOWN .",
  '((enum_field (identifier) @match (int_lit) @v) (#eq? @v "0") (#not-match? @match "_(UNSPECIFIED|UNKNOWN)$"))',
  H3.format("enum Status {\n  ACTIVE = 0;\n  DISABLED = 1;\n}\n"), H3.format("enum Status {\n  STATUS_UNSPECIFIED = 0;\n  STATUS_ACTIVE = 1;\n}\n"),
  "A meaningful zero value is what unset/unknown values decode to; reserve 0 for STATUS_UNSPECIFIED.", sev="minor", kind="best-practice", cat="correctness",
  xref=[DD])
P("ENUM-FIRST-VALUE-NOT-ZERO", "proto3 enum first value is not 0", P3G,
  "There must be a zero value, so that we can use 0 as a numeric default value . The zero value needs to be the first element",
  '((enum_body . (enum_field (int_lit) @v) @match) (#not-eq? @v "0"))',
  H3.format("enum Status {\n  STATUS_ACTIVE = 1;\n}\n"), H3.format("enum Status {\n  STATUS_UNSPECIFIED = 0;\n  STATUS_ACTIVE = 1;\n}\n"),
  "protoc rejects proto3 enums whose first value is not zero.", sev="major", kind="anti-pattern", cat="correctness", filters=[F3])
P("SERVICE-TITLECASE", "Service/RPC name not TitleCase", STYLE, "TitleCase for service names and method names.",
  '((service_name (identifier) @match) (#not-match? @match "^[A-Z][A-Za-z0-9]*$"))\n((rpc_name (identifier) @match) (#not-match? @match "^[A-Z][A-Za-z0-9]*$"))',
  H3.format("service UserService {\n  rpc get_user(GetUserRequest) returns (GetUserResponse);\n}\n"),
  H3.format("service UserService {\n  rpc GetUser(GetUserRequest) returns (GetUserResponse);\n}\n"),
  "Use TitleCase service and method names.", sev="info", kind="best-practice", cat="style")
P("SERVICE-SUFFIX", "Service name lacks Service suffix", BUF, "Service names must end in Service",
  '((service_name (identifier) @match) (#not-match? @match "Service$"))',
  H3.format("service Users {\n  rpc GetUser(GetUserRequest) returns (GetUserResponse);\n}\n"),
  H3.format("service UserService {\n  rpc GetUser(GetUserRequest) returns (GetUserResponse);\n}\n"),
  "Suffix services with Service (Buf STANDARD lint).", sev="info", kind="best-practice", cat="style", docv="Buf CLI v1.5x")
P("RPC-STANDARD-MESSAGE-NAMES", "RPC request/response not a dedicated <Rpc>Request/<Rpc>Response", BUF,
  "These three rules together enforce that every RPC has a uniquely named request and response message.",
  '((rpc (message_or_enum_type) @match) (#not-match? @match "(Request|Response)$"))',
  H3.format("import \"google/protobuf/empty.proto\";\n\nservice UserService {\n  rpc GetUser(User) returns (google.protobuf.Empty);\n}\n"),
  H3.format("service UserService {\n  rpc GetUser(GetUserRequest) returns (GetUserResponse);\n}\n"),
  "Shared/domain or Empty messages as RPC I/O can't evolve per-method; give every RPC its own Request/Response.",
  sev="minor", kind="best-practice", cat="maintainability", docv="Buf CLI v1.5x", xref=[DD])
P("PACKAGE-DEFINED", "File declares no package", BUF, "Every file must declare a package.",
  '(source_file [(syntax) (edition)] @match)',
  'syntax = "proto3";\n\nmessage User {\n  string name = 1;\n}\n', H3.format(M("  string name = 1;\n")),
  "Without a package all types live in the global namespace and collide across modules.", sev="minor", kind="best-practice", cat="maintainability",
  filters=[r"file.lacks_re:(?m)^\s*package\s"], docv="Buf CLI v1.5x")
P("SYNTAX-SPECIFIED", "No syntax/edition declaration", BUF, "Every file must declare a syntax.",
  '(source_file . (_) @match)',
  'package acme.user.v1;\n\nmessage User {\n  string name = 1;\n}\n', H3.format(M("  string name = 1;\n")),
  "Files without syntax silently default to proto2 semantics (and protoc warns); declare syntax or edition.", sev="minor", kind="anti-pattern", cat="correctness",
  filters=[r"file.lacks_re:(?m)^\s*(syntax|edition)\s*="], docv="Buf CLI v1.5x")
P("PACKAGE-LOWERCASE", "Package name not lower_snake/dot.delimited", STYLE, "package names may be lower_snake_case or dot.delimited",
  '((package (full_ident) @match) (#not-match? @match "^[a-z][a-z0-9_]*(\\\\.[a-z][a-z0-9_]*)*$"))',
  'syntax = "proto3";\n\npackage Acme.UserService.v1;\n', 'syntax = "proto3";\n\npackage acme.user_service.v1;\n',
  "Use lowercase package names; generators map them to namespaces/directories.", sev="info", kind="best-practice", cat="style")
P("PACKAGE-VERSION-SUFFIX", "Package lacks a version suffix (v1, v1beta1, ...)", BUF, "The last component of a package must be a version of the form",
  '((package (full_ident) @match) (#not-match? @match "\\\\.v[1-9][0-9]*((alpha|beta)[0-9]*|test.*|p[1-9][0-9]*(alpha|beta)[0-9]*)?$"))',
  'syntax = "proto3";\n\npackage acme.user;\n', 'syntax = "proto3";\n\npackage acme.user.v1;\n',
  "Versioned packages let you ship breaking schema changes side-by-side (v2) instead of in place.", sev="info", kind="best-practice", cat="maintainability",
  docv="Buf CLI v1.5x")
P("IMPORT-PUBLIC", "import public", BUF, "Tip of the week #5: Avoid import public/weak",
  '((import) @match (#match? @match "^import\\\\s+public\\\\b"))',
  H3.format('import public "acme/common/v1/money.proto";\n'), H3.format('import "acme/common/v1/money.proto";\n'),
  "import public re-exports another file's symbols, which many generators (Go, Bazel) don't support well; import directly.",
  sev="minor", kind="best-practice", cat="maintainability", docv="Buf CLI v1.5x")
P("IMPORT-WEAK", "import weak (unsupported)", BUF, "protobuf-go no longer supports weak imports",
  '((import) @match (#match? @match "^import\\\\s+weak\\\\b"))',
  H2.format('import weak "acme/ext/v1/ext.proto";\n'), H2.format('import "acme/ext/v1/ext.proto";\n'),
  "Weak imports are an internal/legacy feature dropped by protobuf-go; use a normal import.", sev="minor", kind="deprecation", cat="compatibility",
  docv="Buf CLI v1.5x")
P("REPEATED-FIELD-PLURAL", "Repeated field name not pluralized", STYLE, "Use pluralized names for repeated fields.",
  '((field (identifier) @match) @f (#match? @f "^repeated\\\\s") (#not-match? @match "(s|data|info|metadata|people|children|history)$"))',
  H3.format(M("  repeated string tag = 1;\n")), H3.format(M("  repeated string tags = 1;\n")),
  "Pluralize repeated fields so accessors read naturally (tags, not tag).", sev="info", kind="best-practice", cat="style",
  mode="ai-confirm", ai="Is this name a singular noun (not already a plural/mass noun like 'data', 'criteria', 'feedback')?")
P("FIELD-LANGUAGE-KEYWORD", "Field named after a language keyword", DD,
  "keywords in your file paths, as this can also cause problems.",
  '((field (identifier) @match) (#match? @match "^(abstract|assert|async|await|break|case|catch|class|const|continue|def|default|del|delete|do|elif|else|enum|except|export|extends|final|finally|for|from|func|function|global|goto|if|implements|import|in|instanceof|interface|is|lambda|new|nil|not|null|or|package|pass|private|protected|public|raise|return|static|switch|this|throw|try|typeof|var|void|volatile|while|with|yield)$"))',
  H3.format(M("  string class = 1;\n")), H3.format(M("  string class_name = 1;\n")),
  "Keyword field names get mangled (class_, Class_) differently per generator; choose a non-keyword name.", sev="minor", kind="best-practice", cat="compatibility")
P("ENUM-MACRO-CONSTANT", "Enum value collides with a C/C++ macro", DD, "macro constants such as “ NULL ,” “ NAN ,” and “ DOMAIN ” as enum values.",
  '((enum_field (identifier) @match) (#match? @match "^(NULL|NAN|DOMAIN|TRUE|FALSE|EOF|DEBUG|ERROR|INFINITY|BIG_ENDIAN|LITTLE_ENDIAN|linux|unix|major|minor|EINVAL|ENOENT)$"))',
  H3.format("enum Value {\n  VALUE_UNSPECIFIED = 0;\n  NULL = 1;\n}\n"), H3.format("enum Value {\n  VALUE_UNSPECIFIED = 0;\n  VALUE_NULL = 1;\n}\n"),
  "System headers #define these names, breaking generated C++; prefix values with the enum name.", sev="minor", kind="best-practice", cat="compatibility")
P("ENUM-ALLOW-ALIAS", "Enum allow_alias", BUF, "Forbids aliased enums",
  '((option (identifier) @n (constant) @v) @match (#eq? @n "allow_alias") (#eq? @v "true"))',
  H3.format("enum Status {\n  option allow_alias = true;\n  STATUS_UNSPECIFIED = 0;\n  STATUS_ON = 1;\n  STATUS_ENABLED = 1;\n}\n"),
  H3.format("enum Status {\n  STATUS_UNSPECIFIED = 0;\n  STATUS_ON = 1;\n}\n"),
  "Only the first alias survives deserialization and JSON/text output is ambiguous; avoid aliases.", sev="minor", kind="best-practice", cat="correctness",
  docv="Buf CLI v1.5x", xref=[P3G])

# ------------------------------------------------------------------ field numbers / language rules
P("FIELD-NUMBER-RESERVED-RANGE", "Field number in 19000-19999", P3G, "Field numbers 19,000 to 19,999 are reserved for the Protobuf implementation.",
  '((field_number) @match (#match? @match "^19[0-9]{3}$"))',
  H3.format(M("  string name = 19000;\n")), H3.format(M("  string name = 1;\n")),
  "protoc rejects field numbers 19000-19999 (reserved for the implementation).", sev="major", kind="anti-pattern", cat="correctness")
P("FIELD-NUMBER-TOO-LARGE", "Field number above 536,870,911", P3G, "536,870,911 with the following restrictions:",
  '((field_number) @match (#match? @match "^([1-9][0-9]{9,}|53687091[2-9]|5368709[2-9][0-9]|536870[2-9][0-9]{2}|53687[1-9][0-9]{3}|5368[89][0-9]{4}|5369[0-9]{5}|53[7-9][0-9]{6}|5[4-9][0-9]{7}|[6-9][0-9]{8})$"))',
  H3.format(M("  string name = 600000000;\n")), H3.format(M("  string name = 2;\n")),
  "Field numbers are 29-bit; protoc rejects anything above 536,870,911.", sev="major", kind="anti-pattern", cat="correctness")
P("FIELD-NUMBER-SMALL-HOT", "High field number on a likely-hot field", P3G, "Field numbers in the range 1 through 15 take one byte to encode",
  '((field (identifier) @match (field_number) @n) (#match? @match "^(id|name|type|kind|status)$") (#match? @n "^[0-9]{3,}$"))',
  H3.format(M("  string id = 2048;\n")), H3.format(M("  string id = 1;\n")),
  "Numbers 1-15 encode in one byte; reserve them for frequently-set fields.", sev="info", kind="best-practice", cat="performance",
  mode="ai-confirm", ai="Is this field set on most messages (so a 1-byte tag would matter) and is renumbering still possible (schema unreleased)?")
P("PROTO2-REQUIRED", "proto2 required field", P2G, "required must not be used for new fields",
  '((field) @match (#match? @match "^required\\\\s"))',
  H2.format(M("  required string name = 1;\n")), H2.format(M("  optional string name = 1;\n")),
  "required is forever: it can never be removed without breaking old readers. Validate at the application layer.",
  sev="major", kind="best-practice", cat="compatibility", filters=[F2], xref=[DD])
P("EDITIONS-LEGACY-REQUIRED", "features.field_presence = LEGACY_REQUIRED", EDF,
  "LEGACY_REQUIRED : The field is required for parsing and serialization.",
  '((field_option) @match (#match? @match "field_presence\\\\s*=\\\\s*LEGACY_REQUIRED"))',
  E23.format(M("  string name = 1 [features.field_presence = LEGACY_REQUIRED];\n")), E23.format(M("  string name = 1;\n")),
  "LEGACY_REQUIRED carries proto2 required's compatibility trap into editions; only keep it for migrated legacy fields.",
  sev="major", kind="best-practice", cat="compatibility", filters=[FED], docv="Edition 2023+")
P("PROTO2-GROUP", "proto2 group", P2G, "Note that the groups feature is deprecated and should not be used when creating new message types.",
  '(group) @match', H2.format("message SearchResponse {\n  repeated group Result = 1 {\n    optional string url = 2;\n  }\n}\n"),
  H2.format("message SearchResponse {\n  message Result {\n    optional string url = 1;\n  }\n  repeated Result results = 1;\n}\n"),
  "Groups are deprecated; use a nested message type.", sev="minor", kind="deprecation", cat="compatibility")
P("PROTO3-PACKED-REDUNDANT", "[packed = true] in proto3", P3G, "In proto3, repeated fields of scalar numeric types use packed encoding by default.",
  '((field_option (identifier) @n (constant) @v) @match (#eq? @n "packed") (#eq? @v "true"))',
  H3.format(M("  repeated int32 ids = 1 [packed = true];\n")), H3.format(M("  repeated int32 ids = 1;\n")),
  "Redundant: proto3 packs repeated scalars by default.", sev="info", kind="best-practice", cat="maintainability", filters=[F3])

# ------------------------------------------------------------------ editions migration
P("MIGRATE-TO-EDITIONS", "proto2/proto3 file (editions available)", EDO, "Protobuf Editions replace the proto2 and proto3 designations that we have used for Protobuf.",
  '((syntax) @match (#match? @match "proto[23]"))',
  H3.format(M("  string name = 1;\n")), E23.format(M("  string name = 1;\n")),
  "Editions supersede syntax declarations; migrate with Prototiller when your toolchain supports edition 2023+.",
  sev="info", kind="modernization", cat="modernization", docv="Edition 2023/2024")
P("EDITIONS-GROUP", "group syntax in an editions file", EDO, "Group syntax, available in proto2, is removed in editions.",
  '(group) @match', E23.format("message SearchResponse {\n  repeated group Result = 1 {\n    string url = 2;\n  }\n}\n"),
  E23.format("message SearchResponse {\n  message Result {\n    string url = 1;\n  }\n  repeated Result results = 1 [features.message_encoding = DELIMITED];\n}\n"),
  "Groups don't compile in editions; use a nested message with features.message_encoding = DELIMITED.", sev="major", kind="removal", cat="compatibility",
  filters=[FED], docv="Edition 2023+")
P("EDITIONS-REQUIRED-LABEL", "required label in an editions file", EDO, "The required label, available only in proto2, is unavailable in editions.",
  '((field) @match (#match? @match "^required\\\\s"))',
  E23.format(M("  required string name = 1;\n")), E23.format(M("  string name = 1;\n")),
  "required doesn't compile in editions; use features.field_presence = LEGACY_REQUIRED (or better, drop it).", sev="major", kind="removal", cat="compatibility",
  filters=[FED], docv="Edition 2023+")
P("EDITIONS-OPTIONAL-LABEL", "optional label in an editions file", PB + "programming-guides/editions/", "Singular : A singular field has no explicit cardinality label.",
  '((field) @match (#match? @match "^optional\\\\s"))',
  E23.format(M("  optional string name = 1;\n")), E23.format(M("  string name = 1 [features.field_presence = EXPLICIT];\n")),
  "Labels other than repeated are invalid in editions; presence is explicit by default (or set features.field_presence).",
  sev="major", kind="removal", cat="compatibility", filters=[FED], docv="Edition 2023+")
P("EDITIONS-PACKED-OPTION", "packed option in an editions file", EDF, "packed option for repeated fields has been migrated to in Editions.",
  '((field_option (identifier) @n) @match (#eq? @n "packed"))',
  E23.format(M("  repeated int32 ids = 1 [packed = false];\n")), E23.format(M("  repeated int32 ids = 1 [features.repeated_field_encoding = EXPANDED];\n")),
  "Use features.repeated_field_encoding (PACKED is the editions default).", sev="major", kind="removal", cat="compatibility", filters=[FED], docv="Edition 2023+")
P("EDITIONS-CTYPE-REMOVED", "ctype option in Edition 2024", EDF, "In Edition 2024, the ctype option is removed.",
  '((field_option (identifier) @n) @match (#eq? @n "ctype"))',
  E24.format(M("  string blob = 1 [ctype = CORD];\n")), E24.format(M("  string blob = 1 [features.(pb.cpp).string_type = CORD];\n")),
  "ctype no longer compiles in Edition 2024; use features.(pb.cpp).string_type.", sev="major", kind="removal", cat="compatibility", filters=[FE24],
  docv="Edition 2024")
P("EDITIONS-CTYPE-DEPRECATED", "ctype option (prefer string_type)", EDF, "ctype option from proto2 and proto3, and offers a new string_type feature.",
  '((field_option (identifier) @n) @match (#eq? @n "ctype"))',
  E23.format(M("  string blob = 1 [ctype = CORD];\n")), E23.format(M("  string blob = 1 [features.(pb.cpp).string_type = CORD];\n")),
  "Switch to features.(pb.cpp).string_type now; ctype is removed in Edition 2024.", sev="minor", kind="deprecation", cat="compatibility", filters=[FE23],
  docv="Edition 2023")
P("EDITIONS-JAVA-MULTIPLE-FILES", "java_multiple_files in Edition 2024+", EDF,
  "Setting this option to NO is the equivalent of setting java_multiple_files = true in proto2/proto3/edition 2023.",
  '((option (identifier) @n) @match (#eq? @n "java_multiple_files"))',
  E24.format('option java_multiple_files = true;\n\n' + M("  string name = 1;\n")),
  E24.format('option features.(pb.java).nest_in_file_class = NO;\n\n' + M("  string name = 1;\n")),
  "Edition 2024 replaces java_multiple_files with features.(pb.java).nest_in_file_class.", sev="major", kind="removal", cat="compatibility",
  filters=[FE24], docv="Edition 2024")
P("EDITIONS-UTF8-VALIDATION-NONE", "features.utf8_validation = NONE", EDF,
  "NONE : The field behaves like an unverified bytes field on the wire. Parsers may handle this type of field in an unpredictable way",
  '((_) @match (#match? @match "^features\\\\.utf8_validation\\\\s*=\\\\s*NONE"))\n((option) @match (#match? @match "features\\\\.utf8_validation\\\\s*=\\\\s*NONE"))',
  E23.format(M("  string name = 1 [features.utf8_validation = NONE];\n")), E23.format(M("  string name = 1;\n")),
  "Unvalidated string fields accept invalid UTF-8 that other runtimes reject or rewrite; use bytes for binary data.",
  sev="minor", kind="anti-pattern", cat="correctness", filters=[FED], docv="Edition 2023+")

# ------------------------------------------------------------------ API design (dos & don'ts)
P("WKT-TIMESTAMP", "Timestamp stored as int64/string", DD, "To use the Common Types, you may need to add a dependency on the googleapis repository",
  '((field (type) @t (identifier) @match) (#match? @t "^(u?int64|s?fixed64|sint64|string|double)$") (#match? @match "(_time|_at|_timestamp|^timestamp|_date)$"))',
  H3.format(M("  int64 created_at = 1;\n")), H3.format('import "google/protobuf/timestamp.proto";\n\n' + M("  google.protobuf.Timestamp create_time = 1;\n")),
  "Use google.protobuf.Timestamp (or google.type.Date) instead of ad-hoc epoch numbers/strings.", sev="minor", kind="best-practice", cat="maintainability",
  quote="Do Use Well-Known Types and Common Types", mode="ai-confirm", ai="Does this field hold a point in time (not e.g. a count or an opaque version)?")
P("WKT-DURATION", "Duration stored as a bare number", DD, "Do Use Well-Known Types and Common Types",
  '((field (type) @t (identifier) @match) (#match? @t "^(u?int(32|64)|double|float)$") (#match? @match "(_ms|_millis|_seconds|_secs|_nanos|_timeout|^timeout|_ttl|^ttl)$"))',
  H3.format(M("  int64 timeout_ms = 1;\n")), H3.format('import "google/protobuf/duration.proto";\n\n' + M("  google.protobuf.Duration timeout = 1;\n")),
  "Use google.protobuf.Duration so units are unambiguous across languages.", sev="info", kind="best-practice", cat="maintainability",
  mode="ai-confirm", ai="Does this field represent a time span whose unit is encoded only in its name?")
P("BOOL-MAY-GROW", "bool for a state that may gain values", DD, "Don’t Use Booleans for Something That Has Two States Now, but Might Have More Later",
  '((field (type) @t (identifier) @match) (#eq? @t "bool") (#match? @match "(status|state|type|mode|kind|level|tier|role)$"))',
  H3.format(M("  bool account_status = 1;\n")), H3.format("enum AccountStatus {\n  ACCOUNT_STATUS_UNSPECIFIED = 0;\n  ACCOUNT_STATUS_ACTIVE = 1;\n}\n\n" + M("  AccountStatus account_status = 1;\n")),
  "Changing bool to enum later is a breaking change; model states as an enum from the start.", sev="minor", kind="best-practice", cat="maintainability",
  mode="ai-confirm", ai="Could this state plausibly gain a third value?")
P("ANY-PREFER-EXTENSIONS", "google.protobuf.Any field", DD, "If you plan to use Any , first double-check if extensions can satisfy the use case instead.",
  '((field (type) @match) (#match? @match "^\\\\.?google\\\\.protobuf\\\\.Any$"))',
  H3.format('import "google/protobuf/any.proto";\n\n' + M("  google.protobuf.Any payload = 1;\n")),
  H3.format(M("  oneof payload {\n    Email email = 1;\n    Sms sms = 2;\n  }\n")),
  "Any loses static typing and requires type URLs at runtime; prefer a oneof or extensions where the set of types is known.",
  sev="info", kind="best-practice", cat="maintainability", mode="ai-confirm", ai="Is the set of payload types closed/known (so a oneof would do)?")
P("JAVA-OUTER-CLASSNAME", "java_package without java_outer_classname", DD, "Do Use java_outer_classname (before Edition 2024)",
  '((option (identifier) @n) @match (#eq? @n "java_package"))',
  H3.format('option java_package = "com.acme.user.v1";\n\n' + M("  string name = 1;\n")),
  H3.format('option java_package = "com.acme.user.v1";\noption java_outer_classname = "UserProto";\n\n' + M("  string name = 1;\n")),
  "Set java_outer_classname so the outer class can't collide with a message named like the file.", sev="info", kind="best-practice", cat="compatibility",
  filters=[r"file.lacks_re:java_outer_classname", r'file.lacks_re:(?m)^\s*edition\s*=\s*"20(2[4-9]|[3-9][0-9])"'])
P("GO-PACKAGE-MISSING", "No option go_package in a Go repo", PB + "reference/go/go-generated/", "go_package option with the full import path of the Go package.",
  '(source_file [(syntax) (edition)] @match)',
  H3.format(M("  string name = 1;\n")), H3.format('option go_package = "example.com/acme/gen/user/v1;userv1";\n\n' + M("  string name = 1;\n")),
  "protoc-gen-go needs the Go import path; set go_package in the file (or via buf managed mode).", sev="minor", kind="best-practice", cat="build",
  applies={"go": "*"}, filters=[r"file.lacks_re:go_package"], mode="ai-confirm",
  ai="Is Go code generated from this file without buf managed mode / M flags supplying the import path?")
P("MONEY-AS-FLOAT", "Money stored as float/double", DD, "the “Common Types” (such as Date and Money ) are not.",
  '((field (type) @t (identifier) @match) (#match? @t "^(float|double)$") (#match? @match "(price|amount|cost|balance|money|total|fee)"))',
  H3.format(M("  double price = 1;\n")), H3.format('import "google/type/money.proto";\n\n' + M("  google.type.Money price = 1;\n")),
  "Binary floating point can't represent cents exactly; use google.type.Money or integer minor units.", sev="major", kind="anti-pattern", cat="correctness")
P("MESSAGE-SEPARATE-FILES", "Many top-level messages in one file", DD, "you should have a single top-level entry point",
  '(source_file (message) @match)',
  H3.format("message A {}\nmessage B {}\nmessage C {}\nmessage D {}\nmessage E {}\nmessage F {}\n"), H3.format("message A {}\n"),
  "Large multi-message files bloat every dependant's dependency graph; keep one top-level entry point per file.", sev="info", kind="best-practice",
  cat="maintainability", filters=[r"file.has_re:(?s)(\n\s*message\s.*){6,}"], mode="ai-confirm",
  ai="Are these unrelated entry-point types (not small helper messages of one API)?")
P("API-STORAGE-SAME-MESSAGE", "Same message used for RPC and storage", DD, "Reusing the same messages for APIs and long-term storage may seem convenient",
  '((rpc (message_or_enum_type) @match) (#match? @match "(Entity|Record|Row|Model|Db|DB|Storage)$"))',
  H3.format("service UserService {\n  rpc GetUser(GetUserRequest) returns (UserRecord);\n}\n"),
  H3.format("service UserService {\n  rpc GetUser(GetUserRequest) returns (GetUserResponse);\n}\n"),
  "Coupling wire API and storage schema means every storage change is an API change; keep them separate and convert.",
  sev="minor", kind="best-practice", cat="maintainability", mode="ai-confirm", ai="Is this message also persisted (DB/log storage)?")
P("DELETED-FIELD-NOT-RESERVED", "Field reuse risk: removed field number not reserved", DD, "Do Reserve Tag Numbers for Deleted Fields",
  '((message_body) @match (#match? @match "(?i)//\\\\s*(removed|deleted|deprecated|unused)\\\\b"))',
  H3.format(M("  string name = 1;\n  // removed: string email = 2;\n")), H3.format(M("  string name = 1;\n  reserved 2;\n  reserved \"email\";\n")),
  "When a field is deleted, reserve its number and name so it can't be reused with a different meaning.", sev="minor", kind="best-practice",
  cat="compatibility", filters=[r"node.lacks_re:reserved"], mode="ai-confirm", ai="Does the comment mark a deleted field whose number is not reserved?")
RULES = P.R

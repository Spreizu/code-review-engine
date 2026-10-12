"""GraphQL pack (vendored bkegley grammar) for SDL schemas and executable documents (.graphql/.gql/.graphqls).
Sources: GraphQL spec (September 2025 edition), graphql.org Learn (security, pagination, schema design, queries),
GraphQL ESLint rule docs, graphql-js release notes. Version dimension `graphql` = graphql-js from package.json
(used for @oneOf support, added in 16.9.0)."""
from specs._common import Pack

SPEC = "https://spec.graphql.org/September2025/"
GE = "https://the-guild.dev/graphql/eslint/rules/"
LEARN = "https://graphql.org/learn/"
P = Pack("GRAPHQL", "graphql", "GraphQL spec September 2025 / GraphQL ESLint 4", {"any": "*"},
         files=["**/*.graphql", "**/*.gql", "**/*.graphqls"])
GEV = "GraphQL ESLint 4.x"


def ge(rule):
    return GE + rule


def obj_field(type_re, field_pred):
    """Field definitions of object types whose name matches type_re."""
    return (f'((object_type_definition (name) @t (fields_definition (field_definition (name) @fname (type) @ftype) @match)) '
            f'(#match? @t "^({type_re})$") {field_pred})')


# ------------------------------------------------------------------ operations (executable documents)
P("NO-ANONYMOUS-OPERATIONS", "Anonymous operation", ge("no-anonymous-operations"),
  "Require name for your GraphQL operations. This is useful since most GraphQL client libraries are using the operation name for caching purposes.",
  '(operation_definition (operation_type) . (selection_set)) @match\n(operation_definition . (selection_set)) @match',
  "query {\n  viewer {\n    id\n  }\n}\n", "query Viewer {\n  viewer {\n    id\n  }\n}\n",
  "Name every operation: clients cache, log and persist by operation name.", sev="minor", kind="best-practice", cat="maintainability", docv=GEV)
P("LONE-ANONYMOUS-OPERATION", "Anonymous operation alongside other operations", ge("lone-anonymous-operation"),
  "A GraphQL document that contains an anonymous operation (the query short-hand) is only valid if it contains only that one operation definition.",
  '(operation_definition (operation_type) . (selection_set)) @match\n(operation_definition . (selection_set)) @match',
  "query {\n  viewer {\n    id\n  }\n}\n\nquery Other {\n  ping\n}\n", "query Viewer {\n  viewer {\n    id\n  }\n}\n\nquery Other {\n  ping\n}\n",
  "A document with an anonymous operation must contain only that operation; servers reject it.", sev="major", kind="anti-pattern", cat="correctness",
  filters=[r"file.has_re:(?s)(^|\n)\s*(query|mutation|subscription|\{)[^\n]*\n.*\n\s*(query|mutation|subscription|\{)"],
  doc="Lone Anonymous Operation", xref=[SPEC], docv=GEV)
P("ONE-FIELD-SUBSCRIPTIONS", "Subscription with more than one root field", SPEC, "Subscription operations must have exactly one root field.",
  '((operation_definition (operation_type) @t (selection_set (selection) (selection))) @match (#eq? @t "subscription"))',
  "subscription OnMessage {\n  newMessage {\n    body\n  }\n  newUser {\n    id\n  }\n}\n", "subscription OnMessage {\n  newMessage {\n    body\n  }\n}\n",
  "Spec validation error: a subscription must select exactly one root field.", sev="major", kind="anti-pattern", cat="correctness")
P("NO-DUPLICATE-FIELDS", "Field selected twice in a selection set", ge("no-duplicate-fields"),
  "Checks for duplicate fields in selection set, variables in operation definition, or in arguments set of a field.",
  '((selection_set (selection (field . (name) @a)) (selection (field . (name) @b) @match)) (#eq? @a @b))\n'
  '((variable_definitions (variable_definition (variable (name) @a)) (variable_definition (variable (name) @b)) @match) (#eq? @a @b))\n'
  '((arguments (argument (name) @a) (argument (name) @b) @match) (#eq? @a @b))',
  "query User {\n  user {\n    id\n    name\n    id\n  }\n}\n", "query User {\n  user {\n    id\n    name\n  }\n}\n",
  "Duplicate selections/variables/arguments are redundant at best and a validation error for variables/arguments.", sev="minor", kind="anti-pattern",
  cat="correctness", docv=GEV)
P("INLINE-DYNAMIC-ARGUMENT", "Literal argument in a named operation (use variables)", LEARN + "queries/",
  "It wouldn’t be a good idea to pass these dynamic arguments directly in the query string",
  '(operation_definition (operation_type) (name) (selection_set (selection (field (arguments (argument (value [(string_value) (int_value)] @match)))))))',
  'query Hero {\n  hero(episode: "JEDI") {\n    name\n  }\n}\n', "query Hero($episode: Episode) {\n  hero(episode: $episode) {\n    name\n  }\n}\n",
  "Interpolating values into the document defeats caching/persisted documents and invites injection; pass them as variables.",
  sev="minor", kind="best-practice", cat="security", mode="ai-confirm", ai="Is this argument value dynamic (user/runtime input) rather than a fixed constant?")
P("SELECTION-SET-DEPTH", "Deeply nested operation (depth > 7)", ge("selection-set-depth"),
  "Limit the complexity of the GraphQL operations solely by their depth.",
  "(selection_set" + " (selection (field (selection_set" * 7 + ")))" * 7 + ") @match",
  "query Deep {\n  a { b { c { d { e { f { g { h { id } } } } } } } }\n}\n", "query Shallow {\n  a { b { c { id } } }\n}\n",
  "Very deep operations are expensive and a common DoS vector; flatten or use fragments with server-side depth limits.",
  sev="minor", kind="best-practice", cat="performance", docv=GEV, xref=[LEARN + "security/"])

P("ALIAS-FAN-OUT", "Same field aliased 5+ times in one selection set", LEARN + "security/",
  "there should also be guardrails in place to limit the number of top-level fields and field aliases included in a single operation.",
  '((selection_set (selection (field (alias) (name) @a0)) (selection (field (alias) (name) @a1)) (selection (field (alias) (name) @a2)) (selection (field (alias) (name) @a3)) (selection (field (alias) (name) @a4))) @match (#eq? @a0 @a1) (#eq? @a0 @a2) (#eq? @a0 @a3) (#eq? @a0 @a4))',
  "query Friends {\n  viewer {\n    f1: friends(limit: 1) { name }\n    f2: friends(limit: 2) { name }\n    f3: friends(limit: 3) { name }\n    f4: friends(limit: 4) { name }\n    f5: friends(limit: 5) { name }\n  }\n}\n",
  "query Friends {\n  viewer {\n    friends(limit: 5) { name }\n  }\n}\n",
  "Alias fan-out multiplies resolver work in one request (a classic GraphQL DoS); fetch once or enforce breadth/complexity limits server-side.",
  sev="minor", kind="security", cat="security", mode="ai-confirm", ai="Is this alias fan-out generated/unbounded or a legit small fixed set?")

# ------------------------------------------------------------------ schema naming / descriptions
P("TYPE-NAME-PASCALCASE", "Type name not PascalCase", ge("naming-convention"), "Require names to follow specified conventions.",
  "\n".join(f'(({n} (name) @match) (#not-match? @match "^[A-Z][A-Za-z0-9]*$"))' for n in
            ["object_type_definition", "interface_type_definition", "input_object_type_definition", "enum_type_definition", "union_type_definition"]),
  "type user_profile {\n  id: ID!\n}\n", "type UserProfile {\n  id: ID!\n}\n", "Use PascalCase type names (the convention all GraphQL tooling assumes).",
  sev="info", kind="best-practice", cat="style", docv=GEV)
P("FIELD-NAME-CAMELCASE", "Field/argument name not camelCase", ge("naming-convention"), "Require names to follow specified conventions.",
  '((field_definition . (name) @match) (#not-match? @match "^[a-z][A-Za-z0-9]*$"))\n((input_value_definition . (name) @match) (#not-match? @match "^[a-z][A-Za-z0-9]*$"))',
  "type User {\n  first_name: String\n}\n", "type User {\n  firstName: String\n}\n", "Use camelCase field and argument names.",
  sev="info", kind="best-practice", cat="style", docv=GEV)
P("ENUM-VALUE-UPPERCASE", "Enum value not UPPER_CASE", ge("naming-convention"), "Require names to follow specified conventions.",
  '((enum_value (name) @match) (#not-match? @match "^[A-Z][A-Z0-9_]*$"))',
  "enum Role {\n  admin\n  USER\n}\n", "enum Role {\n  ADMIN\n  USER\n}\n", "Use UPPER_CASE enum values.", sev="info", kind="best-practice", cat="style", docv=GEV)
P("RESERVED-DOUBLE-UNDERSCORE", "Name starting with __", SPEC, '"__" (two underscores), as this is used exclusively by GraphQL’s introspection system.',
  '((name) @match (#match? @match "^__"))',
  "type User {\n  __internal: String\n}\n", "type User {\n  internal: String\n}\n",
  "Names beginning with __ are reserved for introspection; schema builders reject them.", sev="major", kind="anti-pattern", cat="correctness",
  files=["**/*.graphqls", "**/schema*.graphql", "**/*.schema.graphql", "**/schema/**/*.graphql", "**/*.graphql", "**/*.gql"],
  filters=[r"node.lacks_re:^__(typename|schema|type)$"])
P("NO-HASHTAG-DESCRIPTION", "# comment used as a description", ge("no-hashtag-description"),
  "Requires to use \"\"\" or \" for adding a GraphQL description instead of # .",
  '((comment) @match . (document))\n((document (comment) @match . (definition (type_system_definition))))',
  "# A user account\ntype User {\n  id: ID!\n}\n", '"""A user account"""\ntype User {\n  id: ID!\n}\n',
  "# comments are dropped from the schema; use a \"\"\"description\"\"\" so it shows up in introspection and docs.", sev="info", kind="best-practice",
  cat="maintainability", docv=GEV, filters=[r"file.has_re:(?m)^\s*(type|interface|input|enum|union|scalar|schema|directive|extend)\b"])
P("REQUIRE-DESCRIPTION-ROOT", "Root operation field without description", ge("require-description"),
  "Enforce descriptions in type definitions and operations.",
  '((object_type_definition (name) @t (fields_definition (field_definition . (name) @match))) (#match? @t "^(Query|Mutation|Subscription)$"))',
  "type Query {\n  user(id: ID!): User\n}\n", 'type Query {\n  "Fetch a user by ID."\n  user(id: ID!): User\n}\n',
  "Root fields are your public API; document them.", sev="info", kind="best-practice", cat="maintainability", docv=GEV)

# ------------------------------------------------------------------ deprecation
P("REQUIRE-DEPRECATION-REASON", "@deprecated without reason", ge("require-deprecation-reason"), "Require all deprecation directives to specify a reason.",
  '((directive (name) @n) @match (#eq? @n "deprecated") (#not-match? @match "reason"))',
  "type User {\n  name: String @deprecated\n  fullName: String\n}\n", 'type User {\n  name: String @deprecated(reason: "Use fullName.")\n  fullName: String\n}\n',
  "Say what to use instead; the reason surfaces in IDEs and introspection.", sev="minor", kind="best-practice", cat="maintainability", docv=GEV)
P("REQUIRE-DEPRECATION-DATE", "@deprecated without a removal date", ge("require-deprecation-date"),
  "Require deletion date on @deprecated directive. Suggest removing deprecated things after deprecated date.",
  '((directive (name) @n) @match (#eq? @n "deprecated") (#not-match? @match "deletionDate"))',
  'type User {\n  name: String @deprecated(reason: "Use fullName.")\n}\n', 'type User {\n  name: String @deprecated(reason: "Use fullName.", deletionDate: "31/12/2026")\n}\n',
  "Track when deprecated fields may be removed.", sev="info", kind="best-practice", cat="maintainability", docv=GEV,
  mode="ai-confirm",
  ai="Does this project use deletionDate on other @deprecated directives (i.e. the convention is established)?")
P("DEPRECATED-REQUIRED-ARGUMENT", "@deprecated on a required argument/input field", SPEC,
  "deprecated directive must not be applied to this argument.",
  '((input_value_definition (type (non_null_type)) (directives (directive (name) @d))) @match (#eq? @d "deprecated") (#not-match? @match "="))',
  'type Query {\n  users(limit: Int! @deprecated(reason: "Use first.")): [User]\n}\n',
  'type Query {\n  users(limit: Int @deprecated(reason: "Use first."), first: Int): [User]\n}\n',
  "Required (non-null without default) arguments can't be deprecated; make it nullable or give it a default first.", sev="major", kind="anti-pattern",
  cat="correctness")

# ------------------------------------------------------------------ schema design
P("MUTATION-SCALAR-RESULT", "Mutation returns a bare scalar", ge("no-scalar-result-type-on-mutation"),
  "Avoid scalar result type on mutation type to make sure to return a valid state.",
  obj_field("Mutation", '(#match? @ftype "^(Boolean|Int|String|ID|Float)!?$")'),
  "type Mutation {\n  deleteUser(id: ID!): Boolean\n}\n", "type Mutation {\n  deleteUser(id: ID!): DeleteUserPayload\n}\n",
  "Return a payload type so clients can refetch state and you can add fields/errors later without a breaking change.",
  sev="minor", kind="best-practice", cat="maintainability", docv=GEV)
P("ROOT-NON-NULL-RESULT", "Non-null result on a root Query/Mutation field", ge("require-nullable-result-in-root"), "Require nullable fields in root types.",
  obj_field("Query|Mutation", '(#match? @ftype "!$")'),
  "type Query {\n  user(id: ID!): User!\n}\n", "type Query {\n  user(id: ID!): User\n}\n",
  "A non-null root field turns any resolver error into a null for the whole response data.", sev="info", kind="best-practice", cat="correctness", docv=GEV)
P("MUTATION-INPUT-NAME", "Mutation argument not named input", ge("input-name"),
  "Require mutation argument to be always called “input” and input type to be called Mutation name + “Input”.",
  '((object_type_definition (name) @t (fields_definition (field_definition (name) (arguments_definition (input_value_definition . (name) @match))))) (#eq? @t "Mutation") (#not-eq? @match "input"))',
  "type Mutation {\n  createUser(name: String!, email: String!): CreateUserPayload\n}\n", "type Mutation {\n  createUser(input: CreateUserInput!): CreateUserPayload\n}\n",
  "A single input object per mutation keeps signatures evolvable and predictable.", sev="info", kind="best-practice", cat="maintainability", docv=GEV)
P("INPUT-TYPE-SUFFIX", "Input type name lacks Input suffix", ge("input-name"),
  "Using the same name for all input parameters will make your schemas easier to consume and more predictable.",
  '((input_object_type_definition (name) @match) (#not-match? @match "Input$"))',
  "input NewUser {\n  name: String!\n}\n", "input CreateUserInput {\n  name: String!\n}\n", "Suffix input types with Input.", sev="info", kind="best-practice", cat="style",
  docv=GEV)
P("STRICT-ID-IN-TYPES", "Object type without an id: ID! field", ge("strict-id-in-types"),
  "Requires output types to have one unique identifier unless they do not have a logical one.",
  '((object_type_definition (name) @n (fields_definition) @f) @match (#not-match? @n "^(Query|Mutation|Subscription|PageInfo)$|(Connection|Edge|Payload|Result|Error)$") (#not-match? @f "\\\\bid\\\\s*:\\\\s*ID!"))',
  "type Order {\n  total: Int\n}\n", "type Order {\n  id: ID!\n  total: Int\n}\n",
  "Entities without a stable ID can't be normalized/cached by clients or refetched via node(id:).", sev="info", kind="best-practice", cat="maintainability",
  docv=GEV, mode="ai-confirm", ai="Is this an entity with identity (not a value object like Money/Address)?", xref=[LEARN + "global-object-identification/"])
P("ID-AS-INT-OR-STRING", "id field typed Int/String instead of ID", LEARN + "global-object-identification/", "Consistent object access enables simple",
  '((field_definition . (name) @n (type) @match) (#eq? @n "id") (#match? @match "^(Int|String)!?$"))',
  "type User {\n  id: Int!\n}\n", "type User {\n  id: ID!\n}\n", "Use the ID scalar for identifiers (opaque, cache keys, node lookups).",
  sev="minor", kind="best-practice", cat="maintainability")
P("LIST-FIELD-NOT-PAGINATED", "Unbounded list field without arguments", LEARN + "security/",
  "When a field outputs a List type and the resulting list could potentially return a lot of data, it should",
  '(field_definition (name) . [(type (list_type)) (type (non_null_type (list_type)))]) @match',
  "type Query {\n  users: [User!]!\n}\n", "type Query {\n  users(first: Int!, after: String): UserConnection!\n}\n",
  "Unbounded lists let a single request pull the whole table; paginate (first/after) or cap the size.", sev="minor", kind="security", cat="security",
  mode="ai-confirm", ai="Can this list grow unbounded (rows from a datastore, not a small fixed set)?", xref=[LEARN + "pagination/"])
P("RELAY-CONNECTION-FIELDS", "Connection type missing edges/pageInfo", ge("relay-connection-types"),
  "Any type whose name ends in “Connection” is considered by spec to be a Connection type",
  '((object_type_definition (name) @n (fields_definition) @f) @match (#match? @n "Connection$") (#not-match? @f "(?s)\\\\bedges\\\\s*:.*\\\\bpageInfo\\\\s*:\\\\s*PageInfo!|(?s)\\\\bpageInfo\\\\s*:\\\\s*PageInfo!.*\\\\bedges\\\\s*:"))',
  "type UserConnection {\n  nodes: [User]\n}\n", "type UserConnection {\n  edges: [UserEdge]\n  pageInfo: PageInfo!\n}\n",
  "Connections need edges and pageInfo: PageInfo! for cursor pagination clients.", sev="minor", kind="best-practice", cat="correctness", docv=GEV,
  xref=[LEARN + "pagination/"])
P("RELAY-EDGE-FIELDS", "Edge type missing node/cursor", ge("relay-edge-types"),
  "A type that is returned in list form by a connection type’s edges field is considered by this spec to be an Edge type",
  '((object_type_definition (name) @n (fields_definition) @f) @match (#match? @n "Edge$") (#not-match? @f "(?s)\\\\bnode\\\\s*:.*\\\\bcursor\\\\s*:|(?s)\\\\bcursor\\\\s*:.*\\\\bnode\\\\s*:"))',
  "type UserEdge {\n  user: User\n}\n", "type UserEdge {\n  node: User\n  cursor: String!\n}\n", "Edges need node and cursor.", sev="minor", kind="best-practice",
  cat="correctness", docv=GEV)
P("RELAY-PAGE-INFO-FIELDS", "PageInfo missing required fields", ge("relay-page-info"),
  "PageInfo must contain fields hasPreviousPage and hasNextPage , that return non-null Boolean",
  '((object_type_definition (name) @n (fields_definition) @f) @match (#eq? @n "PageInfo"))',
  "type PageInfo {\n  hasNextPage: Boolean\n}\n", "type PageInfo {\n  hasNextPage: Boolean!\n  hasPreviousPage: Boolean!\n  startCursor: String\n  endCursor: String\n}\n",
  "PageInfo must expose hasNextPage/hasPreviousPage: Boolean! and start/endCursor.", sev="minor", kind="best-practice", cat="correctness", docv=GEV,
  filters=[r"node.lacks_re:(?s)hasNextPage\s*:\s*Boolean!.*hasPreviousPage\s*:\s*Boolean!|hasPreviousPage\s*:\s*Boolean!.*hasNextPage\s*:\s*Boolean!"])
P("RELAY-ARGUMENTS", "Connection field without first/after or last/before", ge("relay-arguments"),
  "A field that returns a Connection type must include forward pagination arguments ( first and after ), backward pagination arguments ( last and before ), or both",
  '((field_definition (type) @t) @match (#match? @t "Connection!?$") (#not-match? @match "\\\\b(first|last)\\\\s*:"))',
  "type Query {\n  users: UserConnection!\n}\n", "type Query {\n  users(first: Int, after: String): UserConnection!\n}\n",
  "Connection fields need cursor pagination arguments.", sev="minor", kind="best-practice", cat="correctness", docv=GEV)
P("SCALAR-SPECIFIED-BY", "Custom scalar without @specifiedBy", SPEC, "should provide a scalar specification URL via the @specifiedBy directive",
  '((scalar_type_definition (name) @n) @match (#not-match? @match "@specifiedBy"))',
  "scalar DateTime\n", 'scalar DateTime @specifiedBy(url: "https://scalars.graphql.org/chillicream/date-time.html")\n',
  "Link custom scalars to their format so clients know how to (de)serialize them.", sev="info", kind="best-practice", cat="maintainability",
  docv="GraphQL spec October 2021+")
P("VERSIONED-NAMES", "Versioned type/field name (V2, _v2)", LEARN + "schema-design/",
  "GraphQL takes a strong opinion on avoiding versioning by providing the tools for the continuous evolution of a GraphQL schema.",
  '((object_type_definition (name) @match) (#match? @match "V[0-9]+$"))\n((field_definition . (name) @match) (#match? @match "(V|_v)[0-9]+$"))',
  "type Query {\n  userV2(id: ID!): User\n}\n", "type Query {\n  user(id: ID!): User\n}\n",
  "Evolve the schema additively (new fields + @deprecated) instead of versioned copies.", sev="info", kind="best-practice", cat="maintainability",
  mode="ai-confirm", ai="Is the version suffix an API version (not a domain term like 'ipV4')?")

# ------------------------------------------------------------------ validity / uniqueness
P("DUPLICATE-ENUM-VALUE", "Enum value defined twice", ge("unique-enum-value-names"),
  "A GraphQL enum type is only valid if all its values are uniquely named.",
  '((enum_values_definition (enum_value_definition (enum_value (name) @a)) (enum_value_definition (enum_value (name) @b)) @match) (#eq? @a @b))',
  "enum Role {\n  ADMIN\n  USER\n  ADMIN\n}\n", "enum Role {\n  ADMIN\n  USER\n}\n", "Duplicate enum values make the schema invalid.",
  sev="major", kind="anti-pattern", cat="correctness", docv=GEV)
P("DUPLICATE-FIELD-DEFINITION", "Field defined twice in a type", SPEC, "must be unique.",
  '((fields_definition (field_definition . (name) @a) (field_definition . (name) @b) @match) (#eq? @a @b))\n'
  '((input_fields_definition (input_value_definition . (name) @a) (input_value_definition . (name) @b) @match) (#eq? @a @b))',
  "type User {\n  id: ID!\n  name: String\n  id: ID!\n}\n", "type User {\n  id: ID!\n  name: String\n}\n",
  "Field names must be unique within a type; schema construction fails.", sev="major", kind="anti-pattern", cat="correctness")
P("LONE-SCHEMA-DEFINITION", "More than one schema definition", ge("lone-schema-definition"),
  "A GraphQL document is only valid if it contains only one schema definition.",
  '(schema_definition) @match', "schema {\n  query: Query\n}\n\nschema {\n  mutation: Mutation\n}\n", "schema {\n  query: Query\n  mutation: Mutation\n}\n",
  "Only one schema definition is allowed (use extend schema).", sev="major", kind="anti-pattern", cat="correctness", docv=GEV,
  filters=[r"file.has_re:(?s)(^|\n)\s*schema\s*\{.*\n\s*schema\s*\{"])

# ------------------------------------------------------------------ @oneOf (spec 2025, graphql-js >= 16.9)
P("ONEOF-NON-NULL-FIELD", "Non-null field in a @oneOf input", SPEC, "must be nullable. The input field must not have a default value.",
  '((input_object_type_definition (directives (directive (name) @d)) (input_fields_definition (input_value_definition (type (non_null_type))) @match)) (#eq? @d "oneOf"))\n'
  '((input_object_type_definition (directives (directive (name) @d)) (input_fields_definition (input_value_definition (default_value)) @match)) (#eq? @d "oneOf"))',
  "input UserBy @oneOf {\n  id: ID!\n  email: String\n}\n", "input UserBy @oneOf {\n  id: ID\n  email: String\n}\n",
  "OneOf input fields must be nullable and have no defaults (exactly one is provided).", sev="major", kind="anti-pattern", cat="correctness",
  xref=[ge("require-nullable-fields-with-oneof")])
P("ONEOF-UNSUPPORTED-GRAPHQL-JS", "@oneOf with graphql-js < 16.9", "https://github.com/graphql/graphql-js/releases/tag/v16.9.0",
  "Implement OneOf Input Objects via @oneOf directive",
  '((directive (name) @d) @match (#eq? @d "oneOf"))',
  "input UserBy @oneOf {\n  id: ID\n  email: String\n}\n", "input UserBy {\n  id: ID\n  email: String\n}\n",
  "graphql-js only understands @oneOf from 16.9.0; older versions treat it as an unknown directive. Upgrade graphql.",
  sev="major", kind="migration", cat="compatibility", applies={"graphql": "<16.9.0"}, docv="graphql-js 16.9.0")
P("PREFER-ONEOF-INPUT", "Mutually exclusive nullable inputs (consider @oneOf)", SPEC, "oneOf directive must not be provided by an Input Object type extension.",
  '((input_object_type_definition (name) @n (input_fields_definition) @f) @match (#match? @n "(By|Selector|Filter|Lookup)(Input)?$") (#not-match? @match "@oneOf"))',
  "input UserByInput {\n  id: ID\n  email: String\n}\n", "input UserByInput @oneOf {\n  id: ID\n  email: String\n}\n",
  "When exactly one field may be set, @oneOf makes that a schema guarantee instead of resolver code.", sev="info", kind="modernization", cat="modernization",
  applies={"graphql": ">=16.9.0"}, docv="GraphQL spec September 2025", mode="ai-confirm", ai="Are these fields mutually exclusive (exactly one expected)?")

RULES = P.R

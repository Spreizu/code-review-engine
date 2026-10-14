# Linter fixture evaluation

485 rules with an equivalent linter suite evaluated (561 listed). Totals: TP 3179, FP 436, FN 4299, TN 5952, precision 0.879, recall 0.425. Deterministic rules (reach the review list without AI): TP 1802, FP 0, precision 1.000, 0 below 0.9. Rules with precision < 0.9: 109.

Case level for RuleTester/hadolint suites (valid = must-not-match); line level for ruff and `// want` testdata. Option-dependent cases skipped; env = FP/FN on cases written for another environment (old ecmaVersion, custom globals, script source, inline directives), not scored.

| rule | mode | xref | cases | skipped | env | TP | FN | FP | TN | precision | recall | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GO-MAINT-IDENTICAL-OPERANDS | ai-confirm | staticcheck:SA4000 | 4 | 0 | 0 | 0 | 11 | 2 | 2 | 0.00 | 0.00 |  |
| GO-MOD-ATOMICTYPES | ai-confirm | govet:modernize | 8 | 0 | 0 | 0 | 5 | 15 | 1 | 0.00 | 0.00 |  |
| GO-MOD-MAPSLOOP | ai-confirm | govet:modernize | 2 | 0 | 0 | 0 | 19 | 11 | 0 | 0.00 | 0.00 |  |
| GO-MOD-MINMAX | ai-confirm | govet:modernize | 12 | 0 | 0 | 0 | 13 | 2 | 8 | 0.00 | 0.00 |  |
| GO-QUAL-VET-PRINTF-NONCONST | ai-confirm | govet:printf | 15 | 0 | 0 | 0 | 279 | 2 | 4 | 0.00 | 0.00 |  |
| GRAPHQL-QUAL-ENUM-VALUE-UPPERCASE | ai-confirm | graphql-eslint:@graphql-eslint/naming-convention | 4 | 41 | 0 | 0 | 1 | 1 | 2 | 0.00 | 0.00 |  |
| GRAPHQL-QUAL-TYPE-NAME-PASCALCASE | ai-confirm | graphql-eslint:@graphql-eslint/naming-convention | 4 | 41 | 0 | 0 | 1 | 1 | 2 | 0.00 | 0.00 |  |
| GO-MOD-SORTSLICE-FUNC | ai-confirm | govet:modernize | 2 | 0 | 0 | 2 | 2 | 6 | 0 | 0.25 | 0.50 |  |
| TS-QUAL-PREFER-FOR-OF | ai-confirm | typescript-eslint:@typescript-eslint/prefer-for-of | 70 | 0 | 0 | 7 | 11 | 19 | 33 | 0.27 | 0.39 |  |
| PY-MAINT-MOCK-MISSPELLED-ASSERT | ai-confirm | ruff:PGH005 | 1 | 0 | 0 | 2 | 16 | 5 | 0 | 0.29 | 0.11 |  |
| GRAPHQL-QUAL-NO-HASHTAG-DESCRIPTION | ai-confirm | graphql-eslint:@graphql-eslint/no-hashtag-description | 18 | 13 | 0 | 2 | 3 | 4 | 9 | 0.33 | 0.40 |  |
| JS-QUAL-NO-LOOP-FUNC | ai-confirm | eslint:no-loop-func | 94 | 13 | 25 | 1 | 17 | 2 | 49 | 0.33 | 0.06 |  |
| JS-QUAL-NO-NEGATED-CONDITION | ai-confirm | eslint:no-negated-condition | 19 | 0 | 0 | 1 | 5 | 2 | 11 | 0.33 | 0.17 |  |
| JS-QUAL-NO-WARNING-COMMENTS | ai-confirm | eslint:no-warning-comments | 9 | 52 | 1 | 2 | 0 | 4 | 2 | 0.33 | 1.00 |  |
| JS-QUAL-PREFER-EXPONENTIATION-OPERATOR | ai-confirm | eslint:prefer-exponentiation-operator | 30 | 207 | 1 | 3 | 2 | 5 | 19 | 0.38 | 0.60 |  |
| PY-QUAL-IMPORT-STAR | ai-confirm | ruff:F403 | 1 | 0 | 0 | 2 | 0 | 3 | 0 | 0.40 | 1.00 |  |
| TS-QUAL-NO-INVALID-VOID-TYPE | ai-confirm | typescript-eslint:@typescript-eslint/no-invalid-void-type | 69 | 27 | 0 | 11 | 23 | 16 | 19 | 0.41 | 0.32 |  |
| GO-MOD-SLICESCLIP | ai-confirm | govet:modernize | 1 | 0 | 0 | 3 | 1 | 4 | 0 | 0.43 | 0.75 |  |
| TS-QUAL-TSIGNORE-001 | ai-confirm | typescript-eslint:@typescript-eslint/ban-ts-comment | 28 | 86 | 0 | 4 | 3 | 5 | 16 | 0.44 | 0.57 |  |
| PY-MAINT-EXCEPTION-NOT-RAISED | ai-confirm | ruff:PLW0133 | 1 | 0 | 0 | 16 | 5 | 19 | 0 | 0.46 | 0.76 |  |
| GO-MOD-BLOOP | ai-confirm | govet:modernize | 2 | 0 | 0 | 7 | 0 | 8 | 1 | 0.47 | 1.00 |  |
| TS-QUAL-NO-REDUNDANT-TYPE-CONSTITUENTS | ai-confirm | typescript-eslint:@typescript-eslint/no-redundant-type-constituents | 104 | 0 | 0 | 8 | 41 | 9 | 46 | 0.47 | 0.16 |  |
| GO-QUAL-VET-ASSIGN | ai-confirm | govet:assign | 2 | 0 | 0 | 10 | 8 | 11 | 0 | 0.48 | 0.56 |  |
| GO-MAINT-EMPTY-BLOCK | ai-confirm | staticcheck:SA9003 | 3 | 0 | 0 | 1 | 6 | 1 | 1 | 0.50 | 0.14 |  |
| GO-MOD-SLICESSORT | ai-confirm | govet:modernize | 2 | 0 | 0 | 2 | 2 | 2 | 0 | 0.50 | 0.50 |  |
| GO-QUAL-VET-APPENDS | ai-confirm | govet:appends | 2 | 0 | 0 | 2 | 0 | 2 | 0 | 0.50 | 1.00 |  |
| GO-QUAL-VET-COMPOSITES | ai-confirm | govet:composite | 5 | 0 | 0 | 6 | 4 | 6 | 3 | 0.50 | 0.60 |  |
| GO-QUAL-VET-TIMEFORMAT | ai-confirm | govet:timeformat | 2 | 0 | 0 | 2 | 1 | 2 | 1 | 0.50 | 0.67 |  |
| JS-QUAL-NO-NEW-NATIVE-NONCONSTRUCTOR | ai-confirm | eslint:no-new-native-nonconstructor | 14 | 4 | 0 | 4 | 0 | 4 | 6 | 0.50 | 1.00 |  |
| PY-MAINT-NEGATED-EQUALITY | ai-confirm | ruff:SIM201 | 1 | 0 | 0 | 3 | 0 | 3 | 0 | 0.50 | 1.00 |  |
| TS-QUAL-PREFER-FIND | ai-confirm | typescript-eslint:@typescript-eslint/prefer-find | 47 | 9 | 0 | 6 | 22 | 6 | 13 | 0.50 | 0.21 |  |
| VUE-MIG-NO-DEPRECATED-PROPS-DEFAULT-THIS | ai-confirm | eslint-plugin-vue:vue/no-deprecated-props-default-this | 8 | 0 | 0 | 3 | 0 | 3 | 2 | 0.50 | 1.00 |  |
| TS-QUAL-PREFER-REDUCE-TYPE-PARAMETER | ai-confirm | typescript-eslint:@typescript-eslint/prefer-reduce-type-parameter | 31 | 4 | 0 | 10 | 4 | 9 | 8 | 0.53 | 0.71 |  |
| GO-MOD-FORVAR | ai-confirm | govet:modernize | 1 | 0 | 0 | 7 | 3 | 6 | 0 | 0.54 | 0.70 |  |
| PY-QUAL-DATETIME-NOW-NAIVE | ai-confirm | ruff:DTZ005 | 1 | 0 | 0 | 7 | 3 | 6 | 0 | 0.54 | 0.70 |  |
| GO-MOD-SLICESBACKWARD | ai-confirm | govet:modernize | 1 | 0 | 0 | 20 | 0 | 17 | 0 | 0.54 | 1.00 |  |
| TS-QUAL-NO-UNNECESSARY-BOOLEAN-LITERAL-COMPARE | ai-confirm | typescript-eslint:@typescript-eslint/no-unnecessary-boolean-literal-compare | 40 | 32 | 0 | 16 | 7 | 13 | 4 | 0.55 | 0.70 |  |
| PY-MAINT-LOCAL-NAMING | ai-confirm | ruff:N806 | 1 | 0 | 0 | 10 | 4 | 8 | 0 | 0.56 | 0.71 |  |
| PY-QUAL-CALLABLE-HASATTR | ai-confirm | ruff:B004 | 1 | 0 | 0 | 5 | 3 | 4 | 0 | 0.56 | 0.62 |  |
| GO-MOD-TESTINGCONTEXT | ai-confirm | govet:modernize | 2 | 0 | 0 | 9 | 0 | 7 | 1 | 0.56 | 1.00 |  |
| JS-SEC-NO-NEW-FUNC | ai-confirm | eslint:no-new-func | 23 | 0 | 2 | 4 | 6 | 3 | 8 | 0.57 | 0.40 |  |
| TS-QUAL-PREFER-STRING-STARTS-ENDS-WITH | ai-confirm | typescript-eslint:@typescript-eslint/prefer-string-starts-ends-with | 131 | 11 | 0 | 11 | 58 | 8 | 54 | 0.58 | 0.16 |  |
| TS-QUAL-CONSISTENT-INDEXED-OBJECT-STYLE | ai-confirm | typescript-eslint:@typescript-eslint/consistent-indexed-object-style | 93 | 62 | 0 | 13 | 37 | 9 | 34 | 0.59 | 0.26 |  |
| PY-MAINT-ANY-ALL-LIST-COMPREHENSION | ai-confirm | ruff:C419 | 2 | 0 | 0 | 3 | 7 | 2 | 0 | 0.60 | 0.30 |  |
| TS-QUAL-NO-NON-NULL-ASSERTED-OPTIONAL-CHAIN | ai-confirm | typescript-eslint:@typescript-eslint/no-non-null-asserted-optional-chain | 23 | 0 | 0 | 3 | 7 | 2 | 11 | 0.60 | 0.30 |  |
| TS-QUAL-PREFER-REGEXP-EXEC | ai-confirm | typescript-eslint:@typescript-eslint/prefer-regexp-exec | 37 | 6 | 0 | 3 | 9 | 2 | 23 | 0.60 | 0.25 |  |
| JS-QUAL-PREFER-SPREAD | ai-confirm | eslint:prefer-spread | 33 | 7 | 0 | 5 | 13 | 3 | 12 | 0.62 | 0.28 |  |
| VUE-MIG-NO-DEPRECATED-DOLLAR-SCOPEDSLOTS-API | ai-confirm | eslint-plugin-vue:vue/no-deprecated-dollar-scopedslots-api | 11 | 0 | 0 | 5 | 0 | 3 | 3 | 0.62 | 1.00 |  |
| TS-QUAL-NO-UNNECESSARY-PARAMETER-PROPERTY-ASSIGNMENT | ai-confirm | typescript-eslint:@typescript-eslint/no-unnecessary-parameter-property-assignment | 45 | 0 | 0 | 12 | 8 | 7 | 18 | 0.63 | 0.60 |  |
| PY-MAINT-FUNCTION-NAMING | ai-confirm | ruff:N802 | 1 | 0 | 0 | 9 | 0 | 5 | 0 | 0.64 | 1.00 |  |
| GO-MOD-FMTAPPENDF | ai-confirm | govet:modernize | 1 | 0 | 0 | 11 | 0 | 6 | 0 | 0.65 | 1.00 |  |
| GO-MOD-ANY | ai-confirm | govet:modernize | 2 | 0 | 0 | 2 | 2 | 1 | 0 | 0.67 | 0.50 |  |
| GO-MOD-ERRORSASTYPE | ai-confirm | govet:modernize | 2 | 0 | 0 | 10 | 1 | 5 | 0 | 0.67 | 0.91 |  |
| GO-MOD-STRINGSBUILDER | ai-confirm | govet:modernize | 2 | 0 | 0 | 10 | 7 | 5 | 0 | 0.67 | 0.59 |  |
| GO-QUAL-VET-SIGCHANYZER | ai-confirm | govet:sigchanyzer | 1 | 0 | 0 | 2 | 2 | 1 | 0 | 0.67 | 0.50 |  |
| JS-QUAL-NEW-WRAPPER-001 | ai-confirm | eslint:no-new-wrappers | 11 | 0 | 3 | 4 | 0 | 2 | 2 | 0.67 | 1.00 |  |
| PY-MAINT-DEFAULTDICT-FACTORY-KEYWORD | ai-confirm | ruff:RUF026 | 1 | 0 | 0 | 14 | 0 | 7 | 0 | 0.67 | 1.00 |  |
| PY-MAINT-INIT-RETURNS-VALUE | ai-confirm | ruff:PLE0101 | 1 | 0 | 0 | 2 | 0 | 1 | 0 | 0.67 | 1.00 |  |
| PY-QUAL-TRY-EXCEPT-PASS | ai-confirm | ruff:S110 | 1 | 0 | 0 | 2 | 0 | 1 | 0 | 0.67 | 1.00 |  |
| PY-SEC-BIND-ALL-INTERFACES | ai-confirm | ruff:S104 | 1 | 0 | 0 | 6 | 0 | 3 | 0 | 0.67 | 1.00 |  |
| TS-QUAL-NO-IMPORT-TYPE-SIDE-EFFECTS | ai-confirm | typescript-eslint:@typescript-eslint/no-import-type-side-effects | 15 | 0 | 0 | 2 | 2 | 1 | 10 | 0.67 | 0.50 |  |
| VUE-QUAL-NO-LIFECYCLE-AFTER-AWAIT | ai-confirm | eslint-plugin-vue:vue/no-lifecycle-after-await | 12 | 1 | 0 | 2 | 1 | 1 | 8 | 0.67 | 0.67 |  |
| VUE-QUAL-VALID-ATTRIBUTE-NAME | ai-confirm | eslint-plugin-vue:vue/valid-attribute-name | 22 | 0 | 0 | 2 | 3 | 1 | 16 | 0.67 | 0.40 |  |
| PY-MAINT-IMMEDIATELY-RETURNED-VARIABLE | ai-confirm | ruff:RET504 | 1 | 0 | 0 | 11 | 4 | 5 | 0 | 0.69 | 0.73 |  |
| GO-MOD-RANGEINT | ai-confirm | govet:modernize | 2 | 0 | 0 | 10 | 32 | 4 | 1 | 0.71 | 0.24 |  |
| GO-QUAL-VET-UNMARSHAL | ai-confirm | govet:unmarshal | 2 | 0 | 0 | 5 | 11 | 2 | 0 | 0.71 | 0.31 |  |
| PY-MAINT-COMMENTED-OUT-CODE | ai-confirm | ruff:ERA001 | 1 | 0 | 0 | 8 | 11 | 3 | 0 | 0.73 | 0.42 |  |
| GO-QUAL-VET-ATOMIC | ai-confirm | govet:atomic | 2 | 0 | 0 | 3 | 9 | 1 | 0 | 0.75 | 0.25 |  |
| JS-QUAL-NO-IMPLICIT-COERCION | ai-confirm | eslint:no-implicit-coercion | 106 | 40 | 7 | 6 | 26 | 2 | 65 | 0.75 | 0.19 |  |
| JS-QUAL-NO-REGEX-SPACES | ai-confirm | eslint:no-regex-spaces | 73 | 8 | 1 | 15 | 13 | 5 | 39 | 0.75 | 0.54 |  |
| PY-MAINT-DICT-COMPREHENSION-CONSTANT-VALUE | ai-confirm | ruff:C420 | 3 | 0 | 0 | 9 | 5 | 3 | 0 | 0.75 | 0.64 |  |
| VUE-QUAL-NO-WATCH-AFTER-AWAIT | ai-confirm | eslint-plugin-vue:vue/no-watch-after-await | 14 | 0 | 0 | 3 | 0 | 1 | 10 | 0.75 | 1.00 |  |
| TS-QUAL-NO-DUPLICATE-ENUM-VALUES | ai-confirm | typescript-eslint:@typescript-eslint/no-duplicate-enum-values | 40 | 0 | 0 | 7 | 8 | 2 | 23 | 0.78 | 0.47 |  |
| TS-QUAL-PREFER-FUNCTION-TYPE | ai-confirm | typescript-eslint:@typescript-eslint/prefer-function-type | 23 | 1 | 0 | 7 | 11 | 2 | 3 | 0.78 | 0.39 |  |
| TS-QUAL-NO-NON-NULL-ASSERTED-NULLISH-COALESCING | ai-confirm | typescript-eslint:@typescript-eslint/no-non-null-asserted-nullish-coalescing | 33 | 0 | 0 | 15 | 0 | 4 | 14 | 0.79 | 1.00 |  |
| JS-QUAL-NO-CONTROL-REGEX | ai-confirm | eslint:no-control-regex | 49 | 1 | 4 | 4 | 13 | 1 | 27 | 0.80 | 0.24 |  |
| JS-QUAL-NO-DUPE-CLASS-MEMBERS | ai-confirm | eslint:no-dupe-class-members | 78 | 5 | 0 | 8 | 30 | 2 | 38 | 0.80 | 0.21 |  |
| PY-MAINT-COLLAPSIBLE-IF | ai-confirm | ruff:SIM102 | 1 | 0 | 0 | 12 | 2 | 3 | 0 | 0.80 | 0.86 |  |
| PY-MAINT-FROMKEYS-MUTABLE-VALUE | ai-confirm | ruff:RUF024 | 1 | 0 | 0 | 8 | 0 | 2 | 0 | 0.80 | 1.00 |  |
| PY-MAINT-OPEN-INVALID-MODE | ai-confirm | ruff:PLW1501 | 1 | 0 | 0 | 8 | 4 | 2 | 0 | 0.80 | 0.67 |  |
| VUE-QUAL-NO-SETUP-PROPS-REACTIVITY-LOSS | ai-confirm | eslint-plugin-vue:vue/no-setup-props-reactivity-loss | 44 | 0 | 0 | 4 | 21 | 1 | 18 | 0.80 | 0.16 |  |
| TS-QUAL-PREFER-INCLUDES | ai-confirm | typescript-eslint:@typescript-eslint/prefer-includes | 42 | 5 | 0 | 22 | 7 | 5 | 8 | 0.81 | 0.76 |  |
| GO-QUAL-VET-HTTPRESPONSE | ai-confirm | govet:httpresponse | 2 | 0 | 0 | 9 | 0 | 2 | 0 | 0.82 | 1.00 |  |
| GO-QUAL-VET-HOSTPORT | ai-confirm | govet:hostport | 1 | 0 | 0 | 5 | 4 | 1 | 0 | 0.83 | 0.56 |  |
| JS-QUAL-PARSEINT-001 | ai-confirm | eslint:radix | 77 | 18 | 1 | 5 | 30 | 1 | 40 | 0.83 | 0.14 |  |
| PY-MAINT-NESTED-LOOP-REUSES-VARIABLE | ai-confirm | ruff:PLW2901 | 1 | 0 | 0 | 5 | 21 | 1 | 0 | 0.83 | 0.19 |  |
| PY-QUAL-NONE-COMPARISON | ai-confirm | ruff:E711 | 1 | 0 | 0 | 5 | 4 | 1 | 0 | 0.83 | 0.56 |  |
| TS-QUAL-MAX-PARAMS | ai-confirm | typescript-eslint:@typescript-eslint/max-params | 12 | 11 | 0 | 5 | 0 | 1 | 6 | 0.83 | 1.00 |  |
| TS-QUAL-PREFER-LITERAL-ENUM-MEMBER | ai-confirm | typescript-eslint:@typescript-eslint/prefer-literal-enum-member | 22 | 11 | 0 | 5 | 7 | 1 | 9 | 0.83 | 0.42 |  |
| VUE-QUAL-NO-NEGATED-V-IF-CONDITION | ai-confirm | eslint-plugin-vue:vue/no-negated-v-if-condition | 22 | 0 | 0 | 5 | 3 | 1 | 13 | 0.83 | 0.62 |  |
| TS-QUAL-NO-ARRAY-DELETE | ai-confirm | typescript-eslint:@typescript-eslint/no-array-delete | 31 | 0 | 0 | 16 | 6 | 3 | 6 | 0.84 | 0.73 |  |
| JS-QUAL-PRESERVE-CAUGHT-ERROR | ai-confirm | eslint:preserve-caught-error | 54 | 79 | 0 | 11 | 27 | 2 | 14 | 0.85 | 0.29 |  |
| PY-QUAL-GETATTR-CONSTANT | ai-confirm | ruff:B009 | 1 | 0 | 0 | 17 | 3 | 3 | 0 | 0.85 | 0.85 |  |
| JS-QUAL-NO-FALLTHROUGH | ai-confirm | eslint:no-fallthrough | 59 | 28 | 0 | 6 | 11 | 1 | 41 | 0.86 | 0.35 |  |
| PY-MAINT-BLOCKING-OPEN-IN-ASYNC | ai-confirm | ruff:ASYNC230 | 1 | 0 | 0 | 6 | 5 | 1 | 0 | 0.86 | 0.55 |  |
| TS-QUAL-NO-DUPLICATE-TYPE-CONSTITUENTS | ai-confirm | typescript-eslint:@typescript-eslint/no-duplicate-type-constituents | 80 | 2 | 0 | 26 | 22 | 4 | 28 | 0.87 | 0.54 |  |
| GO-MOD-WAITGROUPGO | ai-confirm | govet:modernize | 3 | 0 | 0 | 7 | 13 | 1 | 0 | 0.88 | 0.35 |  |
| JS-QUAL-NO-EXTRA-BOOLEAN-CAST | ai-confirm | eslint:no-extra-boolean-cast | 238 | 275 | 12 | 21 | 186 | 3 | 16 | 0.88 | 0.10 |  |
| JS-QUAL-NO-USELESS-COMPUTED-KEY | ai-confirm | eslint:no-useless-computed-key | 76 | 21 | 8 | 7 | 47 | 1 | 13 | 0.88 | 0.13 |  |
| PY-MAINT-CATCH-ONLY-RETHROWS | ai-confirm | ruff:TRY203 | 1 | 0 | 0 | 7 | 5 | 1 | 0 | 0.88 | 0.58 |  |
| PY-MAINT-CLASS-NAMING | ai-confirm | ruff:N801 | 1 | 0 | 0 | 7 | 0 | 1 | 0 | 0.88 | 1.00 |  |
| JS-QUAL-NO-ALERT | ai-confirm | eslint:no-alert | 42 | 1 | 16 | 15 | 2 | 2 | 7 | 0.88 | 0.88 |  |
| JS-QUAL-PREFER-DESTRUCTURING | ai-confirm | eslint:prefer-destructuring | 59 | 48 | 0 | 30 | 7 | 4 | 18 | 0.88 | 0.81 |  |
| GO-QUAL-VET-UNUSEDRESULT | ai-confirm | govet:unusedresult | 3 | 0 | 0 | 8 | 11 | 1 | 1 | 0.89 | 0.42 |  |
| JS-QUAL-VALID-TYPEOF | ai-confirm | eslint:valid-typeof | 41 | 13 | 1 | 8 | 5 | 1 | 26 | 0.89 | 0.62 |  |
| PY-MAINT-LRU-CACHE-ON-METHOD | ai-confirm | ruff:B019 | 1 | 0 | 0 | 8 | 1 | 1 | 0 | 0.89 | 0.89 |  |
| PY-QUAL-CACHED-METHOD | ai-confirm | ruff:B019 | 1 | 0 | 0 | 8 | 1 | 1 | 0 | 0.89 | 0.89 |  |
| TS-QUAL-CONSISTENT-GENERIC-CONSTRUCTORS | ai-confirm | typescript-eslint:@typescript-eslint/consistent-generic-constructors | 46 | 37 | 0 | 8 | 11 | 1 | 26 | 0.89 | 0.42 |  |
| JS-QUAL-NO-EMPTY-CHARACTER-CLASS | ai-confirm | eslint:no-empty-character-class | 42 | 1 | 0 | 17 | 0 | 2 | 23 | 0.89 | 1.00 |  |
| TS-QUAL-NO-FLOATING-PROMISES | ai-confirm | typescript-eslint:@typescript-eslint/no-floating-promises | 106 | 89 | 0 | 9 | 57 | 1 | 39 | 0.90 | 0.14 |  |
| JS-QUAL-CLASS-METHODS-USE-THIS | ai-confirm | eslint:class-methods-use-this | 95 | 69 | 6 | 12 | 39 | 1 | 37 | 0.92 | 0.24 |  |
| PY-MAINT-STOPITERATION-IN-GENERATOR | ai-confirm | ruff:PLR1708 | 1 | 0 | 0 | 12 | 0 | 1 | 0 | 0.92 | 1.00 |  |
| TS-QUAL-DEFAULT-PARAM-LAST | ai-confirm | typescript-eslint:@typescript-eslint/default-param-last | 87 | 0 | 0 | 45 | 0 | 3 | 39 | 0.94 | 1.00 |  |
| TS-QUAL-NO-EMPTY-OBJECT-TYPE | ai-confirm | typescript-eslint:@typescript-eslint/no-empty-object-type | 28 | 14 | 0 | 19 | 3 | 1 | 5 | 0.95 | 0.86 |  |
| PY-QUAL-MUTABLE-DEFAULT | ai-confirm | ruff:B006 | 10 | 0 | 0 | 43 | 9 | 2 | 0 | 0.96 | 0.83 |  |
| CSS-QUAL-CALC-UNSPACED-OPERATOR | deterministic | stylelint:function-calc-no-unspaced-operator | 125 | 0 | 0 | 10 | 41 | 0 | 74 | 1.00 | 0.20 |  |
| CSS-QUAL-DOUBLE-SLASH-COMMENT | deterministic | stylelint:no-invalid-double-slash-comments | 11 | 0 | 1 | 7 | 0 | 0 | 3 | 1.00 | 1.00 |  |
| CSS-QUAL-DUPLICATE-DECLARATION | deterministic | stylelint:declaration-block-no-duplicate-properties | 40 | 0 | 0 | 3 | 26 | 0 | 11 | 1.00 | 0.10 |  |
| CSS-QUAL-DUPLICATE-FONT-FAMILY | deterministic | stylelint:font-family-no-duplicate-names | 11 | 0 | 0 | 3 | 3 | 0 | 5 | 1.00 | 0.50 |  |
| CSS-QUAL-DUPLICATE-SELECTOR | deterministic | stylelint:no-duplicate-selectors | 43 | 0 | 1 | 5 | 23 | 0 | 14 | 1.00 | 0.18 |  |
| CSS-QUAL-EMPTY-RULE | deterministic | stylelint:block-no-empty | 30 | 0 | 1 | 8 | 5 | 0 | 16 | 1.00 | 0.62 |  |
| CSS-QUAL-FONT-FAMILY-WITHOUT-GENERIC | deterministic | stylelint:font-family-no-missing-generic-family-keyword | 58 | 0 | 0 | 4 | 8 | 0 | 46 | 1.00 | 0.33 |  |
| CSS-QUAL-GRADIENT-LEGACY-DIRECTION | deterministic | stylelint:function-linear-gradient-no-nonstandard-direction | 62 | 0 | 0 | 8 | 18 | 0 | 36 | 1.00 | 0.31 |  |
| CSS-QUAL-IMPORTANT | ai-confirm | stylelint:declaration-no-important | 4 | 0 | 0 | 2 | 1 | 0 | 1 | 1.00 | 0.67 |  |
| CSS-QUAL-IMPORTANT-IN-KEYFRAMES | deterministic | stylelint:keyframe-declaration-no-important | 13 | 0 | 0 | 3 | 4 | 0 | 6 | 1.00 | 0.43 |  |
| CSS-QUAL-INVALID-HEX-COLOR | deterministic | stylelint:color-no-invalid-hex | 15 | 0 | 0 | 3 | 1 | 0 | 11 | 1.00 | 0.75 |  |
| CSS-QUAL-OVERRIDDEN-DECLARATION | ai-confirm | stylelint:declaration-block-no-duplicate-properties | 40 | 0 | 0 | 27 | 2 | 0 | 11 | 1.00 | 0.93 |  |
| CSS-QUAL-SHORTHAND-OVERRIDES-LONGHAND | deterministic | stylelint:declaration-block-no-shorthand-property-overrides | 32 | 0 | 0 | 17 | 3 | 0 | 12 | 1.00 | 0.85 |  |
| CSS-QUAL-UNKNOWN-AT-RULE | ai-confirm | stylelint:at-rule-no-unknown | 32 | 0 | 0 | 1 | 0 | 0 | 31 | 1.00 | 1.00 |  |
| CSS-QUAL-UNKNOWN-PROPERTY | deterministic | stylelint:property-no-unknown | 19 | 0 | 0 | 5 | 1 | 0 | 13 | 1.00 | 0.83 |  |
| CSS-QUAL-UNKNOWN-PSEUDO | deterministic | stylelint:selector-pseudo-class-no-unknown | 73 | 0 | 1 | 10 | 10 | 0 | 52 | 1.00 | 0.50 |  |
| CSS-QUAL-UNKNOWN-UNIT | deterministic | stylelint:unit-no-unknown | 102 | 0 | 0 | 19 | 10 | 0 | 73 | 1.00 | 0.66 |  |
| CSS-QUAL-UNNEEDED-VENDOR-PREFIX | deterministic | stylelint:property-no-vendor-prefix | 25 | 0 | 0 | 6 | 9 | 0 | 10 | 1.00 | 0.40 |  |
| DOCKER-MIG-MAINTAINER-DEPRECATED | deterministic | hadolint:DL4000 | 4 | 0 | 0 | 3 | 0 | 0 | 1 | 1.00 | 1.00 |  |
| DOCKER-QUAL-ADD-LOCAL-FILE | ai-confirm | hadolint:DL3020 | 11 | 0 | 0 | 3 | 0 | 0 | 8 | 1.00 | 1.00 |  |
| DOCKER-QUAL-APT-NO-INSTALL-RECOMMENDS | ai-confirm | hadolint:DL3015 | 4 | 0 | 0 | 2 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| DOCKER-QUAL-COPY-FROM-INDEX | deterministic | hadolint:DL3022 | 3 | 4 | 0 | 1 | 1 | 0 | 1 | 1.00 | 0.50 |  |
| DOCKER-QUAL-LATEST-TAG | ai-confirm | hadolint:DL3006 | 6 | 2 | 0 | 2 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| DOCKER-QUAL-SUDO | deterministic | hadolint:DL3004 | 3 | 0 | 0 | 2 | 0 | 0 | 1 | 1.00 | 1.00 |  |
| DOCKER-QUAL-WORKDIR-RELATIVE-PATH | deterministic | hadolint:DL3000 | 12 | 0 | 0 | 3 | 0 | 0 | 9 | 1.00 | 1.00 |  |
| GO-MIG-IOUTIL | deterministic | staticcheck:SA1019 | 16 | 0 | 0 | 1 | 27 | 0 | 9 | 1.00 | 0.04 |  |
| GO-MOD-NEWEXPR | deterministic | govet:modernize | 2 | 0 | 0 | 5 | 9 | 0 | 1 | 1.00 | 0.36 |  |
| GO-MOD-PLUSBUILD | deterministic | govet:modernize | 2 | 0 | 0 | 1 | 0 | 0 | 1 | 1.00 | 1.00 |  |
| GO-MOD-REFLECTTYPEFOR | ai-confirm | govet:modernize | 1 | 0 | 0 | 6 | 14 | 0 | 0 | 1.00 | 0.30 |  |
| GO-MOD-SLICESCONTAINS | deterministic | govet:modernize | 1 | 0 | 0 | 1 | 13 | 0 | 0 | 1.00 | 0.07 |  |
| GO-MOD-STRINGSCUTPREFIX | deterministic | govet:modernize | 4 | 0 | 0 | 12 | 16 | 0 | 0 | 1.00 | 0.43 |  |
| GO-MOD-STRINGSSEQ | deterministic | govet:modernize | 3 | 0 | 0 | 1 | 4 | 0 | 2 | 1.00 | 0.20 |  |
| GO-QUAL-VET-BOOLS | deterministic | govet:bools | 2 | 0 | 0 | 16 | 35 | 0 | 0 | 1.00 | 0.31 |  |
| GO-QUAL-VET-DEFERS | deterministic | govet:defers | 1 | 0 | 0 | 5 | 2 | 0 | 0 | 1.00 | 0.71 |  |
| GO-QUAL-VET-ERRORSAS | ai-confirm | govet:errorsas | 2 | 0 | 0 | 6 | 2 | 0 | 0 | 1.00 | 0.75 |  |
| GO-QUAL-VET-LOSTCANCEL | ai-confirm | govet:lostcancel | 3 | 0 | 0 | 2 | 23 | 0 | 0 | 1.00 | 0.08 |  |
| GO-QUAL-VET-TESTINGGOROUTINE | deterministic | govet:testinggoroutine | 3 | 0 | 0 | 11 | 28 | 0 | 1 | 1.00 | 0.28 |  |
| GO-QUAL-VET-UNREACHABLE | deterministic | govet:unreachable | 1 | 0 | 0 | 32 | 126 | 0 | 0 | 1.00 | 0.20 |  |
| GO-QUAL-VET-WAITGROUP-ADD-IN-GOROUTINE | ai-confirm | govet:waitgroup | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| GRAPHQL-QUAL-NO-ANONYMOUS-OPERATIONS | deterministic | graphql-eslint:@graphql-eslint/no-anonymous-operations | 6 | 0 | 0 | 3 | 0 | 0 | 3 | 1.00 | 1.00 |  |
| GRAPHQL-QUAL-NO-DUPLICATE-FIELDS | deterministic | graphql-eslint:@graphql-eslint/no-duplicate-fields | 4 | 0 | 0 | 3 | 1 | 0 | 0 | 1.00 | 0.75 |  |
| GRAPHQL-QUAL-ONEOF-NON-NULL-FIELD | ai-confirm | graphql-eslint:@graphql-eslint/require-nullable-fields-with-oneof | 4 | 2 | 0 | 1 | 1 | 0 | 2 | 1.00 | 0.50 |  |
| GRAPHQL-QUAL-RELAY-CONNECTION-FIELDS | deterministic | graphql-eslint:@graphql-eslint/relay-connection-types | 10 | 2 | 0 | 3 | 3 | 0 | 4 | 1.00 | 0.50 |  |
| GRAPHQL-QUAL-REQUIRE-DEPRECATION-DATE | ai-confirm | graphql-eslint:@graphql-eslint/require-deprecation-date | 6 | 4 | 0 | 1 | 3 | 0 | 2 | 1.00 | 0.25 |  |
| GRAPHQL-QUAL-REQUIRE-DEPRECATION-REASON | ai-confirm | graphql-eslint:@graphql-eslint/require-deprecation-reason | 3 | 2 | 0 | 1 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| HTML-A11Y-ARIA-INVALID-ATTRIBUTE | deterministic | axe:aria-valid-attr | 1 | 0 | 0 | 8 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| HTML-A11Y-ARIA-INVALID-ROLE | deterministic | axe:aria-roles | 1 | 0 | 0 | 13 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| HTML-A11Y-ARIA-LABEL-ON-GENERIC | deterministic | axe:aria-prohibited-attr | 1 | 0 | 0 | 7 | 88 | 0 | 0 | 1.00 | 0.07 |  |
| HTML-A11Y-BUTTON-WITHOUT-NAME | deterministic | axe:button-name | 1 | 0 | 0 | 5 | 4 | 0 | 0 | 1.00 | 0.56 |  |
| HTML-A11Y-CONTROL-WITHOUT-LABEL | ai-confirm | axe:label | 1 | 0 | 0 | 2 | 12 | 0 | 0 | 1.00 | 0.14 |  |
| HTML-A11Y-EMPTY-HEADING | ai-confirm | axe:empty-heading | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| HTML-A11Y-HEADING-SKIPPED-LEVEL | ai-confirm | axe:heading-order | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 1.00 | 0.50 |  |
| HTML-A11Y-INPUT-IMAGE-WITHOUT-ALT | deterministic | axe:input-image-alt | 1 | 0 | 0 | 3 | 3 | 0 | 0 | 1.00 | 0.50 |  |
| HTML-A11Y-LANG-INVALID | deterministic | axe:valid-lang | 1 | 0 | 0 | 3 | 1 | 0 | 0 | 1.00 | 0.75 |  |
| HTML-A11Y-MARQUEE-OR-BLINK | ai-confirm | axe:marquee | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| HTML-A11Y-ROLE-IMG-WITHOUT-NAME | ai-confirm | axe:role-img-alt | 1 | 0 | 0 | 2 | 2 | 0 | 0 | 1.00 | 0.50 |  |
| HTML-A11Y-TH-INVALID-SCOPE | ai-confirm | axe:scope-attr-valid | 1 | 0 | 0 | 1 | 2 | 0 | 0 | 1.00 | 0.33 |  |
| JS-A11Y-AMBIGUOUS-LINK-TEXT | deterministic | jsx-a11y:anchor-ambiguous-text | 30 | 9 | 0 | 8 | 17 | 0 | 5 | 1.00 | 0.32 |  |
| JS-A11Y-ARIA-INVALID-ATTRIBUTE | deterministic | jsx-a11y:aria-props | 11 | 0 | 0 | 3 | 0 | 0 | 8 | 1.00 | 1.00 |  |
| JS-A11Y-ARIA-INVALID-ROLE | deterministic | jsx-a11y:aria-role | 24 | 12 | 0 | 3 | 9 | 0 | 12 | 1.00 | 0.25 |  |
| JS-A11Y-ARIA-REQUIRED-ATTRIBUTE | deterministic | jsx-a11y:role-has-required-aria-props | 30 | 2 | 0 | 16 | 1 | 0 | 13 | 1.00 | 0.94 |  |
| JS-A11Y-AUTOCOMPLETE-INVALID | ai-confirm | jsx-a11y:autocomplete-valid | 22 | 4 | 0 | 2 | 2 | 0 | 18 | 1.00 | 0.50 |  |
| JS-A11Y-CONTROL-WITHOUT-LABEL | ai-confirm | jsx-a11y:control-has-associated-label | 3 | 0 | 0 | 1 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| JS-A11Y-EMPTY-HEADING | ai-confirm | jsx-a11y:heading-has-content | 19 | 13 | 0 | 2 | 2 | 0 | 15 | 1.00 | 0.50 |  |
| JS-A11Y-IMG-REDUNDANT-ALT | deterministic | jsx-a11y:img-redundant-alt | 50 | 9 | 0 | 13 | 6 | 0 | 31 | 1.00 | 0.68 |  |
| JS-A11Y-MOUSE-WITHOUT-KEYBOARD | ai-confirm | jsx-a11y:mouse-events-have-key-events | 26 | 13 | 0 | 1 | 5 | 0 | 20 | 1.00 | 0.17 |  |
| JS-MIG-NO-ITERATOR | deterministic | eslint:no-iterator | 9 | 0 | 2 | 2 | 1 | 0 | 4 | 1.00 | 0.67 |  |
| JS-QUAL-ARRAY-CALLBACK-RETURN | ai-confirm | eslint:array-callback-return | 132 | 109 | 7 | 38 | 37 | 0 | 50 | 1.00 | 0.51 |  |
| JS-QUAL-ARROW-BODY-STYLE | deterministic | eslint:arrow-body-style | 28 | 60 | 0 | 17 | 0 | 0 | 11 | 1.00 | 1.00 |  |
| JS-QUAL-AWAIT-LOOP-001 | ai-confirm | eslint:no-await-in-loop | 37 | 18 | 12 | 3 | 3 | 0 | 19 | 1.00 | 0.50 |  |
| JS-QUAL-CAMELCASE | ai-confirm | eslint:camelcase | 91 | 121 | 44 | 1 | 2 | 0 | 44 | 1.00 | 0.33 |  |
| JS-QUAL-CURLY | ai-confirm | eslint:curly | 27 | 197 | 15 | 5 | 0 | 0 | 7 | 1.00 | 1.00 |  |
| JS-QUAL-DEFAULT-CASE | ai-confirm | eslint:default-case | 16 | 7 | 0 | 1 | 2 | 0 | 13 | 1.00 | 0.33 |  |
| JS-QUAL-DEFAULT-CASE-LAST | deterministic | eslint:default-case-last | 37 | 0 | 0 | 14 | 0 | 0 | 23 | 1.00 | 1.00 |  |
| JS-QUAL-DEFAULT-PARAM-LAST | deterministic | eslint:default-param-last | 96 | 0 | 28 | 13 | 0 | 0 | 55 | 1.00 | 1.00 |  |
| JS-QUAL-DOT-NOTATION | deterministic | eslint:dot-notation | 44 | 26 | 6 | 24 | 0 | 0 | 14 | 1.00 | 1.00 |  |
| JS-QUAL-FOR-DIRECTION | deterministic | eslint:for-direction | 100 | 18 | 0 | 8 | 24 | 0 | 68 | 1.00 | 0.25 |  |
| JS-QUAL-FUNC-NAMES | ai-confirm | eslint:func-names | 14 | 101 | 0 | 1 | 5 | 0 | 8 | 1.00 | 0.17 |  |
| JS-QUAL-GETTER-RETURN | deterministic | eslint:getter-return | 81 | 21 | 0 | 5 | 29 | 0 | 47 | 1.00 | 0.15 |  |
| JS-QUAL-GUARD-FOR-IN | ai-confirm | eslint:guard-for-in | 12 | 0 | 0 | 1 | 5 | 0 | 6 | 1.00 | 0.17 |  |
| JS-QUAL-LOGICAL-ASSIGNMENT-OPERATORS | deterministic | eslint:logical-assignment-operators | 114 | 238 | 42 | 28 | 1 | 0 | 43 | 1.00 | 0.97 |  |
| JS-QUAL-NEW-CAP | deterministic | eslint:new-cap | 100 | 48 | 5 | 9 | 34 | 0 | 52 | 1.00 | 0.21 |  |
| JS-QUAL-NO-ARRAY-CONSTRUCTOR | deterministic | eslint:no-array-constructor | 78 | 9 | 38 | 9 | 0 | 0 | 31 | 1.00 | 1.00 |  |
| JS-QUAL-NO-BITWISE | ai-confirm | eslint:no-bitwise | 22 | 4 | 0 | 1 | 13 | 0 | 8 | 1.00 | 0.07 |  |
| JS-QUAL-NO-CASE-DECLARATIONS | deterministic | eslint:no-case-declarations | 19 | 1 | 4 | 9 | 0 | 0 | 6 | 1.00 | 1.00 |  |
| JS-QUAL-NO-CLASS-ASSIGN | ai-confirm | eslint:no-class-assign | 18 | 1 | 5 | 2 | 0 | 0 | 11 | 1.00 | 1.00 |  |
| JS-QUAL-NO-COMPARE-NEG-ZERO | deterministic | eslint:no-compare-neg-zero | 50 | 2 | 0 | 15 | 8 | 0 | 27 | 1.00 | 0.65 |  |
| JS-QUAL-NO-COND-ASSIGN | ai-confirm | eslint:no-cond-assign | 20 | 25 | 0 | 3 | 4 | 0 | 13 | 1.00 | 0.43 |  |
| JS-QUAL-NO-CONSOLE | ai-confirm | eslint:no-console | 18 | 33 | 0 | 13 | 3 | 0 | 2 | 1.00 | 0.81 |  |
| JS-QUAL-NO-CONST-ASSIGN | deterministic | eslint:no-const-assign | 33 | 1 | 0 | 4 | 13 | 0 | 16 | 1.00 | 0.24 |  |
| JS-QUAL-NO-CONSTANT-BINARY-EXPRESSION | deterministic | eslint:no-constant-binary-expression | 283 | 45 | 219 | 14 | 0 | 0 | 50 | 1.00 | 1.00 |  |
| JS-QUAL-NO-CONSTANT-CONDITION | deterministic | eslint:no-constant-condition | 281 | 49 | 2 | 16 | 117 | 0 | 146 | 1.00 | 0.12 |  |
| JS-QUAL-NO-CONSTRUCTOR-RETURN | ai-confirm | eslint:no-constructor-return | 20 | 0 | 1 | 1 | 0 | 0 | 18 | 1.00 | 1.00 |  |
| JS-QUAL-NO-DEBUGGER | ai-confirm | eslint:no-debugger | 2 | 0 | 0 | 1 | 0 | 0 | 1 | 1.00 | 1.00 |  |
| JS-QUAL-NO-DELETE-VAR | ai-confirm | eslint:no-delete-var | 2 | 0 | 0 | 1 | 0 | 0 | 1 | 1.00 | 1.00 |  |
| JS-QUAL-NO-DUPE-ELSE-IF | deterministic | eslint:no-dupe-else-if | 89 | 13 | 0 | 15 | 40 | 0 | 34 | 1.00 | 0.27 |  |
| JS-QUAL-NO-DUPE-KEYS | deterministic | eslint:no-dupe-keys | 50 | 0 | 17 | 3 | 2 | 0 | 28 | 1.00 | 0.60 |  |
| JS-QUAL-NO-DUPLICATE-CASE | deterministic | eslint:no-duplicate-case | 29 | 0 | 0 | 11 | 6 | 0 | 12 | 1.00 | 0.65 |  |
| JS-QUAL-NO-DUPLICATE-IMPORTS | ai-confirm | eslint:no-duplicate-imports | 31 | 54 | 9 | 7 | 0 | 0 | 15 | 1.00 | 1.00 |  |
| JS-QUAL-NO-ELSE-RETURN | deterministic | eslint:no-else-return | 83 | 9 | 17 | 59 | 0 | 0 | 7 | 1.00 | 1.00 |  |
| JS-QUAL-NO-EMPTY | ai-confirm | eslint:no-empty | 30 | 5 | 0 | 5 | 4 | 0 | 21 | 1.00 | 0.56 |  |
| JS-QUAL-NO-EMPTY-FUNCTION | deterministic | eslint:no-empty-function | 10 | 1 | 1 | 3 | 1 | 0 | 5 | 1.00 | 0.75 |  |
| JS-QUAL-NO-EMPTY-PATTERN | ai-confirm | eslint:no-empty-pattern | 15 | 16 | 7 | 2 | 0 | 0 | 6 | 1.00 | 1.00 |  |
| JS-QUAL-NO-EMPTY-STATIC-BLOCK | deterministic | eslint:no-empty-static-block | 10 | 0 | 0 | 6 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| JS-QUAL-NO-EQ-NULL | ai-confirm | eslint:no-eq-null | 5 | 0 | 0 | 2 | 1 | 0 | 2 | 1.00 | 0.67 |  |
| JS-QUAL-NO-EX-ASSIGN | ai-confirm | eslint:no-ex-assign | 8 | 0 | 3 | 2 | 0 | 0 | 3 | 1.00 | 1.00 |  |
| JS-QUAL-NO-EXTEND-NATIVE | deterministic | eslint:no-extend-native | 38 | 6 | 8 | 3 | 11 | 0 | 16 | 1.00 | 0.21 |  |
| JS-QUAL-NO-EXTRA-BIND | ai-confirm | eslint:no-extra-bind | 49 | 5 | 2 | 2 | 32 | 0 | 13 | 1.00 | 0.06 |  |
| JS-QUAL-NO-FUNC-ASSIGN | ai-confirm | eslint:no-func-assign | 15 | 0 | 4 | 1 | 3 | 0 | 7 | 1.00 | 0.25 |  |
| JS-QUAL-NO-GLOBAL-ASSIGN | deterministic | eslint:no-global-assign | 17 | 2 | 8 | 2 | 0 | 0 | 7 | 1.00 | 1.00 |  |
| JS-QUAL-NO-IMPORT-ASSIGN | deterministic | eslint:no-import-assign | 116 | 1 | 53 | 3 | 3 | 0 | 57 | 1.00 | 0.50 |  |
| JS-QUAL-NO-LABELS | deterministic | eslint:no-labels | 13 | 20 | 0 | 9 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| JS-QUAL-NO-LONE-BLOCKS | deterministic | eslint:no-lone-blocks | 48 | 6 | 10 | 6 | 11 | 0 | 21 | 1.00 | 0.35 |  |
| JS-QUAL-NO-LONELY-IF | deterministic | eslint:no-lonely-if | 17 | 0 | 0 | 12 | 2 | 0 | 3 | 1.00 | 0.86 |  |
| JS-QUAL-NO-LOSS-OF-PRECISION | deterministic | eslint:no-loss-of-precision | 141 | 1 | 31 | 3 | 19 | 0 | 88 | 1.00 | 0.14 |  |
| JS-QUAL-NO-MULTI-ASSIGN | deterministic | eslint:no-multi-assign | 24 | 7 | 0 | 12 | 1 | 0 | 11 | 1.00 | 0.92 |  |
| JS-QUAL-NO-MULTI-STR | ai-confirm | eslint:no-multi-str | 7 | 0 | 0 | 2 | 3 | 0 | 2 | 1.00 | 0.40 |  |
| JS-QUAL-NO-NESTED-TERNARY | ai-confirm | eslint:no-nested-ternary | 4 | 0 | 0 | 2 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| JS-QUAL-NO-NEW | ai-confirm | eslint:no-new | 3 | 0 | 0 | 1 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| JS-QUAL-NO-NONOCTAL-DECIMAL-ESCAPE | deterministic | eslint:no-nonoctal-decimal-escape | 84 | 6 | 11 | 44 | 0 | 0 | 29 | 1.00 | 1.00 |  |
| JS-QUAL-NO-OBJ-CALLS | deterministic | eslint:no-obj-calls | 139 | 3 | 42 | 26 | 24 | 0 | 47 | 1.00 | 0.52 |  |
| JS-QUAL-NO-OBJECT-CONSTRUCTOR | ai-confirm | eslint:no-object-constructor | 12 | 2 | 7 | 1 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| JS-QUAL-NO-OCTAL | deterministic | eslint:no-octal | 17 | 0 | 8 | 3 | 0 | 0 | 6 | 1.00 | 1.00 |  |
| JS-QUAL-NO-OCTAL-ESCAPE | deterministic | eslint:no-octal-escape | 94 | 2 | 5 | 60 | 0 | 0 | 29 | 1.00 | 1.00 |  |
| JS-QUAL-NO-PARAM-REASSIGN | ai-confirm | eslint:no-param-reassign | 31 | 47 | 7 | 1 | 10 | 0 | 13 | 1.00 | 0.09 |  |
| JS-QUAL-NO-PLUSPLUS | ai-confirm | eslint:no-plusplus | 5 | 20 | 0 | 2 | 2 | 0 | 1 | 1.00 | 0.50 |  |
| JS-QUAL-NO-PROMISE-EXECUTOR-RETURN | ai-confirm | eslint:no-promise-executor-return | 103 | 53 | 28 | 14 | 0 | 0 | 61 | 1.00 | 1.00 |  |
| JS-QUAL-NO-PROTOTYPE-BUILTINS | ai-confirm | eslint:no-prototype-builtins | 47 | 2 | 1 | 13 | 6 | 0 | 27 | 1.00 | 0.68 |  |
| JS-QUAL-NO-RETURN-ASSIGN | deterministic | eslint:no-return-assign | 19 | 11 | 0 | 11 | 0 | 0 | 8 | 1.00 | 1.00 |  |
| JS-QUAL-NO-SELF-ASSIGN | deterministic | eslint:no-self-assign | 63 | 26 | 14 | 19 | 4 | 0 | 26 | 1.00 | 0.83 |  |
| JS-QUAL-NO-SELF-COMPARE | ai-confirm | eslint:no-self-compare | 21 | 0 | 0 | 14 | 1 | 0 | 6 | 1.00 | 0.93 |  |
| JS-QUAL-NO-SEQUENCES | deterministic | eslint:no-sequences | 28 | 19 | 8 | 4 | 0 | 0 | 16 | 1.00 | 1.00 |  |
| JS-QUAL-NO-SETTER-RETURN | deterministic | eslint:no-setter-return | 164 | 45 | 27 | 27 | 2 | 0 | 108 | 1.00 | 0.93 |  |
| JS-QUAL-NO-SHADOW-RESTRICTED-NAMES | deterministic | eslint:no-shadow-restricted-names | 41 | 3 | 11 | 5 | 10 | 0 | 15 | 1.00 | 0.33 |  |
| JS-QUAL-NO-SPARSE-ARRAYS | ai-confirm | eslint:no-sparse-arrays | 6 | 0 | 0 | 4 | 1 | 0 | 1 | 1.00 | 0.80 |  |
| JS-QUAL-NO-TEMPLATE-CURLY-IN-STRING | deterministic | eslint:no-template-curly-in-string | 22 | 0 | 0 | 7 | 0 | 0 | 15 | 1.00 | 1.00 |  |
| JS-QUAL-NO-UNASSIGNED-VARS | ai-confirm | eslint:no-unassigned-vars | 23 | 0 | 9 | 2 | 0 | 0 | 12 | 1.00 | 1.00 |  |
| JS-QUAL-NO-UNDEF-INIT | deterministic | eslint:no-undef-init | 28 | 2 | 2 | 15 | 4 | 0 | 7 | 1.00 | 0.79 |  |
| JS-QUAL-NO-UNDERSCORE-DANGLE | ai-confirm | eslint:no-underscore-dangle | 45 | 72 | 1 | 2 | 6 | 0 | 36 | 1.00 | 0.25 |  |
| JS-QUAL-NO-UNNEEDED-TERNARY | deterministic | eslint:no-unneeded-ternary | 26 | 22 | 0 | 11 | 2 | 0 | 13 | 1.00 | 0.85 |  |
| JS-QUAL-NO-UNREACHABLE | deterministic | eslint:no-unreachable | 70 | 2 | 22 | 12 | 8 | 0 | 28 | 1.00 | 0.60 |  |
| JS-QUAL-NO-UNSAFE-FINALLY | deterministic | eslint:no-unsafe-finally | 30 | 0 | 0 | 6 | 10 | 0 | 14 | 1.00 | 0.38 |  |
| JS-QUAL-NO-UNSAFE-NEGATION | deterministic | eslint:no-unsafe-negation | 18 | 12 | 0 | 6 | 0 | 0 | 12 | 1.00 | 1.00 |  |
| JS-QUAL-NO-UNUSED-EXPRESSIONS | deterministic | eslint:no-unused-expressions | 86 | 42 | 8 | 17 | 25 | 0 | 36 | 1.00 | 0.40 |  |
| JS-QUAL-NO-UNUSED-PRIVATE-CLASS-MEMBERS | deterministic | eslint:no-unused-private-class-members | 61 | 6 | 0 | 20 | 21 | 0 | 20 | 1.00 | 0.49 |  |
| JS-QUAL-NO-USELESS-CALL | deterministic | eslint:no-useless-call | 44 | 9 | 0 | 4 | 21 | 0 | 19 | 1.00 | 0.16 |  |
| JS-QUAL-NO-USELESS-CATCH | deterministic | eslint:no-useless-catch | 16 | 0 | 0 | 3 | 2 | 0 | 11 | 1.00 | 0.60 |  |
| JS-QUAL-NO-USELESS-CONCAT | deterministic | eslint:no-useless-concat | 20 | 1 | 3 | 3 | 2 | 0 | 12 | 1.00 | 0.60 |  |
| JS-QUAL-NO-USELESS-CONSTRUCTOR | deterministic | eslint:no-useless-constructor | 57 | 1 | 10 | 14 | 0 | 0 | 33 | 1.00 | 1.00 |  |
| JS-QUAL-NO-USELESS-ESCAPE | deterministic | eslint:no-useless-escape | 235 | 72 | 52 | 1 | 29 | 0 | 153 | 1.00 | 0.03 |  |
| JS-QUAL-NO-USELESS-RENAME | deterministic | eslint:no-useless-rename | 150 | 16 | 57 | 43 | 7 | 0 | 43 | 1.00 | 0.86 |  |
| JS-QUAL-NO-VOID | deterministic | eslint:no-void | 7 | 5 | 0 | 3 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| JS-QUAL-OBJECT-SHORTHAND | deterministic | eslint:object-shorthand | 112 | 208 | 28 | 33 | 0 | 0 | 51 | 1.00 | 1.00 |  |
| JS-QUAL-OPERATOR-ASSIGNMENT | deterministic | eslint:operator-assignment | 64 | 57 | 0 | 6 | 20 | 0 | 38 | 1.00 | 0.23 |  |
| JS-QUAL-PREFER-ARROW-CALLBACK | deterministic | eslint:prefer-arrow-callback | 110 | 14 | 39 | 30 | 0 | 0 | 41 | 1.00 | 1.00 |  |
| JS-QUAL-PREFER-NAMED-CAPTURE-GROUP | deterministic | eslint:prefer-named-capture-group | 57 | 6 | 18 | 8 | 3 | 0 | 28 | 1.00 | 0.73 |  |
| JS-QUAL-PREFER-NUMERIC-LITERALS | deterministic | eslint:prefer-numeric-literals | 91 | 5 | 5 | 25 | 32 | 0 | 29 | 1.00 | 0.44 |  |
| JS-QUAL-PREFER-OBJECT-SPREAD | deterministic | eslint:prefer-object-spread | 107 | 18 | 1 | 34 | 33 | 0 | 39 | 1.00 | 0.51 |  |
| JS-QUAL-PREFER-REGEX-LITERALS | deterministic | eslint:prefer-regex-literals | 221 | 40 | 73 | 81 | 5 | 0 | 62 | 1.00 | 0.94 |  |
| JS-QUAL-PREFER-REST-PARAMS | deterministic | eslint:prefer-rest-params | 11 | 1 | 3 | 3 | 0 | 0 | 5 | 1.00 | 1.00 |  |
| JS-QUAL-PREFER-TEMPLATE | deterministic | eslint:prefer-template | 87 | 6 | 47 | 31 | 0 | 0 | 9 | 1.00 | 1.00 |  |
| JS-QUAL-PROMISE-EXEC-001 | deterministic | eslint:no-async-promise-executor | 11 | 0 | 7 | 2 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| JS-QUAL-REQUIRE-ATOMIC-UPDATES | ai-confirm | eslint:require-atomic-updates | 55 | 18 | 23 | 10 | 0 | 0 | 22 | 1.00 | 1.00 |  |
| JS-QUAL-REQUIRE-AWAIT | deterministic | eslint:require-await | 39 | 6 | 6 | 15 | 0 | 0 | 18 | 1.00 | 1.00 |  |
| JS-QUAL-REQUIRE-UNICODE-REGEXP | deterministic | eslint:require-unicode-regexp | 60 | 20 | 21 | 3 | 1 | 0 | 35 | 1.00 | 0.75 |  |
| JS-QUAL-REQUIRE-YIELD | ai-confirm | eslint:require-yield | 15 | 0 | 4 | 2 | 0 | 0 | 9 | 1.00 | 1.00 |  |
| JS-QUAL-SYMBOL-DESCRIPTION | ai-confirm | eslint:symbol-description | 8 | 2 | 4 | 2 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| JS-QUAL-THROW-LITERAL-001 | deterministic | eslint:no-throw-literal | 42 | 25 | 0 | 3 | 14 | 0 | 25 | 1.00 | 0.18 |  |
| JS-QUAL-USE-ISNAN | deterministic | eslint:use-isnan | 87 | 162 | 1 | 18 | 27 | 0 | 41 | 1.00 | 0.40 |  |
| JS-QUAL-VAR-001 | deterministic | eslint:no-var | 77 | 14 | 9 | 61 | 0 | 0 | 7 | 1.00 | 1.00 |  |
| JS-SEC-EVAL-001 | deterministic | eslint:no-eval | 86 | 34 | 28 | 3 | 10 | 0 | 45 | 1.00 | 0.23 |  |
| JS-SEC-IMPLIED-EVAL-001 | deterministic | eslint:no-implied-eval | 175 | 16 | 76 | 4 | 4 | 0 | 91 | 1.00 | 0.50 |  |
| JS-SEC-NO-SCRIPT-URL | deterministic | eslint:no-script-url | 10 | 0 | 2 | 2 | 0 | 0 | 6 | 1.00 | 1.00 |  |
| PY-MAINT-ALL-WITH-NON-STRING | ai-confirm | ruff:PLE0604 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 1.00 | 0.50 |  |
| PY-MAINT-BLOCKING-HTTP-IN-ASYNC | deterministic | ruff:ASYNC210 | 1 | 0 | 0 | 13 | 10 | 0 | 0 | 1.00 | 0.57 |  |
| PY-MAINT-BLOCKING-SLEEP-IN-ASYNC | ai-confirm | ruff:ASYNC251 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-MAINT-BLOCKING-SUBPROCESS-IN-ASYNC | deterministic | ruff:ASYNC221 | 1 | 0 | 0 | 8 | 16 | 0 | 0 | 1.00 | 0.33 |  |
| PY-MAINT-DEEP-NESTING | deterministic | ruff:PLR1702 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-MAINT-DICT-COMPREHENSION-STATIC-KEY | deterministic | ruff:B035 | 1 | 0 | 0 | 3 | 5 | 0 | 0 | 1.00 | 0.38 |  |
| PY-MAINT-DUPLICATE-BRANCH | ai-confirm | ruff:SIM114 | 1 | 0 | 0 | 5 | 13 | 0 | 0 | 1.00 | 0.28 |  |
| PY-MAINT-FIXME-COMMENT | ai-confirm | ruff:FIX001 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-MAINT-GENERIC-EXCEPTION-THROWN | deterministic | ruff:TRY002 | 1 | 0 | 0 | 4 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-MAINT-IDENTICAL-OPERANDS | ai-confirm | ruff:PLR0124 | 1 | 0 | 0 | 5 | 7 | 0 | 0 | 1.00 | 0.42 |  |
| PY-MAINT-LIST-FOR-FIRST-ITEM | ai-confirm | ruff:RUF015 | 1 | 0 | 0 | 8 | 12 | 0 | 0 | 1.00 | 0.40 |  |
| PY-MAINT-NAN-EQUALITY | ai-confirm | ruff:PLW0177 | 1 | 0 | 0 | 2 | 13 | 0 | 0 | 1.00 | 0.13 |  |
| PY-MAINT-PREFIX-INCREMENT | deterministic | ruff:B002 | 1 | 0 | 0 | 3 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-MAINT-RETURN-BOOLEAN-IF | deterministic | ruff:SIM103 | 1 | 0 | 0 | 6 | 11 | 0 | 0 | 1.00 | 0.35 |  |
| PY-MAINT-REVERSED-SORTED | deterministic | ruff:C413 | 1 | 0 | 0 | 13 | 2 | 0 | 0 | 1.00 | 0.87 |  |
| PY-MAINT-SET-OF-SORTED | ai-confirm | ruff:C414 | 1 | 0 | 0 | 2 | 20 | 0 | 0 | 1.00 | 0.09 |  |
| PY-MAINT-SHALLOW-COPY-ENVIRON | ai-confirm | ruff:PLW1507 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-MAINT-SUM-CONCATENATES-LISTS | deterministic | ruff:RUF017 | 2 | 0 | 0 | 6 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-MAINT-TASK-REFERENCE-DROPPED | ai-confirm | ruff:RUF006 | 1 | 0 | 0 | 2 | 6 | 0 | 0 | 1.00 | 0.25 |  |
| PY-MAINT-TODO-COMMENT | ai-confirm | ruff:FIX002 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-MAINT-TOO-MANY-PARAMS | deterministic | ruff:PLR0913 | 1 | 0 | 0 | 3 | 6 | 0 | 0 | 1.00 | 0.33 |  |
| PY-MAINT-TOO-MANY-RETURNS | deterministic | ruff:PLR0911 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-MAINT-UNUSED-LOCAL | ai-confirm | ruff:F841 | 3 | 0 | 0 | 22 | 29 | 0 | 0 | 1.00 | 0.43 |  |
| PY-MOD-REMOVEPREFIX | ai-confirm | ruff:FURB188 | 1 | 0 | 0 | 1 | 16 | 0 | 0 | 1.00 | 0.06 |  |
| PY-QUAL-ASSERT-FALSE | ai-confirm | ruff:B011 | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-QUAL-ASSERT-TUPLE | deterministic | ruff:F631 | 1 | 0 | 0 | 3 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-QUAL-BARE-EXCEPT | ai-confirm | ruff:E722 | 1 | 0 | 0 | 3 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-QUAL-BOOL-COMPARISON | ai-confirm | ruff:E712 | 1 | 0 | 0 | 8 | 4 | 0 | 0 | 1.00 | 0.67 |  |
| PY-QUAL-DEBUGGER-LEFT | ai-confirm | ruff:T100 | 1 | 0 | 0 | 2 | 22 | 0 | 0 | 1.00 | 0.08 |  |
| PY-QUAL-EXCEPT-EMPTY-TUPLE | ai-confirm | ruff:B029 | 1 | 0 | 0 | 2 | 2 | 0 | 0 | 1.00 | 0.50 |  |
| PY-QUAL-FSTRING-NO-PLACEHOLDER | ai-confirm | ruff:F541 | 1 | 0 | 0 | 15 | 2 | 0 | 0 | 1.00 | 0.88 |  |
| PY-QUAL-IN-DICT-KEYS | deterministic | ruff:SIM118 | 1 | 0 | 0 | 13 | 6 | 0 | 0 | 1.00 | 0.68 |  |
| PY-QUAL-IS-LITERAL | deterministic | ruff:F632 | 1 | 0 | 0 | 8 | 3 | 0 | 0 | 1.00 | 0.73 |  |
| PY-QUAL-LOOP-VAR-CLOSURE | ai-confirm | ruff:B023 | 1 | 0 | 0 | 2 | 20 | 0 | 0 | 1.00 | 0.09 |  |
| PY-QUAL-OPEN-NO-ENCODING | ai-confirm | ruff:PLW1514 | 1 | 0 | 0 | 11 | 11 | 0 | 0 | 1.00 | 0.50 |  |
| PY-QUAL-RAISE-NOTIMPLEMENTED | deterministic | ruff:F901 | 1 | 0 | 0 | 3 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-QUAL-RAISE-WITHOUT-FROM | ai-confirm | ruff:B904 | 1 | 0 | 0 | 2 | 11 | 0 | 0 | 1.00 | 0.15 |  |
| PY-QUAL-STRIP-MULTICHAR | deterministic | ruff:B005 | 1 | 0 | 0 | 3 | 6 | 0 | 0 | 1.00 | 0.33 |  |
| PY-QUAL-TYPE-COMPARISON | deterministic | ruff:E721 | 1 | 0 | 0 | 13 | 2 | 0 | 0 | 1.00 | 0.87 |  |
| PY-QUAL-USELESS-COMPARISON | deterministic | ruff:B015 | 1 | 0 | 0 | 5 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-SEC-HARDCODED-PASSWORD | deterministic | ruff:S105 | 1 | 0 | 0 | 14 | 21 | 0 | 0 | 1.00 | 0.40 |  |
| PY-SEC-HARDCODED-TMP | ai-confirm | ruff:S108 | 1 | 0 | 0 | 6 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| PY-SEC-JINJA-AUTOESCAPE-FALSE | ai-confirm | ruff:S701 | 1 | 0 | 0 | 5 | 1 | 0 | 0 | 1.00 | 0.83 |  |
| PY-SEC-SQL-STRING-FORMAT | deterministic | ruff:S608 | 1 | 0 | 0 | 4 | 55 | 0 | 0 | 1.00 | 0.07 |  |
| PY-SEC-TARFILE-EXTRACTALL-NO-FILTER | deterministic | ruff:S202 | 1 | 0 | 0 | 4 | 1 | 0 | 0 | 1.00 | 0.80 |  |
| TS-QUAL-ANY-001 | ai-confirm | typescript-eslint:@typescript-eslint/no-explicit-any | 75 | 60 | 0 | 6 | 39 | 0 | 30 | 1.00 | 0.13 |  |
| TS-QUAL-ARRAY-TYPE | deterministic | oxlint:typescript/array-type | 140 | 0 | 105 | 32 | 3 | 0 | 0 | 1.00 | 0.91 |  |
| TS-QUAL-BAN-TS-COMMENT-NOCHECK | ai-confirm | typescript-eslint:@typescript-eslint/ban-ts-comment | 28 | 86 | 0 | 3 | 4 | 0 | 21 | 1.00 | 0.43 |  |
| TS-QUAL-BAN-TSLINT-COMMENT | deterministic | typescript-eslint:@typescript-eslint/ban-tslint-comment | 13 | 0 | 0 | 4 | 4 | 0 | 5 | 1.00 | 0.50 |  |
| TS-QUAL-CONSISTENT-TYPE-ASSERTIONS | deterministic | oxlint:typescript/consistent-type-assertions | 182 | 0 | 86 | 52 | 0 | 0 | 44 | 1.00 | 1.00 |  |
| TS-QUAL-CONSISTENT-TYPE-DEFINITIONS | ai-confirm | typescript-eslint:@typescript-eslint/consistent-type-definitions | 5 | 28 | 0 | 2 | 3 | 0 | 0 | 1.00 | 0.40 |  |
| TS-QUAL-METHOD-SIGNATURE-STYLE | deterministic | typescript-eslint:@typescript-eslint/method-signature-style | 37 | 27 | 0 | 18 | 6 | 0 | 13 | 1.00 | 0.75 |  |
| TS-QUAL-NO-CONFUSING-NON-NULL-ASSERTION | deterministic | typescript-eslint:@typescript-eslint/no-confusing-non-null-assertion | 19 | 1 | 0 | 5 | 6 | 0 | 8 | 1.00 | 0.45 |  |
| TS-QUAL-NO-DYNAMIC-DELETE | ai-confirm | typescript-eslint:@typescript-eslint/no-dynamic-delete | 21 | 0 | 0 | 4 | 6 | 0 | 11 | 1.00 | 0.40 |  |
| TS-QUAL-NO-EXTRA-NON-NULL-ASSERTION | ai-confirm | typescript-eslint:@typescript-eslint/no-extra-non-null-assertion | 13 | 3 | 0 | 2 | 6 | 0 | 5 | 1.00 | 0.25 |  |
| TS-QUAL-NO-EXTRANEOUS-CLASS | ai-confirm | typescript-eslint:@typescript-eslint/no-extraneous-class | 21 | 8 | 0 | 2 | 8 | 0 | 11 | 1.00 | 0.20 |  |
| TS-QUAL-NO-INFERRABLE-TYPES | deterministic | typescript-eslint:@typescript-eslint/no-inferrable-types | 90 | 9 | 0 | 4 | 36 | 0 | 50 | 1.00 | 0.10 |  |
| TS-QUAL-NO-MISUSED-NEW | ai-confirm | typescript-eslint:@typescript-eslint/no-misused-new | 19 | 5 | 0 | 2 | 4 | 0 | 13 | 1.00 | 0.33 |  |
| TS-QUAL-NO-MIXED-ENUMS | deterministic | typescript-eslint:@typescript-eslint/no-mixed-enums | 64 | 0 | 0 | 1 | 27 | 0 | 36 | 1.00 | 0.04 |  |
| TS-QUAL-NO-REQUIRE-IMPORTS | ai-confirm | typescript-eslint:@typescript-eslint/no-require-imports | 17 | 29 | 0 | 7 | 2 | 0 | 8 | 1.00 | 0.78 |  |
| TS-QUAL-NO-THIS-ALIAS | deterministic | typescript-eslint:@typescript-eslint/no-this-alias | 5 | 6 | 0 | 2 | 1 | 0 | 2 | 1.00 | 0.67 |  |
| TS-QUAL-NO-UNNECESSARY-TEMPLATE-EXPRESSION | deterministic | typescript-eslint:@typescript-eslint/no-unnecessary-template-expression | 184 | 0 | 0 | 59 | 58 | 0 | 67 | 1.00 | 0.50 |  |
| TS-QUAL-NO-UNNECESSARY-TYPE-CONSTRAINT | deterministic | typescript-eslint:@typescript-eslint/no-unnecessary-type-constraint | 34 | 0 | 0 | 22 | 0 | 0 | 12 | 1.00 | 1.00 |  |
| TS-QUAL-NO-UNSAFE-DECLARATION-MERGING | ai-confirm | typescript-eslint:@typescript-eslint/no-unsafe-declaration-merging | 11 | 0 | 0 | 2 | 1 | 0 | 8 | 1.00 | 0.67 |  |
| TS-QUAL-NO-UNSAFE-FUNCTION-TYPE | ai-confirm | typescript-eslint:@typescript-eslint/no-unsafe-function-type | 8 | 0 | 0 | 1 | 4 | 0 | 3 | 1.00 | 0.20 |  |
| TS-QUAL-NONNULL-001 | ai-confirm | typescript-eslint:@typescript-eslint/no-non-null-assertion | 28 | 2 | 0 | 22 | 0 | 0 | 6 | 1.00 | 1.00 |  |
| TS-QUAL-ONLY-THROW-ERROR | deterministic | typescript-eslint:@typescript-eslint/only-throw-error | 66 | 23 | 0 | 4 | 30 | 0 | 32 | 1.00 | 0.12 |  |
| TS-QUAL-PREFER-AS-CONST | deterministic | typescript-eslint:@typescript-eslint/prefer-as-const | 46 | 0 | 0 | 6 | 9 | 0 | 31 | 1.00 | 0.40 |  |
| TS-QUAL-PREFER-ENUM-INITIALIZERS | deterministic | typescript-eslint:@typescript-eslint/prefer-enum-initializers | 8 | 0 | 0 | 4 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| TS-QUAL-TRIPLE-SLASH-REFERENCE | deterministic | oxlint:typescript/triple-slash-reference | 21 | 0 | 8 | 1 | 0 | 0 | 12 | 1.00 | 1.00 |  |
| TS-QUAL-USE-UNKNOWN-IN-CATCH-CALLBACK-VARIABLE | ai-confirm | typescript-eslint:@typescript-eslint/use-unknown-in-catch-callback-variable | 57 | 3 | 0 | 5 | 21 | 0 | 31 | 1.00 | 0.19 |  |
| VUE-A11Y-ARIA-INVALID-ATTRIBUTE | ai-confirm | vuejs-accessibility:aria-props | 2 | 0 | 0 | 1 | 0 | 0 | 1 | 1.00 | 1.00 |  |
| VUE-A11Y-ARIA-INVALID-ROLE | ai-confirm | vuejs-accessibility:aria-role | 6 | 1 | 0 | 1 | 1 | 0 | 4 | 1.00 | 0.50 |  |
| VUE-A11Y-CONTROL-WITHOUT-LABEL | ai-confirm | vuejs-accessibility:form-control-has-label | 22 | 2 | 0 | 2 | 5 | 0 | 15 | 1.00 | 0.29 |  |
| VUE-A11Y-MARQUEE-OR-BLINK | ai-confirm | vuejs-accessibility:no-distracting-elements | 3 | 1 | 0 | 2 | 0 | 0 | 1 | 1.00 | 1.00 |  |
| VUE-A11Y-POSITIVE-TABINDEX | ai-confirm | vuejs-accessibility:tabindex-no-positive | 7 | 0 | 0 | 2 | 1 | 0 | 4 | 1.00 | 0.67 |  |
| VUE-MIG-NO-DEPRECATED-FUNCTIONAL-TEMPLATE | deterministic | eslint-plugin-vue:vue/no-deprecated-functional-template | 5 | 0 | 0 | 2 | 0 | 0 | 3 | 1.00 | 1.00 |  |
| VUE-MIG-NO-DEPRECATED-HTML-ELEMENT-IS | ai-confirm | eslint-plugin-vue:vue/no-deprecated-html-element-is | 7 | 1 | 0 | 2 | 0 | 0 | 5 | 1.00 | 1.00 |  |
| VUE-MIG-NO-DEPRECATED-MODEL-DEFINITION | deterministic | eslint-plugin-vue:vue/no-deprecated-model-definition | 4 | 9 | 0 | 1 | 2 | 0 | 1 | 1.00 | 0.33 |  |
| VUE-MIG-NO-DEPRECATED-V-IS | deterministic | eslint-plugin-vue:vue/no-deprecated-v-is | 3 | 0 | 0 | 1 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| VUE-QUAL-HTML-BUTTON-HAS-TYPE | ai-confirm | eslint-plugin-vue:vue/html-button-has-type | 14 | 5 | 4 | 2 | 0 | 0 | 8 | 1.00 | 1.00 |  |
| VUE-QUAL-HTML-QUOTES | ai-confirm | eslint-plugin-vue:vue/html-quotes | 8 | 30 | 3 | 2 | 0 | 0 | 3 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-CHILD-CONTENT | deterministic | eslint-plugin-vue:vue/no-child-content | 14 | 3 | 2 | 5 | 0 | 0 | 7 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-DUPE-V-ELSE-IF | deterministic | eslint-plugin-vue:vue/no-dupe-v-else-if | 97 | 3 | 43 | 24 | 0 | 0 | 30 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-DUPLICATE-ATTR-INHERITANCE | deterministic | eslint-plugin-vue:vue/no-duplicate-attr-inheritance | 21 | 5 | 7 | 5 | 0 | 0 | 9 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-EMPTY-COMPONENT-BLOCK | deterministic | eslint-plugin-vue:vue/no-empty-component-block | 26 | 1 | 13 | 5 | 0 | 0 | 8 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-EXPORT-IN-SCRIPT-SETUP | ai-confirm | eslint-plugin-vue:vue/no-export-in-script-setup | 4 | 2 | 0 | 2 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-EXPOSE-AFTER-AWAIT | ai-confirm | eslint-plugin-vue:vue/no-expose-after-await | 12 | 0 | 0 | 2 | 1 | 0 | 9 | 1.00 | 0.67 |  |
| VUE-QUAL-NO-IMPORT-COMPILER-MACROS | deterministic | eslint-plugin-vue:vue/no-import-compiler-macros | 8 | 1 | 0 | 5 | 1 | 0 | 2 | 1.00 | 0.83 |  |
| VUE-QUAL-NO-MULTIPLE-OBJECTS-IN-CLASS | ai-confirm | eslint-plugin-vue:vue/no-multiple-objects-in-class | 6 | 1 | 2 | 2 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-PARSING-ERROR | ai-confirm | eslint-plugin-vue:vue/no-parsing-error | 56 | 76 | 25 | 19 | 0 | 0 | 12 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-REQUIRED-PROP-WITH-DEFAULT | ai-confirm | eslint-plugin-vue:vue/no-required-prop-with-default | 5 | 30 | 0 | 1 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-ROOT-V-IF | ai-confirm | eslint-plugin-vue:vue/no-root-v-if | 23 | 0 | 0 | 2 | 0 | 0 | 21 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-STATIC-INLINE-STYLES | ai-confirm | eslint-plugin-vue:vue/no-static-inline-styles | 21 | 6 | 10 | 2 | 0 | 0 | 9 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-TEMPLATE-KEY | ai-confirm | eslint-plugin-vue:vue/no-template-key | 14 | 0 | 5 | 1 | 0 | 0 | 8 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-TEXTAREA-MUSTACHE | deterministic | eslint-plugin-vue:vue/no-textarea-mustache | 6 | 0 | 0 | 3 | 0 | 0 | 3 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-USE-V-ELSE-WITH-V-FOR | ai-confirm | eslint-plugin-vue:vue/no-use-v-else-with-v-for | 6 | 0 | 0 | 2 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-USELESS-MUSTACHES | deterministic | eslint-plugin-vue:vue/no-useless-mustaches | 11 | 2 | 0 | 7 | 3 | 0 | 1 | 1.00 | 0.70 |  |
| VUE-QUAL-NO-USELESS-V-BIND | deterministic | eslint-plugin-vue:vue/no-useless-v-bind | 6 | 2 | 0 | 3 | 2 | 0 | 1 | 1.00 | 0.60 |  |
| VUE-QUAL-NO-V-FOR-TEMPLATE-KEY-ON-CHILD | deterministic | eslint-plugin-vue:vue/no-v-for-template-key-on-child | 15 | 0 | 5 | 7 | 0 | 0 | 3 | 1.00 | 1.00 |  |
| VUE-QUAL-NO-V-TEXT | ai-confirm | eslint-plugin-vue:vue/no-v-text | 4 | 0 | 0 | 1 | 0 | 0 | 3 | 1.00 | 1.00 |  |
| VUE-QUAL-PREFER-PROP-TYPE-BOOLEAN-FIRST | deterministic | eslint-plugin-vue:vue/prefer-prop-type-boolean-first | 11 | 1 | 0 | 5 | 3 | 0 | 3 | 1.00 | 0.62 |  |
| VUE-QUAL-REQUIRE-COMPONENT-IS | ai-confirm | eslint-plugin-vue:vue/require-component-is | 5 | 0 | 1 | 2 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| VUE-QUAL-REQUIRE-TOGGLE-INSIDE-TRANSITION | deterministic | eslint-plugin-vue:vue/require-toggle-inside-transition | 25 | 3 | 11 | 6 | 0 | 0 | 8 | 1.00 | 1.00 |  |
| VUE-QUAL-V-FOR-DELIMITER-STYLE | deterministic | eslint-plugin-vue:vue/v-for-delimiter-style | 13 | 4 | 0 | 5 | 0 | 0 | 8 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-NEXT-TICK | ai-confirm | eslint-plugin-vue:vue/valid-next-tick | 14 | 6 | 5 | 1 | 0 | 0 | 8 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-CLOAK | deterministic | eslint-plugin-vue:vue/valid-v-cloak | 8 | 3 | 2 | 4 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-ELSE | deterministic | eslint-plugin-vue:vue/valid-v-else | 18 | 3 | 10 | 4 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-ELSE-IF-NOVALUE | ai-confirm | eslint-plugin-vue:vue/valid-v-else-if | 18 | 3 | 11 | 1 | 0 | 0 | 6 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-FOR-NOVALUE | ai-confirm | eslint-plugin-vue:vue/valid-v-for | 54 | 11 | 21 | 1 | 0 | 0 | 32 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-HTML-NOVALUE | ai-confirm | eslint-plugin-vue:vue/valid-v-html | 8 | 3 | 3 | 1 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-IF-NOVALUE | ai-confirm | eslint-plugin-vue:vue/valid-v-if | 10 | 3 | 5 | 1 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-MODEL-NOVALUE | ai-confirm | eslint-plugin-vue:vue/valid-v-model | 48 | 14 | 0 | 1 | 16 | 0 | 31 | 1.00 | 0.06 |  |
| VUE-QUAL-VALID-V-ONCE | deterministic | eslint-plugin-vue:vue/valid-v-once | 8 | 3 | 2 | 4 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-PRE | deterministic | eslint-plugin-vue:vue/valid-v-pre | 8 | 3 | 2 | 4 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-SHOW | ai-confirm | eslint-plugin-vue:vue/valid-v-show | 10 | 3 | 5 | 1 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-SHOW-NOVALUE | ai-confirm | eslint-plugin-vue:vue/valid-v-show | 10 | 3 | 5 | 1 | 0 | 0 | 4 | 1.00 | 1.00 |  |
| VUE-QUAL-VALID-V-TEXT-NOVALUE | ai-confirm | eslint-plugin-vue:vue/valid-v-text | 9 | 3 | 3 | 1 | 0 | 0 | 5 | 1.00 | 1.00 |  |
| VUE-SEC-NO-TEMPLATE-TARGET-BLANK | deterministic | eslint-plugin-vue:vue/no-template-target-blank | 16 | 2 | 6 | 1 | 0 | 0 | 9 | 1.00 | 1.00 |  |
| CSS-A11Y-FOCUS-OUTLINE-REMOVED | ai-confirm | axe:focus-order-semantics | 1 | 0 | 0 | 0 | 6 | 0 | 0 | - | 0.00 |  |
| CSS-A11Y-FOCUS-VISIBLE-OUTLINE-REMOVED | ai-confirm | stylelint:a11y/no-outline-none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| CSS-A11Y-FONT-SIZE-VIEWPORT-ONLY | ai-confirm | stylelint:a11y/font-size-is-readable | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| CSS-A11Y-LOW-CONTRAST | ai-confirm | axe:color-contrast | 1 | 1 | 0 | 0 | 14 | 0 | 0 | - | 0.00 |  |
| CSS-A11Y-LOW-CONTRAST-ENHANCED | ai-confirm | axe:color-contrast-enhanced | 1 | 0 | 0 | 0 | 2 | 0 | 0 | - | 0.00 |  |
| CSS-A11Y-OUTLINE-REMOVED-ON-CONTROLS | ai-confirm | stylelint:a11y/no-outline-none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| CSS-A11Y-REDUCED-MOTION-MISSING | ai-confirm | stylelint:a11y/media-prefers-reduced-motion | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| DOCKER-QUAL-APT-LISTS-NOT-REMOVED | ai-confirm | hadolint:DL3009 | 2 | 20 | 0 | 0 | 0 | 0 | 2 | - | - |  |
| DOCKER-QUAL-DUPLICATE-STAGE-NAME | ai-confirm | hadolint:DL3024 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| DOCKER-QUAL-EXPOSE-INVALID-FORMAT | deterministic | hadolint:DL3011 | 6 | 0 | 0 | 0 | 2 | 0 | 4 | - | 0.00 |  |
| DOCKER-QUAL-JSON-ARGS-RECOMMENDED | deterministic | hadolint:DL3025 | 0 | 7 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| DOCKER-QUAL-MULTIPLE-CMD | ai-confirm | hadolint:DL4003 | 1 | 3 | 0 | 0 | 0 | 0 | 1 | - | - |  |
| DOCKER-QUAL-PIPE-WITHOUT-PIPEFAIL | ai-confirm | hadolint:DL4006 | 0 | 15 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| DOCKER-QUAL-RUN-CD | deterministic | hadolint:DL3003 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | - | 0.00 |  |
| DOCKER-SEC-CURL-PIPE-SHELL | deterministic | hadolint:DL4006 | 0 | 15 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| DOCKER-SEC-USER-ROOT | deterministic | hadolint:DL3002 | 0 | 9 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| GO-MIG-RAND-SEED | deterministic | staticcheck:SA1019 | 16 | 0 | 0 | 0 | 28 | 0 | 9 | - | 0.00 |  |
| GO-MIG-VET-BUILDTAG | ai-confirm | govet:buildtag | 12 | 0 | 0 | 0 | 14 | 0 | 3 | - | 0.00 |  |
| GO-MOD-IMPORTCOMMENT | deterministic | govet:modernize | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | no modernize testdata for this sub-check |
| GO-MOD-OMITZERO | ai-confirm | govet:modernize | 2 | 0 | 0 | 0 | 5 | 0 | 1 | - | 0.00 |  |
| GO-QUAL-VET-DEEPEQUALERRORS | deterministic | govet:deepequalerrors | 2 | 0 | 0 | 0 | 18 | 0 | 0 | - | 0.00 |  |
| GO-QUAL-VET-LOOPCLOSURE | ai-confirm | govet:loopclosure | 5 | 0 | 0 | 0 | 44 | 0 | 2 | - | 0.00 |  |
| GO-QUAL-VET-STRINGINTCONV | ai-confirm | govet:stringintconv | 10 | 0 | 0 | 0 | 29 | 0 | 3 | - | 0.00 |  |
| GO-SEC-MATH-RAND-READ | ai-confirm | staticcheck:SA1019 | 16 | 0 | 0 | 0 | 28 | 0 | 9 | - | 0.00 |  |
| GRAPHQL-QUAL-DUPLICATE-ENUM-VALUE | ai-confirm | graphql-eslint:@graphql-eslint/unique-enum-value-names | 2 | 0 | 0 | 0 | 2 | 0 | 0 | - | 0.00 |  |
| GRAPHQL-QUAL-FIELD-NAME-CAMELCASE | ai-confirm | graphql-eslint:@graphql-eslint/naming-convention | 4 | 41 | 0 | 0 | 1 | 0 | 3 | - | 0.00 |  |
| GRAPHQL-QUAL-INPUT-TYPE-SUFFIX | deterministic | graphql-eslint:@graphql-eslint/input-name | 4 | 22 | 0 | 0 | 0 | 0 | 4 | - | - |  |
| GRAPHQL-QUAL-LONE-ANONYMOUS-OPERATION | ai-confirm | graphql-eslint:@graphql-eslint/lone-anonymous-operation | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| GRAPHQL-QUAL-LONE-SCHEMA-DEFINITION | ai-confirm | graphql-eslint:@graphql-eslint/lone-schema-definition | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| GRAPHQL-QUAL-MUTATION-INPUT-NAME | deterministic | graphql-eslint:@graphql-eslint/input-name | 4 | 22 | 0 | 0 | 0 | 0 | 4 | - | - |  |
| GRAPHQL-QUAL-MUTATION-SCALAR-RESULT | deterministic | graphql-eslint:@graphql-eslint/no-scalar-result-type-on-mutation | 0 | 8 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| GRAPHQL-QUAL-RELAY-ARGUMENTS | ai-confirm | graphql-eslint:@graphql-eslint/relay-arguments | 0 | 5 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| GRAPHQL-QUAL-RELAY-EDGE-FIELDS | ai-confirm | graphql-eslint:@graphql-eslint/relay-edge-types | 0 | 11 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| GRAPHQL-QUAL-RELAY-PAGE-INFO-FIELDS | ai-confirm | graphql-eslint:@graphql-eslint/relay-page-info | 0 | 10 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| GRAPHQL-QUAL-REQUIRE-DESCRIPTION-ROOT | ai-confirm | graphql-eslint:@graphql-eslint/require-description | 0 | 27 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| GRAPHQL-QUAL-ROOT-NON-NULL-RESULT | ai-confirm | graphql-eslint:@graphql-eslint/require-nullable-result-in-root | 0 | 4 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| GRAPHQL-QUAL-SELECTION-SET-DEPTH | deterministic | graphql-eslint:@graphql-eslint/selection-set-depth | 0 | 7 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| GRAPHQL-QUAL-STRICT-ID-IN-TYPES | ai-confirm | graphql-eslint:@graphql-eslint/strict-id-in-types | 0 | 18 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| HTML-A11Y-AMBIGUOUS-LINK-TEXT | ai-confirm | axe:link-name | 1 | 0 | 0 | 0 | 5 | 0 | 0 | - | 0.00 |  |
| HTML-A11Y-ARIA-REQUIRED-ATTRIBUTE | ai-confirm | axe:aria-required-attr | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| HTML-A11Y-AUTOCOMPLETE-INVALID | ai-confirm | axe:autocomplete-valid | 1 | 0 | 0 | 0 | 5 | 0 | 0 | - | 0.00 |  |
| HTML-A11Y-DUPLICATE-ID | ai-confirm | axe:duplicate-id | 1 | 2 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| HTML-A11Y-IMG-REDUNDANT-ALT | ai-confirm | jsx-a11y:img-redundant-alt | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| HTML-A11Y-MAIN-LANDMARK-MISSING | ai-confirm | axe:landmark-one-main | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| HTML-A11Y-MOUSE-WITHOUT-KEYBOARD | ai-confirm | jsx-a11y:mouse-events-have-key-events | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| HTML-A11Y-NESTED-INTERACTIVE | ai-confirm | axe:nested-interactive | 1 | 0 | 0 | 0 | 5 | 0 | 0 | - | 0.00 |  |
| HTML-A11Y-TABLE-WITHOUT-HEADERS | ai-confirm | axe:td-has-header | 1 | 0 | 0 | 0 | 2 | 0 | 0 | - | 0.00 |  |
| HTML-A11Y-VIDEO-WITHOUT-CAPTIONS | ai-confirm | axe:video-caption | 1 | 0 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| JS-A11Y-ARIA-LABEL-ON-GENERIC | ai-confirm | axe:aria-prohibited-attr | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-AUTOPLAY-WITH-SOUND | ai-confirm | axe:no-autoplay-audio | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-BUTTON-WITHOUT-NAME | ai-confirm | axe:button-name | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-DUPLICATE-ID | ai-confirm | axe:duplicate-id | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-HEADING-SKIPPED-LEVEL | ai-confirm | axe:heading-order | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-INPUT-IMAGE-WITHOUT-ALT | ai-confirm | axe:input-image-alt | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-LANG-INVALID | ai-confirm | jsx-a11y:lang | 15 | 4 | 0 | 0 | 3 | 0 | 12 | - | 0.00 |  |
| JS-A11Y-NESTED-INTERACTIVE | ai-confirm | axe:nested-interactive | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-ROLE-IMG-WITHOUT-NAME | ai-confirm | axe:role-img-alt | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-TABLE-WITHOUT-HEADERS | ai-confirm | axe:td-has-header | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-TH-INVALID-SCOPE | ai-confirm | axe:scope-attr-valid | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-MAINT-CYCLOMATIC-COMPLEXITY | deterministic | eslint:complexity | 1 | 178 | 0 | 0 | 0 | 0 | 1 | - | - |  |
| JS-MAINT-DEEP-NESTING | deterministic | eslint:max-depth | 2 | 28 | 0 | 0 | 1 | 0 | 1 | - | 0.00 |  |
| JS-MAINT-DUPLICATE-PARAMETER | ai-confirm | eslint:no-dupe-args | 13 | 0 | 8 | 0 | 0 | 0 | 5 | - | - |  |
| JS-MAINT-ERROR-NOT-THROWN | ai-confirm | eslint:no-new | 3 | 0 | 0 | 0 | 1 | 0 | 2 | - | 0.00 |  |
| JS-MAINT-IDENTICAL-OPERANDS | ai-confirm | eslint:no-self-compare | 21 | 0 | 0 | 0 | 15 | 0 | 6 | - | 0.00 |  |
| JS-MAINT-LONG-FUNCTION | deterministic | eslint:max-lines-per-function | 0 | 100 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| JS-MAINT-LOOP-RUNS-ONCE | ai-confirm | eslint:no-unreachable-loop | 21 | 24 | 11 | 0 | 0 | 0 | 10 | - | - |  |
| JS-MAINT-NAN-COMPARISON | ai-confirm | eslint:use-isnan | 87 | 162 | 0 | 0 | 45 | 0 | 42 | - | 0.00 |  |
| JS-MAINT-UNUSED-IMPORT | ai-confirm | eslint:no-unused-vars | 333 | 211 | 145 | 0 | 83 | 0 | 105 | - | 0.00 |  |
| JS-MAINT-UNUSED-LOCAL | ai-confirm | eslint:no-unused-vars | 333 | 211 | 145 | 0 | 83 | 0 | 105 | - | 0.00 |  |
| JS-QUAL-EQ-001 | deterministic | eslint:eqeqeq | 2 | 31 | 0 | 0 | 0 | 0 | 2 | - | - |  |
| JS-QUAL-EQEQEQ-SMART | ai-confirm | eslint:eqeqeq | 2 | 31 | 0 | 0 | 0 | 0 | 2 | - | - |  |
| JS-QUAL-NO-UNSAFE-OPTIONAL-CHAINING | ai-confirm | eslint:no-unsafe-optional-chaining | 64 | 8 | 2 | 0 | 2 | 0 | 60 | - | 0.00 |  |
| JS-QUAL-NO-USELESS-RETURN | ai-confirm | eslint:no-useless-return | 25 | 5 | 0 | 0 | 0 | 0 | 25 | - | - |  |
| JS-QUAL-PREFER-PROMISE-REJECT-ERRORS | ai-confirm | eslint:prefer-promise-reject-errors | 33 | 7 | 6 | 0 | 0 | 0 | 27 | - | - |  |
| JS-QUAL-YODA | ai-confirm | eslint:yoda | 2 | 160 | 0 | 0 | 2 | 0 | 0 | - | 0.00 |  |
| PY-MAINT-COMPLEX-CONDITION | deterministic | ruff:PLR0916 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MAINT-CYCLOMATIC-COMPLEXITY | deterministic | ruff:C901 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MAINT-EXCEPT-BOOLEAN-EXPRESSION | ai-confirm | ruff:PLW0711 | 1 | 0 | 0 | 0 | 2 | 0 | 0 | - | 0.00 |  |
| PY-MAINT-LONG-FUNCTION | deterministic | ruff:PLR0915 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | - | 0.00 |  |
| PY-MAINT-MAGIC-NUMBER | ai-confirm | ruff:PLR2004 | 1 | 0 | 0 | 0 | 8 | 0 | 0 | - | 0.00 |  |
| PY-MAINT-SELF-ASSIGNMENT | ai-confirm | ruff:PLW0127 | 1 | 0 | 0 | 0 | 23 | 0 | 0 | - | 0.00 |  |
| PY-MIG-LOGGING-WARN | deterministic | ruff:G010 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-DATETIME-UTC-ALIAS | ai-confirm | ruff:UP017 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-FORMAT-TO-FSTRING | ai-confirm | ruff:UP032 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-FUTURE-IMPORT | ai-confirm | ruff:UP010 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-LRU-CACHE-NONE | ai-confirm | ruff:UP033 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-OBJECT-INHERITANCE | ai-confirm | ruff:UP004 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-OPEN-ALIAS | ai-confirm | ruff:UP020 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-OS-ERROR-ALIAS | ai-confirm | ruff:UP024 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-PEP585-GENERICS | ai-confirm | ruff:UP006 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-PEP604-OPTIONAL | ai-confirm | ruff:UP045 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-PERCENT-FORMAT | ai-confirm | ruff:UP031 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-STR-ENUM | ai-confirm | ruff:UP042 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-SUPER-ARGS | ai-confirm | ruff:UP008 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-TIMEOUT-ERROR-ALIAS | ai-confirm | ruff:UP041 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-TYPE-ALIAS-PEP695 | ai-confirm | ruff:UP040 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-TYPING-TEXT | ai-confirm | ruff:UP019 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-UNICODE-PREFIX | ai-confirm | ruff:UP025 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-MOD-YIELD-FROM | ai-confirm | ruff:UP028 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-QUAL-LOGGING-FSTRING | ai-confirm | ruff:G004 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-QUAL-ZIP-WITHOUT-STRICT | ai-confirm | ruff:B905 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| PY-SEC-EVAL | ai-confirm | ruff:S307 | 1 | 0 | 0 | 0 | 2 | 0 | 0 | - | 0.00 |  |
| PY-SEC-FLASK-DEBUG | deterministic | ruff:S201 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | - | 0.00 |  |
| PY-SEC-HASH-WEAK | ai-confirm | ruff:S324 | 1 | 0 | 0 | 0 | 21 | 0 | 0 | - | 0.00 |  |
| PY-SEC-RANDOM-FOR-SECURITY | ai-confirm | ruff:S311 | 1 | 0 | 0 | 0 | 9 | 0 | 0 | - | 0.00 |  |
| REACT-QUAL-IMPURE-RENDER | ai-confirm | react-hooks:react-hooks/purity | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | no suite for this rule |
| REACT-QUAL-NESTED-COMPONENT-DEFINITION | ai-confirm | react-hooks:react-hooks/static-components | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | no suite for this rule |
| REACT-QUAL-SET-STATE-IN-EFFECT | ai-confirm | react-hooks:react-hooks/set-state-in-effect | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | no suite for this rule |
| REACT-QUAL-SET-STATE-IN-RENDER | ai-confirm | react-hooks:react-hooks/set-state-in-render | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | no suite for this rule |
| REACT-QUAL-TRY-CATCH-AROUND-JSX | deterministic | react-hooks:react-hooks/error-boundaries | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | no suite for this rule |
| REACT-QUAL-USEMEMO-NO-RETURN | ai-confirm | react-hooks:react-hooks/use-memo | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | no suite for this rule |
| TS-QUAL-CATCH-ANY-001 | ai-confirm | typescript-eslint:@typescript-eslint/use-unknown-in-catch-callback-variable | 57 | 3 | 0 | 0 | 26 | 0 | 31 | - | 0.00 |  |
| TS-QUAL-CFG-ALLOWUNUSEDLABELS-001 | ai-confirm | eslint:no-unused-labels | 35 | 5 | 2 | 0 | 26 | 0 | 7 | - | 0.00 |  |
| TS-QUAL-EXPLICIT-FUNCTION-RETURN-TYPE | ai-confirm | typescript-eslint:@typescript-eslint/explicit-function-return-type | 14 | 130 | 0 | 0 | 6 | 0 | 8 | - | 0.00 |  |
| TS-QUAL-NO-UNSAFE-TYPE-ASSERTION | ai-confirm | typescript-eslint:@typescript-eslint/no-unsafe-type-assertion | 102 | 14 | 0 | 0 | 62 | 0 | 40 | - | 0.00 |  |
| TS-QUAL-PREFER-NULLISH-COALESCING | ai-confirm | typescript-eslint:@typescript-eslint/prefer-nullish-coalescing | 129 | 504 | 0 | 0 | 66 | 0 | 63 | - | 0.00 |  |
| VUE-A11Y-AMBIGUOUS-LINK-TEXT | ai-confirm | axe:link-name | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-ARIA-LABEL-ON-GENERIC | ai-confirm | axe:aria-prohibited-attr | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-ARIA-REQUIRED-ATTRIBUTE | ai-confirm | vuejs-accessibility:role-has-required-aria-props | 7 | 0 | 0 | 0 | 3 | 0 | 4 | - | 0.00 |  |
| VUE-A11Y-AUTOCOMPLETE-INVALID | ai-confirm | axe:autocomplete-valid | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-AUTOPLAY-WITH-SOUND | ai-confirm | axe:no-autoplay-audio | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-BUTTON-WITHOUT-NAME | ai-confirm | axe:button-name | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-CLICK-WITHOUT-KEYBOARD | ai-confirm | vuejs-accessibility:click-events-have-key-events | 33 | 0 | 0 | 0 | 11 | 0 | 22 | - | 0.00 |  |
| VUE-A11Y-DUPLICATE-ID | ai-confirm | axe:duplicate-id | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-EMPTY-HEADING | ai-confirm | vuejs-accessibility:heading-has-content | 10 | 4 | 0 | 0 | 4 | 0 | 6 | - | 0.00 |  |
| VUE-A11Y-HEADING-SKIPPED-LEVEL | ai-confirm | axe:heading-order | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-IFRAME-WITHOUT-TITLE | ai-confirm | vuejs-accessibility:iframe-has-title | 5 | 0 | 0 | 0 | 3 | 0 | 2 | - | 0.00 |  |
| VUE-A11Y-IMG-REDUNDANT-ALT | ai-confirm | vuejs-accessibility:alt-text | 16 | 2 | 0 | 0 | 6 | 0 | 10 | - | 0.00 |  |
| VUE-A11Y-IMG-WITHOUT-ALT | ai-confirm | vuejs-accessibility:alt-text | 16 | 2 | 0 | 0 | 6 | 0 | 10 | - | 0.00 |  |
| VUE-A11Y-INPUT-IMAGE-WITHOUT-ALT | ai-confirm | axe:input-image-alt | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-LANG-INVALID | ai-confirm | axe:valid-lang | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-LINK-WITHOUT-NAME | ai-confirm | vuejs-accessibility:anchor-has-content | 12 | 4 | 0 | 0 | 2 | 0 | 10 | - | 0.00 |  |
| VUE-A11Y-MOUSE-WITHOUT-KEYBOARD | ai-confirm | vuejs-accessibility:mouse-events-have-key-events | 7 | 0 | 0 | 0 | 4 | 0 | 3 | - | 0.00 |  |
| VUE-A11Y-NESTED-INTERACTIVE | ai-confirm | axe:nested-interactive | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-ROLE-IMG-WITHOUT-NAME | ai-confirm | axe:role-img-alt | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-TABLE-WITHOUT-HEADERS | ai-confirm | axe:td-has-header | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-TH-INVALID-SCOPE | ai-confirm | axe:scope-attr-valid | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-VIDEO-WITHOUT-CAPTIONS | ai-confirm | vuejs-accessibility:media-has-caption | 38 | 0 | 0 | 0 | 17 | 0 | 21 | - | 0.00 |  |
| VUE-MIG-NO-DEPRECATED-VUE-CONFIG-KEYCODES | deterministic | eslint-plugin-vue:vue/no-deprecated-vue-config-keycodes | 6 | 0 | 0 | 0 | 3 | 0 | 3 | - | 0.00 |  |
| VUE-QUAL-MUSTACHE-INTERPOLATION-SPACING | ai-confirm | eslint-plugin-vue:vue/mustache-interpolation-spacing | 6 | 14 | 0 | 0 | 0 | 0 | 6 | - | - |  |
| VUE-QUAL-NO-ARROW-FUNCTIONS-IN-WATCH | ai-confirm | eslint-plugin-vue:vue/no-arrow-functions-in-watch | 14 | 0 | 6 | 0 | 0 | 0 | 8 | - | - |  |
| VUE-QUAL-NO-BOOLEAN-DEFAULT | ai-confirm | eslint-plugin-vue:vue/no-boolean-default | 5 | 29 | 0 | 0 | 0 | 0 | 5 | - | - |  |
| VUE-QUAL-NO-DUPLICATE-ATTRIBUTES | ai-confirm | eslint-plugin-vue:vue/no-duplicate-attributes | 9 | 11 | 2 | 0 | 0 | 0 | 7 | - | - |  |
| VUE-QUAL-NO-LONE-TEMPLATE | ai-confirm | eslint-plugin-vue:vue/no-lone-template | 8 | 8 | 2 | 0 | 0 | 0 | 6 | - | - |  |
| VUE-QUAL-NO-MULTIPLE-TEMPLATE-ROOT | ai-confirm | eslint-plugin-vue:vue/no-multiple-template-root | 17 | 13 | 8 | 0 | 0 | 0 | 9 | - | - |  |
| VUE-QUAL-NO-SIDE-EFFECTS-IN-COMPUTED-PROPERTIES | deterministic | eslint-plugin-vue:vue/no-side-effects-in-computed-properties | 21 | 1 | 0 | 0 | 12 | 0 | 9 | - | 0.00 |  |
| VUE-QUAL-NO-THIS-IN-BEFORE-ROUTE-ENTER | ai-confirm | eslint-plugin-vue:vue/no-this-in-before-route-enter | 1 | 9 | 0 | 0 | 0 | 0 | 1 | - | - |  |
| VUE-QUAL-NO-USELESS-TEMPLATE-ATTRIBUTES | ai-confirm | eslint-plugin-vue:vue/no-useless-template-attributes | 9 | 1 | 0 | 0 | 1 | 0 | 8 | - | 0.00 |  |
| VUE-QUAL-PREFER-IMPORT-FROM-VUE | ai-confirm | eslint-plugin-vue:vue/prefer-import-from-vue | 25 | 2 | 0 | 0 | 13 | 0 | 12 | - | 0.00 |  |
| VUE-QUAL-REQUIRE-PROP-TYPE-CONSTRUCTOR | ai-confirm | eslint-plugin-vue:vue/require-prop-type-constructor | 9 | 4 | 0 | 0 | 3 | 0 | 6 | - | 0.00 |  |
| VUE-QUAL-REQUIRE-PROP-TYPES | ai-confirm | eslint-plugin-vue:vue/require-prop-types | 15 | 14 | 5 | 0 | 0 | 0 | 10 | - | - |  |
| VUE-QUAL-RETURN-IN-COMPUTED-PROPERTY | ai-confirm | eslint-plugin-vue:vue/return-in-computed-property | 23 | 117 | 2 | 0 | 16 | 0 | 5 | - | 0.00 |  |
| VUE-QUAL-THIS-IN-TEMPLATE | ai-confirm | eslint-plugin-vue:vue/this-in-template | 3 | 13 | 0 | 0 | 0 | 0 | 3 | - | - |  |
| VUE-QUAL-VALID-V-FOR | ai-confirm | eslint-plugin-vue:vue/valid-v-for | 54 | 11 | 25 | 0 | 0 | 0 | 29 | - | - |  |

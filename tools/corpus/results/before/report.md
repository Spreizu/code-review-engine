# Corpus run "before" (oss)

Reported = confirmed (review list with AI off); pending = ai-confirm candidates (shown only after high-confidence AI confirmation); shadow = quarantined rules.

| repo | files | reported | pending | ms | error |
|---|---|---|---|---|---|
| angular-realworld | 86 | 178 | 20 | 4280 |  |
| awesome-compose | 463 | 560 | 338 | 5587 |  |
| axios | 487 | 1923 | 277 | 17543 |  |
| cobra | 65 | 45 | 10 | 1855 |  |
| express | 214 | 4958 | 20 | 6938 |  |
| flask | 235 | 69 | 5 | 2956 |  |
| gin | 128 | 140 | 80 | 4669 |  |
| grpc-gateway | 629 | 699 | 209 | 14094 |  |
| gson | 313 | 58 | 113 | 7521 |  |
| guzzle | 176 | 112 | 25 | 8391 |  |
| nuxt-examples | 278 | 209 | 198 | 6649 |  |
| nuxt-ui-dashboard | 47 | 45 | 20 | 3965 |  |
| okio | 438 | 443 | 340 | 9742 |  |
| pinia | 337 | 828 | 204 | 9781 |  |
| requests | 130 | 188 | 26 | 2023 |  |
| slim | 145 | 9 | 10 | 2130 |  |
| spring-petclinic | 132 | 47 | 49 | 2559 |  |
| swapi-graphql | 62 | 46 | 56 | 1262 |  |
| terraform-aws-vpc | 111 | 157 | 2 | 2104 |  |
| vitesse | 80 | 58 | 18 | 3553 |  |
| zod | 739 | 5085 | 1150 | 57540 |  |
| zustand | 142 | 245 | 28 | 8725 |  |

## Per pack

| pack | reported | pending | shadow |
|---|---|---|---|
| angular | 51 | 1 | 0 |
| composer | 8 | 2 | 0 |
| docker | 239 | 286 | 0 |
| go | 538 | 117 | 0 |
| gradle | 10 | 34 | 0 |
| graphql | 9 | 52 | 0 |
| java | 9 | 57 | 0 |
| javascript | 11155 | 640 | 0 |
| json | 46 | 6 | 0 |
| kotlin | 421 | 279 | 0 |
| maven | 12 | 51 | 0 |
| nuxt | 14 | 7 | 0 |
| nuxt-ui | 3 | 0 | 0 |
| package-json | 42 | 20 | 0 |
| php | 93 | 28 | 0 |
| protobuf | 142 | 225 | 0 |
| python | 237 | 34 | 0 |
| react | 6 | 19 | 0 |
| simplify-go | 12 | 11 | 0 |
| simplify-java | 10 | 7 | 0 |
| simplify-javascript | 3 | 13 | 0 |
| simplify-kotlin | 4 | 11 | 0 |
| simplify-php | 2 | 2 | 0 |
| simplify-python | 1 | 1 | 0 |
| spring-boot | 25 | 12 | 0 |
| terraform | 145 | 2 | 0 |
| typescript | 2293 | 1249 | 0 |
| vue | 112 | 31 | 0 |
| yaml | 460 | 1 | 0 |

## Per rule (flagged first)

Flags: total >= 15, >= 10 in one repo, or >= 25% of a repo's files.

| rule | reported | repos | max/repo | file share | pending | shadow | flags |
|---|---|---|---|---|---|---|---|
| JS-PREFER-ARROW-CALLBACK | 2705 | 7 | 2391 | 56.5% | 0 | 0 | total>=15 repo>=10 files>=25% |
| JS-VAR-001 | 1987 | 7 | 1748 | 63.6% | 0 | 0 | total>=15 repo>=10 files>=25% |
| YAML-DOCUMENT-START | 216 | 22 | 53 | 26.2% | 0 | 0 | total>=15 repo>=10 files>=25% |
| JS-CURLY | 1738 | 10 | 1416 | 22.1% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-CONSOLE | 796 | 11 | 462 | 13.6% | 0 | 0 | total>=15 repo>=10 |
| JS-REQUIRE-UNICODE-REGEXP | 758 | 10 | 370 | 19.2% | 0 | 0 | total>=15 repo>=10 |
| TS-ANY-001 | 698 | 4 | 509 | 10.8% | 0 | 0 | total>=15 repo>=10 |
| JS-PREFER-TEMPLATE | 363 | 7 | 191 | 19.6% | 0 | 0 | total>=15 repo>=10 |
| JS-PREFER-DESTRUCTURING | 287 | 7 | 162 | 14.0% | 0 | 0 | total>=15 repo>=10 |
| TS-METHOD-SIGNATURE-STYLE | 251 | 3 | 210 | 1.2% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-PLUSPLUS | 235 | 8 | 79 | 6.2% | 0 | 0 | total>=15 repo>=10 |
| JS-ARROW-BODY-STYLE | 231 | 8 | 147 | 23.4% | 0 | 0 | total>=15 repo>=10 |
| KT-NOT-NULL-ASSERTION | 223 | 1 | 223 | 12.8% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-UNUSED-EXPRESSIONS | 217 | 5 | 176 | 3.8% | 0 | 0 | total>=15 repo>=10 |
| JS-REQUIRE-AWAIT | 203 | 7 | 68 | 21.3% | 0 | 0 | total>=15 repo>=10 |
| TS-CONSISTENT-TYPE-DEFINITIONS | 197 | 7 | 131 | 11.3% | 0 | 0 | total>=15 repo>=10 |
| JS-OBJECT-SHORTHAND | 167 | 7 | 71 | 9.8% | 0 | 0 | total>=15 repo>=10 |
| TS-MAX-PARAMS | 163 | 5 | 141 | 3.5% | 0 | 0 | total>=15 repo>=10 |
| GO-MOD-ANY | 157 | 1 | 157 | 3.7% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-UNDERSCORE-DANGLE | 157 | 4 | 131 | 11.5% | 0 | 0 | total>=15 repo>=10 |
| TF-LIST-MAP-FUNCTIONS | 144 | 1 | 144 | 2.7% | 0 | 0 | total>=15 repo>=10 |
| TS-NO-UNSAFE-TYPE-ASSERTION | 139 | 4 | 114 | 4.2% | 0 | 0 | total>=15 repo>=10 |
| TS-BAN-TS-COMMENT-NOCHECK | 136 | 3 | 78 | 4.5% | 0 | 0 | total>=15 repo>=10 |
| JS-PREFER-NAMED-CAPTURE-GROUP | 120 | 7 | 67 | 3.7% | 0 | 0 | total>=15 repo>=10 |
| PY-REQUESTS-NO-TIMEOUT | 116 | 1 | 116 | 2.3% | 0 | 0 | total>=15 repo>=10 |
| TS-EXPLICIT-FUNCTION-RETURN-TYPE | 100 | 6 | 60 | 5.3% | 0 | 0 | total>=15 repo>=10 |
| TS-NO-EMPTY-OBJECT-TYPE | 97 | 3 | 87 | 1.2% | 0 | 0 | total>=15 repo>=10 |
| TS-TSIGNORE-001 | 92 | 3 | 83 | 8.9% | 0 | 0 | total>=15 repo>=10 |
| KT-EMPTY-CATCH | 84 | 1 | 84 | 4.3% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-EMPTY-FUNCTION | 83 | 3 | 68 | 4.3% | 0 | 0 | total>=15 repo>=10 |
| YAML-LINE-LENGTH | 82 | 18 | 12 | 4.2% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-EXTEND-NATIVE | 81 | 1 | 81 | 1.8% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-ELSE-RETURN | 78 | 7 | 56 | 3.5% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-VOID | 77 | 4 | 43 | 9.3% | 0 | 0 | total>=15 repo>=10 |
| PHP-URL-CREDENTIALS | 67 | 1 | 67 | 4.0% | 0 | 0 | total>=15 repo>=10 |
| TS-CALLBACK-ANY-001 | 67 | 4 | 25 | 2.1% | 0 | 0 | total>=15 repo>=10 |
| JS-DOT-NOTATION | 66 | 3 | 53 | 10.5% | 0 | 0 | total>=15 repo>=10 |
| VUE-HTML-BUTTON-HAS-TYPE | 62 | 3 | 43 | 6.2% | 0 | 0 | total>=15 repo>=10 |
| GO-MOD-TESTINGCONTEXT | 61 | 2 | 55 | 1.7% | 0 | 0 | total>=15 repo>=10 |
| YAML-EMPTY-VALUE | 60 | 11 | 27 | 3.0% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-NESTED-TERNARY | 59 | 6 | 37 | 2.2% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-PROMISE-EXECUTOR-RETURN | 57 | 7 | 32 | 2.1% | 0 | 0 | total>=15 repo>=10 |
| GO-HTTP-DEFAULT-CLIENT | 56 | 2 | 41 | 3.1% | 0 | 0 | total>=15 repo>=10 |
| JS-EQ-001 | 56 | 7 | 36 | 2.5% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-WARNING-COMMENTS | 56 | 5 | 38 | 7.1% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-EQ-NULL | 53 | 6 | 35 | 2.5% | 0 | 0 | total>=15 repo>=10 |
| JS-OPTCHAIN-001 | 49 | 4 | 39 | 3.7% | 0 | 0 | total>=15 repo>=10 |
| JSON-NON-ISO-DATE | 46 | 6 | 28 | 9.4% | 0 | 0 | total>=15 repo>=10 |
| KT-UNIT-RETURN | 42 | 1 | 42 | 3.0% | 0 | 0 | total>=15 repo>=10 |
| DOCKER-LATEST-TAG | 41 | 2 | 40 | 6.3% | 0 | 0 | total>=15 repo>=10 |
| PROTO-MIGRATE-TO-EDITIONS | 41 | 2 | 37 | 5.9% | 0 | 0 | total>=15 repo>=10 |
| JS-NODE-URL-PARSE-001 | 40 | 2 | 37 | 0.5% | 0 | 0 | total>=15 repo>=10 |
| PY-IN-DICT-KEYS | 39 | 2 | 37 | 0.9% | 0 | 0 | total>=15 repo>=10 |
| TS-CFG-TYPES-001 | 39 | 3 | 31 | 11.2% | 0 | 0 | total>=15 repo>=10 |
| TS-CONSISTENT-INDEXED-OBJECT-STYLE | 38 | 2 | 27 | 1.9% | 0 | 0 | total>=15 repo>=10 |
| TS-VUE-TS7-001 | 37 | 3 | 33 | 11.9% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-EMPTY | 36 | 3 | 34 | 1.5% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-MULTI-ASSIGN | 36 | 4 | 27 | 11.2% | 0 | 0 | total>=15 repo>=10 |
| YAML-COMMENT-SPACE | 36 | 4 | 18 | 2.4% | 0 | 0 | total>=15 repo>=10 |
| GO-INITIALISM-CASE | 35 | 2 | 27 | 8.6% | 0 | 0 | total>=15 repo>=10 |
| PROTO-FIELD-SNAKE-CASE | 33 | 2 | 32 | 0.8% | 0 | 0 | total>=15 repo>=10 |
| GO-MOD-FORVAR | 32 | 1 | 32 | 1.3% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-NEW | 32 | 3 | 24 | 0.8% | 0 | 0 | total>=15 repo>=10 |
| TS-CATCH-ANY-001 | 31 | 3 | 29 | 1.8% | 0 | 0 | total>=15 repo>=10 |
| GO-VET-COMPOSITES | 29 | 2 | 25 | 1.0% | 0 | 0 | total>=15 repo>=10 |
| JS-GUARD-FOR-IN | 28 | 4 | 12 | 2.4% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-NEGATED-CONDITION | 28 | 4 | 13 | 2.3% | 0 | 0 | total>=15 repo>=10 |
| TS-USE-UNKNOWN-IN-CATCH-CALLBACK-VARIABLE | 28 | 3 | 13 | 1.4% | 0 | 0 | total>=15 repo>=10 |
| COMPOSE-ENV-SECRET | 27 | 2 | 24 | 3.7% | 0 | 0 | total>=15 repo>=10 |
| DOCKER-FROM-AS-CASING | 26 | 2 | 25 | 4.5% | 0 | 0 | total>=15 repo>=10 |
| KT-STRING-CONCAT | 26 | 1 | 26 | 3.0% | 0 | 0 | total>=15 repo>=10 |
| JS-SYMBOL-DESCRIPTION | 25 | 3 | 19 | 1.5% | 0 | 0 | total>=15 repo>=10 |
| DOCKER-NO-CACHE-MOUNT | 24 | 1 | 24 | 3.7% | 0 | 0 | total>=15 repo>=10 |
| GO-MOD-ATOMICTYPES | 24 | 1 | 24 | 3.1% | 0 | 0 | total>=15 repo>=10 |
| PKG-DEP-LATEST-TAG | 24 | 3 | 21 | 7.6% | 0 | 0 | total>=15 repo>=10 |
| PHP-ERROR-SUPPRESSION | 23 | 1 | 23 | 5.1% | 0 | 0 | total>=15 repo>=10 |
| PROTO-ENUM-ZERO-VALUE-SUFFIX | 23 | 2 | 18 | 1.0% | 0 | 0 | total>=15 repo>=10 |
| COMPOSE-IMAGE-LATEST | 22 | 1 | 22 | 3.7% | 0 | 0 | total>=15 repo>=10 |
| PY-URL-CREDENTIALS | 22 | 1 | 22 | 1.5% | 0 | 0 | total>=15 repo>=10 |
| COMPOSE-DEPENDS-ON-NO-HEALTH | 20 | 1 | 20 | 3.5% | 0 | 0 | total>=15 repo>=10 |
| KT-TEMPLATE-BRACES | 20 | 1 | 20 | 1.4% | 0 | 0 | total>=15 repo>=10 |
| YAML-TRAILING-SPACES | 20 | 5 | 15 | 3.2% | 0 | 0 | total>=15 repo>=10 |
| DOCKER-APT-LISTS-NOT-REMOVED | 19 | 1 | 19 | 4.1% | 0 | 0 | total>=15 repo>=10 |
| JS-CAMELCASE | 19 | 2 | 18 | 0.5% | 0 | 0 | total>=15 repo>=10 |
| JS-NO-DUPLICATE-IMPORTS | 19 | 4 | 15 | 1.6% | 0 | 0 | total>=15 repo>=10 |
| SB-INJ-001 | 19 | 2 | 17 | 8.3% | 0 | 0 | total>=15 repo>=10 |
| JS-HASOWN-001 | 18 | 1 | 18 | 0.2% | 0 | 0 | total>=15 repo>=10 |
| GO-MOD-RANGEINT | 17 | 2 | 10 | 4.7% | 0 | 0 | total>=15 repo>=10 |
| JS-AT-001 | 17 | 3 | 12 | 1.8% | 0 | 0 | total>=15 repo>=10 |
| NG-CONSTRUCTOR-INJECTION | 17 | 1 | 17 | 19.8% | 0 | 0 | total>=15 repo>=10 |
| VUE-NO-STATIC-INLINE-STYLES | 17 | 1 | 17 | 1.8% | 0 | 0 | total>=15 repo>=10 |
| TS-NO-DYNAMIC-DELETE | 16 | 3 | 11 | 0.9% | 0 | 0 | total>=15 repo>=10 |
| TS-NO-EXTRANEOUS-CLASS | 16 | 4 | 11 | 1.2% | 0 | 0 | total>=15 repo>=10 |
| TS-PREFER-REDUCE-TYPE-PARAMETER | 16 | 1 | 16 | 2.4% | 0 | 0 | total>=15 repo>=10 |
| DOCKER-LEGACY-KEY-VALUE-FORMAT | 15 | 1 | 15 | 1.1% | 0 | 0 | total>=15 repo>=10 |
| JS-FUNC-NAMES | 15 | 3 | 10 | 1.4% | 0 | 0 | total>=15 repo>=10 |
| YAML-BRACKETS-SPACES | 21 | 6 | 6 | 2.3% | 0 | 0 | total>=15 |
| PY-TRY-EXCEPT-PASS | 18 | 2 | 9 | 5.4% | 0 | 0 | total>=15 |
| TS-NO-REDUNDANT-TYPE-CONSTITUENTS | 17 | 4 | 6 | 0.9% | 0 | 0 | total>=15 |
| JS-LOGICAL-ASSIGNMENT-OPERATORS | 15 | 4 | 9 | 1.4% | 0 | 0 | total>=15 |
| COMPOSE-CONTAINER-NAME | 14 | 1 | 14 | 1.9% | 0 | 0 | repo>=10 |
| TS-PREFER-FUNCTION-TYPE | 14 | 1 | 14 | 0.4% | 0 | 0 | repo>=10 |
| NUXT-APPDIR-001 | 13 | 2 | 12 | 4.3% | 0 | 0 | repo>=10 |
| JS-PREFER-REST-PARAMS | 12 | 2 | 11 | 1.9% | 0 | 0 | repo>=10 |
| KT-TRY-FINALLY-CLOSE | 12 | 1 | 12 | 1.6% | 0 | 0 | repo>=10 |
| DOCKER-COPY-SECRET-FILE | 11 | 2 | 10 | 2.2% | 0 | 0 | repo>=10 |
| GO-ERR-COMPARE-EQ | 11 | 1 | 11 | 0.8% | 0 | 0 | repo>=10 |
| GO-MOD-REFLECTTYPEFOR | 11 | 1 | 11 | 0.2% | 0 | 0 | repo>=10 |
| NG-INPUT-DECORATOR | 11 | 1 | 11 | 9.3% | 0 | 0 | repo>=10 |
| TS-ARRAY-TYPE | 11 | 1 | 11 | 0.7% | 0 | 0 | repo>=10 |
| TS-NO-INVALID-VOID-TYPE | 13 | 3 | 6 | 0.9% | 0 | 0 |  |
| TS-CONSISTENT-GENERIC-CONSTRUCTORS | 12 | 3 | 6 | 1.4% | 0 | 0 |  |
| JS-NO-UNDEF-INIT | 11 | 2 | 7 | 0.4% | 0 | 0 |  |
| JS-PROTO-001 | 11 | 2 | 9 | 0.7% | 0 | 0 |  |
| PY-OPEN-NO-ENCODING | 11 | 3 | 6 | 1.5% | 0 | 0 |  |
| TS-NAMESPACE-001 | 11 | 3 | 9 | 0.8% | 0 | 0 |  |
| YAML-NO-FINAL-NEWLINE | 11 | 5 | 5 | 1.5% | 0 | 0 |  |
| GO-REFLECT-PTR | 10 | 2 | 7 | 3.9% | 0 | 0 |  |
| JS-PREFER-OBJECT-SPREAD | 10 | 3 | 7 | 1.4% | 0 | 0 |  |
| PROTO-ENUM-VALUE-UPPER-SNAKE | 10 | 2 | 6 | 0.6% | 0 | 0 |  |
| VUE-SCOPED-ELEMENT-SELECTOR-001 | 10 | 3 | 8 | 2.4% | 0 | 0 |  |
| GO-SORT-STRINGS | 9 | 1 | 9 | 0.8% | 0 | 0 |  |
| TS-CFG-STRICT-001 | 9 | 4 | 4 | 2.3% | 0 | 0 |  |
| TS-PREFER-REGEXP-EXEC | 9 | 3 | 7 | 1.2% | 0 | 0 |  |
| GRAPHQL-NO-ANONYMOUS-OPERATIONS | 8 | 1 | 8 | 12.9% | 0 | 0 |  |
| JS-NO-PARAM-REASSIGN | 8 | 2 | 7 | 1.2% | 0 | 0 |  |
| SIMP-GO-IDX-NESTED-LOOP-NO-PONYTAIL | 8 | 3 | 4 | 4.6% | 0 | 0 |  |
| TS-NO-MIXED-ENUMS | 8 | 1 | 8 | 0.9% | 0 | 0 |  |
| JS-NO-IMPLICIT-COERCION | 7 | 1 | 7 | 1.9% | 0 | 0 |  |
| JS-PARSEINT-001 | 7 | 4 | 3 | 0.7% | 0 | 0 |  |
| NG-PLATFORM-BROWSER-DYNAMIC | 7 | 1 | 7 | 8.1% | 0 | 0 |  |
| PKG-INSTALL-SCRIPT | 7 | 7 | 1 | 2.1% | 0 | 0 |  |
| PROTO-FIELD-LANGUAGE-KEYWORD | 7 | 1 | 7 | 0.5% | 0 | 0 |  |
| PY-UNICODE-PREFIX | 7 | 1 | 7 | 0.8% | 0 | 0 |  |
| GO-MOD-BLOOP | 6 | 1 | 6 | 0.6% | 0 | 0 |  |
| JS-DEFAULT-CASE | 6 | 3 | 2 | 0.9% | 0 | 0 |  |
| JS-NO-ALERT | 6 | 3 | 3 | 0.9% | 0 | 0 |  |
| JS-NO-UNSAFE-OPTIONAL-CHAINING | 6 | 2 | 4 | 0.7% | 0 | 0 |  |
| SIMP-JAVA-LOOP-JOIN | 6 | 1 | 6 | 1.3% | 0 | 0 |  |
| VUE-NO-TEMPLATE-TARGET-BLANK | 6 | 1 | 6 | 1.5% | 0 | 0 |  |
| DOCKER-APT-NO-INSTALL-RECOMMENDS | 5 | 1 | 5 | 1.1% | 0 | 0 |  |
| GO-MOD-ERRORSASTYPE | 5 | 2 | 3 | 0.8% | 0 | 0 |  |
| GO-MOD-PLUSBUILD | 5 | 1 | 5 | 0.8% | 0 | 0 |  |
| GO-MOD-SLICESCONTAINS | 5 | 2 | 3 | 1.6% | 0 | 0 |  |
| GO-MOD-SORTSLICE-FUNC | 5 | 1 | 5 | 0.6% | 0 | 0 |  |
| GO-TEST-TEMPDIR | 5 | 1 | 5 | 7.7% | 0 | 0 |  |
| JS-NO-DUPE-KEYS | 5 | 1 | 5 | 0.2% | 0 | 0 |  |
| JS-NO-LABELS | 5 | 1 | 5 | 1.6% | 0 | 0 |  |
| PROTO-ENUM-MACRO-CONSTANT | 5 | 1 | 5 | 0.5% | 0 | 0 |  |
| PROTO-PACKAGE-VERSION-SUFFIX | 5 | 2 | 4 | 1.3% | 0 | 0 |  |
| PY-FLASK-DEBUG | 5 | 2 | 3 | 0.9% | 0 | 0 |  |
| PY-FSTRING-NO-PLACEHOLDER | 5 | 2 | 4 | 1.5% | 0 | 0 |  |
| TS-NO-REQUIRE-IMPORTS | 5 | 2 | 4 | 0.4% | 0 | 0 |  |
| COMPOSER-PHP-EOL | 4 | 2 | 3 | 1.7% | 0 | 0 |  |
| COMPOSER-REQ-STAR | 4 | 2 | 2 | 0.7% | 0 | 0 |  |
| GO-CTX-WITHVALUE-STRING-KEY | 4 | 2 | 2 | 3.1% | 0 | 0 |  |
| GO-DEFER-IN-LOOP | 4 | 2 | 3 | 4.6% | 0 | 0 |  |
| GO-ERROR-STRING-STYLE | 4 | 2 | 3 | 1.5% | 0 | 0 |  |
| GO-HTTP-LISTEN-NO-TIMEOUTS | 4 | 1 | 4 | 0.9% | 0 | 0 |  |
| GO-MOD-MAPSLOOP | 4 | 1 | 4 | 0.3% | 0 | 0 |  |
| GO-TLS-INSECURE-SKIP-VERIFY | 4 | 1 | 4 | 1.6% | 0 | 0 |  |
| JS-NO-USELESS-CALL | 4 | 3 | 2 | 0.3% | 0 | 0 |  |
| JS-NO-USELESS-COMPUTED-KEY | 4 | 1 | 4 | 0.3% | 0 | 0 |  |
| JS-NO-USELESS-CONCAT | 4 | 1 | 4 | 0.4% | 0 | 0 |  |
| JS-YODA | 4 | 1 | 4 | 0.5% | 0 | 0 |  |
| KT-DEPRECATED-NO-REPLACEWITH | 4 | 1 | 4 | 0.9% | 0 | 0 |  |
| KT-THROW-IAE-REQUIRE | 4 | 1 | 4 | 0.7% | 0 | 0 |  |
| MAVEN-COMPILER-SOURCE-TARGET | 4 | 1 | 4 | 0.4% | 0 | 0 |  |
| MAVEN-POM-EXPRESSIONS | 4 | 1 | 4 | 0.8% | 0 | 0 |  |
| NG-NG-CLASS-STYLE | 4 | 1 | 4 | 2.3% | 0 | 0 |  |
| NG-OUTPUT-DECORATOR | 4 | 1 | 4 | 4.7% | 0 | 0 |  |
| PROTO-ENUM-TITLECASE | 4 | 1 | 4 | 0.5% | 0 | 0 |  |
| PROTO-SERVICE-TITLECASE | 4 | 1 | 4 | 0.3% | 0 | 0 |  |
| PY-HARDCODED-PASSWORD | 4 | 1 | 4 | 1.3% | 0 | 0 |  |
| PY-REQUESTS-VERIFY-FALSE | 4 | 1 | 4 | 0.8% | 0 | 0 |  |
| REACT-UNUSED-REACT-IMPORT | 4 | 1 | 4 | 0.9% | 0 | 0 |  |
| SB-OSIV-001 | 4 | 2 | 2 | 1.5% | 0 | 0 |  |
| TS-NO-DUPLICATE-ENUM-VALUES | 4 | 1 | 4 | 0.4% | 0 | 0 |  |
| TS-PREFER-INCLUDES | 4 | 1 | 4 | 0.5% | 0 | 0 |  |
| COMPOSE-CAP-ADD-ALL | 3 | 1 | 3 | 0.4% | 0 | 0 |  |
| GO-HTTP-CLOSENOTIFIER | 3 | 1 | 3 | 1.6% | 0 | 0 |  |
| GO-MOD-WAITGROUPGO | 3 | 2 | 2 | 0.8% | 0 | 0 |  |
| GO-VET-UNREACHABLE | 3 | 2 | 2 | 1.5% | 0 | 0 |  |
| GRADLE-ALLPROJECTS-KTS | 3 | 1 | 3 | 0.2% | 0 | 0 |  |
| JS-NO-EMPTY-CHARACTER-CLASS | 3 | 1 | 3 | 0.1% | 0 | 0 |  |
| JS-OPERATOR-ASSIGNMENT | 3 | 2 | 2 | 0.4% | 0 | 0 |  |
| JS-PREFER-REGEX-LITERALS | 3 | 2 | 2 | 0.5% | 0 | 0 |  |
| NG-INPUT-SETTER | 3 | 1 | 3 | 3.5% | 0 | 0 |  |
| NG-STANDALONE-TRUE-REDUNDANT | 3 | 1 | 3 | 3.5% | 0 | 0 |  |
| PKG-NO-LICENSE | 3 | 2 | 2 | 0.7% | 0 | 0 |  |
| SIMP-JAVA-LOOP-ANYMATCH | 3 | 1 | 3 | 0.6% | 0 | 0 |  |
| TS-NO-IMPORT-TYPE-SIDE-EFFECTS | 3 | 2 | 2 | 0.6% | 0 | 0 |  |
| TS-NO-UNSAFE-FUNCTION-TYPE | 3 | 2 | 2 | 0.6% | 0 | 0 |  |
| VUE-NO-ROOT-V-IF | 3 | 1 | 3 | 0.9% | 0 | 0 |  |
| VUE-NO-V-TEXT | 3 | 2 | 2 | 2.1% | 0 | 0 |  |
| VUE-V-FOR-DELIMITER-STYLE | 3 | 2 | 2 | 0.7% | 0 | 0 |  |
| YAML-BRACES-SPACES | 3 | 2 | 2 | 0.8% | 0 | 0 |  |
| YAML-IMPLICIT-OCTAL | 3 | 2 | 2 | 0.9% | 0 | 0 |  |
| YAML-TRUTHY | 3 | 3 | 1 | 1.5% | 0 | 0 |  |
| COMPOSE-DOCKER-SOCKET | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| COMPOSE-VERSION-OBSOLETE | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| DOCKER-CURL-PIPE-SHELL | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| DOCKER-JSON-ARGS-RECOMMENDED | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| DOCKER-PIPE-WITHOUT-PIPEFAIL | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| GO-IOUTIL | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| GO-MOD-SLICESSORT | 2 | 1 | 2 | 0.2% | 0 | 0 |  |
| GO-RAND-V2 | 2 | 1 | 2 | 1.6% | 0 | 0 |  |
| GO-SQL-STRING-BUILD | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| GO-SYSCALL | 2 | 1 | 2 | 1.6% | 0 | 0 |  |
| GO-TEST-OS-SETENV | 2 | 1 | 2 | 0.8% | 0 | 0 |  |
| GO-UNSAFE-IMPORT | 2 | 1 | 2 | 1.6% | 0 | 0 |  |
| GRADLE-LEGACY-APPLY-PLUGIN-KTS | 2 | 1 | 2 | 0.2% | 0 | 0 |  |
| JAVA-COR-EQUALS-HASHCODE-001 | 2 | 1 | 2 | 0.6% | 0 | 0 |  |
| JAVA-COR-REQUIRENONNULL-001 | 2 | 1 | 2 | 0.6% | 0 | 0 |  |
| JAVA-COR-REQUIRENONNULLELSE-001 | 2 | 1 | 2 | 1.5% | 0 | 0 |  |
| JS-FOR-DIRECTION | 2 | 1 | 2 | 0.3% | 0 | 0 |  |
| JS-NEW-CAP | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| JS-NO-LONELY-IF | 2 | 1 | 2 | 0.3% | 0 | 0 |  |
| JS-NO-RETURN-ASSIGN | 2 | 2 | 1 | 2.1% | 0 | 0 |  |
| JS-NO-SCRIPT-URL | 2 | 1 | 2 | 0.5% | 0 | 0 |  |
| JS-PREFER-EXPONENTIATION-OPERATOR | 2 | 2 | 1 | 1.2% | 0 | 0 |  |
| JS-PRESERVE-CAUGHT-ERROR | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| KT-INSECURE-RANDOM | 2 | 1 | 2 | 0.5% | 0 | 0 |  |
| KT-KOTLINX-DATETIME-INSTANT | 2 | 1 | 2 | 0.5% | 0 | 0 |  |
| MAVEN-SOURCE-ENCODING-MISSING | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| MAVEN-VERSION-RANGE | 2 | 1 | 2 | 0.3% | 0 | 0 |  |
| PHP-NULL-COALESCE-ASSIGN | 2 | 1 | 2 | 1.1% | 0 | 0 |  |
| PKG-ENGINES-EOL-NODE | 2 | 2 | 1 | 0.7% | 0 | 0 |  |
| PKG-NAME-JS-NODE | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| PROTO-ENUM-ALLOW-ALIAS | 2 | 1 | 2 | 0.6% | 0 | 0 |  |
| PROTO-JAVA-OUTER-CLASSNAME | 2 | 1 | 2 | 0.6% | 0 | 0 |  |
| PROTO-PROTO2-REQUIRED | 2 | 1 | 2 | 0.2% | 0 | 0 |  |
| PY-BARE-EXCEPT | 2 | 2 | 1 | 0.4% | 0 | 0 |  |
| PY-GETATTR-CONSTANT | 2 | 1 | 2 | 0.8% | 0 | 0 |  |
| SIMP-GO-LOOP-INDEX | 2 | 1 | 2 | 0.2% | 0 | 0 |  |
| SIMP-JS-LOOP-SOME | 2 | 1 | 2 | 0.1% | 0 | 0 |  |
| SIMP-KT-IDX-MIDDLE-MAN | 2 | 1 | 2 | 0.5% | 0 | 0 |  |
| TS-BAN-TSLINT-COMMENT | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| TS-DEFAULT-PARAM-LAST | 2 | 2 | 1 | 0.7% | 0 | 0 |  |
| VUE-VFOR-KEY-001 | 2 | 1 | 2 | 0.6% | 0 | 0 |  |
| YAML-CRLF | 2 | 1 | 2 | 0.3% | 0 | 0 |  |
| YAML-URL-CREDENTIALS | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| COMPOSE-NETWORK-MODE-HOST | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| DOCKER-SUDO | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| GO-CTX-IN-STRUCT | 1 | 1 | 1 | 1.5% | 0 | 0 |  |
| GO-CTX-NIL | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| GO-MOD-IMPORTCOMMENT | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| GO-MOD-NEWEXPR | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| GO-MOD-SLICESBACKWARD | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| GO-MOD-STRINGSSEQ | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| GO-STRINGS-TITLE | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| GO-TEXT-TEMPLATE-HTML | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| GRADLE-BUILDDIR-KTS | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| GRADLE-KTS-DELEGATED-PROPERTIES-KTS | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| GRADLE-REPOS-IN-BUILD-SCRIPT-GROOVY | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| GRADLE-REPOS-IN-BUILD-SCRIPT-KTS | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| GRADLE-ROOT-PROJECT-NAME-KTS | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| GRAPHQL-SELECTION-SET-DEPTH | 1 | 1 | 1 | 1.6% | 0 | 0 |  |
| JAVA-MOD-STRINGTOKENIZER-001 | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| JAVA-MOD-UNNAMED-001 | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| JAVA-URL-001 | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| JS-ARRAY-CALLBACK-RETURN | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| JS-EQEQEQ-SMART | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| JS-EVAL-001 | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| JS-NO-CASE-DECLARATIONS | 1 | 1 | 1 | 0.5% | 0 | 0 |  |
| JS-NO-CONTROL-REGEX | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| JS-NO-DUPE-CLASS-MEMBERS | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| JS-NO-LONE-BLOCKS | 1 | 1 | 1 | 1.6% | 0 | 0 |  |
| JS-NO-TEMPLATE-CURLY-IN-STRING | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| JS-NODE-UTIL-IS-001 | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| JS-PREFER-SPREAD | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| JS-SUBSTR-001 | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| JS-THROW-LITERAL-001 | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| JS-WEB-MESSAGE-ORIGIN-001 | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| JS-WEB-POSTMESSAGE-STAR-001 | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| JS-WEB-SYNC-XHR-001 | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| KT-ARRAYLIST-CTOR | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| KT-SIZE-ZERO | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| NG-EVENT-HANDLER-NAMING | 1 | 1 | 1 | 1.2% | 0 | 0 |  |
| NG-ON-PUSH | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| NUXT-PLUGIN-PARALLEL-001 | 1 | 1 | 1 | 0.4% | 0 | 0 |  |
| NUXTUI-BUTTON-PADDED-TRUNCATE | 1 | 1 | 1 | 2.1% | 0 | 0 |  |
| NUXTUI-CHIP-SHOW | 1 | 1 | 1 | 2.1% | 0 | 0 |  |
| NUXTUI-TOOLTIP-SHORTCUTS | 1 | 1 | 1 | 2.1% | 0 | 0 |  |
| PHP-STRICT-TYPES-MISSING | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| PKG-DEP-TARBALL-URL | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| PKG-DEVENGINES-SUGGEST | 1 | 1 | 1 | 0.7% | 0 | 0 |  |
| PKG-EXPORTS-TYPES-NOT-FIRST | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| PKG-SCRIPT-PREPUBLISH | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| PROTO-MESSAGE-TITLECASE | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| PROTO-MONEY-AS-FLOAT | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| PROTO-PROTO2-GROUP | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| PROTO-SYNTAX-SPECIFIED | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| PY-PERCENT-FORMAT | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| PY-SUPER-ARGS | 1 | 1 | 1 | 0.4% | 0 | 0 |  |
| REACT-FORWARD-REF-UNNECESSARY | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| REACT-SETSTATE-FROM-THIS-STATE | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| SB-ACT-001 | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| SB-TX-INTERFACE-001 | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| SIMP-GO-IDX-GLOBAL-LOCK-NO-PONYTAIL | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| SIMP-GO-LOOP-REVERSE | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| SIMP-JAVA-IDX-NESTED-LOOP-NO-PONYTAIL | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| SIMP-JS-LOOP-FROMENTRIES | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| SIMP-KT-LOOP-ANY | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| SIMP-KT-LOOP-SUMOF | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| SIMP-PHP-IDX-NESTED-LOOP-NO-PONYTAIL | 1 | 1 | 1 | 0.6% | 0 | 0 |  |
| SIMP-PHP-LOOP-INARRAY | 1 | 1 | 1 | 0.6% | 0 | 0 |  |
| SIMP-PY-IDX-NESTED-LOOP-NO-PONYTAIL | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| TF-AWS-IAM-WILDCARD-ADMIN | 1 | 1 | 1 | 0.9% | 0 | 0 |  |
| TS-CFG-BASEURL-001 | 1 | 1 | 1 | 0.4% | 0 | 0 |  |
| TS-CFG-MODRES-001 | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| TS-NO-CONFUSING-NON-NULL-ASSERTION | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| TS-ONLY-THROW-ERROR | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| TS-PREFER-STRING-STARTS-ENDS-WITH | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| VUE-EOL-001 | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| VUE-NO-DUPLICATE-ATTR-INHERITANCE | 1 | 1 | 1 | 1.2% | 0 | 0 |  |
| VUE-NO-NEGATED-V-IF-CONDITION | 1 | 1 | 1 | 0.4% | 0 | 0 |  |
| VUE-NO-SIDE-EFFECTS-IN-COMPUTED-PROPERTIES | 1 | 1 | 1 | 2.1% | 0 | 0 |  |
| VUE-REQUIRE-PROP-TYPES | 1 | 1 | 1 | 0.4% | 0 | 0 |  |
| VUE-SIMPLE-EXPRESSIONS-001 | 1 | 1 | 1 | 2.1% | 0 | 0 |  |
| YAML-VERSION-LIST-AS-FLOAT | 1 | 1 | 1 | 0.7% | 0 | 0 |  |
| TS-NONNULL-001 | 0 | 0 | 0 | 0.0% | 707 | 0 |  |
| JS-CLASS-METHODS-USE-THIS | 0 | 0 | 0 | 0.0% | 419 | 0 |  |
| KT-VAR-NEVER-REASSIGNED | 0 | 0 | 0 | 0.0% | 257 | 0 |  |
| PROTO-MESSAGE-SEPARATE-FILES | 0 | 0 | 0 | 0.0% | 135 | 0 |  |
| TS-NO-UNNECESSARY-BOOLEAN-LITERAL-COMPARE | 0 | 0 | 0 | 0.0% | 99 | 0 |  |
| PROTO-REPEATED-FIELD-PLURAL | 0 | 0 | 0 | 0.0% | 86 | 0 |  |
| COMPOSE-READ-ONLY | 0 | 0 | 0 | 0.0% | 80 | 0 |  |
| TS-CFG-EXACTOPTIONAL-001 | 0 | 0 | 0 | 0.0% | 71 | 0 |  |
| TS-CFG-NOIMPLICITOVERRIDE-001 | 0 | 0 | 0 | 0.0% | 70 | 0 |  |
| COMPOSE-PORT-ALL-INTERFACES | 0 | 0 | 0 | 0.0% | 69 | 0 |  |
| TS-CFG-NOFALLTHROUGH-001 | 0 | 0 | 0 | 0.0% | 69 | 0 |  |
| TS-CFG-NOUNCHECKEDINDEXED-001 | 0 | 0 | 0 | 0.0% | 69 | 0 |  |
| TS-CFG-NOIMPLICITRETURNS-001 | 0 | 0 | 0 | 0.0% | 68 | 0 |  |
| JS-WEB-MATH-RANDOM-SECURITY-001 | 0 | 0 | 0 | 0.0% | 58 | 0 |  |
| DOCKER-NO-DIGEST | 0 | 0 | 0 | 0.0% | 52 | 0 |  |
| GRAPHQL-LIST-FIELD-NOT-PAGINATED | 0 | 0 | 0 | 0.0% | 52 | 0 |  |
| JS-FORIN-ARRAY-001 | 0 | 0 | 0 | 0.0% | 52 | 0 |  |
| GO-PANIC-IN-INIT-ERR | 0 | 0 | 0 | 0.0% | 50 | 0 |  |
| COMPOSE-RESTART-MISSING | 0 | 0 | 0 | 0.0% | 41 | 0 |  |
| TS-PREFER-FOR-OF | 0 | 0 | 0 | 0.0% | 34 | 0 |  |
| JS-NULLISH-001 | 0 | 0 | 0 | 0.0% | 32 | 0 |  |
| MAVEN-PLUGIN-METAVERSION-MISSING | 0 | 0 | 0 | 0.0% | 31 | 0 |  |
| DOCKER-NO-USER | 0 | 0 | 0 | 0.0% | 30 | 0 |  |
| GO-HTTP-BODY-NOT-CLOSED | 0 | 0 | 0 | 0.0% | 29 | 0 |  |
| GRADLE-DEPENDS-ON-KTS | 0 | 0 | 0 | 0.0% | 29 | 0 |  |
| JS-NO-BITWISE | 0 | 0 | 0 | 0.0% | 27 | 0 |  |
| TS-NO-FLOATING-PROMISES | 0 | 0 | 0 | 0.0% | 25 | 0 |  |
| PY-RAISE-WITHOUT-FROM | 0 | 0 | 0 | 0.0% | 20 | 0 |  |
| JS-WEB-SORT-DEFAULT-001 | 0 | 0 | 0 | 0.0% | 19 | 0 |  |
| PHP-HASH-COMPARE | 0 | 0 | 0 | 0.0% | 19 | 0 |  |
| GO-PANIC-FOR-ERRORS | 0 | 0 | 0 | 0.0% | 18 | 0 |  |
| JAVA-OPT-002 | 0 | 0 | 0 | 0.0% | 18 | 0 |  |
| VUE-SCOPED-001 | 0 | 0 | 0 | 0.0% | 16 | 0 |  |
| JS-AWAIT-LOOP-001 | 0 | 0 | 0 | 0.0% | 15 | 0 |  |
| MAVEN-SNAPSHOT-DEPENDENCY | 0 | 0 | 0 | 0.0% | 15 | 0 |  |
| PKG-DEVTOOL-IN-DEPENDENCIES | 0 | 0 | 0 | 0.0% | 15 | 0 |  |
| VUE-URL-INJECTION-001 | 0 | 0 | 0 | 0.0% | 15 | 0 |  |
| TS-NO-ARRAY-DELETE | 0 | 0 | 0 | 0.0% | 14 | 0 |  |
| JAVA-MOD-COMPACT-MAIN-001 | 0 | 0 | 0 | 0.0% | 13 | 0 |  |
| DOCKER-HEALTHCHECK-MISSING | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| KT-WHEN-SUBJECT-ELSE | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| SIMP-KT-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| TS-PREFER-NULLISH-COALESCING | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| SIMP-JS-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 10 | 0 |  |
| GO-VET-UNMARSHAL | 0 | 0 | 0 | 0.0% | 9 | 0 |  |
| SB-TX-001 | 0 | 0 | 0 | 0.0% | 9 | 0 |  |
| SIMP-GO-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 9 | 0 |  |
| TS-SATISFIES-001 | 0 | 0 | 0 | 0.0% | 9 | 0 |  |
| GO-ERRORF-NO-WRAP | 0 | 0 | 0 | 0.0% | 8 | 0 |  |
| JS-WEB-FETCH-OK-001 | 0 | 0 | 0 | 0.0% | 7 | 0 |  |
| PY-PICKLE-LOADS | 0 | 0 | 0 | 0.0% | 7 | 0 |  |
| SIMP-JAVA-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 7 | 0 |  |
| PHP-JSON-DECODE-NO-THROW | 0 | 0 | 0 | 0.0% | 6 | 0 |  |
| GRADLE-DEPENDS-ON-GROOVY | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| JAVA-SEC-RANDOM-001 | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| JSON-HTTP-URL | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| MAVEN-SKIP-TESTS | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| PKG-MAIN-AND-EXPORTS-DIVERGE | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| REACT-JSX-KEY-INDEX | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| JAVA-RES-OBJECTOUTPUTSTREAM-001 | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| JAVA-SEC-DESER-001 | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| JAVA-SEC-SERIAL-FILTER-002 | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| JS-JSON-CLONE-001 | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| NUXT-SERVER-UNVALIDATED-BODY-001 | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| PY-BIND-ALL-INTERFACES | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| REACT-SET-STATE-IN-EFFECT | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| DOCKER-COPY-ALL-BEFORE-INSTALL | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| GO-VET-LOOPCLOSURE | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| JS-INNERHTML-001 | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| JS-NO-LOOP-FUNC | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| KT-DATA-OBJECT | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| KT-FUNCTION-NAMING | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| KT-UNSAFE-CAST | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| PHP-IN-ARRAY-LOOSE | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| PROTO-ANY-PREFER-EXTENSIONS | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| REACT-CLASS-COMPONENT | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| REACT-FETCH-EFFECT-NO-CLEANUP | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| REACT-MANUAL-MEMO-WITH-COMPILER | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| SIMP-JS-HELPER-DEEPCLONE | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| TS-CFG-DECORATORS-001 | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| COMPOSER-DEVTOOL-IN-REQUIRE | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| JAVA-CONC-EXECUTOR-CLOSE-001 | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| JAVA-MOD-STRINGBUFFER-001 | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| KT-JAVA-DESERIALIZATION | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| NUXT-NUXT4-PENDING-001 | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| PY-EVAL | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| SB-TX-CHECKED-001 | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| SIMP-GO-LOOP-MAPKEYS | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| SIMP-PHP-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| TF-DEPENDS-ON-LAST-RESORT | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| JAVA-COR-TOLOWER-LOCALE-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JAVA-DEP-FILE-TOURL-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JAVA-MOD-STREAM-TOLIST-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JAVA-RES-SERVERSOCKET-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JAVA-RES-SOCKET-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JS-REQUIRE-ATOMIC-UPDATES | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JSON-SECRET-FIELD | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| NG-TEMPLATE-INNERHTML-BYPASS | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| NUXT-COOKIE-SENSITIVE-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| PROTO-WKT-TIMESTAMP | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| PY-HASH-WEAK | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| REACT-EFFECT-NO-DEPS | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| SB-CFG-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| SIMP-PY-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| YAML-SECRET-FIELD | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| GO-MATH-RAND-SECURITY | 0 | 0 | 0 | 0.0% | 0 | 0 |  |
| JS-NO-PROTOTYPE-BUILTINS | 0 | 0 | 0 | 0.0% | 0 | 0 |  |
| PROTO-RPC-STANDARD-MESSAGE-NAMES | 0 | 0 | 0 | 0.0% | 0 | 0 |  |
| PROTO-SERVICE-SUFFIX | 0 | 0 | 0 | 0.0% | 0 | 0 |  |
| TS-NO-THIS-ALIAS | 0 | 0 | 0 | 0.0% | 0 | 0 |  |

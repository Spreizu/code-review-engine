# Corpus run "t6" (oss)

Reported = confirmed (review list with AI off); pending = ai-confirm candidates (shown only after high-confidence AI confirmation); shadow = quarantined rules.

| repo | files | reported | pending | ms | error |
|---|---|---|---|---|---|
| angular-realworld | 86 | 22 | 49 | 4106 |  |
| awesome-compose | 463 | 61 | 587 | 5523 |  |
| axios | 487 | 10 | 241 | 17219 |  |
| cobra | 65 | 19 | 9 | 1774 |  |
| express | 214 | 8 | 34 | 6619 |  |
| flask | 235 | 5 | 10 | 2919 |  |
| gin | 128 | 41 | 64 | 4183 |  |
| grpc-gateway | 629 | 64 | 608 | 12065 |  |
| gson | 313 | 29 | 122 | 7849 |  |
| guzzle | 176 | 12 | 29 | 7479 |  |
| nuxt-examples | 278 | 6 | 214 | 6259 |  |
| nuxt-ui-dashboard | 47 | 6 | 12 | 3834 |  |
| okio | 438 | 36 | 541 | 9177 |  |
| pinia | 337 | 32 | 262 | 9261 |  |
| requests | 130 | 15 | 40 | 2022 |  |
| slim | 145 | 4 | 11 | 2142 |  |
| spring-petclinic | 132 | 14 | 55 | 2562 |  |
| swapi-graphql | 62 | 31 | 55 | 1167 |  |
| terraform-aws-vpc | 111 | 3 | 5 | 1910 |  |
| vitesse | 80 | 1 | 19 | 3317 |  |
| zod | 739 | 41 | 1497 | 56302 |  |
| zustand | 142 | 3 | 43 | 8479 |  |

## Per pack

| pack | reported | pending | shadow |
|---|---|---|---|
| angular | 23 | 29 | 0 |
| composer | 8 | 2 | 0 |
| docker | 20 | 505 | 0 |
| go | 79 | 410 | 0 |
| gradle | 10 | 34 | 0 |
| graphql | 9 | 52 | 0 |
| java | 9 | 57 | 0 |
| javascript | 51 | 387 | 0 |
| json | 0 | 5 | 0 |
| kotlin | 21 | 477 | 0 |
| maven | 12 | 51 | 0 |
| nuxt | 1 | 20 | 0 |
| nuxt-ui | 3 | 0 | 0 |
| package-json | 18 | 44 | 0 |
| php | 6 | 28 | 0 |
| protobuf | 45 | 322 | 0 |
| python | 24 | 53 | 0 |
| react | 6 | 19 | 0 |
| simplify-go | 12 | 11 | 0 |
| simplify-java | 10 | 7 | 0 |
| simplify-javascript | 3 | 11 | 0 |
| simplify-kotlin | 4 | 11 | 0 |
| simplify-php | 2 | 2 | 0 |
| simplify-python | 1 | 1 | 0 |
| spring-boot | 8 | 12 | 0 |
| taint | 0 | 7 | 0 |
| terraform | 1 | 2 | 0 |
| typescript | 39 | 1859 | 0 |
| vue | 21 | 31 | 0 |
| yaml | 17 | 58 | 0 |

## Per rule (flagged first)

Flags: total >= 15, >= 10 in one repo, or >= 25% of a repo's files.

| rule | reported | repos | max/repo | file share | pending | shadow | flags |
|---|---|---|---|---|---|---|---|
| JS-PROTO-001 | 11 | 2 | 9 | 0.7% | 0 | 0 |  |
| TS-NAMESPACE-001 | 11 | 3 | 9 | 0.8% | 0 | 0 |  |
| GO-REFLECT-PTR | 10 | 2 | 7 | 3.9% | 0 | 0 |  |
| PROTO-ENUM-VALUE-UPPER-SNAKE | 10 | 2 | 6 | 0.6% | 0 | 0 |  |
| VUE-SCOPED-ELEMENT-SELECTOR-001 | 10 | 3 | 8 | 2.4% | 0 | 0 |  |
| GO-SORT-STRINGS | 9 | 1 | 9 | 0.8% | 0 | 0 |  |
| JS-NO-CONSOLE | 9 | 1 | 9 | 4.8% | 0 | 0 |  |
| GO-INITIALISM-CASE | 8 | 1 | 8 | 4.7% | 0 | 0 |  |
| GRAPHQL-NO-ANONYMOUS-OPERATIONS | 8 | 1 | 8 | 12.9% | 0 | 0 |  |
| PY-OPEN-NO-ENCODING | 8 | 3 | 6 | 1.5% | 0 | 0 |  |
| SIMP-GO-IDX-NESTED-LOOP-NO-PONYTAIL | 8 | 3 | 4 | 4.6% | 0 | 0 |  |
| TS-NO-MIXED-ENUMS | 8 | 1 | 8 | 0.9% | 0 | 0 |  |
| YAML-NO-FINAL-NEWLINE | 8 | 3 | 5 | 1.5% | 0 | 0 |  |
| NG-PLATFORM-BROWSER-DYNAMIC | 7 | 1 | 7 | 8.1% | 0 | 0 |  |
| PKG-INSTALL-SCRIPT | 7 | 7 | 1 | 2.1% | 0 | 0 |  |
| PROTO-FIELD-LANGUAGE-KEYWORD | 7 | 1 | 7 | 0.5% | 0 | 0 |  |
| TS-USE-UNKNOWN-IN-CATCH-CALLBACK-VARIABLE | 7 | 2 | 4 | 1.2% | 0 | 0 |  |
| SIMP-JAVA-LOOP-JOIN | 6 | 1 | 6 | 1.3% | 0 | 0 |  |
| VUE-NO-TEMPLATE-TARGET-BLANK | 6 | 1 | 6 | 1.5% | 0 | 0 |  |
| DOCKER-APT-NO-INSTALL-RECOMMENDS | 5 | 1 | 5 | 1.1% | 0 | 0 |  |
| GO-MOD-PLUSBUILD | 5 | 1 | 5 | 0.8% | 0 | 0 |  |
| GO-TEST-TEMPDIR | 5 | 1 | 5 | 7.7% | 0 | 0 |  |
| JS-NO-DUPE-KEYS | 5 | 1 | 5 | 0.2% | 0 | 0 |  |
| JS-NO-LABELS | 5 | 1 | 5 | 1.6% | 0 | 0 |  |
| KT-EMPTY-CATCH | 5 | 1 | 5 | 0.9% | 0 | 0 |  |
| PROTO-ENUM-MACRO-CONSTANT | 5 | 1 | 5 | 0.5% | 0 | 0 |  |
| PROTO-PACKAGE-VERSION-SUFFIX | 5 | 2 | 4 | 1.3% | 0 | 0 |  |
| PY-FLASK-DEBUG | 5 | 2 | 3 | 0.9% | 0 | 0 |  |
| PY-FSTRING-NO-PLACEHOLDER | 5 | 2 | 4 | 1.5% | 0 | 0 |  |
| COMPOSER-PHP-EOL | 4 | 2 | 3 | 1.7% | 0 | 0 |  |
| COMPOSER-REQ-STAR | 4 | 2 | 2 | 0.7% | 0 | 0 |  |
| GO-CTX-WITHVALUE-STRING-KEY | 4 | 2 | 2 | 3.1% | 0 | 0 |  |
| GO-DEFER-IN-LOOP | 4 | 2 | 3 | 4.6% | 0 | 0 |  |
| GO-ERROR-STRING-STYLE | 4 | 2 | 3 | 1.5% | 0 | 0 |  |
| GO-HTTP-LISTEN-NO-TIMEOUTS | 4 | 1 | 4 | 0.9% | 0 | 0 |  |
| GO-TLS-INSECURE-SKIP-VERIFY | 4 | 1 | 4 | 1.6% | 0 | 0 |  |
| JS-EQ-001 | 4 | 2 | 3 | 1.6% | 0 | 0 |  |
| KT-THROW-IAE-REQUIRE | 4 | 1 | 4 | 0.7% | 0 | 0 |  |
| MAVEN-COMPILER-SOURCE-TARGET | 4 | 1 | 4 | 0.4% | 0 | 0 |  |
| MAVEN-POM-EXPRESSIONS | 4 | 1 | 4 | 0.8% | 0 | 0 |  |
| NG-NG-CLASS-STYLE | 4 | 1 | 4 | 2.3% | 0 | 0 |  |
| NG-OUTPUT-DECORATOR | 4 | 1 | 4 | 4.7% | 0 | 0 |  |
| PROTO-ENUM-TITLECASE | 4 | 1 | 4 | 0.5% | 0 | 0 |  |
| PROTO-SERVICE-TITLECASE | 4 | 1 | 4 | 0.3% | 0 | 0 |  |
| PY-REQUESTS-VERIFY-FALSE | 4 | 1 | 4 | 0.8% | 0 | 0 |  |
| REACT-UNUSED-REACT-IMPORT | 4 | 1 | 4 | 0.9% | 0 | 0 |  |
| SB-OSIV-001 | 4 | 2 | 2 | 1.5% | 0 | 0 |  |
| TS-NO-REQUIRE-IMPORTS | 4 | 1 | 4 | 0.4% | 0 | 0 |  |
| COMPOSE-CAP-ADD-ALL | 3 | 1 | 3 | 0.4% | 0 | 0 |  |
| GO-HTTP-CLOSENOTIFIER | 3 | 1 | 3 | 1.6% | 0 | 0 |  |
| GRADLE-ALLPROJECTS-KTS | 3 | 1 | 3 | 0.2% | 0 | 0 |  |
| JS-NO-UNUSED-EXPRESSIONS | 3 | 1 | 3 | 1.6% | 0 | 0 |  |
| NG-INPUT-SETTER | 3 | 1 | 3 | 3.5% | 0 | 0 |  |
| NG-STANDALONE-TRUE-REDUNDANT | 3 | 1 | 3 | 3.5% | 0 | 0 |  |
| PHP-ERROR-SUPPRESSION | 3 | 1 | 3 | 1.7% | 0 | 0 |  |
| PKG-NO-LICENSE | 3 | 2 | 2 | 0.7% | 0 | 0 |  |
| SIMP-JAVA-LOOP-ANYMATCH | 3 | 1 | 3 | 0.6% | 0 | 0 |  |
| TS-NO-UNSAFE-FUNCTION-TYPE | 3 | 2 | 2 | 0.6% | 0 | 0 |  |
| YAML-IMPLICIT-OCTAL | 3 | 2 | 2 | 0.9% | 0 | 0 |  |
| YAML-TRUTHY | 3 | 3 | 1 | 1.5% | 0 | 0 |  |
| COMPOSE-DOCKER-SOCKET | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| COMPOSE-VERSION-OBSOLETE | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| DOCKER-CURL-PIPE-SHELL | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| DOCKER-JSON-ARGS-RECOMMENDED | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| DOCKER-PIPE-WITHOUT-PIPEFAIL | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| GO-IOUTIL | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| GO-RAND-V2 | 2 | 1 | 2 | 1.6% | 0 | 0 |  |
| GO-SQL-STRING-BUILD | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| GO-SYSCALL | 2 | 1 | 2 | 1.6% | 0 | 0 |  |
| GO-TEST-OS-SETENV | 2 | 1 | 2 | 0.8% | 0 | 0 |  |
| GO-UNSAFE-IMPORT | 2 | 1 | 2 | 1.6% | 0 | 0 |  |
| GRADLE-LEGACY-APPLY-PLUGIN-KTS | 2 | 1 | 2 | 0.2% | 0 | 0 |  |
| JAVA-COR-EQUALS-HASHCODE-001 | 2 | 1 | 2 | 0.6% | 0 | 0 |  |
| JAVA-COR-REQUIRENONNULL-001 | 2 | 1 | 2 | 0.6% | 0 | 0 |  |
| JAVA-COR-REQUIRENONNULLELSE-001 | 2 | 1 | 2 | 1.5% | 0 | 0 |  |
| JS-NO-SCRIPT-URL | 2 | 1 | 2 | 0.5% | 0 | 0 |  |
| JS-VAR-001 | 2 | 1 | 2 | 3.2% | 0 | 0 |  |
| KT-DEPRECATED-NO-REPLACEWITH | 2 | 1 | 2 | 0.5% | 0 | 0 |  |
| KT-INSECURE-RANDOM | 2 | 1 | 2 | 0.5% | 0 | 0 |  |
| KT-KOTLINX-DATETIME-INSTANT | 2 | 1 | 2 | 0.5% | 0 | 0 |  |
| KT-STRING-CONCAT | 2 | 1 | 2 | 0.5% | 0 | 0 |  |
| KT-TEMPLATE-BRACES | 2 | 1 | 2 | 0.2% | 0 | 0 |  |
| MAVEN-SOURCE-ENCODING-MISSING | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| MAVEN-VERSION-RANGE | 2 | 1 | 2 | 0.3% | 0 | 0 |  |
| PHP-NULL-COALESCE-ASSIGN | 2 | 1 | 2 | 1.1% | 0 | 0 |  |
| PKG-ENGINES-EOL-NODE | 2 | 2 | 1 | 0.7% | 0 | 0 |  |
| PKG-NAME-JS-NODE | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| PROTO-ENUM-ALLOW-ALIAS | 2 | 1 | 2 | 0.6% | 0 | 0 |  |
| PROTO-JAVA-OUTER-CLASSNAME | 2 | 1 | 2 | 0.6% | 0 | 0 |  |
| PROTO-PROTO2-REQUIRED | 2 | 1 | 2 | 0.2% | 0 | 0 |  |
| PY-BARE-EXCEPT | 2 | 2 | 1 | 0.4% | 0 | 0 |  |
| SB-INJ-001 | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| SIMP-GO-LOOP-INDEX | 2 | 1 | 2 | 0.2% | 0 | 0 |  |
| SIMP-JS-LOOP-SOME | 2 | 1 | 2 | 0.1% | 0 | 0 |  |
| SIMP-KT-IDX-MIDDLE-MAN | 2 | 1 | 2 | 0.5% | 0 | 0 |  |
| TS-DEFAULT-PARAM-LAST | 2 | 2 | 1 | 0.7% | 0 | 0 |  |
| VUE-VFOR-KEY-001 | 2 | 1 | 2 | 0.6% | 0 | 0 |  |
| YAML-URL-CREDENTIALS | 2 | 1 | 2 | 0.4% | 0 | 0 |  |
| COMPOSE-NETWORK-MODE-HOST | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| DOCKER-SUDO | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| GO-CTX-IN-STRUCT | 1 | 1 | 1 | 1.5% | 0 | 0 |  |
| GO-CTX-NIL | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| GO-MOD-IMPORTCOMMENT | 1 | 1 | 1 | 0.8% | 0 | 0 |  |
| GO-MOD-NEWEXPR | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
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
| JS-EVAL-001 | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| JS-NO-CASE-DECLARATIONS | 1 | 1 | 1 | 0.5% | 0 | 0 |  |
| JS-NO-LONE-BLOCKS | 1 | 1 | 1 | 1.6% | 0 | 0 |  |
| JS-NO-TEMPLATE-CURLY-IN-STRING | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| JS-NODE-UTIL-IS-001 | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| JS-SUBSTR-001 | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
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
| TS-CFG-TYPES-001 | 1 | 1 | 1 | 0.4% | 0 | 0 |  |
| TS-NO-CONFUSING-NON-NULL-ASSERTION | 1 | 1 | 1 | 0.1% | 0 | 0 |  |
| TS-ONLY-THROW-ERROR | 1 | 1 | 1 | 0.3% | 0 | 0 |  |
| VUE-EOL-001 | 1 | 1 | 1 | 0.2% | 0 | 0 |  |
| VUE-NO-SIDE-EFFECTS-IN-COMPUTED-PROPERTIES | 1 | 1 | 1 | 2.1% | 0 | 0 |  |
| VUE-SIMPLE-EXPRESSIONS-001 | 1 | 1 | 1 | 2.1% | 0 | 0 |  |
| YAML-VERSION-LIST-AS-FLOAT | 1 | 1 | 1 | 0.7% | 0 | 0 |  |
| TS-NONNULL-001 | 0 | 0 | 0 | 0.0% | 707 | 0 |  |
| TS-ANY-001 | 0 | 0 | 0 | 0.0% | 355 | 0 |  |
| KT-VAR-NEVER-REASSIGNED | 0 | 0 | 0 | 0.0% | 257 | 0 |  |
| GO-MOD-ANY | 0 | 0 | 0 | 0.0% | 157 | 0 |  |
| KT-NOT-NULL-ASSERTION | 0 | 0 | 0 | 0.0% | 144 | 0 |  |
| PROTO-MESSAGE-SEPARATE-FILES | 0 | 0 | 0 | 0.0% | 135 | 0 |  |
| TS-NO-EMPTY-OBJECT-TYPE | 0 | 0 | 0 | 0.0% | 93 | 0 |  |
| TS-TSIGNORE-001 | 0 | 0 | 0 | 0.0% | 92 | 0 |  |
| PROTO-REPEATED-FIELD-PLURAL | 0 | 0 | 0 | 0.0% | 86 | 0 |  |
| COMPOSE-READ-ONLY | 0 | 0 | 0 | 0.0% | 80 | 0 |  |
| TS-CFG-EXACTOPTIONAL-001 | 0 | 0 | 0 | 0.0% | 71 | 0 |  |
| TS-CFG-NOIMPLICITOVERRIDE-001 | 0 | 0 | 0 | 0.0% | 70 | 0 |  |
| COMPOSE-PORT-ALL-INTERFACES | 0 | 0 | 0 | 0.0% | 69 | 0 |  |
| TS-CFG-NOFALLTHROUGH-001 | 0 | 0 | 0 | 0.0% | 69 | 0 |  |
| TS-CFG-NOUNCHECKEDINDEXED-001 | 0 | 0 | 0 | 0.0% | 69 | 0 |  |
| TS-CFG-NOIMPLICITRETURNS-001 | 0 | 0 | 0 | 0.0% | 68 | 0 |  |
| TS-CALLBACK-ANY-001 | 0 | 0 | 0 | 0.0% | 63 | 0 |  |
| GO-MOD-TESTINGCONTEXT | 0 | 0 | 0 | 0.0% | 61 | 0 |  |
| JS-WEB-MATH-RANDOM-SECURITY-001 | 0 | 0 | 0 | 0.0% | 58 | 0 |  |
| DOCKER-NO-DIGEST | 0 | 0 | 0 | 0.0% | 52 | 0 |  |
| GRAPHQL-LIST-FIELD-NOT-PAGINATED | 0 | 0 | 0 | 0.0% | 52 | 0 |  |
| JS-FORIN-ARRAY-001 | 0 | 0 | 0 | 0.0% | 52 | 0 |  |
| JS-OPTCHAIN-001 | 0 | 0 | 0 | 0.0% | 49 | 0 |  |
| KT-UNIT-RETURN | 0 | 0 | 0 | 0.0% | 42 | 0 |  |
| COMPOSE-RESTART-MISSING | 0 | 0 | 0 | 0.0% | 41 | 0 |  |
| DOCKER-LATEST-TAG | 0 | 0 | 0 | 0.0% | 41 | 0 |  |
| PROTO-MIGRATE-TO-EDITIONS | 0 | 0 | 0 | 0.0% | 41 | 0 |  |
| JS-NODE-URL-PARSE-001 | 0 | 0 | 0 | 0.0% | 40 | 0 |  |
| TS-BAN-TS-COMMENT-NOCHECK | 0 | 0 | 0 | 0.0% | 40 | 0 |  |
| YAML-LINE-LENGTH | 0 | 0 | 0 | 0.0% | 39 | 0 |  |
| JS-NO-EMPTY | 0 | 0 | 0 | 0.0% | 36 | 0 |  |
| PROTO-FIELD-SNAKE-CASE | 0 | 0 | 0 | 0.0% | 33 | 0 |  |
| GO-MOD-FORVAR | 0 | 0 | 0 | 0.0% | 32 | 0 |  |
| JS-NULLISH-001 | 0 | 0 | 0 | 0.0% | 32 | 0 |  |
| MAVEN-PLUGIN-METAVERSION-MISSING | 0 | 0 | 0 | 0.0% | 31 | 0 |  |
| DOCKER-NO-USER | 0 | 0 | 0 | 0.0% | 30 | 0 |  |
| GO-VET-COMPOSITES | 0 | 0 | 0 | 0.0% | 29 | 0 |  |
| GRADLE-DEPENDS-ON-KTS | 0 | 0 | 0 | 0.0% | 29 | 0 |  |
| COMPOSE-ENV-SECRET | 0 | 0 | 0 | 0.0% | 27 | 0 |  |
| DOCKER-FROM-AS-CASING | 0 | 0 | 0 | 0.0% | 26 | 0 |  |
| TS-NO-FLOATING-PROMISES | 0 | 0 | 0 | 0.0% | 25 | 0 |  |
| DOCKER-NO-CACHE-MOUNT | 0 | 0 | 0 | 0.0% | 24 | 0 |  |
| GO-HTTP-BODY-NOT-CLOSED | 0 | 0 | 0 | 0.0% | 24 | 0 |  |
| GO-MOD-ATOMICTYPES | 0 | 0 | 0 | 0.0% | 24 | 0 |  |
| PKG-DEP-LATEST-TAG | 0 | 0 | 0 | 0.0% | 24 | 0 |  |
| PROTO-ENUM-ZERO-VALUE-SUFFIX | 0 | 0 | 0 | 0.0% | 23 | 0 |  |
| COMPOSE-IMAGE-LATEST | 0 | 0 | 0 | 0.0% | 22 | 0 |  |
| COMPOSE-DEPENDS-ON-NO-HEALTH | 0 | 0 | 0 | 0.0% | 20 | 0 |  |
| PY-RAISE-WITHOUT-FROM | 0 | 0 | 0 | 0.0% | 20 | 0 |  |
| TS-CFG-STRICT-001 | 0 | 0 | 0 | 0.0% | 20 | 0 |  |
| DOCKER-APT-LISTS-NOT-REMOVED | 0 | 0 | 0 | 0.0% | 19 | 0 |  |
| JS-NO-DUPLICATE-IMPORTS | 0 | 0 | 0 | 0.0% | 19 | 0 |  |
| JS-WEB-SORT-DEFAULT-001 | 0 | 0 | 0 | 0.0% | 19 | 0 |  |
| PHP-HASH-COMPARE | 0 | 0 | 0 | 0.0% | 19 | 0 |  |
| JAVA-OPT-002 | 0 | 0 | 0 | 0.0% | 18 | 0 |  |
| JS-HASOWN-001 | 0 | 0 | 0 | 0.0% | 18 | 0 |  |
| TS-CATCH-ANY-001 | 0 | 0 | 0 | 0.0% | 18 | 0 |  |
| YAML-TRAILING-SPACES | 0 | 0 | 0 | 0.0% | 18 | 0 |  |
| JS-AT-001 | 0 | 0 | 0 | 0.0% | 17 | 0 |  |
| NG-CONSTRUCTOR-INJECTION | 0 | 0 | 0 | 0.0% | 17 | 0 |  |
| TS-NO-REDUNDANT-TYPE-CONSTITUENTS | 0 | 0 | 0 | 0.0% | 17 | 0 |  |
| TS-NO-DYNAMIC-DELETE | 0 | 0 | 0 | 0.0% | 16 | 0 |  |
| VUE-SCOPED-001 | 0 | 0 | 0 | 0.0% | 16 | 0 |  |
| DOCKER-LEGACY-KEY-VALUE-FORMAT | 0 | 0 | 0 | 0.0% | 15 | 0 |  |
| JS-AWAIT-LOOP-001 | 0 | 0 | 0 | 0.0% | 15 | 0 |  |
| MAVEN-SNAPSHOT-DEPENDENCY | 0 | 0 | 0 | 0.0% | 15 | 0 |  |
| PKG-DEVTOOL-IN-DEPENDENCIES | 0 | 0 | 0 | 0.0% | 15 | 0 |  |
| VUE-URL-INJECTION-001 | 0 | 0 | 0 | 0.0% | 15 | 0 |  |
| COMPOSE-CONTAINER-NAME | 0 | 0 | 0 | 0.0% | 14 | 0 |  |
| TS-NO-ARRAY-DELETE | 0 | 0 | 0 | 0.0% | 14 | 0 |  |
| JAVA-MOD-COMPACT-MAIN-001 | 0 | 0 | 0 | 0.0% | 13 | 0 |  |
| NUXT-APPDIR-001 | 0 | 0 | 0 | 0.0% | 13 | 0 |  |
| TS-NO-INVALID-VOID-TYPE | 0 | 0 | 0 | 0.0% | 13 | 0 |  |
| GO-PANIC-FOR-ERRORS | 0 | 0 | 0 | 0.0% | 12 | 0 |  |
| KT-TRY-FINALLY-CLOSE | 0 | 0 | 0 | 0.0% | 12 | 0 |  |
| DOCKER-COPY-SECRET-FILE | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| DOCKER-HEALTHCHECK-MISSING | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| GO-ERR-COMPARE-EQ | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| GO-MOD-REFLECTTYPEFOR | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| KT-WHEN-SUBJECT-ELSE | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| NG-INPUT-DECORATOR | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| SIMP-KT-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| TS-PREFER-NULLISH-COALESCING | 0 | 0 | 0 | 0.0% | 11 | 0 |  |
| JS-CURLY | 0 | 0 | 0 | 0.0% | 10 | 0 |  |
| SIMP-JS-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 10 | 0 |  |
| GO-MOD-RANGEINT | 0 | 0 | 0 | 0.0% | 9 | 0 |  |
| PY-TRY-EXCEPT-PASS | 0 | 0 | 0 | 0.0% | 9 | 0 |  |
| SB-TX-001 | 0 | 0 | 0 | 0.0% | 9 | 0 |  |
| SIMP-GO-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 9 | 0 |  |
| TS-PREFER-REGEXP-EXEC | 0 | 0 | 0 | 0.0% | 9 | 0 |  |
| TS-SATISFIES-001 | 0 | 0 | 0 | 0.0% | 9 | 0 |  |
| GO-ERRORF-NO-WRAP | 0 | 0 | 0 | 0.0% | 8 | 0 |  |
| PY-COOKIE-INSECURE | 0 | 0 | 0 | 0.0% | 8 | 0 |  |
| JS-WEB-FETCH-OK-001 | 0 | 0 | 0 | 0.0% | 7 | 0 |  |
| PY-PICKLE-LOADS | 0 | 0 | 0 | 0.0% | 7 | 0 |  |
| SIMP-JAVA-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 7 | 0 |  |
| GO-MOD-BLOOP | 0 | 0 | 0 | 0.0% | 6 | 0 |  |
| PHP-JSON-DECODE-NO-THROW | 0 | 0 | 0 | 0.0% | 6 | 0 |  |
| GO-MOD-ERRORSASTYPE | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| GO-MOD-SORTSLICE-FUNC | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| GRADLE-DEPENDS-ON-GROOVY | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| JAVA-SEC-RANDOM-001 | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| JSON-HTTP-URL | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| MAVEN-SKIP-TESTS | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| PKG-MAIN-AND-EXPORTS-DIVERGE | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| REACT-JSX-KEY-INDEX | 0 | 0 | 0 | 0.0% | 5 | 0 |  |
| GO-MOD-MAPSLOOP | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| JAVA-RES-OBJECTOUTPUTSTREAM-001 | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| JAVA-SEC-DESER-001 | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| JAVA-SEC-SERIAL-FILTER-002 | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| JS-JSON-CLONE-001 | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| NUXT-SERVER-UNVALIDATED-BODY-001 | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| PY-BIND-ALL-INTERFACES | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| REACT-SET-STATE-IN-EFFECT | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| TS-NO-DUPLICATE-ENUM-VALUES | 0 | 0 | 0 | 0.0% | 4 | 0 |  |
| DOCKER-COPY-ALL-BEFORE-INSTALL | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| GO-MOD-WAITGROUPGO | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| GO-VET-LOOPCLOSURE | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| JS-INNERHTML-001 | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| JS-NO-EMPTY-CHARACTER-CLASS | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| KT-DATA-OBJECT | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| KT-FUNCTION-NAMING | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| KT-UNSAFE-CAST | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| PHP-IN-ARRAY-LOOSE | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| PROTO-ANY-PREFER-EXTENSIONS | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| REACT-CLASS-COMPONENT | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| REACT-FETCH-EFFECT-NO-CLEANUP | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| REACT-MANUAL-MEMO-WITH-COMPILER | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| TAINT-JS-XSS | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| TS-CFG-DECORATORS-001 | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| TS-NO-IMPORT-TYPE-SIDE-EFFECTS | 0 | 0 | 0 | 0.0% | 3 | 0 |  |
| COMPOSER-DEVTOOL-IN-REQUIRE | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| GO-MOD-SLICESSORT | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| GO-VET-UNMARSHAL | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| JAVA-CONC-EXECUTOR-CLOSE-001 | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| JAVA-MOD-STRINGBUFFER-001 | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| JS-PRESERVE-CAUGHT-ERROR | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| KT-JAVA-DESERIALIZATION | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| NUXT-NUXT4-PENDING-001 | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| PY-EVAL | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| PY-GETATTR-CONSTANT | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| SB-TX-CHECKED-001 | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| SIMP-GO-LOOP-MAPKEYS | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| SIMP-PHP-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| TAINT-JS-PATH | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| TF-DEPENDS-ON-LAST-RESORT | 0 | 0 | 0 | 0.0% | 2 | 0 |  |
| GO-MOD-SLICESBACKWARD | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| GO-PANIC-IN-INIT-ERR | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JAVA-COR-TOLOWER-LOCALE-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JAVA-DEP-FILE-TOURL-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JAVA-MOD-STREAM-TOLIST-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JAVA-RES-SERVERSOCKET-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JAVA-RES-SOCKET-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JS-NO-CONTROL-REGEX | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JS-NO-DUPE-CLASS-MEMBERS | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| JS-REQUIRE-ATOMIC-UPDATES | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| NG-TEMPLATE-INNERHTML-BYPASS | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| NUXT-COOKIE-SENSITIVE-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| PROTO-WKT-TIMESTAMP | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| PY-HASH-WEAK | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| REACT-EFFECT-NO-DEPS | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| SB-CFG-001 | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| SIMP-JS-HELPER-DEEPCLONE | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| SIMP-PY-IDX-DUPLICATE-HELPER | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| TAINT-GO-PATH | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| TAINT-JS-REDIRECT | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| YAML-SECRET-FIELD | 0 | 0 | 0 | 0.0% | 1 | 0 |  |
| GO-MATH-RAND-SECURITY | 0 | 0 | 0 | 0.0% | 0 | 0 |  |
| JS-NO-PROTOTYPE-BUILTINS | 0 | 0 | 0 | 0.0% | 0 | 0 |  |
| PROTO-RPC-STANDARD-MESSAGE-NAMES | 0 | 0 | 0 | 0.0% | 0 | 0 |  |
| PROTO-SERVICE-SUFFIX | 0 | 0 | 0 | 0.0% | 0 | 0 |  |
| TS-NO-THIS-ALIAS | 0 | 0 | 0 | 0.0% | 0 | 0 |  |

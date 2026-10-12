# Official documentation sources (update-pipeline seed list)

Every URL below returned HTTP 200 when checked on **2026-10-09** (Europe/Tallinn); the URLs that were found broken that day are listed at the end so nobody adds them back. The machine-readable twin of this file is [`sources.yaml`](sources.yaml); the `crev docs` pipeline (PLAN.md §7) reads it.

**Fetch strategy legend:** `html` = fetch the rendered page and pull out the main content · `md` = raw Markdown from the docs' own git repo (best for diffing) · `gh-wiki` = clone the GitHub wiki git repo · `gh-rel` = GitHub Releases API (version discovery) · `jep` = JEP page, where the Status/Release header is parsed.

Latest versions observed on 2026-10-09 (from GitHub releases/tags and the OpenJDK project page): JDK 27 (GA 2026-09-15, non-LTS; 25 is the current LTS) · Spring Boot 4.1.1 (4.2.0-M2 in progress; 3.5.x and 4.0.x still being patched) · Spring Framework 7.0.9 docs · Vue 3.5.43 (3.6.0-rc.10) · Nuxt 4.6.0 (3.21.x still maintained; Nuxt 5 in development) · TypeScript 7.0.2 (native Go port, released 2026-07-08) and 6.0.3 · ECMAScript 2026 (Temporal and Explicit Resource Management are listed for ES2027).

---

## 1. Java (OpenJDK / Oracle)

| Topic | URL | Version | Fetch |
|---|---|---|---|
| JDK release index (GA dates) | https://openjdk.org/projects/jdk/ | 10 to 28 | html |
| JDK 17 / 21 / 25 / 26 / 27 feature lists | https://openjdk.org/projects/jdk/17/ · https://openjdk.org/projects/jdk/21/ · https://openjdk.org/projects/jdk/25/ · https://openjdk.org/projects/jdk/26/ · https://openjdk.org/projects/jdk/27/ | per release | html |
| JEP 361 Switch Expressions | https://openjdk.org/jeps/361 | 14 | jep |
| JEP 378 Text Blocks | https://openjdk.org/jeps/378 | 15 | jep |
| JEP 390 Warnings for Value-Based Classes | https://openjdk.org/jeps/390 | 16 | jep |
| JEP 394 Pattern Matching for instanceof | https://openjdk.org/jeps/394 | 16 | jep |
| JEP 395 Records | https://openjdk.org/jeps/395 | 16 | jep |
| JEP 403 Strongly Encapsulate JDK Internals | https://openjdk.org/jeps/403 | 17 | jep |
| JEP 409 Sealed Classes | https://openjdk.org/jeps/409 | 17 | jep |
| JEP 411 Deprecate the Security Manager for Removal | https://openjdk.org/jeps/411 | 17 | jep |
| JEP 400 UTF-8 by Default | https://openjdk.org/jeps/400 | 18 | jep |
| JEP 413 Code Snippets in Java API Documentation | https://openjdk.org/jeps/413 | 18 | jep |
| JEP 421 Deprecate Finalization for Removal | https://openjdk.org/jeps/421 | 18 | jep |
| JEP 431 Sequenced Collections | https://openjdk.org/jeps/431 | 21 | jep |
| JEP 440 Record Patterns | https://openjdk.org/jeps/440 | 21 | jep |
| JEP 441 Pattern Matching for switch | https://openjdk.org/jeps/441 | 21 | jep |
| JEP 444 Virtual Threads | https://openjdk.org/jeps/444 | 21 | jep |
| JEP 456 Unnamed Variables & Patterns | https://openjdk.org/jeps/456 | 22 | jep |
| JEP 467 Markdown Documentation Comments | https://openjdk.org/jeps/467 | 23 | jep |
| JEP 471 Deprecate sun.misc.Unsafe memory-access methods | https://openjdk.org/jeps/471 | 23 | jep |
| JEP 486 Permanently Disable the Security Manager | https://openjdk.org/jeps/486 | 24 | jep |
| JEP 491 Synchronize Virtual Threads without Pinning | https://openjdk.org/jeps/491 | 24 | jep |
| JEP 498 Warn upon Use of Unsafe Memory-Access Methods | https://openjdk.org/jeps/498 | 24 | jep |
| JEP 506 Scoped Values | https://openjdk.org/jeps/506 | 25 | jep |
| JEP 512 Compact Source Files and Instance Main Methods | https://openjdk.org/jeps/512 | 25 | jep |
| JEP 513 Flexible Constructor Bodies | https://openjdk.org/jeps/513 | 25 | jep |
| JEP 500 Prepare to Make Final Mean Final | https://openjdk.org/jeps/500 | 26 | jep |
| JEP 504 Remove the Applet API | https://openjdk.org/jeps/504 | 26 | jep |
| Virtual Threads guide (adoption guide, pinning) | https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html | SE 21 | html |
| Deprecated API list | https://docs.oracle.com/en/java/javase/21/docs/api/deprecated-list.html · https://docs.oracle.com/en/java/javase/25/docs/api/deprecated-list.html | SE 21 / 25 | html (best signal for deprecation diffs) |
| JDK Migration Guide | https://docs.oracle.com/en/java/javase/21/migrate/index.html · https://docs.oracle.com/en/java/javase/25/migrate/index.html | SE 21 / 25 | html |
| Release notes (Oracle JDK) | https://www.oracle.com/java/technologies/javase/21-relnote-issues.html · https://www.oracle.com/java/technologies/javase/25-relnote-issues.html | 21 / 25 | html |
| API: Optional | https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Optional.html (also /21/) | SE 25 | html |
| API: Thread | https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html (also /21/) | SE 25 | html |
| API: URL | https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/URL.html (also /21/) | SE 25 | html |
| API: Locale | https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Locale.html (also /21/) | SE 25 | html |

## 2. Spring Boot / Spring Framework / Spring Security

| Topic | URL | Version | Fetch |
|---|---|---|---|
| Releases (version discovery) | https://api.github.com/repos/spring-projects/spring-boot/releases | all | gh-rel |
| Support timeline | https://spring.io/projects/spring-boot | current | html |
| 2.7 Release Notes | https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.7-Release-Notes | 2.7 | gh-wiki (`git clone https://github.com/spring-projects/spring-boot.wiki.git`) |
| 3.0 Migration Guide | https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide | 3.0 | gh-wiki |
| 3.2 Release Notes | https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.2-Release-Notes | 3.2 | gh-wiki |
| 3.4 Release Notes | https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.4-Release-Notes | 3.4 | gh-wiki |
| 4.0 Migration Guide | https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide | 4.0 | gh-wiki |
| 4.0 / 4.1 Release Notes | https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Release-Notes · https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.1-Release-Notes | 4.0 / 4.1 | gh-wiki |
| Reference: Spring Beans and DI | https://docs.spring.io/spring-boot/reference/using/spring-beans-and-dependency-injection.html | current (4.x) | html |
| Reference: Externalized Configuration | https://docs.spring.io/spring-boot/reference/features/external-config.html | current | html |
| Reference: SpringApplication (virtual threads) | https://docs.spring.io/spring-boot/reference/features/spring-application.html | current | html |
| Reference: SQL Databases (open-in-view) | https://docs.spring.io/spring-boot/reference/data/sql.html | current | html |
| Reference: Actuator Endpoints | https://docs.spring.io/spring-boot/reference/actuator/endpoints.html | current | html |
| Reference: Testing Spring Boot Applications | https://docs.spring.io/spring-boot/reference/testing/spring-boot-applications.html | current | html |
| Reference: Calling REST Services | https://docs.spring.io/spring-boot/reference/io/rest-client.html | current | html |
| Reference: Creating Your Own Auto-configuration | https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html | current | html |
| Appendix: Application Properties | https://docs.spring.io/spring-boot/appendix/application-properties/index.html | current | html (good for detecting property renames) |
| Framework: Dependency Injection | https://docs.spring.io/spring-framework/reference/core/beans/dependencies/factory-collaborators.html | 7.0 | html |
| Framework: Using @Transactional | https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html | 7.0 | html |
| Framework: REST Clients | https://docs.spring.io/spring-framework/reference/integration/rest-clients.html | 7.0.9 | html |
| Framework upgrade guides | https://github.com/spring-projects/spring-framework/wiki/Upgrading-to-Spring-Framework-6.x · https://github.com/spring-projects/spring-framework/wiki/Upgrading-to-Spring-Framework-7.x | 6.x / 7.x | gh-wiki |
| Security: Authorize HttpServletRequests | https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html | current (7.x) | html |
| Security: CSRF | https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html | current | html |
| Security: WebSecurityConfigurerAdapter removal (official blog) | https://spring.io/blog/2022/02/21/spring-security-without-the-websecurityconfigureradapter | 5.7 | html |

## 3. Vue

| Topic | URL | Version | Fetch |
|---|---|---|---|
| Releases / changelog | https://api.github.com/repos/vuejs/core/releases · https://raw.githubusercontent.com/vuejs/core/main/CHANGELOG.md | 3.x | gh-rel / md |
| Style Guide (index + priorities) | https://vuejs.org/style-guide/ · https://vuejs.org/style-guide/rules-essential.html · https://vuejs.org/style-guide/rules-strongly-recommended.html · https://vuejs.org/style-guide/rules-use-with-caution.html | Vue 3 docs | md: https://raw.githubusercontent.com/vuejs/docs/main/src/style-guide/rules-essential.md |
| Reactivity Fundamentals | https://vuejs.org/guide/essentials/reactivity-fundamentals.html | 3.x | html/md |
| Computed | https://vuejs.org/guide/essentials/computed.html | 3.x | html/md |
| Watchers | https://vuejs.org/guide/essentials/watchers.html | 3.x | html/md |
| List rendering | https://vuejs.org/guide/essentials/list.html | 3.x | html/md |
| Props | https://vuejs.org/guide/components/props.html | 3.x | html/md |
| Security | https://vuejs.org/guide/best-practices/security.html | 3.x | html/md |
| `<script setup>` | https://vuejs.org/api/sfc-script-setup.html | 3.x | html/md |
| Composition API FAQ | https://vuejs.org/guide/extras/composition-api-faq.html | 3.x | html/md |
| LLM-friendly docs index | https://vuejs.org/llms.txt | 3.x | md |
| Vue 3.5 announcement | https://blog.vuejs.org/posts/vue-3-5 | 3.5 | html |
| Vue 2.7 announcement / migration | https://blog.vuejs.org/posts/vue-2-7-naruto · https://v2.vuejs.org/v2/guide/migration-vue-2-7.html | 2.7 | html |
| Vue 2 EOL | https://v2.vuejs.org/eol/ | 2.x | html |
| Vue 2 slots (deprecated syntax) | https://v2.vuejs.org/v2/guide/components-slots.html | 2.6+ | html |
| Vue 3 Migration Guide: breaking changes index | https://v3-migration.vuejs.org/breaking-changes/ | 2 to 3 | md: repo https://github.com/vuejs/v3-migration-guide |
| Migration pages used by rules | …/breaking-changes/filters.html · events-api.html · listeners-removed.html · v-model.html · v-on-native-modifier-removed.html · v-if-v-for.html · global-api.html · global-api-treeshaking.html · keycode-modifiers.html · children.html · inline-template-attribute.html · emits-option.html · slots-unification.html · functional-components.html · data-option.html · key-attribute.html · watch.html | 2 to 3 | md |
| eslint-plugin-vue rule index (cross-reference) | https://eslint.vuejs.org/rules/ (e.g. no-v-html, no-mutating-props, multi-word-component-names, require-v-for-key, no-use-v-if-with-v-for, no-deprecated-filter, no-deprecated-events-api, no-deprecated-dollar-listeners-api, no-deprecated-v-on-native-modifier, no-deprecated-destroyed-lifecycle, no-side-effects-in-computed-properties, no-setup-props-reactivity-loss, require-explicit-emits, no-async-in-computed-properties, no-deprecated-v-bind-sync, no-deprecated-dollar-scopedslots-api) | latest | html |

## 4. Nuxt

| Topic | URL | Version | Fetch |
|---|---|---|---|
| Releases | https://api.github.com/repos/nuxt/nuxt/releases | 3.x / 4.x | gh-rel |
| Docs source (diff-friendly) | https://github.com/nuxt/nuxt/tree/main/docs (e.g. https://raw.githubusercontent.com/nuxt/nuxt/main/docs/1.getting-started/18.upgrade.md) | 4.x | md |
| LLM-friendly docs index | https://nuxt.com/llms.txt | 4.x | md |
| LLM-friendly full docs | https://nuxt.com/llms-full.txt | 4.x | md |
| Nuxt UI LLM docs (index / full) | https://ui.nuxt.com/llms.txt · https://ui.nuxt.com/llms-full.txt | Nuxt UI 4.x | md |
| Nuxt UI official AI skill (MIT, checklist only) | https://raw.githubusercontent.com/nuxt/ui/v4/skills/nuxt-ui/SKILL.md | Nuxt UI 4.x | md |
| Nuxt UI releases | https://api.github.com/repos/nuxt/ui/releases | 4.x | gh-rel |
| Payload LLM docs (index / full) | https://payloadcms.com/llms.txt · https://payloadcms.com/llms-full.txt | Payload 3.x | md |
| Payload official AI skill (MIT, checklist only) | https://raw.githubusercontent.com/payloadcms/payload/main/packages/payload/skills/payload/SKILL.md | Payload 3.x/4.x | md |
| Payload releases | https://api.github.com/repos/payloadcms/payload/releases | 3.x / 4.x | gh-rel |
| Upgrade Guide (Nuxt 3 to 4, Nuxt 5 preview) | https://nuxt.com/docs/getting-started/upgrade | 4.x | md |
| Nuxt 4 announcement | https://nuxt.com/blog/v4 | 4.0 | html |
| Nuxt 2 EOL | https://nuxt.com/blog/nuxt2-eol | 2.x | html |
| Migration (Nuxt 2 to 3): overview, configuration, component options, plugins & middleware, meta, runtime config, pages & layouts, auto-imports | https://nuxt.com/docs/migration/overview · https://nuxt.com/docs/migration/configuration · https://nuxt.com/docs/migration/component-options · https://nuxt.com/docs/migration/plugins-and-middleware · https://nuxt.com/docs/migration/meta · https://nuxt.com/docs/migration/runtime-config · https://nuxt.com/docs/migration/pages-and-layouts · https://nuxt.com/docs/migration/auto-imports | 2 to 3 | md |
| Data fetching | https://nuxt.com/docs/getting-started/data-fetching | 4.x | md |
| State management | https://nuxt.com/docs/getting-started/state-management | 4.x | md |
| Runtime config | https://nuxt.com/docs/guide/going-further/runtime-config | 4.x | md |
| API: useState / useFetch / useAsyncData / useHead | https://nuxt.com/docs/api/composables/use-state · https://nuxt.com/docs/api/composables/use-fetch · https://nuxt.com/docs/api/composables/use-async-data · https://nuxt.com/docs/api/composables/use-head | 4.x | md |
| API: navigateTo / NuxtLink / import.meta | https://nuxt.com/docs/api/utils/navigate-to · https://nuxt.com/docs/api/components/nuxt-link · https://nuxt.com/docs/api/advanced/import-meta | 4.x | md |
| Nuxt 2 docs (legacy behaviour) | https://v2.nuxt.com/docs/features/data-fetching · https://v2.nuxt.com/docs/configuration-glossary/configuration-runtime-config | 2.x | html |

## 5. TypeScript

| Topic | URL | Version | Fetch |
|---|---|---|---|
| Releases | https://api.github.com/repos/microsoft/TypeScript/releases | all | gh-rel |
| Announcements (blog) | https://devblogs.microsoft.com/typescript/ | all | html |
| TypeScript 7.0 announcement | https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/ | 7.0 | html |
| TS 6 to 7 behavioural differences | https://github.com/microsoft/typescript-go/blob/main/CHANGES.md | 7.0 | md |
| Release notes (diff-friendly source) | https://raw.githubusercontent.com/microsoft/TypeScript-Website/v2/packages/documentation/copy/en/release-notes/TypeScript%205.0.md (same pattern per version) | per version | md |
| Release notes 3.7, 3.8, 3.9, 4.4, 4.9, 5.0, 5.2, 5.5, 5.8, 5.9, 6.0 | https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-7.html · …-3-8.html · …-3-9.html · …-4-4.html · …-4-9.html · …-5-0.html · …-5-2.html · …-5-5.html · …-5-8.html · …-5-9.html · …-6-0.html | per version | html |
| TSConfig reference | https://www.typescriptlang.org/tsconfig/ | current | html |
| Do's and Don'ts | https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html | current | html |
| Enums (const enum pitfalls) | https://www.typescriptlang.org/docs/handbook/enums.html | current | html |
| Namespaces and Modules | https://www.typescriptlang.org/docs/handbook/namespaces-and-modules.html | current | html |
| Everyday Types / Narrowing | https://www.typescriptlang.org/docs/handbook/2/everyday-types.html · https://www.typescriptlang.org/docs/handbook/2/narrowing.html | current | html |
| typescript-eslint rules (cross-reference) | https://typescript-eslint.io/rules/ (no-explicit-any, no-floating-promises, no-misused-promises, consistent-type-imports, no-non-null-assertion, ban-ts-comment, no-wrapper-object-types, no-namespace, prefer-nullish-coalescing) | latest | html |

## 6. JavaScript (ECMAScript / MDN / TC39)

| Topic | URL | Version | Fetch |
|---|---|---|---|
| TC39 finished proposals (edition per feature) | https://github.com/tc39/proposals/blob/main/finished-proposals.md (raw: https://raw.githubusercontent.com/tc39/proposals/main/finished-proposals.md) | ES2016 to ES2027 | md (**main signal for new modernization rules**) |
| ECMA-262 living draft / editions | https://tc39.es/ecma262/ · https://tc39.es/ecma262/2025/ · https://262.ecma-international.org/16.0/ | living / ES2025 | html |
| MDN Deprecated & obsolete features | https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Deprecated_and_obsolete_features | living | md via https://github.com/mdn/content |
| MDN pages used by rules | Statements/var · Statements/let · Equality_comparisons_and_sameness · Global_Objects/eval · Statements/with · Statements/for...in · Global_Objects/Object/hasOwn · Operators/Nullish_coalescing · Operators/Optional_chaining · Global_Objects/Array/forEach · Global_Objects/Promise/Promise · Global_Objects/parseInt · Global_Objects/String/substr · Global_Objects/Object/proto · Global_Objects/escape · Global_Objects/Date/getYear · Global_Objects/Array/toSorted · Global_Objects/Array/at · Global_Objects/Object/groupBy · Statements/for-await...of · Operators/await · Functions/arguments/callee · Strict_mode (all under https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/); Web API: https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML · https://developer.mozilla.org/en-US/docs/Web/API/Window/structuredClone | living | md: https://raw.githubusercontent.com/mdn/content/main/files/en-us/web/javascript/reference/<path>/index.md |
| ESLint core rules (cross-reference) | https://eslint.org/docs/latest/rules/ (no-var, eqeqeq, no-eval, no-implied-eval, prefer-const, no-prototype-builtins, no-await-in-loop, no-async-promise-executor, radix, no-with, no-caller, no-new-wrappers, no-throw-literal, no-promise-executor-return) | latest | html |

## 7. Parser / tooling sources (engine dependencies, also tracked)

| Topic | URL | Notes |
|---|---|---|
| Official Go bindings | https://github.com/tree-sitter/go-tree-sitter | latest tag v0.24.0 only supports grammar ABI ≤14; master (pseudo-version v0.24.1-0.20251112183152-c9492002f76e) loads ABI 15 |
| smacker bindings | https://github.com/smacker/go-tree-sitter | last commit 2024-08-27; bundled grammars include java/javascript/typescript but **no vue** |
| Grammars | https://github.com/tree-sitter/tree-sitter-java · https://github.com/tree-sitter/tree-sitter-javascript · https://github.com/tree-sitter/tree-sitter-typescript · https://github.com/tree-sitter-grammars/tree-sitter-vue | java/js/ts ship `bindings/go`; vue does not (vendored in `internal/grammars/vue`) |

---

### URLs found broken on 2026-10-09 (do not add back)
- https://jdk.java.net/25/release-notes and https://jdk.java.net/26/release-notes (404). Use the Oracle `*-relnote-issues.html` pages or the openjdk.org project pages.
- https://docs.spring.io/spring-security/reference/migration-7/configuration.html, https://docs.spring.io/spring-security/reference/migration-7.html, https://docs.spring.io/spring-security/reference/5.8/migration/servlet/config.html (404)
- https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/structuredClone (404; the page lives under Web/API/Window/structuredClone)
- raw.githubusercontent.com/wiki/... for the Spring Boot wiki (404). Clone `spring-boot.wiki.git` instead.

<!-- BEGIN GENERATED CITATIONS -->

## 8. Rule citation index (generated by `tools/rulegen/sources.py`)

Every URL a rule cites, grouped by ecosystem, with the number of rules citing it. All were fetched (HTTP 200) and every rule's `source.quote` was found verbatim (whitespace/case-normalised) on the page on 2026-10-09 by `tools/rulegen/rulegen.py verify`.

### java (182 URLs, 312 rule citations)

| URL | Kind | Rules |
|---|---|---|
| https://assertj.github.io/doc/ | reference | 2 |
| https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html | reference | 3 |
| https://checkstyle.org/checks/blocks/emptyblock.html | reference | 1 |
| https://checkstyle.org/checks/blocks/emptycatchblock.html | reference | 1 |
| https://checkstyle.org/checks/coding/defaultcomeslast.html | reference | 1 |
| https://checkstyle.org/checks/coding/illegalcatch.html | reference | 1 |
| https://checkstyle.org/checks/coding/magicnumber.html | reference | 1 |
| https://checkstyle.org/checks/coding/missingswitchdefault.html | reference | 1 |
| https://checkstyle.org/checks/coding/nestedifdepth.html | reference | 1 |
| https://checkstyle.org/checks/coding/parameterassignment.html | reference | 1 |
| https://checkstyle.org/checks/coding/returncount.html | reference | 1 |
| https://checkstyle.org/checks/coding/simplifybooleanexpression.html | reference | 2 |
| https://checkstyle.org/checks/coding/simplifybooleanreturn.html | reference | 1 |
| https://checkstyle.org/checks/coding/unnecessaryparentheses.html | reference | 1 |
| https://checkstyle.org/checks/coding/unusedlocalvariable.html | reference | 1 |
| https://checkstyle.org/checks/imports/unusedimports.html | reference | 1 |
| https://checkstyle.org/checks/metrics/booleanexpressioncomplexity.html | reference | 1 |
| https://checkstyle.org/checks/metrics/cyclomaticcomplexity.html | reference | 1 |
| https://checkstyle.org/checks/misc/todocomment.html | reference | 2 |
| https://checkstyle.org/checks/naming/localvariablename.html | reference | 1 |
| https://checkstyle.org/checks/naming/methodname.html | reference | 1 |
| https://checkstyle.org/checks/naming/typename.html | reference | 1 |
| https://checkstyle.org/checks/sizes/methodlength.html | reference | 1 |
| https://checkstyle.org/checks/sizes/parameternumber.html | reference | 1 |
| https://developer.android.com/reference/android/webkit/WebView | reference | 2 |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Disposition | reference | 2 |
| https://docs.junit.org/current/api/org.junit.jupiter.api/org/junit/jupiter/api/Assertions.html | reference | 1 |
| https://docs.junit.org/current/writing-tests/nested-tests.html | reference | 1 |
| https://docs.junit.org/current/writing-tests/test-classes-and-methods.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html | reference | 3 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/Externalizable.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/InputStream.html | reference | 3 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/ObjectOutputStream.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/io/Serializable.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Cloneable.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Comparable.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/IllegalMonitorStateException.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Integer.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Iterable.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runnable.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Runtime.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ScopedValue.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/StringBuilder.html | reference | 3 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/System.html | reference | 3 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Thread.html | reference | 4 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ThreadGroup.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Throwable.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/reflect/AccessibleObject.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/Duration.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/LocalDate.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/time/format/DateTimeFormatter.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HexFormat.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/IdentityHashMap.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Iterator.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/List.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Map.html | reference | 3 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Set.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/ScheduledThreadPoolExecutor.html | reference | 3 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/locks/Lock.html | reference | 3 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/regex/Pattern.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/stream/package-summary.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/zip/ZipOutputStream.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/api/java.sql/java/sql/ResultSet.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/21/docs/specs/serialization/class.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/io/File.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/io/ObjectInputStream.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Character.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Class.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Enum.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Integer.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Math.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Object.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Runtime.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/String.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/StringBuffer.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/System.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Thread.html | reference | 3 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ThreadGroup.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ThreadLocal.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/ref/Reference.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/reflect/AccessibleObject.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/reflect/Proxy.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/math/BigDecimal.html | reference | 3 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/MulticastSocket.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/URL.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/URLDecoder.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/net/URLEncoder.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/nio/file/Files.html | reference | 5 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/nio/file/attribute/PosixFilePermissions.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/security/AccessController.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/security/cert/X509Certificate.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/text/SimpleDateFormat.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Arrays.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Collections.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/ConcurrentModificationException.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Date.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/List.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Locale.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Map.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Objects.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Observable.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Optional.html | reference | 5 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Random.html | reference | 2 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Stack.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/StringTokenizer.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Vector.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/CompletableFuture.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/ExecutorService.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/Executors.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/concurrent/atomic/AtomicInteger.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Stream.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/zip/Inflater.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/javax/net/ssl/SSLSession.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.base/javax/security/auth/Subject.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/docs/api/java.net.http/java/net/http/HttpClient.html | reference | 1 |
| https://docs.oracle.com/en/java/javase/25/security/java-api-xml-processing-jaxp-security-guide.html | reference | 1 |
| https://docs.oracle.com/javase/8/docs/technotes/guides/language/catch-multiple.html | reference | 1 |
| https://docs.oracle.com/javase/8/docs/technotes/guides/language/varargs.html | reference | 1 |
| https://docs.oracle.com/javase/specs/jls/se21/html/jls-12.html | reference | 1 |
| https://docs.oracle.com/javase/specs/jls/se21/html/jls-14.html | reference | 18 |
| https://docs.oracle.com/javase/specs/jls/se21/html/jls-15.html | reference | 10 |
| https://docs.oracle.com/javase/specs/jls/se21/html/jls-3.html | reference | 4 |
| https://docs.oracle.com/javase/specs/jls/se21/html/jls-8.html | reference | 2 |
| https://docs.oracle.com/javase/specs/jls/se25/html/jls-15.html | reference | 2 |
| https://docs.oracle.com/javase/specs/jls/se25/html/jls-3.html | reference | 1 |
| https://docs.oracle.com/javase/specs/jls/se25/html/jls-8.html | reference | 1 |
| https://docs.oracle.com/javase/tutorial/essential/concurrency/guardmeth.html | reference | 1 |
| https://docs.oracle.com/javase/tutorial/essential/concurrency/interrupt.html | reference | 1 |
| https://docs.oracle.com/javase/tutorial/essential/exceptions/chained.html | reference | 1 |
| https://docs.oracle.com/javase/tutorial/essential/exceptions/creating.html | reference | 1 |
| https://docs.oracle.com/javase/tutorial/essential/exceptions/tryResourceClose.html | reference | 18 |
| https://docs.oracle.com/javase/tutorial/jdbc/basics/prepared.html | reference | 1 |
| https://docs.oracle.com/javase/tutorial/jndi/ldap/auth_mechs.html | reference | 1 |
| https://docs.spring.io/spring-boot/api/java/org/springframework/boot/autoconfigure/SpringBootApplication.html | reference | 1 |
| https://docs.spring.io/spring-data/commons/reference/repositories/query-methods-details.html | reference | 1 |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/beans/factory/annotation/Autowired.html | reference | 1 |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/cache/annotation/CachePut.html | reference | 1 |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/context/annotation/Bean.html | reference | 1 |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/context/event/EventListener.html | reference | 1 |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/scheduling/annotation/Async.html | reference | 1 |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/scheduling/annotation/Scheduled.html | reference | 1 |
| https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/web/bind/annotation/InitBinder.html | reference | 1 |
| https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/value-annotations.html | reference | 1 |
| https://docs.spring.io/spring-framework/reference/core/beans/java/configuration-annotation.html | reference | 1 |
| https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-methods/requestparam.html | reference | 1 |
| https://docs.spring.io/spring-security/reference/servlet/authentication/session-management.html | reference | 1 |
| https://docs.spring.io/spring-security/site/docs/current/api/org/springframework/security/config/annotation/web/configuration/EnableWebSecurity.html | reference | 1 |
| https://jakarta.ee/specifications/bean-validation/3.0/jakarta-bean-validation-spec-3.0.html | reference | 1 |
| https://jakarta.ee/specifications/persistence/3.2/jakarta-persistence-spec-3.2.html | reference | 2 |
| https://jakarta.ee/specifications/servlet/6.0/apidocs/jakarta.servlet/jakarta/servlet/http/HttpServlet.html | reference | 1 |
| https://openjdk.org/jeps/306 | reference | 1 |
| https://openjdk.org/jeps/320 | reference | 6 |
| https://openjdk.org/jeps/367 | reference | 1 |
| https://openjdk.org/jeps/372 | reference | 2 |
| https://openjdk.org/jeps/378 | reference | 1 |
| https://openjdk.org/jeps/390 | reference | 1 |
| https://openjdk.org/jeps/394 | reference | 1 |
| https://openjdk.org/jeps/395 | reference | 1 |
| https://openjdk.org/jeps/400 | reference | 1 |
| https://openjdk.org/jeps/403 | reference | 1 |
| https://openjdk.org/jeps/407 | reference | 1 |
| https://openjdk.org/jeps/411 | reference | 1 |
| https://openjdk.org/jeps/421 | reference | 1 |
| https://openjdk.org/jeps/431 | reference | 1 |
| https://openjdk.org/jeps/441 | reference | 1 |
| https://openjdk.org/jeps/456 | reference | 1 |
| https://openjdk.org/jeps/471 | reference | 1 |
| https://openjdk.org/jeps/486 | reference | 1 |
| https://openjdk.org/jeps/491 | reference | 1 |
| https://openjdk.org/jeps/500 | reference | 1 |
| https://openjdk.org/jeps/504 | reference | 1 |
| https://openjdk.org/jeps/506 | reference | 1 |
| https://openjdk.org/jeps/512 | reference | 1 |
| https://openjdk.org/jeps/513 | reference | 1 |
| https://owasp.org/www-community/Fail_securely | reference | 3 |
| https://owasp.org/www-community/attacks/Log_Injection | reference | 3 |
| https://pmd.github.io/pmd/pmd_rules_java_bestpractices.html | reference | 3 |
| https://pmd.github.io/pmd/pmd_rules_java_codestyle.html | reference | 1 |
| https://pmd.github.io/pmd/pmd_rules_java_design.html | reference | 2 |
| https://tomcat.apache.org/tomcat-10.1-doc/config/http.html | reference | 1 |
| https://www.oracle.com/java/technologies/javase/seccodeguide.html | reference | 20 |
| https://www.slf4j.org/faq.html | reference | 1 |

### spring (40 URLs, 328 rule citations)

| URL | Kind | Rules |
|---|---|---|
| https://docs.spring.io/spring-boot/reference/actuator/endpoints.html | reference | 4 |
| https://docs.spring.io/spring-boot/reference/data/sql.html | reference | 4 |
| https://docs.spring.io/spring-boot/reference/features/external-config.html | reference | 1 |
| https://docs.spring.io/spring-boot/reference/features/spring-application.html | reference | 1 |
| https://docs.spring.io/spring-boot/reference/io/rest-client.html | reference | 1 |
| https://docs.spring.io/spring-boot/reference/using/spring-beans-and-dependency-injection.html | reference | 1 |
| https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/autowired.html | reference | 2 |
| https://docs.spring.io/spring-framework/reference/core/beans/java/basic-concepts.html | reference | 1 |
| https://docs.spring.io/spring-framework/reference/core/null-safety.html | reference | 1 |
| https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html | reference | 3 |
| https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/rolling-back.html | reference | 2 |
| https://docs.spring.io/spring-framework/reference/integration/cache/annotations.html | reference | 2 |
| https://docs.spring.io/spring-framework/reference/integration/rest-clients.html | reference | 1 |
| https://docs.spring.io/spring-framework/reference/integration/scheduling.html | reference | 4 |
| https://docs.spring.io/spring-framework/reference/web/webmvc-cors.html | reference | 3 |
| https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-requestmapping.html | reference | 2 |
| https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html | reference | 3 |
| https://docs.spring.io/spring-security/reference/features/exploits/csrf.html | reference | 1 |
| https://docs.spring.io/spring-security/reference/servlet/authorization/authorize-http-requests.html | reference | 3 |
| https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html | reference | 1 |
| https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html | reference | 1 |
| https://docs.spring.io/spring-security/reference/servlet/exploits/headers.html | reference | 1 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.1-Release-Notes | release-notes | 1 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.3-Configuration-Changelog | release-notes | 41 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.4-Configuration-Changelog | release-notes | 36 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.5-Configuration-Changelog | release-notes | 16 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.6-Configuration-Changelog | release-notes | 23 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.6-Release-Notes | release-notes | 1 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-2.7-Configuration-Changelog | release-notes | 8 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Configuration-Changelog | release-notes | 23 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide | migration | 12 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.1-Configuration-Changelog | release-notes | 3 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.2-Configuration-Changelog | release-notes | 9 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.3-Configuration-Changelog | release-notes | 2 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.4-Configuration-Changelog | release-notes | 30 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.4-Release-Notes | reference | 1 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.5-Configuration-Changelog | release-notes | 17 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Configuration-Changelog | release-notes | 38 |
| https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-4.0-Migration-Guide | migration | 23 |
| https://spring.io/blog/2022/02/21/spring-security-without-the-websecurityconfigureradapter | release-notes | 1 |

### javascript (235 URLs, 284 rule citations)

| URL | Kind | Rules |
|---|---|---|
| https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/Document/domain | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/Document/execCommand | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/Document/write | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/Element/innerHTML | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/Element/insertAdjacentHTML | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/Event/initEvent | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/EventTarget/addEventListener | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/dataset | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/keyCode | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/MutationEvent | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/Performance/timing | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage | reference | 2 |
| https://developer.mozilla.org/en-US/docs/Web/API/Window/structuredClone | reference | 2 |
| https://developer.mozilla.org/en-US/docs/Web/API/Window/unload_event | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/open | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/Accessibility/Guides/Keyboard-navigable_JavaScript_widgets | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/a | reference | 4 |
| https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe | reference | 2 |
| https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/img | reference | 3 |
| https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/th | reference | 3 |
| https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/video | reference | 2 |
| https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/accesskey | reference | 2 |
| https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/autofocus | reference | 2 |
| https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/tabindex | reference | 2 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Equality_comparisons_and_sameness | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions/arguments/callee | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions/get | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/at | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/flat | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/flatMap | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/forEach | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/indexOf | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/length | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/map | reference | 2 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/reduce | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/sort | reference | 2 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/toSorted | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/Date | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/getYear | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/now | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Date/toUTCString | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error/Error | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/random | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/trunc | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/NaN | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/EPSILON | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/isNaN | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/__defineGetter__ | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/groupBy | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/hasOwn | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/proto | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/RegExp/escape | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/RegExp/n | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/substr | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/trim | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/escape | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/eval | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Lexical_grammar | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Addition_assignment | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Bitwise_AND | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Comma_operator | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Increment | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Inequality | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Logical_AND | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Nullish_coalescing | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Optional_chaining | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Property_accessors | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/delete | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/in | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/this | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/for | reference | 3 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/for...in | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/return | reference | 3 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/var | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/while | reference | 1 |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/with | reference | 1 |
| https://docs.cypress.io/api/commands/pause | reference | 1 |
| https://eslint.org/docs/latest/rules/array-callback-return | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/arrow-body-style | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/camelcase | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/class-methods-use-this | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/complexity | lint-rule-xref | 2 |
| https://eslint.org/docs/latest/rules/curly | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/default-case | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/default-case-last | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/default-param-last | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/dot-notation | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/eqeqeq | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/for-direction | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/func-names | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/getter-return | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/guard-for-in | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/logical-assignment-operators | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/max-depth | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/max-lines-per-function | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/new-cap | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-alert | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-array-constructor | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-async-promise-executor | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-await-in-loop | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-bitwise | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-case-declarations | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-class-assign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-compare-neg-zero | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-cond-assign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-console | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-const-assign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-constant-binary-expression | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-constant-condition | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-constructor-return | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-control-regex | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-debugger | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-delete-var | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-dupe-args | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-dupe-class-members | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-dupe-else-if | lint-rule-xref | 3 |
| https://eslint.org/docs/latest/rules/no-dupe-keys | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-duplicate-case | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-duplicate-imports | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-else-return | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-empty | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-empty-character-class | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-empty-function | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-empty-pattern | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-empty-static-block | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-eq-null | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-ex-assign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-extend-native | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-extra-bind | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-extra-boolean-cast | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-fallthrough | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-func-assign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-global-assign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-implicit-coercion | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-implied-eval | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-import-assign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-iterator | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-labels | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-lone-blocks | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-lonely-if | lint-rule-xref | 2 |
| https://eslint.org/docs/latest/rules/no-loop-func | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-loss-of-precision | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-multi-assign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-multi-str | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-negated-condition | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-nested-ternary | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-new | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-new-func | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-new-native-nonconstructor | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-new-wrappers | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-nonoctal-decimal-escape | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-obj-calls | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-object-constructor | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-octal | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-octal-escape | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-param-reassign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-plusplus | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-promise-executor-return | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-prototype-builtins | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-regex-spaces | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-return-assign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-script-url | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-self-assign | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-self-compare | lint-rule-xref | 2 |
| https://eslint.org/docs/latest/rules/no-sequences | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-setter-return | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-shadow-restricted-names | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-sparse-arrays | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-template-curly-in-string | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-throw-literal | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-unassigned-vars | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-undef-init | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-underscore-dangle | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-unneeded-ternary | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-unreachable | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-unreachable-loop | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-unsafe-finally | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-unsafe-negation | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-unsafe-optional-chaining | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-unused-expressions | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-unused-private-class-members | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-unused-vars | lint-rule-xref | 2 |
| https://eslint.org/docs/latest/rules/no-useless-call | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-useless-catch | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-useless-computed-key | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-useless-concat | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-useless-constructor | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-useless-escape | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-useless-rename | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-useless-return | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-void | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/no-warning-comments | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/object-shorthand | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/operator-assignment | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-arrow-callback | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-destructuring | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-exponentiation-operator | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-named-capture-group | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-numeric-literals | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-object-spread | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-promise-reject-errors | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-regex-literals | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-rest-params | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-spread | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/prefer-template | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/preserve-caught-error | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/radix | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/require-atomic-updates | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/require-await | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/require-unicode-regexp | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/require-yield | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/symbol-description | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/use-isnan | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/valid-typeof | lint-rule-xref | 1 |
| https://eslint.org/docs/latest/rules/yoda | lint-rule-xref | 1 |
| https://expressjs.com/en/resources/middleware/cors.html | reference | 1 |
| https://expressjs.com/en/resources/middleware/session.html | reference | 1 |
| https://jestjs.io/docs/api | reference | 1 |
| https://jestjs.io/docs/expect | reference | 2 |
| https://legacy.reactjs.org/blog/2015/12/16/ismounted-antipattern.html | reference | 1 |
| https://nodejs.org/api/child_process.html | reference | 2 |
| https://nodejs.org/api/deprecations.html | reference | 17 |
| https://owasp.org/www-community/Double_Encoding | reference | 3 |
| https://owasp.org/www-community/vulnerabilities/Information_exposure_through_query_strings_in_url | reference | 2 |
| https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/06-Test_HTTP_Methods | reference | 1 |
| https://playwright.dev/docs/actionability | reference | 1 |
| https://react.dev/learn/conditional-rendering | reference | 1 |
| https://react.dev/learn/writing-markup-with-jsx | reference | 1 |
| https://react.dev/reference/react/useState | reference | 1 |
| https://tug.org/texlive/doc/texlive-en/texlive-en.html | reference | 2 |
| https://www.rfc-editor.org/rfc/rfc9700.html | reference | 2 |

### typescript (80 URLs, 103 rule citations)

| URL | Kind | Rules |
|---|---|---|
| https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/ | release-notes | 4 |
| https://typescript-eslint.io/rules/array-type/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/ban-ts-comment/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/ban-tslint-comment/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/consistent-generic-constructors/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/consistent-indexed-object-style/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/consistent-type-assertions/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/consistent-type-definitions/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/default-param-last/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/explicit-function-return-type/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/max-params/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/method-signature-style/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-array-delete/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-confusing-non-null-assertion/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-duplicate-enum-values/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-duplicate-type-constituents/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-dynamic-delete/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-empty-object-type/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-extra-non-null-assertion/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-extraneous-class/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-floating-promises/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-import-type-side-effects/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-inferrable-types/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-invalid-void-type/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-misused-new/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-mixed-enums/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-non-null-asserted-nullish-coalescing/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-non-null-asserted-optional-chain/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-redundant-type-constituents/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-require-imports/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-this-alias/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-unnecessary-boolean-literal-compare/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-unnecessary-parameter-property-assignment/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-unnecessary-template-expression/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-unnecessary-type-constraint/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-unsafe-declaration-merging/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-unsafe-function-type/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/no-unsafe-type-assertion/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/only-throw-error/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-as-const/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-enum-initializers/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-find/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-for-of/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-function-type/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-includes/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-literal-enum-member/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-nullish-coalescing/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-reduce-type-parameter/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-regexp-exec/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/prefer-string-starts-ends-with/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/triple-slash-reference/ | lint-rule-xref | 1 |
| https://typescript-eslint.io/rules/use-unknown-in-catch-callback-variable/ | lint-rule-xref | 1 |
| https://www.typescriptlang.org/docs/handbook/2/classes.html | reference | 1 |
| https://www.typescriptlang.org/docs/handbook/2/everyday-types.html | reference | 1 |
| https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html | reference | 3 |
| https://www.typescriptlang.org/docs/handbook/enums.html | reference | 2 |
| https://www.typescriptlang.org/docs/handbook/namespaces-and-modules.html | reference | 1 |
| https://www.typescriptlang.org/docs/handbook/namespaces.html | reference | 1 |
| https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-9.html | release-notes | 1 |
| https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-4.html | release-notes | 1 |
| https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-9.html | release-notes | 1 |
| https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-0.html | release-notes | 9 |
| https://www.typescriptlang.org/docs/handbook/release-notes/typescript-5-2.html | release-notes | 1 |
| https://www.typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html | release-notes | 10 |
| https://www.typescriptlang.org/tsconfig/ | reference | 1 |
| https://www.typescriptlang.org/tsconfig/allowUnreachableCode.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/allowUnusedLabels.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/exactOptionalPropertyTypes.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/forceConsistentCasingInFileNames.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/noFallthroughCasesInSwitch.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/noImplicitAny.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/noImplicitOverride.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/noImplicitReturns.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/noImplicitThis.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/noUncheckedIndexedAccess.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/noUncheckedSideEffectImports.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/strictFunctionTypes.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/strictNullChecks.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/strictPropertyInitialization.html | reference | 1 |
| https://www.typescriptlang.org/tsconfig/useUnknownInCatchVariables.html | reference | 1 |

### vue (97 URLs, 113 rule citations)

| URL | Kind | Rules |
|---|---|---|
| https://blog.vuejs.org/posts/vue-3-5 | release-notes | 1 |
| https://eslint.vuejs.org/rules/html-button-has-type.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/html-quotes.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/mustache-interpolation-spacing.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-arrow-functions-in-watch.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-boolean-default.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-child-content.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-deprecated-dollar-scopedslots-api.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-deprecated-functional-template.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-deprecated-html-element-is.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-deprecated-model-definition.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-deprecated-props-default-this.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-deprecated-v-is.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-deprecated-vue-config-keycodes.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-dupe-v-else-if.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-duplicate-attr-inheritance.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-duplicate-attributes.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-empty-component-block.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-export-in-script-setup.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-expose-after-await.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-import-compiler-macros.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-lifecycle-after-await.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-lone-template.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-multiple-objects-in-class.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-multiple-template-root.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-negated-v-if-condition.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-parsing-error.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-required-prop-with-default.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-root-v-if.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-setup-props-reactivity-loss.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-side-effects-in-computed-properties.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-static-inline-styles.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-template-key.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-template-target-blank.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-textarea-mustache.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-this-in-before-route-enter.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-use-v-else-with-v-for.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-useless-mustaches.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-useless-template-attributes.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-useless-v-bind.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-v-for-template-key-on-child.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-v-text.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/no-watch-after-await.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/prefer-import-from-vue.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/prefer-prop-type-boolean-first.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/require-component-is.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/require-prop-type-constructor.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/require-prop-types.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/require-toggle-inside-transition.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/return-in-computed-property.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/this-in-template.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/v-for-delimiter-style.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-attribute-name.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-next-tick.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-v-cloak.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-v-else-if.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-v-else.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-v-for.html | lint-rule-xref | 2 |
| https://eslint.vuejs.org/rules/valid-v-html.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-v-if.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-v-model.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-v-once.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-v-pre.html | lint-rule-xref | 1 |
| https://eslint.vuejs.org/rules/valid-v-show.html | lint-rule-xref | 2 |
| https://eslint.vuejs.org/rules/valid-v-text.html | lint-rule-xref | 1 |
| https://v2.vuejs.org/eol/ | migration | 1 |
| https://v2.vuejs.org/v2/guide/components-slots.html | reference | 1 |
| https://v2.vuejs.org/v2/guide/migration-vue-2-7.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/ | migration | 2 |
| https://v3-migration.vuejs.org/breaking-changes/children.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/custom-directives.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/data-option.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/emits-option.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/events-api.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/filters.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/functional-components.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/global-api-treeshaking.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/global-api.html | migration | 3 |
| https://v3-migration.vuejs.org/breaking-changes/inline-template-attribute.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/keycode-modifiers.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/listeners-removed.html | migration | 2 |
| https://v3-migration.vuejs.org/breaking-changes/props-data.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/render-function-api.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/transition.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/v-model.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/v-on-native-modifier-removed.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/vnode-lifecycle-events.html | migration | 1 |
| https://v3-migration.vuejs.org/breaking-changes/watch.html | migration | 1 |
| https://vuejs.org/guide/best-practices/security.html | reference | 3 |
| https://vuejs.org/guide/components/props.html | reference | 1 |
| https://vuejs.org/guide/essentials/computed.html | reference | 1 |
| https://vuejs.org/guide/essentials/reactivity-fundamentals.html | reference | 2 |
| https://vuejs.org/guide/essentials/watchers.html | reference | 2 |
| https://vuejs.org/guide/extras/reactivity-transform.html | reference | 1 |
| https://vuejs.org/style-guide/rules-essential.html | reference | 4 |
| https://vuejs.org/style-guide/rules-strongly-recommended.html | reference | 3 |
| https://vuejs.org/style-guide/rules-use-with-caution.html | reference | 2 |

### nuxt (34 URLs, 99 rule citations)

| URL | Kind | Rules |
|---|---|---|
| https://nuxt.com/blog/nuxt2-eol | release-notes | 1 |
| https://nuxt.com/blog/v4-5-security | reference | 3 |
| https://nuxt.com/docs/4.x/api/composables/use-cookie | reference | 1 |
| https://nuxt.com/docs/4.x/api/composables/use-fetch | reference | 1 |
| https://nuxt.com/docs/4.x/api/composables/use-head | reference | 2 |
| https://nuxt.com/docs/4.x/api/utils/dollarfetch | reference | 3 |
| https://nuxt.com/docs/4.x/api/utils/navigate-to | reference | 1 |
| https://nuxt.com/docs/4.x/directory-structure/app/components | reference | 1 |
| https://nuxt.com/docs/4.x/directory-structure/app/plugins | reference | 1 |
| https://nuxt.com/docs/4.x/getting-started/data-fetching | reference | 3 |
| https://nuxt.com/docs/4.x/getting-started/state-management | reference | 1 |
| https://nuxt.com/docs/4.x/getting-started/upgrade | migration | 38 |
| https://nuxt.com/docs/4.x/guide/best-practices/hydration | reference | 2 |
| https://nuxt.com/docs/4.x/guide/concepts/nuxt-lifecycle | reference | 1 |
| https://nuxt.com/docs/4.x/guide/going-further/runtime-config | reference | 1 |
| https://nuxt.com/docs/4.x/migration/component-options | migration | 8 |
| https://nuxt.com/docs/4.x/migration/configuration | migration | 2 |
| https://nuxt.com/docs/4.x/migration/meta | migration | 2 |
| https://nuxt.com/docs/4.x/migration/pages-and-layouts | migration | 2 |
| https://nuxt.com/docs/4.x/migration/plugins-and-middleware | migration | 1 |
| https://nuxt.com/docs/5.x/getting-started/upgrade | migration | 8 |
| https://nuxt.com/docs/5.x/guide/going-further/server-imports | reference | 1 |
| https://nuxt.com/docs/api/advanced/import-meta | reference | 1 |
| https://nuxt.com/docs/api/components/nuxt-link | reference | 1 |
| https://nuxt.com/docs/api/utils/navigate-to | reference | 1 |
| https://nuxt.com/docs/getting-started/data-fetching | reference | 1 |
| https://nuxt.com/docs/getting-started/state-management | reference | 1 |
| https://nuxt.com/docs/getting-started/upgrade | migration | 2 |
| https://nuxt.com/docs/guide/going-further/runtime-config | reference | 1 |
| https://nuxt.com/docs/migration/component-options | migration | 1 |
| https://nuxt.com/docs/migration/configuration | migration | 1 |
| https://nuxt.com/docs/migration/meta | migration | 1 |
| https://nuxt.com/docs/migration/plugins-and-middleware | migration | 2 |
| https://nuxt.com/docs/migration/runtime-config | migration | 2 |

<!-- END GENERATED CITATIONS -->

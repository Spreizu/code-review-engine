# Source currency audit (2026-10-10)

The question for each rule: does the cited source describe current versions? Where it does not, the
rule is re-cited to the current official page, version-gated, or removed. Every new citation was
fetched and quote-checked with `rulegen.py verify` (0 problems), and `sources.yaml` was regenerated.
`rulecheck`: 3325 rules, 0 failures.

Verdicts: **valid** = re-cited, behaviour unchanged · **gated** = only meaningful on old versions,
`applies_to` narrowed · **obsolete** = removed · **kept** = source already current.

## 1. SEI CERT Oracle Coding Standard for Java (written for Java SE 6/7): `rules/packs/java/cert.gen.yaml`

All 8 rules were checked against JDK 17, 21 and 25. **None is obsolete.** CERT stays in `xref` only.
The primary source is now the current JDK 25 API, JLS/JVMS SE 25 or a JEP. Rule IDs did not change,
so existing labels still apply.

| Rule | Still an issue on 17/21/25? | API status / changes | Modern alternative | New primary source | Verdict |
|---|---|---|---|---|---|
| JAVA-CERT-FIO02-FILE-RESULT-IGNORED | Yes. `File.delete/mkdir/renameTo…` still report failure only through a boolean. | `java.io.File` is not deprecated. | `java.nio.file.Files.delete/createDirectory/move`, which throw `IOException` with the reason (named in the message). | JDK 25 `java.io.File#delete` ("true if and only if … successfully deleted"); xref `Files#delete` | valid |
| JAVA-CERT-LCK02-SYNC-GETCLASS | Yes. `getClass()` returns the runtime (sub)class, so subclasses take a different lock. | Unchanged. | `synchronized (A.class)` or a private static final lock. | JDK 25 `Object#getClass` ("The Class object that represents the runtime class of this object") | valid |
| JAVA-CERT-LCK01-SYNC-SHARED-LITERAL | Yes, and the JDK now enforces it: since JDK 16 (JEP 390), boxed primitives are *value-based*, `javac -Xlint:synchronization` warns, and `-XX:DiagnoseSyncOnValueBasedClasses` diagnoses at run time. String literals are interned (JLS 3.10.5). | Wrapper constructors are deprecated for removal. | A private final `Object` lock or `ReentrantLock`. | JEP 390; xref `ValueBased.html` and JLS SE 25 §3.10.5 | valid |
| JAVA-CERT-THI02-NOTIFY | Yes. `notify()` still picks an arbitrary waiter. | Unchanged. | `notifyAll()`, or `java.util.concurrent` `Condition`, `CountDownLatch`, `BlockingQueue`. | JDK 25 `Object#notify` ("The choice is arbitrary …") | valid (stays ai-confirm) |
| JAVA-CERT-OBJ09-CLASS-NAME-COMPARE | Yes. A runtime class is identified by its name *and* its defining loader. | Unchanged. The module system does not change class identity. | `==` on Class objects, `instanceof`, `Class#isAssignableFrom`. | JVMS SE 25 §5.3 ("is the defining loader of C") | valid |
| JAVA-CERT-ERR09-SYSTEM-EXIT | Partly. CERT frames this as *untrusted code* terminating the JVM and fixes it with `SecurityManager.checkExit`. That remedy is gone: SecurityManager was deprecated for removal by JEP 411 (JDK 17) and permanently disabled by JEP 486 (JDK 24). The design problem remains: library or server code calling `System.exit/halt` kills every thread and app in the JVM. | `Runtime.exit` is not deprecated. JDK 17+ can log callers through the `java.lang.Runtime` System.Logger. | Throw or return a status and let `main()` decide. | JDK 25 `Runtime#exit` ("Initiates the shutdown sequence…"); xref JEP 486 | valid, re-framed (the message never relied on SM). Stays ai-confirm with the "outside main" filter. |
| JAVA-CERT-NUM09-FLOAT-LOOP-COUNTER | Yes. IEEE 754 binary floating point is unchanged (strictfp semantics became the default in JDK 17, JEP 306, which does not make 0.1 exact). | n/a | An integer counter, deriving the float value from it. | JLS SE 25 ch. 4 (floating-point values, "inexact") | valid |
| JAVA-CERT-FIO03-TEMP-FILE-NOT-REMOVED | Yes. `File.createTempFile` still "provides only part of a temporary-file facility". | Not deprecated. `Files.createTempFile` (NIO) creates the file with owner-only POSIX permissions. | `Files.createTempFile` with `Files.deleteIfExists` in `finally`, or `StandardOpenOption.DELETE_ON_CLOSE`. | JDK 25 `File#createTempFile` ("To arrange for a file … to be deleted automatically, use the deleteOnExit() method"); xref `DELETE_ON_CLOSE` | valid (stays ai-confirm) |

Pack `doc_version` is now "JDK 25 API / JLS SE 25 (SEI CERT Java as xref)". There are no other CERT
citations in any pack: the `CERT_*` hits in the Python, Terraform and JS packs are TLS-certificate
identifiers, not SEI CERT.

## 2. Other Java rules on APIs that changed after Java 8

| Rule | Finding | Action |
|---|---|---|
| JAVA-MAINT-RUN-FINALIZERS-ON-EXIT | `Runtime/System.runFinalizersOnExit` was **removed in JDK 11** (JDK-8198249). The rule cited the JDK 21 `Runtime` page, where the method does not exist; the quote was just "Runtime". On 11+ the call does not compile, so the rule is redundant there. | **gated** `java: '<11'`. Re-cited to the JDK 11 Migration Guide removed-API list; xref JDK 8 javadoc ("inherently unsafe"). |
| KT-MAINT-RUN-FINALIZERS-ON-EXIT | Same API, called from Kotlin. The Kotlin units have no JDK-target dimension to gate on. | Re-cited to the JDK 11 Migration Guide. Kept: the call only resolves against JDK ≤10. |
| JAVA-MAINT-FINALIZE-CALLED, JAVA-MAINT-FINALIZE-WRONG-SIGNATURE | Finalization has been deprecated for removal since JDK 18 (JEP 421). Both rules are still valid and point to Cleaner / try-with-resources. | xref JEP 421 added. JAVA-MIG-FIN-001 (JEP 421, `>=18`) already covers overriding. |
| JAVA-MIG-THR-001 (Thread.stop) | `Thread.stop()` always throws UOE since JDK 20. | kept (already `>=20`, cites JDK 25 Thread). |
| JAVA-MIG-SM-001 / JAVA-MIG-REM-SM-PERM-002 / JAVA-MIG-DEP-ACCESSCONTROLLER-001 | SecurityManager: JEP 411 (17), JEP 486 (24). | kept (gated `>=17` / `>=24`, cite the JEPs and JDK 25). |
| JAVA-MIG-DEP-RUNFINALIZATION-001, JAVA-MIG-APPLET-001 | JEP 421 (18) and JEP 504 (26). | kept. |
| JAVA-QUAL-RES-* (13 classes + 4 `Files.new*` + JDBC) | Cited the Java Tutorials, a JDK 8 snapshot. try-with-resources is unchanged. | Re-cited to **JLS SE 25 §14.20.3**. |
| JAVA-QUAL-CONC-INTERRUPTED-001 | Cited the Java Tutorials. | Re-cited to the JDK 25 `Thread#interrupt` javadoc. |
| JAVA-QUAL-COR-THREAD-SLEEP-LOOP-001 | Cited the Java Tutorials. | Re-cited to the JDK 25 `Object#wait` javadoc. |
| JAVA-SEC-LDAP-ANON-001 | Cited the JNDI tutorial (JDK 8 era). | Re-cited to the JDK 25 `javax.naming.Context#SECURITY_AUTHENTICATION` ("none", "simple", "strong"); tutorial kept as xref. |
| JAVA-MAINT-LOG-AND-RETHROW | Cited the Java Tutorials. | Re-cited to the JDK 25 `Throwable` javadoc (chained exception facility). |
| JAVA-MAINT-GENERIC-EXCEPTION-THROWN | Java Tutorials "Creating Exception Classes". No current JDK document states this guidance, and the concept has not changed. | kept (Sonar xref). The only remaining Java Tutorials citation. |
| JAVA-MAINT-VARARGS-EXPLICIT-ARRAY | Cited the JDK 8 technotes. | Re-cited to JLS SE 25 §15.12.4.2. |
| JAVA-MAINT-IDENTICAL-CATCH-BLOCKS | Cited the JDK 8 technotes. | Re-cited to JLS SE 25 §14.20 (multi-catch). |
| JAVA-MAINT-SERVLET-MUTABLE-FIELD | Cited Jakarta Servlet 6.0; 6.1 (Jakarta EE 11) is current. | Re-cited to Servlet 6.1 HttpServlet. |
| JAVA-SEC-HTTP-TRACE-ENABLED | Cited Tomcat 10.1; 11.0 is current. `allowTrace` still defaults to false. | Re-cited to Tomcat 11.0. |

The 195 rules citing the JDK 21 API were left as they are. JDK 21 is an LTS release under support, and
the APIs they cite are unchanged in JDK 25. The newer rules cite JDK 25.

## 3. Old-version sources in other packs

I scanned every `source.url` and `doc_version` across all 3325 rules for pinned old versions (507
hits). Results:

- **Django 5.2 → 6.1** (8 rules: PY-SEC-DJANGO-*, PY-SEC-COOKIE-INSECURE). The current docs are 6.1.
  All quotes are unchanged on the 6.1 pages. Re-cited. (5.2 is still a supported LTS, and `applies_to`
  is unchanged.)
- **Vue 2 sources** (VUE-MIG-EOL-001, VUE-MIG-COMPOSITION-API-PKG-001, VUE-MIG-SLOT-001). Each rule is
  about Vue 2 itself (EOL, 2.7 migration, 2.6 slot deprecation) and is gated `<3.0` or `>=2.6` with a
  Vue 3 override, so the v2 docs are the correct primary source. VUE-MIG-SLOT-001 gains xrefs to the
  Vue 3 migration guide (slots unification) and the current slots guide.
  - Open question: the Vue 3 override would also flag a native `slot="…"` attribute on children of
    Web Components. Queued for the sampled FP review.
- **React `isMounted`** (JS-MAINT-REACT-ISMOUNTED) cites the legacy.reactjs.org 2015 post. This is the
  only official statement; react.dev does not document `isMounted`, which exists only on legacy
  `createReactClass` components. Kept as a legacy-API rule.
- **GitHub Actions `ACTIONS_ALLOW_UNSECURE_COMMANDS`** cites the 2020 changelog. The current docs no
  longer mention the variable, but the runner still honours it, so the changelog remains the
  authoritative source. Kept.
- **Maven 3.8.1** (MAVEN-SEC-HTTP-REPOSITORY). The release that blocked HTTP repositories by default
  is still the reference for this behaviour. Kept.
- **OWASP.** All cheat-sheet citations use cheatsheetseries.owasp.org (current). The 28 owasp.org
  `www-community` pages are unversioned community articles. No Top 10 2013/2017 or ASVS 4.0 URLs
  were found. The `owasp`/`asvs` tags use Top 10 2021/2025 and ASVS 5.0 ids. Kept.
- **"Introduced in X" sources** (≈480 rules: Spring Boot 2.x/3.x property migrations, PHP 5.x–8.x
  feature/removal docs, Angular 14–20 removals, Kotlin 1.x features, TypeScript 3.9–5.5, Gradle
  7/8, AWS provider 5.0, VueUse 10–13, Python 3.10–3.12 removals, ytt, Nuxt 2→3). The cited
  version is the release where the feature or removal happened, and every one of these rules is
  gated with a matching `applies_to` (`>=X` for modernization/removal, `<X` for upgrade nags), so the
  versioned page is the right source. Kept.
- RFC 8259 (JSON, 2017) is the current JSON standard. Requests 2.x, cors 2.8 and PyJWT 2.x are the
  current major versions. Kept.

## Totals

- CERT rules audited: 8. Valid and re-cited: 8 (1 re-framed: ERR09). Gated: 0. Obsolete: 0.
- Other rules re-cited to current sources: 36 (Java/Kotlin 28, Django 8). Gated to old versions: 1
  (JAVA-MAINT-RUN-FINALIZERS-ON-EXIT `<11`). xrefs added: 4 rules (2 × JEP 421, VUE-MIG-SLOT-001,
  KT runFinalizersOnExit JDK 8 xref).
- Removed as obsolete: 0. No rule targets an API that is gone on its gated versions.

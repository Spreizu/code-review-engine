"""Spring Boot / Spring Framework / Spring Security rules.

Property rules are generated from the official Spring Boot wiki configuration changelogs
(tables "Deprecated in X" / "Removed in X"), parsed from the wiki git repository
(https://github.com/spring-projects/spring-boot.wiki.git) by tools/rulegen/sbwiki.py.
"""
import json, os, re
from rulegen import rule
from specs._java import cls

RULES = R = []
add = R.append
WIKI = "https://github.com/spring-projects/spring-boot/wiki/"
PROPS_FILES = ["**/application*.properties", "**/application*.yml", "**/application*.yaml", "**/bootstrap*.properties", "**/bootstrap*.yml", "**/bootstrap*.yaml"]
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sb-config-changelog.json")


def slug(k):
    return re.sub(r"-+", "-", re.sub(r"[^A-Z0-9]+", "-", k.upper())).strip("-")


def vtag(v):
    p = v.split(".")
    return p[0] + p[1]


def mm(v):
    return ".".join(v.split(".")[:2])


def prop_rule(id, title, key, repl, ver, url, quote, msg, sev, overrides=None, prefix=False, kind="deprecation"):
    cfg = {"key_prefix": key, "op": "exists"} if prefix else {"key": key, "op": "exists"}
    bad = (key + "example" if prefix else key) + "=value"
    good = (repl + "example" if prefix and repl else repl or "# removed: " + key.replace(".", "_")) + ("=value" if repl else "")
    add(rule(id, title, language="properties", framework="spring-boot", kind=kind, category="configuration", severity=sev,
             applies={"spring-boot": f">={mm(ver)}"}, overrides=overrides, engine="config", files=PROPS_FILES, config=cfg,
             message=msg, url=url, doc=f"Spring Boot {mm(ver)} Configuration Changelog", doc_version=f"Spring Boot {mm(ver)}",
             quote=quote, bad=bad, good=good, tags=["spring-boot-property"]))


d = json.load(open(DATA))
removed_at = {}
for ver, rows in d["Removed"].items():
    for r in rows:
        removed_at.setdefault(r[0].strip("`"), ver.replace(".RELEASE", ""))
seen = set()
for ver, rows in d["Deprecated"].items():
    v = ver.replace(".RELEASE", "")
    page = WIKI + f"Spring-Boot-{mm(v)}-Configuration-Changelog"
    for k, repl, why in rows:
        k, repl = k.strip("`").strip(), repl.strip("`").strip()
        if not repl or "*" in k or "[" in k or k in seen or not re.match(r"^[a-z0-9.\-]+$", repl):
            continue
        seen.add(k)
        ov = None
        rv = removed_at.get(k)
        if rv and rv != v:
            ov = [{"when": {"spring-boot": f">={mm(rv)}"}, "severity": "critical",
                   "message": f"'{k}' was removed in Spring Boot {mm(rv)} and is silently ignored; use '{repl}'."}]
        prop_rule(f"SB-PROP-{vtag(v)}-{slug(k)}", f"{k} is deprecated (use {repl})", k, repl, v, page, f"{k} {repl}",
                  f"'{k}' is deprecated since Spring Boot {mm(v)}; use '{repl}'." + (f" It is removed in {mm(rv)}." if rv and rv != v else ""),
                  "minor", ov)
# Removed-with-replacement keys that were never in a "Deprecated" table: group large prefix moves.
groups = {}
for ver, rows in d["Removed"].items():
    v = ver.replace(".RELEASE", "")
    for r in rows:
        k, repl = r[0].strip("`"), r[1].strip("`")
        if k in seen or not re.match(r"^[a-z][a-z0-9\-]*(\.[a-z0-9\-]+)+$", repl) or "*" in k or "[" in k:
            continue
        pre = ".".join(k.split(".")[:3]) + "."
        groups.setdefault((v, pre), []).append((k, repl))
for (v, pre), items in sorted(groups.items()):
    page = WIKI + f"Spring-Boot-{mm(v)}-Configuration-Changelog"
    if len(items) >= 4 and not any(r.startswith(pre) for _, r in items):
        k, repl = items[0]
        prop_rule(f"SB-PROP-{vtag(v)}-REMOVED-{slug(pre)}", f"{pre}* properties were removed/relocated in Spring Boot {mm(v)}", pre, None, v, page,
                  f"{k} {repl}", f"{len(items)} '{pre}*' properties were removed or relocated in Spring Boot {mm(v)} (e.g. '{k}' -> '{repl}'); old keys are silently ignored. Run spring-boot-properties-migrator to get the exact mapping.",
                  "critical", prefix=True, kind="removal")
        R[-1]["examples"] = {"bad": f"{k}=value", "good": f"{repl}=value"}
    else:
        for k, repl in items:
            seen.add(k)
            prop_rule(f"SB-PROP-{vtag(v)}-{slug(k)}", f"{k} was removed (use {repl})", k, repl, v, page, f"{k} {repl}",
                      f"'{k}' was removed in Spring Boot {mm(v)} and is silently ignored; use '{repl}'.", "critical", kind="removal")

# ------------------------------------------------------------------ code rules (Java)
FW = "https://docs.spring.io/spring-framework/reference/"
SEC = "https://docs.spring.io/spring-security/reference/"
BOOT = "https://docs.spring.io/spring-boot/reference/"


def S(id, title, *, applies=None, fw="spring-boot", lang="java", **kw):
    kw.setdefault("doc_version", "Spring Framework 7.0 reference (current)")
    return add(rule(id, title, language=lang, framework=fw, applies=applies or {"spring-boot": ">=2.0"}, **kw))


def ann(name):
    return f'[(marker_annotation name: (identifier) @an) (annotation name: (identifier) @an)] (#eq? @an "{name}")'


def self_call(anns):
    """Patterns: annotated method + same-class unqualified call at nesting depth 1..3, either order."""
    pats = []
    for d in (1, 2, 3):
        call = "(method_invocation !object name: (identifier) @call)"
        for _ in range(d):
            call = f"(_ {call})"
        caller = f"(method_declaration body: (block {call}))"
        target = "(method_declaration (modifiers (_ name: (identifier) @an)) name: (identifier) @target)"
        for a, b in ((target, caller), (caller, target)):
            pats.append(f'((class_declaration body: (class_body {a} {b})) @match (#match? @an "^({anns})$") (#eq? @target @call))')
    return "\n".join(pats)


S("SB-TX-CHECKED-001", "@Transactional does not roll back on checked exceptions by default", kind="anti-pattern", category="transactions", severity="major",
  query='((method_declaration (modifiers (_ name: (identifier) @an)) (throws) @thr) @match (#eq? @an "Transactional") (#not-match? @match "rollbackFor|rollbackOn") (#match? @thr "Exception"))',
  mode="ai-confirm", ai="Can this method throw a checked exception after it has written data that must be rolled back? (RuntimeException subclasses are fine.)",
  bad="class S {\n  @Transactional\n  public void transfer() throws IOException { debit(); credit(); }\n}\n",
  good="class S {\n  @Transactional(rollbackFor = IOException.class)\n  public void transfer() throws IOException { debit(); credit(); }\n}\n",
  url=FW + "data-access/transaction/declarative/rolling-back.html", doc="Rolling Back a Declarative Transaction",
  quote="marks a transaction for rollback only in the case of runtime, unchecked exceptions",
  message="The method is @Transactional and declares checked exceptions; by default the transaction commits when a checked exception is thrown. Add rollbackFor if it must roll back.")
S("SB-TX-INTERFACE-001", "Annotate concrete classes, not interfaces, with @Transactional", kind="best-practice", category="transactions", severity="minor",
  query='((interface_declaration body: (interface_body (method_declaration (modifiers (_ name: (identifier) @an))))) @match (#eq? @an "Transactional"))',
  bad="interface AccountService {\n  @Transactional\n  void transfer();\n}\n", good="class AccountServiceImpl implements AccountService {\n  @Transactional\n  public void transfer() {}\n}\n",
  url=FW + "data-access/transaction/declarative/annotations.html", doc="Using @Transactional",
  quote="The Spring team recommends that you annotate methods of concrete classes with the @Transactional annotation, rather than relying on annotated methods in interfaces",
  message="@Transactional on interface methods only works with interface-based proxies; annotate the implementing class/methods.")
S("SB-TX-SWALLOW-001", "Exception swallowed inside @Transactional method prevents rollback", kind="anti-pattern", category="transactions", severity="major",
  query='((method_declaration (modifiers (_ name: (identifier) @an)) body: (block (try_statement (catch_clause body: (block) @cb)))) @match (#eq? @an "Transactional") (#not-match? @cb "throw|setRollbackOnly"))',
  mode="ai-confirm", ai="Does the catch block swallow an exception that should roll back the transaction (no rethrow, no setRollbackOnly)?",
  bad="class S {\n  @Transactional\n  public void save() {\n    try { repo.save(a); repo.save(b); } catch (RuntimeException e) { log.warn(\"fail\", e); }\n  }\n}\n",
  good="class S {\n  @Transactional\n  public void save() {\n    try { repo.save(a); repo.save(b); } catch (RuntimeException e) { log.warn(\"fail\", e); throw e; }\n  }\n}\n",
  url=FW + "data-access/transaction/declarative/rolling-back.html", doc="Rolling Back a Declarative Transaction",
  quote="The recommended way to indicate to the Spring Framework’s transaction infrastructure that a transaction’s work is to be rolled back is to throw an Exception from code that is currently executing in the context of a transaction.",
  message="The exception is caught and not rethrown inside a @Transactional method, so the transaction infrastructure never sees it and commits.")
S("SB-ASYNC-SELF-001", "@Async method called from the same class is not asynchronous", kind="anti-pattern", category="async", severity="major",
  query=self_call('Async'),
  bad="class Mailer {\n  @Async\n  public void send(Mail m) {}\n  public void sendAll(List<Mail> ms) {\n    send(ms.get(0));\n  }\n}\n",
  good="class Mailer {\n  private final AsyncMailer async;\n  public void sendAll(List<Mail> ms) {\n    async.send(ms.get(0));\n  }\n}\n",
  url=FW + "integration/scheduling.html", doc="Task Execution and Scheduling - @Async",
  quote="The default advice mode for processing @Async annotations is proxy which allows for interception of calls through the proxy only. Local calls within the same class cannot get intercepted that way.",
  message="A local call to an @Async method bypasses the proxy and runs synchronously on the caller thread.")
S("SB-ASYNC-PRIVATE-001", "@Async on a private method has no effect", kind="anti-pattern", category="async", severity="major",
  query='((method_declaration (modifiers (_ name: (identifier) @an)) @mods) @match (#eq? @an "Async") (#match? @mods "(^|\\\\s)private(\\\\s|$)"))',
  bad="class J {\n  @Async\n  private void run() {}\n}\n", good="class J {\n  @Async\n  public void run() {}\n}\n",
  url=FW + "integration/scheduling.html", doc="Task Execution and Scheduling - @Async",
  quote="Local calls within the same class cannot get intercepted that way.",
  message="Proxies cannot intercept private methods, so @Async on a private method is ignored.")
S("SB-ASYNC-RETURN-001", "@Async method returns a plain value (result is lost)", kind="anti-pattern", category="async", severity="major",
  query='((method_declaration (modifiers (_ name: (identifier) @an)) type: [(type_identifier) (generic_type (type_identifier) @gt) (integral_type) (boolean_type) (floating_point_type)] @rt) @match (#eq? @an "Async") (#not-match? @rt "^(Future|CompletableFuture|ListenableFuture|CompletionStage|Mono|Flux)"))',
  bad="class J {\n  @Async\n  public String compute() { return \"x\"; }\n}\n", good="class J {\n  @Async\n  public CompletableFuture<String> compute() { return CompletableFuture.completedFuture(\"x\"); }\n}\n",
  url=FW + "integration/scheduling.html", doc="Task Execution and Scheduling - @Async",
  quote="@Async methods may not only declare a regular java.util.concurrent.Future return type but also java.util.concurrent.CompletableFuture",
  message="An @Async method must return void or a Future/CompletableFuture; a plain return value is not delivered to the caller (it gets null).")
S("SB-ASYNC-VOID-EXC-001", "@Async void method: exceptions are not propagated", kind="best-practice", category="async", severity="minor",
  query='((method_declaration (modifiers (_ name: (identifier) @an)) type: (void_type)) @match (#eq? @an "Async"))',
  mode="ai-confirm", filters=["file.lacks_text:AsyncUncaughtExceptionHandler"], ai="Can this @Async void method throw, and is there no AsyncUncaughtExceptionHandler configured anywhere in the project?",
  bad="class J {\n  @Async\n  public void sync() { remote.call(); }\n}\n", good="class J implements AsyncConfigurer {\n  public AsyncUncaughtExceptionHandler getAsyncUncaughtExceptionHandler() { return handler; }\n}\n",
  url=FW + "integration/scheduling.html", doc="Task Execution and Scheduling - Exception Management with @Async",
  quote="With a void return type, however, the exception is uncaught and cannot be transmitted.",
  message="Exceptions thrown by @Async void methods are not visible to callers; configure an AsyncUncaughtExceptionHandler or return CompletableFuture.")
S("SB-CACHE-SELF-001", "@Cacheable/@CacheEvict method called from the same class bypasses the cache", kind="anti-pattern", category="caching", severity="major",
  query=self_call('Cacheable|CachePut|CacheEvict'),
  bad="class Prices {\n  @Cacheable(\"p\")\n  public Price find(String id) { return load(id); }\n  public Price cheapest(String id) {\n    return find(id);\n  }\n}\n",
  good="class Prices {\n  private final PriceLookup lookup;\n  public Price cheapest(String id) {\n    return lookup.find(id);\n  }\n}\n",
  url=FW + "integration/cache/annotations.html", doc="Declarative Annotation-based Caching",
  quote="In proxy mode (the default), only external method calls coming in through the proxy are intercepted.",
  message="Self-invocation of a caching-annotated method is not intercepted, so the cache is not used.")
S("SB-DI-AUTOWIRED-CTOR-001", "@Autowired on the only constructor is unnecessary", kind="best-practice", category="dependency-injection", severity="info",
  query='((class_declaration body: (class_body (constructor_declaration (modifiers (marker_annotation name: (identifier) @an))) @ctor)) @match (#eq? @an "Autowired"))',
  bad="class S {\n  private final Repo repo;\n  @Autowired\n  S(Repo repo) { this.repo = repo; }\n}\n", good="class S {\n  private final Repo repo;\n  S(Repo repo) { this.repo = repo; }\n}\n",
  url=FW + "core/beans/annotation-config/autowired.html", doc="Using @Autowired",
  quote="An @Autowired annotation on such a constructor is not necessary if the target bean defines only one constructor.",
  message="Spring autowires a single constructor without @Autowired; the annotation is noise.", mode="ai-confirm", ai="Does the class declare exactly one constructor?")
S("SB-DI-LITE-BEAN-001", "@Bean methods in a non-@Configuration class run in lite mode (no inter-bean proxying)", kind="anti-pattern", category="dependency-injection", severity="minor",
  query='((class_declaration (modifiers (_ name: (identifier) @cls)) body: (class_body (method_declaration (modifiers (_ name: (identifier) @an))))) @match (#match? @cls "^(Component|Service|Repository|Controller|RestController)$") (#eq? @an "Bean"))',
  mode="ai-confirm", ai="Do @Bean methods in this class call each other (expecting the singleton bean), which lite mode does not intercept?",
  bad="@Component\nclass Cfg {\n  @Bean DataSource ds() { return new HikariDataSource(); }\n}\n", good="@Configuration\nclass Cfg {\n  @Bean DataSource ds() { return new HikariDataSource(); }\n}\n",
  url=FW + "core/beans/java/basic-concepts.html", doc="Basic Concepts: @Bean and @Configuration",
  quote="they are referred to as being processed in a \"lite\" mode",
  message="@Bean methods outside @Configuration classes are plain factory methods; calling one from another creates a new instance instead of returning the bean.")
S("SB-DI-CIRCULAR-001", "spring.main.allow-circular-references=true hides design problems", kind="anti-pattern", category="dependency-injection", severity="minor",
  applies={"spring-boot": ">=2.6"}, lang="properties", engine="config", files=PROPS_FILES, config={"key": "spring.main.allow-circular-references", "op": "equals", "value": "true", "case_insensitive": True},
  bad="spring.main.allow-circular-references=true", good="spring.main.lazy-initialization=false",
  url=WIKI + "Spring-Boot-2.6-Release-Notes", doc="Spring Boot 2.6 Release Notes - Circular References Prohibited by Default", doc_version="Spring Boot 2.6",
  quote="Circular references between beans are now prohibited by default.",
  message="Circular bean references are prohibited by default since 2.6; re-enabling them papers over a dependency cycle - break the cycle instead.")
S("SB-DI-OVERRIDE-001", "spring.main.allow-bean-definition-overriding=true", kind="anti-pattern", category="dependency-injection", severity="info",
  applies={"spring-boot": ">=2.1"}, lang="properties", engine="config", files=PROPS_FILES, config={"key": "spring.main.allow-bean-definition-overriding", "op": "equals", "value": "true", "case_insensitive": True},
  bad="spring.main.allow-bean-definition-overriding=true", good="spring.main.banner-mode=off",
  url=WIKI + "Spring-Boot-2.1-Release-Notes", doc="Spring Boot 2.1 Release Notes - Bean Overriding", doc_version="Spring Boot 2.1",
  quote="Bean overriding has been disabled by default to prevent a bean being accidentally overridden.",
  message="Bean overriding is disabled by default to avoid accidental overrides; prefer @ConditionalOnMissingBean / @Primary over globally enabling it.")
S("SB-PROFILES-001", "spring.profiles in a config document must become spring.config.activate.on-profile", kind="migration", category="configuration", severity="major",
  applies={"spring-boot": ">=2.4"}, lang="properties", engine="config", files=PROPS_FILES, config={"key": "spring.profiles", "op": "exists"},
  overrides=[{"when": {"spring-boot": ">=3.0"}, "severity": "critical"}],
  bad="spring.profiles=prod", good="spring.config.activate.on-profile=prod",
  url=WIKI + "Spring-Boot-Config-Data-Migration-Guide", doc="Config Data Migration Guide - Profile Specific Documents", doc_version="Spring Boot 2.4+",
  quote="If you use the spring.profiles property, for example in multi-document YAML files, you should migrate to spring.config.activate.on-profile .",
  message="Profile-specific documents must use spring.config.activate.on-profile (Spring Boot 2.4 config data); the legacy spring.profiles key is no longer supported in 3.x.")

SECV = "Spring Security 7.0 reference (current)"
S("SB-SEC-CSRF-001", "CSRF protection disabled", kind="security", category="security", severity="major", applies={"spring-security": ">=5.0"}, doc_version=SECV,
  query='((method_invocation name: (identifier) @m) @match (#eq? @m "csrf") (#match? @match "disable"))',
  mode="ai-confirm", ai="Is this filter chain reachable by browsers with cookie/session authentication? (Pure stateless token APIs may legitimately disable CSRF.)",
  bad=cls('http.csrf(csrf -> csrf.disable());'), good=cls('http.csrf(Customizer.withDefaults());'),
  url=SEC + "features/exploits/csrf.html", doc="Cross Site Request Forgery (CSRF)",
  quote="Our recommendation is to use CSRF protection for any request that could be processed by a browser by normal users.",
  message="CSRF protection is disabled. Keep it for any endpoint a browser can call with ambient credentials (cookies/sessions).")
S("SB-SEC-NOOP-ENCODER-001", "NoOpPasswordEncoder stores plain-text passwords", kind="security", category="security", severity="critical", applies={"spring-security": ">=5.0"}, doc_version=SECV,
  query='((method_invocation object: (identifier) @c) @match (#eq? @c "NoOpPasswordEncoder"))',
  bad=cls('PasswordEncoder enc = NoOpPasswordEncoder.getInstance();'), good=cls('PasswordEncoder enc = PasswordEncoderFactories.createDelegatingPasswordEncoder();'),
  url=SEC + "features/authentication/password-storage.html", doc="Password Storage",
  quote="Prior to Spring Security 5.0, the default PasswordEncoder was NoOpPasswordEncoder , which required plain-text passwords.",
  message="NoOpPasswordEncoder keeps passwords in plain text; use the DelegatingPasswordEncoder (bcrypt/argon2/scrypt/pbkdf2).")
S("SB-SEC-DEFAULT-ENCODER-001", "User.withDefaultPasswordEncoder() is not intended for production", kind="security", category="security", severity="major", applies={"spring-security": ">=5.0"}, doc_version=SECV,
  query='((method_invocation object: (identifier) @c name: (identifier) @m) @match (#eq? @c "User") (#eq? @m "withDefaultPasswordEncoder"))',
  bad=cls('UserDetails u = User.withDefaultPasswordEncoder().username("u").password("p").roles("USER").build();'),
  good=cls('UserDetails u = User.withUsername("u").password(encoder.encode(raw)).roles("USER").build();'),
  url=SEC + "features/authentication/password-storage.html", doc="Password Storage - withDefaultPasswordEncoder",
  quote="There are convenience mechanisms to make this easier, but this is still not intended for production.",
  message="withDefaultPasswordEncoder() hashes at runtime from a plain-text password in source; it is for demos only.")
S("SB-SEC-LEGACY-ENCODER-001", "Deprecated legacy PasswordEncoder implementations", kind="security", category="security", severity="major", applies={"spring-security": ">=5.0"}, doc_version=SECV,
  query='((object_creation_expression type: (type_identifier) @t) @match (#match? @t "^(MessageDigestPasswordEncoder|StandardPasswordEncoder|Md4PasswordEncoder|LdapShaPasswordEncoder)$"))',
  bad=cls('PasswordEncoder enc = new MessageDigestPasswordEncoder("MD5");'), good=cls('PasswordEncoder enc = new BCryptPasswordEncoder();'),
  url=SEC + "features/authentication/password-storage.html", doc="Password Storage - Other PasswordEncoders",
  quote="They are all deprecated to indicate that they are no longer considered secure.",
  message="This PasswordEncoder exists only for backward compatibility and is not considered secure; migrate via DelegatingPasswordEncoder to bcrypt/argon2.")
S("SB-SEC-GLOBAL-METHOD-001", "@EnableGlobalMethodSecurity is superseded by @EnableMethodSecurity", kind="deprecation", category="security", severity="minor", applies={"spring-security": ">=5.6"}, doc_version=SECV,
  query='([(marker_annotation name: (identifier) @an) (annotation name: (identifier) @an)] @match (#eq? @an "EnableGlobalMethodSecurity"))',
  overrides=[{"when": {"spring-security": ">=7.0"}, "severity": "critical", "message": "@EnableGlobalMethodSecurity is not available in Spring Security 7; use @EnableMethodSecurity."}],
  bad="@EnableGlobalMethodSecurity(prePostEnabled = true)\nclass SecCfg {}\n", good="@EnableMethodSecurity\nclass SecCfg {}\n",
  url=SEC + "servlet/authorization/method-security.html", doc="Method Security",
  quote="This annotation and XML element supercede @EnableGlobalMethodSecurity and <sec:global-method-security/> , respectively.",
  message="Use @EnableMethodSecurity (AuthorizationManager based, pre/post enabled by default) instead of @EnableGlobalMethodSecurity.")
S("SB-SEC-ANTMATCHERS-001", "antMatchers/mvcMatchers/regexMatchers were removed in Spring Security 6", kind="removal", category="security", severity="critical", applies={"spring-security": ">=6.0"}, doc_version=SECV,
  query='((method_invocation name: (identifier) @m) @match (#match? @m "^(antMatchers|mvcMatchers|regexMatchers|antMatcher|mvcMatcher|regexMatcher)$"))',
  bad=cls('http.authorizeHttpRequests(a -> a.antMatchers("/admin/**").hasRole("ADMIN"));'), good=cls('http.authorizeHttpRequests(a -> a.requestMatchers("/admin/**").hasRole("ADMIN"));'),
  url=SEC + "servlet/authorization/authorize-http-requests.html", doc="Authorize HttpServletRequests",
  quote="requestMatchers",
  message="antMatchers/mvcMatchers/regexMatchers do not exist in Spring Security 6+; use requestMatchers(...).")
S("SB-SEC-PERMITALL-001", "anyRequest().permitAll() leaves every endpoint public", kind="security", category="security", severity="major", applies={"spring-security": ">=5.0"}, doc_version=SECV,
  query='((method_invocation object: (method_invocation name: (identifier) @a) name: (identifier) @p) @match (#eq? @a "anyRequest") (#eq? @p "permitAll"))',
  mode="ai-confirm", ai="Is this an application where unauthenticated access to every remaining endpoint is intended (e.g. a public site behind another gateway)?",
  bad=cls('http.authorizeHttpRequests(a -> a.anyRequest().permitAll());'), good=cls('http.authorizeHttpRequests(a -> a.requestMatchers("/public/**").permitAll().anyRequest().authenticated());'),
  url=SEC + "servlet/authorization/authorize-http-requests.html", doc="Authorize HttpServletRequests", quote="anyRequest",
  message="The catch-all rule permits every request; prefer deny-by-default (anyRequest().authenticated() or denyAll()).")
S("SB-SEC-FRAMEOPTIONS-001", "X-Frame-Options disabled", kind="security", category="security", severity="minor", applies={"spring-security": ">=5.0"}, doc_version=SECV,
  query='((method_invocation name: (identifier) @m) @match (#eq? @m "frameOptions") (#match? @match "disable"))',
  mode="ai-confirm", ai="Is disabling frame options needed (e.g. only for the H2 console in dev) and is clickjacking otherwise mitigated (CSP frame-ancestors)?",
  bad=cls('http.headers(h -> h.frameOptions(f -> f.disable()));'), good=cls('http.headers(h -> h.frameOptions(f -> f.sameOrigin()));'),
  url=SEC + "servlet/exploits/headers.html", doc="Security HTTP Response Headers", quote="X-Frame-Options",
  message="Disabling X-Frame-Options exposes pages to clickjacking; use sameOrigin() or a CSP frame-ancestors directive.")
S("SB-WEB-CORS-ALL-001", "@CrossOrigin without origins allows all origins", kind="security", category="security", severity="minor", applies={"spring-boot": ">=2.0"},
  query='((marker_annotation name: (identifier) @an) @match (#eq? @an "CrossOrigin"))',
  mode="ai-confirm", ai="Should this endpoint really be callable from any origin?",
  bad="@RestController\n@CrossOrigin\nclass Api {}\n", good="@RestController\n@CrossOrigin(origins = \"https://app.example.com\")\nclass Api {}\n",
  url=FW + "web/webmvc-cors.html", doc="CORS - @CrossOrigin", quote="By default, @CrossOrigin allows: All origins.",
  message="A bare @CrossOrigin allows all origins, headers and mapped methods; list the allowed origins explicitly.")
S("SB-WEB-CORS-CRED-001", "CORS with allowCredentials(true) widens trust", kind="security", category="security", severity="minor", applies={"spring-boot": ">=2.0"},
  query='((method_invocation name: (identifier) @m arguments: (argument_list . (true) .)) @match (#eq? @m "allowCredentials"))',
  mode="ai-confirm", ai="Are the allowed origins a short explicit list of trusted domains (no wildcard / pattern that matches arbitrary sites)?",
  bad=cls('registry.addMapping("/**").allowedOriginPatterns("*").allowCredentials(true);'), good=cls('registry.addMapping("/api/**").allowedOrigins("https://app.example.com");'),
  url=FW + "web/webmvc-cors.html", doc="CORS - Credentialed Requests",
  quote="Be aware that this option establishes a high level of trust with the configured domains and also increases the surface of attack of the web application",
  message="Credentialed CORS establishes a high level of trust in the configured origins; keep the origin list explicit and minimal.")
S("SB-WEB-REQMAPPING-METHOD-001", "Method-level @RequestMapping without an HTTP method", kind="best-practice", category="web", severity="info", applies={"spring-boot": ">=2.0"},
  query='((method_declaration (modifiers [(marker_annotation name: (identifier) @an) (annotation name: (identifier) @an)] @a)) @match (#eq? @an "RequestMapping") (#not-match? @a "method"))',
  bad="class C {\n  @RequestMapping(\"/users\")\n  List<User> list() { return users; }\n}\n", good="class C {\n  @GetMapping(\"/users\")\n  List<User> list() { return users; }\n}\n",
  url=FW + "web/webmvc/mvc-controller/ann-requestmapping.html", doc="Mapping Requests",
  quote="most controller methods should be mapped to a specific HTTP method versus using @RequestMapping",
  message="A method-level @RequestMapping without method= matches every HTTP method; use @GetMapping/@PostMapping/... .")
S("SB-WEB-RESTTEMPLATE-NEW-001", "RestTemplate/WebClient created with new instead of the auto-configured builder", kind="best-practice", category="web", severity="minor", applies={"spring-boot": ">=2.0"},
  query='((object_creation_expression type: (type_identifier) @t) @match (#eq? @t "RestTemplate"))',
  mode="ai-confirm", ai="Is this RestTemplate created without the auto-configured RestTemplateBuilder (losing message converters, metrics and tracing)?",
  bad=cls('RestTemplate rt = new RestTemplate();'), good=cls('RestClient rc = restClientBuilder.baseUrl(url).build();'),
  url=BOOT + "io/rest-client.html", doc="Calling REST Services", doc_version="Spring Boot reference (current 4.x)",
  quote="RestClient.Builder", message="Use the auto-configured RestClient.Builder / RestTemplateBuilder so converters, observability and SSL bundles apply.")
S("SB-NULL-SPRING-LANG-001", "org.springframework.lang null-safety annotations are superseded by JSpecify (Spring Framework 7)", kind="deprecation", category="null-handling", severity="minor",
  applies={"spring-framework": ">=7.0"},
  query='((import_declaration) @match (#match? @match "org\\\\.springframework\\\\.lang\\\\.(Nullable|NonNull|NonNullApi|NonNullFields)"))',
  bad="import org.springframework.lang.Nullable;\nclass A {}\n", good="import org.jspecify.annotations.Nullable;\nclass A {}\n",
  url=FW + "core/null-safety.html", doc="Null-safety", quote="the Spring Framework codebase is annotated with JSpecify annotations",
  message="Spring Framework 7 uses JSpecify (@NullMarked, @Nullable); migrate from org.springframework.lang.* annotations (Spring Boot 4 actuator no longer honours them).")

MIG3 = WIKI + "Spring-Boot-3.0-Migration-Guide"
MIG4 = WIKI + "Spring-Boot-4.0-Migration-Guide"


def cfg(id, title, key, op, value, bad, good, url, doc, docv, quote, msg, sev="major", kind="security", cat="security", applies=None, mode="deterministic", ai=None, prefix=False, ci=True):
    c = {"key_prefix": key, "op": op} if prefix else {"key": key, "op": op}
    if value is not None:
        c["value"] = value
        if ci:
            c["case_insensitive"] = True
    S(id, title, kind=kind, category=cat, severity=sev, applies=applies or {"spring-boot": ">=2.0"}, lang="properties", engine="config", files=PROPS_FILES,
      config=c, bad=bad, good=good, url=url, doc=doc, doc_version=docv, quote=quote, message=msg, mode=mode, ai=ai)


BV = "Spring Boot reference (current 4.x)"
cfg("SB-CFG-H2-CONSOLE-001", "H2 console enabled", "spring.h2.console.enabled", "equals", "true", "spring.h2.console.enabled=true", "spring.h2.console.enabled=false",
    BOOT + "data/sql.html", "SQL Databases - Using H2's Web Console", BV,
    "The H2 console is only intended for use during development, so you should take care to ensure that spring.h2.console.enabled is not set to true in production.",
    "The H2 web console is enabled; it is a development tool and must not be enabled in production profiles.", mode="ai-confirm",
    ai="Is this a production (non-dev, non-test) configuration file or profile?")
cfg("SB-CFG-H2-REMOTE-001", "H2 console reachable from other hosts", "spring.h2.console.settings.web-allow-others", "equals", "true", "spring.h2.console.settings.web-allow-others=true",
    "spring.h2.console.settings.web-allow-others=false", BOOT + "data/sql.html", "SQL Databases - Using H2's Web Console", BV,
    "The H2 console is only intended for use during development",
    "web-allow-others exposes the H2 console (arbitrary SQL) to remote hosts.", sev="critical")
cfg("SB-CFG-HEALTH-DETAILS-001", "Health endpoint shows details to everyone", "management.endpoint.health.show-details", "equals", "always",
    "management.endpoint.health.show-details=always", "management.endpoint.health.show-details=when-authorized",
    BOOT + "actuator/endpoints.html", "Actuator Endpoints - Health Information", BV,
    "The information exposed by the health endpoint depends on the management.endpoint.health.show-details and management.endpoint.health.show-components properties",
    "show-details=always reveals component details (DB, disk, versions) to unauthenticated callers; use when-authorized.", sev="minor")
cfg("SB-CFG-SHOW-VALUES-001", "Actuator env/configprops values shown unsanitized", "management.endpoint.env.show-values", "equals", "always",
    "management.endpoint.env.show-values=always", "management.endpoint.env.show-values=when-authorized",
    BOOT + "actuator/endpoints.html", "Actuator Endpoints - Sanitize Sensitive Values", BV,
    "Information returned by the /env , /configprops and /quartz endpoints can be sensitive, so by default values are always fully sanitized",
    "show-values=always prints secrets (passwords, tokens) from the environment in clear text.", sev="major", applies={"spring-boot": ">=3.0"})
cfg("SB-CFG-CONFIGPROPS-VALUES-001", "Actuator configprops values shown unsanitized", "management.endpoint.configprops.show-values", "equals", "always",
    "management.endpoint.configprops.show-values=always", "management.endpoint.configprops.show-values=when-authorized",
    BOOT + "actuator/endpoints.html", "Actuator Endpoints - Sanitize Sensitive Values", BV,
    "The show-values property can be configured for sanitizable endpoints to one of the following values",
    "show-values=always prints bound configuration values including secrets.", sev="major", applies={"spring-boot": ">=3.0"})
cfg("SB-CFG-DDL-AUTO-001", "Hibernate ddl-auto modifies the schema at startup", "spring.jpa.hibernate.ddl-auto", "in", ["create", "create-drop", "update"],
    "spring.jpa.hibernate.ddl-auto=update", "spring.jpa.hibernate.ddl-auto=validate", BOOT + "data/sql.html", "SQL Databases - Creating and Dropping JPA Databases", BV,
    "spring.jpa.hibernate.ddl-auto=create-drop",
    "Schema generation (create/create-drop/update) at startup can drop or alter production tables; use a migration tool (Flyway/Liquibase) and ddl-auto=validate/none outside dev.",
    sev="major", kind="anti-pattern", cat="data", mode="ai-confirm", ai="Is this configuration used for a persistent (non-throwaway, non-test) database?")
cfg("SB-CFG-SESSION-STORE-001", "spring.session.store-type is no longer supported", "spring.session.store-type", "exists", None, "spring.session.store-type=redis", "spring.session.redis.namespace=app",
    MIG3, "Spring Boot 3.0 Migration Guide - Spring Session Store Type", "Spring Boot 3.0",
    "Explicitly configuring the store type for Spring session via spring.session.store-type is no longer supported.",
    "spring.session.store-type was removed in 3.0; the store is chosen by classpath order (define a SessionRepository bean to override).", sev="major", kind="removal", cat="configuration", applies={"spring-boot": ">=3.0"})
cfg("SB-CFG-NEW-ID-GEN-001", "spring.jpa.hibernate.use-new-id-generator-mappings was removed", "spring.jpa.hibernate.use-new-id-generator-mappings", "exists", None,
    "spring.jpa.hibernate.use-new-id-generator-mappings=false", "spring.jpa.open-in-view=false", MIG3, "Spring Boot 3.0 Migration Guide - Hibernate 6.1", "Spring Boot 3.0",
    "The spring.jpa.hibernate.use-new-id-generator-mappings configuration property has been removed as Hibernate no longer supports switching back to the old ID generator mappings.",
    "Hibernate 6 no longer supports the old ID generator mappings; this property is ignored.", sev="major", kind="removal", cat="configuration", applies={"spring-boot": ">=3.0"})
cfg("SB-CFG-CASSANDRA-001", "spring.data.cassandra.* moved to spring.cassandra.*", "spring.data.cassandra.", "exists", None, "spring.data.cassandra.keyspace-name=app",
    "spring.cassandra.keyspace-name=app", MIG3, "Spring Boot 3.0 Migration Guide - Cassandra Properties", "Spring Boot 3.0",
    "Configuration Properties for Cassandra have moved from spring.data.cassandra.* to spring.cassandra.* .",
    "Cassandra properties moved to spring.cassandra.* in 3.0; old keys are ignored.", sev="critical", kind="removal", cat="configuration", applies={"spring-boot": ">=3.0"}, prefix=True)
for old, new in [("spring.session.redis.", "spring.session.data.redis."), ("spring.session.mongodb.", "spring.session.data.mongodb.")]:
    cfg(f"SB-BOOT4-CFG-{slug(old)}-001", f"{old}* renamed to {new}* in Spring Boot 4", old, "exists", None, old + "namespace=app", new + "namespace=app",
        MIG4, "Spring Boot 4.0 Migration Guide - Spring Session", "Spring Boot 4.0",
        f"Properties that previously began with {old.rstrip('.')} now begin with {new.rstrip('.')}" if "redis" in old else f"properties that previously began with {old.rstrip('.')} now begin with {new.rstrip('.')}",
        f"Spring Session properties moved from {old}* to {new}* in Spring Boot 4.0.", sev="critical", kind="removal", cat="configuration", applies={"spring-boot": ">=4.0"}, prefix=True)
for k in ["additional-hosts", "authentication-database", "database", "host", "password", "port", "protocol", "replica-set-name", "representation.uuid", "ssl.bundle", "ssl.enabled", "uri", "username"]:
    cfg(f"SB-BOOT4-CFG-MONGO-{slug(k)}-001", f"spring.data.mongodb.{k} is now spring.mongodb.{k}", f"spring.data.mongodb.{k}", "exists", None, f"spring.data.mongodb.{k}=value", f"spring.mongodb.{k}=value",
        MIG4, "Spring Boot 4.0 Migration Guide - MongoDB", "Spring Boot 4.0", f"spring.mongodb.{k}",
        f"MongoDB connection properties moved from spring.data.mongodb.* to spring.mongodb.* in Spring Boot 4.0 (spring.data.mongodb.{k} -> spring.mongodb.{k}).",
        sev="critical", kind="removal", cat="configuration", applies={"spring-boot": ">=4.0"})
cfg("SB-BOOT4-CFG-DAO-EXTRANS-001", "spring.dao.exceptiontranslation.enabled is replaced", "spring.dao.exceptiontranslation.enabled", "exists", None, "spring.dao.exceptiontranslation.enabled=false",
    "spring.persistence.exceptiontranslation.enabled=false", MIG4, "Spring Boot 4.0 Migration Guide - Persistence Modules", "Spring Boot 4.0",
    "The spring.dao.exceptiontranslation.enabled property is no longer supported.", "Use spring.persistence.exceptiontranslation.enabled (Spring Boot 4.0).", sev="critical", kind="removal", cat="configuration", applies={"spring-boot": ">=4.0"})
cfg("SB-BOOT4-CFG-KAFKA-RANDOM-001", "spring.kafka.retry.topic.backoff.random was replaced by jitter", "spring.kafka.retry.topic.backoff.random", "exists", None, "spring.kafka.retry.topic.backoff.random=true",
    "spring.kafka.retry.topic.backoff.jitter=100ms", MIG4, "Spring Boot 4.0 Migration Guide - Spring Kafka Retry Features", "Spring Boot 4.0",
    "spring.kafka.retry.topic.backoff.random has been removed in favor of spring.kafka.retry.topic.backoff.jitter", "Use spring.kafka.retry.topic.backoff.jitter (Spring Boot 4.0).",
    sev="critical", kind="removal", cat="configuration", applies={"spring-boot": ">=4.0"})


def imp_rule(id, title, regex, bad, good, url, doc, docv, quote, msg, applies, sev="critical", kind="removal", cat="migration"):
    S(id, title, kind=kind, category=cat, severity=sev, applies=applies, query=f'((import_declaration) @match (#match? @match "{regex}"))',
      bad=bad + "\nclass A {}\n", good=good + "\nclass A {}\n", url=url, doc=doc, doc_version=docv, quote=quote, message=msg)


imp_rule("SB-BOOT3-HTTPTRACE-001", "HttpTraceRepository was renamed to HttpExchangeRepository (httpexchanges endpoint)", "org\\\\.springframework\\\\.boot\\\\.actuate\\\\.trace\\\\.http",
         "import org.springframework.boot.actuate.trace.http.HttpTraceRepository;", "import org.springframework.boot.actuate.web.exchanges.HttpExchangeRepository;",
         MIG3, "Spring Boot 3.0 Migration Guide - 'httptrace' Endpoint Renamed to 'httpexchanges'", "Spring Boot 3.0",
         "For example, HttpTraceRepository is now named HttpExchangeRepository and can be found in the org.springframework.boot.actuate.web.exchanges package.",
         "The httptrace endpoint and its infrastructure were renamed to httpexchanges in 3.0.", {"spring-boot": ">=3.0"})
imp_rule("SB-BOOT4-ENTITYSCAN-001", "@EntityScan moved to org.springframework.boot.persistence.autoconfigure", "org\\\\.springframework\\\\.boot\\\\.autoconfigure\\\\.domain\\\\.EntityScan",
         "import org.springframework.boot.autoconfigure.domain.EntityScan;", "import org.springframework.boot.persistence.autoconfigure.EntityScan;",
         MIG4, "Spring Boot 4.0 Migration Guide - Persistence Modules", "Spring Boot 4.0",
         "Users of @EntityScan should adapt their imports to org.springframework.boot.persistence.autoconfigure.EntityScan .",
         "Update the @EntityScan import for Spring Boot 4.0's spring-boot-persistence module.", {"spring-boot": ">=4.0"})
imp_rule("SB-BOOT4-EPP-001", "EnvironmentPostProcessor moved from org.springframework.boot.env to org.springframework.boot", "org\\\\.springframework\\\\.boot\\\\.env\\\\.EnvironmentPostProcessor",
         "import org.springframework.boot.env.EnvironmentPostProcessor;", "import org.springframework.boot.EnvironmentPostProcessor;",
         MIG4, "Spring Boot 4.0 Migration Guide - BootstrapRegistry and EnvironmentPostProcessor package changes", "Spring Boot 4.0",
         "The EnvironmentPostProcessor interface has also moved from org.springframework.boot.env to org.springframework.boot .",
         "The old EnvironmentPostProcessor type is deprecated in 4.0 and will be removed; update the import and spring.factories entries.", {"spring-boot": ">=4.0"}, sev="major", kind="deprecation")
imp_rule("SB-BOOT4-BOOTSTRAP-001", "BootstrapRegistry moved to org.springframework.boot.bootstrap", "org\\\\.springframework\\\\.boot\\\\.(BootstrapRegistry|BootstrapContext|ConfigurableBootstrapContext|BootstrapRegistryInitializer|DefaultBootstrapContext)",
         "import org.springframework.boot.BootstrapRegistry;", "import org.springframework.boot.bootstrap.BootstrapRegistry;",
         MIG4, "Spring Boot 4.0 Migration Guide - BootstrapRegistry and EnvironmentPostProcessor package changes", "Spring Boot 4.0",
         "The BootstrapRegistry and related classes have moved from org.springframework.boot to org.springframework.boot.bootstrap .",
         "Update BootstrapRegistry-related imports for Spring Boot 4.0.", {"spring-boot": ">=4.0"})
imp_rule("SB-BOOT4-TESTRESTTEMPLATE-001", "TestRestTemplate moved to org.springframework.boot.resttestclient", "org\\\\.springframework\\\\.boot\\\\.test\\\\.web\\\\.client\\\\.TestRestTemplate",
         "import org.springframework.boot.test.web.client.TestRestTemplate;", "import org.springframework.boot.resttestclient.TestRestTemplate;",
         MIG4, "Spring Boot 4.0 Migration Guide - TestRestTemplate Failures", "Spring Boot 4.0",
         "The package holding that class will also need to be updated to org.springframework.boot.resttestclient.TestRestTemplate .",
         "TestRestTemplate lives in spring-boot-resttestclient in 4.0; add @AutoConfigureTestRestTemplate (or move to RestTestClient).", {"spring-boot": ">=4.0"})
imp_rule("SB-BOOT4-PROPERTYMAPPING-001", "@PropertyMapping moved to org.springframework.boot.test.context", "org\\\\.springframework\\\\.boot\\\\.test\\\\.autoconfigure\\\\.properties\\\\.(PropertyMapping|Skip)",
         "import org.springframework.boot.test.autoconfigure.properties.PropertyMapping;", "import org.springframework.boot.test.context.PropertyMapping;",
         MIG4, "Spring Boot 4.0 Migration Guide - @PropertyMapping Annotation", "Spring Boot 4.0",
         "The @PropertyMapping annotation has been relocated from the org.springframework.boot.test.autoconfigure.properties package to org.springframework.boot.test.context .",
         "Update the @PropertyMapping import for Spring Boot 4.0.", {"spring-boot": ">=4.0"})
imp_rule("SB-BOOT4-HTTPMSGCONV-001", "Spring Boot's HttpMessageConverters is deprecated in 4.0", "org\\\\.springframework\\\\.boot\\\\.(autoconfigure\\\\.http|http\\\\.converter\\\\.autoconfigure)\\\\.HttpMessageConverters",
         "import org.springframework.boot.autoconfigure.http.HttpMessageConverters;", "import org.springframework.boot.http.converter.autoconfigure.ServerHttpMessageConvertersCustomizer;",
         MIG4, "Spring Boot 4.0 Migration Guide - HttpMessageConverters Deprecation", "Spring Boot 4.0",
         "This release deprecates Spring Boot's HttpMessageConverters", "Use ClientHttpMessageConvertersCustomizer / ServerHttpMessageConvertersCustomizer beans instead.",
         {"spring-boot": ">=4.0"}, sev="minor", kind="deprecation")
S("SB-BOOT4-PROPMAPPER-001", "PropertyMapper.alwaysApplyingWhenNonNull() was removed in Spring Boot 4", kind="removal", category="migration", severity="critical", applies={"spring-boot": ">=4.0"},
  query='((method_invocation name: (identifier) @m) @match (#eq? @m "alwaysApplyingWhenNonNull"))',
  bad=cls('PropertyMapper map = PropertyMapper.get().alwaysApplyingWhenNonNull();'), good=cls('PropertyMapper map = PropertyMapper.get();'),
  url=MIG4, doc="Spring Boot 4.0 Migration Guide - Property Mapper API Changes", doc_version="Spring Boot 4.0",
  quote="This has removed the need for the alwaysApplyingWhenNonNull() method which has been removed.",
  message="PropertyMapper skips null sources by default in 4.0 and alwaysApplyingWhenNonNull() is gone; use always() when null must be mapped.")
S("SB-BOOT4-MOCKMVC-001", "@SpringBootTest no longer provides MockMvc without @AutoConfigureMockMvc", kind="migration", category="testing", severity="critical", applies={"spring-boot": ">=4.0"},
  query='((class_declaration (modifiers (_ name: (identifier) @an))) @match (#eq? @an "SpringBootTest"))',
  filters=["file.has_text:MockMvc", "file.lacks_text:AutoConfigureMockMvc"],
  bad="@SpringBootTest\nclass ApiTest {\n  @Autowired MockMvc mvc;\n}\n", good="@SpringBootTest\n@AutoConfigureMockMvc\nclass ApiTest {\n  @Autowired MockMvc mvc;\n}\n",
  url=MIG4, doc="Spring Boot 4.0 Migration Guide - Using MockMVC and @SpringBootTest", doc_version="Spring Boot 4.0",
  quote="Using the @SpringBootTest annotation will no longer provide any MockMVC support.",
  message="Add @AutoConfigureMockMvc to @SpringBootTest classes that inject MockMvc (Spring Boot 4.0).")
S("SB-BOOT4-TESTRESTTEMPLATE-002", "@SpringBootTest no longer provides TestRestTemplate/WebClient beans", kind="migration", category="testing", severity="critical", applies={"spring-boot": ">=4.0"},
  query='((class_declaration (modifiers (_ name: (identifier) @an))) @match (#eq? @an "SpringBootTest"))',
  filters=["file.has_text:TestRestTemplate", "file.lacks_text:AutoConfigureTestRestTemplate"],
  bad="@SpringBootTest(webEnvironment = RANDOM_PORT)\nclass ApiTest {\n  @Autowired TestRestTemplate rest;\n}\n", good="@SpringBootTest(webEnvironment = RANDOM_PORT)\n@AutoConfigureTestRestTemplate\nclass ApiTest {\n  @Autowired TestRestTemplate rest;\n}\n",
  url=MIG4, doc="Spring Boot 4.0 Migration Guide - Using WebClient or TestRestTemplate and @SpringBootTest", doc_version="Spring Boot 4.0",
  quote="Using the @SpringBootTest annotation will no longer provide any WebClient or TestRestTemplate beans.",
  message="Add @AutoConfigureTestRestTemplate (and spring-boot-resttestclient) or migrate to RestTestClient (Spring Boot 4.0).")
S("SB-BOOT4-MOCKITO-LISTENER-001", "@Mock/@Captor fields in Spring tests need MockitoExtension in Spring Boot 4", kind="migration", category="testing", severity="major", applies={"spring-boot": ">=4.0"},
  query='((field_declaration (modifiers (marker_annotation name: (identifier) @an))) @match (#match? @an "^(Mock|Captor|Spy|InjectMocks)$"))',
  filters=["file.has_text:SpringBootTest", "file.lacks_text:MockitoExtension"],
  bad="@SpringBootTest\nclass T {\n  @Mock Repo repo;\n}\n", good="@SpringBootTest\n@ExtendWith(MockitoExtension.class)\nclass T {\n  @Mock Repo repo;\n}\n",
  url=MIG4, doc="Spring Boot 4.0 Migration Guide - Mockito Captor and Mock Annotations", doc_version="Spring Boot 4.0",
  quote="If you find your @Mock or @Captor annotated fields aren't working as expected, you should use MockitoExtension from Mockito itself.",
  message="MockitoTestExecutionListener was removed in 4.0; @Mock/@Captor fields are no longer initialised unless MockitoExtension is used.")
S("SB-BOOT3-BATCH-ENABLE-001", "@EnableBatchProcessing disables Spring Boot's batch auto-configuration", kind="migration", category="migration", severity="major", applies={"spring-boot": ">=3.0"},
  query='((marker_annotation name: (identifier) @an) @match (#eq? @an "EnableBatchProcessing"))',
  mode="ai-confirm", ai="Does the application expect Spring Boot's batch auto-configuration (job launching at startup, schema init)?",
  bad="@Configuration\n@EnableBatchProcessing\nclass BatchCfg {}\n", good="@Configuration\nclass BatchCfg {}\n",
  url=MIG3, doc="Spring Boot 3.0 Migration Guide - @EnableBatchProcessing is now discouraged", doc_version="Spring Boot 3.0",
  quote="It is no longer required and should be removed from applications that want to use Boot's auto-configuration.",
  message="Since 3.0 @EnableBatchProcessing tells Boot's batch auto-configuration to back off; remove it unless you configure Batch yourself.")


def dep_rule(id, title, coord, good_artifact, url, doc, docv, quote, msg, applies, sev="major", kind="deprecation", group="org.springframework.boot"):
    g, a = coord.split(":")
    S(id, title, kind=kind, category="build", severity=sev, applies=applies, lang="manifest", engine="manifest",
      manifest={"check": "has_dependency", "value": coord},
      bad=f"<project><dependencies><dependency><groupId>{g}</groupId><artifactId>{a}</artifactId></dependency></dependencies></project>",
      good=f"<project><dependencies><dependency><groupId>{good_artifact.split(':')[0]}</groupId><artifactId>{good_artifact.split(':')[1]}</artifactId></dependency></dependencies></project>",
      url=url, doc=doc, doc_version=docv, quote=quote, message=msg)


for old, new in [("spring-boot-starter-oauth2-authorization-server", "spring-boot-starter-security-oauth2-authorization-server"),
                 ("spring-boot-starter-oauth2-client", "spring-boot-starter-security-oauth2-client"),
                 ("spring-boot-starter-oauth2-resource-server", "spring-boot-starter-security-oauth2-resource-server"),
                 ("spring-boot-starter-web", "spring-boot-starter-webmvc"),
                 ("spring-boot-starter-web-services", "spring-boot-starter-webservices")]:
    dep_rule(f"SB-BOOT4-STARTER-{slug(old.replace('spring-boot-starter-', ''))}-001", f"{old} is deprecated in Spring Boot 4 (use {new})", f"org.springframework.boot:{old}",
             f"org.springframework.boot:{new}", MIG4, "Spring Boot 4.0 Migration Guide - Deprecated Starters", "Spring Boot 4.0", f"{old} {new}",
             f"The {old} starter was renamed to {new} in Spring Boot 4.0; the old name is deprecated and will be removed.", {"spring-boot": ">=4.0"}, sev="minor")
dep_rule("SB-BOOT4-STARTER-AOP-001", "spring-boot-starter-aop was renamed to spring-boot-starter-aspectj", "org.springframework.boot:spring-boot-starter-aop", "org.springframework.boot:spring-boot-starter-aspectj",
         MIG4, "Spring Boot 4.0 Migration Guide - AOP Starter POM", "Spring Boot 4.0", "it has been renamed to spring-boot-starter-aspectj",
         "spring-boot-starter-aop is spring-boot-starter-aspectj in 4.0; check whether you need AspectJ at all.", {"spring-boot": ">=4.0"})
dep_rule("SB-BOOT4-BATCH-JDBC-001", "spring-boot-starter-batch no longer stores metadata in the database in Spring Boot 4", "org.springframework.boot:spring-boot-starter-batch", "org.springframework.boot:spring-boot-starter-batch-jdbc",
         MIG4, "Spring Boot 4.0 Migration Guide - Spring Batch", "Spring Boot 4.0", "To go back to using a database, you need to change to spring-boot-starter-batch-jdbc .",
         "In 4.0 spring-boot-starter-batch runs Spring Batch in-memory; use spring-boot-starter-batch-jdbc to keep job metadata in your database.", {"spring-boot": ">=4.0"}, kind="migration")
dep_rule("SB-BOOT4-TOMCAT-WAR-001", "WAR deployments to Tomcat need spring-boot-starter-tomcat-runtime in Spring Boot 4", "org.springframework.boot:spring-boot-starter-tomcat", "org.springframework.boot:spring-boot-starter-tomcat-runtime",
         MIG4, "Spring Boot 4.0 Migration Guide - Tomcat", "Spring Boot 4.0", "you need to switch the dependency spring-boot-starter-tomcat to spring-boot-starter-tomcat-runtime",
         "If you deploy a WAR to an external Tomcat, switch to spring-boot-starter-tomcat-runtime (Spring Boot 4.0).", {"spring-boot": ">=4.0"}, kind="migration", sev="minor")
R[-1]["detection"]["mode"] = "ai-confirm"
R[-1]["ai_question"] = "Is this application packaged as a WAR and deployed to an external Tomcat?"
dep_rule("SB-BOOT4-JPAMODELGEN-001", "hibernate-jpamodelgen is replaced by hibernate-processor", "org.hibernate.orm:hibernate-jpamodelgen", "org.hibernate.orm:hibernate-processor",
         MIG4, "Spring Boot 4.0 Migration Guide - Hibernate Dependency Management", "Spring Boot 4.0", "hibernate-jpamodelgen is replaced by hibernate-processor",
         "Use org.hibernate.orm:hibernate-processor (Spring Boot 4.0 dependency management).", {"spring-boot": ">=4.0"}, kind="migration")
dep_rule("SB-BOOT4-ES-RESTCLIENT-001", "Elasticsearch low-level RestClient dependency management removed in Spring Boot 4", "org.elasticsearch.client:elasticsearch-rest-client", "co.elastic.clients:elasticsearch-java",
         MIG4, "Spring Boot 4.0 Migration Guide - Elasticsearch Client", "Spring Boot 4.0", "modules are no longer required and Spring Boot's dependency management for them has been removed",
         "Spring Boot 4 auto-configures the new Rest5Client from co.elastic.clients:elasticsearch-java; the old RestClient modules are unmanaged.", {"spring-boot": ">=4.0"}, kind="removal")
dep_rule("SB-BOOT3-MYSQL-001", "mysql:mysql-connector-java coordinates changed to com.mysql:mysql-connector-j", "mysql:mysql-connector-java", "com.mysql:mysql-connector-j",
         MIG3, "Spring Boot 3.0 Migration Guide - MySQL JDBC Driver", "Spring Boot 3.0", "The coordinates of the MySQL JDBC driver have changed from mysql:mysql-connector-java to com.mysql:mysql-connector-j .",
         "Use com.mysql:mysql-connector-j (Spring Boot 3.0 manages only the new coordinates).", {"spring-boot": ">=3.0"}, kind="migration", sev="critical")
dep_rule("SB-BOOT3-EMBEDDED-MONGO-001", "Flapdoodle embedded MongoDB auto-configuration was removed in Spring Boot 3", "de.flapdoodle.embed:de.flapdoodle.embed.mongo", "org.testcontainers:mongodb",
         MIG3, "Spring Boot 3.0 Migration Guide - Embedded MongoDB", "Spring Boot 3.0", "Auto-configuration and dependency management for Flapdoodle embedded MongoDB has been removed.",
         "Use Testcontainers or Flapdoodle's own Spring integration (Spring Boot 3.0).", {"spring-boot": ">=3.0"}, kind="removal")

# De-duplicate: hand-written config rules whose key is already covered by a changelog-derived rule.
_gen_keys = [((x["detection"].get("config") or {}).get("key") or (x["detection"].get("config") or {}).get("key_prefix"))
             for x in R if x["id"].startswith("SB-PROP-")]
_gen_keys = [k for k in _gen_keys if k]


def _covered(x):
    if x["id"].startswith("SB-PROP-") or x["detection"].get("engine") != "config":
        return False
    c = x["detection"]["config"]
    k = c.get("key") or c.get("key_prefix")
    return any(k == g or (g.endswith(".") and k.startswith(g)) for g in _gen_keys)


R[:] = [x for x in R if not _covered(x)]
RULES = R

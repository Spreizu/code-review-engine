from specs._java import J, api, static_call, call, new, imp, field, cls

R = RULES = []
add = R.append
DEP = dict(kind="deprecation", category="deprecation")


def dep(id, title, query, bad, good, url, quote, msg, since, removal=False, sev=None, mode="deterministic", ai=None, applies=None, fix=None, filters=None):
    add(J(id, title, **DEP, severity=sev or ("major" if removal else "minor"), applies=applies or {"java": f">={since}"},
          query=query, bad=bad, good=good, url=url, doc="Javadoc: " + url.split("/")[-1].replace(".html", ""),
          quote=quote, message=msg, mode=mode, ai=ai, fix=fix, filters=filters,
          tags=["jdk-deprecated", "for-removal"] if removal else ["jdk-deprecated"]))


dep("JAVA-DEP-RUNTIME-EXEC-001", "Runtime.exec(String) is deprecated",
    '((method_invocation object: (method_invocation name: (identifier) @g) name: (identifier) @m arguments: (argument_list . (_) .)) @match (#eq? @g "getRuntime") (#eq? @m "exec"))',
    cls('Process p = Runtime.getRuntime().exec("ls -l " + dir);'), cls('Process p = new ProcessBuilder("ls", "-l", dir).start();'),
    api("java/lang/Runtime"), "Deprecated. This method is error-prone and should not be used, the corresponding method exec(String[]) or ProcessBuilder should be used instead.",
    "Runtime.exec(String) is deprecated since JDK 18 (it tokenises the command string itself); use ProcessBuilder or exec(String[]).", 18,
    fix="new ProcessBuilder(List.of(cmd, arg...)).start()")
dep("JAVA-DEP-THREAD-GETID-001", "Thread.getId() is deprecated; use threadId()",
    '((method_invocation object: (method_invocation name: (identifier) @c) name: (identifier) @m arguments: (argument_list) @a) @match (#eq? @c "currentThread") (#eq? @m "getId") (#eq? @a "()"))',
    cls('long id = Thread.currentThread().getId();'), cls('long id = Thread.currentThread().threadId();'),
    api("java/lang/Thread"), "This method is not final and may be overridden to return a value that is not the thread ID. Use threadId() instead.",
    "Thread.getId() is deprecated since JDK 19; use Thread.threadId().", 19)
dep("JAVA-DEP-CLASS-NEWINSTANCE-001", "Class.newInstance() is deprecated",
    '((method_invocation object: (class_literal) name: (identifier) @m arguments: (argument_list) @a) @match (#eq? @m "newInstance") (#eq? @a "()"))',
    cls('Object o = Foo.class.newInstance();'), cls('Object o = Foo.class.getDeclaredConstructor().newInstance();'),
    api("java/lang/Class"), "This method propagates any exception thrown by the nullary constructor, including a checked exception.",
    "Class.newInstance() is deprecated since 9: it propagates checked exceptions from the constructor unchecked; use getDeclaredConstructor().newInstance().", 9)
dep("JAVA-DEP-BIGDECIMAL-ROUND-001", "BigDecimal.ROUND_* int constants are deprecated",
    field("BigDecimal", "^ROUND_"), cls('x = a.setScale(2, BigDecimal.ROUND_HALF_UP);'), cls('x = a.setScale(2, RoundingMode.HALF_UP);'),
    api("java/math/BigDecimal"), "Deprecated. Use RoundingMode.HALF_UP instead.",
    "BigDecimal.ROUND_* constants (and the int rounding-mode overloads) are deprecated since 9; use java.math.RoundingMode.", 9)
dep("JAVA-DEP-RUNFINALIZATION-001", "System/Runtime.runFinalization() is deprecated for removal",
    '((method_invocation name: (identifier) @m arguments: (argument_list) @a) @match (#eq? @m "runFinalization") (#eq? @a "()"))',
    cls('System.runFinalization();'), cls('System.gc();'),
    api("java/lang/System"), "Finalization has been deprecated for removal.",
    "runFinalization() is deprecated for removal since JDK 18 (JEP 421); use Cleaner / try-with-resources instead of finalization.", 18, removal=True)
dep("JAVA-DEP-EXECUTORS-PRIV-001", "Executors.privileged* factories are deprecated for removal",
    '((method_invocation object: (identifier) @c name: (identifier) @m) @match (#eq? @c "Executors") (#match? @m "^privileged"))',
    cls('Callable<String> c = Executors.privilegedCallable(task);'), cls('Callable<String> c = task;'),
    api("java/util/concurrent/Executors"), "Deprecated, for removal: This API element is subject to removal in a future version.",
    "Executors.privilegedCallable/privilegedThreadFactory only made sense with the Security Manager and are deprecated for removal (JDK 17).", 17, removal=True)
dep("JAVA-DEP-SUBJECT-DOAS-001", "Subject.doAs/doAsPrivileged/getSubject are deprecated for removal",
    '((method_invocation object: (identifier) @c name: (identifier) @m) @match (#eq? @c "Subject") (#match? @m "^(doAs|doAsPrivileged|getSubject)$"))',
    cls('Subject.doAs(subject, action);'), cls('Subject.callAs(subject, callable);'),
    api("javax/security/auth/Subject"), "This method originally performed the specified PrivilegedAction with privileges enabled.",
    "Subject.doAs/getSubject depend on the Security Manager and are deprecated for removal; use Subject.callAs(...) and Subject.current() (JDK 18+).", 18, removal=True, sev="major")
dep("JAVA-DEP-ACCESSCONTROLLER-001", "AccessController is deprecated for removal",
    '((method_invocation object: (identifier) @c) @match (#eq? @c "AccessController"))',
    cls('String v = AccessController.doPrivileged((PrivilegedAction<String>) () -> System.getProperty("k"));'), cls('String v = System.getProperty("k");'),
    api("java/security/AccessController"), "This class was only useful in conjunction with the Security Manager",
    "AccessController is deprecated for removal (JDK 17, JEP 411) and has no effect since the Security Manager was permanently disabled (JDK 24, JEP 486); call the action directly.", 17, removal=True)
dep("JAVA-DEP-X509-DN-001", "X509Certificate.getSubjectDN()/getIssuerDN() are deprecated",
    call("^(getSubjectDN|getIssuerDN)$", 0, regex=True), cls('String dn = cert.getSubjectDN().getName();'), cls('String dn = cert.getSubjectX500Principal().getName();'),
    api("java/security/cert/X509Certificate"), "Deprecated. Use getSubjectX500Principal() instead.",
    "getSubjectDN/getIssuerDN return implementation-specific Principals and are deprecated since 16; use getSubjectX500Principal()/getIssuerX500Principal().", 16)
dep("JAVA-DEP-URLENCODER-001", "URLEncoder.encode(String) uses the default charset (deprecated)",
    static_call("URLEncoder", "encode", 1), cls('String q = URLEncoder.encode(term);'), cls('String q = URLEncoder.encode(term, StandardCharsets.UTF_8);'),
    api("java/net/URLEncoder"), "The resulting string may vary depending on the default charset.",
    "URLEncoder.encode(String) is deprecated: the result depends on the default charset. Pass a Charset explicitly.", 8)
dep("JAVA-DEP-URLDECODER-001", "URLDecoder.decode(String) uses the default charset (deprecated)",
    static_call("URLDecoder", "decode", 1), cls('String q = URLDecoder.decode(raw);'), cls('String q = URLDecoder.decode(raw, StandardCharsets.UTF_8);'),
    api("java/net/URLDecoder"), "The resulting string may vary depending on the default charset.",
    "URLDecoder.decode(String) is deprecated: the result depends on the default charset. Pass a Charset explicitly.", 8)
dep("JAVA-DEP-CHARACTER-001", "Character.isSpace/isJavaLetter/isJavaLetterOrDigit are deprecated",
    '((method_invocation object: (identifier) @c name: (identifier) @m) @match (#eq? @c "Character") (#match? @m "^(isSpace|isJavaLetter|isJavaLetterOrDigit)$"))',
    cls('if (Character.isSpace(ch)) skip();'), cls('if (Character.isWhitespace(ch)) skip();'),
    api("java/lang/Character"), "Deprecated. Replaced by isWhitespace(char).",
    "Character.isSpace/isJavaLetter/isJavaLetterOrDigit are deprecated; use isWhitespace / isJavaIdentifierStart / isJavaIdentifierPart.", 8)
dep("JAVA-DEP-REF-ISENQUEUED-001", "Reference.isEnqueued() is deprecated",
    call("isEnqueued", 0), cls('if (ref.isEnqueued()) cleanup();'), cls('if (ref.refersTo(null)) cleanup();'),
    api("java/lang/ref/Reference"), "This method was originally specified to test if a reference object has been cleared and enqueued but was never implemented to do this test.",
    "Reference.isEnqueued() is deprecated since 16 and was never implemented as specified; use refersTo(null) or a ReferenceQueue.", 16)
dep("JAVA-DEP-ISACCESSIBLE-001", "AccessibleObject.isAccessible() is deprecated",
    call("isAccessible", 0), cls('if (!m.isAccessible()) m.setAccessible(true);'), cls('if (!m.canAccess(target)) m.setAccessible(true);'),
    api("java/lang/reflect/AccessibleObject"), "This method is deprecated because its name hints that it checks if the reflected object is accessible",
    "AccessibleObject.isAccessible() is deprecated since 9; use canAccess(Object).", 9)
dep("JAVA-DEP-WEAKCAS-001", "Atomic*.weakCompareAndSet is deprecated",
    call("weakCompareAndSet"), cls('counter.weakCompareAndSet(1, 2);'), cls('counter.weakCompareAndSetPlain(1, 2);'),
    api("java/util/concurrent/atomic/AtomicInteger"), "This method has plain memory effects but the method name implies volatile memory effects",
    "weakCompareAndSet has plain memory effects despite its name and is deprecated since 9; use weakCompareAndSetPlain or weakCompareAndSetVolatile.", 9)
dep("JAVA-DEP-DATE-CTOR-001", "Deprecated java.util.Date constructors (String / year-month-day)",
    '((object_creation_expression type: (type_identifier) @t arguments: (argument_list . (string_literal) .)) @match (#eq? @t "Date"))\n((object_creation_expression type: (type_identifier) @t arguments: (argument_list . (_) . (_) . (_))) @match (#eq? @t "Date"))',
    cls('Date d = new Date(2024, 1, 15);'), cls('LocalDate d = LocalDate.of(2024, 2, 15);'),
    api("java/util/Date"), "As of JDK version 1.1, replaced by Calendar.set(year + 1900, month, date) or GregorianCalendar(year + 1900, month, date) .",
    "Date(String) and Date(int year, int month, ...) are deprecated since JDK 1.1 (year is offset by 1900, month is 0-based); use java.time (LocalDate, Instant).", 8)
dep("JAVA-DEP-DATE-STATIC-001", "Date.parse / Date.UTC are deprecated",
    '((method_invocation object: (identifier) @c name: (identifier) @m) @match (#eq? @c "Date") (#match? @m "^(parse|UTC)$"))',
    cls('long t = Date.parse("Sat, 12 Aug 1995 13:30:00 GMT");'), cls('long t = Instant.parse("1995-08-12T13:30:00Z").toEpochMilli();'),
    api("java/util/Date"), "As of JDK version 1.1, replaced by DateFormat.parse(String s) .",
    "Date.parse/Date.UTC are deprecated since JDK 1.1; use java.time parsing (Instant.parse, DateTimeFormatter).", 8)
dep("JAVA-DEP-MULTICAST-TTL-001", "MulticastSocket.setTTL/getTTL are deprecated for removal",
    call("^(setTTL|getTTL)$", regex=True), cls('socket.setTTL((byte) 4);'), cls('socket.setTimeToLive(4);'),
    api("java/net/MulticastSocket"), "use the setTimeToLive(int) method instead, which uses int instead of byte as the type for ttl.",
    "MulticastSocket.setTTL/getTTL are deprecated for removal; use setTimeToLive/getTimeToLive.", 8, removal=True)
dep("JAVA-DEP-PROXYCLASS-001", "Proxy.getProxyClass is deprecated",
    static_call("Proxy", "getProxyClass"), cls('Class<?> c = Proxy.getProxyClass(loader, Foo.class);'), cls('Foo f = (Foo) Proxy.newProxyInstance(loader, new Class<?>[] { Foo.class }, handler);'),
    api("java/lang/reflect/Proxy"), "Proxy classes generated in a named module are encapsulated and not accessible to code outside its module.",
    "Proxy.getProxyClass is deprecated since 9; use Proxy.newProxyInstance.", 9)
dep("JAVA-DEP-INFLATER-TOTAL-001", "Inflater/Deflater.getTotalIn/getTotalOut are deprecated (JDK 23)",
    call("^(getTotalIn|getTotalOut)$", 0, regex=True), cls('int n = inflater.getTotalIn();'), cls('long n = inflater.getBytesRead();'),
    api("java/util/zip/Inflater"), "Deprecated. Use getBytesRead() instead",
    "getTotalIn/getTotalOut return int and overflow for large streams; deprecated in JDK 23 in favour of getBytesRead/getBytesWritten.", 23)
dep("JAVA-DEP-SSL-PEERCHAIN-001", "SSLSession.getPeerCertificateChain() is deprecated for removal",
    call("getPeerCertificateChain", 0), cls('var chain = session.getPeerCertificateChain();'), cls('var chain = session.getPeerCertificates();'),
    api("javax/net/ssl/SSLSession"), "The getPeerCertificates() method that returns an array of java.security.cert.Certificate should be used instead.",
    "getPeerCertificateChain() returns the legacy javax.security.cert types and is deprecated for removal; use getPeerCertificates().", 9, removal=True)
dep("JAVA-DEP-FILE-TOURL-001", "File.toURL() is deprecated", call("toURL", 0), cls('URL u = new File(path).toURL();'), cls('URL u = new File(path).toURI().toURL();'),
    api("java/io/File"), "Deprecated. This method does not automatically escape characters that are illegal in URLs.",
    "File.toURL() does not escape illegal URL characters and is deprecated; use file.toURI().toURL(). (URI.toURL() itself is fine.)", 8,
    mode="ai-confirm", ai="Is the receiver of toURL() a java.io.File (deprecated) rather than a java.net.URI (fine)?",
    filters=["node.lacks_descendant_text:toURI()"])
dep("JAVA-DEP-THREADGROUP-001", "ThreadGroup destroy/isDestroyed are deprecated for removal",
    call("^(destroy|isDestroyed)$", 0, regex=True), cls('ThreadGroup g = new ThreadGroup("w"); g.destroy();'), cls('ThreadGroup g = new ThreadGroup("w");'),
    api("java/lang/ThreadGroup"), "This method was originally specified to destroy an empty thread group.",
    "ThreadGroup.destroy/isDestroyed (and daemon status) are deprecated for removal since JDK 16; thread groups can no longer be destroyed.", 16, removal=True,
    mode="ai-confirm", ai="Is destroy()/isDestroyed() invoked on a java.lang.ThreadGroup?", filters=["file.has_text:ThreadGroup"])
dep("JAVA-DEP-OBSERVABLE-001", "java.util.Observable/Observer are deprecated",
    '((superclass (type_identifier) @t) @match (#eq? @t "Observable"))\n((super_interfaces (type_list (type_identifier) @t)) @match (#eq? @t "Observer"))',
    "class Model extends Observable {}\n", "class Model { private final PropertyChangeSupport pcs = new PropertyChangeSupport(this); }\n",
    api("java/util/Observable"), "This class and the Observer interface have been deprecated.",
    "Observable/Observer are deprecated since 9; use java.beans PropertyChangeSupport or java.util.concurrent.Flow.", 9)


def removed(id, title, regex, bad, good, url, quote, msg, since, sev="critical"):
    add(J(id, title, kind="removal", category="removal", severity=sev, applies={"java": f">={since}"},
          query=imp(regex), bad=bad, good=good, url=url, doc=url.split("/")[-1].replace("jeps/", "JEP "), doc_version=f"JEP (delivered in JDK {since})",
          quote=quote, message=msg, tags=["jdk-removed"]))


IMP = "^import\\\\s+(static\\\\s+)?"
removed("JAVA-REM-JAXB-001", "JAXB (javax.xml.bind) was removed from the JDK in 11", IMP + "javax\\\\.xml\\\\.bind\\\\.",
        "import javax.xml.bind.JAXBContext;\nclass A {}\n", "import jakarta.xml.bind.JAXBContext;\nclass A {}\n",
        "https://openjdk.org/jeps/320", "java.xml.bind (JAXB)", "javax.xml.bind was removed in JDK 11 (JEP 320); add the Jakarta XML Binding API + implementation as dependencies.", 11)
removed("JAVA-REM-JAXWS-001", "JAX-WS / SAAJ / Web Services Metadata were removed in JDK 11", IMP + "javax\\\\.(xml\\\\.ws|xml\\\\.soap|jws)\\\\.",
        "import javax.xml.ws.Service;\nclass A {}\n", "import jakarta.xml.ws.Service;\nclass A {}\n",
        "https://openjdk.org/jeps/320", "java.xml.ws (JAX-WS, plus the related technologies SAAJ and Web Services Metadata )",
        "javax.xml.ws / javax.xml.soap / javax.jws were removed in JDK 11 (JEP 320); use the Jakarta XML Web Services artifacts.", 11)
removed("JAVA-REM-CORBA-001", "CORBA (org.omg.*, javax.rmi.CORBA) was removed in JDK 11", IMP + "(org\\\\.omg\\\\.|javax\\\\.rmi\\\\.CORBA|javax\\\\.activity)",
        "import org.omg.CORBA.ORB;\nclass A {}\n", "import java.net.http.HttpClient;\nclass A {}\n",
        "https://openjdk.org/jeps/320", "java.corba (CORBA)", "The CORBA modules were removed in JDK 11 (JEP 320).", 11)
removed("JAVA-REM-ACTIVATION-001", "JavaBeans Activation Framework (javax.activation) was removed in JDK 11", IMP + "javax\\\\.activation\\\\.",
        "import javax.activation.DataHandler;\nclass A {}\n", "import jakarta.activation.DataHandler;\nclass A {}\n",
        "https://openjdk.org/jeps/320", "java.activation (JAF)", "javax.activation was removed in JDK 11 (JEP 320); depend on jakarta.activation.", 11)
removed("JAVA-REM-ANNOTATION-001", "Common Annotations (javax.annotation.PostConstruct etc.) were removed from the JDK in 11", IMP + "javax\\\\.annotation\\\\.(PostConstruct|PreDestroy|Resource|Resources|Generated|Priority)",
        "import javax.annotation.PostConstruct;\nclass A {}\n", "import jakarta.annotation.PostConstruct;\nclass A {}\n",
        "https://openjdk.org/jeps/320", "java.xml.ws.annotation (Common Annotations)", "javax.annotation.PostConstruct/PreDestroy/Resource were removed in JDK 11 (JEP 320); use jakarta.annotation.", 11, sev="major")
removed("JAVA-REM-JTA-001", "javax.transaction (JTA subset) left the JDK in 11", IMP + "javax\\\\.transaction\\\\.",
        "import javax.transaction.Transactional;\nclass A {}\n", "import jakarta.transaction.Transactional;\nclass A {}\n",
        "https://openjdk.org/jeps/320", "java.transaction (JTA)", "The java.transaction module was removed in JDK 11 (JEP 320); use jakarta.transaction (or Spring's @Transactional).", 11, sev="major")
removed("JAVA-REM-NASHORN-001", "The Nashorn JavaScript engine was removed in JDK 15", IMP + "jdk\\\\.nashorn\\\\.",
        "import jdk.nashorn.api.scripting.ScriptObjectMirror;\nclass A {}\n", "import org.graalvm.polyglot.Context;\nclass A {}\n",
        "https://openjdk.org/jeps/372", "jdk.scripting.nashorn -- contains the jdk.nashorn.api.scripting and jdk.nashorn.api.tree packages.",
        "jdk.nashorn.* was removed in JDK 15 (JEP 372); use a standalone engine (e.g. GraalJS or the standalone Nashorn artifact).", 15)
add(J("JAVA-REM-NASHORN-002", "ScriptEngineManager lookups of \"nashorn\"/\"js\" return null on JDK 15+", kind="removal", category="removal", severity="critical",
      applies={"java": ">=15"}, query='((method_invocation name: (identifier) @m arguments: (argument_list (string_literal) @s)) @match (#match? @m "^getEngineBy(Name|Extension|MimeType)$") (#match? @s "(?i)nashorn|\\"js\\"|javascript"))',
      bad=cls('ScriptEngine e = new ScriptEngineManager().getEngineByName("nashorn");'), good=cls('ScriptEngine e = new ScriptEngineManager().getEngineByName("groovy");'),
      url="https://openjdk.org/jeps/372", doc="JEP 372: Remove the Nashorn JavaScript Engine", doc_version="JEP (delivered in JDK 15)",
      quote="This removal does not affect, in any way, the javax.script API.",
      message="The JDK no longer ships a JavaScript ScriptEngine (JEP 372, JDK 15); getEngineByName(\"nashorn\"/\"js\") returns null unless an engine is on the class path."))
removed("JAVA-REM-RMIACT-001", "RMI Activation (java.rmi.activation) was removed in JDK 17", IMP + "java\\\\.rmi\\\\.activation",
        "import java.rmi.activation.Activatable;\nclass A {}\n", "import java.rmi.server.UnicastRemoteObject;\nclass A {}\n",
        "https://openjdk.org/jeps/407", "Remove the java.rmi.activation package from the Java SE API specification", "java.rmi.activation was removed in JDK 17 (JEP 407).", 17)
removed("JAVA-REM-PACK200-001", "java.util.jar.Pack200 was removed in JDK 14", IMP + "java\\\\.util\\\\.jar\\\\.Pack200",
        "import java.util.jar.Pack200;\nclass A {}\n", "import java.util.zip.GZIPOutputStream;\nclass A {}\n",
        "https://openjdk.org/jeps/367", "java.util.jar.Pack200 java.util.jar.Pack200.Packer java.util.jar.Pack200.Unpacker", "Pack200 was removed in JDK 14 (JEP 367).", 14)
add(J("JAVA-REM-STRICTFP-001", "strictfp is redundant since Java 17", kind="modernization", category="modernization", severity="info", applies={"java": ">=17"},
      query='((modifiers) @match (#match? @match "(^|\\\\s)strictfp(\\\\s|$)"))', bad="strictfp class Calc {}\n", good="class Calc {}\n",
      url="https://openjdk.org/jeps/306", doc="JEP 306: Restore Always-Strict Floating-Point Semantics", doc_version="JEP (delivered in JDK 17)",
      quote="updating javac to issue new lint warnings to unnecessary use of the strictfp modifier",
      message="All floating-point operations are strict since Java 17 (JEP 306); strictfp has no effect and javac warns about it."))
add(J("JAVA-REM-SM-PERM-002", "Security-Manager permission checks are dead code on JDK 24+", kind="removal", category="removal", severity="major", applies={"java": ">=24"},
      query='((method_invocation object: (identifier) @c name: (identifier) @m) @match (#eq? @c "System") (#eq? @m "getSecurityManager"))',
      bad=cls('SecurityManager sm = System.getSecurityManager(); if (sm != null) sm.checkPermission(p);'), good=cls('doWork();'),
      url="https://openjdk.org/jeps/486", doc="JEP 486: Permanently Disable the Security Manager", doc_version="JEP (delivered in JDK 24)",
      quote="Permanently Disable the Security Manager",
      message="System.getSecurityManager() always returns null on JDK 24+ (JEP 486); permission-check branches are dead code and can be removed.", xref=["JAVA-SM-001"]))


def modern(id, title, query, bad, good, url, quote, msg, since, doc, docv=None, sev="info", mode="deterministic", ai=None, filters=None, kind="modernization"):
    add(J(id, title, kind=kind, category="modernization" if kind == "modernization" else "best-practice", severity=sev, applies={"java": f">={since}"}, query=query, bad=bad, good=good,
          url=url, doc=doc, doc_version=docv or f"JDK {since}+ (JDK 25 docs)", quote=quote, message=msg, mode=mode, ai=ai, filters=filters))


modern("JAVA-MOD-UNNAMED-001", "Use the unnamed variable _ for unused catch parameters (Java 22+)",
       '((catch_formal_parameter name: (identifier) @match) (#match? @match "^(ignored|ignore|unused|expected)$"))',
       cls('try { parse(); } catch (NumberFormatException ignored) { fallback(); }'), cls('try { parse(); } catch (NumberFormatException _) { fallback(); }'),
       "https://openjdk.org/jeps/456", "catch (NumberFormatException _) { // Unnamed variable",
       "Since Java 22 an unused catch parameter (or lambda/pattern variable) can be declared as _ (JEP 456), making the intent explicit.", 22, "JEP 456: Unnamed Variables & Patterns", "JEP 456 (final in JDK 22)")
modern("JAVA-MOD-STREAM-TOLIST-001", "Prefer Stream.toList() over collect(Collectors.toList()) (Java 16+)",
       '((method_invocation name: (identifier) @m arguments: (argument_list . (method_invocation object: (identifier) @c name: (identifier) @t) .)) @match (#eq? @m "collect") (#eq? @c "Collectors") (#eq? @t "toList"))',
       cls('List<String> names = users.stream().map(User::name).collect(Collectors.toList());'), cls('List<String> names = users.stream().map(User::name).toList();'),
       api("java/util/stream/Stream"), "The returned List is unmodifiable; calls to any mutator method will always cause UnsupportedOperationException to be thrown.",
       "Stream.toList() (Java 16) is shorter and returns an unmodifiable list. Confirm callers do not mutate the result before switching.", 16, "Javadoc: Stream.toList",
       mode="ai-confirm", ai="Is the collected list ever mutated (add/remove/set/sort) afterwards? If not, Stream.toList() is a safe replacement.")
modern("JAVA-MOD-MATH-CLAMP-001", "Use Math.clamp (Java 21+) instead of nested Math.max/Math.min",
       '((method_invocation object: (identifier) @a name: (identifier) @b arguments: (argument_list (method_invocation object: (identifier) @c name: (identifier) @d))) @match (#eq? @a "Math") (#eq? @c "Math") (#match? @b "^(max|min)$") (#match? @d "^(max|min)$") (#not-eq? @b @d))',
       cls('int v = Math.max(lo, Math.min(hi, x));'), cls('int v = Math.clamp(x, lo, hi);'),
       api("java/lang/Math"), "Clamps the value to fit between min and max.", "Math.clamp(value, min, max) (Java 21) states the intent and validates min <= max.", 21, "Javadoc: Math.clamp")
modern("JAVA-MOD-STRINGBUFFER-001", "Prefer StringBuilder over StringBuffer for thread-confined building",
       new("StringBuffer"), cls('StringBuffer sb = new StringBuffer();'), cls('StringBuilder sb = new StringBuilder();'),
       api("java/lang/StringBuffer"), "The StringBuilder class should generally be used in preference to this one, as it supports all of the same operations but it is faster, as it performs no synchronization.",
       "StringBuffer synchronises every call; when the buffer does not escape the thread use StringBuilder.", 8, "Javadoc: StringBuffer",
       mode="ai-confirm", ai="Is this StringBuffer confined to one thread (local variable not shared)?", kind="best-practice", sev="minor")
modern("JAVA-MOD-VECTOR-001", "Avoid legacy synchronized Vector / Hashtable",
       '((object_creation_expression type: [(type_identifier) @t (generic_type (type_identifier) @t)]) @match (#match? @t "^(Vector|Hashtable)$"))',
       cls('List<String> l = new Vector<>();'), cls('List<String> l = new ArrayList<>();'),
       api("java/util/Vector"), "If a thread-safe implementation is not needed, it is recommended to use ArrayList in place of Vector .",
       "Vector/Hashtable are synchronized legacy collections; use ArrayList/HashMap, or ConcurrentHashMap/CopyOnWriteArrayList when concurrency is needed.", 8, "Javadoc: Vector / Hashtable", kind="best-practice", sev="minor")
modern("JAVA-MOD-STACK-001", "Prefer Deque/ArrayDeque over java.util.Stack",
       '((object_creation_expression type: [(type_identifier) @t (generic_type (type_identifier) @t)]) @match (#eq? @t "Stack"))',
       cls('Stack<Node> todo = new Stack<>();'), cls('Deque<Node> todo = new ArrayDeque<>();'),
       api("java/util/Stack"), "A more complete and consistent set of LIFO stack operations is provided by the Deque interface and its implementations, which should be used in preference to this class.",
       "java.util.Stack extends Vector (synchronized); the javadoc recommends Deque/ArrayDeque.", 8, "Javadoc: Stack", kind="best-practice", sev="minor")
modern("JAVA-MOD-STRINGTOKENIZER-001", "StringTokenizer is a legacy class",
       new("StringTokenizer"), cls('StringTokenizer st = new StringTokenizer(line, ",");'), cls('String[] parts = line.split(",");'),
       api("java/util/StringTokenizer"), "StringTokenizer is a legacy class that is retained for compatibility reasons although its use is discouraged in new code.",
       "StringTokenizer is discouraged in new code; use String.split or java.util.regex.", 8, "Javadoc: StringTokenizer", kind="best-practice", sev="info")
modern("JAVA-MOD-COMPACT-MAIN-001", "Simple programs can use an instance main method (Java 25+)",
       '((method_declaration (modifiers) @mods name: (identifier) @n parameters: (formal_parameters (formal_parameter type: (array_type)))) @match (#eq? @n "main") (#match? @mods "public static"))',
       "public class Hello {\n  public static void main(String[] args) {\n    System.out.println(\"hi\");\n  }\n}\n", "void main() {\n  IO.println(\"hi\");\n}\n",
       "https://openjdk.org/jeps/512", "Compact Source Files and Instance Main Methods",
       "Java 25 (JEP 512) allows instance main methods and compact source files; for scripts and small tools `void main()` is enough. Keep the classic form for libraries / launch-compatible apps.", 25,
       "JEP 512: Compact Source Files and Instance Main Methods", "JEP 512 (final in JDK 25)",
       mode="ai-confirm", ai="Is this a small stand-alone program or script (not a framework entry point that must stay public static main)?")
modern("JAVA-MOD-FLEX-CTOR-001", "Validate arguments before super(...) with flexible constructor bodies (Java 25+)",
       '((constructor_body . (explicit_constructor_invocation arguments: (argument_list (method_invocation name: (identifier) @m)))) @match (#match? @m "^(validate|verify|check|require)"))',
       "class Positive extends Num {\n  Positive(long v) { super(verify(v)); }\n}\n",
       "class Positive extends Num {\n  Positive(long v) {\n    if (v <= 0) throw new IllegalArgumentException();\n    super(v);\n  }\n}\n",
       "https://openjdk.org/jeps/513", "Flexible Constructor Bodies",
       "Since Java 25 (JEP 513) statements may precede super(...)/this(...), so argument validation no longer needs static helper calls inside the super() argument list.", 25,
       "JEP 513: Flexible Constructor Bodies", "JEP 513 (final in JDK 25)")

SCG = "https://www.oracle.com/java/technologies/javase/seccodeguide.html"


def sec(id, title, query, bad, good, url, quote, msg, doc, sev="critical", mode="ai-confirm", ai=None, filters=None, docv="Secure Coding Guidelines for Java SE (current)", fix=None):
    add(J(id, title, kind="security", category="security", severity=sev, query=query, bad=bad, good=good, url=url, doc=doc, doc_version=docv,
          quote=quote, message=msg, mode=mode, ai=ai, filters=filters, fix=fix, tags=["security"]))


SQLM = "^(executeQuery|executeUpdate|execute|executeLargeUpdate|addBatch|createQuery|createNativeQuery|queryForObject|queryForList|queryForMap|query|update|batchUpdate)$"
sec("JAVA-SEC-SQLI-001", "Dynamic SQL built by string concatenation",
    '((method_invocation name: (identifier) @m arguments: (argument_list . (binary_expression operator: "+"))) @match (#match? @m "' + SQLM + '"))',
    cls('ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE id = \'" + id + "\'");'),
    cls('PreparedStatement ps = con.prepareStatement("SELECT * FROM users WHERE id = ?"); ps.setString(1, id);'),
    SCG, "Guideline 3-2 / INJECT-2: Avoid dynamic SQL",
    "SQL text is concatenated with variables. Untrusted input in dynamic SQL is an injection vector; use PreparedStatement / bind parameters.",
    "Secure Coding Guidelines for Java SE - INJECT-2", ai="Can any concatenated value originate from user/untrusted input (not a constant or allow-listed identifier)?")
sec("JAVA-SEC-SQLI-FORMAT-002", "Dynamic SQL built with String.format / formatted()",
    '((method_invocation name: (identifier) @m arguments: (argument_list . (method_invocation name: (identifier) @f))) @match (#match? @m "' + SQLM + '") (#match? @f "^(format|formatted)$"))',
    cls('stmt.executeQuery(String.format("SELECT * FROM t WHERE name = \'%s\'", name));'),
    cls('var ps = con.prepareStatement("SELECT * FROM t WHERE name = ?"); ps.setString(1, name);'),
    SCG, "It is well known that dynamically created SQL statements including untrusted input are subject to command injection.",
    "SQL text is built with String.format; values are not bound as parameters.", "Secure Coding Guidelines for Java SE - INJECT-2",
    ai="Can any formatted value originate from untrusted input?")
sec("JAVA-SEC-SQL-PREP-CONCAT-002", "PreparedStatement created from a concatenated SQL string defeats parameterisation",
    '((method_invocation name: (identifier) @m arguments: (argument_list . (binary_expression) .)) @match (#eq? @m "prepareStatement"))',
    cls('var ps = con.prepareStatement("DELETE FROM t WHERE name = \'" + name + "\'");'), cls('var ps = con.prepareStatement("DELETE FROM t WHERE name = ?");'),
    SCG, "It is well known that dynamically created SQL statements including untrusted input are subject to command injection.",
    "prepareStatement() is called with concatenated SQL, so values are not bound as parameters.", "Secure Coding Guidelines for Java SE - INJECT-2",
    ai="Is any concatenated part derived from untrusted input (as opposed to a fixed identifier)?")
sec("JAVA-SEC-CMD-001", "Process command line built from variables",
    '((method_invocation name: (identifier) @m arguments: (argument_list . (binary_expression operator: "+"))) @match (#eq? @m "exec"))\n((object_creation_expression type: (type_identifier) @t arguments: (argument_list (binary_expression operator: "+"))) @match (#eq? @t "ProcessBuilder"))',
    cls('new ProcessBuilder("sh", "-c", "convert " + userFile).start();'),
    cls('new ProcessBuilder("convert", userFile.toString()).start();'),
    SCG, "Guideline 3-4 / INJECT-4: Avoid any untrusted data on the command line",
    "A process command line is assembled by concatenation. Untrusted data on the command line can inject options or shell commands.",
    "Secure Coding Guidelines for Java SE - INJECT-4", ai="Could the concatenated value be attacker-controlled? Answer yes at high confidence for either risk: shell injection (a shell such as sh -c / cmd /c parses the string) or argument injection (Runtime.exec(String) splits the string on whitespace, so a value can add extra arguments or options to the program even without a shell). Answer no only if every concatenated part is a constant, a number, or validated against an allow-list.")
sec("JAVA-SEC-DESER-001", "Deserialization with ObjectInputStream without a filter",
    new("ObjectInputStream"), cls('Object o = new ObjectInputStream(socket.getInputStream()).readObject();'),
    cls('var in = new ObjectInputStream(socket.getInputStream()); in.setObjectInputFilter(ObjectInputFilter.Config.createFilter("com.acme.*;!*")); Object o = in.readObject();'),
    api("java/io/ObjectInputStream"), "Warning: Deserialization of untrusted data is inherently dangerous and should be avoided.",
    "Java deserialization of untrusted data can lead to remote code execution. Avoid it, or set an ObjectInputFilter (JEP 290/415) that allow-lists classes.",
    "Javadoc: ObjectInputStream", docv="JDK 25 API", filters=["file.lacks_text:setObjectInputFilter"],
    ai="Can the stream contain data from outside the trust boundary (network, uploads, message queues)? Is there a JVM-wide jdk.serialFilter?")
sec("JAVA-SEC-SERIAL-FILTER-002", "readObject() on a stream without any serialization filter",
    '((method_invocation name: (identifier) @m arguments: (argument_list) @a) @match (#eq? @m "readObject") (#eq? @a "()"))',
    cls('ObjectInputStream in = open(); Object o = in.readObject();'), cls('ObjectInputStream in = open(); in.setObjectInputFilter(filter); Object o = in.readObject();'),
    SCG, "Guideline 8-6 / SERIAL-6: Filter untrusted serial data",
    "readObject() on data that may be untrusted should be protected by a serialization filter (ObjectInputFilter / jdk.serialFilter).", "Secure Coding Guidelines for Java SE - SERIAL-6",
    sev="major", filters=["file.lacks_text:ObjectInputFilter", "file.has_text:ObjectInputStream"],
    ai="Does this readObject() read data that could come from outside the trust boundary, without any ObjectInputFilter configured?")
XXE_GOOD = {
    "DocumentBuilderFactory": 'var f = DocumentBuilderFactory.newInstance(); f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);',
    "SAXParserFactory": 'var f = SAXParserFactory.newInstance(); f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);',
    "XMLInputFactory": 'var f = XMLInputFactory.newInstance(); f.setProperty(XMLInputFactory.SUPPORT_DTD, false);',
    "TransformerFactory": 'var f = TransformerFactory.newInstance(); f.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");',
    "SchemaFactory": 'var f = SchemaFactory.newInstance(W3C); f.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");',
    "XMLReaderFactory": 'var r = XMLReaderFactory.createXMLReader(); r.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);',
}
for fac, good in XXE_GOOD.items():
    bad = good.split(";")[0] + ";"
    sec(f"JAVA-SEC-XXE-{fac.upper().replace('FACTORY', '')}-001", f"{fac} used without restricting DTDs/external entities (XXE)",
        f'((method_invocation object: (identifier) @c name: (identifier) @m) @match (#eq? @c "{fac}") (#match? @m "^(new(Instance|DefaultInstance|Factory|DefaultFactory)|createXMLReader)$"))',
        cls(bad), cls(good), SCG, "XML External Entity (XXE) attacks insert local files into XML data which may then be accessible to the client.",
        f"{fac} parsing untrusted XML must disable DTDs/external entities (or restrict ACCESS_EXTERNAL_DTD/SCHEMA), otherwise it is open to XXE.",
        "Secure Coding Guidelines for Java SE - INJECT-5", sev="major",
        filters=["file.lacks_text:disallow-doctype-decl", "file.lacks_text:SUPPORT_DTD", "file.lacks_text:ACCESS_EXTERNAL_DTD"],
        ai="Is the XML parsed from an untrusted source, and are DTDs/external entities left enabled for this factory?")
sec("JAVA-SEC-JAXP-FSP-001", "Enable FEATURE_SECURE_PROCESSING on JAXP factories handling untrusted XML",
    '((method_invocation object: (identifier) @c name: (identifier) @m) @match (#match? @c "^(DocumentBuilderFactory|SAXParserFactory|TransformerFactory|SchemaFactory|XPathFactory)$") (#match? @m "^newInstance$"))',
    cls('var f = XPathFactory.newInstance();'), cls('var f = XPathFactory.newInstance(); f.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);'),
    "https://docs.oracle.com/en/java/javase/25/security/java-api-xml-processing-jaxp-security-guide.html",
    "which enables a baseline of secure XML processing by imposing key restrictions through various f",
    "FEATURE_SECURE_PROCESSING imposes entity-expansion and size limits; set it explicitly on factories that process untrusted XML.", "JAXP Security Guide",
    sev="minor", docv="Java SE 25 Security Developer's Guide", filters=["file.lacks_text:FEATURE_SECURE_PROCESSING"],
    ai="Does this factory process XML/XPath input that can come from an untrusted source?")
sec("JAVA-SEC-RANDOM-001", "java.util.Random used for security-sensitive values",
    '((object_creation_expression type: [(type_identifier) (scoped_type_identifier)] @t) @match (#match? @t "^(java\\.util\\.)?Random$"))',
    cls('String token = Long.toHexString(new Random().nextLong());'), cls('byte[] b = new byte[16]; new SecureRandom().nextBytes(b);'),
    api("java/util/Random"), "Instances of java.util.Random are not cryptographically secure. Consider instead using SecureRandom",
    "java.util.Random is predictable. For tokens, passwords, nonces or keys use SecureRandom.", "Javadoc: Random", docv="JDK 25 API", sev="major",
    ai="Is the random value used for anything security-sensitive (token, password, session id, nonce, key, OTP)?")
sec("JAVA-SEC-MATHRANDOM-001", "Math.random() used for security-sensitive values", static_call("Math", "random", 0),
    cls('String otp = String.valueOf((int) (Math.random() * 1000000));'), cls('String otp = String.valueOf(new SecureRandom().nextInt(1000000));'),
    api("java/util/Random"), "Instances of java.util.Random are not cryptographically secure.",
    "Math.random() is not a cryptographically secure generator; it must not produce security-sensitive values.", "Javadoc: Random (Math.random)", docv="JDK 25 API", sev="major",
    ai="Is the value used for a security-sensitive purpose (OTP, token, password, id that must be unguessable)?")
sec("JAVA-SEC-PRINTSTACK-001", "printStackTrace() may leak internal details",
    '((method_invocation name: (identifier) @m arguments: (argument_list) @a) @match (#eq? @m "printStackTrace") (#eq? @a "()"))',
    cls('try { run(); } catch (Exception e) { e.printStackTrace(); }'), cls('try { run(); } catch (Exception e) { log.error("run failed", e); }'),
    SCG, "Guideline 2-1 / CONFIDENTIAL-1: Purge sensitive information from exceptions",
    "printStackTrace() writes to stderr bypassing logging configuration; stack traces sent to clients leak sensitive internals.", "Secure Coding Guidelines for Java SE - CONFIDENTIAL-1",
    sev="minor", mode="deterministic")


def conc(id, title, query, bad, good, url, quote, msg, doc, sev="major", mode="deterministic", ai=None, filters=None, applies=None, kind="anti-pattern", docv="JDK 25 API", cat="concurrency"):
    add(J(id, title, kind=kind, category=cat, severity=sev, query=query, bad=bad, good=good, url=url, doc=doc, doc_version=docv,
          quote=quote, message=msg, mode=mode, ai=ai, filters=filters, applies=applies or {"java": ">=8"}, tags=[cat]))


conc("JAVA-CONC-WAIT-LOOP-001", "Object.wait() must be called in a loop that re-checks the condition",
     '((method_invocation name: (identifier) @m) @match (#eq? @m "wait"))',
     "class Q {\n  synchronized void take() throws InterruptedException {\n    if (items.isEmpty()) wait();\n  }\n}\n",
     "class Q {\n  synchronized void take() throws InterruptedException {\n    while (items.isEmpty()) wait();\n  }\n}\n",
     api("java/lang/Object"), "The recommended approach to waiting is to check the condition being awaited in a while loop around the call to wait",
     "wait() outside a while loop is vulnerable to spurious wakeups and missed conditions.", "Javadoc: Object.wait",
     filters=["node.lacks_ancestor:while_statement|do_statement|for_statement"], mode="ai-confirm", ai="Is this Object.wait() (not an unrelated method named wait) and is the condition not re-checked in a loop?")
conc("JAVA-CONC-THREAD-RUN-001", "Thread.run() called directly instead of start()",
     '((method_invocation object: (object_creation_expression type: (type_identifier) @t) name: (identifier) @m) @match (#eq? @t "Thread") (#eq? @m "run"))',
     cls('new Thread(task).run();'), cls('new Thread(task).start();'),
     api("java/lang/Thread"), "This method is not intended to be invoked directly.",
     "Calling run() executes the task on the current thread; use start() (or an executor / Thread.ofVirtual().start).", "Javadoc: Thread.run")
conc("JAVA-CONC-SDF-STATIC-001", "Shared static SimpleDateFormat/DateFormat is not thread-safe",
     '((field_declaration (modifiers) @mods type: (type_identifier) @t) @match (#match? @mods "static") (#match? @t "^(SimpleDateFormat|DateFormat|DecimalFormat|NumberFormat|MessageFormat)$"))',
     "class Fmt {\n  static final SimpleDateFormat F = new SimpleDateFormat(\"yyyy-MM-dd\");\n}\n",
     "class Fmt {\n  static final DateTimeFormatter F = DateTimeFormatter.ISO_LOCAL_DATE;\n}\n",
     api("java/text/SimpleDateFormat"), "Date formats are not synchronized. It is recommended to create separate format instances for each thread.",
     "java.text formats are mutable and not thread-safe; a static instance is shared by all threads. Use java.time DateTimeFormatter (immutable) or per-thread instances.", "Javadoc: SimpleDateFormat")
conc("JAVA-CONC-CHECKPUT-001", "Check-then-act on a Map (containsKey + put) is not atomic",
     '((if_statement condition: (parenthesized_expression (unary_expression operand: (method_invocation object: (_) @m1 name: (identifier) @c))) consequence: (_ (expression_statement (method_invocation object: (_) @m2 name: (identifier) @p)))) @match (#eq? @c "containsKey") (#eq? @p "put") (#eq? @m1 @m2))',
     cls('if (!cache.containsKey(k)) { cache.put(k, load(k)); }'), cls('cache.computeIfAbsent(k, this::load);'),
     api("java/util/Map"), "If the specified key is not already associated with a value (or is mapped to null ) associates it with the given value and returns null",
     "containsKey followed by put is a race on concurrent maps and does two lookups; use putIfAbsent / computeIfAbsent.", "Javadoc: Map.putIfAbsent / computeIfAbsent",
     sev="minor", mode="ai-confirm", ai="Is this map shared between threads (field, ConcurrentHashMap, cache)? If so the check-then-act is a race.")
conc("JAVA-CONC-CF-COMMONPOOL-001", "CompletableFuture supplyAsync/runAsync without an Executor run on the common pool",
     '((method_invocation object: (identifier) @c name: (identifier) @m arguments: (argument_list . (_) .)) @match (#eq? @c "CompletableFuture") (#match? @m "^(supplyAsync|runAsync)$"))',
     cls('CompletableFuture.supplyAsync(() -> http.get(url));'), cls('CompletableFuture.supplyAsync(() -> http.get(url), ioExecutor);'),
     api("java/util/concurrent/CompletableFuture"), "All async methods without an explicit Executor argument, as well as those involving delays are performed using the ForkJoinPool.commonPool() .",
     "Blocking work (I/O, JDBC, HTTP) on the common pool starves parallel streams and other async stages; pass an explicit Executor (e.g. virtual threads).", "Javadoc: CompletableFuture",
     sev="minor", mode="ai-confirm", ai="Does the supplied task block (I/O, sleep, locks, remote calls)?")
conc("JAVA-CONC-EXECUTOR-CLOSE-001", "ExecutorService created but never shut down",
     '((method_invocation object: (identifier) @c name: (identifier) @m) @match (#eq? @c "Executors") (#match? @m "^new(Fixed|Cached|SingleThread|Scheduled|WorkStealing|VirtualThreadPerTask|ThreadPerTask)"))',
     cls('ExecutorService ex = Executors.newFixedThreadPool(4); ex.submit(task);'),
     cls('try (ExecutorService ex = Executors.newFixedThreadPool(4)) { ex.submit(task); }'),
     api("java/util/concurrent/ExecutorService"), "An unused ExecutorService should be shut down to allow reclamation of its resources.",
     "An ExecutorService that is never shut down leaks threads. Since Java 19 it is AutoCloseable: use try-with-resources, or shut it down in a lifecycle hook.", "Javadoc: ExecutorService",
     mode="ai-confirm", filters=["node.not_in_try_with_resources", "file.lacks_text:shutdown"], ai="Is this executor leaked (created per call, never shut down) rather than a managed long-lived component?", cat="resource-leak")
conc("JAVA-CONC-CME-001", "Collection modified while iterating with for-each",
     '((enhanced_for_statement value: (identifier) @coll body: (block (expression_statement (method_invocation object: (identifier) @obj name: (identifier) @m)))) @match (#eq? @coll @obj) (#match? @m "^(remove|add|clear|addAll|removeAll)$"))\n((enhanced_for_statement value: (identifier) @coll body: (block (if_statement consequence: [(expression_statement (method_invocation object: (identifier) @obj name: (identifier) @m)) (block (expression_statement (method_invocation object: (identifier) @obj name: (identifier) @m)))]))) @match (#eq? @coll @obj) (#match? @m "^(remove|add|clear|addAll|removeAll)$"))',
     cls('for (String s : names) { if (s.isEmpty()) names.remove(s); }'), cls('names.removeIf(String::isEmpty);'),
     api("java/util/ConcurrentModificationException"), "if a thread modifies a collection directly while it is iterating over the collection with a fail-fast iterator, the iterator will throw this exception.",
     "Structurally modifying a collection inside a for-each over it throws ConcurrentModificationException; use removeIf, Iterator.remove(), or collect changes first.", "Javadoc: ConcurrentModificationException",
     cat="correctness")
conc("JAVA-CONC-SYNC-STRING-001", "Synchronizing on a String literal",
     '((synchronized_statement (parenthesized_expression (string_literal))) @match)',
     cls('synchronized ("lock") { counter++; }'), cls('synchronized (lock) { counter++; }'),
     "https://docs.oracle.com/javase/specs/jls/se25/html/jls-3.html", "are \"interned\" so as to share unique instances",
     "String literals are interned and shared JVM-wide; locking on one can contend or deadlock with unrelated code. Lock on a private final Object.", "JLS §3.10.5 String Literals", docv="JLS Java SE 25")
conc("JAVA-CONC-VT-SYNC-IO-001", "Blocking calls inside synchronized pin virtual threads on JDK 21-23",
     '((synchronized_statement body: (block (_ (method_invocation name: (identifier) @m)))) @match (#match? @m "^(sleep|read|readAllBytes|send|executeQuery|join|take|accept)$"))',
     cls('synchronized (this) { Thread.sleep(1000); }'), cls('lock.lock(); try { Thread.sleep(1000); } finally { lock.unlock(); }'),
     "https://openjdk.org/jeps/491", "Synchronize Virtual Threads without Pinning",
     "With virtual threads on JDK 21-23, blocking inside synchronized pins the carrier thread; JDK 24 (JEP 491) removes most pinning. Use ReentrantLock on older JDKs.", "JEP 491: Synchronize Virtual Threads without Pinning",
     sev="minor", mode="ai-confirm", applies={"java": ">=21 <24"}, ai="Does this code run on virtual threads, and does the call block (I/O, sleep, remote call)?", docv="JEP 491 (JDK 24)")
conc("JAVA-CONC-INTERRUPTED-001", "InterruptedException swallowed without restoring the interrupt status",
     '((catch_clause (catch_formal_parameter (catch_type (type_identifier) @t)) body: (block) @b) @match (#eq? @t "InterruptedException") (#not-match? @b "interrupt\\\\(|throw"))',
     cls('try { Thread.sleep(100); } catch (InterruptedException e) { log.warn("x"); }'),
     cls('try { Thread.sleep(100); } catch (InterruptedException e) { Thread.currentThread().interrupt(); return; }'),
     "https://docs.oracle.com/javase/tutorial/essential/concurrency/interrupt.html", "An interrupt is an indication to a thread that it should stop what it is doing and do something else.",
     "Catching InterruptedException without re-interrupting (Thread.currentThread().interrupt()) or rethrowing loses the cancellation request.", "The Java Tutorials: Interrupts",
     docv="Java Tutorials")
conc("JAVA-CONC-THREADLOCAL-REMOVE-001", "ThreadLocal set() without remove() leaks across pooled threads",
     '((method_invocation object: (identifier) @o name: (identifier) @m arguments: (argument_list . (_) .)) @match (#eq? @m "set") (#match? @o "(?i)(context|holder|local|tl)$"))',
     cls('CONTEXT.set(user); handle(req);'), cls('CONTEXT.set(user); try { handle(req); } finally { CONTEXT.remove(); }'),
     api("java/lang/ThreadLocal"), "Removes the current thread's value for this thread-local variable.",
     "A ThreadLocal value set on a pooled thread survives into the next task unless remove() is called (typically in finally).", "Javadoc: ThreadLocal.remove",
     sev="major", mode="ai-confirm", filters=["file.lacks_text:.remove()"], ai="Is the receiver a ThreadLocal used on pooled threads (servlet container, executor) and is remove() never called?", cat="resource-leak")

TWR = "https://docs.oracle.com/javase/tutorial/essential/exceptions/tryResourceClose.html"
for clsname in ["FileInputStream", "FileOutputStream", "FileReader", "FileWriter", "RandomAccessFile", "ZipFile", "JarFile", "Scanner", "PrintWriter", "Socket", "ServerSocket", "BufferedReader", "ObjectOutputStream"]:
    add(J(f"JAVA-RES-{clsname.upper()}-001", f"{clsname} opened outside try-with-resources", kind="anti-pattern", category="resource-leak", severity="major",
          query=new(clsname), filters=["node.not_in_try_with_resources", "node.lacks_ancestor:object_creation_expression|return_statement|field_declaration"], mode="ai-confirm",
          ai=f"Is this {clsname} closed on every path (try/finally, or returned/owned by a Closeable)? Answer rejected if it is.",
          bad=cls(f'var r = new {clsname}(arg); use(r);'), good=cls(f'try (var r = new {clsname}(arg)) {{ use(r); }}'),
          url=TWR, doc="The Java Tutorials: The try-with-resources Statement", doc_version="Java Tutorials (JDK 7+ language feature)",
          quote="The try -with-resources statement ensures that each resource is closed at the end of the statement.",
          message=f"{clsname} holds an OS resource; open it in try-with-resources so it is closed even when exceptions occur.", tags=["resource-leak"]))
for m in ["lines", "list", "walk", "find", "newDirectoryStream", "newBufferedReader", "newInputStream", "newOutputStream", "newBufferedWriter"]:
    stream = m in ("lines", "list", "walk", "find")
    add(J(f"JAVA-RES-FILES-{m.upper()}-001", f"Files.{m}() result must be closed (try-with-resources)", kind="anti-pattern", category="resource-leak", severity="major",
          query=static_call("Files", m), filters=["node.not_in_try_with_resources", "node.lacks_ancestor:return_statement"],
          mode="deterministic" if stream else "ai-confirm", ai=None if stream else f"Is the object returned by Files.{m}() closed on every path?",
          bad=cls(f'var s = Files.{m}(dir); consume(s);'), good=cls(f'try (var s = Files.{m}(dir)) {{ consume(s); }}'),
          url=api("java/nio/file/Files"), doc=f"Javadoc: Files.{m}", doc_version="JDK 25 API",
          quote="This method must be used within a try-with-resources statement or similar control structure to ensure that the stream's open" if stream else
          ("When not using the try-with-resources construct, then directory stream's close method should be invoked after iteration is completed" if m == "newDirectoryStream" else "A resource is an object that must be closed"),
          message=f"Files.{m}() keeps a file/directory handle open until it is closed; use try-with-resources.", tags=["resource-leak"]))
# newBufferedReader etc. quote is from the tutorial, fix url accordingly
for r in R:
    if r["id"] in ("JAVA-RES-FILES-NEWBUFFEREDREADER-001", "JAVA-RES-FILES-NEWINPUTSTREAM-001", "JAVA-RES-FILES-NEWOUTPUTSTREAM-001", "JAVA-RES-FILES-NEWBUFFEREDWRITER-001"):
        r["source"].update(url=TWR, doc="The Java Tutorials: The try-with-resources Statement", doc_version="Java Tutorials (JDK 7+ language feature)",
                           quote="A resource is an object that must be closed after the program is finished with it.")
add(J("JAVA-RES-JDBC-001", "JDBC Connection/Statement/ResultSet outside try-with-resources", kind="anti-pattern", category="resource-leak", severity="major",
      query='((method_invocation name: (identifier) @m) @match (#match? @m "^(getConnection|createStatement|prepareStatement|prepareCall)$"))',
      filters=["node.not_in_try_with_resources", "node.lacks_ancestor:return_statement"], mode="ai-confirm", ai="Is the JDBC resource closed on all paths (or managed by a framework such as JdbcTemplate)?",
      bad=cls('Connection c = ds.getConnection(); Statement s = c.createStatement();'), good=cls('try (Connection c = ds.getConnection(); Statement s = c.createStatement()) { s.execute(sql); }'),
      url=TWR, doc="The Java Tutorials: The try-with-resources Statement", doc_version="Java Tutorials (JDK 7+ language feature)",
      quote="A resource is an object that must be closed after the program is finished with it.",
      message="JDBC connections, statements and result sets must be closed; leaked connections exhaust the pool.", tags=["resource-leak"]))
add(J("JAVA-RES-HTTPCLIENT-001", "HttpClient created per call instead of shared / closed (AutoCloseable since 21)", kind="best-practice", category="resource-leak", severity="minor", applies={"java": ">=21"},
      query='((method_invocation object: (identifier) @c name: (identifier) @m) @match (#eq? @c "HttpClient") (#eq? @m "newHttpClient"))',
      filters=["node.not_in_try_with_resources", "node.lacks_ancestor:field_declaration"], mode="ai-confirm", ai="Is this HttpClient created per request (leaking its selector thread) instead of being shared or closed?",
      bad=cls('var resp = HttpClient.newHttpClient().send(req, BodyHandlers.ofString());'), good=cls('try (var client = HttpClient.newHttpClient()) { client.send(req, BodyHandlers.ofString()); }'),
      url="https://docs.oracle.com/en/java/javase/25/docs/api/java.net.http/java/net/http/HttpClient.html", doc="Javadoc: java.net.http.HttpClient", doc_version="JDK 25 API",
      quote="An HttpClient can be used to send requests and retrieve their responses",
      message="HttpClient owns threads and connections; create it once and share it, or close it (try-with-resources) on Java 21+.", tags=["resource-leak"]))


def corr(id, title, query, bad, good, url, quote, msg, doc, sev="major", mode="deterministic", ai=None, filters=None, kind="anti-pattern", cat="correctness", docv=None, applies=None):
    add(J(id, title, kind=kind, category=cat, severity=sev, query=query, bad=bad, good=good, url=url, doc=doc, applies=applies or {"java": ">=8"},
          doc_version=docv or "JDK 25 API", quote=quote, message=msg, mode=mode, ai=ai, filters=filters))


JLS15 = "https://docs.oracle.com/javase/specs/jls/se25/html/jls-15.html"
corr("JAVA-COR-EQUALS-HASHCODE-001", "equals() overridden without hashCode()",
     '((class_declaration body: (class_body (method_declaration name: (identifier) @n parameters: (formal_parameters . (formal_parameter type: (type_identifier) @t) .)))) @match (#eq? @n "equals") (#eq? @t "Object"))',
     "class P {\n  @Override public boolean equals(Object o) { return o instanceof P; }\n}\n",
     "class P {\n  @Override public boolean equals(Object o) { return o instanceof P; }\n  @Override public int hashCode() { return 1; }\n}\n",
     api("java/lang/Object"), "It is generally necessary to override the hashCode method whenever this method is overridden",
     "Overriding equals without hashCode breaks HashMap/HashSet: equal objects must have equal hash codes.", "Javadoc: Object.equals",
     filters=["node.lacks_descendant_text:hashCode()"])
corr("JAVA-COR-BIGDECIMAL-DOUBLE-001", "new BigDecimal(double) is unpredictable",
     '((object_creation_expression type: (type_identifier) @t arguments: (argument_list . (decimal_floating_point_literal) .)) @match (#eq? @t "BigDecimal"))',
     cls('BigDecimal price = new BigDecimal(0.1);'), cls('BigDecimal price = new BigDecimal("0.1");'),
     api("java/math/BigDecimal"), "The results of this constructor can be somewhat unpredictable.",
     "new BigDecimal(0.1) is 0.1000000000000000055511151231257827...; use the String constructor or BigDecimal.valueOf(double).", "Javadoc: BigDecimal(double)")
corr("JAVA-COR-BIGDECIMAL-EQUALS-001", "BigDecimal.equals considers scale (2.0 != 2.00)",
     '((method_invocation object: (method_invocation object: (identifier) @c name: (identifier) @v) name: (identifier) @m) @match (#eq? @c "BigDecimal") (#eq? @v "valueOf") (#eq? @m "equals"))',
     cls('if (BigDecimal.valueOf(2.0).equals(amount)) pay();'), cls('if (BigDecimal.valueOf(2.0).compareTo(amount) == 0) pay();'),
     api("java/math/BigDecimal"), "Unlike compareTo , this method considers two BigDecimal objects equal only if they are equal in value and scale.",
     "BigDecimal.equals compares value and scale; for numeric equality use compareTo(...) == 0.", "Javadoc: BigDecimal.equals", sev="minor")
corr("JAVA-COR-STRING-EQ-001", "String compared with == / != against a literal",
     '((binary_expression operator: ["==" "!="]) @match (#match? @match "\\"[^\\"]*\\"\\\\s*[=!]=|[=!]=\\\\s*\\""))',
     cls('if (status == "ACTIVE") start();'), cls('if ("ACTIVE".equals(status)) start();'),
     JLS15, "If the operands of an equality operator are both of either reference type or the null type, then the operation is object equality.",
     "== on Strings compares references, not contents; use equals() (literal first, or Objects.equals for null safety).", "JLS §15.21.3 Reference Equality Operators", docv="JLS Java SE 25")
corr("JAVA-COR-NAN-EQ-001", "Comparison with Double.NaN / Float.NaN is always false",
     '((binary_expression operator: ["==" "!="] (field_access object: (identifier) @c field: (identifier) @f)) @match (#match? @c "^(Double|Float)$") (#eq? @f "NaN"))',
     cls('if (x == Double.NaN) reset();'), cls('if (Double.isNaN(x)) reset();'),
     JLS15, "If either operand is NaN, then the result of == is false but the result of != is true .",
     "x == NaN is always false (and != always true); use Double.isNaN(x)/Float.isNaN(x).", "JLS §15.21.1 Numerical Equality Operators", docv="JLS Java SE 25", sev="critical")
corr("JAVA-COR-OPTIONAL-OF-NULL-001", "Optional.of(null) always throws",
     '((method_invocation object: (identifier) @c name: (identifier) @m arguments: (argument_list . (null_literal) .)) @match (#eq? @c "Optional") (#eq? @m "of"))',
     cls('return Optional.of(null);'), cls('return Optional.empty();'), api("java/util/Optional"), "Returns an Optional describing the given non- null value.",
     "Optional.of(null) throws NullPointerException; use Optional.empty() or Optional.ofNullable(x).", "Javadoc: Optional.of", sev="critical", cat="null-handling")
corr("JAVA-COR-OPTIONAL-NULL-RETURN-001", "Method returning Optional returns null",
     '((method_declaration type: (generic_type (type_identifier) @t) body: (block (return_statement (null_literal)))) @match (#eq? @t "Optional"))\n((method_declaration type: (generic_type (type_identifier) @t) body: (block (if_statement consequence: [(return_statement (null_literal)) (block (return_statement (null_literal)))]))) @match (#eq? @t "Optional"))',
     "class R {\n  Optional<User> find(String id) {\n    if (id == null) { return null; }\n    return Optional.of(load(id));\n  }\n}\n",
     "class R {\n  Optional<User> find(String id) {\n    if (id == null) { return Optional.empty(); }\n    return Optional.of(load(id));\n  }\n}\n",
     api("java/util/Optional"), "A variable whose type is Optional should never itself be null",
     "An Optional-returning method must never return null; return Optional.empty().", "Javadoc: Optional (API Note)", cat="null-handling")
corr("JAVA-COR-OPTIONAL-ISPRESENT-GET-001", "isPresent() followed by get(): use ifPresent / map / orElse",
     '((if_statement condition: (parenthesized_expression (method_invocation name: (identifier) @p)) consequence: (_) @c) @match (#eq? @p "isPresent") (#match? @c "\\\\.get\\\\(\\\\)"))',
     cls('if (user.isPresent()) { send(user.get()); }'), cls('user.ifPresent(this::send);'),
     api("java/util/Optional"), "If a value is present, performs the given action with the value, otherwise does nothing.",
     "The isPresent()/get() pair re-implements a null check; ifPresent, map, orElse(Get/Throw) express it without the unchecked get().", "Javadoc: Optional.ifPresent", sev="info", kind="best-practice", cat="null-handling")
corr("JAVA-COR-TOLOWER-LOCALE-001", "toLowerCase()/toUpperCase() without Locale on locale-insensitive data",
     '((method_invocation name: (identifier) @m arguments: (argument_list) @a) @match (#match? @m "^(toLowerCase|toUpperCase)$") (#eq? @a "()"))',
     cls('if (header.toLowerCase().equals("content-type")) handle();'), cls('if (header.toLowerCase(Locale.ROOT).equals("content-type")) handle();'),
     api("java/lang/String"), "To obtain correct results for locale insensitive strings, use toLowerCase(Locale.ROOT) .",
     "The no-arg overloads use the default locale (e.g. Turkish dotless i); for identifiers, protocol keywords and keys use Locale.ROOT.", "Javadoc: String.toLowerCase",
     sev="minor", mode="ai-confirm", ai="Is the string a machine identifier/keyword (header, enum name, key) rather than user-facing text?")
corr("JAVA-COR-GETBYTES-CHARSET-001", "String.getBytes() without an explicit charset",
     '((method_invocation name: (identifier) @m arguments: (argument_list) @a) @match (#eq? @m "getBytes") (#eq? @a "()"))',
     cls('byte[] b = payload.getBytes();'), cls('byte[] b = payload.getBytes(StandardCharsets.UTF_8);'),
     api("java/lang/String"), "Encodes this String into a sequence of bytes using the default charset",
     "getBytes() uses the default charset (UTF-8 since JDK 18, platform-specific before); be explicit for portable/wire formats.", "Javadoc: String.getBytes()",
     sev="minor", mode="ai-confirm", ai="Is the receiver a java.lang.String and are the bytes exchanged with another system or persisted?", kind="best-practice")
corr("JAVA-COR-ARRAYS-ASLIST-PRIM-001", "Arrays.asList on a primitive array creates a List of one array",
     '((method_invocation object: (identifier) @c name: (identifier) @m arguments: (argument_list . (array_creation_expression type: (integral_type)) .)) @match (#eq? @c "Arrays") (#eq? @m "asList"))',
     cls('List<?> l = Arrays.asList(new int[] {1, 2, 3});'), cls('List<Integer> l = List.of(1, 2, 3);'),
     api("java/util/Arrays"), "Returns a fixed-size list backed by the specified array.",
     "Arrays.asList(int[]) yields List<int[]> with a single element; use IntStream/boxed arrays or List.of.", "Javadoc: Arrays.asList")
corr("JAVA-COR-BOXED-EQ-001", "Reference comparison of boxed numbers with ==",
     '((binary_expression left: (method_invocation name: (identifier) @a) operator: ["==" "!="] right: (method_invocation name: (identifier) @b)) @match (#eq? @a "valueOf") (#eq? @b "valueOf"))',
     cls('if (Integer.valueOf(a) == Integer.valueOf(b)) same();'), cls('if (Integer.valueOf(a).equals(Integer.valueOf(b))) same();'),
     api("java/lang/Integer"), "This method will always cache values in the range -128 to 127, inclusive, and may cache other values outside of this range.",
     "== on boxed Integers only works by accident inside the -128..127 cache; compare with equals() or unbox.", "Javadoc: Integer.valueOf")
corr("JAVA-COR-PARSEINT-001", "Integer.parseInt / Long.parseLong on unchecked external input",
     '((method_invocation object: (identifier) @c name: (identifier) @m arguments: (argument_list . (method_invocation name: (identifier) @src) .)) @match (#match? @c "^(Integer|Long)$") (#match? @m "^parse(Int|Long)$") (#match? @src "^(getenv|getProperty|getParameter|getHeader)$"))',
     cls('int port = Integer.parseInt(System.getenv("PORT"));'), cls('int port = parsePortOrDefault(System.getenv("PORT"), 8080);'),
     api("java/lang/Integer"), "NumberFormatException - if the string does not contain a parsable integer.",
     "parseInt/parseLong throw NumberFormatException for missing or malformed input; handle invalid environment/request values explicitly.", "Javadoc: Integer.parseInt",
     sev="minor", mode="ai-confirm", filters=["node.lacks_ancestor:try_statement"], cat="null-handling", ai="Can the parsed string be null or malformed with no surrounding handling?")
corr("JAVA-COR-REQUIRENONNULL-001", "Use Objects.requireNonNull for parameter null checks",
     '((if_statement condition: (parenthesized_expression (binary_expression operator: "==" right: (null_literal))) consequence: [(throw_statement (object_creation_expression type: (type_identifier) @t)) (block . (throw_statement (object_creation_expression type: (type_identifier) @t)) .)]) @match (#eq? @t "NullPointerException"))',
     cls('if (name == null) throw new NullPointerException("name");'), cls('this.name = Objects.requireNonNull(name, "name");'),
     api("java/util/Objects"), "This method is designed primarily for doing parameter validation in methods and constructors",
     "Objects.requireNonNull(x, \"msg\") is the idiomatic, shorter null check for parameters.", "Javadoc: Objects.requireNonNull", sev="info", kind="modernization", cat="null-handling")
corr("JAVA-COR-REQUIRENONNULLELSE-001", "Use Objects.requireNonNullElse instead of a null-check ternary",
     '((ternary_expression condition: (binary_expression left: (identifier) @a operator: "!=" right: (null_literal)) consequence: (identifier) @b) @match (#eq? @a @b))',
     cls('String n = name != null ? name : "anonymous";'), cls('String n = Objects.requireNonNullElse(name, "anonymous");'),
     api("java/util/Objects"), "Returns the first argument if it is non- null and otherwise the second argument if it is non- null",
     "x != null ? x : fallback can be written as Objects.requireNonNullElse(x, fallback) (Java 9).", "Javadoc: Objects.requireNonNullElse", sev="info", kind="modernization", cat="null-handling", applies={"java": ">=9"})
corr("JAVA-COR-RECORD-ARRAY-001", "Record component of array type has reference equality semantics",
     '((record_declaration parameters: (formal_parameters (formal_parameter type: (array_type)))) @match)',
     "record Packet(byte[] payload) {}\n", "record Packet(List<Byte> payload) {}\n",
     "https://docs.oracle.com/javase/specs/jls/se25/html/jls-8.html", "an implicitly declared equals method",
     "Record equals/hashCode compare array components by reference; two records with equal array contents are not equal. Override equals/hashCode or use a List.", "JLS §8.10.3 Record Members", docv="JLS Java SE 25", sev="minor", mode="ai-confirm",
     ai="Is the record compared with equals/hashCode or used as a map key/set element while holding an array?", applies={"java": ">=16"})
corr("JAVA-COR-LIST-OF-NULL-001", "List.of / Set.of / Map.of reject null elements",
     '((method_invocation object: (identifier) @c name: (identifier) @m arguments: (argument_list (null_literal))) @match (#match? @c "^(List|Set|Map)$") (#eq? @m "of"))',
     cls('var l = List.of("a", null);'), cls('var l = Arrays.asList("a", null);'),
     api("java/util/List"), "They disallow null elements. Attempts to create them with null elements result in NullPointerException .",
     "Unmodifiable collection factories throw NullPointerException for null elements.", "Javadoc: List (Unmodifiable Lists)", sev="critical", cat="null-handling", applies={"java": ">=9"})
corr("JAVA-COR-COLLECTIONS-EMPTY-001", "Prefer List.of()/Collections.emptyList() over raw EMPTY_LIST constants",
     field("Collections", "^EMPTY_(LIST|SET|MAP)$"), cls('List<String> l = Collections.EMPTY_LIST;'), cls('List<String> l = Collections.emptyList();'),
     api("java/util/Collections"), "Unlike this method, the field does not provide type safety.",
     "Collections.EMPTY_LIST/SET/MAP are raw types (unchecked warnings); use emptyList()/emptySet()/emptyMap() or List.of().", "Javadoc: Collections.emptyList", sev="info", kind="best-practice")
corr("JAVA-COR-THREAD-SLEEP-LOOP-001", "Busy-wait with Thread.sleep in a loop",
     '((while_statement body: (block (_ (method_invocation object: (identifier) @c name: (identifier) @m)))) @match (#eq? @c "Thread") (#eq? @m "sleep"))',
     cls('while (!done) { Thread.sleep(50); }'), cls('latch.await();'),
     "https://docs.oracle.com/javase/tutorial/essential/concurrency/guardmeth.html", "A more efficient guard invokes Object.wait to suspend the current thread.",
     "Polling a flag with sleep wastes CPU and adds latency; wait on a condition (CountDownLatch, CompletableFuture, BlockingQueue, wait/notify).", "The Java Tutorials: Guarded Blocks",
     docv="Java Tutorials", sev="minor", mode="ai-confirm", ai="Is the loop polling a condition another thread sets (rather than a deliberate rate-limited retry/backoff)?", cat="concurrency")
corr("JAVA-COR-ENUM-ORDINAL-001", "Persisting or comparing Enum.ordinal() is fragile",
     '((method_invocation name: (identifier) @m arguments: (argument_list) @a) @match (#eq? @m "ordinal") (#eq? @a "()"))',
     cls('stmt.setInt(1, status.ordinal());'), cls('stmt.setString(1, status.name());'),
     api("java/lang/Enum"), "Most programmers will have no use for this method.",
     "ordinal() changes when constants are reordered; persist/compare name() or an explicit code instead (EnumMap/EnumSet are fine).", "Javadoc: Enum.ordinal", sev="minor", mode="ai-confirm",
     ai="Is the ordinal stored, transmitted or used for business logic (rather than EnumMap-style internal indexing)?")


# ------------------------------------------------------------------ Sonar-way checklist gaps (own detection/wording)
from specs._common import autoquote as _aq
from specs._java import JDK25
JNDI = "https://docs.oracle.com/javase/tutorial/jndi/ldap/auth_mechs.html"
SPRSESS = "https://docs.spring.io/spring-security/reference/servlet/authentication/session-management.html"
SPRDBG = "https://docs.spring.io/spring-security/site/docs/current/api/org/springframework/security/config/annotation/web/configuration/EnableWebSecurity.html"
H5 = "https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html"
OSECRETS = "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html"
AWV = "https://developer.android.com/reference/android/webkit/WebView"


def gap(id, title, query, bad, good, url, needle, msg, doc, xref, sev="major", mode="deterministic", ai=None, docv="current", fp=None, files=None):
    r = J(id, title, kind="security", category="security", severity=sev, query=query, bad=bad, good=good, url=url, doc=doc, doc_version=docv,
          quote=_aq(url, needle), message=msg, mode=mode, ai=ai, tags=["security"], xref=xref, fp=fp, files=files)
    add(r)


gap("JAVA-SEC-LDAP-ANON-001", "LDAP context configured for anonymous access",
    '((method_invocation name: (identifier) @m arguments: (argument_list . (field_access field: (identifier) @f) . (string_literal) @v .)) @match (#eq? @m "put") (#eq? @f "SECURITY_AUTHENTICATION") (#match? @v "^\\"none\\"$"))',
    cls('env.put(Context.SECURITY_AUTHENTICATION, "none");', "import javax.naming.Context;\n"),
    cls('env.put(Context.SECURITY_AUTHENTICATION, "simple");\n    env.put(Context.SECURITY_PRINCIPAL, dn);', "import javax.naming.Context;\n"),
    JNDI, "Use no authentication (anonymous)",
    "The directory connection is set to anonymous binding, so the server cannot tie queries to an identity. Authenticate the bind (and protect it with TLS).",
    "JNDI tutorial: LDAP authentication mechanisms", ["sonar:java:S4433"], docv="Java SE tutorial")
gap("JAVA-SEC-POSIX-WORLD-WRITABLE-001", "File permissions grant write access to others",
    '((method_invocation object: (identifier) @c name: (identifier) @m arguments: (argument_list . (string_literal) @match .)) (#eq? @c "PosixFilePermissions") (#eq? @m "fromString") (#match? @match "^\\"[-r][-w][-x][-r][-w][-x][-r]w[-x]\\"$"))\n'
    '((method_invocation name: (identifier) @m arguments: (argument_list . (field_access object: (identifier) @o field: (identifier) @match) .)) (#eq? @m "add") (#eq? @o "PosixFilePermission") (#eq? @match "OTHERS_WRITE"))',
    cls('Files.setPosixFilePermissions(path, PosixFilePermissions.fromString("rwxrwxrwx"));'),
    cls('Files.setPosixFilePermissions(path, PosixFilePermissions.fromString("rwxr-x---"));'),
    api("java/nio/file/attribute/PosixFilePermissions"), "others have none",
    "Every local user can modify this file. Drop the write bit for others (and usually group) unless the file is meant to be shared.",
    "Javadoc: PosixFilePermissions", ["sonar:java:S2612"], docv=JDK25,
    fp=[cls('perms.remove(PosixFilePermission.OTHERS_WRITE);')])
gap("JAVA-SEC-SESSION-FIXATION-NONE-001", "Session fixation protection turned off",
    '((method_invocation object: (_) @o name: (identifier) @m) @match (#eq? @m "none") (#match? @o "sessionFixation\\\\(\\\\)$"))\n'
    '((method_invocation name: (identifier) @sf arguments: (argument_list (lambda_expression body: (method_invocation name: (identifier) @m)))) @match (#eq? @sf "sessionFixation") (#eq? @m "none"))',
    cls('http.sessionManagement(s -> s.sessionFixation(f -> f.none()));'),
    cls('http.sessionManagement(s -> s.sessionFixation(f -> f.changeSessionId()));'),
    SPRSESS, "Session fixation attacks are a potential risk",
    "With session fixation protection disabled, the session id chosen before login survives authentication. Keep changeSessionId() (the default) or newSession().",
    "Spring Security: Session Management", ["sonar:java:S5876"], docv="Spring Security 6.x/7.x")
gap("JAVA-SEC-SPRING-SECURITY-DEBUG-001", "Spring Security debug mode enabled",
    '((annotation name: (identifier) @n arguments: (annotation_argument_list (element_value_pair key: (identifier) @k value: (true)))) @match (#eq? @n "EnableWebSecurity") (#eq? @k "debug"))',
    "@EnableWebSecurity(debug = true)\nclass SecurityConfig {}\n", "@EnableWebSecurity\nclass SecurityConfig {}\n",
    SPRDBG, "Controls debugging support for Spring Security",
    "Spring Security debug mode logs request details including sensitive headers and session data. Keep it off outside local debugging.",
    "Spring Security API: @EnableWebSecurity", ["sonar:java:S4507"], docv="Spring Security 6.x/7.x")
gap("JAVA-SEC-CORS-WILDCARD-001", "Access-Control-Allow-Origin: * set by hand",
    '((method_invocation name: (identifier) @m arguments: (argument_list . (string_literal) @k . (string_literal) @v .)) @match (#match? @m "^(setHeader|addHeader)$") (#match? @k "(?i)^\\"access-control-allow-origin\\"$") (#eq? @v "\\"*\\""))',
    cls('response.setHeader("Access-Control-Allow-Origin", "*");'),
    cls('response.setHeader("Access-Control-Allow-Origin", "https://app.example.com");'),
    H5, "Allow only selected, trusted domains",
    "Any origin may read this response from a browser. Use an allow-list of origins unless the endpoint is deliberately public and carries nothing user-specific.",
    "OWASP HTML5 Security Cheat Sheet", ["sonar:java:S5122"], mode="ai-confirm",
    ai="Is this endpoint serving user-specific or non-public data (so a wildcard origin is a real exposure), rather than a deliberately public API/static asset?")
gap("JAVA-SEC-HARDCODED-PASSWORD-001", "Hard-coded password or secret in a variable",
    '((variable_declarator name: (identifier) @n value: (string_literal) @match) (#match? @n "(?i)^(password|passwd|pwd|secret|clientSecret|apiKey|apiSecret|accessToken|authToken|privateKey|secretKey|dbPassword)$") (#not-match? @match "^\\"(\\"|\\\\$\\\\{|<|%|changeme|xxx|example|test|dummy|\\\\*)"))',
    cls('String password = "S3cr3t-Passw0rd";'), cls('String password = System.getenv("DB_PASSWORD");'),
    OSECRETS, "Many organizations have them hardcoded within the source code in plaintext",
    "A credential is embedded in source. Load it from the environment or a secret manager and rotate the leaked value.",
    "OWASP Secrets Management Cheat Sheet", ["sonar:java:S2068", "sonar:java:S6437"], sev="critical", mode="ai-confirm",
    ai="Is this a real credential (not a test fixture, placeholder, property key name, or example value)?",
    fp=[cls('String password = "";'), cls('String password = "${DB_PASSWORD}";')],
    files=["**/*.java", "!**/src/test/**", "!**/src/it/**", "!**/*Test.java", "!**/*Tests.java", "!**/*IT.java"])
gap("JAVA-SEC-WEBVIEW-DEBUG-001", "WebView remote debugging enabled",
    '((method_invocation object: (identifier) @c name: (identifier) @m arguments: (argument_list . (true) .)) @match (#eq? @c "WebView") (#eq? @m "setWebContentsDebuggingEnabled"))',
    cls("WebView.setWebContentsDebuggingEnabled(true);"), cls("WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG);"),
    AWV, "Enables debugging of web contents (HTML / CSS / JavaScript) loaded into any WebViews of this application",
    "Remote debugging exposes every WebView's DOM, storage and JavaScript to anyone with USB/adb access. Enable it only in debug builds (pass BuildConfig.DEBUG).",
    "Android API: WebView", ["sonar:java:S4507"], mode="ai-confirm",
    ai="Is this call reachable in release builds (not wrapped in a BuildConfig.DEBUG / debuggable check)?", docv="Android API 36")

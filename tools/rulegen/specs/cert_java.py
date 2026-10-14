"""Rules that originate in the SEI CERT Oracle Coding Standard for Java (written for Java SE 6/7) and are
decidable from syntax. Each was re-verified against current Java (JDK 25 API docs, JLS/JVMS SE 25, JEPs):
the cited source is now the current official Oracle/OpenJDK page; the CERT page is kept as an xref only.
Audit and per-rule verdicts: tools/gap/source-currency.md."""
from specs._common import Pack

P = Pack("CERT-JAVA", "java", "JDK 25 API / JLS SE 25 (SEI CERT Java as xref)", {"java": ">=8"}, files=["**/*.java"])
W = "https://wiki.sei.cmu.edu/confluence/display/java/"
API = "https://docs.oracle.com/en/java/javase/25/docs/api/java.base/"
SPEC = "https://docs.oracle.com/javase/specs/"
C = lambda body, imports="": f"{imports}class A {{\n{body}}}\n"


def cert(id, title, page, src, query, bad, good, msg, sev="minor", kind="anti-pattern", cat="correctness", xref=(), **kw):
    """page: the CERT wiki page (xref only). src: (current official url, needle on that page)."""
    url, needle = src
    r = P(id, title, url, needle, query, bad, good, msg, sev=sev, kind=kind, cat=cat, xref=[W + page, *xref], **kw)
    r["detection"]["exclude_tests"] = True
    return r


cert("FIO02-FILE-RESULT-IGNORED", "File.delete/mkdir/renameTo result ignored (FIO02-J)", "FIO02-J.+Detect+and+handle+file-related+errors",
     (API + "java/io/File.html", "true if and only if the file or directory is successfully deleted"),
     r"""((expression_statement (method_invocation object: (_) name: (identifier) @m arguments: (argument_list) @a) @match) (#match? @m "^(delete|mkdir|mkdirs|createNewFile|setReadOnly|setLastModified|setExecutable|setReadable|setWritable|renameTo)$"))""",
     C("  void clean(File f) {\n    f.delete();\n  }\n", "import java.io.File;\n\n"),
     C("  void clean(File f) throws java.io.IOException {\n    java.nio.file.Files.delete(f.toPath());\n  }\n", "import java.io.File;\n\n"),
     "java.io.File reports failure only through the boolean result, which is dropped here, so a file that was not deleted/created/renamed goes unnoticed. Check the result, or use java.nio.file.Files, which throws an IOException with the reason.",
     filters=["file.has_re:import java\\.io\\.(File|\\*);", "node.lacks_re:^(this\\.)?\\w*(repo|repository|dao|service|client|cache|map|session|em|entityManager|template)\\w*\\.", "node.lacks_re:\\(\\s*[^)\\s]"],
     cwe=["CWE-252"], xref=[API + "java/nio/file/Files.html#delete(java.nio.file.Path)"], fp=[C("  void d(Repo repository, User u) {\n    repository.delete(u);\n  }\n", "import java.io.File;\n\n")])
cert("LCK02-SYNC-GETCLASS", "synchronized (getClass()) (LCK02-J)", "LCK02-J.+Do+not+synchronize+on+the+class+object+returned+by+getClass%28%29",
     (API + "java/lang/Object.html", "The Class object that represents the runtime class of this object"),
     r"""((synchronized_statement (parenthesized_expression (method_invocation name: (identifier) @m arguments: (argument_list) .))) @match (#eq? @m "getClass"))""",
     C("  static int count;\n  void inc() {\n    synchronized (getClass()) {\n      count++;\n    }\n  }\n"),
     C("  static int count;\n  void inc() {\n    synchronized (A.class) {\n      count++;\n    }\n  }\n"),
     "In a subclass getClass() returns the subclass's Class object, so subclass and parent instances take different locks and the static state is no longer protected. Lock on A.class or a private static final lock object.",
     sev="major", cat="concurrency", cwe=["CWE-667"])
cert("LCK01-SYNC-SHARED-LITERAL", "synchronized on a string literal or boxed constant (LCK01-J)", "LCK01-J.+Do+not+synchronize+on+objects+that+may+be+reused",
     ("https://openjdk.org/jeps/390", "Provide warnings about improper attempts to synchronize on instances of any value-based classes"),
     r"""[((synchronized_statement (parenthesized_expression [(string_literal) (method_invocation object: (identifier) @o name: (identifier) @m)])) @match (#match? @o "^(Boolean|Integer|Long|Short|Byte|Character|String)$") (#match? @m "^(valueOf|intern)$"))
         ((synchronized_statement (parenthesized_expression (string_literal))) @match)
         ((synchronized_statement (parenthesized_expression (field_access field: (identifier) @f))) @match (#match? @f "^(TRUE|FALSE)$"))]""",
     C("  void run() {\n    synchronized (\"lock\") {\n      work();\n    }\n  }\n  void work() {}\n"),
     C("  private final Object lock = new Object();\n  void run() {\n    synchronized (lock) {\n      work();\n    }\n  }\n  void work() {}\n"),
     "String literals and cached boxed values are shared across the whole JVM, so unrelated code (or a library) can take the same lock and deadlock or slow you down. Lock on a private final Object.",
     sev="major", cat="concurrency", cwe=["CWE-412"],
     xref=[API + "java/lang/doc-files/ValueBased.html", SPEC + "jls/se25/html/jls-3.html#jls-3.10.5"])
cert("THI02-NOTIFY", "notify() instead of notifyAll() (THI02-J)", "THI02-J.+Notify+all+waiting+threads+rather+than+a+single+thread",
     (API + "java/lang/Object.html", "The choice is arbitrary and occurs at the discretion of the implementation"),
     r"""((method_invocation name: (identifier) @m arguments: (argument_list) .) @match (#eq? @m "notify"))""",
     C("  boolean ready;\n  synchronized void done() {\n    ready = true;\n    notify();\n  }\n"),
     C("  boolean ready;\n  synchronized void done() {\n    ready = true;\n    notifyAll();\n  }\n"),
     "notify() wakes one arbitrary waiter; if it is waiting for a different condition it goes back to sleep and the thread that could proceed is never woken. Use notifyAll() (or java.util.concurrent conditions).",
     cat="concurrency", mode="ai-confirm", ai="Can more than one thread wait on this monitor for different conditions (so waking a single arbitrary one may wake the wrong one)?",
     cwe=["CWE-662"])
cert("OBJ09-CLASS-NAME-COMPARE", "Classes compared by name (OBJ09-J)", "OBJ09-J.+Compare+classes+and+not+class+names",
     (SPEC + "jvms/se25/html/jvms-5.html", "is the defining loader of C"),
     r"""((method_invocation object: (method_invocation object: (method_invocation name: (identifier) @g) name: (identifier) @n) name: (identifier) @e) @match (#eq? @g "getClass") (#match? @n "^(getName|getSimpleName)$") (#match? @e "^(equals|equalsIgnoreCase)$"))""",
     C("  boolean trusted(Object o) {\n    return o.getClass().getName().equals(\"com.example.Auth\");\n  }\n"),
     C("  boolean trusted(Object o) {\n    return o.getClass() == com.example.Auth.class;\n  }\n"),
     "A class with the same name can come from another package or class loader (including attacker-supplied code), so a name check is not an identity check. Compare Class objects or use instanceof.",
     kind="security", cat="security", sev="minor", cwe=["CWE-486"])
cert("ERR09-SYSTEM-EXIT", "System.exit() outside main (ERR09-J)", "ERR09-J.+Do+not+allow+untrusted+code+to+terminate+the+JVM",
     (API + "java/lang/Runtime.html", "Initiates the shutdown sequence of the Java Virtual Machine"),
     r"""((method_invocation object: (identifier) @o name: (identifier) @m) @match (#match? @o "^(System|Runtime)$") (#match? @m "^(exit|halt)$"))""",
     C("  void handle(String cmd) {\n    if (cmd.equals(\"stop\")) {\n      System.exit(0);\n    }\n  }\n"),
     C("  void handle(String cmd) {\n    if (cmd.equals(\"stop\")) {\n      throw new IllegalStateException(\"stop requested\");\n    }\n  }\n"),
     "Library or server code that calls System.exit() kills the whole JVM, including every other request, thread and application in it. Throw an exception or return a status and let main() decide.",
     cat="reliability", mode="ai-confirm", ai="Is this server, library or framework code (not a command-line entry point or its direct helpers)?",
     filters=["func.lacks_re:static\\s+void\\s+main\\s*\\("], cwe=["CWE-382"],
     # CERT's remedy (a SecurityManager vetoing checkExit) is gone: JEP 486 permanently disabled it in JDK 24.
     xref=["https://openjdk.org/jeps/486"])
cert("NUM09-FLOAT-LOOP-COUNTER", "Floating-point loop counter (NUM09-J)", "NUM09-J.+Do+not+use+floating-point+variables+as+loop+counters",
     (SPEC + "jls/se25/html/jls-4.html", "inexact"),
     r"""((for_statement init: (local_variable_declaration type: (floating_point_type))) @match)""",
     C("  void steps() {\n    for (float x = 0.1f; x <= 1.0f; x += 0.1f) {\n      System.out.println(x);\n    }\n  }\n"),
     C("  void steps() {\n    for (int i = 1; i <= 10; i++) {\n      float x = i / 10.0f;\n      System.out.println(x);\n    }\n  }\n"),
     "0.1 has no exact binary representation, so the counter drifts and the loop runs one time more or less than intended (or forever). Count with an integer and derive the float value.",
     cwe=["CWE-1339"])
cert("FIO03-TEMP-FILE-NOT-REMOVED", "Temporary file created without being removed (FIO03-J)", "FIO03-J.+Remove+temporary+files+before+termination",
     (API + "java/io/File.html", "To arrange for a file created by this method to be deleted automatically, use the deleteOnExit() method"),
     r"""((method_invocation object: (identifier) @o name: (identifier) @m) @match (#match? @o "^(File|Files)$") (#match? @m "^(createTempFile)$"))""",
     C("  File export(byte[] data) throws Exception {\n    File f = File.createTempFile(\"export\", \".csv\");\n    java.nio.file.Files.write(f.toPath(), data);\n    return f;\n  }\n", "import java.io.File;\n\n"),
     C("  void export(byte[] data) throws Exception {\n    java.nio.file.Path p = java.nio.file.Files.createTempFile(\"export\", \".csv\");\n    try {\n      java.nio.file.Files.write(p, data);\n    } finally {\n      java.nio.file.Files.deleteIfExists(p);\n    }\n  }\n", "import java.io.File;\n\n"),
     "The temporary file is never deleted on this path, so data (possibly sensitive) accumulates in a shared directory. Delete it in a finally block (Files.deleteIfExists) or open it with DELETE_ON_CLOSE.",
     kind="security", cat="security", mode="ai-confirm", ai="Is the temporary file left behind on some path (not deleted by the caller or a finally block elsewhere)?",
     filters=["func.lacks_re:\\.delete\\(|deleteIfExists|deleteOnExit|DELETE_ON_CLOSE"], cwe=["CWE-459", "CWE-377"],
     xref=[API + "java/nio/file/StandardOpenOption.html#DELETE_ON_CLOSE"])

RULES = P.R

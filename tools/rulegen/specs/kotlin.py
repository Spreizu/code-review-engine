"""Kotlin pack: kotlinlang.org compatibility guides / What's New (1.4 -> 2.4) for stdlib and Gradle-plugin deprecations,
coroutines guide, null-safety and coding conventions, plus JVM security basics. Version dimension `kotlin` comes from
the Kotlin Gradle plugin version (plugins { kotlin("jvm") version ... } / kotlin_version)."""
from specs._common import Pack, secret_rules, PLACEHOLDER_RE

K = "https://kotlinlang.org/docs/"
CO = "https://kotlinlang.org/api/kotlinx.coroutines/kotlinx-coroutines-core/kotlinx.coroutines/"
P = Pack("KT", "kotlin", "Kotlin 2.4", {"kotlin": "*"})
KTS = ["**/*.gradle.kts"]
SRC = ["**/*.kt", "**/*.kts", "!**/*.gradle.kts"]


def meth(names_re, cap="@match"):
    """receiver.name(...) call."""
    return f'((call_expression (navigation_expression (_) (identifier) {cap})) (#match? {cap} "^({names_re})$"))'


def fcall(names_re):
    return f'((call_expression . (identifier) @match) (#match? @match "^({names_re})$"))'


def qual(recv_re, names_re):
    return (f'((call_expression (navigation_expression . (identifier) @r . (identifier) @match)) (#match? @r "^({recv_re})$") '
            f'(#match? @match "^({names_re})$"))')


def dep(id, title, ver, page, needle, query, bad, good, msg, sev="minor", kind="deprecation", **kw):
    P(id, title, K + page, needle, query, bad, good, msg, sev=sev, kind=kind, cat=kind if kind != "modernization" else "modernization",
      applies=kw.pop("applies", None) or {"kotlin": f">={ver}"}, docv=f"Kotlin {ver}", **kw)


# ------------------------------------------------------------------ stdlib deprecations
dep("CASE-CONVERSION", "toUpperCase()/toLowerCase()/capitalize()/decapitalize()", "1.5", "compatibility-guide-15.html", "toUpperCase() will be deprecated",
    meth("toUpperCase|toLowerCase|capitalize|decapitalize"), 'val s = name.toUpperCase()\n', 'val s = name.uppercase()\n',
    "Locale-sensitive case conversion is deprecated; use uppercase()/lowercase()/replaceFirstChar { it.titlecase() }.", sev="major")
dep("CHAR-TO-INT", "Char.toInt() and number-to-Char conversions", "1.5", "compatibility-guide-15.html", "toInt()/toShort()/toLong()/toByte()/toDouble()/toFloat()",
    '((call_expression (navigation_expression (_) @c (identifier) @match)) (#eq? @match "toInt") (#match? @c "^\'.*\'$|(?i)char"))',
    "val code = 'a'.toInt()\n", "val code = 'a'.code\n", "Char.toInt() is deprecated; use Char.code / digitToInt() / Char(code).")
dep("APPENDLN", "appendln()", "1.4", "compatibility-guide-14.html", "appendln() will be deprecated in favor of StringBuilder.appendLine()",
    meth("appendln"), 'sb.appendln("x")\n', 'sb.appendLine("x")\n', "Use appendLine(); appendln is deprecated.")
dep("MAX-MIN-NULLABLE", "max()/min()/maxBy{} on collections (pre-1.7 semantics)", "1.4", "whatsnew14.html", "maxOrNull()",
    meth("maxBy|minBy|maxWith|minWith"), "val m = xs.maxBy { it.size }\n", "val m = xs.maxByOrNull { it.size }\n",
    "1.4 renamed the nullable variants to *OrNull; 1.7 reintroduced max()/maxBy() as non-null (throwing). Pick the semantics explicitly.",
    applies={"kotlin": ">=1.4 <1.7"})
dep("SUMBY", "sumBy{}/sumByDouble{}", "1.4", "whatsnew14.html", "sumOf() takes a selector function and returns a sum of its values", meth("sumBy|sumByDouble"), "val t = xs.sumBy { it.n }\n", "val t = xs.sumOf { it.n }\n",
    "Use sumOf {}.")
dep("READLINE", "readLine()!!", "1.6", "whatsnew16.html", "readln() and readlnOrNull()",
    '((unary_expression argument: (call_expression (identifier) @match)) (#eq? @match "readLine"))', "val s = readLine()!!\n", "val s = readln()\n",
    "Use readln() / readlnOrNull() (1.6+).", kind="modernization")
dep("ENUM-VALUES", "Enum.values()", "1.9", "whatsnew19.html", "The entries property is a modern and performant replacement",
    '((call_expression (navigation_expression (identifier) @t (identifier) @match) (value_arguments) @a) (#eq? @match "values") (#eq? @a "()") (#match? @t "^[A-Z]"))',
    "for (c in Color.values()) println(c)\n", "for (c in Color.entries) println(c)\n", "entries (1.9+) returns a pre-allocated immutable list.", kind="modernization")
dep("RANGE-UNTIL", "0..n - 1 / until", "1.9", "whatsnew19.html", "operator for open-ended ranges",
    '((range_expression (_) (binary_expression right: (number_literal) @one) @match) (#eq? @one "1") (#match? @match "-\\\\s*1$"))', "for (i in 0..list.size - 1) {}\n",
    "for (i in list.indices) {}\n", "Use indices, ..< (1.9+) or until.", kind="modernization", sev="info")
dep("DATA-OBJECT", "object overriding toString() for its name", "1.9", "whatsnew19.html", "Data object declarations, which were introduced in Kotlin 1.8.20 , are now Stable.",
    '((object_declaration (class_body (function_declaration name: (identifier) @match))) (#eq? @match "toString"))', 'object Empty {\n    override fun toString() = "Empty"\n}\n',
    "data object Empty\n", "data object (1.9+) generates toString/equals/hashCode.", kind="modernization", sev="info", mode="ai-confirm",
    ai="Does this object's toString() just return its name (so `data object` is equivalent)?")
dep("DURATION-FACTORY", "Duration.seconds(x)/Duration.milliseconds(x)", "1.6", "whatsnew15.html", "Old extension properties like Int.seconds are now deprecated.",
    qual("Duration", "nanoseconds|microseconds|milliseconds|seconds|minutes|hours|days"), "val d = Duration.seconds(5)\n", "val d = 5.seconds\n",
    "Since 1.6 the Duration.Companion extensions (5.seconds) are the stable API; the Duration.seconds(x) functions are deprecated.")
dep("CONTEXT-RECEIVERS", "context receivers context(T)", "2.2", "whatsnew22.html", "To migrate from context receivers to context parameters",
    '((call_expression (identifier) @match (value_arguments (value_argument (identifier)))) (#eq? @match "context"))',
    "context(Logger)\nfun log() {}\n", "context(logger: Logger)\nfun log() {}\n", "Context receivers are replaced by context parameters (2.2); migrate to named context(name: T).",
    sev="major", filters=[r"file.has_re:(?m)^\s*context\([A-Z]\w*(,\s*[A-Z]\w*)*\)\s*$"])
dep("ANDROID-SYNTHETICS", "kotlinx.android.synthetic imports", "1.8", "compatibility-guide-18.html", "synthetic property",
    '((import) @match (#match? @match "kotlinx\\\\.android\\\\.synthetic"))', "import kotlinx.android.synthetic.main.activity_main.*\n",
    "import com.example.databinding.ActivityMainBinding\n", "Kotlin Android Extensions (synthetics) are gone; use View Binding.", sev="critical", kind="removal")

# ------------------------------------------------------------------ Kotlin Gradle plugin (Kotlin DSL build scripts)
dep("GRADLE-KOTLINOPTIONS", "kotlinOptions {} block", "2.0", "gradle-compiler-options.html", "Since the kotlinOptions {} block is deprecated from Kotlin 2.0.0",
    '((call_expression (identifier) @match (annotated_lambda)) (#eq? @match "kotlinOptions"))', 'tasks.withType<KotlinCompile> {\n    kotlinOptions {\n        jvmTarget = "17"\n    }\n}\n',
    'kotlin {\n    compilerOptions {\n        jvmTarget.set(JvmTarget.JVM_17)\n    }\n}\n', "kotlinOptions is deprecated (2.0) and an error since 2.2; use compilerOptions {}.",
    sev="major", files=KTS)
dep("GRADLE-KOTLINOPTIONS-22", "kotlinOptions DSL removed path", "2.2", "compatibility-guide-22.html", "The ability to configure compiler options through the kotlinOptions DSL",
    '((navigation_expression (_) (identifier) @match) (#eq? @match "kotlinOptions"))', 'android.kotlinOptions.jvmTarget = "17"\n',
    'kotlin.compilerOptions.jvmTarget.set(JvmTarget.JVM_17)\n', "kotlinOptions property access is deprecated with error in 2.2.", sev="major", files=KTS)
dep("GRADLE-LANGUAGE-VERSION-OLD", "languageVersion/apiVersion set to an old version", "2.1", "compatibility-guide-21.html", "Language versions 1.6 and 1.7 are deprecated.",
    '((assignment left: (_) @l right: (string_literal (string_content) @match)) (#match? @l "(languageVersion|apiVersion)$") (#match? @match "^1\\\\.[0-9]$"))',
    'kotlinOptions {\n    languageVersion = "1.7"\n}\n', 'compilerOptions {\n    languageVersion.set(KotlinVersion.KOTLIN_2_1)\n}\n',
    "Language versions 1.4/1.5 are unsupported and 1.6-1.9 deprecated or erroring in 2.1-2.4.", sev="major", files=KTS)
dep("GRADLE-XJVM-DEFAULT", "-Xjvm-default compiler flag", "2.2", "whatsnew22.html", "replacing the deprecated -Xjvm-default option",
    '((string_content) @match (#match? @match "^-Xjvm-default"))', 'freeCompilerArgs.add("-Xjvm-default=all")\n', 'jvmDefault.set(JvmDefaultMode.ENABLE)\n',
    "Use -jvm-default / compilerOptions.jvmDefault (2.2+).", files=KTS)
dep("GRADLE-KAPT", "kapt annotation processing", "1.8", "kapt.html", "kapt to KSP",
    '((call_expression (identifier) @f (value_arguments (value_argument (string_literal (string_content) @match)))) (#eq? @f "kotlin") (#eq? @match "kapt"))',
    'plugins {\n    kotlin("kapt")\n}\n', 'plugins {\n    id("com.google.devtools.ksp")\n}\n', "kapt is in maintenance mode; migrate processors to KSP where supported.",
    sev="info", kind="modernization", files=KTS, mode="ai-confirm", ai="Do the annotation processors used here (Room, Dagger/Hilt, Moshi...) have KSP support?")
dep("GRADLE-ANDROID-EXTENSIONS", "kotlin-android-extensions plugin", "1.8", "compatibility-guide-18.html", "synthetic property",
    '((string_content) @match (#match? @match "^(kotlin-android-extensions|org\\\\.jetbrains\\\\.kotlin\\\\.android\\\\.extensions)$"))',
    'plugins {\n    id("kotlin-android-extensions")\n}\n', 'plugins {\n    id("kotlin-parcelize")\n}\n', "The plugin was removed in 1.8; use kotlin-parcelize and View Binding.",
    sev="critical", kind="removal", files=KTS)

# ------------------------------------------------------------------ null safety / idioms / conventions
def conv(id, title, page, needle, query, bad, good, msg, sev="minor", cat="best-practice", **kw):
    P(id, title, page if page.startswith("http") else K + page, needle, query, bad, good, msg, sev=sev, cat=cat, docv=kw.pop("docv", "Kotlin 2.4"), files=kw.pop("files", SRC), **kw)


conv("NOT-NULL-ASSERTION", "!! not-null assertion", "null-safety.html", "Not-null assertion operator !!", '((unary_expression) @match (#match? @match "!!$"))',
     "val n = s!!.length\n", "val n = s?.length ?: 0\n", "!! throws NullPointerException; handle null with ?. / ?: / requireNotNull(x) { msg }.", cat="correctness")
conv("ELVIS", "if (x != null) x else y", "idioms.html", "If-not-null-else shorthand",
     '((if_expression condition: (binary_expression left: (identifier) @a right: (_) @n) . (identifier) @b) @match (#eq? @a @b) (#eq? @n "null") (#match? @match "!="))',
     'val y = if (x != null) x else "d"\n', 'val y = x ?: "d"\n', "Use the Elvis operator.", sev="info", cat="style")
conv("EMPTY-CATCH", "Empty catch block", "exceptions.html", "Catching exceptions: handle the unexpected exception manually", '(catch_block (block) @match (#match? @match "^\\\\{\\\\s*\\\\}$"))',
     "try { g() } catch (e: Exception) { }\n", "try { g() } catch (e: IOException) { log.warn(\"g failed\", e) }\n", "Swallowing exceptions hides failures.", cat="correctness",
     # detekt EmptyCatchBlock allowedExceptionNameRegex default: `_|(ignore|expected).*` marks a deliberate swallow
     filters=[r"parent.lacks_re:^catch\s*\(\s*(_|ignore\w*|expected\w*)\s*:"],
     fp=["try { g() } catch (_: Exception) {}\ntry { g() } catch (ignored: IOException) { }\n"])
conv("STRING-CONCAT", "String concatenation with +", "idioms.html", "String interpolation println(\"Name $name\")",
     # the middle operand must be an expression: "a " + "b " + "c" only wraps a long literal over lines
     '((binary_expression left: (binary_expression left: (string_literal) right: (_) @mid) right: (string_literal)) @match (#not-match? @mid "^\\""))', 'val s = "Hello, " + name + "!"\n',
     'val s = "Hello, $name!"\n', "Use string templates.", sev="info", cat="style",
     fp=['val m = "first part of a long message " +\n    "second part " +\n    "third part"\n'])
conv("TEMPLATE-BRACES", "${x} for a simple variable in a template", "coding-conventions.html", "Don't use curly braces when inserting a simple variable into a string template.",
     '((interpolation (identifier) @x) @match (#match? @match "^\\\\$\\\\{"))', 'println("${x}")\n', 'println("$x")\n', "Drop redundant braces.", sev="info", cat="style",
     # braces are required when a letter, digit or _ follows ("${ms}ms", "${name}_v2")
     filters=[r"parent.lacks_re:\$\{{cap:x}\}\w"], fp=['println("took ${ms}ms in ${name}_v2")\n'])
conv("UNIT-RETURN", "Explicit : Unit return type", "coding-conventions.html", "If a function returns Unit, the return type should be omitted",
     '((function_declaration (function_value_parameters) . (user_type (identifier) @match)) (#eq? @match "Unit"))', "fun log(m: String): Unit {\n    println(m)\n}\n",
     "fun log(m: String) {\n    println(m)\n}\n", "Omit Unit return types.", sev="info", cat="style",
     # with an expression body, ": Unit" pins the signature (otherwise inferred from the expression, e.g. Nothing or the lock result)
     filters=[r"ancestor.lacks_re:function_declaration:\)\s*:\s*Unit\s*="], fp=["override fun close(): Unit = synchronized(lock) { release() }\n"])
conv("BOXED-ARRAY", "Array<Int>/Array<Long>... of primitives", "arrays.html", "primitive-type arrays",
     '((user_type (identifier) @a (type_arguments (type_projection (user_type (identifier) @match)))) (#eq? @a "Array") (#match? @match "^(Int|Long|Short|Byte|Double|Float|Boolean|Char)$"))',
     "val a: Array<Int> = arrayOf(1, 2)\n", "val a: IntArray = intArrayOf(1, 2)\n", "Primitive arrays avoid boxing.", sev="info", cat="performance")
conv("SIZE-ZERO", "size == 0 / length == 0", "../api/core/kotlin-stdlib/kotlin.collections/is-empty.html", "Returns true if the array is empty.",
     '((binary_expression left: (navigation_expression (_) (identifier) @p) right: (number_literal) @z) @match (#match? @p "^(size|length)$") (#eq? @z "0") (#match? @match "[=!]="))',
     "if (list.size == 0) return\n", "if (list.isEmpty()) return\n", "Use isEmpty()/isNotEmpty().", sev="info", cat="style")
conv("FILTER-FIRST", "filter{}.first()/.firstOrNull()/.count()/.isEmpty()", "collection-filtering.html", "When called with a predicate, filter() returns the collection elements that match it.",
     '((call_expression (navigation_expression (call_expression (navigation_expression (_) (identifier) @f) (annotated_lambda)) (identifier) @match) (value_arguments) @args) (#eq? @f "filter") (#match? @match "^(first|firstOrNull|last|lastOrNull|single|count|isEmpty|isNotEmpty|any|none)$") (#eq? @args "()"))',
     "val u = users.filter { it.active }.first()\n", "val u = users.first { it.active }\n", "Pass the predicate to first/count/any directly; avoids an intermediate list.",
     sev="info", cat="performance")
conv("MAP-FLATTEN", "map{}.flatten()", "collection-transformations.html", "behaves as a subsequent call of map() (with a collection as a mapping result) and flatten()",
     '((call_expression (navigation_expression (call_expression (navigation_expression (_) (identifier) @f) (annotated_lambda)) (identifier) @match)) (#eq? @f "map") (#eq? @match "flatten"))',
     "val all = groups.map { it.items }.flatten()\n", "val all = groups.flatMap { it.items }\n", "Use flatMap.", sev="info", cat="performance")
conv("SORTED-FIRST", "sortedBy{}.first()", "collection-aggregate.html", "take a selector function and return the element for which it returns the largest or the smallest value.",
     '((call_expression (navigation_expression (call_expression (navigation_expression (_) (identifier) @f) (annotated_lambda)) (identifier) @match)) (#match? @f "^sorted(By|ByDescending)$") (#match? @match "^(first|firstOrNull|last|lastOrNull)$"))',
     "val y = people.sortedBy { it.age }.first()\n", "val y = people.minBy { it.age }\n", "Use minBy/maxBy (O(n) instead of O(n log n)).", sev="info", cat="performance")
conv("ARRAYLIST-CTOR", "ArrayList()/HashMap() constructors", "collections-overview.html", "mutableListOf<String>()",
     '((call_expression . (identifier) @match (value_arguments) @a) (#match? @match "^(ArrayList|HashMap|HashSet|LinkedHashMap|LinkedHashSet)$") (#eq? @a "()"))',
     "val xs = ArrayList<String>()\n", "val xs = mutableListOf<String>()\n", "Prefer mutableListOf()/mutableMapOf()/mutableSetOf().", sev="info", cat="style",
     filters=["node.lacks_re:<"])
conv("WHEN-SUBJECT-ELSE", "when used as statement on a sealed/enum value without else", "control-flow.html", "If you use when as a statement, you don't need to cover all possible cases.",
     '(when_expression (when_subject) . (when_entry) (when_entry)? .) @match', 'when (x) { "a" -> 1 }\n', 'when (x) { "a" -> 1; else -> 0 }\n',
     "A non-exhaustive when silently ignores other values.", cat="correctness", mode="ai-confirm",
     ai="Is the subject not a sealed/enum/Boolean type covered exhaustively, so other values are silently ignored?",
     filters=["node.lacks_re:\\belse\\b"])
conv("PRINTLN-LOGGING", "printStackTrace in production code", "exceptions.html", "Catching exceptions: handle the unexpected exception manually",
     '((call_expression (navigation_expression (_) (identifier) @match)) (#eq? @match "printStackTrace"))', "try { g() } catch (e: Exception) { e.printStackTrace() }\n",
     "try { g() } catch (e: IOException) { log.error(\"failed\", e) }\n", "printStackTrace goes to stderr unstructured; use a logger.", cat="maintainability",
     # printStackTrace(writer) renders into a caller-supplied sink (log formatters), not stderr
     filters=[r"ancestor.lacks_re:call_expression:printStackTrace\s*\(\s*([^S\s)]|S[^y])"], fp=["fun format(t: Throwable, pw: PrintWriter) { t.printStackTrace(pw) }\n"])
conv("LATEINIT-CHECK-ABUSE", "lateinit isInitialized checks", "properties.html", "isInitialized property on the reference to that property",
     '((navigation_expression (callable_reference) (identifier) @match) (#eq? @match "isInitialized"))', "if (::db.isInitialized) db.close()\n", "db?.close()\n",
     "Frequent isInitialized checks suggest the property should be nullable or lazy.", sev="info", cat="design", mode="ai-confirm",
     ai="Is isInitialized used for regular control flow (not tests/teardown)?")
conv("FUN-INTERFACE", "object : SingleMethodInterface", "fun-interfaces.html", "Kotlin can convert any lambda expression whose signature matches the signature of the interface's single method",
     '((object_literal (delegation_specifiers (delegation_specifier (user_type (identifier) @t))) (class_body . (function_declaration) .)) @match (#match? @t "^(Runnable|Callable|Comparator|Supplier|Consumer|Function|Predicate)$"))',
     "val r = object : Runnable {\n    override fun run() { work() }\n}\n", "val r = Runnable { work() }\n", "Use a SAM-converting lambda.", sev="info", cat="style")
conv("EQUALS-EMPTY", "equals(\"\")", "../api/core/kotlin-stdlib/kotlin.collections/is-empty.html", "Returns true if the array is empty.",
     '((call_expression (navigation_expression (_) (identifier) @m) (value_arguments (value_argument (string_literal) @s))) @match (#eq? @m "equals") (#eq? @s "\\"\\""))',
     'if (s.equals("")) return\n', "if (s.isEmpty()) return\n", "Use isEmpty()/isBlank().", sev="info", cat="style")

# ------------------------------------------------------------------ coroutines
def co(id, title, url, needle, query, bad, good, msg, sev="major", cat="concurrency", **kw):
    P(id, title, url, needle, query, bad, good, msg, sev=sev, cat=cat, docv="kotlinx.coroutines 1.10", files=kw.pop("files", SRC), **kw)


co("GLOBALSCOPE", "GlobalScope usage", CO + "-global-scope/", "delicate API",
   '((navigation_expression . (identifier) @match . (identifier) @l) (#eq? @match "GlobalScope") (#match? @l "^(launch|async|produce|actor)$"))',
   "fun start() {\n    GlobalScope.launch { work() }\n}\n", "fun CoroutineScope.start() {\n    launch { work() }\n}\n",
   "GlobalScope coroutines are not bound to any lifecycle and leak; use structured concurrency (a scoped CoroutineScope).",
   # GlobalScope is a delicate API: an explicit DelicateCoroutinesApi opt-in records that the use is deliberate
   filters=["file.lacks_re:DelicateCoroutinesApi"],
   fp=["@OptIn(DelicateCoroutinesApi::class)\nfun start() {\n    GlobalScope.launch { work() }\n}\n"])
co("RUNBLOCKING-IN-SUSPEND", "runBlocking inside a suspend function / coroutine", CO + "run-blocking.html", "designed to bridge regular blocking code to libraries that are written in suspending style",
   '((function_declaration (modifiers (function_modifier) @s) (function_body (block (call_expression . (identifier) @match)))) (#eq? @s "suspend") (#eq? @match "runBlocking"))',
   "suspend fun load() {\n    runBlocking { fetch() }\n}\n", "suspend fun load() {\n    fetch()\n}\n", "runBlocking blocks the thread and can deadlock the dispatcher.")
co("THREAD-SLEEP-IN-COROUTINE", "Thread.sleep in a suspend function", K + "coroutines-basics.html", "function to simulate a suspending task",
   '((function_declaration (modifiers (function_modifier) @s) (function_body (block (call_expression (navigation_expression . (identifier) @t . (identifier) @match))))) (#eq? @s "suspend") (#eq? @t "Thread") (#eq? @match "sleep"))',
   "suspend fun poll() {\n    Thread.sleep(1000)\n}\n", "suspend fun poll() {\n    delay(1000)\n}\n", "Thread.sleep blocks the dispatcher thread; use delay().")
co("CATCH-CANCELLATION", "catch (e: Exception) in a suspend function swallows cancellation", K + "exception-handling.html", "CancellationException",
   '((function_declaration (modifiers (function_modifier) @s) (function_body (block (try_expression (catch_block (identifier) (user_type (identifier) @match)))))) (#eq? @s "suspend") (#match? @match "^(Exception|Throwable)$"))',
   "suspend fun f() {\n    try { g() } catch (e: Exception) { log(e) }\n}\n", "suspend fun f() {\n    try { g() } catch (e: IOException) { log(e) }\n}\n",
   "Catching Exception also catches CancellationException; rethrow it (or catch narrower types) so cancellation propagates.",
   mode="ai-confirm", ai="Does the handler swallow CancellationException (no rethrow, no ensureActive())?")
co("ASYNC-AWAIT-IMMEDIATE", "async { }.await() immediately", K + "composing-suspending-functions.html", "This is where async comes to",
   '((call_expression (navigation_expression (call_expression . (identifier) @a (annotated_lambda)) (identifier) @match)) (#eq? @a "async") (#eq? @match "await"))',
   "val r = async { fetch() }.await()\n", "val r = withContext(Dispatchers.IO) { fetch() }\n", "async+await in one expression is sequential; call directly or use withContext.",
   sev="minor", cat="performance")
co("DISPATCHERS-MAIN-BLOCKING", "Blocking I/O on Dispatchers.Main", K + "coroutine-context-and-dispatchers.html", "uses a shared background pool of threads",
   '((call_expression . (identifier) @w (value_arguments (value_argument (navigation_expression . (identifier) @d . (identifier) @m)))) @match (#eq? @w "withContext") (#eq? @d "Dispatchers") (#eq? @m "Main"))',
   "withContext(Dispatchers.Main) { file.readText() }\n", "withContext(Dispatchers.IO) { file.readText() }\n", "Do blocking work on Dispatchers.IO.",
   mode="ai-confirm", ai="Does the block perform blocking I/O or heavy CPU work on the main dispatcher?")

# ------------------------------------------------------------------ security (JVM APIs)
JDK = "https://docs.oracle.com/en/java/javase/21/docs/api/"
def sec(id, title, url, needle, query, bad, good, msg, sev="critical", **kw):
    P(id, title, url, needle, query, bad, good, msg, sev=sev, kind="security", cat="security", docv=kw.pop("docv", "Java SE 21 API"), files=kw.pop("files", SRC), **kw)


sec("INSECURE-RANDOM", "java.util.Random / kotlin.random for secrets", JDK + "java.base/java/util/Random.html", "not cryptographically secure",
    '((property_declaration (variable_declaration (identifier) @n) (_) @match) (#match? @n "(?i)(token|secret|password|nonce|salt|otp|key|session)") (#match? @match "Random\\\\.|Random\\\\(\\\\)\\\\.|nextInt|nextLong|nextBytes"))',
    "val token = Random.nextLong().toString()\n", "val token = SecureRandom().nextLong().toString()\n", "Use java.security.SecureRandom for security-sensitive values.", sev="major",
    filters=["node.lacks_re:SecureRandom"])
sec("RUNTIME-EXEC-TEMPLATE", "Runtime.exec / ProcessBuilder with an interpolated command string", JDK + "java.base/java/lang/ProcessBuilder.html", "a list of strings which signifies the external program file to be invoked and its arguments",
    '((call_expression (navigation_expression (_) (identifier) @m) (value_arguments . (value_argument (string_literal) @match))) (#eq? @m "exec") (#match? @match "\\\\$[A-Za-z_{]"))',
    'Runtime.getRuntime().exec("convert $name out.png")\n', 'ProcessBuilder("convert", name, "out.png").start()\n',
    "A single command string is split on spaces and interpolated input can inject arguments; pass an argument list.", sev="major")
sec("SQL-TEMPLATE", "SQL built with string templates", "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html", "Parameterized Queries",
    '((call_expression (navigation_expression (_) (identifier) @m) (value_arguments . (value_argument (string_literal) @match))) (#match? @match "\\\\$[A-Za-z_{]") (#match? @m "^(executeQuery|executeUpdate|execute|prepareStatement|rawQuery|execSQL|createQuery|createNativeQuery|query|update)$"))',
    'stmt.executeQuery("SELECT * FROM u WHERE id = $id")\n', 'conn.prepareStatement("SELECT * FROM u WHERE id = ?").apply { setLong(1, id) }\n',
    "Use bind parameters.", docv="OWASP cheat sheet (2026)",
    # execute()/query()/update() are generic names (okhttp TaskQueue.execute("$name ping")): the template must read as SQL
    filters=["taint.clean:sqli", r"node.has_re:(?i)\b(select\s.+\sfrom|insert\s+into|update\s+\S+\s+set|delete\s+from|(create|drop|alter|truncate)\s+table|\swhere\s)"],
    fp=['writerQueue.execute("$connectionName[$streamId] writeSynReset") { run() }\n'])
sec("TRUST-ALL", "TrustManager that accepts every certificate", JDK + "java.base/javax/net/ssl/X509TrustManager.html", "Given the partial or complete certificate chain provided by the peer, build a certificate path to a trus",
    '((function_declaration name: (identifier) @match (function_body (block) @b)) (#match? @match "^(checkServerTrusted|checkClientTrusted)$") (#match? @b "^\\\\{\\\\s*\\\\}$"))',
    "override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {}\n",
    "override fun checkServerTrusted(chain: Array<X509Certificate>, authType: String) {\n    delegate.checkServerTrusted(chain, authType)\n}\n",
    "An empty checkServerTrusted disables TLS verification (MITM).",
    # test fixtures trusting a local self-signed server are not shipped code
    files=SRC + ["!**/src/test/**", "!**/src/*Test/**", "!**/test/**", "!**/*Test.kt", "!**/*Tests.kt", "!**/*TestClass.kt"])
sec("HOSTNAME-VERIFIER-ALL", "HostnameVerifier returning true", JDK + "java.base/javax/net/ssl/HostnameVerifier.html", "This class is the base interface for hostname verification.",
    '((call_expression . (identifier) @h (annotated_lambda (lambda_literal) @l)) @match (#eq? @h "HostnameVerifier") (#match? @l "true\\\\s*\\\\}$"))',
    "val v = HostnameVerifier { _, _ -> true }\n", "val v = HttpsURLConnection.getDefaultHostnameVerifier()\n", "Accepting every hostname disables TLS identity checks.")
sec("WEAK-HASH", "MD5/SHA-1 MessageDigest", JDK + "java.base/java/security/MessageDigest.html", "class provides applications the functionality of a message digest algorithm",
    '((call_expression (navigation_expression . (_) @c . (identifier) @g) (value_arguments (value_argument (string_literal (string_content) @match)))) (#match? @c "^(java\\\\.security\\\\.)?MessageDigest$") (#eq? @g "getInstance") (#match? @match "(?i)^(MD5|MD2|SHA-?1)$"))',
    'fun hashPassword(password: String): ByteArray =\n    java.security.MessageDigest.getInstance("MD5").digest(password.toByteArray())\n', 'val md = MessageDigest.getInstance("SHA-256")\n', "MD5/SHA-1 are collision-broken.", sev="major",
    mode="ai-confirm", ai="Is the digest used for security (signatures, passwords, integrity against attackers)?")
sec("JAVA-DESERIALIZATION", "ObjectInputStream.readObject on external data", JDK + "java.base/java/io/ObjectInputStream.html", "Warning: Deserialization of untrusted data is inherently dangerous",
    '((call_expression (navigation_expression (_) (identifier) @match)) (#eq? @match "readObject"))', "val o = ObjectInputStream(input).readObject()\n",
    "val o = Json.decodeFromString<Payload>(text)\n", "Java deserialization of untrusted data enables gadget-chain RCE; use a data format + ObjectInputFilter.",
    mode="ai-confirm", ai="Can the stream contain untrusted data and no ObjectInputFilter is set?")
sec("CIPHER-ECB", "Cipher in ECB mode / default AES transformation", JDK + "java.base/javax/crypto/Cipher.html", "transformation is of the form:",
    '((call_expression (navigation_expression . (identifier) @c . (identifier) @g) (value_arguments (value_argument (string_literal (string_content) @match)))) (#eq? @c "Cipher") (#eq? @g "getInstance") (#match? @match "(?i)(^AES$|^DES|/ECB/)"))',
    'val c = Cipher.getInstance("AES/ECB/PKCS5Padding")\n', 'val c = Cipher.getInstance("AES/GCM/NoPadding")\n', "ECB leaks plaintext patterns; use AES/GCM.", sev="major")
P("HARDCODED-SECRET", "Hard-coded secret assigned to a property", "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
  "Many organizations have them hardcoded within the source code in plaintext",
  '((property_declaration (variable_declaration (identifier) @n) (string_literal (string_content) @match)) (#match? @n "(?i)^(password|passwd|pwd|secret|clientSecret|apiKey|apikey|accessToken|authToken|privateKey|secretKey|API_KEY|SECRET_KEY|PASSWORD)$") (#not-match? @match "' + PLACEHOLDER_RE + '"))',
  'val apiKey = "a8f5f167f44f4964e6c998dee827110c"\n', 'val apiKey = System.getenv("API_KEY")\n', "Load secrets from the environment or a secret store.",
  sev="critical", kind="security", cat="security", docv="OWASP cheat sheet (2026)", files=SRC)
secret_rules(P, '(string_content)', lambda k, v: f'val {k} = "{v}"\n')
# ------------------------------------------------------------------ more stdlib / language
dep("MEASURE-TIME-MILLIS", "measureTimeMillis/measureNanoTime", "1.9", "whatsnew19.html", "measureTime",
    fcall("measureTimeMillis|measureNanoTime"), "val ms = measureTimeMillis { work() }\n", "val d = measureTime { work() }\n",
    "measureTime (stable in 1.9) returns a Duration.", kind="modernization", sev="info")
dep("HEXFORMAT", "String.format(\"%02x\") hex encoding", "2.2", "whatsnew22.html", "Base64 API and HexFormat API are now Stable",
    '((call_expression (navigation_expression (string_literal (string_content) @match) (identifier) @f)) (#eq? @f "format") (#match? @match "^%0?2[xX]$"))',
    'val hex = bytes.joinToString("") { "%02x".format(it) }\n', "val hex = bytes.toHexString()\n", "Use toHexString()/HexFormat (stable in 2.2).", kind="modernization", sev="info")
dep("KOTLIN-BASE64", "java.util.Base64 in common Kotlin code", "2.2", "whatsnew22.html", "Base64 API and HexFormat API are now Stable",
    '((navigation_expression (navigation_expression (navigation_expression . (identifier) @j . (identifier) @u) (identifier) @match)) (#eq? @j "java") (#eq? @u "util") (#eq? @match "Base64"))',
    "val s = java.util.Base64.getEncoder().encodeToString(b)\n", "val s = kotlin.io.encoding.Base64.encode(b)\n", "kotlin.io.encoding.Base64 is stable in 2.2 and multiplatform.",
    kind="modernization", sev="info")
dep("MIN-MAX-ORNULL-17", "minOrNull()!!/maxOrNull()!!", "1.7", "whatsnew17.html", "In Kotlin 1.4.0 , we renamed the min() and max() collection functions to minOrNull() and maxOrN",
    '((unary_expression argument: (call_expression (navigation_expression (_) (identifier) @match))) (#match? @match "^(minOrNull|maxOrNull|minByOrNull|maxByOrNull)$"))',
    "val m = xs.maxOrNull()!!\n", "val m = xs.max()\n", "Since 1.7 min()/max() return non-null (throwing on empty).", kind="modernization", sev="info")
dep("ENUM-VALUE-OF-GENERIC", "enumValues<T>()", "2.0", "whatsnew20.html", "function is a replacement for the generic enumV",
    '((call_expression . (identifier) @match) (#eq? @match "enumValues"))', "val all = enumValues<Color>()\n", "val all = enumEntries<Color>()\n",
    "Use enumEntries<T>() (stable in 2.0).", kind="modernization", sev="info")
dep("KMP-ANDROID-TARGET", "android() target in Kotlin Multiplatform", "2.1", "whatsnew21.html", "the deprecation warning for the old android target name has been raised to an error",
    '((call_expression . (identifier) @match (value_arguments) @a) (#eq? @match "android") (#eq? @a "()"))', "plugins { kotlin(\"multiplatform\") }\nkotlin {\n    android()\n}\n", "plugins { kotlin(\"multiplatform\") }\nkotlin {\n    androidTarget()\n}\n",
    "android() was renamed androidTarget(); an error since 2.1.", sev="critical", kind="removal", files=KTS, filters=["file.has_re:multiplatform"])
dep("USE-EXPERIMENTAL", "@UseExperimental / @Experimental annotations", "1.7", "compatibility-guide-17.html", "useExperimentalAnnotation compiler option",
    '((user_type (identifier) @match) (#match? @match "^(UseExperimental|Experimental)$"))', "@UseExperimental(ExperimentalTime::class)\nfun f() {}\n",
    "@OptIn(ExperimentalTime::class)\nfun f() {}\n", "Use @OptIn / @RequiresOptIn.", sev="major", kind="removal")
conv("EQUALS-WITHOUT-HASHCODE", "equals() overridden without hashCode()", "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html",
     "generally necessary to override the hashCode method whenever this method is overridden",
     '((class_declaration (class_body) @match) (#match? @match "override\\\\s+fun\\\\s+equals\\\\s*\\\\(") (#not-match? @match "fun\\\\s+hashCode\\\\s*\\\\("))',
     "class P(val x: Int) {\n    override fun equals(other: Any?) = other is P && other.x == x\n}\n",
     "class P(val x: Int) {\n    override fun equals(other: Any?) = other is P && other.x == x\n    override fun hashCode() = x\n}\n",
     "Equal objects must have equal hash codes (HashMap/HashSet break otherwise); or use a data class.", sev="major", cat="correctness", docv="Java SE 21 API")
conv("SIMPLEDATEFORMAT-SHARED", "Shared SimpleDateFormat", "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/text/SimpleDateFormat.html", "Date formats are not synchronized.",
     '((object_declaration (class_body (property_declaration (call_expression . (identifier) @match)))) (#eq? @match "SimpleDateFormat"))\n((companion_object (class_body (property_declaration (call_expression . (identifier) @match)))) (#eq? @match "SimpleDateFormat"))',
     'object Fmt {\n    val df = SimpleDateFormat("yyyy-MM-dd")\n}\n', 'object Fmt {\n    val df: DateTimeFormatter = DateTimeFormatter.ISO_LOCAL_DATE\n}\n',
     "A shared SimpleDateFormat is not thread-safe; use java.time DateTimeFormatter.", sev="major", cat="concurrency", docv="Java SE 21 API")
conv("DEPRECATED-NO-REPLACEWITH", "@Deprecated without ReplaceWith", "annotations.html", "ReplaceWith(\"this === other\")",
     '((annotation (constructor_invocation (user_type (identifier) @a) (value_arguments) @args)) @match (#eq? @a "Deprecated") (#not-match? @args "ReplaceWith") (#not-match? @args "HIDDEN"))',
     '@Deprecated("use bar")\nfun foo() {}\n', '@Deprecated("use bar", ReplaceWith("bar()"))\nfun foo() {}\n', "ReplaceWith enables IDE quick-fix migration.", sev="info", cat="maintainability",
     fp=[{"note": "bench 2026-10-10: level = HIDDEN keeps a symbol for binary compatibility only; it is invisible to callers, so there is nothing to migrate",
          "code": '@Deprecated("binary compatibility", level = DeprecationLevel.HIDDEN)\nfun foo(x: Int) {}\n'},
         {"note": "imported HIDDEN constant", "code": '@Deprecated(message = "kept for ABI", level = HIDDEN)\nfun bar() {}\n'}])
conv("UNSAFE-CAST", "Unsafe cast with as on external data", "typecasts.html", "unsafe operator.",
     '((as_expression (_) (user_type (identifier) @t)) @match (#match? @t "^(String|Int|Long|Map|List|Boolean)$") (#not-match? @match "\\\\sas\\\\?"))', 'val id = json["id"] as String\n', 'val id = json["id"] as? String ?: error("id missing")\n',
     "as throws ClassCastException on mismatch; use as? with a fallback for untyped data.", sev="minor", cat="correctness", mode="ai-confirm",
     ai="Is the cast applied to untyped/external data (JSON maps, Bundle extras) where the type is not guaranteed?")

# ------------------------------------------------------------------ 2026.10 expansion: coroutines context, conventions, compat guides
CTX = K + "coroutine-context-and-dispatchers.html"
STD = "https://kotlinlang.org/api/core/kotlin-stdlib/"
co("DISPATCHERS-UNCONFINED", "Dispatchers.Unconfined in general code", CTX, "The unconfined dispatcher is an advanced mechanism",
   '((navigation_expression . (identifier) @d . (identifier) @match) (#eq? @d "Dispatchers") (#eq? @match "Unconfined"))',
   "fun CoroutineScope.f() {\n    launch(Dispatchers.Unconfined) { work() }\n}\n", "fun CoroutineScope.f() {\n    launch(Dispatchers.Default) { work() }\n}\n",
   "Unconfined resumes on whatever thread the suspension finished on; use a real dispatcher.", sev="minor")
co("NEW-THREAD-CONTEXT-LEAK", "newSingleThreadContext/newFixedThreadPoolContext never closed", CTX, "A dedicated thread is a very expensive resource.",
   '((function_body (block) @b) @match (#match? @b "new(SingleThread|FixedThreadPool)Context\\\\(") (#not-match? @b "\\\\.(use|close)\\\\b"))',
   'fun f() {\n    val ctx = newSingleThreadContext("w")\n    runBlocking(ctx) { work() }\n}\n', 'fun f() {\n    newSingleThreadContext("w").use { ctx ->\n        runBlocking(ctx) { work() }\n    }\n}\n',
   "Release the thread with close()/use {} or keep a single top-level instance.", cat="resources",
   quote="A dedicated thread is a very expensive resource. In a real application it must be either released, when no longer needed, using the close function, or stored in a top-level variable and reused throughout the application.")
co("JOB-PASSED-TO-BUILDER", "Job()/SupervisorJob() passed to launch/async", CTX, "it does not inherit a Job from the parent scope",
   '((call_expression (identifier) @b (value_arguments (value_argument (call_expression . (identifier) @match)))) (#match? @b "^(launch|async)$") (#match? @match "^(Job|SupervisorJob)$"))',
   "fun CoroutineScope.f() {\n    launch(Job()) { work() }\n}\n", "fun CoroutineScope.f() {\n    launch { work() }\n}\n",
   "A new Job breaks structured concurrency: the child is no longer cancelled with its parent.")
co("BROADCAST-CHANNEL", "BroadcastChannel / ConflatedBroadcastChannel (deprecated, error level)",
   "https://raw.githubusercontent.com/Kotlin/kotlinx.coroutines/master/kotlinx-coroutines-core/common/src/channels/BroadcastChannel.kt",
   "BroadcastChannel is deprecated in the favour of SharedFlow", '((identifier) @match (#match? @match "^(BroadcastChannel|ConflatedBroadcastChannel)$"))',
   "val events = BroadcastChannel<Event>(16)\n", "val events = MutableSharedFlow<Event>(extraBufferCapacity = 16)\n", "Use SharedFlow / StateFlow.",
   kind="removal", cat="compatibility")
conv("CONST-NAMING", "const val not in SCREAMING_SNAKE_CASE", "coding-conventions.html", "should use all uppercase, underscore-separated names",
     '((property_declaration (modifiers (property_modifier) @m) (variable_declaration (identifier) @match)) (#eq? @m "const") (#match? @match "^[a-z]"))',
     "const val maxCount = 10\n", "const val MAX_COUNT = 10\n", "Constants use UPPER_SNAKE_CASE.", sev="info", cat="style")
conv("CLASS-NAMING", "Class or object name not in UpperCamelCase", "coding-conventions.html", "Names of classes and objects use upper camel case",
     '([(class_declaration name: (identifier) @match) (object_declaration name: (identifier) @match)] (#match? @match "^[a-z_]"))',
     "class userRepo\n", "class UserRepo\n", "Use UpperCamelCase.", sev="info", cat="style")
conv("FUNCTION-NAMING", "Function name starts with an uppercase letter", "coding-conventions.html", "Names of functions, properties, and local variables start with a lowercase letter",
     '((function_declaration name: (identifier) @n) @match (#match? @n "^[A-Z]") (#not-match? @match "@Composable|@Test"))',
     "fun LoadUser(id: Long) {}\n", "fun loadUser(id: Long) {}\n", "Use lowerCamelCase (factory functions named after the type are the exception).", sev="info", cat="style",
     # factory functions: declared return type or expression body names the same type; explicit @Suppress
     filters=[r"node.lacks_re:\)\s*:\s*([\w.]+\.)?\w*{cap:n}\b|=\s*{cap:n}\s*[(<{.]|@Suppress\([^)]*FunctionNaming",
              # corpus (coil, exposed): factory functions whose expression body is a constructor call, e.g.
              # fun OkHttpNetworkFetcherFactory(...) = NetworkFetcher.Factory(...)
              r"node.lacks_re:\bfun\s+(<[^>]*>\s*)?([\w.<>]+\.)?{cap:n}\s*\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\)\s*(:[^={]+)?=\s*([\w.]+\.)?[A-Z]\w*\s*[(<{]"],
     fp=["fun Size(width: Int, height: Int) = Size(Dimension(width), Dimension(height))\nfun MainViewModel(r: Resources): MainViewModel {\n    return RealVm(r)\n}\n",
         "actual fun ConnectivityChecker(context: PlatformContext) = ConnectivityChecker.ONLINE\n",
         "fun <T> When(cond: Expression<*>, result: Expression<T>): CaseWhen<T> {\n    return CaseWhen<T>().When(cond, result)\n}\n",
         "fun OkHttpFetcherFactory(\n    callFactory: () -> Call.Factory = ::OkHttpClient,\n    cache: () -> Strategy = { Strategy() },\n) = NetworkFetcher.Factory(\n    client = { callFactory() },\n)\n"],
     mode="ai-confirm", ai="Is this a regular function (not a factory function named after the type it returns, and not a Compose/DSL builder)?")
conv("VAR-NEVER-REASSIGNED", "Local var that could be val", "coding-conventions.html", "Always declare local variables and properties as val rather than var if they are not modified after initialization.",
     '((function_body (block (property_declaration (variable_declaration (identifier) @name)) @match)) (#match? @match "^var\\\\b"))',
     "fun f(): Int {\n    var x = compute()\n    return x\n}\n", "fun f(): Int {\n    val x = compute()\n    return x\n}\n", "Prefer immutable locals.", sev="info", cat="style",
     # initialised in the declaration, not delegated (by remember { mutableStateOf() } needs var), and no other
     # assignment/compound assignment/increment of the name anywhere in the function
     filters=[r"node.has_re:^var\s+\w+\s*(:[^=]+)?=", r"node.lacks_re:\bby\b",
              r"func.count_lt:2:\b{cap:name}\s*(:[^=\n]+)?([-+*/%]?=[^=]|\+\+|--)|(\+\+|--)\s*{cap:name}\b"],
     fp=["fun f(): Int {\n    var idx: Map<String, Int>? = null\n    if (idx == null) idx = load()\n    var n = 0\n    repeat(3) { n++ }\n    var s = 1\n    s += 2\n    var on by remember { mutableStateOf(false) }\n    return n + s\n}\n",
         # tree-sitter-kotlin cuts this function at `suspend { }` + KDoc + `.call(`: the later write must still count
         "class T {\n    @Test\n    fun testSuspendMain() {\n        Assumptions.assumeTrue(dialect == TestDB.POSTGRESQL)\n\n        val latch = CountDownLatch(1)\n        var exception: Throwable? = null\n\n        suspend {\n            val db = TestDB.POSTGRESQL.connect()\n\n            suspendTransaction(db) {\n                SchemaUtils.create(UsersTable)\n            }\n        }\n            /**\n             * The main reason for such a coroutine starting is to get\n             * [EmptyCoroutineContext] as coroutine context. It will guarantee\n             * that coroutine dispatcher will be `null` what could lead\n             * to wrong transaction switching\n             */\n            .startCoroutine(object : Continuation<Unit> {\n                override val context = EmptyCoroutineContext\n\n                override fun resumeWith(result: Result<Unit>) {\n                    result.onFailure { exception = it }\n                    latch.countDown()\n                }\n            })\n\n        // Wait for completion with timeout\n        if (!latch.await(10, TimeUnit.SECONDS)) {\n            throw AssertionError(\"Test did not complete within 10 seconds\")\n        }\n\n        assertNull(exception)\n    }\n}\n"],
     mode="ai-confirm", ai="Is this var never reassigned after initialization within the function?")
conv("MUTABLE-COLLECTION-API", "Mutable collection type exposed", "coding-conventions.html", "Always use immutable collection interfaces (Collection, List, Set, Map) to declare collections which are not mutated.",
     '((function_declaration (function_value_parameters) . (user_type (identifier) @match)) (#match? @match "^(MutableList|MutableSet|MutableMap|MutableCollection|ArrayList|HashMap|HashSet)$"))',
     "fun names(): MutableList<String> = mutableListOf()\n", "fun names(): List<String> = listOf()\n", "Expose read-only interfaces.", sev="info", cat="maintainability",
     # return types only; non-public, override and actual declarations are not a free API choice
     filters=[r"ancestor.lacks_re:function_declaration:^[^{=]*?\b(private|internal|protected|override|actual)\s+(\w+\s+)*fun\b"],
     fp=["private fun getMap(): MutableMap<Any, E> = m\nfun MutableSet<String>.newNonce() = 1\nfun merge(ranges: MutableList<R>): List<R> = ranges\n"],
     mode="ai-confirm", ai="Do callers not need to mutate the returned collection?")
conv("TRY-FINALLY-CLOSE", "try/finally close() instead of use {}", "idioms.html", "Java 7's try-with-resources",
     '((try_expression (finally_block) @f) @match (#match? @f "\\\\.close\\\\(\\\\)"))',
     "fun f(r: Reader) {\n    try { r.read() } finally { r.close() }\n}\n", "fun f(r: Reader) {\n    r.use { it.read() }\n}\n",
     "use {} closes the resource and preserves suppressed exceptions.", sev="info", cat="style")
conv("THROW-IAE-REQUIRE", "if (...) throw IllegalArgumentException/IllegalStateException", STD + "kotlin/require.html", "Throws an IllegalArgumentException if the value is false.",
     '((if_expression (throw_expression (call_expression . (identifier) @match))) (#match? @match "^(IllegalArgumentException|IllegalStateException)$"))',
     'fun f(n: Int) {\n    if (n < 0) throw IllegalArgumentException("neg")\n}\n', 'fun f(n: Int) {\n    require(n >= 0) { "neg" }\n}\n',
     "Use require()/check() (also gives smart-casts via contracts).", sev="info", cat="style")
conv("NULL-OR-EMPTY", "x == null || x.isEmpty()", STD + "kotlin.text/is-null-or-empty.html", "Returns true if this nullable char sequence is either null or empty.",
     '((binary_expression left: (binary_expression left: (identifier) @a) right: (call_expression (navigation_expression . (identifier) @b . (identifier) @m))) @match (#eq? @a @b) (#match? @m "^(isEmpty|isBlank)$") (#match? @match "==\\\\s*null\\\\s*\\\\|\\\\|"))',
     "fun f(s: String?) = s == null || s.isEmpty()\n", "fun f(s: String?) = s.isNullOrEmpty()\n", "Use isNullOrEmpty()/isNullOrBlank().", sev="info", cat="style")
conv("MULTI-DOLLAR", "${'$'} escapes (use multi-dollar interpolation)", "coding-conventions.html", "Use multi-dollar string interpolation to treat the dollar sign chars $ as string literals",
     """((string_literal) @match (#match? @match "\\\\$\\\\{'\\\\$'\\\\}"))""", "val schema = \"${'$'}schema\"\n", "val schema = $$\"$schema\"\n",
     "Since Kotlin 2.2, $$\"...\" treats single $ literally.", sev="info", cat="modernization", kind="modernization", applies={"kotlin": ">=2.2"}, docv="Kotlin 2.2")
dep("NATIVE-FREEZE", "Kotlin/Native freezing APIs", "1.7.20", "compatibility-guide-21.html", "Deprecate freezing-related APIs in Kotlin/Native",
    '((call_expression (navigation_expression (_) (identifier) @match)) (#match? @match "^(freeze|ensureNeverFrozen)$"))\n((navigation_expression (_) (identifier) @match) (#eq? @match "isFrozen"))\n((annotation (user_type (identifier) @match)) (#eq? @match "SharedImmutable"))',
    "val cfg = Config().freeze()\n", "val cfg = Config()\n", "The new memory manager makes freezing unnecessary; it is an error since Kotlin 2.1.", sev="major")
dep("DATA-COPY-VISIBILITY", "Data class with non-public constructor exposes copy()", "2.0.20", "whatsnew2020.html", "@ConsistentCopyVisibility to opt in to the behavior",
    '((class_declaration (modifiers (class_modifier) @d) (primary_constructor (modifiers (visibility_modifier) @v))) @match (#eq? @d "data") (#match? @v "^(private|internal)$") (#not-match? @match "@(ConsistentCopyVisibility|ExposedCopyVisibility)"))',
    "data class Money private constructor(val cents: Long)\n", "@ConsistentCopyVisibility\ndata class Money private constructor(val cents: Long)\n",
    "copy() is public and bypasses the private constructor; its visibility will change.", kind="migration")
dep("KOTLINX-DATETIME-INSTANT", "kotlinx.datetime.Instant/Clock (moved to kotlin.time)", "2.1.20", "whatsnew2120.html", "kotlinx.datetime.Instant class as kotlin.time.Instant",
    '((import (qualified_identifier) @match) (#match? @match "^kotlinx\\\\.datetime\\\\.(Instant|Clock)$"))', "import kotlinx.datetime.Instant\n", "import kotlin.time.Instant\n",
    "Instant and Clock are now in the standard library (kotlin.time).", sev="info", kind="modernization")
dep("ENUM-DECLARING-CLASS", "Enum.declaringClass", "1.9", "compatibility-guide-19.html", "Deprecate and remove Enum.declaringClass synthetic property",
    '((navigation_expression (_) (identifier) @match) (#eq? @match "declaringClass"))', "val c = Color.RED.declaringClass\n", "val c = Color.RED.declaringJavaClass\n",
    "Use declaringJavaClass.", sev="major", kind="removal")
dep("GRADLE-STDLIB-DEPENDENCY", "Explicit kotlin-stdlib dependency", "1.4", "gradle-configure-project.html", "A dependency on the standard library (stdlib) is added automatically to each source set.",
    '((string_literal) @match (#match? @match "org\\\\.jetbrains\\\\.kotlin:kotlin-stdlib|^\\"stdlib(-jdk[78]|-common)?\\"$"))',
    'dependencies {\n    implementation(kotlin("stdlib-jdk8"))\n}\n', 'dependencies {\n    implementation(libs.ktor.core)\n}\n',
    "The Kotlin Gradle plugin adds the stdlib (matching its version) automatically; kotlin-stdlib-jdk7/8 and -common are merged/removed.", sev="info", kind="modernization", files=KTS)
dep("GRADLE-MPP-PRESETS", "Multiplatform target presets / fromPreset / jvmWithJava", "1.9.20", "multiplatform/multiplatform-compatibility-guide.html", "all presets-related APIs are now deprecated",
    '((identifier) @match (#match? @match "^(presets|fromPreset|targetPresets|jvmWithJava)$"))',
    "kotlin {\n    targets {\n        fromPreset(presets.iosArm64, \"ios\")\n    }\n}\n", "kotlin {\n    iosArm64(\"ios\")\n}\n", "Use the target functions (iosArm64(), jvm { withJava() }); presets are errors since 2.0.",
    sev="major", files=KTS)
dep("GRADLE-REMOVED-COMPILER-OPTIONS", "Removed Kotlin compiler/Gradle options (useIR, jdkHome, noStdlib, -Xuse-experimental)", "1.7", "compatibility-guide-17.html", "Remove kotlinOptions.jdkHome compiler option",
    '((assignment left: (_) @match) (#match? @match "(^|\\\\.)(useIR|jdkHome|noStdlib)$"))' + "\n" + '((string_literal) @match (#match? @match "-Xuse-experimental="))',
    "tasks.withType<KotlinCompile> {\n    kotlinOptions.useIR = true\n}\n", "tasks.withType<KotlinCompile> {\n    compilerOptions { jvmTarget.set(JvmTarget.JVM_17) }\n}\n",
    "These options were removed; delete them (use toolchains / -opt-in).", sev="major", kind="removal", files=KTS)

# ------------------------------------------------------------------ Sonar-way checklist gaps (own detection/wording)
AWV = "https://developer.android.com/reference/android/webkit/WebView"
ASTORE = "https://developer.android.com/training/data-storage"
ABCAST = "https://developer.android.com/develop/background-work/background-tasks/broadcasts"
sec("WEBVIEW-DEBUG", "WebView remote debugging enabled", AWV,
    "Enables debugging of web contents (HTML / CSS / JavaScript) loaded into any WebViews of this application",
    '((call_expression (navigation_expression . (identifier) @c . (identifier) @m) (value_arguments . (value_argument (_) @b) .)) @match (#eq? @c "WebView") (#eq? @m "setWebContentsDebuggingEnabled") (#eq? @b "true"))',
    "WebView.setWebContentsDebuggingEnabled(true)\n", "WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)\n",
    "Remote debugging exposes every WebView's DOM, storage and JavaScript to anyone with adb access. Enable it only in debug builds (pass BuildConfig.DEBUG).",
    sev="major", mode="ai-confirm", ai="Is this call reachable in release builds (not wrapped in a BuildConfig.DEBUG / debuggable check)?",
    docv="Android API 36", xref=["sonar:kotlin:S4507"])
sec("EXTERNAL-STORAGE", "File written to external storage", ASTORE,
    "Use the directories within internal storage to save sensitive information that other apps shouldn't access",
    '((call_expression [(identifier) @m (navigation_expression (identifier) @m .)]) @match (#match? @m "^(getExternalStorageDirectory|getExternalStoragePublicDirectory|getExternalFilesDir|getExternalCacheDir)$"))',
    'val f = File(context.getExternalFilesDir(null), "session.json")\n', 'val f = File(context.filesDir, "session.json")\n',
    "External storage can be read by other apps (and by the user over USB on older Android). Keep tokens, personal data and caches of them in internal storage.",
    sev="major", mode="ai-confirm", ai="Is the data written here sensitive (credentials, tokens, personal data, health/financial data)?",
    docv="Android developer guide", xref=["sonar:kotlin:S5324"])
sec("BROADCAST-NO-PERMISSION", "Broadcast sent without a receiver permission", ABCAST, "you can specify a permission parameter",
    '((call_expression [(identifier) @m (navigation_expression (identifier) @m .)] (value_arguments . (value_argument) .)) @match (#match? @m "^(sendBroadcast|sendStickyBroadcast)$"))',
    "context.sendBroadcast(Intent(ACTION_SYNC_DONE).putExtra(\"token\", token))\n",
    "context.sendBroadcast(Intent(ACTION_SYNC_DONE).putExtra(\"token\", token), PERMISSION_SYNC)\n",
    "Any installed app can register for this implicit broadcast and read its extras. Pass a receiver permission, set an explicit package, or use a local mechanism.",
    sev="major", mode="ai-confirm", ai="Is the intent implicit (no setPackage/explicit component) and does it carry data other apps should not see?",
    docv="Android developer guide", xref=["sonar:kotlin:S5320"])

# ------------------------------------------------------------------ coding conventions (kotlinlang.org; Sonar kotlin keys as xref only)
P("LIFT-RETURN", "return repeated on both branches of if/when", K + "coding-conventions.html", "Prefer using if for a ternary operator",
  "(if_expression (return_expression) (return_expression) @match)",
  "fun f(x: Boolean): Int {\n    if (x) return 1 else return 2\n}\n",
  "fun f(x: Boolean): Int {\n    return if (x) 1 else 2\n}\n",
  "Both branches return: lift return in front of if so the if is the expression.",
  sev="info", kind="best-practice", cat="maintainability", files=SRC,
  quote="In Kotlin, if is an expression, i.e. it returns a value. Therefore there is no ternary operator (condition ? then : else), because ordinary if works fine in this role.",
  xref=["sonar:kotlin:S6510"])
P("GETTER-SETTER-PROPERTY", "Java-style getX/setX instead of a property", K + "coding-conventions.html", "Prefer using a property rather than a Java-style getter",
  '((function_declaration name: (identifier) @n (function_value_parameters) @p) @match (#match? @n "^get[A-Z]") (#eq? @p "()"))',
  "class User {\n    private var name: String = \"\"\n    fun getName(): String = name\n}\n",
  "class User {\n    var name: String = \"\"\n}\n",
  "A no-arg getX() is a Java getter: expose a Kotlin property instead (the compiler still generates getX for Java callers).",
  sev="info", kind="best-practice", cat="maintainability", files=SRC, mode="ai-confirm",
  ai="Is this a Java-style getter for a backing field (not an expensive computation, factory, or Java override that must stay a function)?",
  quote="In some cases functions with no arguments might be interchangeable with read-only properties.",
  xref=["sonar:kotlin:S6512"])

RULES = P.R

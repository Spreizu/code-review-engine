"""Gradle pack: every rule ships as a Groovy DSL (build.gradle, groovy grammar) and/or Kotlin DSL (build.gradle.kts,
kotlin grammar) variant. Sources: docs.gradle.org upgrading guides (6.x->7, 7.x->8, 8.x, 8->9, 9.x), Best Practices,
task configuration avoidance, repository/dependency docs. Version dimension `gradle` comes from
gradle/wrapper/gradle-wrapper.properties (distributionUrl)."""
from specs._common import Pack, PLACEHOLDER_RE

U = "https://docs.gradle.org/current/userguide/"
DSL = "https://docs.gradle.org/current/dsl/"
P = Pack("GRADLE", "groovy", "Gradle 9.8", {"gradle": "*"}, files=["**/*.gradle"])
GF, KF = ["**/*.gradle"], ["**/*.gradle.kts"]
SETTINGS_G, SETTINGS_K = ["**/settings.gradle"], ["**/settings.gradle.kts"]
STR = "[(character_literal) (string_literal)]"


def gcall(names, extra=""):
    return f'([(juxt_function_call name: (identifier) @match) (method_invocation name: (identifier) @match)] (#match? @match "^({names})$"){extra})'


def kcall(names):
    return f'((call_expression . (identifier) @match) (#match? @match "^({names})$"))'


def gid(names):
    return f'((identifier) @match (#match? @match "^({names})$"))'


def both(id, title, page, needle, gq, kq, gbad, ggood, kbad, kgood, msg, *, ver=None, applies=None, gfiles=GF, kfiles=KF, **kw):
    url = page if page.startswith("http") else U + page
    ap = applies or ({"gradle": f">={ver}"} if ver else None)
    docv = kw.pop("docv", f"Gradle {ver}" if ver else "Gradle 9.8")
    if gq:
        P(id + "-GROOVY", title + " (Groovy DSL)", url, needle, gq, gbad, ggood, msg, applies=ap, lang="groovy", files=gfiles, docv=docv, **kw)
    if kq:
        P(id + "-KTS", title + " (Kotlin DSL)", url, needle, kq, kbad, kgood, msg, applies=ap, lang="kotlin", files=kfiles, docv=docv, **kw)


R = dict(kind="removal", cat="removal", sev="critical")
D = dict(kind="deprecation", cat="deprecation", sev="major")

# ------------------------------------------------------------------ removals (7.0, 8.0, 9.0)
both("COMPILE-CONFIGURATION", "compile/runtime/testCompile/testRuntime configurations", "upgrading_version_6.html",
     "the compile and runtime configurations to declare dependencies",
     f'((juxt_function_call name: (identifier) @match args: (argument_list {STR})) (#match? @match "^(compile|runtime|testCompile|testRuntime)$"))',
     '((call_expression . (identifier) @match (value_arguments (value_argument (string_literal)))) (#match? @match "^(compile|runtime|testCompile|testRuntime)$"))',
     "dependencies {\n    compile 'org.slf4j:slf4j-api:2.0.17'\n}\n", "dependencies {\n    implementation 'org.slf4j:slf4j-api:2.0.17'\n}\n",
     'dependencies {\n    compile("org.slf4j:slf4j-api:2.0.17")\n}\n', 'dependencies {\n    implementation("org.slf4j:slf4j-api:2.0.17")\n}\n',
     "These configurations were removed in Gradle 7.0; use implementation/api/runtimeOnly/testImplementation.", ver="7.0", **R)
both("MAVEN-PLUGIN", "Legacy maven plugin", "upgrading_version_6.html", "The maven plugin has been removed. You should use the maven-publish plugin instead.",
     f'((juxt_function_call name: (identifier) @n args: (argument_list (map_item key: (identifier) @k value: {STR} @match))) (#eq? @n "apply") (#eq? @k "plugin") (#match? @match "^.maven.$"))\n'
     f'((juxt_function_call name: (identifier) @n args: (argument_list {STR} @match)) (#eq? @n "id") (#match? @match "^.maven.$"))',
     '((call_expression . (identifier) @n (value_arguments (value_argument (string_literal (string_content) @match)))) (#match? @n "^(id|apply)$") (#eq? @match "maven"))',
     "apply plugin: 'maven'\n", "apply plugin: 'maven-publish'\n", 'plugins {\n    id("maven")\n}\n', 'plugins {\n    id("maven-publish")\n}\n',
     "The maven plugin (and uploadArchives) was removed in 7.0; use maven-publish.", ver="7.0", **R)
both("UPLOAD-ARCHIVES", "uploadArchives task", "upgrading_version_6.html", "The uploadArchives task was used in combination with the legacy Ivy or Maven publishing mechan",
     gid("uploadArchives"), gid("uploadArchives"), "uploadArchives {\n    repositories { }\n}\n", "publishing {\n    repositories { }\n}\n",
     "tasks.named(\"uploadArchives\")\nuploadArchives {\n}\n", "publishing {\n    repositories { }\n}\n", "Removed in 7.0; configure publishing {} with maven-publish/ivy-publish.",
     ver="7.0", **R)
both("ARCHIVE-TASK-PROPERTIES", "classifier/baseName/appendix/destinationDir on archive tasks", "upgrading_version_7.html",
     "classifier , destinationDir , extension and version properties of the AbstractArchiveTask task type have been removed.",
     '([(assignment_expression left: (identifier) @match) (juxt_function_call name: (identifier) @match)] (#match? @match "^(classifier|baseName|appendix|destinationDir|archiveName)$"))',
     '((assignment left: (identifier) @match) (#match? @match "^(classifier|baseName|appendix|destinationDir|archiveName)$"))',
     "jar {\n    classifier = 'sources'\n}\n", "jar {\n    archiveClassifier = 'sources'\n}\n", 'tasks.jar {\n    classifier = "sources"\n}\n',
     'tasks.jar {\n    archiveClassifier.set("sources")\n}\n', "Removed in 8.0; use archiveClassifier/archiveBaseName/archiveAppendix/destinationDirectory/archiveFileName.",
     ver="8.0", **R)
both("MAIN-CLASS-NAME", "application mainClassName", "upgrading_version_7.html", "mainClassName property of the JavaApplication interface has been removed. Use the mainClass property instead.",
     gid("mainClassName"), gid("mainClassName"), "application {\n    mainClassName = 'app.Main'\n}\n", "application {\n    mainClass = 'app.Main'\n}\n",
     'application {\n    mainClassName = "app.Main"\n}\n', 'application {\n    mainClass.set("app.Main")\n}\n', "Removed in 8.0; use mainClass.", ver="8.0", **R)
both("JCENTER-REMOVED", "jcenter() repository", "upgrading_major_version_9.html", "Removal of deprecated jcenter()",
     gcall("jcenter"), kcall("jcenter"), "repositories {\n    jcenter()\n}\n", "repositories {\n    mavenCentral()\n}\n", "repositories {\n    jcenter()\n}\n",
     "repositories {\n    mavenCentral()\n}\n", "jcenter() was removed in Gradle 9 (JCenter is read-only/sunset); use mavenCentral().", ver="9.0", **R)
both("JCENTER-DEPRECATED", "jcenter() repository", "upgrading_version_6.html", "jcenter() convenience method is now deprecated",
     gcall("jcenter"), kcall("jcenter"), "repositories {\n    jcenter()\n}\n", "repositories {\n    mavenCentral()\n}\n", "repositories {\n    jcenter()\n}\n",
     "repositories {\n    mavenCentral()\n}\n", "jcenter() is deprecated (7.x/8.x) and removed in 9.0.", applies={"gradle": ">=7.0 <9.0"}, docv="Gradle 7.0", **D)
both("PROJECT-EXEC", "Project.exec / javaexec", "upgrading_major_version_9.html", "Project#exec , Project#javaexec , and script-level counterparts",
     '((method_invocation !object name: (identifier) @match body: (closure)) (#match? @match "^(exec|javaexec)$"))\n'
     '((method_invocation object: (identifier) @p name: (identifier) @match) (#eq? @p "project") (#match? @match "^(exec|javaexec)$"))',
     '((call_expression . (identifier) @match (annotated_lambda)) (#match? @match "^(exec|javaexec)$"))\n'
     '((call_expression (navigation_expression . (identifier) @p . (identifier) @match) (annotated_lambda)) (#eq? @p "project") (#match? @match "^(exec|javaexec)$"))',
     "tasks.register('ls') {\n    doLast {\n        exec { commandLine 'ls' }\n    }\n}\n",
     "abstract class Ls extends DefaultTask {\n    @Inject abstract ExecOperations getExecOps()\n    @TaskAction void run() { execOps.exec { commandLine 'ls' } }\n}\n",
     'tasks.register("ls") {\n    doLast {\n        exec { commandLine("ls") }\n    }\n}\n', 'val out = providers.exec { commandLine("ls") }.standardOutput.asText\n',
     "Project.exec/javaexec were removed in 9.0; inject ExecOperations in tasks or use providers.exec at configuration time.", ver="9.0", **R)
both("ARCHIVES-BASE-NAME", "archivesBaseName (base plugin convention)", "upgrading_major_version_9.html", "BasePluginConvention Replaced by project.base extension",
     gid("archivesBaseName"), gid("archivesBaseName"), "archivesBaseName = 'app'\n", "base {\n    archivesName = 'app'\n}\n", 'archivesBaseName = "app"\n',
     'base {\n    archivesName.set("app")\n}\n', "Plugin conventions were removed in 9.0; use base { archivesName }.", ver="9.0", **R)
both("JAVA-CONVENTION-PROPERTIES", "Project-level sourceCompatibility/targetCompatibility (java convention)", "upgrading_version_8.html",
     "The convention properties the java plugin contributed have been deprecated and scheduled for removal in Gradle 9.0.0.",
     '((program (expression_statement (assignment_expression left: (identifier) @match))) (#match? @match "^(sourceCompatibility|targetCompatibility|docsDirName|testResultsDirName|testReportDirName|libsDirName|distsDirName)$"))',
     '((source_file (assignment left: (identifier) @match)) (#match? @match "^(sourceCompatibility|targetCompatibility)$"))',
     "sourceCompatibility = 17\n", "java {\n    sourceCompatibility = JavaVersion.VERSION_17\n}\n", "sourceCompatibility = JavaVersion.VERSION_17\n",
     "java {\n    toolchain.languageVersion.set(JavaLanguageVersion.of(17))\n}\n", "Java plugin conventions were removed in 9.0; configure them in java {} (or use a toolchain).",
     ver="9.0", **R)
both("CONVENTION-API", "Project.convention / getConvention()", "upgrading_major_version_9.html", "Removal of conventions",
     gid("convention|getConvention"), gid("convention|getConvention"), "def jc = project.convention.getPlugin(JavaPluginConvention)\n",
     "def java = project.extensions.getByType(JavaPluginExtension)\n", "val jc = project.convention.getPlugin(JavaPluginConvention::class.java)\n",
     "val java = project.extensions.getByType<JavaPluginExtension>()\n", "The convention API was removed in 9.0; use extensions.", ver="9.0", **R,
     filters=[r"file.has_re:\b(convention|getConvention\(\))\s*\.\s*(getPlugin|findPlugin|plugins|getByType)\b"])
both("KTS-STRING-TASK-INVOKE", "\"name\"() task reference syntax", "upgrading_major_version_9.html", "Removal of \"name\"() task reference syntax in Kotlin DSL",
     None, '(call_expression . (call_expression . (string_literal) @match (value_arguments)))\n(call_expression . (string_literal) @match (annotated_lambda))',
     None, None, '"test"(Test::class) {\n    useJUnitPlatform()\n}\n', 'tasks.named<Test>("test") {\n    useJUnitPlatform()\n}\n',
     "Use tasks.named(\"name\") / tasks.named<T>(\"name\").", ver="9.0", **R)
both("GRADLE-ENTERPRISE-BLOCK", "gradleEnterprise {} block in settings", "upgrading_major_version_9.html", "Removal of the gradle-enterprise plugin block extension in Kotlin DSL",
     None, kcall("gradleEnterprise"), None, None, 'gradleEnterprise {\n    buildScan { }\n}\n', 'develocity {\n    buildScan { }\n}\n',
     "Use the com.gradle.develocity plugin and develocity {}.", ver="9.0", kfiles=SETTINGS_K + KF, **R)
both("KOTLIN-DSL-JVMTARGET", "kotlinDslPluginOptions.jvmTarget", "upgrading_major_version_9.html", "Removal of kotlinDslPluginOptions.jvmTarget",
     None, gid("kotlinDslPluginOptions"), None, None, 'kotlinDslPluginOptions {\n    jvmTarget.set("17")\n}\n', 'kotlin {\n    jvmToolchain(17)\n}\n',
     "Removed in 9.0; configure a Java toolchain.", ver="9.0", **R)
both("EAGER-ARTIFACT-ACCESSOR", "Eager artifact configuration accessors", "upgrading_major_version_9.html", "Removal of eager artifact configuration accessors in Kotlin DSL",
     None, '((call_expression (navigation_expression . (identifier) @a . (identifier) @match) (value_arguments (value_argument (call_expression)))) (#eq? @a "artifacts") (#match? @match "^(archives|default|apiElements|runtimeElements)$"))',
     None, None, "artifacts {\n}\nartifacts.archives(tasks.jar.get())\n", "artifacts {\n    add(\"archives\", tasks.jar)\n}\n",
     "Eager artifact accessors were removed in 9.0; pass the TaskProvider via add(name, provider).", ver="9.0", **R)

# ------------------------------------------------------------------ deprecations (8.x, 9.x)
both("BUILDDIR", "Project.buildDir", "upgrading_version_8.html", "Deprecated Project.buildDir is to be replaced by Project.layout.buildDirectory",
     gid("buildDir") + '\n((string_literal) @match (#match? @match "\\\\$\\\\{?buildDir\\\\b"))', gid("buildDir"), "def out = file(\"$buildDir/out\")\n", "def out = layout.buildDirectory.dir('out')\n",
     'val out = file("$buildDir/out")\nval b = buildDir\n', 'val out = layout.buildDirectory.dir("out")\n', "buildDir is eager and deprecated (8.3); use layout.buildDirectory.",
     ver="8.3", **D)
both("MULTI-STRING-NOTATION", "Multi-string (group:/name:/version:) dependency notation", "upgrading_version_9.html",
     "the multi-string dependency notation used in dependency management has been deprecated and will no longer be permitted in Gradle 10.",
     '((juxt_function_call args: (argument_list (map_item key: (identifier) @match))) (#eq? @match "group"))',
     '((call_expression (value_arguments (value_argument (identifier) @match (string_literal)))) (#eq? @match "group"))',
     "dependencies {\n    implementation group: 'org.slf4j', name: 'slf4j-api', version: '2.0.17'\n}\n", "dependencies {\n    implementation 'org.slf4j:slf4j-api:2.0.17'\n}\n",
     'dependencies {\n    implementation(group = "org.slf4j", name = "slf4j-api", version = "2.0.17")\n}\n', 'dependencies {\n    implementation("org.slf4j:slf4j-api:2.0.17")\n}\n',
     "Deprecated in 9.1, removed in 10; use \"group:name:version\" or a version-catalog alias.", ver="9.1", **D)
both("TEST-CLOSURE-LISTENERS", "Closure-taking Test listener methods", "upgrading_version_9.html", "AbstractTestTask.onOutput(Closure) can be replaced with",
     '((method_invocation name: (identifier) @match body: (closure)) (#match? @match "^(onOutput|beforeTest|afterTest|beforeSuite|afterSuite)$"))', None,
     "test {\n    afterTest { desc, result -> println desc }\n}\n", "test {\n    addTestListener(new MyListener())\n}\n", None, None,
     "Deprecated in 9.4 (removed in 10); register TestListener/TestOutputListener implementations.", ver="9.4", **D)
both("PROJECT-GETPROPERTIES", "project.properties / getProperties()", "upgrading_version_9.html",
     "Project.getProperties() — calling getProperties() or accessing the properties property on a Project instance.",
     '((method_invocation name: (identifier) @match) (#eq? @match "getProperties"))\n((field_access object: (identifier) @p field: (identifier) @match) (#eq? @p "project") (#eq? @match "properties"))',
     '((navigation_expression . (identifier) @p . (identifier) @match) (#eq? @p "project") (#eq? @match "properties"))',
     "def v = project.getProperties().get('x')\n", "def v = providers.gradleProperty('x').get()\n", 'val v = project.properties["x"]\n',
     'val v = providers.gradleProperty("x").get()\n', "Deprecated in 9.6; read individual properties with findProperty() or providers.gradleProperty().", ver="9.6", **D)
both("CONFIGURATION-VISIBLE", "Configuration.visible", "upgrading_version_9.html", "Deprecation of the Configuration.visible property",
     '((assignment_expression left: (identifier) @match) (#eq? @match "visible"))', '((assignment left: (identifier) @match) (#match? @match "^(visible|isVisible)$"))',
     "configurations {\n    custom {\n        visible = false\n    }\n}\n", "configurations {\n    custom {\n        canBeConsumed = false\n    }\n}\n",
     'configurations.create("custom") {\n    isVisible = false\n}\n', 'configurations.create("custom") {\n    isCanBeConsumed = false\n}\n',
     "visible has no effect since 9.0 and is deprecated (9.1).", ver="9.1", sev="minor", kind="deprecation", cat="deprecation", filters=["file.has_re:configurations"])
both("ARCHIVES-CONFIGURATION", "Adding artifacts to the archives configuration", "upgrading_version_9.html",
     "The archives configuration added by the base plugin has been deprecated and will be removed in Gradle 10.0.0.",
     '((juxt_function_call name: (identifier) @match) (#eq? @match "archives"))\n((local_variable_declaration type: (type_identifier) @match) (#eq? @match "archives"))', '((call_expression . (identifier) @match) (#eq? @match "archives"))',
     "artifacts {\n    archives sourcesJar\n}\n", "tasks.named('assemble') {\n    dependsOn sourcesJar\n}\n", "artifacts {\n    archives(sourcesJar)\n}\n",
     'tasks.named("assemble") {\n    dependsOn(sourcesJar)\n}\n', "Deprecated in 9.1; make assemble depend on the task instead.", ver="9.1", **D)
both("REPO-MAP-OVERLOADS", "flatDir(Map)/mavenCentral(Map)", "upgrading_version_9.html",
     "The map-argument overloads RepositoryHandler.flatDir(Map) and RepositoryHandler.mavenCentral(Map) are deprecated",
     '((juxt_function_call name: (identifier) @match args: (argument_list (map_item))) (#match? @match "^(flatDir|mavenCentral)$"))\n((method_invocation name: (identifier) @match arguments: (argument_list (map_item))) (#match? @match "^(flatDir|mavenCentral)$"))',
     '((call_expression . (identifier) @match (value_arguments (value_argument (infix_expression (_) (identifier) @to (_))))) (#match? @match "^(flatDir|mavenCentral)$") (#eq? @to "to"))',
     "repositories {\n    flatDir dirs: 'libs'\n}\n", "repositories {\n    flatDir { dirs 'libs' }\n}\n", 'repositories {\n    flatDir("dirs" to "libs")\n    mavenCentral(mapOf("name" to "c"))\n}\n',
     'repositories {\n    flatDir { dirs("libs") }\n}\n', "Deprecated in 9.6; use the action-based overloads.", ver="9.6", **D,
     filters=[])
both("KTS-DELEGATED-PROPERTIES", "Kotlin DSL property delegates (by registering/getting/existing/creating)", "upgrading_version_9.html",
     "All Kotlin DSL property delegate extensions have been deprecated and will be removed in Gradle 10.",
     None, '((property_delegate (call_expression (navigation_expression (_) (identifier) @match))) (#match? @match "^(registering|creating|existing|getting)$"))\n((property_delegate (navigation_expression (_) (identifier) @match)) (#match? @match "^(registering|creating|existing|getting)$"))\n((property_delegate (identifier) @match) (#match? @match "^(project|extra)$"))', None, None,
     "val integTest by tasks.registering(Test::class)\n", 'val integTest = tasks.register<Test>("integTest")\n',
     "Deprecated in 9.6; use explicit register/named/getByName calls.", ver="9.6", **D)
both("ARTIFACT-URLS", "artifactUrls on Maven repositories", "upgrading_version_9.html", "The artifactUrls family",
     gid("artifactUrls"), gid("artifactUrls"), "repositories {\n    maven {\n        url = 'https://repo'\n        artifactUrls 'https://mirror'\n    }\n}\n",
     "repositories {\n    maven { url = 'https://repo' }\n    maven { url = 'https://mirror' }\n}\n", 'repositories {\n    maven {\n        url = uri("https://repo")\n        artifactUrls("https://mirror")\n    }\n}\n',
     'repositories {\n    maven { url = uri("https://repo") }\n    maven { url = uri("https://mirror") }\n}\n', "Deprecated in 9.6; declare separate repositories.", ver="9.6", **D)
both("CONFIG-TIME-PROCESS", "External process started at configuration time", "upgrading_version_9.html",
     "Starting an external process at configuration time with ExecOperations or the Java and Groovy standard APIs directly is now dep",
     '((method_invocation object: (_) @o name: (identifier) @match) (#match? @match "^(execute)$") (#match? @o "^[\'\\"]"))',
     '((call_expression (navigation_expression (call_expression (navigation_expression . (identifier) @r . (identifier) @g)) (identifier) @match)) (#eq? @r "Runtime") (#eq? @g "getRuntime") (#eq? @match "exec"))\n((call_expression . (identifier) @match (value_arguments (value_argument (string_literal)))) (#eq? @match "ProcessBuilder"))',
     "def sha = 'git rev-parse HEAD'.execute().text.trim()\n", "def sha = providers.exec { commandLine 'git', 'rev-parse', 'HEAD' }.standardOutput.asText.get().trim()\n",
     'val sha = Runtime.getRuntime().exec("git rev-parse HEAD")\n', 'val sha = providers.exec { commandLine("git", "rev-parse", "HEAD") }.standardOutput.asText.get().trim()\n',
     "Deprecated in 9.8 (breaks configuration cache inputs); use providers.exec {}.", ver="9.8", **D,
     filters=["file.lacks_re:@TaskAction"])
both("CONFIG-CACHE-UNSAFE-PROPERTY", "org.gradle.unsafe.configuration-cache flag in scripts", "upgrading_version_8.html",
     "were renamed, in some cases, by removing the unsafe part of the name.",
     '([(character_literal) (string_literal)] @match (#match? @match "org\\\\.gradle\\\\.unsafe\\\\.configuration-cache"))',
     '((string_content) @match (#match? @match "org\\\\.gradle\\\\.unsafe\\\\.configuration-cache"))',
     "if (gradle.startParameter.projectProperties['org.gradle.unsafe.configuration-cache']) {}\n", "if (gradle.startParameter.configurationCache.get()) {}\n",
     'val cc = providers.gradleProperty("org.gradle.unsafe.configuration-cache")\n', 'val cc = providers.gradleProperty("org.gradle.configuration-cache")\n',
     "The unsafe configuration-cache property names were renamed (8.1).", ver="8.1", sev="minor", kind="deprecation", cat="deprecation")

# ------------------------------------------------------------------ best practices (docs.gradle.org Best Practices)
B = dict(kind="best-practice", cat="best-practice", sev="minor")
both("TASKS-CREATE-EAGER", "Eager task creation/lookup (create/getByName/all)", "task_configuration_avoidance.html",
     "Instead of returning a task instance, the register(…​) method returns a TaskProvider",
     '((method_invocation object: (identifier) @t name: (identifier) @match) (#eq? @t "tasks") (#match? @match "^(create|getByName|getAt|all|whenTaskAdded)$"))',
     '((navigation_expression . (identifier) @t . (identifier) @match) (#eq? @t "tasks") (#match? @match "^(create|getByName|getAt|all|whenTaskAdded)$"))',
     "tasks.create('docs') {\n    doLast { }\n}\n", "tasks.register('docs') {\n    doLast { }\n}\n", 'tasks.create("docs") {\n    doLast { }\n}\n',
     'tasks.register("docs") {\n    doLast { }\n}\n', "Eager APIs configure tasks even when they never run; use register/named/configureEach.",
     xref=["sonar:kotlin:S6623", "sonar:kotlin:S6634"], **B)
both("TASK-GROUP-DESCRIPTION", "Task registered without group and description", "more_about_tasks.html",
     "You can assign a group and description to a task",
     '((method_invocation object: (identifier) @t name: (identifier) @m) @match (#eq? @t "tasks") (#match? @m "^(register|create)$"))',
     '((call_expression (call_expression (navigation_expression . (identifier) @t . (identifier) @m)) (annotated_lambda)) @match (#eq? @t "tasks") (#match? @m "^(register|create)$"))',
     "tasks.register('docs') {\n    doLast { }\n}\n",
     "tasks.register('docs') {\n    group = 'documentation'\n    description = 'Build the docs'\n    doLast { }\n}\n",
     'tasks.register("docs") {\n    doLast { }\n}\n',
     'tasks.register("docs") {\n    group = "documentation"\n    description = "Build the docs"\n    doLast { }\n}\n',
     "A task without group and description is hard to find in `gradle tasks`: set both when you register it.",
     xref=["sonar:kotlin:S6626"], filters=[r"node.lacks_re:group\s*=", r"node.lacks_re:description\s*="],
     mode="ai-confirm", ai="Is this a user-facing task (not an internal wiring task) that should show up in `gradle tasks`?",
     quote="You can also assign a group and description to a task.", **B)
both("TASK-KEYWORD", "task name { } (eager task declaration)", "task_configuration_avoidance.html", "Instead of returning a task instance, the register(…​) method returns a TaskProvider",
     '((juxt_function_call name: (identifier) @match) (#eq? @match "task"))', None, "task hello {\n    doLast { println 'hi' }\n}\n",
     "tasks.register('hello') {\n    doLast { println 'hi' }\n}\n", None, None, "The task keyword creates the task eagerly; use tasks.register.", **B)
both("AFTER-EVALUATE", "afterEvaluate {}", "best_practices_general.html", "Avoid afterEvaluate",
     gcall("afterEvaluate"), kcall("afterEvaluate"), "afterEvaluate {\n    println version\n}\n", "plugins.withId('java') {\n    println 'java applied'\n}\n",
     "afterEvaluate {\n    println(version)\n}\n", 'pluginManager.withPlugin("java") {\n    println("java applied")\n}\n',
     "afterEvaluate introduces ordering bugs; use lazy properties and pluginManager.withPlugin().", **B)
both("DEPENDS-ON", "Explicit dependsOn between tasks", "best_practices_tasks.html", "Avoid DependsOn",
     gcall("dependsOn"), kcall("dependsOn"), "tasks.register('pkg', Zip) {\n    dependsOn 'gen'\n    from 'build/gen'\n}\n",
     "tasks.register('pkg', Zip) {\n    from tasks.named('gen')\n}\n", 'tasks.register<Zip>("pkg") {\n    dependsOn("gen")\n    from("build/gen")\n}\n',
     'tasks.register<Zip>("pkg") {\n    from(tasks.named("gen"))\n}\n', "Wire task outputs to inputs instead of dependsOn, so dependencies are inferred.",
     sev="info", kind="best-practice", cat="best-practice", mode="ai-confirm",
     ai="Is dependsOn used to order tasks whose outputs could instead be wired as inputs (not a lifecycle task like assemble/check)?")
both("PROJECT-IN-TASK-ACTION", "project accessed inside doLast/doFirst", "best_practices_tasks.html", "Don’t access a Project instance during Task Execution",
     '((method_invocation name: (identifier) @a body: (closure) @match) (#match? @a "^(doLast|doFirst)$") (#match? @match "\\\\bproject\\\\."))',
     '((call_expression . (identifier) @a (annotated_lambda) @match) (#match? @a "^(doLast|doFirst)$") (#match? @match "\\\\bproject\\\\."))',
     "tasks.register('show') {\n    doLast { println project.version }\n}\n", "tasks.register('show') {\n    def v = project.version\n    doLast { println v }\n}\n",
     'tasks.register("show") {\n    doLast { println(project.version) }\n}\n', 'tasks.register("show") {\n    val v = project.version\n    doLast { println(v) }\n}\n',
     "Project access at execution time is incompatible with the configuration cache.", sev="major", kind="best-practice", cat="best-practice")
both("KOTLIN-STDLIB-EXPLICIT", "Explicit kotlin-stdlib dependency", "best_practices_dependencies.html", "Don’t Explicitly Depend on the Kotlin Standard Library",
     '([(character_literal) (string_literal)] @match (#match? @match "org\\\\.jetbrains\\\\.kotlin:kotlin-stdlib"))', '((string_content) @match (#match? @match "^org\\\\.jetbrains\\\\.kotlin:kotlin-stdlib"))',
     "dependencies {\n    implementation 'org.jetbrains.kotlin:kotlin-stdlib:2.4.10'\n}\n", "dependencies {\n    implementation 'com.squareup.okio:okio:3.16.0'\n}\n",
     'dependencies {\n    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.4.10")\n}\n', 'dependencies {\n    implementation("com.squareup.okio:okio:3.16.0")\n}\n',
     "The Kotlin Gradle plugin adds the stdlib matching the compiler; an explicit one can drift.", **B)
both("REPOS-IN-BUILD-SCRIPT", "repositories {} declared in a project build script", "best_practices_dependencies.html", "Set up your Dependency Repositories in the Settings file",
     '((program (expression_statement (method_invocation name: (identifier) @match body: (closure)))) (#eq? @match "repositories"))',
     '((source_file (call_expression . (identifier) @match (annotated_lambda))) (#eq? @match "repositories"))',
     "repositories {\n    mavenCentral()\n}\n", "dependencies {\n}\n", "repositories {\n    mavenCentral()\n}\n", "dependencies {\n}\n",
     "Declare repositories once in settings (dependencyResolutionManagement).", sev="info", kind="best-practice", cat="best-practice",
     gfiles=["**/build.gradle"], kfiles=["**/build.gradle.kts"])
both("ROOT-PROJECT-NAME", "settings without rootProject.name", "best_practices_general.html", "Always name your root project in the settings.gradle(.kts) file.",
     '(program) @match', '(source_file) @match', "include 'app'\n", "rootProject.name = 'shop'\ninclude 'app'\n", 'include("app")\n',
     'rootProject.name = "shop"\ninclude("app")\n', "Without it the root project name is the checkout directory name.", sev="info", kind="best-practice", cat="best-practice",
     gfiles=SETTINGS_G, kfiles=SETTINGS_K, filters=["file.lacks_re:rootProject\\.name"])
both("ALLPROJECTS", "allprojects {} / subprojects {} cross-project configuration", "best_practices_structuring_builds.html", "Use Convention Plugins for Common Build Logic",
     gcall("allprojects|subprojects"), kcall("allprojects|subprojects"), "subprojects {\n    apply plugin: 'java'\n}\n", "plugins {\n    id 'buildlogic.java-conventions'\n}\n",
     'subprojects {\n    apply(plugin = "java")\n}\n', 'plugins {\n    id("buildlogic.java-conventions")\n}\n',
     "Cross-project configuration couples projects and defeats isolated projects; use convention plugins.", **B)
both("LEGACY-APPLY-PLUGIN", "apply plugin: (legacy plugin application)", "plugins_intermediate.html", "Legacy Plugin Application",
     '((juxt_function_call name: (identifier) @n args: (argument_list (map_item key: (identifier) @match))) (#eq? @n "apply") (#eq? @match "plugin"))',
     '((call_expression . (identifier) @n (value_arguments (value_argument (identifier) @match))) (#eq? @n "apply") (#eq? @match "plugin"))',
     "apply plugin: 'java'\n", "plugins {\n    id 'java'\n}\n", 'apply(plugin = "java")\n', 'plugins {\n    java\n}\n',
     "Use the plugins {} block: type-safe accessors, earlier resolution, version management.", sev="info", kind="modernization", cat="modernization")
both("EAGER-FILE-RESOLUTION", "Configuration resolved during configuration (.files/.resolve()/.singleFile)", "best_practices_tasks.html", "Don’t resolve Configurations before Task Execution",
     '((field_access object: (_) @c field: (identifier) @match) (#match? @c "configurations\\\\.") (#match? @match "^(files|singleFile|asPath)$"))\n((method_invocation object: (_) @c name: (identifier) @match) (#match? @c "configurations\\\\.") (#match? @match "^(resolve|getFiles|getSingleFile|getAsPath)$"))',
     '((navigation_expression (navigation_expression . (identifier) @cf) (identifier) @match) (#eq? @cf "configurations") (#match? @match "^(files|singleFile|asPath)$"))\n((call_expression (navigation_expression (navigation_expression . (identifier) @cf) (identifier) @match)) (#eq? @cf "configurations") (#eq? @match "resolve"))',
     "def cp = configurations.runtimeClasspath.files\n", "def cp = configurations.named('runtimeClasspath')\n", "val cp = configurations.runtimeClasspath.get().files\nval x = configurations.compileClasspath.resolve()\n",
     'val cp = configurations.named("runtimeClasspath")\n', "Resolving at configuration time slows every build and breaks the configuration cache; pass the FileCollection lazily.", sev="major",
     kind="best-practice", cat="performance")
both("PROVIDER-GET-AT-CONFIG", "Provider.get() outside a task action", "best_practices_tasks.html", "Do not call get() on a Provider outside a Task action",
     None, '((call_expression (navigation_expression (call_expression (navigation_expression . (identifier) @p . (identifier) @k)) (identifier) @match) (value_arguments) @a) (#eq? @p "providers") (#match? @k "^(gradleProperty|environmentVariable|systemProperty)$") (#eq? @match "get") (#eq? @a "()"))',
     None, None, 'val token = providers.environmentVariable("TOKEN").get()\n', 'val token = providers.environmentVariable("TOKEN")\n',
     "Call get() only inside task actions; wire the Provider into task properties.", sev="info", kind="best-practice", cat="best-practice", mode="ai-confirm",
     ai="Is get() called at configuration time (script body / configure block) rather than inside doLast/@TaskAction?")

# ------------------------------------------------------------------ security / reproducibility
S = dict(kind="security", cat="security")
S_HTTP = dict(kind="security", cat="security", cwe=["CWE-494", "CWE-829"], owasp=["M2:2024", "MASVS-CODE-3", "A08:2021", "A08:2025"])
S_PIN = dict(kind="security", cat="supply-chain", cwe=["CWE-1104", "CWE-494"], owasp=["M2:2024", "MASVS-CODE-3", "A06:2021", "A03:2025"])
both("INSECURE-REPO-URL", "http:// repository URL", DSL + "org.gradle.api.artifacts.repositories.UrlArtifactRepository.html",
     "Specifies whether it is acceptable to communicate with a repository over an insecure HTTP connection.",
     '((method_invocation name: (identifier) @m body: (closure [(assignment_expression left: (identifier) @u right: [(character_literal) (string_literal)] @match) (juxt_function_call name: (identifier) @u args: (argument_list [(character_literal) (string_literal)] @match))])) (#match? @m "^(maven|ivy)$") (#eq? @u "url") (#match? @match "^.http://"))',
     '((call_expression . (identifier) @m (annotated_lambda (lambda_literal (assignment left: (identifier) @u right: (_) @match)))) (#match? @m "^(maven|ivy)$") (#eq? @u "url") (#match? @match "http://"))',
     "repositories {\n    maven { url = 'http://repo.example.com/m2' }\n}\n", "repositories {\n    maven { url = 'https://repo.example.com/m2' }\n}\n",
     'repositories {\n    maven { url = uri("http://repo.example.com/m2") }\n}\n', 'repositories {\n    maven { url = uri("https://repo.example.com/m2") }\n}\n',
     "Dependencies fetched over HTTP can be tampered with in transit (Gradle 7+ rejects them unless allowInsecureProtocol).", sev="critical", **S_HTTP)
both("ALLOW-INSECURE-PROTOCOL", "allowInsecureProtocol = true", DSL + "org.gradle.api.artifacts.repositories.UrlArtifactRepository.html",
     "Specifies whether it is acceptable to communicate with a repository over an insecure HTTP connection.",
     '((assignment_expression left: (identifier) @match right: (true)) (#eq? @match "allowInsecureProtocol"))\n((juxt_function_call name: (identifier) @match args: (argument_list (true))) (#eq? @match "allowInsecureProtocol"))',
     '((assignment left: (identifier) @match right: (_) @v) (#match? @match "^(isAllowInsecureProtocol|allowInsecureProtocol)$") (#eq? @v "true"))',
     "maven {\n    url = 'https://r'\n    allowInsecureProtocol = true\n}\n", "maven {\n    url = 'https://r'\n}\n",
     'maven {\n    url = uri("https://r")\n    isAllowInsecureProtocol = true\n}\n', 'maven {\n    url = uri("https://r")\n}\n', "Disables Gradle's HTTP protection for this repository.",
     sev="major", **S_HTTP)
both("HARDCODED-REPO-CREDENTIALS", "Hard-coded repository credentials", "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
     "Many organizations have them hardcoded within the source code in plaintext",
     '((assignment_expression left: (identifier) @k right: [(character_literal) (string_literal)] @match) (#match? @k "^(password|username|token|apiKey|secret)$") (#not-match? @match "' + PLACEHOLDER_RE.replace("^(", "^.(") + '"))',
     '((assignment left: (identifier) @k right: (string_literal (string_content) @match)) (#match? @k "^(password|token|apiKey|secret)$") (#not-match? @match "' + PLACEHOLDER_RE + '"))',
     "credentials {\n    password = 's3cr3t-Pass'\n}\n", "credentials {\n    password = providers.gradleProperty('repoPassword').get()\n}\n",
     'credentials {\n    password = "s3cr3t-Pass"\n}\n', 'credentials(PasswordCredentials::class)\n', "Use credentials(PasswordCredentials) / gradle.properties in GRADLE_USER_HOME / env vars.",
     sev="critical", docv="OWASP cheat sheet (2026)", **S)
both("DYNAMIC-VERSION", "Dynamic / latest.* dependency version", "dependency_versions.html", "use this feature with caution.",
     '([(character_literal) (string_literal)] @match (#match? @match "^.[\\\\w.\\\\-]+:[\\\\w.\\\\-]+:([0-9.]*\\\\+|latest\\\\.(release|integration))"))',
     '((string_content) @match (#match? @match "^[\\\\w.\\\\-]+:[\\\\w.\\\\-]+:([0-9.]*\\\\+|latest\\\\.(release|integration))"))',
     "dependencies {\n    implementation 'com.google.guava:guava:33.+'\n}\n", "dependencies {\n    implementation 'com.google.guava:guava:33.5.0-jre'\n}\n",
     'dependencies {\n    implementation("com.google.guava:guava:latest.release")\n}\n', 'dependencies {\n    implementation("com.google.guava:guava:33.5.0-jre")\n}\n',
     "Dynamic versions make builds non-reproducible and can pull a malicious/broken release; pin versions (and use dependency locking).", sev="major", **S_PIN)
both("MAVEN-LOCAL", "mavenLocal() repository", "supported_repository_types.html", "Gradle manages its own cache and doesn’t need to declare the local Maven repository",
     gcall("mavenLocal"), kcall("mavenLocal"), "repositories {\n    mavenLocal()\n    mavenCentral()\n}\n", "repositories {\n    mavenCentral()\n}\n",
     "repositories {\n    mavenLocal()\n    mavenCentral()\n}\n", "repositories {\n    mavenCentral()\n}\n",
     "~/.m2 content is unverified and machine-specific; builds become non-reproducible.", sev="minor", **S_PIN)
both("SNAPSHOT-DEPENDENCY", "SNAPSHOT dependency", "dependency_versions.html", "Declaring changing versions",
     '([(character_literal) (string_literal)] @match (#match? @match "^.[\\\\w.\\\\-]+:[\\\\w.\\\\-]+:[^:\'\\"]*-SNAPSHOT"))', '((string_content) @match (#match? @match "^[\\\\w.\\\\-]+:[\\\\w.\\\\-]+:[^:]*-SNAPSHOT"))',
     "dependencies {\n    implementation 'com.acme:lib:1.2-SNAPSHOT'\n}\n", "dependencies {\n    implementation 'com.acme:lib:1.2.0'\n}\n",
     'dependencies {\n    implementation("com.acme:lib:1.2-SNAPSHOT")\n}\n', 'dependencies {\n    implementation("com.acme:lib:1.2.0")\n}\n',
     "Changing versions are re-resolved and non-reproducible.", sev="minor", **S_PIN, mode="ai-confirm",
     ai="Is this a release/main build (not an intentional local integration of an in-development module)?")
both("FILE-DEPENDENCY", "Local jar file dependency", "supported_repository_types.html", "discouraged, as they do not support metadata formats like Ivy XML or Maven POM files.",
     '((juxt_function_call args: (argument_list (method_invocation name: (identifier) @match))) (#match? @match "^(files|fileTree)$"))\n((juxt_function_call name: (identifier) @c args: (argument_list (identifier) @match)) (#match? @c "^(implementation|api|compileOnly|runtimeOnly|testImplementation)$") (#match? @match "^(files|fileTree)$"))',
     '((call_expression (value_arguments (value_argument (call_expression . (identifier) @match)))) (#match? @match "^(files|fileTree)$"))',
     "dependencies {\n    implementation files('libs/acme.jar')\n}\n", "dependencies {\n    implementation 'com.acme:acme:1.0.0'\n}\n",
     'dependencies {\n    implementation(files("libs/acme.jar"))\n}\n', 'dependencies {\n    implementation("com.acme:acme:1.0.0")\n}\n',
     "Jar files lack metadata (transitives, verification); publish to a repository.", sev="minor", kind="best-practice", cat="supply-chain",
     filters=["file.has_re:dependencies"])
RULES = P.R

"""Maven pack (pom.xml, xml grammar): POM reference, dependency mechanism, Maven 3.x compatibility notes,
3.8.1 HTTP blocking, What's New in Maven 4 (model 4.1.0), compiler/surefire/gpg/enforcer plugin docs.
Version dimension `maven` comes from .mvn/wrapper/maven-wrapper.properties or modelVersion 4.1.0."""
from specs._common import Pack, secret_rules, PLACEHOLDER_RE

M = "https://maven.apache.org/"
P = Pack("MAVEN", "xml", "Maven 3.10 / 4.0", {"maven": "*"}, files=["**/pom.xml"])
X = '<project>\n  <modelVersion>4.0.0</modelVersion>\n{}</project>\n'
X41 = '<project>\n  <modelVersion>4.1.0</modelVersion>\n{}</project>\n'


def el(name_re, val_re):
    """<name>value</name> with name/value regexes."""
    return f'((element (STag (Name) @n) (content (CharData) @match)) (#match? @n "^({name_re})$") (#match? @match "{val_re}"))'


def block(name_re, has_re, lacks_re=None):
    lk = f' (#not-match? @match "{lacks_re}")' if lacks_re else ""
    return f'((element (STag (Name) @n)) @match (#match? @n "^({name_re})$") (#match? @match "{has_re}"){lk})'


DEP = lambda inner: f"  <dependencies>\n    <dependency>\n{inner}    </dependency>\n  </dependencies>\n"
GAV = "      <groupId>org.slf4j</groupId>\n      <artifactId>slf4j-api</artifactId>\n"

# ------------------------------------------------------------------ reproducibility / supply chain
P("SYSTEM-SCOPE", "system-scoped dependency", M + "pom.html", "Set the dependency scope to system and define a systemPath . This is not recommended",
  block("dependency", "<scope>\\\\s*system\\\\s*</scope>"), X.format(DEP(GAV + "      <version>2.0.17</version>\n      <scope>system</scope>\n      <systemPath>${project.basedir}/lib/a.jar</systemPath>\n")),
  X.format(DEP(GAV + "      <version>2.0.17</version>\n")), "system scope bypasses repositories (no transitives, not portable, unverified); install/deploy the jar instead.",
  sev="major", kind="best-practice", cat="supply-chain")
P("VERSION-RANGE", "Dependency version range", M + "pom.html", "(,1.0] : Hard requirement for any version <= 1.0.",
  el("version", "^\\\\s*[\\\\[(][^\\\\])]*,[^\\\\])]*[\\\\])]\\\\s*$"), X.format(DEP(GAV + "      <version>[2.0,)</version>\n")), X.format(DEP(GAV + "      <version>2.0.17</version>\n")),
  "Ranges re-resolve on every build (non-reproducible, can pull a compromised release); pin and update deliberately.", sev="major", kind="security", cat="supply-chain")
P("METAVERSION", "LATEST/RELEASE metaversion", "https://cwiki.apache.org/confluence/display/MAVEN/Maven+3.x+Compatibility+Notes",
  "For the sake of reproducible builds, Maven 3.x no longer supports usage of these metaversions in the POM.",
  el("version", "^\\\\s*(LATEST|RELEASE)\\\\s*$"), X.format(DEP(GAV + "      <version>LATEST</version>\n")), X.format(DEP(GAV + "      <version>2.0.17</version>\n")),
  "Pin an explicit version.", sev="major", kind="removal", cat="supply-chain", applies={"maven": ">=3.0"}, docv="Maven 3.x")
P("HTTP-REPOSITORY", "Repository over plain HTTP", M + "docs/3.8.1/release-notes.html", "The decision was made to block such external HTTP repositories by default",
  '((element (STag (Name) @r) (content (element (STag (Name) @u) (content (CharData) @match)))) (#match? @r "^(repository|pluginRepository|snapshotRepository|mirror)$") (#eq? @u "url") (#match? @match "^\\\\s*http://"))',
  X.format("  <repositories>\n    <repository>\n      <id>corp</id>\n      <url>http://repo.example.com/m2</url>\n    </repository>\n  </repositories>\n"),
  X.format("  <repositories>\n    <repository>\n      <id>corp</id>\n      <url>https://repo.example.com/m2</url>\n    </repository>\n  </repositories>\n"),
  "HTTP repositories are blocked since Maven 3.8.1 and allow artifact tampering; use HTTPS.", sev="critical", kind="security", cat="security", docv="Maven 3.8.1")
P("CHECKSUM-POLICY-LAX", "checksumPolicy warn/ignore", M + "pom.html", "checksumPolicy>fail</checksumPolicy>",
  el("checksumPolicy", "^\\\\s*(warn|ignore)\\\\s*$"), X.format("  <repositories>\n    <repository>\n      <id>c</id>\n      <url>https://r</url>\n      <releases>\n        <checksumPolicy>ignore</checksumPolicy>\n      </releases>\n    </repository>\n  </repositories>\n"),
  X.format("  <repositories>\n    <repository>\n      <id>c</id>\n      <url>https://r</url>\n      <releases>\n        <checksumPolicy>fail</checksumPolicy>\n      </releases>\n    </repository>\n  </repositories>\n"),
  "Corrupted or tampered artifacts are accepted; use fail.", sev="major", kind="security", cat="supply-chain")
P("SNAPSHOT-DEPENDENCY", "SNAPSHOT dependency", M + "guides/getting-started/index.html", "SNAPSHOT value refers to the ‘latest’ code along a development branch",
  el("version", "-SNAPSHOT\\\\s*$"), X.format(DEP(GAV + "      <version>2.1.0-SNAPSHOT</version>\n")), X.format(DEP(GAV + "      <version>2.0.17</version>\n")),
  "Snapshots change under you; release builds must not depend on them.", sev="minor", kind="best-practice", cat="supply-chain",
  filters=[r"parent.lacks_re:<artifactId>[^<]*</artifactId>\s*<version>\$\{project\.version\}"], mode="ai-confirm",
  ai="Is this an external SNAPSHOT (not a sibling module of the same reactor/version)?")
P("PLUGIN-METAVERSION-MISSING", "Plugin declared without version", M + "enforcer/enforcer-rules/requirePluginVersions.html",
  "This rule enforces that all plugins have a version defined, either in the plugin or pluginManagement section of the pom or a parent pom.",
  block("plugin", "<artifactId>", "<version>"), X.format("  <build>\n    <plugins>\n      <plugin>\n        <artifactId>maven-surefire-plugin</artifactId>\n      </plugin>\n    </plugins>\n  </build>\n"),
  X.format("  <build>\n    <plugins>\n      <plugin>\n        <artifactId>maven-surefire-plugin</artifactId>\n        <version>3.5.4</version>\n      </plugin>\n    </plugins>\n  </build>\n"),
  "Unpinned plugins take the Super POM/latest default, which changes with the Maven version.", sev="minor", kind="best-practice", cat="supply-chain",
  mode="ai-confirm", ai="Is the version not managed by pluginManagement here or in a parent POM (e.g. spring-boot-starter-parent)?")

# ------------------------------------------------------------------ deprecated expressions / Maven 4
P("POM-EXPRESSIONS", "${pom.*} / bare ${version}-style expressions", M + "ref/current/maven-model-builder/",
  "project.* pom.* ( deprecated ) * ( deprecated )",
  '((CharData) @match (#match? @match "\\\\$\\\\{(pom\\\\.[a-zA-Z]|version\\\\}|artifactId\\\\}|groupId\\\\}|basedir\\\\})"))',
  X.format("  <build>\n    <finalName>app-${pom.version}</finalName>\n  </build>\n"), X.format("  <build>\n    <finalName>app-${project.version}</finalName>\n  </build>\n"),
  "Use ${project.*}; Maven 4 removes ${pom.*} support.", sev="major", kind="deprecation", cat="deprecation", docv="Maven 3.x/4.0")
P("POM-EXPRESSIONS-REMOVED", "${pom.*} expressions under Maven 4", M + "whatsnewinmaven4.html", "for example using ${pom.*} expressions",
  '((CharData) @match (#match? @match "\\\\$\\\\{pom\\\\.[a-zA-Z]"))', X.format("  <build>\n    <finalName>app-${pom.version}</finalName>\n  </build>\n"),
  X.format("  <build>\n    <finalName>app-${project.version}</finalName>\n  </build>\n"), "Removed in Maven 4.", sev="critical", kind="removal", cat="removal",
  applies={"maven": ">=4.0"}, docv="Maven 4.0")
P("MODULES-TO-SUBPROJECTS", "<modules> in a 4.1.0 model", M + "whatsnewinmaven4.html", "analogous to the now deprecated, but still usable, <modules> element.",
  '((element (STag (Name) @match)) (#eq? @match "modules"))', X41.format("  <modules>\n    <module>app</module>\n  </modules>\n"),
  X41.format("  <subprojects>\n    <subproject>app</subproject>\n  </subprojects>\n"), "Model 4.1.0 renames modules to subprojects.", sev="minor", kind="deprecation",
  cat="deprecation", applies={"maven": ">=4.0"}, filters=[r"file.has_re:<modelVersion>\s*4\.1\.0"], docv="Maven 4.0")
P("MODEL-VERSION-410", "Model 4.0.0 under Maven 4", M + "whatsnewinmaven4.html", "Model version 4.1.0 contains a new <subprojects> element",
  el("modelVersion", "^\\\\s*4\\\\.0\\\\.0\\\\s*$"), X.format(""), X41.format(""),
  "Maven 4 supports model 4.1.0 (subprojects, parent inference, <sources>, CI-friendly versions); the consumer POM stays 4.0.0.", sev="info", kind="modernization",
  cat="modernization", applies={"maven": ">=4.0"}, docv="Maven 4.0")
P("PARENT-INFERENCE", "Fully specified <parent> in a 4.1.0 model", M + "whatsnewinmaven4.html", "you can omit the <version> , <groupId> , and <artifactId> elements from <parent> by using a relative path.",
  block("parent", "<relativePath>", None), X41.format("  <parent>\n    <groupId>com.acme</groupId>\n    <artifactId>root</artifactId>\n    <version>1.0</version>\n    <relativePath>..</relativePath>\n  </parent>\n"),
  X41.format("  <parent/>\n"), "Let Maven 4 infer parent coordinates.", sev="info", kind="modernization", cat="modernization", applies={"maven": ">=4.0"},
  filters=[r"file.has_re:<modelVersion>\s*4\.1\.0", r"node.has_re:<groupId>"], docv="Maven 4.0")
P("SOURCE-DIRECTORY-410", "<sourceDirectory>/<testSourceDirectory> in a 4.1.0 model", M + "whatsnewinmaven4.html", "element for this. Multiple <source> elements can be repeated",
  '((element (STag (Name) @match)) (#match? @match "^(sourceDirectory|testSourceDirectory)$"))', X41.format("  <build>\n    <sourceDirectory>src/java</sourceDirectory>\n  </build>\n"),
  X41.format("  <build>\n    <sources>\n      <source>\n        <directory>src/java</directory>\n      </source>\n    </sources>\n  </build>\n"),
  "Model 4.1.0 declares source roots with <sources>.", sev="info", kind="modernization", cat="modernization", applies={"maven": ">=4.0"},
  filters=[r"file.has_re:<modelVersion>\s*4\.1\.0"], docv="Maven 4.0")
P("ROOT-DIRECTORY-HACK", "Internal multiModuleProjectDirectory property", M + "whatsnewinmaven4.html", "Starting with Maven 4 those properties were removed or marked as deprecated.",
  '((CharData) @match (#match? @match "\\\\$\\\\{maven\\\\.multiModuleProjectDirectory\\\\}"))', X.format("  <properties>\n    <root>${maven.multiModuleProjectDirectory}</root>\n  </properties>\n"),
  X.format("  <properties>\n    <root>${project.rootDirectory}</root>\n  </properties>\n"), "Use ${project.rootDirectory} (Maven 4) / ${session.rootDirectory}.",
  sev="minor", kind="deprecation", cat="deprecation", applies={"maven": ">=4.0"}, docv="Maven 4.0")

# ------------------------------------------------------------------ build configuration
P("SOURCE-ENCODING-MISSING", "project.build.sourceEncoding not set", M + "general.html", "<project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>",
  '((element (STag (Name) @n)) @match (#eq? @n "project"))', X.format("  <artifactId>a</artifactId>\n"),
  X.format("  <properties>\n    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>\n  </properties>\n"),
  "Without it resources/sources use the platform encoding, so builds differ between machines.", sev="minor", kind="best-practice", cat="best-practice",
  filters=["file.lacks_re:sourceEncoding|<parent>"])
P("COMPILER-SOURCE-TARGET", "-source/-target instead of --release", M + "plugins/maven-compiler-plugin/examples/set-compiler-source-and-target.html",
  "Merely setting the target option does not guarantee that your code actually runs on a JRE with the specified version.",
  '((element (STag (Name) @match)) (#match? @match "^(maven\\\\.compiler\\\\.source|maven\\\\.compiler\\\\.target)$"))\n((element (STag (Name) @c) (content (element (STag (Name) @match)))) (#eq? @c "configuration") (#match? @match "^(source|target)$"))',
  X.format("  <properties>\n    <maven.compiler.source>17</maven.compiler.source>\n    <maven.compiler.target>17</maven.compiler.target>\n  </properties>\n"),
  X.format("  <properties>\n    <maven.compiler.release>17</maven.compiler.release>\n  </properties>\n"),
  "Use maven.compiler.release (JDK 9+): it also checks API usage against the target platform.", sev="minor", kind="modernization", cat="modernization",
  filters=["file.lacks_re:maven\\.compiler\\.release|<release>"])
P("TEST-FAILURE-IGNORE", "testFailureIgnore / maven.test.failure.ignore", M + "surefire/maven-surefire-plugin/test-mojo.html", "Set this to \"true\" to ignore a failure during testing. Its use is NOT RECOMMENDED",
  el("testFailureIgnore|maven\\\\.test\\\\.failure\\\\.ignore", "^\\\\s*true\\\\s*$"),
  X.format("  <properties>\n    <maven.test.failure.ignore>true</maven.test.failure.ignore>\n  </properties>\n"), X.format("  <properties>\n    <java.version>21</java.version>\n  </properties>\n"),
  "Failing tests no longer fail the build.", sev="major", kind="best-practice", cat="testing", docv="Surefire 3.5")
P("SKIP-TESTS", "Tests skipped in the POM", M + "surefire/maven-surefire-plugin/test-mojo.html", "because maven.test.skip disables both running the tests and compiling the tests.",
  el("skipTests|skip|maven\\\\.test\\\\.skip|skipITs", "^\\\\s*true\\\\s*$"), X.format("  <properties>\n    <maven.test.skip>true</maven.test.skip>\n  </properties>\n"),
  X.format("  <properties>\n    <java.version>21</java.version>\n  </properties>\n"), "Skipping tests in the POM disables them for everyone (and CI).", sev="major",
  kind="best-practice", cat="testing", docv="Surefire 3.5", filters=[r"file.has_re:maven\.test\.skip|skipTests|skipITs|surefire|failsafe"],
  mode="ai-confirm", ai="Is this skip unconditional (not inside a profile intended for quick local builds)?")
P("SUREFIRE-OLD-JUNIT5", "Old Surefire with JUnit 5", M + "surefire/maven-surefire-plugin/examples/junit-platform.html", "junit-jupiter-engine to the dependencies in POM",
  block("plugin", "maven-(surefire|failsafe)-plugin</artifactId>\\\\s*<version>\\\\s*2\\\\.([0-9]|1[0-9]|2[01])\\\\."), 
  X.format(DEP("      <groupId>org.junit.jupiter</groupId>\n      <artifactId>junit-jupiter</artifactId>\n      <version>5.13.4</version>\n") + "  <build>\n    <plugins>\n      <plugin>\n        <artifactId>maven-surefire-plugin</artifactId>\n        <version>2.19.1</version>\n      </plugin>\n    </plugins>\n  </build>\n"),
  X.format(DEP("      <groupId>org.junit.jupiter</groupId>\n      <artifactId>junit-jupiter</artifactId>\n      <version>5.13.4</version>\n") + "  <build>\n    <plugins>\n      <plugin>\n        <artifactId>maven-surefire-plugin</artifactId>\n        <version>3.5.4</version>\n      </plugin>\n    </plugins>\n  </build>\n"),
  "Surefire < 2.22 does not run JUnit Platform tests: they are silently skipped.", sev="major", kind="best-practice", cat="testing", filters=["file.has_re:junit-jupiter|junit-platform"],
  docv="Surefire 3.5")
P("IMPORT-SCOPE-NOT-POM", "import scope outside dependencyManagement or without type pom", M + "guides/introduction/introduction-to-dependency-mechanism.html",
  "This scope is only supported on a dependency of type pom in the <dependencyManagement> section.",
  block("dependency", "<scope>\\\\s*import\\\\s*</scope>", "<type>\\\\s*pom\\\\s*</type>"),
  X.format("  <dependencyManagement>\n" + DEP("      <groupId>org.junit</groupId>\n      <artifactId>junit-bom</artifactId>\n      <version>5.13.4</version>\n      <scope>import</scope>\n") + "  </dependencyManagement>\n"),
  X.format("  <dependencyManagement>\n" + DEP("      <groupId>org.junit</groupId>\n      <artifactId>junit-bom</artifactId>\n      <version>5.13.4</version>\n      <type>pom</type>\n      <scope>import</scope>\n") + "  </dependencyManagement>\n"),
  "A BOM import without <type>pom</type> is ignored.", sev="major", kind="best-practice", cat="correctness")
P("CI-FRIENDLY-VERSION", "Hard-coded version repeated in parent references", M + "guides/mini/guide-maven-ci-friendly.html", "as placeholders for the version in your pom file.",
  block("parent", "<version>\\\\s*[0-9]", "\\\\$\\\\{revision\\\\}"), X.format("  <modules>\n    <module>app</module>\n  </modules>\n  <parent>\n    <groupId>com.acme</groupId>\n    <artifactId>root</artifactId>\n    <version>1.4.2</version>\n  </parent>\n"),
  X.format("  <modules>\n    <module>app</module>\n  </modules>\n  <parent>\n    <groupId>com.acme</groupId>\n    <artifactId>root</artifactId>\n    <version>${revision}</version>\n  </parent>\n"),
  "In multi-module builds use ${revision} (+ flatten plugin on Maven 3) to avoid editing every POM per release.", sev="info", kind="best-practice", cat="maintainability",
  filters=[r"file.has_re:<modules>|<subprojects>"], mode="ai-confirm", ai="Is this an in-reactor parent (same repository) whose version is bumped together with the module?")

# ------------------------------------------------------------------ secrets
P("GPG-PASSPHRASE-IN-POM", "GPG passphrase in the POM", M + "plugins/maven-gpg-plugin/usage.html", "you should provide passphrases via environment variable",
  '((element (STag (Name) @match) (content (CharData) @v)) (#match? @match "^(passphrase|gpg\\\\.passphrase)$") (#not-match? @v "^\\\\s*\\\\$\\\\{"))',
  X.format("  <properties>\n    <gpg.passphrase>hunter2</gpg.passphrase>\n  </properties>\n"), X.format("  <properties>\n    <gpg.keyname>release</gpg.keyname>\n  </properties>\n"),
  "Signing passphrases must come from the agent or MAVEN_GPG_PASSPHRASE, not the POM.", sev="critical", kind="security", cat="security", docv="GPG plugin 3.2")
P("PASSWORD-PROPERTY", "Password/secret literal in POM properties or configuration", "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
  "Many organizations have them hardcoded within the source code in plaintext",
  '((element (STag (Name) @k) (content (CharData) @match)) (#match? @k "(?i)(password|passwd|secret|token|apikey|api\\\\.key|privatekey)$") (#not-match? @match "' + PLACEHOLDER_RE.replace("^(", "^\\\\s*(") + '"))',
  X.format("  <properties>\n    <db.password>s3cr3t-Pass</db.password>\n  </properties>\n"), X.format("  <properties>\n    <db.password>${env.DB_PASSWORD}</db.password>\n  </properties>\n"),
  "Move credentials to settings.xml (encrypted) or environment variables.", sev="critical", kind="security", cat="security", docv="OWASP cheat sheet (2026)")
secret_rules(P, '(CharData)', lambda k, v: X.format(f"  <properties>\n    <{k}>{v}</{k}>\n  </properties>\n"))
RULES = P.R

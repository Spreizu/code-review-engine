"""Taint-lite pack (engine: taint, internal/taint + rules/data/taint.yaml): untrusted request data that
reaches an injection sink inside one function (Java, Kotlin, Python, JS/TS, PHP, Go).

Every rule is ai-confirm (the engine is intra-procedural and name-based, so a flow is a candidate the
AI step must confirm from the code shown). Citations are the official language/library docs where
they state the risk, otherwise the OWASP cheat sheet for the class. Sonar/Semgrep keys are recorded
only as xref (checklist use; no rule text or code from them)."""
from specs._common import Pack

P = Pack("TAINT", "java", "current", {})

OW = "https://cheatsheetseries.owasp.org/cheatsheets/"
DOC = {
    "sqli": (OW + "SQL_Injection_Prevention_Cheat_Sheet.html", "Stop writing dynamic queries with string concatenation", "OWASP SQL Injection Prevention Cheat Sheet"),
    "cmdi": (OW + "OS_Command_Injection_Defense_Cheat_Sheet.html", "If calling a system command that incorporates user-supplied cannot be avoided", "OWASP OS Command Injection Defense Cheat Sheet"),
    "path": ("https://owasp.org/www-community/attacks/Path_Traversal", "A path traversal attack (also known as directory traversal) aims to access files and directories that are stored outside the web root folder", "OWASP Path Traversal"),
    "ldap": (OW + "LDAP_Injection_Prevention_Cheat_Sheet.html", "LDAP Injection is an attack used to exploit web based applications that construct LDAP statements based on user input", "OWASP LDAP Injection Prevention Cheat Sheet"),
    "xss": (OW + "Cross_Site_Scripting_Prevention_Cheat_Sheet.html", "When you need to safely display data exactly as a user types it in, output encoding is recommended", "OWASP Cross Site Scripting Prevention Cheat Sheet"),
    "ssrf": (OW + "Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html", "SSRF is an attack vector that abuses an application to interact with the internal/external network or the machine itself", "OWASP SSRF Prevention Cheat Sheet"),
    "redirect": (OW + "Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html", "Unvalidated redirects and forwards are possible when a web application accepts untrusted input that could cause the web application to redirect the request to a URL contained within untrusted input", "OWASP Unvalidated Redirects and Forwards Cheat Sheet"),
    "xpath": ("https://owasp.org/www-community/attacks/XPATH_Injection", "XPath Injection attacks occur when a web site uses user-supplied information to construct an XPath query for XML data", "OWASP XPath Injection"),
    "code": ("https://owasp.org/www-community/attacks/Code_Injection", "Code Injection", "OWASP Code Injection"),
    "regex": ("https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS", "An attacker can then cause a program using a Regular Expression (Regex) to enter these extreme situations and then hang for a very long time", "OWASP Regular expression Denial of Service - ReDoS"),
    "smtp": ("https://cwe.mitre.org/data/definitions/93.html", "does not neutralize or incorrectly neutralizes CRLF sequences from inputs", "CWE-93: CRLF Injection"),
    "trust": ("https://cwe.mitre.org/data/definitions/501.html", "The product mixes trusted and untrusted data in the same data structure or structured message", "CWE-501: Trust Boundary Violation"),
}
JSEC = "https://www.oracle.com/java/technologies/javase/seccodeguide.html"
LANGDOC = {
    ("java", "sqli"): (JSEC, "It is well known that dynamically created SQL statements including untrusted input are subject to command injection", "Secure Coding Guidelines for Java SE (INJECT-2)"),
    ("java", "cmdi"): (JSEC, "When creating new processes, do not place any untrusted data on the command line", "Secure Coding Guidelines for Java SE (INJECT-4)"),
    ("java", "xss"): (JSEC, "Untrusted data should be properly sanitized before being included in HTML or XML output", "Secure Coding Guidelines for Java SE (INJECT-3)"),
    ("kotlin", "sqli"): (JSEC, "It is well known that dynamically created SQL statements including untrusted input are subject to command injection", "Secure Coding Guidelines for Java SE (INJECT-2)"),
    ("kotlin", "cmdi"): (JSEC, "When creating new processes, do not place any untrusted data on the command line", "Secure Coding Guidelines for Java SE (INJECT-4)"),
    ("kotlin", "xss"): (JSEC, "Untrusted data should be properly sanitized before being included in HTML or XML output", "Secure Coding Guidelines for Java SE (INJECT-3)"),
    ("python", "sqli"): ("https://docs.python.org/3/library/sqlite3.html", "beware of using Python’s string operations to assemble queries, as they are vulnerable to SQL injection attacks", "Python sqlite3 documentation"),
    ("python", "cmdi"): ("https://docs.python.org/3/library/subprocess.html", "it is the application’s responsibility to ensure that all whitespace and metacharacters are quoted appropriately to avoid shell injection vulnerabilities", "Python subprocess: Security Considerations"),
    ("python", "code"): ("https://docs.python.org/3/library/functions.html", "Calling it with untrusted user-supplied input will lead to security vulnerabilities", "Python built-in functions: eval/exec"),
    ("python", "xss"): ("https://flask.palletsprojects.com/en/stable/web-security/", "developers have to properly escape text so that it cannot include arbitrary HTML tags", "Flask: Security Considerations"),
    ("python", "path"): ("https://flask.palletsprojects.com/en/stable/patterns/fileuploads/", "secure_filename", "Flask: Uploading Files"),
    ("javascript", "cmdi"): ("https://nodejs.org/api/child_process.html", "Never pass unsanitized user input to this function", "Node.js child_process"),
    ("javascript", "code"): ("https://nodejs.org/api/vm.html", "The node:vm module is not a security mechanism. Do not use it to run untrusted code", "Node.js vm"),
    ("php", "sqli"): ("https://www.php.net/manual/en/security.database.sql-injection.php", "The recommended way to avoid SQL injection is by binding all data via prepared statements", "PHP Manual: SQL Injection"),
    ("php", "cmdi"): ("https://www.php.net/manual/en/function.escapeshellarg.php", "allowing you to pass a string directly to a shell function and having it be treated as a single safe argument", "PHP Manual: escapeshellarg"),
    ("php", "path"): ("https://www.php.net/manual/en/security.filesystem.php", "Consider what could happen if the variables submitted were", "PHP Manual: Filesystem Security"),
    ("php", "code"): ("https://www.php.net/manual/en/function.eval.php", "The eval() language construct is very dangerous because it allows execution of arbitrary PHP code", "PHP Manual: eval"),
    ("go", "sqli"): ("https://go.dev/doc/database/sql-injection", "This is not secure!", "Go: Avoiding SQL injection risk"),
    ("go", "path"): ("https://pkg.go.dev/path/filepath", "IsLocal reports whether path, using lexical analysis only, has all of these properties", "Go path/filepath"),
    ("go", "xss"): ("https://pkg.go.dev/html/template", "implements data-driven templates for generating HTML output safe against code injection", "Go html/template"),
}
LANGDOC[("javascript", "sqli")] = DOC["sqli"]
LANGDOC[("php", "smtp")] = ("https://www.php.net/manual/en/function.mail.php", "the data should be sanitized so that no unwanted headers could be injected", "PHP Manual: mail")

META = {  # class: (title, cwe, owasp, severity, sonar key, message)
    "sqli": ("SQL built from request data", ["CWE-89"], ["A03:2021", "A05:2025"], "critical", "S3649",
             "Request data reaches a SQL string in this function. Bind it as a query parameter instead of concatenating or formatting it into the statement."),
    "cmdi": ("OS command built from request data", ["CWE-78"], ["A03:2021", "A05:2025"], "critical", "S2076",
             "Request data reaches a process/shell command in this function. Avoid the shell, pass a fixed program with separate arguments, and validate values against an allow-list."),
    "path": ("File path built from request data", ["CWE-22", "CWE-23"], ["A01:2021", "A01:2025"], "major", "S2083",
             "Request data reaches a file-system path in this function. Reduce it to a bare file name (or check it stays under the base directory after normalising) before opening the file."),
    "ldap": ("LDAP query built from request data", ["CWE-90"], ["A03:2021", "A05:2025"], "major", "S2078",
             "Request data reaches an LDAP filter or DN in this function. Escape it with the LDAP filter/DN encoder for its position before building the query."),
    "xss": ("Request data written to the HTML response", ["CWE-79"], ["A03:2021", "A05:2025"], "major", "S5131",
            "Request data is written to the response body without HTML encoding in this function. Encode it for the output context, or render it through an auto-escaping template."),
    "ssrf": ("Outbound request URL built from request data", ["CWE-918"], ["A10:2021", "A01:2025"], "major", "S5144",
             "Request data decides the URL of a server-side HTTP request in this function. Only allow known hosts/schemes (allow-list), and keep user input out of the host part."),
    "redirect": ("Redirect target taken from request data", ["CWE-601"], ["A01:2021", "A01:2025"], "major", "S5146",
                 "Request data is used as the redirect target. Redirect only to relative paths or to an allow-list of destinations."),
    "xpath": ("XPath expression built from request data", ["CWE-643"], ["A03:2021", "A05:2025"], "major", "S2091",
              "Request data is concatenated into an XPath expression. Use XPath variables (a variable resolver / keyword arguments) instead."),
    "code": ("Code evaluated from request data", ["CWE-94"], ["A03:2021", "A05:2025"], "critical", "S5334",
             "Request data reaches a dynamic code evaluation API. Never evaluate request data; parse it as data (JSON, a literal parser) instead."),
    "regex": ("Regular expression built from request data", ["CWE-1333", "CWE-400", "CWE-730"], ["A03:2021", "A05:2025"], "major", "S2631",
              "Request data is compiled as a regular expression. A crafted pattern can backtrack for minutes (ReDoS) or change what the check accepts; escape it as a literal (re.escape / Pattern.quote / regexp.QuoteMeta / preg_quote) or match it without a regex."),
    "smtp": ("Mail header or recipient built from request data", ["CWE-93", "CWE-284"], ["A03:2021", "A05:2025"], "major", None,
             "Request data reaches a mail header, recipient or subject. CR/LF in the value injects extra headers or recipients (spam relay, spoofing); validate addresses with an address parser and strip CR/LF from header values."),
    "trust": ("Request data stored in the session unvalidated", ["CWE-501"], ["A04:2021", "A06:2025"], "minor", None,
              "Request data is written into the server-side session (as a key or a value) without validation. Later code treats session contents as trusted; validate or normalise the value first."),
}
SONAR_LANG = {"java": ["javasecurity"], "kotlin": ["kotlinsecurity"], "python": ["pythonsecurity"], "php": ["phpsecurity"],
              "go": ["gosecurity"], "javascript": ["jssecurity", "tssecurity"]}
SEMGREP = {
    'go/path': ['go.lang.security.filepath-clean-misuse'], 'go/redirect': ['go.lang.security.injection.open-redirect'],
    'go/sqli': ['go.lang.security.injection.tainted-sql-string', 'go.gorm.security.audit.gorm-dangerous-method-usage'],
    'go/ssrf': ['go.lang.security.injection.tainted-url-host'], 'go/xss': ['go.lang.security.injection.raw-html-format'],
    'java/cmdi': ['java.lang.security.audit.tainted-cmd-from-http-request', 'java.spring.security.injection.tainted-system-command'],
    'java/ldap': ['java.lang.security.audit.tainted-ldapi-from-http-request'],
    'java/path': ['java.lang.security.httpservlet-path-traversal', 'java.spring.security.injection.tainted-file-path'],
    'java/sqli': ['java.lang.security.audit.sqli.tainted-sql-from-http-request', 'java.spring.security.injection.tainted-sql-string', 'java.lang.security.audit.formatted-sql-string', 'java.spring.security.audit.spring-sqli'],
    'java/ssrf': ['java.spring.security.injection.tainted-url-host'], 'java/xpath': ['java.lang.security.audit.tainted-xpath-from-http-request'],
    'java/xss': ['java.lang.security.audit.xss.no-direct-response-writer', 'java.spring.security.injection.tainted-html-string'],
    'javascript/cmdi': ['javascript.lang.security.detect-child-process', 'javascript.lang.security.audit.dangerous-spawn-shell'],
    'javascript/code': ['javascript.lang.security.detect-eval-with-expression', 'javascript.express.security.express-vm-injection', 'javascript.lang.security.audit.code-string-concat'],
    'javascript/path': ['javascript.lang.security.audit.detect-non-literal-fs-filename', 'javascript.express.security.audit.express-res-sendfile', 'javascript.lang.security.audit.path-traversal.path-join-resolve-traversal', 'javascript.express.security.audit.express-path-join-resolve-traversal'],
    'javascript/redirect': ['javascript.express.security.audit.express-open-redirect', 'javascript.browser.security.js-open-redirect'],
    'javascript/sqli': ['javascript.express.security.injection.tainted-sql-string', 'javascript.lang.security.audit.sqli.node-mysql-sqli', 'javascript.lang.security.audit.sqli.node-knex-sqli', 'javascript.lang.security.audit.sqli.node-mssql-sqli', 'javascript.sequelize.security.audit.express-sequelize-injection'],
    'javascript/ssrf': ['javascript.express.security.audit.express-ssrf'],
    'javascript/xss': ['javascript.express.security.audit.xss.direct-response-write', 'javascript.express.security.injection.raw-html-format', 'javascript.browser.security.raw-html-concat'],
    'php/cmdi': ['php.lang.security.injection.tainted-exec'], 'php/code': ['php.lang.security.tainted-exec', 'php.lang.security.injection.tainted-callable'],
    'php/sqli': ['php.lang.security.injection.tainted-sql-string', 'php.laravel.security.laravel-sql-injection', 'php.doctrine.security.audit.doctrine-orm-dangerous-query'],
    'php/ssrf': ['php.lang.security.injection.tainted-url-host'], 'php/path': ['php.lang.security.injection.tainted-filename'],
    'php/xss': ['php.lang.security.injection.echoed-request', 'php.lang.security.injection.printed-request'],
    'python/cmdi': ['python.flask.security.injection.subprocess-injection', 'python.django.security.injection.command.subprocess-injection', 'python.lang.security.dangerous-system-call', 'python.lang.security.dangerous-subprocess-use'],
    'python/sqli': ['python.sqlalchemy.security.audit.avoid-sqlalchemy-text', 'python.pyramid.security.pyramid-sqlalchemy-sql-injection'],
    'python/ssrf': ['python.flask.security.injection.tainted-url-host', 'python.django.security.injection.tainted-url-host'],
    'python/xss': ['python.flask.security.injection.raw-html-format', 'python.flask.security.audit.directly-returned-format-string', 'python.django.security.injection.raw-html-format'],
}
APPLIES = {"java": {"java": ">=8"}, "kotlin": {"kotlin": "*"}, "python": {"python": "*"}, "php": {"php": "*"}, "go": {"go": "*"},
           "javascript": {"ecmascript": ">=3"}}
PREFIX = {"java": "JAVA", "kotlin": "KT", "python": "PY", "javascript": "JS", "php": "PHP", "go": "GO"}
AI = ("Does untrusted request data really flow, along the path shown in the evidence, into this {what} without an "
      "effective guard (allow-list, type conversion, encoder or parameter binding) for this context? Answer no if the "
      "value is constant on every path, validated, or the sink is not reachable with attacker data.")


def T(lang, cls, bad, good, fp=None, doc=None):
    title, cwe, owasp, sev, skey, msg = META[cls]
    url, needle, docname = doc or LANGDOC.get((lang, cls)) or DOC[cls]
    xref = [f"sonar:{s}:{skey}" for s in SONAR_LANG[lang] if skey] + ["semgrep:" + k for k in SEMGREP.get(f"{lang}/{cls}", [])]
    P(f"{PREFIX[lang]}-{cls.upper()}", title, url, needle, None, bad, good, msg, sev=sev, kind="security", cat="security",
      lang=lang, applies=APPLIES[lang], engine="taint", config={"class": cls}, mode="ai-confirm",
      ai=AI.format(what=title.lower().replace("request data", "sink").strip()), doc=docname, docv="current",
      xref=xref, cwe=cwe, owasp=owasp, fp=fp, precision="medium", tags=["taint", cls])
    P.R[-1]["detection"]["exclude_tests"] = True  # test fixtures echo request data on purpose


# ------------------------------------------------------------------ Java
J = lambda body, imports="import java.sql.*;\nimport javax.servlet.http.*;\n": imports + "class C {\n" + body + "}\n"
T("java", "sqli",
  J('  ResultSet find(HttpServletRequest request, Connection conn) throws SQLException {\n    String id = request.getParameter("id");\n    Statement st = conn.createStatement();\n    return st.executeQuery("SELECT * FROM users WHERE id = \'" + id + "\'");\n  }\n'),
  J('  ResultSet find(HttpServletRequest request, Connection conn) throws SQLException {\n    String id = request.getParameter("id");\n    PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");\n    ps.setString(1, id);\n    return ps.executeQuery();\n  }\n'),
  fp=[J('  ResultSet find(HttpServletRequest request, Connection conn) throws SQLException {\n    int id = Integer.parseInt(request.getParameter("id"));\n    return conn.createStatement().executeQuery("SELECT * FROM users WHERE id = " + id);\n  }\n'),
      J('  void bulk(HttpServletRequest request, JdbcTemplate jdbcTemplate) {\n    String v = request.getParameter("v");\n    jdbcTemplate.batchUpdate("INSERT INTO t(v) VALUES (?)", java.util.List.of(new Object[]{v}));\n  }\n', "import org.springframework.jdbc.core.JdbcTemplate;\nimport javax.servlet.http.*;\n")])
T("java", "cmdi",
  J('  void ping(HttpServletRequest request) throws Exception {\n    String host = request.getParameter("host");\n    Runtime.getRuntime().exec("ping -c 1 " + host);\n  }\n', "import javax.servlet.http.*;\n"),
  J('  void ping(HttpServletRequest request) throws Exception {\n    int count = Integer.parseInt(request.getParameter("count"));\n    Runtime.getRuntime().exec("ping -c " + count + " localhost");\n  }\n', "import javax.servlet.http.*;\n"))
T("java", "path",
  J('  byte[] read(HttpServletRequest request) throws Exception {\n    String name = request.getParameter("file");\n    return java.nio.file.Files.readAllBytes(new java.io.File("/var/data/" + name).toPath());\n  }\n', "import javax.servlet.http.*;\n"),
  J('  byte[] read(HttpServletRequest request) throws Exception {\n    String name = FilenameUtils.getName(request.getParameter("file"));\n    return java.nio.file.Files.readAllBytes(new java.io.File("/var/data/" + name).toPath());\n  }\n', "import javax.servlet.http.*;\nimport org.apache.commons.io.FilenameUtils;\n"))
T("java", "ldap",
  J('  Object find(HttpServletRequest request, DirContext ctx, SearchControls sc) throws Exception {\n    String user = request.getParameter("user");\n    return ctx.search("ou=people,dc=example,dc=com", "(uid=" + user + ")", sc);\n  }\n', "import javax.naming.directory.*;\nimport javax.servlet.http.*;\n"),
  J('  Object find(HttpServletRequest request, DirContext ctx, SearchControls sc) throws Exception {\n    String user = request.getParameter("user");\n    return ctx.search("ou=people,dc=example,dc=com", "(uid={0})", new Object[]{user}, sc);\n  }\n', "import javax.naming.directory.*;\nimport javax.servlet.http.*;\n"))
T("java", "xss",
  J('  void hello(HttpServletRequest request, HttpServletResponse response) throws Exception {\n    String name = request.getParameter("name");\n    response.getWriter().println("<p>Hello " + name + "</p>");\n  }\n', "import javax.servlet.http.*;\n"),
  J('  void hello(HttpServletRequest request, HttpServletResponse response) throws Exception {\n    String name = request.getParameter("name");\n    response.getWriter().println("<p>Hello " + Encode.forHtml(name) + "</p>");\n  }\n', "import javax.servlet.http.*;\nimport org.owasp.encoder.Encode;\n"))
T("java", "ssrf",
  J('  java.io.InputStream fetch(HttpServletRequest request) throws Exception {\n    String target = request.getParameter("url");\n    return new java.net.URL(target).openStream();\n  }\n', "import javax.servlet.http.*;\n"),
  J('  java.io.InputStream fetch(HttpServletRequest request) throws Exception {\n    int id = Integer.parseInt(request.getParameter("id"));\n    return new java.net.URL("https://api.example.com/items/" + id).openStream();\n  }\n', "import javax.servlet.http.*;\n"))
T("java", "redirect",
  J('  void next(HttpServletRequest request, HttpServletResponse response) throws Exception {\n    response.sendRedirect(request.getParameter("next"));\n  }\n', "import javax.servlet.http.*;\n"),
  J('  void next(HttpServletRequest request, HttpServletResponse response) throws Exception {\n    response.sendRedirect("/home");\n  }\n', "import javax.servlet.http.*;\n"))
T("java", "xpath",
  J('  Object find(HttpServletRequest request, XPath xp, org.w3c.dom.Document doc) throws Exception {\n    String n = request.getParameter("name");\n    return xp.evaluate("//user[@name=\'" + n + "\']", doc);\n  }\n', "import javax.xml.xpath.*;\nimport javax.servlet.http.*;\n"),
  J('  Object find(HttpServletRequest request, XPath xp, org.w3c.dom.Document doc) throws Exception {\n    String n = request.getParameter("name");\n    xp.setXPathVariableResolver(q -> n);\n    return xp.evaluate("//user[@name=$name]", doc);\n  }\n', "import javax.xml.xpath.*;\nimport javax.servlet.http.*;\n"))
T("java", "code",
  J('  Object calc(HttpServletRequest request, ScriptEngine engine) throws Exception {\n    String expr = request.getParameter("expr");\n    return engine.eval(expr);\n  }\n', "import javax.script.ScriptEngine;\nimport javax.servlet.http.*;\n"),
  J('  Object calc(HttpServletRequest request, ScriptEngine engine) throws Exception {\n    double x = Double.parseDouble(request.getParameter("x"));\n    return engine.eval("Math.sqrt(" + x + ")");\n  }\n', "import javax.script.ScriptEngine;\nimport javax.servlet.http.*;\n"))

# ------------------------------------------------------------------ Kotlin
K = lambda body, imports="import java.sql.Connection\nimport javax.servlet.http.HttpServletRequest\n": imports + "\n" + body
T("kotlin", "sqli",
  K('fun find(request: HttpServletRequest, conn: Connection) {\n    val id = request.getParameter("id")\n    conn.createStatement().executeQuery("SELECT * FROM users WHERE id = \'$id\'")\n}\n'),
  K('fun find(request: HttpServletRequest, conn: Connection) {\n    val id = request.getParameter("id")\n    val ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?")\n    ps.setString(1, id)\n    ps.executeQuery()\n}\n'),
  fp=[K('fun find(request: HttpServletRequest, conn: Connection) {\n    val id = request.getParameter("id").toInt()\n    conn.createStatement().executeQuery("SELECT * FROM users WHERE id = $id")\n}\n')])
T("kotlin", "cmdi",
  K('fun ping(request: HttpServletRequest) {\n    val host = request.getParameter("host")\n    Runtime.getRuntime().exec("ping -c 1 " + host)\n}\n', "import javax.servlet.http.HttpServletRequest\n"),
  K('fun ping(request: HttpServletRequest) {\n    val count = request.getParameter("count").toInt()\n    Runtime.getRuntime().exec("ping -c $count localhost")\n}\n', "import javax.servlet.http.HttpServletRequest\n"))
T("kotlin", "path",
  K('fun read(request: HttpServletRequest): ByteArray {\n    val name = request.getParameter("file")\n    return java.io.File("/var/data/" + name).readBytes()\n}\n', "import javax.servlet.http.HttpServletRequest\n"),
  K('fun read(request: HttpServletRequest): ByteArray {\n    val n = request.getParameter("file").toInt()\n    return java.io.File("/var/data/report-$n.txt").readBytes()\n}\n', "import javax.servlet.http.HttpServletRequest\n"))
T("kotlin", "ldap",
  K('fun find(request: HttpServletRequest, ctx: DirContext, sc: SearchControls) {\n    val user = request.getParameter("user")\n    ctx.search("ou=people,dc=example,dc=com", "(uid=$user)", sc)\n}\n', "import javax.naming.directory.*\nimport javax.servlet.http.HttpServletRequest\n"),
  K('fun find(request: HttpServletRequest, ctx: DirContext, sc: SearchControls) {\n    val user = request.getParameter("user")\n    ctx.search("ou=people,dc=example,dc=com", "(uid={0})", arrayOf(user), sc)\n}\n', "import javax.naming.directory.*\nimport javax.servlet.http.HttpServletRequest\n"))
T("kotlin", "xss",
  K('fun hello(request: HttpServletRequest, response: HttpServletResponse) {\n    val name = request.getParameter("name")\n    response.getWriter().println("<p>Hello $name</p>")\n}\n', "import javax.servlet.http.*\n"),
  K('fun hello(request: HttpServletRequest, response: HttpServletResponse) {\n    val name = request.getParameter("name")\n    response.getWriter().println("<p>Hello " + Encode.forHtml(name) + "</p>")\n}\n', "import javax.servlet.http.*\nimport org.owasp.encoder.Encode\n"))
T("kotlin", "ssrf",
  K('fun fetch(request: HttpServletRequest): String {\n    val target = request.getParameter("url")\n    return java.net.URL(target).readText()\n}\n', "import javax.servlet.http.HttpServletRequest\n"),
  K('fun fetch(request: HttpServletRequest): String {\n    val id = request.getParameter("id").toLong()\n    return java.net.URL("https://api.example.com/items/$id").readText()\n}\n', "import javax.servlet.http.HttpServletRequest\n"))
T("kotlin", "redirect",
  K('fun next(request: HttpServletRequest, response: HttpServletResponse) {\n    response.sendRedirect(request.getParameter("next"))\n}\n', "import javax.servlet.http.*\n"),
  K('fun next(request: HttpServletRequest, response: HttpServletResponse) {\n    response.sendRedirect("/home")\n}\n', "import javax.servlet.http.*\n"))

# ------------------------------------------------------------------ Python
F = "from flask import Flask, request\napp = Flask(__name__)\n\n"
T("python", "sqli",
  F + '@app.route("/user")\ndef user():\n    name = request.args.get("name")\n    cur = db.cursor()\n    cur.execute("SELECT * FROM users WHERE name = \'%s\'" % name)\n    return cur.fetchall()\n',
  F + '@app.route("/user")\ndef user():\n    name = request.args.get("name")\n    cur = db.cursor()\n    cur.execute("SELECT * FROM users WHERE name = ?", (name,))\n    return cur.fetchall()\n',
  fp=[F + '@app.route("/user")\ndef user():\n    uid = int(request.args.get("id"))\n    db.cursor().execute("SELECT * FROM users WHERE id = %d" % uid)\n'])
T("python", "cmdi",
  F + 'import os\n\n@app.route("/ping")\ndef ping():\n    host = request.args.get("host")\n    os.system("ping -c 1 " + host)\n    return "ok"\n',
  F + 'import subprocess\n\n@app.route("/ping")\ndef ping():\n    host = request.args.get("host")\n    subprocess.run(["ping", "-c", "1", host])\n    return "ok"\n')
T("python", "path",
  F + 'import os\n\n@app.route("/file")\ndef file():\n    name = request.args.get("name")\n    with open(os.path.join("/var/data", name)) as f:\n        return f.read()\n',
  F + 'import os\nfrom werkzeug.utils import secure_filename\n\n@app.route("/file")\ndef file():\n    name = secure_filename(request.args.get("name"))\n    with open(os.path.join("/var/data", name)) as f:\n        return f.read()\n')
T("python", "ldap",
  F + 'import ldap\n\n@app.route("/who")\ndef who():\n    user = request.args.get("user")\n    return str(conn.search_s("ou=people,dc=example,dc=com", ldap.SCOPE_SUBTREE, "(uid=%s)" % user))\n',
  F + 'import ldap\nfrom ldap.filter import escape_filter_chars\n\n@app.route("/who")\ndef who():\n    user = escape_filter_chars(request.args.get("user"))\n    return str(conn.search_s("ou=people,dc=example,dc=com", ldap.SCOPE_SUBTREE, "(uid=%s)" % user))\n')
T("python", "xss",
  F + '@app.route("/hello")\ndef hello():\n    name = request.args.get("name", "")\n    return "<h1>Hello " + name + "</h1>"\n',
  F + 'from markupsafe import escape\n\n@app.route("/hello")\ndef hello():\n    name = request.args.get("name", "")\n    return "<h1>Hello " + escape(name) + "</h1>"\n',
  fp=[F + 'from flask import render_template\n\n@app.route("/hello")\ndef hello():\n    return render_template("hello.html", name=request.args.get("name"))\n',
      {"code": F + '@app.post("/add")\ndef add():\n    a = request.form.get("a", type=int)\n    return "<p>" + str(a) + "</p>"\n', "note": "corpus flask examples/celery: type=int converts"},
      {"code": F + '@app.get("/result/<id>")\ndef result(id: str):\n    return {"id": id, "ready": False}\n', "note": "corpus flask examples/celery: dict return is JSON"},
      {"code": F + 'from flask import make_response\n\n@app.get("/r")\ndef r_get():\n    return r_post()\n\n@app.post("/r")\ndef r_post():\n    ref = request.headers.get("Referer", "")\n    resp = make_response(("Saved", {"X-Ref": ref}))\n    return resp\n', "note": "OWASP Benchmark Python 00591: GET wrapper returning the POST handler; value only in a response header"}])
T("python", "ssrf",
  F + 'import requests\n\n@app.route("/proxy")\ndef proxy():\n    url = request.args.get("url")\n    return requests.get(url).text\n',
  F + 'import requests\n\n@app.route("/proxy")\ndef proxy():\n    q = request.args.get("q")\n    return requests.get("https://api.example.com/search", params={"q": q}).text\n')
T("python", "redirect",
  F + 'from flask import redirect\n\n@app.route("/go")\ndef go():\n    return redirect(request.args.get("next"))\n',
  F + 'from flask import redirect, url_for\n\n@app.route("/go")\ndef go():\n    return redirect(url_for("index"))\n')
T("python", "xpath",
  F + 'from lxml import etree\n\n@app.route("/find")\ndef find():\n    name = request.args.get("name")\n    return str(tree.xpath("//user[@name=\'%s\']" % name))\n',
  F + 'from lxml import etree\n\n@app.route("/find")\ndef find():\n    name = request.args.get("name")\n    return str(tree.xpath("//user[@name=$name]", name=name))\n')
T("python", "code",
  F + '@app.route("/calc")\ndef calc():\n    return str(eval(request.args.get("expr")))\n',
  F + 'import ast\n\n@app.route("/calc")\ndef calc():\n    return str(ast.literal_eval(request.args.get("expr")))\n')

# ------------------------------------------------------------------ JavaScript / TypeScript
E = lambda req, body: req + "const app = require('express')();\n\napp.get('/x', (req, res) => {\n" + body + "});\n"
T("javascript", "sqli",
  E("const mysql = require('mysql2');\nconst db = mysql.createConnection({});\n", "  db.query(\"SELECT * FROM users WHERE id = '\" + req.query.id + \"'\", (err, rows) => res.json(rows));\n"),
  E("const mysql = require('mysql2');\nconst db = mysql.createConnection({});\n", "  db.query('SELECT * FROM users WHERE id = ?', [req.query.id], (err, rows) => res.json(rows));\n"))
T("javascript", "cmdi",
  E("const { exec } = require('child_process');\n", "  exec('ls -l ' + req.query.dir, (err, out) => res.send(out));\n"),
  E("const { execFile } = require('child_process');\n", "  execFile('ls', ['-l', '--', req.query.dir], (err, out) => res.json({ out }));\n"))
T("javascript", "path",
  E("const fs = require('fs');\nconst path = require('path');\n", "  fs.readFile(path.join(__dirname, 'files', req.params.name), (err, data) => res.json({ data }));\n"),
  E("const fs = require('fs');\nconst path = require('path');\n", "  fs.readFile(path.join(__dirname, 'files', path.basename(req.params.name)), (err, data) => res.json({ data }));\n"))
T("javascript", "ldap",
  E("const ldap = require('ldapjs');\nconst client = ldap.createClient({ url: 'ldap://localhost' });\n", "  client.search('ou=people,dc=example,dc=com', { filter: '(uid=' + req.query.user + ')' }, () => res.end());\n"),
  E("const ldap = require('ldapjs');\nconst client = ldap.createClient({ url: 'ldap://localhost' });\n", "  const f = new ldap.EqualityFilter({ attribute: 'uid', value: req.query.user });\n  client.search('ou=people,dc=example,dc=com', { filter: 'objectClass=person' }, () => res.end());\n"))
T("javascript", "xss",
  E("", "  res.send('<p>Hello ' + req.query.name + '</p>');\n"),
  E("const escapeHtml = require('escape-html');\n", "  res.send('<p>Hello ' + escapeHtml(req.query.name) + '</p>');\n"))
T("javascript", "ssrf",
  E("", "  fetch(req.query.url).then(r => r.text()).then(t => res.json({ t }));\n"),
  E("", "  const id = Number(req.query.id);\n  fetch('https://api.example.com/items/' + id).then(r => r.text()).then(t => res.json({ t }));\n"))
T("javascript", "redirect",
  E("", "  res.redirect(req.query.next);\n"),
  E("", "  res.redirect('/home');\n"))
T("javascript", "code",
  E("", "  res.json({ result: eval(req.body.expr) });\n"),
  E("", "  res.json({ result: JSON.parse(req.body.expr) });\n"))

# ------------------------------------------------------------------ PHP
H = lambda s: "<?php\n" + s
T("php", "sqli",
  H('$id = $_GET["id"];\n$result = mysqli_query($conn, "SELECT * FROM users WHERE id = \'" . $id . "\'");\n'),
  H('$stmt = $pdo->prepare("SELECT * FROM users WHERE id = ?");\n$stmt->execute([$_GET["id"]]);\n'),
  fp=[H('$id = intval($_GET["id"]);\n$result = mysqli_query($conn, "SELECT * FROM users WHERE id = " . $id);\n')])
T("php", "cmdi",
  H('$host = $_GET["host"];\nsystem("ping -c 1 " . $host);\n'),
  H('$host = escapeshellarg($_GET["host"]);\nsystem("ping -c 1 " . $host);\n'))
T("php", "path",
  H('$file = $_GET["file"];\necho file_get_contents("/var/data/" . $file);\n'),
  H('$file = basename($_GET["file"]);\n$data = file_get_contents("/var/data/" . $file);\n'))
T("php", "ldap",
  H('$user = $_GET["user"];\n$sr = ldap_search($ds, "ou=people,dc=example,dc=com", "(uid=" . $user . ")");\n'),
  H('$user = ldap_escape($_GET["user"], "", LDAP_ESCAPE_FILTER);\n$sr = ldap_search($ds, "ou=people,dc=example,dc=com", "(uid=" . $user . ")");\n'))
T("php", "xss",
  H('$name = $_GET["name"];\necho "<p>Hello " . $name . "</p>";\n'),
  H('$name = $_GET["name"];\necho "<p>Hello " . htmlspecialchars($name, ENT_QUOTES, "UTF-8") . "</p>";\n'))
T("php", "ssrf",
  H('$url = $_GET["url"];\n$ch = curl_init($url);\ncurl_exec($ch);\n'),
  H('$id = intval($_GET["id"]);\n$ch = curl_init("https://api.example.com/items/" . $id);\ncurl_exec($ch);\n'))
T("php", "redirect",
  H('header("Location: " . $_GET["next"]);\n'),
  H('header("Location: /home");\n'))
T("php", "xpath",
  H('$xp = new DOMXPath($doc);\n$nodes = $xp->query("//user[@name=\'" . $_GET["name"] . "\']");\n'),
  H('$xp = new DOMXPath($doc);\n$nodes = $xp->query("//user[@active=\'1\']");\n'))
T("php", "code",
  H('eval($_POST["code"]);\n'),
  H('$data = json_decode($_POST["code"], true);\n'))

# ------------------------------------------------------------------ Go
G = lambda imports, body: "package main\n\nimport (\n" + "".join(f'\t"{i}"\n' for i in imports) + ")\n\nfunc handler(w http.ResponseWriter, r *http.Request) {\n" + body + "}\n"
T("go", "sqli",
  G(["database/sql", "net/http"], '\tid := r.URL.Query().Get("id")\n\trows, _ := db.Query("SELECT * FROM users WHERE id = \'" + id + "\'")\n\tdefer rows.Close()\n'),
  G(["database/sql", "net/http"], '\tid := r.URL.Query().Get("id")\n\trows, _ := db.Query("SELECT * FROM users WHERE id = ?", id)\n\tdefer rows.Close()\n'),
  fp=[G(["database/sql", "net/http", "strconv"], '\tid, _ := strconv.Atoi(r.URL.Query().Get("id"))\n\trows, _ := db.Query(fmt.Sprintf("SELECT * FROM users WHERE id = %d", id))\n\tdefer rows.Close()\n')])
T("go", "cmdi",
  G(["net/http", "os/exec"], '\thost := r.URL.Query().Get("host")\n\tout, _ := exec.Command("sh", "-c", "ping -c 1 "+host).Output()\n\tw.Write(out)\n'),
  G(["net/http", "os/exec", "strconv"], '\tn, _ := strconv.Atoi(r.URL.Query().Get("n"))\n\tout, _ := exec.Command("ping", "-c", strconv.Itoa(n), "localhost").Output()\n\t_ = out\n'))
T("go", "path",
  G(["net/http", "os", "path/filepath"], '\tname := r.URL.Query().Get("file")\n\tdata, _ := os.ReadFile(filepath.Join("/var/data", name))\n\t_ = data\n'),
  G(["net/http", "os", "path/filepath"], '\tname := filepath.Base(r.URL.Query().Get("file"))\n\tdata, _ := os.ReadFile(filepath.Join("/var/data", name))\n\t_ = data\n'),
  fp=[{"code": G(["net/http"], '\thttp.ServeFile(w, r, r.URL.Path)\n'), "note": "corpus grpc-gateway: ServeFile rejects .. in the request path"},
      {"code": G(["net/http", "path", "strings"], '\tp := strings.TrimPrefix(r.URL.Path, "/openapiv2/")\n\tp = path.Join(dir, p)\n\thttp.ServeFile(w, r, p)\n'), "note": "corpus grpc-gateway openAPIServer: name derived only from r.URL.Path, which ServeFile screens for .."}])
T("go", "ldap",
  G(["net/http", "github.com/go-ldap/ldap/v3"], '\tuser := r.URL.Query().Get("user")\n\treq := ldap.NewSearchRequest("ou=people,dc=example,dc=com", ldap.ScopeWholeSubtree, ldap.NeverDerefAliases, 0, 0, false, "(uid="+user+")", nil, nil)\n\t_ = req\n'),
  G(["net/http", "github.com/go-ldap/ldap/v3"], '\tuser := ldap.EscapeFilter(r.URL.Query().Get("user"))\n\treq := ldap.NewSearchRequest("ou=people,dc=example,dc=com", ldap.ScopeWholeSubtree, ldap.NeverDerefAliases, 0, 0, false, "(uid="+user+")", nil, nil)\n\t_ = req\n'))
T("go", "xss",
  G(["fmt", "net/http"], '\tname := r.URL.Query().Get("name")\n\tfmt.Fprintf(w, "<p>Hello %s</p>", name)\n'),
  G(["fmt", "html", "net/http"], '\tname := r.URL.Query().Get("name")\n\tfmt.Fprintf(w, "<p>Hello %s</p>", html.EscapeString(name))\n'))
T("go", "ssrf",
  G(["net/http"], '\tresp, _ := http.Get(r.URL.Query().Get("url"))\n\tdefer resp.Body.Close()\n'),
  G(["net/http", "strconv"], '\tid, _ := strconv.Atoi(r.URL.Query().Get("id"))\n\tresp, _ := http.Get("https://api.example.com/items/" + strconv.Itoa(id))\n\tdefer resp.Body.Close()\n'))
T("go", "redirect",
  G(["net/http"], '\thttp.Redirect(w, r, r.URL.Query().Get("next"), http.StatusFound)\n'),
  G(["net/http"], '\thttp.Redirect(w, r, "/home", http.StatusFound)\n'))

# ------------------------------------------------------------------ regex injection / ReDoS
T("java", "regex",
  J('  boolean find(HttpServletRequest request, String text) {\n    String q = request.getParameter("q");\n    return java.util.regex.Pattern.compile(q).matcher(text).find();\n  }\n', "import javax.servlet.http.*;\n"),
  J('  boolean find(HttpServletRequest request, String text) {\n    String q = request.getParameter("q");\n    return java.util.regex.Pattern.compile(java.util.regex.Pattern.quote(q)).matcher(text).find();\n  }\n', "import javax.servlet.http.*;\n"))
T("kotlin", "regex",
  K('fun find(request: HttpServletRequest, text: String): Boolean {\n    val q = request.getParameter("q")\n    return Regex(q).containsMatchIn(text)\n}\n'),
  K('fun find(request: HttpServletRequest, text: String): Boolean {\n    val q = request.getParameter("q")\n    return Regex(Regex.escape(q)).containsMatchIn(text)\n}\n'))
T("python", "regex",
  F + 'import re\n\n@app.route("/s")\ndef s():\n    q = request.args.get("q", "")\n    return str(bool(re.search(q, TEXT)))\n',
  F + 'import re\n\n@app.route("/s")\ndef s():\n    q = request.args.get("q", "")\n    return str(bool(re.search(re.escape(q), TEXT)))\n')
T("javascript", "regex",
  E("", "  const re = new RegExp(req.query.q);\n  res.json({ ok: re.test(TEXT) });\n"),
  E("const escapeStringRegexp = require('escape-string-regexp');\n", "  const re = new RegExp(escapeStringRegexp(req.query.q));\n  res.json({ ok: re.test(TEXT) });\n"))
T("php", "regex",
  H('$q = $_GET["q"];\n$ok = preg_match("/" . $q . "/", $text);\n'),
  H('$q = preg_quote($_GET["q"], "/");\n$ok = preg_match("/" . $q . "/", $text);\n'))
T("go", "regex",
  G(["net/http", "regexp"], '\tre, _ := regexp.Compile(r.URL.Query().Get("q"))\n\t_ = re\n'),
  G(["net/http", "regexp"], '\tre, _ := regexp.Compile(regexp.QuoteMeta(r.URL.Query().Get("q")))\n\t_ = re\n'))
P.R[-1]["message"] = ("Request data is compiled as a regular expression. Go's RE2 engine runs in linear time, so this is not a ReDoS, but the "
                      "pattern still decides what matches (a validation bypass); escape it with regexp.QuoteMeta when it is meant literally.")
P.R[-1]["severity"] = "minor"

# ------------------------------------------------------------------ mail header / recipient injection
T("java", "smtp",
  J('  void send(HttpServletRequest request, Session s) throws Exception {\n    MimeMessage m = new MimeMessage(s);\n    m.setSubject(request.getParameter("subject"));\n    Transport.send(m);\n  }\n', "import javax.mail.*;\nimport javax.mail.internet.*;\nimport javax.servlet.http.*;\n"),
  J('  void send(HttpServletRequest request, Session s) throws Exception {\n    MimeMessage m = new MimeMessage(s);\n    m.setSubject("Contact form");\n    Transport.send(m);\n  }\n', "import javax.mail.*;\nimport javax.mail.internet.*;\nimport javax.servlet.http.*;\n"))
T("python", "smtp",
  F + 'import smtplib\n\n@app.post("/contact")\ndef contact():\n    to = request.form["to"]\n    with smtplib.SMTP("localhost") as s:\n        s.sendmail("noreply@example.com", to, "Subject: hi\\r\\n\\r\\nhello")\n    return "ok"\n',
  F + 'import smtplib\n\n@app.post("/contact")\ndef contact():\n    with smtplib.SMTP("localhost") as s:\n        s.sendmail("noreply@example.com", "support@example.com", "Subject: contact\\r\\n\\r\\n" + "new message")\n    return "ok"\n')
T("javascript", "smtp",
  E("const nodemailer = require('nodemailer');\n", "  transporter.sendMail({ from: 'noreply@example.com', to: req.body.email, subject: 'Welcome' });\n  res.send('ok');\n"),
  E("const nodemailer = require('nodemailer');\n", "  transporter.sendMail({ from: 'noreply@example.com', to: 'support@example.com', subject: 'Contact form' });\n  res.send('ok');\n"))
T("php", "smtp",
  H('$from = $_POST["email"];\nmail("support@example.com", "Contact", $_POST["message"], "From: " . $from);\n'),
  H('mail("support@example.com", "Contact", "A visitor sent a message.", "From: noreply@example.com");\n'))
T("go", "smtp",
  G(["net/http", "net/smtp"], '\tto := r.FormValue("to")\n\t_ = smtp.SendMail("localhost:25", nil, "noreply@example.com", []string{to}, []byte("Subject: hi\\r\\n\\r\\nhello"))\n'),
  G(["net/http", "net/smtp"], '\t_ = smtp.SendMail("localhost:25", nil, "noreply@example.com", []string{"support@example.com"}, []byte("Subject: contact\\r\\n\\r\\nhello"))\n'))

# ------------------------------------------------------------------ Kotlin code evaluation (CWE-94)
T("kotlin", "code",
  K('fun calc(request: HttpServletRequest, engine: ScriptEngine): Any? {\n    val expr = request.getParameter("expr")\n    return engine.eval(expr)\n}\n', "import javax.script.ScriptEngine\nimport javax.servlet.http.HttpServletRequest\n"),
  K('fun calc(request: HttpServletRequest, engine: ScriptEngine): Any? {\n    val n = request.getParameter("n").toInt()\n    return engine.eval("1 + 1")\n}\n', "import javax.script.ScriptEngine\nimport javax.servlet.http.HttpServletRequest\n"))

# ------------------------------------------------------------------ trust boundary (session stores)
T("java", "trust",
  J('  void save(HttpServletRequest request) {\n    String user = request.getParameter("user");\n    request.getSession().setAttribute("user", user);\n  }\n', "import javax.servlet.http.*;\n"),
  J('  void save(HttpServletRequest request) {\n    String user = request.getParameter("user");\n    if (!user.matches("[a-z]{1,16}")) return;\n    request.getSession().setAttribute("visits", 1);\n  }\n', "import javax.servlet.http.*;\n"),
  fp=[{"code": J('  void save(HttpServletRequest request) {\n    String p = request.getParameter("p");\n    double r = new java.util.Random().nextDouble();\n    request.getSession().setAttribute("rememberMe", Double.toString(r));\n  }\n', "import javax.servlet.http.*;\n"),
       "note": "OWASP Benchmark weakrand: session value is a random number, not request data"}])
T("kotlin", "trust",
  K('fun save(request: HttpServletRequest) {\n    val user = request.getParameter("user")\n    request.session.setAttribute("user", user)\n}\n'),
  K('fun save(request: HttpServletRequest) {\n    val n = request.getParameter("n").toInt()\n    request.session.setAttribute("visits", 1)\n}\n'))
T("python", "trust",
  F + 'from flask import session\n\n@app.post("/login")\ndef login():\n    session["user"] = request.form.get("user")\n    return "ok"\n',
  F + 'from flask import session\n\n@app.post("/login")\ndef login():\n    user = request.form.get("user")\n    session["visits"] = session.get("visits", 0) + 1\n    return "ok"\n',
  fp=[{"code": F + 'import flask\n\n@app.post("/t")\ndef t():\n    param = request.cookies.get("c", "")\n    bar = "safe"\n    if "should" in "This should never happen":\n        bar = "constant"\n    flask.session[bar] = "12345"\n    return "ok"\n',
       "note": "OWASP Benchmark Python trustbound: key is constant on every path"}])
T("javascript", "trust",
  E("", "  req.session[req.query.key] = 'x';\n  res.send('ok');\n"),
  E("", "  req.session['visits'] = (req.session['visits'] || 0) + 1;\n  res.send('ok');\n"))
T("php", "trust",
  H('$_SESSION["user"] = $_POST["user"];\n'),
  H('$_SESSION["visits"] = ($_SESSION["visits"] ?? 0) + 1;\n'))
T("go", "trust",
  G(["net/http", "github.com/gorilla/sessions"], '\tsession, _ := store.Get(r, "s")\n\tsession.Values["user"] = r.FormValue("user")\n\t_ = session.Save(r, w)\n'),
  G(["net/http", "github.com/gorilla/sessions"], '\tsession, _ := store.Get(r, "s")\n\tsession.Values["visits"] = 1\n\t_ = session.Save(r, w)\n'))

RULES = P.R

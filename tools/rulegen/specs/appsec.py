"""AppSec pack: cross-language security rules filling OWASP ASVS 5.0 / Top 10 checklist gaps that the
per-language packs do not cover (static IVs, cleartext WebSockets, GraphQL introspection, proxy trust,
version disclosure, directory listings, secrets in browser storage, prototype pollution, unsafe
deserialisation, error details sent to clients, JNDI lookups, Kotlin CORS/XXE/script eval).
Detection and wording are crev's own; quotes come from the cited official pages (OWASP Cheat Sheet
Series, CC BY-SA 4.0: cited, not copied)."""
from specs._common import Pack

P = Pack("APPSEC", "javascript", "OWASP Cheat Sheet Series (current)", {"ecmascript": ">=2015"})
CS = "https://cheatsheetseries.owasp.org/cheatsheets/"
CRYPTO = CS + "Cryptographic_Storage_Cheat_Sheet.html"
IV_Q = "initialization vector (IV) uniqueness across all instances sharing the key"
ERR = CS + "Error_Handling_Cheat_Sheet.html"
ERR_Q = "a generic response is returned by the application but the error details are logged server side"
LOCAL = r"(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])"
PYA = {"python": ">=3.8"}
GOA = {"go": ">=1.18"}
JA = {"java": ">=8"}
KA = {"kotlin": ">=1.6"}


def sec(id, title, url, needle, query, bad, good, msg, sev="major", **kw):
    return P(id, title, url, needle, query, bad, good, msg, sev=sev, kind="security", cat="security", **kw)


# ------------------------------------------------------------------ V11.3.4 static / zero IVs (CWE-329, CWE-1204)
IV_MSG = "The IV/nonce is a constant, so every message encrypted with this key reuses it: equal plaintexts give equal ciphertexts (CBC) or the keystream repeats (CTR/GCM). Generate a fresh random IV per message and store it with the ciphertext."
sec("JS-STATIC-IV", "createCipheriv with a constant IV", CRYPTO, IV_Q,
    r'''((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments (_) (_) [(string) (call_expression function: (member_expression object: (identifier) @b property: (property_identifier) @a) arguments: (arguments . [(string) (number)]))] @iv)) @match (#eq? @p "createCipheriv") (#eq? @b "Buffer") (#match? @a "^(from|alloc)$"))''',
    "const c = crypto.createCipheriv('aes-256-cbc', key, Buffer.alloc(16))\n",
    "const iv = crypto.randomBytes(16)\nconst c = crypto.createCipheriv('aes-256-cbc', key, iv)\n",
    IV_MSG, cwe=["CWE-329", "CWE-1204"], asvs=["V11.3.4"])

sec("PY-STATIC-IV", "Cipher mode created with a constant IV/nonce", CRYPTO, IV_Q,
    r"""[((call function: (attribute attribute: (identifier) @m) arguments: (argument_list . (string) @iv)) @match (#match? @m "^(CBC|CTR|OFB|CFB|CFB8|GCM)$"))
         ((call function: (attribute object: (identifier) @o attribute: (identifier) @n) arguments: (argument_list (keyword_argument name: (identifier) @k value: (string)))) @match (#match? @o "^(AES|DES3|ChaCha20|ChaCha20_Poly1305|Blowfish|CAST|ARC2)$") (#eq? @n "new") (#match? @k "^(iv|nonce)$"))]""",
    "cipher = Cipher(algorithms.AES(key), modes.CBC(b'0000000000000000'))\n",
    "iv = os.urandom(16)\ncipher = Cipher(algorithms.AES(key), modes.CBC(iv))\n",
    IV_MSG, lang="python", applies=PYA, files=["**/*.py"], cwe=["CWE-329", "CWE-1204"], asvs=["V11.3.4"],
    fp=["cipher = AES.new(key, AES.MODE_GCM, nonce=get_random_bytes(12))\n"])
sec("GO-STATIC-IV", "Block mode created with a constant IV", CRYPTO, IV_Q,
    r"""((call_expression function: (selector_expression operand: (identifier) @pkg field: (field_identifier) @f) arguments: (argument_list (_) [(type_conversion_expression operand: (interpreted_string_literal)) (call_expression function: (identifier) @mk) (composite_literal)] @iv)) @match (#eq? @pkg "cipher") (#match? @f "^(NewCBCEncrypter|NewCBCDecrypter|NewCTR|NewOFB|NewCFBEncrypter|NewCFBDecrypter)$"))""",
    'package p\n\nimport "crypto/cipher"\n\nfunc enc(b cipher.Block) cipher.BlockMode {\n\treturn cipher.NewCBCEncrypter(b, []byte("0123456789abcdef"))\n}\n',
    'package p\n\nimport (\n\t"crypto/cipher"\n\t"crypto/rand"\n)\n\nfunc enc(b cipher.Block) cipher.BlockMode {\n\tiv := make([]byte, b.BlockSize())\n\trand.Read(iv)\n\treturn cipher.NewCBCEncrypter(b, iv)\n}\n',
    IV_MSG, lang="go", applies=GOA, files=["**/*.go"], cwe=["CWE-329", "CWE-1204"], asvs=["V11.3.4"])
sec("JAVA-STATIC-IV", "IvParameterSpec built from a constant", CRYPTO, IV_Q,
    r"""((object_creation_expression type: (type_identifier) @t arguments: (argument_list . [(array_creation_expression) (method_invocation object: (string_literal) name: (identifier) @g)])) @match (#match? @t "^(IvParameterSpec|GCMParameterSpec)$"))""",
    'class C {\n  Cipher c(Key k) throws Exception {\n    Cipher c = Cipher.getInstance("AES/CBC/PKCS5Padding");\n    c.init(Cipher.ENCRYPT_MODE, k, new IvParameterSpec(new byte[16]));\n    return c;\n  }\n}\n',
    'class C {\n  Cipher c(Key k, SecureRandom r) throws Exception {\n    byte[] iv = new byte[16];\n    r.nextBytes(iv);\n    Cipher c = Cipher.getInstance("AES/CBC/PKCS5Padding");\n    c.init(Cipher.ENCRYPT_MODE, k, new IvParameterSpec(iv));\n    return c;\n  }\n}\n',
    IV_MSG, lang="java", applies=JA, files=["**/*.java"], cwe=["CWE-329", "CWE-1204"], asvs=["V11.3.4"],
    fp=['class C { GCMParameterSpec s(byte[] iv) { return new GCMParameterSpec(128, iv); } }\n'])

# ------------------------------------------------------------------ V4.4.1 cleartext WebSocket (CWE-319)
WS = CS + "WebSocket_Security_Cheat_Sheet.html"
WS_MSG = "The WebSocket connects over ws://, so messages (and any token sent on them) travel unencrypted and can be read or injected on the network. Use wss://."
sec("JS-WS-CLEARTEXT", "WebSocket opened over cleartext ws://", WS, "Insecure - never use in production",
    r"""((new_expression constructor: (identifier) @c arguments: (arguments . [(string) (template_string)] @u)) @match (#match? @c "^(WebSocket|ReconnectingWebSocket)$") (#match? @u "^['\"`]ws://"))""",
    "const socket = new WebSocket('ws://chat.example.com/socket')\n", "const socket = new WebSocket('wss://chat.example.com/socket')\n",
    WS_MSG, cwe=["CWE-319"], asvs=["V4.4.1"], filters=["node.lacks_re:ws://" + LOCAL],
    fp=["const dev = new WebSocket('ws://localhost:8080/hmr')\n"])
sec("PY-WS-CLEARTEXT", "WebSocket client connecting over ws://", WS, "Insecure - never use in production",
    r"""((call function: [(attribute attribute: (identifier) @f) (identifier) @f] arguments: (argument_list . (string) @u)) @match (#match? @f "^(connect|create_connection|WebSocketApp|ws_connect)$") (#match? @u "^[rbf]?['\"]ws://"))""",
    "ws = websocket.create_connection('ws://feed.example.com/stream')\n", "ws = websocket.create_connection('wss://feed.example.com/stream')\n",
    WS_MSG, lang="python", applies=PYA, files=["**/*.py"], cwe=["CWE-319"], asvs=["V4.4.1"], filters=["node.lacks_re:ws://" + LOCAL])

# ------------------------------------------------------------------ V4.3.2 GraphQL introspection (CWE-200)
GQL = "https://www.apollographql.com/docs/apollo-server/api/apollo-server"
sec("JS-GRAPHQL-INTROSPECTION", "Apollo Server with introspection forced on", CS + "GraphQL_Cheat_Sheet.html",
    "Disable insecure default configurations ( e.g. excessive errors, introspection, GraphiQL, etc.)",
    r"""((new_expression constructor: (identifier) @c arguments: (arguments (object (pair key: (property_identifier) @k value: (true)) @match))) (#match? @c "^(ApolloServer|ApolloServerBase)$") (#eq? @k "introspection"))""",
    "const server = new ApolloServer({ typeDefs, resolvers, introspection: true })\n",
    "const server = new ApolloServer({ typeDefs, resolvers, introspection: process.env.NODE_ENV !== 'production' })\n",
    "introspection: true publishes the whole schema (every type, field and argument) in production too, which maps the API for attackers. Leave the default (off when NODE_ENV=production) or tie it to the environment.",
    sev="minor", mode="ai-confirm", ai="Is this server deployed to production and the schema not meant to be public?", cwe=["CWE-200"], asvs=["V4.3.2"],
    docv="OWASP GraphQL Cheat Sheet")

# ------------------------------------------------------------------ V4.1.3 trust proxy (CWE-348)
sec("JS-TRUST-PROXY-ALL", "Express trusts X-Forwarded-* from any hop", "https://expressjs.com/en/guide/behind-proxies.html",
    "it is important to ensure that the last reverse proxy trusted is removing/overwriting all of the following HTTP headers",
    r"""((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (string (string_fragment) @k) . (true) .)) @match (#eq? @p "set") (#eq? @k "trust proxy"))""",
    "app.set('trust proxy', true)\n", "app.set('trust proxy', 1)\n",
    "With trust proxy = true, req.ip, req.protocol and req.hostname come from client-supplied X-Forwarded-* headers unless every proxy in front rewrites them, so rate limits, IP allow-lists and logs can be spoofed. Trust a hop count or the proxy addresses instead.",
    sev="minor", mode="ai-confirm", ai="Is req.ip / req.hostname / req.protocol used for security decisions (rate limiting, allow-lists, redirects) in this app?",
    cwe=["CWE-348"], asvs=["V4.1.3"], docv="Express 5 guide")

# ------------------------------------------------------------------ V13.4.6 version disclosure (CWE-497)
sec("JS-EXPRESS-POWERED-BY", "Express app keeps the X-Powered-By header", "https://expressjs.com/en/advanced/best-practice-security.html",
    "By default, Express sends the X-Powered-By response header that you can disable using the app.disable() method",
    r"""((variable_declarator value: (call_expression function: (identifier) @f arguments: (arguments) @a)) @match (#eq? @f "express"))""",
    "const express = require('express')\nconst app = express()\napp.get('/', (req, res) => res.send('ok'))\napp.listen(3000)\n",
    "const express = require('express')\nconst app = express()\napp.disable('x-powered-by')\napp.listen(3000)\n",
    "Express announces itself in an X-Powered-By header, which helps automated scanners pick exploits. Call app.disable('x-powered-by') or use helmet.",
    sev="info", cwe=["CWE-497"], asvs=["V13.4.6"], docv="Express production best practices: security",
    filters=["file.lacks_re:(?i)x-powered-by|helmet|hidePoweredBy", "file.has_re:\\.listen\\("],
    fp=["const app = express()\napp.use(helmet())\napp.listen(3000)\n", "const app = express()\napp.get('/', h)\nmodule.exports = app\n"])

# ------------------------------------------------------------------ V13.4.3 directory listing (CWE-548)
sec("JS-SERVE-INDEX", "Directory listing served (serve-index)", "https://expressjs.com/en/resources/middleware/serve-index.html",
    "Serves pages that contain directory listings for a given path",
    r"""((call_expression function: (identifier) @f) @match (#eq? @f "serveIndex"))""",
    "app.use('/files', serveIndex('public/files', { icons: true }))\n", "app.use('/files', express.static('public/files'))\n",
    "Directory listings reveal every file under the path, including backups and files never meant to be linked. Serve known files only.",
    sev="minor", mode="ai-confirm", ai="Is the listed directory intended to be publicly browsable and free of sensitive files?", cwe=["CWE-548"], asvs=["V13.4.3"],
    docv="Express middleware docs")

# ------------------------------------------------------------------ V14.3.3 secrets in browser storage (CWE-922)
sec("JS-STORAGE-SECRET", "Credential stored in localStorage/sessionStorage", CS + "HTML5_Security_Cheat_Sheet.html",
    "A single Cross Site Scripting can be used to steal all the data",
    r"""((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p) arguments: (arguments . [(string) (template_string)] @k)) @match (#match? @o "^(localStorage|sessionStorage)$") (#eq? @p "setItem") (#match? @k "(?i)(token|jwt|passw(or)?d|secret|api[_-]?key|credential|private[_-]?key)"))""",
    "localStorage.setItem('accessToken', response.token)\n", "localStorage.setItem('theme', 'dark')\n",
    "Web storage is readable by every script on the origin, so one XSS bug leaks this credential. Keep session tokens in HttpOnly, Secure, SameSite cookies, or in memory.",
    mode="ai-confirm", ai="Is the stored value a credential or session token (not a public, non-sensitive identifier)?", cwe=["CWE-922"], asvs=["V14.3.3"],
    docv="OWASP HTML5 Security Cheat Sheet")

# ------------------------------------------------------------------ V15.3.6 prototype pollution (CWE-1321)
sec("JS-DEEP-MERGE-REQUEST", "Request data deep-merged into an object", CS + "Prototype_Pollution_Prevention_Cheat_Sheet.html",
    "Prototype Pollution is a critical vulnerability that can allow attackers to manipulate an application's JavaScript objects and properties",
    r"""((call_expression function: [(identifier) @f (member_expression property: (property_identifier) @f)] arguments: (arguments (member_expression object: (identifier) @r property: (property_identifier) @q))) @match (#match? @f "^(merge|mergeWith|defaultsDeep|deepmerge|deepMerge|extend|assignDeep|mergeDeep)$") (#match? @r "^(req|request|ctx)$") (#match? @q "^(body|query|params|cookies)$"))""",
    "const settings = _.merge({}, defaults, req.body)\n", "const settings = { ...defaults, theme: String(req.body.theme) }\n",
    "Deep-merging request data copies attacker-chosen keys such as __proto__ or constructor.prototype onto objects, which can change every object in the process. Pick the expected fields explicitly or validate against a schema first.",
    mode="ai-confirm", ai="Can the merged request data contain arbitrary keys (no schema validation stripping __proto__/constructor before the merge)?",
    cwe=["CWE-1321"], asvs=["V15.3.6"], docv="OWASP Prototype Pollution Prevention Cheat Sheet")

# ------------------------------------------------------------------ V1.5.2 node-serialize (CWE-502)
sec("JS-NODE-SERIALIZE", "node-serialize unserialize()", "https://github.com/advisories/GHSA-q4v7-4rhw-9hqm",
    "can be abused to execute arbitrary code via an immediately invoked function expression (IIFE) if untrusted user input is passed into unserialize()",
    r"""((call_expression function: [(identifier) @f (member_expression property: (property_identifier) @f)]) @match (#eq? @f "unserialize"))""",
    "const serialize = require('node-serialize')\nconst prefs = serialize.unserialize(req.cookies.prefs)\n",
    "const prefs = JSON.parse(req.cookies.prefs)\n",
    "node-serialize revives functions, so unserialize() on data an attacker can influence runs their code. Use JSON.parse and validate the result.",
    sev="critical", cwe=["CWE-502"], asvs=["V1.5.2"], docv="GitHub Advisory Database", filters=["file.has_re:node-serialize"])

# ------------------------------------------------------------------ V16.5.1 error details to clients (CWE-209)
ERR_MSG = "The response carries a stack trace or raw exception text, which reveals file paths, library versions and sometimes queries. Log the details server-side and return a generic message with a correlation id."
sec("JS-STACK-IN-RESPONSE", "Stack trace sent in an HTTP response", ERR, ERR_Q,
    r"""((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments [(member_expression property: (property_identifier) @s) (object (pair value: (member_expression property: (property_identifier) @s)))])) @match (#match? @p "^(send|json|end|write|jsonp|render)$") (#eq? @s "stack"))""",
    "app.use((err, req, res, next) => {\n  res.status(500).send(err.stack)\n})\n",
    "app.use((err, req, res, next) => {\n  logger.error(err)\n  res.status(500).json({ error: 'internal error' })\n})\n",
    ERR_MSG, cwe=["CWE-209"], asvs=["V16.5.1"], docv="OWASP Error Handling Cheat Sheet", filters=["func.lacks_re:NODE_ENV|isDev|development"])
sec("PY-TRACEBACK-IN-RESPONSE", "traceback.format_exc() returned to the client", ERR, ERR_Q,
    r"""((call function: (attribute object: (identifier) @t attribute: (identifier) @f)) @match (#eq? @t "traceback") (#match? @f "^(format_exc|format_exception|format_tb)$"))""",
    "@app.errorhandler(Exception)\ndef boom(e):\n    return traceback.format_exc(), 500\n",
    "@app.errorhandler(Exception)\ndef boom(e):\n    app.logger.exception(e)\n    return {'error': 'internal error'}, 500\n",
    ERR_MSG, lang="python", applies=PYA, files=["**/*.py"], cwe=["CWE-209"], asvs=["V16.5.1"], docv="OWASP Error Handling Cheat Sheet",
    filters=["node.has_ancestor:return_statement"])
sec("JAVA-STACKTRACE-TO-RESPONSE", "printStackTrace written to the HTTP response", ERR, ERR_Q,
    r"""((method_invocation name: (identifier) @m arguments: (argument_list [(method_invocation name: (identifier) @g) (object_creation_expression arguments: (argument_list (method_invocation name: (identifier) @g)))])) @match (#eq? @m "printStackTrace") (#match? @g "^(getWriter|getOutputStream)$"))""",
    "class S extends HttpServlet {\n  void h(HttpServletResponse resp, Exception e) throws IOException {\n    e.printStackTrace(resp.getWriter());\n  }\n}\n",
    "class S extends HttpServlet {\n  void h(HttpServletResponse resp, Exception e) throws IOException {\n    log.error(\"request failed\", e);\n    resp.sendError(500);\n  }\n}\n",
    ERR_MSG, lang="java", applies=JA, files=["**/*.java"], cwe=["CWE-209"], asvs=["V16.5.1"], docv="OWASP Error Handling Cheat Sheet")
sec("GO-ERR-TO-CLIENT", "err.Error() written to the HTTP response", ERR, ERR_Q,
    r"""((call_expression function: (selector_expression operand: (identifier) @pkg field: (field_identifier) @f) arguments: (argument_list (_) (call_expression function: (selector_expression field: (field_identifier) @e)) (_))) @match (#eq? @pkg "http") (#eq? @f "Error") (#eq? @e "Error"))""",
    'package p\n\nimport "net/http"\n\nfunc h(w http.ResponseWriter, r *http.Request) {\n\tif err := save(r); err != nil {\n\t\thttp.Error(w, err.Error(), http.StatusInternalServerError)\n\t}\n}\n',
    'package p\n\nimport (\n\t"log"\n\t"net/http"\n)\n\nfunc h(w http.ResponseWriter, r *http.Request) {\n\tif err := save(r); err != nil {\n\t\tlog.Printf("save: %v", err)\n\t\thttp.Error(w, "internal error", http.StatusInternalServerError)\n\t}\n}\n',
    "Raw error text from the server reaches the client; database and file-system errors often include queries, paths or hostnames. Log err and send a generic message.",
    sev="minor", lang="go", applies=GOA, files=["**/*.go"], mode="ai-confirm",
    ai="Can this error come from an internal component (database, file system, upstream service) rather than being a validation message meant for the user?",
    cwe=["CWE-209"], asvs=["V16.5.1"], docv="OWASP Error Handling Cheat Sheet")

# ------------------------------------------------------------------ V1.3.8 JNDI lookup (CWE-74)
sec("JAVA-JNDI-LOOKUP-DYNAMIC", "JNDI lookup with a non-constant name", "https://docs.oracle.com/en/java/javase/21/docs/api/java.naming/javax/naming/Context.html",
    "Retrieves the named object",
    r"""((method_invocation object: (_) name: (identifier) @m arguments: (argument_list . [(identifier) (binary_expression) (method_invocation)] .)) @match (#eq? @m "lookup"))""",
    "class C {\n  Object find(String name) throws NamingException {\n    return new InitialContext().lookup(name);\n  }\n}\n",
    "class C {\n  Object find() throws NamingException {\n    return new InitialContext().lookup(\"java:comp/env/jdbc/app\");\n  }\n}\n",
    "A JNDI name that an attacker can influence (ldap://, rmi://) can load and run remote classes. Look up fixed names only, or validate against an allow-list of java:comp/env/ names.",
    sev="major", lang="java", applies=JA, files=["**/*.java"], mode="ai-confirm", ai="Can the looked-up name be influenced by request data or other untrusted input?",
    cwe=["CWE-74"], asvs=["V1.3.8"], docv="Java SE 21 API", filters=["file.has_re:javax\\.naming|InitialContext|InitialDirContext"])

# ------------------------------------------------------------------ Kotlin gaps: CWE-942, CWE-611, CWE-94
SBCORS = "https://docs.spring.io/spring-framework/reference/web/webmvc-cors.html"
sec("KT-CORS-ANY-ORIGIN", "CORS allows any origin", SBCORS, "By default, @CrossOrigin allows: All origins.",
    r"""((call_expression [(identifier) @m (navigation_expression (_) (identifier) @m .)] (value_arguments (value_argument (string_literal) @s))) @match (#match? @m "^(allowedOrigins|allowedOriginPatterns|addAllowedOrigin|addAllowedOriginPattern|allowOrigin|anyHost)$") (#eq? @s "\"*\""))""",
    'fun cors(registry: CorsRegistry) {\n    registry.addMapping("/api/**").allowedOrigins("*")\n}\n',
    'fun cors(registry: CorsRegistry) {\n    registry.addMapping("/api/**").allowedOrigins("https://app.example.com")\n}\n',
    "Every website may call this API from a browser and read the responses. Use an explicit allow-list of origins.",
    sev="minor", lang="kotlin", applies=KA, files=["**/*.kt"], mode="ai-confirm",
    ai="Does this API serve user-specific or non-public data to browsers?", cwe=["CWE-942"], asvs=["V3.4.2"], docv="Spring Framework reference")
JSCG = "https://www.oracle.com/java/technologies/javase/seccodeguide.html"
sec("KT-XXE", "XML parser factory without XXE hardening", JSCG,
    "XML External Entity (XXE) attacks insert local files into XML data which may then be accessible to the client.",
    r"""((call_expression (navigation_expression (identifier) @c (identifier) @m)) @match (#match? @c "^(DocumentBuilderFactory|SAXParserFactory|XMLInputFactory|TransformerFactory|SchemaFactory)$") (#match? @m "^(newInstance|newDefaultInstance|newFactory|newDefaultFactory)$"))""",
    "fun parse(input: InputStream) = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(input)\n",
    'fun parse(input: InputStream): Document {\n    val f = DocumentBuilderFactory.newInstance()\n    f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)\n    return f.newDocumentBuilder().parse(input)\n}\n',
    "This factory keeps DTDs and external entities enabled, so XML from an untrusted source can read local files or reach internal hosts (XXE). Disable doctype declarations, or set ACCESS_EXTERNAL_DTD/SCHEMA to empty.",
    sev="major", lang="kotlin", applies=KA, files=["**/*.kt"], mode="ai-confirm",
    ai="Is the XML parsed from an untrusted source, and are DTDs/external entities left enabled for this factory?",
    cwe=["CWE-611"], asvs=["V1.5.1"], docv="Secure Coding Guidelines for Java SE (current)",
    filters=["file.lacks_re:disallow-doctype-decl|SUPPORT_DTD|ACCESS_EXTERNAL_DTD|IS_SUPPORTING_EXTERNAL_ENTITIES"])
sec("KT-SCRIPT-EVAL", "ScriptEngine.eval with a non-constant script", JSCG,
    "Scripts run through the javax.script scripting API or similar",
    r"""((call_expression (navigation_expression (_) (identifier) @m .) (value_arguments . (value_argument [(identifier) (string_literal (interpolation)) (binary_expression)]))) @match (#eq? @m "eval"))""",
    'fun calc(expr: String): Any? {\n    val engine = ScriptEngineManager().getEngineByName("js")\n    return engine.eval(expr)\n}\n',
    'fun calc(a: Int, b: Int): Int = a + b\n',
    "A script built from data is executed with the app's permissions; if any part comes from a user this is code injection. Use a restricted expression parser or a fixed script with bound parameters.",
    sev="major", lang="kotlin", applies=KA, files=["**/*.kt"], mode="ai-confirm", ai="Can any part of the evaluated script come from user input or another untrusted source?",
    cwe=["CWE-94"], asvs=["V1.3.2"], docv="Secure Coding Guidelines for Java SE (current)", filters=["file.has_re:ScriptEngine"])
# ================================================================== batch 2 (ASVS 5.0 gaps)
SSTI = CS + "Server_Side_Template_Injection_Prevention_Cheat_Sheet.html"
SSTI_Q = "Keep templates with the application source, review changes to them like code, and never build them from untrusted data."
sec("PY-TEMPLATE-FROM-STRING", "Template compiled from a non-constant string (SSTI)", SSTI, SSTI_Q,
    r"""((call function: [(identifier) @f (attribute attribute: (identifier) @f)] arguments: (argument_list . [(identifier) (string (interpolation)) (binary_operator) (call) (attribute) (subscript)])) @match (#match? @f "^(render_template_string|from_string|Template)$"))""",
    "@app.route('/hello')\ndef hello():\n    name = request.args.get('name', '')\n    return render_template_string('<h1>Hello ' + name + '</h1>')\n",
    "@app.route('/hello')\ndef hello():\n    name = request.args.get('name', '')\n    return render_template_string('<h1>Hello {{ name }}</h1>', name=name)\n",
    "The template source is built from data. If any part comes from a user, template syntax in it runs on the server (SSTI, often remote code execution in Jinja2/Mako). Render a fixed template and pass values as variables.",
    sev="critical", lang="python", applies=PYA, files=["**/*.py"], mode="ai-confirm", ai="Can any part of the template source come from request data or other untrusted input?",
    filters=["file.has_re:jinja2|flask|mako|render_template_string|django\\.template", "file.lacks_re:from string import .*Template|string\\.Template"],
    cwe=["CWE-1336"], asvs=["V1.3.7"], docv="OWASP SSTI Prevention Cheat Sheet")
SPEL = "https://docs.spring.io/spring-framework/reference/core/expressions/evaluation.html"
sec("JAVA-SPEL-DYNAMIC", "SpEL expression parsed from a non-constant string", SPEL,
    "SimpleEvaluationContext is designed to support only a subset of the SpEL language syntax.",
    r"""((method_invocation name: (identifier) @m arguments: (argument_list . [(identifier) (binary_expression) (method_invocation)])) @match (#match? @m "^(parseExpression|parseRaw)$"))""",
    "class C {\n  Object eval(ExpressionParser parser, String expr) {\n    return parser.parseExpression(expr).getValue();\n  }\n}\n",
    "class C {\n  Object eval(ExpressionParser parser, Order o) {\n    return parser.parseExpression(\"total * 1.2\").getValue(SimpleEvaluationContext.forReadOnlyDataBinding().build(), o);\n  }\n}\n",
    "An expression string that is not a constant is evaluated with SpEL. With the default (standard) context, user-controlled text can call constructors and static methods (T(java.lang.Runtime)), which is remote code execution. Evaluate fixed expressions, or use SimpleEvaluationContext.",
    sev="critical", lang="java", applies=JA, files=["**/*.java"], mode="ai-confirm", ai="Can the expression text come from request data or other untrusted input, and is it evaluated with a StandardEvaluationContext (or none)?",
    filters=["file.has_re:org\\.springframework\\.expression|ExpressionParser|SpelExpressionParser"], cwe=["CWE-917"], asvs=["V1.3.5"], docv="Spring Framework reference")
GWS = "https://pkg.go.dev/github.com/gorilla/websocket"
sec("GO-WS-ANY-ORIGIN", "WebSocket upgrader accepts any Origin", GWS,
    "If // CheckOrigin is nil, then a safe default is used: return false if the // Origin request header is present and the origin host is not equal to // request Host header.",
    r"""[((keyed_element key: (literal_element (identifier) @k) value: (literal_element (func_literal body: (block (statement_list . (return_statement (expression_list (true))) .))))) @match (#eq? @k "CheckOrigin"))
         ((assignment_statement left: (expression_list (selector_expression field: (field_identifier) @k)) right: (expression_list (func_literal body: (block (statement_list . (return_statement (expression_list (true))) .))))) @match (#eq? @k "CheckOrigin"))]""",
    'package p\n\nimport (\n\t"net/http"\n\n\t"github.com/gorilla/websocket"\n)\n\nvar up = websocket.Upgrader{\n\tCheckOrigin: func(r *http.Request) bool { return true },\n}\n',
    'package p\n\nimport "github.com/gorilla/websocket"\n\nvar up = websocket.Upgrader{}\n',
    "Returning true from CheckOrigin lets any website open a WebSocket to this server with the visitor's cookies (cross-site WebSocket hijacking). Leave CheckOrigin nil for the same-origin default, or compare the Origin against an allow-list.",
    lang="go", applies=GOA, files=["**/*.go"], cwe=["CWE-1385"], asvs=["V4.4.2"], docv="gorilla/websocket docs",
    fp=['package p\n\nfunc init() {\n\tup.CheckOrigin = func(r *http.Request) bool {\n\t\treturn allowed[r.Header.Get("Origin")]\n\t}\n}\n'])
PYJWT = "https://pyjwt.readthedocs.io/en/stable/usage.html"
sec("PY-JWT-CLAIM-CHECK-OFF", "JWT claim validation turned off (aud/exp/iss/nbf)", PYJWT,
    "If the principal processing the claim does not identify itself with a value in the “aud” claim when this claim is present, then the JWT MUST be rejected.",
    r"""((pair key: (string (string_content) @k) value: (false)) @match (#match? @k "^verify_(aud|exp|iss|nbf|iat)$"))""",
    "import jwt\nclaims = jwt.decode(token, key, algorithms=['RS256'], options={'verify_aud': False})\n",
    "import jwt\nclaims = jwt.decode(token, key, algorithms=['RS256'], audience='api://orders')\n",
    "Turning off this claim check accepts tokens issued for other services (aud), expired tokens (exp) or tokens from other issuers. Pass audience=/issuer= and keep the checks on.",
    lang="python", applies=PYA, files=["**/*.py"], filters=["file.has_re:\\bjwt\\b"], cwe=["CWE-287"], asvs=["V9.2.3"], docv="PyJWT 2.x")
MFORM = "https://docs.djangoproject.com/en/5.2/topics/forms/modelforms/"
sec("PY-DJANGO-FIELDS-ALL", "ModelForm/serializer exposes all model fields", MFORM,
    "Failure to do so can easily lead to security problems when a form unexpectedly allows a user to set certain fields",
    r"""((assignment left: (identifier) @f right: (string (string_content) @v)) @match (#eq? @f "fields") (#eq? @v "__all__"))""",
    "class ProfileForm(forms.ModelForm):\n    class Meta:\n        model = Profile\n        fields = '__all__'\n",
    "class ProfileForm(forms.ModelForm):\n    class Meta:\n        model = Profile\n        fields = ['display_name', 'bio']\n",
    "Every model field, including ones added later such as is_staff or balance, becomes writable (or readable for serializers). List the allowed fields explicitly.",
    sev="minor", lang="python", applies=PYA, files=["**/*.py"], mode="ai-confirm",
    ai="Does the model have (or could it gain) fields the user must not set or see, such as ownership, role or price fields?",
    filters=["file.has_re:ModelForm|ModelSerializer|HyperlinkedModelSerializer"], cwe=["CWE-915"], asvs=["V15.3.3", "V8.2.3"], docv="Django 5.2 docs")
MASS = CS + "Mass_Assignment_Cheat_Sheet.html"
sec("JS-MASS-ASSIGN-BODY", "Request body passed whole to a model write", MASS,
    "Software frameworks sometimes allow developers to automatically bind HTTP request parameters into program code variables or objects",
    r"""((call_expression function: (member_expression property: (property_identifier) @m) arguments: (arguments (member_expression object: (identifier) @r property: (property_identifier) @b))) @match (#match? @m "^(create|insertMany|insertOne|findByIdAndUpdate|findOneAndUpdate|updateOne|updateMany|update|upsert|build|assign|save|merge)$") (#match? @r "^(req|request|ctx)$") (#eq? @b "body"))""",
    "app.post('/users', async (req, res) => {\n  res.json(await User.create(req.body))\n})\n",
    "app.post('/users', async (req, res) => {\n  const { name, email } = req.body\n  res.json(await User.create({ name, email }))\n})\n",
    "The whole request body is written to the model, so a client can set fields it should not (role, isAdmin, ownerId, price). Pick the allowed fields explicitly or validate against a schema that strips unknown keys.",
    mode="ai-confirm", ai="Does the model have fields the client must not set (role, admin flags, ownership, prices), with no schema validation stripping unknown keys before this call?",
    cwe=["CWE-915"], asvs=["V15.3.3", "V8.2.3"], docv="OWASP Mass Assignment Cheat Sheet")
GTLS = "https://pkg.go.dev/crypto/tls"
sec("GO-TLS-INSECURE-CIPHER", "Insecure TLS cipher suite configured", GTLS,
    "InsecureCipherSuites returns a list of cipher suites currently implemented by this package and which have security issues.",
    r"""((selector_expression operand: (identifier) @p field: (field_identifier) @match) (#eq? @p "tls") (#match? @match "^TLS_.*(_RC4_|_3DES_|_CBC_SHA256$)"))""",
    'package p\n\nimport "crypto/tls"\n\nvar cfg = &tls.Config{CipherSuites: []uint16{tls.TLS_ECDHE_RSA_WITH_RC4_128_SHA}}\n',
    'package p\n\nimport "crypto/tls"\n\nvar cfg = &tls.Config{MinVersion: tls.VersionTLS12}\n',
    "This cipher suite is on Go's insecure list (RC4, 3DES or CBC-SHA256), open to known practical attacks. Remove CipherSuites to use Go's secure defaults.",
    lang="go", applies=GOA, files=["**/*.go"], cwe=["CWE-327"], asvs=["V12.1.2"], docv="Go crypto/tls docs")
HDR = CS + "HTTP_Headers_Cheat_Sheet.html"
sec("JS-HELMET-HEADER-OFF", "helmet() with a protective header switched off", HDR, "Ensure X-Content-Type-Options: nosniff is set to prevent MIME type sniffing.",
    r"""((call_expression function: (identifier) @h arguments: (arguments (object (pair key: (property_identifier) @k value: (false)) @match))) (#eq? @h "helmet") (#match? @k "^(contentSecurityPolicy|strictTransportSecurity|hsts|xContentTypeOptions|noSniff|referrerPolicy|crossOriginOpenerPolicy|frameguard|xFrameOptions)$"))""",
    "app.use(helmet({ contentSecurityPolicy: false }))\n", "app.use(helmet({ contentSecurityPolicy: { directives: { scriptSrc: [\"'self'\"] } } }))\n",
    "A browser protection header (CSP, HSTS, nosniff, Referrer-Policy, COOP or frame options) is disabled for every response. Configure it instead of turning it off.",
    sev="minor", mode="ai-confirm", ai="Is the header disabled without an equivalent set elsewhere (proxy, CDN, meta tag)?",
    cwe=["CWE-693"], asvs=["V3.4.1", "V3.4.3", "V3.4.4", "V3.4.5", "V3.4.8"], docv="OWASP HTTP Headers Cheat Sheet")
sec("JAVA-SPRING-HEADERS-OFF", "Spring Security response headers disabled", HDR, "Ensure X-Content-Type-Options: nosniff is set to prevent MIME type sniffing.",
    r"""((method_invocation object: (method_invocation name: (identifier) @h) name: (identifier) @d) @match (#match? @h "^(headers|httpStrictTransportSecurity|contentTypeOptions|contentSecurityPolicy|referrerPolicy|crossOriginOpenerPolicy)$") (#eq? @d "disable"))""",
    "class Sec {\n  SecurityFilterChain chain(HttpSecurity http) throws Exception {\n    http.headers().disable();\n    return http.build();\n  }\n}\n",
    "class Sec {\n  SecurityFilterChain chain(HttpSecurity http) throws Exception {\n    http.headers(h -> h.contentSecurityPolicy(c -> c.policyDirectives(\"script-src 'self'\")));\n    return http.build();\n  }\n}\n",
    "Spring Security's default security headers (HSTS, nosniff, frame options, cache control) are removed. Keep the defaults and customise single headers instead.",
    sev="minor", lang="java", applies=JA, files=["**/*.java"], mode="ai-confirm", ai="Are these headers not set by another layer (proxy, CDN, gateway) for this application?",
    cwe=["CWE-693"], asvs=["V3.4.1", "V3.4.4"], docv="OWASP HTTP Headers Cheat Sheet")
PYOS = "https://docs.python.org/3/library/os.html"
sec("PY-ACCESS-THEN-OPEN", "os.access() check before using the file (TOCTOU)", PYOS,
    "Using access() to check if a user is authorized to e.g. open a file before actually doing so using open() creates a security hole",
    r"""((if_statement condition: (call function: (attribute object: (identifier) @o attribute: (identifier) @a)) consequence: (block) @b) @match (#eq? @o "os") (#eq? @a "access"))""",
    "if os.access(path, os.W_OK):\n    with open(path, 'w') as f:\n        f.write(data)\n",
    "try:\n    with open(path, 'w') as f:\n        f.write(data)\nexcept PermissionError:\n    log.warning('no write access to %s', path)\n",
    "The file can be swapped (e.g. for a symlink) between the access() check and the open, so the check protects nothing. Open the file directly and handle the error.",
    sev="minor", lang="python", applies=PYA, files=["**/*.py"], filters=["node.has_re:\\bopen\\(|os\\.(remove|unlink|rename|chmod|chown)\\("],
    cwe=["CWE-367"], asvs=["V15.4.2"], docv="Python 3 docs")
PWV = "https://docs.djangoproject.com/en/5.2/topics/auth/passwords/"
sec("PY-DJANGO-NO-PASSWORD-VALIDATORS", "Django password validation disabled", PWV,
    "The default for the setting is an empty list, which means no validators are applied.",
    r"""((assignment left: (identifier) @n right: (list) @match) (#eq? @n "AUTH_PASSWORD_VALIDATORS") (#match? @match "^\\[\\s*\\]$"))""",
    "AUTH_PASSWORD_VALIDATORS = []\n",
    "AUTH_PASSWORD_VALIDATORS = [\n    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},\n]\n",
    "No password rules are enforced, so one-character and common passwords are accepted. Enable at least MinimumLengthValidator and CommonPasswordValidator.",
    lang="python", applies=PYA, files=["**/*.py"], cwe=["CWE-521"], asvs=["V6.2.1"], docv="Django 5.2 docs")
COOK = "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie"
sec("JS-COOKIE-SAMESITE-NONE", "Cookie sent cross-site (sameSite none/false)", COOK, "SameSite=None; Secure",
    r"""((pair key: (property_identifier) @k value: [(string (string_fragment) @v) (false) @v]) @match (#eq? @k "sameSite") (#match? @v "^(?i)(none|false)$"))""",
    "app.use(session({ secret: process.env.SESSION_SECRET, cookie: { secure: true, sameSite: 'none' } }))\n",
    "app.use(session({ secret: process.env.SESSION_SECRET, cookie: { secure: true, sameSite: 'lax' } }))\n",
    "The cookie is attached to requests from any other site, so the browser's built-in CSRF protection is gone. Use 'lax' or 'strict' unless the cookie must work in third-party embeds, and then add CSRF tokens.",
    sev="minor", mode="ai-confirm", ai="Is this an authentication/session cookie without other CSRF protection (tokens, origin checks)?",
    filters=["ancestor.has_re:call_expression:(?i)(cookie|session)"], cwe=["CWE-1275", "CWE-352"], asvs=["V3.3.2"], docv="MDN Web Docs")
GOINT = "https://pkg.go.dev/strconv"
sec("GO-ATOI-NARROWING", "strconv result narrowed to a smaller integer type", GOINT,
    "Atoi is equivalent to ParseInt(s, 10, 0), converted to type int.",
    r"""((call_expression function: (identifier) @t arguments: (argument_list . (identifier) .)) @match (#match? @t "^(int8|int16|int32|uint8|uint16|uint32)$"))""",
    'package p\n\nimport "strconv"\n\nfunc port(s string) int16 {\n\tn, _ := strconv.Atoi(s)\n\treturn int16(n)\n}\n',
    'package p\n\nimport "strconv"\n\nfunc port(s string) int16 {\n\tn, _ := strconv.ParseInt(s, 10, 16)\n\treturn int16(n)\n}\n',
    "A value parsed as a full-size int is converted to a smaller type, so large inputs wrap around silently (a port, size or index becomes negative or small). Parse with the target bitSize (ParseInt(s, 10, 16)) or range-check before converting.",
    sev="minor", lang="go", applies=GOA, files=["**/*.go"], mode="ai-confirm", ai="Is the converted value derived from strconv.Atoi/ParseInt(...,64) on external input without a range check?",
    filters=["func.has_re:strconv\\.(Atoi|ParseInt\\([^)]*,\\s*(0|64)\\)|ParseUint\\([^)]*,\\s*(0|64)\\))", "func.lacks_re:math\\.(Max|Min)(Int|Uint)(8|16|32)"],
    cwe=["CWE-190", "CWE-681"], asvs=["V1.4.2"], docv="Go strconv docs")


# ------------------------------------------------------------------ batch 3: Snyk/ASVS gaps
SECRETNAME = r"(?i)(signature|sig|hmac|mac|digest|token|secret|api_?key|apikey|password|passwd)$"
TSE = "https://nodejs.org/api/crypto.html"
TIMING_MSG = "A secret (token, signature, HMAC) is compared with an ordinary equality operator, which returns as soon as a byte differs; the response time leaks how much of a guess was right. Use a constant-time comparison."
TIMING_AI = "Is one side a secret (HMAC, signature, API token, password hash) and the other an attacker-supplied value, e.g. from a request?"
sec("JS-TIMING-COMPARE", "Secret compared with === instead of a constant-time check", TSE, "using a constant-time algorithm",
    r"""[((binary_expression left: [(identifier) (member_expression) (subscript_expression)] @l right: [(identifier) (member_expression) (subscript_expression)] @r) @match (#match? @l "(?i)(signature|hmac|digest|secret|api_?key|(api|access|auth|csrf|xsrf|reset|session|bearer|refresh|expected|stored|provided|given|user|verify|verification|webhook)_?token)$") (#not-match? @r "^(null|nil|None|undefined|NaN|true|false)$") (#match? @match "^\\S+\\s*[!=]==?\\s*\\S+$"))
         ((binary_expression left: [(identifier) (member_expression) (subscript_expression)] @l2 right: [(identifier) (member_expression) (subscript_expression)] @r2) @match (#match? @r2 "(?i)(signature|hmac|digest|secret|api_?key|(api|access|auth|csrf|xsrf|reset|session|bearer|refresh|expected|stored|provided|given|user|verify|verification|webhook)_?token)$") (#not-match? @l2 "^(null|nil|None|undefined|NaN|true|false)$") (#match? @match "^\\S+\\s*[!=]==?\\s*\\S+$"))]""",
    "function check(req) {\n  const expected = sign(req.body)\n  return req.headers['x-sig'] === expectedSignature\n}\n",
    "function check(req) {\n  const a = Buffer.from(req.headers['x-sig'])\n  const b = Buffer.from(expectedSignature)\n  return a.length === b.length && crypto.timingSafeEqual(a, b)\n}\n",
    TIMING_MSG, sev="minor", mode="ai-confirm", ai=TIMING_AI, filters=["file.lacks_re:timingSafeEqual"],
    fp=["if (token === undefined) return\n", "if (typeof token === 'string') x()\n", "if (data === token) return\n"], cwe=["CWE-208"], asvs=["V11.2.4"], docv="Node.js crypto docs")
sec("PY-TIMING-COMPARE", "Secret compared with == instead of hmac.compare_digest", "https://docs.python.org/3/library/hmac.html",
    "designed to prevent timing analysis",
    r"""[((comparison_operator . [(identifier) (attribute)] @l . [(identifier) (attribute)] @r .) @match (#match? @match "^\\S+\\s*[!=]=\\s*\\S+$") (#match? @l "(?i)(signature|hmac|digest|secret|api_?key|(api|access|auth|csrf|xsrf|reset|session|bearer|refresh|expected|stored|provided|given|user|verify|verification|webhook)_?token)$") (#not-match? @r "^(null|nil|None|undefined|NaN|true|false)$"))
         ((comparison_operator . [(identifier) (attribute)] @l2 . [(identifier) (attribute)] @r2 .) @match (#match? @match "^\\S+\\s*[!=]=\\s*\\S+$") (#match? @r2 "(?i)(signature|hmac|digest|secret|api_?key|(api|access|auth|csrf|xsrf|reset|session|bearer|refresh|expected|stored|provided|given|user|verify|verification|webhook)_?token)$") (#not-match? @l2 "^(null|nil|None|undefined|NaN|true|false)$"))]""",
    "def check(sig, body):\n    expected_signature = sign(body)\n    return sig == expected_signature\n",
    "import hmac\n\ndef check(sig, body):\n    expected_signature = sign(body)\n    return hmac.compare_digest(sig, expected_signature)\n",
    TIMING_MSG, sev="minor", lang="python", applies=PYA, files=["**/*.py"], mode="ai-confirm", ai=TIMING_AI,
    filters=["file.lacks_re:compare_digest|secrets\\.compare"], fp=["if token is None:\n    pass\n", "if token_type == 'bearer':\n    pass\n", "if token.type == tokenize.NAME:\n    pass\n"],
    cwe=["CWE-208"], asvs=["V11.2.4"], docv="Python 3 docs")
MDE = "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/security/MessageDigest.html"
sec("JAVA-TIMING-COMPARE", "Secret compared with equals() instead of MessageDigest.isEqual", MDE,
    "Compares two digests for equality.",
    r"""[((method_invocation object: (identifier) @o name: (identifier) @m arguments: (argument_list . (_) .)) @match (#eq? @m "equals") (#match? @o "(?i)(signature|hmac|digest|secret|api_?key|(api|access|auth|csrf|xsrf|reset|session|bearer|refresh|expected|stored|provided|given|user|verify|verification|webhook)_?token)$"))
         ((method_invocation object: (identifier) @o2 name: (identifier) @m2 arguments: (argument_list . (_) . (_) .)) @match (#eq? @o2 "Arrays") (#eq? @m2 "equals") (#match? @match "(?i)(signature|hmac|digest|secret)"))]""",
    "class V {\n  boolean ok(String given, String expectedSignature) {\n    return expectedSignature.equals(given);\n  }\n}\n",
    "class V {\n  boolean ok(byte[] given, byte[] expectedSignature) {\n    return java.security.MessageDigest.isEqual(expectedSignature, given);\n  }\n}\n",
    TIMING_MSG, sev="minor", lang="java", applies=JA, files=["**/*.java"], mode="ai-confirm", ai=TIMING_AI,
    filters=["file.lacks_re:MessageDigest\\.isEqual"], cwe=["CWE-208"], asvs=["V11.2.4"], docv="Java SE 21 API")
sec("KT-TIMING-COMPARE", "Secret compared with == instead of MessageDigest.isEqual", MDE,
    "Compares two digests for equality.",
    r"""[((binary_expression left: [(identifier) (navigation_expression)] @l right: [(identifier) (navigation_expression)] @r) @match (#match? @match "^\\S+\\s*[!=]=\\s*\\S+$") (#match? @l "(?i)(signature|hmac|digest|secret|api_?key|(api|access|auth|csrf|xsrf|reset|session|bearer|refresh|expected|stored|provided|given|user|verify|verification|webhook)_?token)$") (#not-match? @r "^(null|nil|None|undefined|NaN|true|false)$"))
         ((binary_expression left: [(identifier) (navigation_expression)] @l2 right: [(identifier) (navigation_expression)] @r2) @match (#match? @match "^\\S+\\s*[!=]=\\s*\\S+$") (#match? @r2 "(?i)(signature|hmac|digest|secret|api_?key|(api|access|auth|csrf|xsrf|reset|session|bearer|refresh|expected|stored|provided|given|user|verify|verification|webhook)_?token)$") (#not-match? @l2 "^(null|nil|None|undefined|NaN|true|false)$"))]""",
    "fun ok(given: String, expectedSignature: String): Boolean {\n    return given == expectedSignature\n}\n",
    "fun ok(given: ByteArray, expectedSignature: ByteArray): Boolean {\n    return java.security.MessageDigest.isEqual(given, expectedSignature)\n}\n",
    TIMING_MSG, sev="minor", lang="kotlin", applies=KA, files=["**/*.kt"], mode="ai-confirm", ai=TIMING_AI,
    filters=["file.lacks_re:MessageDigest\\.isEqual"], cwe=["CWE-208"], asvs=["V11.2.4"], docv="Java SE 21 API")

NJWT = "https://github.com/auth0/node-jsonwebtoken"
sec("JS-JWT-DECODE-NO-VERIFY", "jwt.decode() result used without jwt.verify()", NJWT,
    "Returns the decoded payload without verifying if the signature is valid.",
    r"""((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p)) @match (#match? @o "^(jwt|jsonwebtoken|JWT)$") (#eq? @p "decode"))""",
    "const jwt = require('jsonwebtoken')\nfunction user(req) {\n  return jwt.decode(req.headers.authorization.slice(7)).sub\n}\n",
    "const jwt = require('jsonwebtoken')\nfunction user(req) {\n  return jwt.verify(req.headers.authorization.slice(7), process.env.JWT_KEY, { algorithms: ['HS256'] }).sub\n}\n",
    "jwt.decode() does not check the signature, so anyone can forge the claims it returns. Use jwt.verify() with the key and an algorithms allow-list before trusting any claim.",
    mode="ai-confirm", ai="Are the decoded claims used for an authentication or authorisation decision without a jwt.verify() on the same token?",
    filters=["file.has_re:jsonwebtoken", "func.lacks_re:\\.verify\\("], cwe=["CWE-347"], asvs=["V9.1.1"], docv="jsonwebtoken README")
sec("JS-JWT-ALG-NONE", "JWT verification accepts the 'none' algorithm", NJWT,
    "List of strings with the names of the allowed algorithms.",
    r"""((pair key: (property_identifier) @k value: (array (string (string_fragment) @v))) @match (#eq? @k "algorithms") (#match? @v "^(?i)none$"))""",
    "jwt.verify(token, key, { algorithms: ['HS256', 'none'] })\n",
    "jwt.verify(token, key, { algorithms: ['HS256'] })\n",
    "Allowing 'none' lets a token without any signature pass verification, so every claim can be forged. List only the signing algorithms you actually use.",
    sev="critical", cwe=["CWE-347"], asvs=["V9.1.2"], docv="jsonwebtoken README")

MSF = "https://mongoosejs.com/docs/api/mongoose.html"
sec("JS-NOSQL-REQUEST-FILTER", "MongoDB query filter taken from the request body/query", MSF,
    "Sanitizes query filters against query selector injection attacks",
    r"""((call_expression function: (member_expression property: (property_identifier) @m) arguments: (arguments . (_) @a)) @match (#match? @m "^(find|findOne|findOneAndUpdate|findOneAndDelete|findOneAndReplace|updateOne|updateMany|deleteOne|deleteMany|countDocuments|exists)$") (#match? @a "^(req|request)\\.(body|query)(\\.\\w+)?$|:\\s*(req|request)\\.(body|query)\\.[\\w.]+\\s*[,}]"))""",
    "const mongoose = require('mongoose')\napp.post('/login', async (req, res) => {\n  const u = await User.findOne({ name: req.body.name, password: req.body.password })\n  res.json(!!u)\n})\n",
    "const mongoose = require('mongoose')\nmongoose.set('sanitizeFilter', true)\napp.post('/login', async (req, res) => {\n  const u = await User.findOne({ name: String(req.body.name) })\n  res.json(!!u)\n})\n",
    "A JSON body can carry objects such as {\"$ne\": null} instead of strings, turning an equality match into an operator query (login bypass, data dump). Cast fields to strings, validate the body schema, or enable sanitizeFilter.",
    mode="ai-confirm", ai="Can a request field here be an object (JSON body or qs-parsed query) that reaches the filter without casting, schema validation or sanitizeFilter?",
    filters=["file.has_re:mongoose|mongodb|monk", "file.lacks_re:sanitizeFilter|mongo-sanitize|mongoSanitize"], cwe=["CWE-943"], asvs=["V1.2.4"], docv="Mongoose API docs")
MWH = "https://www.mongodb.com/docs/manual/reference/operator/query/where/"
sec("JS-MONGO-WHERE-DYNAMIC", "MongoDB $where built from a variable", MWH,
    "Use the $where operator to pass either a string containing a JavaScript expression",
    r"""((pair key: [(string (string_fragment) @k) (property_identifier) @k] value: [(binary_expression) (template_string (template_substitution))] @match) (#eq? @k "$where"))""",
    "db.users.find({ $where: 'this.name == \"' + req.query.name + '\"' })\n",
    "db.users.find({ name: String(req.query.name) })\n",
    "$where runs JavaScript on the database server; concatenating input into it lets an attacker inject code into the query. Use ordinary query operators instead.",
    mode="ai-confirm", ai="Can a part of the concatenated $where expression come from request or other untrusted data?", cwe=["CWE-943"], asvs=["V1.2.4"], docv="MongoDB manual")

C113 = "https://cwe.mitre.org/data/definitions/113.html"
C113_Q = "before the data is included in outgoing HTTP headers"
HDR_MSG = "A request value goes straight into a response header. If the server stack does not reject CR/LF, the value can split the response or inject headers/cookies. Validate it against an allow-list or strip CR and LF."
HDR_AI = "Does the header value come from the request without CR/LF filtering, on a server stack that does not reject CR/LF in header values itself?"
sec("JAVA-HEADER-FROM-REQUEST", "Request value written into a response header", C113, C113_Q,
    r"""((method_invocation name: (identifier) @m arguments: (argument_list . (_) . (_) @v .)) @match (#match? @m "^(setHeader|addHeader)$") (#match? @v "\\.(getParameter|getHeader|getQueryString)\\("))""",
    "class H {\n  void h(HttpServletRequest request, HttpServletResponse response) {\n    response.setHeader(\"X-Trace\", request.getParameter(\"trace\"));\n  }\n}\n",
    "class H {\n  void h(HttpServletRequest request, HttpServletResponse response) {\n    response.setHeader(\"X-Trace\", request.getParameter(\"trace\").replaceAll(\"[\\\\r\\\\n]\", \"\"));\n  }\n}\n",
    HDR_MSG, sev="minor", lang="java", applies=JA, files=["**/*.java"], mode="ai-confirm", ai=HDR_AI,
    filters=["node.lacks_re:replace(All)?\\(|encode|sanitize|matches\\("], cwe=["CWE-113"], asvs=["V1.2.2"], docv="MITRE CWE")
sec("KT-HEADER-FROM-REQUEST", "Request value written into a response header", C113, C113_Q,
    r"""((call_expression (navigation_expression (_) (identifier) @m) (value_arguments . (value_argument) . (value_argument) @v .)) @match (#match? @m "^(setHeader|addHeader|header|append)$") (#match? @v "(getParameter|getHeader)\\(|\\.(parameters|queryParameters|headers)\\["))""",
    "fun h(request: HttpServletRequest, response: HttpServletResponse) {\n    response.setHeader(\"X-Trace\", request.getParameter(\"trace\"))\n}\n",
    "fun h(request: HttpServletRequest, response: HttpServletResponse) {\n    response.setHeader(\"X-Trace\", request.getParameter(\"trace\")?.filter { it != '\\r' && it != '\\n' })\n}\n",
    HDR_MSG, sev="minor", lang="kotlin", applies=KA, files=["**/*.kt"], mode="ai-confirm", ai=HDR_AI,
    filters=["node.lacks_re:replace\\(|filter|encode|sanitize"], cwe=["CWE-113"], asvs=["V1.2.2"], docv="MITRE CWE")
sec("PY-HEADER-FROM-REQUEST", "Request value written into a response header", C113, C113_Q,
    r"""((assignment left: (subscript value: (attribute attribute: (identifier) @h)) right: (_) @v) @match (#eq? @h "headers") (#match? @v "^request\\.(args|form|values|headers|cookies|GET|POST|META)\\b"))""",
    "from flask import request, make_response\n\ndef h():\n    resp = make_response('ok')\n    resp.headers['X-Trace'] = request.args['trace']\n    return resp\n",
    "from flask import request, make_response\n\ndef h():\n    resp = make_response('ok')\n    resp.headers['X-Trace'] = request.args['trace'].replace('\\r', '').replace('\\n', '')\n    return resp\n",
    HDR_MSG, sev="minor", lang="python", applies=PYA, files=["**/*.py"], mode="ai-confirm", ai=HDR_AI,
    filters=["node.lacks_re:replace\\(|quote|sanitize"], cwe=["CWE-113"], asvs=["V1.2.2"], docv="MITRE CWE")

C134 = "https://cwe.mitre.org/data/definitions/134.html"
C134_Q = "The programmer rarely intends for a format string to be externally-controlled at all."
FMT_MSG = "The format string itself is a variable. If it can come from a user, format specifiers in it can throw, read other arguments or produce unexpected output. Keep the format a constant and pass the data as arguments."
FMT_AI = "Can the format-string argument come from a request, file or other external input?"
sec("JAVA-FORMAT-STRING-VARIABLE", "String.format/printf with a non-constant format", C134, C134_Q,
    r"""((method_invocation object: (_) @o name: (identifier) @m arguments: (argument_list . (identifier) @f . (_))) @match (#match? @m "^(format|printf)$") (#match? @o "^(String|System\\.out|System\\.err|writer|out|\\w*[Ww]riter)$"))""",
    "class F {\n  void f(HttpServletRequest request, java.io.PrintWriter out, String name) {\n    String fmt = request.getParameter(\"fmt\");\n    out.printf(fmt, name);\n  }\n}\n",
    "class F {\n  void f(HttpServletRequest request, java.io.PrintWriter out, String name) {\n    out.printf(\"Hello %s\", name);\n  }\n}\n",
    FMT_MSG, sev="minor", lang="java", applies=JA, files=["**/*.java"], mode="ai-confirm", ai=FMT_AI,
    filters=["func.has_re:getParameter|getHeader|getQueryString|@RequestParam|@PathVariable|@RequestBody|readLine\\("], cwe=["CWE-134"], asvs=["V1.2.4"], docv="MITRE CWE")
sec("KT-FORMAT-STRING-VARIABLE", "String.format with a non-constant format", C134, C134_Q,
    r"""((call_expression (navigation_expression (identifier) @o (identifier) @m) (value_arguments . (value_argument (identifier)) . (value_argument))) @match (#eq? @o "String") (#eq? @m "format"))""",
    "fun f(request: HttpServletRequest, name: String): String {\n    val fmt = request.getParameter(\"fmt\")\n    return String.format(fmt, name)\n}\n",
    "fun f(request: HttpServletRequest, name: String): String {\n    return String.format(\"Hello %s\", name)\n}\n",
    FMT_MSG, sev="minor", lang="kotlin", applies=KA, files=["**/*.kt"], mode="ai-confirm", ai=FMT_AI,
    filters=["func.has_re:getParameter|getHeader|parameters\\[|queryParameters|receive|readLine\\("], cwe=["CWE-134"], asvs=["V1.2.4"], docv="MITRE CWE")

SM = CS + "Session_Management_Cheat_Sheet.html"
KCOOK_AI = "Is this cookie a session, authentication or otherwise sensitive cookie (not a harmless preference)?"
sec("KT-COOKIE-NO-SECURE", "Cookie created without the Secure flag", SM, "The Secure cookie attribute instructs",
    r"""((call_expression (identifier) @c (value_arguments . (value_argument) . (value_argument))) @match (#eq? @c "Cookie"))""",
    "fun login(response: HttpServletResponse, sid: String) {\n    val c = Cookie(\"SESSION\", sid)\n    c.isHttpOnly = true\n    response.addCookie(c)\n}\n",
    "fun login(response: HttpServletResponse, sid: String) {\n    val c = Cookie(\"SESSION\", sid)\n    c.isHttpOnly = true\n    c.secure = true\n    response.addCookie(c)\n}\n",
    "The cookie is sent over plain HTTP too, where it can be read on the network. Set the Secure flag (cookie.secure = true / secure = true).",
    sev="minor", lang="kotlin", applies=KA, files=["**/*.kt"], mode="ai-confirm", ai=KCOOK_AI,
    filters=["func.lacks_re:(isSecure|secure)\\s*=\\s*true|setSecure\\(true\\)"], cwe=["CWE-614"], asvs=["V3.3.1"], docv="OWASP Cheat Sheet Series (current)")
sec("KT-COOKIE-NO-HTTPONLY", "Cookie created without the HttpOnly flag", SM, "The HttpOnly cookie attribute instructs",
    r"""((call_expression (identifier) @c (value_arguments . (value_argument) . (value_argument))) @match (#eq? @c "Cookie"))""",
    "fun login(response: HttpServletResponse, sid: String) {\n    val c = Cookie(\"SESSION\", sid)\n    c.secure = true\n    response.addCookie(c)\n}\n",
    "fun login(response: HttpServletResponse, sid: String) {\n    val c = Cookie(\"SESSION\", sid)\n    c.secure = true\n    c.isHttpOnly = true\n    response.addCookie(c)\n}\n",
    "Scripts on the page can read the cookie, so any XSS steals it. Set HttpOnly (cookie.isHttpOnly = true / httpOnly = true) unless client code genuinely needs it.",
    sev="minor", lang="kotlin", applies=KA, files=["**/*.kt"], mode="ai-confirm", ai=KCOOK_AI,
    filters=["func.lacks_re:(isHttpOnly|httpOnly)\\s*=\\s*true|setHttpOnly\\(true\\)"], cwe=["CWE-1004"], asvs=["V3.3.4"], docv="OWASP Cheat Sheet Series (current)")
SCSRF = "https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html"
sec("KT-SPRING-CSRF-DISABLED", "Spring Security CSRF protection disabled (Kotlin)", SCSRF,
    "If you need to disable CSRF protection, you can do so using the following configuration",
    r"""[((call_expression (identifier) @c (annotated_lambda (lambda_literal (call_expression (identifier) @d)))) @match (#eq? @c "csrf") (#eq? @d "disable"))
         ((call_expression (navigation_expression (call_expression (navigation_expression (_) (identifier) @c)) (identifier) @d)) @match (#eq? @c "csrf") (#eq? @d "disable"))]""",
    "@Bean\nfun chain(http: HttpSecurity): SecurityFilterChain {\n    http {\n        csrf { disable() }\n        formLogin { }\n    }\n    return http.build()\n}\n",
    "@Bean\nfun chain(http: HttpSecurity): SecurityFilterChain {\n    http {\n        formLogin { }\n    }\n    return http.build()\n}\n",
    "CSRF protection is switched off. Keep it for any endpoint a browser calls with cookie or session authentication.",
    lang="kotlin", applies={"spring-security": ">=5.0"}, files=["**/*.kt"], mode="ai-confirm",
    ai="Is this filter chain reachable by browsers with cookie/session authentication? (Pure stateless token APIs may legitimately disable CSRF.)",
    cwe=["CWE-352"], asvs=["V3.5.1"], docv="Spring Security reference")

LOGCS = CS + "Logging_Cheat_Sheet.html"
LOG_MSG = "A password, token or key is written to the log, where it is kept, shipped and readable by far more people than the secret itself. Log an identifier or a masked value instead."
LOG_AI = "Is the logged value an actual secret (password, token, key) rather than e.g. a boolean, a length or a redacted form?"
SECRET_ARG = r"(?i)\b(password|passwd|pwd|secret|token|apikey|api_key|accesstoken|access_token|credentials?|privatekey|private_key)\b"
sec("JAVA-LOG-SECRET", "Secret written to a log", LOGCS, "Authentication passwords",
    r"""((method_invocation object: (identifier) @o name: (identifier) @m arguments: (argument_list (_) @a)) @match (#match? @o "^(log|logger|LOG|LOGGER|Log)$") (#match? @m "^(trace|debug|info|warn|error|fine|finer|finest|severe|warning)$") (#match? @a "(?i)^(\\w+\\.)*(password|passwd|pwd|secret|token|apikey|accesstoken|credentials?|privatekey)(\\(\\))?$|\\+\\s*(\\w+\\.)*(password|passwd|secret|token|apikey|accesstoken)\\b"))""",
    "class A {\n  void login(String user, String password) {\n    log.info(\"login \" + user + \" with \" + password);\n  }\n}\n",
    "class A {\n  void login(String user, String password) {\n    log.info(\"login {}\", user);\n  }\n}\n",
    LOG_MSG, sev="minor", lang="java", applies=JA, files=["**/*.java"], mode="ai-confirm", ai=LOG_AI,
    fp=["class A {\n  void f(String token) {\n    log.debug(\"token present: \" + (token != null));\n  }\n}\n"], cwe=["CWE-532"], asvs=["V16.2.5"], docv="OWASP Cheat Sheet Series (current)")
sec("KT-LOG-SECRET", "Secret written to a log", LOGCS, "Authentication passwords",
    r"""((call_expression (navigation_expression (identifier) @o (identifier) @m) (value_arguments (value_argument) @a)) @match (#match? @o "^(log|logger|LOG|LOGGER|Log)$") (#match? @m "^(trace|debug|info|warn|error|d|i|w|e|v)$") (#match? @a "(?i)^(\\w+\\.)*(password|passwd|pwd|secret|token|apikey|accesstoken|credentials?|privatekey)$|\\+\\s*(\\w+\\.)*(password|passwd|secret|token|apikey|accesstoken)\\b|\\$\\{?(password|passwd|secret|token|apiKey|accessToken)\\b"))""",
    "fun login(user: String, password: String) {\n    log.info(\"login $user with $password\")\n}\n",
    "fun login(user: String, password: String) {\n    log.info(\"login $user\")\n}\n",
    LOG_MSG, sev="minor", lang="kotlin", applies=KA, files=["**/*.kt"], mode="ai-confirm", ai=LOG_AI,
    cwe=["CWE-532"], asvs=["V16.2.5"], docv="OWASP Cheat Sheet Series (current)")
sec("GO-LOG-SECRET", "Secret written to a log", LOGCS, "Authentication passwords",
    r"""((call_expression function: (selector_expression operand: (identifier) @o field: (field_identifier) @m) arguments: (argument_list (identifier) @a)) @match (#match? @o "^(log|logger|slog|zap|logrus|klog)$") (#match? @m "^(Print|Printf|Println|Fatal|Fatalf|Debug|Debugf|Info|Infof|Warn|Warnf|Error|Errorf)$") (#match? @a "(?i)^(\\w+\\.)*(password|passwd|pwd|secret|token|apikey|apiKey|accesstoken|accessToken|privatekey)$"))""",
    'package p\n\nimport "log"\n\nfunc login(user, password string) {\n\tlog.Printf("login %s %s", user, password)\n}\n',
    'package p\n\nimport "log"\n\nfunc login(user, password string) {\n\tlog.Printf("login %s", user)\n}\n',
    LOG_MSG, sev="minor", lang="go", applies=GOA, files=["**/*.go"], mode="ai-confirm", ai=LOG_AI,
    cwe=["CWE-532", "CWE-312"], asvs=["V16.2.5"], docv="OWASP Cheat Sheet Series (current)")

TLSCS = CS + "Transport_Layer_Security_Cheat_Sheet.html"
TLS_Q = "TLS should be used for all pages, not just those that are considered sensitive"
HTTP_MSG = "The client connects over plain http://, so the request, response and any credentials travel unencrypted. Use https://."
HTTP_AI = "Does this URL carry real traffic (API calls, downloads, credentials) to a non-local host, rather than being an XML namespace, schema id or documentation link?"
sec("JAVA-HTTP-URL", "Connection to a cleartext http:// URL", TLSCS, TLS_Q,
    r"""[((object_creation_expression type: (type_identifier) @t arguments: (argument_list . (string_literal) @u)) @match (#match? @t "^(URL|HttpGet|HttpPost|HttpPut)$") (#match? @u "^\"http://") (#not-match? @u "^\"http://(localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0|\\[::1\\])"))
         ((method_invocation object: (identifier) @o name: (identifier) @m arguments: (argument_list . (string_literal) @u)) @match (#eq? @o "URI") (#eq? @m "create") (#match? @u "^\"http://") (#not-match? @u "^\"http://(localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0|\\[::1\\])"))]""",
    "class C {\n  java.io.InputStream get() throws Exception {\n    return new java.net.URL(\"http://api.example.com/data\").openStream();\n  }\n}\n".replace("java.net.URL", "URL"),
    "class C {\n  java.io.InputStream get() throws Exception {\n    return new URL(\"https://api.example.com/data\").openStream();\n  }\n}\n",
    HTTP_MSG, sev="minor", lang="java", applies=JA, files=["**/*.java"], mode="ai-confirm", ai=HTTP_AI,
    cwe=["CWE-319"], asvs=["V12.2.1"], docv="OWASP Cheat Sheet Series (current)")
sec("KT-HTTP-URL", "Connection to a cleartext http:// URL", TLSCS, TLS_Q,
    r"""((call_expression [(identifier) (navigation_expression (_) (identifier))] @c (value_arguments . (value_argument (string_literal) @u))) @match (#match? @c "(^|\\.)(URL|URI|create|get|post|put|url)$") (#match? @u "^\"http://") (#not-match? @u "^\"http://(localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0|10\\.0\\.2\\.2|\\[::1\\])"))""",
    "fun get(): String = URL(\"http://api.example.com/data\").readText()\n",
    "fun get(): String = URL(\"https://api.example.com/data\").readText()\n",
    HTTP_MSG, sev="minor", lang="kotlin", applies=KA, files=["**/*.kt"], mode="ai-confirm", ai=HTTP_AI,
    cwe=["CWE-319"], asvs=["V12.2.1"], docv="OWASP Cheat Sheet Series (current)")

sec("PHP-PHPINFO", "phpinfo() exposes the server configuration", "https://www.php.net/manual/en/function.phpinfo.php",
    "Outputs information about PHP's configuration",
    r"""((function_call_expression function: (name) @f) @match (#eq? @f "phpinfo"))""",
    "<?php\nphpinfo();\n", "<?php\necho 'ok';\n",
    "phpinfo() prints PHP and server versions, loaded modules, paths and environment variables (often including secrets) to whoever requests the page. Remove it from deployed code.",
    lang="php", applies={"php": ">=7.0"}, files=["**/*.php"], cwe=["CWE-200"], asvs=["V13.4.2"], docv="PHP manual")
sec("PHP-LIBXML-NOENT", "XML parsed with LIBXML_NOENT (entity substitution)", "https://www.php.net/manual/en/libxml.constants.php",
    "Enabling entity substitution may facilitate XML External Entity (XXE) attacks.",
    r"""((name) @match (#eq? @match "LIBXML_NOENT"))""",
    "<?php\n$doc = new DOMDocument();\n$doc->loadXML($xml, LIBXML_NOENT | LIBXML_DTDLOAD);\n",
    "<?php\n$doc = new DOMDocument();\n$doc->loadXML($xml, LIBXML_NONET);\n",
    "LIBXML_NOENT substitutes entities, including external ones, so a DOCTYPE in the input can read local files or reach internal URLs. Drop the flag.",
    lang="php", applies={"php": ">=7.0"}, files=["**/*.php"], cwe=["CWE-611"], asvs=["V1.5.1"], docv="PHP manual")
LX2 = "https://gnome.pages.gitlab.gnome.org/libxml2/html/parser_8h.html"
sec("JS-LIBXML-NOENT", "libxmljs parse with noent: true (entity substitution)", LX2,
    "Despite the confusing name, this option enables substitution of entities.",
    r"""((call_expression function: (member_expression property: (property_identifier) @m) arguments: (arguments (object (pair key: (property_identifier) @k value: (true))))) @match (#match? @m "^(parseXml|parseXmlString|parseXmlAsync|parseHtml)$") (#eq? @k "noent"))""",
    "const libxmljs = require('libxmljs')\nconst doc = libxmljs.parseXml(req.body, { noent: true })\n",
    "const libxmljs = require('libxmljs')\nconst doc = libxmljs.parseXml(req.body, { noent: false, nonet: true })\n",
    "noent: true makes libxml2 substitute entities, including external ones, so a DOCTYPE in the input can read local files or reach internal URLs (XXE). Leave it off.",
    cwe=["CWE-611"], asvs=["V1.5.1"], docv="libxml2 API docs")

SMCS = CS + "Secrets_Management_Cheat_Sheet.html"
SM_Q = "hardcoded within the source code in plaintext"
KEY_MSG = "The key is a literal in the source, so everyone with the code (or the binary) has it, and it cannot be rotated without a release. Load it from a secret store or the environment."
PLACEHOLDER = r"^(changeme|secret|xxx+|test.*|dummy.*|example.*|your[-_].*|<.*>|\$\{.*\})$"
sec("PY-HARDCODED-CRYPTO-KEY", "Encryption/HMAC key is a string literal", SMCS, SM_Q,
    r"""[((call function: (attribute object: (identifier) @o attribute: (identifier) @n) arguments: (argument_list . (string (string_content) @k))) @match (#match? @o "^(AES|DES3|ChaCha20|ChaCha20_Poly1305|Blowfish|Salsa20|hmac|algorithms)$") (#match? @n "^(new|AES|ChaCha20|TripleDES|Camellia)$") (#not-match? @k "(?i)^(changeme|xxx+|<.*>)$"))
         ((call function: (identifier) @f arguments: (argument_list . (string (string_content) @k))) @match (#match? @f "^(Fernet|AESGCM|ChaCha20Poly1305|AESCCM)$"))]""",
    "from Crypto.Cipher import AES\n\ndef enc(data):\n    return AES.new(b'0123456789abcdef', AES.MODE_GCM).encrypt(data)\n",
    "import os\nfrom Crypto.Cipher import AES\n\ndef enc(data):\n    return AES.new(bytes.fromhex(os.environ['DATA_KEY']), AES.MODE_GCM).encrypt(data)\n",
    KEY_MSG, lang="python", applies=PYA, files=["**/*.py"], cwe=["CWE-321", "CWE-798"], asvs=["V13.3.1"], docv="OWASP Cheat Sheet Series (current)")
sec("JS-HARDCODED-CRYPTO-KEY", "Encryption/HMAC/JWT key is a string literal", SMCS, SM_Q,
    r"""[((call_expression function: (member_expression property: (property_identifier) @m) arguments: (arguments . (_) . [(string (string_fragment)) (call_expression function: (member_expression object: (identifier) @b) arguments: (arguments . (string)))] @k)) @match (#match? @m "^(createCipheriv|createDecipheriv|createHmac)$"))
         ((call_expression function: (member_expression object: (identifier) @o2 property: (property_identifier) @m2) arguments: (arguments . (_) . (string (string_fragment) @k2))) @match (#match? @o2 "^(jwt|jsonwebtoken)$") (#match? @m2 "^(sign|verify)$") (#not-match? @k2 "^-----BEGIN (PUBLIC KEY|CERTIFICATE)"))]""",
    "const jwt = require('jsonwebtoken')\nconst token = jwt.sign({ sub: user.id }, 'my-super-secret-key')\n",
    "const jwt = require('jsonwebtoken')\nconst token = jwt.sign({ sub: user.id }, process.env.JWT_KEY)\n",
    KEY_MSG, fp=["const c = crypto.createCipheriv('aes-256-gcm', key, iv)\n"], cwe=["CWE-321", "CWE-798"], asvs=["V13.3.1"], docv="OWASP Cheat Sheet Series (current)")
sec("GO-HARDCODED-CRYPTO-KEY", "Encryption/HMAC key is a string literal", SMCS, SM_Q,
    r"""[((call_expression function: (selector_expression operand: (identifier) @p field: (field_identifier) @f) arguments: (argument_list . (type_conversion_expression operand: (interpreted_string_literal)))) @match (#match? @p "^(aes|des|chacha20poly1305|blowfish)$") (#match? @f "^(NewCipher|NewTripleDESCipher|New|NewX)$"))
         ((call_expression function: (selector_expression operand: (identifier) @p2 field: (field_identifier) @f2) arguments: (argument_list . (_) . (type_conversion_expression operand: (interpreted_string_literal)))) @match (#eq? @p2 "hmac") (#eq? @f2 "New"))]""",
    'package p\n\nimport "crypto/aes"\n\nfunc c() {\n\tblock, _ := aes.NewCipher([]byte("0123456789abcdef"))\n\t_ = block\n}\n',
    'package p\n\nimport (\n\t"crypto/aes"\n\t"os"\n)\n\nfunc c() {\n\tblock, _ := aes.NewCipher([]byte(os.Getenv("DATA_KEY")))\n\t_ = block\n}\n',
    KEY_MSG, lang="go", applies=GOA, files=["**/*.go"], cwe=["CWE-321", "CWE-798"], asvs=["V13.3.1"], docv="OWASP Cheat Sheet Series (current)")
sec("JS-HARDCODED-SECRET", "Password/API key assigned a string literal", SMCS, SM_Q,
    r"""[((variable_declarator name: (identifier) @n value: (string (string_fragment) @match)) (#match? @n "(?i)^(password|passwd|pwd|secret|client_?secret|api_?key|access_?token|auth_?token|private_?key|secret_?key)$"))
         ((pair key: [(property_identifier) (string (string_fragment))] @n value: (string (string_fragment) @match)) (#match? @n "(?i)^[\"']?(password|passwd|secret|client_?secret|api_?key|access_?token|auth_?token|private_?key|secret_?key)[\"']?$"))]""",
    "const db = mysql.createConnection({ host: 'db', user: 'app', password: 'S3cr3t!pass' })\n",
    "const db = mysql.createConnection({ host: 'db', user: 'app', password: process.env.DB_PASSWORD })\n",
    "A credential is written into the source, so everyone with the code has it and rotating it needs a release. Read it from the environment or a secret manager.",
    sev="critical", mode="ai-confirm", ai="Is this a real credential (not a placeholder, test fixture, form field label or documentation example)?",
    filters=["node.lacks_re:(?i)^(changeme|password|secret|xxx+|\\*+|<.*>|\\$\\{.*\\}|example.*|your.*|test.*|dummy.*|placeholder.*|\\s*)$"],
    cwe=["CWE-798"], asvs=["V13.3.1"], docv="OWASP Cheat Sheet Series (current)")
sec("PHP-HARDCODED-SECRET", "Password/API key assigned a string literal", SMCS, SM_Q,
    r"""[((assignment_expression left: (variable_name (name) @n) right: (string (string_content) @match)) (#match? @n "(?i)^(password|passwd|pwd|secret|client_?secret|api_?key|access_?token|auth_?token|private_?key|secret_?key|db_?pass(word)?)$"))
         ((assignment_expression left: (variable_name (name) @n) right: (encapsed_string (string_content) @match)) (#match? @n "(?i)^(password|passwd|pwd|secret|client_?secret|api_?key|access_?token|auth_?token|private_?key|secret_?key|db_?pass(word)?)$"))]""",
    "<?php\n$db_password = 'S3cr3t!pass';\n$pdo = new PDO($dsn, 'app', $db_password);\n",
    "<?php\n$db_password = getenv('DB_PASSWORD');\n$pdo = new PDO($dsn, 'app', $db_password);\n",
    "A credential is written into the source, so everyone with the code has it and rotating it needs a release. Read it from the environment or a secret manager.",
    sev="critical", lang="php", applies={"php": ">=7.0"}, files=["**/*.php"], mode="ai-confirm", ai="Is this a real credential (not a placeholder, test fixture or documentation example)?",
    filters=["node.lacks_re:(?i)^(changeme|password|secret|xxx+|\\*+|<.*>|example.*|your.*|test.*|dummy.*|placeholder.*|\\s*)$"],
    cwe=["CWE-798"], asvs=["V13.3.1"], docv="OWASP Cheat Sheet Series (current)")

PYSSL = "https://docs.python.org/3/library/ssl.html"
sec("PY-SSL-OLD-PROTOCOL", "SSL/TLS context pinned to SSLv2/SSLv3/TLS 1.0/1.1", PYSSL,
    "OpenSSL has deprecated all version specific protocols.",
    r"""[((attribute object: (identifier) @o attribute: (identifier) @a) @match (#eq? @o "ssl") (#match? @a "^PROTOCOL_(SSLv2|SSLv3|TLSv1|TLSv1_1)$"))
         ((assignment left: (attribute attribute: (identifier) @k) right: (attribute attribute: (identifier) @v) @match) (#eq? @k "minimum_version") (#match? @v "^(SSLv3|TLSv1|TLSv1_1)$"))]""",
    "import ssl\nctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1)\n",
    "import ssl\nctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)\nctx.minimum_version = ssl.TLSVersion.TLSv1_2\n",
    "The context negotiates (or allows) a protocol version with known weaknesses (POODLE, BEAST, no modern ciphers). Use PROTOCOL_TLS_CLIENT/SERVER with minimum_version = TLSVersion.TLSv1_2 or later.",
    lang="python", applies=PYA, files=["**/*.py"], cwe=["CWE-757", "CWE-327"], asvs=["V12.1.1"], docv="Python 3 docs")
sec("KT-STACKTRACE-TO-RESPONSE", "Stack trace sent in the HTTP response (Kotlin)", ERR, ERR_Q,
    r"""((call_expression [(identifier) (navigation_expression (_) (identifier))] @c (value_arguments (value_argument) @a)) @match (#match? @c "(^|\\.)(respond|respondText|write|print|println)$") (#match? @a "stackTraceToString\\(\\)|printStackTrace"))""",
    "fun Application.errors() {\n    install(StatusPages) {\n        exception<Throwable> { call, cause ->\n            call.respondText(cause.stackTraceToString(), status = HttpStatusCode.InternalServerError)\n        }\n    }\n}\n",
    "fun Application.errors() {\n    install(StatusPages) {\n        exception<Throwable> { call, cause ->\n            log.error(\"request failed\", cause)\n            call.respondText(\"Internal error\", status = HttpStatusCode.InternalServerError)\n        }\n    }\n}\n",
    ERR_MSG, lang="kotlin", applies=KA, files=["**/*.kt"], filters=["file.has_re:respond|HttpServletResponse|ServerResponse"],
    cwe=["CWE-209"], asvs=["V16.5.1"], docv="OWASP Cheat Sheet Series (current)")


# ------------------------------------------------------------------ framework security guides (Django checklist, Flask, Express)
DJCK = "https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/"
PROD_AI = "Are these production settings (not a development/test settings module or a local-only configuration)?"
sec("PY-DJANGO-ALLOWED-HOSTS-ANY", "Django ALLOWED_HOSTS accepts any host", DJCK,
    "This setting is required to protect your site against some CSRF attacks.",
    r"""((assignment left: (identifier) @n right: (list (string (string_content) @v)) @match) (#eq? @n "ALLOWED_HOSTS") (#eq? @v "*"))""",
    "DEBUG = False\nALLOWED_HOSTS = ['*']\n", "DEBUG = False\nALLOWED_HOSTS = ['shop.example.com']\n",
    "Any Host header is accepted, enabling host-header poisoning of password-reset links and cache entries. List the real host names.",
    sev="minor", lang="python", applies={"django": ">=3.2"}, files=["**/*.py"], mode="ai-confirm", ai=PROD_AI,
    filters=["file.has_re:(?m)^(DEBUG|INSTALLED_APPS|MIDDLEWARE|ROOT_URLCONF)\\s*="], cwe=["CWE-20"], asvs=["V4.1.3"], docv="Django 5.2 docs")
sec("PY-DJANGO-COOKIE-NOT-SECURE", "Django session/CSRF cookie Secure flag turned off", DJCK,
    "Set this to True to avoid transmitting the session cookie over HTTP accidentally.",
    r"""((assignment left: (identifier) @n right: (false) @match) (#match? @n "^(SESSION_COOKIE_SECURE|CSRF_COOKIE_SECURE)$"))""",
    "SESSION_COOKIE_SECURE = False\n", "SESSION_COOKIE_SECURE = True\n",
    "The session (or CSRF) cookie is also sent over plain HTTP, where it can be read and replayed. Set it to True once the site is served over HTTPS.",
    sev="minor", lang="python", applies={"django": ">=3.2"}, files=["**/*.py"], mode="ai-confirm", ai=PROD_AI,
    cwe=["CWE-614"], asvs=["V3.3.1"], docv="Django 5.2 docs")
FLSEC = "https://flask.palletsprojects.com/en/stable/web-security/"
sec("PY-FLASK-SESSION-COOKIE-NOT-SECURE", "Flask session cookie Secure/HttpOnly turned off", FLSEC, "SESSION_COOKIE_SECURE = True",
    r"""[((keyword_argument name: (identifier) @n value: (false)) @match (#match? @n "^(SESSION_COOKIE_SECURE|SESSION_COOKIE_HTTPONLY|REMEMBER_COOKIE_SECURE)$"))
         ((assignment left: (subscript subscript: (string (string_content) @k)) right: (false)) @match (#match? @k "^(SESSION_COOKIE_SECURE|SESSION_COOKIE_HTTPONLY|REMEMBER_COOKIE_SECURE)$"))]""",
    "app.config.update(SESSION_COOKIE_SECURE=False, SESSION_COOKIE_SAMESITE='Lax')\n",
    "app.config.update(SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')\n",
    "The Flask session cookie is sent over plain HTTP (or readable by scripts), so it can be stolen and replayed. Enable SESSION_COOKIE_SECURE and SESSION_COOKIE_HTTPONLY in production.",
    sev="minor", lang="python", applies={"flask": ">=2.0"}, files=["**/*.py"], mode="ai-confirm", ai=PROD_AI,
    cwe=["CWE-614", "CWE-1004"], asvs=["V3.3.1"], docv="Flask docs (stable)")
EXSEC = "https://expressjs.com/en/advanced/best-practice-security.html"
sec("JS-SESSION-COOKIE-NOT-SECURE", "express-session/cookie-session cookie with secure: false", EXSEC,
    "Ensures the browser only sends the cookie over HTTPS",
    r"""((pair key: (property_identifier) @k value: (object (pair key: (property_identifier) @s value: (false)) @match)) (#eq? @k "cookie") (#match? @s "^(secure|httpOnly)$"))""",
    "const session = require('express-session')\napp.use(session({ secret: process.env.SESSION_SECRET, cookie: { secure: false } }))\n",
    "const session = require('express-session')\napp.use(session({ secret: process.env.SESSION_SECRET, cookie: { secure: true, httpOnly: true, sameSite: 'lax' } }))\n",
    "The session cookie is sent over plain HTTP (or readable by scripts), so it can be stolen and replayed. Set secure: true (behind a proxy also app.set('trust proxy', 1)) and keep httpOnly.",
    sev="minor", mode="ai-confirm", ai=PROD_AI, filters=["file.has_re:express-session|cookie-session"], cwe=["CWE-614", "CWE-1004"], asvs=["V3.3.1"], docv="Express docs")

# ------------------------------------------------------------------ ASVS 5.0 gap batch (2026-10)
PYF = dict(lang="python", applies=PYA, files=["**/*.py"])
JAF = dict(lang="java", applies=JA, files=["**/*.java"])
PHF = dict(lang="php", applies={"php": ">=7.4"}, files=["**/*.php"])
DKF = dict(lang="dockerfile", applies={"any": "*"}, files=["**/Dockerfile", "**/Dockerfile.*", "**/*.dockerfile", "**/Containerfile"])

# V1.1.2 double encoding (CWE-116)
DENC = "https://owasp.org/www-community/Double_Encoding"
DENC_Q = "encoding user request parameters twice"
DENC_MSG = "The value is encoded twice, so the receiver decodes it once and is left with escape sequences (%2520, &amp;lt;): output is garbled, and a filter that checks the once-decoded text can be bypassed. Encode exactly once, at the boundary where the value enters the target syntax."
sec("JS-DOUBLE-ENCODING", "Value encoded twice with the same encoder", DENC, DENC_Q,
    r"""((call_expression function: (identifier) @f arguments: (arguments . (call_expression function: (identifier) @g) .)) @match (#eq? @f @g) (#match? @f "^(encodeURIComponent|encodeURI|escape)$"))""",
    "const url = '/search?q=' + encodeURIComponent(encodeURIComponent(term))\n",
    "const url = '/search?q=' + encodeURIComponent(term)\n",
    DENC_MSG, sev="minor", cwe=["CWE-116"], asvs=["V1.1.2"])
sec("PY-DOUBLE-ENCODING", "Value escaped or quoted twice with the same function", DENC, DENC_Q,
    r"""((call function: (_) @f arguments: (argument_list . (call function: (_) @g) .)) @match (#eq? @f @g) (#match? @f "^(html\\.escape|escape|quote|quote_plus|parse\\.quote|parse\\.quote_plus|urllib\\.parse\\.quote|urllib\\.parse\\.quote_plus|markupsafe\\.escape)$"))""",
    "from urllib.parse import quote\nurl = '/files/' + quote(quote(name))\n",
    "from urllib.parse import quote\nurl = '/files/' + quote(name)\n",
    DENC_MSG, sev="minor", cwe=["CWE-116"], asvs=["V1.1.2"], **PYF)
sec("PHP-DOUBLE-ENCODING", "Value encoded twice with the same function", DENC, DENC_Q,
    r"""((function_call_expression function: (name) @f arguments: (arguments . (argument (function_call_expression function: (name) @g)) .)) @match (#eq? @f @g) (#match? @f "^(htmlspecialchars|htmlentities|urlencode|rawurlencode)$"))""",
    "<?php\necho htmlspecialchars(htmlspecialchars($title));\n",
    "<?php\necho htmlspecialchars($title);\n",
    DENC_MSG, sev="minor", cwe=["CWE-116"], asvs=["V1.1.2"], **PHF)

# V1.2.8 LaTeX shell escape
TEX = "https://tug.org/texlive/doc/texlive-en/texlive-en.html"
TEX_MSG = "The TeX engine runs with shell escape enabled, so a document that contains \\write18 (or \\immediate\\write18) executes arbitrary shell commands. When any part of the document comes from users this is command execution; drop -shell-escape (TeX Live's restricted mode is the default)."
sec("PY-LATEX-SHELL-ESCAPE", "TeX engine started with -shell-escape", TEX, "shell_escape",
    r"""((call function: (_) @f arguments: (argument_list [(list (string) @s) (string) @s])) @match (#match? @f "(subprocess\\.)?(run|Popen|call|check_call|check_output|system)$") (#match? @s "(^[rbuf]*['\"]|\\s)--?(shell-escape|enable-write18)(['\"]|\\s)"))""",
    "import subprocess\nsubprocess.run(['pdflatex', '-shell-escape', path], check=True)\n",
    "import subprocess\nsubprocess.run(['pdflatex', '-no-shell-escape', path], check=True)\n",
    TEX_MSG, cwe=["CWE-78"], asvs=["V1.2.8"], **PYF)
sec("JS-LATEX-SHELL-ESCAPE", "TeX engine started with -shell-escape", TEX, "shell_escape",
    r"""((call_expression function: (_) @f arguments: (arguments [(array [(string) (template_string)] @s) (string) @s (template_string) @s])) @match (#match? @f "(^|\\.)(spawn|spawnSync|exec|execSync|execFile|execFileSync)$") (#match? @s "(^['\"`]|\\s)--?(shell-escape|enable-write18)(['\"`]|\\s)"))""",
    "const { spawn } = require('child_process')\nspawn('xelatex', ['-shell-escape', file])\n",
    "const { spawn } = require('child_process')\nspawn('xelatex', ['-no-shell-escape', file])\n",
    TEX_MSG, cwe=["CWE-78"], asvs=["V1.2.8"])

# V1.2.9 untrusted input used as a regular expression (CWE-730)
RX_MSG = "Request data becomes a regular expression, so a user can inject metacharacters to change what matches or send a catastrophically backtracking pattern that ties up the server (ReDoS). Escape the value first ({esc}) or match it as plain text."
sec("JS-REGEX-INJECTION", "Request data used as a RegExp pattern", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/RegExp/escape",
    "escapes any potential regex syntax characters",
    r"""([(new_expression constructor: (identifier) @c arguments: (arguments . (_) @a)) (call_expression function: (identifier) @c arguments: (arguments . (_) @a))] @match (#eq? @c "RegExp") (#match? @a "^((req|request)\\.(query|body|params)|ctx\\.(query|params|request\\.body))\\b"))""",
    "app.get('/find', (req, res) => {\n  const re = new RegExp(req.query.q, 'i')\n  res.json(items.filter((i) => re.test(i.name)))\n})\n",
    "app.get('/find', (req, res) => {\n  const re = new RegExp(RegExp.escape(req.query.q), 'i')\n  res.json(items.filter((i) => re.test(i.name)))\n})\n",
    RX_MSG.format(esc="RegExp.escape or a lodash escapeRegExp"), cwe=["CWE-730"], asvs=["V1.2.9"], docv="MDN (current)")
sec("PY-REGEX-INJECTION", "Request data used as a regular expression", "https://docs.python.org/3/library/re.html",
    "may have regular expression metacharacters in it",
    r"""((call function: (attribute object: (identifier) @m attribute: (identifier) @f) arguments: (argument_list . (_) @a)) @match (#eq? @m "re") (#match? @f "^(compile|search|match|fullmatch|findall|finditer|sub|subn|split)$") (#match? @a "^request\\.(args|form|values|GET|POST|json|query_params|data)\\b"))""",
    "import re\n\n@app.route('/find')\ndef find():\n    pat = re.compile(request.args['q'])\n    return [n for n in NAMES if pat.search(n)]\n",
    "import re\n\n@app.route('/find')\ndef find():\n    pat = re.compile(re.escape(request.args['q']))\n    return [n for n in NAMES if pat.search(n)]\n",
    RX_MSG.format(esc="re.escape"), cwe=["CWE-730"], asvs=["V1.2.9"], docv="Python 3 docs", **PYF)
sec("JAVA-REGEX-INJECTION", "Request parameter compiled as a regex Pattern", "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/regex/Pattern.html",
    "Returns a literal pattern",
    r"""((method_invocation object: (identifier) @o name: (identifier) @n arguments: (argument_list . (method_invocation name: (identifier) @g))) @match (#eq? @o "Pattern") (#match? @n "^(compile|matches)$") (#match? @g "^(getParameter|getHeader|getQueryString)$"))""",
    "class S {\n  boolean find(HttpServletRequest req, String text) {\n    return Pattern.compile(req.getParameter(\"q\")).matcher(text).find();\n  }\n}\n",
    "class S {\n  boolean find(HttpServletRequest req, String text) {\n    return Pattern.compile(Pattern.quote(req.getParameter(\"q\"))).matcher(text).find();\n  }\n}\n",
    RX_MSG.format(esc="Pattern.quote"), cwe=["CWE-730"], asvs=["V1.2.9"], docv="Java SE 21 API", **JAF)

# V1.2.10 CSV formula injection (CWE-1236): needs to know where cell values come from -> ai-confirm
CSV = "https://owasp.org/www-community/attacks/CSV_Injection"
CSV_MSG = "Cells starting with =, +, -, @, tab or CR are run as formulas when the export is opened in a spreadsheet, so user-supplied text can execute formulas or exfiltrate data. Prefix such values with a single quote (and quote every field) before writing."
CSV_AI = "Do any of the written cell values come from users (form fields, names, comments) without neutralising a leading = + - @ tab or CR?"
sec("PY-CSV-FORMULA-INJECTION", "CSV export of request-derived values", CSV, "Formula Injection",
    r"""((call function: (attribute attribute: (identifier) @f) arguments: (argument_list . (_))) @match (#match? @f "^(writerow|writerows)$"))""",
    "import csv\nfrom flask import request\n\ndef export(out):\n    w = csv.writer(out)\n    w.writerow([request.form['name'], request.form['comment']])\n",
    "import csv\n\ndef export(out, totals):\n    w = csv.writer(out)\n    w.writerow(['total', totals])\n",
    CSV_MSG, sev="minor", mode="ai-confirm", ai=CSV_AI, cwe=["CWE-1236"], asvs=["V1.2.10"],
    filters=[r"file.has_re:\bimport csv\b|\bfrom csv import\b", r"file.has_re:\b(request|flask|django|fastapi|starlette)\b"], **PYF)
sec("PHP-CSV-FORMULA-INJECTION", "fputcsv with request-derived values", CSV, "Formula Injection",
    r"""((function_call_expression function: (name) @f) @match (#eq? @f "fputcsv"))""",
    "<?php\n$out = fopen('php://output', 'w');\nfputcsv($out, [$_POST['name'], $_POST['comment']]);\n",
    "<?php\n$out = fopen('php://output', 'w');\nfputcsv($out, ['total', $total]);\n",
    CSV_MSG, sev="minor", mode="ai-confirm", ai=CSV_AI, cwe=["CWE-1236"], asvs=["V1.2.10"],
    filters=[r"file.has_re:\$_(GET|POST|REQUEST)\b|->(input|get|post)\(|Request\b"], **PHF)

# V3.3.3 __Host- prefix for host-only session cookies (CWE-565)
HOST = "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie"
HOST_MSG = "This session/auth cookie has no __Host- prefix, so a sibling subdomain (or a network attacker on http://) can plant a cookie with the same name that the app then trusts (cookie tossing/fixation). Name it __Host-<name> and set Secure, Path=/ and no Domain."
HOST_AI = "Is this a session or authentication cookie for a single host (no Domain needed for sharing across subdomains)?"
sec("JS-COOKIE-WITHOUT-HOST-PREFIX", "Session cookie set without the __Host- prefix", HOST, "__Host-",
    r"""((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p) arguments: (arguments . (string (string_fragment) @n) (_) (object) @opts)) @match (#eq? @p "cookie") (#match? @o "^(res|response|reply)$") (#match? @n "(?i)(sess|auth|token|sid|jwt)") (#not-match? @n "^__(Host|Secure)-"))""",
    "app.post('/login', (req, res) => {\n  res.cookie('session', token, { secure: true, httpOnly: true, sameSite: 'lax' })\n  res.end()\n})\n",
    "app.post('/login', (req, res) => {\n  res.cookie('__Host-session', token, { secure: true, httpOnly: true, sameSite: 'lax', path: '/' })\n  res.end()\n})\n",
    HOST_MSG, sev="minor", mode="ai-confirm", ai=HOST_AI, cwe=["CWE-565"], asvs=["V3.3.3"], filters=[r"cap.lacks_re:opts:\bdomain\s*:"], docv="MDN (current)")
sec("PY-COOKIE-WITHOUT-HOST-PREFIX", "Session cookie set without the __Host- prefix", HOST, "__Host-",
    r"""((call function: (attribute attribute: (identifier) @f) arguments: (argument_list . (string (string_content) @n))) @match (#eq? @f "set_cookie") (#match? @n "(?i)(sess|auth|token|sid|jwt)") (#not-match? @n "^__(Host|Secure)-"))""",
    "resp.set_cookie('session', token, secure=True, httponly=True, samesite='Lax')\n",
    "resp.set_cookie('__Host-session', token, secure=True, httponly=True, samesite='Lax', path='/')\n",
    HOST_MSG, sev="minor", mode="ai-confirm", ai=HOST_AI, cwe=["CWE-565"], asvs=["V3.3.3"], filters=[r"node.lacks_re:\bdomain\s*="], docv="MDN (current)", **PYF)

# V3.5.3 state changes through GET / any method (CWE-650, CWE-352)
CSRF = CS + "Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html"
sec("JAVA-REQUESTMAPPING-NO-METHOD", "Handler @RequestMapping without an HTTP method", "https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-requestmapping.html",
    "HTTP method specific shortcut variants",
    r"""((method_declaration (modifiers (annotation name: (identifier) @a) @ann)) @match (#eq? @a "RequestMapping"))""",
    "@RestController\nclass AccountController {\n  @RequestMapping(\"/account/delete\")\n  void delete(@RequestParam long id) { accounts.delete(id); }\n}\n",
    "@RestController\nclass AccountController {\n  @PostMapping(\"/account/delete\")\n  void delete(@RequestParam long id) { accounts.delete(id); }\n}\n",
    "A method-level @RequestMapping without method= answers every HTTP verb, including GET, so a state-changing handler can be triggered by a link or image tag and slips past CSRF protection that only covers POST. Use @PostMapping/@PutMapping/@DeleteMapping (or @GetMapping for read-only handlers).",
    sev="minor", mode="ai-confirm", ai="Does this handler change server-side state (write, delete, send, log out)?", cwe=["CWE-650", "CWE-352"], asvs=["V3.5.3"],
    filters=[r"cap.lacks_re:ann:\bmethod\s*="], docv="Spring Framework 6.2 reference", **JAF)
sec("JS-GET-STATE-CHANGE", "GET route whose path names a state change", CSRF, "Do not use GET requests for state changing operations",
    r"""((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p) arguments: (arguments . (string (string_fragment) @path))) @match (#eq? @p "get") (#match? @o "^(app|router|api|server)$") (#match? @path "(?i)/(delete|remove|destroy|update|create|logout|signout|transfer|approve|reset|unsubscribe)([/?:-]|$)"))""",
    "const router = express.Router()\nrouter.get('/account/delete/:id', async (req, res) => {\n  await accounts.remove(req.params.id)\n  res.redirect('/')\n})\n",
    "const router = express.Router()\nrouter.post('/account/delete/:id', async (req, res) => {\n  await accounts.remove(req.params.id)\n  res.redirect('/')\n})\n",
    "This GET route's path names a state change. GET requests are sent by links, prefetchers and image tags and are usually exempt from CSRF checks, so the action can be triggered cross-site. Use POST/PUT/DELETE with CSRF protection.",
    sev="minor", mode="ai-confirm", ai="Does this GET handler change server-side state?", cwe=["CWE-650", "CWE-352"], asvs=["V3.5.3"],
    filters=[r"file.has_re:express|Router\(|fastify|koa"])

# V4.3.1 GraphQL depth/cost limits (CWE-770)
GQLCS = CS + "GraphQL_Cheat_Sheet.html"
sec("JS-GRAPHQL-NO-DEPTH-LIMIT", "GraphQL server without query depth/cost limits", GQLCS, "Query Limiting",
    r"""((new_expression constructor: (identifier) @c arguments: (arguments . (object) @cfg)) @match (#match? @c "^(ApolloServer|ApolloServerBase)$"))""",
    "const server = new ApolloServer({ typeDefs, resolvers })\n",
    "const server = new ApolloServer({ typeDefs, resolvers, validationRules: [depthLimit(8)] })\n",
    "The server accepts arbitrarily deep or expensive queries, so one nested query (friends { friends { friends ... } }) can exhaust CPU, memory or the database. Add depth and cost/complexity limits (validationRules such as graphql-depth-limit, or a cost-analysis plugin).",
    sev="minor", mode="ai-confirm", ai="Is this a production GraphQL endpoint reachable by untrusted clients, with no depth/cost limiting configured elsewhere (gateway, plugin)?",
    cwe=["CWE-770"], asvs=["V4.3.1"], filters=[r"cap.lacks_re:cfg:(?i)validationRules|depth|complexity|cost|plugins", r"file.lacks_re:(?i)depthLimit|costAnalysis|createComplexityLimitRule|queryComplexity"])

# V5.2.3 archive decompression limits (CWE-409) / V5.2.5 symlinks from archives (CWE-59)
ZIPPY = "https://docs.python.org/3/library/zipfile.html"
sec("PY-ARCHIVE-EXTRACT-NO-LIMIT", "Archive extracted without size or entry limits", ZIPPY, "Decompression pitfalls",
    r"""((call function: (attribute attribute: (identifier) @f)) @match (#eq? @f "extractall"))""",
    "import zipfile\n\ndef unpack(upload, dest):\n    with zipfile.ZipFile(upload) as z:\n        z.extractall(dest)\n",
    "import zipfile\n\ndef unpack(upload, dest):\n    with zipfile.ZipFile(upload) as z:\n        if sum(i.file_size for i in z.infolist()) > MAX_BYTES:\n            raise ValueError('archive too large')\n        z.extractall(dest)\n",
    "The whole archive is unpacked without checking total uncompressed size or entry count, so a small zip bomb can fill the disk or memory. Sum ZipInfo.file_size / TarInfo.size (and count entries) against a limit before extracting.",
    sev="minor", mode="ai-confirm", ai="Can the archive come from users or another untrusted source?", cwe=["CWE-409"], asvs=["V5.2.3"],
    filters=[r"func.lacks_re:file_size|\.size\b|infolist|getmembers|namelist|MAX_|max_"], docv="Python 3 docs", **PYF)
TARPY = "https://docs.python.org/3/library/tarfile.html"
sec("PY-TAR-EXTRACT-NO-FILTER", "tarfile extraction without an extraction filter", TARPY, "Extraction filters",
    r"""((call function: (attribute object: (_) @o attribute: (identifier) @f) arguments: (argument_list) @args) @match (#match? @f "^(extractall|extract)$") (#match? @o "(?i)tar"))""",
    "import tarfile\n\ndef unpack(path, dest):\n    with tarfile.open(path) as tar:\n        tar.extractall(dest)\n",
    "import tarfile\n\ndef unpack(path, dest):\n    with tarfile.open(path) as tar:\n        tar.extractall(dest, filter='data')\n",
    "Without filter='data' the archive may create symlinks or hard links pointing outside the destination, absolute paths, device files and setuid bits, so a crafted tarball can overwrite files elsewhere. Pass filter='data' (Python 3.12+, backported to security releases).",
    cwe=["CWE-59", "CWE-22"], asvs=["V5.2.5"], filters=[r"cap.lacks_re:args:\bfilter\s*="], docv="Python 3 docs", **PYF)

# V5.4.2 Content-Disposition built from a raw file name (CWE-113)
CD = "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Disposition"
CD_MSG = "The download file name is concatenated into Content-Disposition as-is: quotes, semicolons or CR/LF in it break the header (header injection, a different file name or type). Build the header with a helper that quotes and encodes it ({h}) or use filename*=UTF-8''<percent-encoded>."
CD_AI = "Can the file name come from users or uploaded metadata?"
sec("JS-CONTENT-DISPOSITION-CONCAT", "Content-Disposition built by string concatenation", CD, "filename*",
    r"""((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments . (string (string_fragment) @h) . [(binary_expression) (template_string (template_substitution))] .)) @match (#match? @p "^(setHeader|set|header|append)$") (#match? @h "(?i)^content-disposition$"))""",
    "res.setHeader('Content-Disposition', 'attachment; filename=\"' + file.name + '\"')\n",
    "res.attachment(file.name)\n",
    CD_MSG.format(h="res.attachment() / content-disposition package"), sev="minor", mode="ai-confirm", ai=CD_AI, cwe=["CWE-113"], asvs=["V5.4.2"], docv="MDN (current)")
sec("JAVA-CONTENT-DISPOSITION-CONCAT", "Content-Disposition built by string concatenation", CD, "filename*",
    r"""((method_invocation name: (identifier) @n arguments: (argument_list . (string_literal) @h . (binary_expression) .)) @match (#match? @n "^(setHeader|addHeader|header)$") (#match? @h "(?i)^\"content-disposition\"$"))""",
    "class D {\n  void send(HttpServletResponse resp, String name) {\n    resp.setHeader(\"Content-Disposition\", \"attachment; filename=\" + name);\n  }\n}\n",
    "class D {\n  void send(HttpServletResponse resp, String name) {\n    resp.setHeader(\"Content-Disposition\", ContentDisposition.attachment().filename(name, StandardCharsets.UTF_8).build().toString());\n  }\n}\n",
    CD_MSG.format(h="Spring ContentDisposition.attachment().filename(name, UTF_8)"), sev="minor", mode="ai-confirm", ai=CD_AI, cwe=["CWE-113"], asvs=["V5.4.2"], docv="MDN (current)", **JAF)

# V7.3.1 inactivity timeout / V7.3.2 absolute lifetime (CWE-613)
SESS = "https://expressjs.com/en/resources/middleware/session.html"
sec("JS-SESSION-NO-MAXAGE", "express-session without cookie maxAge/expires", SESS, "no maximum age is set",
    r"""((call_expression function: (identifier) @s arguments: (arguments . (object) @cfg)) @match (#match? @s "^(session|expressSession)$"))""",
    "const session = require('express-session')\napp.use(session({ secret: process.env.SESSION_SECRET, resave: false, saveUninitialized: false }))\n",
    "const session = require('express-session')\napp.use(session({ secret: process.env.SESSION_SECRET, resave: false, saveUninitialized: false, rolling: true, cookie: { maxAge: 30 * 60 * 1000 } }))\n",
    "No cookie maxAge/expires is set, so the session lives as long as the browser keeps running (often days) and is never ended for inactivity. Set cookie.maxAge (with rolling: true for an idle timeout) and expire sessions server-side in the store.",
    sev="minor", cwe=["CWE-613"], asvs=["V7.3.1"], filters=[r"file.has_re:express-session", r"cap.lacks_re:cfg:\b(maxAge|expires)\b"], docv="Express docs")
OSESS = CS + "Session_Management_Cheat_Sheet.html"
sec("PY-SESSION-LIFETIME-LONG", "Session lifetime set to 30 days or more", OSESS, "Absolute Timeout",
    r"""[((assignment left: (_) @n right: (integer) @v) @match (#match? @n "SESSION_COOKIE_AGE|PERMANENT_SESSION_LIFETIME") (#match? @v "^([3-9][0-9]{6}|2[6-9][0-9]{5}|259[2-9][0-9]{3}|[0-9]{8,})$"))
         ((assignment left: (_) @n right: (call function: (_) @td arguments: (argument_list (keyword_argument name: (identifier) @k value: (integer) @v)))) @match (#match? @n "SESSION_COOKIE_AGE|PERMANENT_SESSION_LIFETIME") (#match? @td "timedelta$") (#eq? @k "days") (#match? @v "^([3-9][0-9]|[0-9]{3,})$"))]""",
    "SESSION_COOKIE_AGE = 31536000  # one year\n",
    "SESSION_COOKIE_AGE = 60 * 60 * 8\n",
    "Sessions stay valid for 30 days or more, so a stolen session cookie (or an unattended device) keeps working for that long. Use an absolute lifetime of hours to a few days and re-authenticate after it.",
    sev="minor", mode="ai-confirm", ai="Is this the lifetime of an authenticated session (not a separate long-lived 'remember me' token with its own protections)?",
    cwe=["CWE-613"], asvs=["V7.3.2"], docv="OWASP Cheat Sheet Series (current)", **PYF)

# V10.2.1 OAuth authorization request without state/PKCE (CWE-352)
OAUTH = "https://www.rfc-editor.org/rfc/rfc9700.html"
OAUTH_MSG = "The authorization request asks for a code but carries neither state nor a PKCE code_challenge, so an attacker can inject their own authorization code into the victim's session (login CSRF). Send a PKCE code_challenge (S256), and a per-request state bound to the session."
OAUTH_AI = "Is this URL sent as-is (state and code_challenge are not appended elsewhere before redirecting)?"
OAUTH_FILTER = [r"node.has_re:response_type=code", r"node.lacks_re:[?&](state|code_challenge)="]
sec("JS-OAUTH-NO-STATE-PKCE", "OAuth authorization URL without state or PKCE", OAUTH, "Clients MUST prevent Cross-Site Request Forgery",
    r"""([(string) (template_string)] @match (#match? @match "response_type=code"))""",
    "const authUrl = `https://idp.example.com/authorize?response_type=code&client_id=${id}&redirect_uri=${cb}`\n",
    "const authUrl = `https://idp.example.com/authorize?response_type=code&client_id=${id}&redirect_uri=${cb}&state=${state}&code_challenge=${challenge}&code_challenge_method=S256`\n",
    OAUTH_MSG, sev="minor", mode="ai-confirm", ai=OAUTH_AI, cwe=["CWE-352"], asvs=["V10.2.1"], filters=OAUTH_FILTER, docv="RFC 9700")
sec("PY-OAUTH-NO-STATE-PKCE", "OAuth authorization URL without state or PKCE", OAUTH, "Clients MUST prevent Cross-Site Request Forgery",
    r"""((string) @match (#match? @match "response_type=code"))""",
    "AUTH_URL = f'https://idp.example.com/authorize?response_type=code&client_id={CLIENT_ID}'\n",
    "AUTH_URL = f'https://idp.example.com/authorize?response_type=code&client_id={CLIENT_ID}&state={state}&code_challenge={challenge}&code_challenge_method=S256'\n",
    OAUTH_MSG, sev="minor", mode="ai-confirm", ai=OAUTH_AI, cwe=["CWE-352"], asvs=["V10.2.1"], filters=OAUTH_FILTER, docv="RFC 9700", **PYF)

# V13.4.1 source-control metadata in images (CWE-538)
DCTX = "https://docs.docker.com/build/concepts/context/"
sec("DOCKER-COPY-GIT-DIR", "Repository .git directory copied into the image", DCTX, ".dockerignore",
    r"""([((copy_instruction (path) @p) @match) ((add_instruction (path) @p) @match)] (#match? @p "(^|/)\\.git/?$"))""",
    "FROM python:3.13-slim\nCOPY .git /app/.git\n", "FROM python:3.13-slim\nCOPY src /app/src\n",
    "The .git directory ends up in the image, exposing full history (including removed secrets) to anyone who can pull it. Keep .git out of images (list it in .dockerignore) and pass a commit id as a build arg instead.",
    cwe=["CWE-538"], asvs=["V13.4.1"], docv="Docker docs", **DKF)

# V13.4.4 HTTP TRACE enabled
TRACE = "https://tomcat.apache.org/tomcat-10.1-doc/config/http.html"
TRACE_MSG = "The TRACE method is enabled, so the server echoes requests back, including cookies and auth headers; combined with an XSS or a misbehaving proxy this exposes them (cross-site tracing). Keep TRACE disabled (the default)."
sec("JAVA-HTTP-TRACE-ENABLED", "HTTP TRACE turned on for the connector", TRACE, "allowTrace",
    r"""((method_invocation name: (identifier) @n arguments: (argument_list . (true) .)) @match (#eq? @n "setAllowTrace"))""",
    "class Cfg {\n  void customize(Connector connector) {\n    connector.setAllowTrace(true);\n  }\n}\n",
    "class Cfg {\n  void customize(Connector connector) {\n    connector.setAllowTrace(false);\n  }\n}\n",
    TRACE_MSG, sev="minor", cwe=["CWE-693"], asvs=["V13.4.4"], docv="Apache Tomcat 10.1 docs", **JAF)
sec("JS-HTTP-TRACE-ROUTE", "Route handler registered for HTTP TRACE", "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/06-Test_HTTP_Methods",
    "TRACE",
    r"""((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p)) @match (#eq? @p "trace") (#match? @o "^(app|router|server)$"))""",
    "const app = express()\napp.trace('*', (req, res) => res.send(req.headers))\n", "const app = express()\napp.get('/health', (req, res) => res.send('ok'))\n",
    TRACE_MSG, sev="minor", cwe=["CWE-693"], asvs=["V13.4.4"], filters=[r"file.has_re:express|Router\(|fastify|koa"])

# V14.2.1 secrets in URL query strings (CWE-598)
QS = "https://owasp.org/www-community/vulnerabilities/Information_exposure_through_query_strings_in_url"
QS_RX = r"[?&](password|passwd|pwd|secret|client_secret|api_?key|apikey|access_token|token|auth)=[$\x60{a-zA-Z0-9]"
QS_MSG = "A secret is sent in the URL query string, where it is written to server and proxy access logs, browser history and Referer headers. Send it in an Authorization header or the request body instead."
sec("JS-SECRET-IN-QUERY-STRING", "Secret sent in a URL query string", QS, "sensitive data",
    r"""((call_expression function: (_) @f arguments: (arguments . [(string) (template_string) (binary_expression)] @u)) @match (#match? @f "^(fetch|axios(\\.(get|post|put|delete|request))?|got|request|superagent\\.(get|post)|http\\.get|https\\.get|\\$\\.(get|ajax))$"))""",
    "const res = await fetch(`https://api.example.com/v1/items?api_key=${API_KEY}`)\n",
    "const res = await fetch('https://api.example.com/v1/items', { headers: { Authorization: `Bearer ${API_KEY}` } })\n",
    QS_MSG, sev="minor", cwe=["CWE-598"], asvs=["V14.2.1"], filters=["cap.has_re:u:(?i)" + QS_RX])
sec("PY-SECRET-IN-QUERY-STRING", "Secret sent in a URL query string", QS, "sensitive data",
    r"""((call function: (attribute object: (identifier) @o attribute: (identifier) @f) arguments: (argument_list . [(string) (binary_operator)] @u)) @match (#match? @o "^(requests|httpx|session|client|s)$") (#match? @f "^(get|post|put|delete|request)$"))""",
    "import requests\nr = requests.get(f'https://api.example.com/v1/items?api_key={API_KEY}')\n",
    "import requests\nr = requests.get('https://api.example.com/v1/items', headers={'Authorization': f'Bearer {API_KEY}'})\n",
    QS_MSG, sev="minor", cwe=["CWE-598"], asvs=["V14.2.1"], filters=["cap.has_re:u:(?i)" + QS_RX], **PYF)

# V15.4.1 shared non-thread-safe objects (CWE-567, CWE-362)
sec("JAVA-STATIC-DATEFORMAT", "Shared static DateFormat/MessageDigest instance", "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/text/SimpleDateFormat.html",
    "Date formats are not synchronized",
    r"""((field_declaration (modifiers) @mods type: (type_identifier) @t) @match (#match? @t "^(SimpleDateFormat|DateFormat|DecimalFormat|NumberFormat|MessageFormat|MessageDigest)$") (#match? @mods "\\bstatic\\b"))""",
    "class Dates {\n  private static final SimpleDateFormat FMT = new SimpleDateFormat(\"yyyy-MM-dd\");\n  static String day(Date d) { return FMT.format(d); }\n}\n",
    "class Dates {\n  private static final DateTimeFormatter FMT = DateTimeFormatter.ofPattern(\"yyyy-MM-dd\");\n  static String day(LocalDate d) { return FMT.format(d); }\n}\n",
    "This formatter/digest keeps internal mutable state but is shared through a static field, so concurrent threads corrupt each other's results (wrong dates, exceptions, bad hashes) with no error. Use java.time's immutable DateTimeFormatter, a ThreadLocal, or a new instance per call.",
    sev="major", cwe=["CWE-567", "CWE-362"], asvs=["V15.4.1"], filters=[r"node.lacks_re:ThreadLocal"], docv="Java SE 21 API", **JAF)

# V16.4.1 request data written to logs unencoded (CWE-117)
LOGI = "https://owasp.org/www-community/attacks/Log_Injection"
LOGI_MSG = "Request data goes into the log line unchanged, so CR/LF in it forges extra log entries (and other control characters can attack log viewers). Pass it as a structured/parameterised argument and strip or encode CR/LF (or use a JSON log encoder)."
sec("JAVA-LOG-INJECTION", "Request parameter concatenated into a log message", LOGI, "forge log entries",
    r"""((method_invocation object: (identifier) @l name: (identifier) @n arguments: (argument_list (binary_expression) @msg)) @match (#match? @l "(?i)^(log|logger)$") (#match? @n "^(trace|debug|info|warn|error)$") (#match? @msg "\\.(getParameter|getHeader|getQueryString|getRequestURI)\\("))""",
    "class L {\n  void login(HttpServletRequest req) {\n    log.info(\"login attempt for \" + req.getParameter(\"user\"));\n  }\n}\n",
    "class L {\n  void login(HttpServletRequest req) {\n    log.info(\"login attempt for {}\", Encode.forJava(req.getParameter(\"user\")));\n  }\n}\n",
    LOGI_MSG, sev="minor", cwe=["CWE-117"], asvs=["V16.4.1"], **JAF)
sec("PY-LOG-INJECTION", "Request data formatted into a log message", LOGI, "forge log entries",
    r"""((call function: (attribute object: (identifier) @l attribute: (identifier) @n) arguments: (argument_list . [(string) (binary_operator) (call)] @msg)) @match (#match? @l "^(log|logger|logging|_log|LOG|LOGGER)$") (#match? @n "^(debug|info|warning|error|critical|exception)$") (#match? @msg "\\brequest\\.(args|form|values|GET|POST|headers|json|query_params)\\b"))""",
    "logger.info(f\"login attempt for {request.form['user']}\")\n",
    "logger.info('login attempt for %r', request.form['user'])\n",
    LOGI_MSG, sev="minor", cwe=["CWE-117"], asvs=["V16.4.1"], **PYF)
sec("JS-LOG-INJECTION", "Request data formatted into a log message", LOGI, "forge log entries",
    r"""((call_expression function: (member_expression object: (_) @l property: (property_identifier) @n) arguments: (arguments . [(template_string) (binary_expression)] @msg)) @match (#match? @l "^(logger|log|console|req\\.log|fastify\\.log)$") (#match? @n "^(debug|info|warn|error|log)$") (#match? @msg "\\b(req|request)\\.(query|body|params|headers)\\b"))""",
    "logger.info(`login attempt for ${req.body.user}`)\n",
    "logger.info({ user: req.body.user }, 'login attempt')\n",
    LOGI_MSG, sev="minor", cwe=["CWE-117"], asvs=["V16.4.1"])

# V16.5.2 fail open when a dependency fails (CWE-636)
FAILS = "https://owasp.org/www-community/Fail_securely"
FAIL_MSG = "When the check throws (directory, policy service or token store down) this security decision returns true, so failures grant access. Return false / deny (or rethrow) on error and log the failure."
FAIL_AI = "Is this function's true result a security permission (authorised, valid token, allowed)?"
FAIL_NAME = "(?i)^(is|has|can|check|verify|validate)[A-Za-z]*(auth|allow|permi|access|valid|admin|role|grant|token|signature)"
sec("JAVA-FAIL-OPEN-CATCH", "Security check returns true from its catch block", FAILS, "isAdmin",
    r"""((method_declaration name: (identifier) @n body: (block (try_statement (catch_clause body: (block (return_statement (true))))))) @match (#match? @n "(?i)^(is|has|can|check|verify|validate)[A-Za-z]*(auth|allow|permi|access|valid|admin|role|grant|token|signature)"))""",
    "class Guard {\n  boolean isAuthorized(User u, String res) {\n    try {\n      return policy.allows(u, res);\n    } catch (Exception e) {\n      return true;\n    }\n  }\n}\n",
    "class Guard {\n  boolean isAuthorized(User u, String res) {\n    try {\n      return policy.allows(u, res);\n    } catch (Exception e) {\n      log.warn(\"policy check failed\", e);\n      return false;\n    }\n  }\n}\n",
    FAIL_MSG, mode="ai-confirm", ai=FAIL_AI, cwe=["CWE-636", "CWE-755"], asvs=["V16.5.2"], **JAF)
sec("PY-FAIL-OPEN-EXCEPT", "Security check returns True from its except block", FAILS, "isAdmin",
    r"""((function_definition name: (identifier) @n body: (block (try_statement (except_clause (block (return_statement (true))))))) @match (#match? @n "(?i)^(is|has|can|check|verify|validate)_?[a-z_]*(auth|allow|permi|access|valid|admin|role|grant|token|signature)"))""",
    "def is_authorized(user, resource):\n    try:\n        return policy.allows(user, resource)\n    except Exception:\n        return True\n",
    "def is_authorized(user, resource):\n    try:\n        return policy.allows(user, resource)\n    except Exception:\n        log.warning('policy check failed', exc_info=True)\n        return False\n",
    FAIL_MSG, mode="ai-confirm", ai=FAIL_AI, cwe=["CWE-636", "CWE-755"], asvs=["V16.5.2"], **PYF)
sec("JS-FAIL-OPEN-CATCH", "Security check returns true from its catch block", FAILS, "isAdmin",
    r"""([(function_declaration name: (identifier) @n body: (statement_block (try_statement handler: (catch_clause body: (statement_block (return_statement (true))))))) (method_definition name: (property_identifier) @n body: (statement_block (try_statement handler: (catch_clause body: (statement_block (return_statement (true)))))))] @match (#match? @n "(?i)^(is|has|can|check|verify|validate)[A-Za-z]*(auth|allow|permi|access|valid|admin|role|grant|token|signature)"))""",
    "async function isAuthorized(user, res) {\n  try {\n    return await policy.allows(user, res)\n  } catch (e) {\n    return true\n  }\n}\n",
    "async function isAuthorized(user, res) {\n  try {\n    return await policy.allows(user, res)\n  } catch (e) {\n    log.warn('policy check failed', e)\n    return false\n  }\n}\n",
    FAIL_MSG, mode="ai-confirm", ai=FAIL_AI, cwe=["CWE-636", "CWE-755"], asvs=["V16.5.2"])

for _r in P.R:
    _r["detection"]["exclude_tests"] = True  # security findings in test code are not production exposure

RULES = P.R

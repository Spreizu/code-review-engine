"""Python 3 pack: What's New removals/deprecations per release (3.8-3.14), stdlib security warnings,
Ruff rule docs (pyflakes/pycodestyle/bugbear/pyupgrade/bandit ports) for idioms and modernization gated on the
`python` dimension (pyproject requires-python, .python-version, setup.cfg, Pipfile, runtime.txt)."""
import re
from specs._common import Pack, secret_rules, PLACEHOLDER_RE

DOCS = "https://docs.python.org/3/"
WN = lambda v: DOCS + f"whatsnew/{v}.html"
LIB = lambda m: DOCS + f"library/{m}.html"
RUFF = lambda n: f"https://docs.astral.sh/ruff/rules/{n}/"


def rn(needle):
    """Ruff pages render `code` spans with surrounding spaces; normalise a doc sentence to the page text."""
    needle = re.sub(r"`([,.;:)])", r" \1", needle).replace("`", "")
    return needle.rstrip(" .")
P = Pack("PY", "python", "Python 3.14", {"python": "*"})


def imports(mod_re):
    """Any import of a module matching mod_re (import x / import x as y / from x import ...)."""
    return ('([(import_statement name: (dotted_name) @match) (import_statement name: (aliased_import name: (dotted_name) @match)) '
            f'(import_from_statement module_name: (dotted_name) @match)] (#match? @match "{mod_re}"))')


def from_import(mod, names_re):
    return f'(import_from_statement module_name: (dotted_name) @m (#eq? @m "{mod}") name: [(dotted_name) @match (aliased_import name: (dotted_name) @match)] (#match? @match "^({names_re})$"))'


def mcall(obj_re, attr_re, args=""):
    """obj.attr(...) where obj is a plain name."""
    a = f" {args}" if args else ""
    return (f'((call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list{a})) @match '
            f'(#match? @o "^({obj_re})$") (#match? @a "^({attr_re})$"))')


def dcall(obj_re, attr_re):
    """pkg.sub.attr(...) or pkg.attr(...): match on the attribute text."""
    return f'((call function: (attribute attribute: (identifier) @a) @f) @match (#match? @a "^({attr_re})$") (#match? @f "^({obj_re})\\\\.[A-Za-z_.]*$"))'


def kwarg(fn_re, name, value_node):
    return (f'((call function: (_) @f arguments: (argument_list (keyword_argument name: (identifier) @k value: {value_node}))) @match '
            f'(#match? @f "{fn_re}") (#eq? @k "{name}"))')


def removed_mod(id, ver, mods_re, url, needle, bad, good, msg, sev="critical"):
    P(id, f"Module removed in Python {ver}", url, needle, imports(f"^({mods_re})(\\\\.|$)"), bad, good, msg, sev=sev, kind="removal",
      cat="removal", applies={"python": f">={ver}"}, doc=f"What's New in Python {ver}", docv=f"Python {ver}")


# ------------------------------------------------------------------ removed modules
removed_mod("REMOVED-DISTUTILS", "3.12", "distutils", WN("3.12"), "distutils", "from distutils.core import setup\n",
            "from setuptools import setup\n", "distutils is gone in 3.12 (PEP 632); use setuptools / packaging / sysconfig / shutil.")
removed_mod("REMOVED-IMP", "3.12", "imp", WN("3.12"), "imp", "import imp\nm = imp.load_source('m', path)\n",
            "import importlib.util\nspec = importlib.util.spec_from_file_location('m', path)\n", "imp was removed in 3.12; use importlib.")
removed_mod("REMOVED-ASYNCORE", "3.12", "asynchat|asyncore|smtpd", WN("3.12"), "asynchat", "import asyncore\n", "import asyncio\n",
            "asynchat/asyncore/smtpd were removed in 3.12 (PEP 594); use asyncio (aiosmtpd for SMTP servers).")
removed_mod("REMOVED-DEAD-BATTERIES", "3.13", "aifc|audioop|cgitb|chunk|imghdr|mailcap|msilib|nis|nntplib|ossaudiodev|pipes|sndhdr|spwd|sunau|uu|xdrlib",
            WN("3.13"), "PEP 594", "import imghdr\nkind = imghdr.what(p)\n", "import filetype\nkind = filetype.guess(p)\n",
            "This 'dead battery' module was removed in 3.13 (PEP 594); see What's New for replacements.")
removed_mod("REMOVED-CGI", "3.13", "cgi", WN("3.13"), "cgi", "import cgi\nform = cgi.FieldStorage()\n",
            "from urllib.parse import parse_qs\nform = parse_qs(qs)\n", "cgi was removed in 3.13; use urllib.parse / email.message or a web framework.")
removed_mod("REMOVED-CRYPT", "3.13", "crypt", WN("3.13"), "crypt", "import crypt\nh = crypt.crypt(pw)\n",
            "import hashlib\nh = hashlib.scrypt(pw, salt=salt, n=2**14, r=8, p=1)\n", "crypt was removed in 3.13; use hashlib (scrypt/pbkdf2) or argon2/bcrypt packages.")
removed_mod("REMOVED-TELNETLIB", "3.13", "telnetlib", WN("3.13"), "telnetlib", "import telnetlib\n", "import asyncssh\n",
            "telnetlib was removed in 3.13; Telnet is plaintext anyway — prefer SSH (or telnetlib3 from PyPI).")
removed_mod("REMOVED-LIB2TO3", "3.13", "lib2to3", WN("3.13"), "lib2to3", "from lib2to3 import refactor\n", "import ast\n",
            "lib2to3 and 2to3 were removed in 3.13; use ast/LibCST/parso.")
removed_mod("REMOVED-TKINTER-TIX", "3.13", "tkinter\\\\.tix", WN("3.13"), "tkinter.tix", "import tkinter.tix\n", "import tkinter.ttk\n",
            "tkinter.tix was removed in 3.13; use tkinter.ttk.")
removed_mod("REMOVED-BINHEX", "3.11", "binhex", WN("3.11"), "binhex", "import binhex\n", "import binascii\n", "binhex was removed in 3.11.")
removed_mod("REMOVED-PARSER-FORMATTER", "3.10", "parser|formatter|symbol", WN("3.10"), "parser", "import parser\n", "import ast\n",
            "parser, symbol and formatter were removed in 3.10; use ast.")

# ------------------------------------------------------------------ removed / deprecated APIs
P("REMOVED-COLLECTIONS-ABC-ALIASES", "ABC imported from collections", WN("3.10"), "collections.abc",
  from_import("collections", "Mapping|MutableMapping|Sequence|MutableSequence|Set|MutableSet|Iterable|Iterator|Callable|Hashable|Sized|Container|Generator|Awaitable|Coroutine|AsyncIterable|AsyncIterator|KeysView|ValuesView|ItemsView|MappingView|ByteString"),
  "from collections import Mapping\n", "from collections.abc import Mapping\n",
  "The ABC aliases in collections were removed in 3.10; import from collections.abc.", sev="critical", kind="removal", cat="removal",
  applies={"python": ">=3.10"})
P("REMOVED-ASYNCIO-COROUTINE", "@asyncio.coroutine decorator", WN("3.11"), "asyncio.coroutine",
  '((decorator (attribute object: (identifier) @o attribute: (identifier) @match)) (#eq? @o "asyncio") (#eq? @match "coroutine"))',
  "@asyncio.coroutine\ndef f():\n    yield from g()\n", "async def f():\n    await g()\n",
  "Generator-based coroutines were removed in 3.11; use async def / await.", sev="critical", kind="removal", cat="removal", applies={"python": ">=3.11"})
P("REMOVED-UNITTEST-ALIASES", "Deprecated unittest assertion alias", WN("3.12"), "assertEquals",
  mcall("self", "assertEquals|assertNotEquals|failUnless|failIf|failUnlessEqual|failIfEqual|failUnlessRaises|assert_|assertAlmostEquals|assertNotAlmostEquals|failUnlessAlmostEqual|failIfAlmostEqual|assertRegexpMatches|assertNotRegexpMatches|assertRaisesRegexp|assertDictContainsSubset"),
  "class T(TestCase):\n    def test(self):\n        self.assertEquals(a, b)\n", "class T(TestCase):\n    def test(self):\n        self.assertEqual(a, b)\n",
  "These TestCase aliases were removed in 3.12; use the canonical names (assertEqual, assertTrue, assertRaisesRegex ...).",
  sev="critical", kind="removal", cat="removal", applies={"python": ">=3.12"})
P("REMOVED-SSL-WRAP-SOCKET", "ssl.wrap_socket()", WN("3.12"), "wrap_socket", mcall("ssl", "wrap_socket|match_hostname|RAND_pseudo_bytes"),
  "s = ssl.wrap_socket(sock)\n", "ctx = ssl.create_default_context()\ns = ctx.wrap_socket(sock, server_hostname=host)\n",
  "ssl.wrap_socket()/match_hostname() were removed in 3.12; use SSLContext.wrap_socket with create_default_context().",
  sev="critical", kind="removal", cat="removal", applies={"python": ">=3.12"})
P("REMOVED-CONFIGPARSER-LEGACY", "SafeConfigParser / readfp", WN("3.12"), "SafeConfigParser",
  '((call function: (attribute object: (identifier) @o attribute: (identifier) @match)) (#eq? @o "configparser") (#eq? @match "SafeConfigParser"))\n((call function: (attribute attribute: (identifier) @match)) (#eq? @match "readfp"))',
  "cp = configparser.SafeConfigParser()\n", "cp = configparser.ConfigParser()\n",
  "configparser.SafeConfigParser and readfp() were removed in 3.12; use ConfigParser and read_file().",
  sev="critical", kind="removal", cat="removal", applies={"python": ">=3.12"})
P("REMOVED-TIME-CLOCK", "time.clock()", WN("3.8"), "time.clock", mcall("time", "clock"), "t0 = time.clock()\n", "t0 = time.perf_counter()\n",
  "time.clock() was removed in 3.8; use time.perf_counter() or time.process_time().", sev="critical", kind="removal", cat="removal", applies={"python": ">=3.8"})
P("REMOVED-CGI-ESCAPE", "cgi.escape()", WN("3.8"), "and escape are removed from the cgi module", mcall("cgi", "escape"), "s = cgi.escape(t)\n", "s = html.escape(t)\n",
  "cgi.escape() was removed in 3.8; use html.escape().", sev="critical", kind="removal", cat="removal", applies={"python": ">=3.8"})
P("REMOVED-BASE64-ENCODESTRING", "base64.encodestring/decodestring", WN("3.9"), "encodestring", mcall("base64", "encodestring|decodestring"),
  "b = base64.encodestring(data)\n", "b = base64.encodebytes(data)\n", "Removed in 3.9; use encodebytes()/decodebytes().",
  sev="critical", kind="removal", cat="removal", applies={"python": ">=3.9"})
P("REMOVED-ISALIVE", "Thread.isAlive()", WN("3.9"), "isAlive",
  '((call function: (attribute attribute: (identifier) @match)) (#eq? @match "isAlive"))', "if t.isAlive():\n    pass\n", "if t.is_alive():\n    pass\n",
  "Thread.isAlive() was removed in 3.9; use is_alive().", sev="critical", kind="removal", cat="removal", applies={"python": ">=3.9"})
P("REMOVED-ETREE-GETCHILDREN", "Element.getchildren()/getiterator()", WN("3.9"), "getchildren",
  '((call function: (attribute attribute: (identifier) @match)) (#match? @match "^(getchildren|getiterator)$"))',
  "import xml.etree.ElementTree as ET\nfor c in root.getchildren():\n    pass\n", "import xml.etree.ElementTree as ET\nfor c in list(root):\n    pass\n",
  "Removed in 3.9; iterate the element (list(elem)) or use elem.iter().", sev="critical", kind="removal", cat="removal", applies={"python": ">=3.9"},
  filters=['file.has_re:(etree|ElementTree|minidom|lxml)'])
P("REMOVED-ARRAY-TOSTRING", "array.tostring()/fromstring()", WN("3.9"), "tostring",
  '((call function: (attribute attribute: (identifier) @match)) (#match? @match "^(tostring|fromstring)$"))',
  "import array\nb = arr.tostring()\n", "import array\nb = arr.tobytes()\n", "array.tostring()/fromstring() were removed in 3.9; use tobytes()/frombytes().",
  sev="critical", kind="removal", cat="removal", applies={"python": ">=3.9"}, filters=["file.has_re:import array|from array import"])
P("REMOVED-INSPECT-GETARGSPEC", "inspect.getargspec()", WN("3.11"), "getargspec", mcall("inspect", "getargspec|formatargspec"),
  "spec = inspect.getargspec(fn)\n", "sig = inspect.signature(fn)\n", "Removed in 3.11; use inspect.signature() or getfullargspec().",
  sev="critical", kind="removal", cat="removal", applies={"python": ">=3.11"})
P("REMOVED-ASYNCIO-LOOP-PARAM", "loop= argument to asyncio high-level APIs", WN("3.10"), "loop parameter",
  kwarg("^asyncio\\\\.(sleep|gather|wait|wait_for|shield|as_completed|open_connection|start_server|Queue|Lock|Event|Semaphore|BoundedSemaphore|Condition|create_subprocess_exec|create_subprocess_shell)$", "loop", "(_)"),
  "await asyncio.sleep(1, loop=loop)\n", "await asyncio.sleep(1)\n", "The loop parameter was removed from these APIs in 3.10.",
  sev="critical", kind="removal", cat="removal", applies={"python": ">=3.10"})
P("REMOVED-AST-NUM", "ast.Num/Str/Bytes/NameConstant/Ellipsis", WN("3.14"), "have emitted deprecation warnings since Python 3.12: Bytes Ellipsis NameConstant Num Str",
  '((attribute object: (identifier) @o attribute: (identifier) @match) (#eq? @o "ast") (#match? @match "^(Num|Str|Bytes|NameConstant|Ellipsis)$"))',
  "if isinstance(node, ast.Num):\n    pass\n", "if isinstance(node, ast.Constant):\n    pass\n",
  "These node classes were removed in 3.14; use ast.Constant.", sev="critical", kind="removal", cat="removal", applies={"python": ">=3.14"})
P("REMOVED-PKGUTIL-FIND-LOADER", "pkgutil.find_loader()/get_loader()", WN("3.14"), "find_loader", mcall("pkgutil", "find_loader|get_loader"),
  "l = pkgutil.find_loader('m')\n", "spec = importlib.util.find_spec('m')\n", "Removed in 3.14; use importlib.util.find_spec().",
  sev="critical", kind="removal", cat="removal", applies={"python": ">=3.14"})
P("REMOVED-UNITTEST-MAKESUITE", "unittest.makeSuite/findTestCases/getTestCaseNames", WN("3.13"), "makeSuite",
  mcall("unittest", "makeSuite|findTestCases|getTestCaseNames"), "s = unittest.makeSuite(T)\n", "s = unittest.TestLoader().loadTestsFromTestCase(T)\n",
  "Removed in 3.13; use TestLoader methods.", sev="critical", kind="removal", cat="removal", applies={"python": ">=3.13"})
P("REMOVED-LOCALE-RESETLOCALE", "locale.resetlocale()", WN("3.13"), "resetlocale", mcall("locale", "resetlocale"),
  "locale.resetlocale()\n", "locale.setlocale(locale.LC_ALL, '')\n", "Removed in 3.13; use setlocale(LC_ALL, '').",
  sev="critical", kind="removal", cat="removal", applies={"python": ">=3.13"})
P("REMOVED-TYPING-IO-RE", "typing.io / typing.re namespaces", WN("3.13"), "typing.io", imports("^typing\\\\.(io|re)$"),
  "from typing.io import IO\n", "from typing import IO\n", "typing.io and typing.re were removed in 3.13.",
  sev="critical", kind="removal", cat="removal", applies={"python": ">=3.13"})
P("DEPRECATED-UTCNOW", "datetime.utcnow()/utcfromtimestamp()", WN("3.12"), "utcnow",
  '((call function: (attribute attribute: (identifier) @match)) (#match? @match "^(utcnow|utcfromtimestamp)$"))',
  "import datetime\nnow = datetime.datetime.utcnow()\n", "import datetime\nnow = datetime.datetime.now(datetime.UTC)\n",
  "Deprecated in 3.12: they return naive datetimes that are easily mistaken for local time; use now(tz=UTC)/fromtimestamp(ts, tz=UTC).",
  sev="major", kind="deprecation", cat="deprecation", applies={"python": ">=3.12"}, filters=["file.has_re:datetime"])
P("DEPRECATED-GETDEFAULTLOCALE", "locale.getdefaultlocale()", WN("3.11"), "getdefaultlocale", mcall("locale", "getdefaultlocale"),
  "lang, enc = locale.getdefaultlocale()\n", "lang, enc = locale.getlocale()\n",
  "Deprecated in 3.11 and scheduled for removal in 3.15; use getlocale()/getpreferredencoding(False)/getencoding().",
  sev="major", kind="deprecation", cat="deprecation", applies={"python": ">=3.11"})
P("DEPRECATED-SRE-MODULES", "sre_compile / sre_constants / sre_parse", WN("3.11"), "sre_compile", imports("^(sre_compile|sre_constants|sre_parse)$"),
  "import sre_parse\n", "import re\n", "These internal modules are deprecated since 3.11.", sev="minor", kind="deprecation", cat="deprecation",
  applies={"python": ">=3.11"})
P("DEPRECATED-GET-EVENT-LOOP", "asyncio.get_event_loop() at module level / outside a coroutine", WN("3.12"), "get_event_loop",
  mcall("asyncio", "get_event_loop"), "loop = asyncio.get_event_loop()\nloop.run_until_complete(main())\n", "asyncio.run(main())\n",
  "Calling get_event_loop() with no running loop is deprecated (3.12 warns; 3.14 raises RuntimeError); use asyncio.run() or get_running_loop().",
  sev="major", kind="deprecation", cat="deprecation", applies={"python": ">=3.12"},
  mode="ai-confirm", ai="Is asyncio.get_event_loop() called where no event loop is running (module level, sync code), rather than inside a coroutine?")
P("DEPRECATED-EVENT-LOOP-POLICY", "asyncio event-loop policy API", WN("3.14"), "set_event_loop_policy",
  mcall("asyncio", "set_event_loop_policy|get_event_loop_policy"), "asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())\nasyncio.run(main())\n",
  "asyncio.run(main(), loop_factory=uvloop.new_event_loop)\n", "The policy system is deprecated in 3.14 (removal in 3.16); pass loop_factory to asyncio.run/Runner.",
  sev="minor", kind="deprecation", cat="deprecation", applies={"python": ">=3.14"})
P("DEPRECATED-PKG-RESOURCES", "pkg_resources", "https://setuptools.pypa.io/en/latest/deprecated/pkg_resources.html", "Distribution metadata & entry points: use importlib.metadata",
  imports("^pkg_resources$"), "import pkg_resources\nv = pkg_resources.get_distribution('x').version\n",
  "from importlib.metadata import version\nv = version('x')\n", "pkg_resources is deprecated; use importlib.metadata / importlib.resources.",
  sev="major", kind="deprecation", cat="deprecation", doc="setuptools: Package Discovery and Resource Access using pkg_resources", docv="setuptools (2026)")
P("FINALLY-JUMP", "return/break/continue inside finally", WN("3.14"), "PEP 765",
  '(finally_clause (block [(return_statement) (break_statement) (continue_statement)] @match))',
  "def f():\n    try:\n        return g()\n    finally:\n        return None\n", "def f():\n    try:\n        return g()\n    finally:\n        cleanup()\n",
  "A jump in finally silently swallows any in-flight exception; 3.14 emits a SyntaxWarning (PEP 765).", sev="major", cat="correctness")

# ------------------------------------------------------------------ security (stdlib docs + bandit/ruff S rules)
P("PICKLE-LOADS", "Unpickling data", LIB("pickle"), "The pickle module is not secure", mcall("pickle|cPickle|dill|_pickle", "load|loads|Unpickler"),
  "obj = pickle.loads(body)\n", "obj = json.loads(body)\n", "Unpickling attacker-controlled data executes arbitrary code; use JSON or sign the payload (hmac).",
  sev="critical", kind="security", cat="security", mode="ai-confirm", ai="Can the pickled data come from an untrusted source (network, user upload, shared cache)?",
  filters=[r"node.lacks_re:\bdumps\("], xref=["ruff:S301", "bandit:B301"],
  fp=["copy = pickle.loads(pickle.dumps(obj))\n"])
P("MARSHAL-LOADS", "marshal.load(s) on external data", LIB("marshal"), "not intended to be secure", mcall("marshal", "load|loads"),
  "code = marshal.loads(blob)\n", "data = json.loads(blob)\n", "marshal is not secure against malicious data.", sev="major", kind="security", cat="security")
P("SHELVE-UNTRUSTED", "shelve.open on a possibly untrusted file", LIB("shelve"), "insecure to load a shelf from an untrusted source", mcall("shelve", "open"),
  "db = shelve.open(upload_path)\n", "db = sqlite3.connect(upload_path)\n", "shelve is pickle-backed.", sev="major", kind="security", cat="security",
  mode="ai-confirm", ai="Can the shelf file be supplied or modified by an untrusted party?")
P("EVAL", "eval()/exec() on dynamic input", RUFF("suspicious-eval-usage"), rn("Checks for uses of the builtin `eval()` function."),
  '((call function: (identifier) @match arguments: (argument_list . [(identifier) (attribute) (call) (binary_operator) (subscript)])) (#match? @match "^(eval|exec)$"))',
  "result = eval(expr)\n", "result = ast.literal_eval(expr)\n", "eval/exec run arbitrary code; use ast.literal_eval or a parser.",
  sev="critical", kind="security", cat="security", docv="Ruff (2026)", mode="ai-confirm", ai="Can the evaluated string be influenced by user/external input?",
  xref=["ruff:S307", "ruff:S102", "bandit:B307", "bandit:B102"])
P("SUBPROCESS-SHELL", "subprocess with shell=True", LIB("subprocess"), "Unlike some other popen functions",
  kwarg("^subprocess\\\\.(run|call|check_call|check_output|Popen|getoutput)$", "shell", "(true)"),
  "subprocess.run(f\"convert {name} out.png\", shell=True)\n", "subprocess.run([\"convert\", name, \"out.png\"])\n",
  "shell=True passes the string to /bin/sh; any interpolated input becomes command injection. Pass an argument list.",
  sev="major", kind="security", cat="security")
P("OS-SYSTEM", "os.system()/os.popen()", LIB("os"), "The subprocess module provides more powerful facilities", mcall("os", "system|popen"),
  "os.system('rm -rf ' + path)\n", "subprocess.run(['rm', '-rf', path], check=True)\n",
  "os.system/os.popen run through the shell; prefer subprocess with an argument list.", sev="major", kind="security", cat="security")
P("RANDOM-FOR-SECURITY", "random module used for tokens/secrets", LIB("random"), "should not be used for security purposes",
  '((assignment left: (identifier) @n right: (call function: (attribute object: (identifier) @o attribute: (identifier) @a)) @match) (#match? @n "(?i)(token|secret|password|passwd|nonce|salt|otp|api_?key|session)") (#eq? @o "random") (#match? @a "^(random|randint|choice|choices|getrandbits|randrange|sample)$"))',
  "token = random.getrandbits(128)\n", "token = secrets.token_hex(16)\n", "random is a deterministic PRNG; use the secrets module.",
  sev="major", kind="security", cat="security")
P("TEMPFILE-MKTEMP", "tempfile.mktemp()", LIB("tempfile"), "Use of this function may introduce a security hole", mcall("tempfile", "mktemp"),
  "path = tempfile.mktemp()\n", "fd, path = tempfile.mkstemp()\n", "mktemp is racy (TOCTOU); use mkstemp/NamedTemporaryFile.", sev="major", kind="security", cat="security")
P("XML-UNTRUSTED", "stdlib XML parser on untrusted data", LIB("xml"), "may be vulnerable to the",
  '((call function: (attribute attribute: (identifier) @a) @f) @match (#match? @f "^(ET|ElementTree|etree|xml\\\\.etree\\\\.ElementTree|minidom|xml\\\\.dom\\\\.minidom|xml\\\\.sax|pulldom|expatbuilder)\\\\.") (#match? @a "^(parse|fromstring|XML|iterparse|parseString|XMLParser)$"))',
  "root = ET.fromstring(request.body)\n", "root = defusedxml.ElementTree.fromstring(request.body)\n",
  "Check the stdlib XML vulnerability table (entity expansion etc.) for the parser in use; prefer defusedxml for untrusted input.",
  sev="major", kind="security", cat="security", mode="ai-confirm", ai="Is the XML untrusted (request body, upload, third-party feed)?")
P("SSL-NO-VERIFY", "TLS verification disabled", LIB("ssl"), "CERT_NONE",
  '((attribute object: (identifier) @o attribute: (identifier) @match) (#eq? @o "ssl") (#match? @match "^(CERT_NONE|_create_unverified_context)$"))\n((assignment left: (attribute attribute: (identifier) @match) right: (false)) (#eq? @match "check_hostname"))',
  "ctx.check_hostname = False\nctx.verify_mode = ssl.CERT_NONE\n", "ctx = ssl.create_default_context()\n",
  "Disabling certificate/hostname verification enables MITM; trust the right CA instead.", sev="critical", kind="security", cat="security")
P("REQUESTS-VERIFY-FALSE", "requests/httpx with verify=False", "https://requests.readthedocs.io/en/latest/user/advanced/", "Requests verifies SSL certificates for HTTPS requests",
  kwarg("^(requests|httpx|session|s|client)\\\\.(get|post|put|patch|delete|head|options|request|Client|AsyncClient)$", "verify", "(false)"),
  "r = requests.get(url, verify=False)\n", "r = requests.get(url, verify='/etc/ssl/corp-ca.pem')\n",
  "verify=False disables certificate checks.", sev="critical", kind="security", cat="security", docv="Requests 2.x")
P("REQUESTS-NO-TIMEOUT", "requests call without timeout", "https://requests.readthedocs.io/en/latest/user/quickstart/", "Nearly all production code should use this parameter",
  '((call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list) @args) @match (#eq? @o "requests") (#match? @a "^(get|post|put|patch|delete|head|options|request)$") (#not-match? @args "timeout\\\\s*="))',
  "r = requests.get(url)\n", "r = requests.get(url, timeout=10)\n", "Without a timeout a stalled server hangs the caller indefinitely.",
  sev="major", cat="reliability", docv="Requests 2.x")
P("SQL-STRING-FORMAT", "SQL built with string formatting", LIB("sqlite3"), "vulnerable to SQL injection attacks",
  '((call function: (attribute attribute: (identifier) @a) arguments: (argument_list . [(string (interpolation)) (binary_operator left: (string)) (call function: (attribute object: (string) attribute: (identifier) @fm))] @match)) (#match? @a "^(execute|executemany|executescript|raw|text)$"))',
  "cur.execute(f\"SELECT * FROM users WHERE name = '{name}'\")\n", "cur.execute(\"SELECT * FROM users WHERE name = ?\", (name,))\n",
  "Bind parameters instead of formatting values into SQL.", sev="critical", kind="security", cat="security")
P("HTTP-SERVER-PRODUCTION", "http.server used to serve an app", LIB("http.server"), "not recommended for production",
  '((call function: (attribute object: (identifier) @o attribute: (identifier) @match)) (#match? @o "^(http\\\\.server|server|socketserver)$") (#match? @match "^(HTTPServer|ThreadingHTTPServer)$"))',
  "srv = server.HTTPServer(('', 8000), Handler)\n", "uvicorn.run(app, host='127.0.0.1', port=8000)\n",
  "http.server implements only basic security checks; use a production server.", sev="minor", kind="security", cat="security",
  mode="ai-confirm", ai="Is this a production/network-exposed server rather than a dev/test helper?")
P("TARFILE-EXTRACTALL-NO-FILTER", "tarfile extractall without filter", LIB("tarfile"), "Never extract archives from untrusted sources without prior inspection",
  '((call function: (attribute attribute: (identifier) @a) arguments: (argument_list) @args) @match (#match? @a "^(extractall|extract)$") (#not-match? @args "filter\\\\s*="))',
  "import tarfile\nwith tarfile.open(p) as t:\n    t.extractall(dest)\n", "import tarfile\nwith tarfile.open(p) as t:\n    t.extractall(dest, filter='data')\n",
  "Without filter='data' members can escape dest (../, absolute paths, links). 3.12+ warns; 3.14 defaults to 'data'.",
  sev="major", kind="security", cat="security", applies={"python": ">=3.8"}, filters=["file.has_re:tarfile"])
P("ZIPFILE-EXTRACT-UNTRUSTED", "zipfile extractall on untrusted archives", LIB("zipfile"), "Never extract archives from untrusted sources without prior inspection",
  '((call function: (attribute attribute: (identifier) @a)) @match (#eq? @a "extractall"))', "import zipfile\nzipfile.ZipFile(upload).extractall(dest)\n",
  "import zipfile\nwith zipfile.ZipFile(upload) as z:\n    check_members(z)\n", "Validate members (size, count, paths) first: zip bombs and overwrite attacks.",
  sev="minor", kind="security", cat="security", filters=["file.has_re:zipfile", "file.lacks_re:tarfile"], mode="ai-confirm",
  ai="Is the archive untrusted and extracted without validating member names/sizes?")
P("ASSERT-FOR-SECURITY", "assert used for an access/security check", DOCS + "reference/simple_stmts.html", "when optimization is requested at compile time",
  '((assert_statement) @match (#match? @match "(?i)\\\\b(is_admin|is_staff|is_superuser|is_authenticated|authenticated|is_authorized|authorized|has_perms?|has_permission|permission_required|user_passes_test|check_permission|csrf_\\\\w+|is_owner)\\\\b"))',
  "def delete(user):\n    assert user.is_admin\n    do_delete()\n", "def delete(user):\n    if not user.is_admin:\n        raise PermissionError\n    do_delete()\n",
  "assert is stripped under -O; never use it to enforce security.", sev="major", kind="security", cat="security", docv="Python 3.14 Language Reference",
  xref=["bandit:B101", "ruff:S101"],
  fp=["assert orig_name.type == token.NAME, \"Invalid syntax\"\n", "assert is_rpar_token(parent.children[-1])\n"])
P("YAML-LOAD-UNSAFE", "yaml.load without SafeLoader", "https://pyyaml.org/wiki/PyYAMLDocumentation", "safe_load",
  '((call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list) @args) @match (#eq? @o "yaml") (#match? @a "^(load|load_all|unsafe_load|full_load)$") (#not-match? @args "Loader\\\\s*=\\\\s*(yaml\\\\.)?(Safe|CSafe)Loader"))',
  "cfg = yaml.load(f)\n", "cfg = yaml.safe_load(f)\n", "Non-safe loaders can construct arbitrary Python objects; use safe_load.",
  sev="critical", kind="security", cat="security", docv="PyYAML 6.x")
P("HASH-WEAK", "MD5/SHA-1 for security purposes", LIB("hashlib"), "usedforsecurity",
  '((call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list) @args) @match (#eq? @o "hashlib") (#match? @a "^(md5|sha1)$") (#not-match? @args "usedforsecurity\\\\s*=\\\\s*False"))',
  "h = hashlib.md5(data).hexdigest()\n", "h = hashlib.md5(data, usedforsecurity=False).hexdigest()\n",
  "MD5/SHA-1 are broken for security; use sha256+/scrypt, or mark non-security use with usedforsecurity=False (3.9+).",
  sev="major", kind="security", cat="security", mode="ai-confirm", precision="low", ai="Is this hash used for a security purpose (passwords, signatures, tokens, integrity against attackers)?",
  filters=["func.lacks_re:(?i)(session|cookie|token|passw|pwd|secret|nonce|otp|csrf|api_?key|salt|rememberme|credential|signature|hmac)"])
P("HASH-WEAK-SECURITY-CONTEXT", "MD5/SHA-1 in a function handling passwords, tokens or signatures", LIB("hashlib"), "usedforsecurity",
  '((call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list) @args) @match (#eq? @o "hashlib") (#match? @a "^(md5|sha1)$") (#not-match? @args "usedforsecurity\\\\s*=\\\\s*False"))',
  "h = hashlib.md5(password.encode()).hexdigest()\n", "h = hashlib.sha256(data).hexdigest()\n",
  "MD5/SHA-1 are broken for security and this function handles a password/token/signature value: use hashlib.scrypt / sha256+ (or a password hash).",
  sev="major", kind="security", cat="security", filters=["func.has_re:(?i)(session|cookie|token|passw|pwd|secret|nonce|otp|csrf|api_?key|salt|rememberme|credential|signature|hmac)"])
P("HMAC-COMPARE", "Secret compared with ==", LIB("hmac"), "compare_digest",
  '((comparison_operator (_) @l (_) @r) @match (#match? @match "==|!="))',
  "if signature == expected:\n    ok()\n", "if hmac.compare_digest(signature, expected):\n    ok()\n", "== leaks timing; use hmac.compare_digest.",
  sev="major", kind="security", cat="security", mode="ai-confirm", ai="Are secrets/MACs compared here (timing-sensitive), not public values?",
  # one side must be a MAC/digest value: a .digest()/.hexdigest() call or a name ending in sig/signature/digest/hmac/mac
  filters=[r"node.has_re:(?i)(\.(hex)?digest\(\)|\b\w*(sig|signature|digest|hmac|mac))\s*(\)\s*)?([!=]=|$)|[!=]=\s*\S*(\.(hex)?digest\(\)|\b\w*(sig|signature|digest|hmac|mac))\b",
           r"ancestor.lacks_re:assert_statement:.", r"node.lacks_re:\.type\b"],
  fp=["if token.type == TokenType.identifier:\n    pass\n", "assert record[\"token\"] == \"secret\"\n", "if x_token != fake_secret_token:\n    pass\n"])
P("BIND-ALL-INTERFACES", "Server bound to 0.0.0.0", RUFF("hardcoded-bind-all-interfaces"), rn("Checks for hardcoded bindings to all network interfaces"),
  '((string (string_content) @c) @match (#eq? @c "0.0.0.0"))', "app.run(host=\"0.0.0.0\")\n", "app.run(host=os.environ.get(\"HOST\", \"127.0.0.1\"))\n",
  "Binding to all interfaces exposes the service on every network.", sev="minor", kind="security", cat="security", docv="Ruff (2026)",
  mode="ai-confirm", ai="Is binding to all interfaces unintended (not a container entrypoint behind a network policy)?",
  # the literal is only a bind when it is used as an address: not a member of an all-string
  # deny/allow list, set or tuple, not an operand of a comparison or membership test, not inside
  # an assert or a mock call assertion (corpus 2026-10-10: starlette, fastapi tests)
  filters=[r"""parentkind.lacks_re:list|set|tuple:^[\[{(]\s*(?:[rbuRBU]?["'][^"']*["']\s*,\s*)*[rbuRBU]?["'][^"']*["']\s*,?\s*[\]})]$""",
           "ancestor.lacks_re:comparison_operator|assert_statement:.",
           r"ancestor.lacks_re:call:^[\w.]*\.assert_\w+\("],
  fp=["BLOCKED_HOSTS = (\"0.0.0.0\", \"127.0.0.1\", \"localhost\")\n",
      "if host in {\"0.0.0.0\", \"::\"}:\n    raise ValueError(\"refusing to expose the admin port\")\n",
      "if parsed.hostname == \"0.0.0.0\":\n    warn_public_bind()\n",
      "assert hosts == [\"localhost\", \"0.0.0.0\"]\n",
      "run_mock.assert_called_once_with(app, host=\"0.0.0.0\", port=8000)\n",
      "UNSAFE = [\"0.0.0.0\"]\n"])
P("HARDCODED-TMP", "Hard-coded /tmp path", RUFF("hardcoded-temp-file"), rn("Checks for the use of hardcoded temporary file or directory paths."),
  '((string (string_content) @match) (#match? @match "^/(tmp|var/tmp|dev/shm)/"))', "open(\"/tmp/report.csv\", \"w\")\n",
  "tempfile.NamedTemporaryFile(\"w\", suffix=\".csv\")\n", "Predictable temp paths enable symlink/race attacks; use tempfile.", sev="minor", kind="security",
  cat="security", docv="Ruff (2026)", mode="ai-confirm", precision="low",
  ai="Does the code create or write a file/directory at this predictable shared path (not just read or glob it, and not an overridable default)?",
  # reading/globbing a known path, or a default the environment overrides, is not the insecure-temp-file pattern
  filters=[r"ancestor.lacks_re:call:^(glob\.i?glob|os\.(environ\.get|getenv)|os\.path\.(exists|isfile|isdir)|Path\([^)]*\)\.(exists|glob)|[\w.]+\.(startswith|endswith))\(",
           # a path compared against or listed in a deny-list is a check, not a file creation
           "ancestor.lacks_re:comparison_operator|assert_statement:."],
  fp=['CACHE = os.environ.get("RULEGEN_CACHE", "/tmp/rulegen-cache")\n',
      'if out.startswith("/tmp/"):\n    raise ValueError("refusing a shared temp dir")\n',
      'if path in ("/tmp/x.lock", "/var/tmp/x.lock"):\n    cleanup()\n',
      "files = sorted(glob.glob('/tmp/src/notes/*.asciidoc'))\n"])
P("FLASK-DEBUG", "Flask app.run(debug=True)", RUFF("flask-debug-true"), rn("Checks for uses of `debug=True` in Flask."),
  kwarg("^(app|application)\\\\.run$", "debug", "(true)"), "app.run(debug=True)\n", "app.run(debug=os.environ.get('FLASK_DEBUG') == '1')\n",
  "The Werkzeug debugger allows arbitrary code execution.", sev="critical", kind="security", cat="security", docv="Ruff (2026)",
  filters=[r"file.lacks_re:(?m)^\s*(app|application)\s*=\s*([^\sFc(]|F[^l]|c[^r])"])  # app rebound to something that is not Flask(...) / create_app()
P("JINJA-AUTOESCAPE-FALSE", "Jinja2 Environment without autoescape", RUFF("jinja2-autoescape-false"), rn("Checks for `jinja2` templates that use `autoescape=False`."),
  '((call function: (_) @f arguments: (argument_list) @args) @match (#match? @f "^(jinja2\\\\.)?Environment$") (#not-match? @args "autoescape\\\\s*=\\\\s*(True|[A-Za-z0-9_.]*select_autoescape)"))',
  "env = jinja2.Environment(loader=loader)\n", "env = jinja2.Environment(loader=loader, autoescape=jinja2.select_autoescape())\n",
  "Without autoescape, rendering user data into HTML is XSS.", sev="major", kind="security", cat="security", docv="Ruff (2026)")
P("DEBUGGER-LEFT", "Debugger breakpoint left in code", RUFF("debugger"), rn("Checks for the presence of debugger calls and imports."),
  '((call function: (identifier) @match) (#eq? @match "breakpoint"))\n((call function: (attribute object: (identifier) @o attribute: (identifier) @match)) (#match? @o "^(pdb|ipdb|pudb)$") (#eq? @match "set_trace"))',
  "def f():\n    breakpoint()\n    return 1\n", "def f():\n    return 1\n", "Remove debugger hooks before committing.", sev="major", cat="correctness", docv="Ruff (2026)")
secret_rules(P, '(string_content)', lambda k, v: f'{k} = "{v}"\n')
P("HARDCODED-PASSWORD", "Hard-coded password/secret assigned to a variable", RUFF("hardcoded-password-string"), rn("Checks for potential uses of hardcoded passwords in strings."),
  '((assignment left: [(identifier) (attribute attribute: (identifier))] @n right: (string (string_content) @match)) (#match? @n "(?i)(^|[._])(password|passwd|pwd|secret|client_secret|api_?key|access_?token|auth_?token|private_?key|secret_?key)$") (#not-match? @match "' + PLACEHOLDER_RE + '"))',
  'DB_PASSWORD = "s3cr3t-Pa55"\n', 'DB_PASSWORD = os.environ["DB_PASSWORD"]\n', "Load secrets from the environment or a secret manager.",
  sev="critical", kind="security", cat="security", docv="Ruff (2026)")

# ------------------------------------------------------------------ correctness / idioms (Ruff docs)
# Ruff rule codes (docs.astral.sh/ruff/rules) so `# noqa: CODE` suppresses the crev equivalent.
RUFF_CODES = {
    "mutable-argument-default": "B006", "bare-except": "E722", "try-except-pass": "S110", "none-comparison": "E711",
    "true-false-comparison": "E712", "is-literal": "F632", "type-comparison": "E721", "f-string-missing-placeholders": "F541",
    "assert-tuple": "F631", "raise-not-implemented": "F901", "get-attr-with-constant": "B009",
    "zip-without-explicit-strict": "B905", "call-datetime-now-without-tzinfo": "DTZ005", "unspecified-encoding": "PLW1514",
    "undefined-local-with-import-star": "F403", "function-uses-loop-variable": "B023", "strip-with-multi-characters": "B005",
    "assert-false": "B011", "except-with-empty-tuple": "B029", "raise-without-from-inside-except": "B904",
    "cached-instance-method": "B019", "logging-f-string": "G004", "logging-warn": "G010", "in-dict-keys": "SIM118",
    "useless-comparison": "B015", "unreliable-callable-check": "B004",
}
# flake8/pycodestyle names for the same checks (bare-except is also pylint's name).
PYLINT_EQ = {"bare-except": "bare-except", "unspecified-encoding": "unspecified-encoding", "logging-f-string": "logging-fstring-interpolation",
             "none-comparison": "singleton-comparison", "true-false-comparison": "singleton-comparison", "raise-without-from-inside-except": "raise-missing-from"}


def ruff(id, title, name, needle, query, bad, good, msg, sev="minor", cat="correctness", **kw):
    xr = list(kw.pop("xref", None) or [])
    if name in RUFF_CODES:
        xr += [f"ruff:{RUFF_CODES[name]}", f"flake8:{RUFF_CODES[name]}"]
    if name in PYLINT_EQ:
        xr.append(f"pylint:{PYLINT_EQ[name]}")
    P(id, title, RUFF(name), rn(needle), query, bad, good, msg, sev=sev, cat=cat, docv="Ruff (2026)", xref=xr or None, **kw)


ruff("MUTABLE-DEFAULT", "Mutable default argument", "mutable-argument-default", "Checks for uses of mutable objects as function argument defaults.",
     '([(default_parameter value: [(list) (dictionary) (set)] @match) (typed_default_parameter value: [(list) (dictionary) (set)] @match)])',
     "def add(x, acc=[]):\n    acc.append(x)\n    return acc\n", "def add(x, acc=None):\n    acc = [] if acc is None else acc\n    acc.append(x)\n    return acc\n",
     "Defaults are evaluated once and shared between calls.", sev="major",
     # FastAPI parameter declarations: the default is a pydantic field default, copied per request (FastAPI docs: Query parameter list).
     filters=[r"ancestor.lacks_re:typed_default_parameter:\b(Query|Header|Cookie|Form|Body|Path|File)\("],
     fp=["async def read_items(q: Annotated[list[str], Query()] = [\"foo\"]):\n    return q\n"])
ruff("BARE-EXCEPT", "Bare except:", "bare-except", "Checks for bare `except` catches", '((except_clause . (block)) @match)',
     "try:\n    f()\nexcept:\n    log()\n", "try:\n    f()\nexcept Exception:\n    log()\n", "Bare except also catches KeyboardInterrupt/SystemExit.", sev="major")
ruff("TRY-EXCEPT-PASS", "Exception silently swallowed", "try-except-pass", "Checks for uses of the try - except - pass pattern",
     '(except_clause (block . (pass_statement) .) @match)', "try:\n    f()\nexcept Exception:\n    pass\n",
     "try:\n    f()\nexcept Exception:\n    log.debug('ignored', exc_info=True)\n", "Silently ignoring errors hides bugs; log or use contextlib.suppress explicitly.",
     # Ruff S110 default (check-typed-exception = false): only bare except, Exception and BaseException.
     filters=[r"parentkind.has_re:except_clause:^except\s*(\(?\s*(builtins\.)?(Exception|BaseException)\s*\)?\s*(as\s+\w+\s*)?)?:"],
     fp=["try:\n    import ujson\nexcept ImportError:\n    pass\n"])
ruff("NONE-COMPARISON", "== None / != None", "none-comparison", "Checks for comparisons to `None` which are not using the `is` operator.",
     '((comparison_operator (_) operators: ["==" "!="] (none)) @match)', "if x == None:\n    pass\n", "if x is None:\n    pass\n",
     "Use `is None`; == can be overridden.")
ruff("BOOL-COMPARISON", "== True / == False", "true-false-comparison", "Checks for equality comparisons to boolean literals.",
     '((comparison_operator (_) operators: ["==" "!="] [(true) (false)]) @match)', "if flag == True:\n    pass\n", "if flag:\n    pass\n",
     "Compare truthiness directly (or `is True` if identity matters).")
ruff("IS-LITERAL", "`is` comparison with a literal", "is-literal", "Checks for `is` and `is not` comparisons against literals",
     '((comparison_operator (_) operators: ["is" "is not"] [(string) (integer) (float) (tuple) (list) (dictionary)]) @match)', "if x is \"a\":\n    pass\n",
     "if x == \"a\":\n    pass\n", "Identity of literals is an implementation detail (SyntaxWarning since 3.8).", sev="major")
ruff("TYPE-COMPARISON", "type(x) == T", "type-comparison", "Checks for object type comparisons using `==` and other comparison operators.",
     '((comparison_operator (call function: (identifier) @t) operators: ["==" "!="]) @match (#eq? @t "type"))', "if type(x) == int:\n    pass\n",
     "if isinstance(x, int):\n    pass\n", "Use isinstance() (or `is` for exact type checks).")
ruff("FSTRING-NO-PLACEHOLDER", "f-string without placeholders", "f-string-missing-placeholders", "Checks for f-strings that do not contain any placeholder expressions.",
     '((string (string_start) @s) @match (#match? @s "^[rRbB]?[fF]") (#not-match? @match "\\\\{[^{]"))', "msg = f\"done\"\n", "msg = \"done\"\n",
     "The f prefix is unnecessary — or a placeholder was forgotten.",
     # Implicit concatenation is one f-string (one JoinedStr in the AST): F541 only fires when no part has a placeholder.
     filters=[r"parentkind.lacks_re:concatenated_string:\{[^{]"],
     fp=["msg = (f\"Timed out after \"\n       f\"{secs}s\")\n"])
ruff("ASSERT-TUPLE", "assert on a tuple (always true)", "assert-tuple", "Checks for `assert` statements that use non-empty tuples as test conditions.",
     '(assert_statement . (tuple) @match)', "assert (x > 0, \"positive\")\n", "assert x > 0, \"positive\"\n", "A non-empty tuple is always truthy.", sev="major")
ruff("RAISE-NOTIMPLEMENTED", "raise NotImplemented", "raise-not-implemented", "Checks for `raise` statements that raise `NotImplemented`.",
     '((raise_statement [(identifier) @match (call function: (identifier) @match)]) (#eq? @match "NotImplemented"))', "def f():\n    raise NotImplemented\n",
     "def f():\n    raise NotImplementedError\n", "NotImplemented is a constant, not an exception (TypeError at runtime).", sev="major")
ruff("GETATTR-CONSTANT", "getattr/setattr with a constant name", "get-attr-with-constant", "Checks for uses of `getattr` that take a constant attribute value",
     '((call function: (identifier) @f arguments: (argument_list . (_) . (string (string_content) @n) @s .)) @match (#match? @f "^getattr$") (#match? @n "^[A-Za-z_][A-Za-z0-9_]*$"))',
     "v = getattr(obj, \"name\")\n", "v = obj.name\n", "Use plain attribute access.",
     filters=[r"cap.lacks_re:s:^[rRbBuU]*[fF]|\{", r"cap.lacks_re:n:^_[A-Za-z0-9]+__[A-Za-z0-9_]"],
     fp=["f = getattr(self, f\"parse_{kind}\")\n", "class T:\n    def t(self, x):\n        return getattr(x, \"_Thread__stopped\")\n"])
ruff("ZIP-WITHOUT-STRICT", "zip() without strict=", "zip-without-explicit-strict", "Checks for `zip` calls without an explicit `strict` parameter.",
     '((call function: (identifier) @f arguments: (argument_list (_) (_)) @args) @match (#eq? @f "zip") (#not-match? @args "strict\\\\s*="))',
     "for a, b in zip(xs, ys):\n    pass\n", "for a, b in zip(xs, ys, strict=True):\n    pass\n", "zip silently truncates to the shortest input.",
     applies={"python": ">=3.10"}, mode="ai-confirm", ai="Must the iterables have equal length (truncation would be a bug)?")
ruff("DATETIME-NOW-NAIVE", "datetime.now() without tz", "call-datetime-now-without-tzinfo", "Checks for usages of `datetime.datetime.now()` that do not specify a timezone.",
     '((call function: (attribute object: (_) @o attribute: (identifier) @a) arguments: (argument_list) @args) @match (#match? @o "^(datetime|datetime\\\\.datetime|dt)$") (#eq? @a "now") (#eq? @args "()"))',
     "ts = datetime.now()\n", "ts = datetime.now(timezone.utc)\n", "Naive datetimes are ambiguous across zones/DST.",
     filters=["file.has_re:datetime"])
ruff("OPEN-NO-ENCODING", "open() in text mode without encoding", "unspecified-encoding", "Checks for uses of `open` and related calls without an explicit `encoding` argument.",
     '((call function: (identifier) @f arguments: (argument_list) @args) @match (#eq? @f "open") (#not-match? @args "encoding\\\\s*=|[\'\\"][rwax+]*b[rwax+]*[\'\\"]"))',
     "with open(path) as f:\n    data = f.read()\n", "with open(path, encoding=\"utf-8\") as f:\n    data = f.read()\n",
     "The default is locale-dependent (PEP 597); Python 3.15 switches to UTF-8 mode by default. Be explicit.",
     applies={"python": "<3.15"},  # PEP 686: UTF-8 mode is the default from 3.15
     # fixture triage (ruff PLW1514): encoding passed positionally (4th arg), forwarded *args /
     # **kwargs, and a mode computed at runtime cannot be judged statically
     filters=[r"cap.lacks_re:args:\*|^\(\s*[^,()]+,\s*[^,()]+,\s*[^,()]+,\s*[^,()]+|mode\s*=\s*[A-Za-z_]|^\(\s*[^,()]+,\s*[A-Za-z_][\w.\[\]]*\s*[,)]"],
     fp=[{"note": "encoding as the 4th positional argument", "code": "with open(path, \"r\", -1, \"utf-8\") as f:\n    data = f.read()\n"},
         {"note": "arguments forwarded", "code": "def opener(*args, **kwargs):\n    return open(*args, **kwargs)\n"},
         {"note": "mode decided at runtime", "code": "def load(path, mode):\n    return open(path, mode=mode)\n"}])
ruff("IMPORT-STAR", "from module import *", "undefined-local-with-import-star", "Checks for the use of wildcard imports.",
     '(import_from_statement (wildcard_import) @match)', "from os.path import *\n", "from os.path import join, exists\n",
     "Star imports hide where names come from and break static analysis.")
ruff("LOOP-VAR-CLOSURE", "Closure captures loop variable", "function-uses-loop-variable", "Checks for function definitions that use a loop variable.",
     '(for_statement left: (identifier) @v body: (block (expression_statement (call arguments: (argument_list (lambda !parameters body: (identifier) @b)))) @match) (#eq? @v @b))',
     "fs = []\nfor i in range(3):\n    fs.append(lambda: i)\n", "fs = []\nfor i in range(3):\n    fs.append(lambda i=i: i)\n",
     "Late binding: every closure sees the final value.", sev="major", mode="ai-confirm",
     ai="Does the lambda run after the loop iteration ends (so it observes a later value of the loop variable)?")
ruff("STRIP-MULTICHAR", "str.strip() with a multi-character string", "strip-with-multi-characters", "Checks for uses of multi-character strings in `.strip()`, `.lstrip()`, and `.rstrip()` calls.",
     '((call function: (attribute attribute: (identifier) @a) arguments: (argument_list . (string (string_content) @s) .)) @match (#match? @a "^(strip|lstrip|rstrip)$") (#match? @s "^[A-Za-z0-9_.]{3,}$"))',
     "name = fn.rstrip(\".txt\")\n", "name = fn.removesuffix(\".txt\")\n", "strip removes a character set, not a prefix/suffix; use removeprefix/removesuffix (3.9+).", sev="major")
ruff("ASSERT-FALSE", "assert False", "assert-false", "Checks for uses of `assert False`.", '(assert_statement . (false) @match)',
     "def f():\n    assert False, \"unreachable\"\n", "def f():\n    raise AssertionError(\"unreachable\")\n", "assert statements are removed under -O.")
ruff("EXCEPT-EMPTY-TUPLE", "except () catches nothing", "except-with-empty-tuple", "Checks for exception handlers that catch an empty tuple.",
     '((except_clause (tuple) @match) (#eq? @match "()"))', "try:\n    f()\nexcept ():\n    pass\n", "try:\n    f()\nexcept OSError:\n    pass\n",
     "An empty tuple matches no exception.", sev="major")
ruff("RAISE-WITHOUT-FROM", "Re-raise inside except without from", "raise-without-from-inside-except", "Checks for `raise` statements in exception handlers that lack a `from` clause.",
     '(except_clause (block (raise_statement (call) .) @match))', "try:\n    f()\nexcept KeyError as e:\n    raise ValueError('missing')\n",
     "try:\n    f()\nexcept KeyError as e:\n    raise ValueError('missing') from e\n", "Chain with `from err` (or `from None`) so the cause is clear.",
     mode="ai-confirm", ai="Is the raise in the except body (not a nested function) and missing a from clause?")
ruff("CACHED-METHOD", "functools.cache/lru_cache on a method", "cached-instance-method", "Checks for uses of the `functools.lru_cache` and `functools.cache` decorators on methods.",
     '(class_definition body: (block (decorated_definition (decorator) @match definition: (function_definition parameters: (parameters . (identifier) @s))) (#match? @match "^@(functools\\\\.)?(lru_cache|cache)\\\\b") (#eq? @s "self")))',
     "class A:\n    @lru_cache\n    def get(self, k):\n        return k\n", "class A:\n    def get(self, k):\n        return k\n",
     "The cache holds a reference to self, leaking instances.", sev="major")
ruff("LOGGING-FSTRING", "f-string passed to a logging call", "logging-f-string", "Checks for uses of f-strings to format logging messages.",
     '((call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list . (string (interpolation)) @match)) (#match? @o "^(log|logger|logging|LOG|LOGGER|_log|_logger)$") (#match? @a "^(debug|info|warning|error|exception|critical|log)$"))',
     "logger.info(f\"user {uid} logged in\")\n", "logger.info(\"user %s logged in\", uid)\n", "Formatting happens even when the level is disabled; pass args lazily.", cat="performance")
ruff("LOGGING-WARN", "logger.warn()", "logging-warn", "Checks for uses of `logging.warn` and `logging.Logger.warn`.",
     mcall("log|logger|logging|LOG|LOGGER|_log|_logger", "warn"), "logger.warn(\"x\")\n", "logger.warning(\"x\")\n",
     "warn() is a deprecated alias of warning() (logging.warn was removed in 3.13).", kind="deprecation", cat="deprecation")
ruff("IN-DICT-KEYS", "key in dict.keys()", "in-dict-keys", "Checks for key-existence checks against `dict.keys()` calls.",
     '((comparison_operator (_) operators: ["in" "not in"] (call function: (attribute attribute: (identifier) @k) arguments: (argument_list) @args) @match) (#eq? @k "keys") (#eq? @args "()"))',
     "if k in d.keys():\n    pass\n", "if k in d:\n    pass\n", "Test membership on the dict directly.", sev="info", cat="style",
     filters=[r"ancestor.lacks_re:function_definition:^(async\s+)?def\s+__contains__\b"])  # `in self` there would recurse
ruff("USELESS-COMPARISON", "Comparison result unused", "useless-comparison", "Checks for useless comparisons.",
     '(expression_statement (comparison_operator) @match)', "def f(x):\n    x == 1\n", "def f(x):\n    assert x == 1\n",
     "The comparison has no effect (probably meant = or assert).", sev="major")
ruff("CALLABLE-HASATTR", "hasattr(x, '__call__')", "unreliable-callable-check", "Checks for uses of `hasattr` to test if an object is callable",
     '((call function: (identifier) @f arguments: (argument_list (_) (string (string_content) @s))) @match (#eq? @f "hasattr") (#eq? @s "__call__"))',
     "if hasattr(f, \"__call__\"):\n    pass\n", "if callable(f):\n    pass\n", "Use callable().")

# ------------------------------------------------------------------ modernization (pyupgrade via Ruff, version-gated)
def up(id, title, name, needle, query, bad, good, msg, ver=None, sev="info", **kw):
    url = name if name.startswith("http") else RUFF(name)
    P(id, title, url, rn(needle) if url != name else needle, query, bad, good, msg, sev=sev, kind="modernization", cat="modernization",
      applies={"python": f">={ver}"} if ver else None, docv="Ruff (2026)" if url != name else "Python 3.14", **kw)


up("SUPER-ARGS", "super(Class, self)", "super-call-with-parameters", "Checks for `super` calls that pass redundant arguments.",
   '((call function: (identifier) @f arguments: (argument_list (identifier) (identifier) @s)) @match (#eq? @f "super") (#match? @s "^(self|cls)$"))',
   "class A(B):\n    def m(self):\n        super(A, self).m()\n", "class A(B):\n    def m(self):\n        super().m()\n", "Use zero-argument super().")
up("OBJECT-INHERITANCE", "class X(object)", "useless-object-inheritance", "Checks for classes that inherit from `object`.",
   '((class_definition superclasses: (argument_list (identifier) @match)) (#eq? @match "object"))', "class A(object):\n    pass\n", "class A:\n    pass\n",
   "All classes are new-style in Python 3.")
up("UNICODE-PREFIX", "u'' string prefix", "unicode-kind-prefix", "Checks for uses of the Unicode kind prefix (`u`) in strings.",
   '((string (string_start) @match) (#match? @match "^[uU]"))', "s = u\"x\"\n", "s = \"x\"\n", "Strings are Unicode in Python 3.")
up("FUTURE-IMPORT", "Obsolete __future__ import", "unnecessary-future-import", "Checks for unnecessary `__future__` imports.",
   '((future_import_statement name: (dotted_name) @match) (#match? @match "^(nested_scopes|generators|division|absolute_import|with_statement|print_function|unicode_literals|generator_stop)$"))',
   "from __future__ import print_function\n", "from __future__ import annotations\n", "These features are mandatory in Python 3.")
up("OS-ERROR-ALIAS", "IOError/EnvironmentError/socket.error", "os-error-alias", "Checks for uses of exceptions that alias `OSError`.",
   '((except_clause [(identifier) @match (attribute) @match]) (#match? @match "^(IOError|EnvironmentError|WindowsError|socket\\\\.error|select\\\\.error|mmap\\\\.error)$"))',
   "try:\n    f()\nexcept IOError:\n    pass\n", "try:\n    f()\nexcept OSError:\n    pass\n", "These are aliases of OSError since 3.3.")
up("YIELD-FROM", "for x in y: yield x", "yield-in-for-loop", "Checks for `for` loops that can be replaced with `yield from` expressions.",
   '((for_statement left: (identifier) @a body: (block . (expression_statement (yield (identifier) @b)) .)) @match (#eq? @a @b))',
   "def g(xs):\n    for x in xs:\n        yield x\n", "def g(xs):\n    yield from xs\n", "Use yield from.")
up("PEP585-GENERICS", "typing.List/Dict/Set/Tuple/Type", "non-pep585-annotation", "Checks for the use of generics that can be replaced with standard library variants based on PEP 585.",
   from_import("typing", "List|Dict|Set|FrozenSet|Tuple|Type|Deque|DefaultDict|OrderedDict|Counter|ChainMap"), "from typing import List\nxs: List[int] = []\n",
   "xs: list[int] = []\n", "Use builtin generics (list[int], dict[str, int]) since 3.9.", ver="3.9")
up("PEP604-OPTIONAL", "Optional[X] / Union[X, Y]", "non-pep604-annotation-optional", "Check for `typing.Optional` annotations that can be rewritten based on PEP 604 syntax.",
   '((generic_type (identifier) @match) (#match? @match "^(Optional|Union)$"))', "def f(x: Optional[int]) -> None:\n    pass\n",
   "def f(x: int | None) -> None:\n    pass\n", "Use X | None (3.10+).", ver="3.10")
up("LRU-CACHE-NONE", "lru_cache(maxsize=None)", "lru-cache-with-maxsize-none", "Checks for uses of `functools.lru_cache` that set `maxsize=None`.",
   '((decorator (call function: (_) @f arguments: (argument_list (keyword_argument name: (identifier) @k value: (none))))) @match (#match? @f "lru_cache$") (#eq? @k "maxsize"))',
   "@lru_cache(maxsize=None)\ndef f(x):\n    return x\n", "@cache\ndef f(x):\n    return x\n", "Use functools.cache (3.9+).", ver="3.9")
up("FORMAT-TO-FSTRING", "str.format() on a literal", "f-string", "Checks for `str.format` calls that can be replaced with f-strings.",
   '((call function: (attribute object: (string) attribute: (identifier) @a) arguments: (argument_list . [(identifier) (attribute)] .)) @match (#eq? @a "format"))',
   "msg = \"hello {}\".format(name)\n", "msg = f\"hello {name}\"\n", "f-strings are clearer and faster.", ver="3.6")
up("PERCENT-FORMAT", "printf-style % formatting", "printf-string-formatting", "Checks for printf -style string formatting",
   '((binary_operator left: (string) @match operator: "%") (#match? @match "%[sdrifx]"))', "msg = \"hello %s\" % name\n", "msg = f\"hello {name}\"\n",
   "Prefer f-strings / str.format.", ver="3.6")
up("DATETIME-UTC-ALIAS", "datetime.timezone.utc", "datetime-timezone-utc", "Checks for uses of `datetime.timezone.utc`.",
   '((attribute object: (attribute attribute: (identifier) @t) attribute: (identifier) @match) (#eq? @t "timezone") (#eq? @match "utc"))',
   "now = datetime.now(datetime.timezone.utc)\n", "now = datetime.now(datetime.UTC)\n", "datetime.UTC alias exists since 3.11.", ver="3.11")
up("TIMEOUT-ERROR-ALIAS", "asyncio.TimeoutError", "timeout-error-alias", "Checks for uses of exceptions that alias `TimeoutError`.",
   '((attribute object: (identifier) @o attribute: (identifier) @match) (#match? @o "^(asyncio|socket)$") (#match? @match "^(TimeoutError|timeout)$"))',
   "try:\n    await f()\nexcept asyncio.TimeoutError:\n    pass\n", "try:\n    await f()\nexcept TimeoutError:\n    pass\n",
   "asyncio.TimeoutError/socket.timeout alias the builtin since 3.11/3.10.", ver="3.11")
up("STR-ENUM", "class X(str, Enum)", "replace-str-enum", "Checks for classes that inherit from both `str` and `enum.Enum`.",
   '((class_definition superclasses: (argument_list (identifier) @s [(identifier) (attribute)] @e) @match) (#eq? @s "str") (#match? @e "Enum$"))',
   "class Color(str, Enum):\n    RED = \"red\"\n", "class Color(StrEnum):\n    RED = \"red\"\n", "Use enum.StrEnum (3.11+); note str() differs.", ver="3.11")
up("TYPE-ALIAS-PEP695", "TypeAlias annotation", "non-pep695-type-alias", "Checks for use of `TypeAlias` annotations",
   '((assignment type: (type (_) @match) right: (_)) (#match? @match "TypeAlias$"))', "Vector: TypeAlias = list[float]\n", "type Vector = list[float]\n",
   "Use the type statement (3.12+).", ver="3.12")
up("TYPING-TEXT", "typing.Text", "typing-text-str-alias", "Checks for uses of `typing.Text`.", from_import("typing", "Text"),
   "from typing import Text\n", "s: str = \"\"\n", "typing.Text is just str.")
up("OPEN-ALIAS", "io.open()", "open-alias", "Checks for uses of `io.open`.", mcall("io", "open"), "f = io.open(p)\n", "f = open(p)\n", "io.open is the builtin open.")
up("REMOVEPREFIX", "Manual prefix stripping", "slice-to-remove-prefix-or-suffix", "Checks for code that could be written more idiomatically using `str.removeprefix()` or `str.removesuffix()`.",
   '((conditional_expression (subscript (identifier) @a (slice (call function: (identifier) @l))) (call function: (attribute object: (identifier) @b attribute: (identifier) @m))) @match (#eq? @a @b) (#eq? @l "len") (#eq? @m "startswith"))',
   "s = s[len(p):] if s.startswith(p) else s\n", "s = s.removeprefix(p)\n", "Use str.removeprefix/removesuffix (3.9+).", ver="3.9")
up("ZONEINFO", "pytz instead of zoneinfo", "https://docs.python.org/3/library/zoneinfo.html", "IANA time zone", imports("^pytz$"),
   "import pytz\ntz = pytz.timezone('Europe/Tallinn')\n", "from zoneinfo import ZoneInfo\ntz = ZoneInfo('Europe/Tallinn')\n",
   "zoneinfo (3.9+) provides IANA zones with standard tzinfo semantics.", ver="3.9")
up("TOMLLIB", "Third-party toml reader", "https://docs.python.org/3/library/tomllib.html", "This module provides an interface for parsing TOML", imports("^(toml|tomli)$"),
   "import toml\ncfg = toml.load(f)\n", "import tomllib\ncfg = tomllib.load(f)\n", "tomllib is in the stdlib since 3.11 (read-only).", ver="3.11")
up("ITERTOOLS-BATCHED", "Manual chunking with range/slicing", "https://docs.python.org/3/library/itertools.html", "batched('ABCDEFG', n=3)",
   '((list_comprehension body: (subscript (identifier) @a (slice (identifier) @i (binary_operator))) (for_in_clause left: (identifier) @j right: (call function: (identifier) @r arguments: (argument_list (_) (_) (_))))) @match (#eq? @i @j) (#eq? @r "range"))',
   "chunks = [xs[i:i + n] for i in range(0, len(xs), n)]\n", "chunks = list(itertools.batched(xs, n))\n", "itertools.batched (3.12+).", ver="3.12")
up("CONTEXTLIB-CHDIR", "os.chdir with manual restore", "https://docs.python.org/3/library/contextlib.html", "Non parallel-safe context manager to change the current working directory",
   '(try_statement body: (block (expression_statement (call function: (attribute object: (identifier) @o attribute: (identifier) @a)))) (finally_clause (block (expression_statement (call function: (attribute attribute: (identifier) @b))))) @match (#eq? @o "os") (#eq? @a "chdir") (#eq? @b "chdir"))',
   "try:\n    os.chdir(d)\n    run()\nfinally:\n    os.chdir(old)\n", "with contextlib.chdir(d):\n    run()\n", "Use contextlib.chdir (3.11+).", ver="3.11")
# ------------------------------------------------------------------ Sonar-way checklist gaps (own detection/wording)
P("CHMOD-WORLD-WRITABLE", "File mode grants write access to others", LIB("stat"), "Others have write permission",
  '((call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list (_) (integer) @match)) (#eq? @o "os") (#match? @a "^(chmod|fchmod|lchmod|mkdir|makedirs)$") (#match? @match "^0[oO]?[0-7]*[2367]$"))',
  "import os\nos.chmod(path, 0o777)\n", "import os\nos.chmod(path, 0o750)\n",
  "Every local user can modify this file or directory. Drop the write bit for others (and usually group).",
  sev="major", kind="security", cat="security", xref=["sonar:python:S2612"])
P("DJANGO-CSRF-EXEMPT", "Django view exempted from CSRF protection", "https://docs.djangoproject.com/en/6.1/ref/csrf/",
  "This decorator marks a view as being exempt from the protection ensured by the middleware",
  '(decorator [(identifier) @match (attribute attribute: (identifier) @match)] (#eq? @match "csrf_exempt"))',
  "from django.views.decorators.csrf import csrf_exempt\n\n@csrf_exempt\ndef update_profile(request):\n    request.user.email = request.POST['email']\n",
  "def update_profile(request):\n    request.user.email = request.POST['email']\n",
  "The view accepts state-changing requests from any site the user visits. Keep CSRF on, or authenticate the caller another way (signed webhook, token header).",
  sev="major", kind="security", cat="security", mode="ai-confirm", framework="django",
  ai="Does this view change state for a cookie-authenticated user (rather than being a signed webhook / token-authenticated API endpoint)?",
  xref=["sonar:python:S4502"], docv="Django 6.1")
P("DJANGO-DEBUG-TRUE", "Django DEBUG = True in settings", "https://docs.djangoproject.com/en/6.1/ref/settings/",
  "Never deploy a site into production with DEBUG turned on",
  '((expression_statement (assignment left: (identifier) @n right: (true))) @match (#eq? @n "DEBUG"))',
  "DEBUG = True\nALLOWED_HOSTS = ['example.com']\n", "DEBUG = os.environ.get('DJANGO_DEBUG') == '1'\n",
  "Debug mode shows stack traces, settings and SQL to anyone who triggers an error. Read DEBUG from the environment and default it to False.",
  sev="major", kind="security", cat="security", mode="ai-confirm", framework="django",
  files=["**/settings.py", "**/settings/*.py", "!**/settings/dev*.py", "!**/settings/local*.py", "!**/settings/test*.py"],
  ai="Is this the settings module used in production (not a local/dev/test settings file)?", xref=["sonar:python:S4507"], docv="Django 6.1")
P("JWT-NO-VERIFY", "JWT decoded without signature verification", "https://pyjwt.readthedocs.io/en/stable/usage.html",
  "the integrity or authenticity of the claimset cannot be trusted",
  '((call function: (attribute object: (identifier) @o attribute: (identifier) @a) arguments: (argument_list (keyword_argument name: (identifier) @k value: (dictionary (pair key: (string) @key value: (false)))))) @match (#eq? @o "jwt") (#eq? @a "decode") (#eq? @k "options") (#match? @key "verify_signature"))',
  "import jwt\nclaims = jwt.decode(token, options={\"verify_signature\": False})\n",
  "import jwt\nclaims = jwt.decode(token, key, algorithms=[\"RS256\"])\n",
  "Claims from an unverified token can be forged by anyone. Verify the signature with the expected key and an explicit algorithms list.",
  sev="critical", kind="security", cat="security", xref=["sonar:python:S5659"], docv="PyJWT 2.x")
P("COOKIE-HTTPONLY-FALSE", "Cookie explicitly readable by JavaScript (httponly=False)", "https://werkzeug.palletsprojects.com/en/stable/wrappers/",
  "Disallow JavaScript access to the cookie",
  kwarg("set_cookie$", "httponly", "(false)"),
  "resp.set_cookie('session', sid, secure=True, httponly=False)\n", "resp.set_cookie('session', sid, secure=True, httponly=True)\n",
  "Scripts on the page (including injected ones) can read this cookie. Keep httponly=True unless client code must read it and it holds nothing sensitive.",
  sev="major", kind="security", cat="security", mode="ai-confirm",
  ai="Does the cookie hold a session id, auth token or other secret (rather than a UI preference that client code must read)?",
  xref=["sonar:python:S3330"], docv="Werkzeug 3.x")
P("TORCH-LOAD-UNSAFE", "torch.load with weights_only=False", "https://docs.pytorch.org/docs/main/generated/torch.load.html",
  "Never load data from an untrusted source",
  kwarg("^torch\\\\.load$", "weights_only", "(false)"),
  "import torch\nmodel = torch.load(path, weights_only=False)\n", "import torch\nstate = torch.load(path, weights_only=True)\n",
  "weights_only=False unpickles arbitrary objects, so a crafted checkpoint runs code on load. Load tensors/state dicts with weights_only=True (the default since PyTorch 2.6).",
  sev="critical", kind="security", cat="security", xref=["sonar:python:S6985"], docv="PyTorch 2.x")

P("FLASK-CORS-ALL-ORIGINS", "flask_cors CORS(app) without origins allows every origin", "https://flask-cors.readthedocs.io/en/latest/api.html",
  "by default enables CORS support on all routes, for all origins and methods",
  '((call function: (identifier) @f arguments: (argument_list . (identifier) .) @a) @match (#eq? @f "CORS"))\n'
  '((call function: (identifier) @f arguments: (argument_list (keyword_argument name: (identifier) @k value: (string) @v))) @match (#eq? @f "CORS") (#match? @k "^(origins|resources)$") (#match? @v "^[\\x27\\"]\\\\*[\\x27\\"]$"))',
  "from flask_cors import CORS\nCORS(app)\n", "from flask_cors import CORS\nCORS(app, origins=[\"https://app.example.com\"])\n",
  "Every website can call this API from a browser. Pass origins= with the frontends that need access.",
  sev="major", kind="security", cat="security", mode="ai-confirm", ai="Does this API serve authenticated or non-public data (not a fully public read-only API)?",
  cwe=["CWE-942"], xref=["sonar:python:S5122"], files=["**/*.py", "!**/test*/**", "!**/*_test.py", "!**/test_*.py"])

P("RANDOM-SESSION-VALUE", "random module value stored in a session, cookie or token", "https://docs.python.org/3/library/random.html",
  "should not be used for security purposes",
  '((assignment left: (_) @n right: (_) @match) (#match? @match "\\\\brandom\\\\.(random|randint|randrange|getrandbits|randbytes|choice|choices|sample|uniform|normalvariate|gauss|triangular|betavariate|expovariate)\\\\("))',
  "import random\n\ndef remember(session):\n    value = str(random.getrandbits(32))\n    session['rememberMe'] = value\n",
  "import secrets\n\ndef remember(session):\n    value = str(secrets.randbelow(2**32))\n    session['rememberMe'] = value\n",
  "This value comes from the random module (a predictable PRNG) and ends up in a session/cookie/token in the same function. Use the secrets module.",
  sev="major", kind="security", cat="security", mode="ai-confirm",
  filters=["func.has_re:(?i)session|set_cookie|cookie|token|password|passwd|secret|nonce|otp|csrf|api_?key",
           r"func.lacks_re:(?i)\bjitter\b|backoff|span_id|trace_id|traceid|spanid"],
  ai="Is the random value used as (or to derive) a secret/identifier an attacker should not predict (session value, cookie, token, password, nonce)?",
  cwe=["CWE-330"], xref=["sonar:python:S2245"],
  fp=["import random\nimport time\n\ndef retry(secret_name):\n    delay = random.uniform(0.1, 0.5)  # jitter\n    time.sleep(delay)\n",
      "import random\n\ndef new_span_id(token_store):\n    return format(random.getrandbits(64), '016x')\n"])

P("INDEX-RETURNS-NON-INT", "__index__ returns a non-integer", LIB("stdtypes"), "Called to implement operator.index()",
  '(function_definition name: (identifier) @n body: (block (return_statement [(string) (float) (true) (false) (none) (list) (dictionary) (set)] @match)) (#eq? @n "__index__"))',
  "class N:\n    def __index__(self):\n        return '1'\n",
  "class N:\n    def __index__(self):\n        return 1\n",
  "__index__ must return an int (or a subclass of int); any other type raises TypeError when the object is used as a sequence index.",
  sev="major", kind="anti-pattern", cat="correctness", quote="Called to implement operator.index() and whenever Python needs to losslessly convert the numeric object to an integer object (such as in slicing, or in the built-in bin(), hex() and oct() functions).",
  xref=["sonar:python:S6663"])
P("ORDERING-WITHOUT-EQ", "__lt__ defined without __eq__", "https://docs.python.org/3/library/functools.html", "Given a class defining one or more rich comparison ordering methods",
  '((class_definition body: (block (function_definition name: (identifier) @n))) @match (#eq? @n "__lt__") (#not-match? @match "__eq__"))',
  "class V:\n    def __lt__(self, other):\n        return self.n < other.n\n",
  "class V:\n    def __eq__(self, other):\n        return self.n == other.n\n    def __lt__(self, other):\n        return self.n < other.n\n",
  "Ordering without equality is incomplete: objects can be less-than each other and still not compare equal to anything. Define __eq__ (and functools.total_ordering, or the rest of the rich comparisons).",
  sev="minor", kind="best-practice", cat="correctness", mode="ai-confirm",
  ai="Does this class participate in sorting or comparisons where equality should be consistent with ordering?",
  quote="The class must define one of __lt__(), __le__(), __gt__(), or __ge__(). In addition, the class should supply an __eq__() method.",
  xref=["sonar:python:S8500"])

RULES = P.R

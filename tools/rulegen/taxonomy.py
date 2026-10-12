#!/usr/bin/env python3
"""taxonomy: security rules -> CWE / OWASP Top 10 (2021, 2025) / OWASP ASVS 5.0 section ids.

Writes rules/data/taxonomy.yaml, applied by internal/rules.ApplyTaxonomy at load time (a rule's
own cwe/owasp/asvs fields win). Every rule of kind "security" must resolve to at least one CWE;
`python3 tools/rulegen/taxonomy.py` fails when one does not.

CWE -> OWASP comes from the official category CWE lists (https://owasp.org/Top10/2021/,
https://owasp.org/Top10/2025/); where a CWE is not listed in a year's mapping the entry carries no
category for that year rather than a guess. ASVS ids are 5.0 section ids
(https://github.com/OWASP/ASVS/tree/master/5.0/en), e.g. V1.2 Injection Prevention.
"""
import glob, os, re, sys
import yaml


class NoAlias(yaml.SafeDumper):
    """Write shared lists out in full: anchors/aliases make a data file harder to diff and review."""

    def ignore_aliases(self, data):
        return True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# CWE -> (OWASP 2021, OWASP 2025, ASVS 5.0 sections)
CWE = {
    # added 2026-10 (OWASP Top 10 2021/2025 category pages checked for each id)
    # added 2026-10 (ASVS gap batch); a year is None where its official CWE list does not name the id
    "CWE-116":  ("A03:2021", None, ["V1.1"]),               # improper encoding/escaping (double encoding)
    "CWE-117":  ("A09:2021", None, ["V16.4"]),              # log neutralisation (log injection)
    "CWE-1236": ("A03:2021", None, ["V1.2"]),               # CSV formula injection
    "CWE-565":  ("A08:2021", None, ["V3.3"]),               # cookie trust without integrity (prefixes)
    "CWE-409":  (None, None, ["V5.2"]),                     # highly compressed data (zip bombs)
    "CWE-59":   ("A01:2021", None, ["V5.2"]),               # link following (archive symlinks)
    "CWE-598":  ("A04:2021", None, ["V14.2"]),              # sensitive data in GET query strings
    "CWE-636":  (None, None, ["V16.5"]),                    # not failing securely (fail open)
    "CWE-650":  (None, None, ["V3.5"]),                     # trusting HTTP method semantics
    "CWE-613":  ("A07:2021", None, ["V7.3"]),               # insufficient session expiration
    "CWE-353":  ("A08:2021", None, ["V3.6"]),               # missing integrity check (SRI)
    "CWE-755":  (None, None, ["V16.5"]),                    # improper handling of exceptional conditions
    "CWE-362":  (None, None, ["V15.4"]),                    # race condition on shared state
    "CWE-567":  (None, None, ["V15.4"]),                    # unsynchronised shared data across threads
    "CWE-1333": (None, None, ["V1.3"]),                     # ReDoS
    "CWE-730":  (None, None, ["V1.3"]),                     # regex DoS (OWASP view)
    "CWE-943":  (None, None, ["V1.2"]),                     # NoSQL / data query injection (not in a Top 10 CWE list)
    "CWE-459":  (None, None, []),                           # incomplete cleanup (temporary files)
    "CWE-486":  (None, None, []),                           # comparison of classes by name
    "CWE-324":  ("A02:2021", "A04:2025", ["V11.1"]),       # key past its expiration (no rotation)
    "CWE-113":  ("A03:2021", "A05:2025", ["V1.2"]),        # CRLF in HTTP headers
    "CWE-134":  (None, None, ["V1.2"]),                     # externally-controlled format string (not in a Top 10 CWE list)
    "CWE-321":  ("A02:2021", "A04:2025", ["V13.3"]),       # hard-coded cryptographic key
    "CWE-757":  ("A02:2021", "A04:2025", ["V12.1"]),       # less-secure algorithm during negotiation
    "CWE-93":   ("A03:2021", "A05:2025", ["V1.3"]),         # CRLF / SMTP header injection
    "CWE-74":   ("A03:2021", "A05:2025", ["V1.3"]),         # injection (JNDI)
    "CWE-530":  (None, None, ["V14.2"]),                    # backup file exposure
    "CWE-926":  (None, "A08:2025", []),                     # exported Android component
    "CWE-749":  (None, "A01:2025", []),                     # exposed dangerous method
    "CWE-312":  ("A04:2021", "A06:2025", ["V14.2"]),        # cleartext storage
    "CWE-656":  ("A04:2021", "A06:2025", []),               # security through obscurity
    "CWE-329":  ("A02:2021", "A04:2025", ["V11.3"]),        # predictable IV
    "CWE-1204": (None, None, ["V11.3"]),                    # weak IV
    "CWE-348":  (None, None, ["V4.1"]),                     # untrusted source (proxy headers)
    "CWE-497":  ("A01:2021", "A01:2025", ["V13.4"]),        # system information exposure
    "CWE-548":  ("A01:2021", "A01:2025", ["V13.4"]),        # directory listing
    "CWE-668": ("A01:2021", "A01:2025", ["V13.2"]),
    "CWE-522": ("A04:2021", "A06:2025", ["V14.2"]),          # insufficiently protected credentials
    "CWE-77": ("A03:2021", "A05:2025", ["V1.2"]),            # command (prompt) injection
    "CWE-778": ("A09:2021", "A09:2025", ["V16.2"]),          # insufficient logging
    "CWE-1275": ("A01:2021", "A01:2025", ["V3.3"]),          # SameSite cookie attribute
    "CWE-917": ("A03:2021", "A05:2025", ["V1.3"]),           # expression language injection
    "CWE-521": ("A07:2021", "A07:2025", ["V6.2"]),           # weak password requirements
    "CWE-915": ("A08:2021", "A08:2025", ["V15.3"]),          # mass assignment
    "CWE-1385": (None, None, ["V4.4"]),                      # WebSocket origin validation
    "CWE-367": (None, None, ["V15.4"]),                      # TOCTOU
    "CWE-1336": (None, None, ["V1.3"]),                      # template injection
    "CWE-190": (None, None, ["V1.4"]),                       # integer overflow
    "CWE-681": (None, None, ["V1.4"]),                       # numeric conversion
    "CWE-693": (None, "A06:2025", ["V3.4"]),
    "CWE-269": ("A04:2021", "A06:2025", ["V8.2"]),
    "CWE-306": ("A07:2021", "A07:2025", ["V6.1"]),
    "CWE-90": ("A03:2021", "A05:2025", ["V1.2"]),
    "CWE-643": ("A03:2021", "A05:2025", ["V1.2"]),
    "CWE-501": ("A04:2021", "A06:2025", ["V2.2"]),
    "CWE-22":   ("A01:2021", "A01:2025", ["V5.3"]),        # path traversal
    "CWE-23":   ("A01:2021", "A01:2025", ["V5.3"]),        # relative path traversal
    "CWE-78":   ("A03:2021", "A05:2025", ["V1.2"]),        # OS command injection
    "CWE-79":   ("A03:2021", "A05:2025", ["V1.2", "V3.2"]),  # XSS
    "CWE-89":   ("A03:2021", "A05:2025", ["V1.2"]),        # SQL injection
    "CWE-95":   ("A03:2021", "A05:2025", ["V1.2"]),        # eval injection
    "CWE-98":   ("A03:2021", "A05:2025", ["V1.2"]),        # PHP file inclusion
    "CWE-20":   ("A03:2021", "A05:2025", ["V2.2"]),              # input validation
    "CWE-200":  ("A01:2021", "A01:2025", ["V13.4"]),       # information exposure
    "CWE-208":  (None, None, ["V11.2"]),             # timing discrepancy
    "CWE-209":  ("A04:2021", "A10:2025", ["V16.5"]),       # error message info leak
    "CWE-250":  (None, None, []),                    # unnecessary privileges
    "CWE-256":  ("A04:2021", "A06:2025", ["V6.2"]),              # plaintext password storage
    "CWE-284":  ("A01:2021", "A01:2025", ["V8.2"]),        # improper access control
    "CWE-295":  ("A07:2021", "A07:2025", ["V12.2", "V12.3"]),    # certificate validation
    "CWE-297":  ("A07:2021", "A07:2025", ["V12.3"]),             # host mismatch
    "CWE-319":  ("A02:2021", "A04:2025", ["V12.2"]),             # cleartext transmission
    "CWE-326":  ("A02:2021", "A04:2025", ["V12.1"]),       # inadequate strength
    "CWE-327":  ("A02:2021", "A04:2025", ["V11.3"]),       # broken crypto
    "CWE-328":  ("A02:2021", "A04:2025", ["V11.4"]),       # weak hash
    "CWE-330":  ("A02:2021", "A04:2025", ["V11.5"]),       # insufficient randomness
    "CWE-338":  ("A02:2021", "A04:2025", ["V11.5"]),       # weak PRNG
    "CWE-345":  ("A08:2021", "A08:2025", ["V3.5"]),        # data authenticity
    "CWE-346":  ("A07:2021", "A07:2025", ["V3.5"]),              # origin validation
    "CWE-352":  ("A01:2021", "A01:2025", ["V3.5"]),        # CSRF
    "CWE-354":  (None, None, ["V15.2"]),       # integrity check value
    "CWE-377":  ("A01:2021", "A01:2025", ["V5.3"]),              # insecure temp file
    "CWE-391":  (None, "A10:2025", ["V16.5"]),             # unchecked error condition
    "CWE-400":  (None, None, ["V15.3"]),                   # resource exhaustion
    "CWE-434":  ("A04:2021", "A06:2025", ["V5.2"]),        # unrestricted upload
    "CWE-477":  (None, "A03:2025", ["V15.2"]),             # obsolete function  # OWASP lists it as "CWE-447 Use of Obsolete Function" (typo: that title is CWE-477)
    "CWE-489":  (None, "A02:2025", ["V13.4"]),       # debug code left enabled
    "CWE-494":  ("A08:2021", "A08:2025", ["V15.2"]),       # download without integrity check
    "CWE-502":  ("A08:2021", "A08:2025", ["V1.5"]),        # deserialization
    "CWE-532":  ("A09:2021", "A09:2025", ["V16.2"]),       # sensitive data in logs/output
    "CWE-538":  ("A01:2021", "A01:2025", ["V13.3"]),       # sensitive info in accessible file
    "CWE-601":  ("A01:2021", "A01:2025", []),              # open redirect
    "CWE-611":  ("A05:2021", "A02:2025", ["V1.5"]),        # XXE
    "CWE-614":  ("A05:2021", "A02:2025", ["V3.3"]),        # cookie without Secure
    "CWE-617":  (None, None, ["V15.3"]),                   # reachable assertion
    "CWE-621":  (None, None, ["V15.3"]),                   # variable extraction
    "CWE-665":  (None, None, ["V1.4"]),                    # improper initialization
    "CWE-697":  (None, None, ["V15.3"]),                   # incorrect comparison
    "CWE-732":  (None, "A01:2025", []),              # incorrect permission assignment
    "CWE-770":  (None, None, ["V4.3"]),                    # allocation without limits
    "CWE-776":  ("A05:2021", "A02:2025", ["V1.5"]),        # entity/alias expansion
    "CWE-798":  ("A07:2021", "A07:2025", ["V13.3"]),       # hard-coded credentials
    "CWE-862":  ("A01:2021", "A01:2025", ["V8.3"]),        # missing authorization
    "CWE-916":  ("A02:2021", "A04:2025", ["V11.4"]),       # weak password hash
    "CWE-942":  ("A05:2021", "A02:2025", ["V3.4"]),        # permissive CORS
    "CWE-1004": ("A05:2021", "A02:2025", ["V3.3"]),        # cookie without HttpOnly
    "CWE-1021": ("A04:2021", "A06:2025", ["V3.4"]),              # clickjacking
    "CWE-1022": (None, "A06:2025", ["V3.7"]),                    # target=_blank opener
    "CWE-1104": ("A06:2021", "A03:2025", ["V15.2"]),       # unmaintained / unpinned components
    "CWE-1321": (None, None, ["V15.3"]),       # prototype pollution
    "CWE-1327": (None, None, ["V13.2"]),                   # bind to unrestricted address
    "CWE-1357": (None, "A03:2025", ["V15.2"]),             # insufficiently trustworthy component
    "CWE-1395": (None, "A03:2025", ["V15.2"]),             # vulnerable third-party component
    "CWE-242":  (None, None, ["V1.4"]),                    # inherently dangerous function (unsafe)
    "CWE-16":   ("A05:2021", "A02:2025", ["V13.4"]),       # configuration
    "CWE-829":  ("A08:2021", "A08:2025", ["V15.2"]),       # untrusted control sphere
    "CWE-311":  ("A04:2021", "A06:2025", ["V14.2"]),       # missing encryption
    "CWE-287":  ("A07:2021", "A07:2025", ["V6.3"]),        # improper authentication
    "CWE-863":  ("A01:2021", "A01:2025", ["V8.2"]),        # incorrect authorization
    "CWE-524":  (None, None, ["V14.3"]),                   # sensitive info in cache
    "CWE-307":  ("A07:2021", "A07:2025", ["V6.3"]),        # brute force not limited
    "CWE-384":  ("A07:2021", "A07:2025", ["V7.2"]),        # session fixation
    "CWE-347":  ("A02:2021", None, ["V9.1"]),              # signature not verified
    "CWE-922":  (None, None, ["V14.2"]),                   # insecure storage of sensitive data
    "CWE-918":  ("A10:2021", "A01:2025", ["V1.3"]),       # SSRF
    "CWE-94":   ("A03:2021", "A05:2025", ["V1.2"]),        # code injection
    "CWE-927":  (None, None, []),                          # implicit intent for sensitive communication
}

# (regex on "<ID> | <title>", [CWE...]) - first match wins.
PATTERNS = [
    (r"LDAP-ANON", ["CWE-287"]),
    (r"ENDPOINT-NO-AUTH", ["CWE-862"]),
    (r"FIELD-ACCESS-QUERY", ["CWE-284"]),
    (r"LOGIN-LOCKOUT", ["CWE-307"]),
    (r"SESSION-FIXATION", ["CWE-384"]),
    (r"JWT-NO-VERIFY", ["CWE-347"]),
    (r"EXTERNAL-STORAGE", ["CWE-922"]),
    (r"BROADCAST-NO-PERMISSION", ["CWE-927"]),
    (r"WORLD-WRITABLE", ["CWE-732"]),
    (r"TORCH-LOAD", ["CWE-502"]),
    (r"COOKIE-HTTPONLY", ["CWE-1004"]),
    (r"DISPLAY-ERRORS", ["CWE-209"]),
    (r"SECURITY-DEBUG|DJANGO-DEBUG|GIN-DEBUG|WEBVIEW-DEBUG|PPROF-IMPORTED", ["CWE-489"]),
    (r"SCRIPT-REMOTE-EXEC|CURL-PIPE-SHELL|INSTALL-SCRIPT-DOWNLOAD", ["CWE-494"]),
    (r"MATH-RAND-READ", ["CWE-338"]),
    (r"AWS-ACCESS-KEY|PRIVATE-KEY|GITHUB-TOKEN|SLACK-TOKEN|STRIPE-LIVE-KEY|JWT-LITERAL|AZURE-STORAGE-KEY|GCP-SERVICE-ACCOUNT|URL-CREDENTIALS|HARDCODED-(SECRET|PASSWORD|REPO-CREDENTIALS)|SECRET-FIELD|SECRET-VARIABLE-DEFAULT|BACKEND-CREDENTIALS|PROVIDER-HARDCODED|AUTH-IN-COMPOSER|GPG-PASSPHRASE|PASSWORD-PROPERTY|COMPOSE-(ENV|BUILD-ARGS)-SECRET|PAYLOAD-HARDCODED", ["CWE-798"]),
    (r"SQL", ["CWE-89"]),
    (r"XXE|JAXP-FSP|PY-SEC-XML-UNTRUSTED", ["CWE-611"]),
    (r"ALIAS-BOMB", ["CWE-776"]),
    (r"DESER|SERIAL-FILTER|PICKLE|MARSHAL|SHELVE|UNSERIALIZE|YAML-LOAD-UNSAFE|UNSAFE-TAG", ["CWE-502"]),
    (r"CMD|EXEC|SHELL-INJECTION|SUBPROCESS|OS-SYSTEM|SHELL-ARGS|EXEC-SHELL|RUNTIME-EXEC", ["CWE-78"]),
    (r"(^|-)EVAL|NO-NEW-FUNC|IMPLIED-EVAL", ["CWE-95"]),
    (r"INCLUDE-INPUT", ["CWE-98"]),
    (r"EXTRACT-INPUT", ["CWE-621"]),
    (r"INNERHTML|INNER-HTML|OUTERHTML|VHTML|BYPASS-SECURITY|XSS|SCRIPT-URL|JAVASCRIPT-URL|DOCUMENT-WRITE|TEXT-TEMPLATE-HTML|TEMPLATE-HTML-CONVERSION|AUTOESCAPE|USEHEAD|URL-INJECTION|STYLE-INJECTION", ["CWE-79"]),
    (r"PATH-TRAVERSAL|EXTRACTALL|ZIPFILE-EXTRACT", ["CWE-22"]),
    (r"OPEN-REDIRECT", ["CWE-601"]),
    (r"CSRF", ["CWE-352"]),
    (r"CORS", ["CWE-942"]),
    (r"FRAMEOPTIONS", ["CWE-1021"]),
    (r"TARGET-BLANK", ["CWE-1022"]),
    (r"POSTMESSAGE-STAR", ["CWE-345"]),
    (r"MESSAGE-ORIGIN|DOCUMENT-DOMAIN", ["CWE-346"]),
    (r"TRUST-ALL|INSECURE-SKIP-VERIFY|CURL-NO-VERIFY|SSL-NO-VERIFY|VERIFY-FALSE|INSECURE-HOST-KEY|DISABLE-TLS", ["CWE-295"]),
    (r"HOSTNAME-VERIFIER", ["CWE-297"]),
    (r"TLS-OLD-VERSION", ["CWE-326"]),
    (r"MD5-PASSWORD|NOOP-ENCODER|DEFAULT-ENCODER|LEGACY-ENCODER", ["CWE-916"]),
    (r"WEAK-CRYPTO-(MD5|SHA1)|WEAK-HASH|HASH-WEAK", ["CWE-328"]),
    (r"WEAK-CRYPTO|CIPHER|X509-PEM", ["CWE-327"]),
    (r"RANDOM|RAND", ["CWE-330"]),
    (r"HASH-COMPARE|HMAC-COMPARE", ["CWE-208"]),
    (r"PRINTSTACK", ["CWE-209"]),
    (r"MKTEMP|HARDCODED-TMP", ["CWE-377"]),
    (r"ASSERT-FOR-SECURITY", ["CWE-617"]),
    (r"PERMITALL|OPEN-WRITE-ACCESS|SERVER-FUNCTION-NO-AUTH|LOCAL-API|H2-REMOTE", ["CWE-862"]),
    (r"UPLOAD-NO-MIME", ["CWE-434"]),
    (r"FLASK-DEBUG|H2-CONSOLE|HTTP-SERVER-PRODUCTION", ["CWE-489"]),
    (r"HEALTH-DETAILS|SHOW-VALUES|CONFIGPROPS|SB-ACT|RTC-|NEXT-PUBLIC-SECRET|AUTH-COLLECTION-VERSIONS|PUBLIC-READ-VERSIONS|REMOTE-STATE-DATA", ["CWE-200"]),
    (r"SENSITIVE-(VARIABLE|OUTPUT)", ["CWE-532"]),
    (r"SECRETS-USED-IN-ARG|ENV-SECRET-LAYER|COPY-SECRET-FILE", ["CWE-538"]),
    (r"COOKIE", ["CWE-614", "CWE-1004"]),
    (r"CURL-PIPE-SHELL|SCRIPT-REMOTE-EXEC|INSTALL-SCRIPT-DOWNLOAD|ADD-REMOTE-NO-CHECKSUM", ["CWE-494"]),
    (r"CHECKSUM-POLICY", ["CWE-354"]),
    (r"HTTP-TARBALL|INSECURE-REPO-URL|HTTP-REPOSITORY|REPO-HTTP|PUBLISHCONFIG-HTTP|SECURE-HTTP-OFF|ALLOW-INSECURE-PROTOCOL|HTTP-URL", ["CWE-319"]),
    (r"BLOCK-INSECURE-OFF", ["CWE-1395"]),
    (r"ALLOW(-ALL)?-PLUGINS", ["CWE-829"]),
    (r"DYNAMIC-VERSION|SNAPSHOT|MAVEN-LOCAL|VERSION-RANGE|TARBALL-URL|PINNED-SOURCE|MUTABLE-REF|MOST-RECENT-NO-OWNER", ["CWE-1357"]),
    (r"PORT-ALL-INTERFACES|BIND-ALL", ["CWE-1327"]),
    (r"SG-ADMIN-PORT|RDS-PUBLICLY|S3-PUBLIC|IAM-WILDCARD|DOCKER-SOCKET", ["CWE-732"]),
    (r"UNENCRYPTED", ["CWE-311"]),
    (r"PRIVILEGED|NETWORK-MODE-HOST|PID-HOST|IPC-HOST|CAP-ADD|SECCOMP|USERNS|UTS-HOST|CGROUP-HOST|READ-ONLY|USER-ROOT|NO-USER|SUDO", ["CWE-250"]),
    (r"PROTO-KEY", ["CWE-1321"]),
    (r"LISTEN-NO-TIMEOUTS", ["CWE-400"]),
    (r"ALIAS-FAN-OUT|NOT-PAGINATED", ["CWE-770"]),
    (r"UNSAFE-IMPORT", ["CWE-242"]),
    (r"BUFFER-CTOR", ["CWE-665"]),
    (r"URL-PARSE|UNVALIDATED-BODY", ["CWE-20"]),
    (r"MATH-RAND-READ", ["CWE-338"]),
    (r"JSON-DECODE-NO-THROW", ["CWE-391"]),
    (r"IN-ARRAY-LOOSE", ["CWE-697"]),
    (r"NG-MIG-JSONP|BLOCK-INSECURE-DEPRECATED|JAVA-MIG-SM-001|SB-SEC-GLOBAL-METHOD|SB-SEC-ANTMATCHERS|SB-SEC-00[12] ", ["CWE-477"]),
    (r"GO-MIG-DSA|ELLIPTIC-LOW-LEVEL", ["CWE-327"]),
    (r"PBKDF2-DIGEST", ["CWE-916"]),
    (r"INLINE-DYNAMIC-ARGUMENT", ["CWE-20"]),
    (r"GRAPHQL-UNUSED", ["CWE-16"]),
    (r"EPHEMERAL-SECRET", ["CWE-532"]),
]


# Code-quality rules that implement a CWE weakness (no OWASP category): CWE tag only, so CWE coverage
# reports count them. Exact rule ids; each mapping is the CWE whose description matches the rule's check.
QUALITY = {
    "CWE-476": r"^(GO-QUAL-VET-HTTPRESPONSE|GO-QUAL-CTX-NIL|KT-QUAL-NOT-NULL-ASSERTION|JAVA-QUAL-COR-OPTIONAL-OF-NULL-001|JAVA-QUAL-COR-LIST-OF-NULL-001)$",
    "CWE-667": r"^GO-QUAL-VET-COPYLOCKS$",
    "CWE-772": r"^(GO-QUAL-VET-LOSTCANCEL|GO-QUAL-HTTP-BODY-NOT-CLOSED)$",
    "CWE-561": r"^(GO-QUAL-VET-UNREACHABLE|JS-QUAL-NO-UNREACHABLE|JS-QUAL-NO-DUPE-ELSE-IF)$",
    "CWE-581": r"^(JAVA-QUAL-COR-EQUALS-HASHCODE-001|KT-QUAL-EQUALS-WITHOUT-HASHCODE)$",
    "CWE-1077": r"^(JAVA-QUAL-COR-NAN-EQ-001|JS-QUAL-USE-ISNAN)$",
    "CWE-484": r"^JS-QUAL-NO-FALLTHROUGH$",
    "CWE-1069": r"^KT-QUAL-EMPTY-CATCH$",
    "CWE-390": r"^SB-QUAL-TX-SWALLOW-001$",
}


def quality(rid):
    return [c for c, rx in QUALITY.items() if re.search(rx, rid)]


def classify(rid, title):
    key = f"{rid} | {title}"
    for pat, cwes in PATTERNS:
        if re.search(pat, key):
            return cwes
    return None


FAM = {"338": "330", "331": "330", "328": "327", "326": "327", "916": "327", "759": "327", "760": "327",
       "77": "78", "95": "94", "80": "79", "1004": "614", "776": "611"}


def asvs_reqs(rid, cwes):
    """ASVS 5.0 requirement ids (tools/gap/owasp/asvs5_map.py) this rule implements: rule-id regex when the
    requirement has one, otherwise a shared CWE family."""
    sys.path.insert(0, os.path.join(ROOT, "tools", "gap", "owasp"))
    import asvs5_map
    fam = lambda cs: {FAM.get(c.replace("CWE-", ""), c.replace("CWE-", "")) for c in cs}
    mine = fam(cwes)
    out = []
    for req, (_, rc, rx) in asvs5_map.M.items():
        if (rx and re.search(rx, rid)) or (not rx and mine & fam(rc)):
            out.append(req)
    return out


def main():
    out, missing = {}, []
    for f in sorted(glob.glob(os.path.join(ROOT, "rules", "packs", "*", "*.yaml"))):
        for r in yaml.safe_load(open(f, encoding="utf-8"))["rules"]:
            if r.get("kind") != "security" and r.get("category") != "security":
                q = r.get("cwe") or quality(r["id"])
                if q:
                    out[r["id"]] = {"cwe": q}
                continue
            cwes = r.get("cwe") or classify(r["id"], r.get("title", ""))
            if not cwes:
                missing.append(r["id"])
                continue
            o21 = sorted({CWE[c][0] for c in cwes if c in CWE and CWE[c][0]})
            o25 = sorted({CWE[c][1] for c in cwes if c in CWE and CWE[c][1]})
            asvs = sorted({a for c in cwes if c in CWE for a in CWE[c][2]} | set(asvs_reqs(r["id"], cwes)) | set(r.get("asvs") or []),
                          key=lambda a: [int(x) for x in a[1:].split(".")])
            unknown = [c for c in cwes if c not in CWE]
            if unknown:
                sys.exit(f"{r['id']}: CWE without OWASP/ASVS mapping: {unknown}")
            e = {"cwe": cwes}
            if o21 + o25:
                e["owasp"] = o21 + o25
            if asvs:
                e["asvs"] = asvs
            out[r["id"]] = e
    if missing:
        sys.exit("security rules without a CWE pattern: " + ", ".join(missing))
    p = os.path.join(ROOT, "rules", "data", "taxonomy.yaml")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("# GENERATED by tools/rulegen/taxonomy.py: security rule -> CWE / OWASP Top 10 2021+2025 / ASVS 5.0 sections.\n")
        fh.write("# Applied at load time (internal/rules.ApplyTaxonomy); a rule's own cwe wins; owasp/asvs are merged.\n")
        yaml.dump({"rules": out}, fh, Dumper=NoAlias, sort_keys=True, width=200)
    print(f"{p}: {len(out)} rules")


if __name__ == "__main__":
    main()

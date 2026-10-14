"""OWASP Top 10-style checklists -> how crev rules map to each item.

Each item: id -> (own short label, CWE ids, rule-id regex or None, scope regex or None).
The labels are crev's own paraphrases. Ids follow each project's official numbering.
Coverage: an enabled security rule carries the id in `owasp`, matches the regex, or (when no regex is
given) shares a CWE family. A scope limits the candidate rules, e.g. mobile items only count Android
and Kotlin rules. A None entry means the item cannot be verified from code or config (process,
runtime or design), and it is reported as such.
"""
MOBILE = r"^(ANDROID|KT|TAINT-KT|APPSEC-KT|GRADLE)-"
K8S = r"^KUBE-"
DOCKER = r"^(DOCKER|COMPOSE)-"
LLM = r"LLM-"

PROJECTS = {
    "API Security Top 10 2023": ("https://owasp.org/API-Security/editions/2023/en/0x11-t10/", {
        "API1:2023": ("Object-level authorization on every object access", ["CWE-639", "CWE-284"], r"IDOR|BOLA|OBJECT-LEVEL|OWNERSHIP", None),
        "API2:2023": ("Authentication done right (tokens verified, no hard-coded credentials)", ["CWE-287", "CWE-798", "CWE-347", "CWE-345", "CWE-307"], None, None),
        "API3:2023": ("Object property-level authorization (mass assignment, over-exposure)", ["CWE-915", "CWE-213"], r"MASS-ASSIGN|FIELDS-ALL|SERIALIZE-ALL|DEEP-MERGE", None),
        "API4:2023": ("Bounded resource consumption (sizes, timeouts, pagination, regex)", ["CWE-400", "CWE-770", "CWE-1333", "CWE-730"], None, None),
        "API5:2023": ("Function-level authorization", ["CWE-285", "CWE-862", "CWE-863"], None, None),
        "API6:2023": None,
        "API7:2023": ("No server-side request forgery", ["CWE-918"], None, None),
        "API8:2023": ("Secure configuration (CORS, TLS, errors, headers, debug)", ["CWE-942", "CWE-209", "CWE-497", "CWE-548", "CWE-489", "CWE-16", "CWE-319"], None, None),
        "API9:2023": ("API inventory: no exposed docs/introspection/debug endpoints", [], r"SWAGGER|ACTUATOR|INTROSPECTION|PPROF|DEBUG-ENDPOINT|MANAGEMENT-ENDPOINTS", None),
        "API10:2023": ("Safe consumption of third-party APIs (TLS verified, input validated)", ["CWE-295", "CWE-20"], None, None),
    }),
    "Mobile Top 10 2024": ("https://owasp.org/www-project-mobile-top-10/2023-risks/", {
        "M1:2024": ("No hard-coded credentials or keys in the app", ["CWE-798", "CWE-312", "CWE-321"], None, MOBILE),
        "M2:2024": ("Supply chain: pinned, trusted dependencies and repositories", ["CWE-1104", "CWE-829", "CWE-494", "CWE-1395"], None, MOBILE),
        "M3:2024": ("Authentication/authorization (exported components, biometrics)", ["CWE-287", "CWE-926", "CWE-285"], None, MOBILE),
        "M4:2024": ("Input/output validation (injection, WebView content)", ["CWE-79", "CWE-89", "CWE-78", "CWE-94", "CWE-611", "CWE-22"], None, MOBILE),
        "M5:2024": ("Secure communication (TLS, no cleartext, trust anchors)", ["CWE-319", "CWE-295"], None, MOBILE),
        "M6:2024": ("Privacy controls (no personal data in logs)", ["CWE-532", "CWE-359"], None, MOBILE),
        "M7:2024": ("Binary protections (shrinking/obfuscation, not debuggable)", ["CWE-656", "CWE-489"], None, MOBILE),
        "M8:2024": ("Security misconfiguration (backup, exported, debuggable, cleartext)", ["CWE-530", "CWE-926", "CWE-489", "CWE-16"], None, MOBILE),
        "M9:2024": ("Secure data storage", ["CWE-312", "CWE-922", "CWE-732", "CWE-276"], None, MOBILE),
        "M10:2024": ("Sufficient cryptography", ["CWE-327", "CWE-329", "CWE-330", "CWE-328"], None, MOBILE),
    }),
    "MASVS v2": ("https://mas.owasp.org/MASVS/", {
        "MASVS-STORAGE-1": ("Sensitive data stored securely", ["CWE-312", "CWE-922", "CWE-732"], None, MOBILE),
        "MASVS-STORAGE-2": ("Sensitive data does not leak (backups, logs)", ["CWE-530", "CWE-532"], None, MOBILE),
        "MASVS-CRYPTO-1": ("Strong, current cryptography", ["CWE-327", "CWE-329", "CWE-330", "CWE-328"], None, MOBILE),
        "MASVS-CRYPTO-2": ("Key management (no hard-coded keys)", ["CWE-321", "CWE-798"], None, MOBILE),
        "MASVS-AUTH-1": None,
        "MASVS-AUTH-2": ("Local authentication bound to crypto", [], r"BIOMETRIC", MOBILE),
        "MASVS-AUTH-3": None,
        "MASVS-NETWORK-1": ("Network traffic encrypted", ["CWE-319"], None, MOBILE),
        "MASVS-NETWORK-2": ("Server identity verified (no user CAs, no trust-all)", ["CWE-295"], None, MOBILE),
        "MASVS-PLATFORM-1": ("IPC used securely (exported components, broadcasts)", ["CWE-926", "CWE-927"], None, MOBILE),
        "MASVS-PLATFORM-2": ("WebViews used securely", [], r"WEBVIEW", MOBILE),
        "MASVS-PLATFORM-3": ("UI protects sensitive data (FLAG_SECURE)", [], r"FLAG-SECURE|SCREENSHOT", MOBILE),
        "MASVS-CODE-1": ("Up-to-date platform version required", [], r"MIN-SDK|TARGET-SDK", MOBILE),
        "MASVS-CODE-2": None,
        "MASVS-CODE-3": ("No components with known vulnerabilities", ["CWE-1104", "CWE-1395"], None, MOBILE),
        "MASVS-CODE-4": ("Untrusted input validated and sanitized", ["CWE-89", "CWE-78", "CWE-94", "CWE-611", "CWE-22", "CWE-79"], None, MOBILE),
        "MASVS-RESILIENCE-1": None,
        "MASVS-RESILIENCE-2": None,
        "MASVS-RESILIENCE-3": ("Anti-static-analysis (shrinking/obfuscation on)", [], r"MINIFY|OBFUSCAT", MOBILE),
        "MASVS-RESILIENCE-4": ("Anti-dynamic-analysis (release not debuggable)", [], r"DEBUGGABLE|WEBVIEW-DEBUG", MOBILE),
        "MASVS-PRIVACY-1": None,
        "MASVS-PRIVACY-2": None,
        "MASVS-PRIVACY-3": None,
        "MASVS-PRIVACY-4": None,
    }),
    "Top 10 for LLM Applications 2025": ("https://genai.owasp.org/llm-top-10/", {
        "LLM01:2025": ("Untrusted input concatenated into prompts", [], r"PROMPT-INJECTION|PROMPT-CONCAT|PROMPT-FROM", LLM),
        "LLM02:2025": ("No secrets or personal data sent to the model", [], r"SECRET-IN-PROMPT|PII", LLM),
        "LLM03:2025": ("Model supply chain (no remote code, no pickle loads)", [], r"TRUST-REMOTE-CODE|PICKLE|TORCH-LOAD|UNSAFE-LOAD", LLM),
        "LLM04:2025": ("Model files loaded safely (weights only)", [], r"TORCH-LOAD|PICKLE", LLM),
        "LLM05:2025": ("Model output handled as untrusted (HTML, SQL, shell, eval)", [], r"OUTPUT-TO|OUTPUT-", LLM),
        "LLM06:2025": ("Bounded agency (no shell/eval tools without approval)", [], r"AGENT|TOOL-EXEC|TOOL-SHELL", LLM),
        "LLM07:2025": ("No secrets in system prompts", [], r"SYSTEM-PROMPT-SECRET|SECRET-IN-PROMPT", LLM),
        "LLM08:2025": None,
        "LLM09:2025": None,
        "LLM10:2025": ("Bounded consumption (max tokens, timeouts)", [], r"MAX-TOKENS|TIMEOUT|UNBOUNDED", LLM),
    }),
    "Docker Top 10": ("https://owasp.org/www-project-docker-top-10/", {
        "D01": ("Containers do not run as root", [], r"USER-ROOT|NO-USER|USERNS", DOCKER),
        "D02": ("Patched, pinned base images", [], r"LATEST|DIGEST", DOCKER),
        "D03": ("Network segmentation (no host network, no 0.0.0.0 ports)", [], r"NETWORK-MODE-HOST|PORT-ALL-INTERFACES|PID-HOST|IPC-HOST|UTS-HOST", DOCKER),
        "D04": ("Secure defaults and hardening (no privileged, caps, seccomp)", [], r"PRIVILEGED|CAP-ADD|SECCOMP|DOCKER-SOCKET|SUDO|CGROUP-HOST", DOCKER),
        "D05": ("Security contexts (no-new-privileges, read-only)", [], r"NO-NEW-PRIV|READ-ONLY", DOCKER),
        "D06": ("Secrets not baked into images or env", [], r"SECRET", DOCKER),
        "D07": ("Resource limits", [], r"MEM-LIMIT|CPU-LIMIT|PIDS-LIMIT|RESOURCE", DOCKER),
        "D08": ("Image integrity and origin (checksums, no curl|sh)", [], r"ADD-REMOTE|CURL-PIPE|DIGEST", DOCKER),
        "D09": ("Immutable containers (read-only root filesystem)", [], r"READ-ONLY", DOCKER),
        "D10": ("Logging enabled", [], r"LOGGING", DOCKER),
    }),
    "Kubernetes Top 10 2022": ("https://owasp.org/www-project-kubernetes-top-ten/", {
        "K01:2022": ("Secure workload configuration (securityContext)", [], r"PRIVILEGED|PRIV-ESC|RUN-AS-ROOT|READONLY-ROOT|CAPABILIT|SECCOMP|HOST-PATH", K8S),
        "K02:2022": ("Supply chain (pinned images)", [], r"IMAGE-LATEST|IMAGE-DIGEST|IMAGE-TAG", K8S),
        "K03:2022": ("Least-privilege RBAC", [], r"RBAC|CLUSTER-ADMIN", K8S),
        "K04:2022": None,
        "K05:2022": None,
        "K06:2022": ("Authentication (no anonymous kubelet, token automount)", [], r"ANONYMOUS|AUTOMOUNT|KUBELET-AUTH", K8S),
        "K07:2022": ("Network segmentation (host network/ports)", [], r"HOST-NETWORK|HOST-PID|HOST-IPC|HOST-PORT", K8S),
        "K08:2022": ("Secrets management (no literal secrets in manifests)", [], r"SECRET", K8S),
        "K09:2022": ("Cluster component configuration", [], r"KUBELET|DASHBOARD", K8S),
        "K10:2022": ("Current Kubernetes APIs/components", [], r"DEPRECATED-API", K8S),
    }),
    "Proactive Controls 2024": ("https://top10proactive.owasp.org/", {
        "C1:2024": ("Access control", ["CWE-284", "CWE-285", "CWE-862", "CWE-863", "CWE-639", "CWE-22"], None, None),
        "C2:2024": ("Cryptography to protect data", ["CWE-327", "CWE-326", "CWE-330", "CWE-329", "CWE-319", "CWE-312", "CWE-328"], None, None),
        "C3:2024": ("Validate input and handle exceptions", ["CWE-20", "CWE-89", "CWE-78", "CWE-79", "CWE-94", "CWE-209", "CWE-390", "CWE-611", "CWE-502"], None, None),
        "C4:2024": None,
        "C5:2024": ("Secure-by-default configuration", ["CWE-489", "CWE-16", "CWE-942", "CWE-1004", "CWE-614", "CWE-548", "CWE-497"], None, None),
        "C6:2024": ("Keep components secure", ["CWE-1104", "CWE-1395", "CWE-829", "CWE-494"], None, None),
        "C7:2024": ("Secure digital identities", ["CWE-287", "CWE-798", "CWE-521", "CWE-916", "CWE-347", "CWE-384", "CWE-613"], None, None),
        "C8:2024": ("Leverage browser security features (cookies, CSP, HSTS, SRI)", ["CWE-1004", "CWE-614", "CWE-1275", "CWE-1021", "CWE-693"], None, None),
        "C9:2024": ("Security logging and monitoring", ["CWE-117", "CWE-532", "CWE-778"], None, None),
        "C10:2024": ("Stop server-side request forgery", ["CWE-918"], None, None),
    }),
}

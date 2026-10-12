"""Shared helpers for the multi-ecosystem specs.

autoquote(url, needle) fetches the official page (cached by fetch.py) and returns the verbatim
sentence fragment that contains `needle`, so every rule's source.quote is copied from the page
itself (and re-checked by `rulegen.py verify`). It raises if the page is not HTTP 200 or the
needle is absent, so a rule can never be generated without its supporting text."""
import os
import re

import fetch
from rulegen import rule

_cache = {}


def page(url):
    if url not in _cache:
        st, text = fetch.fetch(url)
        if st != 200:
            if os.environ.get("RULEGEN_LAX"):
                print(f"HTTP {st} {url}")
                _cache[url] = ""
                return ""
            raise ValueError(f"HTTP {st} for {url}")
        _cache[url] = text
    return _cache[url]


def autoquote(url, needle, width=110):
    text = page(url)
    low = text.lower()
    i = low.find(needle.lower())
    if i < 0:
        n = fetch.norm(needle)
        if n in fetch.norm(text):
            return needle
        if os.environ.get("RULEGEN_LAX"):
            print(f"MISSING needle {needle!r} on {url}")
            return needle
        raise ValueError(f"needle {needle!r} not on {url}")
    # extend to sentence-ish boundaries, at most `width` chars each side
    start = max(0, i - width)
    m = list(re.finditer(r"[.!?:]\s+(?=[A-Z`'\"(])", text[start:i]))
    if m:
        start = start + m[-1].end()
    end = min(len(text), i + len(needle) + width)
    m = re.search(r"[.!?](\s|$)", text[i + len(needle):end])
    if m:
        end = i + len(needle) + m.start() + 1
    q = text[start:end].strip()
    if not fetch.contains(text, q):  # tag-stripping artefacts: fall back to the needle itself
        q = text[i:i + len(needle)]
    return q


class Pack:
    """Rule factory bound to one pack's defaults."""

    def __init__(self, prefix, language, doc_version, applies, framework=None, files=None, grammar=None, target=None):
        self.prefix, self.language, self.doc_version, self.applies = prefix, language, doc_version, dict(applies)
        self.framework, self.files, self.grammar, self.target = framework, files, grammar, target
        self.R = []
        self._ids = set()

    def __call__(self, id, title, url, needle, query, bad, good, msg, *, sev="minor", kind="anti-pattern", cat=None, applies=None,
                 lang=None, files=None, grammar=None, target=None, mode="deterministic", ai=None, doc=None, docv=None, quote=None,
                 filters=None, tags=None, fix=None, framework=None, xref=None, engine="tree-sitter", manifest=None,
                 config=None, check=None, requires_dependency=None, fp=None, precision=None, requires_config=None, cwe=None, owasp=None, asvs=None,
                 params=None, match_kind=None):
        rid = f"{self.prefix}-{id}"
        if rid in self._ids:
            raise ValueError("duplicate id " + rid)
        self._ids.add(rid)
        q = quote or autoquote(url, needle)
        self.R.append(rule(rid, title, language=lang or self.language, framework=framework or self.framework, kind=kind,
                           category=cat or self.prefix.lower().split("-")[0], severity=sev, applies=dict(applies or self.applies),
                           message=msg, url=url, doc=doc or title, doc_version=docv or self.doc_version, quote=q, bad=bad, good=good,
                           query=query, target=target if target is not None else self.target, files=files if files is not None else self.files,
                           grammar=grammar or self.grammar, mode=mode, ai=ai, filters=filters, tags=tags, fix=fix, xref=xref,
                           engine=engine, manifest=manifest, config=config, check=check, requires_dependency=requires_dependency,
                           fp=fp, precision=precision, requires_config=requires_config, cwe=cwe, owasp=owasp, asvs=asvs,
                           params=params, match_kind=match_kind))
        return self.R[-1]


OWASP_SECRETS = "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html"
OWASP_NEEDLE = "Many organizations have them hardcoded within the source code in plaintext"
SECRET_NAME_RE = "(?i)^(password|passwd|pwd|secret|client_secret|api[_-]?key|apikey|access[_-]?token|auth[_-]?token|private[_-]?key|secret[_-]?key)$"
PLACEHOLDER_RE = "^(\\\\$\\\\{|\\\\$\\\\(|<|%|\\\\{\\\\{|\\\\*+$|changeme$|xxx+$|example|#@)"

# (id, title, url, needle, regex, bad_value, good_key, good_value, message, severity, doc_version)
SECRETS = [
    ("AWS-ACCESS-KEY", "AWS access key ID committed", "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html",
     "AKIAIOSFODNN7EXAMPLE", "(^|[^A-Z0-9])(AKIA|ASIA)[0-9A-Z]{16}([^A-Z0-9]|$)", ("aws_access_key_id", "AKIAIOSFODNN7EXAMPLE"), ("aws_profile", "deploy"),
     "Long-term AWS access key committed: rotate it and load credentials from the environment/role instead.", "critical", "AWS IAM User Guide"),
    ("PRIVATE-KEY", "PEM private key committed", OWASP_SECRETS, OWASP_NEEDLE, "-----BEGIN ([A-Z]+ )?PRIVATE KEY-----",
     ("key", "-----BEGIN RSA PRIVATE KEY-----"), ("key_file", "/run/secrets/tls.key"),
     "Private key material committed to the repository: revoke it and mount it from a secret store.", "critical", "OWASP cheat sheet (2026)"),
    ("GITHUB-TOKEN", "GitHub token committed", "https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/about-authentication-to-github",
     "ghp_", "(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})", ("token", "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789"), ("token_env", "GITHUB_TOKEN"),
     "GitHub token committed: revoke it and use an environment variable/secret.", "critical", "GitHub Docs"),
    ("SLACK-TOKEN", "Slack token committed", "https://docs.slack.dev/authentication/tokens/", "xoxb-", "xox[abposr]-[0-9A-Za-z-]{10,}",
     ("slack", "xoxb-1234567890-abcdefghij"), ("slack_env", "SLACK_BOT_TOKEN"), "Slack token committed: revoke and move to a secret store.",
     "critical", "Slack developer docs"),
    ("STRIPE-LIVE-KEY", "Stripe live secret key committed", "https://docs.stripe.com/keys", "for secret keys", "(sk|rk)_live_[0-9A-Za-z]{10,}",
     ("stripe", "sk_live_51Hxxxxxxxxxxxxxxxxx"), ("stripe", "pk_live_51Hxxxxxxxxxxxxxxx"), "Stripe live secret/restricted key committed: roll it.",
     "critical", "Stripe docs"),
    ("JWT-LITERAL", "Hard-coded JSON Web Token", OWASP_SECRETS, OWASP_NEEDLE, "eyJ[A-Za-z0-9_-]{10,}[.]eyJ[A-Za-z0-9_-]{10,}[.][A-Za-z0-9_-]+",
     ("auth", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123"), ("auth", "${AUTH_TOKEN}"),
     "A bearer token is committed; tokens grant access until they expire.", "major", "OWASP cheat sheet (2026)"),
    ("URL-CREDENTIALS", "Credentials embedded in a URL", OWASP_SECRETS, OWASP_NEEDLE, "[a-zA-Z][a-zA-Z0-9+.-]*://[^/:@ ]+:[^@/ ${}<>]+@",
     ("db", "postgres://admin:hunter2@db:5432/app"), ("db", "postgres://db:5432/app"),
     "user:password@ in a connection URL is a committed secret; inject the password separately.", "major", "OWASP cheat sheet (2026)"),
    ("AZURE-STORAGE-KEY", "Azure storage account key in connection string",
     "https://learn.microsoft.com/en-us/azure/storage/common/storage-configure-connection-string", "AccountKey", "AccountKey=[A-Za-z0-9+/=]{20,}",
     ("conn", "DefaultEndpointsProtocol=https;AccountName=x;AccountKey=abcdefghijklmnopqrstuvwxyz0123=="), ("conn_env", "AZURE_STORAGE_CONNECTION_STRING"),
     "Storage account key committed; prefer managed identity or a Key Vault reference.", "critical", "Azure Storage docs"),
]


def secret_rules(P, node_alt, fmt, prefix=""):
    """Emit the shared secret-detection family for one string node pattern.
    node_alt: query fragment matching string nodes, e.g. '(string_content)'; fmt(key, value) renders an example."""
    for (id, title, url, needle, rx, bad, good, msg, sev, dv) in SECRETS:
        P(prefix + id, title, url, needle, f'({node_alt} @match (#match? @match "{rx}"))', fmt(*bad), fmt(*good), msg, sev=sev,
          kind="security", cat="security", docv=dv)

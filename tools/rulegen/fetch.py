"""Fetch + cache official doc pages as normalised text (used by rulegen verify)."""
import hashlib, html, os, re, subprocess

CACHE = os.environ.get("RULEGEN_CACHE", "/tmp/rulegen-cache")


def _key(url):
    return os.path.join(CACHE, hashlib.sha1(url.encode(), usedforsecurity=False).hexdigest())


def fetch(url, refresh=False):
    """Returns (status, text). text is tag-stripped, whitespace-collapsed."""
    os.makedirs(CACHE, exist_ok=True)
    k = _key(url)
    if not refresh and os.path.exists(k + ".txt"):
        return int(open(k + ".status", encoding="utf-8").read()), open(k + ".txt", encoding="utf-8").read()
    page = url.split("#")[0]
    r = subprocess.run(["curl", "-sL", "-m", "40", "-A", "Mozilla/5.0 (crev rulegen)", "-o", k + ".raw",
                        "-w", "%{http_code}", page], capture_output=True, text=True)
    status = int(r.stdout or 0)
    raw = open(k + ".raw", "rb").read().decode("utf-8", "replace") if os.path.exists(k + ".raw") else ""
    raw = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"\s+", " ", text)
    open(k + ".txt", "w", encoding="utf-8").write(text)
    open(k + ".status", "w", encoding="utf-8").write(str(status))
    return status, text


def norm(s):
    s = re.sub(r"\s+", " ", s.replace("\u00a0", " ").replace("’", "'").replace("“", '"').replace("”", '"')).strip().lower()
    # tag stripping leaves spaces around inline <code> elements: "const , using ," -> "const, using,"
    s = re.sub(r"(\w)- (\w)", r"\1-\2", s)
    return re.sub(r"\s+([,.;:)])", r"\1", re.sub(r"\(\s+", "(", s))


def contains(text, quote):
    return norm(quote) in norm(text)

"""Shared builder for the simplification packs (simplify_<lang>.py).

Every pack has two parts:
  * collapsible-loop / known-shortcut rules: tree-sitter queries with version ranges, each citing
    the official API doc of the stdlib call that replaces the loop;
  * repo-index rules (detection.engine: index): checks run against the repo-wide index built from
    tree-sitter (symbols, callers, imports, manifest deps). See internal/index/checks.go.

Category `simplification` is advisory: severity is capped at minor and never gates CI. The
`test` category flags non-trivial new logic without a runnable check. Code that is security or
correctness sensitive is excluded by the index checks (and overlapping findings are routed to the
bug/security finding instead)."""
from specs._common import Pack

SIMPLE_NOTE = ("Prefer the simplest code that works. When a shortcut is deliberate, add a `limit:` comment saying how far "
               "it holds (e.g. input size, request rate) and what to switch to beyond that.")


def simp(prefix, language, doc_version, applies):
    return Pack(prefix, language, doc_version, applies)


def index_rules(P, ex, docs):
    """ex: check -> (bad, good[, config]); docs: check -> (url, needle, doc title)."""
    meta = {
        "unused-export": ("New export with no references", "minor", "anti-pattern", "simplification", "deterministic",
                          "YAGNI: nothing in the repo uses this new export. Delete it or make it private until a caller exists.", None),
        "unused-flag": ("Flag defined but never read", "minor", "anti-pattern", "simplification", "deterministic",
                        "The option is parsed but its value is never used. Remove the flag (and its docs) or wire it up.", None),
        "unused-file": ("New file nothing imports", "minor", "anti-pattern", "simplification", "deterministic",
                        "No import resolves to this new file and no other file mentions it. Delete it or import it where it is needed.", None),
        "middle-man": ("Pass-through module (middle man)", "minor", "anti-pattern", "simplification", "deterministic",
                       "Every function here only forwards its arguments to another object. Call the target directly, or use the language's delegation feature.", None),
        "nested-loop-no-limit-note": ("Nested loop comparing elements is O(n·m)", "minor", "anti-pattern", "simplification", "deterministic",
                                    "Look one side up in a set/map instead (O(n+m)). If both collections stay small, keep the loop and add a comment noting the size limit and the upgrade path, e.g. `limit: both lists < 100 items; switch to a set if they grow`.", None),
        "limit-note-incomplete": ("Shortcut comment lacks its limit or upgrade path", "info", "best-practice", "simplification", "deterministic",
                                "Say how far the shortcut holds (a concrete limit such as input size or request rate) and what to switch to beyond it.", None),
        "global-lock-no-limit-note": ("Package-level lock serialises every caller", "minor", "anti-pattern", "simplification", "deterministic",
                                    "One global lock is fine at low concurrency. Add a comment noting the load it is sized for and the finer-grained alternative (per-key locks, sharding, sync.Map), e.g. `limit: fine below ~1k req/s; shard per key beyond that`.", None),
        "duplicate-helper": ("Duplicates an existing helper", "minor", "anti-pattern", "simplification", "ai-confirm",
                             "The repo already has a function with the same normalized body. Call the existing helper instead of adding a copy.",
                             "Given the index evidence (an existing function with an identical normalized body), is this new function a redundant copy that could call the existing helper instead (not intentionally separate, e.g. different packages that must not depend on each other)?"),
        "call-site-patches": ("Same guard patched into many call sites", "minor", "anti-pattern", "simplification", "ai-confirm",
                              "The same guard was added before several calls to one function. Put the check inside that function once.",
                              "Do these new guards all protect the same callee from the same bad input, so a single check inside the callee would replace them (without changing behaviour for other callers)?"),
        "test-missing": ("Non-trivial new logic without a runnable check", "minor", "best-practice", "test", "deterministic",
                         "This new function has branches but no test references it. Add a small runnable check (unit test, doctest, example) that pins its behaviour.", None),
    }
    for check, spec in ex.items():
        bad, good = spec[0], spec[1]
        cfg = spec[2] if len(spec) > 2 else None
        title, sev, kind, cat, mode, msg, ai = meta[check]
        url, needle, doc = docs[check]
        P("IDX-" + check.upper(), title, url, needle, None, bad, good, msg, fix=SIMPLE_NOTE, sev=sev, kind=kind, cat=cat,
          mode=mode, ai=ai, doc=doc, engine="index", check=check, config=cfg, tags=["simplify", "index"])


def helper(P, id, title, url, needle, names, api, bad, good, *, applies=None, uses=None, loop=True, dep=None, doc=None, max_lines=40, name_re=None,
           body_re=None, fp=None):
    """Hand-written helper that a stdlib / native / installed-dependency API replaces (ai-confirm).
    body_re: the body must match (shape guard); methods never count (a type's own API)."""
    cfg = {"names": names, "api": api, "uses": uses or [api.split("(")[0]], "requires_loop": loop, "max_lines": max_lines}
    if body_re:
        cfg["body_re"] = body_re
    if name_re:
        cfg["name_re"] = name_re
    if dep:
        cfg["dependency"] = dep
    src = "installed dependency " + dep if dep else "standard library"
    P("HELPER-" + id, title, url, needle, None, bad, good,
      f"This hand-written helper re-implements {api} from the {src}. Use it directly and delete the helper.", fix=SIMPLE_NOTE,
      sev="minor", kind="modernization", cat="simplification", mode="ai-confirm", applies=applies, doc=doc or api,
      ai=f"Does this function behave the same as {api} for every input its callers pass (same result, ordering and edge cases), so it can be replaced by {api}?",
      engine="index", check="helper-replacement", config=cfg, requires_dependency=dep, tags=["simplify", "index", "stdlib" if not dep else "dependency"], fp=fp)


def loop(P, id, title, url, needle, query, bad, good, msg, *, applies=None, mode="deterministic", ai=None, filters=None, doc=None, kind="modernization", fp=None):
    P("LOOP-" + id, title, url, needle, query, bad, good, msg, fix=SIMPLE_NOTE, sev="minor", kind=kind, cat="simplification",
      applies=applies, mode=mode, ai=ai, filters=filters, doc=doc, tags=["simplify", "collapsible-loop"], **({"fp": fp} if fp else {}))

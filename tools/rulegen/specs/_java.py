"""Java query/rule helpers."""
from rulegen import rule

API = "https://docs.oracle.com/en/java/javase/25/docs/api/java.base/"
JDK25 = "JDK 25 API (javadoc, current LTS; unchanged in 26/27)"


def api(path):
    return API + path + ".html"


def args(n):
    if n is None:
        return ""
    if n == 0:
        return ' arguments: (argument_list) @args (#eq? @args "()")'
    return " arguments: (argument_list . " + " . ".join(["(_)"] * n) + " .)"


def static_call(cls, method, n=None):
    a = args(n)
    pred = ""
    if n == 0:
        a = " arguments: (argument_list) @args"
        pred = ' (#eq? @args "()")'
    return f'((method_invocation object: (identifier) @c name: (identifier) @m{a}) @match (#eq? @c "{cls}") (#eq? @m "{method}"){pred})'


def call(method, n=None, regex=False):
    a, pred = args(n), ""
    if n == 0:
        a, pred = " arguments: (argument_list) @args", ' (#eq? @args "()")'
    op = "match" if regex else "eq"
    return f'((method_invocation name: (identifier) @m{a}) @match (#{op}? @m "{method}"){pred})'


def new(cls, n=None):
    a = args(n)
    return f'((object_creation_expression type: (type_identifier) @t{a}) @match (#eq? @t "{cls}"))'


def imp(regex):
    return f'((import_declaration) @match (#match? @match "{regex}"))'


def field(cls, regex):
    return f'((field_access object: (identifier) @c field: (identifier) @f) @match (#eq? @c "{cls}") (#match? @f "{regex}"))'


def J(id, title, **kw):
    kw.setdefault("language", "java")
    kw.setdefault("applies", {"java": ">=8"})
    kw.setdefault("doc_version", JDK25)
    return rule(id, title, **kw)


def cls(body, imports=""):
    """Wrap statements in a compilable-looking class for examples."""
    return f"{imports}class Example {{\n  void run() throws Exception {{\n    {body}\n  }}\n}}\n"

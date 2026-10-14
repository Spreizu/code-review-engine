"""Accessibility (WCAG 2.0/2.1/2.2) rules for CSS, HTML, Vue templates, Angular templates and JSX.

Every rule tags the WCAG success criteria it checks (`wcag`, level and version come from
internal/rules/wcag.go); best-practice-only checks carry the a11y-best-practice tag. Sources are
W3C WCAG 2.2 Understanding documents and Techniques (failures F*, CSS techniques C*), WAI-ARIA 1.2
/ APG and MDN; axe-core, eslint-plugin-jsx-a11y, eslint-plugin-vuejs-accessibility,
angular-eslint template rules and stylelint plugins are cross-references only."""
from specs._common import Pack

WAI = "https://www.w3.org/WAI/WCAG22/"
U = WAI + "Understanding/"
F = WAI + "Techniques/failures/"
CSSP = Pack("CSS", "css", "WCAG 2.2 (W3C Recommendation)", {"any": "*"})

FOCUS_REPLACEMENT = r"node.lacks_re:(?i)(box-shadow|(^|[;{\s])color|border(-[a-z-]+)?|background(-color)?|text-decoration(-[a-z-]+)?|text-underline-offset|filter|transform)\s*:|outline\s*:\s*(auto|thin|medium|thick|[1-9]|\.\d|0?\.\d*[1-9])|outline-style\s*:\s*(solid|dotted|dashed|double|groove|ridge|inset|outset|auto)"
OUTLINE_GONE = r"node.has_re:(?i)(^|[;{\s])outline(-style)?\s*:\s*(none|0(px)?)\s*(!important\s*)?(;|\}|$)|outline-color\s*:\s*transparent|outline-width\s*:\s*0(px)?\s*(;|\}|$)"


def css(id, title, src, query, bad, good, msg, wcag=None, **kw):
    kw.setdefault("sev", "major")
    kw.setdefault("kind", "best-practice")
    tags = list(kw.pop("tags", None) or [])
    if wcag is None:
        tags.append("a11y-best-practice")
    url, needle, doc = src
    return CSSP(id, title, url, needle, query, bad, good, msg, cat="accessibility", doc=doc, docv="WCAG 2.2", wcag=wcag, tags=tags or None, **kw)


# ---- CSS: focus visibility (2.4.7) ----------------------------------------------------------------
css("FOCUS-OUTLINE-REMOVED", "Focus outline removed without a replacement style",
    (F + "F78", "outline", "WCAG failure F78: removing the visual focus indicator"),
    "((rule_set (selectors) @s (block) @b) @match (#match? @s \":focus([^-a-zA-Z]|$)\"))",
    "a:focus {\n  outline: none;\n}\n",
    "a:focus {\n  outline: none;\n  box-shadow: 0 0 0 3px #1a73e8;\n}\n\nbutton:focus:not(:focus-visible) {\n  outline: none;\n}\n",
    "This removes the keyboard focus indicator and nothing replaces it, so keyboard users cannot see where they are: keep an outline or add another visible focus style.",
    wcag=["2.4.7"], filters=[OUTLINE_GONE.replace("node.", "cap.", 1).replace("cap.has_re:", "cap.has_re:b:", 1),
                             FOCUS_REPLACEMENT.replace("node.lacks_re:", "cap.lacks_re:b:", 1),
                             r"cap.lacks_re:s::not\(\s*:focus-visible\s*\)", r"file.lacks_re::focus-visible"],
    xref=["axe:focus-order-semantics", "stylelint:a11y/no-outline-none"],
    fp=[{"code": "a:focus {\n  outline: none;\n}\n\na:focus-visible {\n  outline: 2px solid #1a73e8;\n}\n", "note": ":focus-visible restores the ring for keyboard users"}])
css("FOCUS-VISIBLE-OUTLINE-REMOVED", ":focus-visible rule that removes the focus indicator",
    (F + "F78", "outline", "WCAG failure F78: removing the visual focus indicator"),
    "((rule_set (selectors) @s (block) @b) @match (#match? @s \":focus-visible\"))",
    "button:focus-visible {\n  outline: 0;\n}\n",
    "button:focus-visible {\n  outline: 2px solid #1a73e8;\n  outline-offset: 2px;\n}\n\nbutton:focus:not(:focus-visible) {\n  outline: none;\n}\n",
    ":focus-visible is exactly when keyboard users need the indicator: removing it here hides focus from them.",
    wcag=["2.4.7"], filters=[OUTLINE_GONE.replace("node.has_re:", "cap.has_re:b:", 1), FOCUS_REPLACEMENT.replace("node.lacks_re:", "cap.lacks_re:b:", 1),
                             r"cap.lacks_re:s::not\(\s*:focus-visible\s*\)"],
    xref=["stylelint:a11y/no-outline-none"])
css("OUTLINE-REMOVED-ON-CONTROLS", "Outline removed from links/buttons/inputs in a stylesheet without any focus style",
    (F + "F78", "outline", "WCAG failure F78: removing the visual focus indicator"),
    "((rule_set (selectors) @s (block) @b) @match (#match? @s \"^\\\\s*(\\\\*|a|button|input|select|textarea|summary|\\\\[tabindex[^\\\\]]*\\\\])(\\\\s*,\\\\s*(\\\\*|a|button|input|select|textarea|summary|\\\\[tabindex[^\\\\]]*\\\\]))*\\\\s*$\"))",
    "button,\na {\n  outline: none;\n}\n",
    "button,\na {\n  outline: none;\n}\n\nbutton:focus-visible,\na:focus-visible {\n  outline: 2px solid #1a73e8;\n}\n",
    "Outlines are removed from interactive elements and this stylesheet defines no focus style: keyboard focus may be invisible (check that another stylesheet restores it).",
    wcag=["2.4.7"], filters=[OUTLINE_GONE.replace("node.has_re:", "cap.has_re:b:", 1), FOCUS_REPLACEMENT.replace("node.lacks_re:", "cap.lacks_re:b:", 1), r"file.lacks_re::focus"],
    mode="ai-confirm", ai="Is there no other stylesheet or component style that gives these elements a visible focus indicator?",
    xref=["stylelint:a11y/no-outline-none"])

# ---- CSS: text resizing, spacing, presentation ---------------------------------------------------
css("FONT-SIZE-VIEWPORT-ONLY", "font-size set only in viewport units",
    (F + "F94", "viewport units", "WCAG failure F94: text sized with viewport units"),
    "((declaration (property_name) @p) @match (#match? @p \"^(?i)font-size$\"))",
    ".title {\n  font-size: 5vw;\n}\n", ".title {\n  font-size: clamp(1.5rem, 1rem + 3vw, 3rem);\n}\n\n.lead {\n  font-size: 1.25rem;\n}\n",
    "Text sized purely in viewport units does not grow with browser zoom: combine it with rem/em (for example clamp() or calc()).",
    wcag=["1.4.4"], filters=[r"node.has_re:(?i):\s*-?\d*\.?\d+(vw|vh|vmin|vmax|vi|vb|svw|svh|lvw|lvh|dvw|dvh)\s*(!important\s*)?;?$"],
    xref=["stylelint:a11y/font-size-is-readable"])
css("ROOT-FONT-SIZE-PX", "Root font size fixed in px",
    ("https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/font-size", "user", "MDN: font-size"),
    "((rule_set (selectors) @s (block (declaration (property_name) @p) @match)) (#match? @s \"^\\\\s*(html|:root)\\\\s*$\") (#match? @p \"^(?i)font-size$\"))",
    "html {\n  font-size: 10px;\n}\n", "html {\n  font-size: 62.5%;\n}\n\n.card {\n  font-size: 14px;\n}\n",
    "A px root size ignores the reader's browser font-size setting, and every rem on the page with it: use a percentage or leave the default.",
    filters=[r"node.has_re:(?i):\s*\d*\.?\d+px\b"], sev="minor")
css("TEXT-JUSTIFIED", "Justified text",
    (U + "visual-presentation.html", "Text is not justified", "Understanding SC 1.4.8 Visual Presentation"),
    "((declaration (property_name) @p (plain_value) @v) @match (#match? @p \"^(?i)text-align$\") (#match? @v \"^(?i)justify$\"))",
    "article p {\n  text-align: justify;\n}\n", "article p {\n  text-align: start;\n}\n",
    "Justified text creates uneven word gaps (\"rivers\") that make reading hard for people with dyslexia: align to the start edge.",
    wcag=["1.4.8"], sev="minor")
css("LINE-HEIGHT-BELOW-1-5", "Body text line height below 1.5",
    (U + "visual-presentation.html", "space-and-a-half", "Understanding SC 1.4.8 Visual Presentation"),
    "((rule_set (selectors) @s (block (declaration (property_name) @p [(float_value) (integer_value)] @v) @match)) (#match? @s \"^\\\\s*(body|p|article|main|li)(\\\\s*,\\\\s*(body|p|article|main|li))*\\\\s*$\") (#match? @p \"^(?i)line-height$\") (#match? @v \"^(0?\\\\.\\\\d+|1(\\\\.[0-4]\\\\d*)?)$\"))",
    "body {\n  line-height: 1.2;\n}\n", "body {\n  line-height: 1.5;\n}\n\nh1 {\n  line-height: 1.1;\n}\n",
    "Paragraph text needs at least 1.5 line spacing to stay readable for people with low vision or dyslexia (WCAG AAA).",
    wcag=["1.4.8"], sev="minor")
css("TEXT-CLIPPED-FIXED-HEIGHT", "Text container with fixed px height and hidden overflow",
    (F + "F104", "overflow", "WCAG failure F104: content clipped when text spacing is adjusted"),
    "((rule_set (block) @b) @match)",
    ".card-title {\n  height: 40px;\n  overflow: hidden;\n}\n", ".card-title {\n  min-height: 40px;\n}\n",
    "When readers increase line height or letter spacing, text in a fixed-height box with hidden overflow is cut off: use min-height or let it grow.",
    wcag=["1.4.12"], filters=[r"cap.has_re:b:(?i)(^|[;{\s])(height|max-height)\s*:\s*\d+(\.\d+)?px", r"cap.has_re:b:(?i)overflow(-y)?\s*:\s*(hidden|clip)",
                              r"cap.lacks_re:b:(?i)object-fit|aspect-ratio|background-image|position\s*:\s*(absolute|fixed)|text-overflow|line-clamp"],
    mode="ai-confirm", ai="Does this box hold text (not an image, icon, scroll area or decorative element) that would be cut off if line height or letter spacing increase?")
css("TEXT-DECORATION-BLINK", "Blinking text",
    (F + "F4", "text-decoration:blink", "WCAG failure F4: text-decoration:blink"),
    "((declaration (property_name) @p) @match (#match? @p \"^(?i)text-decoration(-line)?$\"))",
    ".sale {\n  text-decoration: blink;\n}\n", ".sale {\n  text-decoration: underline;\n}\n",
    "Blinking content cannot be paused and distracts people with attention or vestibular disorders: remove it.",
    wcag=["2.2.2"], filters=[r"node.has_re:(?i)\bblink\b"])
css("REDUCED-MOTION-MISSING", "Animations without a prefers-reduced-motion alternative",
    (WAI + "Techniques/css/C39", "prefers-reduced-motion", "WCAG technique C39: prefers-reduced-motion"),
    "(keyframes_statement (keyframes_name)) @match",
    "@keyframes slide {\n  from {\n    transform: translateX(-100%);\n  }\n  to {\n    transform: none;\n  }\n}\n",
    "@keyframes slide {\n  from {\n    transform: translateX(-100%);\n  }\n  to {\n    transform: none;\n  }\n}\n\n@media (prefers-reduced-motion: reduce) {\n  * {\n    animation: none !important;\n  }\n}\n",
    "Motion here has no reduced-motion fallback: wrap it in @media (prefers-reduced-motion: no-preference) or disable it under reduce.",
    wcag=["2.3.3"], sev="minor", filters=[r"file.lacks_re:prefers-reduced-motion", r"node.has_re:(?i)transform|translate|rotate|scale|left|top|right|bottom|margin|width|height|background-position"],
    mode="ai-confirm", ai="Does the project not handle prefers-reduced-motion elsewhere (global stylesheet, JS, framework setting) for this animation?",
    xref=["stylelint:a11y/media-prefers-reduced-motion"])
css("SMALL-TARGET", "Interactive element sized below 24x24 px",
    (U + "target-size-minimum.html", "at least 24 by 24 CSS pixels", "Understanding SC 2.5.8 Target Size (Minimum)"),
    "((rule_set (selectors) @s (block) @b) @match (#match? @s \"(^|[\\\\s,>+~])(button|a|input|select|summary|\\\\.(btn|button|icon-button|close)[\\\\w-]*|\\\\[role=[\\\"']?button)\"))",
    ".icon-button {\n  width: 16px;\n  height: 16px;\n}\n", ".icon-button {\n  width: 16px;\n  height: 16px;\n  padding: 4px;\n}\n\n.icon-button {\n  width: 24px;\n  height: 24px;\n}\n",
    "This control is smaller than 24x24 CSS px: enlarge it (padding counts) or keep enough spacing around it.",
    wcag=["2.5.8"], filters=[r"cap.has_re:b:(?i)(^|[;{\s])(width|min-width)\s*:\s*(1?\d|2[0-3])(\.\d+)?px", r"cap.has_re:b:(?i)(^|[;{\s])(height|min-height)\s*:\s*(1?\d|2[0-3])(\.\d+)?px",
                             r"cap.lacks_re:b:(?i)padding(-[a-z]+)?\s*:\s*[^0;]|display\s*:\s*inline\b|box-sizing\s*:\s*content-box"],
    mode="ai-confirm", ai="Is this an interactive target (not inline text link, not visually hidden) whose clickable area really stays below 24x24 px without enough spacing to neighbours?")
css("GENERATED-CONTENT-TEXT", "Meaningful text inserted with ::before/::after",
    (F + "F87", ":before", "WCAG failure F87: inserting non-decorative content with :before/:after"),
    "((rule_set (selectors (pseudo_element_selector (tag_name) @pe .)) (block (declaration (property_name) @p (string_value) @v) @match)) (#match? @pe \"^(?i)(before|after)$\") (#match? @p \"^(?i)content$\") (#match? @v \"[A-Za-z]{3,}\"))",
    ".price-old::after {\n  content: \"Sale ends today\";\n}\n",
    ".price-old::after {\n  content: \"\";\n}\n\n.icon-check::before {\n  content: \"\\\\f00c\";\n}\n\nq::before {\n  content: open-quote;\n}\n",
    "Text added by CSS is not part of the document: it is lost without styles, may be skipped by assistive technology and cannot be selected or translated. Put information in the HTML.",
    wcag=["1.3.1"], sev="minor", filters=[r"node.lacks_re:(?i)content\s*:\s*[\x22'][^\x22']*[\x22']\s*/"],
    mode="ai-confirm", ai="Does the generated text carry information (not decoration, a visual separator, a quote mark or a label already present in the HTML)?")
css("LOW-CONTRAST", "Text colour contrast below 4.5:1 (3:1 for large text)",
    (U + "contrast-minimum.html", "contrast ratio of at least 4.5:1", "Understanding SC 1.4.3 Contrast (Minimum)"),
    "(rule_set (block (declaration (property_name) @p)) (#match? @p \"^(?i)color$\")) @match",
    ".hint {\n  color: #999;\n  background-color: #fff;\n}\n",
    ".hint {\n  color: #595959;\n  background-color: #fff;\n}\n\n.hero {\n  color: #777;\n  background: #fff url(hero.png);\n}\n\n.big {\n  color: #888;\n  background: #fff;\n  font-size: 32px;\n}\n",
    "The text and background colours declared here fall below the WCAG AA minimum contrast (4.5:1, or 3:1 for large text): darken the text or lighten the background.",
    wcag=["1.4.3"], filters=["css.contrast_lt:AA"], xref=["axe:color-contrast"])
css("ORIENTATION-LOCK", "Styles restricted to one screen orientation",
    (U + "orientation.html", "Content does not restrict its view and operation to a single display orientation", "Understanding SC 1.3.4 Orientation"),
    "((feature_query (feature_name) @n (plain_value) @v) @match (#match? @n \"^(?i)orientation$\") (#match? @v \"^(?i)(landscape|portrait)$\"))",
    "@media (orientation: landscape) {\n  .app {\n    display: none;\n  }\n}\n",
    ".side {\n  width: 16rem;\n}\n@media (min-width: 40em) {\n  .side {\n    width: 20rem;\n  }\n}\n",
    "Locking layout to landscape or portrait fails when the device is the other way (or the user cannot rotate it): keep the same content available in both orientations.",
    wcag=["1.3.4"], sev="major", mode="ai-confirm",
    ai="Does this media query hide or block essential content in the other orientation (rather than only rearranging a layout that still works when rotated)?",
    xref=["axe:css-orientation-lock", "sonar:css:S7923"])
css("LOW-CONTRAST-ENHANCED", "Text colour contrast below 7:1 (4.5:1 for large text)",
    (U + "contrast-enhanced.html", "contrast ratio of at least 7:1", "Understanding SC 1.4.6 Contrast (Enhanced)"),
    "(rule_set (block (declaration (property_name) @p)) (#match? @p \"^(?i)color$\")) @match",
    ".hint {\n  color: #666;\n  background-color: #fff;\n}\n",
    ".hint {\n  color: #444;\n  background-color: #fff;\n}\n\n.low {\n  color: #999;\n  background: #fff;\n}\n",
    "The text and background colours declared here meet AA but not the enhanced AAA contrast (7:1, or 4.5:1 for large text).",
    wcag=["1.4.6"], sev="minor", filters=["css.contrast_lt:AAA", "css.contrast_ge:AA"], xref=["axe:color-contrast-enhanced"])


# ---- markup: HTML documents + Angular templates (html), Vue templates (vue), JSX (jsx) -------------
import re as _re

HTMLP = Pack("HTML", "html", "WCAG 2.2 / HTML Living Standard", {"any": "*"})
VUEP = Pack("VUE", "vue", "WCAG 2.2 / Vue 3 templates", {"vue": ">=2.0"}, framework="vue", target="template")
JSXP = Pack("JS", "jsx", "WCAG 2.2 / JSX", {"any": "*"})
NUXTUIP = Pack("NUXTUI", "vue", "WCAG 2.2 / Nuxt UI 4", {"nuxt-ui": ">=3.0"}, framework="nuxt-ui", target="template")
ANY = "[a-zA-Z][a-zA-Z0-9-]*"


def hq(tags):
    return "\n".join(f'(({k} (tag_name) @t) @match (#match? @t "^(?i)({tags})$"))' for k in ("start_tag", "self_closing_tag"))


def vq(tags):  # Vue: case-sensitive so components (Img, Button) are not taken for HTML elements
    return "\n".join(f'(({k} (tag_name) @t) @match (#match? @t "^({tags})$"))' for k in ("start_tag", "self_closing_tag"))


def jq(tags):
    return "\n".join(f'(({k} name: (identifier) @t) @match (#match? @t "^({tags})$"))' for k in ("jsx_opening_element", "jsx_self_closing_element"))


def page(body, lang=' lang="en"', main=True):
    if main:
        body = f"<main>\n{body}\n</main>"
    return f"<!DOCTYPE html>\n<html{lang}>\n<head><title>Orders</title></head>\n<body>\n{body}\n</body>\n</html>\n"


def vue_tpl(body):
    return "<template>\n  <main>\n" + "\n".join("    " + l for l in body.split("\n")) + "\n  </main>\n</template>\n"


EVENTS = ["click", "keydown", "keyup", "keypress", "mouseover", "mouseout", "mouseenter", "focus", "blur"]
VOID = "img|input|br|hr|area|source|track|meta|link|col|embed|wbr"


def to_vue(h):
    for e in EVENTS:
        h = _re.sub(rf'\bon{e}="(\w+)\(\)"', rf'@{e}="\1"', h)
    return h


def to_jsx(h):
    h = _re.sub(r"<!--.*?-->", "", h)
    for a, b in (("class", "className"), ("for", "htmlFor"), ("tabindex", "tabIndex"), ("autocomplete", "autoComplete"),
                 ("autoplay", "autoPlay"), ("readonly", "readOnly"), ("viewbox", "viewBox")):
        h = _re.sub(rf'(\s){a}(=|\s|>)', rf"\1{b}\2", h)
    for e in EVENTS:
        cam = "on" + {"keydown": "KeyDown", "keyup": "KeyUp", "keypress": "KeyPress", "mouseover": "MouseOver", "mouseout": "MouseOut",
                      "mouseenter": "MouseEnter"}.get(e, e.capitalize())
        h = _re.sub(rf'\bon{e}="(\w+)\(\)"', rf"{cam}={{\1}}", h)
    h = _re.sub(rf"<({VOID})\b([^>]*?)\s*/?>", r"<\1\2 />", h)
    return "export function View() {\n  return (\n    <main>\n" + "\n".join("      " + l for l in h.split("\n")) + "\n    </main>\n  );\n}\n"


# per-syntax linter suites that test the same check (jsx-a11y, vuejs-accessibility): cross-reference
# and local fixtures for the JSX / Vue variants
SUITES = {
    "ARIA-INVALID-ROLE": ("aria-role", "aria-role"), "ARIA-INVALID-ATTRIBUTE": ("aria-props", "aria-props"),
    "ARIA-REQUIRED-ATTRIBUTE": ("role-has-required-aria-props", "role-has-required-aria-props"),
    "AUTOCOMPLETE-INVALID": ("autocomplete-valid", None), "EMPTY-HEADING": ("heading-has-content", "heading-has-content"),
    "LANG-INVALID": ("lang", None), "MOUSE-WITHOUT-KEYBOARD": ("mouse-events-have-key-events", "mouse-events-have-key-events"),
    "IMG-REDUNDANT-ALT": ("img-redundant-alt", None), "MARQUEE-OR-BLINK": ("no-distracting-elements", "no-distracting-elements"),
    "AMBIGUOUS-LINK-TEXT": ("anchor-ambiguous-text", None), "POSITIVE-TABINDEX": (None, "tabindex-no-positive"),
    "IFRAME-WITHOUT-TITLE": (None, "iframe-has-title"), "IMG-WITHOUT-ALT": (None, "alt-text"),
    "LINK-WITHOUT-NAME": (None, "anchor-has-content"), "CONTROL-WITHOUT-LABEL": (None, "form-control-has-label"),
    "VIDEO-WITHOUT-CAPTIONS": ("media-has-caption", "media-has-caption"),
}


def mk(id, title, src, tags, bad, good, msg, wcag=None, *, variants=("html", "vue", "jsx"), filters=(), extra=None, query=None, **kw):
    """One accessibility check emitted for HTML/Angular (html), Vue templates and JSX. bad/good are
    HTML bodies converted per syntax; extra = {variant: {"bad"/"good"/"fp"/"filters"/"mode"/"ai": ...}}."""
    url, needle, doc = src
    kw.setdefault("sev", "major")
    kw.setdefault("kind", "best-practice")
    tags_ = list(kw.pop("rtags", None) or [])
    if wcag is None:
        tags_.append("a11y-best-practice")
    for v in variants:
        x = dict((extra or {}).get(v, {}))
        k = dict(kw)
        for key in ("mode", "ai", "sev", "fp", "xref"):
            if key in x:
                k[key] = x.pop(key)
        f = list(filters) + list(x.pop("filters", []))
        jx, vx = SUITES.get(id, (None, None))
        extra_x = {"jsx": jx and "jsx-a11y:" + jx, "vue": vx and "vuejs-accessibility:" + vx}.get(v)
        if extra_x and extra_x not in (k.get("xref") or []):
            k["xref"] = [extra_x] + list(k.get("xref") or [])
        if v == "html":
            P_, q, b, g = HTMLP, query or hq(tags), page(x.get("bad", bad), main=x.get("main", True)), page(x.get("good", good))
        elif v == "vue":
            P_, q, b, g = VUEP, query or vq(tags), vue_tpl(to_vue(x.get("bad", bad))), vue_tpl(to_vue(x.get("good", good)))
            f = ["markup.native"] + f
        elif v == "nuxtui":
            P_, q, b, g = NUXTUIP, vq(tags), vue_tpl(x["bad"]), vue_tpl(x["good"])
        else:
            P_, q, b, g = JSXP, query or jq(tags), to_jsx(x.get("bad", bad)), to_jsx(x.get("good", good))
            f = ["markup.native"] + f
        P_(id, title, url, needle, q, b, g, msg, cat="accessibility", doc=doc, docv="WCAG 2.2", wcag=wcag, tags=tags_ or None,
           filters=f or None, **k)


NAMES = "aria-label|aria-labelledby|title"
U412 = (U + "name-role-value.html", "name and role can be programmatically determined", "Understanding SC 4.1.2 Name, Role, Value")
U111 = (U + "non-text-content.html", "All non-text content that is presented to the user has a text alternative", "Understanding SC 1.1.1 Non-text Content")
U131 = (U + "info-and-relationships.html", "Information, structure, and relationships conveyed through presentation can be programmatically determined",
        "Understanding SC 1.3.1 Info and Relationships")
ARIA = ("https://www.w3.org/TR/wai-aria-1.2/", "Required States and Properties", "WAI-ARIA 1.2")
SVG = '<svg viewbox="0 0 16 16"><path d="M0 0h16v16H0z"></path></svg>'

mk("BUTTON-WITHOUT-NAME", "Button without an accessible name", U412, "button",
   f'<button type="button">{SVG}</button>',
   f'<button type="button" aria-label="Close">{SVG}</button>\n<button type="submit">Save</button>\n<button type="button"><img src="x.png" alt="Close"></button>',
   "Screen readers announce this button as just \"button\": give it visible text, aria-label or aria-labelledby.",
   ["4.1.2"], filters=["markup.not_hidden", "markup.no_text", f"markup.lacks_attr:{NAMES}", "markup.unlabelled", r"node.lacks_re:\brole\s*=\s*[\x22']?(presentation|none)\b"],
   extra={"vue": {"fp": [{"code": vue_tpl('<button type="button" :aria-label="t(\'close\')"><XIcon /></button>\n<button type="button"><Icon name="x" /></button>\n<button v-t="\'save\'" type="button"></button>'), "note": "bound name, components and v-t may supply the name"}]},
          "jsx": {"fp": [{"code": to_jsx('<button type="button">{label}</button>').replace("{label}", "{label}"), "note": "expression child"}]}},
   xref=["axe:button-name"])
mk("LINK-WITHOUT-NAME", "Link without an accessible name", (U + "link-purpose-in-context.html", "The purpose of each link can be determined from the link text alone", "Understanding SC 2.4.4 Link Purpose (In Context)"),
   "a", f'<a href="/cart">{SVG}</a>', f'<a href="/cart" aria-label="Cart">{SVG}</a>\n<a href="/help">Help</a>',
   "This link has no text, so assistive technology announces only \"link\" (or the URL): add link text or aria-label.",
   ["2.4.4", "4.1.2"], variants=("vue",), filters=["markup.not_hidden", "markup.has_attr:href", "markup.no_text", f"markup.lacks_attr:{NAMES}"], xref=["axe:link-name"])
mk("CONTROL-WITHOUT-LABEL", "Form field without a label", (U + "labels-or-instructions.html", "Labels or instructions are provided when content requires user input", "Understanding SC 3.3.2 Labels or Instructions"),
   "input|select|textarea", '<input type="text" id="q" name="q">',
   '<label for="q">Search</label>\n<input type="text" id="q" name="q">\n<label>Name <input type="text" name="n"></label>\n<input type="email" aria-label="Email">\n<input type="hidden" name="t">\n<input type="submit" value="Go">',
   "Nothing labels this field, so screen-reader users hear only its type: add a <label for>, wrap it in <label>, or use aria-label/aria-labelledby.",
   ["1.3.1", "3.3.2", "4.1.2"], filters=["markup.not_hidden", r"node.lacks_re:(?i)\btype\s*=\s*[\x22']?(hidden|submit|reset|button|image)\b", r"node.lacks_re:(:|\[|v-bind:)type\b", "markup.unlabelled", r"node.lacks_re:\brole\s*=\s*[\x22']?(presentation|none)\b"],
   extra={"html": {"fp": [{"code": page('<input type="text" [attr.aria-label]="label">\n<input type="text" id="{{ fid }}">'), "note": "Angular bindings"}]}},
   xref=["axe:label", "jsx-a11y:control-has-associated-label", "vuejs-accessibility:form-control-has-label"])
mk("INPUT-IMAGE-WITHOUT-ALT", "Image button without alternative text", ("https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/input/image", "alt", "MDN: <input type=\"image\">"),
   "input", '<input type="image" src="go.png">', '<input type="image" src="go.png" alt="Search">',
   "An image button needs alt text that says what it does; without it the button has no name.",
   ["1.1.1", "4.1.2"], filters=[r"node.has_re:(?i)\btype\s*=\s*[\x22']?image\b", f"markup.lacks_attr:alt|{NAMES}", "markup.unlabelled"], xref=["axe:input-image-alt"])
mk("ROLE-IMG-WITHOUT-NAME", "role=\"img\" without an accessible name", ("https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/img_role", "aria-label", "MDN: ARIA img role"),
   ANY, '<div role="img" class="rating-4"></div>', '<div role="img" class="rating-4" aria-label="4 out of 5 stars"></div>\n<svg role="img"><title>Logo</title></svg>',
   "An element exposed as an image needs a text alternative: add aria-label or aria-labelledby (or a <title> for SVG).",
   ["1.1.1"], filters=["markup.not_hidden", r"markup.attr_re:role:^\s*(img|image)\s*$", f"markup.lacks_attr:alt|{NAMES}", "markup.no_text"], xref=["axe:role-img-alt", "axe:svg-img-alt"])
mk("ARIA-INVALID-ROLE", "Unknown ARIA role", ("https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles", "role", "MDN: WAI-ARIA roles"),
   ANY, '<div role="buton" tabindex="0">Save</div>', '<div role="button" tabindex="0">Save</div>\n<section role="doc-chapter">x</section>',
   "This is not a WAI-ARIA role, so browsers ignore it and the element keeps its native (or no) semantics.",
   ["4.1.2"], filters=["markup.invalid_role"], xref=["axe:aria-roles", "jsx-a11y:aria-role", "vuejs-accessibility:aria-role"])
mk("ARIA-INVALID-ATTRIBUTE", "Unknown aria-* attribute", ARIA, ANY,
   '<input type="text" aria-labeledby="name-label">', '<input type="text" aria-labelledby="name-label">',
   "Not a WAI-ARIA state or property (often a misspelling such as aria-labeledby): assistive technology ignores it.",
   ["4.1.2"], filters=["markup.invalid_aria_attr"], xref=["axe:aria-valid-attr", "jsx-a11y:aria-props", "vuejs-accessibility:aria-props"])
mk("ARIA-REQUIRED-ATTRIBUTE", "ARIA role without its required state", ARIA, ANY,
   '<div role="checkbox" tabindex="0">Agree</div>', '<div role="checkbox" tabindex="0" aria-checked="false">Agree</div>\n<input type="checkbox" role="switch">',
   "This role needs a state that native markup would supply (aria-checked, aria-valuenow, aria-level, aria-expanded...): without it the widget's state is not announced.",
   ["4.1.2"], filters=["markup.role_missing_required"], xref=["axe:aria-required-attr", "jsx-a11y:role-has-required-aria-props"])
mk("ARIA-LABEL-ON-GENERIC", "aria-label on a div/span without a role", ("https://www.w3.org/TR/wai-aria-1.2/", "Prohibited States and Properties", "WAI-ARIA 1.2"),
   "div|span", '<p>Name <span aria-label="Required">*</span></p>', '<span aria-hidden="true">*</span><span class="visually-hidden">Required</span>\n<div role="group" aria-label="Filters">x</div>',
   "Generic elements cannot be named with aria-label/aria-labelledby (ARIA 1.2), so many screen readers skip the label: use visible text or give the element a role.",
   ["4.1.2"], filters=["markup.lacks_attr:role", "markup.has_attr:aria-label|aria-labelledby", r"node.lacks_re:aria-label(ledby)?\s*=\s*[\x22']\s*[\x22']",
                       "markup.parent_lacks_attr:role"], xref=["axe:aria-prohibited-attr"])
mk("AUTOCOMPLETE-INVALID", "autocomplete value that is not an autofill token", (U + "identify-input-purpose.html", "The purpose of each input field collecting information about the user can be programmatically determined", "Understanding SC 1.3.5 Identify Input Purpose"),
   "input|select|textarea", '<label>First name <input type="text" autocomplete="first-name"></label>',
   '<label>Email <input type="email" autocomplete="email"></label>\n<label>Street <input type="text" autocomplete="shipping street-address"></label>\n<label>Code <input type="text" autocomplete="off"></label>',
   "Browsers and assistive tools only recognise the HTML autofill tokens (email, given-name, tel, street-address...): use one so the field's purpose is machine-readable.",
   ["1.3.5"], filters=["markup.invalid_autocomplete"], xref=["axe:autocomplete-valid", "jsx-a11y:autocomplete-valid"])
mk("DUPLICATE-ID", "Duplicate id in one document", ("https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/id", "unique", "MDN: id attribute"),
   ANY, '<p id="intro">One</p>\n<p id="intro">Two</p>', '<p id="intro">One</p>\n<p id="outro">Two</p>',
   "ids must be unique: label for=, aria-labelledby and fragment links only reach the first element with this id.",
   filters=["markup.dup_id"], sev="minor",
   extra={"vue": {"fp": [{"code": vue_tpl('<p v-if="a" id="intro">One</p>\n<p v-else id="intro">Two</p>'), "note": "v-if/v-else render one element"}]}},
   xref=["axe:duplicate-id"])
mk("HEADING-SKIPPED-LEVEL", "Heading level skipped", ("https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/Heading_Elements", "Do not skip heading levels", "MDN: heading elements"),
   "h[1-6]", "<h1>Orders</h1>\n<h3>Open orders</h3>", "<h1>Orders</h1>\n<h2>Open orders</h2>\n<h3>Today</h3>\n<h2>Closed</h2>",
   "Heading levels jump here (for example h1 to h3): screen-reader users navigate by headings and assume content is missing.",
   filters=["markup.heading_skip"], sev="minor", xref=["axe:heading-order"])
mk("EMPTY-HEADING", "Heading without text", (U + "headings-and-labels.html", "Headings and labels describe topic or purpose", "Understanding SC 2.4.6 Headings and Labels"),
   "h[1-6]", "<h2></h2>", "<h2>Orders</h2>", "An empty heading is announced as a heading with no name: remove it or give it text.",
   ["2.4.6"], filters=["markup.not_hidden", "markup.no_text", f"markup.lacks_attr:{NAMES}"], xref=["axe:empty-heading", "jsx-a11y:heading-has-content"])
mk("NESTED-INTERACTIVE", "Interactive element inside a link or button", ("https://html.spec.whatwg.org/multipage/text-level-semantics.html", "no interactive content descendant", "HTML Living Standard: the a element"),
   "a|button|input|select|textarea", '<a href="/order/1"><button type="button">Open</button></a>', '<a href="/order/1">Open</a>\n<button type="button">Delete</button>',
   "Controls nested in a link or button are not reachable or announced reliably, and HTML forbids the nesting: separate them.",
   ["4.1.2"], filters=["markup.in:a|button"], xref=["axe:nested-interactive"])
mk("LANG-INVALID", "lang value that is not a language tag", ("https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/lang", "BCP 47", "MDN: lang attribute"),
   ANY, '<p lang="english">Hello</p>', '<p lang="en-GB">Hello</p>\n<p lang="">x</p>',
   "Not a BCP 47 language tag (use en, en-GB, pt-BR...): screen readers cannot pick the right voice.",
   ["3.1.1", "3.1.2"], filters=["markup.has_text_without:lang", r"node.lacks_re:(?i)^<(style|script|template|i18n|docs)\b", r"markup.attr_lacks_re:lang:^([a-zA-Z]{2,3}(-[a-zA-Z0-9]{1,8})*|[iIxX](-[a-zA-Z0-9]{1,8})+|)$"],
   xref=["axe:valid-lang", "axe:html-lang-valid", "jsx-a11y:lang"])
mk("VIDEO-WITHOUT-CAPTIONS", "<video> without a captions track", (U + "captions-prerecorded.html", "Captions are provided for all prerecorded audio content", "Understanding SC 1.2.2 Captions (Prerecorded)"),
   "video", '<video src="intro.mp4" controls></video>', '<video src="intro.mp4" controls>\n<track kind="captions" src="intro.vtt" srclang="en">\n</video>\n<video src="bg.mp4" autoplay muted loop></video>',
   "This video has no <track> for captions: deaf and hard-of-hearing users miss its audio.",
   ["1.2.2"], variants=("html", "vue"), filters=["markup.lacks_attr:muted", "markup.lacks_child:track"],
   mode="ai-confirm", ai="Does the video have meaningful audio (speech, narration) and no captions burned in or provided elsewhere?", xref=["axe:video-caption"])
mk("MARQUEE-OR-BLINK", "<marquee> or <blink> element", (U + "pause-stop-hide.html", "moving, blinking, scrolling", "Understanding SC 2.2.2 Pause, Stop, Hide"),
   "marquee|blink", "<marquee>Sale today</marquee>", "<p>Sale today</p>",
   "Moving or blinking text cannot be paused by the user and these elements are obsolete: use static content.", ["2.2.2"], variants=("html", "vue"),
   xref=["axe:marquee", "axe:blink"])
mk("MOUSE-WITHOUT-KEYBOARD", "Mouse-over handler without a focus equivalent", (F + "F54", "pointing-device-specific event handlers", "WCAG failure F54: pointer-only event handlers"),
   ANY, '<div onmouseover="show()">Details</div>', '<div tabindex="0" onmouseover="show()" onfocus="show()">Details</div>',
   "Behaviour triggered only on mouse-over is unavailable to keyboard users: trigger the same on focus.",
   ["2.1.1"], filters=["markup.has_event:mouseover|mouseenter", "markup.lacks_event:focus|focusin"],
   mode="ai-confirm", ai="Does the mouse-over handler provide functionality or content (not just a cosmetic effect or prefetch) that keyboard users cannot reach another way?",
   xref=["jsx-a11y:mouse-events-have-key-events", "vuejs-accessibility:mouse-events-have-key-events"])
mk("MAIN-LANDMARK-MISSING", "Page without a main landmark", (WAI + "Techniques/aria/ARIA11", "landmarks", "WCAG technique ARIA11: landmarks"),
   "body", "<p>Orders</p>", "<p>Orders</p>", "Without a <main> landmark, screen-reader users cannot jump straight to the page content.",
   variants=("html",), filters=[r"file.lacks_re:(?i)<main\b|role\s*=\s*[\x22']?main\b", r"file.lacks_re:\{%|\{\{|<%|\$\{|\bth:|\{#|@\w+\(|<ng-|\*ng"],
   extra={"html": {"main": False}}, sev="minor", rtags=["opt-in"], xref=["axe:landmark-one-main"])
mk("IMG-WITHOUT-ALT", "<img> without alt", U111, "img|area", '<img src="chart.png">', '<img src="chart.png" alt="Sales by month">\n<img src="divider.png" alt="">',
   "Images need an alt attribute: a description, or alt=\"\" when decorative.", ["1.1.1"], variants=("vue",),
   filters=[f"markup.lacks_attr:alt|{NAMES}", r"node.lacks_re:\brole\s*=\s*[\x22']?(presentation|none)\b"], xref=["axe:image-alt", "vuejs-accessibility:alt-text"])
mk("IFRAME-WITHOUT-TITLE", "<iframe> without a title", U412, "iframe", '<iframe src="/map"></iframe>', '<iframe src="/map" title="Store map"></iframe>',
   "Frames need a title that says what they contain, otherwise they are announced as just \"frame\".", ["4.1.2"], variants=("vue",),
   filters=[f"markup.lacks_attr:{NAMES}", r"node.lacks_re:aria-hidden\s*=\s*[\x22']?true"], xref=["axe:frame-title", "vuejs-accessibility:iframe-has-title"])
mk("OBJECT-WITHOUT-ALTERNATIVE", "<object> without alternative content", ("https://www.w3.org/WAI/WCAG22/Techniques/html/H53", "body of the object element", "WCAG technique H53"),
   "object", '<object data="chart.svg" type="image/svg+xml"></object>', '<object data="chart.svg" type="image/svg+xml">Sales rose 20% in May</object>',
   "Embedded objects need a text alternative inside the element (or aria-label/title) for users and browsers that cannot render them.", ["1.1.1"],
   variants=("vue", "jsx"),  # plain HTML: HTML-MAINT-OBJECT-WITHOUT-FALLBACK (Web:S5264)
   filters=["markup.not_hidden", "markup.no_text", f"markup.lacks_attr:{NAMES}", "markup.has_attr:data",
            r"node.lacks_re:\brole\s*=\s*[\x22']?(presentation|none)\b"], xref=["sonar:javascript:S5264", "sonar:typescript:S5264"])
mk("POSITIVE-TABINDEX", "tabindex greater than zero", (U + "focus-order.html", "focusable components receive focus in an order that preserves meaning and operability", "Understanding SC 2.4.3 Focus Order"),
   ANY, '<input type="text" aria-label="Name" tabindex="3">', '<input type="text" aria-label="Name">\n<div tabindex="0" role="button">x</div>',
   "Positive tabindex values reorder keyboard focus away from the visual order: use 0 or -1 and fix the DOM order.", ["2.4.3"], variants=("vue",),
   filters=[r"markup.attr_re:tabindex:^\s*[1-9]"], xref=["axe:tabindex", "vuejs-accessibility:tabindex-no-positive"])
mk("CLICK-WITHOUT-KEYBOARD", "Click handler on a non-interactive element without a key handler", (U + "keyboard.html", "All functionality of the content is operable through a keyboard interface", "Understanding SC 2.1.1 Keyboard"),
   "div|span|li|p|td|img|section|article|label", '<div onclick="save()">Save</div>', '<div role="button" tabindex="0" onclick="save()" onkeydown="save()">Save</div>\n<button type="button" onclick="save()">Save</button>',
   "Keyboard users cannot trigger this click handler: use a <button>, or add a role, tabindex and a key handler.", ["2.1.1"], variants=("vue",),
   filters=["markup.has_event:click", "markup.lacks_event:keydown|keyup|keypress", r"node.lacks_re:(@|v-on:)click(\.[\w-]+)*(\s|/|>|$)", r"node.lacks_re:aria-hidden(\s|/|>|=\s*[\x22']?true)", r"node.lacks_re:\brole\s*=\s*[\x22']?(presentation|none)\b"],
   xref=["vuejs-accessibility:click-events-have-key-events", "sonar:javascript:S6847", "sonar:typescript:S6847"])
mk("AUTOPLAY-WITH-SOUND", "Audio/video set to autoplay with sound", (U + "audio-control.html", "plays automatically for more than 3 seconds", "Understanding SC 1.4.2 Audio Control"),
   "video|audio", '<video src="promo.mp4" autoplay></video>', '<video src="promo.mp4" autoplay muted></video>\n<video src="promo.mp4" controls></video>',
   "Sound that starts by itself talks over screen readers: do not autoplay, or start muted.", ["1.4.2"], variants=("vue", "jsx"),
   filters=["markup.has_attr:autoplay", "markup.lacks_attr:muted"], mode="ai-confirm", ai="Does the media have an audio track that plays for more than 3 seconds without a way to pause or mute it?",
   xref=["axe:no-autoplay-audio", "vuejs-accessibility:no-autoplay"])
mk("TH-INVALID-SCOPE", "Header cell with an invalid scope", ("https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/th", "scope", "MDN: <th>"),
   "th", '<table><tr><th scope="column">Item</th></tr></table>', '<table><tr><th scope="col">Item</th></tr></table>',
   "scope must be row, col, rowgroup or colgroup; any other value is ignored and the header is not associated.",
   ["1.3.1"], filters=[r"markup.attr_lacks_re:scope:^(?i)(row|col|rowgroup|colgroup|auto)$"], xref=["axe:scope-attr-valid"])
mk("IMG-REDUNDANT-ALT", "alt text that repeats \"image\"/\"picture\"", ("https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/img", "alt", "MDN: <img>"),
   "img", '<img src="ceo.jpg" alt="Photo of our CEO">', '<img src="ceo.jpg" alt="Our CEO, Ana Silva">',
   "Screen readers already say \"image\": describe the content instead of the medium.",
   filters=[r"markup.attr_re:alt:(?i)\b(image|picture|photo|graphic)( of)?\b", r"node.lacks_re:aria-hidden(\s|/|>|=\s*[\x22'{]?true)"], sev="minor", xref=["jsx-a11y:img-redundant-alt", "vuejs-accessibility:alt-text"])
mk("TABLE-WITHOUT-HEADERS", "Data table without header cells", U131, "table",
   "<table>\n<tr><td>Item</td><td>Price</td></tr>\n<tr><td>Tea</td><td>3</td></tr>\n</table>",
   "<table>\n<tr><th scope=\"col\">Item</th><th scope=\"col\">Price</th></tr>\n<tr><td>Tea</td><td>3</td></tr>\n</table>\n<table role=\"presentation\"><tr><td>x</td></tr></table>",
   "Without <th> cells, screen readers cannot tell users which column or row a value belongs to: mark up the header row/column.",
   ["1.3.1"], filters=["markup.lacks_child:th", r"node.lacks_re:\brole\s*=\s*[\x22']?(presentation|none)\b", r"parent.lacks_re:\brole\s*=\s*[\x22']?(columnheader|rowheader)|\bheaders\s*="],
   mode="ai-confirm", ai="Is this a data table (values in rows and columns that need headers), not a layout table?", xref=["axe:td-has-header"])
mk("AMBIGUOUS-LINK-TEXT", "Link text that does not say where it goes", (U + "link-purpose-link-only.html", "a mechanism is available to allow the purpose of each link to be identified from link text alone", "Understanding SC 2.4.9 Link Purpose (Link Only)"),
   "a", '<p>Our returns policy changed. <a href="/returns">Read more</a></p>', '<p>Our returns policy changed. <a href="/returns">Read the returns policy</a></p>\n<a href="/returns" aria-label="Read more about returns">Read more</a>',
   "\"Click here\"/\"Read more\" links are meaningless in a links list: make the text describe the destination.",
   ["2.4.9"], sev="minor", filters=["markup.not_hidden", r"parent.has_re:(?i)^<a\b[^>]*>\s*(click here|here|read more|more|learn more|link|this link|details|continue)\s*[.!]?\s*</a>$", f"markup.lacks_attr:{NAMES}|aria-describedby"],
   xref=["axe:link-name", "jsx-a11y:anchor-ambiguous-text"])

# ---- Nuxt UI components (rendered markup comes from the component's props) -------------------------
mk("UBUTTON-ICON-WITHOUT-LABEL", "Icon-only Nuxt UI button without an accessible name", U412, "UButton|u-button", "", "",
   "An icon-only UButton renders a <button> with no text: pass label, aria-label or slot text.", ["4.1.2"], variants=("nuxtui",),
   filters=["markup.has_attr:icon|leading-icon|trailing-icon|avatar", f"markup.lacks_attr:label|{NAMES}", "markup.no_text"],
   extra={"nuxtui": {"bad": '<UButton icon="i-lucide-x" color="neutral" @click="close" />',
                     "good": '<UButton icon="i-lucide-x" aria-label="Close" @click="close" />\n<UButton icon="i-lucide-save" label="Save" />\n<UButton icon="i-lucide-save">{{ t("save") }}</UButton>'}})
mk("NUXT-IMG-WITHOUT-ALT", "NuxtImg/NuxtPicture/UAvatar image without alt", U111, "NuxtImg|NuxtPicture|nuxt-img|nuxt-picture|UAvatar|u-avatar", "", "",
   "The component renders an <img> without alt text: pass alt (empty for decorative images).", ["1.1.1"], variants=("nuxtui",),
   filters=["markup.has_attr:src", f"markup.lacks_attr:alt|{NAMES}"],
   extra={"nuxtui": {"bad": '<NuxtImg src="/chart.png" width="400" />', "good": '<NuxtImg src="/chart.png" alt="Sales by month" width="400" />\n<UAvatar src="/u.png" :alt="user.name" />'}})
mk("LINK-COMPONENT-WITHOUT-NAME", "NuxtLink/ULink without text", (U + "link-purpose-in-context.html", "The purpose of each link can be determined from the link text alone", "Understanding SC 2.4.4 Link Purpose (In Context)"),
   "NuxtLink|ULink|nuxt-link|u-link|RouterLink|router-link", "", "",
   "This link component renders an <a> with no text: add link text or aria-label.", ["2.4.4", "4.1.2"], variants=("nuxtui",),
   filters=["markup.no_text", f"markup.lacks_attr:{NAMES}|label"],
   extra={"nuxtui": {"bad": '<NuxtLink to="/cart" />', "good": '<NuxtLink to="/cart">Cart</NuxtLink>\n<ULink to="/cart" aria-label="Cart"><UIcon name="i-lucide-cart" /></ULink>'}})

RULES = CSSP.R + HTMLP.R + VUEP.R + JSXP.R + NUXTUIP.R

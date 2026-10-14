"""CSS pack (official tree-sitter-css grammar): stylesheet correctness and maintainability.

Runs on .css files and on plain-CSS <style> blocks of HTML pages and Vue SFCs (lang scss/less/
stylus blocks are skipped). Sources: W3C CSS specifications (CSS 2.2 error handling, Cascade 4,
Color 4, Values 4, Animations 1, Fonts 4, Images 3, Selectors 4) and MDN. Unknown-name checks use
internal/engine/data/css-known.txt (tools/rulegen/cssdata.py: @webref/css + the CSS WG property
index), so drafts count as known. stylelint and Sonar CSS rules are cross-references only."""
from specs._common import Pack

P = Pack("CSS", "css", "CSS (W3C TR, 2026)", {"any": "*"})
TR = "https://www.w3.org/TR/"
MDN = "https://developer.mozilla.org/en-US/docs/Web/CSS/"
CASCADE = (TR + "css-cascade-4/", "The last declaration in document order wins", "CSS Cascading and Inheritance Level 4")


def sl(rule, *sonar):
    return [f"stylelint:{rule}"] + [f"sonar:css:{k}" for k in sonar]


P("UNKNOWN-PROPERTY", "Unknown CSS property", TR + "CSS22/syndata.html", "ignore a declaration with an unknown property",
  "(declaration (property_name) @match)",
  ".card {\n  colr: #333;\n}\n", ".card {\n  color: #333;\n  --brand: #333;\n  -webkit-line-clamp: 2;\n  field-sizing: content;\n}\n",
  "Browsers drop declarations with an unknown property: this line has no effect (typo or invented name).",
  sev="major", kind="anti-pattern", cat="correctness", doc="CSS 2.2: rules for handling parsing errors", filters=["css.unknown_property"],
  xref=sl("property-no-unknown", "S4654"),
  fp=[{"code": "@font-face {\n  font-family: Inter;\n  src: url(inter.woff2);\n  font-display: swap;\n}\n", "note": "@font-face descriptors"},
      {"code": ".a {\n  *zoom: 1;\n  _height: 1px;\n}\n", "note": "IE hacks are deliberate"}])
P("DUPLICATE-DECLARATION", "Same declaration repeated in a rule", *CASCADE[:2],
  "(declaration (property_name)) @match",
  ".card {\n  color: #333;\n  padding: 0;\n  color: #333;\n}\n", ".card {\n  color: #333;\n  padding: 0;\n}\n",
  "The identical declaration appears earlier in the same block: delete the copy.",
  sev="minor", kind="anti-pattern", cat="maintainability", doc=CASCADE[2], filters=["css.dup_decl"],
  xref=sl("declaration-block-no-duplicate-properties", "S4656"))
P("OVERRIDDEN-DECLARATION", "Property set twice in a rule, first value never used", *CASCADE[:2],
  "(declaration (property_name)) @match",
  ".card {\n  color: #333;\n  padding: 0;\n  color: #444;\n}\n",
  ".card {\n  color: #444;\n  padding: 0;\n}\n\n.box {\n  height: 100vh;\n  height: 100dvh;\n  display: -webkit-box;\n  display: flex;\n  width: 100%;\n  width: calc(100% - 2rem);\n}\n",
  "A later declaration of the same property in this block wins, so the earlier value is dead: keep one (fallbacks for newer syntax are not flagged).",
  sev="minor", kind="anti-pattern", cat="correctness", doc=CASCADE[2], filters=["css.dup_prop"],
  mode="ai-confirm", ai="Is the earlier declaration a dead duplicate rather than a deliberate fallback for browsers that do not support the later value?",
  xref=sl("declaration-block-no-duplicate-properties", "S4656"))
P("SHORTHAND-OVERRIDES-LONGHAND", "Shorthand property resets a longhand set just before it",
  MDN + "Guides/Cascade/Shorthand_properties", "That means that it overrides previously set values",
  "(declaration (property_name)) @match",
  ".hero {\n  background-color: #036;\n  background: url(hero.png) no-repeat;\n}\n",
  ".hero {\n  background: url(hero.png) no-repeat;\n  background-color: #036;\n}\n\n.row {\n  flex-direction: column;\n  flex: 1;\n}\n",
  "The shorthand resets every sub-property it covers, so the longhand above it is lost: put the longhand after the shorthand.",
  sev="major", kind="anti-pattern", cat="correctness", doc="MDN: Shorthand properties", filters=["css.shorthand_override"],
  xref=sl("declaration-block-no-shorthand-property-overrides", "S4657"))
P("DUPLICATE-SELECTOR", "Same selector defined twice at one level", *CASCADE[:2],
  "(rule_set (selectors)) @match",
  ".card {\n  color: #333;\n}\n\n.title {\n  margin: 0;\n}\n\n.card {\n  padding: 0;\n}\n",
  ".card {\n  color: #333;\n  padding: 0;\n}\n\n@media (min-width: 40em) {\n  .card {\n    padding: 1rem;\n  }\n}\n\n:root {\n  --bg: #fff;\n}\n\n.card-title {\n  margin: 0;\n}\n\n:root {\n  --fg: #111;\n}\n",
  "This selector already has a rule at this level: merge the two so the styles for it live in one place.",
  sev="minor", kind="best-practice", cat="maintainability", doc=CASCADE[2], filters=["css.dup_selector"],
  xref=sl("no-duplicate-selectors", "S4666"))
P("EMPTY-RULE", "Rule with an empty block", TR + "CSS22/syndata.html", "consists of a selector followed by a declaration block",
  "(rule_set (block) @b) @match",
  ".card {\n}\n", ".card {\n  /* filled by the theme */\n}\n\n.title {\n  margin: 0;\n}\n",
  "An empty rule does nothing: remove it (or leave a comment saying why it is there).",
  sev="minor", kind="best-practice", cat="maintainability", doc="CSS 2.2 syntax", filters=[r"cap.lacks_re:b:[^{}\s]"],
  xref=sl("block-no-empty", "S4658"))
P("INVALID-HEX-COLOR", "Hex colour with the wrong number of digits", TR + "css-color-4/", "3, 4, 6, or 8 hexadecimal digits",
  "((color_value) @match (#not-match? @match \"^#([0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$\"))",
  ".card {\n  color: #12345;\n}\n", ".card {\n  color: #123456;\n  border-color: #abcd;\n}\n",
  "Not a valid hex colour, so the whole declaration is dropped: use 3, 4, 6 or 8 hex digits.",
  sev="major", kind="anti-pattern", cat="correctness", doc="CSS Color Module Level 4", xref=sl("color-no-invalid-hex", "S4647"))
P("IMPORTANT-IN-KEYFRAMES", "!important inside @keyframes", TR + "css-animations-1/", "properties qualified with !important are invalid and ignored",
  "((keyframes_statement (keyframe_block_list (keyframe_block (block (declaration (important) @match))))) @k (#match? @k \"^@(-[a-zA-Z]+-)?(?i:keyframes)\\\\b\"))",
  "@keyframes fade {\n  from {\n    opacity: 0 !important;\n  }\n  to {\n    opacity: 1;\n  }\n}\n",
  "@keyframes fade {\n  from {\n    opacity: 0;\n  }\n  to {\n    opacity: 1;\n  }\n}\n",
  "Browsers ignore the whole declaration when it is marked !important inside a keyframe: drop !important.",
  sev="major", kind="anti-pattern", cat="correctness", doc="CSS Animations Level 1", xref=sl("keyframe-declaration-no-important", "S4655"))
P("FONT-FAMILY-WITHOUT-GENERIC", "font-family list without a generic family", MDN + "Reference/Properties/font-family", "generic",
  "((declaration (property_name) @p) @match (#match? @p \"^(?i)font-family$\"))",
  ".card {\n  font-family: Inter, Helvetica;\n}\n",
  ".card {\n  font-family: Inter, Helvetica, sans-serif;\n}\n\n@font-face {\n  font-family: Inter;\n  src: url(inter.woff2);\n}\n\n.icon {\n  font-family: \"Font Awesome 6 Free\";\n}\n\n.x {\n  font-family: var(--font);\n}\n",
  "If none of the listed fonts loads, the browser default is used: end the list with a generic family (sans-serif, serif, monospace, system-ui...).",
  sev="minor", kind="best-practice", cat="correctness", doc="MDN: font-family",
  filters=[r"node.lacks_re:(?i)\b(serif|sans-serif|monospace|cursive|fantasy|system-ui|ui-serif|ui-sans-serif|ui-monospace|ui-rounded|math|emoji|fangsong|inherit|initial|unset|revert|revert-layer)\b|var\(|\$|@|#\{",
           r"node.lacks_re:(?i)icon|awesome|symbol|glyph|material|feather|ionicons|dashicons|fontello|icomoon",
           r"ancestor.lacks_re:at_rule:(?i)^@font-"],
  xref=sl("font-family-no-missing-generic-family-keyword", "S4649"))
P("DUPLICATE-FONT-FAMILY", "Font listed twice in font-family", MDN + "Reference/Properties/font-family", "generic",
  "((declaration (property_name) @p) @match (#match? @p \"^(?i)font-family$\"))",
  ".card {\n  font-family: Inter, Arial, Inter, sans-serif;\n}\n", ".card {\n  font-family: Inter, Arial, sans-serif;\n}\n",
  "The second occurrence of this font is never used: remove it.",
  sev="minor", kind="best-practice", cat="maintainability", doc="MDN: font-family", filters=["css.dup_font_family"],
  xref=sl("font-family-no-duplicate-names", "S4648"))
P("CALC-UNSPACED-OPERATOR", "calc() with + or - not surrounded by spaces", MDN + "Reference/Values/calc", "whitespace",
  "((call_expression (function_name) @f) @match (#match? @f \"^(?i)(calc|min|max|clamp)$\"))",
  ".card {\n  width: calc(100%-2rem);\n}\n", ".card {\n  width: calc(100% - 2rem);\n  margin: calc(-1 * 1rem);\n  height: calc(var(--h)*2);\n}\n",
  "Without spaces around + and - the expression is invalid (\"100%-2rem\" reads as one token) and the declaration is dropped.",
  sev="major", kind="anti-pattern", cat="correctness", doc="MDN: calc()", xref=sl("function-calc-no-unspaced-operator", "S4650"),
  filters=[r"node.has_re:(\d|%|\))(\+|-)(\d|\.\d|\()|(\d[a-zA-Z%]+|\))\+[\w(.]", r"node.lacks_re:\[|var\(--[\w-]+\s*,"])
P("GRADIENT-LEGACY-DIRECTION", "linear-gradient() direction without \"to\"", MDN + "Reference/Values/gradient/linear-gradient", "to top",
  "((call_expression (function_name) @f (arguments . (plain_value) @d)) @match (#match? @f \"^(?i)(repeating-)?linear-gradient$\") (#match? @d \"^(?i)(top|bottom|left|right)$\"))",
  ".hero {\n  background: linear-gradient(top, #fff, #000);\n}\n", ".hero {\n  background: linear-gradient(to bottom, #fff, #000);\n  background: -webkit-linear-gradient(top, #fff, #000);\n}\n",
  "The standard syntax needs \"to <side>\" (and means the opposite of the old prefixed syntax): without it the value is invalid.",
  sev="major", kind="anti-pattern", cat="correctness", doc="MDN: linear-gradient()", xref=sl("function-linear-gradient-no-nonstandard-direction", "S4651"))
P("UNKNOWN-PSEUDO", "Unknown pseudo-class or pseudo-element", TR + "selectors-4/", "invalid selector",
  "(pseudo_class_selector (class_name) @match)\n(pseudo_element_selector (tag_name) @match .)",
  ".card::befor {\n  content: \"\";\n}\n\n.link:hovr {\n  color: red;\n}\n",
  ".card::before {\n  content: \"\";\n}\n\n.link:hover,\n.link:focus-visible {\n  color: red;\n}\n\n:deep(.x) {\n  color: red;\n}\n\ninput::-webkit-input-placeholder {\n  color: gray;\n}\n",
  "An unknown pseudo-class or pseudo-element makes the whole selector invalid, so the rule never applies.",
  sev="major", kind="anti-pattern", cat="correctness", doc="Selectors Level 4", filters=["css.unknown_pseudo"],
  xref=sl("selector-pseudo-class-no-unknown", "S4659") + sl("selector-pseudo-element-no-unknown", "S4660"))
P("UNKNOWN-AT-RULE", "Unknown at-rule", TR + "CSS22/syndata.html", "must ignore an invalid at-keyword",
  "(at_rule (at_keyword) @match)",
  "@layr base;\n", "@tailwind base;\n@layer base {\n  .a {\n    color: red;\n  }\n}\n@font-face {\n  font-family: X;\n  src: url(x.woff2);\n}\n",
  "Browsers skip an unknown at-rule and everything in its block: check the name.",
  sev="major", kind="anti-pattern", cat="correctness", doc="CSS 2.2: rules for handling parsing errors", filters=["css.unknown_at_rule"],
  xref=sl("at-rule-no-unknown", "S4662"))
P("UNKNOWN-MEDIA-FEATURE", "Unknown media feature", TR + "mediaqueries-4/", "For unknown features",
  "(feature_name) @match",
  "@media (min-wdth: 40em) {\n  .card {\n    padding: 1rem;\n  }\n}\n",
  "@media (min-width: 40em) {\n  .card {\n    padding: 1rem;\n  }\n}\n@media (prefers-color-scheme: dark) {\n  .card {\n    color: #eee;\n  }\n}\n",
  "An unknown media feature makes the query false, so the whole @media block never applies: check the name.",
  sev="major", kind="anti-pattern", cat="correctness", doc="Media Queries Level 4", filters=["css.unknown_media"],
  xref=sl("media-feature-name-no-unknown", "S4661"),
  quote="For unknown features, user agents instead assume a value of zero for numeric values, or unknown / false for enum values.")
P("DUPLICATE-KEYFRAME-SELECTOR", "Same keyframe offset declared twice", TR + "css-animations-1/", "from is equivalent to 0% and to is equivalent to 100%",
  "(keyframe_block) @match",
  "@keyframes fade {\n  from {\n    opacity: 0;\n  }\n  from {\n    opacity: 0.1;\n  }\n  to {\n    opacity: 1;\n  }\n}\n",
  "@keyframes fade {\n  from {\n    opacity: 0;\n  }\n  to {\n    opacity: 1;\n  }\n}\n",
  "The later keyframe with this offset replaces the earlier one, so the first declaration never runs: keep a single block per offset (from equals 0%, to equals 100%).",
  sev="major", kind="anti-pattern", cat="correctness", doc="CSS Animations Level 1", filters=["css.dup_keyframe"],
  xref=sl("keyframe-block-no-duplicate-selectors", "S8773"),
  quote="The keyframe selector for a keyframe rule consists of a comma-separated list of percentage values or the keywords from or to. The selector is used to specify the percentage along the duration of the animation that the keyframe represents. The keyframe itself is specified by the block of property values declared inside. The keyword from is equivalent to 0% and the keyword to is equivalent to 100%.")
P("UNMATCHABLE-NTH", "An+B selector that never matches", TR + "selectors-4/#the-nth-child-pseudo", "An+B-1 siblings before them",
  '((pseudo_class_selector (class_name) @n (arguments (integer_value) @v)) @match (#match? @n "^(?i)nth-(last-)?(child|of-type)$") (#eq? @v "0"))\n'
  '((pseudo_class_selector (class_name) @n (arguments (plain_value) @v)) @match (#match? @n "^(?i)nth-(last-)?(child|of-type)$") (#match? @v "^(?i)0n$"))',
  "li:nth-child(0) {\n  color: red;\n}\n",
  "li:nth-child(2n) {\n  color: red;\n}\n\nli:nth-child(1) {\n  color: red;\n}\n",
  ":nth-child(0) and :nth-child(0n) never match (elements are counted from 1): use 1, odd/even, or An+B with a positive B.",
  sev="major", kind="anti-pattern", cat="correctness", doc="Selectors Level 4",
  xref=sl("selector-anb-no-unmatchable", "S8774"),
  quote="The :nth-child(An+B) pseudo-class notation represents elements that have An+B-1 siblings before them in the document tree.")
P("TOP-LEVEL-NESTING-SELECTOR", "Nesting selector & used at the top level", TR + "css-nesting-1/#nest-selector", "The nesting selector",
  "((stylesheet (rule_set (selectors [(nesting_selector) (descendant_selector (nesting_selector)) (child_selector (nesting_selector)) (sibling_selector (nesting_selector)) (adjacent_sibling_selector (nesting_selector))]))) @match)",
  "& .title {\n  color: red;\n}\n",
  ".card {\n  & .title {\n    color: red;\n  }\n}\n",
  "The nesting selector & only means something inside a nested style rule: at the top of a stylesheet it does not match, so this rule never applies.",
  sev="major", kind="anti-pattern", cat="correctness", doc="CSS Nesting Module Level 1",
  xref=sl("nesting-selector-no-missing-scoping-root", "S8776"),
  quote="The nesting selector can be used anywhere in a nested style rule's selector.")
P("UNKNOWN-TYPE-SELECTOR", "Unknown type selector", TR + "selectors-4/", "type selector",
  "(tag_name) @match",
  "foo {\n  color: red;\n}\n",
  "div {\n  color: red;\n}\nmy-widget {\n  color: red;\n}\n",
  "Not an HTML, SVG or MathML element name, so this type selector never matches: use a real tag, a class, or a custom element (with a hyphen).",
  sev="major", kind="anti-pattern", cat="correctness", doc="Selectors Level 4", filters=["css.unknown_type"],
  xref=sl("selector-type-no-unknown", "S4670"),
  quote="A type selector is the name of a document language element type, and it represents an instance of that element type in the document tree.")
P("UNKNOWN-UNIT", "Unknown unit", TR + "css-values-4/", "Lengths",
  "((integer_value (unit) @match) (#not-match? @match \"^(?i)(px|cm|mm|q|in|pt|pc|em|rem|ex|rex|cap|rcap|ch|rch|ic|ric|lh|rlh|vw|vh|vi|vb|vmin|vmax|svw|svh|svi|svb|svmin|svmax|lvw|lvh|lvi|lvb|lvmin|lvmax|dvw|dvh|dvi|dvb|dvmin|dvmax|cqw|cqh|cqi|cqb|cqmin|cqmax|deg|grad|rad|turn|s|ms|hz|khz|dpi|dpcm|dppx|x|fr|%)$\"))\n"
  "((float_value (unit) @match) (#not-match? @match \"^(?i)(px|cm|mm|q|in|pt|pc|em|rem|ex|rex|cap|rcap|ch|rch|ic|ric|lh|rlh|vw|vh|vi|vb|vmin|vmax|svw|svh|svi|svb|svmin|svmax|lvw|lvh|lvi|lvb|lvmin|lvmax|dvw|dvh|dvi|dvb|dvmin|dvmax|cqw|cqh|cqi|cqb|cqmin|cqmax|deg|grad|rad|turn|s|ms|hz|khz|dpi|dpcm|dppx|x|fr|%)$\"))",
  ".card {\n  margin: 10pxx;\n}\n", ".card {\n  margin: 10px 1.5rem 2dvh 5cqi;\n  transition: opacity .2s;\n}\n",
  "Not a CSS unit, so the declaration is invalid and dropped.",
  sev="major", kind="anti-pattern", cat="correctness", doc="CSS Values and Units Level 4", xref=sl("unit-no-unknown", "S4653"),
  filters=[r"ancestor.lacks_re:call_expression:^(?i)url\(", r"ancestor.lacks_re:attribute_selector:.", r"ancestor.lacks_re:declaration:[$@][\w-]*\d"])
P("DOUBLE-SLASH-COMMENT", "// comment in plain CSS", TR + "CSS22/syndata.html", "Comments begin with the characters",
  "(js_comment) @match",
  "// card styles\n.card {\n  color: #333;\n}\n", "/* card styles */\n.card {\n  color: #333;\n}\n",
  "CSS has no // comments: the text is parsed as part of the next selector or declaration, which is then dropped.",
  sev="major", kind="anti-pattern", cat="correctness", doc="CSS 2.2: comments", xref=["stylelint:no-invalid-double-slash-comments"])
P("IMPORTANT", "!important declaration", MDN + "Reference/Values/important", "!important",
  "(declaration (important) @match)",
  ".card {\n  color: #333 !important;\n}\n", ".page .card {\n  color: #333;\n}\n",
  "!important breaks normal cascade and specificity and forces more !important to override it: raise specificity or use cascade layers instead.",
  sev="minor", kind="best-practice", cat="maintainability", doc="MDN: !important", tags=["opt-in"], xref=["stylelint:declaration-no-important"])
P("UNNEEDED-VENDOR-PREFIX", "Vendor prefix on a property every current browser supports unprefixed",
  "https://developer.mozilla.org/en-US/docs/Glossary/Vendor_Prefix", "vendor prefix",
  "((declaration (property_name) @match) (#match? @match \"^-(webkit|moz|ms|o)-(border-radius|box-shadow|box-sizing|transition(-[a-z-]+)?|transform(-origin|-style)?|animation(-[a-z-]+)?|border-image|opacity|flex(-grow|-shrink|-basis|-direction|-wrap|-flow)?|justify-content|align-items|align-self|align-content|order|column-count|column-gap|column-width|columns|perspective|backface-visibility)$\"))",
  ".card {\n  -webkit-border-radius: 4px;\n  border-radius: 4px;\n}\n", ".card {\n  border-radius: 4px;\n  -webkit-background-clip: text;\n  -webkit-user-select: none;\n}\n",
  "Every supported browser understands the unprefixed property: drop the prefixed copy (let a build-time prefixer add what an old target needs).",
  sev="minor", kind="best-practice", cat="maintainability", doc="MDN glossary: Vendor prefix", tags=["opt-in"], xref=["stylelint:property-no-vendor-prefix"])

RULES = P.R

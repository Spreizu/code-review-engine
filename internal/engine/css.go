package engine

import (
	_ "embed"
	"math"
	"regexp"
	"strconv"
	"strings"

	ts "github.com/tree-sitter/go-tree-sitter"
)

// CSS post-filters (rules with language css). They work on the official tree-sitter-css tree:
// rule_set -> block -> declaration (property_name, values..., important).

//go:embed data/css-known.txt
var cssKnownData string

//go:embed data/css-colors.txt
var cssColorData string

var (
	cssKnown  = map[string]map[string]bool{} // kind -> name
	cssColors = map[string][3]float64{}
)

func init() {
	for _, l := range strings.Split(cssKnownData, "\n") {
		k, n, ok := strings.Cut(strings.TrimSpace(l), " ")
		if !ok || strings.HasPrefix(l, "#") {
			continue
		}
		if cssKnown[k] == nil {
			cssKnown[k] = map[string]bool{}
		}
		cssKnown[k][n] = true
	}
	for _, l := range strings.Split(cssColorData, "\n") {
		f := strings.Fields(l)
		if len(f) == 3 && f[0] == "color" {
			if c, ok := parseHex(f[2]); ok {
				cssColors[f[1]] = [3]float64{c[0], c[1], c[2]}
			}
		}
	}
}

// CSSKnown reports whether name is a known CSS name of kind (property, descriptor,
// pseudo-class, pseudo-element, at-rule).
func CSSKnown(kind, name string) bool { return cssKnown[kind][strings.ToLower(name)] }

// cssFilter evaluates the css.* filters; handled=false for other names.
func cssFilter(name, arg string, n ts.Node, src []byte) (pass, handled bool) {
	switch name {
	case "css.unknown_property":
		d := declNode(n)
		if d == nil {
			return false, true
		}
		p := cssProp(d, src)
		if p == "" || strings.HasPrefix(p, "--") || strings.HasPrefix(p, "-") || strings.ContainsAny(p, "$@#{}*_") {
			return false, true // custom properties, vendor prefixes, preprocessor syntax and IE hacks
		}
		for a := d.Parent(); a != nil; a = a.Parent() {
			if a.Kind() == "at_rule" || a.Kind() == "declaration" ||
				a.Kind() == "rule_set" && strings.HasPrefix(strings.TrimSpace(a.Utf8Text(src)), "--") {
				return false, true // descriptors of other at-rules, custom property sets
			}
		}
		if cssKnown["property"][p] || cssKnown["descriptor"][p] {
			return false, true
		}
		return true, true
	case "css.dup_decl", "css.dup_prop":
		d := declNode(n)
		if d == nil {
			return false, true
		}
		p, v := cssProp(d, src), cssValue(d, src)
		if name == "css.dup_prop" && (strings.HasPrefix(p, "--") || p == "src") {
			return false, true // custom properties are often redefined on purpose; @font-face src lists fall back
		}
		for s := d.PrevNamedSibling(); s != nil; s = s.PrevNamedSibling() {
			if s.Kind() != "declaration" || cssProp(s, src) != p {
				continue
			}
			if name == "css.dup_decl" && cssValue(s, src) == v {
				return true, true
			}
			if name == "css.dup_prop" && cssValue(s, src) != v && !cssFallback(cssValue(s, src), v) && !cssFallback(v, cssValue(s, src)) {
				return true, true
			}
		}
		return false, true
	case "css.shorthand_override":
		d := declNode(n)
		if d == nil {
			return false, true
		}
		long := cssShorthands[cssProp(d, src)]
		if long == nil || cssValue(d, src) == "" || strings.Contains(cssValue(d, src), "var(") {
			return false, true
		}
		for s := d.PrevNamedSibling(); s != nil; s = s.PrevNamedSibling() {
			if s.Kind() == "declaration" && long[cssProp(s, src)] && !strings.Contains(cssValue(s, src), "!important") {
				return true, true
			}
		}
		return false, true
	case "css.dup_selector":
		if n.Kind() != "rule_set" {
			return false, true
		}
		sel := cssSelectors(&n, src)
		if sel == "" || sel == ":root" || sel == ":host" {
			return false, true // splitting custom properties across :root/:host blocks is idiomatic
		}
		for s := n.PrevNamedSibling(); s != nil; s = s.PrevNamedSibling() {
			if strings.Contains(string(src[s.EndByte():n.StartByte()]), StyleBoundary) {
				return false, true // an earlier <style> block (scoped vs global, another media attribute)
			}
			if s.Kind() == "rule_set" && cssSelectors(s, src) == sel {
				return true, true
			}
		}
		return false, true
	case "css.unknown_pseudo":
		// node: the name of a pseudo-class (class_name) or pseudo-element (tag_name) selector
		nm := strings.ToLower(n.Utf8Text(src))
		p := n.Parent()
		if p == nil || strings.HasPrefix(nm, "-") || cssFrameworkPseudo[nm] {
			return false, true
		}
		switch p.Kind() {
		case "pseudo_element_selector":
			return !cssKnown["pseudo-element"][nm], true
		case "pseudo_class_selector":
			return !cssKnown["pseudo-class"][nm] && !cssKnown["pseudo-element"][nm], true
		}
		return false, true
	case "css.unknown_at_rule":
		nm := strings.ToLower(strings.TrimPrefix(n.Utf8Text(src), "@"))
		if strings.HasPrefix(nm, "-") || cssFrameworkAtRules[nm] {
			return false, true
		}
		return !cssKnown["at-rule"][nm], true
	case "css.unknown_media":
		// node: feature_name inside a media/container query
		nm := strings.ToLower(n.Utf8Text(src))
		if strings.HasPrefix(nm, "-") {
			return false, true
		}
		nm = strings.TrimPrefix(strings.TrimPrefix(nm, "min-"), "max-")
		return !cssMediaFeatures[nm], true
	case "css.unknown_type":
		// node: tag_name used as a type selector (div, svg|rect, a:hover)
		if p := n.Parent(); p != nil && p.Kind() == "pseudo_element_selector" {
			return false, true
		}
		if p := n.Parent(); p != nil && p.Kind() == "namespace_selector" {
			// first child is the namespace prefix, not an element name
			if c := p.NamedChild(0); c != nil && c.Id() == n.Id() {
				return false, true
			}
		}
		nm := strings.ToLower(n.Utf8Text(src))
		if nm == "" || nm == "*" || strings.Contains(nm, "-") || strings.HasPrefix(nm, "-") {
			return false, true // universal, custom elements, vendor prefixes
		}
		return !cssTypeSelectors[nm], true
	case "css.dup_keyframe":
		if n.Kind() != "keyframe_block" {
			return false, true
		}
		sel := cssKeyframeSel(&n, src)
		if sel == "" {
			return false, true
		}
		for s := n.PrevNamedSibling(); s != nil; s = s.PrevNamedSibling() {
			if s.Kind() == "keyframe_block" && cssKeyframeSel(s, src) == sel {
				return true, true
			}
		}
		return false, true
	case "css.dup_font_family":
		d := declNode(n)
		if d == nil {
			return false, true
		}
		seen := map[string]bool{}
		for _, f := range strings.Split(strings.TrimSuffix(cssValue(d, src), "!important"), ",") {
			f = strings.Trim(strings.TrimSpace(f), `"'`)
			if f == "" {
				continue
			}
			if seen[f] {
				return true, true
			}
			seen[f] = true
		}
		return false, true
	case "css.contrast_lt", "css.contrast_ge":
		// css.contrast_lt:AA|AAA - the rule set's own literal color and background pair has a
		// contrast ratio below the WCAG minimum (large text: 3 for AA, 4.5 for AAA); contrast_ge:
		// the pair is known and meets it.
		r, ok := cssContrast(&n, src)
		if !ok {
			return false, true
		}
		large := cssLargeText(&n, src)
		need := 4.5
		switch {
		case arg == "AAA" && large:
			need = 4.5
		case arg == "AAA":
			need = 7
		case large:
			need = 3
		}
		return (r < need) == (name == "css.contrast_lt"), true
	}
	return false, false
}

func declNode(n ts.Node) *ts.Node {
	for p := &n; p != nil; p = p.Parent() {
		if p.Kind() == "declaration" {
			return p
		}
	}
	return nil
}

func cssProp(d *ts.Node, src []byte) string {
	for _, c := range named(d) {
		if c.Kind() == "property_name" {
			return strings.ToLower(c.Utf8Text(src))
		}
	}
	return ""
}

var wsRe = regexp.MustCompile(`\s+`)

// cssValue is the declaration's value text, whitespace-normalised, lower-cased, with
// "!important" kept (it changes the cascade).
func cssValue(d *ts.Node, src []byte) string {
	t := d.Utf8Text(src)
	if _, v, ok := strings.Cut(t, ":"); ok {
		t = v
	}
	t = strings.TrimSuffix(strings.TrimSpace(t), ";")
	return strings.ToLower(wsRe.ReplaceAllString(strings.TrimSpace(t), " "))
}

// cssFallback: b after a is a progressive-enhancement fallback pair (vendor-prefixed value,
// newer function or unit), the documented reason to repeat a property.
var fallbackRe = regexp.MustCompile(`(^|[\s(,])-(webkit|moz|ms|o)-|\b(var|env|clamp|min|max|calc|color-mix|oklch|oklab|lab|lch|hwb|color|image-set|light-dark|fit-content|min-content|max-content|stretch)\(|\d(dvh|svh|lvh|dvw|svw|lvw|cqw|cqh|cqi|cqb|cqmin|cqmax|vi|vb|lh|rlh|ic|cap|rem|ch)\b|\b(fit-content|min-content|max-content|stretch|flex|grid|inline-flex|inline-grid|sticky|contents|flow-root|subgrid|dvh)\b`)

func cssFallback(a, b string) bool { return fallbackRe.MatchString(a) || fallbackRe.MatchString(b) }

func cssSelectors(rs *ts.Node, src []byte) string {
	for _, c := range named(rs) {
		if c.Kind() == "selectors" {
			if t := c.Utf8Text(src); strings.ContainsAny(t, "\"'") {
				return strings.TrimSpace(t) // whitespace inside quoted attribute values is significant
			}
			parts := strings.Split(wsRe.ReplaceAllString(strings.TrimSpace(c.Utf8Text(src)), " "), ",")
			for i := range parts {
				parts[i] = strings.TrimSpace(parts[i])
			}
			return strings.Join(parts, ",")
		}
	}
	return ""
}

// Names that CSS tooling legitimately adds on top of the standard: Vue SFC scoped-style and CSS
// Modules pseudo-classes, Angular's legacy ::ng-deep, Tailwind/PostCSS/Sass at-rules.
var (
	cssFrameworkPseudo = map[string]bool{"horizontal": true, "vertical": true, "decrement": true, "increment": true, "start": true, "end": true,
		"double-button": true, "single-button": true, "no-button": true, "corner-present": true, "window-inactive": true,
		"user-error": true, "low-value": true, "high-value": true, "optimal-value": true, "suboptimal-value": true, "even-less-good-value": true,
		"deep": true, "slotted": true, "global": true, "local": true, "export": true, "import": true,
		"v-deep": true, "v-slotted": true, "v-global": true, "ng-deep": true}
	cssFrameworkAtRules = map[string]bool{"tailwind": true, "apply": true, "config": true, "plugin": true, "source": true, "theme": true,
		"utility": true, "variant": true, "custom-variant": true, "reference": true, "screen": true, "responsive": true, "variants": true,
		"custom-media": true, "custom-selector": true, "nest": true, "mixin": true, "define-mixin": true, "extend": true, "include": true,
		"use": true, "forward": true, "if": true, "else": true, "each": true, "for": true, "while": true, "function": true, "return": true,
		"content": true, "at-root": true, "viewport": true, "scroll-timeline": true, "document": true, "debug": true, "warn": true, "error": true, "value": true, "unocss": true}
	// Media Queries 4/5 + CSS Conditional 5 container features (range names are stored without min-/max-).
	cssMediaFeatures = setOf(`width height aspect-ratio orientation resolution scan grid update overflow-block overflow-inline
color color-index monochrome color-gamut pointer hover any-pointer any-hover prefers-color-scheme prefers-contrast
prefers-reduced-motion prefers-reduced-transparency prefers-reduced-data forced-colors inverted-colors scripting
display-mode dynamic-range video-dynamic-range video-color-gamut horizontal-viewport-segments vertical-viewport-segments
nav-controls environment-blending device-width device-height device-aspect-ratio device-posture light-level
dynamic-range-limit overflow-block overflow-inline shape grid scan update color-gamut
block-size inline-size aspect-ratio orientation style scroll-state`)
	// HTML, SVG and MathML type selectors; custom elements (with a hyphen) are accepted in the filter.
	cssTypeSelectors = setOf(`a abbr address area article aside audio b base bdi bdo blockquote body br button canvas caption
cite code col colgroup data datalist dd del details dfn dialog div dl dt em embed fieldset figcaption figure footer
form h1 h2 h3 h4 h5 h6 head header hgroup hr html i iframe img input ins kbd label legend li link main map mark menu
meta meter nav noscript object ol optgroup option output p picture pre progress q rp rt ruby s samp script search
section select slot small source span strong style sub summary sup table tbody td template textarea tfoot th thead
time title tr track u ul var video wbr portal fencedframe selectedcontent
svg circle ellipse line polyline polygon polygon path rect g text tspan textpath defs symbol use clippath mask
pattern image foreignobject switch marker lineargradient radialgradient stop filter view desc title metadata
animate animatemotion animatetransform set mpath
math mrow mi mo mn mfrac msup msub msubsup msqrt mroot mtext mspace mtable mtr mtd annotation semantics mstyle
merror mpadded mphantom munder mover munderover mmultiscripts none mprescripts`)
)

// cssShorthands maps a shorthand to the longhands it resets (CSS specs' "shorthand for" lists;
// sub-properties a shorthand does NOT reset, e.g. flex-direction for flex, are left out).
var cssShorthands = map[string]map[string]bool{}

func init() {
	for _, row := range []string{
		"margin margin-top margin-right margin-bottom margin-left",
		"padding padding-top padding-right padding-bottom padding-left",
		"inset top right bottom left",
		"border border-width border-style border-color border-top border-right border-bottom border-left border-top-width border-right-width border-bottom-width border-left-width border-top-style border-right-style border-bottom-style border-left-style border-top-color border-right-color border-bottom-color border-left-color border-image border-image-source border-image-slice border-image-width border-image-outset border-image-repeat",
		"border-width border-top-width border-right-width border-bottom-width border-left-width",
		"border-style border-top-style border-right-style border-bottom-style border-left-style",
		"border-color border-top-color border-right-color border-bottom-color border-left-color",
		"border-top border-top-width border-top-style border-top-color",
		"border-right border-right-width border-right-style border-right-color",
		"border-bottom border-bottom-width border-bottom-style border-bottom-color",
		"border-left border-left-width border-left-style border-left-color",
		"border-radius border-top-left-radius border-top-right-radius border-bottom-right-radius border-bottom-left-radius",
		"border-image border-image-source border-image-slice border-image-width border-image-outset border-image-repeat",
		"background background-color background-image background-repeat background-attachment background-position background-position-x background-position-y background-size background-origin background-clip",
		"font font-style font-variant font-variant-caps font-variant-ligatures font-variant-numeric font-variant-east-asian font-weight font-stretch font-size line-height font-family font-size-adjust font-kerning",
		"flex flex-grow flex-shrink flex-basis",
		"flex-flow flex-direction flex-wrap",
		"grid-template grid-template-rows grid-template-columns grid-template-areas",
		"grid grid-template grid-template-rows grid-template-columns grid-template-areas grid-auto-rows grid-auto-columns grid-auto-flow",
		"grid-area grid-row grid-column grid-row-start grid-row-end grid-column-start grid-column-end",
		"grid-row grid-row-start grid-row-end",
		"grid-column grid-column-start grid-column-end",
		"gap row-gap column-gap",
		"place-items align-items justify-items",
		"place-content align-content justify-content",
		"place-self align-self justify-self",
		"transition transition-property transition-duration transition-timing-function transition-delay transition-behavior",
		"animation animation-name animation-duration animation-timing-function animation-delay animation-iteration-count animation-direction animation-fill-mode animation-play-state",
		"list-style list-style-type list-style-position list-style-image",
		"outline outline-width outline-style outline-color",
		"overflow overflow-x overflow-y",
		"text-decoration text-decoration-line text-decoration-style text-decoration-color text-decoration-thickness",
		"columns column-width column-count",
		"column-rule column-rule-width column-rule-style column-rule-color",
		"mask mask-image mask-mode mask-repeat mask-position mask-clip mask-origin mask-size mask-composite",
		"text-emphasis text-emphasis-style text-emphasis-color",
		"scroll-margin scroll-margin-top scroll-margin-right scroll-margin-bottom scroll-margin-left",
		"scroll-padding scroll-padding-top scroll-padding-right scroll-padding-bottom scroll-padding-left",
		"container container-name container-type",
	} {
		f := strings.Fields(row)
		m := map[string]bool{}
		for _, l := range f[1:] {
			m[l] = true
		}
		cssShorthands[f[0]] = m
	}
}

// ---- colour contrast (WCAG 2.x relative luminance) ----

func parseHex(s string) ([4]float64, bool) {
	s = strings.TrimPrefix(strings.ToLower(s), "#")
	switch len(s) {
	case 3, 4:
		var b strings.Builder
		for _, c := range s {
			b.WriteRune(c)
			b.WriteRune(c)
		}
		s = b.String()
	case 6, 8:
	default:
		return [4]float64{}, false
	}
	v, err := strconv.ParseUint(s, 16, 64)
	if err != nil {
		return [4]float64{}, false
	}
	if len(s) == 6 {
		return [4]float64{float64(v>>16&255) / 255, float64(v>>8&255) / 255, float64(v&255) / 255, 1}, true
	}
	return [4]float64{float64(v>>24&255) / 255, float64(v>>16&255) / 255, float64(v>>8&255) / 255, float64(v&255) / 255}, true
}

var rgbRe = regexp.MustCompile(`^rgba?\(\s*(\d+(?:\.\d+)?%?)[\s,]+(\d+(?:\.\d+)?%?)[\s,]+(\d+(?:\.\d+)?%?)\s*(?:[,/]\s*(\d*\.?\d+%?)\s*)?\)$`)

func cssChannel(s string, scale float64) float64 {
	if p, ok := strings.CutSuffix(s, "%"); ok {
		v, _ := strconv.ParseFloat(p, 64)
		return v / 100
	}
	v, _ := strconv.ParseFloat(s, 64)
	return v / scale
}

// cssColor parses an opaque literal colour (hex, rgb()/rgba(), named); ok=false for anything
// else (variables, transparency, currentColor, gradients, keywords).
func cssColor(v string) ([3]float64, bool) {
	v = strings.TrimSpace(strings.TrimSuffix(strings.TrimSpace(v), "!important"))
	if strings.HasPrefix(v, "#") {
		c, ok := parseHex(v)
		if !ok || c[3] < 1 {
			return [3]float64{}, false
		}
		return [3]float64{c[0], c[1], c[2]}, true
	}
	if m := rgbRe.FindStringSubmatch(v); m != nil {
		if m[4] != "" && cssChannel(m[4], 1) < 1 {
			return [3]float64{}, false
		}
		return [3]float64{cssChannel(m[1], 255), cssChannel(m[2], 255), cssChannel(m[3], 255)}, true
	}
	c, ok := cssColors[v]
	return c, ok
}

// cssKeyframeSel is the normalised selector of a keyframe_block (from -> 0%, to -> 100%).
func cssKeyframeSel(n *ts.Node, src []byte) string {
	var parts []string
	for _, c := range named(n) {
		if c.Kind() == "block" {
			break
		}
		t := strings.ToLower(strings.TrimSpace(c.Utf8Text(src)))
		switch t {
		case "from":
			t = "0%"
		case "to":
			t = "100%"
		}
		if t != "" {
			parts = append(parts, t)
		}
	}
	return strings.Join(parts, ",")
}

func luminance(c [3]float64) float64 {
	lin := func(x float64) float64 {
		if x <= 0.04045 { // WCAG 2.x text uses 0.03928; both agree on 8-bit colours
			return x / 12.92
		}
		return math.Pow((x+0.055)/1.055, 2.4)
	}
	return 0.2126*lin(c[0]) + 0.7152*lin(c[1]) + 0.0722*lin(c[2])
}

// ContrastRatio is the WCAG 2.x contrast ratio of two opaque colours.
func ContrastRatio(a, b [3]float64) float64 {
	la, lb := luminance(a), luminance(b)
	if la < lb {
		la, lb = lb, la
	}
	return (la + 0.05) / (lb + 0.05)
}

// ruleDecls returns the declarations directly inside a rule set's block (last one wins).
func ruleDecls(n *ts.Node, src []byte) map[string]string {
	rs := n
	for rs != nil && rs.Kind() != "rule_set" {
		rs = rs.Parent()
	}
	out := map[string]string{}
	if rs == nil {
		return out
	}
	for _, b := range named(rs) {
		if b.Kind() != "block" {
			continue
		}
		for _, d := range named(b) {
			if d.Kind() == "declaration" {
				out[cssProp(d, src)] = cssValue(d, src)
			}
		}
	}
	return out
}

func cssContrast(n *ts.Node, src []byte) (float64, bool) {
	d := ruleDecls(n, src)
	fg, ok := cssColor(d["color"])
	if !ok {
		return 0, false
	}
	bgv, has := d["background-color"]
	if b, ok2 := d["background"]; ok2 {
		if has && b != bgv {
			return 0, false // both set: the cascade order inside the block decides
		}
		bgv, has = b, true // a shorthand that is not a single colour fails cssColor below
	}
	if !has {
		return 0, false
	}
	if _, img := d["background-image"]; img {
		return 0, false
	}
	for _, p := range []string{"opacity", "mix-blend-mode", "filter", "-webkit-text-stroke", "text-shadow"} {
		if _, ok := d[p]; ok {
			return 0, false
		}
	}
	bg, ok := cssColor(bgv)
	if !ok {
		return 0, false
	}
	return ContrastRatio(fg, bg), true
}

var pxRe = regexp.MustCompile(`^(\d+(?:\.\d+)?)(px|pt|rem|em)$`)

// cssLargeText: the rule declares a font size that WCAG counts as large text (at least 18pt, or
// 14pt bold); rem/em assume the 16px browser default.
func cssLargeText(n *ts.Node, src []byte) bool {
	d := ruleDecls(n, src)
	m := pxRe.FindStringSubmatch(strings.TrimSpace(strings.TrimSuffix(d["font-size"], "!important")))
	if m == nil {
		return false
	}
	v, _ := strconv.ParseFloat(m[1], 64)
	switch m[2] {
	case "pt":
		v *= 4.0 / 3
	case "rem", "em":
		v *= 16
	}
	w := d["font-weight"]
	bold := w == "bold" || w == "bolder" || (len(w) == 3 && w >= "700")
	return v >= 24 || (bold && v >= 18.66)
}

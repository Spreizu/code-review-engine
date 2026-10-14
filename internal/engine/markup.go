package engine

import (
	"bytes"
	"regexp"
	"strings"
	"sync"

	ts "github.com/tree-sitter/go-tree-sitter"
)

// Markup post-filters shared by HTML documents, Angular templates (HTML grammar with [x], (x),
// *x and bind-/on- syntax), Vue templates (:x, v-bind:x, @x, v-on:x, v-bind="obj") and JSX
// (camelCase names, {...spread}). Rules match a start tag / self-closing tag / JSX opening
// element; the filters read its attributes and the element around it. Anything the template
// computes at run time (bound values, spreads, components, slots) counts as "might provide it",
// so absence checks never fire on what cannot be seen statically.

type mAttr struct {
	name  string // normalised: lower-case, JSX aliases mapped (className -> class, htmlFor -> for)
	value string // static value ("" when bound or valueless)
	bound bool   // value computed at run time
	event bool   // event handler (onclick, @click, (click), onClick)
}

type mTag struct {
	tag    string // tag name as written (lower-cased for HTML documents)
	native bool   // a plain HTML element (not a component / custom element)
	attrs  []mAttr
	spread bool // v-bind="obj", {...props}: unknown attributes
	node   *ts.Node
	elem   *ts.Node // element node (start/self-closing tag's parent element; the tag itself when self-closing)
}

var jsxAlias = map[string]string{"classname": "class", "htmlfor": "for"}

// markupTag decodes a tag-like node (start_tag, self_closing_tag, element, jsx_opening_element,
// jsx_self_closing_element, jsx_element).
// vueRootElem: e is the single root element of a Vue SFC <template> (attribute fallthrough applies
// unless the component sets inheritAttrs: false).
func vueRootElem(e *ts.Node, src []byte) bool {
	p := e.Parent()
	if p == nil || !bytes.HasPrefix(src[p.StartByte():], []byte("<template")) {
		return false
	}
	if g := p.Parent(); g == nil || g.Parent() != nil {
		return false
	}
	if inheritAttrsOff.Match(src) {
		return false
	}
	n := 0
	for _, c := range named(p) {
		if strings.HasSuffix(c.Kind(), "element") {
			n++
		}
	}
	return n == 1
}

var (
	hiddenClass = regexp.MustCompile(`(^|\s)(hidden|d-none|invisible|is-hidden|visually-hidden-focusable)(\s|$)`)
	displayNone = regexp.MustCompile(`display\s*:\s*none|visibility\s*:\s*hidden`)
)

var inheritAttrsOff = regexp.MustCompile(`inheritAttrs\s*:\s*false|defineOptions\(\s*\{[^}]*inheritAttrs\s*:\s*false`)

// per-file memo of parsed tags (dup_id / heading_skip / ancestor checks revisit the same tags for
// every match); a handful of recent sources is kept, keyed by the source buffer.
type markupMemo struct {
	mu   sync.Mutex
	tags map[[3]uint]*mTag
	ids   map[string]uint // static id -> start byte of its first unconditional tag
	hds   [][2]uint       // (start byte, heading level) in document order
	links []linkRec       // static <a> text+href in document order
	done  bool
}

type linkRec struct {
	text, href string
	start      uint
}

var (
	memoMu sync.Mutex
	memos  = map[*byte]*markupMemo{}
)

func memoFor(src []byte) *markupMemo {
	if len(src) == 0 {
		return nil
	}
	memoMu.Lock()
	defer memoMu.Unlock()
	m := memos[&src[0]]
	if m == nil {
		if len(memos) >= 32 {
			clear(memos)
		}
		m = &markupMemo{tags: map[[3]uint]*mTag{}}
		memos[&src[0]] = m
	}
	return m
}

func markupTag(n *ts.Node, src []byte) *mTag {
	m := memoFor(src)
	if m == nil {
		return markupTagRaw(n, src)
	}
	k := [3]uint{n.StartByte(), n.EndByte(), uint(n.KindId())}
	m.mu.Lock()
	t, ok := m.tags[k]
	m.mu.Unlock()
	if ok {
		return t
	}
	t = markupTagRaw(n, src)
	m.mu.Lock()
	m.tags[k] = t
	m.mu.Unlock()
	return t
}

// markupIndex builds the per-file id and heading index once.
func markupIndex(root *ts.Node, src []byte) *markupMemo {
	m := memoFor(src)
	m.mu.Lock()
	done := m.done
	m.mu.Unlock()
	if done {
		return m
	}
	ids := map[string]uint{}
	var hds [][2]uint
	var links []linkRec
	markupWalk(root, src, func(o *mTag) bool {
		if oid := o.attr("id"); oid != nil && !oid.bound && oid.value != "" && !markupConditional(o, src) {
			if _, ok := ids[oid.value]; !ok {
				ids[oid.value] = o.node.StartByte()
			}
		}
		if l := headingLevel(o); l > 0 {
			hds = append(hds, [2]uint{o.node.StartByte(), uint(l)})
		}
		if strings.ToLower(o.tag) == "a" {
			href := o.attr("href")
			if href != nil && !href.bound && href.value != "" && href.value != "#" && !strings.HasPrefix(href.value, "javascript:") {
				text := strings.ToLower(wsRe.ReplaceAllString(strings.TrimSpace(markupPlainText(o.elem, src)), " "))
				if text != "" {
					links = append(links, linkRec{text: text, href: href.value, start: o.node.StartByte()})
				}
			}
		}
		return true
	})
	m.mu.Lock()
	m.ids, m.hds, m.links, m.done = ids, hds, links, true
	m.mu.Unlock()
	return m
}

func markupTagRaw(n *ts.Node, src []byte) *mTag {
	switch n.Kind() {
	case "element":
		for _, c := range named(n) {
			if c.Kind() == "start_tag" || c.Kind() == "self_closing_tag" {
				return markupTag(c, src)
			}
		}
		return nil
	case "jsx_element":
		if o := n.ChildByFieldName("open_tag"); o != nil {
			return markupTag(o, src)
		}
		return nil
	case "start_tag", "self_closing_tag":
		t := &mTag{node: n, elem: n}
		if n.Kind() == "start_tag" && n.Parent() != nil {
			t.elem = n.Parent()
		} else if p := n.Parent(); p != nil && p.Kind() == "element" {
			t.elem = p
		}
		for _, c := range named(n) {
			switch c.Kind() {
			case "tag_name":
				t.tag = c.Utf8Text(src)
			case "attribute", "directive_attribute":
				htmlAttr(t, c, src)
			}
		}
		t.native = isNativeTag(t.tag)
		if t.native {
			t.tag = strings.ToLower(t.tag)
		}
		if vueRootElem(t.elem, src) {
			t.spread = true // attributes passed to the component fall through to its single root element
		}
		return t
	case "jsx_opening_element", "jsx_self_closing_element":
		t := &mTag{node: n, elem: n}
		if n.Kind() == "jsx_opening_element" && n.Parent() != nil {
			t.elem = n.Parent()
		}
		if nm := n.ChildByFieldName("name"); nm != nil {
			t.tag = nm.Utf8Text(src)
		}
		t.native = t.tag != "" && t.tag[0] >= 'a' && t.tag[0] <= 'z' && !strings.ContainsAny(t.tag, ".:-")
		for _, c := range named(n) {
			switch c.Kind() {
			case "jsx_expression":
				if strings.HasPrefix(strings.TrimSpace(strings.TrimPrefix(c.Utf8Text(src), "{")), "...") {
					t.spread = true
				}
			case "jsx_attribute":
				var a mAttr
				for i, x := range named(c) {
					if i == 0 {
						a.name = x.Utf8Text(src)
						continue
					}
					switch x.Kind() {
					case "string":
						a.value = strings.Trim(x.Utf8Text(src), `"'`)
					default:
						a.bound = true
						if x.Kind() == "jsx_expression" {
							if s := strings.TrimSpace(strings.Trim(x.Utf8Text(src), "{}")); len(s) > 1 && (s[0] == '"' || s[0] == '\'' || s[0] == '`') && !strings.Contains(s, "${") && strings.Count(s, s[:1]) == 2 {
								a.value, a.bound = s[1:len(s)-1], false
							}
						}
					}
				}
				if len(a.name) > 2 && strings.HasPrefix(a.name, "on") && a.name[2] >= 'A' && a.name[2] <= 'Z' {
					a.event, a.name = true, strings.ToLower(a.name[2:])
				} else {
					a.name = strings.ToLower(a.name)
					if v, ok := jsxAlias[a.name]; ok {
						a.name = v
					}
				}
				t.attrs = append(t.attrs, a)
			}
		}
		return t
	}
	return nil
}

// htmlAttr decodes one HTML/Vue/Angular attribute.
func htmlAttr(t *mTag, c *ts.Node, src []byte) {
	raw := c.Utf8Text(src)
	name, val, hasVal := strings.Cut(raw, "=")
	name = strings.TrimSpace(name)
	val = strings.TrimSpace(val)
	if len(val) >= 2 && (val[0] == '"' || val[0] == '\'') {
		val = val[1 : len(val)-1]
	}
	_ = hasVal
	a := mAttr{value: val}
	switch {
	case name == "v-bind" || name == ":" || name == "v-on":
		t.spread = true
		return
	case strings.HasPrefix(name, "v-bind:"):
		a.name, a.bound = name[len("v-bind:"):], true
	case strings.HasPrefix(name, ":"):
		a.name, a.bound = name[1:], true
	case strings.HasPrefix(name, "@"):
		a.name, a.event = name[1:], true
	case strings.HasPrefix(name, "v-on:"):
		a.name, a.event = name[len("v-on:"):], true
	case strings.HasPrefix(name, "[(") && strings.HasSuffix(name, ")]"):
		a.name, a.bound = name[2:len(name)-2], true
	case strings.HasPrefix(name, "[") && strings.HasSuffix(name, "]"):
		a.name, a.bound = strings.TrimPrefix(name[1:len(name)-1], "attr."), true
	case strings.HasPrefix(name, "(") && strings.HasSuffix(name, ")"):
		a.name, a.event = name[1:len(name)-1], true
	case strings.HasPrefix(name, "bind-"):
		a.name, a.bound = name[len("bind-"):], true
	case strings.HasPrefix(name, "on-") && len(name) > 3:
		a.name, a.event = name[3:], true
	case len(name) > 2 && strings.HasPrefix(strings.ToLower(name), "on") && !strings.Contains(name, "-"):
		a.name, a.event = strings.ToLower(name[2:]), true
	default:
		a.name = name
		if strings.Contains(val, "{{") { // Angular/legacy interpolation inside a plain attribute
			a.bound = true
		}
	}
	if i := strings.IndexByte(a.name, '.'); i > 0 && !strings.HasPrefix(a.name, "attr") { // :foo.prop, (keyup.enter)
		a.name = a.name[:i]
	}
	if a.bound {
		a.value = ""
	}
	a.name = strings.ToLower(a.name)
	t.attrs = append(t.attrs, a)
}

func (t *mTag) attr(names ...string) *mAttr {
	for i := range t.attrs {
		if t.attrs[i].event {
			continue
		}
		for _, n := range names {
			if t.attrs[i].name == n {
				return &t.attrs[i]
			}
		}
	}
	return nil
}

func (t *mTag) hasEvent(names ...string) bool {
	for _, a := range t.attrs {
		if a.event {
			for _, n := range names {
				if a.name == n {
					return true
				}
			}
		}
	}
	return false
}

// HTML element names (WHATWG HTML + SVG/MathML roots); anything else is a component or custom element.
var nativeTags = map[string]bool{}

func init() {
	for _, t := range strings.Fields(`a abbr address area article aside audio b base bdi bdo blockquote body br button canvas caption
cite code col colgroup data datalist dd del details dfn dialog div dl dt em embed fieldset figcaption figure footer form h1 h2 h3 h4
h5 h6 head header hgroup hr html i iframe img input ins kbd label legend li link main map mark menu meta meter nav noscript object ol
optgroup option output p picture pre progress q rp rt ruby s samp script search section select slot small source span strong style
sub summary sup table tbody td template textarea tfoot th thead time title tr track u ul var video wbr svg math marquee blink frame
frameset center font acronym big tt strike applet dir noframes`) {
		nativeTags[t] = true
	}
}

func isNativeTag(t string) bool {
	// Vue/Angular components are PascalCase or contain '-'; HTML is case-insensitive in documents.
	return nativeTags[t] || (nativeTags[strings.ToLower(t)] && strings.ToUpper(t) == t)
}

// markupHasText: the element has content that can give it an accessible name, or content the
// static view cannot see (interpolation, components, slots, v-html/innerHTML).
func markupHasText(e *ts.Node, src []byte) bool { return markupText(e, src, "") }

// markupPlainText concatenates visible text descendants (no interpolation). Empty when the
// accessible name is computed at run time.
func markupPlainText(e *ts.Node, src []byte) string {
	if e == nil {
		return ""
	}
	var b strings.Builder
	var walk func(*ts.Node)
	walk = func(n *ts.Node) {
		for _, c := range named(n) {
			switch c.Kind() {
			case "start_tag", "end_tag", "jsx_opening_element", "jsx_closing_element", "comment":
				continue
			case "text", "jsx_text", "raw_text":
				b.WriteString(c.Utf8Text(src))
			case "element", "jsx_element":
				walk(c)
			}
		}
	}
	walk(e)
	return b.String()
}

// markupText: as markupHasText; children carrying the skip attribute (e.g. their own lang) do not count.
func markupText(e *ts.Node, src []byte, skip string) bool {
	if t := markupTag(e, src); t != nil && (t.node.Kind() == "self_closing_tag" || t.node.Kind() == "jsx_self_closing_element") {
		return t.attr("v-text", "v-html", "v-t", "innerhtml", "innertext", "textcontent", "dangerouslysetinnerhtml", "children") != nil
	}
	var walk func(n *ts.Node) bool
	walk = func(n *ts.Node) bool {
		for _, c := range named(n) {
			switch c.Kind() {
			case "start_tag", "end_tag", "jsx_opening_element", "jsx_closing_element", "comment":
				continue
			case "text", "jsx_text", "raw_text":
				if strings.TrimSpace(c.Utf8Text(src)) != "" {
					return true
				}
			case "interpolation", "jsx_expression", "erroneous_end_tag", "entity":
				if c.Kind() == "jsx_expression" && strings.HasPrefix(strings.TrimSpace(strings.Trim(c.Utf8Text(src), "{}")), "/*") {
					continue
				}
				return true
			case "element", "jsx_element", "jsx_self_closing_element", "self_closing_tag", "script_element", "style_element":
				t := markupTag(c, src)
				if t == nil {
					return true
				}
				if !t.native || t.spread || t.tag == "slot" {
					return true
				}
				if a := t.attr("aria-hidden"); a != nil && (a.bound || a.value == "true") {
					continue
				}
				if a := t.attr("hidden"); a != nil && !a.bound {
					continue
				}
				if skip != "" && t.attr(skip) != nil {
					continue
				}
				if t.attr("v-text", "v-html", "v-t", "innerhtml", "innertext", "textcontent", "dangerouslysetinnerhtml", "children") != nil {
					return true
				}
				switch t.tag {
				case "img", "area":
					if a := t.attr("alt"); a != nil && (a.bound || strings.TrimSpace(a.value) != "") {
						return true
					}
					if t.attr("aria-label", "aria-labelledby", "title") != nil {
						return true
					}
					continue
				case "svg":
					if t.attr("aria-label", "aria-labelledby") != nil || strings.Contains(c.Utf8Text(src), "<title") {
						return true
					}
					continue
				case "input":
					continue
				}
				if t.attr("aria-label", "aria-labelledby") != nil {
					return true
				}
				if walk(c) {
					return true
				}
			default:
				if walk(c) {
					return true
				}
			}
		}
		return false
	}
	if t := markupTag(e, src); t != nil && t.attr("v-text", "v-html", "v-t", "innerhtml", "innertext", "textcontent", "dangerouslysetinnerhtml", "children") != nil {
		return true
	}
	return walk(e)
}

func markupAncestors(t *mTag, src []byte, fn func(a *mTag) bool) bool {
	for p := t.elem.Parent(); p != nil; p = p.Parent() {
		switch p.Kind() {
		case "element", "jsx_element":
			if a := markupTag(p, src); a != nil && fn(a) {
				return true
			}
		}
	}
	return false
}

var ctrlDynamicFor = regexp.MustCompile(`(?:^|[\s<])(?::for|v-bind:for|\[for\]|\[attr\.for\]|htmlFor=\{)`)

// markupLabelled: a form control has a programmatic label (or one the static view cannot rule out).
func markupLabelled(t *mTag, src []byte) bool {
	if t.spread || t.attr("aria-label", "aria-labelledby", "title", "placeholder") != nil {
		return true
	}
	if markupAncestors(t, src, func(a *mTag) bool {
		return a.tag == "label" || !a.native && strings.Contains(strings.ToLower(a.tag), "label")
	}) {
		return true
	}
	if id := t.attr("id"); id != nil {
		if id.bound || id.value == "" {
			return true
		}
		if ctrlDynamicFor.Match(src) {
			return true
		}
		q := regexp.QuoteMeta(id.value)
		if regexp.MustCompile(`(?:\bfor|htmlFor)\s*=\s*(?:"` + q + `"|'` + q + `'|\{\s*["'` + "`" + `]` + q + `["'` + "`" + `]\s*\})`).Match(src) {
			return true
		}
		if regexp.MustCompile(`aria-labelledby\s*=\s*["'][^"']*\b` + q + `\b`).Match(src) {
			return false
		}
	}
	return false
}

var conditionalAttr = map[string]bool{"v-if": true, "v-else": true, "v-else-if": true, "*ngif": true, "*ngswitchcase": true, "*ngswitchdefault": true, "v-for": true, "*ngfor": true}

func markupConditional(t *mTag, src []byte) bool {
	self := func(a *mTag) bool {
		for _, x := range a.attrs {
			if conditionalAttr[x.name] {
				return true
			}
		}
		return false
	}
	if self(t) || markupAncestors(t, src, self) {
		return true
	}
	for p := t.elem.Parent(); p != nil; p = p.Parent() {
		if p.Kind() == "jsx_expression" || p.Kind() == "ternary_expression" || p.Kind() == "arrow_function" {
			return true
		}
	}
	return false
}

var ngControlFlow = regexp.MustCompile(`(?m)^\s*@(if|for|switch|case|defer|else)\b`)

// markupWalk visits every tag in document order until fn returns false.
func markupWalk(root *ts.Node, src []byte, fn func(t *mTag) bool) {
	var walk func(n *ts.Node) bool
	walk = func(n *ts.Node) bool {
		switch n.Kind() {
		case "start_tag", "self_closing_tag", "jsx_opening_element", "jsx_self_closing_element":
			if t := markupTag(n, src); t != nil && !fn(t) {
				return false
			}
		}
		for _, c := range named(n) {
			if !walk(c) {
				return false
			}
		}
		return true
	}
	walk(root)
}

func rootOf(n ts.Node) *ts.Node {
	r := &n
	for p := n.Parent(); p != nil; p = p.Parent() {
		r = p
	}
	return r
}

func splitNames(arg string) []string { return strings.Split(strings.ToLower(arg), "|") }

// markupFilter evaluates the markup.* filters; handled=false for other names.
func markupFilter(name, arg string, n ts.Node, src []byte) (pass, handled bool) {
	if !strings.HasPrefix(name, "markup.") {
		return false, false
	}
	t := markupTag(&n, src)
	if t == nil {
		return false, true
	}
	if pass, ok := markupAria(name, t); ok {
		return pass, true
	}
	switch name {
	case "markup.native":
		return t.native, true
	case "markup.lacks_attr":
		return !t.spread && t.attr(splitNames(arg)...) == nil, true
	case "markup.has_attr":
		return t.attr(splitNames(arg)...) != nil, true
	case "markup.has_event":
		return t.hasEvent(splitNames(arg)...), true
	case "markup.lacks_event":
		return !t.spread && !t.hasEvent(splitNames(arg)...), true
	case "markup.attr_re", "markup.attr_lacks_re":
		// markup.attr_re:NAME:regex - static value of NAME matches; attr_lacks_re: static value
		// present and does not match. Bound or absent values never pass.
		an, expr, _ := strings.Cut(arg, ":")
		a := t.attr(strings.ToLower(an))
		if a == nil || a.bound {
			return false, true
		}
		re, err := cachedRe(expr)
		if err != nil {
			return false, true
		}
		return re.MatchString(a.value) == (name == "markup.attr_re"), true
	case "markup.no_text", "markup.has_text":
		return markupHasText(t.elem, src) == (name == "markup.has_text"), true
	case "markup.has_text_without":
		return markupText(t.elem, src, strings.ToLower(arg)), true
	case "markup.not_hidden":
		// neither the element nor an ancestor is removed from the accessibility tree
		hidden := func(a *mTag) bool {
			h := a.attr("aria-hidden")
			if c := a.attr("class"); c != nil && !c.bound && hiddenClass.MatchString(c.value) {
				return true
			}
			if st := a.attr("style"); st != nil && !st.bound && displayNone.MatchString(st.value) {
				return true
			}
			return h != nil && (h.bound || h.value == "" || h.value == "true") || a.attr("hidden") != nil
		}
		return !hidden(t) && !markupAncestors(t, src, hidden), true
	case "markup.parent_lacks_attr":
		var parent *mTag
		markupAncestors(t, src, func(a *mTag) bool { parent = a; return true })
		return parent == nil || !parent.spread && parent.attr(splitNames(arg)...) == nil, true
	case "markup.in", "markup.not_in":
		want := splitNames(arg)
		in := markupAncestors(t, src, func(a *mTag) bool {
			for _, w := range want {
				if strings.ToLower(a.tag) == w {
					return true
				}
			}
			return false
		})
		return in == (name == "markup.in"), true
	case "markup.has_child", "markup.lacks_child":
		want := splitNames(arg)
		found, unknown := false, false
		markupWalk(t.elem, src, func(c *mTag) bool {
			if c.node == t.node {
				return true
			}
			if !c.native {
				unknown = true
			}
			for _, w := range want {
				if c.tag == w {
					found = true
					return false
				}
			}
			return true
		})
		if name == "markup.has_child" {
			return found, true
		}
		return !found && !unknown, true
	case "markup.unlabelled":
		return !markupLabelled(t, src), true
	case "markup.dup_id":
		id := t.attr("id")
		if id == nil || id.bound || id.value == "" || markupConditional(t, src) || ngControlFlow.Match(src) {
			return false, true
		}
		first, ok := markupIndex(rootOf(n), src).ids[id.value]
		return ok && first < t.node.StartByte(), true
	case "markup.heading_skip":
		lvl := headingLevel(t)
		if lvl == 0 {
			return false, true
		}
		prev := 0
		for _, h := range markupIndex(rootOf(n), src).hds {
			if h[0] >= t.node.StartByte() {
				break
			}
			prev = int(h[1])
		}
		return prev > 0 && lvl > prev+1 && !markupConditional(t, src), true
	case "markup.dup_link_text":
		if strings.ToLower(t.tag) != "a" {
			return false, true
		}
		href := t.attr("href")
		if href == nil || href.bound || href.value == "" || href.value == "#" || strings.HasPrefix(href.value, "javascript:") {
			return false, true
		}
		text := strings.ToLower(wsRe.ReplaceAllString(strings.TrimSpace(markupPlainText(t.elem, src)), " "))
		if text == "" {
			return false, true
		}
		for _, l := range markupIndex(rootOf(n), src).links {
			if l.text == text && l.href != href.value {
				return true, true
			}
		}
		return false, true
	}
	return false, true
}

func headingLevel(t *mTag) int {
	if t.native && len(t.tag) == 2 && t.tag[0] == 'h' && t.tag[1] >= '1' && t.tag[1] <= '6' {
		return int(t.tag[1] - '0')
	}
	return 0
}

// WAI-ARIA 1.2 concrete roles (plus ARIA 1.3 additions and the DPub/Graphics modules by prefix),
// states and properties, and the HTML autofill field names.
var (
	ariaRoles = setOf(`alert alertdialog application article banner blockquote button caption cell checkbox code columnheader
combobox complementary contentinfo definition deletion dialog directory document emphasis feed figure form generic grid gridcell
group heading img image insertion link list listbox listitem log main mark marquee math menu menubar menuitem menuitemcheckbox
menuitemradio meter navigation none note option paragraph presentation progressbar radio radiogroup region row rowgroup rowheader
scrollbar search searchbox sectionfooter sectionheader separator slider spinbutton status strong subscript suggestion comment superscript
switch tab table tablist text tabpanel term textbox time timer toolbar tooltip tree treegrid treeitem`)
	ariaAttrs = setOf(`aria-actions aria-activedescendant aria-atomic aria-autocomplete aria-braillelabel aria-brailleroledescription
aria-busy aria-checked aria-colcount aria-colindex aria-colindextext aria-colspan aria-controls aria-current aria-describedby
aria-description aria-details aria-disabled aria-dropeffect aria-errormessage aria-expanded aria-flowto aria-grabbed aria-haspopup
aria-hidden aria-invalid aria-keyshortcuts aria-label aria-labelledby aria-level aria-live aria-modal aria-multiline
aria-multiselectable aria-orientation aria-owns aria-placeholder aria-posinset aria-pressed aria-readonly aria-relevant
aria-required aria-roledescription aria-rowcount aria-rowindex aria-rowindextext aria-rowspan aria-selected aria-setsize aria-sort
aria-valuemax aria-valuemin aria-valuenow aria-valuetext`)
	autofillTokens = setOf(`off on name honorific-prefix given-name additional-name family-name honorific-suffix nickname username
new-password current-password one-time-code organization-title organization street-address address-line1 address-line2
address-line3 address-level4 address-level3 address-level2 address-level1 country country-name postal-code cc-name cc-given-name
cc-additional-name cc-family-name cc-number cc-exp cc-exp-month cc-exp-year cc-csc cc-type transaction-currency transaction-amount
language bday bday-day bday-month bday-year sex url photo tel tel-country-code tel-national tel-area-code tel-local tel-local-prefix
tel-local-suffix tel-extension email impp webauthn shipping billing home work mobile fax pager`)
	// roles whose required states (WAI-ARIA 1.2 "Required States and Properties") have no native
	// source when the role sits on a generic element
	ariaRequired = map[string][]string{"checkbox": {"aria-checked"}, "radio": {"aria-checked"}, "switch": {"aria-checked"},
		"menuitemcheckbox": {"aria-checked"}, "menuitemradio": {"aria-checked"}, "slider": {"aria-valuenow"},
		"scrollbar": {"aria-controls", "aria-valuenow"}, "heading": {"aria-level"}, "combobox": {"aria-expanded"}, "meter": {"aria-valuenow"}}
)

func setOf(s string) map[string]bool {
	m := map[string]bool{}
	for _, f := range strings.Fields(s) {
		m[f] = true
	}
	return m
}

func validRoleToken(r string) bool {
	return ariaRoles[r] || strings.HasPrefix(r, "doc-") || strings.HasPrefix(r, "graphics-")
}

// markupAria evaluates the ARIA/autofill value filters; handled=false for other names.
func markupAria(name string, t *mTag) (pass, handled bool) {
	switch name {
	case "markup.invalid_role":
		a := t.attr("role")
		if a == nil || a.bound || strings.TrimSpace(a.value) == "" || strings.Contains(a.value, "{") {
			return false, true
		}
		for _, r := range strings.Fields(strings.ToLower(a.value)) {
			if validRoleToken(r) {
				return false, true // the first valid token is used; fallbacks are allowed
			}
		}
		return true, true
	case "markup.invalid_aria_attr":
		for _, a := range t.attrs {
			if strings.HasPrefix(a.name, "aria-") && !ariaAttrs[a.name] {
				return true, true
			}
		}
		return false, true
	case "markup.invalid_autocomplete":
		a := t.attr("autocomplete")
		if a == nil || a.bound || strings.Contains(a.value, "{") {
			return false, true
		}
		toks := strings.Fields(strings.ToLower(a.value))
		if len(toks) == 0 || len(toks) == 1 && !strings.Contains(toks[0], "-") {
			return false, true // a lone unknown word (none, false, nope) is treated like "on" by browsers; flag token-like misuse only
		}
		for _, tk := range toks {
			if !autofillTokens[tk] && !strings.HasPrefix(tk, "section-") {
				return true, true
			}
		}
		return false, true
	case "markup.role_missing_required":
		if !t.native || t.spread || t.tag == "input" {
			return false, true
		}
		a := t.attr("role")
		if a == nil || a.bound {
			return false, true
		}
		f := strings.Fields(strings.ToLower(a.value))
		if len(f) == 0 {
			return false, true
		}
		for _, req := range ariaRequired[f[0]] {
			if t.attr(req) == nil {
				return true, true
			}
		}
		return false, true
	}
	return false, false
}

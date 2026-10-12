"""Vue pack: eslint-plugin-vue rules (eslint.vuejs.org), Vue style guide, Vue 3 migration guide and
vuejs.org guide pitfalls. Template rules use the vue grammar on the SFC; script rules run on the
<script>/<script setup> content (typescript grammar)."""
from specs._lint import lint
from rulegen import rule

R = RULES = []
V2 = {"vue": ">=2.0"}
V3 = {"vue": ">=3.0"}


def P(name, sev, cat, query, bad, good, msg, *, id=None, target="template", applies=None, **kw):
    R.append(lint("eslint-plugin-vue", name, id or "VUE-" + name.upper(), language="vue", framework="vue", severity=sev, category=cat,
                  query=query, bad=bad, good=good, message=msg, target=target, applies=applies or V2, **kw))


def tpl(s):
    return f"<template>\n  {s}\n</template>\n"


def scr(s, setup=False):
    return f"<script{' setup' if setup else ''}>\n{s}\n</script>\n"


def tag(pred):
    """start_tag or self_closing_tag pattern (as @match) with tag_name capture @t and an extra predicate."""
    return "\n".join(f"(({k} (tag_name) @t) @match {pred})" for k in ("start_tag", "self_closing_tag"))


def dir_(name, extra=""):
    return f'((directive_attribute (directive_name) @d) @match (#eq? @d "{name}"){extra})'


# ------------------------------------------------------------- essential / correctness (template)
P("no-child-content", "major", "correctness",
  r'''((element (start_tag (directive_attribute (directive_name) @d)) [(text) (element) (interpolation)] @match) (#match? @d "^v-(html|text)$"))''',
  tpl('<div v-html="html">fallback</div>'), tpl('<div v-html="html"></div>'), "Child content is overwritten by v-html/v-text.")
P("no-deprecated-dollar-scopedslots-api", "critical", "migration",
  r'''((member_expression property: (property_identifier) @p) @match (#eq? @p "$scopedSlots"))''',
  scr("export default { render() { return this.$scopedSlots.default() } }"), scr("export default { render() { return this.$slots.default() } }"),
  "$scopedSlots is removed in Vue 3; all slots are exposed on $slots as functions.", target="script", applies=V3, kind="removal")
P("no-deprecated-functional-template", "critical", "migration",
  r'''((template_element (start_tag (attribute (attribute_name) @a)) @match) (#eq? @a "functional"))''',
  "<template functional>\n  <div>{{ props.msg }}</div>\n</template>\n", "<template>\n  <div>{{ msg }}</div>\n</template>\n",
  "<template functional> is not supported in Vue 3; use a plain (stateful) component.", applies=V3, kind="removal")
P("no-deprecated-html-element-is", "critical", "migration",
  tag(r'''(#match? @t "^[a-z]+$") (#not-match? @t "^(component|template|slot)$") (#match? @match "\\sv?-?(bind)?:?is=") (#not-match? @match "is=\"vue:")'''),
  tpl('<table><tr is="my-row"></tr></table>'), tpl('<table><tr is="vue:my-row"></tr></table>'),
  "In Vue 3 is on native elements is a custom-element attribute; use is=\"vue:Comp\" to render a component.", applies=V3, kind="removal",
  mode="ai-confirm", ai="Is the is value meant to render a Vue component (not a customized built-in element)?")
P("no-deprecated-model-definition", "critical", "migration",
  r'''((export_statement (object (pair key: (property_identifier) @k value: (object)) @match)) (#eq? @k "model"))''',
  scr("export default { model: { prop: 'checked', event: 'change' } }"), scr("export default { props: ['modelValue'], emits: ['update:modelValue'] }"),
  "The model option is removed in Vue 3; v-model uses modelValue/update:modelValue (or v-model:arg).", target="script", applies=V3, kind="removal")
P("no-deprecated-props-default-this", "critical", "migration",
  r'''((pair key: (property_identifier) @props value: (object (pair value: (object (method_definition name: (property_identifier) @k body: (_) @b) @match)))) (#eq? @props "props") (#eq? @k "default") (#match? @b "\\bthis\\."))''',
  scr("export default { props: { size: { type: Number, default() { return this.base } } } }"),
  scr("export default { props: { size: { type: Number, default(props) { return props.base } } } }"),
  "Props default factories no longer receive this in Vue 3; use the raw props argument or inject().", target="script", applies=V3, kind="removal")
P("no-deprecated-v-is", "major", "migration", dir_("v-is"), tpl('<tr v-is="\'my-row\'"></tr>'), tpl('<tr is="vue:my-row"></tr>'),
  "v-is is deprecated since Vue 3.1; use is=\"vue:Comp\".", applies={"vue": ">=3.1"}, kind="deprecation")
P("no-deprecated-vue-config-keycodes", "critical", "migration",
  r'''((member_expression object: (member_expression object: (identifier) @v property: (property_identifier) @c) property: (property_identifier) @k) @match (#eq? @v "Vue") (#eq? @c "config") (#eq? @k "keyCodes"))''',
  scr("Vue.config.keyCodes = { f1: 112 }"), scr("const app = createApp(App)"), "Vue.config.keyCodes is removed in Vue 3; use key name modifiers.", target="script", applies=V3, kind="removal")
P("no-dupe-v-else-if", "major", "correctness",
  r'''((_ (element [(start_tag (directive_attribute (directive_name) @d1 (quoted_attribute_value (attribute_value) @a))) (self_closing_tag (directive_attribute (directive_name) @d1 (quoted_attribute_value (attribute_value) @a)))]) (element [(start_tag (directive_attribute (directive_name) @d2 (quoted_attribute_value (attribute_value) @b))) (self_closing_tag (directive_attribute (directive_name) @d2 (quoted_attribute_value (attribute_value) @b)))] @match)) (#match? @d1 "^v-(if|else-if)$") (#eq? @d2 "v-else-if") (#eq? @a @b))''',
  tpl('<div><p v-if="a">x</p><p v-else-if="a">y</p></div>'), tpl('<div><p v-if="a">x</p><p v-else-if="b">y</p></div>'),
  "The same condition repeated in a v-else-if chain is never true.")
P("no-duplicate-attr-inheritance", "minor", "correctness",
  r'''((directive_attribute (directive_name) @d (quoted_attribute_value (attribute_value) @v)) @match (#eq? @d "v-bind") (#eq? @v "$attrs"))''',
  tpl('<div><input v-bind="$attrs"></div>'), tpl('<div><input :value="v"></div>'),
  "With v-bind=\"$attrs\" also set inheritAttrs: false, or attributes are applied twice (root and target).", filters=["file.lacks_text:inheritAttrs"])
P("no-duplicate-attributes", "major", "correctness",
  r'''((start_tag (attribute (attribute_name) @a) (attribute (attribute_name) @b) @match) (#eq? @a @b))
((self_closing_tag (attribute (attribute_name) @a) (attribute (attribute_name) @b) @match) (#eq? @a @b))''',
  tpl('<input type="text" type="email">'), tpl('<input type="email">'), "Duplicate attribute: only one value is used.")
P("no-empty-component-block", "info", "maintainability", r'''(template_element (start_tag) @match . (end_tag))''',
  "<template></template>\n<script>export default {}</script>\n", "<template><div /></template>\n", "Empty SFC block.")
P("no-export-in-script-setup", "critical", "correctness",
  r'''((script_element (start_tag (attribute (attribute_name) @a)) (raw_text) @match) (#eq? @a "setup") (#match? @match "(^|\\n)\\s*export\\s+(const|let|var|function|class|default)\\b"))''',
  "<script setup>\nexport const size = 1\n</script>\n", "<script setup>\nconst size = 1\n</script>\n",
  "<script setup> cannot contain ES exports (compile error); use a separate normal <script> or defineExpose.", applies={"vue": ">=3.2"})
for name, fns in (("no-lifecycle-after-await", "onMounted|onBeforeMount|onUpdated|onBeforeUpdate|onUnmounted|onBeforeUnmount|onActivated|onDeactivated|onErrorCaptured|onRenderTracked|onRenderTriggered|onServerPrefetch"),
                  ("no-watch-after-await", "watch|watchEffect|watchPostEffect|watchSyncEffect"), ("no-expose-after-await", "expose")):
    P(name, "major", "async",
      f'''((method_definition "async" name: (property_identifier) @n body: (statement_block) @b) @match (#eq? @n "setup") (#match? @b "(?s)\\\\bawait\\\\b.*\\\\b({fns})\\\\("))''',
      scr("export default {\n  async setup() {\n    await load()\n    " + fns.split("|")[0] + "(() => {})\n  }\n}"),
      scr("export default {\n  async setup() {\n    " + fns.split("|")[0] + "(() => {})\n    await load()\n  }\n}"),
      "After an await in setup() the current instance is lost; register hooks/watchers/expose before the first await.", target="script", applies=V3)
P("no-import-compiler-macros", "minor", "correctness",
  r'''((import_statement (import_clause (named_imports (import_specifier name: (identifier) @n))) source: (string (string_fragment) @s)) @match (#match? @n "^(defineProps|defineEmits|defineExpose|withDefaults|defineModel|defineOptions|defineSlots)$") (#match? @s "^(vue|@vue/runtime-core|@vue/runtime-dom)$"))''',
  scr("import { defineProps } from 'vue'\nconst props = defineProps(['a'])", True), scr("const props = defineProps(['a'])", True),
  "Compiler macros are global in <script setup>; importing them is unnecessary (and an error/warning in recent Vue).", target="script", applies={"vue": ">=3.3"})
P("no-lone-template", "info", "style", r'''((element (template_element (start_tag) @match)) (#eq? @match "<template>"))''',
  tpl('<div><template><p>x</p></template></div>'), tpl('<div><p>x</p></div>'), "A <template> without directives is useless.")
P("no-multiple-objects-in-class", "info", "style",
  r'''((directive_attribute (directive_value) @n (quoted_attribute_value (attribute_value) @v)) @match (#eq? @n "class") (#match? @v "^\\[\\s*\\{[^\\]]*\\}\\s*,\\s*\\{"))''',
  tpl('<div :class="[{ a: x }, { b: y }]"></div>'), tpl('<div :class="{ a: x, b: y }"></div>'), "Merge the class objects into one.")
P("no-multiple-template-root", "critical", "correctness", r'''(document (template_element (start_tag) (element) (element) @match))''',
  "<template>\n  <h1>a</h1>\n  <p>b</p>\n</template>\n", "<template>\n  <div><h1>a</h1><p>b</p></div>\n</template>\n",
  "Vue 2 components must have exactly one root element (Vue 3 supports fragments).", applies={"vue": "<3.0"})
P("no-negated-v-if-condition", "info", "style",
  r'''((_ (element (start_tag (directive_attribute (directive_name) @d (quoted_attribute_value (attribute_value) @v)))) @match (element (start_tag (directive_attribute (directive_name) @e)))) (#eq? @d "v-if") (#match? @v "^\\s*!") (#eq? @e "v-else"))''',
  tpl('<div><p v-if="!ok">no</p><p v-else>yes</p></div>'), tpl('<div><p v-if="ok">yes</p><p v-else>no</p></div>'), "Invert the condition and swap branches.")
P("no-required-prop-with-default", "minor", "correctness",
  r'''((object (pair key: (property_identifier) @r value: (true)) (pair key: (property_identifier) @d) @match) (#eq? @r "required") (#eq? @d "default"))
((object (pair key: (property_identifier) @d) @match (pair key: (property_identifier) @r value: (true))) (#eq? @r "required") (#eq? @d "default"))''',
  scr("export default { props: { size: { type: Number, required: true, default: 1 } } }"), scr("export default { props: { size: { type: Number, default: 1 } } }"),
  "A required prop's default is never used.", target="script")
P("no-root-v-if", "minor", "correctness",
  r'''((document (template_element (start_tag) . (element (start_tag (directive_attribute (directive_name) @d)) @match) . (end_tag))) (#eq? @d "v-if"))''',
  "<template>\n  <div v-if=\"show\">x</div>\n</template>\n", "<template>\n  <div v-show=\"show\">x</div>\n</template>\n",
  "A v-if on the only root element renders nothing (a comment) when false; wrap or move the condition to the parent.")
P("no-setup-props-reactivity-loss", "major", "reactivity",
  r'''((method_definition name: (property_identifier) @n parameters: (formal_parameters . (required_parameter pattern: (identifier) @p)) body: (statement_block (lexical_declaration (variable_declarator name: (object_pattern) value: (identifier) @v)) @match)) (#eq? @n "setup") (#eq? @p @v))''',
  scr("export default {\n  setup(props) {\n    const { count } = props\n    return { count }\n  }\n}"), scr("export default {\n  setup(props) {\n    const { count } = toRefs(props)\n    return { count }\n  }\n}"),
  "Destructuring props in setup() loses reactivity; use toRefs(props) or props.x.", target="script", applies=V3)
P("no-side-effects-in-computed-properties", "major", "correctness",
  r'''((call_expression function: (identifier) @c arguments: (arguments . [(arrow_function body: (_) @b) (function_expression body: (_) @b)])) @match (#eq? @c "computed") (#match? @b "\\.value\\s*=[^=]|\\.value\\.(push|splice|sort|reverse|pop|shift|unshift)\\("))
((pair key: (property_identifier) @k value: (object (method_definition body: (_) @b) @match)) (#eq? @k "computed") (#match? @b "this\\.[\\w$.]+\\s*=[^=]|this\\.[\\w$.]+\\.(push|splice|sort|reverse)\\("))''',
  scr("const sorted = computed(() => items.value.sort())", True), scr("const sorted = computed(() => [...items.value].sort())", True),
  "Computed getters must be pure; mutating state inside them causes update loops and hard-to-trace bugs.", target="script")
P("no-static-inline-styles", "info", "style",
  "\n".join(f'(({k} (attribute (attribute_name) @n) @match) (#eq? @n "style"))' for k in ("start_tag", "self_closing_tag")),
  tpl('<div style="color: red"></div>'), tpl('<div class="error"></div>'), "Prefer classes over static inline styles.")
P("no-template-key", "minor", "correctness",
  r'''((template_element (start_tag (attribute (attribute_name) @a)) @match) (#eq? @a "key"))''',
  tpl('<div><template key="x"><p>a</p></template></div>'), tpl('<div><p key="x">a</p></div>'),
  "A static key on <template> has no effect; put it on a real element (Vue 3 only allows key on <template v-for>).")
P("no-template-target-blank", "minor", "security",
  tag(r'''(#match? @match "target=\"_blank\"") (#match? @match "\\shref=")'''),
  tpl('<a href="https://ext.example" target="_blank">x</a>'), tpl('<a href="https://ext.example" target="_blank" rel="noopener noreferrer">x</a>'),
  "target=\"_blank\" without rel=\"noopener\" lets the opened page access window.opener (reverse tabnabbing) in older browsers.",
  kind="security", filters=["vue.start_tag_lacks_attr:rel"])
P("no-textarea-mustache", "major", "correctness",
  r'''((element (start_tag (tag_name) @t) (interpolation) @match) (#eq? @t "textarea"))''',
  tpl('<textarea>{{ message }}</textarea>'), tpl('<textarea v-model="message"></textarea>'), "Interpolation in <textarea> is not reactive; use v-model.")
P("no-this-in-before-route-enter", "major", "correctness",
  r'''((method_definition name: (property_identifier) @n body: (_) @b) @match (#eq? @n "beforeRouteEnter") (#match? @b "\\bthis\\b"))''',
  scr("export default { beforeRouteEnter(to, from, next) { this.load(); next() } }"), scr("export default { beforeRouteEnter(to, from, next) { next((vm) => vm.load()) } }"),
  "this is undefined in beforeRouteEnter (the component is not created yet); use next(vm => ...).", target="script")
P("no-use-v-else-with-v-for", "major", "correctness",
  "\n".join(f'(({k} (directive_attribute (directive_name) @a) (directive_attribute (directive_name) @b)) @match (#eq? @a "{x}") (#match? @b "{y}"))'
            for k in ("start_tag", "self_closing_tag") for x, y in (("v-for", "^v-else(-if)?$"),) for _ in (0,)) + "\n" +
  "\n".join(f'(({k} (directive_attribute (directive_name) @a) (directive_attribute (directive_name) @b)) @match (#match? @a "^v-else(-if)?$") (#eq? @b "v-for"))' for k in ("start_tag", "self_closing_tag")),
  tpl('<div><p v-if="a">x</p><p v-else v-for="i in items" :key="i">{{ i }}</p></div>'), tpl('<div><p v-if="a">x</p><template v-else><p v-for="i in items" :key="i">{{ i }}</p></template></div>'),
  "v-else/v-else-if combined with v-for on the same element is confusing; wrap in <template v-else>.", quote="on the same element as v-for")
P("no-useless-mustaches", "info", "style",
  r'''((interpolation (raw_text) @r) @match (#match? @r "^\\s*'[^'$`]*'\\s*$|^\\s*\"[^\"$`]*\"\\s*$"))''',
  tpl("<p>{{ 'Hello' }}</p>"), tpl("<p>Hello</p>"), "A mustache with only a string literal is unnecessary.")
P("no-useless-template-attributes", "minor", "correctness",
  r'''((element (template_element (start_tag (attribute (attribute_name) @a)) @match)) (#match? @a "^(class|style|id)$"))''',
  tpl('<div><template v-if="ok" class="box"><p>x</p></template></div>'), tpl('<div><template v-if="ok"><p class="box">x</p></template></div>'),
  "<template> renders no element, so class/style/id on it are dropped.")
P("no-useless-v-bind", "info", "style",
  r'''((directive_attribute (directive_value) (quoted_attribute_value (attribute_value) @v)) @match (#match? @match "^:") (#match? @v "^'[^'$`]*'$"))''',
  tpl("<div :id=\"'main'\"></div>"), tpl('<div id="main"></div>'), "Binding a string literal with v-bind is unnecessary.")
P("no-v-for-template-key-on-child", "major", "migration",
  r'''((template_element (start_tag (directive_attribute (directive_name) @f)) (element [(start_tag (directive_attribute (directive_value) @k)) (self_closing_tag (directive_attribute (directive_value) @k))]) @match) (#eq? @f "v-for") (#eq? @k "key"))''',
  tpl('<ul><template v-for="i in items"><li :key="i.id">{{ i.n }}</li></template></ul>'), tpl('<ul><template v-for="i in items" :key="i.id"><li>{{ i.n }}</li></template></ul>'),
  "In Vue 3 the key of <template v-for> belongs on the <template> tag.", applies=V3)
P("no-v-text", "info", "style", dir_("v-text"), tpl('<p v-text="msg"></p>'), tpl('<p>{{ msg }}</p>'), "Prefer mustache interpolation over v-text.")
P("prefer-import-from-vue", "minor", "correctness",
  r'''((import_statement source: (string (string_fragment) @s)) @match (#match? @s "^@vue/(runtime-dom|runtime-core|reactivity|shared)$"))''',
  scr("import { ref } from '@vue/reactivity'", True), scr("import { ref } from 'vue'", True),
  "Import from 'vue'; @vue/* internal packages can resolve to duplicate copies.", target="script", applies=V3)
P("require-component-is", "major", "correctness", tag(r'''(#eq? @t "component")'''),
  tpl('<component is="MyComp"></component>'), tpl('<component :is="current"></component>'),
  "<component> needs a bound :is (a static is is treated as a plain string/custom element).", filters=["vue.start_tag_lacks_attr::is"])
P("require-prop-type-constructor", "major", "correctness",
  r'''((pair key: (property_identifier) @p value: (object (pair key: (property_identifier) @k value: (string)) @match)) (#eq? @p "props"))
((pair key: (property_identifier) @t value: (string (string_fragment) @v)) @match (#eq? @t "type") (#match? @v "^(String|Number|Boolean|Array|Object|Date|Function|Symbol)$"))''',
  scr("export default { props: { size: { type: 'Number' } } }"), scr("export default { props: { size: { type: Number } } }"),
  "Prop types must be constructors (Number), not strings ('Number').", target="script")
P("require-toggle-inside-transition", "major", "correctness",
  r'''((element (start_tag (tag_name) @t) . (element [(start_tag) (self_closing_tag)] @inner) . (end_tag)) @match (#match? @t "^([Tt]ransition)$") (#not-match? @inner "v-if|v-show|v-else|:key"))''',
  tpl('<Transition><div>x</div></Transition>'), tpl('<Transition><div v-if="show">x</div></Transition>'),
  "Content inside <transition> must be toggled (v-if/v-show/key), otherwise no transition runs.", applies=V3)
P("return-in-computed-property", "major", "correctness",
  r'''((pair key: (property_identifier) @k value: (object (method_definition body: (statement_block) @b) @match)) (#eq? @k "computed") (#not-match? @b "return"))
((call_expression function: (identifier) @c arguments: (arguments . (arrow_function body: (statement_block) @b))) @match (#eq? @c "computed") (#not-match? @b "return"))''',
  scr("export default { computed: { total() { this.items.length } } }"), scr("export default { computed: { total() { return this.items.length } } }"),
  "A computed getter without return always yields undefined.", target="script")
P("this-in-template", "info", "style", r'''((interpolation (raw_text) @r) @match (#match? @r "\\bthis\\."))''',
  tpl('<p>{{ this.msg }}</p>'), tpl('<p>{{ msg }}</p>'), "this is implicit in templates.")
P("valid-v-for", "critical", "correctness",
  r'''((directive_attribute (directive_name) @d (quoted_attribute_value (attribute_value) @v)) @match (#eq? @d "v-for") (#not-match? @v "\\s(in|of)\\s"))''',
  tpl('<li v-for="items" :key="x">a</li>'), tpl('<li v-for="x in items" :key="x">a</li>'), "v-for needs the form \"alias in source\".")
P("valid-v-show", "major", "correctness", r'''((template_element (start_tag (directive_attribute (directive_name) @d)) @match) (#eq? @d "v-show"))''',
  tpl('<div><template v-show="ok"><p>x</p></template></div>'), tpl('<div><div v-show="ok"><p>x</p></div></div>'), "v-show does not work on <template>.")
for d in ("v-else", "v-once", "v-pre", "v-cloak"):
    P(f"valid-{d}", "major", "correctness", f'''((directive_attribute (directive_name) @d (quoted_attribute_value)) @match (#eq? @d "{d}"))''',
      tpl(f'<div><p v-if="a">x</p><p {d}="b">y</p></div>' if d == "v-else" else f'<p {d}="x">y</p>'),
      tpl(f'<div><p v-if="a">x</p><p {d}>y</p></div>' if d == "v-else" else f'<p {d}>y</p>'), f"{d} takes no value.")
for d in ("v-if", "v-else-if", "v-html", "v-text", "v-model", "v-show", "v-for"):
    P(f"valid-{d}", "critical", "correctness", f'''((directive_attribute (directive_name) @d) @match (#eq? @d "{d}") (#eq? @match "{d}"))''',
      tpl(f'<div><p v-if="a">x</p><p {d}>y</p></div>' if d == "v-else-if" else f'<input {d}>'),
      tpl(f'<div><p v-if="a">x</p><p {d}="b">y</p></div>' if d == "v-else-if" else f'<input {d}="x in xs">' if d == "v-for" else f'<input {d}="x">'),
      f"{d} requires an expression.", id=f"VUE-VALID-{d.upper()}-NOVALUE")
P("valid-next-tick", "major", "async",
  r'''((expression_statement (member_expression property: (property_identifier) @p) @match) (#match? @p "^(\\$nextTick|nextTick)$"))''',
  scr("export default { methods: { f() { this.$nextTick } } }"), scr("export default { methods: { async f() { await this.$nextTick() } } }"),
  "nextTick must be called (and awaited or given a callback).", target="script")
P("valid-attribute-name", "major", "correctness", r'''((attribute_name) @match (#match? @match "^[0-9\\-.]"))''',
  tpl('<div 0abc="x"></div>'), tpl('<div data-abc="x"></div>'), "Invalid attribute name.")
P("html-button-has-type", "minor", "correctness", tag(r'''(#eq? @t "button")'''),
  tpl('<button @click="go">Go</button>'), tpl('<button type="button" @click="go">Go</button>'),
  "A <button> without type defaults to submit inside forms.", filters=["vue.start_tag_lacks_attr:type"])
P("no-boolean-default", "info", "style",
  r'''((object (pair key: (property_identifier) @t value: (identifier) @b) (pair key: (property_identifier) @d value: [(true) (false)]) @match) (#eq? @t "type") (#eq? @b "Boolean") (#eq? @d "default"))''',
  scr("export default { props: { open: { type: Boolean, default: true } } }"), scr("export default { props: { closed: { type: Boolean } } }"),
  "Boolean props default to false; prefer naming so the default is false (no default needed).", target="script")
P("require-prop-types", "minor", "maintainability",
  r'''((pair key: (property_identifier) @k value: (array) @match) (#eq? @k "props"))
((call_expression function: (identifier) @f arguments: (arguments . (array))) @match (#eq? @f "defineProps"))''',
  scr("export default { props: ['status'] }"), scr("export default { props: { status: { type: String, required: true } } }"),
  "Style guide (essential): prop definitions should be as detailed as possible (at least types).", target="script")
P("prefer-prop-type-boolean-first", "info", "correctness",
  r'''((pair key: (property_identifier) @t value: (array . (identifier) @first (identifier) @b)) @match (#eq? @t "type") (#not-eq? @first "Boolean") (#eq? @b "Boolean"))''',
  scr("export default { props: { flag: { type: [String, Boolean] } } }"), scr("export default { props: { flag: { type: [Boolean, String] } } }"),
  "Boolean casting of empty attributes depends on Boolean coming first.", target="script")
P("mustache-interpolation-spacing", "info", "style", r'''((interpolation) @match (#match? @match "^\\{\\{\\S|\\S\\}\\}$"))''',
  tpl('<p>{{msg}}</p>'), tpl('<p>{{ msg }}</p>'), "Use spaces inside mustaches.")
P("html-quotes", "info", "style", r'''((quoted_attribute_value) @match (#match? @match "^'"))''',
  tpl("<div class='box'></div>"), tpl('<div class="box"></div>'), "Use double quotes for attribute values.")
P("v-for-delimiter-style", "info", "style",
  r'''((directive_attribute (directive_name) @d (quoted_attribute_value (attribute_value) @v)) @match (#eq? @d "v-for") (#match? @v "\\sof\\s"))''',
  tpl('<li v-for="x of xs" :key="x">a</li>'), tpl('<li v-for="x in xs" :key="x">a</li>'), "Use in as the v-for delimiter consistently.")
P("no-parsing-error", "major", "correctness", r'''(ERROR) @match''', tpl('<div class="a></div'), tpl('<div class="a"></div>'),
  "The template does not parse.", mode="ai-confirm", ai="Is this a real template syntax error (not a parser limitation of valid Vue syntax)?")
P("no-arrow-functions-in-watch", "major", "correctness",
  r'''((pair key: (property_identifier) @k value: (object (pair value: (arrow_function)) @match)) (#eq? @k "watch"))''',
  scr("export default { watch: { q: (v) => { this.search(v) } } }"), scr("export default { watch: { q(v) { this.search(v) } } }"),
  "Arrow-function watchers do not get the component as this.", target="script")

# ------------------------------------------------------------- vuejs.org guide / migration guide
MIG = "https://v3-migration.vuejs.org/breaking-changes/"
G = "https://vuejs.org/"


def D(id, title, url, quote, query, bad, good, msg, *, sev="major", kind="removal", cat="migration", applies=V3, target="script", doc=None, **kw):
    R.append(rule("VUE-" + id, title, language="vue", framework="vue", kind=kind, category=cat, severity=sev, applies=applies, message=msg,
                  url=url, doc=doc or ("Vue 3 Migration Guide - " + url.rstrip("/").split("/")[-1].replace(".html", "") if url.startswith(MIG) else "Vue docs - " + url.split("/")[-1].replace(".html", "")),
                  doc_version="Vue 3 docs (vuejs.org)", quote=quote, bad=bad, good=good, query=query, target=target, **kw))


D("DIRECTIVE-HOOKS-001", "Custom directive hooks were renamed in Vue 3", MIG + "custom-directives.html",
  "functions for directives have been renamed to better align with the component lifecycle",
  r'''((pair key: (property_identifier) @k) @match (#match? @k "^(inserted|componentUpdated|unbind)$"))
((method_definition name: (property_identifier) @k) @match (#match? @k "^(inserted|componentUpdated|unbind)$"))''',
  scr("export const focus = { inserted(el) { el.focus() } }"), scr("export const focus = { mounted(el) { el.focus() } }"),
  "Vue 3 directive hooks: bind->beforeMount, inserted->mounted, componentUpdated->updated, unbind->unmounted.", sev="critical",
  mode="ai-confirm", ai="Is this object a Vue custom directive definition?")
D("TRANSITION-CLASS-001", "Transition classes v-enter / v-leave were renamed", MIG + "transition.html",
  "The v-enter transition class has been renamed to v-enter-from and the v-leave transition class has been renamed to v-leave-from",
  r'''((style_element (raw_text) @match) (#match? @match "\\.[\\w-]*-(enter|leave)\\s*[,{]"))''',
  "<style>\n.fade-enter { opacity: 0 }\n</style>\n", "<style>\n.fade-enter-from { opacity: 0 }\n</style>\n",
  "Rename .x-enter/.x-leave to .x-enter-from/.x-leave-from for Vue 3.", target="template")
D("HOOK-EVENTS-001", "@hook: lifecycle events are now @vue:", MIG + "vnode-lifecycle-events.html", "In Vue 3, this prefix has been changed to vue:",
  r'''((directive_attribute (directive_value) @v) @match (#eq? @v "hook"))''',
  tpl('<Child @hook:mounted="onMounted" />'), tpl('<Child @vue:mounted="onMounted" />'), "Use @vue:mounted etc. in Vue 3.", target="template")
D("CHILDREN-001", "$children was removed", MIG + "children.html", "$children",
  r'''((member_expression property: (property_identifier) @p) @match (#eq? @p "$children"))''',
  scr("export default { mounted() { console.log(this.$children) } }"), scr("export default { mounted() { console.log(this.$refs.child) } }"),
  "$children is removed in Vue 3; use template refs.", sev="critical")
D("PROPSDATA-001", "propsData option was removed", MIG + "props-data.html", "propsData",
  r'''((pair key: (property_identifier) @k) @match (#eq? @k "propsData"))''',
  scr("new Comp({ propsData: { msg: 'hi' } })"), scr("createApp(Comp, { msg: 'hi' })"), "Pass props as the second argument of createApp.", sev="critical")
D("CONFIG-PRODTIP-001", "Vue.config.productionTip / ignoredElements were removed", MIG + "global-api.html", "Vue.config.productionTip removed",
  r'''((member_expression object: (member_expression object: (identifier) @v property: (property_identifier) @c) property: (property_identifier) @k) @match (#eq? @v "Vue") (#eq? @c "config") (#match? @k "^(productionTip|ignoredElements)$"))''',
  scr("Vue.config.productionTip = false"), scr("app.config.compilerOptions.isCustomElement = (t) => t.startsWith('x-')"),
  "Remove productionTip; ignoredElements becomes app.config.compilerOptions.isCustomElement.")
D("PROTOTYPE-001", "Vue.prototype globals moved to app.config.globalProperties", MIG + "global-api.html", "Vue.prototype",
  r'''((assignment_expression left: (member_expression object: (member_expression object: (identifier) @v property: (property_identifier) @p))) @match (#eq? @v "Vue") (#eq? @p "prototype"))''',
  scr("Vue.prototype.$http = axios"), scr("app.config.globalProperties.$http = axios"), "Use app.config.globalProperties (or provide/inject).", sev="critical")
D("RENDER-H-001", "Render functions no longer receive h", MIG + "render-function-api.html", "h is now globally imported instead of being automatically passed as an argument",
  r'''((method_definition name: (property_identifier) @n parameters: (formal_parameters . (required_parameter pattern: (identifier) @h))) @match (#eq? @n "render") (#match? @h "^(h|createElement)$"))''',
  scr("export default { render(h) { return h('div') } }"), scr("import { h } from 'vue'\nexport default { render() { return h('div') } }"),
  "Import h from 'vue'; the render() argument is no longer createElement.", sev="critical")
D("WATCH-ARRAY-001", "Watching an array no longer triggers on mutation without deep", MIG + "watch.html",
  "When watching an array, the callback will only trigger when the array is replaced.",
  r'''((pair key: (property_identifier) @k value: (object (pair key: (property_identifier) @w value: [(arrow_function) (function_expression)]) @match)) (#eq? @k "watch"))''',
  scr("export default { watch: { items: function (v) { this.save(v) } } }"), scr("export default { watch: { items: { handler(v) { this.save(v) }, deep: true } } }"),
  "If the watched value is an array that is mutated in place, Vue 3 needs deep: true (or deep: 1 in 3.5+).", sev="minor", kind="migration",
  mode="ai-confirm", ai="Is the watched property an array that is mutated in place (push/splice) rather than replaced?")
D("FUNCTIONAL-OPTION-001", "functional: true component option was removed", MIG + "functional-components.html", "functional",
  r'''((export_statement (object (pair key: (property_identifier) @k value: (true)) @match)) (#eq? @k "functional"))''',
  scr("export default { functional: true, render(h, ctx) { return h('div') } }"), scr("import { h } from 'vue'\nexport default (props) => h('div', props)"),
  "Functional components are plain functions in Vue 3.", sev="critical")
D("OBSERVABLE-001", "Vue.observable was replaced by reactive()", MIG + "global-api-treeshaking.html", "Vue.observable (replaced by Vue.reactive )",
  r'''((call_expression function: (member_expression object: (identifier) @v property: (property_identifier) @p)) @match (#eq? @v "Vue") (#eq? @p "observable"))''',
  scr("const store = Vue.observable({ n: 0 })"), scr("import { reactive } from 'vue'\nconst store = reactive({ n: 0 })"), "Use reactive().", sev="critical")
D("REACTIVITY-TRANSFORM-001", "Reactivity Transform ($ref, $computed, ...) was removed in Vue 3.4", G + "guide/extras/reactivity-transform.html",
  "Reactivity Transform was an experimental feature, and has been removed in the latest 3.4 release.",
  r'''((call_expression function: (identifier) @f) @match (#match? @f "^\\$(ref|computed|shallowRef|customRef|toRef)$"))''',
  scr("let count = $ref(0)", True), scr("const count = ref(0)", True), "Use ref()/computed() (or the Vue Macros plugin).", sev="critical", applies={"vue": ">=3.4"})
D("REACTIVE-REASSIGN-001", "Reassigning a reactive() variable loses reactivity", G + "guide/essentials/reactivity-fundamentals.html",
  "we must always keep the same reference to the reactive object",
  r'''((assignment_expression left: (identifier) right: (call_expression function: (identifier) @f)) @match (#eq? @f "reactive"))''',
  scr("let state = reactive({ n: 0 })\nstate = reactive({ n: 1 })", True), scr("const state = reactive({ n: 0 })\nstate.n = 1", True),
  "Replacing a reactive object disconnects existing watchers/templates; mutate properties or use ref().", kind="anti-pattern", cat="reactivity", applies=V3)
D("WATCH-REACTIVE-PROP-001", "watch() on a reactive object's property value", G + "guide/essentials/watchers.html",
  "Do note that you can't watch a property of a reactive object like this",
  r'''((call_expression function: (identifier) @w arguments: (arguments . (member_expression) @src)) @match (#eq? @w "watch") (#not-match? @src "\\.value$"))''',
  scr("watch(state.count, (c) => log(c))", True), scr("watch(() => state.count, (c) => log(c))", True),
  "Passing state.count passes a plain value; use a getter () => state.count.", kind="anti-pattern", cat="reactivity", applies=V3,
  mode="ai-confirm", ai="Is the watched expression a property of a reactive() object (not a ref)?")
D("URL-INJECTION-001", "Bound href/src with user-provided URL", G + "guide/best-practices/security.html",
  "There's a potential security issue if the URL has not been \"sanitized\"",
  r'''((directive_attribute (directive_value) @n (quoted_attribute_value (attribute_value) @v)) @match (#match? @n "^(href|src|action|formaction)$") (#match? @match "^:") (#not-match? @v "(?i)saniti"))''',
  tpl('<a :href="userProvidedUrl">click</a>'), tpl('<a :href="sanitizeUrl(userProvidedUrl)">click</a>'),
  "A javascript: URL in a bound href/src executes code; sanitize user-provided URLs (allow-list http/https).", kind="security", cat="security", applies=V2,
  target="template", mode="ai-confirm", ai="Can this URL come from user input, and is it not sanitized against javascript: URLs?")
D("STYLE-INJECTION-001", "Bound style from user-provided values", G + "guide/best-practices/security.html", "Style Injection",
  r'''((directive_attribute (directive_value) @n (quoted_attribute_value (attribute_value) @v)) @match (#eq? @n "style") (#match? @match "^:") (#not-match? @v "^\\{"))''',
  tpl('<div :style="userProvidedStyles"></div>'), tpl('<div :style="{ color: userProvidedColor }"></div>'),
  "Binding a whole user-provided style string/object allows clickjacking-style overlays; bind only specific vetted properties.",
  kind="security", cat="security", applies=V2, target="template", sev="minor", mode="ai-confirm", ai="Is the bound style object/string user-controlled?")
D("PARENT-001", "Implicit parent-child communication via $parent", G + "style-guide/rules-use-with-caution.html", "Implicit parent-child communication",
  r'''((member_expression property: (property_identifier) @p) @match (#eq? @p "$parent"))''',
  scr("export default { methods: { close() { this.$parent.visible = false } } }"), scr("export default { emits: ['close'], methods: { close() { this.$emit('close') } } }"),
  "Prefer props and events over this.$parent.", sev="minor", kind="best-practice", cat="style-guide", applies=V2)
D("SCOPED-ELEMENT-SELECTOR-001", "Element selectors in scoped styles", G + "style-guide/rules-use-with-caution.html", "Element selectors should be avoided with scoped",
  r'''((style_element (start_tag (attribute (attribute_name) @a)) (raw_text) @match) (#eq? @a "scoped") (#match? @match "(^|[}\\n])\\s*[a-z][a-z0-9]*\\s*[{,]"))''',
  "<style scoped>\nbutton { color: red }\n</style>\n", "<style scoped>\n.btn-close { color: red }\n</style>\n",
  "Element selectors with scoped styles are slow (attribute selector on every element); use classes.", sev="info", kind="best-practice", cat="performance", applies=V2, target="template")
D("SELF-CLOSING-001", "Components with no content should be self-closing", G + "style-guide/rules-strongly-recommended.html", "Self-closing components",
  r'''((element (start_tag (tag_name) @t) @match . (end_tag)) (#match? @t "^[A-Z]"))''',
  tpl('<MyComponent></MyComponent>'), tpl('<MyComponent />'), "Self-close components without content in SFCs.", sev="info", kind="best-practice", cat="style-guide", applies=V2, target="template")
D("SIMPLE-EXPRESSIONS-001", "Complex expressions in templates", G + "style-guide/rules-strongly-recommended.html", "Simple expressions in templates",
  r'''((interpolation (raw_text) @r) @match (#match? @r ".{80,}|\\?.*:.*\\?|\\.(map|filter|reduce|split|join)\\("))''',
  tpl("<p>{{ fullName.split(' ').map((w) => w[0].toUpperCase() + w.slice(1)).join(' ') }}</p>"), tpl("<p>{{ normalizedFullName }}</p>"),
  "Move complex template expressions into computed properties or methods.", sev="info", kind="best-practice", cat="style-guide", applies=V2, target="template")
D("UNQUOTED-ATTR-001", "Unquoted attribute values", G + "style-guide/rules-strongly-recommended.html", "Quoted attribute values",
  "\n".join(f"({k} (attribute (attribute_name) (attribute_value) @match))" for k in ("start_tag", "self_closing_tag")),
  tpl('<input type=text>'), tpl('<input type="text">'), "Quote attribute values.", sev="info", kind="best-practice", cat="style-guide", applies=V2, target="template")
D("COMPOSITION-API-PKG-001", "@vue/composition-api is built into Vue 2.7", G.replace("vuejs.org/", "v2.vuejs.org/") + "v2/guide/migration-vue-2-7.html",
  "@vue/composition-api", None, '{ "dependencies": { "vue": "^2.7.16", "@vue/composition-api": "^1.7.0" } }', '{ "dependencies": { "vue": "^2.7.16" } }',
  "Vue 2.7 ships the Composition API; remove @vue/composition-api and import from 'vue'.", kind="migration", sev="minor", applies={"vue": ">=2.7 <3.0"},
  target=None, engine="manifest", manifest={"check": "has_dependency", "value": "@vue/composition-api"})
R[-1]["language"] = "manifest"
D("LISTENERS-SCRIPT-001", "this.$listeners was removed (merged into $attrs)", MIG + "listeners-removed.html", "$listeners",
  r'''((member_expression property: (property_identifier) @p) @match (#eq? @p "$listeners"))''',
  scr("export default { mounted() { console.log(this.$listeners) } }"), scr("export default { mounted() { console.log(this.$attrs) } }"),
  "Listeners are part of $attrs in Vue 3.", sev="critical")

for _r in R:
    if _r["id"].endswith("-NOVALUE"):
        _r["title"] = _r["title"] + " (missing expression)"

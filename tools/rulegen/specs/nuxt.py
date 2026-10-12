"""Nuxt pack: Nuxt 4 docs (nuxt.com/docs/4.x), Nuxt 2->3 migration guide, Nuxt 3->4 and 4->5 upgrade
guides (versioned doc URLs so quotes stay stable)."""
from rulegen import rule

R = RULES = []
D4 = "https://nuxt.com/docs/4.x/"
D5 = "https://nuxt.com/docs/5.x/"
N3 = {"nuxt": ">=3.0"}
N4 = {"nuxt": ">=4.0"}
N5 = {"nuxt": ">=5.0"}
CFG = ["nuxt.config.ts", "nuxt.config.js", "nuxt.config.mjs", "**/nuxt.config.ts", "**/nuxt.config.js", "**/nuxt.config.mjs"]
SERVER = ["server/**/*.ts", "server/**/*.js", "**/server/**/*.ts", "**/server/**/*.js"]


def N(id, title, path, quote, query, bad, good, msg, *, sev="major", kind="anti-pattern", cat="nuxt", applies=None, lang="javascript",
      target=None, files=None, docv=None, base=D4, **kw):
    url = base + path
    if lang == "javascript" and not files:
        bad, good = (unwrap(x) for x in (bad, good))
    R.append(rule("NUXT-" + id, title, language=lang, framework="nuxt", kind=kind, category=cat, severity=sev, applies=applies or N3,
                  message=msg, url=url, doc="Nuxt docs - " + path.split("#")[0], doc_version=docv or ("Nuxt 5 docs (5.x)" if base == D5 else "Nuxt 4 docs (4.x)"),
                  quote=quote, bad=bad, good=good, query=query, target=target, files=files, **kw))


def unwrap(s):
    import re
    m = re.match(r"^<script[^>]*>\n(.*)\n</script>\n$", s, re.S)
    return m.group(1) + "\n" if m else s


def scr(s, setup=True):
    return f"<script{' setup' if setup else ''}>\n{s}\n</script>\n"


def tpl(s):
    return f"<template>\n  {s}\n</template>\n"


def call(fn):
    return f'((call_expression function: (identifier) @f) @match (#match? @f "^({fn})$"))'


def cfgkey(path_regex):
    """A property (possibly nested) in the defineNuxtConfig({...}) object whose key matches."""
    return f'''((call_expression function: (identifier) @d arguments: (arguments (object (pair key: [(property_identifier) (string)] @k) @match))) (#eq? @d "defineNuxtConfig") (#match? @k "{path_regex}"))'''


def cfgnested(parent, child):
    return f'''((call_expression function: (identifier) @d arguments: (arguments (object (pair key: (property_identifier) @p value: (object (pair key: (property_identifier) @k) @match))))) (#eq? @d "defineNuxtConfig") (#eq? @p "{parent}") (#match? @k "{child}"))'''


# ------------------------------------------------------------- data fetching
DF = "getting-started/data-fetching"
N("USEFETCH-IN-HANDLER-001", "useFetch/useAsyncData called inside a function or lifecycle hook", "api/composables/use-fetch",
  "useFetch is a composable meant to be called directly in a setup function, plugin, or route middleware.",
  r'''((call_expression function: (identifier) @h arguments: (arguments (arrow_function body: (_) @b))) @match (#match? @h "^(onMounted|onBeforeMount|watch|watchEffect|onUpdated)$") (#match? @b "\\b(useFetch|useAsyncData|useLazyFetch|useLazyAsyncData)\\("))
((method_definition body: (statement_block) @b) @match (#match? @b "\\b(useFetch|useAsyncData)\\("))''',
  scr("onMounted(async () => {\n  const { data } = await useFetch('/api/user')\n})"), scr("const { data } = await useFetch('/api/user')"),
  "useFetch/useAsyncData are composables: call them at the top level of setup/plugins/middleware. In event handlers or hooks use $fetch.",
  mode="ai-confirm", ai="Is the composable called outside the synchronous top level of setup (in a hook, callback or event handler)?")
N("ASYNCDATA-SIDE-EFFECT-001", "useAsyncData used to trigger side effects (store actions)", DF,
  "useAsyncData is for fetching and caching data, not triggering side effects like calling Pinia actions",
  r'''((call_expression function: (identifier) @f arguments: (arguments (_)? [(arrow_function body: (_) @b) (function_expression body: (_) @b)])) @match (#eq? @f "useAsyncData") (#match? @b "(?i)store\\.|Store\\(\\)\\."))''',
  scr("await useAsyncData('init', () => store.fetchUser())"), scr("await callOnce(store.fetchUser)"),
  "Use callOnce (or a plain action) for side effects; useAsyncData may re-run with nullish values.", mode="ai-confirm",
  ai="Does the handler perform a side effect (store mutation/action) rather than returning fetched data?")
N("PARALLEL-FETCH-001", "Sequential awaits of independent data fetches", DF, "When requests don't rely on each other, you can make them in parallel with Promise.all() to boost performance.",
  r'''((program (lexical_declaration (variable_declarator value: (await_expression (call_expression function: (identifier) @a)))) . (lexical_declaration (variable_declarator value: (await_expression (call_expression function: (identifier) @b)))) @match) (#match? @a "^(useFetch|useAsyncData|\\$fetch)$") (#match? @b "^(useFetch|useAsyncData|\\$fetch)$"))''',
  scr("const { data: a } = await useFetch('/api/a')\nconst { data: b } = await useFetch('/api/b')"),
  scr("const [{ data: a }, { data: b }] = await Promise.all([useFetch('/api/a'), useFetch('/api/b')])"),
  "Back-to-back awaits serialise independent requests; use Promise.all when the second does not depend on the first.", sev="minor", cat="performance",
  mode="ai-confirm", ai="Is the second request independent of the first one's result?")
N("USEFETCH-HEADERS-001", "$fetch in server-rendered code does not forward cookies/headers", DF,
  "to proxy client headers and cookies",
  r'''((call_expression function: (identifier) @f arguments: (arguments . (_) . (_) @o)) @match (#eq? @f "$fetch") (#match? @o "useRequestHeaders"))''',
  scr("const { data } = await useAsyncData(() => $fetch('/api/me', { headers: useRequestHeaders(['cookie']) }))"),
  scr("const { data } = await useFetch('/api/me')"), "Prefer useFetch or useRequestFetch, which proxy request headers/cookies safely on the server.", sev="info", kind="best-practice")
N("STATE-SERIALIZABLE-001", "useState value that cannot be serialized", "getting-started/state-management",
  "it is important that it does not contain anything that cannot be serialized, such as classes, functions or symbols",
  r'''((call_expression function: (identifier) @f arguments: (arguments (_) [(arrow_function body: [(new_expression) (arrow_function) (function_expression) (class)]) (arrow_function body: (parenthesized_expression [(new_expression)]))])) @match (#eq? @f "useState"))''',
  scr("const client = useState('client', () => new ApiClient())"), scr("const token = useState('token', () => '')"),
  "useState values travel in the SSR payload as JSON; classes/functions/symbols are lost or break hydration.", cat="state")
N("LAZY-COMPONENT-001", "Heavy, conditionally shown component not lazy-loaded", "directory-structure/app/components",
  "By using the Lazy prefix you can delay loading the component code until the right moment",
  r'''((element (start_tag (tag_name) @t (directive_attribute (directive_name) @d)) @match) (#match? @t "^[A-Z][A-Za-z]*(Modal|Dialog|Drawer|Chart|Editor|Map)$") (#not-match? @t "^Lazy") (#eq? @d "v-if"))
((element (self_closing_tag (tag_name) @t (directive_attribute (directive_name) @d)) @match) (#match? @t "^[A-Z][A-Za-z]*(Modal|Dialog|Drawer|Chart|Editor|Map)$") (#not-match? @t "^Lazy") (#eq? @d "v-if"))''',
  tpl('<SettingsModal v-if="open" />'), tpl('<LazySettingsModal v-if="open" />'),
  "Prefix rarely shown components with Lazy to split them out of the initial bundle.", sev="info", kind="best-practice", cat="performance",
  lang="vue", target="template", mode="ai-confirm", ai="Is this component large and not needed for the initial render?")
N("PLUGIN-PARALLEL-001", "Async plugin without parallel: true", "directory-structure/app/plugins",
  "You can define a plugin as parallel so Nuxt won't wait until the end of the plugin's execution before loading the next plugin.",
  r'''((call_expression function: (identifier) @f arguments: (arguments . (arrow_function "async") .)) @match (#eq? @f "defineNuxtPlugin"))''',
  "export default defineNuxtPlugin(async () => {\n  await loadAnalytics()\n})\n",
  "export default defineNuxtPlugin({\n  parallel: true,\n  async setup() {\n    await loadAnalytics()\n  },\n})\n",
  "Async plugins block the next plugin; use the object form with parallel: true when there are no dependencies.", sev="info", kind="best-practice", cat="performance",
  files=["plugins/**", "app/plugins/**"])

# ------------------------------------------------------------- hydration / SSR safety
HY = "guide/best-practices/hydration"
N("HYDRATION-RANDOM-001", "Random/time-dependent values rendered during SSR", HY, "Inconsistent Data Problem: Different data between server and client.",
  r'''((interpolation (raw_text) @r) @match (#match? @r "Math\\.random\\(|Date\\.now\\(|new Date\\(\\)"))''',
  tpl("<div>{{ Math.random() }}</div>"), tpl("<NuxtTime :datetime=\"createdAt\" />"),
  "Values that differ between server and client cause hydration mismatches; compute once (useState) or render client-only.",
  sev="minor", kind="anti-pattern", cat="hydration", lang="vue", target="template")
N("HYDRATION-BROWSER-API-001", "Browser-only API used at setup top level", HY, "localStorage doesn't exist on the server!",
  r'''((call_expression function: (member_expression object: (identifier) @o)) @match (#match? @o "^(localStorage|sessionStorage|window|document|navigator)$"))''',
  scr("const userTheme = localStorage.getItem('theme') || 'light'"), scr("const userTheme = useCookie('theme', { default: () => 'light' })"),
  "localStorage/window/document do not exist during SSR; use useCookie/useState, onMounted or import.meta.client.", sev="major", cat="hydration", lang="vue", target="script")
N("SETUP-TIMER-001", "Timer created at the root of <script setup>", "guide/concepts/nuxt-lifecycle",
  "You should avoid code that produces side effects that need cleanup in root scope of <script setup>.",
  r'''((program (expression_statement (call_expression function: (identifier) @f) @match)) (#match? @f "^(setInterval|setTimeout)$"))
((program (lexical_declaration (variable_declarator value: (call_expression function: (identifier) @f) @match))) (#match? @f "^(setInterval)$"))''',
  scr("setInterval(() => tick(), 1000)"), scr("onMounted(() => {\n  const id = setInterval(() => tick(), 1000)\n  onBeforeUnmount(() => clearInterval(id))\n})"),
  "Timers started during SSR are never cleaned up and leak memory on the server; start them in onMounted.", sev="major", cat="hydration", lang="vue", target="script")

# ------------------------------------------------------------- security
N("USEHEAD-UNTRUSTED-001", "useHead with untrusted data (use useHeadSafe)", "api/composables/use-head",
  "If the data comes from a user or other untrusted source, we recommend you check out useHeadSafe",
  r'''((call_expression function: (identifier) @f arguments: (arguments (object) @o)) @match (#eq? @f "useHead") (#match? @o "\\b(route|query|params|props|data)\\b"))''',
  scr("useHead({ title: route.query.q })"), scr("useHeadSafe({ title: route.query.q })"), "Head tags built from user input can inject script/links; useHeadSafe restricts values.",
  kind="security", cat="security", mode="ai-confirm", ai="Does any value come from user input (query, params, API data)?")
N("USEHEAD-INNERHTML-001", "Inline script/style innerHTML via useHead", "api/composables/use-head",
  "If the data comes from a user or other untrusted source, we recommend you check out useHeadSafe",
  r'''((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @k) @match))) (#match? @f "^(useHead|useServerHead)$") (#eq? @k "script") (#match? @match "innerHTML|textContent|children"))''',
  scr("useHead({ script: [{ innerHTML: userSnippet }] })"), scr("useHead({ script: [{ src: '/analytics.js', defer: true }] })"),
  "Inline head scripts are an XSS sink; never interpolate untrusted data.", kind="security", cat="security", sev="minor",
  mode="ai-confirm", ai="Does the inline script content include any untrusted/dynamic data?")
N("COOKIE-SENSITIVE-001", "Sensitive cookie set without httpOnly/secure", "api/composables/use-cookie", "be careful when setting this to true, as compliant clients will not allow client-side JavaScript",
  r'''((call_expression function: (identifier) @f arguments: (arguments . (string (string_fragment) @n) .)) @match (#eq? @f "useCookie") (#match? @n "(?i)(token|session|auth|jwt|secret)"))''',
  scr("const token = useCookie('auth_token')"), scr("const token = useCookie('auth_token', { secure: true, sameSite: 'strict' })"),
  "Auth/session cookies need explicit options: secure, sameSite, and httpOnly when set server-side.", kind="security", cat="security", sev="minor",
  mode="ai-confirm", ai="Is this cookie a credential readable by client JS where httpOnly would be appropriate?")
N("SERVER-UNVALIDATED-BODY-001", "Server route reads the request body without validation", "guide/going-further/server-imports", "readBody, readValidatedBody Read and parse the request body, optionally validated.",
  r'''((call_expression function: (identifier) @f) @match (#match? @f "^(readBody|getQuery|getRouterParams)$"))''',
  "export default defineEventHandler(async (event) => {\n  const body = await readBody(event)\n  return db.insert(body)\n})\n",
  "export default defineEventHandler(async (event) => {\n  const body = await readValidatedBody(event, schema.parse)\n  return db.insert(body)\n})\n",
  "Validate untrusted input with readValidatedBody/getValidatedQuery (Standard Schema) before using it.", kind="security", cat="security", sev="minor",
  files=SERVER, base=D5, mode="ai-confirm", ai="Is the body/query used without any validation?")
N("RTC-SECRET-CLIENT-001", "Private runtimeConfig accessed in client code", "guide/going-further/runtime-config", "The private keys which are only available within server-side",
  r'''((member_expression object: (call_expression function: (identifier) @f) property: (property_identifier) @p) @match (#eq? @f "useRuntimeConfig") (#not-match? @p "^(public|app)$"))''',
  scr("const key = useRuntimeConfig().apiSecret"), scr("const base = useRuntimeConfig().public.apiBase"),
  "Only runtimeConfig.public is available in the browser; private keys are undefined on the client (and must never be sent there).",
  kind="security", cat="security", sev="minor", lang="vue", target="script")

# ------------------------------------------------------------- Nuxt 2 -> 3 migration
CO = "migration/component-options"
for opt, path, q, msg in [
    ("layout", CO, "layout Read more in Docs > Migration > Pages and Layouts", "Use definePageMeta({ layout: '...' })."),
    ("middleware", CO, "middleware Read more in Docs > Migration > Plugins and Middleware", "Use definePageMeta({ middleware: [...] })."),
    ("transition", CO, "transition Read more in Docs > Getting Started > Transitions", "Use definePageMeta({ pageTransition: ... })."),
    ("scrollToTop", CO, "if you want to overwrite the default scroll behavior of vue-router", "Use definePageMeta({ scrollToTop }) or app/router.options.ts."),
    ("validate", CO, "The validate hook in Nuxt 3 only accepts a single argument, the route.", "Use definePageMeta({ validate: (route) => ... })."),
    ("watchQuery", CO, "Instead, you can directly use a watcher to trigger refetching data.", "Use watch(() => route.query, ...) or a key on <NuxtPage>."),
    ("loading", CO, "loading This feature is not yet supported in Nuxt 3.", "The per-page loading option is not supported; use <NuxtLoadingIndicator> / useLoadingIndicator for a global indicator."),
    ("key", CO, "you can now define a key within the definePageMeta compiler macro", "Use definePageMeta({ key }) to key pages."),
]:
    N(f"MIG-OPT-{opt.upper()}-001", f"Nuxt 2 '{opt}' component option", path, q,
      f'''((export_statement (object [(pair key: (property_identifier) @k) (method_definition name: (property_identifier) @k)] @match)) (#eq? @k "{opt}"))''',
      scr(f"export default {{ {opt}: {'() => ({})' if opt in ('head','validate','key') else repr('x') if opt in ('layout','middleware','transition') else 'true'} }}", False),
      scr("definePageMeta({ layout: 'custom' })" if opt != "head" else "useHead({ title: 'x' })"),
      f"Nuxt 3+ ignores the {opt} component option. {msg}", sev="major", kind="migration", cat="migration", lang="vue", target="script")
N("MIG-NUXT-COMPONENT-001", "<Nuxt> / <NuxtChild> were replaced by <NuxtPage> / <slot>", "migration/pages-and-layouts",
  "In Nuxt 3, these have been replaced with a single <NuxtPage> component.",
  r'''((self_closing_tag (tag_name) @t) @match (#match? @t "^(Nuxt|NuxtChild|nuxt|nuxt-child)$"))
((start_tag (tag_name) @t) @match (#match? @t "^(Nuxt|NuxtChild|nuxt|nuxt-child)$"))''',
  tpl("<div><Nuxt /></div>"), tpl("<div><slot /></div>"), "Layouts render <slot />, parent pages render <NuxtPage />.", sev="critical", kind="migration",
  cat="migration", lang="vue", target="template")
N("MIG-AXIOS-001", "@nuxtjs/axios / @nuxt/http are Nuxt 2 modules", "api/utils/dollarfetch",
  "is the preferred way to make HTTP calls in Nuxt instead of @nuxt/http and @nuxtjs/axios that are made for Nuxt 2.",
  None, '{ "dependencies": { "nuxt": "^4.1.0", "@nuxtjs/axios": "^5.13.6" } }', '{ "dependencies": { "nuxt": "^4.1.0" } }',
  "Replace @nuxtjs/axios/@nuxt/http with $fetch/useFetch.", sev="major", kind="migration", cat="migration", lang="manifest", engine="manifest",
  manifest={"check": "has_dependency", "value": "@nuxtjs/axios"})
N("MIG-HTTP-001", "@nuxt/http is a Nuxt 2 module", "api/utils/dollarfetch",
  "is the preferred way to make HTTP calls in Nuxt instead of @nuxt/http and @nuxtjs/axios that are made for Nuxt 2.",
  None, '{ "dependencies": { "nuxt": "^4.1.0", "@nuxt/http": "^0.6.4" } }', '{ "dependencies": { "nuxt": "^4.1.0" } }',
  "Replace @nuxt/http with $fetch/useFetch.", sev="major", kind="migration", cat="migration", lang="manifest", engine="manifest",
  manifest={"check": "has_dependency", "value": "@nuxt/http"})
N("MIG-THIS-AXIOS-001", "this.$axios / context.$axios usage", "api/utils/dollarfetch", "is the preferred way to make HTTP calls in Nuxt instead of @nuxt/http and @nuxtjs/axios",
  r'''((member_expression property: (property_identifier) @p) @match (#match? @p "^\\$(axios|http)$"))''',
  scr("export default { methods: { load() { return this.$axios.$get('/api') } } }", False), scr("const load = () => $fetch('/api')"),
  "Use $fetch / useFetch in Nuxt 3+.", sev="major", kind="migration", cat="migration")
N("MIG-VUEX-001", "Vuex store integration is not provided by Nuxt 3+", "migration/configuration", "Nuxt no longer provides a Vuex integration.",
  r'''((member_expression property: (property_identifier) @p) @match (#eq? @p "$store"))''',
  scr("export default { computed: { user() { return this.$store.state.user } } }", False), scr("const user = useUserStore()"),
  "Migrate the store to Pinia (@pinia/nuxt) or wire Vuex 4 manually.", sev="major", kind="migration", cat="migration")
N("MIG-BUILDMODULES-001", "buildModules is deprecated (use modules)", "migration/configuration",
  "Move all your buildModules into modules.", cfgkey("^buildModules$"),
  "export default defineNuxtConfig({ buildModules: ['@nuxtjs/tailwindcss'] })\n", "export default defineNuxtConfig({ modules: ['@nuxtjs/tailwindcss'] })\n",
  "Move buildModules entries into modules.", sev="major", kind="deprecation", cat="configuration", files=CFG)
N("MIG-CONFIG-HEAD-001", "Top-level head in nuxt.config (use app.head)", "migration/meta", "rename head to meta", cfgkey("^head$"),
  "export default defineNuxtConfig({ head: { title: 'App' } })\n", "export default defineNuxtConfig({ app: { head: { title: 'App' } } })\n",
  "Nuxt 3+ reads app.head (or useHead in app.vue).", sev="major", kind="migration", cat="configuration", files=CFG)
N("MIG-HID-001", "hid/vmid keys in head meta", "migration/meta", "Note that objects no longer have a hid key for deduplication.",
  r'''((pair key: (property_identifier) @k) @match (#match? @k "^(hid|vmid)$"))''',
  scr("useHead({ meta: [{ hid: 'description', name: 'description', content: 'x' }] })"), scr("useHead({ meta: [{ name: 'description', content: 'x' }] })"),
  "Unhead deduplicates by name/property; hid/vmid are ignored (Unhead v2 removed them).", sev="minor", kind="migration", cat="seo")
N("MIG-DOLLAR-NUXT-001", "Global $nuxt / window.$nuxt", "migration/plugins-and-middleware", "take only one argument (nuxtApp)",
  r'''((member_expression object: (identifier) @w property: (property_identifier) @p) @match (#eq? @w "window") (#eq? @p "$nuxt"))
((member_expression object: (this) property: (property_identifier) @p) @match (#eq? @p "$nuxt"))''',
  scr("window.$nuxt.$router.push('/')"), scr("const nuxtApp = useNuxtApp()"), "Use useNuxtApp(); the $nuxt global is a Nuxt 2 API.", sev="major", kind="migration", cat="migration")
N("MIG-ROUTER-LINK-001", "<router-link>/<nuxt-link> lowercase in Nuxt 3+", "migration/pages-and-layouts", "most of the syntax and functionality are the same for the global NuxtLink component",
  r'''((start_tag (tag_name) @t) @match (#match? @t "^(router-link|RouterLink)$"))''',
  tpl('<router-link to="/about">About</router-link>'), tpl('<NuxtLink to="/about">About</NuxtLink>'),
  "Use <NuxtLink> for prefetching and external-link handling.", sev="info", kind="best-practice", cat="routing", lang="vue", target="template")

# ------------------------------------------------------------- Nuxt 4
UP4 = "getting-started/upgrade"
N("NUXT4-WINDOW-NUXT-001", "window.__NUXT__ is removed after hydration (Nuxt 4)", UP4, "We are removing the global window.__NUXT__ object after the app finishes hydration.",
  r'''((member_expression object: (identifier) @w property: (property_identifier) @p) @match (#eq? @w "window") (#eq? @p "__NUXT__"))''',
  "const state = window.__NUXT__.state\n", "const state = useNuxtApp().payload.state\n", "Use useNuxtApp().payload instead of window.__NUXT__.",
  sev="critical", kind="removal", cat="migration", applies=N4)
N("NUXT4-DEDUPE-BOOL-001", "refresh({ dedupe: true|false }) boolean values were removed (Nuxt 4)", UP4, "Removal of deprecated boolean values for dedupe option",
  r'''((call_expression function: [(identifier) @f (member_expression property: (property_identifier) @f)] arguments: (arguments (object (pair key: (property_identifier) @k value: [(true) (false)])))) @match (#match? @f "^(refresh|refreshNuxtData|execute)$") (#eq? @k "dedupe"))''',
  scr("await refresh({ dedupe: true })"), scr("await refresh({ dedupe: 'cancel' })"), "Use dedupe: 'cancel' | 'defer'.", sev="critical", kind="removal", cat="migration", applies=N4)
N("NUXT4-GENERATE-CONFIG-001", "Top-level generate config was removed (Nuxt 4)", UP4, "The top-level generate configuration option is no longer available in Nuxt 4.",
  cfgkey("^generate$"), "export default defineNuxtConfig({ generate: { routes: ['/a'] } })\n", "export default defineNuxtConfig({ nitro: { prerender: { routes: ['/a'] } } })\n",
  "Use nitro.prerender (routes/ignore).", sev="critical", kind="removal", cat="configuration", applies=N4, files=CFG)
N("NUXT4-EXPERIMENTAL-REMOVED-001", "Experimental options removed in Nuxt 4", UP4, "respectNoSSRHeader is implementable in user-land with server middleware",
  cfgnested("experimental", "^(treeshakeClientOnly|configSchema|polyfillVueUseHead|respectNoSSRHeader)$"),
  "export default defineNuxtConfig({ experimental: { treeshakeClientOnly: true } })\n", "export default defineNuxtConfig({ experimental: {} })\n",
  "These experimental flags no longer exist in Nuxt 4 (behaviour is now default or removed).", sev="major", kind="removal", cat="configuration", applies=N4, files=CFG)
N("NUXT4-DATA-NULL-001", "useAsyncData/useFetch data compared with null (default is undefined in Nuxt 4)", UP4, "Default data and error values in useAsyncData and useFetch",
  r'''((binary_expression left: (member_expression object: (identifier) @d property: (property_identifier) @v) operator: ["===" "!=="] right: (null)) @match (#match? @d "^(data|error)$") (#eq? @v "value"))''',
  scr("if (data.value === null) showEmpty()"), scr("if (!data.value) showEmpty()"),
  "data/error default to undefined in Nuxt 4, so === null checks no longer match.", sev="major", kind="migration", cat="migration", applies=N4)
N("NUXT4-PENDING-001", "pending from useAsyncData/useFetch no longer true before fetching starts (Nuxt 4)", UP4, "Alignment of pending value in useAsyncData and useFetch",
  r'''((variable_declarator name: (object_pattern) @pat value: (await_expression (call_expression function: (identifier) @f))) @match (#match? @f "^(useFetch|useAsyncData|useLazyFetch|useLazyAsyncData)$") (#match? @pat "\\bpending\\b"))''',
  scr("const { data, pending } = await useLazyFetch('/api/x')"), scr("const { data, status } = await useLazyFetch('/api/x')"),
  "Use status ('idle' | 'pending' | 'success' | 'error'); with immediate: false, pending stays false until execution.", sev="minor", kind="migration", cat="migration", applies=N4,
  mode="ai-confirm", ai="Does the code rely on pending being true before the request starts (e.g. immediate: false or lazy)?")
N("NUXT4-UNHEAD-CHILDREN-001", "Unhead v2 removed children/body props", UP4, "Removed props: vmid, hid, children, body.",
  r'''((pair key: (property_identifier) @k) @match (#eq? @k "children"))''',
  scr("useHead({ script: [{ children: 'console.log(1)' }] })"), scr("useHead({ script: [{ innerHTML: 'console.log(1)' }] })"),
  "Use innerHTML (and tagPosition: 'bodyClose' instead of body: true).", sev="major", kind="removal", cat="seo", applies=N4,
  filters=["file.has_text:useHead"])

# ------------------------------------------------------------- Nuxt 5 (applies once the project is on Nuxt >= 5)
UP5 = "getting-started/upgrade"
N("NUXT5-H3-IMPORT-001", "Server utilities should be imported from nuxt/server", UP5, "Server Imports Move to nuxt/server",
  r'''((import_statement source: (string (string_fragment) @s)) @match (#eq? @s "h3"))''',
  "import { defineEventHandler } from 'h3'\nexport default defineEventHandler(() => 'ok')\n", "import { defineEventHandler } from 'nuxt/server'\nexport default defineEventHandler(() => 'ok')\n",
  "Nuxt 5 runs on h3 v2; import server helpers from nuxt/server.", sev="minor", kind="migration", cat="migration", applies=N5, base=D5, docv="Nuxt 5 docs (5.x)", files=SERVER)
N("NUXT5-IMPORTS-SERVER-001", "#imports in server code is deprecated (use #imports/server)", UP5, "Server code should import from #imports/server",
  r'''((import_statement source: (string (string_fragment) @s)) @match (#eq? @s "#imports"))''',
  "import { defineEventHandler } from '#imports'\n", "import { defineEventHandler } from '#imports/server'\n",
  "#imports is untyped in Nuxt 5 server code.", sev="minor", kind="deprecation", cat="migration", applies=N5, base=D5, files=SERVER)
N("NUXT5-CREATEERROR-STATUS-001", "createError statusCode/statusMessage replaced by status/statusText", UP5, "status / statusText replace statusCode / statusMessage",
  r'''((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @k)))) @match (#eq? @f "createError") (#match? @k "^(statusCode|statusMessage)$"))''',
  scr("throw createError({ statusCode: 404, statusMessage: 'Not Found' })"), scr("throw createError({ status: 404, statusText: 'Not Found' })"),
  "Use status/statusText (Nuxt 5 / h3 v2).", sev="major", kind="migration", cat="error-handling", applies=N5, base=D5)
N("NUXT5-RTC-EVENT-001", "useRuntimeConfig(event) no longer accepts event", UP5, "useRuntimeConfig() No Longer Accepts event",
  r'''((call_expression function: (identifier) @f arguments: (arguments . (identifier))) @match (#eq? @f "useRuntimeConfig"))''',
  "export default defineEventHandler((event) => useRuntimeConfig(event).apiSecret)\n", "export default defineEventHandler(() => useRuntimeConfig().apiSecret)\n",
  "Call useRuntimeConfig() without the event in Nuxt 5.", sev="minor", kind="migration", cat="migration", applies=N5, base=D5, files=SERVER)
N("NUXT5-ROUTERULE-STATUSCODE-001", "Route rules statusCode renamed to status", UP5, "Route Rules: statusCode Renamed to status",
  r'''((pair key: (property_identifier) @r value: (object (pair value: (object (pair value: (object (pair key: (property_identifier) @k) @match)))))) (#eq? @r "routeRules") (#eq? @k "statusCode"))''',
  "export default defineNuxtConfig({ routeRules: { '/old': { redirect: { to: '/new', statusCode: 301 } } } })\n",
  "export default defineNuxtConfig({ routeRules: { '/old': { redirect: { to: '/new', status: 301 } } } })\n",
  "Rename statusCode to status in route rules.", sev="major", kind="migration", cat="configuration", applies=N5, base=D5, files=CFG)
N("NUXT5-SERVERHEAD-IMPORT-001", "useServerHead/useServerSeoMeta are no longer auto-imported", UP5,
  "useServerHead , useServerHeadSafe and useServerSeoMeta are removed from Nuxt's auto-imports.",
  call("useServerHead|useServerHeadSafe|useServerSeoMeta"), scr("useServerHead({ meta: [{ name: 'generator', content: 'Nuxt' }] })"),
  scr("useHead({ meta: [{ name: 'generator', content: 'Nuxt' }] })"), "Import them explicitly from #app (or use useHead/useSeoMeta).",
  sev="major", kind="migration", cat="seo", applies=N5, base=D5, filters=["file.lacks_text:from '#app'"])
N("NUXT5-EXTERNALVUE-001", "experimental.externalVue was removed", UP5, "The experimental.externalVue option has been removed.",
  cfgnested("experimental", "^externalVue$"), "export default defineNuxtConfig({ experimental: { externalVue: false } })\n", "export default defineNuxtConfig({ experimental: {} })\n",
  "Remove experimental.externalVue (Nitro v3 bundles everything).", sev="minor", kind="removal", cat="configuration", applies=N5, base=D5, files=CFG)
N("NUXT5-PARSEERRORDATA-001", "experimental.parseErrorData is no longer configurable", UP5, "experimental.parseErrorData Is No Longer Configurable",
  cfgnested("experimental", "^parseErrorData$"), "export default defineNuxtConfig({ experimental: { parseErrorData: false } })\n", "export default defineNuxtConfig({ experimental: {} })\n",
  "error.data is always parsed in Nuxt 5; remove the option and any JSON.parse(error.data).", sev="minor", kind="removal", cat="configuration", applies=N5, base=D5, files=CFG)
# ------------------------------------------------------------- Nuxt 4 upgrade guide (more)
N("NUXT4-ROUTE-META-NAME-001", "route.meta.name/path are no longer duplicated on route metadata (Nuxt 4)", UP4, "Now, they are only accessible on the route object.",
  r'''((member_expression object: (member_expression property: (property_identifier) @m) property: (property_identifier) @p) @match (#eq? @m "meta") (#match? @p "^(name|path|alias|redirect)$"))''',
  "const route = useRoute()\nconsole.log(route.meta.name)\n", "const route = useRoute()\nconsole.log(route.name)\n",
  "Read name/path from the route itself (route.name), not route.meta.", sev="major", kind="migration", cat="routing", applies=N4)
N("NUXT4-UNHEAD-IMPORT-001", "Import head composables from #imports, not @unhead/vue", UP4,
  "While not required it's recommended to update any imports from @unhead/vue to #imports or nuxt/app.",
  r'''((import_statement source: (string (string_fragment) @s)) @match (#eq? @s "@unhead/vue"))''',
  "import { useHead } from '@unhead/vue'\n", "import { useHead } from '#imports'\n", "Use the Nuxt re-exports (#imports / nuxt/app).", sev="info", kind="best-practice", cat="seo", applies=N4)
N("NUXT4-UNHEAD-LEGACY-001", "unhead.legacy revert flag", UP4, "you may revert to the v1 behavior by enabling the head.legacy config",
  cfgnested("unhead", "^legacy$"), "export default defineNuxtConfig({ unhead: { legacy: true } })\n", "export default defineNuxtConfig({})\n",
  "unhead.legacy is a temporary escape hatch (ignored with compatibilityVersion 5); migrate off removed Unhead v1 props.", sev="minor", kind="migration", cat="configuration", applies=N4, files=CFG)
N("NUXT4-ERROR-DATA-PARSE-001", "Manual JSON.parse(error.data) (error.data is parsed in Nuxt 4)", UP4, "Update your custom error.vue to remove any additional parsing of error.data",
  r'''((call_expression function: (member_expression object: (identifier) @j property: (property_identifier) @p) arguments: (arguments (member_expression property: (property_identifier) @d))) @match (#eq? @j "JSON") (#eq? @p "parse") (#eq? @d "data"))''',
  "const data = JSON.parse(props.error.data)\n", "const data = props.error.data\n", "error.data is already an object; parsing it again throws.", sev="major", kind="migration", cat="error-handling", applies=N4)
N("NUXT4-PAGES-EXTEND-META-001", "Page meta overridden in pages:extend (use pages:resolved)", UP4, "If you want to override page metadata, do that in pages:resolved rather than in pages:extend.",
  r'''((method_definition name: (string (string_fragment) @h) body: (statement_block) @b) @match (#eq? @h "pages:extend") (#match? @b "\\.meta\\b"))
((pair key: (string (string_fragment) @h) value: (_) @b) @match (#eq? @h "pages:extend") (#match? @b "\\.meta\\b"))''',
  "export default defineNuxtConfig({\n  hooks: {\n    'pages:extend'(pages) {\n      pages[0].meta = { layout: 'x' }\n    },\n  },\n})\n",
  "export default defineNuxtConfig({\n  hooks: {\n    'pages:resolved'(pages) {\n      pages[0].meta = { layout: 'x' }\n    },\n  },\n})\n",
  "Page meta is scanned after pages:extend in Nuxt 4; overrides there are lost.", sev="major", kind="migration", cat="configuration", applies=N4, files=CFG)
N("NUXT4-ASYNCDATA-KEY-001", "useAsyncData without a key whose data depends on route params", UP4, "you should provide a key that uniquely matches that data",
  r'''((call_expression function: (identifier) @f arguments: (arguments . [(arrow_function) (function_expression)] @h .)) @match (#eq? @f "useAsyncData") (#match? @h "route\\.(params|query)"))''',
  "const { data } = await useAsyncData(async () => $fetch(`/api/page/${route.params.slug}`))\n",
  "const { data } = await useAsyncData(() => `page-${route.params.slug}`, async () => $fetch(`/api/page/${route.params.slug}`))\n",
  "Shared prerender data is keyed: an auto key on a dynamic page serves one page's data to all of them.", sev="major", cat="data-fetching", applies=N4)
N("NUXT4-IMMEDIATE-FALSE-001", "immediate: false but execute/refresh never called", UP4, "If you have set immediate: false, then you must call refresh or execute or data will never be fetched",
  r'''((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @k value: (false))))) @match (#match? @f "^(useFetch|useAsyncData|useLazyFetch|useLazyAsyncData)$") (#eq? @k "immediate"))''',
  "const { data } = await useFetch('/api/x', { immediate: false })\n", "const { data, execute } = await useFetch('/api/x', { immediate: false })\nonMounted(() => execute())\n",
  "Nothing triggers the first request; key changes no longer start it in Nuxt 4.", sev="major", cat="data-fetching", applies=N4,
  filters=["file.lacks_text:execute(", "file.lacks_text:refresh("])
VAL = {"pendingWhenIdle": "true", "alwaysRunFetchOnKeyChange": "true", "scanPageMeta": "true", "spaLoadingTemplateLocation": "'within'",
       "normalizeComponentNames": "false", "sharedPrerenderData": "false"}
for flag, q, msg in [
    ("pendingWhenIdle", "you can temporarily revert to the previous behavior with", "Temporary revert of the Nuxt 4 pending alignment; migrate to status."),
    ("alwaysRunFetchOnKeyChange", "To opt out of this behavior", "Opt-out of Nuxt 4 key-change semantics; trigger the first fetch explicitly instead."),
    ("normalizeComponentNames", "Alternatively, for now, you can disable this behaviour with", "Temporary opt-out; update <KeepAlive>/findComponent to Nuxt component names."),
    ("spaLoadingTemplateLocation", "Alternatively, you can revert to the previous behaviour with", "Temporary revert; update selectors (app.spaLoaderTag/spaLoaderAttrs)."),
    ("scanPageMeta", "Alternatively, you can revert to the previous behaviour with", "Temporary revert; move meta overrides to pages:resolved."),
    ("sharedPrerenderData", "Alternatively, you can disable this feature with", "Disabling shared prerender data costs build time; give useAsyncData unique keys instead."),
]:
    N(f"NUXT4-REVERT-{flag.upper()}-001", f"experimental.{flag} reverts a Nuxt 4 default", UP4, q, cfgnested("experimental", f"^{flag}$"),
      "export default defineNuxtConfig({ experimental: { %s: %s } })\n" % (flag, VAL[flag]),
      "export default defineNuxtConfig({ experimental: {} })\n", msg, sev="info", kind="migration", cat="configuration", applies=N4, files=CFG)
N("NUXT4-NOUNCHECKED-OVERRIDE-001", "noUncheckedIndexedAccess turned off (Nuxt 4 default is true)", UP4, "Run a typecheck on your app and fix any new errors (recommended).",
  r'''((pair key: (property_identifier) @k value: (false)) @match (#eq? @k "noUncheckedIndexedAccess"))''',
  "export default defineNuxtConfig({ typescript: { tsConfig: { compilerOptions: { noUncheckedIndexedAccess: false } } } })\n", "export default defineNuxtConfig({})\n",
  "Prefer fixing the new type errors over disabling the stricter default.", sev="info", kind="best-practice", cat="typescript", applies=N4, files=CFG)
N("NUXT4-DEVBUNDLER-001", "vite.devBundler is no longer configurable (Nuxt 4)", UP4, "vite.devBundler is no longer configurable",
  cfgnested("vite", "^devBundler$"), "export default defineNuxtConfig({ vite: { devBundler: 'legacy' } })\n", "export default defineNuxtConfig({ vite: {} })\n",
  "Remove vite.devBundler (vite-node is always used).", sev="minor", kind="removal", cat="configuration", applies=N4, files=CFG)
N("NUXT4-EJS-TEMPLATE-001", "addTemplate with an .ejs src (lodash/template compilation removed)", UP4, "Previously, Nuxt used lodash/template to compile templates",
  r'''((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @k value: (_) @v)))) @match (#eq? @f "addTemplate") (#eq? @k "src") (#match? @v "\\.ejs"))''',
  "addTemplate({ fileName: 'plugin.js', src: resolver.resolve('./runtime/plugin.ejs') })\n",
  "addTemplate({ fileName: 'plugin.js', getContents: ({ options }) => render(options) })\n",
  "Nuxt 4 no longer compiles .ejs templates; use getContents().", sev="critical", kind="removal", cat="modules", applies=N4)
N("NUXT4-TEMPLATE-UTILS-001", "Template utilities serialize/importName/importSources removed", UP4, "which could be used for code-generation within these templates, which are now being removed",
  r'''((member_expression object: (identifier) @o property: (property_identifier) @p) @match (#eq? @o "utils") (#match? @p "^(serialize|importName|importSources)$"))''',
  "const code = utils.serialize(options)\n", "const code = JSON.stringify(options, null, 2)\n", "Use knitwork (genImport, genSafeVariableName...) instead.", sev="major", kind="removal", cat="modules", applies=N4)
N("NUXT4-BUILDER-WATCH-001", "builder:watch hook path is absolute in Nuxt 4", UP4, "hook now emits a path which is absolute rather than relative to your project srcDir",
  r'''((call_expression function: (member_expression property: (property_identifier) @h) arguments: (arguments . (string (string_fragment) @e))) @match (#eq? @h "hook") (#eq? @e "builder:watch"))''',
  "nuxt.hook('builder:watch', (event, path) => {\n  if (path.startsWith('content/')) reload()\n})\n",
  "nuxt.hook('builder:watch', (event, path) => {\n  path = relative(nuxt.options.srcDir, resolve(nuxt.options.srcDir, path))\n})\n",
  "Normalise the path with relative(srcDir, resolve(srcDir, path)) to work on Nuxt 3 and 4.", sev="minor", kind="migration", cat="modules", applies=N4,
  filters=["node.lacks_descendant_text:relative("])

# ------------------------------------------------------------- nuxt/server (Nuxt 4.6+) and Nuxt 5 / h3 v2
NS = UP4 + "#differences-from-h3-v1"
N46 = {"nuxt": ">=4.6"}
N("SERVER-E8012-001", "nuxt/server helpers used with h3's defineEventHandler (NUXT_E8012)", UP4,
  "Import defineEventHandler from nuxt/server in the same file as the helpers.",
  r'''((import_statement source: (string (string_fragment) @s)) @match (#eq? @s "nuxt/server") (#not-match? @match "defineEventHandler"))''',
  "import { readValidatedBody } from 'nuxt/server'\nexport default defineEventHandler(async (event) => readValidatedBody(event, schema))\n",
  "import { defineEventHandler, readValidatedBody } from 'nuxt/server'\nexport default defineEventHandler(async (event) => readValidatedBody(event, schema))\n",
  "The auto-imported defineEventHandler is h3 v1's; nuxt/server helpers then fail with a 500 [NUXT_E8012].", sev="critical", cat="server", applies=N46, files=SERVER,
  filters=["file.has_text:defineEventHandler"])
for id, title, query, bad, good, q, msg, sev in [
    ("SENDREDIRECT", "sendRedirect result not returned",
     r'''(expression_statement [(call_expression function: (identifier) @f) (await_expression (call_expression function: (identifier) @f))] @match (#eq? @f "sendRedirect"))''',
     "export default defineEventHandler((event) => {\n  sendRedirect(event, '/login')\n})\n", "export default defineEventHandler((event) => {\n  return sendRedirect(event, '/login')\n})\n",
     "returns the response body: return sendRedirect(event, '/login')", "With h3 v2 / nuxt/server sendRedirect only builds the response; return it.", "critical"),
    ("ISERROR", "isError(error) replaced by isNuxtError(error)", call("isError"), "if (isError(e)) throw e\n", "if (isNuxtError(e)) throw e\n",
     "isNuxtError(error)", "Use isNuxtError.", "major"),
    ("EVENT-NODE", "event.node is not part of nuxt/server", r'''((member_expression object: (identifier) @e property: (property_identifier) @p) @match (#eq? @e "event") (#eq? @p "node"))''',
     "const ua = event.node.req.headers['user-agent']\n", "const ua = event.req.headers.get('user-agent')\n", "Not part of nuxt/server. Use event.req and event.res.",
     "Use the Web Request/Response on event.req / event.res.", "major"),
    ("EVENT-PATH", "event.path replaced by getRequestURL(event).pathname", r'''((member_expression object: (identifier) @e property: (property_identifier) @p) @match (#eq? @e "event") (#eq? @p "path"))''',
     "const p = event.path\n", "const p = event.url.pathname\n", "getRequestURL(event).pathname, or event.url.pathname", "Use event.url.pathname.", "major"),
    ("GETMETHOD", "getMethod/isMethod/assertMethod are not in nuxt/server", call("getMethod|isMethod|assertMethod"),
     "if (isMethod(event, 'POST')) save()\n", "if (event.req.method === 'POST') save()\n", "Compare event.req.method.", "Compare event.req.method directly.", "major"),
    ("MULTIPART", "readMultipartFormData replaced by event.req.formData()", call("readMultipartFormData"),
     "const parts = await readMultipartFormData(event)\n", "const form = await event.req.formData()\n", "await event.req.formData()", "Use event.req.formData().", "major"),
    ("RAWBODY", "readRawBody/getRequestWebStream replaced by event.req body methods", call("readRawBody|getRequestWebStream"),
     "const raw = await readRawBody(event)\n", "const raw = await event.req.text()\n", "await event.req.arrayBuffer()", "Use event.req.arrayBuffer()/text()/body.", "major"),
    ("RESPONSE-HEADER", "get/set/append/removeResponseHeader replaced by event.res.headers", call("getResponseHeader|setResponseHeader|appendResponseHeader|removeResponseHeader"),
     "setResponseHeader(event, 'x-id', id)\n", "event.res.headers.set('x-id', id)\n", "event.res.headers.get()", "Use event.res.headers.get/set/append/delete.", "major"),
    ("SANITIZE-STATUS", "sanitizeStatusCode is not provided", call("sanitizeStatusCode"), "const code = sanitizeStatusCode(input)\n", "const code = Number(input)\n",
     "sanitizeStatusCode", "sanitizeStatusCode no longer exists in nuxt/server / Nuxt 5.", "minor"),
    ("GLOBAL-FETCH", "Global $fetch in server routes (use serverFetch / fetch)",
     r'''((call_expression function: (identifier) @f) @match (#eq? @f "$fetch"))''',
     "export default defineEventHandler(async () => $fetch('/api/other'))\n", "export default defineEventHandler(async (event) => serverFetch(event, '/api/other'))\n",
     "Call a route of the app with serverFetch(event, path), which returns a Response.",
     "Global $fetch is not part of nuxt/server; use serverFetch for internal routes or fetch (check response.ok).", "major"),
    ("ROUTER-PARAM-DECODE", "getRouterParam(s) no longer decode values", call("getRouterParam|getRouterParams"),
     "const slug = getRouterParam(event, 'slug')\n", "const slug = getRouterParam(event, 'slug', { decode: true })\n",
     "Pass { decode: true } to decode them.", "Values are returned as they appear in the URL; pass { decode: true } where decoded values are expected.", "minor"),
    ("HANDLECORS", "handleCors return value changed (returns preflight Response)",
     r'''((if_statement condition: (parenthesized_expression (call_expression function: (identifier) @f))) @match (#eq? @f "handleCors"))''',
     "export default defineEventHandler((event) => {\n  if (handleCors(event, opts)) {\n    return\n  }\n})\n",
     "export default defineEventHandler((event) => {\n  const preflight = handleCors(event, opts)\n  if (preflight) return preflight\n})\n",
     "returns the preflight Response to return from the handler, or false", "Return the preflight Response handleCors gives you.", "major"),
]:
    N(f"NUXT5-{id}-001", title, UP4, q, query, bad, good, msg, sev=sev, kind="migration", cat="server", applies=N5, files=SERVER,
      docv="Nuxt 4 docs (4.x) - Moving to nuxt/server")
N("NAVIGATETO-EXTERNAL-001", "navigateTo() to an external URL without external: true", "api/utils/navigate-to",
  "external URLs throw an error",
  r'''((call_expression function: (identifier) @f arguments: (arguments . (string (string_fragment) @u) .)) @match (#eq? @f "navigateTo") (#match? @u "^(https?:)?//"))''',
  "await navigateTo('https://nuxt.com')\n", "await navigateTo('https://nuxt.com', { external: true })\n",
  "Without external: true navigating to an external URL throws.", sev="major", kind="anti-pattern", cat="routing")
for _r in R:
    if _r["id"] == "NUXT-NUXT5-ROUTER-PARAM-DECODE-001":
        _r["detection"]["filters"] = ["node.lacks_descendant_text:decode"]

# ------------------------------------------------------------- security advisories (nuxt.com/blog/v4-5-security; gated to the vulnerable ranges)
SECBLOG = "https://nuxt.com/blog/v4-5-security"
VULN = {"nuxt": ">=3.0 <3.21.10 || >=4.0 <4.5.1"}


def SEC(id, title, quote, query, bad, good, msg, applies, **kw):
    R.append(rule("NUXT-" + id, title, language="javascript", framework="nuxt", kind="security", category="security",
                  severity=kw.pop("sev", "critical"), applies=applies, message=msg, url=SECBLOG, doc="Nuxt blog - Security Patch Releases (4.5.1 / 3.21.10)",
                  doc_version="Nuxt 4.5.1 / 3.21.10", quote=quote, bad=bad, good=good, query=query, files=CFG, **kw))


SEC("SEC-RUNTIME-COMPILER-ISLANDS-001", "vue.runtimeCompiler enabled on a Nuxt release with the island-props RCE",
    "You're affected only if you have enabled vue.runtimeCompiler (which is off by default)",
    r'''((call_expression function: (identifier) @d arguments: (arguments (object (pair key: (property_identifier) @p value: (object (pair key: (property_identifier) @k value: (true)) @match))))) (#eq? @d "defineNuxtConfig") (#eq? @p "vue") (#eq? @k "runtimeCompiler"))''',
    "export default defineNuxtConfig({ vue: { runtimeCompiler: true } })\n", "export default defineNuxtConfig({ vue: { runtimeCompiler: false } })\n",
    "With the runtime compiler on, server island props that reach dynamic component resolution allow remote code execution on this Nuxt version (GHSA-9473-5f9j-94wq). Upgrade to 4.5.1 / 3.21.10 and turn the runtime compiler off unless you need it.",
    VULN, cwe=["CWE-94"])
SEC("SEC-ROUTERULE-UPPERCASE-AUTH-001", "routeRules authorization key with uppercase characters (case bypass)",
    "any rule key contains an uppercase character",
    r'''((pair key: (property_identifier) @r value: (object (pair key: (string (string_fragment) @k) value: (object) @v) @match)) (#eq? @r "routeRules") (#match? @k "[A-Z]") (#match? @v "appMiddleware"))''',
    "export default defineNuxtConfig({ routeRules: { '/Admin/**': { appMiddleware: ['auth'] } } })\n",
    "export default defineNuxtConfig({ routeRules: { '/admin/**': { appMiddleware: ['auth'] } } })\n",
    "On this Nuxt version route rules match case-sensitively while routing does not, so /admin bypasses the middleware gate on /Admin (GHSA-hxvh-4h3w-prp9). Upgrade to 4.5.1 / 3.21.10 and use lowercase keys.",
    VULN, cwe=["CWE-863"])
SEC("SEC-CACHED-PAYLOAD-001", "cache/swr/isr route rule on Nuxt 4.4.x (cross-user payload disclosure)",
    "on authenticated pages that render user-specific data",
    r'''((pair key: (property_identifier) @r value: (object (pair value: (object (pair key: (property_identifier) @k) @match)))) (#eq? @r "routeRules") (#match? @k "^(swr|isr|cache)$"))''',
    "export default defineNuxtConfig({ routeRules: { '/account/**': { swr: 60 } } })\n",
    "export default defineNuxtConfig({ routeRules: { '/blog/**': { prerender: true } } })\n",
    "On Nuxt 4.4.0-4.5.0 a cached _payload.json can be served to another user (GHSA-wm8w-6qjm-cv43). Upgrade to 4.5.1 and purge CDN caches; keep caching off pages with per-user data.",
    {"nuxt": ">=4.4.0 <4.5.1"}, sev="major", mode="ai-confirm", cwe=["CWE-524"],
    ai="Does this cached route render authenticated, user-specific data?")

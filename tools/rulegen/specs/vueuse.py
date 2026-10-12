"""VueUse pack (framework layer on the Vue + JS/TS packs). Language `javascript` (runs on JS/TS and .vue <script>).
Version dimension `vueuse` (@vueuse/core). Sources: vueuse.org guide + function docs, VueUse GitHub release notes / PRs for
breaking changes, VueUse source @deprecated annotations, vuejs.org for the Vue-native replacements."""
from specs._common import Pack

VU = "https://vueuse.org/"
REL = "https://github.com/vueuse/vueuse/releases/tag/"
SRC = "https://raw.githubusercontent.com/vueuse/vueuse/main/packages/"
BP = VU + "guide/best-practice"
P = Pack("VUEUSE", "javascript", "VueUse 15", {"vueuse": "*"}, framework="vueuse")
PKGS = "@vueuse/(core|shared|math|components|nuxt)"


def imp(names, src=PKGS):
    return (f'((import_statement (import_clause (named_imports (import_specifier name: (identifier) @n))) source: (string (string_fragment) @s)) @match '
            f'(#match? @s "^({src})$") (#match? @n "^({names})$"))')


def call_opt(fn, keys):
    return (f'((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @k) @match))) '
            f'(#match? @f "^({fn})$") (#match? @k "^({keys})$"))')


# ======================================================================== deprecated alias exports (v14)
ALIASES = [("and|or|not", "logicAnd / logicOr / logicNot", "math/logicAnd/index.ts", "@deprecated use `logicAnd` instead", "@vueuse/math"),
           ("controlledRef", "refWithControl", "shared/refWithControl/index.ts", "@deprecated use `refWithControl` instead", PKGS),
           ("eagerComputed", "computedEager", "shared/computedEager/index.ts", "@deprecated use `computedEager` instead", PKGS),
           ("debouncedWatch", "watchDebounced", "shared/watchDebounced/index.ts", "@deprecated use `watchDebounced` instead", PKGS),
           ("throttledWatch", "watchThrottled", "shared/watchThrottled/index.ts", "@deprecated use `watchThrottled` instead", PKGS),
           ("createReactiveFn", "reactify", "shared/reactify/index.ts", "@deprecated use `reactify` instead", PKGS),
           ("ignorableWatch", "watchIgnorable", "shared/watchIgnorable/index.ts", "@deprecated use `watchIgnorable` instead", PKGS),
           ("asyncComputed", "computedAsync", "core/computedAsync/index.ts", "@deprecated use `computedAsync` instead", PKGS),
           ("controlledComputed", "computedWithControl", "shared/computedWithControl/index.ts", "@deprecated use `computedWithControl` instead", PKGS),
           ("autoResetRef", "refAutoReset", "shared/refAutoReset/index.ts", "@deprecated use `refAutoReset` instead", PKGS),
           ("throttledRef|useThrottle", "refThrottled", "shared/refThrottled/index.ts", "@deprecated use `refThrottled` instead", PKGS),
           ("debouncedRef|useDebounce", "refDebounced", "shared/refDebounced/index.ts", "@deprecated use `refDebounced` instead", PKGS),
           ("VOnClickOutside", "vOnClickOutside", "core/onClickOutside/directive.ts", "@deprecated use `vOnClickOutside` instead", PKGS),
           ("VOnLongPress", "vOnLongPress", "core/onLongPress/directive.ts", "@deprecated use `vOnLongPress` instead", PKGS)]
for names, orig, path, needle, src in ALIASES:
    first = names.split("|")[0]
    o1 = orig.split(" / ")[0]
    rid = "ALIAS-" + o1.upper()
    P(rid, f"Deprecated alias {names.replace('|', '/')} (use {orig})", SRC + path, needle, imp(names, src),
      f"import {{ {first} }} from '{src if src.startswith('@vueuse/math') else '@vueuse/core'}'\n",
      f"import {{ {o1} }} from '{src if src.startswith('@vueuse/math') else '@vueuse/core'}'\n",
      f"Alias exports are deprecated since VueUse 14; import {orig}.", sev="minor", kind="deprecation", cat="compatibility",
      applies={"vueuse": ">=14.0"}, docv="VueUse 14", xref=[REL + "v14.0.0"])

# ======================================================================== removals / breaking changes
P("TEMPLATE-REF-REMOVED", "templateRef removed (v15)", REL + "v15.0.0", "Drop templateRef", imp("templateRef"),
  "import { templateRef } from '@vueuse/core'\nconst el = templateRef('target')\n", "import { useTemplateRef } from 'vue'\nconst el = useTemplateRef('target')\n",
  "Use Vue 3.5's useTemplateRef().", sev="critical", kind="removal", cat="compatibility", applies={"vueuse": ">=15.0"}, docv="VueUse 15",
  xref=["https://vuejs.org/guide/essentials/template-refs.html"])
P("TEMPLATE-REF-NATIVE", "templateRef (Vue has useTemplateRef)", "https://vuejs.org/guide/essentials/template-refs.html", "useTemplateRef", imp("templateRef"),
  "import { templateRef } from '@vueuse/core'\nconst el = templateRef('target')\n", "import { useTemplateRef } from 'vue'\nconst el = useTemplateRef('target')\n",
  "templateRef is removed in VueUse 15; use useTemplateRef (Vue 3.5+).", sev="minor", kind="deprecation", cat="modernization",
  applies={"vueuse": ">=10.0 <15.0", "vue": ">=3.5"}, docv="Vue 3.5")
P("TIMER-OPTIONS-REMOVED", "interval/immediate timer options (now scheduler)", "https://github.com/vueuse/vueuse/pull/5564",
  "The following deprecated options are removed, pass a scheduler instead",
  call_opt("useNow|useTimestamp|useCountdown|useElementByPoint|useMemory|useVibrate", "interval|immediate|immediateCallback") + "\n"
  + call_opt("useTimeAgo|useTimeAgoIntl", "updateInterval"),
  "const now = useNow({ interval: 1000 })\n", "const now = useNow({ scheduler: (cb) => useIntervalFn(cb, 1000) })\n",
  "These options were removed in VueUse 15; pass a scheduler (useIntervalFn / useRafFn).", sev="critical", kind="removal", cat="compatibility",
  applies={"vueuse": ">=15.0"}, docv="VueUse 15")
P("WEBSOCKET-HEARTBEAT-INTERVAL", "useWebSocket heartbeat.interval removed", "https://github.com/vueuse/vueuse/pull/5564", "useWebSocket : heartbeat.interval",
  r'((call_expression function: (identifier) @f arguments: (arguments (_) (object (pair key: (property_identifier) @h value: (object (pair key: (property_identifier) @i) @match))))) (#eq? @f "useWebSocket") (#eq? @h "heartbeat") (#eq? @i "interval"))',
  "const ws = useWebSocket(url, { heartbeat: { message: 'ping', interval: 1000 } })\n",
  "const ws = useWebSocket(url, { heartbeat: { message: 'ping', scheduler: (cb) => useIntervalFn(cb, 1000) } })\n",
  "Use heartbeat.scheduler.", sev="critical", kind="removal", cat="compatibility", applies={"vueuse": ">=15.0"}, docv="VueUse 15")
P("THROTTLE-FN-TRAILING-DEFAULT", "useThrottleFn trailing now defaults to true", REL + "v15.0.0", "Change default trailing option from false to true",
  r'((call_expression function: (identifier) @f arguments: (arguments . (_) . (_) .)) @match (#match? @f "^(useThrottleFn|refThrottled|watchThrottled)$"))',
  "const onScroll = useThrottleFn(save, 500)\n", "const onScroll = useThrottleFn(save, 500, false)\n",
  "VueUse 15 fires a trailing call by default; pass trailing explicitly if the old behaviour mattered.", sev="minor", kind="migration", cat="correctness",
  applies={"vueuse": ">=15.0"}, docv="VueUse 15", mode="ai-confirm", ai="Would an extra trailing invocation change behaviour here (e.g. duplicate requests)?")
P("PASSIVE-EVENT-SUPPORTED", "isPassiveEventSupported removed", REL + "v14.0.0", "Remove isPassiveEventSupported", imp("isPassiveEventSupported"),
  "import { isPassiveEventSupported } from '@vueuse/core'\n", "const opts = { passive: true }\n", "All supported browsers handle passive listeners.",
  sev="critical", kind="removal", cat="compatibility", applies={"vueuse": ">=14.0"}, docv="VueUse 14")
P("ESM-ONLY-REQUIRE", "require('@vueuse/*') (ESM-only since v13)", REL + "v13.0.0", "Drop CJS build, now it's ESM-only",
  r'((call_expression function: (identifier) @f arguments: (arguments (string (string_fragment) @s))) @match (#eq? @f "require") (#match? @s "^@vueuse/"))',
  "const { useMouse } = require('@vueuse/core')\n", "import { useMouse } from '@vueuse/core'\n", "Use ESM imports (or dynamic import()).",
  sev="critical", kind="removal", cat="compatibility", applies={"vueuse": ">=13.0"}, docv="VueUse 13")
P("RESOLVE-REF-RENAMED", "resolveRef/resolveUnref (renamed in v10)", REL + "v10.0.0", "Rename resolveRef to toRef", imp("resolveRef|resolveUnref"),
  "import { resolveUnref } from '@vueuse/core'\n", "import { toValue } from 'vue'\n", "Use toRef / toValue (Vue 3.3+ has toValue natively).",
  sev="critical", kind="removal", cat="compatibility", applies={"vueuse": ">=10.0"}, docv="VueUse 10")
P("MAYBE-COMPUTED-REF", "MaybeComputedRef type (renamed MaybeRefOrGetter)", REL + "v10.0.0", "Rename MaybeComputedRef to MaybeRefOrGetter",
  imp("MaybeComputedRef|MaybeReadonlyRef"), "import type { MaybeComputedRef } from '@vueuse/core'\n", "import type { MaybeRefOrGetter } from 'vue'\n",
  "Use MaybeRefOrGetter (exported by Vue 3.3+).", sev="major", kind="removal", cat="compatibility", applies={"vueuse": ">=10.0"}, docv="VueUse 10")
P("IS-FUNCTION-STRING", "isFunction/isString utils removed", REL + "v10.0.0", "Remove isFunction and isString utils", imp("isFunction|isString"),
  "import { isString } from '@vueuse/core'\n", "const isString = (v) => typeof v === 'string'\n", "Use typeof checks.", sev="critical", kind="removal",
  cat="compatibility", applies={"vueuse": ">=10.0"}, docv="VueUse 10")
P("USE-TO-FIXED", "useToFixed removed", REL + "v10.0.0", "Remove deprecated function", imp("useToFixed", "@vueuse/math"),
  "import { useToFixed } from '@vueuse/math'\n", "import { usePrecision } from '@vueuse/math'\n", "Use usePrecision.", sev="critical", kind="removal",
  cat="compatibility", applies={"vueuse": ">=10.0"}, docv="VueUse 10")

# ======================================================================== deprecated in favour of Vue built-ins
P("WATCH-PAUSABLE", "watchPausable (Vue 3.5 watch is pausable)", VU + "shared/watchPausable/", "has been added to Vue",
  imp("watchPausable|pausableWatch"), "import { watchPausable } from '@vueuse/core'\nconst { pause, resume } = watchPausable(src, cb)\n",
  "import { watch } from 'vue'\nconst { pause, resume } = watch(src, cb)\n", "Vue 3.5's watch returns pause/resume; this function will be removed.",
  sev="minor", kind="deprecation", cat="modernization", applies={"vueuse": ">=10.0", "vue": ">=3.5"},
  quote="This function will be removed in future version.")
P("COMPUTED-EAGER", "computedEager (plain computed suffices on Vue 3.4+)", VU + "shared/computedEager/", "If you are using Vue 3.4+, you can use computed right away",
  imp("computedEager|eagerComputed"), "import { computedEager } from '@vueuse/core'\nconst isEmpty = computedEager(() => list.value.length === 0)\n",
  "import { computed } from 'vue'\nconst isEmpty = computed(() => list.value.length === 0)\n", "Vue 3.4 computed no longer triggers when the value is unchanged.",
  sev="minor", kind="deprecation", cat="modernization", applies={"vueuse": ">=10.0", "vue": ">=3.4"})
P("USE-VMODEL-DEFINE-MODEL", "useVModel/useVModels (defineModel on Vue 3.4+)", "https://vuejs.org/guide/components/v-model.html",
  "Starting in Vue 3.4, the recommended approach to achieve this is using the", imp("useVModel|useVModels"),
  "import { useVModel } from '@vueuse/core'\nconst props = defineProps(['modelValue'])\nconst emit = defineEmits(['update:modelValue'])\nconst value = useVModel(props, 'modelValue', emit)\n",
  "const value = defineModel()\n", "defineModel() is the built-in two-way binding.", sev="info", kind="modernization", cat="modernization",
  applies={"vueuse": "*", "vue": ">=3.4"}, docv="Vue 3.4", quote="Starting in Vue 3.4, the recommended approach to achieve this is using the defineModel() macro:")
P("TRANSITION-OPTION", "useTransition `transition` option / executeTransition", SRC + "core/useTransition/index.ts",
  "The `transition` option is deprecated, use `easing` instead.",
  call_opt("useTransition", "transition") + "\n" + imp("executeTransition"),
  "const out = useTransition(source, { duration: 300, transition: TransitionPresets.easeInCubic })\n",
  "const out = useTransition(source, { duration: 300, easing: TransitionPresets.easeInCubic })\n", "Use easing (and transition() instead of executeTransition).",
  sev="minor", kind="deprecation", cat="compatibility", applies={"vueuse": ">=13.0"})
P("BREAKPOINTS-VUETIFY", "breakpointsVuetify (ambiguous)", SRC + "core/useBreakpoints/breakpoints.ts", "explictly use `breakpointsVuetifyV2` or `breakpointsVuetifyV3` instead",
  imp("breakpointsVuetify"), "import { breakpointsVuetify, useBreakpoints } from '@vueuse/core'\nconst bp = useBreakpoints(breakpointsVuetify)\n",
  "import { breakpointsVuetifyV3, useBreakpoints } from '@vueuse/core'\nconst bp = useBreakpoints(breakpointsVuetifyV3)\n",
  "Pick the Vuetify version explicitly (the default values differ).", sev="minor", kind="deprecation", cat="correctness", applies={"vueuse": ">=10.0"})
P("MULTI-WATCH-SOURCES-TYPE", "MultiWatchSources from @vueuse (use Vue's)", SRC + "shared/utils/types.ts", "Use `import type { MultiWatchSources } from 'vue'` instead",
  imp("MultiWatchSources"), "import type { MultiWatchSources } from '@vueuse/core'\n", "import type { MultiWatchSources } from 'vue'\n", "Import from vue.",
  sev="info", kind="deprecation", cat="compatibility", applies={"vueuse": ">=13.0", "vue": ">=3.5"})

# ======================================================================== best practices (vueuse.org guide + function docs)
LISTENERS = "useEventListener|onClickOutside|useIntervalFn|useTimeoutFn|useRafFn|useResizeObserver|useMutationObserver|useIntersectionObserver|onKeyStroke|useMediaQuery|useWebSocket|useEventSource|useScroll|useInfiniteScroll|useStorage|useLocalStorage|useSessionStorage"
P("COMPOSABLE-IN-ASYNC-CALLBACK", "VueUse composable created inside an async callback", BP,
  "VueUse's functions also clean up the side-effects automatically",
  f'((call_expression function: (identifier) @cb arguments: (arguments (arrow_function body: (_) @b))) @match (#match? @cb "^(setTimeout|setInterval|requestAnimationFrame|queueMicrotask)$") (#match? @b "\\\\b({LISTENERS})\\\\s*\\\\("))' + "\n"
  + f'((call_expression function: (member_expression property: (property_identifier) @m) arguments: (arguments (arrow_function body: (_) @b))) @match (#match? @m "^(then|addEventListener|on)$") (#match? @b "\\\\b({LISTENERS})\\\\s*\\\\("))',
  "setTimeout(() => {\n  useEventListener(window, 'resize', onResize)\n}, 100)\n", "useEventListener(window, 'resize', onResize)\n",
  "Outside the synchronous setup scope there is no owner to dispose it — the listener/timer leaks after unmount. Create it in setup or wrap in effectScope().",
  sev="major", kind="anti-pattern", cat="correctness", quote="Similar to Vue's watch and computed that will be disposed when the component is unmounted, VueUse's functions also clean up the side-effects automatically.")
P("MODULE-SCOPE-LISTENER", "Listener composable at module scope (never disposed)", BP,
  "Not all functions return a stop handler so a more general solution is to use the",
  f'((program [(expression_statement (call_expression function: (identifier) @f)) (lexical_declaration (variable_declarator value: (call_expression function: (identifier) @f)))] @match) (#match? @f "^({LISTENERS})$"))',
  "import { useEventListener } from '@vueuse/core'\nuseEventListener(window, 'online', sync)\n",
  "import { effectScope } from 'vue'\nimport { useEventListener } from '@vueuse/core'\nexport const scope = effectScope(true)\nscope.run(() => useEventListener(window, 'online', sync))\n",
  "Module-level side effects have no component scope; use createGlobalState/createSharedComposable or an effectScope you can stop (HMR/tests leak otherwise).",
  sev="minor", kind="anti-pattern", cat="correctness", files=["**/*.ts", "**/*.js", "**/*.mjs", "**/*.mts"],
  filters=[r"file.has_re:@vueuse/"], mode="ai-confirm", ai="Is this module-scope side effect intended to live for the app lifetime and safe under HMR/tests/SSR?")
P("UNWRAPPED-ARGUMENT", "Passing .value to a VueUse composable (loses reactivity)", BP,
  "most of the VueUse functions also accept refs for the arguments because refs are reactive",
  r'((call_expression function: (identifier) @f arguments: (arguments (member_expression property: (property_identifier) @v))) @match (#match? @f "^(use[A-Z]\\w*|on[A-Z]\\w*|watch[A-Z]\\w*|ref[A-Z]\\w*)$") (#eq? @v "value"))',
  "import { useTitle } from '@vueuse/core'\nuseTitle(pageTitle.value)\n", "import { useTitle } from '@vueuse/core'\nuseTitle(pageTitle)\n",
  "Pass the ref or a getter (() => x.value) so the composable tracks changes.", sev="minor", kind="anti-pattern", cat="correctness",
  filters=[r"file.has_re:@vueuse/"], mode="ai-confirm", ai="Is the callee a VueUse composable that accepts MaybeRefOrGetter, and should it react to changes of this value?")
P("USE-TITLE-SSR", "useTitle in an SSR app", VU + "core/useTitle/", "This composable isn't compatible with SSR.",
  r'((call_expression function: (identifier) @f) @match (#eq? @f "useTitle"))', "import { useTitle } from '@vueuse/core'\nuseTitle('Dashboard')\n",
  "useHead({ title: 'Dashboard' })\n", "Use useHead/useSeoMeta (Nuxt/unhead) in SSR apps so the title is rendered server-side.", sev="minor", kind="anti-pattern",
  cat="correctness", applies={"vueuse": "*", "nuxt": ">=3.0"}, filters=[r"file.has_re:@vueuse/"])
P("USE-MEMOIZE-NO-CLEAR", "useMemoize without clear()", VU + "core/useMemoize/", "The results are not cleared automatically.",
  r'((call_expression function: (identifier) @f) @match (#eq? @f "useMemoize"))', "const getUser = useMemoize((id) => fetchUser(id))\n",
  "const getUser = useMemoize((id) => fetchUser(id), { cache: new LRUCache({ max: 100 }) })\nonUnmounted(() => getUser.clear())\n",
  "Unbounded caches grow forever; call clear()/delete() or pass a bounded cache.", sev="minor", kind="anti-pattern", cat="performance",
  filters=[r"file.lacks_re:\.clear\(\)|cache\s*:"], quote="The results are not cleared automatically. Call clear() in case you no longer need the results or use own caching mechanism to avoid memory leaks.")
P("NUXT-USEFETCH-SHADOW", "VueUse useFetch in a Nuxt app", VU + "core/useFetch/", "this function will NOT be auto imported in favor of Nuxt's built-in",
  imp("useFetch", "@vueuse/core"), "import { useFetch } from '@vueuse/core'\nconst { data } = useFetch('/api/user').json()\n",
  "const { data } = await useFetch('/api/user')\n", "Nuxt's useFetch dedupes and transfers SSR payloads; VueUse's runs again on the client.",
  sev="info", kind="best-practice", cat="performance", applies={"vueuse": "*", "nuxt": ">=3.0"}, mode="ai-confirm",
  ai="Does this component render on the server where SSR data transfer/deduplication matters?",
  quote="When using with Nuxt 3, this function will NOT be auto imported in favor of Nuxt's built-in useFetch() . Use explicit import if you want to use the function from VueUse.")

RULES = P.R

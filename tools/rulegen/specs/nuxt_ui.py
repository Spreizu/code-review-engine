"""Nuxt UI pack (framework layer on the Vue/Nuxt + JS/TS packs). Targets Nuxt UI 4+ (v3 API changes are still flagged
because v2-era code breaks on v3/v4). Template rules use the vue grammar (target template); script/config rules use
`javascript`. Version dimension `nuxt-ui` (@nuxt/ui or @nuxt/ui-pro). Sources: ui.nuxt.com migration guides (v3, v4) and
installation guide."""
from specs._common import Pack

U = "https://ui.nuxt.com/docs/getting-started/"
M4, M3, INST = U + "migration/v4", U + "migration/v3", U + "installation/nuxt"
P = Pack("NUXTUI", "vue", "Nuxt UI 4.11", {"nuxt-ui": ">=3.0"}, framework="nuxt-ui")
V4 = {"nuxt-ui": ">=4.0"}


def kebab(n):
    import re
    return re.sub(r"(?<!^)([A-Z])", r"-\1", n).lower()


def tagrx(*names):
    return "^(" + "|".join(f"U{n}|u-{kebab(n)}" for n in names) + ")$"


def tag(*names):
    rx = tagrx(*names)
    return "\n".join(f'(({k} (tag_name) @t) @match (#match? @t "{rx}"))' for k in ("start_tag", "self_closing_tag"))


def tagattr(names, attr_rx):
    rx = tagrx(*names) if isinstance(names, (list, tuple)) else tagrx(names)
    return "\n".join(f'(({k} (tag_name) @t [(attribute) (directive_attribute)] @a) @match (#match? @t "{rx}") (#match? @a "{attr_rx}"))'
                     for k in ("start_tag", "self_closing_tag"))


def slot(names, slot_rx):
    rx = tagrx(*names)
    return f'((element (start_tag (tag_name) @t) (template_element (start_tag (directive_attribute) @a) @match)) (#match? @t "{rx}") (#match? @a "{slot_rx}"))'


def T(id, title, url, needle, query, bad, good, msg, **kw):
    kw.setdefault("kind", "removal")
    kw.setdefault("sev", "major")
    kw.setdefault("cat", "migration")
    P(id, title, url, needle, query, f"<template>\n  {bad}\n</template>\n", f"<template>\n  {good}\n</template>\n", msg, target="template", **kw)


def J(id, title, url, needle, query, bad, good, msg, **kw):
    kw.setdefault("kind", "removal")
    kw.setdefault("sev", "major")
    kw.setdefault("cat", "migration")
    P(id, title, url, needle, query, bad, good, msg, lang="javascript", **kw)


# ======================================================================== v4 (from v3 / UI Pro)
T("BUTTON-GROUP-RENAMED", "ButtonGroup renamed to FieldGroup", M4, "The ButtonGroup component has been renamed to FieldGroup",
  tag("ButtonGroup"), "<UButtonGroup><UButton label=\"A\" /></UButtonGroup>", "<UFieldGroup><UButton label=\"A\" /></UFieldGroup>",
  "Rename <UButtonGroup> to <UFieldGroup>.", applies=V4, docv="Nuxt UI 4")
T("PAGE-MARQUEE-RENAMED", "PageMarquee renamed to Marquee", M4, "The PageMarquee component has been renamed to Marquee", tag("PageMarquee"),
  "<UPageMarquee :items=\"items\" />", "<UMarquee :items=\"items\" />", "Rename <UPageMarquee> to <UMarquee>.", applies=V4, docv="Nuxt UI 4")
T("PAGE-ACCORDION-REMOVED", "PageAccordion removed", M4, "The PageAccordion component has been removed in favor of Accordion", tag("PageAccordion"),
  "<UPageAccordion :items=\"items\" />", "<UAccordion :items=\"items\" :unmount-on-hide=\"false\" />",
  "Use <UAccordion :unmount-on-hide=\"false\"> with your ui overrides.", applies=V4, docv="Nuxt UI 4")
T("MODEL-NULLIFY", "nullify model modifier renamed to nullable", M4, "The nullify modifier was renamed to nullable",
  '((directive_attribute (directive_name) @d (directive_modifiers (directive_modifier) @m)) @match (#eq? @d "v-model") (#eq? @m "nullify"))' + "\n"
  + tagattr(["Input", "InputNumber", "Textarea"], "^:model-modifiers=.*nullify"),
  "<UInput v-model.nullify=\"value\" />", "<UInput v-model.nullable=\"value\" />", "Use .nullable (null) or .optional (undefined).", applies=V4, docv="Nuxt UI 4")
J("UI-PRO-IMPORT", "Import from @nuxt/ui-pro", M4, "Replace @nuxt/ui-pro with @nuxt/ui in your imports",
  r'((import_statement source: (string (string_fragment) @s)) @match (#match? @s "^@nuxt/ui-pro(/(vite|vue-plugin|components/.*|runtime/.*))?$"))',
  "import type { BannerProps } from '@nuxt/ui-pro'\n", "import type { BannerProps } from '@nuxt/ui'\n",
  "Nuxt UI Pro merged into @nuxt/ui in v4.", sev="critical", applies=V4, docv="Nuxt UI 4")
J("UI-PRO-MODULE", "@nuxt/ui-pro in nuxt.config modules", M4, "Replace @nuxt/ui-pro with @nuxt/ui in your nuxt.config.ts",
  r'((pair key: (property_identifier) @k value: (array (string (string_fragment) @s) @match)) (#match? @k "^(modules|extends)$") (#eq? @s "@nuxt/ui-pro"))',
  "export default defineNuxtConfig({\n  modules: ['@nuxt/ui-pro']\n})\n", "export default defineNuxtConfig({\n  modules: ['@nuxt/ui']\n})\n",
  "Use the @nuxt/ui module.", sev="critical", applies=V4, docv="Nuxt UI 4", files=["nuxt.config.ts", "nuxt.config.js", "nuxt.config.mjs", "**/nuxt.config.ts", "**/nuxt.config.js"])
J("APP-CONFIG-UIPRO", "uiPro key in app config", M4, "Use the ui key instead of uiPro in your app.config.ts",
  r'((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @k) @match))) (#match? @f "^(defineAppConfig|ui|uiPro)$") (#eq? @k "uiPro"))',
  "export default defineAppConfig({\n  uiPro: { pageCard: { slots: { root: 'rounded-xl' } } }\n})\n",
  "export default defineAppConfig({\n  ui: { pageCard: { slots: { root: 'rounded-xl' } } }\n})\n", "Move uiPro overrides under ui.", applies=V4, docv="Nuxt UI 4")
J("CONTENT-UTILS-REMOVED", "findPageHeadline/findPageBreadcrumb from @nuxt/ui-pro", M4,
  "These are now fully provided by Nuxt Content.",
  r'((import_statement source: (string (string_fragment) @s)) @match (#eq? @s "@nuxt/ui-pro/utils/content"))',
  "import { findPageHeadline } from '@nuxt/ui-pro/utils/content'\n", "import { findPageHeadline } from '@nuxt/content/utils'\n",
  "Import from @nuxt/content/utils.", sev="critical", applies=V4, docv="Nuxt UI 4")
T("NESTED-FORM-NOT-EXPLICIT", "Nested UForm without nested/name", M4, "Nested forms must be enabled explicitly using the nested prop.",
  '((element (start_tag (tag_name) @o) (element (start_tag (tag_name) @t) @match)) (#match? @o "^(UForm|u-form)$") (#match? @t "^(UForm|u-form)$"))\n'
  '((element (start_tag (tag_name) @o) (_ (element (start_tag (tag_name) @t) @match))) (#match? @o "^(UForm|u-form)$") (#match? @t "^(UForm|u-form)$"))',
  "<UForm :state=\"state\"><div v-for=\"(item, i) in state.items\" :key=\"i\"><UForm :state=\"item\" :schema=\"itemSchema\"></UForm></div></UForm>",
  "<UForm :state=\"state\"><div v-for=\"(item, i) in state.items\" :key=\"i\"><UForm :name=\"`items.${i}`\" :schema=\"itemSchema\" nested></UForm></div></UForm>",
  "In v4 nested forms need `nested` + `name` (state is inherited from the parent).", kind="migration", applies=V4, docv="Nuxt UI 4",
  mode="ai-confirm", ai="Is this UForm rendered inside another UForm (directly or via child components) without `nested`?",
  filters=[r"node.lacks_re:\bnested\b"])
T("SCHEMA-TRANSFORM-STATE", "Relying on schema transforms mutating form state", M4,
  "Schema transformations will only be applied to the @submit data and will no longer mutate the form's state.",
  tagattr(["Form"], "^:schema="), "<UForm :state=\"state\" :schema=\"schema\" @submit=\"save(state)\" />",
  "<UForm :state=\"state\" :schema=\"schema\" @submit=\"(e) => save(e.data)\" />",
  "Read transformed values from the submit event (event.data), not from state.", kind="migration", sev="minor", applies=V4, docv="Nuxt UI 4",
  mode="ai-confirm", ai="Does the submit handler/other code read `state` expecting schema-transformed (coerced/trimmed/defaulted) values?",
  filters=[r"node.has_re:@submit=\"[^\"]*\bstate\b"])
T("CHAT-MESSAGE-CONTENT", "UChatMessage :content (AI SDK v5+ uses parts)", M4, "Messages now use parts instead of content",
  tagattr(["ChatMessage"], "^:content="), "<UChatMessage :content=\"message.content\" />", "<UChatMessage :parts=\"message.parts\" />",
  "Pass message.parts.", applies=V4, docv="Nuxt UI 4")
J("USECHAT-REMOVED-MEMBERS", "useChat input/handleSubmit/reload", M4, "input and handleSubmit were removed in favor of sendMessage",
  r'((variable_declarator name: (object_pattern) @p value: (call_expression function: (identifier) @f)) @match (#eq? @f "useChat") (#match? @p "\\b(input|handleSubmit|reload|setMessages)\\b"))',
  "import { useChat } from '@ai-sdk/vue'\nconst { messages, input, handleSubmit } = useChat()\n", "const { messages, sendMessage, regenerate } = useChat()\n",
  "Use sendMessage/regenerate and manage the input ref yourself.", applies=V4, docv="Nuxt UI 4 / AI SDK", filters=[r"file.has_re:@ai-sdk/vue"])

# ======================================================================== v3 (v2-era API that no longer exists)
for old, new, needle in [("Divider", "Separator", "v2 v3 Divider Separator"), ("Dropdown", "DropdownMenu", "Dropdown DropdownMenu"),
                         ("FormGroup", "FormField", "FormGroup FormField"), ("Range", "Slider", "Range Slider"), ("Toggle", "Switch", "Toggle Switch"),
                         ("Notification", "Toast", "Notification Toast"), ("VerticalNavigation", "NavigationMenu orientation=\"vertical\"", "VerticalNavigation NavigationMenu"),
                         ("HorizontalNavigation", "NavigationMenu", "HorizontalNavigation NavigationMenu")]:
    nt = new.split()[0]
    T(f"{kebab(old).upper()}-RENAMED", f"U{old} renamed to U{nt}", M3, needle, tag(old), f"<U{old} />", f"<U{nt} />",
      f"Nuxt UI v3+ renamed U{old} to U{new}.", sev="critical", docv="Nuxt UI 3")
T("RADIO-METER-REMOVED", "URadio / UMeter removed", M3, "Meter Removed", tag("Radio", "Meter", "MeterGroup"), "<URadio v-model=\"v\" value=\"a\" />",
  "<URadioGroup v-model=\"v\" :items=\"items\" />", "URadio was removed (use URadioGroup); UMeter was removed (use UProgress).", sev="critical", docv="Nuxt UI 3")
T("PRO-COMPONENT-RENAMED", "Renamed Nuxt UI Pro v1 component", M3, "Here are the Nuxt UI Pro components that have been renamed or removed",
  tag("BlogList", "ColorModeToggle", "DashboardLayout", "DashboardNavbarToggle", "DashboardPanelHandle", "LandingCTA", "LandingLogos", "LandingSection",
      "NavigationAccordion", "NavigationLinks", "NavigationTree", "PageError", "PricingCard", "PricingGrid"),
  "<UBlogList />", "<UBlogPosts />", "Renamed in v3 (e.g. BlogList→BlogPosts, LandingSection→PageSection, PricingCard→PricingPlan).", sev="critical",
  docv="Nuxt UI 3")
T("PRO-COMPONENT-REMOVED", "Removed Nuxt UI Pro v1 component", M3, "DashboardCard Removed (use PageCard instead)",
  tag("DashboardCard", "DashboardModal", "DashboardPage", "DashboardPanelContent", "DashboardSection", "DashboardSidebarLinks", "DashboardSlideover",
      "FooterLinks", "HeaderLinks", "LandingCard", "LandingFAQ", "LandingGrid", "LandingHero", "LandingTestimonial", "PricingSwitch"),
  "<ULandingHero title=\"Hi\" />", "<UPageHero title=\"Hi\" />", "Removed in v3; use the replacement listed in the migration guide.", sev="critical",
  docv="Nuxt UI 3")
T("GLOBAL-OVERLAYS-REMOVED", "UModals/USlideovers/UNotifications removed", M3,
  "The global Modals , Slideovers and Notifications components have been removed in favor of the App component",
  tag("Modals", "Slideovers", "Notifications"), "<UModals />", "<UApp><NuxtPage /></UApp>", "Wrap the app in <UApp>.", sev="critical", docv="Nuxt UI 3")
T("COLOR-GRAY-BLACK-WHITE", "color=\"gray|black|white\" removed", M3, "The gray , black and white in the color props have been removed in favor of neutral",
  tagattr(["Button", "Badge", "Alert", "Chip", "Avatar", "Link", "Input", "Select", "Checkbox", "Switch", "Progress", "Kbd"], "^color=.(gray|black|white).$"),
  "<UButton color=\"gray\" />", "<UButton color=\"neutral\" variant=\"subtle\" />", "Use color=\"neutral\" with a variant.", docv="Nuxt UI 3")
T("COLOR-TAILWIND-NAME", "Tailwind color name in color prop", M3, "You can no longer use Tailwind CSS colors in the color props, use the new aliases instead",
  tagattr(["Button", "Badge", "Alert", "Chip", "Avatar", "Link", "Input", "Select", "Checkbox", "Switch", "Progress", "Kbd"],
          "^color=.(red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|zinc|stone).$"),
  "<UButton color=\"red\" />", "<UButton color=\"error\" />", "Use design-system aliases (primary, secondary, success, info, warning, error, neutral).",
  docv="Nuxt UI 3")
T("GRAY-UTILITY-CLASSES", "gray-* utility classes (renamed neutral)", M3, "The gray color has been renamed to neutral",
  '((attribute (attribute_name) @n (quoted_attribute_value (attribute_value) @v)) @match (#eq? @n "class") (#match? @v "\\\\b(text|bg|border|ring|divide)-gray-[0-9]+"))',
  "<p class=\"text-gray-500 dark:text-gray-400\" />", "<p class=\"text-muted\" />", "Use neutral-* or design tokens (text-muted, text-highlighted, bg-elevated).",
  kind="migration", sev="minor", docv="Nuxt UI 3", mode="ai-confirm", ai="Does this project still define a custom `gray` palette (Tailwind v4 default gray exists but differs from the Nuxt UI neutral alias)?")
T("OPTIONS-LINKS-TO-ITEMS", ":options / :links renamed to :items", M3, "The links and options props have been renamed to items for consistency",
  tagattr(["Select", "SelectMenu", "InputMenu", "RadioGroup", "Breadcrumb", "NavigationMenu"], "^:(options|links)="),
  "<USelect :options=\"countries\" />", "<USelect :items=\"countries\" />", "Use :items.", sev="critical", docv="Nuxt UI 3")
J("ITEM-CLICK-TO-ONCLICK", "Menu item click: handler (now onClick)", M3, "The click field in different components has been removed in favor of the native Vue onClick event",
  r'((object (pair key: (property_identifier) @l) (pair key: (property_identifier) @c value: [(arrow_function) (function_expression)]) @match) (#eq? @l "label") (#eq? @c "click"))',
  "const items = [{ label: 'Edit', click: () => edit() }]\n", "const items = [{ label: 'Edit', onClick: () => edit() }]\n",
  "Rename click to onClick (Toast actions, DropdownMenu, NavigationMenu, CommandPalette items).", sev="critical", docv="Nuxt UI 3")
T("OVERLAY-V-MODEL", "v-model on Modal/Slideover/ContextMenu (now v-model:open)", M3,
  "The v-model:open directive and default-open prop are now used to control visibility",
  tagattr(["Modal", "Slideover", "ContextMenu"], "^v-model="), "<UModal v-model=\"open\" />", "<UModal v-model:open=\"open\" />",
  "Use v-model:open (or the trigger slot).", sev="critical", docv="Nuxt UI 3")
T("PREVENT-CLOSE", "prevent-close removed (use :dismissible=\"false\")", M3, "The prevent-close prop has been removed in favor of the dismissible prop",
  tagattr(["Modal", "Slideover"], "^(prevent-close|:prevent-close=)"), "<UModal prevent-close />", "<UModal :dismissible=\"false\" />",
  "Use :dismissible=\"false\".", docv="Nuxt UI 3")
T("PAGINATION-V-MODEL", "UPagination v-model (now v-model:page)", M3, "The Pagination component v-model directive has been renamed to v-model:page",
  tagattr(["Pagination"], "^v-model="), "<UPagination v-model=\"page\" />", "<UPagination v-model:page=\"page\" />", "Use v-model:page.", sev="critical", docv="Nuxt UI 3")
T("SELECT-CHANGE-EVENT", "@change on Select/SelectMenu/RadioGroup (native event now)", M3,
  "The change event now emits the native change event, not the new value, which is now emitted in the update:modelValue event",
  tagattr(["Select", "SelectMenu", "RadioGroup"], "^@change="), "<USelectMenu v-model=\"c\" :items=\"items\" @change=\"onPick\" />",
  "<USelectMenu v-model=\"c\" :items=\"items\" @update:model-value=\"onPick\" />", "Listen to update:modelValue for the new value.",
  kind="migration", docv="Nuxt UI 3")
T("SELECT-MENU-SEARCHABLE", "USelectMenu searchable (now search-input)", M3, "The SelectMenu component searchable prop has been renamed to search-input",
  tagattr(["SelectMenu"], "^:?searchable"), "<USelectMenu searchable :items=\"items\" />", "<USelectMenu :items=\"items\" />",
  "search-input is on by default; remove searchable or use :search-input.", docv="Nuxt UI 3")
T("ACCORDION-MULTIPLE", "UAccordion multiple (now type=\"multiple\")", M3, "The multiple prop has been replaced by the type prop",
  tagattr(["Accordion"], "^:?multiple"), "<UAccordion multiple :items=\"items\" />", "<UAccordion type=\"multiple\" :items=\"items\" />",
  "Use type=\"multiple\".", docv="Nuxt UI 3")
T("ACCORDION-DEFAULT-OPEN", "UAccordion default-open removed", M3, "The Accordion component default-open prop and defaultOpen item property have been removed",
  tagattr(["Accordion"], "^:?default-open"), "<UAccordion default-open :items=\"items\" />", "<UAccordion :default-value=\"['0']\" :items=\"items\" />",
  "Use default-value or v-model.", docv="Nuxt UI 3")
T("ITEM-SLOT-REMOVED", "#item slot on Accordion/Tabs removed", M3, "The Accordion component #item slot has been removed in favor of #content and #body",
  slot(["Accordion", "Tabs"], "^(#item|v-slot:item)\\\\b"),
  "<UAccordion :items=\"items\"><template #item=\"{ item }\">{{ item.content }}</template></UAccordion>",
  "<UAccordion :items=\"items\"><template #content=\"{ item }\">{{ item.content }}</template></UAccordion>", "Use #content (or #body).", docv="Nuxt UI 3")
T("UNMOUNT-PROP", "unmount prop (now unmount-on-hide)", M3, "unmount prop has been renamed to unmount-on-hide",
  tagattr(["Accordion", "Tabs"], "^:?unmount(=|$)"), "<UTabs :unmount=\"false\" :items=\"tabs\" />", "<UTabs :unmount-on-hide=\"false\" :items=\"tabs\" />",
  "Use unmount-on-hide (defaults to true).", docv="Nuxt UI 3", quote="The Accordion component unmount prop has been renamed to unmount-on-hide and now defaults to true .")
T("TABLE-ROWS", "UTable :rows (now :data)", M3, "The Table component now uses TanStack Table under the hood. The rows prop has been renamed to data",
  tagattr(["Table"], "^:rows="), "<UTable :rows=\"rows\" />", "<UTable :data=\"data\" />", "Use :data.", sev="critical", docv="Nuxt UI 3")
J("TABLE-COLUMN-KEY-LABEL", "Table column {key,label} (now {accessorKey,header})", M3, "The Table component columns definition is now explicit and semantic",
  r'((variable_declarator name: (identifier) @n value: (_ (object) @o)) @match (#match? @n "(?i)columns$") (#match? @o "\\bkey\\s*:") (#match? @o "\\blabel\\s*:"))',
  "const columns = [{ key: 'status', label: 'Status' }]\n", "const columns = [{ accessorKey: 'status', header: 'Status' }]\n",
  "Use TanStack column defs (accessorKey, header, cell).", sev="critical", docv="Nuxt UI 3", mode="ai-confirm", ai="Are these columns passed to UTable?")
T("TABLE-DATA-SLOT", "#<column>-data slot (now -cell)", M3, "row cell slot names have been changed from",
  slot(["Table"], "^(#|v-slot:)[\\\\w-]+-data\\\\b"), "<UTable :data=\"d\"><template #status-data=\"{ row }\">{{ row.status }}</template></UTable>",
  "<UTable :data=\"d\"><template #status-cell=\"{ row }\">{{ row.original.status }}</template></UTable>", "Rename to #<accessorKey>-cell.",
  docv="Nuxt UI 3")
T("TABS-DEFAULT-INDEX", "UTabs default-index (now default-value)", M3, "The Tabs component default-index prop has been removed in favor of default-value",
  tagattr(["Tabs"], "^:?default-index"), "<UTabs :default-index=\"0\" :items=\"tabs\" />", "<UTabs :default-value=\"0\" :items=\"tabs\" />",
  "Use default-value.", docv="Nuxt UI 3")
T("ALERT-CLOSE-BUTTON", "UAlert close-button / @close", M3, "The Alert component close-button prop has been replaced by the close prop",
  tagattr(["Alert"], "^(:?close-button|@close=)"), "<UAlert :close-button=\"{ variant: 'link' }\" @close=\"open = false\" />",
  "<UAlert :close=\"{ variant: 'link' }\" @update:open=\"open = $event\" />", "Use :close and @update:open.", docv="Nuxt UI 3")
T("ALERT-ICON-SLOT", "UAlert #icon/#avatar slots (now #leading)", M3, "The Alert component #icon and #avatar slots have been replaced by a single #leading slot",
  slot(["Alert"], "^(#|v-slot:)(icon|avatar)\\\\b"), "<UAlert><template #icon><UIcon name=\"i-lucide-terminal\" /></template></UAlert>",
  "<UAlert><template #leading><UIcon name=\"i-lucide-terminal\" /></template></UAlert>", "Use #leading.", docv="Nuxt UI 3")
T("FORM-VALIDATE-ON-SUBMIT", "validate-on containing 'submit'", M3, "The Form component now always validates on submit.",
  tagattr(["Form"], "^:validate-on=.*submit"), "<UForm :validate-on=\"['submit']\" />", "<UForm :validate-on=\"[]\" />",
  "Submit always validates; pass [] to validate only on submit.", kind="migration", sev="minor", docv="Nuxt UI 3")
T("POPPER-PROP", ":popper (now :content)", M3, "The popper prop has been replaced by content for positioning",
  tagattr(["Tooltip", "Popover", "DropdownMenu", "ContextMenu", "SelectMenu", "InputMenu"], "^:popper="),
  "<UTooltip :popper=\"{ placement: 'top' }\" />", "<UTooltip :content=\"{ side: 'top' }\" />", "Use :content={ side, align }.", docv="Nuxt UI 3")
T("TOOLTIP-SHORTCUTS", "UTooltip shortcuts/prevent", M3, "The Tooltip component shortcuts prop has been renamed to kbds and prevent to disabled",
  tagattr(["Tooltip"], "^(:shortcuts=|:?prevent(=|$))"), "<UTooltip text=\"Open\" :shortcuts=\"['⌘', 'O']\" />", "<UTooltip text=\"Open\" :kbds=\"['meta', 'O']\" />",
  "Use kbds / disabled.", docv="Nuxt UI 3")
T("POPOVER-PANEL-SLOT", "UPopover #panel (now #content)", M3, "The Popover component #panel slot has been renamed to #content",
  slot(["Popover"], "^(#|v-slot:)panel\\\\b"), "<UPopover><UButton label=\"Open\" /><template #panel><div /></template></UPopover>",
  "<UPopover><UButton label=\"Open\" /><template #content><div /></template></UPopover>", "Use #content.", docv="Nuxt UI 3")
T("PROGRESS-VALUE", "UProgress value/indicator", M3, "The Progress component value prop has been replaced by model-value and indicator by status",
  tagattr(["Progress"], "^(:value=|:?indicator(=|$))"), "<UProgress :value=\"50\" indicator />", "<UProgress :model-value=\"50\" status />",
  "Use model-value / status.", docv="Nuxt UI 3")
T("CAROUSEL-INDICATORS", "UCarousel indicators (now dots)", M3, "The Carousel component indicators prop has been renamed to dots",
  tagattr(["Carousel"], "^:?indicators"), "<UCarousel :items=\"items\" indicators />", "<UCarousel :items=\"items\" dots />", "Use dots.", docv="Nuxt UI 3")
T("HELP-PROP", "help prop (now description)", M3, "The help prop/property has been renamed to description",
  tagattr(["Checkbox", "RadioGroup", "FormField"], "^:?help="), "<UCheckbox label=\"Remember me\" help=\"Save my login\" />",
  "<UCheckbox label=\"Remember me\" description=\"Save my login\" />", "Use description (FormField keeps help).", docv="Nuxt UI 3",
  filters=[r"node.lacks_re:^<(UFormField|u-form-field)\b"])
T("BREADCRUMB-DIVIDER", "UBreadcrumb divider (now separator-icon)", M3, "The Breadcrumb component divider prop has been renamed to separator-icon",
  tagattr(["Breadcrumb"], "^:?divider="), "<UBreadcrumb :items=\"items\" divider=\"i-lucide-arrow-right\" />",
  "<UBreadcrumb :items=\"items\" separator-icon=\"i-lucide-arrow-right\" />", "Use separator-icon.", docv="Nuxt UI 3")
T("AVATAR-CHIP-PROPS", "UAvatar chip-* props (now :chip)", M3, "chip props ( chip-color , chip-position , chip-text ) have been consolidated into a single chip prop",
  tagattr(["Avatar"], "^:?chip-(color|position|text)="), "<UAvatar src=\"/a.png\" chip-color=\"green\" chip-position=\"top-right\" />",
  "<UAvatar src=\"/a.png\" :chip=\"{ color: 'success', position: 'top-right' }\" />", "Use :chip={...}.", docv="Nuxt UI 3")
T("BUTTON-PADDED-TRUNCATE", "UButton padded/truncate removed", M3, "The Button component padded and truncate props have been removed.",
  tagattr(["Button"], "^:?(padded|truncate)(=|$)"), "<UButton :padded=\"false\" icon=\"i-lucide-x\" />", "<UButton square icon=\"i-lucide-x\" />",
  "Use square (or classes).", docv="Nuxt UI 3")
T("CHIP-SHOW", "UChip :show (now v-model:show)", M3, "The Chip component show prop is now a model", tagattr(["Chip"], "^:show="),
  "<UChip :show=\"isVisible\" />", "<UChip v-model:show=\"isVisible\" />", "Use v-model:show (or :show with @update:show).", kind="migration", sev="minor",
  docv="Nuxt UI 3")
J("COMMAND-PALETTE-COMMANDS", "CommandPalette groups[].commands (now items)", M3, "Each group now has an items array and uses onSelect instead of click",
  r'((object (pair key: (property_identifier) @i) (pair key: (property_identifier) @c value: (array)) @match) (#eq? @i "id") (#eq? @c "commands"))',
  "const groups = [{ id: 'actions', label: 'Actions', commands: [{ id: 'new', label: 'New file' }] }]\n",
  "const groups = [{ id: 'actions', label: 'Actions', items: [{ id: 'new', label: 'New file' }] }]\n", "Rename commands to items.", sev="critical",
  docv="Nuxt UI 3")
J("TOAST-TIMEOUT", "toast.add({ timeout }) (now duration)", M3, "The useToast() composable timeout prop has been renamed to duration",
  r'((call_expression function: (member_expression property: (property_identifier) @a) arguments: (arguments (object (pair key: (property_identifier) @k) @match))) (#eq? @a "add") (#eq? @k "timeout"))',
  "const toast = useToast()\ntoast.add({ title: 'Invitation sent', timeout: 0 })\n", "toast.add({ title: 'Invitation sent', duration: 0 })\n", "Use duration.",
  docv="Nuxt UI 3", filters=[r"file.has_re:useToast"], quote="The useToast() composable timeout prop has been renamed to duration :")
J("USE-MODAL-REMOVED", "useModal/useSlideover removed (useOverlay)", M3,
  "The useModal and useSlideover composables have been removed in favor of a more generic useOverlay composable",
  r'((call_expression function: (identifier) @f) @match (#match? @f "^(useModal|useSlideover)$"))', "const modal = useModal()\nmodal.open(ConfirmModal)\n",
  "const overlay = useOverlay()\nconst modal = overlay.create(ConfirmModal)\n", "Use useOverlay().create(Component, { props }).", sev="critical",
  docv="Nuxt UI 3")
J("FORM-ERROR-PATH", "FormError.path (now name)", M3, "The error object property for targeting form fields has been renamed from path to name",
  r'((call_expression function: (member_expression property: (property_identifier) @p) arguments: (arguments (object (pair key: (property_identifier) @k) @match))) (#eq? @p "push") (#eq? @k "path"))',
  "function validate(state: any): FormError[] {\n  const errors = []\n  errors.push({ path: 'email', message: 'Required' })\n  return errors\n}\n",
  "function validate(state: any): FormError[] {\n  const errors = []\n  errors.push({ name: 'email', message: 'Required' })\n  return errors\n}\n",
  "Use name.", sev="critical", docv="Nuxt UI 3", filters=[r"file.has_re:FormError|UForm"])
J("APP-CONFIG-COLORS", "ui.primary/ui.gray in app config (now ui.colors)", M3, "The color configuration in app.config.ts has been moved into a colors object",
  r'((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @u value: (object (pair key: (property_identifier) @k) @match))))) (#eq? @f "defineAppConfig") (#eq? @u "ui") (#match? @k "^(primary|gray)$"))',
  "export default defineAppConfig({\n  ui: { primary: 'green', gray: 'cool' }\n})\n",
  "export default defineAppConfig({\n  ui: { colors: { primary: 'green', neutral: 'slate' } }\n})\n", "Move to ui.colors (gray → neutral).", sev="critical",
  docv="Nuxt UI 3")
J("APP-CONFIG-V2-THEME", "v2-style component overrides in app config", M3,
  "Nuxt UI components are now styled using the Tailwind Variants API , which makes all the overrides you made using the app.config.ts and the ui prop obsolete.",
  r'((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @u value: (object (pair key: (property_identifier) @c value: (object (pair key: (property_identifier) @k) @match))))))) (#eq? @f "defineAppConfig") (#eq? @u "ui") (#not-match? @c "^colors$") (#match? @k "^(default|font|rounded|padding|size|color|variant|wrapper|base)$"))',
  "export default defineAppConfig({\n  ui: { button: { font: 'font-bold', default: { size: 'md' } } }\n})\n",
  "export default defineAppConfig({\n  ui: { button: { slots: { base: 'font-medium' }, defaultVariants: { size: 'md' } } }\n})\n",
  "Use slots / variants / defaultVariants per the component theme.", kind="migration", docv="Nuxt UI 3", mode="ai-confirm",
  ai="Is this a v2-style override (not slots/variants/compoundVariants/defaultVariants) for a Nuxt UI component theme?")
T("APP-WRAPPER-MISSING", "app.vue without <UApp>", INST, "The App component sets up global config and is required for Toast , Tooltip and programmatic overlays .",
  '((document (template_element) @match) (#not-match? @match "<(UApp|u-app)[\\\\s>]"))', "<NuxtPage />", "<UApp><NuxtPage /></UApp>",
  "Wrap the root in <UApp>; toasts, tooltips and useOverlay depend on it.", kind="best-practice", sev="major", cat="correctness",
  files=["app.vue", "app/app.vue", "**/app/app.vue", "src/App.vue", "**/src/App.vue"])

# ------------------------------------------------------------- official Nuxt UI skill checklist (nuxt/ui skills/nuxt-ui, MIT); own detection/wording
J("CONTENT-MODULE-ORDER", "@nuxt/content registered before @nuxt/ui", U + "integrations/content",
  "You need to register @nuxt/content after @nuxt/ui in the modules array",
  r'((pair key: (property_identifier) @m value: (array (string (string_fragment) @c) (string (string_fragment) @u)) @match) (#eq? @m "modules") (#eq? @c "@nuxt/content") (#match? @u "^@nuxt/ui(-pro)?$"))',
  "export default defineNuxtConfig({\n  modules: ['@nuxt/content', '@nuxt/ui'],\n})\n", "export default defineNuxtConfig({\n  modules: ['@nuxt/ui', '@nuxt/content'],\n})\n",
  "Put @nuxt/ui before @nuxt/content, otherwise the Nuxt UI prose components are not registered for markdown.",
  kind="best-practice", sev="major", cat="correctness", docv="Nuxt UI 4.x")
T("RAW-PALETTE-CLASS", "Raw Tailwind palette color instead of a semantic color", U + "theme/design-system",
  "Nuxt UI's color system is designed around semantic naming rather than specific color values",
  '((attribute (attribute_name) @n (quoted_attribute_value (attribute_value) @v)) @match (#eq? @n "class") (#match? @v "(^|\\\\s)(dark:)?(text|bg|border|ring|divide|outline)-(slate|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-[0-9]{2,3}(\\\\s|$)"))',
  "<p class=\"text-zinc-500 dark:text-zinc-400\">Last updated</p>", "<p class=\"text-muted\">Last updated</p>",
  "Palette classes bypass the theme and need manual dark-mode pairs. Use the semantic utilities (text-muted, bg-elevated, border-default, text-error ...).",
  kind="best-practice", sev="info", cat="maintainability", docv="Nuxt UI 4.x", mode="ai-confirm",
  ai="Is this UI-chrome color that should follow the theme (not a deliberate brand, illustration or data-visualisation color)?")

RULES = P.R

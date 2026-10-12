"""Payload CMS pack (3.x and 4.x; framework layer on the JS/TS + React packs). Language `javascript` (runs on JS/TS/TSX).
Version dimension `payload`. Sources: payloadcms.com docs (3.x: 2.0→3.0 migration guide, Local API, access control,
hooks, transactions, environment variables) and the official 3.0→4.0 migration guide (docs/migration-guide/v4.mdx in
payloadcms/payload, rendered from the repo because v4 is pre-release)."""
from specs._common import Pack

D = "https://payloadcms.com/docs/"
M3 = D + "migration-guide/overview"
M4 = "https://raw.githubusercontent.com/payloadcms/payload/main/docs/migration-guide/v4.mdx"
P = Pack("PAYLOAD", "javascript", "Payload 3.x docs", {"payload": ">=3.0"}, framework="payload")
V3, V4, PRE4 = {"payload": ">=3.0"}, {"payload": ">=4.0"}, {"payload": ">=3.0 <4.0"}


def imp(src, names):
    return (f'((import_statement (import_clause (named_imports (import_specifier name: (identifier) @n))) source: (string (string_fragment) @s)) @match '
            f'(#match? @s "^({src})$") (#match? @n "^({names})$"))')


def src(s):
    return f'((import_statement source: (string (string_fragment) @s)) @match (#match? @s "^({s})$"))'


def key(k, parent=None):
    if parent:
        return (f'((pair key: (property_identifier) @p value: (object (pair key: (property_identifier) @k) @match)) '
                f'(#match? @p "^({parent})$") (#match? @k "^({k})$"))')
    return f'((pair key: (property_identifier) @k) @match (#match? @k "^({k})$"))'


def destr(fn, names):
    return (f'((variable_declarator name: (object_pattern) @o value: (call_expression function: (identifier) @f)) @match '
            f'(#eq? @f "{fn}") (#match? @o "\\\\b({names})\\\\b"))')


LOCAL = "find|findByID|findGlobal|create|update|updateGlobal|delete|count|findVersions|duplicate"


def local_call(extra=""):
    return (f'((call_expression function: (member_expression object: (_) @o property: (property_identifier) @m) arguments: (arguments (object) @a)) @match '
            f'(#match? @o "(^|\\\\.)payload$") (#match? @m "^({LOCAL})$"){extra})')


def M(id, title, needle, query, bad, good, msg, v=3, **kw):
    kw.setdefault("kind", "removal")
    kw.setdefault("sev", "major")
    kw.setdefault("cat", "migration")
    P(id, title, M3 if v == 3 else M4, needle, query, bad, good, msg, applies=V3 if v == 3 else V4,
      docv="Payload 3.0" if v == 3 else "Payload 4.0", **kw)


# ======================================================================== 2.x → 3.0 (applies to 3.x and later)
M("ADMIN-BUNDLER", "admin.bundler / bundler packages", "Delete the admin.bundler property from your Payload Config.",
  key("bundler", "admin") + "\n" + src("@payloadcms/bundler-(webpack|vite)"),
  "export default buildConfig({\n  admin: { bundler: webpackBundler() },\n})\n", "export default buildConfig({\n  admin: {},\n})\n",
  "Next.js bundles the admin panel; remove the bundler and its package.", sev="critical")
M("PAYLOAD-PUBLIC-ENV", "PAYLOAD_PUBLIC_ env var on the client", "Environment variables prefixed with PAYLOAD_PUBLIC will no longer be available on the client.",
  r'((member_expression object: (member_expression object: (identifier) @p property: (property_identifier) @e) property: (property_identifier) @v) @match (#eq? @p "process") (#eq? @e "env") (#match? @v "^PAYLOAD_PUBLIC_"))',
  "'use client'\nconst v = process.env.PAYLOAD_PUBLIC_MY_ENV_VAR\n", "'use client'\nconst v = process.env.NEXT_PUBLIC_MY_ENV_VAR\n",
  "Use NEXT_PUBLIC_ (and audit what you expose).", sev="critical", filters=[r"file.has_re:\A(?:\s|//[^\n]*|/\*(?s:.*?)\*/)*['\"]use client['\"]"])
M("REQ-HEADERS-INDEX", "req.headers['x'] (req is a Web Request now)", "The req object used to extend the Express Request , but now extends the Web Request .",
  r'((subscript_expression object: (member_expression object: (identifier) @r property: (property_identifier) @h)) @match (#eq? @r "req") (#eq? @h "headers"))',
  "import type { PayloadRequest } from 'payload'\nconst type = req.headers['content-type']\n", "import type { PayloadRequest } from 'payload'\nconst type = req.headers.get('content-type')\n", "Use req.headers.get().", sev="critical",
  filters=[r"file.has_re:from ['\"](payload|@payloadcms/)"])
M("ADMIN-CSS", "admin.css / admin.scss removed", "The admin.css and admin.scss properties in the Payload Config have been removed.",
  key("css|scss", "admin"), "export default buildConfig({\n  admin: { css: './custom.css' },\n})\n", "export default buildConfig({\n  admin: {},\n})\n",
  "Use (payload)/custom.scss or a custom provider.", filters=[r"file.has_re:buildConfig"])
M("ADMIN-INDEX-HTML", "admin.indexHTML removed", "The admin.indexHTML property has been removed.", key("indexHTML", "admin"),
  "export default buildConfig({\n  admin: { indexHTML: './index.html' },\n})\n", "export default buildConfig({\n  admin: {},\n})\n", "Delete it.")
M("COLLECTION-ADMIN-HOOKS", "collection.admin.hooks removed", "The collection.admin.hooks property has been removed.", key("hooks", "admin"),
  "export const Posts = {\n  slug: 'posts',\n  admin: { hooks: { beforeDuplicate: ({ data }) => data } },\n}\n",
  "export const Posts = {\n  slug: 'posts',\n  fields: [{ name: 'title', type: 'text', hooks: { beforeDuplicate: [({ value }) => value] } }],\n}\n",
  "Use the field-level beforeDuplicate hook.")
M("STATIC-DIR-RELATIVE", "upload.staticDir relative / __dirname", "The upload.staticDir property must now be an absolute path.",
  r'((pair key: (property_identifier) @k value: (string (string_fragment) @v)) @match (#eq? @k "staticDir") (#not-match? @v "^/"))' + "\n"
  + r'((pair key: (property_identifier) @k value: (_) @v) @match (#eq? @k "staticDir") (#match? @v "__dirname"))',
  "export const Media = {\n  slug: 'media',\n  upload: { staticDir: 'uploads' },\n}\n",
  "const dirname = path.dirname(fileURLToPath(import.meta.url))\nexport const Media = {\n  slug: 'media',\n  upload: { staticDir: path.resolve(dirname, '../uploads') },\n}\n",
  "staticDir must be absolute (ESM has no __dirname; derive it from import.meta.url).", kind="migration")
M("STATIC-URL", "upload.staticURL removed", "The upload.staticURL property has been removed.", key("staticURL", "upload"),
  "export const Media = {\n  slug: 'media',\n  upload: { staticURL: '/media' },\n}\n", "export const Media = {\n  slug: 'media',\n  upload: true,\n}\n",
  "Use generateFileURL on your storage adapter.")
M("ADMIN-FAVICON", "admin.favicon (now admin.icons)", "The admin.favicon property is now admin.icons and the types have changed", key("favicon", "admin"),
  "export default buildConfig({\n  admin: { favicon: '/favicon.svg' },\n})\n", "export default buildConfig({\n  admin: { meta: { icons: [{ url: '/favicon.svg' }] } },\n})\n",
  "Use admin icons.")
M("ADMIN-OG-IMAGE", "admin.meta.ogImage (now openGraph.images)", "The admin.meta.ogImage property has been replaced by admin.meta.openGraph.images",
  key("ogImage", "meta"), "export default buildConfig({\n  admin: { meta: { ogImage: '/og.png' } },\n})\n",
  "export default buildConfig({\n  admin: { meta: { openGraph: { images: [{ url: '/og.png' }] } } },\n})\n", "Use openGraph.images.")
M("ADMIN-LOGOUT-ROUTE", "admin.logoutRoute / inactivityRoute", "The admin.logoutRoute and admin.inactivityRoute properties have been consolidated into a single admin.routes property.",
  key("logoutRoute|inactivityRoute", "admin"), "export default buildConfig({\n  admin: { logoutRoute: '/custom-logout' },\n})\n",
  "export default buildConfig({\n  admin: { routes: { logout: '/custom-logout' } },\n})\n", "Move to admin.routes.")
M("AFTER-ERROR-FUNCTION", "hooks.afterError as a single function", "hooks.afterError is now an array of functions instead of a single function.",
  r'((pair key: (property_identifier) @k value: [(arrow_function) (function_expression)]) @match (#eq? @k "afterError"))',
  "export default buildConfig({\n  hooks: { afterError: async ({ error }) => log(error) },\n})\n",
  "export default buildConfig({\n  hooks: { afterError: [async ({ error }) => log(error)] },\n})\n", "Wrap it in an array.", sev="critical")
M("UI-FROM-PAYLOAD", "React components/hooks imported from 'payload'", "All Payload React components have been moved from the payload package to @payloadcms/ui .",
  imp("payload|payload/components.*", "use[A-Z]\\\\w*|[A-Z]\\\\w*(Field|Input|Button|Provider)|Gutter|Banner|Pill|Translation"),
  "import { useField, TextField } from 'payload'\n", "import { useField, TextField } from '@payloadcms/ui'\n", "Import from @payloadcms/ui.", sev="critical")
M("COMPONENT-DIRECT-IMPORT", "Custom Component passed as an import (not a path)", "All Custom Components are now defined as file paths instead of direct imports.",
  r'((pair key: (property_identifier) @c value: (object (pair key: (property_identifier) value: (identifier) @v) @match)) (#match? @c "^(components|logout|graphics|afterNavLinks|beforeNavLinks|edit|views|Field|Cell)$") (#match? @v "^[A-Z]"))',
  "import { MyComponent } from './components/Logout'\nexport default buildConfig({\n  admin: { components: { logout: { Button: MyComponent } } },\n})\n",
  "export default buildConfig({\n  admin: { components: { logout: { Button: '/components/Logout#MyComponent' } } },\n})\n",
  "Reference components by path ('/path/to/File#Export') and regenerate the import map.", sev="critical")
M("DESCRIPTION-COMPONENT", "admin.description as a React component", "The admin.description property within Collection, Globals, and Fields no longer accepts a React Component.",
  r'((pair key: (property_identifier) @a value: (object (pair key: (property_identifier) @k value: (identifier) @v) @match)) (#eq? @a "admin") (#eq? @k "description") (#match? @v "^[A-Z]"))',
  "export const Posts = {\n  slug: 'posts',\n  admin: { description: MyCustomDescription },\n}\n",
  "export const Posts = {\n  slug: 'posts',\n  admin: { components: { edit: { Description: 'path/to/MyCustomDescription' } } },\n}\n",
  "Use admin.components.(edit.)Description with a path.")
M("CLIENT-HOOKS-WITHOUT-USE-CLIENT", "Admin component uses hooks without 'use client'",
  "All Custom Components are now server-rendered by default, and therefore, cannot use state or hooks directly.",
  r'((call_expression function: (identifier) @f) @match (#match? @f "^use(State|Effect|Reducer|Ref|Field|Form|FormFields|Config|DocumentInfo|Translation|Auth|Locale|ListQuery)$"))',
  "import { useField } from '@payloadcms/ui'\nexport const MyField = () => {\n  const { value } = useField({ path: 'title' })\n  return value\n}\n",
  "'use client'\nimport { useField } from '@payloadcms/ui'\nexport const MyField = () => {\n  const { value } = useField({ path: 'title' })\n  return value\n}\n",
  "Add 'use client' at the top of the file.", kind="anti-pattern", sev="critical", cat="correctness",
  filters=[r"file.has_re:@payloadcms/ui", r"file.lacks_re:\A(?:\s|//[^\n]*|/\*(?s:.*?)\*/)*['\"]use client['\"]"])
M("VIEW-KEYS-PASCAL", "PascalCase admin view keys", "All default view keys are now camelcase", key("Account|Edit|Default|Dashboard|Version|Versions|API|LivePreview", "views"),
  "export const Posts = {\n  slug: 'posts',\n  admin: { views: { Edit: { Default: { Component: './V' } } } },\n}\n",
  "export const Posts = {\n  slug: 'posts',\n  admin: { components: { views: { edit: { default: { Component: './V' } } } } },\n}\n", "Use camelCase keys (edit, default, account).")
M("TAB-PILL-LABEL", "Tab.pillLabel (now tab.Pill)", "has been replaced with admin.components.views[key].tab.Pill", key("pillLabel"),
  "import type { CollectionConfig } from 'payload'\nconst views = { Edit: { Tab: { pillLabel: 'Hello' } } }\n", "const views = { edit: { tab: { Pill: './path/to/CustomPill.tsx' } } }\n", "Use tab.Pill (a component path).",
  filters=[r"file.has_re:payload"])
M("REACT-I18N-TRANS", "Trans from react-i18n", "react-i18n was removed, the Trans component from react-i18n has been replaced with a Payload-provided solution",
  imp("react-i18n|react-i18next", "Trans"), "import { Trans } from 'react-i18n'\nimport { useConfig } from '@payloadcms/ui'\n", "import { Translation } from '@payloadcms/ui'\n", "Use <Translation> from @payloadcms/ui.",
  filters=[r"file.has_re:payload"])
M("ENDPOINT-RES-ARG", "Endpoint handler using (req, res)", "All endpoint handlers have changed. The args no longer include res , and next",
  r'((pair key: (property_identifier) @k value: (arrow_function parameters: (formal_parameters (_) (_) @r))) @match (#eq? @k "handler") (#match? @r "^res\\b"))',
  "export const Posts = {\n  slug: 'posts',\n  endpoints: [{ path: '/whoami', method: 'get', handler: (req, res) => { res.json({ ok: true }) } }],\n}\n",
  "export const Posts = {\n  slug: 'posts',\n  endpoints: [{ path: '/whoami', method: 'get', handler: (req) => Response.json({ ok: true }) }],\n}\n",
  "Return a Web Response (Response.json(...)); use req.routeParams.", sev="critical")
M("ENDPOINT-REQ-DATA", "Endpoint reads req.data without addDataAndFileToRequest", "Endpoint handlers no longer resolves data , locale , or fallbackLocale for you on the request.",
  r'((pair key: (property_identifier) @k value: (arrow_function body: (_) @b)) @match (#eq? @k "handler") (#match? @b "req\\.(data|locale|fallbackLocale|file)\\b") (#not-match? @b "addDataAndFileToRequest|addLocalesToRequest"))',
  "const endpoints = [{ path: '/x', method: 'post', handler: async (req) => Response.json({ name: req.data.name }) }]\n",
  "const ep = { path: '/x', method: 'post', handler: async (req) => {\n  await addDataAndFileToRequest(req)\n  return Response.json({ name: req.data.name })\n} }\n",
  "Call addDataAndFileToRequest / addLocalesToRequest first (or req.json()).", kind="migration", cat="correctness", filters=[r"file.has_re:endpoints|PayloadHandler|Endpoint"])
M("USE-TITLE", "useTitle removed", "The useTitle hook has been consolidated into the useDocumentInfo hook.", imp("payload|@payloadcms/ui", "useTitle"),
  "import { useTitle } from 'payload'\n", "import { useDocumentInfo } from '@payloadcms/ui'\n", "Read title from useDocumentInfo (useDocumentTitle in v4).", sev="critical")
M("DOCUMENT-INFO-COLLECTION", "useDocumentInfo().collection/global", "The useDocumentInfo hook no longer returns collection or global .",
  destr("useDocumentInfo", "collection|global"), "const { collection, global } = useDocumentInfo()\n", "const { collectionSlug, globalSlug } = useDocumentInfo()\n",
  "Use collectionSlug/globalSlug.")
M("USE-CONFIG-SHAPE", "const config = useConfig()", "The useConfig hook now returns a ClientConfig and not a SanitizedConfig .",
  r'((variable_declarator name: (identifier) value: (call_expression function: (identifier) @f)) @match (#eq? @f "useConfig"))',
  "import { useConfig } from '@payloadcms/ui'\nconst config = useConfig()\n", "import { useConfig } from '@payloadcms/ui'\nconst { config } = useConfig()\n", "Destructure { config } (a ClientConfig without server-only props).", kind="migration",
  filters=[r"file.has_re:@payloadcms/ui|from ['\"]payload"])
M("USE-COLLAPSIBLE-NAMES", "useCollapsible collapsed/withinCollapsible", "collapsed is now isCollapsed and withinCollapsible is now isWithinCollapsible",
  destr("useCollapsible", "collapsed|withinCollapsible"), "const { collapsed, withinCollapsible } = useCollapsible()\n",
  "const { isCollapsed, isWithinCollapsible } = useCollapsible()\n", "Use the is* names.")
M("USE-TRANSLATION-NAMESPACE", "useTranslation('ns') argument", "The useTranslation hook no longer takes any options",
  r'((call_expression function: (identifier) @f arguments: (arguments (_))) @match (#eq? @f "useTranslation"))',
  "import { useTranslation } from '@payloadcms/ui'\nconst { t } = useTranslation('general')\n", "import { useTranslation } from '@payloadcms/ui'\nconst { t } = useTranslation()\n",
  "Call useTranslation() and use 'group:key'.", filters=[r"file.has_re:@payloadcms/ui|from ['\"]payload"])
M("RENAMED-TYPES-V3", "Fields / BlockField types renamed", "The Fields type was renamed to FormState for improved semantics.",
  imp("payload|payload/types", "Fields|BlockField|BlockFieldProps"), "import type { Fields, BlockField } from 'payload'\n",
  "import type { FormState, BlocksField } from 'payload'\n", "Use FormState / BlocksField.")
M("EMAIL-TRANSPORT-CONFIG", "email: { transport } config (use an adapter)", "Email functionality has been abstracted out into email adapters.",
  r'((pair key: (property_identifier) @k value: (object (pair key: (property_identifier) @t))) @match (#eq? @k "email") (#match? @t "^(transport|transportOptions|fromName|fromAddress)$"))',
  "export default buildConfig({\n  email: { transport, fromName: 'hello', fromAddress: 'hello@example.com' },\n})\n",
  "export default buildConfig({\n  email: nodemailerAdapter({ transport, defaultFromName: 'hello', defaultFromAddress: 'hello@example.com' }),\n})\n",
  "Use @payloadcms/email-nodemailer or email-resend.", sev="critical")
M("PLUGIN-DEFAULT-IMPORT", "Default import of a @payloadcms plugin", "All plugins have been standardized to use named exports (as opposed to default exports).",
  r'((import_statement (import_clause . (identifier)) source: (string (string_fragment) @s)) @match (#match? @s "^@payloadcms/plugin-"))',
  "import seo from '@payloadcms/plugin-seo'\n", "import { seoPlugin } from '@payloadcms/plugin-seo'\n", "Use the named *Plugin export.", sev="critical")
M("CLOUD-STORAGE-ADAPTER-IMPORT", "@payloadcms/plugin-cloud-storage/<adapter>", "The adapters that are exported from @payloadcms/plugin-cloud-storage (ie. @payloadcms/plugin-cloud-storage/s3 ) package have been removed.",
  src("@payloadcms/plugin-cloud-storage/(s3|azure|gcs|vercelBlob|vercel-blob)"), "import { s3Adapter } from '@payloadcms/plugin-cloud-storage/s3'\n",
  "import { s3Storage } from '@payloadcms/storage-s3'\n", "Use the dedicated @payloadcms/storage-* package.", sev="critical")
M("PLUGIN-CLOUD", "@payloadcms/plugin-cloud", "For Payload Cloud users, the plugin has changed.", src("@payloadcms/plugin-cloud"),
  "import { payloadCloud } from '@payloadcms/plugin-cloud'\n", "import { payloadCloudPlugin } from '@payloadcms/payload-cloud'\n", "Use @payloadcms/payload-cloud.",
  sev="critical")
M("RESERVED-FIELD-NAME", "Reserved field name", "Payload reserves certain field names for internal use.",
  r'((object (pair key: (property_identifier) @n value: (string (string_fragment) @v)) (pair key: (property_identifier) @t)) @match (#eq? @n "name") (#match? @v "^(file|_id|__v|_order|_path|_uuid|_parent_id|_locale)$") (#eq? @t "type"))',
  "import type { Field } from 'payload'\nconst fields = [{ name: 'file', type: 'text' }]\n", "const fields = [{ name: 'attachmentName', type: 'text' }]\n",
  "Reserved names are sanitized out of the config; rename the field.", kind="anti-pattern", cat="correctness", filters=[r"file.has_re:payload"])
M("AUTH-RESERVED-FIELD-NAME", "Field name reserved by auth/upload collections", "If any of these names are found in your collection / global fields, update them before migrating",
  r'((object (pair key: (property_identifier) @n value: (string (string_fragment) @v)) (pair key: (property_identifier) @t)) @match (#eq? @n "name") (#match? @v "^(salt|hash|apiKey|useAPIKey|resetPasswordToken|resetPasswordExpiration|password|filename|mimetype|filesize|focalX|focalY|thumbnailURL|sizes)$") (#eq? @t "type"))',
  "export const Users = {\n  slug: 'users',\n  auth: true,\n  fields: [{ name: 'hash', type: 'text' }],\n}\n",
  "export const Users = {\n  slug: 'users',\n  auth: true,\n  fields: [{ name: 'contentHash', type: 'text' }],\n}\n",
  "Clashes with auth/upload internal fields.", kind="anti-pattern", cat="correctness", filters=[r"file.has_re:\b(auth|upload)\s*:"],
  mode="ai-confirm", ai="Is this field in an auth-enabled (or upload-enabled for upload names) collection?")

# ======================================================================== 3.x best practices / security
P("HARDCODED-SECRET", "Hardcoded Payload secret", D + "configuration/overview", "A secure, unguessable string that Payload will use for any encryption workflows",
  r'((call_expression function: (identifier) @f arguments: (arguments (object (pair key: (property_identifier) @k value: [(string) (template_string)]) @match))) (#eq? @f "buildConfig") (#eq? @k "secret"))',
  "export default buildConfig({\n  secret: 'my-secret',\n})\n", "export default buildConfig({\n  secret: process.env.PAYLOAD_SECRET,\n})\n",
  "Load the secret from the environment; a committed secret lets anyone forge tokens.", sev="critical", kind="security", cat="security", applies={"payload": "*"})
P("LOCAL-API-USER-WITHOUT-OVERRIDE", "Local API call passes user but not overrideAccess:false", D + "local-api/access-control",
  "you need to explicitly pass the user object and set the overrideAccess option to false",
  local_call(' (#match? @a "\\\\buser\\\\s*[:,}]") (#not-match? @a "overrideAccess")'),
  "const posts = await payload.find({ collection: 'posts', user })\n", "const posts = await payload.find({ collection: 'posts', user, overrideAccess: false })\n",
  "In Payload 3 the Local API skips access control by default — passing user alone does not enforce it.", sev="critical", kind="security", cat="security",
  applies=PRE4)
P("LOCAL-API-REQUEST-CONTEXT", "Local API in a request/server-action without access control", D + "access-control/overview",
  "In the Local API , all Access Control is skipped by default.", local_call(' (#not-match? @a "overrideAccess")'),
  "'use server'\nexport async function deletePost(id) {\n  await payload.delete({ collection: 'posts', id })\n}\n",
  "'use server'\nexport async function deletePost(id, user) {\n  await payload.delete({ collection: 'posts', id, user, overrideAccess: false })\n}\n",
  "Code acting for a user must enforce access (overrideAccess:false + user).", sev="major", kind="security", cat="security", applies=PRE4,
  filters=[r"file.has_re:['\"]use server['\"]|export\s+(async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE)\b|NextRequest"],
  mode="ai-confirm", ai="Does this Local API call act on behalf of an end user (route handler / server action / page), not a trusted job or seed script?")
P("HOOK-WITHOUT-REQ", "Local API in a hook without passing req (transaction)", D + "database/transactions",
  "you can opt in to using the same transaction by passing the req in the arguments.",
  local_call(' (#not-match? @a "\\\\breq\\\\b")'),
  "const afterChange = async ({ doc, req }) => {\n  await req.payload.update({ collection: 'items', id: doc.item, data: { stock: 1 } })\n}\n",
  "const afterChange = async ({ doc, req }) => {\n  await req.payload.update({ collection: 'items', id: doc.item, data: { stock: 1 }, req })\n}\n",
  "Without req the write runs outside the request transaction (no rollback, possible deadlocks).", sev="major", kind="anti-pattern", cat="correctness",
  applies=V3, filters=[r"file.has_re:\b(before|after)(Change|Delete|Validate|Read|Operation|Login)\b"])
P("AFTERCHANGE-SELF-UPDATE", "afterChange updating its own collection (infinite loop)", D + "hooks/context",
  "Calling payload.update() on the same document that triggered an afterChange hook will create an infinite loop",
  r'((pair key: (property_identifier) @k value: (array (_ body: (_) @b))) @match (#eq? @k "afterChange") (#match? @b "\\.update\\s*\\(") (#not-match? @b "context"))',
  "export const Customers = {\n  slug: 'customers',\n  hooks: { afterChange: [async ({ doc, req }) => { await req.payload.update({ collection: 'customers', id: doc.id, data: {}, req }) }] },\n}\n",
  "export const Customers = {\n  slug: 'customers',\n  hooks: { afterChange: [async ({ doc, req, context }) => { if (context.skip) return; await req.payload.update({ collection: 'customers', id: doc.id, data: {}, req, context: { skip: true } }) }] },\n}\n",
  "Guard with req.context (pass context: { skipHook: true }) or use beforeChange.", sev="critical", kind="anti-pattern", cat="correctness",
  mode="ai-confirm", ai="Does this afterChange update the same collection/document that triggered it without a context guard?")
P("OPEN-WRITE-ACCESS", "create/update/delete access always true", D + "access-control/overview",
  "Payload provides default Access Control so that your data is secured behind Authentication without additional configuration.",
  r'((pair key: (property_identifier) @a value: (object (pair key: (property_identifier) @k value: (arrow_function body: (true))) @match)) (#eq? @a "access") (#match? @k "^(create|update|delete|unlock|admin|readVersions)$"))',
  "export const Posts = {\n  slug: 'posts',\n  access: { update: () => true },\n}\n", "export const Posts = {\n  slug: 'posts',\n  access: { update: ({ req: { user } }) => Boolean(user) },\n}\n",
  "Anyone (unauthenticated) can modify data; replacing the default Boolean(user) check removes protection.", sev="critical", kind="security", cat="security",
  applies={"payload": "*"}, mode="ai-confirm", ai="Is anonymous write intended here (e.g. public form submissions with field-level protections)?")
P("NEXT-PUBLIC-SECRET", "Secret-looking NEXT_PUBLIC_ variable", D + "configuration/environment-vars",
  "Be careful about what variables you provide to your client-side code.",
  r'((member_expression object: (member_expression object: (identifier) @p property: (property_identifier) @e) property: (property_identifier) @v) @match (#eq? @p "process") (#eq? @e "env") (#match? @v "^NEXT_PUBLIC_.*(SECRET|PRIVATE|PASSWORD|TOKEN|API_KEY|SERVICE_ROLE)"))',
  "const k = process.env.NEXT_PUBLIC_STRIPE_SECRET_KEY\n", "const k = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY\n",
  "NEXT_PUBLIC_ values are inlined into the client bundle.", sev="critical", kind="security", cat="security", applies={"payload": "*"},
  quote="Important: Be careful about what variables you provide to your client-side code. Analyze every single one to make sure that you're not accidentally leaking sensitive information")
P("UPLOAD-NO-MIME-TYPES", "Upload collection without mimeTypes", D + "upload/overview", "Restrict mimeTypes in the file picker.",
  r'((pair key: (property_identifier) @k value: (object) @o) @match (#eq? @k "upload") (#not-match? @o "mimeTypes"))',
  "export const Media = {\n  slug: 'media',\n  upload: { staticDir: dir },\n}\n", "export const Media = {\n  slug: 'media',\n  upload: { staticDir: dir, mimeTypes: ['image/*', 'application/pdf'] },\n}\n",
  "Accepting any file type invites stored-XSS (SVG/HTML) and abuse.", sev="minor", kind="security", cat="security", applies={"payload": "*"},
  filters=[r"file.has_re:slug\s*:"])
P("GRAPHQL-UNUSED", "GraphQL enabled but unused", D + "production/preventing-abuse", "not need GraphQL it is advised that you disable it altogether",
  r'((call_expression function: (identifier) @f arguments: (arguments (object) @o)) @match (#eq? @f "buildConfig") (#not-match? @o "graphQL"))',
  "export default buildConfig({\n  collections: [Posts],\n})\n", "export default buildConfig({\n  collections: [Posts],\n  graphQL: { disable: true },\n})\n",
  "Disable unused GraphQL to shrink attack surface and startup cost.", sev="info", kind="best-practice", cat="security", applies={"payload": "*"},
  mode="ai-confirm", ai="Does the project not use the GraphQL API (no /api/graphql clients, no graphql codegen)?",
  quote="If you do not need GraphQL it is advised that you disable it altogether with the Payload Config by setting graphQL.disable: true .")

# ======================================================================== 3.x → 4.0
M("OVERRIDE-ACCESS-DEFAULT", "Trusted Local API call relying on overrideAccess default", "now defaults to `false` on Local API operations",
  local_call(' (#not-match? @a "overrideAccess|\\\\buser\\\\b")'), "// seed script\nawait payload.find({ collection: 'posts' })\n",
  "// seed script\nawait payload.find({ collection: 'posts', overrideAccess: true })\n",
  "In v4 omitted overrideAccess enforces access control (no user = anonymous); trusted jobs/seeds must pass overrideAccess: true.", v=4,
  kind="migration", cat="correctness", filters=[r"file.has_re:(?i)seed|migrat|cron|job|script|task"], mode="ai-confirm",
  ai="Is this trusted server-side code (seed, migration, job, cron) that previously relied on bypassing access control?")
M("CONFIG-BIN", "config.bin (now cli.commands)", "API has been removed. Custom commands are now registered through", key("bin"),
  "export default buildConfig({\n  bin: [{ key: 'seed', scriptPath: './seed.ts' }],\n})\n", "export default buildConfig({\n  cli: { commands: { seed: './seed.js#seedCommand' } },\n})\n",
  "Define commands with defineCLICommand and register under cli.commands.", v=4, sev="critical", filters=[r"file.has_re:buildConfig"])
M("MIGRATE-CLI", "migrateCLI export removed", "export has been removed.", imp("payload", "migrateCLI"), "import { migrateCLI } from 'payload'\n",
  "await payload.db.migrate()\n", "Call payload.db.migrate*() or payload.bin().", v=4, sev="critical")
M("VERSIONS-DEFAULT", "Collection without explicit versions (now on by default)", "Collections and globals now have `versions: true` by default",
  r'((object (pair key: (property_identifier) @s) (pair key: (property_identifier) @f)) @match (#eq? @s "slug") (#eq? @f "fields") (#not-match? @match "\\bversions\\s*:"))',
  "export const Posts: CollectionConfig = {\n  slug: 'posts',\n  fields: [],\n}\n", "export const Posts: CollectionConfig = {\n  slug: 'posts',\n  fields: [],\n  versions: false,\n}\n",
  "v4 creates _<slug>_versions tables for every collection; set versions explicitly and run a migration.", v=4, kind="migration", sev="minor",
  filters=[r"file.has_re:CollectionConfig|GlobalConfig"])
M("AUTH-COLLECTION-VERSIONS", "Auth collection without versions: false", "you should do the same for any custom auth collection",
  r'((object (pair key: (property_identifier) @a) (pair key: (property_identifier) @f)) @match (#eq? @a "auth") (#eq? @f "fields") (#not-match? @match "\\bversions\\s*:"))',
  "export const Users: CollectionConfig = {\n  slug: 'users',\n  auth: true,\n  fields: [],\n}\n",
  "export const Users: CollectionConfig = {\n  slug: 'users',\n  auth: true,\n  fields: [],\n  versions: false,\n}\n",
  "Versioning auth collections stores password hashes/tokens history.", v=4, kind="security", cat="security")
M("VERSIONS-TRUE-REDUNDANT", "versions: true (default in v4)", "The bare `versions: true` you may have added previously is now redundant and can be removed.",
  r'((pair key: (property_identifier) @k value: (true)) @match (#eq? @k "versions"))', "export const Posts = {\n  slug: 'posts',\n  versions: true,\n  fields: [],\n}\n",
  "export const Posts = {\n  slug: 'posts',\n  fields: [],\n}\n", "Remove it.", v=4, kind="modernization", sev="info", cat="maintainability")
M("PUBLIC-READ-VERSIONS", "Public read without readVersions (versions become public)", "version access now inherits the Collection or Global",
  r'((pair key: (property_identifier) @a value: (object (pair key: (property_identifier) @r value: (arrow_function body: (true)))) @o) @match (#eq? @a "access") (#eq? @r "read") (#not-match? @o "readVersions"))',
  "export const Posts = {\n  slug: 'posts',\n  access: { read: () => true },\n  fields: [],\n}\n",
  "export const Posts = {\n  slug: 'posts',\n  access: { read: () => true, readVersions: ({ req: { user } }) => Boolean(user) },\n  fields: [],\n}\n",
  "In v4 drafts/old versions inherit public read; add readVersions.", v=4, kind="security", cat="security", sev="critical")
M("ENABLE-LIST-VIEW-SELECT-API", "admin.enableListViewSelectAPI removed", "Collection Config property has been removed.", key("enableListViewSelectAPI"),
  "export const Posts = {\n  slug: 'posts',\n  admin: { enableListViewSelectAPI: true },\n}\n", "export const Posts = {\n  slug: 'posts',\n  admin: {},\n}\n", "Remove it.", v=4, sev="minor")
M("GLOBAL-COMPONENTS-ELEMENTS", "Global admin.components.elements (now edit)", "The Edit View slot container is renamed from", key("elements", "components"),
  "export const Header: GlobalConfig = {\n  slug: 'header',\n  admin: { components: { elements: { SaveButton: '/Save' } } },\n}\n",
  "export const Header: GlobalConfig = {\n  slug: 'header',\n  admin: { components: { edit: { SaveButton: '/Save' } } },\n}\n", "Rename to edit (Description moves up).", v=4)
M("FORCE-SELECT", "forceSelect removed (select function)", "The static `forceSelect` config has been removed.", key("forceSelect"),
  "export const Posts = {\n  slug: 'posts',\n  forceSelect: { title: true },\n}\n",
  "export const Posts = {\n  slug: 'posts',\n  select: ({ select }) => (select ? { ...select, title: true } : undefined),\n}\n", "Use the select function (codemod migrate-force-select).", v=4,
  sev="critical")
M("HIDE-API-URL", "admin.hideAPIURL removed", "has been removed from Collections and Globals.", key("hideAPIURL", "admin"),
  "export const Posts = {\n  slug: 'posts',\n  admin: { hideAPIURL: true },\n}\n",
  "export const Posts = {\n  slug: 'posts',\n  admin: { components: { views: { edit: { api: { tab: { condition: () => false } } } } } },\n}\n", "Use the api tab condition.", v=4)
M("UI-ALIASED-REEXPORTS", "Aliased re-exports from @payloadcms/ui / next/utilities", "for backwards compatibility have been removed.",
  imp("@payloadcms/ui|@payloadcms/ui/shared|@payloadcms/next/utilities",
      "Column|ListViewSlots|ListViewClientProps|EntityType|formatAdminURL|mergeListSearchAndWhere|mergeHeaders|headersWithCors|createPayloadRequest|addDataAndFileToRequest|sanitizeLocales|addLocalesToRequestFromData"),
  "import { addDataAndFileToRequest } from '@payloadcms/next/utilities'\n", "import { addDataAndFileToRequest } from 'payload'\n",
  "Import from payload / payload/shared.", v=4, sev="critical")
M("NEXT-ROUTER-IN-ADMIN", "next/navigation or next/link in admin components", "no longer depends on `next` directly.",
  imp("next/navigation", "useRouter|usePathname|useSearchParams|useParams") + "\n"
  + r'((import_statement source: (string (string_fragment) @s)) @match (#eq? @s "next/link"))',
  "import { useRouter } from 'next/navigation'\nimport { useField } from '@payloadcms/ui'\n", "import { useRouter, useField } from '@payloadcms/ui'\n",
  "Use the framework-agnostic hooks / PayloadLink from @payloadcms/ui.", v=4, kind="migration", filters=[r"file.has_re:@payloadcms/ui"])
M("NEXT-SUBPATH-EXPORTS", "@payloadcms/next/client|rsc|templates imports", "subpath exports on `@payloadcms/next` were thin re-exports",
  src("@payloadcms/next/(client|rsc|templates)"), "import { DefaultTemplate } from '@payloadcms/next/templates'\n", "import { DefaultTemplate } from '@payloadcms/ui/rsc'\n",
  "Import from @payloadcms/ui or @payloadcms/ui/rsc.", v=4, sev="critical")
M("DOCUMENT-TITLE-HOOK", "title/setDocumentTitle from useDocumentInfo", "Access it through the `useDocumentTitle` hook",
  destr("useDocumentInfo", "title|setDocumentTitle"), "const { title, setDocumentTitle } = useDocumentInfo()\n", "const { title, setDocumentTitle } = useDocumentTitle()\n",
  "Use useDocumentTitle().", v=4, sev="critical")
M("USE-FIELD-READONLY", "readOnly from useField", "const { readOnly, value } = useField({ path })", destr("useField", "readOnly"),
  "const { value, readOnly } = useField({ path })\n", "const { value } = useField({ path })\nconst readOnly = props.readOnly\n", "Read readOnly from props.", v=4)
M("AFTER-OPERATION-READ", "afterOperation checking operation === 'read'", "Collection after-operation hooks no longer report read operations",
  r'((binary_expression left: (identifier) @o right: (string (string_fragment) @v)) @match (#eq? @o "operation") (#eq? @v "read"))',
  "// afterOperation\nconst hook = ({ operation, result }) => {\n  if (operation === 'read') log(result)\n}\n", "const hook = ({ operation, result }) => {\n  if (operation === 'find' || operation === 'findByID') log(result)\n}\n",
  "Check 'find' / 'findByID' (beforeOperation still uses 'read').", v=4, filters=[r"file.has_re:afterOperation"])
M("RICHTEXT-SLATE", "@payloadcms/richtext-slate removed", "package has been deleted and will no longer be published.", src("@payloadcms/richtext-slate"),
  "import { slateEditor } from '@payloadcms/richtext-slate'\n", "import { lexicalEditor } from '@payloadcms/richtext-lexical'\n",
  "Migrate to Lexical on 3.x before upgrading.", v=4, sev="critical")
M("LEXICAL-HTML-CONVERTER", "HTMLConverterFeature / lexicalHTML removed", "Use `convertLexicalToHTML` and `lexicalHTMLField` from the non-deprecated converter instead.",
  imp("@payloadcms/richtext-lexical", "HTMLConverterFeature|lexicalHTML"), "import { HTMLConverterFeature, lexicalHTML } from '@payloadcms/richtext-lexical'\n",
  "import { lexicalHTMLField } from '@payloadcms/richtext-lexical'\n", "Use convertLexicalToHTML / lexicalHTMLField.", v=4, sev="critical")
M("TYPESCRIPT-SCHEMA", "field typescriptSchema (now jsonSchema)", "renamed to `jsonSchema`", key("typescriptSchema"),
  "const f = { name: 'meta', type: 'json', typescriptSchema: [() => schema] }\n", "const f = { name: 'meta', type: 'json', jsonSchema: schema }\n",
  "Use jsonSchema.", v=4, quote="accepted JSON Schema, not TypeScript, so the name lied. Renamed to")
M("RENAMED-TYPES-V4", "Renamed/removed v4 types", "exports have been renamed to `TaskSlug` and `WorkflowSlug`.",
  imp("payload|@payloadcms/richtext-lexical|@payloadcms/ui",
      "TaskType|WorkflowTypes|RunningJob|RunningJobSimple|LexicalEditorProps|UploadDataImproved|FileSizeImproved|SharpDependency|ImageUploadFormatOptions|ImageUploadTrimOptions|SharpImageSizeOptions|baseAPIKeyFields"),
  "import type { TaskType, WorkflowTypes } from 'payload'\n", "import type { TaskSlug, WorkflowSlug } from 'payload'\n",
  "Use TaskSlug/WorkflowSlug, Job, LexicalEditorArgs, UploadData, FileSize, createAPIKeyFields(), @payloadcms/transformer-sharp types.", v=4, sev="critical")
M("CRON-SLOPPY-RANGE", "Cron step without range (n/m)", "stepping expressions must use either `*` or an explicit range before the `/`.",
  r'((pair key: (property_identifier) @k value: (string (string_fragment) @v)) @match (#eq? @k "cron") (#match? @v "(^|\\s)[0-9]+/[0-9]+"))',
  "const autoRun = [{ cron: '5/10 * * * *', queue: 'default' }]\n", "const autoRun = [{ cron: '5-59/10 * * * *', queue: 'default' }]\n",
  "Croner strict mode rejects 'n/m'; use '*/m' or 'a-b/m'.", v=4, sev="critical")
M("STORAGE-IN-PLUGINS", "Storage adapter inside plugins", "must now be placed under the top-level `storage` key",
  r'((pair key: (property_identifier) @k value: (array (call_expression function: (identifier) @f) @match)) (#eq? @k "plugins") (#match? @f "^(s3Storage|azureStorage|gcsStorage|r2Storage|vercelBlobStorage)$"))',
  "export default buildConfig({\n  plugins: [s3Storage({ collections: { media: true }, bucket })],\n})\n",
  "export default buildConfig({\n  storage: [s3Storage({ collections: { media: true }, bucket })],\n})\n", "Move adapters to the storage key.", v=4, sev="critical",
  quote="Storage adapter packages (`@payloadcms/storage-s3`, `-azure`, `-gcs`, `-r2`, `-vercel-blob`) must now be placed under the top-level `storage` key in your Payload config instead of inside `plugins`.")
M("UPLOADTHING-REMOVED", "@payloadcms/storage-uploadthing removed", "The Uploadthing storage adapter, deprecated in a previous release, has been deleted",
  src("@payloadcms/storage-uploadthing"), "import { uploadthingStorage } from '@payloadcms/storage-uploadthing'\n", "import { s3Storage } from '@payloadcms/storage-s3'\n",
  "Migrate to another adapter before upgrading.", v=4, sev="critical")
M("SHARP-CONFIG", "sharp / imageSizes / resizeOptions in core config", "The top-level `sharp` config property has been removed.",
  r'((call_expression function: (identifier) @f arguments: (arguments (object [(pair key: (property_identifier) @k) (shorthand_property_identifier) @k] @match))) (#eq? @f "buildConfig") (#eq? @k "sharp"))' + "\n"
  + key("imageSizes|resizeOptions|formatOptions|trimOptions|constructorOptions|withMetadata", "upload"),
  "export default buildConfig({\n  sharp,\n})\n", "export default buildConfig({\n  upload: { transformers: [sharpTransformer({ sharp })] },\n})\n",
  "Use @payloadcms/transformer-sharp (variants replace imageSizes).", v=4, sev="critical")
M("DEFAULT-DEPTH", "Relies on depth 2 population", "Queries that omit `depth` now populate one relationship level instead of two.",
  local_call(' (#match? @m "^(find|findByID|findGlobal)$") (#not-match? @a "\\\\bdepth\\\\b")'),
  "const post = await payload.findByID({ collection: 'posts', id, overrideAccess: true })\nconsole.log(post.author.avatar.url)\n",
  "const post = await payload.findByID({ collection: 'posts', id, overrideAccess: true, depth: 2 })\nconsole.log(post.author.avatar.url)\n",
  "Default depth is 1 in v4; pass depth where nested relations are read (or defaultDepth: 2).", v=4, kind="migration", sev="minor", cat="correctness",
  mode="ai-confirm", ai="Does code using this result access relationships two levels deep (e.g. doc.rel.rel.field)?")
M("VALIDATE-OPERATION-SIDE-EFFECT", "beforeChange side effects run on validate operation", "On-demand validation runs these hooks without saving the candidate.",
  r'((pair key: (property_identifier) @k value: (array (_ body: (_) @b))) @match (#match? @k "^(beforeChange|beforeValidate)$") (#match? @b "await\\s+\\w+") (#not-match? @b "validate"))',
  "export const Customers = {\n  slug: 'customers',\n  hooks: { beforeChange: [async ({ data }) => { await syncCustomerWithStripe(data); return data }] },\n}\n",
  "export const Customers = {\n  slug: 'customers',\n  hooks: { beforeChange: [async ({ data, operation }) => { if (operation === 'validate') return data; await syncCustomerWithStripe(data); return data }] },\n}\n",
  "v4 runs beforeChange for on-demand validation; skip external side effects when operation === 'validate'.", v=4, kind="migration", cat="correctness",
  mode="ai-confirm", ai="Does the awaited call have external side effects (API calls, emails, writes) that must not run during validation?")

# ======================================================================== official Payload skill checklist (payloadcms/payload, MIT):
# packages/payload/skills/payload/{SKILL.md,reference/*.md}. Detection and wording are ours; each rule cites the payloadcms.com page.
ANY = {"payload": "*"}
P("ENDPOINT-NO-AUTH", "Custom endpoint handler never checks the caller", D + "rest-api/overview",
  "Custom endpoints are not authenticated by default",
  r'((pair key: (property_identifier) @e value: (array (object (pair key: (property_identifier) @h value: [(arrow_function) (function_expression)] @fn)) @match)) (#eq? @e "endpoints") (#eq? @h "handler") (#not-match? @fn "user|access|auth|apiKey|api_key|secret|signature|token|verify|headers|overrideAccess:\\s*false"))',
  "export const Orders = {\n  slug: 'orders',\n  endpoints: [{ path: '/:id/refund', method: 'post', handler: async (req) => {\n    await req.payload.update({ collection: 'orders', id: req.routeParams.id, data: { refunded: true } })\n    return Response.json({ ok: true })\n  } }],\n}\n",
  "export const Orders = {\n  slug: 'orders',\n  endpoints: [{ path: '/:id/refund', method: 'post', handler: async (req) => {\n    if (!req.user) return Response.json({ error: 'forbidden' }, { status: 403 })\n    await req.payload.update({ collection: 'orders', id: req.routeParams.id, data: { refunded: true }, user: req.user, overrideAccess: false, req })\n    return Response.json({ ok: true })\n  } }],\n}\n",
  "Payload does not authenticate custom endpoints. Check req.user (or a signature/API key) before doing work, and run Local API calls with the user and overrideAccess: false.",
  sev="critical", kind="security", cat="security", applies=V3, mode="ai-confirm",
  ai="Does this endpoint read non-public data or change state without any authentication/authorization check (it is not a deliberately public endpoint like a health check)?")
P("CORS-WILDCARD", "Payload cors: '*' accepts every origin", D + "configuration/overview", "to accept incoming requests from any domain",
  r'((pair key: (property_identifier) @k value: (string (string_fragment) @v)) @match (#match? @k "^(cors|origins)$") (#eq? @v "*"))',
  "export default buildConfig({\n  cors: '*',\n  collections: [Posts],\n})\n", "export default buildConfig({\n  cors: [process.env.FRONTEND_URL],\n  collections: [Posts],\n})\n",
  "Every website can call this API from a browser. List the frontends that need access (and set csrf for cookie auth).",
  sev="major", kind="security", cat="security", applies=ANY, mode="ai-confirm", filters=[r"file.has_re:buildConfig"],
  ai="Does this API serve authenticated or non-public data (rather than being a fully public, read-only content API)?")
P("VALIDATE-RETURNS-FALSE", "Field validate returns false (passes silently)", D + "fields/overview",
  "Custom validation functions should return either true or a string representing the error message",
  r'((pair key: (property_identifier) @k value: [(arrow_function) (function_expression)] @match) (#eq? @k "validate") (#match? @match "return\\s+false\\b|=>\\s*false\\s*[,}\\n]|=>\\s*false$|\\|\\|\\s*false\\b|\\?\\s*true\\s*:\\s*false\\b"))',
  "const field = {\n  name: 'sku',\n  type: 'text',\n  validate: (value) => /^[A-Z0-9-]+$/.test(value) || false,\n}\n",
  "const field = {\n  name: 'sku',\n  type: 'text',\n  validate: (value) => /^[A-Z0-9-]+$/.test(value) || 'SKU may only contain A-Z, 0-9 and -',\n}\n",
  "Payload treats only a returned string as an error, so false lets the invalid value through on the server. Return an error message string instead.",
  sev="critical", kind="anti-pattern", cat="correctness", applies=V3)
P("FIELD-ACCESS-QUERY", "Field access function returns a query object", D + "access-control/fields",
  "Field Access Control does not support returning Query constraints like Collection Access Control does",
  r'((object (pair key: (property_identifier) @t) (pair key: (property_identifier) @a value: (object (pair value: [(arrow_function) (function_expression)] @match)))) (#eq? @t "type") (#eq? @a "access") (#match? @match "=>\\s*\\(\\s*\\{|return\\s*\\{"))',
  "const salary = {\n  name: 'salary',\n  type: 'number',\n  access: { read: ({ req }) => ({ owner: { equals: req.user?.id } }) },\n}\n",
  "const salary = {\n  name: 'salary',\n  type: 'number',\n  access: { read: ({ req, doc }) => Boolean(req.user && doc?.owner === req.user.id) },\n}\n",
  "Field access must return a boolean. A Where object is truthy, so this grants access to everyone instead of filtering. Compare against doc/siblingData and return true/false.",
  sev="critical", kind="security", cat="security", applies=ANY)
P("PAGINATION-FALSE-NO-LIMIT", "find with pagination: false and no limit loads every document", D + "queries/pagination",
  "If you do not specify a limit , Payload returns all matching documents",
  local_call(' (#eq? @m "find") (#match? @a "pagination\\\\s*:\\\\s*false") (#not-match? @a "\\\\blimit\\\\b")'),
  "const all = await payload.find({ collection: 'orders', pagination: false, overrideAccess: true })\n",
  "const page = await payload.find({ collection: 'orders', pagination: false, limit: 500, overrideAccess: true })\n",
  "With pagination off and no limit, the query returns the whole collection into memory. Set a limit or page through results.",
  sev="minor", kind="best-practice", cat="performance", applies=V3, mode="ai-confirm",
  ai="Can this collection grow large (user content, orders, logs) so loading every matching document is a real cost?",
  quote="If you do not specify a limit , Payload returns all matching documents.")
P("LOGIN-LOCKOUT-DISABLED", "Auth collection disables login lockout (maxLoginAttempts: 0)", D + "production/preventing-abuse",
  "Set the max number of failed login attempts before a user account is locked out",
  r'((pair key: (property_identifier) @k value: (number) @v) @match (#eq? @k "maxLoginAttempts") (#eq? @v "0"))',
  "export const Users = {\n  slug: 'users',\n  auth: { maxLoginAttempts: 0 },\n  fields: [],\n}\n",
  "export const Users = {\n  slug: 'users',\n  auth: { maxLoginAttempts: 5, lockTime: 600 * 1000 },\n  fields: [],\n}\n",
  "0 turns off account lockout, leaving password guessing unthrottled. Use a small number with a lockTime.",
  sev="major", kind="security", cat="security", applies=ANY)
P("TRANSACTION-NOT-FINISHED", "beginTransaction without commit/rollback in the same function", D + "database/transactions",
  "payload.db.commitTransaction - Takes the identifier for the transaction, finalizes any changes",
  r'((call_expression function: (member_expression object: (member_expression property: (property_identifier) @db) property: (property_identifier) @m)) @match (#eq? @db "db") (#eq? @m "beginTransaction"))',
  "async function transfer(payload, a, b) {\n  const transactionID = await payload.db.beginTransaction()\n  const req = { transactionID }\n  await payload.update({ collection: 'accounts', id: a, data: { balance: 0 }, req })\n}\n",
  "async function transfer(payload, a, b) {\n  const transactionID = await payload.db.beginTransaction()\n  const req = { transactionID }\n  try {\n    await payload.update({ collection: 'accounts', id: a, data: { balance: 0 }, req })\n    await payload.db.commitTransaction(transactionID)\n  } catch (e) {\n    await payload.db.rollbackTransaction(transactionID)\n    throw e\n  }\n}\n",
  "A started transaction must be committed on success and rolled back on failure, or it holds a session/locks and the writes never land. Wrap the work in try/catch with commitTransaction and rollbackTransaction.",
  sev="major", kind="anti-pattern", cat="correctness", applies=V3, mode="ai-confirm", filters=["func.lacks_re:commitTransaction[\\s\\S]*rollbackTransaction|rollbackTransaction[\\s\\S]*commitTransaction"],
  ai="Is the transaction ID not handed to a caller/helper that commits or rolls it back?")

RULES = P.R

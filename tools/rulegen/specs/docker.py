"""Docker pack: Dockerfile (Docker build checks + build best practices + Dockerfile reference) and Compose files
(Compose Specification). Compose files are YAML, so the generic YAML pack also applies to them."""
from specs._common import Pack, SECRET_NAME_RE

BC = "https://docs.docker.com/reference/build-checks/"
BP = "https://docs.docker.com/build/building/best-practices/"
REF = "https://docs.docker.com/reference/dockerfile/"
SEC = "https://docs.docker.com/engine/security/"
SVC = "https://docs.docker.com/reference/compose-file/services/"
P = Pack("DOCKER", "dockerfile", "Dockerfile frontend 1.28 / Docker docs 2026-10", {"any": "*"}, files=["**/Dockerfile", "**/Dockerfile.*", "**/*.dockerfile", "**/Containerfile", "**/Containerfile.*"])


def bc(id, slug, needle, query, bad, good, msg, **kw):
    kw.setdefault("cat", "build-check")
    P(id, f"Build check {slug}", BC + slug + "/", needle, query, bad, good, msg, doc=f"Docker build check: {slug}", **kw)


bc("STAGE-NAME-CASING", "stage-name-casing", "this rule forces names of stages in a multi-stage Dockerfile to be all lowercase",
   '((image_alias) @match (#match? @match "[A-Z]"))', "FROM alpine AS BuilderBase\n", "FROM alpine AS builder-base\n",
   "Stage names should be lowercase.", sev="info")
bc("FROM-AS-CASING", "from-as-casing", "mixing case styles is not recommended for readability",
   '((from_instruction) @match (#match? @match "^FROM .* as "))\n((from_instruction) @match (#match? @match "^from .* AS "))',
   "FROM alpine as builder\n", "FROM alpine AS builder\n", "Use the same casing for FROM and AS.", sev="info")
bc("NO-EMPTY-CONTINUATION", "no-empty-continuation", "lines have been deprecated and will generate errors in future versions of the Dockerfile syntax",
   '(source_file) @match', "RUN apk add \\\n\n    curl\n", "RUN apk add \\\n    curl\n",
   "Empty continuation lines are deprecated and will become errors.", sev="minor", kind="deprecation",
   filters=[r"file.has_re:\\[ \t]*\r?\n([ \t]*\r?\n)+[ \t]*\S"])
bc("CONSISTENT-INSTRUCTION-CASING", "consistent-instruction-casing", "Instruction keywords should use consistent casing",
   '([(from_instruction) (run_instruction) (cmd_instruction) (copy_instruction) (add_instruction) (env_instruction) (arg_instruction) (entrypoint_instruction) (workdir_instruction) (user_instruction) (expose_instruction) (label_instruction)] @match (#match? @match "^([A-Z][a-z]|[a-z]+[A-Z])"))',
   "FROM alpine\nRun echo hi\n", "FROM alpine\nRUN echo hi\n", "Use all-uppercase (or all-lowercase) instruction keywords.", sev="info")
bc("DUPLICATE-STAGE-NAME", "duplicate-stage-name", "Defining multiple stages with the same name results in an error",
   '(source_file (from_instruction as: (image_alias) @first) (from_instruction as: (image_alias) @match) (#eq? @first @match))',
   "FROM alpine AS build\nFROM debian AS build\n", "FROM alpine AS build\nFROM debian AS runtime\n", "Stage names must be unique.", sev="major", cat="correctness")
bc("RESERVED-STAGE-NAME", "reserved-stage-name", "Reserved words should not be used as names for stages in multi-stage builds.",
   '((image_alias) @match (#match? @match "^(?i)(scratch|context)$"))', "FROM alpine AS scratch\n", "FROM alpine AS base\n",
   "`scratch` and `context` are reserved stage names.", sev="major", cat="correctness")
bc("JSON-ARGS-RECOMMENDED", "json-args-recommended", "ENTRYPOINT and CMD instructions both support two different syntaxes for arguments",
   '([(cmd_instruction (shell_command) @match) (entrypoint_instruction (shell_command) @match)])', "FROM node\nCMD npm start\n",
   'FROM node\nCMD ["npm", "start"]\n', "Shell form runs under /bin/sh -c: the process is not PID 1 and won't receive SIGTERM; use exec (JSON) form.",
   sev="minor", cat="best-practice", filters=["node.lacks_ancestor:healthcheck_instruction"])
bc("MAINTAINER-DEPRECATED", "maintainer-deprecated", "used historically for specifying the author of the Dockerfile, is deprecated",
   '(maintainer_instruction) @match', "FROM alpine\nMAINTAINER me@example.com\n", 'FROM alpine\nLABEL org.opencontainers.image.authors="me@example.com"\n',
   "Use the org.opencontainers.image.authors label.", sev="minor", kind="deprecation")
bc("UNDEFINED-ARG-IN-FROM", "undefined-arg-in-from", "This rule warns for cases where you're consuming an undefined build argument in FROM instructions.",
   '(from_instruction (image_spec (_ (expansion (variable) @match))))', "FROM node:${VARIANT}\n", "ARG VARIANT=22-alpine\nFROM node:${VARIANT}\n",
   "The ARG used in FROM is not declared before the first FROM.", sev="major", cat="correctness",
   filters=[r"file.count_lt:1:(?im)^\s*ARG\s+{text}\b", r"node.lacks_re:^(BUILDPLATFORM|TARGETPLATFORM|TARGETOS|TARGETARCH|TARGETVARIANT|BUILDOS|BUILDARCH|BUILDVARIANT)$"])
bc("WORKDIR-RELATIVE-PATH", "workdir-relative-path", "Using a relative path means that the working directory",
   '(workdir_instruction (path) @match (#not-match? @match "^[\\\"\']?(/|[$]|[A-Za-z]:)"))', "FROM alpine\nWORKDIR app/src\n", "FROM alpine\nWORKDIR /app/src\n",
   "Use absolute WORKDIR paths; relative ones depend on the base image's working dir.", sev="minor",
   # fixture triage (hadolint DL3000): quoted absolute, variable and Windows paths are absolute
   fp=["FROM alpine\nWORKDIR \"/srv/app\"\n", "FROM alpine\nWORKDIR \"${APP_HOME}\"\n", "FROM mcr.microsoft.com/windows/servercore\nWORKDIR 'C:\\app'\n"])
bc("MULTIPLE-CMD", "multiple-instructions-disallowed", "only the last occurrence is used",
   '[(source_file (cmd_instruction) (cmd_instruction) @match) (source_file (entrypoint_instruction) (entrypoint_instruction) @match) (source_file (healthcheck_instruction) (healthcheck_instruction) @match)]',
   'FROM alpine\nCMD ["a"]\nCMD ["b"]\n', 'FROM alpine\nCMD ["b"]\n', "Only the last CMD/ENTRYPOINT/HEALTHCHECK of a stage takes effect.",
   sev="minor", cat="correctness", filters=[r"file.count_lt:2:(?im)^\s*FROM\s"])
bc("LEGACY-KEY-VALUE-FORMAT", "legacy-key-value-format", "The correct format for declaring environment variables and build arguments",
   '((env_instruction) @match (#match? @match "(?i)^env\\\\s+[^=\\\\s]+\\\\s+[^=]"))', "FROM alpine\nENV NODE_ENV production\n", "FROM alpine\nENV NODE_ENV=production\n",
   "Use ENV key=value; the space-separated legacy form is ambiguous.", sev="minor", kind="deprecation")
bc("REDUNDANT-TARGET-PLATFORM", "redundant-target-platform", "setting the platform to $TARGETPLATFORM is redundant",
   '((from_instruction (param) @match) (#match? @match "^--platform=[$][{]?TARGETPLATFORM[}]?$"))', "FROM --platform=$TARGETPLATFORM alpine\n", "FROM alpine\n",
   "--platform=$TARGETPLATFORM is the default.", sev="info")
bc("SECRETS-USED-IN-ARG-OR-ENV", "secrets-used-in-arg-or-env", "setting secrets in a Dockerfile using ENV or ARG is insecure",
   r'([(arg_instruction name: (_) @match) (env_instruction (env_pair name: (_) @match))] (#match? @match "(?i)(^|_)(password|passwd|secret|token|api_?key|access_?key|private_?key|credentials?)($|_)"))',
   "FROM alpine\nARG GITHUB_TOKEN\n", "FROM alpine\nRUN --mount=type=secret,id=github_token cat /run/secrets/github_token\n",
   "ARG/ENV values persist in image metadata/history; use RUN --mount=type=secret.", sev="major", kind="security", cat="security")
bc("FROM-PLATFORM-FLAG-CONST", "from-platform-flag-const-disallowed", "forces the image to build on only one target platform",
   '((from_instruction (param) @match) (#match? @match "^--platform=[a-z]"))', "FROM --platform=linux/amd64 alpine\n", "FROM alpine\n",
   "A constant --platform prevents multi-platform builds; use $BUILDPLATFORM/$TARGETPLATFORM.", sev="minor")
bc("EXPOSE-PROTO-CASING", "expose-proto-casing", "Protocol names in the EXPOSE instruction should be specified in lowercase",
   '(source_file) @match', "FROM nginx\nEXPOSE 80/TCP\n", "FROM nginx\nEXPOSE 80/tcp\n", "Use lowercase tcp/udp.", sev="info",
   filters=["node.is_root", r"file.has_re:(?m)^\s*(?i:EXPOSE)\s.*/(T[Cc][Pp]|t[Cc]P|tC[Pp]|U[Dd][Pp]|u[Dd]P|uD[Pp])\b"])
bc("EXPOSE-INVALID-FORMAT", "expose-invalid-format", "It should not include an IP address or host-port mapping",
   '(source_file) @match', "FROM nginx\nEXPOSE 127.0.0.1:80:80\n", "FROM nginx\nEXPOSE 80\n",
   "EXPOSE takes container ports only; publish host ports at run time.", sev="minor", cat="correctness",
   filters=["node.is_root", r"file.has_re:(?im)^\s*EXPOSE\s+.*\b\d+:\d+"])
# --- best practices ----------------------------------------------------------------------------------------------------
P("LATEST-TAG", "Base image without a pinned tag (or :latest)", REF, "If you omit either of them, the builder assumes a latest tag by default.",
  '[(image_spec name: (image_name) @match !tag !digest) (image_spec name: (image_name) @match tag: (image_tag) @t (#match? @t "^:?latest$"))]',
  "FROM node\n", "FROM node:24.11-alpine\n", "Unpinned/latest base images change under you; pin a version (ideally a digest).",
  sev="minor", cat="reproducibility", filters=[r"node.lacks_re:^(scratch|[$].*)$", r"file.count_lt:1:(?i)\bAS\s+{text}\s*$"])
P("NO-DIGEST", "Base image not pinned by digest", BP, "Pin base image versions", '(from_instruction (image_spec name: (image_name) @match tag: (image_tag) !digest))',
  "FROM node:24-alpine\n", "FROM node:24-alpine@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n",
  "Tags are mutable; pin a digest for reproducible, tamper-evident builds (and let a bot update it).", sev="info", cat="reproducibility",
  mode="ai-confirm", ai="Is this a production/release Dockerfile where a mutable tag (not a digest) is a real supply-chain/reproducibility concern?")
P("APT-UPDATE-ALONE", "apt-get update in a separate RUN", BP, "Always combine RUN apt-get update with apt-get install in the same RUN statement.",
  '((run_instruction) @match (#match? @match "apt-get +(-[a-z]+ +)*update"))', "FROM debian\nRUN apt-get update\nRUN apt-get install -y curl\n",
  "FROM debian\nRUN apt-get update && apt-get install -y curl\n", "A cached `apt-get update` layer makes later installs use stale indexes.",
  sev="minor", cat="cache", filters=["node.lacks_re:apt-get +(-[a-z]+ +)*install"])
P("APT-NO-INSTALL-RECOMMENDS", "apt-get install without --no-install-recommends", BP, "--no-install-recommends",
  '((run_instruction) @match (#match? @match "apt-get +(-[a-z]+ +)*install"))', "FROM debian\nRUN apt-get update && apt-get install -y curl\n",
  "FROM debian\nRUN apt-get update && apt-get install -y --no-install-recommends curl\n", "Avoid pulling recommended packages you don't need.",
  sev="info", cat="image-size", filters=["node.lacks_re:no-install-recommends"])
P("APT-LISTS-NOT-REMOVED", "apt lists not cleaned in the same layer", BP, "rm -rf /var/lib/apt/lists/*",
  '((run_instruction) @match (#match? @match "apt-get +(-[a-z]+ +)*install"))', "FROM debian\nRUN apt-get update && apt-get install -y curl\n",
  "FROM debian\nRUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*\n", "Remove /var/lib/apt/lists/* in the same RUN to keep the layer small.",
  sev="info", cat="image-size", filters=["node.lacks_re:/var/lib/apt/lists", "node.lacks_re:type=cache"])
P("PIPE-WITHOUT-PIPEFAIL", "RUN pipeline without set -o pipefail", BP, "prepend set -o pipefail && to ensure that an unexpected error prevents the build from inadvertently succeeding",
  '((run_instruction (shell_command) @match) (#match? @match "[^|][|][^|]"))', "FROM debian\nRUN wget -O - https://example.com/x | wc -l > /n\n",
  "FROM debian\nRUN set -o pipefail && wget -O - https://example.com/x | wc -l > /n\n", "Without pipefail only the last command's exit status counts.",
  sev="minor", cat="correctness", filters=["node.lacks_re:pipefail", r"file.lacks_re:(?im)^\s*SHELL\s.*pipefail"])
P("CURL-PIPE-SHELL", "RUN pipes a download straight into a shell", BP, "prepend set -o pipefail && to ensure that an unexpected error prevents the build from inadvertently succeeding",
  '((run_instruction) @match (#match? @match "(curl|wget)[^|;&]*[|] *(sudo +)?(ba|z|da)?sh"))', "FROM debian\nRUN curl -fsSL https://get.example.com | sh\n",
  "FROM debian\nADD --checksum=sha256:0123abcd https://get.example.com/install.sh /tmp/install.sh\nRUN sh /tmp/install.sh\n",
  "Executing unverified remote scripts at build time is a supply-chain risk; download, verify (checksum/signature), then run.",
  sev="major", kind="security", cat="security")
P("ADD-LOCAL-FILE", "ADD used to copy local files", BP, "ADD and COPY are functionally similar.",
  '((add_instruction (path) @match . (path)) (#not-match? @match "^[\\\"\']?((https?|git)://|git@)|[.](tar|tgz|tbz2?|txz|gz|bz2|xz|zst|lz|lzma)[\\\"\']?$"))', "FROM alpine\nADD . /app\n", "FROM alpine\nCOPY . /app\n",
  "Prefer COPY for local files; ADD's implicit URL fetch and auto-extraction surprise readers.", sev="minor", cat="best-practice",
  filters=[r"parent.lacks_re:(?i)^add\s+(--[a-z-]+=?\S*\s+)*[\"']?(https?|git)://"],
  # fixture triage (hadolint DL3020): the query used to test the destination, not the source;
  # archives are auto-extracted (a legitimate ADD), quoted sources included
  fp=["FROM alpine\nADD vendor.tar.gz /opt/\n", "FROM alpine\nADD \"bundle.tgz\" /opt/\n", "FROM alpine\nADD \"https://example.com/x\" /opt/\n"])
P("ADD-REMOTE-NO-CHECKSUM", "ADD of a remote resource without --checksum", REF, "The --checksum flag lets you verify the checksum of a remote Git or HTTP resource",
  '((add_instruction) @match (#match? @match "(?i)^add\\\\s+(--[a-z-]+(=\\\\S*)?\\\\s+)*(https?|git)://"))', "FROM alpine\nADD https://example.com/tool.tgz /opt/\n",
  "FROM alpine\nADD --checksum=sha256:24454f830cdb571e2c4ad15481119c43b3cafd48dd869a9b2945d1036d1dc68d https://example.com/tool.tgz /opt/\n",
  "Remote downloads should be integrity-checked with --checksum.", sev="major", kind="security", cat="security",
  filters=["node.lacks_re:--checksum"])
P("USER-ROOT", "Final USER is root", BP, "If a service can run without privileges, use USER to change to a non-root user.",
  '((user_instruction user: (_) @match) (#match? @match "^(root|0)(:|$)"))', "FROM alpine\nUSER root\nCMD [\"app\"]\n",
  "FROM alpine\nUSER root\nRUN apk add curl\nUSER app\nCMD [\"app\"]\n", "The container runs as root; switch back to an unprivileged user.",
  sev="major", kind="security", cat="security", filters=[r"file.count_lt:1:(?is)USER\s+{text}\s.*\n\s*USER\s+[^r0\s]"])
P("NO-USER", "Image never switches to a non-root user", BP, "If a service can run without privileges, use USER to change to a non-root user.",
  '(source_file) @match', "FROM node:24\nCOPY . /app\nCMD [\"node\", \"/app/index.js\"]\n",
  "FROM node:24\nCOPY . /app\nUSER node\nCMD [\"node\", \"/app/index.js\"]\n", "No USER instruction: the container runs as root unless the base image sets a user.",
  sev="minor", kind="security", cat="security", mode="ai-confirm", filters=["node.is_root", r"file.lacks_re:(?im)^\s*USER\s", r"file.has_re:(?im)^\s*(CMD|ENTRYPOINT)\s"],
  ai="Is this a runtime image whose base image does not already set a non-root USER (e.g. not distroless:nonroot, not an image whose docs state it runs unprivileged)?")
P("SUDO", "sudo used in RUN", BP, "Avoid installing or using sudo as it has unpredictable TTY and signal-forwarding behavior",
  '((run_instruction) @match (#match? @match "(^|[;&|] *|RUN +)sudo "))', "FROM debian\nRUN sudo apt-get install -y x\n", "FROM debian\nRUN apt-get install -y x\n",
  "Builds already run as root unless USER changed; use gosu/su-exec for runtime privilege drops.", sev="minor", cat="best-practice")
P("RUN-CD", "RUN cd ... instead of WORKDIR", BP, "you should use WORKDIR instead of proliferating instructions like RUN cd",
  '((run_instruction (shell_command) @match) (#match? @match "^cd +[^&;]+&&"))', "FROM alpine\nRUN cd /app && make\n", "FROM alpine\nWORKDIR /app\nRUN make\n",
  "Use WORKDIR rather than RUN cd.", sev="info", cat="best-practice")
P("ENV-SECRET-LAYER", "Secret written by ENV persists in the layer", BP, "Each ENV line creates a new intermediate layer, just like RUN commands.",
  f'(env_instruction (env_pair name: (_) @n value: (_) @match) (#match? @n "{SECRET_NAME_RE.replace("^(", "(?i)^.*(").replace(")$", ")$")}"))',
  "FROM alpine\nENV DB_PASSWORD=hunter2\n", "FROM alpine\nRUN --mount=type=secret,id=db_password ./configure\n",
  "Unsetting an ENV later does not remove it from earlier layers or `docker history`.", sev="critical", kind="security", cat="security")
P("HEALTHCHECK-MISSING", "Long-running service image without HEALTHCHECK", REF, "The HEALTHCHECK instruction tells Docker how to test a container",
  '(source_file) @match', 'FROM nginx\nEXPOSE 80\nCMD ["nginx", "-g", "daemon off;"]\n',
  'FROM nginx\nEXPOSE 80\nHEALTHCHECK CMD curl -f http://localhost/ || exit 1\nCMD ["nginx", "-g", "daemon off;"]\n',
  "Declare a HEALTHCHECK so orchestrators can detect a hung service (unless your platform probes health itself).", sev="info",
  cat="best-practice", mode="ai-confirm", filters=["node.is_root", r"file.has_re:(?im)^\s*EXPOSE\s", r"file.lacks_re:(?im)^\s*HEALTHCHECK\s"],
  ai="Is this a long-running network service image deployed somewhere without its own health probing (e.g. plain Docker/Compose rather than Kubernetes probes)?")

# --- Compose -------------------------------------------------------------------------------------------------------------

# ---- 2026.10 expansion (Dockerfile)
bc("INVALID-DEFAULT-ARG-IN-FROM", "invalid-default-arg-in-from", "An ARG used in an image reference should be valid when no build arguments are used.",
   '(source_file) @match', "ARG TAG=\nFROM alpine:${TAG}\n", "ARG TAG=3.20\nFROM alpine:${TAG}\n",
   "With the empty default the build fails unless --build-arg is passed; give the ARG a valid default.", sev="minor", cat="correctness",
   filters=[r"file.has_re:(?m)^\s*ARG\s+\w+=(\x22\x22)?\s*$", r"file.has_re:(?m)^\s*FROM\s+\S*\$"])
P("ENV-DEBIAN-FRONTEND", "ENV DEBIAN_FRONTEND persisted into the image", REF + "#env", "setting ENV DEBIAN_FRONTEND=noninteractive changes the behavior of apt-get",
  '((env_instruction (env_pair name: (_) @n)) @match (#eq? @n "DEBIAN_FRONTEND"))', "FROM debian:12\nENV DEBIAN_FRONTEND=noninteractive\n",
  "FROM debian:12\nARG DEBIAN_FRONTEND=noninteractive\n", "ENV persists into containers; use ARG or set it inline on the RUN line.", sev="minor", cat="best-practice")
P("ENTRYPOINT-SHELL-WITH-CMD", "Shell-form ENTRYPOINT ignores CMD", REF + "#entrypoint", "The shell form of ENTRYPOINT ignores any CMD or docker run command line arguments.",
  '(source_file (entrypoint_instruction (shell_command)) @match (cmd_instruction))', 'FROM node:22\nENTRYPOINT node app.js\nCMD ["--port", "80"]\n',
  'FROM node:22\nENTRYPOINT ["node", "app.js"]\nCMD ["--port", "80"]\n', "CMD arguments are silently dropped and signals are not forwarded; use exec form.", sev="major", cat="correctness")
P("COPY-FROM-INDEX", "COPY --from=<stage number>", "https://docs.docker.com/build/building/multi-stage/", "you refer to them by their integer number",
  '((copy_instruction (param) @match) (#match? @match "^--from=[0-9]+$"))', "FROM golang:1.25 AS build\nFROM alpine:3.20\nCOPY --from=0 /out/app /app\n",
  "FROM golang:1.25 AS build\nFROM alpine:3.20\nCOPY --from=build /out/app /app\n", "Name stages (FROM ... AS name); indexes break when stages are reordered.", sev="info", cat="best-practice",
  quote="By default, the stages aren't named, and you refer to them by their integer number, starting with 0 for the first FROM instruction. However, you can name your stages, by adding an AS <NAME> to the FROM instruction.")
P("COPY-SECRET-FILE", "Credential file copied into the image", "https://docs.docker.com/build/building/secrets/", "A build secret is any piece of sensitive information",
  '((copy_instruction (path) @match) (#match? @match "(^|/)(\\\\.npmrc|\\\\.pypirc|\\\\.netrc|\\\\.env|id_rsa|id_ed25519|\\\\.aws|\\\\.docker/config\\\\.json|credentials\\\\.json|\\\\.git-credentials)$"))\n((add_instruction (path) @match) (#match? @match "(^|/)(\\\\.npmrc|\\\\.pypirc|\\\\.netrc|\\\\.env|id_rsa|id_ed25519|\\\\.aws|credentials\\\\.json)$"))',
  "FROM node:22\nCOPY .npmrc /root/.npmrc\nRUN npm ci\n", "FROM node:22\nRUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci\n",
  "Files copied into a layer stay in the image history even if deleted later; use RUN --mount=type=secret.", sev="critical", kind="security", cat="security")
P("NO-CACHE-MOUNT", "Package install without a cache mount", "https://docs.docker.com/build/cache/optimize/", "Cache mounts let you specify a persistent package cache to be used during builds.",
  '((run_instruction (shell_command) @match) (#match? @match "^(npm (ci|install)|yarn install|pnpm install|pip install|go mod download|go build|cargo build|apt-get install|apk add|composer install|bundle install|mvn |gradle )"))',
  "FROM golang:1.25\nRUN go mod download\n", "FROM golang:1.25\nRUN --mount=type=cache,target=/go/pkg/mod go mod download\n",
  "A cache mount keeps the package cache across builds without bloating layers.", sev="info", cat="performance", filters=[r"parent.lacks_re:--mount=type=cache"])
P("COPY-ALL-BEFORE-INSTALL", "COPY . before installing dependencies", "https://docs.docker.com/build/cache/optimize/", "First, copy over the package management files",
  '((copy_instruction (path) @src) @match (#eq? @src "."))', "FROM node:22\nWORKDIR /app\nCOPY . .\nRUN npm ci\n",
  "FROM node:22\nWORKDIR /app\nCOPY package.json package-lock.json ./\nRUN npm ci\nCOPY . .\n", "Every source change invalidates the dependency layer; copy manifests first.",
  sev="minor", cat="performance", filters=[r"file.has_re:(?ms)^\s*COPY\s+\.\s+\S+\s*$.*^\s*RUN\s+.*(npm (ci|install)|yarn( install)?\b|pnpm install|pip install -r|poetry install|go mod download|bundle install|composer install)"],
  mode="ai-confirm", ai="Is the dependency install step after this COPY . (not preceded by a manifest-only COPY + install)?")


C = Pack("COMPOSE", "yaml", "Compose Specification (docker compose 5.6)", {"any": "*"},
         files=["**/compose.yaml", "**/compose.yml", "**/compose.*.yaml", "**/compose.*.yml", "**/docker-compose.yaml", "**/docker-compose.yml",
                "**/docker-compose.*.yaml", "**/docker-compose.*.yml"])
C.R = P.R  # one module, one rule list


def svc(key, value="(_) @match", kpred=None):
    kp = kpred or f'(#eq? @k "{key}")'
    return ('(block_mapping_pair key: (flow_node) @s (#eq? @s "services") value: (block_node (block_mapping (block_mapping_pair value: '
            f'(block_node (block_mapping (block_mapping_pair key: (flow_node) @k {kp} value: {value})))))))')


SV = lambda body: "services:\n  web:\n    image: nginx:1.29\n" + body
C("VERSION-OBSOLETE", "Top-level `version` is obsolete", "https://docs.docker.com/reference/compose-file/version-and-name/",
  "The top-level version property is defined by the Compose Specification for backward compatibility.",
  '(stream (document (block_node (block_mapping (block_mapping_pair key: (flow_node) @match (#eq? @match "version"))))))',
  'version: "3.8"\nservices:\n  web:\n    image: nginx:1.29\n', "services:\n  web:\n    image: nginx:1.29\n",
  "Compose ignores `version` and prints an obsolescence warning; remove it.", sev="minor", kind="deprecation", cat="compose")
C("PRIVILEGED", "Service runs privileged", SVC, "privileged configures the service container to run with elevated privileges.",
  svc("privileged", '(flow_node (plain_scalar (boolean_scalar) @match (#eq? @match "true")))'), SV("    privileged: true\n"), SV("    cap_add: [NET_BIND_SERVICE]\n"),
  "A privileged container has (nearly) full host access; grant only the capabilities needed.", sev="critical", kind="security", cat="security")
C("NETWORK-MODE-HOST", "network_mode: host", SVC, "network_mode sets a service container's network mode.",
  svc("network_mode", '(flow_node) @match (#match? @match "^[\\"\']?host[\\"\']?$")'), SV("    network_mode: host\n"), SV("    ports: [\"127.0.0.1:8080:80\"]\n"),
  "Host networking removes network isolation and exposes every listening port on the host.", sev="major", kind="security", cat="security")
C("PID-HOST", "pid: host", SVC, "pid sets the PID mode for container created by Compose.",
  svc("pid", '(flow_node) @match (#match? @match "host")'), SV("    pid: host\n"), SV("    init: true\n"),
  "Sharing the host PID namespace lets the container see/signal host processes.", sev="major", kind="security", cat="security")
C("IPC-HOST", "ipc: host", SVC, "ipc configures the IPC isolation mode set by the service container.",
  svc("ipc", '(flow_node) @match (#match? @match "host")'), SV("    ipc: host\n"), SV("    ipc: private\n"),
  "Host IPC namespace sharing breaks isolation.", sev="major", kind="security", cat="security")
C("CAP-ADD-ALL", "cap_add: ALL / SYS_ADMIN", SVC, "cap_add specifies additional container capabilities as strings.",
  svc("cap_add", '(_ (_ (_ (flow_node) @match (#match? @match "ALL|SYS_ADMIN|SYS_PTRACE|SYS_MODULE|NET_ADMIN"))))'),
  SV("    cap_add:\n      - ALL\n"), SV("    cap_add:\n      - NET_BIND_SERVICE\n"),
  "Broad capabilities (ALL, SYS_ADMIN, ...) are close to privileged mode.", sev="major", kind="security", cat="security")
C("SECCOMP-UNCONFINED", "security_opt disables seccomp/AppArmor", SVC, "security_opt overrides the default labeling scheme for each container.",
  svc("security_opt", '(_ (_ (_ (flow_node) @match (#match? @match "unconfined"))))'), SV("    security_opt:\n      - seccomp:unconfined\n"),
  SV("    security_opt:\n      - no-new-privileges:true\n"), "Disabling seccomp/AppArmor removes kernel attack-surface filtering.",
  sev="major", kind="security", cat="security")
C("DOCKER-SOCKET", "Docker socket mounted into a container", SEC, "only trusted users should be allowed to control your Docker daemon.",
  svc("volumes", '(_ (_ (_ (flow_node) @match (#match? @match "docker[.]sock"))))'), SV("    volumes:\n      - /var/run/docker.sock:/var/run/docker.sock\n"),
  SV("    volumes:\n      - data:/data\n"), "Mounting the Docker socket gives the container root on the host.", sev="critical", kind="security", cat="security",
  docv="Docker Engine security docs")
C("PORT-ALL-INTERFACES", "Port published on all interfaces", SVC, "If it is not set, it binds to all network interfaces",
  svc("ports", '(_ (_ (_ (flow_node) @match (#match? @match "^[\\"\']?[0-9]+(-[0-9]+)?:[0-9]"))))'), SV("    ports:\n      - \"5432:5432\"\n"),
  SV("    ports:\n      - \"127.0.0.1:5432:5432\"\n"), "Without a host IP the port is reachable from every network the host is on (and bypasses ufw/firewalld rules).",
  sev="minor", kind="security", cat="security", mode="ai-confirm",
  ai="Is this service (e.g. a database, cache or admin UI) one that should not be reachable from outside the host?")
C("LINKS-LEGACY", "Legacy `links`", SVC, "links defines a network link to containers in another service.", svc("links"),
  SV("    links:\n      - db\n"), SV("    depends_on:\n      - db\n"), "Services on the same network reach each other by name; links are legacy.",
  sev="info", kind="modernization", cat="compose")
C("CONTAINER-NAME", "container_name prevents scaling", SVC, "Compose does not scale a service beyond one container if the Compose",
  svc("container_name"), SV("    container_name: web\n"), SV("    hostname: web\n"), "A fixed container_name blocks `--scale` and clashes across projects.",
  sev="info", cat="compose")
C("IMAGE-LATEST", "Service image untagged or :latest", SVC, "image specifies the image to start the container from.",
  svc("image", '(flow_node) @match (#match? @match "^[\\"\']?[^:@\\"\']+(:latest)?[\\"\']?$")'), "services:\n  web:\n    image: nginx\n",
  "services:\n  web:\n    image: nginx:1.29\n", "Pin image tags (or digests) for reproducible deployments.", sev="minor", cat="reproducibility",
  filters=[r"node.lacks_re:\$\{"])
C("ENV-SECRET", "Secret passed via environment", SVC, "The secrets attribute grants access to sensitive data defined by the secrets top-level element",
  svc("environment", f'(_ (_ (block_mapping_pair key: (flow_node) @n (#match? @n "{SECRET_NAME_RE.replace("^(", "(?i)^.*(").replace(")$", ")$")}") value: (flow_node) @match)))') + "\n" +
  svc("environment", '(_ (_ (block_sequence_item (flow_node) @match (#match? @match "(?i)(password|secret|token|api_?key)[^=]*=[^$]"))))'),
  SV("    environment:\n      DB_PASSWORD: hunter2\n"), SV("    secrets:\n      - db_password\n"),
  "Literal secrets in environment end up in `docker inspect` and the repo; use Compose secrets or an env_file outside VCS.",
  sev="major", kind="security", cat="security", filters=[r"node.lacks_re:^[\"']?\$\{"])
C("RESTART-MISSING", "Long-running service without a restart policy", SVC, "restart defines the policy that the platform applies on container termination.",
  '(block_mapping_pair key: (flow_node) @s (#eq? @s "services") value: (block_node (block_mapping (block_mapping_pair key: (flow_node) @match value: (block_node) @body))))',
  "services:\n  web:\n    image: nginx:1.29\n", "services:\n  web:\n    image: nginx:1.29\n    restart: unless-stopped\n",
  "Default restart policy is `no`: a crashed service stays down.", sev="info", cat="compose", mode="ai-confirm",
  filters=[r"parent.lacks_re:(?m)^\s+restart\s*:"],
  ai="Is this a long-running production service (not a one-off job, dev-only container, or Swarm service using deploy.restart_policy)?")
C("DEPENDS-ON-NO-HEALTH", "depends_on without condition: service_healthy", SVC, "Specifies that a dependency is expected to be \"healthy\"",
  svc("depends_on", '(block_node (block_sequence) @match)'), SV("    depends_on:\n      - db\n"),
  SV("    depends_on:\n      db:\n        condition: service_healthy\n"), "Short-form depends_on only waits for the container to start, not to be ready.",
  sev="info", cat="compose")
C("READ-ONLY", "Writable root filesystem", SVC, "read_only configures the service container to be created with a read-only filesystem.",
  '(block_mapping_pair key: (flow_node) @s (#eq? @s "services") value: (block_node (block_mapping (block_mapping_pair key: (flow_node) @match value: (block_node) @body))))',
  "services:\n  api:\n    image: acme/api:1.2\n", "services:\n  api:\n    image: acme/api:1.2\n    read_only: true\n",
  "Hardening: a read-only root filesystem limits what an attacker can persist.", sev="info", kind="security", cat="security",
  mode="ai-confirm", filters=[r"parent.lacks_re:(?m)^\s+read_only\s*:\s*true"],
  ai="Is this a stateless application service that could run with read_only: true (writable paths via tmpfs/volumes)?")
C("LOGGING-DRIVER-NONE", "Container logging disabled (driver: none)", SVC, "logging defines the logging configuration for the service.",
  '(block_mapping_pair key: (flow_node) @l (#eq? @l "logging") value: (block_node (block_mapping (block_mapping_pair key: (flow_node) @k (#eq? @k "driver") value: (flow_node) @match (#match? @match "^[\\"\']?none[\\"\']?$")))))',
  SV("    logging:\n      driver: none\n"), SV("    logging:\n      driver: json-file\n      options:\n        max-size: 10m\n"),
  "With the none driver the service's output is discarded, so errors and attack traces leave no record (OWASP Docker Top 10 D10). Use a driver that ships logs, with rotation.",
  sev="minor", kind="security", cat="security", cwe=["CWE-778"], owasp=["D10"])
C("NO-RESOURCE-LIMITS", "Service without memory/CPU/PID limits", "https://docs.docker.com/reference/compose-file/deploy/",
  "resources configures physical resource constraints for container to run on platform.",
  '(block_mapping_pair key: (flow_node) @s (#eq? @s "services") value: (block_node (block_mapping (block_mapping_pair key: (flow_node) @match value: (block_node) @body))))',
  "services:\n  api:\n    image: acme/api:1.2\n", "services:\n  api:\n    image: acme/api:1.2\n    deploy:\n      resources:\n        limits:\n          memory: 512m\n          pids: 200\n",
  "Without limits one container can exhaust the host's memory, CPU or process table and take down its neighbours (OWASP Docker Top 10 D07). Set deploy.resources.limits (or mem_limit / pids_limit).",
  sev="info", kind="security", cat="security", mode="ai-confirm", cwe=["CWE-770"], owasp=["D07"],
  filters=[r"parent.lacks_re:(?m)^\s+(limits|mem_limit|pids_limit|cpus)\s*:"],
  ai="Is this a long-running service on a shared host (not a one-off tool or a dev-only container) where a runaway process would affect others?")

# ---- 2026.10 expansion (Compose)
for key, val, why in [("userns_mode", "host", "disables user-namespace remapping"), ("uts", "host", "shares the host's hostname/UTS namespace"),
                      ("cgroup", "host", "runs the container in the host's cgroup namespace")]:
    C(f"{key.upper().replace('_', '-')}-HOST", f"{key}: host", SVC, {"userns_mode": "userns_mode sets the user namespace for the service.",
      "uts": "uts configures the UTS namespace mode set for the service container.", "cgroup": "cgroup specifies"}[key],
      svc(key, f'(flow_node) @match (#eq? @match "{val}")'), SV(f"    {key}: {val}\n"), SV(""),
      f"Weakens isolation: {why}.", sev="major", kind="security", cat="security")
C("BUILD-ARGS-SECRET", "Secret passed as a build arg", "https://docs.docker.com/reference/compose-file/build/", "args define build arguments, that is Dockerfile ARG values.",
  svc("build", f'(block_node (block_mapping (block_mapping_pair key: (flow_node) @a (#eq? @a "args") value: (block_node (block_mapping (block_mapping_pair key: (flow_node) @match (#match? @match "(?i)(token|password|passwd|secret|api[_-]?key|private[_-]?key)")))))))'),
  SV("    build:\n      context: .\n      args:\n        NPM_TOKEN: abc123\n"), SV("    build:\n      context: .\n      secrets:\n        - npm_token\n"),
  "Build args are visible in image history; use build secrets.", sev="major", kind="security", cat="security")
RULES = P.R

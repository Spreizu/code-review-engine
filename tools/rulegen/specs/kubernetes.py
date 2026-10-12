"""Kubernetes manifests (OWASP Kubernetes Top 10 2022 / Pod Security Standards / CIS-style hardening).
Tree-sitter YAML queries on files that declare both apiVersion and kind. Detection and wording are
crev's own; quotes come from kubernetes.io (CC BY 4.0)."""
from specs._common import Pack

P = Pack("KUBE", "yaml", "Kubernetes docs (v1.37)", {"any": "*"}, files=["**/*.yaml", "**/*.yml"])
PSS = "https://kubernetes.io/docs/concepts/security/pod-security-standards/"
RBAC = "https://kubernetes.io/docs/concepts/security/rbac-good-practices/"
MANIFEST = ["file.has_re:(?m)^apiVersion:\\s*\\S", "file.has_re:(?m)^kind:\\s*\\S"]
POD = lambda body: "apiVersion: v1\nkind: Pod\nmetadata:\n  name: web\nspec:\n" + body
CTR = lambda body="": POD("  containers:\n    - name: web\n      image: nginx:1.29\n" + body)


def pair(key, rx, kpred=None):
    kp = kpred or f'(#eq? @k "{key}")'
    return f'((block_mapping_pair key: (flow_node) @k value: (flow_node) @match) {kp} (#match? @match "{rx}"))'


def under(parent, key, rx):
    return (f'((block_mapping_pair key: (flow_node) @p value: (block_node (block_mapping (block_mapping_pair key: (flow_node) @k value: (flow_node) @match)))) '
            f'(#eq? @p "{parent}") (#eq? @k "{key}") (#match? @match "{rx}"))')


def k8s(id, title, url, needle, query, bad, good, msg, sev="major", kind="security", cat="security", **kw):
    kw["filters"] = MANIFEST + kw.get("filters", [])
    r = P(id, title, url, needle, query, bad, good, msg, sev=sev, kind=kind, cat=cat, **kw)
    r["detection"]["exclude_tests"] = True
    return r


TRUE = '^[\\"\']?true[\\"\']?$'
k8s("PRIVILEGED", "Privileged container", PSS, "Privileged Pods disable most security mechanisms and must be disallowed.",
    pair("privileged", TRUE), CTR("      securityContext:\n        privileged: true\n"), CTR("      securityContext:\n        privileged: false\n"),
    "A privileged container can access every host device and escape to the node. Grant only the specific capabilities it needs.",
    sev="critical", cwe=["CWE-250"], owasp=["K01:2022"])
k8s("PRIV-ESC", "allowPrivilegeEscalation: true", PSS, "Privilege escalation (such as via set-user-ID or set-group-ID file mode) should not be allowed.",
    pair("allowPrivilegeEscalation", TRUE), CTR("      securityContext:\n        allowPrivilegeEscalation: true\n"),
    CTR("      securityContext:\n        allowPrivilegeEscalation: false\n"),
    "Processes in the container may gain more privileges than their parent (setuid binaries). Set allowPrivilegeEscalation: false.",
    cwe=["CWE-250"], owasp=["K01:2022"])
k8s("HOST-NAMESPACE", "Pod shares a host namespace (hostNetwork/hostPID/hostIPC)", PSS, "Sharing the host namespaces must be disallowed.",
    pair("", TRUE, '(#match? @k "^(hostNetwork|hostPID|hostIPC)$")'), POD("  hostNetwork: true\n  containers:\n    - name: web\n      image: nginx:1.29\n"), CTR(),
    "The pod sees the node's network stack, processes or IPC, so a compromise reaches other workloads and the node. Drop host namespaces unless this is a node agent.",
    mode="ai-confirm", ai="Is this a node-level agent (CNI, monitoring, log collector) that genuinely needs the host namespace?", cwe=["CWE-668"], owasp=["K07:2022", "K01:2022"])
k8s("HOST-PATH", "hostPath volume", PSS, "HostPath volumes must be forbidden.",
    '((block_mapping_pair key: (flow_node) @k value: (block_node) @match) (#eq? @k "hostPath"))',
    POD("  containers:\n    - name: web\n      image: nginx:1.29\n  volumes:\n    - name: data\n      hostPath:\n        path: /var/data\n"),
    POD("  containers:\n    - name: web\n      image: nginx:1.29\n  volumes:\n    - name: data\n      emptyDir: {}\n"),
    "A hostPath volume exposes the node's filesystem to the pod; with write access it is a common container escape. Use emptyDir, a PVC or a CSI volume.",
    mode="ai-confirm", ai="Is this a node-level agent that needs this host directory, and is the mount read-only and narrowly scoped?", cwe=["CWE-668"], owasp=["K01:2022"],
    filters=["node.lacks_re:\\.sock\\b"])  # runtime sockets: KUBE-RUNTIME-SOCKET
k8s("RUNTIME-SOCKET", "Container runtime socket mounted", PSS, "HostPath volumes must be forbidden.",
    under("hostPath", "path", "(docker|containerd|crio|cri-dockerd)\\\\.sock"),
    POD("  containers:\n    - name: ci\n      image: docker:27\n  volumes:\n    - name: sock\n      hostPath:\n        path: /var/run/docker.sock\n"),
    POD("  containers:\n    - name: ci\n      image: gcr.io/kaniko-project/executor:v1.23.2\n"),
    "Access to the container runtime socket is root on the node: the pod can start privileged containers. Build images with a rootless builder instead.",
    sev="critical", cwe=["CWE-250"], owasp=["K01:2022"])
k8s("RUN-AS-ROOT", "Container explicitly runs as root", PSS, "Containers must not set runAsUser to 0",
    pair("", '^[\\"\']?(0|false)[\\"\']?$', '(#match? @k "^(runAsUser|runAsNonRoot)$")'),
    CTR("      securityContext:\n        runAsUser: 0\n"), CTR("      securityContext:\n        runAsNonRoot: true\n        runAsUser: 10001\n"),
    "The container process runs as UID 0, so any escape or writable host mount acts as root. Run as a non-root UID and set runAsNonRoot: true.",
    cwe=["CWE-250"], owasp=["K01:2022"])
k8s("DANGEROUS-CAPABILITIES", "Dangerous Linux capability added", PSS, "Adding additional capabilities beyond those listed below must be disallowed.",
    '((block_mapping_pair key: (flow_node) @c value: (block_node (block_mapping (block_mapping_pair key: (flow_node) @k value: (_) @match)))) (#eq? @c "capabilities") (#eq? @k "add"))',
    CTR("      securityContext:\n        capabilities:\n          add: [\"SYS_ADMIN\"]\n"), CTR("      securityContext:\n        capabilities:\n          add: [\"NET_BIND_SERVICE\"]\n          drop: [\"ALL\"]\n"),
    "SYS_ADMIN, NET_ADMIN, SYS_PTRACE, SYS_MODULE, BPF or ALL give the container near-root power over the node. Drop ALL and add back only what is needed.",
    filters=["node.has_re:(?i)\\b(SYS_ADMIN|NET_ADMIN|SYS_PTRACE|SYS_MODULE|DAC_READ_SEARCH|BPF|PERFMON|SYS_RAWIO|ALL)\\b"], cwe=["CWE-250"], owasp=["K01:2022"])
k8s("SECCOMP-UNCONFINED", "seccomp profile set to Unconfined", PSS, "Seccomp profile must not be explicitly set to Unconfined",
    under("seccompProfile", "type", "^[\\\"']?Unconfined[\\\"']?$"), CTR("      securityContext:\n        seccompProfile:\n          type: Unconfined\n"),
    CTR("      securityContext:\n        seccompProfile:\n          type: RuntimeDefault\n"),
    "Unconfined turns off syscall filtering, widening the kernel attack surface. Use RuntimeDefault (or a Localhost profile).",
    cwe=["CWE-693"], owasp=["K01:2022"])
k8s("READONLY-ROOT-FALSE", "readOnlyRootFilesystem: false", "https://kubernetes.io/docs/tasks/configure-pod-container/security-context/",
    "readOnlyRootFilesystem : Mounts the container's root filesystem as read-only.",
    pair("readOnlyRootFilesystem", '^[\\"\']?false[\\"\']?$'), CTR("      securityContext:\n        readOnlyRootFilesystem: false\n"),
    CTR("      securityContext:\n        readOnlyRootFilesystem: true\n"),
    "A writable root filesystem lets an intruder drop tools and persist changes. Set readOnlyRootFilesystem: true and mount emptyDir for paths that must be writable.",
    sev="minor", cwe=["CWE-732"], owasp=["K01:2022"])
k8s("HOST-PORT", "Container binds a hostPort", PSS, "HostPorts should be disallowed entirely (recommended) or restricted to a known list",
    '((block_mapping_pair key: (flow_node) @k value: (flow_node) @match) (#eq? @k "hostPort"))',
    CTR("      ports:\n        - containerPort: 8080\n          hostPort: 8080\n"), CTR("      ports:\n        - containerPort: 8080\n"),
    "hostPort opens the port on the node itself, bypassing Services and NetworkPolicies. Expose the pod through a Service instead.",
    sev="minor", mode="ai-confirm", ai="Is this a node-level agent or ingress controller that deliberately listens on the node?", cwe=["CWE-668"], owasp=["K07:2022"])
IMG = "https://kubernetes.io/docs/concepts/containers/images/"
IMG_Q = "If you don't specify a tag, Kubernetes assumes you mean the tag latest"
IMG_MSG = "The image is unpinned, so each node may pull a different build and a compromised or broken push rolls out silently. Pin a version tag, ideally with a digest."
CONTAINERS = ["file.has_re:(?m)^\\s+(containers|initContainers):"]
k8s("IMAGE-LATEST", "Container image pinned to :latest", IMG, IMG_Q,
    pair("image", ':latest[\\"\']?$'), CTR().replace("nginx:1.29", "nginx:latest"), CTR(), IMG_MSG,
    sev="minor", filters=CONTAINERS, cwe=["CWE-1357"], owasp=["K02:2022"])
k8s("IMAGE-UNTAGGED", "Container image without a tag or digest", IMG, IMG_Q,
    pair("image", '^[\\"\']?([a-z0-9.-]+(:[0-9]+)?/)?[a-z0-9._/-]+[\\"\']?$'), CTR().replace("nginx:1.29", "nginx"), CTR(), IMG_MSG,
    sev="minor", mode="ai-confirm", filters=CONTAINERS, cwe=["CWE-1357"], owasp=["K02:2022"],
    ai="Is this a real registry image rather than a placeholder that a build tool (skaffold, kustomize images:, ko, Helm values) replaces with a pinned reference?",
    fp=[CTR().replace("nginx:1.29", "registry.example.com:5000/team/web@sha256:" + "a" * 64)])
k8s("RBAC-WILDCARD", "RBAC rule grants wildcard verbs or resources", RBAC, "Avoid providing wildcard permissions when possible, especially to all resources.",
    '((block_mapping_pair key: (flow_node) @k value: (_) @match) (#match? @k "^(verbs|resources)$"))',
    'apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRole\nmetadata:\n  name: ops\nrules:\n  - apiGroups: [""]\n    resources: ["*"]\n    verbs: ["*"]\n',
    'apiVersion: rbac.authorization.k8s.io/v1\nkind: Role\nmetadata:\n  name: reader\nrules:\n  - apiGroups: [""]\n    resources: ["pods"]\n    verbs: ["get", "list", "watch"]\n',
    "A wildcard grants every verb or resource, including ones added to the cluster later (CRDs, secrets). List the exact resources and verbs.",
    filters=["file.has_re:(?m)^kind:\\s*(Cluster)?Role\\s*$", "node.has_re:[\\\"']\\*[\\\"']|^\\s*-\\s*\\*\\s*$|\\[\\s*\\*\\s*\\]"], cwe=["CWE-269"], owasp=["K03:2022"])
k8s("CLUSTER-ADMIN-BINDING", "Binding to cluster-admin", RBAC, "Administrators should not use cluster-admin accounts except where specifically needed.",
    under("roleRef", "name", "^[\\\"']?cluster-admin[\\\"']?$"),
    'apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRoleBinding\nmetadata:\n  name: ci\nroleRef:\n  apiGroup: rbac.authorization.k8s.io\n  kind: ClusterRole\n  name: cluster-admin\nsubjects:\n  - kind: ServiceAccount\n    name: ci\n    namespace: build\n',
    'apiVersion: rbac.authorization.k8s.io/v1\nkind: RoleBinding\nmetadata:\n  name: ci\n  namespace: build\nroleRef:\n  apiGroup: rbac.authorization.k8s.io\n  kind: Role\n  name: deployer\nsubjects:\n  - kind: ServiceAccount\n    name: ci\n    namespace: build\n',
    "The subject gets unrestricted control of the whole cluster; a leaked token for it is a full compromise. Bind a role scoped to the namespaces and resources needed.",
    mode="ai-confirm", ai="Does this subject (service account, user, group) genuinely need full cluster administration?", cwe=["CWE-269"], owasp=["K03:2022"])
k8s("ENV-SECRET-LITERAL", "Secret value written inline in a container env", "https://kubernetes.io/docs/concepts/security/secrets-good-practices/",
    "Secrets are designed for confidential data and ConfigMaps are designed for non-confidential data.",
    '((block_mapping (block_mapping_pair key: (flow_node) @n value: (flow_node) @nv) (block_mapping_pair key: (flow_node) @v value: (flow_node) @match)) (#eq? @n "name") (#eq? @v "value") (#match? @nv "(?i)(password|passwd|secret|token|api_?key|private_?key|credentials?)[\\"\']?$"))',
    CTR("      env:\n        - name: DB_PASSWORD\n          value: \"s3cr3t-prod\"\n"),
    CTR("      env:\n        - name: DB_PASSWORD\n          valueFrom:\n            secretKeyRef:\n              name: db\n              key: password\n"),
    "The secret sits in plain text in the manifest (and in Git and the pod spec, readable by anyone who can get pods). Reference a Secret with valueFrom.secretKeyRef.",
    filters=["node.lacks_re:^[\\\"']?(\\$|\\{\\{|<|changeme|example|$)", "node.lacks_re:^[\\\"']?[A-Z0-9_]+[\\\"']?$"], cwe=["CWE-798", "CWE-312"], owasp=["K08:2022"],
    fp=[CTR("      env:\n        - name: TOKEN_TTL_SECONDS\n          value: \"3600\"\n")])
k8s("KUBELET-ANONYMOUS", "Kubelet allows anonymous requests", "https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/",
    "are treated as anonymous requests, and given a username of system:anonymous",
    under("anonymous", "enabled", TRUE),
    "apiVersion: kubelet.config.k8s.io/v1beta1\nkind: KubeletConfiguration\nauthentication:\n  anonymous:\n    enabled: true\n",
    "apiVersion: kubelet.config.k8s.io/v1beta1\nkind: KubeletConfiguration\nauthentication:\n  anonymous:\n    enabled: false\n  webhook:\n    enabled: true\n",
    "Unauthenticated callers can reach the kubelet API (exec into pods, read logs) on every node. Disable anonymous auth and use webhook authentication/authorization.",
    sev="critical", cwe=["CWE-306"], owasp=["K06:2022", "K09:2022"])
DEPRECATED = r"^(extensions/v1beta1|apps/v1beta1|apps/v1beta2|policy/v1beta1|batch/v1beta1|networking\\.k8s\\.io/v1beta1|rbac\\.authorization\\.k8s\\.io/v1beta1|admissionregistration\\.k8s\\.io/v1beta1|apiextensions\\.k8s\\.io/v1beta1|autoscaling/v2beta1|autoscaling/v2beta2|scheduling\\.k8s\\.io/v1beta1|coordination\\.k8s\\.io/v1beta1|storage\\.k8s\\.io/v1beta1|flowcontrol\\.apiserver\\.k8s\\.io/v1beta[123])$"
k8s("DEPRECATED-API", "Manifest uses a removed API version", "https://kubernetes.io/docs/reference/using-api/deprecation-guide/",
    "API versions of Ingress is no longer served as of v1.22",
    '(stream (document (block_node (block_mapping (block_mapping_pair key: (flow_node) @k value: (flow_node) @match) (#eq? @k "apiVersion") (#match? @match "' + DEPRECATED + '")))))',
    "apiVersion: extensions/v1beta1\nkind: Ingress\nmetadata:\n  name: web\n", "apiVersion: networking.k8s.io/v1\nkind: Ingress\nmetadata:\n  name: web\n",
    "This API version is no longer served by current Kubernetes, so applying the manifest fails; older removed APIs also miss later security fields. Migrate to the stable version.",
    sev="major", kind="deprecation", cat="deprecation", owasp=["K10:2022"])
k8s("NO-RESOURCE-LIMITS", "Container without resource limits", "https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/",
    "the kubelet enforces those limits so that the running container is not allowed to use more of that resource than the limit you set",
    '((block_mapping_pair key: (flow_node) @c value: (block_node (block_sequence (block_sequence_item (block_node (block_mapping) @match))))) (#eq? @c "containers"))',
    CTR(), CTR("      resources:\n        limits:\n          memory: 256Mi\n        requests:\n          cpu: 100m\n          memory: 128Mi\n"),
    "Without limits one container can exhaust the node's memory or CPU and starve its neighbours (denial of service). Set memory limits and requests.",
    sev="info", kind="best-practice", mode="ai-confirm", ai="Is there no LimitRange/policy in this deployment that applies default limits, and is this a long-running workload?",
    filters=["node.lacks_re:(?m)^\\s+limits:"], cwe=["CWE-770"], owasp=["K01:2022"])

# ------------------------------------------------------------------ Pod Security Standards baseline (remaining controls) / CIS 5.x
k8s("APPARMOR-UNCONFINED", "AppArmor disabled (unconfined)", PSS, "The baseline policy should prevent overriding or disabling the default AppArmor profile",
    under("appArmorProfile", "type", "^[\\\"']?Unconfined[\\\"']?$") + '\n ' + pair("", "^[\\\"']?unconfined[\\\"']?$", '(#match? @k "^container\\\\.apparmor\\\\.security\\\\.beta\\\\.kubernetes\\\\.io/")'),
    CTR("      securityContext:\n        appArmorProfile:\n          type: Unconfined\n"), CTR("      securityContext:\n        appArmorProfile:\n          type: RuntimeDefault\n"),
    "The container runs without the AppArmor profile that limits file, mount and capability access, removing a layer that blocks many escapes. Use RuntimeDefault or a Localhost profile.",
    cwe=["CWE-693"], owasp=["K01:2022"])
k8s("PROC-MOUNT-UNMASKED", "procMount: Unmasked", PSS, "The default /proc masks are set up to reduce attack surface, and should be required.",
    pair("procMount", "^[\\\"']?Unmasked[\\\"']?$"), CTR("      securityContext:\n        procMount: Unmasked\n"), CTR("      securityContext:\n        procMount: Default\n"),
    "Unmasked /proc exposes kernel interfaces that the default masks hide, helping an attacker escape the container. Remove procMount or set Default.",
    cwe=["CWE-693"], owasp=["K01:2022"])
k8s("SELINUX-CUSTOM", "Custom SELinux type/user/role on a pod", PSS, "Setting the SELinux type is restricted, and setting a custom SELinux user or role option is forbidden.",
    under("seLinuxOptions", "type", "^[\\\"']?(spc_t|unconfined_t|[a-z_]+_t)[\\\"']?$") + '\n ' + under("seLinuxOptions", "user", ".") + '\n ' + under("seLinuxOptions", "role", "."),
    CTR("      securityContext:\n        seLinuxOptions:\n          type: spc_t\n"), CTR("      securityContext:\n        seLinuxOptions:\n          level: \"s0:c123,c456\"\n"),
    "A custom SELinux type such as spc_t runs the container unconfined by SELinux. Only container_t, container_init_t, container_kvm_t or container_engine_t are allowed by the baseline policy.",
    filters=["node.lacks_re:^[\\\"']?(container_t|container_init_t|container_kvm_t|container_engine_t)[\\\"']?$"], cwe=["CWE-693"], owasp=["K01:2022"])
k8s("WINDOWS-HOSTPROCESS", "Windows HostProcess container", PSS, "Windows Pods offer the ability to run HostProcess containers which enables privileged access to the Windows host machine.",
    pair("hostProcess", TRUE), CTR("      securityContext:\n        windowsOptions:\n          hostProcess: true\n"), CTR("      securityContext:\n        windowsOptions:\n          runAsUserName: ContainerUser\n"),
    "A HostProcess container runs directly on the Windows node with host privileges. Use it only for node agents.",
    sev="critical", mode="ai-confirm", ai="Is this a Windows node agent (CNI, CSI, monitoring) that genuinely needs host access?", cwe=["CWE-250"], owasp=["K01:2022"])
k8s("UNSAFE-SYSCTL", "Pod sets a sysctl outside the safe set", PSS, "Sysctls can disable security mechanisms or affect all containers on a host",
    '((block_mapping_pair key: (flow_node) @k value: (flow_node) @match) (#eq? @k "name") (#match? @match "^[\\"\']?(kernel|net|vm|fs)\\\\.") (#not-match? @match "^[\\"\']?(kernel\\\\.shm_rmid_forced|net\\\\.ipv4\\\\.ip_local_port_range|net\\\\.ipv4\\\\.ip_unprivileged_port_start|net\\\\.ipv4\\\\.tcp_syncookies|net\\\\.ipv4\\\\.ping_group_range|net\\\\.ipv4\\\\.ip_local_reserved_ports|net\\\\.ipv4\\\\.tcp_keepalive_time|net\\\\.ipv4\\\\.tcp_fin_timeout|net\\\\.ipv4\\\\.tcp_keepalive_intvl|net\\\\.ipv4\\\\.tcp_keepalive_probes|net\\\\.ipv4\\\\.tcp_rmem|net\\\\.ipv4\\\\.tcp_wmem)[\\"\']?$"))',
    POD("  securityContext:\n    sysctls:\n      - name: kernel.msgmax\n        value: \"65536\"\n  containers:\n    - name: web\n      image: nginx:1.29\n"),
    POD("  securityContext:\n    sysctls:\n      - name: net.ipv4.ip_local_port_range\n        value: \"32768 60999\"\n  containers:\n    - name: web\n      image: nginx:1.29\n"),
    "This sysctl is not namespaced per pod (or is not in the baseline safe list), so it can weaken or change kernel behaviour for every container on the node. Remove it or set it at node level deliberately.",
    sev="minor", filters=["file.has_re:sysctls:"], cwe=["CWE-693"], owasp=["K01:2022"])
k8s("SA-TOKEN-AUTOMOUNT", "Service account token mounted automatically", "https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/",
    "you can opt out of automounting API credentials",
    '((block_mapping_pair key: (flow_node) @k value: (block_node (block_sequence (block_sequence_item (block_node (block_mapping) @match))))) (#eq? @k "containers"))',
    CTR(), POD("  automountServiceAccountToken: false\n  containers:\n    - name: web\n      image: nginx:1.29\n"),
    "Every container gets a Kubernetes API token by default; if the app never calls the API, a compromise of it should not hand the attacker that token. Set automountServiceAccountToken: false on the pod or its ServiceAccount.",
    sev="info", kind="best-practice", mode="ai-confirm", ai="Does this workload not need to call the Kubernetes API (no client-go/kubectl/operator behaviour)?",
    filters=["file.lacks_re:automountServiceAccountToken:\\s*false"], cwe=["CWE-250"], owasp=["K03:2022"])

RULES = P.R

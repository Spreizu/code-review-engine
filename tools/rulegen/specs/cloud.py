"""Cloud Terraform pack: AWS (Security Hub CSPM controls), Azure (Microsoft Learn security guidance) and
Google Cloud (product security docs) configuration checks on Terraform resources. Only explicit insecure
values are flagged deterministically; settings whose risk depends on intent are ai-confirm. Detection
and wording are crev's own; quotes come from the cited vendor pages."""
from specs._common import Pack

P = Pack("TF", "hcl", "Terraform 1.16", {"terraform": "*"}, files=["**/*.tf"])
AWSP, AZP, GCPP = {"tf-provider.aws": ">=5.0"}, {"tf-provider.azurerm": ">=3.0"}, {"tf-provider.google": ">=5.0"}
SH = "https://docs.aws.amazon.com/securityhub/latest/userguide/"


def R(rtype, body, name="this"):
    return f'resource "{rtype}" "{name}" {{\n{body}}}\n'


def attr(label, name_re, val_re):
    return (f'((block (identifier) @bt . (string_lit) @rt (body (attribute (identifier) @an (expression) @val) @match)) '
            f'(#eq? @bt "resource") (#match? @rt "^.({label}).$") (#match? @an "^({name_re})$") (#match? @val "{val_re}"))')


def nattr(label, nb_re, name_re, val_re):
    """attribute inside a nested block (one level) of a resource."""
    return (f'((block (identifier) @bt . (string_lit) @rt (body (block (identifier) @nb (body (attribute (identifier) @an (expression) @val) @match)))) '
            f'(#eq? @bt "resource") (#match? @rt "^.({label}).$") (#match? @nb "^({nb_re})$") (#match? @an "^({name_re})$") (#match? @val "{val_re}"))')


def cloud(id, title, url, needle, query, bad, good, msg, sev="major", **kw):
    r = P(id, title, url, needle, query, bad, good, msg, sev=sev, kind="security", cat="security", **kw)
    r["detection"]["exclude_tests"] = True
    return r


FALSE, TRUE = "^false$", "^true$"
# ------------------------------------------------------------------ AWS
cloud("AWS-CLOUDTRAIL-NO-LOG-VALIDATION", "CloudTrail log file validation disabled", SH + "cloudtrail-controls.html",
      "CloudTrail log file validation should be enabled", attr("aws_cloudtrail", "enable_log_file_validation", FALSE),
      R("aws_cloudtrail", '  name                       = "main"\n  s3_bucket_name             = aws_s3_bucket.trail.id\n  enable_log_file_validation = false\n'),
      R("aws_cloudtrail", '  name                       = "main"\n  s3_bucket_name             = aws_s3_bucket.trail.id\n  enable_log_file_validation = true\n'),
      "Without digest files nobody can prove the audit logs were not edited or deleted after an incident. Set enable_log_file_validation = true.",
      sev="minor", applies=AWSP, cwe=["CWE-778"], owasp=["A09:2021", "A09:2025"], docv="AWS Security Hub User Guide")
cloud("AWS-CLOUDTRAIL-SINGLE-REGION", "CloudTrail trail limited to one region", SH + "cloudtrail-controls.html",
      "CloudTrail should be enabled and configured with at least one multi-Region trail", attr("aws_cloudtrail", "is_multi_region_trail", FALSE),
      R("aws_cloudtrail", '  name                  = "main"\n  s3_bucket_name        = aws_s3_bucket.trail.id\n  is_multi_region_trail = false\n'),
      R("aws_cloudtrail", '  name                  = "main"\n  s3_bucket_name        = aws_s3_bucket.trail.id\n  is_multi_region_trail = true\n'),
      "Activity in other regions (a favourite place to run crypto miners) is not recorded. Use a multi-region trail.",
      sev="minor", applies=AWSP, mode="ai-confirm", ai="Is there no other multi-region trail (e.g. an organisation trail) covering this account?",
      cwe=["CWE-778"], owasp=["A09:2021", "A09:2025"], docv="AWS Security Hub User Guide")
cloud("AWS-KMS-NO-ROTATION", "KMS key rotation disabled", SH + "kms-controls.html", "AWS KMS key rotation should be enabled",
      attr("aws_kms_key", "enable_key_rotation", FALSE),
      R("aws_kms_key", '  description         = "app data"\n  enable_key_rotation = false\n'),
      R("aws_kms_key", '  description         = "app data"\n  enable_key_rotation = true\n'),
      "The same key material protects data indefinitely, so one leak exposes everything ever encrypted. Enable automatic rotation (symmetric keys).",
      sev="minor", applies=AWSP, cwe=["CWE-324"], owasp=["A02:2021", "A04:2025"], docv="AWS Security Hub User Guide")
cloud("AWS-EC2-IMDSV1", "EC2 instance metadata allows IMDSv1", SH + "ec2-controls.html",
      "EC2 instances should use Instance Metadata Service Version 2 (IMDSv2)",
      nattr("aws_instance|aws_launch_template", "metadata_options", "http_tokens", '^\\"optional\\"$'),
      R("aws_instance", '  ami           = data.aws_ami.al2023.id\n  instance_type = "t3.micro"\n\n  metadata_options {\n    http_tokens = "optional"\n  }\n'),
      R("aws_instance", '  ami           = data.aws_ami.al2023.id\n  instance_type = "t3.micro"\n\n  metadata_options {\n    http_tokens = "required"\n  }\n'),
      "IMDSv1 answers plain GET requests, so any SSRF in the instance's apps can read its IAM role credentials. Require session tokens (http_tokens = \"required\").",
      applies=AWSP, cwe=["CWE-918", "CWE-522"], owasp=["A10:2021", "A01:2025"], docv="AWS Security Hub User Guide")
cloud("AWS-EKS-PUBLIC-ENDPOINT", "EKS API endpoint public to the internet", SH + "eks-controls.html",
      "EKS cluster endpoints should not be publicly accessible",
      nattr("aws_eks_cluster", "vpc_config", "endpoint_public_access", TRUE),
      R("aws_eks_cluster", '  name     = "prod"\n  role_arn = aws_iam_role.eks.arn\n\n  vpc_config {\n    subnet_ids             = var.subnets\n    endpoint_public_access = true\n  }\n'),
      R("aws_eks_cluster", '  name     = "prod"\n  role_arn = aws_iam_role.eks.arn\n\n  vpc_config {\n    subnet_ids              = var.subnets\n    endpoint_private_access = true\n    endpoint_public_access  = false\n  }\n'),
      "The Kubernetes API is reachable from the internet; a leaked kubeconfig or an API server CVE is directly exploitable. Use private access, or restrict public_access_cidrs to known ranges.",
      applies=AWSP, mode="ai-confirm", ai="Is public_access_cidrs missing or 0.0.0.0/0 for this cluster (i.e. not restricted to known ranges)?",
      cwe=["CWE-284"], owasp=["A01:2021", "A01:2025"], docv="AWS Security Hub User Guide")
cloud("AWS-OPENSEARCH-UNENCRYPTED", "OpenSearch domain without encryption at rest", SH + "opensearch-controls.html",
      "OpenSearch domains should have encryption at rest enabled",
      nattr("aws_opensearch_domain|aws_elasticsearch_domain", "encrypt_at_rest", "enabled", FALSE),
      R("aws_opensearch_domain", '  domain_name = "logs"\n\n  encrypt_at_rest {\n    enabled = false\n  }\n'),
      R("aws_opensearch_domain", '  domain_name = "logs"\n\n  encrypt_at_rest {\n    enabled = true\n  }\n'),
      "Indices, logs and snapshots are stored unencrypted. Enable encrypt_at_rest (it can only be set at domain creation on older engines).",
      applies=AWSP, cwe=["CWE-311"], owasp=["A02:2021", "A04:2025"], docv="AWS Security Hub User Guide")
cloud("AWS-ECR-MUTABLE-TAGS", "ECR repository allows tags to be overwritten", SH + "ecr-controls.html",
      "ECR private repositories should have tag immutability configured",
      attr("aws_ecr_repository", "image_tag_mutability", '^\\"MUTABLE\\"$'),
      R("aws_ecr_repository", '  name                 = "api"\n  image_tag_mutability = "MUTABLE"\n'),
      R("aws_ecr_repository", '  name                 = "api"\n  image_tag_mutability = "IMMUTABLE"\n'),
      "A pushed tag can be replaced, so the image deployed as api:1.4.2 tomorrow may not be the one you tested. Make tags immutable (or deploy by digest).",
      sev="minor", applies=AWSP, cwe=["CWE-494"], owasp=["A08:2021", "A08:2025"], docv="AWS Security Hub User Guide")
cloud("AWS-ECR-NO-SCAN", "ECR repository without image scanning on push", SH + "ecr-controls.html",
      "ECR private repositories should have image scanning configured",
      nattr("aws_ecr_repository", "image_scanning_configuration", "scan_on_push", FALSE),
      R("aws_ecr_repository", '  name = "api"\n\n  image_scanning_configuration {\n    scan_on_push = false\n  }\n'),
      R("aws_ecr_repository", '  name = "api"\n\n  image_scanning_configuration {\n    scan_on_push = true\n  }\n'),
      "Images with known vulnerable packages are accepted without a report. Enable scan_on_push (or registry-level enhanced scanning).",
      sev="minor", applies=AWSP, mode="ai-confirm", ai="Is there no registry-level (enhanced/Inspector) scanning configured elsewhere for this repository?",
      cwe=["CWE-1104"], owasp=["A06:2021", "A03:2025"], docv="AWS Security Hub User Guide")
cloud("AWS-LAMBDA-URL-NO-AUTH", "Lambda function URL without authentication", "https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html",
      "Using the NONE auth type", attr("aws_lambda_function_url", "authorization_type", '^\\"NONE\\"$'),
      R("aws_lambda_function_url", '  function_name      = aws_lambda_function.api.function_name\n  authorization_type = "NONE"\n'),
      R("aws_lambda_function_url", '  function_name      = aws_lambda_function.api.function_name\n  authorization_type = "AWS_IAM"\n'),
      "Anyone on the internet can invoke the function directly, bypassing API Gateway throttling, WAF and auth. Use AWS_IAM, or make sure the function authenticates every request itself.",
      applies=AWSP, mode="ai-confirm", ai="Is this function meant to be a public endpoint that authenticates requests itself (e.g. a signed webhook receiver)? Answer no if it is.",
      cwe=["CWE-306"], owasp=["A07:2021", "A07:2025"], docv="AWS Lambda Developer Guide")

# ------------------------------------------------------------------ Azure
cloud("AZURE-STORAGE-HTTP-ALLOWED", "Storage account accepts plain HTTP", "https://learn.microsoft.com/en-us/azure/storage/common/storage-require-secure-transfer",
      "When you require secure transfer, any requests originating from an insecure connection are rejected.",
      attr("azurerm_storage_account", "https_traffic_only_enabled|enable_https_traffic_only", FALSE),
      R("azurerm_storage_account", '  name                       = "appdata"\n  account_tier               = "Standard"\n  https_traffic_only_enabled = false\n'),
      R("azurerm_storage_account", '  name                       = "appdata"\n  account_tier               = "Standard"\n  https_traffic_only_enabled = true\n'),
      "Requests and shared-key/SAS credentials can travel unencrypted. Require secure transfer.",
      applies=AZP, cwe=["CWE-319"], owasp=["A02:2021", "A04:2025"], docv="Microsoft Learn (2026)")
cloud("AZURE-OLD-TLS", "Azure resource accepts TLS 1.0/1.1", "https://learn.microsoft.com/en-us/azure/app-service/overview-tls",
      "These are legacy protocols and are no longer considered secure.",
      attr("azurerm_storage_account|azurerm_mssql_server|azurerm_redis_cache|azurerm_postgresql_server|azurerm_mysql_server", "min_tls_version|minimum_tls_version|ssl_minimal_tls_version_enforced", '^\\"(TLS1_0|TLS1_1|1\\\\.0|1\\\\.1|TLS1_0|TLSEnforcementDisabled)\\"$')
      + "\n" + nattr("azurerm_linux_web_app|azurerm_windows_web_app|azurerm_linux_function_app|azurerm_windows_function_app|azurerm_app_service", "site_config", "minimum_tls_version|min_tls_version", '^\\"(1\\\\.0|1\\\\.1)\\"$'),
      R("azurerm_storage_account", '  name            = "appdata"\n  account_tier    = "Standard"\n  min_tls_version = "TLS1_0"\n'),
      R("azurerm_storage_account", '  name            = "appdata"\n  account_tier    = "Standard"\n  min_tls_version = "TLS1_2"\n'),
      "Clients may negotiate TLS 1.0/1.1, which lack modern ciphers and are deprecated. Set the minimum to TLS 1.2.",
      applies=AZP, cwe=["CWE-326", "CWE-757"], owasp=["A02:2021", "A04:2025"], docv="Microsoft Learn (2026)")
cloud("AZURE-STORAGE-PUBLIC-BLOBS", "Storage account allows anonymous blob access", "https://learn.microsoft.com/en-us/azure/storage/blobs/anonymous-read-access-prevent",
      "Microsoft recommends disallowing anonymous access for your storage accounts for optimal security.",
      attr("azurerm_storage_account", "allow_nested_items_to_be_public|allow_blob_public_access", TRUE),
      R("azurerm_storage_account", '  name                            = "appdata"\n  account_tier                    = "Standard"\n  allow_nested_items_to_be_public = true\n'),
      R("azurerm_storage_account", '  name                            = "appdata"\n  account_tier                    = "Standard"\n  allow_nested_items_to_be_public = false\n'),
      "Any container in the account can be switched to anonymous read, a common source of data leaks. Disallow it at the account level and serve public files through a CDN or SAS.",
      applies=AZP, mode="ai-confirm", ai="Is this account meant to serve public static content? Answer yes only if it clearly is.", cwe=["CWE-284"], owasp=["A01:2021", "A01:2025"],
      docv="Microsoft Learn (2026)")
cloud("AZURE-NSG-ADMIN-OPEN", "NSG allows SSH/RDP from the internet", "https://learn.microsoft.com/en-us/azure/security/fundamentals/network-best-practices",
      "Disable RDP and SSH access to virtual machines",
      '((block (identifier) @b (body) @match) (#match? @b "^(security_rule|resource)$") (#match? @match "access\\\\s*=\\\\s*\\"Allow\\"") (#match? @match "direction\\\\s*=\\\\s*\\"Inbound\\"") (#match? @match "source_address_prefix\\\\s*=\\\\s*\\"(\\\\*|Internet|0\\\\.0\\\\.0\\\\.0/0|Any)\\"") (#match? @match "destination_port_ranges?\\\\s*=\\\\s*\\\\[?[^\\\\n]*\\"(22|3389|\\\\*)\\""))',
      R("azurerm_network_security_rule", '  name                        = "ssh"\n  priority                    = 100\n  direction                   = "Inbound"\n  access                      = "Allow"\n  protocol                    = "Tcp"\n  source_port_range           = "*"\n  destination_port_range      = "22"\n  source_address_prefix       = "*"\n  destination_address_prefix  = "*"\n'),
      R("azurerm_network_security_rule", '  name                        = "ssh"\n  priority                    = 100\n  direction                   = "Inbound"\n  access                      = "Allow"\n  protocol                    = "Tcp"\n  source_port_range           = "*"\n  destination_port_range      = "22"\n  source_address_prefix       = var.admin_cidr\n  destination_address_prefix  = "*"\n'),
      "SSH/RDP open to the internet is scanned and brute-forced constantly. Restrict the source, or use Azure Bastion / just-in-time access.",
      sev="critical", applies=AZP, cwe=["CWE-284"], owasp=["A01:2021", "A01:2025"], docv="Microsoft Learn (2026)")
cloud("AZURE-SQL-FIREWALL-ALL", "SQL firewall rule opens the whole internet", "https://learn.microsoft.com/en-us/azure/azure-sql/database/firewall-configure",
      "create a firewall rule with starting and ending IP addresses set to 0.0.0.0",
      '((block (identifier) @bt . (string_lit) @rt (body) @match) (#eq? @bt "resource") (#match? @rt "^.(azurerm_mssql_firewall_rule|azurerm_sql_firewall_rule|azurerm_postgresql_flexible_server_firewall_rule|azurerm_mysql_flexible_server_firewall_rule).$") (#match? @match "start_ip_address\\\\s*=\\\\s*\\"0\\\\.0\\\\.0\\\\.0\\"") (#match? @match "end_ip_address\\\\s*=\\\\s*\\"255\\\\.255\\\\.255\\\\.255\\""))',
      R("azurerm_mssql_firewall_rule", '  name             = "all"\n  server_id        = azurerm_mssql_server.db.id\n  start_ip_address = "0.0.0.0"\n  end_ip_address   = "255.255.255.255"\n'),
      R("azurerm_mssql_firewall_rule", '  name             = "office"\n  server_id        = azurerm_mssql_server.db.id\n  start_ip_address = "203.0.113.10"\n  end_ip_address   = "203.0.113.20"\n'),
      "Every IPv4 address may connect to the database server; only the password stands between the internet and the data. Allow specific ranges or use private endpoints.",
      sev="critical", applies=AZP, cwe=["CWE-284"], owasp=["A01:2021", "A01:2025"], docv="Microsoft Learn (2026)")
cloud("AZURE-KEYVAULT-NO-PURGE-PROTECTION", "Key Vault purge protection disabled", "https://learn.microsoft.com/en-us/azure/key-vault/general/soft-delete-overview",
      "Purge protection is an optional Key Vault behavior and is not enabled by default",
      attr("azurerm_key_vault", "purge_protection_enabled", FALSE),
      R("azurerm_key_vault", '  name                     = "app-kv"\n  sku_name                 = "standard"\n  purge_protection_enabled = false\n'),
      R("azurerm_key_vault", '  name                     = "app-kv"\n  sku_name                 = "standard"\n  purge_protection_enabled = true\n'),
      "A compromised admin (or a mistake) can permanently purge keys, making data encrypted with them unrecoverable. Enable purge protection for vaults holding encryption keys.",
      sev="minor", applies=AZP, mode="ai-confirm", ai="Does this vault hold keys or secrets whose loss would be unrecoverable (not a throwaway dev vault)?",
      cwe=["CWE-693"], owasp=["A04:2021", "A06:2025"], docv="Microsoft Learn (2026)")
cloud("AZURE-APP-HTTP-ALLOWED", "App Service accepts plain HTTP", "https://learn.microsoft.com/en-us/azure/app-service/overview-security",
      "Redirect all HTTP traffic to HTTPS by enabling HTTPS-only mode",
      attr("azurerm_linux_web_app|azurerm_windows_web_app|azurerm_linux_function_app|azurerm_windows_function_app|azurerm_app_service|azurerm_function_app", "https_only", FALSE),
      R("azurerm_linux_web_app", '  name       = "api"\n  https_only = false\n'),
      R("azurerm_linux_web_app", '  name       = "api"\n  https_only = true\n'),
      "The app answers on http:// too, so sessions and credentials can be read or modified on the network. Set https_only = true.",
      applies=AZP, cwe=["CWE-319"], owasp=["A02:2021", "A04:2025"], docv="Microsoft Learn (2026)")

# ------------------------------------------------------------------ Google Cloud
cloud("GCP-FIREWALL-ADMIN-OPEN", "Firewall allows SSH/RDP from 0.0.0.0/0", "https://cloud.google.com/vpc/docs/firewalls",
      "default-allow-ssh ingress 65534 0.0.0.0/0 allow tcp:22",
      '((block (identifier) @bt . (string_lit) @rt (body) @match) (#eq? @bt "resource") (#match? @rt "^.google_compute_firewall.$") (#match? @match "source_ranges\\\\s*=\\\\s*\\\\[[^\\\\]]*\\"0\\\\.0\\\\.0\\\\.0/0\\"") (#match? @match "ports\\\\s*=\\\\s*\\\\[[^\\\\]]*\\"(22|3389)\\"|protocol\\\\s*=\\\\s*\\"all\\"") (#not-match? @match "direction\\\\s*=\\\\s*\\"EGRESS\\""))',
      R("google_compute_firewall", '  name    = "allow-ssh"\n  network = google_compute_network.main.name\n\n  allow {\n    protocol = "tcp"\n    ports    = ["22"]\n  }\n\n  source_ranges = ["0.0.0.0/0"]\n'),
      R("google_compute_firewall", '  name    = "allow-ssh-iap"\n  network = google_compute_network.main.name\n\n  allow {\n    protocol = "tcp"\n    ports    = ["22"]\n  }\n\n  source_ranges = ["35.235.240.0/20"]\n'),
      "SSH/RDP open to the internet is brute-forced constantly. Restrict source_ranges, or use IAP TCP forwarding (35.235.240.0/20).",
      sev="critical", applies=GCPP, cwe=["CWE-284"], owasp=["A01:2021", "A01:2025"], docv="Google Cloud docs (2026)")
cloud("GCP-BUCKET-PUBLIC", "Cloud Storage bucket granted to allUsers/allAuthenticatedUsers", "https://cloud.google.com/storage/docs/access-control/making-data-public",
      "grant the principal allUsers the Storage Object Viewer",
      '((block (identifier) @bt . (string_lit) @rt (body (attribute (identifier) @an (expression) @match))) (#eq? @bt "resource") (#match? @rt "^.(google_storage_bucket_iam_member|google_storage_bucket_iam_binding|google_storage_object_access_control|google_storage_bucket_access_control|google_storage_default_object_access_control).$") (#match? @an "^(member|members|entity)$") (#match? @match "allUsers|allAuthenticatedUsers"))',
      R("google_storage_bucket_iam_member", '  bucket = google_storage_bucket.reports.name\n  role   = "roles/storage.objectViewer"\n  member = "allUsers"\n'),
      R("google_storage_bucket_iam_member", '  bucket = google_storage_bucket.reports.name\n  role   = "roles/storage.objectViewer"\n  member = "serviceAccount:${google_service_account.app.email}"\n'),
      "Everyone on the internet can read (or list) the bucket's objects. Grant specific principals, or serve public files through a CDN with signed URLs.",
      applies=GCPP, mode="ai-confirm", ai="Is this bucket meant to host public content (a static site or public downloads)? Answer yes only if it clearly is.",
      cwe=["CWE-284"], owasp=["A01:2021", "A01:2025"], docv="Google Cloud docs (2026)")
cloud("GCP-SQL-SSL-OPTIONAL", "Cloud SQL accepts unencrypted connections", "https://cloud.google.com/sql/docs/mysql/configure-ssl-instance",
      "ALLOW_UNENCRYPTED_AND_ENCRYPTED allows non-SSL/non-TLS and SSL/TLS connections.",
      nattr("google_sql_database_instance", "ip_configuration", "ssl_mode|require_ssl", '^(false|\\"ALLOW_UNENCRYPTED_AND_ENCRYPTED\\")$')
      + "\n" + '((block (identifier) @bt . (string_lit) @rt (body (block (identifier) @s (body (block (identifier) @nb (body (attribute (identifier) @an (expression) @val) @match)))))) (#eq? @bt "resource") (#match? @rt "^.google_sql_database_instance.$") (#eq? @s "settings") (#eq? @nb "ip_configuration") (#match? @an "^(ssl_mode|require_ssl)$") (#match? @val "^(false|\\"ALLOW_UNENCRYPTED_AND_ENCRYPTED\\")$"))',
      R("google_sql_database_instance", '  name             = "main"\n  database_version = "POSTGRES_17"\n\n  settings {\n    tier = "db-f1-micro"\n\n    ip_configuration {\n      ssl_mode = "ALLOW_UNENCRYPTED_AND_ENCRYPTED"\n    }\n  }\n'),
      R("google_sql_database_instance", '  name             = "main"\n  database_version = "POSTGRES_17"\n\n  settings {\n    tier = "db-f1-micro"\n\n    ip_configuration {\n      ssl_mode = "ENCRYPTED_ONLY"\n    }\n  }\n'),
      "Clients may connect without TLS, sending credentials and query results in clear text. Use ssl_mode = \"ENCRYPTED_ONLY\" (or TRUSTED_CLIENT_CERTIFICATE_REQUIRED).",
      applies=GCPP, cwe=["CWE-319"], owasp=["A02:2021", "A04:2025"], docv="Google Cloud docs (2026)")
cloud("GCP-SERIAL-PORT-ENABLED", "Interactive serial console enabled", "https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-using-serial-console",
      "The interactive serial console does not support IP-based access restrictions such as IP allowlists",
      '((block (identifier) @bt . (string_lit) @rt (body (attribute (identifier) @an (expression) @match))) (#eq? @bt "resource") (#match? @rt "^.(google_compute_instance|google_compute_instance_template|google_compute_project_metadata|google_compute_project_metadata_item).$") (#match? @an "^(metadata|key)$") (#match? @match "serial-port-enable\\"?\\\\s*[=:]\\\\s*\\"?(true|TRUE|1)"))',
      R("google_compute_instance", '  name         = "vm"\n  machine_type = "e2-small"\n  metadata = {\n    "serial-port-enable" = "true"\n  }\n'),
      R("google_compute_instance", '  name         = "vm"\n  machine_type = "e2-small"\n  metadata = {\n    "enable-oslogin" = "TRUE"\n  }\n'),
      "The serial console is reachable from anywhere and bypasses VPC firewall rules; only IAM and the OS login protect it. Leave it off and enable it temporarily for debugging.",
      sev="minor", applies=GCPP, cwe=["CWE-284"], owasp=["A05:2021", "A02:2025"], docv="Google Cloud docs (2026)")
cloud("GCP-GKE-LEGACY-ABAC", "GKE legacy ABAC enabled", "https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster",
      "Leave ABAC disabled", attr("google_container_cluster", "enable_legacy_abac", TRUE),
      R("google_container_cluster", '  name               = "prod"\n  location           = "europe-north1"\n  enable_legacy_abac = true\n'),
      R("google_container_cluster", '  name               = "prod"\n  location           = "europe-north1"\n  enable_legacy_abac = false\n'),
      "Legacy ABAC grants broad static permissions that RBAC policies cannot narrow. Disable it and use RBAC.",
      applies=GCPP, cwe=["CWE-284"], owasp=["A01:2021", "A01:2025"], docv="Google Cloud docs (2026)")
cloud("GCP-GKE-CLIENT-CERT", "GKE issues a legacy client certificate", "https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster",
      "Leave legacy client authentication methods disabled",
      '((block (identifier) @bt . (string_lit) @rt (body (block (identifier) @nb (body (block (identifier) @cc (body (attribute (identifier) @an (expression) @val) @match)))))) (#eq? @bt "resource") (#match? @rt "^.google_container_cluster.$") (#eq? @nb "master_auth") (#eq? @cc "client_certificate_config") (#eq? @an "issue_client_certificate") (#eq? @val "true"))',
      R("google_container_cluster", '  name     = "prod"\n  location = "europe-north1"\n\n  master_auth {\n    client_certificate_config {\n      issue_client_certificate = true\n    }\n  }\n'),
      R("google_container_cluster", '  name     = "prod"\n  location = "europe-north1"\n\n  master_auth {\n    client_certificate_config {\n      issue_client_certificate = false\n    }\n  }\n'),
      "The cluster issues a long-lived admin client certificate that cannot be revoked. Disable it and authenticate with IAM/OIDC.",
      applies=GCPP, cwe=["CWE-287"], owasp=["A07:2021", "A07:2025"], docv="Google Cloud docs (2026)")
cloud("GCP-PRIMITIVE-ROLE", "Basic role (owner/editor) granted on a project/folder/org", "https://cloud.google.com/iam/docs/roles-overview",
      "In production environments, do not grant basic roles unless there is no alternative.",
      '((block (identifier) @bt . (string_lit) @rt (body (attribute (identifier) @an (expression) @match))) (#eq? @bt "resource") (#match? @rt "^.google_(project|folder|organization)_iam_(member|binding).$") (#eq? @an "role") (#match? @match "^\\"roles/(owner|editor)\\"$"))',
      R("google_project_iam_member", '  project = var.project\n  role    = "roles/editor"\n  member  = "serviceAccount:${google_service_account.app.email}"\n'),
      R("google_project_iam_member", '  project = var.project\n  role    = "roles/storage.objectAdmin"\n  member  = "serviceAccount:${google_service_account.app.email}"\n'),
      "Owner/Editor include thousands of permissions across every service, so a leaked credential for this principal compromises the whole project. Grant predefined or custom roles scoped to the job.",
      applies=GCPP, mode="ai-confirm", ai="Is the member a workload/service account or broad group rather than a small break-glass admin group?",
      cwe=["CWE-250"], owasp=["A01:2021", "A01:2025"], docv="Google Cloud docs (2026)")

RULES = P.R

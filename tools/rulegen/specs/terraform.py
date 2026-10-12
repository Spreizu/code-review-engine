"""Terraform pack (official tree-sitter-hcl grammar) for *.tf. Version-aware on `terraform` (required_version /
.terraform-version) and `tf-provider.<name>` (required_providers / .terraform.lock.hcl), e.g. AWS provider 4/5/6
upgrade-guide removals. Sources: developer.hashicorp.com Terraform language docs + style guide, TFLint terraform
ruleset docs, terraform-provider-aws docs/upgrade guides, AWS service documentation."""
from specs._common import Pack, secret_rules

L = "https://developer.hashicorp.com/terraform/language/"
TFL = "https://raw.githubusercontent.com/terraform-linters/tflint-ruleset-terraform/main/docs/rules/"
TFLR = TFL + "README.md"
AWSD = "https://raw.githubusercontent.com/hashicorp/terraform-provider-aws/main/website/docs/"
V4, V5, V6 = (AWSD + f"guides/version-{n}-upgrade.html.markdown" for n in (4, 5, 6))
P = Pack("TF", "hcl", "Terraform 1.16", {"terraform": "*"}, files=["**/*.tf"])
TFLV = "tflint-ruleset-terraform 0.13"
AWS = "tf-provider.aws"


def R(rtype, body, name="this", kind="resource"):
    return f'{kind} "{rtype}" "{name}" {{\n{body}}}\n'


def blk(bt, extra="", label=None):
    """Top-level block of type bt (resource/data/module/variable/...), optional first-label regex."""
    lab = f' (#match? @rt "^.({label}).$")' if label else ""
    lt = " . (string_lit) @rt" if label else ""
    return f'((block (identifier) @bt{lt}) @match (#eq? @bt "{bt}"){lab}{extra})'


def attr(bt, label, name_re, val_pred="", cap="@match"):
    """attribute `name_re = <expr>` directly in a bt block whose first label matches label."""
    lt = " . (string_lit) @rt" if label else ""
    lab = f' (#match? @rt "^.({label}).$")' if label else ""
    return (f'((block (identifier) @bt{lt} (body (attribute (identifier) @an (expression) @val) {cap})) '
            f'(#eq? @bt "{bt}"){lab} (#match? @an "^({name_re})$"){val_pred})')


def nested(bt, label, name_re, extra=""):
    lt = " . (string_lit) @rt" if label else ""
    lab = f' (#match? @rt "^.({label}).$")' if label else ""
    return (f'((block (identifier) @bt{lt} (body (block (identifier) @nb) @match)) (#eq? @bt "{bt}"){lab} '
            f'(#match? @nb "^({name_re})$"){extra})')


# ------------------------------------------------------------------ language: deprecated syntax (TFLint recommended)
P("DEPRECATED-INTERPOLATION", "Interpolation-only expression \"${...}\"", TFLR, "Disallow deprecated (0.11-style) interpolation",
  '(expression (template_expr (quoted_template . (quoted_template_start) . (template_interpolation) . (quoted_template_end)))) @match',
  R("aws_instance", '  ami = "${var.ami}"\n'), R("aws_instance", "  ami = var.ami\n"),
  "Since 0.12 expressions are first-class; write var.ami instead of \"${var.ami}\".", sev="minor", kind="deprecation", cat="modernization",
  applies={"terraform": ">=0.12"}, docv=TFLV, xref=[L + "expressions/strings"])
P("DEPRECATED-INDEX", "Legacy dot index (foo.0)", TFL + "terraform_deprecated_index.md",
  "However, for backward compatibility, Terraform continues to support accessing list items with the dot syntax normally used for attributes.",
  '(index (legacy_index)) @match', 'output "id" {\n  value = aws_instance.web.0.id\n}\n', 'output "id" {\n  value = aws_instance.web[0].id\n}\n',
  "Use square-bracket indexing (web[0]).", sev="minor", kind="deprecation", cat="modernization", docv=TFLV)
P("LEGACY-SPLAT", "Legacy attribute-only splat (.*.)", L + "expressions/splat", "Legacy (Attribute-only) Splat Expressions",
  '(splat (attr_splat)) @match', 'output "ids" {\n  value = aws_instance.web.*.id\n}\n', 'output "ids" {\n  value = aws_instance.web[*].id\n}\n',
  "The legacy splat stops at the first index operator; use the full splat [*].", sev="info", kind="deprecation", cat="modernization", xref=[TFL + "terraform_deprecated_index.md"])
P("DEPRECATED-LOOKUP", "lookup() with only two arguments", L + "functions/lookup", "omitting default is deprecated since v0.7",
  '((function_call (identifier) @f (function_arguments . (expression) . (expression) .)) @match (#eq? @f "lookup"))',
  'locals {\n  ami = lookup(var.amis, "us-east-1")\n}\n', 'locals {\n  ami = var.amis["us-east-1"]\n}\n',
  "Use index syntax map[key] (or pass a default).", sev="minor", kind="deprecation", cat="modernization", xref=[TFLR])
P("LIST-MAP-FUNCTIONS", "list()/map() functions (removed)", L + "functions/list",
  "Prior to Terraform v0.12 it was the only available syntax for writing a literal list inside an expression",
  '((function_call (identifier) @f) @match (#match? @f "^(list|map)$"))',
  'locals {\n  zones = list("a", "b")\n}\n', 'locals {\n  zones = ["a", "b"]\n}\n',
  "list()/map() no longer exist; use [ ... ] / { ... } literals (or tolist/tomap).", sev="major", kind="removal", cat="compatibility",
  applies={"terraform": ">=0.15"}, xref=[L + "functions/map"])
P("COMMENT-SYNTAX", "// comment instead of #", TFLR, "Disallow `//` comments in favor of `#`",
  '((comment) @match (#match? @match "^//"))', '// main network\nlocals {\n  a = 1\n}\n', '# main network\nlocals {\n  a = 1\n}\n',
  "Use # for comments (idiomatic; terraform fmt style).", sev="info", kind="best-practice", cat="style", docv=TFLV, xref=[L + "style"])
P("EMPTY-LIST-EQUALITY", "Comparison with [] to test emptiness", TFL + "terraform_empty_list_equality.md",
  "operator can only return true when the two operands have identical types",
  r'((binary_operation (collection_value (tuple . (tuple_start) . (tuple_end)))) @match (#match? @match "(==|!=)"))',
  'locals {\n  none = var.subnets == []\n}\n', 'locals {\n  none = length(var.subnets) == 0\n}\n',
  "x == [] compares against an empty tuple type and is almost always false; use length(x) == 0.", sev="major", kind="anti-pattern", cat="correctness",
  docv=TFLV)
P("MAP-DUPLICATE-KEYS", "Duplicate key in an object/map literal", TFL + "terraform_map_duplicate_keys.md",
  "In the Terraform language, duplicate map keys are overwritten rather than throwing an error.",
  '((object (object_elem key: (expression) @a) (object_elem key: (expression) @b) @match) (#eq? @a @b))',
  'locals {\n  tags = {\n    env  = "prod"\n    team = "core"\n    env  = "dev"\n  }\n}\n', 'locals {\n  tags = {\n    env  = "prod"\n    team = "core"\n  }\n}\n',
  "The later key silently wins; remove the duplicate.", sev="major", kind="anti-pattern", cat="correctness", docv=TFLV)

# ------------------------------------------------------------------ modules / versions / providers
P("MODULE-PINNED-SOURCE", "Git/Mercurial module source without a pinned ref", TFL + "terraform_module_pinned_source.md",
  "If you do not pin the revision to use, the dependency you require may introduce unexpected breaking changes.",
  attr("module", None, "source", r' (#match? @val "^.(git::|hg::|git@|github[.]com/|bitbucket[.]org/)") (#not-match? @val "[?&]ref=")'),
  'module "vpc" {\n  source = "git::https://example.com/vpc.git"\n}\n', 'module "vpc" {\n  source = "git::https://example.com/vpc.git?ref=v1.2.0"\n}\n',
  "Unpinned VCS modules change under you (supply-chain risk); pin ?ref= to a tag or commit SHA.", sev="major", kind="security", cat="supply-chain", docv=TFLV)
P("MODULE-MUTABLE-REF", "Module pinned to a branch", TFL + "terraform_module_pinned_source.md", "Pinning to a mutable reference, such as a bra",
  attr("module", None, "source", r' (#match? @val "[?&]ref=(main|master|develop|dev|trunk|HEAD)([&\"]|$)")'),
  'module "vpc" {\n  source = "git::https://example.com/vpc.git?ref=main"\n}\n', 'module "vpc" {\n  source = "git::https://example.com/vpc.git?ref=v1.2.0"\n}\n',
  "A branch ref is not a pin; use a tag or commit SHA.", sev="minor", kind="security", cat="supply-chain", docv=TFLV, quote="Pinning to a mutable reference, such as a branch")
P("MODULE-VERSION", "Registry module without version", TFLR, "Checks that Terraform modules sourced from a registry specify a version",
  r'((block (identifier) @bt (body (attribute (identifier) @an (expression) @val))) @match (#eq? @bt "module") (#eq? @an "source") (#match? @val "^.[A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+.$") (#not-match? @match "\\bversion\\s*="))',
  'module "vpc" {\n  source = "terraform-aws-modules/vpc/aws"\n}\n', 'module "vpc" {\n  source  = "terraform-aws-modules/vpc/aws"\n  version = "~> 6.0"\n}\n',
  "Without version every init may pull a new major; constrain it.", sev="major", kind="best-practice", cat="supply-chain", docv=TFLV,
  xref=[L + "expressions/version-constraints"])
P("REQUIRED-VERSION", "terraform block without required_version", TFLR, "Disallow `terraform` declarations without require_version",
  r'((block (identifier) @bt) @match (#eq? @bt "terraform") (#not-match? @match "required_version"))',
  'terraform {\n  required_providers {\n    aws = {\n      source  = "hashicorp/aws"\n      version = "~> 6.0"\n    }\n  }\n}\n',
  'terraform {\n  required_version = ">= 1.9"\n  required_providers {\n    aws = {\n      source  = "hashicorp/aws"\n      version = "~> 6.0"\n    }\n  }\n}\n',
  "Pin the Terraform CLI range so older/newer binaries can't misapply the config.", sev="minor", kind="best-practice", cat="compatibility", docv=TFLV)
P("REQUIRED-PROVIDERS-VERSION", "Provider in required_providers without version", TFL + "terraform_required_providers.md",
  "For production use, you should constrain the acceptable provider versions via configuration",
  r'((block (identifier) @rp (body (attribute (identifier) (expression (collection_value (object) @o))) @match)) (#eq? @rp "required_providers") (#not-match? @o "\\bversion\\s*="))',
  'terraform {\n  required_providers {\n    aws = {\n      source = "hashicorp/aws"\n    }\n  }\n}\n',
  'terraform {\n  required_providers {\n    aws = {\n      source  = "hashicorp/aws"\n      version = "~> 6.0"\n    }\n  }\n}\n',
  "Unconstrained providers upgrade to new majors with breaking changes on the next init.", sev="major", kind="best-practice", cat="supply-chain", docv=TFLV)
P("REQUIRED-PROVIDERS-LEGACY-STRING", "required_providers entry as bare version string (no source)", L + "providers/requirements",
  "Each Terraform module must declare which providers it requires",
  r'((block (identifier) @rp (body (attribute (identifier) (expression (literal_value (string_lit))) ) @match)) (#eq? @rp "required_providers"))',
  'terraform {\n  required_providers {\n    aws = "~> 3.0"\n  }\n}\n', 'terraform {\n  required_providers {\n    aws = {\n      source  = "hashicorp/aws"\n      version = "~> 3.0"\n    }\n  }\n}\n',
  "Since 0.13 use the object form with source (namespace/name) and version.", sev="minor", kind="deprecation", cat="modernization",
  applies={"terraform": ">=0.13"})
P("PROVIDER-VERSION-ARGUMENT", "version argument in a provider block", L + "providers/configuration",
  "version A version constraint for the provider. This argument is deprecated.",
  attr("provider", None, "version"), 'provider "aws" {\n  region  = "eu-north-1"\n  version = "~> 5.0"\n}\n', 'provider "aws" {\n  region = "eu-north-1"\n}\n',
  "Move version constraints to terraform { required_providers { ... } }.", sev="minor", kind="deprecation", cat="modernization", applies={"terraform": ">=0.13"})
P("WORKSPACE-REMOTE", "terraform.workspace with a remote backend", TFLR, "should not be used with a \"remote\" backend with remote execution in Terraform v1.0.x",
  r'((expression (variable_expr (identifier) @t) (get_attr (identifier) @w)) @match (#eq? @t "terraform") (#eq? @w "workspace"))',
  'terraform {\n  backend "remote" {\n    organization = "acme"\n  }\n}\n\nlocals {\n  env = terraform.workspace\n}\n',
  'terraform {\n  backend "remote" {\n    organization = "acme"\n  }\n}\n\nlocals {\n  env = var.environment\n}\n',
  "Remote execution always reports \"default\"; pass the environment as a variable.", sev="minor", kind="anti-pattern", cat="correctness",
  filters=[r'file.has_re:backend\s+"remote"'], applies={"terraform": "<1.1.0"}, docv=TFLV,
  quote="`terraform.workspace` should not be used with a \"remote\" backend with remote execution in Terraform v1.0.x")

# ------------------------------------------------------------------ variables / outputs / style
P("TYPED-VARIABLES", "variable without type", TFLR, "Disallow `variable` declarations without type",
  r'((block (identifier) @bt) @match (#eq? @bt "variable") (#not-match? @match "\\btype\\s*="))',
  'variable "instance_count" {\n  default = 1\n}\n', 'variable "instance_count" {\n  type    = number\n  default = 1\n}\n',
  "Declare a type so bad inputs fail at plan time with a clear error.", sev="minor", kind="best-practice", cat="correctness", docv=TFLV, xref=[L + "style"])
P("DOCUMENTED-VARIABLES", "variable without description", TFLR, "Disallow `variable` declarations without description",
  r'((block (identifier) @bt) @match (#eq? @bt "variable") (#not-match? @match "\\bdescription\\s*="))',
  'variable "region" {\n  type = string\n}\n', 'variable "region" {\n  type        = string\n  description = "AWS region to deploy into."\n}\n',
  "Describe every variable (shown in docs, registry and prompts).", sev="info", kind="best-practice", cat="maintainability", docv=TFLV, xref=[L + "style"])
P("DOCUMENTED-OUTPUTS", "output without description", TFLR, "Disallow `output` declarations without description",
  r'((block (identifier) @bt) @match (#eq? @bt "output") (#not-match? @match "\\bdescription\\s*="))',
  'output "vpc_id" {\n  value = aws_vpc.main.id\n}\n', 'output "vpc_id" {\n  description = "ID of the main VPC."\n  value       = aws_vpc.main.id\n}\n',
  "Describe every output.", sev="info", kind="best-practice", cat="maintainability", docv=TFLV)
SECRET_NAME = "(?i)(password|passwd|secret|token|api_?key|private_?key|credentials?)"
P("SENSITIVE-VARIABLE", "Secret-looking variable not marked sensitive", L + "values/variables",
  "use the sensitive argument to prevent Terraform from displaying the value in CLI output",
  rf'((block (identifier) @bt . (string_lit) @n) @match (#eq? @bt "variable") (#match? @n "{SECRET_NAME}") (#not-match? @match "sensitive\\s*=\\s*true"))',
  'variable "db_password" {\n  type = string\n}\n', 'variable "db_password" {\n  type      = string\n  sensitive = true\n}\n',
  "Mark secrets sensitive so they're redacted from plan/apply output.", sev="major", kind="security", cat="security")
P("SENSITIVE-OUTPUT", "Secret-looking output not marked sensitive", L + "values/outputs",
  "use the sensitive argument to prevent Terraform from displaying the value in CLI output",
  rf'((block (identifier) @bt . (string_lit) @n) @match (#eq? @bt "output") (#match? @n "{SECRET_NAME}") (#not-match? @match "sensitive\\s*=\\s*true"))',
  'output "db_password" {\n  value = random_password.db.result\n}\n', 'output "db_password" {\n  value     = random_password.db.result\n  sensitive = true\n}\n',
  "Mark secret outputs sensitive.", sev="major", kind="security", cat="security")
P("SECRET-VARIABLE-DEFAULT", "Secret variable with a literal default", L + "values/variables",
  "use the sensitive argument to prevent Terraform from displaying the value in CLI output",
  rf'((block (identifier) @bt . (string_lit) @n (body (attribute (identifier) @an (expression (literal_value (string_lit) @match))))) (#eq? @bt "variable") (#match? @n "{SECRET_NAME}") (#eq? @an "default") (#not-match? @match "^.\\s*.$"))',
  'variable "db_password" {\n  type      = string\n  sensitive = true\n  default   = "hunter2!"\n}\n', 'variable "db_password" {\n  type      = string\n  sensitive = true\n}\n',
  "A committed default is a committed secret; supply it via TF_VAR_*, a secret manager or ephemeral input.", sev="critical", kind="security", cat="security")
P("EPHEMERAL-SECRET-VARIABLE", "Secret variable could be ephemeral", L + "values/variables",
  "ephemeral argument to your variable configuration to omit the variable from state and plan files.",
  rf'((block (identifier) @bt . (string_lit) @n) @match (#eq? @bt "variable") (#match? @n "{SECRET_NAME}") (#not-match? @match "ephemeral\\s*=\\s*true"))',
  'variable "db_password" {\n  type      = string\n  sensitive = true\n}\n', 'variable "db_password" {\n  type      = string\n  sensitive = true\n  ephemeral = true\n}\n',
  "Terraform 1.10+ can keep secrets out of state/plan entirely (ephemeral vars + write-only arguments).", sev="info", kind="modernization", cat="security",
  applies={"terraform": ">=1.10"}, mode="ai-confirm", ai="Is the value only passed to write-only/ephemeral contexts (so ephemeral = true is possible)?")
P("BACKEND-CREDENTIALS", "Credentials hard-coded in backend block", L + "settings/backends/configuration",
  "we do not recommend including access credentials directly in the configuration",
  r'((block (identifier) @bt (body (block (identifier) @b (body (attribute (identifier) @an (expression (literal_value (string_lit))) @match))))) (#eq? @bt "terraform") (#match? @b "^(backend|cloud)$") (#match? @an "^(access_key|secret_key|token|password|client_secret|sas_token|access_token|credentials)$"))',
  'terraform {\n  backend "s3" {\n    bucket     = "tf-state"\n    access_key = "AKIAEXAMPLE"\n    secret_key = "abc123"\n  }\n}\n',
  'terraform {\n  backend "s3" {\n    bucket = "tf-state"\n  }\n}\n',
  "Backend credentials end up in .terraform/ and VCS; use env vars/credentials files.", sev="critical", kind="security", cat="security")
P("RESOURCE-NAME-DASHES", "Resource/data name with dashes", L + "style", "underscores to separate multiple words in names.",
  r'((block (identifier) @bt . (string_lit) . (string_lit) @match) (#match? @bt "^(resource|data)$") (#match? @match "-"))',
  R("aws_instance", "  ami = var.ami\n", name="web-server"), R("aws_instance", "  ami = var.ami\n", name="web_server"),
  "Use lower_snake_case names (style guide).", sev="info", kind="best-practice", cat="style")
P("RESOURCE-NAME-REPEATS-TYPE", "Resource name repeats the provider/type prefix", L + "style",
  "Use nouns for resource names and do not include the resource type in the name.",
  r'((block (identifier) @bt . (string_lit) . (string_lit) @match) (#match? @bt "^(resource|data)$") (#match? @match "^.(aws|azurerm|google|kubernetes|helm)_"))',
  R("aws_instance", "  ami = var.ami\n", name="aws_instance_web"), R("aws_instance", "  ami = var.ami\n", name="web"),
  "Name resources with nouns (web, main) — the type is already in the address.", sev="info", kind="best-practice", cat="style")

# ------------------------------------------------------------------ meta-arguments / design
P("PROVISIONER-USED", "Provisioner (post-apply side effects)", L + "resources/provisioners/syntax",
  "so we strongly recommend using purpose-built solutions to perform post-apply operations",
  r'((block (identifier) @p . (string_lit) @t) @match (#eq? @p "provisioner") (#match? @t "(local-exec|remote-exec|file)"))',
  R("aws_instance", '  ami = var.ami\n\n  provisioner "remote-exec" {\n    inline = ["sudo apt-get install -y nginx"]\n  }\n'),
  R("aws_instance", "  ami       = var.ami\n  user_data = file(\"${path.module}/init.sh\")\n"),
  "Provisioners aren't modeled in plan, break idempotency and can't be imported; prefer user_data/cloud-init, images or provider features.",
  sev="minor", kind="best-practice", cat="maintainability", mode="ai-confirm", ai="Is there a purpose-built alternative (user_data, image build, provider resource)?")
P("NULL-RESOURCE", "null_resource (use terraform_data)", L + "resources/terraform-data",
  "triggering provisioners when there is no other logical managed resource in which to place them",
  blk("resource", label="null_resource"), R("null_resource", "  triggers = {\n    v = var.version\n  }\n", name="deploy"),
  R("terraform_data", "  triggers_replace = [var.version]\n", name="deploy"),
  "terraform_data (1.4+) is built in — no hashicorp/null provider needed.", sev="info", kind="modernization", cat="modernization",
  applies={"terraform": ">=1.4"})
P("REMOTE-STATE-DATA", "terraform_remote_state data source", L + "state/remote-state-data",
  "The tfe_outputs data source is more secure because it does not require full access to workspace state",
  blk("data", label="terraform_remote_state"),
  R("terraform_remote_state", '  backend = "s3"\n  config = {\n    bucket = "tf-state"\n    key    = "net.tfstate"\n  }\n', name="net", kind="data"),
  'data "aws_ssm_parameter" "vpc_id" {\n  name = "/net/vpc_id"\n}\n',
  "Remote state access grants read of the whole state (incl. secrets); publish needed values explicitly (SSM, tfe_outputs).",
  sev="minor", kind="security", cat="security", mode="ai-confirm", ai="Does the consumer need read access to the full producer state?")
P("DEPENDS-ON-LAST-RESORT", "Explicit depends_on", L + "meta-arguments/depends_on",
  "last resort because it can cause Terraform to create more conservative plans that replace more resources than necessary.",
  attr("resource", None, "depends_on"), R("aws_instance", "  ami        = var.ami\n  depends_on = [aws_s3_bucket.logs]\n"),
  R("aws_instance", "  ami = var.ami\n  iam_instance_profile = aws_iam_instance_profile.app.name\n"),
  "Prefer implicit dependencies via references; depends_on makes plans more conservative.", sev="info", kind="best-practice", cat="maintainability",
  mode="ai-confirm", ai="Is there a hidden dependency that no attribute reference can express?")
P("DYNAMIC-BLOCK-OVERUSE", "dynamic block over a literal collection", L + "expressions/dynamic-blocks",
  "Overuse of dynamic blocks can make configuration hard to read and maintain",
  r'((block (identifier) @d (body (attribute (identifier) @fe (expression (collection_value)))) ) @match (#eq? @d "dynamic") (#eq? @fe "for_each"))',
  R("aws_security_group", '  dynamic "ingress" {\n    for_each = [443]\n    content {\n      from_port = ingress.value\n      to_port   = ingress.value\n      protocol  = "tcp"\n    }\n  }\n'),
  R("aws_security_group", '  ingress {\n    from_port = 443\n    to_port   = 443\n    protocol  = "tcp"\n  }\n'),
  "Write nested blocks literally when the collection is static.", sev="info", kind="best-practice", cat="maintainability")
P("IGNORE-CHANGES-ALL", "lifecycle ignore_changes = all", L + "meta-arguments/lifecycle", "Use the ignore_changes argument when a resource is c",
  r'((block (identifier) @l (body (attribute (identifier) @a (expression (variable_expr (identifier) @v))) @match)) (#eq? @l "lifecycle") (#eq? @a "ignore_changes") (#eq? @v "all"))',
  R("aws_instance", "  ami = var.ami\n\n  lifecycle {\n    ignore_changes = all\n  }\n"),
  R("aws_instance", "  ami = var.ami\n\n  lifecycle {\n    ignore_changes = [tags]\n  }\n"),
  "ignore_changes = all hides every drift, including security-relevant changes; list the specific attributes.", sev="minor",
  kind="best-practice", cat="correctness", quote="Use the ignore_changes argument when a resource is created with references to data that may change in the future")

# ------------------------------------------------------------------ AWS provider: credentials and security
P("AWS-PROVIDER-HARDCODED-CREDENTIALS", "Static credentials in provider \"aws\"", AWSD + "index.html.markdown",
  "Hard-coded credentials are not recommended in any Terraform configuration and risks secret leakage",
  attr("provider", None, "access_key|secret_key|token", r' (#match? @val "^.[A-Za-z0-9/+=]{8,}.$")'),
  'provider "aws" {\n  region     = "eu-north-1"\n  access_key = "AKIAIOSFODNN7EXAMPLE"\n  secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n}\n',
  'provider "aws" {\n  region = "eu-north-1"\n}\n', "Use env vars, shared config/SSO or an assumed role; rotate the leaked key.",
  sev="critical", kind="security", cat="security", docv="AWS provider 6.x")
P("AWS-S3-PUBLIC-ACL", "S3 public canned ACL", "https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html",
  "we recommend that you turn on all four settings for block public access for your account.",
  attr("resource", "aws_s3_bucket|aws_s3_bucket_acl|aws_s3_object", "acl", r' (#match? @val "public-read|authenticated-read")'),
  R("aws_s3_bucket_acl", '  bucket = aws_s3_bucket.site.id\n  acl    = "public-read"\n'), R("aws_s3_bucket_acl", '  bucket = aws_s3_bucket.site.id\n  acl    = "private"\n'),
  "Public ACLs expose objects to the internet; keep Block Public Access on and serve via CloudFront OAC.", sev="critical", kind="security", cat="security",
  docv="Amazon S3 User Guide")
P("AWS-S3-PUBLIC-ACCESS-BLOCK-OFF", "S3 Block Public Access setting disabled", "https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html",
  "we recommend that you turn on all four settings for block public access for your account.",
  attr("resource", "aws_s3_bucket_public_access_block|aws_s3_account_public_access_block", "block_public_acls|block_public_policy|ignore_public_acls|restrict_public_buckets",
       r' (#eq? @val "false")'),
  R("aws_s3_bucket_public_access_block", "  bucket                  = aws_s3_bucket.b.id\n  block_public_acls       = false\n  block_public_policy     = true\n  ignore_public_acls      = true\n  restrict_public_buckets = true\n"),
  R("aws_s3_bucket_public_access_block", "  bucket                  = aws_s3_bucket.b.id\n  block_public_acls       = true\n  block_public_policy     = true\n  ignore_public_acls      = true\n  restrict_public_buckets = true\n"),
  "Turn on all four Block Public Access settings.", sev="major", kind="security", cat="security", docv="Amazon S3 User Guide")
P("AWS-SG-ADMIN-PORT-OPEN", "SSH/RDP open to 0.0.0.0/0", "https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html",
  "This rule allows inbound SSH traffic from the instances associated with sg-0abcdef1234567890.",
  r'((block (identifier) @i (body) @b) @match (#eq? @i "ingress") (#match? @b "0[.]0[.]0[.]0/0|::/0") (#match? @b "from_port\\s*=\\s*(22|3389|0)\\b|protocol\\s*=\\s*.-1."))'
  '\n'
  r'((block (identifier) @bt . (string_lit) @rt (body) @b) @match (#eq? @bt "resource") (#match? @rt "^.(aws_vpc_security_group_ingress_rule|aws_security_group_rule).$") (#match? @b "0[.]0[.]0[.]0/0|::/0") (#match? @b "from_port\\s*=\\s*(22|3389)\\b|ip_protocol\\s*=\\s*.-1.|protocol\\s*=\\s*.-1.") (#not-match? @b "type\\s*=\\s*.egress."))',
  R("aws_security_group", '  name = "bastion"\n\n  ingress {\n    from_port   = 22\n    to_port     = 22\n    protocol    = "tcp"\n    cidr_blocks = ["0.0.0.0/0"]\n  }\n'),
  R("aws_security_group", '  name = "bastion"\n\n  ingress {\n    from_port   = 22\n    to_port     = 22\n    protocol    = "tcp"\n    cidr_blocks = [var.admin_cidr]\n  }\n'),
  "Admin ports open to the internet are brute-forced constantly; restrict sources (or use SSM Session Manager).", sev="critical", kind="security",
  cat="security", docv="Amazon VPC User Guide")
P("AWS-RDS-PUBLICLY-ACCESSIBLE", "RDS instance publicly accessible", "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html",
  "If you want your DB instance in the VPC to be publicly accessible",
  attr("resource", "aws_db_instance|aws_rds_cluster_instance|aws_redshift_cluster", "publicly_accessible", r' (#eq? @val "true")'),
  R("aws_db_instance", '  engine              = "postgres"\n  instance_class      = "db.t4g.micro"\n  publicly_accessible = true\n'),
  R("aws_db_instance", '  engine              = "postgres"\n  instance_class      = "db.t4g.micro"\n  publicly_accessible = false\n'),
  "Keep databases in private subnets; reach them through the app tier or a bastion/SSM.", sev="major", kind="security", cat="security", docv="Amazon RDS User Guide")
P("AWS-RDS-UNENCRYPTED", "RDS storage encryption disabled", "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html",
  "Amazon RDS can encrypt your Amazon RDS DB instances.",
  attr("resource", "aws_db_instance|aws_rds_cluster", "storage_encrypted", r' (#eq? @val "false")'),
  R("aws_db_instance", '  engine            = "postgres"\n  storage_encrypted = false\n'), R("aws_db_instance", '  engine            = "postgres"\n  storage_encrypted = true\n'),
  "Encrypt at rest (cannot be enabled later without a snapshot restore).", sev="major", kind="security", cat="security", docv="Amazon RDS User Guide")
P("AWS-EBS-UNENCRYPTED", "EBS volume encryption disabled", "https://docs.aws.amazon.com/ebs/latest/userguide/ebs-encryption.html",
  "Use Amazon EBS encryption as a straight-forward encryption solution for your Amazon EBS resources",
  attr("resource", "aws_ebs_volume", "encrypted", r' (#eq? @val "false")'),
  R("aws_ebs_volume", '  availability_zone = "eu-north-1a"\n  size              = 40\n  encrypted         = false\n'),
  R("aws_ebs_volume", '  availability_zone = "eu-north-1a"\n  size              = 40\n  encrypted         = true\n'),
  "Encrypt EBS volumes (or enable account-level encryption by default).", sev="major", kind="security", cat="security", docv="Amazon EBS User Guide")
P("AWS-IAM-WILDCARD-ADMIN", "IAM policy granting Action \"*\"", "https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html",
  "When you set permissions with IAM policies, grant only the permissions required to perform a task.",
  r'((attribute (identifier) @a (expression) @match) (#match? @a "^(policy|inline_policy|assume_role_policy)$") (#match? @match "(?i)\"?action\"?\\s*[:=]\\s*\\[?\\s*\"\\*\""))'
  '\n'
  r'((attribute (identifier) @a (expression) @match) (#eq? @a "actions") (#match? @match "^\\[\\s*\"\\*\"\\s*\\]$"))',
  R("aws_iam_policy", '  name   = "app"\n  policy = jsonencode({\n    Version   = "2012-10-17"\n    Statement = [{ Effect = "Allow", Action = "*", Resource = "*" }]\n  })\n'),
  R("aws_iam_policy", '  name   = "app"\n  policy = jsonencode({\n    Version   = "2012-10-17"\n    Statement = [{ Effect = "Allow", Action = ["s3:GetObject"], Resource = "arn:aws:s3:::app/*" }]\n  })\n'),
  "Wildcard actions grant admin; scope actions and resources (least privilege).", sev="critical", kind="security", cat="security", docv="AWS IAM User Guide")
P("AWS-AMI-MOST-RECENT-NO-OWNER", "aws_ami most_recent without owners/filter", V6,
  "When using `most_recent = true`, your configuration **must now include** `owners` or a `filter`",
  r'((block (identifier) @bt . (string_lit) @rt) @match (#eq? @bt "data") (#match? @rt "^.aws_ami.$") (#match? @match "most_recent\\s*=\\s*true") (#not-match? @match "\\bowners\\s*=|\\bfilter\\s*\\{"))',
  R("aws_ami", '  most_recent = true\n  name_regex  = "^ubuntu-24.04"\n', name="ubuntu", kind="data"),
  R("aws_ami", '  most_recent = true\n  owners      = ["099720109477"]\n  name_regex  = "^ubuntu-24.04"\n', name="ubuntu", kind="data"),
  "Without owners anyone can publish a matching newer AMI (AMI squatting); v6 rejects this config.", sev="major", kind="security", cat="security",
  docv="AWS provider 6.0")

# ------------------------------------------------------------------ AWS provider: aws_s3_bucket inline arguments (deprecated since v4)
S3D = AWSD + "r/s3_bucket.html.markdown"
for arg, isblock, repl, body in [
        ("acceleration_status", False, "aws_s3_bucket_accelerate_configuration", '"Enabled"'),
        ("acl", False, "aws_s3_bucket_acl", '"private"'),
        ("cors_rule", True, "aws_s3_bucket_cors_configuration", '    allowed_methods = ["GET"]\n    allowed_origins = ["https://example.com"]\n'),
        ("grant", True, "aws_s3_bucket_acl", '    type        = "Group"\n    permissions = ["READ_ACP"]\n'),
        ("lifecycle_rule", True, "aws_s3_bucket_lifecycle_configuration", '    enabled = true\n'),
        ("logging", True, "aws_s3_bucket_logging", '    target_bucket = aws_s3_bucket.logs.id\n'),
        ("object_lock_configuration", True, "aws_s3_bucket_object_lock_configuration", '    object_lock_enabled = "Enabled"\n'),
        ("policy", False, "aws_s3_bucket_policy", "data.aws_iam_policy_document.b.json"),
        ("replication_configuration", True, "aws_s3_bucket_replication_configuration", '    role = aws_iam_role.r.arn\n'),
        ("request_payer", False, "aws_s3_bucket_request_payment_configuration", '"Requester"'),
        ("server_side_encryption_configuration", True, "aws_s3_bucket_server_side_encryption_configuration", '    rule {\n      apply_server_side_encryption_by_default {\n        sse_algorithm = "aws:kms"\n      }\n    }\n'),
        ("versioning", True, "aws_s3_bucket_versioning", '    enabled = true\n'),
        ("website", True, "aws_s3_bucket_website_configuration", '    index_document = "index.html"\n')]:
    bad = R("aws_s3_bucket", f'  bucket = "acme-data"\n\n  {arg} {{\n{body}  }}\n' if isblock else f'  bucket = "acme-data"\n  {arg} = {body}\n')
    good = R("aws_s3_bucket", '  bucket = "acme-data"\n') + "\n" + R(repl, "  bucket = aws_s3_bucket.this.id\n")
    P(f"AWS-S3-BUCKET-INLINE-{arg.upper().replace('_', '-')}", f"aws_s3_bucket inline {arg} (deprecated)", S3D, f"* `{arg}` - (Optional, **Deprecated**)",
      nested("resource", "aws_s3_bucket", arg) if isblock else attr("resource", "aws_s3_bucket", arg),
      bad, good, f"Since AWS provider v4 configure this with the standalone {repl} resource; the inline argument is deprecated and drifts.",
      sev="minor", kind="deprecation", cat="compatibility", applies={AWS: ">=4.0"}, docv="AWS provider 4.x+", xref=[V4])

# ------------------------------------------------------------------ AWS provider: v5 / v6 removals
AWSRM = [
    # id, rtype regex, arg regex, is_block, guide, needle, applies, bad body, good body, message
    ("DB-INSTANCE-NAME", "aws_db_instance", "name", False, V5, "Change `name` to `db_name` in configurations as `name` no longer exists.", ">=5.0",
     '  engine = "postgres"\n  name   = "app"\n', '  engine  = "postgres"\n  db_name = "app"\n', "Use db_name."),
    ("DB-SECURITY-GROUP-NAMES", "aws_db_instance|aws_elasticache_cluster", "security_group_names", False, V5,
     "resource's `security_group_names` argument", ">=5.0", '  engine               = "postgres"\n  security_group_names = ["legacy"]\n',
     '  engine                 = "postgres"\n  vpc_security_group_ids = [aws_security_group.db.id]\n', "EC2-Classic security groups are gone; use vpc_security_group_ids."),
    ("ASG-TAGS", "aws_autoscaling_group", "tags", False, V5, "Remove `tags` from configurations as it no longer exists. Use the `tag` attribute instead.", ">=5.0",
     '  max_size = 2\n  tags     = [{ key = "env", value = "prod", propagate_at_launch = true }]\n',
     '  max_size = 2\n\n  tag {\n    key                 = "env"\n    value               = "prod"\n    propagate_at_launch = true\n  }\n', "Use tag blocks (dynamic \"tag\" for lists)."),
    ("BUDGET-COST-FILTERS", "aws_budgets_budget", "cost_filters", False, V5, "Remove `cost_filters` from configurations as it no longer exists.", ">=5.0",
     '  budget_type  = "COST"\n  cost_filters = { Service = "Amazon EC2" }\n', '  budget_type = "COST"\n\n  cost_filter {\n    name   = "Service"\n    values = ["Amazon EC2"]\n  }\n',
     "Use cost_filter blocks."),
    ("ECS-CLUSTER-CAPACITY-PROVIDERS", "aws_ecs_cluster", "capacity_providers|default_capacity_provider_strategy", False, V5,
     "Remove `capacity_providers` and `default_capacity_provider_strategy` from configurations as they no longer exist.", ">=5.0",
     '  name               = "app"\n  capacity_providers = ["FARGATE"]\n', '  name = "app"\n', "Use aws_ecs_cluster_capacity_providers."),
    ("ROUTE-INSTANCE-ID", "aws_route", "instance_id", False, V5, "rather than `instance_id`, which no longer exists.", ">=5.0",
     '  route_table_id         = aws_route_table.r.id\n  destination_cidr_block = "0.0.0.0/0"\n  instance_id            = aws_instance.nat.id\n',
     '  route_table_id         = aws_route_table.r.id\n  destination_cidr_block = "0.0.0.0/0"\n  network_interface_id   = aws_instance.nat.primary_network_interface_id\n',
     "Route via network_interface_id."),
    ("SECRET-ROTATION-INLINE", "aws_secretsmanager_secret", "rotation_enabled|rotation_lambda_arn", False, V5,
     "Remove `rotation_enabled`, `rotation_lambda_arn` and `rotation_rules` from configurations as they no longer exist.", ">=5.0",
     '  name                = "db"\n  rotation_lambda_arn = aws_lambda_function.rot.arn\n', '  name = "db"\n', "Use aws_secretsmanager_secret_rotation."),
    ("VPC-CLASSICLINK", "aws_vpc|aws_default_vpc", "enable_classiclink|enable_classiclink_dns_support", False, V5,
     "Remove `enable_classiclink` and `enable_classiclink_dns_support` from configurations as they no longer exist.", ">=5.0",
     '  cidr_block         = "10.0.0.0/16"\n  enable_classiclink = false\n', '  cidr_block = "10.0.0.0/16"\n', "ClassicLink is retired; delete the argument."),
    ("LAUNCH-CONFIG-CLASSICLINK", "aws_launch_configuration", "vpc_classic_link_id|vpc_classic_link_security_groups", False, V5,
     "Remove `vpc_classic_link_id` and `vpc_classic_link_security_groups` from configurations as they no longer exist.", ">=5.0",
     '  image_id            = var.ami\n  vpc_classic_link_id = "vpc-123"\n', '  image_id = var.ami\n', "ClassicLink is retired; delete the argument."),
    ("REDSHIFT-CLUSTER-SECURITY-GROUPS", "aws_redshift_cluster", "cluster_security_groups", False, V5,
     "Remove `cluster_security_groups` from configurations as it no longer exists.", ">=5.0",
     '  cluster_identifier      = "dw"\n  cluster_security_groups = ["legacy"]\n', '  cluster_identifier     = "dw"\n  vpc_security_group_ids = [aws_security_group.dw.id]\n',
     "Use vpc_security_group_ids."),
    ("SSM-ASSOCIATION-INSTANCE-ID", "aws_ssm_association", "instance_id", False, V5,
     "should be updated to use the `targets` attribute instead.", ">=5.0",
     '  name        = "AWS-RunPatchBaseline"\n  instance_id = aws_instance.web.id\n',
     '  name = "AWS-RunPatchBaseline"\n\n  targets {\n    key    = "InstanceIds"\n    values = [aws_instance.web.id]\n  }\n', "Use targets."),
    ("DX-GATEWAY-VPN-GATEWAY-ID", "aws_dx_gateway_association", "vpn_gateway_id", False, V5, "The `vpn_gateway_id` attribute has been deprecated.", ">=5.0",
     '  dx_gateway_id  = aws_dx_gateway.g.id\n  vpn_gateway_id = aws_vpn_gateway.v.id\n', '  dx_gateway_id         = aws_dx_gateway.g.id\n  associated_gateway_id = aws_vpn_gateway.v.id\n',
     "Use associated_gateway_id."),
    ("EIP-VPC", "aws_eip", "vpc", False, V6, "Remove `vpc`—it is no longer supported. Use `domain` instead.", ">=6.0",
     '  vpc = true\n', '  domain = "vpc"\n', 'Use domain = "vpc".'),
    ("EKS-ADDON-RESOLVE-CONFLICTS", "aws_eks_addon", "resolve_conflicts", False, V6, "Remove `resolve_conflicts`—it is no longer supported.", ">=6.0",
     '  addon_name        = "vpc-cni"\n  resolve_conflicts = "OVERWRITE"\n', '  addon_name                  = "vpc-cni"\n  resolve_conflicts_on_update = "OVERWRITE"\n',
     "Use resolve_conflicts_on_create / resolve_conflicts_on_update."),
    ("FLOW-LOG-LOG-GROUP-NAME", "aws_flow_log", "log_group_name", False, V6, "Remove `log_group_name`—it is no longer supported. Use `log_destination` instead.", ">=6.0",
     '  vpc_id         = aws_vpc.main.id\n  log_group_name = "vpc-flow"\n', '  vpc_id          = aws_vpc.main.id\n  log_destination = aws_cloudwatch_log_group.flow.arn\n',
     "Use log_destination (log group ARN)."),
    ("GUARDDUTY-ORG-AUTO-ENABLE", "aws_guardduty_organization_configuration", "auto_enable", False, V6, "Remove `auto_enable`—it is no longer supported.", ">=6.0",
     '  detector_id = aws_guardduty_detector.d.id\n  auto_enable = true\n', '  detector_id                      = aws_guardduty_detector.d.id\n  auto_enable_organization_members = "ALL"\n',
     "Use auto_enable_organization_members."),
    ("GUARDDUTY-DETECTOR-DATASOURCES", "aws_guardduty_detector", "datasources", True, V6,
     "`datasources` is deprecated. Use the `aws_guardduty_detector_feature` resource instead.", ">=6.0",
     '  enable = true\n\n  datasources {\n    s3_logs {\n      enable = true\n    }\n  }\n', '  enable = true\n', "Use aws_guardduty_detector_feature."),
    ("API-GATEWAY-DEPLOYMENT-STAGE", "aws_api_gateway_deployment", "stage_name|stage_description", False, V6,
     "Use the `aws_api_gateway_stage` resource if your configuration uses any of the following", ">=6.0",
     '  rest_api_id = aws_api_gateway_rest_api.api.id\n  stage_name  = "prod"\n', '  rest_api_id = aws_api_gateway_rest_api.api.id\n',
     "Create an aws_api_gateway_stage resource."),
    ("LAUNCH-TEMPLATE-ELASTIC-GPU", "aws_launch_template", "elastic_gpu_specifications|elastic_inference_accelerator", True, V6,
     "Remove `elastic_gpu_specifications`—it is no longer supported.", ">=6.0",
     '  image_id = var.ami\n\n  elastic_gpu_specifications {\n    type = "eg1.medium"\n  }\n', '  image_id = var.ami\n', "Elastic Graphics/Inference reached end of life; remove."),
    ("REDSHIFT-SNAPSHOT-COPY", "aws_redshift_cluster", "snapshot_copy", True, V6, "Remove `snapshot_copy`—it is no longer supported.", ">=6.0",
     '  cluster_identifier = "dw"\n\n  snapshot_copy {\n    destination_region = "eu-west-1"\n  }\n', '  cluster_identifier = "dw"\n', "Use aws_redshift_snapshot_copy."),
    ("SPOT-BLOCK-DURATION", "aws_spot_instance_request", "block_duration_minutes", False, V6, "Remove `block_duration_minutes`—it is no longer supported.", ">=6.0",
     '  ami                    = var.ami\n  block_duration_minutes = 60\n', '  ami = var.ami\n', "Spot blocks are discontinued; remove."),
    ("SAGEMAKER-NOTEBOOK-ACCELERATOR", "aws_sagemaker_notebook_instance", "accelerator_types", False, V6, "Remove `accelerator_types`—it is no longer supported.", ">=6.0",
     '  instance_type     = "ml.t3.medium"\n  accelerator_types = ["ml.eia2.medium"]\n', '  instance_type = "ml.inf1.xlarge"\n', "Use an Inferentia instance_type."),
]
for rid, rtype, arg, isblock, guide, needle, ver, badb, goodb, msg in AWSRM:
    P("AWS-" + rid, f"{rtype.split('|')[0]}.{arg.split('|')[0]} removed (AWS provider {ver.lstrip('>=')})", guide, needle,
      nested("resource", rtype, arg) if isblock else attr("resource", rtype, arg),
      R(rtype.split("|")[0], badb), R(rtype.split("|")[0], goodb), msg + f" (removed/deprecated in AWS provider {ver.lstrip('>=')}).",
      sev="major", kind="removal", cat="compatibility", applies={AWS: ver}, docv="AWS provider " + ver.lstrip(">="))

AWSRES = [
    ("DB-SECURITY-GROUP-RESOURCE", "resource", "aws_db_security_group|aws_elasticache_security_group|aws_redshift_security_group", V5,
     "We removed this resource as part of the EC2-Classic retirement.", ">=5.0", "aws_db_security_group", '  name = "legacy"\n',
     "aws_security_group", '  name   = "db"\n  vpc_id = aws_vpc.main.id\n', "Use VPC security groups."),
    ("MACIE-CLASSIC", "resource", "aws_macie_member_account_association|aws_macie_s3_bucket_association", V5,
     "Following the retirement of Amazon Macie Classic, we removed these resources", ">=5.0", "aws_macie_s3_bucket_association", '  bucket_name = "b"\n',
     "aws_macie2_classification_job", '  job_type = "ONE_TIME"\n', "Use Macie (aws_macie2_*) resources."),
    ("SUBNET-IDS-DATA", "data", "aws_subnet_ids", V5, "We removed the `aws_subnet_ids` data source.", ">=5.0", "aws_subnet_ids", '  vpc_id = var.vpc_id\n',
     "aws_subnets", '  filter {\n    name   = "vpc-id"\n    values = [var.vpc_id]\n  }\n', "Use data aws_subnets."),
    ("OPSWORKS", "resource", "aws_opsworks_[a-z_]+", V6, "The AWS OpsWorks Stacks service has reached [End of Life]", ">=6.0", "aws_opsworks_stack",
     '  name = "app"\n', "aws_ssm_document", '  name          = "app-config"\n  document_type = "Command"\n', "OpsWorks Stacks is end-of-life and removed; migrate (e.g. Systems Manager)."),
    ("SIMPLEDB", "resource", "aws_simpledb_domain", V6, "The `aws_simpledb_domain` resource has been removed", ">=6.0", "aws_simpledb_domain", '  name = "users"\n',
     "aws_dynamodb_table", '  name     = "users"\n  hash_key = "id"\n', "SimpleDB support was removed; migrate (e.g. DynamoDB)."),
    ("WORKLINK", "resource", "aws_worklink_[a-z_]+", V6, "The following resources have been removed due to dropped support for Amazon Worklink", ">=6.0",
     "aws_worklink_fleet", '  name = "f"\n', "aws_workspacesweb_portal", '  display_name = "p"\n', "WorkLink is discontinued and removed."),
    ("REDSHIFT-SERVICE-ACCOUNT", "data", "aws_redshift_service_account", V6, "The `aws_redshift_service_account` resource has been removed.", ">=6.0",
     "aws_redshift_service_account", "", "aws_iam_policy_document", '  statement {\n    actions = ["s3:PutObject"]\n  }\n',
     "Grant the redshift.amazonaws.com service principal in the bucket policy instead."),
]
for rid, kind, rtype, guide, needle, ver, bt, bb, gt, gb, msg in AWSRES:
    P("AWS-" + rid, f"{bt} removed (AWS provider {ver.lstrip('>=')})", guide, needle, blk(kind, label=rtype),
      R(bt, bb, kind=kind), R(gt, gb, kind=kind), msg, sev="major", kind="removal", cat="compatibility", applies={AWS: ver},
      docv="AWS provider " + ver.lstrip(">="))
AWSDEP = [
    ("ELASTIC-TRANSCODER", "aws_elastictranscoder_[a-z_]+", "Amazon Elastic Transcoder will be [discontinued]", "aws_elastictranscoder_pipeline",
     "Elastic Transcoder is being discontinued; migrate to AWS Elemental MediaConvert."),
    ("EVIDENTLY", "aws_evidently_[a-z_]+", "AWS will [end support]", "aws_evidently_project", "CloudWatch Evidently is ending; migrate to AppConfig feature flags."),
    ("KINESIS-ANALYTICS-V1", "aws_kinesis_analytics_application", "This resource is deprecated and will be removed in a future version. [Effective January 27, 2026]",
     "aws_kinesis_analytics_application", "Kinesis Data Analytics for SQL is discontinued; use aws_kinesisanalyticsv2_application (Managed Flink)."),
    ("MEDIASTORE", "aws_media_store_container|aws_media_store_container_policy", "AWS has [announced](https://aws.amazon.com/blogs/media/support-for-aws-elemental-mediastore-ending-soo",
     "aws_media_store_container", "MediaStore support is ending; migrate (e.g. S3 + CloudFront)."),
]
for rid, rtype, needle, bt, msg in AWSDEP:
    P("AWS-" + rid, f"{bt} (deprecated service)", V6, needle, blk("resource", label=rtype), R(bt, '  name = "x"\n'),
      R("aws_s3_bucket", '  bucket = "x"\n'), msg, sev="minor", kind="deprecation", cat="compatibility", applies={AWS: ">=6.0"}, docv="AWS provider 6.0")

P("AWS-RDS-CLUSTER-ENGINE-REQUIRED", "aws_rds_cluster without engine", V5, "Update configurations to always include `engine` since it is now required and has no default.",
  blk("resource", r' (#not-match? @match "\\bengine\\s*=")', label="aws_rds_cluster|aws_rds_cluster_instance"),
  R("aws_rds_cluster", '  cluster_identifier = "app"\n'), R("aws_rds_cluster", '  cluster_identifier = "app"\n  engine             = "aurora-postgresql"\n'),
  "engine has no default since v5 (it used to mean aurora MySQL 5.6).", sev="major", kind="removal", cat="compatibility", applies={AWS: ">=5.0"}, docv="AWS provider 5.0")
P("AWS-DB-INSTANCE-ID-AS-IDENTIFIER", "aws_db_instance.<x>.id used as identifier", V5, "must be updated to use `identifier` instead.",
  r'((attribute (identifier) @a (expression) @match) (#match? @a "^(db_instance_identifier|source_ids|source_db_instance_identifier|replicate_source_db)$") (#match? @match "aws_db_instance[.][A-Za-z0-9_-]+[.]id\\b"))',
  R("aws_db_snapshot", "  db_instance_identifier = aws_db_instance.main.id\n  db_snapshot_identifier = \"snap\"\n"),
  R("aws_db_snapshot", "  db_instance_identifier = aws_db_instance.main.identifier\n  db_snapshot_identifier = \"snap\"\n"),
  "Since v5 id is the DBI resource ID, not the identifier; use .identifier.", sev="major", kind="removal", cat="correctness", applies={AWS: ">=5.0"},
  docv="AWS provider 5.0")
P("AWS-PROVIDER-ASSUME-ROLE-DURATION-SECONDS", "assume_role.duration_seconds (removed)", V5, "* `assume_role.duration_seconds` - Use `assume_role.duration` instead",
  r'((block (identifier) @p (body (block (identifier) @ar (body (attribute (identifier) @a) @match)))) (#eq? @p "provider") (#match? @ar "^assume_role") (#eq? @a "duration_seconds"))',
  'provider "aws" {\n  assume_role {\n    role_arn         = var.role\n    duration_seconds = 3600\n  }\n}\n',
  'provider "aws" {\n  assume_role {\n    role_arn = var.role\n    duration = "1h"\n  }\n}\n',
  "Use duration (a duration string).", sev="major", kind="removal", cat="compatibility", applies={AWS: ">=5.0"}, docv="AWS provider 5.0")

secret_rules(P, '(template_literal)', lambda k, v: f'locals {{\n  {k} = "{v}"\n}}\n')

RULES = P.R

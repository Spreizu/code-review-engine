"""LLM pack (OWASP Top 10 for LLM Applications 2025): code that calls model SDKs (OpenAI, Anthropic,
Google GenAI, LangChain, Vercel AI SDK, Hugging Face, PyTorch). Model output is untrusted data:
the rules flag it reaching interpreters (eval/shell/SQL/HTML), secrets placed in prompts, request
data in system prompts, unbounded generation, remote-code model loading and open-ended agent tools.
Detection and wording are crev's own; quotes are from the cited official pages (genai.owasp.org and
the OWASP Cheat Sheet Series are CC BY-SA 4.0: cited, not copied)."""
from specs._common import Pack

P = Pack("LLM", "python", "OWASP Top 10 for LLM Applications 2025", {"python": ">=3.8"}, files=["**/*.py"])
G = "https://genai.owasp.org/llmrisk/"
OUT = G + "llm052025-improper-output-handling/"
OUT_Q = "LLM output is entered directly into a system shell or similar function such as exec or eval, resulting in remote code execution."
JSA = {"ecmascript": ">=2015"}
JSF = ["**/*.js", "**/*.mjs", "**/*.cjs", "**/*.jsx", "**/*.ts", "**/*.tsx", "**/*.mts"]
# Calls that return model output (Python / JS SDKs). Used as same-function evidence.
PYLLM = r"(chat\.completions\.create|\bcompletions\.create|responses\.create|messages\.create|generate_content|ChatCompletion\.create|\b(llm|chain|model|chat|agent|runnable)\w*\.a?invoke\(|ollama\.(chat|generate)\(|InferenceClient)"
JSLLM = r"(chat\.completions\.create|responses\.create|messages\.create|generateContent|generateText\(|streamText\(|generateObject\(|\b(llm|chain|model|chat|agent)\w*\.invoke\(|ollama\.(chat|generate)\()"
PYREQ = r"request\.(args|form|json|get_json|data|values|query_params|GET|POST|body)|\breq\.(body|query|params)|Body\(|Query\("
JSREQ = r"\b(req|request|ctx\.request)\.(body|query|params)|readBody\(|getQuery\(|await request\.json\(\)"
SECRET_NAME = "(?i)(password|passwd|api_?key|secret|private_?key|access_?token|credential|conn(ection)?_?str)"


def sec(id, title, url, needle, query, bad, good, msg, sev="major", js=False, **kw):
    if js:
        kw.setdefault("lang", "javascript")
        kw.setdefault("applies", JSA)
        kw.setdefault("files", JSF)
    r = P(id, title, url, needle, query, bad, good, msg, sev=sev, kind="security", cat="security", **kw)
    r["detection"]["exclude_tests"] = True
    return r


AI_OUT = "Does the value passed here come from model output (directly or via variables) without validation or an allow-list?"
# ------------------------------------------------------------------ LLM05 improper output handling
sec("PY-OUTPUT-TO-EXEC", "Model output may reach eval/exec or a shell", OUT, OUT_Q,
    r"""((call function: (_) @f arguments: (argument_list . (_) @arg)) @match (#match? @f "^(eval|exec|os\\.(system|popen)|subprocess\\.(run|call|check_output|check_call|Popen|getoutput|getstatusoutput))$"))""",
    "def act(client, task):\n    r = client.chat.completions.create(model='gpt-4.1', messages=[{'role': 'user', 'content': task}])\n    exec(r.choices[0].message.content)\n",
    "def act(client, task):\n    r = client.chat.completions.create(model='gpt-4.1', messages=[{'role': 'user', 'content': task}])\n    return ACTIONS[r.choices[0].message.content.strip()]()\n",
    "Text produced by the model is executed. Anyone who can influence the prompt (users, retrieved documents, web pages) can make the model emit code that runs with the app's permissions. Map model output onto an allow-list of actions, or run it in a sandbox.",
    sev="critical", mode="ai-confirm", ai=AI_OUT, filters=["func.has_re:" + PYLLM, "node.lacks_re:^[\\w.]+\\(\\s*([\\[(](\\s*['\\\"][^'\\\"]*['\\\"]\\s*,?)*\\s*[\\])]|['\\\"][^'\\\"{}]*['\\\"])\\s*[,)]"],
    cwe=["CWE-94", "CWE-78"], owasp=["LLM05:2025"],
    fp=["def act(client):\n    r = client.messages.create(model='claude-sonnet-4-5', max_tokens=256, messages=[])\n    subprocess.run(['git', 'status'])\n",
        "async def main(client):\n    await client.chat.completions.create(model='gpt-4.1', messages=[], max_tokens=10)\n\nasyncio.run(main())\n"])
sec("PY-OUTPUT-TO-SQL", "Model output may be executed as SQL", OUT, "LLM-generated SQL queries are executed without proper parameterization, leading to SQL injection.",
    r"""((call function: (attribute attribute: (identifier) @m) arguments: (argument_list . [(identifier) (string (interpolation)) (binary_operator) (call) (attribute) (subscript)])) @match (#match? @m "^(execute|executemany|executescript|raw|text|read_sql|read_sql_query)$"))""",
    "def ask(client, cur, q):\n    r = client.chat.completions.create(model='gpt-4.1', messages=[{'role': 'user', 'content': 'SQL for: ' + q}])\n    cur.execute(r.choices[0].message.content)\n",
    "def ask(client, cur, q):\n    r = client.chat.completions.create(model='gpt-4.1', messages=[{'role': 'user', 'content': q}])\n    cur.execute('SELECT * FROM faq WHERE topic = %s', (r.choices[0].message.content,))\n",
    "A query string built by or from model output is executed. Prompt injection turns into SQL injection (read or drop any table). Let the model choose among parameterized queries, or run generated SQL on a read-only connection limited to safe views.",
    sev="critical", mode="ai-confirm", ai=AI_OUT, filters=["func.has_re:" + PYLLM], cwe=["CWE-89"], owasp=["LLM05:2025"])
sec("JS-OUTPUT-TO-EXEC", "Model output may reach eval or a shell", OUT, OUT_Q,
    r"""((call_expression function: (_) @f arguments: (arguments . (_) @arg)) @match (#match? @f "^(eval|exec|execSync|spawn|spawnSync|execFile|execFileSync|(child_process|cp|vm)\\.(exec|execSync|spawn|spawnSync|execFile|execFileSync|runInNewContext|runInThisContext))$"))""",
    "export async function act(task) {\n  const r = await openai.chat.completions.create({ model: 'gpt-4.1', messages: [{ role: 'user', content: task }] })\n  eval(r.choices[0].message.content)\n}\n",
    "export async function act(task) {\n  const r = await openai.chat.completions.create({ model: 'gpt-4.1', messages: [{ role: 'user', content: task }] })\n  return ACTIONS[r.choices[0].message.content.trim()]?.()\n}\n",
    "Text produced by the model is executed. Anyone who can influence the prompt can make the model emit code or shell commands that run with the server's permissions. Map output onto an allow-list of actions or use a sandbox.",
    sev="critical", js=True, mode="ai-confirm", ai=AI_OUT, filters=["func.has_re:" + JSLLM, "node.lacks_re:^\\w+(\\.\\w+)?\\(\\s*['\\\"`][^'\\\"`$]*['\\\"`]\\s*[,)]"],
    cwe=["CWE-94", "CWE-78"], owasp=["LLM05:2025"])
sec("JS-OUTPUT-TO-HTML", "Model output may be inserted as HTML", OUT,
    "JavaScript or Markdown is generated by the LLM and returned to a user. The code is then interpreted by the browser, resulting in XSS.",
    r"""((assignment_expression left: (member_expression property: (property_identifier) @p)) @match (#match? @p "^(innerHTML|outerHTML)$"))""",
    "async function show(el, q) {\n  const r = await openai.chat.completions.create({ model: 'gpt-4.1', messages: [{ role: 'user', content: q }] })\n  el.innerHTML = marked.parse(r.choices[0].message.content)\n}\n",
    "async function show(el, q) {\n  const r = await openai.chat.completions.create({ model: 'gpt-4.1', messages: [{ role: 'user', content: q }] })\n  el.innerHTML = DOMPurify.sanitize(marked.parse(r.choices[0].message.content))\n}\n",
    "Model output (or Markdown rendered from it) is written as HTML. Injected instructions can make the model emit script tags or event handlers, which run in the user's session (XSS). Sanitize with DOMPurify or render as text.",
    js=True, mode="ai-confirm", ai=AI_OUT, filters=["func.has_re:" + JSLLM, "node.lacks_re:(?i)sanitiz|DOMPurify|escape"], cwe=["CWE-79"], owasp=["LLM05:2025"])

# ------------------------------------------------------------------ LLM02 / LLM07 secrets in prompts
SP = G + "llm072025-system-prompt-leakage/"
SP_Q = "sensitive data such as credentials, connection strings, etc. should not be contained within the system prompt language."
SECRET_MSG = "A credential is placed into the prompt text. Models repeat their context on request, logs and providers store prompts, so the secret leaks. Keep secrets in code that calls tools on the model's behalf, never in the prompt."
sec("PY-SECRET-IN-PROMPT", "Secret interpolated into a prompt", SP, SP_Q,
    r"""((interpolation expression: (_) @v) @match (#match? @v "(?i)(password|passwd|api_?key|secret|private_?key|access_?token|credential|conn(ection)?_?str)"))""",
    "def run(client, db_password):\n    return client.messages.create(model='claude-sonnet-4-5', max_tokens=512, system=f'You manage the DB. Password: {db_password}', messages=[])\n",
    "def run(client, schema):\n    return client.messages.create(model='claude-sonnet-4-5', max_tokens=512, system=f'You manage the DB. Schema: {schema}', messages=[])\n",
    SECRET_MSG, mode="ai-confirm", ai="Does the interpolated value hold an actual secret (not e.g. a boolean flag or a field name)?",
    filters=["ancestor.has_re:call:" + PYLLM], cwe=["CWE-200", "CWE-522"], owasp=["LLM02:2025", "LLM07:2025"])
sec("JS-SECRET-IN-PROMPT", "Secret interpolated into a prompt", SP, SP_Q,
    r"""((template_substitution (_) @v) @match (#match? @v "(?i)(password|passwd|api_?key|secret|private_?key|access_?token|credential|conn(ection)?_?str)"))""",
    "const r = await openai.chat.completions.create({ model: 'gpt-4.1', messages: [{ role: 'system', content: `Use API key ${process.env.STRIPE_SECRET_KEY} for refunds` }] })\n",
    "const r = await openai.chat.completions.create({ model: 'gpt-4.1', messages: [{ role: 'system', content: `Refunds go through the refund tool` }] })\n",
    SECRET_MSG, js=True, mode="ai-confirm", ai="Does the interpolated value hold an actual secret (not e.g. a boolean flag or a field name)?",
    filters=["ancestor.has_re:call_expression:" + JSLLM], cwe=["CWE-200", "CWE-522"], owasp=["LLM02:2025", "LLM07:2025"])

# ------------------------------------------------------------------ LLM01 request data in the system prompt
PI = "https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html"
PI_Q = "The LLM processes this as a legitimate instruction change rather than data to be processed."
PI_MSG = "Request data is interpolated into the system (instruction) prompt, so a user can rewrite the model's instructions. Keep instructions fixed and pass user content as a separate user message, clearly delimited."
sec("PY-REQUEST-IN-SYSTEM-PROMPT", "Request data interpolated into the system prompt", PI, PI_Q,
    r"""((dictionary (pair key: (string (string_content) @rk) value: (string (string_content) @rv)) (pair key: (string (string_content) @ck) value: (string (interpolation)) @match)) (#eq? @rk "role") (#eq? @rv "system") (#eq? @ck "content"))""",
    "@app.post('/ask')\ndef ask():\n    q = request.json['q']\n    msgs = [{'role': 'system', 'content': f'Answer as the support bot. Customer says: {q}'}]\n    return client.chat.completions.create(model='gpt-4.1', messages=msgs)\n",
    "@app.post('/ask')\ndef ask():\n    q = request.json['q']\n    msgs = [{'role': 'system', 'content': 'Answer as the support bot.'}, {'role': 'user', 'content': q}]\n    return client.chat.completions.create(model='gpt-4.1', messages=msgs)\n",
    PI_MSG, mode="ai-confirm", ai="Is any interpolated value derived from the request or other end-user/external content?",
    filters=[r"""file.has_re:["']role["']\s*:\s*["']system["']""", "func.has_re:" + PYREQ], cwe=["CWE-77"], owasp=["LLM01:2025"], docv="OWASP LLM Prompt Injection Prevention Cheat Sheet")
sec("JS-REQUEST-IN-SYSTEM-PROMPT", "Request data interpolated into the system prompt", PI, PI_Q,
    r"""((object (pair key: (property_identifier) @rk value: (string (string_fragment) @rv)) (pair key: (property_identifier) @ck value: (template_string (template_substitution)) @match)) (#eq? @rk "role") (#eq? @rv "system") (#eq? @ck "content"))""",
    "app.post('/ask', async (req, res) => {\n  const messages = [{ role: 'system', content: `You are the support bot. Customer: ${req.body.q}` }]\n  res.json(await openai.chat.completions.create({ model: 'gpt-4.1', messages }))\n})\n",
    "app.post('/ask', async (req, res) => {\n  const messages = [{ role: 'system', content: 'You are the support bot.' }, { role: 'user', content: req.body.q }]\n  res.json(await openai.chat.completions.create({ model: 'gpt-4.1', messages }))\n})\n",
    PI_MSG, js=True, mode="ai-confirm", ai="Is any interpolated value derived from the request or other end-user/external content?",
    filters=[r"""file.has_re:\brole["']?\s*:\s*["']system["']""", "func.has_re:" + JSREQ], cwe=["CWE-77"], owasp=["LLM01:2025"], docv="OWASP LLM Prompt Injection Prevention Cheat Sheet")

# ------------------------------------------------------------------ LLM10 unbounded consumption
UC = G + "llm102025-unbounded-consumption/"
UC_Q = "Monitor and manage resource allocation dynamically to prevent any single user or request from consuming excessive resources."
UC_MSG = "The completion has no output-token cap, so one request can generate up to the model's maximum, multiplying cost and latency (and an attacker can force that repeatedly). Set max_tokens / max_completion_tokens / max_output_tokens."
sec("PY-NO-MAX-TOKENS", "OpenAI completion without an output-token limit", UC, UC_Q,
    r"""((call function: (attribute object: (attribute attribute: (identifier) @c) attribute: (identifier) @m) arguments: (argument_list) @match) (#match? @c "^(completions|responses)$") (#eq? @m "create"))""",
    "r = client.chat.completions.create(model='gpt-4.1', messages=msgs)\n", "r = client.chat.completions.create(model='gpt-4.1', messages=msgs, max_completion_tokens=800)\n",
    UC_MSG, sev="info", filters=["node.lacks_re:max_(completion_|output_)?tokens|\\*\\*"], cwe=["CWE-770"], owasp=["LLM10:2025"],
    fp=["r = client.chat.completions.create(**params)\n"])
sec("JS-NO-MAX-TOKENS", "OpenAI completion without an output-token limit", UC, UC_Q,
    r"""((call_expression function: (member_expression object: (member_expression property: (property_identifier) @c) property: (property_identifier) @m) arguments: (arguments . (object) @match .)) (#match? @c "^(completions|responses)$") (#eq? @m "create"))""",
    "const r = await openai.chat.completions.create({ model: 'gpt-4.1', messages })\n", "const r = await openai.chat.completions.create({ model: 'gpt-4.1', messages, max_completion_tokens: 800 })\n",
    UC_MSG, sev="info", js=True, filters=["node.lacks_re:max_(completion_|output_)?tokens|\\.\\.\\."], cwe=["CWE-770"], owasp=["LLM10:2025"])

# ------------------------------------------------------------------ LLM03 model supply chain
HF = "https://huggingface.co/docs/transformers/main/en/model_doc/auto"
sec("PY-TRUST-REMOTE-CODE", "Model loaded with trust_remote_code=True", HF, "Whether or not to allow for custom models defined on the Hub in their own modeling file",
    r"""((keyword_argument name: (identifier) @k value: (true)) @match (#eq? @k "trust_remote_code"))""",
    "model = AutoModelForCausalLM.from_pretrained(repo_id, trust_remote_code=True)\n",
    "model = AutoModelForCausalLM.from_pretrained('Qwen/Qwen3-8B', revision='b968826d9c46dd6066d109eabc6255188de91218')\n",
    "Python files from the model repository are executed when the model loads. Whoever controls that repo (or a later commit) runs code in your process. Use built-in architectures, or pin revision= to an audited commit.",
    mode="ai-confirm", ai="Is the repository id not a fixed, audited model pinned to a specific revision commit?", cwe=["CWE-829", "CWE-94"], owasp=["LLM03:2025"],
    docv="Hugging Face Transformers docs")
TL = "https://raw.githubusercontent.com/pytorch/pytorch/main/torch/serialization.py"
sec("PY-TORCH-LOAD-UNSAFE", "torch.load with weights_only=False", TL, "but it can result in arbitrary code execution. Do it only if you got the file from a",
    r"""((call function: (attribute object: (identifier) @t attribute: (identifier) @l) arguments: (argument_list (keyword_argument name: (identifier) @k value: (false)))) @match (#eq? @t "torch") (#eq? @l "load") (#eq? @k "weights_only"))""",
    "state = torch.load(path, weights_only=False)\n", "state = torch.load(path, weights_only=True)\n",
    "weights_only=False unpickles the file, so a crafted checkpoint runs arbitrary code when loaded. Keep the default weights_only=True (allow-list extra types with torch.serialization.add_safe_globals) or use safetensors.",
    cwe=["CWE-502"], owasp=["LLM03:2025", "LLM04:2025"], docv="PyTorch source (torch/serialization.py)")

# ------------------------------------------------------------------ LLM06 excessive agency
EA = G + "llm062025-excessive-agency/"
sec("PY-AGENT-SHELL-TOOL", "Agent given a shell / Python REPL tool or dangerous mode", EA,
    "Avoid the use of open-ended extensions where possible (e.g., run a shell command, fetch a URL, etc.)",
    r"""[((call function: [(identifier) @f (attribute attribute: (identifier) @f)]) @match (#match? @f "^(ShellTool|PythonREPLTool|PythonAstREPLTool|PythonREPL|TerminalTool|BashProcess)$"))
         ((keyword_argument name: (identifier) @k value: (true)) @match (#match? @k "^(allow_dangerous_code|allow_dangerous_requests|allow_dangerous_deserialization)$"))]""",
    "tools = [ShellTool(), search]\nagent = create_react_agent(llm, tools)\n", "tools = [search, lookup_order]\nagent = create_react_agent(llm, tools)\n",
    "The model can run arbitrary shell commands or Python (or deserialize untrusted data). A prompt injection in any input becomes code execution. Give the agent narrow tools with validated parameters, or run it in an isolated sandbox with human approval.",
    cwe=["CWE-250", "CWE-94"], owasp=["LLM06:2025"])

RULES = P.R

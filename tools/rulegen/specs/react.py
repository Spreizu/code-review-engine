"""React pack (framework layer on the JS/TS packs). JS/TS-level rules use language `javascript` (runs on .js/.jsx/.ts/.tsx);
JSX-structure rules use language `jsx` (javascript + tsx grammars); TS-type rules use `typescript`. Version dimension
`react` from package.json/lockfile. Sources: react.dev (React 19 upgrade guide, React 19 / 19.2 posts, React 18 upgrade
guide, API reference, Rules of React, eslint-plugin-react-hooks lint docs, Learn)."""
from specs._common import Pack

R = "https://react.dev/"
UG19 = R + "blog/2024/04/25/react-19-upgrade-guide"
UG18 = R + "blog/2022/03/08/react-18-upgrade-guide"
LINT = R + "reference/eslint-plugin-react-hooks/lints/"
P = Pack("REACT", "javascript", "React 19.2 (react.dev)", {"react": "*"}, framework="react")
R19, R18 = {"react": ">=19.0"}, {"react": ">=18.0"}


def imp(src, names):
    return (f'((import_statement (import_clause (named_imports (import_specifier name: (identifier) @n))) source: (string (string_fragment) @s)) @match '
            f'(#match? @s "^({src})$") (#match? @n "^({names})$"))')


def mem(obj, prop):
    return (f'((call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p)) @match '
            f'(#match? @o "^({obj})$") (#match? @p "^({prop})$"))')


def call(fn):
    return f'((call_expression function: (identifier) @f) @match (#match? @f "^({fn})$"))'


def src(s):
    return f'((import_statement source: (string (string_fragment) @s)) @match (#match? @s "^({s})$"))'


COMP = lambda body: f"function App() {{\n{body}}}\n"

# ------------------------------------------------------------------ react-dom legacy root APIs (deprecated 18, removed 19)
for api, since, repl, bad, good in [
        ("render", "18.0", "createRoot", "import { render } from 'react-dom';\nrender(<App />, document.getElementById('root'));\n",
         "import { createRoot } from 'react-dom/client';\ncreateRoot(document.getElementById('root')).render(<App />);\n"),
        ("hydrate", "18.0", "hydrateRoot", "import { hydrate } from 'react-dom';\nhydrate(<App />, document.getElementById('root'));\n",
         "import { hydrateRoot } from 'react-dom/client';\nhydrateRoot(document.getElementById('root'), <App />);\n"),
        ("unmountComponentAtNode", "18.0", "root.unmount()", "import { unmountComponentAtNode } from 'react-dom';\nunmountComponentAtNode(el);\n", "root.unmount();\n"),
        ("findDOMNode", "16.6", "DOM refs", "import { findDOMNode } from 'react-dom';\nconst node = findDOMNode(this);\n",
         "const ref = useRef(null);\nconst node = ref.current;\n")]:
    q = imp("react-dom", api) + "\n" + mem("ReactDOM|ReactDom", api)
    name = api.upper().replace("COMPONENTATNODE", "-COMPONENT-AT-NODE").replace("DOMNODE", "-DOM-NODE")
    P(f"REACTDOM-{name}-REMOVED", f"ReactDOM.{api} (removed in React 19)", UG19, f"Removed: {'ReactDOM.' if api != 'unmountComponentAtNode' else ''}{api}",
      q, bad, good, f"ReactDOM.{api} no longer exists in React 19; migrate to {repl}.", sev="critical", kind="removal", cat="compatibility", applies=R19,
      docv="React 19")
    P(f"REACTDOM-{name}-DEPRECATED", f"ReactDOM.{api} (deprecated)", UG19, f"was deprecated in {'March 2022 (v18.0.0)' if since == '18.0' else 'October 2018 (v16.6.0)'}",
      q, bad, good, f"Deprecated since React {since} and removed in 19; migrate to {repl} before upgrading.", sev="minor", kind="deprecation",
      cat="compatibility", applies={"react": f">={since} <19.0"}, docv=f"React {since}")
P("REACTDOM-UNSTABLE-REMOVED", "Removed react-dom unstable_* APIs", UG19, "Remove unstable_renderSubtreeIntoContainer",
  imp("react-dom", "unstable_flushControlled|unstable_createEventHandle|unstable_renderSubtreeIntoContainer|unstable_runWithPriority") + "\n"
  + mem("ReactDOM", "unstable_flushControlled|unstable_createEventHandle|unstable_renderSubtreeIntoContainer|unstable_runWithPriority"),
  "import { unstable_renderSubtreeIntoContainer } from 'react-dom';\n", "import { createPortal } from 'react-dom';\n",
  "These unstable APIs were removed in React 19 (use createPortal / createRoot).", sev="critical", kind="removal", cat="compatibility", applies=R19, docv="React 19")
P("RENDER-TO-NODE-STREAM", "renderToNodeStream (deprecated/removed)", UG18, "renderToNodeStream : Deprecated ⛔️️ Instead, for streaming in Node environments, use: renderToPipeableStream",
  imp("react-dom/server", "renderToNodeStream") + "\n" + mem("ReactDOMServer", "renderToNodeStream"),
  "import { renderToNodeStream } from 'react-dom/server';\nrenderToNodeStream(<App />).pipe(res);\n",
  "import { renderToPipeableStream } from 'react-dom/server';\nrenderToPipeableStream(<App />).pipe(res);\n",
  "Use renderToPipeableStream (Node) or renderToReadableStream (web streams).", sev="major", kind="deprecation", cat="compatibility", applies=R18, docv="React 18")
P("TEST-UTILS-REMOVED", "react-dom/test-utils (removed in 19)", UG19, "We’ve moved act from react-dom/test-utils to the react package",
  src("react-dom/test-utils"), "import { act } from 'react-dom/test-utils';\n", "import { act } from 'react';\n",
  "Import act from 'react'; the other test-utils were removed — use @testing-library/react.", sev="major", kind="removal", cat="compatibility", applies=R19, docv="React 19")
P("TEST-RENDERER-SHALLOW-REMOVED", "react-test-renderer/shallow (removed in 19)", UG19, "In React 19, we’re removing react-test-render/shallow to prefer installing the package directly",
  src("react-test-renderer/shallow"), "import ShallowRenderer from 'react-test-renderer/shallow';\n", "import { render } from '@testing-library/react';\n",
  "Install react-shallow-renderer directly — or better, migrate to @testing-library/react.", sev="major", kind="removal", cat="compatibility", applies=R19, docv="React 19")
P("TEST-RENDERER-DEPRECATED", "react-test-renderer (deprecated in 19)", UG19, "We are deprecating react-test-renderer because it implements its own renderer environment",
  src("react-test-renderer"), "import renderer from 'react-test-renderer';\n", "import { render } from '@testing-library/react';\n",
  "Migrate tests to @testing-library/react (or -native).", sev="minor", kind="deprecation", cat="testing", applies=R19, docv="React 19")

# ------------------------------------------------------------------ react legacy APIs removed in 19
P("PROPTYPES-IGNORED", "propTypes are ignored in React 19", UG19, "In React 19, we’re removing the propType checks from the React package, and using them will be silently ignored.",
  r'((assignment_expression left: (member_expression property: (property_identifier) @p)) @match (#eq? @p "propTypes"))' + "\n"
  + r'((class_body (_ . (property_identifier) @p) @match) (#eq? @p "propTypes"))',
  "function Heading({ text }) {\n  return <h1>{text}</h1>;\n}\nHeading.propTypes = { text: PropTypes.string };\n",
  "function Heading({ text }: { text?: string }) {\n  return <h1>{text}</h1>;\n}\n",
  "propTypes do nothing in React 19; use TypeScript (codemod: react/prop-types-typescript).", sev="major", kind="removal", cat="compatibility", applies=R19, docv="React 19")
P("FUNCTION-DEFAULTPROPS", "defaultProps on a function component", UG19, "We’re also removing defaultProps from function components in place of ES6 default parameters.",
  r'((assignment_expression left: (member_expression object: (identifier) @c property: (property_identifier) @p)) @match (#eq? @p "defaultProps") (#match? @c "^[A-Z]"))',
  "function Heading({ text }) {\n  return <h1>{text}</h1>;\n}\nHeading.defaultProps = { text: 'Hello' };\n",
  "function Heading({ text = 'Hello' }) {\n  return <h1>{text}</h1>;\n}\n",
  "defaultProps is ignored on function components in React 19; use default parameters (class components still support it).",
  sev="major", kind="removal", cat="compatibility", applies=R19, docv="React 19", filters=[r"file.lacks_re:extends\s+(React\.)?(Pure)?Component\b"])
P("LEGACY-CONTEXT", "Legacy context (contextTypes / getChildContext)", UG19, "In React 19, we’re removing Legacy Context to make React slightly smaller and faster.",
  r'((class_body (_ . (property_identifier) @p) @match) (#match? @p "^(contextTypes|childContextTypes)$"))' + "\n"
  + r'((method_definition name: (property_identifier) @p) @match (#eq? @p "getChildContext"))' + "\n"
  + r'((assignment_expression left: (member_expression property: (property_identifier) @p)) @match (#match? @p "^(contextTypes|childContextTypes)$"))',
  "class Parent extends React.Component {\n  getChildContext() {\n    return { foo: 'bar' };\n  }\n}\n",
  "const FooContext = React.createContext('bar');\nclass Child extends React.Component {\n  static contextType = FooContext;\n}\n",
  "Legacy context is removed in React 19; use createContext + contextType/useContext.", sev="critical", kind="removal", cat="compatibility", applies=R19, docv="React 19")
P("STRING-REFS", "String ref", UG19, "In React 19, we’re removing string refs to make React simpler and easier to understand.",
  r'((jsx_attribute (property_identifier) @a (string)) @match (#eq? @a "ref"))' + "\n"
  + r'((member_expression object: (this) property: (property_identifier) @p) @match (#eq? @p "refs"))',
  "class C extends React.Component {\n  render() {\n    return <input ref='input' />;\n  }\n}\n",
  "class C extends React.Component {\n  render() {\n    return <input ref={(el) => { this.input = el; }} />;\n  }\n}\n",
  "String refs are removed in React 19; use callback refs or createRef (codemod: react/19/replace-string-ref).", sev="critical", kind="removal",
  cat="compatibility", applies=R19, lang="jsx", docv="React 19")
P("CREATE-FACTORY", "React.createFactory", UG19, "In React 19, we’re removing createFactory and you’ll need to migrate to JSX",
  imp("react", "createFactory") + "\n" + mem("React", "createFactory"), "import { createFactory } from 'react';\nconst button = createFactory('button');\n",
  "const button = <button />;\n", "createFactory is removed in React 19; use JSX.", sev="critical", kind="removal", cat="compatibility", applies=R19, docv="React 19")
P("SECRET-INTERNALS", "Use of React internals", UG19, "The recommendation is to remove any code that depends on internals.",
  r'((_) @match (#match? @match "^__?(SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED|CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE)$"))',
  "const internals = React.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;\n", "const version = React.version;\n",
  "React internals changed in 19 and will be blocked; remove the dependency (or upgrade the library that uses it).", sev="major", kind="anti-pattern",
  cat="compatibility", docv="React 19")
P("USE-FORM-STATE", "useFormState (renamed useActionState)", R + "blog/2024/12/05/react-19", "we’ve renamed it and deprecated useFormState",
  imp("react-dom", "useFormState") + "\n" + mem("ReactDOM", "useFormState"),
  "import { useFormState } from 'react-dom';\nconst [state, action] = useFormState(fn, null);\n", "import { useActionState } from 'react';\nconst [state, action, pending] = useActionState(fn, null);\n",
  "Use React.useActionState (codemod: react/19/replace-use-form-state).", sev="minor", kind="deprecation", cat="compatibility", applies=R19, docv="React 19")

# ------------------------------------------------------------------ React 19 modernization
P("FORWARD-REF-UNNECESSARY", "forwardRef (ref is a prop in 19)", R + "reference/react/forwardRef", "In React 19, forwardRef is no longer necessary. Pass ref as a prop instead.",
  call("forwardRef") + "\n" + mem("React", "forwardRef"),
  "const Input = forwardRef(function Input(props, ref) {\n  return <input ref={ref} {...props} />;\n});\n",
  "function Input({ ref, ...props }) {\n  return <input ref={ref} {...props} />;\n}\n",
  "Accept ref as a regular prop; forwardRef will be deprecated.", sev="info", kind="modernization", cat="modernization", applies=R19, docv="React 19")
P("CONTEXT-PROVIDER", "<Context.Provider> (render <Context> in 19)", R + "reference/react/createContext", "Starting in React 19, you can render <SomeContext> as a provider.",
  r'((jsx_opening_element name: (member_expression property: (property_identifier) @p)) @match (#eq? @p "Provider"))' + "\n"
  + r'((jsx_self_closing_element name: (member_expression property: (property_identifier) @p)) @match (#eq? @p "Provider"))',
  "const el = <ThemeContext.Provider value='dark'><Page /></ThemeContext.Provider>;\n", "const el = <ThemeContext value='dark'><Page /></ThemeContext>;\n",
  "Render the context itself as the provider; .Provider will be deprecated.", sev="info", kind="modernization", cat="modernization", applies=R19, lang="jsx",
  docv="React 19")
P("UNUSED-REACT-IMPORT", "import React only for JSX (new JSX transform)", UG19, "We introduced a new JSX transform in 2020 to improve bundle size and use JSX without importing React.",
  r'((import_statement (import_clause . (identifier) @d .) source: (string (string_fragment) @s)) @match (#eq? @d "React") (#eq? @s "react"))',
  "import React from 'react';\nexport const A = () => <div />;\n", "export const A = () => <div />;\n",
  "With the modern JSX transform (required in React 19) the default React import is unnecessary.", sev="info", kind="modernization", cat="maintainability",
  applies={"react": ">=17.0"}, filters=[r"file.lacks_re:\bReact\."])
P("USEREF-REQUIRES-ARGUMENT", "useRef() without an argument (React 19 types)", UG19, "We’ve changed the types so that useRef now requires an argument.",
  r'((call_expression function: (identifier) @f arguments: (arguments . ")")) @match (#eq? @f "useRef"))' + "\n"
  + r'((call_expression function: (identifier) @f type_arguments: (type_arguments) arguments: (arguments . ")")) @match (#eq? @f "useRef"))',
  "const ref = useRef<HTMLDivElement>();\n", "const ref = useRef<HTMLDivElement>(null);\n",
  "@types/react 19 requires an initial value: useRef(null) / useRef(undefined).", sev="minor", kind="migration", cat="compatibility", applies=R19,
  lang="typescript", docv="@types/react 19")
P("REF-CALLBACK-IMPLICIT-RETURN", "Ref callback with implicit return", UG19, "Due to the introduction of ref cleanup functions, returning anything else from a ref callback will now be rejected by TypeScript.",
  r'((jsx_attribute (property_identifier) @a (jsx_expression (arrow_function body: [(parenthesized_expression (assignment_expression)) (assignment_expression)]))) @match (#eq? @a "ref"))',
  "const el = <div ref={(current) => (instance = current)} />;\n", "const el = <div ref={(current) => { instance = current; }} />;\n",
  "React 19 treats a returned function as ref cleanup; use a block body.", sev="minor", kind="migration", cat="correctness", applies=R19, lang="jsx", docv="React 19")
P("GLOBAL-JSX-NAMESPACE", "Global JSX namespace augmentation", UG19, "A long-time request is to remove the global JSX namespace from our types in favor of React.JSX .",
  r'((ambient_declaration (statement_block (expression_statement (internal_module name: (identifier) @n)))) @match (#eq? @n "JSX"))' + "\n"
  + r'((program (expression_statement (internal_module name: (identifier) @n)) @match) (#eq? @n "JSX"))' + "\n"
  + r'((ambient_declaration (statement_block (module name: (identifier) @n))) @match (#eq? @n "JSX"))',
  "declare global {\n  namespace JSX {\n    interface IntrinsicElements {\n      'my-element': { foo: string };\n    }\n  }\n}\n",
  "declare module 'react' {\n  namespace JSX {\n    interface IntrinsicElements {\n      'my-element': { foo: string };\n    }\n  }\n}\n",
  "@types/react 19 removed the global JSX namespace; augment it inside declare module 'react' (or react/jsx-runtime).", sev="minor", kind="migration",
  cat="compatibility", applies=R19, lang="typescript", docv="@types/react 19")
P("USEREDUCER-REDUCER-TYPE-ARG", "useReducer<React.Reducer<...>> type argument", UG19, "The new best practice is not to pass type arguments to useReducer .",
  r'((call_expression function: (identifier) @f type_arguments: (type_arguments) @t) @match (#eq? @f "useReducer") (#match? @t "Reducer\\s*<"))',
  "const [s, d] = useReducer<React.Reducer<State, Action>>(reducer, init);\n", "const [s, d] = useReducer(reducer, init);\n",
  "React 19 types infer from the reducer; drop the type argument or pass <State, [Action]>.", sev="minor", kind="migration", cat="compatibility", applies=R19,
  lang="typescript", docv="@types/react 19")

# ------------------------------------------------------------------ Rules of Hooks / purity (eslint-plugin-react-hooks)
HOOK = "^use[A-Z0-9]"
ROH = R + "reference/rules/rules-of-hooks"
P("HOOK-CONDITIONAL", "Hook called conditionally / in a loop", ROH,
  "Don’t call Hooks inside loops, conditions, nested functions, or try / catch / finally blocks.",
  "\n".join(f'(({s} (statement_block [(expression_statement (call_expression function: (identifier) @f)) (lexical_declaration (variable_declarator value: (call_expression function: (identifier) @f)))] @match)) (#match? @f "{HOOK}"))'
            for s in ["if_statement consequence:", "else_clause", "for_statement body:", "for_in_statement body:", "while_statement body:", "try_statement body:"]),
  COMP("  if (enabled) {\n    const [v, setV] = useState(0);\n  }\n  return null;\n"), COMP("  const [v, setV] = useState(0);\n  if (!enabled) return null;\n  return v;\n"),
  "Hooks must run in the same order every render; move the call to the top level (React 19's use() is the only exception).", sev="critical",
  kind="anti-pattern", cat="correctness", xref=[LINT.rsplit("/lints/", 1)[0]])
P("HOOK-IN-CALLBACK", "Hook called inside a callback", ROH,
  "Don’t call Hooks inside loops, conditions, nested functions, or try / catch / finally blocks.",
  f'((arguments (arrow_function body: (call_expression function: (identifier) @f) @match)) (#match? @f "{HOOK}"))' + "\n"
  + f'((arguments (arrow_function body: (statement_block (lexical_declaration (variable_declarator value: (call_expression function: (identifier) @f))) @match))) (#match? @f "{HOOK}"))',
  COMP("  const values = items.map((item) => useMemo(() => format(item), [item]));\n  return values;\n"),
  COMP("  const values = useMemo(() => items.map(format), [items]);\n  return values;\n"),
  "Hooks can't be called inside callbacks; lift the hook or extract a child component.", sev="critical", kind="anti-pattern", cat="correctness")
P("SET-STATE-IN-RENDER", "setState called unconditionally during render", LINT + "set-state-in-render",
  "Calling setState during render unconditionally triggers another render before the current one finishes.",
  r'((function_declaration name: (identifier) @c body: (statement_block (expression_statement (call_expression function: (identifier) @f)) @match)) (#match? @c "^[A-Z]") (#match? @f "^set[A-Z]"))',
  "function Counter({ value }) {\n  const [count, setCount] = useState(0);\n  setCount(value);\n  return count;\n}\n",
  "function Counter({ value }) {\n  const count = value;\n  return count;\n}\n",
  "Infinite re-render loop; derive the value during render instead.", sev="critical", kind="anti-pattern", cat="correctness")
P("SET-STATE-IN-EFFECT", "Synchronous setState at the top of an effect", LINT + "set-state-in-effect",
  "Setting state immediately inside an effect forces React to restart the entire render cycle.",
  r'((call_expression function: (identifier) @e arguments: (arguments . (arrow_function body: (statement_block . (expression_statement (call_expression function: (identifier) @f)) @match)))) (#match? @e "^(useEffect|useLayoutEffect)$") (#match? @f "^set[A-Z]"))',
  "function List({ items }) {\n  const [visible, setVisible] = useState([]);\n  useEffect(() => {\n    setVisible(items.filter((i) => i.on));\n  }, [items]);\n  return visible.length;\n}\n",
  "function List({ items }) {\n  const visible = items.filter((i) => i.on);\n  return visible.length;\n}\n",
  "Derived state in an effect costs an extra render pass; compute it during render (or useMemo).", sev="minor", kind="anti-pattern", cat="performance",
  mode="ai-confirm", ai="Is this state derivable from props/state (not synchronizing with an external system)?", xref=[R + "learn/you-might-not-need-an-effect"])
P("IMPURE-RENDER", "Math.random()/Date.now() during render", LINT + "purity",
  "When components use functions like Math.random() or Date.now() during render, they produce different output each time",
  r'((function_declaration name: (identifier) @c body: (statement_block (lexical_declaration (variable_declarator value: (call_expression function: (member_expression object: (identifier) @o property: (property_identifier) @p)))) @match)) (#match? @c "^[A-Z]") (#match? @o "^(Math|Date|performance|crypto)$") (#match? @p "^(random|now|randomUUID)$"))',
  "function Id() {\n  const id = Math.random();\n  return id;\n}\n", "function Id() {\n  const id = useId();\n  return id;\n}\n",
  "Impure render output breaks hydration and memoization; use useId/useState initializer/effects.", sev="major", kind="anti-pattern", cat="correctness")
P("NESTED-COMPONENT-DEFINITION", "Component defined inside another component", LINT + "static-components",
  "Components defined inside other components are recreated on every render.",
  r'((function_declaration name: (identifier) @p body: (statement_block (function_declaration name: (identifier) @c) @match)) (#match? @p "^[A-Z]") (#match? @c "^[A-Z]"))' + "\n"
  + r'((function_declaration name: (identifier) @p body: (statement_block (lexical_declaration (variable_declarator name: (identifier) @c value: (arrow_function))) @match)) (#match? @p "^[A-Z]") (#match? @c "^[A-Z]"))',
  "function Parent() {\n  function Child() {\n    return null;\n  }\n  return Child;\n}\n", "function Child() {\n  return null;\n}\nfunction Parent() {\n  return Child;\n}\n",
  "Each render creates a new component type, remounting the subtree and losing its state; define it at module level.", sev="major", kind="anti-pattern",
  cat="correctness", xref=[LINT + "component-hook-factories"])
P("USEMEMO-NO-RETURN", "useMemo callback without return", LINT + "use-memo", "Without a return value, useMemo returns undefined",
  r'((call_expression function: (identifier) @f arguments: (arguments . (arrow_function body: (statement_block) @b))) @match (#eq? @f "useMemo") (#not-match? @b "\\breturn\\b"))',
  COMP("  const v = useMemo(() => {\n    track(data);\n  }, [data]);\n  return v;\n"), COMP("  const v = useMemo(() => {\n    return compute(data);\n  }, [data]);\n  return v;\n"),
  "useMemo is for values; use useEffect for side effects or return the value.", sev="major", kind="anti-pattern", cat="correctness")
P("TRY-CATCH-AROUND-JSX", "try/catch around JSX (use an Error Boundary)", LINT + "error-boundaries",
  "Try/catch blocks can’t catch errors that happen during React’s rendering process.",
  '(try_statement body: (statement_block (return_statement [(jsx_element) (jsx_self_closing_element) (parenthesized_expression)] @r))) @match',
  "function Parent() {\n  try {\n    return <Child />;\n  } catch (e) {\n    return <Fallback />;\n  }\n}\n",
  "function Parent() {\n  return (\n    <ErrorBoundary fallback={<Fallback />}>\n      <Child />\n    </ErrorBoundary>\n  );\n}\n",
  "Rendering happens later, outside the try; wrap children in an Error Boundary.", sev="major", kind="anti-pattern", cat="correctness", lang="jsx",
  filters=[r"node.has_re:<[A-Za-z]"])
P("COMPONENT-CALLED-AS-FUNCTION", "Component called as a function", R + "reference/rules/react-calls-components-and-hooks",
  "Components should only be used in JSX. Don’t call them as regular functions.",
  r'((jsx_expression (call_expression function: (identifier) @f arguments: (arguments . ")")) @match) (#match? @f "^[A-Z][a-z]+[A-Z]?[A-Za-z]*$"))',
  "const page = <main>{Header()}</main>;\n", "const page = <main><Header /></main>;\n",
  "Calling a component bypasses React (hooks attach to the caller, no reconciliation); render it as <Header />.", sev="major", kind="anti-pattern",
  cat="correctness", lang="jsx", mode="ai-confirm", ai="Is the callee a React component (returns JSX / uses hooks), not a plain helper?")
P("EFFECT-NO-DEPS", "useEffect without a dependency array", R + "reference/react/useEffect", "If you omit this argument, your Effect will re-run after every commit of the component.",
  r'((call_expression function: (identifier) @f arguments: (arguments . (arrow_function) .)) @match (#match? @f "^(useEffect|useLayoutEffect)$"))',
  COMP("  useEffect(() => {\n    subscribe(id);\n  });\n  return null;\n"), COMP("  useEffect(() => {\n    subscribe(id);\n  }, [id]);\n  return null;\n"),
  "Runs after every render (often a loop with setState or resubscribes); pass the dependencies.", sev="minor", kind="anti-pattern", cat="performance",
  mode="ai-confirm", ai="Is running after every render unintended here?")
P("EFFECT-ASYNC-CALLBACK", "async function passed to useEffect", R + "reference/react/useEffect", "You can also rewrite using the async / await syntax, but you still need to provide a cleanup function",
  r'((call_expression function: (identifier) @f arguments: (arguments . (arrow_function) @a)) @match (#match? @f "^(useEffect|useLayoutEffect)$") (#match? @a "^async\\b"))',
  COMP("  useEffect(async () => {\n    setData(await load(id));\n  }, [id]);\n  return null;\n"),
  COMP("  useEffect(() => {\n    let ignore = false;\n    load(id).then((d) => { if (!ignore) setData(d); });\n    return () => { ignore = true; };\n  }, [id]);\n  return null;\n"),
  "An async effect returns a Promise, not a cleanup, so races can't be cancelled; define an inner async function and an ignore flag/AbortController.",
  sev="major", kind="anti-pattern", cat="correctness")
P("FETCH-EFFECT-NO-CLEANUP", "Data fetch in effect without race guard", R + "reference/react/useEffect",
  "This ensures your code doesn’t suffer from “race conditions”: network responses may arrive in a different order than you sent them.",
  r'((call_expression function: (identifier) @f arguments: (arguments . (arrow_function body: (statement_block) @b))) @match (#match? @f "^useEffect$") (#match? @b "\\b(fetch|axios|load[A-Z]\\w*)\\s*\\(") (#not-match? @b "return\\s*\\(?\\s*\\)?\\s*=>|abort|ignore|cancel"))',
  COMP("  useEffect(() => {\n    fetch(url).then((r) => r.json()).then(setData);\n  }, [url]);\n  return null;\n"),
  COMP("  useEffect(() => {\n    const c = new AbortController();\n    fetch(url, { signal: c.signal }).then((r) => r.json()).then(setData);\n    return () => c.abort();\n  }, [url]);\n  return null;\n"),
  "Without cleanup, a slow earlier response can overwrite a newer one; abort or ignore stale responses.", sev="minor", kind="anti-pattern", cat="correctness",
  mode="ai-confirm", ai="Can the dependency change while a request is in flight (so a stale response could win)?")
P("MANUAL-MEMO-WITH-COMPILER", "Manual useMemo/useCallback/memo (React Compiler)", R + "learn/react-compiler/introduction",
  "unless you have applied some form of manual memoization with useMemo() , useCallback() , or React.memo() .",
  call("useMemo|useCallback") + "\n" + mem("React", "memo|useMemo|useCallback"),
  COMP("  const onClick = useCallback(() => select(id), [id]);\n  return onClick;\n"), COMP("  const onClick = () => select(id);\n  return onClick;\n"),
  "With React Compiler enabled, manual memoization is usually redundant noise.", sev="info", kind="best-practice", cat="simplification", applies=R19,
  mode="ai-confirm", ai="Is React Compiler (babel-plugin-react-compiler) enabled for this file and is this memo not needed for an external API identity?")

# ------------------------------------------------------------------ lists / keys
P("JSX-KEY-MISSING", "Element in map() without key", R + "learn/rendering-lists", "JSX elements directly inside a map() call always need keys!",
  r'((call_expression function: (member_expression property: (property_identifier) @m) arguments: (arguments (arrow_function body: [(jsx_element open_tag: (jsx_opening_element) @o) (jsx_self_closing_element) @o (parenthesized_expression (jsx_element open_tag: (jsx_opening_element) @o)) (parenthesized_expression (jsx_self_closing_element) @o)]))) @match (#eq? @m "map") (#not-match? @o "\\bkey\\s*="))',
  "const list = items.map((item) => <li>{item.name}</li>);\n", "const list = items.map((item) => <li key={item.id}>{item.name}</li>);\n",
  "Missing keys make React reuse the wrong DOM/state when items move; use a stable id.", sev="major", kind="anti-pattern", cat="correctness", lang="jsx")
P("JSX-KEY-INDEX", "Array index used as key", R + "learn/rendering-lists", "You might be tempted to use an item’s index in the array as its key.",
  r'((arrow_function parameters: (formal_parameters (_) (_) @i) body: (_) @b) @match (#match? @b "key=\\{\\s*(index|idx|i)\\s*\\}") (#match? @i "^(index|idx|i)\\b"))',
  "const list = items.map((item, index) => <li key={index}>{item.name}</li>);\n", "const list = items.map((item) => <li key={item.id}>{item.name}</li>);\n",
  "Index keys break state and animations when the list is reordered/filtered; use a stable id.", sev="minor", kind="anti-pattern", cat="correctness", lang="jsx",
  mode="ai-confirm", ai="Can this list be reordered, filtered or have items inserted (so index keys are unstable)?")
P("JSX-KEY-GENERATED", "Key generated during render", R + "learn/rendering-lists", "Keys must not change or that defeats their purpose! Don’t generate them while rendering.",
  r'((jsx_attribute (property_identifier) @a (jsx_expression (call_expression) @c)) @match (#eq? @a "key") (#match? @c "^(Math\\.random|crypto\\.randomUUID|uuid|uuidv4|nanoid|Date\\.now)\\b"))',
  "const list = items.map((item) => <li key={Math.random()}>{item.name}</li>);\n", "const list = items.map((item) => <li key={item.id}>{item.name}</li>);\n",
  "New keys each render remount every item (lost state, slow); use stable ids from the data.", sev="major", kind="anti-pattern", cat="performance", lang="jsx")

# ------------------------------------------------------------------ security
P("DANGEROUSLY-SET-INNER-HTML", "dangerouslySetInnerHTML without sanitization", R + "reference/react-dom/components/common",
  "This should be used with extreme caution! If the HTML inside isn’t trusted (for example, if it’s based on user da",
  r'((jsx_attribute (property_identifier) @a (jsx_expression) @v) @match (#eq? @a "dangerouslySetInnerHTML") (#not-match? @v "(?i)sanitize|purify|escape"))',
  "const el = <div dangerouslySetInnerHTML={{ __html: comment.body }} />;\n", "const el = <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(comment.body) }} />;\n",
  "Raw HTML from data is an XSS vector; sanitize (DOMPurify / Trusted Types) or render text.", sev="major", kind="security", cat="security", lang="jsx",
  quote="This should be used with extreme caution! If the HTML inside isn’t trusted (for example, if it’s based on user data), you risk introducing an XSS vulnerability.")
P("JAVASCRIPT-URL", "javascript: URL in href/src", UG19, "Error for javascript URLs in src and href",
  r'((jsx_attribute (property_identifier) @a (string) @v) @match (#match? @a "^(href|src|action|formAction)$") (#match? @v "^.\\s*javascript:"))',
  "const a = <a href=\"javascript:void(0)\">Open</a>;\n", "const a = <button type=\"button\" onClick={open}>Open</button>;\n",
  "javascript: URLs are an XSS sink and React 19 errors on them; use an onClick handler.", sev="major", kind="security", cat="security", lang="jsx", docv="React 19")
P("SERVER-FUNCTION-NO-AUTH", "Server Function without authorization check", R + "reference/rsc/use-server",
  "Always treat arguments to Server Functions as untrusted input and authorize any mutations.",
  r'((program (expression_statement (string (string_fragment) @d)) (export_statement declaration: (function_declaration body: (statement_block) @b) @match)) (#eq? @d "use server") (#not-match? @b "(?i)auth|session|currentUser|getUser|verify|permission|can[A-Z]"))',
  "'use server';\nexport async function deletePost(id) {\n  await db.post.delete({ where: { id } });\n}\n",
  "'use server';\nexport async function deletePost(id) {\n  const user = await auth();\n  if (!user?.canDelete(id)) throw new Error('forbidden');\n  await db.post.delete({ where: { id } });\n}\n",
  "Server Functions are public HTTP endpoints; authenticate, authorize and validate inside every one.", sev="critical", kind="security", cat="security",
  applies=R19, filters=[r"file.has_re:\A(?:\s|//[^\n]*|/\*(?s:.*?)\*/)*['\"]use server['\"]"], mode="ai-confirm", ai="Does this exported Server Function mutate data or read private data without an auth/authorization check (directly or in a helper)?")
P("USE-DIRECTIVE-NOT-FIRST", "'use client'/'use server' after imports", R + "reference/rsc/use-client",
  "Add 'use client' at the top of a file to mark the module and its transitive dependencies as client code.",
  r'((program (import_statement) (expression_statement (string (string_fragment) @d)) @match) (#match? @d "^use (client|server)$"))',
  "import { useState } from 'react';\n'use client';\nexport default function A() {\n  return useState(0);\n}\n",
  "'use client';\nimport { useState } from 'react';\nexport default function A() {\n  return useState(0);\n}\n",
  "Directives only count as the first statement; after imports it's a no-op string.", sev="major", kind="anti-pattern", cat="correctness", applies=R19)

# ------------------------------------------------------------------ class components
P("UNSAFE-LEGACY-LIFECYCLE", "Legacy lifecycle (componentWillMount/ReceiveProps/Update)", R + "reference/react/Component",
  "UNSAFE_componentWillMount() UNSAFE_componentWillReceiveProps(nextProps, nextContext) UNSAFE_componentWillUpdate(nextProps, nextState)",
  r'((method_definition name: (property_identifier) @m) @match (#match? @m "^(UNSAFE_)?(componentWillMount|componentWillReceiveProps|componentWillUpdate)$"))',
  "class A extends React.Component {\n  componentWillReceiveProps(next) {\n    this.setState({ v: next.v });\n  }\n}\n",
  "class A extends React.Component {\n  static getDerivedStateFromProps(props) {\n    return { v: props.v };\n  }\n}\n",
  "These lifecycles are unsafe with concurrent rendering; use componentDidMount/componentDidUpdate/getDerivedStateFromProps.", sev="minor",
  kind="deprecation", cat="compatibility", applies={"react": ">=16.3"})
P("CLASS-COMPONENT", "Class component in new code", R + "reference/react/Component", "We recommend defining components as functions instead of classes.",
  r'((class_declaration (class_heritage) @h body: (class_body) @b) @match (#match? @h "(Pure)?Component\\b") (#not-match? @b "componentDidCatch|getDerivedStateFromError"))',
  "class Greeting extends Component {\n  render() {\n    return null;\n  }\n}\n", "function Greeting() {\n  return null;\n}\n",
  "Function components + hooks are the supported path (compiler, server components); keep classes only for error boundaries.", sev="info",
  kind="best-practice", cat="maintainability", mode="ai-confirm", ai="Is this new/actively developed code (not a stable legacy component)?")
P("STATE-MUTATION", "Direct this.state mutation", R + "reference/react/Component", "Do not mutate the state directly.",
  r'((assignment_expression left: (member_expression object: (member_expression object: (this) property: (property_identifier) @s))) @match (#eq? @s "state"))' + "\n"
  + r'((call_expression function: (member_expression object: (member_expression object: (member_expression object: (this) property: (property_identifier) @s)) property: (property_identifier) @m)) @match (#eq? @s "state") (#match? @m "^(push|pop|shift|unshift|splice|sort|reverse)$"))',
  "class A extends React.Component {\n  add() {\n    this.state.items.push(1);\n  }\n}\n", "class A extends React.Component {\n  add() {\n    this.setState((s) => ({ items: [...s.items, 1] }));\n  }\n}\n",
  "Mutations don't re-render and corrupt batched updates; call setState with a new object.", sev="major", kind="anti-pattern", cat="correctness",
  xref=[R + "reference/rules/components-and-hooks-must-be-pure"])
P("SETSTATE-FROM-THIS-STATE", "setState computed from this.state (use updater)", R + "reference/react/Component",
  "If you pass a function as nextState , it will be treated as an updater function .",
  r'((call_expression function: (member_expression object: (this) property: (property_identifier) @f) arguments: (arguments . (object) @o)) @match (#eq? @f "setState") (#match? @o "this\\.state\\."))',
  "class A extends React.Component {\n  inc() {\n    this.setState({ n: this.state.n + 1 });\n  }\n}\n", "class A extends React.Component {\n  inc() {\n    this.setState((s) => ({ n: s.n + 1 }));\n  }\n}\n",
  "Updates are batched, so this.state may be stale; use the updater form.", sev="minor", kind="anti-pattern", cat="correctness")

RULES = P.R

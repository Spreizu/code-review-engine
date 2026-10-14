"""Go pack: go vet analyzers, gopls/go fix modernizers (with the Go version each needs), stdlib deprecations,
crypto/security notes from package docs, Effective Go. Version dimension `go` comes from go.mod."""
from specs._common import Pack

PKG = "https://pkg.go.dev/"
VET = PKG + "golang.org/x/tools/go/analysis/passes/"
MOD = VET + "modernize"
P = Pack("GO", "go", "Go 1.27", {"go": "*"})


def sel(pkg, fn):
    """selector pkg.fn (fn may be a regex alternation)."""
    fp = f'(#eq? @f "{fn}")' if fn.isidentifier() else f'(#match? @f "^({fn})$")'
    return f'(selector_expression operand: (identifier) @p (#eq? @p "{pkg}") field: (field_identifier) @f {fp})'


def call(pkg, fn, args="", cap="@match"):
    return f'(call_expression function: {sel(pkg, fn)} arguments: (argument_list{(" " + args) if args else ""})) {cap}'


IMP = lambda path: f'file.has_re:"{path}"'
v = lambda name: VET + name

# ---------------------------------------------------------------- go vet analyzers
P("VET-COPYLOCKS", "sync type passed by value", "https://pkg.go.dev/cmd/vet", "copylocks check for locks erroneously passed by value",
  '(parameter_declaration type: (qualified_type package: (package_identifier) @p (#eq? @p "sync") name: (type_identifier) @match (#match? @match "^(Mutex|RWMutex|WaitGroup|Once|Cond|Map|Pool)$")))',
  "func work(mu sync.Mutex) {}\n", "func work(mu *sync.Mutex) {}\n", "Copying a lock copies its state; pass a pointer.", sev="major", cat="concurrency", doc="go vet copylocks")
P("VET-LOSTCANCEL", "Context cancel function discarded", v("lostcancel"), "The cancellation function returned by context.WithCancel",
  '(short_var_declaration left: (expression_list (identifier) (identifier) @match (#eq? @match "_")) right: (expression_list (call_expression function: ' + sel("context", "WithCancel|WithTimeout|WithDeadline|WithCancelCause|WithTimeoutCause|WithDeadlineCause") + ')))',
  "func f() {\n\tctx, _ := context.WithTimeout(parent, time.Second)\n\tuse(ctx)\n}\n", "func f() {\n\tctx, cancel := context.WithTimeout(parent, time.Second)\n\tdefer cancel()\n\tuse(ctx)\n}\n",
  "Discarding cancel leaks the context's resources until the parent is done.", sev="major", cat="concurrency", doc="go vet lostcancel")
P("VET-HTTPRESPONSE", "resp.Body.Close deferred before the error check", v("httpresponse"), "defines an Analyzer that checks for mistakes using HTTP responses",
  '(statement_list (short_var_declaration left: (expression_list (identifier) @r (identifier)) right: (expression_list (call_expression function: (selector_expression operand: (identifier) @h (#match? @h "^(http|client|c)$"))))) . (defer_statement (call_expression function: (selector_expression operand: (selector_expression operand: (identifier) @r2 field: (field_identifier) @b (#eq? @b "Body"))))) @match (#eq? @r @r2))',
  "func f() {\n\tresp, err := http.Get(u)\n\tdefer resp.Body.Close()\n\t_ = err\n}\n",
  "func f() error {\n\tresp, err := http.Get(u)\n\tif err != nil {\n\t\treturn err\n\t}\n\tdefer resp.Body.Close()\n\treturn nil\n}\n",
  "If err != nil, resp is nil and the deferred Close panics; check err first.", sev="major", cat="correctness", doc="go vet httpresponse")
P("VET-ERRORSAS", "errors.As target may not be a pointer", v("errorsas"), "checks that the second argument to errors.As is a pointer to a type implementing error", call("errors", "As", "(_) (identifier)"),
  "func f(err error) {\n\tvar pe *fs.PathError\n\tif errors.As(err, pe) {}\n}\n", "func f(err error) {\n\tvar pe *fs.PathError\n\tif errors.As(err, &pe) {}\n}\n",
  "errors.As needs a pointer to an interface or to a type implementing error; it panics otherwise.", sev="major", cat="correctness",
  mode="ai-confirm", ai="Is the second argument of errors.As a non-pointer value (rather than a variable already of pointer-to-target type)?", doc="go vet errorsas")
P("VET-STRINGINTCONV", "string(int) conversion", v("stringintconv"), "check for string(int) conversions",
  '(call_expression function: (identifier) @s (#eq? @s "string") arguments: (argument_list (int_literal))) @match', 'var s = string(65)\n', 'var s = string(rune(65))\n',
  "string(int) yields a rune, not decimal digits; use strconv.Itoa or string(rune(x)).", sev="major", cat="correctness", doc="go vet stringintconv")
P("VET-UNUSEDRESULT", "Result of a pure function discarded", v("unusedresult"), "check for unused results of calls to some functions",
  '(expression_statement (call_expression function: (selector_expression operand: (identifier) @p field: (field_identifier) @f)) @match (#match? @p "^(fmt|errors|strings|bytes|sort|slices|maps)$") (#match? @f "^(Sprint|Sprintf|Sprintln|Errorf|New|Clone|Compact|Repeat|ToLower|ToUpper|TrimSpace|Replace|ReplaceAll|Join|Split|Fields)$"))',
  'func f() {\n\tfmt.Sprintf("%d", 1)\n}\n', 'func f() string {\n\treturn fmt.Sprintf("%d", 1)\n}\n', "The call has no side effects; its result is the only point.",
  sev="major", cat="correctness", doc="go vet unusedresult")
P("VET-ASSIGN", "Self-assignment", v("assign"), "check for useless assignments",
  '(assignment_statement left: (expression_list . (_) @a .) operator: "=" right: (expression_list . (_) @match .) (#eq? @a @match))',
  "func f() {\n\tx = x\n}\n", "func f() {\n\tx = y\n}\n", "x = x has no effect (often a typo).", sev="major", cat="correctness", doc="go vet assign")
P("VET-BOOLS", "Redundant or suspicious boolean expression", v("bools"), "check for common mistakes involving boolean operators",
  '(binary_expression left: (_) @a operator: ["||" "&&"] right: (_) @match (#eq? @a @match))', "var ok = a == b || a == b\n", "var ok = a == b || a == c\n",
  "Both operands are identical.", sev="major", cat="correctness", doc="go vet bools",
  filters=[r"cap.lacks_re:a:\(|<-"])  # calls and channel receives may yield different values each time
P("VET-ATOMIC", "Result of atomic.Add assigned to its own operand", v("atomic"), "check for common mistakes using the sync/atomic package",
  '(assignment_statement left: (expression_list (identifier) @x) right: (expression_list (call_expression function: ' + sel("atomic", "AddInt32|AddInt64|AddUint32|AddUint64|AddUintptr") + ' arguments: (argument_list (unary_expression operand: (identifier) @y) (_)))) (#eq? @x @y)) @match',
  "func f() {\n\tx = atomic.AddInt64(&x, 1)\n}\n", "func f() {\n\tatomic.AddInt64(&x, 1)\n}\n", "The plain assignment races with the atomic update.",
  sev="major", cat="concurrency", doc="go vet atomic")
P("VET-DEEPEQUALERRORS", "reflect.DeepEqual on errors", v("deepequalerrors"), "checks for the use of reflect.DeepEqual with error values",
  call("reflect", "DeepEqual", '(identifier) @a (#match? @a "(?i)err")'), "func f() bool {\n\treturn reflect.DeepEqual(err, io.EOF)\n}\n",
  "func f() bool {\n\treturn errors.Is(err, io.EOF)\n}\n", "Errors carry unexported state (stack, wrapping); compare with errors.Is.", sev="minor", cat="correctness", doc="go vet deepequalerrors")
P("VET-UNMARSHAL", "Unmarshal into a non-pointer", v("unmarshal"), "report passing non-pointer or non-interface values to unmarshal",
  '(call_expression function: (selector_expression operand: (identifier) @p (#match? @p "^(json|xml|yaml|gob|asn1)$") field: (field_identifier) @f (#eq? @f "Unmarshal")) arguments: (argument_list (_) [(identifier) (composite_literal) (selector_expression)] @match))',
  "func f() {\n\tvar c Config\n\tjson.Unmarshal(b, c)\n}\n", "func f() {\n\tvar c Config\n\tjson.Unmarshal(b, &c)\n}\n",
  "Unmarshal needs a pointer; with a value it returns InvalidUnmarshalError and fills nothing.", sev="major", cat="correctness",
  mode="ai-confirm", ai="Is the destination argument a non-pointer value (not a variable that already holds a pointer or interface)?", doc="go vet unmarshal",
  filters=[r"func.lacks_re:\b{cap:match}\s+(any\b|interface\s*\{|\*)|\b{cap:match}\s*:?=\s*(&|new\()"],
  fp=["func readJSON(p string, v any) error {\n\tb, err := os.ReadFile(p)\n\tif err != nil {\n\t\treturn err\n\t}\n\treturn json.Unmarshal(b, v)\n}\n",
      "func f(b []byte) {\n\tc := &Config{}\n\tjson.Unmarshal(b, c)\n}\n"])
P("VET-TIMEFORMAT", "Time layout 2006-02-01 (day/month swapped)", v("timeformat"), "2006-02-01",
  '(call_expression function: (selector_expression field: (field_identifier) @f (#match? @f "^(Format|Parse|ParseInLocation|AppendFormat)$")) arguments: (argument_list (interpreted_string_literal) @match (#match? @match "2006-02-01")))',
  'var s = t.Format("2006-02-01")\n', 'var s = t.Format("2006-01-02")\n', "The reference layout is 2006-01-02; 02-01 swaps month and day.", sev="major", cat="correctness", doc="go vet timeformat")
P("VET-DEFERS", "defer evaluates time.Since immediately", v("defers"), "time.Since",
  '(defer_statement (call_expression arguments: (argument_list (call_expression function: ' + sel("time", "Since") + ') @match)))',
  "func f() {\n\tstart := time.Now()\n\tdefer log.Println(time.Since(start))\n}\n", "func f() {\n\tstart := time.Now()\n\tdefer func() { log.Println(time.Since(start)) }()\n}\n",
  "Deferred call arguments are evaluated at the defer statement, so this logs ~0s.", sev="major", cat="correctness", doc="go vet defers")
P("VET-APPENDS", "append with a single argument", v("appends"), "check for missing values after append",
  '(call_expression function: (identifier) @a (#eq? @a "append") arguments: (argument_list . (_) .)) @match', "func f() {\n\ts = append(s)\n}\n",
  "func f() {\n\ts = append(s, x)\n}\n", "append(s) appends nothing.", sev="minor", cat="correctness", doc="go vet appends")
P("VET-SIGCHANYZER", "Unbuffered channel passed to signal.Notify", v("sigchanyzer"), "check for unbuffered channel of os.Signal",
  '(short_var_declaration left: (expression_list (identifier) @match) right: (expression_list (call_expression function: (identifier) @m (#eq? @m "make") arguments: (argument_list (channel_type) .))))',
  "func f() {\n\tc := make(chan os.Signal)\n\tsignal.Notify(c, os.Interrupt)\n}\n", "func f() {\n\tc := make(chan os.Signal, 1)\n\tsignal.Notify(c, os.Interrupt)\n}\n",
  "signal.Notify does not block; an unbuffered channel can miss the signal.", sev="major", cat="concurrency", doc="go vet sigchanyzer",
  filters=[r"file.count_ge:1:signal\.Notify\(\s*{text}\b"])
P("VET-WAITGROUP-ADD-IN-GOROUTINE", "WaitGroup.Add called inside the goroutine", v("waitgroup"), "check for misuses of sync.WaitGroup",
  '(go_statement (call_expression function: (func_literal body: (block (statement_list . (expression_statement (call_expression function: (selector_expression field: (field_identifier) @a (#eq? @a "Add"))) @match))))))',
  "func f() {\n\tgo func() {\n\t\twg.Add(1)\n\t\tdefer wg.Done()\n\t}()\n}\n", "func f() {\n\twg.Add(1)\n\tgo func() {\n\t\tdefer wg.Done()\n\t}()\n}\n",
  "Add inside the goroutine races with Wait; call Add before `go` (or use wg.Go on Go 1.25+).", sev="major", cat="concurrency", doc="go vet waitgroup")
P("VET-HOSTPORT", "host:port built with Sprintf for net.Dial", v("hostport"), "which work only with IPv4",
  '(call_expression function: ' + sel("net", "Dial|DialTimeout|Listen") + ' arguments: (argument_list (_) (call_expression function: (selector_expression operand: (identifier) @x (#eq? @x "fmt") field: (field_identifier) @s (#eq? @s "Sprintf")) arguments: (argument_list (interpreted_string_literal) @match (#match? @match "^\\"%[sv]:%[dsv]\\"$")))))',
  'func f() {\n\tnet.Dial("tcp", fmt.Sprintf("%s:%d", host, port))\n}\n', 'func f() {\n\tnet.Dial("tcp", net.JoinHostPort(host, strconv.Itoa(port)))\n}\n',
  "Sprintf breaks IPv6 literals; use net.JoinHostPort.", sev="minor", cat="correctness", doc="go vet hostport")
P("VET-TESTINGGOROUTINE", "t.Fatal called from a goroutine", v("testinggoroutine"), "report calls to (*testing.T).Fatal from goroutines started by a test",
  '(go_statement (call_expression function: (func_literal body: (block (statement_list (expression_statement (call_expression function: (selector_expression operand: (identifier) @t (#match? @t "^(t|b|tb)$") field: (field_identifier) @match (#match? @match "^(Fatal|Fatalf|FailNow|SkipNow|Skip|Skipf)$")))))))))',
  "func TestX(t *testing.T) {\n\tgo func() {\n\t\tt.Fatal(\"x\")\n\t}()\n}\n", "func TestX(t *testing.T) {\n\tgo func() {\n\t\tt.Error(\"x\")\n\t}()\n}\n",
  "FailNow/Fatal must run on the test goroutine; from others they do not stop the test.", sev="major", cat="testing", doc="go vet testinggoroutine")
P("VET-LOOPCLOSURE", "Goroutine/defer closure captures a loop variable (pre-1.22)", v("loopclosure"), "check references to loop variables from within nested functions",
  '(for_statement (range_clause) body: (block (statement_list [(go_statement (call_expression function: (func_literal) @match arguments: (argument_list) @args)) (defer_statement (call_expression function: (func_literal) @match arguments: (argument_list) @args))])) (#eq? @args "()"))',
  "func f() {\n\tfor _, v := range s {\n\t\tgo func() { use(v) }()\n\t}\n}\n", "func f() {\n\tfor _, v := range s {\n\t\tgo func(v T) { use(v) }(v)\n\t}\n}\n",
  "Before Go 1.22 all iterations share one loop variable; the closure sees the last value.", sev="major", cat="concurrency",
  applies={"go": "<1.22"}, mode="ai-confirm", ai="Does the closure reference the range loop's key/value variable?", doc="go vet loopclosure")
P("VET-STRUCTTAG", "Malformed struct tag", PKG + "reflect#StructTag", "By convention, tag strings are a concatenation of optionally space-separated key:\"value\" pairs.",
  '((raw_string_literal) @match (#match? @match "^`(json|xml|yaml|db|toml|form|validate):[^\\"]"))', "type T struct {\n\tA int `json:a`\n}\n",
  "type T struct {\n\tA int `json:\"a\"`\n}\n", "Tag values must be quoted (key:\"value\").", sev="major", cat="correctness", doc="reflect.StructTag")
P("VET-BUILDTAG", "// +build without //go:build", v("buildtag"), "check //go:build and // +build directives",
  '((comment) @match (#match? @match "^// ?[+]build "))', "// +build linux\n\npackage x\n", "//go:build linux\n\npackage x\n",
  "Go 1.17+ uses //go:build; gofmt/`go fix` add it and keep the two in sync.", sev="minor", kind="migration", cat="build",
  applies={"go": ">=1.17"}, filters=["file.lacks_re://go:build"], doc="go vet buildtag")
# ---------------------------------------------------------------- deprecations
P("IOUTIL", "io/ioutil is deprecated", PKG + "io/ioutil", "As of Go 1.16, the same functionality is now provided by package io or package os",
  '(import_spec path: (interpreted_string_literal) @match (#eq? @match "\\"io/ioutil\\""))', 'import "io/ioutil"\n', 'import "os"\n',
  "Use io.ReadAll, os.ReadFile, os.WriteFile, os.ReadDir, os.MkdirTemp, os.CreateTemp.", sev="minor", kind="deprecation", cat="deprecation",
  applies={"go": ">=1.16"})
P("RAND-SEED", "math/rand.Seed is deprecated", PKG + "math/rand#Seed", "As of Go 1.20 there is no reason to call Seed with a random value.",
  call("rand", "Seed"), 'import "math/rand"\n\nfunc init() {\n\trand.Seed(time.Now().UnixNano())\n}\n', 'import "math/rand"\n\nfunc init() {}\n',
  "The global source is randomly seeded since Go 1.20; use rand.New(rand.NewSource(x)) for determinism.", sev="minor", kind="deprecation",
  cat="deprecation", applies={"go": ">=1.20"}, filters=[IMP("math/rand")])
P("RAND-V2", "math/rand instead of math/rand/v2", PKG + "math/rand/v2", "Package rand implements pseudo-random number generators suitable for tasks such as simulation",
  '(import_spec path: (interpreted_string_literal) @match (#eq? @match "\\"math/rand\\""))', 'import "math/rand"\n', 'import "math/rand/v2"\n',
  "math/rand/v2 (Go 1.22) has better generators and a cleaner API.", sev="info", kind="modernization", cat="modernization", applies={"go": ">=1.22"})
P("STRINGS-TITLE", "strings.Title is deprecated", PKG + "strings#Title", "Title uses for word boundaries does not handle Unicode punctuation properly",
  call("strings", "Title"), 'var s = strings.Title(name)\n', 'var s = cases.Title(language.English).String(name)\n', "Use golang.org/x/text/cases.",
  sev="minor", kind="deprecation", cat="deprecation", applies={"go": ">=1.18"})
P("REFLECT-HEADER", "reflect.SliceHeader/StringHeader are deprecated", PKG + "reflect#SliceHeader", "Use unsafe.Slice or unsafe.SliceData instead.",
  '([(qualified_type package: (package_identifier) @p name: (type_identifier) @match) (selector_expression operand: (identifier) @p field: (field_identifier) @match)] (#eq? @p "reflect") (#match? @match "^(SliceHeader|StringHeader)$"))',
  "func f(b []byte) {\n\th := (*reflect.SliceHeader)(unsafe.Pointer(&b))\n\t_ = h\n}\n", "func f(b []byte) {\n\tp := unsafe.SliceData(b)\n\t_ = p\n}\n",
  "Use unsafe.Slice/SliceData/String/StringData (Go 1.20+).", sev="minor", kind="deprecation", cat="deprecation", applies={"go": ">=1.21"})
P("X-NET-CONTEXT", "golang.org/x/net/context import", PKG + "golang.org/x/net/context", "Use the standard library context package instead.",
  '(import_spec path: (interpreted_string_literal) @match (#eq? @match "\\"golang.org/x/net/context\\""))', 'import "golang.org/x/net/context"\n',
  'import "context"\n', "Use the standard context package.", sev="minor", kind="deprecation", cat="deprecation",
  applies={"go": ">=1.7"})
P("NET-ERROR-TEMPORARY", "net.Error.Temporary is deprecated", PKG + "net#Error", "Temporary errors are not well-defined.",
  '(call_expression function: (selector_expression field: (field_identifier) @match (#eq? @match "Temporary")) arguments: (argument_list) @args (#eq? @args "()"))',
  "import \"net\"\n\nfunc f(ne net.Error) bool {\n\treturn ne.Temporary()\n}\n", "import \"net\"\n\nfunc f(ne net.Error) bool {\n\treturn ne.Timeout()\n}\n",
  "Temporary() is ill-defined; check Timeout() or specific errors.", sev="minor", kind="deprecation", cat="deprecation", filters=[IMP("net")])
P("HTTP-CLOSENOTIFIER", "http.CloseNotifier is deprecated", PKG + "net/http#CloseNotifier", "the CloseNotifier interface predates Go's context package",
  '(qualified_type package: (package_identifier) @p (#eq? @p "http") name: (type_identifier) @match (#eq? @match "CloseNotifier"))',
  "func h(w http.ResponseWriter, r *http.Request) {\n\tcn := w.(http.CloseNotifier)\n\t_ = cn\n}\n", "func h(w http.ResponseWriter, r *http.Request) {\n\t<-r.Context().Done()\n}\n",
  "Use Request.Context().", sev="minor", kind="deprecation", cat="deprecation", applies={"go": ">=1.7"})
P("SORT-STRINGS", "sort.Strings/Ints/Float64s (wrappers since Go 1.22)", PKG + "sort#Strings", "as of Go 1.22, this function simply calls slices.Sort",
  call("sort", "Strings|Ints|Float64s"), "func f(s []string) {\n\tsort.Strings(s)\n}\n", "func f(s []string) {\n\tslices.Sort(s)\n}\n",
  "Call slices.Sort directly.", sev="info", kind="modernization", cat="modernization", applies={"go": ">=1.22"})
P("SYSCALL", "syscall package (locked down)", PKG + "syscall", "most new code should prefer that package where possible",
  '(import_spec path: (interpreted_string_literal) @match (#eq? @match "\\"syscall\\""))', 'import "syscall"\n', 'import "golang.org/x/sys/unix"\n',
  "Prefer golang.org/x/sys for system calls.", sev="info", kind="best-practice", cat="portability")
P("TIME-TICK-LEAK", "time.Tick leaks before Go 1.23", PKG + "time#Tick", "Before Go 1.23, this documentation warned that the underlying Ticker would never be recovered by the garbage collector",
  call("time", "Tick"), "func f() {\n\tfor range time.Tick(time.Second) {\n\t}\n}\n", "func f() {\n\tt := time.NewTicker(time.Second)\n\tdefer t.Stop()\n\tfor range t.C {\n\t}\n}\n",
  "Before Go 1.23 an unstopped time.Tick ticker is never collected.", sev="minor", cat="resource", applies={"go": "<1.23"})
# ---------------------------------------------------------------- modernize (go fix)
M = lambda id, title, needle, query, bad, good, msg, ver, **kw: P("MOD-" + id, title, MOD, needle, query, bad, good, msg, sev=kw.pop("sev", "info"),
                                                                 kind="modernization", cat="modernization", applies={"go": ">=" + ver}, doc="gopls/go fix modernize", **kw)
M("ANY", "interface{} instead of any", "The any analyzer suggests replacing uses of the empty interface type",
  '((interface_type) @match (#eq? @match "interface{}"))', "func f(v interface{}) {}\n", "func f(v any) {}\n", "Use `any` (Go 1.18).", "1.18")
M("FORVAR", "Redundant x := x loop-variable copy", "Go 1.22 changed the semantics of `for` loops, making this pattern redundant.",
  '(for_statement (range_clause) body: (block (statement_list (short_var_declaration left: (expression_list . (identifier) @a .) right: (expression_list . (identifier) @b .)) @match)) (#eq? @a @b))',
  "func f() {\n\tfor _, x := range s {\n\t\tx := x\n\t\tgo use(x)\n\t}\n}\n", "func f() {\n\tfor _, x := range s {\n\t\tgo use(x)\n\t}\n}\n",
  "Each iteration has its own variable since Go 1.22.", "1.22")
M("RANGEINT", "3-clause loop could range over an integer", "for i := range n { ... }",
  '(for_statement (for_clause initializer: (short_var_declaration left: (expression_list . (identifier) @i .) right: (expression_list (int_literal) @z (#eq? @z "0"))) condition: (binary_expression left: (identifier) @i2 operator: "<" right: [(identifier) @n (int_literal) (call_expression function: (identifier) @len (#eq? @len "len") arguments: (argument_list . (identifier) @n .))]) update: (inc_statement (identifier) @i3)) body: (block) @body (#eq? @i @i2) (#eq? @i @i3)) @match',
  "func f() {\n\tfor i := 0; i < n; i++ {\n\t\tuse(i)\n\t}\n}\n", "func f() {\n\tfor i := range n {\n\t\tuse(i)\n\t}\n}\n",
  "`for i := range n` (Go 1.22): i and n are not modified in the body.", "1.22",
  filters=[r"node.lacks_re:\bb\.N\b",
           # the loop variable must not be assigned, incremented or address-taken in the body
           r"cap.lacks_re:body:(^|[^\w.])({cap:i}\s*(\+\+|--|[-+*/%&|^]?=[^=]|<<=|>>=|,[^:=]*[^:]=[^=])|&{cap:i}\b)",
           # nor the bound (n, or the slice in len(s))
           r"cap.lacks_re:body:(^|[^\w.]){cap:n}\s*(\+\+|--|[-+*/]?=[^=])"],
  fp=["func scan(p string) {\n\tfor i := 0; i < len(p); i++ {\n\t\tif p[i] == '\\\\' {\n\t\t\ti++\n\t\t}\n\t\tuse(p[i])\n\t}\n}\n",
      "func grow(s []int) {\n\tfor i := 0; i < len(s); i++ {\n\t\tif s[i] > 0 {\n\t\t\ts = append(s, 0)\n\t\t}\n\t}\n}\n",
      "func skip(b []byte) {\n\tfor i := 0; i < len(b); i++ {\n\t\ti += 2\n\t}\n}\n"])
M("BLOOP", "Benchmark loop over b.N", "with the more modern `for b.Loop()`, which was added in Go 1.24",
  '[(for_statement (for_clause condition: (binary_expression right: (selector_expression field: (field_identifier) @n (#eq? @n "N"))))) (for_statement (range_clause right: (selector_expression field: (field_identifier) @n (#eq? @n "N"))))] @match',
  "func BenchmarkX(b *testing.B) {\n\tfor i := 0; i < b.N; i++ {\n\t\twork()\n\t}\n}\n", "func BenchmarkX(b *testing.B) {\n\tfor b.Loop() {\n\t\twork()\n\t}\n}\n",
  "Use `for b.Loop()` (Go 1.24): no manual timer resets, and the compiler cannot optimise the body away.", "1.24", files=["**/*_test.go"])
M("MINMAX", "if/else that is min or max", "suggesting the use of the built-in `min` and `max` functions, introduced in Go 1.21",
  '(if_statement condition: (binary_expression left: (_) @a operator: ["<" ">" "<=" ">="] right: (_) @b) consequence: (block (statement_list . (assignment_statement right: (expression_list . (_) @c .)) .)) alternative: (block (statement_list . (assignment_statement right: (expression_list . (_) @d .)) .)) (#eq? @a @c) (#eq? @b @d)) @match',
  "func f() {\n\tif a < b {\n\t\tx = a\n\t} else {\n\t\tx = b\n\t}\n}\n", "func f() {\n\tx = min(a, b)\n}\n", "Use min/max (Go 1.21); not for floats with NaN.", "1.21")
M("SLICESCONTAINS", "Loop that is slices.Contains", "It replaces them with calls to `slices.Contains` or `slices.ContainsFunc`",
  '(for_statement (range_clause left: (expression_list (identifier) @u (#eq? @u "_") (identifier) @v)) body: (block (statement_list . (if_statement !initializer condition: [(binary_expression left: (identifier) @l operator: "==") (binary_expression operator: "==" right: (identifier) @l)] consequence: (block (statement_list . (return_statement (expression_list . (true) .)) .))) .)) (#eq? @l @v)) @match',
  "func has(s []string, x string) bool {\n\tfor _, v := range s {\n\t\tif v == x {\n\t\t\treturn true\n\t\t}\n\t}\n\treturn false\n}\n",
  "func has(s []string, x string) bool {\n\treturn slices.Contains(s, x)\n}\n", "Use slices.Contains (Go 1.21).", "1.21")
M("SLICESSORT", "sort.Slice with a plain < comparison", "sort.Slice(s, func(i, j int) bool { return s[i] < s[j] })",
  '(call_expression function: ' + sel("sort", "Slice") + ' arguments: (argument_list (identifier) (func_literal body: (block (statement_list (return_statement (expression_list (binary_expression left: (index_expression) operator: "<" right: (index_expression))))))))) @match',
  "func f() {\n\tsort.Slice(s, func(i, j int) bool { return s[i] < s[j] })\n}\n", "func f() {\n\tslices.Sort(s)\n}\n", "Use slices.Sort (Go 1.21).", "1.21")
P("MOD-SORTSLICE-FUNC", "sort.Slice with a custom comparator", PKG + "sort#Slice", "the newer slices.SortFunc function is more ergonomic and runs faster",
  call("sort", "Slice|SliceStable", "(_) (func_literal)"), "func f() {\n\tsort.Slice(users, func(i, j int) bool { return users[i].Age < users[j].Age })\n}\n",
  "func f() {\n\tslices.SortFunc(users, func(a, b User) int { return cmp.Compare(a.Age, b.Age) })\n}\n",
  "slices.SortFunc/SortStableFunc (Go 1.21) are type-safe and faster than reflection-based sort.Slice.",
  sev="info", kind="modernization", cat="modernization", applies={"go": ">=1.21"}, filters=[r"node.lacks_re:return \w+\[\w+\] < \w+\[\w+\] \}"])
M("MAPSLOOP", "Map copy loop", "with a single call to a function from the `maps` package, added in Go 1.23",
  '(for_statement (range_clause left: (expression_list (identifier) @k (identifier) @v)) body: (block (statement_list . (assignment_statement left: (expression_list (index_expression index: (identifier) @k2)) right: (expression_list (identifier) @v2)) .)) (#eq? @k @k2) (#eq? @v @v2)) @match',
  "func f() {\n\tfor k, v := range src {\n\t\tdst[k] = v\n\t}\n}\n", "func f() {\n\tmaps.Copy(dst, src)\n}\n", "Use maps.Copy / maps.Clone / maps.Collect.", "1.23")
M("STRINGSCUTPREFIX", "HasPrefix + TrimPrefix", "It replaces this two-step process with a single call to `strings.CutPrefix`, introduced in Go 1.20.",
  '(if_statement !initializer condition: (call_expression function: (selector_expression operand: (identifier) @p (#match? @p "^(strings|bytes)$") field: (field_identifier) @f (#match? @f "^Has(Prefix|Suffix)$")) arguments: (argument_list) @args) consequence: (block) @b) @match',
  "func f() {\n\tif strings.HasPrefix(s, p) {\n\t\tuse(strings.TrimPrefix(s, p))\n\t}\n}\n",
  "func f() {\n\tif after, ok := strings.CutPrefix(s, p); ok {\n\t\tuse(after)\n\t}\n}\n", "Use strings.CutPrefix/CutSuffix (Go 1.20).", "1.20",
  filters=[r"cap.has_re:b:\b(strings|bytes)\.Trim(Prefix|Suffix){cap:args}"],
  fp=['func f(p *parser, q byte) {\n\tif strings.HasPrefix(p.rest(), strings.Repeat(string(q), 3)) {\n\t\tp.i += 3\n\t\tv := strings.TrimPrefix(p.s[p.i:], "\\n")\n\t\tuse(v)\n\t}\n}\n'])
M("STRINGSSEQ", "Ranging over strings.Split / Fields", "which was added in Go 1.24 and avoids allocating a slice for the substrings",
  '(for_statement (range_clause left: (expression_list (identifier) @u (#eq? @u "_") (identifier)) right: (call_expression function: (selector_expression operand: (identifier) @p (#match? @p "^(strings|bytes)$") field: (field_identifier) @f (#match? @f "^(Split|Fields)$")))) @match)',
  "func f() {\n\tfor _, part := range strings.Split(s, \",\") {\n\t\tuse(part)\n\t}\n}\n", "func f() {\n\tfor part := range strings.SplitSeq(s, \",\") {\n\t\tuse(part)\n\t}\n}\n",
  "Use strings.SplitSeq/FieldsSeq (Go 1.24) to avoid allocating the slice.", "1.24")
M("STRINGSBUILDER", "String concatenation in a loop", "replace += with strings.Builder",
  '(for_statement body: (block (statement_list (assignment_statement operator: "+=" right: (expression_list [(interpreted_string_literal) (call_expression function: (selector_expression operand: (identifier) @x (#eq? @x "fmt")))])) @match)))',
  "func f() string {\n\tfor _, v := range s {\n\t\tout += fmt.Sprint(v)\n\t}\n\treturn out\n}\n",
  "func f() string {\n\tvar b strings.Builder\n\tfor _, v := range s {\n\t\tfmt.Fprint(&b, v)\n\t}\n\treturn b.String()\n}\n",
  "Repeated += on strings is quadratic; use strings.Builder.", "1.10", sev="minor")
M("FMTAPPENDF", "[]byte(fmt.Sprintf(...))", "The fmtappendf analyzer suggests replacing `[]byte(fmt.Sprintf(...))` with `fmt.Appendf(nil, ...)`.",
  '(type_conversion_expression type: (slice_type) operand: (call_expression function: ' + sel("fmt", "Sprintf|Sprint|Sprintln") + ')) @match',
  'var b = []byte(fmt.Sprintf("%d", n))\n', 'var b = fmt.Appendf(nil, "%d", n)\n', "fmt.Appendf avoids the intermediate string.", "1.19")
M("TESTINGCONTEXT", "context.WithCancel + defer cancel in a test", "it replaces the manual creation of a cancellable context",
  '(statement_list (short_var_declaration left: (expression_list . (identifier) . (identifier) @c .) right: (expression_list . (call_expression function: ' + sel("context", "WithCancel")
  + ' arguments: (argument_list . (call_expression function: (selector_expression operand: (identifier) @p2 (#eq? @p2 "context") field: (field_identifier) @f2 (#match? @f2 "^(Background|TODO)$"))) .)) .)) @match . (defer_statement (call_expression function: (identifier) @d arguments: (argument_list) .)) (#eq? @c @d))',
  "func TestX(t *testing.T) {\n\tctx, cancel := context.WithCancel(context.Background())\n\tdefer cancel()\n\trun(ctx)\n}\n",
  "func TestX(t *testing.T) {\n\tctx := t.Context()\n\trun(ctx)\n}\n", "Use t.Context() (Go 1.24): cancelled when the test ends.", "1.24", files=["**/*_test.go"],
  # only in a function that has a *testing.T/B/F, and only when cancel is used for nothing but the defer
  filters=[r"ancestor.has_re:function_declaration|method_declaration|func_literal:^[^{]*\*testing\.[TBF]\b", r"func.count_lt:3:(^|[^\w.]){cap:c}\b"],
  fp=["func TestX(t *testing.T) {\n\tctx := context.Background()\n\trun(ctx)\n}\n",
      "func TestMain(m *testing.M) {\n\tctx, cancel := context.WithCancel(context.Background())\n\tdefer cancel()\n\trun(ctx)\n}\n",
      "func TestX(t *testing.T) {\n\tctx, cancel := context.WithCancel(context.Background())\n\tdefer cancel()\n\tgo stop(cancel)\n\trun(ctx)\n}\n"])
M("PLUSBUILD", "Obsolete // +build line next to //go:build", "The plusbuild analyzer suggests a fix to remove obsolete build tags of the form",
  '((comment) @match (#match? @match "^// ?[+]build "))', "//go:build linux\n// +build linux\n\npackage x\n", "//go:build linux\n\npackage x\n",
  "Delete the // +build line.", "1.18", filters=["file.has_re://go:build"])
M("IMPORTCOMMENT", "Obsolete import comment on package clause", "The importcomment analyzer removes comments specifying the canonical import path",
  '((package_clause) . (comment) @match (#match? @match "^// import \\""))', 'package foo // import "example.com/foo"\n', "package foo\n",
  "Module mode ignores import comments.", "1.11")
M("OMITZERO", "omitempty on a time.Time field", "For struct-typed fields, the `omitempty` tag has no effect on the behavior of json.Marshal and json.Unmarshal.",
  '(field_declaration type: (qualified_type) @t (#eq? @t "time.Time") tag: (raw_string_literal) @match (#match? @match "omitempty"))',
  "type T struct {\n\tAt time.Time `json:\"at,omitempty\"`\n}\n", "type T struct {\n\tAt time.Time `json:\"at,omitzero\"`\n}\n",
  "omitempty never omits struct values; use omitzero (Go 1.24) — note this changes output.", "1.24", sev="minor")
M("SLICESCLIP", "s[:len(s):len(s)]", "with the simpler and more readable slices.Clip(x) added in Go 1.21",
  '((slice_expression operand: (identifier) @s end: (call_expression arguments: (argument_list (identifier) @a)) capacity: (call_expression arguments: (argument_list (identifier) @b))) @match (#eq? @s @a) (#eq? @s @b))',
  "var c = s[:len(s):len(s)]\n", "var c = slices.Clip(s)\n", "Use slices.Clip.", "1.21")
M("SLICESBACKWARD", "Manual backward loop over a slice", "with the more readable Go 1.23 style using slices.Backward",
  '(for_statement (for_clause initializer: (short_var_declaration right: (expression_list (binary_expression left: (call_expression function: (identifier) @l (#eq? @l "len")) operator: "-" right: (int_literal) @one (#eq? @one "1")))) update: (dec_statement))) @match',
  "func f() {\n\tfor i := len(s) - 1; i >= 0; i-- {\n\t\tuse(s[i])\n\t}\n}\n", "func f() {\n\tfor _, v := range slices.Backward(s) {\n\t\tuse(v)\n\t}\n}\n",
  "Use slices.Backward (Go 1.23).", "1.23")
M("ATOMICTYPES", "sync/atomic functions on plain integers", "with the strongly typed atomic wrapper types introduced in Go1.19",
  call("atomic", "(Add|Load|Store|Swap|CompareAndSwap)(Int32|Int64|Uint32|Uint64|Uintptr|Pointer)"), "func f() {\n\tatomic.AddInt64(&n, 1)\n}\n",
  "func f() {\n\tn.Add(1)\n}\n", "atomic.Int64 etc. prevent non-atomic access and fix 32-bit alignment.", "1.19",
  # changing the type of an exported field/var breaks the API; a pointer conversion means the storage is another type
  filters=[r"node.lacks_re:\(\s*\(\*|&(\w+\.)*[A-Z]\w*\s*[,)]"],
  fp=["func (l *Logger) SetLevel(v Level) {\n\tatomic.StoreUint32((*uint32)(&l.level), uint32(v))\n}\n",
      "func f(s *Stats) {\n\tatomic.AddInt64(&s.Count, 1)\n}\n"])
M("WAITGROUPGO", "wg.Add(1) + go func(){ defer wg.Done() }", "waitgroupgo",
  '(statement_list (expression_statement (call_expression function: (selector_expression field: (field_identifier) @a (#eq? @a "Add")))) . (go_statement (call_expression function: (func_literal body: (block (statement_list . (defer_statement (call_expression function: (selector_expression field: (field_identifier) @d (#eq? @d "Done"))))))))) @match)',
  "func f() {\n\twg.Add(1)\n\tgo func() {\n\t\tdefer wg.Done()\n\t\twork()\n\t}()\n}\n", "func f() {\n\twg.Go(func() {\n\t\twork()\n\t})\n}\n", "Use wg.Go (Go 1.25).", "1.25")
M("ERRORSASTYPE", "errors.As with a pre-declared target", "by using the less error-prone generic errors.AsType function, introduced in Go 1.26",
  '((call_expression function: ' + sel("errors", "As") + ' arguments: (argument_list (_) (unary_expression operand: (identifier) @t))) @match)',
  "func f(err error) {\n\tvar pe *fs.PathError\n\tif errors.As(err, &pe) {\n\t\tuse(pe)\n\t}\n}\n",
  "func f(err error) {\n\tif pe, ok := errors.AsType[*fs.PathError](err); ok {\n\t\tuse(pe)\n\t}\n}\n", "Use errors.AsType[T] (Go 1.26).", "1.26",
  # the fix needs `var t T` in this function and the call as the if condition (not negated, not assigned)
  filters=[r"parentkind.has_re:if_statement:.", r"func.has_re:\bvar\s+{cap:t}\s+[^=\n]+\n"],
  fp=["func f(err error) bool {\n\treturn errors.As(err, &MyErr{})\n}\n",
      "func f(err error) {\n\tvar pe *fs.PathError\n\tif !errors.As(err, &pe) {\n\t\treturn\n\t}\n\tuse(pe)\n}\n",
      "func f(err error, pe **fs.PathError) {\n\tif errors.As(err, pe) {\n\t}\n}\n"])
M("REFLECTTYPEFOR", "reflect.TypeOf((*T)(nil)).Elem()", "This analyzer suggests fixes to replace uses of reflect.TypeOf(x) with reflect.TypeFor, introduced in go1.22",
  call("reflect", "TypeOf", "(call_expression arguments: (argument_list (nil)))"), "var t = reflect.TypeOf((*io.Reader)(nil)).Elem()\n", "var t = reflect.TypeFor[io.Reader]()\n",
  "Use reflect.TypeFor[T]() (Go 1.22).", "1.22")
M("NEWEXPR", "Helper returning &param (use new(expr))", "simplify code by using go1.26's new(expr)",
  '(function_declaration parameters: (parameter_list . (parameter_declaration name: (identifier) @x) .) result: (pointer_type) body: (block (statement_list . (return_statement (expression_list (unary_expression operand: (identifier) @y))) .)) (#eq? @x @y)) @match',
  "func intPtr(x int) *int { return &x }\n", "var p = new(42)\n", "Go 1.26 new(expr) replaces pointer-helper functions.", "1.26")
# ---------------------------------------------------------------- security
P("TLS-INSECURE-SKIP-VERIFY", "TLS certificate verification disabled", PKG + "crypto/tls#Config", "In this mode, TLS is susceptible to machine-in-the-middle // attacks unless custom verification is used.",
  '(keyed_element key: (literal_element (identifier) @k (#eq? @k "InsecureSkipVerify")) value: (literal_element (true))) @match',
  "var c = &tls.Config{InsecureSkipVerify: true}\n", "var c = &tls.Config{MinVersion: tls.VersionTLS12}\n",
  "Accepts any certificate: trivially MITM-able.", sev="critical", kind="security", cat="security", xref=["gosec:G402"],
  files=["!**/*_test.go"])  # tests against self-signed httptest/TLS servers skip verification by design
P("TLS-OLD-VERSION", "TLS minimum version below 1.2", PKG + "crypto/tls#Config", "MinVersion contains the minimum TLS version that is acceptable.",
  '(keyed_element key: (literal_element (identifier) @k (#eq? @k "MinVersion")) value: (literal_element (selector_expression field: (field_identifier) @match (#match? @match "^(VersionTLS10|VersionTLS11|VersionSSL30)$"))))',
  "var c = &tls.Config{MinVersion: tls.VersionTLS10}\n", "var c = &tls.Config{MinVersion: tls.VersionTLS12}\n", "TLS 1.0/1.1 are deprecated (RFC 8996).",
  sev="major", kind="security", cat="security")
for alg, path, needle in [("MD5", "crypto/md5", "MD5 is cryptographically broken and should not be used for secure applications."),
                          ("SHA1", "crypto/sha1", "SHA-1 is cryptographically broken and should not be used for secure applications."),
                          ("RC4", "crypto/rc4", "RC4 is cryptographically broken and should not be used for secure applications."),
                          ("DES", "crypto/des", "Triple Data Encryption Algorithm")]:
    P("WEAK-CRYPTO-" + alg, f"{path} imported", PKG + path, needle,
      f'(import_spec path: (interpreted_string_literal) @match (#eq? @match "\\"{path}\\""))', f'import "{path}"\n', 'import "crypto/sha256"\n',
      f"{alg} is broken for security purposes; use it only for non-security checksums.", sev="major", kind="security", cat="security",
      mode="ai-confirm", ai=f"Is {alg} used here for a security purpose (passwords, signatures, tokens, integrity against attackers) rather than a non-security checksum/compat protocol?")
P("DSA", "crypto/dsa (deprecated legacy algorithm)", PKG + "crypto/dsa", "DSA is a legacy algorithm",
  '(import_spec path: (interpreted_string_literal) @match (#eq? @match "\\"crypto/dsa\\""))', 'import "crypto/dsa"\n', 'import "crypto/ed25519"\n',
  "Use Ed25519, ECDSA or RSA.", sev="major", kind="deprecation", cat="security",
  applies={"go": ">=1.16"})
P("MATH-RAND-SECURITY", "math/rand used where crypto/rand may be needed", PKG + "math/rand", "For random numbers suitable for security-sensitive work, see the crypto/rand package.",
  '(call_expression function: (selector_expression operand: (identifier) @p (#eq? @p "rand") field: (field_identifier) @f (#match? @f "^(Int|Intn|Int63|Int31|Uint32|Uint64|Read|IntN|N|Text)$"))) @match',
  'import "math/rand"\n\nfunc token() int {\n\treturn rand.Int()\n}\n', 'import "crypto/rand"\n\nfunc token() string {\n\treturn rand.Text()\n}\n',
  "math/rand output is predictable; use crypto/rand for tokens, keys, nonces and passwords.", sev="major", kind="security", cat="security",
  mode="ai-confirm", ai="Is the random value used for something security-sensitive (token, password, key, nonce, session id)?",
  filters=[r'file.has_re:"math/rand(/v2)?"'])
P("EXEC-SHELL", "Shell invoked with a dynamic command", PKG + "os/exec", "the os/exec package intentionally does not invoke the system shell",
  '(call_expression function: ' + sel("exec", "Command|CommandContext") + ' arguments: (argument_list . (_)? (interpreted_string_literal) @sh (#match? @sh "^\\"(/bin/)?(sh|bash|zsh|cmd|cmd.exe|powershell)\\"$") (interpreted_string_literal) @c (#match? @c "^\\"(-c|/c|-Command)\\"$") [(identifier) (binary_expression) (call_expression)])) @match',
  'func f(name string) {\n\texec.Command("sh", "-c", "ls "+name)\n}\n', 'func f(name string) {\n\texec.Command("ls", "--", name)\n}\n',
  "Passing a constructed string to a shell enables command injection; call the program directly with separate args.",
  sev="critical", kind="security", cat="security")
P("SQL-STRING-BUILD", "SQL built by string concatenation / Sprintf", "https://go.dev/doc/database/sql-injection", "by providing SQL parameter values as sql package function arguments",
  '(call_expression function: (selector_expression field: (field_identifier) @f (#match? @f "^(Query|QueryRow|Exec|QueryContext|QueryRowContext|ExecContext|Prepare|PrepareContext)$")) arguments: (argument_list . (binary_expression operator: "+") @match))\n(call_expression function: (selector_expression field: (field_identifier) @f (#match? @f "^(Query|QueryRow|Exec|QueryContext|QueryRowContext|ExecContext|Prepare|PrepareContext)$")) arguments: (argument_list . (call_expression function: (selector_expression operand: (identifier) @x field: (field_identifier) @s)) @match (#eq? @x "fmt") (#eq? @s "Sprintf")))\n(call_expression function: (selector_expression field: (field_identifier) @f (#match? @f "^(Query|QueryRow|Exec|QueryContext|QueryRowContext|ExecContext|Prepare|PrepareContext)$")) arguments: (argument_list . (_) @ctx . (binary_expression operator: "+") @match))\n(call_expression function: (selector_expression field: (field_identifier) @f (#match? @f "^(Query|QueryRow|Exec|QueryContext|QueryRowContext|ExecContext|Prepare|PrepareContext)$")) arguments: (argument_list . (_) @ctx . (call_expression function: (selector_expression operand: (identifier) @x field: (field_identifier) @s)) @match (#eq? @x "fmt") (#eq? @s "Sprintf")))',
  'func f(id string) {\n\tdb.Query("SELECT * FROM users WHERE id = " + id)\n}\n', 'func f(id string) {\n\tdb.Query("SELECT * FROM users WHERE id = ?", id)\n}\n',
  "Use placeholders and pass values as arguments.", sev="critical", kind="security", cat="security", docv="go.dev/doc/database (2026)",
  xref=["gosec:G201", "gosec:G202"],
  # the built string must be the query argument (first, or second after a ctx) and look like SQL
  filters=[r"cap.lacks_re:ctx:^[\"`]", r"node.has_re:(?i)\b(select|insert|update|delete|create|drop|alter|truncate|where|from|into)\b"],
  fp=['func f(i int) {\n\tdb.Exec("INSERT INTO blog (title) VALUES ($1);", fmt.Sprintf("post #%d", i))\n}\n',
      'func f(addr string) {\n\tNew().Query("http://"+addr, cfg)\n}\n'])
P("TEXT-TEMPLATE-HTML", "text/template used to render HTML", PKG + "html/template", "safe against code injection",
  '(import_spec path: (interpreted_string_literal) @match (#eq? @match "\\"text/template\\""))', 'import "text/template"\n\nconst page = "<html><body>{{.Name}}</body></html>"\n',
  'import "html/template"\n\nconst page = "<html><body>{{.Name}}</body></html>"\n', "text/template does no contextual escaping; use html/template for HTML.",
  sev="major", kind="security", cat="security", filters=[r"file.has_re:(?i)<(html|body|div|span|script|a |p>|td|li)|http\.ResponseWriter"])
P("HTTP-DEFAULT-CLIENT", "http.Get/Post with the default client (no timeout)", PKG + "net/http#Client", "A Timeout of zero means no timeout.",
  call("http", "Get|Post|PostForm|Head"), "func f() {\n\thttp.Get(u)\n}\n", "var client = &http.Client{Timeout: 10 * time.Second}\n\nfunc f() {\n\tclient.Get(u)\n}\n",
  "http.DefaultClient has no timeout: a slow server can hang the caller forever.", sev="minor", kind="best-practice", cat="reliability",
  filters=[r"file.lacks_re:\bhttptest\.New(TLS|Unstarted)?Server\("],
  fp=['func TestAPI(t *testing.T) {\n\tsrv := httptest.NewServer(h)\n\tdefer srv.Close()\n\tres, err := http.Get(srv.URL + "/")\n\t_, _ = res, err\n}\n'])
P("HTTP-LISTEN-NO-TIMEOUTS", "http.ListenAndServe without server timeouts", PKG + "net/http#Server", "A zero or negative value means there will be no timeout.",
  call("http", "ListenAndServe|ListenAndServeTLS"), 'func main() {\n\thttp.ListenAndServe(":8080", mux)\n}\n',
  'func main() {\n\tsrv := &http.Server{Addr: ":8080", Handler: mux, ReadHeaderTimeout: 5 * time.Second}\n\tsrv.ListenAndServe()\n}\n',
  "The package-level helpers use a Server with no timeouts (slowloris exposure); configure ReadHeaderTimeout etc.", sev="minor", kind="security", cat="security")
P("PATH-TRAVERSAL-ROOT", "filepath.Join with request data (use os.Root)", PKG + "os#Root", "Root may be used to only access files within a single directory tree.",
  '(call_expression function: (selector_expression operand: (identifier) @p (#match? @p "^(os|ioutil)$") field: (field_identifier) @f (#match? @f "^(Open|OpenFile|ReadFile|Create|WriteFile|Remove|RemoveAll)$")) arguments: (argument_list (call_expression function: (selector_expression operand: (identifier) @fp (#eq? @fp "filepath") field: (field_identifier) @j (#eq? @j "Join")) arguments: (argument_list (_) [(call_expression) (selector_expression) (index_expression)])))) @match',
  'func h(w http.ResponseWriter, r *http.Request) {\n\tos.ReadFile(filepath.Join(base, r.URL.Query().Get("f")))\n}\n',
  'func h(w http.ResponseWriter, r *http.Request) {\n\troot, _ := os.OpenRoot(base)\n\troot.ReadFile(r.URL.Query().Get("f"))\n}\n',
  "Joining untrusted path segments allows ../ traversal; use os.OpenRoot/os.Root (Go 1.24) or filepath.IsLocal.", sev="major", kind="security",
  cat="security", applies={"go": ">=1.24"}, mode="ai-confirm", ai="Does the joined path segment come from untrusted input (request, user, archive entry)?")
P("UNSAFE-IMPORT", "Package unsafe imported", PKG + "unsafe", "Package unsafe contains operations that step around the type safety of Go programs.",
  '(import_spec path: (interpreted_string_literal) @match (#eq? @match "\\"unsafe\\""))', 'import "unsafe"\n', 'import "strings"\n',
  "unsafe code is not covered by the Go 1 compatibility promise; review carefully.", sev="info", kind="security", cat="security",
  filters=[r'file.lacks_re:(?m)^import "C"|^\s*"C"\s*$'],
  fp=['package vue\n\n// #include "tree_sitter/parser.h"\nimport "C"\n\nimport "unsafe"\n\nfunc Language() unsafe.Pointer { return unsafe.Pointer(C.tree_sitter_vue()) }\n'])
# ---------------------------------------------------------------- errors & idioms
P("ERR-COMPARE-EQ", "Error compared with == instead of errors.Is", PKG + "errors#Is", "Is reports whether any error in err's tree matches target.",
  '(binary_expression left: (identifier) @e (#match? @e "(?i)^err") operator: ["==" "!="] right: (selector_expression field: (field_identifier) @match (#match? @match "^(Err[A-Z]|EOF$)")))',
  "func f() bool {\n\treturn err == fs.ErrNotExist\n}\n", "func f() bool {\n\treturn errors.Is(err, fs.ErrNotExist)\n}\n",
  "== fails on wrapped errors; use errors.Is.", sev="minor", cat="errors", xref=["errorlint:comparison"],
  # sentinels the stdlib documents as returned unwrapped (io.Reader must return EOF itself; ListenAndServe
  # returns ErrServerClosed; Scan returns ErrNoRows; ctx.Err returns Canceled/DeadlineExceeded) - errorlint allowlists these
  filters=[r"parent.lacks_re:^(io\.(EOF|ErrUnexpectedEOF)|http\.Err\w+|sql\.(ErrNoRows|ErrTxDone|ErrConnDone)|context\.(Canceled|DeadlineExceeded))$"],
  fp=["func f(r io.Reader) {\n\tif _, err := r.Read(b); err == io.EOF {\n\t}\n}\n",
      "func f() {\n\tif err := srv.ListenAndServe(); err != http.ErrServerClosed {\n\t}\n}\n"])
P("ERRORF-NO-WRAP", "fmt.Errorf formats an error without %w", PKG + "fmt#Errorf", "If the format specifier includes a %w verb with an error operand",
  call("fmt", "Errorf", '(interpreted_string_literal) @fmt (#not-match? @fmt "%w") (#match? @fmt "%[vs]") . (_)* (identifier) @e (#match? @e "^err$")', cap="@match"),
  'func f() error {\n\treturn fmt.Errorf("load: %v", err)\n}\n', 'func f() error {\n\treturn fmt.Errorf("load: %w", err)\n}\n',
  "%v flattens the cause; %w keeps it inspectable with errors.Is/As (unless hiding it is intended).", sev="minor", cat="errors",
  mode="ai-confirm", ai="Should callers be able to inspect the wrapped error here (i.e. is hiding the cause not an intentional API decision)?")
P("DEFER-IN-LOOP", "defer inside a loop", "https://go.dev/doc/effective_go#defer", "The arguments to the deferred function (which include the receiver if the function is a method) are evaluated when the defer executes",
  '(for_statement body: (block (statement_list (defer_statement) @match)))', "func f() {\n\tfor _, p := range paths {\n\t\tf, _ := os.Open(p)\n\t\tdefer f.Close()\n\t}\n}\n",
  "func f() {\n\tfor _, p := range paths {\n\t\tfunc() {\n\t\t\tf, _ := os.Open(p)\n\t\t\tdefer f.Close()\n\t\t}()\n\t}\n}\n",
  "Deferred calls run when the function returns, not per iteration: resources pile up.", sev="minor", cat="resource", docv="Effective Go")
P("PANIC-IN-INIT-ERR", "Error ignored with blank identifier from os/io calls", "https://go.dev/doc/effective_go#errors", "Library routines must often return some sort of error indication to the caller.",
  # json.Marshal* of plain data and http.NewRequest with a constant method only fail for programmer errors;
  # strconv on a regexp digit group cannot fail; tests may ignore setup errors.
  '(short_var_declaration left: (expression_list (identifier) (identifier) @match (#eq? @match "_")) right: (expression_list (call_expression function: (selector_expression operand: (identifier) @p (#match? @p "^(os|io|json|strconv|http|sql|db)$") field: (field_identifier) @f (#not-match? @f "^(Marshal|MarshalIndent|NewRequest|NewRequestWithContext)$")) arguments: (argument_list) @args)))',
  "func f() {\n\tb, _ := os.ReadFile(p)\n\tuse(b)\n}\n", "func f() error {\n\tb, err := os.ReadFile(p)\n\tif err != nil {\n\t\treturn err\n\t}\n\tuse(b)\n\treturn nil\n}\n",
  "The error is discarded; failures will surface later as confusing zero values.", sev="minor", cat="errors", docv="Effective Go",
  mode="ai-confirm", ai="Is discarding this error unsafe here (the call can realistically fail and the zero value would be used)?",
  files=["!**/*_test.go"], filters=[r"cap.lacks_re:args:^\(\w+\[\d+\]\)$"],
  fp=["func jsonString(v any) string { b, _ := json.Marshal(v); return string(b) }\n",
      'func f(url string) {\n\treq, _ := http.NewRequest("GET", url, nil)\n\tuse(req)\n}\n',
      "func f(m []string) int {\n\tstart, _ := strconv.Atoi(m[1])\n\treturn start\n}\n",
      {"code": "func TestX(t *testing.T) {\n\tf, _ := os.Create(filepath.Join(t.TempDir(), \"r.json\"))\n\tuse(f)\n}\n", "path": "pkg/x_test.go", "note": "test setup"}])

# ---------------------------------------------------------------- additional vet analyzers / stdlib API guidance (2026.10 expansion)
CRC = "https://go.dev/wiki/CodeReviewComments"
P("VET-PRINTF-NONCONST", "Non-constant format string", v("printf"), "non-constant format string in call",
  '(call_expression function: ' + sel("fmt", "Printf|Sprintf|Errorf|Fprintf") + ' arguments: (argument_list . (identifier) .)) @match' + "\n"
  + '(call_expression function: ' + sel("fmt", "Fprintf") + ' arguments: (argument_list . (_) . (identifier) .)) @match',
  "func f(msg string) {\n\tfmt.Printf(msg)\n}\n", "func f(msg string) {\n\tfmt.Print(msg)\n}\n",
  "A % in the data is interpreted as a verb; use Print or Printf(\"%s\", msg).", sev="minor", cat="correctness", doc="go vet printf",
  applies={"go": ">=1.24"}, docv="Go 1.24 vet")
P("VET-COMPOSITES", "Unkeyed fields in an imported struct literal", v("composite"), "defines an Analyzer that checks for unkeyed",
  '(composite_literal type: (qualified_type) body: (literal_value . (literal_element))) @match',
  'var s = http.Server{":8080", h}\n', 'var s = http.Server{Addr: ":8080", Handler: h}\n',
  "Positional fields break when the other package adds or reorders fields.", sev="minor", cat="maintainability", doc="go vet composites")
UNREACH = '[(expression_statement) (short_var_declaration) (assignment_statement) (if_statement) (for_statement) (return_statement) (var_declaration) (go_statement) (defer_statement) (inc_statement) (dec_statement) (send_statement) (expression_switch_statement) (type_switch_statement) (select_statement) (block)]'
P("VET-UNREACHABLE", "Unreachable code after return/panic", v("unreachable"), "check for unreachable code",
  '(block (statement_list (return_statement) . (comment)* . ' + UNREACH + ' @match))' + "\n"
  + '((block (statement_list (expression_statement (call_expression function: (identifier) @p)) . (comment)* . ' + UNREACH + ' @match)) (#eq? @p "panic"))',
  "func f() int {\n\treturn 1\n\tlog.Println(\"never\")\n}\n", "func f() int {\n\tlog.Println(\"now\")\n\treturn 1\n}\n",
  "Statements after an unconditional return never run.", sev="minor", cat="correctness", doc="go vet unreachable",
  fp=[{"code": "func f(x bool) int {\n\tif x {\n\t\treturn 2 // early\n\t}\n\treturn 1 // trailing comment is not code\n}\n",
       "note": "self-scan: a trailing comment after return is a sibling node, not a statement"},
      {"code": "func g() {\n\tpanic(\"boom\") // explain\n}\n", "note": "comment after panic"},
      {"code": "func h() {\n\tvar panic = func(int) {}\n\tpanic(2)\n\tprintln(\"still runs\")\n}\n",
       "note": "fixture triage (go vet unreachable): a local variable named panic is not the builtin"}],
  filters=[r"func.lacks_re:\bpanic\s*(:=|=[^=])"])
P("CTX-WITHVALUE-STRING-KEY", "context.WithValue with a built-in key type", PKG + "context#WithValue",
  "should not be of type string or any other built-in type to avoid collisions between packages using context",
  call("context", "WithValue", ". (_) . [(interpreted_string_literal) (raw_string_literal) (int_literal)]"),
  'func f(ctx context.Context) context.Context {\n\treturn context.WithValue(ctx, "user", u)\n}\n',
  "type userKey struct{}\n\nfunc f(ctx context.Context) context.Context {\n\treturn context.WithValue(ctx, userKey{}, u)\n}\n",
  "Use an unexported key type to avoid collisions.", sev="minor", cat="correctness", xref=["staticcheck:SA1029", "revive:context-keys-type"],
  fp=['type k struct{ n string }\n\nfunc f(ctx context.Context) context.Context {\n\treturn context.WithValue(ctx, k{"id"}, "1")\n}\n'])
P("CTX-IN-STRUCT", "context.Context stored in a struct", PKG + "context", "Do not store Contexts inside a struct type",
  '(field_declaration name: (field_identifier) type: (qualified_type package: (package_identifier) @p name: (type_identifier) @t) (#eq? @p "context") (#eq? @t "Context")) @match',
  "type Worker struct {\n\tctx context.Context\n}\n", "type Worker struct{}\n\nfunc (w *Worker) Run(ctx context.Context) {}\n",
  "Pass the Context explicitly to each function that needs it.", sev="minor", cat="maintainability",
  quote="Do not store Contexts inside a struct type; instead, pass a Context explicitly to each function that needs it.",
  xref=["containedctx:containedctx"],
  # an embedded Context makes the type itself a Context (wrapper), which the guidance does not cover
  fp=["type valueCtx struct {\n\tcontext.Context\n\tv any\n}\n"])
P("CTX-NOT-FIRST", "context.Context is not the first parameter", PKG + "context", "The Context should be the first parameter, typically named ctx",
  '(parameter_list (parameter_declaration) (parameter_declaration type: (qualified_type package: (package_identifier) @p name: (type_identifier) @t) (#eq? @p "context") (#eq? @t "Context")) @match)',
  "func Get(id string, ctx context.Context) error { return nil }\n", "func Get(ctx context.Context, id string) error { return nil }\n",
  "Convention: ctx first.", sev="info", cat="style")
P("CTX-NIL", "nil passed as a Context", PKG + "context", "Do not pass a nil Context, even if a function permits it.",
  '((call_expression function: (selector_expression field: (field_identifier) @f) arguments: (argument_list . (nil))) @match (#match? @f "(Context|Ctx)$"))',
  'func f() {\n\treq, _ := http.NewRequestWithContext(nil, "GET", u, nil)\n\t_ = req\n}\n',
  'func f(ctx context.Context) {\n\treq, _ := http.NewRequestWithContext(ctx, "GET", u, nil)\n\t_ = req\n}\n', "Pass context.TODO() if unsure.", sev="major", cat="correctness")
P("HTTP-BODY-NOT-CLOSED", "HTTP response body never closed", PKG + "net/http", "The caller must close the response body when finished with it",
  '((function_declaration body: (block) @b) @match (#match? @b "\\\\b(\\\\w+)\\\\s*,\\\\s*\\\\w+\\\\s*:?=\\\\s*(http\\\\.(Get|Post|Head|PostForm)|\\\\w*([Cc]lient|http\\\\.DefaultClient)\\\\.(Get|Post|Head|PostForm|Do))\\\\(") (#not-match? @b "Body\\\\.Close\\\\(\\\\)"))',
  "func f() error {\n\tresp, err := http.Get(u)\n\tif err != nil {\n\t\treturn err\n\t}\n\t_ = resp\n\treturn nil\n}\n",
  "func f() error {\n\tresp, err := http.Get(u)\n\tif err != nil {\n\t\treturn err\n\t}\n\tdefer resp.Body.Close()\n\treturn nil\n}\n",
  "Unclosed bodies leak connections and file descriptors.", sev="major", cat="resources", mode="ai-confirm",
  ai="Is the response returned/handed off to a caller that closes it? If not, this is a leak.",
  # handed off: returned to the caller, or passed to a close/drain helper
  filters=[r"node.lacks_re:^func[^{]*\*http\.Response|\breturn\s+&?\w*[Rr]es(p|ponse)?\w*\s*(,|\n|$)|\b\w*([Cc]lose|[Dd]rain|[Dd]iscard)\w*\(\s*\w*[Rr]es(p|ponse)?\w*\s*[,)]"],
  fp=["func Fetch(u string) (*http.Response, error) {\n\tresp, err := http.Get(u)\n\tif err != nil {\n\t\treturn nil, err\n\t}\n\treturn resp, nil\n}\n",
      "func f(u string) error {\n\tresp, err := http.Get(u)\n\tif err != nil {\n\t\treturn err\n\t}\n\tdefer closeBody(resp)\n\treturn nil\n}\n",
      {"code": "import \"net/http\"\n\nfunc FromCache(items []string, c Cache) int {\n\tn := 0\n\tfor _, it := range items {\n\t\tif _, ok := c.Get(it); ok {\n\t\t\tn++\n\t\t}\n\t}\n\treturn n\n}\n",
       "note": "self-scan: c.Get on a cache, not an HTTP client"}])
P("ERROR-STRING-STYLE", "Capitalized or punctuated error string", CRC, "Error strings should not be capitalized (unless beginning with proper nouns or acronyms) or end with punctuation",
  '((call_expression function: (selector_expression operand: (identifier) @p field: (field_identifier) @f) arguments: (argument_list . (interpreted_string_literal) @s)) @match (#match? @p "^(errors|fmt)$") (#match? @f "^(New|Errorf)$") (#match? @s "^\\"([A-Z][a-z]|.*[.!:]\\"$)"))',
  'var errX = errors.New("Something failed.")\n', 'var errX = errors.New("something failed")\n', "Errors are usually wrapped into longer messages.",
  sev="info", cat="style", docv="Go Code Review Comments", xref=["revive:error-strings", "staticcheck:ST1005"],
  # starts with an identifier (CamelCase type/func name, Header-Name, call) and has no trailing punctuation
  filters=[r'cap.lacks_re:s:^"([A-Z][a-z0-9]*[A-Z]\w*|[A-Z]\w*-[A-Z]\w*|[A-Z]\w*\()([^"\\]|\\.)*[^.!:"\\]"$'],
  fp=['var e = errors.New("ResponseWriter does not implement Flusher")\n', 'var e = fmt.Errorf("If-Match header did not match")\n',
      'var e = errors.New("EnsureRunning: config not active")\n'])
P("RECEIVER-NAME-THIS", "Receiver named this/self/me", CRC, "Don't use generic names such as \"me\", \"this\" or \"self\"",
  '(method_declaration receiver: (parameter_list (parameter_declaration name: (identifier) @match (#match? @match "^(this|self|me)$"))))',
  "func (this *Server) Start() {}\n", "func (s *Server) Start() {}\n", "Use a short name reflecting the type.", sev="info", cat="style",
  docv="Go Code Review Comments")
P("PACKAGE-NAME-GENERIC", "Meaningless package name", "https://go.dev/blog/package-names", "Avoid meaningless package names.",
  '(package_clause (package_identifier) @match (#match? @match "^(util|utils|common|misc|helpers|helper|base)$"))', "package util\n", "package textconv\n",
  "Name packages for what they provide.", sev="info", cat="maintainability", docv="Go blog: Package names",
  quote="Avoid meaningless package names. Packages named util, common, or misc provide clients with no sense of what the package contains.")
P("INITIALISM-CASE", "Initialism written in mixed case (Url, Id, Http)", CRC, "Words in names that are initialisms or acronyms (e.g. \"URL\" or \"NATO\") have a consistent case.",
  '([(function_declaration name: (identifier) @match) (method_declaration name: (field_identifier) @match) (type_spec name: (type_identifier) @match)] (#match? @match "^[A-Z]\\\\w*(Url|Http|Json|Api|Sql|Html|Uri|Xml|Id)([A-Z]|$)"))',
  "func ParseUrl(s string) {}\n", "func ParseURL(s string) {}\n", "Keep initialisms in consistent case (URL, ID, HTTP).", sev="info", cat="style",
  docv="Go Code Review Comments")
P("TEST-OS-SETENV", "os.Setenv in a test (use t.Setenv)", PKG + "testing#T.Setenv", "Setenv calls os.Setenv(key, value) and uses Cleanup to restore the environment variable to its original value after the test.",
  '((function_declaration name: (identifier) @n body: (block) @match) (#match? @n "^Test") (#match? @match "\\\\bos\\\\.Setenv\\\\("))',
  "func TestX(t *testing.T) {\n\tos.Setenv(\"MODE\", \"x\")\n}\n", "func TestX(t *testing.T) {\n\tt.Setenv(\"MODE\", \"x\")\n}\n",
  "os.Setenv leaks into other tests.", sev="minor", cat="testing", applies={"go": ">=1.17"}, docv="Go 1.17")
P("TEST-TEMPDIR", "os.MkdirTemp/ioutil.TempDir in a test (use t.TempDir)", PKG + "testing#T.TempDir", "TempDir returns a temporary directory for the test to use. The directory is automatically removed when the test and all its subtests complete.",
  '((function_declaration name: (identifier) @n body: (block) @match) (#match? @n "^(Test|Benchmark)") (#match? @match "\\\\b(os\\\\.MkdirTemp|ioutil\\\\.TempDir)\\\\("))',
  "func TestX(t *testing.T) {\n\tdir, _ := os.MkdirTemp(\"\", \"x\")\n\t_ = dir\n}\n", "func TestX(t *testing.T) {\n\tdir := t.TempDir()\n\t_ = dir\n}\n",
  "t.TempDir is cleaned up automatically.", sev="info", cat="testing", applies={"go": ">=1.15"}, docv="Go 1.15")
P("OS-SEEK-CONSTANTS", "os.SEEK_SET/CUR/END (deprecated)", PKG + "os#pkg-constants", "Deprecated: Use io.SeekStart, io.SeekCurrent, and io.SeekEnd.",
  '(selector_expression operand: (identifier) @p field: (field_identifier) @match (#eq? @p "os") (#match? @match "^SEEK_(SET|CUR|END)$"))',
  "func f(fh *os.File) {\n\tfh.Seek(0, os.SEEK_SET)\n}\n", "func f(fh *os.File) {\n\tfh.Seek(0, io.SeekStart)\n}\n", "Use io.Seek* constants.", sev="minor", kind="deprecation",
  cat="compatibility", applies={"go": ">=1.7"})
P("ELLIPTIC-LOW-LEVEL", "crypto/elliptic low-level functions (deprecated)", PKG + "crypto/elliptic", "Deprecated: for ECDH, use the GenerateKey methods of the crypto/ecdh package",
  call("elliptic", "GenerateKey|Marshal|Unmarshal|MarshalCompressed|UnmarshalCompressed"), "func f() {\n\tpriv, x, y, _ := elliptic.GenerateKey(elliptic.P256(), rand.Reader)\n\t_, _, _ = priv, x, y\n}\n",
  "func f() {\n\tkey, _ := ecdh.P256().GenerateKey(rand.Reader)\n\t_ = key\n}\n", "Use crypto/ecdh or crypto/ecdsa.", sev="minor", kind="deprecation", cat="security",
  applies={"go": ">=1.21"})
P("X509-PEM-ENCRYPTION", "x509.DecryptPEMBlock / EncryptPEMBlock (insecure, deprecated)", PKG + "crypto/x509#DecryptPEMBlock",
  "Legacy PEM encryption as specified in RFC 1423 is insecure by design.", call("x509", "DecryptPEMBlock|EncryptPEMBlock|IsEncryptedPEMBlock"),
  "func f(b *pem.Block) {\n\tder, _ := x509.DecryptPEMBlock(b, pw)\n\t_ = der\n}\n", "func f(b *pem.Block) {\n\tkey, _ := x509.ParsePKCS8PrivateKey(b.Bytes)\n\t_ = key\n}\n",
  "Not authenticated, vulnerable to padding-oracle attacks; use PKCS#8 with a modern KDF.", sev="major", kind="security", cat="security")
P("CIPHER-UNAUTHENTICATED-MODE", "cipher CFB/OFB stream modes (deprecated, unauthenticated)", PKG + "crypto/cipher#NewCFBEncrypter",
  "CFB mode is not authenticated, which generally enables active attacks to manipulate and recover the plaintext.",
  call("cipher", "NewCFBEncrypter|NewCFBDecrypter|NewOFB"), "func f(b cipher.Block, iv []byte) {\n\ts := cipher.NewCFBEncrypter(b, iv)\n\t_ = s\n}\n",
  "func f(b cipher.Block) {\n\taead, _ := cipher.NewGCM(b)\n\t_ = aead\n}\n", "Use an AEAD (cipher.NewGCM, chacha20poly1305).", sev="major", kind="security", cat="security",
  applies={"go": ">=1.24"}, docv="Go 1.24")
P("MATH-RAND-READ", "math/rand.Read (deprecated)", PKG + "math/rand#Read", "Deprecated: For almost all use cases, crypto/rand.Read is more appropriate.",
  '(call_expression function: (selector_expression operand: (identifier) @p field: (field_identifier) @f) @match (#eq? @p "rand") (#eq? @f "Read"))',
  'import "math/rand"\n\nfunc f(b []byte) {\n\trand.Read(b)\n}\n', 'import "crypto/rand"\n\nfunc f(b []byte) {\n\trand.Read(b)\n}\n',
  "math/rand bytes are predictable.", sev="major", kind="security", cat="security", filters=[r'file.has_re:"math/rand"'])
P("SET-FINALIZER", "runtime.SetFinalizer (prefer AddCleanup)", PKG + "runtime#SetFinalizer", "New Go code should consider using AddCleanup instead",
  call("runtime", "SetFinalizer"), "func f(r *Res) {\n\truntime.SetFinalizer(r, (*Res).Close)\n}\n", "func f(r *Res) {\n\truntime.AddCleanup(r, func(fd int) { syscall.Close(fd) }, r.fd)\n}\n",
  "AddCleanup avoids resurrection and cycle leaks.", sev="info", kind="modernization", cat="modernization", applies={"go": ">=1.24"}, docv="Go 1.24")
P("REFLECT-PTR", "reflect.Ptr (old name of reflect.Pointer)", PKG + "reflect#Kind", "Ptr is the old name for the Pointer kind.",
  '(selector_expression operand: (identifier) @p field: (field_identifier) @match (#eq? @p "reflect") (#match? @match "^(Ptr|PtrTo)$"))',
  "func f(t reflect.Type) bool {\n\treturn t.Kind() == reflect.Ptr\n}\n", "func f(t reflect.Type) bool {\n\treturn t.Kind() == reflect.Pointer\n}\n",
  "Use reflect.Pointer / reflect.PointerTo.", sev="info", kind="modernization", cat="modernization", applies={"go": ">=1.18"}, docv="Go 1.18")
P("TEMPLATE-HTML-CONVERSION", "template.HTML(dynamic value)", PKG + "html/template#HTML", "Use of this type presents a security risk",
  '(call_expression function: ' + sel("template", "HTML|JS|URL|CSS|HTMLAttr|JSStr|Srcset") + ' arguments: (argument_list . [(identifier) (selector_expression) (call_expression) (index_expression)])) @match',
  "func f(c string) template.HTML {\n\treturn template.HTML(c)\n}\n", "func f(c string) string {\n\treturn c\n}\n",
  "Bypasses html/template escaping; only wrap trusted, constant content.", sev="major", kind="security", cat="security", mode="ai-confirm",
  ai="Can the wrapped value contain user-controlled data?", quote="Use of this type presents a security risk: the encapsulated content should come from a trusted source, as it will be included verbatim in the template output.")
P("SSH-INSECURE-HOST-KEY", "ssh.InsecureIgnoreHostKey", "https://pkg.go.dev/golang.org/x/crypto/ssh#InsecureIgnoreHostKey", "It should not be used for production code.",
  call("ssh", "InsecureIgnoreHostKey"), "var cfg = &ssh.ClientConfig{HostKeyCallback: ssh.InsecureIgnoreHostKey()}\n",
  "var cfg = &ssh.ClientConfig{HostKeyCallback: knownhosts.New(path)}\n", "Accepting any host key allows MITM.", sev="critical", kind="security", cat="security")
P("SERVEMUX-PATTERN-OLD-GO", "Method/wildcard ServeMux pattern on Go < 1.22", PKG + "net/http#hdr-Patterns-ServeMux", "Patterns can match the method, host and path of a request.",
  '((call_expression function: (selector_expression field: (field_identifier) @f) arguments: (argument_list . (interpreted_string_literal) @s)) @match (#match? @f "^(Handle|HandleFunc)$") (#match? @s "^\\"(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) /|\\\\{[a-zA-Z_]+(\\\\.\\\\.\\\\.)?\\\\}"))',
  'func f() {\n\thttp.HandleFunc("GET /items/{id}", h)\n}\n', 'func f() {\n\thttp.HandleFunc("/items/", h)\n}\n',
  "Before Go 1.22 these patterns are literal paths and never match.", sev="critical", kind="anti-pattern", cat="compatibility", applies={"go": "<1.22"})
P("MAP-CLEAR-LOOP", "Loop deleting every map key (use clear)", "https://go.dev/ref/spec#Clear", "The built-in function clear takes an argument of map",
  '((for_statement (range_clause left: (expression_list . (identifier) @k .) right: (identifier) @m) body: (block (statement_list . (expression_statement (call_expression function: (identifier) @d arguments: (argument_list (identifier) @m2 (identifier) @k2))) .))) @match (#eq? @d "delete") (#eq? @m @m2) (#eq? @k @k2))',
  "func f(m map[string]int) {\n\tfor k := range m {\n\t\tdelete(m, k)\n\t}\n}\n", "func f(m map[string]int) {\n\tclear(m)\n}\n", "Use the clear builtin.",
  sev="info", kind="modernization", cat="modernization", applies={"go": ">=1.21"}, docv="Go 1.21")
P("PANIC-FOR-ERRORS", "panic used for ordinary error handling", CRC, "Don't use panic for normal error handling.",
  '((if_statement condition: (binary_expression left: (identifier) @e right: (nil)) consequence: (block (statement_list (expression_statement (call_expression function: (identifier) @p arguments: (argument_list (identifier) @e2))) @match))) (#eq? @p "panic") (#eq? @e @e2) (#match? @e "^err"))',
  "func Load(p string) []byte {\n\tb, err := os.ReadFile(p)\n\tif err != nil {\n\t\tpanic(err)\n\t}\n\treturn b\n}\n",
  "func Load(p string) ([]byte, error) {\n\treturn os.ReadFile(p)\n}\n", "Return the error; reserve panic for truly unrecoverable states.", sev="minor", cat="errors",
  docv="Go Code Review Comments", filters=[r"file.lacks_re:(?m)^package main\b", r"func.lacks_re:^func (\([^)]*\)\s*)?Must[A-Z]"],
  files=["!**/*_test.go"], mode="ai-confirm",
  fp=["// Command astdump prints a tree.\npackage main\n\nfunc main() {\n\tsrc, err := os.ReadFile(os.Args[1])\n\tif err != nil {\n\t\tpanic(err)\n\t}\n\t_ = src\n}\n",
      "func MustLoad(p string) []byte {\n\tb, err := os.ReadFile(p)\n\tif err != nil {\n\t\tpanic(err)\n\t}\n\treturn b\n}\n"],
  ai="Is this library/request-path code (not program init/main or a Must* helper) where the error should be returned?")

# ------------------------------------------------------------------ Sonar-way checklist gaps (own detection/wording)
P("FILE-WORLD-WRITABLE", "File mode grants write access to others", "https://pkg.go.dev/io/fs",
  "The nine least-significant bits are the standard Unix rwxrwxrwx permissions",
  '((call_expression function: (selector_expression operand: (identifier) @p field: (field_identifier) @f) arguments: (argument_list (int_literal) @match .)) (#eq? @p "os") (#match? @f "^(WriteFile|OpenFile|Chmod|Mkdir|MkdirAll)$") (#match? @match "^0[oO]?[0-7]*[2367]$"))',
  'package main\n\nimport "os"\n\nfunc save(b []byte) error {\n\treturn os.WriteFile("state.json", b, 0666)\n}\n',
  'package main\n\nimport "os"\n\nfunc save(b []byte) error {\n\treturn os.WriteFile("state.json", b, 0600)\n}\n',
  "Every local user can modify this file or directory (before umask). Drop the write bit for others.", sev="major", kind="security", cat="security",
  xref=["sonar:go:S2612"])
P("PPROF-IMPORTED", "net/http/pprof imported", "https://pkg.go.dev/net/http/pprof",
  "The package is typically only imported for the side effect of registering its HTTP handlers",
  '((import_spec name: (blank_identifier) path: (interpreted_string_literal) @match) (#eq? @match "\\"net/http/pprof\\""))',
  'package main\n\nimport (\n\t"net/http"\n\t_ "net/http/pprof"\n)\n\nfunc main() { http.ListenAndServe(":8080", nil) }\n',
  'package main\n\nimport "net/http"\n\nfunc main() { http.ListenAndServe(":8080", nil) }\n',
  "Importing pprof registers /debug/pprof/ on http.DefaultServeMux, exposing profiles, goroutine dumps and command-line flags. Serve it only on a private listener.",
  sev="major", kind="security", cat="security", mode="ai-confirm",
  ai="Is http.DefaultServeMux (or the pprof handlers) reachable from untrusted networks in production?", xref=["sonar:go:S4507"], files=["!**/*_test.go"])
P("GIN-DEBUG-MODE", "gin forced into debug mode", "https://pkg.go.dev/github.com/gin-gonic/gin", "DebugMode indicates gin mode is debug",
  '((call_expression function: (selector_expression operand: (identifier) @p field: (field_identifier) @f) arguments: (argument_list . (selector_expression operand: (identifier) @p2 field: (field_identifier) @m) .)) @match (#eq? @p "gin") (#eq? @f "SetMode") (#eq? @p2 "gin") (#eq? @m "DebugMode"))',
  'package main\n\nimport "github.com/gin-gonic/gin"\n\nfunc main() {\n\tgin.SetMode(gin.DebugMode)\n}\n',
  'package main\n\nimport "github.com/gin-gonic/gin"\n\nfunc main() {\n\tgin.SetMode(gin.ReleaseMode)\n}\n',
  "Debug mode logs every route and request detail. Leave the mode to GIN_MODE / ReleaseMode in deployed builds.",
  sev="minor", kind="security", cat="security", mode="ai-confirm", ai="Is this code path used in deployed builds (not a local dev entry point)?",
  xref=["sonar:go:S4507"], files=["!**/*_test.go"])
P("HARDCODED-PASSWORD", "Hard-coded password or secret", "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
  "Many organizations have them hardcoded within the source code in plaintext",
  '([(const_spec name: (identifier) @n value: (expression_list . (interpreted_string_literal) @match .)) (var_spec name: (identifier) @n value: (expression_list . (interpreted_string_literal) @match .)) (short_var_declaration left: (expression_list . (identifier) @n .) right: (expression_list . (interpreted_string_literal) @match .))] (#match? @n "(?i)^(password|passwd|pwd|secret|clientSecret|apiKey|apiSecret|accessToken|authToken|privateKey|secretKey|dbPassword)$") (#not-match? @match "^\\"(\\"|\\\\$\\\\{|<|%|changeme|xxx|example|test|dummy|\\\\*)"))',
  'package main\n\nconst password = "S3cr3t-Passw0rd"\n', 'package main\n\nimport "os"\n\nvar password = os.Getenv("DB_PASSWORD")\n',
  "A credential is embedded in source. Load it from the environment or a secret manager and rotate the leaked value.",
  sev="critical", kind="security", cat="security", mode="ai-confirm", ai="Is this a real credential (not a test fixture, placeholder or example value)?",
  xref=["sonar:go:S2068", "sonar:go:S6418"], files=["!**/*_test.go"])

P("COOKIE-NO-HTTPONLY", "http.Cookie for a session/token without HttpOnly", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie",
  "Forbids JavaScript from accessing the cookie",
  '((composite_literal type: (qualified_type package: (package_identifier) @p name: (type_identifier) @t) body: (literal_value) @b) @match (#eq? @p "http") (#eq? @t "Cookie") (#match? @b "(?i)Name:\\\\s*\\"[^\\"]*(session|sid|token|auth|jwt)") (#not-match? @b "HttpOnly:\\\\s*true"))',
  'package main\n\nimport "net/http"\n\nfunc login(w http.ResponseWriter, sid string) {\n\thttp.SetCookie(w, &http.Cookie{Name: "session", Value: sid, Secure: true})\n}\n',
  'package main\n\nimport "net/http"\n\nfunc login(w http.ResponseWriter, sid string) {\n\thttp.SetCookie(w, &http.Cookie{Name: "session", Value: sid, Secure: true, HttpOnly: true})\n}\n',
  "Scripts on the page (including injected ones) can read this session cookie. Set HttpOnly: true (and Secure, SameSite).",
  sev="major", kind="security", cat="security", cwe=["CWE-1004"], xref=["sonar:go:S3330"])
P("COOKIE-NO-SECURE", "http.Cookie for a session/token without Secure", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie",
  "Indicates that the cookie is sent to the server only when a request is made with the",
  '((composite_literal type: (qualified_type package: (package_identifier) @p name: (type_identifier) @t) body: (literal_value) @b) @match (#eq? @p "http") (#eq? @t "Cookie") (#match? @b "(?i)Name:\\\\s*\\"[^\\"]*(session|sid|token|auth|jwt)") (#not-match? @b "Secure:"))',
  'package main\n\nimport "net/http"\n\nfunc login(w http.ResponseWriter, sid string) {\n\thttp.SetCookie(w, &http.Cookie{Name: "session", Value: sid, HttpOnly: true})\n}\n',
  'package main\n\nimport "net/http"\n\nfunc login(w http.ResponseWriter, sid string) {\n\thttp.SetCookie(w, &http.Cookie{Name: "session", Value: sid, HttpOnly: true, Secure: true})\n}\n',
  "Without Secure the session cookie is also sent over plain HTTP. Set Secure: true.",
  sev="major", kind="security", cat="security", mode="ai-confirm", ai="Is this service reachable over HTTPS in production (so Secure would not break it), or is Secure set elsewhere (e.g. a cookie wrapper)?",
  cwe=["CWE-614"], xref=["sonar:go:S2092"])

RULES = P.R

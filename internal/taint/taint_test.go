package taint

import (
	"testing"

	"github.com/elmo/code-review-engine/internal/grammars"
	ts "github.com/tree-sitter/go-tree-sitter"
)

func run(t *testing.T, grammar, src string) []Hit {
	t.Helper()
	p := ts.NewParser()
	defer p.Close()
	if err := p.SetLanguage(grammars.Get(grammar)); err != nil {
		t.Fatal(err)
	}
	tree := p.Parse([]byte(src), nil)
	defer tree.Close()
	l, err := Spec(Family(grammar))
	if err != nil {
		t.Fatal(err)
	}
	return Analyze(Convert(tree.RootNode()), []byte(src), Family(grammar), l)
}

func classes(hs []Hit) map[string]int {
	m := map[string]int{}
	for _, h := range hs {
		m[h.Class]++
	}
	return m
}

func TestTaintCases(t *testing.T) {
	cases := []struct {
		name, grammar, src string
		want               map[string]int
	}{
		{"java sqli concat", "java", `import java.sql.*;
class A { void f(HttpServletRequest request, Connection c) throws Exception {
  String p = request.getParameter("id");
  String sql = "SELECT * FROM t WHERE id='" + p + "'";
  Statement st = c.createStatement();
  st.executeQuery(sql);
} }`, map[string]int{"sqli": 1}},
		{"java prepared is safe", "java", `import java.sql.*;
class A { void f(HttpServletRequest request, Connection c) throws Exception {
  String p = request.getParameter("id");
  PreparedStatement ps = c.prepareStatement("SELECT * FROM t WHERE id=?");
  ps.setString(1, p);
  ps.executeQuery();
} }`, map[string]int{}},
		{"java constant-folded if", "java", `import java.sql.*;
class A { void f(HttpServletRequest request, Connection c) throws Exception {
  String param = request.getParameter("id");
  String bar;
  int num = 86;
  if ((7 * 42) - num > 200) bar = "This_should_always_happen";
  else bar = param;
  c.createStatement().execute("SELECT " + bar);
} }`, map[string]int{}},
		{"java ternary taken", "java", `import java.sql.*;
class A { void f(HttpServletRequest request, Connection c) throws Exception {
  String param = request.getParameter("id");
  int num = 50;
  String bar = (7 * 18) + num > 200 ? "x" : param;
  c.createStatement().execute("SELECT " + bar);
} }`, map[string]int{"sqli": 1}},
		{"java map keys", "java", `import java.sql.*;
class A { void f(HttpServletRequest request, Connection c) throws Exception {
  String param = request.getParameter("id");
  java.util.HashMap<String,Object> map = new java.util.HashMap<String,Object>();
  map.put("keyA", "a_Value");
  map.put("keyB", param);
  map.put("keyC", "another_Value");
  String bar = (String) map.get("keyA");
  c.createStatement().execute("SELECT " + bar);
} }`, map[string]int{}},
		{"java list index", "java", `import java.sql.*;
class A { void f(HttpServletRequest request, Connection c) throws Exception {
  String param = request.getParameter("id");
  java.util.List<String> l = new java.util.ArrayList<String>();
  l.add("safe"); l.add(param); l.add("moresafe");
  l.remove(0);
  String bar = l.get(1);
  String bad = l.get(0);
  c.createStatement().execute("SELECT " + bar);
  c.createStatement().execute("SELECT " + bad);
} }`, map[string]int{"sqli": 1}},
		{"java switch const", "java", `import java.sql.*;
class A { void f(HttpServletRequest request, Connection c) throws Exception {
  String param = request.getParameter("id");
  String guess = "ABC";
  char switchTarget = guess.charAt(1);
  String bar;
  switch (switchTarget) {
    case 'A': bar = param; break;
    case 'B': bar = "bob"; break;
    default: bar = param; break;
  }
  c.createStatement().execute("SELECT " + bar);
} }`, map[string]int{}},
		{"java summary helper", "java", `import java.sql.*;
class A { void f(HttpServletRequest request, Connection c) throws Exception {
  String param = request.getParameter("id");
  String bar = new Test().doSomething(request, param);
  String ok = new Test().safe(param);
  c.createStatement().execute("SELECT " + bar);
  c.createStatement().execute("SELECT " + ok);
}
  private class Test {
    public String doSomething(HttpServletRequest request, String param) { String b = "x" + param; return b; }
    public String safe(String param) { return "constant"; }
  }
}`, map[string]int{"sqli": 1}},
		{"java xss sanitized", "java", `class A { void f(HttpServletRequest request, HttpServletResponse response) throws Exception {
  String p = request.getParameter("q");
  response.getWriter().println("hi " + org.owasp.esapi.ESAPI.encoder().encodeForHTML(p));
  response.getWriter().println("hi " + p);
} }`, map[string]int{"xss": 1}},
		{"java path + cookies loop", "java", `class A { void f(HttpServletRequest request) throws Exception {
  javax.servlet.http.Cookie[] cs = request.getCookies();
  String param = "none";
  for (javax.servlet.http.Cookie c : cs) { if (c.getName().equals("x")) { param = java.net.URLDecoder.decode(c.getValue(), "UTF-8"); } }
  java.io.File f = new java.io.File("/tmp/" + param);
} }`, map[string]int{"path": 1}},
		{"java spring param", "java", `import org.springframework.jdbc.core.JdbcTemplate;
class C { JdbcTemplate jdbcTemplate;
  String f(@RequestParam String name) { jdbcTemplate.batchUpdate("DELETE FROM t WHERE n='" + name + "'"); return "ok"; }
}`, map[string]int{"sqli": 1}},
		{"java runtime exec", "java", `class A { void f(HttpServletRequest request) throws Exception {
  String p = request.getParameter("h");
  Runtime r = Runtime.getRuntime();
  r.exec(new String[] {"ping", "-c", "1", p});
} }`, map[string]int{"cmdi": 1}},
		{"python flask path + xss", "python", `from flask import request
import codecs
def init(app):
    @app.route('/x', methods=['POST'])
    def x_post():
        RESPONSE = ""
        param = request.cookies.get("x", "none")
        bar = "This should never happen"
        if 'should' in bar:
            bar = param
        f = codecs.open(f'/tmp/{bar}', 'r', 'utf-8')
        RESPONSE += escape_for_html(bar)
        return RESPONSE
`, map[string]int{"path": 1}},
		{"python dead branch", "python", `from flask import request
def init(app):
    @app.route('/x', methods=['POST'])
    def x_post():
        param = request.args.get("x")
        bar = "safe"
        if 'unsafe' in bar:
            bar = param
        return open(bar).read()
`, map[string]int{}},
		{"python reflected xss", "python", `from flask import request
def init(app):
    @app.route('/x')
    def x():
        name = request.args.get("name", "")
        return "<p>Hello " + name + "</p>"
`, map[string]int{"xss": 1}},
		{"python sqli params safe", "python", `from flask import request
def v(cur):
    bar = request.form.get("x")
    cur.execute("SELECT * FROM t WHERE a = ?", (bar,))
    cur.execute("SELECT * FROM t WHERE a = '" + bar + "'")
`, map[string]int{"sqli": 1}},
		{"python subprocess shell", "python", `from flask import request
import subprocess
def v():
    p = request.args.get("x")
    subprocess.run("ls " + p, shell=True)
    subprocess.run(["ls", p])
`, map[string]int{"cmdi": 1}},
		{"js express", "javascript", `const { exec } = require('child_process');
const fs = require('fs');
app.get('/x', (req, res) => {
  const f = req.query.file;
  fs.readFile('/data/' + f, (e, d) => res.send(d));
  exec('ls ' + req.query.dir);
  res.send('<p>' + req.query.name + '</p>');
  res.send('<p>' + escapeHtml(req.query.name) + '</p>');
});`, map[string]int{"path": 1, "cmdi": 1, "xss": 1}},
		{"php", "php", `<?php
$id = $_GET['id'];
$q = "SELECT * FROM users WHERE id = " . $id;
mysqli_query($conn, $q);
$safe = intval($_GET['n']);
mysqli_query($conn, "SELECT * FROM t WHERE n = " . $safe);
echo "Hello " . $_GET['name'];
echo "Hello " . htmlspecialchars($_GET['name']);
include($_GET['page'] . '.php');
system("ping " . escapeshellarg($_GET['h']));
`, map[string]int{"sqli": 1, "xss": 1, "path": 1}},
		{"go", "go", `package main
import ("database/sql"; "net/http"; "os/exec"; "fmt")
func h(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	db.Query("SELECT * FROM t WHERE id = " + id)
	db.Query("SELECT * FROM t WHERE id = $1", id)
	exec.Command("sh", "-c", "ls "+r.FormValue("d")).Run()
	fmt.Fprintf(w, "<p>%s</p>", id)
}`, map[string]int{"sqli": 1, "cmdi": 1, "xss": 1}},
		{"kotlin", "kotlin", `import java.sql.Connection
fun f(request: HttpServletRequest, c: Connection) {
    val p = request.getParameter("x")
    val sql = "SELECT * FROM t WHERE a = '" + p + "'"
    c.createStatement().executeQuery(sql)
    val file = File("/tmp/" + p)
}`, map[string]int{"sqli": 1, "path": 1}},
		{"kotlin string template", "kotlin", `import java.sql.Connection
fun f(request: HttpServletRequest, c: Connection) {
    val p = request.getParameter("x")
    c.createStatement().executeQuery("SELECT * FROM t WHERE a = '$p'")
    c.createStatement().executeQuery("SELECT * FROM t WHERE a = '\$p'")
}`, map[string]int{"sqli": 1}},
		{"python folding + guards + dead code", "python", `from flask import Flask, request
import flask
app = Flask(__name__)
@app.route("/a", methods=["POST"])
def a():
    param = request.form.get("p")
    num = 106
    bar = "x" if 7 * 18 + num > 200 else param
    open(bar)
    if 7 * 42 - 86 > 200:
        b2 = "y"
    else:
        b2 = param
    open(b2)
    if '../' in param:
        return "no"
    open(param)
@app.route("/b", methods=["GET"])
def b():
    return "ok"
    return flask.redirect(request.args.get("n"))
@app.route("/c", methods=["POST"])
def c():
    p = request.form.get("p")
    if p.startswith("/"):
        return "bad"
    open(p)
    if not p:
        return ""
    eval(p)
`, map[string]int{"path": 1, "code": 1}},
		{"java batchUpdate", "java", `import org.springframework.jdbc.core.JdbcTemplate;
class C { void f(HttpServletRequest request, JdbcTemplate jdbcTemplate) {
    String v = request.getParameter("v");
    jdbcTemplate.batchUpdate("UPDATE t SET a = '" + v + "'");
} }`, map[string]int{"sqli": 1}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := classes(run(t, c.grammar, c.src))
			for k, v := range c.want {
				if got[k] != v {
					t.Errorf("%s: got %v want %v", k, got, c.want)
				}
			}
			for k, v := range got {
				if c.want[k] == 0 && v > 0 {
					t.Errorf("unexpected %s: got %v want %v (hits %+v)", k, got, c.want, run(t, c.grammar, c.src))
				}
			}
		})
	}
}

func runFull(t *testing.T, grammar, src string) Result {
	t.Helper()
	p := ts.NewParser()
	defer p.Close()
	if err := p.SetLanguage(grammars.Get(grammar)); err != nil {
		t.Fatal(err)
	}
	tree := p.Parse([]byte(src), nil)
	defer tree.Close()
	l, err := Spec(Family(grammar))
	if err != nil {
		t.Fatal(err)
	}
	return AnalyzeFull(Convert(tree.RootNode()), []byte(src), Family(grammar), l)
}

func TestCleanSinksAndDicts(t *testing.T) {
	py := `from flask import Flask, request, session
import subprocess
app = Flask(__name__)

@app.post("/a")
def a():
    p = request.form.get("p")
    m = {"x": "'ok'", "y": p}
    eval(m["x"])
    eval(m["y"])

def helper(cmd):
    subprocess.run(cmd, shell=True)

@app.post("/b")
def b():
    p = request.form.get("p")
    session[p] = "1"
    session["k"] = "v"
`
	r := runFull(t, "python", py)
	if got := classes(r.Hits); got["code"] != 1 || got["trust"] != 1 {
		t.Fatalf("hits %v", got)
	}
	if got := classes(r.Clean); got["code"] != 1 || got["trust"] != 1 || got["cmdi"] != 0 {
		t.Fatalf("clean %v (helper without a source must not be clean)", got)
	}
	js := `const app = require('express')();
app.get('/x', (req, res) => {
  const m = {a: 'ls', b: req.query.c};
  require('child_process').exec(m.a);
  eval(m['a']);
});
`
	if got := classes(run(t, "javascript", js)); got["code"] != 0 {
		t.Fatalf("js dict literal: %v", got)
	}
}

func TestURLAllowList(t *testing.T) {
	py := `import requests
from urllib.parse import urlparse
from flask import Flask, request, redirect
app = Flask(__name__)
ALLOWED = {"api.example.com"}

@app.get("/a")
def a():
    url = request.args.get("u")
    if urlparse(url).hostname not in ALLOWED:
        return "no", 400
    requests.get(url)
    return "ok"

@app.get("/b")
def b():
    url = request.args.get("u")
    p = urlparse(url)
    if p.hostname in ALLOWED and p.scheme == "https":
        requests.get(url)
    return "ok"

@app.get("/c")
def c():
    nxt = request.args.get("next")
    if nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect("/")

@app.get("/bad")
def bad():
    url = request.args.get("u")
    if url.startswith("http"):
        requests.get(url)
    return "x"
`
	if got := classes(run(t, "python", py)); got["ssrf"] != 1 || got["redirect"] != 0 {
		t.Fatalf("python allow-list: %v", got)
	}
	java := `import javax.servlet.http.*;
class C {
  static final java.util.Set<String> HOSTS = java.util.Set.of("api.example.com");
  java.io.InputStream f(HttpServletRequest request) throws Exception {
    String u = request.getParameter("u");
    java.net.URI uri = new java.net.URI(u);
    if (!HOSTS.contains(uri.getHost())) { throw new IllegalArgumentException(); }
    return new java.net.URL(u).openStream();
  }
}
`
	if got := classes(run(t, "java", java)); got["ssrf"] != 0 {
		t.Fatalf("java allow-list: %v", got)
	}
	golang := `package main
import "net/http"
var allowed = map[string]bool{"api.example.com": true}
func h(w http.ResponseWriter, r *http.Request) {
	raw := r.URL.Query().Get("u")
	u, _ := url.Parse(raw)
	if !allowed[u.Host] {
		return
	}
	http.Get(raw)
}
`
	if got := classes(run(t, "go", golang)); got["ssrf"] != 0 {
		t.Fatalf("go allow-list: %v", got)
	}
}

// Corpus look-alikes found on OSS code (express examples, microservices-demo).
func TestCorpusNearMisses(t *testing.T) {
	cases := []struct {
		name, grammar, src string
		want               map[string]int
	}{
		{"js slice indexes", "javascript", `const app = require('express')();
app.get('/u/:from-:to', function (req, res) {
  var from = req.params.from, to = req.params.to;
  res.send('users ' + names.slice(from, to + 1).join(', '));
});`, map[string]int{}},
		{"js slice receiver", "javascript", `const app = require('express')();
app.get('/u', function (req, res) {
  res.send('<b>' + req.query.q.slice(0, 10) + '</b>');
});`, map[string]int{"xss": 1}},
		{"js same-site redirect", "javascript", `const app = require('express')();
app.post('/u/:id', function (req, res) { res.redirect('/user/' + req.params.id); });`, map[string]int{}},
		{"js open redirect", "javascript", `const app = require('express')();
app.get('/r', function (req, res) { res.redirect(req.query.next); });`, map[string]int{"redirect": 1}},
		{"js protocol-relative redirect", "javascript", `const app = require('express')();
app.get('/r', function (req, res) { res.redirect('//' + req.query.host); });`, map[string]int{"redirect": 1}},
		{"go json body", "go", `package m
import ("encoding/json"; "net/http")
func h(w http.ResponseWriter, r *http.Request) {
	b, _ := json.Marshal(map[string]string{"q": r.FormValue("q")})
	w.Write(b)
}`, map[string]int{}},
		{"py return dict var", "python", `from flask import Flask, request
app = Flask(__name__)
@app.post("/a")
def a():
    data = {"content": request.json["prompt"]}
    return data`, map[string]int{}},
		{"py return str var", "python", `from flask import Flask, request
app = Flask(__name__)
@app.get("/a")
def a():
    data = "<p>" + request.args["q"]
    return data`, map[string]int{"xss": 1}},
	}
	for _, c := range cases {
		got := classes(run(t, c.grammar, c.src))
		for k, v := range c.want {
			if got[k] != v {
				t.Errorf("%s: %s=%d, want %d (%v)", c.name, k, got[k], v, got)
			}
		}
		if len(c.want) == 0 && len(got) > 0 {
			t.Errorf("%s: unexpected %v", c.name, got)
		}
	}
}

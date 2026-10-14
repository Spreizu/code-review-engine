package taint

import (
	"reflect"
	"testing"

	"github.com/elmo/code-review-engine/internal/grammars"
	ts "github.com/tree-sitter/go-tree-sitter"
)

func runProject(t *testing.T, grammar string, files map[string]string, caller string) map[string]int {
	t.Helper()
	fam := Family(grammar)
	l, err := Spec(fam)
	if err != nil {
		t.Fatal(err)
	}
	parse := func(src string) (*ts.Tree, func()) {
		p := ts.NewParser()
		if err := p.SetLanguage(grammars.Get(grammar)); err != nil {
			t.Fatal(err)
		}
		tr := p.Parse([]byte(src), nil)
		return tr, func() { tr.Close(); p.Close() }
	}
	x := NewIndex()
	for path, src := range files {
		tr, done := parse(src)
		x.Add(fam, Summarize(Convert(tr.RootNode()), []byte(src), fam, path, l))
		done()
	}
	SetProject(x)
	defer SetProject(nil)
	tr, done := parse(files[caller])
	defer done()
	return classes(AnalyzeFullAt(Convert(tr.RootNode()), []byte(files[caller]), fam, caller, l).Hits)
}

func TestCrossFile(t *testing.T) {
	pyDB := `import sqlite3
def find_user(conn, name):
    return conn.execute("SELECT * FROM u WHERE n = '" + name + "'")
def safe_int(v):
    return int(v)
`
	cases := []struct {
		name, grammar string
		files         map[string]string
		caller        string
		want          map[string]int
	}{
		{"py from-import sink", "python", map[string]string{"app/db.py": pyDB, "app/views.py": `from flask import Flask, request
from app.db import find_user
app = Flask(__name__)
@app.get("/u")
def u():
    find_user(None, request.args["n"])
    return "ok"
`}, "app/views.py", map[string]int{"sqli": 1}},
		{"py module-attr sink", "python", map[string]string{"app/db.py": pyDB, "app/views.py": `from flask import Flask, request
from app import db
app = Flask(__name__)
@app.get("/u")
def u():
    db.find_user(None, request.args["n"])
    return "ok"
`}, "app/views.py", map[string]int{"sqli": 1}},
		{"py not imported", "python", map[string]string{"app/db.py": pyDB, "app/views.py": `from flask import Flask, request
app = Flask(__name__)
@app.get("/u")
def u():
    find_user(None, request.args["n"])
    return "ok"
`}, "app/views.py", map[string]int{}},
		{"py sanitiser across files", "python", map[string]string{"app/db.py": pyDB, "app/views.py": `import os
from flask import Flask, request
from app.db import safe_int
app = Flask(__name__)
@app.get("/u")
def u():
    os.system("kill " + str(safe_int(request.args["p"])))
    return "ok"
`}, "app/views.py", map[string]int{}},
		{"js require sink", "javascript", map[string]string{"lib/run.js": `const cp = require('child_process');
function runTool(arg) { cp.exec('tool ' + arg); }
module.exports = { runTool };
`, "routes/a.js": `const { runTool } = require('../lib/run');
app.get('/x', (req, res) => { runTool(req.query.a); res.send('ok'); });
`}, "routes/a.js", map[string]int{"cmdi": 1}},
		{"js ambiguous name not followed", "javascript", map[string]string{"lib/run.js": `const cp = require('child_process');
function runTool(arg) { cp.exec('tool ' + arg); }
`, "routes/a.js": `const { runTool } = require('./other');
app.get('/x', (req, res) => { runTool(req.query.a); res.send('ok'); });
`}, "routes/a.js", map[string]int{}},
		{"go same package", "go", map[string]string{"svc/db.go": "package svc\nimport \"os/exec\"\nfunc RunCmd(name string) { exec.Command(name).Run() }\n",
			"svc/h.go": "package svc\nimport \"net/http\"\nfunc h(w http.ResponseWriter, r *http.Request) { RunCmd(r.FormValue(\"c\")) }\n"}, "svc/h.go", map[string]int{"cmdi": 1}},
		{"java static helper", "java", map[string]string{"src/a/Db.java": `package a;
import java.sql.*;
public class Db { public static void find(Connection c, String n) throws Exception { c.createStatement().executeQuery("SELECT " + n); } }
`, "src/b/Ctl.java": `package b;
import a.Db;
class Ctl { void h(HttpServletRequest request) throws Exception { Db.find(null, request.getParameter("n")); } }
`}, "src/b/Ctl.java", map[string]int{"sqli": 1}},
		{"java typed field", "java", map[string]string{"src/a/Repo.java": `package a;
import java.sql.*;
public class Repo { Connection c; public void find(String n) throws Exception { c.createStatement().executeQuery("SELECT " + n); } }
`, "src/a/Ctl.java": `package a;
class Ctl { private Repo repo; void h(HttpServletRequest request) throws Exception { repo.find(request.getParameter("n")); } }
`}, "src/a/Ctl.java", map[string]int{"sqli": 1}},
		{"java other class same name", "java", map[string]string{"src/a/Repo.java": `package a;
import java.sql.*;
public class Repo { Connection c; public void find(String n) throws Exception { c.createStatement().executeQuery("SELECT " + n); } }
`, "src/a/Ctl.java": `package a;
class Ctl { private Cache repo; void h(HttpServletRequest request) throws Exception { repo.find(request.getParameter("n")); } }
`}, "src/a/Ctl.java", map[string]int{}},
		{"php typed property", "php", map[string]string{"src/Repo.php": `<?php
namespace App;
class Repo { function find($n) { mysqli_query($this->db, "SELECT * FROM u WHERE n='" . $n . "'"); } }
`, "src/Ctl.php": `<?php
namespace App;
class Ctl { private Repo $repo; function h() { $this->repo->find($_GET['n']); } }
`}, "src/Ctl.php", map[string]int{"sqli": 1}},
		{"sequelize via project module", "typescript", map[string]string{"routes/search.ts": `import * as models from '../models/index'
export function search () {
  return (req, res) => {
    const criteria = req.query.q
    models.sequelize.query(` + "`SELECT * FROM P WHERE name LIKE '%${criteria}%'`" + `).then(() => res.end())
  }
}
`}, "routes/search.ts", map[string]int{"sqli": 1}},
		{"js || yields the operand", "typescript", map[string]string{"routes/login.ts": "import * as models from '../models/index'\nexport function login () {\n  return (req, res) => { models.sequelize.query(`SELECT * FROM U WHERE email = '${req.body.email || ''}'`, { plain: true }) }\n}\n"}, "routes/login.ts", map[string]int{"sqli": 1}},
		{"py class method", "python", map[string]string{"app/db.py": `import sqlite3
class Repo:
    def find(self, name):
        return conn.execute("SELECT * FROM u WHERE n = '" + name + "'")
`, "app/views.py": `from flask import Flask, request
from app.db import Repo
app = Flask(__name__)
repo = Repo()
@app.get("/u")
def u():
    repo.find(request.args["n"])
    return "ok"
`}, "app/views.py", map[string]int{"sqli": 1}},
		{"py class method not constructed", "python", map[string]string{"app/db.py": `import sqlite3
class Repo:
    def find(self, name):
        return conn.execute("SELECT * FROM u WHERE n = '" + name + "'")
`, "app/views.py": `from flask import Flask, request
from app.db import Repo
app = Flask(__name__)
@app.get("/u")
def u():
    repo.find(request.args["n"])
    return "ok"
`}, "app/views.py", map[string]int{}},
		{"js class method", "javascript", map[string]string{"lib/run.js": `const cp = require('child_process');
class Runner {
  runTool(arg) { cp.exec('tool ' + arg); }
}
module.exports = { Runner };
`, "routes/a.js": `const { Runner } = require('../lib/run');
const runner = new Runner();
app.get('/x', (req, res) => { runner.runTool(req.query.a); res.send('ok'); });
`}, "routes/a.js", map[string]int{"cmdi": 1}},
		{"go method same package", "go", map[string]string{"svc/db.go": "package svc\nimport \"os/exec\"\ntype Store struct{}\nfunc (s *Store) RunCmd(name string) { exec.Command(name).Run() }\n",
			"svc/h.go": "package svc\nimport \"net/http\"\nfunc h(w http.ResponseWriter, r *http.Request, s *Store) { s.RunCmd(r.FormValue(\"c\")) }\n"}, "svc/h.go", map[string]int{"cmdi": 1}},
		{"go method wrong type", "go", map[string]string{"svc/db.go": "package svc\nimport \"os/exec\"\ntype Store struct{}\nfunc (s *Store) RunCmd(name string) { exec.Command(name).Run() }\n",
			"svc/h.go": "package svc\nimport \"net/http\"\nfunc h(w http.ResponseWriter, r *http.Request, s *Other) { s.RunCmd(r.FormValue(\"c\")) }\n"}, "svc/h.go", map[string]int{}},
		{"kotlin typed field", "kotlin", map[string]string{"src/a/Repo.kt": `package a
import java.sql.*
class Repo { var c: Connection? = null
  fun find(n: String) { c!!.createStatement().executeQuery("SELECT " + n) }
}
`, "src/a/Ctl.kt": `package a
class Ctl { private val repo: Repo
  fun h(request: javax.servlet.http.HttpServletRequest) { repo.find(request.getParameter("n")) }
}
`}, "src/a/Ctl.kt", map[string]int{"sqli": 1}},
	}
	for _, c := range []struct {
		name, grammar, src string
		want               map[string]int
	}{
		{"php numeric octets", "php", `<?php
$target = $_REQUEST['ip'];
$octet = explode(".", $target);
if (is_numeric($octet[0]) && is_numeric($octet[1])) {
  $t = $octet[0] . '.' . $octet[1];
  shell_exec('ping ' . $t);
}`, map[string]int{}},
		{"php numeric one octet (twin)", "php", `<?php
$target = $_REQUEST['ip'];
$octet = explode(".", $target);
if (is_numeric($octet[0])) {
  $t = $octet[0] . '.' . $octet[1];
  shell_exec('ping ' . $t);
}`, map[string]int{"cmdi": 1}},
		{"py isdigit early return", "python", `import os
from flask import request
def f():
    n = request.args["n"]
    if not n.isdigit():
        return "bad"
    os.system("kill " + n)
`, map[string]int{}},
	} {
		if got := classes(run(t, c.grammar, c.src)); !reflect.DeepEqual(got, c.want) {
			t.Errorf("%s: got %v, want %v", c.name, got, c.want)
		}
	}
	for _, c := range cases {
		if got := runProject(t, c.grammar, c.files, c.caller); !reflect.DeepEqual(got, c.want) {
			t.Errorf("%s: got %v, want %v", c.name, got, c.want)
		}
	}
}

func TestGoPathValue(t *testing.T) {
	src := `package p
import (
	"net/http"
	"os/exec"
)
func h(w http.ResponseWriter, r *http.Request) {
	exec.Command(r.PathValue("c")).Run()
}
`
	if got := classes(run(t, "go", src)); !reflect.DeepEqual(got, map[string]int{"cmdi": 1}) {
		t.Errorf("PathValue: got %v, want cmdi", got)
	}
}

func TestGoSniffedPlainText(t *testing.T) {
	for _, c := range []struct {
		src  string
		want map[string]int
	}{
		{"package p\nimport \"net/http\"\nfunc h(w http.ResponseWriter, r *http.Request) { w.Write([]byte(fmt.Sprintf(\"user id %v\", r.FormValue(\"id\")))) }\n", map[string]int{}},
		{"package p\nimport \"net/http\"\nfunc h(w http.ResponseWriter, r *http.Request) { w.Write([]byte(\"<p>\" + r.FormValue(\"id\"))) }\n", map[string]int{"xss": 1}},
		{"package p\nimport \"net/http\"\nfunc h(w http.ResponseWriter, r *http.Request) { fmt.Fprintf(w, \"hello %s\", r.FormValue(\"n\")) }\n", map[string]int{}},
		{"package p\nimport \"net/http\"\nfunc h(w http.ResponseWriter, r *http.Request) { fmt.Fprintf(w, \"<b>%s</b>\", r.FormValue(\"n\")) }\n", map[string]int{"xss": 1}},
	} {
		if got := classes(run(t, "go", c.src)); !reflect.DeepEqual(got, c.want) {
			t.Errorf("%q: got %v, want %v", c.src, got, c.want)
		}
	}
}

func TestQueryOnlyRedirect(t *testing.T) {
	for _, c := range []struct {
		src  string
		want map[string]int
	}{
		{"from django.http import HttpResponseRedirect\ndef v(request):\n    url = build_absolute_uri(request, '/finish')\n    return HttpResponseRedirect(f\"{url}?{urlencode({'code': request.GET['code']})}\")\n", map[string]int{}},
		{"from django.http import HttpResponseRedirect\ndef v(request):\n    return HttpResponseRedirect(f\"{request.GET['next']}?a=1\")\n", map[string]int{"redirect": 1}},
		{"from django.http import HttpResponse\ndef v(request):\n    return HttpResponse(request.GET['e'], content_type=\"text/plain\")\n", map[string]int{}},
	} {
		if got := classes(run(t, "python", c.src)); !reflect.DeepEqual(got, c.want) {
			t.Errorf("%q: got %v, want %v", c.src, got, c.want)
		}
	}
}

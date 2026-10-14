package taint

import (
	"reflect"
	"strings"
	"testing"
)

// Each framework model fires with the framework imported and stays silent on the same code
// without it (the import guard).
func TestFrameworkModels(t *testing.T) {
	cases := []struct {
		name, grammar, imp, src string
		want                    map[string]int
	}{
		{"javalin", "java", "import io.javalin.Javalin;\n", `class A { void h(Context ctx) throws Exception {
  new java.io.File(ctx.queryParam("f")).delete();
} }`, map[string]int{"path": 1}},
		{"javalin html", "java", "import io.javalin.Javalin;\n", `class A { void h(Context ctx) {
  ctx.html("<p>" + ctx.pathParam("n"));
} }`, map[string]int{"xss": 1}},
		{"quarkus", "java", "import org.jboss.resteasy.reactive.RestQuery;\n", `class A { String h(@RestQuery String f) throws Exception {
  return new String(java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(f)));
} }`, map[string]int{"path": 2}},
		{"webflux", "java", "import org.springframework.web.reactive.function.server.ServerRequest;\n", `class A { void h(ServerRequest request) throws Exception {
  String n = request.pathVariable("n");
  Runtime.getRuntime().exec(n);
} }`, map[string]int{"cmdi": 1}},
		{"javalin kotlin", "kotlin", "import io.javalin.Javalin\n", `fun h(ctx: Context) {
  java.io.File(ctx.queryParam("f")).delete()
}`, map[string]int{"path": 1}},
		{"aiohttp", "python", "from aiohttp import web\n", `import os
async def h(request):
    os.system(request.match_info["cmd"])
`, map[string]int{"cmdi": 1}},
		{"falcon", "python", "import falcon\n", `import os
class R:
    def on_get(self, req, resp):
        os.system(req.get_param("cmd"))
`, map[string]int{"cmdi": 1}},
		{"nestjs", "typescript", "import { Controller, Get, Query } from '@nestjs/common';\n", `const cp = require('child_process');
class C {
  run(@Query('c') c: string) { cp.exec(c); }
}`, map[string]int{"cmdi": 1}},
		{"hapi", "javascript", "const Hapi = require('@hapi/hapi');\n", `const cp = require('child_process');
function h(request) { cp.exec(request.payload.cmd); }`, map[string]int{"cmdi": 1}},
		{"fiber", "go", "import \"github.com/gofiber/fiber/v2\"\n", `func h(c *fiber.Ctx) error {
	return c.SendFile(c.Query("f"))
}`, map[string]int{"path": 1}},
		{"chi", "go", "import \"github.com/go-chi/chi/v5\"\nimport \"os/exec\"\n", `func h(w http.ResponseWriter, r *http.Request) {
	exec.Command(chi.URLParam(r, "c")).Run()
}`, map[string]int{"cmdi": 1}},
		{"psr7", "php", "use Psr\\Http\\Message\\ServerRequestInterface;\n", `function h($request) {
  $p = $request->getQueryParams();
  system($p['c']);
}`, map[string]int{"cmdi": 1}},
		{"codeigniter", "php", "use CodeIgniter\\Controller;\n", `class C extends Controller { function h() {
  system($this->request->getGet('c'));
} }`, map[string]int{"cmdi": 1}},
		{"symfony", "php", "use Symfony\\Component\\HttpFoundation\\Request;\n", `function h($request) {
  system($request->getContent());
}`, map[string]int{"cmdi": 1}},
		{"micronaut", "java", "import io.micronaut.http.annotation.QueryValue;\n", `class A { String h(@QueryValue String f) throws Exception {
  return new String(java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(f)));
} }`, map[string]int{"path": 2}},
		{"vertx", "java", "import io.vertx.ext.web.RoutingContext;\n", `class A { void h(RoutingContext ctx) throws Exception {
  Runtime.getRuntime().exec(ctx.pathParam("c"));
} }`, map[string]int{"cmdi": 1}},
		{"sparkjava", "java", "import spark.Request;\n", `class A { void h(Request req) throws Exception {
  new java.io.File(req.queryParams("f")).delete();
} }`, map[string]int{"path": 1}},
		{"http4k", "kotlin", "import org.http4k.core.Request\n", `fun h(request: Request) {
  java.lang.Runtime.getRuntime().exec(request.query("c"))
}`, map[string]int{"cmdi": 1}},
		{"play", "java", "import play.mvc.Http;\n", `class A { void h(play.mvc.Http.Request request) throws Exception {
  Runtime.getRuntime().exec(request.queryString().get("c")[0]);
} }`, map[string]int{"cmdi": 1}},
	}
	for _, c := range cases {
		src := c.src
		head := ""
		switch c.grammar {
		case "php":
			head = "<?php\n"
		case "go":
			head = "package p\n"
		}
		got := classes(run(t, c.grammar, head+c.imp+src))
		if !reflect.DeepEqual(got, c.want) {
			t.Errorf("%s: got %v, want %v", c.name, got, c.want)
		}
		if c.grammar == "go" && strings.Contains(c.imp, "os/exec") {
			src = "import \"os/exec\"\n" + src
		}
		if got := classes(run(t, c.grammar, head+src)); len(got) != 0 {
			t.Errorf("%s without import: got %v, want none", c.name, got)
		}
	}
}

func TestTrustLookupIsStoredData(t *testing.T) {
	src := `from aiohttp import web
async def login(request):
    data = await request.post()
    user = await User.get_by_username(conn, data['username'])
    session['user_id'] = user.id
    session['name'] = data['username']
`
	if got := classes(run(t, "python", src)); !reflect.DeepEqual(got, map[string]int{"trust": 1}) {
		t.Errorf("got %v, want one trust flow (the raw name, not the looked-up id)", got)
	}
}

package taint

import (
	"reflect"
	"testing"
)

// Adversarial near-misses for the Java taint rules promoted to deterministic (sqli, cmdi, path,
// xss): look-alikes of the vulnerable shape that must stay silent, each next to the vulnerable
// twin that must still fire.
func TestJavaPromotedNearMisses(t *testing.T) {
	const head = "import java.io.*; import java.sql.*; import javax.servlet.http.*;\nclass C extends HttpServlet {\n"
	cases := []struct {
		name, body string
		want       map[string]int
	}{
		{"sqli prepared placeholder", `void doGet(HttpServletRequest request, HttpServletResponse response, Connection con) throws Exception {
	String id = request.getParameter("id");
	PreparedStatement ps = con.prepareStatement("SELECT * FROM users WHERE id = ?");
	ps.setString(1, id);
	ps.executeQuery();
}`, map[string]int{}},
		{"sqli concatenated (twin)", `void doGet(HttpServletRequest request, HttpServletResponse response, Connection con) throws Exception {
	String id = request.getParameter("id");
	Statement st = con.createStatement();
	st.executeQuery("SELECT * FROM users WHERE id = '" + id + "'");
}`, map[string]int{"sqli": 1}},
		{"sqli numeric parse", `void doGet(HttpServletRequest request, HttpServletResponse response, Connection con) throws Exception {
	int id = Integer.parseInt(request.getParameter("id"));
	Statement st = con.createStatement();
	st.executeQuery("SELECT * FROM users WHERE id = " + id);
}`, map[string]int{}},
		{"sqli constant overwrite", `void doGet(HttpServletRequest request, HttpServletResponse response, Connection con) throws Exception {
	String col = request.getParameter("sort");
	col = "name";
	con.createStatement().executeQuery("SELECT * FROM users ORDER BY " + col);
}`, map[string]int{}},
		{"cmdi constant argv", `void doGet(HttpServletRequest request, HttpServletResponse response) throws Exception {
	String who = request.getParameter("u");
	new ProcessBuilder("ls", "-l", "/tmp").start();
	response.getWriter().println(who.length());
}`, map[string]int{}},
		{"cmdi request argv (twin)", `void doGet(HttpServletRequest request, HttpServletResponse response) throws Exception {
	String dir = request.getParameter("d");
	new ProcessBuilder("ls", "-l", dir).start();
}`, map[string]int{"cmdi": 1}},
		{"path file name only", `void doGet(HttpServletRequest request, HttpServletResponse response) throws Exception {
	String f = request.getParameter("f");
	new FileInputStream(new File("/data", new File(f).getName()));
}`, map[string]int{}},
		{"path raw (twin)", `void doGet(HttpServletRequest request, HttpServletResponse response) throws Exception {
	String f = request.getParameter("f");
	new FileInputStream("/data/" + f);
}`, map[string]int{"path": 1}},
		{"xss encoded", `void doGet(HttpServletRequest request, HttpServletResponse response) throws Exception {
	String q = request.getParameter("q");
	response.getWriter().println("<p>" + org.owasp.esapi.ESAPI.encoder().encodeForHTML(q) + "</p>");
}`, map[string]int{}},
		{"xss length only", `void doGet(HttpServletRequest request, HttpServletResponse response) throws Exception {
	String q = request.getParameter("q");
	response.getWriter().println("len=" + q.length());
}`, map[string]int{}},
		{"xss query result", `void doGet(HttpServletRequest request, HttpServletResponse response, org.springframework.jdbc.core.JdbcTemplate jdbcTemplate) throws Exception {
	String u = request.getParameter("u");
	Long n = jdbcTemplate.queryForObject("SELECT COUNT(*) FROM t WHERE u = ?", Long.class, u);
	response.getWriter().println("count " + n);
}`, map[string]int{}},
		{"xss raw (twin)", `void doGet(HttpServletRequest request, HttpServletResponse response) throws Exception {
	String q = request.getParameter("q");
	response.getWriter().println("<p>" + q + "</p>");
}`, map[string]int{"xss": 1}},
	}
	for _, c := range cases {
		got := classes(run(t, "java", head+c.body+"\n}\n"))
		if !reflect.DeepEqual(got, c.want) {
			t.Errorf("%s: got %v, want %v", c.name, got, c.want)
		}
	}
}

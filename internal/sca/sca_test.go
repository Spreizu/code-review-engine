package sca

import (
	"archive/zip"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/elmo/code-review-engine/internal/engine"
)

func parse(t *testing.T, rel string) map[string]Package {
	t.Helper()
	b, err := os.ReadFile(filepath.Join("testdata", rel))
	if err != nil {
		t.Fatal(err)
	}
	ps, err := ParseFile(rel, b)
	if err != nil {
		t.Fatalf("%s: %v", rel, err)
	}
	m := map[string]Package{}
	for _, p := range ps {
		m[p.Ecosystem+" "+p.Name+"@"+p.Version] = p
	}
	return m
}

func TestLockfileParsers(t *testing.T) {
	cases := map[string][]string{
		"package-lock.json":        {"npm lodash@4.17.20", "npm @babel/core@7.24.0", "npm minimist@1.2.5"},
		"npm-v1/package-lock.json": {"npm express@4.17.1", "npm qs@6.7.0"},
		"yarn.lock":                {"npm @types/node@20.11.5", "npm minimist@1.2.5"},
		"yarn-berry/yarn.lock":     {"npm axios@1.6.0"},
		"pnpm-lock.yaml":           {"npm vue@3.4.21", "npm @vue/shared@3.4.21"},
		"pnpm9/pnpm-lock.yaml":     {"npm next@14.1.0", "npm @next/env@14.1.0"},
		"composer.lock":            {"Packagist guzzlehttp/guzzle@7.4.4", "Packagist symfony/http-kernel@5.4.19", "Packagist phpunit/phpunit@9.6.0"},
		"go.mod":                   {"Go github.com/gin-gonic/gin@1.9.0", "Go golang.org/x/net@0.17.0", "Go github.com/docker/docker@20.10.24", "Go stdlib@1.21.5"},
		"gosum-only/go.sum":        {"Go github.com/gorilla/websocket@1.4.0"},
		"poetry.lock":              {"PyPI django@4.2.1", "PyPI typing-extensions@4.9.0"},
		"Pipfile.lock":             {"PyPI requests@2.25.0", "PyPI flask@2.0.0", "PyPI pytest@7.0.0"},
		"requirements.txt":         {"PyPI jinja2@2.11.2", "PyPI urllib3@1.26.4"},
		"gradle.lockfile":          {"Maven com.fasterxml.jackson.core:jackson-databind@2.13.0", "Maven org.apache.logging.log4j:log4j-core@2.14.1"},
		"pom.xml":                  {"Maven org.springframework:spring-webmvc@5.3.17", "Maven junit:junit@4.12"},
	}
	notWanted := map[string][]string{
		"package-lock.json":        {"local-lib"},
		"npm-v1/package-lock.json": {"mylib"},
		"yarn-berry/yarn.lock":     {"app"},
		"composer.lock":            {"acme/dev-thing"},
		"requirements.txt":         {"pyyaml"},
		"pom.xml":                  {"managed"},
	}
	for rel, want := range cases {
		got := parse(t, rel)
		for _, w := range want {
			if _, ok := got[w]; !ok {
				keys := make([]string, 0, len(got))
				for k := range got {
					keys = append(keys, k)
				}
				slices.Sort(keys)
				t.Errorf("%s: missing %s (got %v)", rel, w, keys)
			}
		}
		if len(got) != len(want) {
			t.Errorf("%s: got %d packages, want %d", rel, len(got), len(want))
		}
		for _, n := range notWanted[rel] {
			for k := range got {
				if strings.Contains(k, " "+n+"@") {
					t.Errorf("%s: must skip %s", rel, k)
				}
			}
		}
	}
	if p := parse(t, "package-lock.json")["npm @babel/core@7.24.0"]; !p.Dev || p.Line != 8 {
		t.Errorf("dev flag / line: %+v", p)
	}
	if p := parse(t, "pom.xml")["Maven junit:junit@4.12"]; !p.Dev {
		t.Error("test-scoped maven dependency should be dev")
	}
}

func TestCompare(t *testing.T) {
	for _, c := range []struct {
		eco, a, b string
		want      int
	}{
		{EcoNPM, "1.2.3", "1.2.10", -1},
		{EcoNPM, "1.0.0-rc.1", "1.0.0", -1},
		{EcoNPM, "1.0.0-alpha", "1.0.0-beta", -1},
		{EcoNPM, "1.0.0-rc.2", "1.0.0-rc.10", -1},
		{EcoGo, "v0.17.0", "0.17.0", 0},
		{EcoPyPI, "2.0.0rc1", "2.0.0", -1},
		{EcoPyPI, "2.0.0.post1", "2.0.0", 1},
		{EcoPyPI, "1.26.4", "1.26.18", -1},
		{EcoMaven, "2.14.1", "2.15.0", -1},
		{EcoMaven, "2.13.4.2", "2.13.4", 1},
		{EcoMaven, "5.3.17", "5.3.18", -1},
		{EcoMaven, "1.0-SNAPSHOT", "1.0", -1},
		{EcoMaven, "1.0.Final", "1.0", 0},
		{EcoPackagist, "5.4.19", "5.4.20", -1},
	} {
		if got := Compare(c.eco, c.a, c.b); (got > 0) != (c.want > 0) || (got < 0) != (c.want < 0) {
			t.Errorf("Compare(%s, %s, %s) = %d, want %d", c.eco, c.a, c.b, got, c.want)
		}
	}
}

func TestCVSS3(t *testing.T) {
	for v, want := range map[string]float64{
		"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H": 9.8,
		"CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:H": 7.2,
		"CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N": 6.1,
		"CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H": 10.0,
		"CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:N": 0,
	} {
		got, ok := CVSS3Score(v)
		if !ok || got != want {
			t.Errorf("%s = %.1f (%v), want %.1f", v, got, ok, want)
		}
	}
	if _, ok := CVSS3Score("CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N"); ok {
		t.Error("CVSS 4 vector must not be scored by the v3 calculator")
	}
	if SeverityOf(9.8, "") != "critical" || SeverityOf(7.2, "") != "major" || SeverityOf(0, "MODERATE") != "minor" {
		t.Error("severity mapping")
	}
}

// Fixture advisories in OSV format (hand-written for the tests, shaped like the real records).
var fixtureVulns = map[string]string{
	"GHSA-35jh-r3h4-6jhm": `{"id":"GHSA-35jh-r3h4-6jhm","summary":"Command Injection in lodash","aliases":["CVE-2021-23337"],"modified":"2024-01-01T00:00:00Z",
	  "severity":[{"type":"CVSS_V3","score":"CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:H"}],
	  "affected":[{"package":{"ecosystem":"npm","name":"lodash"},"ranges":[{"type":"SEMVER","events":[{"introduced":"0"},{"fixed":"4.17.21"}]}]}],
	  "database_specific":{"severity":"HIGH","cwe_ids":["CWE-77","CWE-94"]}}`,
	"GHSA-xvch-5gv4-984h": `{"id":"GHSA-xvch-5gv4-984h","summary":"Prototype Pollution in minimist","aliases":["CVE-2021-44906"],"modified":"2024-01-01T00:00:00Z",
	  "severity":[{"type":"CVSS_V3","score":"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}],
	  "affected":[{"package":{"ecosystem":"npm","name":"minimist"},"ranges":[{"type":"SEMVER","events":[{"introduced":"0"},{"fixed":"0.2.4"},{"introduced":"1.0.0"},{"fixed":"1.2.6"}]}]}],
	  "database_specific":{"severity":"CRITICAL","cwe_ids":["CWE-1321"]}}`,
	"PYSEC-2021-59": `{"id":"PYSEC-2021-59","aliases":["CVE-2021-23337","GHSA-35jh-r3h4-6jhm"],"affected":[{"package":{"ecosystem":"npm","name":"lodash"},"versions":["4.17.20"]}]}`,
	"GHSA-jfh8-c2jp-5v3q": `{"id":"GHSA-jfh8-c2jp-5v3q","summary":"Remote code injection in Log4j","aliases":["CVE-2021-44228"],"modified":"2024-01-01T00:00:00Z",
	  "severity":[{"type":"CVSS_V3","score":"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"}],
	  "affected":[{"package":{"ecosystem":"Maven","name":"org.apache.logging.log4j:log4j-core"},"ranges":[{"type":"ECOSYSTEM","events":[{"introduced":"2.13.0"},{"fixed":"2.15.0"},{"introduced":"2.0-beta9"},{"fixed":"2.3.1"}]}]}]}`,
	"GHSA-withdrawn": `{"id":"GHSA-withdrawn","withdrawn":"2024-01-01T00:00:00Z","affected":[{"package":{"ecosystem":"npm","name":"lodash"},"ranges":[{"type":"SEMVER","events":[{"introduced":"0"}]}]}]}`,
	"GHSA-last":      `{"id":"GHSA-last","affected":[{"package":{"ecosystem":"PyPI","name":"Jinja2"},"ranges":[{"type":"ECOSYSTEM","events":[{"introduced":"0"},{"last_affected":"2.11.2"}]}]}],"database_specific":{"severity":"MODERATE"}}`,
}

func vuln(t *testing.T, id string) *Vuln {
	var v Vuln
	if err := json.Unmarshal([]byte(fixtureVulns[id]), &v); err != nil {
		t.Fatal(id, err)
	}
	return &v
}

func TestMatch(t *testing.T) {
	ok, ranges, fixed := Match(vuln(t, "GHSA-xvch-5gv4-984h"), Package{Ecosystem: EcoNPM, Name: "minimist", Version: "1.2.5"})
	if !ok || fixed != "1.2.6" || len(ranges) != 2 || ranges[1] != ">=1.0.0 <1.2.6" {
		t.Errorf("minimist: %v %v %q", ok, ranges, fixed)
	}
	if ok, _, _ := Match(vuln(t, "GHSA-xvch-5gv4-984h"), Package{Ecosystem: EcoNPM, Name: "minimist", Version: "1.2.6"}); ok {
		t.Error("fixed version must not match")
	}
	if ok, _, fixed := Match(vuln(t, "GHSA-jfh8-c2jp-5v3q"), Package{Ecosystem: EcoMaven, Name: "org.apache.logging.log4j:log4j-core", Version: "2.14.1"}); !ok || fixed != "2.15.0" {
		t.Errorf("log4j: %v %q", ok, fixed)
	}
	if ok, _, _ := Match(vuln(t, "GHSA-withdrawn"), Package{Ecosystem: EcoNPM, Name: "lodash", Version: "1.0.0"}); ok {
		t.Error("withdrawn advisory must not match")
	}
	if ok, _, fixed := Match(vuln(t, "GHSA-last"), Package{Ecosystem: EcoPyPI, Name: "jinja2", Version: "2.11.2"}); !ok || fixed != "" {
		t.Errorf("last_affected / PEP 503 name: %v %q", ok, fixed)
	}
	if ok, _, _ := Match(vuln(t, "GHSA-last"), Package{Ecosystem: EcoPyPI, Name: "jinja2", Version: "2.11.3"}); ok {
		t.Error("above last_affected must not match")
	}
}

func project(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	for _, f := range []string{"package-lock.json", "requirements.txt", "gradle.lockfile"} {
		b, _ := os.ReadFile(filepath.Join("testdata", f))
		os.WriteFile(filepath.Join(root, f), b, 0o644)
	}
	os.MkdirAll(filepath.Join(root, "node_modules", "x"), 0o755)
	os.WriteFile(filepath.Join(root, "node_modules", "x", "package-lock.json"), []byte(`{"packages":{"node_modules/lodash":{"version":"1.0.0"}}}`), 0o644)
	return root
}

func osvServer(t *testing.T) (*httptest.Server, *int) {
	byPkg := map[string][]string{"npm/lodash/4.17.20": {"GHSA-35jh-r3h4-6jhm", "PYSEC-2021-59"}, "npm/minimist/1.2.5": {"GHSA-xvch-5gv4-984h"},
		"Maven/org.apache.logging.log4j:log4j-core/2.14.1": {"GHSA-jfh8-c2jp-5v3q"}, "PyPI/jinja2/2.11.2": {"GHSA-last"}}
	calls := 0
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		switch {
		case r.Method == http.MethodPost && r.URL.Path == "/v1/querybatch":
			var body struct {
				Queries []struct {
					Package struct{ Name, Ecosystem string }
					Version string
				}
			}
			json.NewDecoder(r.Body).Decode(&body)
			type id struct {
				ID string `json:"id"`
			}
			var res struct {
				Results []map[string][]id `json:"results"`
			}
			for _, q := range body.Queries {
				m := map[string][]id{}
				for _, v := range byPkg[q.Package.Ecosystem+"/"+q.Package.Name+"/"+q.Version] {
					m["vulns"] = append(m["vulns"], id{v})
				}
				res.Results = append(res.Results, m)
			}
			json.NewEncoder(w).Encode(res)
		case strings.HasPrefix(r.URL.Path, "/v1/vulns/"):
			id := strings.TrimPrefix(r.URL.Path, "/v1/vulns/")
			if fixtureVulns[id] == "" {
				http.NotFound(w, r)
				return
			}
			w.Write([]byte(fixtureVulns[id]))
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(srv.Close)
	return srv, &calls
}

func TestScanOnline(t *testing.T) {
	srv, _ := osvServer(t)
	res, err := Scan(context.Background(), Options{Root: project(t), Mode: "online", APIURL: srv.URL, Timeout: 5 * time.Second})
	if err != nil {
		t.Fatal(err)
	}
	got := map[string]bool{}
	for _, f := range res.Findings {
		got[f.Vuln.Package+" "+f.Vuln.ID] = true
		if f.RuleID != RuleID || f.Category != "security" || f.Status != "confirmed" || f.Location.Path == "" || f.Location.StartLine == 0 {
			t.Errorf("finding fields: %+v", f)
		}
		switch f.Vuln.ID {
		case "GHSA-35jh-r3h4-6jhm":
			if f.Severity != "major" || f.Vuln.CVSSScore != 7.2 || f.Vuln.Fixed != "4.17.21" || len(f.Vuln.CVE) != 1 || f.Vuln.CVE[0] != "CVE-2021-23337" ||
				!strings.Contains(f.Message, "Fixed in 4.17.21") || f.CWE[0] != "CWE-77" || f.Location.StartLine != 6 {
				t.Errorf("lodash finding: %+v %+v", f, f.Vuln)
			}
		case "GHSA-jfh8-c2jp-5v3q":
			if f.Severity != "critical" || f.Vuln.Fixed != "2.15.0" || f.Location.Path != "gradle.lockfile" {
				t.Errorf("log4j finding: %+v", f.Vuln)
			}
		case "GHSA-last":
			if f.Severity != "minor" || f.Vuln.Fixed != "" || !strings.Contains(f.Message, "No fixed version") {
				t.Errorf("jinja2 finding: %+v", f.Vuln)
			}
		}
	}
	for _, w := range []string{"lodash GHSA-35jh-r3h4-6jhm", "minimist GHSA-xvch-5gv4-984h", "org.apache.logging.log4j:log4j-core GHSA-jfh8-c2jp-5v3q", "jinja2 GHSA-last"} {
		if !got[w] {
			t.Errorf("missing %s (got %v)", w, got)
		}
	}
	if got["lodash PYSEC-2021-59"] {
		t.Error("alias advisory must be merged into the primary one")
	}
	if len(res.Findings) != 4 || res.Vulnerable != 4 {
		t.Errorf("findings %d vulnerable %d", len(res.Findings), res.Vulnerable)
	}
	// node_modules lockfiles are never read
	for _, f := range res.Findings {
		if strings.Contains(f.Location.Path, "node_modules") {
			t.Error("scanned node_modules")
		}
	}
}

func TestScanOnlineFailureIsAWarning(t *testing.T) {
	res, err := Scan(context.Background(), Options{Root: project(t), Mode: "online", APIURL: "http://127.0.0.1:1", Timeout: time.Second})
	if err != nil || len(res.Findings) != 0 || len(res.Warnings) == 0 || !strings.Contains(res.Warnings[0], "OSV.dev query failed") {
		t.Fatalf("err=%v warnings=%v", err, res.Warnings)
	}
}

func writeDB(t *testing.T, dir, eco string, ids []string, updated time.Time) {
	t.Helper()
	d := filepath.Join(dir, eco)
	os.MkdirAll(d, 0o755)
	f, _ := os.Create(filepath.Join(d, "all.zip"))
	zw := zip.NewWriter(f)
	for _, id := range ids {
		w, _ := zw.Create(id + ".json")
		w.Write([]byte(fixtureVulns[id]))
	}
	zw.Close()
	f.Close()
	b, _ := json.Marshal(Meta{Ecosystem: eco, Updated: updated, Advisories: len(ids)})
	os.WriteFile(filepath.Join(d, "meta.json"), b, 0o644)
}

func TestScanOffline(t *testing.T) {
	dir := t.TempDir()
	now := time.Date(2026, 10, 10, 12, 0, 0, 0, time.UTC)
	writeDB(t, dir, EcoNPM, []string{"GHSA-35jh-r3h4-6jhm", "GHSA-xvch-5gv4-984h", "GHSA-withdrawn"}, now.Add(-2*24*time.Hour))
	writeDB(t, dir, EcoMaven, []string{"GHSA-jfh8-c2jp-5v3q"}, now.Add(-30*24*time.Hour))
	res, err := Scan(context.Background(), Options{Root: project(t), Mode: "offline", Dir: dir, MaxAge: 7 * 24 * time.Hour, Now: func() time.Time { return now }})
	if err != nil {
		t.Fatal(err)
	}
	ids := map[string]bool{}
	for _, f := range res.Findings {
		ids[f.Vuln.ID] = true
	}
	if !ids["GHSA-35jh-r3h4-6jhm"] || !ids["GHSA-xvch-5gv4-984h"] || !ids["GHSA-jfh8-c2jp-5v3q"] || ids["GHSA-withdrawn"] || len(res.Findings) != 3 {
		t.Errorf("offline findings: %v", ids)
	}
	w := strings.Join(res.Warnings, "\n")
	if !strings.Contains(w, "Maven database is 30 days old") || strings.Contains(w, "npm database is") {
		t.Errorf("freshness warning: %s", w)
	}
	if !strings.Contains(w, "no offline PyPI database") {
		t.Errorf("missing-ecosystem warning: %s", w)
	}
}

func TestScanOffAndDiffScope(t *testing.T) {
	root := project(t)
	if res, _ := Scan(context.Background(), Options{Root: root, Mode: "off"}); res.Packages != 0 {
		t.Error("mode off must not parse lockfiles")
	}
	srv, _ := osvServer(t)
	res, _ := Scan(context.Background(), Options{Root: root, Mode: "online", APIURL: srv.URL, InScope: func(rel string) bool { return rel == "gradle.lockfile" }})
	if len(res.Findings) != 1 || res.Findings[0].Vuln.ID != "GHSA-jfh8-c2jp-5v3q" {
		t.Errorf("diff scope: %d findings", len(res.Findings))
	}
}

func TestUpdate(t *testing.T) {
	src := t.TempDir()
	writeDB(t, src, EcoNPM, []string{"GHSA-35jh-r3h4-6jhm"}, time.Now())
	zb, _ := os.ReadFile(filepath.Join(src, EcoNPM, "all.zip"))
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/npm/all.zip" {
			http.NotFound(w, r)
			return
		}
		w.Write(zb)
	}))
	defer srv.Close()
	dir := t.TempDir()
	metas, err := Update(context.Background(), dir, []string{EcoNPM}, srv.Client(), srv.URL+"/%s/all.zip")
	if err != nil || len(metas) != 1 || metas[0].Advisories != 1 {
		t.Fatalf("update: %v %+v", err, metas)
	}
	if m, ok := ReadMeta(dir, EcoNPM); !ok || time.Since(m.Updated) > time.Minute {
		t.Error("meta not written")
	}
	if _, err := Update(context.Background(), dir, []string{"PyPI"}, srv.Client(), srv.URL+"/%s/all.zip"); err == nil {
		t.Error("404 must fail")
	}
	if m, ok := ReadMeta(dir, EcoNPM); !ok || m.Advisories != 1 {
		t.Error("failed update must keep the previous database")
	}
}

func TestDiscoverHonoursPathFilter(t *testing.T) {
	root := project(t)
	os.MkdirAll(filepath.Join(root, "tools", "cache", "repo"), 0o755)
	b, _ := os.ReadFile(filepath.Join("testdata", "composer.lock"))
	os.WriteFile(filepath.Join(root, "tools", "cache", "repo", "composer.lock"), b, 0o644)
	os.WriteFile(filepath.Join(root, "tools", ".gitignore"), []byte("/cache/\n"), 0o644)
	all, _, _ := Discover(root, nil)
	filtered, _, _ := Discover(root, engine.PathFilter(root, nil, false, false))
	has := func(ps []Package) bool {
		for _, p := range ps {
			if strings.HasPrefix(p.File, "tools/cache/") {
				return true
			}
		}
		return false
	}
	if !has(all) || has(filtered) {
		t.Errorf("gitignored lockfile: unfiltered %v filtered %v", has(all), has(filtered))
	}
	if ignored, _, _ := Discover(root, engine.PathFilter(root, []string{"gradle.lockfile"}, true, false)); len(ignored) == len(all) {
		t.Error("ignore globs not applied")
	}
}

package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestNormalizeAndQuote(t *testing.T) {
	txt := Normalize([]byte("<html><script>x()</script><p>The <code>foo</code>  API is&nbsp;deprecated.</p></html>"))
	if strings.Contains(txt, "x()") || !QuoteOK(txt, "The foo API is deprecated.") {
		t.Fatalf("normalize: %q", txt)
	}
}

func TestDiffAndDeprecations(t *testing.T) {
	prev := "Intro sentence that stays here. The old helper is documented here."
	cur := "Intro sentence that stays here. The helper is deprecated and will be removed in 3.0. A brand new option was added today."
	add, rem := Diff(prev, cur)
	if len(add) != 2 || len(rem) != 1 {
		t.Fatalf("added %q removed %q", add, rem)
	}
	if d := DeprecationLines(add); len(d) != 1 || !strings.Contains(d[0], "deprecated") {
		t.Fatalf("deprecations %q", d)
	}
}

func TestRunSnapshots(t *testing.T) {
	page := "<p>Use slices.Contains for membership tests in Go code.</p>"
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/gone" {
			http.NotFound(w, r)
			return
		}
		w.Write([]byte(page))
	}))
	defer srv.Close()
	st := &Store{Dir: t.TempDir()}
	f := &Fetcher{Client: srv.Client()}
	srcs := []source{{URL: srv.URL + "/doc", CitedBy: []string{"R1", "R2"}}, {URL: srv.URL + "/gone"}}
	q := map[string][]ruleQuote{srv.URL + "/doc": {{ID: "R1", Quote: "Use slices.Contains for membership"}, {ID: "R2", Quote: "Use sort.Strings"}}}

	rep := Run(srcs, q, st, f, false, 2)
	if rep.Checked != 2 || rep.Errors != 1 || rep.Changed != 0 || rep.QuotesMissing != 1 || !rep.Pages[0].FirstSnapshot {
		t.Fatalf("first run: %+v %+v", rep, rep.Pages[0])
	}
	page = "<p>Use slices.Contains for membership tests in Go code.</p><p>The sort.Strings function is deprecated since Go 1.22.</p>"
	rep = Run(srcs[:1], q, st, &Fetcher{Client: srv.Client()}, false, 1) // new run = new fetch cache
	p := rep.Pages[0]
	if !p.Changed || len(p.Deprecations) != 1 || rep.QuotesMissing != 1 {
		t.Fatalf("second run: %+v", p)
	}
	rep = Run(srcs[:1], q, st, f, true, 1) // offline: quotes against snapshot only
	if rep.Pages[0].Changed || rep.QuotesMissing != 1 {
		t.Fatalf("offline: %+v", rep.Pages[0])
	}
	md := Markdown(rep)
	if !strings.Contains(md, "Missing rule quotes") || !strings.Contains(md, "R2") {
		t.Fatalf("markdown:\n%s", md)
	}
}

func TestNewer(t *testing.T) {
	for _, c := range []struct {
		a, b string
		want bool
	}{{"1.27.3", "1.27.2", true}, {"1.27", "1.27.0", false}, {"26.0.0", "26.11.1", false}, {"4.0", "3.10.0", true}} {
		if Newer(c.a, c.b) != c.want {
			t.Errorf("Newer(%s,%s)", c.a, c.b)
		}
	}
}

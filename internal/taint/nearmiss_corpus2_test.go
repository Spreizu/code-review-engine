package taint

import (
	"reflect"
	"testing"
)

// Corpus triage 2026-10-10 (gke-samples, django-allauth, caddy, chi, echo): fixed-host requests,
// reverse()-based redirects, project send_mail methods and same-origin path redirects, each with a
// vulnerable twin so the fix does not hide the real pattern.
func TestCorpusTriageNearMisses(t *testing.T) {
	cases := []struct {
		name, lang, src string
		want            map[string]int
	}{
		{"py ssrf fixed service host", "python", `import requests
from flask import Flask, request
app = Flask(__name__)
BOOK_SERVICE_URL = "http://books"
@app.get("/b")
def b():
    r = requests.get(f"{BOOK_SERVICE_URL}/book/{request.args['id']}")
    return "ok"`, map[string]int{}},
		{"py ssrf user host (twin)", "python", `import requests
from flask import Flask, request
app = Flask(__name__)
@app.get("/b")
def b():
    r = requests.get(f"{request.args['host']}/book")
    return "ok"`, map[string]int{"ssrf": 1}},
		{"django redirect to reverse() with query", "python", `from django.http import HttpResponseRedirect
from django.urls import reverse
def v(request):
    return HttpResponseRedirect(f"{reverse('authorize')}?{request.POST.urlencode()}")`, map[string]int{}},
		{"django redirect to user url (twin)", "python", `from django.http import HttpResponseRedirect
def v(request):
    return HttpResponseRedirect(request.GET["next"])`, map[string]int{"redirect": 1}},
		{"go redirect after stripping leading slashes", "go", `package p
import ("net/http"; "strings")
func h(w http.ResponseWriter, r *http.Request) {
	p := r.URL.Path
	for strings.HasPrefix(p, "//") {
		p = strings.TrimPrefix(p, "/")
	}
	http.Redirect(w, r, p+"/", http.StatusMovedPermanently)
}`, map[string]int{}},
		{"go redirect to query value (twin)", "go", `package p
import "net/http"
func h(w http.ResponseWriter, r *http.Request) {
	http.Redirect(w, r, r.URL.Query().Get("next"), http.StatusFound)
}`, map[string]int{"redirect": 1}},
	}
	for _, c := range cases {
		got := classes(run(t, c.lang, c.src))
		if !reflect.DeepEqual(got, c.want) {
			t.Errorf("%s: got %v, want %v", c.name, got, c.want)
		}
	}
}

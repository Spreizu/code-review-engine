package taint

import (
	"reflect"
	"testing"
)

// Corpus-expansion near-misses (scrapy, Django REST framework): look-alikes of request data and
// HTML responses that are neither.
func TestPythonFrameworkNearMisses(t *testing.T) {
	cases := []struct {
		name, src string
		want      map[string]int
	}{
		{"scrapy request object", `from pathlib import Path
from scrapy import Request
def download(request):
    return Path(request.url).read_bytes()`, map[string]int{}},
		{"flask request (twin)", `from pathlib import Path
from flask import Flask, request
app = Flask(__name__)
@app.get("/f")
def f():
    open(request.args["p"]).close()
    return "ok"`, map[string]int{"path": 1}},
		{"drf response is rendered", `from rest_framework.response import Response
from rest_framework.decorators import api_view
@api_view(["GET"])
def echo(request):
    return Response({"q": request.query_params["q"]})`, map[string]int{}},
		{"flask Response raw (twin)", `from flask import Flask, Response, request
app = Flask(__name__)
@app.get("/e")
def e():
    return Response("<p>" + request.args["q"])`, map[string]int{"xss": 1}},
	}
	for _, c := range cases {
		got := classes(run(t, "python", c.src))
		if !reflect.DeepEqual(got, c.want) {
			t.Errorf("%s: got %v, want %v", c.name, got, c.want)
		}
	}
}

package main

import (
	"encoding/json"
	"fmt"
	"maps"
	"net/http"
	"os"
	"slices"
	"strings"

	"gopkg.in/yaml.v3"
)

// LatestVersion compares one version dimension with its upstream registry.
type LatestVersion struct {
	Dim      string `json:"dim"`
	Catalog  string `json:"catalog"`
	Upstream string `json:"upstream,omitempty"`
	Source   string `json:"source"`
	Outdated bool   `json:"outdated"`
	Error    string `json:"error,omitempty"`
}

// upstreams maps a dimension to a JSON endpoint and an extractor.
var upstreams = map[string]struct {
	url  string
	pick func(any) string
}{
	"go":          {"https://go.dev/dl/?mode=json", func(v any) string { return strings.TrimPrefix(str(idx(v, 0), "version"), "go") }},
	"node":        {"https://nodejs.org/dist/index.json", func(v any) string { return strings.TrimPrefix(str(idx(v, 0), "version"), "v") }},
	"python":      eol("python"),
	"php":         eol("php"),
	"kotlin":      eol("kotlin"),
	"gradle":      eol("gradle"),
	"terraform":   eol("terraform"),
	"spring-boot": eol("spring-boot"),
	"vue":         npm("vue"),
	"nuxt":        npm("nuxt"),
	"typescript":  npm("typescript"),
	"react":       npm("react"),
	"angular":     npm("@angular/core"),
	"nuxt-ui":     npm("@nuxt/ui"),
	"payload":     npm("payload"),
	"vueuse":      npm("@vueuse/core"),
	"graphql":     npm("graphql"),
	"npm":         npm("npm"),
	"pnpm":        npm("pnpm"),
}

func eol(product string) struct {
	url  string
	pick func(any) string
} {
	return struct {
		url  string
		pick func(any) string
	}{"https://endoflife.date/api/" + product + ".json", func(v any) string { return str(idx(v, 0), "latest") }}
}

func npm(pkg string) struct {
	url  string
	pick func(any) string
} {
	return struct {
		url  string
		pick func(any) string
	}{"https://registry.npmjs.org/" + pkg + "/latest", func(v any) string { return str(v, "version") }}
}

func idx(v any, i int) any {
	if a, ok := v.([]any); ok && len(a) > i {
		return a[i]
	}
	return nil
}

func str(v any, k string) string {
	if m, ok := v.(map[string]any); ok {
		if s, ok := m[k].(string); ok {
			return s
		}
	}
	return ""
}

// CheckLatest fetches upstream versions for the dimensions in the latest-versions file.
func CheckLatest(c *http.Client, path string) []LatestVersion {
	b, err := os.ReadFile(path)
	if err != nil {
		return []LatestVersion{{Dim: "*", Error: err.Error()}}
	}
	var f struct {
		Latest map[string]string `yaml:"latest"`
	}
	if err := yaml.Unmarshal(b, &f); err != nil {
		return []LatestVersion{{Dim: "*", Error: err.Error()}}
	}
	dims := slices.Sorted(maps.Keys(f.Latest))
	var out []LatestVersion
	for _, d := range dims {
		u, ok := upstreams[d]
		l := LatestVersion{Dim: d, Catalog: f.Latest[d]}
		if !ok {
			l.Source, l.Error = "-", "no registry endpoint; check its release page manually"
			out = append(out, l)
			continue
		}
		l.Source = u.url
		v, err := getJSON(c, u.url)
		if err != nil {
			l.Error = err.Error()
		} else if l.Upstream = u.pick(v); l.Upstream == "" {
			l.Error = "no version in response"
		} else {
			l.Outdated = Newer(l.Upstream, l.Catalog)
		}
		out = append(out, l)
	}
	return out
}

func getJSON(c *http.Client, url string) (any, error) {
	req, _ := http.NewRequest("GET", url, nil)
	req.Header.Set("User-Agent", "crev ruleupdate")
	resp, err := c.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}
	var v any
	return v, json.NewDecoder(resp.Body).Decode(&v)
}

// Newer reports whether version a is greater than b (numeric dotted comparison).
func Newer(a, b string) bool {
	pa, pb := strings.Split(a, "."), strings.Split(b, ".")
	for i := 0; i < len(pa) || i < len(pb); i++ {
		var x, y int
		if i < len(pa) {
			fmt.Sscanf(pa[i], "%d", &x)
		}
		if i < len(pb) {
			fmt.Sscanf(pb[i], "%d", &y)
		}
		if x != y {
			return x > y
		}
	}
	return false
}

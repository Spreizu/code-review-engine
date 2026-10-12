package projcfg

import (
	"encoding/json"
	"strings"
)

func init() {
	register(golangci, ".golangci.yml", ".golangci.yaml", ".golangci.json", ".golangci.toml")
	register(staticcheckConf, "staticcheck.conf")
	register(reviveTOML, "revive.toml")
}

// golangci reads golangci-lint v1 and v2 configs: explicitly disabled linters, govet analyzer
// enable/disable, staticcheck checks ("-SA1019"), gosec excludes, revive rule disables and
// path-scoped exclusion rules (issues.exclude-rules / linters.exclusions.rules without a text
// filter).
func golangci(s *Set, c ctx, b []byte) error {
	var m map[string]any
	var err error
	if strings.HasSuffix(c.rel, ".toml") {
		m, err = parseTOML(string(b))
	} else if strings.HasSuffix(c.rel, ".json") {
		err = json.Unmarshal(b, &m)
	} else {
		m, err = loose(b)
	}
	if err != nil {
		return err
	}
	linters, _ := m["linters"].(map[string]any)
	off := func(linter string, d Directive) {
		for _, t := range linterTools(linter) {
			d.Tool = t
			s.add(d)
		}
	}
	for _, l := range listOf(linters["disable"]) {
		off(l, c.d("", "*", true))
	}
	// explicitly enabled linters ("<linter>:<linter>"): opt-in crev rules with that equivalent
	// (e.g. gocyclo, funlen, godox, mnd) switch on when the project runs the linter
	for _, l := range listOf(linters["enable"]) {
		s.add(c.d(l, l, false))
	}
	settings, _ := m["linters-settings"].(map[string]any)
	if v2, ok := linters["settings"].(map[string]any); ok {
		settings = v2
	}
	if gv, ok := settings["govet"].(map[string]any); ok {
		for _, a := range listOf(gv["disable"]) {
			s.add(c.d("govet", a, true))
		}
		if gv["disable-all"] == true {
			s.add(c.d("govet", "*", true))
			for _, a := range listOf(gv["enable"]) {
				s.add(c.d("govet", a, false))
			}
		}
	}
	for _, k := range []string{"staticcheck", "stylecheck", "gosimple"} {
		if sc, ok := settings[k].(map[string]any); ok {
			staticChecks(s, c, listOf(sc["checks"]))
		}
	}
	// complexity/size thresholds: gocognit/gocyclo/nestif min-complexity, cyclop max-complexity,
	// funlen lines/statements (crev metric rules read them as params, e.g. "gocognit:*.min-complexity")
	for _, k := range []string{"gocognit", "gocyclo", "cyclop", "nestif", "funlen", "maintidx"} {
		if ls, ok := settings[k].(map[string]any); ok {
			d := c.d(k, "*", false)
			d.Params = ls
			s.add(d)
		}
	}
	if gs, ok := settings["gosec"].(map[string]any); ok {
		for _, g := range listOf(gs["excludes"]) {
			s.add(c.d("gosec", g, true))
		}
	}
	if rv, ok := settings["revive"].(map[string]any); ok {
		if rules, ok := rv["rules"].([]any); ok {
			for _, r := range rules {
				if rm, ok := r.(map[string]any); ok && rm["disabled"] == true {
					s.add(c.d("revive", toString(rm["name"]), true))
				}
			}
		}
	}
	var excl []any
	if is, ok := m["issues"].(map[string]any); ok {
		excl, _ = is["exclude-rules"].([]any)
	}
	if ex, ok := linters["exclusions"].(map[string]any); ok {
		if r, ok := ex["rules"].([]any); ok {
			excl = append(excl, r...)
		}
		for _, p := range listOf(ex["paths"]) {
			for _, t := range []string{"govet", "staticcheck", "gosec", "revive"} {
				d := c.d(t, "*", true)
				d.Paths = []string{p}
				s.add(d)
			}
		}
	}
	for _, e := range excl {
		em, ok := e.(map[string]any)
		if !ok || em["text"] != nil || em["source"] != nil {
			continue // text/source filters cannot be mapped to a crev rule safely
		}
		var paths []string
		if p := toString(em["path"]); p != "" {
			paths = []string{p}
		}
		for _, l := range listOf(em["linters"]) {
			d := c.d("", "*", true)
			d.Paths = paths
			off(l, d)
		}
	}
	return nil
}

// linterTools maps a golangci linter name to crev xref tools.
func linterTools(l string) []string {
	switch l {
	case "govet", "vet", "vetshadow":
		return []string{"govet"}
	case "staticcheck", "gosimple", "stylecheck":
		return []string{"staticcheck"}
	case "gosec":
		return []string{"gosec"}
	case "revive", "golint":
		return []string{"revive"}
	}
	return nil
}

func staticChecks(s *Set, c ctx, checks []string) {
	for _, ch := range checks {
		if id, ok := strings.CutPrefix(ch, "-"); ok {
			if prefix, ok := strings.CutSuffix(id, "*"); ok {
				id = prefix
				d := c.d("staticcheck", id, true)
				d.ID = id + "*"
				s.add(d)
				continue
			}
			s.add(c.d("staticcheck", id, true))
		}
	}
}

func staticcheckConf(s *Set, c ctx, b []byte) error {
	m, err := parseTOML(string(b))
	if err != nil {
		return err
	}
	staticChecks(s, c, listOf(m["checks"]))
	return nil
}

func reviveTOML(s *Set, c ctx, b []byte) error {
	m, err := parseTOML(string(b))
	if err != nil {
		return err
	}
	if rules, ok := m["rule"].(map[string]any); ok {
		for name, v := range rules {
			if rm, ok := v.(map[string]any); ok && rm["Disabled"] == true {
				s.add(c.d("revive", name, true))
			}
		}
	}
	return nil
}

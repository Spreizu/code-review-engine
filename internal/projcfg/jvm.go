package projcfg

import (
	"encoding/xml"
	"maps"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

func init() {
	register(tsconfig, "tsconfig.json", "tsconfig.*.json", "jsconfig.json")
	register(checkstyleXML, "checkstyle.xml", "checkstyle-config.xml", "google_checks.xml", "sun_checks.xml")
	register(checkstyleSuppressions, "checkstyle-suppressions.xml", "suppressions.xml")
	register(pmdXML, "pmd.xml", "pmd-ruleset.xml", "ruleset.xml", "pmd-rules.xml")
	register(spotbugsXML, "spotbugs-exclude.xml", "findbugs-exclude.xml", "spotbugs-excludes.xml")
	register(errorProne, "pom.xml", "build.gradle", "build.gradle.kts")
	register(detektYML, "detekt.yml", "detekt.yaml", "detekt-config.yml")
	register(editorconfig, ".editorconfig")
}

// tsconfig: compilerOptions (following relative `extends` chains) become tsconfig:<option>
// directives. An option explicitly relaxed (allow*/skip*/suppress* = true, any other strictness
// flag = false) is "off" for the equivalent crev rules; strict values are recorded as "on".
func tsconfig(s *Set, c ctx, b []byte) error {
	opts := map[string]any{}
	seen := map[string]bool{}
	var load func(path string, b []byte) error
	load = func(path string, b []byte) error {
		if seen[path] {
			return nil
		}
		seen[path] = true
		m, err := loose(b)
		if err != nil {
			return err
		}
		for _, ext := range listOf(m["extends"]) {
			if strings.HasPrefix(ext, ".") {
				p := filepath.Join(filepath.Dir(path), ext)
				if !strings.HasSuffix(p, ".json") {
					p += ".json"
				}
				if eb, err := os.ReadFile(p); err == nil {
					_ = load(p, eb)
				}
			}
		}
		if co, ok := m["compilerOptions"].(map[string]any); ok {
			maps.Copy(opts, co)
		}
		return nil
	}
	if err := load(filepath.Join(c.root, c.rel), b); err != nil {
		return err
	}
	for k, v := range opts {
		bv, ok := v.(bool)
		if !ok {
			d := c.d("tsconfig", k, false)
			d.Params = map[string]any{"value": v}
			s.add(d)
			continue
		}
		relaxed := !bv
		if strings.HasPrefix(k, "allow") || strings.HasPrefix(k, "skip") || strings.HasPrefix(k, "suppress") {
			relaxed = bv
		}
		s.add(c.d("tsconfig", k, relaxed))
	}
	return nil
}

// moduleCtx re-roots configs that conventionally live in a config dir (config/checkstyle/,
// config/detekt/, etc/, .config/) to the module that contains that dir.
func moduleCtx(c ctx) ctx {
	parts := strings.Split(c.dir, "/")
	for i, p := range parts {
		if p == "config" || p == ".config" || p == "etc" || p == "quality" || p == "codequality" || p == "gradle" {
			c.dir = strings.Join(parts[:i], "/")
			return c
		}
	}
	return c
}

type xmlNode struct {
	XMLName xml.Name
	Attrs   []xml.Attr `xml:",any,attr"`
	Text    string     `xml:",chardata"`
	Nodes   []xmlNode  `xml:",any"`
}

func (n *xmlNode) attr(name string) string {
	for _, a := range n.Attrs {
		if a.Name.Local == name {
			return a.Value
		}
	}
	return ""
}

func (n *xmlNode) walk(fn func(*xmlNode)) {
	fn(n)
	for i := range n.Nodes {
		n.Nodes[i].walk(fn)
	}
}

func parseXML(b []byte) (*xmlNode, error) {
	var n xmlNode
	d := xml.NewDecoder(strings.NewReader(string(b)))
	d.Strict = false
	d.Entity = xml.HTMLEntity
	if err := d.Decode(&n); err != nil {
		return nil, err
	}
	return &n, nil
}

// checkstyle: <module name="X"><property name="severity" value="ignore"/></module>.
func checkstyleXML(s *Set, c ctx, b []byte) error {
	c = moduleCtx(c)
	root, err := parseXML(b)
	if err != nil {
		return err
	}
	root.walk(func(n *xmlNode) {
		if n.XMLName.Local != "module" {
			return
		}
		name := n.attr("name")
		params := map[string]any{}
		off := false
		for _, p := range n.Nodes {
			if p.XMLName.Local == "property" {
				if p.attr("name") == "severity" && p.attr("value") == "ignore" {
					off = true
				} else if p.attr("name") != "" {
					params[p.attr("name")] = p.attr("value")
				}
			}
		}
		if name == "" || name == "Checker" || name == "TreeWalker" {
			return
		}
		name = strings.TrimSuffix(name, "Check")
		d := c.d("checkstyle", name, off)
		if len(params) > 0 {
			d.Params = params
		}
		s.add(d)
	})
	return nil
}

// checkstyle suppressions: <suppress checks="Regex" files="Regex"/>.
func checkstyleSuppressions(s *Set, c ctx, b []byte) error {
	root, err := parseXML(b)
	if err != nil {
		return err
	}
	if root.XMLName.Local != "suppressions" {
		return nil
	}
	for _, n := range root.Nodes {
		if n.XMLName.Local != "suppress" || n.attr("checks") == "" {
			continue
		}
		re, err := regexp.Compile("^(?:" + n.attr("checks") + ")$")
		if err != nil {
			continue
		}
		d := c.d("checkstyle", "re:"+re.String(), true)
		d.Base = ""
		if f := n.attr("files"); f != "" {
			d.Paths = []string{f}
		}
		s.add(d)
	}
	return nil
}

// pmd: <rule ref="category/java/x.xml"><exclude name="Rule"/></rule> and <rule ref=".../Rule">
// with <priority>5</priority> are treated as off; <rule ref=".../Rule"> is on.
func pmdXML(s *Set, c ctx, b []byte) error {
	c = moduleCtx(c)
	root, err := parseXML(b)
	if err != nil {
		return err
	}
	if root.XMLName.Local != "ruleset" {
		return nil
	}
	for _, n := range root.Nodes {
		if n.XMLName.Local == "exclude-pattern" {
			for _, t := range []string{"pmd"} {
				d := c.d(t, "*", true)
				d.Paths = []string{strings.TrimSpace(n.Text)}
				s.add(d)
			}
		}
		if n.XMLName.Local != "rule" {
			continue
		}
		ref := n.attr("ref")
		for _, ex := range n.Nodes {
			if ex.XMLName.Local == "exclude" && ex.attr("name") != "" {
				s.add(c.d("pmd", ex.attr("name"), true))
			}
		}
		if i := strings.LastIndex(ref, "/"); i >= 0 && !strings.HasSuffix(ref, ".xml") {
			s.add(c.d("pmd", ref[i+1:], false))
		}
	}
	return nil
}

// spotbugs exclude filter: <Match><Bug pattern="A,B"/>[<Source name="regex"/>]</Match>.
func spotbugsXML(s *Set, c ctx, b []byte) error {
	c = moduleCtx(c)
	root, err := parseXML(b)
	if err != nil {
		return err
	}
	for _, m := range root.Nodes {
		if m.XMLName.Local != "Match" {
			continue
		}
		var bugs, paths []string
		for _, n := range m.Nodes {
			switch n.XMLName.Local {
			case "Bug":
				bugs = append(bugs, splitList(n.attr("pattern"))...)
			case "Source":
				if v := n.attr("name"); v != "" {
					paths = append(paths, strings.TrimPrefix(v, "~"))
				}
			case "Class", "Package":
				paths = nil // class-scoped excludes cannot be mapped to paths; skip the match
				bugs = nil
			}
		}
		for _, bug := range bugs {
			d := c.d("spotbugs", bug, true)
			d.Base = ""
			d.Paths = paths
			s.add(d)
		}
	}
	return nil
}

var epFlag = regexp.MustCompile(`-Xep:([A-Za-z0-9_]+)(?::(OFF|WARN|ERROR))?`)

// errorProne: -Xep:Check:OFF compiler args in Maven/Gradle builds.
func errorProne(s *Set, c ctx, b []byte) error {
	for _, m := range epFlag.FindAllStringSubmatch(string(b), -1) {
		s.add(c.d("errorprone", m[1], m[2] == "OFF"))
	}
	return nil
}

// detekt: RuleSet: Rule: {active: false, excludes: [...], <options>}.
func detektYML(s *Set, c ctx, b []byte) error {
	c = moduleCtx(c)
	m, err := loose(b)
	if err != nil {
		return err
	}
	for set, v := range m {
		rs, ok := v.(map[string]any)
		if !ok || set == "config" || set == "build" || set == "processors" || set == "console-reports" || set == "output-reports" {
			continue
		}
		setOff := rs["active"] == false
		for rule, rv := range rs {
			r, ok := rv.(map[string]any)
			if !ok {
				continue
			}
			d := c.d("detekt", rule, setOff || r["active"] == false)
			d.Ignore = listOf(r["excludes"])
			params := map[string]any{}
			for k, pv := range r {
				if k != "active" && k != "excludes" && k != "includes" {
					params[k] = pv
				}
			}
			if len(params) > 0 {
				d.Params = params
			}
			s.add(d)
		}
	}
	return nil
}

// editorconfig: sections are globs; properties map to editorconfig:<prop> (max_line_length,
// insert_final_newline, trim_trailing_whitespace, end_of_line) plus ktlint rule switches
// (ktlint_standard_<rule> = disabled, ktlint_standard = disabled).
func editorconfig(s *Set, c ctx, b []byte) error {
	var glob string
	for _, line := range strings.Split(string(b), "\n") {
		t := strings.TrimSpace(line)
		if t == "" || t[0] == '#' || t[0] == ';' {
			continue
		}
		if t[0] == '[' && strings.HasSuffix(t, "]") {
			glob = t[1 : len(t)-1]
			continue
		}
		k, v, ok := strings.Cut(t, "=")
		if !ok || glob == "" {
			continue
		}
		k, v = strings.ToLower(strings.TrimSpace(k)), strings.TrimSpace(v)
		files := []string{glob}
		if !strings.Contains(glob, "/") {
			files = []string{"**/" + glob}
		}
		switch {
		case strings.HasPrefix(k, "ktlint_") && (v == "disabled" || v == "enabled"):
			id := strings.TrimPrefix(k, "ktlint_")
			if id == "standard" || id == "experimental" {
				id += ":*"
			} else if i := strings.Index(id, "_"); i > 0 {
				id = id[:i] + ":" + strings.ReplaceAll(id[i+1:], "_", "-")
			}
			d := c.d("ktlint", id, v == "disabled")
			d.Files = files
			s.add(d)
		case k == "max_line_length" || k == "insert_final_newline" || k == "trim_trailing_whitespace" || k == "end_of_line":
			d := c.d("editorconfig", k, v == "off" || v == "false" || v == "unset")
			d.Files = files
			d.Params = map[string]any{"max": v, "value": v}
			s.add(d)
			if k == "max_line_length" {
				kd := c.d("ktlint", "standard:max-line-length", v == "off")
				kd.Files, kd.Params = files, map[string]any{"max": v}
				s.add(kd)
			}
		}
	}
	return nil
}

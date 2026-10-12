package projcfg

import (
	"regexp"
	"strings"
)

func init() {
	register(phpstanNeon, "phpstan.neon", "phpstan.neon.dist", "phpstan.dist.neon")
	register(psalmXML, "psalm.xml", "psalm.xml.dist")
	register(phpcsXML, "phpcs.xml", ".phpcs.xml", "phpcs.xml.dist", ".phpcs.xml.dist", "ruleset.phpcs.xml")
	register(hadolintYAML, ".hadolint.yaml", ".hadolint.yml", "hadolint.yaml")
	register(tflintHCL, ".tflint.hcl")
	register(yamllintConf, ".yamllint", ".yamllint.yaml", ".yamllint.yml")
	register(bufYAML, "buf.yaml")
	register(checkovYAML, ".checkov.yaml", ".checkov.yml")
}

// phpstan: parameters.ignoreErrors entries with an identifier (optionally path/paths).
func phpstanNeon(s *Set, c ctx, b []byte) error {
	m, err := loose([]byte(strings.ReplaceAll(string(b), "\t", "    ")))
	if err != nil {
		return err
	}
	params, _ := m["parameters"].(map[string]any)
	ign, _ := params["ignoreErrors"].([]any)
	for _, e := range ign {
		em, ok := e.(map[string]any)
		if !ok {
			continue
		}
		for _, id := range append(listOf(em["identifier"]), listOf(em["identifiers"])...) {
			d := c.d("phpstan", id, true)
			d.Files = append(listOf(em["path"]), listOf(em["paths"])...)
			s.add(d)
		}
	}
	return nil
}

// psalm: <issueHandlers><IssueName errorLevel="suppress"/> (optionally <errorLevel type="suppress"><directory|file name=.../>).
func psalmXML(s *Set, c ctx, b []byte) error {
	root, err := parseXML(b)
	if err != nil {
		return err
	}
	root.walk(func(n *xmlNode) {
		if n.XMLName.Local != "issueHandlers" {
			return
		}
		for _, iss := range n.Nodes {
			name := iss.XMLName.Local
			if iss.attr("errorLevel") == "suppress" {
				s.add(c.d("psalm", name, true))
			}
			for _, lvl := range iss.Nodes {
				if lvl.XMLName.Local != "errorLevel" || lvl.attr("type") != "suppress" {
					continue
				}
				d := c.d("psalm", name, true)
				for _, f := range lvl.Nodes {
					if v := f.attr("name"); v != "" {
						if f.XMLName.Local == "directory" {
							v = strings.TrimSuffix(v, "/") + "/**"
						}
						d.Files = append(d.Files, v)
					}
				}
				s.add(d)
			}
		}
	})
	return nil
}

// phpcs: <rule ref="Std.Cat.Sniff"><severity>0</severity></rule>, <rule ref="Std"><exclude name="Std.Cat.Sniff"/></rule>,
// <rule ref="X"><exclude-pattern>glob</exclude-pattern></rule>, global <exclude-pattern>.
func phpcsXML(s *Set, c ctx, b []byte) error {
	root, err := parseXML(b)
	if err != nil {
		return err
	}
	if root.XMLName.Local != "ruleset" {
		return nil
	}
	for _, n := range root.Nodes {
		if n.XMLName.Local != "rule" {
			continue
		}
		ref := n.attr("ref")
		var excl []string
		sev0 := false
		for _, ch := range n.Nodes {
			switch ch.XMLName.Local {
			case "exclude":
				s.add(c.d("phpcs", ch.attr("name"), true))
			case "severity":
				sev0 = strings.TrimSpace(ch.Text) == "0"
			case "exclude-pattern":
				excl = append(excl, strings.TrimSpace(ch.Text))
			}
		}
		if ref == "" || strings.Contains(ref, "/") {
			continue
		}
		if sev0 {
			s.add(c.d("phpcs", ref, true))
		}
		if len(excl) > 0 {
			d := c.d("phpcs", ref, true)
			d.Files = excl
			s.add(d)
		}
	}
	return nil
}

// hadolint: ignored: [DLxxxx] (and override levels kept as params).
func hadolintYAML(s *Set, c ctx, b []byte) error {
	m, err := loose(b)
	if err != nil {
		return err
	}
	for _, id := range listOf(m["ignored"]) {
		s.add(c.d("hadolint", id, true))
	}
	return nil
}

var tflintRule = regexp.MustCompile(`(?s)rule\s+"([a-z0-9_]+)"\s*\{([^}]*)\}`)
var tflintEnabled = regexp.MustCompile(`enabled\s*=\s*(true|false)`)

// tflint: rule "name" { enabled = false }.
func tflintHCL(s *Set, c ctx, b []byte) error {
	for _, m := range tflintRule.FindAllStringSubmatch(string(b), -1) {
		if e := tflintEnabled.FindStringSubmatch(m[2]); e != nil {
			s.add(c.d("tflint", m[1], e[1] == "false"))
		}
	}
	return nil
}

// yamllint: rules: {name: disable | enable | {level, max, ignore, ...}}, top-level ignore.
func yamllintConf(s *Set, c ctx, b []byte) error {
	m, err := loose(b)
	if err != nil {
		return err
	}
	var globalIgnore []string
	if ig, ok := m["ignore"].(string); ok {
		globalIgnore = gitignoreLines(ig)
	}
	globalIgnore = append(globalIgnore, listOf(m["ignore"])...)
	if len(globalIgnore) > 0 {
		d := c.d("yamllint", "*", true)
		d.Files = globalIgnore
		s.add(d)
	}
	rules, _ := m["rules"].(map[string]any)
	for name, v := range rules {
		switch x := v.(type) {
		case string:
			s.add(c.d("yamllint", name, x == "disable"))
		case bool:
			s.add(c.d("yamllint", name, !x))
		case map[string]any:
			d := c.d("yamllint", name, false)
			params := map[string]any{}
			for k, pv := range x {
				if k != "ignore" && k != "level" {
					params[k] = pv
				}
			}
			d.Params = params
			s.add(d)
			if ig, ok := x["ignore"].(string); ok {
				id := c.d("yamllint", name, true)
				id.Files = gitignoreLines(ig)
				s.add(id)
			} else if l := listOf(x["ignore"]); len(l) > 0 {
				id := c.d("yamllint", name, true)
				id.Files = l
				s.add(id)
			}
		}
	}
	return nil
}

func gitignoreLines(s string) []string {
	var out []string
	for _, l := range strings.Split(s, "\n") {
		if l = strings.TrimSpace(l); l != "" && !strings.HasPrefix(l, "#") {
			out = append(out, l)
		}
	}
	return out
}

// buf.yaml (v1/v2): lint.except, lint.ignore (paths), lint.ignore_only {RULE: [paths]}.
func bufYAML(s *Set, c ctx, b []byte) error {
	m, err := loose(b)
	if err != nil {
		return err
	}
	lint, _ := m["lint"].(map[string]any)
	for _, id := range listOf(lint["except"]) {
		s.add(c.d("buf", id, true))
	}
	if ig := listOf(lint["ignore"]); len(ig) > 0 {
		d := c.d("buf", "*", true)
		for _, p := range ig {
			d.Files = append(d.Files, strings.TrimSuffix(p, "/"), strings.TrimSuffix(p, "/")+"/**")
		}
		s.add(d)
	}
	if io, ok := lint["ignore_only"].(map[string]any); ok {
		for id, paths := range io {
			d := c.d("buf", id, true)
			for _, p := range listOf(paths) {
				d.Files = append(d.Files, strings.TrimSuffix(p, "/"), strings.TrimSuffix(p, "/")+"/**")
			}
			s.add(d)
		}
	}
	return nil
}

// checkov: skip-check: [CKV_...].
func checkovYAML(s *Set, c ctx, b []byte) error {
	m, err := loose(b)
	if err != nil {
		return err
	}
	for _, id := range listOf(m["skip-check"]) {
		s.add(c.d("checkov", id, true))
	}
	return nil
}

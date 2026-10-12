package projcfg

import "strings"

func init() {
	register(pyproject, "pyproject.toml")
	register(ruffTOML, "ruff.toml", ".ruff.toml")
	register(iniPython, "setup.cfg", "tox.ini", ".flake8", ".pylintrc", "pylintrc", "mypy.ini", ".mypy.ini", ".bandit")
}

func pyproject(s *Set, c ctx, b []byte) error {
	m, err := parseTOML(string(b))
	if err != nil {
		return err
	}
	tool, _ := m["tool"].(map[string]any)
	if r, ok := tool["ruff"].(map[string]any); ok {
		ruffConfig(s, c, r)
	}
	if p, ok := tool["pylint"].(map[string]any); ok {
		for k, v := range p {
			if sec, ok := v.(map[string]any); ok && strings.EqualFold(strings.ReplaceAll(k, "_", " "), "messages control") {
				for _, id := range listOf(sec["disable"]) {
					s.add(c.d("pylint", id, true))
				}
			}
			if sec, ok := v.(map[string]any); ok && strings.EqualFold(k, "design") {
				pylintDesign(s, c, func(o string) any { return sec[o] })
			}
			if k == "format" {
				if sec, ok := v.(map[string]any); ok && sec["max-line-length"] != nil {
					d := c.d("pylint", "line-too-long", false)
					d.Params = map[string]any{"max": sec["max-line-length"]}
					s.add(d)
				}
			}
		}
	}
	if my, ok := tool["mypy"].(map[string]any); ok {
		for _, id := range listOf(my["disable_error_code"]) {
			s.add(c.d("mypy", id, true))
		}
	}
	if bd, ok := tool["bandit"].(map[string]any); ok {
		for _, id := range listOf(bd["skips"]) {
			s.add(c.d("bandit", id, true))
		}
	}
	if fl, ok := tool["flake8"].(map[string]any); ok { // flake8-pyproject / Flake8-pyproject plugins
		sec := map[string]string{}
		for k, v := range fl {
			sec[k] = strings.Join(listOf(v), ",")
		}
		flake8Section(s, c, sec)
	}
	return nil
}

func listOf(v any) []string {
	switch x := v.(type) {
	case string:
		return splitList(x)
	case []any:
		var out []string
		for _, e := range x {
			out = append(out, toString(e))
		}
		return out
	case float64:
		return []string{toString(x)}
	}
	return nil
}

func ruffTOML(s *Set, c ctx, b []byte) error {
	m, err := parseTOML(string(b))
	if err != nil {
		return err
	}
	ruffConfig(s, c, m)
	return nil
}

func ruffConfig(s *Set, c ctx, r map[string]any) {
	sections := []map[string]any{r}
	if l, ok := r["lint"].(map[string]any); ok {
		sections = append(sections, l)
	}
	for _, sec := range sections {
		for _, k := range []string{"ignore", "extend-ignore"} {
			for _, id := range listOf(sec[k]) {
				s.add(c.d("ruff", id, true))
			}
		}
		for _, k := range []string{"per-file-ignores", "extend-per-file-ignores"} {
			if pf, ok := sec[k].(map[string]any); ok {
				for g, ids := range pf {
					neg := strings.HasPrefix(g, "!")
					for _, id := range listOf(ids) {
						d := c.d("ruff", id, true)
						if neg {
							d.Ignore = []string{strings.TrimPrefix(g, "!")}
						} else {
							d.Files = []string{g}
						}
						s.add(d)
					}
				}
			}
		}
	}
	for _, sec := range sections {
		if mc, ok := sec["mccabe"].(map[string]any); ok && mc["max-complexity"] != nil {
			d := c.d("ruff", "C901", false)
			d.Params = map[string]any{"max": mc["max-complexity"]}
			s.add(d)
		}
		if pl, ok := sec["pylint"].(map[string]any); ok {
			for opt, code := range ruffPylintLimits {
				if v, ok := pl[opt]; ok {
					d := c.d("ruff", code, false)
					d.Params = map[string]any{"max": v}
					s.add(d)
				}
			}
		}
	}
	if ll, ok := r["line-length"]; ok {
		d := c.d("ruff", "E501", false)
		d.Params = map[string]any{"max": ll}
		s.add(d)
	}
}

func iniPython(s *Set, c ctx, b []byte) error {
	ini := parseINI(string(b))
	for name, sec := range ini {
		switch name {
		case "flake8":
			flake8Section(s, c, sec)
		case "messages control", "pylint.messages control", "pylint.messages_control":
			for _, id := range splitList(sec["disable"]) {
				s.add(c.d("pylint", id, true))
			}
		case "format", "pylint.format":
			if v := sec["max-line-length"]; v != "" {
				d := c.d("pylint", "line-too-long", false)
				d.Params = map[string]any{"max": v}
				s.add(d)
			}
		case "design", "pylint.design":
			pylintDesign(s, c, func(o string) any {
				if v, ok := sec[o]; ok && v != "" {
					return v
				}
				return nil
			})
		case "mypy":
			for _, id := range splitList(sec["disable_error_code"]) {
				s.add(c.d("mypy", id, true))
			}
		case "bandit":
			for _, id := range splitList(sec["skips"]) {
				s.add(c.d("bandit", id, true))
			}
		}
	}
	return nil
}

func flake8Section(s *Set, c ctx, sec map[string]string) {
	for _, k := range []string{"ignore", "extend-ignore", "extend_ignore"} {
		for _, id := range splitList(sec[k]) {
			s.add(c.d("flake8", id, true))
		}
	}
	for _, k := range []string{"per-file-ignores", "per_file_ignores"} {
		for _, line := range strings.FieldsFunc(sec[k], func(r rune) bool { return r == '\n' }) {
			g, ids, ok := strings.Cut(line, ":")
			if !ok {
				continue
			}
			for _, id := range splitList(ids) {
				d := c.d("flake8", id, true)
				d.Files = []string{strings.TrimSpace(g)}
				s.add(d)
			}
		}
	}
	if v := sec["max-line-length"]; v != "" {
		d := c.d("flake8", "E501", false)
		d.Params = map[string]any{"max": v}
		s.add(d)
	}
}

// ruffPylintLimits maps [lint.pylint] limit options to the ruff codes that use them.
var ruffPylintLimits = map[string]string{
	"max-args": "PLR0913", "max-positional-args": "PLR0917", "max-returns": "PLR0911", "max-branches": "PLR0912",
	"max-statements": "PLR0915", "max-nested-blocks": "PLR1702", "max-bool-expr": "PLR0916",
}

// pylintLimits maps pylint [DESIGN] options to the messages that use them.
var pylintLimits = map[string]string{
	"max-args": "too-many-arguments", "max-returns": "too-many-return-statements", "max-branches": "too-many-branches",
	"max-statements": "too-many-statements", "max-nested-blocks": "too-many-nested-blocks", "max-bool-expr": "too-many-boolean-expressions",
}

func pylintDesign(s *Set, c ctx, get func(string) any) {
	for opt, msg := range pylintLimits {
		if v := get(opt); v != nil {
			d := c.d("pylint", msg, false)
			d.Params = map[string]any{"max": v}
			s.add(d)
		}
	}
}

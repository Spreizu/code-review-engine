package projcfg

import (
	"fmt"
	"maps"
	"regexp"
	"slices"
	"strings"
)

// inlineSup is one suppression comment/annotation with the line range it covers (1-based, inclusive).
type inlineSup struct {
	tools    []string // xref tools covered
	ids      []string // nil = every rule of those tools
	from, to int
	line     int
	text     string
	crev     bool // crev-ignore (ids are crev rule ids)
}

// FileInline holds the suppressions found in one file.
type FileInline struct{ sups []inlineSup }

var eslintFamily = []string{"eslint", "typescript-eslint", "eslint-plugin-vue", "graphql-eslint", "react-hooks", "angular-eslint", "react",
	"oxlint", "unicorn", "jsx-a11y", "import", "jest", "vitest", "promise", "node", "nextjs", "jsdoc", "react-perf"}
var jvmTools = []string{"checkstyle", "pmd", "errorprone", "spotbugs", "detekt", "ktlint"}

var (
	reESLint      = regexp.MustCompile(`(?:es|ox)lint-(disable-next-line|disable-line|disable|enable)\b([^*\n]*?)(?:\s--.*?)?\s*(?:\*/|$)`)
	reNolint      = regexp.MustCompile(`//\s?nolint(?::([\w,-]+))?`)
	reLintIgnore  = regexp.MustCompile(`//lint:(ignore|file-ignore)\s+([\w,]+)`)
	reNosec       = regexp.MustCompile(`#\s?nosec\b((?:\s+[GB]\d+)*)`)
	reNoqa        = regexp.MustCompile(`#\s*noqa(?::\s*([A-Z]+[0-9]*(?:[\s,]+[A-Z]+[0-9]*)*))?`)
	reFileNoqa    = regexp.MustCompile(`^#\s*(ruff|flake8):\s*noqa(?::\s*([A-Z0-9, ]+))?`)
	rePylint      = regexp.MustCompile(`#\s*pylint:\s*disable(-next)?=([\w,\- ]+)`)
	reTypeIgnore  = regexp.MustCompile(`#\s*type:\s*ignore(?:\[([\w,\- ]+)\])?`)
	reSuppress    = regexp.MustCompile(`@(?:java\.lang\.)?(SuppressWarnings|Suppress|SuppressFBWarnings|SuppressLint)\s*\(([^)]*)\)`)
	reQuoted      = regexp.MustCompile(`"([^"]+)"`)
	rePhpcs       = regexp.MustCompile(`phpcs:(ignoreFile|ignore|disable|enable)\b([^\n*]*)`)
	rePhpstan     = regexp.MustCompile(`@phpstan-ignore(-next-line|-line)?\b([\w.,\s-]*)`)
	rePsalm       = regexp.MustCompile(`@psalm-suppress\s+([\w, ]+)`)
	reHadolint    = regexp.MustCompile(`#\s*hadolint\s+(global\s+)?ignore=([\w,]+)`)
	reTflint      = regexp.MustCompile(`#\s*tflint-ignore:\s*([\w, ]+)`)
	reCheckov     = regexp.MustCompile(`#\s*checkov:skip=([A-Z0-9_]+)`)
	reYamllint    = regexp.MustCompile(`#\s*yamllint\s+(disable-line|disable-file|disable|enable)((?:\s+rule:[\w-]+)*)`)
	reBuf         = regexp.MustCompile(`//\s*buf:lint:ignore\s+([A-Z0-9_]+)`)
	reDockerCheck = regexp.MustCompile(`^#\s*check\s*=\s*skip\s*=\s*([\w,]+)`)
	reCrev        = regexp.MustCompile(`crev-ignore(-next-line|-file)?\s+([A-Za-z0-9_\-, ]+|all)`)
)

func fields(s string) []string {
	return strings.FieldsFunc(s, func(r rune) bool { return r == ',' || r == ' ' || r == '\t' })
}

func commentOnly(line string) bool {
	t := strings.TrimSpace(line)
	return strings.HasPrefix(t, "//") || strings.HasPrefix(t, "#") || strings.HasPrefix(t, "/*") || strings.HasPrefix(t, "*") || strings.HasPrefix(t, "<!--") || strings.HasPrefix(t, "{{!--")
}

// declExtent returns the last line of the declaration starting at line i (0-based): up to the
// first ';' before any '{', or the matching close brace.
func declExtent(lines []string, i int) int { return declExtentFrom(lines, i, 0) }

// declExtentFrom is declExtent starting at byte col of line i (skips e.g. the annotation itself).
func declExtentFrom(lines []string, i, col int) int {
	depth, opened := 0, false
	for j := i; j < len(lines) && j < i+5000; j++ {
		l := lines[j]
		if j == i && col <= len(l) {
			l = l[col:]
		}
		for _, ch := range l {
			switch ch {
			case '{':
				depth++
				opened = true
			case '}':
				depth--
				if opened && depth <= 0 {
					return j
				}
			case ';':
				if !opened {
					return j
				}
			}
		}
		if !opened && j > i+3 {
			return i + 1
		}
	}
	return len(lines) - 1
}

func indent(s string) int { return len(s) - len(strings.TrimLeft(s, " \t")) }

// ParseInline extracts suppression comments from a file's source.
func ParseInline(rel string, src []byte) *FileInline {
	lines := strings.Split(string(src), "\n")
	fi := &FileInline{}
	n := len(lines)
	add := func(tools, ids []string, from, to, line int, text string) {
		if to < from {
			to = from
		}
		fi.sups = append(fi.sups, inlineSup{tools: tools, ids: ids, from: from + 1, to: to + 1, line: line + 1, text: strings.TrimSpace(text)})
	}
	nextOrSame := func(i int) (int, int) {
		if commentOnly(lines[i]) {
			return i + 1, i + 1
		}
		return i, i
	}
	type open struct {
		ids  []string
		line int
	}
	eslintOpen := map[string]open{} // "" = all
	phpcsOpen := map[string]open{}
	yamlOpen := map[string]open{}
	isDocker := strings.HasSuffix(strings.ToLower(rel), "dockerfile") || strings.Contains(strings.ToLower(rel), "dockerfile.") || strings.HasSuffix(rel, ".dockerfile")
	for i, l := range lines {
		if !strings.ContainsAny(l, "/#@*-") {
			continue
		}
		// ESLint
		for _, m := range reESLint.FindAllStringSubmatch(l, -1) {
			ids := fields(m[2])
			if strings.HasPrefix(m[0], "oxlint-") {
				ids = oxlintInlineIDs(ids)
			}
			switch m[1] {
			case "disable-next-line":
				add(eslintFamily, nilIfEmpty(ids), i+1, i+1, i, m[0])
			case "disable-line":
				add(eslintFamily, nilIfEmpty(ids), i, i, i, m[0])
			case "disable":
				if len(ids) == 0 {
					eslintOpen[""] = open{nil, i}
				}
				for _, id := range ids {
					eslintOpen[id] = open{[]string{id}, i}
				}
			case "enable":
				keys := ids
				if len(ids) == 0 {
					keys = slices.Collect(maps.Keys(eslintOpen))
				}
				for _, k := range keys {
					if o, ok := eslintOpen[k]; ok {
						add(eslintFamily, o.ids, o.line, i, o.line, "eslint-disable "+k)
						delete(eslintOpen, k)
					}
				}
			}
		}
		// Go
		if m := reNolint.FindStringSubmatch(l); m != nil {
			from, to := nextOrSame(i)
			if commentOnly(l) {
				to = declExtent(lines, i+1)
			}
			tools := []string{"govet", "staticcheck", "gosec", "revive"}
			if m[1] != "" && m[1] != "all" {
				tools = nil
				for _, ln := range fields(m[1]) {
					tools = append(tools, linterTools(ln)...)
				}
			}
			if len(tools) > 0 {
				add(tools, nil, from, to, i, m[0])
			}
		}
		if m := reLintIgnore.FindStringSubmatch(l); m != nil {
			if m[1] == "file-ignore" {
				add([]string{"staticcheck"}, fields(m[2]), 0, n-1, i, m[0])
			} else {
				add([]string{"staticcheck"}, fields(m[2]), i+1, declExtent(lines, i+1), i, m[0])
			}
		}
		if m := reNosec.FindStringSubmatch(l); m != nil {
			from, to := nextOrSame(i)
			var g, b []string
			for _, id := range fields(m[1]) {
				if id[0] == 'G' {
					g = append(g, id)
				} else {
					b = append(b, id)
				}
			}
			if len(m[1]) == 0 || len(g) > 0 {
				add([]string{"gosec"}, nilIfEmpty(g), from, to, i, m[0])
			}
			if len(m[1]) == 0 || len(b) > 0 {
				add([]string{"bandit"}, nilIfEmpty(b), from, to, i, m[0])
			}
		}
		// Python
		if m := reFileNoqa.FindStringSubmatch(strings.TrimSpace(l)); m != nil {
			add([]string{"ruff", "flake8"}, nilIfEmpty(fields(m[2])), 0, n-1, i, m[0])
		} else if m := reNoqa.FindStringSubmatch(l); m != nil {
			add([]string{"ruff", "flake8", "pylint"}, nilIfEmpty(fields(m[1])), i, i, i, m[0])
		}
		if m := rePylint.FindStringSubmatch(l); m != nil {
			ids := fields(m[2])
			switch {
			case m[1] == "-next":
				add([]string{"pylint"}, ids, i+1, i+1, i, m[0])
			case commentOnly(l):
				end := n - 1
				for j := i + 1; j < n; j++ {
					if strings.TrimSpace(lines[j]) != "" && indent(lines[j]) < indent(l) {
						end = j - 1
						break
					}
				}
				add([]string{"pylint"}, ids, i, end, i, m[0])
			default:
				add([]string{"pylint"}, ids, i, i, i, m[0])
			}
		}
		if m := reTypeIgnore.FindStringSubmatch(l); m != nil {
			add([]string{"mypy"}, nilIfEmpty(fields(m[1])), i, i, i, m[0])
		}
		// JVM annotations
		for _, loc := range reSuppress.FindAllStringSubmatchIndex(l, -1) {
			m := []string{l[loc[0]:loc[1]], l[loc[2]:loc[3]], l[loc[4]:loc[5]]}
			to := declExtentFrom(lines, i, loc[1])
			for _, q := range reQuoted.FindAllStringSubmatch(m[2], -1) {
				v := q[1]
				switch {
				case v == "all" || v == "ALL":
					add(jvmTools, nil, i, to, i, m[0])
				case v == "PMD":
					add([]string{"pmd"}, nil, i, to, i, m[0])
				case strings.HasPrefix(v, "PMD."):
					add([]string{"pmd"}, []string{v[4:]}, i, to, i, m[0])
				case strings.HasPrefix(strings.ToLower(v), "checkstyle:"):
					add([]string{"checkstyle"}, []string{"ci:" + strings.ToLower(v[11:])}, i, to, i, m[0])
				case strings.HasPrefix(v, "detekt:"):
					add([]string{"detekt"}, []string{v[7:]}, i, to, i, m[0])
				case strings.HasPrefix(v, "ktlint"):
					if id := strings.TrimPrefix(strings.TrimPrefix(v, "ktlint"), ":"); id != "" {
						add([]string{"ktlint"}, []string{id}, i, to, i, m[0])
					} else {
						add([]string{"ktlint"}, nil, i, to, i, m[0])
					}
				case strings.HasPrefix(v, "crev:"):
					fi.sups = append(fi.sups, inlineSup{crev: true, ids: []string{v[5:]}, from: i + 1, to: to + 1, line: i + 1, text: m[0]})
				default:
					add([]string{"errorprone", "spotbugs", "detekt"}, []string{v}, i, to, i, m[0])
					add([]string{"checkstyle"}, []string{"ci:" + strings.ToLower(v)}, i, to, i, m[0])
				}
			}
		}
		// PHP
		if m := rePhpcs.FindStringSubmatch(l); m != nil {
			ids := fields(strings.Split(m[2], "--")[0])
			switch m[1] {
			case "ignoreFile":
				add([]string{"phpcs"}, nil, 0, n-1, i, m[0])
			case "ignore":
				from, to := nextOrSame(i)
				add([]string{"phpcs"}, nilIfEmpty(ids), from, to, i, m[0])
			case "disable":
				k := strings.Join(ids, ",")
				phpcsOpen[k] = open{nilIfEmpty(ids), i}
			case "enable":
				for k, o := range phpcsOpen {
					add([]string{"phpcs"}, o.ids, o.line, i, o.line, "phpcs:disable "+k)
					delete(phpcsOpen, k)
				}
			}
		}
		if m := rePhpstan.FindStringSubmatch(l); m != nil {
			ids := nilIfEmpty(fields(m[2]))
			switch {
			case m[1] == "-next-line":
				add([]string{"phpstan"}, nil, i+1, i+1, i, m[0])
			case m[1] == "-line":
				add([]string{"phpstan"}, nil, i, i, i, m[0])
			default:
				from, to := nextOrSame(i)
				add([]string{"phpstan"}, ids, from, to, i, m[0])
			}
		}
		if m := rePsalm.FindStringSubmatch(l); m != nil {
			j := i + 1
			for j < n && commentOnly(lines[j]) {
				j++
			}
			add([]string{"psalm"}, fields(m[1]), i, declExtent(lines, min(j, n-1)), i, m[0])
		}
		// Docker / Terraform / YAML / protobuf
		if m := reHadolint.FindStringSubmatch(l); m != nil {
			if m[1] != "" {
				add([]string{"hadolint"}, fields(m[2]), 0, n-1, i, m[0])
			} else {
				j := i + 1
				for j < n-1 && strings.HasSuffix(strings.TrimSpace(lines[j]), "\\") {
					j++
				}
				add([]string{"hadolint"}, fields(m[2]), i+1, j, i, m[0])
			}
		}
		if isDocker && i < 20 {
			if m := reDockerCheck.FindStringSubmatch(strings.TrimSpace(l)); m != nil {
				ids := fields(m[1])
				if len(ids) == 1 && ids[0] == "all" {
					ids = nil
				}
				add([]string{"docker-build-check"}, ids, 0, n-1, i, m[0])
			}
		}
		if m := reTflint.FindStringSubmatch(l); m != nil {
			ids := fields(m[1])
			if len(ids) == 1 && ids[0] == "all" {
				ids = nil
			}
			from := i
			if commentOnly(l) {
				from = i + 1
			}
			to := from
			if from < n && strings.Contains(lines[from], "{") {
				to = declExtent(lines, from)
			}
			add([]string{"tflint"}, ids, from, to, i, m[0])
		}
		if m := reCheckov.FindStringSubmatch(l); m != nil {
			start := i
			for start > 0 && !(indent(lines[start]) == 0 && strings.Contains(lines[start], "{")) {
				start--
			}
			to := n - 1
			if strings.Contains(lines[start], "{") {
				to = declExtent(lines, start)
			}
			if isDocker {
				start, to = 0, n-1
			}
			add([]string{"checkov"}, []string{m[1]}, start, to, i, m[0])
		}
		if m := reYamllint.FindStringSubmatch(l); m != nil {
			var ids []string
			for _, r := range fields(m[2]) {
				ids = append(ids, strings.TrimPrefix(r, "rule:"))
			}
			switch m[1] {
			case "disable-file":
				add([]string{"yamllint"}, nil, 0, n-1, i, m[0])
			case "disable-line":
				from, to := nextOrSame(i)
				add([]string{"yamllint"}, nilIfEmpty(ids), from, to, i, m[0])
			case "disable":
				yamlOpen[strings.Join(ids, ",")] = open{nilIfEmpty(ids), i}
			case "enable":
				for k, o := range yamlOpen {
					add([]string{"yamllint"}, o.ids, o.line, i, o.line, "yamllint disable "+k)
					delete(yamlOpen, k)
				}
			}
		}
		if m := reBuf.FindStringSubmatch(l); m != nil {
			j := i + 1
			for j < n && commentOnly(lines[j]) {
				j++
			}
			add([]string{"buf"}, []string{m[1]}, i+1, declExtent(lines, min(j, n-1)), i, m[0])
		}
		// crev
		if m := reCrev.FindStringSubmatch(l); m != nil {
			ids := fields(m[2])
			if len(ids) == 1 && ids[0] == "all" {
				ids = nil
			}
			s := inlineSup{crev: true, ids: ids, line: i + 1, text: strings.TrimSpace(m[0])}
			switch m[1] {
			case "-file":
				s.from, s.to = 1, n
			case "-next-line":
				s.from, s.to = i+2, i+2
			default:
				s.from, s.to = i+1, i+2 // same line, or the line below a comment-only line
			}
			fi.sups = append(fi.sups, s)
		}
	}
	for k, o := range eslintOpen {
		add(eslintFamily, o.ids, o.line, n-1, o.line, "eslint-disable "+k)
	}
	for k, o := range phpcsOpen {
		add([]string{"phpcs"}, o.ids, o.line, n-1, o.line, "phpcs:disable "+k)
	}
	for k, o := range yamlOpen {
		add([]string{"yamllint"}, o.ids, o.line, n-1, o.line, "yamllint disable "+k)
	}
	return fi
}

func nilIfEmpty(s []string) []string {
	if len(s) == 0 {
		return nil
	}
	return s
}

// Match returns why a finding (crev rule id + equivalents, lines start..end) is suppressed inline.
func (fi *FileInline) Match(rel, ruleID string, equivalents []string, start, end int) *SuppressedBy {
	if fi == nil {
		return nil
	}
	if end < start {
		end = start
	}
	for _, s := range fi.sups {
		if start > s.to || start < s.from {
			continue
		}
		src := fmt.Sprintf("%s:%d %s", rel, s.line, s.text)
		if s.crev {
			if s.ids == nil {
				return &SuppressedBy{Kind: "crev-ignore", Tool: "crev", ID: "all", Source: src}
			}
			for _, id := range s.ids {
				if id == ruleID {
					return &SuppressedBy{Kind: "crev-ignore", Tool: "crev", ID: id, Source: src}
				}
			}
			continue
		}
		for _, eq := range equivalents {
			tool, id, ok := strings.Cut(eq, ":")
			if !ok || !slices.Contains(s.tools, tool) {
				continue
			}
			if s.ids == nil {
				return &SuppressedBy{Kind: "inline", Tool: tool, ID: id, Source: src}
			}
			for _, sid := range s.ids {
				if inlineIDMatch(tool, sid, id) {
					return &SuppressedBy{Kind: "inline", Tool: tool, ID: id, Source: src}
				}
			}
		}
	}
	return nil
}

func inlineIDMatch(tool, sid, id string) bool {
	if sid == id {
		return true
	}
	if c, ok := strings.CutPrefix(sid, "ci:"); ok {
		return strings.EqualFold(c, id)
	}
	switch tool {
	case "pylint":
		return idMatch(sid, id)
	case "ruff", "flake8":
		return strings.HasPrefix(id, sid) // "# noqa: E5" style prefixes are accepted by ruff
	case "ktlint":
		return strings.TrimPrefix(id, "standard:") == strings.TrimPrefix(sid, "standard:")
	}
	return false
}

func (fi *FileInline) crevOnly() *FileInline {
	out := &FileInline{}
	for _, s := range fi.sups {
		if s.crev {
			out.sups = append(out.sups, s)
		}
	}
	return out
}

// oxlintInlineIDs expands oxlint-disable ids ("no-console", "typescript/no-explicit-any") to the
// oxlint key and its ESLint-family id so either kind of crev equivalent matches.
func oxlintInlineIDs(ids []string) []string {
	var out []string
	for _, id := range ids {
		k := OxlintKey(id)
		_, fam := oxlintFamily(k)
		out = append(out, id, k, fam)
	}
	return slices.Compact(out)
}

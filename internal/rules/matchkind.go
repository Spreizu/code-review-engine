package rules

import (
	"regexp"
	"regexp/syntax"
	"strings"
)

// MatchKindExactAPI marks a version-gated deprecation/removal/migration rule whose detection is an
// exact identifier, import, config key or dependency match (user decision 2026-10-10): such rules
// report directly even when their trust level is unproven, because a hit is the documented API by
// name inside the documented version range. Everything else that is unproven stays ai-confirm.
const MatchKindExactAPI = "exact-api"

// MatchKindMetric marks a threshold rule whose finding is a measured fact (a metric.gt / metric.ge
// filter: cognitive complexity, parameter count, nesting depth, ...) with a threshold the project
// can configure through its linter settings. The hit is the number itself, so it reports directly
// even when unproven; whether the threshold suits the project is the project's setting.
const MatchKindMetric = "metric"

// IsMetric reports whether r is a valid metric rule (declared match_kind metric, a metric filter).
func IsMetric(r *Rule) bool {
	if r.MatchKind != MatchKindMetric {
		return false
	}
	for _, f := range r.Detection.Filters {
		if strings.HasPrefix(f, "metric.gt:") || strings.HasPrefix(f, "metric.ge:") {
			return true
		}
	}
	return false
}

// ReportsUnproven: match kinds that report directly when unproven.
func ReportsUnproven(r *Rule) bool {
	return r.MatchKind == MatchKindExactAPI || IsMetric(r)
}

var (
	predRe = regexp.MustCompile(`\(#([a-z-]+[?!])\s+@\w+\s*((?:"(?:[^"\\]|\\.)*"\s*)*)\)`)
	strRe  = regexp.MustCompile(`"((?:[^"\\]|\\.)*)"`)
)

var exactKinds = map[string]bool{"deprecation": true, "removal": true, "migration": true}

// ExactAPI classifies a rule (declared detection, after governance, before the trust policy).
// ok is true when every condition holds; why explains the decision either way.
func ExactAPI(r *Rule) (ok bool, why string) {
	if !exactKinds[r.Kind] {
		return false, "kind " + r.Kind + " is not deprecation/removal/migration"
	}
	if r.Detection.Mode != "deterministic" {
		return false, "not deterministic"
	}
	gated := false
	for k, v := range r.AppliesTo {
		if k != "any" && strings.TrimSpace(v) != "" && strings.TrimSpace(v) != "*" {
			gated = true
		}
	}
	if !gated {
		return false, "no version range in applies_to"
	}
	switch r.Detection.Engine {
	case "tree-sitter":
		return exactQuery(r)
	case "config":
		c := r.Detection.Config
		if _, ok := c["key"]; !ok {
			if _, ok := c["key_any_of"]; !ok {
				return false, "config rule without an exact key (key_prefix / check)"
			}
		}
		switch c["op"] {
		case "exists", "equals", "absent", "in":
		default:
			return false, "config op is not an exact comparison"
		}
		if ci, _ := c["case_insensitive"].(bool); ci {
			return false, "case-insensitive config match"
		}
		return true, "exact config key"
	case "manifest":
		switch r.Detection.Manifest["check"] {
		case "has_dependency", "dependency_version":
			return true, "exact dependency name"
		}
		return false, "manifest check is not a dependency-name match"
	}
	return false, "engine " + r.Detection.Engine + " is not an exact match engine"
}

func exactQuery(r *Rule) (bool, string) {
	q := r.Detection.Query
	preds := predRe.FindAllStringSubmatch(q, -1)
	if len(preds) == 0 {
		return false, "query names no identifier (structural pattern)"
	}
	if strings.Count(q, "(#") != len(preds) {
		return false, "query uses predicates the classifier cannot read"
	}
	positive := false
	for _, p := range preds {
		name, args := p[1], strRe.FindAllStringSubmatch(p[2], -1)
		switch name {
		case "eq?", "any-of?":
			positive = true
		case "not-eq?", "not-any-of?":
		case "match?", "not-match?":
			for _, a := range args {
				if !finiteAnchored(strings.ReplaceAll(a[1], `\\`, `\`)) {
					return false, "regex predicate is not an anchored literal set: " + a[1]
				}
			}
			if name == "match?" {
				positive = true
			}
		default:
			return false, "predicate #" + name + " is not an exact comparison"
		}
	}
	if !positive {
		return false, "no positive exact predicate"
	}
	// every top-level pattern must carry its own positive exact predicate (an alternative pattern
	// without one would match structurally). Filters only narrow matches, so they cannot widen an
	// exact identifier match.
	for _, pat := range topPatterns(q) {
		ok := false
		for _, p := range predRe.FindAllStringSubmatch(pat, -1) {
			if p[1] == "eq?" || p[1] == "any-of?" || p[1] == "match?" {
				ok = true
			}
		}
		if !ok {
			return false, "a query pattern has no exact identifier predicate"
		}
	}
	return true, "exact identifier predicates"
}

// topPatterns splits a query into its top-level patterns; a top-level predicate group "(#...)"
// belongs to the pattern before it.
func topPatterns(q string) []string {
	var out []string
	depth, start, inStr := 0, -1, false
	for i := 0; i < len(q); i++ {
		c := q[i]
		if inStr {
			if c == '\\' {
				i++
			} else if c == '"' {
				inStr = false
			}
			continue
		}
		switch c {
		case '"':
			inStr = true
		case ';': // comment
			for i < len(q) && q[i] != '\n' {
				i++
			}
		case '(', '[':
			if depth == 0 {
				start = i
			}
			depth++
		case ')', ']':
			depth--
			if depth == 0 && start >= 0 {
				pat := q[start : i+1]
				if strings.HasPrefix(pat, "(#") && len(out) > 0 {
					out[len(out)-1] += " " + pat
				} else {
					out = append(out, pat)
				}
				start = -1
			}
		}
	}
	return out
}

// finiteAnchored reports whether a regex is anchored at both ends and matches only a finite set of
// short strings (literals, alternations, optional parts, single-character classes such as the
// quote around a Terraform type name): i.e. it names identifiers instead of describing a shape.
func finiteAnchored(expr string) bool {
	re, err := syntax.Parse(expr, syntax.Perl)
	if err != nil {
		return false
	}
	re = re.Simplify()
	subs := []*syntax.Regexp{re}
	if re.Op == syntax.OpConcat {
		subs = re.Sub
	}
	if len(subs) < 3 || !isBegin(subs[0]) || !isEnd(subs[len(subs)-1]) {
		// ^(a$|b$) style alternations of anchored literals
		if re.Op == syntax.OpAlternate {
			for _, s := range re.Sub {
				if !finiteAnchoredRe(s) {
					return false
				}
			}
			return true
		}
		return false
	}
	return finite(re)
}

func finiteAnchoredRe(re *syntax.Regexp) bool {
	return re.Op == syntax.OpConcat && len(re.Sub) >= 3 && isBegin(re.Sub[0]) && isEnd(re.Sub[len(re.Sub)-1]) && finite(re)
}

func isBegin(r *syntax.Regexp) bool { return r.Op == syntax.OpBeginText || r.Op == syntax.OpBeginLine }
func isEnd(r *syntax.Regexp) bool   { return r.Op == syntax.OpEndText || r.Op == syntax.OpEndLine }

func finite(re *syntax.Regexp) bool {
	switch re.Op {
	case syntax.OpLiteral, syntax.OpEmptyMatch, syntax.OpBeginText, syntax.OpEndText, syntax.OpBeginLine, syntax.OpEndLine, syntax.OpAnyCharNotNL:
		return true
	case syntax.OpCharClass:
		n := 0
		for i := 0; i+1 < len(re.Rune); i += 2 {
			n += int(re.Rune[i+1]-re.Rune[i]) + 1
		}
		return n <= 12 || (re.Flags&syntax.FoldCase != 0 && n <= 24)
	case syntax.OpCapture, syntax.OpConcat, syntax.OpAlternate, syntax.OpQuest:
		for _, s := range re.Sub {
			if !finite(s) {
				return false
			}
		}
		return true
	case syntax.OpRepeat:
		return re.Max >= 0 && re.Max <= 3 && finite(re.Sub[0])
	}
	return false
}

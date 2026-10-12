package engine

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/elmo/code-review-engine/internal/rules"
	ts "github.com/tree-sitter/go-tree-sitter"
)

// Code metrics for maintainability rules (filters metric.gt / metric.ge). They work on the node
// kinds of every supported grammar at once (java, javascript/typescript/tsx, python, go, kotlin,
// php): the kind names do not collide in meaning, so one table serves all languages.
//
//   cognitive   crev's implementation of the cognitive-complexity idea: +1 for each break in the
//               linear flow (if / else if / else, loops, switch/when/match, catch, ternaries, a
//               new sequence of && / || / and / or / ??, labelled jumps, goto), plus the current
//               nesting depth for structures that nest; nested functions and lambdas add depth.
//   cyclomatic  1 + decision points (branches, loop heads, case labels, catches, ternaries,
//               logical operators); nested functions are measured on their own.
//   params      declared parameters (Python self/cls, Python _-prefixed names and Go receivers excluded).
//   returns     return statements of the function itself.
//   nesting     deepest nesting of control structures (an else-if chain is one level).
//   lines       non-blank, non-comment lines of the node.
//   cases       case/when/match arms of a switch-like node.

var (
	ifKinds = set("if_statement", "if_expression")
	// structures that add 1 + nesting and nest their children
	nestKinds = set("if_statement", "if_expression", "for_statement", "enhanced_for_statement", "for_in_statement",
		"foreach_statement", "while_statement", "do_statement", "do_while_statement", "switch_statement",
		"switch_expression", "expression_switch_statement", "type_switch_statement", "select_statement",
		"when_expression", "match_statement", "match_expression", "catch_clause", "catch_block", "except_clause",
		"ternary_expression", "conditional_expression")
	loopKinds = set("for_statement", "enhanced_for_statement", "for_in_statement", "foreach_statement",
		"while_statement", "do_statement", "do_while_statement")
	clauseKinds = set("elif_clause", "else_if_clause", "else_clause")
	logicKinds  = set("binary_expression", "boolean_operator", "conjunction_expression", "disjunction_expression")
	logicOps    = set("&&", "||", "and", "or", "??")
	lambdaKinds = set("lambda_expression", "arrow_function", "function_expression", "func_literal", "lambda",
		"lambda_literal", "anonymous_function", "anonymous_function_creation_expression", "function_definition",
		"function_declaration", "method_declaration", "method_definition", "generator_function_declaration",
		"generator_function", "function", "secondary_constructor", "constructor_declaration")
	caseKinds = set("switch_label", "switch_case", "expression_case", "type_case", "communication_case",
		"case_statement", "case_clause", "match_conditional_expression", "switch_rule")
	returnKinds = set("return_statement", "return_expression")
	commentRe   = regexp.MustCompile(`^\s*(//|#|/\*|\*|\*/|--)`)
)

func set(xs ...string) map[string]bool {
	m := make(map[string]bool, len(xs))
	for _, x := range xs {
		m[x] = true
	}
	return m
}

// operator returns the operator token of a binary-like node (first anonymous child that is not a parenthesis).
func operator(n *ts.Node, src []byte) string {
	for i := uint(0); i < n.ChildCount(); i++ {
		c := n.Child(i)
		if c == nil || c.IsNamed() {
			continue
		}
		t := c.Utf8Text(src)
		if t != "(" && t != ")" {
			return t
		}
	}
	return ""
}

func isLogic(n *ts.Node, src []byte) (string, bool) {
	if !logicKinds[n.Kind()] {
		return "", false
	}
	op := operator(n, src)
	return op, logicOps[op]
}

func named(n *ts.Node) []*ts.Node {
	var out []*ts.Node
	for i := uint(0); i < n.NamedChildCount(); i++ {
		if c := n.NamedChild(i); c != nil && c.Kind() != "comment" && c.Kind() != "line_comment" && c.Kind() != "block_comment" {
			out = append(out, c)
		}
	}
	return out
}

// isElseIf: an if that is the else branch of another if (directly, or wrapped in an else clause).
func isElseIf(n *ts.Node) bool {
	if !ifKinds[n.Kind()] {
		return false
	}
	p := n.Parent()
	if p == nil {
		return false
	}
	if p.Kind() == "else_clause" {
		return p.Parent() != nil && ifKinds[p.Parent().Kind()]
	}
	if !ifKinds[p.Kind()] {
		return false
	}
	if c := p.ChildByFieldName("condition"); c != nil && c.Id() == n.Id() {
		return false
	}
	kids := named(p)
	return len(kids) > 0 && kids[len(kids)-1].Id() == n.Id() && len(kids) >= 3
}

// elseBlock: a plain else branch of an if in grammars without an else_clause node (java, go, kotlin).
func elseBlock(n *ts.Node) bool {
	p := n.Parent()
	if p == nil || !ifKinds[p.Kind()] || ifKinds[n.Kind()] || clauseKinds[n.Kind()] {
		return false
	}
	if a := p.ChildByFieldName("alternative"); a != nil {
		return a.Id() == n.Id()
	}
	if p.ChildByFieldName("consequence") != nil {
		return false // java/go name the else branch "alternative"; js/python use clauses
	}
	kids := named(p)
	cond := p.ChildByFieldName("condition")
	var branches []*ts.Node
	for _, k := range kids {
		if cond != nil && k.Id() == cond.Id() {
			continue
		}
		branches = append(branches, k)
	}
	return len(branches) == 2 && branches[1].Id() == n.Id()
}

func labelled(n *ts.Node) bool {
	switch n.Kind() {
	case "break_statement", "continue_statement", "break_expression", "continue_expression":
		return len(named(n)) > 0
	case "goto_statement":
		return true
	}
	return false
}

func cognitive(root *ts.Node, src []byte) int {
	total := 0
	var walk func(n *ts.Node, level int)
	walk = func(n *ts.Node, level int) {
		for _, c := range named(n) {
			k := c.Kind()
			switch {
			case lambdaKinds[k]:
				walk(c, level+1)
			case isElseIf(c):
				total++
				walk(c, level)
			case clauseKinds[k]:
				// "else if" in JS is an else clause wrapping an if: the if counts it
				if !(k == "else_clause" && len(named(c)) == 1 && ifKinds[named(c)[0].Kind()]) {
					total++
				}
				walk(c, level)
			case elseBlock(c):
				total++
				walk(c, level)
			case nestKinds[k]:
				total += 1 + level
				walk(c, level+1)
			default:
				if op, ok := isLogic(c, src); ok {
					if pop, pok := isLogic(n, src); !pok || pop != op {
						total++
					}
				} else if labelled(c) {
					total++
				}
				walk(c, level)
			}
		}
	}
	walk(root, 0)
	return total
}

func cyclomatic(root *ts.Node, src []byte) int {
	total := 1
	var walk func(n *ts.Node)
	walk = func(n *ts.Node) {
		for _, c := range named(n) {
			k := c.Kind()
			if lambdaKinds[k] {
				continue
			}
			switch {
			case ifKinds[k], loopKinds[k], k == "elif_clause", k == "else_if_clause", k == "catch_clause", k == "catch_block",
				k == "except_clause", k == "ternary_expression", k == "conditional_expression":
				total++
			case caseKinds[k]:
				if !strings.HasPrefix(strings.TrimSpace(c.Utf8Text(src)), "default") {
					total++
				}
			case k == "when_entry":
				if !strings.HasPrefix(strings.TrimSpace(c.Utf8Text(src)), "else") {
					total++
				}
			default:
				if _, ok := isLogic(c, src); ok {
					total++
				}
			}
			walk(c)
		}
	}
	walk(root)
	return total
}

func paramCount(fn *ts.Node, src []byte) int {
	pl := fn.ChildByFieldName("parameters")
	if pl == nil {
		for _, c := range named(fn) {
			switch c.Kind() {
			case "formal_parameters", "parameters", "function_value_parameters", "parameter_list", "lambda_parameters":
				pl = c
			}
			if pl != nil {
				break
			}
		}
	}
	if pl == nil {
		return 0
	}
	n := 0
	for i, c := range named(pl) {
		t := strings.TrimSpace(c.Utf8Text(src))
		if i == 0 && (t == "self" || t == "cls") {
			continue
		}
		if pl.Kind() == "parameters" && pyDummyParam(c, src) {
			continue // Python: underscore-prefixed names are deliberately unused (ruff/pylint dummy names)
		}
		switch c.Kind() {
		case "receiver_parameter", "positional_separator", "keyword_separator":
			continue
		case "parameter_declaration", "variadic_parameter_declaration": // go: a, b int
			ids := 0
			for _, x := range named(c) {
				if x.Kind() == "identifier" {
					ids++
				}
			}
			n += max(ids, 1)
			continue
		}
		n++
	}
	return n
}

// pyDummyParam reports a Python parameter whose name starts with "_".
func pyDummyParam(c *ts.Node, src []byte) bool {
	id := c
	if c.Kind() != "identifier" {
		id = c.ChildByFieldName("name")
		if id == nil {
			for _, x := range named(c) {
				if x.Kind() == "identifier" {
					id = x
					break
				}
			}
		}
	}
	return id != nil && id.Kind() == "identifier" && strings.HasPrefix(id.Utf8Text(src), "_")
}

func returns(root *ts.Node) int {
	total := 0
	var walk func(n *ts.Node)
	walk = func(n *ts.Node) {
		for _, c := range named(n) {
			if lambdaKinds[c.Kind()] {
				continue
			}
			if returnKinds[c.Kind()] {
				total++
			}
			walk(c)
		}
	}
	walk(root)
	return total
}

func nesting(root *ts.Node) int {
	best := 0
	var walk func(n *ts.Node, d int)
	walk = func(n *ts.Node, d int) {
		for _, c := range named(n) {
			k := c.Kind()
			switch {
			case lambdaKinds[k]:
				continue
			case isElseIf(c) || clauseKinds[k] || elseBlock(c):
				walk(c, d)
			case nestKinds[k] && k != "ternary_expression" && k != "conditional_expression" || k == "try_statement" || k == "try_expression":
				best = max(best, d+1)
				walk(c, d+1)
			default:
				walk(c, d)
			}
		}
	}
	walk(root, 0)
	return best
}

func codeLines(n *ts.Node, src []byte) int {
	c := 0
	inBlock := false
	for _, l := range strings.Split(n.Utf8Text(src), "\n") {
		t := strings.TrimSpace(l)
		if inBlock {
			if strings.Contains(t, "*/") {
				inBlock = false
			}
			continue
		}
		if t == "" || commentRe.MatchString(t) && !strings.HasPrefix(t, "*/") {
			if strings.HasPrefix(t, "/*") && !strings.Contains(t, "*/") {
				inBlock = true
			}
			continue
		}
		c++
	}
	return c
}

func caseCount(n *ts.Node, src []byte) int {
	total := 0
	var walk func(x *ts.Node)
	walk = func(x *ts.Node) {
		for _, c := range named(x) {
			k := c.Kind()
			if nestKinds[k] && k != "ternary_expression" && k != "conditional_expression" && !loopKinds[k] && !ifKinds[k] {
				continue // a nested switch counts on its own
			}
			if caseKinds[k] || k == "when_entry" || k == "switch_block_statement_group" {
				if k != "switch_label" || !strings.HasPrefix(strings.TrimSpace(c.Utf8Text(src)), "default") {
					if k != "switch_block_statement_group" {
						total++
					}
				}
			}
			walk(c)
		}
	}
	walk(n)
	return total
}

// Metric computes one named metric on n.
func Metric(name string, n *ts.Node, src []byte) (int, error) {
	body := n
	if b := n.ChildByFieldName("body"); b != nil && name != "params" && name != "lines" {
		body = b
	}
	switch name {
	case "cognitive":
		return cognitive(body, src), nil
	case "cyclomatic":
		return cyclomatic(body, src), nil
	case "params":
		return paramCount(n, src), nil
	case "returns":
		return returns(body), nil
	case "nesting":
		return nesting(body), nil
	case "lines":
		return codeLines(n, src), nil
	case "cases":
		return caseCount(n, src), nil
	case "boolops":
		return boolOps(n, src), nil
	}
	return 0, fmt.Errorf("unknown metric %q", name)
}

// metricFilter implements metric.gt:NAME:N / metric.ge:NAME:N.
func metricFilter(name, arg string, n ts.Node, src []byte) (bool, error) {
	m, ns, ok := strings.Cut(arg, ":")
	if !ok {
		return false, fmt.Errorf("filter %s wants METRIC:N", name)
	}
	lim, err := strconv.Atoi(strings.TrimSpace(ns))
	if err != nil {
		return false, fmt.Errorf("filter %s: threshold %q: %w", name, ns, err)
	}
	v, err := Metric(m, &n, src)
	if err != nil {
		return false, err
	}
	if name == "metric.gt" {
		return v > lim, nil
	}
	return v >= lim, nil
}

// metricValue returns the measured value of the rule's (first) metric filter.
func metricValue(r *rules.Rule, n ts.Node, src []byte) (string, bool) {
	for _, f := range r.Detection.Filters {
		name, arg, _ := strings.Cut(f, ":")
		if name != "metric.gt" && name != "metric.ge" {
			continue
		}
		m, _, _ := strings.Cut(arg, ":")
		if v, err := Metric(m, &n, src); err == nil {
			return strconv.Itoa(v), true
		}
	}
	return "", false
}

// boolOps counts the && / || / and / or / ?? operators of a whole condition: only the outermost
// logical node of an expression is measured (inner ones return 0, so one condition = one finding).
func boolOps(n *ts.Node, src []byte) int {
	if _, ok := isLogic(n, src); !ok {
		return 0
	}
	for p := n.Parent(); p != nil && p.Kind() == "parenthesized_expression"; p = p.Parent() {
		n2 := p.Parent()
		if n2 != nil {
			if _, ok := isLogic(n2, src); ok {
				return 0
			}
		}
	}
	if p := n.Parent(); p != nil {
		if _, ok := isLogic(p, src); ok {
			return 0
		}
	}
	total := 0
	var walk func(x *ts.Node)
	walk = func(x *ts.Node) {
		if _, ok := isLogic(x, src); ok {
			total++
		}
		for _, c := range named(x) {
			if lambdaKinds[c.Kind()] {
				continue
			}
			walk(c)
		}
	}
	walk(n)
	return total
}

var literalRe = regexp.MustCompile(`^(-?\d[\d_.]*[lLfFdD]?|true|false|True|False|null|nil|None|"[^"]*"|'[^']*')$`)

// returnsInvariant: the function has at least two return statements and all of them return the
// same literal (nested functions are not looked at).
func returnsInvariant(fn *ts.Node, src []byte) bool {
	var vals []string
	var walk func(x *ts.Node)
	walk = func(x *ts.Node) {
		for _, c := range named(x) {
			if lambdaKinds[c.Kind()] {
				continue
			}
			if returnKinds[c.Kind()] {
				kids := named(c)
				if len(kids) == 0 {
					vals = append(vals, "")
				} else {
					vals = append(vals, strings.TrimSpace(kids[0].Utf8Text(src)))
				}
				continue
			}
			walk(c)
		}
	}
	body := fn
	if b := fn.ChildByFieldName("body"); b != nil {
		body = b
	}
	walk(body)
	if len(vals) < 2 || !literalRe.MatchString(vals[0]) {
		return false
	}
	for _, v := range vals[1:] {
		if v != vals[0] {
			return false
		}
	}
	return true
}

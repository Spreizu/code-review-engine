package engine

import (
	"regexp"
	"strings"

	ts "github.com/tree-sitter/go-tree-sitter"
)

// Branch analysis for if/else-if chains and switch-like statements (filter branches.*):
//
//   branches.dup_body     two branches of the chain/switch have the same (non-trivial) body
//   branches.all_same     every branch, including a final else/default, has the same body
//   branches.dup_cond     a condition of an if/else-if chain repeats an earlier one (side-effect free)
//
// Bodies are compared after removing comments and whitespace. The filters are evaluated on the
// head of a chain only (an if that is itself an else-if is skipped) so one chain = one finding.

type branch struct {
	cond, body string
	stmts      int
	isElse     bool
	init       bool   // the branch's if has an init statement (Go `if v, ok := f(); ok`)
	falls      bool   // a C-style case arm that falls through into the next arm (not mergeable)
	subj       string // Kotlin `when (x)` / `when (val x = …)` subject name; "" when unknown, `this` or absent
}

var whenSubjVal = regexp.MustCompile(`^\(\s*val\s+([A-Za-z_]\w*)`)
var whenSubjID = regexp.MustCompile(`^\(\s*([A-Za-z_]\w*)\s*\)$`)

// whenSubject returns the named subject of a Kotlin when expression, or "" (no subject, `this`, or an expression).
func whenSubject(n *ts.Node, src []byte) string {
	for _, c := range named(n) {
		if c.Kind() != "when_subject" {
			continue
		}
		t := strings.TrimSpace(c.Utf8Text(src))
		if m := whenSubjVal.FindStringSubmatch(t); m != nil {
			return m[1]
		}
		if m := whenSubjID.FindStringSubmatch(t); m != nil && m[1] != "this" {
			return m[1]
		}
	}
	return ""
}

// castMatters reports whether a branch's `is` smart cast can change how its body resolves: always when the
// subject is implicit or unknown, otherwise only when the body mentions the subject.
func castMatters(b branch) bool {
	if !smartCast.MatchString(b.cond) {
		return false
	}
	if b.subj == "" {
		return true
	}
	return regexp.MustCompile(`(^|[^\w.])` + regexp.QuoteMeta(b.subj) + `\b`).MatchString(b.body)
}

var (
	smartCast   = regexp.MustCompile(`(^| )!?is `) // Kotlin: identical text resolves differently after a smart cast
	sideEffect  = regexp.MustCompile(`\(|\+\+|--|[^=!<>]=[^=]|\bawait\b|\byield\b|:=`)
	blockKinds  = set("block", "statement_block", "compound_statement", "constructor_body", "control_structure_body", "switch_block")
	switchKinds = set("switch_statement", "switch_expression", "expression_switch_statement", "type_switch_statement",
		"when_expression", "match_statement", "match_expression", "select_statement")
)

// tokens renders n as its leaf tokens separated by a space, comments dropped.
func tokens(n *ts.Node, src []byte, b *strings.Builder) {
	if strings.Contains(n.Kind(), "comment") {
		return
	}
	if n.ChildCount() == 0 || strings.Contains(n.Kind(), "literal") && !strings.Contains(n.Kind(), "string") {
		// leaf, or a char/number literal whose content is not a child token (Kotlin 'Y' vs 'N')
		b.WriteString(n.Utf8Text(src))
		b.WriteByte(' ')
		return
	}
	for i := uint(0); i < n.ChildCount(); i++ {
		if c := n.Child(i); c != nil {
			tokens(c, src, b)
		}
	}
}

func normNode(n *ts.Node, src []byte) string {
	var b strings.Builder
	tokens(n, src, &b)
	s := strings.TrimSpace(b.String())
	if s == "{ }" || s == "{}" {
		return ""
	}
	if len(s) >= 4 && strings.HasPrefix(s, "{ ") && strings.HasSuffix(s, " }") {
		s = strings.TrimSpace(s[2 : len(s)-2])
	}
	return s
}

func stmtCount(n *ts.Node) int {
	if n == nil {
		return 0
	}
	if blockKinds[n.Kind()] || n.Kind() == "block" || n.Kind() == "statement_list" {
		c := 0
		for _, k := range named(n) {
			if k.Kind() == "statement_list" { // Go: block > statement_list
				c += stmtCount(k)
			} else if !jumpOnly(k) && !strings.Contains(k.Kind(), "comment") {
				c++
			}
		}
		return c
	}
	if jumpOnly(n) {
		return 0
	}
	return 1
}

// jumpOnly: a bare break/continue/fallthrough that ends a case arm is not a statement of its own
// for the "short branch" exemption.
func jumpOnly(n *ts.Node) bool {
	switch n.Kind() {
	case "break_statement", "continue_statement", "fallthrough_statement":
		return n.NamedChildCount() == 0
	}
	return false
}

func mkBranch(cond, body *ts.Node, src []byte, isElse bool) branch {
	b := branch{isElse: isElse}
	if cond != nil {
		b.cond = normNode(cond, src)
	}
	if body != nil {
		b.body = normNode(body, src)
		b.stmts = stmtCount(body)
	}
	return b
}

// ifChain flattens an if / else if / else chain into branches.
func ifChain(n *ts.Node, src []byte) []branch {
	var out []branch
	cur := n
	for cur != nil {
		cond := cur.ChildByFieldName("condition")
		var then, alt []*ts.Node
		if c := cur.ChildByFieldName("consequence"); c != nil {
			then = []*ts.Node{c}
		} else if c := cur.ChildByFieldName("body"); c != nil {
			then = []*ts.Node{c}
		}
		for _, k := range named(cur) {
			if cond != nil && k.Id() == cond.Id() || k.Kind() == "if_initializer" || len(then) > 0 && k.Id() == then[0].Id() {
				continue
			}
			if cur.ChildByFieldName("initializer") != nil && k.Id() == cur.ChildByFieldName("initializer").Id() {
				continue
			}
			if len(then) == 0 {
				then = []*ts.Node{k}
				continue
			}
			alt = append(alt, k)
		}
		if len(then) == 0 {
			return out
		}
		br := mkBranch(cond, then[0], src, false)
		br.init = cur.ChildByFieldName("initializer") != nil
		for _, k := range named(cur) {
			br.init = br.init || k.Kind() == "if_initializer"
		}
		out = append(out, br)
		cur = nil
		for _, a := range alt {
			switch {
			case ifKinds[a.Kind()]:
				cur = a
			case a.Kind() == "elif_clause" || a.Kind() == "else_if_clause":
				body := a.ChildByFieldName("consequence")
				if body == nil {
					body = a.ChildByFieldName("body")
				}
				out = append(out, mkBranch(a.ChildByFieldName("condition"), body, src, false))
			case a.Kind() == "else_clause":
				kids := named(a)
				if len(kids) == 1 && ifKinds[kids[0].Kind()] {
					cur = kids[0]
					continue
				}
				body := a.ChildByFieldName("body")
				if body == nil && len(kids) > 0 {
					body = kids[0]
				}
				out = append(out, mkBranch(nil, body, src, true))
			default:
				out = append(out, mkBranch(nil, a, src, true))
			}
		}
	}
	return out
}

var caseArmKinds = set("switch_block_statement_group", "switch_rule", "switch_case", "switch_default", "expression_case",
	"type_case", "communication_case", "default_case", "case_statement", "default_statement", "case_clause",
	"when_entry", "match_conditional_expression", "match_default_expression")

// switchArms returns the arms of a switch-like node (empty fall-through arms are dropped).
func switchArms(n *ts.Node, src []byte) []branch {
	var arms []*ts.Node
	var walk func(x *ts.Node)
	walk = func(x *ts.Node) {
		for _, c := range named(x) {
			if caseArmKinds[c.Kind()] {
				arms = append(arms, c)
			} else if !switchKinds[c.Kind()] && (blockKinds[c.Kind()] || strings.HasSuffix(c.Kind(), "_block") || c.Kind() == "switch_body") {
				walk(c)
			}
		}
	}
	walk(n)
	subj := whenSubject(n, src)
	var out []branch
	for ai, a := range arms {
		txt := a.Utf8Text(src)
		isDefault := strings.HasPrefix(strings.TrimSpace(txt), "default") || strings.HasPrefix(strings.TrimSpace(txt), "else") ||
			a.Kind() == "switch_default" || a.Kind() == "default_case" || a.Kind() == "default_statement" || a.Kind() == "match_default_expression"
		var parts, conds []string
		stmts := 0
		_ = txt
		for _, k := range named(a) {
			switch k.Kind() {
			case "switch_label", "case_pattern", "match_condition_list", "when_condition", "type_list", "expression_list":
				conds = append(conds, normNode(k, src))
				continue
			}
			if v := a.ChildByFieldName("value"); v != nil && v.Id() == k.Id() {
				continue
			}
			if v := a.ChildByFieldName("condition"); v != nil && v.Id() == k.Id() {
				// Kotlin when_entry: `is T` is the condition field itself (type_test), so record it
				// for the smart-cast check (corpus FP: okhttp MappingTables, coil when (this)).
				conds = append(conds, normNode(k, src))
				continue
			}
			if v := a.ChildByFieldName("conditional_expressions"); v != nil && v.Id() == k.Id() {
				continue
			}
			if v := a.ChildByFieldName("guard"); v != nil && v.Id() == k.Id() {
				continue
			}
			parts = append(parts, normNode(k, src))
			stmts += stmtCount(k)
		}
		body := strings.Join(parts, " ; ")
		if body == "" {
			continue
		}
		falls := fallThroughArms[a.Kind()] && ai < len(arms)-1 && !endsInJump(a, src)
		out = append(out, branch{cond: strings.Join(conds, " , "), body: body, stmts: stmts, isElse: isDefault, falls: falls, subj: subj})
	}
	return out
}

// fallThroughArms are case arms of switches whose cases fall through (Java/JS/TS/PHP/C-style):
// two textually equal arms where one falls into the next are not duplicates (merging them
// changes how many times the shared code runs, e.g. an unrolled loop).
var fallThroughArms = set("switch_block_statement_group", "switch_case", "switch_default", "case_statement", "default_statement")

// endsInJump reports whether the last statement of n leaves the switch arm.
func endsInJump(n *ts.Node, src []byte) bool {
	kids := named(n)
	for i := len(kids) - 1; i >= 0; i-- {
		k := kids[i]
		if strings.Contains(k.Kind(), "comment") {
			continue
		}
		switch k.Kind() {
		case "break_statement", "return_statement", "throw_statement", "continue_statement", "yield_statement", "goto_statement", "exit_statement":
			return true
		case "block", "statement_block", "compound_statement":
			return endsInJump(k, src)
		case "expression_statement":
			t := strings.TrimSpace(k.Utf8Text(src))
			return strings.HasPrefix(t, "throw ") || strings.HasPrefix(t, "exit") || strings.HasPrefix(t, "die")
		}
		return false
	}
	return false
}

func trivial(b branch) bool {
	// a lone break/return/continue/pass or a single short statement is not worth reporting
	return b.stmts < 2 && len(b.body) < 30
}

func branchesOf(n *ts.Node, src []byte) ([]branch, bool) {
	if ifKinds[n.Kind()] {
		if isElseIf(n) {
			return nil, false
		}
		return ifChain(n, src), true
	}
	if switchKinds[n.Kind()] {
		return switchArms(n, src), true
	}
	return nil, false
}

// branchFilter evaluates the branches.* filters on n.
func branchFilter(name string, n ts.Node, src []byte) bool {
	bs, ok := branchesOf(&n, src)
	if !ok || len(bs) < 2 {
		return false
	}
	switch name {
	case "branches.dup_body":
		seen := map[string]bool{} // body -> an earlier branch tested a smart cast
		for _, b := range bs {
			if trivial(b) || b.falls {
				continue
			}
			cast := castMatters(b)
			if earlierCast, ok := seen[b.body]; ok && !cast && !earlierCast {
				return true
			}
			seen[b.body] = seen[b.body] || cast
		}
	case "branches.all_same":
		hasElse := false
		for _, b := range bs {
			if castMatters(b) {
				return false
			}
			hasElse = hasElse || b.isElse
			if b.body != bs[0].body {
				return false
			}
		}
		return hasElse
	case "branches.dup_cond":
		seen := map[string]bool{}
		for _, b := range bs {
			if b.init {
				return false // an init statement re-evaluates the tested variables per branch
			}
			c := b.cond
			if strings.HasPrefix(c, "( ") && strings.HasSuffix(c, " )") {
				c = c[2 : len(c)-2]
			}
			if c == "" || sideEffect.MatchString(c) {
				continue
			}
			if seen[c] {
				return true
			}
			seen[c] = true
		}
	}
	return false
}

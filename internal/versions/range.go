// Package versions detects project version facts and evaluates version ranges.
package versions

import (
	"strconv"
	"strings"
)

// Normalize turns "1.8" into "8", strips leading v/^/~ and build metadata.
func Normalize(key, v string) string {
	v = strings.TrimSpace(strings.Trim(v, `"'`))
	v = strings.TrimLeft(v, "v^~=> <")
	if i := strings.IndexAny(v, "+ "); i >= 0 {
		v = v[:i]
	}
	if key == "java" && strings.HasPrefix(v, "1.") {
		v = strings.TrimPrefix(v, "1.")
	}
	if key == "ecmascript" {
		l := strings.ToLower(v)
		l = strings.TrimPrefix(l, "es")
		switch l {
		case "3":
			return "3"
		case "5":
			return "5"
		case "6":
			return "2015"
		}
		if n, err := strconv.Atoi(l); err == nil && n >= 7 && n < 100 { // ecmaVersion 7..17
			return strconv.Itoa(2009 + n)
		}
		return l
	}
	return v
}

func parts(v string) []int {
	var out []int
	for _, p := range strings.Split(v, ".") {
		n := 0
		for _, c := range p {
			if c < '0' || c > '9' {
				break
			}
			n = n*10 + int(c-'0')
		}
		out = append(out, n)
	}
	return out
}

// Compare returns -1, 0, 1 comparing dotted numeric versions (missing parts = 0).
func Compare(a, b string) int {
	pa, pb := parts(a), parts(b)
	for i := 0; i < len(pa) || i < len(pb); i++ {
		x, y := 0, 0
		if i < len(pa) {
			x = pa[i]
		}
		if i < len(pb) {
			y = pb[i]
		}
		if x < y {
			return -1
		}
		if x > y {
			return 1
		}
	}
	return 0
}

// Satisfies evaluates a range like ">=3.0 <3.5" or "<17 || >=25" (or "true"/"false" for flags).
func Satisfies(version, rng string) bool {
	rng = strings.TrimSpace(rng)
	if rng == "" || rng == "*" {
		return true
	}
	if rng == "true" || rng == "false" {
		return strings.EqualFold(version, rng)
	}
	for _, alt := range strings.Split(rng, "||") {
		ok := true
		for _, c := range strings.Fields(alt) {
			op := c[:len(c)-len(strings.TrimLeft(c, "<>=^~"))]
			v := c[len(op):]
			cmp := Compare(version, v)
			switch op {
			case ">=":
				ok = ok && cmp >= 0
			case ">":
				ok = ok && cmp > 0
			case "<=":
				ok = ok && cmp <= 0
			case "<":
				ok = ok && cmp < 0
			case "=", "":
				ok = ok && cmp == 0
			case "^":
				ok = ok && cmp >= 0 && parts(version)[0] == parts(v)[0]
			case "~":
				pv, pw := parts(version), parts(v)
				ok = ok && cmp >= 0 && pv[0] == pw[0] && len(pv) > 1 && len(pw) > 1 && pv[1] == pw[1]
			default:
				ok = false
			}
		}
		if ok {
			return true
		}
	}
	return false
}

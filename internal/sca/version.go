package sca

import (
	"strconv"
	"strings"
	"unicode"
)

// Compare orders two versions of an ecosystem: <0, 0, >0. It follows SemVer 2.0 precedence for
// npm / Go / Packagist (pre-release < release, numeric identifiers numerically) and a close
// approximation of PEP 440 and Maven ComparableVersion for PyPI / Maven: numeric segments compare
// numerically, a release outranks its pre-releases (a/alpha < b/beta < rc < release < post/sp),
// build metadata is ignored. Exotic version schemes (epochs, local versions) are approximated.
func Compare(eco, a, b string) int {
	a, b = norm(eco, a), norm(eco, b)
	if a == b {
		return 0
	}
	ra, pa := splitPre(a)
	rb, pb := splitPre(b)
	if c := cmpParts(parts(ra), parts(rb)); c != 0 {
		return c
	}
	switch {
	case pa == "" && pb == "":
		return 0
	case pa == "":
		return 1
	case pb == "":
		return -1
	}
	return cmpParts(parts(pa), parts(pb))
}

func norm(eco, v string) string {
	v = strings.TrimSpace(strings.ToLower(v))
	v = strings.TrimPrefix(v, "v")
	if i := strings.IndexByte(v, '+'); i >= 0 { // build metadata / local version
		v = v[:i]
	}
	if eco == EcoPyPI {
		if i := strings.IndexByte(v, '!'); i >= 0 { // epoch
			v = v[i+1:]
		}
	}
	return v
}

// pre-release qualifiers in ascending order; anything after the release that is not one of these
// (post, sp, patch levels) sorts after the release.
var preRank = map[string]int{"dev": 1, "snapshot": 1, "alpha": 2, "a": 2, "beta": 3, "b": 3, "milestone": 4, "m": 4, "rc": 5, "cr": 5, "c": 5, "pre": 5, "preview": 5}

// splitPre splits "1.2.3-rc.1" / "1.2.3rc1" / "1.2.3.beta1" into release and pre-release.
func splitPre(v string) (string, string) {
	i := 0
	for i < len(v) && (v[i] == '.' || unicode.IsDigit(rune(v[i]))) {
		i++
	}
	rel, rest := strings.TrimRight(v[:i], "."), strings.TrimLeft(v[i:], ".-_")
	if rest == "" {
		return rel, ""
	}
	w := rest
	if j := strings.IndexFunc(rest, func(r rune) bool { return !unicode.IsLetter(r) }); j >= 0 {
		w = rest[:j]
	}
	if _, pre := preRank[w]; pre {
		return rel, rest
	}
	// post-release / final / ga / sp: treat as release followed by extra parts
	if w == "final" || w == "ga" || w == "release" {
		return rel, ""
	}
	return rel + ".~" + rest, ""
}

type part struct {
	num   int64
	str   string
	isNum bool
}

func parts(s string) []part {
	var out []part
	cur := strings.Builder{}
	digit := false
	flush := func() {
		if cur.Len() == 0 {
			return
		}
		t := cur.String()
		if digit {
			n, _ := strconv.ParseInt(t, 10, 64)
			out = append(out, part{num: n, isNum: true})
		} else {
			out = append(out, part{str: t})
		}
		cur.Reset()
	}
	for _, r := range s {
		switch {
		case r == '.' || r == '-' || r == '_':
			flush()
		case unicode.IsDigit(r) != digit && cur.Len() > 0:
			flush()
			digit = unicode.IsDigit(r)
			cur.WriteRune(r)
		default:
			digit = unicode.IsDigit(r)
			cur.WriteRune(r)
		}
	}
	flush()
	return out
}

func cmpParts(a, b []part) int {
	for i := 0; i < max(len(a), len(b)); i++ {
		var x, y part
		if i < len(a) {
			x = a[i]
		} else {
			x = part{isNum: true}
		}
		if i < len(b) {
			y = b[i]
		} else {
			y = part{isNum: true}
		}
		switch {
		case x.isNum && y.isNum:
			if x.num != y.num {
				if x.num < y.num {
					return -1
				}
				return 1
			}
		case x.isNum: // number > qualifier, except post-release marker "~" which ranks above
			if strings.HasPrefix(y.str, "~") {
				return -1
			}
			return 1
		case y.isNum:
			if strings.HasPrefix(x.str, "~") {
				return 1
			}
			return -1
		default:
			rx, okx := preRank[x.str]
			ry, oky := preRank[y.str]
			if okx && oky && rx != ry {
				if rx < ry {
					return -1
				}
				return 1
			}
			if c := strings.Compare(x.str, y.str); c != 0 && !(okx && oky) {
				return c
			}
		}
	}
	return 0
}

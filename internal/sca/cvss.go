package sca

import (
	"math"
	"strings"
)

// CVSS3Score computes the CVSS v3.0/v3.1 base score of a vector string
// ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H" -> 9.8), per the FIRST specification
// (https://www.first.org/cvss/v3.1/specification-document, section 7). ok is false for other
// vector versions or incomplete vectors.
func CVSS3Score(vector string) (score float64, ok bool) {
	if !strings.HasPrefix(vector, "CVSS:3.") {
		return 0, false
	}
	m := map[string]string{}
	for _, kv := range strings.Split(vector, "/")[1:] {
		k, v, _ := strings.Cut(kv, ":")
		m[k] = v
	}
	av := map[string]float64{"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}[m["AV"]]
	ac := map[string]float64{"L": 0.77, "H": 0.44}[m["AC"]]
	ui := map[string]float64{"N": 0.85, "R": 0.62}[m["UI"]]
	changed := m["S"] == "C"
	pr := map[string]float64{"N": 0.85, "L": 0.62, "H": 0.27}[m["PR"]]
	if changed {
		pr = map[string]float64{"N": 0.85, "L": 0.68, "H": 0.5}[m["PR"]]
	}
	cia := map[string]float64{"H": 0.56, "L": 0.22, "N": 0}
	c, okc := cia[m["C"]]
	i, oki := cia[m["I"]]
	a, oka := cia[m["A"]]
	if av == 0 || ac == 0 || ui == 0 || pr == 0 || !okc || !oki || !oka || (m["S"] != "U" && m["S"] != "C") {
		return 0, false
	}
	iss := 1 - (1-c)*(1-i)*(1-a)
	var impact float64
	if changed {
		impact = 7.52*(iss-0.029) - 3.25*math.Pow(iss-0.02, 15)
	} else {
		impact = 6.42 * iss
	}
	expl := 8.22 * av * ac * pr * ui
	if impact <= 0 {
		return 0, true
	}
	if changed {
		return roundup(math.Min(1.08*(impact+expl), 10)), true
	}
	return roundup(math.Min(impact+expl, 10)), true
}

// roundup is the specification's Roundup (smallest one-decimal number >= x, float-safe).
func roundup(x float64) float64 {
	n := int64(math.Round(x * 100000))
	if n%10000 == 0 {
		return float64(n) / 100000
	}
	return float64(n/10000+1) / 10
}

// SeverityOf maps a CVSS base score (or a qualitative advisory severity) to crev's levels:
// critical (>= 9.0), major (>= 7.0, "high"), minor (>= 4.0, "medium"/"moderate"), info.
func SeverityOf(score float64, qualitative string) string {
	if score > 0 {
		switch {
		case score >= 9:
			return "critical"
		case score >= 7:
			return "major"
		case score >= 4:
			return "minor"
		}
		return "info"
	}
	switch strings.ToUpper(qualitative) {
	case "CRITICAL":
		return "critical"
	case "HIGH":
		return "major"
	case "MODERATE", "MEDIUM":
		return "minor"
	case "LOW":
		return "info"
	}
	return "major" // unknown severity: do not under-report a known vulnerability
}

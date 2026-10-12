package sca

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"slices"
	"sort"
	"strings"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/rules"
)

// RuleID is the rule every SCA finding reports under.
const RuleID = "SCA-OSV-VULNERABLE-DEPENDENCY"

// Rule describes SCA findings for reports (SARIF driver rules, UI, `crev rules show`).
func Rule() *rules.Rule {
	r := &rules.Rule{ID: RuleID, Title: "Dependency with a known vulnerability (OSV.dev)", Language: "any", Kind: "security",
		Category: "security", Severity: "major", Pack: "sca", PackVersion: "osv",
		Message: "A locked dependency version is affected by a published advisory (OSV.dev); upgrade to a fixed version.",
		CWE:     []string{"CWE-1395"}, OWASP: []string{"A06:2021", "A03:2025"}, ASVS: []string{"V3.7.1", "V15.2.1"}, RuleVersion: 1,
		Trust: &rules.Trust{Level: rules.TrustProven, Why: "advisory database match on exact locked versions"}}
	r.Detection.Mode, r.Detection.Engine = "deterministic", "sca"
	r.Source = rules.Source{URL: "https://osv.dev", Doc: "OSV.dev - Open Source Vulnerabilities database", DocVersion: "live"}
	return r
}

// Options configures a scan.
type Options struct {
	Root    string
	Mode    string // online | offline | off
	Dir     string // offline database directory
	MaxAge  time.Duration
	APIURL  string
	Timeout time.Duration
	HTTP    *http.Client
	Skip    func(rel string, isDir bool) bool // path exclusions (engine.PathFilter)
	InScope func(rel string) bool             // diff scans: only lockfiles in scope
	Now     func() time.Time
}

// Result of an SCA scan.
type Result struct {
	Findings   []*findings.Finding
	Packages   int
	Vulnerable int
	Warnings   []string
}

// DefaultDir is the offline database cache: $XDG_CACHE_HOME/crev/vulndb or ~/.cache/crev/vulndb.
func DefaultDir() string {
	if d := os.Getenv("XDG_CACHE_HOME"); d != "" {
		return filepath.Join(d, "crev", "vulndb")
	}
	if h, err := os.UserHomeDir(); err == nil {
		return filepath.Join(h, ".cache", "crev", "vulndb")
	}
	return filepath.Join(os.TempDir(), "crev-vulndb")
}

// Scan discovers lockfiles under o.Root and reports vulnerable packages.
func Scan(ctx context.Context, o Options) (*Result, error) {
	res := &Result{}
	if o.Mode == "off" {
		return res, nil
	}
	pkgs, errs, err := Discover(o.Root, o.Skip)
	if err != nil {
		return res, err
	}
	res.Warnings = append(res.Warnings, errs...)
	if o.InScope != nil {
		keep := pkgs[:0]
		for _, p := range pkgs {
			if o.InScope(p.File) {
				keep = append(keep, p)
			}
		}
		pkgs = keep
	}
	res.Packages = len(pkgs)
	if len(pkgs) == 0 {
		return res, nil
	}
	// query each distinct package version once
	uniq := []Package{}
	idx := map[string]int{}
	for _, p := range pkgs {
		if _, ok := idx[p.Key()]; !ok {
			idx[p.Key()] = len(uniq)
			uniq = append(uniq, p)
		}
	}
	var vulns [][]*Vuln
	switch o.Mode {
	case "offline":
		dir := o.Dir
		if dir == "" {
			dir = DefaultDir()
		}
		now := time.Now
		if o.Now != nil {
			now = o.Now
		}
		need := map[string]bool{}
		for _, p := range uniq {
			need[p.Ecosystem] = true
		}
		for _, eco := range sortedKeys(need) {
			if m, ok := ReadMeta(dir, eco); ok && o.MaxAge > 0 && now().Sub(m.Updated) > o.MaxAge {
				res.Warnings = append(res.Warnings, fmt.Sprintf("vulndb: %s database is %d days old (downloaded %s); run `crev vulndb update`",
					eco, int(now().Sub(m.Updated).Hours()/24), m.Updated.Format("2006-01-02")))
			}
		}
		var missing []string
		vulns, missing, err = Offline{Dir: dir}.Query(uniq)
		if err != nil {
			return res, err
		}
		for _, eco := range missing {
			res.Warnings = append(res.Warnings, fmt.Sprintf("vulndb: no offline %s database in %s; run `crev vulndb update` (dependencies of that ecosystem were not checked)", eco, dir))
		}
	default: // online
		hc := o.HTTP
		if hc == nil {
			hc = &http.Client{Timeout: o.Timeout}
		}
		c := &Client{BaseURL: o.APIURL, HTTP: hc}
		vulns, err = c.Query(ctx, uniq)
		if err != nil {
			res.Warnings = append(res.Warnings, "vulndb: OSV.dev query failed, dependencies not checked: "+err.Error())
			return res, nil
		}
	}
	vulnerable := map[string]bool{}
	for _, p := range pkgs {
		vs := mergeAliases(vulns[idx[p.Key()]])
		for _, v := range vs {
			res.Findings = append(res.Findings, finding(p, v))
			vulnerable[p.Key()] = true
		}
	}
	res.Vulnerable = len(vulnerable)
	sort.SliceStable(res.Findings, func(i, j int) bool {
		a, b := res.Findings[i], res.Findings[j]
		if a.Location.Path != b.Location.Path {
			return a.Location.Path < b.Location.Path
		}
		return a.Location.StartLine < b.Location.StartLine
	})
	return res, nil
}

func sortedKeys(m map[string]bool) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	slices.Sort(out)
	return out
}

// mergeAliases drops advisories that are aliases of one already listed (GHSA vs PYSEC vs GO ids
// for the same CVE), keeping the first (OSV returns the primary id first).
func mergeAliases(vs []*Vuln) []*Vuln {
	var out []*Vuln
	seen := map[string]bool{}
	for _, v := range vs {
		ids := append([]string{v.ID}, v.Aliases...)
		dup := false
		for _, id := range ids {
			if seen[id] {
				dup = true
			}
		}
		for _, id := range ids {
			seen[id] = true
		}
		if !dup {
			out = append(out, v)
		}
	}
	return out
}

// Severity resolves CVSS v3 score/vector (advisory or package level) or the qualitative
// database severity.
func severity(v *Vuln, p Package) (sev string, score float64, vector, source string) {
	vecs := v.Severity
	for _, a := range v.Affected {
		if samePkg(p.Ecosystem, a.Package.Name, p.Name) {
			vecs = append(vecs, a.Severity...)
		}
	}
	for _, s := range vecs {
		if sc, ok := CVSS3Score(s.Score); ok && sc > score {
			score, vector, source = sc, s.Score, s.Type
		}
	}
	if score == 0 {
		for _, s := range vecs {
			if strings.HasPrefix(s.Score, "CVSS:4") {
				vector, source = s.Score, s.Type
			}
		}
		if v.DatabaseSpecific.Severity != "" {
			source = "database_specific.severity " + v.DatabaseSpecific.Severity
		}
	}
	return SeverityOf(score, v.DatabaseSpecific.Severity), score, vector, source
}

func finding(p Package, v *Vuln) *findings.Finding {
	_, ranges, fixed := Match(v, p)
	sev, score, vector, ssrc := severity(v, p)
	var cves, ghsas []string
	for _, id := range append([]string{v.ID}, v.Aliases...) {
		switch {
		case strings.HasPrefix(id, "CVE-"):
			cves = append(cves, id)
		case strings.HasPrefix(id, "GHSA-"):
			ghsas = append(ghsas, id)
		}
	}
	ids := v.ID
	if len(cves) > 0 && cves[0] != v.ID {
		ids += " (" + strings.Join(cves, ", ") + ")"
	}
	summary := v.Summary
	if summary == "" {
		summary = firstLine(v.Details)
	}
	msg := fmt.Sprintf("%s %s (%s) is affected by %s", p.Name, p.Version, p.Ecosystem, ids)
	if summary != "" {
		msg += ": " + summary
	}
	fix := "No fixed version is published; consider replacing the dependency or mitigating."
	if fixed != "" {
		msg += ". Fixed in " + fixed + "."
		fix = fmt.Sprintf("Upgrade %s to %s or later (and regenerate %s).", p.Name, fixed, filepath.Base(p.File))
	} else {
		msg += ". No fixed version published."
	}
	cwe := v.DatabaseSpecific.CWEIDs
	if len(cwe) == 0 {
		cwe = []string{"CWE-1395"}
	}
	snippet := p.Name + "@" + p.Version
	f := &findings.Finding{
		RuleID: RuleID, RuleVersion: 1, PackVersion: "osv", Status: "confirmed", Severity: sev, Confidence: "high",
		DetectionMode: "deterministic", Kind: "security", Category: "security",
		Title:    "Vulnerable dependency: " + p.Name + " " + p.Version + " (" + v.ID + ")",
		Location: findings.Location{Path: p.File, StartLine: p.Line, EndLine: p.Line, StartColumn: 1},
		Snippet:  snippet, Message: msg, Fix: fix,
		Source: findings.Source{URL: "https://osv.dev/vulnerability/" + v.ID, Doc: "OSV " + v.ID, DocVersion: "modified " + v.Modified},
		CWE:    cwe, OWASP: []string{"A06:2021", "A03:2025"},
		Vuln: &findings.Vuln{ID: v.ID, Aliases: v.Aliases, CVE: cves, GHSA: ghsas, Ecosystem: p.Ecosystem, Package: p.Name, Version: p.Version,
			Affected: ranges, Fixed: fixed, CVSSScore: score, CVSSVector: vector, SeveritySource: ssrc, Summary: summary,
			Published: v.Published, Modified: v.Modified, Dev: p.Dev},
	}
	f.ID = findings.Fingerprint(RuleID, p.File, snippet+" "+v.ID, "", 0)
	return f
}

func firstLine(s string) string {
	s = strings.TrimSpace(s)
	if i := strings.IndexByte(s, '\n'); i >= 0 {
		s = s[:i]
	}
	if len(s) > 200 {
		s = s[:200] + "…"
	}
	return s
}

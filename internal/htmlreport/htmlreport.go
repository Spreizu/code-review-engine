// Package htmlreport builds the data model for a static HTML report from run history and renders
// it with a minimal built-in template.
//
// PLACEHOLDER LAYOUT: the visual design will follow an example the user provides later. The stable
// part is Data (also available as JSON via `crev report --data`); a new template only needs to
// consume Data, so Render can be swapped without touching run storage or the ledger.
package htmlreport

import (
	"fmt"
	"html"
	"html/template"
	"io"
	"slices"
	"strings"
	"time"

	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/runs"
)

// Data is the report contract.
type Data struct {
	Generated time.Time           `json:"generated"`
	Run       *runs.Meta          `json:"run"`
	Findings  []*findings.Finding `json:"findings"` // review-list findings of the run (findings.InReview)
	Branch    string              `json:"branch"`
	Timeline  []runs.RunPoint     `json:"timeline"` // per-branch ledger timeline (found vs fixed over time)
	Lifecycle map[string]int      `json:"lifecycle"`
	Fixed     []*runs.Entry       `json:"fixed"` // fixed in this run
	New       []*runs.Entry       `json:"new"`   // first seen in this run
}

// Build loads a run, its report and the branch ledger.
func Build(st runs.Store, ref string) (*Data, error) {
	m, err := st.Resolve(ref)
	if err != nil {
		return nil, err
	}
	rep, err := st.Report(m)
	if err != nil {
		return nil, err
	}
	d := &Data{Generated: time.Now().UTC(), Run: m, Branch: m.Branch, Lifecycle: map[string]int{}}
	for _, f := range rep.Findings {
		if findings.InReview(f, "") {
			d.Findings = append(d.Findings, f)
		}
	}
	l, err := st.LoadLedger(m.Branch)
	if err != nil {
		return nil, err
	}
	d.Timeline = l.Timeline
	for _, e := range l.Entries {
		d.Lifecycle[e.Status]++
	}
	if m.Ledger != nil {
		for _, fp := range m.Ledger.Fixed {
			if e := l.Entries[fp]; e != nil {
				d.Fixed = append(d.Fixed, e)
			}
		}
		for _, fp := range m.Ledger.New {
			if e := l.Entries[fp]; e != nil {
				d.New = append(d.New, e)
			}
		}
	}
	byPath := func(a, b *runs.Entry) int { return strings.Compare(a.Path, b.Path) }
	slices.SortFunc(d.Fixed, byPath)
	slices.SortFunc(d.New, byPath)
	return d, nil
}

// TimelineSVG draws open/fixed counts per run as an inline SVG (no JS, no external assets).
func TimelineSVG(tl []runs.RunPoint, w, h int) template.HTML {
	if len(tl) == 0 {
		return ""
	}
	max := 1
	for _, p := range tl {
		if p.Open > max {
			max = p.Open
		}
		if p.Fixed > max {
			max = p.Fixed
		}
	}
	x := func(i int) float64 {
		if len(tl) == 1 {
			return float64(w) / 2
		}
		return 10 + float64(i)*float64(w-20)/float64(len(tl)-1)
	}
	y := func(v int) float64 { return float64(h-15) - float64(v)*float64(h-30)/float64(max) }
	var open, bars strings.Builder
	for i, p := range tl {
		fmt.Fprintf(&open, "%.1f,%.1f ", x(i), y(p.Open))
		if p.Fixed > 0 {
			fmt.Fprintf(&bars, `<rect x="%.1f" y="%.1f" width="6" height="%.1f" class="fx"><title>%s: %d fixed</title></rect>`, x(i)-3, y(p.Fixed), y(0)-y(p.Fixed), html.EscapeString(p.Run), p.Fixed)
		}
	}
	// Built only from numbers and escaped run ids, so marking it safe HTML is sound.
	return template.HTML(fmt.Sprintf(`<svg viewBox="0 0 %d %d" class="chart" role="img" aria-label="open vs fixed per run">%s<polyline points="%s" class="op"/><text x="10" y="12">max %d open</text></svg>`,
		w, h, bars.String(), strings.TrimSpace(open.String()), max))
}

var tpl = template.Must(template.New("r").Funcs(template.FuncMap{"svg": TimelineSVG, "upper": strings.ToUpper}).Parse(`<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>crev report · {{.Branch}}</title>
<style>
:root{color-scheme:light dark;--bg:#fff;--fg:#1d1f23;--mut:#6b7280;--line:#e5e7eb;--acc:#2563eb;--crit:#dc2626;--maj:#ea580c;--min:#ca8a04;--inf:#6b7280}
@media(prefers-color-scheme:dark){:root{--bg:#0f1115;--fg:#e6e8eb;--mut:#9aa1ab;--line:#262a31;--acc:#60a5fa}}
body{margin:0;font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--fg)}
main{max-width:1100px;margin:auto;padding:24px}h1{font-size:20px;margin:0 0 4px}.mut{color:var(--mut)}
.kpis{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}.kpi{border:1px solid var(--line);border-radius:8px;padding:8px 14px}.kpi b{font-size:18px;display:block}
table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
.sev{font-size:11px;font-weight:600;padding:1px 6px;border-radius:4px;color:#fff}.critical{background:var(--crit)}.major{background:var(--maj)}.minor{background:var(--min)}.info{background:var(--inf)}
code{font:12px ui-monospace,monospace}.chart{width:100%;height:120px}.chart .op{fill:none;stroke:var(--acc);stroke-width:2}.chart .fx{fill:#16a34a}.chart text{fill:var(--mut);font-size:10px}
a{color:var(--acc)}
</style></head><body><main>
<h1>crev · {{.Branch}}</h1>
<div class="mut">run {{.Run.ID}} · commit {{.Run.Commit}}{{if .Run.Dirty}} (dirty){{end}} · {{.Run.Timestamp}} · crev {{.Run.CrevVersion}}{{if .Run.Scope}} · scope {{.Run.Scope.Mode}}{{end}}</div>
<div class="kpis">
<div class="kpi"><b>{{.Run.Counts.Total}}</b>findings</div><div class="kpi"><b>{{.Run.Counts.Gating}}</b>gating ({{.Run.FailOn}})</div>
<div class="kpi"><b>{{index .Lifecycle "open"}}</b>open</div><div class="kpi"><b>{{index .Lifecycle "fixed"}}</b>fixed</div>
<div class="kpi"><b>{{index .Lifecycle "reopened"}}</b>reopened</div><div class="kpi"><b>{{len .New}}</b>new this run</div><div class="kpi"><b>{{len .Fixed}}</b>fixed this run</div>
</div>
<h2>Timeline</h2>{{svg .Timeline 1000 120}}
<h2>Findings</h2>
<table><tr><th>Severity</th><th>Rule</th><th>Location</th><th>Message</th><th>Status</th></tr>
{{range .Findings}}<tr><td><span class="sev {{.Severity}}">{{upper .Severity}}</span></td><td><a href="{{.Source.URL}}">{{.RuleID}}</a></td><td><code>{{.Location.Path}}:{{.Location.StartLine}}</code></td><td>{{.Message}}</td><td>{{.Status}}</td></tr>
{{end}}</table>
{{if .Fixed}}<h2>Fixed in this run</h2><table>{{range .Fixed}}<tr><td>{{.RuleID}}</td><td><code>{{.Path}}:{{.Line}}</code></td><td>{{.Message}}</td></tr>{{end}}</table>{{end}}
<p class="mut">Static report (placeholder layout; data contract: crev report --data).</p>
</main></body></html>
`))

// Render writes the HTML.
func Render(w io.Writer, d *Data) error { return tpl.Execute(w, d) }

# crev ui

`crev ui [--port N]` serves a local, read-only web UI over the stored runs. It is built from one embedded
vanilla-JS file (`internal/ui/static/index.html`, about 47.6 KB, about 15.5 KB gzipped) and uses no external assets.

Views (hash routes; every filter is kept in the URL, so links and saved views work):

- `#/` dashboard: the latest run per branch, review, gating and hidden counts, new and fixed since the previous run,
  a trend sparkline, totals per category and severity, and why findings are hidden.
- `#/run/<id|latest>` findings: grouped by file and rule in collapsible groups, with a file tree and faceted
  filters (severity, category, language, pack, rule, CWE, OWASP, trust, new/existing/fixed, hidden reason).
  It also has full-text search, sorting, saved views and 200 rows per page. The detail panel shows a
  highlighted snippet, why the finding is hidden, the AI verdict, the fingerprint, a crev-ignore snippet
  and the rule docs.
- `#/compare?a=&b=&tab=new|fixed|unchanged`, `#/runs`, `#/timeline`.
- `#/rules` and `#/rule/<id>`: a rules browser with pack, language, category, severity, mode, trust and version filters,
  plus per-rule hit stats over the last 50 runs.

Keyboard: `j`/`k` move, `Enter` opens, `/` searches, `Esc` closes, `g d|f|r|u|c|t` jumps to a view, `?` shows help.
The light and dark themes follow the system setting, and the header button toggles them.

Paginated JSON API: `/api/dashboard`, `/api/runs/{id}/findings?offset=&limit=&<filters>`,
`/api/rules?offset=&limit=&sort=hits|severity&fired=1`, `/api/compare?a=&b=&limit=`.

The screenshots in this folder were taken with headless Chrome against a scan of InsecureShop.

// Command ruleupdate is the doc-drift dev tool for the rule catalog (PLAN §7).
//
// For every URL in sources.yaml it fetches the page, normalises it to text (same normalisation
// as tools/rulegen/fetch.py), stores a snapshot under the state dir, and diffs it against the
// previous snapshot sentence by sentence. It then:
//   - verifies that every rule's source.quote still appears on its cited page;
//   - reports changed pages with added/removed sentences, highlighting new deprecation/removal
//     lines ("deprecated", "will be removed", "no longer supported", ...);
//   - optionally (--latest) checks current stable versions against rules/data/latest-versions.yaml.
//
// Output: <state>/report.md and <state>/report.json, a needs-review list for a maintainer. It
// never edits rules. It exits 1 with --fail-on-review when anything needs review.
//
//	go run ./tools/ruleupdate [-sources sources.yaml] [-packs 'rules/packs/*/*.yaml'] [-state .ruleupdate]
//	                          [-only SUBSTR] [-cadence weekly] [-limit N] [-offline] [-latest] [-fail-on-review]
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"html"
	"io"
	"net/http"
	neturl "net/url"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"sync"
	"time"

	"gopkg.in/yaml.v3"
)

type source struct {
	URL      string   `yaml:"url"`
	Cadence  string   `yaml:"cadence"`
	Kind     string   `yaml:"kind"`
	CitedBy  []string `yaml:"cited_by"`
	Ecosys   string   `yaml:"ecosystem"`
	Fetch    string   `yaml:"fetch"`
	Disabled bool     `yaml:"disabled"`
}

type ruleQuote struct {
	ID, URL, Quote, Pack, File string
}

// EditTarget is where a maintainer changes a rule: the hand-edited pack file, or the rulegen spec
// directory for a generated rules/packs/<pack>/<topic>.gen.yaml file.
func EditTarget(file string) string {
	if strings.HasSuffix(file, ".gen.yaml") {
		return "tools/rulegen/specs/ (generates " + filepath.ToSlash(file) + ")"
	}
	return filepath.ToSlash(file)
}

// DraftTarget is the hand-edited file a new rule drafted from a deprecation line on a page belongs
// in: rules/packs/<pack>/migration.yaml of the pack whose rules cite the page.
func DraftTarget(packsDir, pack string) string {
	return filepath.ToSlash(filepath.Join(packsDir, pack, "migration.yaml"))
}

// Snapshot metadata for one URL.
type Snapshot struct {
	URL     string    `json:"url"`
	Status  int       `json:"status"`
	SHA256  string    `json:"sha256"`
	Fetched time.Time `json:"fetched"`
	Chars   int       `json:"chars"`
}

// PageResult is the per-URL outcome.
type PageResult struct {
	URL           string   `json:"url"`
	Status        int      `json:"status"`
	Error         string   `json:"error,omitempty"`
	Changed       bool     `json:"changed"`
	FirstSnapshot bool     `json:"first_snapshot,omitempty"`
	Added         []string `json:"added,omitempty"`
	Removed       []string `json:"removed,omitempty"`
	Deprecations  []string `json:"new_deprecation_lines,omitempty"`
	MissingQuotes []string `json:"missing_quotes,omitempty"` // rule ids
	// EditFiles lists, per missing quote, the file to edit (hand-edited pack file or rulegen spec)
	EditFiles []string `json:"edit_files,omitempty"`
	// DraftFile is the per-pack file where new rules drafted from this page's deprecation lines go
	DraftFile string   `json:"draft_file,omitempty"`
	CitedBy   []string `json:"cited_by,omitempty"`
}

// Report is the full needs-review report.
type Report struct {
	Generated     time.Time       `json:"generated"`
	Checked       int             `json:"checked"`
	Changed       int             `json:"changed"`
	Errors        int             `json:"errors"`
	QuotesChecked int             `json:"quotes_checked"`
	QuotesMissing int             `json:"quotes_missing"`
	Deprecations  int             `json:"new_deprecation_lines"`
	Pages         []*PageResult   `json:"pages"`
	Latest        []LatestVersion `json:"latest,omitempty"`
}

func main() {
	sourcesPath := flag.String("sources", "sources.yaml", "sources registry")
	packs := flag.String("packs", "rules/packs/*/*.yaml", "rule packs (glob) whose source.quote values are verified")
	state := flag.String("state", ".ruleupdate", "snapshot + report directory")
	only := flag.String("only", "", "only URLs containing this substring")
	cadence := flag.String("cadence", "", "only sources with this cadence (daily|weekly|monthly)")
	limit := flag.Int("limit", 0, "check at most N URLs (0 = all)")
	conc := flag.Int("concurrency", 8, "parallel fetches")
	perHost := flag.Int("per-host", 2, "parallel fetches per host (429/503 are retried with backoff)")
	offline := flag.Bool("offline", false, "do not fetch; verify quotes against the stored snapshots")
	latest := flag.Bool("latest", false, "also check latest stable versions against rules/data/latest-versions.yaml")
	latestPath := flag.String("latest-file", "rules/data/latest-versions.yaml", "latest-versions file for -latest")
	failOn := flag.Bool("fail-on-review", false, "exit 1 when anything needs review")
	flag.Parse()

	srcs, err := loadSources(*sourcesPath)
	if err != nil {
		fatal(err)
	}
	quotes, err := loadQuotes(*packs)
	if err != nil {
		fatal(err)
	}
	var sel []source
	for _, s := range srcs {
		if s.Disabled || (*only != "" && !strings.Contains(s.URL, *only)) || (*cadence != "" && s.Cadence != *cadence) {
			continue
		}
		sel = append(sel, s)
	}
	if *limit > 0 && len(sel) > *limit {
		sel = sel[:*limit]
	}
	st := &Store{Dir: *state}
	f := &Fetcher{Client: &http.Client{Timeout: 40 * time.Second}, PerHost: *perHost}
	rep := Run(sel, quotes, st, f, *offline, *conc)
	if *latest {
		rep.Latest = CheckLatest(f.Client, *latestPath)
	}
	if err := WriteReport(*state, rep); err != nil {
		fatal(err)
	}
	fmt.Printf("checked=%d changed=%d errors=%d quotes=%d missing=%d deprecation_lines=%d -> %s\n", rep.Checked, rep.Changed, rep.Errors,
		rep.QuotesChecked, rep.QuotesMissing, rep.Deprecations, filepath.Join(*state, "report.md"))
	if *failOn && rep.NeedsReview() {
		os.Exit(1)
	}
}

func fatal(err error) {
	fmt.Fprintln(os.Stderr, "ruleupdate:", err)
	os.Exit(2)
}

func loadSources(p string) ([]source, error) {
	b, err := os.ReadFile(p)
	if err != nil {
		return nil, err
	}
	var f struct {
		Sources []source `yaml:"sources"`
	}
	if err := yaml.Unmarshal(b, &f); err != nil {
		return nil, err
	}
	return f.Sources, nil
}

func loadQuotes(glob string) (map[string][]ruleQuote, error) {
	files, err := filepath.Glob(glob)
	if err != nil {
		return nil, err
	}
	out := map[string][]ruleQuote{}
	for _, fn := range files {
		b, err := os.ReadFile(fn)
		if err != nil {
			return nil, err
		}
		var p struct {
			Pack  string `yaml:"pack"`
			Rules []struct {
				ID     string `yaml:"id"`
				Source struct {
					URL   string `yaml:"url"`
					Quote string `yaml:"quote"`
				} `yaml:"source"`
			} `yaml:"rules"`
		}
		if err := yaml.Unmarshal(b, &p); err != nil {
			return nil, fmt.Errorf("%s: %w", fn, err)
		}
		for _, r := range p.Rules {
			if r.Source.URL != "" {
				out[r.Source.URL] = append(out[r.Source.URL], ruleQuote{ID: r.ID, URL: r.Source.URL, Quote: r.Source.Quote, Pack: p.Pack, File: fn})
			}
		}
	}
	return out, nil
}

// ---------------------------------------------------------------- fetching and normalisation

// Fetcher downloads pages: one request per page (URL fragments share it), at most PerHost
// concurrent requests per host, and retries with backoff on 429/503.
type Fetcher struct {
	Client  *http.Client
	PerHost int
	Backoff time.Duration // first retry delay (default 2s)

	mu    sync.Mutex
	hosts map[string]chan struct{}
	pages map[string]*pageEntry
}

type pageEntry struct {
	once   sync.Once
	status int
	body   []byte
	err    error
}

// Get returns the HTTP status and body of url (fragment stripped).
func (f *Fetcher) Get(url string) (int, []byte, error) {
	page, _, _ := strings.Cut(url, "#")
	f.mu.Lock()
	if f.pages == nil {
		f.pages, f.hosts = map[string]*pageEntry{}, map[string]chan struct{}{}
	}
	e := f.pages[page]
	if e == nil {
		e = &pageEntry{}
		f.pages[page] = e
	}
	f.mu.Unlock()
	e.once.Do(func() { e.status, e.body, e.err = f.fetch(page) })
	return e.status, e.body, e.err
}

func (f *Fetcher) fetch(page string) (int, []byte, error) {
	host := page
	if u, err := neturl.Parse(page); err == nil {
		host = u.Host
	}
	f.mu.Lock()
	sem := f.hosts[host]
	if sem == nil {
		n := f.PerHost
		if n <= 0 {
			n = 2
		}
		sem = make(chan struct{}, n)
		f.hosts[host] = sem
	}
	f.mu.Unlock()
	sem <- struct{}{}
	defer func() { <-sem }()
	delay := f.Backoff
	if delay == 0 {
		delay = 2 * time.Second
	}
	for attempt := 0; ; attempt++ {
		st, b, wait, err := f.once(page)
		if (st == 429 || st == 503) && attempt < 3 {
			if wait <= 0 || wait > 20*time.Second {
				wait = delay
			}
			time.Sleep(wait)
			delay *= 2
			continue
		}
		return st, b, err
	}
}

func (f *Fetcher) once(page string) (int, []byte, time.Duration, error) {
	if u, err := neturl.Parse(page); err == nil && strings.Contains(u.Path, "/..") {
		page = u.ResolveReference(&neturl.URL{Path: u.Path}).String() // resolve dot segments like browsers/curl
	}
	req, err := http.NewRequest("GET", page, nil)
	if err != nil {
		return 0, nil, 0, err
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (crev ruleupdate)")
	resp, err := f.Client.Do(req)
	if err != nil {
		return 0, nil, 0, err
	}
	defer resp.Body.Close()
	var wait time.Duration
	if ra, err := strconv.Atoi(resp.Header.Get("Retry-After")); err == nil {
		wait = time.Duration(ra) * time.Second
	}
	b, err := io.ReadAll(io.LimitReader(resp.Body, 32<<20))
	return resp.StatusCode, b, wait, err
}

var (
	scriptRe = regexp.MustCompile(`(?is)<(script|style)\b.*?</(script|style)>`)
	tagRe    = regexp.MustCompile(`<[^>]+>`)
	spaceRe  = regexp.MustCompile(`\s+`)
)

// Normalize turns HTML (or text) into tag-stripped, whitespace-collapsed text, like fetch.py.
func Normalize(b []byte) string {
	s := scriptRe.ReplaceAllString(string(b), " ")
	s = html.UnescapeString(tagRe.ReplaceAllString(s, " "))
	return strings.TrimSpace(spaceRe.ReplaceAllString(s, " "))
}

var (
	hyphenRe = regexp.MustCompile(`(\w)- (\w)`)
	punctRe  = regexp.MustCompile(`\s+([,.;:)])`)
	parenRe  = regexp.MustCompile(`\(\s+`)
)

// norm is fetch.norm: the comparison form for quotes.
func norm(s string) string {
	r := strings.NewReplacer("\u00a0", " ", "’", "'", "“", `"`, "”", `"`)
	s = strings.ToLower(strings.TrimSpace(spaceRe.ReplaceAllString(r.Replace(s), " ")))
	s = hyphenRe.ReplaceAllString(s, "$1-$2")
	return spaceRe.ReplaceAllString(punctRe.ReplaceAllString(parenRe.ReplaceAllString(s, "("), "$1"), " ")
}

// QuoteOK reports whether quote appears in text (normalised comparison).
func QuoteOK(text, quote string) bool { return strings.Contains(norm(text), norm(quote)) }

var sentEnd = regexp.MustCompile(`[.!?]\s+`)

// Sentences splits normalised text into de-duplicated sentence-ish units (>= 20 chars).
func Sentences(text string) []string {
	var out []string
	seen := map[string]bool{}
	last := 0
	add := func(s string) {
		s = strings.TrimSpace(s)
		if len(s) >= 20 && !seen[s] {
			seen[s] = true
			out = append(out, s)
		}
	}
	for _, m := range sentEnd.FindAllStringIndex(text, -1) {
		add(text[last : m[0]+1])
		last = m[1]
	}
	add(text[last:])
	return out
}

// Diff returns sentences added in cur and removed from prev (order of appearance).
func Diff(prev, cur string) (added, removed []string) {
	ps, cs := Sentences(prev), Sentences(cur)
	pm, cm := map[string]bool{}, map[string]bool{}
	for _, s := range ps {
		pm[s] = true
	}
	for _, s := range cs {
		cm[s] = true
		if !pm[s] {
			added = append(added, s)
		}
	}
	for _, s := range ps {
		if !cm[s] {
			removed = append(removed, s)
		}
	}
	return
}

var deprecRe = regexp.MustCompile(`(?i)\b(deprecat\w*|will be removed|(?:was|were|is|are|been) removed|removed in|no longer (?:supported|available|recommended)|end[- ]of[- ]life|\bEOL\b|obsolete|superseded|discouraged|breaking change|sunset)`)

// DeprecationLines filters sentences mentioning deprecation/removal.
func DeprecationLines(ss []string) []string {
	var out []string
	for _, s := range ss {
		if deprecRe.MatchString(s) {
			out = append(out, truncate(s, 400))
		}
	}
	return out
}

func truncate(s string, n int) string {
	if len(s) > n {
		return s[:n] + "…"
	}
	return s
}

// ---------------------------------------------------------------- snapshots

// Store keeps the latest normalised snapshot per URL.
type Store struct{ Dir string }

func key(url string) string {
	url, _, _ = strings.Cut(url, "#") // fragments share the page snapshot
	h := sha256.Sum256([]byte(url))
	return hex.EncodeToString(h[:10])
}

func (s *Store) paths(url string) (txt, meta string) {
	k := key(url)
	return filepath.Join(s.Dir, "snapshots", k+".txt"), filepath.Join(s.Dir, "snapshots", k+".json")
}

// Load returns the previous snapshot text and metadata (ok=false when none).
func (s *Store) Load(url string) (string, Snapshot, bool) {
	t, m := s.paths(url)
	b, err := os.ReadFile(t)
	if err != nil {
		return "", Snapshot{}, false
	}
	var meta Snapshot
	if mb, err := os.ReadFile(m); err == nil {
		_ = json.Unmarshal(mb, &meta)
	}
	return string(b), meta, true
}

// Save writes the snapshot; the previous one is kept as .prev.txt for manual diffing.
func (s *Store) Save(url, text string, status int) error {
	t, m := s.paths(url)
	if err := os.MkdirAll(filepath.Dir(t), 0o755); err != nil {
		return err
	}
	if _, err := os.Stat(t); err == nil {
		_ = os.Rename(t, strings.TrimSuffix(t, ".txt")+".prev.txt")
	}
	if err := os.WriteFile(t, []byte(text), 0o644); err != nil {
		return err
	}
	h := sha256.Sum256([]byte(text))
	mb, _ := json.MarshalIndent(Snapshot{URL: url, Status: status, SHA256: hex.EncodeToString(h[:]), Fetched: time.Now().UTC(), Chars: len(text)}, "", "  ")
	return os.WriteFile(m, mb, 0o644)
}

// ---------------------------------------------------------------- run

// Run checks every source and returns the report.
func Run(srcs []source, quotes map[string][]ruleQuote, st *Store, f *Fetcher, offline bool, conc int) *Report {
	if conc < 1 {
		conc = 1
	}
	rep := &Report{Generated: time.Now().UTC()}
	// One check per page: URLs that differ only by #fragment share the fetch and the snapshot.
	byPage := map[string]int{}
	var pages []source
	pq := map[string][]ruleQuote{}
	for _, s := range srcs {
		page, _, _ := strings.Cut(s.URL, "#")
		pq[page] = append(pq[page], quotes[s.URL]...)
		if i, ok := byPage[page]; ok {
			pages[i].CitedBy = append(pages[i].CitedBy, s.CitedBy...)
			continue
		}
		byPage[page] = len(pages)
		s.URL = page
		s.CitedBy = append([]string{}, s.CitedBy...)
		pages = append(pages, s)
	}
	srcs, quotes = pages, pq
	res := make([]*PageResult, len(srcs))
	var wg sync.WaitGroup
	sem := make(chan struct{}, conc)
	for i, s := range srcs {
		wg.Add(1)
		go func(i int, s source) {
			defer wg.Done()
			sem <- struct{}{}
			defer func() { <-sem }()
			res[i] = checkOne(s, quotes[s.URL], st, f, offline)
		}(i, s)
	}
	wg.Wait()
	for _, r := range res {
		rep.Checked++
		if r.Error != "" || (r.Status != 0 && r.Status != 200) {
			rep.Errors++
		}
		if r.Changed {
			rep.Changed++
		}
		rep.QuotesMissing += len(r.MissingQuotes)
		rep.Deprecations += len(r.Deprecations)
		rep.QuotesChecked += len(quotes[r.URL])
		rep.Pages = append(rep.Pages, r)
	}
	slices.SortStableFunc(rep.Pages, func(a, b *PageResult) int { return strings.Compare(a.URL, b.URL) })
	return rep
}

func checkOne(s source, qs []ruleQuote, st *Store, f *Fetcher, offline bool) *PageResult {
	r := &PageResult{URL: s.URL, CitedBy: s.CitedBy}
	prev, _, had := st.Load(s.URL)
	var cur string
	if offline {
		if !had {
			r.Error = "no snapshot (run without -offline first)"
			return r
		}
		cur, r.Status = prev, 200
	} else {
		status, body, err := f.Get(s.URL)
		r.Status = status
		if err != nil {
			r.Error = err.Error()
			return r
		}
		if status != 200 {
			r.Error = fmt.Sprintf("HTTP %d", status)
			return r
		}
		cur = Normalize(body)
		if had && prev != cur {
			r.Changed = true
			r.Added, r.Removed = Diff(prev, cur)
			r.Deprecations = DeprecationLines(r.Added)
			r.Added, r.Removed = capList(r.Added, 40), capList(r.Removed, 40)
		}
		r.FirstSnapshot = !had
		if err := st.Save(s.URL, cur, status); err != nil {
			r.Error = err.Error()
		}
	}
	for _, q := range qs {
		if q.Quote != "" && !QuoteOK(cur, q.Quote) {
			r.MissingQuotes = append(r.MissingQuotes, q.ID)
			if t := EditTarget(q.File); !slices.Contains(r.EditFiles, t) {
				r.EditFiles = append(r.EditFiles, t)
			}
		}
	}
	if len(r.Deprecations) > 0 && len(qs) > 0 && qs[0].File != "" {
		r.DraftFile = DraftTarget(filepath.Dir(filepath.Dir(qs[0].File)), qs[0].Pack)
	}
	return r
}

func capList(ss []string, n int) []string {
	for i := range ss {
		ss[i] = truncate(ss[i], 300)
	}
	if len(ss) > n {
		return append(ss[:n], fmt.Sprintf("… %d more", len(ss)-n))
	}
	return ss
}

// NeedsReview reports whether a maintainer has something to look at.
func (r *Report) NeedsReview() bool {
	if r.Changed > 0 || r.Errors > 0 || r.QuotesMissing > 0 {
		return true
	}
	for _, l := range r.Latest {
		if l.Outdated {
			return true
		}
	}
	return false
}

// WriteReport writes report.json and report.md.
func WriteReport(dir string, r *Report) error {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	b, _ := json.MarshalIndent(r, "", "  ")
	if err := os.WriteFile(filepath.Join(dir, "report.json"), b, 0o644); err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(dir, "report.md"), []byte(Markdown(r)), 0o644)
}

// Markdown renders the needs-review report.
func Markdown(r *Report) string {
	var b strings.Builder
	fmt.Fprintf(&b, "# Rule source review (%s)\n\n", r.Generated.Format("2006-01-02 15:04 UTC"))
	fmt.Fprintf(&b, "Checked %d page(s): %d changed, %d error(s); %d/%d rule quote(s) missing; %d new deprecation/removal line(s).\n\n",
		r.Checked, r.Changed, r.Errors, r.QuotesMissing, r.QuotesChecked, r.Deprecations)
	if !r.NeedsReview() {
		b.WriteString("Nothing needs review.\n")
	}
	section := func(title string, pick func(*PageResult) bool, body func(*PageResult)) {
		var ps []*PageResult
		for _, p := range r.Pages {
			if pick(p) {
				ps = append(ps, p)
			}
		}
		if len(ps) == 0 {
			return
		}
		fmt.Fprintf(&b, "## %s (%d)\n\n", title, len(ps))
		for _, p := range ps {
			body(p)
		}
		b.WriteString("\n")
	}
	section("Missing rule quotes: citation no longer supported by the page", func(p *PageResult) bool { return len(p.MissingQuotes) > 0 }, func(p *PageResult) {
		fmt.Fprintf(&b, "- %s: %s (edit: %s)\n", p.URL, strings.Join(p.MissingQuotes, ", "), strings.Join(p.EditFiles, "; "))
	})
	section("New deprecation / removal lines", func(p *PageResult) bool { return len(p.Deprecations) > 0 }, func(p *PageResult) {
		fmt.Fprintf(&b, "- %s (cited by %d rule(s); new rules go in %s)\n", p.URL, len(p.CitedBy), p.DraftFile)
		for _, d := range p.Deprecations {
			fmt.Fprintf(&b, "  - %s\n", d)
		}
	})
	section("Changed pages", func(p *PageResult) bool { return p.Changed }, func(p *PageResult) {
		fmt.Fprintf(&b, "- %s: +%d / -%d sentence(s); cited by %s\n", p.URL, len(p.Added), len(p.Removed), strings.Join(firstN(p.CitedBy, 8), ", "))
	})
	section("Fetch errors", func(p *PageResult) bool { return p.Error != "" }, func(p *PageResult) {
		fmt.Fprintf(&b, "- %s: %s\n", p.URL, p.Error)
	})
	if len(r.Latest) > 0 {
		b.WriteString("## Latest versions\n\n| dimension | catalog | upstream | source |\n|---|---|---|---|\n")
		for _, l := range r.Latest {
			mark := ""
			if l.Outdated {
				mark = " **update**"
			}
			if l.Error != "" {
				mark = " (" + l.Error + ")"
			}
			fmt.Fprintf(&b, "| %s | %s | %s%s | %s |\n", l.Dim, l.Catalog, l.Upstream, mark, l.Source)
		}
	}
	return b.String()
}

func firstN(s []string, n int) []string {
	if len(s) > n {
		return append(append([]string{}, s[:n]...), fmt.Sprintf("+%d", len(s)-n))
	}
	if len(s) == 0 {
		return []string{"(none)"}
	}
	return s
}

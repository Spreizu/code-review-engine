package sca

import (
	"archive/zip"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"sync"
	"time"
)

// Vuln is the subset of the OSV schema (https://ossf.github.io/osv-schema/) crev uses.
type Vuln struct {
	ID        string   `json:"id"`
	Summary   string   `json:"summary"`
	Details   string   `json:"details"`
	Aliases   []string `json:"aliases"`
	Modified  string   `json:"modified"`
	Published string   `json:"published"`
	Withdrawn string   `json:"withdrawn"`
	Severity  []struct {
		Type  string `json:"type"`
		Score string `json:"score"`
	} `json:"severity"`
	Affected         []Affected `json:"affected"`
	DatabaseSpecific struct {
		Severity string   `json:"severity"`
		CWEIDs   []string `json:"cwe_ids"`
	} `json:"database_specific"`
}

type Affected struct {
	Package struct {
		Ecosystem string `json:"ecosystem"`
		Name      string `json:"name"`
	} `json:"package"`
	Severity []struct {
		Type  string `json:"type"`
		Score string `json:"score"`
	} `json:"severity"`
	Ranges []struct {
		Type   string `json:"type"`
		Events []struct {
			Introduced   string `json:"introduced,omitempty"`
			Fixed        string `json:"fixed,omitempty"`
			LastAffected string `json:"last_affected,omitempty"`
			Limit        string `json:"limit,omitempty"`
		} `json:"events"`
	} `json:"ranges"`
	Versions []string `json:"versions"`
}

// baseEco strips an ecosystem suffix ("Debian:12" -> "Debian"); crev's ecosystems have none.
func baseEco(e string) string {
	if i := strings.IndexByte(e, ':'); i >= 0 {
		return e[:i]
	}
	return e
}

func samePkg(eco, a, b string) bool {
	if eco == EcoPyPI {
		return PyName(a) == PyName(b)
	}
	if eco == EcoPackagist {
		return strings.EqualFold(a, b)
	}
	return a == b
}

// interval is one affected range [Introduced, Fixed) or [Introduced, LastAffected].
type interval struct{ Introduced, Fixed, LastAffected string }

func (a Affected) intervals() []interval {
	var out []interval
	for _, r := range a.Ranges {
		if r.Type != "SEMVER" && r.Type != "ECOSYSTEM" {
			continue // GIT ranges need commit graphs
		}
		var cur *interval
		for _, e := range r.Events {
			switch {
			case e.Introduced != "":
				out = append(out, interval{Introduced: e.Introduced})
				cur = &out[len(out)-1]
			case e.Fixed != "" && cur != nil:
				cur.Fixed, cur = e.Fixed, nil
			case e.LastAffected != "" && cur != nil:
				cur.LastAffected, cur = e.LastAffected, nil
			case e.Limit != "" && cur != nil:
				cur.Fixed, cur = e.Limit, nil
			}
		}
	}
	return out
}

func (iv interval) contains(eco, v string) bool {
	if iv.Introduced != "0" && Compare(eco, v, iv.Introduced) < 0 {
		return false
	}
	if iv.Fixed != "" && Compare(eco, v, iv.Fixed) >= 0 {
		return false
	}
	if iv.LastAffected != "" && Compare(eco, v, iv.LastAffected) > 0 {
		return false
	}
	return true
}

func (iv interval) String() string {
	s := ">=" + iv.Introduced
	if iv.Introduced == "0" {
		s = ""
	}
	switch {
	case iv.Fixed != "":
		s = strings.TrimSpace(s + " <" + iv.Fixed)
	case iv.LastAffected != "":
		s = strings.TrimSpace(s + " <=" + iv.LastAffected)
	}
	if s == "" {
		return "all versions"
	}
	return s
}

// Match reports whether p is affected by v, with the affected ranges of p's package and the
// first fixed version above p.Version ("" if none is published).
func Match(v *Vuln, p Package) (ok bool, ranges []string, fixed string) {
	if v.Withdrawn != "" {
		return false, nil, ""
	}
	for _, a := range v.Affected {
		if baseEco(a.Package.Ecosystem) != p.Ecosystem || !samePkg(p.Ecosystem, a.Package.Name, p.Name) {
			continue
		}
		hit := false
		for _, x := range a.Versions {
			if Compare(p.Ecosystem, x, p.Version) == 0 {
				hit = true
			}
		}
		for _, iv := range a.intervals() {
			ranges = append(ranges, iv.String())
			if iv.contains(p.Ecosystem, p.Version) {
				hit = true
				if iv.Fixed != "" && (fixed == "" || Compare(p.Ecosystem, iv.Fixed, fixed) < 0) {
					fixed = iv.Fixed
				}
			}
		}
		if hit {
			ok = true
		}
	}
	if ok && fixed == "" { // listed by version only: lowest fixed event above our version
		for _, a := range v.Affected {
			if baseEco(a.Package.Ecosystem) != p.Ecosystem || !samePkg(p.Ecosystem, a.Package.Name, p.Name) {
				continue
			}
			for _, iv := range a.intervals() {
				if iv.Fixed != "" && Compare(p.Ecosystem, iv.Fixed, p.Version) > 0 && (fixed == "" || Compare(p.Ecosystem, iv.Fixed, fixed) < 0) {
					fixed = iv.Fixed
				}
			}
		}
	}
	return ok, ranges, fixed
}

// ---- online: api.osv.dev ----

// Client queries the OSV.dev API (https://google.github.io/osv.dev/api/).
type Client struct {
	BaseURL string // default https://api.osv.dev
	HTTP    *http.Client
	mu      sync.Mutex
	cache   map[string]*Vuln
}

func (c *Client) base() string {
	if c.BaseURL == "" {
		return "https://api.osv.dev"
	}
	return strings.TrimRight(c.BaseURL, "/")
}

func (c *Client) http() *http.Client {
	if c.HTTP == nil {
		return &http.Client{Timeout: 30 * time.Second}
	}
	return c.HTTP
}

const batchSize = 1000 // querybatch limit

// Query returns the advisories affecting each package (index-aligned with pkgs).
func (c *Client) Query(ctx context.Context, pkgs []Package) ([][]*Vuln, error) {
	ids := make([][]string, len(pkgs))
	for s := 0; s < len(pkgs); s += batchSize {
		e := min(s+batchSize, len(pkgs))
		type q struct {
			Package struct {
				Name      string `json:"name"`
				Ecosystem string `json:"ecosystem"`
			} `json:"package"`
			Version   string `json:"version"`
			PageToken string `json:"page_token,omitempty"`
		}
		var body struct {
			Queries []q `json:"queries"`
		}
		for _, p := range pkgs[s:e] {
			var x q
			x.Package.Name, x.Package.Ecosystem, x.Version = p.Name, p.Ecosystem, p.Version
			body.Queries = append(body.Queries, x)
		}
		var resp struct {
			Results []struct {
				Vulns []struct {
					ID string `json:"id"`
				} `json:"vulns"`
				NextPageToken string `json:"next_page_token"`
			} `json:"results"`
		}
		if err := c.post(ctx, "/v1/querybatch", body, &resp); err != nil {
			return nil, err
		}
		for i, r := range resp.Results {
			if s+i >= len(pkgs) {
				break
			}
			for _, v := range r.Vulns {
				ids[s+i] = append(ids[s+i], v.ID)
			}
			if r.NextPageToken != "" { // rare: more than one page for a package; query it alone
				more, err := c.queryAll(ctx, pkgs[s+i])
				if err != nil {
					return nil, err
				}
				ids[s+i] = append(ids[s+i], more...)
			}
		}
	}
	// details (querybatch returns ids only)
	uniq := map[string]bool{}
	for _, l := range ids {
		for _, id := range l {
			uniq[id] = true
		}
	}
	if err := c.fetch(ctx, uniq); err != nil {
		return nil, err
	}
	out := make([][]*Vuln, len(pkgs))
	for i, l := range ids {
		seen := map[string]bool{}
		for _, id := range l {
			if v := c.cache[id]; v != nil && !seen[id] {
				seen[id] = true
				out[i] = append(out[i], v)
			}
		}
	}
	return out, nil
}

func (c *Client) queryAll(ctx context.Context, p Package) ([]string, error) {
	var ids []string
	token := ""
	for page := 0; page < 20; page++ {
		body := map[string]any{"package": map[string]string{"name": p.Name, "ecosystem": p.Ecosystem}, "version": p.Version}
		if token != "" {
			body["page_token"] = token
		}
		var resp struct {
			Vulns []struct {
				ID string `json:"id"`
			} `json:"vulns"`
			NextPageToken string `json:"next_page_token"`
		}
		if err := c.post(ctx, "/v1/query", body, &resp); err != nil {
			return nil, err
		}
		for _, v := range resp.Vulns {
			ids = append(ids, v.ID)
		}
		if token = resp.NextPageToken; token == "" {
			break
		}
	}
	return ids, nil
}

func (c *Client) fetch(ctx context.Context, ids map[string]bool) error {
	c.mu.Lock()
	if c.cache == nil {
		c.cache = map[string]*Vuln{}
	}
	var todo []string
	for id := range ids {
		if c.cache[id] == nil {
			todo = append(todo, id)
		}
	}
	c.mu.Unlock()
	slices.Sort(todo)
	sem := make(chan struct{}, 8)
	var wg sync.WaitGroup
	var firstErr error
	var emu sync.Mutex
	for _, id := range todo {
		wg.Add(1)
		sem <- struct{}{}
		go func(id string) {
			defer wg.Done()
			defer func() { <-sem }()
			var v Vuln
			if err := c.get(ctx, "/v1/vulns/"+url.PathEscape(id), &v); err != nil {
				emu.Lock()
				if firstErr == nil {
					firstErr = err
				}
				emu.Unlock()
				return
			}
			c.mu.Lock()
			c.cache[id] = &v
			c.mu.Unlock()
		}(id)
	}
	wg.Wait()
	return firstErr
}

func (c *Client) post(ctx context.Context, path string, body, out any) error {
	b, _ := json.Marshal(body)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.base()+path, bytes.NewReader(b))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	return c.do(req, out)
}

func (c *Client) get(ctx context.Context, path string, out any) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.base()+path, nil)
	if err != nil {
		return err
	}
	return c.do(req, out)
}

func (c *Client) do(req *http.Request, out any) error {
	req.Header.Set("User-Agent", "crev-sca")
	resp, err := c.http().Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(io.LimitReader(resp.Body, 512))
		return fmt.Errorf("osv %s: %s %s", req.URL.Path, resp.Status, strings.TrimSpace(string(b)))
	}
	return json.NewDecoder(resp.Body).Decode(out)
}

// ---- offline: per-ecosystem exports ----

// ExportURL is the OSV per-ecosystem database export
// (https://google.github.io/osv.dev/data/#data-dumps).
const ExportURL = "https://osv-vulnerabilities.storage.googleapis.com/%s/all.zip"

// Meta records when an ecosystem database was downloaded.
type Meta struct {
	Ecosystem  string    `json:"ecosystem"`
	Updated    time.Time `json:"updated"`
	Source     string    `json:"source"`
	Bytes      int64     `json:"bytes"`
	Advisories int       `json:"advisories"`
}

func ecoDir(dir, eco string) string { return filepath.Join(dir, eco) }

// Update downloads the export of each ecosystem into dir/<ecosystem>/all.zip (atomically).
func Update(ctx context.Context, dir string, ecos []string, hc *http.Client, urlFmt string) ([]Meta, error) {
	if hc == nil {
		hc = &http.Client{Timeout: 30 * time.Minute}
	}
	if urlFmt == "" {
		urlFmt = ExportURL
	}
	var metas []Meta
	for _, eco := range ecos {
		d := ecoDir(dir, eco)
		if err := os.MkdirAll(d, 0o755); err != nil {
			return metas, err
		}
		src := fmt.Sprintf(urlFmt, url.PathEscape(eco))
		req, err := http.NewRequestWithContext(ctx, http.MethodGet, src, nil)
		if err != nil {
			return metas, err
		}
		req.Header.Set("User-Agent", "crev-sca")
		resp, err := hc.Do(req)
		if err != nil {
			return metas, fmt.Errorf("%s: %w", eco, err)
		}
		if resp.StatusCode != http.StatusOK {
			resp.Body.Close()
			return metas, fmt.Errorf("%s: GET %s: %s", eco, src, resp.Status)
		}
		tmp, err := os.CreateTemp(d, "all-*.zip.tmp")
		if err != nil {
			resp.Body.Close()
			return metas, err
		}
		n, err := io.Copy(tmp, resp.Body)
		resp.Body.Close()
		tmp.Close()
		if err != nil {
			os.Remove(tmp.Name())
			return metas, fmt.Errorf("%s: %w", eco, err)
		}
		zr, err := zip.OpenReader(tmp.Name())
		if err != nil {
			os.Remove(tmp.Name())
			return metas, fmt.Errorf("%s: downloaded file is not a zip: %w", eco, err)
		}
		count := len(zr.File)
		zr.Close()
		if err := os.Rename(tmp.Name(), filepath.Join(d, "all.zip")); err != nil {
			return metas, err
		}
		m := Meta{Ecosystem: eco, Updated: time.Now().UTC(), Source: src, Bytes: n, Advisories: count}
		b, _ := json.MarshalIndent(m, "", "  ")
		if err := os.WriteFile(filepath.Join(d, "meta.json"), b, 0o644); err != nil {
			return metas, err
		}
		metas = append(metas, m)
	}
	return metas, nil
}

// ReadMeta returns the download metadata of an ecosystem database (ok false when absent).
func ReadMeta(dir, eco string) (Meta, bool) {
	var m Meta
	b, err := os.ReadFile(filepath.Join(ecoDir(dir, eco), "meta.json"))
	if err != nil || json.Unmarshal(b, &m) != nil {
		return m, false
	}
	if _, err := os.Stat(filepath.Join(ecoDir(dir, eco), "all.zip")); err != nil {
		return m, false
	}
	return m, true
}

// Offline matches packages against the downloaded exports.
type Offline struct{ Dir string }

// Query returns the advisories affecting each package (index-aligned with pkgs); missing
// ecosystem databases are reported in missing.
func (o Offline) Query(pkgs []Package) (out [][]*Vuln, missing []string, err error) {
	out = make([][]*Vuln, len(pkgs))
	byEco := map[string]map[string][]int{} // eco -> normalised name -> package indexes
	for i, p := range pkgs {
		if byEco[p.Ecosystem] == nil {
			byEco[p.Ecosystem] = map[string][]int{}
		}
		n := normName(p.Ecosystem, p.Name)
		byEco[p.Ecosystem][n] = append(byEco[p.Ecosystem][n], i)
	}
	ecos := make([]string, 0, len(byEco))
	for e := range byEco {
		ecos = append(ecos, e)
	}
	slices.Sort(ecos)
	for _, eco := range ecos {
		zr, err := zip.OpenReader(filepath.Join(ecoDir(o.Dir, eco), "all.zip"))
		if err != nil {
			missing = append(missing, eco)
			continue
		}
		want := byEco[eco]
		for _, f := range zr.File {
			if !strings.HasSuffix(f.Name, ".json") {
				continue
			}
			rc, err := f.Open()
			if err != nil {
				continue
			}
			b, err := io.ReadAll(rc)
			rc.Close()
			if err != nil {
				continue
			}
			// cheap pre-filter on the raw bytes before decoding
			hit := false
			for n := range want {
				if bytes.Contains(bytes.ToLower(b), []byte(strings.ToLower(n))) {
					hit = true
					break
				}
			}
			if !hit && eco != EcoPyPI {
				continue
			}
			var v Vuln
			if json.Unmarshal(b, &v) != nil {
				continue
			}
			for _, a := range v.Affected {
				if baseEco(a.Package.Ecosystem) != eco {
					continue
				}
				for _, i := range want[normName(eco, a.Package.Name)] {
					if ok, _, _ := Match(&v, pkgs[i]); ok && !containsID(out[i], v.ID) {
						vv := v
						out[i] = append(out[i], &vv)
					}
				}
			}
		}
		zr.Close()
	}
	return out, missing, nil
}

func normName(eco, n string) string {
	switch eco {
	case EcoPyPI:
		return PyName(n)
	case EcoPackagist:
		return strings.ToLower(n)
	}
	return n
}

func containsID(vs []*Vuln, id string) bool {
	return slices.ContainsFunc(vs, func(v *Vuln) bool { return v.ID == id })
}

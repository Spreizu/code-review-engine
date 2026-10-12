package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/elmo/code-review-engine/internal/config"
	"github.com/elmo/code-review-engine/internal/engine"
	"github.com/elmo/code-review-engine/internal/findings"
	"github.com/elmo/code-review-engine/internal/sca"
	"github.com/elmo/code-review-engine/internal/scope"
)

// vulndbDir is the offline database directory (config vulndb.dir, default user cache).
func (e *env) vulndbDir() string {
	if d := e.cfg.VulnDB.Dir; d != "" {
		return e.abs(d)
	}
	return sca.DefaultDir()
}

// runSCA adds dependency-vulnerability findings (OSV.dev) to the report.
func (e *env) runSCA(rep *findings.Report, mode string, sc *scope.Scope, quiet, noGitignore, noDefaultExcludes bool) {
	if mode == "" {
		mode = e.cfg.VulnDB.Mode
	}
	if mode == "off" {
		return
	}
	o := sca.Options{Root: e.root, Mode: mode, Dir: e.vulndbDir(), MaxAge: time.Duration(e.cfg.VulnDB.MaxAgeDays) * 24 * time.Hour,
		APIURL: e.cfg.VulnDB.APIURL, Timeout: time.Duration(e.cfg.VulnDB.TimeoutSeconds) * time.Second,
		Skip: engine.PathFilter(e.root, e.cfg.Ignore, noGitignore || !config.On(e.cfg.Gitignore), noDefaultExcludes || !config.On(e.cfg.DefaultExcludes))}

	if sc.IsDiff() {
		o.InScope = sc.FileInScope // diff scans: only lockfiles the change touches
	}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()
	res, err := sca.Scan(ctx, o)
	if err != nil {
		rep.Errors = append(rep.Errors, "sca: "+err.Error())
		return
	}
	for _, w := range res.Warnings {
		rep.Errors = append(rep.Errors, w)
		if !quiet {
			fmt.Fprintln(os.Stderr, "crev:", w)
		}
	}
	if rep.Stats == nil {
		rep.Stats = map[string]int{}
	}
	rep.Stats["sca_packages"] = res.Packages
	rep.Stats["sca_vulnerable_packages"] = res.Vulnerable
	rep.Stats["sca_findings"] = len(res.Findings)
	rep.Findings = append(rep.Findings, res.Findings...)
}

func cmdVulndb(args []string) error {
	const use = "usage: crev vulndb update [--ecosystems npm,PyPI,Go,Packagist,Maven] [--dir DIR] | status [--dir DIR]"
	if len(args) == 0 {
		return fail(2, use)
	}
	fs := flag.NewFlagSet("vulndb", flag.ContinueOnError)
	ecos := fs.String("ecosystems", strings.Join(sca.Ecosystems, ","), "OSV ecosystems to download")
	dir := fs.String("dir", "", "database directory (default vulndb.dir from .crev.yaml, else the user cache)")
	root := fs.String("root", ".", "project root (for .crev.yaml)")
	cfgPath := fs.String("config", "", "config file (default <root>/.crev.yaml)")
	if err := parseInterspersed(fs, args[1:]); err != nil {
		return fail(2, "%v", err)
	}
	e, err := setup(*root, *cfgPath, "", "")
	if err != nil {
		return err
	}
	d := *dir
	if d == "" {
		d = e.vulndbDir()
	}
	var list []string
	for _, x := range strings.Split(*ecos, ",") {
		if x = strings.TrimSpace(x); x != "" {
			list = append(list, x)
		}
	}
	switch args[0] {
	case "update":
		fmt.Fprintf(os.Stderr, "downloading OSV databases (%s) into %s\n", strings.Join(list, ", "), d)
		metas, err := sca.Update(context.Background(), d, list, nil, "")
		for _, m := range metas {
			fmt.Printf("%-10s %6d advisories  %5.1f MB  %s\n", m.Ecosystem, m.Advisories, float64(m.Bytes)/1e6, m.Updated.Format(time.RFC3339))
		}
		if err != nil {
			return fail(3, "vulndb update: %v", err)
		}
		return nil
	case "status":
		for _, eco := range list {
			m, ok := sca.ReadMeta(d, eco)
			if !ok {
				fmt.Printf("%-10s missing (run crev vulndb update)\n", eco)
				continue
			}
			age := time.Since(m.Updated)
			stale := ""
			if age > time.Duration(e.cfg.VulnDB.MaxAgeDays)*24*time.Hour {
				stale = "  STALE"
			}
			fmt.Printf("%-10s %6d advisories  updated %s (%d days ago)%s\n", eco, m.Advisories, m.Updated.Format("2006-01-02"), int(age.Hours()/24), stale)
		}
		return nil
	}
	return fail(2, "unknown vulndb subcommand %q\n%s", args[0], use)
}

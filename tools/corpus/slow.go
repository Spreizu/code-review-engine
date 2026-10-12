package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"time"

	"github.com/elmo/code-review-engine/internal/engine"
	"github.com/elmo/code-review-engine/internal/rules"
	"github.com/elmo/code-review-engine/internal/versions"
)

// slow times every rule on one directory (copy the slow file into an empty dir): the corpus
// run flags repositories that take minutes, and this finds the rule responsible.
func slow(args []string) {
	fs := flag.NewFlagSet("slow", flag.ExitOnError)
	root := fs.String("dir", "", "directory to scan")
	top := fs.Int("n", 15, "rules to show")
	fs.Parse(args)
	rs, err := rules.LoadFS(os.DirFS("rules"), "packs/*/*.yaml")
	die(err)
	die(rules.ApplyData(rs, os.DirFS("rules")))
	latest := versions.Latest("")
	if b, err := os.ReadFile(filepath.Join("rules", "data", "latest-versions.yaml")); err == nil {
		latest = versions.LatestFrom(b)
	}
	type t struct {
		id string
		d  time.Duration
	}
	var out []t
	for _, r := range rs {
		c := *r
		c.Status = "active"
		t0 := time.Now()
		engine.Scan(engine.Options{Root: *root, Rules: []*rules.Rule{&c}, Latest: latest})
		out = append(out, t{r.ID, time.Since(t0)})
	}
	slices.SortFunc(out, func(a, b t) int { return int(b.d - a.d) })
	for _, x := range out[:min(*top, len(out))] {
		fmt.Printf("%8.2fs %s\n", x.d.Seconds(), x.id)
	}
}

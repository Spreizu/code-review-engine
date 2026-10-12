package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestTemplateLoads(t *testing.T) {
	p := filepath.Join(t.TempDir(), ".crev.yaml")
	if err := os.WriteFile(p, Template, 0o644); err != nil {
		t.Fatal(err)
	}
	c, err := Load(p)
	if err != nil {
		t.Fatal(err)
	}
	if c.FailOn != "critical" || c.UnknownVersionPolicy != "assume-latest" || len(c.Packs) != 0 {
		t.Fatalf("template defaults changed: %+v", c)
	}
}

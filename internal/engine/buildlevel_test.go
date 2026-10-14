package engine

import (
	"testing"

	"github.com/elmo/code-review-engine/internal/versions"
)

func TestInheritBuildLevel(t *testing.T) {
	units := map[string]*versions.Unit{
		"lib":     {Facts: map[string]versions.Fact{"java": {Version: "8"}}},
		"app":     {Facts: map[string]versions.Fact{"java": {Version: "17"}}},
		"samples": {Facts: map[string]versions.Fact{"java": {Version: "27", Assumed: true}}},
		"web":     {Facts: map[string]versions.Fact{"typescript": {Version: "6.0", Assumed: true}}},
	}
	inheritBuildLevel(units, "java", "kotlin")
	if f := units["samples"].Facts["java"]; f.Version != "8" || f.Assumed {
		t.Fatalf("samples java = %+v, want declared 8", f)
	}
	if f := units["app"].Facts["java"]; f.Version != "17" {
		t.Fatalf("declared level changed: %+v", f)
	}
	if f := units["web"].Facts["typescript"]; !f.Assumed {
		t.Fatalf("non-JVM dimension must keep assume-latest: %+v", f)
	}
}

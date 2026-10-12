package engine

import (
	"strings"
	"testing"
	"time"

	"github.com/elmo/code-review-engine/internal/rules"
)

func TestQueryTimeoutReportsInsteadOfHanging(t *testing.T) {
	var b strings.Builder
	b.WriteString("x = {\n")
	for i := 0; i < 4000; i++ {
		b.WriteString("    \"k" + strings.Repeat("a", i%7) + string(rune('0'+i%10)) + "\": \"v\",\n")
	}
	b.WriteString("}\n")
	tr, err := Parse("python", []byte(b.String()))
	if err != nil {
		t.Fatal(err)
	}
	defer tr.Close()
	r := &rules.Rule{ID: "T"}
	r.Detection.Query = `((dictionary (pair key: (string) @a) (pair key: (string) @b) @match) (#eq? @a @b))`
	old := QueryTimeout
	QueryTimeout = 5 * time.Millisecond
	defer func() { QueryTimeout = old }()
	start := time.Now()
	_, err = Run(r, tr)
	if time.Since(start) > 2*time.Second {
		t.Fatalf("query ran %s despite the timeout", time.Since(start))
	}
	if err == nil || !strings.Contains(err.Error(), "timed out") {
		t.Fatalf("want a timeout error, got %v", err)
	}
}

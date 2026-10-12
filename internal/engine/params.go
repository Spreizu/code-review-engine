package engine

import (
	"fmt"
	"strings"
	"sync"

	"github.com/elmo/code-review-engine/internal/projcfg"
	"github.com/elmo/code-review-engine/internal/rules"
)

var paramRules sync.Map // key -> *rules.Rule

// WithParams resolves rule params for rel (set may be nil: defaults only).
func WithParams(r *rules.Rule, set *projcfg.Set, rel string) *rules.Rule {
	return withParams(r, set, rel)
}

// withParams returns r with ${name} placeholders in filters and message replaced by the
// project's configured value (e.g. yamllint line-length max) or the rule's default.
func withParams(r *rules.Rule, set *projcfg.Set, rel string) *rules.Rule {
	if len(r.Params) == 0 {
		return r
	}
	vals := map[string]string{}
	var key strings.Builder
	key.WriteString(r.ID)
	for name, p := range r.Params {
		v := fmt.Sprint(p.Default)
		if pv, _ := set.ParamFrom(p.From, rel); pv != nil {
			if f, ok := pv.(float64); ok {
				v = fmt.Sprint(int(f))
			} else {
				v = fmt.Sprint(pv)
			}
		}
		vals[name] = v
		key.WriteString("\x00" + name + "=" + v)
	}
	if c, ok := paramRules.Load(key.String()); ok {
		return c.(*rules.Rule)
	}
	c := *r
	sub := func(s string) string {
		for k, v := range vals {
			s = strings.ReplaceAll(s, "${"+k+"}", v)
		}
		return s
	}
	c.Detection.Filters = make([]string, len(r.Detection.Filters))
	for i, f := range r.Detection.Filters {
		c.Detection.Filters[i] = sub(f)
	}
	c.Message, c.Title = sub(r.Message), sub(r.Title)
	paramRules.Store(key.String(), &c)
	return &c
}

package taint

import "maps"

type val struct {
	t   T
	why string
}

func (a val) or(b val) val {
	if a.t == 0 {
		return val{a.t | b.t, b.why}
	}
	if b.t != 0 && a.why == "" {
		a.why = b.why
	}
	a.t |= b.t
	return a
}

type cv struct {
	kind byte // 'i' int, 's' string, 'b' bool
	i    int64
	s    string
	b    bool
}

func (c cv) truthy() bool {
	switch c.kind {
	case 'i':
		return c.i != 0
	case 's':
		return c.s != ""
	}
	return c.b
}

type env struct {
	vars   map[string]val
	keys   map[string]map[string]val // container -> literal key -> value
	lists  map[string][]val          // literal-index lists created in this function
	consts map[string]cv
	origin map[string]string // var -> the variable it was parsed from (u := url.Parse(raw))
	dead   bool              // the path ended (return/throw/raise): nothing after it runs
}

func newEnv() *env {
	return &env{vars: map[string]val{}, keys: map[string]map[string]val{}, lists: map[string][]val{}, consts: map[string]cv{}, origin: map[string]string{}}
}

func (e *env) clone() *env {
	c := &env{vars: maps.Clone(e.vars), keys: map[string]map[string]val{}, lists: map[string][]val{}, consts: maps.Clone(e.consts), origin: maps.Clone(e.origin), dead: e.dead}
	for k, m := range e.keys {
		c.keys[k] = maps.Clone(m)
	}
	for k, l := range e.lists {
		c.lists[k] = append([]val(nil), l...)
	}
	return c
}

// merge joins two branch states: a value is tainted if it is tainted on either path.
func merge(a, b *env) *env {
	if a == nil {
		return b
	}
	if b == nil {
		return a
	}
	if a.dead && !b.dead {
		return b.clone()
	}
	if b.dead && !a.dead {
		return a.clone()
	}
	out := a.clone()
	for k, o := range b.origin {
		if _, ok := out.origin[k]; !ok {
			out.origin[k] = o
		}
	}
	for k, v := range b.vars {
		out.vars[k] = out.vars[k].or(v)
	}
	for k, m := range b.keys {
		om := out.keys[k]
		if om == nil {
			om = map[string]val{}
			out.keys[k] = om
		}
		for kk, v := range m {
			om[kk] = om[kk].or(v)
		}
	}
	for k, l := range out.lists {
		bl, ok := b.lists[k]
		if !ok || len(bl) != len(l) {
			// shapes differ: fall back to the container's union
			u := out.vars[k]
			for _, v := range l {
				u = u.or(v)
			}
			for _, v := range bl {
				u = u.or(v)
			}
			out.vars[k] = u
			delete(out.lists, k)
			continue
		}
		for i := range l {
			l[i] = l[i].or(bl[i])
		}
	}
	for k, bl := range b.lists {
		if _, ok := a.lists[k]; !ok {
			u := out.vars[k]
			for _, v := range bl {
				u = u.or(v)
			}
			out.vars[k] = u
		}
	}
	for k, c := range out.consts {
		if bc, ok := b.consts[k]; !ok || bc != c {
			delete(out.consts, k)
		}
	}
	return out
}

// container returns the union of everything a container holds (vars, keyed entries, list items).
func (e *env) container(name string) val {
	v := e.vars[name]
	for _, x := range e.keys[name] {
		v = v.or(x)
	}
	for _, x := range e.lists[name] {
		v = v.or(x)
	}
	return v
}

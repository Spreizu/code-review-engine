#!/usr/bin/env python3
"""Add reviewed crev-rule -> Sonar key links to tools/gap/sonar-map.yaml.

Input: a mapping file (YAML) with
  by_tag:  {"eslint:no-empty": ["S108"], ...}   # every crev rule carrying the tag
  by_id:   {"JS-QUAL-WITH-001": ["S1321"], ...}
  lang:    javascript                            # Sonar repository prefix(es) to try, comma separated
Keys are expanded to every listed Sonar repository whose cached catalog has that key
(e.g. javascript + typescript for JS rules that also run on TS). Each pair was reviewed by
reading both titles; only keys are written.

  python tools/gap/sonar_addmap.py tools/gap/sonar-links/<file>.yaml
"""
import glob, json, os, sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAT = {"javascript": "js", "typescript": "ts", "python": "py", "java": "java", "go": "go", "godre": "go", "kotlin": "kotlin",
       "php": "php", "docker": "docker", "terraform": "terraform", "Web": "web", "css": "css"}


def catalog(repo):
    p = os.path.join(ROOT, "tools/gap/cache", f"sonar-{CAT[repo]}.json")
    if not os.path.exists(p):
        return set()
    return {r["key"].split(":", 1)[1] for r in json.load(open(p)) if r["key"].split(":", 1)[0] == repo}


def main(path):
    spec = yaml.safe_load(open(path))
    repos = spec["lang"].split(",")
    cats = {r: catalog(r) for r in repos}
    rules = {}
    for f in glob.glob(os.path.join(ROOT, "rules/packs/*/*.yaml")):
        for r in yaml.safe_load(open(f))["rules"]:
            rules[r["id"]] = r
    add = {}
    for tag, keys in (spec.get("by_tag") or {}).items():
        hit = [i for i, r in rules.items() if tag in (r.get("tags") or [])]
        if not hit:
            print("no rule with tag", tag)
        for i in hit:
            add.setdefault(i, []).extend(keys)
    for i, keys in (spec.get("by_id") or {}).items():
        if i not in rules:
            print("unknown rule", i)
            continue
        add.setdefault(i, []).extend(keys)
    mp = os.path.join(ROOT, "tools/gap/sonar-map.yaml")
    text = open(mp).read()
    m = yaml.safe_load(text)
    cur = m["rules"]
    n = 0
    for i, keys in sorted(add.items()):
        for k in keys:
            for repo in repos:
                if repo == "javascript" and rules[i].get("language") == "typescript":
                    continue  # a TypeScript-only rule does not run on JavaScript files
                if k in cats[repo]:
                    full = f"{repo}:{k}"
                    if full not in cur.setdefault(i, []):
                        cur[i].append(full)
                        n += 1
                elif repo == repos[0]:
                    print("key not in catalog", repo, k, "for", i)
    head = "".join(l for l in text.splitlines(True) if l.startswith("#"))
    with open(mp, "w") as fh:
        fh.write(head)
        yaml.safe_dump({"rules": {k: cur[k] for k in cur}}, fh, sort_keys=False, default_flow_style=False)
    print("added", n, "links")


if __name__ == "__main__":
    main(sys.argv[1])

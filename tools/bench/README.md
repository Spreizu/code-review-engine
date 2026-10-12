# tools/bench: crev vs AI review benchmark (dev tool, not part of the crev binary)

```bash
go build -o /tmp/crev ./cmd/crev
# 1. clone the pinned repos (tools/bench/cache/repos.txt) into tools/bench/cache/<name> (blobless clones)
python tools/bench/mine.py            # SZZ bug-introducing + real clean commits -> cases/mined.json
python tools/bench/build.py cases     # + seeded + OWASP cases -> work/cases/<id>/ (git repo, diff.patch, meta.json)
python tools/bench/build.py scan      # crev --base HEAD~1, 3 runs per case (time + determinism)
python tools/bench/review.py prompts  # anonymised reviewer inputs work/review/batch-NN.md (+ -crev.md), crev ai export
# reviewer writes answers/{B,C,A}.jsonl (B before reading the crev file of a batch)
python tools/bench/review.py judge    # blinded pool of findings that hit no label -> work/review/judge.md
# reviewer writes answers/judge.jsonl
python tools/bench/review.py score && python tools/bench/tables.py
```

`cache/` and `work/` hold third-party source and are git-ignored (cache has its own go.mod so `go ./...`
skips it). Committed: the scripts, `cases/*.json` (repo, pinned sha, commit ids, label line numbers;
no source), the reviewer answers, `results.json` and `report.md`.

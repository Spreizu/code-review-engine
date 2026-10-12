"""needles.py URL needle... - report which needles (case-insensitive regex) occur on the fetched page, with context."""
import re, sys
import fetch
st, t = fetch.fetch(sys.argv[1])
print("HTTP", st, len(t))
for n in sys.argv[2:]:
    m = re.search(n, t, re.I)
    print(("OK   " if m else "MISS ") + n + ("  ::  " + t[max(0, m.start()-80):m.end()+120] if m else ""))

"""pgrep.py URL REGEX [width] - show matches of REGEX in the fetched (cached) page text."""
import re, sys
import fetch
st, t = fetch.fetch(sys.argv[1])
w = int(sys.argv[3]) if len(sys.argv) > 3 else 90
print("HTTP", st, len(t))
for i, m in enumerate(re.finditer(sys.argv[2], t, re.I)):
    if i >= 6: break
    print("...", t[max(0, m.start()-w):m.end()+w].replace("\n", " "))

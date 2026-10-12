# OWASP Benchmark scoring (t2)

Flagged = finding with matching CWE family in the test file. TPR = TP/(TP+FN), FPR = FP/(FP+TN). "Review" counts confirmed findings only; "candidates" adds pending ai-confirm findings (they still need AI confirmation at high confidence).

## BenchmarkJava (expectedresults-1.2.csv)

| category | CWE | real | TPR review | FPR review | score | TPR cand | FPR cand | rules |
|---|---|---|---|---|---|---|---|---|
| cmdi | 78 | 126 | 0.00 | 0.00 | +0.00 | 0.77 | 0.26 | JAVA-SEC-CMD-001(61) TAINT-JAVA-CMDI(97) |
| crypto | 327 | 130 | 0.75 | 0.00 | +0.75 | 0.75 | 0.00 | JAVA-SEC-WEAK-CIPHER-001(97) |
| hash | 328 | 129 | 0.00 | 0.00 | +0.00 | 0.69 | 0.00 | JAVA-SEC-WEAK-HASH-001(113) |
| ldapi | 90 | 27 | 0.00 | 0.00 | +0.00 | 0.89 | 0.00 | TAINT-JAVA-LDAP(24) |
| pathtraver | 22 | 133 | 0.00 | 0.00 | +0.00 | 0.89 | 0.00 | TAINT-JAVA-PATH(155) |
| securecookie | 614 | 36 | 1.00 | 0.00 | +1.00 | 1.00 | 0.00 | JAVA-SEC-COOKIE-SECURE-001(36) JAVA-SEC-COOKIE-SECURE-002(33) |
| sqli | 89 | 272 | 0.00 | 0.00 | +0.00 | 0.94 | 0.00 | TAINT-JAVA-SQLI(255) |
| trustbound | 501 | 83 | 0.00 | 0.00 | +0.00 | 0.54 | 0.53 | JAVA-SEC-TRUST-BOUNDARY-001(68) |
| weakrand | 330 | 218 | 0.00 | 0.00 | +0.00 | 0.89 | 0.00 | JAVA-SEC-RANDOM-001(193) |
| xpathi | 643 | 15 | 0.00 | 0.00 | +0.00 | 0.93 | 0.00 | TAINT-JAVA-XPATH(14) |
| xss | 79 | 246 | 0.00 | 0.00 | +0.00 | 0.89 | 0.61 | JAVA-SEC-XSS-WRITER-001(370) TAINT-JAVA-XSS(220) |
| **all** | | 1415 | 0.09 | 0.00 | +0.09 | 0.84 | 0.14 | |

## BenchmarkPython (expectedresults-0.1.csv)

| category | CWE | real | TPR review | FPR review | score | TPR cand | FPR cand | rules |
|---|---|---|---|---|---|---|---|---|
| cmdi | 78 | 13 | 0.00 | 0.00 | +0.00 | 0.54 | 1.00 | PY-SUBPROCESS-SHELL(14) TAINT-PY-CMDI(7) |
| codeinj | 94 | 20 | 0.00 | 0.00 | +0.00 | 1.00 | 1.00 | PY-EVAL(53) TAINT-PY-CODE(12) |
| deserialization | 502 | 18 | 0.00 | 0.00 | +0.00 | 1.00 | 0.33 | PY-PICKLE-LOADS(20) PY-YAML-LOAD-UNSAFE(10) |
| hash | 328 | 71 | 0.00 | 0.00 | +0.00 | 0.52 | 0.00 | PY-HASH-WEAK(37) |
| ldapi | 90 | 16 | 0.00 | 0.00 | +0.00 | 0.56 | 0.00 | TAINT-PY-LDAP(9) |
| pathtraver | 22 | 65 | 0.00 | 0.00 | +0.00 | 0.54 | 0.05 | TAINT-PY-PATH(40) |
| redirect | 601 | 13 | 0.00 | 0.00 | +0.00 | 0.92 | 0.24 | TAINT-PY-REDIRECT(17) |
| securecookie | 614 | 24 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-COOKIE-INSECURE(24) |
| sqli | 89 | 5 | 0.00 | 0.00 | +0.00 | 0.40 | 0.00 | TAINT-PY-SQLI(2) |
| trustbound | 501 | 18 | 0.00 | 0.00 | +0.00 | 0.00 | 0.00 |  |
| weakrand | 330 | 99 | 0.00 | 0.00 | +0.00 | 0.00 | 0.00 |  |
| xpathi | 643 | 51 | 0.00 | 0.00 | +0.00 | 0.55 | 0.16 | PY-XPATH-INJECTION(18) TAINT-PY-XPATH(37) |
| xss | 79 | 31 | 0.00 | 0.00 | +0.00 | 0.55 | 0.24 | TAINT-PY-XSS(69) |
| xxe | 611 | 8 | 0.00 | 0.00 | +0.00 | 1.00 | 1.00 | PY-XML-UNTRUSTED(28) |
| **all** | | 452 | 0.00 | 0.00 | +0.00 | 0.48 | 0.15 | |

# Vulnerable apps

| app | security review | security candidates | OWASP categories (review+candidates) |
|---|---|---|---|
| juice-shop | n/a | n/a | open tools/corpus/results/t2/raw/juice-shop.json: no such file or directory |
| NodeGoat | n/a | n/a | open tools/corpus/results/t2/raw/NodeGoat.json: no such file or directory |
| WebGoat | n/a | n/a | open tools/corpus/results/t2/raw/WebGoat.json: no such file or directory |
| DVWA | n/a | n/a | open tools/corpus/results/t2/raw/DVWA.json: no such file or directory |
| pygoat | n/a | n/a | open tools/corpus/results/t2/raw/pygoat.json: no such file or directory |
| dvpwa | n/a | n/a | open tools/corpus/results/t2/raw/dvpwa.json: no such file or directory |
| govwa | n/a | n/a | open tools/corpus/results/t2/raw/govwa.json: no such file or directory |
| terragoat | n/a | n/a | open tools/corpus/results/t2/raw/terragoat.json: no such file or directory |
| kubernetes-goat | n/a | n/a | open tools/corpus/results/t2/raw/kubernetes-goat.json: no such file or directory |
| DVGA | n/a | n/a | open tools/corpus/results/t2/raw/DVGA.json: no such file or directory |

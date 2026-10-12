# OWASP Benchmark scoring (m4)

Flagged = finding with matching CWE family in the test file. TPR = TP/(TP+FN), FPR = FP/(FP+TN). "Review" counts confirmed findings only; "candidates" adds pending ai-confirm findings (they still need AI confirmation at high confidence).

## BenchmarkJava (expectedresults-1.2.csv)

| category | CWE | real | TPR review | FPR review | score | TPR cand | FPR cand | rules |
|---|---|---|---|---|---|---|---|---|
| cmdi | 78 | 126 | 0.91 | 0.00 | +0.91 | 0.91 | 0.08 | JAVA-SEC-CMD-001(38) JAVA-TAINT-CMDI(115) |
| crypto | 327 | 130 | 0.75 | 0.00 | +0.75 | 0.75 | 0.00 | JAVA-SEC-WEAK-CIPHER-001(97) |
| hash | 328 | 129 | 0.00 | 0.00 | +0.00 | 0.69 | 0.00 | JAVA-SEC-WEAK-HASH-001(113) |
| ldapi | 90 | 27 | 0.00 | 0.00 | +0.00 | 0.89 | 0.00 | JAVA-TAINT-LDAP(24) |
| pathtraver | 22 | 133 | 0.89 | 0.00 | +0.89 | 0.89 | 0.00 | JAVA-TAINT-PATH(155) |
| securecookie | 614 | 36 | 1.00 | 0.00 | +1.00 | 1.00 | 0.00 | JAVA-SEC-COOKIE-SECURE-001(36) JAVA-SEC-COOKIE-SECURE-002(33) |
| sqli | 89 | 272 | 0.94 | 0.00 | +0.94 | 0.94 | 0.00 | JAVA-TAINT-SQLI(255) |
| trustbound | 501 | 83 | 0.00 | 0.00 | +0.00 | 0.87 | 0.00 | JAVA-SEC-TRUST-BOUNDARY-001(45) JAVA-TAINT-TRUST(72) |
| weakrand | 330 | 218 | 0.00 | 0.00 | +0.00 | 0.89 | 0.00 | JAVA-SEC-RANDOM-001(193) |
| xpathi | 643 | 15 | 0.00 | 0.00 | +0.00 | 0.93 | 0.00 | JAVA-TAINT-XPATH(14) |
| xss | 79 | 246 | 0.89 | 0.00 | +0.89 | 0.89 | 0.00 | JAVA-SEC-XSS-WRITER-001(183) JAVA-TAINT-XSS(220) |
| **all** | | 1415 | 0.59 | 0.00 | +0.59 | 0.87 | 0.01 | |

## BenchmarkPython (expectedresults-0.1.csv)

| category | CWE | real | TPR review | FPR review | score | TPR cand | FPR cand | rules |
|---|---|---|---|---|---|---|---|---|
| cmdi | 78 | 13 | 0.00 | 0.00 | +0.00 | 1.00 | 0.14 | PY-SEC-SUBPROCESS-SHELL(8) PY-TAINT-CMDI(13) |
| codeinj | 94 | 20 | 0.00 | 0.00 | +0.00 | 1.00 | 0.12 | PY-SEC-EVAL(24) PY-TAINT-CODE(20) |
| deserialization | 502 | 18 | 0.00 | 0.00 | +0.00 | 1.00 | 0.33 | PY-SEC-PICKLE-LOADS(20) PY-SEC-YAML-LOAD-UNSAFE(10) |
| hash | 328 | 71 | 0.00 | 0.00 | +0.00 | 0.52 | 0.00 | PY-SEC-HASH-WEAK(37) |
| ldapi | 90 | 16 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-TAINT-LDAP(16) |
| pathtraver | 22 | 65 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-TAINT-PATH(65) |
| redirect | 601 | 13 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-TAINT-REDIRECT(13) |
| securecookie | 614 | 24 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-SEC-COOKIE-INSECURE(24) |
| sqli | 89 | 5 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-TAINT-SQLI(5) |
| trustbound | 501 | 18 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-TAINT-TRUST(18) |
| weakrand | 330 | 99 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-SEC-RANDOM-SESSION-VALUE(99) |
| xpathi | 643 | 51 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-TAINT-XPATH(51) |
| xss | 79 | 31 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-TAINT-XSS(31) |
| xxe | 611 | 8 | 0.00 | 0.00 | +0.00 | 1.00 | 1.00 | PY-SEC-XML-UNTRUSTED(28) |
| **all** | | 452 | 0.00 | 0.00 | +0.00 | 0.92 | 0.05 | |

# Vulnerable apps

| app | security review | security candidates | OWASP categories (review+candidates) |
|---|---|---|---|
| juice-shop | 5 | 259 | (no 2025 mapping)=29 A01=51 A02=1 A03=18 A04=109 A05=26 A07=30 A08=19 |
| NodeGoat | 4 | 21 | (no 2025 mapping)=6 A01=4 A03=1 A04=7 A05=7 A08=1 |
| WebGoat | 16 | 105 | (no 2025 mapping)=15 A01=15 A02=3 A03=10 A04=15 A05=46 A07=4 A08=15 A10=8 |
| DVWA | 22 | 127 | (no 2025 mapping)=23 A01=30 A02=2 A03=4 A04=18 A05=49 A06=1 A07=2 A08=4 A10=20 |
| pygoat | 4 | 121 | (no 2025 mapping)=56 A01=28 A02=20 A04=1 A05=13 A07=3 A08=4 |
| dvpwa | 0 | 17 | (no 2025 mapping)=9 A04=2 A05=5 A07=1 |
| govwa | 0 | 39 | (no 2025 mapping)=9 A01=1 A04=6 A05=21 A07=2 |
| terragoat | 10 | 9 | A01=6 A03=3 A06=1 A07=6 A08=3 A09=3 |
| kubernetes-goat | 19 | 85 | (no 2025 mapping)=33 A01=43 A02=1 A03=19 A05=4 A06=4 A08=2 |
| DVGA | 8 | 28 | A01=1 A02=1 A04=6 A05=22 A07=6 |
| InsecureShop | 4 | 9 | (no 2025 mapping)=4 A01=3 A04=1 A06=1 A08=3 A09=1 |

## juice-shop marked challenges

36 challenges with vuln-line markers; hit on the review list 1 (3%), as candidates 7 (19%). Missed: adminSectionChallenge, changeProductChallenge, chatbotGreedyInjectionChallenge, chatbotPromptInjecti, chatbotPromptInjectionChallenge, dbSchemaChallenge, exposedMetricsChallenge, forgedReviewChallenge, loginAdminChallenge, loginBenderChallenge, loginJimChallenge, nftMintChallenge, nftUnlockChallenge, noSqlReviewsChallenge, redirectChallenge, redirectCryptoCurrencyChallenge, registerAdminChallenge, resetPasswordBenderChallenge, resetPasswordBjoernChallenge, resetPasswordBjoernOwaspChallenge, resetPasswordJimChallenge, resetPasswordMortyChallenge, resetPasswordUvoginChallenge, scoreBoardChallenge, tokenSaleChallenge, unionSqlInjectionChallenge, weakPasswordChallenge, web3SandboxChallenge, web3WalletChallenge

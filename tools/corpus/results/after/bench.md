# OWASP Benchmark scoring (after)

Flagged = finding with matching CWE family in the test file. TPR = TP/(TP+FN), FPR = FP/(FP+TN). "Review" counts confirmed findings only; "candidates" adds pending ai-confirm findings (they still need AI confirmation at high confidence).

## BenchmarkJava (expectedresults-1.2.csv)

| category | CWE | real | TPR review | FPR review | score | TPR cand | FPR cand | rules |
|---|---|---|---|---|---|---|---|---|
| cmdi | 78 | 126 | 0.91 | 0.00 | +0.91 | 0.91 | 0.08 | JAVA-SEC-CMD-001(38) TAINT-JAVA-CMDI(115) |
| crypto | 327 | 130 | 0.75 | 0.00 | +0.75 | 0.75 | 0.00 | JAVA-SEC-WEAK-CIPHER-001(97) |
| hash | 328 | 129 | 0.00 | 0.00 | +0.00 | 0.69 | 0.00 | JAVA-SEC-WEAK-HASH-001(113) |
| ldapi | 90 | 27 | 0.00 | 0.00 | +0.00 | 0.89 | 0.00 | TAINT-JAVA-LDAP(24) |
| pathtraver | 22 | 133 | 0.89 | 0.00 | +0.89 | 0.89 | 0.00 | TAINT-JAVA-PATH(155) |
| securecookie | 614 | 36 | 1.00 | 0.00 | +1.00 | 1.00 | 0.00 | JAVA-SEC-COOKIE-SECURE-001(36) JAVA-SEC-COOKIE-SECURE-002(33) |
| sqli | 89 | 272 | 0.94 | 0.00 | +0.94 | 0.94 | 0.00 | TAINT-JAVA-SQLI(255) |
| trustbound | 501 | 83 | 0.00 | 0.00 | +0.00 | 0.87 | 0.00 | JAVA-SEC-TRUST-BOUNDARY-001(45) TAINT-JAVA-TRUST(72) |
| weakrand | 330 | 218 | 0.00 | 0.00 | +0.00 | 0.89 | 0.00 | JAVA-SEC-RANDOM-001(193) |
| xpathi | 643 | 15 | 0.00 | 0.00 | +0.00 | 0.93 | 0.00 | TAINT-JAVA-XPATH(14) |
| xss | 79 | 246 | 0.89 | 0.00 | +0.89 | 0.89 | 0.00 | JAVA-SEC-XSS-WRITER-001(183) TAINT-JAVA-XSS(220) |
| **all** | | 1415 | 0.59 | 0.00 | +0.59 | 0.87 | 0.01 | |

## BenchmarkPython (expectedresults-0.1.csv)

| category | CWE | real | TPR review | FPR review | score | TPR cand | FPR cand | rules |
|---|---|---|---|---|---|---|---|---|
| cmdi | 78 | 13 | 0.54 | 0.14 | +0.40 | 1.00 | 0.14 | PY-SUBPROCESS-SHELL(8) TAINT-PY-CMDI(13) |
| codeinj | 94 | 20 | 0.00 | 0.00 | +0.00 | 1.00 | 0.12 | PY-EVAL(24) TAINT-PY-CODE(20) |
| deserialization | 502 | 18 | 0.28 | 0.14 | +0.14 | 1.00 | 0.33 | PY-PICKLE-LOADS(20) PY-YAML-LOAD-UNSAFE(10) |
| hash | 328 | 71 | 0.00 | 0.00 | +0.00 | 0.52 | 0.00 | PY-HASH-WEAK(37) |
| ldapi | 90 | 16 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | TAINT-PY-LDAP(16) |
| pathtraver | 22 | 65 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | TAINT-PY-PATH(65) |
| redirect | 601 | 13 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | TAINT-PY-REDIRECT(13) |
| securecookie | 614 | 24 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-COOKIE-INSECURE(24) |
| sqli | 89 | 5 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | TAINT-PY-SQLI(5) |
| trustbound | 501 | 18 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | TAINT-PY-TRUST(18) |
| weakrand | 330 | 99 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-RANDOM-SESSION-VALUE(99) |
| xpathi | 643 | 51 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | TAINT-PY-XPATH(51) |
| xss | 79 | 31 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | TAINT-PY-XSS(31) |
| xxe | 611 | 8 | 0.00 | 0.00 | +0.00 | 1.00 | 1.00 | PY-XML-UNTRUSTED(28) |
| **all** | | 452 | 0.03 | 0.01 | +0.02 | 0.92 | 0.05 | |

# Vulnerable apps

| app | security review | security candidates | OWASP categories (review+candidates) |
|---|---|---|---|
| juice-shop | 2 | 262 | (no 2025 mapping)=28 A01=52 A02=1 A03=18 A04=109 A05=26 A07=30 A08=19 |
| NodeGoat | 3 | 22 | (no 2025 mapping)=6 A01=4 A03=1 A04=7 A05=7 A08=1 |
| WebGoat | 24 | 87 | (no 2025 mapping)=5 A01=15 A02=3 A03=10 A04=15 A05=46 A07=4 A08=15 A10=8 |
| DVWA | 21 | 128 | (no 2025 mapping)=23 A01=30 A02=2 A03=4 A04=18 A05=49 A06=1 A07=2 A08=4 A10=20 |
| pygoat | 8 | 82 | (no 2025 mapping)=21 A01=28 A02=20 A04=1 A05=13 A07=3 A08=4 |
| dvpwa | 0 | 17 | (no 2025 mapping)=9 A04=2 A05=5 A07=1 |
| govwa | 1 | 36 | (no 2025 mapping)=7 A01=1 A04=6 A05=21 A07=2 |
| terragoat | 13 | 6 | A01=6 A03=3 A06=1 A07=6 A08=3 A09=3 |
| kubernetes-goat | 28 | 74 | (no 2025 mapping)=31 A01=43 A02=1 A03=19 A05=4 A06=4 A08=2 |
| DVGA | 8 | 28 | A01=1 A02=1 A04=6 A05=22 A07=6 |
| InsecureShop | 4 | 9 | (no 2025 mapping)=4 A01=3 A04=1 A06=1 A08=3 A09=1 |

## juice-shop marked challenges

36 challenges with vuln-line markers; hit on the review list 1 (3%), as candidates 7 (19%). Missed: adminSectionChallenge, changeProductChallenge, chatbotGreedyInjectionChallenge, chatbotPromptInjecti, chatbotPromptInjectionChallenge, dbSchemaChallenge, exposedMetricsChallenge, forgedReviewChallenge, loginAdminChallenge, loginBenderChallenge, loginJimChallenge, nftMintChallenge, nftUnlockChallenge, noSqlReviewsChallenge, redirectChallenge, redirectCryptoCurrencyChallenge, registerAdminChallenge, resetPasswordBenderChallenge, resetPasswordBjoernChallenge, resetPasswordBjoernOwaspChallenge, resetPasswordJimChallenge, resetPasswordMortyChallenge, resetPasswordUvoginChallenge, scoreBoardChallenge, tokenSaleChallenge, unionSqlInjectionChallenge, weakPasswordChallenge, web3SandboxChallenge, web3WalletChallenge

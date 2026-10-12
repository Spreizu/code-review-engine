# OWASP Benchmark scoring (t7)

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
| codeinj | 94 | 20 | 0.00 | 0.00 | +0.00 | 1.00 | 1.00 | PY-EVAL(53) TAINT-PY-CODE(15) |
| deserialization | 502 | 18 | 0.00 | 0.00 | +0.00 | 1.00 | 0.33 | PY-PICKLE-LOADS(20) PY-YAML-LOAD-UNSAFE(10) |
| hash | 328 | 71 | 0.00 | 0.00 | +0.00 | 0.52 | 0.00 | PY-HASH-WEAK(37) |
| ldapi | 90 | 16 | 0.00 | 0.00 | +0.00 | 0.88 | 0.00 | TAINT-PY-LDAP(14) |
| pathtraver | 22 | 65 | 0.00 | 0.00 | +0.00 | 0.91 | 0.00 | TAINT-PY-PATH(59) |
| redirect | 601 | 13 | 0.00 | 0.00 | +0.00 | 1.00 | 0.33 | TAINT-PY-REDIRECT(20) |
| securecookie | 614 | 24 | 0.00 | 0.00 | +0.00 | 1.00 | 0.00 | PY-COOKIE-INSECURE(24) |
| sqli | 89 | 5 | 0.00 | 0.00 | +0.00 | 0.60 | 0.00 | TAINT-PY-SQLI(3) |
| trustbound | 501 | 18 | 0.00 | 0.00 | +0.00 | 0.00 | 0.00 |  |
| weakrand | 330 | 99 | 0.00 | 0.00 | +0.00 | 0.00 | 0.00 |  |
| xpathi | 643 | 51 | 0.00 | 0.00 | +0.00 | 0.84 | 0.10 | PY-XPATH-INJECTION(18) TAINT-PY-XPATH(43) |
| xss | 79 | 31 | 0.00 | 0.00 | +0.00 | 0.65 | 0.07 | TAINT-PY-XSS(48) |
| xxe | 611 | 8 | 0.00 | 0.00 | +0.00 | 1.00 | 1.00 | PY-XML-UNTRUSTED(28) |
| **all** | | 452 | 0.00 | 0.00 | +0.00 | 0.59 | 0.12 | |

# Vulnerable apps

| app | security review | security candidates | OWASP categories (review+candidates) |
|---|---|---|---|
| juice-shop | 5 | 174 | (no 2025 mapping)=9 A01=6 A02=1 A04=108 A05=29 A07=26 |
| NodeGoat | 3 | 16 | (no 2025 mapping)=3 A01=2 A04=7 A05=7 |
| WebGoat | 17 | 82 | A01=13 A02=3 A04=15 A05=46 A07=9 A08=5 A10=8 |
| DVWA | 21 | 115 | (no 2025 mapping)=21 A01=24 A02=2 A04=18 A05=49 A07=2 A10=20 |
| pygoat | 4 | 80 | (no 2025 mapping)=16 A01=27 A02=20 A04=1 A05=13 A07=3 A08=4 |
| dvpwa | 0 | 14 | (no 2025 mapping)=6 A04=2 A05=5 A07=1 |
| govwa | 1 | 33 | (no 2025 mapping)=5 A04=6 A05=21 A07=2 |
| terragoat | 13 | 0 | A01=3 A06=1 A07=6 A09=3 |
| kubernetes-goat | 5 | 17 | (no 2025 mapping)=15 A01=2 A02=1 A05=4 |
| DVGA | 24 | 27 | (no 2025 mapping)=17 A02=1 A04=6 A05=22 A07=5 |

## juice-shop marked challenges

36 challenges with vuln-line markers; hit on the review list 1 (3%), as candidates 5 (14%). Missed: accessLogDisclosureChallenge, adminSectionChallenge, changeProductChallenge, chatbotGreedyInjectionChallenge, chatbotPromptInjecti, chatbotPromptInjectionChallenge, dbSchemaChallenge, directoryListingChallenge, exposedMetricsChallenge, forgedReviewChallenge, loginAdminChallenge, loginBenderChallenge, loginJimChallenge, nftMintChallenge, nftUnlockChallenge, noSqlReviewsChallenge, redirectChallenge, redirectCryptoCurrencyChallenge, registerAdminChallenge, resetPasswordBenderChallenge, resetPasswordBjoernChallenge, resetPasswordBjoernOwaspChallenge, resetPasswordJimChallenge, resetPasswordMortyChallenge, resetPasswordUvoginChallenge, scoreBoardChallenge, tokenSaleChallenge, unionSqlInjectionChallenge, weakPasswordChallenge, web3SandboxChallenge, web3WalletChallenge

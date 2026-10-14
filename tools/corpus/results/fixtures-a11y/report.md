# Linter fixture evaluation

63 rules with an equivalent linter suite evaluated (94 listed). Totals: TP 246, FP 0, FN 425, TN 674, precision 1.000, recall 0.367. Deterministic rules (reach the review list without AI): TP 195, FP 0, precision 1.000, 0 below 0.9. Rules with precision < 0.9: 0.

Case level for RuleTester/hadolint suites (valid = must-not-match); line level for ruff and `// want` testdata. Option-dependent cases skipped; env = FP/FN on cases written for another environment (old ecmaVersion, custom globals, script source, inline directives), not scored.

| rule | mode | xref | cases | skipped | env | TP | FN | FP | TN | precision | recall | note |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CSS-QUAL-CALC-UNSPACED-OPERATOR | deterministic | stylelint:function-calc-no-unspaced-operator | 125 | 0 | 0 | 10 | 41 | 0 | 74 | 1.00 | 0.20 |  |
| CSS-QUAL-DOUBLE-SLASH-COMMENT | deterministic | stylelint:no-invalid-double-slash-comments | 11 | 0 | 1 | 7 | 0 | 0 | 3 | 1.00 | 1.00 |  |
| CSS-QUAL-DUPLICATE-DECLARATION | deterministic | stylelint:declaration-block-no-duplicate-properties | 40 | 0 | 0 | 3 | 26 | 0 | 11 | 1.00 | 0.10 |  |
| CSS-QUAL-DUPLICATE-FONT-FAMILY | deterministic | stylelint:font-family-no-duplicate-names | 11 | 0 | 0 | 3 | 3 | 0 | 5 | 1.00 | 0.50 |  |
| CSS-QUAL-DUPLICATE-SELECTOR | deterministic | stylelint:no-duplicate-selectors | 43 | 0 | 1 | 5 | 23 | 0 | 14 | 1.00 | 0.18 |  |
| CSS-QUAL-EMPTY-RULE | deterministic | stylelint:block-no-empty | 30 | 0 | 1 | 8 | 5 | 0 | 16 | 1.00 | 0.62 |  |
| CSS-QUAL-FONT-FAMILY-WITHOUT-GENERIC | deterministic | stylelint:font-family-no-missing-generic-family-keyword | 58 | 0 | 0 | 4 | 8 | 0 | 46 | 1.00 | 0.33 |  |
| CSS-QUAL-GRADIENT-LEGACY-DIRECTION | deterministic | stylelint:function-linear-gradient-no-nonstandard-direction | 62 | 0 | 0 | 8 | 18 | 0 | 36 | 1.00 | 0.31 |  |
| CSS-QUAL-IMPORTANT | ai-confirm | stylelint:declaration-no-important | 4 | 0 | 0 | 2 | 1 | 0 | 1 | 1.00 | 0.67 |  |
| CSS-QUAL-IMPORTANT-IN-KEYFRAMES | deterministic | stylelint:keyframe-declaration-no-important | 13 | 0 | 0 | 3 | 4 | 0 | 6 | 1.00 | 0.43 |  |
| CSS-QUAL-INVALID-HEX-COLOR | deterministic | stylelint:color-no-invalid-hex | 15 | 0 | 0 | 3 | 1 | 0 | 11 | 1.00 | 0.75 |  |
| CSS-QUAL-OVERRIDDEN-DECLARATION | ai-confirm | stylelint:declaration-block-no-duplicate-properties | 40 | 0 | 0 | 27 | 2 | 0 | 11 | 1.00 | 0.93 |  |
| CSS-QUAL-SHORTHAND-OVERRIDES-LONGHAND | deterministic | stylelint:declaration-block-no-shorthand-property-overrides | 32 | 0 | 0 | 17 | 3 | 0 | 12 | 1.00 | 0.85 |  |
| CSS-QUAL-UNKNOWN-AT-RULE | ai-confirm | stylelint:at-rule-no-unknown | 32 | 0 | 0 | 1 | 0 | 0 | 31 | 1.00 | 1.00 |  |
| CSS-QUAL-UNKNOWN-PROPERTY | deterministic | stylelint:property-no-unknown | 19 | 0 | 0 | 5 | 1 | 0 | 13 | 1.00 | 0.83 |  |
| CSS-QUAL-UNKNOWN-PSEUDO | deterministic | stylelint:selector-pseudo-class-no-unknown | 73 | 0 | 1 | 10 | 10 | 0 | 52 | 1.00 | 0.50 |  |
| CSS-QUAL-UNKNOWN-UNIT | deterministic | stylelint:unit-no-unknown | 102 | 0 | 0 | 19 | 10 | 0 | 73 | 1.00 | 0.66 |  |
| CSS-QUAL-UNNEEDED-VENDOR-PREFIX | deterministic | stylelint:property-no-vendor-prefix | 25 | 0 | 0 | 6 | 9 | 0 | 10 | 1.00 | 0.40 |  |
| HTML-A11Y-ARIA-INVALID-ATTRIBUTE | deterministic | axe:aria-valid-attr | 1 | 0 | 0 | 8 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| HTML-A11Y-ARIA-INVALID-ROLE | deterministic | axe:aria-roles | 1 | 0 | 0 | 13 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| HTML-A11Y-ARIA-LABEL-ON-GENERIC | deterministic | axe:aria-prohibited-attr | 1 | 0 | 0 | 7 | 88 | 0 | 0 | 1.00 | 0.07 |  |
| HTML-A11Y-BUTTON-WITHOUT-NAME | deterministic | axe:button-name | 1 | 0 | 0 | 5 | 4 | 0 | 0 | 1.00 | 0.56 |  |
| HTML-A11Y-CONTROL-WITHOUT-LABEL | ai-confirm | axe:label | 1 | 0 | 0 | 2 | 12 | 0 | 0 | 1.00 | 0.14 |  |
| HTML-A11Y-EMPTY-HEADING | ai-confirm | axe:empty-heading | 1 | 0 | 0 | 2 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| HTML-A11Y-HEADING-SKIPPED-LEVEL | ai-confirm | axe:heading-order | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 1.00 | 0.50 |  |
| HTML-A11Y-INPUT-IMAGE-WITHOUT-ALT | deterministic | axe:input-image-alt | 1 | 0 | 0 | 3 | 3 | 0 | 0 | 1.00 | 0.50 |  |
| HTML-A11Y-LANG-INVALID | deterministic | axe:valid-lang | 1 | 0 | 0 | 3 | 1 | 0 | 0 | 1.00 | 0.75 |  |
| HTML-A11Y-MARQUEE-OR-BLINK | ai-confirm | axe:marquee | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1.00 | 1.00 |  |
| HTML-A11Y-ROLE-IMG-WITHOUT-NAME | ai-confirm | axe:role-img-alt | 1 | 0 | 0 | 2 | 2 | 0 | 0 | 1.00 | 0.50 |  |
| HTML-A11Y-TH-INVALID-SCOPE | ai-confirm | axe:scope-attr-valid | 1 | 0 | 0 | 1 | 2 | 0 | 0 | 1.00 | 0.33 |  |
| JS-A11Y-AMBIGUOUS-LINK-TEXT | deterministic | jsx-a11y:anchor-ambiguous-text | 30 | 9 | 0 | 8 | 17 | 0 | 5 | 1.00 | 0.32 |  |
| JS-A11Y-ARIA-INVALID-ATTRIBUTE | deterministic | jsx-a11y:aria-props | 11 | 0 | 0 | 3 | 0 | 0 | 8 | 1.00 | 1.00 |  |
| JS-A11Y-ARIA-INVALID-ROLE | deterministic | jsx-a11y:aria-role | 24 | 12 | 0 | 3 | 9 | 0 | 12 | 1.00 | 0.25 |  |
| JS-A11Y-ARIA-REQUIRED-ATTRIBUTE | deterministic | jsx-a11y:role-has-required-aria-props | 30 | 2 | 0 | 16 | 1 | 0 | 13 | 1.00 | 0.94 |  |
| JS-A11Y-AUTOCOMPLETE-INVALID | ai-confirm | jsx-a11y:autocomplete-valid | 22 | 4 | 0 | 2 | 2 | 0 | 18 | 1.00 | 0.50 |  |
| JS-A11Y-CONTROL-WITHOUT-LABEL | ai-confirm | jsx-a11y:control-has-associated-label | 3 | 0 | 0 | 1 | 0 | 0 | 2 | 1.00 | 1.00 |  |
| JS-A11Y-EMPTY-HEADING | ai-confirm | jsx-a11y:heading-has-content | 19 | 13 | 0 | 2 | 2 | 0 | 15 | 1.00 | 0.50 |  |
| JS-A11Y-IMG-REDUNDANT-ALT | deterministic | jsx-a11y:img-redundant-alt | 50 | 9 | 0 | 13 | 6 | 0 | 31 | 1.00 | 0.68 |  |
| JS-A11Y-MOUSE-WITHOUT-KEYBOARD | ai-confirm | jsx-a11y:mouse-events-have-key-events | 26 | 13 | 0 | 1 | 5 | 0 | 20 | 1.00 | 0.17 |  |
| VUE-A11Y-ARIA-INVALID-ATTRIBUTE | ai-confirm | vuejs-accessibility:aria-props | 2 | 0 | 0 | 1 | 0 | 0 | 1 | 1.00 | 1.00 |  |
| VUE-A11Y-ARIA-INVALID-ROLE | ai-confirm | vuejs-accessibility:aria-role | 6 | 1 | 0 | 1 | 1 | 0 | 4 | 1.00 | 0.50 |  |
| VUE-A11Y-CONTROL-WITHOUT-LABEL | deterministic | vuejs-accessibility:form-control-has-label | 22 | 2 | 0 | 2 | 5 | 0 | 15 | 1.00 | 0.29 |  |
| VUE-A11Y-MARQUEE-OR-BLINK | ai-confirm | vuejs-accessibility:no-distracting-elements | 3 | 1 | 0 | 2 | 0 | 0 | 1 | 1.00 | 1.00 |  |
| VUE-A11Y-POSITIVE-TABINDEX | ai-confirm | vuejs-accessibility:tabindex-no-positive | 7 | 0 | 0 | 2 | 1 | 0 | 4 | 1.00 | 0.67 |  |
| CSS-A11Y-FOCUS-OUTLINE-REMOVED | ai-confirm | axe:focus-order-semantics | 1 | 0 | 0 | 0 | 6 | 0 | 0 | - | 0.00 |  |
| CSS-A11Y-FOCUS-VISIBLE-OUTLINE-REMOVED | ai-confirm | stylelint:a11y/no-outline-none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| CSS-A11Y-FONT-SIZE-VIEWPORT-ONLY | ai-confirm | stylelint:a11y/font-size-is-readable | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| CSS-A11Y-LOW-CONTRAST | ai-confirm | axe:color-contrast | 1 | 1 | 0 | 0 | 14 | 0 | 0 | - | 0.00 |  |
| CSS-A11Y-LOW-CONTRAST-ENHANCED | ai-confirm | axe:color-contrast-enhanced | 1 | 0 | 0 | 0 | 2 | 0 | 0 | - | 0.00 |  |
| CSS-A11Y-OUTLINE-REMOVED-ON-CONTROLS | ai-confirm | stylelint:a11y/no-outline-none | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| CSS-A11Y-REDUCED-MOTION-MISSING | ai-confirm | stylelint:a11y/media-prefers-reduced-motion | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| HTML-A11Y-AMBIGUOUS-LINK-TEXT | ai-confirm | axe:link-name | 1 | 0 | 0 | 0 | 5 | 0 | 0 | - | 0.00 |  |
| HTML-A11Y-ARIA-REQUIRED-ATTRIBUTE | ai-confirm | axe:aria-required-attr | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| HTML-A11Y-AUTOCOMPLETE-INVALID | ai-confirm | axe:autocomplete-valid | 1 | 0 | 0 | 0 | 5 | 0 | 0 | - | 0.00 |  |
| HTML-A11Y-DUPLICATE-ID | ai-confirm | axe:duplicate-id | 1 | 2 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| HTML-A11Y-IMG-REDUNDANT-ALT | ai-confirm | jsx-a11y:img-redundant-alt | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| HTML-A11Y-MAIN-LANDMARK-MISSING | ai-confirm | axe:landmark-one-main | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite not found |
| HTML-A11Y-MOUSE-WITHOUT-KEYBOARD | ai-confirm | jsx-a11y:mouse-events-have-key-events | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| HTML-A11Y-NESTED-INTERACTIVE | ai-confirm | axe:nested-interactive | 1 | 0 | 0 | 0 | 5 | 0 | 0 | - | 0.00 |  |
| HTML-A11Y-TABLE-WITHOUT-HEADERS | ai-confirm | axe:td-has-header | 1 | 0 | 0 | 0 | 2 | 0 | 0 | - | 0.00 |  |
| HTML-A11Y-VIDEO-WITHOUT-CAPTIONS | ai-confirm | axe:video-caption | 1 | 0 | 0 | 0 | 0 | 0 | 0 | - | - |  |
| JS-A11Y-ARIA-LABEL-ON-GENERIC | ai-confirm | axe:aria-prohibited-attr | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-AUTOPLAY-WITH-SOUND | ai-confirm | axe:no-autoplay-audio | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-BUTTON-WITHOUT-NAME | ai-confirm | axe:button-name | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-DUPLICATE-ID | ai-confirm | axe:duplicate-id | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-HEADING-SKIPPED-LEVEL | ai-confirm | axe:heading-order | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-INPUT-IMAGE-WITHOUT-ALT | ai-confirm | axe:input-image-alt | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-LANG-INVALID | ai-confirm | jsx-a11y:lang | 15 | 4 | 0 | 0 | 3 | 0 | 12 | - | 0.00 |  |
| JS-A11Y-NESTED-INTERACTIVE | ai-confirm | axe:nested-interactive | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-ROLE-IMG-WITHOUT-NAME | ai-confirm | axe:role-img-alt | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-TABLE-WITHOUT-HEADERS | ai-confirm | axe:td-has-header | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| JS-A11Y-TH-INVALID-SCOPE | ai-confirm | axe:scope-attr-valid | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-AMBIGUOUS-LINK-TEXT | ai-confirm | axe:link-name | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-ARIA-LABEL-ON-GENERIC | ai-confirm | axe:aria-prohibited-attr | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-ARIA-REQUIRED-ATTRIBUTE | ai-confirm | vuejs-accessibility:role-has-required-aria-props | 7 | 0 | 0 | 0 | 3 | 0 | 4 | - | 0.00 |  |
| VUE-A11Y-AUTOCOMPLETE-INVALID | ai-confirm | axe:autocomplete-valid | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-AUTOPLAY-WITH-SOUND | ai-confirm | axe:no-autoplay-audio | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-BUTTON-WITHOUT-NAME | ai-confirm | axe:button-name | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-CLICK-WITHOUT-KEYBOARD | deterministic | vuejs-accessibility:click-events-have-key-events | 33 | 0 | 0 | 0 | 11 | 0 | 22 | - | 0.00 |  |
| VUE-A11Y-DUPLICATE-ID | ai-confirm | axe:duplicate-id | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-EMPTY-HEADING | deterministic | vuejs-accessibility:heading-has-content | 10 | 4 | 0 | 0 | 4 | 0 | 6 | - | 0.00 |  |
| VUE-A11Y-HEADING-SKIPPED-LEVEL | ai-confirm | axe:heading-order | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-IFRAME-WITHOUT-TITLE | ai-confirm | vuejs-accessibility:iframe-has-title | 5 | 0 | 0 | 0 | 3 | 0 | 2 | - | 0.00 |  |
| VUE-A11Y-IMG-REDUNDANT-ALT | ai-confirm | vuejs-accessibility:alt-text | 16 | 2 | 0 | 0 | 6 | 0 | 10 | - | 0.00 |  |
| VUE-A11Y-IMG-WITHOUT-ALT | ai-confirm | vuejs-accessibility:alt-text | 16 | 2 | 0 | 0 | 6 | 0 | 10 | - | 0.00 |  |
| VUE-A11Y-INPUT-IMAGE-WITHOUT-ALT | ai-confirm | axe:input-image-alt | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-LANG-INVALID | ai-confirm | axe:valid-lang | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-LINK-WITHOUT-NAME | ai-confirm | vuejs-accessibility:anchor-has-content | 12 | 4 | 0 | 0 | 2 | 0 | 10 | - | 0.00 |  |
| VUE-A11Y-MOUSE-WITHOUT-KEYBOARD | ai-confirm | vuejs-accessibility:mouse-events-have-key-events | 7 | 0 | 0 | 0 | 4 | 0 | 3 | - | 0.00 |  |
| VUE-A11Y-NESTED-INTERACTIVE | ai-confirm | axe:nested-interactive | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-ROLE-IMG-WITHOUT-NAME | ai-confirm | axe:role-img-alt | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-TABLE-WITHOUT-HEADERS | ai-confirm | axe:td-has-header | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-TH-INVALID-SCOPE | ai-confirm | axe:scope-attr-valid | 0 | 0 | 0 | 0 | 0 | 0 | 0 | - | - | suite written for another syntax |
| VUE-A11Y-VIDEO-WITHOUT-CAPTIONS | ai-confirm | vuejs-accessibility:media-has-caption | 38 | 0 | 0 | 0 | 17 | 0 | 21 | - | 0.00 |  |

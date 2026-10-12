package config

import _ "embed"

// Template is the shipped default .crev.yaml written by `crev init`. It is deliberately separate from
// this repository's own .crev.yaml (which only tunes scanning crev's source tree).
//
//go:embed template.crev.yaml
var Template []byte

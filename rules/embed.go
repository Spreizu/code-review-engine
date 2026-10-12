// Package catalog embeds the rule packs and version data shipped with crev.
package catalog

import "embed"

// FS holds packs/*/*.yaml and data/*.yaml.
//
//go:embed packs/*/*.yaml data/*.yaml
var FS embed.FS

// Package grammars maps rule language ids to tree-sitter languages.
//
// Official/maintained Go bindings are used where they exist; grammars without a usable Go
// binding are vendored (vue, dockerfile, proto, graphql) under internal/grammars/<name>.
package grammars

import (
	tsgroovy "github.com/amaanq/tree-sitter-groovy/bindings/go"
	tshcl "github.com/tree-sitter-grammars/tree-sitter-hcl/bindings/go"
	tskotlin "github.com/tree-sitter-grammars/tree-sitter-kotlin/bindings/go"
	tsxml "github.com/tree-sitter-grammars/tree-sitter-xml/bindings/go"
	tsyaml "github.com/tree-sitter-grammars/tree-sitter-yaml/bindings/go"
	ts "github.com/tree-sitter/go-tree-sitter"
	tscss "github.com/tree-sitter/tree-sitter-css/bindings/go"
	tsgo "github.com/tree-sitter/tree-sitter-go/bindings/go"
	tshtml "github.com/tree-sitter/tree-sitter-html/bindings/go"
	tsjava "github.com/tree-sitter/tree-sitter-java/bindings/go"
	tsjs "github.com/tree-sitter/tree-sitter-javascript/bindings/go"
	tsjson "github.com/tree-sitter/tree-sitter-json/bindings/go"
	tsphp "github.com/tree-sitter/tree-sitter-php/bindings/go"
	tspython "github.com/tree-sitter/tree-sitter-python/bindings/go"
	tsts "github.com/tree-sitter/tree-sitter-typescript/bindings/go"

	"github.com/elmo/code-review-engine/internal/grammars/dockerfile"
	"github.com/elmo/code-review-engine/internal/grammars/graphql"
	"github.com/elmo/code-review-engine/internal/grammars/proto"
	"github.com/elmo/code-review-engine/internal/grammars/vue"
)

// Names lists every grammar id Get understands.
var Names = []string{"java", "javascript", "typescript", "tsx", "vue", "go", "python", "php", "kotlin", "groovy",
	"json", "yaml", "xml", "hcl", "dockerfile", "proto", "graphql", "html", "css"}

// Get returns the language for an id.
func Get(id string) *ts.Language {
	switch id {
	case "java":
		return ts.NewLanguage(tsjava.Language())
	case "javascript", "js", "jsx":
		return ts.NewLanguage(tsjs.Language())
	case "typescript", "ts":
		return ts.NewLanguage(tsts.LanguageTypescript())
	case "tsx":
		return ts.NewLanguage(tsts.LanguageTSX())
	case "vue":
		return ts.NewLanguage(vue.Language())
	case "go":
		return ts.NewLanguage(tsgo.Language())
	case "python":
		return ts.NewLanguage(tspython.Language())
	case "php":
		return ts.NewLanguage(tsphp.LanguagePHP()) // PHP with HTML outside <?php ?>
	case "kotlin":
		return ts.NewLanguage(tskotlin.Language())
	case "groovy":
		return ts.NewLanguage(tsgroovy.Language())
	case "json":
		return ts.NewLanguage(tsjson.Language())
	case "yaml":
		return ts.NewLanguage(tsyaml.Language())
	case "xml":
		return ts.NewLanguage(tsxml.LanguageXML())
	case "hcl", "terraform":
		return ts.NewLanguage(tshcl.Language())
	case "dockerfile":
		return ts.NewLanguage(dockerfile.Language())
	case "proto", "protobuf":
		return ts.NewLanguage(proto.Language())
	case "graphql":
		return ts.NewLanguage(graphql.Language())
	case "css", "scss", "less":
		return ts.NewLanguage(tscss.Language()) // official CSS grammar; SCSS/Less files parse their CSS subset
	case "html":
		return ts.NewLanguage(tshtml.Language()) // Angular external templates (control-flow blocks parse as text)
	}
	return nil
}

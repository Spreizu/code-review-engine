package rules

import "testing"

func TestEslintFullKey(t *testing.T) {
	for in, want := range map[string]string{
		"typescript-eslint:no-explicit-any":                    "typescript-eslint:@typescript-eslint/no-explicit-any",
		"typescript-eslint:@typescript-eslint/no-explicit-any": "",
		"eslint-plugin-vue:require-v-for-key":                  "eslint-plugin-vue:vue/require-v-for-key",
		"eslint:no-console":                                    "",
	} {
		if got := eslintFullKey(in); got != want {
			t.Errorf("eslintFullKey(%q) = %q, want %q", in, got, want)
		}
	}
}

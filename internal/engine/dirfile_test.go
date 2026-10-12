package engine

import (
	"os"
	"path/filepath"
	"testing"
)

func TestDirHasFileWalksUpToRoot(t *testing.T) {
	root := t.TempDir()
	sub := filepath.Join(root, "packages", "web")
	if err := os.MkdirAll(sub, 0o755); err != nil {
		t.Fatal(err)
	}
	names := []string{"package-lock.json", "yarn.lock"}
	if dirHasFile(sub, root, names) {
		t.Fatal("no lockfile yet")
	}
	if err := os.WriteFile(filepath.Join(root, "yarn.lock"), nil, 0o644); err != nil {
		t.Fatal(err)
	}
	if !dirHasFile(sub, root, names) {
		t.Fatal("workspace-root lockfile must count for a nested package")
	}
	if dirHasFile(filepath.Dir(root), filepath.Join(filepath.Dir(root), "x"), []string{"nope"}) {
		t.Fatal("outside root")
	}
}

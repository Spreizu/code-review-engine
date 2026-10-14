package versions

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParentPomJava(t *testing.T) {
	root := t.TempDir()
	must := func(p, s string) {
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte(s), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	must(filepath.Join(root, "acme-parent/pom.xml"), `<project><properties><maven.compiler.release>17</maven.compiler.release></properties></project>`)
	must(filepath.Join(root, "acme-core/pom.xml"), `<project><parent><artifactId>acme-parent</artifactId><relativePath>../acme-parent</relativePath></parent></project>`)
	u := DetectUnit(filepath.Join(root, "acme-core"))
	if u.Facts["java"].Version != "17" {
		t.Fatalf("java = %+v, want 17 from the sibling parent pom", u.Facts["java"])
	}
}

func TestPomJavaIgnoresProfiles(t *testing.T) {
	root := t.TempDir()
	pom := `<project><properties><javac.src.version>17</javac.src.version></properties>
<profiles><profile><id>jdk21</id><build><plugins><plugin><artifactId>maven-compiler-plugin</artifactId>
<configuration><release>21</release></configuration></plugin></plugins></build></profile></profiles></project>`
	if err := os.WriteFile(filepath.Join(root, "pom.xml"), []byte(pom), 0o644); err != nil {
		t.Fatal(err)
	}
	if v := DetectUnit(root).Facts["java"].Version; v != "17" {
		t.Fatalf("java = %q, want 17 (profile release ignored)", v)
	}
}

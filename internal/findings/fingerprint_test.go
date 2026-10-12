package findings

import "testing"

func TestFingerprintStability(t *testing.T) {
	base := Fingerprint("GO-X", "a.go", "func (this *S) Run() {}", "S#Run", 1)
	if base != Fingerprint("GO-X", "a.go", "  func (this *S)\n\tRun() {}  ", "S#Run", 1) {
		t.Fatal("whitespace/reflow must not change the fingerprint")
	}
	// line numbers are not part of the fingerprint: shifting code keeps the identity
	for name, other := range map[string]string{
		"rule":    Fingerprint("GO-Y", "a.go", "func (this *S) Run() {}", "S#Run", 1),
		"path":    Fingerprint("GO-X", "b.go", "func (this *S) Run() {}", "S#Run", 1),
		"code":    Fingerprint("GO-X", "a.go", "func (this *S) Stop() {}", "S#Run", 1),
		"symbol":  Fingerprint("GO-X", "a.go", "func (this *S) Run() {}", "T#Run", 1),
		"ordinal": Fingerprint("GO-X", "a.go", "func (this *S) Run() {}", "S#Run", 2),
	} {
		if other == base {
			t.Errorf("%s must change the fingerprint", name)
		}
	}
}

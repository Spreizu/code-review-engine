package engine

import (
	"testing"

	"github.com/elmo/code-review-engine/internal/rules"
)

func TestParseXMLAndKeyRe(t *testing.T) {
	src := `<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <application android:debuggable="true" android:allowBackup="false">
    <activity android:name=".A" android:exported="true"/>
    <activity android:name=".B" android:exported="true" android:permission="com.x.P"/>
  </application>
</manifest>
`
	c, err := ParseConfig("AndroidManifest.xml", []byte(src))
	if err != nil {
		t.Fatal(err)
	}
	if v := c["manifest.application.@debuggable"]; v.Value != "true" || v.Line != 3 {
		t.Fatalf("debuggable: %+v", v)
	}
	if _, ok := c["manifest.application.activity#2.@permission"]; !ok {
		t.Fatalf("second activity missing: %v", c)
	}
	r := &rules.Rule{}
	r.Detection.Config = map[string]any{"key_re": `^manifest\.application\.activity(#\d+)?$`, "op": "matches", "value": `\bexported=true\b`, "unless_value": `\bpermission=`}
	h, err := EvalConfig(r, c)
	if err != nil || len(h) != 1 || h[0].Line != 4 {
		t.Fatalf("hits %+v %v", h, err)
	}
}

func TestXMLUnlessChildAndStartLine(t *testing.T) {
	src := []byte("<manifest>\n  <application>\n    <activity\n      exported=\"true\">\n      <intent-filter>\n        <category name=\"android.intent.category.LAUNCHER\"/>\n      </intent-filter>\n    </activity>\n    <service exported=\"true\"/>\n  </application>\n</manifest>\n")
	c, err := parseXML(src)
	if err != nil {
		t.Fatal(err)
	}
	if got := c["manifest.application.activity"].Line; got != 3 {
		t.Fatalf("activity line = %d, want 3 (start of tag)", got)
	}
	r := &rules.Rule{}
	r.Detection.Config = map[string]any{"key_re": `^manifest\.application\.(activity|service)$`, "op": "matches", "value": `exported=true`,
		"unless_child": `intent-filter\.category\.@name=android\.intent\.category\.LAUNCHER$`}
	hits, err := EvalConfig(r, c)
	if err != nil {
		t.Fatal(err)
	}
	if len(hits) != 1 || hits[0].Key != "manifest.application.service" {
		t.Fatalf("hits = %+v", hits)
	}
}

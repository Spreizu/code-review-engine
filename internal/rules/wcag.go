package rules

import (
	"sort"
	"strings"
)

// WCAGCriterion is one WCAG 2.x success criterion: its conformance level and the WCAG version
// that introduced it (2.0, 2.1 or 2.2). Name is the criterion's official short title.
type WCAGCriterion struct {
	ID, Name, Level, Since string
	// Obsolete: removed in a later version (4.1.1 Parsing is obsolete in WCAG 2.2).
	Obsolete bool
}

// WCAG lists every WCAG 2.2 success criterion (plus the obsolete 4.1.1), keyed by id
// (https://www.w3.org/TR/WCAG22/). Rules tag the criteria they check in their `wcag` field.
var WCAG = map[string]WCAGCriterion{}

func init() {
	for _, row := range strings.Split(strings.TrimSpace(wcagTable), "\n") {
		f := strings.Split(row, "|")
		c := WCAGCriterion{ID: f[0], Level: f[1], Since: f[2], Name: f[3]}
		if len(f) > 4 {
			c.Obsolete = true
		}
		WCAG[c.ID] = c
	}
}

// WCAGLevel is the strictest (lowest) conformance level among ids: "A" before "AA" before "AAA";
// "" when none is known.
func WCAGLevel(ids []string) string {
	best := ""
	for _, id := range ids {
		l := WCAG[id].Level
		if l != "" && (best == "" || len(l) < len(best)) {
			best = l
		}
	}
	return best
}

// WCAGLabels renders ids as "1.4.3 Contrast (Minimum) (AA)", sorted by id.
func WCAGLabels(ids []string) []string {
	var out []string
	for _, id := range ids {
		if c, ok := WCAG[id]; ok {
			out = append(out, c.ID+" "+c.Name+" ("+c.Level+")")
		}
	}
	sort.Strings(out)
	return out
}

const wcagTable = `
1.1.1|A|2.0|Non-text Content
1.2.1|A|2.0|Audio-only and Video-only (Prerecorded)
1.2.2|A|2.0|Captions (Prerecorded)
1.2.3|A|2.0|Audio Description or Media Alternative (Prerecorded)
1.2.4|AA|2.0|Captions (Live)
1.2.5|AA|2.0|Audio Description (Prerecorded)
1.2.6|AAA|2.0|Sign Language (Prerecorded)
1.2.7|AAA|2.0|Extended Audio Description (Prerecorded)
1.2.8|AAA|2.0|Media Alternative (Prerecorded)
1.2.9|AAA|2.0|Audio-only (Live)
1.3.1|A|2.0|Info and Relationships
1.3.2|A|2.0|Meaningful Sequence
1.3.3|A|2.0|Sensory Characteristics
1.3.4|AA|2.1|Orientation
1.3.5|AA|2.1|Identify Input Purpose
1.3.6|AAA|2.1|Identify Purpose
1.4.1|A|2.0|Use of Color
1.4.2|A|2.0|Audio Control
1.4.3|AA|2.0|Contrast (Minimum)
1.4.4|AA|2.0|Resize Text
1.4.5|AA|2.0|Images of Text
1.4.6|AAA|2.0|Contrast (Enhanced)
1.4.7|AAA|2.0|Low or No Background Audio
1.4.8|AAA|2.0|Visual Presentation
1.4.9|AAA|2.0|Images of Text (No Exception)
1.4.10|AA|2.1|Reflow
1.4.11|AA|2.1|Non-text Contrast
1.4.12|AA|2.1|Text Spacing
1.4.13|AA|2.1|Content on Hover or Focus
2.1.1|A|2.0|Keyboard
2.1.2|A|2.0|No Keyboard Trap
2.1.3|AAA|2.0|Keyboard (No Exception)
2.1.4|A|2.1|Character Key Shortcuts
2.2.1|A|2.0|Timing Adjustable
2.2.2|A|2.0|Pause, Stop, Hide
2.2.3|AAA|2.0|No Timing
2.2.4|AAA|2.0|Interruptions
2.2.5|AAA|2.0|Re-authenticating
2.2.6|AAA|2.1|Timeouts
2.3.1|A|2.0|Three Flashes or Below Threshold
2.3.2|AAA|2.0|Three Flashes
2.3.3|AAA|2.1|Animation from Interactions
2.4.1|A|2.0|Bypass Blocks
2.4.2|A|2.0|Page Titled
2.4.3|A|2.0|Focus Order
2.4.4|A|2.0|Link Purpose (In Context)
2.4.5|AA|2.0|Multiple Ways
2.4.6|AA|2.0|Headings and Labels
2.4.7|AA|2.0|Focus Visible
2.4.8|AAA|2.0|Location
2.4.9|AAA|2.0|Link Purpose (Link Only)
2.4.10|AAA|2.0|Section Headings
2.4.11|AA|2.2|Focus Not Obscured (Minimum)
2.4.12|AAA|2.2|Focus Not Obscured (Enhanced)
2.4.13|AAA|2.2|Focus Appearance
2.5.1|A|2.1|Pointer Gestures
2.5.2|A|2.1|Pointer Cancellation
2.5.3|A|2.1|Label in Name
2.5.4|A|2.1|Motion Actuation
2.5.5|AAA|2.1|Target Size (Enhanced)
2.5.6|AAA|2.1|Concurrent Input Mechanisms
2.5.7|AA|2.2|Dragging Movements
2.5.8|AA|2.2|Target Size (Minimum)
3.1.1|A|2.0|Language of Page
3.1.2|AA|2.0|Language of Parts
3.1.3|AAA|2.0|Unusual Words
3.1.4|AAA|2.0|Abbreviations
3.1.5|AAA|2.0|Reading Level
3.1.6|AAA|2.0|Pronunciation
3.2.1|A|2.0|On Focus
3.2.2|A|2.0|On Input
3.2.3|AA|2.0|Consistent Navigation
3.2.4|AA|2.0|Consistent Identification
3.2.5|AAA|2.0|Change on Request
3.2.6|A|2.2|Consistent Help
3.3.1|A|2.0|Error Identification
3.3.2|A|2.0|Labels or Instructions
3.3.3|AA|2.0|Error Suggestion
3.3.4|AA|2.0|Error Prevention (Legal, Financial, Data)
3.3.5|AAA|2.0|Help
3.3.6|AAA|2.0|Error Prevention (All)
3.3.7|A|2.2|Redundant Entry
3.3.8|AA|2.2|Accessible Authentication (Minimum)
3.3.9|AAA|2.2|Accessible Authentication (Enhanced)
4.1.1|A|2.0|Parsing|obsolete
4.1.2|A|2.0|Name, Role, Value
4.1.3|AA|2.1|Status Messages
`

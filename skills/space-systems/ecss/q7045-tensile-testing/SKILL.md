---
name: q7045-tensile-testing
description: "Compute the tensile properties of a metallic specimen from its stress-strain record. Use when a tension test has been run under ECSS-Q-ST-70-45 and the properties have to be reported: fit the modulus by least squares over a declared elastic window and report the quality of that fit, locate the offset proof strength where the shifted line crosses the record, take the ultimate strength from the peak of the curve rather than its last point, derive elongation and reduction of area from the broken halves, and refuse a record whose strain does not increase. Trigger: ecss, q-st-70-45, metallic-tensile-offset-proof-strength, tensile-ultimate-strength-peak, tensile-elongation-after-fracture, tensile-modulus-least-squares-window, tensile-reduction-of-area."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-70-45-mechanical-testing-scope, q7045-tensile-testing, metallic-tensile-offset-proof-strength, tensile-ultimate-strength-peak, tensile-elongation-after-fracture, tensile-modulus-least-squares-window, tensile-reduction-of-area]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing of Metals -- Tensile Testing (space-systems/ecss/q7045-tensile-testing)

Use when the task is the tension test of the methods clause of
ECSS-Q-ST-70-45: a specimen of declared gauge length has been pulled to
fracture, the load-extension record has been converted to engineering stress
and strain, and the question is which properties the record supports and
which of them have to be reported with a caveat.

## Domain quick reference

- Modulus is a fit, not a ratio of two points. It is the least-squares slope
  over a declared elastic window, and it only means anything alongside the
  quality of that fit; a window that has crept past the knee still returns a
  slope, and the slope it returns is too low and looks plausible.
- Proof strength is a crossing, not a sample. The offset line of slope E,
  shifted by the offset strain, meets the record inside one segment; the
  crossing is interpolated in that segment rather than snapped to whichever
  recorded point happens to sit nearest it.
- Ultimate strength is the peak of the engineering curve. On a ductile alloy
  the peak sits well before the last point, because necking drops the
  engineering stress while the specimen is still extending.
- Elongation and reduction of area come from the broken halves. Crosshead
  strain at fracture includes the compliance of the frame and the grips, so
  it is a machine property, not a material property.
- A specified minimum is a floor the measured value may sit exactly on. A
  property landing on its minimum is compliant, and rejecting it is a defect
  of the comparison, not a finding about the material.

## Workflow

1. Validate the record: every point carries a strain and a stress, neither is
   negative, and the strain strictly increases through the whole record.
2. Fit the modulus over the declared elastic window, requiring at least three
   points inside it, and keep the fit quality beside the slope.
3. Build the offset line from that modulus and the offset strain, walk the
   record for the segment where the record falls below it, and interpolate
   the crossing inside that segment.
4. Scan for the peak engineering stress and keep the strain it occurred at,
   so uniform elongation is available and necking is visible.
5. Reduce the broken halves into elongation after fracture and, when the
   fracture section was measured, reduction of area.
6. Compare each property against its specified minimum with an inclusive
   test, and report the modulus fit quality as a finding when the declared
   window was not elastic.

## Pitfalls

- Taking the modulus from the first and last point of the window. Two points
  always fit a line perfectly and the fit quality that would have exposed the
  bad window is then unavailable.
- Reporting the last recorded stress as the ultimate strength. On anything
  ductile that is the fracture stress and it understates the material.
- Snapping the proof strength to the nearest sample. On a coarse record that
  moves the reported value by tens of megapascals with no trace in the report.
- Using crosshead travel for elongation after fracture. The frame and the
  grips are in that number and the specimen is not the only thing that
  stretched.
- Treating a property that lands exactly on its specified minimum as a
  failure. Floating-point representation of the minimum is what failed, and
  the comparison has to absorb it.

## Behavior contract (gate 3)

The record validation, least-squares modulus with its fit quality, offset
proof-strength crossing, peak detection, elongation and reduction of area,
and the comparison against specified minima are exercised by the gate 3
contract test: scripts/test_q7045_tensile_testing.py against
scripts/q7045_tensile_testing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7045_tensile_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

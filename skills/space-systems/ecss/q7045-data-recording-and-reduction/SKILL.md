---
name: q7045-data-recording-and-reduction
description: "Convert a recorded force-extension trace into the material properties a mechanical test report carries. Use when a test under ECSS-Q-ST-70-45 has produced raw channel data and someone has to turn it into numbers: normalise every quantity through a unit registry that refuses an unknown unit, check the record advances monotonically, form engineering stress and strain from the original section and gauge length, fit the modulus by least squares over a declared elastic window with its coefficient of determination as evidence, intersect the offset line to get the proof strength, and take the tensile strength and the elongation after fracture. Trigger: ecss, q-st-70-45-mechanical-testing, tensile-curve-data-reduction, tensile-offset-proof-strength-extraction, tensile-modulus-least-squares-window, tensile-engineering-stress-strain-conversion, tensile-test-unit-normalisation."
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
  tags: [ecss, q-st-70-45-mechanical-testing, q7045-data-recording-and-reduction, tensile-curve-data-reduction, tensile-offset-proof-strength-extraction, tensile-modulus-least-squares-window, tensile-engineering-stress-strain-conversion, tensile-test-unit-normalisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing — Data Recording and Reduction (space-systems/ecss/q7045-data-recording-and-reduction)

Use when the task is the data step of a mechanical test under
ECSS-Q-ST-70-45: the machine has written a force and an extension
channel, and the report needs a modulus, a proof strength, a tensile
strength and an elongation that can each be traced back to the trace
they came from.

## Domain quick reference

- Units are part of the data, not a footnote. A registry that refuses an
  unrecognised unit is what stops a kilonewton column being read as
  newtons; a reduction that guesses is off by a thousand and still
  produces a curve that looks plausible.
- A record has to advance. A trace that goes backwards, or repeats an
  extension, is a rewind, a duplicated block or a slipped extensometer,
  and no property taken from it means anything.
- Engineering stress and strain are referred to the original section and
  the original gauge length throughout, including past maximum force.
  That is what makes the maximum of the curve the tensile strength.
- A modulus is a fit, so it carries a fit quality. The coefficient of
  determination over the declared window is the evidence the window was
  elastic; a window that reaches into the knee bends the line and drops
  it, which is the signal to move the window rather than the floor.
- The offset proof strength is an intersection, not a curve reading. The
  offset line rises from the offset strain with the fitted slope, and
  the proof strength is where the recorded curve first falls back
  through it, interpolated between the two bracketing points.
- A record that stops inside the elastic range has no proof strength at
  all. Reporting the last recorded stress instead invents a yield.

## Workflow

1. Normalise force and length through the unit registry; refuse any unit
   not in it rather than assuming a default.
2. Validate the record: enough points, finite, non-negative, and
   strictly advancing in extension.
3. Form the original cross-section from a diameter or from width and
   thickness, and convert the record into engineering stress and strain.
4. Fit the modulus by least squares over the declared strain window,
   keeping the slope, the intercept and the coefficient of
   determination, and raise a finding when the fit quality falls under
   its floor.
5. Intersect the offset line with the curve, interpolating between the
   bracketing points, and report no proof strength rather than a
   substitute when the curve never crosses it.
6. Take the maximum stress and the strain it occurred at, and the
   elongation after fracture when the specimen was reassembled and
   remeasured.
7. Report the properties with every finding attached, and mark the
   record reportable only when nothing was raised.

## Pitfalls

- Letting an unrecognised unit through with a default. The factor of a
  thousand between newtons and kilonewtons survives every downstream
  sanity check because the curve shape is unchanged.
- Fitting the modulus over the whole rise to yield. The knee is inside
  that range, so the slope comes out low and the proof strength moves
  with it.
- Relaxing the fit-quality floor to keep a window. The floor is the
  detector for a window that is not elastic; moving it deletes the
  detector and keeps the defect.
- Reading the proof strength off the curve at the offset strain. That is
  a point on the curve, not the intersection with the offset line, and
  it is low by the whole elastic recovery.
- Taking the last recorded stress as a yield when the test was stopped
  early. No crossing means no proof strength, and that is the result.

## Behavior contract (gate 3)

The unit registry, record validation, engineering conversion,
least-squares modulus window, offset-line intersection, tensile-strength
maximum and elongation after fracture are exercised by the gate 3
contract test:
scripts/test_q7045_data_recording_and_reduction.py against
scripts/q7045_data_recording_and_reduction_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7045_data_recording_and_reduction.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

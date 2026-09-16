---
name: e2008-working-standard-linearity
description: "Use when an irradiance sweep must become a linearity verdict. Assess the linearity of a secondary working standard by the method the referenced photovoltaic standard sets out, for ECSS-E-ST-20-08C clause 10.2.2.3.3: turn each short-circuit-current reading into a responsivity per unit irradiance, anchor a reference responsivity on the points taken at the reference irradiance, express every other point as a deviation from it, fit current against irradiance by least squares so a non-zero intercept shows as an offset instead of hiding inside the slope, check the irradiance range the points actually span, and name the irradiance carrying the worst deviation. Trigger: ecss, e-st-20-08c, clause-10-2-2-3-3, working-standard-linearity, responsivity-deviation-band, irradiance-range-coverage, least-squares-offset-check."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-working-standard-linearity, e-st-20-08c, clause-10-2-2-3-3, working-standard-linearity, responsivity-deviation-band, irradiance-range-coverage, least-squares-offset-check, photovoltaic-working-standard-irradiance-sweep]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Working Standard Linearity (space-systems/ecss/e2008-working-standard-linearity)

Use when the task is clause 10.2.2.3.3 of ECSS-E-ST-20-08C: establishing
that a secondary working standard responds linearly, by the method the
referenced photovoltaic measurement standard sets out. This leaf reads
one irradiance sweep and returns a per-point disposition, the fit it
implies, and the device verdict.

## Domain quick reference

- The clause writes no method of its own; it defers to the referenced
  photovoltaic standard. The device record therefore has to name the
  method it was measured by. A sweep with no declared method is a set of
  numbers, not an assessment, and cannot be dispositioned.
- The quantity under test is not the current. A working standard is used
  to read an irradiance from a current, so what has to be constant is the
  current per unit irradiance. That responsivity is what the assessment
  works in.
- The anchor is the reference irradiance, not the average of the sweep.
  That is where the device's calibration value lives, so a deviation
  reported against it is a deviation from the condition the device is
  actually certified at.
- If no point sits at the reference level the sweep has nothing to anchor
  on, and the honest answer is that the assessment cannot be made rather
  than an average substituted for the anchor.
- The straight-line fit earns its place by separating slope from
  intercept. A device with a dark or leakage current reports current with
  no light on it, and that is a fixed error rather than a curvature.
- A fixed offset bites hardest at the bottom of the range. It is a
  constant number of amps against a current that is falling, so the
  relative error grows as the light goes down; that is why it appears as
  a rising deviation at low irradiance.
- The range the sweep spans is part of the result. A device shown to be
  linear only around one sun says nothing about the low-irradiance end it
  is later used at, so the endpoints and the ratio between them are
  checked against what the assessment has to cover.
- A current that falls while the irradiance rises is not a linearity
  figure. It is a reading that went wrong, and it is reported as such
  instead of being folded into a deviation.

## Workflow

1. Resolve the device: identifier, the referenced method it was measured
   by, and the sweep. Reject a sweep with too few points to show a shape.
2. Convert every point to a responsivity, sort by irradiance and reject a
   repeated irradiance, which is a repeat reading rather than a point.
3. Anchor the reference responsivity on the points inside the band around
   the reference irradiance, and refuse the assessment if there are none.
4. Express each point as a fractional deviation from the anchor and
   disposition it against the accept band and its review band above.
5. Fit current against irradiance by least squares, and screen the
   intercept as a share of the reference current.
6. Check the lowest and highest irradiance reached and the ratio between
   them against the range the assessment has to cover.
7. Report any step where the current fell as the irradiance rose.
8. Take the worst disposition, add the offset, coverage and monotonicity
   findings, and name the irradiance carrying the worst deviation.

## Pitfalls

- Assessing the sweep without recording which referenced method produced
  it. The clause's whole content is that the method comes from the
  referenced standard, so an unnamed method is the finding.
- Judging linearity on the currents. Currents rise across a sweep by
  design; only the responsivity is supposed to stay put.
- Anchoring on the mean responsivity of the sweep. That buries part of
  the departure in the reference and moves the anchor away from the
  condition the device is certified at.
- Substituting an average anchor when no point was taken at the reference
  level. The sweep is not anchored and the assessment is not available.
- Fitting a line through the origin because the device should read zero
  in the dark. Forcing the intercept to zero pushes a real offset into
  the slope, where it looks like a sensitivity error instead.
- Reading a large deviation at the bottom of the range as curvature
  without checking the intercept. A constant offset produces exactly that
  shape and has a different cause and a different fix.
- Sweeping only around one sun and declaring the device linear. The range
  the points span is part of the answer, not a detail of the setup.
- Folding a falling reading into the deviation statistics. It is a
  measurement failure and it has to be reported as one.
- Comparing a deviation with its band by bare arithmetic. Both sides are
  ratios of measured quantities, so a point sitting exactly on the band
  can evaluate a few units in the last place above it; the comparison
  absorbs that representation error while the band stays untouched.

## Behavior contract (gate 3)

The criteria validation, the responsivity conversion, the sweep ordering
and repeat-irradiance rejection, the reference anchor with its
no-anchor refusal, the per-point deviation bands, the least-squares slope
and intercept, the offset screen against the reference current, the range
coverage gaps, the monotonicity findings and the device verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_working_standard_linearity.py against
scripts/e2008_working_standard_linearity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_working_standard_linearity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

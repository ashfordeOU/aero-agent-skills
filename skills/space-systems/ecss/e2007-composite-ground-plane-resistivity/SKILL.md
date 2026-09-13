---
name: e2007-composite-ground-plane-resistivity
description: "Use when verify that a composite mounting plane used under a unit on electromagnetic-compatibility test reproduces the surface-resistivity of the real installation, per ECSS-E-ST-20-07C clause 5.2.3.3: reduce a two-probe bar reading, a collinear four-point-probe reading or a volume-resistivity value over laminate thickness to ohms-per-square, categorize each panel as conductive, static-dissipative or insulating, require the test panel and the flight panel to share that band and to agree within a declared decade-deviation, check that fibre-direction anisotropy is reproduced, check the panel-to-facility bonding path, and raise a finding when the real installation was never characterized. Trigger: ecss, e-st-20-electrical-scope, composite-ground-plane, surface-resistivity, ohms-per-square, cfrp-mounting-panel, four-point-probe, decade-deviation, emc-test-setup."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-composite-ground-plane-resistivity, composite-ground-plane, surface-resistivity, ohms-per-square, cfrp-mounting-panel, four-point-probe, emc-test-setup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Composite Ground-Plane Resistivity (space-systems/ecss/e2007-composite-ground-plane-resistivity)

Use when the task is the composite test-plane requirement of
ECSS-E-ST-20-07C clause 5.2.3.3 -- showing that a composite plane a
unit is mounted on during an electromagnetic-compatibility test
reproduces the surface-resistivity of the composite structure the unit
actually flies on.

## Domain quick reference

- A metallic plane is controlled by an upper cap: lower resistance is
  always acceptable. A composite plane is controlled by a match: the
  test plane has to land near the flight value, because a plane made
  deliberately more conductive than the flight structure hides the
  very coupling the test exists to find, and one made less conductive
  overstates it. This is a two-sided requirement, not a cap.
- The controlled quantity is surface-resistivity in ohms per square.
  It can be reduced from a two-electrode bar reading (measured
  resistance scaled by the width-to-spacing ratio of the bar), from a
  collinear four-point probe on a sheet much wider than the probe span
  (the reading scaled by the thin-sheet geometry factor of about
  4.532), or from a volume-resistivity value divided by the laminate
  thickness. Each reduction is a different geometry, so the method
  used on each panel is itself recorded.
- Panels are categorized into three bands: conductive below 1e4 ohms
  per square, static-dissipative from there to 1e11, and insulating
  above that. A band difference between the test plane and the flight
  structure changes the physics of the return path, so it is a major
  finding on its own, independent of the numeric gap.
- Within one band, the house tolerance is a decade-deviation: the test
  plane has to sit within a factor of two of the flight value, written
  as the absolute difference of the two base-ten logarithms. Working
  in decades keeps the tolerance meaningful across the many orders of
  magnitude a composite laminate can span.
- A carbon-fibre laminate is anisotropic: resistivity along the fibre
  direction differs from resistivity across it, often by a large
  factor. The test laminate has to reproduce the flight ratio, not
  only the flight magnitude, so directional data on one panel and not
  the other is a gap in the evidence rather than a pass.
- A composite plane still needs a low-resistance bond to the facility
  reference; that path is checked here against a millohm cap, while
  the wider arrangement sits in clause 5.2.3.1 and the metallic-plane
  cap in clause 5.2.3.2.

## Workflow

1. Confirm the real installation carries a characterized
   surface-resistivity, from a recorded value or from a measurement
   record that can be reduced. An uncharacterized flight structure
   ends the assessment as a major finding -- there is nothing to
   reproduce and no pass is available.
2. Reduce each panel to ohms per square. Dispatch on the recorded
   method: two-probe bar, four-point probe or volume-resistivity over
   thickness. Reject an uncategorized method rather than assuming one,
   and reject a zero probe current, a zero electrode spacing or a zero
   laminate thickness.
3. Categorize each panel into its conduction band and require the two
   to agree. Record a band difference as a major finding.
4. Compute the decade-deviation between the test and flight values and
   compare it against the tolerance, tightening the tolerance when the
   programme has declared a narrower one.
5. When both panels carry directional data, compute the anisotropy
   ratio of each -- the more resistive fibre direction over the less
   resistive one -- and require the test ratio to track the flight
   ratio. Directional data on only one side is a minor finding.
6. Check the panel-to-facility bond resistance against the cap, and
   record a missing bond value as a minor finding rather than a pass.
7. Compare the measurement methods used on the two panels and note a
   deviation, then aggregate. The plane is compliant when no major
   finding stands and clean only when the minor list is empty too.

## Pitfalls

- Substituting an aluminium plane for a composite flight structure
  "because it is a better ground" -- a conductive substitute breaks
  the match the clause asks for and changes the measured coupling in
  both directions.
- Comparing a raw probe reading in ohms against a value in ohms per
  square -- the two differ by the geometry of the probe, and only the
  reduced value is comparable between panels.
- Comparing panels by percentage when they sit decades apart -- a
  laminate can span many orders of magnitude, so the gap is measured
  in decades, and a percentage reads as negligible exactly where the
  physics has changed.
- Matching the magnitude and ignoring the fibre-direction anisotropy
  -- a laminate with the right average resistivity and the wrong
  directional ratio presents a different return path along one axis.
- Treating an uncharacterized flight structure as a free pass -- with
  no flight value on record the comparison cannot be made at all, and
  that absence is the finding.
- Letting a boundary case fail on representation error -- a test panel
  at exactly twice the flight value evaluates a few units in the last
  place above the decade tolerance in binary, so the comparison
  absorbs that with a tolerance instead of the tolerance being widened.

## Behavior contract (gate 3)

The measurement-reduction, band-categorization, decade-deviation,
anisotropy, panel-bonding and method-comparison logic is exercised by
the gate 3 contract test:
scripts/test_e2007_composite_ground_plane_resistivity.py against
scripts/e2007_composite_ground_plane_resistivity_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_composite_ground_plane_resistivity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

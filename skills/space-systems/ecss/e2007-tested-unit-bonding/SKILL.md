---
name: e2007-tested-unit-bonding
description: "Use when verify that a tested unit is bonded to the test reference-plane only through the bonding provisions built into its own design, as ECSS-E-ST-20-07C clause 5.2.6.2 requires: categorize each bond path as design-provided or test-added, raise every test-added jumper as a setup non-conformance, compute the series strap-and-contact resistance of each design-provided path and the parallel effective bonding-resistance of the set, compare it with the declared bonding-resistance requirement, check each bond-strap length-to-width ratio against the low-inductance geometry rule, and reconcile the computed value with the bench reading. Trigger: ecss, e-st-20-electrical-scope, tested-unit-bonding, bonding-provisions, bonding-resistance, bond-strap-aspect-ratio, reference-plane-bonding, design-provided-bonding, test-added-jumper."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-tested-unit-bonding, bonding-provisions, bonding-resistance, bond-strap-aspect-ratio, reference-plane-bonding, design-provided-bonding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Test Setup — Tested-Unit Bonding (space-systems/ecss/e2007-tested-unit-bonding)

Use when the task is the ECSS-E-ST-20-07C clause 5.2.6.2 restriction that
a tested unit is bonded to the test reference plane only by the bonding
means already built into its own design -- categorizing every bond path
by provenance, excluding test-added paths from the number, computing the
effective bonding resistance of the design-provided set, and reconciling
it with the bench measurement.

## Domain quick reference

- The bond between a unit and the reference plane is part of what the
  measurement characterizes, not part of the instrumentation. A strap the
  laboratory adds for convenience lowers the impedance the flight
  configuration will actually have, so the measurement then describes a
  unit that will never fly.
- Every bond path is categorized by provenance before any arithmetic:
  design-provided (the unit design, its interface documentation, its
  qualified mounting interface) or test-added (a setup jumper, an
  auxiliary laboratory strap). A provenance outside that set is a record
  defect and is rejected rather than assumed benign.
- A test-added path is a non-conformance on its own, independent of what
  it measures. Its resistance is never folded into the result, because
  a parallel path can only lower the combined value and would make an
  out-of-family bond look compliant.
- The direct-current resistance of one path is the strap or foot
  resistance -- material resistivity times length divided by the
  cross-section -- in series with the contact resistance of every joint
  along it. Joints usually dominate a short, thick foot.
- Paths energized together carry current in parallel, so the unit's
  effective bonding resistance is the parallel combination of the
  design-provided paths only, and it is always lower than the lowest
  single path.
- Direct current is not the whole requirement. At radio frequency the
  strap inductance dominates, and that is controlled geometrically by
  holding the strap length-to-width ratio at or below a stated maximum
  (commonly five to one).
- The computed value is finally reconciled with the bench reading. A
  relative disagreement beyond a stated fraction means either the model
  or a joint is wrong; it is reported, not averaged.

## Workflow

1. Categorize every bond path by provenance as design-provided or
   test-added. Reject an unrecognized provenance, a path without a name,
   or duplicate path names before computing anything.
2. Raise each test-added path as a setup non-conformance naming the path,
   and remove it from the resistance calculation entirely.
3. For each design-provided path, compute the strap resistance from the
   material resistivity, length and cross-section, and add the series
   contact resistance of every joint.
4. Combine the design-provided path resistances in parallel to get the
   effective bonding resistance, and compare it with the declared
   bonding-resistance requirement.
5. Check each design-provided strap's length-to-width ratio against the
   low-inductance maximum; a compliant direct-current resistance on a
   long, thin strap is still a radio-frequency finding.
6. Reconcile the computed effective resistance with the bench reading
   against a stated relative tolerance, and flag a missing bench reading
   as a finding in its own right.
7. Aggregate: the bonding is as designed only when no test-added path
   exists, the effective resistance is within requirement, every strap
   geometry passes, and the bench reading agrees.

## Pitfalls

- Adding a jumper because the bond "looked high" and re-measuring. That
  changes the configuration the clause exists to preserve; the correct
  move is to record the finding and restore the design bonding means.
- Folding a test-added path into the parallel combination. Parallel paths
  can only lower the result, so including the jumper turns a
  non-conformance into an apparent pass.
- Computing strap resistance and stopping there. The joints are in series
  with it and typically dominate a short, thick mounting foot by an order
  of magnitude.
- Accepting a compliant direct-current resistance on a long, thin strap.
  The resistance requirement and the length-to-width geometry rule are
  independent, and the geometry rule is the one that governs at radio
  frequency.
- Treating a missing bench measurement as a pass because the computed
  number is comfortable. The computation uses declared materials and
  nominal joints; the reading is the only evidence of the joint actually
  made.
- Reporting only the combined figure. A single bad joint can hide inside
  a parallel set, so each path resistance stays on the record beside the
  combined value.
- Letting a series sum that lands a few units in the last place above the
  requirement read as an exceedance. The logic absorbs representation
  error with a named tolerance far below any milliohm value; the
  requirement itself is never widened.

## Behavior contract (gate 3)

The provenance categorization, strap and contact resistance, parallel
combination, strap-geometry, requirement-comparison and bench
reconciliation logic is exercised by the gate 3 contract test:
`scripts/test_e2007_tested_unit_bonding.py` against
`scripts/e2007_tested_unit_bonding_logic.py` (stdlib unittest, offline).
Run: python3 scripts/test_e2007_tested_unit_bonding.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

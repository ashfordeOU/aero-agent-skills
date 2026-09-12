---
name: composite-material-characterization
description: "Use when determine composite overwrap and liner material allowables for a pressure-vessel structure per ECSS-E-ST-32C clause 5.6: select the appropriate coupon test programme (fiber tensile and compression, in-plane shear, interlaminar shear strength, open-hole and bearing), verify specimen counts meet CMH-17 statistical basis requirements, compute A-basis or B-basis allowables from test data using the k-factor tolerance-limit method, apply environmental and process knockdown factors, and confirm that the assembled test matrix covers the required property set before deriving design allowables. Trigger: ecss, e-st-32-structures-scope, composite-overwrap, copv, material-allowables, cmh17, coupon-testing, basis-values, knockdown-factors."
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
  tags: [ecss, e-st-32-structures-scope, composite-overwrap, copv, material-allowables, cmh17, coupon-testing, basis-values, knockdown-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Composite Material Characterization (space-systems/ecss/composite-material-characterization)

Use when the task is deriving material allowables for composite overwrap
and liner materials in pressure-vessel applications per ECSS-E-ST-32C
clause 5.6 — selecting and executing a coupon test programme, computing
statistical basis values, applying knockdown factors, and confirming
that the property set is complete before allowables are committed to
the design database.

## Domain quick reference

- ECSS-E-ST-32C clause 5.6 covers the characterization of overwrap and
  liner materials via coupon tests. Allowables are the statistically
  derived property limits that bound stress margins; they are distinct
  from nominal test values and must account for population scatter.
- The CMH-17 (Composite Materials Handbook) k-factor method is the
  standard approach: a one-sided tolerance limit on a normal population
  produces an A-basis (99th-percentile lower bound, 95 % confidence)
  or B-basis (90th-percentile lower bound, 95 % confidence) value.
  A-basis applies to single-load-path elements; B-basis applies where
  the load can redistribute to a parallel path.
- Minimum specimen counts before a basis value is statistically valid:
  25 specimens for A-basis, 18 for B-basis (CMH-17 section 8.3).
  Fewer specimens means the k-factor cannot be determined with the
  required confidence level.
- A coupon allowable is not a design allowable until environmental
  and process knockdowns are applied: moisture/temperature
  (wet–hot typically governs), manufacturing variability (filament-
  winding tension, fiber volume fraction), and damage state
  (open-hole for fastened interfaces). Each knockdown is a
  multiplicative factor in (0, 1].
- Translation efficiency quantifies how well the manufacturing process
  converts dry-fiber strength into laminate strength. Values below 0.85
  indicate processing problems that must be resolved before allowables
  are accepted.

## Workflow

1. Inventory the composite system (fiber type, matrix type) and
   categorize each into the recognized families (high-modulus fiber,
   glass fiber, aramid fiber; thermoset, thermoplastic). Reject an
   unrecognized system before test planning proceeds.
2. Define the coupon test matrix. For a complete overwrap
   characterization the minimum required property set is:
   fiber-direction tensile, transverse tensile, fiber-direction
   compression, transverse compression, in-plane shear (±45° tensile
   method), and interlaminar shear strength. Document any additional
   tests (open-hole, bearing, filled-hole) as supplemental.
3. Before testing, verify that the planned specimen count meets the
   CMH-17 minimum for the target basis level: 25 for A-basis, 18 for
   B-basis. Flag a shortfall and do not proceed with coupon machining
   until the batch size is increased.
4. After testing, compute the basis value for each property using the
   k-factor tolerance-limit method on the sample mean and standard
   deviation. Confirm that the resulting basis value is below the
   sample mean (a basis value above the mean indicates data entry or
   sign errors).
5. Apply all applicable knockdown factors to the statistical allowable.
   Record each factor, its physical basis, and its source reference;
   the product of all factors times the statistical allowable is the
   design allowable entered into the structural model.
6. Compute the margin of safety for each critical load case:
   MoS = (design allowable / applied stress) − 1. A negative margin is
   a finding and must be resolved before the design is baselined.
7. Check test matrix completeness: confirm all required property types
   were tested before releasing allowables to the design database.
   A missing test type is a finding even if all tested properties have
   positive margins.
8. Confirm translation efficiency from dry-fiber reference to laminate
   is at or above 0.85. A low efficiency finding requires root-cause
   investigation of the winding or curing process before allowables
   are used.

## Pitfalls

- Using a specimen count below the CMH-17 minimum and reporting the
  result as a valid basis value — the k-factor is only tabulated and
  statistically valid above the minimum count; below it the tolerance
  interval is undefined.
- Entering the basis value directly into the structural model without
  applying knockdowns — the coupon test environment (ambient
  temperature, dry conditioning) is not the design environment;
  wet-hot conditions routinely govern and can reduce allowables by
  10–25 %.
- Accepting a positive margin as confirmation that the test matrix is
  complete — a missing property type (e.g., interlaminar shear
  strength) is a programme risk regardless of margins on the tests
  that were performed.
- Treating A-basis and B-basis as interchangeable — A-basis is required
  for single-load-path elements and is substantially more conservative;
  using B-basis on a single-path element is non-compliant.
- Ignoring translation efficiency — a low efficiency indicates a
  process defect whose effect may not be captured in the coupon data
  if the coupons were made under controlled lab conditions rather than
  representative production conditions.

## Behavior contract (gate 3)

The coupon test validation, specimen count check, basis value
computation, knockdown application, margin calculation, material
categorization, test matrix completeness, and translation efficiency
logic is exercised by the gate 3 contract test:
scripts/test_composite_material_characterization.py against
scripts/composite_material_characterization_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_composite_material_characterization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- CMH-17 (Composite Materials Handbook, 17th volume series) is a US
  DoD reference freely available through the CMH-17 Coordination Group.
- compliance: STANDARDS-REF, gated: false.

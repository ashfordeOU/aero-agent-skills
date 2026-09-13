---
name: e2001-analysis-level-two-requirements
description: "Use when determine which radio-frequency equipment items escalate to the second multipactor-analysis-level of ECSS-E-ST-20-01C clause 5.3.2.3.1 instead of staying with the first-level susceptibility-chart lookup: categorize each item against its equipment-type profile, form the frequency-gap-product of its narrowest multipactor-gap and check the validated chart-band, evaluate the peak-to-mean field-uniformity-ratio, and read the first-level margin-outcome. Any driver - geometry no parallel-plate-chart represents, an out-of-band frequency-gap-product, field-non-uniformity above the uniformity-limit, a first-level margin-shortfall - escalates the item, while a dielectric-exposed equipment-type routes instead to a seeded multipactor-test because the tracked-electron model carries no surface-charging path. Trigger: ecss, e-st-20-electrical-scope, second-analysis-level, multipactor-analysis-level, frequency-gap-product, equipment-type-eligibility, parallel-plate-chart-band, field-uniformity-ratio."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-analysis-level-two-requirements, second-analysis-level, multipactor-analysis-level, frequency-gap-product, equipment-type-eligibility, field-uniformity-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Second-Analysis-Level Applicability (space-systems/ecss/e2001-analysis-level-two-requirements)

Use when the task is deciding, per radio-frequency equipment item, whether
the detailed second multipactor-analysis-level of ECSS-E-ST-20-01C clause
5.3.2.3.1 applies — which equipment-types are eligible for it, what
escalates an item off the first level, and what the second level needs on
record before it can start.

## Domain quick reference

- The standard offers two multipactor-analysis-levels. The first level maps
  the susceptible geometry onto an equivalent parallel-plate gap, forms the
  frequency-gap-product, and reads a breakdown-voltage off a validated
  susceptibility-chart. It is fast and deliberately conservative, but it is
  only meaningful where the real field distribution behaves like a uniform
  parallel-plate field and where the frequency-gap-product sits inside the
  chart's validated band.
- The second level replaces that lookup with a three-dimensional
  electromagnetic field model plus electron-trajectory tracking against
  measured secondary-emission data. It is more expensive and it is the route
  the standard reserves for geometries and operating points where the first
  level either cannot be applied or returns a shortfall that the designer
  believes is an artefact of its conservatism.
- Eligibility is a property of the equipment-type, not of the margin alone.
  A metal-walled guided-wave, planar, radiative or interface item is
  representable by the tracked-electron model of the second level. An item
  whose dielectric is exposed to the radio-frequency field is not: the
  dielectric accumulates surface charge, which the metal-wall tracking model
  does not carry, so such an item is escalated to a seeded multipactor-test
  rather than to the second level.
- The second level cannot start on geometry alone. It needs a
  secondary-emission dataset for the electrode material in its flight surface
  condition, an identified three-dimensional field model, and a validation
  reference for the electron-tracking solver. A missing one of those is a
  finding in its own right, not a silent assumption.

## Workflow

1. Categorize every multipactor-critical item by equipment-type and pull its
   profile: whether a parallel-plate-chart represents it, and whether the
   tracked-electron model of the second level is admissible for it. Reject an
   unrecognized equipment-type before it enters the assessment.
2. Form the frequency-gap-product from the operating frequency and the
   narrowest susceptible gap, and check it against the validated chart-band.
   Outside the band the first-level reading carries no credible value.
3. Compute the peak-to-mean field-uniformity-ratio across that gap from the
   field model. Above the uniformity-limit the single-equivalent-gap premise
   of the first level no longer holds.
4. Where the first level is applicable, read its margin-outcome against the
   required value. Treat an absent margin record as a driver, not as a pass.
5. Collect the drivers. No driver means the first level is sufficient. One or
   more drivers escalate the item: to the second level where the
   equipment-type admits the tracked-electron model, and to a seeded
   multipactor-test where it does not.
6. For every item escalated to the second level, confirm the three
   prerequisites are on record; raise a finding for each missing one and
   report the item as not yet ready.
7. Aggregate per item and roll up counts by route; the inventory is not clean
   until no item carries an open finding.

## Pitfalls

- Reading a first-level chart value for a geometry the chart does not
  represent, and treating the number as conservative. A chart lookup outside
  its premises is not conservative, it is undefined.
- Escalating on margin-shortfall alone and never checking the
  frequency-gap-product against the validated band — an out-of-band item can
  show a comfortable first-level margin that means nothing.
- Sending a dielectric-exposed item to the second level because it is "more
  detailed". The tracked-electron model has no surface-charging path, so the
  detailed run is silently optimistic; that item belongs on hardware.
- Declaring an item ready for the second level while its secondary-emission
  dataset, field model or solver-validation reference is unset. An unset
  prerequisite is an open finding, not a default.
- Comparing a decibel margin against its requirement with a bare inequality.
  A margin formed as a difference of logarithms can land a unit in the last
  place below an exactly compliant value; absorb the representation error in
  the comparison, never by relaxing the required value.

## Behavior contract (gate 3)

The equipment-type categorization, chart-band check, field-uniformity-ratio,
escalation routing and prerequisite logic are exercised by the gate 3
contract test: scripts/test_e2001_analysis_level_two_requirements.py against
scripts/e2001_analysis_level_two_requirements_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_analysis_level_two_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e20-corona-design-and-verification
description: "Use when design radio-frequency chain hardware against corona onset and verify it with the margin-allowance the evidence in hand actually earns, under ECSS-E-ST-20C clause 7.3.3.2: convert an onset voltage into a corona-onset-power, raise the applied peak voltage for the standing-wave mismatch the item presents, state the headroom between them as a corona-margin, categorize the route as flight-standard-test, representative-model-test, numerical-analysis or heritage-similarity, apply the allowance that route earns, and reject a relaxed allowance with no agreement on record, a null result taken without a seed-electron-source, and a pressure sweep that never crossed the critical band. Trigger: ecss, e-st-20-electrical-scope, corona-design-and-verification, corona-onset-voltage, corona-margin-allowance, seed-electron-source, discharge-detection-method, verification-route-category, critical-pressure-sweep."
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
  tags: [ecss, e-st-20-electrical-scope, e20-corona-design-and-verification, corona-onset-voltage, corona-margin-allowance, seed-electron-source, discharge-detection-method, verification-route-category, critical-pressure-sweep]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Corona Design and Verification (space-systems/ecss/e20-corona-design-and-verification)

Use when the task is the clause 7.3.3.2 design-and-verification duty of
ECSS-E-ST-20C -- setting the headroom a radio-frequency chain item has
to hold below corona onset, choosing the evidence that will close it,
and deciding whether the evidence actually earns the allowance being
claimed.

## Domain quick reference

- The design side works in voltage. The applied quantity is the peak
  voltage the standing wave presents across the critical gap: the
  matched peak of the applied power across the item's equivalent
  impedance, multiplied by one plus the reflection coefficient of the
  mismatch the item really presents. A well-matched item and a poorly
  matched one at the same power stress the gap differently.
- Onset is stated as a voltage and converted to power through the same
  equivalent impedance, so the headroom is identical whether it is
  written as twenty times the logarithm of the voltage ratio or ten
  times the logarithm of the power ratio. Mixing the two coefficients
  is the most common arithmetic error in this clause.
- The allowance is not a single number. It is a function of the
  evidence: a measurement on flight-standard hardware earns the
  smallest headroom, a measurement on a representative model rather
  more, a numerical prediction more again, and an argument from
  heritage the most. The ordering is the point -- weaker evidence buys
  a larger allowance, never a smaller one.
- An allowance below the route default is a relaxation. It is usable
  only with the agreement that granted it recorded against the item;
  without that record the relaxation is a finding regardless of how
  comfortable the measured headroom looks.
- A measurement route carries three preconditions. A seed-electron
  source has to be present, because an unseeded gap can sit above its
  onset voltage for a long time without striking and the null result
  then proves nothing. A recognized detection method has to be on
  record, since a discharge is inferred rather than seen. And the
  pressure sweep has to cross the whole critical band, because that is
  where onset is lowest.
- Design targets fall out of the same relation: given the applied
  power, the equivalent impedance, the mismatch and the allowance, the
  onset voltage the geometry must reach is fixed, and that number is
  what the gap, the corner radius and the surface treatment are chosen
  against.

## Workflow

1. Categorize the declared verification route into one of the four
   evidence categories, resolving the common aliases, and reject an
   unrecognized route before anything else is computed.
2. Settle the allowance in force: the route default unless an agreed
   value is on record. Treat an agreed value below the default as a
   relaxation and require the agreement reference with it.
3. Compute the applied peak voltage from the applied power, the
   equivalent impedance and the declared mismatch; reject a
   non-positive power or impedance and a mismatch below unity.
4. Compute the corona margin as twenty times the base-ten logarithm of
   the onset-to-applied voltage ratio, and compare it against the
   allowance, absorbing representation error at an exact equality
   rather than widening the allowance.
5. Derive the onset voltage the design has to reach for that allowance
   and report it next to the one claimed, so a shortfall states how
   much geometry has to change.
6. For a measurement route, confirm the seed-electron source, the
   detection method and a pressure sweep that covers the whole
   critical band; report each uncovered sub-band.
7. Roll the items up into a chain verdict: the driving item is the one
   with the least headroom, and the chain is compliant only when no
   item carries a finding.

## Pitfalls

- Using ten times the logarithm on a voltage ratio. That halves the
  stated headroom and turns a compliant item into a finding, or the
  reverse when the error runs the other way.
- Computing the applied voltage as if the item were matched. The
  standing wave raises the peak by one plus the reflection
  coefficient, which at a three-to-one mismatch is half again.
- Claiming the small flight-standard allowance on the strength of a
  measurement taken on an engineering model. The model earns the
  representative-model allowance, and the difference is real hardware
  margin.
- Accepting an unseeded null result. Without a seed-electron source
  the gap may simply never have been given a starting electron, and
  the run says nothing about onset.
- Sweeping pressure only where the chamber is comfortable. A sweep
  that stops short of the low-onset band has not exercised the
  condition the clause is about.
- Relaxing the allowance in a review and never writing the agreement
  down. The number in the budget then has no authority behind it, and
  the next reviewer cannot tell a granted relaxation from an error.

## Behavior contract (gate 3)

The route categorization, allowance-resolution, applied-voltage,
onset-power, margin, design-target, seed-electron, detection-method
and critical-band-coverage logic is exercised by the gate 3 contract
test: scripts/test_e20_corona_design_and_verification.py against
scripts/e20_corona_design_and_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_corona_design_and_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

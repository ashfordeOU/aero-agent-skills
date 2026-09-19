---
name: q7053-specimen-selection
description: "Define the representative specimen set a sterilization compatibility campaign is run on, so the tested coupons stand for the flight hardware rather than for whatever was on the shelf. Use when a bill of materials and a pool of candidate coupons and hardware specimens must be reduced to a defensible test set carrying replicates and unexposed controls. Covers every material family, picks the least-margin specimen per family against the dominant stressor of the process, sets aside a coupon whose thickness sits outside the flight range, and reports a family left uncovered, short of replicates or without a control. Trigger: ecss, q-st-70-53, sterilization-specimen-selection, material-family-coverage, unexposed-control-specimen, specimen-replicate-count, coupon-thickness-representativeness, worst-case-specimen."
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
  tags: [ecss, q-st-70-53-sterilization-compatibility-scope, q7053-specimen-selection, sterilization-specimen-selection, material-family-coverage, unexposed-control-specimen, specimen-replicate-count, coupon-thickness-representativeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Sterilization Compatibility — Test Item Selection (space-systems/ecss/q7053-specimen-selection)

Use when the task is the test-item step of a sterilization compatibility
campaign: turning a bill of materials and a pool of available coupons
into the specimen set the exposure is actually run on, and saying what
that set does not cover.

## Domain quick reference

- A compatibility result belongs to the specimen, not to the material
  name printed on it. The set is defensible only when every material
  family in the item is represented, and a family with no specimen is
  a family with no evidence however many coupons the campaign ran.
- Inside a family the specimen that matters is the one with the least
  margin against the dominant stressor of the process. Testing the
  most capable grade of a family and reporting the family as
  compatible is a selection error that no amount of replication
  repairs.
- An exposed specimen without an unexposed control measures nothing.
  Property change is the observable, so the control is what the
  post-exposure measurement is differenced against, and it is drawn
  from the same lot as the exposed specimens rather than from stock.
- Replicates separate the material from its preparation. A single
  exposed coupon per family cannot tell a material effect from a
  surface, cure or handling effect, and the minimum replicate count is
  a property of the campaign rather than of how many coupons arrived.
- Geometry carries the result. A coupon far thinner than the flight
  part reaches the process temperature faster and takes a higher dose
  per unit volume; one far thicker never sees the full exposure
  through its section. A specimen outside the flight thickness range
  is set aside rather than quietly counted toward coverage.

## Workflow

1. Validate the flight thickness range and each candidate specimen:
   identifier, family, positive thickness, declared capability against
   the dominant stressor, and whether it is an unexposed control. A
   duplicate identifier or a non-positive thickness is an input error.
2. Group the pool by material family, keeping controls separate from
   the specimens that will be exposed.
3. Set aside every specimen whose thickness lies outside the flight
   range, absorbing an equality at either end with the named tolerance,
   and record it as not representative rather than discarding it
   silently.
4. For each family required by the bill of materials, select the
   worst-case exposed specimen: least capability against the dominant
   stressor, ties broken on the identifier so the selection is
   reproducible.
5. Fill the family up to the minimum replicate count from the
   remaining representative exposed specimens, taking the least
   capable first.
6. Attach one representative control per family and raise a finding
   when none exists.
7. Report the selected set per family, the set-aside specimens, and a
   finding for every family left uncovered, short of replicates,
   without a control, or whose worst-case specimen sits at or below
   the applied stressor.

## Pitfalls

- Counting a set-aside coupon toward coverage. A specimen outside the
  flight thickness range is not a weak data point, it is a data point
  about a different heat and diffusion path.
- Selecting the most convenient grade in a family. The campaign exists
  to find the limiting material, so the selection rule is least
  margin, not best availability.
- Taking the control from a different lot. A control exists to
  difference out everything except the exposure, and a different lot
  puts the lot variation straight into the reported property change.
- Treating replicate count as a target to be met by splitting one
  coupon. Two halves of the same coupon share their preparation and do
  not separate a material effect from a handling effect.
- Passing over a family because no coupon was delivered. An uncovered
  family is a finding against the campaign, and silence in the report
  reads as coverage nobody has.

## Behavior contract (gate 3)

The specimen validation, family grouping, thickness representativeness
rule, worst-case selection, replicate filling, control attachment and
coverage findings are exercised by the gate 3 contract test:
scripts/test_q7053_specimen_selection.py against
scripts/q7053_specimen_selection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7053_specimen_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q7002-tml-measurement
description: "Determine the total mass loss of specimens taken through an outgassing screening. Use when the three weighings of a run under ECSS-Q-ST-70-02C have to become a screening result: refer the loss to the initial mass so light and heavy coupons are comparable, refuse a specimen heavier after the exposure as a weighing error, subtract the water taken back on to leave the recovered mass loss, report a loss smaller than the balance division as unresolvable rather than small, and grade the replicate spread against its scatter allowance. Trigger: ecss, q-st-70-02c, outgassing-total-mass-loss, outgassing-recovered-mass-loss, outgassing-water-vapour-regained, outgassing-balance-resolution-floor, outgassing-replicate-scatter, outgassing-screening-limit."
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
  tags: [ecss, q-st-70-02-outgassing-scope, q7002-tml-measurement, outgassing-total-mass-loss, outgassing-recovered-mass-loss, outgassing-water-vapour-regained, outgassing-balance-resolution-floor, outgassing-replicate-scatter]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening -- Total Mass Loss (space-systems/ecss/q7002-tml-measurement)

Use when the task is the mass-loss measurement of a thermal-vacuum outgassing
screening under ECSS-Q-ST-70-02C: the specimens have been weighed before the
exposure, after it, and again after reconditioning in laboratory air, and the
question is what the screening result is and whether the replicate set
supports it.

## Domain quick reference

- Total mass loss is a ratio, not an amount. The same two milligrams lost from
  a hundred-milligram coupon and from a three-hundred-milligram coupon are
  different results, which is why the per-specimen mass window exists at all.
- A specimen heavier after the exposure is not a negative loss. It is a
  weighing, handling or condensation error, and reporting it as a small
  positive number by taking the magnitude hides the mistake.
- The mass a coupon takes back on in laboratory air was water, not material.
  Subtracting it on the same initial-mass basis leaves the loss that describes
  the material, which is the figure a screening decision rests on.
- A loss below what the balance division can distinguish is not a low result.
  It is a result the run cannot report, and the honest outcome is to say the
  measurement was not resolvable rather than to record a very small number.
- The replicate set has to agree with itself. A spread beyond the scatter
  allowance points at the specimens or the run, and a mean taken across such a
  set reports neither of the two populations inside it.

## Workflow

1. Validate the three masses as positive finite quantities and refuse a final
   mass above the initial one, a recovery below the final mass, or a recovery
   above the initial mass.
2. Form total mass loss as the difference between the initial and final masses
   referred to the initial mass, in percent.
3. Where a reconditioning weighing exists, form the regained water on the same
   initial-mass basis and subtract it to give the recovered mass loss.
4. Where the balance division is declared, turn it into the smallest
   distinguishable percentage for that coupon and report a result below it as
   unresolvable.
5. Grade each result against its screening limit, absorbing an exact equality
   at the limit as representation error rather than by moving the limit.
6. Report the set mean, spread, minimum and maximum, raise a finding when the
   spread exceeds the scatter allowance, and pass the material only when no
   coupon and no set-level check raised anything.

## Pitfalls

- Reporting an absolute loss in milligrams. It is not comparable between
  coupons and cannot be graded against a percentage limit.
- Taking the magnitude of a negative loss. The sign was the evidence, and
  removing it turns a bench error into a quietly plausible result.
- Subtracting the regained water on the final mass instead of the initial one.
  The two denominators differ by the loss itself, so the correction lands
  slightly wrong and always in the same direction.
- Recording a result finer than the balance can see. The number will be quoted
  later as though it were measured.
- Averaging a scattered set. Two populations with a wide spread produce a mean
  belonging to neither, and the spread is the finding.

## Behavior contract (gate 3)

The mass validation, total mass loss, regained water, recovered mass loss,
balance resolution floor, screening-limit comparison and the replicate set
statistics are exercised by the gate 3 contract test:
scripts/test_q7002_tml_measurement.py against
scripts/q7002_tml_measurement_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7002_tml_measurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

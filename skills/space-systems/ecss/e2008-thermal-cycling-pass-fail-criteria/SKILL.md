---
name: e2008-thermal-cycling-pass-fail-criteria
description: "Use when accepting or rejecting a cycled solar-array coupon. Verify that a thermally cycled photovoltaic-assembly coupon meets its acceptance criteria under ECSS-E-ST-20-08C clause 5.5.1.3.5: bring the pre-cycling and post-cycling output-power readings to the same reference irradiance and cell temperature before comparing them, form the retention ratio against the declared threshold, compute the series-resistance drift of the string, treat a non-conducting string as an open circuit rather than a large drift, count the discontinuity events the in-situ monitor caught during the run, and name every criterion the coupon failed in one acceptance verdict. Trigger: ecss, e-st-20-08c, clause-5-5-1-3-5, photovoltaic-coupon-acceptance-criteria, solar-array-string-continuity, interconnect-resistance-drift, coupon-power-retention, post-cycling-power-measurement, discontinuity-event-count."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-thermal-cycling-pass-fail-criteria, photovoltaic-coupon-acceptance-criteria, solar-array-string-continuity, interconnect-resistance-drift, coupon-power-retention, post-cycling-power-measurement, discontinuity-event-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Thermal-cycling Pass/Fail Criteria (space-systems/ecss/e2008-thermal-cycling-pass-fail-criteria)

Use when the task is the acceptance decision at the end of the
thermal-cycling test of ECSS-E-ST-20-08C clause 5.5.1.3.5 -- deciding
whether a photovoltaic-assembly coupon that has come out of the chamber
still conducts as it did and still delivers the power it did.

## Domain quick reference

- The campaign closes on two independent questions. Electrical
  continuity asks whether the string stayed whole; power retention asks
  whether it still produces. A coupon can pass either one and fail the
  other, so they are decided separately and reported separately.
- Continuity degrades in three distinguishable ways. A cracked
  interconnect can leave the string open, can leave it conducting
  through a higher series resistance, or can leave it intact at rest
  while dropping out momentarily under the thermal excursion. The third
  is only visible to a monitor watching during the run, which is why
  the event count is part of the criteria and not an afterthought.
- An open string is its own verdict. Reporting it as a very large
  resistance drift invites someone to compare it with a percentage
  allowance; it is a different failure and carries a different repair.
- Two output-power readings are comparable only after both are brought
  to the same reference irradiance and the same cell temperature. A
  cell delivers less power when it is hot and less when the lamp is
  weak, and neither of those is a cycling effect.
- The temperature correction runs through the power temperature
  coefficient of the cell. A reading taken twenty kelvin warm can look
  like a five percent loss and be no loss at all, so the correction
  decides the verdict as much as the measurement does.
- The retention threshold is a declared criteria-set value from the
  source control drawing, not a physical constant. It is applied as a
  ratio of corrected powers so the decision is reproducible, and a
  coupon that lands exactly on it is accepted: the tolerance absorbs
  representation error, the threshold itself never moves.

## Workflow

1. Validate the criteria set before reading any measurement: a drift
   allowance that permits the resistance to double, a negative event
   allowance or a retention threshold above unity is a criteria error
   and is refused rather than applied.
2. Correct the pre-cycling output-power reading to the reference
   irradiance and reference temperature, using the declared power
   temperature coefficient of the cell.
3. Correct the post-cycling reading through the same step, then form
   the retention ratio as corrected-after over corrected-before.
4. Decide continuity. When the post-cycling reading shows no conduction
   at all, record an open circuit and do not compute a drift; otherwise
   form the drift ratio from the pre and post series resistance and
   compare it with the allowance.
5. Add the discontinuity events the in-situ monitor recorded during the
   run and compare the count with the allowance, which is normally
   zero: a dropout under thermal load is a defect whether or not the
   string reads whole afterwards.
6. Group every failed criterion into one verdict, naming each one with
   its measured value and its limit, so the review sees what the coupon
   failed on rather than only that it failed.

## Pitfalls

- Comparing raw watts before and after. Ambient drift in the lamp or in
  the coupon temperature between the two measurement sessions is
  routinely larger than the retention allowance, so an uncorrected
  comparison rejects sound coupons and accepts degraded ones.
- Correcting only one of the two readings. The correction has to be
  applied to both or the ratio inherits the whole of the uncorrected
  offset.
- Folding an open circuit into the drift number. A percentage allowance
  cannot express an open string, and a pipeline that represents it as a
  large float will eventually compare it with a threshold and pass it.
- Ignoring the monitor trace because the post-test resistance is fine.
  An intermittent dropout under thermal load is the early stage of the
  crack that opens on orbit; the resting resistance is measured at one
  temperature and hides it.
- Relaxing the retention threshold for a coupon that lands on it. The
  equality is a representation question that the comparison tolerance
  handles; the declared threshold stays as the drawing specifies.

## Behavior contract (gate 3)

The criteria validation, reference correction, resistance-drift
computation, open-circuit handling, discontinuity counting, power
retention decision and combined acceptance verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_thermal_cycling_pass_fail_criteria.py against
scripts/e2008_thermal_cycling_pass_fail_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_thermal_cycling_pass_fail_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

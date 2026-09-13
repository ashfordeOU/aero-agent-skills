---
name: e2008-thermal-cycling-test-execution
description: "Execute the thermal-cycling qualification of a photovoltaic-assembly coupon under ECSS-E-ST-20-08C clause 5.5.1.3.4: derive the cycle count from the eclipse rate of the mission orbit regime, the mission duration and the qualification factor against a policy floor, widen the predicted on-orbit extremes by the temperature margin and refuse a profile the coupon materials are not declared to survive, size the ramp and the stabilisation dwells into a cycle period and a campaign duration, then grade every recorded cycle on whether both extremes were actually reached and both dwells actually held, counting only conforming cycles toward the requirement. Use when planning or auditing a solar-array coupon cycling run. Trigger: ecss, e-st-20-08c, clause-5-5-1-3-4, photovoltaic-assembly-thermal-cycling, solar-array-coupon-cycle-count, eclipse-cycle-derivation, qualification-temperature-extremes, cycling-profile-execution, coupon-dwell-verification."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-thermal-cycling-test-execution, photovoltaic-assembly-thermal-cycling, solar-array-coupon-cycle-count, eclipse-cycle-derivation, qualification-temperature-extremes, cycling-profile-execution, coupon-dwell-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Thermal-cycling Test Execution (space-systems/ecss/e2008-thermal-cycling-test-execution)

Use when the task is the execution step of the thermal-cycling test of
ECSS-E-ST-20-08C clause 5.5.1.3.4 -- choosing how many cycles a
photovoltaic-assembly coupon is run through and between which two
temperatures, building the profile that joins them, and grading the run
that comes back from the chamber.

## Domain quick reference

- The cycle count is a mission number, not a chamber number. An array
  sees one deep temperature excursion per eclipse, so the count follows
  the eclipse rate of the orbit regime multiplied by the mission
  duration and by a qualification factor. A low orbit produces
  thousands of eclipses a year; a geostationary orbit produces two
  eclipse seasons and of order ninety. The same mission length
  therefore buys wildly different campaigns.
- A policy floor still applies. A short or high-orbit mission can
  derive a handful of cycles, which demonstrates nothing about the
  fatigue of an interconnect or a bondline, so the derived count is
  floored at a minimum the project declares.
- The temperature extremes are the predicted on-orbit extremes widened
  by a qualification margin on both ends. The widened extremes are then
  checked against what the coupon materials are declared to survive.
  When the margin pushes an extreme past a declared material limit the
  correct answer is to refuse the profile: the prediction or the coupon
  build has to change, never the margin.
- Dwell exists so the whole coupon stabilises, not just the face the
  thermocouple sits on. A dwell shorter than the stabilisation time
  cycles the surface while the bondline underneath never sees the
  extreme, which is the failure mode the test was bought to find.
- Ramp rate is bounded from above by the chamber and by the coupon.
  Together with the range it fixes the cycle period, and the period
  times the count fixes how long the chamber is occupied, which is the
  number the programme schedule actually cares about.
- A cycle counts only when the record shows it met the profile. A run
  logged as complete on chamber hours, with a tenth of its cycles
  never reaching the cold extreme, has delivered nine tenths of the
  campaign.

## Workflow

1. Validate the mission inputs: orbit regime, mission duration, the
   predicted temperature extremes and the declared coupon material
   limits. An uncategorized orbit regime or a non-positive duration is
   an input error, not a case to be defaulted.
2. Derive the required cycle count from the eclipse rate, the duration
   and the qualification factor, then floor it at the policy minimum.
   Absorb the representation error of the product before rounding up so
   an exact whole number of cycles does not silently gain one.
3. Widen the predicted extremes by the temperature margin and compare
   both against the declared coupon limits. Refuse an extreme that lies
   outside a limit; record a finding when an extreme lands exactly on
   one, because that coupon has no margin left for a chamber overshoot.
4. Size the profile: check the ramp rate against the policy ceiling and
   both dwells against the stabilisation floor, then form the cycle
   period from two ramps and two dwells and the campaign duration from
   the period and the required count.
5. Grade the run. For each recorded cycle check that the cold extreme
   was reached within the stabilisation tolerance, that the hot extreme
   was reached within it, and that both dwells were held; a cycle
   missing any of these is grouped with the non-conforming ones and
   does not count.
6. Close with the verdict: the campaign is complete only when the
   conforming cycle count reaches the requirement. Report the shortfall,
   the non-conforming cycles and their reasons, and leave the verdict
   explicitly undetermined when no records exist yet.

## Pitfalls

- Counting chamber cycles instead of conforming cycles. The chamber log
  says how many times the controller ran the profile; only the recorded
  extremes and dwells say how many times the coupon experienced it.
- Deriving the count from mission years alone. Eclipse rate is the
  driver, so a five-year low-orbit mission and a five-year
  geostationary mission differ by nearly two orders of magnitude in
  cycles and cannot share a campaign.
- Trimming the qualification margin to fit the coupon's material
  limits. That converts a hardware problem into a paper one: the
  margin is what makes the test bound the flight environment, and a
  coupon that cannot take it is the finding.
- Shortening the dwell to save chamber time. The saving is real and the
  test is then blind to exactly the slow bondline and interconnect
  fatigue it was meant to expose.
- Rounding the derived count up from a product that was already a whole
  number. The multiplication can land one unit in the last place high,
  and a gate that rounds without absorbing that adds a cycle on one
  machine and not on another.

## Behavior contract (gate 3)

The policy validation, cycle-count derivation, extreme selection and
refusal, profile sizing, recorded-cycle grading and campaign verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_thermal_cycling_test_execution.py against
scripts/e2008_thermal_cycling_test_execution_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_thermal_cycling_test_execution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2008-humidity-test-pass-fail-criteria
description: "Verify that a photovoltaic coupon still respects its continuity and output-power limits once humidity exposure has ended, per ECSS-E-ST-20-08C clause 5.5.1.4.5. Use when a post-exposure measurement set must be judged against its pre-exposure baseline: confirm the coupon stabilized for the required recovery period before measurement, correct both illuminated readings back to reference irradiance and cell-temperature so the comparison is between coupon states, not measurement conditions, derive the output-power loss fraction and retention ratio, screen every interconnect circuit for an open circuit and for series-resistance increase past its allowance, then aggregate recovery, power and continuity into one verdict. Trigger: ecss, e-st-20-08c, humidity-exposure-pass-criteria, photovoltaic-coupon-continuity, coupon-output-power-retention, interconnect-series-resistance-increase, irradiance-and-temperature-correction, post-exposure-recovery-period, solar-array-coupon-acceptance."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-humidity-test-pass-fail-criteria, e-st-20-08c, photovoltaic-coupon-humidity-exposure, coupon-output-power-retention, interconnect-continuity-screening, series-resistance-increase-allowance, irradiance-and-temperature-correction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Humidity-Exposure Pass Criteria (space-systems/ecss/e2008-humidity-test-pass-fail-criteria)

Use when the task is the clause 5.5.1.4.5 acceptance decision of
ECSS-E-ST-20-08C: a photovoltaic coupon has come out of its humidity
exposure, and it is admissible only if every interconnect circuit still
conducts and the output power it delivers has not fallen past the
permitted fraction of its pre-exposure value.

## Domain quick reference

- The verdict rests on two conditions, and both are pre-versus-post
  comparisons of the same coupon. Continuity: every interconnect circuit
  still conducts, and its series resistance has not grown past the
  allowance. Output power: the illuminated power delivered after the
  exposure retains the required fraction of the power delivered before
  it. Neither condition can be read off a single post-exposure number.
- Raw illuminated readings are not comparable. Output power moves with
  irradiance almost proportionally and with cell temperature through the
  power temperature coefficient, so a pre-exposure reading taken at one
  set of conditions and a post-exposure reading taken at another differ
  even on an undamaged coupon. Both readings are reported back to
  reference irradiance and reference cell-temperature first, and the loss
  fraction is formed from the two corrected values.
- Moisture leaving the coupon takes time. A reading taken before the
  prescribed stabilization period has elapsed measures the residual
  moisture as much as the coupon, so an unrecorded or short recovery
  period is a finding against the measurement, independent of whatever
  the numbers then say.
- An open circuit and a resistance increase are different findings with
  the same root: a degraded interconnect or cell-to-cell joint. An open
  circuit has no meaningful increase fraction to report, so it is carried
  as its own outcome rather than as an infinite ratio; a circuit that
  still conducts but has grown past its allowance is a finding in its own
  right and not a partial pass.
- A power reading that comes back higher than the pre-exposure value is a
  negative loss. That is admissible against the limit — the condition is
  one-sided — but it is reported as what it is rather than clamped to
  zero, because a large apparent gain usually points at a measurement or
  correction error worth chasing.

## Workflow

1. Check the stabilization period: compare the recovery hours actually
   observed before the post-exposure measurement against the required
   period. An unrecorded period is a finding, and so is a short one; an
   exact equality is compliant.
2. Correct the pre-exposure and the post-exposure illuminated readings to
   reference irradiance and reference cell-temperature, using the
   coupon's own measured temperature coefficient when it carries one.
   Refuse a correction whose temperature factor is not positive rather
   than returning a sign-inverted power.
3. Form the output-power loss fraction and the retention ratio from the
   two corrected powers, and compare the loss with its permitted value,
   absorbing representation error at the boundary with a named tolerance
   instead of relaxing the limit.
4. Screen every interconnect circuit. A missing or infinite post-exposure
   reading is an open circuit; otherwise form the series-resistance
   increase fraction and compare it with the allowance. Reject a
   duplicate circuit identifier, a missing key or a non-positive
   resistance as an input error.
5. Aggregate the recovery, power and continuity findings into one list.
   The coupon is accepted only when that list is empty; report the open
   circuit count alongside it so the severity is visible at a glance.

## Pitfalls

- Comparing raw watts across the exposure. Irradiance and cell
  temperature differences between the two measurement sessions can
  manufacture a loss on an undamaged coupon, or mask a real one; the
  correction to reference conditions is what makes the comparison mean
  anything.
- Measuring the coupon as soon as the chamber opens. Residual surface
  moisture shifts both the resistance readings and the illuminated
  power, so the stabilization period is part of the criterion and not
  laboratory housekeeping.
- Treating a conducting circuit as a passed circuit. Continuity is not
  binary here: a joint that survived as a high-resistance path has lost
  margin, and the increase allowance is what catches it before flight.
- Recording an open circuit as an enormous resistance increase. An
  infinite ratio pollutes any aggregation of the increase fractions; the
  open circuit is carried as its own outcome and counted separately.
- Widening the permitted loss to let an exactly-compliant coupon through.
  An equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the permitted value stays as
  specified.

## Behavior contract (gate 3)

The recovery-period check, the irradiance and temperature correction, the
output-power comparison, the per-circuit continuity screening and the
aggregated verdict are exercised by the gate 3 contract test:
scripts/test_e2008_humidity_test_pass_fail_criteria.py against
scripts/e2008_humidity_test_pass_fail_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_humidity_test_pass_fail_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

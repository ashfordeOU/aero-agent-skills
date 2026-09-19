---
name: q7006-dosimetry-and-monitoring
description: "Compute what a radiation degradation run actually delivered to the coupons under ECSS-Q-ST-70-06C and decide whether the dosimetry supports it: check each monitor's calibration is in date and traceable on the run date, require redundant monitors per agent so a drift can be seen at all, integrate the sampled flux over the run by trapezoid including beam trips, compare the redundant readings against the agreement limit, combine the uncertainty contributions in quadrature, and reconcile delivered exposure with target. Use when reviewing a run log or accepting facility dosimetry. Trigger: ecss, q-st-70-06c, irradiation-dosimetry-acceptance, monitor-calibration-validity, redundant-flux-monitor-agreement, delivered-fluence-integration, dosimetry-uncertainty-quadrature."
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
  tags: [ecss, q-st-70-06c-particle-and-uv-radiation-testing, q-st-70-06c, q7006-dosimetry-and-monitoring, irradiation-dosimetry-acceptance, monitor-calibration-validity, redundant-flux-monitor-agreement, delivered-fluence-integration, dosimetry-uncertainty-quadrature]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Dosimetry and Monitoring (space-systems/ecss/q7006-dosimetry-and-monitoring)

Use when the task is the dosimetry part of the facility clause of
ECSS-Q-ST-70-06C: what the coupons received while the beam was on, measured
by monitors whose calibration can be defended, and reconciled with what the
specification asked for.

## Domain quick reference

- The delivered exposure is an integral, not a set point. Flux drifts, the
  source warms, the beam trips and is restarted; the fluence the coupons saw
  is the area under the sampled flux against time, and a nominal flux
  multiplied by elapsed time counts the trips as exposure.
- One monitor cannot be checked. A drifting instrument reports a smooth,
  plausible record right up to the point it is recalibrated, so at least two
  independent monitors read each agent and their disagreement is the only
  in-run evidence that either can be believed.
- Agreement is a relative figure about the mean of the pair, so it does not
  presuppose which of the two is correct. A pair outside the agreement limit
  invalidates the delivered figure; it does not license picking the reading
  that suits the result.
- Calibration validity is a date question, decided against the run date.
  An instrument calibrated after the run, or whose interval expired before
  it, produces a number with no traceable meaning, and an untraceable
  calibration is the same defect with a different cause.
- Uncertainties combine in quadrature, not by addition, because the monitor
  contributions are independent. The combined figure travels with the
  delivered exposure and is what the acceptance band is judged against.
- Delivery is bounded on both sides. Short delivery leaves the material
  untested at the specified level; overshoot puts it past the level and can
  saturate a degradation mechanism, so both are named and neither is quietly
  accepted as conservative.

## Workflow

1. Validate each monitor: the agent it reads, its calibration date and
   interval, whether that calibration is traceable, and the uncertainty it
   contributes. A non-integer interval or a malformed date is an input error.
2. Compute each monitor's expiry from its calibration date and interval, and
   decide whether the run date falls inside it; a run before the calibration
   date is refused outright rather than treated as valid.
3. Integrate every monitor's sampled flux over the run by the trapezoidal
   rule, requiring strictly increasing sample times so a reordered log
   cannot silently produce a smaller exposure.
4. Group the monitors by agent and raise a finding for any agent read by
   fewer than the redundancy minimum.
5. Compare every pair of readings for an agent and raise a finding when the
   worst deviation passes the agreement limit, absorbing representation error
   at the boundary with a named tolerance.
6. Average the redundant readings into the delivered exposure, combine the
   monitor uncertainties in quadrature, and judge the delivered figure
   against the target inside the acceptance band.
7. Return the run record — per monitor and per agent — with every finding,
   and accept the dosimetry only when there are none.

## Pitfalls

- Reporting nominal flux times elapsed time. Every beam trip and every drift
  is then counted as exposure, and the coupons are credited with a fluence
  the log itself shows they did not receive.
- Monitoring an agent with a single instrument. The record looks clean
  whatever the instrument did, and the first evidence of a drift arrives at
  the next calibration, long after the coupons were measured.
- Resolving a monitor disagreement by preferring one reading. The pair is
  outside its limit; that is a finding about the run, and choosing the
  convenient reading converts a known defect into an unknown one.
- Adding percentage uncertainties. Independent contributions combine in
  quadrature, and summing them inflates the stated uncertainty enough to make
  an out-of-band delivery look acceptable.
- Treating overshoot as conservative. Past the specified level a degradation
  mechanism can saturate or a second one can start, so an over-delivered run
  is not a stronger version of the specified one.
- Checking calibration against the report date. Validity is decided on the
  day the beam was on, and a recalibration afterwards does not retrospectively
  qualify the instrument that made the measurement.

## Behavior contract (gate 3)

The monitor validation, calibration expiry and validity, trapezoidal exposure
accumulation, redundancy and agreement checks, quadrature uncertainty
combination and the delivery verdict are exercised by the gate 3 contract
test: scripts/test_q7006_dosimetry_and_monitoring.py against
scripts/q7006_dosimetry_and_monitoring_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7006_dosimetry_and_monitoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

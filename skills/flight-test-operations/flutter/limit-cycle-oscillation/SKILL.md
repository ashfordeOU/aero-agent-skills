---
name: limit-cycle-oscillation
description: "Use when you must assess a limit cycle oscillation (LCO) during a flight test flutter clearance campaign: compute the damping ratio from the log decrement of the decaying oscillation, estimate the amplitude growth rate from the amplitude time history, judge whether the oscillation is sustained or diverging at a fixed airspeed, and compute the amplitude margin against the limit amplitude. Covers freeplay and nonlinear damping effects on LCO onset below the linear flutter speed, and the amplitude stability band that separates sustained oscillation from flutter divergence. Produces damping ratios, growth rates, amplitude margins, and clearance verdicts that feed the flutter clearance decision. Trigger: limit cycle oscillation, LCO, sustained oscillation, freeplay, nonlinear damping, amplitude stability, log decrement, amplitude margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: flutter
  tags: [limit-cycle-oscillation, lco, sustained-oscillation, freeplay, nonlinear-damping, amplitude-stability, log-decrement, amplitude-margin, damping-ratio, growth-rate, flutter, clearance, airspeed, oscillation, damping]
  version: 0.1.0
  author: Aero Agent Skills
---

# Limit Cycle Oscillation (flight-test-operations/flutter/limit-cycle-oscillation)

Use when the task is limit cycle oscillation (LCO) assessment for a
flight test flutter clearance campaign: damping ratio from the log
decrement, amplitude growth rate from the amplitude time history,
sustained versus diverging oscillation at a fixed airspeed, amplitude
margin against the limit amplitude, and the effect of control surface
freeplay and nonlinear damping on LCO onset.

## Domain quick reference

- Log decrement from a decaying amplitude history: delta = (1/n) *
  ln(A_0 / A_n), with A_0 the amplitude at the start and A_n the
  amplitude n oscillation cycles later (m or deg; the ratio makes the
  decrement dimensionless). Example: amplitude falling from 5.0 mm to
  2.5 mm in one cycle gives delta = ln(2) = 0.693.
- Damping ratio from the log decrement: zeta = delta / sqrt(4 * pi^2
  + delta^2), dimensionless. Example: delta = 1.0 gives zeta = 1 /
  sqrt(4 * pi^2 + 1) = 0.157; for small delta the ratio approaches
  delta / (2 * pi); delta = 0 gives zeta = 0 (undamped). The formula
  is valid only for a decaying response, so delta must be non-
  negative.
- Amplitude growth rate: the linear least squares slope of amplitude
  versus time, slope = (N * sum(t*A) - sum(t) * sum(A)) / (N *
  sum(t^2) - (sum(t))^2), with amplitude in m and time in s, so the
  slope is in m/s (or deg/s for angular amplitude). A positive slope
  means the amplitude is growing (flutter-like divergence), a slope
  within tolerance at a fixed airspeed means the amplitude is
  stabilizing (the LCO signature), and a negative slope means the
  response is decaying.
- LCO amplitude margin: margin = (A_limit - A) / A_limit, with A the
  measured sustained amplitude and A_limit the limit amplitude of the
  clearance basis, both in the same unit. Positive margin means below
  the limit, zero means at the limit, negative means above the limit.
- Sustained LCO verdict: the oscillation is sustained when the
  amplitude stabilizes (|growth rate| within tolerance) at a fixed
  airspeed with the amplitude at or below the limit amplitude.
  Clearance requires a positive margin to the limit amplitude, no
  growing trend, and airspeed at or below the limit speed.
- Freeplay effect: freeplay in a control surface hinge creates a
  deadband of near-zero hinge stiffness below the freeplay angle;
  once the oscillation amplitude exceeds the deadband the effective
  stiffness drops, and LCO can onset at airspeeds below the linear
  flutter speed, so the linear extrapolation is not conservative.
- FAR-25 (14 CFR Part 25) and CS-25 set the flutter clearance context
  (25.629 family: the airframe must be free of flutter and sustained
  oscillations within the envelope with margin); the LCO relations
  above are common flight test practice feeding that clearance.

## Workflow

1. Extract the amplitude time history at the test airspeed from
   accelerometer, gyro, or strain data band-passed at the mode
   frequency, and record the test airspeed against the limit speed.
2. Estimate the damping from decaying segments of the response with
   log_decrement(amplitudes, cycles), then convert with
   damping_ratio_from_log_decrement(delta).
3. Fit the amplitude trend with
   amplitude_growth_rate(amplitudes, times) and classify it as
   growing, stable (sustained), or decaying.
4. Compute the margin with
   lco_amplitude_margin(amplitude, amplitude_limit) and compare the
   sustained amplitude with the limit amplitude of the clearance
   basis.
5. Combine airspeed band, amplitude band, and damping trend with
   lco_verdict(airspeed, limit_speed, amplitude, amplitude_limit,
   damping_slope, ...); the sustained_lco flag marks the LCO
   signature and the clearance field applies the margin requirement.
6. Flag control surface freeplay with
   freeplay_lco_onset_risk(freeplay_angle_deg) and re-check the LCO
   onset speed when freeplay is present, since the linear flutter
   speed is not conservative.

## Pitfalls

- Using the flutter speed extrapolation where LCO amplitude
  assessment belongs: LCO is bounded and flutter is divergent, so the
  damping trend and amplitude stabilization separate them, not the
  peak amplitude alone.
- Treating a single large spike as sustained LCO: sustained means the
  amplitude stabilizes within tolerance at a fixed airspeed; one
  transient peak is not an LCO and needs a longer record.
- Feeding a negative log decrement to the damping ratio: a negative
  decrement means the amplitude is growing, and the damping ratio
  formula is undefined for it (ValueError); re-check the data
  segment instead of forcing a damping value.
- Mixing units: amplitudes in mm and m, or time in minutes with
  amplitude in m; keep everything SI (m, s) so the growth rate is
  m/s and the margin is a clean ratio.
- Clearing an oscillation sitting exactly at the limit amplitude: a
  zero margin at the limit is not clearance; the verdict applies the
  required margin above the limit amplitude, not equality.
- Ignoring freeplay: a control surface with freeplay can show LCO
  onset below the linear flutter speed, so the linear flutter speed
  extrapolation alone is not conservative for the clearance.
- Passing zero or negative inputs: amplitude limits and speeds must
  be positive, and amplitudes non-negative; the module raises
  ValueError instead of returning a nonsense margin or verdict.

## Behavior contract (gate 3)

The log decrement, damping ratio, amplitude growth rate, amplitude
margin, LCO verdict, and freeplay onset risk logic is exercised by
the gate 3 contract test: scripts/test_limit_cycle_oscillation.py
against scripts/limit_cycle_oscillation.py (stdlib unittest,
offline). Run:
python3 scripts/test_limit_cycle_oscillation.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the LCO
  assessment methodology (log decrement damping, amplitude growth
  rate, amplitude margin, freeplay effects) is common flight test
  practice in the flutter clearance context of the 25.629 family,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

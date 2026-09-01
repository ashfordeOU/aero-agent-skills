---
name: dynamic-stability-flight-test
description: "Plan and analyze a dynamic stability flight test: select the excitation technique for each mode (elevator doublet for the short period, elevator pulse for the phugoid, rudder pulse for the Dutch roll, aileron step for roll subsidence, rudder step for the spiral), reduce the decaying oscillation records to the log decrement, damping ratio, damped and undamped frequencies, time to half amplitude, and cycles to half amplitude, and return a handling qualities verdict per band. Produces the mode identification summary and the acceptable, marginal, or inadequate verdict that gates the stability demonstration. Use when the task is dynamic stability flight testing, mode damping estimation, log decrement analysis, or handling qualities assessment. Trigger: dynamic stability, short period, phugoid, Dutch roll, log decrement, damping ratio, handling qualities."
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
  subdomain: stability
  tags: [dynamic-stability, short-period, phugoid, dutch-roll, log-decrement, handling-qualities]
  version: 0.1.0
  author: AeroSkills
---

# Dynamic Stability Flight Test (flight-test-operations/stability/dynamic-stability-flight-test)

Use when the task is a dynamic stability flight test: mode excitation,
decaying oscillation reduction, and handling qualities verdicts.

## Domain quick reference

- Each mode is excited with a control input: elevator doublet or
  pulse for the short period, elevator pulse for the phugoid, rudder
  pulse for the Dutch roll, aileron step for roll subsidence, rudder
  step for the spiral. The response time history is recorded until
  the oscillation damps (2 to 3 full cycles for the long-period
  phugoid).
- Log decrement from same-sign peak amplitudes n cycles apart:
  delta = (1/n) * ln(A0 / An). The mode must decay; equal or growing
  amplitudes raise a no-decay error.
- Damping ratio: zeta = delta / sqrt(delta^2 + 4 * pi^2). For small
  delta, zeta is about delta / (2 * pi).
- Frequencies: damped w_d = 2 * pi / T_d from the peak period, undamped
  w_n = w_d / sqrt(1 - zeta^2) for an under-damped mode.
- Decay times: time to half amplitude t_half = ln(2) / (zeta * w_n),
  cycles to half amplitude N = ln(2) / (2 * pi * zeta). A divergent
  mode (zeta < 0) has a time to double amplitude.
- Handling qualities verdicts use the typical flight test practice
  bands (certification values in FAR-25 / CS-25 take precedence):
  short period 0.3 to 2.0 acceptable, 0.08 to 0.3 marginal, below
  0.08 inadequate; Dutch roll 0.08 to 2.0 acceptable, 0.02 to 0.08
  marginal, below 0.02 inadequate; phugoid 0.04 to 2.0 acceptable;
  spiral must converge (zeta >= 0), else divergent.

## Workflow

1. Choose the excitation for the mode with excitation_technique.
2. Record the response and extract the same-sign peak amplitudes and
   their timestamps (local_maxima helps find the peaks).
3. Reduce the sequence with mode_identification: log decrement,
   damping ratio, period, damped and undamped frequencies, and time
   to half amplitude.
4. Judge the result with handling_qualities_verdict against the band
   table.
5. For a divergent mode, report time_to_double_amplitude instead of a
   half-amplitude time.

## Pitfalls

- Using peaks of alternating sign: the log decrement needs same-sign
  peaks n whole cycles apart.
- Reading the undamped frequency as the damped value: w_n is always
  larger than w_d for zeta > 0.
- Quoting a half-amplitude time for a divergent mode: apply the time
  to double amplitude.
- Treating the band values as regulation text: they are typical flight
  test practice; the certification criteria in the cited standards
  take precedence.

## Behavior contract (gate 3)

The dynamic stability logic is exercised by the gate 3 contract test:
scripts/test_dynamic_stability_flight_test.py against
scripts/dynamic_stability_flight_test_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_dynamic_stability_flight_test.py

## Compliance

- The excitation techniques, log decrement reduction, and damping
  relations are common flight test methodology, paraphrased here.
  FAR-25 and CS-25 are cited as reference only for the stability
  demonstration context; no proprietary or copyrighted text is
  reproduced.
- compliance: STANDARDS-REF, gated: false.

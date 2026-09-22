---
name: e50-telemetry-data-time-stamping
description: "Compute the time-stamp error budget of a telemetry stream against ECSS-E-ST-50C clause 5.5.5: gather the contributors that separate the sampling instant from the stamp actually downlinked, namely on-board clock drift since the last time correlation, acquisition-to-stamp latency, correlation residual and field quantisation, combine them worst-case or root-sum-square, size the time field from the mission span and the least significant bit, and screen the stamp sequence for a non-monotonic step. Use when specifying a time-stamp field, verifying a time-correlation procedure, or explaining a mis-ordered telemetry archive. Trigger: ecss, e-st-50-communications-scope, telemetry-data-time-stamping, on-board-clock-drift-budget, time-correlation-residual, stamp-field-quantisation, sampling-to-stamp-latency, telemetry-stamp-monotonicity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.5.5
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications-scope, e50-telemetry-data-time-stamping, telemetry-time-stamp-budget, on-board-clock-drift-budget, time-correlation-residual, stamp-field-quantisation, sampling-to-stamp-latency, telemetry-stamp-monotonicity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Telemetry Data Time Stamping (space-systems/ecss/e50-telemetry-data-time-stamping)

Use when the task is the time-stamping provision of ECSS-E-ST-50C clause
5.5.5 — showing that the time attached to a telemetry datum identifies
the instant the datum was sampled, to a stated accuracy, and that the
stamp can be carried back to a ground time reference.

## Domain quick reference

- The stamp answers for the sampling instant, not for the packetisation
  instant. Everything between the two — the acquisition conversion, the
  queue into the packetiser, the frame assembly — is latency that has to
  be either compensated in the stamp or carried as an error contributor.
- On-board time drifts against the ground reference between correlations.
  The drift contribution is the clock stability in parts per million
  times the elapsed time since the last correlation, so the budget grows
  linearly with correlation interval and is the term that dominates on
  a mission that correlates once a week.
- Quantisation is set by the least significant bit of the time field,
  and the error it contributes is half that bit, not the whole bit. It is
  the one contributor that cannot be reduced by better operations: it is
  fixed by the field format.
- Worst-case and root-sum-square are different answers to different
  questions. Worst-case addition is right when the contributors can align
  and the requirement is an envelope; root-sum-square is right when they
  are independent random terms. The combination rule belongs in the
  assessment inputs, not implicitly in the arithmetic.
- The time field has to span the mission and resolve the requirement at
  once. The number of bits is set by the span divided by the least
  significant bit; a field that wraps mid-mission is an ambiguity, and a
  field whose least significant bit is coarser than the accuracy
  requirement cannot meet it however good the clock is.
- Monotonicity is evidence, not decoration. A stamp sequence that steps
  backwards means a correlation update was applied inside a stream, or
  two sources were merged with different references; both change what the
  archive means.

## Workflow

1. Validate each contributor: a non-negative magnitude in seconds with a
   name. A negative or non-finite contributor is an input error.
2. Compute the drift contribution from the clock stability and the
   elapsed time since the last time correlation.
3. Compute the quantisation contribution as half the least significant
   bit of the time field.
4. Combine the contributors by the declared rule — worst-case sum or
   root-sum-square — and report both the total and the ranked
   contributions, so the dominant term is visible.
5. Compare the total with the required stamp accuracy, absorbing
   floating-point representation error at the boundary with a named
   tolerance rather than by relaxing the requirement.
6. Size the time field: the bits needed to enumerate the mission span at
   the chosen least significant bit, compared with the declared field
   width.
7. Screen the stamp sequence for a backward step, and report its index
   and size rather than a bare pass or fail.
8. Put the streams side by side: confirm every on-board application that
   produces telemetry attaches a stamp, and that all of them read the
   one common on-board reference, so that data acquired by two different
   applications can still be placed in order once it reaches the ground.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.5.5a | 8 |

## Pitfalls

- Stamping at packetisation and calling it the sampling time. On a
  spacecraft that buffers before downlink the two differ by far more than
  the accuracy requirement, and the error is systematic, so it never
  averages out.
- Taking the whole least significant bit as the quantisation error.
  Half the bit is the correct magnitude, and using the whole bit
  overstates the budget enough to drive an unnecessary field change.
- Budgeting drift over the pass instead of over the correlation
  interval. The clock has been free-running since the last correlation,
  not since acquisition of signal.
- Mixing the combination rules within one budget. Summing some terms and
  root-sum-squaring others gives a number that belongs to neither
  question; choose the rule for the budget and state it.
- Sizing the field from the requirement alone. The span sets the number
  of bits above the least significant bit; a field that meets the
  accuracy but wraps before end of mission fails on the other side.

## Behavior contract (gate 3)

The contributor validation, drift and quantisation computation, the
worst-case and root-sum-square combination, the accuracy comparison,
field sizing and monotonicity screening are exercised by the gate 3
contract test: scripts/test_e50_telemetry_data_time_stamping.py against
scripts/e50_telemetry_data_time_stamping_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e50_telemetry_data_time_stamping.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

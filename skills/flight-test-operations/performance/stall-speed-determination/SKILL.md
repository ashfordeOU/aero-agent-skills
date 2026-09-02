---
name: stall-speed-determination
description: "Use when you must determine the reference stall speed Vs1g for a flight test: derive it from the wing loading and the maximum lift coefficient, correct it for a weight change, and check the stall margin against the current flight speed. Produces the Vs1g reference stall speed in m/s, the weight-corrected stall speed, and the stall margin verdict that gate the performance assessment. Trigger: Vs1g, stall speed, wing loading, stall margin, flight test, weight correction."
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
  subdomain: performance
  tags: [stall-speed, vs1g, wing-loading, stall-margin, weight-correction, flight-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# Stall Speed Determination (flight-test-operations/performance/stall-speed-determination)

Use when the task is stall speed determination for a flight test:
reference stall speed Vs1g from wing loading and maximum lift
coefficient, weight correction, and stall margin checks.

## Domain quick reference

- Wing loading W/S is in N/m^2, air density rho in kg/m^3, and
  speeds in m/s.
- Vs1g = sqrt(2*(W/S)/(rho*CLmax)) is the 1g reference stall speed.
- Stall speed scales with the square root of the weight ratio:
  V_new = Vs1g*sqrt(W_new/W_ref).
- Stall margin = (V_current - Vs1g)/Vs1g; a negative margin means the
  current speed is below the reference stall speed.

## Workflow

1. Collect the wing loading, air density, and maximum lift
   coefficient.
2. Derive the reference stall speed with vs1g.
3. Correct for the weight change with weight_corrected_stall_speed.
4. Check the stall margin with stall_margin.
5. Gate the flight test on the margin verdict.

## Pitfalls

- Using Vso instead of Vs1g: Vso is the stalling speed in the landing
  configuration at maximum weight, not the 1g reference stall speed.
- Correcting weight with linear instead of sqrt scaling: stall speed
  scales with the square root of the weight ratio, not the ratio
  itself.
- Misinterpreting a negative stall margin: it is not an error; a
  current speed below Vs1g is a real, reportable stall-onset risk.

## Behavior contract (gate 3)

The vs1g, weight correction, and stall margin logic is exercised by
the gate 3 contract test: scripts/test_stall_speed.py against
scripts/stall_speed_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_stall_speed.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the stall speed
  method is common flight-test methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

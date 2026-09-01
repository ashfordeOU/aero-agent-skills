---
name: spin-testing
description: "Plan and execute the spin flight test: build the spin test point matrix across configurations, center of gravity positions, weights, and altitudes, flag the points outside the approved CG envelope, classify the entry, incipient, and developed spin phases from the rotation, apply the recovery control procedure and check the recovery against the turn count and altitude loss limits, decide when the recovery parachute is required, and judge the FAR 25.201 spin resistance verdict with pro-spin controls held at the stall. Produces the test point matrix, the phase classification, the recovery verdict, the parachute decision, and the spin resistance assessment. Use when the task is spin flight testing, spin recovery, spin resistance, or recovery parachute planning. Trigger: spin testing, spin entry, incipient spin, developed spin, spin recovery, recovery parachute, spin resistance, FAR 25.201, spin test point matrix."
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
  subdomain: envelope
  tags: [spin-testing, spin-entry, incipient-spin, developed-spin, spin-recovery, recovery-parachute, spin-resistance, pro-spin-controls, spin-test-point-matrix, flight-test-envelope]
  version: 0.1.0
  author: AeroSkills
---

# Spin Testing (flight-test-operations/envelope/spin-testing)

Use when the task is the spin flight test: the spin test point matrix
across configuration, center of gravity, weight, and altitude, the
entry, incipient, and developed spin phases, the recovery control
procedure and its turn count and altitude loss criteria, the recovery
parachute decision, and the spin resistance verdict with pro-spin
controls held at the stall. This leaf covers the spin itself and its
recovery; the stall boundary and warning onset are the
stall-characteristics-testing leaf, and the post-stall and deep stall
envelope with departure and spin entry resistance from the high angle
of attack side is the high-angle-of-attack-testing leaf.

## Domain quick reference

- Spin entry procedure: from a stabilized condition at or above the
  entry altitude, slow to the stall, then apply the pro-spin controls
  (full aft stick, full rudder in the spin direction, ailerons neutral
  or with the rotation) and hold them until autorotation develops; the
  entry point is recorded at the first sustained yaw rate.
- Incipient versus developed spin: the incipient phase covers the
  first 1 to 2 turns while the rotation rate builds and the motion is
  not yet steady; the developed spin is the steady autorotation with a
  stabilized yaw rate, typically from about 2 turns onward.
- Spin recovery controls: the standard recovery is opposite rudder
  against the rotation, stick forward to break the stall, and ailerons
  neutral, held until rotation stops, then the resulting dive is
  arrested; recovery is measured from the moment the recovery controls
  are applied.
- Recovery criteria: a program typically requires the recovery to be
  complete within a set turn count (for example 2 additional turns) and
  a set altitude loss (for example 3000 m) from recovery control
  application; exceeding either limit marks the spin unrecoverable by
  the criterion.
- Recovery parachute requirements: the spin chute is the last-resort
  recovery device, required when there is no prior recovery
  demonstration for the configuration, when developed spin testing is
  planned, when the recovery check predicts an unrecoverable spin, or
  on the first flight of a new configuration.
- Test point matrix: points combine configuration (gear and flap
  setting), CG position in percent MAC, gross weight, and pressure
  altitude; the critical points are the aft CG, the light weight, and
  the high altitude cases, and points outside the approved CG envelope
  are flagged for envelope approval or parachute coverage before they
  fly.
- Spin-resistant criteria (FAR 25.201 / CS-25.201 context,
  paraphrased): in the stall demonstration with pro-spin controls
  applied at the stall, the airplane must be resistant to spinning; if
  autorotation develops it must stay within the allowed turn count and
  altitude loss and stop promptly.
- Instrumentation and data reduction: rotation rate, bank angle, angle
  of attack, sideslip, control positions, altitude and altitude loss,
  and the turn count from entry are recorded and reduced per flight;
  the phase classification uses the turn count and the sustained yaw
  rate.
- Safety and abort criteria: a minimum entry altitude floor, the
  parachute arm and disarm sequence, and the abort rule that the spin
  is terminated the moment the recovery controls fail to stop the
  rotation within the limits.

## Workflow

1. Build the spin test point matrix with
   spin_test_point_matrix(configs, cg_conditions, weights_kg,
   altitudes_m): every combination of configuration, CG, weight, and
   altitude is one point, and each point carries the cg_envelope_ok
   flag against the approved CG envelope.
2. Classify the rotation with
   spin_phase_classify(turns, yaw_rate_deg_s) to label the entry,
   incipient, and developed phases of each spin.
3. Check the recovery with
   spin_recovery_check(turns_to_recover, altitude_loss_m,
   turns_limit, altitude_loss_limit_m) for each spin flown.
4. Decide the recovery parachute with
   recovery_parachute_requirement(prior_recovery_demonstrated,
   developed_spin_planned, unrecoverable_predicted, first_flight)
   before the campaign starts and before any developed spin point.
5. Judge the spin resistance with
   spin_resistance_check(pro_spin_turns, pro_spin_altitude_loss_m,
   max_allowed_turns, max_allowed_altitude_loss_m) for the
   pro-spin control checks at the stall.
6. Confirm the deterministic behavior with the contract test
   scripts/test_spin_testing.py.

## Worked example

A transport test program plans spin points over configurations
[clean, takeoff-flaps], CG positions [18.0, 30.0, 36.0] percent MAC,
weights [18000, 21000] kg, and altitudes [3000, 6000] m, with an
approved CG envelope of 15 to 35 percent MAC:

- spin_test_point_matrix builds 2 * 3 * 2 * 2 = 24 points; the 8
  points at 36.0 percent MAC carry cg_envelope_ok False and need
  envelope approval or parachute coverage before they fly.
- spin_phase_classify(0.5, 25.0) returns "entry";
  spin_phase_classify(1.5, 30.0) returns "incipient";
  spin_phase_classify(2.5, 40.0) returns "developed".
- spin_recovery_check(1.5, 1800.0) against the 2 turn and 3000 m
  limits returns recoverable; spin_recovery_check(3.5, 1500.0)
  exceeds the turn limit and returns unrecoverable.
- With no prior recovery demonstration and developed spins planned,
  recovery_parachute_requirement returns required with two reasons,
  so the spin chute is fitted before the developed spin points.
- spin_resistance_check(0.8, 900.0) against the 1 turn and 1500 m
  limits returns resistant; spin_resistance_check(2.1, 800.0)
  returns not-resistant.

## Related leaves

This leaf sits in the envelope pack beside
stall-characteristics-testing (the stall boundary, warning onset, and
stall recovery demonstration), high-angle-of-attack-testing (the
post-stall and deep stall envelope with departure and spin entry
resistance), envelope-expansion (clearing the envelope that spin
testing probes), and v-speeds (the speed references for the entry
maneuvers).

## Behavior contract (gate 3)

The matrix builder, phase classification, recovery check, parachute
requirement, and spin resistance logic is exercised by the gate 3
contract test: scripts/test_spin_testing.py against
scripts/spin_testing_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_spin_testing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the spin entry,
  phase, recovery, parachute, and spin resistance practice is common
  flight test methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

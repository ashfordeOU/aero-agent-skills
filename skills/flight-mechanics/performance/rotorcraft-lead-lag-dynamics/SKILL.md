---
name: rotorcraft-lead-lag-dynamics
description: "Use when you must compute the lead-lag dynamics of a helicopter main rotor: the lead-lag frequency ratio from the lag-hinge offset of an idealized uniform blade or as a measured or design input, the fixed-frame lag mode frequencies of a 3+ bladed rotor (collective, regressing, advancing), and the coincidence rotor speed where the regressing lag mode meets the airframe lateral frequency, with a ground-resonance clearance verdict at the operating rotor speed. Produces the lag frequency ratio, mode frequencies, the coincidence rotor speed and a clear or resonance-adjacent verdict. Trigger: rotorcraft lead lag dynamics, lag hinge offset, regressing lag mode, coincidence rotor speed, ground resonance clearance, multiblade modes, articulated rotor."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [rotorcraft-lead-lag-dynamics, lead-lag-frequency, lag-hinge-offset, regressing-lag-mode, ground-resonance-clearance, coincidence-rotor-speed, multiblade-modes]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Lead-Lag Dynamics (flight-mechanics/performance/rotorcraft-lead-lag-dynamics)

Use when the task is the lead-lag dynamics of a helicopter main rotor:
the rotating lead-lag (in-plane) frequency ratio of an idealized uniform
blade from its lag-hinge offset, the fixed-frame multiblade lag mode
frequencies for a rotor with three or more blades, and the rotor speed at
which the regressing lag mode coincides with the airframe lateral
frequency (Coleman-diagram coincidence), returning a ground-resonance
clearance verdict against the operating rotor speed. This leaf implements
the deterministic frequency-coincidence and clearance layer in pure
Python, stdlib only, deterministic: damping and coupled eigenvalue
stability analysis are out of scope, and blade flapping motion, coning and
the rotating flap natural frequency belong to the flap-dynamics sibling.
The momentum-theory hover leaves own rotor power and inflow.

## Domain quick reference

- Rotating lead-lag frequency ratio: nu = sqrt(1.5 * e / (1 - e)), with e
  the lag-hinge offset as a fraction of rotor radius, idealized uniform
  blade, centrifugal-potential derivation (the in-plane analog of the flap
  frequency formula). At e = 0 the rotating lag frequency is exactly zero,
  because lag has no 1/rev term (unlike flap, where nu = 1 at e = 0).
  Published articulated lag frequencies run about 0.2-0.4 per rev; e = 0.5
  gives sqrt(1.5) = 1.2247.
- Fixed-frame multiblade modes (3+ bladed rotor): the per-blade lag motion
  at nu per rev maps to collective, regressing and advancing fixed-frame
  modes with frequencies nu*Omega, |1 - nu|*Omega and (1 + nu)*Omega
  respectively, where Omega is the rotor speed in rad/s and the factor
  converts per-rev to Hz via /2pi.
- Regressing lag mode: the fixed-frame mode that sweeps downward through
  the airframe frequencies as the rotor slows, which makes ground
  resonance a low-rotor-speed phenomenon.
- Coincidence rotor speed: Omega* = 2*pi*omega_F / |1 - nu| in rad/s, the
  rotor speed at which the regressing lag mode frequency equals the
  airframe lateral frequency omega_F in Hz. Stiff-inplane designs push nu
  above 1 so the coincidence sits far from the operating speed.
- Clearance verdict: with clearance_fraction = (Omega* - Omega_op) /
  Omega_op, the operating point is "clear" when |clearance_fraction| is
  more than the margin (default 0.20) from the operating speed, else
  "resonance-adjacent".
- Units are SI throughout: Hz, rad/s, dimensionless ratios and fractions.
- FAR-29 frames the transport-category rotorcraft certification context;
  the relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the rotor inputs: the lag-hinge offset fraction e (typical
   articulated 0.02-0.05) or a measured or design lag frequency ratio nu,
   the operating rotor speed Omega in rad/s, and the airframe lateral
   natural frequency in Hz.
2. Get the lag frequency ratio with
   lag_frequency_ratio_hinge_offset(e); e = 0 is the exact zero limit,
   larger offsets stiffen the blade in plane. Skip this step when nu is
   the direct input.
3. Compute the three fixed-frame mode frequencies with
   fixed_frame_lag_modes(nu, Omega): collective, regressing and advancing
   in Hz, and confirm the regressing mode with
   regressing_lag_frequency(nu, Omega).
4. Compute the coincidence rotor speed with
   coincidence_rotor_speed(nu, airframe_frequency_hz): the Coleman-diagram
   crossing where the regressing mode meets the airframe lateral mode.
5. Judge the operating point with ground_resonance_clearance(nu, Omega,
   airframe_frequency_hz, margin): resonance-adjacent when the coincidence
   sits within margin of the operating speed, else clear.
6. Run lead_lag_summary(e_or_nu, Omega, airframe_frequency_hz) for the
   one-call assessment dict with all eight documented keys
   (lag_frequency_ratio, collective_hz, regressing_hz, advancing_hz,
   coincidence_omega, operating_omega, clearance_fraction, verdict). Input
   convention: a first argument below 1 is the hinge offset fraction e and
   is converted by the formula; a value of 1 or more is taken as nu
   directly, matching design practice where stiff-inplane rotors are
   specified by a measured nu at or above 1/rev.
7. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_lead_lag_dynamics.py.

## Worked example

Typical articulated rotor: lag-hinge offset e = 0.05, operating rotor
speed Omega = 44 rad/s, airframe lateral natural frequency 5.0 Hz. Real
module outputs:

- lag_frequency_ratio_hinge_offset(0.05) = 0.28098, inside the published
  0.2-0.4 per rev articulated lag band.
- fixed_frame_lag_modes(0.28098, 44): collective 1.96762 Hz, regressing
  5.03520 Hz (0.719/rev), advancing 8.97044 Hz.
- coincidence_rotor_speed(0.28098, 5.0) = 43.69244 rad/s, about 0.7%
  below the operating 44 rad/s.
- ground_resonance_clearance(0.28098, 44, 5.0) returns
  clearance_fraction -0.00699 and verdict resonance-adjacent, the classic
  ground-resonance exposure for a typical articulated rotor at operating
  speed.
- With a separated airframe frequency of 3.5 Hz,
  coincidence_rotor_speed(0.28098, 3.5) = 30.58471 rad/s (about 30.5%
  below operating), clearance_fraction -0.30489 and verdict clear.
- lead_lag_summary(0.05, 44, 5.0) returns the eight-key dict above with
  lag_frequency_ratio 0.28098, regressing_hz 5.03520, coincidence_omega
  43.69244 and verdict resonance-adjacent.

## Verification

- Confirm lag_frequency_ratio_hinge_offset(0.05) returns about 0.2810 in
  the 0.2-0.4 band, e = 0 returns exactly 0.0, larger e always raises nu,
  and e = 0.5 returns sqrt(1.5) = 1.2247.
- Confirm the fixed-frame identities: regressing_hz = |1 - nu|*Omega/2pi,
  advancing_hz = (1 + nu)*Omega/2pi, and the regressing mode falls while
  the advancing mode rises as nu increases.
- Confirm coincidence_rotor_speed(0.28098, 5.0) about 43.69 rad/s and the
  resonance-adjacent verdict at operating 44 rad/s; the 3.5 Hz airframe
  case is clear; the margin parameter moves the verdict boundary.
- Confirm the summary dict contains exactly the eight documented keys and
  that its values match the component functions for the same inputs.
- Confirm ValueError rejection of hinge offset below 0 or at or above 1,
  nu below 0, rotor speed at or below 0, airframe frequency at or below 0,
  the |1 - nu| = 0 coincidence guard, and a negative margin.
- Run the contract test offline: python3
  scripts/test_rotorcraft_lead_lag_dynamics.py (30 tests, deterministic,
  no network).

## Related leaves

- flight-mechanics/performance/rotorcraft-blade-flapping-dynamics: the
  flap-dynamics sibling, which owns blade flapping, coning and the
  rotating flap natural frequency from its hinge offset; the lead-lag nu
  formula here is this leaf's own.
- flight-mechanics/performance/rotorcraft-blade-element-hover-performance:
  blade-element hover thrust and torque from the same rotor geometry
  inputs, on the power side of the rotorcraft family.
- flight-mechanics/stability-control/spin-recovery: fixed-wing
  autorotation of a stalled wing is a different topic and lives in the
  fixed-wing stability leaves.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_lead_lag_dynamics.py

The test covers the worked example magnitude bounds (lag frequency ratio
about 0.2810 in the 0.2-0.4 per rev band, modes at 44 rad/s about 1.968 /
5.035 / 8.970 Hz, coincidence about 43.69 rad/s for the 5.0 Hz airframe
and about 30.58 rad/s for 3.5 Hz), the exact zero-offset limit, the
sqrt(1.5) closed form at e = 0.5, the multiblade closed-form identities
and trends, coincidence closed form and scaling, margin boundary
behavior, the summary input convention, ValueError rejection of every
non-physical input including the |1 - nu| = 0 guard, and run-to-run
determinism.

## Compliance

- Standards referenced, not reproduced: FAR-29 is the FAA
  transport-category rotorcraft airworthiness standard (ecfr.gov); the
  lead-lag relations above are standard engineering methodology (Johnson,
  Leishman), summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

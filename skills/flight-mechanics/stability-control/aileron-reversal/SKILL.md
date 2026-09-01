---
name: aileron-reversal
description: "Use when you must assess the aileron control reversal of a wing from its torsional stiffness: compute the reversal dynamic pressure q_rev = k_t / (C_l_alpha * eta * S * c * e) from the torsional stiffness about the elastic axis, the lift curve slope, the aileron effectiveness factor, the wing area, the mean chord, and the elastic axis to aerodynamic center offset, convert it into the reversal true airspeed with V_rev = sqrt(2 q_rev / rho) at the flight density, evaluate the aileron effectiveness fraction 1 - q / q_rev at the flight dynamic pressure, and check whether the dive speed limit exceeds the reversal speed for the control reversal verdict. Produces the reversal dynamic pressure, the reversal speed, the effectiveness fraction, and the reversed verdict that gate the aeroelastic control assessment. Trigger: aileron reversal, control reversal, reversal speed, torsional stiffness, elastic axis, aileron effectiveness, reversal dynamic pressure."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: stability-control
  tags: [aileron-reversal, control-reversal, reversal-speed, reversal-dynamic-pressure, torsional-stiffness, elastic-axis, aileron-effectiveness]
  version: 0.1.0
  author: AeroSkills
---

# Aileron Reversal (flight-mechanics/stability-control/aileron-reversal)

Use when the task is the aeroelastic control check of a wing: the
reversal dynamic pressure and reversal speed from the torsional
stiffness, the aileron effectiveness fraction at the flight dynamic
pressure, and the control reversal verdict against the dive speed
limit.

## Domain quick reference

- Reversal dynamic pressure from the torsional stiffness:
  q_rev = k_t / (C_l_alpha * eta * S * c * e), with k_t the wing
  torsional stiffness about the elastic axis in N m / rad, C_l_alpha
  the lift curve slope in per radian, eta the dimensionless aileron
  effectiveness factor (0 < eta <= 1), S the wing area in m^2, c the
  mean chord in m, and e the elastic axis to aerodynamic center
  offset in m; q_rev comes out in Pa.
- Reversal true airspeed from the dynamic pressure:
  V_rev = sqrt(2 q_rev / rho), with rho the air density in kg/m^3
  and the speed in m/s. Lower density at altitude raises the
  reversal speed.
- Aileron effectiveness fraction at a flight dynamic pressure:
  eff = 1 - q / q_rev. Unity at zero speed, zero at the reversal
  point, and negative beyond it: negative effectiveness is control
  reversal.
- Reversed verdict: the ailerons reverse when the flight dynamic
  pressure q exceeds q_rev, which the design dive speed must never
  reach. FAR-25.629 requires the airplane to be free from control
  reversal within the design envelope (CS-25.629 mirrors it).
- The method is the classical simplified aeroelastic estimate of the
  NACA TR-799 lineage; it assumes the aileron lift acts at the
  aerodynamic center, offset e behind the elastic axis.

## Workflow

1. Collect the torsional stiffness k_t, the lift curve slope, the
   aileron effectiveness factor eta, the wing area S, the mean chord
   c, and the offset e.
2. Compute the reversal dynamic pressure with
   reversal_dynamic_pressure.
3. Convert it to the reversal speed with reversal_speed at the flight
   density, or use reversal_speed_from_stiffness for the direct
   answer.
4. Compute the effectiveness fraction at the flight dynamic pressure
   q with aileron_effectiveness.
5. Check the verdict with is_reversed against the dive speed dynamic
   pressure q = 0.5 rho V_dive^2.
6. If reversed, raise k_t (stiffen the wing) or reduce the offset e
   and re-evaluate until the dive limit clears the reversal speed.

## Pitfalls

- Using the stiffness per unit span or the beam bending stiffness
  where the formula takes the total torsional stiffness k_t in
  N m / rad about the elastic axis.
- Setting eta above 1 or at 0: eta is a dimensionless effectiveness
  factor in (0, 1], and reversal_dynamic_pressure raises ValueError
  outside that range.
- Confusing the elastic axis with the aerodynamic center: e is the
  distance from the elastic axis to the aerodynamic center, positive
  when the aerodynamic center lies aft of the elastic axis.
- Quoting the reversal speed as an indicated or calibrated airspeed:
  V_rev is a true airspeed at the flight density rho, so it changes
  with altitude.
- Declaring reversal from a single negative effectiveness reading:
  the verdict must compare the dive speed dynamic pressure of the
  design envelope against q_rev.
- Mixing units: chord, area, and offset in m and m^2, stiffness in
  N m / rad, density in kg/m^3, angles in radians.

## Behavior contract (gate 3)

The aileron reversal logic is exercised by the gate 3 contract test:
scripts/test_aileron_reversal.py against
scripts/aileron_reversal_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_aileron_reversal.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the reversal
  estimate is common aeroelastic methodology in the NACA TR-799
  lineage, and FAR-25.629 / CS-25.629 set the control reversal
  requirement, all summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

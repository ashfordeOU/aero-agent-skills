---
name: divergence-speed
description: "Use when you must compute the static aeroelastic divergence condition of a lifting surface: calculate the divergence dynamic pressure from the torsional stiffness, the reference area, the chord, the lift curve slope, and the aerodynamic-center-to-shear-center offset ratio, convert it to the divergence speed at sea level, and assess the divergence margin against the design dive speed, flagging risk when the margin falls below the required 1.15 threshold. Produces the divergence dynamic pressure, the divergence speed, and a margin verdict that feed torsional stiffness sizing for divergence clearance. Trigger: divergence speed, divergence dynamic pressure, torsional stiffness, aerodynamic center, shear center, divergence margin, static aeroelastic divergence."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: aeroelasticity
  tags: [divergence, aeroelastic, divergence-speed, divergence-dynamic-pressure, divergence-margin, torsional-stiffness, shear-center, aerodynamic-center, dive-speed, lifting-surface, static-aeroelasticity]
  version: 0.1.0
  author: AeroSkills
---

# Static Aeroelastic Divergence (aerodynamics/aeroelasticity/divergence-speed)

Use when the task is the static aeroelastic divergence condition of a
lifting surface: the divergence dynamic pressure from the torsional
stiffness and the aerodynamic center to shear center offset, the
divergence speed, and the divergence margin against the design dive
speed.

## Domain quick reference

- Static divergence: the lift acts at the aerodynamic center, ahead of
  the shear center (elastic axis). Its torsional moment about the shear
  center twists the surface nose-up, which raises the local angle of
  attack and the lift. The destabilizing moment grows with the dynamic
  pressure; at the divergence dynamic pressure it overcomes the
  torsional stiffness and the twist grows without bound.
- Divergence dynamic pressure: q_div = k_theta / (S * c * C_Lalpha *
  e), where k_theta is the torsional stiffness about the shear center
  axis (N m per rad; for a beam model the product G * K_theta of the
  shear modulus and the torsion constant), S the reference area (m^2),
  c the chord (m), C_Lalpha the lift curve slope per radian, and e the
  offset ratio, the aerodynamic-center-to-shear-center distance divided
  by the chord, positive when the aerodynamic center lies ahead of the
  shear center. Worked example, k_theta = 40000 N m per rad, S = 16 m^2
  (2 m chord over an 8 m strip), c = 2 m, C_Lalpha = 5.0 per radian,
  e = 0.2 (aerodynamic center at 25 percent chord, shear center at 45
  percent chord): q_div = 1250 Pa.
- Divergence speed: V_div = sqrt(2 * q_div / rho) with the flight
  density; the ISA sea level value rho = 1.225 kg/m^3 is the default.
  For the example: V_div = 45.18 m/s. Thinner air at altitude raises
  the speed for the same q_div.
- Divergence margin: m = V_div / V_design. Common design practice keeps
  the margin at or above 1.15, a rule of thumb (not a regulatory limit;
  the airworthiness aeroelastic requirements belong to the
  certification standards and are referenced, not reproduced, in the
  standards map). For the example with V_design = 40 m/s: m = 1.129,
  below the threshold, so the surface is flagged at divergence risk and
  needs more torsional stiffness.
- Stiffness for a target margin: k_theta_req = q_target * S * c *
  C_Lalpha * e with q_target = 0.5 * rho * (margin * V_design)^2. For
  V_design = 40 m/s and margin 1.15 (V_div target 46 m/s): q_target =
  1296.05 Pa, k_theta_req = 41473.6 N m per rad, which restores the
  exact 1.15 margin.
- Offset sign: an aerodynamic center at or aft of the shear center
  (e <= 0) gives a restoring torsion; such a configuration has no
  divergence and the formulas are out of domain.

## Workflow

1. Collect the inputs: torsional stiffness k_theta (N m per rad),
   reference area S, chord c, lift curve slope C_Lalpha per radian, and
   the offset ratio e = (x_AC - x_SC) / c with x_AC the aerodynamic
   center station and x_SC the shear center station.
2. Confirm e > 0: a zero or negative offset means no divergence
   mechanism (aerodynamic center at or aft of the shear center).
3. Compute the divergence dynamic pressure with
   divergence_dynamic_pressure(k_theta, area, chord, cl_alpha,
   offset_ratio).
4. Convert to the divergence speed with divergence_speed(q_div) at the
   sea level density, or pass the flight density for altitude cases.
5. Assess the margin with assess_divergence_margin(v_div, v_design),
   which returns (margin, acceptable) against the 1.15 threshold; a
   margin below 1.15 flags divergence risk.
6. When the surface is flagged, size the required torsional stiffness
   with stiffness_for_margin(v_design, area, chord, cl_alpha,
   offset_ratio) and re-run steps 3 to 5 to confirm the margin closes.
7. Record the divergence dynamic pressure, the divergence speed, and
   the margin verdict in the aeroelastic clearance assessment.

## Pitfalls

- Routing control reversal there: aileron control reversal, where the
  aileron effectiveness vanishes at the reversal dynamic pressure,
  belongs to flight-mechanics/stability-control/aileron-reversal; this
  leaf is the pure torsion divergence condition, not the control
  effectiveness problem.
- Routing dynamic flutter there: coupled bending-torsion oscillation
  and flutter clearance testing belong to the
  flight-test-operations/flutter leaves; divergence is a static
  aeroelastic divergence, not an oscillation.
- Sign of the offset: with the aerodynamic center aft of the shear
  center the torsion is restoring and divergence does not occur;
  forcing the formula gives a negative q_div, which is meaningless.
- Wrong density: V_div depends on the flight density; report the value
  used (sea level 1.225 kg/m^3 is the default, thinner air gives a
  higher speed).
- Treating 1.15 as a regulation: the 1.15 margin is a common design
  practice rule of thumb; the airworthiness aeroelastic requirements
  live in the certification standards (FAR/CS part 25), which this
  leaf references but never reproduces.
- Mixing speeds and pressures: the margin compares speeds at the same
  density, which is equivalent to comparing the dynamic pressures only
  when the density is fixed; convert consistently.
- Units on the stiffness: k_theta must be N m per rad; a stiffness
  expressed per unit span combined with an area that already includes
  the span double-counts the geometry.
- Forgetting the strip convention: in a per-unit-span typical-section
  model set the area S equal to the chord c, so q_div = k_theta /
  (c^2 * C_Lalpha * e).

## Behavior contract (gate 3)

The divergence logic is exercised by the gate 3 contract test:
scripts/test_divergence_speed.py against
scripts/divergence_speed_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_divergence_speed.py

## Compliance

- The typical section divergence analysis is public-domain textbook
  methodology (Bisplinghoff, Ashley and Halfman, Aeroelasticity;
  Hodges and Pierce, Introduction to Structural Dynamics and
  Aeroelasticity); NACA TR 824 is referenced as the pack's
  public-domain anchor for the section lift data, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

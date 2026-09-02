---
name: high-lift-systems
description: "Estimate high-lift system performance for conceptual design: compute the section clmax increment for trailing-edge flaps (plain, split, slotted, Fowler) and leading-edge devices (slat, Krueger), scale the increment with deflection, flap chord ratio, and flapped span fraction, combine flap and slat increments by superposition, apply the three-dimensional and sweep reduction to get wing CLmax, and derive the resulting stall speed. Produces the wing maximum lift coefficient, stall speed, drag increment, and pitching moment increment that size the flap schedule and drive field performance estimates. Use when the task is high-lift device selection, flap clmax estimation, slat contribution, wing CLmax, or stall speed with flaps. Trigger: high-lift, flap, slat, Fowler, Krueger, clmax, stall speed, lift increment."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: aerodynamics
pack: aerodynamics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: high-lift
  tags: [high-lift-systems, trailing-edge-flaps, leading-edge-devices, clmax, stall-speed]
  version: 0.1.0
  author: Aero Agent Skills
---

# High-Lift Systems (aerodynamics/high-lift/high-lift-systems)

Use when the task is high-lift device selection and performance: flap
and slat clmax increments, wing maximum lift coefficient, and the
stall speed that results.

## Domain quick reference

- Trailing-edge flaps raise the section clmax by an increment that
  depends on flap type, deflection, flap chord ratio, and flapped
  span fraction. Reference increments at full deflection and a flap
  chord ratio near 0.25 (widely cited textbook estimates, Raymer
  Aircraft Design: A Conceptual Approach, DATCOM-style scaling):

  Delta clmax = Delta clmax_ref * K_delta * K_chord * K_span
  K_delta = sin(delta) / sin(delta_max), clamped at delta_max
  K_chord = (c_f / c) / (c_f / c)_ref
  K_span = flapped span fraction

- Typical section clmax increments at full deflection (chord ratio
  near 0.25, full span): plain 0.9, split 0.9, slotted 1.3, Fowler
  1.6. A Fowler flap extends the chord, adding extension chord as
  c_f = c_f_base + extension_frac * c.
- Leading-edge devices add a further increment: a full-span slat about
  0.4, a partial-span slat scaled by span fraction, a Krueger flap
  about 0.3.
- Wing-level CLmax applies a three-dimensional and sweep reduction:
  CLmax_wing = 0.9 * clmax_section * cos(Lambda) with the sweep angle
  Lambda in degrees.
- Stall speed: V_stall = sqrt(2 * W / (rho * S * CLmax_wing)), with
  weight W in N, area S in m^2, and rho in kg/m^3.
- Drag increment: Delta CD0 = CD0_ref * sin(delta) / sin(delta_max),
  plus the induced-drag rise Delta CDi = Delta CL^2 / (pi * AR * e).
- Pitching moment increment: Delta Cm = -Delta CL * (x_cp - x_ac)
  with the flap center-of-pressure and the wing aerodynamic center as
  fractions of chord.

## Workflow

1. Select the flap type and the maximum deflection; get the reference
   increment and scaling constants with flap_clmax_increment.
2. For Fowler flaps, extend the chord with fowler_chord_ratio when the
   extension is known.
3. Add leading-edge device increments with slat_clmax_increment and
   combine with combined_clmax_increment (superposition).
4. Convert the section clmax to the wing value with wing_clmax using
   the sweep angle.
5. Compute the stall speed with stall_speed; estimate the drag and
   pitching moment increments with flap_drag_increment and
   flap_pitch_moment_increment.

## Pitfalls

- Mixing section and wing values: the 0.9 factor and the sweep cosine
  reduction apply once, at the wing level, not per device.
- Using full-span reference increments for partial-span flaps: scale
  by the flapped span fraction first.
- Forgetting the deflection clamp: beyond delta_max the increment
  stops growing (K_delta clamps at 1).
- Treating a Krueger flap as a slat: increments differ (about 0.3 vs
  0.4 at full span), and the scaling rules are separate.
- Using stall speed with the clean CLmax: the whole point of the
  high-lift system is the flapped CLmax.

## Behavior contract (gate 3)

The high-lift logic is exercised by the gate 3 contract test:
scripts/test_high_lift_systems.py against
scripts/high_lift_systems_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_high_lift_systems.py

## Compliance

- The flap and slat increment values are widely cited textbook
  estimates (Raymer, Aircraft Design: A Conceptual Approach),
  paraphrased here. FAR-25 and CS-25 are cited as reference only for
  the stall and field performance context; no proprietary or
  copyrighted text is reproduced.
- compliance: STANDARDS-REF, gated: false.

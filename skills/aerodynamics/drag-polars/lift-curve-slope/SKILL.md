---
name: lift-curve-slope
description: "Use when you must estimate the lift curve slope of a wing from section data: compute the thin-airfoil section slope a0 = 2*pi per radian, correct it for finite aspect ratio with the lifting-line formula a = a0 / (1 + a0 / (pi * e * AR)), apply the simple sweep theory cosine correction, apply the Prandtl-Glauert Mach correction a / sqrt(1 - M^2) with a documented M < 0.7 limit, and predict lift coefficient from angle of attack with C_L = a * (alpha - alpha_zero), including an optional stall guard. Produces the corrected wing slope and lift coefficient for a given angle of attack that feed wing sizing and performance estimates. Trigger: lift curve slope, thin-airfoil theory, finite wing correction, aspect ratio, sweep correction, Prandtl-Glauert, lift coefficient."
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
  subdomain: drag-polars
  tags: [lift-curve-slope, thin-airfoil-theory, finite-wing-correction, aspect-ratio, sweep-correction, prandtl-glauert, lift-coefficient, angle-of-attack]
  version: 0.1.0
  author: Aero Agent Skills
---

# Lift Curve Slope Estimation (aerodynamics/drag-polars/lift-curve-slope)

Use when the task is wing lift curve slope estimation from section
data: thin-airfoil theory for the section slope, lifting-line theory
for the finite wing, simple sweep theory, the Prandtl-Glauert Mach
correction, and lift coefficient from angle of attack.

## Domain quick reference

- Section slope: thin-airfoil theory gives a0 = 2 * pi per radian for
  a flat plate or thin uncambered section; use a measured or computed
  value when one is available. Camber shifts the zero-lift angle, it
  does not change the thin-airfoil slope.
- Finite wing (lifting-line theory, span efficiency e):
  a = a0 / (1 + a0 / (pi * e * AR)). With a0 = 2 * pi and e = 1
  (elliptic loading) this reduces to a = a0 * AR / (AR + 2).
- Sweep (simple sweep theory): a_swept = a * cos(sweep), sweep in
  degrees, documented range 0 <= sweep < 90 where cos(sweep) > 0.
- Mach (Prandtl-Glauert): a_mach = a / sqrt(1 - M^2), documented
  range 0 <= M < 0.7. The correction is a subsonic small-disturbance
  result and becomes invalid as transonic effects appear above 0.7.
- Combined order: section slope, then finite wing, then sweep, then
  Mach. Each step consumes the slope produced by the previous step.
- Lift coefficient: C_L = a * (alpha - alpha_zero), alpha and
  alpha_zero in degrees, a per radian. The optional stall guard flags
  angles whose linear prediction exceeds the stall limit.
- Validation anchor: NACA Report 824 (public domain) supplies section
  lift data; the thin-airfoil slope 2 * pi is the theoretical limit
  that measured thin sections approach.

## Workflow

1. Choose the section slope with airfoil_slope(a0), or the default
   thin-airfoil value 2 * pi.
2. Correct for the finite wing with finite_wing_slope(a0, ar, e).
3. Apply the sweep correction with sweep_correction(a, sweep_deg).
4. Apply the Mach correction with mach_correction(a, mach).
5. Or chain all three corrections in one call:
   wing_lift_curve_slope(ar, a0, sweep_deg, mach, e).
6. Predict the lift coefficient at the operating angle with
   lift_coefficient(a, alpha_deg, alpha_zero_deg, stall_cl).

## Pitfalls

- Using the section slope as the wing slope: a finite aspect ratio
  always reduces the slope below 2 * pi.
- Accepting sweep at or beyond 90 degrees where cos(sweep) <= 0.
- Accepting Mach at or above 0.7 where Prandtl-Glauert breaks down.
- Mixing degrees and radians: a is per radian, alpha is in degrees.
- Ignoring alpha_zero for cambered sections: C_L = 0 at the
  zero-lift angle, not at alpha = 0.
- Reordering the correction chain when the intermediate values are
  reported for design use.

## Behavior contract (gate 3)

The slope and lift coefficient logic is exercised by the gate 3
contract test: scripts/test_lift_curve.py against
scripts/lift_curve_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_lift_curve.py

## Compliance

- NACA Report 824 is US government work (public domain); summary and
  physics values only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

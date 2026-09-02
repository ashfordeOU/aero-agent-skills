---
name: stability-derivatives-avl
description: "Use when you must estimate the aerodynamic stability derivatives of an aircraft from its geometry in AVL style: estimate the wing and tail lift curve slopes from the planform aspect ratio, the quarter-chord sweep, and the Mach number; estimate Cm_alpha from the tail volume coefficient and the downwash gradient; estimate the lateral-directional derivatives Cn_beta, Cl_beta, Cl_p, Cl_r, Cn_p, and Cn_r from the vertical tail geometry, the wing dihedral, and the sweep contribution; and derive the neutral point and the static margin from the longitudinal estimates. Produces the non-dimensional derivative table that feeds the longitudinal and dynamic stability leaves. Trigger: stability derivatives, lift curve slope, wing planform, aspect ratio, quarter chord sweep, Mach correction, Cn beta, neutral point, static margin, AVL."
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
  tags: [stability-derivatives, lift-curve-slope, wing-planform, aspect-ratio, sweep-effect, mach-correction, tail-volume, neutral-point, static-margin, avl-style]
  version: 0.1.0
  author: Aero Agent Skills
---

# Stability Derivative Estimation (flight-mechanics/stability-control/stability-derivatives-avl)

Use when the task is estimating the aerodynamic stability derivatives
of an aircraft from its geometry, in the style of vortex-lattice (AVL)
and DATCOM-type preliminary methods: wing and tail lift curve slopes,
pitch stiffness, directional and roll stability derivatives, and the
neutral point with the static margin.

This leaf ESTIMATES the derivatives from geometry. It is different
from longitudinal-stability (which computes the neutral point from
given coefficients) and from dynamic-stability (which classifies modes
from given derivatives): start here when the input is the wing and
tail planform, then hand the derivative table to those leaves.

## Domain quick reference

Conventions: stability axes, x forward, y out the right wing, z down.
All angles in radians, all lengths in meters, all areas in square
meters. Every derivative below is non-dimensional, per radian of the
relevant motion variable, unless stated otherwise. The roll and yaw
rate variables are the non-dimensional rates pb/2V and rb/2V.

- Wing lift curve slope, per radian (subsonic planform estimate, valid
  for Mach below 0.9):

      CL_alpha = 2*pi*A / (2 + sqrt( (A*beta/k)^2 * (1 + tan^2(Lambda)/
                 beta^2) + 4 ))

  with A the aspect ratio (dimensionless), Lambda the quarter-chord
  sweep in radians, beta = sqrt(1 - M^2) the compressibility factor
  (dimensionless), and k = a0 / (2*pi) the section slope ratio, where
  a0 is the airfoil section lift slope, 2*pi per radian by default.
  The tail lift curve slope uses the same formula with the tail
  surface aspect ratio and sweep.

- Downwash gradient at the tail, dimensionless (elliptical-loading
  estimate):

      depsilon/dalpha = 2 * CL_alpha_w / (pi * A)

- Horizontal tail volume coefficient, dimensionless (tail arm l_t in
  m, tail area S_t in m^2, mean aerodynamic chord c_bar in m, wing
  area S_w in m^2):

      V_h = l_t * S_t / (c_bar * S_w)

- Vertical tail volume coefficient, dimensionless (vertical tail arm
  l_v in m, vertical tail area S_v in m^2, span b in m):

      V_v = l_v * S_v / (b * S_w)

- Pitch stiffness Cm_alpha, per radian, referenced to the center of
  gravity h_cg (positions are fractions of the mean aerodynamic
  chord):

      Cm_alpha = a_w * (h_cg - h_ac_w) - V_h * a_t * (1 - depsilon/dalpha)

  with h_ac_w the wing aerodynamic center and a_w, a_t the wing and
  tail lift slopes. Negative Cm_alpha means pitch stable.

- Neutral point, fraction of mean aerodynamic chord:

      h_np = h_ac_w + V_h * (a_t / a_w) * (1 - depsilon/dalpha)

- Static margin = h_np - h_cg, dimensionless; positive means a stable
  configuration.

- Directional stability Cn_beta, per radian: the vertical tail
  contribution is stabilizing (positive weathercock term), the
  wing-body sweep contribution is destabilizing (negative):

      Cn_beta = V_v * a_t * (1 + sigma) - (C_L^2 / (pi * A)) * tan(Lambda)

  with sigma the sidewash factor (0.72 common preliminary value,
  dimensionless) and C_L the cruise lift coefficient.

- Dihedral contribution to roll stability Cl_beta, per radian:

      Cl_beta = -(a_w / 2) * Gamma

  with Gamma the wing dihedral angle in radians. Negative means
  stabilizing in sideslip.

- Roll damping Cl_p and yaw damping Cn_r, per radian of pb/2V and
  rb/2V (lambda is the taper ratio, dimensionless, in (0, 1]):

      Cl_p = -(a_w / 12) * (1 + 3*lambda) / (1 + lambda)
      Cn_r = -2 * V_v * a_t * (l_v / b)

- Cross derivatives Cl_r and Cn_p, per radian (wing estimates):

      Cl_r = (C_L / 4) * (1 + 3*lambda) / (1 + lambda)
      Cn_p = -C_L / 8

## Workflow

1. Collect the wing planform: aspect ratio, quarter-chord sweep
   (degrees in, converted to radians inside), taper ratio, airfoil
   section slope, and the Mach number and cruise lift coefficient.
2. Estimate the wing and tail lift curve slopes with cl_alpha_wing and
   cl_alpha_tail, then the downwash gradient with downwash_gradient.
3. Build the tail volume coefficients with tail_volume_coeff and
   vertical_tail_volume_coeff from the tail arms, areas, mean chord,
   span, and wing area.
4. Estimate Cm_alpha with cm_alpha; derive the neutral point with
   neutral_point and the static margin with static_margin.
5. Estimate the lateral-directional derivatives with cn_beta,
   cl_beta, cl_p, cl_r, cn_p, and cn_r from the vertical tail, the
   dihedral, and the sweep.
6. Assemble the full non-dimensional table with estimate_derivative_table
   and read the verdicts: pitch_stable, directionally_stable, and
   statically_stable.
7. Hand the derivative table to the longitudinal-stability and
   dynamic-stability leaves for the neutral-point check and the mode
   classification.

## Pitfalls

- Mixing units: the formulas take sweep and dihedral in degrees and
  convert internally, but lengths and areas must be SI (meters, square
  meters); feeding feet or inches misstates every result.
- Mach limit: the subsonic planform formula is valid for M below 0.9;
  feeding transonic or supersonic Mach numbers raises ValueError
  instead of returning a misleading slope.
- Reversing the Cm_alpha sign: negative Cm_alpha is pitch stable,
  positive is unstable; the same sign rule applies to Cl_p and Cn_r
  (negative is damping) and to Cn_beta (positive is weathercock
  stable).
- Confusing the neutral point with the wing aerodynamic center: the
  neutral point includes the tail contribution, the wing aerodynamic
  center alone does not.
- Downwash gradient at or above 1.0: physically invalid for this
  model and rejected.
- Treating the estimates as final values: these are preliminary
  design approximations; validate the final configuration with
  higher-fidelity tools.
- Zero vertical tail volume: a configuration with no vertical tail
  cannot be directionally stable under this model; the wing-body
  contribution is destabilizing.

## Behavior contract (gate 3)

The derivative estimation logic is exercised by the gate 3 contract
test: scripts/test_stability_derivatives_avl.py against
scripts/stability_derivatives_avl_logic.py (stdlib unittest, offline).
Run:

python3 scripts/test_stability_derivatives_avl.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 require
  positive static longitudinal stability and adequate directional
  stability for transport aeroplanes; the derivative estimation
  formulas are common flight mechanics methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

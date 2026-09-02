---
name: boundary-layer-theory
description: "Compute laminar and turbulent boundary-layer thicknesses for a smooth flat plate: estimate the 99-percent thickness, displacement thickness, and momentum thickness from the local Reynolds number with the Blasius and 1/7 power-law correlations, evaluate the local and average skin-friction coefficients, and classify the flow into laminar or turbulent regimes by the transition Reynolds number. Use when the task is boundary-layer thickness estimation, displacement or momentum thickness, skin-friction coefficient on a surface, Reynolds-number regime classification, or transition location on a smooth surface. Trigger: boundary layer, displacement thickness, momentum thickness, skin friction, transition, Reynolds number, Blasius."
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
  subdomain: boundary-layer
  tags: [boundary-layer, displacement-thickness, momentum-thickness, skin-friction, transition]
  version: 0.1.0
  author: Aero Agent Skills
---

# Boundary Layer Theory (aerodynamics/boundary-layer/boundary-layer-theory)

Use when the task is flat-plate boundary-layer estimation: thickness,
displacement and momentum thickness, skin friction, and the laminar to
turbulent transition.

## Domain quick reference

- The boundary layer is the thin viscous region next to a surface
  where the velocity rises from zero at the wall (no-slip) to the edge
  value U_e. The local Reynolds number Re_x = rho * U * x / mu =
  U * x / nu sets the flow regime at station x.
- Laminar flat plate (Blasius similarity solution, 1908): 99-percent
  thickness delta = 5.0 * x / sqrt(Re_x), displacement thickness
  delta* = 1.7208 * x / sqrt(Re_x), momentum thickness
  theta = 0.664 * x / sqrt(Re_x), shape factor H = delta* / theta =
  2.5916, local skin friction Cf = 0.664 / sqrt(Re_x), average Cf over
  one side = 1.328 / sqrt(Re_x).
- Turbulent flat plate (1/7 power law, Re_x up to about 1e7):
  delta = 0.37 * x / Re_x^(1/5), delta* = delta / 8,
  theta = 7 * delta / 72, H = 9 / 7 = 1.286,
  local Cf = 0.0592 / Re_x^(1/5), average Cf = 0.074 / Re_x^(1/5).
  Above about 1e7 prefer the fully turbulent log-law correlation
  Cf = 0.455 / (log10 Re_x)^2.58.
- Displacement thickness delta* = integral_0^inf (1 - u / U_e) dy is
  the mass deficit of the layer; the outer flow behaves as if the body
  were thickened by delta*. Momentum thickness theta =
  integral_0^inf (u / U_e) * (1 - u / U_e) dy is the momentum deficit.
- The von Karman momentum integral d(theta)/dx + (H + 2) *
  (theta / U_e) * dU_e/dx = Cf / 2 relates the thickness growth to the
  edge velocity gradient for pressure-gradient layers.
- Transition: the laminar layer destabilizes through Tollmien-
  Schlichting waves. On a smooth flat plate with low free-stream
  turbulence the transition Reynolds number is near Re_x = 5e5; values
  range from about 3e5 (rough surface, high turbulence) to 3e6 (very
  quiet flow). Favorable pressure gradients delay transition, adverse
  gradients advance it.
- Reynolds-number regimes (flat plate): laminar below the transition
  Reynolds number, turbulent above; a fully laminar boundary layer
  over a whole chord is rare at flight Reynolds numbers (typically 1e6
  to 1e8).

## Workflow

1. Establish the condition: speed U, density rho, dynamic viscosity mu,
   and the station x (or chord position).
2. Compute Re_x with reynolds_number; use kinematic_viscosity when
   only nu = mu / rho is available.
3. Pick the regime with classify_regime (default transition at
   Re_x = 5e5) and use the laminar or turbulent functions.
4. Estimate delta, delta*, theta with the Blasius or 1/7 power-law
   thickness functions; form the shape factor with shape_factor.
5. Evaluate local and average skin friction with the cf functions;
   switch to cf_turbulent_log_law above Re_x ~ 1e7.
6. State the transition assumption explicitly; recheck when the
   surface is rough or the free-stream turbulence is high.

## Pitfalls

- Using the Blasius laminar values beyond transition: the turbulent
  layer is several times thicker and draggier at the same Re_x.
- Quoting delta where delta* was meant: the displacement thickness is
  about one third of delta for laminar flow and one eighth for
  turbulent flow.
- Mixing the local Cf with the average (total-drag) Cf: the laminar
  pair differs by a factor of two (0.664 vs 1.328), the turbulent pair
  by about 25 percent (0.0592 vs 0.074).
- Using the freestream speed where the edge velocity U_e differs
  (wing suction side, curved bodies): the correlations then misstate
  the thicknesses.
- Treating the transition point as fixed: roughness, free-stream
  turbulence, and pressure gradient move it by orders of magnitude.
- Applying the 1/7 power law near the wall or at very high Re_x: the
  profile has an infinite wall gradient; use the log-law correlation
  for friction above Re_x ~ 1e7.
- Forgetting the two-sided factor when converting skin friction to
  total surface drag: delta and Cf are per side.
- Mixing the length scale: the delta correlations are keyed to the
  local Re_x at station x, not a global chord Reynolds number.

## Behavior contract (gate 3)

The boundary-layer logic is exercised by the gate 3 contract test:
scripts/test_boundary_layer_theory.py against
scripts/boundary_layer_theory_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_boundary_layer_theory.py

## Compliance

- The Blasius solution and the 1/7 power-law and log-law correlations
  are classical physics results (public-domain knowledge), paraphrased
  here. NACA Report 824 is cited as reference only for the
  aerodynamics validation context; no proprietary or copyrighted text
  is reproduced.
- compliance: STANDARDS-REF, gated: false.

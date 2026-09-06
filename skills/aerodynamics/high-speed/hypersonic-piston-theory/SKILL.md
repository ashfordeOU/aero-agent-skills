---
name: hypersonic-piston-theory
description: "Use when you must estimate the surface pressure on a small-perturbation hypersonic surface by Lighthill piston theory: evaluate the piston-theory pressure ratio p/p_inf = (1 + ((gamma - 1)/2) v/a_inf)^(2 gamma/(gamma - 1)) from the piston velocity ratio, apply the linearized limit p/p_inf = 1 + gamma v/a_inf for a small piston velocity, split the compression side from the expansion side of the inclined surface, compute the surface-pressure coefficient Cp = 2/(gamma M^2) (p/p_inf - 1) from the freestream Mach and inclination on either side, and extend the same law to an unsteady surface whose normal motion adds to the geometric piston velocity. Produces the piston-theory surface-pressure ratios, the linearized limits and the per-side and instantaneous pressure coefficients that gate hypersonic panel pressure, stability derivative and oscillating-surface load estimates. Trigger: piston theory, hypersonic piston analogy, small perturbation hypersonic surface pressure, Lighthill."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: high-speed
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags: [hypersonic-piston-theory, lighthill-piston-analogy, small-perturbation-hypersonic, piston-theory-pressure-ratio, unsteady-hypersonic-surface-pressure]
  version: 0.1.0
  author: AeroSkills
---

# Lighthill Piston Theory Surface Pressure (aerodynamics/high-speed/hypersonic-piston-theory)

Use when the task is the surface pressure on a small-perturbation
hypersonic surface by Lighthill piston theory (the Lighthill 1953
piston analogy in the Ashley-Zartarian hypersonic small-perturbation
class): a surface element moving into the gas compresses it like a
piston pushing down a tube, so the local pressure ratio follows the
closed form p/p_inf = (1 + ((gamma - 1)/2) * (v/a_inf))^(2 gamma/(gamma
- 1)) from the local piston velocity ratio v/a_inf, positive for a
compression (shock-side) motion and negative for an expansion, with the
law collapsing to p/p_inf = 0 at the expansion cutoff v/a_inf =
-2/(gamma - 1). This leaf evaluates that law, its linearized limit
p/p_inf = 1 + gamma * v/a_inf, the piston velocity ratio of a steady
surface inclined theta to the freestream (v/a_inf = M * sin(theta)),
the per-side surface-pressure coefficient Cp = 2/(gamma M^2) *
(p/p_inf - 1) with the linearized hypersonic limit Cp = 2 * sin(theta)/M,
and the extension to an unsteady surface whose normal wall motion adds
to the geometric piston velocity for the instantaneous pressure at any
phase of its motion. Pure Python, stdlib only, deterministic. It is the
unsteady complement to the steady blunt-body impact theory of
aerodynamics/high-speed/hypersonic-flow: the same hypersonic
surface-pressure physics built from the local piston velocity rather
than from steady impact integrals.

## Domain quick reference

- Piston law: p/p_inf = (1 + ((gamma - 1)/2) * (v/a_inf))^(2 gamma/(gamma
  - 1)), equal to 1.0 at v/a_inf = 0, strictly increasing in the piston
  velocity ratio, above 1 on the compression side and between 1 and 0 on
  the expansion side down to the cutoff. The exponent 2 gamma/(gamma -
  1) is 7 at gamma 1.4 and the cutoff -2/(gamma - 1) is -5, where the
  base (1 + ((gamma - 1)/2) * v/a_inf) reaches exactly zero and the
  pressure ratio is exactly 0.0 (vacuum).
- Linearized limit: p_lin/p_inf = 1 + gamma * (v/a_inf), the first-order
  expansion of the piston law and the regime of small M*sin(theta).
- Piston velocity ratio of a steady surface: v/a_inf = M * sin(theta),
  the freestream normal component U*sin(theta) divided by a_inf = U/M.
- Surface-pressure coefficient: Cp = 2/(gamma M^2) * (p/p_inf - 1),
  evaluated per side with the side's own pressure ratio; from the
  linearized ratio gamma cancels and Cp_lin = 2 * sin(theta)/M, the
  Mach-independent hypersonic linear coefficient.
- Unsteady composition: the instantaneous piston velocity ratio of a
  moving surface is the steady geometric term M*sin(theta) plus the
  wall normal velocity ratio w/a_inf, added for inward (compression)
  wall motion and subtracted for retreat; the instantaneous pressure
  follows from the composed ratio through the same closed form, no time
  integration.
- Scope: perfect-gas small-perturbation hypersonic surfaces at Mach
  above 1 (hypersonic usage sits well above 5, but the closed form only
  guards Mach > 1), inclination theta in degrees over [0, 90), piston
  velocity ratios above the expansion cutoff -2/(gamma - 1), gamma =
  1.4 air by default and a parameter elsewhere.
- NACA TR-824 frames the classic compressible-flow data context; the
  piston analogy itself is the Lighthill 1953 result in the
  Ashley-Zartarian small-perturbation class, summary-only here.

## Workflow

1. Fix the operating point: freestream Mach M (must exceed 1),
   surface inclination theta in degrees over [0, 90) and the gas gamma
   (must exceed 1), the guards every function shares.
2. Traverse the piston velocity ratio of the steady inclined surface
   with piston_velocity_ratio(M, theta_deg) = M * sin(theta).
3. Evaluate the piston-theory pressure ratio from the piston velocity
   ratio with piston_pressure_ratio(v_a, gamma): the closed form above,
   returning 0.0 at the expansion cutoff and raising ValueError below
   it (fully expanded flow).
4. Apply the linearized limit with linear_pressure_ratio(v_a, gamma) =
   1 + gamma * v_a when the piston velocity ratio is small; past a
   ratio of about 0.5 the exact law is required.
5. Split the compression side from the expansion side of the inclined
   surface with surface_pressure_ratio(M, theta_deg, side, gamma),
   which carries v/a_inf = +M*sin(theta) on the compression side and
   -M*sin(theta) on the expansion side.
6. Compute the per-side surface-pressure coefficient with
   surface_pressure_coefficient(M, theta_deg, side, gamma) and
   cross-check the linearized limit with linear_cp(M, theta_deg) =
   2 * sin(theta)/M.
7. For an unsteady surface, compose the instantaneous piston velocity
   ratio with unsteady_piston_ratio(M, theta_deg, wall_v_a, direction)
   (geometric term plus direction * abs(wall_v_a), +1 for wall motion
   into the gas, -1 for retreat) and evaluate the instantaneous
   pressure ratio with unsteady_pressure_ratio(M, theta_deg, wall_v_a,
   direction, gamma) at the phase of the motion of interest.
8. Confirm the deterministic checks with the contract test
   scripts/test_hypersonic_piston_theory.py.

## Worked example

Two steady surfaces and one unsteady surface, gamma 1.4 (real module
outputs, spec anchors):

- Raw law: piston_pressure_ratio(0.5) = 1.948717100000 and
  piston_pressure_ratio(-0.5) = 0.478296900000; at +1.5 the ratio
  6.274851700000 runs far above the linearized 3.100000000000
  (residual 3.174851700000), so the exponent-7 law is nonlinear once
  the piston ratio is not small. At v/a = -5.0 the base vanishes and
  the law returns exactly 0.000000000000 (vacuum); below the cutoff it
  raises ValueError.
- Linearized limit: at v/a = +-0.02 the exact ratios are 1.028338248982
  and 0.972333768939 against linearized 1.028000000000 and
  0.972000000000, relative errors 0.000328927745 and 0.000343265810, so
  the linear limit is the small-M*sin(theta) regime.
- Steady surface A, M = 6, theta = 5 deg: piston_velocity_ratio =
  0.522934456486 (moderate); compression side p/p_inf =
  2.006315343379 with Cp = 0.039933148547; expansion side p/p_inf =
  0.461491957246 with Cp = -0.021369366776; the linearized coefficient
  linear_cp = 0.029051914249 equals the Cp rebuilt from the linearized
  pressure ratio to float zero (residual 0.000000000000). The exact
  compression Cp is 37 percent above the linearized value, so at
  M*sin(theta) = 0.52 the linear limit underestimates the load.
- Steady surface B, M = 8, theta = 10 deg: piston_velocity_ratio =
  1.389185421335 (order 1); compression side p/p_inf = 5.563247915155
  with Cp = 0.101858212392; expansion side p/p_inf = 0.102434506727
  with Cp = -0.020034944046, a compression-to-expansion ratio near
  54.3; linear_cp = 0.043412044417 is less than half the exact
  compression coefficient and the product p_c * p_e = 0.569868555988
  shows the exponent-7 law is far from reciprocal at this loading.
- Unsteady surface, M = 6, theta = 5 deg, wall normal velocity ratio
  amplitude 0.10 (an oscillating panel whose normal speed peaks at one
  tenth of the local sound speed): geometric steady piston ratio
  0.522934456486, inward peak 0.622934456486, retreat peak
  0.422934456486; pressures steady 2.006315343379, inward
  2.274841372010, retreat 1.765429818550; pressure coefficients steady
  0.039933148547, inward 0.050588943334, retreat 0.030374199149. The
  motion swings the surface pressure by 0.253904031159 of the steady
  p/p_inf, a quarter-wave load cycle about the steady compression state,
  the unsteady content the steady blunt-body leaf cannot produce.

## Verification

- Confirm piston_pressure_ratio(0.5) = 1.948717100000 and that the law
  table at gamma 1.4 matches the spec anchors within 1e-5, strictly
  increasing across both sides of the sweep.
- Confirm the cutoff: piston_pressure_ratio(-5.0) = 0.000000000000
  within 1e-12 and piston_pressure_ratio(-5.5) raises ValueError
  (fully expanded flow).
- Confirm the linearized limit matches 1 + gamma * v/a at every sample
  and that its relative error against the exact law at v/a = +-0.02 is
  0.000328927745 / 0.000343265810 within 1e-5.
- Confirm surface A (M 6, theta 5 deg): compression p/p_inf =
  2.006315343379, Cp = 0.039933148547; expansion p/p_inf =
  0.461491957246, Cp = -0.021369366776; linear_cp = 0.029051914249; the
  Cp rebuilt from the linearized ratio equals linear_cp to float zero.
- Confirm surface B (M 8, theta 10 deg): compression 5.563247915155,
  expansion 0.102434506727, linear_cp = 0.043412044417, product p_c *
  p_e = 0.569868555988 (not 1).
- Confirm the unsteady surface: inward/retreat piston ratios
  0.622934456486 / 0.422934456486 and pressures 2.274841372010 /
  1.765429818550 with swing 0.253904031159 of the steady ratio.
- Confirm gamma is honored (piston_pressure_ratio(0.5, gamma = 1.3) =
  1.871572650534) and that gamma at or below 1, Mach at or below 1,
  theta outside [0, 90), piston ratios below the cutoff, and side or
  direction values outside the allowed names all raise ValueError.
- Run the contract test offline: python3
  scripts/test_hypersonic_piston_theory.py (35 tests, deterministic).

## Related leaves

- aerodynamics/high-speed/hypersonic-flow: the steady blunt-body
  impact-theory sibling; steady stagnation, blunt-body and sphere drag
  integrals and the vacuum limit on shadowed surfaces stay with it,
  while this leaf carries the unsteady piston law.
- aerodynamics/high-speed/oblique-shock and prandtl-meyer: steady
  shock-polar turning methods, no piston velocity ratio.
- aerodynamics/high-speed/shock-expansion-airfoil: steady supersonic
  airfoil patches, the M^2 - 1 supersonic neighbor of the hypersonic
  piston law.
- aerodynamics/aeroelasticity/flutter-speed-prediction: the subsonic
  oscillatory C(k) lift-deficiency leaf, the inverse regime (no
  hypersonic Mach content, no compression-expansion pressure law).
- aerodynamics/aeroelasticity/added-mass-coefficients-potential-flow:
  incompressible apparent-mass coefficients, no compressible pressure
  law.

## Pitfalls

- Using the linearized limit where the piston ratio is not small: at
  v/a = 0.5 the exact ratio 1.948717100000 already sits 14.6 percent
  above the linearized 1.700000000000, and at M*sin(theta) of order 1
  (surface B) the linear coefficient 0.043412044417 is less than half
  the exact compression Cp; apply the exact law once the ratio is not
  small.
- Expecting the law to be reciprocal: the exponent 2 gamma/(gamma - 1)
  is not antisymmetric under a sign flip, so p_c * p_e = 0.569868555988
  at M 8, theta 10 deg, never 1; read each side from its own pressure
  ratio.
- Pushing an expansion below the cutoff: v/a_inf = -2/(gamma - 1) is the
  vacuum state (exactly 0.0); below it the flow is fully expanded and
  the function raises ValueError, so a steep expansion side of a high
  Mach surface can raise through surface_pressure_ratio as well.
- Confusing this leaf with steady blunt-body impact theory: this law is
  built from the local piston velocity ratio, not from steady
  stagnation integrals over spheres, cones or plates (hypersonic-flow
  owns those), and it carries no C(k) circulation-lag or
  reduced-frequency machinery (flutter-speed-prediction owns that).
- Mixing the wall-motion direction: direction +1 adds abs(wall_v_a) to
  the geometric piston velocity (inward, compression) and -1 subtracts
  it (retreat); the sign of wall_v_a itself is ignored, so pass the
  amplitude and the direction separately.
- Forgetting the Mach guard is only M > 1: the closed form is a pure
  gas-dynamic law valid above Mach 1, but hypersonic usage of piston
  theory sits at Mach well above 5, so read the result in that regime.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_hypersonic_piston_theory.py

The 35 tests cover the piston-theory pressure ratio across the law
table and the expansion cutoff, the linearized limit and its relative
error at small piston velocity ratios, the piston velocity ratio
M*sin(theta) of the steady surfaces, the per-side pressure ratios and
pressure coefficients of surfaces A and B, the linearized Cp identity
and gamma independence, the gamma-1.3 anchors, the unsteady
composition at the inward and retreat phases with the quarter-wave
swing, and ValueError rejection of gamma at or below 1, Mach at or
below 1, theta outside [0, 90), ratios below the cutoff and invalid
side and direction names. Two identical runs return identical bits and
the logic imports only the stdlib math module.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is the classic
  compressible-flow data source (public domain); the piston analogy is
  the Lighthill 1953 result summarized as standard engineering
  methodology per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

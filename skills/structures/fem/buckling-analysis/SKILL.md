---
name: buckling-analysis
description: "Use when a column, strut, spar cap, landing-gear leg or actuator rod must be sized or margin-checked against elastic instability in a stdlib-only environment without FEA software. Calculate the Euler critical buckling load of slender compression members: apply Pcr = pi^2*E*I/(K*L)^2 for pinned-pinned, fixed-fixed, fixed-pinned and cantilever end conditions, resolve the effective length factor K from the support type, compute the slenderness ratio from the radius of gyration, and run the buckling stress check against the yield-based transition slenderness. Units are SI. Trigger: euler buckling, critical buckling load, slenderness ratio, effective length factor, column buckling, buckling stress, end conditions, radius of gyration, cantilever."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [euler-buckling, critical-buckling-load, slenderness-ratio, effective-length-factor, end-conditions, buckling-stress, radius-of-gyration, cantilever-column, pinned-pinned, fixed-fixed]
  version: 0.1.0
  author: Aero Agent Skills
---

# Buckling Analysis (structures/fem/buckling-analysis)

Use when the task is the elastic instability of a slender axially
loaded member: computing the Euler critical buckling load Pcr =
pi^2 * E * I / (K * L)^2 for the common end conditions (pinned at
both ends, fixed at both ends, one end fixed and one pinned, and the
fixed-free cantilever), resolving the effective length factor K,
deriving the slenderness ratio from the radius of gyration, and
running the buckling stress check against the yield-based transition
slenderness so the column is rated as slender (Euler governs) or
stubby (yield governs). The logic module is pure Python standard
library (no numpy, no FEA software) and deterministic. Units are SI:
E in Pa, I in m^4, A in m^2, L in m, forces in N, stresses in Pa.

## Domain quick reference

- Euler critical buckling load of an ideal slender column:

      Pcr = pi^2 * E * I / (K * L)^2

  where E is Young's modulus, I the second moment of area about the
  buckling axis, L the actual member length and K the effective
  length factor from the end conditions.

- Effective length factor K and effective length Le = K * L:

  | End conditions | K | Le for L = 3 m |
  |---|---|---|
  | pinned-pinned (both ends pinned) | 1.0 | 3.0 m |
  | fixed-fixed (both ends fixed) | 0.5 | 1.5 m |
  | fixed-pinned (one end fixed, one pinned) | 0.7 | 2.1 m |
  | fixed-free (cantilever, one end fixed) | 2.0 | 6.0 m |

- Radius of gyration r = sqrt(I / A); effective slenderness ratio
  lambda = K * L / r.

- Euler buckling stress (same physics, stress form):

      sigma_cr = Pcr / A = pi^2 * E / lambda^2

- Transition slenderness, where the Euler stress crosses the yield
  strength:

      lambda_1 = pi * sqrt(E / sigma_y)

  If lambda > lambda_1 the column is slender and Euler governs; if
  lambda < lambda_1 the material yields first and Euler overpredicts
  the capacity (Johnson or test-data range).

- Margin of safety against an applied limit load P:

      MS = Pcr / P - 1

Worked anchor (verified by running scripts/buckling_analysis_logic.py):
the steel column with E = 200 GPa, I = 1e-6 m^4 and L = 3 m gives

    pinned-pinned (K = 1):   Pcr = 219.3 kN
    fixed-fixed (K = 0.5):   Pcr = 877.3 kN
    fixed-pinned (K = 0.7):  Pcr = 447.6 kN
    cantilever (K = 2):      Pcr = 54.8 kN

The K factor enters squared: the cantilever buckles at one quarter
of the pinned-pinned load and the fixed-fixed column at four times
it. With A = 1e-3 m^2 the same pinned column has r = 0.0316 m,
lambda = 94.9 and sigma_cr = 219.3 MPa; against sigma_y = 250 MPa
the transition slenderness is 88.9, so this column is slender and
Euler governs, and against an applied load of 100 kN the margin of
safety is 1.19.

Second worked anchor (verified by running the logic): a solid
circular steel column of diameter d = 0.1 m and L = 3 m, pinned at
both ends, has I = pi*d^4/64 = 4.909e-6 m^4, A = pi*d^2/4 =
7.854e-3 m^2, r = d/4 = 0.025 m, lambda = 120, Pcr = 1.077 MN and
sigma_cr = 137.1 MPa, all reproduced by the module.

## Workflow

1. Identify the end conditions of the member and resolve K with
   effective_length_factor("pinned-pinned") = 1.0,
   ("fixed-fixed") = 0.5, ("fixed-pinned") = 0.7,
   ("cantilever" or "fixed-free") = 2.0. Aliases accepted: pinned,
   hinged, fixed, clamped, cantilever.
2. Gather the section properties: E in Pa, I in m^4 about the
   buckling (weak) axis, A in m^2, and the member length L in m.
   For a solid circular section of diameter d, I = pi*d^4/64 and
   A = pi*d^2/4; for a rectangle b x h with b < h, the weak-axis
   I = h*b^3/12 governs.
3. Compute the radius of gyration r = sqrt(I / A) with
   radius_of_gyration(I, A).
4. Compute the effective length Le = K * L and the slenderness
   ratio lambda = K * L / r with slenderness_ratio(L, K, r).
5. Compute the critical buckling load Pcr = pi^2 * E * I / (K * L)^2
   with critical_buckling_load(E, I, L, K).
6. Compute the buckling stress sigma_cr = Pcr / A with
   buckling_stress(E, I, A, L, K) or euler_stress(E, lambda); both
   must agree.
7. Classify the column: compute lambda_1 = pi * sqrt(E / sigma_y)
   with transition_slenderness(E, yield_strength). If lambda >
   lambda_1, Euler governs and Pcr is the capacity; if not, Euler is
   unconservative, so fall back to a Johnson parabola or test data.
8. Run the complete check in one call with column_check(E, I, A, L,
   end_condition, applied_load, yield_strength), which returns the
   critical load, slenderness, transition slenderness, the
   euler_governs verdict and the margin of safety Pcr / P - 1.
   Apply the required factor of safety from the certification basis
   (1.5 ultimate-to-limit per FAR-25.303 / CS-25.303) before
   comparing Pcr against the applied load.

## Pitfalls

- Confusing buckling-analysis with fem/truss-analysis:
  truss-analysis solves pin-jointed bar models with element
  stiffness matrices, global assembly and Gaussian elimination;
  buckling-analysis is a closed-form elastic-instability eigenvalue
  check of a single member and never builds a stiffness matrix.
- Confusing buckling-analysis with fem/calculix-linear:
  calculix-linear drives full continuum FEA in CalculiX (ccx) with
  element-basis stress checks and margins of safety; buckling-analysis
  is a hand-scale closed-form column check with no FEA software.
- Confusing buckling-analysis with fem/modal-analysis:
  modal-analysis computes natural frequencies and mode shapes of
  mass-spring systems (an eigenvalue problem in time); the buckling
  eigenvalue is spatial, the load at which the straight equilibrium
  becomes unstable, and there are no masses and no frequencies here.
- Using the wrong effective length factor: a cantilever is K = 2,
  not K = 1; a fixed-pinned column is K = 0.7; a fixed-fixed column
  is K = 0.5. Because K enters squared, using K = 1 for a cantilever
  overstates Pcr by a factor of four.
- Applying Euler below the transition slenderness: for stubby
  columns (lambda < pi * sqrt(E / sigma_y)) the Euler stress exceeds
  the yield strength, so the ideal-column formula overpredicts;
  always classify with transition_slenderness first.
- Using the wrong second moment of area: a column buckles about its
  weakest axis, so use I_min of the section, not the I about the
  plane in which you expect bending; for a rectangle b x h with
  b < h the governing I is h*b^3/12.
- Mixing units: E in GPa with I in m^4 or L in mm silently corrupts
  Pcr by factors of 1e9 or 1e6; keep everything SI (Pa, m^4, m^2, m,
  N).
- Forgetting the factor of safety and the ideal-column assumptions:
  Pcr is a limit-load instability, so compare P against Pcr divided
  by the required factor of safety (1.5 per FAR-25.303 / CS-25.303),
  and remember Euler assumes a perfectly straight, concentrically
  loaded column; initial imperfection and load eccentricity reduce
  the real capacity below Pcr.

## Behavior contract (gate 3)

The buckling logic is exercised by the gate 3 contract test:
scripts/test_buckling_analysis.py against
scripts/buckling_analysis_logic.py (stdlib unittest, offline). It
asserts the worked anchors above, the trend that the critical load
drops as the effective length grows, the end-condition K table and
its aliases, the stress-form equivalence sigma_cr = pi^2*E/lambda^2,
the transition-slenderness classification and the ValueError cases
for non-positive or non-finite inputs and unknown end conditions.
Run:

python3 scripts/test_buckling_analysis.py

## Compliance

- FAR-25 and CS-25 are referenced, not reproduced: standards-map.yaml
  marks them gated: false and reference-only: true; only the summary
  paraphrase above is used, never standard text.
- compliance: STANDARDS-REF, gated: false.

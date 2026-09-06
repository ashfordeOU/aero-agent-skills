---
name: thin-airfoil-section-theory
description: "Use when you must compute the section lift and the quarter-chord pitching moment of a thin cambered airfoil from its camber line: decompose the camber slope into the glauert-sine-series coefficients A0, A1 and A2 by trapezoid quadrature over the theta transform x = (1 - cos(theta))/2, then recover the zero-lift angle alpha_L0, the section lift coefficient cl = 2*pi*(alpha - alpha_L0), the quarter-chord pitching-moment coefficient cm_c4 = (pi/4)*(A2 - A1) and the center-of-pressure location x_cp/c = 1/4 - cm_c4/cl, for a NACA 4-digit mean line, a polynomial camber line or sampled camber stations. Produces the closed-form analytic section aerodynamics that anchor the numerical panel and viscous section tools. Trigger: glauert coefficients, zero lift angle, section pitching moment, camber line analysis, thin airfoil section."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: airfoil
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: airfoil
  tags: [thin-airfoil-section-theory, glauert-sine-series, zero-lift-angle, quarter-chord-moment, camber-line]
  version: 0.1.0
  author: Aero Agent Skills
---

# Thin Airfoil Section Theory (aerodynamics/airfoil/thin-airfoil-section-theory)

Use when you must turn a thin airfoil's camber line into its analytic
section aerodynamics: the Glauert sine-series coefficients of the camber
slope, the zero-lift angle, the section lift curve and the quarter-chord
pitching moment. This leaf computes the closed-form thin-airfoil solution
in pure stdlib Python, with trapezoid quadrature used only for the Fourier
integrals over the theta transform. It pairs with
aerodynamics/airfoil/airfoil-geometry, which produces the mean camber line
ordinates and slope consumed here (both leaves can be cross-checked on the
same NACA 2412 camber line), and it supplies the analytic anchor that the
numerical and viscous section layers beneath it verify against. Section
coefficients are derived here from the camber line; the finite-wing slope
leaf aerodynamics/drag-polars/lift-curve-slope instead consumes alpha_zero
and the section slope as given inputs for its aspect-ratio and sweep
corrections, so it is the complement, not the duplicate.

## Domain quick reference

- Glauert theta transform: x = (1 - cos(theta))/2 maps the chord x in [0, 1]
  onto theta in [0, pi], clustering stations at the leading edge where the
  camber slope varies fastest. All integrals run over this theta grid.
- Camber slope input routes: NACA 4-digit mean line (m, p) with dz/dx =
  (2m/p^2)(p - x) for x <= p and dz/dx = (2m/(1-p)^2)(p - x) for x >= p
  (zero at x = p, matching the airfoil-geometry formulas); polynomial mean
  line z = sum(c_i x^i) with dz/dx = sum(i c_i x^(i-1)); or sampled (x, z)
  stations read as piecewise-linear camber with constant slope per segment.
- Glauert sine-series coefficients (gamma(theta) = 2U(A0 (1+cos)/sin +
  A1 sin(theta) + A2 sin(2 theta))):
  A0 = alpha - (1/pi) int dz/dx dtheta,
  A1 = (2/pi) int dz/dx cos(theta) dtheta,
  A2 = (2/pi) int dz/dx cos(2 theta) dtheta.
- Zero-lift angle: alpha_L0 = (1/pi) int dz/dx (1 - cos(theta)) dtheta,
  identically -A0(alpha = 0) - A1/2; the identity A0(alpha_L0) = -A1/2
  holds exactly, so cl vanishes at the zero-lift angle.
- Section lift: cl = 2 pi A0 + pi A1 = 2 pi (alpha - alpha_L0).
- Quarter-chord pitching moment (aerodynamic center at c/4):
  cm_c4 = (pi/4)(A2 - A1), equivalently cm_le + cl/4 with
  cm_le = -(pi/2)(A0 + A1) + (pi/4) A2. The mistranscribed reading
  -(pi/4)(A1 + A2) is off by (pi/2) A2 and fails the identity; it is
  rejected (it coincides with the classical form only at A2 = 0).
- Center of pressure: x_cp/c = 1/4 - cm_c4/cl, defined only at nonzero lift.
- KNOWN-EXACT closed forms: the parabolic mean line z = 4m x (1 - x) (the
  NACA 4-digit mean line at p = 0.5) gives alpha_L0 = -2m, A1 = 4m, A2 = 0,
  cm_c4 = -pi m exactly; a flat mean line gives A0 = alpha and zero
  everything else. Incompressible potential flow only: no Mach effects, no
  viscosity, no stall.

## Workflow

1. Choose the camber-line input route: NACA 4-digit mean-line parameters
   (m, p) with glauert_coefficients_naca4, polynomial power-series
   coefficients with glauert_coefficients_poly, or sampled (x, z) camber
   stations spanning [0, 1] with glauert_coefficients_points. All three
   take alpha_rad first and default to n_theta = 40000 quadrature intervals.
2. Run the Glauert sine-series decomposition: each route integrates the
   camber slope dz/dx by trapezoid quadrature on the uniform theta grid
   (endpoints included) and returns A0, A1, A2 and the zero-lift angle
   alpha_L0 as a 4-tuple.
3. Recover the section lift coefficient with lift_coefficient(alpha_rad,
   alpha_L0_rad) = 2 pi (alpha - alpha_L0); cross-check the identity
   cl = 2 pi A0 + pi A1 on the same coefficients.
4. Read the quarter-chord pitching-moment coefficient with
   quarter_chord_moment(A1, A2) = (pi/4)(A2 - A1); verify via the
   independent route cm_le + cl/4 when the full series is available.
5. Locate the center of pressure with
   center_of_pressure_over_chord(cl, cm_c4) = 1/4 - cm_c4/cl; the function
   raises ValueError at |cl| < 1e-12, where the cp is not defined.
6. Confirm the deterministic checks with the contract test
   scripts/test_thin_airfoil_section_theory.py.

## Worked example

NACA 2412 mean line (m = 0.02, p = 0.4) at alpha = 4 deg =
0.069813170080 rad, the section whose camber line airfoil-geometry also
handles. Real module outputs (trapezoid quadrature, n_theta = 40000):

- glauert_coefficients_naca4(0.069813170080, 0.02, 0.4): A0 =
  0.065320283700, A1 = 0.081495141601, A2 = 0.013861276465, alpha_L0 =
  -0.036254684420 rad = -2.077240404870 deg, within a few hundredths of a
  degree of the measured 2412 zero-lift angle near -2 deg.
- Zero-lift identity: alpha_L0 = -A0(0) - A1/2 agrees with the direct
  integral to 1.3e-16; A0(alpha_L0) = -0.040747570801 equals -A1/2.
- Section lift: cl = 2 pi (0.069813170080 + 0.036254684420) =
  0.666443984960, matching cl = 2 pi A0 + pi A1 to 7.8e-16; at alpha = 0
  the camber alone lifts at cl = 0.227794900467.
- Quarter-chord moment: cm_c4 = (pi/4)(A2 - A1) = -0.053119513461, near the
  familiar measured 2412 cm0.25 of about -0.05; the route cm_le + cl/4
  gives the same value to 1.9e-16, while the mistranscribed
  -(pi/4)(A1 + A2) = -0.074892755617 is off by (pi/2) A2 = +0.021773242156.
- Center of pressure: x_cp/c = 1/4 - cm_c4/cl = 0.329705893759: the cp sits
  at 0.330 chord at 4 deg and moves back toward the quarter chord as cl
  grows.
- Quadrature convergence: A1 at n_theta = 40000 agrees with n_theta =
  1000000 to 3.0e-13, so the default resolution is converged at the kinked
  2412 slope to all printed digits.

KNOWN-EXACT validation on the parabolic mean line z = 4m x (1 - x), m =
0.04 (polynomial route, coeffs [0.0, 0.16, -0.16]) at 4 deg: exact closed
forms are alpha_L0 = -2m = -0.08 rad, A1 = 4m = 0.16, A2 = 0, cm_c4 =
-pi m = -0.125663706144, cl(4 deg) = 0.941303909067, cl(0) = 4 pi m =
0.502654824574, x_cp/c(4 deg) = 0.383499611478. Quadrature recovers them
to 1e-15, and the NACA 4-digit route at p = 0.5 reproduces the parabola
exactly (A1 = 0.160000000000, alpha_L0 = -0.080000000000, cm_c4 =
-0.125663706144). A flat mean line (coeffs [0.0, 0.0]) gives A0 =
0.069813170080 = alpha with A1 = A2 = alpha_L0 = cm_c4 = 0.

Sampled camber stations: a 4001-station sample of the parabola gives
alpha_L0 = -0.079999658257 (3.4e-7 from -2m) and A1 = 0.159999318515
(6.8e-7 from 4m); a 4001-station sample of the 2412 mean line gives
alpha_L0 = -0.036254564543 rad and cm_c4 = -0.053119329442, within 1.2e-7
and 1.8e-7 of the analytic route respectively.

## Verification

- glauert_coefficients_naca4(0.069813170080, 0.02, 0.4) returns A0 =
  0.065320283700, A1 = 0.081495141601, A2 = 0.013861276465, alpha_L0 =
  -0.036254684420 within 1e-9 of the spec anchors.
- lift_coefficient gives 0.666443984960 at 4 deg and 0.227794900467 at
  alpha = 0; quarter_chord_moment gives -0.053119513461;
  center_of_pressure_over_chord gives 0.329705893759, all within 1e-9.
- Closed forms hold: parabolic alpha_L0 = -2m, A1 = 4m, A2 = 0,
  cm_c4 = -pi m; flat mean line A0 = alpha with the rest zero; the
  identities alpha_L0 = -A0(0) - A1/2, A0(alpha_L0) = -A1/2,
  cl = 2 pi A0 + pi A1 = 2 pi (alpha - alpha_L0) and cm_c4 = cm_le + cl/4
  all hold to 1e-12.
- Convergence: A1 at n_theta = 1000000 differs from n_theta = 40000 by
  3.0e-13 on the 2412 mean line.
- ValueError rejection: m = -0.01 and m = 0.2 (4-digit camber range),
  p = 0.0 and p = 1.0, n_theta below 100 or non-int, empty or non-list
  polynomial coeffs, non-monotone sample stations, sample stations not
  spanning [0, 1], and center_of_pressure_over_chord at |cl| < 1e-12.
- Run the deterministic contract test offline: python3
  scripts/test_thin_airfoil_section_theory.py (33 tests, under 2 s).

## Related leaves

- aerodynamics/airfoil/airfoil-geometry: produces the mean camber line
  ordinates and slope consumed here; the NACA 2412 cross-check airfoil is
  shared by both leaves.
- aerodynamics/drag-polars/lift-curve-slope: the finite-wing slope leaf
  that consumes alpha_zero and the section slope as inputs; complementary
  scope, never a duplicate of the camber-line derivation.
- aerodynamics/airfoil/xfoil-analysis: numerical viscous section results
  that use the analytic section solution as their verification anchor.
- aerodynamics/cfd/panel-method: the numerical potential layer beneath the
  closed-form section solution.

## Pitfalls

- Transcribing the quarter-chord moment with the wrong sign: the anchor
  rejects cm_c4 = -(pi/4)(A1 + A2), which is off by (pi/2) A2 and fails
  the identity cm_c4 = cm_le + cl/4. The classical relation is
  cm_c4 = (pi/4)(A2 - A1).
- Deriving section data that is input elsewhere: alpha_zero and the
  section slope are inputs to the lift-curve-slope leaf for its finite
  aspect-ratio and sweep work; this leaf derives them from the camber
  line instead. Do not reuse the lift-curve-slope routing tag for this
  leaf's camber-line claim.
- Reading the camber as lift: the flat mean line still lifts at
  cl = 2 pi alpha; only the zero-lift angle, not the slope 2 pi, is set
  by camber.
- Calling the center of pressure at zero lift: x_cp/c = 1/4 - cm_c4/cl
  diverges as cl approaches zero; the module raises ValueError at
  |cl| < 1e-12 rather than return a meaningless station.
- Feeding sample stations that are not strictly increasing or that do not
  span exactly [0, 1]: the piecewise-linear route rejects both, since a
  camber line must cover the full chord once.
- Under-resolving the quadrature: kinked 4-digit slopes converge slowly
  (A1 needs about 40000 intervals to reach 1e-12); the default
  n_theta = 40000 is converged, but n_theta below 100 is rejected.
- Extending beyond the model: no Mach correction, viscosity or stall lives
  in this leaf; it is the incompressible potential-flow section solution
  only.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_thin_airfoil_section_theory.py

The 33 tests cover the NACA 2412 worked example at 4 deg (all four Glauert
coefficients, the zero-lift angle in rad and deg, cl at 4 deg and at zero
alpha, the quarter-chord moment, the center of pressure), the closed-form
identities (zero-lift angle from -A0(0) - A1/2, A0(alpha_L0) = -A1/2, the
two cl routes, cm_c4 = cm_le + cl/4, rejection of the A1 + A2
mistranscription), the KNOWN-EXACT parabolic mean line through the
polynomial route and the NACA p = 0.5 crossover, the flat mean line,
quadrature convergence at one million intervals, the 4001-station sampled
camber routes, and ValueError rejection of every non-physical input
listed in the spec. All numeric asserts are order-safe
(assertAlmostEqual with delta or math.isclose); no exact float equality
on computed sums.

## Compliance

- NACA Report 824 (naca-tr-824) frames the thin-airfoil theory context as
  US government work in the public domain; the relations above are
  standard engineering methodology from Anderson and Katz and Plotkin,
  summary-only per standards-map.yaml, never reproduced verbatim.
- compliance: STANDARDS-REF, gated: false.

---
name: laminar-far-wake
description: "Use when you must compute the two-dimensional laminar far-wake velocity-defect profile and drag downstream of a thin flat plate or slender body at zero incidence, the Goldstein 1933 similarity wake: evaluate the Gaussian cross-stream velocity-defect profile with the spread parameter U/(4*nu*x), the centerline-defect decay as x^-1/2 and the wake half-width growth as x^1/2 downstream of the trailing edge, integrate the momentum deficit across the wake with the wake-momentum-integral drag identity D = rho*U*integral u1 dy to recover the plate drag, and link the far-wake traverse to the laminar Blasius trailing-edge momentum state with the 0.664 constant. Produces the wake velocity-defect and recovered-velocity profiles, the decay and spreading laws and the wake-survey drag in SI units that anchor laminar wake diagnostics and drag checks. Trigger: laminar-far-wake, far-wake-velocity-defect, wake-momentum-integral, velocity-defect-profile, wake-survey-drag."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: boundary-layer
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: boundary-layer
  tags: [laminar-far-wake, far-wake-velocity-defect, wake-momentum-integral, velocity-defect-profile, wake-survey-drag]
  version: 0.1.0
  author: AeroSkills
---

# Laminar Far Wake (aerodynamics/boundary-layer/laminar-far-wake)

Use when you must compute the two-dimensional incompressible laminar far
wake downstream of a thin flat plate at zero incidence, the Goldstein
(1933) similarity wake that the attached laminar boundary layers shed
from the trailing edge, in the form Schlichting Boundary-Layer Theory
(wakes and free-shear-layers chapter, wake behind a flat plate) and
White Viscous Fluid Flow (laminar free shear layers, plane wake defect
solution) present it. This leaf is the eighth member of the
boundary-layer pack and owns the downstream free-shear wake region that
every attached-layer sibling stops short of: boundary-layer-theory
stops at the plate surface quantities and the transition, separation
and unsteady siblings never leave the attached layer. Far downstream of
the trailing edge the small velocity defect u1 = U - u collapses onto a
Gaussian similarity profile whose cross-stream integral conserves the
momentum deficit, and the wake-momentum-integral identity
D = rho*U*integral u1 dy is the closed-form basis of wake-survey drag
measurement. It does not do attached flat-plate boundary-layer
thickness or skin-friction estimation on the surface, transition or
separation traverses, creeping Stokes sphere flow, unsteady plate
Stokes layers, the wind-tunnel solid-blockage and wake-blockage
corrections, or turbulent, axisymmetric, compressible and near-wake
flows: incompressible constant-property laminar flow only, small defect
u1 << U (x/c at least of order ten), two-dimensional thin-plate
small-deficit wakes of a symmetric body at zero incidence.

## Domain quick reference

The wake coordinate x is measured downstream from the trailing edge, y
is the cross-stream coordinate, u1 is the positive velocity defect
U - u. Module constants: NU_AIR = 1.46e-5 m2/s, RHO_AIR = 1.225 kg/m3,
U_INF = 5.0 m/s, PLATE_CHORD = 1.0 m, BLASIUS_THETA_COEF = 0.664,
BLASIUS_DRAG_COEF = 1.328, SIDES = 2.

- Trailing-edge state (attached Blasius layer, one side): theta_c =
  0.664*sqrt(nu*c/U) = 0.664*c/sqrt(Re_c) with Re_c = U*c/nu the chord
  Reynolds number.
- Plate drag per unit span (both sides), the momentum source of the
  wake: D = 2*rho*U^2*theta_c = 1.328*rho*U^2*sqrt(nu*c/U), N/m; the
  drag coefficient C_D = D/(0.5*rho*U^2*c) = 4*theta_c/c =
  2.656/sqrt(Re_c), dimensionless.
- Linearized wake defect equation: U*du1/dx = nu*d2u1/dy2, the
  small-defect (u1 << U) form of the boundary-layer equations in the
  wake, with the momentum invariant D = rho*U*integral_{-inf}^{+inf}
  u1 dy, the wake-momentum-integral drag identity (exact in the
  far-wake limit, the closed-form basis of wake-survey drag).
- Gaussian similarity profile (the Goldstein far-wake solution):
  u1(x, y) = u_c(x)*exp(-B(x)*y^2) with spread parameter
  B(x) = U/(4*nu*x), 1/m2, which satisfies the linearized equation
  identically, hence u_c proportional to x^-1/2.
- Centerline defect from the drag: u_c(x) = (D/(rho*U))*sqrt(B/pi),
  m/s, collapsing for the two-sided Blasius plate to the closed form
  u_c(x) = (0.664*U/sqrt(pi))*sqrt(c/x) (coefficient 0.664/sqrt(pi) =
  0.3746218835).
- Defect and wake velocity at (x, y): u1 = u_c*exp(-B*y^2) and
  u = U - u1, both m/s.
- Widths: half-defect width y_half = sqrt(ln(2)/B) (u1 = u_c/2 there)
  and one-over-e width y_e = sqrt(1/B) (u1 = u_c*exp(-1) there), both
  m, growing as x^1/2 since B is proportional to 1/x.
- Momentum integral of the Gaussian: integral u1 dy = u_c*sqrt(pi/B),
  m2/s, independent of x and equal to D/(rho*U) = 2*U*theta_c at every
  station; the wake-survey drag is D = rho*U*u_c*sqrt(pi/B), N/m.
- Full (nonlinear) momentum deficit, documented for honesty:
  rho*integral u*(U - u) dy = rho*(U*integral u1 dy - integral u1^2 dy)
  with integral u1^2 dy = u_c^2*sqrt(pi/(2*B)) closed form; it lies
  below the linearized identity by a relative amount of order u_c/U and
  converges to it downstream (ratios 0.94702046516 at x = 25*c,
  0.97351023258 at x = 100*c, 0.98675511629 at x = 400*c).

SI units throughout; Goldstein 1933, Schlichting Boundary-Layer Theory
and White Viscous Fluid Flow material cited through NACA TR-824,
summary-only.

## Workflow

1. Fix the trailing-edge state of the fully laminar plate: chord c,
   freestream speed U, rho, nu, then the chord Reynolds number
   (reynolds_number) and the trailing-edge momentum thickness
   (momentum_thickness_blasius): theta_c = 0.664*c/sqrt(Re_c), the
   state the far wake carries downstream.
2. Assemble the plate drag, the momentum source of the wake:
   plate_drag_per_span(U, rho, nu, c) with the default two-sided plate
   (SIDES = 2, one side carrying rho*U^2*theta_c), and reduce it with
   plate_drag_coefficient, cross-checked against C_D = 2.656/sqrt(Re_c)
   and C_D = 4*theta_c/c.
3. Choose the downstream traverse station x measured from the trailing
   edge (x/c of order ten or more for the linearized far-wake regime)
   and evaluate the Gaussian spread parameter with
   wake_spread_parameter(U, nu, x): B = U/(4*nu*x).
4. Traverse the centerline defect: centerline_defect_from_drag(D, rho,
   U, B) is the normalization that conserves the drag exactly, and
   centerline_defect_blasius(U, c, x) is its closed-form twin for the
   two-sided Blasius plate, giving the x^-1/2 decay law explicitly.
5. Traverse the Gaussian defect profile across y with
   velocity_defect_gaussian(u_c, B, y) and recover the wake velocity
   with wake_velocity(U, u_c, B, y); read the wake widths from
   half_defect_width(B) and one_over_e_width(B).
6. Check the decay and spreading laws across stations: the invariant
   u_c*sqrt(x) is constant (x^-1/2 centerline decay) and the half-defect
   width grows as x^1/2, doubling when x quadruples.
7. Integrate the momentum deficit: defect_integral(u_c, B) =
   u_c*sqrt(pi/B) is station-independent, and drag_from_wake(u_c, B,
   rho, U) = rho*U*integral u1 dy reproduces the plate drag at every
   station to float noise, the wake-survey drag identity.
8. Run the nonlinear honesty check: full_momentum_deficit(rho, U, u_c,
   B) lies a few percent below the linearized drag_from_wake and
   converges to it as the wake spreads; report the residual when the
   defect is not tiny.
9. Report the drag diagnostic: the wake-survey drag per unit span and
   the drag coefficient from the traverse, with the profile decay and
   spreading numbers as the laminar-wake fingerprint.
10. Confirm the deterministic checks: rerun the closed-form identities
    and reject non-physical inputs (non-positive U, nu, rho, c, x, D,
    B, u_centerline, sides below one) with the contract test
    scripts/test_laminar_far_wake.py.

## Worked example

Air at standard conditions nu = 1.46e-5 m2/s, rho = 1.225 kg/m3, a flat
plate of chord c = 1.0 m at U = 5.0 m/s, wetted on both sides with
fully laminar Blasius boundary layers to the trailing edge. All values
below are real outputs of the module.

- Trailing-edge state: Re_c = U*c/nu = 342465.7534; momentum thickness
  at the trailing edge (one side) theta_c = 0.664*sqrt(nu*c/U) =
  1.1346436974e-3 m (1.135 mm); total drag per unit span, both sides,
  D = 1.328*rho*U^2*sqrt(nu*c/U) = 2*rho*U^2*theta_c = 6.9496926464e-2
  N/m; drag coefficient C_D = D/(0.5*rho*U^2*c) = 0.00453857479,
  identical to 2.656/sqrt(Re_c) = 0.00453857479 and to 4*theta_c/c =
  0.00453857479 (three routes agree).
- Far-wake traverse at x = 100*c = 100.0 m downstream of the trailing
  edge (centerline defect 3.746 percent of U, solidly small-defect):
  spread parameter B = U/(4*nu*x) = 8.5616438356e2 1/m2; centerline
  defect u_c = (D/(rho*U))*sqrt(B/pi) = 0.18731094174 m/s, identical to
  the closed form (0.664*U/sqrt(pi))*sqrt(c/x) = 0.18731094174 m/s;
  widths y_half = sqrt(ln(2)/B) = 2.8453398864e-2 m (2.845 cm) and
  y_e = sqrt(1/B) = 3.4176014981e-2 m, with y_e/y_half =
  1.2011224087 = sqrt(1/ln(2)).
- Profile values: u1(y_half) = 9.3655470869e-2 m/s (exactly u_c/2),
  u1(y_e) = 6.8907844572e-2 m/s (u_c*exp(-1)), and the recovered
  wake-axis velocity u(0) = U - u_c = 4.8126890583 m/s; at
  y = 6*y_half = 0.170720393182 m the wake is indistinguishable from
  the freestream, u/U = 0.999999999999455.
- Momentum integral: integral u1 dy = u_c*sqrt(pi/B) = 1.1346436974e-2
  m2/s, equal to D/(rho*U) and to 2*U*theta_c at every station; the
  wake-survey drag D = rho*U*integral u1 dy = 6.9496926464e-2 N/m
  equals the plate drag to float noise (ratio 1.0).
- Decay and spreading across stations: centerline defect
  0.37462188348 m/s at x = 25*c, 0.18731094174 m/s at x = 100*c and
  0.093655470869 m/s at x = 400*c, so u_c(4x)/u_c(x) = 0.5 exactly and
  the invariant u_c*sqrt(x) = 1.8731094174 m/s*sqrt(m) is unchanged
  (x^-1/2 decay); half-defect width 1.4226699432e-2 m at x = 25*c,
  2.8453398864e-2 m at x = 100*c and 5.6906797727e-2 m at x = 400*c,
  so y_half(4x)/y_half(x) = 2 exactly (x^1/2 spreading).
- Nonlinear honesty check: the full deficit rho*integral u*(U - u) dy
  lies 5.297953 percent below D at x = 25*c (ratio 0.94702046516),
  2.648977 percent below at x = 100*c (ratio 0.97351023258, residual
  1.8409574184e-3 N/m) and 1.324488 percent below at x = 400*c (ratio
  0.98675511629), converging to the linearized identity downstream.

Read-off: a 1 m fully laminar plate at 5 m/s in air drags 6.95e-2 N
per metre of span; 100 m downstream the wake axis runs 3.75 percent
slow inside a Gaussian defect 2.85 cm wide at half depth, the
integrated momentum deficit of that Gaussian recovers the plate drag
exactly, and quadrupling the downstream distance halves the centerline
defect while the wake doubles in width. A wake-survey traverse at
x/c = 100 integrated with the identity D = rho*U*integral u1 dy reports
the drag without any force balance.

## Verification

- Confirm reynolds_number(5.0, 1.0, 1.46e-5) returns 342465.7534 and
  momentum_thickness_blasius(5.0, 1.0, 1.46e-5) returns
  1.1346436974e-3 m, equal to 0.664/sqrt(Re_c) to float noise.
- Confirm plate_drag_per_span(5.0, 1.225, 1.46e-5, 1.0) returns
  6.9496926464e-2 N/m (between 6.5e-2 and 7.5e-2 N/m), the sides = 1
  value equals rho*U^2*theta_c, and the two-sided value is twice the
  one-sided value.
- Confirm plate_drag_coefficient(5.0, 1.225, 1.46e-5, 1.0) returns
  4.53857479e-3, equal to 2.656/sqrt(Re_c) and to 4*theta_c/c.
- Confirm wake_spread_parameter(5.0, 1.46e-5, 100.0) returns
  8.5616438356e2 1/m2 and is 0.25 of the x = 400.0 value.
- Confirm the centerline defect at x = 100.0 m is 0.18731094174 m/s by
  both routes (drag normalization and closed form, agreeing to float
  noise), with u_c/U = 0.03746218835 and the invariant u_c*sqrt(x) =
  1.8731094174 across x = 25, 100 and 400 m.
- Confirm the decay and spreading laws: u_c(4x)/u_c(x) = 0.5,
  u_c(2x)/u_c(x) = 1/sqrt(2), y_half(4x)/y_half(x) = 2 and
  B(4x)/B(x) = 0.25, all exact to float noise.
- Confirm the Gaussian shape at x = 100.0 m: y_half = 2.8453398864e-2 m,
  y_e = 3.4176014981e-2 m, u1(y_half)/u_c = 0.5, u1(y_e)/u_c = 1/e,
  u(0) = 4.8126890583 m/s and u/U = 0.999999999999455 at y = 6*y_half.
- Confirm the momentum identity: defect_integral = 1.1346436974e-2 m2/s
  and drag_from_wake = 6.9496926464e-2 N/m at x = 25, 100 and 400 m,
  equal to the plate drag to float noise at every station.
- Confirm the nonlinear ratios 0.94702046516, 0.97351023258 and
  0.98675511629 (monotone toward one) and the linearized residual
  1.8409574184e-3 N/m at x = 100.0 m.
- Confirm every non-positive U, nu, rho, c, x, D, B, every negative
  u_centerline and every sides below one raises ValueError, and that
  every function is deterministic on repeat calls.
- Run the contract test offline: python3
  scripts/test_laminar_far_wake.py (32 tests, deterministic).

## Related leaves

- aerodynamics/boundary-layer/boundary-layer-theory: the attached
  flat-plate layer owner (Blasius thickness, skin friction, transition
  on the surface); this leaf consumes the trailing-edge momentum state
  as the source the wake carries and never estimates surface-layer
  quantities.
- aerodynamics/boundary-layer/stokes-creeping-flow-drag: the Re << 1
  attached-body limit with its no-wake fore-aft symmetric creeping
  flow, the regime fence that stays away from the finite-Reynolds wake
  profile of this leaf.
- aerodynamics/boundary-layer/boundary-layer-transition and
  boundary-layer-separation: the attached-layer traverse leaves that
  stop at transition onset and separation, never mapping the downstream
  wake state this leaf owns.
- aerodynamics/wind-tunnel/windtunnel-wall-corrections: uses wake
  blockage, a scalar tunnel-geometry correction to the dynamic
  pressure, not the wake velocity-defect profile or the momentum
  integration of this leaf.
- aerodynamics/wind-tunnel/windtunnel-data-reduction: the raw-run
  pressure-rake reduction leaf; the wake-survey drag identity of this
  leaf is the physics behind its rake traverse.

## Pitfalls

- Applying the far-wake Gaussian too close to the trailing edge: the
  similarity profile holds for x/c of order ten or more; immediately
  behind the trailing edge the near-wake defect follows the Goldstein
  error-function solution, not this small-defect Gaussian.
- Treating the linearized identity as exact when the defect is not
  small: D = rho*U*integral u1 dy neglects the u1^2 term, which runs a
  few percent of the drag at x/c ~ 25 and only converges downstream;
  use the full_momentum_deficit diagnostic for honesty.
- Mixing the width conventions: y_half = sqrt(ln(2)/B) (defect halved)
  differs from y_e = sqrt(1/B) (defect at 1/e) by the factor
  sqrt(1/ln(2)) = 1.2011224087; report which width is meant.
- Forgetting the two-sided plate: the plate drag doubles with SIDES = 2
  (each side carries rho*U^2*theta_c), and the centerline defect scales
  with the square root of the drag, so a one-sided mistake shifts every
  downstream profile value.
- Measuring x from the wrong origin: the wake coordinate x runs
  downstream from the trailing edge, not from the plate leading edge,
  and the chord Reynolds number Re_c still uses the full chord.
- Confusing this leaf with the pack's attached-layer owners: it does
  not estimate displacement thickness, momentum thickness or skin
  friction on the plate surface, and the wake-blockage scalar of the
  wind-tunnel leaves is not a velocity-defect profile.
- Extending the Gaussian beyond its regime: turbulent wakes, jets,
  mixing layers, axisymmetric wakes, compressible wakes and the
  near-wake error-function layer all lie outside this small-defect
  laminar solution.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_laminar_far_wake.py

The test covers the worked-example contract (Reynolds number, momentum
thickness, plate drag with magnitude bound, the three-route drag
coefficient, spread parameter, centerline defect by both routes, widths,
profile values and wake velocities), the decay and spreading laws across
stations (x^-1/2 centerline decay, x^1/2 width growth), the momentum
identity at every station (defect integral and wake-survey drag against
the plate drag), the nonlinear momentum-deficit honesty check with the
linearized residual, deterministic repeat calls, and the input-rejection
traverse of non-physical U, nu, rho, c, x, D, B, u_centerline and sides
arguments.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is the cited
  reference for the boundary-layer pack; the laminar wake treatment
  follows Goldstein 1933, Schlichting Boundary-Layer Theory (wakes and
  free-shear-layers chapter) and White Viscous Fluid Flow (laminar free
  shear layers), whose material is cited through the report. Summary-
  only methodology per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

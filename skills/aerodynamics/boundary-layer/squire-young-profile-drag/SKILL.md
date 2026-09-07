---
name: squire-young-profile-drag
description: "Use when you must compute the section profile-drag coefficient of a two-dimensional body or airfoil from the boundary-layer momentum state at its trailing edge: evaluate the squire-young-formula c_d,p = 2*(theta_TE/c)*(U_TE/U_inf)^((H_TE+5)/2) with the documented trailing-edge shape factor about 1.4, and the zero-pressure-gradient reduction to the Blasius flat-plate drag 1.328/sqrt(Re_c) when the trailing-edge velocity equals the freestream. Grows the laminar momentum thickness to the trailing edge on the integral growth relation for the fully laminar chain, then applies the edge-velocity-ratio exponent. Produces the section profile-drag-coefficient, the trailing-edge momentum thickness and the edge-velocity factor that gate airfoil section drag estimates and boundary-layer checks. Trigger: squire young formula, profile drag coefficient, trailing edge momentum thickness, edge velocity ratio, laminar profile drag, momentum integral drag."
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
  tags: [squire-young-profile-drag, squire-young-formula, profile-drag-coefficient, trailing-edge-momentum-thickness, laminar-profile-drag, momentum-integral-drag]
  version: 0.1.0
  author: AeroSkills
---

# Squire-Young Profile Drag (aerodynamics/boundary-layer/squire-young-profile-drag)

Use when you must compute the section profile-drag coefficient of a
two-dimensional body or airfoil from the boundary-layer momentum state
at its trailing edge with the Squire-Young formula (Squire and Young,
ARC R&M 1838, 1938; Schlichting, Boundary-Layer Theory, 7th ed., pp.
158-162; validated against surface-integrated CFD within 2-3 percent in
the low-drag range by Coder and Maughmer, Journal of Aircraft 52(3),
2015): c_d,p = 2*(theta_TE/c)*(U_TE/U_inf)**((H_TE+5)/2). This leaf
evaluates the trailing-edge factor, maps a known TE momentum state to
the profile-drag coefficient, grows the laminar momentum thickness to
the trailing edge on the integral growth relation for the fully laminar
chain, and reproduces the Blasius flat-plate drag exactly at zero
pressure gradient. It is the TE-to-drag member of the boundary-layer
pack, complementing the traverses of boundary-layer-separation and
boundary-layer-transition, which stop at their separation and
transition signals and never map the TE momentum state to drag. It does
not do Thwaites lambda traverses, separation or transition criteria,
flat-plate skin-friction or thickness correlations, whole-aircraft drag
buildup, XFOIL-style polar runs, rotor-blade profile power, or
wake-survey instrumentation: incompressible clean 2-D attached flow
only, one surface of the section at a time.

## Domain quick reference

Module constants (fixed numbers): NU_AIR = 1.46e-5 m2/s (air kinematic
viscosity at standard conditions), H_TE = 1.4 (default trailing-edge
shape factor H = delta*/theta, documented at about 1.4), LAMINAR_THETA_C
= 0.664 and BLASIUS_DRAG_C = 1.328 (= 2*0.664, the laminar flat-plate
drag constant), GROWTH_C = 0.664**2 = 0.440896 (the laminar
integral-growth constant, pinned so the zero-pressure-gradient plate
closes to the Blasius momentum thickness exactly; the sibling Thwaites
constant 0.45 would run the flat-plate theta 1.03 percent high because
the siblings' theta feeds the Michel criterion while this leaf's theta
feeds a drag mapping anchored at Blasius exactness).

- Squire-Young profile drag: c_d,p = 2*(theta_TE/c)*
  (U_TE/U_inf)**((H_TE+5)/2), dimensionless, ONE surface of the
  section.
- Edge-velocity factor: f = (U_TE/U_inf)**((H_TE+5)/2). Unity at
  U_TE = U_inf for any shape factor (the flat plate), below unity for
  U_TE < U_inf, the attached-flow band of a closed section. The
  exponent reads (H_TE+5)/2 = 3.2 at the default H_TE = 1.4.
- Zero-pressure-gradient reduction: at U_TE = U_inf the formula is
  c_d,p = 2*theta_TE/c, and with the Blasius TE momentum thickness
  theta_TE = 0.664*c/sqrt(Re_c) it reproduces the Blasius flat-plate
  drag 2*theta_TE/c = 1.328/sqrt(Re_c) exactly, independent of H_TE
  because the velocity ratio is unity. This reduction is the leaf's
  deterministic anchor.
- Laminar integral growth of theta to the trailing edge:
  theta_TE^2 = GROWTH_C * nu / U_TE**6 * integral_0^c Ue(x)**5 dx,
  cumulative trapezoid rule over the supplied stations; the segment
  from the leading edge (x = 0) to the first station keeps Ue at its
  first-station value, so a constant-velocity plate is exact.
- Linear edge-velocity law Ue(x) = U_inf*(1 - a*x/c): closed form
  theta_TE = sqrt(GROWTH_C * nu * U_inf**5 * c * (1 - (1-a)**6) /
  (6*a) / U_TE**6) with U_TE = U_inf*(1 - a).
- Both surfaces: for a symmetric section at zero lift whose surfaces
  share the TE state, the total profile drag is twice the one-surface
  value.

SI units throughout: x in m, U in m/s, nu in m2/s, theta in m, c_d,p
dimensionless. The Blasius constants 0.664 and 1.328 appear only as the
closed-form zero-pressure-gradient identity targets of the TE mapping,
never to compute surface skin-friction distributions or regime classes.

## Workflow

1. Fix the section state: chord c, freestream velocity U_inf and
   kinematic viscosity nu (NU_AIR default at standard conditions); the
   chord Reynolds number Re_c = U_inf*c/nu places the estimate
   (2.0548e6 in the worked example).
2. Take the trailing-edge momentum state: the trailing-edge-momentum-
   thickness theta_TE and the trailing-edge edge velocity U_TE, with
   the documented trailing-edge shape factor H_TE = 1.4 default (the
   realistic band runs from about 1.2 to about 2.6).
3. Evaluate the edge-velocity factor with trailing_edge_factor(U_TE,
   U_inf, H_TE): (U_TE/U_inf)**((H_TE+5)/2), unity on the flat plate,
   below unity when the TE edge flow still has pressure to recover.
4. Map the momentum state to the section profile-drag coefficient with
   squire_young_profile_drag(theta_TE, c, U_TE, U_inf, H_TE) =
   2*(theta_TE/c)*factor, one surface of the section.
5. Check the zero-pressure-gradient reduction: at U_TE = U_inf the
   formula collapses to the momentum-integral value 2*theta_TE/c and
   reproduces the laminar flat-plate drag 1.328/sqrt(Re_c) when theta_TE
   sits at the Blasius value 0.664*c/sqrt(Re_c); this closes the
   deterministic anchor identity of the leaf.
6. For the fully laminar chain, grow the momentum thickness to the
   trailing edge with momentum_thickness_at_te(xs, ues, nu) over the
   edge-velocity traverse: theta_TE^2 = GROWTH_C*nu/U_TE**6 *
   integral_0^c Ue**5 dx on the cumulative trapezoid rule, U_TE read as
   the last-station edge velocity.
7. Run the one-call fully laminar chain with fully_laminar_profile_drag
   (xs, ues, nu, c, U_inf, H_TE): growth then squire-young-formula
   mapping in one step.
8. Combine surfaces: for a symmetric section at zero lift whose surfaces
   share the TE state, the total is twice the one-surface value.
9. Run the deterministic checks: rerun the identities above and the
   input-rejection traverse with the contract test
   scripts/test_squire_young_profile_drag.py.

## Worked example

Air at standard conditions nu = 1.46e-5 m2/s, chord c = 1.0 m,
freestream U_inf = 30.0 m/s, so Re_c = 2.0547945205e6. The traverse
grids use 4001 stations (step 2.5e-4 m). All values are real outputs of
the module.

Case A, direct formula from a TE momentum state: one-surface theta_TE =
3.0e-3 m (theta_TE/c = 0.003), U_TE = 27.0 m/s (edge-velocity ratio
0.9), H_TE = 1.4:

- trailing_edge_factor(27.0, 30.0, 1.4) = 0.71379915616, the
  (U_TE/U_inf)**3.2 wake-transfer factor, below unity because the TE
  edge flow still has pressure to recover.
- Raw momentum value 2*theta_TE/c = 6.0e-3; the Squire-Young estimate
  squire_young_profile_drag(3.0e-3, 1.0, 27.0, 30.0, 1.4) =
  4.2827949370e-3 one surface, and 8.5655898739e-3 for both surfaces of
  a symmetric section at zero lift sharing the TE state.
- H sensitivity: trailing_edge_factor(27.0, 30.0, 2.6) =
  0.67007210063, which lowers the one-surface estimate to
  4.0204326038e-3, 6.1 percent below the H_TE = 1.4 value at this
  velocity ratio.

Case B, the anchor identity on the fully laminar flat plate (U_TE =
U_inf = 30.0 m/s, zero pressure gradient):

- Blasius TE momentum thickness theta_TE = 0.664*c/sqrt(Re_c) =
  4.6321634974e-4 m.
- Reference drag 1.328/sqrt(Re_c) = 9.2643269948e-4.
- squire_young_profile_drag(4.6321634974e-4, 1.0, 30.0, 30.0, 1.4) =
  9.2643269948e-4, identity residual 0.0: the formula reproduces the
  Blasius flat-plate drag exactly when U_TE = U_inf.
- Chain end to end: momentum_thickness_at_te over the 4001-station
  constant-30 m/s plate = 4.6321634974e-4 m (rel 3.066e-14 against the
  Blasius value) and fully_laminar_profile_drag(...) = 9.2643269948e-4
  (rel 3.066e-14 against 1.328/sqrt(Re_c)): the fully laminar chain
  reproduces the Blasius drag on the plate.
- Reynolds invariance: c_d,p*sqrt(Re_c) = 1.3280000000 at Re_c and at
  Re_c/2 (U = 15 m/s), rel residual 3.060e-14.

Case C, the fully laminar 2-D section at low Reynolds number with a
decelerated edge flow Ue(x) = 30.0*(1 - 0.1*x/c) m/s over x in [0, 1]
m (U_TE/U_inf = 0.9 at the TE), H_TE = 1.4:

- momentum_thickness_at_te over the 4001-station traverse =
  5.6151694776e-4 m; the closed form of the linear law,
  sqrt(GROWTH_C*nu*U_inf**5*c*(1-0.9**6)/(6*0.1)/27.0**6) =
  5.6151694744e-4 m, quadrature residual 3.220e-13 m (rel 5.734e-10):
  the integral growth closes to the exact integral.
- Raw momentum value 2*theta_TE/c = 1.1230338955e-3, above the flat
  plate's 9.2643269948e-4 because the deceleration thickens the layer;
  the Squire-Young mapping fully_laminar_profile_drag(xs, ues, 1.46e-5,
  1.0, 30.0, 1.4) = 8.0162064696e-4, identical to the hand
  recomputation 2*(theta_TE/c)*(0.9)**3.2 = 8.0162064696e-4 (residual
  0.0).
- The exponent factor carries the whole difference between the raw
  momentum value and the drag estimate: 0.71379915616 at U_TE/U_inf =
  0.9 and H_TE = 1.4, versus unity on the flat plate.

Read-off: a section whose TE layer carries theta_TE/c = 0.003 at an
edge-velocity ratio 0.9 and H_TE = 1.4 has a Squire-Young profile-drag
coefficient of 4.283e-3 per surface (8.566e-3 total at zero lift), 29
percent below the raw 2*theta_TE/c momentum value 6.0e-3; the fully
laminar flat plate at Re_c = 2.0548e6 lands exactly on the Blasius
value 9.264e-4 through both the direct formula and the integral-growth
chain; and a fully laminar section whose edge flow decelerates 10
percent over the chord grows theta_TE to 5.615e-4 m (raw 2*theta_TE/c =
1.123e-3) before the edge-velocity-ratio factor 0.7138 brings the
estimate to 8.016e-4.

## Verification

- Confirm trailing_edge_factor(27.0, 30.0, 1.4) returns 0.71379915616
  and trailing_edge_factor(27.0, 30.0, 2.6) returns 0.67007210063, both
  inside the (U_TE/U_inf)**3.2 band, with the factor unity to float
  noise at U_TE = U_inf for any shape factor and the ratio f(1.4)/f(2.6)
  equal to (0.9)**(-0.6).
- Confirm squire_young_profile_drag(3.0e-3, 1.0, 27.0, 30.0, 1.4)
  returns 4.2827949370e-3 (magnitude band 4.0e-3 to 4.5e-3) and that it
  equals 2.0*(3.0e-3/1.0)*trailing_edge_factor(27.0, 30.0, 1.4); the
  both-surfaces total at symmetric zero lift is 8.5655898739e-3.
- Confirm the anchor identity: with theta_bl = 0.664/sqrt(Re_c) =
  4.6321634974e-4 m, squire_young_profile_drag(theta_bl, 1.0, 30.0,
  30.0, h_te) equals 1.328/sqrt(Re_c) = 9.2643269948e-4 within 1e-9
  relative for h_te in (1.4, 2.6), the reduction being independent of
  the shape factor at U_TE = U_inf.
- Confirm the chain equals the identity on the flat plate: a
  4001-station constant-30 m/s traverse gives momentum_thickness_at_te
  = 4.6321634974e-4 m and fully_laminar_profile_drag = 9.2643269948e-4
  within 1e-6 relative of the Blasius values.
- Confirm Reynolds invariance: on the plate,
  fully_laminar_profile_drag*sqrt(Re_c) = 1.328 within 1e-9 at U = 30.0
  and at U = 15.0 m/s (Re_c/2).
- Confirm the Case C chain: the 4001-station linear-decay traverse
  ue(x) = 30.0*(1 - 0.1*x) gives momentum_thickness_at_te =
  5.6151694776e-4 m within 1e-6 relative of the closed-form integral
  and fully_laminar_profile_drag = 8.0162064696e-4 within 1e-6
  relative, equal to 2.0*(theta_te/1.0)*(0.9)**3.2.
- Confirm the LE-gap convention: a constant-velocity traverse starting
  mid-plate (first station above x = 0) still closes to the Blasius
  theta, because the segment from the leading edge keeps the
  first-station edge velocity.
- Confirm the input-rejection traverse: non-positive u_te, u_inf,
  theta_te, chord, nu, a shape factor at or below 1.0, fewer than two
  stations, unequal or non-increasing station sets, a negative leading
  station and a non-positive edge velocity all raise ValueError.
- Run the contract test offline: python3
  scripts/test_squire_young_profile_drag.py (28 tests, deterministic,
  passes under both /usr/bin/python3 3.9.6 and the pyenv 3.13.12
  interpreter).

## Related leaves

- aerodynamics/boundary-layer/boundary-layer-separation: the Thwaites
  lambda traverse with the -0.09 laminar separation flag and the
  Stratford turbulent recovery criterion; its traverse stops at the
  separation signal and never maps the TE momentum state to drag.
- aerodynamics/boundary-layer/boundary-layer-transition: the Michel
  criterion traverse for the laminar-turbulent transition location; its
  traverse stops at the natural-transition onset, no TE-to-drag mapping.
- aerodynamics/boundary-layer/boundary-layer-theory: steady flat-plate
  layer definitions and correlations (Blasius and 1/7-power
  thicknesses, skin-friction coefficients, regime assignment), flat
  plate only, no section profile-drag coefficient from a TE momentum
  state.
- aerodynamics/boundary-layer/stokes-creeping-flow-drag: the exact
  low-Reynolds-number sphere drag member of the viscous-layer family,
  the creeping-flow complement to the attached TE-layer mapping here.
- aerodynamics/drag-polars/parasite-drag: the whole-aircraft zero-lift
  drag buildup over components with form and interference factors, the
  far-wake level this leaf's TE mapping feeds at section level.
- aerodynamics/airfoil/xfoil-analysis: numerical viscous polar runs,
  the tool-adjacent route that produces section polars without the
  closed-form Squire-Young relation.

## Pitfalls

- Reading the raw momentum value as the drag: 2*theta_TE/c is the
  momentum-integral value only when the TE edge velocity equals the
  freestream; on a decelerated section the edge-velocity-ratio exponent
  (U_TE/U_inf)**3.2 at H_TE = 1.4 lowers the estimate (0.7138 at ratio
  0.9, about 29 percent below the raw value in the worked example).
- Using the Thwaites constant 0.45 in the laminar integral growth: the
  siblings' theta feeds the Michel criterion, while this leaf's growth
  constant GROWTH_C = 0.664**2 = 0.440896 is pinned so the flat plate
  closes to the Blasius theta exactly; 0.45 runs the plate theta about
  1.03 percent high and breaks the 1.328/sqrt(Re_c) identity.
- Feeding a shape factor at or below 1.0: H = delta*/theta below unity
  is not an attached boundary layer (the realistic band runs from about
  1.2 to about 2.6), and the module raises ValueError.
- Forgetting the one-surface convention: c_d,p is per surface; a
  symmetric section at zero lift whose surfaces share the TE state
  carries twice the value.
- Extending the method beyond its fences: no turbulent or
  mixed-laminar-turbulent growth model, no compressibility, roughness,
  sweep, suction or wake-survey instrumentation inputs, and no
  whole-aircraft buildup; the clean incompressible attached 2-D
  section state is the whole claim.
- Mixing the momentum-thickness conventions: the trailing-edge-
  momentum-thickness here feeds a drag mapping, not a flat-plate
  skin-friction or displacement-thickness correlation, which belongs to
  boundary-layer-theory.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_squire_young_profile_drag.py

The 28 tests cover the trailing-edge factor anchors and the unity
flat-plate reduction, the factor-ratio exponent algebra, the
profile-drag coefficient of Case A with its magnitude band and the
both-surfaces total, the Blasius anchor identity at both shape factors,
the H sensitivity, the flat-plate momentum-thickness and fully laminar
chain identities (rel 3e-14 against the Blasius values), the Reynolds
invariance at Re_c and Re_c/2, the Case C linear-decay anchors against
the closed-form integral, the leading-edge-gap and partial-plate
scaling checks, the deterministic repeat calls, the module-constant and
no-RNG structure checks, and the full input-rejection traverse of
non-physical velocities, shape factors, chords, thicknesses, stations
and viscosities. All numeric asserts are tolerance-based
(assertAlmostEqual/isclose), so the suite passes identically under
/usr/bin/python3 3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is the cited
  reference for the boundary-layer family context (the report frames
  the airfoil boundary-layer data context for the relations above).
  The Squire-Young relation follows Squire and Young, "The Calculation
  of the Profile Drag of Aerofoils", ARC R&M 1838, 1938, and Schlichting
  Boundary-Layer Theory, 7th ed., McGraw-Hill, pp. 158-162, the
  treatment cited for the method by Coder and Maughmer, "Numerical
  Validation of the Squire-Young Formula for Profile-Drag Prediction",
  Journal of Aircraft 52(3), 2015, pp. 948-955. The equations are
  standard engineering methodology, summary-only per standards-map.yaml,
  and no standards text is reproduced.
- compliance: STANDARDS-REF, gated: false.

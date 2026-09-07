# Wave-45 leaf spec: laminar-far-wake (aerodynamics,
# boundary-layer pack)

- Path: skills/aerodynamics/boundary-layer/laminar-far-wake/
- Pack: boundary-layer (present siblings boundary-layer-theory,
  boundary-layer-transition, boundary-layer-separation,
  rough-wall-skin-friction, stagnation-flow-boundary-layer,
  stokes-creeping-flow-drag, unsteady-laminar-stokes-layers; the new
  leaf is the eighth member; adjacent fences in
  aerodynamics/wind-tunnel/windtunnel-wall-corrections, the wake
  BLOCKAGE correction terms of closed-wall tunnel testing, and
  aerodynamics/wind-tunnel/windtunnel-data-reduction, the raw-run
  pressure-rake reduction leaf).
- Provenance: probe receipt ops/automation/state/wave45-recon/
  task-8-receipt.md GO-3 (rank 3, MED): "Closed-form 2-D laminar far
  wake downstream of a body or flat plate: Goldstein small-defect
  similarity wake (Gaussian cross-stream defect profile, centerline
  defect decaying as x^-1/2, half-width growing as x^1/2), the
  momentum-deficit drag identity D = rho U_inf integral u1 dy across
  the wake (the closed-form basis of wake-survey drag), and the
  far-wake profile shape as a drag diagnostic"; the receipt records
  the wave-43 reserve pool item laminar-far-wake-free-shear (never
  built because reserves were unused) as a prior GO-quality signal.
  ZERO-OWNER GREPS RE-RUN AT SPEC TIME (read-only, 2026-09-07, git
  HEAD 20df81ba): "far-wake|far wake|velocity-defect|velocity defect|
  goldstein" under skills/ returns rc=1 (zero files); the tokens
  far-wake-velocity-defect, wake-momentum-integral,
  centerline-defect-decay and laminar-far-wake appear in 0 corpus
  tasks of eval/hit1-corpus.yaml; the only "wake" owners in the tree
  are the wind-tunnel leaves (blockage-correction content, quoted
  below) plus an incidental stokes-creeping-flow-drag comment
  ("no wake, no separation" as the creeping-flow signature, which
  fences the low-Re sphere leaf AWAY from wake-profile physics).
  GENUINE boundary-layer gap: no leaf owns the downstream free-shear
  wake region; every boundary-layer sibling stops at the attached
  layer or at separation/transition. GO.
- Claim fences (quoted from the sibling frontmatter and body at
  spec time, none owns the far-wake velocity-defect profile or the
  wake-momentum drag identity):
  - boundary-layer-theory (this pack, the attached-layer owner) opens
    "Use when the task is boundary-layer thickness estimation,
    displacement or momentum thickness, skin-friction coefficient on
    a surface, Reynolds-number regime classification, or transition
    location on a smooth surface", and its body restates the fence:
    "Use when the task is flat-plate boundary-layer estimation:
    thickness, displacement and momentum thickness, skin friction,
    and the laminar to turbulent transition", with the Blasius
    laminar plate values (0.664 momentum-thickness and local Cf
    coefficients, 1.7208 displacement thickness, 1.328 average Cf)
    as ATTACHED boundary-layer quantities on the plate surface. The
    leaf never leaves the plate: no downstream wake, no velocity
    defect, no momentum-deficit drag integration. The new leaf
    consumes the plate drag only as the momentum source the wake
    carries and must not claim any attached-layer thickness,
    displacement-thickness or surface skin-friction estimation.
  - boundary-layer-transition and boundary-layer-separation (this
    pack) run their Thwaites traverses along the attached layer and
    stop at the Michel transition onset and the Thwaites lambda
    -0.09 separation flag respectively; neither maps any downstream
    wake state, per the receipt fence quotes. rough-wall-skin-friction
    owns the sand-roughness k-plus turbulent skin-friction
    correlation and trip-strip sizing; stagnation-flow-boundary-layer
    owns the Hiemenz/Homann stagnation-point layer.
  - stokes-creeping-flow-drag (this pack, the wave-44 sibling) opens
    "Use when you must compute the steady low-Reynolds-number viscous
    drag on a sphere in creeping flow" and its claim states the
    creeping flow is fore-aft symmetric with "no wake, no
    separation"; that leaf is the Re << 1 attached-body limit, a
    different regime and geometry from the finite-Reynolds wake
    region the new leaf owns.
  - unsteady-laminar-stokes-layers (this pack) owns the time-
    dependent erfc and oscillating plate layers only.
  - windtunnel-wall-corrections (aerodynamics/wind-tunnel) opens
    "Use when you must apply closed-wall wind tunnel corrections to
    measured lift and drag coefficients: compute solid blockage from
    model volume over the test-section volume scale with K1 = 0.52,
    wake blockage from the uncorrected drag coefficient", with the
    wake-blockage fraction eps_wb = (S_model/(4*C))*CDu a tunnel
    CONSTANT geometry correction. Its "wake" is blockage, a scalar
    correction to the test-section dynamic pressure; it contains no
    wake velocity profile, no cross-stream integration and no
    velocity defect. windtunnel-data-reduction owns raw-run rake
    reduction and uncertainty, not the laminar wake physics.
  Whole-tree greps at spec time confirm the receipt: "wake" appears
  in no aerodynamic leaf outside the two wind-tunnel owners (and the
  incidental stokes comment above), and the wave-45 corpus tokens
  exist nowhere. GENUINE aerodynamics gap, GO.
- Standards id: naca-tr-824 (reference-only, present in
  standards-map.yaml line 171, the boundary-layer pack convention;
  the laminar wake treatment follows Goldstein 1933, Schlichting
  Boundary-Layer Theory (wakes and free-shear-layers chapter, wake
  behind a flat plate) and White Viscous Fluid Flow (laminar free
  shear layers, plane wake defect solution), whose material is cited
  through the report). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Compute the two-dimensional incompressible laminar far wake
downstream of a thin flat plate at zero incidence, the Goldstein
(1933) similarity wake that the attached laminar boundary layers shed
from the trailing edge. The plate of chord c, wetted on both sides
with fully laminar Blasius layers to the trailing edge, carries a
total drag per unit span D = 1.328*rho*U^2*sqrt(nu*c/U) = 2*rho*U^2*
theta_c with theta_c = 0.664*sqrt(nu*c/U) the Blasius momentum
thickness at the trailing edge, and far downstream of the trailing
edge the velocity defect u1 = U - u collapses onto the small-defect
Gaussian similarity profile u1(x, y) = u_c(x)*exp(-B(x)*y^2) with
spread parameter B = U/(4*nu*x) (x measured downstream from the
trailing edge): the exact solution of the linearized wake equation
U*du1/dx = nu*d2u1/dy2 that conserves the momentum deficit. The
centerline defect decays as the inverse square root of downstream
distance, u_c(x) = (D/(rho*U))*sqrt(B/pi) = (0.664*U/sqrt(pi))*
sqrt(c/x), the wake half-width (the y where the defect halves)
grows as the square root of downstream distance, y_half = sqrt(4*nu*
x*ln(2)/U), and the wake-momentum-integral drag identity
D = rho*U*integral_{-inf}^{+inf} u1 dy, the closed-form basis of
wake-survey drag measurement, reproduces the plate drag exactly at
every downstream station. Produces the Gaussian defect profile and
the recovered wake velocity u = U - u1 at any station, the
centerline-defect decay law and its u_c*sqrt(x) invariant, the
half-defect and one-over-e widths with their x^1/2 growth, and the
wake-survey drag and drag coefficient, in SI units, that anchor
laminar wake-profile diagnostics and drag checks downstream of thin
bodies. Does NOT do: attached flat-plate boundary-layer thickness,
displacement-thickness or momentum-thickness estimation on the plate
surface, local or average skin-friction coefficients, transition
location or Reynolds-number-regime classification (boundary-layer-
theory, boundary-layer-transition, boundary-layer-separation); the
Thwaites/Michel/Stratford integral traverses or the roughness k-plus
and trip-strip machinery of the pack siblings; the steady creeping
Stokes sphere flow or the Oseen correction at Reynolds number well
below one (stokes-creeping-flow-drag, which owns "no wake" flow);
the time-dependent unsteady plate Stokes layers
(unsteady-laminar-stokes-layers); the wind-tunnel solid-blockage and
wake-blockage corrections of closed-wall testing or the reduction of
raw rake pressures (windtunnel-wall-corrections, windtunnel-data-
reduction); turbulent wakes, jets, mixing layers, the near-wake
Goldstein error-function solution immediately behind the trailing
edge, axisymmetric wakes or compressible wakes. Incompressible
constant-property laminar flow only, uniform nu and rho, small defect
u1 << U (the linearized far-wake regime, x/c at least of order ten),
two-dimensional, thin-plate small-deficit wakes of a symmetric body
at zero incidence.

## Model (implement exactly)

Pure stdlib, math only, closed form, no iteration, no RNG. Module
constants (air at standard conditions and the worked plate, mirroring
the anchor): NU_AIR = 1.46e-5 (m2/s kinematic viscosity),
RHO_AIR = 1.225 (kg/m3), U_INF = 5.0 (m/s freestream),
PLATE_CHORD = 1.0 (m), BLASIUS_THETA_COEF = 0.664 (Blasius
momentum-thickness coefficient), BLASIUS_DRAG_COEF = 1.328 (the
both-sides average skin-friction drag coefficient, 2*0.664),
SIDES = 2 (plate wetted on both sides). The wake coordinate x is
measured downstream from the trailing edge, y is the cross-stream
coordinate, u1 is the positive velocity defect U - u. Every function
below derives from the defining relations, which are pinned exactly
as written.

Defining relations:
- Trailing-edge state (attached Blasius layer, one side):
  theta_c = 0.664*sqrt(nu*c/U) = 0.664*c/sqrt(Re_c), Re_c = U*c/nu.
- Plate drag per unit span (both sides), the momentum source of the
  wake: D = SIDES*rho*U^2*theta_c = 1.328*rho*U^2*sqrt(nu*c/U);
  drag coefficient C_D = D/(0.5*rho*U^2*c) = 4*theta_c/c =
  2.656/sqrt(Re_c).
- Linearized wake defect equation: U*du1/dx = nu*d2u1/dy2, the
  small-defect (u1 << U) form of the boundary-layer equations in the
  wake, with the momentum invariant D = rho*U*integral_{-inf}^{+inf}
  u1 dy (the wake-momentum-integral drag identity, small-defect
  form; it is exact in the far-wake limit and the closed-form basis
  of wake-survey drag).
- Gaussian similarity profile (the Goldstein far-wake solution of
  the linearized equation): u1(x, y) = u_c(x)*exp(-B(x)*y^2), spread
  parameter B(x) = U/(4*nu*x), which satisfies U*du1/dx =
  nu*d2u1/dy2 identically with B'(x) = -4*nu*B^2/U and u_c'(x)/u_c =
  -2*nu*B/U, hence u_c proportional to x^-1/2.
- Centerline defect from the drag: u_c(x) = (D/(rho*U))*sqrt(B/pi),
  the normalization that makes the momentum identity exact; for the
  two-sided Blasius plate this collapses to the closed form
  u_c(x) = (0.664*U/sqrt(pi))*sqrt(c/x) (the 0.664 Blasius drag
  link with pi-scaled Gaussian spreading; coefficient 0.664/sqrt(pi)
  = 0.3746218835).
- Defect and wake velocity at (x, y): u1 = u_c*exp(-B*y^2) and
  u = U - u1.
- Widths: half-defect width y_half = sqrt(ln(2)/B) (u1 = u_c/2
  there) and one-over-e width y_e = sqrt(1/B) (u1 = u_c*exp(-1)
  there); both grow as x^1/2 since B is proportional to 1/x.
- Momentum integral of the Gaussian: integral u1 dy = u_c*sqrt(pi/B),
  independent of x (equal to D/(rho*U) = 2*U*theta_c at every
  station); the wake-survey drag is D = rho*U*u_c*sqrt(pi/B).
- Full (nonlinear) momentum deficit, documented for honesty:
  rho*integral u*(U - u) dy = rho*(U*integral u1 dy - integral
  u1^2 dy) with integral u1^2 dy = u_c^2*sqrt(pi/(2*B)) closed form
  for the Gaussian; it lies below the linearized identity by a
  relative amount of order u_c/U and converges to it downstream
  (anchor ratios 0.94702046516 at x = 25*c, 0.97351023258 at x =
  100*c, 0.98675511629 at x = 400*c).

Functions (signatures and validation pinned; no imports beyond
math):
- reynolds_number(U, x, nu) -> float. U*x/nu. ValueError if U <= 0,
  x <= 0 or nu <= 0.
- momentum_thickness_blasius(U, x, nu) -> float.
  BLASIUS_THETA_COEF*sqrt(nu*x/U) in m, the attached Blasius
  momentum thickness at running length x (0.664*c/sqrt(Re_c) at the
  trailing edge). ValueError set as reynolds_number.
- plate_drag_per_span(U, rho, nu, c, sides=SIDES) -> float.
  sides*rho*U*U*momentum_thickness_blasius(U, c, nu) in N/m: the
  laminar flat-plate drag per unit span, one side carrying
  rho*U^2*theta_c and the default two-sided plate doubling it.
  ValueError if U <= 0, rho <= 0, nu <= 0, c <= 0 or sides < 1.
- plate_drag_coefficient(U, rho, nu, c) -> float.
  plate_drag_per_span(U, rho, nu, c)/(0.5*rho*U^2*c), the two-sided
  drag coefficient 4*theta_c/c = 2.656/sqrt(Re_c). ValueError set as
  plate_drag_per_span (sides fixed at 2 internally).
- wake_spread_parameter(U, nu, x) -> float. U/(4*nu*x) in 1/m2, the
  Gaussian spread parameter at station x. ValueError if U <= 0,
  nu <= 0 or x <= 0.
- centerline_defect_from_drag(D, rho, U, B) -> float.
  (D/(rho*U))*sqrt(B/pi) in m/s, the centerline velocity defect that
  conserves the momentum deficit D. ValueError if D <= 0, rho <= 0,
  U <= 0 or B <= 0.
- centerline_defect_blasius(U, c, x) -> float.
  (BLASIUS_THETA_COEF*U/sqrt(pi))*sqrt(c/x) in m/s, the closed form
  of centerline_defect_from_drag for the two-sided Blasius plate
  (identical values; anchor residual 0.0). ValueError if U <= 0,
  c <= 0 or x <= 0.
- velocity_defect_gaussian(u_centerline, B, y) -> float.
  u_centerline*exp(-B*y*y) in m/s, the cross-stream defect profile
  at y, always non-negative. ValueError if u_centerline < 0 or
  B <= 0.
- wake_velocity(U, u_centerline, B, y) -> float.
  U - velocity_defect_gaussian(...) in m/s, the recovered wake
  velocity. ValueError if U <= 0, u_centerline < 0 or B <= 0.
- defect_integral(u_centerline, B) -> float.
  u_centerline*sqrt(pi/B) in m2/s, the cross-stream integral of the
  Gaussian defect. ValueError if u_centerline < 0 or B <= 0.
- drag_from_wake(u_centerline, B, rho, U) -> float.
  rho*U*defect_integral(...) in N/m, the wake-survey drag from the
  momentum identity. ValueError if u_centerline < 0, B <= 0,
  rho <= 0 or U <= 0.
- half_defect_width(B) -> float. sqrt(ln(2)/B) in m, the y where the
  defect equals half its centerline value. ValueError if B <= 0.
- one_over_e_width(B) -> float. sqrt(1/B) in m, the y where the
  defect equals u_c*exp(-1). ValueError if B <= 0.
- full_momentum_deficit(rho, U, u_centerline, B) -> float.
  rho*(U*defect_integral(...) - u_centerline^2*sqrt(pi/(2*B))) in
  N/m, the nonlinear wake deficit (documented diagnostic; approaches
  drag_from_wake from below as x grows). ValueError if u_centerline
  < 0, B <= 0, rho <= 0 or U <= 0.

Identities to test (closed-form checks verifiable without the
builder's module):
- Momentum conservation: drag_from_wake(u_c, B, rho, U) equals
  plate_drag_per_span(U, rho, nu, c) exactly to float noise at every
  station (anchor ratio 1.0 at x/c = 25, 100 and 400); equivalently
  defect_integral = D/(rho*U) = 2*U*theta_c = 1.1346436974e-2 m2/s
  at all three stations.
- Centerline decay: u_c(4x)/u_c(x) = 0.5 exactly (x^-1/2 law),
  u_c(2x)/u_c(x) = 1/sqrt(2) = 0.707106781186548, and the invariant
  u_c*sqrt(x) = 1.8731094174 m/s*sqrt(m) is identical at x = 25, 100
  and 400 m (anchor residuals 0.0).
- Spreading: half_defect_width(4x)/half_defect_width(x) = 2 exactly
  (x^1/2 law), wake_spread_parameter(4x)/wake_spread_parameter(x) =
  0.25 exactly, and y_e/y_half = sqrt(1/ln(2)) = 1.2011224087.
- Gaussian shape: velocity_defect_gaussian(u_c, B, y_half)/u_c =
  0.5 exactly, at y_e the ratio is 1/e = 0.367879441171442, and
  wake_velocity at y = 6*y_half is within 1e-9 of U (anchor
  0.999999999999455 at x = 100*c).
- Closed-form equivalence: centerline_defect_from_drag and
  centerline_defect_blasius agree to float noise (anchor 0.0); the
  drag coefficient C_D = 2.656/sqrt(Re_c) = 4*theta_c/c agrees three
  ways (anchor 4.53857479e-3).
- Nonlinear convergence: full_momentum_deficit/plate drag rises from
  0.94702046516 at x = 25*c through 0.97351023258 at x = 100*c to
  0.98675511629 at x = 400*c, monotone toward 1; the linearized
  residual at x = 100*c is 1.8409574184e-3 N/m (2.649 percent of D).
- ValueErrors across the module: U at 0 and negative on every U
  argument; nu at 0 and -1e-5 on reynolds_number,
  momentum_thickness_blasius, plate_drag_per_span, plate_drag_
  coefficient, wake_spread_parameter; rho at 0 on plate_drag_per_
  span, plate_drag_coefficient, drag_from_wake, full_momentum_
  deficit; c at 0 and -1.0 on plate_drag_per_span, plate_drag_
  coefficient, centerline_defect_blasius; x at 0 on reynolds_number,
  wake_spread_parameter, centerline_defect_blasius; sides at 0 on
  plate_drag_per_span; D at 0 and -1.0 on centerline_defect_from_
  drag; B at 0 and -2.0 on every B argument (velocity_defect_
  gaussian, wake_velocity, defect_integral, drag_from_wake,
  half_defect_width, one_over_e_width, full_momentum_deficit);
  u_centerline at -0.1 on velocity_defect_gaussian, wake_velocity,
  defect_integral, drag_from_wake, full_momentum_deficit.
- Determinism; no imports beyond math; closed form, no iteration;
  every function returns identical values on repeated calls.

## Worked example

Air at standard conditions nu = 1.46e-5 m2/s, rho = 1.225 kg/m3, a
flat plate of chord c = 1.0 m at U = 5.0 m/s, wetted on both sides
with fully laminar Blasius boundary layers to the trailing edge. All
values below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_laminar_far_wake.py (stdlib math, closed form,
exit 0, byte-identical under /usr/bin/python3 and
~/.pyenv/versions/3.13.12/bin/python3).
- Trailing-edge state:
  - Re_c = U*c/nu = 342465.7534, the chord Reynolds number of the
    fully laminar plate.
  - Momentum thickness at the trailing edge (one side) theta_c =
    0.664*sqrt(nu*c/U) = 1.1346436974e-3 m (1.135 mm).
  - Total drag per unit span, both sides: D = 1.328*rho*U^2*sqrt(nu*
    c/U) = 2*rho*U^2*theta_c = 6.9496926464e-2 N/m, the momentum
    source the far wake carries.
  - Drag coefficient C_D = D/(0.5*rho*U^2*c) = 0.00453857479,
    identical to 2.656/sqrt(Re_c) = 0.00453857479 and to
    4*theta_c/c = 0.00453857479 (three routes agree).
- Far-wake traverse at x = 100*c = 100.0 m downstream of the
  trailing edge (centerline defect 3.75 percent of U, solidly in the
  small-defect regime):
  - Spread parameter B = U/(4*nu*x) = 8.5616438356e2 1/m2.
  - Centerline defect u_c = (D/(rho*U))*sqrt(B/pi) = 0.18731094174
    m/s, i.e. u_c/U = 0.03746218835 (3.746 percent), identical to
    the closed form (0.664*U/sqrt(pi))*sqrt(c/x) = 0.18731094174
    m/s.
  - Widths: half-defect width y_half = sqrt(ln(2)/B) =
    2.8453398864e-2 m (2.845 cm) and one-over-e width y_e =
    sqrt(1/B) = 3.4176014981e-2 m (3.418 cm); the ratio
    y_e/y_half = 1.2011224087 = sqrt(1/ln(2)).
  - Profile values: u1(y_half) = 9.3655470869e-2 m/s (exactly u_c/2),
    u1(y_e) = 6.8907844572e-2 m/s (u_c*exp(-1)), and the recovered
    wake-axis velocity u(0) = U - u_c = 4.8126890583 m/s; at
    y = 6*y_half = 0.170720393184 m the wake is indistinguishable
    from the freestream, u/U = 0.999999999999455.
  - Momentum integral: integral u1 dy = u_c*sqrt(pi/B) =
    1.1346436974e-2 m2/s, equal to D/(rho*U) and to 2*U*theta_c at
    every station; the wake-survey drag D = rho*U*integral u1 dy =
    6.9496926464e-2 N/m equals the plate drag to float noise (ratio
    1.0, anchor printed exactly 1).
- Decay and spreading across stations:
  - Centerline defect: 0.37462188348 m/s at x = 25*c (7.492 percent
    of U), 0.18731094174 m/s at x = 100*c, 0.093655470869 m/s at
    x = 400*c (1.873 percent of U): u_c(4x)/u_c(x) = 0.5 exactly and
    the invariant u_c*sqrt(x) = 1.8731094174 is unchanged across the
    three stations (x^-1/2 decay).
  - Half-defect width: 1.4226699432e-2 m at x = 25*c,
    2.8453398864e-2 m at x = 100*c, 5.6906797727e-2 m at x = 400*c:
    y_half(4x)/y_half(x) = 2 exactly (x^1/2 spreading).
  - Momentum conservation at every station: D_wake/D_plate = 1.0 at
    x/c = 25, 100 and 400.
  - Nonlinear-form honesty check: the full deficit rho*integral
    u*(U-u) dy lies 5.29795348 percent below D at x = 25*c
    (ratio 0.94702046516), 2.64897674 percent below at x = 100*c
    (ratio 0.97351023258, residual 1.8409574184e-3 N/m) and
    1.32448837 percent below at x = 400*c (ratio 0.98675511629),
    converging to the linearized identity as the wake spreads.
- Read-off: a 1 m fully laminar plate at 5 m/s in air drags
  6.95e-2 N per metre of span; 100 m downstream the wake axis runs
  3.75 percent slow inside a Gaussian defect 2.85 cm wide at half
  depth, the integrated momentum deficit of that Gaussian recovers
  the plate drag exactly, and doubling the downstream distance halves
  the centerline defect while the wake grows by the square root of
  the distance. A wake-survey traverse at x/c = 100 integrated with
  the identity D = rho*U*integral u1 dy reports the drag without any
  force balance.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w45spec/
anchor_laminar_far_wake.py (stdlib math, closed form, exit 0).

## Validation list (contract test must include)

- reynolds_number(5.0, 1.0, 1.46e-5) = 342465.7534 within 1e-6
  relative.
- momentum_thickness_blasius(5.0, 1.0, 1.46e-5) = 1.1346436974e-3 m
  within 1e-6 relative; equals 0.664*1.0/sqrt(Re_c) within 1e-9
  relative; equals 0.664*sqrt(1.46e-5*1.0/5.0) within 1e-12
  relative.
- plate_drag_per_span(5.0, 1.225, 1.46e-5, 1.0) = 6.9496926464e-2
  N/m within 1e-6 relative (magnitude bound: between 6.5e-2 and
  7.5e-2 N/m); one-sided value (sides=1) equals rho*U^2*theta_c
  within 1e-9 relative; the sides=2 value is exactly 2 times the
  sides=1 value within 1e-12.
- plate_drag_coefficient(5.0, 1.225, 1.46e-5, 1.0) = 4.53857479e-3
  within 1e-6 relative; equals 2.656/sqrt(Re_c) within 1e-9
  relative; equals 4*theta_c/c within 1e-9 relative.
- wake_spread_parameter(5.0, 1.46e-5, 100.0) = 8.5616438356e2 1/m2
  within 1e-6 relative; at x = 400.0 it is 2.1404109589e2 within
  1e-6 relative and exactly one quarter of the x = 100.0 value
  within 1e-12.
- centerline_defect_from_drag(6.9496926464e-2, 1.225, 5.0,
  8.5616438356e2) = 0.18731094174 m/s within 1e-6 relative;
  centerline_defect_blasius(5.0, 1.0, 100.0) = 0.18731094174 m/s
  within 1e-6 relative and the two functions agree within 1e-12
  relative; u_c/U = 0.03746218835 within 1e-6; the invariant
  u_c*sqrt(x) = 1.8731094174 within 1e-6 relative at x = 25.0,
  100.0 and 400.0 m.
- Decay and spreading laws: u_c(4x)/u_c(x) = 0.5 within 1e-12;
  u_c(2x)/u_c(x) = 0.707106781186548 within 1e-12;
  half_defect_width(4x)/half_defect_width(x) = 2 within 1e-12;
  wake_spread_parameter(4x)/wake_spread_parameter(x) = 0.25 within
  1e-12.
- Gaussian shape at x = 100.0 m: half_defect_width(B) =
  2.8453398864e-2 m within 1e-6 relative; one_over_e_width(B) =
  3.4176014981e-2 m within 1e-6 relative; y_e/y_half =
  1.2011224087 within 1e-9;
  velocity_defect_gaussian(u_c, B, y_half)/u_c = 0.5 within 1e-12;
  velocity_defect_gaussian(u_c, B, y_e)/u_c = 0.367879441171442
  within 1e-12; wake_velocity(5.0, u_c, B, 0.0) = 4.8126890583 m/s
  within 1e-6 relative; wake_velocity at y = 6*y_half within 1e-9
  relative of U.
- Momentum identity: defect_integral(u_c, B) = 1.1346436974e-2 m2/s
  within 1e-6 relative at x = 25.0, 100.0 and 400.0 m; equals
  2*U*theta_c within 1e-9 relative and D/(rho*U) within 1e-12;
  drag_from_wake(u_c, B, 1.225, 5.0) = 6.9496926464e-2 N/m within
  1e-6 relative and equals plate_drag_per_span(5.0, 1.225, 1.46e-5,
  1.0) within 1e-9 relative at all three stations.
- Nonlinear diagnostic: full_momentum_deficit(rho, U, u_c, B)/
  plate_drag_per_span = 0.94702046516 at x = 25.0 m, 0.97351023258
  at x = 100.0 m and 0.98675511629 at x = 400.0 m, each within 1e-6
  relative, and the sequence is monotone increasing; the linearized
  residual drag_from_wake - full_momentum_deficit = 1.8409574184e-3
  N/m at x = 100.0 m within 1e-6 relative.
- ValueErrors: U at 0 and -0.01 on every U argument (reynolds_number,
  momentum_thickness_blasius, plate_drag_per_span, plate_drag_
  coefficient, centerline_defect_from_drag, centerline_defect_
  blasius, wake_velocity, drag_from_wake, full_momentum_deficit);
  nu at 0 and -1e-5 on reynolds_number, momentum_thickness_blasius,
  plate_drag_per_span, plate_drag_coefficient and wake_spread_
  parameter; rho at 0 on plate_drag_per_span, plate_drag_
  coefficient, centerline_defect_from_drag, drag_from_wake and
  full_momentum_deficit; c at 0 on plate_drag_per_span, plate_drag_
  coefficient and centerline_defect_blasius; x at 0 on
  reynolds_number, wake_spread_parameter and centerline_defect_
  blasius; x at 0 on wake_spread_parameter with nu = 1.46e-5; D at 0
  and -1.0 on centerline_defect_from_drag; B at 0 and -2.0 on
  velocity_defect_gaussian, wake_velocity, defect_integral,
  drag_from_wake, half_defect_width, one_over_e_width and
  full_momentum_deficit; u_centerline at -0.1 on velocity_defect_
  gaussian, wake_velocity, defect_integral, drag_from_wake and
  full_momentum_deficit; sides at 0 on plate_drag_per_span.
- Determinism: every function called twice returns bit-identical
  values; no imports beyond math; no random or time-dependent
  content; closed form, no iteration anywhere.
- Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
  ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
  computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (eval/hit1-wave45-laminar-far-wake.yaml)

Query 1 (copy verbatim):
  "compute the drag of the thin plate from the measured laminar
  far-wake velocity-defect profile at the traverse station: integrate
  the momentum deficit across the wake with the wake-momentum-
  integral identity and report the drag coefficient"
  intent: "aerodynamics; laminar free-shear far wake in the viscous
  boundary-layer vein: velocity-defect profile of the Gaussian
  laminar far wake behind a thin plate, wake-momentum-integral drag
  identity D = rho*U*integral u1 dy as the closed-form basis of
  wake-survey drag, drag coefficient from the integrated momentum
  deficit"
  expected_skill: "aerodynamics/boundary-layer/laminar-far-wake"
Query 2 (copy verbatim):
  "predict the laminar far-wake velocity-defect profile downstream of
  the flat plate: the Gaussian similarity defect shape, the
  centerline-defect decay with downstream distance, and the wake
  half-width growth from the similarity solution"
  intent: "aerodynamics; Goldstein laminar far-wake similarity behind
  a flat plate: Gaussian cross-stream velocity-defect profile with
  spread parameter U/(4*nu*x), centerline defect decaying as x^-1/2,
  wake half-width growing as x^1/2, linking the far-wake traverse to
  the laminar Blasius trailing-edge momentum state"
  expected_skill: "aerodynamics/boundary-layer/laminar-far-wake"
Task ids: w45-laminar-far-wake-1 and -2. The queries stay inside the
aerodynamics viscous-flow vein and carry the distinctive leaf tokens
(far-wake-velocity-defect, wake-momentum-integral,
centerline-defect-decay, laminar-far-wake, half-width growth) that
exist on no router row or leaf today: the spec-time greps found the
tokens in 0 corpus tasks and 0 files under skills/. The wind-tunnel
wake tasks in the corpus route on wake-blockage and solid-blockage
tokens to windtunnel-wall-corrections and share no velocity-defect
content; the boundary-layer sibling tasks route on their own
attached-layer tokens (momentum-thickness and displacement-thickness
estimation on the surface for boundary-layer-theory, thwaites and
michel for the transition and separation leaves), so both queries
above are collision-free. Corpus wording deliberately avoids
surface-skin-friction, transition, separation, blockage and
creeping-flow phrasing that the siblings own.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the two-dimensional
laminar far-wake velocity-defect profile and drag downstream of a
thin flat plate or slender body at zero incidence, the Goldstein 1933
similarity wake:" and include the outputs in the Claim. First tag:
laminar-far-wake. Additional tags ONLY: far-wake-velocity-defect,
wake-momentum-integral, velocity-defect-profile, wake-survey-drag.
NEVER single generic words (wake, drag, profile, boundary, layer,
velocity, defect, plate, blasius, goldstein, similarity) and NEVER
the sibling-owned tokens displacement-thickness, momentum-thickness,
skin-friction-coefficient, transition-location, reynolds-number-
regime, thwaites-integral, michel-criterion, stratford, k-plus,
sand-roughness, trip-strip (the boundary-layer pack siblings,
boundary-layer-theory, boundary-layer-transition, boundary-layer-
separation, rough-wall-skin-friction); stokes-drag, creeping-flow,
oseen-correction, terminal-velocity, stokes-streamfunction (stokes-
creeping-flow-drag); rayleigh-layer, oscillating-plate-layer,
penetration-depth (unsteady-laminar-stokes-layers); solid-blockage,
wake-blockage, wall-interference, corrected-drag-coefficient,
test-section-constraint (windtunnel-wall-corrections). 50-150 words,
<=1000 chars, no em dash, action verb present (compute). The
description must not assign flow regimes, transition classes or any
categorical verdict. Recommended wording:
"Use when you must compute the two-dimensional laminar far-wake
velocity-defect profile and drag downstream of a thin flat plate or
slender body at zero incidence, the Goldstein 1933 similarity wake:
evaluate the Gaussian cross-stream velocity-defect profile with the
spread parameter U/(4*nu*x), the centerline-defect decay as x^-1/2
and the wake half-width growth as x^1/2 downstream of the trailing
edge, integrate the momentum deficit across the wake with the
wake-momentum-integral drag identity D = rho*U*integral u1 dy to
recover the plate drag, and link the far-wake traverse to the laminar
Blasius trailing-edge momentum state with the 0.664 constant.
Produces the wake velocity-defect and recovered-velocity profiles,
the decay and spreading laws and the wake-survey drag in SI units
that anchor laminar wake diagnostics and drag checks. Trigger:
laminar-far-wake, far-wake-velocity-defect, wake-momentum-integral,
velocity-defect-profile, wake-survey-drag."

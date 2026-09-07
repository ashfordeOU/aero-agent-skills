# Wave-45 leaf spec: squire-young-profile-drag (aerodynamics, boundary-layer pack)

- Path: skills/aerodynamics/boundary-layer/squire-young-profile-drag/
- Pack: boundary-layer (7 leaves present at prep per the wave-45 disk
  split: boundary-layer-separation, boundary-layer-theory,
  boundary-layer-transition, rough-wall-skin-friction,
  stagnation-flow-boundary-layer, stokes-creeping-flow-drag,
  unsteady-laminar-stokes-layers; squire-young-profile-drag is the
  wave-45 boundary-layer addition). Adjacent fences:
  aerodynamics/drag-polars/parasite-drag owns the whole-aircraft CD0
  buildup and aerodynamics/airfoil/xfoil-analysis is the numerical
  polar tool-adjacent leaf with no closed-form section formula.
  Flight-mechanics/performance/rotorcraft-blade-element-hover-
  performance and rotorcraft-forward-flight-performance (flight-
  mechanics family) use the phrase profile drag for rotor-blade
  profile power, a different family and context.
- Claim fences (quoted from the sibling frontmatter and bodies at
  prep; no sibling maps a trailing-edge momentum state to a section
  profile-drag coefficient):
  - boundary-layer-transition (this pack) opens "Use when you must
    predict the laminar-turbulent transition location on a
    two-dimensional body from its edge-velocity distribution: grow the
    laminar boundary layer with the Thwaites integral relation to
    obtain the boundary-layer momentum deficit at each station, build
    the local Reynolds numbers from the edge velocity and that deficit,
    evaluate the Michel transition criterion against them, and
    interpolate the first station where the criterion is crossed to
    give the transition location", and its whole claim is the Michel
    natural-transition onset: "no roughness, sweep or suction inputs
    and no Tollmien-Schlichting wave-growth integration; the Michel
    criterion replaces an eN envelope". Its Thwaites traverse stops at
    the onset crossing; nothing in its SKILL.md, logic or contract test
    maps the TE momentum state to a drag coefficient or evaluates the
    Squire-Young trailing-edge relation (fresh probe: zero occurrences
    of squire, profile drag and trailing edge in the leaf).
  - boundary-layer-separation (this pack) "grows the laminar layer
    with the Thwaites integral relation along the edge-velocity
    traverse and flags the first station where the Thwaites lambda
    parameter crosses -0.09, the classical laminar separation
    criterion, and evaluates the Stratford-style pressure recovery
    criterion to estimate the turbulent separation station and the
    margin below the 0.35 threshold". Its claim ends at the separation
    signal; zero occurrences of squire, profile drag and trailing edge
    in the leaf (fresh probe). The new leaf runs an integral growth of
    theta to the TE and maps it to drag, with no lambda traverse, no
    separation flag and no Stratford recovery content.
  - boundary-layer-theory (this pack) owns the steady flat-plate layer
    definitions and correlations: its Domain quick reference states
    "integral_0^inf (u / U_e) * (1 - u / U_e) dy is the momentum
    deficit" and it carries the Blasius and 1/7-power thicknesses and
    skin-friction coefficients, Reynolds-number regime and transition
    location on a smooth surface. Flat plate only: it produces no
    section profile-drag coefficient from a TE momentum state and no
    Squire-Young mapping. The new leaf uses the Blasius constants
    0.664 and 1.328 only as the closed-form zero-pressure-gradient
    identity targets of its own TE mapping, never to compute surface
    skin-friction distributions or regime classes.
  - parasite-drag (aerodynamics/drag-polars) opens "Use when the task
    is drag buildup, zero-lift drag estimation, the wetted-area method,
    skin-friction coefficients, form factor, interference factor, or
    equivalent skin-friction coefficient in a preliminary drag
    assessment", and builds the whole-aircraft CD0 as the sum of
    Cf * FF * Q * S_wet/S_ref over components. It uses the flat-plate
    laminar Cf = 1.328/sqrt(Re) inside that buildup and never computes
    a section profile-drag coefficient from a boundary-layer momentum
    state at a trailing edge.
  - xfoil-analysis (aerodynamics/airfoil) is the numerical viscous
    polar tool leaf: an XFOIL-style run produces polars, no closed-form
    Squire-Young formula.
  - The two rotorcraft performance leaves (flight-mechanics family)
    name profile drag only as rotor-blade profile drag inside the
    blade-element hover and momentum-theory forward-flight power
    balances; the single corpus task carrying the phrase "profile
    drag" (line 3947 of eval/hit1-corpus.yaml) is the rotorcraft
    forward-flight power sweep routing to
    rotorcraft-forward-flight-performance, no section boundary-layer
    content.
  Whole-tree greps at prep (real runs for this spec, repo HEAD
  20df81bae):
  "squire" = 0 hits in skills/ (grep exit 1), 0 hits in
  eval/hit1-corpus.yaml, and no router row in skills/aerodynamics/
  SKILL.md; "squire-young" = 0 hits under skills/, eval/ and docs/;
  "profile-drag|profile drag" = only the two flight-mechanics
  rotorcraft leaves quoted above and the one rotorcraft corpus task;
  "trailing-edge|trailing edge" appears in aerodynamic leaves only as
  geometry or flap terminology (high-lift-systems, airfoil-geometry,
  airfoil-optimization, supercritical-airfoil, panel-method,
  wing-planform-design, ackeret-linearized-supersonic, control-surface
  leaves) with no drag-from-momentum-state content; the hyphenated
  "wake-survey|wake rake|momentum-deficit" tokens = 0 hits in skills/
  (grep exit 1). The unhyphenated phrase momentum deficit appears in
  boundary-layer-theory (the theta definition quoted above) and in the
  boundary-layer-transition description as the name of theta itself,
  never as a TE-to-drag or wake mapping. The receipt's probe greps at
  HEAD 5cc8fef3 returned the same zero-owner result for squire and the
  drag tokens. GENUINE boundary-layer gap (GO-2 of the wave-45 probe
  receipt, task-8): no leaf owns the Squire-Young trailing-edge
  profile-drag mapping, the edge-velocity-ratio exponent, or the
  fully laminar TE-drag chain; boundary-layer-separation and
  boundary-layer-transition stop their traverses at the separation
  flag and the Michel onset and never map the TE momentum state to
  drag.
- Standards id: naca-tr-824 (reference-only, present in
  standards-map.yaml line 171, the sibling precedent for the whole
  boundary-layer pack; the Squire-Young method follows Squire and
  Young, "The Calculation of the Profile Drag of Aerofoils", ARC R&M
  1838, 1938, and Schlichting, Boundary-Layer Theory, 7th ed.,
  McGraw-Hill, pp. 158-162, the treatment cited for the method by
  Coder and Maughmer, "Numerical Validation of the Squire-Young
  Formula for Profile-Drag Prediction", Journal of Aircraft 52(3),
  2015, pp. 948-955; the report frames the boundary-layer data
  context, the relations above are standard engineering methodology,
  summary-only). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Compute the section profile-drag coefficient of a two-dimensional
body or airfoil from the boundary-layer momentum state at its
trailing edge with the Squire-Young formula (Squire and Young, ARC
R&M 1838, 1938; Schlichting, Boundary-Layer Theory, pp. 158-162;
validated against surface-integrated CFD within 2-3 percent in the
low-drag range by Coder and Maughmer, Journal of Aircraft 52(3),
2015):

    c_d,p = 2 * (theta_TE / c) * (U_TE / U_inf) ** ((H_TE + 5) / 2)

with theta_TE the boundary-layer momentum thickness at the trailing
edge, c the chord, U_TE the edge velocity at the trailing edge, U_inf
the freestream velocity, and H_TE = delta*_TE/theta_TE the trailing-
edge shape factor, documented at about 1.4 for the trailing-edge
layer in standard profile-drag practice (the exponent then reads
(H_TE + 5)/2 = 3.2). The trailing-edge factor
(U_TE/U_inf)**((H_TE+5)/2) transfers the TE momentum state to the
far-wake drag level: it is unity on a flat plate (U_TE = U_inf) where
the formula reduces exactly to the momentum-integral value
2*theta_TE/c, and below unity when the TE edge velocity lies below
the freestream, the attached-flow case of a closed section. The
zero-pressure-gradient reduction is the leaf's deterministic anchor:
with U_TE = U_inf and theta_TE at the Blasius laminar value
0.664*c/sqrt(Re_c), the formula reproduces the Blasius flat-plate
drag 1.328/sqrt(Re_c) exactly. For the fully laminar chain the leaf
grows the momentum thickness to the trailing edge on the laminar
integral growth relation theta_TE^2 = GROWTH_C * nu/U_TE^6 *
integral_0^c Ue^5 dx (constant pinned so the zero-pressure-gradient
plate closes to the Blasius value exactly, GROWTH_C = 0.664^2 =
0.440896, distinct from the 0.45 Thwaites constant the transition and
separation traverses embed for their Michel and lambda criteria), then
applies the Squire-Young mapping. Produces the section
profile-drag-coefficient, the trailing-edge momentum thickness and
the edge-velocity-ratio factor that gate airfoil section drag
estimates, fully laminar low-Reynolds drag checks and boundary-layer
TE-state validation. Does NOT do: the Thwaites lambda traverse with
the -0.09 laminar separation flag or the Stratford 0.35 turbulent
separation criterion (boundary-layer-separation); the Michel
transition criterion, transition location or eN replacement
(boundary-layer-transition); flat-plate thickness, displacement or
momentum-thickness correlations, local or average skin-friction
coefficients, Reynolds-number regime assignment or transition
location on a smooth surface (boundary-layer-theory); the
whole-aircraft parasite-drag buildup with form factors, interference
factors, wetted areas or the CD0 term (parasite-drag); numerical
XFOIL-style polar runs (xfoil-analysis); rotor-blade profile drag
inside a rotorcraft power balance (the flight-mechanics rotorcraft
leaves); wake-survey or wake-rake instrumentation methods, and no
turbulent or mixed-laminar-turbulent boundary-layer growth model, no
compressibility, roughness, sweep or suction inputs. Incompressible
clean 2-D attached flow only, one surface of the section at a time
(for a symmetric section at zero lift the total is twice the
one-surface value when both surfaces share the TE state); SI units
throughout, x in m, U in m/s, nu in m2/s, theta in m, c_d,p
dimensionless.

## Model (implement exactly)

Pure stdlib, math only, closed form. Module constants (fixed numbers):

- NU_AIR = 1.46e-5 (m2/s air kinematic viscosity, the family value
  used by the worked example).
- H_TE = 1.4 (default trailing-edge shape factor H = delta*/theta,
  documented at about 1.4).
- LAMINAR_THETA_C = 0.664 (Blasius momentum-thickness constant:
  theta = 0.664*x/sqrt(Re_x) on the laminar flat plate).
- BLASIUS_DRAG_C = 1.328 (= 2*0.664, the laminar flat-plate drag
  constant of the identity 1.328/sqrt(Re_c)).
- GROWTH_C = 0.664**2 = 0.440896 (the laminar integral-growth
  constant, pinned so the zero-pressure-gradient plate closes to the
  Blasius momentum thickness exactly; note the sibling Thwaites
  constant 0.45 would run the flat-plate theta sqrt(0.45)/0.664 =
  1.010271676, about 1.03 percent high, because the siblings' theta
  feeds the Michel criterion while this leaf's theta feeds the drag
  mapping anchored at Blasius exactness).

Defining relations, pinned exactly as written:
- Squire-Young profile drag: c_d,p = 2*(theta_TE/c)*
  (U_TE/U_inf)**((H_TE+5)/2), one surface of the section.
- Edge-velocity factor: f = (U_TE/U_inf)**((H_TE+5)/2), unity at
  U_TE = U_inf for any H_TE (the flat plate), below unity for
  U_TE < U_inf, the attached-flow band of a closed section; the
  exponent is (H_TE+5)/2 = 3.2 at the default H_TE = 1.4.
- Zero-pressure-gradient reduction: at U_TE = U_inf the formula is
  c_d,p = 2*theta_TE/c, and with the Blasius TE momentum thickness
  theta_TE = 0.664*c/sqrt(Re_c) it reproduces the Blasius flat-plate
  drag 2*theta_TE/c = 1.328/sqrt(Re_c) exactly (the receipt's
  deterministic anchor, independent of H_TE because the velocity
  ratio is unity).
- Laminar integral growth of theta to the trailing edge:
  theta_TE^2 = GROWTH_C * nu / U_TE**6 * integral_0^c Ue(x)**5 dx,
  evaluated by the cumulative trapezoid rule over the supplied
  stations; the segment from the leading edge (x = 0) to the first
  station keeps Ue at its first-station value, so the constant-
  velocity plate is exact. For the linear edge-velocity law
  Ue(x) = U_inf*(1 - a*x/c) the integral is closed form:
  theta_TE = sqrt(GROWTH_C * nu * U_inf**5 * c * (1 - (1-a)**6) /
  (6*a) / U_TE**6) with U_TE = U_inf*(1 - a).
- Fully laminar chain: grow theta to the TE on the relation above,
  read U_TE from the traverse (the last station edge velocity), then
  apply the Squire-Young mapping with the default or supplied H_TE.

Functions (signatures, return shapes and ValueError rejections pinned;
no imports beyond math):
- trailing_edge_factor(u_te, u_inf, h_te=H_TE) -> float
  (u_te/u_inf)**((h_te+5.0)/2.0), dimensionless. ValueError if
  u_te <= 0, u_inf <= 0, or h_te <= 1.0 (a shape factor at or below
  1 is not an attached boundary layer; the realistic band runs from
  about 1.2 to about 2.6).
- squire_young_profile_drag(theta_te, chord, u_te, u_inf,
  h_te=H_TE) -> float
  2.0*(theta_te/chord)*trailing_edge_factor(u_te, u_inf, h_te),
  dimensionless, one surface. ValueError if theta_te <= 0 or
  chord <= 0 plus the trailing_edge_factor set.
- momentum_thickness_at_te(xs, ues, nu) -> float
  theta_TE in m from the laminar integral growth relation, trapezoid
  rule with the leading-edge-gap convention above, evaluated at the
  last station. ValueError if fewer than two stations, unequal
  station and velocity lengths, xs[0] < 0, stations not strictly
  increasing, any edge velocity <= 0, or nu <= 0.
- fully_laminar_profile_drag(xs, ues, nu, chord, u_inf,
  h_te=H_TE) -> float
  the one-call chain: theta_TE = momentum_thickness_at_te(xs, ues,
  nu), then squire_young_profile_drag(theta_TE, chord, ues[-1],
  u_inf, h_te). ValueError if chord <= 0 or u_inf <= 0 plus the
  momentum_thickness_at_te set.

Identities to test (closed form, verifiable without the builder's
module):
- The anchor identity: with U_TE = U_inf and theta_TE =
  0.664*c/sqrt(Re_c), the formula returns 1.328/sqrt(Re_c) exactly;
  at c = 1 m, U = 30 m/s, nu = 1.46e-5 (Re_c = 2.0547945205e6) the
  residual between squire_young_profile_drag(4.6321634974e-4, 1.0,
  30.0, 30.0, h_te) and 1.328/sqrt(Re_c) is 0.0 for any h_te above 1.
- Zero-pressure-gradient factor: trailing_edge_factor(U, U, h_te) =
  1.0 to float noise for any h_te (math: 1.0**x = 1.0 exactly).
- Chain equals identity on the flat plate: the fully laminar chain on
  a constant-velocity traverse returns 1.328/sqrt(Re_c) within 1e-9
  relative (anchor rel residual 3.066e-14), because GROWTH_C = 0.664^2
  makes the growth close to the Blasius theta exactly.
- Blasius growth: momentum_thickness_at_te on a constant-velocity
  traverse equals 0.664*c/sqrt(Re_c) within 1e-9 relative (anchor rel
  residual 3.066e-14), the trapezoid integral being exact for constant
  Ue.
- Reynolds invariance: on the flat plate c_d,p*sqrt(Re_c) = 1.328
  within 1e-9 at Re_c and at Re_c/2 (anchor value 1.3280000000 at both,
  rel residual 3.060e-14).
- Linear-law closed form: for Ue(x) = U_inf*(1 - a*x/c) the
  quadrature theta matches the exact integral above within 1e-6
  relative at 1001 stations or more (anchor residual 3.220e-13 m,
  rel 5.734e-10 at 4001 stations).
- Algebra: squire_young_profile_drag(...) equals
  2.0*(theta_te/chord)*trailing_edge_factor(...) to float noise
  (anchor residual 0.0).
- Factor scaling: f(h2)/f(h1) = (U_TE/U_inf)**((h2-h1)/2) exactly;
  f(0.9, 1.4) = 0.9**3.2 = 0.71379915616 and f(0.9, 2.6) =
  0.9**3.8 = 0.67007210063 (the laminar-to-turbulent H band moves the
  factor by about 6.1 percent at ratio 0.9).
- ValueErrors across the module: every non-physical input listed
  under the functions raises ValueError (anchor: 13 of 13 expected).
- Determinism; no imports beyond math; closed form with a single
  deterministic quadrature, no iteration, no RNG.

## Worked example

Air at standard conditions nu = 1.46e-5 m2/s, chord c = 1.0 m,
freestream U_inf = 30.0 m/s, so Re_c = U_inf*c/nu = 2.0547945205e6.
The traverse grids use 4001 stations (step 2.5e-4 m). All values
below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_squire_young_profile_drag.py (stdlib math,
closed form, exit 0, run from ~/AeroSkills with python3).

- Case A, direct formula from a TE momentum state: one-surface
  theta_TE = 3.0e-3 m at the trailing edge (theta_TE/c = 0.003),
  U_TE = 27.0 m/s (edge-velocity ratio 0.9), H_TE = 1.4:
  - trailing_edge_factor(27.0, 30.0, 1.4) = 0.71379915616, the
    (U_TE/U_inf)**3.2 wake-transfer factor, below unity because the
    TE edge flow still has pressure to recover.
  - Raw momentum value 2*theta_TE/c = 6.0e-3; the Squire-Young
    estimate squire_young_profile_drag(3.0e-3, 1.0, 27.0, 30.0, 1.4)
    = 4.2827949370e-3 one surface, and 8.5655898739e-3 for both
    surfaces of a symmetric section at zero lift sharing the TE
    state.
  - H sensitivity: trailing_edge_factor(27.0, 30.0, 2.6) =
    0.67007210063 (the laminar shape-factor value would lower the
    one-surface estimate to 4.0204326038e-3, 6.1 percent below the
    H_TE = 1.4 value at this velocity ratio).
- Case B, the anchor identity on the fully laminar flat plate
  (U_TE = U_inf = 30.0 m/s, zero pressure gradient):
  - Blasius TE momentum thickness theta_TE = 0.664*c/sqrt(Re_c) =
    4.6321634974e-4 m.
  - Reference drag 1.328/sqrt(Re_c) = 9.2643269948e-4.
  - squire_young_profile_drag(4.6321634974e-4, 1.0, 30.0, 30.0, 1.4)
    = 9.2643269948e-4, identity residual 0.0 (the formula reproduces
    the Blasius flat-plate drag exactly when U_TE = U_inf).
  - Chain end to end: momentum_thickness_at_te over the 4001-station
    constant-30 m/s plate = 4.6321634974e-4 m (rel 3.066e-14 against
    the Blasius value) and fully_laminar_profile_drag(...) =
    9.2643269948e-4 (rel 3.066e-14 against 1.328/sqrt(Re_c)): the
    fully laminar chain reproduces the Blasius drag on the plate.
  - Reynolds invariance: c_d,p*sqrt(Re_c) = 1.3280000000 at Re_c and
    at Re_c/2 (U = 15 m/s), rel residual 3.060e-14.
- Case C, the fully laminar 2-D section at low Reynolds number with a
  decelerated edge flow Ue(x) = 30.0*(1 - 0.1*x/c) m/s over
  x in [0, 1] m (U_TE/U_inf = 0.9 at the TE), H_TE = 1.4:
  - momentum_thickness_at_te over the 4001-station traverse =
    5.6151694776e-4 m; the closed form of the linear law,
    sqrt(GROWTH_C*nu*U_inf**5*c*(1-0.9**6)/(6*0.1)/27.0**6) =
    5.6151694744e-4 m, quadrature residual 3.220e-13 m
    (rel 5.734e-10): the integral growth closes to the exact integral.
  - Raw momentum value 2*theta_TE/c = 1.1230338955e-3, above the flat
    plate's 9.2643269948e-4 because the deceleration thickens the
    layer; the Squire-Young mapping
    fully_laminar_profile_drag(xs, ues, 1.46e-5, 1.0, 30.0, 1.4) =
    8.0162064696e-4, identical to the hand recomputation
    2*(theta_TE/c)*(0.9)**3.2 = 8.0162064696e-4 (residual 0.0).
  - The exponent factor carries the whole difference between the raw
    momentum value and the drag estimate: 0.71379915616 at
    U_TE/U_inf = 0.9 and H_TE = 1.4, versus unity on the flat plate.
- Read-off: a section whose TE layer carries theta_TE/c = 0.003 at an
  edge-velocity ratio 0.9 and H_TE = 1.4 has a Squire-Young
  profile-drag coefficient of 4.283e-3 per surface (8.566e-3 total at
  zero lift), 29 percent below the raw 2*theta_TE/c momentum value
  6.0e-3; the fully laminar flat plate at Re_c = 2.0548e6 lands
  exactly on the Blasius value 9.264e-4 through both the direct
  formula and the integral-growth chain, and a fully laminar section
  whose edge flow decelerates 10 percent over the chord grows theta_TE
  to 5.615e-4 m (raw 2*theta_TE/c = 1.123e-3) before the
  edge-velocity-ratio factor 0.7138 brings the estimate to
  8.016e-4. The flat-plate equality and the 1.328/sqrt(Re_c)
  reproduction are the deterministic contract anchors: no external
  data is needed to verify the leaf.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w45spec/anchor_squire_young_profile_drag.py (stdlib math,
closed form, exit 0).

## Validation list (contract test must include)

- trailing_edge_factor(27.0, 30.0, 1.4) = 0.71379915616 within 1e-8;
  trailing_edge_factor(30.0, 30.0, 1.4) and (30.0, 30.0, 2.6) within
  1e-12 of 1.0 (the flat-plate factor is unity for any shape factor);
  trailing_edge_factor(27.0, 30.0, 2.6) = 0.67007210063 within 1e-8,
  and the ratio f(1.4)/f(2.6) equals (0.9)**((1.4-2.6)/2) =
  (0.9)**(-0.6) within 1e-9.
- squire_young_profile_drag(3.0e-3, 1.0, 27.0, 30.0, 1.4) =
  4.2827949370e-3 within 1e-9 (magnitude band 4.0e-3 to 4.5e-3) and
  equal to 2.0*(3.0e-3/1.0)*trailing_edge_factor(27.0, 30.0, 1.4)
  within 1e-12; twice that value (8.5655898739e-3) is the
  both-surfaces total at symmetric zero lift.
- The anchor identity: with Re_c = 30.0*1.0/1.46e-5 =
  2.0547945205e6, theta_bl = 0.664*1.0/sqrt(Re_c) =
  4.6321634974e-4, and squire_young_profile_drag(theta_bl, 1.0, 30.0,
  30.0, h_te) equals 1.328/sqrt(Re_c) = 9.2643269948e-4 within 1e-9
  relative for h_te in (1.4, 2.6) (the reduction is independent of the
  shape factor at U_TE = U_inf).
- Chain equals identity on the flat plate: a 4001-station traverse
  with ue = 30.0 m/s over x in [0, 1] m gives
  momentum_thickness_at_te = 4.6321634974e-4 m within 1e-6 relative
  and fully_laminar_profile_drag = 9.2643269948e-4 within 1e-6
  relative of 1.328/sqrt(Re_c).
- Reynolds invariance: on the constant-velocity plate,
  fully_laminar_profile_drag(...)*sqrt(Re_c) = 1.328 within 1e-9 at
  U = 30.0 m/s and at U = 15.0 m/s (Re_c/2).
- Case C chain: the 4001-station linear-decay traverse
  ue(x) = 30.0*(1 - 0.1*x) gives momentum_thickness_at_te =
  5.6151694776e-4 m within 1e-6 relative of the closed-form
  sqrt(GROWTH_C*nu*U_INF**5*1.0*(1-0.9**6)/(0.6)/27.0**6) and
  fully_laminar_profile_drag = 8.0162064696e-4 within 1e-6 relative,
  equal to 2.0*(theta_te/1.0)*(0.9)**3.2 within 1e-9.
- ValueErrors: u_te at 0 and -1.0 and u_inf at 0 on both velocity
  arguments of trailing_edge_factor and squire_young_profile_drag;
  h_te at 1.0 and 0.5 (at or below 1) on both h_te arguments;
  theta_te at 0 and chord at 0 on squire_young_profile_drag; fewer
  than two stations, unequal xs/ues lengths, xs starting below 0,
  non-increasing stations, a zero edge velocity, and nu at 0 on
  momentum_thickness_at_te; chord at 0 and u_inf at -1.0 on
  fully_laminar_profile_drag.
- Determinism: repeated calls on identical inputs return identical
  results; no imports beyond math; closed form with a single
  deterministic trapezoid quadrature, no iteration.
- Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
  ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
  computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (2 verbatim queries for
eval/hit1-wave45-squire-young-profile-drag.yaml)

Query 1 (copy verbatim):
  "compute the section profile-drag coefficient of the airfoil with
  the squire-young-formula from the trailing-edge momentum thickness,
  the trailing-edge to freestream edge-velocity ratio, and the shape
  factor 1.4 at the trailing edge"
  intent: "aerodynamics; boundary-layer trailing-edge drag mapping:
  squire-young-formula section profile-drag coefficient from the
  trailing-edge momentum thickness over chord, the trailing-edge to
  freestream edge-velocity ratio, and the trailing-edge shape factor
  1.4"
  expected_skill: "aerodynamics/boundary-layer/
  squire-young-profile-drag"
Query 2 (copy verbatim):
  "estimate the profile drag of the fully laminar 2-D section at low
  Reynolds number with the squire-young-formula: grow the
  boundary-layer momentum thickness to the trailing edge on the
  integral growth relation and apply the edge-velocity-ratio exponent
  to the profile-drag coefficient"
  intent: "aerodynamics; fully laminar low-Reynolds section drag
  chain: integral growth of the boundary-layer momentum thickness to
  the trailing edge and the squire-young-formula edge-velocity-ratio
  exponent applied to the profile-drag coefficient"
  expected_skill: "aerodynamics/boundary-layer/
  squire-young-profile-drag"
Task ids: w45-squire-young-profile-drag-1 and -2. The queries carry
the receipt gate (e) tokens verbatim: squire-young-formula,
profile-drag-coefficient, trailing-edge-momentum-thickness and
edge-velocity-ratio appear on NO router row, in NO skills/ leaf and in
NO eval/hit1-corpus.yaml task (real greps for this spec: "squire" =
0 corpus tasks, "squire-young" = 0 tree hits, hyphenated
wake-survey/wake-rake/momentum-deficit = 0 tree hits). The wording
deliberately avoids the momentum-thickness tag of boundary-layer-
theory, the thwaites-integral token of boundary-layer-transition, the
polar wording of xfoil-analysis, and the bare phrase profile drag: the
single corpus task carrying "profile drag" (line 3947) is the
rotorcraft forward-flight power sweep routing to
flight-mechanics/performance/rotorcraft-forward-flight-performance,
with no squire-young or trailing-edge-momentum content, so neither
query can be captured by it. No em dashes in the queries.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the section
profile-drag coefficient of a two-dimensional body or airfoil from
the boundary-layer momentum state at its trailing edge:" and include
the outputs in the Claim. First tag: squire-young-formula.
Additional tags ONLY the receipt's gate (f) list, verbatim:
squire-young-formula, profile-drag-coefficient,
trailing-edge-momentum-thickness, laminar-profile-drag,
momentum-integral-drag. NEVER the bare single words drag,
boundary-layer, momentum, airfoil, profile, trailing edge (each
collides with pack-wide or geometry leaves) and NEVER the sibling
tokens thwaites-integral, thwaites-lambda-criterion,
michel-criterion, transition-location, natural-transition,
laminar-separation-point, turbulent-separation-station,
stratford-separation-criterion, separation-margin,
adverse-pressure-gradient (boundary-layer-separation and
boundary-layer-transition, whose traverses stop at the separation
flag and the Michel onset and whose tags own the edge-velocity-
distribution phrasing), blasius, 1-7-power, displacement-thickness,
momentum-thickness (bare), skin-friction-coefficient,
reynolds-number-regime (boundary-layer-theory), form-factor,
interference-factor, wetted-area, drag-buildup, zero-lift-drag,
parasite-drag, equivalent-skin-friction (parasite-drag), polar,
xfoil, viscous-analysis (xfoil-analysis), rotor-profile-drag,
profile-power, blade-element (the rotorcraft power leaves),
wake-survey, wake-rake, momentum-deficit, velocity-defect,
laminar-far-wake (the wake-survey instrumentation and free-shear
slots, plus the momentum-deficit phrasing owned by
boundary-layer-theory and boundary-layer-transition), and
roughness, sweep, suction, compressibility inputs. 50-150 words,
<=1000 chars, no em dash, action verb present. The description must
not assign transition classes, regime verdicts or separation
outcomes. Recommended wording: "Use when you must compute the section
profile-drag coefficient of a two-dimensional body or airfoil from
the boundary-layer momentum state at its trailing edge: evaluate the
squire-young-formula c_d,p = 2*(theta_TE/c)*(U_TE/U_inf)^((H_TE+5)/2)
with the documented trailing-edge shape factor about 1.4, and the
zero-pressure-gradient reduction to the Blasius flat-plate drag
1.328/sqrt(Re_c) when the trailing-edge velocity equals the
freestream. Grows the laminar momentum thickness to the trailing edge
on the integral growth relation for the fully laminar chain, then
applies the edge-velocity-ratio exponent. Produces the section
profile-drag-coefficient, the trailing-edge momentum thickness and
the edge-velocity factor that gate airfoil section drag estimates and
boundary-layer checks. Trigger: squire young formula, profile drag
coefficient, trailing edge momentum thickness, edge velocity ratio,
laminar profile drag, momentum integral drag." The sibling trigger
words thwaites, michel,
stratford, separation, transition location, blasius, form factor,
interference, wetted area, xfoil polar, wake survey and rotor profile
drag must not appear. ZERO em dashes in every file. Standards
reference-only: naca-tr-824 named as
the boundary-layer family context; the Squire-Young relation and the
integral growth above are standard engineering methodology,
summary-only per standards-map.yaml, and no standards text is
reproduced.

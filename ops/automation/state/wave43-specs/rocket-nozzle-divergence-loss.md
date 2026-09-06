# Wave-43 leaf spec: rocket-nozzle-divergence-loss (propulsion,
# rocket pack)

- Path: skills/propulsion/rocket/rocket-nozzle-divergence-loss/
- Pack: rocket (present siblings cold-gas-thruster,
  combustion-chamber-design, hybrid-rocket-motor, injector-design,
  nozzle-design, propellant-selection, rocket-engine-cycle,
  rocket-gravity-loss, rocket-nozzle-flow-separation, rocket-sizing,
  rocket-staging, solid-rocket-motor, thrust-chamber-cooling,
  thrust-vector-control; adjacent fences in propulsion/combustion/
  cea-rocket-combustion and propulsion/electric).
- Provenance: wave-42 flagged this leaf MARGINAL thin
  (single-coefficient thinness, ops/automation/state/wave42-leaf-plan.md)
  and did NOT plan it; the wave-43 dispatch probe receipt C1 WIDENS the
  scope to full delivered-thrust loss bookkeeping (divergence factor +
  bell equivalence + boundary-layer displacement + delivered Isp chain),
  which clears the thinness objection: GO.
- Claim fences (quoted from the sibling frontmatter and body at prep,
  none owns the delivered-thrust loss chain of an attached-flow nozzle):
  - cea-rocket-combustion (propulsion/combustion, the thermochemistry
    ceiling) states in its quick reference: "The reported Isp values are
    ideal-gas frozen-flow ceilings: real engines deliver roughly 80 to
    95 percent of them because of finite expansion ratio, nozzle
    divergence, boundary layers and combustion losses. The c-star
    efficiency (0.92 to 0.98) and the Isp efficiency (0.8 to 0.95)
    bridge from the ideal ceilings to delivered values." Its
    isp_with_efficiency helper (scripts/cea_rocket_combustion_logic.py)
    is a plain band multiplier, efficiency * ideal_isp, with the
    efficiency a user-supplied 0.8-0.95 constant. The new leaf computes
    the nozzle-side share of that band (divergence and boundary layer)
    from geometry and flow state instead of a band multiplier, and MUST
    NOT duplicate isp_with_efficiency: cea keeps the c-star side
    (combustion efficiency) and the user-supplied quick-look bands; the
    new leaf supplies the computed divergence/BL correction.
  - nozzle-design (this pack) OWNS the ideal attached-flow sizing: its
    description reads "design a rocket engine nozzle from the chamber
    conditions: compute the exit Mach number for a target area ratio,
    the choked mass flow through the throat, the exit velocity and the
    exit static pressure, and the ideal thrust with the pressure term"
    with optimum_expansion against the ambient pressure. The new leaf
    CONSUMES that ideal state (ve, pe, Ae, mdot and the ideal thrust at
    the geometry) as its loss-free baseline and never re-derives exit
    Mach, choked mass flow or the ideal thrust as a deliverable; the
    finite-expansion-ratio choice (the gap between the geometry ideal
    and the fully expanded ceiling) belongs to nozzle-design's
    expansion verdict, not to this leaf.
  - rocket-nozzle-flow-separation (this pack) OWNS the off-design
    overexpanded boundary: its description reads "predict flow
    separation in an overexpanded rocket nozzle: apply the
    separation-pressure-ratio criterion (wall static pressure falling
    to K_SEP times ambient, K_SEP 0.4) ... separated-thrust loss and
    the side-load flag". The new leaf's loss chain is valid only while
    the wall flow stays attached; when the exit area ratio exceeds the
    separation-station area ratio at the operating ambient, the
    separation leaf takes over and the attached-flow loss bookkeeping
    no longer applies (its separated-thrust loss replaces this leaf's
    corrections).
  - Propulsion electric leaves (gridded-ion-thruster, hall-thruster)
    mention conical/bell optics and divergence in their ion-optics
    context only: grid erosion and beam divergence of an ion accelerator
    grid, not the gasdynamic thrust-loss bookkeeping of a chemical
    nozzle; no fence overlap.
  - Whole-tree greps at prep: "divergence" inside eval/hit1-corpus.yaml
    hits only aerodynamic drag-divergence tasks (supercritical airfoil)
    and the aerodynamics/aeroelasticity/divergence-speed wave comment;
    "conical" or "half-angle" in propulsion appears only in the two
    electric leaves named above. GENUINE propulsion gap (probe receipt
    C1, widened scope, GO): no leaf computes the conical divergence
    factor, the bell equivalence, the nozzle boundary-layer loss or a
    delivered Isp that replaces the cea band multiplier.
- Standards id: ecss (reference-only, present in standards-map.yaml,
  sibling rocket convention: nozzle-design and
  rocket-nozzle-flow-separation both carry standards: [id: ecss,
  reference-only: true]). Ledger Standard: ecss.
- Family: propulsion

## Claim

Compute the deterministic delivered-thrust loss bookkeeping of an
attached-flow rocket nozzle (probe receipt C1 wording): the
conical-nozzle divergence factor lambda = (1 + cos(alpha))/2 for a
half-angle alpha applied to the ideal axial momentum thrust, the
equivalent bell/parabolic-contour (GVC 80-percent) efficiency relative
to conical (a Rao-class contour bell of about 80 percent of the length
of the equivalent 15-degree conical nozzle, contour efficiency 0.98
typical and parameterized), the turbulent boundary-layer
displacement-thickness effect on the effective expansion ratio and on
the delivered thrust, and the combined delivered Isp equal to the ideal
Isp minus the computed losses, replacing cea's band multipliers with a
computed estimate. The model picks the 1-D mass-flux correction and
states it exactly: the exit wall layer removes the momentum flux
through the annulus of momentum thickness theta over the exit
perimeter; for the 1/7-power turbulent profile theta = (7/9)*delta*, so
the fractional loss of the momentum term is 2*theta/r_exit =
(14/9)*delta*/r_exit to first order in delta*/r_exit (thin layer),
while the pressure term (pe - pa)*Ae acts over the full geometric exit
area and is unchanged. The displacement thickness itself grows as the
turbulent flat-plate law delta = 0.37*L*Re_L**(-0.2) over the divergent
length L with delta* = delta/8. Delivered thrust = shape_factor *
(1 - xi_bl) * mdot * ve + (pe - pa) * Ae, with shape_factor the conical
lambda or the bell contour efficiency; delivered Isp = delivered thrust
/ (mdot * g0). Produces the shape factor (conical or bell), the
contour-only bell-to-conical efficiency ratio, the exit displacement
and momentum thicknesses, the boundary-layer loss fraction, the
displaced-core effective exit area ratio eps_eff = eps *
(1 - delta*/r_exit)**2, the delivered thrust, the delivered Isp, and
the delivered fraction of the ideal attached-flow value at the same
area ratio, with the design verdict that the 80-percent-length bell
delivers within a few tenths of a percent of the full-length conical
(the bell's mass saving is its benefit, not an Isp gain). Does NOT do:
exit Mach, choked mass flow, exit velocity, static pressure or ideal
thrust from the chamber conditions, or the expansion verdict against
the ambient (nozzle-design, the ideal attached-flow sizing at a given
area ratio); separation-station area ratio, separation altitude,
separated-thrust loss or side loads of an overexpanded nozzle
(rocket-nozzle-flow-separation); chamber thermochemistry, c-star,
ideal Isp ceilings or the isp_with_efficiency band multiplier
(cea-rocket-combustion); throat sizing and chamber volume
(combustion-chamber-design); gravity, drag or trajectory losses
(rocket-gravity-loss, a different loss class); combustion
inefficiency, finite-expansion shortfall against the fully expanded
ceiling, heat-transfer or kinetic (frozen versus equilibrium) effects.
Attached flow at the operating ambient is assumed; off-design
overexpansion past the separation limit invalidates the chain. Gamma
and R are supplied by the caller (representative hot combustion
products); the module constants are documented below.

## Model (implement exactly)

Pure stdlib, math only, closed form. Module constants: G0 = 9.80665
m/s^2 (standard gravity, sibling rocket convention), ETA_BELL_DEFAULT =
0.98 (documented typical contour efficiency of the equivalent
80-percent-length Rao-class bell, allowed as a parameter), ALPHA_REF_DEG
= 15.0 (the comparison conical half-angle for the bell ratio),
TURB_COEFF = 0.37 (turbulent flat-plate growth coefficient),
DELTA_STAR_OVER_DELTA = 1.0/8.0 and THETA_OVER_DELTA = 7.0/72.0 (the
1/7-power profile shape ratios, so theta = (7/9)*delta_star exactly).

Defining relations (pin these exactly; every function below derives
from them):
- Conical divergence factor: lambda = (1 + cos(alpha))/2 with alpha the
  half-angle in degrees, the axial projection of the momentum flux
  leaving a conical wall; lambda(0 deg) tends to 1, lambda(60 deg) =
  0.75 exactly, lambda(15 deg) = 0.982963.
- Bell equivalence: the parabolic-contour bell of about 80 percent of
  the equivalent 15-degree conical length carries the contour
  efficiency eta_bell (0.98 typical of ideal, allowed parameter); the
  contour-only comparison with the conical it replaces is eta_bell /
  lambda(alpha). At eta_bell = lambda(15 deg) the ratio is exactly 1.
- Turbulent boundary layer over the divergent length L (flat-plate
  growth, edge conditions at the exit): Re_L = rho_e * ve * L / mu,
  delta = 0.37 * L * Re_L**(-0.2), delta* = delta/8, theta = (7/72) *
  delta = (7/9) * delta*. The effective (displaced-core) exit area
  ratio is eps_eff = eps * (1 - delta*/r_exit)**2, because the internal
  flow shrinks the inviscid core, A_eff = pi * (r_exit - delta*)**2,
  with the throat boundary layer neglected; the plus-sign displaced-wall
  form of external-flow displacement is NOT used.
- 1-D mass-flux correction (the standard method picked and stated): the
  wall layer removes the momentum flux rho_e * ve * theta through the
  annulus 2*pi*r_exit*theta at the exit, so the fractional loss of the
  momentum term is 2*theta/r_exit = (14/9)*delta*/r_exit to first order
  in delta*/r_exit. The pressure term is unaffected because the wall
  pressure force acts over the full geometric exit area.
- Delivered thrust and Isp: F_del = shape_factor * (1 - xi_bl) * mdot *
  ve + (pe - pa) * Ae and Isp_del = F_del / (mdot * g0), where
  shape_factor is lambda (conical) or eta_bell (bell) and the ideal
  attached-flow state (ve, pe, Ae, mdot) is the nozzle-design output at
  the same geometry. At shape_factor = 1 and xi_bl = 0 the chain
  reproduces the ideal thrust exactly (the no-loss identity).

Functions (public API, 8 functions, all pure):
- conical_divergence_factor(alpha_deg) -> float
  (1 + cos(radians(alpha_deg)))/2. ValueError if alpha_deg <= 0 or
  alpha_deg >= 90.
- bell_contour_efficiency(eta_bell = ETA_BELL_DEFAULT) -> float
  returns the validated contour efficiency parameter (documented
  typical 0.98). ValueError if eta_bell not in (0, 1].
- bell_relative_to_conical(eta_bell = ETA_BELL_DEFAULT,
  alpha_deg = ALPHA_REF_DEG) -> float
  bell_contour_efficiency(eta_bell) / conical_divergence_factor
  (alpha_deg), the contour-only efficiency of the equivalent
  80-percent-length bell relative to the conical nozzle it replaces;
  0.996986 at the defaults, exactly 1.0 when eta_bell equals
  lambda(15 deg). ValueError set as both callers.
- turbulent_displacement_thickness(length_m, vel_ms, rho_kgm3,
  mu_pas) -> float
  delta* = (1/8) * 0.37 * length_m * Re_L**(-0.2) with Re_L =
  rho_kgm3 * vel_ms * length_m / mu_pas, the exit displacement
  thickness of the turbulent wall layer grown over the divergent
  length. ValueError if any argument <= 0.
- boundary_layer_loss_fraction(delta_star_m, r_exit_m) -> float
  (14.0/9.0) * delta_star_m / r_exit_m, the 1-D mass-flux momentum
  loss fraction of the momentum term. ValueError if delta_star_m <= 0,
  r_exit_m <= 0, or delta_star_m >= r_exit_m.
- effective_exit_area_ratio(area_ratio, delta_star_m, r_exit_m) ->
  float
  area_ratio * (1 - delta_star_m / r_exit_m)**2, the displaced-core
  expansion ratio. ValueError if area_ratio <= 1 or the delta* checks
  above.
- delivered_thrust(mdot_kgs, ve_ms, pe_pa, pa_pa, ae_m2,
  shape_factor, bl_loss_fraction) -> float
  shape_factor * (1 - bl_loss_fraction) * mdot_kgs * ve_ms +
  (pe_pa - pa_pa) * ae_m2. ValueError if mdot_kgs <= 0, ve_ms <= 0 or
  ae_m2 <= 0 (non-positive flow/area), shape_factor not in (0, 1], or
  bl_loss_fraction not in [0, 1).
- delivered_isp(mdot_kgs, ve_ms, pe_pa, pa_pa, ae_m2, shape_factor,
  bl_loss_fraction, g0 = G0) -> float
  delivered_thrust(...) / (mdot_kgs * g0). ValueError set as
  delivered_thrust plus g0 <= 0.

Identities to test (closed form; assert with isclose/abs bounds, never
exact float equality on computed sums):
- conical_divergence_factor(60.0) = 0.75 exactly (cos 60 = 1/2) and
  conical_divergence_factor(15.0) = 0.982963 within 1e-5; lambda falls
  monotonically with the half-angle.
- Degeneracy: bell_contour_efficiency() = 0.98 and
  bell_relative_to_conical(conical_divergence_factor(15.0), 15.0) =
  1.0 within 1e-9; bell_relative_to_conical() = 0.996986 within 1e-5.
- No-loss identity: delivered_thrust(mdot, ve, pe, pa, ae, 1.0, 0.0)
  equals mdot*ve + (pe - pa)*ae to float noise (anchor residual
  0.000e+00 N), i.e. the ideal thrust of the same state; delivered_isp
  at pe = pa, shape 1, xi 0 equals ve/g0 exactly (anchor 332.496090 s
  on both sides).
- Profile identities: delta*/delta = 1/8 = 0.125 and theta/delta* =
  7/9 = 0.777778 (exact module constants), so xi_bl = 2*theta/r_exit =
  (14/9)*delta*/r_exit.
- Boundary of the loss fraction: xi_bl tends to 0 as delta*/r_exit
  tends to 0; effective_exit_area_ratio(eps, 0, r) = eps.
- Loss ordering: the delivered fraction falls as the half-angle grows
  beyond the 10-12 deg boundary-layer/divergence balance (anchor sweep
  below: peak near 10 deg, then monotone fall to 30 deg); the bell
  delivers within 0.1 percent of the 15-degree conical (anchor
  0.99901) at 80 percent of the length.
- ValueErrors across the module: alpha_deg at 0, 90, -5 and 95;
  eta_bell at 0, 1.1 and 2.0; delta_star_m at 0 and >= r_exit_m;
  area_ratio at 1.0 and 0.5; mdot_kgs at 0, ve_ms at -1 and ae_m2 at 0;
  shape_factor at 0 and 1.5; bl_loss_fraction at -0.1 and 1.0; g0 at 0.
- Determinism; no imports beyond math; the model never re-derives the
  ideal exit Mach or mass flow (those are nozzle-design inputs here).

## Worked example

Representative LOX/RP-1 upper-stage nozzle: chamber pressure 7.0 MPa,
chamber temperature 3672 K, molecular weight 22.1 kg/kmol (so R =
8314.462/22.1 = 376.220 J/(kg K)), gamma = 1.24, c-star = 1791.2 m/s,
area ratio Ae/At = 70, throat radius 0.150 m, and a representative
hot-product viscosity mu = 8.0e-5 Pa s at the exit. The ideal
attached-flow exit state at the geometry (nozzle-design domain,
computed in the anchor so the numbers are real): Me = 4.931384,
pe = 6036.738 Pa, Te = 937.159 K, rho_e = 0.017122 kg/m^3,
ve = 3260.673 m/s, mdot = 276.24 kg/s, r_exit = 1.2550 m, ideal vacuum
thrust F_id = 930594.6 N, ideal vacuum Isp at the geometry =
343.522 s (the fully expanded zero-pressure ceiling of the same gas is
385.276 s, 41.754 s higher, 12.2 percent above the geometry ideal, 10.8
percent of the ceiling: that gap is the finite-expansion-ratio verdict
of nozzle-design, not a divergence/BL loss). All values below
are REAL outputs of the prep anchor /tmp/w43spec/anchor_nozdiv.py
(usr/bin/python3 3.9.6, stdlib math, closed form, exit 0).
- Conical, half-angle 15 deg: lambda = (1 + cos 15)/2 = 0.982963 over
  the divergent length L = (r_exit - r_throat)/tan(15 deg) = 4.124 m.
  Turbulent growth at Re_L = rho*ve*L/mu = 2.879e6 gives delta* =
  0.00974 m and the 1-D mass-flux loss xi_bl = (14/9)*delta*/r_exit =
  0.01207 (1.21 percent of the momentum term); the displaced core
  eps_eff = 68.9176 (from 70). Delivered vacuum thrust F_del =
  904558.9 N, delivered Isp = 333.911 s, fraction of the geometry ideal
  = 0.97202 (in the plausibility band [0.93, 0.98]).
- Equivalent bell (GVC 80-percent convention): Rao-class
  parabolic-contour bell at L = 0.8 * 4.124 = 3.299 m with contour
  efficiency eta_bell = 0.98. Shorter wall growth gives delta* =
  0.00815 m, xi_bl = 0.01010, eps_eff = 69.0940. Delivered thrust
  F_del = 903664.7 N, delivered Isp = 333.581 s, fraction = 0.97106.
  Bell/conical delivered ratio = 0.99901: the 80-percent-length bell
  delivers within 0.10 percent of the full-length 15-degree conical
  (contour-only ratio 0.996986), the design verdict that the bell's
  benefit is its 20 percent length and mass saving, not an Isp gain.
- Half-angle sensitivity at fixed area ratio 70 (conical, real anchor
  sweep): the delivered fraction peaks near 10 deg where the shallow
  cone's longer wall starts to cost more boundary layer than the
  divergence saves: 8 deg 0.97580, 10 deg 0.97644, 12 deg 0.97551,
  15 deg 0.97202, 20 deg 0.96194, 25 deg 0.94751, 28 deg 0.93699,
  30 deg 0.92926. The typical design band 12-25 deg spans 0.94751 to
  0.97551, inside [0.93, 0.98]; the extended sweep 8-28 deg holds
  0.93699-0.97644 inside the band, and only the steep 30 deg cone dips
  to 0.92926.
- Identity anchors: lambda(60 deg) = 0.750000 (exact), lambda(15 deg)
  = 0.982963, bell_relative_to_conical() = 0.996986, and at eta_bell =
  lambda(15 deg) the ratio is 1.000000. The no-loss chain returns the
  ideal thrust exactly (residual 0.000e+00 N) and delivered_isp at
  pe = pa with shape 1, xi 0 equals ve/g0 = 332.496090 s.
- Read-off: an RP-1 upper stage with this 70:1 nozzle loses about 2.8
  percent of its ideal vacuum Isp at the geometry to divergence plus
  boundary layer (15-deg conical), or 2.9 percent with the shorter
  80-percent bell (0.98 contour); the nozzle-side share of the cea
  "80 to 95 percent of ideal" band is about 0.97, and the rest of that
  band is combustion (c-star) and finite-expansion accounting owned by
  the sibling leaves.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w43spec/anchor_nozdiv.py
(usr/bin/python3 3.9.6, stdlib math, closed form, exit 0).

## Validation list (contract test must include)

- conical_divergence_factor(15.0) = 0.982963 within 1e-5;
  conical_divergence_factor(60.0) = 0.75 within 1e-9; lambda falls
  monotonically from 8 to 30 deg.
- bell_contour_efficiency() = 0.98;
  bell_relative_to_conical() = 0.996986 within 1e-5;
  bell_relative_to_conical(conical_divergence_factor(15.0), 15.0) =
  1.0 within 1e-9.
- turbulent_displacement_thickness(4.124, 3260.673, 0.017122, 8.0e-5)
  = 0.00974 within 1e-4 and
  boundary_layer_loss_fraction(0.00974, 1.2550) = 0.01207 within 1e-4
  (xi = (14/9)*delta*/r_exit); effective_exit_area_ratio(70.0,
  0.00974, 1.2550) = 68.9176 within 0.01.
- No-loss identity: delivered_thrust(mdot, ve, pe, pa, ae, 1.0, 0.0)
  reproduces mdot*ve + (pe - pa)*ae with abs residual below 1e-6 N;
  delivered_isp at pe = pa, shape 1, xi 0 equals ve/g0 within 1e-9
  relative (anchor 332.496090 s).
- Worked example: conical 15 deg delivers F_del = 904558.9 N within
  1 N, Isp_del = 333.911 s within 0.05 s, fraction 0.97202 within
  1e-4; bell (0.98 contour, 0.8 length) delivers F_del = 903664.7 N
  within 1 N, Isp_del = 333.581 s within 0.05 s, fraction 0.97106
  within 1e-4; bell/conical ratio 0.99901 within 1e-4; both fractions
  inside [0.93, 0.98].
- Sensitivity anchors: fraction(10 deg) = 0.97644 within 1e-4 and
  above its neighbours fraction(8 deg) = 0.97580 and fraction(12 deg) =
  0.97551; fraction(25 deg) = 0.94751 within 1e-4; fraction(30 deg) =
  0.92926 within 1e-4 (below the band, the steep boundary).
- ValueErrors: alpha_deg at 0, 90, -5 and 95; eta_bell at 0, 1.1 and
  2.0; delta_star_m at 0 and equal to r_exit_m; area_ratio at 1.0 and
  0.5; mdot_kgs at 0, ve_ms at -1 and ae_m2 at 0; shape_factor at 0
  and 1.5; bl_loss_fraction at -0.1 and 1.0; g0 at 0.
- Determinism; no imports beyond math; the ideal exit state is an input
  (never re-derived inside the module).

## Corpus fragment (eval/hit1-wave43-rocket-nozzle-divergence-loss.yaml)

Query 1 (copy verbatim):
  "compute the rocket-nozzle-divergence-loss delivered thrust of a
  conical nozzle from the half-angle divergence factor and the
  turbulent boundary-layer correction and report the
  nozzle-delivered-isp as a fraction of the ideal"
  intent: "propulsion; rocket nozzle divergence factor and boundary
  layer loss bookkeeping to the delivered Isp fraction of the ideal
  attached-flow thrust"
  expected_skill: "propulsion/rocket/rocket-nozzle-divergence-loss"
Query 2 (copy verbatim):
  "compare the conical-nozzle-thrust-correction of a 15 degree
  half-angle conical rocket nozzle with the bell-nozzle-efficiency of
  the equivalent 80 percent length bell contour for delivered specific
  impulse"
  intent: "propulsion; conical divergence thrust correction versus the
  equivalent 80-percent-length bell contour efficiency and their
  delivered Isp comparison"
  expected_skill: "propulsion/rocket/rocket-nozzle-divergence-loss"
Task ids: w43-rocket-nozzle-divergence-loss-1 and -2. Prep grep of
eval/hit1-corpus.yaml (real counts): rocket-nozzle-divergence-loss 0,
conical-nozzle-thrust-correction 0, bell-nozzle-efficiency 0,
nozzle-delivered-isp 0, divergence-loss 0, nozzle-divergence 0,
delivered-isp 0. The nearest corpus tasks route elsewhere: the
nozzle-design tasks (nz1, nz2) ask for the area ratio, exit Mach and
ideal thrust at a target geometry, the rocket-nozzle-flow-separation
tasks (w38-rocket-nozzle-flow-separation-1/-2) route on the
separation-pressure-ratio criterion, separation station and altitude,
and every other "divergence" hit in the corpus is aerodynamic
drag-divergence of a transonic airfoil, so the queries above are
collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the
rocket-nozzle-divergence-loss bookkeeping from the nozzle geometry and
the ideal attached-flow state:" and include the outputs in the Claim.
First tag: rocket-nozzle-divergence-loss. Additional tags ONLY:
conical-nozzle-thrust-correction, bell-nozzle-efficiency,
nozzle-delivered-isp, divergence-loss-bookkeeping,
boundary-layer-thrust-loss. NEVER single generic words (nozzle,
conical, bell, divergence, thrust, isp, boundary, layer, efficiency,
loss, half-angle) and NEVER area-ratio, exit-mach, mass-flow,
ideal-thrust or expansion-ratio, which nozzle-design owns, and NEVER
separation-pressure-ratio, summerfield-criterion, overexpanded-nozzle,
separation-altitude, side-load-regime, which
rocket-nozzle-flow-separation owns. 50-150 words, <=1000 chars, no em
dash, action verb present. Recommended wording: "Use when you must
compute the rocket-nozzle-divergence-loss bookkeeping from the nozzle
geometry and the ideal attached-flow state: apply the conical
divergence factor lambda = (1 + cos(alpha))/2 for the half-angle to
the ideal axial momentum thrust, or the bell contour efficiency (0.98
typical for the 80-percent bell) in its place; grow the turbulent
boundary layer over the divergent length to the exit displacement
thickness and convert it with the 1-D mass-flux correction to the
momentum loss fraction; assemble the delivered thrust from the
loss-corrected momentum term plus the unchanged pressure term.
Produces the shape factor, the loss fraction, the effective exit area
ratio, the delivered thrust and the nozzle-delivered-isp fraction of
the ideal value in SI units, replacing the band multiplier. Trigger:
rocket-nozzle-divergence-loss, conical-nozzle-thrust-correction,
bell-nozzle-efficiency, nozzle-delivered-isp, divergence loss,
half-angle thrust loss." The sibling-owned tokens listed above must not
appear.

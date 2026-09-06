---
name: rocket-nozzle-divergence-loss
description: "Use when you must compute the rocket-nozzle-divergence-loss bookkeeping from the nozzle geometry and the ideal attached-flow state: apply the conical divergence factor lambda = (1 + cos(alpha))/2 for the half-angle to the ideal axial momentum thrust, or the bell contour efficiency (0.98 typical for the 80-percent bell) in its place; grow the turbulent boundary layer over the divergent length to the displacement thickness and convert it with the 1-D mass-flux correction to the momentum loss fraction; assemble the delivered thrust from the loss-corrected momentum term and the unchanged pressure term. Produces the shape factor, the loss fraction, the effective exit area ratio, the delivered thrust and the nozzle-delivered-isp fraction of the ideal in SI units, replacing the band multiplier. Trigger: rocket-nozzle-divergence-loss, conical-nozzle-thrust-correction, bell-nozzle-efficiency, nozzle-delivered-isp, divergence loss, half-angle thrust loss."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: rocket
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [rocket-nozzle-divergence-loss, conical-nozzle-thrust-correction, bell-nozzle-efficiency, nozzle-delivered-isp, divergence-loss-bookkeeping, boundary-layer-thrust-loss]
  version: 0.1.0
  author: AeroSkills
---

# Rocket Nozzle Divergence Loss (propulsion/rocket/rocket-nozzle-divergence-loss)

Use when the task is the deterministic delivered-thrust loss bookkeeping
of an attached-flow rocket nozzle: how much of the ideal axial momentum
thrust a conical or bell divergent contour actually delivers, what the
turbulent boundary layer over the divergent wall removes, and the
delivered Isp that results. The model computes the conical divergence
factor lambda = (1 + cos(alpha))/2 for the half-angle, the equivalent
80-percent-length bell contour efficiency in its place, the
boundary-layer displacement thickness grown over the divergent length,
the 1-D mass-flux momentum loss fraction, and the combined delivered
thrust and delivered Isp. It pairs with propulsion/rocket/nozzle-design,
which supplies the ideal attached-flow exit state at the geometry that
this leaf consumes as its loss-free baseline.

## Domain quick reference

- Conical divergence factor: lambda = (1 + cos(alpha))/2 for the
  half-angle alpha, the axial projection of the momentum flux leaving a
  conical wall. lambda(0 deg) tends to 1, lambda(60 deg) = 0.75
  exactly, lambda(15 deg) = 0.982963.
- Bell equivalence: the parabolic-contour bell at about 80 percent of
  the equivalent 15-degree conical length carries the contour
  efficiency eta_bell (0.98 typical, allowed as a parameter); the
  contour-only comparison with the cone it replaces is eta_bell /
  lambda(alpha), exactly 1.0 when eta_bell = lambda(15 deg).
- Turbulent growth over the divergent length L (flat plate, edge
  conditions at the exit): Re_L = rho_e * ve * L / mu, delta = 0.37 * L
  * Re_L**(-0.2), delta* = delta/8 and theta = (7/72) * delta =
  (7/9) * delta* for the 1/7-power profile.
- Displaced-core area: the wall layer shrinks the inviscid core, so
  eps_eff = eps * (1 - delta*/r_exit)**2 (internal flow); the throat
  boundary layer is neglected and the external-flow plus-sign
  displaced-wall form is not used.
- 1-D mass-flux correction: the layer removes the momentum flux through
  the exit annulus of momentum thickness theta, so the fractional loss
  of the momentum term is 2*theta/r_exit = (14/9)*delta*/r_exit to
  first order in delta*/r_exit; the pressure term (pe - pa)*Ae acts
  over the full geometric exit area and is unchanged.
- Delivered thrust and Isp: F_del = shape_factor * (1 - xi_bl) * mdot *
  ve + (pe - pa) * Ae and Isp_del = F_del / (mdot * g0), g0 =
  9.80665 m/s^2, with shape_factor the conical lambda or the bell
  contour efficiency. At shape 1 and xi_bl = 0 the chain reproduces the
  ideal thrust exactly (the no-loss identity).
- Units are SI throughout: N, kg/s, m/s, Pa, m^2, s.
- ECSS frames the space-propulsion context; the relations above are
  standard engineering methodology, summary-only. The claim does not
  extend past attached flow: off-design overexpansion to the
  separation limit invalidates the chain, and gamma and R are caller
  inputs from the hot-product state.

## Workflow

1. Collect the geometry and the ideal attached-flow state: the
   half-angle alpha or the bell length fraction, the divergent length L
   (for a conical nozzle, L = (r_exit - r_throat)/tan(alpha)), the exit
   radius r_exit, and the ideal state mdot, ve, pe and Ae from
   nozzle-design at the same area ratio. Attached flow at the operating
   ambient is assumed.
2. Choose the shape factor: conical_divergence_factor for a conical
   half-angle, or bell_contour_efficiency for the 80-percent bell
   contour in its place.
3. Judge the bell-to-conical contour comparison with
   bell_relative_to_conical and note whether the shorter bell contour
   closes the gap to the cone it replaces.
4. Grow the turbulent boundary layer over the divergent length with
   turbulent_displacement_thickness(length_m, vel_ms, rho_kgm3,
   mu_pas) to the exit displacement thickness.
5. Convert the displacement thickness with boundary_layer_loss_fraction
   to the momentum loss fraction xi_bl and with
   effective_exit_area_ratio to the displaced-core effective exit area
   ratio eps_eff.
6. Assemble the delivered thrust with delivered_thrust(mdot, ve, pe,
   pa, Ae, shape_factor, xi_bl) and the delivered Isp with
   delivered_isp(...); the pressure term keeps the full geometric exit
   area.
7. Read off the delivered fraction of the ideal (F_del over the ideal
   thrust at the same geometry) and the bell-versus-conical verdict:
   the 80-percent-length bell delivers within about 0.1 percent of the
   full-length 15-degree conical, so its benefit is the 20 percent
   length and mass saving, not an Isp gain.
8. Confirm the deterministic checks with the contract test
   scripts/test_rocket_nozzle_divergence_loss.py.

## Worked example

Representative LOX/RP-1 upper-stage nozzle: pc = 7.0 MPa, Tc = 3672 K,
Mw = 22.1 (R = 376.220 J/(kg K)), gamma = 1.24, c-star = 1791.2 m/s,
area ratio Ae/At = 70, throat radius 0.150 m, hot-product viscosity mu
= 8.0e-5 Pa s at the exit. The ideal attached-flow state at the
geometry (nozzle-design domain) is Me = 4.931384, pe = 6036.738 Pa,
rho_e = 0.017122 kg/m^3, ve = 3260.673 m/s, mdot = 276.24 kg/s,
r_exit = 1.2550 m, ideal vacuum thrust F_id = 930598.1 N and ideal
vacuum Isp = 343.522 s. Module outputs with these inputs are real:

- Conical, half-angle 15 deg: lambda = 0.982963 over the divergent
  length L = (r_exit - r_throat)/tan(15 deg) = 4.124 m. Turbulent
  growth at Re_L = 2.879e6 gives delta* = 0.00974 m and the 1-D
  mass-flux loss xi_bl = (14/9)*delta*/r_exit = 0.01207 (1.21 percent
  of the momentum term); the displaced core eps_eff = 68.9176 (from
  70). Delivered vacuum thrust F_del = 904562.3 N, delivered Isp =
  333.911 s, fraction of the geometry ideal = 0.97202, inside the
  plausibility band [0.93, 0.98]. The prep anchor (full-precision
  unrounded ideal state) reports F_del = 904558.9 N, 3.4 N lower: the
  rounding of the printed mdot input, a 4e-6 relative difference.
- Equivalent bell (GVC 80-percent convention): Rao-class parabolic
  contour at L = 0.8 * 4.124 = 3.299 m with contour efficiency eta_bell
  = 0.98. The shorter wall grows delta* = 0.00815 m, xi_bl = 0.01010,
  eps_eff = 69.0940. Delivered thrust F_del = 903668.2 N, delivered
  Isp = 333.581 s, fraction = 0.97106 (anchor 903664.7 N, same 4e-6
  input-rounding band).
- Bell/conical delivered ratio = 0.99901: the 80-percent-length bell
  delivers within 0.10 percent of the full-length 15-degree conical
  (contour-only ratio 0.996986), the design verdict that the bell's
  benefit is its 20 percent length and mass saving, not an Isp gain.
- Half-angle sensitivity at fixed area ratio 70 (conical): the
  delivered fraction peaks near 10 deg where the shallow cone's longer
  wall starts to cost more boundary layer than the divergence saves:
  8 deg 0.97580, 10 deg 0.97644, 12 deg 0.97551, 15 deg 0.97202, 20
  deg 0.96194, 25 deg 0.94751, 28 deg 0.93699, 30 deg 0.92926. The
  typical design band 12-25 deg holds inside [0.93, 0.98]; only the
  steep 30 deg cone dips below the band.
- Read-off: this 70:1 nozzle loses about 2.8 percent of its ideal
  vacuum Isp at the geometry to divergence plus boundary layer (15-deg
  conical), or 2.9 percent with the shorter 80-percent bell; the
  nozzle-side share of the cea-rocket-combustion "80 to 95 percent of
  ideal" band is about 0.97, with the rest of the band owned by
  combustion (c-star) and finite-expansion accounting in the sibling
  leaves.

## Verification

- Confirm conical_divergence_factor(15.0) = 0.982963 within 1e-5 and
  conical_divergence_factor(60.0) = 0.75 exactly; lambda falls
  monotonically from 8 to 30 deg.
- Confirm bell_contour_efficiency() = 0.98,
  bell_relative_to_conical() = 0.996986 within 1e-5, and the ratio is
  1.0 within 1e-9 when eta_bell equals lambda(15 deg).
- Confirm the no-loss identity: delivered_thrust with shape 1 and xi 0
  reproduces mdot*ve + (pe - pa)*Ae with residual below 1e-6 N, and
  delivered_isp at pe = pa, shape 1, xi 0 equals ve/g0 = 332.496090 s.
- Confirm the worked-example chain returns F_del = 904562.3 N (conical
  15 deg) and 903668.2 N (80-percent bell, 0.98 contour) within 1 N,
  delivered Isp 333.911 s and 333.581 s within 0.05 s, fractions
  0.97202 and 0.97106 within 1e-4 and inside [0.93, 0.98], and the
  bell/conical ratio 0.99901 within 1e-4.
- Confirm the deterministic checks of step 8 and the ValueError
  rejections of non-physical inputs: half-angle at or beyond the (0,
  90) deg limits, contour efficiency outside (0, 1], displacement
  thickness at zero or at the exit radius, area ratio at or below 1,
  non-positive mass flow, velocity, area or g0, shape factor outside
  (0, 1] and loss fraction outside [0, 1).
- Run the contract test offline: python3
  scripts/test_rocket_nozzle_divergence_loss.py (30 tests,
  deterministic).

## Pitfalls

- Reading the anchor thrust at full precision: the prep anchor computes
  the ideal state at full internal precision, so its 904558.9 N sits
  3.4 N below the module output fed the spec's rounded inputs
  (904562.3 N). The 4e-6 relative difference is input rounding, not
  model error; the fractions, Isp, thicknesses and area ratios agree
  to the printed digits.
- Reporting the finite-expansion shortfall as a nozzle loss: the gap
  between the geometry ideal (343.522 s) and the fully expanded
  ceiling (385.276 s) is the area-ratio verdict of nozzle-design, not
  divergence or boundary-layer loss.
- Applying the chain past the separation limit: when the exit area
  ratio exceeds the separation-station area ratio at the operating
  ambient, the wall flow detaches and rocket-nozzle-flow-separation's
  separated-thrust loss replaces these attached-flow corrections.
- Using the plus-sign displaced-wall form: the effective area ratio
  shrinks the core (eps_eff = eps * (1 - delta*/r_exit)**2) for this
  internal flow; external-flow displacement conventions do not apply.
- Double-counting the cea band: cea-rocket-combustion's
  isp_with_efficiency remains the c-star and user-supplied quick-look
  band tool; this leaf supplies only the computed divergence and
  boundary-layer share (about 0.97 of the ideal at the worked
  example), so applying both to the same ideal Isp double counts the
  nozzle side.

## Related leaves

- propulsion/rocket/nozzle-design: the ideal attached-flow sizing
  (exit Mach, mass flow, exit velocity, static pressure, ideal thrust
  at the area ratio) that feeds this leaf its loss-free baseline.
- propulsion/rocket/rocket-nozzle-flow-separation: the off-design
  overexpanded boundary that takes over once the wall flow separates.
- propulsion/combustion/cea-rocket-combustion: the ideal Isp ceiling
  and the c-star side of the efficiency band this leaf computes the
  nozzle share of.
- propulsion/rocket/rocket-gravity-loss: a different loss class
  (trajectory), kept separate from the nozzle-side bookkeeping.
- propulsion/electric/hall-thruster: ion-optics divergence in its
  electric context only, no gasdynamic overlap.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rocket_nozzle_divergence_loss.py

The test covers the module constants and 1/7-power profile shape, the
conical divergence factor at the reference half-angles and its
monotonic fall, the bell contour efficiency and its validation, the
bell-to-conical ratio and its unit-ratio identity, the turbulent
displacement thickness worked value and growth scaling, the momentum
loss fraction and the theta profile identity, the displaced-core
effective exit area ratio and its limits, the no-loss thrust and Isp
identities, the full worked-example delivered chains for the 15-degree
conical and the 80-percent bell, the bell/conical delivered-ratio
verdict, the half-angle sensitivity peak and design band, and the
ValueError rejection of every non-physical input class across the
module, plus import purity and determinism.

## Compliance

- Standards referenced, not reproduced: ECSS (ecss) frames the space
  propulsion context per standards-map.yaml; the divergence,
  boundary-layer and delivered-thrust relations above are standard
  engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false. The model never re-derives
  the ideal exit Mach or mass flow: those are nozzle-design inputs.

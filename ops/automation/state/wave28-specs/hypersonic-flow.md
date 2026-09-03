# Wave-28 leaf spec: hypersonic-flow (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/hypersonic-flow/
- Pack: high-speed (existing siblings: normal-shock, oblique-shock,
  prandtl-meyer, shock-expansion-airfoil, supercritical-airfoil,
  swept-wing-aerodynamics, transonic-similarity, wave-drag-area-rule)
- Standards ids: naca-tr-824  (Ledger Standard: naca-tr-824)
- Family: aerodynamics

## Claim

Estimate the aerodynamic forces on a body in hypersonic flow with
modified Newtonian impact theory: compute the stagnation pressure
behind the normal shock with the Rayleigh pitot relation, derive the
finite-Mach stagnation pressure coefficient, evaluate the local
pressure coefficient on a surface from its inclination with the
modified Newtonian sine-squared law, integrate the pressure over a
sphere, a cone, and an inclined flat plate into force coefficients,
and apply the hypersonic vacuum limit for shadowed surfaces. Produces
the stagnation pressure coefficient, the local pressure coefficients,
the sphere drag coefficient, the cone axial-force coefficient, the
flat-plate lift and drag, and the lift to drag ratio that gate
hypersonic force estimation.

Does NOT do: tabulate general normal shock relations (normal-shock
owns the five shock ratios); compute expansion fans or supersonic
airfoil patches (prandtl-meyer, shock-expansion-airfoil); analyze
transonic or swept effects (supercritical-airfoil, transonic-
similarity, swept-wing-aerodynamics); size the entry trajectory or
the heating environment (space-systems entry-descent-landing owns
the corridor, ballistic coefficient, and Sutton-Graves heating);
analyze ramjet or inlet propulsion cycles at high Mach (propulsion
ramjet-cycle and ramjet-inlet).

## Model (implement exactly)

Module constants:
- GAMMA = 1.4 (default), D2R = 0.017453292519943295.
- Cp_max at infinite Mach for gamma 1.4 approaches 1.839 (documented
  in the body as the modified Newtonian limit).

Functions:
- rayleigh_pitot_ratio(M, gamma=GAMMA) -> float:
  p02/p1 = ((gamma+1)^2*M^2/(4*gamma*M^2 - 2*(gamma-1)))^(gamma/
  (gamma-1)) * ((2*gamma*M^2 - gamma + 1)/(gamma+1)).
  ValueError on M <= 1.0 (subsonic or sonic not allowed) or gamma <= 1.
- cp_stagnation(M, gamma=GAMMA) -> float: Cp_max(M) =
  2/(gamma*M^2) * (rayleigh_pitot_ratio(M, gamma) - 1).
- newtonian_cp(theta_deg, M, gamma=GAMMA) -> float:
  cp_stagnation * sin(theta)^2. ValueError on theta outside [0, 90].
- cp_vacuum(M, gamma=GAMMA) -> float: -2/(gamma*M^2) (pressure
  ratio p->0 limit for a shadowed surface).
- sphere_drag_coefficient(M, gamma=GAMMA) -> float:
  cp_stagnation(M, gamma)/2 (integrated modified Newtonian pressure
  over a hemisphere, frontal-area reference).
- cone_axial_force_coefficient(half_angle_deg, M, gamma=GAMMA) ->
  float: cp_stagnation * sin(half_angle)^2 (axial force on a sharp
  cone at zero incidence, base-area reference).
- flat_plate_coefficients(alpha_deg, M, gamma=GAMMA) -> dict:
  windward Cp = newtonian_cp(alpha, M, gamma); leeward Cp = 0.0
  (Newtonian shadow); normal-force coefficient CN = Cp_windward -
  Cp_leeward (per unit planform area); CL = CN*cos(alpha);
  CD = CN*sin(alpha); returns {cp_windward, cp_leeward, cn, cl, cd,
  ld_ratio}. ValueError on alpha outside [0, 45].
- analyze_body(body_type, params, M, gamma=GAMMA) -> dict: dispatches
  to the sphere/cone/flat-plate functions and returns the coefficient
  set plus the stagnation Cp and the pitot ratio.
ValueError on: M <= 1.0 anywhere, gamma <= 1, negative geometry.

## Worked example

gamma 1.4.
- rayleigh_pitot_ratio(2.0) = 5.640 (assert within 1e-3; known
  pitot value at M 2).
- rayleigh_pitot_ratio(5.0) = 32.65 (assert within 0.05).
- rayleigh_pitot_ratio(8.0): base = 5.76*64/(5.6*64 - 0.8) =
  368.64/357.6 = 1.03087; ^3.5 = 1.1124; second = (2*1.4*64 - 0.4)/
  2.4 = 178.8/2.4 = 74.5; p02/p1 = 82.87 (assert within 0.1).
- cp_stagnation(8.0) = 2/(1.4*64)*(82.87 - 1) = 0.022321*81.87 =
  1.8275 (assert within 0.002; the gamma-1.4 infinite-M limit 1.839
  is approached from below).
- sphere_drag_coefficient(8.0) = 0.9137 (assert within 0.001).
- cone_axial_force_coefficient(20.0, 8.0): sin(20 deg) = 0.34202,
  squared 0.11698; CA = 1.8275*0.11698 = 0.2138 (assert within
  0.0005).
- flat_plate_coefficients(10.0, 8.0): cp_windward = 1.8275*
  sin(10 deg)^2 = 1.8275*0.030154 = 0.05511; cn = 0.05511;
  cl = 0.05511*cos(10 deg) = 0.05511*0.98481 = 0.05427;
  cd = 0.05511*sin(10 deg) = 0.05511*0.17365 = 0.009570;
  ld_ratio = 5.671 (assert each within 1e-3 of the module value and
  the module value within 1e-3 of these).
- cp_vacuum(8.0) = -2/(1.4*64) = -0.02232 (assert within 1e-4).
- M 5 sphere: cp_stagnation(5.0) = 2/(1.4*25)*(32.65-1) =
  0.057143*31.65 = 1.8086; sphere Cd = 0.9043 (assert).
- ValueErrors on M 1.0, M 0.8, alpha 60, theta -5, gamma 1.0.
Keep at least 16 test methods: pitot at M 2/5/8, pitot at M 1.2 (check
it exceeds 1.89 and monotonic), cp_stagnation at 5 and 8 and the limit
approach, sphere Cd, cone CA at 20 and 40 deg, flat plate at 0 and 10
and 30 deg (cl/cd), ld_ratio, vacuum limit, analyze_body dispatch,
ValueErrors.

## Corpus tasks (ids w28-hypersonic-flow-1/2)

Distinctive tokens: hypersonic flow, modified Newtonian theory,
Newtonian impact pressure, stagnation pressure coefficient, blunt body
drag, sphere drag coefficient, cone axial force, hypersonic vacuum
limit. Avoid: normal shock ratios, stagnation pressure loss tables
(normal-shock); Sutton-Graves heating, ballistic coefficient, entry
corridor (space-systems entry-descent-landing); ramjet inlet, specific
impulse, contraction ratio (propulsion ramjet-cycle / ramjet-inlet).

1. "estimate the drag of the blunt reentry body at hypersonic speed
   with modified Newtonian theory from the stagnation pressure
   coefficient behind the normal shock"
2. "compute the hypersonic lift and drag of the inclined flat plate
   and the axial force of the sharp cone with the Newtonian sine
   squared pressure law"

## SKILL body notes

Pair with normal-shock (the pitot relation neighbor) and the
supersonic high-speed leaves (boundary at Mach ~ 5 where Newtonian
methods become the standard estimate). The body must note the method
is the classical engineering estimate for hypersonic continuum flow,
not a CFD replacement, and that Cp_max tends to 1.839 for gamma 1.4.
NACA TR-824 referenced (name only) as the classic compressible-flow
data source.

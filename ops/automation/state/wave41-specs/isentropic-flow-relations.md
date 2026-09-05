# Wave-41 leaf spec: isentropic-flow-relations (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/isentropic-flow-relations/
- Pack: high-speed (verified present at prep with the 12 sibling leaves
  aerodynamic-heating, bow-shock-standoff, flat-plate-skin-friction-heating,
  hypersonic-flow, normal-shock, oblique-shock, prandtl-meyer,
  shock-expansion-airfoil, supercritical-airfoil, swept-wing-aerodynamics,
  transonic-similarity and wave-drag-area-rule). Closest siblings:
  normal-shock (shock-state ratios only, no isentropic total to static
  conversion: its frontmatter claim is "find the downstream Mach number,
  static pressure, density, and temperature ratios across the shock, and the
  stagnation pressure loss from the upstream Mach number"),
  prandtl-meyer (expansion-fan relations only: "derive the expansion angle
  from the Mach number, find the downstream Mach number after the flow turns
  away from itself by a given angle"; its p2/p1 uses the same p0/p function
  internally but the leaf owns the fan, not the ratio conversion),
  oblique-shock (wave-angle solving only: "compute the wave angle beta from
  the upstream Mach number M1 and the flow deflection angle theta with the
  theta-beta-M relation"),
  shock-expansion-airfoil (patches oblique-shock and prandtl-meyer over a
  diamond airfoil; no area-Mach relation),
  transonic-similarity (compressibility corrections: "estimate the critical
  Mach number at which local flow first reaches sonic speed"; the isentropic
  sonic limit appears only as a critical pressure coefficient),
  hypersonic-flow (modified Newtonian impact theory and the Rayleigh pitot
  stagnation pressure behind the normal shock; no isentropic area relation).
  Cross-family neighbors that touch the same physics in an application
  context: propelling-nozzle (gas-turbine pack: "decide the choked or
  unchoked regime from the nozzle pressure ratio against the critical ratio
  1.851, size the throat area from the design mass flow and total conditions
  under the choked flow relation"),
  ramjet-inlet (ramjet pack: "compute the diffuser total pressure recovery
  at the flight Mach number from the isentropic limit or from the normal
  shock standing at the cowl lip"),
  rocket/nozzle-design (rocket pack: "compute the exit Mach number for a
  target area ratio, the choked mass flow through the throat, the exit
  velocity and the exit static pressure, and the ideal thrust with the
  pressure term", chamber-conditions context only) and
  cross-cutting/numerics/root-finding (generic solving: "determine the root
  of a nonlinear scalar equation f(x) = 0 numerically with the bisection
  method, Newton-Raphson, the secant method, or fixed-point iteration").
  Whole-tree greps at prep: "choked" and "A/A*" = 0 hits in
  skills/aerodynamics; "isentropic" hits only as the mentions above and the
  prandtl-meyer tag isentropic-expansion. GENUINE AERO gap (fresh probe): no
  high-speed leaf converts a Mach number into the isentropic total to static
  ratio set as its deliverable, recovers the Mach number from an area ratio
  A/A* on both branches, or computes choked mass flow for a passage.
- Standards id: naca-tr-824 (reference-only, matching every high-speed
  sibling and present in standards-map.yaml). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Convert a Mach number into the isentropic total to static ratios of a
perfect gas flow at gamma 1.4: total temperature ratio T0/T =
1 + (gamma - 1) / 2 * M^2 with the total pressure ratio p0/p and total
density ratio rho0/rho from the isentropic exponents, and rebuild total
conditions from a static state and Mach number; recover the Mach number
that produces a given area ratio A/A* from the area-Mach relation
A/A* = (1/M) * ((2/(gamma+1)) * (1 + (gamma-1)/2 * M^2))^((gamma+1)/(2
(gamma-1))) by deterministic bisection, returning the subsonic root on the
low branch or the supersonic root on the high branch for the same area
ratio, the two roots that size supersonic wind tunnel contractions and test
sections; and compute the choked mass flow a passage passes at its sonic
throat from the total pressure, total temperature and throat area through
the mass flow parameter. Produces the three total to static ratios, the
A/A* value for a given Mach number, both Mach roots for a given A/A*, and
the choked mass flow in kg/s, the gate numbers for duct, wind tunnel and
internal passage analysis at any Mach. Does NOT do: static ratios across a
normal shock, oblique shock or expansion fan (normal-shock, oblique-shock,
prandtl-meyer, shock-expansion-airfoil); pitot or impact stagnation behind a
shock (hypersonic-flow); compressibility corrections and critical Mach
(supercritical-airfoil, transonic-similarity, swept-wing-aerodynamics);
airspeed indicator inversions (airspeed-conversion); nozzle throat sizing,
gross thrust or rocket nozzle design (propelling-nozzle, rocket
nozzle-design); inlet starting or diffuser recovery (ramjet-inlet); generic
root solving with a method of choice (root-finding). Deterministic closed
forms and a fixed bisection schedule only, no seeded iteration schemes.

## Model (implement exactly)

Functions (pure stdlib, math only):
- total_static_ratios(mach) -> dict {"t0_over_t", "p0_over_p",
  "rho0_over_rho"} with t0_over_t = 1 + 0.5 * (GAMMA - 1) * mach**2,
  p0_over_p = t0_over_t ** (GAMMA / (GAMMA - 1)) and rho0_over_rho =
  t0_over_t ** (1 / (GAMMA - 1)); all three are 1.0 at mach 0.0; ValueError
  if mach < 0.
- area_ratio(mach) -> float (1 / mach) * ((2 / (GAMMA + 1)) * (1 + 0.5 *
  (GAMMA - 1) * mach**2)) ** ((GAMMA + 1) / (2 * (GAMMA - 1))), the area-Mach
  relation with A* the sonic throat area; monotone decreasing on the
  subsonic branch, monotone increasing on the supersonic branch, minimum
  exactly 1.0 at mach = 1.0; ValueError if mach <= 0.
- mach_from_area_ratio(aa, subsonic = True) -> float, deterministic
  bisection of f(M) = area_ratio(M) - aa on the bracket [SUB_LO, SUB_HI] =
  [0.05, 0.99] for the subsonic root and [SUP_LO, SUP_HI] = [1.01, 20.0]
  for the supersonic root, halving until the bracket width is below
  MACH_TOL = 1e-12 (max 200 iterations, no RNG, identical inputs give
  identical bits) and returning the bracket midpoint. Edge and domain rules,
  in order: aa < 1.0 raises ValueError (the sonic-throat floor, no physical
  area ratio below 1.0); aa == 1.0 returns 1.0 exactly for either branch;
  subsonic aa below area_ratio(SUB_HI) re-brackets on [SUB_HI, 1.0] and
  supersonic aa below area_ratio(SUP_LO) re-brackets on [1.0, SUP_LO] so the
  near-sonic roots stay inside a sign-change bracket; subsonic aa at or
  above area_ratio(SUB_LO) = 11.591443867187 raises ValueError (root below
  the 0.05 bracket floor, documented domain limit) and supersonic aa above
  area_ratio(SUP_HI) = 15377.343750000022 raises ValueError (root above the
  20.0 bracket ceiling, documented domain limit).
- static_to_total(p_static, t_static, mach) -> dict {"p0", "t0"} with p0 =
  p_static * p0_over_p and t0 = t_static * t0_over_t from the same closed
  forms, rebuilding total conditions from a static state; ValueErrors if
  p_static <= 0, t_static <= 0 or mach < 0. Round trip with
  total_static_ratios is exact to floating point.
- choked_mass_flow(p0, t0, area_star) -> float MFP * p0 * area_star /
  sqrt(t0) with the mass flow parameter MFP = sqrt(GAMMA / R) * (2 /
  (GAMMA + 1)) ** ((GAMMA + 1) / (2 * (GAMMA - 1))) = 0.0404184199
  (kg sqrt(K) / (Pa s)), giving mdot in kg/s for p0 in Pa, t0 in K and
  area_star in m2 (the standard choked flow relation, name and paraphrase
  only); ValueError if p0 <= 0, t0 <= 0 or area_star <= 0.
Module constants: GAMMA = 1.4, R = 287.0, MACH_TOL = 1e-12, SUB_LO = 0.05,
SUB_HI = 0.99, SUP_LO = 1.01, SUP_HI = 20.0.

Identity to test: area_ratio(1.0) = 1.0 exactly; area_ratio(2.0) =
1.6875 exactly and area_ratio(0.5) = 1.33984375 exactly (closed forms);
mach_from_area_ratio round trips: mach_from_area_ratio(area_ratio(m), m on
its own branch) returns m within 1e-10 for m = 0.5, 2.0 and 3.0; the
supersonic root for A/A* = 1.6875 is exactly 2.0; static_to_total inverts
total_static_ratios to machine precision; choked mass flow scales linearly
with p0 and with area_star and as 1 / sqrt(t0), and mdot * sqrt(t0) / (p0 *
area_star) = MFP for every input; both roots of one area ratio bracket 1.0
(subsonic root below 1.0, supersonic root above 1.0) and approach 1.0 as
the ratio approaches 1.0.

## Worked example

Air, gamma = 1.4, R = 287.0. Supersonic wind tunnel test section at
M = 2.0 fed from a stilling chamber at p0 = 101325 Pa, T0 = 288.15 K:
T0/T = 1.8 exactly, p0/p = 7.82445, rho0/rho = 4.34692 and A/A* =
1.6875 exactly (the classic supersonic value). mach_from_area_ratio(1.6875,
subsonic = False) returns 2.000000000000 within the 1e-12 bracket width,
and the subsonic root for the same area ratio, the contraction-side Mach at
the same area station, is 0.372244486203. For the common contraction ratio
A/A* = 2.0 the supersonic root is 2.197198121652 and the subsonic root is
0.305903834189.
- Subsonic cruise point M = 0.85: T0/T = 1.1445, p0/p = 1.60382, rho0/rho =
  1.40133, A/A* = 1.02067; static_to_total on a static state of 30000 Pa
  and 220 K returns p0 = 48114.562843 Pa and t0 = 251.79 K.
- Choked flow through the passage: p0 = 101325 Pa, T0 = 288.15 K and a
  sonic throat of 0.01 m2 give mdot = 2.4126072679 kg/s. Doubling p0 to
  202650 Pa gives 4.8252145358 kg/s and doubling area_star to 0.02 m2 gives
  the same 4.8252145358 kg/s (linear in both), while quadrupling T0 to
  1152.6 K halves the flow to 1.2063036339 kg/s; the ratio mdot *
  sqrt(T0) / (p0 * area_star) = 0.0404184199, the mass flow parameter, for
  every one of these points.
- Rebuilding the static state at M = 2.0 from the stilling chamber gives
  p = 12949.793543 Pa and T = 160.083333 K; feeding those back through
  static_to_total returns p0 = 101325.000000000 and t0 = 288.150000000, a
  round trip exact to the last printed digit.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds, computed by running the prep anchor scripts
/tmp/w41spec/anchor_isentropic.py and /tmp/w41spec/helper_isentropic.py
(prep-verified by stdlib math).

## Validation list (contract test must include)

- total_static_ratios(0.85): t0_over_t 1.1445 within 1e-12, p0_over_p
  1.6038187614 within 1e-9, rho0_over_rho 1.4013270087 within 1e-9;
  total_static_ratios(2.0): 1.8, 7.8244490669 and 4.3469161483 within
  1e-9; total_static_ratios(3.0): 2.8, 36.7327218050 and 13.1188292161
  within 1e-9; total_static_ratios(0.0) all 1.0; ValueError at negative
  mach.
- area_ratio(1.0) = 1.0 within 1e-15; area_ratio(2.0) = 1.6875 within
  1e-12; area_ratio(0.5) = 1.33984375 within 1e-12; area_ratio(0.85) =
  1.020668536305 within 1e-9; monotone decreasing on (0, 1] and increasing
  on [1, 20] with minimum 1.0 at mach 1.0; ValueError at mach 0 and
  negative.
- mach_from_area_ratio(1.6875, subsonic = False) = 2.0 within 1e-10;
  (1.6875, True) = 0.372244486203 within 1e-10; (2.0, False) =
  2.197198121652 within 1e-10; (2.0, True) = 0.305903834189 within 1e-10.
- Round trips: mach_from_area_ratio(area_ratio(m), branch of m) = m within
  1e-10 for m = 0.5, 2.0 and 3.0 on their own branches.
- Near-sonic edge: aa = 1.00005 gives subsonic root 0.992270777840 and
  supersonic root 1.007762554875 within 1e-10 (re-bracket on [0.99, 1.0]
  and [1.0, 1.01]); aa = 1.0 returns 1.0 for both branches; aa = 0.999
  raises ValueError.
- Domain ValueErrors: subsonic aa = 12.0 (above area_ratio(0.05) =
  11.591443867187) and supersonic aa = 16000.0 (above area_ratio(20.0) =
  15377.343750000022) raise ValueError.
- static_to_total(30000.0, 220.0, 0.85): p0 48114.562843 within 1e-6, t0
  251.79 within 1e-9; round trip on the worked example static state is
  exact within 1e-6; ValueErrors at non-positive p_static, t_static and at
  negative mach.
- choked_mass_flow(101325.0, 288.15, 0.01) = 2.4126072679 within 1e-8;
  doubling p0 or area_star doubles the flow to 4.8252145358 within 1e-8;
  t0 = 1152.6 K halves it to 1.2063036339 within 1e-8; the MFP identity
  mdot * sqrt(t0) / (p0 * area_star) = 0.0404184199 within 1e-10;
  ValueErrors at p0 0, t0 0, t0 negative and area_star 0.
- Determinism: two calls of mach_from_area_ratio on the same input return
  identical bits; dict keys exactly t0_over_t, p0_over_p, rho0_over_rho for
  total_static_ratios, p0 and t0 for static_to_total.
- ValueErrors across the module: mach < 0 in total_static_ratios and
  static_to_total, mach <= 0 in area_ratio, non-positive p0, t0, area_star
  in choked_mass_flow.

## Corpus fragment (eval/hit1-wave41-isentropic-flow-relations.yaml)

Query 1 (copy verbatim):
  "for the isentropic flow of air at mach 2.0 in a wind tunnel passage compute the total to static pressure, temperature and density ratios and the choked mass flow the passage passes from its total pressure, total temperature and sonic throat area"
  intent: "aerodynamics; isentropic total to static ratio conversion and choked mass flow through a passage"
  expected_skill: "aerodynamics/high-speed/isentropic-flow-relations"
Query 2 (copy verbatim):
  "find both roots of the isentropic area ratio relation: the subsonic mach number and the supersonic mach number that give an A over A star of 1.6875 for the flow in the wind tunnel contraction"
  intent: "aerodynamics; both subsonic and supersonic roots of the area-Mach relation for a given A over A star in isentropic duct flow"
  expected_skill: "aerodynamics/high-speed/isentropic-flow-relations"
Task ids: w41-isentropic-flow-relations-1 and -2.
Routing collision notes: eval/hit1-corpus.yaml already routes w17-root-
finding-2 ("solve for the Mach number root in the isentropic compressible
flow relation with the secant method") to cross-cutting/numerics/root-
finding, nz1 (rocket nozzle area ratio and exit Mach) to
propulsion/rocket/nozzle-design, rii1/rii2 (Kantrowitz starting and
isentropic versus normal shock recovery) to propulsion/ramjet/ramjet-inlet,
and the cold-gas-thruster and propelling-nozzle and valve tasks to their
propulsion and vehicle-design leaves on choked flow. The two queries above
route ONLY to the new leaf: they carry the isentropic total to static and
area-Mach vocabulary (total to static, A over A star, isentropic flow, both
roots, wind tunnel) with no nozzle, rocket, chamber, thruster, valve,
shock, expansion or method tokens, so no token set collides with those
tasks.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must convert a Mach number into the
isentropic total to static ratios of a compressible flow:" and include the
outputs in the Claim. First tag: isentropic-flow-relations. Additional tags
ONLY: total-to-static-ratio, mach-from-area-ratio, choked-mass-flow. NEVER
single generic words (isentropic, mach, area, ratio, mass, flow, subsonic,
supersonic, compressible, pressure, temperature, density, throat, duct,
passage, tunnel). 50-150 words, <=1000 chars, no em dash, no banned
content-policy word, action verb present. The Claim and SKILL body may name
"deterministic
bisection" as the implementation note, but description, tags and corpus
queries must route on the physics vocabulary above and never on a generic
solving method.

FORBIDDEN TOKENS (belong to siblings): normal-shock-relations,
shock-ratios, stagnation-pressure-loss, total-pressure-loss-across-shock
(normal-shock); theta-beta-m, wave-angle, deflection-angle, shock-polar,
weak-solution, strong-solution, detached-shock, compression-corner
(oblique-shock); prandtl-meyer-angle, expansion-fan, turning-angle,
isentropic-expansion, downstream-mach (prandtl-meyer); shock-expansion,
diamond-airfoil, double-wedge, surface-pressure-integration
(shock-expansion-airfoil); modified-newtonian, newtonian-impact,
rayleigh-pitot, stagnation-pressure-coefficient, vacuum-limit
(hypersonic-flow); prandtl-glauert, karman-tsien, compressibility-
correction, critical-mach-number, critical-pressure-coefficient
(transonic-similarity, supercritical-airfoil, swept-wing-aerodynamics);
sears-haack, area-rule, cross-sectional-area-distribution (wave-drag-area-
rule); billig, standoff-distance, shock-layer-thickness (bow-shock-
standoff); sutton-graves, stagnation-point-heating,
radiation-equilibrium-temperature (aerodynamic-heating); recovery-factor,
adiabatic-wall-temperature, cold-wall-heat-flux, reference-temperature-
method, reynolds-analogy, sutherland-viscosity
(flat-plate-skin-friction-heating); nozzle-design, rocket-nozzle, exit-
mach, ideal-thrust, expansion-ratio, chamber-pressure, characteristic-
velocity (rocket/nozzle-design); propelling-nozzle, convergent-jet-nozzle,
nozzle-throat-area, gross-thrust-pressure-term, critical-pressure-ratio
(propelling-nozzle); kantrowitz, starting-criterion, contraction-ratio,
diffuser-pressure-recovery, inlet-recovery (ramjet-inlet); secant-method,
newton-raphson, fixed-point-iteration, root-finding, zero-finding,
nonlinear-equation, initial-guess, convergence-criteria
(cross-cutting/numerics/root-finding). The word "nozzle" and the generic
method names never appear in description, tags or corpus queries.

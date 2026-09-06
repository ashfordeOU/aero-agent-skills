# Wave-44 leaf spec: nozzle-area-ratio-selection (propulsion,
# rocket pack)

- Path: skills/propulsion/rocket/nozzle-area-ratio-selection/
- Pack: rocket (present siblings cold-gas-thruster,
  combustion-chamber-design, hybrid-rocket-motor, injector-design,
  nozzle-design, propellant-selection, rocket-engine-cycle,
  rocket-gravity-loss, rocket-nozzle-divergence-loss,
  rocket-nozzle-flow-separation, rocket-sizing, rocket-staging,
  solid-rocket-motor, thrust-chamber-cooling, thrust-vector-control;
  adjacent fences in propulsion/combustion/cea-rocket-combustion and
  propulsion/electric).
- Provenance: wave-44 leaf-plan entry (ops/automation/state/
  wave44-leaf-plan.md, line 38) dispatches this leaf from probe PROP 46
  task-1 rank 2, flagged GO-thin MED-overlap: "design-altitude
  expansion-ratio selection: solve epsilon such that Pe(epsilon) =
  Pa(h_design), sea-level/vacuum/design-
  altitude Isp at chosen epsilon, flow-separation minimum-epsilon
  guard". SPEC-TIME TRIAGE (leaf-plan line 152 gate) DONE FIRST:
  nozzle-design SKILL.md body read IN FULL (skills/propulsion/rocket/
  nozzle-design/SKILL.md, 78 lines). Its optimum_expansion is a
  verdict function on a GIVEN area ratio (returns over/under/optimum
  expansion strings against the ambient); its workflow step 2 is
  "Pick the target area ratio and solve the exit Mach number with
  exit_mach_from_area_ratio" and step 5 "judge the expansion with
  optimum_expansion". The body contains NO solver that returns the
  epsilon satisfying Pe(eps) = Pa(h_design) as an output: the ratio
  is always a caller-supplied input there, never a solved unknown.
  Genuine overlap NOT found: GO, no DECLINE file written (triage gate
  cleared; reserve-pool fallback in the leaf plan not needed).
- Claim fences (quoted from the sibling frontmatter and body at prep,
  none owns the design-altitude expansion-ratio SELECTION, the inverse
  solve of Pe(eps) = Pa(h_design)):
  - nozzle-design (this pack) is the FORWARD ideal attached-flow
    sizing at a given geometry. Its description reads "compute the
    exit Mach number for a target area ratio, the choked mass flow
    through the throat, the exit velocity and the exit static
    pressure, and the ideal thrust with the pressure term. Produces
    the nozzle area ratio, exit Mach number, mass flow, exit
    velocity, and thrust, plus the expansion verdict against the
    ambient pressure" and its workflow reads "Pick the target area
    ratio and solve the exit Mach number" then "judge the expansion
    with optimum_expansion". The new leaf is the inverse of that
    forward envelope: the area ratio is the OUTPUT of the solve here
    (matched to a design-altitude ambient), never an input. The new
    leaf MUST NOT return optimum_expansion-style over/under verdict
    strings and MUST NOT present a forward nozzle design as a
    deliverable: its exit-state evaluation exists only to close the
    selection loop and to report the isp triple at the CHOSEN ratio.
    nozzle-design stays the owner of forward sizing and of the
    expansion-state explanation.
  - cea-rocket-combustion (propulsion/combustion) supplies the ideal
    chamber gas (Tc, Mw, gamma, c-star) and the ideal Isp at two
    FIXED ambient choices only. Its quick reference pins "Ideal
    vacuum specific impulse (Pe = 0)" and "Ideal sea-level specific
    impulse: the same exhaust velocity formula with the exit pressure
    equal to the ambient pressure, Pe = 101325 Pa", and its pitfalls
    fence reads "Routing nozzle geometry here: area ratio, exit Mach
    and expansion belong to nozzle-design; this leaf only provides
    the ideal Isp from the chamber gas, not a nozzle design." The
    implied expansion ratio there is fixed by the chosen pe (0 or
    101325 Pa); nothing in cea selects an expansion ratio for a
    design altitude, and the isp_with_efficiency band multiplier
    stays with cea (this leaf uses no efficiency bands).
  - rocket-nozzle-flow-separation (this pack) OWNS the off-design
    separation boundary. Its description reads "apply the
    separation-pressure-ratio criterion (wall static pressure falling
    to K_SEP times ambient, K_SEP 0.4) to decide whether the wall
    flow separates, find the separation-station area ratio from the
    isentropic area-Mach relation at the separation pressure, and
    estimate the separation altitude where the nozzle un-separates".
    That leaf solves the STATION (A_sep/At) and the ALTITUDE of
    un-separation as deliverables. The new leaf uses the same
    documented K_SEP = 0.4 constant ONLY as a guard decision on the
    ratio IT selected: attached iff the exit static pressure at the
    chosen eps stays at or above K_SEP * pa at the operating ambient.
    The guard is a pure boolean evaluation of Pe(eps), computed
    directly with NO separation-station solve and NO separation-
    altitude output; the station, the separated-thrust loss and the
    side-load flag remain flow-separation deliverables. The new leaf
    carries none of the separation-pressure-ratio,
    separation-station, separation-altitude, overexpanded-nozzle or
    side-load-regime tokens.
  - rocket-nozzle-divergence-loss (this pack, wave-43) takes the
    geometry as a given INPUT (its claim: "the ideal attached-flow
    state (ve, pe, Ae, mdot) is the nozzle-design output at the same
    geometry") and computes the divergence and boundary-layer
    corrections on top of it. The wave-43 fold of an
    expansion-ratio-selection leaf into divergence-loss did NOT
    happen (verified at wave-44 prep: divergence-loss consumes eps,
    it never picks it); the new leaf produces the eps that the
    divergence-loss chain later consumes. No overlap; the new leaf
    has no contour-loss bookkeeping (no conical divergence factor,
    no bell contour efficiency, no boundary-layer displacement).
  - Propulsion electric leaves (gridded-ion-thruster, hall-thruster)
    never mention expansion-ratio selection; their optics context is
    ion accelerator grid geometry, not gasdynamic nozzle area
    selection; no fence overlap.
  - Whole-tree greps at prep (real counts): the combined token set
    design-altitude-expansion-ratio | matched-expansion-ratio |
    area-ratio-selection | nozzle-area-ratio-selection |
    expansion-ratio-selection | matched-expansion | design-altitude
    returns ZERO hits inside eval/hit1-corpus.yaml, and exactly ONE
    hit inside skills/: the comment "the matched-expansion identity"
    at line 280 of the wave-43 rocket-nozzle-divergence-loss CONTRACT
    TEST file (skills/propulsion/rocket/rocket-nozzle-divergence-
    loss/scripts/test_rocket_nozzle_divergence_loss.py), which names
    its ve/g0 identity anchor, not a selection claim. The nearest
    corpus tasks route elsewhere: the nozzle-design tasks (nz1, nz2:
    "compute the rocket nozzle area ratio and exit mach number for
    the design chamber conditions" and "calculate the ideal thrust
    with the pressure term and check the nozzle expansion against the
    ambient pressure") are FORWARD tasks with no design-altitude
    ambient target, and the rocket-nozzle-flow-separation tasks
    (w38-rocket-nozzle-flow-separation-1/-2) route on the
    separation-pressure-ratio criterion, the separation-station area
    ratio and the separation altitude. GENUINE propulsion gap (probe
    receipt PROP 46 task-1 rank 2, GO): no leaf solves the inverse
    design-altitude expansion-ratio selection with the isp triple at
    the chosen ratio.
- Standards id: ecss (reference-only, present in standards-map.yaml
  lines 94-103, sibling rocket convention: nozzle-design,
  rocket-nozzle-flow-separation and cea-rocket-combustion all carry
  standards: [id: ecss, reference-only: true]). Ledger Standard:
  ecss.
- Family: propulsion

## Claim

Select the rocket nozzle expansion ratio for a design altitude by
solving the inverse isentropic problem Pe(eps) = Pa(h_design): find
the matched expansion ratio eps* whose ideal exit static pressure
equals the ambient pressure at the design altitude, on the monotone
supersonic branch of the area-Mach relation (exit Mach root by
bisection, expansion ratio root by bisection over the monotone
decreasing Pe(eps)). The ambient pressure comes from a documented
ISA-76 three-layer model (troposphere 0-11 km with the 0.0065 K/m
lapse, isothermal stratosphere 11-20 km at 216.65 K, 0.001 K/m
lapse 20-32 km). Produces the design-altitude matched expansion
ratio eps* with the matched exit Mach and exit static pressure, the
ambient pressure at the design altitude, and the delivered specific
impulse triple at the chosen eps: sea-level Isp (pa = 101325 Pa),
vacuum Isp (pa = 0), and design-altitude Isp (pa = Pa(h_design)),
each from the ideal rocket relations Isp = (mdot * ve + (Pe - pa) *
eps * At) / (mdot * g0) with the choked mass flow and the isentropic
exit velocity; at the matched ratio the design-altitude Isp equals
ve/g0 exactly because the pressure term vanishes. Also produces the
attached-flow guard decision on the chosen ratio at any operating
ambient: attached (True) iff the exit static pressure stays at or
above K_SEP * pa with K_SEP = 0.4, the documented
rocket-nozzle-flow-separation criterion constant used here as a
verdict-only minimum-eps guard (no separation-station solve, no
separation-altitude output). Does NOT do: forward nozzle sizing at a
given area ratio, the exit-state explanation, or over/under
expansion verdict strings against the ambient (nozzle-design, the
forward envelope this leaf inverts); thermochemistry, c-star or the
ideal Isp at the fixed Pe = 0 / Pe = 101325 choices and the
isp_with_efficiency bands (cea-rocket-combustion); the
separation-station area ratio, the separation altitude where the
nozzle un-separates, the separated-thrust loss or the side-load
flag of an overexpanded nozzle (rocket-nozzle-flow-separation, which
owns everything downstream of the guard decision); divergence
factor, bell contour efficiency or boundary-layer thrust loss at the
chosen geometry (rocket-nozzle-divergence-loss, which consumes the
eps this leaf selects); throat sizing or chamber volume
(combustion-chamber-design); gravity, drag or trajectory losses
(rocket-gravity-loss); engine cycle, propellant choice or thrust
chamber cooling. Gamma and R are supplied by the caller
(representative hot combustion products); the module constants are
documented below.

## Model (implement exactly)

Pure stdlib, math only, deterministic, closed form plus two nested
bisections. Module constants: G0 = 9.80665 m/s^2 (standard gravity,
sibling rocket convention), K_SEP_DEFAULT = 0.4 (the documented
sibling rocket-nozzle-flow-separation wall-separation criterion
constant, guard-only usage here), and the ISA-76 layer constants
ISA_P0 = 101325.0 Pa, ISA_T0 = 288.15 K, ISA_L1 = 0.0065 K/m,
ISA_H1 = 11000.0 m, ISA_H2 = 20000.0 m, ISA_H3 = 32000.0 m,
ISA_R = 287.053 J/(kg K) for dry air, tropopause temperature 216.65 K
and the 20-32 km lapse +0.001 K/m.

Defining relations (pin these exactly; every function below derives
from them):
- Isentropic area-Mach relation: A/A* = (1/M) * ((2/(gamma+1)) *
  (1 + ((gamma-1)/2) * M^2))^((gamma+1)/(2*(gamma-1))). On the
  supersonic branch M >= 1 the relation is strictly increasing in M,
  so the inverse exit_mach_from_area_ratio is a clean bisection
  between the bracket [1, M_hi] with M_hi doubled until the area
  exceeds the target.
- Exit static pressure: Pe(eps) = P0 * (1 + ((gamma-1)/2) *
  M_e^2)^(-gamma/(gamma-1)) with M_e the supersonic root; Pe is
  strictly DECREASING in eps, from the throat-plane ceiling
  Pe(1) = P0 * (2/(gamma+1))^(gamma/(gamma-1)) down toward 0 as eps
  grows without bound. The ceiling bounds the selection: a matched
  supersonic expansion exists only for pa strictly between 0 and
  Pe(1).
- Matched selection (the inverse solve): eps* solves Pe(eps*) = pa
  by bisection over eps on the monotone decreasing Pe(eps), with the
  upper bracket doubled until Pe falls at or below pa. At
  Pe(eps*) = pa the pressure term (Pe - pa) * Ae vanishes by
  construction. No closed-form shortcut replaces the bisection: the
  selection is the inverse of the nozzle-design forward map and the
  module owns that inversion.
- ISA-76 ambient pressure (three layers, 0-32000 m): troposphere
  h <= 11000 m, T = 288.15 - 0.0065*h and p = 101325 *
  (T/288.15)^(G0/(ISA_R * 0.0065)); isothermal stratosphere
  11000 < h <= 20000 m, T = 216.65 K and p = p(11000) *
  exp(-G0*(h - 11000)/(ISA_R * 216.65)); upper layer
  20000 < h <= 32000 m, T = 216.65 + 0.001*(h - 20000) and p =
  p(20000) * (T/216.65)^(-G0/(ISA_R * 0.001)).
- Exit velocity (energy equation): ve(eps) = sqrt(2*gamma/(gamma-1)
  * R * T0 * (1 - (Pe/P0)^((gamma-1)/gamma))), the fully expanded
  ceiling at Pe = 0 being sqrt(2*gamma/(gamma-1) * R * T0).
- Choked mass flow: mdot = (P0 * At / sqrt(T0)) * sqrt(gamma/R) *
  (2/(gamma+1))^((gamma+1)/(2*(gamma-1))), the nozzle-design choked
  relation reproduced here only to normalize the isp triple.
- Delivered Isp at a chosen eps and ambient: Isp = (mdot * ve +
  (Pe - pa) * eps * At) / (mdot * g0). The throat area At cancels
  exactly (Ae/mdot is proportional to eps with the same choked-flow
  factor), so the isp triple depends on the area RATIO and the
  ambient, not on the engine scale; At is kept as a parameter so the
  physical assembly stays explicit.
- Attached-flow guard (verdict only): attached iff
  Pe(eps) >= K_SEP * pa at the operating ambient, evaluated directly
  from the module's own Pe(eps). The guard computes NO
  separation-station eps and NO altitude: when it returns False at an
  ambient, the wall flow would separate there and the
  rocket-nozzle-flow-separation leaf takes over the off-design
  bookkeeping.

Functions (public API, 9 functions, all pure):
- ambient_pressure_at_altitude(h_m) -> float
  the ISA-76 layer model above. ValueError if h_m < 0 or
  h_m > 32000.0.
- exit_mach_from_area_ratio(area_ratio, gamma) -> float
  the supersonic-branch root of A/A* = area_ratio by bisection,
  bracket [1, M_hi] with M_hi doubled until the area exceeds the
  target (400 iterations, float-noise closure). ValueError if
  area_ratio <= 1 or gamma <= 1.
- exit_static_pressure(area_ratio, p0, gamma) -> float
  Pe(eps) = p0 * (1 + ((gamma-1)/2) * M^2)^(-gamma/(gamma-1)) with M
  the supersonic root. ValueError if area_ratio <= 1, p0 <= 0 or
  gamma <= 1.
- expansion_matched_area_ratio(p0, gamma, pa) -> float
  the selection solve: the eps with exit_static_pressure(eps, p0,
  gamma) = pa, by bisection over eps (300 iterations) on the
  monotone decreasing branch. ValueError if pa <= 0 (vacuum has no
  finite matched ratio), pa >= p0 * (2/(gamma+1))^(gamma/(gamma-1))
  (ambient at or above the throat-plane ceiling: no supersonic
  matched expansion), p0 <= 0 or gamma <= 1.
- design_altitude_area_ratio(p0, gamma, h_design_m) -> float
  expansion_matched_area_ratio(p0, gamma,
  ambient_pressure_at_altitude(h_design_m)). ValueError set as both
  callers.
- exit_velocity(area_ratio, p0, t0, gamma, r_gas) -> float
  the energy-equation exit velocity above. ValueError if area_ratio
  <= 1 or any of p0, t0, r_gas <= 0 or gamma <= 1.
- choked_mass_flow(throat_area_m2, p0, t0, gamma, r_gas) -> float
  the choked mass flow above. ValueError if any argument <= 0 or
  gamma <= 1.
- delivered_isp(area_ratio, p0, t0, gamma, r_gas, pa,
  throat_area_m2, g0 = G0) -> float
  (mdot * ve + (exit_static_pressure(area_ratio, p0, gamma) - pa) *
  area_ratio * throat_area_m2) / (mdot * g0). The sea-level, vacuum
  and design-altitude values are the same call with pa = 101325.0,
  pa = 0.0 and pa = ambient_pressure_at_altitude(h_design).
  ValueError set as choked_mass_flow plus exit_velocity plus
  pa < 0 (negative ambient rejected; pa = 0 vacuum allowed) and
  g0 <= 0.
- attached_flow_guard(area_ratio, p0, gamma, pa,
  k_sep = K_SEP_DEFAULT) -> bool
  exit_static_pressure(area_ratio, p0, gamma) >= k_sep * pa, the
  verdict-only minimum-eps guard. ValueError set as
  exit_static_pressure plus pa <= 0 or k_sep not in (0, 1].

Identities to test (closed form; assert with isclose/abs bounds,
never exact float equality on computed sums):
- Roundtrip: exit_mach_from_area_ratio(70.0, 1.24) feeds back
  through the area-Mach relation to 70.000000 with relative error
  1.22e-15 (real anchor).
- Boundary: the throat-plane ceiling Pe(1) = P0 *
  (2/(gamma+1))^(gamma/(gamma-1)) = 3897668.7 Pa at P0 = 7.0 MPa,
  gamma = 1.24 (real anchor); expansion_matched_area_ratio raises
  ValueError at pa >= the ceiling (anchor case p0 = 150000.0 Pa,
  gamma = 1.4, pa = 101325.0 Pa, ceiling 81190.5 Pa) and at pa <= 0.
- Matched closure: at the solved eps*, exit_static_pressure minus pa
  prints -0.000 Pa (abs residual below 1e-3 Pa) at every altitude in
  the sweep 0/11/20/30 km (real anchor, four rows).
- Monotone selection: eps* grows strictly with the design altitude
  as pa falls: 8.3061 (0 km), 25.416 (11 km), 75.4961 (20 km),
  251.1241 (30 km) at the worked-example chamber (real anchor), so
  the sea-level matched ratio is the smallest of the four.
- Sibling cross-check: at eps = 70.0 the anchor reproduces the
  wave-43 rocket-nozzle-divergence-loss real values exactly, Me =
  4.931384 and Pe = 6036.738 Pa (same gas and throat), proving the
  forward map the module inverts is the nozzle-design map.
- Matched-isp identity: delivered_isp at eps* and the design ambient
  pa = Pa(h_design) equals exit_velocity/g0 exactly (the pressure
  term vanishes): 333.561 s both sides at 20 km and 288.174 s both
  sides at sea level (real anchor).
- Pressure-term split at the chosen eps: Isp_vac - Isp_design =
  (Pe - 0) * Ae / (mdot * g0) = 10.785 s (344.347 - 333.561) and
  Isp_sea - Isp_design = (Pe - 101325) * Ae / (mdot * g0) =
  -188.818 s (144.743 - 333.561) at eps* = 75.4961, 20 km design
  (real anchor).
- Throat-area invariance: delivered_isp is unchanged when
  throat_area_m2 is scaled (mdot and Ae scale together; the ratio
  Ae/mdot carries only eps), so the isp triple is an area-ratio
  property.
- Guard semantics: the 20 km matched eps* = 75.4961 is attached at
  20 km (True: Pe 5474.9 Pa >= 0.4 * 5474.88 = 2190.0 Pa) and
  separated at sea level (False: Pe 5474.9 Pa below
  0.4 * 101325 = 40530.0 Pa); the sea-level matched eps* = 8.3061 is
  attached at sea level (True) (real anchor).
- Ceiling bound: the fully expanded ceiling Isp = 385.276 s at the
  worked-example chamber sits above every finite-eps vacuum value
  (real anchor, ve ceiling 3778.266 m/s).
- ValueErrors across the module: h_m at -1 and 40000;
  area_ratio at 1.0 and 0.5; pa at 0.0 and at/above the Pe(1)
  ceiling; p0 at 0; gamma at 1.0; k_sep at 0 and 1.0; g0 at 0.
- Determinism; no imports beyond math; the module never returns
  over/under expansion strings and never computes a
  separation-station eps or a separation altitude.

## Worked example

Representative LOX/RP-1 upper-stage nozzle: chamber pressure
7.0 MPa, chamber temperature 3672 K, molecular weight 22.1 kg/kmol
(so R = 8314.462/22.1 = 376.220 J/(kg K)), gamma = 1.24, throat
radius 0.150 m (so At = 0.070686 m^2, the wave-43 sibling throat and
gas, so every forward cross-check below is a REAL number already
published by the sibling anchor), design altitude 20 km. The
choked mass flow is mdot = 276.24 kg/s (sibling cross-check
276.24), and the fully expanded ceiling is ve = 3778.266 m/s,
Isp = 385.276 s, the upper bound of any finite-eps vacuum value.
All values below are REAL outputs of the prep anchor
/tmp/w44spec/anchor_nozzle_ar.py (usr/bin/python3 3.9.6, stdlib
math, closed form, exit 0).
- ISA-76 ambient at the design altitude: pa(20 km) = 5474.88 Pa
  (layer table real: 0 km 101325.00 Pa, 11 km 22632.06 Pa, 20 km
  5474.88 Pa, 30 km 1171.87 Pa).
- Design-altitude selection (the inverse solve): eps* = 75.4961,
  matched exit Mach Me = 4.994178, Pe(eps*) = 5474.885 Pa against
  pa = 5474.88 Pa, closure residual -0.000 Pa (abs below 1e-3).
  Exit velocity ve = 3271.120 m/s, Ae = eps * At = 5.3365 m^2.
- Isp triple at the chosen eps* = 75.4961 (real): design-altitude
  Isp = 333.561 s, which equals ve/g0 = 333.561 s exactly because
  Pe = Pa kills the pressure term; vacuum Isp = 344.347 s, the
  (Pe - 0) * Ae pressure bonus adding 10.785 s; sea-level Isp =
  144.743 s, the (Pe - 101325) * Ae pressure penalty subtracting
  188.818 s.
- Attached-flow guard on the chosen eps* (real): at the 20 km
  design ambient the guard returns True (exit static 5474.9 Pa
  above K_SEP * pa = 0.4 * 5474.88 = 2190.0 Pa); at sea level the
  same ratio returns False (exit static 5474.9 Pa below
  K_SEP * 101325 = 40530.0 Pa), so the wall flow would separate
  there and the off-design bookkeeping at sea level belongs to
  rocket-nozzle-flow-separation (the 144.743 s attached-flow figure
  is invalid at sea level; the guard override is the deliverable).
- Altitude sweep (monotone selection, real): sea-level matched
  eps* = 8.3061 (Me = 3.253093) with Isp at sea level = 288.174 s
  (= ve/g0, matched) and vacuum Isp at that eps = 310.134 s, guard
  attached True at sea level; 11 km eps* = 25.416 (Me = 4.1170);
  20 km eps* = 75.4961 (Me = 4.9942); 30 km eps* = 251.124
  (Me = 6.0424). The four ratios rise monotonically as the ambient
  pressure falls with altitude.
- Forward-map cross-checks (real): the anchor reproduces the wave-43
  divergence-loss sibling real numbers at eps = 70.0 exactly (Me =
  4.931384, Pe = 6036.738 Pa), and the throat-plane ceiling
  Pe(1) = 3897668.7 Pa (3.8977 MPa) at this chamber bounds the
  selection domain: matched expansion exists for any pa below it.
- Read-off: the 20 km matched RP-1 upper-stage nozzle is eps = 75.5
  and delivers 333.561 s at its design altitude, 344.347 s in
  vacuum (about 10.8 s of pressure bonus), and it cannot be fired at
  sea level (attached-flow guard False; separation leaf takes over).
  A sea-level-matched booster nozzle for the same chamber is
  eps = 8.3 and delivers 288.174 s at sea level and 310.134 s in
  vacuum, staying attached at sea level. The gap from the geometry
  vacuum value to the 385.276 s fully expanded ceiling is the
  finite-expansion-ratio account that nozzle-design's expansion
  state explains at a given geometry; this leaf closes the eps that
  sits at the chosen altitude's ambient.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w44spec/anchor_nozzle_ar.py
(usr/bin/python3 3.9.6, stdlib math, closed form, exit 0).

## Validation list (contract test must include)

- ambient_pressure_at_altitude: 0 m = 101325.00 Pa, 11000 m =
  22632.06 Pa, 20000 m = 5474.88 Pa, 30000 m = 1171.87 Pa, each
  within 0.01 Pa; ValueError at -1 and 40000 m.
- exit_mach_from_area_ratio(70.0, 1.24) = 4.931384 within 1e-5
  (sibling cross-check) and the roundtrip area(M) - 70.0 relative
  error below 1e-12; ValueError at area_ratio 1.0 and 0.5.
- exit_static_pressure(70.0, 7.0e6, 1.24) = 6036.738 Pa within
  0.01 Pa; Pe(1) = 3897668.7 Pa within 0.1 Pa at 7.0 MPa, gamma
  1.24.
- expansion_matched_area_ratio(7.0e6, 1.24, 5474.88) = 75.4961
  within 1e-3, and the closure |Pe(eps*) - pa| below 1e-3 Pa;
  expansion_matched_area_ratio(7.0e6, 1.24, 101325.0) = 8.3061
  within 1e-3; ValueError at pa = 0 and at
  expansion_matched_area_ratio(150000.0, 1.4, 101325.0) (pa above
  the Pe(1) ceiling 81190.5 Pa).
- design_altitude_area_ratio(7.0e6, 1.24, 20000.0) = 75.4961 within
  1e-3, and the four-altitude sweep 0/11/20/30 km returns
  8.3061 / 25.416 / 75.4961 / 251.1241, strictly increasing.
- choked_mass_flow(0.070686, 7.0e6, 3672.0, 1.24, 376.220) =
  276.24 kg/s within 0.01 (sibling cross-check).
- delivered_isp: at eps* = 75.4961 the triple is design-altitude
  333.561 s, vacuum 344.347 s, sea level 144.743 s, each within
  0.05 s; design-altitude value equals exit_velocity/g0 within 1e-9
  relative (matched identity); vacuum minus design-altitude equals
  (Pe * Ae)/(mdot * g0) = 10.785 s within 0.01; sea-level minus
  design-altitude equals (Pe - 101325) * Ae/(mdot * g0) =
  -188.818 s within 0.01; scaling throat_area_m2 by 2 leaves every
  Isp unchanged within 1e-9 relative.
- Sea-level matched reference: delivered_isp at eps* = 8.3061 and
  pa = 101325.0 = 288.174 s within 0.05 s and equals ve/g0; vacuum
  value at that eps = 310.134 s within 0.05 s.
- attached_flow_guard(75.4961, 7.0e6, 1.24, 5474.88) is True and
  attached_flow_guard(75.4961, 7.0e6, 1.24, 101325.0) is False;
  attached_flow_guard(8.3061, 7.0e6, 1.24, 101325.0) is True.
- ValueErrors: altitude -1 and 40000; area_ratio 1.0 and 0.5; pa 0
  and the above-ceiling case; k_sep at 0 and 1.0; g0 at 0.
- Determinism; no imports beyond math; no over/under expansion
  string outputs and no separation-station or separation-altitude
  outputs anywhere in the public API.

## Corpus fragment (eval/hit1-wave44-nozzle-area-ratio-selection.yaml)

Query 1 (copy verbatim):
  "solve the design-altitude-expansion-ratio for the rocket nozzle:
  find the matched-expansion-ratio whose isentropic exit pressure
  equals the ambient pressure at the 20 km design altitude and
  report the sea-level vacuum and design-altitude isp at the chosen
  area ratio"
  intent: "propulsion; design-altitude expansion-ratio selection,
  matched Pe = Pa(h_design) by the inverse area-Mach solve, with the
  sea-level/vacuum/design-altitude Isp triple at the chosen ratio"
  expected_skill: "propulsion/rocket/nozzle-area-ratio-selection"
Query 2 (copy verbatim):
  "select the nozzle-area-ratio-selection matched to the design
  altitude of the LOX RP1 upper stage and apply the
  attached-flow-guard to verify that the chosen expansion ratio
  keeps the nozzle wall flow attached when the stage fires near sea
  level"
  intent: "propulsion; expansion-ratio selection at a design
  altitude plus the K_SEP attached-flow guard decision on the chosen
  ratio at a lower ambient"
  expected_skill: "propulsion/rocket/nozzle-area-ratio-selection"
Task ids: w44-nozzle-area-ratio-selection-1 and -2. Prep grep of
eval/hit1-corpus.yaml (real counts, combined search):
design-altitude-expansion-ratio 0, matched-expansion-ratio 0,
area-ratio-selection 0, nozzle-area-ratio-selection 0,
expansion-ratio-selection 0, matched-expansion 0, design-altitude 0.
The nearest corpus tasks route elsewhere: the nozzle-design tasks
(nz1, nz2) are forward tasks on a given geometry with no
design-altitude ambient target, and the
rocket-nozzle-flow-separation tasks
(w38-rocket-nozzle-flow-separation-1/-2) route on the
separation-pressure-ratio criterion, the separation-station area
ratio and the separation altitude, so the queries above are
collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must select the rocket nozzle
expansion ratio for a design altitude:" and include the outputs in
the Claim. First tag: nozzle-area-ratio-selection. Additional tags
ONLY: design-altitude-expansion-ratio, matched-expansion-ratio,
expansion-ratio-selection, attached-flow-guard. NEVER single
generic words (nozzle, area, ratio, isp, altitude, mach, expansion,
selection, guard, rocket, engine) and NEVER area-ratio, exit-mach,
mass-flow, ideal-thrust, expansion-ratio or choked-throat, which
nozzle-design owns, and NEVER separation-pressure-ratio,
summerfield-criterion, separation-station, separation-altitude,
overexpanded-nozzle or side-load-regime, which
rocket-nozzle-flow-separation owns, and NEVER divergence-loss,
nozzle-contour-loss, conical-nozzle-thrust-correction or
bell-nozzle-efficiency, which rocket-nozzle-divergence-loss owns.
50-150 words, <=1000 chars, no em dash, action verb present.
Recommended wording: "Use when you must select the rocket nozzle
expansion ratio for a design altitude: solve the inverse isentropic
problem for the matched-expansion-ratio whose ideal exit static
pressure equals the ambient pressure at the design altitude, using
the supersonic-branch area-Mach root and the monotone expansion
solve by bisection, and evaluate the sea-level, vacuum and
design-altitude delivered isp at the chosen ratio from the ideal
rocket relations with the choked mass flow. Produces the
design-altitude-expansion-ratio, the matched exit Mach and exit
static pressure, the delivered isp triple at the chosen ratio, and
the attached-flow-guard decision that the exit static pressure stays
above K_SEP times the operating ambient. Trigger:
nozzle-area-ratio-selection, design-altitude-expansion-ratio,
matched-expansion-ratio, expansion-ratio-selection,
attached-flow-guard." The sibling-owned tokens listed above must not
appear.

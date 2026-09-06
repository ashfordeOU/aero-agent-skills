---
name: nozzle-area-ratio-selection
description: "Use when you must select the rocket nozzle expansion ratio for a design altitude: solve the inverse isentropic problem for the matched-expansion-ratio whose ideal exit static pressure equals the ambient pressure at the design altitude, using the supersonic-branch area-Mach root and the monotone expansion solve by bisection, and evaluate the sea-level, vacuum and design-altitude delivered isp at the chosen ratio from the ideal rocket relations with the choked mass flow. Produces the design-altitude-expansion-ratio, the matched exit Mach and exit static pressure, the delivered isp triple at the chosen ratio, and the attached-flow-guard decision that the exit static pressure stays above K_SEP times the operating ambient. Trigger: nozzle-area-ratio-selection, design-altitude-expansion-ratio, matched-expansion-ratio, expansion-ratio-selection, attached-flow-guard."
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
  tags: [nozzle-area-ratio-selection, design-altitude-expansion-ratio, matched-expansion-ratio, expansion-ratio-selection, attached-flow-guard]
  version: 0.1.0
  author: AeroSkills
---

# Nozzle Area Ratio Selection (propulsion/rocket/nozzle-area-ratio-selection)

Use when you must pick the rocket nozzle expansion ratio that matches a
design altitude, the inverse of the forward nozzle sizing that
propulsion/rocket/nozzle-design performs at a given geometry. This leaf
solves Pe(eps) = Pa(h_design) for the matched expansion ratio eps* whose
ideal exit static pressure equals the ISA ambient pressure at the design
altitude, then evaluates the delivered specific impulse at the chosen
ratio for sea level, vacuum and the design altitude, and applies the
attached-flow guard that the exit static pressure stays at or above
K_SEP times the operating ambient. Pure Python, stdlib only,
deterministic. It inverts the forward envelope owned by
propulsion/rocket/nozzle-design, uses the K_SEP = 0.4 constant of
propulsion/rocket/rocket-nozzle-flow-separation as a verdict-only guard,
and produces the eps that the
propulsion/rocket/rocket-nozzle-divergence-loss chain later consumes.

## Domain quick reference

- Matched selection (the inverse solve): eps* solves Pe(eps*) = pa by
  bisection over eps on the monotone decreasing Pe(eps), with the upper
  bracket doubled until Pe falls at or below pa. At Pe(eps*) = pa the
  pressure term (Pe - pa) * Ae vanishes by construction and the
  design-altitude Isp equals ve / g0 exactly. No closed-form shortcut
  replaces the bisection: the selection is the inverse of the
  nozzle-design forward map and this module owns that inversion.
- Isentropic area-Mach relation: A/A* = (1/M) * ((2/(gamma+1)) *
  (1 + ((gamma-1)/2) * M^2))^((gamma+1)/(2*(gamma-1))). On the supersonic
  branch M >= 1 the relation is strictly increasing in M, so the inverse
  exit Mach root is a bisection on [1, M_hi] with M_hi doubled until the
  area exceeds the target (400 iterations).
- Exit static pressure: Pe(eps) = P0 * (1 + ((gamma-1)/2) *
  M_e^2)^(-gamma/(gamma-1)) with M_e the supersonic root. Pe is strictly
  DECREASING in eps, from the throat-plane ceiling
  Pe(1) = P0 * (2/(gamma+1))^(gamma/(gamma-1)) toward 0 as eps grows. The
  ceiling bounds the selection: a matched supersonic expansion exists only
  for pa strictly between 0 and Pe(1); pa = 0 (vacuum) has no finite
  matched ratio.
- ISA-76 ambient pressure (three layers, 0-32000 m): troposphere
  h <= 11000 m with T = 288.15 - 0.0065*h and p = 101325 *
  (T/288.15)^(G0/(ISA_R*0.0065)); isothermal stratosphere 11000 < h <=
  20000 m at T = 216.65 K with p = p(11000) * exp(-G0*(h - 11000) /
  (ISA_R*216.65)); upper layer 20000 < h <= 32000 m with T = 216.65 +
  0.001*(h - 20000) and p = p(20000) * (T/216.65)^(-G0/(ISA_R*0.001)).
- Exit velocity (energy equation): ve(eps) = sqrt(2*gamma/(gamma-1) *
  R * T0 * (1 - (Pe/P0)^((gamma-1)/gamma))). The fully expanded ceiling at
  Pe = 0 is sqrt(2*gamma/(gamma-1) * R * T0), approached only as eps grows
  without bound, never reached at a finite ratio.
- Choked mass flow: mdot = (P0 * At / sqrt(T0)) * sqrt(gamma/R) *
  (2/(gamma+1))^((gamma+1)/(2*(gamma-1))), reproduced here only to
  normalize the isp triple.
- Delivered Isp at a chosen eps and ambient: Isp = (mdot * ve + (Pe - pa)
  * eps * At) / (mdot * g0). The throat area At cancels exactly (Ae/mdot is
  proportional to eps with the same choked-flow factor), so the isp triple
  is an area ratio property, not an engine-scale property.
- Attached-flow guard (verdict only): attached iff
  Pe(eps) >= K_SEP * pa at the operating ambient, evaluated directly from
  Pe(eps). The guard computes no separation station ratio and no
  separation altitude; when it returns False the wall flow would separate
  at that ambient and rocket-nozzle-flow-separation takes over the
  off-design bookkeeping.
- Module constants: G0 = 9.80665 m/s^2, K_SEP_DEFAULT = 0.4 (the
  documented rocket-nozzle-flow-separation criterion constant, guard-only
  usage here), ISA_P0 = 101325.0 Pa, ISA_T0 = 288.15 K, ISA_L1 = 0.0065
  K/m, ISA_H1 = 11000.0 m, ISA_H2 = 20000.0 m, ISA_H3 = 32000.0 m,
  ISA_R = 287.053 J/(kg K), tropopause temperature 216.65 K and the
  20-32 km lapse +0.001 K/m.
- Units are SI throughout (Pa, K, m, m^2, kg/s, m/s, s). Gamma and R are
  caller-supplied for representative hot combustion products (R =
  8314.462 / molecular weight). ECSS space-systems standards frame the
  rocket propulsion context; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Fix the operating point: chamber pressure p0, chamber temperature t0,
   specific heat ratio gamma, the specific gas constant r_gas, and the
   throat area At. Gamma and R describe the hot combustion products and
   come from the caller (cea-rocket-combustion supplies the ideal chamber
   gas); At is kept so the physical assembly stays explicit even though
   the isp cancels it.
2. Read the design-altitude ambient pressure with
   ambient_pressure_at_altitude(h_design_m), the ISA-76 three-layer model
   over 0-32000 m (raise ValueError outside that band).
3. Run the design-altitude selection solve with
   design_altitude_area_ratio(p0, gamma, h_design_m): the matched
   expansion ratio whose ideal exit static pressure equals the ambient at
   the design altitude, the inverse of the nozzle-design forward map. For
   a fixed ambient pressure instead of an altitude, call
   expansion_matched_area_ratio(p0, gamma, pa) directly; both raise
   ValueError for a vacuum ambient or an ambient at or above the
   throat-plane ceiling, where no supersonic matched expansion exists.
4. Read off the matched flow state at the chosen ratio with
   exit_mach_from_area_ratio (the supersonic-branch root), the exit static
   pressure with exit_static_pressure, the exit velocity with
   exit_velocity, and the flow scale with choked_mass_flow.
5. Evaluate the delivered isp triple at the chosen ratio with
   delivered_isp: the sea-level value (pa = 101325.0), the vacuum value
   (pa = 0.0) and the design-altitude value (pa =
   ambient_pressure_at_altitude(h_design)). At the matched ratio the
   design-altitude value equals ve / g0 exactly because the pressure term
   vanishes; the vacuum minus design-altitude gap and the sea-level minus
   design-altitude gap are the pressure-term bonus and penalty of the
   finite ratio.
6. Apply the attached-flow guard with
   attached_flow_guard(area_ratio, p0, gamma, pa_operating): attached
   (True) iff the exit static pressure at the chosen ratio stays at or
   above K_SEP * pa at the operating ambient. A False verdict at a lower
   ambient means the wall flow would separate there; the off-design
   bookkeeping at that ambient belongs to
   rocket-nozzle-flow-separation, which owns everything downstream of the
   guard decision.
7. Confirm the deterministic checks with the contract test
   scripts/test_nozzle_area_ratio_selection.py (stdlib unittest, offline,
   both interpreter environments).

## Worked example

Representative LOX/RP-1 upper-stage nozzle: chamber pressure 7.0 MPa,
chamber temperature 3672 K, molecular weight 22.1 kg/kmol (so R =
8314.462 / 22.1 = 376.220 J/(kg K)), gamma = 1.24, throat radius 0.150 m
(At = 0.070686 m^2), design altitude 20 km. All values below are real
module outputs of scripts/nozzle_area_ratio_selection_logic.py.

- ISA-76 ambient at the design altitude: Pa(20 km) = 5474.88 Pa (layer
  table: 0 km 101325.00 Pa, 11 km 22632.06 Pa, 20 km 5474.88 Pa, 30 km
  1171.87 Pa, each within 0.01 Pa of the module).
- Design-altitude selection: eps* = 75.4961, matched exit Mach
  Me = 4.994178, Pe(eps*) = 5474.885 Pa against Pa = 5474.88 Pa, closure
  residual below 1e-3 Pa. Exit velocity ve = 3271.120 m/s, exit area
  Ae = eps * At = 5.3365 m^2. Choked mass flow mdot = 276.24 kg/s (the
  wave-43 sibling throat and gas, so the forward cross-checks below are
  real numbers already published by that anchor).
- Isp triple at the chosen eps*: design-altitude Isp = 333.561 s, which
  equals ve / g0 = 333.561 s because Pe = Pa kills the pressure term;
  vacuum Isp = 344.347 s, the pressure bonus adding 10.785 s; sea-level
  Isp = 144.743 s, the pressure penalty subtracting 188.818 s.
- Attached-flow guard on the chosen eps*: at the 20 km design ambient the
  guard returns True (exit static 5474.9 Pa above K_SEP * Pa = 0.4 *
  5474.88 = 2190.0 Pa); at sea level the same ratio returns False (exit
  static 5474.9 Pa below 0.4 * 101325 = 40530.0 Pa), so the wall flow
  would separate there and the off-design bookkeeping at sea level
  belongs to rocket-nozzle-flow-separation (the 144.743 s attached-flow
  figure is invalid at sea level; the guard override is the deliverable).
- Altitude sweep (monotone selection): sea-level matched eps* = 8.3061
  (Me = 3.253093) with Isp at sea level = 288.174 s (= ve / g0, matched)
  and vacuum Isp at that ratio = 310.134 s, guard attached True at sea
  level; 11 km eps* = 25.416 (Me = 4.11698); 20 km eps* = 75.4961
  (Me = 4.994178); 30 km eps* = 251.1241 (Me = 6.042370). The four
  ratios rise monotonically as the ambient pressure falls with altitude,
  and the sea-level matched ratio is the smallest of the four.
- Forward-map cross-checks: the module reproduces the wave-43
  rocket-nozzle-divergence-loss sibling real numbers at eps = 70.0
  exactly (Me = 4.931384, Pe = 6036.738 Pa), proving the forward map this
  module inverts is the nozzle-design map; the throat-plane ceiling
  Pe(1) = 3897668.7 Pa (3.8977 MPa) at this chamber bounds the selection
  domain, and the fully expanded ceiling ve = 3778.266 m/s (Isp =
  385.276 s) sits above every finite-ratio vacuum value.
- Read-off: the 20 km matched RP-1 upper-stage nozzle is eps = 75.5 and
  delivers 333.561 s at its design altitude and 344.347 s in vacuum
  (about 10.8 s of pressure bonus), and it cannot be fired at sea level
  (attached-flow guard False). A sea-level-matched booster nozzle for the
  same chamber is eps = 8.3 and delivers 288.174 s at sea level and
  310.134 s in vacuum, staying attached at sea level. The gap from the
  geometry vacuum value to the 385.276 s fully expanded ceiling is the
  finite-ratio account that nozzle-design's expansion state explains at a
  given geometry; this leaf closes the eps that sits at the chosen
  altitude's ambient.

## Verification

- Confirm ambient_pressure_at_altitude returns 101325.00 Pa at 0 m,
  22632.06 Pa at 11000 m, 5474.88 Pa at 20000 m and 1171.87 Pa at
  30000 m, each within 0.01 Pa, and raises ValueError at -1 m and 40000 m.
- Confirm exit_mach_from_area_ratio(70.0, 1.24) = 4.931384 within 1e-5
  (sibling cross-check) and that the round trip back through the
  area-Mach relation recovers 70.0 with relative error below 1e-12.
- Confirm exit_static_pressure(70.0, 7.0e6, 1.24) = 6036.738 Pa within
  0.01 Pa, and the throat-plane ceiling Pe(1) = 3897668.7 Pa within 0.1 Pa
  at 7.0 MPa, gamma 1.24.
- Confirm expansion_matched_area_ratio(7.0e6, 1.24, 5474.88) = 75.4961
  within 1e-3 with the closure |Pe(eps*) - pa| below 1e-3 Pa, and
  expansion_matched_area_ratio(7.0e6, 1.24, 101325.0) = 8.3061 within
  1e-3. ValueError at pa = 0 and at
  expansion_matched_area_ratio(150000.0, 1.4, 101325.0), where the
  ambient sits above the Pe(1) ceiling of 81190.5 Pa.
- Confirm design_altitude_area_ratio(7.0e6, 1.24, 20000.0) = 75.4961
  within 1e-3 and that the four-altitude sweep 0/11/20/30 km returns
  8.3061 / 25.416 / 75.4961 / 251.1241, strictly increasing.
- Confirm choked_mass_flow(0.070686, 7.0e6, 3672.0, 1.24, 376.220) =
  276.24 kg/s within 0.01 (sibling cross-check).
- Confirm the delivered isp triple at eps* = 75.4961: design-altitude
  333.561 s, vacuum 344.347 s, sea level 144.743 s, each within 0.05 s;
  the design-altitude value equals exit_velocity / g0 within 1e-9
  relative (matched identity); vacuum minus design-altitude equals
  Pa_design * Ae / (mdot * g0) = 10.785 s within 0.01; sea-level minus
  design-altitude equals (Pa_design - 101325) * Ae / (mdot * g0) =
  -188.818 s within 0.01; scaling the throat area by 2 leaves every Isp
  unchanged within 1e-9 relative.
- Confirm attached_flow_guard(75.4961, 7.0e6, 1.24, 5474.88) is True,
  attached_flow_guard(75.4961, 7.0e6, 1.24, 101325.0) is False, and
  attached_flow_guard(8.3061, 7.0e6, 1.24, 101325.0) is True.
- Confirm every non-physical input raises ValueError: altitude outside
  0-32000 m, area ratio at or below 1, ambient at or above the
  throat-plane ceiling or at 0, non-positive chamber pressure,
  temperature, gas constant, throat area or g0, gamma at or below 1, and
  a guard constant k_sep outside (0, 1).
- Run the contract test offline: python3
  scripts/test_nozzle_area_ratio_selection.py (deterministic, under a
  second).

## Related leaves

- propulsion/rocket/nozzle-design: the forward ideal attached-flow sizing
  at a given geometry (exit Mach, exit static pressure, mass flow,
  velocity, thrust, expansion state). This leaf is the inverse of that
  forward envelope: the area ratio is the solved output here, never a
  caller-supplied input.
- propulsion/rocket/rocket-nozzle-flow-separation: owns everything
  downstream of the attached-flow guard decision, the separation station
  bookkeeping and the altitude where the wall flow un-separates; this
  leaf reuses its documented K_SEP = 0.4 constant as a verdict-only
  minimum-eps guard on the ratio it selected.
- propulsion/rocket/rocket-nozzle-divergence-loss: consumes the eps this
  leaf selects and applies the divergence and boundary-layer corrections
  at that geometry.
- propulsion/combustion/cea-rocket-combustion: supplies the ideal chamber
  gas (Tc, Mw, gamma, c-star) that feeds the selection and the fixed
  ambient Isp reference points.
- propulsion/rocket/rocket-sizing: the stage mass loop around the nozzle
  ratio trade for the design altitude.

## Pitfalls

- Reading the guard as a performance correction: attached_flow_guard is a
  boolean verdict on the ratio this leaf selected. When it returns False
  at an ambient (Pe below K_SEP * pa), the wall flow would separate there
  and every attached-flow Isp figure at that ambient is invalid; the
  separation station bookkeeping belongs to rocket-nozzle-flow-separation,
  not here.
- Matching to vacuum: expansion_matched_area_ratio raises ValueError at
  pa = 0 because no finite ratio ever expands to zero exit pressure. The
  vacuum Isp is always evaluated at the ratio chosen for a finite design
  ambient, and it stays below the fully expanded ceiling ve / g0
  (385.276 s in the worked example) that only Pe = 0 reaches.
- Confusing the inverse solve with forward sizing: nozzle-design takes
  the area ratio as an input and returns the exit state; this leaf takes
  the design altitude (or ambient) as the input and returns the ratio.
  Feeding a ratio in here to get an exit state duplicates the forward
  envelope instead of closing the selection loop.
- Ignoring the throat-plane ceiling: Pe(eps) starts at Pe(1) = P0 *
  (2/(gamma+1))^(gamma/(gamma-1)) and only falls from there, so an
  ambient at or above the ceiling (101325 Pa against 81190.5 Pa at p0 =
  150000 Pa, gamma 1.4) has no supersonic matched expansion and raises
  ValueError instead of returning a bogus ratio below 1.
- Treating the sea-level matched ratio as universal: eps* = 8.3 at 0 km
  grows to 75.5 at 20 km and 251.1 at 30 km as the ambient pressure
  falls, so quoting one ratio for an upper stage hides the altitude
  dependence of the whole selection sweep.
- Using the air gas constant: R must describe the combustion products
  (376.220 J/(kg K) for Mw = 22.1 from R = 8314.462 / Mw); plugging the
  air value shifts every exit velocity and Isp.
- Reading the guard False at a high ratio as a design error: a 20 km
  matched ratio separated at sea level is expected, not a defect; the
  design-altitude match and the vacuum bonus are the deliverables, and
  the off-design ambient hands over to rocket-nozzle-flow-separation.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_nozzle_area_ratio_selection.py

The test must pass with exit 0 and covers the worked-example anchors
(ISA-76 ambient at 0/11/20/30 km within 0.01 Pa, eps* = 75.4961 at 20 km
and 8.3061 at sea level within 1e-3 with closure below 1e-3 Pa, the
monotone four-altitude sweep, the sibling cross-checks Me = 4.931384 and
Pe = 6036.738 Pa at eps = 70.0 and mdot = 276.24 kg/s, the throat-plane
ceiling anchor, the isp triple 333.561 / 344.347 / 144.743 s with the
matched identity and the pressure-term split, the throat-area invariance,
the fully expanded ceiling bound, the attached-flow guard truth table at
the design and sea-level ambients, the area-Mach round trip, determinism
and the API surface, and ValueError rejection of every non-physical input
listed in the Verification section).

## Contract test

Run the contract test from the repo root:

    python3 skills/propulsion/rocket/nozzle-area-ratio-selection/scripts/test_nozzle_area_ratio_selection.py

Stdlib unittest only, deterministic, offline, exit 0 in about a second.
The test imports the sibling logic module
nozzle_area_ratio_selection_logic from its own scripts directory, so no
install or path configuration is needed.

## Compliance

- Standards referenced, not reproduced: ECSS is a free ESA download
  (ecss.nl/standards); the isentropic nozzle relations, the ideal rocket
  equation and the ISA-76 ambient model above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

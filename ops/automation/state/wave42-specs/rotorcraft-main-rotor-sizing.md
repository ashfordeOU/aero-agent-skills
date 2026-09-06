# Wave-42 leaf spec: rotorcraft-main-rotor-sizing (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-main-rotor-sizing/
- Pack: performance (verified present at prep with the rotorcraft
  performance siblings rotorcraft-hover-performance, rotorcraft-forward-
  flight-performance, rotorcraft-vertical-climb-performance, rotorcraft-
  autorotative-descent, rotorcraft-axial-descent-flow-states, rotorcraft-
  hover-ground-effect, rotorcraft-range-endurance, rotorcraft-turn-
  performance, rotorcraft-tail-rotor-sizing and the fixed-wing turn-
  performance; leaf rotorcraft-main-rotor-sizing absent at prep). Whole-
  tree greps at prep: the sizing vocabulary "tip speed | blade chord |
  rotor diameter | main rotor radius | blade area | rotor solidity" across
  ALL skills/** returns 32 hits, every one in a rotorcraft PERFORMANCE
  leaf that consumes geometry as a given input (hover, forward-flight,
  blade-element-hover, tail-rotor-sizing, turn, vertical-climb,
  autorotation, flapping), plus vehicle-design propeller-sizing and
  propulsion turbomachinery running on their own propulsor geometry; no
  leaf anywhere selects or derives MAIN-ROTOR geometry from a weight
  requirement. Corpus grep: no main-rotor sizing task exists in eval, and
  the sizing task vocabulary (disk-loading ceiling, ct-over-sigma closure,
  blade chord from a blade count) routes to no owner. GENUINE rotorcraft
  n > 1 gap (fresh probe): the sizing inversion for the MAIN rotor
  (takeoff weight plus design ceilings into disk area, radius, solidity,
  blade area, chord and tip Mach) is owned by no leaf. Fences within the
  pack (quoted from the leaves at prep, read in full):
  - rotorcraft-hover-performance (hover power and disk loading FOR GIVEN
    radius): its body states "Geometry (radius, solidity, blade drag
    coefficient, tip speed) is an input; this leaf does not size the
    rotor." The pack itself declares the sizing gap open, and its worked
    rotor is always given (R = 5.0 m, m = 2200 kg).
  - rotorcraft-tail-rotor-sizing (the SAME sizing inversion already
    applied to the anti-torque rotor): "The main rotor power is an INPUT
    to this leaf: it is never computed from weight and geometry here."
    Its constants convention, quoted from the SKILL body and its logic
    script: "A = T_tr / DL_max, with DL_max the maximum disk loading
    (default 300 Pa)" and "solidity sigma = 0.10, Cd = 0.012 and tip
    speed V_tip = 200 m/s defaults" (logic script SIGMA_TR_DEFAULT =
    0.10, tail_rotor_sizing with max_disk_loading = 300.0, k = 1.15),
    with the inversion precedent A = T/DL_max then R = sqrt(A/PI).
    Main-rotor sizing is its unclaimed counterpart: inputs are the
    takeoff weight and design ceilings, never the main rotor torque or
    the tail arm, so there is no overlap (its anti-torque thrust comes
    from a torque balance; the main-rotor sizing thrust is the weight-
    borne hover thrust T = m * g0).
  - rotorcraft-forward-flight-performance, rotorcraft-vertical-climb-
    performance, rotorcraft-autorotative-descent, rotorcraft-axial-
    descent-flow-states, rotorcraft-hover-ground-effect, rotorcraft-
    range-endurance and rotorcraft-turn-performance: flight-state and
    closure leaves that consume a given radius and solidity (the turn
    leaf reuses the hover worked rotor R = 5.0 m at n times weight);
    none sizes the main rotor, and none of their power vocabulary
    appears here.
- Standards id: far-29 (line 270 of standards-map.yaml, public-domain
  US government work per the map; the rotorcraft performance siblings
  all reference far-29, and the tail-rotor-sizing and hover-performance
  frontmatter carry it reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Size the main rotor of a single-main-rotor rotorcraft from the takeoff
weight and the design ceilings in the momentum-theory weight-borne hover
reference: the disk area and radius from the weight against the chosen
main-rotor-disk-loading ceiling (A = T / DL_max, R = sqrt(A / PI)), the
hover thrust coefficient CT at the chosen rotor tip speed, the rotor
solidity closure from the ct-over-sigma design point (sigma = CT / (CT /
sigma)_design), the total blade area and the constant blade chord from
the blade count on rectangular blades, and the rotor tip Mach at the tip
speed. Produces the disk area, radius, thrust coefficient, solidity,
blade area, chord and tip Mach that gate a main rotor sizing pass, so the
geometry can then feed the sibling power leaves that consume a given
rotor. Does NOT do: hover power and figure of merit (rotorcraft-hover-
performance); the anti-torque rotor torque balance, its disk sizing from
the main rotor torque over the tail arm, and the tail rotor power
(rotorcraft-tail-rotor-sizing); the forward-flight power curve
(rotorcraft-forward-flight-performance); climb, autorotation, descent
flow states, ground effect, range or turn analysis (the other rotorcraft
performance leaves); any rotor power at all. Closed-form sizing only: no
inflow solve, no power term, no figure of merit, no blade-element
sections, no compressibility corrections beyond the tip Mach check, no
structural or dynamics content, no RNG, pure stdlib.

## Model (implement exactly)

Closed-form sizing chain in the weight-borne hover reference, thrust
T = m * g0 at the takeoff weight. All quantities SI (N, m, m2, Pa,
m/s). Module constants: G0 = 9.80665 m/s2, PI = math.pi,
RHO_SL = 1.225 kg/m3, A0_SL = 340.3 m/s (sea-level speed of sound). The
design ceilings are caller inputs in every primitive, following the
sibling convention that constants are explicit documented settings
(the tail-rotor-sizing leaf documents the same style: DL_max 300 Pa,
sigma 0.10, tip speed 200 m/s, k 1.15): main-rotor disk-loading
ceilings of 250-500 Pa with the 350 Pa worked value; ct-over-sigma
design points 0.10-0.14 with 0.12 worked; rotor tip speeds 200-230 m/s
with 210 m/s worked.

Functions (pure stdlib, math only):

- disk_area_and_radius(thrust, disk_loading_max) -> tuple (area,
  radius): area = thrust / disk_loading_max in m2, radius =
  sqrt(area / PI) in m, the disk sized exactly at the ceiling. ValueError
  if thrust <= 0 or disk_loading_max <= 0.
- hover_thrust_coefficient(thrust, rho, radius, tip_speed) -> float
  CT = thrust / (rho * area * tip_speed**2), with area = PI * radius**2
  computed inside; tip_speed is the rotor tip speed Vtip = Omega * R in
  m/s; CT dimensionless. ValueError if thrust <= 0, rho <= 0, radius <= 0
  or tip_speed <= 0. At the sized disk (thrust over area equals the
  ceiling) the identity CT = disk_loading_max / (rho * tip_speed**2)
  holds, so the thrust coefficient is independent of the rotor size.
- solidity_closure(thrust_coefficient, ct_over_sigma_design) -> float
  sigma = thrust_coefficient / ct_over_sigma_design, dimensionless, the
  rotor solidity the hover design point implies; the closure round trip
  sigma * ct_over_sigma_design == thrust_coefficient holds. ValueError if
  thrust_coefficient <= 0 or ct_over_sigma_design <= 0.
- blade_area_chord(solidity, area, blade_count, radius) -> tuple
  (blade_area, chord): blade_area = solidity * area in m2, chord =
  blade_area / (blade_count * radius) in m; rectangular blades, chord
  constant along the span. ValueError if solidity <= 0, area <= 0,
  radius <= 0, blade_count < 1 or blade_count is not a positive integer.
- tip_mach(tip_speed, speed_of_sound) -> float M_tip = tip_speed /
  speed_of_sound, dimensionless. ValueError if tip_speed < 0 or
  speed_of_sound <= 0.

Identities to test: sizing sits exactly at the ceiling (thrust / area
from disk_area_and_radius equals disk_loading_max; PI * radius**2
recovers the area to float precision); the CT closed form equals the
definition with area = PI * radius**2 and equals disk_loading_max /
(rho * tip_speed**2) at the sized disk; the solidity closure round trip
sigma * ct_over_sigma_design returns the input CT; the blade-area
identity sigma = blade_count * chord * radius / area recovers the input
solidity, and chord * blade_count * radius equals the blade area; M_tip
= tip_speed / speed_of_sound; the radius scales with the square root of
the mass at a fixed ceiling; the tip Mach is unchanged when only the
mass or the ceiling changes at a fixed tip speed; disk_area_and_radius
fed the tail-rotor-sizing anti-torque thrust at its 300 Pa ceiling
reproduces the sibling worked anchors (the shared inversion, different
inputs).

## Worked example

Primary state: helicopter takeoff mass m = 4500 kg so W = m * g0 =
44129.925 N, main-rotor disk-loading ceiling DL_max = 350 Pa, ct_over-
sigma design point 0.12, blade count b = 4, rotor tip speed Vtip = 210
m/s, rho = 1.225 kg/m3 (sea level), speed of sound a = 340.3 m/s. Anchor
script /tmp/w42spec/anchor_rotorcraft_main_rotor_sizing.py, run at prep
(pure stdlib, exit 0), module outputs:

- Thrust: T = W = 44129.925 N (weight-borne hover reference).
- Disk area: A = 44129.925 / 350 = 126.0855 m2.
- Disk radius: R = sqrt(126.0855 / PI) = 6.3352 m.
- Achieved disk loading: T / A = 350.0 Pa, exactly the ceiling.
- Thrust coefficient: CT = 44129.925 / (1.225 * 126.0855 * 210^2) =
  0.006479 (the manual closed form with A = PI * R^2 prints the same
  value, and the ceiling identity 350.0 / (1.225 * 210^2) = 0.006479).
- Solidity closure: sigma = 0.006479 / 0.12 = 0.053990, design-point
  check CT / sigma = 0.1200.
- Blade area: Ab = 0.053990 * 126.0855 = 6.8073 m2.
- Blade chord: c = 6.8073 / (4 * 6.3352) = 0.2686 m, blade aspect ratio
  R / c = 23.58 (rectangular constant-chord blades); solidity check
  b * c * R / A = 0.053990.
- Tip Mach: M_tip = 210.0 / 340.3 = 0.61710, comfortably subcritical at
  sea level, so no compressibility correction enters the sizing.

The light 350 Pa ceiling gives a large disk (about 126 m2, R = 6.34 m)
and hence a low hover thrust coefficient, so the 0.12 design point
closes at sigma about 0.054 with a 0.269 m chord; sigma scales linearly
with the ceiling at fixed tip speed and design point (sigma = DL_max /
(rho * Vtip^2 * (CT/sigma)_design), about 0.092 at a 600 Pa ceiling).

Second state (supplementary anchor run from the same module, exit 0):
m = 3000 kg, DL_max = 300 Pa, ct_over_sigma = 0.10, b = 4, Vtip = 210
m/s: W = 29419.950 N, A = 98.0665 m2, R = 5.5871 m, achieved disk
loading 300.0 Pa, CT = 0.005553, sigma = 0.055532 (CT / sigma = 0.1000),
blade area 5.4459 m2, chord 0.2437 m, M_tip = 0.61710 unchanged at the
fixed tip speed. Convention cross-check against the tail-rotor-sizing
precedent: disk_area_and_radius(1851.8519, 300.0) returns (6.1728,
1.4017), reproducing the sibling worked anchors (Q = 400000 / 27 N m,
anti-torque thrust Q / 8.0 m = 1851.8519 N) of the identical
A = T / DL_max, R = sqrt(A / PI) inversion applied to its own thrust
input. Run your module and take the real outputs as assert targets; the
anchors above are prep-verified, computed by running the prep anchor
script /tmp/w42spec/anchor_rotorcraft_main_rotor_sizing.py and its
supplementary state run (prep-verified by stdlib math).

## Validation list (contract test must include)

- disk_area_and_radius(44129.925, 350.0) = (126.0855, 6.3352) within
  1e-4 (bounds: area 115-140 m2, radius 6.0-6.7 m); the round trip
  PI * radius**2 recovers 126.0855 and thrust / area equals 350.0 Pa
  exactly (sized at the ceiling).
- hover_thrust_coefficient(44129.925, 1.225, 6.3352, 210.0) = 0.006479
  within 1e-6 (bound 0.0055 to 0.0075), equal to the ceiling identity
  350.0 / (1.225 * 210**2) = 0.006479.
- solidity_closure(0.006479, 0.12) = 0.053990 within 1e-6 (bound 0.045
  to 0.065); the round trip sigma * 0.12 returns 0.006479 and the
  design-point check CT / sigma = 0.1200.
- blade_area_chord(0.053990, 126.0855, 4, 6.3352) = (6.8073, 0.2686)
  within 1e-4 (chord bound 0.22 to 0.32 m); the solidity identity
  4 * 0.2686 * 6.3352 / 126.0855 = 0.053990 and chord * blade_count *
  radius = 6.8073.
- tip_mach(210.0, 340.3) = 0.61710 within 1e-5 (bound 0.55 to 0.70).
- Second state: disk_area_and_radius(29419.950, 300.0) = (98.0665,
  5.5871) within 1e-4; hover_thrust_coefficient(29419.950, 1.225,
  5.5871, 210.0) = 0.005553 within 1e-6; solidity_closure(0.005553,
  0.10) = 0.055532 within 1e-6; blade_area_chord(0.055532, 98.0665, 4,
  5.5871) = (5.4459, 0.2437) within 1e-4; the radius shrinks with the
  mass (6.3352 to 5.5871 m) and the tip Mach stays 0.61710 at the fixed
  tip speed.
- Convention cross-check: disk_area_and_radius(1851.8519, 300.0) =
  (6.1728, 1.4017) within 1e-4, matching the rotorcraft-tail-rotor-sizing
  worked example (torque 14814.8 N m over the 8.0 m tail arm gives its
  anti-torque thrust 1851.9 N; the same inversion sizes that disk at
  300 Pa). This verifies the shared inversion convention, not any shared
  input: the torque balance inputs never enter this leaf.
- ValueErrors: disk_area_and_radius at thrust 0 and disk_loading_max 0;
  hover_thrust_coefficient at thrust 0, rho 0, radius 0, tip_speed 0;
  solidity_closure at thrust_coefficient 0 and ct_over_sigma_design 0;
  blade_area_chord at solidity 0, area 0, radius 0, blade_count 0 and
  non-integral blade_count 2.5; tip_mach at tip_speed -1 and
  speed_of_sound 0 (15 rejection classes, all confirmed at prep).
- Determinism: two identical calls return bit-identical floats; fixed
  outputs across runs (no RNG, stdlib only).

## Corpus fragment (eval/hit1-wave42-rotorcraft-main-rotor-sizing.yaml)

Query 1 (copy verbatim; embeds the leaf tag tokens main-rotor-disk-
loading, ct-over-sigma and rotor-tip-mach and leads with the sizing
intent):
  "size the main rotor of a 4500-kg helicopter: set the disk area and radius from the takeoff weight against the main-rotor-disk-loading ceiling, close the rotor solidity from the 0.12 ct-over-sigma hover design point, and check the rotor-tip-mach number at the 210 m/s rotor tip speed"
  intent: "flight-mechanics; main rotor disk area and radius from the takeoff weight at the disk loading ceiling, solidity closure and tip mach check"
  expected_skill: "flight-mechanics/performance/rotorcraft-main-rotor-sizing"
Query 2 (copy verbatim; embeds the tag token rotor-thrust-coefficient
and the blade geometry intent):
  "select main-rotor blade geometry for a 3000-kg rotorcraft: the rotor-thrust-coefficient from momentum theory at the rotor tip speed, the blade area and blade chord from the closed rotor solidity and a 4-blade count, and the disk-loading verdict against the ceiling"
  intent: "flight-mechanics; rotor thrust coefficient, blade area and blade chord from the solidity closure and the blade count"
  expected_skill: "flight-mechanics/performance/rotorcraft-main-rotor-sizing"
Task ids: w42-rotorcraft-main-rotor-sizing-1 and -2. Both queries embed
the leaf's own hyphenated tag tokens (main-rotor-disk-loading, rotor-
thrust-coefficient, ct-over-sigma, rotor-tip-mach, rotorcraft-main-rotor-
sizing) and lead with helicopter main-rotor sizing intent so the
geometry-consuming rotorcraft leaves keep routing to their owners, as
the zero-owner greps at prep confirmed.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description EXACTLY (copy verbatim; 134 words, 909 chars, opens with the
action verb, no em dash, no "classified"):
"Use when you must size the main rotor of a single-main-rotor rotorcraft from the takeoff weight and design ceilings: the main-rotor-disk-loading ceiling sets the disk area and radius, the rotor-thrust-coefficient follows from momentum theory at the chosen rotor tip speed, the rotor solidity closes from the ct-over-sigma hover design point, the blade area and chord follow from the blade count on constant-chord blades, and the rotor-tip-mach number checks the tip speed against the speed of sound. Produces the disk area, radius, thrust coefficient, solidity, blade area, chord and tip mach that gate a main rotor sizing pass before the power leaves consume the geometry. Sizing only: closed-form inversions from weight, no rotor power, no flight-state performance; the geometry-consuming rotorcraft leaves keep their owners. Trigger: main rotor sizing, disk loading ceiling, ct-over-sigma, rotor tip speed."
First tag: rotorcraft-main-rotor-sizing. Additional tags ONLY:
main-rotor-disk-loading, rotor-thrust-coefficient, ct-over-sigma,
rotor-tip-mach. NEVER single generic words (rotor, main, sizing,
helicopter, disk, blade, chord, speed, weight, area, radius, solidity,
thrust, loading alone) as tags.

FORBIDDEN TOKENS (belong to siblings; keep them out of the description,
tags and corpus queries): tail-rotor, anti-torque-rotor, tail-rotor-
thrust, main-rotor-torque, tail-rotor-power, tail-arm (rotorcraft-tail-
rotor-sizing); hover-power, figure-of-merit, rotor-induced-velocity,
rotor-disk-loading, rotor-solidity (rotorcraft-hover-performance); the
forward-flight power curve terms (rotorcraft-forward-flight-performance);
autorotative-descent, power-off-descent (rotorcraft-autorotative-descent).
The hyphenated tokens main-rotor-disk-loading, rotor-thrust-coefficient,
ct-over-sigma and rotor-tip-mach are THIS leaf's own compound terms; do
not write them with spaces ("main rotor disk loading", "ct over sigma")
in the description or corpus queries, because the spaced form tokenizes
into the generic words that belong to the geometry-consuming leaves, and
never emit the bare sibling token rotor-disk-loading for the sizing
ceiling: write the main-rotor-disk-loading compound, because the hover
sibling owns rotor-disk-loading for a given rotor.

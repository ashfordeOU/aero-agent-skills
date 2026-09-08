# Wave-46 leaf spec: hydrogen-peroxide-monopropellant-thruster (propulsion,
# rocket pack)

- Path: skills/propulsion/rocket/hydrogen-peroxide-monopropellant-thruster/
- Pack: rocket (present siblings cold-gas-thruster,
  combustion-chamber-design, hybrid-rocket-motor,
  hydrazine-monopropellant-thruster, injector-design,
  nozzle-area-ratio-selection, nozzle-design, propellant-selection,
  rocket-engine-cycle, rocket-gravity-loss,
  rocket-nozzle-divergence-loss, rocket-nozzle-flow-separation,
  rocket-sizing, rocket-staging, solid-rocket-motor,
  thrust-chamber-cooling, thrust-vector-control; adjacent fences in
  propulsion/electric (electrothermal-thruster) and the whole
  propulsion tree has no other chemical-decomposition station leaf).
- Provenance: wave-46 propulsion probe receipt (ops/automation/state/
  wave46-recon/task-5-receipt.md, GO-1 rank 1, whole family FRESH at
  HEAD 45931c16) dispatches this leaf: "Hydrogen peroxide monopropellant
  thruster station model, the direct chemical sibling of the wave-45
  hydrazine leaf: catalytic decomposition of H2O2 over a silver catalyst
  bed, 2 H2O2(l) -> 2 H2O(g) + O2(g) exothermic, adiabatic decomposition
  (chamber) temperature from the Hess-law energy balance at a documented
  peroxide concentration (water dilution), then frozen-composition
  isentropic expansion of the steam/oxygen product mixture to vacuum
  exhaust velocity and vacuum specific impulse, propellant mass flow at
  the thrust point, with published decomposition-temperature and impulse
  bands reported reference-only. Deterministic closed form, stdlib-only,
  no tables." SPEC-TIME TRIAGE DONE FIRST: the four sibling SKILL.md
  bodies quoted below were read IN FULL at prep
  (skills/propulsion/rocket/hydrazine-monopropellant-thruster/SKILL.md,
  skills/propulsion/rocket/cold-gas-thruster/SKILL.md,
  skills/propulsion/rocket/propellant-selection/SKILL.md,
  skills/propulsion/rocket/rocket-engine-cycle/SKILL.md) and the
  electrothermal fence line was quoted from the probe receipt. Genuine
  overlap NOT found: the peroxide decomposition energy balance, the
  concentration-limited decomposition temperature and the expansion of
  the steam-oxygen product mixture are owned by no sibling; the
  hydrazine leaf is N2H4-specific end to end, and H2O2 appears in
  propellant-selection exactly once, as a storable BIPROPELLANT oxidizer
  example in a propellant-family classification bullet (do not touch
  that content). GO, no decline file written.
- Claim fences (quoted from the sibling frontmatter and body at prep;
  none owns the H2O2 decomposition station math, the concentration input
  with water dilution, or the steam-oxygen expansion):
  - hydrazine-monopropellant-thruster (this pack, the wave-45 sibling)
    is hydrazine-specific end to end. Its body reads "Use when the task
    is sizing and assessing a hydrazine monopropellant thruster for
    spacecraft reaction control: liquid hydrazine decomposes
    catalytically over a catalyst bed and the hot product gas expands
    through a nozzle to produce a small thrust for attitude control."
    Its boundary fence reads "The boundary is strict: this leaf is the
    decomposition station math, not a feed cycle model, not a nozzle
    hardware sizer, not a tank sizer and not an attitude control law."
    Its energy balance is N2H4-specific (primary decomposition releasing
    111.8833 kJ per mole fed, ammonia dissociation fraction x, product
    mixture NH3/N2/H2) and its metadata tags are
    hydrazine-monopropellant-thruster, catalytic-decomposition,
    ammonia-dissociation-fraction, monopropellant-rcs,
    decomposition-temperature. Nothing in that leaf models a different
    monopropellant chemistry: no H2O2 reactant, no water dilution, no
    steam-oxygen products, no silver catalyst.
  - propellant-selection (this pack) classifies H2O2 once, as a storable
    BIPROPELLANT oxidizer: its line 31 reads "Propellant families:
    cryogenic (LOX, LH2, LCH4), storable (RP-1, H2O2), hypergolic
    (MMH/UDMH with NTO or IRFNA, ignites on contact), solid (HTPB/APCP
    composite grain), and hybrids." The leaf domain is families, density
    impulse, O/F bulk density and mass fraction; it has no decomposition
    chemistry and no thruster station content. The new leaf performs no
    propellant-family classification, no O/F bulk-density and no
    mass-fraction trades, and it never edits that classification bullet.
  - rocket-engine-cycle (this pack) covers the FEED SYSTEM only: its
    frontmatter/body reads "with a small reference propellant table
    (LOX/RP-1, LOX/LH2, N2O4/MMH, monopropellant hydrazine). It covers
    the feed system only." Only hydrazine is named as its monopropellant
    reference row; there is no H2O2 feed row, no decomposition chemistry
    and no chamber-temperature or exhaust calculation there. The new
    leaf carries no feed-cycle, pump-power, turbine-power or
    pressure-fed-tank-mass content.
  - cold-gas-thruster (this pack) scopes itself to INERT gas plenum
    blowdown: its body reads "Use when the task is sizing and assessing
    a cold gas thruster for spacecraft reaction control: a high pressure
    inert gas plenum, often nitrogen, discharges through a choked nozzle
    throat and produces a small thrust for attitude control." No
    catalytic chemistry and no chemical energy release anywhere in that
    leaf. The new leaf's propellant mass flow comes from F = mdot * v_e
    at the thrust point, not from a choked-throat solve, and it carries
    none of the cold-gas tokens (blowdown, plenum, choked-mass-flow,
    isothermal-blowdown-time-constant, nitrogen-rcs, total-impulse).
  - electrothermal-thruster (propulsion/electric) heats propellant
    ELECTRICALLY with an NH3/N2/H2/He working-gas table; its energy
    source is input electrical power, not in-propellant chemical heat
    release. The new leaf's energy source is the exothermic catalytic
    decomposition of hydrogen peroxide (2 H2O2(l) -> 2 H2O(g) + O2(g)),
    a different mechanism the electrothermal leaf never claims; the new
    leaf uses no heating efficiency, no resistojet or arcjet family and
    no thrust-to-power ratio.
  - Whole-tree greps at prep (real counts, from the probe receipt gate
    (a)): 'peroxide' 0 files across the whole skills/ + eval/ tree (the
    word appears nowhere in the repo); 'H2O2' 1 file
    (skills/propulsion/rocket/propellant-selection/SKILL.md line 31, the
    bipropellant oxidizer bullet above); 'silver[- ]catalyst' 0 files;
    'electrospray' / 'field[- ]emission' / 'feep' 0 files. Corpus
    eval/hit1-corpus.yaml: 'peroxide' 0 tasks, 'H2O2' 0 tasks;
    'hydrazine' 9 lines (2 route to the hydrazine leaf, the rest are
    router-leaf comment headers and space-systems tank rows);
    'monopropellant' appears only in hydrazine-thruster /
    rocket-engine-cycle / space-systems tank contexts. GENUINE
    propulsion gap (GO-1): no leaf owns the peroxide decomposition
    energy balance, the concentration input with water dilution, or the
    expansion of the steam-oxygen product mixture.
- Standards id: ecss (reference-only, present in standards-map.yaml
  line 94, grep-verified; sibling rocket convention: cold-gas-thruster,
  hydrazine-monopropellant-thruster, rocket-engine-cycle and the rest
  of the rocket pack all carry standards: [id: ecss,
  reference-only: true]). Ledger Standard: ecss.
- Family: propulsion

## Claim

Compute the hydrogen peroxide monopropellant thruster station point for
spacecraft reaction control duty: decompose high-test hydrogen peroxide
(HTP) catalytically over a silver catalyst bed at a documented peroxide
concentration w (mass fraction H2O2 in water, the water dilution) and
expand the hot product gas to vacuum. The decomposition 2 H2O2(l) ->
2 H2O(g) + O2(g) is exothermic; the adiabatic decomposition (chamber)
temperature T_c comes from the Hess-law energy balance at the 298.15 K
reference state: the net heat released per mole of H2O2 fed (products
all vapor, dilution water included) equals the product sensible heat
from T_REF up to T_c, with documented quadratic heat-capacity fits for
H2O(g) and O2(g). The product mixture is the steam-oxygen gas from the
decomposition plus the vaporized dilution water, at a fixed frozen
composition; it expands isentropically to vacuum: exhaust velocity
v_e = sqrt(2 gamma/(gamma-1) R_mix T_c) with gamma evaluated at the
chamber state and R_mix from the mixture molar mass, giving the vacuum
specific impulse Isp = v_e / g0 and, at a required vacuum thrust F, the
propellant mass flow mdot = F / v_e (F = mdot * v_e, no exit-pressure
term). Produces the steam-oxygen product mole and mass fractions, the
net decomposition heat release at the reference state, the adiabatic
decomposition temperature T_c, the mixture molar mass, gas constant and
isentropic exponent, the vacuum exhaust velocity, the vacuum specific
impulse, the propellant mass flow at the thrust point, and the advisory
silver-catalyst-bed band verdict (published silver-catalyst bed band,
reported reference-only, never enforced). The model is closed form and
deterministic, with the peroxide concentration w in the documented
decomposition-supporting band [0.85, 1.0] (85 to 100 percent by mass;
85 percent is the published silver-catalyst HTP monopropellant service
floor, 85 to 98 percent by weight in the literature) as the single
composition-driving input: raising w removes dilution water, which
removes the vaporization load and the extra gas mass, so T_c rises
monotonically from 901.7013222428 K at w = 0.85 to the pure-peroxide
water-vapor-heating-only bound 1271.0022500679 K at w = 1.0 (real
anchor); the computed span brackets the published decomposition-
temperature class of roughly 900 to 1100 K for 85 to 98 percent service
(98 percent near the published 98 percent adiabatic decomposition
temperature of about 1210 K, 937 C, reported reference-only), and the
pure-peroxide point rises above the silver melting ceiling, which is
exactly why service concentration is capped near 98 percent on silver
beds. Does NOT do: cold-gas inert-plenum blowdown, choked-throat mass
flow, plenum pressure history, tank gas mass, blowdown time constant,
operating time or total impulse (cold-gas-thruster owns the inert gas
RCS model; peroxide is never a cold-gas propellant there); feed cycles,
pump discharge pressure, pump and turbine powers, cycle power balance
or pressure-fed tank mass for any feed system (rocket-engine-cycle owns
the feed system, and its monopropellant row is the N2H4 feed-table
entry); electrical heating of NH3, N2, H2 or He, resistojet or arcjet
families, heating efficiency or thrust-to-power (electrothermal-thruster
owns electrically heated propellant); hydrazine decomposition, the
ammonia dissociation fraction, the NH3/N2/H2 product mixture or any
N2H4 chemistry (hydrazine-monopropellant-thruster owns the hydrazine
station, N2H4-specific end to end); propellant-family classification,
O/F bulk density, density impulse or propellant mass fraction trades
(propellant-selection owns the families trade; its H2O2 storable-
oxidizer classification bullet stays untouched); nozzle hardware sizing,
throat area solve, area ratio, exit static pressure or any
(Pe - Pa) * Ae pressure term (nozzle-design and the nozzle leaves own
expansion hardware; the exhaust velocity here is the fully expanded
vacuum form of the decomposed steam-oxygen gas only); a chemical-
equilibrium solve (w is an input, never solved, no equilibrium
composition iteration, and the decomposition is treated as complete);
catalyst-bed hardware design, bed heat transfer, silver surface area or
ignition transient analysis; decomposition of dilute peroxide below the
documented 0.85 support floor; any efficiency multiplier on the ideal
exhaust velocity; enforcement of the published ~150 to 190 s vacuum
impulse class or of the published decomposition-temperature band, which
are reported reference-only, and the concentration band [0.85, 1.0] is
the model domain, enforced, while the temperature and impulse bands are
advisory only.

## Model (implement exactly)

Pure stdlib, math only, deterministic, closed form plus one bisection.
Module constants (every fixed number):

- G0 = 9.80665 m/s^2 (standard gravity, rocket pack convention).
- T_REF = 298.15 K (reference state: liquid H2O2 feed and liquid
  dilution water, ideal gas products).
- R_UNIV = 8.314462618 J/(mol K), R_UNIV_KMOL = 8314.462618
  J/(kmol K).
- Molar masses, g/mol (internally consistent, H = 1.00794,
  O = 15.9994): M_H2O2 = 34.01468, M_H2O = 18.01528, M_O2 = 31.9988.
  Product mass closes on the feed mass at every w (mass closure
  identity, real anchor).
- Formation enthalpies at T_REF, J/mol (published NIST data):
  DELTA_HF_H2O2_LIQ = -187780.0 (liquid hydrogen peroxide),
  DELTA_HF_H2O_LIQ = -285830.0 (liquid water),
  DELTA_HF_H2O_GAS = -241826.4 (steam). Derived constants:
  Q_BASE = -(DELTA_HF_H2O_GAS - DELTA_HF_H2O2_LIQ) = 54046.4 J/mol,
  the gas-product decomposition enthalpy release per mole of H2O2 at
  T_REF (the receipt's published formation-enthalpy pair, H2O2(l)
  -187.8 kJ/mol and H2O(g) -241.8 kJ/mol, gives the same -54 kJ/mol
  class; the widely published condensed-product decomposition enthalpy
  -98.2 kJ/mol at 25 C differs from the gas-product value by the water
  vaporization load, DELTA_H_VAP_H2O_298 = DELTA_HF_H2O_GAS -
  DELTA_HF_H2O_LIQ = 44003.6 J/mol, i.e. 98.2 - 44.0 = 54.2 kJ/mol
  class, internally consistent).
- Heat-capacity fits cp(T) = a + b*T + c*T^2, J/(mol K), exact
  quadratics through the documented NIST-JANAF (Chase 1998) ideal-gas
  reference points (T K, cp J/(mol K)): H2O(g) (298.15, 33.59),
  (1000.0, 41.27), (2000.0, 51.20); O2(g) (298.15, 29.38),
  (1000.0, 34.86), (2000.0, 37.75). Coefficients from the closed-form
  divided-difference fit, c = (slope13 - slope12)/(T3 - T2),
  b = slope12 - c*(T1 + T2), a = cp1 - b*T1 - c*T1^2 with slope12 =
  (cp2 - cp1)/(T2 - T1) and slope13 = (cp3 - cp1)/(T3 - T1); the
  builder must implement that fit (or hardcode the anchor coefficients,
  which must then reproduce the anchor bit-for-bit):
  CP_H2O = (30.150107726136, 0.011714838411, -0.000000594946),
  CP_O2 = (26.190482217943, 0.011559276673, -0.000002889759).
- Decomposition-supporting concentration domain (documented, enforced):
  DECOMPOSITION_SUPPORT_MIN_W = 0.85, domain w in [0.85, 1.0]; the
  published silver-catalyst HTP monopropellant service range is 85 to
  98 percent by weight, and below 0.85 the dilution-water vaporization
  load dominates the release so the all-vapor decomposition temperature
  leaves the documented monopropellant class. w outside the domain
  raises ValueError.
- T_SOLVE_HI = 2600.0 K (bisection upper bracket; the maximum in-domain
  root is the pure-peroxide limit 1271.0022500679 K, real anchor, well
  inside the bracket).
- Silver-catalyst-bed operating band (reference-only, advisory):
  SILVER_BED_BAND_LO = 823.15 K (550 C), SILVER_BED_BAND_HI = 1234.93 K
  (961.78 C, the silver melting point, published reference data; the
  published 98 percent HTP catalyst-bed studies report adiabatic
  decomposition near 937 C, leaving a narrow margin below melting).
  Never enforced.

Defining relations (pin these exactly; every function below derives
from them):

- Stoichiometry per mole of H2O2 fed at mass fraction w: dilution water
  n_w = (1 - w)/w * M_H2O2 / M_H2O moles (liquid, vaporized into the
  products); decomposition products n_h2o = 1 + n_w and n_o2 = 0.5
  (2 H2O2 -> 2 H2O + O2 plus the dilution water as steam); total product
  moles n_tot = 1.5 + n_w (1.709789072881 at w = 0.90, 1.5 at w = 1.0,
  real anchor). Product mass is conserved: (1 + n_w) * 18.01528 +
  0.5 * 31.9988 = 34.01468 + n_w * 18.01528 exactly.
- Net heat release (Hess-law energy balance at T_REF, J per mole of
  H2O2 fed, all products vapor): Q(w) = -[(1 + n_w) DELTA_HF_H2O_GAS +
  0.5 * 0 - DELTA_HF_H2O2_LIQ - n_w DELTA_HF_H2O_LIQ], equivalently
  Q(w) = Q_BASE - n_w * DELTA_H_VAP_H2O_298. The dilution water enters
  liquid and leaves steam, so its vaporization load is implicit in the
  liquid-reference feed term. Q is linear in n_w with slope
  -44003.6 J/mol water (real anchor: -44003.600000, diff 1.019e-10) and
  strictly increasing in w across the domain: Q(0.90) =
  44814.925553 J/mol, Q(1.0) = 54046.400000 J/mol = Q_BASE exactly
  (real anchor).
- Adiabatic decomposition temperature T_c: the root of product sensible
  heat from T_REF to T_c equaling Q(w), where the sensible heat is the
  integral of product_heat_capacity over temperature, i.e. per product
  species i, n_i times (a_i (T - T_REF) + (b_i/2)(T^2 - T_REF^2) +
  (c_i/3)(T^3 - T_REF^3)). The left side is strictly increasing in T
  and Q(w) > 0 on the domain, so the root on [T_REF, T_SOLVE_HI] is
  unique and the bisection (300 iterations) closes it. No closed-form
  shortcut replaces the solve: the quadratic cp fits make the balance
  cubic in T.
- Mixture gas: mean molar mass M_mix = (34.01468 + n_w * 18.01528) /
  n_tot g/mol (also kg/kmol), specific gas constant R_mix =
  8314.462618 / M_mix J/(kg K). Isentropic exponent at T: gamma =
  cp_mix / (cp_mix - R_UNIV) with cp_mix the mole-fraction-weighted
  frozen mixture heat capacity at T, J/(mol K).
- Vacuum exhaust velocity (frozen-composition isentropic expansion,
  fully expanded, p_e = 0): v_e = sqrt(2 gamma/(gamma - 1) R_mix T_c)
  with gamma evaluated at T_c. Vacuum specific impulse Isp = v_e / G0.
  Vacuum thrust F = mdot * v_e (no pressure term), so the propellant
  mass flow at the thrust point is mdot = F / v_e.
- Silver-catalyst-bed band verdict (advisory, reference-only): within
  the band iff t_k is inside [SILVER_BED_BAND_LO, SILVER_BED_BAND_HI];
  the verdict is a boolean report, never an enforced limit.

Functions (public API, 16 functions, all pure, math only):

- dilution_water_moles(w) -> float, moles of liquid dilution water per
  mole of H2O2: (1 - w)/w * M_H2O2 / M_H2O. ValueError if w is not
  finite or lies outside [0.85, 1.0].
- product_mole_numbers(w) -> tuple (n_h2o, n_o2), moles of H2O and O2
  per mole of H2O2 fed: (1 + n_w, 0.5). ValueError domain as
  dilution_water_moles.
- total_product_moles(w) -> float, n_tot = 1.5 + n_w. ValueError domain
  as dilution_water_moles.
- decomposition_heat_released(w) -> float, J per mole of H2O2 fed:
  Q_BASE - n_w * DELTA_H_VAP_H2O_298 (Hess-law balance at T_REF,
  products all vapor). ValueError domain as dilution_water_moles.
- product_heat_capacity(w, t_k) -> float, Sigma n_i cp_i(t_k) at
  temperature t_k, J/(K mol H2O2 fed). ValueError domain as
  dilution_water_moles plus t_k not positive and finite.
- product_sensible_heat(w, t_k) -> float, product sensible heat from
  T_REF up to t_k, J per mole of H2O2 fed. ValueError domain as
  product_heat_capacity.
- decomposition_temperature(w) -> float, the adiabatic decomposition
  (chamber) temperature T_c in K by bisection on [T_REF, T_SOLVE_HI]
  (300 iterations). ValueError domain as dilution_water_moles, plus a
  defensive ValueError if the solved root is not physical (not finite
  or not above T_REF, e.g. if the heat release never meets the sensible
  heat inside the bracket).
- product_mole_fractions(w) -> tuple (y_h2o, y_o2), steam-oxygen mole
  fractions of the product mixture; sum to 1. ValueError domain as
  dilution_water_moles.
- product_mass_fractions(w) -> tuple (x_h2o, x_o2), steam-oxygen mass
  fractions of the product mixture (x_o2 is the oxygen fraction carried
  in the exhaust); sum to 1. ValueError domain as dilution_water_moles.
- mixture_molar_mass(w) -> float, g/mol = feed mass per mole H2O2 /
  n_tot. ValueError domain as dilution_water_moles.
- mixture_gas_constant(w) -> float, J/(kg K) = R_UNIV_KMOL /
  mixture_molar_mass(w). ValueError domain as dilution_water_moles.
- mixture_gamma(w, t_k) -> float, cp_mix / (cp_mix - R_UNIV) at t_k.
  ValueError domain as dilution_water_moles plus t_k not positive and
  finite.
- vacuum_exhaust_velocity(w) -> float, m/s: sqrt(2 gamma/(gamma - 1)
  R_mix T_c) with T_c = decomposition_temperature(w), gamma =
  mixture_gamma(w, T_c), R_mix = mixture_gas_constant(w). ValueError
  domain as dilution_water_moles.
- vacuum_specific_impulse(w, g0 = G0) -> float, s:
  vacuum_exhaust_velocity(w) / g0. ValueError domain as
  dilution_water_moles plus g0 not positive and finite.
- propellant_mass_flow(thrust_n, w) -> float, kg/s: thrust_n /
  vacuum_exhaust_velocity(w). ValueError if thrust_n is not positive
  and finite or w out of domain.
- within_silver_catalyst_bed_band(t_k) -> bool,
  SILVER_BED_BAND_LO <= t_k <= SILVER_BED_BAND_HI. ValueError if t_k is
  not positive and finite.

Identities to test (closed form; assert with isclose/abs bounds, never
exact float equality on computed sums):

- Mass closure: product mass (1 + n_w) * 18.01528 + 0.5 * 31.9988
  equals the feed mass 34.01468 + n_w * 18.01528 per mole of H2O2 fed
  at w = 0.85, 0.90, 0.98, 1.0 with relative error 0 to 2.047e-16
  (real anchor: 1.776e-16, 0.000e+00, 2.047e-16, 0.000e+00), proving
  the internally consistent molar masses.
- Fraction sums: y_h2o + y_o2 = 1 and x_h2o + x_o2 = 1 to machine zero
  (real anchor, 0.000e+00) at w = 0.85, 0.90, 0.98, 1.0.
- Heat-release identity at the pure-peroxide bound:
  decomposition_heat_released(1.0) = 54046.400000 J/mol equals Q_BASE
  to 0.000e+00 J (real anchor), i.e. the gas-product decomposition
  release equals -(DELTA_HF_H2O_GAS - DELTA_HF_H2O2_LIQ); the
  condensed-product published class -98.2 kJ/mol differs from this gas-
  product value by the 44003.6 J/mol water vaporization load at
  298.15 K, documented, and the decomposition heat release at w = 0.90
  is 44814.925553 J/mol (real anchor).
- Heat-release linearity in the dilution: Q(w) = Q_BASE - n_w *
  DELTA_H_VAP_H2O_298, so dQ/dn_w = -44003.600000 J/mol water against
  -DELTA_H_VAP_H2O_298 with difference 1.019e-10 (real anchor).
- Energy-balance closure: the sensible-heat residual at the solved T_c
  is at or below 2.183e-11 J at w = 0.85, 0.90, 0.98, 1.0 (real anchor:
  -7.276e-12, 7.276e-12, -7.276e-12, -2.183e-11 J).
- Concentration-limited-decomposition sweep: T_c, v_e and Isp rise
  strictly with w across 0.85, 0.90, 0.95, 0.98, 1.0 (real anchor:
  T_c 901.701322, 1024.235458, 1147.220926, 1221.371921, 1271.002250
  K; v_e 1785.807842, 1916.066827, 2039.097072, 2109.814494,
  2155.758028 m/s; Isp 182.101721, 195.384441, 207.930034, 215.141205,
  219.826141 s). Raising the concentration toward w = 1.0 raises the
  decomposition temperature toward the water-vapor-heating-only bound
  T_c(1.0) = 1271.0022500679 K (no dilution water: the release heats
  only the decomposition steam and oxygen, 1.5 mol gas per mole H2O2);
  the pure-peroxide point exceeds the reported silver-catalyst-bed
  ceiling 1234.93 K, which is why service concentration on silver beds
  is capped near 98 percent. The w -> 0 direction is not a physical
  decomposition state: dilution water raises the vaporization load and
  the net all-vapor reaction turns endothermic below roughly 60 percent
  by mass, and the model refuses below the documented support floor
  0.85, so the closed-form bound reported here is the pure-peroxide
  endpoint, not a dilute limit. The computed span 901.7 to 1271.0 K
  brackets the published decomposition-temperature class of roughly 900
  to 1100 K for 85 to 98 percent service (the 98 percent point,
  1221.372 K, sits within one percent of the published 98 percent
  adiabatic decomposition temperature of about 1210 K, 937 C),
  reported reference-only.
- Gamma trend: mixture_gamma at the chamber state falls mildly as the
  mixture dries (steam fraction up, mean cp up relative to the gas
  constant): real anchor 1.274513 at w = 0.85, 1.265623 at w = 0.90,
  1.257779 at w = 0.95, 1.253527 at w = 0.98, 1.250869 at w = 1.0.
- Exhaust identity: vacuum_exhaust_velocity(w) reproduces
  sqrt(2 gamma/(gamma - 1) R_mix T_c) evaluated term by term, and the
  frozen-expansion energy identity 0.5 * v_e^2 = cp_specific * T_c
  (cp_specific the mass-basis mixture heat capacity at the chamber
  state, cp_mix_molar * 1000 / M_mix) closes to at or below 9.313e-10
  J/kg at w = 0.85, 0.90, 0.98 and to 0.000e+00 at w = 1.0 (real
  anchor); vacuum_specific_impulse(w) equals v_e / G0 exactly.
- Isentropic consistency (Mach relation check): the finite-pressure
  frozen isentropic form v_e(p_e) = sqrt(2 gamma/(gamma - 1) R_mix
  T_c (1 - (p_e/p_c)^((gamma-1)/gamma))) evaluated at p_e/p_c = 1e-6
  and w = 0.90 gives 1862.581707 m/s, and the vacuum form
  1916.066827 m/s is its p_e -> 0 limit (real anchor, relative
  difference 2.791e-02 between the two pressure ratios, physically the
  residual expansion work of the last 1e-6 of pressure).
- Band verdict semantics: within_silver_catalyst_bed_band(T_c(0.85)),
  (T_c(0.90)) and (T_c(0.98)) are True (901.701, 1024.235 and
  1221.372 K inside [823.15, 1234.93] K, the 98 percent point with
  only about 13.6 K of margin below the reported silver melting
  ceiling); within_silver_catalyst_bed_band(T_c(1.0)) is False
  (1271.002 K above the ceiling); True at the closed boundaries
  823.15 K and 1234.93 K (real anchor).
- Mass flow linearity: propellant_mass_flow scales linearly with thrust
  at fixed w; mdot(44 N)/mdot(22 N) at w = 0.90 = 2.000000000000000
  (real anchor).
- Determinism: decomposition_temperature(0.90) returns
  1024.2354582656317 on every call, bit-identical.
- ValueErrors across the module: concentration w at -0.1, 0.0, 0.5,
  0.84, 1.01, nan and inf; t_k at 0 and -5 for product_heat_capacity,
  product_sensible_heat and mixture_gamma; g0 at 0; thrust_n at 0 and
  -5; t_k at 0 and nan for within_silver_catalyst_bed_band. All raise
  ValueError (real anchor, 20 cases).
- The module never returns blowdown, plenum, choked-throat, feed-cycle,
  pump-power, heating-efficiency, hydrazine or ammonia outputs, never
  solves an equilibrium, never enforces a band: the temperature and
  impulse bands are reported by the advisory boolean only, and the
  concentration band is the enforced model domain.

## Worked example

The 1 N reaction-control duty at peroxide concentration w = 0.90 (the
query-1 design point, 90 percent H2O2 by mass with the water dilution),
the 22 N RCS reference point at w = 0.90, and the query-2
concentration-limit points at w = 0.85 and w = 0.98. All values below
are REAL outputs of the prep anchor /tmp/w46spec/anchor_h2o2_thruster.py
(/usr/bin/python3 3.9.6, stdlib math, closed form plus one bisection,
exit 0; byte-identical output verified under
~/.pyenv/versions/3.13.12/bin/python3).

- 1 N point, w = 0.90 (real anchor): per mole of H2O2 fed, dilution
  water n_w = 0.209789072881 mol; products 1.209789072881 mol H2O +
  0.5 mol O2 (n_tot = 1.709789072881 mol; mole fractions 0.707566267717
  H2O and 0.292433732283 O2; mass fractions 0.576669249865 H2O and
  0.423330750135 O2); net heat release Q = 44814.925553 J/mol; mixture
  molar mass 22.1045329441 g/mol with R_mix = 376.1428770760 J/(kg K);
  adiabatic decomposition temperature T_c = 1024.2354582656 K; gamma at
  the chamber state = 1.2656230167; vacuum exhaust velocity
  v_e = 1916.0668272739 m/s; vacuum specific impulse
  Isp = 195.3844408920 s; propellant mass flow at 1 N mdot =
  0.000521902465 kg/s (0.521902465 g/s); silver-catalyst-bed band
  verdict True (1024.235 K inside the reported [823.15, 1234.93] K
  band; energy-balance residual 7.276e-12 J).
- 22 N point, w = 0.90 (real anchor): identical station numbers
  (n_w, products, Q, M_mix, R_mix, T_c, gamma, v_e, Isp, verdict), with
  propellant mass flow mdot = 22 / 1916.0668272739 = 0.011481854227
  kg/s (11.481854227 g/s).
- Concentration-limit points at 22 N (query-2 limits, real anchor):
  w = 0.85 gives T_c = 901.7013222428 K, v_e = 1785.8078417405 m/s,
  Isp = 182.1017209486 s and mdot = 0.012319354572 kg/s, verdict True;
  w = 0.98 gives T_c = 1221.3719212069 K, v_e = 2109.8144943685 m/s,
  Isp = 215.1412046283 s and mdot = 0.010427457039 kg/s, verdict True.
  The 98 percent decomposition temperature sits within one percent of
  the published 98 percent adiabatic decomposition temperature of about
  1210 K (937 C) and leaves only about 13.6 K of margin below the
  reported 1234.93 K silver melting ceiling, matching the published
  narrow-margin reports for 98 percent HTP on silver beds.
- Pure-peroxide heating-only bound, w = 1.0 (real anchor): no dilution
  water; Q(1.0) = 54046.400000 J/mol equals Q_BASE exactly; products
  1.0 mol H2O(g) + 0.5 mol O2(g) per mole of H2O2 (1.5 mol gas, all
  water vapor); T_c = 1271.0022500679 K, v_e = 2155.7580276312 m/s,
  Isp = 219.8261412033 s, and the silver-catalyst-bed band verdict is
  False (1271.002 K above the reported silver melting ceiling 1234.93 K:
  pure peroxide decomposition would melt a silver bed, which is why
  service concentration on silver beds is capped near 98 percent).
- Read-off: the 1 N duty needs 0.521902465 g/s of 90 percent HTP at an
  ideal vacuum Isp of 195.3844408920 s with a 1024.235 K decomposition
  temperature inside the reported silver-bed band; the 22 N point needs
  11.481854227 g/s. Running the same duty at the 85 percent floor cools
  the chamber to 901.701 K and drops the ideal impulse to 182.101721 s;
  the 98 percent top pushes the chamber to 1221.372 K, near the silver
  melting ceiling, at 215.141205 s ideal. The ideal-model impulses sit
  at or just above the published real-engine vacuum class of roughly
  150 to 190 s for peroxide thrusters because real thrusters carry
  nozzle efficiency and finite-expansion losses that this leaf's fully
  expanded ideal vacuum form does not model; the gap is the loss
  account, and the published class stays reference-only. The sweep
  shows the physics trade: raising the concentration removes dilution
  water (less vaporization load, less gas mass per mole of H2O2), so
  T_c and Isp rise monotonically from 901.7 K / 182.1 s at 85 percent
  to the pure-peroxide water-vapor-heating-only bound 1271.0 K /
  219.8 s at 100 percent, with the chamber gamma falling mildly from
  1.2745 to 1.2509 as the mixture dries.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w46spec/anchor_h2o2_thruster.py (/usr/bin/python3 3.9.6, stdlib
math, closed form plus one bisection, exit 0, byte-identical under
~/.pyenv/versions/3.13.12/bin/python3).

## Validation list (contract test must include)

1. dilution_water_moles: 0.209789072881 at w = 0.90,
   0.333194409870 at w = 0.85 (formula (1 - w)/w * 34.01468/18.01528)
   and 0.000000000000 at w = 1.0, within 1e-9 relative.
2. product_mole_numbers and total_product_moles: (1.209789072881,
   0.5) and 1.709789072881 at w = 0.90; (1.0, 0.5) and 1.5 at w = 1.0,
   within 1e-12 relative.
3. Mass closure: (1 + n_w) * 18.01528 + 0.5 * 31.9988 equals
   34.01468 + n_w * 18.01528 within 1e-12 relative at w = 0.85, 0.90,
   0.98, 1.0 (real anchor relative errors 1.776e-16 to 2.047e-16).
4. product_mole_fractions and product_mass_fractions: y sums and x sums
   equal 1 within 1e-12 at w = 0.85, 0.90, 0.98, 1.0; the w = 0.90
   pairs are (0.707566267717, 0.292433732283) and (0.576669249865,
   0.423330750135), each within 1e-9 relative.
5. decomposition_heat_released: 44814.925553 J/mol at w = 0.90 and
   54046.400000 J/mol at w = 1.0 within 1e-9 relative; Q(1.0) equals
   Q_BASE within 1e-12 relative; (Q(0.98) - Q(0.90)) /
   (n_w(0.98) - n_w(0.90)) = -44003.600000 within 1e-9 relative of
   -DELTA_H_VAP_H2O_298.
6. decomposition_temperature: 1024.2354582656 K at w = 0.90,
   901.7013222428 K at w = 0.85, 1221.3719212069 K at w = 0.98 and
   1271.0022500679 K at w = 1.0 within 1e-9 relative; the five-point
   sweep 0.85/0.90/0.95/0.98/1.0 gives strictly increasing chamber
   temperatures 901.701322, 1024.235458, 1147.220926, 1221.371921,
   1271.002250 K; the sensible-heat residual at each solved T_c is
   below 1e-9 J.
7. mixture_molar_mass and mixture_gas_constant: 22.1045329441 g/mol
   and 376.1428770760 J/(kg K) at w = 0.90, within 1e-9 relative.
8. mixture_gamma at the chamber state: 1.2656230167 at w = 0.90 within
   1e-9 relative; gamma falls across the sweep from 1.274513 (w = 0.85)
   to 1.250869 (w = 1.0).
9. vacuum_exhaust_velocity and vacuum_specific_impulse: 1916.0668272739
   m/s and 195.3844408920 s at w = 0.90; 1785.8078417405 m/s and
   182.1017209486 s at w = 0.85; 2109.8144943685 m/s and
   215.1412046283 s at w = 0.98; 2155.7580276312 m/s and
   219.8261412033 s at w = 1.0, each within 1e-6 relative; Isp equals
   v_e / G0 within 1e-12 relative; the frozen-expansion energy identity
   0.5 * v_e^2 = cp_specific * T_c closes within 1e-6 relative at each
   worked point; the finite-pressure isentropic form at p_e/p_c = 1e-6,
   w = 0.90 gives 1862.581707 m/s against the vacuum 1916.066827 m/s.
10. propellant_mass_flow: 0.000521902465 kg/s at (1.0, 0.90),
    0.011481854227 kg/s at (22.0, 0.90), 0.012319354572 kg/s at
    (22.0, 0.85) and 0.010427457039 kg/s at (22.0, 0.98), each within
    1e-6 relative; mass flow scales linearly with thrust at fixed w
    (ratio exactly 2.000000000000000 for 44 N over 22 N at w = 0.90).
11. within_silver_catalyst_bed_band: True at T_c(0.85) = 901.701 K,
    T_c(0.90) = 1024.235 K and T_c(0.98) = 1221.372 K; False at
    T_c(1.0) = 1271.002 K (above the 1234.93 K ceiling); True at the
    closed boundaries 823.15 K and 1234.93 K.
12. ValueErrors: dilution_water_moles and decomposition_temperature at
    w = -0.1, 0.0, 0.5, 0.84, 1.01, nan and inf;
    product_heat_capacity, product_sensible_heat and mixture_gamma at
    t_k = 0 and -5; vacuum_specific_impulse at g0 = 0;
    propellant_mass_flow at thrust 0 and -5;
    within_silver_catalyst_bed_band at t_k = 0 and nan. Every call
    raises ValueError (real anchor, 20 cases).
13. Determinism: decomposition_temperature(0.90) returns
    1024.2354582656317 bit-identical on repeated calls; no imports
    beyond math; the public API returns no blowdown, plenum,
    choked-throat, feed-cycle, pump-power, heating-efficiency, hydrazine
    or ammonia outputs anywhere and never enforces the temperature or
    impulse bands. Test passes under BOTH interpreters (/usr/bin/python3
    3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3), verified
    byte-identical at prep. No exact-float equality on computed sums;
    use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (eval/hit1-wave46-hydrogen-peroxide-monopropellant-thruster.yaml)

Query 1 (copy verbatim):
  "size the hydrogen-peroxide-monopropellant-thruster for the 1 N
  spacecraft reaction control duty: the peroxide-decomposition chamber
  temperature from the catalytic energy balance of H2O2 at the 90
  percent concentration with the water dilution, then the vacuum exhaust
  velocity and specific impulse of the steam-oxygen product mixture
  through the nozzle"
  intent: "propulsion; hydrogen peroxide monopropellant RCS sizing at
  1 N, chamber temperature from the peroxide-decomposition catalytic
  energy balance of H2O2 at the 90 percent concentration with the water
  dilution, then vacuum exhaust velocity and specific impulse of the
  steam-oxygen product mixture"
  expected_skill: "propulsion/rocket/hydrogen-peroxide-monopropellant-thruster"
Query 2 (copy verbatim):
  "run the peroxide-decomposition energy balance for the
  hydrogen-peroxide-thruster design point: adiabatic decomposition
  temperature and frozen-mixture expansion to vacuum specific impulse
  at the 85 and the 98 percent concentration limits, with the
  silver-catalyst-bed band check for the monopropellant RCS thruster"
  intent: "propulsion; peroxide-decomposition energy balance at the 85
  and 98 percent concentration limits with decomposition temperatures
  and frozen-mixture vacuum impulses plus the advisory
  silver-catalyst-bed band check"
  expected_skill: "propulsion/rocket/hydrogen-peroxide-monopropellant-thruster"
Task ids: w46-hydrogen-peroxide-monopropellant-thruster-1 and -2. Prep
grep of eval/hit1-corpus.yaml (real counts from the wave-46 receipt gate
(e)): hydrogen-peroxide-monopropellant-thruster 0, peroxide-decomposition
0, steam-oxygen 0, silver-catalyst-bed 0, hydrogen-peroxide-thruster 0,
peroxide 0 tasks, H2O2 0 tasks. The tokens above exist on no router row
and in no corpus task today, so Hit@1 is clean. The hydrazine leaf's
owned tokens (hydrazine-decomposition, ammonia-dissociation-fraction,
catalytic-decomposition, monopropellant-rcs, catalyst-bed,
decomposition-temperature) are deliberately absent from both queries;
the nearest router rows route elsewhere (rocket-engine-cycle rows carry
feed-cycle, pump and turbine tokens; cold-gas-thruster rows carry
blowdown, plenum and choked-mass-flow tokens, which this leaf avoids;
the propellant-tank-sizing row carries the density example). The
queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size and assess a hydrogen
peroxide monopropellant thruster for spacecraft reaction control:" and
include the outputs in the Claim. First tag:
hydrogen-peroxide-monopropellant-thruster. Additional tags ONLY (the
receipt gate (f) list, verbatim): peroxide-decomposition,
steam-oxygen-mixture, silver-catalyst-bed,
concentration-limited-decomposition. NEVER single generic words
(peroxide, thruster, monopropellant, decomposition, temperature,
catalyst, bed, nozzle, thrust, impulse, isp, exhaust, mixture,
concentration) and NEVER the hydrazine-monopropellant-thruster tokens
hydrazine-decomposition, ammonia-dissociation-fraction,
catalytic-decomposition, monopropellant-rcs, catalyst-bed,
decomposition-temperature, hydrazine-monopropellant-thruster, and NEVER
the cold-gas-thruster tokens blowdown, plenum, choked-mass-flow,
nitrogen-rcs, plenum-blowdown, isothermal-blowdown-time-constant,
total-impulse, reaction-control-thruster-sizing, and NEVER the
rocket-engine-cycle tokens feed-cycle, gas-generator-cycle,
staged-combustion, expander-cycle, pressure-fed, pump-fed, pump-power,
turbine-power, and NEVER the electrothermal-thruster tokens resistojet,
arcjet, heated-propellant, power-to-thrust, electric-propulsion, and
NEVER propellant-selection tokens (propellant-family, o-f-ratio,
density-impulse, bulk-density, propellant-mass-fraction) or
propellant-tank-sizing tokens (tank-volume, ullage, tank-density).
50-150 words, <=1000 chars, no em dash, action verb present.
Recommended wording (117 words, 992 chars, verified): "Use when you
must size and assess a hydrogen peroxide monopropellant thruster for
spacecraft reaction control: compute the decomposition heat release of
H2O2 at a documented concentration with the water dilution, the
adiabatic decomposition temperature from the peroxide decomposition
energy balance, and the frozen composition isentropic nozzle expansion
of the steam-oxygen product mixture to the vacuum exhaust velocity, the
vacuum specific impulse and the propellant mass flow at the required
thrust, with the advisory silver-catalyst-bed band check. Produces the
steam-oxygen mixture composition and mass fractions, decomposition
temperature, mixture gas constant, isentropic exponent, exhaust
velocity, vacuum specific impulse, propellant mass flow and the
silver-catalyst-bed band verdict that size a monopropellant RCS
thruster. Trigger: hydrogen-peroxide-monopropellant-thruster,
peroxide-decomposition, steam-oxygen-mixture, silver-catalyst-bed,
concentration-limited-decomposition." The sibling-owned tokens listed
above must not appear.

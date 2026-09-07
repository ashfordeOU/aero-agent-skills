# Wave-45 leaf spec: hydrazine-monopropellant-thruster (propulsion,
# rocket pack)

- Path: skills/propulsion/rocket/hydrazine-monopropellant-thruster/
- Pack: rocket (present siblings cold-gas-thruster,
  combustion-chamber-design, hybrid-rocket-motor, injector-design,
  nozzle-area-ratio-selection, nozzle-design, propellant-selection,
  rocket-engine-cycle, rocket-gravity-loss,
  rocket-nozzle-divergence-loss, rocket-nozzle-flow-separation,
  rocket-sizing, rocket-staging, solid-rocket-motor,
  thrust-chamber-cooling, thrust-vector-control; adjacent fences in
  propulsion/electric (electrothermal-thruster) and
  space-systems/subsystems (propellant-tank-sizing)).
- Provenance: wave-45 propulsion probe receipt (ops/automation/state/
  wave45-recon/task-3-receipt.md, GO-2 rank 2, whole family FRESH at
  HEAD 5cc8fef3) dispatches this leaf: "Chemical monopropellant
  hydrazine thruster station math: catalytic decomposition energy
  balance to the chamber temperature with the ammonia-dissociation
  fraction as documented input, then isentropic nozzle expansion to
  exhaust velocity and vacuum specific impulse, with published
  decomposition-temperature and impulse bands reported
  reference-only." SPEC-TIME TRIAGE DONE FIRST: the three sibling
  SKILL.md bodies quoted below were read IN FULL at prep
  (skills/propulsion/rocket/cold-gas-thruster/SKILL.md,
  skills/propulsion/rocket/rocket-engine-cycle/SKILL.md,
  skills/propulsion/electric/electrothermal-thruster/SKILL.md) and
  the space-systems fence line was grep-verified in place
  (propellant-tank-sizing/SKILL.md line 95). Genuine overlap NOT
  found: the decomposition energy balance and the decomposed-gas
  expansion are owned by no sibling; GO, no decline file written.
- Claim fences (quoted from the sibling frontmatter and body at prep,
  none owns the hydrazine catalytic-decomposition station math, the
  energy balance to the chamber temperature at a documented
  ammonia-dissociation-fraction input):
  - cold-gas-thruster (this pack) scopes itself to INERT gas blowdown
    and defers hydrazine explicitly. Its body reads "Cold gas
    thrusters suit small spacecraft RCS duty: simple, safe, low
    thrust, modest total impulse; hydrazine and electric options
    carry far more impulse per kilogram when the mission demands it."
    Its frontmatter claims the plenum model: "compute the choked mass
    flow through the nozzle throat from the plenum pressure and
    temperature, the thrust from the mass flow and specific impulse,
    the tank gas mass from the plenum volume and pressure, the
    isothermal blowdown time constant and pressure history". Nothing
    in that leaf touches chemical decomposition: hydrazine appears in
    its body only as a deferred alternative, never as a reactant. The
    new leaf carries NONE of the cold-gas tokens (blowdown, plenum,
    choked-mass-flow, isothermal blowdown, nitrogen RCS): its
    propellant mass flow comes from F = mdot * v_e at the thrust
    point, not from a choked throat solve.
  - rocket-engine-cycle (this pack) limits itself to the FEED SYSTEM.
    Its frontmatter/body reads "with a small reference propellant
    table (LOX/RP-1, LOX/LH2, N2O4/MMH, monopropellant hydrazine).
    It covers the feed system only." The hydrazine entry there is a
    table row for feed analysis (single stream, no oxidizer split);
    the leaf computes pump discharge pressures, pump and turbine
    powers, the cycle power balance and feed-tank mass penalty. It
    has no decomposition chemistry and no chamber-temperature or
    exhaust calculation for the monopropellant: the new leaf does not
    touch feed-cycle, pump-power, turbine-power or
    pressure-fed-tank-mass content.
  - electrothermal-thruster (propulsion/electric) heats propellant
    ELECTRICALLY. Its body reads "this leaf only heats propellant, so
    it neither accelerates charged beams nor uses extraction electrode
    assemblies", and its propellant table is NH3, N2, H2, He (300 K
    reference values, no N2H4 anywhere). Its energy source is input
    electrical power converted to useful heating power with a heating
    efficiency; the new leaf's energy source is the exothermic
    catalytic decomposition of hydrazine (chemical heat release
    inside the propellant itself), which is a different mechanism the
    electrothermal leaf never claims. The new leaf uses no heating
    efficiency, no resistojet or arcjet family, no thrust-efficiency
    identity and no thrust-to-power ratio.
  - propellant-tank-sizing (space-systems/subsystems) touches
    hydrazine once, as a tank-sizing DENSITY example: its line 95
    reads "Hydrazine monopropellant tank: mass 100 kg, density 1008
    kg/m3" (grep-verified in place). The new leaf performs no tank
    volume, mass, ullage or pressure-vessel math; hydrazine density
    and tank sizing stay with propellant-tank-sizing.
  - Whole-tree greps at prep (real counts, from the probe receipt
    gate (a)): 'hydrazine decomposition' 0 files, 'catalytic
    decomposition' 0 files, 'catalyst bed' 0 files, 'N2H4' 0 files
    across the whole skills/ tree; 'monopropellant' appears in 4
    files, all tank or feed-cycle rows (rocket-engine-cycle
    propellant-table row and space-systems propellant-tank-sizing
    density rows). Corpus: 'hydrazine' 0 tasks, 'monopropellant' 1
    task (the space-systems tank-sizing task at eval corpus line
    3751), 'catalyst' 0 tasks. GENUINE propulsion gap (GO-2): no leaf
    owns the hydrazine decomposition energy balance, the
    ammonia-dissociation-fraction input, or the expansion of the
    decomposed product mixture.
- Standards id: ecss (reference-only, present in standards-map.yaml
  lines 94-103, grep-verified at line 94; sibling rocket convention:
  cold-gas-thruster, rocket-engine-cycle and the rest of the rocket
  pack all carry standards: [id: ecss, reference-only: true]). Ledger
  Standard: ecss.
- Family: propulsion

## Claim

Compute the hydrazine monopropellant thruster station point for
reaction control duty: decompose hydrazine catalytically at a
documented ammonia-dissociation-fraction input x and expand the
product gas to vacuum. The primary decomposition N2H4(l) ->
(4/3) NH3 + (1/3) N2 releases a fixed heat of decomposition, while a
fraction x of the ammonia formed dissociates endothermically
(NH3 -> (1/2) N2 + (3/2) H2), so the net heat release is a linear
decreasing function of x. The adiabatic decomposition (chamber)
temperature T_c comes from the Hess-law energy balance: the net heat
released at the reference state equals the product sensible heat
from T_REF up to T_c, with documented quadratic heat-capacity fits
cp(T) for NH3, N2 and H2 (298-2000 K reference data). The product
mixture (fixed, frozen composition) then expands isentropically to
vacuum: exhaust velocity v_e = sqrt(2 gamma/(gamma-1) R_mix T_c)
with gamma evaluated at the chamber state and R_mix from the mixture
molar mass, giving the vacuum specific impulse Isp = v_e / g0 and,
at a required vacuum thrust F, the propellant mass flow
mdot = F / v_e (F = mdot * v_e, no exit-pressure term). Produces the
decomposed mixture stoichiometry and mole numbers, the net
decomposition heat release, the decomposition temperature T_c, the
mixture molar mass, gas constant and isentropic exponent, the vacuum
exhaust velocity, the vacuum specific impulse, the propellant mass
flow at the thrust point, and the advisory catalyst-bed temperature
band verdict (published band, reported reference-only, never
enforced). The model is closed form and deterministic, with the
ammonia-dissociation fraction x in [0, 1] as the single
composition-driving input: x = 0 is the frozen limit (no ammonia
dissociation, ~1734 K chamber, real anchor) and x = 1 is the fully
dissociated limit N2H4 -> N2 + 2 H2 (~865 K chamber, real anchor);
the computed span brackets the published decomposition-temperature
band class of roughly 900 K near equilibrium dissociation to roughly
1700 K frozen, reported reference-only. Does NOT do: cold-gas
inert-plenum blowdown, choked-throat mass flow, tank gas mass,
blowdown time constant, operating time or total impulse
(cold-gas-thruster owns the inert gas RCS model; hydrazine appears
there only as a deferred alternative); feed cycles, pump discharge
pressure, pump and turbine powers, power balance, drive mass
fraction or pressure-fed tank mass for a monopropellant (or any)
feed system (rocket-engine-cycle owns the feed system, its hydrazine
row is a feed-analysis propellant-table entry only); electrical
heating of NH3, N2, H2 or He, resistojet or arcjet families,
heating efficiency, thrust efficiency or thrust-to-power
(electrothermal-thruster owns electrically heated propellant, its
table has no N2H4); tank volume, tank mass, ullage or density-based
propellant tank sizing (space-systems propellant-tank-sizing owns the
hydrazine density example); forward nozzle sizing, throat area
solve, choked mass flow through a throat, area ratio, exit static
pressure or any (Pe - Pa) * Ae pressure term (nozzle-design and the
nozzle leaves own expansion hardware; the exhaust velocity here is
the fully expanded vacuum form of the decomposed gas only); a
chemical-equilibrium solve (x is an input, never solved, no
equilibrium composition iteration); catalyst-bed hardware design,
bed heat transfer or ignition transient analysis; chamber
contraction, injector or thrust-chamber design; combustion products
beyond the closed-form decomposition balance; any efficiency
multiplier on the ideal exhaust velocity; enforcement of the
published ~230 s vacuum-impulse class or of the ~900 to ~1700 K
decomposition band, which are reported reference-only.

## Model (implement exactly)

Pure stdlib, math only, deterministic, closed form plus one
bisection. Module constants (every fixed number):

- G0 = 9.80665 m/s^2 (standard gravity, sibling rocket convention).
- T_REF = 298.15 K (reference state: liquid N2H4 feed, ideal gas
  products).
- R_UNIV = 8.314462618 J/(mol K), R_UNIV_KMOL = 8314.462618
  J/(kmol K).
- Molar masses, g/mol (internally consistent, N = 14.0067,
  H = 1.00794): HYDRAZINE_MOLAR_MASS = 32.04516,
  NH3_MOLAR_MASS = 17.03052, N2_MOLAR_MASS = 28.0134,
  H2_MOLAR_MASS = 2.01588. The product masses close on 32.04516 g
  per mole N2H4 at every x (rel err 2.2e-16, real anchor).
- Formation/dissociation enthalpies at T_REF, J/mol:
  DELTA_HF_N2H4_LIQ = 50.63e3 (liquid hydrazine),
  DELTA_HF_NH3_GAS = -45.94e3, DELTA_H_DISS_NH3 = 45.94e3 (heat
  absorbed dissociating one mole NH3(g)).
- Heat-capacity fits cp(T) = a + b*T + c*T^2, J/(mol K), exact
  quadratics through the documented 298-2000 K reference points
  (T, cp): NH3 (298.15, 35.59), (1000, 51.10), (2000, 62.60);
  N2 (298.15, 29.12), (1000, 32.70), (2000, 36.03);
  H2 (298.15, 28.84), (1000, 30.20), (2000, 33.00). Coefficients
  (must reproduce the anchor bit-for-bit):
  CP_NH3 = (27.1444498084, 3.018332529e-02, -6.227775096e-06),
  CP_N2 = (27.2889646381, 6.451553043e-03, -1.040517681e-06),
  CP_H2 = (28.4133255181, 1.280011723e-03, 5.066627591e-07).
- T_SOLVE_HI = 2600.0 K (bisection upper bracket; the maximum root
  is the frozen T_c ~1733.6 K, real anchor, well inside the bracket).
- Catalyst-bed continuous operating band (reference-only, advisory):
  CATALYST_BED_BAND_LO = 1073.15 K (800 C), CATALYST_BED_BAND_HI =
  1423.15 K (1150 C), reported from published hydrazine thruster
  catalyst-bed design monographs; never enforced.

Defining relations (pin these exactly; every function below derives
from them):

- Stoichiometry per mole N2H4 fed at dissociation fraction x
  (fraction of the 4/3 mol NH3 formed by the primary decomposition
  that dissociates): n_NH3 = (4/3)(1 - x), n_N2 = 1/3 + (2/3)x,
  n_H2 = 2x. Total product moles n_tot = 5/3 + (4/3)x (1.6667 at
  x = 0, 3.0 at x = 1, real anchor). Product mass is conserved:
  n_NH3 * 17.03052 + n_N2 * 28.0134 + n_H2 * 2.01588 =
  32.04516 g exactly.
- Net heat release (Hess-law energy balance at T_REF, J per mole
  N2H4): Q(x) = Q_BASE - (4/3) x DELTA_H_DISS_NH3 with
  Q_BASE = -((4/3) DELTA_HF_NH3_GAS - DELTA_HF_N2H4_LIQ)
  = 111883.333333333 J/mol, the exothermic release of N2H4(l) to
  (4/3) NH3 + (1/3) N2. Q is strictly linear and decreasing in x:
  Q(0) = 111883.333333 J/mol, Q(1) = 50630.000000 J/mol, and the
  fully dissociated limit is exactly -DELTA_HF_N2H4_LIQ (the net
  reaction N2H4(l) -> N2 + 2 H2), real anchor.
- Adiabatic decomposition temperature T_c: the root of product
  sensible heat from T_REF to T_c equaling Q(x), where the sensible
  heat is the integral of product_heat_capacity over temperature,
  i.e. per product i, n_i times (a_i (T - T_REF) + (b_i/2)(T^2 -
  T_REF^2) + (c_i/3)(T^3 - T_REF^3)). The left side is strictly
  increasing in T and Q(x) > 0 for all x in [0, 1], so the root on
  [T_REF, T_SOLVE_HI] is unique and the bisection (300 iterations)
  closes it. No closed-form shortcut replaces the solve: the
  quadratic cp fits make the balance cubic in T.
- Mixture gas: mean molar mass M_mix = 32.04516 / n_tot g/mol (also
  kg/kmol), specific gas constant R_mix = 8314.462618 / M_mix
  J/(kg K). Isentropic exponent at T: gamma = cp_mix / (cp_mix -
  R_UNIV) with cp_mix the mole-fraction-weighted cp(T) of the
  frozen product mixture, J/(mol K).
- Vacuum exhaust velocity (frozen-composition isentropic expansion,
  fully expanded, p_e = 0): v_e = sqrt(2 gamma/(gamma - 1) R_mix
  T_c) with gamma evaluated at T_c. Vacuum specific impulse
  Isp = v_e / G0. Vacuum thrust F = mdot * v_e (no pressure term),
  so the propellant mass flow at the thrust point is mdot = F / v_e.
- Catalyst-bed band verdict (advisory, reference-only):
  within the band iff T_c is inside [CATALYST_BED_BAND_LO,
  CATALYST_BED_BAND_HI]; the verdict is a boolean report, never an
  enforced limit.

Functions (public API, 12 functions, all pure, math only):

- decomposition_products(x) -> tuple (n_nh3, n_n2, n_h2), moles of
  NH3, N2, H2 per mole N2H4 fed. ValueError if x is not finite or
  lies outside [0, 1].
- total_product_moles(x) -> float, n_tot = 5/3 + (4/3)x. ValueError
  domain as decomposition_products.
- decomposition_heat_released(x) -> float, J per mole N2H4 fed:
  Q_BASE - (4/3) x DELTA_H_DISS_NH3. ValueError domain as
  decomposition_products.
- product_heat_capacity(x, t_k) -> float, Sigma n_i cp_i(t_k) at
  temperature t_k, J/(K mol N2H4). ValueError domain as
  decomposition_products plus t_k not positive and finite.
- decomposition_temperature(x) -> float, the adiabatic chamber
  temperature T_c in K by bisection on [T_REF, T_SOLVE_HI]
  (300 iterations). ValueError domain as decomposition_products.
- mixture_molar_mass(x) -> float, g/mol = 32.04516 / n_tot.
  ValueError domain as decomposition_products.
- mixture_gas_constant(x) -> float, J/(kg K) = R_UNIV_KMOL /
  mixture_molar_mass(x). ValueError domain as decomposition_products.
- mixture_gamma(x, t_k) -> float, cp_mix / (cp_mix - R_UNIV) at t_k.
  ValueError domain as decomposition_products plus t_k not positive
  and finite.
- vacuum_exhaust_velocity(x) -> float, m/s:
  sqrt(2 gamma/(gamma - 1) R_mix T_c) with T_c =
  decomposition_temperature(x), gamma = mixture_gamma(x, T_c),
  R_mix = mixture_gas_constant(x). ValueError domain as
  decomposition_products.
- vacuum_specific_impulse(x, g0 = G0) -> float, s:
  vacuum_exhaust_velocity(x) / g0. ValueError domain as
  decomposition_products plus g0 not positive and finite.
- propellant_mass_flow(thrust_n, x) -> float, kg/s:
  thrust_n / vacuum_exhaust_velocity(x). ValueError if thrust_n is
  not positive and finite or x out of domain.
- within_catalyst_bed_band(t_k) -> bool, CATALYST_BED_BAND_LO <= t_k
  <= CATALYST_BED_BAND_HI. ValueError if t_k is not finite.

Identities to test (closed form; assert with isclose/abs bounds,
never exact float equality on computed sums):

- Mass closure: the product masses close on 32.04516 g per mole
  N2H4 at x = 0.0, 0.4, 0.6, 1.0 with relative error 2.2e-16 (real
  anchor), proving the internally consistent molar masses.
- Mole-sum identity: n_tot = 5/3 + (4/3)x: 1.666666666666667 at
  x = 0, 2.200000000000000 at x = 0.4, 2.466666666666667 at x = 0.6,
  3.000000000000000 at x = 1.0 (real anchor, differences at or below
  2.2e-16).
- Heat-release linearity: Q(0.6) - Q(0.4) = -12250.666666667 J
  equals -(4/3)(0.2) DELTA_H_DISS_NH3 to 5.5e-12 J (real anchor),
  and Q(1.0) = 50630.000000000 J equals -DELTA_HF_N2H4_LIQ exactly.
- Energy-balance closure: the sensible-heat residual at the solved
  T_c is at or below 3e-11 J at x = 0.0, 0.4, 0.6, 1.0 (real
  anchor).
- Published band reproduction: T_c(0.0) = 1733.5829956423 K (frozen)
  and T_c(1.0) = 864.8245821564 K (fully dissociated), span
  868.758413 K, sit within a few percent of the published
  decomposition-temperature band class (~1700 K frozen to ~900 K
  near-equilibrium, reported reference-only). Monotone in x: T_c and
  Isp_vac fall strictly as x rises across the grid 0.0, 0.25, 0.4,
  0.5, 0.6, 0.75, 1.0 (chamber temperatures 1733.583, 1510.170,
  1377.055, 1288.942, 1201.560, 1072.411, 864.825 K; impulses
  323.093, 299.628, 285.093, 275.328, 265.560, 250.985, 227.095 s,
  real anchor): the endothermic dissociation cools the products, and
  the cooling dominates the lightening of the mixture, so more
  dissociation always lowers Isp in this model.
- Gamma trend: mixture_gamma at the chamber state rises with x, from
  1.175568 (frozen, NH3-rich polyatomic mix) to 1.372593 (fully
  dissociated N2 + 2 H2), real anchor.
- Exhaust identity: vacuum_exhaust_velocity(x) reproduces
  sqrt(2 gamma/(gamma - 1) R_mix T_c) evaluated term by term with
  zero difference at x = 0.4 (real anchor), and
  vacuum_specific_impulse(0.4) = 285.093103776821 s equals
  v_e/G0 exactly.
- Band verdict semantics: within_catalyst_bed_band(T_c(0.4)) and
  (T_c(0.6)) are True (1377.055 K and 1201.560 K inside
  [1073.15, 1423.15] K); within_catalyst_bed_band(T_c(0.0)) is False
  (frozen point above the continuous bed band) and
  within_catalyst_bed_band(T_c(1.0)) is False (fully dissociated
  point below it), real anchor.
- Determinism: decomposition_temperature(0.4) returns
  1377.055452116803281 on every call, bit-identical.
- ValueErrors across the module: x at -0.01, 1.01 and nan; t_k at 0
  and -5 for product_heat_capacity and mixture_gamma; g0 at 0;
  thrust_n at 0 and -5; t_k nan for within_catalyst_bed_band. All
  raise ValueError (real anchor, 12 cases).
- The module never returns blowdown, plenum, choked-throat,
  feed-cycle, pump-power or heating-efficiency outputs, never solves
  an equilibrium, and never enforces a band: the bands are reported
  by the advisory boolean only.

## Worked example

Two reaction-control duty points sized from the anchor: a 5 N RCS
thruster at ammonia-dissociation fraction x = 0.4 and a 22 N RCS
thruster at x = 0.6, the two corpus-query design points. All values
below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_hydrazine_monopropellant_thruster.py
(/usr/bin/python3 3.9.6, stdlib math, closed form plus one
bisection, exit 0; byte-identical output verified under
~/.pyenv/versions/3.13.12/bin/python3).

- 5 N point, x = 0.4 (real anchor): products per mole N2H4 fed are
  0.8 NH3 + 0.6 N2 + 0.8 H2, 2.2 mol total (mole fractions
  0.363636 NH3, 0.272727 N2, 0.363636 H2); net heat release
  Q = 87382.000000 J/mol; mixture molar mass 14.5659818182 g/mol,
  R_mix = 570.81374409 J/(kg K); adiabatic decomposition temperature
  T_c = 1377.0554521168 K; gamma at the chamber state
  = 1.2517566697; vacuum exhaust velocity v_e = 2795.8082861530 m/s;
  vacuum specific impulse Isp = 285.0931037768 s; propellant mass
  flow at 5 N mdot = 5 / 2795.808 = 0.001788391581 kg/s
  (1.78839158 g/s); catalyst-bed band verdict True (1377.055 K
  inside the reported [1073.15, 1423.15] K band).
- 22 N point, x = 0.6 (real anchor): products per mole N2H4 fed are
  0.533333333333 NH3 + 0.733333333333 N2 + 1.2 H2, 2.466666666667
  mol total; Q = 75131.333333 J/mol; mixture molar mass
  12.9912810811 g/mol, R_mix = 640.00328883 J/(kg K);
  T_c = 1201.5600973905 K; gamma = 1.2932811881;
  v_e = 2604.2533178836 m/s; Isp = 265.5599330947 s; mdot at 22 N =
  0.008447718910 kg/s (8.44771891 g/s); band verdict True
  (1201.560 K inside the band).
- Decomposition band endpoints (real anchor): the frozen limit
  x = 0 gives T_c = 1733.5829956423 K with Isp = 323.0932607158 s
  and band verdict False (above the reported continuous bed band);
  the fully dissociated limit x = 1.0 gives
  T_c = 864.8245821564 K with Isp = 227.0953242569 s and verdict
  False (below the band). The computed span 864.8 to 1733.6 K
  brackets the published decomposition-temperature band class of
  roughly 900 to 1700 K, and the fully dissociated ideal vacuum
  impulse 227.1 s sits at the low edge of the published real-engine
  vacuum impulse class of roughly 230 s: both published bands are
  reported reference-only and are never enforced, matching the
  electric-pack band-verdict convention.
- Read-off: the 5 N point needs 1.7884 g/s of hydrazine at an ideal
  vacuum Isp of 285.09 s, the 22 N point 8.4477 g/s at 265.56 s;
  both decomposition temperatures lie inside the reported
  continuous-duty catalyst-bed band, while a frozen-composition
  firing (no ammonia dissociation) would push the bed to 1733.6 K,
  above the reported band, and a fully dissociated firing would run
  it at 864.8 K, below it. The ideal-model impulses sit above the
  published real-engine class of roughly 230 s because real thrusters
  carry nozzle efficiency and finite-expansion losses that this
  leaf's fully expanded ideal vacuum form does not model; the gap is
  the loss account, and the published class stays reference-only.
  The sweep shows the physics trade: pushing the dissociation
  fraction up cools the chamber (heat sunk into NH3 dissociation)
  and lightens the exhaust, but the temperature fall dominates, so
  Isp falls monotonically from 323.09 s (frozen) to 227.10 s (fully
  dissociated).
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w45spec/anchor_hydrazine_monopropellant_thruster.py
(/usr/bin/python3 3.9.6, stdlib math, closed form plus one
bisection, exit 0, byte-identical under
~/.pyenv/versions/3.13.12/bin/python3).

## Validation list (contract test must include)

1. decomposition_products: at x = 0.4 returns (0.8, 0.6, 0.8), at
   x = 0.6 (0.533333333333, 0.733333333333, 1.2), at x = 0.0
   (1.333333333333, 0.333333333333, 0.0) and at x = 1.0 (0.0, 1.0,
   2.0), each within 1e-9 relative.
2. Mass closure: n_NH3 * 17.03052 + n_N2 * 28.0134 + n_H2 * 2.01588
   = 32.04516 within 1e-12 relative at x = 0.0, 0.4, 0.6, 1.0.
3. total_product_moles: 1.666666666667 at x = 0, 2.2 at x = 0.4,
   2.466666666667 at x = 0.6, 3.0 at x = 1.0, each within 1e-12.
4. decomposition_heat_released: 111883.333333 J/mol at x = 0 and
   50630.000000 J/mol at x = 1.0 within 1e-9 relative; Q(0.6) -
   Q(0.4) = -12250.666666667 J within 1e-9 relative of
   -(4/3)(0.2) * 45940.
5. decomposition_temperature: 1377.0554521168 K at x = 0.4 and
   1201.5600973905 K at x = 0.6 within 1e-9 relative; endpoints
   1733.5829956423 K (x = 0) and 864.8245821564 K (x = 1.0) within
   1e-9 relative; the seven-point sweep 0.0/0.25/0.4/0.5/0.6/0.75/
   1.0 gives strictly decreasing chamber temperatures 1733.583,
   1510.170, 1377.055, 1288.942, 1201.560, 1072.411, 864.825 K; the
   sensible-heat residual at each solved T_c is below 1e-9 J.
6. mixture_molar_mass and mixture_gas_constant: 14.5659818182 g/mol
   and 570.81374409 J/(kg K) at x = 0.4; 12.9912810811 g/mol and
   640.00328883 J/(kg K) at x = 0.6, each within 1e-9 relative.
7. mixture_gamma at the chamber state: 1.2517566697 at x = 0.4 and
   1.2932811881 at x = 0.6 within 1e-9 relative; gamma rises with x
   from 1.1755681751 (x = 0) to 1.3725934345 (x = 1.0).
8. vacuum_exhaust_velocity and vacuum_specific_impulse:
   2795.8082861530 m/s and 285.0931037768 s at x = 0.4;
   2604.2533178836 m/s and 265.5599330947 s at x = 0.6, each within
   1e-6 relative; Isp equals v_e / G0 within 1e-12 relative; the
   frozen value 323.0932607158 s exceeds the fully dissociated
   227.0953242569 s.
9. propellant_mass_flow: 0.001788391581 kg/s at (5.0, 0.4) and
   0.008447718910 kg/s at (22.0, 0.6), each within 1e-6 relative;
   mass flow scales linearly with thrust at fixed x.
10. within_catalyst_bed_band: True at T_c(0.4) = 1377.055 K and
    T_c(0.6) = 1201.560 K; False at T_c(0.0) = 1733.583 K (above
    1423.15 K) and T_c(1.0) = 864.825 K (below 1073.15 K); True at
    the closed boundaries 1073.15 K and 1423.15 K.
11. ValueErrors: decomposition_products at x = -0.01, 1.01 and nan;
    decomposition_temperature at x = -0.01 and 1.5;
    product_heat_capacity and mixture_gamma at t_k = 0 and -5;
    vacuum_specific_impulse at g0 = 0; propellant_mass_flow at
    thrust 0 and -5; within_catalyst_bed_band at nan. Every call
    raises ValueError.
12. Determinism: decomposition_temperature(0.4) returns
    1377.055452116803281 bit-identical on repeated calls; no imports
    beyond math; the public API returns no blowdown, plenum,
    choked-throat, feed-cycle, pump-power, heating-efficiency or
    band-enforcement outputs anywhere. Test passes under BOTH
    interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3), verified byte-identical
    at prep. No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (eval/hit1-wave45-hydrazine-monopropellant-thruster.yaml)

Query 1 (copy verbatim):
  "size the hydrazine-monopropellant-thruster for the 5 N spacecraft
  reaction control duty: the catalytic-decomposition chamber
  temperature from the hydrazine-decomposition energy balance at the
  0.4 ammonia-dissociation fraction, then the nozzle exhaust
  velocity and vacuum specific impulse for the decomposed gas
  mixture"
  intent: "propulsion; hydrazine monopropellant RCS sizing, chamber
  temperature from the catalytic-decomposition energy balance at the
  0.4 ammonia-dissociation fraction, then vacuum exhaust velocity
  and specific impulse of the decomposed mixture"
  expected_skill: "propulsion/rocket/hydrazine-monopropellant-thruster"
Query 2 (copy verbatim):
  "run the hydrazine-decomposition energy balance for the
  monopropellant-thruster design point at 22 N: chamber temperature
  and specific impulse at the frozen and the 0.6
  ammonia-dissociation limits, and the catalyst-bed temperature band
  check for the RCS thruster"
  intent: "propulsion; hydrazine decomposition energy balance at 22 N
  with the frozen and 0.6 dissociation-fraction chamber temperatures
  and impulses plus the advisory catalyst-bed temperature band check"
  expected_skill: "propulsion/rocket/hydrazine-monopropellant-thruster"
Task ids: w45-hydrazine-monopropellant-thruster-1 and -2. Prep grep
of eval/hit1-corpus.yaml (real counts from the wave-45 receipt gate
(e)): hydrazine-monopropellant-thruster 0, catalytic-decomposition
0, hydrazine-decomposition 0, ammonia-dissociation 0, catalyst-bed
0. Corpus tasks with hydrazine 0, monopropellant 1 (the
space-systems propellant-tank-sizing task at line 3751, which routes
on tank density and volume), catalyst 0. The nearest router rows
route elsewhere: rocket-engine-cycle rows carry feed-cycle, pump and
turbine tokens; cold-gas-thruster rows carry blowdown, plenum and
choked-mass-flow tokens, which this leaf deliberately avoids; the
propellant-tank-sizing row carries the density example. The queries
above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size and assess a hydrazine
monopropellant thruster for spacecraft reaction control:" and
include the outputs in the Claim. First tag:
hydrazine-monopropellant-thruster. Additional tags ONLY (the receipt
gate (f) list, verbatim):
catalytic-decomposition, ammonia-dissociation-fraction,
monopropellant-rcs, decomposition-temperature. NEVER single generic
words (hydrazine, thruster, monopropellant, catalyst, decomposition,
temperature, chamber, nozzle, thrust, impulse, isp, exhaust,
mixture) and NEVER the cold-gas-thruster tokens blowdown, plenum,
choked-mass-flow, nitrogen-rcs, plenum-blowdown,
isothermal-blowdown-time-constant, total-impulse,
reaction-control-thruster-sizing, and NEVER the
rocket-engine-cycle tokens feed-cycle, gas-generator-cycle,
staged-combustion, expander-cycle, pressure-fed, pump-fed,
pump-power, turbine-power, and NEVER the electrothermal-thruster
tokens resistojet, arcjet, heated-propellant, power-to-thrust,
electric-propulsion, and NEVER propellant-tank-sizing tokens
(tank-volume, ullage, tank-density). 50-150 words, <=1000 chars, no
em dash, action verb present. Recommended wording (117 words, 986
chars, verified): "Use when you must size and assess a hydrazine
monopropellant thruster for spacecraft reaction control: compute the
catalytic decomposition products and net decomposition heat release
of hydrazine at a documented ammonia dissociation fraction, the
adiabatic decomposition temperature from the hydrazine decomposition
energy balance, and the frozen composition isentropic nozzle
expansion of the decomposed gas mixture to the vacuum exhaust
velocity, the vacuum specific impulse and the propellant mass flow
at the required thrust, with the advisory catalyst-bed temperature
band check. Produces the decomposed mixture composition,
decomposition temperature, mixture gas constant, isentropic
exponent, exhaust velocity, vacuum specific impulse, propellant mass
flow and the catalyst-bed band verdict that size a monopropellant
RCS thruster. Trigger: hydrazine-monopropellant-thruster,
catalytic-decomposition, ammonia-dissociation-fraction,
monopropellant-rcs, decomposition-temperature." The sibling-owned
tokens listed above must not appear.

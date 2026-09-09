# Wave-48 leaf spec: fuel-system-weight-estimation (vehicle-design,
# sizing pack)

- Path: skills/vehicle-design/sizing/fuel-system-weight-estimation/
- Pack: sizing (present siblings fuel-tank-sizing (the fuel mass to
  tank volume converter whose tags fuel-mass, fuel-volume, usable-fuel
  and ullage mean the fuel carried, never tank hardware mass),
  fuel-feed-system-sizing (feed line hydraulics and boost pump power),
  fuel-jettison-sizing (dumpable fuel mass and jettison rate),
  fuel-tank-inerting-sizing (ullage washout flow) and
  apu-fuel-burn-sizing (APU fuel flow), the five fuel-family leaves
  that size volume, feed, jettison, inerting and APU burn; engine-sizing
  (the installed engine weight producer W_eng = T_SL / (T/W)_eng that
  owns the engine-weight line), weight-estimation (the class-I /
  class-II weight-and-balance reducer that consumes component weights
  as given inputs), component-weight-estimation (the wave-47 GO whose
  four-airframe-group claim fences this leaf in and whose wing
  regression consumes the in-wing fuel MASS as an input term) and the
  rest of the 41-leaf sizing pack; adjacent fences in
  vehicle-design/mass-properties (mass-budget) and in
  vehicle-design/conceptual (tow-estimation)). Wave-48 probe receipt
  task-4 rank 2 GO; 0 owners verified whole-tree (greps below re-run at
  spec time).
- Claim fences (quoted from the sibling frontmatter and bodies at spec
  time, re-verified at HEAD 3a0931f6; the nearest owners all treat the
  fuel SYSTEM group mass as absent or as a GIVEN input, and each fuel
  sibling produces a volume, a flow, a rate or a burn, never the fuel
  system group mass, which is the exact gap this leaf closes):
  - skills/vehicle-design/sizing/fuel-tank-sizing/SKILL.md lines 25-29:
    "Use when the task is sizing the fuel tanks at the conceptual
    level: converting the fuel mass into a fuel volume with the fuel
    density, adding the ullage allowance to get the required tank
    volume, and checking that volume against the volume available in
    the wing and fuselage tanks." Its metadata tags (line 18) are
    [fuel-tank-sizing, fuel-volume, usable-fuel, ullage, fuel-density,
    tank-capacity, fuel-mass]: fuel MASS in, tank VOLUME out, never
    tank hardware mass.
  - skills/vehicle-design/sizing/fuel-feed-system-sizing/SKILL.md
    frontmatter description (line 3): "Use when you must size the
    aircraft fuel feed system between the tank and the engine: the
    per-engine feed flow from the takeoff fuel flow demand, the feed
    line velocity and Reynolds number, the line pressure loss from the
    Darcy friction factor... and the net positive suction head
    available at the engine-driven pump inlet against the required
    NPSH with the boost pump pressure rise added at cruise altitude.
    Produces the feed flow, the line pressure loss, the NPSH available
    with and without the boost pump, the feed PASS/FAIL verdict, and
    the boost pump hydraulic power..." Hydraulics and power, never a
    fuel system group mass.
  - skills/vehicle-design/sizing/fuel-jettison-sizing/SKILL.md
    frontmatter description (line 3): "Use when you must size the fuel
    jettison system: from the maximum takeoff weight and the maximum
    landing weight, compute the fuel mass that must be dumpable and the
    required average jettison rate to reach the landing weight within
    the 15-minute limit of FAR 25.1001..." Dumpable fuel MASS (the
    fuel itself) and jettison rate, never hardware mass.
  - skills/vehicle-design/sizing/fuel-tank-inerting-sizing/SKILL.md
    frontmatter description (line 3): "model the ullage as a
    well-mixed volume washed by nitrogen-enriched air (NEA)... solve
    the flow that reaches a target oxygen fraction within a required
    time" and skills/vehicle-design/sizing/apu-fuel-burn-sizing/SKILL.md
    frontmatter description (line 3): "compute the APU fuel burn: take
    the generator electrical output and the bleed mass flow at a fixed
    load point... convert that load into fuel flow through the APU
    thermal efficiency and the fuel lower heating value." Washout flow
    and APU fuel flow rate, never a group mass.
  - skills/vehicle-design/sizing/component-weight-estimation/SKILL.md
    lines 25-29: "Use when the task is predicting the four airframe
    structural group masses at the class-II level from geometry and
    design loading: the wing group, the horizontal tail group, the
    vertical tail group and the fuselage group, each from a published
    closed-form statistical regression..." The wave-47 spec claim fence
    (verbatim from ops/automation/state/wave47-specs/
    component-weight-estimation.md lines 151-153): "non-airframe group
    weights (landing gear, installed engines, systems, fuel, fixed
    equipment): the four airframe structural groups are the whole
    claim." The fuel weight group is deliberately OUT of the four-group
    claim, and the wing regression consumes the in-wing fuel MASS as an
    input term (fuel_in_wing_kg, lines 78 and 177-180 of the leaf),
    never a fuel system group mass; this leaf produces that
    weight-statement line.
  - skills/vehicle-design/sizing/engine-sizing/SKILL.md line 64:
    "Engine weight: W_eng = T_SL / (T/W)_eng with the engine thrust to
    weight ratio" (engine-weight tag, corpus esg2). The installed
    engine weight producer is owned, so "installed engines" is NOT an
    open seam; this candidate is scoped to the fuel system group only.
  - skills/vehicle-design/mass-properties/mass-budget/SKILL.md lines
    54-55: "1. Collect the subsystem mass estimates in kg, one entry
    per subsystem." Its rollup, growth allowance and margin policy
    consume given subsystem masses; the fuel system subsystem mass
    would be a given input to it.
  - skills/vehicle-design/sizing/weight-estimation/SKILL.md lines
    25-28: "Use when the task is aircraft weight estimation and weight
    and balance: moments and center of gravity from component weights
    and arms, CG envelope checks, and empty-weight fraction band checks
    for class-I / class-II sizing." Its workflow step 1 (line 43):
    "1. Collect component weights and arms into matching lists."
    Component weights are the INPUT of the only weight-named sizing
    sibling; the build must disambiguate its generic class-ii trigger
    token: class-II fuel system group weight PREDICTION from the total
    fuel weight and the tank arrangement routes to this leaf; class-II
    weight and balance of given component weights stays with
    weight-estimation.
  - skills/vehicle-design/conceptual/tow-estimation/SKILL.md lines
    31-34: "W0 = payload / (1 - empty fraction - fuel fraction)." and
    "Empty and fuel fractions are class-based estimates from similar
    aircraft; the sizing iteration refines them." The class-I fraction
    iteration works on category bands, not on a hardware group
    regression.
  - Zero-owner evidence re-verified at spec time at HEAD (real
    outputs): `grep -rilE "fuel-system-weight|fuel-system-group-weight|
    tank-group-weight-estimation|fuel-system-weight-regression|
    class-ii-fuel-system" skills/ eval/` returns no files (EXIT=1),
    and the corpus token scan of eval/hit1-corpus.yaml for
    fuel-system-weight, fuel-system-group-weight, tank-group-weight,
    fuel-system-weight-regression,
    class-ii-fuel-system-weight-buildup, equipment-weight-estimation
    and systems-weight-estimation returns count 0 (zero of the 1306
    task blocks). No leaf anywhere produces the fuel system group mass;
    the fuel-system-weight tokens have zero owners.
  - Merge-time notes (probe receipt gate (f), carried into this
    contract): add a fence line to fuel-tank-sizing reading "fuel
    system hardware group weight prediction belongs to the
    fuel-system-weight-estimation sibling; this leaf converts the fuel
    mass to volume", add a router row in skills/vehicle-design/SKILL.md
    beside the fuel rows (the fuel-tank-sizing row sits at line 51 at
    spec time), and add 2 corpus tasks at merge with the hyphenated
    tokens below. Family spread: vehicle-design 57 to 58 after the
    rank-1 GO lands, and 58 to 59 when this leaf lands.
- Standards id: far-25 (14 CFR Part 25, reference-only, family
  convention) and cs-25 (CS-25, reference-only), both verified present
  in standards-map.yaml at spec time (grep line 16 for far-25, line 27
  for cs-25; 30 ids total). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Predict the fuel system group mass at the class-II level from the
total fuel weight and the tank arrangement: the hardware mass of the
fuel system (tanks and sealing, pumps, collector tanks and plumbing,
distribution and filling hardware) of a commercial transport with
integral (wet wing) fuel tanks, from a published closed-form
statistical regression on the number of separate fuel tanks, the
number of engines and the fuel weight, the fixed count allowance term
linear in the tank and engine count sum plus the volume-scaled tankage
term raising the tank count to the 0.5 power and the fuel quantity to
the one-third power at the published fuel specific weight, summed into
the fuel system group mass for the weight statement. The method is the
fuel system group weight regression of the fuel system weight
estimation treatment of Roskam, Airplane Design Part V: Component
Weight Estimation (the Torenbeek method for commercial transport
airplanes with integral fuel tanks), paraphrased in this leaf's own
notation (brief 06, summary-only; the books are proprietary-sold);
Torenbeek, Synthesis of Subsonic Airplane Design carries the same
method in its own notation as the cross-check source, and Raymer,
Aircraft Design: A Conceptual Approach treats the fuel system weight
as a function of the fuel volume and the tank count at the same scale.
The public NASA comparison of conceptual design weight methods
(Horvath and Wells) reports the FLOPS and actual Boeing 737-200 fuel
system (tanks and plumbing) weights near 553 lb and 575 lb, about 0.02
of that airplane's fuel weight and about 0.005 of its gross weight,
the class-II magnitude band this leaf's worked example lands in. Every
regression is deterministic stdlib power-law and additive arithmetic
over fixed published constants: no tables beyond the constants, no
vendor catalogs, no numerical integration, no composite material
factors, no bladder-cell variants and no in-flight refuelling or fuel
dumping variants. The fuel weight regressor is the design total fuel
weight, the mission fuel weight including reserves of the source
convention, and the fuel quantity enters the regression as its volume
at the published fuel specific weight constant 6.55 lb per US gallon
(the JP-4 jet-fuel value of the source; modern Jet A sits within about
2 percent of it, and the fixed constant keeps every published
coefficient visible). The worked example below is a 180-seat narrowbody
transport whose fuel system group mass lands at 0.017 of the total fuel
weight and 0.0047 of MTOW, inside the class-II expectation band and
consistent with the systems-group breakdown the mass-budget categories
expect. Inputs and outputs are SI (kg, dimensionless counts); the
regression itself is the published lb / US gallon closed form converted
at the boundary by fixed unit constants, so every published coefficient
stays visible. Produces the fuel system group mass in kg and its
fractions of the total fuel weight and of MTOW that gate the weight
statement. Does NOT do: fuel volume, ullage allowance, required tank
volume or the wing and fuselage tank capacity fit
(vehicle-design/sizing/fuel-tank-sizing); feed line velocity, Reynolds
number, pressure loss, NPSH, boost pump power or feed verdicts
(vehicle-design/sizing/fuel-feed-system-sizing); dumpable fuel mass,
jettison rate, dump mast flow split or the 15-minute landing weight
rule (vehicle-design/sizing/fuel-jettison-sizing); inerting washout
flow or ullage oxygen decay (vehicle-design/sizing/
fuel-tank-inerting-sizing); APU generator or bleed fuel burn
(vehicle-design/sizing/apu-fuel-burn-sizing); the installed engine
weight producer W_eng = T_SL / (T/W)_eng and every propulsion sizing
output (vehicle-design/sizing/engine-sizing); the four airframe
structural group masses, the wing group, the horizontal tail group,
the vertical tail group and the fuselage group, and every other group
weight of the weight statement (vehicle-design/sizing/
component-weight-estimation); moments, center of gravity, envelope
limits or empty-weight fraction band checks of given component weights
(vehicle-design/sizing/weight-estimation); the subsystem mass rollup,
growth allowance, contingency margin or MTOW target check
(vehicle-design/mass-properties/mass-budget); the class-I takeoff
weight fraction iteration on category bands
(vehicle-design/conceptual/tow-estimation); cg stations, envelope
polygons, static margin, moments of inertia or radii of gyration
(vehicle-design/mass-properties/cg-envelope and inertia-estimation);
MDO coupling loops or optimization over the weight statement
(vehicle-design/mdo/multidisciplinary-optimization). The fuel chain
leaves own volume, feed hydraulics, jettison, inerting and APU burn,
and the fuel system group mass everywhere else is a given input, never
derived; this leaf is the missing producer of the fuel system line of
the weight statement.

## Model (implement exactly)

Pure stdlib, closed form, deterministic, no RNG. The regression is
pure power-law and additive arithmetic, so no imports are required.
The public functions take SI (kg, dimensionless counts) and return kg;
the regression runs in the published lb / US gallon closed form.

Module constants (fixed, no others):
- Unit conversions: KG_TO_LB = 1.0 / 0.45359237; LB_TO_KG =
  0.45359237.
- FUEL_SYSTEM_COUNT_K = 80.0 (lb per (N_t + N_e - 1) count unit of
  the fixed count allowance term).
- FUEL_SYSTEM_VOLUME_K = 15.0 (lb per (N_t)^0.5 (V)^(1/3) unit of the
  volume-scaled tankage term).
- FUEL_SYSTEM_E_NT = 0.5 (tank count exponent in the volume term).
- FUEL_SYSTEM_E_V = 1.0 / 3.0 (fuel volume exponent; the published
  form prints 0.333).
- FUEL_SPECIFIC_WEIGHT = 6.55 (lb per US gallon, the published JP-4
  jet-fuel value of the source; the aviation gasoline value 5.87 is
  outside the claim).
Every fixed number in the model is one of the constants above; the
boundary conversions multiply or divide once per input or output and
introduce no other numbers.

Defining relations (pin these exactly; every function derives from
them; N_t is the number of separate fuel tanks, N_e the number of
engines, W_F the total fuel weight in lb and V = W_F / 6.55 the fuel
quantity in US gallons):
- Fixed count allowance term: W_a = 80 * (N_t + N_e - 1). Fuel
  independent; linear in the tank and engine counts.
- Volume-scaled tankage term: W_v = 15 * (N_t)^0.5 * V^(1/3). Sublinear
  in both the tank count (exponent 0.5) and the fuel quantity
  (exponent 1/3, so the effective fuel weight exponent of the term is
  one-third).
- Fuel system group: W_fs = W_a + W_v, the sum of the two published
  terms of the source equation.
- The group total scales strictly sublinearly in the fuel weight: the
  allowance is fuel independent and the tankage term carries the
  one-third exponent, so the fuel system group fraction of the fuel
  weight falls as the fuel weight grows (at the worked parameters,
  doubling the fuel weight scales the group by 1.159273519641, below
  2^(1/3) = 1.259921049895, and the fraction falls from 0.017038500 to
  0.009876141), which is the scale behavior the class-I band checks of
  the weight-estimation sibling bracket.
- Units: inputs are SI (kg, dimensionless counts), outputs kg. Every
  fixed number in the model is one of the module constants above.

Functions:
- fuel_system_count_allowance_kg(n_tanks, n_engines) -> float
  Fixed count allowance term in kg. Raises ValueError for a non-number,
  sub-1 or fractional tank or engine count.
- fuel_system_volume_term_kg(total_fuel_kg, n_tanks) -> float
  Volume-scaled tankage term in kg. Raises ValueError for a
  non-positive total fuel weight, and for a non-number, sub-1 or
  fractional tank count.
- fuel_system_group_weight(total_fuel_kg, n_tanks, n_engines) -> float
  Fuel system group mass in kg, the sum of the two terms. Raises
  ValueError for a non-positive total fuel weight, for a non-number,
  sub-1 or fractional tank or engine count, and when the tank count is
  below the engine count (the integral-tank transport arrangement of
  the source feeds every engine from its own tank group, so N_t must
  be at least N_e; a tank count below the engine count is outside the
  arrangement).

Identities to test (closed form, checkable without the builder module):
- Physical-sanity bands: at the worked parameters the fuel system group
  mass is 0.017038500 of the total fuel weight and 0.004744899 of the
  MTOW, inside the class-II expectation band (the FLOPS and actual
  Boeing 737-200 tanks-and-plumbing weights of the NASA weight-methods
  comparison sit near 0.02 of the fuel weight and near 0.005 of gross
  weight), and the MTOW fraction sits strictly below the class-I empty
  weight implied by the weight-estimation sibling's transport band
  lower bound (0.004744899 below 0.42), so the fuel system group alone
  never approaches the empty weight of the transport class.
- Exact power laws: the volume term doubles as exactly 2^(1/3) when
  the total fuel weight doubles with all else fixed, and as exactly
  2^0.5 when the tank count doubles with all else fixed. The count
  allowance is exactly additive: one extra tank at fixed engines and
  one extra engine at fixed tanks each add exactly 80 lb =
  36.287389600 kg, and the allowance is fuel independent.
- Group additivity: the group mass equals the count allowance plus the
  volume term exactly (the two published terms of the source
  equation).
- Sublinear scaling: doubling the fuel weight scales the group by
  1.159273519641, below 2^(1/3) = 1.259921049895, and the fuel system
  fraction of the fuel weight falls from 0.017038500 to 0.009876141.
- Monotonicity: the group mass increases strictly with the total fuel
  weight (the volume term exponent is positive) and with the tank
  count (both terms increase with N_t).
- ValueErrors across the module as enumerated in the Worked example.
- Determinism: identical outputs run to run and under both
  interpreters; no randomness; no imports; the constants fixed as
  above.

## Worked example

180-seat narrowbody transport, all inputs SI:
- Total fuel weight 22000.0 kg (the design total fuel weight, mission
  fuel including reserves per the source convention), MTOW 79000.0 kg
  for the weight-statement fractions.
- Tank arrangement: 3 separate integral fuel tanks (left wing, right
  wing and center wing), 2 engines.
- Fuel quantity at the published specific weight: 7404.839341 US
  gallons.

All values below are REAL outputs of the prep anchor
/tmp/w48spec/anchor_fuel_system_weight.py (pure stdlib, closed-form
power-law and additive arithmetic, no imports, exit 0, no RNG,
byte-identical output under both interpreters), run once and quoted as
printed:

- Group terms (module output): fuel_system_count_allowance_kg (3, 2)
  gives 145.149558400 kg (the 320 lb allowance at 4 count units),
  fuel_system_volume_term_kg (22000.0, 3) gives 229.697449925 kg, and
  fuel_system_group_weight (22000.0, 3, 2) gives 374.847008325 kg, the
  exact sum of the two terms (residual 2.842e-14 kg). As fractions:
  0.017038500 of the 22000.0 kg total fuel weight, 0.004744899 of the
  79000.0 kg MTOW. The group mass sits inside the class-II band: the
  FLOPS and actual Boeing 737-200 tanks-and-plumbing fuel system
  weights of the NASA weight-methods comparison (553 lb and 575 lb)
  sit near 0.02 of the fuel weight and near 0.005 of gross weight, and
  the worked group fraction of MTOW is far below the class-I transport
  empty-weight band lower bound of 0.42 that the weight-estimation
  sibling checks.
- Fuel volume power law (identity, module output): recomputing
  fuel_system_volume_term_kg at 44000.0 kg gives 289.400652267 kg, a
  ratio of 1.259921049895 against its value at 22000.0 kg, matching
  2^(1/3) = 1.259921049895.
- Tank count power law (identity, module output): recomputing
  fuel_system_volume_term_kg with 6 tanks at the same fuel gives
  324.841248926 kg, a ratio of 1.414213562373 against the 3 tank
  value, matching 2^0.5 = 1.414213562373.
- Count allowance additivity (identity, module output): one extra tank
  at 2 engines adds 36.287389600 kg and one extra engine at 3 tanks
  adds 36.287389600 kg, each exactly the 80.0 lb = 36.287389600 kg
  allowance unit.
- Sublinear fuel scaling (identity, module output):
  fuel_system_group_weight at 44000.0 kg gives 434.550210667 kg, a
  ratio of 1.159273519641 against the 22000.0 kg value, below 2^(1/3)
  = 1.259921049895, and the fuel system fraction of the fuel weight
  falls from 0.017038500 at 22000.0 kg to 0.009876141 at 44000.0 kg.
- Monotonicity (module output): the group at 1.01 times the fuel
  (22220.0 kg) gives 375.610128382 kg and the group at 4 tanks gives
  446.668717092 kg, both strictly above the worked 374.847008325 kg.
- ValueErrors with real messages (module output, quoted as printed): a
  total fuel weight of 0.0 raises "total fuel weight must be positive,
  got 0.0"; a negative fuel weight raises "total fuel weight must be
  positive, got -1.0"; a non-number fuel weight raises "total fuel
  weight must be a number, got 'a'"; a tank count of 0 raises "number
  of separate fuel tanks must be at least 1, got 0"; a tank count of
  2.5 raises "number of separate fuel tanks must be a whole number,
  got 2.5"; an engine count of 0 raises "number of engines must be at
  least 1, got 0"; one tank feeding two engines raises "number of
  separate fuel tanks must be at least the number of engines, got
  tanks 1 and engines 2"; an engine count of 1.5 raises "number of
  engines must be a whole number, got 1.5" from
  fuel_system_count_allowance_kg.
- Determinism: two consecutive runs return identical values; the anchor
  exits 0 and its internal asserts (positive masses, magnitude bands,
  every exact-power identity within 1e-9 relative, the exact count
  allowance additivity within 1e-9, the group additivity within 1e-9,
  monotonicity, the sublinear fraction fall, byte-identical output
  under both interpreters) all pass.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w48spec/anchor_fuel_system_weight.py (stdlib, closed form, exit
0, no randomness, identical under both interpreters).

## Validation list (contract test must include)

1. Worked example asserts within 1e-6 relative:
   fuel_system_count_allowance_kg (3, 2) = 145.149558400 kg,
   fuel_system_volume_term_kg (22000.0, 3) = 229.697449925 kg and
   fuel_system_group_weight (22000.0, 3, 2) = 374.847008325 kg; the
   group fractions of the 22000.0 kg total fuel weight are 0.017038500,
   and of the 79000.0 kg MTOW 0.004744899.
2. Physical-sanity bands: the group mass is positive and below the
   total fuel weight and the MTOW; the fuel system fraction of the
   total fuel weight lies in [0.010, 0.025] and of the MTOW in [0.003,
   0.010]; the MTOW fraction 0.004744899 lies below the class-I
   transport empty-weight fraction band lower bound 0.42 (the
   weight-estimation sibling's band), the fuel system group sanity
   identity.
3. Fuel volume power law within 1e-9 relative:
   fuel_system_volume_term_kg recomputed at 44000.0 kg divides by its
   value at 22000.0 kg to give 2^(1/3) = 1.259921049895.
4. Tank count power law within 1e-9 relative: the volume term at 6
   tanks divides by its value at 3 tanks to give 2^0.5 =
   1.414213562373 at fixed fuel.
5. Count allowance additivity within 1e-9 relative: one extra tank at
   fixed engines and one extra engine at fixed tanks each add exactly
   36.287389600 kg (80 lb), and the allowance is unchanged when only
   the fuel weight changes.
6. Group additivity: the group mass equals the count allowance plus
   the volume term within 1e-12 relative (the two published terms of
   the source equation).
7. Sublinear fuel scaling: the group ratio at doubled fuel weight is
   1.159273519641, below 2^(1/3) = 1.259921049895, and the fuel system
   fraction of the fuel weight falls from 0.017038500 at 22000.0 kg to
   0.009876141 at 44000.0 kg.
8. Monotonicity: a 1 percent higher total fuel weight (22220.0 kg)
   strictly raises the group mass to 375.610128382 kg and one more
   tank (4 tanks) strictly raises it to 446.668717092 kg.
9. All ValueErrors enumerated in the Worked example raise from the
   named public function with the real messages quoted there: zero,
   negative and non-number total fuel weight; tank and engine counts
   below 1; fractional tank and engine counts (2.5 tanks, 1.5
   engines); a tank count below the engine count (1 tank, 2 engines).
10. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports; module constants
    exactly as pinned in the Model section. No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.
11. The prep anchor runs offline and exits 0 with every internal assert
    passing (positive masses, magnitude bands, the exact-power
    identities within 1e-9 relative, the count allowance additivity,
    monotonicity, the sublinear fraction fall).
12. Run the deterministic contract test offline (no network); it exits
    0. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave48-fuel-system-weight-estimation.yaml)

Query 1 (copy verbatim):
  "estimate the fuel-system-group-weight for the weight statement
  with the statistical fuel system weight regression from the total
  fuel weight and roll the fuel-system-group-weight into the mass
  budget"
  expected_skill: "vehicle-design/sizing/fuel-system-weight-estimation"
Query 2 (copy verbatim):
  "run the fuel-system-weight-estimation at class II: compute the
  fuel-system-group-weight with the
  class-ii-fuel-system-weight-buildup regression from the total fuel
  weight for the tank and plumbing group mass"
  expected_skill: "vehicle-design/sizing/fuel-system-weight-estimation"
Task ids: w48-fuel-system-weight-estimation-1 and -2. The two query
texts are the receipt gate (e) queries verbatim (wave-48 probe receipt,
task-4), sim-verified by replicating the scripts/router_eval.py token
router EXACTLY over the real index plus BOTH hypothetical candidates
(margins include cross-candidate competition): query 1 HIT1 16.0 with
runner-up component-weight-estimation 9.0 (margin 7.0), query 2 HIT1
25.0 with runner-up component-weight-estimation 9.5 (margin 15.5),
zero theft over all 1306 corpus tasks. Prep grep (run at spec time):
each of the tokens fuel-system-weight-estimation,
fuel-system-group-weight, fuel-system-weight-regression,
class-ii-fuel-system-weight-buildup and tank-group-weight-estimation
returns ZERO matches in every skills/ SKILL.md and in eval/
hit1-corpus.yaml (grep exit 1), and the corpus scans for
equipment-weight-estimation and systems-weight-estimation count 0, so
the queries are collision-free; the fuel corpus tasks route on
fuel-volume, ullage, NPSH, feed-line, jettison-rate, inerting and APU
tokens, none of which carries fuel-system-group-weight content. Add
one fence line to fuel-tank-sizing reading "fuel system hardware group
weight prediction belongs to the fuel-system-weight-estimation
sibling; this leaf converts the fuel mass to volume" and one router
row to skills/vehicle-design/SKILL.md at build time beside the fuel
rows pointing class-II fuel system group weight prediction to the new
leaf (the landing-gear-height-sizing precedent). Family spread:
vehicle-design 57 to 58 after the rank-1 GO lands, and 58 to 59 when
this leaf lands.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must predict the fuel system group
weight at the class-II level for the weight statement:" and include
the outputs in the Claim order (the fuel system group mass from the
statistical regression on the total fuel weight and the tank
arrangement, and its fraction of the total fuel weight), then close
with the Trigger list. Refer to the outputs as the fuel system group
mass or group weight, never as the bare single words fuel, weight,
mass, tank, system, estimation or group; never claim fuel volume,
tank capacity, feed flow, jettison rate, inerting washout, APU burn or
installed engine weight outputs; never reproduce the anchor book text
(reference-only, paraphrase). First tag: fuel-system-weight-estimation.
Metadata tags EXACTLY as the probe receipt gate (f) lists them,
nothing else: fuel-system-group-weight,
fuel-system-weight-regression, class-ii-fuel-system-weight-buildup,
tank-group-weight-estimation. 50-150 words, <=1000 chars, no em dash,
action verb present. Recommended wording (147 words, 879 chars,
verified at spec time):

"Use when you must predict the fuel system group weight at the
class-II level for the weight statement: evaluate the statistical fuel
system weight regression of the transport integral-tank fuel system on
the total fuel weight and the tank arrangement, the fixed 80 lb count
allowance per tank and engine unit plus the 15 lb volume term scaling
with the square root of the tank count and the cube root of the fuel
quantity at the published fuel specific weight, and sum the terms into
the fuel system group mass. Produces the fuel system group mass in kg
for the tanks, sealing, pumps, plumbing and distribution hardware, and
its fraction of the total fuel weight for the weight statement and the
mass budget rollup. Trigger: fuel system weight estimation, fuel
system group weight, fuel system weight regression, class ii fuel
system weight buildup, tank group weight estimation."

FORBIDDEN TOKENS (belong to siblings): fuel volume, ullage allowance,
required tank volume, tank capacity, usable fuel, fuel density,
wing and fuselage tank fits (fuel-tank-sizing); feed line velocity,
Reynolds number, Darcy friction factor, feed line pressure loss,
engine feed NPSH, boost pump, feed flow, fuel pump power
(fuel-feed-system-sizing); jettison rate, fuel dump rate, time to
landing weight, 15-minute rule, dump mast (fuel-jettison-sizing);
OBIGGS, nitrogen enriched air, ullage oxygen washout, NEA generator
(fuel-tank-inerting-sizing); APU fuel burn, generator shaft power,
bleed pumping power, APU fuel flow rate (apu-fuel-burn-sizing);
installed engine weight, engine thrust to weight ratio, sea level
static thrust, thrust lapse (engine-sizing); wing group, horizontal
tail group, vertical tail group, fuselage group, airframe group total
and any other group weight of the weight statement
(component-weight-estimation); moments, center of gravity, weight and
balance, envelope limit, empty weight fraction band, static margin
(weight-estimation); mass rollup, growth allowance, contingency
margin, mtow target check (mass-budget); takeoff gross weight, fuel
fraction method, sizing iteration (tow-estimation); cg station,
moment of inertia, radius of gyration (cg-envelope,
inertia-estimation); multidisciplinary optimization, coupling
variables (multidisciplinary-optimization). Never the bare words fuel,
weight, mass, tank, system, pump, estimation or sizing as standalone
metadata tags (fuel-tank-sizing, fuel-feed-system-sizing and
weight-estimation own the generic surface), and never claim that the
fuel system group mass is a fuel volume, a tank capacity, a feed rate,
a jettison rate, an installed engine weight, an empty weight, a total
aircraft mass or any four-airframe-group weight of the
component-weight-estimation sibling.

# Wave-47 leaf spec: component-weight-estimation (vehicle-design,
# sizing pack)

- Path: skills/vehicle-design/sizing/component-weight-estimation/
- Pack: sizing (present siblings weight-estimation (the class-I /
  class-II weight-and-balance reducer that consumes component weights
  as given inputs), fuselage-sizing, tail-sizing, wing-planform-sizing
  (the geometry producers this leaf consumes), fuel-tank-sizing (the
  in-wing fuel mass source for the wing regression), engine-sizing,
  landing-gear-sizing and the rest of the 40-leaf sizing pack; adjacent
  fences in vehicle-design/mass-properties (mass-budget, cg-envelope,
  inertia-estimation), in vehicle-design/conceptual (tow-estimation)
  and in vehicle-design/structures-integration (wing-box-sizing,
  fuselage-skin-stringer)). Wave-47 probe receipt task-4 rank 1 GO; 0
  owners verified whole-tree (greps below re-run at spec time).
- Claim fences (quoted from the sibling frontmatter and bodies at spec
  time, re-verified at HEAD 2fa029ea; the nearest owners all treat
  component weights as GIVEN inputs, and none derives an airframe
  group weight from geometry, which is the exact gap this leaf closes):
  - skills/vehicle-design/sizing/weight-estimation/SKILL.md lines
    25-28: "Use when the task is aircraft weight estimation and weight
    and balance: moments and center of gravity from component weights
    and arms, CG envelope checks, and empty-weight fraction band
    checks for class-I / class-II sizing." Its workflow step 1 (line
    43): "Collect component weights and arms into matching lists."
    Component weights are the INPUT of the only weight-named sibling;
    its functional scope is moments, CG, envelope and empty-weight
    fraction band checks (its bands, lines 35-37: "transport
    0.42-0.55, general-aviation 0.55-0.68, turboprop 0.50-0.62").
    The build must disambiguate its generic class-ii trigger token:
    class-II group-weight PREDICTION from geometry routes to this
    leaf; class-II weight and balance of given component weights stays
    with weight-estimation.
  - skills/vehicle-design/mass-properties/mass-budget/SKILL.md lines
    25-29: "Use when the task is building the vehicle mass budget at
    the conceptual level: allocating subsystem masses, applying the
    growth allowance and contingency margin policy, rolling up the
    estimated total mass, and checking the margin-backed total against
    the MTOW target." Its workflow step 1 (lines 54-55): "Collect the
    subsystem mass estimates in kg, one entry per subsystem." Its
    quick reference (lines 33-34) names the breakdown categories
    "(wing, fuselage, empennage, systems, payload, and so on)" but the
    rollup, growth allowance and margin policy consume given subsystem
    masses; no line derives the wing or fuselage entry.
  - skills/vehicle-design/conceptual/tow-estimation/SKILL.md lines
    31-34: "Empty and fuel fractions are class-based estimates from
    similar aircraft; the sizing iteration refines them." and line 32
    "W0 = payload / (1 - empty fraction - fuel fraction)." Its
    workflow step 1 (line 41): "Collect payload and class-based empty
    and fuel fractions." The class-I fraction iteration works on
    category bands, not geometry-driven group weights; total aircraft
    sizing and the takeoff weight loop stay with tow-estimation.
  - skills/vehicle-design/mass-properties/cg-envelope/SKILL.md lines
    32-34: "Center of gravity: x_cg = sum(w_i * x_i) / sum(w_i) over
    the components; the same rule applies to the z stations for the
    vertical cg." and step 1 (lines 54-56): "Collect component weights
    and stations: x arms for the longitudinal cg, z stations when the
    vertical cg matters." Weights are inputs to the station sum.
  - skills/vehicle-design/mass-properties/inertia-estimation/SKILL.md
    lines 31 and 40-41: "Moment of inertia from the radius of
    gyration: I = m * k^2." and step 1: "Collect component masses and
    radii of gyration." Masses are inputs.
  - skills/vehicle-design/mdo/multidisciplinary-optimization/SKILL.md
    lines 91-93 (pitfall): "Confusing MDO with the mass-budget:
    mass-budget allocates the weight statement; MDO consumes the mass
    estimate as a discipline output and couples it to the structural
    and aerodynamic responses." MDO explicitly fences mass PRODUCTION
    out.
  - skills/vehicle-design/structures-integration/wing-box-sizing/
    SKILL.md lines 31-49: sizes the box-beam members from closed
    forms, root bending moment "M = (2/(3*pi)) * n * W * b",
    "FAR-25.303 context: the factor of safety between limit and
    ultimate loads is 1.5", "Spar cap area from the box-beam bending
    relation M = sigma * A * h: A = M / (sigma * h)" and "Spar web
    shear flow: q = V / (n_webs * h), and web thickness t = q / tau".
    It takes the design weight W as input and yields member areas and
    thicknesses, never a wing-group mass; skin, rib and non-optimum
    structure weight is outside its scope.
  - Zero-owner evidence re-verified at spec time at HEAD (real
    outputs): `grep -rilE "component-weight|wing-group-weight|
    fuselage-group-weight|statistical-group-weight|class-ii-weight"
    skills/ eval/` returns no files (EXIT=1), and the corpus token
    scan of eval/hit1-corpus.yaml for component-weight,
    group-weight-equation, wing-group-weight and statistical-weight
    returns count 0 (zero of the 1286 task blocks). No leaf anywhere
    derives airframe group weights from geometry; the class-II
    regression tokens have zero owners.
  - Merge-time notes (probe receipt gate (f), carried into this
    contract): add a fence line to weight-estimation reading
    "statistical group-weight prediction from geometry belongs to the
    component-weight-estimation sibling", add a router row in
    skills/vehicle-design/SKILL.md beside the weight-estimation row,
    and add 2 corpus tasks at merge with the hyphenated tokens below.
    Family spread: vehicle-design 56 to 57 after landing.
- Standards id: far-25 (14 CFR Part 25, reference-only, family
  convention) and cs-25 (CS-25, reference-only), both verified present
  in standards-map.yaml at spec time (grep line 16 for far-25, line 27
  for cs-25; 30 ids total). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Predict the four airframe structural group masses at the class-II
level from geometry and design loading: the wing group, the horizontal
tail group, the vertical tail group and the fuselage group, each from
a published closed-form statistical regression on its planform or body
dimensions, sweep, thickness ratio, dynamic pressure, design load
factor and design gross weight, with the four group masses summed into
an airframe group total for the weight statement. The method is the
class-II statistical group-weight prediction approach of the weight
estimation chapter of Raymer, Aircraft Design: A Conceptual Approach,
paraphrased in this leaf's own notation (brief 06, summary-only; the
books are proprietary-sold); Torenbeek, Synthesis of Subsonic Airplane
Design is the cross-check source, and the Gudmundsson and Sadraey
treatments of the same method sit in the book family the siblings
already paraphrase. Every regression is deterministic stdlib
arithmetic over fixed published constants: no tables beyond the
constants, no numeric integration, no vendor data, no composite
material factors, no non-airframe groups. The design load factor
enters every regression as the ULTIMATE value, the design limit
maneuvering load factor times the 1.5 factor of safety (the FAR-25.303
convention the wing-box-sizing sibling already applies between limit
and ultimate), and the design gross weight is the MTOW. The fuselage
group carries an additive cabin pressurization penalty when a
pressurized volume and a pressure differential are both supplied; the
published regressions apply to metal structure and the worked example
below is a 180-seat narrowbody transport whose four group masses land
in the established class-II fraction bands of MTOW and reconcile
against the class-I empty-weight band the weight-estimation sibling
checks. Inputs and outputs are SI (kg, m, m^2, Pa, deg, kg out); the
regressions themselves are the published lb / ft^2 / psf closed forms
converted at the boundary by fixed unit constants, so every published
coefficient stays visible. Produces the four group masses in kg, the
airframe group total in kg, and the per-group and total fractions of
MTOW that gate the weight statement. Does NOT do: the moments, CG,
forward and aft limit envelope checks and empty-weight fraction band
checks of given component weights, and the class-I / class-II
weight-and-balance reduction (vehicle-design/sizing/weight-estimation);
the mass rollup, growth allowance, contingency margin and MTOW target
check of given subsystem masses (vehicle-design/mass-properties/
mass-budget); the class-I fuel-fraction takeoff gross weight iteration
on category bands and its convergence verdict (vehicle-design/
conceptual/tow-estimation); cg stations, envelope polygon, static
margin or fuel-burn cg excursion (vehicle-design/mass-properties/
cg-envelope); moments of inertia, radii of gyration or parallel axis
transfers (vehicle-design/mass-properties/inertia-estimation);
structural member sizing, spar cap areas, web thicknesses, skin and
stringer sizing or root bending moments (vehicle-design/
structures-integration/wing-box-sizing and fuselage-skin-stringer);
MDO coupling loops or optimization over the weight statement
(vehicle-design/mdo/multidisciplinary-optimization); and non-airframe
group weights (landing gear, installed engines, systems, fuel, fixed
equipment): the four airframe structural groups are the whole claim.
Component weights and masses elsewhere are always given inputs,
never derived; this leaf is the producer side of the weight chain.

## Model (implement exactly)

Pure stdlib, math only (math.cos, math.radians), closed form,
deterministic, no RNG. The public functions take SI and return kg; the
regressions run in the published lb / ft^2 / psf units.

Module constants (fixed, no others):
- Unit conversions: KG_TO_LB = 1.0 / 0.45359237; M_TO_FT =
  1.0 / 0.3048; M2_TO_FT2 = M_TO_FT ** 2; M3_TO_FT3 = M_TO_FT ** 3;
  PA_TO_PSF = 1.0 / 47.88025898033584; PA_TO_PSI =
  1.0 / 6894.757293168361.
- ULTIMATE_OVER_LIMIT = 1.5 (FAR-25.303 factor of safety between the
  design limit maneuvering load factor and the ultimate value used in
  the regressions).
- Wing group (lb): WING_K = 0.036, WING_E_S = 0.758, WING_E_FW =
  0.0035, WING_E_A = 0.6, WING_E_Q = 0.006, WING_E_LAM = 0.04,
  WING_E_TC = -0.3, WING_E_NW = 0.49.
- Horizontal tail group (lb): HT_K = 0.016, HT_E_NW = 0.414, HT_E_A =
  0.168, HT_E_Q = 0.043, HT_E_S = 0.896, HT_E_TC = -0.12, HT_E_LAM =
  0.02.
- Vertical tail group (lb): VT_K = 0.073, VT_H_FACTOR = 0.2, VT_E_NW =
  0.376, VT_E_Q = 0.122, VT_E_S = 0.873, VT_E_TC = -0.49, VT_E_A =
  0.357, VT_E_LAM = 0.039.
- Fuselage group (lb): FUS_K = 0.052, FUS_E_SF = 1.086, FUS_E_NW =
  0.177, FUS_E_LD = -0.072, FUS_E_Q = 0.241; pressurization penalty
  FUS_PRESS_K = 11.9, FUS_E_PRESS = 0.271.
- The source table's additional small tail-arm decorrelation factor on
  the fuselage regression (published exponent magnitude 0.051, printed
  argument scattered across editions) is OMITTED by this leaf as below
  class-II resolution; every other factor of the published form is
  implemented. This deviation is recorded here for the builder; it
  changes the worked fuselage mass by under 1 percent.

Defining relations (pin these exactly; every function derives from
them; W0 is the MTOW in lb, N_ult = 1.5 * nz_limit the ultimate load
factor, S the reference area in ft^2, A the aspect ratio, lam the
taper ratio, tc the thickness to chord ratio, L the sweep angle at
quarter chord in radians, q the cruise dynamic pressure in psf):
- Wing group: W_w = 0.036 * S_w^0.758 * W_fw^0.0035 *
  (A_w / cos^2 L_w)^0.6 * q^0.006 * lam_w^0.04 *
  (100 * tc_w / cos L_w)^-0.3 * (N_ult * W0)^0.49, with W_fw the fuel
  weight carried in the wing in lb (the regression requires a positive
  in-wing fuel mass; a fuel-less wing is outside its domain).
- Horizontal tail group: W_ht = 0.016 * (N_ult * W0)^0.414 *
  (A_ht / cos^2 L_ht)^0.168 * q^0.043 * S_ht^0.896 *
  (100 * tc_ht / cos L_ht)^-0.12 * lam_ht^0.02.
- Vertical tail group: W_vt = 0.073 * (1 + 0.2 * H_t) * (N_ult * W0)^
  0.376 * q^0.122 * S_vt^0.873 * (100 * tc_vt / cos L_vt)^-0.49 *
  A_vt^0.357 * (lam_vt / cos^2 L_vt)^0.039, with H_t the T-tail
  location factor: 0.0 for a fuselage-mounted tail, 1.0 for a T-tail
  (any non-negative float is accepted as the fraction); the factor is
  LINEAR in H_t, so the T-tail variant is exactly 1.2 times the
  conventional variant.
- Fuselage group: W_fus = 0.052 * S_f^1.086 * (N_ult * W0)^0.177 *
  (L_f / D_f)^-0.072 * q^0.241, with S_f the fuselage wetted area in
  ft^2, L_f the fuselage length and D_f the equivalent fuselage
  diameter ((width + height) / 2); plus the additive pressurization
  penalty W_press = 11.9 * (V_p * dp)^0.271 with V_p the pressurized
  volume in ft^3 and dp the cabin pressure differential in psi,
  active only when both are supplied.
- The group total: the sum of the four group masses; every group mass
  is a fraction of MTOW, and the regressions are sublinear in W0 (all
  (N_ult * W0) exponents below 0.5), so the four-group total scales
  slower than MTOW: the class-II structural share falls as the design
  grows, which is what the class-I empty-weight fraction bands of the
  weight-estimation sibling encode.
- Units: inputs are SI, outputs kg. Every fixed number in the model is
  one of the module constants above; the boundary conversions multiply
  or divide once per input or output and introduce no other numbers.

Functions:
- wing_group_weight(mtow_kg, nz_limit, q_pa, s_m2, ar, taper, tc,
  sweep_deg, fuel_in_wing_kg) -> float
  Wing group mass in kg. Raises ValueError for a non-positive MTOW,
  limit load factor, dynamic pressure, planform area, aspect ratio,
  taper ratio, thickness to chord, sweep angle or in-wing fuel mass,
  for a thickness ratio at or above 1.0, and for a sweep angle at or
  above 90 degrees.
- horizontal_tail_group_weight(mtow_kg, nz_limit, q_pa, s_m2, ar,
  taper, tc, sweep_deg) -> float
  Horizontal tail group mass in kg. Same ValueErrors.
- vertical_tail_group_weight(mtow_kg, nz_limit, q_pa, s_m2, ar,
  taper, tc, sweep_deg, t_tail=0.0) -> float
  Vertical tail group mass in kg; t_tail is the T-tail location
  factor, non-negative, default 0.0. Same ValueErrors plus a negative
  t_tail.
- fuselage_group_weight(mtow_kg, nz_limit, q_pa, wetted_area_m2,
  length_m, diameter_m, press_volume_m3=0.0, delta_p_pa=0.0) -> float
  Fuselage group mass in kg including the additive pressurization
  penalty when both press_volume_m3 and delta_p_pa are positive.
  Raises ValueError for a non-positive MTOW, limit load factor,
  dynamic pressure, wetted area, length or diameter, and when exactly
  one of the two pressurization parameters is positive (both or
  neither must be given).
- airframe_group_total(w_wing, w_ht, w_vt, w_fus) -> float
  Sum of the four group masses in kg. Raises ValueError for a
  non-number or negative group mass.

Identities to test (closed form, exact where noted; checkable without
the builder module):
- Physical-sanity bands: at the worked parameters the wing group is
  0.073865 of MTOW, the fuselage group 0.093202, each empennage group
  between 0.004 and 0.03, and the four-group total 0.178450 of MTOW,
  inside the class-II expectation bands; the four-group total sits
  strictly below the class-I empty weight implied by the
  weight-estimation sibling's transport band lower bound (0.178450
  below 0.42), so the airframe structural groups alone never exceed
  the empty weight of the transport class.
- Exact-power laws: every regression factor that is a pure power of
  one regressor doubles as exactly 2^e when that regressor doubles
  with all else fixed (sweep fixed when the aspect ratio doubles, and
  the length to diameter ratio doubles by doubling the length at fixed
  diameter). The (N_ult * W0) exponents are 0.49 (wing), 0.414
  (horizontal tail), 0.376 (vertical tail) and 0.177 (fuselage); the
  q exponents 0.006, 0.043, 0.122 and 0.241; the area exponents 0.758
  (wing), 0.896 (horizontal tail), 0.873 (vertical tail) and 1.086
  (fuselage wetted area); the wing aspect ratio and taper exponents
  0.6 and 0.04; the fuselage L/D exponent -0.072. The pressurization
  penalty scales as 2^0.271 in the volume times pressure product, and
  the in-wing fuel term as 2^0.0035.
- T-tail factor: vertical_tail_group_weight with t_tail 1.0 is exactly
  1.2 times the t_tail 0.0 value (the factor is linear).
- Pressurization additivity: the pressurized fuselage mass equals the
  unpressurized fuselage mass plus the penalty 11.9 * (V_p * dp)^0.271
  in lb, converted; the penalty is load-factor and q independent (the
  load-factor and q power laws hold on the UNPRESSURIZED fuselage
  variant).
- Sweep penalty: a larger quarter-chord sweep raises each group weight
  (the net cosine power is negative for every group: the wing combines
  cos^-1.2 from the aspect ratio term with cos^0.3 from the thickness
  term, net about cos^-0.9).
- Sublinear scaling: every (N_ult * W0) exponent is below 0.5, so
  doubling the design weight times load factor scales each group by
  less than the square root of 2.
- ValueErrors across the module as enumerated in the Worked example.
- Determinism: identical outputs run to run and under both
  interpreters; no randomness; no imports beyond math; the constants
  fixed as above.

## Worked example

180-seat narrowbody transport, all inputs SI:
- MTOW = 79000.0 kg, design limit maneuvering load factor nz_limit =
  2.5 (so N_ult = 3.75), cruise dynamic pressure at the design point
  q = 12000.0 Pa.
- Wing: planform area 125.0 m^2, aspect ratio 10.0, taper ratio 0.25,
  thickness to chord 0.11, quarter-chord sweep 25.0 degrees, fuel
  weight in the wing 14000.0 kg.
- Horizontal tail: area 32.0 m^2, aspect ratio 6.0, taper ratio 0.30,
  thickness to chord 0.09, sweep 30.0 degrees.
- Vertical tail: area 26.0 m^2, aspect ratio 1.8, taper ratio 0.30,
  thickness to chord 0.12, sweep 35.0 degrees, t_tail 0.0
  (fuselage mounted).
- Fuselage: wetted area 405.0 m^2, length 39.5 m, equivalent diameter
  3.9 m; pressurized volume 300.0 m^3, cabin pressure differential
  55158.0 Pa (8.0 psi).

All values below are REAL outputs of the prep anchor
/tmp/w47spec/anchor_component_weight_estimation.py (pure stdlib, math
only, closed form, exit 0, no RNG, byte-identical under both
interpreters), run once and quoted as printed:

- Group masses (module output): wing_group_weight gives
  5835.319661 kg, horizontal_tail_group_weight gives 461.175701 kg,
  vertical_tail_group_weight gives 438.062259 kg and
  fuselage_group_weight (pressurized) gives 7362.993775 kg; the
  airframe group total is 14097.551395 kg. As fractions of the 79000.0
  kg MTOW: wing 0.073865, horizontal tail 0.005838, vertical tail
  0.005545, fuselage 0.093202, four-group total 0.178450. Each value
  sits in its class-II band and the total reconciles against the
  transport empty-weight band: the four groups are about 36.6 percent
  of the class-I mid-band empty weight (0.485 times MTOW), consistent
  with the primary structure share of empty weight that the mass-budget
  breakdown categories expect.
- The fuselage pressurization penalty: the unpressurized variant
  fuselage_group_weight (no volume, no delta) gives 7246.112306 kg, so
  the penalty is 116.881468 kg (about 1.6 percent of the fuselage
  group, 11.9 * (V_p * dp)^0.271 in lb units with V_p 300.0 m^3 =
  10594.4 ft^3 and dp 8.0 psi). Doubling the pressure differential to
  110316.0 Pa gives a penalty of 141.034313 kg, a ratio of 1.206644
  against 2^0.271 = 1.206643920.
- T-tail variant: vertical_tail_group_weight with t_tail 1.0 gives
  525.674710 kg, exactly 1.2 times the conventional 438.062259 kg.
- Load-factor power law (identity, module output): recomputing every
  group at nz_limit 5.0 (N_ult doubled) scales the wing by 1.404445,
  the horizontal tail by 1.332375, the vertical tail by 1.297739 and
  the unpressurized fuselage by 1.130531, matching 2^0.490 =
  1.404444876, 2^0.414 = 1.332374825, 2^0.376 = 1.297738767 and
  2^0.177 = 1.130530567.
- Dynamic-pressure power law (identity, module output): recomputing
  every group at q = 24000.0 Pa scales the wing by 1.004168, the
  horizontal tail by 1.030254, the vertical tail by 1.088242 and the
  unpressurized fuselage by 1.181812, matching 2^0.006 =
  1.004167543, 2^0.043 = 1.030253954, 2^0.122 = 1.088242442 and
  2^0.241 = 1.181811547.
- Geometric power laws (identity, module output): doubling the wing
  planform area scales the wing group by 1.691144575 (2^0.758), the
  wing aspect ratio by 1.515716567 (2^0.600), the wing taper ratio by
  1.028113827 (2^0.040), the horizontal tail area by 1.860899315
  (2^0.896), the vertical tail area by 1.831467373 (2^0.873), the
  fuselage wetted area by 2.122846418 (2^1.086) and the fuselage
  length to diameter ratio (length doubled at fixed diameter) by
  0.951318276 (2^-0.072); doubling the in-wing fuel scales the wing by
  1.002428960 (2^0.0035).
- Sweep penalty (module output): the wing at 40 degrees sweep gives
  6788.662565 kg against 5835.319661 kg at 25 degrees, and the
  horizontal tail at 40 degrees gives 473.559089 kg against 461.175701
  kg at 30 degrees.
- ValueErrors with real messages (module output, quoted as printed):
  an MTOW of 0.0 raises "MTOW must be positive, got 0.0"; a wing area
  of 0.0 raises "planform area must be positive, got 0.0"; an aspect
  ratio of 0.0 raises "aspect ratio must be positive, got 0.0"; a
  taper ratio of 0.0 raises "taper ratio must be positive, got 0.0";
  a thickness to chord of 1.0 raises "thickness to chord must be below
  1.0, got 1.0"; a sweep of 90.0 degrees raises "sweep angle must be
  below 90 degrees, got 90.0"; an in-wing fuel of 0.0 raises "fuel
  weight in the wing must be positive, got 0.0"; a limit load factor
  of -1.0 raises "design limit load factor must be positive, got
  -1.0"; a t_tail of -0.5 raises "t_tail must be non-negative, got
  -0.5"; a dynamic pressure of 0.0 raises "dynamic pressure must be
  positive, got 0.0"; a fuselage diameter of 0.0 raises "fuselage
  diameter must be positive, got 0.0"; a pressurized volume with a
  zero pressure differential raises "pressurization requires both the
  pressurized volume and the pressure differential, got volume 300.0
  m^3 and dp 0.0 Pa"; a negative group mass raises "group mass 1 must
  be non-negative, got -1.0" from airframe_group_total.
- Determinism: two consecutive runs return identical values; the
  anchor exits 0 and its internal asserts (fraction bands, every
  exact-power identity within 1e-9 relative, the linear T-tail factor
  within 1e-12) all pass.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w47spec/anchor_component_weight_estimation.py (stdlib math,
closed form, exit 0, no randomness, identical under both
interpreters).

## Validation list (contract test must include)

1. Worked example asserts within 1e-6 relative: wing_group_weight
   (79000.0, 2.5, 12000.0, 125.0, 10.0, 0.25, 0.11, 25.0, 14000.0)
   = 5835.319661 kg, horizontal_tail_group_weight (79000.0, 2.5,
   12000.0, 32.0, 6.0, 0.30, 0.09, 30.0) = 461.175701 kg,
   vertical_tail_group_weight (79000.0, 2.5, 12000.0, 26.0, 1.8,
   0.30, 0.12, 35.0, 0.0) = 438.062259 kg and fuselage_group_weight
   (79000.0, 2.5, 12000.0, 405.0, 39.5, 3.9, 300.0, 55158.0) =
   7362.993775 kg; airframe_group_total = 14097.551395 kg; the
   fractions of MTOW are 0.073865, 0.005838, 0.005545, 0.093202 and
   0.178450.
2. Physical-sanity bands: each group mass is positive, below the total,
   and the total is below the MTOW; the wing and fuselage fractions of
   MTOW lie in [0.05, 0.15], each empennage fraction in [0.004, 0.03],
   and the four-group fraction in [0.10, 0.30]; the four-group
   fraction 0.178450 lies below the class-I transport empty-weight
   band lower bound 0.42 (the weight-estimation sibling's band), the
   empty-weight sanity band identity.
3. Load-factor power law within 1e-9 relative: every group recomputed
   at nz_limit 5.0 divides by its value at 2.5 to give 2^0.49 =
   1.404444876 for the wing, 2^0.414 = 1.332374825 for the horizontal
   tail, 2^0.376 = 1.297738767 for the vertical tail and 2^0.177 =
   1.130530567 for the UNPRESSURIZED fuselage variant (the
   pressurization penalty is load independent).
4. Dynamic-pressure power law within 1e-9 relative: every group
   recomputed at q 24000.0 Pa gives 2^0.006 = 1.004167543 (wing),
   2^0.043 = 1.030253954 (horizontal tail), 2^0.122 = 1.088242442
   (vertical tail) and 2^0.241 = 1.181811547 (unpressurized fuselage).
5. Geometric power laws within 1e-9 relative: doubling the wing area
   gives 2^0.758 = 1.691144575, the wing aspect ratio 2^0.600 =
   1.515716567, the wing taper ratio 2^0.040 = 1.028113827, the
   horizontal tail area 2^0.896 = 1.860899315, the vertical tail area
   2^0.873 = 1.831467373, the fuselage wetted area 2^1.086 =
   2.122846418, the fuselage length to diameter ratio 2^-0.072 =
   0.951318276 (length doubled at fixed diameter), and the in-wing
   fuel 2^0.0035 = 1.002428960.
6. T-tail factor: vertical_tail_group_weight with t_tail 1.0 is
   525.674710 kg within 1e-6 relative, exactly 1.2 times the
   conventional value within 1e-12 relative.
7. Pressurization decomposition: fuselage_group_weight without the
   pressurization parameters gives 7246.112306 kg within 1e-6
   relative; the penalty 116.881468 kg is the difference; doubling
   delta_p to 110316.0 Pa scales the penalty by 2^0.271 =
   1.206643920 within 1e-9 relative, and the penalty is unchanged
   (within 1e-12) when the load factor or the dynamic pressure
   changes.
8. Sweep penalty: the wing at 40.0 degrees (6788.662565 kg) exceeds
   the wing at 25.0 degrees (5835.319661 kg), and the horizontal tail
   at 40.0 degrees (473.559089 kg) exceeds the horizontal tail at 30.0
   degrees (461.175701 kg).
9. Sublinear class-II scaling: for every group, doubling the design
   weight times load factor scales the mass by less than 1.5 (every
   exponent below 0.5, the largest wing exponent 0.49 giving 2^0.49 =
   1.404444876).
10. All ValueErrors enumerated in the Worked example raise from the
    named public function with the real messages quoted there: zero or
    negative MTOW, limit load factor, dynamic pressure, planform area,
    aspect ratio, taper ratio, thickness to chord, sweep angle, wetted
    area, fuselage length and diameter; thickness to chord at or above
    1.0; sweep at or above 90 degrees; zero or negative in-wing fuel;
    negative t_tail; exactly one pressurization parameter positive;
    negative group mass in the total.
11. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math;
    module constants exactly as pinned in the Model section. No
    exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere.
12. Run the deterministic contract test offline (no network); it exits
    0. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave47-component-weight-estimation.yaml)

Query 1 (copy verbatim):
  "run the component-weight-estimation at class II for the
  transport: evaluate the wing-group-weight regression on the
  planform area, aspect ratio, sweep, thickness ratio and design
  load factor, then the fuselage-group-weight regression on the
  fuselage dimensions, and hand the group-weight totals to the
  balance sheet"
  intent: "vehicle-design/sizing; component-weight-estimation: the
  class-II wing-group-weight statistical regression on the planform
  area, aspect ratio, sweep, thickness ratio and design load factor,
  then the fuselage-group-weight regression on the fuselage
  dimensions, and the group-weight totals handed to the balance
  sheet"
  expected_skill: "vehicle-design/sizing/component-weight-estimation"
Query 2 (copy verbatim):
  "predict the empennage group weights with the statistical-weight
  equations: horizontal-tail-group-weight and
  vertical-tail-group-weight from the tail areas, tail aspect ratios
  and the design gross weight, then roll the component-weight totals
  into the mass-budget"
  intent: "vehicle-design/sizing; the statistical-weight regressions
  for the empennage groups: horizontal-tail-group-weight and
  vertical-tail-group-weight from the tail areas, tail aspect ratios
  and the design gross weight, with the component-weight totals
  rolled into the mass-budget"
  expected_skill: "vehicle-design/sizing/component-weight-estimation"
Task ids: w47-component-weight-estimation-1 and -2. Prep grep (run at
spec time by the probe): each of the tokens component-weight,
wing-group-weight, fuselage-group-weight, horizontal-tail-group-weight,
vertical-tail-group-weight, group-weight-equation,
statistical-group-weight and class-ii-weight returns ZERO matches in
every skills/ SKILL.md and in eval/hit1-corpus.yaml (grep exit 1), and
the corpus scans for weight-prediction and statistical-weight task
rows are empty (re-verified at spec time, count 0), so the queries are
collision-free; the sibling tasks route on weight-and-balance language
(weight-estimation: moments, cg, empty-weight-fraction-band, class-i
and class-ii band checks of given weights), mass rollup language
(mass-budget), class-I fraction language (tow-estimation), station
language (cg-envelope), gyration language (inertia-estimation) and
member sizing language (wing-box-sizing), none of which carries
geometry-driven group-weight content. Add one fence line to
weight-estimation reading "statistical group-weight prediction from
geometry belongs to the component-weight-estimation sibling" and one
router row to skills/vehicle-design/SKILL.md at build time pointing
class-II group-weight prediction to the new leaf (the
landing-gear-height-sizing precedent). Family spread: vehicle-design
56 to 57 after landing.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must predict the airframe
structural group weights at the class-II level from geometry and
design loading:" and include the outputs in the Claim order (the wing
group, horizontal tail group, vertical tail group and fuselage group
masses from the statistical regressions, the airframe group total, and
the per-group and total fractions of MTOW), then close with the
Trigger list. Refer to the outputs as group masses or group weights,
never as the bare single words weight, mass, estimation or group;
never claim total aircraft sizing, takeoff weight iteration, cg or
inertia outputs; never reproduce the anchor book text (reference-only,
paraphrase). First tag: component-weight-estimation. Metadata tags
EXACTLY as the probe receipt gate (f) lists them, nothing else:
group-weight-equation, wing-group-weight, fuselage-group-weight,
horizontal-tail-group-weight, vertical-tail-group-weight,
statistical-weight-prediction, class-ii-weight-buildup. 50-150 words,
<=1000 chars, no em dash, action verb present. Recommended wording
(verified at spec time):

"Use when you must predict the airframe structural group weights at
the class-II level from geometry and design loading: evaluate the
statistical wing-group-weight regression on the planform area, aspect
ratio, sweep, thickness ratio and design load factor, the
horizontal-tail-group-weight and vertical-tail-group-weight
regressions on the tail planforms, and the fuselage-group-weight
regression on the fuselage wetted area, fineness ratio and design
gross weight, with the limit load factor scaled to ultimate by the 1.5
safety factor and the pressurization penalty added when the
pressurized volume and differential are given. Produces the four group
masses in kg, the airframe group total, and the group fractions of
MTOW that feed the weight statement. Trigger: component weight
estimation, group weight equation, wing group weight, fuselage group
weight, horizontal tail weight, vertical tail weight, statistical
weight prediction, class ii weight buildup."

FORBIDDEN TOKENS (belong to siblings): moments, center of gravity,
cg, weight and balance, forward limit, aft limit, empty weight
fraction band, static margin and the generic class-i or class-ii as
standalone terms (weight-estimation; use class-ii-weight-buildup);
mass rollup, growth allowance, contingency margin, margin policy,
mtow target check, mass breakdown (mass-budget); takeoff gross
weight, fuel fraction method, sizing iteration, convergence verdict,
weight breakdown balance (tow-estimation); cg station, envelope
polygon, neutral point, cg excursion (cg-envelope); moment of
inertia, radius of gyration, parallel axis theorem
(inertia-estimation); wing box, spar cap, spar web, shear flow, root
bending moment, skin stringer, panel buckling (wing-box-sizing,
fuselage-skin-stringer); multidisciplinary optimization, coupling
variables, fixed point iteration (multidisciplinary-optimization);
landing gear, installed engine, systems group, fuel weight group and
any non-airframe group weight (out of the four-group claim). Never
the bare words weight, mass, estimation, group, component, load,
factor, aircraft, design or sizing as standalone metadata tags, and
never claim that a group mass is a takeoff weight, an empty weight or
a total aircraft mass.

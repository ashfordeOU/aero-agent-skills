# Wave-48 leaf spec: landing-gear-weight-estimation (vehicle-design,
# sizing pack)

- Path: skills/vehicle-design/sizing/landing-gear-weight-estimation/
- Pack: sizing (present siblings landing-gear-sizing (static loads over
  the struts, nose and main gear load share from the CG and wheelbase,
  shock absorber stroke and the tire rating margin),
  landing-gear-retraction-sizing (the gear weight consumer that takes
  the gear group weight as a given input to the retraction moment),
  landing-gear-height-sizing (the wave-46 GO that solves the vertical
  ground line and the gear heights that scale the strut length inputs),
  landing-gear-layout (arrangement angles and the nose gear load
  fraction band), tire-sizing, weight-estimation (the class-I /
  class-II weight-and-balance reducer that consumes component weights
  as given inputs), component-weight-estimation (the wave-47 GO whose
  four-airframe-group claim fences this leaf in) and the rest of the
  41-leaf sizing pack; adjacent fences in vehicle-design/mass-properties
  (mass-budget, cg-envelope, inertia-estimation), in
  vehicle-design/conceptual (tow-estimation) and in structures/loads
  (landing-ground-loads, which owns the certification landing reaction
  cases)). Wave-48 probe receipt task-4 rank 1 GO; 0 owners verified
  whole-tree (greps below re-run at spec time).
- Claim fences (quoted from the sibling frontmatter and bodies at spec
  time, re-verified at HEAD b03e6ff1; the nearest owners all treat the
  gear weight as a GIVEN input or own the gear DESIGN surface, and none
  derives the landing gear group MASS from the design landing weight and
  landing load factor, which is the exact gap this leaf closes):
  - skills/vehicle-design/sizing/landing-gear-retraction-sizing/SKILL.md
    frontmatter description (line 3): "Use when you must size the
    landing gear retraction mechanism: the gear moment about the retract
    pivot from gear weight and CG arm, the retraction actuator force
    from that moment and actuator arm with a design factor, the actuator
    stroke from the four-bar linkage geometry..." Its workflow step 1
    (lines 72-73): "Fix the gear demand: gear weight W and its CG arm d
    ahead of the retract pivot (retraction_moment)." Its worked example
    (line 95): "Reference main gear: gear weight 14000 N with CG arm
    1.10 m ahead of the retract pivot." The retraction leaf REQUIRES the
    gear weight as an input and never derives it; this leaf is the
    missing producer of that input.
  - skills/vehicle-design/sizing/landing-gear-sizing/SKILL.md lines
    24-26: "Use when the task is sizing the landing gear at the
    conceptual level: static loads over the struts, nose and main gear
    load share from the CG and wheelbase, shock absorber stroke, and the
    tire rating margin." Loads and stroke, never a gear group mass
    output.
  - skills/vehicle-design/sizing/tire-sizing/SKILL.md frontmatter
    description (line 3): "Use when you must size the tires for an
    aircraft landing gear at the conceptual level: split the static load
    per tire from the takeoff weight, the gear load share, and the tire
    count, compute the tire diameter and width with the power law
    fit..." Tire dimensions, count, pressure and footprint, never a gear
    group mass.
  - skills/vehicle-design/sizing/landing-gear-height-sizing/SKILL.md
    lines 25-27: "Use when the task is selecting the vertical landing
    gear geometry of a tricycle-gear aircraft at the conceptual level:
    solving the static ground line from the ground clearance
    constraints, setting the main and nose gear heights..." and its
    quick reference (lines 55-58): "Gear heights: main gear height =
    H_gl (the main gear is vertical, contact directly below the attach
    point); nose gear height = H_gl + z_na." Heights are geometry
    outputs that scale this leaf's strut length inputs.
  - skills/vehicle-design/sizing/landing-gear-layout/SKILL.md lines
    79-80: "The fraction is dimensionless and layout-level only; strut
    loads are never computed here." Layout angles and the load fraction
    band, let alone gear group mass.
  - skills/vehicle-design/mass-properties/mass-budget/SKILL.md lines
    54-55: "Collect the subsystem mass estimates in kg, one entry per
    subsystem." The gear subsystem mass would be a given input to the
    rollup, growth allowance and margin policy; no line derives it.
  - skills/vehicle-design/sizing/weight-estimation/SKILL.md lines
    25-28: "Use when the task is aircraft weight estimation and weight
    and balance: moments and center of gravity from component weights
    and arms, CG envelope checks, and empty-weight fraction band checks
    for class-I / class-II sizing." Its workflow step 1 (line 43):
    "Collect component weights and arms into matching lists." Component
    weights are the INPUT of the only weight-named sizing sibling; the
    build must disambiguate its generic class-ii trigger token: class-II
    gear group weight PREDICTION from the design landing weight and
    landing load factor routes to this leaf; class-II weight and balance
    of given component weights stays with weight-estimation.
  - skills/vehicle-design/sizing/component-weight-estimation/SKILL.md
    lines 25-29: "Use when the task is predicting the four airframe
    structural group masses at the class-II level from geometry and
    design loading: the wing group, the horizontal tail group, the
    vertical tail group and the fuselage group, each from a published
    closed-form statistical regression..." The wave-47 spec claim fence
    (verbatim from ops/automation/state/wave47-specs/
    component-weight-estimation.md): "non-airframe group weights
    (landing gear, installed engines, systems, fuel, fixed equipment):
    the four airframe structural groups are the whole claim." The
    landing gear group weight is deliberately OUT of its claim; this
    leaf produces that weight-statement line.
  - Zero-owner evidence re-verified at spec time at HEAD (real outputs):
    `grep -rilE "landing-gear-group-weight|main-gear-group-weight|
    nose-gear-group-weight|landing-gear-weight-estimation|gear-group-
    weight|gear-weight-regression|class-ii-gear-weight" skills/ eval/`
    returns no files (EXIT=1), and the corpus token scan of
    eval/hit1-corpus.yaml for the same battery returns count 0 (zero of
    the 1306 task blocks). The only gear weight mentions in the tree are
    inside landing-gear-retraction-sizing, where gear weight W is the
    given input to the retraction moment, never an output. No leaf
    anywhere produces the landing gear group mass; the gear-group-weight
    tokens have zero owners.
  - Merge-time notes (probe receipt gate (f), carried into this
    contract): add a fence line to landing-gear-retraction-sizing
    reading "landing gear group weight prediction from design landing
    weight and load factor belongs to the
    landing-gear-weight-estimation sibling; this leaf takes the gear
    weight as a given input", add a router row in
    skills/vehicle-design/SKILL.md beside the landing-gear rows (the
    retraction-sizing row sits at line 77 at spec time), and add 2
    corpus tasks at merge with the hyphenated tokens below. Family
    spread: vehicle-design 57 to 58 after landing.
- Standards id: far-25 (14 CFR Part 25, reference-only, family
  convention) and cs-25 (CS-25, reference-only), both verified present
  in standards-map.yaml at spec time (grep line 16 for far-25, line 27
  for cs-25; 30 ids total). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Predict the landing gear group mass at the class-II level from the
design landing weight, the landing load factor and the gear geometry:
the main gear group mass from a statistical regression on the design
landing weight, the ultimate landing load factor, the main gear strut
length, the total main wheel count, the main shock strut count and the
stall speed, and the nose gear group mass from a regression on the
design landing weight, the ultimate landing load factor, the nose gear
strut length and the nose wheel count, with the two group masses summed
into the landing gear group total for the weight statement. The method
is the class-II landing gear weight prediction of the weight estimation
chapter of Raymer, Aircraft Design: A Conceptual Approach, paraphrased
in this leaf's own notation (brief 06, summary-only; the books are
proprietary-sold); Torenbeek, Synthesis of Subsonic Airplane Design
carries the magnitude cross-check, its landing gear group treatment
placing the group near 3.8 to 4.5 percent of gross weight for aircraft
above 10000 lb, and the FLOPS and Roskam treatments of the same book
family sit beside it. Every regression is deterministic stdlib
power-law arithmetic over fixed published constants: no tables beyond
the constants, no vendor catalogs, no numerical integration, no
composite material factors. The load factor enters both regressions as
the ULTIMATE value, the limit landing load factor times the 1.5 factor
of safety between limit and ultimate loads (the FAR-25.303 convention
the wing-box-sizing sibling already applies between limit and
ultimate), and the weight regressor is the design LANDING weight, not
the MTOW; the regressions are landing-weight based and the worked
example below is a 180-seat narrowbody transport whose gear group total
lands in the established class-II band and reconciles against the
retraction sibling's given gear weight scale. The regressions apply to
the transport form with the non-kneeling K_mp factor and the
turbine-transport K_np factor equal to 1.0 folded into the published
leading constants; kneeling-gear and reciprocating-engine variants are
outside the claim. Inputs and outputs are SI (kg, m, dimensionless
counts), with the stall speed kept in knots because the published
regression raises the numeric knots value to the 0.1 power; the
regressions themselves are the published lb / in closed forms converted
at the boundary by fixed unit constants, so every published coefficient
stays visible. Produces the main and nose gear group masses in kg, the
landing gear group total in kg, and the group fractions of the design
landing weight and of MTOW that gate the weight statement. Does NOT do:
static loads over the struts, nose and main gear load share from the CG
and wheelbase, shock absorber stroke or tire rating margin, and any
gear DESIGN verdict (vehicle-design/sizing/landing-gear-sizing); the
retraction moment, actuator force and stroke, lock hold loads or gear
bay stowage fit (vehicle-design/sizing/landing-gear-retraction-sizing);
the tipback, tail strike and lateral turnover angles, the nose gear
load fraction band or the main gear position check
(vehicle-design/sizing/landing-gear-layout); the vertical ground line,
the gear heights or the clearance margins
(vehicle-design/sizing/landing-gear-height-sizing); tire diameter,
width, count, pressure or footprint (vehicle-design/sizing/
tire-sizing); rejected-takeoff brake energy or heat sink sizing
(vehicle-design/sizing/brake-energy-sizing); the certification landing
reaction cases, level landing, tail down condition, one wheel load or
braked roll (structures/loads/landing-ground-loads); the four airframe
structural group masses, the wing group, the horizontal tail group, the
vertical tail group and the fuselage group, and every other group
weight of the weight statement (vehicle-design/sizing/
component-weight-estimation); moments, center of gravity, envelope
limits or empty-weight fraction band checks of given component weights
(vehicle-design/sizing/weight-estimation); the subsystem mass rollup,
growth allowance, contingency margin or MTOW target check
(vehicle-design/mass-properties/mass-budget); the class-I takeoff
weight fraction iteration on category bands (vehicle-design/conceptual/
tow-estimation); cg stations, envelope polygons, static margin,
moments of inertia or radii of gyration (vehicle-design/mass-properties/
cg-envelope and inertia-estimation); MDO coupling loops or optimization
over the weight statement (vehicle-design/mdo/
multidisciplinary-optimization). The landing gear DESIGN surface
(layout, static loads, retraction, height, tires, brakes) is fully
owned by its siblings and the gear weight everywhere else is a given
input, never derived; this leaf produces the gear group MASS only, the
missing producer of the gear weight line of the weight statement.

## Model (implement exactly)

Pure stdlib, closed form, deterministic, no RNG. The regressions are
pure power-law arithmetic, so no imports are required. The public
functions take SI (kg, m, dimensionless counts) and return kg; the
stall speed stays in knots as published, and the regressions run in the
published lb / in closed forms.

Module constants (fixed, no others):
- Unit conversions: KG_TO_LB = 1.0 / 0.45359237; M_TO_IN =
  1.0 / 0.0254.
- ULTIMATE_OVER_LIMIT = 1.5 (the factor between the design limit
  landing load factor and the ultimate value used in both regressions;
  the worked example's limit 3.0 gives the ultimate 4.5 of the source
  treatment's transport assumption).
- Main gear group (lb, strut length in, stall speed in knots): MAIN_LG_K
  = 0.0106, MAIN_LG_E_WL = 0.888, MAIN_LG_E_NL = 0.25, MAIN_LG_E_LM =
  0.4, MAIN_LG_E_NMW = 0.321, MAIN_LG_E_NMSS = -0.5, MAIN_LG_E_VS = 0.1.
- Nose gear group (lb, strut length in): NOSE_LG_K = 0.032,
  NOSE_LG_E_WL = 0.646, NOSE_LG_E_NL = 0.2, NOSE_LG_E_LN = 0.5,
  NOSE_LG_E_NNW = 0.45.
- Configuration defaults: SHOCK_STRUTS_DEFAULT = 2.0 (main gear shock
  struts, the source treatment's assumption for a transport main gear)
  and STALL_SPEED_KTS_DEFAULT = 51.0 (the stall speed assumption of the
  source treatment; the 0.1 exponent makes the term mild).
- The published K_mp (non-kneeling gear) and K_np (non-reciprocating
  installation) factors are 1.0 in the transport form implemented here
  and are folded into the leading constants MAIN_LG_K and NOSE_LG_K;
  the kneeling-gear and reciprocating-engine variants are outside the
  claim. Every fixed number in the model is one of the constants above;
  the boundary conversions multiply or divide once per input or output
  and introduce no other numbers.

Defining relations (pin these exactly; every function derives from
them; W_l is the design landing weight in lb, N_ult = 1.5 *
n_land_limit the ultimate landing load factor, L_m and L_n the extended
main and nose gear strut lengths in inches, N_mw the total number of
main gear wheels, N_mss the number of main gear shock struts, N_nw the
total number of nose gear wheels and V_s the stall speed in knots):
- Main gear group: W_main = 0.0106 * W_l^0.888 * N_ult^0.25 * L_m^0.4
  * N_mw^0.321 * N_mss^-0.5 * V_s^0.1.
- Nose gear group: W_nose = 0.032 * W_l^0.646 * N_ult^0.2 * L_n^0.5 *
  N_nw^0.45.
- The gear group total: the sum of the two group masses; every group
  mass is a fraction of the design landing weight, and the landing
  weight exponents (0.888 main, 0.646 nose) are below 1, so the group
  total scales slower than the landing weight and the gear group
  fraction of the landing weight falls as the design grows, which is
  the scale behavior the class-I band checks of the weight-estimation
  sibling bracket. The shock strut exponent is negative (-0.5), so
  spreading the main gear load over more shock struts lowers the main
  gear group estimate.
- Units: inputs are SI (kg, m, dimensionless counts) with the stall
  speed in knots, outputs kg. Every fixed number in the model is one of
  the module constants above.

Functions:
- main_gear_group_weight(design_landing_weight_kg, n_land_limit,
  main_strut_length_m, main_wheels, main_shock_struts=2.0,
  stall_speed_kts=51.0) -> float
  Main gear group mass in kg. Raises ValueError for a non-positive
  design landing weight, limit landing load factor, main strut length
  or stall speed, for fewer than 1 main wheel or shock strut, and for
  non-number arguments.
- nose_gear_group_weight(design_landing_weight_kg, n_land_limit,
  nose_strut_length_m, nose_wheels) -> float
  Nose gear group mass in kg. Raises ValueError for a non-positive
  design landing weight, limit landing load factor or nose strut
  length, for fewer than 1 nose wheel, and for non-number arguments.
- landing_gear_group_total(w_main, w_nose) -> float
  Sum of the two group masses in kg. Raises ValueError for a non-number
  or negative group mass.

Identities to test (closed form, checkable without the builder module):
- Physical-sanity bands: at the worked parameters the gear group total
  is 0.050367 of the design landing weight and 0.042079 of the MTOW,
  inside the class-II expectation band (the Torenbeek treatment places
  the gear group near 3.8 to 4.5 percent of gross weight for aircraft
  above 10000 lb), the nose gear group is 0.129449 of the group total,
  the main gear group sits above the nose gear group, and the total
  sits strictly below the design landing weight and far below the
  class-I empty weight implied by the weight-estimation sibling's
  transport band lower bound (0.042079 below 0.42), so the gear group
  alone never approaches the empty weight of the transport class.
- Exact-power laws: every regression factor that is a pure power of one
  regressor doubles as exactly 2^e when that regressor doubles with all
  else fixed. The design landing weight exponents are 0.888 (main) and
  0.646 (nose); the ultimate load factor exponents 0.25 (main) and 0.2
  (nose); the strut length exponents 0.4 (main) and 0.5 (nose); the
  wheel count exponents 0.321 (main) and 0.45 (nose); the shock strut
  exponent -0.5 (main, negative) and the stall speed exponent 0.1
  (main).
- Sublinear scaling: doubling the design landing weight scales the main
  group by 2^0.888 = 1.850608856 and the nose group by 2^0.646 =
  1.564823563, both below 2, and the gear group fraction of the design
  landing weight falls from 0.050367 to 0.045673.
- Monotonicity: both group masses increase strictly with the design
  landing weight (both landing weight exponents positive).
- ValueErrors across the module as enumerated in the Worked example.
- Determinism: identical outputs run to run and under both
  interpreters; no randomness; no imports; the constants fixed as
  above.

## Worked example

180-seat narrowbody transport, design inputs:
- Design landing weight 66000.0 kg, limit landing load factor 3.0 (so
  N_ult = 4.5, the source treatment's transport assumption).
- Main gear: extended strut length 2.30 m, 4 main wheels in total on 2
  shock struts, stall speed 115.0 kts.
- Nose gear: extended strut length 1.40 m, 2 nose wheels.
- Scale context: the 66000.0 kg design landing weight is 0.835 of the
  79000.0 kg MTOW, a realistic transport-category landing weight ratio.

All values below are REAL outputs of the prep anchor
/tmp/w48spec/anchor_landing_gear_weight.py (pure stdlib, closed-form
power laws, exit 0, no RNG, byte-identical output under both
interpreters), run once and quoted as printed:

- Group masses (module output): main_gear_group_weight gives
  2893.904950 kg, nose_gear_group_weight gives 430.316692 kg, and the
  landing gear group total is 3324.221642 kg. As fractions: 0.050367 of
  the 66000.0 kg design landing weight, 0.042079 of the 79000.0 kg MTOW
  (inside the Torenbeek 0.038 to 0.045 gross-weight band), and the nose
  gear group is 0.129449 of the group total. The main gear group is
  28.380 kN as a force, 14.190 kN per shock strut leg.
- Consumer scale cross-check: the 14.190 kN per-leg main gear weight is
  on the order of the 14000 N main-gear leg weight that the
  landing-gear-retraction-sizing worked example fixes as a GIVEN input
  ("gear weight 14000 N with CG arm 1.10 m"), confirming that the gear
  weight this leaf produces is the input that leaf consumes.
- Design landing weight power law (identity, module output):
  recomputing both groups at 132000.0 kg (doubled) scales the main
  group by 1.850608856 and the nose group by 1.564823563, matching
  2^0.888 = 1.850608856 and 2^0.646 = 1.564823563; the gear group
  fraction of the design landing weight falls from 0.050367 to
  0.045673.
- Load factor power law (identity, module output): recomputing both
  groups at n_land_limit 6.0 (ultimate 9.0, doubled) scales the main
  group by 1.189207115 and the nose group by 1.148698355, matching
  2^0.25 = 1.189207115 and 2^0.2 = 1.148698355.
- Geometry power laws (identity, module output): doubling the main
  strut length scales the main group by 1.319507911 (2^0.4), the nose
  strut length the nose group by 1.414213562 (2^0.5), the main wheel
  count the main group by 1.249196126 (2^0.321), the nose wheel count
  the nose group by 1.366040257 (2^0.45), the main shock strut count
  the main group by 0.707106781 (2^-0.5, the main group FALLS when the
  load spreads over more struts) and the stall speed the main group by
  1.071773463 (2^0.1).
- ValueErrors with real messages (module output, quoted as printed): a
  design landing weight of 0.0 raises "design landing weight must be
  positive, got 0.0"; a limit load factor of -1.0 raises "design limit
  landing load factor must be positive, got -1.0"; a main strut length
  of 0.0 raises "main strut length must be positive, got 0.0"; a main
  wheel count of 0 raises "number of main gear wheels must be at least
  1, got 0"; a shock strut count of 0 raises "number of main gear shock
  struts must be at least 1, got 0"; a stall speed of 0.0 raises "stall
  speed must be positive, got 0.0"; a nose strut length of 0.0 raises
  "nose strut length must be positive, got 0.0"; a nose wheel count of
  0 raises "number of nose gear wheels must be at least 1, got 0"; a
  negative group mass raises "group mass 1 must be non-negative, got
  -1.0" and a non-number group mass raises "group mass 1 must be a
  number, got 'a'" from landing_gear_group_total.
- Determinism: two consecutive runs return identical values; the anchor
  exits 0 and its internal asserts (positive masses, magnitude bands,
  every exact-power identity within 1e-9 relative, monotonicity in the
  design landing weight, the sublinear fraction fall, byte-identical
  output under both interpreters) all pass.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w48spec/anchor_landing_gear_weight.py (stdlib, closed form, exit
0, no randomness, identical under both interpreters).

## Validation list (contract test must include)

1. Worked example asserts within 1e-6 relative: main_gear_group_weight
   (66000.0, 3.0, 2.30, 4, 2, 115.0) = 2893.904950 kg,
   nose_gear_group_weight (66000.0, 3.0, 1.40, 2) = 430.316692 kg and
   landing_gear_group_total = 3324.221642 kg; the group fractions of
   the 66000.0 kg design landing weight are 0.050367 total, and of the
   79000.0 kg MTOW 0.042079; the nose gear group share of the total is
   0.129449.
2. Physical-sanity bands: each group mass is positive, the main gear
   group sits above the nose gear group, and the total is below the
   design landing weight; the gear group fraction of the design landing
   weight lies in [0.03, 0.07] and of the MTOW in [0.03, 0.06]; the
   nose gear group share lies in [0.05, 0.25]; the MTOW fraction
   0.042079 lies below the class-I transport empty-weight band lower
   bound 0.42 (the weight-estimation sibling's band), the gear group
   sanity identity.
3. Design landing weight power law within 1e-9 relative: every group
   recomputed at 132000.0 kg divides by its value at 66000.0 kg to give
   2^0.888 = 1.850608856 for the main gear group and 2^0.646 =
   1.564823563 for the nose gear group.
4. Load factor power law within 1e-9 relative: every group recomputed
   at n_land_limit 6.0 (ultimate 9.0) gives 2^0.25 = 1.189207115 (main)
   and 2^0.2 = 1.148698355 (nose).
5. Geometry power laws within 1e-9 relative: doubling the main strut
   length gives 2^0.4 = 1.319507911, the nose strut length 2^0.5 =
   1.414213562, the main wheel count 2^0.321 = 1.249196126, the nose
   wheel count 2^0.45 = 1.366040257, the main shock strut count 2^-0.5
   = 0.707106781 (the main group estimate falls when the load spreads
   over more struts) and the stall speed 2^0.1 = 1.071773463.
6. Sublinear scaling: doubling the design landing weight scales each
   group by less than 2 (the exponents 0.888 and 0.646 are below 1),
   and the gear group fraction of the design landing weight falls from
   0.050367 at 66000.0 kg to 0.045673 at 132000.0 kg.
7. Monotonicity: a 1 percent higher design landing weight (66660.0 kg)
   strictly raises both group masses.
8. Consumer scale cross-check: the worked main gear group over the 2
   shock struts is 14.190 kN per leg, on the order of the 14000 N
   main-gear leg weight the landing-gear-retraction-sizing worked
   example fixes as a given input; the module never sizes the
   retraction mechanism.
9. All ValueErrors enumerated in the Worked example raise from the
   named public function with the real messages quoted there: zero or
   negative design landing weight, limit landing load factor, main and
   nose strut lengths and stall speed; fewer than 1 main wheel, main
   shock strut or nose wheel; negative or non-number group mass in the
   total.
10. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports; module constants
    exactly as pinned in the Model section. No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.
11. The prep anchor runs offline and exits 0 with every internal assert
    passing (positive masses, magnitude bands, the exact-power
    identities within 1e-9 relative, monotonicity, the sublinear
    fraction fall).
12. Run the deterministic contract test offline (no network); it exits
    0. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave48-landing-gear-weight-estimation.yaml)

Query 1 (copy verbatim):
  "estimate the landing-gear-group-weight at class II with the
  statistical gear-weight regression: main-gear-group-weight and
  nose-gear-group-weight from the design landing weight, the ultimate
  landing load factor and the main and nose gear strut lengths, then
  hand the gear weight total to the mass budget"
  expected_skill: "vehicle-design/sizing/landing-gear-weight-estimation"
Query 2 (copy verbatim):
  "run the landing-gear-weight-estimation for the tricycle transport:
  predict the landing-gear-group-weight with the
  class-ii-gear-weight-buildup regression so the retraction mechanism
  sizing gets the gear weight input"
  expected_skill: "vehicle-design/sizing/landing-gear-weight-estimation"
Task ids: w48-landing-gear-weight-estimation-1 and -2. The two query
texts are the receipt gate (e) queries verbatim (wave-48 probe receipt,
task-4), sim-verified by replicating the scripts/router_eval.py token
router EXACTLY over the real index plus this candidate: query 1 HIT1
36.0 with runner-up component-weight-estimation 15.5 (margin 20.5),
query 2 HIT1 21.5 with runner-up landing-gear-retraction-sizing 8.5
(margin 13.0), zero theft over all 1306 corpus tasks. Prep grep (run at
spec time by the probe): each of the tokens landing-gear-weight-
estimation, landing-gear-group-weight, main-gear-group-weight,
nose-gear-group-weight, gear-group-weight-regression and
class-ii-gear-weight-buildup returns ZERO matches in every skills/
SKILL.md and in eval/hit1-corpus.yaml (grep exit 1), so the queries are
collision-free; the sibling corpus gear tasks route on strut-load,
stroke, tipback, retraction-actuator and tire tokens, none of which
carries gear-group-weight content. Add one fence line to
landing-gear-retraction-sizing reading "landing gear group weight
prediction from design landing weight and load factor belongs to the
landing-gear-weight-estimation sibling; this leaf takes the gear weight
as a given input" and one router row to skills/vehicle-design/SKILL.md
at build time beside the landing-gear rows pointing class-II gear group
weight prediction to the new leaf (the landing-gear-height-sizing
precedent). Family spread: vehicle-design 57 to 58 after landing.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must predict the landing gear group
weight at the class-II level for the weight statement:" and include the
outputs in the Claim order (the main and nose gear group masses from
the statistical regressions, the landing gear group total, and its
fraction of the design landing weight), then close with the Trigger
list. Refer to the outputs as group masses or group weights, never as
the bare single words gear, weight, mass, landing, estimation or
group; never claim static strut loads, retraction mechanism outputs,
tire sizing, layout angles or height geometry; never reproduce the
anchor book text (reference-only, paraphrase). First tag:
landing-gear-weight-estimation. Metadata tags EXACTLY as the probe
receipt gate (f) lists them, nothing else: landing-gear-group-weight,
main-gear-group-weight, nose-gear-group-weight,
gear-group-weight-regression, class-ii-gear-weight-buildup. 50-150
words, <=1000 chars, no em dash, action verb present. Recommended
wording (verified at spec time):

"Use when you must predict the landing gear group weight at the class-II
level for the weight statement: evaluate the statistical
main-gear-group-weight regression on the design landing weight, the
ultimate landing load factor and the main gear strut length with the
wheel, strut and stall speed terms, evaluate the
nose-gear-group-weight regression on the design landing weight, the
ultimate landing load factor and the nose gear strut length with the
nose wheel count, with the limit landing load factor scaled to ultimate
by the 1.5 safety factor, and sum the two group masses into the landing
gear group total. Produces the main and nose gear group masses in kg,
the gear group total, and its fraction of the design landing weight for
the weight statement. Trigger: landing gear group weight estimation,
gear weight regression, main gear group weight, nose gear group weight,
class ii gear weight buildup."

FORBIDDEN TOKENS (belong to siblings): strut load, static load, gear
load share, shock absorber stroke, sink speed, tire rating
(landing-gear-sizing); retraction moment, actuator force, actuator
stroke, four-bar linkage, lock hold load, down-lock, up-lock, gear bay
stowage (landing-gear-retraction-sizing); tipback angle, tail strike,
turnover angle, nose gear load fraction, main gear position
(landing-gear-layout); static ground line, gear height, tail-cone
clearance, ground clearance, waterline (landing-gear-height-sizing);
tire diameter, tire width, tire count, inflation pressure, footprint,
rolling radius (tire-sizing); brake energy, heat sink
(brake-energy-sizing); level landing, tail down condition, one wheel
load, braked roll (structures/loads/landing-ground-loads); wing group,
horizontal tail group, vertical tail group, fuselage group, airframe
group total and any other group weight of the weight statement
(component-weight-estimation); moments, center of gravity, weight and
balance, envelope limit, empty weight fraction band, static margin
(weight-estimation); mass rollup, growth allowance, contingency margin,
mtow target check (mass-budget); takeoff gross weight, fuel fraction
method, sizing iteration (tow-estimation); cg station, moment of
inertia, radius of gyration (cg-envelope, inertia-estimation);
multidisciplinary optimization, coupling variables
(multidisciplinary-optimization). Never the bare words gear, weight,
mass, landing, estimation, load, group, strut, wheel or sizing as
standalone metadata tags (landing-gear-sizing, tire-sizing and
weight-estimation own the generic surface), and never claim that the
gear group mass is a strut load, a takeoff weight, an empty weight, a
total aircraft mass or any four-airframe-group weight of the
component-weight-estimation sibling.

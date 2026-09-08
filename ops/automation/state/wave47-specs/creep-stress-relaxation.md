# Wave-47 leaf spec: creep-stress-relaxation (structures, materials pack)

- Path: skills/structures/materials/creep-stress-relaxation/
- Pack: materials (present siblings creep-rupture, ramberg-osgood,
  fracture-toughness, material-selection, mmpsd-allowables,
  multiaxial-yield-criteria, crack-tip-plasticity-correction; adjacent
  fences structures/thermal-structures/thermal-stress-analysis for the
  load side of the elevated-temperature environment and the
  structures/fatigue pack for cyclic life). Wave-47 probe receipt
  task-5 rank 2 GO (CONDITIONAL), flagged conditional on the
  deterministic-anchor gate; the gate is re-run at spec time and PASSES
  (real closed-form Norton relaxation integral, real anchor numbers
  below, physically verified monotone decay).
- Claim fences (quoted from the sibling frontmatter and bodies at
  spec time; creep-rupture is the constant-stress owner and the fence
  that matters):
  - creep-rupture (this pack) frontmatter description: "Use when you
    must assess the elevated-temperature creep and stress rupture
    behavior of an aerospace metallic part: compute the steady-state
    creep strain rate with the Norton power law eps_dot = A * sigma^n *
    exp(-Q/(R*T)) from the stress and the temperature, estimate the
    rupture life in hours with the Larson-Miller parameter from the
    stress-LMP master curve, apply the Monkman-Grant relation between
    the minimum creep rate and the rupture life, accumulate the creep
    strain over the service time, and check the time to 1 percent creep
    strain and the rupture life against the required design life with
    the margin verdict." Its intro scope note (body lines 37-40):
    "This leaf does NOT cover cyclic endurance (the structures/fatigue
    pack owns cyclic life methods), constrained-expansion thermal
    stress, or statistically based tensile design values
    (structures/materials/mmpsd-allowables)." Its creep accumulation is
    constant-stress-only: body line 60-62 "Accumulated creep strain:
    eps_c(t) = eps_dot_c * t over the service time (steady-state only;
    primary creep is neglected in this leaf...)" and workflow step 5
    accumulates at the fixed stress. The sibling's entire machinery is
    a function of a SUSTAINED constant stress; a decaying-stress
    question (preload held at fixed total strain) has no function in
    its contract. There is no relaxation carve-out line because the
    model cannot express one: eps_c = eps_dot * t at a fixed sigma
    cannot answer how sigma falls while the total strain is held. The
    gap this leaf closes: the fixed-total-strain stress decay of a
    preloaded element (bolted joint preload retention, spring preload,
    interference-fit relaxation), which the constant-stress sibling
    never computes.
  - Whole-tree greps at spec time (probe receipt gate (a), re-run
    FRESH at this HEAD): the tokens stress.relaxation, creep.relaxation,
    norton.relaxation, preload.*relax, retained.preload return ZERO
    matches across every skills/ SKILL.md and ZERO of the 1286 task
    blocks in eval/hit1-corpus.yaml (grep -c returns 0), and the
    wave-41..47 recon history has no stress-relaxation adjudication
    (grep -ril over ops/automation/state/wave4*-recon/ empty). The only
    creep corpus tasks (w25-creep-rupture-1/2) route on
    larson-miller-parameter, norton-creep-law and rupture-life tokens
    for the CONSTANT-stress life and margin question; no relaxation
    content exists anywhere. GENUINE materials-pack producer seam
    (probe receipt task-5, verified zero-owner at this HEAD): no leaf
    computes the fixed-strain relaxation that the constant-stress
    creep-rupture sibling cannot express.
- Standards id: mmpsd (line 160) and far-25 (line 16), both present in
  standards-map.yaml (grep-verified at spec time), reference-only: the
  exact pair creep-rupture carries at this HEAD. Ledger Standard:
  mmpsd (primary), far-25 (secondary), both STANDARDS-REF, gated false.
- Family: structures

## Claim

Compute the stress relaxation of an initially elastic stress held at
fixed total strain while a metallic material creeps at elevated
temperature under the Norton power law. Given the initial (preload)
stress sigma_0 in Pa, the hold time t in seconds, the temperature T in
K and the material constants (Norton coefficient A, stress exponent n,
activation energy Q and elastic modulus E), the relaxed stress follows
the closed-form integral of the relaxation ODE
d(sigma)/dt = -E * A * sigma^n * exp(-Q / (R * T)) at constant total
strain (the elastic strain unloads one-for-one into creep strain):
sigma(t) = [sigma_0^(1-n) + (n - 1) * A * E * t * exp(-Q / (R * T))]
^(1 / (1 - n)) for n != 1, and sigma(t) = sigma_0 * exp(-E * A *
exp(-Q / (R * T)) * t) for n = 1 (the Newtonian viscous branch, the
n -> 1 limit of the power form). Produces the relaxed stress after the
hold, the retained fraction sigma(t) / sigma_0 (the preload-retention
fraction), the time for the stress to relax to a given fraction of the
preload, and the retained-preload margin check (margin =
retained / required - 1 with the PASS/FAIL verdict) for bolted joints,
spring preloads and interference-fit fasteners at temperature. The
model is deterministic closed-form algebra with a physically verified
power-law decay tail: for n > 1 the stress decays monotonically toward
zero and never quite reaches it, sigma(t) ~ t^(-1/(n-1)) at long time,
so the relaxed stress after any finite hold is strictly positive. Does
NOT do: rupture life, the Larson-Miller parameter, the Monkman-Grant
cross-check, the time to 1 percent creep strain or any accumulated
creep strain at a sustained stress, and the design-life margin verdict
of a constant-stress part (structures/materials/creep-rupture owns the
constant-stress rupture vein and its LMP/MG machinery); steady-state
creep rate as a standalone product or the creep-rate-at-a-given-stress
question as a claim surface (creep-rupture, which this leaf consumes
internally only); cyclic endurance and creep-fatigue interaction (the
structures/fatigue pack owns cyclic life methods and the wave-46
creep-fatigue decline stands); constrained-expansion thermal stress
(structures/thermal-structures/thermal-stress-analysis); the
room-temperature elastic-plastic curve (ramberg-osgood); crack-driven
failure (fracture-toughness, crack-tip-plasticity-correction);
statistically based tensile design values (mmpsd-allowables);
temperature limits and alloy-family screening (material-selection);
MMPDS design-value tables (never reproduced, reference-only). Primary
creep is neglected (steady-state Norton creep only), the same
documented conservative assumption the creep-rupture sibling makes;
the stress relaxes monotonically, so the steady-state-only model
overestimates the retained preload early and converges to the
steady-state answer as primary creep exhausts. The elastic modulus E
is the material's high-temperature modulus at the operating point, an
input constant, never derived.

## Model (implement exactly)

Pure stdlib, math only, closed form, deterministic, no RNG. Module
constants:

- R_GAS = 8.314 (J/mol/K, the gas constant).
- MATERIALS = {"inconel-718": {"norton_a": 2.0e-47, "norton_n": 7.0,
  "norton_q": 360000.0, "elastic_modulus": 2.1e11}}; the reference-only
  typicals A = 2.0e-47, n = 7.0, Q = 360000 J/mol are the SAME
  Inconel-718 class values the creep-rupture sibling uses (its
  MATERIALS dict at this HEAD, so both leaves answer consistently on
  the same part), plus the elastic modulus E = 2.1e11 Pa that the
  relaxation ODE needs and creep-rupture does not.
- DEFAULT_MATERIAL = "inconel-718".

Defining relations (pin exactly; every function derives from them):

- Relaxation rate coefficient: K = E * A * exp(-Q / (R * T)), units
  Pa^(1-n) / s, from d(sigma)/dt = -K * sigma^n (the Norton creep rate
  eps_dot = A * sigma^n * exp(-Q / (R * T)) unloading the elastic
  strain at fixed total strain, d(sigma)/dt = -E * eps_dot).
- Power-law branch (n != 1): the separable ODE integrates to
  sigma^(1-n) = sigma_0^(1-n) + (n - 1) * K * t, i.e.
  sigma(t) = [sigma_0^(1-n) + (n - 1) * K * t]^(1 / (1 - n)).
  For n > 1 and t >= 0 the base is strictly positive (sigma_0 > 0) so
  the power is well defined; sigma(0) = sigma_0 and sigma decays
  monotonically with the long-time tail sigma ~
  [(n - 1) * K * t]^(1/(1-n)) = const * t^(-1/(n-1)) toward zero.
- Linear branch (n = 1): d(sigma)/dt = -K * sigma with the same K,
  sigma(t) = sigma_0 * exp(-K * t); this is the n -> 1 limit of the
  power branch (identity tested below).
- Retained fraction: f(t) = sigma(t) / sigma_0 in (0, 1] for n >= 1.
- Time to a retained fraction f: invert the closed form,
  t(f) = sigma_0^(1-n) * (f^(1-n) - 1) / ((n - 1) * K) for n != 1 and
  t(f) = -ln(f) / K for n = 1. Monotone: smaller f needs longer t.
- Margin: margin = retained_fraction / required_fraction - 1, verdict
  PASS when margin >= 0 (the creep-rupture margin convention,
  available / required - 1).

Functions:

- relaxed_stress(sigma_0, time_s, temp_k, material=DEFAULT_MATERIAL)
  -> float, the relaxed stress in Pa after time_s seconds of fixed-
  total-strain relaxation from sigma_0. Raises ValueError on
  non-positive sigma_0 or temp_k, negative time_s, a stress exponent
  below 1 (n < 1 makes the power-branch base cross zero at finite
  time; the module contract is n >= 1), or an unknown material.
- retained_fraction(sigma_0, time_s, temp_k, material=DEFAULT_MATERIAL)
  -> float in (0, 1], sigma(t) / sigma_0. Same ValueErrors.
- time_to_relaxed_fraction(fraction, sigma_0, temp_k,
  material=DEFAULT_MATERIAL) -> float, seconds for the stress to decay
  to `fraction` of sigma_0. Raises ValueError on fraction outside
  (0, 1], non-positive sigma_0 or temp_k, a stress exponent below 1,
  or an unknown material.
- preload_margin(sigma_0, time_s, temp_k, required_fraction,
  material=DEFAULT_MATERIAL) -> dict {"retained_fraction",
  "margin", "verdict"}: the retained fraction at the hold time, the
  margin retained / required - 1, and "PASS" when the margin is >= 0
  else "FAIL". Raises ValueError on required_fraction outside (0, 1]
  and the same non-physical-input rejections as retained_fraction.

Material handling mirrors the creep-rupture sibling: a string name
must be a key of MATERIALS (ValueError otherwise, listing the known
names); a dict is merged over the default alloy constants so any
subset of A, n, Q and E can be overridden (the dict keys are
norton_a, norton_n, norton_q, elastic_modulus). Units: stress in Pa,
temperature in K (Celsius plus 273.15), time in seconds; hold times in
hours in the worked text convert by 3600. All functions raise
ValueError on non-positive stress, temperature or required fraction,
on negative time, on a fraction or exponent outside the stated range,
and on an unknown material; relaxed_stress and retained_fraction
accept time_s = 0 and return sigma_0 exactly (limit check).

## Identities to test (closed form, checkable without the module)

- Zero hold time: relaxed_stress(sigma_0, 0.0, T) = sigma_0 exactly
  (the power base at t = 0 is sigma_0^(1-n), raised to 1/(1-n)
  recovers sigma_0). Real anchor: relaxed_stress(2.0e8, 0.0, 973.15)
  = 199999999.9999998 Pa.
- Initial relaxation rate: differentiating the closed form at t = 0
  gives d(sigma)/dt | 0 = -E * eps_dot(sigma_0, T), i.e. the stress
  first falls at exactly the elastic rate the Norton creep strain
  would accumulate: sigma(dt) - sigma_0 ~ -E * A * sigma_0^n *
  exp(-Q / (R * T)) * dt for small dt. Real anchor: at 200 MPa and
  700 C the initial creep rate eps0 = 1.2140624548073926e-08 1/s, so
  E * eps0 = 2549.5311550955244 Pa/s, and the module's 1 ms finite
  difference matches this within 1e-6 relative.
- n = 1 exponential limit: as n -> 1 the power branch tends to
  sigma_0 * exp(-K * t). Real anchor: the override dict
  {"norton_a": 5.0e-16, "norton_n": 1.0 + 1e-9, "norton_q": 0.0} at
  200 MPa and 600 C for 1e4 s gives 69987546.61987615 Pa against the
  exact exponential 69987549.82223107 Pa, within 1e-6 relative (the
  epsilon-perturbation gap, not a model error).
- Monotone decay: over the hold grid [0, 1e3, 1e4, 3.6e5, 3.6e6,
  3.6e7] s at 700 C the relaxed stress falls strictly at every step
  and stays positive; at 1e4 h (3.6e7 s) the retained fraction is
  0.26709127676828587, the t^(-1/6) power-law tail (n = 7) still
  positive, never zero in finite time.
- Temperature sensitivity: higher T relaxes faster (the exp(-Q/(RT))
  factor). Real anchors at 1000 h: 600 C retains 0.8482, 650 C
  retains 0.5820, 700 C retains 0.3918 (below).
- Round trip: relaxing for t(f) recovers exactly f * sigma_0: at 700 C
  the retained fraction after time_to_relaxed_fraction(0.8, ...) is
  0.8 within 1e-9.
- Margin boundary: required_fraction below the achieved retention
  PASSes and above it FAILs (never assert at exact equality; roundoff
  flips the verdict at the boundary).

## Worked example

A 200 MPa bolt preload (sigma_0 = 2.0e8 Pa) at fixed total strain in
the default Inconel-718 class alloy (A = 2.0e-47, n = 7.0,
Q = 360000 J/mol, E = 2.1e11 Pa) held at 700 C (973.15 K), the
temperature at which relaxation of this alloy is meaningful over
hours to days (at 600 C the same alloy retains 99.92 percent of the
preload after 1e4 s; relaxation lives at the hot operating point).

All values below are REAL outputs of the spec anchor
/tmp/w47spec/anchor_creep_stress_relaxation.py (pure stdlib, math
only, closed form, exit 0, no RNG, internal asserts all pass), run
once at spec time and quoted as printed:

- After 100 h (3.6e5 s): relaxed_stress(2.0e8, 3.6e5, 973.15) =
  114410840.82577138 Pa, retained fraction 0.5720542041288569: the
  preload has relaxed to 57.21 percent of its initial value.
- After 1000 h (3.6e6 s): relaxed_stress(2.0e8, 3.6e6, 973.15) =
  78364659.4406817 Pa, retained fraction 0.39182329720340847: 39.18
  percent retained, the 100 h to 1000 h drop (0.572 to 0.392) showing
  the slowing power-law tail, not a linear bleed.
- Time to relax to 90 percent of the preload at 700 C:
  time_to_relaxed_fraction(0.9, 2.0e8, 973.15) = 11527.301420325737 s
  = 3.202028172312705 h; to 80 percent: 36800.19442005393 s =
  10.222276227792758 h; to 50 percent: 823680.8543417541 s =
  228.80023731715391 h (9.53 days). Monotone: 3.2 h < 10.2 h < 228.8 h.
- Temperature sensitivity at the same 1000 h hold: 650 C (923.15 K)
  gives 116399871.02150063 Pa (0.5820 retained) and 600 C (873.15 K)
  gives 169638258.38946512 Pa (0.8482 retained), against 0.3918 at
  700 C: a 100 K slip from 700 C to 600 C nearly doubles the retained
  preload, the exp(-Q / (R * T)) Arrhenius sensitivity.
- Retained-preload margin after 1000 h at 700 C:
  preload_margin(2.0e8, 3.6e6, 973.15, 0.35) = {"retained_fraction":
  0.39182329720340847, "margin": 0.11949513486688135, "verdict":
  "PASS"} (39.18 percent retained against a 35 percent requirement);
  preload_margin(2.0e8, 3.6e6, 973.15, 0.45) = {"retained_fraction":
  0.39182329720340847, "margin": -0.12928156177020345, "verdict":
  "FAIL"} (against a 45 percent requirement the preload retention is
  short and the joint would need re-torque or a higher initial
  preload).
- Receipt magnitude cross-check (probe receipt gate (d) estimate: a
  200 MPa preload at 600 C relaxing to roughly a third after ~1e4 s
  with the creep-rupture default constants): the real closed form does
  NOT reproduce that estimate. relaxed_stress(2.0e8, 1.0e4, 873.15) =
  199844353.157 Pa, retained 0.99922: at 600 C the Inconel-718 class
  constants relax only 0.08 percent in 1e4 s (the 600 C Norton rate at
  200 MPa is ~7.4e-11 1/s, so E * eps ~ 15 Pa/s of stress decay). The
  gate estimate was an order-of-magnitude slip; the worked example
  above therefore runs at 700 C, where the anchor numbers are the
  physically verified magnitudes, and the spec pins the true 600 C
  behavior as a monotone-decay sanity case instead.
- Initial-rate identity: eps_dot(200 MPa, 700 C) =
  1.2140624548073926e-08 1/s and E * eps_dot = 2549.5311550955244
  Pa/s, so the stress first falls at ~2.55 kPa per second; the module
  finite difference over a 1 ms step matches within 1e-6 relative.
- n = 1 exponential branch (override dict {"norton_a": 5.0e-16,
  "norton_n": 1.0, "norton_q": 0.0}, so K = E * A = 1.05e-4 1/s):
  relaxed_stress(2.0e8, 1.0e3, 873.15) = 180064904.51725313 Pa and
  relaxed_stress(2.0e8, 1.0e4, 873.15) = 69987549.82223107 Pa,
  exactly sigma_0 * exp(-K * t) within 1e-12 relative.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w47spec/anchor_creep_stress_relaxation.py (stdlib math, closed
form, exit 0, no randomness, identical under both interpreters).

## Validation list (contract test must include)

1. Worked-example asserts within 1e-6 relative: relaxed_stress(2.0e8,
   3.6e5, 973.15) = 114410840.82577138; relaxed_stress(2.0e8, 3.6e6,
   973.15) = 78364659.4406817; retained_fraction at those points =
   0.5720542041288569 and 0.39182329720340847; the 600 C and 650 C
   1000 h cases = 169638258.38946512 and 116399871.02150063.
2. Time-to-fraction anchors within 1e-6 relative:
   time_to_relaxed_fraction(0.9, 2.0e8, 973.15) = 11527.301420325737,
   0.8 -> 36800.19442005393, 0.5 -> 823680.8543417541, and the three
   are strictly ordered 0.9 < 0.8 < 0.5.
3. Round trip: retained_fraction(2.0e8, t80, 973.15) = 0.8 within
   1e-9 where t80 is the 0.8 time; time_to_relaxed_fraction(f, ...) of
   a relaxed hold recovers f for f in {0.3, 0.5, 0.8, 0.95}.
4. Margin verdicts: preload_margin(2.0e8, 3.6e6, 973.15, 0.35) gives
   retained 0.39182329720340847, margin 0.11949513486688135, verdict
   PASS; required 0.45 gives margin -0.12928156177020345, verdict
   FAIL; required 0.39182329720340847 gives margin 0.0 (within 1e-12)
   and verdict PASS (margin >= 0 includes equality).
5. Zero-hold-time and initial-rate identities:
   relaxed_stress(2.0e8, 0.0, 973.15) = 2.0e8 within 1e-6 relative;
   the finite difference (relaxed_stress(sigma_0, 1e-3, T) -
   sigma_0) / 1e-3 equals -E * A * sigma_0^n * exp(-Q / (R * T)) at
   200 MPa and 700 C (E * eps0 = 2549.5311550955244 Pa/s) within
   1e-6 relative.
6. Monotone decay: relaxed stress falls strictly over the grid
   [0, 1e3, 1e4, 3.6e5, 3.6e6, 3.6e7] s at 700 C, every value
   positive, and the 1e4 h retained fraction
   0.26709127676828587 sits in (0.2, 0.4): the power-law tail never
   reaches zero in finite time.
7. n = 1 branch: with {"norton_a": 5.0e-16, "norton_n": 1.0,
   "norton_q": 0.0}, relaxed_stress(2.0e8, t, 873.15) equals
   sigma_0 * exp(-1.05e-4 * t) within 1e-12 relative at t in
   {1e3, 1e4, 3.6e5}; the n -> 1 limit {"norton_n": 1.0 + 1e-9}
   matches the exponential within 1e-6 relative at 1e4 s
   (69987546.61987615 vs 69987549.82223107, the perturbation gap).
8. Material override and default parity: the dict override
   {"norton_a": 2.0e-47, "norton_n": 7.0, "norton_q": 360000.0,
   "elastic_modulus": 2.1e11} reproduces the default alloy numbers
   within 1e-12 relative; the default creep rate at 300 MPa and 600 C
   inside this module (A * sigma^n * exp(-Q / (R * T))) equals the
   creep-rupture sibling anchor 1.2698242552930268e-09 1/s within
   1e-6 relative, proving the shared constant set.
9. Temperature monotonicity: retained fraction after 1000 h falls as
   T rises over [873.15, 923.15, 973.15, 1023.15] K (600 C 0.8482,
   650 C 0.5820, 700 C 0.3918, 750 C lower still), and rises with
   sigma_0 at fixed T and t (higher preload relaxes slower in
   relative terms for n > 1).
10. All ValueErrors enumerated above raise from the named public
    function with the real message shape: non-positive sigma_0 or
    temp_k ("initial stress must be > 0 Pa, got ...", "temperature
    must be > 0 K, got ..."), negative time_s ("hold time must be >=
    0 s, got ..."), fraction or required_fraction outside (0, 1]
    ("retained fraction must be in (0, 1], got ...", "required
    fraction must be in (0, 1], got ..."), stress exponent below 1
    ("stress exponent must be >= 1 for the relaxation closed form,
    got ..."), and an unknown material name ("unknown material ...
    known: inconel-718").
11. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math;
    module constants R_GAS = 8.314 and the MATERIALS/DEFAULT_MATERIAL
    block fixed as above. No exact-float equality on computed sums;
    use assertAlmostEqual/math.isclose everywhere.
12. Run the deterministic contract test offline (no network); it
    exits 0. Test passes under BOTH interpreters (/usr/bin/python3
    3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave47-creep-stress-relaxation.yaml)

Query 1 (copy verbatim):
  "compute the creep-stress-relaxation of the 200 MPa bolt preload held
  at 600 C for 10000 seconds with the norton-relaxation closed form:
  the relaxed stress from the fixed-strain rate-law integral, the
  retained-preload fraction and the preload-retention margin"
  intent: "structures/materials; creep-stress-relaxation: the relaxed
  stress of the 200 MPa bolt preload after the hold time from the
  fixed-total-strain norton-relaxation closed-form integral of
  d(sigma)/dt = -E*A*sigma^n*exp(-Q/(R*T)), the retained-preload
  fraction sigma/sigma_0 and the preload-retention margin against the
  required retained fraction"
  expected_skill: "structures/materials/creep-stress-relaxation"
Query 2 (copy verbatim):
  "find the stress-relaxation time for the titanium fastener preload to
  decay to 80 percent of its initial value at the elevated temperature
  with the norton-power-law relaxation equation, and report the
  remaining preload after the design hold time"
  intent: "structures/materials; creep-stress-relaxation: the time for
  the fastener preload to relax to 80 percent of its initial value
  from the inverted norton-power-law relaxation closed form at the
  elevated temperature, and the remaining preload after the design
  hold time"
  expected_skill: "structures/materials/creep-stress-relaxation"
Task ids: w47-creep-stress-relaxation-1 and -2. Spec-time grep (run
fresh by the probe): each of the tokens stress-relaxation,
creep-stress-relaxation, norton-relaxation, preload-retention,
retained-preload and fixed-strain-creep-relaxation returns ZERO
matches in every skills/ SKILL.md and ZERO of the 1286 task blocks in
eval/hit1-corpus.yaml, and the existing creep corpus tasks route on
larson-miller-parameter, norton-creep-law, steady-state-creep-rate,
monkman-grant, rupture-life and accumulated-creep-strain tokens for
the CONSTANT-stress life question, none of which carry fixed-strain
decay content, so the queries are collision-free in both directions.
Add one routing line to creep-rupture at build time pointing
preload-decay and fixed-strain relaxation questions at this leaf (the
wave-46 crack-tip-plasticity-correction routing-line precedent).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the stress relaxation
of a preloaded metallic part held at fixed total strain at elevated
temperature:" and include the outputs in the Claim order (the relaxed
stress after the hold time from the Norton power-law relaxation closed
form, the retained-preload fraction, the time to relax to a given
fraction of the preload, and the retained-preload margin verdict),
then close with the Trigger list. Refer to the fixed-strain relaxation
as creep-stress-relaxation and its equation as the
norton-relaxation-closed-form throughout; never claim a creep rate,
rupture life, LMP, Monkman-Grant, accumulated creep strain, or
constant-stress life verdict as a product (creep-rupture owns the
constant-stress vein), never claim cyclic endurance or creep-fatigue
interaction, and never reproduce MMPDS or FAR-25 text (reference-only).
Metadata tags EXACTLY as the probe receipt gate (f) lists them,
nothing else: creep-stress-relaxation, norton-relaxation-closed-form,
preload-retention, fixed-strain-creep-relaxation,
relaxed-stress-fraction, elevated-temperature-preload. 50-150 words,
<=1000 chars, action verb present. Recommended wording (measured at
spec time):

"Use when you must compute the stress relaxation of a preloaded
metallic part held at fixed total strain at elevated temperature:
evaluate the closed-form integral of the fixed-strain relaxation ODE
for a Norton power-law creeping material, the relaxed stress sigma(t)
= [sigma_0^(1-n) + (n-1)*A*E*t*exp(-Q/(R*T))]^(1/(1-n)) from the
initial preload stress, the hold time, the temperature and the Norton
constants A, n, Q and elastic modulus E, the retained-preload
fraction after the hold, the time for the preload to relax to a target
fraction, and the preload-retention margin against a required retained
fraction with the PASS or FAIL verdict for bolted joints, spring
preloads and interference-fit fasteners. Produces the relaxed stress,
the retained-preload fraction and the retention margin verdict at the
operating point. Trigger: creep-stress-relaxation,
norton-relaxation-closed-form, preload-retention,
fixed-strain-creep-relaxation, relaxed-stress-fraction,
elevated-temperature-preload."

FORBIDDEN TOKENS (belong to creep-rupture, the fatigue pack, or the
adjacent materials leaves): rupture-life, larson-miller-parameter,
monkman-grant, stress-rupture, rupture, creep-rate-as-product,
steady-state-creep-rate claim surface, accumulated-creep-strain,
time-to-one-percent-creep, creep-fatigue, cyclic-endurance,
strain-life, fatigue-interaction, constrained-expansion,
elastic-plastic-curve, ramberg-osgood, yield-strength, fracture,
stress-intensity, crack-tip, plastic-zone, design-values, a-basis,
b-basis, temperature-limit screening, alloy-selection; never the bare
single words creep, stress, relaxation, rate, life, fatigue, or
temperature as standalone metadata tags (all are sibling-owned or too
generic). Standards are reference-only (mmpsd, far-25), never
reproduced.

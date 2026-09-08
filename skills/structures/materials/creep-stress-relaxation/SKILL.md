---
name: creep-stress-relaxation
description: "Use when you must compute the stress relaxation of a preloaded metallic part held at fixed total strain at elevated temperature: evaluate the closed-form integral of the fixed-strain relaxation ODE for a Norton power-law creeping material, the relaxed stress sigma(t) = [sigma_0^(1-n) + (n-1)*A*E*t*exp(-Q/(R*T))]^(1/(1-n)) from the initial preload stress, the hold time, the temperature and the Norton constants A, n, Q and elastic modulus E, the retained-preload fraction after the hold, the time for the preload to relax to a target fraction, and the preload-retention margin against a required retained fraction with the PASS or FAIL verdict for bolted joints, spring preloads and interference-fit fasteners. Produces the relaxed stress, the retained-preload fraction and the retention margin verdict at the operating point. Trigger: creep-stress-relaxation, norton-relaxation-closed-form, preload-retention, fixed-strain-creep-relaxation, relaxed-stress-fraction, elevated-temperature-preload."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: materials
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: materials
  tags: [creep-stress-relaxation, norton-relaxation-closed-form, preload-retention, fixed-strain-creep-relaxation, relaxed-stress-fraction, elevated-temperature-preload]
  version: 0.1.0
  author: Aero Agent Skills
---

# Creep Stress Relaxation (structures/materials/creep-stress-relaxation)

Use when the task is the fixed-total-strain stress decay of a preloaded
metallic element (a bolted joint preload, a spring preload or an
interference-fit fastener) held at elevated temperature: the relaxed
stress after the hold from the closed-form integral of the relaxation
ODE d(sigma)/dt = -E * eps_dot under Norton power-law creep, the
retained-preload fraction, the time to relax to a target fraction of
the preload, and the retained-preload margin check against a required
retained fraction with the PASS/FAIL verdict. This leaf implements the
deterministic closed-form algebra in pure Python, stdlib only. It pairs
with structures/materials/creep-rupture, which owns the constant-stress
vein: a preload held at fixed total strain relaxes here, while a part
under a sustained stress with accumulated creep strain, rupture-life
and design-life margin questions stays with creep-rupture. The
fixed-strain decay this leaf computes has no function in the
constant-stress sibling, whose creep accumulation eps_c = eps_dot * t
cannot answer how sigma falls while the total strain is held. Adjacent
fences: structures/thermal-structures/thermal-stress-analysis owns the
constrained-expansion load side of the elevated-temperature
environment, and the structures/fatigue pack owns cyclic endurance and
creep-fatigue interaction. This leaf does NOT cover rupture life, the
Larson-Miller parameter, the Monkman-Grant cross-check, time to 1
percent creep strain or accumulated creep strain at a sustained stress
(all constant-stress products of creep-rupture), statistically based
tensile design values (structures/materials/mmpsd-allowables), or the
room-temperature elastic-plastic curve (ramberg-osgood).

## Domain quick reference

- Fixed-strain relaxation ODE: with the total strain held constant the
  elastic strain unloads one-for-one into creep strain,
  d(sigma)/dt = -E * eps_dot, so under the Norton law eps_dot =
  A * sigma^n * exp(-Q / (R * T)) the stress obeys
  d(sigma)/dt = -K * sigma^n with the relaxation rate coefficient
  K = E * A * exp(-Q / (R * T)) in Pa^(1-n) / s (A in 1/s per Pa^n, n
  the stress exponent, Q the activation energy in J/mol, R = 8.314
  J/mol/K, E the high-temperature elastic modulus in Pa, T in K).
- Power-law branch (n != 1): the separable ODE integrates in closed
  form to sigma(t) = [sigma_0^(1-n) + (n - 1) * K * t]^(1 / (1 - n));
  sigma(0) = sigma_0 and for n > 1 the stress decays monotonically with
  the long-time tail sigma ~ [(n - 1) * K * t]^(1/(1-n)) toward zero,
  never reaching it in finite time.
- Linear branch (n = 1): sigma(t) = sigma_0 * exp(-K * t), the n -> 1
  limit of the power branch (Newtonian viscous relaxation).
- Retained fraction: f(t) = sigma(t) / sigma_0 in (0, 1] for n >= 1.
- Time to a retained fraction f: t(f) = sigma_0^(1-n) * (f^(1-n) - 1)
  / ((n - 1) * K) for n != 1 and t(f) = -ln(f) / K for n = 1; smaller
  f needs longer t.
- Retained-preload margin: margin = retained / required - 1 with the
  verdict PASS when the margin is >= 0 (the available / required - 1
  convention shared with the creep-rupture margin checks).
- Units: stress in Pa (MPa times 1e6), temperature in K (Celsius plus
  273.15), time in seconds (hold times in hours convert by 3600). All
  functions raise ValueError on non-positive stress, temperature or
  required fraction, on negative time, on a fraction outside (0, 1], on
  a stress exponent below 1, or on an unknown material name.

## Workflow

1. Fix the operating point: the initial preload stress sigma_0 in Pa
   (convert MPa by multiplying by 1e6), the metal temperature T in K
   (Celsius plus 273.15) and the hold time in seconds (hours times
   3600). Select the material: pass the registered name
   "inconel-718" (the default, reference-only typicals A = 2.0e-47,
   n = 7.0, Q = 360000 J/mol, E = 2.1e11 Pa shared with the
   creep-rupture sibling, plus the modulus this ODE needs) or a dict of
   overrides on top of the default alloy with any subset of keys
   norton_a, norton_n, norton_q and elastic_modulus.
2. Compute the relaxed stress after the hold with
   relaxed_stress(sigma_0, time_s, temp_k, material): the closed-form
   integral of the fixed-strain relaxation ODE, the power-law branch
   for n != 1 and the exponential branch for n = 1. A zero hold time
   returns sigma_0 exactly.
3. Read the retained-preload fraction with retained_fraction(sigma_0,
   time_s, temp_k, material): sigma(t) / sigma_0, the preload-retention
   fraction in (0, 1].
4. Find the time for the preload to relax to a target fraction of its
   initial value with time_to_relaxed_fraction(fraction, sigma_0,
   temp_k, material): the inverted closed form in seconds, for example
   the time to 80 percent of the preload for a fastener joint.
5. Run the retained-preload margin check with preload_margin(sigma_0,
   time_s, temp_k, required_fraction, material): it returns the
   retained fraction at the hold time, the margin
   retained / required - 1 and the verdict PASS when the margin is
   >= 0 else FAIL. PASS means the joint holds the required retention
   through the design hold; FAIL means re-torque, a higher initial
   preload or a cooler operating point is needed.
6. Read the result with the model assumptions in view: steady-state
   Norton creep only (primary creep is neglected, the same documented
   conservative assumption the creep-rupture sibling makes; the stress
   relaxes monotonically, so the model overestimates the retained
   preload early and converges as primary creep exhausts), and the
   power-law tail for n > 1 (sigma ~ t^(-1/(n-1)), strictly positive
   after any finite hold).
7. Confirm the deterministic checks with the contract test
   scripts/test_creep_stress_relaxation.py.

## Worked example

A 200 MPa bolt preload (sigma_0 = 2.0e8 Pa) at fixed total strain in
the default Inconel-718 class alloy held at 700 C (973.15 K), the hot
operating point where relaxation of this alloy is meaningful over hours
to days. All values are real outputs of the module:

- After 100 h (3.6e5 s): relaxed_stress(2.0e8, 3.6e5, 973.15) =
  114410840.82577138 Pa, retained fraction 0.5720542041288569: the
  preload has relaxed to 57.21 percent of its initial value.
- After 1000 h (3.6e6 s): relaxed_stress(2.0e8, 3.6e6, 973.15) =
  78364659.4406817 Pa, retained 0.39182329720340847: 39.18 percent
  retained, the 100 h to 1000 h drop showing the slowing power-law
  tail, not a linear bleed.
- Time to relax to 90 percent of the preload at 700 C:
  time_to_relaxed_fraction(0.9, 2.0e8, 973.15) = 11527.301420325737 s
  = 3.202 h; to 80 percent: 36800.19442005393 s = 10.222 h; to 50
  percent: 823680.8543417541 s = 228.800 h (9.53 days). Monotone:
  3.2 h < 10.2 h < 228.8 h.
- Temperature sensitivity at the same 1000 h hold: 650 C (923.15 K)
  gives 116399871.02150063 Pa (0.5820 retained) and 600 C (873.15 K)
  gives 169638258.38946512 Pa (0.8482 retained) against 0.3918 at
  700 C: a 100 K slip from 700 C to 600 C nearly doubles the retained
  preload, the exp(-Q / (R * T)) Arrhenius sensitivity.
- Retained-preload margin after 1000 h at 700 C:
  preload_margin(2.0e8, 3.6e6, 973.15, 0.35) = {"retained_fraction":
  0.39182329720340847, "margin": 0.11949513486688135, "verdict":
  "PASS"} (39.18 percent retained against a 35 percent requirement);
  preload_margin(2.0e8, 3.6e6, 973.15, 0.45) = {"retained_fraction":
  0.39182329720340847, "margin": -0.12928156177020345, "verdict":
  "FAIL"} (against a 45 percent requirement the joint needs re-torque
  or a higher initial preload).
- Initial rate identity: at 200 MPa and 700 C the initial creep rate is
  1.2140624548073926e-08 1/s, so E * eps_dot = 2549.5311550955244 Pa/s
  and the stress first falls at about 2.55 kPa per second; the module
  finite difference over a 1 ms step matches within 1e-6 relative.
- Newtonian branch: with the override dict {"norton_a": 5.0e-16,
  "norton_n": 1.0, "norton_q": 0.0} (K = E * A = 1.05e-4 1/s),
  relaxed_stress(2.0e8, 1.0e4, 873.15) = 69987549.82223107 Pa, exactly
  sigma_0 * exp(-K * t) within 1e-12 relative.
- 600 C sanity: relaxed_stress(2.0e8, 1.0e4, 873.15) =
  199844353.157 Pa, retained 0.99922: at 600 C the alloy relaxes only
  0.08 percent in 1e4 s, which is why the worked example lives at
  700 C.

## Pitfalls

- Confusing this leaf with the constant-stress sibling: creep-rupture
  accumulates creep strain at a sustained stress and reports rupture
  life and design-life margins; this leaf answers how a preload decays
  at fixed total strain. The fixed-strain decay question has no
  function in creep-rupture's constant-stress machinery, and the
  constant-stress life products are not claimed here.
- Running the relaxation check at a cool operating point: at 600 C the
  default alloy retains 99.92 percent of the preload after 1e4 s, so a
  room-temperature or mildly elevated check misses the failure mode
  entirely; the relaxation check lives at the hot operating point
  (700 C in the worked example) where the decay is meaningful over
  hours to days.
- Mixing units in the input chain: stress enters in Pa (convert MPa by
  1e6), temperature in K (Celsius plus 273.15) and time in seconds
  (hold times in hours convert by 3600); a seconds-versus-hours slip
  misreads the relaxation by 3600x.
- Forgetting the modulus is an input: E is the high-temperature elastic
  modulus of the material at the operating point, an input constant
  (2.1e11 Pa for the default alloy); it is never derived from the
  stress-strain curve here.
- Overriding the material carelessly: a dict override merges over the
  default alloy, so a partial override (for example only norton_n)
  silently keeps the other Inconel-718 class constants; quoting the
  defaults for another alloy is a material-data error.
- Reading the verdict without the steady-state-only assumption: the
  model overestimates the retained preload early because primary creep
  is neglected; the margin is conservative in the direction of the
  retained preload only as the creep exhausts.
- Treating the module material as an alloy database: the Inconel-718
  class constants are reference-only typicals shared with the
  creep-rupture sibling; production preload-retention margins need
  measured alloy data.

## Verification

- Confirm relaxed_stress(2.0e8, 3.6e5, 973.15) returns
  114410840.82577138 Pa and relaxed_stress(2.0e8, 3.6e6, 973.15)
  returns 78364659.4406817 Pa, with retained fractions 0.5720542041288569
  and 0.39182329720340847; the 600 C and 650 C 1000 h cases return
  169638258.38946512 and 116399871.02150063 Pa.
- Confirm time_to_relaxed_fraction(0.9, 2.0e8, 973.15) returns
  11527.301420325737 s, 0.8 -> 36800.19442005393 s and
  0.5 -> 823680.8543417541 s, strictly ordered, and the round trip:
  relaxing for the time computed for a fraction f and reading the
  retained fraction recovers f within 1e-9 for f in {0.3, 0.5, 0.8,
  0.95}.
- Confirm preload_margin(2.0e8, 3.6e6, 973.15, 0.35) returns margin
  0.11949513486688135 with verdict PASS and the 0.45 requirement
  returns margin -0.12928156177020345 with verdict FAIL; a required
  fraction equal to the achieved retention gives margin 0.0 and PASS
  (never assert at exact equality at the boundary).
- Confirm the decay identities: a zero hold returns sigma_0 within 1e-6
  relative; the 1 ms finite difference matches -E * A * sigma_0^n *
  exp(-Q / (R * T)) = -2549.5311550955244 Pa/s within 1e-6 relative;
  the n = 1 branch matches sigma_0 * exp(-K * t) within 1e-12 relative
  and the n = 1 + 1e-9 power branch matches the exponential within 1e-6
  relative.
- Confirm monotone decay over the grid [0, 1e3, 1e4, 3.6e5, 3.6e6,
  3.6e7] s at 700 C (strictly falling, every value positive, the 1e4 h
  retained fraction 0.26709127676828587 in (0.2, 0.4)), that the
  retained fraction after 1000 h falls as T rises over [873.15,
  923.15, 973.15, 1023.15] K, and that for n > 1 a higher preload
  relaxes to a lower retained fraction at fixed T and t (100 MPa 0.757,
  200 MPa 0.392, 400 MPa 0.196), the closed-form consequence of the
  sigma_0-independent power-law tail.
- Confirm the material handling: the dict override reproducing the
  default constants gives identical numbers within 1e-12 relative, and
  the shared constant set is proven by the default alloy Norton rate at
  300 MPa and 600 C equaling the creep-rupture sibling anchor
  1.2698242552930268e-09 1/s within 1e-6 relative.
- Confirm every non-positive stress, temperature or required fraction,
  every fraction outside (0, 1], every negative hold time, every stress
  exponent below 1 and every unknown material name raises ValueError.
- Run the contract test offline: python3
  scripts/test_creep_stress_relaxation.py (42 tests, deterministic,
  passes under both the system python3 and the pyenv 3.13.12
  interpreter).

## Related leaves

- structures/materials/creep-rupture: the constant-stress owner in this
  pack; sustained-stress creep rate, accumulated creep strain, rupture
  life and design-life margin questions route there, and this leaf
  consumes the shared Inconel-718 class Norton constants internally.
- structures/thermal-structures/thermal-stress-analysis: the
  constrained-expansion load side of the same elevated-temperature
  environment (owned by that leaf, not here).
- structures/materials/ramberg-osgood: the room-temperature
  elastic-plastic curve beneath the creep regime.
- structures/materials/fracture-toughness and
  structures/materials/crack-tip-plasticity-correction: the crack-driven
  failure modes that compete with preload decay in hot fasteners.
- structures/materials/material-selection: temperature limits and alloy
  family screening before the preload-retention check.
- structures/fatigue/stress-life-curve and structures/fatigue/strain-
  life-fatigue: cyclic life methods, the non-creep route for the same
  part (creep-fatigue interaction stays with the fatigue pack).

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_creep_stress_relaxation.py

The test covers the worked-example anchors (100 h relaxed stress
114410840.82577138 Pa retained 0.5721, 1000 h 78364659.4406817 Pa
retained 0.3918, the 600 C and 650 C cases, the 0.9/0.8/0.5
time-to-fraction anchors 11527.30 / 36800.19 / 823680.85 s), the round
trips recovering each target fraction, the margin verdicts at the 0.35
PASS and 0.45 FAIL requirements and the equality boundary, the zero
hold time and initial-rate identities, the monotone decay grid and the
1e4 h power-law tail, the n = 1 exponential branch and the n -> 1
limit, temperature and preload monotonicity, material dict overrides
and the shared-constant parity with creep-rupture, and ValueError
rejection of non-physical inputs and unknown materials.

## Compliance

- Standards referenced, not reproduced: MMPDS documents elevated-
  temperature creep and relaxation design practice for metallic
  airframe materials; FAR-25 frames the elevated-temperature part and
  its strength demonstration. The equations above are standard
  engineering methodology, summary-only per standards-map.yaml, and the
  material constants are reference-only typicals, not a reproduced data
  table.
- compliance: STANDARDS-REF, gated: false.

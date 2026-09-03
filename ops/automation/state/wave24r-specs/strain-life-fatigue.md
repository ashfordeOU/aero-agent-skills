# Wave-24R leaf spec: strain-life-fatigue (structures, headroom)

- Path: skills/structures/fatigue/strain-life-fatigue/
- Pack: fatigue (existing: goodman-diagram, load-spectrum-counting,
  miner-damage, notch-sensitivity, stress-life-curve)
- Standards ids: far-25, cs-25, mmpsd  (Ledger Standard: far-25, mmpsd)
- Family: structures

## Claim

Strain-life (low-cycle fatigue) analysis with the Coffin-Manson
relation: fit or apply the elastic and plastic strain amplitude curves
against reversals to failure, compute the total strain amplitude at a
given life and the life at a given strain amplitude, apply the Neuber
rule to convert a nominal elastic stress into the local elastic-plastic
strain at a notch, and compare stress-life (high-cycle) with
strain-life (low-cycle) regimes to give the fatigue-life verdict for a
load point. Produces the reversals/cycles to failure, the Neuber local
strain, and the regime classification.

Does NOT do: the S-N high-cycle curve fit and endurance limit
(stress-life-curve owns Basquin S-N fitting), the fatigue notch factor
for the endurance check (notch-sensitivity owns k_f from k_t and
material sensitivity q), mean-stress correction diagrams
(goodman-diagram), damage accumulation across a spectrum
(miner-damage, load-spectrum-counting). This leaf is the LOW-cycle
strain-life method with the Neuber local-strain conversion as its notch
bridge.

## Model (implement exactly)

Coffin-Manson (total strain amplitude vs reversals 2N_f):
- Elastic term: eps_e = (sigma_f_prime / E) * (2*N_f)^b
- Plastic term: eps_p = eps_f_prime * (2*N_f)^c
- Total: eps_a = eps_e + eps_p = (sigma_f_prime/E)*(2N_f)^b +
  eps_f_prime*(2N_f)^c
with fatigue strength coefficient sigma_f_prime (Pa), fatigue strength
exponent b (negative), fatigue ductility coefficient eps_f_prime
(dimensionless), fatigue ductility exponent c (negative), modulus E
(Pa). Module constant table for common aerospace alloys (reference-only
typical values, state them as typical): e.g. 2024-T3 aluminum:
sigma_f_prime ~ 660 MPa? (state the exact typical value you use and the
source note "typical published value, reference-only"), b ~ -0.12? use
consistent published typicals: 2024-T3 sigma_f' = 660 MPa? Common: 2024-
T3: sigma_f' ~ 662 MPa? Keep it simple: aluminum 2024-T351:
sigma_f' = 927? Do NOT overclaim precision: give one representative
set: 7075-T6 aluminum sigma_f_prime 826 MPa? Provide the values YOU
will assert in tests; label them reference-only typicals for a
representative aluminum alloy and an aerospace steel. Simplify: allow
the user to input all four constants with the defaults being the
representative aluminum set:
  Aluminum 7075-T6 (typical, reference-only): sigma_f_prime = 730 MPa?
  Use internally consistent values that make the test numbers clean.
  You MUST compute your own worked-example numbers from your module and
  assert them; the module constants are what make them reproducible.
- Life from strain: invert eps_a = ... for 2N_f by bisection on
  log(2N_f) over a wide bracket (deterministic; assert monotonic).
- Strain from life: direct evaluation.
- Transition life: 2N_t where eps_e = eps_p (solve by bisection).
Regime classification: for the applied eps_a, if 2N_f < 2N_t the
failure is low-cycle (plastic-dominated), else high-cycle
(elastic-dominated). Report the regime string.
Neuber rule (local notch strain):
- Given the nominal elastic stress amplitude S (Pa) on the net section
  and the fatigue notch factor k_f (input; from notch-sensitivity leaf
  methods, but do NOT import other leaves - k_f is an input here), the
  local stress-strain satisfies
    sigma_loc * eps_loc = (k_f * S)^2 / E
  with the Ramberg-Osgood cyclic curve
    eps_loc = sigma_loc/E + (sigma_loc/K_prime)^(1/n_prime)
  Solve the pair by fixed-point or bisection on sigma_loc (deterministic)
  and return sigma_loc, eps_loc, and the elastic-plastic flag
  (plastic if eps_loc exceeds the elastic value sigma_loc/E by more
  than a small tolerance).
- Local strain amplitude -> life via the Coffin-Manson relation with
  eps_a = eps_loc (mean-stress correction documented as a stated
  assumption when the mean is zero; otherwise note that the leaf
  computes the fully-reversed life).
Functions:
- strain_amplitude(n_reversals, material) -> eps_a
- reversals_to_failure(eps_a, material) -> 2N_f (and cycles N_f)
- transition_reversals(material) -> 2N_t
- regime_classification(eps_a, material) -> str
- ramberg_osgood(sigma_loc, e, k_prime, n_prime) -> eps_loc
- neuber_local_strain(k_f, s_nominal, material) -> (sigma_loc, eps_loc,
  plastic_flag)
- strain_life_point(s_nominal, k_f, material, ...) -> summary dict
  (eps_loc, 2N_f, cycles, regime, verdict)
ValueError on: non-positive strain/stress/modulus, k_f < 1, unknown
material, non-finite inputs, n_prime outside (0,1), K_prime <= 0.

## Worked example

Representative aluminum alloy (your module constants; compute and quote
exact numbers in the SKILL):
- Fully reversed strain amplitude eps_a = 0.01: expect the life in the
  low-cycle regime (2N_f between 1e3 and 1e5 reversals for a typical
  aluminum; assert your value and the regime string).
- A high-cycle point eps_a = 0.002: life longer than the 0.01 point
  (monotonic; assert) and regime high-cycle when above 2N_t.
- Neuber: k_f = 2.5, S = 200 MPa on the aluminum: local eps_loc is
  larger than the nominal elastic eps = S/E; assert plastic_flag True
  when the local stress exceeds yield-scale (check with your constants)
  and assert the Neuber product identity sigma_loc*eps_loc =
  (k_f*S)^2/E within 1e-9 relative.
- Monotonicity: reversals_to_failure falls as eps_a rises (assert over
  5 points).
- Transition: at 2N_t the elastic and plastic amplitudes are equal
  (assert within 1e-6 relative).
- ValueError rejections.
Keep at least 18 test methods.

## Corpus tasks (2 tasks, ids w24r-strain-life-fatigue-1/2)

Distinctive tokens: strain-life, coffin-manson, low-cycle fatigue,
reversals to failure, neuber local strain, transition life. Avoid:
"s-n curve", "basquin", "endurance limit", "stress amplitude for
infinite life", "goodman" (stress-life/goodman/notch claims; the
neuber mention must always be paired with "local strain" or
"elastic-plastic" tokens, never "fatigue notch factor kf for the
endurance check").

1. "run the strain-life fatigue analysis for the notched lug under the
   fully reversed 0.8 percent strain amplitude: apply the Coffin-Manson
   curve to find the reversals to failure and classify the point as
   low-cycle or high-cycle against the transition life"
2. "convert the nominal 200 MPa elastic stress at the kt 2.5 notch into
   the Neuber local elastic-plastic strain with the cyclic
   Ramberg-Osgood curve and compute the Coffin-Manson low-cycle life
   for the representative aluminum alloy"

## SKILL body notes

Pair with stress-life-curve (high-cycle counterpart), notch-sensitivity
(k_f input source), miner-damage (damage accumulation over the variable
loads), goodman-diagram (mean stress). Worked example uses the module
constants and real outputs. Compliance: MMPDS/FAR damage tolerance
practice referenced by name, no reproduced tables.

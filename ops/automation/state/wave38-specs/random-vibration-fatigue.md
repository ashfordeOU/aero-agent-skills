# Wave-38 leaf spec: random-vibration-fatigue (structures, fatigue pack)

- Path: skills/structures/fatigue/random-vibration-fatigue/
- Pack: fatigue. Closest siblings: load-spectrum-counting (TIME-DOMAIN
  rainflow counting of a mission load history into an exceedance spectrum,
  then Miner on the counted spectrum), miner-damage (cumulative damage of
  a counted spectrum), stress-life-curve (Basquin S-N fitting and life
  prediction from amplitudes), random-vibration-analysis (structures/loads:
  SDOF response PSD, g-rms and 3-sigma response from Miles - it stops at
  the equivalent static response and does NO fatigue damage), goodman-
  diagram. Whole-tree grep: "Dirlik", "Wirsching", "narrow band fatigue",
  "spectral fatigue", "PSD moments" = ZERO owning hits in any leaf
  (random-vibration-analysis matches "narrow band" only as bandwidth
  language in the response PSD, not a damage method). ZERO owners of the
  spectral fatigue damage function. GENUINE STRUCT gap (fresh probe).
- Standards id: far-25 (reference-only); cs-25 reference-only (fatigue
  sibling convention). Ledger Standard: far-25,cs-25.
- Family: structures

## Claim

Estimate fatigue damage and life directly from a response power spectral
density: compute the spectral moments of the stress PSD, apply the
narrow-band Rayleigh amplitude model and the Dirlik amplitude probability
density to get the expected damage rate under a Basquin S-N curve, and
convert the damage rate to a fatigue life. Produces the spectral moments,
the expected peak rate, the damage rate by each model, and the fatigue
life verdict that gate random-vibration fatigue screening. Does NOT do:
rainflow counting of a time history (load-spectrum-counting); Miner
summation of a counted spectrum (miner-damage); S-N curve fitting
(stress-life-curve); g-rms and 3-sigma response without damage (random-
vibration-analysis).

## Model (implement exactly)

Conventions: the stress PSD G(f) is supplied as parallel arrays of
frequency (Hz) and one-sided PSD values (stress^2 / Hz, e.g. MPa^2/Hz).
Spectral moments m_n = sum(f_i^n * G_i * df) over the array (trapezoid
rule). Basquin relation N * S^m = A (S stress amplitude, A material
constant; input as A and m).

Module constant: GAMMA_FN = math.gamma (stdlib).

Functions (pure stdlib):
- psd_moments(freqs, psd) -> dict {m0, m1, m2, m4} by trapezoid
  integration. ValueErrors: empty arrays, mismatched lengths, negative
  frequency or PSD.
- expected_peak_rate(m0, m2, m4) -> float: sqrt(m4 / m2) (peaks per
  second).
- narrowband_damage_rate(m0, m2, m4, A, m) -> float:
  nu0 = sqrt(m2/m0); D = nu0 / A * (sqrt(2*m0))**m *
  gamma(1 + m/2) (Rayleigh amplitude closed form).
- dirlik_coefficients(m0, m1, m2, m4) -> dict {gamma, x_m, D1, D2, D3,
  Q, R}: the standard Dirlik parameter set (documented closed forms).
- dirlik_damage_rate(m0, m1, m2, m4, A, m) -> float: Ep * E[S^m] / A
  with Ep = sqrt(m4/m2) and E[S^m] = (sqrt(m0))**m * (D1 * Q**m *
  gamma(1+m) + 2**m * gamma(1 + m/2) * (D2 * |R|**m + D3)).
- fatigue_life_hours(damage_rate) -> float: 1.0 / (damage_rate * 3600).
  ValueError: damage_rate <= 0.
- random_vibration_fatigue(freqs, psd, A, m) -> dict {moments, peak_rate,
  nb_damage_rate, dirlik_damage_rate, nb_life_h, dirlik_life_h, verdict}
  where verdict prefers the Dirlik estimate (documented as the wider-band
  model) for the life check.
ValueErrors: A <= 0, m <= 0, m0 == 0 (no energy -> zero damage, allowed
and reported).

Identity to test: a flat PSD over [f1, f2] has m0 = G0 * (f2 - f1); m2 =
G0 * (f2**3 - f1**3)/3; m4 = G0 * (f2**5 - f1**5)/5 (the anchor check);
damage rate scales linearly with G0 (doubling G0 doubles m0 and the
narrow-band damage rate for fixed m); narrow-band damage rate exceeds the
Dirlik estimate on a narrow-band input (both converge as bandwidth
narrows).

## Worked example

Verified at prep: flat stress PSD G0 = 2.0 MPa^2/Hz over 10 to 100 Hz,
Basquin A = 1e12, m = 4:
- m0 = 180.0, m1 = 9900.0, m2 = 666000.0, m4 = 3.99996e9.
- peak rate Ep = 77.50 peaks/s.
- narrow-band: nu0 = 60.83; damage rate = 1.577e-5 per s; life =
  17.62 h.
- Dirlik coefficients: gamma 0.7849, x_m 0.7097, D1 0.1159, R 0.5483,
  D2 0.2494, D3 0.6347, Q 0.1449; damage rate = 5.281e-5 per s; life =
  5.26 h.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds from the closed-form spectral relations and
the Dirlik parameter set (independently evaluated by the anchor script at
prep).

## Validation list (contract test must include)

- Flat-PSD moment identities within 1 percent.
- Peak rate 77.50 within 1 percent on the anchor.
- Narrow-band damage rate 1.577e-5 within 2 percent; life 17.6 h.
- Dirlik damage rate 5.28e-5 within 5 percent (Dirlik coefficient
  formulas are sensitive; assert the coefficients D1/D2/D3 sum to 1 and
  the damage-rate anchor within 5 percent).
- D1 + D2 + D3 == 1 identity.
- Zero-energy PSD returns zero damage with no error.
- ValueErrors for non-physical inputs.
- Determinism.

## Corpus fragment (eval/hit1-wave38-random-vibration-fatigue.yaml)

Query 1 (copy verbatim):
  "estimate the random-vibration-fatigue damage rate and life from the response stress psd with the dirlik-method amplitude model"
  intent: "structures; spectral fatigue damage from a response PSD"
  expected_skill: "structures/fatigue/random-vibration-fatigue"
Query 2 (copy verbatim):
  "compute the narrow-band fatigue life from the psd spectral moments and the basquin S-N curve under base-excitation random vibration"
  intent: "structures; narrow band fatigue life from PSD moments"
  expected_skill: "structures/fatigue/random-vibration-fatigue"
Task ids: w38-random-vibration-fatigue-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate fatigue damage directly
from a random-vibration response PSD:" and include the outputs in the
Claim. First tag: random-vibration-fatigue. Additional tags ONLY:
dirlik-method, spectral-fatigue, narrow-band-damage, psd-spectral-moments,
expected-peak-rate, basquin-gamma-damage. NEVER single generic words
(fatigue, vibration, damage, spectrum, PSD, life, random). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): rainflow, exceedance spectrum,
level crossing (load-spectrum-counting); Miner sum, damage fraction
(miner-damage); S-N fit, endurance limit (stress-life-curve); g-rms,
3-sigma, transmissibility, Miles equation (random-vibration-analysis).

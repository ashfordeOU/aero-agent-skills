---
name: random-vibration-fatigue
description: "Use when you must estimate fatigue damage directly from a random-vibration response PSD: compute the psd-spectral-moments of a one-sided stress power spectral density by trapezoid integration, derive the expected-peak-rate, and apply the narrow-band Rayleigh model and the Dirlik amplitude mixture (dirlik-method) for the expected damage rate under a Basquin S-N curve with gamma closed forms; convert each damage rate to a fatigue life in hours. Produces the spectral moments, the expected peak rate, the narrow-band-damage and Dirlik damage rates, and the fatigue life verdict that gates random-vibration fatigue screening. Trigger: random vibration fatigue, spectral fatigue, Dirlik method, PSD moments, narrow band fatigue life, response stress PSD, peak rate."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: fatigue
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fatigue
  tags: [random-vibration-fatigue, dirlik-method, spectral-fatigue, narrow-band-damage, psd-spectral-moments, expected-peak-rate, basquin-gamma-damage]
  version: 0.1.0
  author: Aero Agent Skills
---

# Random Vibration Fatigue from a Stress PSD (structures/fatigue/random-vibration-fatigue)

Use when the task is estimating fatigue damage and life directly from a
random-vibration response power spectral density, without a time
history. This leaf computes the spectral moments of the one-sided
stress PSD, forms the expected peak rate, and applies the narrow-band
Rayleigh amplitude model and the Dirlik mixture model to get expected
damage rates under a Basquin S-N curve, then converts each rate into a
fatigue life in hours. It is the frequency-domain damage step that
pairs with structures/loads/random-vibration-analysis (which stops at
the response PSD without damage) and with the counted-spectrum fatigue
leaves in this pack for time-domain loads.

## Domain quick reference

- Inputs: a one-sided stress PSD G(f) as parallel arrays of frequency
  (Hz) and PSD value (stress^2 / Hz, e.g. MPa^2/Hz), and the Basquin
  relation N * S^m = A on the stress amplitude S (A material constant,
  m slope exponent).
- Spectral moments by trapezoid integration over the samples:
  m_n = sum_i (f_i^n * G_i + f_{i+1}^n * G_{i+1}) * df_i / 2 for
  n = 0, 1, 2, 4. A flat band G0 over [f1, f2] gives the closed forms
  m0 = G0*(f2 - f1), m2 = G0*(f2^3 - f1^3)/3 and
  m4 = G0*(f2^5 - f1^5)/5 used as the anchor identity.
- Expected peak rate: Ep = sqrt(m4 / m2), peaks per second.
- Narrow-band (Rayleigh amplitudes): zero-crossing rate
  nu0 = sqrt(m2 / m0); damage rate D_nb = nu0 / A * (sqrt(2*m0))^m *
  GAMMA(1 + m/2), where GAMMA = math.gamma (module constant
  GAMMA_FN). The Rayleigh amplitude moment (sqrt(2*m0))^m *
  GAMMA(1 + m/2) equals (2*m0)^(m/2) * GAMMA(1 + m/2).
- Dirlik mixture parameters (module dirlik_coefficients), with
  gamma = m2 / sqrt(m0*m4), x_m = (m1/m0) * sqrt(m2/m4),
  D1 = 2*(x_m - gamma^2)/(1 + gamma^2),
  R = (gamma - x_m - D1^2)/(1 - gamma - D1 + D1^2),
  D2 = (1 - gamma - D1 + D1^2)/(1 - R), D3 = 1 - D1 - D2 (so the
  mixture weights sum to 1 by construction), and the exponential decay
  scale Q = 1.25 * D1. This closed-form set reproduces the
  prep-verified anchor values of the wave-38 worked example.
- Dirlik damage rate: D_dl = Ep * E[S^m] / A with the amplitude moment
  E[S^m] = (sqrt(m0))^m * (D1 * Q^m * GAMMA(1 + m) + 2^m *
  GAMMA(1 + m/2) * (D2 * |R|^m + D3)), following the spec convention
  exactly. Under this 2^m convention the Dirlik estimate lies above
  the narrow-band estimate at every bandwidth and the two rates track
  each other as the band narrows (rate ratio tends to 2^(m/2), i.e. 4
  for m = 4).
- Fatigue life: life_h = 1 / (damage_rate * 3600).
- FAR 25.571 / CS 25.571 damage tolerance practice frames the fatigue
  evaluation; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Supply the response stress PSD as sorted frequency and PSD arrays,
   one-sided, in consistent stress units (psd_moments validates
   non-empty, matched, non-negative input).
2. Integrate the spectral moments m0, m1, m2 and m4 with psd_moments
   (trapezoid rule, so irregular frequency spacing is weighted
   correctly).
3. Get the expected peak rate with expected_peak_rate(m0, m2, m4) and
   the zero-crossing rate nu0 = sqrt(m2/m0) for the narrow-band model.
4. Compute the narrow-band Rayleigh damage rate with
   narrowband_damage_rate(m0, m2, m4, A, m).
5. Form the Dirlik mixture parameters with dirlik_coefficients(m0, m1,
   m2, m4) and the wide-band damage rate with dirlik_damage_rate(m0,
   m1, m2, m4, A, m).
6. Convert both damage rates to fatigue lives in hours with
   fatigue_life_hours.
7. Run the full screening in one call: random_vibration_fatigue(freqs,
   psd, A, m) returns the moments, peak rate, both damage rates, both
   lives and the verdict, which reports the Dirlik life as the
   governing estimate for the life check (the wider-band model).
8. Confirm the deterministic checks with the contract test
   scripts/test_random_vibration_fatigue.py.

## Worked example

Flat stress PSD G0 = 2.0 MPa^2/Hz over 10 to 100 Hz (uniformly
sampled), Basquin A = 1e12, m = 4:

- Spectral moments: m0 = 180.0 MPa^2, m1 = 9900.0, m2 = 666000.0,
  m4 = 3.99996e9 (within 0.0005% of the closed forms above).
- Expected peak rate: Ep = sqrt(m4/m2) = 77.498 peaks/s (anchor
  77.50).
- Narrow-band model: nu0 = sqrt(m2/m0) = 60.83 crossings/s; damage
  rate 1.57665e-5 per second (anchor 1.577e-5), life 17.62 h.
- Dirlik coefficients: gamma 0.7849, x_m 0.7097, D1 0.1159,
  R 0.5483, D2 0.2494, D3 0.6347, Q 0.1449; D1 + D2 + D3 = 1.0000.
- Dirlik model: damage rate 5.28137e-5 per second (anchor 5.281e-5),
  life 5.26 h.
- Verdict: "dirlik fatigue life 5.26 h governs the random-vibration
  screening (narrow-band model gives 17.62 h)". The Dirlik estimate
  is the wider-band model and is the conservative one here, so it
  gates the screening.

## Verification

- Flat-PSD moment identities (m0 = G0*(f2-f1), m2 = G0*(f2^3-f1^3)/3,
  m4 = G0*(f2^5-f1^5)/5) hold within 1% on the worked example.
- Peak rate within 1% of 77.50 peaks/s; narrow-band damage rate within
  2% of 1.577e-5 per s and life near 17.6 h; Dirlik damage rate within
  5% of 5.281e-5 per s and life near 5.26 h.
- Dirlik mixture weights satisfy D1 + D2 + D3 == 1 (tested to 12
  places).
- Doubling G0 doubles m0 and scales both damage rates by m0^(m/2):
  exactly 2x at m = 2 and 4x at m = 4.
- Bandwidth convergence: the Dirlik-to-narrow-band damage rate ratio
  approaches 2^(m/2) = 4 as the band narrows (48 to 52 Hz input gives
  3.997).
- Zero-energy PSD (all-zero G) returns zero damage rate with an
  unbounded-life verdict instead of raising.
- Non-physical inputs raise ValueError: empty or mismatched PSD
  arrays, negative frequency or PSD values, unsorted frequencies,
  A <= 0, m <= 0, non-positive moments in the rate models, and
  non-positive damage rate in fatigue_life_hours.
- All checks are deterministic (no RNG, stdlib only) and run offline
  via python3 scripts/test_random_vibration_fatigue.py.

## Related leaves

- structures/loads/random-vibration-analysis: builds the response
  stress PSD from a base input through the single-degree-of-freedom
  response and stops before any fatigue damage; feed its output PSD
  here.
- structures/fatigue/load-spectrum-counting: time-domain cycle
  counting of a measured load history, the alternative input path when
  no response PSD exists.
- structures/fatigue/miner-damage: cumulative damage accounting for a
  counted spectrum, the time-domain counterpart of this rate-based
  spectral damage.
- structures/fatigue/stress-life-curve: Basquin S-N curve life
  prediction for deterministic amplitude loads; supplies the A and m
  constants used here.
- structures/fatigue/goodman-diagram: mean-stress correction for the
  amplitude-based life relations.

## Pitfalls

- Feeding a response PSD that is not in stress units: the moments and
  damage rates inherit the PSD units, so G(f) must already be
  stress^2/Hz (convert an acceleration or displacement response PSD
  with the correct stress transfer before calling the module), or the
  life estimate is meaningless.
- Ignoring the trapezoid weighting on irregular frequency spacing:
  m_n is the integral of f^n * G(f) over the samples, so summing
  f^n * G without the segment widths overstates the moments; the
  module weights every segment by its own df.
- Mixing amplitude and range conventions in the Basquin law: N * S^m =
  A is on the stress amplitude S here. Writing the curve on stress
  range doubles S and shifts A by 2^m (a factor 16 at m = 4) if the
  same A is reused, which silently changes the life by that factor.
- Expecting the narrow-band model to bound the Dirlik estimate from
  above: under this spec's 2^m amplitude-moment convention the Dirlik
  rate exceeds the narrow-band rate at every bandwidth (by the anchor
  ratio 5.281e-5 against 1.577e-5 per s) and the two converge only in
  proportion, toward 2^(m/2) = 4 for m = 4 as the band narrows. Treat
  the Dirlik life as the governing one for screening.
- Truncating the analysis band too close to the resonance content:
  m4 weights f^4, so dropping high-frequency response content that is
  small in energy but non-negligible at f^4 pulls the peak rate
  sqrt(m4/m2) and the Dirlik damage down; widen the band until the
  top-of-band content is truly negligible.
- Pushing m large or damage rates to zero: GAMMA(1 + m) grows factor-
  ially with m and damage rates near zero make fatigue_life_hours
  raise ValueError; a zero-energy PSD is reported as zero damage with
  an unbounded life verdict, never as a numeric life.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_random_vibration_fatigue.py

29 tests cover: trapezoid moment identities for a flat PSD, the
worked-example anchors (peak rate 77.50 within 1%, narrow-band damage
1.577e-5 per s and life 17.62 h within 2%, Dirlik damage 5.281e-5 per
s and life 5.26 h within 5%), the Dirlik coefficient anchors with
D1 + D2 + D3 == 1, level scaling (doubling G0 scales both damage rates
by m0^(m/2)), bandwidth convergence of the two damage models, the
zero-energy PSD path, ValueError rejection of every non-physical input
class, closed-form amplitude-moment identities, and determinism across
repeated runs.

## Compliance

- Standards referenced, not reproduced: FAR 25.571 and CS 25.571 frame
  the fatigue and damage tolerance evaluation context
  (standards-map.yaml, reference-only). The spectral fatigue relations
  above are standard engineering methodology, summary-only; no
  regulatory text is quoted.
- compliance: STANDARDS-REF, gated: false.

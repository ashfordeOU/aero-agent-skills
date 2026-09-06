---
name: gnss-carrier-smoothing
description: "Use when you must smooth GNSS code pseudoranges with carrier-phase delta ranges before positioning: run the first-order Hatch recursion at a smoothing time constant, carry the smoothed range between epochs on the precise carrier increments, and monitor the code-carrier ionospheric divergence whose trailing-window slope fit predicts the smoothed-minus-code bias that would alarm a diverging range. Computes the noise-reduction verdict from the exact steady-state code-noise closed form sigma_code*sqrt(alpha/(2 - alpha)), its sigma_code/sqrt(2*tau/T) textbook limit and the carrier delta-range term. Produces the smoothed range time series, the verdict (code-only std, quoted limit, carrier term, total std, improvement factor) and the divergence alarm that gate the range before it feeds positioning. Trigger: carrier-phase smoothing, code-carrier smoothing, hatch recursion, smoothing time constant, code-carrier divergence, ionospheric divergence, smoothed range noise reduction."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: rtca-do-229
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [gnss-carrier-smoothing, carrier-phase-smoothing, hatch-filter-recursion, code-carrier-divergence-monitor, ionospheric-divergence-check, smoothed-range-noise-reduction]
  version: 0.1.0
  author: AeroSkills
---

# GNSS Carrier-Phase Smoothing (gnc-autonomy/navigation/gnss-carrier-smoothing)

Use when the task is smoothing GNSS code pseudoranges with
carrier-phase delta ranges as a measurement preprocessor for
positioning. The code pseudorange is low-pass filtered at a smoothing
time constant tau while the precise carrier delta range carries the
smoothed range between epochs, cutting the raw code noise by about an
order of magnitude while a code-carrier ionospheric divergence monitor
alarms the slowly growing error that a linear ionosphere induces. This
leaf implements the first-order Hatch recursion, its exact
steady-state noise closed forms, and the divergence monitor in pure
Python, stdlib only. It pairs with gnc-autonomy/navigation/
gnss-pseudorange-positioning (the single-epoch snapshot fix that
consumes the smoothed ranges), gnss-raim-fde for integrity on the raw
measurement set, and kalman-filter-design as the alternative
estimation route with a dynamics model. RTCA DO-229 MOPS
carrier-smoothing and divergence concepts appear here in paraphrased
summary form only. Continuous carrier phase between epochs is assumed;
cycle-slip repair and integer ambiguity resolution are out of scope.

## Domain quick reference

- Hatch gain: alpha = T / tau in (0, 1), so the recursion pole
  (1 - alpha) lies in (0, 1) and the variance relaxation e-folds in
  about tau/2 seconds (50 s at tau = 100 s). A time constant at or
  below the update interval (alpha >= 1) means no smoothing.
- Recursion: s_0 = c_0; for k >= 1,
  s_k = alpha*c_k + (1 - alpha)*(s_(k-1) + (phi_k - phi_(k-1))).
  The code is low-pass filtered while the carrier delta range bridges
  epochs, so a slowly growing code bias is smoothed out over tau while
  the fast, precise carrier motion is followed.
- Exact code-only steady-state std: sigma_smoothed =
  sigma_code*sqrt(alpha/(2 - alpha)). An input fed with weight w to a
  pole-(1-alpha) recursion contributes w^2/(alpha*(2 - alpha)) times
  its variance, giving the code term alpha^2/(alpha*(2 - alpha)) and
  the carrier term (1 - alpha)^2/(alpha*(2 - alpha)).
- Textbook limit: sigma_code/sqrt(2*tau/T) = sigma_code*sqrt(alpha/2),
  the tau >> T small-alpha form, with the exact identity
  approx = exact*sqrt((2 - alpha)/2) and relative gap
  (exact - approx)/exact = alpha/4 + alpha^2/32 + alpha^3/128 + ...,
  about 0.0025 at alpha = 0.01.
- Carrier delta-range term std:
  (1 - alpha)*sigma_carrier/sqrt(alpha*(2 - alpha)). The two noise
  inputs are independent per epoch, so the total smoothed variance is
  the exact sum of the code-term and carrier-term variances and the
  total std is sqrt(code-term variance + carrier-term variance).
- Improvement factor: sigma_code / total_std (10.025 at the defaults).
- Ionospheric divergence: the code is delayed by +I while the carrier
  is advanced by -I, so the code-carrier difference D = code - phi =
  2*I grows at rate dD/dt = 2*dI/dt. A Hatch filter lags a linear
  ramp: at steady state the smoothed-minus-code error is
  -rate*(tau - T) = -2*(dI/dt)*(tau - T), the classic code-carrier
  divergence error whose tau >> T form is -2*(dI/dt)*tau.
- Units are SI throughout (m, s, m/s). Deterministic recursion,
  closed-form noise and slope fits, stdlib math only.

## Workflow

1. Set the smoothing configuration: choose the smoothing time
   constant tau, the update interval T and the raw noise sigmas, and
   confirm 0 < T < tau with alpha_from_time_constant so alpha = T/tau
   lies in (0, 1). The defaults are tau = 100 s, T = 1 s,
   sigma_code = 0.3 m, sigma_carrier = 0.003 m, window 60, threshold
   1.0 m.
2. Run the Hatch recursion traverse over the code-carrier stream:
   run_hatch_smoother seeds the first epoch with the raw code and each
   later epoch applies hatch_update with the carrier delta range
   phi_k - phi_(k-1). On a diverging ionosphere the early smoothed
   values sink below the raw code, the expected lag signature.
3. Form the noise-reduction verdict with code_noise_std_smoothed and
   noise_reduction_verdict: the exact code-only std against the
   sigma_code/sqrt(2*tau/T) textbook limit and their identity, the
   carrier delta-range term, the total std and the improvement factor
   over the raw code.
4. Run the code-carrier divergence monitor: iono_divergence_rate fits
   the least-squares slope of the code-carrier difference over the
   trailing window (divided by T into m/s), smoothed_iono_bias
   predicts the steady-state smoothed-minus-code bias -rate*(tau - T),
   and divergence_check raises the alarm when the predicted bias
   exceeds the threshold.
5. Gate the smoothed range for positioning: release the smoothed range
   time series with the noise-reduction verdict and the divergence
   alarm, and confirm the deterministic checks with the contract test
   (see Behavior contract below).

## Worked example

Receiver at a fixed 20000000.0 m range, tau = 100 s, T = 1 s,
sigma_code = 0.3 m, sigma_carrier = 0.003 m, divergence window 60
epochs, alarm threshold 1.0 m. All values are real module outputs of
this leaf (deterministic, offline).

- Configuration: alpha = T/tau = 0.010000; pole 1 - alpha = 0.990000;
  variance relaxation e-folding about tau/2 = 50.0 s.
- Noise-reduction verdict (noise_reduction_verdict):
  - exact code-only std = sigma_code*sqrt(alpha/(2 - alpha)) =
    0.021266 m;
  - textbook limit sigma_code/sqrt(2*tau/T) = 0.3/sqrt(200) =
    0.021213 m, relative gap 0.002503 = alpha/4 + alpha^2/32 +
    alpha^3/128 (identity asserted to 1e-8);
  - carrier delta-range term = 0.021054 m, comparable to the code term
    because the recursion integrates many millimeter increments;
  - total smoothed std = 0.029925 m (variance is the exact sum of the
    code term and the carrier term, asserted to 1e-15);
  - improvement factor = sigma_code/total_std = 10.025: the smoothed
    range is about ten times quieter than the raw code.
- Empirical confirmation over 38000 settled epochs: code-only replay
  (Random(42), perfect carrier) gives empirical std 0.021043 m against
  the closed form 0.021266 m (within 0.002 m and 5%); code plus
  carrier replay (Random(7)) gives 0.027221 m against 0.029925 m
  (relative difference 0.0904, within the 15% autocorrelation budget,
  effective samples about N/(2*tau/T) ~ 190).
- Ionospheric ramp at v = 0.02 m/s (divergence rate dD/dt = 2*v = 0.04
  m/s, noise free): closed-form steady-state smoothed-minus-code bias
  smoothed_iono_bias(0.04, 100, 1) = -3.9600 m = -(2v)*(tau - T), and
  the empirical mean over the last 2000 of 4000 epochs is -3.9600 m
  (matched within 0.1%). The smoothed range lags the growing code
  delay by about 4 m at this time constant.
- Early epochs of that ramp (raw code 20000000.02 m, carrier delta
  -0.0200 m per epoch): smoothed 20000000.000000 (seed),
  19999999.980400, 19999999.961196, 19999999.942384,
  19999999.923960 m: the recursion sinks below the code while the
  ionosphere climbs.
- Divergence monitor on noisy code-carrier differences (code noise
  0.3 m on the diffs, Random(123)):
  - quiet ionosphere v = 0.001 m/s: estimated rate -0.0001 m/s,
    predicted smoothed bias +0.0075 m, alarm False (the noise floor of
    the 60 s slope fit stays far below the 1.0 m threshold);
  - ramp v = 0.02 m/s: estimated rate 0.0427 m/s (near the true
    0.04), predicted smoothed bias -4.2256 m, alarm True.

## Verification

- Confirm alpha_from_time_constant(100, 1) = 0.01 and the pole
  0.99 in (0, 1).
- Confirm code_noise_std_smoothed(0.01, 0.3) = 0.021266 m and the
  identity approx = 0.021213 = exact*sqrt(1.99/2) to 1e-12.
- Confirm the verdict: carrier_term_std 0.021054 m, total_std 0.029925
  m, improvement_factor 10.025; total variance equals the exact sum of
  the code and carrier term variances to 1e-15.
- Confirm run_hatch_smoother on the noise-free ramp reproduces the
  five early smoothed values above within 1e-6.
- Confirm smoothed_iono_bias(0.04, 100, 1) = -3.96 m and the
  divergence_check replayed verdicts (quiet no alarm, ramp alarms).
- Confirm every non-physical input raises ValueError: tau <= 0, T <=
  0, T >= tau, alpha outside (0, 1), sigma_code or sigma_carrier at 0
  or negative, window below 2 or above the epoch count, non-finite
  measurements and differences, threshold at 0 or negative, unequal or
  empty epoch lists.
- Run the deterministic contract test offline: python3
  scripts/test_gnss_carrier_smoothing.py (34 tests).

## Related leaves

- gnc-autonomy/navigation/gnss-pseudorange-positioning: the
  single-epoch snapshot fix that consumes the smoothed pseudoranges
  (its scope explicitly excludes smoothing).
- gnc-autonomy/navigation/gnss-raim-fde: integrity fault detection and
  exclusion on the raw measurement set, the snapshot guard around the
  positioning solution.
- gnc-autonomy/navigation/kalman-filter-design: the scalar
  predict/correct estimator with a dynamics model and covariance
  tuning, the alternative to the measurement-domain Hatch recursion.
- gnc-autonomy/navigation/dilution-of-precision: geometry quality
  reads that complement the range-quality verdict.
- gnc-autonomy/navigation/ins-gnss-integrated-filter: the loosely
  coupled integration that consumes gated GNSS range updates.

## Pitfalls

- Reporting the textbook limit as the exact reduction: at alpha =
  0.01 the exact code-only std is 0.021266 m while
  sigma_code/sqrt(2*tau/T) = 0.021213 m, a 0.25% relative gap that
  grows with alpha/4; use the exact closed form and quote the limit
  only as the tau >> T approximation.
- Dropping the carrier delta-range term: the carrier increments are
  millimeter-level per epoch but the recursion integrates them, so
  their term (0.021054 m) rivals the code term (0.021266 m) at the
  defaults; the total smoothed std is 0.029925 m, not the code-only
  0.021266 m.
- Forgetting the divergence monitor before release: a linear
  ionosphere with dI/dt = 0.02 m/s leaves a steady smoothed-minus-code
  bias of about -4 m at tau = 100 s, enough to corrupt the position
  fix even though the smoothed range looks quiet.
- Running the recursion without validating the configuration: alpha
  outside (0, 1), T >= tau, or an empty or unmatched code-carrier
  stream raises ValueError rather than producing a plausible-looking
  series.
- Assuming continuous carrier phase: the recursion needs an unbroken
  carrier arc between epochs; cycle-slip repair and integer ambiguity
  resolution are out of scope for this leaf.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline, exit 0):

    python3 scripts/test_gnss_carrier_smoothing.py

The test covers the worked-example contract (alpha 0.01, code-only std
0.021266 m, total std 0.029925 m, improvement factor 10.025, early
ramp epochs), the closed-form identities (textbook limit identity to
1e-12, variance sum to 1e-15, relative-gap expansion to 1e-8), the
empirical replays (Random(42) code-only within 0.002 m and 5%,
Random(7) code plus carrier within 15%, ionospheric ramp bias within
0.1%), the divergence monitor replay (quiet no alarm, ramp rate near
0.04 m/s with alarm), deterministic replay, and ValueError rejection of
every non-physical input.

## Compliance

- Standards referenced, not reproduced: RTCA DO-229 MOPS is the GNSS
  airborne equipment standard whose carrier-smoothing and divergence
  monitoring concepts this leaf paraphrases in summary form per
  standards-map.yaml; no MOPS text is reproduced verbatim.
- compliance: STANDARDS-REF, gated: false.

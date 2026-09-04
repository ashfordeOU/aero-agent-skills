# Wave-34 leaf spec: gyro-allan-variance (space-systems, adcs pack)

- Path: skills/space-systems/adcs/gyro-allan-variance/
- Pack: adcs. Closest siblings: attitude-determination-quest / triad
  (attitude from vector observations), star-tracker (star ID), sun-
  pointing (solar geometry), reaction-wheel-control / control-moment-
  gyro / magnetorquer-control / attitude-control-sizing (control
  actuators), gnc-autonomy/estimation-filtering/complementary-filter
  (gyro+vector fusion CONSUMES gyro specs), gnc-autonomy/navigation/
  inertial-navigation (propagates INS position error from drift/bias
  specs; does NOT characterize sensor noise), cross-cutting/numerics/
  power-spectral-density (Welch periodogram, frequency domain; not the
  time-domain Allan method). Repo-wide grep: zero "allan" hits.
- Standards id: ecss (reference-only; adcs convention). Ledger
  Standard: ecss.
- Family: space-systems

## Claim

Characterize gyroscope noise for ADCS sensor selection: compute the
overlapping Allan deviation over a correlation-time (tau) grid from a
rate sample time series, classify the noise type from the log-log slope
(white noise / angle random walk slope about -1/2, rate random walk
about +1/2, quantization about -1, bias instability flat floor), and
extract the angle random walk coefficient in deg/sqrt(h). Produces the
Allan deviation curve, the noise classification, the fitted slope and
the ARW coefficient, the metrology layer beneath any gyro-using
estimation leaf.

Does NOT do: gyro+vector attitude estimation (complementary-filter
owns the fusion); INS position error propagation from given drift/bias
(gnc inertial-navigation); frequency-domain PSD estimation
(cross-cutting power-spectral-density); star tracker / sun sensor
models.

## Model (implement exactly)

Module constants:
- ARW_DEG_PER_SQRT_H = 57.2958 * sqrt(3600) scale handled in
  angle_random_walk (convert rad/s at tau0 = 1 s to deg/sqrt(h)):
  ARW = AD(tau=1) [rad/s] * 57.2958 * sqrt(3600) / sqrt(1)? No: for
  white rate noise with tau0 = 1 s, AD(tau) = sigma sqrt(tau0/tau),
  and the angle random walk coefficient N [deg/sqrt(h)] relates to the
  rate PSD; for a rate sample series the standard result is
  ARW = sigma_rate [rad/s] * sqrt(tau0 [s]) * 57.2958 * sqrt(3600)
  with tau0 = 1 s -> sigma_rate * 3437.75. Implement exactly:
  angle_random_walk(ad_at_tau1, tau0 = 1.0) -> ad_at_tau1 *
  57.2958 * sqrt(3600 * tau0).
- RNG_SEED = 20260904 (used ONLY in the contract test to synthesize
  the white-noise sample; the module itself is deterministic on its
  inputs).

Conventions: rate samples in rad/s, equally spaced tau0 seconds apart.
The overlapping Allan deviation at cluster time tau = m tau0:
AD(tau) = sqrt( 1/(2 (N - 2m)) sum_{k=1}^{N-2m} (mean_{k+m..k+2m-1} -
mean_{k..k+m-1})^2 ). Implement with cumulative sums for stability.

Functions (pure stdlib):
- allan_deviation(rate_samples, tau0_s, taus) -> list of AD values
  (rad/s) in the same order as taus, using the overlapping estimator.
  ValueErrors: fewer than 3 samples; tau0 <= 0; any tau < tau0;
  max tau requiring clusters longer than the sample (m > (N-1)/2).
- noise_slope(log_taus, log_ads) -> least-squares slope of log(AD)
  vs log(tau). ValueErrors on empty/mismatched lists.
- classify_noise(slope) -> one of "angle-random-walk" (slope in
  [-0.75, -0.25]), "rate-random-walk" (slope in [0.25, 0.75]),
  "quantization-noise" (slope <= -0.85), "bias-instability" (|slope|
  < 0.15) else "mixed". Deterministic band classification.
- angle_random_walk(ad_at_tau1, tau0_s = 1.0) -> deg/sqrt(h) via the
  scale above. ValueError on non-positive ad/tau0.
- gyro_noise_summary(rate_samples, tau0_s, taus) -> dict
  {taus, allan_deviations, fitted_slope, noise_class,
  arw_deg_per_sqrt_h, ad_at_1s}.

Deterministic test fixtures: the contract test synthesizes a pure
white-noise series with a seeded RNG (random.Random(20260904)) and
asserts the estimator against the theoretical AD(tau) = sigma
sqrt(tau0/tau) within tight ratios; it also synthesizes an integrated
white-noise series (rate random walk) and asserts slope about +0.5.

## Worked example

Synthesized white rate noise: sigma = 2.0e-5 rad/s, tau0 = 1 s,
N = 65536 samples, seeded random.Random(20260904).

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- AD(1 s) = 2.0032e-5 rad/s vs theory 2.0000e-5 (ratio 1.0016).
- AD(256 s) = 1.2760e-6 vs theory 1.2500e-6 (ratio 1.0208); ratios at
  every intermediate tau within [1.00, 1.03].
- fitted slope over tau 2..256 s = -0.4976 (theory -0.5).
- classify_noise(-0.4976) = "angle-random-walk".
- angle_random_walk(AD(1 s), 1.0) = 2.0032e-5 * 57.2958 * sqrt(3600)
  = 0.0689 deg/sqrt(h) (a typical high-grade MEMS/RLG band).
- Integrated white noise (rate random walk): fitted slope = +0.4979
  (theory +0.5).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: fewer than 3 samples; tau0 <= 0; tau < tau0; tau too
  long for the sample; empty/mismatched log lists.
- White-noise fixture (seeded): AD ratio at tau = 1 s within [0.97,
  1.03] of sigma; AD(tau) decays as 1/sqrt(tau) (ratio at 4 s vs 1 s
  within [0.45, 0.55]); slope within [-0.55, -0.45].
- Rate-random-walk fixture (cumulative sum of seeded white noise):
  slope within [0.45, 0.55]; classification "rate-random-walk".
- Classification bands: slope -0.5 -> angle-random-walk; +0.5 ->
  rate-random-walk; -1.0 -> quantization-noise; 0.0 -> bias-
  instability.
- ARW scale: angle_random_walk(2.0e-5, 1.0) about 0.0689 deg/sqrt(h);
  doubling AD doubles ARW; tau0 0.25 s with the same AD(1s-style)
  input scales by sqrt(0.25) = 0.5.
- Determinism: the module itself is input-deterministic; the seeded
  fixtures are reproducible run-to-run.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-gyro-allan-variance.yaml)

Query 1 (copy verbatim):
  "compute the overlapping Allan deviation of gyroscope rate samples and classify the noise as angle random walk or rate random walk from the log log slope"
  intent: "space-systems; gyro Allan deviation and noise slope classification"
  expected_skill: "space-systems/adcs/gyro-allan-variance"
Query 2 (copy verbatim):
  "extract the angle random walk coefficient in degrees per root hour from a gyro rate noise series for ADCS sensor selection"
  intent: "space-systems; gyro angle random walk coefficient from Allan variance"
  expected_skill: "space-systems/adcs/gyro-allan-variance"
Task ids: w34-gyro-allan-variance-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must characterize gyroscope noise
for ADCS sensor selection:" and include the outputs in the Claim. First
tag: gyro-allan-variance. Additional tags ONLY: allan-deviation,
angle-random-walk, rate-random-walk, bias-instability, gyro-noise-model.
NEVER single generic words (gyro, noise, variance, sensor, deviation,
walk). 50-150 words, <=1000 chars, no em dash, no "classified", action
verb present.

FORBIDDEN TOKENS (belong to siblings): attitude quaternion, Wahba,
vector observation (attitude-determination-quest/triad); star
identification (star-tracker); control law, momentum (reaction-wheel-
control etc.); gyro/vector fusion, bias estimation filter
(gnc complementary-filter); INS position error, drift propagation
(gnc inertial-navigation); Welch, periodogram, PSD (cross-cutting
power-spectral-density). The words "Allan deviation", "angle random
walk", "rate random walk", "bias instability", "noise slope" are this
leaf's own.

Tags: [gyro-allan-variance, allan-deviation, angle-random-walk,
rate-random-walk, bias-instability, gyro-noise-model]

Sibling-citation lines for Related leaves:
space-systems/adcs/attitude-determination-quest (determination
sibling), gnc-autonomy/estimation-filtering/complementary-filter
(consumer of gyro noise specs in gyro/vector fusion),
gnc-autonomy/navigation/inertial-navigation (INS error propagation
boundary: metrology vs propagation),
cross-cutting/numerics/power-spectral-density (frequency-domain
boundary).

Ledger Standard: ecss.

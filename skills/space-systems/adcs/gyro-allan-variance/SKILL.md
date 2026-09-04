---
name: gyro-allan-variance
description: "Use when you must characterize gyroscope noise for ADCS sensor selection: compute the overlapping Allan deviation AD(tau) over a correlation-time grid from a rate sample time series with cumulative sums, fit the log-log noise slope, categorize the noise process from the slope band (white noise or angle random walk at about -1/2, rate random walk at about +1/2, quantization at about -1, bias instability as a flat floor), and extract the angle random walk coefficient in deg/sqrt(h). Produces the Allan deviation curve, the noise classification, the fitted slope and the ARW coefficient that gate gyro selection. Trigger: gyro Allan deviation, allan deviation, angle random walk, rate random walk, bias instability, gyro noise model, noise slope, gyroscope rate noise, ARW coefficient, deg per root hour."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: adcs
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: adcs
  tags: [gyro-allan-variance, allan-deviation, angle-random-walk, rate-random-walk, bias-instability, gyro-noise-model]
  version: 0.1.0
  author: Aero Agent Skills
---

# Gyro Allan Variance (space-systems/adcs/gyro-allan-variance)

Use when you must characterize gyroscope noise for ADCS sensor selection:
turning a rate sample time series into the overlapping Allan deviation
curve and reading the noise process off its log-log slope. This leaf
implements the time-domain Allan method in pure Python, stdlib only, and
pairs with space-systems/adcs/attitude-determination-quest for the
attitude side of the sensor suite; gnc-autonomy/estimation-filtering/
complementary-filter consumes gyro noise specs in gyro/vector fusion, so
the ARW coefficient produced here is the metrology layer beneath any
gyro-using estimation leaf.

## Domain quick reference

- Overlapping Allan deviation at cluster time tau = m * tau0, N rate
  samples spaced tau0 seconds apart:

      AD(tau) = sqrt( 1 / (2 (N - 2m)) * sum_{k=0}^{N-2m-1}
                ( mean(samples[k+m : k+2m]) - mean(samples[k : k+m]) )^2 )

  Implemented with cumulative sums S[i] = sum of samples[:i], so each
  cluster mean is (S[b] - S[a]) / m and the estimator stays stable on
  long series.
- White rate noise: AD(tau) = sigma * sqrt(tau0 / tau), a straight line
  of slope -1/2 on a log-log plot. The tau = 1 s deviation equals the
  rate standard deviation sigma.
- Angle random walk coefficient in deg/sqrt(h): ARW = AD(1 s) * 57.2958
  * sqrt(3600 * tau0). With tau0 = 1 s the scale is 3437.748, so
  sigma = 2.0e-5 rad/s gives about 0.0688 deg/sqrt(h), a high-grade
  MEMS/RLG band.
- Noise classes from the log-log slope: about -1/2 angle random walk,
  about +1/2 rate random walk, about -1 quantization noise, flat (near
  zero slope) bias instability.
- classify_noise bands: slope <= -0.85 quantization-noise; [-0.75,
  -0.25] angle-random-walk; [0.25, 0.75] rate-random-walk; |slope| <
  0.15 bias-instability; otherwise mixed.
- Units are SI: rate samples in rad/s, tau in s, AD in rad/s. ECSS
  frames the ADCS context; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Load the gyro rate time series (rad/s) and its sample period tau0 in
   seconds.
2. Choose the correlation-time grid: integer multiples of tau0, with the
   largest cluster m = tau / tau0 at most (N - 1) / 2.
3. Compute the Allan deviation curve with allan_deviation(rate_samples,
   tau0_s, taus); it returns AD values in rad/s in the order of taus.
4. Fit the noise slope: log(AD) against log(tau) with noise_slope, then
   categorize with classify_noise (angle-random-walk, rate-random-walk,
   quantization-noise, bias-instability, or mixed).
5. Read off the angle random walk coefficient: angle_random_walk(ad_at_
   tau1, tau0_s) scales AD at tau = 1 s into deg/sqrt(h).
6. For the full picture in one call, gyro_noise_summary(rate_samples,
   tau0_s, taus) returns the dict {taus, allan_deviations, fitted_slope,
   noise_class, arw_deg_per_sqrt_h, ad_at_1s}.
7. Confirm the deterministic checks with the contract test
   scripts/test_gyro_allan_variance.py.

## Worked example

Seeded white rate noise: sigma = 2.0e-5 rad/s, tau0 = 1 s, N = 65536
samples, generated with random.Random(20260904) via the Box-Muller
transform (module inputs only; the module itself draws no randomness).
Real module outputs on that fixture:

- AD(1 s) = 2.0009e-5 rad/s, ratio 1.0005 to sigma (theory 1.0000).
- Decay: AD(4 s) / AD(1 s) = 0.5009, matching the 1/sqrt(tau) law
  (theory 0.5000).
- AD(256 s) = 1.2680e-6 rad/s, ratio 1.0144 to sigma / sqrt(256)
  (theory 1.2500e-6).
- Fitted slope over the dyadic grid tau = 2..256 s: -0.4977 (theory
  -0.5); classify_noise(-0.4977) = "angle-random-walk".
- Angle random walk: angle_random_walk(2.0009e-5, 1.0) = 0.0688
  deg/sqrt(h), the metrology number a gyro datasheet quotes.
- Integrated white noise (rate random walk, cumulative sum of the same
  fixture): fitted slope +0.5006 (theory +0.5), categorized
  "rate-random-walk".
- gyro_noise_summary on the white fixture returns noise_class
  "angle-random-walk", fitted_slope -0.4977, ad_at_1s 2.0009e-5 and
  arw_deg_per_sqrt_h 0.0688.

## Verification

- allan_deviation raises ValueError for fewer than 3 samples, tau0 <= 0,
  a tau below tau0, a tau that is not a whole multiple of tau0, and a
  cluster longer than (N - 1) / 2 samples.
- noise_slope raises ValueError on empty or mismatched lists, fewer than
  two points, and a zero-variance log-tau grid.
- angle_random_walk raises ValueError on non-positive AD or tau0.
- The white-noise closed form AD(tau) = sigma sqrt(tau0 / tau) is
  checked inside the contract test with ratio bands [0.97, 1.03] from
  tau = 1 s up to 256 s, and the integrated fixture must fit a slope in
  [0.45, 0.55].
- Module determinism: identical inputs give identical outputs; the
  seeded fixture is reproducible run-to-run.

## Related leaves

- space-systems/adcs/attitude-determination-quest: determination
  sibling; the QUEST attitude from vector observations is the consumer
  of a gyro-specified pointing budget.
- gnc-autonomy/estimation-filtering/complementary-filter: consumer of
  gyro noise specs in gyro/vector fusion, where the ARW coefficient
  weights the gyro channel.
- gnc-autonomy/navigation/inertial-navigation: INS error propagation
  boundary; that leaf propagates given drift and bias, this leaf
  characterizes sensor noise, metrology vs propagation.
- cross-cutting/numerics/power-spectral-density: frequency-domain
  boundary; PSD estimation with the Welch periodogram, not the
  time-domain Allan method.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_gyro_allan_variance.py

The 34 tests cover the overlapping Allan deviation against the
white-noise closed form, the seeded fixture anchors (AD(1 s), AD(256 s),
fitted slope -0.4977, ARW 0.0688 deg/sqrt(h)), the rate random walk
slope, classification band boundaries, ARW scaling with tau0, summary
dict keys and consistency, module determinism, and ValueError rejection
of every non-physical input.

## Compliance

- Standards referenced, not reproduced: ECSS is the adcs convention id
  in standards-map.yaml; the Allan deviation relations above are
  standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.

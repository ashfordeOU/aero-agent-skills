---
name: cross-correlation-analysis
description: "Use when you must compute the cross-correlation or autocorrelation of sampled signal sequences to quantify channel similarity and time delay: evaluate the raw cross-correlation over the full lag range with zero padding, normalize it to a correlation coefficient in [-1, 1] from the zero-lag energies, estimate the delay between channels from the peak lag, apply the biased or unbiased convention, and verify the even symmetry of the autocorrelation. Produces the correlation sequence, the peak lag, the normalized coefficient, and the delay in samples that gate time-delay analysis. Trigger: cross-correlation, autocorrelation, time-delay-estimation, lag, normalized-correlation-coefficient, channel-similarity, delay-between-signals."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: numerics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [cross-correlation-analysis, cross-correlation, autocorrelation, time-delay-estimation, normalized-correlation-coefficient, channel-similarity, delay-between-signals, correlation-sequence, biased-normalization, unbiased-normalization]
  version: 0.1.0
  author: Aero Agent Skills
---

# Cross-Correlation Analysis (cross-cutting/numerics/cross-correlation-analysis)

Use when the task is measuring how one sampled signal sequence relates
to another: the raw cross-correlation over every integer lag with zero
padding, the normalized correlation coefficient in [-1, 1], the lag of
the peak as a time-delay estimate, and the even-symmetry check of the
autocorrelation. This leaf is the generic discrete correlation utility
for sampled sequences: all coefficients are computed, none are lookup
values. It pairs with cross-cutting/numerics/fast-fourier-transform
(the frequency-domain view of the same signals) and with
cross-cutting/numerics/digital-filter-design (prefiltering before
correlation), and it shares the correlation-style statistics spirit of
cross-cutting/numerics/least-squares-regression. It does not smooth or
time-align raw flight-test traces (flight-test-operations/planning/
flight-test-data-reduction owns moving-average smoothing and test-data
alignment) and it does not match test-to-analysis mode shapes
(ground-vibration-testing owns MAC-based modal correlation).

## Domain quick reference

- Convention: rxy[k] = sum over n of x[n] * y[n - k], for every integer
  lag k in [-(Ny - 1), Nx - 1]; terms whose index falls outside a
  sequence contribute zero. Nx = len(x), Ny = len(y).
- Sign convention: a positive peak lag means x leads y. If y is x
  delayed by d samples, the peak sits at lag -d (as in the worked
  example). In delay_estimate, delay_samples = -peak_lag, so a positive
  delay_samples means y is delayed relative to x.
- Modes: raw returns the plain sums; biased divides every value by Nx;
  unbiased divides by the number of overlapping samples at each lag.
- Normalized coefficient: value / sqrt(rxx0 * ryy0) with rxx0 = sum
  x[n]^2 and ryy0 = sum y[n]^2 the zero-lag energies. Coefficients lie
  in [-1, 1]; an identical shape gives 1.0 at the matching lag.
- Autocorrelation rxx[k] = cross_correlation(x, x): even, rxx[k] =
  rxx[-k], with the zero-lag value rxx[0] = sum x[n]^2 the signal
  energy.
- Peak selection: lag of the maximum absolute value; ties resolve to
  the smaller absolute lag, then the first encountered.
- Zero-lag coefficient: sum x[n] y[n] / sqrt(rxx0 ryy0), the normalized
  similarity at k = 0.
- NACA TR-824 frames the numerics-pack reference set; the relations
  above are standard discrete-signal methodology, summary-only.

## Workflow

1. Load the two sampled sequences x and y as lists of floats (SI
   samples, any physical unit carried by the caller).
2. Run the raw correlation: lags, values = cross_correlation(x, y);
   lags runs -(Ny-1) .. Nx-1 with one value per lag.
3. Inspect the peak: peak_lag(lags, values) gives the lag of the
   maximum absolute correlation and the delay sign per the convention
   above.
4. Get the bounded similarity view: lags, coeffs =
   normalized_cross_correlation(x, y); read the coefficient at the peak
   lag, 1.0 for a perfect delayed match.
5. For the compact delay result, run delay_estimate(x, y) and read
   peak_lag, peak_value, normalized_peak and delay_samples.
6. Compare two channels at zero offset with
   zero_lag_coefficient(x, y).
7. For a single channel, run autocorrelation(x) and verify evenness
   rxx[k] == rxx[-k] and the zero-lag energy rxx[0] = sum x[n]^2.
8. Repeat with mode = "biased" or "unbiased" when the caller needs the
   scaled conventions for spectral-density-style work.
9. Confirm the deterministic checks with the contract test
   scripts/test_cross_correlation_analysis.py.

## Worked example

x = [1, 2, 3, 4, 5]; y = [0, 0, 1, 2, 3, 4, 5] (y is x delayed by 2
samples, Nx = 5, Ny = 7).

- cross_correlation(x, y): lags -6..4; raw values [5, 14, 26, 40, 55,
  40, 26, 14, 5, 0, 0]. Peak at lag -2 with value 55.
- Sign check: peak lag -2 (negative), so x leads y; delay_samples =
  -(-2) = +2, y is delayed by 2 samples relative to x.
- normalized_cross_correlation at the peak lag: 55 / sqrt(55 * 55) =
  1.0, a perfect delayed match.
- delay_estimate(x, y): {peak_lag: -2, peak_value: 55.0,
  normalized_peak: 1.0, delay_samples: 2}.
- autocorrelation([1, 2, 3]): rxx[0] = 14, rxx[1] = rxx[-1] = 8,
  rxx[2] = rxx[-2] = 3; the sequence [3, 8, 14, 8, 3] is even.
- autocorrelation([1, 1, 1, 1], "biased"): 1.0 at lag 0, 0.75 at lag
  +1 (3/4); "unbiased": 1.0 at both lags (3 overlapping samples give
  3/3).
- zero_lag_coefficient([1, 2, 3], [3, 2, 1]) = 10/14 = 0.7143.

## Verification

- Confirm cross_correlation(x, y) on the worked example returns the raw
  values list above with peak_lag -2 and peak value 55.
- Confirm the normalized peak coefficient is 1.0 within 1e-9 and every
  normalized coefficient lies in [-1, 1].
- Confirm delay_estimate(x, y) returns delay_samples +2 and that
  swapping the inputs flips the peak lag sign (delay_samples -2).
- Confirm autocorrelation([1, 2, 3]) is even with rxx[0] = 14 and that
  the identical-signal cross-correlation peaks at lag 0.
- Confirm biased divides by Nx and unbiased divides by the overlap
  count: [1, 1, 1, 1] gives 0.75 biased and 1.0 unbiased at lag +1.
- Confirm every invalid input raises ValueError: empty sequences,
  non-numeric or non-finite entries, unknown modes, and zero-energy
  normalization.
- Run the contract test offline: python3
  scripts/test_cross_correlation_analysis.py (41 tests, deterministic).

## Related leaves

- cross-cutting/numerics/fast-fourier-transform: spectrum of the same
  sampled signals, the frequency-domain partner to time-domain
  correlation.
- cross-cutting/numerics/digital-filter-design: prefilter the channels
  before correlating so out-of-band content does not mask the peak.
- cross-cutting/numerics/least-squares-regression: regression fitting
  that consumes correlation-style statistics between variables.
- flight-test-operations/planning/flight-test-data-reduction: domain
  smoothing and time alignment of raw flight-test traces, distinct from
  this generic discrete correlation utility.
- flight-test-operations/flutter/ground-vibration-testing owns MAC-based
  modal correlation of test and analysis mode shapes, which is
  mode-shape matching, not time-series delay estimation.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_cross_correlation_analysis.py

The test covers the spec worked example anchors (lag range -6..4, raw
values list, peak lag -2, peak value 55, normalized peak 1.0, delay
estimate with delay_samples +2, zero-lag coefficient 10/14),
autocorrelation evenness with the 14/8/3 values, biased and unbiased
scaling (0.75 and 1.0 at lag +1 on four ones), the identical-signal
peak at lag 0, cross-correlation reversal symmetry, the Cauchy-Schwarz
peak identity, and ValueError rejection of empty, non-finite,
non-numeric, unknown-mode and zero-energy inputs. Runs in well under a
second.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the
  numerics-pack public-domain reference set; discrete cross-correlation
  is standard signal-analysis methodology (Bendat and Piersol style
  summary), paraphrase-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

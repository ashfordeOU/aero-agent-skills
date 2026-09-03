# Wave-29 leaf spec: cross-correlation-analysis (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/cross-correlation-analysis/
- Pack: numerics (existing siblings: convergence-verification,
  digital-filter-design, eigenvalue-decomposition, fast-fourier-
  transform, finite-difference-derivatives, hypothesis-testing,
  interpolation, least-squares-regression, matrix-operations,
  monte-carlo-sampling, numerical-integration, ode-solvers,
  optimization-algorithms, probability-distributions,
  quaternion-algebra, root-finding, uncertainty-propagation)
- Standards ids: naca-tr-824 (reference-only; the numerics-pack
  convention). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Compute the cross-correlation and autocorrelation of sampled signal
sequences: evaluate the raw cross-correlation over the full lag range,
normalize it to a correlation coefficient in [-1, 1], estimate the
time delay between two channels by the lag of the peak, apply the
biased or unbiased normalization convention, and verify the
autocorrelation symmetry. Produces the correlation sequence, the
peak lag, the normalized coefficient, and the delay estimate that gate
time-delay and similarity analysis of measured channels.

Does NOT do: design frequency-selective filters (digital-filter-design
owns Butterworth IIR design); compute spectra (fast-fourier-transform
owns the DFT/FFT and spectral analysis); interpolate tables
(interpolation owns linear and spline interpolation); smooth or
reduce flight-test traces (flight-test-operations
flight-test-data-reduction owns moving-average smoothing and time
alignment of test data); estimate modal correlation between test and
analysis mode shapes (ground-vibration-testing owns MAC-based
GVT-to-flight correlation). This leaf is the generic discrete
correlation utility for sampled sequences.

## Model (implement exactly)

Module constants: none.

Convention: rxy[k] = sum over n of x[n] * y[n - k], computed for every
integer lag k in the range [-(Ny - 1), Nx - 1]; terms where the index
falls outside a sequence contribute zero. With this convention a
positive peak lag means x leads y (x is a delayed copy of y gives a
peak at a negative lag as in the worked example; state the convention
in the SKILL body).

Functions (pure stdlib, floats):
- cross_correlation(x, y, mode="raw") -> (lags, values):
  x length Nx, y length Ny; for each k in range(-(Ny-1), Nx) compute
  the raw sum. mode "raw" returns the raw sums; mode "biased" divides
  by Nx (the longer sequence length); mode "unbiased" divides by the
  number of overlapping samples per lag. ValueError on empty inputs,
  non-finite entries, or an unknown mode.
- normalized_cross_correlation(x, y) -> (lags, coeffs): coefficient
  at each lag = raw value / sqrt(rxx0 * ryy0) where rxx0 = sum x[n]^2
  and ryy0 = sum y[n]^2 (zero-lag energies). ValueError if either
  energy is zero.
- autocorrelation(x, mode="raw") -> (lags, values):
  cross_correlation(x, x, mode). ValueError on empty x.
- peak_lag(lags, values) -> int: lag of the maximum absolute value
  (ties resolved to the smaller absolute lag, then the first
  encountered). ValueError on empty lists.
- delay_estimate(x, y) -> dict: runs cross_correlation, peak_lag,
  and normalized_cross_correlation; returns {peak_lag,
  peak_value, normalized_peak, delay_samples: -peak_lag} (a positive
  delay_samples means y is delayed relative to x; state the sign
  convention in the SKILL body).
- zero_lag_coefficient(x, y) -> float: normalized coefficient at lag
  0: sum x[n] y[n] / sqrt(rxx0 ryy0). ValueError on zero energy.

## Worked example

x = [1, 2, 3, 4, 5]; y = [0, 0, 1, 2, 3, 4, 5] (y is x delayed by 2
samples).

Deterministic anchors (compute with the exact formulas; assert within
the stated tolerances):
- cross_correlation(x, y): lags -6..4; raw values
  [5, 14, 26, 40, 55, 40, 26, 14, 5, 0, 0]; peak at lag -2 with value
  55 (assert peak_lag == -2 and peak_value == 55).
- normalized peak coefficient = 1.0 (55 / sqrt(55*55)), within 1e-9.
- delay_estimate(x, y) returns delay_samples = +2 (y delayed by 2
  samples relative to x).
- zero_lag_coefficient([1,2,3], [3,2,1]) = 10 / 14 = 0.7143 (within
  1e-4).
- autocorrelation([1,2,3]) at lag 0 = 14; autocorrelation is even:
  value at lag +1 equals the value at lag -1 (both 8 for [1,2,3]:
  rxx[1] = x[1]*x[0] + x[2]*x[1] = 2*1 + 3*2 = 8) and lag +2 equals
  lag -2 (both 3).
- biased/unbiased modes scale correctly: for x = y = [1,1,1,1],
  biased zero-lag value = 4/4 = 1 (divide by Nx), unbiased = 4/4 = 1
  at zero lag (4 overlapping samples); at lag +1 biased = 3/4,
  unbiased = 3/3 = 1.
- ValueErrors: empty lists, non-finite entries, unknown mode, zero
  energy normalization.

Keep at least 16 test methods: raw sequence anchor, peak lag,
normalized peak 1.0, delay estimate sign, zero-lag coefficient,
autocorrelation evenness, biased/unbiased scaling, identity
cross-correlation of a signal with itself peaks at lag 0, ValueErrors.
Runs offline in under 20 s.

## Corpus tasks (ids w29-cross-correlation-analysis-1/2)

Distinctive tokens: cross-correlation, autocorrelation, time delay
estimation, lag, normalized correlation coefficient, channel
similarity, delay between signals. Avoid: Butterworth, IIR, filter
coefficients, cutoff (digital-filter-design); FFT, DFT, power
spectrum (fast-fourier-transform); moving-average smoothing, time
alignment of flight-test traces (flight-test-data-reduction); MAC,
mode shape correlation (ground-vibration-testing).

1. "estimate the time delay between two sampled channels with
   cross-correlation: find the peak lag and the normalized
   correlation coefficient"
2. "compute the autocorrelation of a vibration record and verify the
   even symmetry and the zero-lag energy"

## SKILL body notes

Pair with fast-fourier-transform (frequency-domain view of the same
signals), digital-filter-design (prefiltering before correlation),
least-squares-regression (fitting that uses correlation-like
statistics). State the sign convention explicitly and the boundary to
flight-test data reduction (domain processing of raw test traces) and
GVT MAC correlation (mode-shape matching, not time-series delay). All
coefficients are computed, none are lookup values. Mirror the
numerics-pack SKILL body style (SI units, stdlib only).

# Wave-28 leaf spec: digital-filter-design (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/digital-filter-design/
- Pack: numerics (existing siblings: fast-fourier-transform,
  finite-difference-derivatives, numerical-integration, ode-solvers,
  interpolation, least-squares-regression, root-finding,
  optimization-algorithms, matrix-operations, eigenvalue-decomposition,
  quaternion-algebra, probability-distributions, hypothesis-testing,
  uncertainty-propagation, monte-carlo-sampling, convergence-verification)
- Standards ids: naca-tr-824 (reference-only; the numerics-pack
  convention - fast-fourier-transform and unit-conversion both carry
  this id). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Design digital IIR frequency-selective filters from a cutoff frequency
and an order, with the Butterworth prototype mapped through the
bilinear transform, and apply the filter to a sampled signal. The leaf
computes the prewarped analog cutoff, builds the filter coefficients
(lowpass or highpass), evaluates the magnitude response at a frequency,
filters a signal with the direct-form difference equation, and checks
the design (3 dB point at cutoff, DC gain for lowpass, stability of the
denominator roots). Produces the b and a coefficient vectors, the
magnitude in dB at requested frequencies, the filtered signal, and the
design-verification verdict.

Does NOT do: estimate states or fuse sensors (gnc-autonomy
estimation-filtering leaves own Kalman, alpha-beta, complementary,
particle filters); smooth a flight-test trace (flight-test-operations
flight-test-data-reduction owns moving-average smoothing of raw test
data); compute frequency content (fast-fourier-transform owns the
DFT/FFT of a signal). This leaf designs a frequency-selective
Butterworth IIR filter (cutoff, order, bilinear transform) and applies
it.

## Model (implement exactly)

Module constants:
- GAMMA = 1.4 unused here; PI = 3.141592653589793.
- All magnitudes returned in dB.
- TOL_3DB = 0.02 (dB tolerance on the -3.0103 dB cutoff check).

Functions (pure stdlib, floats):
- prewarp(cutoff_hz, fs) -> float: Omega_a = 2*fs*tan(PI*cutoff_hz/fs).
  ValueError on fs <= 0, cutoff_hz <= 0, cutoff_hz >= fs/2.
- butterworth_poles(order) -> list of complex: normalized unit-circle
  LHP poles s_k = exp(1j*PI*(2*k + order - 1)/(2*order)) for k = 1..order
  (all have negative real part). ValueError on order < 1 or order > 10.
- analog_scale(poles, omega_a) -> scaled poles s = pole*omega_a.
- bilinear_pole(s, fs) -> complex z = (2*fs + s)/(2*fs - s).
- design_lowpass(fs, cutoff_hz, order) -> (b, a):
  1. Omega_a = prewarp(cutoff_hz, fs).
  2. poles = butterworth_poles(order) scaled by Omega_a, then mapped by
     bilinear_pole. a = poly from mapped poles (complex conjugate pairs
     combine to real coefficients; a[0] = 1).
  3. b = zeros(order+1); for a lowpass the digital transfer function
     from the bilinear transform of H(s) = Omega_a^order / prod(s - p_i)
     has numerator b built by the substitution s = 2*fs*(1 - z^-1)/(1 +
     z^-1): implement by the standard recipe: compute the analog
     numerator coefficient array num_a = [0..0, Omega_a^order] (length
     order+1), den_a = poly(scaled poles); apply the bilinear
     coefficient transform (substitute s = 2fs*(1-z^-1)/(1+z^-1) by the
     matrix-free recursion: b = zeros; den = zeros; for each analog
     coefficient index do the binomial expansion of (1+z^-1)^(order-i) *
     (2fs)^i * (1-z^-1)^i) - OR the simpler equivalent: build H(z)
     directly from the mapped digital poles and a numerator that forces
     the DC gain to 1 by evaluating the all-pole response at z=1:
     b = [K], a from poles, K = sum(a)/... with b constant only when
     order <= 2? NO - bilinear Butterworth lowpass of order n has
     numerator b = K*(1+z^-1)^n. So: b_k = K * C(n,k) binomial, K
     chosen so the DC gain (z=1) is 1: K = sum(a) / 2^n. Implement this
     closed form (document it). a from the mapped digital poles via
     poly. Normalize so a[0] = 1 (divide all by a[0]).
  Guarantee: |H(e^{j*2*pi*cutoff/fs})| = 1/sqrt(2) exactly (prewarping
  places the analog 3 dB point at the digital cutoff).
- design_highpass(fs, cutoff_hz, order) -> (b, a): Butterworth highpass
  via the prototype substitution s -> Omega_a^2/s on the squared
  magnitude (mirror poles: for each analog lowpass pole p_i the
  highpass pole is Omega_a^2/p_i, keep LHP), then bilinear map, with
  numerator b_k = K * C(n,k) * (-1)^k and K chosen so the Nyquist gain
  (z = -1) is 1: K = sum(a * (-1)^k) / 2^n. Document the recipe in the
  SKILL body.
- freq_response_db(b, a, freq_hz, fs) -> float: 20*log10(|H(e^{j
  2*pi*freq/fs})|) where H is evaluated by Horner on z^-1 with z^-1 =
  exp(-1j*2*pi*freq/fs). ValueError on freq_hz outside (0, fs/2).
- apply_filter(b, a, x) -> list: direct-form II transposed difference
  equation y[n] = b[0]*x[n] + sum_{k>=1}(b[k]*x[n-k] - a[k]*y[n-k]),
  a[0] normalized to 1; past samples treated as zero (zero initial
  condition). Accepts x as list of floats.
- filter_design_checks(b, a, fs, cutoff_hz, ftype) -> dict: compute
  gain_at_cutoff_db = freq_response_db(b, a, cutoff_hz, fs);
  dc_or_nyquist_gain_db (lowpass: gain at 1 Hz; highpass: gain at
  fs/2 - 1 Hz); stability: all |roots of a| < 1 (root finder: for
  order <= 4 use the closed-form quadratic/cubic? implement a tiny
  companion-matrix-free bisection? SIMPLEST: for order <= 4 evaluate
  stability via the Schur-Jury table on a; for order > 4 return
  stability as not-checked. Use the Schur-Jury table for orders 1..4
  and document the limit). Return dict with keys: cutoff_gain_db,
  reference_gain_db, passband_ok (|cutoff_gain_db + 3.0103| <= 0.02),
  stable (bool or None), verdict (str).
ValueError on: fs <= 0, cutoff_hz <= 0, cutoff_hz >= fs/2, order < 1 or
order > 8, x not a non-empty list of finite floats.

## Worked example

fs = 1000 Hz, lowpass, fc = 100 Hz, order 2.
- prewarp = 2000*tan(0.1*PI) = 649.8393 (assert within 1e-3).
- butterworth_poles(2) = -0.7071068 +/- 0.7071068j (assert real and
  imag within 1e-9).
- freq_response_db at cutoff must be -3.0103 +/- 0.02 dB.
- freq_response_db at 10 Hz: between -0.02 and +0.02 dB.
- freq_response_db at 400 Hz: below -30 dB (compute the module value
  and assert the module returns it deterministically; also assert the
  bound).
- apply_filter to x = [5.0]*400: the last 50 output samples within
  0.001 of 5.0 (DC gain 1).
- design_checks: passband_ok True, stable True (order 2).
- Highpass order 2 fc = 100: freq_response_db at 400 Hz within 0.05 dB
  of 0 dB; at 50 Hz below -15 dB (compute module value, assert
  determinism and the bound); reference gain at fs/2 - 1 Hz within 0.05
  dB of 0 dB.
- Order 1 lowpass fc 100: cutoff gain -3.0103 +/- 0.02; DC gain ~1.
- ValueErrors on fs 0, cutoff 500 (>= Nyquist), order 0, order 9,
  freq_hz 0, freq_hz 600.
Keep at least 18 test methods: prewarp, pole placement order 1/2/3
(symmetry), coefficient shapes (len b == len a == order+1, a[0] == 1),
cutoff gain lowpass, DC gain, attenuation band, highpass cutoff and
reference gains, apply_filter impulse response sanity (y length == x
length), steady state DC, stability table order 2 and order 4, verdict
strings, ValueErrors.

## Corpus tasks (ids w28-digital-filter-design-1/2)

Distinctive tokens: digital filter design, Butterworth, bilinear
transform, IIR lowpass, cutoff frequency, prewarping, filter
coefficients, highpass. Avoid: Kalman, alpha-beta, tracking filter,
attitude observer, particle filter (gnc estimation-filtering); moving
average smoothing, time alignment (flight-test-data-reduction); DFT,
FFT, frequency spectrum (fast-fourier-transform).

1. "design a Butterworth IIR lowpass digital filter with the bilinear
   transform: prewarp the cutoff frequency, compute the filter
   coefficients, and check the 3 dB point at the cutoff"
2. "build a second order Butterworth highpass filter at 2 Hz cutoff on
   a 50 Hz sampled accelerometer channel and verify the magnitude
   response near Nyquist"

## SKILL body notes

Pair with fast-fourier-transform (frequency analysis of the filtered
output), finite-difference-derivatives (differentiation of noisy
signals), and state the boundary to gnc-autonomy estimation-filtering
(state observers, not frequency-selective filters). All coefficients
are computed, none are lookup values. Mirror the numerics-pack SKILL
body style of cross-cutting numerics leaves (units SI, stdlib only).

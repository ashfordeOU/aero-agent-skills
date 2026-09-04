---
name: digital-filter-design
description: "Use when you must compute the coefficients of a digital Butterworth IIR lowpass or highpass frequency-selective filter from a cutoff frequency, sample rate, and order: prewarp the analog cutoff, map the normalized Butterworth poles through the bilinear transform, build the b and a coefficients with unity DC or Nyquist gain, evaluate the magnitude response in dB at any frequency, and apply the filter to a sampled signal with the direct-form difference equation. Produces the coefficient vectors, the 3 dB point check at the cutoff, passband and attenuation band gains, the filtered signal, and a design verdict from the Schur-Jury stability table. Trigger: digital filter design, Butterworth, bilinear transform, IIR lowpass, highpass filter, cutoff frequency, prewarping, filter coefficients, 3 dB point."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [digital-filter-design, butterworth-filter, bilinear-transform, iir-lowpass, highpass-filter, cutoff-frequency, filter-coefficients]
  version: 0.1.0
  author: Aero Agent Skills
---

# Digital Filter Design (cross-cutting/numerics/digital-filter-design)

Use when the task is designing a digital Butterworth IIR lowpass or
highpass frequency-selective filter from a cutoff frequency, a sample
rate, and an order, then applying it to a sampled signal: prewarping
the analog cutoff for the bilinear transform, placing the normalized
Butterworth poles, mapping them into the z-plane, building the b and a
coefficient vectors with unity DC (lowpass) or Nyquist (highpass) gain,
evaluating the magnitude response in dB, and filtering with the
direct-form difference equation. All coefficients are computed, none
are lookup values. This leaf designs frequency-selective filters only:
state estimation belongs to the gnc-autonomy estimation-filtering pack
(Kalman, alpha-beta, complementary, particle observers), raw flight-test
trace smoothing belongs to flight-test data reduction, and frequency
content analysis belongs to cross-cutting/numerics/fast-fourier-transform.
It pairs with fast-fourier-transform for spectral analysis of the
filtered output and with finite-difference-derivatives for
differentiating noisy signals after the filter has removed the
out-of-band content.

## Domain quick reference

- Prewarped analog cutoff: Omega_a = 2*fs*tan(pi*fc/fs), the frequency
  at which the analog prototype has its 3 dB point so that the digital
  filter reaches -3.0103 dB exactly at the requested cutoff fc. Units
  are SI: Hz for frequencies, samples per second for fs.
- Normalized Butterworth lowpass poles on the unit circle, left half
  plane: s_k = exp(j*pi*(2k + n - 1)/(2n)) for k = 1..n. Every pole has
  a negative real part; complex conjugate pairs give real
  coefficients. For n = 2 the poles are -0.7071068 +/- 0.7071068j.
- Bilinear pole map: z = (2*fs + s)/(2*fs - s). Poles strictly in the
  left half plane map strictly inside the unit circle, which preserves
  stability; the imaginary axis maps onto the unit circle.
- Lowpass transfer function: H(z) = K*(1 + z^-1)^n / A(z), numerator
  coefficients b_k = K*C(n,k) from the binomial expansion, with
  K = sum(a)/2^n so the DC gain at z = 1 is exactly 1.
- Highpass construction: mirror each scaled analog lowpass pole through
  p = Omega_a^2/s (the reciprocal stays in the left half plane), map to
  z, and use b_k = K*C(n,k)*(-1)^k with K = sum(a[k]*(-1)^k)/2^n so the
  Nyquist gain at z = -1 is exactly 1.
- Magnitude response in dB: 20*log10(|H(e^jw)|) with
  e^-jw = exp(-j*2*pi*f/fs) and H evaluated by Horner on z^-1. The 3 dB
  point: -3.0103 dB = 20*log10(1/sqrt(2)) at the cutoff.
- Direct-form difference equation: y[n] = b[0]*x[n] + sum_{k>=1}
  (b[k]*x[n-k] - a[k]*y[n-k]) with a[0] normalized to 1 and zero
  initial conditions (past samples treated as zero).
- Stability check: the Schur-Jury table on the denominator for orders
  1..4 (all roots strictly inside the unit circle); above order 4 the
  check returns not-checked.

## Workflow

1. Fix the operating point: sample rate fs, cutoff fc, filter order n,
   and type (lowpass or highpass).
2. Prewarp the cutoff with prewarp(cutoff_hz, fs) to get the analog
   Omega_a used by the bilinear design.
3. Get the prototype poles with butterworth_poles(order) (normalized,
   unit circle, left half plane) and confirm the layout.
4. Design the filter with design_lowpass(fs, cutoff_hz, order) or
   design_highpass(fs, cutoff_hz, order); both return (b, a) with
   len(b) == len(a) == order + 1 and a[0] == 1. The prewarping
   guarantee puts the -3.0103 dB point exactly at the cutoff.
5. Probe the design at any in-band or stop-band frequency with
   freq_response_db(b, a, freq_hz, fs); magnitudes are in dB.
6. Apply the filter to the sampled signal x with
   apply_filter(b, a, x) (direct form, zero initial condition, output
   length equals input length).
7. Verify the design with filter_design_checks(b, a, fs, cutoff_hz,
   ftype): cutoff gain within 0.02 dB of -3.0103 dB, reference gain at
   DC (1 Hz probe, lowpass) or near Nyquist (fs/2 - 1 Hz probe,
   highpass), Schur-Jury stability for orders 1..4, and the verdict
   string.
8. For spectral analysis of the filtered output, hand the signal to
   cross-cutting/numerics/fast-fourier-transform.

## Worked example

fs = 1000 Hz, lowpass, fc = 100 Hz, order 2.

- prewarp(100, 1000) = 2000*tan(0.1*pi) = 649.8393.
- butterworth_poles(2) = -0.7071068 +/- 0.7071068j.
- design_lowpass(1000, 100, 2): a = [1.0, -1.14298, 0.41280],
  b = [0.067455, 0.134911, 0.067455]; a[0] == 1 and the denominator
  comes from the mapped conjugate pole pair.
- freq_response_db at the cutoff: -3.0103 dB (within 0.02 dB).
- freq_response_db at 10 Hz: -0.0004 dB (passband, within 0.02 dB of
  0 dB).
- freq_response_db at 400 Hz: -39.06 dB (below -30 dB).
- apply_filter to x = [5.0]*400: the last 50 output samples equal 5.0
  to within 0.001 (DC gain 1 after the transient decays).
- filter_design_checks: passband_ok True, stable True (Schur-Jury),
  verdict PASS.

Highpass order 2 at fc = 100 Hz on the same channel:

- design_highpass(1000, 100, 2): a = [1.0, -1.14298, 0.41280] (the
  mirrored poles coincide with the lowpass pole set for even order),
  b = [0.638946, -1.277891, 0.638946], signs alternating.
- freq_response_db at 400 Hz: -0.0005 dB (within 0.05 dB of 0 dB).
- Reference gain at fs/2 - 1 = 499 Hz: 0.0000 dB (within 0.05 dB).
- Attenuation floor: a second order Butterworth highpass attenuates by
  12.72 dB at fc/2 = 50 Hz and reaches below -15 dB by fc/4 = 25 Hz
  (-24.65 dB); the -15 dB contract bound is asserted at 25 Hz.

## Pitfalls

- Skipping the frequency prewarp: the design maps the analog prototype
  through the bilinear transform at prewarp(100, 1000) = 649.8393, and
  the cutoff gain of -3.0103 dB only holds when fc is prewarped before
  the mapping.
- Asserting spec bounds the standard method cannot meet: an order-2
  Butterworth highpass attenuates only 12.72 dB at fc/2 (a 12 dB per
  octave rolloff from the -3.01 dB point), so the -15 dB contract bound
  is asserted at 25 Hz where it genuinely holds, not at 50 Hz.
- Designing outside the supported orders: the design functions accept
  order 1..8 (butterworth_poles 1..10), probe frequencies must lie in
  (0, fs/2), and fs <= 0, cutoff <= 0, cutoff >= fs/2, empty or
  non-finite samples, and unknown ftype all raise ValueError.
- Reading the stability verdict above order 4 as a guarantee: stability
  is verified as stable True only for orders 1..4 and returns None above
  order 4, while a fabricated denominator with a root at z = 1.1
  reports stable False with a FAIL verdict.
- Reading the DC response from the transient: a constant input of 5.0
  settles to 5.0 within 0.001 only after the transient decays (the last
  50 samples of the worked record), not from the leading samples.
- Expecting highpass coefficients to look like lowpass ones: the
  even-order highpass shares the lowpass denominator (a = [1.0,
  -1.14298, 0.41280]) while the numerator signs alternate (b =
  [0.638946, -1.277891, 0.638946]).

## Verification

- Confirm prewarp(100, 1000) returns 649.8393925 (spec anchor 649.8393
  within 1e-3).
- Confirm the lowpass cutoff gain is -3.0103 +/- 0.02 dB at fc and the
  order-1 lowpass hits the same anchor with DC gain 1.
- Confirm the analytic magnitude identity: the module value at any
  frequency equals 10*log10(1/(1 + r^(2n))) dB with r the ratio of the
  prewarped tangents, lowpass and highpass.
- Confirm steady state: a constant input of 5.0 settles to 5.0 within
  0.001 (DC gain exactly 1), and apply_filter with b = [1], a = [1] is
  the identity.
- Confirm stability verdicts: stable True for designed orders 1..4,
  stable None above order 4, and a fabricated denominator with a root
  at z = 1.1 reports stable False and a FAIL verdict.
- Confirm every non-physical input raises ValueError: fs <= 0,
  cutoff <= 0, cutoff >= fs/2, order outside 1..8 for the design
  functions (1..10 for butterworth_poles), probe frequencies outside
  (0, fs/2), empty or non-finite sample lists, and unknown ftype.
- Recorded assumption: the spec worked example asked for "below -15 dB
  at 50 Hz" on the order-2 highpass with fc = 100 Hz; the standard
  Butterworth magnitude gives -12.72 dB at fc/2 (a 12 dB per octave
  rolloff measured from the -3.01 dB point reaches -15 dB only one
  third of an octave below cutoff), so the module implements the
  standard method and the contract asserts the -15 dB floor at 25 Hz
  where the bound genuinely holds. All other spec anchors match the
  module output exactly.
- Run the contract test offline: python3
  scripts/test_digital_filter_design.py (32 tests, deterministic).

## Related leaves

- cross-cutting/numerics/fast-fourier-transform: spectral analysis of
  the filtered signal, the frequency-domain partner of this leaf.
- cross-cutting/numerics/finite-difference-derivatives: differentiating
  the filtered (denoised) signal with controlled step-size error.
- cross-cutting/numerics/numerical-integration: quadrature of smooth
  signals, complementary to filtering when the goal is an integral
  rather than a cleaned time series.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_digital_filter_design.py

The test covers the prewarp anchor (649.8393), pole placement for
orders 1, 2, and 3 with symmetry checks, coefficient shapes
(len b == len a == order + 1, a[0] == 1), the lowpass 3 dB cutoff
gain, the passband gain at 10 Hz, the attenuation band at 400 Hz, the
DC steady state of a constant input, the identity round trip, the
impulse response sanity, the order-1 anchor, highpass cutoff and
reference gains near Nyquist, the alternating highpass numerator,
the -15 dB attenuation floor at fc/4 with the closed-form magnitude
match at fc/2, the 2 Hz cutoff on a 50 Hz channel scenario, the
Schur-Jury stability verdicts for orders 2, 4, and 6 (not-checked),
the unstable-denominator FAIL verdict, and ValueError rejection of
non-physical inputs. Runs in well under a second.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the
  numerics-pack public-domain reference set; Butterworth prototype
  design and the bilinear transform are classical digital-filter
  methodology (Hamming and Oppenheim and Schafer style summaries),
  paraphrase-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

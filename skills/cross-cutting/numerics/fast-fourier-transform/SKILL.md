---
name: fast-fourier-transform
description: "Use when you must compute the frequency content of a sampled signal with the discrete Fourier transform or the radix-2 fast Fourier transform: apply the DFT definition for small N, use the Cooley-Tukey decomposition when N is a power of two, extract the magnitude and phase spectrum, and recover the time series with the inverse FFT. Produces the complex spectrum, the magnitude, phase, and power spectra, and the reconstructed signal with Parseval energy checks that gate spectral analysis of sampled time series. Trigger: fast fourier transform, discrete fourier transform, cooley tukey, radix 2, magnitude spectrum, phase spectrum, inverse fft, frequency bin, parseval."
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
  tags: [fast-fourier-transform, discrete-fourier-transform, cooley-tukey, radix-2, magnitude-spectrum, phase-spectrum, inverse-fft, parseval]
  version: 0.1.0
  author: Aero Agent Skills
---

# Fast Fourier Transform (cross-cutting/numerics/fast-fourier-transform)

Use when the task is transforming a sampled signal into its frequency
content: computing the DFT or the radix-2 FFT, extracting the
magnitude and phase spectrum, or inverting back to the time series.

## Domain quick reference

- DFT definition: X[k] = sum_{n=0}^{N-1} x[n] * exp(-2 pi i k n / N),
  one complex sinusoid per bin k. Worked anchor for N = 4 with
  x = [1, 2, 3, 4]: X = [10, -2+2i, -2, -2-2i]. The transform is
  exact by definition: it is a change of basis, not an approximation.
- Impulse anchor: x = [1, 0, 0, 0] gives X = [1, 1, 1, 1], all bins
  equal to one, because only the n = 0 sample contributes.
- Radix-2 Cooley-Tukey decomposition: requires N a power of two,
  splits the sequence into even and odd indexed samples, transforms
  each half recursively, and recombines with the twiddle factors
  exp(-2 pi i k / N). Cost drops from O(N^2) for the plain DFT to
  O(N log2 N). fft([1, 2, 3, 4]) equals dft([1, 2, 3, 4]) exactly in
  value: [10, -2+2i, -2, -2-2i].
- Inverse FFT: x[n] = (1/N) sum_{k=0}^{N-1} X[k] * exp(+2 pi i k n / N),
  the forward transform with the sign of the exponent flipped and a
  1/N scale. Round trip: ifft(fft(x)) == x; ifft([1, 1, 1, 1]) =
  [1, 0, 0, 0].
- Magnitude and phase spectrum: |X[k]| and arg(X[k]) per bin. A pure
  sine at bin k0 with N samples peaks at bins k0 and N-k0 with
  magnitude N/2: for x[n] = sin(pi n / 2), N = 8, the magnitude
  spectrum is 4.0 at bins 2 and 6 and near zero elsewhere; the phase
  is -pi/2 at bin 2 and +pi/2 at bin 6. A cosine at its bin gives
  phase 0.
- Parseval energy check: sum |x[n]|^2 = (1/N) sum |X[k]|^2. Worked
  anchor: x = [1, 2, 3, 4] gives 30 = 120/4, so parseval_ratio
  returns 1.0. Any transform implementation that breaks this ratio is
  wrong, no matter how clean the spectrum looks.
- All functions are deterministic and stdlib-only (math, cmath); no
  network, no third-party numerical libraries.

## Workflow

1. Collect the sampled sequence x (real or complex values) and its
   length N.
2. For a general N use the DFT definition (dft). For a power-of-two N
   use the radix-2 FFT (fft), which returns the same values in
   O(N log2 N) time.
3. Extract the magnitude, phase, and power spectra with
   magnitude_spectrum, phase_spectrum, and power_spectrum; identify
   the dominant bin k0 and its mirror N-k0.
4. Verify the transform: check parseval_ratio(x) equals 1.0 and the
   round trip ifft(fft(x)) recovers x within floating point
   tolerance.
5. Report the peak bin, its magnitude (N/2 for a pure sine), and the
   physical frequency k0 * fs / N when the sample rate fs is known.

## Pitfalls

- Calling fft or ifft on a non-power-of-two length: both raise
  ValueError; use dft for a general N. The spectrum helpers
  (magnitude_spectrum, phase_spectrum, power_spectrum) dispatch
  automatically and accept any N.
- Passing an empty sequence: every function raises ValueError; there
  is no spectrum of nothing.
- Confusing the DFT with numerical integration: quadrature rules
  (trapezoid, Simpson, Gauss-Legendre) approximate the integral of a
  function and carry error estimates; the DFT sums weighted samples
  and is exact by definition, with no quadrature error to estimate.
- Confusing the spectrum with interpolation: interpolation fits
  values between tabulated data points; the DFT is a global change of
  basis of the whole sequence into sinusoids, never a table lookup
  between bins.
- Confusing the transform with finite differences:
  finite-difference-derivatives estimates local slopes of a function
  with step-size truncation error; the FFT is a decomposition of a
  sequence into frequency components and produces no derivative
  estimates at all.
- Reading the peak bin as the physical frequency: bin k is the
  frequency k * fs / N, not k Hz, and for a real signal the mirror
  bin N-k duplicates the peak, so both bins report the same tone.
- Expecting a real spectrum from a real input: the spectrum is
  complex; only the magnitude is real, and the phase must be read
  from arg(X[k]), which the phase spectrum returns on (-pi, pi].
- Forgetting the 1/N scale on the inverse: ifft carries the 1/N;
  omitting it returns N times the original signal. The Parseval ratio
  and the round trip both catch this scaling error.

## Behavior contract (gate 3)

The DFT, radix-2 Cooley-Tukey FFT, inverse FFT, magnitude, phase, and
power spectra, and the Parseval energy check are exercised by the
gate 3 contract test: scripts/test_fast_fourier_transform.py against
scripts/fast_fourier_transform_logic.py (stdlib unittest, offline,
27 cases). Run: python3 scripts/test_fast_fourier_transform.py

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the
  pack's public-domain reference set; the DFT and the Cooley-Tukey
  decomposition are classical numerical-analysis methodology
  (Abramowitz and Stegun), summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

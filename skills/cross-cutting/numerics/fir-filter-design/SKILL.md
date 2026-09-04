---
name: fir-filter-design
description: "Use when you must design a linear-phase finite-impulse-response lowpass filter with the windowed-sinc method: build the ideal lowpass impulse response from the cutoff frequency and the sample rate, apply a selected window (rectangular, Hann, Hamming, or Blackman), normalize the coefficient vector to unity DC gain, evaluate the magnitude response in dB at any frequency as the real cosine sum of the symmetric tap set, return the group delay of the taps, and filter a sampled signal by direct convolution. Produces the coefficient vector, the magnitude response checks (passband gain, -6 dB point at the cutoff, stopband attenuation), the group delay, and the filtered signal that gate a digital filter design task. Trigger: fir-filter-design, windowed-sinc, fir lowpass, finite impulse response, hamming window, filter taps, cutoff frequency, linear phase, magnitude response dB, group delay."
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
  tags: [fir-filter-design, windowed-sinc, finite-impulse-response, linear-phase-filter, fir-lowpass, filter-taps, hamming-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# FIR Filter Design (cross-cutting/numerics/fir-filter-design)

Use when the task is designing a linear-phase finite-impulse-response
(FIR) lowpass filter with the windowed-sinc method: truncating the
ideal lowpass impulse response to a finite symmetric tap set, shaping
the sidelobes with a selected window (rectangular, Hann, Hamming, or
Blackman), normalizing the coefficients to unity DC gain, probing the
magnitude response in dB at any frequency through the real cosine sum
of the symmetric taps, and filtering a sampled signal by direct
convolution. Every coefficient is computed, none are lookup values.
The taps are symmetric about an integer center, so the filter is
linear phase with a constant group delay of (N-1)/2 samples and needs
no recursion and no feedback path: the all-zero transfer function is
unconditionally bounded. Frequency-content analysis of the filtered
output belongs to cross-cutting/numerics/fast-fourier-transform; delay
estimation between two filtered traces belongs to
cross-cutting/numerics/cross-correlation-analysis. This leaf pairs
with digital-filter-design, the numerics partner that covers the
feedback-form frequency-selective family (a separate design method
space that this leaf does not implement).

## Domain quick reference

- Ideal lowpass impulse response (windowed-sinc prototype), centered
  at tap index (N-1)/2:
  h[n] = sin(2*pi*fc/fs * (n - (N-1)/2)) / (pi * (n - (N-1)/2)), with
  the center tap set to the limit value 2*fc/fs.
- Window weights w[n] for n = 0..N-1 (denominator N-1): rectangular
  all 1.0; hann 0.5 - 0.5*cos(2*pi*n/(N-1)); hamming
  0.54 - 0.46*cos(2*pi*n/(N-1)); blackman
  0.42 - 0.5*cos(2*pi*n/(N-1)) + 0.08*cos(4*pi*n/(N-1)). The windows
  are symmetric, so the windowed taps stay symmetric (linear phase).
- Designed taps: b[n] = h[n] * w[n], then normalized by the sum of
  the weighted taps so the DC gain sum(b) is exactly 1.0. An odd
  number of taps keeps the center integer; even N is rejected.
- Magnitude response: H(f) = sum_n b[n] * cos(2*pi*f/fs * (n -
  (N-1)/2)) is the real response of the symmetric tap set with the
  linear phase term dropped; |H(f)| is the linear gain, and
  20*log10(|H(f)|) the magnitude in dB.
- The windowed-sinc design places the -6 dB point (gain 0.5, the
  midpoint of the transition) at the requested cutoff fc; passband
  ripple is small near DC and the stopband floor follows the window
  sidelobe level (about -31 dB rectangular, -44 dB Hann, -53 dB
  Hamming, -74 dB Blackman asymptotic sidelobe peaks).
- Group delay of the symmetric tap set: (N-1)/2 samples, constant for
  every frequency because the phase is exactly linear.
- Direct-form convolution filter: y[n] = sum_k b[k] * x[n-k], input
  treated as zero outside its range, output the same length as the
  input.
- Units are SI throughout: Hz for frequencies, samples per second for
  fs. NACA TR-824 anchors the numerics-pack public-domain reference
  set; the relations above are classical digital filter methodology
  (Hamming, Oppenheim and Schafer style), summary-only.

## Workflow

1. Fix the operating point: sample rate fs, cutoff frequency fc
   (below fs/2), tap count N (odd), and the window.
2. Get the window weights with window_coefficients(window, num_taps)
   and confirm their symmetry about the center.
3. Build the ideal prototype with ideal_lowpass_taps(cutoff_hz,
   sample_rate_hz, num_taps); the center tap equals 2*fc/fs.
4. Design the filter with design_lowpass(cutoff_hz, sample_rate_hz,
   num_taps, window); the returned dict carries the DC-normalized
   coefficient vector, the window name, the group delay in samples,
   and the achieved DC gain (1.0 to float precision).
5. Probe the design at any in-band or stop-band frequency with
   gain_at (linear) or magnitude_response_db (dB); the cutoff gain
   should sit near 0.5 (-6 dB).
6. Run the self-check with design_check(coefficients, cutoff_hz,
   sample_rate_hz) to confirm the DC gain, the cutoff gain in dB, the
   stopband gain at 2*fc, and the stopband attenuation in dB.
7. Apply the filter to the sampled signal with filter_signal
   (direct convolution, zero-padded boundaries, same output length);
   allow the first (N-1)/2 samples to settle before reading
   steady-state amplitudes.
8. Confirm the deterministic checks with the contract test
   scripts/test_fir_filter_design.py.

## Worked example

Sample rate fs = 1000 Hz, cutoff fc = 100 Hz, N = 101 taps, Hamming
window (design_lowpass(100, 1000, 101, "hamming")). Real module
outputs:

- Ideal center tap: 2*fc/fs = 0.2 (taps[50]).
- Coefficients symmetric: max |b[n] - b[100-n]| = 1.4e-17 (linear
  phase to float precision).
- DC gain after normalization: 1.0 (sum(b) = 1.0).
- Group delay: (101 - 1)/2 = 50.0 samples.
- Gain at 50 Hz (passband): 1.00319, within 0.98-1.02.
- Gain at 100 Hz (cutoff): 0.50039, magnitude -6.0138 dB, within
  0.45-0.55 (the -6 dB point sits at the cutoff).
- Gain at 150 Hz: 0.000975 (-60.2 dB), below 0.01.
- Gain at 300 Hz: 0.000263 (-71.6 dB), below 0.001.
- design_check: dc_gain 1.0, cutoff_gain_db -6.0138 dB,
  stopband_gain_db (at 200 Hz) -65.144 dB, stopband_attenuation_db
  65.144 dB.
- Filtering a 1.0-amplitude 50 Hz cosine at fs = 1000: the steady-
  state output amplitude after the first 50 samples is 1.00319,
  within 0.95-1.05.
- Filtering a 1.0-amplitude 10 Hz sine (fully in-band): the tail
  amplitude is 1.00296, amplitude preserved within 5%.
- Window trade at N = 51, fc = 100 Hz: stopband gain at 200 Hz is
  -36.9 dB (rectangular), -61.7 dB (Hamming), -68.2 dB (Hann), and
  -79.5 dB (Blackman); wider main lobe for deeper stopband.

Recorded assumptions: the defining window formulas divide by N-1, so
a degenerate single tap (N = 1) takes the center limit value 1.0 for
every window; design_check probes the stopband at 2*fc, which is only
physical while 2*fc stays at or below the Nyquist frequency, so
design_check requires fc <= fs/4 and raises ValueError otherwise.

## Pitfalls

- Asking for an even number of taps: even N is rejected because the
  center tap index (N-1)/2 must stay integer for the windowed taps to
  remain symmetric (linear phase).
- Running design_check with the cutoff above fs/4: the stopband probe
  sits at 2*fc and is only physical while 2*fc stays at or below the
  Nyquist frequency, so design_check requires fc <= fs/4 and raises
  ValueError otherwise.
- Expecting a brick-wall response at the cutoff: the windowed-sinc
  design places the -6 dB point at fc with a transition band whose
  width follows the window, and the stopband floor follows the window
  sidelobe level (about -53 dB for Hamming at N = 51).
- Forgetting the group delay when comparing input and output: the
  symmetric tap set delays by (N-1)/2 = 50 samples at N = 101, so the
  steady-state amplitude checks apply only after the delay.
- Passing non-physical design inputs: even num_taps, num_taps < 1,
  fc <= 0, fs <= 0, fc >= fs/2, unknown window names, negative or
  above-Nyquist probe frequencies, and empty coefficient or signal
  lists all raise ValueError.
- Choosing a window without the sidelobe trade: at N = 51, fc = 100 Hz
  the stopband gain at 200 Hz runs from -36.9 dB (rectangular) to
  -79.5 dB (Blackman) at the price of a wider main lobe.

## Verification

- Confirm design_lowpass(100, 1000, 101, "hamming") returns a dict
  with exactly the keys coefficients, num_taps, cutoff_hz,
  sample_rate_hz, window, group_delay_samples, dc_gain, and that
  coefficients[n] == coefficients[100-n] within 1e-12.
- Confirm the DC gain is within 1e-9 of 1.0 and the magnitude
  response at 0 Hz is 0 dB.
- Confirm gain_at(b, 100, 1000) returns 0.50039 (about -6 dB at the
  cutoff), gain_at(b, 50, 1000) returns 1.00319, and gain_at(b, 150,
  1000) returns 0.000975 with the spec bounds (0.45-0.55 at the
  cutoff, below 0.01 at 150 Hz, below 0.001 at 300 Hz).
- Confirm the group delay identity group_delay_samples(101) = 50.0
  and the round trips: an impulse input reproduces the coefficient
  vector exactly, a constant 5.0 input settles to 5.0 within 0.001,
  and a below-cutoff 10 Hz sine keeps its amplitude within 5% after
  the group delay.
- Confirm every non-physical input raises ValueError: even num_taps,
  num_taps < 1, fc <= 0, fs <= 0, fc >= fs/2, unknown window,
  negative or above-Nyquist probe frequency, and empty coefficient or
  signal lists.
- Run the contract test offline: python3
  scripts/test_fir_filter_design.py (34 tests, deterministic).

## Related leaves

- cross-cutting/numerics/digital-filter-design: the numerics partner
  covering the feedback-form frequency-selective family (separate
  design method space, analog-prototype mapped coefficients).
- cross-cutting/numerics/fast-fourier-transform: spectral analysis of
  the filtered signal, the frequency-domain partner of this leaf.
- cross-cutting/numerics/finite-difference-derivatives: differentiating
  the filtered (denoised) signal with controlled step-size error.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fir_filter_design.py

The test covers the window formulas (rectangular, Hann, Hamming,
Blackman) and their symmetry, the ideal-prototype center tap limit
2*fc/fs, the exact convenience-dict keys, the worked-example anchors
(DC gain 1.0, gain 1.00319 at 50 Hz, gain 0.50039 and -6.0138 dB at
the 100 Hz cutoff, gains below 0.01 at 150 Hz and below 0.001 at 300
Hz, group delay 50.0), coefficient symmetry within 1e-12, the
steady-state amplitude of a filtered 50 Hz cosine within 0.95-1.05,
the 10 Hz sine round trip within 5%, the magnitude response in dB
matching 20*log10 of the linear gain, the design self-check anchors,
and ValueError rejection of every non-physical input in the spec
validation list. Runs in well under a second.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the
  numerics-pack public-domain reference set; windowed-sinc FIR design
  and its windows are classical digital filter methodology (Hamming,
  Oppenheim and Schafer style summaries), paraphrase-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

# Wave-31 leaf spec: fir-filter-design (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/fir-filter-design/
- Pack: numerics (19 siblings). Direct sibling: digital-filter-design owns the
  Butterworth IIR lowpass/highpass design (bilinear transform, poles, Schur-Jury
  stability). The FINITE impulse response (FIR) design space is entirely absent:
  no leaf computes windowed-sinc coefficients, linear-phase taps, or FIR
  magnitude responses. This leaf fills that gap with a finite-impulse-response
  design method, NOT an IIR recursion.
- Standards ids: naca-tr-824 (reference-only, same convention as the IIR
  sibling). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Design a linear-phase finite-impulse-response (FIR) lowpass filter with the
windowed-sinc method: build the ideal lowpass impulse response from the cutoff
frequency and the sample rate, apply a selected window (rectangular, Hann,
Hamming, or Blackman), normalize the coefficient vector, evaluate the
magnitude response in dB at any frequency by a real cosine sum, return the
group delay of the symmetric tap set, and filter a sampled signal by direct
convolution. Produces the coefficient vector, the magnitude response checks
(passband gain, -6 dB point at the cutoff, stopband attenuation), the group
delay, and the filtered signal that gate a digital filter design task.

Does NOT do: IIR recursive filters, Butterworth pole mapping, bilinear
transform, or Schur-Jury stability checks (digital-filter-design owns those);
FFT-based frequency analysis (fast-fourier-transform owns the DFT/FFT);
cross-correlation or delay estimation (cross-correlation-analysis); moving
average or other smoothing windows as a separate estimator. Windowed-sinc FIR
only: symmetric taps, linear phase, no recursion, no stability test needed.

## Model (implement exactly)

Module constants:
- PI = math.pi.
- WINDOWS = ("rectangular", "hann", "hamming", "blackman").

Functions (pure stdlib):
- window_coefficients(window, num_taps) -> list[float]: window weights w[n]
  for n = 0..N-1: rectangular all 1.0; hann 0.5 - 0.5*cos(2*pi*n/(N-1));
  hamming 0.54 - 0.46*cos(2*pi*n/(N-1)); blackman
  0.42 - 0.5*cos(2*pi*n/(N-1)) + 0.08*cos(4*pi*n/(N-1)). ValueError if
  num_taps < 1 or not an integer, or window not in WINDOWS.
- ideal_lowpass_taps(cutoff_hz, sample_rate_hz, num_taps) -> list[float]:
  h[n] = sin(2*pi*fc/fs*(n - (N-1)/2)) / (pi*(n - (N-1)/2)) with the center
  tap (n = (N-1)/2) set to 2*fc/fs (the limit value). ValueErrors: fc <= 0,
  fs <= 0, fc >= fs/2 (cutoff must be below Nyquist), num_taps < 1.
- design_lowpass(cutoff_hz, sample_rate_hz, num_taps, window="hamming") ->
  dict: coefficient vector b = ideal taps * window weights, normalized by
  dividing by the sum of the taps so the DC gain is 1.0; returns
  {coefficients, num_taps, cutoff_hz, sample_rate_hz, window,
  group_delay_samples: (num_taps-1)/2, dc_gain: sum(b)}. num_taps must be odd
  (ValueError if even) so the taps are symmetric about an integer center.
- magnitude_response_db(coefficients, frequency_hz, sample_rate_hz) -> float:
  20*log10(|H(f)|) with H(f) = sum_n b[n] * cos(2*pi*f/fs*(n - (N-1)/2))
  (real response of the symmetric tap set; the linear phase term is dropped
  for the magnitude). ValueErrors: fs <= 0, f < 0, f > fs/2, empty
  coefficients.
- gain_at(coefficients, frequency_hz, sample_rate_hz) -> float: linear
  magnitude |H(f)| as defined above.
- group_delay_samples(num_taps) -> float: (num_taps - 1)/2. ValueError if
  num_taps < 1.
- filter_signal(coefficients, signal) -> list[float]: direct-form convolution
  y[n] = sum_k b[k] * x[n-k] with x treated as zero outside its range
  (zero-padded boundaries) and the output the SAME length as the input.
  ValueError if coefficients empty or signal empty.
- design_check(coefficients, cutoff_hz, sample_rate_hz) -> dict: passband
  gain at 0 Hz (should be about 1.0 or 0 dB), gain at the cutoff (should be
  about 0.5 or -6 dB for the windowed-sinc design), gain at 2*cutoff
  (stopband check), returns {dc_gain, cutoff_gain_db, stopband_gain_db,
  stopband_attenuation_db}.

## Worked example

Sample rate fs = 1000 Hz, cutoff fc = 100 Hz, N = 101 taps, Hamming window.

Deterministic anchors (run your module, take the printed values as the assert
targets, then CHECK the magnitude bounds):
- DC gain within 0.99-1.01 after normalization.
- Gain at 50 Hz within 0.98-1.02 (passband).
- Gain at 100 Hz within 0.45-0.55 (about -6 dB at the cutoff).
- Gain at 150 Hz below 0.01 (-40 dB or better).
- Gain at 300 Hz below 0.001 (-60 dB or better).
- group delay = 50.0 samples.
- Filtering a 1.0-amplitude 50 Hz cosine at fs = 1000 with the designed
  filter returns a steady-state output amplitude within 0.95-1.05 after the
  first 50 samples (the group delay).
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: even num_taps, num_taps < 1, fc <= 0, fs <= 0, fc >= fs/2,
  unknown window, f > fs/2, negative frequency, empty coefficient or signal
  list.
- Symmetry: coefficients[n] == coefficients[N-1-n] within 1e-12 for a Hamming
  design (linear phase).
- DC gain of the normalized filter is within 1e-9 of 1.0.
- Magnitude response of a pure delay-free symmetric filter at 0 Hz equals the
  DC gain.
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Round-trip: filtering a signal that is entirely below the cutoff (e.g. a
  10 Hz sine at fs = 1000) preserves amplitude within 5% after the group
  delay.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-fir-filter-design.yaml)

Query 1 (copy verbatim):
  "design a linear phase finite impulse response lowpass filter with the windowed sinc method: hamming window coefficients for a 100 hertz cutoff at 1000 hertz sample rate"
  intent: "cross-cutting; FIR windowed-sinc lowpass coefficient design"
  expected_skill: "cross-cutting/numerics/fir-filter-design"
Query 2 (copy verbatim):
  "compute the magnitude response in dB and the group delay of a symmetric finite impulse response filter tap set for a sampled signal"
  intent: "cross-cutting; FIR linear-phase magnitude response and group delay"
  expected_skill: "cross-cutting/numerics/fir-filter-design"
Task ids: w31-fir-filter-design-1 and -2.

Forbidden tokens that belong to siblings: do NOT use Butterworth, bilinear
transform, IIR, recursive, poles, Schur-Jury, stability table, prewarping,
highpass (unless explicitly combined as a lowpass-only claim: this leaf is a
LOWPASS design; do not claim highpass), cutoff frequency phrasing that implies
analog prewarping. Do NOT claim FFT/DFT or correlation outputs.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design a linear-phase finite-impulse-
response lowpass filter with the windowed-sinc method:" and include the
outputs listed in the Claim. First tag: fir-filter-design. Additional tags
only: windowed-sinc, finite-impulse-response, linear-phase-filter,
fir-lowpass, filter-taps, hamming-window. NEVER single generic words
(filter, design, window, signal). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

# Wave-33 leaf spec: power-spectral-density (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/power-spectral-density/
- Pack: numerics. Sibling scope check: fast-fourier-transform owns the
  single-record DFT spectrum (per-bin |X[k]|^2, no window, no segment
  averaging, no Hz scaling - verified in its logic); fir-filter-design
  uses Hamming for tap truncation only; digital-filter-design owns
  filter coefficients; cross-correlation-analysis owns time-domain lag;
  hypothesis-testing "Welch" is the t-test (unrelated); structures/
  loads/random-vibration-analysis CONSUMES an input PSD but no leaf
  estimates one. This leaf owns Welch-averaged periodogram PSD
  estimation.
- Standards id: naca-tr-824 (reference-only; numerics anchor per
  standards-map convention - the methodology is generic summary).
  Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Estimate the one-sided power spectral density (units^2/Hz) of a
stochastic sampled signal by Welch's averaged modified periodogram:
Hann-windowed, overlapping segments, density-scaled, with the
equivalent noise bandwidth and the integrated total power. Produces the
PSD array and its frequency axis for random-vibration and noise
surveys - the measurement-to-spectrum step that complements the
single-record DFT spectrum leaf.

Does NOT do: single-record DFT / raw |X[k]|^2 spectrum
(fast-fourier-transform); filter design (digital/fir leaves); time-
domain correlation (cross-correlation); statistical Welch t-test
(hypothesis-testing); SDOF response to a given PSD (structures/loads/
random-vibration-analysis consumes a PSD input).

## Model (implement exactly)

Conventions: sampling frequency fs (Hz), segment length M samples
(power of two for the FFT), overlap fraction (default 0.5). One-sided
density scaling: P[k] = 2 |X[k]|^2 / (fs * sum(w^2)) for interior bins
(k = 1..M/2 - 1); DC (k=0) and Nyquist (k = M/2) are NOT doubled.
Hann window: w[n] = 0.5 - 0.5 cos(2 pi n / M). Segment periodograms
are averaged. Equivalent noise bandwidth ENBW = fs * sum(w^2) /
(sum(w))^2. Total power = sum over bins of P[k] * df (df = fs / M) =
variance for a zero-mean signal (Parseval-style check).

Functions (pure stdlib):

- hann_window(m) -> list of m weights.
- periodogram(x_segment, fs, window) -> (freqs, P) one-sided density
  array with the scaling above. Use an iterative radix-2 FFT or the
  leaf's own DFT for the transform (pure stdlib, no numpy); M power of
  two required (ValueError otherwise).
- _fft(x) -> complex DFT via radix-2 Cooley-Tukey (internal helper;
  deterministic).
- welch_psd(x, fs, seg_len, overlap=0.5) -> (freqs, PSD) mean of the
  segment periodograms. ValueError on seg_len not power of two, fs <= 0,
  overlap outside [0, 1), x shorter than seg_len.
- equivalent_noise_bw(window, fs) -> fs * sum(w^2) / (sum(w))^2.
- psd_total_power(psd, df) -> sum(P) * df.
- psd_summary(x, fs, seg_len, overlap=0.5) -> dict {freqs, psd,
  enbw_hz, df_hz, total_power, peak_density, peak_freq_hz}.

## Worked example

fs = 1024 Hz, M = 256, Hann window, 50% overlap (63 segments for a
63*128+256 sample record; use a record of 8192 samples for the test:
(8192-256)/128 + 1 = 63 segments exactly). Sine at 60 Hz (bin 15
exactly, 60 = 15 * 1024/256) amplitude A = 1.0.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- hann_window sum about 128.0 (M/2 for even M), sum of squares about
  96.0 (3M/8) for M = 256.
- ENBW = 1024 * 96 / (128^2) = 6.0 Hz.
- Peak density about 0.083333333 = A^2 / (2 * ENBW) with A = 1 (ratio
  1.0 to ~1e-9).
- Integrated one-sided power about 0.500000000 = A^2 / 2 (exact).
- A = 0.5 -> peak about 0.020833333 (4x lower = 6.02 dB).
- Tone + seeded 0.2-sigma noise: peak about 0.0836 vs noise floor about
  5.6e-4 (SNR ~150x) - reproducible with a fixed seed.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: seg_len not a power of two; fs <= 0; overlap outside
  [0,1); x shorter than seg_len.
- Hann window sums: sum ~ M/2, sum-sq ~ 3M/8 (M = 256: 128.0 and 96.0).
- Pure-sine anchors: peak density A^2/(2 ENBW); integrated power A^2/2
  (both to 1e-6 relative).
- Amplitude law: A=0.5 peak is exactly 1/4 of the A=1 peak.
- DC and Nyquist bins are not doubled (a DC-only signal integrates to
  its variance with the documented scaling).
- Determinism: seeded-noise run reproduces the same PSD (fixed seed).
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-power-spectral-density.yaml)

Query 1 (copy verbatim):
  "estimate the power spectral density of a measured acceleration time history with a welch averaged periodogram in g squared per hertz"
  intent: "cross-cutting; Welch-averaged periodogram PSD estimation of a time history"
  expected_skill: "cross-cutting/numerics/power-spectral-density"
Query 2 (copy verbatim):
  "hann window segment averaged psd and equivalent noise bandwidth for a random vibration survey of a sampled signal"
  intent: "cross-cutting; Hann-window segment-averaged PSD and ENBW for a random vibration survey"
  expected_skill: "cross-cutting/numerics/power-spectral-density"
Task ids: w33-power-spectral-density-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the power spectral
density of a stochastic signal:" and include the outputs in the Claim.
First tag: power-spectral-density. Additional tags ONLY:
welch-periodogram, hann-window, spectral-density-estimation,
equivalent-noise-bandwidth, random-vibration-survey,
segment-averaging. NEVER single generic words (spectrum, density,
window, power, signal, frequency, fft, noise). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): DFT, discrete Fourier
transform, Parseval, single record (fast-fourier-transform); filter
taps, windowed sinc (fir-filter-design); digital filter, Butterworth
(digital-filter-design); cross correlation, lag (cross-correlation-
analysis); Miles, SDOF response (structures random-vibration-analysis).
The tokens "Welch periodogram", "power spectral density", "segment
averaged", "equivalent noise bandwidth" are this leaf's own.

Tags: [power-spectral-density, welch-periodogram, hann-window,
spectral-density-estimation, equivalent-noise-bandwidth,
random-vibration-survey, segment-averaging]

Sibling-citation lines for Related leaves:
cross-cutting/numerics/fast-fourier-transform (the single-record
spectrum sibling; this leaf adds windowing, segment averaging and
density scaling),
cross-cutting/numerics/fir-filter-design,
structures/loads/random-vibration-analysis (a PSD consumer).

Ledger Standard: naca-tr-824.

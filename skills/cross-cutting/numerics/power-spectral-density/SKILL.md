---
name: power-spectral-density
description: "Use when you must estimate the power spectral density of a stochastic signal: Welch averaged periodogram estimation with a Hann window, overlapping segments (default 50 percent), and one-sided density scaling in units squared per hertz. Produces the PSD array and its frequency axis, the equivalent noise bandwidth, the integrated total power, and a peak summary for random-vibration and noise surveys of measured acceleration or response time histories. Trigger: power spectral density, welch periodogram, hann window, segment averaged, equivalent noise bandwidth, random vibration survey, g squared per hertz, spectral density estimation."
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
  tags: [power-spectral-density, welch-periodogram, hann-window, spectral-density-estimation, equivalent-noise-bandwidth, random-vibration-survey, segment-averaging]
  version: 0.1.0
  author: Aero Agent Skills
---

# Power Spectral Density (cross-cutting/numerics/power-spectral-density)

Use when the task is estimating the one-sided power spectral density
(units^2/Hz) of a stochastic sampled signal by Welch's averaged
modified periodogram: Hann-windowed, overlapping segments,
density-scaled, with the equivalent noise bandwidth and the integrated
total power. This is the measurement-to-spectrum step for
random-vibration and noise surveys, complementing the single-record
spectrum leaf that transforms one record without windowing, segment
averaging, or Hz scaling. Implemented in pure stdlib Python, offline
and deterministic.

## Domain quick reference

- Welch method: split the record into segments of M samples, multiply
  each by the Hann window w[n] = 0.5 - 0.5 cos(2 pi n / M), transform
  each windowed segment with the leaf's iterative radix-2 Cooley-Tukey
  transform, scale each to a one-sided density periodogram, and
  average over segments. Segments start every hop = M * (1 - overlap)
  samples; the default overlap is 50 percent, giving 63 segments for
  an 8192-sample record at M = 256: (8192 - 256) / 128 + 1.
- One-sided density scaling for a real segment, X the transform of the
  windowed segment and w the window: P[k] = 2 |X[k]|^2 / (fs *
  sum(w^2)) on interior bins k = 1..M/2 - 1. The DC bin (k = 0) and
  the Nyquist bin (k = M/2) are NOT doubled: P[0] and P[M/2] keep the
  single-sided numerator |X|^2 / (fs * sum(w^2)).
- Frequency axis: freqs[k] = k * fs / M for k = 0..M/2, so the bin
  width df = fs / M. A 60 Hz tone at fs = 1024 Hz with M = 256 lands
  on bin 15 exactly (60 = 15 * 4).
- Equivalent noise bandwidth: ENBW = fs * sum(w^2) / (sum(w))^2, the
  Hz width of an ideal rectangular filter passing the same white-noise
  power as the window. Hann at M = 256: 1024 * 96 / 128^2 = 6.0 Hz.
- Total power = sum_k P[k] * df. With this scaling the integral equals
  the variance for a zero-mean signal and the mean square otherwise,
  the energy-conservation check that catches scaling bugs.
- Peak density of a pure sine of amplitude A on an interior bin:
  P_peak = A^2 / (2 * ENBW); the integrated one-sided power is A^2 / 2
  regardless of window, because sum(w^2) cancels in the density scale.
- Units: fs in Hz, amplitudes in the signal unit, PSD in
  (signal unit)^2 / Hz, e.g. g^2/Hz for an acceleration survey.
- All functions are deterministic and stdlib-only (math); no network,
  no third-party numerical libraries. NACA Report 824 anchors the
  pack's public-domain reference set; Welch's method is generic
  signal-processing methodology, summary-only.

## Workflow

1. Collect the sampled record x (real values), the sample rate fs in
   Hz, and choose the segment length M, a power of two.
2. Form the window with hann_window(M); check the noise-width cost of
   the window with equivalent_noise_bw(window, fs).
3. Estimate the density: welch_psd(x, fs, M, overlap=0.5) returns the
   frequency axis and the averaged PSD. Reduce overlap to lower the
   segment count, or toward 1.0 for more averaging at the cost of
   correlated segments (the hop never drops below one sample).
4. Identify the tone or response peak: psd_summary returns the peak
   density and peak frequency together with enbw_hz, df_hz, total
   power, and the full freqs/psd arrays.
5. Integrate the level: psd_total_power(psd, df) gives the band or
   total power; compare with the variance of a zero-mean record as an
   energy check.
6. For a random-vibration survey, report the peak g^2/Hz level, the
   frequency of the peak, and the total rms from sqrt(total power),
   the quantities a downstream response analysis consumes.
7. Confirm the deterministic checks with the contract test
   scripts/test_power_spectral_density.py.

## Worked example

fs = 1024 Hz, M = 256, Hann window, 50% overlap, 8192-sample record
(63 segments), 60 Hz sine at amplitude A = 1.0 (bin 15 exactly). Real
outputs of this module:

- hann_window(256) sums to 128.000000 (M/2) with sum of squares
  96.000000 (3M/8).
- equivalent_noise_bw = 6.000000 Hz = 1024 * 96 / 128^2.
- welch_psd returns 129 bins, df = 4.000000 Hz; the peak sits at bin
  15, 60.000000 Hz, with density 0.08333333333 = A^2 / (2 * ENBW) =
  1/12 (ratio to theory 1.0 to 1e-15).
- Integrated total power = 0.50000000000 = A^2 / 2 (energy check).
- Amplitude A = 0.5: peak density 0.02083333333, exactly one quarter
  of the A = 1 peak (6.02 dB down), integrated power 0.125000000.
- DC bin not doubled: a constant record of 1.0 integrates to
  1.000000000 (= c^2, its mean square) with P[0] = 0.166666667 =
  (sum w)^2 / (fs * sum w^2), not the doubled 0.333333333.
- Nyquist bin not doubled: a (-1)^n record integrates to 1.000000000
  with P[128] = 0.166666667, again undoubled.
- Tone A = 1 plus seeded Gaussian noise of variance 0.2 (sigma 0.447),
  fixed seed 21: peak density 0.084140 at 60.0 Hz against the clean
  tone 0.083333, off-peak noise floor 5.66e-4 (max bin beyond three
  bins of the peak), signal-to-noise ratio about 149, and the run is
  bit-identical on repetition.

## Verification

- Confirm the window identities: sum(w) = 128.0 and sum(w^2) = 96.0
  for M = 256, and ENBW = fs * sum(w^2) / (sum(w))^2 = 6.0 Hz.
- Confirm the pure-sine anchors to 1e-6 relative: peak density equals
  A^2 / (2 * ENBW) and the integrated power equals A^2 / 2; halving
  the amplitude quarters the peak density.
- Confirm the DC and Nyquist bins are not doubled: a constant record
  and a (-1)^n record each integrate to their mean square with P[0]
  and P[M/2] at the undoubled value.
- Confirm determinism: two calls on the same record return identical
  PSDs, and a fixed seed regenerates an identical noisy PSD.
- Confirm psd_summary returns exactly the keys freqs, psd, enbw_hz,
  df_hz, total_power, peak_density, peak_freq_hz.
- Confirm every non-physical input raises ValueError: seg_len not a
  power of two, fs <= 0, overlap outside [0, 1), x shorter than
  seg_len, empty or zero-sum windows, and df <= 0.
- Run the contract test offline: python3
  scripts/test_power_spectral_density.py (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/fast-fourier-transform: the single-record
  spectrum sibling; this leaf adds windowing, segment averaging and
  density scaling on top of the radix-2 transform.
- cross-cutting/numerics/fir-filter-design: Hamming-window truncation
  for FIR coefficient design, a different use of windows.
- structures/loads/random-vibration-analysis: a PSD consumer that
  turns an input density spectrum into a response; this leaf estimates
  the input PSD from a measured time history.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_power_spectral_density.py

The test covers the Hann window identities (sum M/2, sum of squares
3M/8, symmetry), the equivalent noise bandwidth (6.0 Hz anchor and the
rectangular-window limit fs/M), the internal radix-2 transform against
the transform definition, the one-sided periodogram (axis, peak
density A^2/(2 ENBW), integrated power A^2/2, the quarter-amplitude
law, undoubled DC and Nyquist bins), the Welch average (63 segments at
default overlap, mean-of-periodograms identity, frequency axis, full
8192-sample anchors, zero-overlap path, determinism, seeded-noise
reproducibility and the peak/floor/SNR magnitude bounds), the total
power integral, the summary dict keys and values, and ValueError
rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the pack's
  public-domain reference set; Welch's averaged periodogram method is
  standard signal-processing methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

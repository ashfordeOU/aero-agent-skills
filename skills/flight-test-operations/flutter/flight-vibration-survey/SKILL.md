---
name: flight-vibration-survey
description: "Use when you must reduce an in-flight vibration survey: extract the per-rev order amplitudes from measured accelerometer time histories with a synchronous DFT over integer-revolution windows, compute the windowed total RMS survey level, combine the order components by root-sum-square, and gate each survey point against the declared vibration limit and the 1P trim limit. Produces the per-order amplitudes, the total level, the RSS check, and the pass or needs-trim verdicts for rotorcraft main-rotor track-and-balance and airframe vibration limits, and for fixed-wing vibration or buzz surveys. Trigger: vibration survey, track and balance, per-rev order, order analysis, synchronous DFT, rotor balance survey, 1P trim."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flutter
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: flutter
  tags: [flight-vibration-survey, track-and-balance, order-analysis, per-rev-amplitude, synchronous-dft, vibration-limit, rotor-balance-survey]
  version: 0.1.0
  author: Aero Agent Skills
---

# Flight Vibration Survey (flight-test-operations/flutter/flight-vibration-survey)

Use when the task is reducing an in-flight mechanical vibration survey,
rotorcraft main-rotor track-and-balance and airframe vibration limits
and fixed-wing vibration or buzz surveys, from measured accelerometer
time histories. This leaf implements the order-domain reduction in pure
Python, stdlib only: per-rev (N/rev) order amplitudes from a
synchronous DFT over integer-revolution windows, windowed total RMS
survey levels, root-sum-square combination of the orders, and gating of
each survey point against the declared vibration limit and the 1P trim
limit.

## Domain quick reference

- Integer-revolution window: N = round(m_revs * rate / rotor_hz),
  rounded to the nearest integer sample count; the window holds exactly
  m_revs rotor revolutions. The worked example uses N = 12 * 1000 / 5 =
  2400 samples.
- Synchronous order DFT at order p: A_p = (2/N) |sum_{k=0}^{N-1} x_k
  exp(-j 2 pi (p m) k / N)| with m = m_revs. The p-per-rev component
  falls exactly on DFT bin p * m_revs of the m-rev window, so
  integer-revolution windows are exact, with no leakage.
- Total RMS over a segment: RMS = sqrt(mean(x^2)); this is the survey
  level of the window. windowed_rms slides with hop equal to the window
  and drops a trailing partial window.
- Root-sum-square of the orders: RMS_tot = sqrt(sum_p A_p^2 / 2), which
  equals the full-record RMS over integer revolutions for a pure
  multi-order signal.
- Vibration verdict: margin = (limit - level) / limit, pass when the
  margin is >= 0.
- 1P trim verdict: the same margin applied to the 1P amplitude against
  the trim limit; needs_trim when the amplitude exceeds the limit.
- Units: the accelerometer record is in g and the limits are declared
  in g; all reductions are unit-consistent.

## Workflow

1. Fix the survey point: the accelerometer time history samples (g),
   the sample rate rate (Hz), the rotor frequency rotor_hz (Hz), the
   window length m_revs (integer revolutions, 12 in the worked
   example) and the declared vibration limit and 1P trim limit (g).
2. Extract each order of interest with order_amplitude(samples,
   sample_rate_hz, rotor_hz, order, m_revs). The synchronous DFT runs
   over the first N samples of the integer-rev window; a record
   shorter than one full window raises ValueError.
3. Get the survey level with total_rms over the window, or
   windowed_rms(samples, sample_rate_hz, window_s) when the record
   spans several windows and the per-window levels matter.
4. Combine the orders with rss_of_orders over the amplitude dict.
5. Gate the point with vibration_verdict(level_g, limit_g) and the 1P
   component with trim_verdict(amp_1p_g, limit_1p_g).
6. Reduce the whole point in one call with
   vibration_survey_summary(samples, sample_rate_hz, rotor_hz, orders,
   m_revs, vibration_limit_g, trim_limit_g); the returned dict carries
   the order amplitudes, the windowed total RMS, the RSS check and
   both verdicts. orders must include order 1 for the trim verdict.
7. Confirm the deterministic checks with the contract test.

## Worked example

Rotor 5.0 Hz, 1000 Hz sampling, signal 0.15 g at 1P + 0.06 g at 2P +
0.08 g at 4P (deterministic sines with a phase offset per order),
12-rev window N = 2400 samples. Running the module gives these real
outputs:

- Recovered order amplitudes: 0.150000 g at 1P, 0.060000 g at 2P and
  0.080000 g at 4P, exact to 1e-6.
- total_rms = 0.127475 g and rss_of_orders = 0.127475 g (rounds to
  0.12748 g); the RSS identity holds to floating-point round-off
  (difference about 5.6e-17).
- vibration_verdict(0.127475, 0.15): margin +0.150163, pass. The
  margin rounds to +0.150, the survey point clears the 0.15 g limit
  by 15 percent of the limit.
- trim_verdict(0.150000, 0.10): margin -0.500000, needs_trim. The 1P
  component sits 50 percent above the 0.10 g trim limit.
- vibration_survey_summary returns exactly the keys
  order_amplitudes_g, total_rms_g, rss_of_orders_g, vibration_verdict
  and trim_verdict.

## Verification

- Confirm order_amplitude recovers 0.150000 / 0.060000 / 0.080000 g to
  1e-6 on the worked signal, and that recovery is phase invariant.
- Confirm rss_of_orders equals total_rms to 1e-6 (the identity holds
  over the 12-rev window).
- Confirm the verdict margins: +0.150 pass against the 0.15 g limit
  and -0.500 needs-trim against the 0.10 g trim limit, with zero
  margin at the boundary counting as pass or no-trim.
- Leakage: a 2.5P off-order tone stays below 1e-6 g in every
  integer-order bin (bin-centered orthogonality), and a non-bin-
  centered 2.3P tone stays below 0.05 g, the sidelobe envelope, in
  every order bin.
- Confirm every non-physical input raises ValueError: empty samples,
  non-positive sample rate, rotor frequency or window length, order
  below 1, m_revs below 1, non-positive vibration or trim limits,
  negative levels, and a record shorter than one full window.
- Run the contract test offline: python3
  scripts/test_flight_vibration_survey.py (35 tests, deterministic,
  under 20 s).

## Related leaves

- flight-test-operations/flutter/ground-vibration-testing: the
  ground-based sibling; this leaf covers the in-flight survey.
- flight-test-operations/performance/rotorcraft-performance-flight-test:
  rotorcraft performance testing that sits alongside the rotor balance
  survey flight work.
- flight-test-operations/envelope/buffet-boundary-testing: the
  high-Mach envelope sibling; this leaf reduces the steady in-flight
  survey points.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_flight_vibration_survey.py

The test covers exact 1P/2P/4P amplitude recovery to 1e-6 (single
tone, multi-order and phase-shifted), the total-RMS equals
RSS-of-orders identity at 0.12748 g, windowed RMS over one, two and
partial windows, the verdict margins of the worked example, the
documented survey summary key set, leakage rejection of 2.5P and
non-bin-centered off-order tones, the integer-rev window rounding
convention, run-to-run determinism, and ValueError rejection of
non-physical inputs.

## Compliance

- Standards referenced, not reproduced: FAR 29 for the rotorcraft
  track-and-balance and vibration survey airworthiness context, and
  the FAR 25 / CS 25 vibration and buffeting context of 25.251 for
  fixed-wing survey work; name-and-paraphrase references only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: noise-certification-test
description: "Use when you must plan and analyze the noise certification flight test for a transport airplane: lay out the flyover, sideline, and approach measurement conditions with the reference geometry (6500 m flyover distance, 450 m sideline offset, 1200 m approach distance at 120 m altitude on a 3 degree glide slope), compute the effective perceived noise level (EPNL) from the measured tone corrected perceived noise level (PNLT) time history with the 10 dB down integration rule and the 10 s normalization, and check each point and the cumulative three point margin against the noise limits. Produces the EPNL per condition, the margin to limit with verdict, and the cumulative margin verdict that gate the certification submission. Trigger: noise certification flight test, EPNL, effective perceived noise level, PNLT, tone corrected, 10 dB down integration, flyover noise, sideline noise, approach noise, cumulative margin, noise limit, FAR 36."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: planning
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: planning
  tags: [noise-certification-test, noise-certification, epnl-computation, effective-perceived-noise-level, flyover-noise, sideline-noise, approach-noise, 10-db-down-integration, cumulative-margin, noise-limit, far-36, chapter-4-margin-rule]
  version: 0.1.0
  author: Aero Agent Skills
---

# Noise Certification Test (flight-test-operations/planning/noise-certification-test)

Use when the task is planning and analyzing the noise certification
flight test for a transport category airplane: laying out the flyover,
sideline and approach measurement conditions, reducing the measured
tone corrected perceived noise level (PNLT) time history into the
effective perceived noise level (EPNL) with the 10 dB down integration
rule, and checking the per point and cumulative margins against the
stated noise limits. This leaf implements the EPNL math and the test
geometry layer in pure Python, stdlib only. The measured PNLT input is
the tone corrected perceived noisiness output of the acoustic
measurement chain; the noy conversion and the acoustic data
acquisition hardware are out of scope. It pairs with
flight-test-operations/planning/flight-test-planning for program
sequencing, flight-test-operations/planning/flight-test-instrumentation
for the acoustic measurement system, and
flight-test-operations/planning/position-error-calibration for the
airspeed reference flown at each certification condition.

## Domain quick reference

The noise certification measurement procedure is summarized here at
reference level from the public FAR 36 / ICAO Annex 16 Volume I
description (name and paraphrase only, no verbatim regulation text;
the certification basis states the applicable limits, which this leaf
accepts as inputs).

- Flyover: the airplane accelerates at maximum takeoff thrust along
  the runway and passes over the reference point on the extended
  centerline 6500 m from the brake release point, speed reference
  V2 + 10 kt.
- Sideline: the microphone sits 450 m lateral of the runway
  centerline at the point of maximum noise during the takeoff run.
- Approach: the airplane descends the 3 degree glide slope to the
  threshold; the microphone is 1200 m from the threshold under the
  flight path at 120 m altitude.
- Effective perceived noise level: EPNL = 10 * log10((1 / T0) *
  sum(10^(PNLT_i / 10)) * dt), T0 = 10 s, summed over the 10 dB down
  interval where the PNLT stays within 10 EPNdB of its maximum.
- 10 dB down rule: find the PNLT maximum, then walk left and right to
  the times where the PNLT has dropped 10 dB below that maximum;
  boundary times are linearly interpolated between the bracketing
  samples. A series that never drops 10 dB is integrated over its
  full span and flagged as not truncated.
- Margin to limit: margin_db = limit - EPNL, pass when margin_db >= 0.
- Cumulative rule (typical chapter 4 / stage 4 check at reference
  level): the sum of the three per point margins must be >= 10 EPNdB
  and every individual margin must be >= 0. The exact rule set
  depends on the certification basis.
- Units: geometry in meters and degrees, EPNL in EPNdB, time in
  seconds, airspeeds in knots.

## Workflow

1. Lay out the three measurement conditions with geometry(condition)
   for flyover, sideline and approach; each returns the reference
   distances from the module constants.
2. Build the certification test matrix from the weight and speed
   inputs with test_matrix(takeoff_weight, landing_weight, v2_kt,
   approach_speed_kt, limits); each row carries the configuration,
   reference speed, stated limit and target EPNL.
3. For each measured run, integrate the tone corrected PNLT time
   history with epnl_from_pnlt(pnlt_series, dt) to get the EPNL, the
   10 dB down window bounds and the truncation flag.
4. Check every point against its stated limit with
   margin_to_limit(epnl, limit) to get the margin and the pass or
   fail verdict.
5. Assess the three point set with cumulative_margin(margins) against
   the chapter 4 style rule: summed margin at or above the required
   10 EPNdB and no negative individual margin.
6. Combine everything with summarize(epnl_by_condition, limits) for
   the per condition EPNL, margin, verdict and the cumulative
   verdict.
7. Confirm the deterministic checks with the contract test
   scripts/test_noise_certification_test.py.

## Worked example

A transport airplane noise certification data set, 41 PNLT samples at
0.5 s spacing (20 s per run):

- Constant 90 dB flyover run that never drops 10 dB: the full 20 s
  series is integrated and EPNL = 90 + 10 * log10(20 / 10) =
  93.0103 EPNdB (window 0.0 to 20.0 s, not truncated).
- Single peak flyover run peaking at 92.0 dB at sample 20 with values
  falling 10 dB below the maximum at the series ends: EPNL =
  89.1267 EPNdB over the truncated 10 dB down window from 4.0 s to
  16.0 s.
- Pulse approach run at 100 dB from 8 s to 12 s and 80 dB elsewhere:
  EPNL = 96.3094 EPNdB, below the 100 dB instantaneous peak because
  the effective duration is below the 10 s reference; the 90 dB
  crossings are linearly interpolated at 7.75 s and 12.25 s.
- Margin: margin_to_limit(93.01, 95.0) returns margin 1.99 EPNdB,
  verdict pass; margin_to_limit(96.0, 95.0) fails.
- Cumulative: margins [3.0, 4.0, 4.0] sum to 11.0 EPNdB with all
  margins at or above zero, verdict pass; [3.0, 3.0, 3.0] fails on
  the 9.0 EPNdB sum; [-1.0, 6.0, 6.0] fails on the negative
  individual margin.
- Geometry: geometry("approach") returns distance 1200.0 m,
  altitude 120.0 m, glide 3.0 degrees.

## Verification

- Confirm epnl_from_pnlt([90.0] * 41, 0.5) returns 93.0102999566
  within 1e-6, matching 90 + 10 * log10(20 / 10).
- Confirm the single peak 92 dB series stays near 89.0 EPNdB and
  below the instantaneous peak level.
- Confirm the constant series returns a not truncated flag and the
  full span bounds; the peaked series returns truncated True with the
  interpolated window bounds.
- Confirm margin_to_limit(93.01, 95.0) returns 1.99 pass and that a
  level shift identity holds: adding c dB to every PNLT sample adds
  c EPNdB to the EPNL.
- Confirm ValueError rejection of an empty or non-finite PNLT series,
  dt <= 0, an unknown condition, and negative noise limits.
- Run the contract test offline: python3
  scripts/test_noise_certification_test.py (33 tests, deterministic).

## Related leaves

- flight-test-operations/planning/flight-test-planning: orders the
  noise certification runs inside the overall build-up sequence.
- flight-test-operations/planning/flight-test-instrumentation: owns
  the acoustic measurement system that delivers the PNLT series.
- flight-test-operations/planning/position-error-calibration:
  provides the airspeed reference flown at each certification
  condition.
- flight-test-operations/planning/test-point-matrix-design: expands
  the certification conditions into the full flown point matrix.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_noise_certification_test.py

The test covers the reference geometry table for the three
conditions, the EPNL integration contract (the constant series closed
form 93.0103 EPNdB, the ~89.0 EPNdB truncated peak series with
interpolated window bounds, the 100 dB pulse staying below 100 EPNdB,
the level shift identity), the margin to limit verdicts, the
cumulative rule branches (pass, sum shortfall, negative individual
margin), the test matrix and summary helpers, and ValueError rejection
of empty, non-finite and non-physical inputs.

## Compliance

- Standards referenced, not reproduced: the noise certification
  measurement procedure (FAR 36 / ICAO Annex 16 Volume I) is named
  and summarized at reference level only, never quoted verbatim; the
  mapped standards ids far-25 and cs-25 frame the transport type
  certification context this test supports. The acoustic math above
  is the standard engineering method, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

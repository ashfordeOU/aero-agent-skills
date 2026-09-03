# Wave-26 leaf spec: noise-certification-test (flight-test-operations, planning pack)

- Path: skills/flight-test-operations/planning/noise-certification-test/
- Pack: planning (existing siblings: flight-test-planning,
  flight-test-safety, flight-test-data-reduction,
  flight-test-instrumentation, telemetry-data-acquisition,
  test-point-matrix-design, position-error-calibration)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
  NOTE: the noise certification regulation is FAR 36 / ICAO Annex 16
  Volume I, which are NOT in standards-map.yaml; name them in prose
  only (reference-only) and use far-25/cs-25 as the mapped ids (the
  transport type-cert context the noise test supports).
- Family: flight-test-operations

## Claim

Plan and analyze a transport-category noise certification flight test
per FAR 36 / ICAO Annex 16: lay out the three certification
measurement conditions (flyover, sideline, approach) with their
reference geometry, compute the effective perceived noise level EPNL
from a measured tone-corrected perceived noise level PNLT time
history, apply the 10 dB down integration rule and the 10 second
normalization, check each point against its stated noise limit, and
assess the cumulative margin of the three-point set. Produces the
EPNL per condition, the per-point margin to limit, and the cumulative
margin verdict that gate the noise certification submission.

Does NOT do: acquire the acoustic data or run the microphone hardware
(flight-test-instrumentation owns instrumentation; the acoustic
measurement system is out of scope), compute structural or component
noise, or derive the applicable noise limits from the regulation (the
certification basis states them; this leaf accepts the point limits as
inputs and computes the acoustic quantities). The perceived noisiness
(noy) conversion is out of scope: the input is the PNLT time history
already tone-corrected. This leaf is the EPNL math and test-geometry
layer.

## Model (implement exactly)

Reference geometry (module constants, documented typical values from
the public FAR 36 measurement procedure summary, not verbatim):
- FLYOVER: reference point on the extended runway centerline 6500 m
  from the brake release point; the airplane passes over at
  maximum takeoff thrust; speed reference is V2 + 10 kt (module
  constant FLYOVER_DISTANCE_M = 6500.0).
- SIDELINE: lateral distance 450 m from the runway centerline at the
  point of maximum noise during takeoff (SIDELINE_LATERAL_M = 450.0).
- APPROACH: the airplane flies a 3 degree glide slope to the
  threshold; the microphone is 1200 m from the threshold under the
  flight path at 120 m altitude (APPROACH_DISTANCE_M = 1200.0,
  APPROACH_ALTITUDE_M = 120.0, APPROACH_GLIDE_DEG = 3.0).
Functions:
- geometry(condition, ...) -> dict of the reference distances for the
  condition (flyover, sideline, approach) with the module constants;
  ValueError on an unknown condition.
- epnl_from_pnlt(pnlt_series, dt=0.5) -> (epnl, t_start, t_end):
  EPNL = 10 * log10( (1 / T0) * sum(10^(PNLT_i / 10)) * dt ) with
  T0 = 10 s over the 10 dB down interval: find the time of maximum
  PNLT, extend left and right to the points where PNLT drops more than
  10 dB below the maximum (linear interpolation between samples for
  the boundary), integrate over that interval; when the series never
  drops 10 dB, integrate the full series and note the truncation flag.
  Module constants T0 = 10.0, DB_DOWN = 10.0.
- margin_to_limit(epnl, limit) -> (margin_db = limit - epnl, verdict:
  pass when margin_db >= 0 else fail).
- cumulative_margin(margins) -> dict: Chapter-4-style cumulative rule
  (documented as the typical transport rule): the sum of the three
  per-point margins must be >= 10 EPNdB and each individual margin
  must be >= 0; verdict pass/fail with reasons. Module constant
  CUMULATIVE_REQUIRED_DB = 10.0. (The exact rule set depends on the
  certification basis; document this as the typical Chapter 4 / Stage
  4 cumulative check at reference level.)
- test_matrix(configs, weights...) -> list of rows
  {condition, configuration (takeoff/landing weights from inputs),
  reference_speed, limit, target_epnl}: the planner helper builds the
  three-condition matrix from the certification weight inputs
  (takeoff_weight, landing_weight, V2, approach_speed, limits dict);
  ValueError on missing keys.
- summarize(...) -> dict {epnl per condition, margin per condition,
  cumulative verdict} used in the SKILL worked example.
ValueError on: non-finite PNLT values, dt <= 0, unknown condition,
empty pnlt_series, negative limits.

## Worked example

1. pnlt_series: 41 samples at dt 0.5 s (20 s total), a symmetric
   single-peak series peaking at sample 20 (t = 10 s) with PNLT_max
   92.0 dB and values falling 10 dB below max by the series ends:
   epnl_from_pnlt returns ~ 89.0 EPNdB (within the 10 dB down
   truncation; builder computes the exact module value and asserts it
   plus the interval bounds). Simpler asserted anchor: a constant
   series of 90.0 dB for the full 20 s never drops 10 dB, so the
   integration covers the full series and
   EPNL = 90 + 10 log10(20 / 10) = 93.01 EPNdB (assert within 1e-6).
2. Peak series: PNLT = 100 dB at t 8-12 s and 80 dB elsewhere (no
   tone): EPNL from the module; assert monotonic behavior EPNL < 100.
3. margin_to_limit(93.01, 95.0) -> margin 1.99 pass;
   margin_to_limit(96.0, 95.0) -> fail.
4. cumulative_margin([3.0, 4.0, 4.0]) -> sum 11.0 >= 10, all >= 0 ->
   pass; cumulative_margin([3.0, 3.0, 3.0]) -> sum 9.0 -> fail;
   cumulative_margin([-1.0, 6.0, 6.0]) -> fail with the individual
   margin reason.
5. geometry("approach") returns 1200 m / 120 m / 3 deg; ValueError on
   "unknown-condition".
6. ValueError on an empty PNLT series and on negative limits.
Keep at least 16 test methods (geometry table, EPNL integration
including the constant-series closed form, truncation, margin and
cumulative verdict branches, test matrix helper, ValueErrors).

## Corpus tasks (ids w26-noise-certification-test-1/2)

Distinctive tokens: noise certification flight test, EPNL, effective
perceived noise level, PNLT, tone corrected, 10 dB down integration,
flyover noise, sideline noise, approach noise, FAR 36, cumulative
margin, noise limit. Avoid: instrumentation hardware (flight-test-
instrumentation), flutter / vibration test (sibling packs), acoustic
emission NDT (manufacturing-quality acoustic-emission-inspection).

1. "compute the EPNL from the measured tone corrected PNLT time
   history of the flyover noise certification run with the 10 dB down
   integration rule and check the margin against the 95 EPNdB limit"
2. "plan the FAR 36 noise certification test matrix for the flyover,
   sideline, and approach conditions and assess the cumulative margin
   of the three point set against the chapter 4 style rule"

## SKILL body notes

Pair with flight-test-planning (program sequencing), flight-test-
instrumentation (acoustic measurement system), and position-error-
calibration (airspeed reference for the test conditions). Geometry and
rules are summarized at reference level from the public FAR 36 /
Annex 16 procedure description (name and paraphrase only; no verbatim
regulation text). Standards referenced not reproduced.

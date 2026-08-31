---
name: flight-test-data-reduction
description: "Use when you must reduce post-flight flight test data: apply the calibration correction with the channel slope and intercept, align the time series from separate recorders with the offset, smooth the raw trace with the moving average filter, compute the corrected airspeed from the impact pressure and density, and combine the measurement uncertainty sources with the root sum square into the combined uncertainty. Produces the corrected and filtered channel time series, the corrected airspeed, the combined uncertainty, and the data quality verdict that flags out-of-range values, NaN samples, and time gaps before the performance analysis. Trigger: data reduction, calibration correction, time alignment, filtering, measurement uncertainty, corrected airspeed."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: planning
  tags: [flight-test-data-reduction, data-reduction, calibration-correction, time-alignment, moving-average, filtering, measurement-uncertainty, corrected-airspeed, post-flight, rss, data-quality, gap-detection]
  version: 0.1.0
  author: AeroSkills
---

# Flight Test Data Reduction (flight-test-operations/planning/flight-test-data-reduction)

Use when the task is post-flight data reduction for a flight test
campaign: calibration correction of the recorded channels, time
alignment of traces from separate recorders, smoothing with a moving
average filter, computation of the corrected airspeed from the impact
pressure, combination of the measurement uncertainty sources, and the
data quality verdict that gates the reduced data before the
performance analysis.

## Domain quick reference

- Calibration correction: V_corr = m * V_raw + b, with m the slope
  (gain) and b the intercept (offset) of the channel calibration.
  Example: a slope of 1.02 and an intercept of -0.5 m/s turn a raw
  50.0 m/s reading into 50.5 m/s.
- Time alignment: t_aligned = t_raw + offset, with offset in s; a
  positive offset shifts the trace later in time. Alignment removes
  the start-time skew between recorders, which is fixed with GPS time
  tags, tape marks, or maneuver triggers.
- Moving average filter: y_k = (1/N) * sum of the N samples in the
  window; an n-sample trace gives n - N + 1 smoothed samples. Odd
  windows are centered on the samples, even windows lag by half a
  sample. Example: window 3 on [1, 2, 3, 4, 5] m/s gives [2.0, 3.0,
  4.0] m/s.
- Corrected airspeed: V_c = sqrt(2 * q_c / rho), with q_c the impact
  pressure in Pa and rho the air density in kg/m^3. Example: q_c =
  6125 Pa at rho = 1.225 kg/m^3 (sea level standard) gives V_c = 100
  m/s.
- Combined uncertainty: u_c = sqrt(u_1^2 + u_2^2 + ... + u_n^2), the
  root sum square (RSS) of the independent standard uncertainties, in
  the same unit as the contributors. Example: 0.5 m/s and 1.0 m/s
  combine into 1.118 m/s. The RSS rule is the zero-correlation special
  case of the GUM first-order law.
- Data quality verdict: a reduced trace is usable when it has no NaN
  samples, no values outside the valid range of the channel, and no
  time gaps beyond the allowed maximum; any single issue flags the
  trace for review.

## Workflow

1. Load the recorded channels and apply the calibration with
   apply_calibration(raw, slope, intercept) channel by channel.
2. Align the traces with align_time_series(times, offset) so all
   channels share the same time base.
3. Smooth the noisy traces with moving_average(values, window),
   choosing the window from the signal content and the sample rate.
4. Compute the corrected airspeed with
   corrected_airspeed(impact_pressure, density) from the calibrated
   impact pressure and the measured density.
5. Combine the uncertainty sources with
   combined_uncertainty(uncertainties) into the combined uncertainty
   for the reported values.
6. Gate the reduced data with data_quality_verdict(times, values,
   valid_min, valid_max, max_gap) and flag or fix every NaN sample,
   out-of-range value, and time gap before the performance analysis.

## Pitfalls

- Correcting channels without the calibration: raw recorded values
  carry the sensor gain and offset, so applying the slope and
  intercept is the first reduction step.
- Forgetting the time alignment: channels recorded on separate
  recorders start at different times, and unaligned traces smear the
  maneuver analysis.
- Using an even window without accounting for the half-sample lag:
  prefer odd windows when the smoothed trace must stay centered on the
  samples.
- A window larger than the trace: the moving average raises ValueError
  instead of silently returning a short output.
- Zero density: corrected_airspeed raises ValueError; a zero density
  is a data error, not a valid flight condition.
- Treating the root sum square as the worst case: RSS assumes
  independent, uncorrelated sources, and correlated errors combine
  linearly, which RSS understates.
- Shipping reduced data without the quality verdict: NaN samples,
  out-of-range values, and time gaps must be flagged before the data
  feeds the analysis.

## Behavior contract (gate 3)

The calibration correction, time alignment, moving average, corrected
airspeed, combined uncertainty, and data quality verdict relations are
exercised by the gate 3 contract test:
scripts/test_flight_test_data_reduction.py against
scripts/flight_test_data_reduction.py (stdlib unittest, offline). Run:
python3 scripts/test_flight_test_data_reduction.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 set the
  flight test and certification context; the calibration, time
  alignment, filtering, corrected airspeed, and uncertainty relations
  are common measurement and data reduction methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: rotorcraft-autorotation-flight-test
description: "Use when you must reduce a rotorcraft power-off autorotation demonstration flight test: least-squares fit the telemetered pressure-altitude samples against time over the steady autorotative descent, read the measured sink rate from the fitted slope, run the rotor-RPM checks across the entry decay, steady descent and flare recovery against the declared floor, band and recovery target, compute the altitude lost to the recovery from the flare-initiation and re-established level-flight altitudes, and give the PASS or FAIL verdict per check plus the overall demonstration verdict. Produces the fitted slope, intercept and R-squared, the measured sink rate in the realistic 8 to 15 m/s autorotative band, the three rotor-RPM check verdicts, the altitude loss with its limit verdict and margin, and the overall verdict gating the demonstration. Trigger: rotorcraft-autorotation-flight-test, measured-sink-rate, rotor-rpm-band-check, autorotation-demonstration-reduction, flare-altitude-loss."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-test-operations
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [rotorcraft-autorotation-flight-test, measured-sink-rate, rotor-rpm-band-check, autorotation-demonstration-reduction, flare-altitude-loss]
  version: 0.1.0
  author: Aero Agent Skills
---

# Rotorcraft Autorotation Flight Test (flight-test-operations/performance/rotorcraft-autorotation-flight-test)

Use when you must reduce the measurement side of a FAR 29 power-off
rotorcraft autorotation demonstration flight test (requirement named and
framed only, no rule text reproduced) from the telemetered record: fit
the steady autorotative descent window, read the measured sink rate,
check the rotor RPM across the entry decay, the steady descent and the
flare recovery, and judge the altitude lost to the recovery plus the
overall demonstration verdict against the declared limits. This leaf is
the flight-test side of the function the analytic flight-mechanics leaf
estimates: it reduces what the telemetered demonstration actually showed,
while flight-mechanics/performance/rotorcraft-autorotative-descent
predicts the power-off sink from minimum level-flight power and weight.
Deterministic stdlib least squares only; scatter in the samples is
carried by the fit R-squared, never by a stochastic model.

## Domain quick reference

- Least-squares fit of the steady descent: for n pressure-altitude
  samples y at times x, slope = (n*sum(xy) - sum(x)*sum(y)) /
  (n*sum(x^2) - sum(x)^2), intercept = mean(y) - slope * mean(x). The
  fitted slope is negative while the rotorcraft descends, in m/s.
- Fit quality: r_squared = 1 - ss_res / ss_tot, with ss_res the residual
  sum of squares and ss_tot = sum((y - mean(y))^2); a constant-altitude
  record (ss_tot 0) is defined as r_squared 1.0.
- Measured sink rate: sink_rate = -fitted slope, positive for a descent
  and expected inside the realistic 8 to 15 m/s steady autorotative band
  (about 1500 to 3000 ft/min).
- Entry decay floor: minimum rotor RPM across the power cut and decay in
  percent NR must hold at or above the declared floor, inclusive.
- Steady RPM band: every steady-descent rotor RPM sample in percent NR
  must lie inside the declared band, inclusive at both edges; verdict
  tracks the extreme samples, never the mean.
- Flare recovery target: the peak rotor RPM reached during the flare must
  reach at least the declared recovery target, inclusive.
- Altitude lost to recovery: h_flare_start - h_recovery (pressure
  altitude at flare initiation minus pressure altitude at the
  re-established level flight), judged against the declared limit with
  margin = limit - loss.
- Overall verdict: PASS only when the entry, steady, flare and
  altitude-loss checks all PASS.
- Module constants (percent NR, meters): entry floor 90.0, steady band
  95.0 to 105.0, flare recovery target 100.0, altitude-loss limit 60.0 m,
  MIN_SAMPLES 2. FAR 29 frames the demonstration requirement; the
  relations above are standard flight-test reduction practice,
  summary-only.

## Workflow

1. Extract the telemetered demonstration record: the entry rotor RPM
   history across the power cut, the steady autorotative descent samples
   (pressure altitude vs time), the steady-descent rotor RPM samples,
   the flare rotor RPM history, and the flare-initiation plus
   re-established level-flight pressure altitudes.
2. Fit the steady autorotative descent with lsq_fit: the closed-form
   least-squares regression of pressure altitude against time returns
   the fitted slope, intercept and R-squared of the descent line.
3. Read the measured sink rate with sink_rate: the negative of the
   fitted slope, positive for a descent, rejected with ValueError when
   the window shows no descent (slope >= 0).
4. Run the entry rotor-RPM floor check with entry_rpm_decay_check: the
   minimum rotor RPM of the decay against the declared floor, PASS
   inclusive at the floor.
5. Run the steady rotor-RPM band check with steady_rpm_band_check: every
   steady-descent rotor RPM sample inside the declared band, inclusive
   at both edges, with the mean, min and max reported.
6. Run the flare rotor-RPM recovery check with flare_rpm_recovery_check:
   the peak flare rotor RPM against the declared recovery target, PASS
   inclusive at the target.
7. Compute the altitude lost to the recovery with
   altitude_lost_to_recovery, then judge it with altitude_loss_verdict
   against the declared limit, reading the PASS or FAIL verdict and the
   margin.
8. Chain the four checks into the demonstration summary with
   reduce_autorotation_demonstration for the sink rate, R-squared, the
   four component verdicts, the altitude loss and the overall PASS or
   FAIL verdict.
9. Confirm the deterministic reduction with the contract test
   scripts/test_rotorcraft_autorotation_flight_test.py.

## Worked example

Telemetered power-off autorotation demonstration record (rotor RPM in
percent NR, pressure altitude in m): entry history [100.0, 94.6, 91.2,
91.6, 95.4, 96.7]; steady window of 15 altitude samples at 2 s spacing
over 28 s, Hp = [620.4, 599.7, 578.6, 557.2, 535.9, 514.8, 493.6, 472.3,
451.0, 429.8, 408.5, 387.1, 366.0, 344.7, 323.2] m at t = [0, 2, ..., 28]
s; steady rotor RPM [96.8, 97.4, 97.1, 97.6, 96.9, 97.5, 97.2, 97.7,
96.7, 97.5, 97.3, 97.0, 97.6, 96.9, 97.4]; flare history [96.5, 99.4,
102.1, 103.6, 103.9, 103.1]; flare initiation at 458.0 m, recovery at
412.6 m:

- lsq_fit over the steady window: slope -10.6225 m/s, intercept
  620.9016666667 m, r_squared 0.9999964366.
- sink_rate: 10.6225 m/s, inside the realistic 8 to 15 m/s autorotative
  band (about 2091 ft/min).
- entry_rpm_decay_check: min_rpm_pct 91.2 vs floor 90.0, PASS.
- steady_rpm_band_check: mean 97.24, min 96.7, max 97.7 vs band [95.0,
  105.0], PASS.
- flare_rpm_recovery_check: peak 103.9 vs target 100.0, PASS.
- altitude_lost_to_recovery(458.0, 412.6) = 45.4 m;
  altitude_loss_verdict: loss 45.4 vs limit 60.0 m, PASS, margin 14.6 m.
- reduce_autorotation_demonstration: sink_rate_mps 10.6225, r_squared
  0.9999964366, entry_verdict PASS, steady_verdict PASS, flare_verdict
  PASS, altitude_verdict PASS, altitude_loss_m 45.4, overall_verdict
  PASS.

## Verification

- Confirm lsq_fit on the worked steady window returns slope -10.6225
  within 1e-4, intercept 620.9016666667 within 1e-6 and r_squared
  0.9999964366 within 1e-9, with keys exactly slope, intercept,
  r_squared.
- Confirm the regression identity: perfectly linear altitude generated
  as 620.0 - 10.5 * t recovers slope -10.5 and intercept 620.0 at any
  sample count of 2 or more; constant-altitude samples give r_squared
  1.0 and sink_rate still raises ValueError (no descent observable).
- Confirm sink_rate equals -lsq_fit slope on any valid window.
- Confirm every verdict boundary is inclusive: entry minimum exactly
  90.0 PASSes and 89.9 FAILs; band samples exactly 95.0 and 105.0 PASS
  and 105.1 FAILs; flare peak exactly 100.0 PASSes and 99.9 FAILs;
  altitude loss exactly 60.0 m PASSes with margin 0.0 and 60.1 FAILs
  with margin -0.1.
- Confirm a single failing check fails the overall demonstration verdict
  regardless of the other three, and the summary agrees with the chained
  functions.
- Confirm ValueError rejection of non-physical inputs: unequal-length or
  too-few fit samples, a zero fit denominator, a non-negative fitted
  slope, empty or negative rotor RPM samples, non-positive floor, band,
  target or limit values, a high band edge below the low edge,
  non-positive altitudes, a recovery altitude above the flare-initiation
  altitude, and a negative altitude loss.
- Run the contract test offline: python3
  scripts/test_rotorcraft_autorotation_flight_test.py (35 tests,
  deterministic, no RNG).

## Related leaves

- flight-mechanics/performance/rotorcraft-autorotative-descent: the
  analytic estimate of the power-off descent rate from minimum
  level-flight power and weight; this leaf is the measured-data side of
  the same function.
- flight-test-operations/performance/rotorcraft-performance-flight-test:
  hover power, measured figure of merit, weight-corrected rate of climb
  and hover ceiling reduction; a measured descent point enters only as a
  negative-ROC input there, with no autorotation reduction.
- flight-test-operations/performance/rotorcraft-forward-flight-
  performance-test: the level-flight polar reduction, not the
  autorotative state.
- flight-mechanics/performance/rotorcraft-axial-descent-flow-states:
  vortex-ring and windmill flow-state physics, not test reduction.
- flight-test-operations/performance/in-flight-engine-relight-test: the
  rotorcraft windmill and descent-state deferral companion.

## Pitfalls

- Confusing the measured reduction with the analytic estimate: this leaf
  fits the telemetered pressure-altitude record, while the flight-
  mechanics leaf predicts the power-off sink from minimum level-flight
  power and weight; never substitute one result for the other.
- Reading the sink rate from single sample-to-sample altitude drops: the
  least-squares slope over the whole steady window is the measured rate,
  and the scatter is carried by r_squared, not by the point deltas.
- Sign errors: the fitted slope is negative while descending, so the
  measured sink rate is the negative of the slope, positive for a
  descent; a window whose fit shows no descent is degenerate and raises
  ValueError.
- Forgetting the inclusive boundaries: a check at exactly its declared
  floor, band edge, recovery target or altitude limit PASSes; only a
  value strictly outside FAILs.
- Reading the overall verdict from one check: the demonstration summary
  is PASS only when the entry floor, steady band, flare recovery and
  altitude-loss checks all PASS.
- Mixing the three rotor-RPM checks: the entry minimum, the steady
  extreme samples and the flare peak are separate verifications against
  separate declared values, taken from separate phases of the record.
- Widening the meaning of autorotation: in this leaf the word covers the
  power-off rotorcraft descent demonstration only, never the fixed-wing
  stalled-wing autorotation of the spin and high-angle-of-attack
  envelope leaves.
- Treating a recovery that gained altitude as a flare loss: the recovery
  altitude above the flare-initiation altitude raises ValueError rather
  than reporting a negative loss.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_autorotation_flight_test.py

The test covers the worked-example reduction end to end (fitted slope,
intercept and R-squared within tolerance, measured sink rate in the
realistic autorotative band, all four component verdicts and the overall
verdict), the closed-form regression identity on perfectly linear data,
the inclusive verdict boundaries at every declared limit, the chained-
summary agreement, the overall-verdict FAIL on any single failing check,
determinism across repeated calls, and ValueError rejection of every
non-physical input class. All numeric asserts are order-safe
(assertAlmostEqual or math.isclose).

## Compliance

- FAR 29 is referenced by name and frame only (the power-off
  autorotation demonstration requirement context); no rule text is
  reproduced. The reduction relations above are standard flight-test
  engineering practice, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

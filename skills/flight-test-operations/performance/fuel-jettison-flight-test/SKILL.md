---
name: fuel-jettison-flight-test
description: "Use when you must reduce a fuel jettison flight test demonstration: least-squares fit the telemetered fuel-weight-vs-time samples taken while the dump runs, read the measured average dump rate from the fitted slope, extrapolate the time from the takeoff weight down to the landing weight at that measured rate, judge the PASS or FAIL verdict against the 900 s limit, and check the measured rate against the design-side required rate. Produces the fitted slope, intercept and R^2, the measured dump rate, the extrapolated landing-weight time, the verdict with margin in seconds, and the rate-requirement check with margin in kg/s. Trigger: fuel jettison flight test, measured dump rate, fuel-weight-vs-time samples, jettison demonstration."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [fuel-jettison-flight-test, measured-jettison-rate, fuel-weight-vs-time-fit, dump-rate-requirement-check, jettison-demonstration-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# Fuel Jettison Flight Test (flight-test-operations/performance/fuel-jettison-flight-test)

Use when you must reduce a fuel jettison flight test demonstration from
telemetered fuel-weight-vs-time samples taken while the dump is running:
fit the sample weights W(t) with a deterministic closed-form
least-squares straight line, read the measured average dump rate from the
fitted slope, extrapolate the time the aircraft needs to come down from
its takeoff weight to its landing weight at that measured rate, and give
the PASS or FAIL verdict against the 900 s limit of FAR 25.1001 (name and
requirement frame only, no verbatim rule text). This leaf is the
flight-test verification side of the jettison function; the design side,
vehicle-design/sizing/fuel-jettison-sizing, sets the required rate q_req
from MTOW and MLW over the same 900 s limit, and this leaf checks the
measured rate against that anchor. The planning-pack data leaves stop
short of this reduction: flight-test-data-reduction applies channel
calibration and smoothing only, with no fitted dump rate and no
landing-weight extrapolation, and cruise-performance-flight-test reduces
fuel flow versus Mach with no weight-vs-time dump reduction, so this leaf
fills the measured jettison demonstration analysis gap.

## Domain quick reference

- Jettison demonstration limit: FAR 25.1001 frames the fuel jettison
  demonstration within 15 minutes of flight (name and frame only, no rule
  text reproduced). Module constant JETTISON_LIMIT_S = 900.0 s.
- Sample model over the dump window: W(t) = intercept + slope * t, slope
  in kg/s (negative while fuel is dumped), intercept in kg.
- Least-squares closed forms: slope = (n * sum(t*w) - sum(t) * sum(w)) /
  (n * sum(t^2) - (sum(t))^2), intercept = mean(w) - slope * mean(t).
- Coefficient of determination: r_squared = 1 - ss_res / ss_tot with
  ss_res the residual sum of squares and ss_tot = sum((w - mean(w))^2);
  when ss_tot is 0 (all weights equal) r_squared is defined as 1.0.
- Measured average dump rate: measured_rate = -slope, positive for a
  dump. A non-negative fitted slope means no dump is observable in the
  window (ValueError).
- Extrapolated time to the landing weight: t = (w_start - w_landing) /
  rate in seconds, with w_start the takeoff weight at dump start and
  w_landing the landing weight target.
- Verdict: PASS when t <= limit (inclusive at the boundary, so exactly
  900.0 s is PASS), else FAIL. margin_s = limit - t, positive for PASS
  and negative for FAIL.
- Rate requirement check: the design side's anchor is q_req = (MTOW -
  MLW) / 900 s. meets is True when measured_rate >= q_req (inclusive);
  margin_kg_s = measured_rate - q_req.
- Units are SI: kg, kg/s, s. Deterministic stdlib least squares only;
  scatter in the samples is handled by the fit's r_squared, not by a
  stochastic model.

## Workflow

1. Assemble the dump-window samples: order the telemetered
   fuel-weight-vs-time samples W(t) taken while the dump is running, with
   strictly increasing times and the takeoff weight at dump start noted
   as w_start, plus the landing weight target w_landing.
2. Fit the weight trend with the least-squares lsq_fit over the dump
   window: lsq_fit(weights, times) returns the fitted slope, intercept
   and r_squared; a low r_squared flags scatter or a non-linear trace.
3. Read the measured average dump rate from the fitted slope:
   measured_rate(weights, times) returns -slope in kg/s and raises
   ValueError when no dump is observable.
4. Extrapolate the time to the landing weight:
   time_to_landing_weight(w_start, w_landing, rate) returns
   (w_start - w_landing) / rate in seconds at the measured rate.
5. Judge the PASS or FAIL verdict against the 900 s limit:
   verdict(time_s, limit) returns the verdict, the limit used and the
   margin in seconds; the boundary is inclusive.
6. Check the rate requirement against the required rate:
   rate_meets_requirement(measured, required) compares the measured rate
   with the design side's q_req and reports meets with the rate margin in
   kg/s.
7. Summarize the demonstration reduction with reduce_dump_demonstration:
   one call on the samples, w_start, w_landing, required_rate and limit
   returns the nine-key record (measured rate, r_squared, time to the
   landing weight, verdict, limit, margin, requirement verdict, required
   rate, rate margin), chaining steps 3 to 6 in order.
8. Reject non-physical inputs and confirm determinism: every function
   raises ValueError on the invalid inputs listed in Verification, and
   the module is deterministic with fixed constants, verified by the
   contract test.

## Worked example

Reference transport at the design leaf's own weights: takeoff weight
79,000 kg, landing weight 66,500 kg, so the required rate anchor q_req =
(79000 - 66500) / 900 = 13.88888889 kg/s. Six telemetered samples at 60 s
spacing over a 300 s dump window: weights 79000, 78148, 77305, 76450,
75605, 74756 kg at times 0, 60, 120, 180, 240, 300 s. Real module
outputs:

- lsq_fit: slope = -14.1447619 kg/s, intercept = 78999.04762 kg,
  r_squared = 0.9999978496.
- measured_rate = 14.1447619 kg/s, the positive fitted dump rate.
- time_to_landing_weight(79000, 66500, 14.1447619) = 883.7193644 s,
  inside the 900 s limit.
- verdict(883.7193644) = {"verdict": "PASS", "limit_s": 900.0,
  "margin_s": 16.2806356}.
- rate_meets_requirement(14.1447619, 13.88888889) = {"meets": True,
  "margin_kg_s": 0.2558730159}: the measured rate clears q_req.
- reduce_dump_demonstration returns measured_rate_kg_s 14.1447619,
  r_squared 0.9999978496, time_to_landing_weight_s 883.7193644, verdict
  PASS, limit_s 900.0, margin_s 16.2806356, meets_required_rate True,
  required_rate_kg_s 13.88888889, rate_margin_kg_s 0.2558730159.
- Boundary anchors: a rate of exactly 13.88888889 kg/s gives exactly
  900.0 s and PASS with zero margin; verdict(900.001) is FAIL with
  margin_s -0.001; a slow dump at 13.0 kg/s gives 961.5384615 s and FAIL
  with margin_s -61.53846154.
- Perfect-fit identity: samples exactly on W = 79000 - 14.15 * t recover
  slope -14.15, measured_rate 14.15 and r_squared exactly 1.0.

## Verification

- Confirm lsq_fit on the worked example returns slope -14.1447619 within
  1e-6, intercept 78999.04762 within 1e-3 and r_squared 0.9999978496
  within 1e-9.
- Confirm measured_rate equals -lsq_fit slope by construction and returns
  14.1447619 within 1e-6.
- Confirm time_to_landing_weight(79000, 66500, 14.1447619) = 883.7193644
  within 1e-4 and that the function is exactly (w_start - w_landing) /
  rate at any valid inputs.
- Confirm the inclusive verdict boundary: verdict(900.0) is PASS with
  zero margin, verdict(900.001) is FAIL with margin_s -0.001.
- Confirm the inclusive rate-requirement boundary: measured equal to
  required is meets True with zero rate margin.
- Confirm perfect-line samples are recovered exactly (r_squared exactly
  1.0) and that all non-physical inputs raise ValueError: fewer than 2
  samples, unequal-length arrays, times not strictly increasing, zero fit
  denominator from duplicate times, a non-negative fitted slope (no dump
  observed), w_start <= 0, w_landing <= 0, w_start <= w_landing, rate <=
  0, time_s <= 0, limit <= 0, measured <= 0 and required <= 0.
- Run the deterministic contract test offline: python3
  scripts/test_fuel_jettison_flight_test.py (33 tests).

## Related leaves

- vehicle-design/sizing/fuel-jettison-sizing: the design-side partner
  that sets q_req from MTOW and MLW over the 900 s limit; this leaf
  checks the measured rate against that anchor from flight data.
- flight-test-operations/performance/cruise-performance-flight-test: the
  closest performance data-analysis sibling, fuel flow versus Mach with
  the square-root weight correction; it does no dump reduction.
- flight-test-operations/performance/engine-flight-test: thrust, EGT and
  transient times from engine flight tests; no weight-vs-time reduction.
- flight-test-operations/planning/flight-test-data-reduction: channel
  calibration and moving-average smoothing of raw traces, upstream of the
  fitted-rate reduction in this leaf.
- flight-test-operations/planning/flight-test-planning: ordering of test
  points and go/no-go gating that frames the demonstration flight.

## Contract test

Run the deterministic contract test (stdlib unittest, offline, no
network, under 1 s):

    cd ~/AeroSkills
    python3 skills/flight-test-operations/performance/fuel-jettison-flight-test/scripts/test_fuel_jettison_flight_test.py

It covers the worked-example least-squares fit (slope, intercept,
r_squared), the measured-rate read and its negative-slope identity, the
landing-weight time extrapolation and its direct identity, the inclusive
verdict boundary at 900.0 s, the inclusive rate-requirement boundary, the
perfect-line recovery identity, the nine-key demonstration summary and
its agreement with the chained steps, ValueError rejection of every
non-physical input listed in Verification, determinism of repeated runs,
and the fixed module constants.

## Pitfalls

- Reporting the fitted slope as the dump rate: the slope is negative
  while fuel is dumped (about -14.14 kg/s in the example); the measured
  average dump rate is its negative, so quoting the raw slope as a
  positive rate or taking the absolute value of a rising trace hides
  that no dump was observed.
- Verdict from a two-sample chord instead of the trend: the extrapolated
  time must come from the least-squares slope over the dump window, not
  from the chord of the first and last sample, because scatter can tilt
  the chord by more than the trend tolerance on short windows.
- Confusing the verdict with the rate-requirement check: the verdict
  extrapolates the time at the measured rate from the actual test weights
  against the 900 s limit, while the requirement check compares the
  measured rate with q_req directly; a test that starts below MTOW can
  PASS the verdict with a rate below q_req, so report both margins.
- Treating the boundary as strict: exactly 900.0 s is PASS and a rate of
  exactly (MTOW - MLW) / 900 gives exactly 900.0 s, so strict-less
  comparisons flip a legal demonstration to FAIL at the limit.
- Extrapolating from the wrong starting weight: w_start is the takeoff
  weight at dump start, not the first fitted intercept or a book MTOW
  when the dump begins below it; the time is driven by the weight
  actually on board when the dump starts.
- Ignoring r_squared: a fit far below 1.0 means the weight trace is not a
  clean linear dump (pump cycling, sensor noise, or the dump stopping
  mid-window), and the extrapolated time is not a trustworthy verdict
  input.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fuel_jettison_flight_test.py

The test covers the worked-example reduction (measured dump rate
14.1447619 kg/s within 1e-6, time to the landing weight 883.7193644 s
within 1e-4, PASS verdict with margin 16.2806356 s, requirement met with
rate margin 0.2558730159 kg/s), the least-squares fit anchors, the
inclusive verdict and rate-requirement boundaries, the perfect-line and
direct identities, the nine-key summary, ValueError rejection of all
non-physical inputs, determinism and the fixed module constants. Exit 0
with 33 tests passing is the creation gate.

## Compliance

- FAR 25.1001 frames the fuel jettison demonstration requirement; it is
  named and paraphrased only (15-minute frame, PASS within the limit) and
  never reproduced verbatim, per standards-map.yaml reference-only
  convention. Id: far-25.
- compliance: STANDARDS-REF, gated: false.

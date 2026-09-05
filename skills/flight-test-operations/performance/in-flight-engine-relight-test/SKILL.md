---
name: in-flight-engine-relight-test
description: 'Use when you must reduce an in-flight engine restart demonstration: fit the least-squares windmill N2 regression against true airspeed from the windmill survey, read the minimum relight airspeed where the fitted N2 line crosses the required relight threshold, summarize the starter-assisted relight time-to-idle samples against the type-data limit per altitude band, and combine the band verdicts with the airspeed into the overall restart-demonstration verdict. Produces the regression slope, intercept and R-squared, the minimum relight airspeed in m/s, per-band time-to-idle statistics and verdicts, and the combined PASS or FAIL verdict. Trigger: in-flight relight test, engine restart demonstration, windmill N2 survey, relight airspeed, time-to-idle limit.'
license: Apache-2.0
compliance: STANDARDS-REF
standards:
- id: far-25
  reference-only: true
gated: false
domain: flight-test-operations
pack: performance
compatibility: agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags:
  - in-flight-engine-relight-test
  - windmill-relight-airspeed
  - starter-assisted-relight
  - time-to-idle
  - restart-demonstration
  - windmill-n2-regression
  version: 0.1.0
  author: AeroSkills
---

# In-Flight Engine Relight Test (flight-test-operations/performance/in-flight-engine-relight-test)

A FAR 25.903(d)-style in-flight engine restart demonstration for a
fixed-wing aircraft is reduced from two measurement sets: a windmill
survey that maps the windmill N2 percent reached at each true airspeed,
and the starter-assisted relight attempts that time the restart from
start to idle at each altitude band of the demonstration. This leaf fits
the least-squares regression of windmill N2 against true airspeed from
the windmill survey points, reads the minimum relight airspeed where the
fitted line crosses the required relight N2 threshold, summarizes the
starter-assisted relight time-to-idle samples with the mean, the worst
sample and a PASS/FAIL verdict against the type-data limit, applies the
same check per altitude band, and combines the band verdicts with the
determined minimum relight airspeed into one overall
restart-demonstration verdict. Deterministic reduction only: the windmill
N2 regression is the classic linear survey fit, not a transient model of
the relight itself. It pairs with flight-test-operations/performance/
engine-flight-test for the altitude engine performance campaign around
the restart demonstration, and with flight-test-operations/performance/
engine-failure-takeoff-flight-test for the ground-run failure case that
is not followed by an in-flight restart.

## Domain quick reference

- Windmill N2 regression (least squares, windmill N2 y in percent against
  true airspeed x in m/s): slope = (n * sxy - sx * sy) / (n * sxx - sx *
  sx), intercept = (sy - slope * sx) / n, R-squared = 1 - ss_res /
  ss_tot, with ss_tot = syy - sy * sy / n and ss_res = syy - intercept *
  sy - slope * sxy. The degenerate constant-line case (ss_tot = 0.0)
  returns R-squared 1.0. Fewer than two survey points, mismatched list
  lengths, or zero TAS variance (denominator zero) are errors.
- Minimum relight airspeed: TAS = (N2_required - intercept) / slope where
  the fitted windmill N2 line crosses the required relight N2 threshold
  WINDMILL_N2_MIN_REQUIRED_PCT = 18.0 percent. The threshold and the slope
  must be positive (windmill N2 rises with airspeed) and the computed
  airspeed must be positive (a threshold below the idle line means the
  relight airspeed is never reached on the survey).
- Starter-assisted relight time to idle: mean = sum / n, worst sample =
  max of the samples, and the verdict is PASS when the worst sample is at
  or below the type-data limit RELIGHT_IDLE_LIMIT_S = 60.0 s (inclusive),
  FAIL otherwise. The verdict tracks the worst sample, never the mean.
- Altitude band score: each altitude band name of the demonstration maps
  to the time-to-idle result dict computed on that band's samples.
- Combined verdict: PASS iff every band verdict is PASS and the minimum
  relight airspeed is positive (a determined threshold); any failing band
  fails the whole restart demonstration. An empty band set or a
  non-positive airspeed is an error, never a PASS.
- The regulation is named and paraphrased only (FAR 25.903(d)-style
  restart demonstration); no standard text is reproduced. Units: N2 in
  percent, true airspeed in m/s, time in seconds.

## Workflow

1. Collect the windmill survey points: the true airspeed samples with the
   windmill N2 percent observed at each survey speed, one paired list per
   flight (windmill_regression inputs, two or more points, airspeeds that
   actually vary).
2. Fit the windmill N2 regression: windmill_regression(n2_pct_list,
   tas_list) returns the least-squares slope, intercept and r_squared of
   the windmill N2 line against true airspeed; check that R-squared is
   high enough to read a threshold crossing.
3. Read the minimum relight airspeed: min_relight_airspeed(
   WINDMILL_N2_MIN_REQUIRED_PCT, slope, intercept) returns the TAS in m/s
   where the fitted windmill N2 line crosses the 18.0 percent required
   relight threshold.
4. Summarize the starter-assisted relight samples: time_to_idle(
   relight_time_samples) returns the mean time to idle, the worst sample,
   the type-data limit and the PASS/FAIL verdict for the attempted
   relights.
5. Score each altitude band of the demonstration: altitude_band_verdict(
   relight_results_per_altitude) applies the step 4 time-to-idle check to
   every altitude band flown, keeping the band name keys exactly.
6. Combine the band verdicts with the minimum relight airspeed into the
   overall restart-demonstration verdict: combined_verdict(band_verdicts,
   min_relight_airspeed_mps) returns PASS only when every band PASSes and
   a relight airspeed was determined, otherwise FAIL (or ValueError for an
   empty band set or a non-positive airspeed).
7. Confirm the reduction with the deterministic contract test
   scripts/test_in_flight_engine_relight_test.py.

## Worked example

Windmill survey: TAS [70, 85, 105, 130] m/s with windmill N2 [13.5, 15.75,
18.75, 22.5] percent, a perfectly linear spread. Real module outputs from
running the logic module:

- Windmill N2 regression: slope 0.1500 percent per m/s, intercept 3.0000
  percent, r_squared 1.0000.
- Minimum relight airspeed: min_relight_airspeed(18.0, 0.15, 3.0) = 100.0
  m/s (194.4 kt TAS), the airspeed where the fitted line reaches the 18.0
  percent required windmill N2.
- Starter-assisted relight samples [34.2, 41.7, 38.9, 52.4] s: mean 41.80
  s, worst sample 52.40 s, limit 60.00 s, verdict PASS (the worst
  starter-assisted relight stays below the type-data limit).
- Altitude bands FL200 [37.4, 40.2, 41.9], FL300 [42.6, 44.8, 47.1],
  FL410 [46.5, 49.3, 58.9] s: FL200 mean 39.83 s, worst 41.90 s, PASS;
  FL300 mean 44.83 s, worst 47.10 s, PASS; FL410 mean 51.57 s, worst
  58.90 s, PASS.
- Combined verdict on those bands with the minimum relight airspeed 100.0
  m/s: PASS.
- Boundary anchors: time_to_idle([60.0]) PASS (inclusive at the limit),
  time_to_idle([60.1]) FAIL; a FL410 band with a 62.5 s sample FAILs, and
  the combined verdict on that failing band with airspeed 100.0 m/s is
  FAIL.

## Verification

- Confirm the worked example outputs above fall inside the spec magnitude
  bounds: slope 0.1500, intercept 3.0000, r_squared 1.0000, minimum
  relight airspeed 100.0 m/s, time-to-idle mean 41.80 s with worst sample
  52.40 s, and PASS at every stage of the three-band demonstration.
- Regression identity: windmill N2 generated as 0.15 * TAS + 3.0 recovers
  slope 0.15 and intercept 3.0 exactly (within 1e-12) at any survey point
  count of two or more; constant windmill N2 data returns r_squared 1.0.
- Threshold shift identity: raising the required relight N2 threshold by a
  delta moves the minimum relight airspeed by delta / slope (1.5 percent
  moves it 10.0 m/s on the worked example line).
- Verdict boundary: the time-to-idle verdict flips exactly at the 60.0 s
  type-data limit (60.0 PASS, 60.1 FAIL), and the verdict tracks the worst
  sample, not the mean.
- Band identity: altitude_band_verdict results replicate time_to_idle
  computed directly on the same samples; a single failing band fails the
  combined verdict regardless of the other bands.
- ValueError rejection: mismatched list lengths, a single survey point,
  zero TAS variance, a non-positive required N2 threshold, a non-positive
  slope, a threshold below the idle line, empty relight time samples, a
  negative relight time, an empty altitude band dict, an empty band
  verdict set, and a non-positive minimum relight airspeed all raise
  ValueError.
- Determinism: no randomness anywhere; repeated calls return identical
  results. Confirm everything with the contract test below.

## Related leaves

- flight-test-operations/performance/engine-flight-test: the altitude
  engine performance campaign around the restart demonstration, covering
  the installed engine output side of the flight test program.
- flight-test-operations/performance/engine-failure-takeoff-flight-test:
  the takeoff ground-run failure case, which is not followed by an
  in-flight restart demonstration.
- flight-test-operations/performance/cruise-performance-flight-test: the
  cruise survey context around the windmill survey speeds.
- flight-test-operations/performance/level-acceleration-test: the
  energy-state runs that bound the survey speed range.
- flight-test-operations/performance/climb-performance-flight-test: the
  climb segment of the flight test program that precedes the restart
  demonstration bands.

## Contract test

Run offline from the leaf directory or the repo root:

    python3 scripts/test_in_flight_engine_relight_test.py

The stdlib unittest contract (33 methods, deterministic, under 1 second)
covers the SKILL.md workflow steps 1 to 7: the module thresholds, the
worked-example windmill N2 regression values and exact dict keys, the
regression recovery identity at two and nine survey points, the constant
windmill N2 degenerate case, step 3 threshold crossings with the
delta-over-slope shift identity, the worked-example time-to-idle summary
with the inclusive 60.0 s boundary and the worst-sample verdict rule,
per-band scoring on the FL200/FL300/FL410 demonstration bands with exact
band keys and the replicate-time_to_idle identity, the combined
restart-demonstration verdict including the any-failing-band rule and the
PASS independence of airspeed magnitude, ValueError rejection of every
non-physical input class, and determinism across repeated calls.

## Compliance

- compliance: STANDARDS-REF, gated: false.
- Standards referenced, not reproduced: the FAR 25.903(d)-style in-flight
  restart demonstration (id far-25 in standards-map.yaml) is named and
  paraphrased only; the regression and time-to-idle relations above are
  standard flight-test reduction methodology, summary-only, never verbatim
  regulation text.

## Pitfalls

- Reading the relight airspeed off an inadequate survey: fewer than two
  windmill survey points, mismatched N2 and airspeed lists, or a survey
  flown at constant true airspeed make the regression undefined, and a
  required threshold below the fitted idle line means the relight
  airspeed is never reached on the survey. Extend the survey or report
  that no threshold crossing was demonstrated instead of extrapolating
  the fitted line outside the measured speed range.
- Comparing the mean time to idle against the limit: the starter-assisted
  relight verdict is driven by the worst sample, inclusive at 60.0 s (60.0
  PASS, 60.1 FAIL). A low mean with one sample over the type-data limit
  still FAILs the band.
- Scoring one band and calling it the demonstration: every altitude band
  flown must be scored, and a single failing band fails the combined
  restart-demonstration verdict regardless of how cleanly the other bands
  PASS. The combined verdict also needs a determined (positive) minimum
  relight airspeed, so a demonstration that never reached a threshold
  crossing cannot be passed.
- Treating the regression as a relight model: the windmill N2 line is a
  steady survey fit used to find the threshold airspeed. It does not
  model the restart transient, the starter engagement, or the windmilling
  spool-up dynamics of the relight itself.
- Routing rotor windmill tasks here: in this leaf "windmill" means engine
  windmill N2 only. Rotor windmill state and autorotation airspeed work
  belong to the flight-mechanics rotorcraft leaves
  (rotorcraft-autorotative-descent, rotorcraft-axial-descent-flow-states),
  not to this engine restart reduction.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline, pure
Python, no network):

    python3 scripts/test_in_flight_engine_relight_test.py

The test must exit 0 with 33 methods passing. It pins the worked-example
outputs (regression slope 0.1500, intercept 3.0000, r_squared 1.0000;
minimum relight airspeed 100.0 m/s at the 18.0 percent required windmill
N2; time-to-idle mean 41.80 s with worst sample 52.40 s and PASS; the
three FL200/FL300/FL410 bands all PASS; combined verdict PASS), the
regression and threshold-shift identities within 1e-12, the inclusive
60.0 s verdict boundary, the replicate band identity, ValueError rejection
of every non-physical input class, and deterministic, fixed-string
verdicts with no randomness.

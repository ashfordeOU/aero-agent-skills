# Wave-41 leaf spec: in-flight-engine-relight-test (flight-test-operations, performance pack)

- Path: skills/flight-test-operations/performance/in-flight-engine-relight-test/
- Pack: performance (verified present at prep with accelerate-stop-distance,
  climb-performance-flight-test, cruise-performance-flight-test,
  engine-failure-takeoff-flight-test, engine-flight-test,
  glide-flight-test, landing-distance-determination,
  level-acceleration-test, rotorcraft-forward-flight-performance-test,
  rotorcraft-performance-flight-test, stall-speed-determination,
  takeoff-distance-determination).
- Closest siblings: engine-flight-test (its claim is "determine the
  installed thrust and verify the engine performance at altitude: derive
  the thrust from the rate of climb or the level acceleration and the
  measured drag, compute the fuel flow from the thrust specific fuel
  consumption, check the exhaust gas temperature margin against the limit,
  correct the EGT to the ISA temperature, scale the sea-level thrust to
  the test altitude with the density ratio, time the acceleration and
  deceleration transients between the test speeds" - thrust, fuel flow,
  EGT and transient timing only; its trigger list is "engine flight test,
  thrust determination, fuel flow, EGT margin, altitude performance,
  acceleration transient, deceleration transient" with no start, relight,
  restart or windmill anywhere in the description),
  cruise-performance-flight-test (its claim is "correct measured fuel flow
  from the test weight to the reference weight with the square-root weight
  correction, convert corrected fuel flow and true airspeed into range
  performance, fit a quadratic range performance curve versus Mach" - fuel
  flow versus Mach only, no restart reduction),
  level-acceleration-test (its claim is "evaluate the specific excess
  power by the total energy method, P_s = dh/dt + V a / g" - excess
  thrust assessment, no relight demonstration),
  engine-failure-takeoff-flight-test (its claim is "locate the engine
  failure point in the measured ground run at the failure speed VEF, add
  the V1 recognition time segment, integrate the continued takeoff to the
  35 ft obstacle at the measured engine out climb rate" - takeoff only,
  the failure is not followed by an in-flight restart demonstration).
  Whole-tree greps at prep: "relight", "engine restart" and
  "restart demonstration" = 0 hits in skills/; "windmill" hits sit in
  flight-mechanics rotorcraft leaves (rotorcraft-autorotative-descent
  and rotorcraft-axial-descent-flow-states, rotor windmill state, not
  engine windmill N2). GENUINE FTO gap (fresh probe): no leaf reduces an
  in-flight engine restart demonstration from windmill N2 survey data.
- Standards id: far-25 (reference-only). Ledger Standard: far-25. The
  regulation is named and paraphrased (FAR 25.903(d)-style restart
  demonstration), never reproduced.
- Family: flight-test-operations

## Claim

Reduce a FAR 25.903(d)-style in-flight engine restart demonstration for a
fixed-wing aircraft: fit the least-squares regression of windmill N2
percent against true airspeed from the windmill survey points, read the
minimum relight airspeed where the fitted windmill N2 line crosses the
required relight N2 threshold, summarize the starter-assisted relight
time-to-idle samples from the attempted restarts with the mean, the worst
sample and a PASS/FAIL verdict against the type-data limit, apply the same
check per altitude band of the demonstration, and combine the band
verdicts with the determined minimum relight airspeed into one overall
restart-demonstration verdict. Produces the regression slope, intercept
and R-squared, the minimum relight airspeed in m/s, the per-band
time-to-idle statistics with their limits and verdicts, and the combined
PASS or FAIL verdict that gates the in-flight restart demonstration.
Does NOT do: installed thrust, fuel flow, EGT margin or acceleration and
deceleration transient timing (engine-flight-test); fuel flow correction
and range performance curves (cruise-performance-flight-test); excess
thrust or specific excess power from level acceleration runs
(level-acceleration-test); engine failure and V1 decision speed on the
takeoff ground run (engine-failure-takeoff-flight-test); climb rate and
ceiling determination (climb-performance-flight-test); fuel dump sizing
or the measured fuel jettison rate (fuel-jettison-sizing and
fuel-jettison-flight-test). Deterministic reduction only; the windmill
N2 regression is the classic linear survey fit, not a transient model of
the relight itself.

## Model (implement exactly)

The prep-verified anchor /tmp/w41spec/anchor_relight.py (pure stdlib,
math only) defines the implementation. Functions (implement exactly):

- windmill_regression(n2_pct_list, tas_list) -> dict {"slope",
  "intercept", "r_squared"}: ordinary least-squares line of windmill N2
  (%) against TAS (m/s), r_squared computed as 1 - ss_res / ss_tot with
  the degenerate constant-line case returning 1.0 when ss_tot is 0.0.
  ValueError if the lists differ in length, if fewer than two points are
  given, or if the TAS variance is zero (denominator n * sxx - sx * sx
  == 0.0). Returned keys exactly as documented.
- min_relight_airspeed(n2_min_required, slope, intercept) -> float TAS in
  m/s where the fitted line reaches the required windmill N2 threshold:
  (n2_min_required - intercept) / slope. ValueError if n2_min_required
  <= 0.0, if slope <= 0.0 (windmill N2 must rise with airspeed), or if
  the computed airspeed is <= 0.0 (threshold below the idle line, relight
  airspeed not reached).
- time_to_idle(relight_time_samples) -> dict {"mean_s", "max_s",
  "limit_s", "verdict"}: mean and worst starter-assisted relight time
  from start to idle over the samples; verdict is "PASS" when max_s <=
  RELIGHT_IDLE_LIMIT_S and "FAIL" otherwise, the comparison inclusive at
  the limit. ValueError if the sample list is empty or any sample is
  negative.
- altitude_band_verdict(relight_results_per_altitude) -> dict mapping
  each altitude band name (str) to the time_to_idle result dict for that
  band's samples. ValueError if the input dict is empty.
- combined_verdict(band_verdicts, min_relight_airspeed_mps) -> "PASS" or
  "FAIL": PASS iff every band verdict is "PASS" and the minimum relight
  airspeed is positive (a determined threshold); any failing band fails
  the whole restart demonstration. ValueError if band_verdicts is empty
  or min_relight_airspeed_mps <= 0.0.

Module constants: WINDMILL_N2_MIN_REQUIRED_PCT = 18.0 (windmill N2
needed before a relight attempt) and RELIGHT_IDLE_LIMIT_S = 60.0
(starter-assisted time-to-idle limit from the type data).

Identity to test: on perfectly linear windmill N2 data the regression
recovers the generating slope and intercept exactly with r_squared 1.0;
raising the required N2 threshold by delta moves the minimum relight
airspeed by delta / slope; time_to_idle verdict flips exactly at the
60.0 s boundary (60.0 PASS, 60.1 FAIL); a single failing band fails the
combined verdict regardless of the other bands; band verdicts replicate
time_to_idle on the same samples.

## Worked example

Windmill survey: TAS [70, 85, 105, 130] m/s with windmill N2 [13.5,
15.75, 18.75, 22.5] %, a perfectly linear spread:
- windmill_regression: slope 0.1500, intercept 3.0000, r_squared 1.0000.
- min_relight_airspeed(WINDMILL_N2_MIN_REQUIRED_PCT = 18.0, 0.15, 3.0) =
  100.0000 m/s (194.4 kt TAS), the airspeed where the fitted line reaches
  the 18.0 % required windmill N2.
- time_to_idle([34.2, 41.7, 38.9, 52.4]): mean_s 41.80 s, max_s 52.40 s,
  limit_s 60.00 s, verdict PASS (worst starter-assisted relight below the
  type-data limit).
- altitude_band_verdict({"FL200": [37.4, 40.2, 41.9], "FL300": [42.6,
  44.8, 47.1], "FL410": [46.5, 49.3, 58.9]}): FL200 mean 39.83 s, max
  41.90 s, PASS; FL300 mean 44.83 s, max 47.10 s, PASS; FL410 mean 51.57
  s, max 58.90 s, PASS.
- combined_verdict on those bands with min_relight_airspeed 100.0 m/s:
  PASS.
- Boundary anchors: time_to_idle([60.0]) PASS (inclusive), time_to_idle
  ([60.1]) FAIL; altitude_band_verdict({"FL410": [62.5]}) gives a FAIL
  band; combined_verdict on that failing band with airspeed 100.0 is
  FAIL.
Run your module and take the real outputs as assert targets; the values
above are the actual outputs of the prep anchor, recaptured by running
python3 /tmp/w41spec/anchor_relight.py.

## Validation list (contract test must include)

- windmill_regression on the worked example: slope 0.1500, intercept
  3.0000, r_squared 1.0000 within 1e-9; keys exactly slope, intercept,
  r_squared.
- Regression identity: windmill_regression on N2 generated as 0.15 * TAS
  + 3.0 recovers slope 0.15 and intercept 3.0 exactly (within 1e-12) at
  any point count of 2 or more; constant N2 data returns r_squared 1.0.
- min_relight_airspeed(18.0, 0.15, 3.0) = 100.0 within 1e-9; threshold
  shift identity: raising n2_min_required by 1.5 raises the airspeed by
  10.0 m/s (1.5 / 0.15).
- time_to_idle([34.2, 41.7, 38.9, 52.4]) = mean_s 41.80, max_s 52.40,
  limit_s 60.0, verdict PASS within 1e-9; inclusive boundary: sample
  exactly 60.0 PASSes, 60.1 FAILs; verdict tracks the max, not the mean
  (a sample list with a low mean but one sample over the limit FAILs).
- altitude_band_verdict on the worked example bands: FL200/FL300/FL410
  all PASS with the stated mean and max values; band name keys preserved
  exactly; a band carrying a 62.5 s sample is FAIL.
- combined_verdict: PASS on the worked-example bands with airspeed 100.0;
  FAIL when any single band FAILs (regardless of the others); FAIL result
  also when every band PASSes but min_relight_airspeed_mps is 0.0 or
  negative; PASS independent of the airspeed magnitude once positive.
- ValueErrors: mismatched list lengths, a single survey point, zero TAS
  variance, n2_min_required <= 0, slope <= 0, threshold below the idle
  line (computed airspeed <= 0), empty relight time samples, a negative
  relight time, empty altitude band dict, empty band verdicts, and
  non-positive minimum relight airspeed in combined_verdict.
- Determinism across repeated calls; no randomness anywhere.

## Corpus fragment (eval/hit1-wave41-in-flight-engine-relight-test.yaml)

Query 1 (copy verbatim):
  "reduce the in-flight-relight demonstration from the windmill-n2 survey: fit the least-squares windmill-n2 regression against true airspeed and read off the windmill-relight-airspeed where the fitted line crosses the required relight threshold"
  intent: "flight-test-operations; windmill N2 vs TAS regression and minimum relight airspeed"
  expected_skill: "flight-test-operations/performance/in-flight-engine-relight-test"
Query 2 (copy verbatim):
  "check the starter-assisted-relight time-to-idle samples at each altitude band against the type-data limit and form the restart-demonstration verdict for the in-flight relight test"
  intent: "flight-test-operations; time-to-idle limit check and combined restart demonstration verdict"
  expected_skill: "flight-test-operations/performance/in-flight-engine-relight-test"
Task ids: w41-in-flight-engine-relight-test-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce an in-flight engine
restart demonstration:" and include the outputs in the Claim. First tag:
in-flight-engine-relight-test. Additional tags ONLY:
windmill-relight-airspeed, starter-assisted-relight, time-to-idle,
restart-demonstration, windmill-n2-regression. NEVER single generic
words (relight, restart, windmill, engine, airspeed, altitude, band,
verdict, idle, regression). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): installed-thrust,
thrust-specific-fuel-consumption, fuel-flow, egt, egt-margin,
exhaust-gas-temperature, throttle-transient, acceleration-transient,
deceleration-transient, transient-times (engine-flight-test);
square-root-weight-correction, range-performance, specific-range,
cruise-mach (cruise-performance-flight-test); specific-excess-power,
total-energy-method, excess-thrust (level-acceleration-test); v1,
decision-speed, vef, balanced-field, engine-out, engine-failure-point
(engine-failure-takeoff-flight-test); rate-of-climb, service-ceiling,
density-altitude-correction (climb-performance-flight-test);
jettison-rate, dump-mast, time-to-landing-weight (fuel-jettison-sizing,
fuel-jettison-flight-test). The word "windmill" in this leaf means engine
windmill N2 only; never route rotor windmill autorotation tasks that
belong to the flight-mechanics rotorcraft leaves.

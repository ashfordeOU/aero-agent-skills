# Wave-41 leaf spec: fuel-jettison-flight-test (flight-test-operations, performance pack)

- Path: skills/flight-test-operations/performance/fuel-jettison-flight-test/
- Pack: performance (verified present at prep with accelerate-stop-distance,
  climb-performance-flight-test, cruise-performance-flight-test,
  engine-failure-takeoff-flight-test, engine-flight-test,
  glide-flight-test, landing-distance-determination,
  level-acceleration-test, rotorcraft-forward-flight-performance-test,
  rotorcraft-performance-flight-test, stall-speed-determination,
  takeoff-distance-determination). No performance sibling reduces a fuel
  dump: the nearest data-analysis siblings are cruise-performance-flight-test
  (its claim is "correct measured fuel flow from the test weight to the
  reference weight with the square-root weight correction, convert corrected
  fuel flow and true airspeed into range performance, fit a quadratic range
  performance curve versus Mach" - fuel flow versus Mach, no dump and no
  weight-vs-time reduction) and engine-flight-test (thrust, EGT and transient
  times, no weight trace reduction). The planning-pack data chain leaves stop
  short of this analysis: flight-test-planning claims "order the test points
  with the build-up approach so risk increases step by step ... and the
  go/no-go gate verdict that releases or blocks the flight",
  flight-test-instrumentation claims "select sensors for the measurement
  parameters ... and verify the recording, telemetry, pre-test calibration,
  and measurement uncertainty chain before the test" and
  flight-test-data-reduction claims "apply the calibration correction with
  the channel slope and intercept, align the time series from separate
  recorders ... smooth the raw trace with the moving average filter" -
  channel calibration and smoothing only, no fitted rate and no
  landing-weight extrapolation. GENUINE FTO gap (fresh probe): whole-tree
  greps "jettison", "fuel-weight", "dump rate" return 0 hits under
  skills/flight-test-operations/; every jettison hit in skills/ sits in
  vehicle-design, headed by the DESIGN leaf
  vehicle-design/sizing/fuel-jettison-sizing whose claim is "compute the
  fuel mass that must be dumpable and the required average jettison rate to
  reach the landing weight within the 15-minute limit of FAR 25.1001, apply
  the design margin to the required rate, split the design flow over the
  dump mast count" - a paper sizing computation from MTOW and MLW with a
  design margin and mast split, no telemetered flight data anywhere. This
  new leaf is the flight-test/verification side of that same function:
  the design leaf sets q_req = (MTOW - MLW) / 900 s; this leaf measures the
  installed rate from telemetered fuel-weight-vs-time samples and verifies
  the demonstration against the same 900 s limit.
- Corpus collision warning (do NOT steal these design-leaf tasks; they route
  on sizing phrasing): eval/hit1-corpus.yaml holds
  w35-fuel-jettison-sizing-1, query "compute the required fuel jettison rate
  to reach the maximum landing weight within 15 minutes per FAR 25.1001"
  (intent "vehicle-design; fuel jettison rate to landing weight within 15
  minutes") and w35-fuel-jettison-sizing-2, query "size the fuel dump mast
  flow split and verify the time to landing weight for the aircraft jettison
  system" (intent "vehicle-design; fuel dump mast flow and jettison time
  check"), both expected_skill vehicle-design/sizing/fuel-jettison-sizing.
  This leaf's corpus queries MUST lead with flight-test tokens (measured
  dump rate, fuel-weight-vs-time telemetry samples, jettison demonstration
  reduction) so they score to flight-test-operations/performance/
  fuel-jettison-flight-test and never to the design leaf.
- Standards id: far-25 (exists in standards-map.yaml; used reference-only by
  the design leaf). Ledger Standard: far-25.
- Family: flight-test-operations

## Claim

Reduce a FAR 25.1001 fuel jettison demonstration flight test (name and
requirement frame only, no verbatim rule text) from telemetered
fuel-weight-vs-time samples taken while the dump is running: fit the sample
weights W(t) with a deterministic least-squares straight line, read the
measured average dump rate from the fitted slope, extrapolate the time the
aircraft needs to go from its takeoff weight down to its landing weight at
that measured rate, and give the PASS or FAIL verdict against the 900 s
limit (PASS when the extrapolated time is within the limit, inclusive).
Checks the measured rate against the required rate q_req that the design
side (vehicle-design/sizing/fuel-jettison-sizing) sets from MTOW and MLW
over the same 900 s limit, and reports the margin in seconds and in kg/s.
Produces the fitted slope, intercept and R^2, the measured dump rate, the
extrapolated time to the landing weight, the PASS/FAIL verdict with its
margin, and the rate-requirement check that verify the jettison
demonstration from flight data. Does NOT do: the design-side sizing of the
dumpable mass, the required or design jettison rate with margin, or the
per-mast flow split from MTOW, MLW and mast count (vehicle-design/sizing/
fuel-jettison-sizing); generic channel calibration, time alignment or
moving-average smoothing of raw traces (flight-test-planning group,
flight-test-data-reduction); sensor selection or sample-rate sizing for the
instrumentation chain (flight-test-instrumentation). Deterministic stdlib
least squares only; scatter in the telemetered samples is handled by the
fit's R^2, not by a stochastic model.

## Model (implement exactly)

Functions (pure stdlib, math only):
- lsq_fit(weights, times) -> dict {"slope", "intercept", "r_squared"}:
  deterministic closed-form least-squares fit of W(t) = intercept + slope *
  t over the dump window, slope in kg/s (negative while fuel is dumped),
  intercept in kg. Closed forms: slope = (n * sum(t*w) - sum(t) * sum(w)) /
  (n * sum(t^2) - (sum(t))^2), intercept = mean(w) - slope * mean(t),
  r_squared = 1 - ss_res / ss_tot with ss_res the residual sum of squares
  and ss_tot = sum((w - mean(w))^2); when ss_tot is 0 (all weights equal)
  r_squared is defined as 1.0. ValueErrors: weights and times of unequal
  length, fewer than MIN_SAMPLES = 2 samples, times not strictly
  increasing, or a zero fit denominator (duplicate time values).
- measured_rate(weights, times) -> float: the measured average dump rate in
  kg/s, taken as -lsq_fit(weights, times)["slope"] so the rate is positive
  for a dump. The fitted slope must be negative (weight decreasing while
  the dump runs); a non-negative fitted slope means no dump is observable
  in the window and raises ValueError (a zero or negative measured rate is
  degenerate).
- time_to_landing_weight(w_start, w_landing, rate) -> float (w_start -
  w_landing) / rate in seconds: the extrapolated time at the measured rate
  to come down from the takeoff weight (the weight at dump start, taken as
  the takeoff weight) to the landing weight target. ValueErrors: w_start <=
  0, w_landing <= 0, w_start <= w_landing (nothing to jettison), rate <= 0.
- verdict(time_s, limit = 900.0) -> dict {"verdict", "limit_s",
  "margin_s"}: "PASS" when time_s <= limit (inclusive at the boundary),
  else "FAIL"; limit_s carries the limit used (default the module constant
  JETTISON_LIMIT_S = 900.0, the 15-minute limit of FAR 25.1001, paraphrased
  frame only); margin_s = limit - time_s, positive for PASS and negative
  for FAIL. ValueErrors: time_s <= 0, limit <= 0.
- rate_meets_requirement(measured, required) -> dict {"meets",
  "margin_kg_s"}: meets is measured >= required (inclusive), margin_kg_s =
  measured - required. required is the design leaf's q_req = (MTOW - MLW) /
  900 s. ValueErrors: measured <= 0, required <= 0.
- reduce_dump_demonstration(weights, times, w_start, w_landing,
  required_rate, limit = 900.0) -> dict {"measured_rate_kg_s",
  "r_squared", "time_to_landing_weight_s", "verdict", "limit_s",
  "margin_s", "meets_required_rate", "required_rate_kg_s",
  "rate_margin_kg_s"}: the one-call summary of the demonstration reduction,
  chaining measured_rate, time_to_landing_weight, verdict and
  rate_meets_requirement in that order; dict keys exactly as documented.
Module constants: JETTISON_LIMIT_S = 900.0, MIN_SAMPLES = 2.

Identity to test: measured_rate equals -lsq_fit slope by construction;
time_to_landing_weight = (w_start - w_landing) / rate exactly; the verdict
boundary is inclusive (a time of exactly 900.0 s is PASS); a rate of
exactly (MTOW - MLW) / 900 gives exactly 900.0 s and PASS; samples that lie
exactly on one straight line are recovered by the fit with r_squared 1.0
and the exact line slope; rate_meets_requirement boundary inclusive
(measured == required is meets True).

## Worked example

Reference transport at the design leaf's own weights: takeoff weight 79,000
kg (MTOW), landing weight 66,500 kg (MLW); the design leaf's required rate
q_req = (79000 - 66500) / 900 = 13.88888889 kg/s is the requirement anchor
for the flight test. Six telemetered samples at 60 s spacing over a 300 s
dump window, small scatter about a ~14.14 kg/s trend (weights 79000, 78148,
77305, 76450, 75605, 74756 kg at times 0, 60, 120, 180, 240, 300 s):

- lsq_fit: slope = -14.1447619 kg/s, intercept = 78999.04762 kg,
  r_squared = 0.9999978496.
- measured_rate = 14.1447619 kg/s (the positive fitted dump rate).
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
  900.0 s and verdict PASS (inclusive); verdict(900.001) is FAIL with
  margin_s -0.001; a slow dump at 13.0 kg/s gives 961.5384615 s and FAIL
  with margin_s -61.53846154.
- Perfect-fit identity: samples exactly on W = 79000 - 14.15 * t recover
  slope -14.15, measured_rate 14.15 and r_squared 1.0 exactly.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds, computed by running the prep anchor script
/tmp/w41spec/anchor_fuel_jettison_ft.py (prep-verified by stdlib math).

## Validation list (contract test must include)

- lsq_fit on the worked example: slope -14.1447619 within 1e-6, intercept
  78999.04762 within 1e-3, r_squared 0.9999978496 within 1e-9.
- measured_rate on the worked example = 14.1447619 within 1e-6; identity
  measured_rate equals -slope.
- time_to_landing_weight(79000, 66500, 14.1447619) = 883.7193644 within
  1e-4; identity (w_start - w_landing) / rate at any valid inputs.
- verdict(883.7193644): PASS with margin_s 16.2806356 within 1e-6;
  inclusive boundary: verdict(900.0) PASS, verdict(900.001) FAIL with
  margin_s -0.001.
- rate_meets_requirement(14.1447619, 13.88888889): meets True, margin_kg_s
  0.2558730159 within 1e-6; inclusive boundary: meets True when measured
  equals required; meets False with margin -0.5 one rate unit below.
- Perfect-fit identity: exact-line samples recover the line slope and rate
  with r_squared exactly 1.0.
- reduce_dump_demonstration returns all 9 keys exactly as documented with
  the worked-example values; summary agrees with the chained functions.
- ValueErrors: fewer than 2 samples, unequal-length arrays, times not
  strictly increasing, duplicate time values (zero denominator), non-
  negative fitted slope (no dump observed), w_start <= 0, w_landing <= 0,
  w_start <= w_landing, rate <= 0, time_s <= 0, limit <= 0, measured <= 0,
  required <= 0.
- Determinism: identical inputs give identical outputs; fixed module
  constants.

## Corpus fragment (eval/hit1-wave41-fuel-jettison-flight-test.yaml)

Query 1 (copy verbatim):
  "reduce the fuel jettison flight test telemetry: least-squares fit the fuel-weight-vs-time samples to the measured dump rate and extrapolate the time to reach the landing weight"
  intent: "flight-test-operations; measured dump rate from telemetered fuel-weight-vs-time samples"
  expected_skill: "flight-test-operations/performance/fuel-jettison-flight-test"
Query 2 (copy verbatim):
  "verify the fuel jettison demonstration from the flight test data: check the measured dump rate against the required rate and judge the PASS or FAIL verdict against the 900 s limit from the telemetered weight samples"
  intent: "flight-test-operations; jettison demonstration verification, measured rate versus the 900 s limit"
  expected_skill: "flight-test-operations/performance/fuel-jettison-flight-test"
Task ids: w41-fuel-jettison-flight-test-1 and -2. Both queries lead with
flight-test tokens (flight test telemetry, telemetered weight samples,
measured dump rate, demonstration verification) and never with the design
leaf's sizing verbs (compute the required rate, size the mast flow split,
design margin), so they must not collide with w35-fuel-jettison-sizing-1
and -2 listed in the header.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce a fuel jettison flight test
demonstration:" and include the outputs in the Claim. First tag:
fuel-jettison-flight-test. Additional tags ONLY: measured-jettison-rate,
fuel-weight-vs-time-fit, dump-rate-requirement-check,
jettison-demonstration-verification. NEVER single generic words (fuel,
weight, rate, time, jettison, dump, flight, test, reduction, limit,
verdict). 50-150 words, <=1000 chars, no em dash, no "classified", action
verb present.

FORBIDDEN TOKENS (belong to the design leaf vehicle-design/sizing/
fuel-jettison-sizing and its corpus tasks): dumpable-fuel-mass,
required-jettison-rate, design-jettison-rate, design-margin,
fuel-jettison-mast, per-mast-flow, mast-count, dump-mast-flow-split,
mtow-mlw-sizing, sizing (as the operative noun). Also forbidden from the
planning-pack data leaves: calibration-correction, time-alignment,
moving-average-filter, sample-rate-sizing, anti-aliasing, nyquist,
build-up-approach, go-no-go (flight-test-planning and flight-test-
instrumentation and flight-test-data-reduction). Do NOT put "compute the
required ... rate" phrasing in the description, tags or corpus queries:
that phrasing is exactly what routes the two w35 design-leaf tasks.

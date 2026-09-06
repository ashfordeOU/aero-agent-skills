# Wave-42 leaf spec: rotorcraft-autorotation-flight-test (flight-test-operations, performance pack)

- Path: skills/flight-test-operations/performance/rotorcraft-autorotation-flight-test/
- Pack: performance (verified present at prep with accelerate-stop-distance,
  climb-performance-flight-test, cruise-performance-flight-test,
  engine-failure-takeoff-flight-test, engine-flight-test,
  fuel-jettison-flight-test, glide-flight-test,
  in-flight-engine-relight-test, landing-distance-determination,
  level-acceleration-test, rotorcraft-forward-flight-performance-test,
  rotorcraft-performance-flight-test, stall-speed-determination,
  takeoff-distance-determination).
- Closest siblings: rotorcraft-performance-flight-test (its claim is
  "convert measured main rotor torque and rotor speed into shaft power,
  compute the measured figure of merit ... correct a measured vertical rate
  of climb for the test weight ... reduce hover power-required points
  measured across density altitudes to a hover ceiling" - hover power,
  figure of merit, ROC weight correction and ceiling determination only; a
  measured descent point enters solely as a negative-ROC input to the same
  hover-power machinery, and nothing in its trigger list or body claims an
  autorotation reduction),
  rotorcraft-forward-flight-performance-test (level-flight polar only),
  flight-mechanics/performance/rotorcraft-autorotative-descent (the
  ANALYTIC estimate: energy-method sink rate P_min / W plus the
  Talbot-Schroers empirical correlation of NASA TM 78452, computed from
  weight and minimum level-flight power; its Related-leaves section closes
  with "flight-test-operations/performance/rotorcraft-performance-flight-test:
  flight-test reduction of rotorcraft performance, not to be confused with
  this analytic estimate", naming the FTO family as the measured-data side
  without owning the autorotation demonstration reduction itself),
  flight-mechanics/performance/rotorcraft-axial-descent-flow-states (flow-
  state physics: vortex-ring and windmill states, not test reduction).
  Whole-tree greps at prep: "autorotat" inside
  skills/flight-test-operations/*/*/SKILL.md hits ONLY the fixed-wing
  departure/stall sense in envelope/high-angle-of-attack-testing and
  envelope/spin-testing ("resists entering autorotation", "developed spin
  is the steady autorotation") and the in-flight-engine-relight-test
  deferral lines 227-229, which send ROTORCRAFT windmill/descent state to
  the flight-mechanics leaves. GENUINE FTO gap (fresh probe): no FTO leaf
  reduces a rotorcraft power-off autorotation demonstration; this leaf is
  the flight-test side of the function the FM analytic leaf estimates, the
  same measurement-vs-design split the wave-41 fuel-jettison precedent
  blessed (vehicle-design/sizing/fuel-jettison-sizing versus
  flight-test-operations/performance/fuel-jettison-flight-test).
- Standards id: far-29 (exists in standards-map.yaml; sibling convention -
  both FTO rotorcraft leaves and FM rotorcraft-autorotative-descent carry
  far-29 reference-only). Ledger Standard: far-29.
- Family: flight-test-operations

## Claim

Reduce a FAR 29 power-off rotorcraft autorotation demonstration flight test
(name and requirement frame only, no verbatim rule text) from the
telemetered record: fit the least-squares regression of pressure altitude
against time over the steady autorotative descent window, read the measured
sink rate from the fitted slope, run the rotor-RPM band checks across the
three phases of the demonstration (minimum rotor RPM during the entry
decay against the declared floor, steady-state rotor RPM samples against
the declared band, peak flare rotor RPM against the declared recovery
target), compute the altitude lost to the recovery as the pressure altitude
at flare initiation minus the pressure altitude at the re-established
level flight, and give the PASS or FAIL verdict against the declared limit
for each check plus the combined demonstration verdict. Produces the
fitted slope, intercept and R-squared, the measured sink rate in m/s
within the realistic 8 to 15 m/s autorotative band, the three rotor-RPM
check verdicts, the altitude lost to the recovery with its limit verdict
and margin, and the overall PASS or FAIL verdict that gates the
autorotation demonstration. Does NOT do: the analytic estimate of the
power-off descent rate from minimum level-flight power, weight and the
Talbot-Schroers correlation (flight-mechanics/performance/
rotorcraft-autorotative-descent); shaft power from torque, measured figure
of merit, weight and density power correction, corrected vertical rate of
climb or hover ceiling determination (rotorcraft-performance-flight-test);
the level-flight polar (rotorcraft-forward-flight-performance-test);
vortex-ring or windmill flow-state physics
(flight-mechanics/performance/rotorcraft-axial-descent-flow-states); the
fixed-wing stalled-wing autorotation band (flight-mechanics/stability-
control/spin-recovery, envelope leaves). Deterministic stdlib least
squares only; scatter in the telemetered samples is carried by the fit's
R-squared, not by a stochastic model.

## Model (implement exactly)

The prep-verified anchor /tmp/w42spec/
anchor_rotorcraft_autorotation_flight_test.py (pure stdlib, math only)
defines the implementation. Functions (implement exactly):

- lsq_fit(y_list, x_list) -> dict {"slope", "intercept", "r_squared"}:
  ordinary least-squares line y = intercept + slope * x over the steady
  autorotative descent, slope in m/s (negative while descending),
  intercept in m. Closed forms: slope = (n * sum(x*y) - sum(x) * sum(y)) /
  (n * sum(x^2) - (sum(x))^2), intercept = mean(y) - slope * mean(x),
  r_squared = 1 - ss_res / ss_tot with ss_res the residual sum of squares
  and ss_tot = sum((y - mean(y))^2); when ss_tot is 0 (constant altitude
  samples) r_squared is defined as 1.0. ValueErrors: y and x lists of
  unequal length, fewer than MIN_SAMPLES = 2 points, or a zero fit
  denominator (n * sxx - sx * sx == 0.0, all x equal).
- sink_rate(press_alt_m, time_s) -> float: the measured autorotative sink
  rate in m/s, taken as -lsq_fit(press_alt_m, time_s)["slope"] so the rate
  is positive for a descent. The fitted slope must be negative (pressure
  altitude decreasing while the autorotation is steady); a fitted slope
  >= 0.0 means no descent is observable in the window and raises ValueError
  (a zero or negative measured rate is degenerate).
- entry_rpm_decay_check(rpm_samples, floor_pct = ENTRY_RPM_FLOOR_PCT) ->
  dict {"min_rpm_pct", "floor_pct", "verdict"}: the minimum rotor RPM
  percent seen across the power-off entry decay samples against the
  declared floor; verdict is "PASS" when min_rpm_pct >= floor_pct
  (inclusive at the floor) and "FAIL" otherwise. ValueErrors: empty sample
  list, any negative sample, floor_pct <= 0.
- steady_rpm_band_check(rpm_samples, low_pct = STEADY_RPM_BAND_LOW_PCT,
  high_pct = STEADY_RPM_BAND_HIGH_PCT) -> dict {"mean_rpm_pct",
  "min_rpm_pct", "max_rpm_pct", "band_low_pct", "band_high_pct",
  "verdict"}: every steady-descent rotor RPM sample must lie inside the
  declared band, inclusive at both edges; verdict is "PASS" when
  min_rpm_pct >= low_pct and max_rpm_pct <= high_pct. ValueErrors: empty
  sample list, any negative sample, low_pct <= 0, high_pct < low_pct.
- flare_rpm_recovery_check(rpm_samples,
  target_pct = FLARE_RPM_RECOVERY_TARGET_PCT) -> dict {"peak_rpm_pct",
  "recovery_target_pct", "verdict"}: the peak rotor RPM percent reached
  during the flare against the declared recovery target; verdict is "PASS"
  when peak_rpm_pct >= target_pct (inclusive) and "FAIL" otherwise.
  ValueErrors: empty sample list, any negative sample, target_pct <= 0.
- altitude_lost_to_recovery(h_flare_start_m, h_recovery_m) -> float:
  h_flare_start_m - h_recovery_m in m, the pressure altitude at flare
  initiation minus the pressure altitude at the re-established level
  flight (non-negative). ValueErrors: either altitude <= 0, or
  h_recovery_m > h_flare_start_m (the recovery gained altitude; no flare
  loss to report).
- altitude_loss_verdict(loss_m, limit_m = ALTITUDE_LOSS_LIMIT_M) -> dict
  {"loss_m", "limit_m", "verdict", "margin_m"}: verdict is "PASS" when
  loss_m <= limit_m (inclusive at the boundary), "FAIL" otherwise;
  margin_m = limit_m - loss_m, positive for PASS and negative for FAIL.
  ValueErrors: loss_m < 0, limit_m <= 0.
- reduce_autorotation_demonstration(entry_rpm, steady_rpm, steady_alt_m,
  steady_time_s, flare_rpm, h_flare_start_m, h_recovery_m) -> dict
  {"sink_rate_mps", "r_squared", "entry_verdict", "steady_verdict",
  "flare_verdict", "altitude_verdict", "altitude_loss_m",
  "overall_verdict"}: the one-call summary of the demonstration
  reduction, chaining sink_rate, entry_rpm_decay_check,
  steady_rpm_band_check, flare_rpm_recovery_check and
  altitude_loss_verdict in that order; overall_verdict is "PASS" iff every
  component verdict is "PASS". Dict keys exactly as documented.

Module constants: MIN_SAMPLES = 2, ENTRY_RPM_FLOOR_PCT = 90.0 (declared
minimum rotor RPM during the entry decay), STEADY_RPM_BAND_LOW_PCT = 95.0
and STEADY_RPM_BAND_HIGH_PCT = 105.0 (declared steady autorotation RPM
band), FLARE_RPM_RECOVERY_TARGET_PCT = 100.0 (declared flare recovery
target), ALTITUDE_LOSS_LIMIT_M = 60.0 (declared altitude-lost-to-recovery
limit).

Identity to test: sink_rate equals -lsq_fit slope by construction; on
perfectly linear pressure-altitude data the fit recovers the generating
slope and intercept exactly with r_squared 1.0; every verdict boundary is
inclusive (floor exactly 90.0 PASSes, 89.9 FAILs; band samples exactly at
95.0 and 105.0 PASS, 105.1 FAILs; flare peak exactly 100.0 PASSes, 99.9
FAILs; altitude loss exactly 60.0 m PASSes, 60.1 FAILs); a single failing
check fails the overall verdict regardless of the others; each component
verdict replicates its standalone function on the same inputs.

## Worked example

Telemetered demo record of a power-off autorotation demonstration (rotor
RPM in percent NR, pressure altitude in m): entry RPM history across the
power cut [100.0, 94.6, 91.2, 91.6, 95.4, 96.7]; steady autorotative
descent window of 15 pressure-altitude samples at 2 s spacing over 28 s,
Hp = [620.4, 599.7, 578.6, 557.2, 535.9, 514.8, 493.6, 472.3, 451.0,
429.8, 408.5, 387.1, 366.0, 344.7, 323.2] m at t = [0, 2, 4, 6, 8, 10,
12, 14, 16, 18, 20, 22, 24, 26, 28] s; steady-descent rotor RPM samples
[96.8, 97.4, 97.1, 97.6, 96.9, 97.5, 97.2, 97.7, 96.7, 97.5, 97.3, 97.0,
97.6, 96.9, 97.4]; flare RPM history [96.5, 99.4, 102.1, 103.6, 103.9,
103.1]; flare-initiation pressure altitude 458.0 m, recovery pressure
altitude 412.6 m:

- lsq_fit on the steady window: slope = -10.6225 m/s, intercept =
  620.9016666667 m, r_squared = 0.9999964366.
- sink_rate = 10.6225 m/s, inside the realistic 8 to 15 m/s steady
  autorotation sink band (about 2091 ft/min equivalent; the analytic FM
  leaf's measured band is 1500-2000 ft/min for minimum rate, and this
  demonstration flies a slightly higher working sink rate).
- entry_rpm_decay_check([100.0, 94.6, 91.2, 91.6, 95.4, 96.7]):
  min_rpm_pct 91.2, floor_pct 90.0, verdict PASS (minimum during the decay
  holds above the declared floor).
- steady_rpm_band_check(steady samples): mean_rpm_pct 97.24, min_rpm_pct
  96.7, max_rpm_pct 97.7, band_low_pct 95.0, band_high_pct 105.0,
  verdict PASS (every sample inside the declared band).
- flare_rpm_recovery_check([96.5, 99.4, 102.1, 103.6, 103.9, 103.1]):
  peak_rpm_pct 103.9, recovery_target_pct 100.0, verdict PASS (the flare
  rebuilds rotor RPM above the recovery target).
- altitude_lost_to_recovery(458.0, 412.6) = 45.4 m; altitude_loss_verdict:
  loss_m 45.4, limit_m 60.0, verdict PASS, margin_m 14.6.
- reduce_autorotation_demonstration returns sink_rate_mps 10.6225,
  r_squared 0.9999964366, entry_verdict PASS, steady_verdict PASS,
  flare_verdict PASS, altitude_verdict PASS, altitude_loss_m 45.4,
  overall_verdict PASS.
- Boundary anchors: entry min exactly 90.0 PASSes and 89.9 FAILs; band
  samples exactly 95.0 and 105.0 PASS and a 105.1 sample FAILs; flare peak
  exactly 100.0 PASSes and 99.9 FAILs; altitude loss exactly 60.0 m PASSes
  with margin_m 0.0 and 60.1 FAILs with margin_m -0.1; a flat
  pressure-altitude record (all samples equal, no descent observable)
  raises ValueError.
Run your module and take the real outputs as assert targets; the values
above are the actual outputs of the prep anchor, recaptured by running
python3 /tmp/w42spec/anchor_rotorcraft_autorotation_flight_test.py (exit 0).

## Validation list (contract test must include)

- lsq_fit on the worked steady window: slope -10.6225 within 1e-4,
  intercept 620.9016666667 within 1e-6, r_squared 0.9999964366 within
  1e-9; keys exactly slope, intercept, r_squared.
- Regression identity: lsq_fit on altitude generated as 620.0 - 10.5 * t
  recovers slope -10.5 and intercept 620.0 exactly (within 1e-12) at any
  point count of 2 or more; constant-altitude samples return r_squared 1.0
  and still raise ValueError from sink_rate (no descent).
- sink_rate on the worked window = 10.6225 within 1e-4; identity
  sink_rate equals -lsq_fit slope.
- entry_rpm_decay_check on the worked entry history: min_rpm_pct 91.2,
  verdict PASS; inclusive boundary: min exactly 90.0 PASSes, 89.9 FAILs;
  verdict tracks the minimum sample, not the mean.
- steady_rpm_band_check on the worked samples: mean_rpm_pct 97.24,
  min_rpm_pct 96.7, max_rpm_pct 97.7, verdict PASS; inclusive edges:
  samples at exactly 95.0 and 105.0 PASS, a 105.1 sample FAILs; verdict
  tracks the extreme samples, not the mean.
- flare_rpm_recovery_check on the worked flare history: peak_rpm_pct
  103.9, verdict PASS; inclusive boundary: peak exactly 100.0 PASSes,
  99.9 FAILs.
- altitude_lost_to_recovery(458.0, 412.6) = 45.4 within 1e-9; identity
  h_flare_start_m - h_recovery_m at any valid inputs.
- altitude_loss_verdict(45.4): PASS with margin_m 14.6 within 1e-9;
  inclusive boundary: loss exactly 60.0 PASSes with margin_m 0.0, 60.1
  FAILs with margin_m -0.1.
- reduce_autorotation_demonstration returns all 8 keys exactly as
  documented with the worked-example values; overall_verdict FAILs when
  any single component check FAILs (regardless of the others) and PASSes
  only when all four are PASS; summary agrees with the chained functions.
- ValueErrors: unequal-length y/x lists, a single sample, zero fit
  denominator (all x equal), non-negative fitted slope (no descent
  observed in the window), empty entry/steady/flare RPM lists, negative
  rotor RPM samples, floor_pct <= 0, low_pct <= 0, high_pct < low_pct,
  target_pct <= 0, non-positive flare or recovery altitude, recovery
  altitude above flare-initiation altitude, negative altitude loss,
  limit_m <= 0.
- Determinism across repeated calls; no randomness anywhere.

## Corpus fragment (eval/hit1-wave42-rotorcraft-autorotation-flight-test.yaml)

Query 1 (copy verbatim):
  "reduce the power-off autorotation demonstration flight test from the telemetered record: least-squares fit the pressure-altitude-vs-time samples over the steady autorotative descent to the measured sink rate"
  intent: "flight-test-operations; measured autorotative sink rate from telemetered pressure-altitude samples"
  expected_skill: "flight-test-operations/performance/rotorcraft-autorotation-flight-test"
Query 2 (copy verbatim):
  "check the rotor-rpm band of the rotorcraft autorotation demonstration through the entry decay, the steady descent and the flare recovery and judge the altitude-loss and overall demonstration verdicts against the declared limits"
  intent: "flight-test-operations; rotor RPM band checks and altitude-loss verdict of the autorotation demonstration"
  expected_skill: "flight-test-operations/performance/rotorcraft-autorotation-flight-test"
Task ids: w42-rotorcraft-autorotation-flight-test-1 and -2. Both queries
lead with flight-test tokens (flight test, telemetered record, measured
sink rate, demonstration verdicts) and never with the analytic FM leaf's
estimate phrasing (estimate the descent rate from the minimum power,
energy-method, Talbot correlation), so they must not collide with tasks
routed to flight-mechanics/performance/rotorcraft-autorotative-descent.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce a rotorcraft power-off
autorotation demonstration flight test:" and include the outputs in the
Claim. First tag: rotorcraft-autorotation-flight-test. Additional tags
ONLY: measured-sink-rate, rotor-rpm-band-check,
autorotation-demonstration-reduction, flare-altitude-loss. NEVER single
generic words (rotorcraft, autorotation, descent, sink, rpm, flare,
altitude, test, flight, verdict, band, reduction, limit). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to the analytic FM leaf
flight-mechanics/performance/rotorcraft-autorotative-descent and the FTO
rotorcraft siblings): energy-method, talbot-correlation,
power-to-weight-ratio, rotor-energy-balance, minimum-descent-rate,
descent-rate-estimate (rotorcraft-autorotative-descent); shaft-power,
torque-to-power, measured-figure-of-merit, ideal-induced-power,
induced-power, hover-ceiling, weight-density-correction,
corrected-vertical-rate-of-climb, hover-power-required,
hover-ceiling-determination (rotorcraft-performance-flight-test);
level-flight-polar (rotorcraft-forward-flight-performance-test);
vortex-ring, windmill-state (rotorcraft-axial-descent-flow-states). The
word "autorotation" in this leaf means the power-off rotorcraft descent
demonstration only; never route fixed-wing stalled-wing autorotation
tasks (spin-recovery, high-angle-of-attack-testing envelope leaves) or the
analytic FM descent estimate, and never place "estimate", "predict" or
"compute the descent rate" phrasing in the description, tags or corpus
queries: that phrasing routes to the flight-mechanics leaf.

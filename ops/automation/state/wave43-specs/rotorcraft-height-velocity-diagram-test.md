# Wave-43 leaf spec: rotorcraft-height-velocity-diagram-test
# (flight-test-operations, performance pack)

- Path: skills/flight-test-operations/performance/rotorcraft-height-velocity-diagram-test/
- Pack: performance (present siblings at prep: accelerate-stop-distance,
  climb-performance-flight-test, cruise-performance-flight-test,
  engine-failure-takeoff-flight-test, engine-flight-test,
  fuel-jettison-flight-test, glide-flight-test,
  in-flight-engine-relight-test, landing-distance-determination,
  level-acceleration-test, rotorcraft-autorotation-flight-test,
  rotorcraft-forward-flight-performance-test,
  rotorcraft-performance-flight-test, stall-speed-determination,
  takeoff-distance-determination).
- Claim fences (quoted from the sibling frontmatter at prep):
  - rotorcraft-autorotation-flight-test (same pack; MED overlap flagged
    honestly, fence by regime and by framing): its description opens "Use
    when you must reduce a rotorcraft power-off autorotation demonstration
    flight test: least-squares fit the telemetered pressure-altitude
    samples against time over the steady autorotative descent, read the
    measured sink rate from the fitted slope, run the rotor-RPM checks
    across the entry decay, steady descent and flare recovery against the
    declared floor, band and recovery target, compute the altitude lost to
    the recovery from the flare-initiation and re-established level-flight
    altitudes, and give the PASS or FAIL verdict per check plus the overall
    demonstration verdict", with tags measured-sink-rate,
    rotor-rpm-band-check, autorotation-demonstration-reduction,
    flare-altitude-loss. Its worked example is a demonstration cut from
    altitude with a 28 s steady autorotative descent window; the altitude
    loss is measured between the flare initiation and the re-established
    LEVEL FLIGHT, and its reduction ends in a landing-capable level
    condition. It never touches the engine-failure-at-hover or
    engine-failure-at-low-speed regime below 200 ft AGL, never measures a
    recognition delay or a touchdown sink, and never produces a
    height-velocity boundary or avoid-region map. The new leaf owns that
    complementary region: demonstrations initiated by an engine failure at
    hover or at low speed (0 to 40 KTAS, below 200 ft AGL) whose entire
    record is recognition delay, autorotation establishment and the
    touchdown flare, reduced to the height-velocity (dead-man-curve)
    boundary where the measured height loss plus the recovery altitude
    equals the starting height, the measured avoid-region map over the
    (height, speed) grid and the clearance verdict against the predicted
    height-velocity diagram. A passing demo started far above the boundary
    does carry a brief steady autorotation segment between establishment
    and the standard flare; this leaf stops its reduction at the
    flare-initiation mark, keeps that segment as flown and never regresses
    it nor runs rotor-RPM checks (those belong to the sibling leaf). In the
    worked record the hover marginal-pass steady segment lasts about 0.16 s.
  - flight-mechanics/performance/rotorcraft-autorotative-descent (analytic
    sink model, referenced, not duplicated): its description opens "Use
    when you must estimate the power-off autorotative descent performance
    of a single-rotor helicopter: the energy-method sink rate from the
    minimum level-flight power and the weight, the empirical minimum
    descent rate from the Talbot-Schoers correlation of NASA TM 78452
    (public domain), its equivalent power-based entry, and the
    feet-per-minute conversion". The steady autorotative sink rates of the
    worked demonstration record (33 ft/s easing to 28 ft/s across 0 to 40
    KTAS) are QUOTED INPUTS supplied by that analytic leaf for the
    representative rotorcraft, never re-derived here; the predicted
    height-velocity diagram compared for clearance is likewise an input
    table built from that leaf's sink model in the standard energy
    reduction (recognition at the full steady sink over the measured
    delay, entry with the linear sink build, flare arresting the steady
    sink to the limit sink at a declared 0.45 g mean deceleration), and
    the module only subtracts it from the measured boundary.
  - flight-mechanics/performance/rotorcraft-vertical-climb-performance
    (hover-axis climb prediction): its description opens "Use when you
    must compute the vertical climb performance of a rotorcraft rotor with
    axial momentum theory: the climb induced velocity from the hover
    induced velocity and the climb rate, the induced power through an
    induced power factor, the total rotor power required in a vertical
    climb as induced plus profile power, and the maximum vertical rate of
    climb for an available shaft power". Climb is out of scope here; every
    record of this leaf descends to a touchdown.
  Whole-tree greps at prep (REAL receipts, run on the wave-42 close tree):
  "dead-man" and "dead man": 0 files under skills/; "height-velocity": 1
  file under skills/, flight-mechanics/stability-control/phugoid-mode-
  analysis/SKILL.md, and only as the tag height-velocity-exchange (the
  phugoid airspeed-to-height energy exchange of a fixed-wing long-period
  mode, a different compound with no dead-man-curve, hover engine-failure
  or rotorcraft demonstration content); the rotorcraft-autorotation-flight-
  test SKILL.md carries 0 hits for height-velocity, dead-man or H-V.
  eval/hit1-corpus.yaml greps (REAL): "height-velocity" 0 hits,
  "dead-man" and "dead man" 0 hits, "hover engine-failure height-loss" 0
  hits; "height loss" hits 2 tasks, both w25-windshear-analysis (the
  energy height loss rate of the windshear F-factor escape decision), a
  distinct energy-height context whose tasks route on windshear F-factor
  tokens; the flight-mechanics phugoid corpus tasks
  (w23-phugoid-mode-analysis-1/-2 and the short-period task) carry no
  height-velocity tokens. GENUINE FTO gap (fresh probe, GO): no FTO leaf
  reduces the hover and low-speed engine-failure height-velocity
  demonstration; the wave-42 autorotation leaf landed the steady-descent
  measurement side, and this leaf is its low-altitude complement, the
  flight-test side of the height-velocity function the FM leaves predict.
- Standards id: far-29 (exists in standards-map.yaml; sibling convention:
  both FTO rotorcraft leaves and FM rotorcraft-autorotative-descent carry
  far-29 reference-only, and FAR 29 is named and framed only, no rule text
  reproduced). Ledger Standard: far-29.
- Family: flight-test-operations

## Claim

Reduce a FAR 29 rotorcraft height-velocity (dead-man-curve) demonstration
flight test (requirement named and framed only) from the hover and
low-speed engine-failure demonstration runs: for each run, cut at a
starting height of 20 to 200 ft AGL at 0 to 40 KTAS, read the baro/radar
altitude-loss-versus-time trace from the engine-failure event mark to the
touchdown, measure the engine-failure recognition delay (failure mark to
first control input, the 0.5 to 1.0 s band of the worked record), the time
to establish autorotation and complete the flare or landing, the height
lost before the flare and the recovery altitude the flare consumes, apply
the declared reaction time allowance to the recognition-phase height loss,
and give the PASS or FAIL touchdown verdict against the declared
safe-touchdown sink limit. Interpolate, at each speed, the height-velocity
boundary height where the measured height loss plus the recovery altitude
equals the starting height (the linear crossing of the touchdown-sink
versus starting-height line through the highest FAILING and lowest PASSING
demonstration pair at the sink limit). Build the measured avoid-region map
over the (height, speed) grid, AVOID strictly below the reduced boundary
at each speed, SAFE at or above it, and compare the boundary against the
predicted height-velocity diagram for the clearance verdict at each speed
(PASS when the measured avoid region does not extend above the predicted
boundary). Produces the recognition delay, the establishment and recovery
times, the measured height-loss split with the flare and recovery
altitudes, the touchdown verdict of every demonstration, the reduced
boundary heights with and without the reaction time allowance, the
measured avoid-region map and the per-speed clearance margins and verdicts
that gate the height-velocity demonstration. Does NOT do: the steady
autorotative-descent demonstration reduction (least-squares sink-rate
regression over the steady window, the rotor-RPM floor, band and recovery
checks, and the altitude lost to a recovery ending in re-established level
flight: rotorcraft-autorotation-flight-test; this leaf never fits a steady
window and never checks rotor RPM, and any steady segment in a passing
high-start record is left unreduced); the analytic estimate of the
power-off sink rate from minimum level-flight power, weight and the
Talbot-Schroers correlation, and the analytic predicted height-velocity
diagram itself (flight-mechanics/performance/rotorcraft-autorotative-
descent: the sink rates and the predicted boundary table are quoted inputs
here); hover-axis climb prediction (flight-mechanics/performance/
rotorcraft-vertical-climb-performance); hover power, figure of merit or
ceiling reduction (rotorcraft-performance-flight-test); the level-flight
polar (rotorcraft-forward-flight-performance-test); vortex-ring and
windmill flow-state physics (flight-mechanics/performance/rotorcraft-
axial-descent-flow-states); fixed-wing phugoid airspeed-to-height energy
exchange (flight-mechanics/stability-control/phugoid-mode-analysis, whose
height-velocity-exchange tag is a different compound and stays untouched);
windshear energy-height analysis (flight-mechanics/performance/
windshear-analysis). Units are ft AGL, KTAS, seconds and ft/min; the
reduction is deterministic stdlib arithmetic on measured marks and traces,
never a stochastic model.

## Model (implement exactly)

Pure stdlib, math only, deterministic closed-form reduction of measured
marks and trace read-offs. Module constants (representative demonstration
rotorcraft; declared values, FAR 29 frames the demonstration requirement
by name only):
- SAFE_TOUCHDOWN_FPM = 600.0: declared safe-touchdown sink-rate limit,
  ft/min (10 ft/s), the demonstration PASS threshold, inclusive.
- REACTION_ALLOWANCE_S = 1.0: declared reaction time allowance, s, added
  beyond the measured recognition delay when the published boundary is
  read off.

Functions (all raise ValueError on non-physical input; none uses exact-
float asserts internally):
- recognition_delay(t_reaction_s, t_failure_s) -> float: the measured
  engine-failure recognition delay in s, the trace time of the first
  control input minus the trace time of the engine-failure event mark.
  ValueError if t_failure_s < 0 or t_reaction_s <= t_failure_s.
- recognition_loss_with_allowance(h_rec_measured_ft,
  sink_end_recognition_fps, allowance_s = REACTION_ALLOWANCE_S) -> float:
  the recognition-phase height loss in ft with the declared reaction time
  allowance applied: the measured height lost over the recognition window
  plus the additional height the rotorcraft sinks at the measured
  recognition-window end sink rate during the allowance seconds. ValueError
  if h_rec_measured_ft < 0, sink_end_recognition_fps < 0 or
  allowance_s < 0.
- time_to_establish_autorotation(t_flare_s, t_reaction_s) -> float: the
  time in s from the first control input to the flare-initiation mark, the
  measured time to establish autorotation and set up the flare. ValueError
  if t_reaction_s < 0 or t_flare_s <= t_reaction_s.
- height_lost_to_flare(h_start_ft, h_flare_ft) -> float: the measured
  height lost in ft from the engine-failure starting height to the
  flare-initiation mark (the recognition and establishment losses
  together, read off the baro/radar altitude trace). ValueError if
  h_start_ft <= 0 or h_flare_ft <= 0 or h_flare_ft >= h_start_ft.
- flare_recovery_altitude(h_flare_ft, h_contact_ft = 0.0) -> float: the
  recovery altitude in ft, the altitude consumed completing the flare and
  landing, the flare-initiation altitude above the touchdown altitude
  (0 ft for a touchdown). ValueError if h_flare_ft <= 0 or h_contact_ft
  < 0 or h_contact_ft >= h_flare_ft.
- touchdown_verdict(touchdown_sink_fpm, limit_fpm =
  SAFE_TOUCHDOWN_FPM) -> "PASS" or "FAIL": PASS when the measured
  touchdown sink rate is at or below the declared limit, inclusive at the
  limit. ValueError if touchdown_sink_fpm < 0 or limit_fpm <= 0.
- interpolate_boundary_height(fail_h0_ft, pass_h0_ft, fail_sink_fpm,
  pass_sink_fpm, limit_fpm = SAFE_TOUCHDOWN_FPM) -> float: the reduced
  height-velocity boundary height in ft at one speed, the linear crossing
  of the touchdown-sink versus starting-height line through the bracketing
  demonstration pair (highest FAILING starting height, lowest PASSING
  starting height) at the declared touchdown sink limit. ValueError if
  either height <= 0, pass_h0_ft <= fail_h0_ft (no FAIL to PASS flip in
  the swept heights: the sweep must extend further), fail_sink_fpm <=
  limit_fpm, pass_sink_fpm > limit_fpm, limit_fpm <= 0, or the two sink
  rates are equal (flat line).
- build_avoid_map(heights_ft, speeds_kt, boundary_ft) -> list of dicts:
  the measured avoid-region map over the (height AGL, speed KTAS) grid,
  one dict per cell with keys height_ft, speed_kt, region; region AVOID
  when the height is strictly below the reduced boundary at that speed
  (inside the dead-man-curve region), SAFE at or above it. ValueError if
  the height or speed grid is empty, len(boundary_ft) !=
  len(speeds_kt), any grid height <= 0 or any boundary height < 0.
- clearance_verdict(measured_boundary_ft, predicted_boundary_ft) -> dict:
  the clearance of the measured height-velocity boundary against the
  predicted height-velocity diagram at one speed, keys
  measured_boundary_ft, predicted_boundary_ft, margin_ft (predicted minus
  measured) and verdict; verdict PASS when the measured avoid region does
  not extend above the predicted boundary, margin >= 0 inclusive. ValueError
  if either height < 0.

Identities to test (closed form, order-safe asserts only):
- recognition_delay(t_reaction, t_failure) = t_reaction - t_failure; on
  the worked hover record 0.6 s.
- recognition_loss_with_allowance(h_rec, sink_end) = h_rec + 6.0 with the
  default 1.0 s allowance at the worked 6.0 ft/s recognition-window end
  sink, and equals h_rec with allowance_s = 0.
- time_to_establish_autorotation(t_flare, t_reaction) =
  t_flare - t_reaction.
- Height-loss split identity on any marginal passing demonstration:
  height_lost_to_flare(h0, h_flare) + flare_recovery_altitude(h_flare,
  0.0) == h0 exactly to float noise (anchor residual 0.00e+00 at every
  speed); time identity: recognition delay + establishment time + flare
  duration == measured failure-to-touchdown time.
- Boundary reduction: the interpolated boundary lies strictly inside the
  bracketing pair and falls where the measured height loss plus the
  recovery altitude equals the starting height; with the declared
  allowance it rises by exactly sink_end_recognition * allowance (6.0 ft
  in the worked record).
- Avoid map: every grid cell at or above the boundary is SAFE and every
  cell strictly below is AVOID; cells total heights x speeds.
- Clearance: PASS whenever predicted >= measured (inclusive), margin =
  predicted - measured; all five worked speeds PASS.
- ValueErrors across every function (26 offending-input cases exercised by
  the anchor, all raised).
- Determinism; no imports beyond math; no randomness anywhere.

## Worked example

Representative rotorcraft height-velocity demonstration record, speeds
0, 10, 20, 30, 40 KTAS, height sweep 20 to 200 ft AGL (grid 20, 30, 40,
50, 60, 70, 80, 90, 100, 120, 150, 200 ft). Per speed the record carries
measured parameters (recognition delay tau_r from 0.5 to 1.0 s across the
speeds, recognition-window end sink 6.0 ft/s, steady autorotative sink
rate quoted from the flight-mechanics autorotative-descent leaf, time to
establish autorotation, declared minimum flare altitude). The deterministic
trace model behind the record (documented, generator side only; the module
above only reads measured marks): after the failure event at t = 0 the
sink rate ramps linearly from 0 to the recognition-window end sink over
the recognition delay, then from that value to the steady autorotative
sink over the establishment time; a demonstration whose height runs out in
either phase touches down during establishment; otherwise the flare begins
at the declared minimum flare altitude (or at the height available when it
is below that) and bleeds the sink to the touchdown value at the measured
flare deceleration. All values below are REAL outputs of the prep anchor
/tmp/w43spec/anchor_hvtest.py (stdlib math, exit 0), which replicates the
module functions above exactly, reduces the full record and prints the
results; recapture them by running python3 /tmp/w43spec/anchor_hvtest.py.

- Module constants: SAFE_TOUCHDOWN_FPM 600.0, REACTION_ALLOWANCE_S 1.0.
- Per-speed measured demonstration parameters and the model-truth required
  height (recognition loss + establishment loss + declared minimum flare
  altitude, the generator-side boundary the reduction recovers):
  speed 0 KTAS: tau_r 0.6 s, recognition-window end sink 6.0 ft/s, steady
  sink 33.0 ft/s, establishment time 2.2 s, minimum flare altitude 28.0 ft,
  required height 72.7 ft;
  speed 10 KTAS: tau_r 0.7 s, steady sink 33.0 ft/s, establishment time
  2.4 s, minimum flare altitude 33.0 ft, required height 81.9 ft;
  speed 20 KTAS: tau_r 0.8 s, steady sink 32.0 ft/s, establishment time
  2.4 s, minimum flare altitude 31.0 ft, required height 79.0 ft;
  speed 30 KTAS: tau_r 0.9 s, steady sink 30.0 ft/s, establishment time
  2.1 s, minimum flare altitude 22.0 ft, required height 62.5 ft;
  speed 40 KTAS: tau_r 1.0 s, steady sink 28.0 ft/s, establishment time
  1.7 s, minimum flare altitude 14.0 ft, required height 45.9 ft.
- Hover column (0 KTAS) reduction over the sweep (recognition delay 0.60 s
  on every run; recognition window consumes 1.8 ft; establishment consumes
  42.9 ft):
  from 20 ft: contact at 1.901 s during establishment, touchdown 1318.3
  fpm, FAIL; 30 ft: contact 2.310 s, 1619.1 fpm, FAIL; 40 ft: contact
  2.654 s, 1872.2 fpm, FAIL; 50 ft: flare at 5.3 ft, contact 2.968 s,
  1801.8 fpm, FAIL; 60 ft: flare at 15.3 ft, contact 3.342 s, 1405.3 fpm,
  FAIL; 70 ft: flare at 25.3 ft, contact 3.877 s, 838.6 fpm, FAIL; 80 ft:
  flare at 30.1 ft, contact 4.542 s, 300.0 fpm, PASS; 90 ft: flare at
  30.1 ft, contact 4.845 s, 300.0 fpm, PASS; 100 ft: contact 5.148 s,
  PASS; 120 ft: contact 5.754 s, PASS; 150 ft: contact 6.664 s, PASS;
  200 ft: contact 8.179 s, PASS. The lowest passing height is 80 ft, the
  highest failing 70 ft at 838.6 fpm.
- Sampled baro/radar altitude trace of the passing 80 ft hover demo at
  0.5 s spacing (ft AGL): t 0.00 s h 80.0; 0.50 s 78.8; 1.00 s 74.8;
  1.50 s 67.8; 2.00 s 57.8; 2.50 s 44.6; 3.00 s 28.7; 3.50 s 14.8;
  4.00 s 5.3; 4.50 s 0.2; touchdown 4.54 s h 0.0. Reduced marks:
  recognition_delay 0.60 s, time_to_establish_autorotation 2.36 s (the
  flare mark sits 0.16 s after establishment, past the brief unreduced
  steady segment), total time failure to touchdown 4.542 s, flare duration
  1.585 s; 0.60 + 2.36 + 1.585 = 4.542 s, the time identity.
- Per-speed boundary reduction from the bracketing pairs (highest FAIL
  height and sink, lowest PASS height and sink, reduced boundary, boundary
  with the 1.0 s reaction allowance at the 6.0 ft/s recognition-window end
  sink):
  0 KTAS: 70.0 ft at 838.6 fpm, 80.0 ft at 300.0 fpm, boundary 74.430 ft,
  with allowance 80.430 ft;
  10 KTAS: 80.0 ft at 751.7 fpm, 90.0 ft at 300.0 fpm, boundary 83.358 ft,
  with allowance 89.358 ft;
  20 KTAS: 70.0 ft at 1151.4 fpm, 80.0 ft at 502.7 fpm, boundary 78.500 ft,
  with allowance 84.500 ft;
  30 KTAS: 60.0 ft at 829.0 fpm, 70.0 ft at 300.0 fpm, boundary 64.329 ft,
  with allowance 70.329 ft;
  40 KTAS: 40.0 ft at 1182.3 fpm, 50.0 ft at 300.0 fpm, boundary 46.600 ft,
  with allowance 52.600 ft.
  The reduced dead-man-curve boundary rises from 74.430 ft at hover to the
  knee at 83.358 ft near 10 KTAS and then falls to 46.600 ft at 40 KTAS as
  recoverable translational energy grows; the reduced values sit within
  about 2 ft of the generator-side required heights (74.430 versus 72.7 at
  hover) because the 10 ft sweep spacing brackets the verdict flip.
- Boundary identity on the marginal passing demonstration of each speed
  (height lost before the flare + flare recovery altitude == starting
  height, residual 0.00e+00 at every speed):
  0 KTAS, pass at 80 ft: height lost to flare 49.877 ft, recovery altitude
  30.123 ft, sum 80.0 ft;
  10 KTAS, pass at 90 ft: 54.497 + 35.503 = 90.0 ft;
  20 KTAS, pass at 80 ft: 48.000 + 32.000 = 80.0 ft;
  30 KTAS, pass at 70 ft: 45.938 + 24.062 = 70.0 ft;
  40 KTAS, pass at 50 ft: 34.465 + 15.535 = 50.0 ft.
- Measured avoid-region map over the 12-height by 5-speed grid: 60 cells,
  27 AVOID, 33 SAFE; per speed 6 AVOID cells below the 74.4 ft boundary at
  0 KTAS, 7 AVOID cells below 83.4 ft at 10 KTAS, 6 AVOID cells below
  78.5 ft at 20 KTAS, 5 AVOID cells below 64.3 ft at 30 KTAS, and
  3 AVOID cells below the 46.6 ft boundary at 40 KTAS: the avoid region
  tops out near the 10 KTAS knee and shrinks as speed adds recoverable
  energy.
- Clearance against the predicted height-velocity diagram (input table
  built from the flight-mechanics autorotative-descent sink model: the
  recognition loss at the full steady sink over the measured delay, the
  entry loss, and the flare arresting the steady sink to the limit sink at
  a declared 0.45 g mean deceleration, 96.855, 104.055, 103.110, 92.428
  and 80.522 ft across the speeds), judged against the measured boundary
  with the reaction allowance:
  0 KTAS: predicted 96.855 ft, measured with allowance 80.430 ft, margin
  16.424 ft, PASS;
  10 KTAS: 104.055 versus 89.358 ft, margin 14.697 ft, PASS;
  20 KTAS: 103.110 versus 84.500 ft, margin 18.610 ft, PASS;
  30 KTAS: 92.428 versus 70.329 ft, margin 22.098 ft, PASS;
  40 KTAS: 80.522 versus 52.600 ft, margin 27.922 ft, PASS.
  The measured avoid region clears the predicted diagram at every speed:
  the demonstration data show a tighter dead-man-curve region than the
  conservative analytic prediction.
- ValueError checks: 26 offending-input cases across the nine functions,
  every one raising ValueError (module function and offending input listed
  in the anchor output).
- Determinism: repeated reduction and map calls return identical results,
  exit 0.
Run your module and take the real outputs as assert targets; the values
above are the actual prep outputs of /tmp/w43spec/anchor_hvtest.py
(stdlib math, deterministic, exit 0).

## Validation list (contract test must include)

- recognition_delay(0.6, 0.0) = 0.6 within 1e-9; identity at any valid
  pair; ValueErrors at t_failure -1.0, t_reaction 0.6 with t_failure 0.6
  (zero delay) and 0.6/0.6 reversed.
- recognition_loss_with_allowance(1.8, 6.0) = 7.8 within 1e-9 (default
  1.0 s allowance); with allowance_s 0.0 equals 1.8; ValueErrors at
  negative measured loss, negative sink, negative allowance.
- time_to_establish_autorotation on the marginal hover pass mark
  (t_flare 2.957, t_reaction 0.6) = 2.357 within 1e-9; ValueErrors at
  t_flare == t_reaction and negative reaction time.
- height_lost_to_flare(80.0, 30.123) = 49.877 within 1e-9; identity
  h_start - h_flare at any valid pair; ValueErrors at h_start 0.0,
  h_flare 0.0 and h_flare above h_start.
- flare_recovery_altitude(30.123, 0.0) = 30.123 within 1e-9; ValueErrors
  at h_flare 0.0, h_contact equal to h_flare and negative h_contact.
- touchdown_verdict: 300.0 and exactly 600.0 PASS, 600.1 FAIL; ValueErrors
  at negative sink and zero limit.
- interpolate_boundary_height(70.0, 80.0, 838.6, 300.0) = 74.430 within
  0.01; strictly inside the bracket; recognition_loss_with_allowance on
  the result adds 6.0 ft (74.430 + 6.0 = 80.430 within 1e-9); ValueErrors
  at equal bracket heights, failing sink at or under the limit, passing
  sink above the limit, equal sink rates, non-positive heights or limit.
- Hover column: the reduction reproduces the verdict flip between 70 ft
  (FAIL, 838.6 fpm) and 80 ft (PASS, 300.0 fpm); every sweep verdict and
  touchdown sink of the printed column within tolerance (sinks within
  0.05 fpm of the quoted values, heights exact).
- Marginal-pass identity per speed: height_lost_to_flare(h0, h_flare) +
  flare_recovery_altitude(h_flare) == h0 within 1e-9 (anchor residual
  0.00e+00); the time identity holds: recognition_delay + establishment
  time + flare duration == failure-to-touchdown time within 1e-9.
- Boundary ordering: 74.430 (0 KTAS) < 83.358 (10 KTAS) > 78.500 (20
  KTAS) > 64.329 (30 KTAS) > 46.600 (40 KTAS), the dead-man-curve knee
  near 10 KTAS; boundaries with allowance are each exactly 6.0 ft higher.
- build_avoid_map on the worked grid: 60 cells, 27 AVOID, 33 SAFE, cell
  counts per speed 6, 7, 6, 5, 3; region AVOID exactly when the height is
  strictly below the reduced boundary at that speed; ValueErrors at empty
  grids, boundary table length mismatch, non-positive grid height and
  negative boundary.
- clearance_verdict per speed: margins 16.424, 14.697, 18.610, 22.098,
  27.922 ft within 1e-3, verdict PASS at every speed, and PASS inclusive
  when predicted equals measured (margin 0.0); ValueError at negative
  heights.
- ValueErrors across the module (the 26 anchor cases); determinism across
  repeated calls; no randomness; no imports beyond math.

## Corpus fragment (eval/hit1-wave43-rotorcraft-height-velocity-diagram-test.yaml)

Query 1 (copy verbatim):
  "reduce the rotorcraft height-velocity demonstration flight test from the
  hover and low-speed engine-failure runs: measure the height loss and the
  time to establish autorotation and complete the flare from the
  baro/radar altitude traces and interpolate the dead-man-curve boundary
  height where the height loss plus the recovery altitude equals the
  starting height"
  intent: "flight-test-operations; hover and low-speed engine-failure
  demonstration reduction to the measured rotorcraft height-velocity
  boundary"
  expected_skill: "flight-test-operations/performance/
  rotorcraft-height-velocity-diagram-test"
Query 2 (copy verbatim):
  "build the measured avoid-region map over the height and speed grid from
  the hover engine-failure height-loss demonstrations of the
  rotorcraft-height-velocity-diagram-test and judge the clearance of the
  dead-man-curve boundary against the predicted height-velocity diagram"
  intent: "flight-test-operations; measured avoid-region map and clearance
  verdict against the predicted rotorcraft height-velocity diagram"
  expected_skill: "flight-test-operations/performance/
  rotorcraft-height-velocity-diagram-test"
Task ids: w43-rotorcraft-height-velocity-diagram-test-1 and -2. Prep greps
(REAL): no existing hit1-corpus.yaml task carries height-velocity,
dead-man, dead man, hover engine-failure height-loss or avoid-region
tokens, so the queries above are collision-free; in particular the
flight-mechanics phugoid tasks route on phugoid, lanchester and
long-period tokens with no height-velocity content, and the two
windshear-analysis tasks that contain "height loss" do so only as the
energy height loss rate of the F-factor escape decision. The queries never
use the sibling steady-descent tokens (autorotation demonstration,
rotor-rpm, steady autorotative descent, measured sink rate,
pressure-altitude samples) nor the analytic-leaf phrasing (estimate the
descent rate, energy-method, Talbot correlation), and never the phugoid
compound height-velocity-exchange.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce a rotorcraft
height-velocity (dead-man-curve) demonstration flight test:" and include
the outputs in the Claim. First tag: rotorcraft-height-velocity-diagram-
test. Additional tags ONLY: dead-man-curve-boundary,
hover-engine-failure-height-loss, height-velocity-boundary-interpolation,
avoid-region-map. NEVER single generic words (rotorcraft, helicopter,
height, velocity, hover, speed, altitude, flare, boundary, demonstration,
test, flight, verdict, map, diagram, descent) and NEVER height-velocity-
exchange, which phugoid-mode-analysis owns (its airspeed-to-height energy
exchange of the long-period mode is a different compound and a different
function). 50-150 words, <=1000 chars, no em dash, no content-policy
sweep term (the banned word from the builder kit), action
verb present. Recommended wording (outputs in Claim order): "Use when you
must reduce a rotorcraft height-velocity (dead-man-curve) demonstration
flight test from the hover and low-speed engine-failure runs: measure the
engine-failure recognition delay and the height loss and time to establish
autorotation and complete the flare or landing from the baro/radar
altitude traces, apply the reaction time allowance, interpolate the
dead-man-curve boundary height where the measured height loss plus the
recovery altitude equals the starting height at each speed, build the
measured avoid-region map over the height and speed grid, and compare the
boundary against the predicted height-velocity diagram for the clearance
verdict. Produces the recognition delay, the establishment and recovery
times, the height-loss split with the flare and recovery altitudes, the
reduced boundary heights with and without the reaction allowance, the
avoid-region map and the per-speed clearance margins and verdicts that
gate the height-velocity demonstration. Trigger: rotorcraft-height-
velocity-diagram-test, dead-man-curve boundary, hover engine-failure
height-loss, height-velocity demonstration reduction."

FORBIDDEN TOKENS (belong to siblings): steady-descent sink-rate regression,
rotor-rpm-band, measured-sink-rate, autorotation-demonstration-reduction,
flare-altitude-loss, re-established level flight (rotorcraft-autorotation-
flight-test, the steady-descent demonstration, fenced by regime and by the
engine-failure-at-hover framing); energy-method, talbot-correlation,
power-to-weight-ratio, rotor-energy-balance, minimum-descent-rate,
descent-rate-estimate, and any re-derivation of the steady sink (flight-
mechanics/performance/rotorcraft-autorotative-descent, whose sink values
and predicted diagram are quoted inputs only); vertical rate of climb,
hover ceiling, climb induced velocity (rotorcraft-vertical-climb-
performance); shaft-power, torque-to-power, measured-figure-of-merit,
hover-power-required, hover-ceiling-determination
(rotorcraft-performance-flight-test); level-flight-polar
(rotorcraft-forward-flight-performance-test); vortex-ring, windmill-state
(rotorcraft-axial-descent-flow-states); height-velocity-exchange, phugoid,
lanchester-approximation, long-period-mode, airspeed-oscillation
(phugoid-mode-analysis); energy height loss rate, windshear F-factor
(windshear-analysis). The word "autorotation" appears here only as the
establishment phase of a hover or low-speed engine-failure recovery, never
as the steady-descent demonstration; the reduced quantity is the height-
velocity boundary, not a sink rate, and the diagrams and maps are
measured-data products of this leaf alone.

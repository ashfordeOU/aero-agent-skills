# Wave-28 leaf spec: cruise-performance-flight-test (flight-test-operations, performance pack)

- Path: skills/flight-test-operations/performance/cruise-performance-flight-test/
- Pack: performance (existing siblings: takeoff-distance-determination,
  landing-distance-determination, accelerate-stop-distance,
  climb-performance-flight-test, level-acceleration-test,
  engine-flight-test, glide-flight-test, stall-speed-determination)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: flight-test-operations

## Claim

Plan and reduce a cruise performance flight test that measures fuel
flow versus Mach number at constant altitude to build the flight-test
range-performance curve: schedule the level cruise test points across a
Mach sweep with stabilized fuel-flow runs, correct each measured fuel
flow from the test weight to the reference weight with the square-root
fuel-flow correction, convert the corrected fuel flow and the Mach
number into the range performance in meters per kilogram of fuel, fit a
quadratic curve to the range-performance points over Mach, and read off
the maximum-range cruise Mach and the long-range cruise speed (the
faster Mach at which range performance falls to 99 percent of its
maximum). Produces the corrected fuel-flow table, the fitted curve, the
maximum-range cruise Mach, the long-range cruise Mach, and verdicts
that gate the cruise fuel-economy flight test assessment.

Does NOT do: compute cruise range or fuel burn analytically from the
Breguet equation (flight-mechanics breguet-range owns the range
equation); compute range performance from the drag polar and thrust
specific fuel consumption alone (flight-mechanics specific-range owns
the analytic calculation); select ECON cruise speed from cost index or
step climbs (avionics flight-management performance-computation);
determine installed thrust from climbs or accelerations
(engine-flight-test); reduce an accelerated level-flight run
(level-acceleration-test). This leaf reduces MEASURED fuel-flow runs
from a dedicated cruise test and applies the weight correction.

## Model (implement exactly)

Module constants:
- GAMMA = 1.4, R_GAS = 287.05, G0 = 9.80665.
- LRC_FRACTION = 0.99 (long-range cruise = 99 percent of maximum range
  performance).
- W_REF default 200000.0 kg (reference weight input with default).

Functions:
- isa_speed_of_sound(altitude_m) -> float:
  T = 288.15 - 0.0065*altitude_m below 11000 m else 216.65;
  return sqrt(GAMMA*R_GAS*T). ValueError on altitude_m < 0.
- tas_from_mach(mach, altitude_m) -> float: mach * isa_speed_of_sound.
- weight_correction_factor(w_test, w_ref) -> float:
  sqrt(w_ref/w_test). ValueError on w_test <= 0 or w_ref <= 0.
- corrected_fuel_flow(wf_measured, w_test, w_ref) -> float:
  wf_measured * weight_correction_factor(w_test, w_ref).
  ValueError on wf_measured < 0.
- range_performance(tas_m_s, wf_corrected) -> float: tas/wf_corrected
  (m per kg). ValueError on wf_corrected <= 0.
- reduce_cruise_test(points, w_ref) -> dict: points is a list of dicts
  {mach, altitude_m, w_test_kg, wf_measured_kg_s}. For each point
  compute tas, wf_corr, range_performance. Fit quadratic
  rp(M) = c2*M^2 + c1*M + c0 to the (mach, range_performance) pairs
  with ordinary least squares (normal equations, 3x3 solve with the
  local Gaussian-elimination helper from a 20-line linear solver inside
  this module - do not import matrix-operations). Return dict with
  points table entries {mach, tas, wf_corr, rp}, the coefficients, the
  fitted rp at each point, max_rp_mach = -c1/(2*c2) (only if c2 < 0;
  else None), max_rp value, lrc_mach (larger root of
  c2 M^2 + c1 M + c0 = LRC_FRACTION*max_rp via the quadratic formula;
  None if no real roots or c2 >= 0), and the residuals (fitted - data).
  ValueError on fewer than 3 points, duplicate Mach, mach outside
  (0.3, 1.0), or wf_measured <= 0 anywhere.
- lrc_99(mach_max_rp) -> float: None (informational helper kept out;
  the LRC root lives in reduce_cruise_test).
- plan_test_matrix(mach_list, altitude_m, w_start_kg, w_end_kg,
  run_minutes) -> list of dicts: one entry per Mach with a linear
  weight decay across the sweep (each run burns fuel; assign each run a
  w_test_kg on the linear ramp from w_start at the first Mach to w_end
  at the last). Used to build the test card; the fixture in the tests
  uses explicit weights instead.
- verify_speed_ordering(mach_max_rp, mach_lrc) -> str:
  "lrc-faster" when mach_lrc > mach_max_rp else "lrc-not-faster"
  (engineering check: long-range cruise is the faster 99-percent point).

ValueError on: w_ref <= 0, any w_test <= 0, any wf_measured <= 0,
fewer than 3 points.

## Worked example

Reference: W_ref = 200000 kg; altitude 10668 m
(a = 296.51 m/s). Measured runs across 7 Mach values with test weights
ramping down from 209000 kg (M = 0.72) to 197000 kg (M = 0.84).

The measured fuel-flow table is BUILT from an exact quadratic range
performance curve so the reduction recovers it exactly:
rp_model(M) = 90.0 - 6000.0*(M - 0.80)^2  (m per kg, a parabola peaked
at M = 0.80). For each point the fixture sets
wf_corrected = tas / rp_model and then wf_measured =
wf_corrected * sqrt(w_test/W_ref) (the inverse of the leaf correction,
so the reduction returns exactly wf_corrected).

Mach list: [0.72, 0.74, 0.76, 0.78, 0.80, 0.82, 0.84]
W test: [209000, 207000, 205000, 203000, 201000, 199000, 197000] kg.
- At M = 0.80, W = 201000: tas = 0.80*296.51 = 237.21 m/s;
  rp_model = 90.0; wf_corrected = 237.21/90.0 = 2.6357 kg/s;
  correction factor sqrt(201000/200000) = 1.00250;
  wf_measured = 2.6357*1.00250 = 2.6423 kg/s. Assert
  corrected_fuel_flow(2.6423, 201000, 200000) returns 2.6357 within
  1e-3 and range_performance(237.21, 2.6357) returns 90.0 within 1e-6.
- reduce_cruise_test must return max_rp_mach = 0.800000 within 1e-6,
  max_rp = 90.0 within 1e-6, coefficients c2 = -6000.0, c1 = +9600.0,
  c0 = -3750.0 within 1e-3. Derivation: rp = 90 - 6000*(M - 0.8)^2 =
  90 - 6000*(M^2 - 1.6M + 0.64) = -6000 M^2 + 9600 M - 3840 + 90 =
  -6000 M^2 + 9600 M - 3750. Vertex M = -9600/(2*-6000) = 0.8; max rp
  = -6000*0.64 + 9600*0.8 - 3750 = 90.0.
- lrc: solve -6000 M^2 + 9600 M - 3750 = 0.99*90 = 89.1 ->
  -6000 M^2 + 9600 M - 3839.1 = 0 -> M = (9600 - sqrt(9600^2 -
  4*6000*3839.1))/(2*6000) for the lower root and (9600 + sqrt(...))/...
  for the upper root. 9600^2 = 92160000; 4*6000*3839.1 = 92138400;
  discriminant = 21600; sqrt = 146.97; roots (9600 +/- 146.97)/12000 =
  0.78775 and 0.81225. lrc_mach = 0.81225 within 1e-6 (the larger
  root). verify_speed_ordering(0.8, 0.81225) = "lrc-faster".
- residuals are all < 1e-9 (noise-free parabola).
- Sanity case: 5 points that are linear in M (not a parabola with
  negative curvature): c2 near 0 -> max_rp_mach None, verdict
  "no-maximum".
- ValueErrors on 2 points, w_ref 0, wf_measured -1.
Keep at least 18 test methods: isa_speed_of_sound at 0 and 10668 m
(340.29, 296.51 within 0.1), tas conversion, correction factor exact
values, corrected fuel flow, range performance, full reduction on the
fixture (vertex, max, coefficients, lrc, residuals), point-table
entries, verdicts, plan_test_matrix shape, ValueErrors.

## Corpus tasks (ids w28-cruise-performance-flight-test-1/2)

Distinctive tokens: cruise performance flight test, fuel flow versus
Mach, stabilized fuel flow runs, weight corrected fuel flow, maximum
range cruise speed, long range cruise speed, Mach sweep at altitude.
Avoid (sibling claims): specific air range, instantaneous range,
meters per kilogram as a trigger phrase, sector fuel burn
(flight-mechanics specific-range); Breguet range, cruise fuel burn
(breguet-range); cost index, ECON cruise Mach (avionics
performance-computation); excess thrust, specific excess power,
accelerated level flight (level-acceleration-test); thrust
determination, EGT margin (engine-flight-test).

1. "reduce the cruise performance flight test data from the stabilized
   fuel flow runs across the Mach sweep, correct each fuel flow to the
   reference weight, and find the maximum range cruise speed"
2. "plan and analyze the level cruise fuel flow test at altitude: build
   the range performance curve versus Mach and set the long range
   cruise speed at the 99 percent point"

## SKILL body notes

Pair with flight-mechanics specific-range and breguet-range as the
analytic neighbors (flight-test result vs calculation), and with
level-acceleration-test and engine-flight-test as the other performance
flight tests. State the square-root weight correction as a documented
engineering approximation valid for small weight differences at
constant Mach and altitude (induced-drag-dominated regime). FAR/CS-25
referenced for cruise performance context only (no verbatim text).

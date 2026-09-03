# Wave-28 leaf spec: buffet-boundary-testing (flight-test-operations, envelope pack)

- Path: skills/flight-test-operations/envelope/buffet-boundary-testing/
- Pack: envelope (existing siblings: envelope-expansion,
  load-factor-envelope, v-speeds, stall-speed-determination,
  stall-characteristics-testing, high-angle-of-attack-testing,
  spin-testing, icing-flight-test, flight-loads-survey,
  structural-coupling-test)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: flight-test-operations

## Claim

Plan and analyze the flight test that maps the buffet boundary of a
transport airplane: schedule pull-up and steady-turn test points across
a Mach sweep at constant altitude with the load factor increasing until
the buffet-onset accelerometer signature appears, detect buffet onset
from the vertical accelerometer RMS rise above a threshold, convert the
onset load factor to the boundary lift coefficient at each Mach, fit a
linear buffet-boundary line over the tested Mach band, and compute the
buffet margin at a cruise condition against a maneuver-buffet target
load factor. Produces the onset load factor and boundary lift
coefficient per Mach, the fitted boundary line, the buffet margin and
the pass or fail verdict that gate the high-speed buffet clearance
assessment.

Does NOT do: plan or gate natural or accelerated stall entries
(stall-characteristics-testing owns stall behavior and entry
techniques); size expansion steps or compute the corner speed
(envelope-expansion); build the V-n diagram or gust lines
(load-factor-envelope); measure stall warning margins or departure
resistance (high-angle-of-attack-testing); compute flutter margins or
damping (flutter-testing); calibrate strain stations for a loads
survey (flight-loads-survey).

## Model (implement exactly)

Module constants:
- RMS_ONSET_G = 0.02 (buffet-onset RMS threshold in g, documented
  typical).
- RMS_FLOOR_G = 0.004 (RMS below onset, documented typical).
- RMS_RISE_PER_G = 0.4 (RMS rise per g above onset, documented
  typical).
- G0 = 9.80665.

Inputs (dict or kwargs):
- weight_kg (float, test gross weight in kg),
- wing_area_m2 (float, S),
- mach_list (list of floats, test Mach values),
- altitude_m (float),
- rms_table (list of lists: for each Mach, a list of (load_factor,
  rms_g) measured samples sorted by load factor),
- onset_rms_g (float, default RMS_ONSET_G),
- buffet_target_n (float, default 1.3; the maneuver-buffet margin
  target load factor at the cruise condition, an engineering target,
  not a regulation value),
- cruise_mach (float, Mach at which the margin is evaluated).

Functions:
- isa_state(altitude_m) -> dict: {T, P, rho} from the ISA model
  (T = 288.15 - 0.0065*altitude below 11000 m else 216.65; P =
  101325*(T/288.15)^5.25588 below 11000 m else 22632.1*exp(-9.80665*
  (altitude - 11000)/(287.05*216.65)); rho = P/(287.05*T)).
  ValueError on altitude < 0.
- dynamic_pressure(mach, altitude_m) -> float:
  q = 0.5*rho*V^2 with V = mach*sqrt(1.4*287.05*T).
  ValueError on mach outside (0.1, 2.0).
- onset_detect(samples, onset_rms_g) -> float: samples is a list of
  (load_factor, rms_g) sorted by load factor; verify rms is
  non-decreasing with load factor (else ValueError "non-monotonic rms
  table"); find the first sample with rms >= onset_rms_g; if none,
  ValueError "no onset crossing"; linearly interpolate the load factor
  at the crossing between that sample and the previous one and return
  it. ValueError on fewer than 2 samples.
- boundary_lift_coefficient(onset_n, q, weight_kg, wing_area_m2) ->
  float: onset_n * weight_kg * G0 / (q * wing_area_m2).
- fit_boundary_line(mach_list, cl_buf_list) -> dict:
  least-squares linear fit cl_buf = slope*mach + intercept (local 2x2
  normal equations); return {slope, intercept, cl_at_cruise,
  residuals}. ValueError on fewer than 2 points.
- buffet_margin(n_buf_at_cruise, target_n) -> float: n_buf - target_n.
- analyze(inputs) -> dict:
  per-Mach: q, onset_n (from onset_detect), cl_buf; then the fitted
  line, cl_buf at cruise_mach from the line, n_buf_cruise =
  cl_buf_cruise * q_cruise * wing_area_m2 / (weight_kg * G0), margin_n,
  verdict "buffet-margin-pass" when margin_n >= 0.0 else
  "buffet-margin-fail".
ValueError on: weight_kg <= 0, wing_area_m2 <= 0, altitude_m < 0,
cruise_mach outside the fitted Mach range (extrapolation guard),
target_n <= 0, mismatched table lengths.

## Worked example (REVISED fixture - use exactly this)

Test: weight 195000 kg (W = 1912297 N), S = 360.0 m2, altitude
10668 m, Mach list [0.74, 0.76, 0.78, 0.80, 0.82]. Pull-up at each
Mach with load factor samples every 0.1 from 1.0 to 2.2. The measured
rms fixture: rms(n) = 0.004 for n <= n_onset_model(M), else 0.004 +
0.4*(n - n_onset_model(M)), with n_onset_model(M) = 1.90 - 1.50*(M -
0.74). (The fixture is BUILT IN THE TEST FILE from this model, then
passed to the module; the module does not know the model.)

With the 0.02 g onset threshold, the detector crosses at
n_det = n_onset_model + (0.02 - 0.004)/0.4 = n_onset_model + 0.04:
M 0.74 -> 1.94; M 0.76 -> 1.91; M 0.78 -> 1.88; M 0.80 -> 1.85;
M 0.82 -> 1.82.

ISA at 10668 m: T = 218.81 K, P = 23843 Pa, rho = 0.37960 kg/m3,
a = 296.51 m/s (assert within 0.1).
q(M) = 0.5*0.37960*(M*296.51)^2: q(0.74) = 9139.5, q(0.76) = 9638.7,
q(0.78) = 10150.6, q(0.80) = 10675.1, q(0.82) = 11212.4 (assert each
within 1.0).
cl_buf(M) = onset_n * 1912297 / (q * 360.0):
M 0.74: 1.94*1912297/(9139.5*360) = 3709856/3290220 = 1.1276
M 0.76: 1.91*1912297/3469932 = 3652487/3469932 = 1.0526
M 0.78: 1.88*1912297/3654216 = 3595118/3654216 = 0.9838
M 0.80: 1.85*1912297/3843036 = 3537749/3843036 = 0.9206
M 0.82: 1.82*1912297/4036464 = 3480380/4036464 = 0.8622
(assert each within 0.01 of the module value and the module value
within 0.01 of these).
fit_boundary_line: assert slope is negative (about -3.3 per Mach,
compute the exact module value) and the line at M = 0.80 equals 0.9206
within 0.01.
n_buf_cruise = cl_line(0.80)*q(0.80)*360/1912297 = 0.9206*3843036/
1912297 = 1.8500 (assert within 0.01).
buffet_margin(1.85, 1.3) = +0.55 (assert within 0.02) -> verdict
"buffet-margin-pass". Same data with buffet_target_n = 2.0 -> margin
-0.15 -> "buffet-margin-fail".
ValueErrors on: empty or 1-sample rms row, no crossing (all rms below
threshold), non-monotonic rms, cruise_mach = 0.70 (outside fitted
range), weight_kg 0.

Keep at least 18 test methods: isa_state values at 0 and 10668 m
(288.15/101325/1.225 and 218.81/23843/0.3796), dynamic pressure at two
Mach values, onset_detect interpolation exact value (1.94 at M 0.74),
no-crossing error, non-monotonic error, cl_buf values, fit slope sign
and cruise value, margin pass and fail, verdict strings,
extrapolation guard, ValueErrors.

## Corpus tasks (ids w28-buffet-boundary-testing-1/2)

Distinctive tokens: buffet boundary flight test, buffet onset, high
speed buffet, maneuver buffet, accelerometer RMS rise, pull-up sweep,
buffet margin. Avoid: stall entry technique, natural stall, accelerated
stall (stall-characteristics-testing); corner speed, expansion steps
(envelope-expansion); gust line, V-n diagram (load-factor-envelope);
flutter damping (flutter-testing); stall warning margin
(high-angle-of-attack-testing).

1. "map the buffet boundary from the flight test pull-up sweeps:
   detect buffet onset from the accelerometer RMS rise at each Mach and
   fit the boundary lift coefficient line"
2. "check the high speed buffet margin at the cruise Mach: convert the
   measured onset load factors to the buffet boundary and score the
   margin against the maneuver buffet target"

## SKILL body notes

Pair with load-factor-envelope (V-n context), envelope-expansion
(expansion context) and flutter-testing (other clearance boundary).
RMS floor/rise and the 0.02 g onset threshold are documented typical
engineering criteria, not regulation values; the SKILL body must say
so. FAR/CS-25 referenced for buffet and vibration context by name and
paraphrase only (no verbatim text).

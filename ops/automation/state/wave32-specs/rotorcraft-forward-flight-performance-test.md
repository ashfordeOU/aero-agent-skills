# Wave-32 leaf spec: rotorcraft-forward-flight-performance-test (flight-test-operations, performance pack)

- Path: skills/flight-test-operations/performance/rotorcraft-forward-flight-performance-test/
- Pack: performance. FTO siblings: rotorcraft-performance-flight-test
  (wave-31, hover + vertical-climb measured reduction), cruise-
  performance-flight-test (fixed-wing fuel-flow reduction),
  level-acceleration-test (fixed-wing Ps), climb-performance-flight-test.
- Standards id: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-test-operations

## Claim

Reduce a rotorcraft level-flight (forward flight) performance flight
test from measured data: convert measured main-rotor torque and rotor
speed samples into shaft power across a level-flight speed sweep,
correct the measured power-required polar to a reference weight and
standard-day density altitude with the induced and profile power split,
fit the corrected power-required curve, read off the best-endurance
speed at the minimum-power point, the best-range speed at the tangent
from the origin, and the maximum level-flight speed Vh against the
maximum continuous available power. Produces the measured torque-to-
shaft-power values, the corrected polar, the fitted curve coefficients,
the best-endurance speed, the best-range speed and the Vh verdict that
gate a rotorcraft level-flight performance assessment.

Does NOT do: predicting the rotorcraft forward-flight power-required
curve from momentum theory (flight-mechanics/performance/
rotorcraft-forward-flight-performance owns the Glauert-inflow predicted
induced power, parasite power from equivalent flat-plate drag, profile
power from solidity and tip speed - the ANALYSIS leaf; this leaf reduces
MEASURED torque data, the same FM-analysis/FTO-reduction pairing that
exists for hover); hover or vertical-climb measured reduction
(rotorcraft-performance-flight-test owns the hover torque-to-power,
measured figure of merit, hover-ceiling reduction); fixed-wing cruise
fuel-flow reduction (cruise-performance-flight-test); rotor blade
dynamics, flapping or vibration (not a performance-reduction topic).

## Model (implement exactly)

Constants:
- RHO_STD = 1.225 (kg/m3), G0 = 9.80665 (m/s2).
- MIN_SPEED_SWEEP = 4 (points), MAX_SPEED_SWEEP = 40.
- FIT_ORDER = 2 (quadratic polar fit).
- RANGE_TANGENT_EPS = 1e-9 (guard for the tangent condition).

Functions (pure stdlib, deterministic):

- shaft_power(torque_Nm, omega_rad_s) -> P = torque * omega. ValueError
  if torque < 0 or omega <= 0.
- density_correct_power(power_W, rho_test) -> P_std = power_W *
  RHO_STD / rho_test. ValueError if power_W < 0 or rho_test <= 0.
- weight_correct_power(power_W, weight_test_N, weight_ref_N,
  induced_fraction) -> P_ref = power_W * (induced_fraction *
  (weight_ref/weight_test)**(3/2) + (1 - induced_fraction) *
  (weight_ref/weight_test)).  The induced share scales with
  (W_ref/W_test)^1.5 (induced velocity ~ sqrt(W), power ~ W*v_i ~
  W^1.5); the profile/parasite share scales linearly with weight
  (drag ~ weight at the same speed).  ValueErrors on non-positive
  weights, induced_fraction outside [0,1], power_W < 0.
- correct_to_reference(power_W, weight_test_N, weight_ref_N,
  induced_fraction, rho_test) -> density then weight correction chain.
- fit_power_polar(speeds_ms, powers_W) -> (a, b, c) quadratic least
  squares fit P(V) = a*V^2 + b*V + c, solved by normal equations over
  the declared arrays (stdlib only; return floats). ValueError if the
  arrays differ in length, fewer than MIN_SPEED_SWEEP points, any
  speed <= 0 or power < 0, or the fit is degenerate (a <= 0 with
  powers not constant).
- best_endurance_speed(a, b) -> V_ben = -b / (2*a) when a > 0; when
  a == 0 (flat polar), return None (no interior minimum). ValueError
  if a < 0.
- best_range_speed(a, c) -> V_br = sqrt(c / a) from the tangent
  condition dP/dV = P/V -> a*V^2 = c. ValueError if a <= 0 or c < 0.
  None when c == 0.
- max_level_speed(a, b, c, p_avail_W) -> largest real root of a*V^2 +
  b*V + c = P_avail. Discriminant D = b^2 - 4*a*(c - P_avail);
  ValueError if a <= 0; return None when D < 0 (available power below
  the minimum of the polar -> no level flight); else Vh = (-b +
  sqrt(D)) / (2*a).  (The + root is the high-speed intersection; the
  - root is the low-speed/min-power intersection.)
- validate_speed_order(v_ben, v_br, vh) -> dict {ben_lt_br: bool,
  br_lt_vh_or_none: bool, order_ok: bool}: order_ok True when (v_ben
  is None or v_br is None or v_ben < v_br) and (vh is None or v_br is
  None or v_br < vh).  Speed ordering check only, does not police
  physics magnitudes.
- reduce_level_flight_sweep(torques_Nm, omegas_rad_s, speeds_ms,
  rho_test, weight_test_N, weight_ref_N, induced_fraction,
  p_avail_max_continuous_W=None) -> dict:
  {shaft_powers_W, corrected_powers_W, fit (a,b,c),
  best_endurance_speed_ms, best_range_speed_ms,
  max_level_speed_ms (None when p_avail is None or D < 0),
  speed_order (dict), point_count}.  All ValueErrors propagate.
  When p_avail_max_continuous_W is None, max_level_speed_ms is None.
  The leaf does NOT extrapolate beyond the highest measured speed for
  Vh: if the computed Vh exceeds the top of the measured band, still
  return the computed Vh but set a flag vh_beyond_measured: True so
  the report marks it an extrapolation.

## Worked example

Measured level-flight sweep of a light single-rotor helicopter at
standard day (rho = 1.225 kg/m3) at the reference weight (21 000 N), so
the density and weight corrections are identity in the main example and
the raw shaft powers carry the example.  Hover torque 12.222 kN*m at
27.0 rad/s (shaft power 330.0 kW), then torque samples across the speed
sweep V = [0, 12, 24, 36, 48, 60, 72] m/s giving shaft powers about
[330.0, 271.4, 251.8, 259.4, 304.2, 376.0, 487.0] kW at omega =
27.0 rad/s (torque per point = power/27.0).  Pass powers to the fit in
WATTS (multiply the kW values by 1000).

Run your module and take the real outputs as assert targets, then check
magnitude bounds:
- shaft powers about [330000, 271400, 251800, 259400, 304200, 376000,
  487000] W (each within +-2000 W of the listed value).
- corrected powers equal the shaft powers in this example (identity
  corrections at standard day and reference weight).
- fit coefficients in W/(m/s)^2, W/(m/s), W: a in 100-130 (about
  114.0), b in -7000 to -5000 (about -6030), c in 320000-340000
  (about 329300).
- best_endurance_speed in 23-30 m/s (about 26.4); polar minimum power
  about 250 kW.
- best_range_speed in 48-58 m/s (about 53.7), > best_endurance, and
  inside the measured band.
- with p_avail_max_continuous = 470000 W: max_level_speed in 66-74 m/s
  (about 70.4, 137 kt), inside the band (max measured 72), and the
  speed_order.order_ok True with vh/v_br ratio about 1.31.
- Scale invariance check (validation-level property): multiplying every
  measured power by a constant factor leaves best_endurance_speed and
  best_range_speed unchanged (the fit coefficients scale, their ratio
  does not).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: negative torque, omega <= 0, rho_test <= 0, power_W < 0,
  weight <= 0, induced_fraction outside [0,1], fewer than 4 points,
  length mismatch, speed <= 0, degenerate fit (a < 0).
- shaft_power(12222, 27) about 330 000 W.
- density correction: density_correct_power(330000, 1.225) returns
  330000 (identity at standard day); at rho_test = 1.10 returns
  330000 * 1.225/1.10 about 367 500 W.
- weight correction identity: at weight_ref == weight_test the
  correction returns the input power unchanged.
- induced fraction edge: induced_fraction 0 (all profile/parasite)
  scales linearly; 1.0 scales with the 1.5 power.
- best_endurance_speed at the vertex equals -b/(2a); best_range_speed
  satisfies a*V^2 = c; verify against the quadratic by evaluating
  P(V_br)/V_br and dP/dV(V_br) equality to tolerance 1e-6 (tangent
  condition).
- max_level_speed: at P_avail equal to the polar minimum, the
  discriminant is ~0 and Vh equals the vertex speed (single root);
  below the minimum returns None.
- vh_beyond_measured flag True when computed Vh > max measured speed.
- Scale invariance: multiplying every measured power by 2.0 leaves
  best_endurance_speed and best_range_speed unchanged to 1e-9.
- Determinism: no RNG, run-to-run identical floats.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-rotorcraft-forward-flight-performance-test.yaml)

Query 1 (copy verbatim):
  "reduce measured rotor torque and rotor speed samples from a helicopter level-flight speed sweep into shaft power and a corrected power-required polar for the flight test report"
  intent: "flight-test-operations; rotorcraft level-flight measured torque-to-shaft-power reduction"
  expected_skill: "flight-test-operations/performance/rotorcraft-forward-flight-performance-test"
Query 2 (copy verbatim):
  "determine the best-endurance speed best-range speed and maximum level-flight speed vh of a rotorcraft from the corrected measured power-required curve and the maximum continuous power"
  intent: "flight-test-operations; rotorcraft flight test characteristic speeds from the measured polar"
  expected_skill: "flight-test-operations/performance/rotorcraft-forward-flight-performance-test"
Task ids: w32-rotorcraft-forward-flight-performance-test-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce a rotorcraft level-flight
performance flight test from measured data:" and include the outputs in
the Claim. First tag: rotorcraft-forward-flight-performance-test.
Additional tags ONLY: rotorcraft-forward-flight, level-flight-speed-
sweep, torque-to-shaft-power, power-required-polar, vh-determination,
max-continuous-power. NEVER single generic words (flight, test,
performance, power, rotorcraft, speed). 50-150 words, <=1000 chars, no
em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): momentum theory, Glauert inflow,
induced power from inflow, parasite power from flat-plate drag,
equivalent flat-plate area, predicted polar (flight-mechanics/
performance/rotorcraft-forward-flight-performance owns the ANALYSIS
leaf); measured figure of merit, hover ceiling, vertical climb,
density-altitude hover reduction (rotorcraft-performance-flight-test
owns hover/climb measured reduction); fuel flow, Mach sweep, quadratic
range curve vs Mach (cruise-performance-flight-test); specific excess
power, level acceleration (level-acceleration-test). The word "polar"
is allowed only as "power-required polar" (measured); never claim
"predicted polar" or "momentum theory".

Tags: [rotorcraft-forward-flight-performance-test,
rotorcraft-forward-flight, level-flight-speed-sweep,
torque-to-shaft-power, power-required-polar, vh-determination,
max-continuous-power]

Sibling-citation lines for Related leaves:
flight-mechanics/performance/rotorcraft-forward-flight-performance (the
analysis sibling, momentum-theory prediction),
flight-test-operations/performance/rotorcraft-performance-flight-test
(hover/climb measured reduction sibling),
flight-test-operations/performance/cruise-performance-flight-test
(fixed-wing fuel-flow reduction), flight-test-operations/performance/
climb-performance-flight-test (weight/density correction conventions).

Ledger Standard: far-29.

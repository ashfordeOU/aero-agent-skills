# Wave-31 leaf spec: rotorcraft-performance-flight-test (flight-test-operations, performance pack)

- Path: skills/flight-test-operations/performance/rotorcraft-performance-flight-test/
- Pack: performance (fixed-wing siblings: accelerate-stop-distance,
  climb-performance-flight-test, cruise-performance-flight-test,
  engine-flight-test, glide-flight-test, landing-distance-determination,
  level-acceleration-test, stall-speed-determination,
  takeoff-distance-determination). Zero leaves in the flight-test-operations
  family mention rotorcraft or helicopter (grep receipt at prep): every FTO
  leaf is fixed-wing or transport-airplane. The wave-30 rotorcraft performance
  leaves in flight-mechanics compute rotor physics models; nothing reduces
  MEASURED rotorcraft flight-test data. This leaf is the flight-test reduction
  counterpart.
- Standards ids: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-test-operations

## Claim

Reduce rotorcraft performance flight-test data: convert measured main rotor
torque and rotor speed into shaft power, compute the measured figure of merit
from the ideal induced power and the measured power, correct measured hover
power to a reference weight and density altitude with the induced and profile
fraction split, correct a measured vertical rate of climb for test weight,
reduce a set of hover power-required points measured across density altitudes
to a hover-ceiling assessment against the available power, and check the test
day against the flight manual limits. Produces the measured power, measured
figure of merit, corrected power, corrected vertical rate of climb, the OGE
and IGE hover ceiling altitudes, and the test verdict that gate a rotorcraft
performance flight-test report.

Does NOT do: compute rotor physics from geometry and weight (flight-mechanics/
performance/rotorcraft-hover-performance and the wave-31 rotorcraft siblings
own the analytic models; this leaf works from MEASURED torque, rotor speed,
weight, and altitude data); fixed-wing climb/cruise/glide reduction
(climb-performance-flight-test etc. own the airplane methods); hover ceiling
computation from a momentum-theory model (this leaf interpolates the measured
power-required points against a supplied available power); engine or
transmission test data beyond the torque-to-power conversion.

## Model (implement exactly)

Module constants:
- G0 = 9.80665 (m/s2).
- PI = math.pi.

Functions (pure stdlib):
- shaft_power_from_torque(torque_nm, omega_rad_s) -> float:
  P = torque * omega. ValueError if torque < 0 or omega <= 0.
- ideal_induced_power(thrust_n, rho, area_m2) -> float:
  P_ideal = thrust * sqrt(thrust / (2 * rho * area)).
  ValueErrors on thrust <= 0, rho <= 0, area <= 0.
- measured_figure_of_merit(thrust_n, rho, area_m2, measured_power_w) ->
  float: FM = P_ideal / P_measured. ValueError if measured_power <= 0 or
  P_ideal < 0; the ratio must be <= 1.0 for a physical measurement (raise
  ValueError if P_ideal > measured_power: the measured power cannot be below
  the ideal induced power).
- power_correction_weight_density(measured_power_w, weight_meas_n,
  weight_ref_n, rho_meas, rho_ref, induced_fraction=0.6) -> float:
  P_corr = P_meas * [ f_i * (W_ref/W_meas)^1.5 * sqrt(rho_meas/rho_ref) +
  (1 - f_i) * (rho_ref/rho_meas) ]. The induced part scales as
  W^1.5 / sqrt(rho) (momentum theory: P_i ~ T sqrt(T/rho)); the profile part
  scales with rho. ValueErrors: measured_power < 0, weight_meas <= 0,
  weight_ref <= 0, rho_meas <= 0, rho_ref <= 0, induced_fraction outside
  [0, 1].
- corrected_vertical_rate_of_climb(roc_meas_m_s, weight_meas_n,
  weight_ref_n) -> float: ROC_corr = ROC_meas * weight_meas / weight_ref
  (excess-power scaling: ROC ~ excess power / weight). ValueError if
  weight_meas <= 0 or weight_ref <= 0; ROC_meas may be negative (a descent
  test point is allowed through).
- hover_ceiling_altitude(power_available_w, altitude_m_list,
  power_required_w_list) -> float: linear interpolation of the measured
  power-required versus altitude points; return the altitude where the
  required power equals the available power. If power_required at the lowest
  altitude already exceeds the available power, return None (hover not
  achieved at the lowest test altitude). If power_required at the highest
  altitude is still below the available power, return None plus a flag in the
  caller (no ceiling within the tested range). ValueErrors: mismatched list
  lengths, fewer than 2 points, any negative altitude or power.
- torque_to_power_check(torque_nm, omega_rad_s, rated_power_w,
  tolerance=0.05) -> dict: {shaft_power_w, within_rated: bool} where
  within_rated is True when shaft power <= rated_power * (1 + tolerance).
  ValueErrors as in shaft_power_from_torque.
- rotorcraft_performance_test_reduction(torque_points_nm, omega_rad_s,
  weight_meas_n, weight_ref_n, rho_meas, rho_ref, area_m2,
  rated_power_w, induced_fraction=0.6) -> dict: convenience chain computing
  the mean measured shaft power, the measured figure of merit at the mean
  torque point (thrust = weight_meas), the weight-density corrected power,
  and the torque check verdict; returns {mean_shaft_power_w,
  measured_figure_of_merit, corrected_power_w, within_rated}.

## Worked example

Main rotor: radius 5.0 m (area 78.54 m2), measured torque 14 815 Nm at
27 rad/s, test weight 22 500 N, reference weight 21 574.63 N,
rho_meas = 1.10, rho_ref = 1.225, induced fraction 0.6.

Deterministic anchors (run your module, take the printed values as the assert
targets, then CHECK the magnitude bounds):
- shaft power in 380 000-420 000 W (about 400 005: 14 815 * 27).
- ideal induced power at test weight and rho_meas in 210 000-240 000 W.
- measured figure of merit in 0.52-0.62 (about 0.57).
- corrected power (f_i = 0.6) in 370 000-410 000 W (about 391 700, within 3%
  of the measured value; the measurement is near the reference condition).
- corrected vertical rate of climb for a measured 8.0 m/s at 22 500 N to the
  21 574.63 N reference in 7.5-8.5 m/s (about 8.34).
- torque check against 450 000 W rated with 5% tolerance: within_rated True.
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: torque < 0, omega <= 0, thrust <= 0, rho <= 0, area <= 0,
  measured_power <= 0, measured_power < ideal power (measured FM > 1),
  weight <= 0, induced_fraction outside [0, 1], mismatched ceiling lists,
  fewer than 2 ceiling points, negative altitude.
- power_correction returns measured power unchanged when weight and density
  are at the reference (W_ref = W_meas, rho_ref = rho_meas).
- corrected ROC scales linearly with the weight ratio.
- hover_ceiling_altitude returns None when the required power at the lowest
  altitude exceeds the available power.
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-rotorcraft-performance-flight-test.yaml)

Query 1 (copy verbatim):
  "reduce a rotorcraft-hover-flight-test: measured figure of merit from torque and rotor speed, corrected to reference weight and density altitude"
  intent: "flight-test-operations; rotorcraft hover performance flight test reduction"
  expected_skill: "flight-test-operations/performance/rotorcraft-performance-flight-test"
Query 2 (copy verbatim):
  "determine the hover ceiling from measured rotorcraft power required points across density altitudes against the available power in a rotorcraft-performance-flight-test report"
  intent: "flight-test-operations; rotorcraft hover ceiling from flight test power data"
  expected_skill: "flight-test-operations/performance/rotorcraft-performance-flight-test"
Task ids: w31-rotorcraft-performance-flight-test-1 and -2.

Forbidden tokens that belong to siblings: do NOT use fixed-wing rate of climb
from pressure altitude, cruise Mach sweep, accelerate stop, stall speed,
glide sink rate, takeoff ground roll (those belong to the fixed-wing FTO
performance leaves), and do NOT claim the momentum-theory computation of hover
power from geometry (flight-mechanics rotorcraft leaves own the model). Use
measured-data framing only.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce a rotorcraft performance
flight test from measured data:" and include the outputs listed in the Claim.
First tag: rotorcraft-performance-flight-test. Additional tags only:
rotorcraft-hover-flight-test, measured-figure-of-merit, torque-to-power,
hover-ceiling-determination, weight-density-correction. NEVER single generic
words (flight, test, performance, torque, power, helicopter). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

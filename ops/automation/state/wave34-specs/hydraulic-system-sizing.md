# Wave-34 leaf spec: hydraulic-system-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/hydraulic-system-sizing/
- Pack: sizing. Closest siblings: control-surface-sizing and
  spoiler-sizing (output surface geometry and the aero HINGE MOMENT ON
  the actuator, the demand side, and stop there), landing-gear-sizing
  (strut loads, shock absorber stroke), ice-protection-sizing,
  battery-sizing, brake-energy-sizing (other aircraft-subsystem leaves),
  environmental-control-sizing (cabin conditioning; the two subsystem
  leaves are disjoint). Whole-tree grep proves ZERO owners for actuator
  piston-area flow, pump flow/power, accumulator and reservoir sizing;
  the only repo hits for hydraulic pumps are rocket turbopump
  (propulsion/rocket) and incidental leak-testing context.
- Standards id: far-25 (reference-only). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the aircraft hydraulic power system from flight-control and
utility actuation demand: actuator flow from piston area and rod speed,
pump flow from the worst-case simultaneous demand group plus leakage,
pump power from system pressure and flow over efficiency, the emergency
accumulator gas volume from the adiabatic gas law between charged and
depleted pressures given the usable volume, and the reservoir volume
from leakage make-up over a hold time with margin. Produces the per-
actuator flow, the simultaneous demand, pump flow and power, the
accumulator charged/depleted volumes with the p V^n closure, and the
reservoir volume.

Does NOT do: surface geometry and hinge moment on the actuator
(control-surface-sizing, spoiler-sizing own the demand side); landing
gear strut loads (landing-gear-sizing); anti-icing bleed (ice-
protection-sizing); rocket turbopumps (propulsion/rocket/
rocket-turbopump); pressure vessel wall stress of the accumulator shell
(structures).

## Model (implement exactly)

Module constants:
- LPM_PER_M3S = 60000.0 (m3/s to L/min).
- PSI_PA = 6894.757 (Pa per psi).
- GAS_ADIABATIC_DEFAULT = 1.4.
- DEFAULT_LEAKAGE_LPM = 15.0.
- DEFAULT_RESERVOIR_HOLD_MIN = 2.0 (minutes of leakage make-up).
- DEFAULT_RESERVOIR_MARGIN = 1.2.

Conventions: pressure inputs may be given in psi (function arg
pressure_psi) and are converted internally; all volume outputs in L.
The actuator group is a list of identical-demand actuators with a
simultaneity count.

Functions (pure stdlib):
- actuator_flow(piston_area_m2, rod_speed_m_s) -> dict {flow_m3s,
  flow_lpm} = area * speed. ValueErrors on non-positive inputs.
- simultaneous_demand(actuator_flow_lpm, n_simultaneous) ->
  n * flow_lpm. ValueError on negative count / flow.
- pump_flow(actuator_flow_lpm, n_actuators, n_simultaneous,
  leakage_lpm = DEFAULT_LEAKAGE_LPM) -> dict {simultaneous_lpm,
  pump_flow_lpm, pump_flow_m3s} = simultaneous demand + leakage.
  ValueError on n_simultaneous > n_actuators or negative leakage.
- pump_power(system_pressure_psi, pump_flow_m3s, efficiency) ->
  dict {pressure_pa, pressure_mpa, power_w, power_kw} =
  p_pa * Q / eta. ValueErrors on non-positive inputs; efficiency in
  (0, 1].
- accumulator_volumes(charged_pressure_psi, depleted_pressure_psi,
  usable_volume_l, n_gas = GAS_ADIABATIC_DEFAULT) -> dict
  {charged_gas_volume_l, depleted_gas_volume_l, closure_check} solving
  p1 V1^n = p2 V2^n with V2 - V1 = usable. Closed form: ratio =
  (p1/p2)^(1/n); V1 = usable / (ratio - 1); V2 = V1 + usable.
  ValueErrors on non-positive pressures/usable; depleted >= charged.
- reservoir_volume(leakage_lpm, hold_minutes =
  DEFAULT_RESERVOIR_HOLD_MIN, margin = DEFAULT_RESERVOIR_MARGIN) ->
  leakage * hold_minutes * margin. ValueErrors on non-positive inputs,
  margin < 1.
- hydraulic_system_summary(...) -> dict with all of the above keys.

Accumulator identity to test: p1 V1^n equals p2 V2^n to float
tolerance on every input pair (the closure_check field).

## Worked example

Reference system: 3000 psi, six actuators of 0.0025 m2 piston area at
0.30 m/s rod speed, 4 simultaneous, leakage 15 L/min, pump efficiency
0.85, accumulator 1.0 L usable between 3000 and 1500 psi with n = 1.4,
reservoir hold 2 minutes at 1.2 margin.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- actuator_flow: flow_m3s = 0.0025 * 0.30 = 0.00075 m3/s; flow_lpm =
  45.0 L/min.
- simultaneous_demand: 4 * 45 = 180 L/min.
- pump_flow: 180 + 15 = 195 L/min; pump_flow_m3s = 0.00325 m3/s.
- pump_power: pressure_pa = 3000 * 6894.757 = 20.6843 MPa; power_w =
  20.6843e6 * 0.00325 / 0.85 = 79087 W; power_kw = 79.0869 kW.
- accumulator: ratio = (3000/1500)^(1/1.4) = 2^(0.714286) = 1.64067;
  V1 = 1.0 / (1.64067 - 1) = 1.5609 L; V2 = 2.5609 L; closure p V^n
  = 2434.17 both sides (match 0.0).
- reservoir_volume: 15 * 2 * 1.2 = 36.0 L.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive area/speed/flow/count/pressure/usable;
  n_simultaneous > n_actuators; efficiency <= 0 or > 1; depleted
  pressure >= charged pressure; margin < 1.
- Actuator flow: 0.0025 m2 at 0.30 m/s = 45.0 L/min; doubling area
  doubles flow.
- Simultaneous demand: 4 of 6 at 45 L/min = 180 L/min; all 6 = 270
  L/min.
- Pump flow: 180 + 15 leakage = 195 L/min; zero leakage gives 180.
- Pump power: worked case 79.0869 kW within 1e-3; efficiency 1.0 gives
  p*Q exactly; efficiency 0.5 doubles power.
- Accumulator closure: p1 V1^n == p2 V2^n to 1e-9 relative on the
  worked case and on a second pair (e.g. 4000/2000 psi, 2 L usable);
  depleted volume minus charged volume equals the usable volume to
  1e-9.
- Reservoir: 15 L/min, 2 min, 1.2 margin = 36.0 L; margin 1.0 with 1
  minute hold = leakage itself.
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-hydraulic-system-sizing.yaml)

Query 1 (copy verbatim):
  "size the aircraft hydraulic pump flow and power from the simultaneous actuator flow demand, piston area, rod speed and leakage"
  intent: "vehicle-design; hydraulic pump flow and power from actuation demand and leakage"
  expected_skill: "vehicle-design/sizing/hydraulic-system-sizing"
Query 2 (copy verbatim):
  "compute the emergency accumulator gas volume between charged and depleted pressure and the reservoir volume for an aircraft hydraulic system"
  intent: "vehicle-design; hydraulic accumulator adiabatic gas volume and reservoir sizing"
  expected_skill: "vehicle-design/sizing/hydraulic-system-sizing"
Task ids: w34-hydraulic-system-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the aircraft hydraulic
power system from actuation demand:" and include the outputs in the
Claim. First tag: hydraulic-system-sizing. Additional tags ONLY:
hydraulic-power-sizing, actuator-flow-demand, pump-flow-sizing,
accumulator-sizing, reservoir-sizing, system-pressure,
emergency-hydraulic. NEVER single generic words (hydraulic, pump, flow,
pressure, actuator, system, sizing). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): hinge moment, control surface
geometry, deflection (control-surface-sizing, spoiler-sizing); strut
loads, shock absorber (landing-gear-sizing); turbopump, rocket
(propulsion/rocket/rocket-turbopump); ice protection (ice-protection-
sizing). The words "actuator flow", "pump flow", "accumulator",
"reservoir", "system pressure" are this leaf's own.

Tags: [hydraulic-system-sizing, hydraulic-power-sizing,
actuator-flow-demand, pump-flow-sizing, accumulator-sizing,
reservoir-sizing, system-pressure, emergency-hydraulic]

Sibling-citation lines for Related leaves:
vehicle-design/sizing/control-surface-sizing (demand side: hinge moment
on the actuator this leaf's pump feeds),
vehicle-design/sizing/environmental-control-sizing (sibling aircraft-
subsystem sizing leaf in the same pack),
vehicle-design/sizing/landing-gear-sizing (utility actuation consumer),
propulsion/rocket/rocket-turbopump (rocket pump boundary).

Ledger Standard: far-25.

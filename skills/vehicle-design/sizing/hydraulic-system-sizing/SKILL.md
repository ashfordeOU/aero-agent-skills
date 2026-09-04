---
name: hydraulic-system-sizing
description: "Use when you must size the aircraft hydraulic power system from actuation demand: actuator flow from piston area and rod speed, worst-case simultaneous demand, pump flow and drive power from system pressure, flow and efficiency with leakage make-up, the emergency accumulator gas volume between charged and depleted pressure from the adiabatic gas law given the usable volume, and the reservoir volume from leakage make-up over a hold time with margin. Produces the per-actuator flow, the simultaneous demand group, pump flow and power, the accumulator charged and depleted gas volumes with the p V^n closure check, and the reservoir volume for hydraulic system architecture studies. Trigger: hydraulic pump sizing, actuator flow demand, pump flow and power, accumulator sizing, hydraulic reservoir sizing, system pressure, emergency hydraulic system, hydraulic power sizing."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [hydraulic-system-sizing, hydraulic-power-sizing, actuator-flow-demand, pump-flow-sizing, accumulator-sizing, reservoir-sizing, system-pressure, emergency-hydraulic]
  version: 0.1.0
  author: AeroSkills
---

# Hydraulic System Sizing (vehicle-design/sizing/hydraulic-system-sizing)

Use when the task is sizing the aircraft hydraulic power system from
flight-control and utility actuation demand: converting each actuator
demand into a flow from the piston area and rod speed, aggregating the
worst-case simultaneous demand group, sizing the pump flow with leakage
make-up and the pump drive power from system pressure, flow and
efficiency, sizing the emergency accumulator gas volume from the
adiabatic gas law between charged and depleted pressure given the
usable volume, and sizing the reservoir from leakage make-up over a
hold time with margin. This leaf implements the model in pure Python,
stdlib only, in scripts/hydraulic_system_sizing_logic.py. It pairs
with vehicle-design/sizing/control-surface-sizing and
vehicle-design/sizing/spoiler-sizing as the demand side (the surfaces
and their hinge moment loads that this leaf's pump feeds) and with
vehicle-design/sizing/landing-gear-sizing as a utility actuation
consumer.

## Domain quick reference

- Actuator flow: Q_a = A_p * v_rod in m3/s (piston area times rod
  speed), with L/min = Q_a * 60000.
- Simultaneous demand: Q_sim = n_sim * Q_a, the worst case with
  n_sim of the identical actuators moving together.
- Pump flow: Q_pump = Q_sim + Q_leak (system leakage make-up, L/min);
  the pump volume rate is Q_pump / 60000 in m3/s.
- Pump power: P = p_pa * Q / eta, where p_pa = p_psi * 6894.757 Pa
  and eta is the pump total efficiency in (0, 1].
- Accumulator: the emergency accumulator gas follows p1 * V1^n = p2 *
  V2^n between charged pressure p1 and depleted pressure p2 with V2 -
  V1 = V_usable. Closed form: ratio = (p1/p2)^(1/n), V1 = V_usable /
  (ratio - 1), V2 = V1 + V_usable. The closure is evaluated in SI
  (p in Pa, V in m3); on the worked example both sides equal 2434.17.
- Reservoir volume: V_res = Q_leak * t_hold * margin, the leakage
  make-up volume over the hold time with the design margin.
- Units: pressures entered in psi and converted internally to Pa,
  flows in L/min and m3/s, volumes in L.
- FAR 25 frames the transport category hydraulic system context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: system pressure p_psi, the identical
   actuator group (piston area A_p, rod speed v_rod, n_actuators,
   n_simultaneous) and the system leakage.
2. Get the per-actuator flow with actuator_flow; doubling the piston
   area doubles the flow.
3. Aggregate the worst case with simultaneous_demand (n_sim * flow).
4. Size the pump with pump_flow: simultaneous demand plus leakage,
   which also returns the pump flow in m3/s. The simultaneity count
   cannot exceed the actuator count.
5. Size the pump drive with pump_power from the system pressure and
   the pump volume rate over the total efficiency.
6. Size the emergency accumulator with accumulator_volumes: charged
   and depleted pressures, the usable volume and the gas exponent n
   (nitrogen, 1.4 adiabatic); the p1 * V1^n = p2 * V2^n closure_check
   is returned for identity verification.
7. Size the reservoir with reservoir_volume from leakage, hold time
   and margin.
8. Run the whole chain in one call with hydraulic_system_summary for
   the complete sizing dict, then confirm the deterministic checks
   with the contract test scripts/test_hydraulic_system_sizing.py.

## Worked example

Reference system: 3000 psi, six actuators of 0.0025 m2 piston area at
0.30 m/s rod speed, 4 simultaneous, leakage 15 L/min, pump efficiency
0.85, accumulator 1.0 L usable between 3000 and 1500 psi with n = 1.4,
reservoir hold 2 minutes at 1.2 margin. Real module outputs:

- actuator_flow(0.0025, 0.30): flow_m3s = 0.00075, flow_lpm = 45.0.
- simultaneous_demand(45.0, 4): 180.0 L/min (all six: 270.0 L/min).
- pump_flow(45.0, 6, 4, 15.0): simultaneous_lpm = 180.0,
  pump_flow_lpm = 195.0, pump_flow_m3s = 0.00325.
- pump_power(3000.0, 0.00325, 0.85): pressure_pa = 20684271.0
  (pressure_mpa = 20.6843), power_w = 79086.9 (79087 W),
  power_kw = 79.0869.
- accumulator_volumes(3000.0, 1500.0, 1.0, 1.4): ratio = 2^(1/1.4) =
  1.64067, charged_gas_volume_l = 1.5609, depleted_gas_volume_l =
  2.5609; the closure sides p1 * V1^n = p2 * V2^n both equal 2434.17
  in SI units and closure_check = 4.5e-13 (match 0.0).
- reservoir_volume(15.0, 2.0, 1.2): 36.0 L.
- hydraulic_system_summary(0.0025, 0.30, 6, 4, 3000.0, 0.85, 3000.0,
  1500.0, 1.0): all 13 keys above in one dict.

## Verification

- Confirm actuator_flow(0.0025, 0.30) returns flow_lpm 45.0 and that
  doubling the area doubles the flow.
- Confirm pump_flow(45.0, 6, 4, 15.0) returns 195.0 L/min and that
  zero leakage returns the 180.0 L/min simultaneous demand.
- Confirm pump_power(3000.0, 0.00325, 0.85) returns power_kw 79.0869;
  efficiency 1.0 gives the p * Q product exactly and 0.5 doubles it.
- Confirm the accumulator closure identity p1 * V1^n = p2 * V2^n to
  1e-9 relative on the worked case and on a second pair (for example
  4000/2000 psi with 2 L usable), and that the depleted volume minus
  the charged volume equals the usable volume.
- Confirm every non-positive area, speed, flow, count, pressure,
  usable volume and margin below 1 raises ValueError, together with
  n_simultaneous above n_actuators, efficiency outside (0, 1] and
  depleted pressure at or above charged pressure.
- Run the contract test offline: python3
  scripts/test_hydraulic_system_sizing.py (34 tests, deterministic).

## Related leaves

- vehicle-design/sizing/control-surface-sizing: the demand side, the
  surface geometry and the hinge moment on the actuator this leaf's
  pump feeds.
- vehicle-design/sizing/environmental-control-sizing: sibling
  aircraft-subsystem sizing leaf in the same pack.
- vehicle-design/sizing/landing-gear-sizing: a utility actuation
  consumer drawing on the hydraulic power system.
- propulsion/turbomachinery/rocket-turbopump: the rocket pump
  boundary, out of scope for aircraft hydraulic pumps.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_hydraulic_system_sizing.py

The test covers the worked-example anchors (45.0 L/min actuator flow,
180 L/min simultaneous demand, 195 L/min pump flow at 0.00325 m3/s,
79.0869 kW at 20.6843 MPa over 0.85 efficiency, 1.5609 L charged and
2.5609 L depleted accumulator volumes, 36.0 L reservoir), the
accumulator p1 * V1^n = p2 * V2^n closure identity to 1e-9 relative
with the closure_check matching zero, depleted minus charged volume
equaling the usable volume, the isothermal n = 1 case, dict key
contracts, run-to-run determinism, and ValueError rejection of every
non-physical input in the validation list.

## Compliance

- Standards referenced, not reproduced: FAR 25 frames the hydraulic
  system installation and power requirements context; the sizing
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

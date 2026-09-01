---
name: engine-flight-test
description: "Use when you must run an engine flight test to determine the installed thrust and verify the engine performance at altitude: derive the thrust from the rate of climb or the level acceleration and the measured drag, compute the fuel flow from the thrust specific fuel consumption, check the exhaust gas temperature margin against the limit, correct the EGT to the ISA temperature, scale the sea-level thrust to the test altitude with the density ratio, time the acceleration and deceleration transients between the test speeds, and report the thrust verification error against the predicted value. Produces the determined thrust in N, the fuel flow in kg/s, the EGT margin in deg C, and the transient times that gate the engine flight test assessment. Trigger: engine flight test, thrust determination, fuel flow, EGT margin, altitude performance, acceleration transient, deceleration transient."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [engine-flight-test, thrust-determination, fuel-flow-measurement, egt-margin, altitude-performance, acceleration-transient, deceleration-transient]
  version: 0.1.0
  author: AeroSkills
---

# Engine Flight Test (flight-test-operations/performance/engine-flight-test)

Use when the task is engine flight testing for a flight test program:
installed thrust determination from the climb or the level
acceleration, fuel flow and specific fuel consumption checks, exhaust
gas temperature margin against the limit, altitude performance
verification, and acceleration and deceleration transient timing.

## Domain quick reference

- Units: forces and weight in N, speeds in m/s, rate of climb in m/s,
  fuel flow in kg/s, thrust specific fuel consumption in kg/(N*s),
  temperatures in deg C, ambient temperature in K, densities in
  kg/m^3.
- thrust_from_rate_of_climb: T = D + W * ROC / V, the small-angle form
  of the steady climb balance T = D + W * sin(gamma).
- thrust_from_acceleration: T = D + (W / g) * a, the level flight
  balance from Newton's second law.
- fuel_flow_from_tsfc: Wf = TSFC * T, the fuel flow burned at the
  determined thrust.
- tsfc_from_flight: TSFC = Wf / T, the achieved specific fuel
  consumption from the measured fuel flow.
- egt_margin: margin = T_limit - T_egt in deg C; a negative margin
  means the exhaust gas temperature exceeds the limit.
- egt_corrected_to_isa: T_corr = (T_egt + 273.15) * 288.15 / T_amb -
  273.15, the absolute temperature ratio correction to the ISA day.
- thrust_at_altitude: T_alt = T_sl * rho_alt / rho_sl, the density
  ratio scaling of the sea-level thrust at constant Mach number.
- accel_time_between_speeds: t = (W / g) * (V2 - V1) / (T - D), the
  time to accelerate between the test speeds at the excess thrust.
- decel_time_between_speeds: t = (W / g) * (V1 - V2) / (D - T_idle),
  the time to decelerate at the idle thrust drag force.
- thrust_verification_error: e = (T_ach - T_pred) / T_pred * 100 in
  percent; negative means a thrust shortfall against the prediction.
- Test condition: engines stabilized at the test thrust setting, the
  airplane trimmed in level flight or a steady climb at the test
  configuration, no configuration changes during the transient.

## Workflow

1. Stabilize the airplane at the test configuration and the thrust
   setting; record weight, altitude, airspeed, fuel flow, and exhaust
   gas temperature at the stabilized condition.
2. Determine the installed thrust with thrust_from_rate_of_climb from
   the rate of climb, or with thrust_from_acceleration from a level
   acceleration, using the measured drag.
3. Compute the fuel flow with fuel_flow_from_tsfc from the thrust
   specific fuel consumption, or reduce the measured fuel flow to the
   achieved consumption with tsfc_from_flight.
4. Check the exhaust gas temperature margin with egt_margin against
   the engine limit, and correct the measurement to the ISA day with
   egt_corrected_to_isa when the ambient temperature differs.
5. Verify the altitude performance with thrust_at_altitude, and
   compare the achieved thrust with thrust_verification_error against
   the predicted installed value.
6. Time the acceleration and deceleration transients between the test
   speeds with accel_time_between_speeds and
   decel_time_between_speeds from the excess thrust and the idle
   thrust drag force.
7. Report the determined thrust, the fuel flow, the EGT margin, the
   altitude verification error, and the transient times for the engine
   flight test assessment.

## Pitfalls

- Mixing unit systems: the mass comes from W / g, so weight, forces,
  and g must share one consistent unit system (N, kg, m, s).
- Treating the drag as zero: the determined thrust is the drag plus
  the climb or acceleration term; neglecting drag overstates the
  thrust.
- Reading the rate of climb term as exact at steep angles: W * ROC / V
  is the small-angle form of W * sin(gamma); use the exact energy
  balance when the climb angle is large.
- Confusing fuel flow with specific fuel consumption: Wf is kg/s and
  TSFC is kg/(N*s); the ratio TSFC = Wf / T only holds in consistent
  units.
- Taking the measured EGT at face value on a non-ISA day: apply the
  absolute temperature ratio correction before the margin comparison.
- Scaling the altitude thrust with the pressure ratio alone: the
  density ratio is the first-order turbojet scale at constant Mach.
- Discarding a negative EGT margin: it is a limit exceedance and a
  test finding, not a computation error; report it.
- Timing a transient with configuration or thrust changes: the
  acceleration and deceleration times are only valid for the fixed
  setting and configuration of the test segment.
- A non-positive excess thrust has no acceleration: the transient time
  is undefined and must raise.

## Behavior contract (gate 3)

The thrust, fuel flow, EGT margin, and transient logic is exercised by
the gate 3 contract test: scripts/test_engine_flight_test.py against
scripts/engine_flight_test_logic.py (stdlib unittest, offline). Run:
`python3 scripts/test_engine_flight_test.py`

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; installed thrust
  determination and engine performance verification in flight is
  common flight-test methodology in the FAR 25.101 general performance
  context, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

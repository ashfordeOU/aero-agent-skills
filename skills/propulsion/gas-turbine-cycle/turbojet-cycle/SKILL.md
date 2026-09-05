---
name: turbojet-cycle
description: "Use when you must analyze an ideal single-stream turbojet core cycle at flight conditions: compute the freestream stagnation temperature from the flight Mach number, the compressor exit temperature from the pressure ratio, the fuel-to-air ratio from the turbine inlet temperature and the combustor efficiency, the turbine exit temperature from the compressor-turbine work balance, the nozzle exit temperature and exit velocity, the net specific thrust as the exit velocity minus the flight velocity, the turbojet TSFC and the propulsive efficiency. Produces the station temperatures, the specific thrust and the TSFC that gate core-engine matching and cycle-trade studies. Trigger: turbojet core cycle, ideal turbojet, compressor-turbine matching, turbine inlet temperature, net specific thrust, turbojet TSFC, core-engine matching, cycle trade study."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: gas-turbine-cycle
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: gas-turbine-cycle
  tags: [turbojet-cycle, ideal-turbojet, compressor-turbine-matching, turbine-inlet-temperature, net-specific-thrust, turbojet-tsfc, core-engine-matching]
  version: 0.1.0
  author: AeroSkills
---

# Turbojet Cycle (propulsion/gas-turbine-cycle/turbojet-cycle)

Use when the task is the ideal single-stream turbojet core cycle at a
flight Mach number: the inlet stagnation state, the compressor exit
state, the combustor fuel-to-air ratio, the turbine exit state from the
compressor-turbine work balance, the fully expanded nozzle state, and
the net specific thrust, TSFC and propulsive efficiency that close the
cycle. This leaf owns the compressor-turbine matching middle of the
core-engine cycle assessment, which no other leaf computes. It pairs
with the shaft-power cycle leaf (gas-turbine-cycle/gas-turbine-cycle)
and the lossy cycle leaf (gas-turbine-cycle/real-cycle-effects) for the
ideal-to-real follow-on, with gas-turbine-cycle/subsonic-inlet-recovery
for the ram recovery that sets the inlet stagnation state, and with
gas-turbine-cycle/combustor-design for the burner sizing side of the
fuel-to-air ratio.

## Domain quick reference

- Stations: 0 freestream, 3 compressor exit, 4 combustor exit (turbine
  inlet), 5 turbine exit, 9 nozzle exit. SI units throughout: K, kg fuel
  per kg air, N per (kg/s), kg/(N s), m/s.
- Freestream stagnation temperature: Tt0 = t0 * (1 + (gamma - 1)/2 *
  M^2). At mach 0.9 and 288.15 K this gives 334.8 K.
- Compressor exit temperature: T03 = Tt0 * pr^((gamma-1)/gamma). The
  compression traverse raises 334.8 K to 764.7 K at pressure ratio 18.
- Fuel-to-air ratio: f = cp_c * (t04 - t03) / (eta_b * lhv), the
  combustor energy balance at efficiency eta_b.
- Compressor-turbine work balance (the matching step): Tt5 = t04 -
  (cp_c/cp_g) * (t03 - Tt0). The turbine work equals the compressor
  work, so Tt5 falls when the compressor exit temperature rises at fixed
  turbine inlet temperature.
- Nozzle total pressure ratio chain: pt5/p0 = (1 + (gamma-1)/2 * M^2)^
  (gamma/(gamma-1)) * pr * (Tt5/Tt4)^(gamma/(gamma-1)), the ram factor
  times the compressor ratio times the turbine expansion factor.
- Nozzle exit temperature: T9 = Tt5 * (p0/pt5)^((gamma-1)/gamma) for a
  fully expanded nozzle to ambient pressure.
- Exit velocity: v9 = sqrt(2 * cp_g * (Tt5 - T9)), the thermal expansion
  of the remaining enthalpy drop.
- Net specific thrust: F/mdot = v9 - v0 with v0 = M * sqrt(gamma * R *
  t0). The flight velocity term is the ram drag, so the specific thrust
  falls as the Mach number rises at fixed turbine inlet temperature.
- Turbojet TSFC: TSFC = f / (F/mdot) in kg/(N s); TSFC times the
  specific thrust equals the fuel-to-air ratio.
- Propulsive efficiency: eta_p = 2 * v0 / (v0 + v9), always below 1 and
  rising as v9 approaches v0.
- Module gas constants: gamma 1.4, cp_c 1005 J/(kg K), cp_g 1150 J/(kg
  K), R 287 J/(kg K), lhv 43 MJ/kg, eta_b 0.99; keyword overrides
  allowed. FAR 33 frames the engine context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: freestream static temperature t0, flight
   Mach number mach, compressor pressure ratio pr and turbine inlet
   temperature t04, all SI, the cycle_report input set.
2. Freestream stagnation temperature traverse: freestream_stagnation_
   temperature(t0, mach) returns Tt0 from the Mach number.
3. Compression traverse: compressor_exit_temperature(t0, mach, pr)
   returns the compressor exit temperature T03.
4. Combustor energy balance: fuel_air_ratio(t03, t04) returns the
   fuel-to-air ratio f from the turbine inlet temperature, the combustor
   efficiency and the lower heating value.
5. Compressor-turbine matching step: turbine_exit_temperature(t03, t04,
   t0, mach) returns the turbine exit temperature Tt5 from the work
   balance; this is the canonical compressor-turbine matching of the
   core engine.
6. Nozzle expansion: nozzle_exit_temperature(t0, mach, pr, t04) returns
   the nozzle exit temperature T9 through the nozzle total pressure
   ratio chain, then exit_velocity(t05, t9) returns the exit velocity v9
   from the thermal drop Tt5 - T9.
7. Thrust bookkeeping: net_specific_thrust(t0, mach, t05, t9) returns
   the net specific thrust F/mdot, turbojet_tsfc(f, F/mdot) returns the
   turbojet TSFC, and propulsive_efficiency(v0, v9) returns the
   propulsive efficiency.
8. Cycle report: cycle_report(t0, mach, pr, t04) returns the dict with
   keys tt0, t03, fuel_air, t05, t9, v9, specific_thrust, tsfc and
   propulsive_efficiency for the matching and trade study.
9. Verify: run python3 scripts/test_turbojet_cycle.py; the contract
   test asserts the worked-example anchors, the TSFC round-trip
   identity, the ram-drag trend, the zero-Mach degenerate thermal
   expansion identity and every ValueError guard.

## Worked example

Sea level static day, t0 = 288.15 K, mach 0.9, pr 18, t04 = 1600 K.
Module outputs (contract test anchors in parentheses):

- Tt0 = 334.83 K (334.8 within 0.2 K).
- T03 = 764.67 K (764.7 within 0.5 K).
- f = 0.01972 (0.0197 within 1e-4), about 19.7 g fuel per kg air.
- Tt5 = 1224.36 K (1224.4 within 0.5 K) from the compressor-turbine
  work balance.
- T9 = 602.93 K; v9 = 1195.53 m/s (1195.5 within 1 m/s).
- v0 = 306.24 m/s; F/mdot = 889.29 N/(kg/s) (889.3 within 1).
- TSFC = 2.218e-5 kg/(N s) (2.22e-5 within 1e-7), about 22.2 mg/(N s).
- Propulsive efficiency = 0.408 (0.408 within 0.002).
- Round trip: TSFC * F/mdot = 0.01972 = f exactly.
- The degenerate identity: at zero Mach the flight velocity vanishes and
  the net specific thrust equals the nozzle exit velocity, the thermal
  expansion of the added heat.

## Verification

- Confirm freestream_stagnation_temperature(288.15, 0.9) returns 334.83
  K and compressor_exit_temperature(288.15, 0.9, 18.0) returns 764.67 K.
- Confirm fuel_air_ratio(764.67, 1600.0) returns 0.01972 and
  turbine_exit_temperature(764.67, 1600.0, 288.15, 0.9) returns 1224.36 K.
- Confirm exit_velocity then net_specific_thrust reproduce v9 = 1195.53
  m/s and F/mdot = 889.29 N/(kg/s); the TSFC round trip TSFC * F/mdot
  equals f.
- Confirm the net specific thrust decreases as the Mach number rises at
  fixed t04 (ram drag) and the propulsive efficiency stays below 1.
- Degenerate identity: the spec states it at zero Mach with a unity
  pressure ratio, but the model rejects pressure ratio 1 (no compression
  means no expandable pressure ratio, a ValueError guard in the
  validation list), so the identity is exercised at zero Mach with
  pressure ratio 18, where v0 = 0 and the net specific thrust equals the
  nozzle thermal expansion velocity, and in the near-unity limit at
  pressure ratio 1.001 where the cycle stays defined.
- Confirm every non-positive temperature or LHV, mach below 0, pressure
  ratio at or below 1, turbine inlet temperature at or below the
  compressor exit temperature, combustor efficiency outside (0, 1] and
  every non-finite input raises ValueError.
- Run the contract test offline: python3 scripts/test_turbojet_cycle.py
  (34 tests, deterministic, exits 0).

## Related leaves

- propulsion/gas-turbine-cycle/gas-turbine-cycle: the shaft-power
  Brayton cycle leaf upstream of the propulsive stream.
- propulsion/gas-turbine-cycle/real-cycle-effects: component
  efficiencies and pressure loss that turn this ideal cycle real.
- propulsion/gas-turbine-cycle/subsonic-inlet-recovery: the ram recovery
  that sets the inlet stagnation state at flight Mach.
- propulsion/gas-turbine-cycle/combustor-design: burner geometry and
  efficiency on the fuel-to-air ratio computed in step 4.

## Pitfalls

- Treating the ideal cycle as the real engine: this leaf assumes
  isentropic machines and no pressure loss; real-cycle-effects adds the
  component efficiencies that lower Tt5 and raise the TSFC.
- Balancing the shaft power on the wrong specific heats: the work
  balance Tt5 = t04 - (cp_c/cp_g) * (t03 - Tt0) mixes the cold-side
  compressor work (cp_c = 1005) with the hot-side turbine (cp_g =
  1150); using one cp for both shifts Tt5 by tens of kelvin.
- Forgetting the ram drag: F/mdot is v9 minus v0, not v9; at mach 0.9
  the 306 m/s flight velocity is a third of the exit velocity, so a
  gross-thrust number overstates the net specific thrust.
- Reading the degenerate identity at pressure ratio 1: the model
  rejects pressure ratio 1 by design, and the check runs at zero Mach
  where the ram term vanishes, not at a unity compression ratio.
- Quoting TSFC without the round trip: TSFC * F/mdot must equal the
  fuel-to-air ratio; if the product drifts from f, the fuel or thrust
  leg is inconsistent.
- Expanding states that cannot reach ambient: the nozzle model requires
  pt5/p0 above 1; states that do not expand to ambient raise ValueError
  instead of returning an imaginary exit velocity.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_turbojet_cycle.py

The test covers the worked-example anchors (Tt0 334.8 K, T03 764.7 K,
f 0.0197, Tt5 1224.4 K, v9 1195.5 m/s, F/mdot 889.3 N/(kg/s), TSFC
2.22e-5 kg/(N s), propulsive efficiency 0.408), the closed forms of
every traverse, the compressor-turbine work balance trend, the TSFC
round-trip identity, the ram-drag trend, the zero-Mach degenerate
thermal expansion identity, the exact cycle report keys, determinism,
and ValueError rejection of pressure ratio at or below 1, turbine inlet
temperature at or below the compressor exit temperature, negative Mach,
non-positive temperatures and LHV, out-of-range combustor efficiency,
non-finite inputs and nozzle states that do not expand.

## Compliance

- Standards referenced, not reproduced: 14 CFR Part 33 (FAR 33) frames
  the engine type-certification context (ecfr.gov); the ideal cycle
  relations above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

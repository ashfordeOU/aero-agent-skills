# Wave-39 leaf spec: turbojet-cycle (propulsion, gas-turbine-cycle pack)

- Path: skills/propulsion/gas-turbine-cycle/turbojet-cycle/
- Pack: gas-turbine-cycle. Closest siblings: gas-turbine-cycle (shaft-power
  Brayton: brayton_thermal_efficiency, compressor_exit_temperature,
  turbine_exit_temperature, cycle_specific_work - no flight Mach, no work
  balance), real-cycle-effects (station temperatures with component
  efficiencies and SFC, no matching), afterburner-cycle (its module
  docstring delegates the core upward: the turbine exit state comes from the
  gas-turbine-cycle / real-cycle-effects core leaves; it computes reheat
  augmentation with t04 given), ramjet-cycle (no rotating machinery),
  turbofan-cycle (takes vj as given), intercooled-cycle, regenerative-cycle.
  Whole-tree greps at prep: "work balance" = 0 owning hits; "turbojet" = 0
  leaves computing a turbojet core cycle (only incidental text in
  real-cycle-effects docstring, flight-test, vehicle-design engine-sizing
  and export-control). GENUINE PROP gap (fresh probe): the canonical missing
  middle - compressor-turbine matching - is computed by no leaf.
- Standards id: far-33 (reference-only). Ledger Standard: far-33.
- Family: propulsion

## Claim

Analyze the ideal single-stream non-afterburning turbojet core cycle at
flight Mach number: compute the freestream stagnation temperature, the
compressor exit temperature from the pressure ratio, the fuel-to-air ratio
from the turbine inlet temperature and the combustor efficiency, size the
turbine exit temperature from the compressor-turbine work balance, expand
through the nozzle to the exit temperature and velocity, and return the net
specific thrust (nozzle exit velocity minus flight velocity), the turbojet
TSFC and the propulsive efficiency. Produces the station temperatures, the
specific thrust and the TSFC that gate core-engine matching and
cycle-trade studies. Does NOT do: shaft-power Brayton efficiency or SFC
(gas-turbine-cycle, real-cycle-effects); reheat augmentation (afterburner-
cycle); bypass or fan streams (turbofan-cycle); ramjet cycles without
rotating machinery (ramjet-cycle); regenerative or intercooled variants.

## Model (implement exactly)

Station sequence 0 (freestream) to 3 (compressor exit) to 4 (combustor
exit / turbine inlet) to 5 (turbine exit) to 9 (nozzle exit). Ideal cycle
with gamma = 1.4, cp_c = 1005 J/(kg K) and cp_g = 1150 J/(kg K) as module
defaults (callable overrides allowed through keyword arguments).

Functions (pure stdlib):
- freestream_stagnation_temperature(t0, mach) -> Tt0 = t0 * (1 + (gamma -
  1)/2 * M^2).
- compressor_exit_temperature(t0, mach, pr) -> T03 = Tt0 * pr^((gamma-1)/
  gamma).
- fuel_air_ratio(t03, t04, eta_b=0.99, lhv=43e6) -> f = cp_c * (t04 - t03)
  / (eta_b * lhv).
- turbine_exit_temperature(t03, t04, t0, mach) -> Tt5 = t04 - (cp_c /
  cp_g) * (t03 - Tt0) (compressor-turbine work balance).
- nozzle_exit_temperature(t0, mach, pr, t04, ...) -> T9 = Tt5 * (p0/pt5)
  ^((gamma-1)/gamma) with pt5/p0 = (1 + (gamma-1)/2*M^2)^(gamma/(gamma-1))
  * pr * (Tt5/Tt4)^(gamma/(gamma-1)).
- exit_velocity(t05, t9) -> v9 = sqrt(2 * cp_g * (Tt5 - T9)).
- net_specific_thrust(t0, mach, t05, t9) -> F/mdot = v9 - v0 with
  v0 = M * sqrt(gamma * R * t0), R = 287 J/(kg K).
- turbojet_tsfc(f, f_over_mdot) -> f / (F/mdot) in kg/(N s).
- propulsive_efficiency(v0, v9) -> 2 * v0 / (v0 + v9).
- cycle_report(...) -> dict with keys tt0, t03, fuel_air, t05, t9, v9,
  specific_thrust, tsfc, propulsive_efficiency.
ValueErrors: non-positive temperatures or LHV, mach < 0, pr <= 1,
t04 <= t03, eta_b outside (0, 1], non-finite inputs.

Identity to test: at zero Mach and pr = 1 the nozzle exit velocity equals
the thermal expansion of the added heat (degenerate check); TSFC times
specific thrust equals the fuel-to-air ratio; specific thrust decreases as
mach rises at fixed t04 (ram drag); propulsive efficiency is below 1 and
increases as v9 approaches v0.

## Worked example

t0 = 288.15 K, mach = 0.9, pr = 18, t04 = 1600 K, cp_c = 1005,
cp_g = 1150, lhv = 43e6, eta_b = 0.99, gamma = 1.4, R = 287:
- Tt0 = 334.8 K; T03 = 764.7 K; f = 0.0197.
- Tt5 = 1224.4 K (work balance).
- v9 = 1195.5 m/s; v0 = 306.2 m/s; F/mdot = 889.3 N/(kg s);
  TSFC = 2.22e-5 kg/(N s) (22.2 mg/(N s)); propulsive efficiency 0.408.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (independently evaluated at prep).

## Validation list (contract test must include)

- Tt0 334.8 K within 0.2 K; T03 764.7 K within 0.5 K.
- f = 0.0197 within 1e-4; Tt5 = 1224.4 K within 0.5 K.
- v9 1195.5 m/s within 1 m/s; F/mdot 889.3 N/(kg s) within 1.
- TSFC 2.22e-5 kg/(N s) within 1e-7; propulsive efficiency 0.408 within
  0.002.
- Work balance: Tt5 falls when t03 rises at fixed t04.
- ValueErrors: pr = 1, t04 <= t03, mach negative, eta_b 1.5, t0 0.
- Identity: TSFC * F/mdot == f within float tolerance.
- Determinism; report dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-turbojet-cycle.yaml)

Query 1 (copy verbatim):
  "compute the turbojet-cycle net specific thrust and the turbojet-tsfc at mach 0.9 with pressure ratio 18 and a 1600 kelvin turbine-inlet-temperature"
  intent: "propulsion; ideal turbojet core cycle specific thrust and TSFC"
  expected_skill: "propulsion/gas-turbine-cycle/turbojet-cycle"
Query 2 (copy verbatim):
  "size the turbine exit temperature by the compressor work-balance for the non-afterburning turbojet core engine"
  intent: "propulsion; compressor-turbine work balance matching"
  expected_skill: "propulsion/gas-turbine-cycle/turbojet-cycle"
Task ids: w39-turbojet-cycle-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must analyze an ideal single-stream
turbojet core cycle at flight conditions:" and include the outputs in the
Claim. First tag: turbojet-cycle. Additional tags ONLY: ideal-turbojet,
compressor-turbine-matching, turbine-inlet-temperature, net-specific-thrust,
turbojet-tsfc, core-engine-matching. NEVER single generic words (cycle,
thrust, turbine, compressor, engine, matching, efficiency). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): brayton-thermal-efficiency,
regenerative, intercooled (gas-turbine-cycle leaves); reheat, afterburner
(afterburner-cycle); bypass-ratio, fan (turbofan-cycle); ramjet, scramjet
(ramjet-cycle); propelling-nozzle; rocket-equation.

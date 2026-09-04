# Wave-37 leaf spec: subsonic-inlet-recovery (propulsion, gas-turbine-cycle pack)

- Path: skills/propulsion/gas-turbine-cycle/subsonic-inlet-recovery/
- Pack: gas-turbine-cycle. Closest siblings: gas-turbine-cycle and
  turbofan-cycle (station-by-station cycle decks that take the inlet
  recovery as an INPUT at the fan/compressor face station - whole-tree
  grep for "ram recovery" / "inlet recovery" / "pressure recovery" has
  ZERO owning hits outside ramjet-inlet), ramjet-inlet (supersonic
  ramjet intake shock system for the RAMJET family - not the subsonic
  turbofan intake), propelling-nozzle (exhaust side; wave-36),
  real-cycle-effects (component loss bookkeeping, not inlet recovery
  from flight Mach). ZERO owners of the subsonic-intake recovery
  function. GENUINE PROP gap (fresh probe, wave-36 PROP receipt did not
  cover it).
- Standards id: far-33 (reference-only; family spine - the inlet feeds
  the engine installation; Part 25 installation context is named in the
  body). Ledger Standard: far-33.
- Family: propulsion

## Claim

Compute the total-pressure recovery and the compressor-face condition
for a subsonic turbofan or turboprop intake at a flight condition: the
ram recovery ratio from the free-stream Mach number (unity at subsonic
Mach, MIL-E-5008B style roll-off above Mach 1), the free-stream
stagnation pressure ratio from the isentropic relation, the total
pressure delivered at the engine face after the duct total-pressure
efficiency, the required capture area for the engine mass flow at the
flight speed and density, and the capture verdict against the intake
highlight area (spillage when the required capture area exceeds the
highlight). Produces the ram recovery, face total pressure, capture
area, and a full-capture or spillage verdict that gate the cycle deck
inlet condition. Does NOT do: supersonic ramjet inlet shock recovery and
starting (ramjet-inlet); nozzle expansion (propelling-nozzle); full
station-by-station cycle bookkeeping (gas-turbine-cycle / turbofan-
cycle); duct loss allocation among bleed and power offtakes (real-cycle-
effects).

## Model (implement exactly)

Module constants: GAMMA = 1.4, R_AIR = 287.0, RECOVERY_ROLLOFF = 0.075,
RECOVERY_EXPONENT = 1.35.

Functions (pure stdlib):
- ram_recovery(mach) -> float: mach <= 1.0 -> 1.0; mach < 5.0 ->
  1.0 - RECOVERY_ROLLOFF * (mach - 1.0) ** RECOVERY_EXPONENT; mach >= 5.0
  raises ValueError. Negative mach raises ValueError.
- stagnation_pressure_ratio(mach) -> float:
  (1 + 0.2 * mach**2) ** 3.5.
- face_total_pressure(p0, mach, duct_efficiency) -> float:
  p0 * stagnation_pressure_ratio(mach) * ram_recovery(mach) *
  duct_efficiency. ValueErrors: p0 <= 0; duct_efficiency not in (0, 1].
- capture_area(mass_flow, p0, T0, mach) -> float: freestream density rho
  = p0 / (R_AIR * T0), freestream speed V = mach *
  sqrt(GAMMA * R_AIR * T0), area = mass_flow / (rho * V). ValueErrors:
  mass_flow <= 0, p0 <= 0, T0 <= 0.
- capture_verdict(capture_area, highlight_area) -> "full-capture" when
  capture_area <= highlight_area else "spillage".

Identity to test: face_total_pressure at mach <= 1 with duct efficiency
1.0 equals p0 * stagnation_pressure_ratio(mach); capture_area scales
inversely with density.

## Worked example

Flight condition: mach 0.82, p0 = 101325 Pa, T0 = 216.65 K,
duct_efficiency 0.98, engine mass flow 200 kg/s.
Run your module and take the real outputs as assert targets; bounds
independently verified at prep:
- ram_recovery(0.82) = 1.0; ram_recovery(1.5) = 0.970578.
- stagnation_pressure_ratio(0.82) = 1.5552.
- face_total_pressure = 101325 * 1.5552 * 1.0 * 0.98 = 154430 Pa
  (within 1 Pa of the module's real value at the anchor).
- rho = 1.629 kg/m3, V = 241.9 m/s, capture_area = 0.5075 m2
  (200 / (1.629 * 241.9)).
- capture_verdict against a highlight of 0.60 m2 -> full-capture;
  against 0.45 m2 -> spillage.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: negative mach; mach >= 5; p0 <= 0; duct efficiency 0 or
  negative or > 1; mass_flow <= 0.
- ram recovery truth table: 0.8 -> 1.0; 1.2 -> 1 - 0.075*0.2**1.35;
  2.0 -> 1 - 0.075*1.0**1.35 = 0.925.
- face total pressure anchor 154430 Pa within 1 Pa.
- capture area anchor 0.5075 m2 within 1e-3.
- Identity: subsonic full-recovery identity above.
- Determinism; dict/float outputs as documented.

## Corpus fragment (eval/hit1-wave37-subsonic-inlet-recovery.yaml)

Query 1 (copy verbatim):
  "compute the subsonic-inlet-recovery ram recovery and engine face total pressure for a turbofan intake at flight mach"
  intent: "propulsion; subsonic intake ram recovery and face total pressure"
  expected_skill: "propulsion/gas-turbine-cycle/subsonic-inlet-recovery"
Query 2 (copy verbatim):
  "check the intake capture-area verdict and spillage against the highlight area for the engine mass flow"
  intent: "propulsion; intake capture area and spillage verdict"
  expected_skill: "propulsion/gas-turbine-cycle/subsonic-inlet-recovery"
Task ids: w37-subsonic-inlet-recovery-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute subsonic inlet total
pressure recovery:" and include the outputs in the Claim. First tag:
subsonic-inlet-recovery. Additional tags ONLY: ram-recovery-ratio,
engine-face-total-pressure, intake-capture-area, spillage-verdict,
duct-total-pressure-efficiency. NEVER single generic words (inlet,
recovery, intake, pressure, duct, capture). 50-150 words, <=1000 chars,
no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): shock system, supersonic inlet,
starting (ramjet-inlet); nozzle throat, gross thrust (propelling-nozzle);
station-by-station cycle, compressor face temperatures as cycle output
(gas-turbine-cycle); bleed and power offtake losses (real-cycle-effects).

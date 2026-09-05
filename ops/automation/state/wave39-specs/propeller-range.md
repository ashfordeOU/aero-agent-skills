# Wave-39 leaf spec: propeller-range (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/propeller-range/
- Pack: performance. Closest siblings: breguet-range (implements exactly
  one function breguet_range(v, tsfc, ld, m0, m1) - jet and TSFC only; its
  SKILL body is FAR-25/CS-25 transport context and never takes a propeller
  efficiency or power-specific fuel consumption), breguet-endurance
  (implements BOTH jet_endurance and prop_endurance - the propeller branch
  of the Breguet family exists on the endurance side but is MISSING on the
  range side), specific-range, thrust-required, turboprop-cycle (engine-side
  specific_fuel_consumption and propeller_efficiency from slipstream
  velocities - cycle metrics, not aircraft range). Whole-tree greps at
  prep: "psfc" = only turboprop-cycle engine metrics; name propeller-range
  unused; corpus has no PSFC range task. GENUINE FM gap (fresh probe:
  function-level asymmetry inside the Breguet family).
- Standards id: far-25 (reference-only; sibling convention - the ledger row
  Standard is far-25). Ledger Standard: far-25.
- Family: flight-mechanics

## Claim

Compute the cruise range of a propeller or turboprop aircraft from
power-specific fuel consumption and propeller efficiency: form the range
with the propeller Breguet equation R = (eta_p / (c_p * g0)) * (L/D) *
ln(m0/m1), convert a pounds-per-horsepower-hour PSFC into SI kilograms per
watt-second when needed, and derive the final mass from a fuel fraction.
Produces the cruise range in meters (and kilometers) that gates fuel
planning for propeller aircraft. Does NOT do: jet/TSFC cruise range
(breguet-range); endurance of either propulsion type (breguet-endurance);
specific air range (specific-range); engine-side PSFC or propeller
efficiency from slipstream velocities (turboprop-cycle).

## Model (implement exactly)

Module constant G0 = 9.80665 m/s2.

Functions (pure stdlib):
- psfc_lb_per_hp_h_to_kg_per_w_s(value) -> value * 0.45359237 /
  (745.6999 * 3600).
- final_mass_from_fuel_fraction(initial_mass, fuel_fraction) ->
  m0 * (1 - f); ValueError if initial_mass <= 0 or fuel_fraction outside
  [0, 1).
- propeller_range(propeller_efficiency, psfc_kg_per_w_s, ld, initial_mass,
  final_mass) -> R = (eta_p / (c_p * g0)) * (L/D) * ln(m0/m1) in meters;
  ValueError if propeller_efficiency <= 0 or > 1, psfc <= 0, ld <= 0,
  initial_mass <= 0, final_mass <= 0, final_mass >= initial_mass.
- range_km(...) convenience or a report dict with keys range_m, range_km.

Identity to test: doubling the propeller efficiency doubles the range;
doubling the PSFC halves the range; range goes to zero as the final mass
approaches the initial mass; the range of a fuel-fraction profile matches
the direct m0/m1 form.

## Worked example

eta_p = 0.80, c_p = 0.55 lb/hp/h = 9.293e-8 kg/(W s), L/D = 12,
m0 = 11,500 kg, m1 = 10,000 kg:
- R = (0.80 / (9.293e-8 * 9.80665)) * 12 * ln(1.15) = 1,472.2 km
  (1.4722e6 m).
- final_mass_from_fuel_fraction(11500, 0.1304) = 10,000 kg.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (independently evaluated at prep).

## Validation list (contract test must include)

- psfc conversion: 0.55 lb/hp/h -> 9.293e-8 kg/(W s) within 1e-10.
- propeller_range = 1.4722e6 m within 1e3 (1472.2 km within 1 km).
- Range scales linearly with eta_p (0.9 gives 1656 km within 2 km).
- Range halves when PSFC doubles.
- final_mass_from_fuel_fraction round trip.
- ValueErrors: eta_p 0 or 1.05, psfc 0, ld 0, m1 >= m0, fuel fraction 1.
- Determinism; report dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-propeller-range.yaml)

Query 1 (copy verbatim):
  "compute the propeller-range of the turboprop transport from the power specific fuel consumption and the propeller efficiency at a lift to drag ratio of twelve"
  intent: "flight-mechanics; propeller aircraft cruise range from PSFC"
  expected_skill: "flight-mechanics/performance/propeller-range"
Query 2 (copy verbatim):
  "estimate the cruise range with psfc and prop efficiency for the propeller aircraft fuel planning between the initial and the final mass"
  intent: "flight-mechanics; Breguet range with power-specific fuel consumption"
  expected_skill: "flight-mechanics/performance/propeller-range"
Task ids: w39-propeller-range-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the cruise range of a
propeller or turboprop aircraft:" and include the outputs in the Claim.
First tag: propeller-range. Additional tags ONLY: psfc, power-specific-
fuel-consumption, propeller-efficiency, turboprop-range, fuel-fraction.
NEVER single generic words (range, propeller, fuel, efficiency, cruise,
aircraft). 50-150 words, <=1000 chars, no em dash, no "classified", action
verb present.

FORBIDDEN TOKENS (belong to siblings): tsfc, cruise-time, specific-range
(breguet-range, specific-range); endurance, loiter (breguet-endurance);
slipstream-velocity, shaft-power (turboprop-cycle); thrust-required.

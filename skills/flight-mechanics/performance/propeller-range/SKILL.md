---
name: propeller-range
description: "Use when you must compute the cruise range of a propeller or turboprop aircraft: form the range with the propeller Breguet equation from power specific fuel consumption and propeller efficiency at a given lift to drag ratio, convert a pounds per horsepower hour PSFC into SI kilograms per watt second when needed, and derive the final mass from the fuel fraction. Produces the cruise range in meters and kilometers for fuel planning between the initial and final mass. Covers the propeller branch of the Breguet range family that the jet-only range relation leaves open. Trigger: propeller range, turboprop cruise range, PSFC, power specific fuel consumption, propeller efficiency, fuel fraction, lift to drag ratio, mass ratio."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [propeller-range, psfc, power-specific-fuel-consumption, propeller-efficiency, turboprop-range, fuel-fraction]
  version: 0.1.0
  author: AeroSkills
---

# Propeller Range (flight-mechanics/performance/propeller-range)

Use when the task is the cruise range of a propeller or turboprop
aircraft from the propeller Breguet equation: power specific fuel
consumption (PSFC), propeller efficiency, lift to drag ratio and the
initial and final masses. This is the propeller branch of the Breguet
range family; the jet side of the family (flight-mechanics/performance/
breguet-range) never takes a propeller efficiency, and the endurance
leaf (flight-mechanics/performance/breguet-endurance) already carries
the propeller branch on the endurance side, so the range side is
completed here. It pairs with the engine-side leaf
propulsion/turboprop/turboprop-cycle, which evaluates PSFC and
propeller efficiency from slipstream velocities; this leaf turns those
engine metrics into an aircraft cruise range. Does NOT do: jet
transport cruise range from thrust specific fuel consumption
(breguet-range); endurance of either propulsion type
(breguet-endurance); specific air range (specific-range); required
thrust for the cruise condition (thrust-required); engine-side PSFC or
propeller efficiency from slipstream velocities (turboprop-cycle).

## Domain quick reference

- Propeller Breguet range equation for still-air cruise range R:

  R = (eta_p / (c_p * g0)) * (L/D) * ln(m0 / m1)

  with eta_p the propeller efficiency, c_p the power specific fuel
  consumption in kg/(W s), g0 = 9.80665 m/s^2 the standard gravity,
  L/D the lift to drag ratio, m0 the initial (start of cruise) mass
  and m1 the final mass, all masses in kg.
- Units: PSFC in kg/(W s), range in meters (divide by 1000 for
  kilometers). There is no cruise speed term: the propeller relation
  is an energy bookkeeping on the shaft fuel flow, so the efficiency
  enters the numerator and the PSFC the denominator.
- Unit conversion: 1 lb/(hp h) = 0.45359237 / (745.6999 * 3600)
  kg/(W s); a pounds per horsepower hour PSFC is multiplied by that
  factor with psfc_lb_per_hp_h_to_kg_per_w_s.
- Final mass from the fuel fraction f: m1 = m0 * (1 - f), the form
  used when the fuel plan is stated as the burned fraction of the
  initial mass.
- Range analysis sits in the FAR-25 transport performance context for
  cruise fuel planning of propeller and turboprop aircraft.

## Workflow

1. Fix the operating inputs: propeller efficiency eta_p in (0, 1],
   the power specific fuel consumption c_p, lift to drag ratio L/D,
   initial mass m0 and final mass m1. When the PSFC arrives in pounds
   per horsepower hour, run step 1's unit conversion with
   psfc_lb_per_hp_h_to_kg_per_w_s to get c_p in kg/(W s).
2. When the fuel plan is a burned fuel fraction, derive the final
   cruise mass with final_mass_from_fuel_fraction: m1 = m0 * (1 - f).
3. Form the cruise range with propeller_range (or propeller_range_km
   for kilometers directly), evaluating the propeller Breguet equation
   on the mass ratio m0/m1.
4. Run the physical sanity gate: eta_p must sit in (0, 1], c_p and
   L/D positive, and 0 < m1 < m0 so ln(m0/m1) stays positive; confirm
   the range scales linearly with the propeller efficiency (eta_p 0.9
   against the 0.8 reference) and halves when the PSFC doubles.
5. Package the result with range_report, which returns the report
   dict with the range_m and range_km keys, and cross check that the
   kilometers figure equals the meters value divided by 1000.
6. Close with the deterministic offline checks in the contract test
   scripts/test_propeller_range.py.

## Worked example

A turboprop transport cruises at L/D = 12 with propeller efficiency
eta_p = 0.80 and PSFC c_p = 0.55 lb/hp/h, from m0 = 11,500 kg to
m1 = 10,000 kg.

- Unit conversion (workflow step 1): psfc_lb_per_hp_h_to_kg_per_w_s
  (0.55) = 9.293126e-8 kg/(W s), within the 9.293e-8 anchor.
- Cruise range (workflow step 3): propeller_range(0.80,
  9.293126e-8, 12, 11500, 10000) = 1.4722367e6 m = 1472.24 km, within
  1 km of the 1472.2 km anchor.
- Efficiency scaling (workflow step 4): eta_p 0.9 raises the range to
  1656.27 km (0.9/0.8 * 1472.24), within 2 km of the 1656 km anchor.
- Fuel fraction (workflow step 2): final_mass_from_fuel_fraction
  (11500, 1500/11500) = 10,000 kg exactly; the range computed through
  the fuel fraction profile equals the direct m0/m1 form.
- Report (workflow step 5): range_report returns {"range_m":
  1472236.70, "range_km": 1472.24}, exactly the two documented keys.

## Verification

- Confirm propeller_range(0.80, 9.293126e-8, 12, 11500, 10000)
  returns 1.4722367e6 m and that doubling the propeller efficiency
  doubles the range while doubling the PSFC halves it.
- Confirm the range vanishes toward zero as the final mass approaches
  the initial mass (the ln(m0/m1) factor collapses).
- Confirm final_mass_from_fuel_fraction(11500, 1500/11500) returns
  10,000 kg and the fraction round trips: (m0 - m1) / m0 = f.
- Confirm range_report returns exactly the keys range_m and range_km
  and that range_km equals range_m / 1000.
- Confirm every non-physical input raises ValueError: propeller
  efficiency 0, above 1 or negative; PSFC zero or negative; L/D zero;
  initial or final mass not positive; final mass at or above the
  initial mass; fuel fraction 1, above 1 or negative; negative PSFC
  in the unit conversion.
- Run the contract test offline: python3
  scripts/test_propeller_range.py (35 tests, deterministic).

## Related leaves

- flight-mechanics/performance/breguet-range: jet transport cruise
  range from speed and thrust specific fuel consumption, the jet side
  of the same family.
- flight-mechanics/performance/breguet-endurance: endurance of both
  propulsion types, where the propeller branch already exists.
- flight-mechanics/performance/specific-range: specific air range
  for fuel planning at a fixed flight condition.
- flight-mechanics/performance/thrust-required: the required thrust
  at the cruise condition that sets the L/D operating point.
- propulsion/turboprop/turboprop-cycle: engine-side PSFC and
  propeller efficiency from slipstream velocities, the inputs this
  leaf consumes.

## Pitfalls

- Feeding a thrust specific fuel consumption or a cruise speed into
  the propeller equation: the propeller Breguet relation uses the
  power specific fuel consumption in kg/(W s) with the propeller
  efficiency in the numerator, and has no speed term.
- Leaving the PSFC in pounds per horsepower hour: 0.55 lb/hp/h must
  be converted to 9.293e-8 kg/(W s) before the range evaluation, or
  the range comes out wrong by the conversion factor.
- Inverting the mass ratio: m1 >= m0 makes ln(m0/m1) zero, negative
  or undefined, so the sanity gate rejects it.
- Using a fuel fraction of 1 or above: m1 = m0 * (1 - f) leaves no
  vehicle mass, so the derivation rejects the fraction outside [0, 1).
- Reporting a near-full-range burn as infinite: as m1 approaches m0
  the log factor collapses and the range goes to zero, so a tiny
  fuel fraction gives a tiny range, not an unbounded one.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_propeller_range.py

The test covers the worked example anchors (range 1.4722367e6 m and
1472.24 km within the spec bounds, PSFC conversion 9.293e-8 kg/(W s)),
linear scaling with propeller efficiency and inverse scaling with PSFC,
the fuel fraction derivation and its round trip, the fuel fraction
profile against the direct mass ratio form, the near-zero range limit,
the range report keys, determinism, and ValueError rejection of every
non-physical input listed in the Verification section.

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain); the propeller Breguet range relation is common
  range methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

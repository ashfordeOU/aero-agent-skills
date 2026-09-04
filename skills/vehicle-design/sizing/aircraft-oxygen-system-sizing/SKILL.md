---
name: aircraft-oxygen-system-sizing
description: "Use when you must size the aircraft supplemental oxygen system: computing passenger continuous-flow chemical generator demand and unit count, crew diluter-demand gaseous oxygen requirement, converting standard-litre demand volumes to oxygen mass at standard conditions, and sizing crew gaseous oxygen bottle volume from the ideal gas law at the service pressure and storage temperature. Produces the passenger and crew oxygen demands, the generator count, the crew bottle volume and the stored oxygen mass that gate the oxygen system architecture. Trigger: supplemental oxygen sizing, oxygen generator count, oxygen demand mass, oxygen bottle volume, breathing oxygen, diluter-demand, chemical generator, gaseous oxygen."
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
  tags: [aircraft-oxygen-system-sizing, supplemental-oxygen-sizing, oxygen-generator-count, gaseous-oxygen-bottle-volume, oxygen-demand-calculation]
  version: 0.1.0
  author: AeroSkills
---

# Aircraft Oxygen System Sizing (vehicle-design/sizing/aircraft-oxygen-system-sizing)

Use when the task is sizing the supplemental oxygen system of a
transport aircraft at the conceptual level: passenger continuous-flow
chemical oxygen generators (one unit per passenger, TSO-C64 style 22
minute protection) against a crew diluter-demand gaseous oxygen
system, the oxygen demand volume at standard conditions from the
per-occupant flow rate and protection duration, the stored oxygen
mass, and the crew high-pressure bottle volume from the ideal gas law.
This leaf implements that sizing in pure Python, stdlib only. It pairs
with vehicle-design/sizing/environmental-control-sizing, which
produces the governing cabin pressure altitude that this leaf consumes
as the demand driver (the schedule itself lives there; this leaf takes
its altitude result as an input). The aircraft oxygen system sizing
never covers surface thermal protection (ice-protection-sizing) or
seat layout (fuselage-sizing).

## Domain quick reference

- Passenger continuous-flow demand: V_pax = n_pax * q_pax * t_pax in
  standard litres (SL), with q_pax = 5.0 SLPM per passenger and
  t_pax = 22 min of protection per generator unit. The architecture
  supplies one chemical generator unit per passenger.
- Demand mass: m = V * 1e-3 * RHO_O2_STP with RHO_O2_STP = 1.429
  kg/m3, the oxygen density at 0 C and 101.325 kPa (1.429 g per
  standard litre), so m_kg = V_SL * 1.429e-3 exactly.
- Crew diluter-demand: V_crew = n_crew * q_crew * t_crew with q_crew =
  2.5 SLPM average per crew member and t_crew = 120 min (2 h crew
  protection); same volume-to-mass conversion.
- Crew storage: the gaseous oxygen bottle holds the crew demand mass at
  the service pressure. Ideal gas law V = m * R_O2 * T / p with R_O2 =
  259.8 J/(kg K), T = 288.15 K (15 C storage) and p = p_psi *
  6894.757 Pa. The bottle volume is inversely proportional to the
  service pressure at fixed mass and temperature.
- The design cabin pressure altitude sets the demand context: cabin
  partial pressure of oxygen at an 8000 ft cabin altitude is about
  15.8 kPa versus 21.2 kPa at sea level, which is why the altitude
  drives the demand. The altitude itself comes from
  environmental-control-sizing.
- All demand volumes are standard litres at 0 C and 101.325 kPa;
  pressures enter as psi and are converted internally.

## Workflow

1. Fix the occupant split: passenger count n_passengers and crew count
   n_crew (sources: fuselage-sizing for seats, the operator's crew
   complement) and the governing cabin pressure altitude from
   environmental-control-sizing.
2. Decide the delivery architecture: continuous-flow chemical
   generators for passengers, diluter-demand gaseous oxygen for the
   crew.
3. Compute the passenger demand with passenger_demand (volume_sl and
   mass_kg at the default 5.0 SLPM over 22 min) and the generator unit
   count with generator_units, one unit per passenger.
4. Compute the crew demand with crew_demand (default 2.5 SLPM over 120
   min).
5. Size the crew storage with bottle_volume from the crew demand mass,
   the service pressure in psi and the storage temperature; it returns
   volume_m3 and volume_l (for layout, one bottle or two half-size
   bottles).
6. Roll everything up with oxygen_summary(n_passengers, n_crew,
   service_pressure_psi), which returns the passenger demand, the
   generator count, the crew demand, the crew bottle volume and the
   total stored mass.
7. Confirm the deterministic checks with the contract test
   scripts/test_aircraft_oxygen_system_sizing.py.

## Worked example

Reference transport: 150 passengers, 6 crew, crew bottle service
pressure 1800 psi. Real module outputs:

- passenger_demand(150): volume_sl = 16500.0 SL (150 * 5.0 * 22),
  mass_kg = 23.5785 kg (spec bound 23.58 within 1e-1).
- generator_units(150): 150 units, one per passenger.
- crew_demand(6): volume_sl = 1800.0 SL (6 * 2.5 * 120), mass_kg =
  2.5722 kg (spec bound 2.57 within 1e-2).
- bottle_volume(2.5722, 1800): volume_m3 = 0.015516 m3, volume_l =
  15.52 L within 1e-2 of the spec value (2.5722 * 259.8 * 288.15 /
  (1800 * 6894.757) = 0.015516 m3). For layout, one 15.5 L bottle or
  two 7.76 L bottles.
- oxygen_summary(150, 6, 1800): total_mass_kg = 26.1507 kg (23.5785
  passenger + 2.5722 crew), bottle_volume_l = 15.516 L.


## Pitfalls

- Using one architecture for both cabins: passengers get
  continuous-flow chemical generators (one unit per passenger,
  5.0 SLPM over 22 min) while the crew runs on diluter-demand
  gaseous oxygen (2.5 SLPM over 120 min); swapping the flow rates or
  durations mis-sizes both.
- Forgetting the unit conversion in the demand mass: m_kg =
  V_SL * 1.429e-3 exactly (one standard litre of oxygen masses
  1.429 g at 0 C and 101.325 kPa), so a standard-litre volume quoted
  directly as grams is off by 1000.
- Sizing the bottle at the wrong pressure convention: pressures
  enter in psi and are converted internally (1800 psi in the worked
  example); the ideal-gas volume is inversely proportional to the
  service pressure, so a psi-versus-Pa slip mis-sizes the bottle.
- Confusing standard litres with ambient litres: all demand volumes
  are at standard conditions (0 C, 101.325 kPa); an ambient-volume
  demand does not convert through the same density.
- Neglecting the cabin altitude driver: the design cabin pressure
  altitude sets the demand context and comes from
  environmental-control-sizing; this leaf consumes that altitude
  result as an input rather than re-deriving the schedule.
- Feeding non-positive occupants, flows, durations, mass, pressure
  or temperature: every one of these raises ValueError, including
  through the oxygen_summary convenience call.
## Verification

- Confirm passenger_demand(150) returns 16500.0 SL and 23.5785 kg,
  and that doubling the passenger count doubles both the volume and
  the mass.
- Confirm generator_units(150) returns 150 and generator_units(1)
  returns 1.
- Confirm crew_demand(6) returns 1800.0 SL and 2.5722 kg.
- Confirm bottle_volume(2.5722, 1800) returns 0.015516 m3 and
  15.516 L, that doubling the pressure halves the volume and doubling
  the mass doubles the volume.
- Confirm the mass round trip: one standard litre of oxygen masses
  exactly 1.429e-3 kg (mass_kg = volume_sl * 1.429e-3).
- Confirm identical inputs give identical outputs (deterministic).
- Confirm every non-positive n_passengers, n_crew, flow, duration,
  mass, pressure and temperature raises ValueError, including through
  oxygen_summary.
- Confirm the oxygen_summary keys match the documented contract
  exactly: passenger_demand_sl, passenger_mass_kg, generator_units,
  crew_demand_sl, crew_mass_kg, bottle_volume_m3, bottle_volume_l,
  total_mass_kg.
- Run the contract test offline: python3
  scripts/test_aircraft_oxygen_system_sizing.py (34 tests,
  deterministic).

## Related leaves

- vehicle-design/sizing/environmental-control-sizing: produces the
  governing cabin pressure altitude this leaf consumes as the demand
  driver.
- vehicle-design/sizing/fuselage-sizing: seat count and cabin layout
  source for the occupant split.
- vehicle-design/sizing/ice-protection-sizing: surface thermal
  protection, distinct from the breathing oxygen demand sized here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_aircraft_oxygen_system_sizing.py

The test covers the 150 passenger / 6 crew / 1800 psi worked example
within the spec magnitude bounds, the doubling identities (passengers,
pressure, mass), the exact standard-litre mass round trip, the
oxygen_summary convenience keys and values, and ValueError rejection
of every non-physical input class (34 test methods).

## Compliance

- Standards referenced, not reproduced: FAR 25.1443 frames the
  supplemental oxygen context (framing only); the flow, density and
  protection-duration values above are standard engineering design
  practice per the summary-only convention of standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

# Wave-35 leaf spec: aircraft-oxygen-system-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/aircraft-oxygen-system-sizing/
- Pack: sizing. Closest siblings: environmental-control-sizing
  (produces the cabin pressure altitude that this leaf CONSUMES as
  the demand driver; ECS never contains the token "oxygen"),
  fuselage-sizing (seat count and cabin layout source),
  ice-protection-sizing (surface thermal anti-icing; not breathing
  oxygen). Whole-tree grep proves ZERO owners for oxygen, breathing
  oxygen, masks, diluter-demand, chemical generator.
- Standards id: far-25 (reference-only; 25.1443 supplemental oxygen
  context, framing only, no verbatim tables). Ledger Standard:
  far-25.
- Family: vehicle-design

## Claim

Size the aircraft supplemental oxygen system for a transport at the
conceptual level: take the occupant split (passenger count, crew
count) and the governing cabin pressure altitude, decide the
delivery architecture (continuous-flow per-passenger chemical oxygen
generators versus crew diluter-demand gaseous oxygen), compute the
oxygen demand volume at standard conditions from the per-occupant
flow rate and the protection duration, convert the demand volume to
oxygen mass with the standard-condition density, size the crew
high-pressure gaseous oxygen bottle volume from the ideal gas law at
the service pressure and storage temperature, and return the
passenger generator unit count, the crew bottle volume, and the
stored oxygen mass. Produces the passenger and crew demands, the
generator count, the bottle volume and the mass that gate the oxygen
system architecture.

Does NOT do: cabin ventilation, pack airflow, the pressurization
schedule and cabin altitude computation (environmental-control-sizing
owns the schedule; this leaf takes its altitude result as an input);
surface anti-icing bleed (ice-protection-sizing); mask/regulator
hardware geometry; physiological/hypoxia modeling; oxygen
compressors or their electrical power.

## Model (implement exactly)

Module constants:
- R_O2 = 259.8 (J/(kg K), oxygen specific gas constant).
- RHO_O2_STP = 1.429 (kg/m3, oxygen density at 0 C and 101.325 kPa;
  equivalently 1.429 g per standard litre).
- STORAGE_TEMP_K = 288.15 (15 C storage temperature).
- PSI_TO_PA = 6894.757.
- FLOW_PAX_SLPM = 5.0 (continuous-flow litres per minute per
  passenger, design value in FAR 25.1443 context).
- FLOW_CREW_SLPM = 2.5 (average diluter-demand litres per minute per
  crew member, design value).
- PAX_PROTECTION_MIN = 22.0 (minutes of protection per passenger
  generator unit, TSO-C64 practice).
- CREW_PROTECTION_MIN = 120.0 (2 h crew protection duration).

Conventions: all demand volumes are standard litres (SL) at 0 C and
101.325 kPa. The chemical generator architecture supplies one unit
per passenger (per-person continuous flow). The crew system is
gaseous oxygen stored at the service pressure.

Functions (pure stdlib):
- passenger_demand(n_passengers, flow_slpm = FLOW_PAX_SLPM,
  duration_min = PAX_PROTECTION_MIN) -> dict {volume_sl, mass_kg}
  = n * flow * duration and volume * 1e-3 * RHO_O2_STP.
  ValueErrors on non-positive inputs.
- generator_units(n_passengers) -> n_passengers (one per person);
  ValueError: n < 1.
- crew_demand(n_crew, flow_slpm = FLOW_CREW_SLPM,
  duration_min = CREW_PROTECTION_MIN) -> dict {volume_sl, mass_kg}
  same math as passenger_demand. ValueErrors on non-positive inputs.
- bottle_volume(mass_kg, service_pressure_psi, temperature_k =
  STORAGE_TEMP_K) -> dict {volume_m3, volume_l} = m R T / p with p =
  psi * PSI_TO_PA. ValueErrors: mass <= 0, pressure <= 0,
  temperature <= 0.
- oxygen_summary(n_passengers, n_crew, service_pressure_psi) -> dict
  with passenger demand, generator count, crew demand, crew bottle
  volume and total stored mass keys.

Identity to test: doubling the passenger count doubles the passenger
demand volume and mass; the bottle volume is inversely proportional
to the service pressure at fixed mass and temperature; the mass in
kg equals the standard-litre volume times 1.429e-3.

## Worked example

Reference transport: 150 passengers, 6 crew, crew bottle service
pressure 1800 psi.

Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- passenger_demand: 150 * 5.0 * 22 = 16500 SL; mass = 16500 * 1e-3 *
  1.429 = 23.58 kg.
- generator_units: 150.
- crew_demand: 6 * 2.5 * 120 = 1800 SL; mass = 2.57 kg.
- bottle_volume: 2.57 * 259.8 * 288.15 / (1800 * 6894.757) =
  2.57 * 259.8 * 288.15 / 1.24106e7 = 0.01552 m3 = 15.52 L (one
  bottle, or two 7.76 L bottles for layout).
- Context anchor: cabin pO2 at an 8000 ft cabin altitude is about
  15.8 kPa versus 21.2 kPa at sea level, which is why the cabin
  pressure altitude drives the demand (reference framing only).

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: n_passengers <= 0; n_crew <= 0; flow <= 0; duration
  <= 0; mass <= 0; pressure <= 0; temperature <= 0.
- Passenger demand: 150 pax case 16500 SL / 23.58 kg within 1e-1;
  doubling passengers doubles volume; zero duration input raises.
- Generator units: 150 passengers -> 150; 1 passenger -> 1.
- Crew demand: 6 crew case 1800 SL / 2.57 kg within 1e-2.
- Bottle volume: worked case 15.52 L within 1e-2; doubling pressure
  halves the volume; doubling mass doubles the volume.
- Mass round trip: 1 SL of oxygen masses exactly 1.429e-3 kg.
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-aircraft-oxygen-system-sizing.yaml)

Query 1 (copy verbatim):
  "size the passenger oxygen chemical generator count and the crew oxygen bottle volume for a transport aircraft"
  intent: "vehicle-design; passenger oxygen generators and crew oxygen bottle sizing"
  expected_skill: "vehicle-design/sizing/aircraft-oxygen-system-sizing"
Query 2 (copy verbatim):
  "compute the supplemental oxygen demand mass and gaseous oxygen bottle volume from the occupant flow rate and protection duration"
  intent: "vehicle-design; supplemental oxygen demand and bottle volume"
  expected_skill: "vehicle-design/sizing/aircraft-oxygen-system-sizing"
Task ids: w35-aircraft-oxygen-system-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the aircraft
supplemental oxygen system:" and include the outputs in the Claim.
First tag: aircraft-oxygen-system-sizing. Additional tags ONLY:
supplemental-oxygen-sizing, oxygen-generator-count,
gaseous-oxygen-bottle-volume, oxygen-demand-calculation. NEVER
single generic words (oxygen, bottle, generator, flow, mask,
duration). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): cabin ventilation, fresh air,
cabin heat load, pack airflow, pressurization schedule, cabin
altitude limit (environmental-control-sizing); bleed air mass flow,
anti-icing (ice-protection-sizing); seat pitch, cabin length
(fuselage-sizing); hypoxia (out of scope).

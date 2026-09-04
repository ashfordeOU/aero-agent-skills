---
name: density-altitude
description: "Use when you must compute the density altitude from the pressure altitude and the outside temperature: the ISA deviation, the density ratio sigma from the ISA pressure ratio and the temperature ratio, and the density altitude via the troposphere closed-form inverse with the stratosphere branch. Produces the density altitude in meters and feet for hot-day and cold-day takeoff and performance checks. Trigger: density altitude, pressure altitude, outside air temperature, non-standard day, ISA deviation, density ratio, hot day, cold day, takeoff performance, performance reduction."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: cross-cutting
pack: units-atmos
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: units-atmos
  tags: [density-altitude, non-standard-day, isa-deviation, hot-day-performance, density-ratio, inverse-isa, performance-reduction]
  version: 0.1.0
  author: AeroSkills
---

# Density Altitude (cross-cutting/units-atmos/density-altitude)

Use when the task is the density altitude on a non-standard day:
the pressure altitude and the outside air temperature (OAT) collapse
to the altitude the air would occupy on an ISA day, which gates
takeoff distance, climb rate and performance reduction. This leaf
owns the inverse-density step: the ISA deviation, the density ratio
sigma = delta(hp) * T0 / T_oat, and the density altitude from the
troposphere closed-form inverse with the stratosphere branch, in
pure Python stdlib only. It pairs with cross-cutting/units-atmos/
isa-atmosphere, the forward ISA model this leaf inverts, and serves
the domain consumers that previously duplicated this function.

## Domain quick reference

- Constants: T0 = 288.15 K, L = 0.0065 K/m, g = 9.80665 m/s2,
  R = 287.0 J/(kg K), p0 = 101325 Pa, tropopause 11000 m, isothermal
  stratosphere 216.65 K.
- ISA temperature at pressure altitude hp: T0 - L * hp in the
  troposphere, 216.65 K above it (isa_temperature_k).
- ISA pressure ratio: delta(hp) = (1 - L hp / T0)^(g/(R L)) in the
  troposphere, exponential decay from the tropopause state above
  (isa_pressure_ratio).
- ISA deviation: DeltaT = OAT - T_ISA(hp) (isa_deviation_k).
- Density ratio: sigma = delta(hp) * T0 / T_oat. At fixed pressure
  altitude a warm day gives sigma below the ISA value and raises the
  density altitude; a cold day lowers it.
- Troposphere density altitude, closed form:
  h_rho = (T0 / L) * (1 - sigma^e) with e = 1 / (g/(R L) - 1),
  the exact inverse of the density power law (about 0.2349). Note:
  the exponent e equals R L / (g - R L) with the module constants;
  the classical R L / g inverts the pressure law, not the density
  law, and would break the ISA identity, so the exact density
  inverse is used here.
- Stratosphere branch (sigma below the tropopause density ratio):
  h_rho = 11000 - (R * 216.65 / g) * ln(sigma / sigma_trop). The two
  branches meet exactly at the tropopause.
- Units: hp and altitude in meters (ft wrapper accepts feet), OAT in
  kelvin for the meter forms and degrees C for the ft wrapper.

## Workflow

1. Fix the pressure altitude and the OAT at the test point.
2. Read the ISA temperature there with isa_temperature_k.
3. Get the day's non-standard character with isa_deviation_k.
4. Read the ISA pressure ratio with isa_pressure_ratio, then the
   density ratio sigma with density_ratio_from_pressure_temperature
   or the direct product delta * T0 / oat_k.
5. Compute the density altitude with density_altitude_m (meters,
   kelvin) or density_altitude_ft (feet, degrees C).
6. Collect the full set with density_altitude_summary.
7. Confirm the deterministic checks with the contract test.

## Worked example

Module outputs on the spec anchors (real values, R = 287.0):

- ISA identity: density_altitude_m(0, 288.15) = 0.00 m and
  density_altitude_m(3048, isa_temperature_k(3048)) = 3048.00 m
  (h_rho = h_p on the standard day, exact at 10000 ft); the identity
  also holds at the tropopause and in the stratosphere branch.
- Hot day, sea level: OAT 30 C, 15 K above the standard day:
  density_altitude_m(0, 303.15) = 525.34 m,
  density_altitude_ft(0, 30) = 1723.55 ft (about 525.46 m =
  1723.94 ft by the independent check).
- Warm day at 10000 ft pressure altitude, OAT = ISA + 10 K (5.19 C):
  density_altitude_ft(10000, 5.188) = 11159.18 ft, above the
  pressure altitude (about 11159.44 ft by the independent check).
- Cold day at 10000 ft, OAT = ISA - 10 K (-14.81 C):
  density_altitude_ft(10000, -14.812) = 8786.21 ft, below the
  pressure altitude (about 8785.93 ft by the independent check).
- Domain cross-check: density_altitude_ft(10000, 15) = 12247.62 ft,
  reproducing the climb-performance-flight-test bisection result of
  12248.13 ft at OAT 15 C absolute on a 10000 ft pressure altitude.

## Verification

- ISA identity: density altitude equals pressure altitude at 0 m,
  3048 m and the tropopause on the standard day, to 0.2 m.
- Worked magnitudes: sea level OAT 30 C about 525.4 m / 1723.6 ft;
  10000 ft ISA +10 K about 11159 ft; ISA -10 K about 8786 ft.
- Monotonicity: at fixed pressure altitude a warmer OAT raises the
  density altitude and a colder one lowers it; at fixed OAT a higher
  pressure altitude raises it.
- Closed form versus 200-iteration bisection of the forward ISA
  density law agrees to 1e-6 on both the troposphere and the
  stratosphere branches; the branch switch is continuous.
- Determinism: identical outputs run to run, no RNG, offline.
- ValueError rejection: pressure altitude below -1000 m (small
  negative geopotential is allowed) and OAT at or below 0 K.
- Run the contract test offline: python3
  scripts/test_density_altitude.py (35 tests, deterministic).

## Related leaves

- cross-cutting/units-atmos/isa-atmosphere: the forward ISA state
  model this leaf inverts.
- cross-cutting/units-atmos/airspeed-conversion: takes pressure
  altitude as input and pairs with the density altitude for air-data
  reduction.
- flight-test-operations/performance/climb-performance-flight-test:
  the domain consumer that previously duplicated this function.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_density_altitude.py

The test covers the module constants and sea-level anchors, the ISA
temperature and pressure ratio branches, the ISA deviation, the
density ratio from pressure and temperature, the ISA identity at
0 m, 3048 m, the tropopause and in the stratosphere, the worked
magnitude anchors (sea level OAT 30 C, 10000 ft ISA +10 K and
ISA -10 K), the domain-precedent cross-check at 10000 ft OAT 15 C,
monotonicity in temperature and pressure altitude, closed-form
agreement with an independent 200-iteration bisection on both
branches, continuity across the tropopause branch switch, ValueError
rejection of non-physical inputs including the -1000 m boundary,
the ft wrapper against the meter form, the exact summary dict key
set and its consistency with the functions, and run-to-run
determinism.

## Compliance

- Standards referenced, not reproduced: ECSS frames the atmosphere
  reference context; the ISA model is common reference data and the
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

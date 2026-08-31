---
name: unit-conversion
description: "Use when you must convert aerospace quantities between SI and imperial or aviation units: length (m, ft, NM), speed (m/s, kt, ft/s, Mach), temperature (K, C, F, R), pressure (Pa, hPa, psi, inHg), density (kg/m3, slug/ft3), mass (kg, lb, slug), and force (N, lbf). Converts with a deterministic factor table, handles offset temperature scales, computes Mach from true airspeed and speed of sound, and relates pressure altitude to geometric altitude. Trigger: unit conversion, convert units, knots, mach number, temperature conversion, pressure altitude, SI imperial."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: units-atmos
  tags: [unit-conversion, convert-units, knots, mach-number, temperature-conversion, pressure-altitude, si-imperial]
  version: 0.1.0
  author: AeroSkills
---

# Unit Conversion (cross-cutting/units-atmos/unit-conversion)

Use when the task is converting an aerospace quantity between unit
systems: SI to imperial, imperial to SI, or to the aviation units
pilots and flight manuals use (knots, NM, inHg, Mach).

## Domain quick reference

Deterministic factor tables, one canonical base per quantity
(m, m/s, K, Pa, kg/m3, kg, N). Exact where the unit system defines
them; standard reference values otherwise.

- Length (base m): 1 ft = 0.3048 m; 1 NM = 1852 m.
- Speed (base m/s): 1 kt = 1852/3600 = 0.514444 m/s; 1 ft/s = 0.3048
  m/s. Mach converts through a speed of sound; the default is the ISA
  sea-level value 340.294 m/s, pass the flight-condition value for
  altitude-corrected Mach.
- Temperature (base K, offset scales, not factors): K = C + 273.15;
  F = K * 9/5 - 459.67; R = K * 9/5. Anchor: 0 C = 273.15 K = 32 F =
  491.67 R.
- Pressure (base Pa): 1 hPa = 100 Pa; 1 psi = 6894.757293168 Pa;
  1 inHg = 3386.389 Pa. ISA sea level is 101325 Pa = 1013.25 hPa =
  29.92 inHg = 14.6959 psi.
- Density (base kg/m3): 1 slug/ft3 = 515.3788184 kg/m3; ISA sea level
  is 1.225 kg/m3 = 0.0023769 slug/ft3.
- Mass (base kg): 1 lb = 0.45359237 kg; 1 slug = 14.59390294 kg =
  32.1740 lb.
- Force (base N): 1 lbf = 0.45359237 kg * 9.80665 m/s2 =
  4.4482216152605 N.
- Altitude conventions: pressure altitude inverts the ISA troposphere
  pressure field (what an altimeter set to 1013.25 hPa reads);
  geometric altitude converts to geopotential altitude with the
  nominal Earth radius 6356766 m: h_gp = h * R / (R + h).

## Workflow

1. Name the quantity and the two units involved.
2. Pick the matching function: convert_length, convert_speed,
   convert_temperature, convert_pressure, convert_density,
   convert_mass, convert_force.
3. Pass value, from_unit, to_unit. Unit tokens are case-insensitive;
   "NM", "kts", "kg/m^3" all resolve.
4. For Mach, pass the speed of sound at the flight condition, or
   accept the ISA sea-level default.
5. For altitude, use pressure_altitude_m on a static pressure, or
   convert_altitude between geom and geopotential.
6. Sanity-check the result against the quick-reference anchors
   (e.g. 1013.25 hPa, 1.225 kg/m3, 250 kt about 129 m/s).

## Pitfalls

- Treating temperature as a plain factor: 0 C is not 32 F minus an
  offset; the code routes every temperature through kelvin.
- Mach without a speed of sound: the default is ISA sea level; at
  altitude the speed of sound drops and Mach rises for the same
  true airspeed.
- Confusing pressure altitude with geometric altitude, or geometric
  with geopotential (the difference is about 19 m at 11 km).
- Confusing slug with lb (factor 32.1740) and NM with statute miles
  or km.
- Mixing gauge pressure with absolute pressure; the tables here are
  absolute.
- Writing "kph" or "mph": not in the table by design, raises
  ValueError, convert via m/s first.

## Behavior contract (gate 3)

The conversion logic is exercised by the gate 3 contract test:
scripts/test_unit_conversion.py against
scripts/unit_conversion_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_unit_conversion.py

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is public-domain
  US government work; this skill uses only its standard-atmosphere
  context (sea-level state, speed of sound, pressure altitude) as
  common reference data, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

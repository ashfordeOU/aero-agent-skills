---
name: isa-atmosphere
description: "Use when you must apply the international standard atmosphere in aerospace calculations: read temperature, pressure, and density at altitude from the ISA model, from sea level through the tropopause and lower stratosphere. Produces the atmospheric state values at the requested altitude for performance and flight mechanics work. Trigger: standard atmosphere, isa, atmospheric density, temperature lapse, pressure altitude, troposphere."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: units-atmos
  tags: [standard-atmosphere, isa, atmospheric-density, temperature-lapse, pressure-altitude, troposphere]
  version: 0.1.0
  author: Aero Agent Skills
---

# ISA Standard Atmosphere (cross-cutting/units-atmos/isa-atmosphere)

Use when the task is the international standard atmosphere:
temperature, pressure, and density at altitude for performance and
flight mechanics calculations.

## Domain quick reference

- ISA sea level: 288.15 K, 101325 Pa, density about 1.225 kg/m3.
- Troposphere: temperature lapses 6.5 K per km up to 11 km.
- Lower stratosphere: isothermal at 216.65 K from 11 to 20 km.
- Pressure integrates the hydrostatic balance with the lapse rate.

## Workflow

1. Pick the altitude and the needed state variable.
2. Read temperature with isa_temperature_k.
3. Read pressure with isa_pressure_pa.
4. Read density with isa_density_kgm3.
5. Confirm the sea-level anchor with isa_sea_level.

## Pitfalls

- Using a linear pressure falloff instead of the lapse-rate
  integral.
- Reading a constant temperature above the tropopause as a lapse.
- Taking the model beyond its 20 km range.

## Behavior contract (gate 3)

The temperature, pressure, and density logic is exercised by the
gate 3 contract test: scripts/test_isa_atmosphere.py against
scripts/isa_atmosphere_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_isa_atmosphere.py

## Compliance

- Standards referenced, not reproduced: ECSS text is copyright
  ESA; the ISA model here is common reference data, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

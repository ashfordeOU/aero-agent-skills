---
name: temperature-conversion
description: "Use when you must convert temperatures between the kelvin, celsius, fahrenheit, and rankine scales for a test or an analysis: convert absolute temperatures with the scale offsets and ratios, convert temperature differences with the degree sizes only, and check the result against the absolute zero limit of each scale. Produces the converted absolute temperature or the converted temperature difference that gates the thermal data exchange. Trigger: temperature conversion, kelvin, celsius, fahrenheit, rankine, absolute zero, temperature difference, delta temperature."
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
  tags: [temperature-conversion, kelvin, celsius, fahrenheit, rankine, absolute-zero, delta-temperature, temperature-scale]
  version: 0.1.0
  author: Aero Agent Skills
---

# Temperature Conversion (cross-cutting/units-atmos/temperature-conversion)

Use when the task is converting temperatures between the kelvin,
celsius, fahrenheit, and rankine scales: absolute temperatures with
the scale offsets and ratios, temperature differences with the
degree sizes only, and the absolute zero limit of each scale. The
general aerospace quantity conversion table (knots, pressure, Mach)
lives in the unit-conversion leaf; this leaf is the dedicated
temperature scale logic.

## Domain quick reference

- Scale pivots: 0 C is 273.15 K, 32 F, and 491.67 R; absolute zero
  is 0 K, 0 R, -273.15 C, and -459.67 F.
- Celsius to kelvin adds 273.15; celsius to fahrenheit applies the
  9/5 ratio plus the 32 offset; rankine uses fahrenheit-sized
  degrees from absolute zero.
- Degree sizes: one kelvin equals one celsius degree; one rankine
  equals one fahrenheit degree; one kelvin equals 9/5 rankine.
- Absolute temperature conversion routes every scale through kelvin,
  so the physical temperature is invariant across the scales.
- Temperature differences use only the degree sizes: a ten celsius
  degree change is an eighteen fahrenheit degree change.
- A temperature below the absolute zero of its scale is physically
  meaningless; the logic raises ValueError.

## Workflow

1. Identify whether the input is an absolute temperature or a
   temperature difference: a difference carries no scale offset.
2. For an absolute temperature, call convert_temperature(value,
   from_unit, to_unit) with the unit letters k, c, f, or r.
3. For a temperature difference, call convert_delta(value,
   from_unit, to_unit) with the same unit letters.
4. Check the result against the absolute zero of the target scale
   before gating the thermal data exchange.

## Pitfalls

- Applying the 32 offset to a temperature difference: only absolute
  temperatures carry the offset; a difference uses degree sizes
  only, so ten celsius degrees are eighteen fahrenheit degrees.
- Mixing up the degree sizes: one kelvin is 9/5 rankine, not 5/9.
- Using the wrong scale letter: the logic accepts k, c, f, and r
  only, case-insensitive; full names like kelvin raise ValueError.
- Accepting a temperature below absolute zero: the logic raises
  ValueError; zero kelvin and zero rankine are the lower bounds.
- Duplicating the unit-conversion leaf: general quantity conversion
  (knots, pressure, density, mass) belongs to unit-conversion; this
  leaf covers the temperature scales.

## Behavior contract (gate 3)

The scale, offset, and delta logic is exercised by the gate 3
contract test: scripts/test_temperature_conversion.py against
scripts/temperature_conversion_logic.py (stdlib unittest, offline).
Run:

python3 scripts/test_temperature_conversion.py

## Compliance

- NACA Report 824 is US government work (public domain); the pack
  anchor per standards-map.yaml. The four temperature scales and
  their conversion factors are common engineering conventions, not
  RTCA or SAE content; summary and formulas only.
- compliance: STANDARDS-REF, gated: false.

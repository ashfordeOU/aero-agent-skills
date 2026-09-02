---
name: fuel-tank-sizing
description: "Use when you must size the fuel tanks for the aircraft: convert the fuel mass to the fuel volume with the fuel density, add the ullage allowance to get the required tank volume, and check it against the available volume in the wing and fuselage tanks. Produces the usable fuel volume, the required tank volume with ullage, and the fits verdict that gate the fuel system sizing. Trigger: fuel tank sizing, ullage, fuel volume, usable fuel, tank capacity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [fuel-tank-sizing, fuel-volume, usable-fuel, ullage, fuel-density, tank-capacity, fuel-mass]
  version: 0.1.0
  author: Aero Agent Skills
---

# Fuel Tank Sizing (vehicle-design/sizing/fuel-tank-sizing)

Use when the task is sizing the fuel tanks at the conceptual level:
converting the fuel mass into a fuel volume with the fuel density,
adding the ullage allowance to get the required tank volume, and
checking that volume against the volume available in the wing and
fuselage tanks.

## Domain quick reference

- Fuel volume is the fuel mass divided by the fuel density; jet fuel
  density is commonly about 0.8 kg per liter, or 800 kg per cubic
  meter.
- Volume units: liters for tank bookkeeping, cubic meters for the
  wing box and fuselage volume checks; one cubic meter is 1000
  liters.
- Ullage is the allowance for fuel expansion and tank venting space,
  added on top of the usable fuel volume; typical values are a few
  percent of the usable volume.
- Required tank volume: usable fuel volume times (1 + ullage
  fraction).
- The fits verdict subtracts the required tank volume from the
  available volume; a non-negative margin fits, and the margin
  percent is relative to the required volume.
- Fuel tank sizing sits in the FAR-25 / CS-25 fuel system context
  (fuel quantity, unusable fuel, and expansion space for the tank).

## Workflow

1. Collect the fuel mass in kg, the fuel density in kg per liter, the
   ullage fraction, and the available tank volume in liters.
2. Compute the usable fuel volume with fuel_volume_liters (and the
   cubic meter value with fuel_volume_m3 for the structure check).
3. Add the ullage allowance with tank_volume_with_ullage, or use
   required_tank_volume directly.
4. Check the required volume against the available volume with
   check_available_volume and read the fits verdict.

## Pitfalls

- Mixing density units: 0.8 kg per liter is 800 kg per cubic meter;
  using the wrong one changes the volume by a factor of 1000.
- Forgetting the ullage allowance: the tank must hold the fuel plus
  the expansion and venting space, not the fuel alone.
- Checking against the total aircraft volume instead of the volume
  actually available in the wing box and fuselage tanks.
- Passing a zero fuel mass or a negative ullage; the module raises
  ValueError instead of guessing.

## Behavior contract (gate 3)

The volume conversion, ullage, required tank volume, and fits verdict
logic are exercised by the gate 3 contract test:
scripts/test_fuel_tank_sizing.py against
scripts/fuel_tank_sizing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fuel_tank_sizing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the volume and
  ullage calculations are common fuel system sizing methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

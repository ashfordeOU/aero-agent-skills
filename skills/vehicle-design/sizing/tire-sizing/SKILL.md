---
name: tire-sizing
description: "Use when you must size the tires for an aircraft landing gear at the conceptual level: split the static load per tire from the takeoff weight, the gear load share, and the tire count, compute the tire diameter and width with the power law fit, select the number of tires from the load capacity per tire, set the inflation pressure, and compute the footprint contact area and the rolling radius. Produces the tire dimensions, the required tire count, and the footprint that gate the landing gear configuration. Trigger: tire sizing, tire diameter, tire width, static load per tire, number of tires, inflation pressure, footprint, rolling radius."
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
  tags: [tire-sizing, tire, tires, tire-diameter, tire-width, static-load, inflation-pressure, tire-pressure, footprint, rolling-radius, number-of-tires, wheel, wheels]
  version: 0.1.0
  author: Aero Agent Skills
---
# Tire Sizing (vehicle-design/sizing/tire-sizing)

Use when the task is selecting the tires for the landing gear at the
conceptual level: the static load per tire, the tire diameter and
width estimates, the number of tires, the inflation pressure, and the
footprint and rolling radius that come out of the load.

## Domain quick reference

- The static load per tire is the gear load share of the takeoff
  weight divided by the number of tires on that gear. Worked: a
  78,000 kg transport with 0.95 of the weight on the main gear and 4
  main tires carries 78000 * 0.95 / 4 = 18,525 kg per tire, which is
  40,841 lb.
- Tire diameter and width are estimated with power law fits of the
  form dimension = coeff * load**exponent on the load per tire in
  pounds. Representative class-I fit values: diameter = 1.63 *
  P**0.315 and width = 0.40 * P**0.36, giving 46.2 in (1174 mm)
  diameter and 18.3 in (464 mm) width at 40,841 lb. The fits are
  estimates: the final tire comes from the tire catalog and the wheel
  rating.
- The footprint contact area is the load per tire divided by the
  inflation pressure: 40,841 lb at 200 psi gives 204.2 sq in. Main
  tire inflation pressures for transports commonly fall in the 150 to
  220 psi band.
- The rolling radius is half the tire diameter: 23.1 in (587 mm) for
  the 46.2 in tire.
- The required number of tires on a gear is the gear load total
  divided by the maximum load capacity per tire, rounded up: 163,363
  lb on the main gear at 45,000 lb per tire gives 4 tires.
- Nose gear worked example: 0.10 of the weight and 2 nose tires give
  3,900 kg per tire (8,598 lb) and a 28.3 in (719 mm) diameter tire.
- Tire and wheel selection sits in the FAR-25 / CS-25 context,
  including the wheel and tire rating and landing gear drop test
  requirements (25.723, 25.733, 25.735).

## Workflow

1. Collect the takeoff weight, the gear load share fraction (for
   example 0.95 main gear and 0.10 nose gear), the number of tires on
   the gear, and the inflation pressure.
2. Compute the load per tire with static_load_per_tire(mtow_kg,
   gear_fraction, n_tires) and convert it to pounds with kg_to_lb.
3. Estimate the dimensions with tire_diameter_inches(load_lb) and
   tire_width_inches(load_lb).
4. Select the tire count with required_number_of_tires(gear_load_lb,
   max_load_per_tire_lb) from the gear load total and the catalog
   capacity.
5. Compute the footprint with footprint_area_sqin(load_lb,
   pressure_psi) and the rolling radius with
   rolling_radius_inches(diameter_in).
6. Close with the catalog check: pick the catalog tire whose rating
   covers the static load per tire at the selected pressure.

## Pitfalls

- Routing strut load distribution here: the CG-based nose and main
  gear load share, the shock absorber stroke, and the tire rating
  margin check against an existing tire belong to the
  landing-gear-sizing sub-skill; this leaf starts from the per-tire
  static load and selects the tire itself.
- Routing ground handling questions here: braking friction,
  cornering, and traction coefficients belong to the performance
  leaves, not to tire geometry sizing.
- Treating the power law fit as a catalog value: the fit is a class-I
  estimate; the final tire must come from the tire catalog with the
  rating checked against the static load per tire.
- Mixing units: the fits are pound-inch curve fits; convert kg to lb
  (1 kg = 2.20462 lb) and inches to mm (1 in = 25.4 mm) before
  comparing with a metric catalog.
- Rounding the tire count down: the required number of tires rounds
  up; a fractional division result means one more tire is needed.
- A gear fraction above 1: one gear cannot carry more than the total
  weight; the logic raises ValueError instead of guessing.
- Passing a zero load, a zero pressure, or a non-integer tire count:
  the logic raises ValueError.

## Behavior contract (gate 3)

The load split, power law dimension fits, footprint, rolling radius,
and tire count logic are exercised by the gate 3 contract test:
scripts/test_tire_sizing.py against scripts/tire_sizing_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_tire_sizing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the wheel and
  tire rating and landing gear drop test requirements frame the tire
  sizing context, and the power law fits are common conceptual design
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

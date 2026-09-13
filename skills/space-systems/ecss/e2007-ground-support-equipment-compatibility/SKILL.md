---
name: e2007-ground-support-equipment-compatibility
description: "Use when verify that electrical and mechanical ground-support-equipment around a spacecraft during integration-and-test leaves its electromagnetic compatibility intact under ECSS-E-ST-20-07C clause 4.2.9: categorize each item as electrical-ground-support-equipment or mechanical-ground-support-equipment, sum the bond-path segment resistances against the bond-resistance-ceiling, move each radiated-emission level to the real stand-off distance and margin-check it and every umbilical-line conducted-emission against the vehicle susceptibility-limit, derive the reference-potential-difference a return-current raises on that bond, place a contacting handling-fixture in the electrostatic-bleed-path window, and flag any item lacking a compatibility-verification-status. Trigger: ecss, e-st-20-electrical-scope, ground-support-equipment, electrical-ground-support-equipment, mechanical-ground-support-equipment, bond-resistance-ceiling, umbilical-line-emission, electrostatic-bleed-path."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e2007-ground-support-equipment-compatibility, ground-support-equipment, electrical-ground-support-equipment, mechanical-ground-support-equipment, bond-resistance-ceiling, umbilical-line-emission, electrostatic-bleed-path, reference-potential-difference]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Ground-Support-Equipment Compatibility (space-systems/ecss/e2007-ground-support-equipment-compatibility)

Use when the task is the clause 4.2.9 obligation of ECSS-E-ST-20-07C: the
racks, umbilicals, trolleys and handling-fixtures that surround a spacecraft
on the integration floor are themselves part of its electromagnetic
environment, and none of them is allowed to degrade the compatibility the
flight design was qualified to.

## Domain quick reference

- Ground-support-equipment splits into two families with different checks.
  An electrical item (a stimulus rack, a power-feed, an umbilical, a
  check-out console) is bonded and can inject energy, so it carries the
  bond-path, emission and reference-potential checks. A mechanical item (a
  handling-fixture, a container, a trolley, a lifting-device) is checked for
  the electrostatic-bleed-path it presents wherever it touches flight
  hardware. An item type belonging to neither family is not evaluated.
- The bond path is a chain, not a single joint: the strap, the clamp and the
  interface each contribute resistance, and the number that matters is their
  sum against the bond-resistance-ceiling. A chain built from compliant
  individual joints can still exceed the ceiling, which is why the sum is
  the governed quantity.
- Emission levels are declared at a reference distance and have to be moved
  to the stand-off distance the item actually occupies on the floor before
  they mean anything. In decibel terms the move is twenty times the base-ten
  logarithm of the distance ratio; an item declared benign at three metres
  is not benign at half a metre.
- Compatibility is a margin, not a pass. The emission, once moved to the
  real distance, is compared with the vehicle susceptibility-limit and the
  difference has to reach the programme compatibility margin. The same
  comparison runs for every conducted level injected on an umbilical-line.
- The bond resistance also sets the reference-potential-difference the
  return-current raises between the item reference and the vehicle
  reference. That product is checked against the safe interface potential,
  because a bond that merely meets the ceiling can still float a sensitive
  interface when a large return-current flows through it.
- A contacting mechanical item needs a dissipative surface, not an extreme
  one. Too insulating and it cannot bleed away triboelectric charge; too
  conductive and it becomes a low-resistance path across a powered
  interface. The check is membership of a resistivity window with a finding
  named for the side that was crossed.
- Clause 4.2.9 is satisfied per activity, not per item in the abstract. An
  item with no compatibility-verification-status on record cannot be brought
  into a powered activity, and a waived item needs the rationale recorded
  with the waiver.

## Workflow

1. Categorize every item in the activity as an electrical or a mechanical
   ground-support-equipment family member; reject an unrecognised item type
   before any computation runs.
2. For an electrical item, sum the declared bond-path segment resistances
   and compare the total against the bond-resistance-ceiling, absorbing
   floating-point round-off exactly at the ceiling rather than widening it.
3. Multiply that bond resistance by the expected return-current to obtain
   the reference-potential-difference, and compare it with the safe
   interface potential.
4. Move each declared radiated-emission level from its reference distance to
   the item's stand-off distance, then compute the margin against the
   vehicle radiated-susceptibility-limit and check it against the required
   compatibility margin.
5. Repeat the margin check for every conducted level declared on an
   umbilical-line against the interface conducted-susceptibility-limit.
6. For a mechanical item that contacts flight hardware, place its surface
   resistivity in the dissipative window and record which side was crossed
   when it is not.
7. Check the compatibility-verification-status of every item taking part in
   the activity, and require a recorded rationale for any waiver.
8. Aggregate: the activity is compatible only when no item carries a bond,
   potential, emission, bleed-path or verification finding.

## Pitfalls

- Checking each bond joint against the ceiling instead of the chain total.
  Three joints that each pass can sum past the ceiling, and the sum is what
  the vehicle sees.
- Comparing a declared emission level against the susceptibility-limit
  without moving it to the real stand-off distance. Datasheet levels are
  quoted at a reference distance and understate a rack parked close to the
  vehicle by twenty times the logarithm of the ratio.
- Reading a bond that meets the ceiling as automatically safe for a
  sensitive interface. With a large return-current even a small resistance
  lifts the reference by a potential the interface cannot tolerate.
- Treating a highly conductive handling-fixture surface as the safest
  option. The bleed-path window is bounded on both sides, and an
  over-conductive contact is its own hazard across a powered interface.
- Relaxing the required compatibility margin so an exactly-on-margin item
  passes. An item that lands precisely on the required margin is compliant;
  the fix is to absorb decibel representation error at the comparison.
- Letting an unverified item into a powered activity because its numbers
  look reasonable. Clause 4.2.9 asks for the compatibility to be shown, so
  an absent verification record is the finding itself.

## Behavior contract (gate 3)

The item categorization, bond-path summation, reference-potential,
distance-scaled emission, margin, electrostatic-bleed-path window and
verification-status logic is exercised by the gate 3 contract test:
scripts/test_e2007_ground_support_equipment_compatibility.py against
scripts/e2007_ground_support_equipment_compatibility_logic.py (stdlib
unittest, offline, deterministic). Run:
python3 scripts/test_e2007_ground_support_equipment_compatibility.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

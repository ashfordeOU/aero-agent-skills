---
name: e3311-gse-test-equipment-launch-site-items
description: "Allocate the explosive-subsystem requirements of ECSS-E-ST-33-11C clause 4.13 to the items that are not flight hardware. Use when the task is deciding what ground support equipment, test equipment and launch-site items owe once they touch an explosive item: deriving the requirement set from what the item contacts and energizes and from where it operates, capping instrument fault current at a fraction of the no-fire current, grading bond resistance and personnel separation, and screening a whole inventory so no item is left ungraded. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-gse-requirement-applicability, eed-test-instrument-fault-current, launch-site-explosive-item-controls, firing-circuit-gse-safing, ground-support-bonding-resistance-limit."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-gse-test-equipment-launch-site-items, explosive-gse-requirement-applicability, eed-test-instrument-fault-current, launch-site-explosive-item-controls, firing-circuit-gse-safing, ground-support-bonding-resistance-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — GSE, Test Equipment and Launch-Site Items (space-systems/ecss/e3311-gse-test-equipment-launch-site-items)

Use when the task is the external-item requirement of ECSS-E-ST-33-11C
clause 4.13 -- deciding which of the requirements written for flight
explosive hardware also bind the ground support equipment, the test
equipment and the launch-site items that handle, energize or sit
alongside it, and grading each of those items against the ones that
carry a number.

## Domain quick reference

- The clause exists because the hazard does not stop at the flight
  interface. An item that never leaves the ground can still fire an
  initiator, and the requirement set it owes is derived from what it
  touches and what it can energize, not from the fact that it is not
  flight hardware.
- Applicability is a function of three declarations: the item kind,
  whether it contacts an explosive item, and whether it can put energy
  into one. Energizing without contacting is not a coherent
  declaration and is rejected rather than interpreted.
- Bonding and grounding bind every item on the list. An ungrounded
  trolley, jig or rack is a charge reservoir near an initiator, so the
  requirement has no exemption tier.
- Test equipment carries a limit the other kinds do not: any current an
  instrument can drive into a bridgewire, including under a first
  fault, is held to a small fraction of the no-fire current. A meter
  that measures the bridgewire is the one instrument routinely placed
  across the hazard.
- Launch-site location adds requirements rather than relaxing them.
  Lightning protection, the radio-frequency environment and personnel
  separation are properties of the place, so an item qualified in an
  integration hall inherits them again when it moves to the pad.
- A screen is only worth the coverage of its inventory. Every item has
  to come out with a requirement set and a verdict, and an item whose
  numbers were not supplied is an open finding, never a silent pass.

## Workflow

1. Declare each item: its kind, whether it contacts an explosive item,
   whether it can energize one, and whether it operates at the launch
   site. Reject an item that energizes without contacting.
2. Derive the requirement set for the item from those declarations,
   keeping the rationale with each requirement so the allocation can be
   read back rather than trusted.
3. Where the item is test equipment that can energize an initiator, cap
   its worst-case fault current at the policy fraction of the no-fire
   current and grade the declared fault current against that cap.
4. Grade the measured bond resistance of every item against the ground
   support limit, and reject a negative or non-numeric reading rather
   than treating it as zero.
5. For launch-site items, grade the declared personnel separation
   against the minimum, and record lightning and radio-frequency
   controls as duties the item now carries.
6. Screen the whole inventory, count the items graded against each
   requirement, and report every item whose numbers were missing as an
   open finding alongside the ones that failed.

## Pitfalls

- Reading the clause as applying only to items that fire something. A
  handling trolley never energizes an initiator and still owes bonding
  and shock control, so scoping the screen to firing equipment drops
  most of the inventory.
- Grading an instrument's normal measuring current and stopping there.
  The number that matters is the current the instrument can drive under
  a fault, and a meter that is safe in normal use can be a firing
  source with one component short.
- Grading a fault current directly against the no-fire current. The
  no-fire current is where initiation begins; the instrument limit sits
  a declared fraction below it, and using the no-fire value as the
  limit removes the whole margin.
- Treating launch-site qualification as inherited. The environment adds
  lightning, radio-frequency and separation requirements that the
  integration hall never imposed, so an item cleared indoors is not
  cleared at the pad.
- Letting an item with no supplied numbers fall out of the screen. An
  ungraded item reads as a pass in a count, and the count is what gets
  reported, so a missing measurement has to surface as a finding.
- Comparing a fault current or a bond resistance with its limit by bare
  arithmetic. Both limits are products of declared terms, so a case
  that sits exactly on the limit can land a few units in the last place
  the wrong side of it; the comparison absorbs that while the limit
  stays untouched.

## Behavior contract (gate 3)

The requirement allocation, instrument fault-current cap, bond
resistance grading, personnel separation screen and the inventory-wide
verdict are exercised by the gate 3 contract test:
scripts/test_e3311_gse_test_equipment_launch_site_items.py against
scripts/e3311_gse_test_equipment_launch_site_items_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3311_gse_test_equipment_launch_site_items.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

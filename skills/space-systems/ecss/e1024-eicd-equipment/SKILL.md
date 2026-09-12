---
name: e1024-eicd-equipment
description: "Use when produce an Equipment-level Interface Control Document (EICD) for a space-segment equipment item per ECSS-E-ST-10-24C §5.8.1: inventory all equipment interfaces, categorize each as electrical (pin/signal/connector), mechanical (envelope/attachment/mass), or thermal (dissipation/contact resistance/temperature range), validate pin-level signal data per connector, detect duplicate pin assignments, confirm mechanical and thermal field completeness, and flag any interface category absent from the EICD record. Trigger: ecss, e-st-10-24c, eicd, equipment-interface, pin-assignment, mechanical-interface, thermal-interface."
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
  tags: [ecss, e-st-10-24c, eicd, equipment-interface, pin-assignment, mechanical-interface, thermal-interface]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — Equipment-Level EICD (space-systems/ecss/e1024-eicd-equipment)

Use when the task is to produce or validate an Equipment-level Interface
Control Document (EICD) per ECSS-E-ST-10-24C §5.8.1 — capturing every
interface exposed by a space-segment equipment item across three interface
families: electrical (pin/signal/connector), mechanical
(envelope/attachment/mass), and thermal (dissipation/contact
resistance/temperature range).

## Domain quick reference

- §5.8.1 requires that every equipment item in the space segment carries a
  dedicated EICD covering all three interface families. An EICD with one
  family absent is incomplete regardless of how thoroughly the other two
  are specified.
- Electrical interfaces are defined at pin level: each connector has a
  connector identifier, a connector type (e.g. D-Sub, DSUB-MIL, SMA), and
  a pin table where every row carries a pin identifier, signal name,
  direction (in/out/bidir/power/return/nc), nominal voltage, and worst-case
  current. Duplicate pin identifiers within one connector are a data
  integrity error.
- Mechanical interfaces record the physical envelope (bounding box in mm),
  the attachment pattern (bolt/stud pattern, PCD, interface standard), and
  the item mass in kg. A negative mass value is unphysical and must be
  rejected.
- Thermal interfaces record the maximum steady-state power dissipation in
  watts, the allowable operating temperature range in degrees Celsius, and
  the thermal interface resistance (theta, K/W) at the mounting surface.
  Negative dissipation or negative theta values are unphysical.
- An EICD is compliant when every interface record is complete, all
  electrical pin tables are free of duplicates and carry valid direction
  codes, and all three interface families are present.

## Workflow

1. Identify the equipment item and assign it a unique equipment identifier;
   reject any record lacking an identifier before proceeding.
2. Enumerate all physical interfaces of the equipment and assign each a type
   (electrical, mechanical, thermal). Any interface type not in those three
   families cannot be categorized and must be reported before continuing.
3. For each electrical connector: record the connector identifier and
   connector type, then populate the pin table. Validate that every pin row
   carries all required fields (pin_id, signal_name, direction, voltage_v,
   current_ma) and that direction is one of the recognized codes. Scan for
   duplicate pin identifiers within the connector.
4. For each mechanical interface: confirm the attachment pattern,
   three-dimensional envelope, and mass are all present. Reject negative
   mass values.
5. For each thermal interface: confirm dissipation, temperature range, and
   thermal interface resistance are present. Reject negative dissipation or
   negative theta values.
6. Verify that at least one electrical, one mechanical, and one thermal
   interface record exists in the EICD; flag each absent family as a
   separate finding.
7. Declare the EICD compliant only when the findings list is empty.

## Pitfalls

- Omitting the thermal interface because it seems implicit — §5.8.1 mandates
  an explicit thermal record; a missing thermal block is a non-conformance,
  not an editorial gap.
- Treating an incomplete pin table as a minor issue — a pin row missing its
  direction code cannot be used by an integrating subsystem to determine
  drive/load topology, so it is a blocking finding.
- Accepting duplicate pin identifiers as "harmless aliases" — two pins with
  the same identifier make the table ambiguous and break automated harness
  generation tools.
- Applying unit assumptions when fields are absent — if mass_kg is missing,
  do not assume zero; flag the absence and reject the record.

## Behavior contract (gate 3)

The interface-categorization, pin-validation, duplicate-detection,
mechanical-validation, thermal-validation, and EICD-completeness logic
is exercised by the gate 3 contract test:
scripts/test_e1024_eicd_equipment.py against
scripts/e1024_eicd_equipment_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1024_eicd_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

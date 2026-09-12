---
name: production-and-manufacturing-control
description: "Use when verify production and manufacturing controls for structural
  hardware under ECSS-E-ST-32 section 4.7: confirm each manufacturing process is
  authorized and documented, engineering drawings are at the correct revision and
  change-controlled, tooling is qualified and traceable, assembly procedures include
  acceptance criteria and traveler records, storage conditions satisfy material
  specifications, cleanliness levels are defined and monitored, and health-and-safety
  hazards are identified with active mitigations. Flag any process without
  authorization, drawing at a superseded revision, unqualified tool, missing
  acceptance criterion, storage exceedance, undefined cleanliness level, or
  unmitigated hazard before hardware advances to the next build phase. Trigger:
  ecss, e-st-32-structures-scope, manufacturing-control, production-control,
  tooling-qualification, assembly-procedures, cleanliness-control, health-and-safety."
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
  tags: [ecss, e-st-32-structures-scope, manufacturing-control, production-control, tooling-qualification, assembly-procedures, cleanliness-control, health-and-safety]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Production and Manufacturing Control (space-systems/ecss/production-and-manufacturing-control)

Use when the task is verifying the production and manufacturing controls for
structural hardware under ECSS-E-ST-32 section 4.7 — checking that every
manufacturing process, drawing, tool, assembly procedure, storage arrangement,
cleanliness requirement, and health-and-safety provision is in a compliant state
before hardware advances to the next build phase.

## Domain quick reference

- ECSS-E-ST-32 section 4.7 requires that all manufacturing processes applied to
  structural hardware be explicitly authorized and supported by a process document.
  Processes without authorization must cause a manufacturing hold; processes with
  pending status are treated the same way.
- Engineering drawings must be at the current approved revision before use. A
  drawing at a superseded revision introduces an uncontrolled configuration risk
  and must be updated before any manufacturing action proceeds against it.
- Tooling and fixtures used to produce or inspect structural hardware must be
  qualified and carry a traceability reference (calibration or qualification
  record). An unqualified tool may introduce undetected dimensional errors.
- Assembly procedures must include explicit acceptance criteria and a traveler
  record. Acceptance criteria define the pass/fail boundary for each assembly
  operation; the traveler records actual measured values and operator signatures.
  A procedure lacking either is incomplete and must not be used for acceptance.
- Storage conditions (temperature, humidity) must remain within the material
  specification limits throughout the storage period. Moisture or temperature
  exceedances can degrade composite matrices, adhesives, and seals before
  they are installed.
- Cleanliness levels must be defined for every item where contamination affects
  structural or functional performance, and active monitoring must confirm the
  level is maintained. An item with an undefined cleanliness level has no
  measurable compliance baseline.
- Every health-and-safety hazard associated with a manufacturing operation (toxic
  substances, pressure systems, cryogenic handling, energetic processes) must
  have a documented mitigation and that mitigation must be confirmed in place
  before work begins.

## Workflow

1. Inventory every manufacturing process to be applied to the hardware item.
   For each process, confirm its authorization status and the existence of a
   supporting process document. Categorize each process as authorized,
   pending, or unauthorized. Reject any process that is not authorized before
   work begins.
2. For each engineering drawing referenced by the work order, compare the
   revision on the shop floor to the latest approved revision in the
   configuration management system. Flag any drawing at a superseded revision
   and halt work on the affected feature until the current revision is in use.
3. For each tool or fixture in the work package, verify the qualification status
   and retrieve the traceability reference (calibration certificate or
   qualification report number). Flag unqualified tools and tools with no
   traceability reference; remove them from the build station until the
   deficiency is resolved.
4. For each assembly procedure, confirm that explicit acceptance criteria are
   stated for every operation and that a traveler record template is present.
   Flag any procedure missing either element; the procedure must be revised
   before it can be used for formal acceptance.
5. For each stored hardware item, record the actual temperature and relative
   humidity in the storage environment and compare against the material
   specification limits. Flag any parameter outside its allowed range and
   initiate the non-conformance process immediately.
6. For each hardware item where cleanliness matters (optical interfaces, bonded
   surfaces, sealing faces, load-bearing fastener holes), confirm a cleanliness
   level is defined and that active monitoring (particle counts, visual
   inspection records) is in place. Flag any item with an undefined or
   unmonitored cleanliness level.
7. For each identified health-and-safety hazard associated with the manufacturing
   operations, confirm a mitigation is documented and confirmed implemented.
   A hazard with no mitigation plan or with an unconfirmed mitigation must block
   the associated operation until the mitigation is verified.
8. Aggregate all findings. The production and manufacturing control review is
   complete only when every finding list is empty. Any open finding must be
   resolved and re-checked; do not carry findings forward to the next build phase.

## Pitfalls

- Treating a process as compliant because it has been used before without
  checking that the current work order references an authorized revision of the
  process document — re-authorization is required when the process document
  is updated.
- Accepting a drawing at a superseded revision on the grounds that the
  differences are "minor" — any difference between revisions is a configuration
  change that must be formally assessed; informal judgements are not acceptable.
- Skipping the traceability check for tooling that is visually undamaged —
  physical condition is not a substitute for a calibration record; a tool can be
  dimensionally out of tolerance without visible damage.
- Declaring storage compliant based on a single spot-check reading — storage
  conditions must be monitored continuously or at the frequency required by the
  material specification, not just at the time of inspection.
- Assuming a cleanliness level is satisfied because the cleanroom meets its
  rated class — the item itself must be monitored; the ambient class does not
  guarantee the item's surface cleanliness.
- Closing a health-and-safety finding when a mitigation is written but before
  it is physically verified as in place — the confirmed-in-place state is the
  only acceptable closure criterion.

## Behavior contract (gate 3)

The process authorization, drawing revision, tooling qualification, assembly
procedure, storage condition, cleanliness level, and hazard mitigation logic
is exercised by the gate 3 contract test:
scripts/test_production_and_manufacturing_control.py against
scripts/production_and_manufacturing_control_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_production_and_manufacturing_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

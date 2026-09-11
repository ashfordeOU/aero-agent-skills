---
name: e10-coordsys-units
description: "Use when engineering data across an ECSS-E-ST-10C programme (system level) needs to be checked for consistent use of reference coordinate systems per E-ST-10-09 and SI units, before it is exchanged between disciplines, suppliers, or verification/operations teams. Trigger: coordinate system, reference frame, SI units, unit consistency, coordinate systems document, CSD, E-ST-10-09, frame consistency, ecss, e-st-10c."
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
  tags: [ecss, e-st-10c, coordinate-systems, si-units, csd, consistency, frames, transformations]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Reference Coordinate System & SI Unit Consistency (space-systems/ecss/e10-coordsys-units)

Use when the task is checking that engineering data produced across an
ECSS-E-ST-10C programme -- by system, subsystem, or supplier teams --
uses reference coordinate systems per E-ST-10-09 and SI units
consistently, ahead of exchange between disciplines or hand-off to
verification and operations.

## Domain quick reference

- ECSS-E-ST-10C clause 5.6.5 requires that reference coordinate systems
  be applied per E-ST-10-09 and that SI units be used consistently
  across the programme, as a system-engineering-function
  responsibility alongside interface control (5.6.4) and technical
  budget consolidation (5.6.6).
- E-ST-10-09 owns the detailed frame definitions, notation, and the
  Coordinate Systems Document (CSD) that records the programme's
  approved frames, transformations, and per-quantity units (see the
  sibling e1009-* leaves: e1009-documentation for the CSD itself,
  e1009-csys/e1009-units for frame and unit definitions,
  e1009-chain-analysis for transformation chains). This leaf does not
  redefine that content; it checks that engineering data actually in
  use is consistent with it.
- A unit is consistent if it is the SI unit for its quantity (metre,
  kilogram, second, radian, and their combinations), or if a
  non-SI unit is used and the exception is explicitly documented
  (e.g. a heritage subsystem still reporting pressure in bar).
- A coordinate frame reference is consistent if it is one of the
  frames the programme has approved and recorded in the CSD; a frame
  invented ad hoc by a discipline team outside the CSD control loop is
  a nonconformance, not a valid alternative.

## Workflow

1. Obtain the programme's approved reference frame set from the
   current CSD (E-ST-10-09, maintained by the sibling
   e1009-documentation leaf).
2. For each engineering data item to check, capture: an identifier,
   its quantity type (length, mass, time, angle, velocity,
   acceleration, force, temperature, pressure, frequency, angular
   rate), the unit it is expressed in, the reference frame it is
   expressed against, and whether any non-SI unit use carries a
   documented exception.
3. Check the unit: compare it against the canonical SI unit for the
   item's quantity type; accept a mismatch only when the exception is
   documented.
4. Check the frame: confirm it is a member of the programme's approved
   frame set from the CSD.
5. Build the consistency audit across all data items in scope, keyed
   by item id, recording which of unit/frame (or both) is violated;
   an item with no violations does not appear in the audit.
6. Separately, scan all frames actually referenced in the data against
   the approved set to surface any frame that is missing a CSD
   definition entirely, not just misused.
7. Route unit violations and undocumented-exception cases back to the
   originating discipline for correction or exception sign-off; route
   frame violations and missing frame definitions to the E-ST-10-09
   coordinate system owner (e1009-responsibility) for CSD update or
   correction.

## Pitfalls

- Treating a non-SI unit as acceptable because it is common practice
  in a discipline, without a documented exception on record.
- Letting a discipline or supplier team introduce a convenient local
  frame instead of routing it through the CSD control loop, producing
  silent transformation errors downstream.
- Auditing only the data items already known to be problematic instead
  of the full data set, which misses the "consistently across the
  programme" scope of clause 5.6.5.
- Confusing this system-level consistency check with the detailed
  frame/unit definition work of E-ST-10-09 (owned by the sibling
  e1009-* leaves) -- this leaf verifies usage, it does not define
  frames or units.

## Behavior contract (gate 3)

The unit-check, frame-check, programme-audit, and missing-frame-
definition logic is exercised by the gate 3 contract test:
scripts/test_e10_coordsys_units.py against
scripts/e10_coordsys_units_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_coordsys_units.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

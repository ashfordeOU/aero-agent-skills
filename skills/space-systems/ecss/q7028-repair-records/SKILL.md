---
name: q7028-repair-records
description: "Audit the record a repair or modification of a printed circuit board assembly leaves behind under ECSS-Q-ST-70-28C: score the mandatory header fields, require a location that names a side and a reference designator or grid rather than prose, require an approved method with the revision of the procedure that was followed, require every material to carry a batch and a shelf life still valid on the day it was used, match the verification activities recorded against the set the method demands, read the authorization, repair and verification dates in order, and check the retention period. Use when auditing repair paperwork or closing a board out. Trigger: ecss, q-st-70-28c, board-repair-record-audit, repair-location-identification, repair-material-batch-traceability, repair-verification-record-set, repair-record-chronology."
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
  tags: [ecss, q-st-70-28c-pcb-repair-and-modification, q-st-70-28c, q7028-repair-records, board-repair-record-audit, repair-location-identification, repair-material-batch-traceability, repair-verification-record-set, repair-record-chronology, board-repair-record-retention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS PCB Repair — Repair Records (space-systems/ecss/q7028-repair-records)

Use when the task is the documentation clause of ECSS-Q-ST-70-28C: what has to
be written down when a printed circuit board assembly is repaired or modified
— where on the board the work was done, by what method, with which materials,
and what verification followed — and whether a record in hand actually carries
it.

## Domain quick reference

- The record is the only durable evidence the repair happened the way it was
  meant to. The board looks the same whether the procedure was followed or
  not, so a record that omits a field has removed that field from the
  qualification argument, not merely from the paperwork.
- A location is a side plus an identifier. A reference designator or a grid
  reference on a named side finds the work years later; a sentence of prose
  describing the neighbourhood does not, and it is prose that is written when
  the repair is fresh and obvious to everybody present.
- A procedure number without a revision does not say which text was followed.
  Procedures are revised precisely because the earlier text was wrong about
  something, so the revision is the part that carries the information.
- A material without a batch cannot be traced. When a batch is later found to
  be out of specification, the recall list is built from these entries, and a
  record naming only the material type puts the whole fleet on the list.
- Shelf life is checked against the day of use, not the day of the audit. A
  material that expired after the repair was in date when it mattered, and a
  material that expired before it was not, however recent the record looks.
- The verification set belongs to the method. An eyelet needs a radiographic
  view that a jumper does not; a land rebuild needs a pull test that no other
  method needs. Recording a generic visual check against every method leaves
  the method-specific failure unexamined.
- Dates have to run in order. A repair dated before its authorization and a
  verification dated before the repair are both records of something other
  than what they claim, and both are common transcription failures.

## Workflow

1. Score the mandatory header fields, counting a blank entry as missing.
2. Test the location for a valid side and for a reference designator or a
   well-formed grid reference; report prose-only locations.
3. Test the method against the approved set and require the procedure
   revision alongside the procedure reference.
4. Test each material for a designation, a batch and an expiry date, and
   compare the expiry against the repair date rather than today.
5. Resolve the verification set the method requires, report each required
   activity that is absent, and report a recorded activity that belongs to a
   different method.
6. Read the authorization, repair and verification dates in order.
7. Check the retention period against the years the record is kept.
8. Return the findings grouped by the part of the record they came from, with
   a completeness score over the groups.

## Pitfalls

- Describing the repair location instead of identifying it. The description
  is unambiguous only to the people standing at the bench that afternoon.
- Recording the procedure number and leaving the revision blank. The audit
  then cannot tell whether the superseded text or the corrected one was used.
- Listing materials by type with no batch. Traceability is the whole purpose
  of the entry, and a type name traces to the entire stores holding.
- Checking shelf life against the audit date. A material long expired now may
  have been perfectly in date on the day it was applied, and the reverse.
- Copying one verification list onto every method. The method-specific check
  is the one that catches the method-specific failure, and it is the one that
  gets dropped.
- Leaving the authorization date off because the authorization reference is
  present. The reference proves an authorization exists, not that it existed
  before the work.
- Treating the record as complete because no field is blank. Fields can be
  filled with values that contradict each other, and the chronology check is
  what catches that.

## Behavior contract (gate 3)

The header scoring, location identification, approved method and revision,
material batch and shelf-life checks against the day of use, method-specific
verification set, date chronology, retention period and the grouped
completeness score are exercised by the gate 3 contract test:
scripts/test_q7028_repair_records.py against
scripts/q7028_repair_records_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7028_repair_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

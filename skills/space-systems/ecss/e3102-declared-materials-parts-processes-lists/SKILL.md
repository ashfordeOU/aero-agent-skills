---
name: e3102-declared-materials-parts-processes-lists
description: "Maintain the declared materials, mechanical parts and processes lists ECSS-E-ST-31-02 clause 5.2 and its content table require of two-phase heat transport equipment: group every entry into its own list, reject a reused item identifier, test each entry against the mandatory fields that list owes, demand a recorded compatibility basis from anything the working fluid wets, and track approval separately from completeness so a refused item and an unfinished one are not confused. Use when a heat pipe or loop heat pipe build has to get its declared lists under control before a review. Trigger: ecss, e-st-31-02-two-phase, two-phase-declared-materials-list, declared-mechanical-parts-list, declared-processes-list, fluid-wetted-material-compatibility, non-condensable-gas-generation, declared-list-approval-status."
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
  tags: [ecss, e-st-31-02-two-phase, e3102-declared-materials-parts-processes-lists, two-phase-declared-materials-list, declared-mechanical-parts-list, declared-processes-list, fluid-wetted-material-compatibility, non-condensable-gas-generation, declared-list-approval-status]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase — Declared Materials, Parts and Processes Lists (space-systems/ecss/e3102-declared-materials-parts-processes-lists)

Use when the task is the declared-list duty of ECSS-E-ST-31-02 clause
5.2 -- compiling the materials, mechanical parts and processes that go
into a heat pipe or loop heat pipe, and keeping them under control
rather than merely written down.

## Domain quick reference

- Three lists are kept: the declared materials list, the declared
  mechanical parts list and the declared processes list. They are
  separate registers, so the same identifier may legitimately appear
  once in each, and twice in one is a control defect.
- Each list carries a common core -- item identifier, designation,
  specification reference, supplier, approval status -- plus fields of
  its own. Materials owe a form and lot traceability; parts owe a part
  number and lot traceability; processes owe a process specification
  and the operator qualification behind it.
- The concern peculiar to two-phase hardware is fluid wetting. Any
  material the working fluid touches has to carry a recorded
  compatibility basis, naming the fluid it was assessed against. An
  incompatible wetted material generates non-condensable gas, the gas
  collects in the condenser, and transport capability decays over years
  in a way an acceptance test at delivery would never have shown.
- Completeness and approval fail independently and are tracked
  separately. A complete entry can still be unapproved, and an approved
  entry can still be missing the fields that would let anyone check
  what was approved.
- A refused item is not the same as a pending one. Refused means the
  item cannot stay in the build; pending means the customer still has
  to act. Both keep the lists open, but only one is a design change.
- A list with no entries at all is a finding in its own right. A build
  with no declared processes has not been surveyed; it has been
  overlooked.

## Workflow

1. Take the declaration as typed entries, each naming its list and its
   item identifier. Reject an entry whose list is not one of the three,
   rather than filing it somewhere plausible.
2. Group the entries by list and refuse a reused identifier inside any
   one list, while allowing the same identifier across two lists.
3. Test each entry against the mandatory fields of its own list,
   counting a blank string as absent rather than present.
4. Grade the wetted items: a compatibility basis has to be recorded and
   the fluid it was assessed against has to be named. Both are needed;
   an assessment against a different fluid is not evidence for this
   one.
5. Read approval status separately, sorting refused items into the
   uncontrolled set and pending items into a list of customer actions.
6. Report per-list totals, controlled counts, the uncontrolled
   identifiers and the wetted items, and close controlled only when no
   finding stands anywhere.

## Pitfalls

- Treating an approved entry as a complete one. Approval was given
  against whatever was submitted, and an entry missing its lot
  traceability cannot be tied back to what was actually approved.
- Recording fluid compatibility without naming the fluid. A compatible
  pairing is a property of the material AND the fluid; the same alloy
  that is sound with one fluid generates gas with another.
- Leaving a process off the list because it leaves no part behind.
  Cleaning, passivation and fill processes touch the wetted surfaces
  directly and are exactly the ones that decide gas generation.
- Filing a refused item alongside a pending one. Pending is an action on
  the customer; refused is a design change on the supplier, and merging
  the two hides the work that actually has to happen.
- Reporting an empty list as nothing to declare. A two-phase build with
  no declared processes has not been surveyed, and the empty list is
  the evidence of that rather than a clean result.

## Behavior contract (gate 3)

Entry validation, per-list mandatory field checks, fluid compatibility
assessment, grouping with duplicate rejection, approval tracking, list
summaries and the control verdict are exercised by the gate 3 contract
test: scripts/test_e3102_declared_materials_parts_processes_lists.py
against scripts/e3102_declared_materials_parts_processes_lists_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3102_declared_materials_parts_processes_lists.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q6005-delivery-data-documentation
description: "Audit the documentation handed over with a delivered lot of hybrid microcircuits and decide whether it evidences the manufacture and test history of every unit shipped, under ECSS-Q-ST-60-05 clause 13.2. Use when a data package is assembled or reviewed before despatch: grade each record group by the state it arrives in, find the history phases no usable record speaks for, match the delivered serials against the traceability index, test the nonconformance and rework records against what the lot actually went through, and return the documentation-coverage index with one verdict. Trigger: ecss, q-st-60-05, delivery-data-documentation, hybrid-delivery-record-groups, hybrid-manufacture-history-phase-gap, hybrid-serial-traceability-index, hybrid-documentation-coverage-index, hybrid-delivery-package-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-delivery-data-documentation, hybrid-delivery-record-groups, hybrid-manufacture-history-phase-gap, hybrid-serial-traceability-index, hybrid-documentation-coverage-index, hybrid-delivery-package-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Delivery Data Documentation (space-systems/ecss/q6005-delivery-data-documentation)

Use when the task is clause 13.2 of ECSS-Q-ST-60-05: the records assembled to
evidence the manufacture and testing history of the units actually being
delivered — the set as a whole, not the format rules it obeys or the cover
sheets and certificate that sit on the front of it.

## Domain quick reference

- The delivery documentation is a chain, not a pile. Materials and chips,
  assembly, in-process inspection, screening, lot acceptance and final test
  each leave a record group behind, and a chain with a phase nobody evidenced
  does not describe the units that were shipped.
- A record group that exists is not a record group that covers the shipment.
  Every delivered serial has to resolve in the traceability index; a package
  that documents forty of forty-two units documents forty units, and the other
  two travel with no history at all.
- A record for a unit that is not in the shipment is a finding in its own
  right. It means the index and the packing list were built from different
  lists, and neither can now be trusted on its own.
- Legibility and completeness are graded, never assumed. A group supplied as an
  unreadable or partial copy earns part credit, because a reviewer can see it
  was produced without being able to use it — and for a mandatory group that
  is a deficiency, not an observation.
- Nonconformances and rework belong in the package. A lot that raised
  nonconformances and hands over no nonconformance records has a hole exactly
  where the risk is, and an approved waiver nobody referenced is invisible to
  the next reader.
- The general format and retention provisions, the cover sheets, the
  certificate of conformity and the packing are each graded against their own
  clauses; this leaf grades whether the history is there.

## Workflow

1. Name the lot and collect the shipment: the delivered serials, and the
   serials the traceability index actually reaches.
2. Collect the record groups the package carries and the state each one
   arrives in — supplied, observed, partial, illegible or absent.
3. Grade every group against the full published set, so a group nobody
   mentioned is graded as not supplied, and mark the mandatory ones.
4. Take weighted credit over total weight as the documentation-coverage index.
5. Map the usable groups onto the history phases and report, in order, every
   phase no usable group speaks for.
6. Difference the delivered serials against the indexed serials both ways:
   undocumented units, and records for units nobody shipped.
7. Test the lot history against the package — nonconformances against
   nonconformance records, rework against rework records, approved waivers
   against the references listed.
8. Name the verdict — incomplete while a mandatory group is absent, deficient
   on an unevidenced phase, an undocumented unit, a stray record, an unusable
   mandatory group, a history finding or a low index, complete with open
   actions while findings remain, complete only when none do.

## Pitfalls

- Counting documents instead of reading them. A package with every group
  present and one of them illegible evidences less than the count suggests,
  and the count is what most reviews report.
- Checking the traceability index one way. Units missing from the index are
  the obvious failure; records for units that were never shipped are the one
  that shows the two lists were built independently.
- Treating the rework records as optional paperwork. They are optional only
  for a lot that was never reworked, and the lot history is what decides that,
  not the assembler's preference.
- Accepting a waiver that is approved but unreferenced. The approval lives in
  someone else's file; unless the package points at it the delivered unit
  looks non-compliant to every later reader.
- Grading the phase chain from the group names. A group that arrived partial
  or illegible carries a name and no evidence, and a phase covered only by
  such a group is bare.
- Confusing this clause with the general provisions. Retention period, medium
  and format live one clause down; a package can be perfectly formatted and
  still evidence nothing.

## Behavior contract (gate 3)

The record-group grading, the documentation-coverage index, the history-phase
chain, the two-way serial reconciliation, the lot-history checks and the
package verdict are exercised by the gate 3 contract test:
scripts/test_q6005_delivery_data_documentation.py against
scripts/q6005_delivery_data_documentation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6005_delivery_data_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

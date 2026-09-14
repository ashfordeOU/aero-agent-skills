---
name: q6013-procurement-test-table-selection
description: "Determine which per-family procurement test matrix governs a commercial part under ECSS-Q-ST-60-13C clause 8.2: resolve the part family from the component type and the technology together rather than from either field alone, map that family to its procurement test table, split the table into the test groups applicable at the declared assurance class and the groups the class defers, report applicability as a fraction judged under a named tolerance, detect a multifunction part that pulls in a second table before the purchase order goes out, and reconcile every proposed waiver against the groups that actually apply. Use when a part has to be matched to its procurement test table. Trigger: ecss, q-st-60-13c-clause-8-2, procurement-test-table-selection, commercial-part-family-resolution, class-dependent-test-applicability, multifunction-part-table-conflict, procurement-test-waiver-reconciliation."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-procurement-test-table-selection, q-st-60-13c-clause-8-2, commercial-part-family-resolution, procurement-test-matrix-selection, class-dependent-test-applicability, multifunction-part-table-conflict, procurement-test-waiver-reconciliation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial Parts — Procurement Test Table Selection (space-systems/ecss/q6013-procurement-test-table-selection)

Use when the task is the procurement testing provision of ECSS-Q-ST-60-13C
clause 8.2 — deciding which of the per-family test matrices a given
commercial electrical, electronic and electromechanical part is bought
against, and which rows of that matrix the declared assurance class actually
calls for.

## Domain quick reference

- The matrix is chosen per family, not per part. Every downstream argument
  about what was tested starts from which table was picked, so a wrong table
  is not a wrong test — it is a whole wrong test programme.
- The family is named by two fields together. A technology token is ambiguous
  on its own: a film capacitor and a film resistor share the word and share
  no matrix. A component type is ambiguous the other way, splitting across
  technologies whose matrices differ.
- The table is the superset; the class picks the rows. A table carrying seven
  test groups may call for two of them at the lowest assurance level, so the
  applicable set and the deferred set are reported separately and always
  partition the table exactly.
- Applicability is reported as a fraction of the table, which makes two parts
  of different families comparable and makes a class change visible as a
  number rather than as a re-read of the matrix.
- A multifunction part is the trap. A device that is also an optocoupler, or
  a module carrying a relay, resolves into more than one family and therefore
  more than one table; the conflict is cheap to settle before the purchase
  order and expensive after delivery.
- A waiver is only meaningful against a group that applies. Waiving a group
  the class already defers changes nothing and hides the waivers that do
  change something; waiving a group the table never carried is a drafting
  error in the purchase order.

## Workflow

1. Validate the part: part number, component type, technology, declared
   assurance class, and any waivers the procurement proposes.
2. Resolve the family from the component type and technology pair, refusing a
   pair no family is defined for rather than guessing from one field.
3. Map the family to its procurement test table and list the table's groups
   in table order.
4. Split the table into the groups applicable at the declared class and the
   groups the class defers, and express applicability as a fraction.
5. Resolve every additional function the part carries, and report the second
   table as a conflict to be settled when one appears.
6. Reconcile the proposed waivers into unknown, already-deferred and
   effective, and report the selection with a verdict carrying every finding.

## Pitfalls

- Selecting on the technology word alone. Film, hybrid and discrete each
  appear under more than one component type or resolve to different matrices.
- Reading the whole table as the test programme. At the lower assurance
  classes most of a table is deferred, and buying the whole table is as wrong
  as buying two rows of it.
- Treating a multifunction part as its dominant function. The second family
  brings its own table, and silence about it is what surfaces at incoming
  inspection.
- Counting a redundant waiver as a relaxation. It measures nothing and
  crowds out the waiver that really did relax an applicable group.
- Comparing test counts across families. Tables differ in length, which is
  why the fraction rather than the count is the comparable quantity.
- Stopping at the first finding. The buyer needs the table, the class split
  and every waiver problem in one pass, before the order is placed.

## Behavior contract (gate 3)

The part validation, family resolution from the type and technology pair,
table mapping, class-dependent applicable and deferred split, applicability
fraction, multifunction table-conflict detection, waiver reconciliation and
the overall settled-selection verdict are exercised by the gate 3 contract
test: scripts/test_q6013_procurement_test_table_selection.py against
scripts/q6013_procurement_test_table_selection_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q6013_procurement_test_table_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

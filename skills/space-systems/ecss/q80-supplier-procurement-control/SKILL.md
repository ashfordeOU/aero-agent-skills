---
name: q80-supplier-procurement-control
description: "Audit supplier selection and the control of procured and customer-furnished software under ECSS-Q-ST-80C Rev.2: grade a supplier selection record, build and check the flow-down package a lower-level supplier receives for its role, criticality category and security sensitivity, grade supplier monitoring by milestone, check each procured item for ordering and receiving inspection criteria, backup solution, contract terms, configuration registration and exportability, run a receiving inspection that hashes the delivered image against the order, and grade the justification of operational ground equipment and services. Use when software is subcontracted or bought in for a space project. Trigger: q80-supplier-procurement-control, procured-software, receiving-inspection, supplier-selection, customer-furnished-software, ground-equipment-selection."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.4.1.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.4.1.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.4.2.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.4.2.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.4.3.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.4.3.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.4.3.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.4.3.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.4.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.4.5
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.5.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.5.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.5.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.5.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.5.5
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 5.5.6
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.4.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.4.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.4.3
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.4.4
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 7.4.5
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-80c, q80-supplier-procurement-control, procured-software, receiving-inspection, supplier-selection, customer-furnished-software, ground-equipment-selection, software-procurement-data]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Software Supplier and Procurement Control (space-systems/ecss/q80-supplier-procurement-control)

Use when the task is the buyer's side of ECSS-Q-ST-80C Rev.2 (30 April
2025): choosing a software supplier and controlling what it delivers
(clause 5.4), procuring software items (clause 5.5), and choosing ground
computers and support services for the operational system (clause 7.4).
Software the customer hands over is existing software and gets the same
treatment. How the assurance plan describes supplier control is graded by
`q80-software-product-assurance-plan`; this skill checks the records.

## Domain quick reference

- Selection follows the general quality assurance standard: a pre-award
  audit or assessment and a record of the procurement source. A supplier
  offering existing software, including software inside an off-the-shelf
  unit, makes its reuse analysis available before it is chosen.
- The flow-down is tailored to the supplier's role. A developer or
  maintainer receives assurance requirements and the obligation to write
  its own assurance plan, and those requirements go to the customer for
  acceptance before the system requirements review (SRR). Every supplier
  learns the category of what it builds, the higher-level failures it can
  cause, and its security sensitivity with the attack scenarios behind it.
- Monitoring means reviewing and approving the supplier's plan and passing
  it to the customer by the preliminary design review (PDR), checking
  process and product continuously, and following the supplier's final
  validation.
- Each procured item carries its ordering criteria (version, options,
  security certifications), receiving inspection criteria, a backup plan
  if the product disappears, contract terms for maintenance and upgrades,
  and country of origin where the customer asks for it. It is registered
  under configuration management, inspected on receipt and checked for
  export constraints.
- Ground computers and services for operations are justified against
  performance, maintenance, lifetime, category and sensitivity, support,
  warranty, copyright, availability, compatibility and site constraints;
  services also need service levels and escalation.

## Workflow

1. Grade each supplier selection record with `grade_supplier_selection`.
   Selection follows the supplier-selection rules of ECSS-Q-ST-20 (its
   clause 5.4.1): a pre-award audit or assessment on file and a record of
   the procurement source.
2. Where the candidate offers existing software, including software
   inside an off-the-shelf unit or equipment, check that its reuse
   analysis was in hand before the choice: the case for reuse, the
   assessment against the functional, performance, quality and security
   requirements, the quality-level analysis, the reuse file entry and the
   suitability assessment.
3. For each lower-level supplier, run `build_flowdown`: assurance
   requirements tailored to the supplier's role, among them the
   obligation to write its own software product assurance plan; the
   criticality category of what it builds and the failures it can cause
   at higher level, from the dependability and safety analyses; and its
   security sensitivity with the failures, attacks and security effects
   it can cause at higher level during development and in operation, from
   the security analyses.
4. Compare the package actually sent with `check_flowdown_package`, and
   confirm the flowed-down assurance requirements went to the customer
   for acceptance before the system requirements review (SRR).
5. At each milestone, run `check_supplier_monitoring` per supplier: the
   supplier's conformance to its assurance requirements is followed; its
   assurance plan was reviewed and approved, then passed to the customer
   for acceptance by the preliminary design review (PDR); its development
   processes are defined and actually applied as that plan says; its
   processes and products are checked continuously; and its final
   validation is followed.
6. Check the procurement documents follow ECSS-Q-ST-20 (its clause
   5.4.2), and that the choice of each procured product is described and
   was put to the customer for review.
7. List every procured and customer-furnished item and run
   `check_procured_item` on each: ordering criteria (version, options,
   security certifications), receiving inspection criteria, a backup if
   the product stops being available, contract terms for development,
   maintenance and upgrades, country of origin when the customer asks for
   it, registration under configuration management, and the export
   constraints identified.
8. On delivery, run `receiving_inspection` with the delivered bytes
   against the inspection criteria of step 7, as a planned inspection
   under ECSS-Q-ST-20 (its clause 5.4.4), and record the digest in the
   configuration file.
9. For operational ground equipment, confirm hardware is subcontracted and
   bought under the same ECSS-Q-ST-20 procurement rules (its clause 5.4)
   with receiving inspection reports, then run `check_ground_selection`:
   the choice is justified against performance, maintenance, durability
   and consistency with the operational equipment, category and security
   sensitivity, the security regulations and standards that apply,
   support documentation, acceptance and warranty, installation and
   training, maintenance and evolution, copyright, availability,
   compatibility and site constraints, and it covers the constraints of
   both developing and using the software.
10. For operational support services, check the justification covers
    service levels, quality of service and escalation, and that the
    provider's product and support policy lets the hardware and the
    services be kept going for the whole specified life of the software.
11. Send the findings to the reviewer as a draft.

## Obligations

| Item | Step |
|---|---|
| ECSS-Q-ST-80C Rev.2 5.4.1.1a | 1 |
| ECSS-Q-ST-80C Rev.2 5.4.1.2a | 2 |
| ECSS-Q-ST-80C Rev.2 5.4.2.1a | 3 |
| ECSS-Q-ST-80C Rev.2 5.4.2.2a | 4 |
| ECSS-Q-ST-80C Rev.2 5.4.3.1a | 5 |
| ECSS-Q-ST-80C Rev.2 5.4.3.2a | 5 |
| ECSS-Q-ST-80C Rev.2 5.4.3.3a | 5 |
| ECSS-Q-ST-80C Rev.2 5.4.3.4a | 5 |
| ECSS-Q-ST-80C Rev.2 5.4.4a | 3 |
| ECSS-Q-ST-80C Rev.2 5.4.5a | 3 |
| ECSS-Q-ST-80C Rev.2 5.5.1a | 6 |
| ECSS-Q-ST-80C Rev.2 5.5.2a | 6 |
| ECSS-Q-ST-80C Rev.2 5.5.3a | 7 |
| ECSS-Q-ST-80C Rev.2 5.5.4a | 7 |
| ECSS-Q-ST-80C Rev.2 5.5.5a | 8 |
| ECSS-Q-ST-80C Rev.2 5.5.6a | 7 |
| ECSS-Q-ST-80C Rev.2 7.4.1a | 9 |
| ECSS-Q-ST-80C Rev.2 7.4.2a | 10 |
| ECSS-Q-ST-80C Rev.2 7.4.3a | 9 |
| ECSS-Q-ST-80C Rev.2 7.4.4a | 9 |
| ECSS-Q-ST-80C Rev.2 7.4.5a | 10 |

## Pitfalls

- Flowing down the category and forgetting the sensitivity and the
  failure information that explains it.
- Asking an off-the-shelf vendor for an assurance plan it will never
  write, instead of covering it by the reuse file and inspection.
- Accepting a delivery by its label; the digest and the version are what
  was ordered or they are not.
- Treating customer-furnished software as already assured.
- Leaving export constraints to the end, when they can block the
  architecture.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- Selection or rejection of a supplier.
- Acceptance or return of a delivered software item.
- The procured component list and the flow-down package sent to the
  customer or a supplier.

Mark every such output as a draft, list the open questions for the
reviewer, and end with the line: STOP: human sign-off required before
submission.

## Behavior contract (gate 3)

The selection grading, the flow-down builder and package check, the
monitoring check by milestone, the procured item check, the receiving
inspection with its computed digest and the ground equipment selection
check are exercised by the gate 3 contract test:
scripts/test_q80_supplier_procurement_control.py against
scripts/q80_supplier_procurement_control_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q80_supplier_procurement_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

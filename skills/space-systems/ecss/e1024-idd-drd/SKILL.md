---
name: e1024-idd-drd
description: "Use when generate or validate an Interface Definition Document (IDD) or single-end ICD under ECSS-E-ST-10-24C Annex C: confirm each interface record carries a recognized type and status, verify that every record names its mating item and supplies non-empty interface characteristics, flag any agreed interface that lacks a bilateral ICD reference, surface superseded entries without a successor reference, tally interfaces by status, and decide whether the IDD is complete. Trigger: ecss, e-st-10-system-scope, idd, interface-definition-document, single-end-icd, interface-type, icd-reference, mating-item, interface-status."
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
  tags: [ecss, e-st-10-system-scope, idd, interface-definition-document, single-end-icd, icd-reference, annex-c-drd, interface-type]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — Interface Definition Document DRD (space-systems/ecss/e1024-idd-drd)

Use when the task is to generate or validate the Interface Definition
Document (IDD) of ECSS-E-ST-10-24C Annex C -- the record that captures,
interface by interface, the full characteristics of every connection point
owned by a product, and that may serve as a single-end ICD until bilateral
agreement is reached.

## Domain quick reference

- Annex C defines the IDD as the instrument through which a product
  declares its interface obligations. Each interface record must carry a
  recognized type (physical, functional, operational, data, electrical,
  mechanical, thermal, optical, or RF), name the mating item it connects
  to, and provide a non-empty set of characteristics. A record missing
  any of these elements is structurally incomplete and cannot be graded
  on its status.
- Interface status follows a lifecycle: draft (initial definition, not
  yet reviewed), under_review (submitted for review by the mating end
  or system), agreed (both product and mating end have accepted the
  definition), superseded (replaced by a successor interface or
  document). Status drives different obligations: an agreed interface
  must cite the bilateral ICD that formalised the agreement; a
  superseded interface must cite its successor so the trail is not lost.
- When the IDD serves as a single-end ICD, it represents the owning
  product's declared view of the interface before bilateral agreement
  exists. Once agreement is reached, the IDD entry transitions to
  "agreed" and gains an ICD reference. An entry still in "agreed" status
  with no ICD reference means the bilateral instrument was never recorded
  -- that is a finding, not a pass.
- Type and status are validated before any record is graded. An
  unrecognized value cannot be placed in the status lifecycle, so it
  raises rather than landing in a bucket.
- The IDD is complete only when no interface remains in draft or
  under_review and no finding stands. Agreed and superseded-with-
  successor entries are terminal valid states.

## Workflow

1. Validate the interface type and status of every interface record;
   raise on any unrecognized value before proceeding.
2. Confirm each record names a mating item; flag any record that does not.
3. Confirm each record provides non-empty interface characteristics;
   flag any record where the characteristics block is absent or empty.
4. For each record in "agreed" status, confirm an ICD reference is
   present; flag any agreed entry without one.
5. For each record in "superseded" status, confirm a successor reference
   is present; flag any superseded entry without one.
6. Partition every interface into exactly one status bucket; reject a
   duplicate interface identifier.
7. Tally interfaces by status and assemble the finding list. The IDD
   is complete only when no draft, no under_review, and no finding stands.

## Pitfalls

- Treating an "agreed" entry as complete without checking for an ICD
  reference. Agreement without a bilateral instrument means the
  controlling document was never captured, which defeats the purpose of
  the IDD as a traceability anchor.
- Accepting a record with no characteristics defined. Interface
  characteristics are the substance of the IDD; a record that lists
  only a type and a mating item has declared an interface but not
  defined it.
- Filing a superseded interface without a successor reference. A dead-
  end supersession breaks the traceability chain and cannot be
  audited.
- Grading a record whose type or status is unrecognized by mapping it
  to the nearest known value. An unknown value is a data-quality
  defect; the review must stop and have the record corrected.
- Declaring the IDD complete because all interfaces have an assigned
  status. Completion requires that all statuses are terminal (agreed or
  superseded with successor) and that no finding stands.

## Behavior contract (gate 3)

The type/status validation, record completeness, agreed-ICD-reference,
superseded-successor, partition, tally, and completeness logic is
exercised by the gate 3 contract test:
scripts/test_e1024_idd_drd.py against scripts/e1024_idd_drd_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1024_idd_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

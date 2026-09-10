---
name: e10-delivery-per-review
description: "Use when planning or checking which systems-engineering documents a space project must deliver or re-baseline at each review milestone per ECSS-E-ST-10C Annex A (informative): build the document-by-review delivery schedule, verify a given review's deliveries against it (missing and unplanned deliveries), and roll up readiness across the whole review sequence. Trigger: delivery schedule, document delivery per review, Annex A, review deliverables, MDR PRR SRR PDR CDR QR AR FRR CRR ER documents, ECSS-E-ST-10C Annex A."
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
  tags: [ecss, e-st-10c, annex-a, delivery-schedule, review, document-management]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SE Document Delivery Per Review (space-systems/ecss/e10-delivery-per-review)

Use when the task is planning or checking the systems-engineering (SE)
document delivery schedule for a space project under ECSS-E-ST-10C
Annex A (informative): which SE documents must be delivered or
re-baselined at which review milestone, and whether an actual review's
deliveries satisfy that schedule.

## Domain quick reference

- ECSS-E-ST-10C Annex A is an informative table mapping SE documents
  (e.g. mission description, SEP, specification tree, technical
  specifications, interface control documents, verification/technical
  budget reports) to the review milestones at which each is due,
  either as a first delivery or a re-baseline/update.
- The review milestones follow the sibling systems-engineering leaf's
  phase-gate sequence: MDR, PRR, SRR, PDR, CDR, QR, AR, FRR, CRR, ER.
- Being informative, Annex A is guidance for tailoring a project's own
  document delivery schedule, not a fixed mandatory checklist -- a
  project's schedule is the authoritative record this leaf checks
  against, not the Annex A table itself.
- A document can be due at more than one review (first issue at one
  gate, re-baseline at later gates); the schedule is a document x
  review applicability matrix, not a one-to-one mapping.

## Workflow

1. Build the project's delivery schedule: for each SE document, record
   the set of review milestones at which it must be delivered or
   re-baselined (tailored from Annex A, agreed with the customer).
2. Before a given review, list the documents the schedule requires for
   that review.
3. Compare against the documents actually delivered for that review:
   - missing deliveries: scheduled for the review but not delivered.
   - unplanned deliveries: delivered for the review but not scheduled
     (flag for review -- may be a legitimate addition or a schedule
     gap).
4. A review's delivery is complete only when there are no missing
   deliveries (unplanned deliveries do not block completeness but
   must be reconciled into the schedule).
5. Roll up across the full review sequence: report which reviews are
   complete and which still have missing deliveries, to see delivery
   readiness across the whole program.

## Pitfalls

- Treating Annex A's informative table as a mandatory universal
  checklist instead of tailoring it into the project's own schedule.
- Missing that a document is due again as a re-baseline at a later
  review, not just once at its first-issue review.
- Blocking a review on an unplanned (extra) delivery instead of only
  on missing scheduled deliveries.
- Confusing this leaf's document-delivery check with the sibling
  systems-engineering leaf's review-gate/phase-exit readiness, which
  checks that reviews themselves are completed, not that documents
  were delivered on schedule.

## Behavior contract (gate 3)

The delivery-schedule and review-readiness logic is exercised by the
gate 3 contract test: scripts/test_e10_delivery_per_review.py against
scripts/e10_delivery_per_review_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e10_delivery_per_review.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

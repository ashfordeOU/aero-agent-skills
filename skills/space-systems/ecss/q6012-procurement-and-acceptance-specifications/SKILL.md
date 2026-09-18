---
name: q6012-procurement-and-acceptance-specifications
description: "Assess the buying document and its companion batch acceptance document as one pair rather than two drafts. Use when ECSS-Q-ST-60-12C clause 9 content has to be settled for a microwave die: confirm each required item is present and actually stated rather than merely listed, hold each item in the document it belongs to, make the few items both carry say the same thing, check that the procurement specification really invokes the acceptance specification it names, and size the lot sample against both the floor and the proportional rule before judging the accept number. An empty heading counts as a gap, not as content. Trigger: ecss, q-st-60-12c-clause-9, die-procurement-specification, lot-acceptance-specification, specification-content-allocation, procurement-acceptance-cross-reference, lot-sampling-plan-sizing."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-procurement-and-acceptance-specifications, q-st-60-12c-clause-9, die-procurement-specification, lot-acceptance-specification, specification-content-allocation, procurement-acceptance-cross-reference, lot-sampling-plan-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die -- Procurement and Acceptance Specifications (space-systems/ecss/q6012-procurement-and-acceptance-specifications)

Use when the task is the specification content of ECSS-Q-ST-60-12C clause
9: the document a microwave die is bought against, and the companion
document each delivered batch is accepted against. Both are being written
or reviewed, and the question is whether the pair is complete and
consistent enough to release.

## Domain quick reference

- The two documents are one instrument. The buying document says which die,
  on which approved application, to which electrical limits, marked and
  delivered how, and what happens to a nonconformance. The acceptance
  document says how a delivered lot is proved: its lot definition, its
  sampling, its electrical and environmental tests, the sequence, the
  accept and reject criteria, the data package, and what happens to a
  rejected lot.
- Each item has a home. An acceptance item written into the buying document
  looks like diligence and behaves like a second source of truth, because
  the lot is tested against the acceptance document and nobody reads the
  buying document again once the order is placed.
- A few items are carried by both because both are unusable without them --
  the die identification above all. Carried twice, they have to say the
  same thing, and a revision suffix that differs between the two is the
  whole defect this check exists to catch.
- The buying document has to invoke the acceptance document by name. A
  reference that is absent, or that names a different document than the one
  actually supplied, leaves the lot arriving with nothing governing its
  testing.
- A listed item with nothing under it is a gap, not content. A heading
  counts towards completeness only when something is actually stated
  beneath it, otherwise the review is grading a table of contents.
- A sampling plan is coherent before it is adequate. A sample larger than
  its lot, or an accept number that covers the whole sample, is an input
  error; a coherent plan can still draw too few parts for the lot size or
  tolerate more failures than the policy allows.
- Sample size is a floor and a proportion, taking whichever is larger and
  never more than the lot itself. A proportion alone under-samples a small
  lot; a floor alone under-samples a large one.

## Workflow

1. Normalise both documents: an identifier and a content mapping each.
   Refuse a document with no identifier rather than assessing an anonymous
   draft.
2. Walk the required content of each document separately, recording an
   absent item and a listed-but-empty item as distinct findings, since they
   are fixed in different ways.
3. Check allocation: an item belonging to the other document, unless it is
   one of the few both documents carry.
4. Compare the shared items value by value and report a disagreement rather
   than choosing a winner.
5. Confirm the buying document invokes the acceptance document that was
   actually supplied, comparing the reference with the document identifier.
6. Validate the lot sampling plan for coherence first, then size the
   required sample from the floor and the proportional rule and judge the
   accept number against the policy ceiling.
7. Report completeness as a fraction of the required items across both
   documents, and release the pair only when no finding stands.

## Pitfalls

- Reviewing the two documents in separate passes. Allocation, shared-item
  agreement and the cross-reference are all properties of the pair, and a
  per-document review passes both while the set stays broken.
- Counting a heading as content. An item listed with an empty value is the
  most common way a specification reaches full marks without saying
  anything, and it reads as complete in every table of contents.
- Duplicating an acceptance item into the buying document for convenience.
  The duplicate drifts at the first revision and the lot is then tested
  against whichever copy the test house happened to receive.
- Accepting a cross-reference because a reference exists. The reference has
  to name the document actually supplied; a plausible identifier pointing
  at a superseded acceptance specification passes a glance and fails a lot.
- Sizing the sample by proportion alone. A small lot then draws a sample of
  one or two parts, and the accept number stops discriminating at all.
- Judging the accept number before the plan is coherent. An accept number
  equal to the sample size accepts every lot, and comparing it with a
  policy ceiling first hides that the plan was never a test.

## Behavior contract (gate 3)

The document normalisation, the absent and unstated content gaps, the
allocation and shared-item consistency checks, the cross-reference between
the two documents, sampling-plan coherence, required sample sizing from
floor and proportion, the accept-number ceiling, the completeness fraction
and the release verdict are exercised by the gate 3 contract test:
scripts/test_q6012_procurement_and_acceptance_specifications.py against
scripts/q6012_procurement_and_acceptance_specifications_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_procurement_and_acceptance_specifications.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

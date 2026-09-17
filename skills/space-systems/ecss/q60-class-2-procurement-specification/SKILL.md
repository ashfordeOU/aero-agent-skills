---
name: q60-class-2-procurement-specification
description: "Validate the controlled written purchasing specification that each Class 2 EEE part type is bought against. Use when an order is raised or its document control is reviewed: index the library so one controlled document owns one part type, score the mandatory content the specification owes, reject a line raised against a draft, superseded or withdrawn issue or against one released after the order date, compare the revision the order cites with the revision actually released on a family-aware ordering, and reconcile ordered part types against the library both ways. Trigger: ecss, ecss-q-st-60c-clause-5-3-2, class-2-procurement-specification, class-2-purchasing-specification-content, class-2-specification-revision-control, class-2-specification-release-status, class-2-specification-part-type-coverage."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-2-procurement-specification, ecss-q-st-60c-clause-5-3-2, class-2-procurement-specification, class-2-purchasing-specification-content, class-2-specification-revision-control, class-2-specification-release-status, class-2-specification-part-type-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 2 EEE Parts — Purchasing Specification (space-systems/ecss/q60-class-2-procurement-specification)

Use when the task is the purchasing specification duty of ECSS-Q-ST-60C
clause 5.3.2 — buying Class 2 parts against a controlled written purchasing
specification held for each part type, rather than against a catalogue line.

## Domain quick reference

- One controlled document owns one part type. Two documents claiming the same
  type means the buyer read one of them, and the other is the requirement
  that quietly went unmet.
- A document number is not document control. The reference, the revision, the
  release state and the release date are what make an issue citable, and a
  line raised against a draft is a line raised against something that can
  still change underneath it.
- A specification released after the order was raised did not govern that
  order. The date ordering is the check, not the presence of a release
  record.
- The content is what the specification is for. A document that omits the
  screening regime or the lot acceptance and marking rules is a datasheet
  reprint, so the mandatory items are scored rather than assumed.
- Revisions come in two schemes and they are not comparable. Numeric
  revisions sort as numbers and alphabetic revisions as letters; comparing a
  '3' with a 'C' produces an answer that means nothing, so the scheme travels
  with the key and a mixed comparison is refused.
- Citing a revision ahead of the released one is a finding too. It usually
  means the order was written against a draft the buyer had seen and the
  library had not.
- A completeness score landing on its threshold is met. The score is a ratio
  of small integers compared in binary, so a representation-sized tolerance
  keeps the verdict the same on every machine.
- Reconciliation runs both ways. An ordered type with no specification is the
  obvious gap; a controlled specification no line cites is the type somebody
  forgot to order.

## Workflow

1. Index the specification library by part type, refusing two documents that
   claim the same type and a revision in no recognised scheme.
2. For each document, score the mandatory content items it carries and name
   the ones it omits.
3. Judge the release state and the release date of the document against the
   order date.
4. Compare the revision the order line cites with the revision released,
   refusing a comparison across revision schemes.
5. Report a line with no controlled specification at all.
6. Compare each score with the minimum completeness required, within a
   representation-sized tolerance.
7. Reconcile ordered part types against the library in both directions.
8. Report the per-line records, the specified fraction and a verdict carrying
   every finding.

## Pitfalls

- Treating the manufacturer datasheet as the purchasing specification. The
  datasheet describes the part on offer; the specification states what the
  project agreed to buy and what the lot owes on delivery.
- Citing a specification reference with no revision. The reference survives
  every reissue, so the order is bound to whatever the library holds on the
  day somebody looks.
- Comparing a numeric revision with an alphabetic one. The answer is an
  accident of encoding and it will be wrong roughly half the time.
- Accepting a specification released the week after the order went out. It
  may describe exactly what arrived, and it governed nothing.
- Scoring content by page count. A long document can still be silent on
  screening; the mandatory items are named, so check for the names.
- Failing a score that landed on its threshold. The shortfall is in the last
  bit of a ratio, not in the document.
- Reconciling one way only. Every line has a specification and the part type
  nobody ordered is still missing at kitting.
- Stopping at the first finding. Document control is closed once, on the
  whole list.

## Behavior contract (gate 3)

The library indexing and its one-document-per-part-type rule, the mandatory
content score, the release state and release date checks, the family-aware
revision ordering and its refusal of a mixed comparison, the completeness
threshold with its representation-sized tolerance, the two-way
reconciliation, the specified fraction and the overall verdict are exercised
by the gate 3 contract test:
scripts/test_q60_class_2_procurement_specification.py against
scripts/q60_class_2_procurement_specification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_procurement_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

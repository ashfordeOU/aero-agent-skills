---
name: q60-class-1-procurement-specification
description: "Verify that every Class 1 part type on an order is bought against one controlled purchasing specification in force. Use when a Class 1 procurement baseline has to be judged orderable: refuse a document with no identifier, issue or approving authority, reject a type carried by two specifications or by none, confirm the issue was effective on the order date, require the declared quality level, the named manufacturer and manufacturing line, an invoked procurement test programme and a lot traceability level, and hold every deviation to an approval reference. Trigger: ecss, ecss-q-st-60c-clause-4-3-2, class-1-purchasing-specification-control, class-1-component-type-coverage, purchasing-specification-issue-currency, class-1-approved-manufacturing-line, class-1-lot-traceability-level."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-1-procurement-specification, ecss-q-st-60c-clause-4-3-2, class-1-purchasing-specification-control, class-1-component-type-coverage, purchasing-specification-issue-currency, class-1-approved-manufacturing-line, class-1-lot-traceability-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 EEE Parts — Purchasing Specification (space-systems/ecss/q60-class-1-procurement-specification)

Use when the task is the purchasing specification of ECSS-Q-ST-60C clause
4.3.2 — the controlled written document raised for each Class 1 component
type, which fixes what is bought, from which line, to which test programme,
and under which traceability, before any purchase order cites it.

## Domain quick reference

- The clause buys per component type, not per order line. One type, one
  specification: a type with no specification has no acceptance basis at all,
  and a type carried by two leaves the delivery review choosing between them
  after the parts have arrived.
- A purchasing specification is a configuration-controlled document. Without
  an identifier, an issue and an approving authority there is nothing for a
  purchase order to invoke, and nobody can later say which text the delivery
  was bought under.
- The issue has to have been in force when the order was placed. A document
  made effective afterwards may describe better parts, but it is not the
  baseline these parts were bought against, so citing it rewrites history
  rather than controlling the purchase.
- Class 1 is a declared level, not an implied one. A specification that omits
  the quality level buys whatever the manufacturer's standard product happens
  to be that quarter.
- The manufacturer alone does not fix the product; the manufacturing line
  does. The same part number built on a second line is a different population
  with its own defect history, so both are named.
- Traceability is ordered as a level, and the levels are ranked. Delivery
  batch traceability cannot reconstruct a lot, so Class 1 orders at least lot
  and date code, and may order wafer lot or serial number above it.
- A deviation is admissible; an unapproved deviation is not. Each one carries
  the reference of the authority that accepted it, or it silently widens the
  baseline it sits in.

## Workflow

1. Validate each purchasing specification: identifier, issue, approving
   authority, effective date and a non-empty list of component types, with no
   type listed twice on one document.
2. Judge each specification's content — declared quality level, manufacturer,
   manufacturing line, invoked procurement test programme, traceability level
   — and compare its effective date with the order date.
3. Hold every declared deviation to an approval reference.
4. Map the ordered component types onto the specifications, raising a finding
   for a type with none, a type with more than one, and a specification entry
   naming a type the order does not carry.
5. Mark a type governed only when exactly one specification carries it and
   that specification raised no finding of its own.
6. Compute the controlled fraction of the ordered types and report the
   per-type records with a verdict carrying every finding.

## Pitfalls

- Treating the manufacturer's datasheet as the purchasing specification. A
  datasheet is published by the seller and revised without notice; it is
  evidence, not a controlled purchase baseline.
- Raising one specification for a whole family of types. The coverage looks
  complete while the test programme and traceability belong to whichever type
  the author had in mind.
- Leaving an obsolete specification in the register alongside its successor.
  Both carry the type, so the acceptance basis is undecided and the finding
  only surfaces at delivery.
- Citing an issue that became effective after the order date. The parts were
  bought under the previous text, whatever the purchase file now contains.
- Naming the manufacturer and stopping there. Line changes are the usual
  route by which a qualified part quietly becomes an unqualified one.
- Accepting delivery batch traceability because the paperwork is present. It
  cannot reconstruct the lot a failure belongs to, which is the whole reason
  the level is ordered.
- Stopping at the first finding. The specification owner needs the whole list
  to close it in one revision rather than one revision per finding.

## Behavior contract (gate 3)

Document validation, the specification content findings, the issue-currency
comparison against the order date, deviation approval, the two-way
type-to-specification mapping, the controlled fraction and the overall
orderable verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_1_procurement_specification.py against
scripts/q60_class_1_procurement_specification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_procurement_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

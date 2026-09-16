---
name: q6013-class-1-procurement-specification
description: "Use when a purchase specification has to be judged fit to order against. Verify that a controlled purchase specification defines the tests and acceptance each class 1 commercial part is bought against under ECSS-Q-ST-60-13C clause 4.3.2: refuse a document with no identifier, issue or approving authority, require every ordered part number to be covered and flag an entry the order does not carry, hold each parameter to a test condition and an ordered limit pair, confirm the ordered limits are no wider than the published ones under a named tolerance, and require a declared screening or lot acceptance route. Trigger: ecss, q-st-60-13c-clause-4-3-2, class-1-purchase-specification-control, purchase-specification-part-coverage, purchase-acceptance-limit-pair, purchase-limit-tightening-check, lot-acceptance-sampling-route."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-procurement-specification, q-st-60-13c-clause-4-3-2, class-1-purchase-specification-control, purchase-specification-part-coverage, purchase-acceptance-limit-pair, purchase-limit-tightening-check, lot-acceptance-sampling-route]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 Commercial Parts — Procurement Specification (space-systems/ecss/q6013-class-1-procurement-specification)

Use when the task is the purchase specification of ECSS-Q-ST-60-13C clause
4.3.2 — the configuration-controlled document that fixes, part by part, which
tests are performed on a commercial electrical, electronic and
electromechanical part and what acceptance the delivery is measured against.

## Domain quick reference

- The purchase specification is the document a purchase order invokes, so it
  has to be identifiable: an identifier, an issue, and an approving authority.
  A draft with no issue cannot be cited on an order, because nobody can later
  say which text the delivery was bought under.
- Coverage runs in both directions. Every part number on the order needs an
  entry, and an entry naming a part the order does not carry is a signal that
  the specification and the order have drifted apart.
- A parameter is only orderable when it carries both halves: the test
  condition it is measured at, and the acceptance limits it is measured
  against. A limit with no condition is untestable, a condition with no limit
  is undispositionable, and either one alone reaches the delivery review as an
  argument rather than a verdict.
- Limits are ordered as a pair, and the pair may be one-sided. A minimum with
  no maximum is a legitimate order for a parameter with no upper concern; a
  lower bound above its upper bound is an input error.
- The purchase may tighten a published limit; it may never loosen one. Buying
  to a wider window than the manufacturer publishes orders parts that the
  manufacturer never claimed, so the ordered bounds are compared against the
  published ones, with an ordered limit equal to the published limit
  admissible under a named tolerance.
- Acceptance needs a declared route: every device screened, or a lot
  acceptance sample with a sample size and an accept number that sample can
  carry. An accept number reaching the sample size accepts every lot and is
  not a plan.

## Workflow

1. Validate the specification header: identifier, issue and approving
   authority, each non-blank.
2. Validate the ordered part-number list and reject an empty order.
3. For each entry, validate the part number and every parameter: name, test
   condition, ordered limit pair and any published bounds. Reject a parameter
   declared twice and a specification listing one part twice.
4. Raise a finding for a parameter with no test condition and for a parameter
   with no acceptance limit at all.
5. Compare each ordered bound with its published bound, keeping both findings
   when both sides are loosened, and treating a dropped bound as a finding in
   its own right. Absorb representation error at an equal-limit boundary with
   a named tolerance rather than by relaxing the comparison.
6. Validate the declared acceptance route per part and raise a finding when no
   route is declared.
7. Reconcile the covered part numbers against the ordered ones in both
   directions, then report the per-part records and a verdict carrying every
   finding.

## Pitfalls

- Accepting an uncontrolled document. A specification with no issue is not
  invocable on an order; whichever revision the supplier happens to hold
  becomes the acceptance basis.
- Checking coverage one way only. An order line with no entry is the obvious
  gap; an entry for a part the order does not carry is the one that hides a
  mismatched revision of either document.
- Copying the published limits into the purchase unchanged and calling it
  tightened. Equal limits are admissible, but they leave no margin for the
  delivery, so the equality is a deliberate decision rather than a default.
- Ordering a bound wider than the published one to make an incoming lot pass.
  That buys parts outside anything the manufacturer characterized and cannot
  be recovered at the delivery review.
- Dropping a bound the published data fixes. An unbounded parameter reads as
  covered on the specification while accepting anything on delivery.
- Writing a lot acceptance plan whose accept number reaches the sample size.
  Such a plan accepts every lot and only looks like sampling.
- Stopping at the first finding. The specification owner needs the whole list
  to close it in one revision rather than one revision per finding.

## Behavior contract (gate 3)

The header validation, ordered-limit pair validation, parameter assessment,
limit-tightening comparison, acceptance-route validation, two-way part
coverage and the overall fit-to-order verdict are exercised by the gate 3
contract test: scripts/test_q6013_class_1_procurement_specification.py against
scripts/q6013_class_1_procurement_specification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_procurement_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

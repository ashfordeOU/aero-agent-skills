---
name: order-requirements-review
description: "Use when you must review an incoming aerospace purchase order before acceptance: verify all eight canonical order elements are declared (product identification, spec or drawing revision, quantity and schedule, delivery date, acceptance criteria, special requirements, preservation and packaging, records), classify special requirements into recognized aerospace classes (FAI, delta FAI notification, key characteristic control, provenance evidence, special process approval, source verification, certificate of conformance, serialization) or unrecognized clauses, apply the feasibility gates (qualified special process, approved material, NDT capability, delivery within frozen lead time), and return the verdict: reject-review, accept-with-fai-condition, or accept. Produces the completeness check, recognized and unrecognized specials, blockers, and verdict gating acceptance. Trigger: purchase order review, contract review, special requirement classification, requirements completeness."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: as9100
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [order-requirements-review, purchase-order-review, special-requirement-classification, contract-review, order-acceptance-verdict, feasibility-gates, requirements-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# Order Requirements Review (manufacturing-quality/as9100/order-requirements-review)

Use when the task is reviewing an incoming aerospace purchase order or
contract before acceptance (AS9100 requirements review, ISO 9001:2015
base): verifying the order carries every required element, recognizing
aerospace special-requirement classes, applying feasibility gates, and
deciding whether to accept, accept with a first article inspection (FAI)
condition, or reject for review. This leaf reviews orders IN; it pairs
with manufacturing-quality/as9100/supplier-control, which flows
requirements OUT to suppliers after acceptance.

## Domain quick reference

- The eight canonical order elements an incoming aerospace order must
  declare (module constant REQUIRED_ORDER_ELEMENTS):
  product-identification, spec-drawing-revision, quantity-schedule,
  delivery-date, acceptance-criteria, special-requirements,
  preservation-packaging, records. Any element missing from the
  declaration is reported; an empty declaration reports all eight.
- The eight aerospace special-requirement classes (SPECIAL_REQUIREMENT_CLASSES):
  fai, delta-fai-notification, key-characteristic-control,
  counterfeit-free-evidence, special-process-approval, source-verification,
  certificate-of-conformance, serialization. Declared tokens that match a
  class are recognized; anything else is flagged unrecognized and sent
  back to the customer for clarification.
- Feasibility gates (feasibility_blockers): the special process must be
  qualified (special_process_qualified), the material approved
  (material_approved), NDT capability available (ndt_capability_ok), and
  the quoted delivery must fit the frozen lead time. Delivery is a
  blocker exactly when quoted_delivery_days > frozen_lead_time_days;
  equality meets the frozen lead time and is not a blocker. Each gate
  fires independently.
- Verdict precedence (order_acceptance_verdict), evaluated in order:
  1. any missing element, unrecognized special requirement, or blocker
     returns reject-review;
  2. else FAI pending returns accept-with-fai-condition;
  3. else accept.
- AS9100 clause 8.2 frames the review of requirements related to products
  and services before commitment to supply (paraphrase; the standard text
  is not reproduced). This review runs before supplier flow-down and
  before production release.

## Workflow

1. Collect the order declaration: the eight canonical elements the order
   states, and the special requirements it cites, as hyphenated slugs.
2. Run requirements_completeness(declared) and review the missing list;
   every canonical element must be present.
3. Run classify_special_requirements(declared) and separate recognized
   aerospace classes from unrecognized clauses.
4. Check the feasibility gates with feasibility_blockers(...): qualified
   special processes, approved material, NDT capability, and quoted
   delivery days against the frozen lead time in days.
5. Decide with order_acceptance_verdict(missing, unrecognized, blockers,
   fai_pending), honoring the precedence: any defect rejects the order
   for review; a clean order with FAI pending is accepted with the FAI
   condition; a clean order with no FAI pending is accepted.
6. For a single consolidated record, call order_review_summary(...) and
   file the seven-key dict with the order.

## Worked example

Three orders reviewed with the module (real outputs):

Order A declares 7 of 8 elements (missing acceptance-criteria), specials
{fai, key-characteristic-control, serialization, exotic-clause}, an
unqualified special process, and a 30-day quoted delivery against a
25-day frozen lead time:

- requirements_completeness: complete False, missing
  ['acceptance-criteria'].
- classify_special_requirements: recognized ['fai',
  'key-characteristic-control', 'serialization'], unrecognized
  ['exotic-clause'].
- feasibility_blockers(False, True, True, 30, 25):
  ['unqualified-special-process', 'delivery-exceeds-frozen-lead-time'].
  The 30-day quote strictly exceeds the 25-day frozen lead time, so the
  delivery blocker fires alongside the unqualified special process
  (equality, 25 versus 25, would not fire).
- order_acceptance_verdict: reject-review (missing element, unrecognized
  special, and blockers all present).

Order B declares all 8 elements, 6 recognized special classes (fai,
delta-fai-notification, key-characteristic-control,
special-process-approval, source-verification, serialization), every
gate qualified (40-day quote against a 45-day frozen lead time), and FAI
pending: verdict accept-with-fai-condition, blockers [].

Order C declares all 8 elements, recognized specials only
(certificate-of-conformance, serialization), every gate qualified, no
FAI pending: verdict accept.

The convenience dict order_review_summary returns exactly {complete,
missing, recognized_specials, unrecognized_specials, blockers,
fai_pending, verdict}.

## Verification

- Confirm Order A returns missing ['acceptance-criteria'], recognized
  ['fai', 'key-characteristic-control', 'serialization'], unrecognized
  ['exotic-clause'], the two blockers above, and verdict
  reject-review.
- Confirm Order B returns verdict accept-with-fai-condition and Order C
  verdict accept.
- Confirm delivery blocks only when quoted > frozen: 25 versus 25
  returns no delivery blocker.
- Confirm each of the four blocker codes fires on its own condition and
  no blockers fire when every gate passes.
- Confirm every non-string, empty, or negative-day input raises
  ValueError, and identical inputs give identical outputs run to run.
- Run the contract test offline: python3
  scripts/test_order_requirements_review.py (34 tests, deterministic).

## Related leaves

- manufacturing-quality/as9100/supplier-control: flows requirements OUT
  to suppliers after this leaf has accepted the order IN.
- manufacturing-quality/as9100/counterfeit-prevention: procurement
  controls for material risk once the order is accepted.
- manufacturing-quality/as9102/first-article-inspection: executes the
  first article process; this leaf only recognizes FAI as an order
  condition.

## Pitfalls

- Failing an order whose quoted delivery equals the frozen lead time:
  delivery is a blocker only when quoted_delivery_days >
  frozen_lead_time_days, so 25 versus 25 meets the frozen lead time
  and must not fire.
- Letting FAI pending rescue a defective order: the verdict precedence
  puts reject-review first, so any missing element, unrecognized
  special, or blocker rejects for review - accept-with-fai-condition
  applies only to an otherwise clean order.
- Silently dropping unrecognized specials: a declared token that
  matches no aerospace class is flagged unrecognized and sent back to
  the customer for clarification, not folded into the recognized set
  or ignored.
- Treating a recognized FAI special as FAI execution: this leaf only
  recognizes FAI as an order condition (accept-with-fai-condition);
  running the first article belongs to the as9102/first-article-
  inspection leaf and gates production release after acceptance.
- Scoring completeness from a partial declaration: every canonical
  element must be declared, and an empty declaration reports all eight
  missing - a claim of "complete" requires the full eight-element set,
  not the elements the supplier happened to state.
- Feeding non-physical orders: non-string, empty, or negative-day
  inputs raise ValueError, so a malformed order dict is rejected
  rather than scored into a plausible verdict.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_order_requirements_review.py

The test covers the three worked orders (reject-review,
accept-with-fai-condition, accept), detection of each of the eight
canonical elements when missing, recognition of each of the eight
aerospace special classes, independent firing of each feasibility
blocker, delivery equality not blocking, the verdict precedence, empty
and unknown declarations, token normalization, ValueError rejection of
non-physical inputs, the exact seven-key summary dict, and
run-to-run determinism.

## Compliance

- Standards referenced, not reproduced: AS9100 (IAQG/SAE) text is
  proprietary; this skill names and paraphrases the requirements review
  only. The purchase link is recorded in standards-map.yaml (as9100
  entry).
- compliance: STANDARDS-REF, gated: false; the standard is listed
  reference-only.

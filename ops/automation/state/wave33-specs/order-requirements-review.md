# Wave-33 leaf spec: order-requirements-review (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/order-requirements-review/
- Pack: as9100 (13 leaves -> 14). Sibling receipts: supplier-control
  owns requirements flow-down OUT to suppliers (flow_down_required,
  supplier_record_complete); counterfeit-prevention owns procurement
  controls for counterfeit risk only; the quality leaf's CLAUSE_BY_FOCUS
  enumerates 8.1.1/8.1.2/8.1.3/8.1.4/8.4.1/8.5.1.3 - the 8.2.x
  order-review clause is absent; space-systems ECSS "requirements
  review" = MDR/PRR/SRR/PDR/CDR technical gates; do254/requirements-
  capture = design requirements. Family grep for order-acceptance/
  special-requirement/requirements-review/contract-review/purchase-order
  review = zero files. This leaf owns pre-acceptance review of an
  INCOMING aerospace purchase order or contract.
- Standards id: as9100 (reference-only; ISO 9001:2015 base + aerospace
  requirements review). Ledger Standard: as9100.
- Family: manufacturing-quality

## Claim

Run the pre-acceptance review of an incoming aerospace purchase order
or contract: check the eight canonical order elements (product
identification, spec/drawing revision, quantity/schedule, delivery
date, acceptance criteria, special requirements, preservation/
packaging, records), recognize aerospace special-requirement classes
(FAI, delta-FAI notification, key characteristic control,
counterfeit-free evidence, special-process approval, source
verification, certificate of conformance, serialization), apply the
feasibility gates (qualified special processes, approved material, NDT
capability, delivery versus frozen lead time), and return the order
acceptance verdict: reject-review | accept-with-fai-condition |
accept. Runs BEFORE supplier flow-down or production release.

Does NOT do: requirements flow-down to suppliers (supplier-control);
counterfeit procurement controls (counterfeit-prevention); production
release; technical design requirements review (do254/ECSS).

## Model (implement exactly)

Constants:
- REQUIRED_ORDER_ELEMENTS: the 8 canonical elements above.
- SPECIAL_REQUIREMENT_CLASSES: the 8 aerospace classes above.

Functions (pure stdlib):

- requirements_completeness(declared) -> (complete: bool, missing:
  list[str]) against the 8 canonical elements (set arithmetic).
- classify_special_requirements(declared) -> (recognized, unrecognized)
  against the 8-class map (set arithmetic).
- feasibility_blockers(special_process_qualified: bool,
  material_approved: bool, ndt_capability_ok: bool,
  quoted_delivery_days, frozen_lead_time_days) -> list[str] of blocker
  codes ("unqualified-special-process", "unapproved-material",
  "no-ndt-capability", "delivery-exceeds-frozen-lead-time"). Delivery
  is a blocker when quoted_delivery_days > frozen_lead_time_days.
- order_acceptance_verdict(missing, unrecognized, blockers,
  fai_pending: bool) -> one of "reject-review" (any missing element,
  unrecognized special, or blocker), "accept-with-fai-condition"
  (complete and no blockers, fai_pending True), "accept" (otherwise).
  Document the precedence exactly.
- order_review_summary(...) -> dict {complete, missing,
  recognized_specials, unrecognized_specials, blockers, fai_pending,
  verdict}.

## Worked example

Order A: declared set missing "acceptance-criteria" -> missing = 1;
declared specials include 3 recognized + 1 unrecognized
("exotic-clause"); special process unqualified AND delivery 30 days >=
frozen 25 days -> blockers = ["unqualified-special-process"];
verdict reject-review.
Order B: complete 8/8, 6/6 recognized specials, all gates OK, FAI
pending -> accept-with-fai-condition.
Order C: clean and complete -> accept.

Run your module and take the real outputs as assert targets, then check
the verdicts match those three cases exactly.

If a value falls outside its expected verdict, your implementation has
a bug: find it before writing tests. In the SKILL.md worked example
show your module's real outputs (do not invent them).

## Validation list (contract test must include)

- Completeness: each of the 8 canonical elements is detected when
  missing; an empty declaration reports all 8 missing.
- Classification: every one of the 8 aerospace classes is recognized;
  an unknown class lands in unrecognized.
- Feasibility: each blocker condition fires independently; delivery is
  a blocker exactly when quoted > frozen (equality is not a blocker).
- Verdict precedence: any missing element -> reject-review even when
  everything else passes; a blocker -> reject-review; complete + no
  blockers + fai_pending -> accept-with-fai-condition; else accept.
- Determinism: identical outputs run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-order-requirements-review.yaml)

Query 1 (copy verbatim):
  "pre acceptance purchase order requirements review and aerospace special requirement classification for an incoming order"
  intent: "manufacturing-quality; incoming purchase-order requirements review and special-requirement classification"
  expected_skill: "manufacturing-quality/as9100/order-requirements-review"
Query 2 (copy verbatim):
  "contract review feasibility gates and order acceptance verdict before supplier flow down and production release"
  intent: "manufacturing-quality; order-acceptance feasibility gates and verdict"
  expected_skill: "manufacturing-quality/as9100/order-requirements-review"
Task ids: w33-order-requirements-review-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must review an incoming aerospace
purchase order before acceptance:" and include the outputs in the
Claim. First tag: order-requirements-review. Additional tags ONLY:
purchase-order-review, special-requirement-classification,
contract-review, order-acceptance-verdict, feasibility-gates,
requirements-completeness. NEVER single generic words (order, review,
requirement, contract, acceptance, supplier, quality). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): flow down, supplier
requirements (supplier-control); counterfeit, suspect parts
(counterfeit-prevention); clause map, audit focus (quality leaf);
FAI execution (as9102 first-article leaves own the FAI process; this
leaf only recognizes FAI as an order condition); design requirements
capture. The tokens "order requirements review", "special
requirement", "acceptance verdict", "pre-acceptance" are this leaf's
own.

Tags: [order-requirements-review, purchase-order-review,
special-requirement-classification, contract-review,
order-acceptance-verdict, feasibility-gates, requirements-completeness]

Sibling-citation lines for Related leaves:
manufacturing-quality/as9100/supplier-control (flow-down OUT; this leaf
reviews orders IN),
manufacturing-quality/as9100/counterfeit-prevention,
manufacturing-quality/as9102/first-article-inspection.

Ledger Standard: as9100.

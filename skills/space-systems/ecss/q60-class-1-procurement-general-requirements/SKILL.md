---
name: q60-class-1-procurement-general-requirements
description: "Verify that a purchase of class 1 EEE parts meets the technical baseline agreed for it under ECSS-Q-ST-60C clause 4.3.1: refuse a part number or manufacturer that is neither the baseline one nor a declared alternate, rank the ordered assurance level against the baseline rank, name every baseline requirement the order never flowed down to the supplier, and hold the delivered lot to the ordered quantity, the baseline temperature range, the baseline dose figure and its traceability records. Use when a delivered lot has to be shown to match what was agreed. Trigger: ecss, q-st-60c-clause-4-3-1, class-1-part-procurement-conformity, purchase-order-requirement-flowdown, undeclared-part-substitution, delivered-lot-temperature-range-coverage, procurement-assurance-level-rank, delivered-lot-traceability-records."
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
  tags: [ecss, q-st-60c-class-1-eee-scope, q60-class-1-procurement-general-requirements, q-st-60c-clause-4-3-1, class-1-part-procurement-conformity, purchase-order-requirement-flowdown, undeclared-part-substitution, delivered-lot-temperature-range-coverage, procurement-assurance-level-rank]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 EEE Parts — Procurement General Requirements (space-systems/ecss/q60-class-1-procurement-general-requirements)

Use when the task is the general procurement duty of ECSS-Q-ST-60C clause
4.3.1 — showing that the electrical, electronic and electromechanical parts
actually bought for class 1 use meet the technical baseline that was agreed
for them, rather than only the parts that were specified.

## Domain quick reference

- Procurement conformity is a chain of three documents that can disagree with
  each other: the agreed baseline, the purchase order placed against it, and
  the lot that arrived. A finding can sit in any link, so each link is
  compared with the one before it rather than the whole chain being judged at
  the delivery.
- A substitution is a procurement event, not a paperwork variant. A different
  part number, or the baseline part number from a different manufacturer, is
  outside the baseline unless it was declared as an approved alternate before
  the order was placed.
- Assurance levels form a ladder, not a set of labels. An order may be placed
  at or above the baseline rank; comparing the level names for equality either
  refuses a legitimate upgrade or silently accepts a downgrade.
- A baseline requirement that was never written into the purchase order is a
  requirement the supplier never saw. It cannot be recovered at incoming
  inspection, because the lot was built without it, so the flow-down is
  checked against the order and not against the delivery note.
- A temperature range is a containment question, not an equality. The
  delivered rating has to reach at least as low and at least as high as the
  baseline range; a narrower rating on either end leaves part of the mission
  profile unevidenced.
- Temperature limits and dose figures travel through unit conversions, so a
  value that should sit exactly on the baseline can land a few units in the
  last place away from it. That is absorbed by a named tolerance; the agreed
  figure itself is never relaxed to close a finding.

## Workflow

1. Validate the agreed baseline: part number, manufacturer, assurance level,
   temperature range, dose capability, the requirements to be flowed down and
   any declared alternates. Reject an inverted or degenerate range instead of
   reordering it.
2. Validate the purchase order and the delivered lot on their own terms, so a
   malformed quantity or a repeated reference is an input error rather than a
   conformity finding.
3. Test the order for an undeclared substitution against the baseline part,
   its manufacturer and the declared alternate list.
4. Rank the ordered assurance level on the ladder and compare it with the
   baseline rank.
5. Name every baseline requirement the order failed to flow down, each as its
   own finding.
6. Compare the delivered lot with the order for quantity, and with the
   baseline for temperature-range containment and dose capability, absorbing
   an exactly-met bound with the named tolerance.
7. Check the lot carries each mandatory traceability record, then report the
   per-check results and a conformity verdict carrying every finding rather
   than only the first.

## Pitfalls

- Comparing assurance levels by name. Equality refuses an order placed above
  the baseline and accepts nothing below it only by accident; the comparison
  belongs on the ladder rank.
- Accepting a part number that differs from the baseline because the datasheet
  looks equivalent. Equivalence is a decision taken before the order, recorded
  as a declared alternate; taken after delivery it is an undeclared
  substitution.
- Checking the flow-down against the delivery documents. The requirement had
  to reach the supplier before the lot was built, so the order is the document
  the flow-down is graded on.
- Reading a delivered temperature range as met because it overlaps the
  baseline. Containment is end to end, and a narrow limit on either end leaves
  a part of the mission profile with no evidence behind it.
- Relaxing the baseline dose figure or a temperature limit to close an
  exactly-met case. An equality at the limit is handled by the tolerance
  inside the comparison; the agreed figure stays as agreed.
- Stopping at the first finding. The buyer needs the whole list to raise one
  corrective action with the supplier rather than discovering the next gap
  after the next delivery.

## Behavior contract (gate 3)

The baseline, order and lot validation, the undeclared-substitution test, the
assurance-ladder comparison, the flow-down coverage, the temperature-range and
dose comparisons, the traceability-record check and the overall conformity
verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_1_procurement_general_requirements.py against
scripts/q60_class_1_procurement_general_requirements_logic.py (stdlib
unittest, offline).
Run: python3 scripts/test_q60_class_1_procurement_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

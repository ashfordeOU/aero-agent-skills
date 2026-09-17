---
name: q60-class-3-manufacturer-data-deliveries
description: "Verify that the manufacturer data delivered with a Class 3 EEE shipment reaches the parts actually in the box, under clause 6.3.11 of ECSS-Q-ST-60C: take the shipment as its sub-lots, derive the owed set from the part profile with core items held apart from attribute-driven ones, test each record for an issue date inside the delivery window, an accountable signature and a certified specification revision matching the one ordered, map admissible records onto sub-lots, weight coverage by shipped quantity, and release only the sub-lots every core item reaches. Use when a delivered data folder has to become a dock disposition. Trigger: ecss, q-st-60c-clause-6-3-11, q60-c3-delivered-data-package-reconciliation, q60-c3-quantity-weighted-document-coverage, q60-c3-certificate-revision-match, q60-c3-document-admissibility-window, q60-c3-sublot-release-disposition."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c-clause-6-3-11, q60-class-3-manufacturer-data-deliveries, q60-c3-delivered-data-package-reconciliation, q60-c3-quantity-weighted-document-coverage, q60-c3-certificate-revision-match, q60-c3-document-admissibility-window, q60-c3-sublot-release-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Manufacturer Data Deliveries (space-systems/ecss/q60-class-3-manufacturer-data-deliveries)

Use when the task is clause 6.3.11 of ECSS-Q-ST-60C: a Class 3 delivery has
arrived with a folder of manufacturer paper, and the receiving side has to
decide what that paper actually covers. The leaf reconciles the folder against
the sub-lots in the box, by quantity rather than by document count, and returns
a dock disposition with the releasable quantity named.

## Domain quick reference

- The shipment is not the purchase-order line. One line routinely arrives as
  several sub-lots with different date codes, and the data package is owed
  against those sub-lots. A folder reconciled against the order number instead
  of against the box will pass while half the parts are uncovered.
- Coverage is a quantity, not a count. Two certificates out of three sounds like
  most of the delivery and can be a fifth of it; the number that matters is how
  many of the parts in the box a valid record reaches.
- A present-but-inadmissible record is worse than an absent one. An absent
  record shows up as a gap in any review; an inadmissible one is counted as
  coverage by anybody working from a checklist of document titles.
- The certificate is specific to a specification revision. A certificate against
  the revision the supplier happened to hold, rather than the one the order
  called out, certifies conformity to something nobody bought.
- The delivery window bounds the paper at both ends. A record issued after the
  box arrived was written to close a gap rather than to report work, and one
  issued before the earliest sub-lot was made cannot describe those parts.
- A signature is owed on some items and not on others. A certificate of
  conformity and a lot acceptance report are statements somebody is accountable
  for; screening data is a measurement record and stands on its identifiers.
- The owed set grows with the part, not with the customer's appetite. Radiation
  sensitivity, a destructive analysis requirement, lot acceptance testing and
  die-level traceability each bring one item in, and nothing else does.
- Release is per sub-lot. A delivery where the core items reach some sub-lots
  and not others is neither an acceptance nor a rejection; the covered sub-lots
  go to stores and the rest stay at the dock, with the split recorded.

## Workflow

1. Validate the sub-lot records, reject a shipment naming one sub-lot twice, and
   take the earliest manufacture date as the lower bound of the delivery window.
2. Derive the owed set: the core items every delivery owes, plus the items the
   part profile brings in.
3. Test each delivered record for admissibility — identifiers, issue date inside
   the window, signature where owed, certified revision against the ordered one.
4. Map every admissible record onto the sub-lots it names, and report a name
   that was never shipped rather than silently discarding it.
5. Take coverage per owed item by shipped quantity, keeping the covered sub-lot
   identities alongside the fraction.
6. Release the sub-lots every core item reaches, and total the quantity that is.
7. Return the verdict: accepted whole, accepted pending an attribute-driven
   item, partially accepted, or held at the dock, with every reason listed.

## Pitfalls

- Reconciling against the purchase order. The box, not the order, is what has to
  be covered, and the two differ whenever a line ships as several sub-lots.
- Counting documents. A folder with one of every title looks complete and can
  leave most of the shipped quantity with no record reaching it.
- Accepting a certificate on the wrong specification revision because the part
  number matched. The part number is not the thing being certified.
- Taking a record issued after arrival at face value. It may be perfectly true
  and it was still written after the fact, which is what the window tests.
- Requiring a signature everywhere. Demanding one on measurement data invites a
  meaningless one and devalues the signature on the items that need it.
- Reading an attribute-driven item as optional. It is conditional on the part,
  not on the schedule, and a part with the attribute owes it outright.
- Treating a partial delivery as a pass or a fail. The releasable sub-lots are
  releasable; collapsing the split either strands good parts or ships uncovered.

## Behavior contract (gate 3)

The owed-set derivation, document admissibility tests, quantity-weighted
coverage, unshipped-reference reporting, per-sub-lot release, delivery verdict
and the full shipment reconciliation are exercised by the gate 3 contract test:
scripts/test_q60_class_3_manufacturer_data_deliveries.py against
scripts/q60_class_3_manufacturer_data_deliveries_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_manufacturer_data_deliveries.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

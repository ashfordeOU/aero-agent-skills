---
name: q6013-class-2-manufacturer-data-deliveries
description: "Use when a delivered data folder has to become a receiving verdict. Assess whether the documentation package a manufacturer delivered with a commercial EEE lot holds what the intermediate assurance class requires under ECSS-Q-ST-60-13C clause 5.3.11: fix the lot identity every item is matched against, assemble the owed item set including any on-request item the procurement specification called off, dispose each item as delivered in full, delivered as a supported summary, unidentified, matched to another lot, late or absent, credit a summary below the data it points at, and take the delivered share and the weighted completeness. Trigger: ecss, q-st-60-13c-clause-5-3-11, class-two-manufacturer-data-package, lot-identity-item-matching, retained-data-summary-credit, data-item-retention-period, on-request-data-item-call-off, data-package-delivery-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-manufacturer-data-deliveries, class-two-manufacturer-data-package, lot-identity-item-matching, retained-data-summary-credit, data-item-retention-period, on-request-data-item-call-off, data-package-delivery-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Manufacturer Data Deliveries (space-systems/ecss/q6013-class-2-manufacturer-data-deliveries)

Use when the task is the clause 5.3.11 delivered-documentation question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a commercial EEE lot
has arrived with a folder of manufacturer paper, and the question is
whether that paper covers the units in the box and reaches the content the
class demands.

## Domain quick reference

- The folder is not the deliverable. What the paper says about the units
  in this box is, so every item is matched against the lot identity --
  the lot identifier and the date code together -- rather than against
  the purchase order the lot was bought on.
- This class differs from the class above in one structural way: an item
  may arrive as a summary pointing at data the manufacturer retains,
  instead of as the data itself. That is a thinner delivery and it is
  credited below a full one, which is what keeps a package assembled
  entirely out of summaries from scoring as a package of data.
- A pointer counts only while what it points at still exists. A summary
  with no retained data behind it, or with a retention period that runs
  out before the data would be needed, points at nothing and is not a
  delivery.
- An item with no reference or no issue has not been delivered in any
  usable sense. The issue is what fixes which version of that document
  was the one covering this lot, and an unissued document says whatever
  it says today.
- Timing decides whether the package controlled anything. Data arriving
  after the lot was accepted documents a decision already taken, and the
  units are already in the store by then.
- The owed item set is not fixed. Every lot owes the required items; an
  on-request item joins them only where the procurement specification
  called it off for this purchase, and an item delivered that the lot
  does not owe is recorded rather than credited against one it does.
- Both figures run over the full owed set. An absent item counts as
  nothing rather than dropping out of the denominator, so removing a
  weak item can only lower the score, which is the way round it has to
  be.
- A figure landing exactly on its floor is inside it. The credit and the
  division can leave the two sides a few ULP apart, and that is
  representation error rather than a short package.

## Workflow

1. Validate the delivery policy first: the delivered-share floor, the
   credit a summary earns, the weighted completeness floor, the minimum
   retention behind a summary and the marginal band. A summary credited
   in full, a completeness floor above the share floor, or a band
   reaching the floor is refused rather than used.
2. Fix the lot identity the package is offered against, refusing a blank
   lot identifier or date code.
3. Assemble the owed item set: the required items plus any on-request
   item called off. Refuse a request naming a required item or an item
   outside the register.
4. Validate every delivered record and refuse an unregistered item, a
   duplicated item or a non-boolean timing declaration.
5. Dispose each owed item in order: identifier first, then lot match,
   then timing, then the summary support test. Report all failing lists
   in full rather than truncating at the first entry.
6. Take the delivered share and the credit-weighted completeness over
   the owed set, comparing both against their floors with a tolerance
   that absorbs representation error.
7. Close on one verdict -- package not delivered, package covers another
   lot, package delivered after acceptance, package items short, or
   package meets class two scope -- and raise an advisory for a
   completeness sitting inside the marginal band above its floor.

## Pitfalls

- Matching items to the order rather than to the lot. One order line is
  routinely filled from more than one build, and a certificate covering
  the other build covers none of the units in this box.
- Accepting a summary because a summary is permitted here. It is
  permitted with retained data behind it and a retention period that
  outlives the need; without both it is a sentence, not a record.
- Crediting a summary in full. The credit is what records that pointing
  at data is thinner than delivering it, and without it a package of
  pure pointers scores as a package.
- Treating a missing issue as a clerical gap. It is the mechanism that
  ties a named document to the version that covered this lot, and
  without it the lot was accepted against a document that has since
  moved.
- Averaging only over the items that arrived. Deleting a weak item would
  then raise the score, so the denominator stays the full owed set.
- Letting an item the lot does not owe make up the numbers. A radiation
  report nobody asked for does not stand in for an absent screening
  record.

## Behavior contract (gate 3)

The policy validation, the lot identity, the owed item set including the
on-request call-off, the item record validation, the in-full, supported
summary, unsupported summary, unidentified, mismatched, late and absent
dispositions, the delivered share, the credit-weighted completeness, the
marginal advisory and the delivery verdict are exercised by the gate 3
contract test:
scripts/test_q6013_class_2_manufacturer_data_deliveries.py against
scripts/q6013_class_2_manufacturer_data_deliveries_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6013_class_2_manufacturer_data_deliveries.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

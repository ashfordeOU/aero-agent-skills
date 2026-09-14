---
name: q6013-class-3-manufacturer-data-deliveries
description: "Assess whether the documentation a manufacturer supplied with a commercial EEE shipment reaches what the lowest assurance class asks under ECSS-Q-ST-60-13C clause 6.3.11: fix the lot identity every item is matched against, separate the core items no waiver reaches from supporting items a recorded project acceptance may drop, credit each item by the provenance that issued it, hold a certificate from an unfranchised source, credit a published datasheet only where the revision was archived, and take the provenance-weighted completeness against its floor. Use when a delivered data folder has to become a receiving verdict at the lightest class. Trigger: ecss, q-st-60-13c-clause-6-3-11, class-three-manufacturer-data-package, data-item-provenance-credit, franchised-distributor-authenticity, archived-published-datasheet-credit, supporting-item-waiver-record, data-package-receiving-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-manufacturer-data-deliveries, class-three-manufacturer-data-package, data-item-provenance-credit, franchised-distributor-authenticity, archived-published-datasheet-credit, supporting-item-waiver-record, data-package-receiving-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 3 Manufacturer Data Deliveries (space-systems/ecss/q6013-class-3-manufacturer-data-deliveries)

Use when the task is the clause 6.3.11 delivered-documentation question of
ECSS-Q-ST-60-13C at the lowest assurance class: a commercial EEE lot has
arrived with a folder of manufacturer paper, and the question is whether
that paper covers the units in the box and comes from somewhere that can be
relied on.

## Domain quick reference

- The folder is not the deliverable. What the paper says about the units in
  this box is, so every item is matched against the lot identity -- the lot
  identifier and the date code together -- rather than against the purchase
  order the lot was bought on.
- The owed set splits in two at this class. A short core is owed by every
  lot and no waiver reaches it; the rest are supporting items, and a
  supporting item leaves the owed set only where the project recorded an
  acceptance for dropping it. A waiver with nothing recorded behind it is
  not a waiver, it is a gap with a name.
- Provenance carries a credit rather than a yes or no. A record the
  manufacturer issued is worth more than one issued by a franchised
  distributor, which is worth more than a published datasheet archived at a
  named revision, which is worth more than the same datasheet left where the
  manufacturer can move it.
- A published page that has not been archived points at whatever is there
  today. That is why it credits nothing here: the project cannot show which
  words it accepted the lot against.
- A core item carries a credit floor of its own, above the floor the package
  as a whole has to reach. Catalogue material may support a supporting item
  at this class; it may not stand in for a certificate of conformity.
- A record issued by a source outside the franchised chain closes the
  assessment where it stands. The parts are commercial, the chain is short,
  and at this class that certificate is the strongest counterfeit indication
  the receiving bay will ever be handed.
- The denominator is the whole owed set. An item delivered as nothing lowers
  the fraction rather than dropping out of it, so removing a weak item can
  only lower the score -- which is the way round it has to be. Dropping an
  item legitimately is a waiver, and a waiver leaves the owed set before the
  fraction is taken.
- A fraction landing exactly on its floor is inside it. The credits and the
  division can leave the two sides a few ULP apart, and that is
  representation error rather than a short package.

## Workflow

1. Validate the delivery policy: the completeness floor, the marginal band
   above it, the credit a core item owes and whether the date code is part
   of the identity. A band reaching past a complete package, or a core floor
   under the package floor, is refused rather than used.
2. Fix the lot identity the folder is offered against, refusing a blank lot
   identifier or, where the policy asks for one, a blank date code.
3. Assemble the owed set: the core items plus the supporting items no
   recorded acceptance has dropped. Refuse a waiver naming a core item, an
   unregistered item, or carrying no acceptance record.
4. Validate the delivered records, refusing an unregistered item, a
   duplicated item or an unregistered provenance, and record the items the
   lot does not owe rather than crediting them.
5. Dispose each owed item in order: unfranchised source first, then the lot
   match, then the issue reference, then the provenance credit. Report every
   failing list in full rather than stopping at the first entry.
6. Test the core items against the core credit floor once the folder has
   survived authenticity and lot matching.
7. Take the provenance-weighted completeness over the owed set, compare it
   against the floor and the marginal band, and close on one verdict with
   the findings that produced it.

## Pitfalls

- Matching items to the order rather than to the lot. One order line is
  routinely filled from more than one build, and a certificate covering the
  other build covers none of the units in this box.
- Crediting a datasheet nobody archived. The revision is what fixes the
  words the lot was accepted against, and a live page is a moving target
  dressed as a record.
- Letting a catalogue page carry a core item because catalogue pages are
  permitted here. They are permitted as support, and the core credit floor
  is what keeps the distinction.
- Scoring an unfranchised certificate instead of holding the lot. A credit
  of zero still lets a strong folder average over it; the assessment closes
  instead, because the question has stopped being about completeness.
- Averaging only over the items that arrived. Deleting a weak item would
  then raise the score, so the denominator stays the whole owed set and a
  genuine drop goes through the waiver route on the record.
- Treating a missing issue reference as a clerical gap. It is the mechanism
  that ties a named document to the version that covered this lot, and
  without it the lot was accepted against a document that has since moved.

## Behavior contract (gate 3)

The policy validation, the lot identity, the core and supporting split, the
waiver record, the delivered-record validation and the unowed-item report,
the in-full, reduced, unidentified, mismatched, unfranchised and absent
dispositions, the core credit floor, the provenance-weighted completeness,
the marginal band and the receiving verdict are exercised by the gate 3
contract test:
scripts/test_q6013_class_3_manufacturer_data_deliveries.py against
scripts/q6013_class_3_manufacturer_data_deliveries_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6013_class_3_manufacturer_data_deliveries.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

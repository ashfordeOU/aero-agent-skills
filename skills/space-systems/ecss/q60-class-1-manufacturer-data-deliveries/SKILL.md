---
name: q60-class-1-manufacturer-data-deliveries
description: "Verify the manufacturer data package delivered with a class 1 EEE shipment under ECSS-Q-ST-60C clause 4.3.11: derive the record set the lot's radiation duty, delta-qualification status, approved deviations and rework history owe, test every delivered certificate for an authorised signature, lot-code agreement with the box, an issue date at or before dispatch and coverage of the delivered quantity, walk the identity chain the records claim, and return the completeness fraction with one accept, accept-with-actions or hold-shipment disposition. Use when a class 1 delivery is booked in and its paperwork decides whether the parts reach stores. Trigger: ecss, q-st-60c, class-1-certificate-of-conformity, class-1-lot-traceability-chain, class-1-data-package-completeness, manufacturer-record-defect-ranking, class-1-shipment-release-disposition."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-1-manufacturer-data-deliveries, class-1-certificate-of-conformity, class-1-lot-traceability-chain, class-1-data-package-completeness, manufacturer-record-defect-ranking, class-1-shipment-release-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 1 — Manufacturer Data Deliveries (space-systems/ecss/q60-class-1-manufacturer-data-deliveries)

Use when the task is clause 4.3.11 of ECSS-Q-ST-60C: the certificates of
conformity and supporting manufacturer records that travel with a class 1
shipment. This leaf grades one delivery on whether the paperwork in the
envelope actually describes the parts in the box.

## Domain quick reference

- The certificate is not the deliverable; the tie between the certificate and
  the parts is. A perfectly drafted certificate of conformity naming a lot
  code that is not the lot code on the reel proves nothing about the parts
  that arrived, and it is the commonest defect in a data package that looks
  complete on a checklist.
- The owed record set is not fixed. A lot that carries radiation duty, that
  was delta-qualified, that ships against an approved deviation or that was
  reworked each pulls an extra record into the delivery, so the set has to be
  derived from the lot's own history before anything is compared.
- Traceability is a chain, not a label. Wafer lot, assembly lot, date code
  and shipment lot each have to be evidenced; a break at any link leaves every
  finer link unsupported, which is why the gaps are reported coarsest first.
- A record issued after the parts left is a record written about a shipment
  its author had already dispatched. It may still be true, but it was not the
  basis on which the parts were released, and it is graded as a timing defect
  rather than waved through.
- Quantity coverage is a real test. A certificate covering two hundred parts
  against a delivery of two hundred and forty leaves forty parts uncertified,
  and the shortfall is silent unless someone compares the two numbers.
- Defects are weighted, not counted. A missing record, a lot-code mismatch
  and an unsigned certificate stop the shipment; a late issue date or a short
  coverage is worked off after the parts are booked in. Collapsing the two
  groups into one number loses the disposition.

## Workflow

1. Derive the owed record set from the core class 1 certificates plus the
   conditional records the lot's radiation duty, delta-qualification,
   approved deviations and rework history add. An unrecognised condition key
   is an input error, not a silently dropped requirement.
2. Name the owed records that did not arrive, and reject a delivery that
   presents the same record type twice rather than guessing which copy governs.
3. Test each delivered record against the shipment it travels with: issuing
   authority signature, lot-code agreement compared without case sensitivity,
   an issue date at or before dispatch, coverage of the delivered quantity
   with the exact-coverage boundary absorbed by a named tolerance, and any
   superseded issue.
4. Walk the identity chain the records claim and report the links that are
   not evidenced, coarsest first.
5. Return the completeness fraction of the owed set, so a delivery that is
   three quarters there is distinguishable from one that is empty.
6. Rank the findings by severity and close with one disposition: accepted,
   accepted-with-actions, or hold-shipment.

## Pitfalls

- Grading the package against a fixed checklist. The conditional records are
  the ones that go missing, because the checklist was written for a lot
  without radiation duty and nobody revisited it.
- Reading a present record as a valid record. Presence is the cheapest of the
  five tests and the least informative; the signature, the lot code, the date
  and the covered quantity are where deliveries actually fail.
- Comparing lot codes literally. A supplier writing the code in lower case
  has not shipped a different lot, and a mismatch raised on case alone
  discredits every real mismatch the same run reports.
- Accepting the shipment lot link as the whole of traceability. The finest
  link is the easiest to evidence and the least load-bearing; the wafer and
  assembly lots are what tie the parts to their process history.
- Treating a short coverage as a paperwork nicety. The uncovered parts are
  uncertified parts, and they are indistinguishable from the covered ones once
  the reel is opened.
- Counting defects instead of weighting them. Three minor timing findings are
  not worse than one lot-code mismatch, and a count says they are.

## Behavior contract (gate 3)

The owed-record derivation, per-record defect tests, traceability chain walk,
completeness fraction, severity weighting and the delivery disposition are
exercised by the gate 3 contract test:
scripts/test_q60_class_1_manufacturer_data_deliveries.py against
scripts/q60_class_1_manufacturer_data_deliveries_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_manufacturer_data_deliveries.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

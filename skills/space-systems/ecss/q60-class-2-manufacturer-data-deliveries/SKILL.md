---
name: q60-class-2-manufacturer-data-deliveries
description: "Verify the manufacturer data package delivered with a Class 2 EEE shipment under ECSS-Q-ST-60C clause 5.3.11: derive the record set the part category and the lot's screening, radiation, deviation and rework history owe, grade every delivered certificate for an authorised signature, a lot code agreeing with the box, an issue day at or before dispatch and a quantity covering what arrived, weight the graded records into a completeness fraction, and name the mandatory gaps that hold a shipment whatever that fraction says. Use when a Class 2 delivery is booked in and its paperwork decides whether the parts reach stores. Trigger: ecss, q-st-60c, class-2-certificate-of-conformity, class-2-owed-record-set, class-2-record-status-grading, class-2-data-package-completeness-fraction, class-2-shipment-release-disposition."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c, q60-class-2-manufacturer-data-deliveries, class-2-certificate-of-conformity, class-2-owed-record-set, class-2-record-status-grading, class-2-data-package-completeness-fraction, class-2-shipment-release-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 2 — Manufacturer Data Deliveries (space-systems/ecss/q60-class-2-manufacturer-data-deliveries)

Use when the task is clause 5.3.11 of ECSS-Q-ST-60C: the certificate of
conformity and the supporting manufacturer records that travel with a Class 2
shipment, and whether what arrived in the folder lets the parts into stores.

## Domain quick reference

- The owed record set is derived from the lot, not from the purchase order
  boilerplate. A screened lot, a radiation lot acceptance, a delta
  qualification, an approved deviation and a rework each add a record, and a
  lot history flag the register does not carry is refused rather than ignored.
- A certificate is graded against the box it arrived with. The signature, the
  lot code, the issue day against dispatch and the quantity covered are four
  independent questions, and a folder can be complete on three of them.
- The grades are ordered by how far a record is from being usable. A record
  naming another lot is not a signature problem; a record covering fewer parts
  than arrived is not a late one; a summary is not a shortfall in the data.
- Records are weighted. A missing screening data set and a missing packing
  note are both gaps and are not the same gap, so the completeness fraction is
  weighted rather than a count of ticks.
- A summary is credited below the data it points at. It evidences that the
  data exists somewhere; it does not put the data in the folder.
- Some gaps are not tradeable. A shipment without a certificate of conformity
  or without its traceability record is held at any completeness fraction, and
  a high score is the usual way that gap is argued past.

## Workflow

1. Derive the owed record set from the part category and the lot history
   flags, refusing an unrecognised flag.
2. Grade every delivered record against the shipment lot code, the dispatch
   day and the delivered quantity, and mark every owed record that never
   arrived as absent.
3. Refuse a delivered record the shipment does not owe; it usually names
   another lot and is about to be filed against this one.
4. Credit each status, weight the credits by the record register, and take the
   weighted completeness fraction of the owed set.
5. Name the mandatory gaps separately from the fraction.
6. Return the disposition: a mandatory gap holds the shipment; otherwise the
   fraction against the accept and actions thresholds decides between
   accept-into-stores, accept-with-actions and hold-shipment.

## Pitfalls

- Counting records rather than weighting them. Nine light records and a
  missing certificate score well and ship nothing usable.
- Reading a certificate that names another lot as a signature problem. It is
  evidence about a different population and carries no credit at all.
- Accepting a certificate issued after dispatch. It was written from the
  shipping note rather than from the lot, and it is the record most often
  back-dated when the gap is found later.
- Taking a summary as the data. It is worth crediting and it is not worth
  full credit, and a folder of summaries reads as complete.
- Letting a high completeness fraction argue past a missing certificate of
  conformity. The mandatory set is checked before the fraction is read.
- Filing an unowed record because it arrived. A record the shipment does not
  owe is a signal that somebody matched the folder to the wrong box.

## Behavior contract (gate 3)

The owed record derivation, record status grading, absent marking, credit
weighting, completeness fraction, mandatory gaps and the shipment disposition
are exercised by the gate 3 contract test:
scripts/test_q60_class_2_manufacturer_data_deliveries.py against
scripts/q60_class_2_manufacturer_data_deliveries_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_manufacturer_data_deliveries.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

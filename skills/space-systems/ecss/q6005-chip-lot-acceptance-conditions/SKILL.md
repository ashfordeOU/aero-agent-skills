---
name: q6005-chip-lot-acceptance-conditions
description: "Determine whether a delivered batch of bare semiconductor or passive chips meets the traceability, homogeneity and documentation conditions of ECSS-Q-ST-60-05C clause 8.1.4: reconcile the sublot quantities against the delivery note and the order, measure the fraction of dice carrying both a wafer-lot and a diffusion-lot identity, compute the homogeneity ratio as the largest wafer-lot aggregate over the whole delivery, check the delivery documentation set, and return accept, accept-with-reservation or reject with every failing condition named. Use when receiving or dispositioning a bare-die lot. Trigger: ecss, q-st-60-05c, bare-die-lot-acceptance, wafer-lot-homogeneity-ratio, diffusion-lot-traceability, die-delivery-documentation, sublot-quantity-reconciliation, chip-lot-disposition."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-chip-lot-acceptance-conditions, bare-die-lot-acceptance, wafer-lot-homogeneity-ratio, diffusion-lot-traceability, sublot-quantity-reconciliation, chip-lot-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Chips — Delivered Lot Acceptance (space-systems/ecss/q6005-chip-lot-acceptance-conditions)

Use when the task is dispositioning a delivered batch of bare
semiconductor or passive chips under ECSS-Q-ST-60-05C clause 8.1.4 —
deciding whether what arrived satisfies the traceability, homogeneity
and documentation conditions that let it be accepted into stores and
built into a hybrid.

## Domain quick reference

- A delivery is not one undifferentiated pile of dice. It arrives as
  sublots, each of which came from a particular wafer lot and, inside
  that, a particular diffusion lot. The acceptance conditions are all
  statements about that structure, so the structure is what gets
  graded, not the total count on the delivery note.
- Traceability is a per-die property measured over the whole delivery.
  A die whose wafer lot or diffusion lot is unknown cannot be tied back
  to the process history, the wafer acceptance data or a future alert,
  and no incoming inspection recovers that — the identity was lost
  upstream. Coverage short of the whole delivery therefore refuses the
  batch rather than reducing its grade.
- Homogeneity is what lets the sample speak for the population. Wafer
  lot acceptance data, and any screening done on a sample, characterise
  the lot they came from; a delivery spanning two wafer lots has two
  populations in one container and one set of data. The homogeneity
  ratio — the largest wafer-lot aggregate over the whole delivery —
  makes that visible as a number, and only an order that permitted
  multiple lots can carry a split delivery as a reservation.
- Quantity has two independent checks, and they fail differently. The
  sublots have to sum to the quantity the delivery note declares, and
  the delivered quantity is compared with the ordered quantity. The
  first is the paperwork disagreeing with the goods, which invalidates
  every other statement on that note; the second is a commercial
  shortfall or overage, which does not.
- The documentation set travels with the batch: the certificate of
  conformity, the wafer lot acceptance data, the visual inspection
  record, the packaging and storage record and the ESD handling record.
  A missing document is not a paperwork chase to be closed later — the
  condition it evidences is unverified until it arrives.
- The disposition is three-way on purpose. Accept, accept-with-
  reservation and reject carry different downstream obligations, and
  collapsing the middle one either blocks usable material or lets a
  split lot into stores unmarked.

## Workflow

1. Validate the delivery as sublots, each with a positive integer
   quantity. An absent or placeholder lot identity normalises to
   unknown rather than raising: an untraceable delivery is a real case
   to be graded, not an input error to be refused at the door.
2. Reconcile the quantities: sum the sublots, compare with the declared
   delivery-note quantity where one is given, and compare with the
   ordered quantity. Keep the two findings separate.
3. Measure traceability coverage as the quantity-weighted fraction of
   dice carrying both a wafer-lot and a diffusion-lot identity, so one
   small untraceable sublot is not diluted by a large clean one.
4. Aggregate the delivery by wafer lot, largest first, and take the
   homogeneity ratio from the largest aggregate over the total.
5. Check the documentation set, matching names insensitively to case and
   separator so a differently punctuated certificate still counts.
6. Sort the findings into rejections and reservations: lost
   traceability, missing documentation, paperwork that does not describe
   the goods, and an unpermitted split lot reject; a permitted split lot
   and a quantity mismatch against the order reserve.
7. Return the disposition with the coverage, the homogeneity ratio, the
   lot breakdown and every failing condition named, so the decision can
   be reproduced and the supplier told exactly what to correct.

## Pitfalls

- Reading the delivery-note total as the delivered quantity. The note is
  a claim; the sublots are the goods. When they disagree, the note's
  other statements — lot identities included — are unverified too.
- Counting untraceable sublots instead of untraceable dice. Coverage is
  weighted by quantity, and one sublot of a thousand dice missing its
  diffusion lot is not the same finding as one sublot of ten.
- Accepting a split delivery because both wafer lots are individually
  traceable. Traceability and homogeneity are separate conditions: the
  dice can be perfectly identified and still be two populations against
  one set of acceptance data.
- Treating a missing document as an administrative follow-up. Each
  document is the evidence for a condition; until it arrives, that
  condition is unknown, and unknown is not met.
- Collapsing accept-with-reservation into accept. A permitted split lot
  accepted without its reservation loses the one record that tells the
  assembly line to keep the sublots segregated.
- Re-grading a rejected batch by inspecting harder. A lost lot identity
  is not recoverable downstream; the correct response is a replacement
  delivery or the supplier's own traceability record, not more
  measurement.

## Behavior contract (gate 3)

The sublot validation, quantity reconciliation, quantity-weighted
traceability coverage, wafer-lot homogeneity ratio, documentation check
and the three-way disposition are exercised by the gate 3 contract test:
scripts/test_q6005_chip_lot_acceptance_conditions.py against
scripts/q6005_chip_lot_acceptance_conditions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_chip_lot_acceptance_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q7022-procurement-data-requirements
description: "Evaluate the procurement data package a limited-shelf-life material lot arrives with under ECSS-Q-ST-70-22C: check the mandatory items that fix an expiry date, cross-check the manufacture, receipt and expiry chain against any declared duration, convert it into remaining shelf life at receipt in days and as a fraction of the full life, grade the recorded storage temperature and humidity envelope against the specified limits, and close with an accept, accept-with-actions or reject disposition. Use when writing purchase-order data requirements for adhesives, sealants, propellants or elastomers, or grading a goods-in delivery. Trigger: ecss, q-st-70-22c, shelf-life-procurement-data-items, shelf-life-remaining-at-receipt, shelf-life-storage-evidence-envelope, shelf-life-goods-in-disposition, limited-shelf-life-material-lot."
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
  tags: [ecss, q-st-70-22c-limited-shelf-life-control, q-st-70-22c, q7022-procurement-data-requirements, shelf-life-procurement-data-items, shelf-life-remaining-at-receipt, shelf-life-storage-evidence-envelope, shelf-life-goods-in-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limited Shelf Life — Procurement Data Requirements (space-systems/ecss/q7022-procurement-data-requirements)

Use when the task is the procurement clause of ECSS-Q-ST-70-22C: deciding what
a purchase order has to demand from the supplier of a limited-shelf-life
material, and grading the package a delivered lot actually turns up with.

## Domain quick reference

- A shelf life is not a property of a material, it is a property of a lot. It
  starts at a manufacture date that only the supplier holds, so a purchase
  order that does not demand that date buys a material with no usable expiry
  at all. The batch identifier is what binds the date to the drum in stores.
- The expiry date and the manufacture date are two statements of the same
  fact, and a declared shelf-life duration is a third. When the three do not
  agree the lot has a paperwork defect, not a rounding difference; the
  cheapest place to find it is goods-in, before the drum is decanted.
- Remaining life at receipt is the number the purchase order can actually set
  a threshold against. Expressed as a fraction of the full life it is
  comparable across a 90-day primer and a three-year elastomer, which is why
  the acceptance threshold is written as a fraction rather than in days.
- Two thresholds are needed, not one. Above the target fraction the lot can
  go straight to stores; between the target and the floor it is usable but
  the work has to be planned against the shortened window; below the floor
  there is not enough life left to plan against and the lot goes back.
- Storage evidence answers a different question from the dates. A lot inside
  its expiry that spent a week on a sunlit dock has consumed more of its life
  than the calendar says, so the recorded temperature and humidity envelope is
  graded against the specified one and an excursion outranks a fresh date.
- Absent evidence is not clean evidence. A delivery with no recorded envelope
  cannot be assumed nominal; it is a finding that costs the lot its clean
  acceptance even when every date is in order.

## Workflow

1. Check the mandatory data items first: manufacturer, batch identifier,
   manufacture date, expiry date and conformity certificate. A lot missing any
   of them is refused before any arithmetic runs, because the arithmetic would
   be inventing the number it is missing.
2. Parse the manufacture, receipt and expiry dates and cross-check their
   order. An expiry that does not follow manufacture, a receipt before
   manufacture, or a lot already past expiry on arrival each stop the
   assessment at a reject.
3. Compare any declared shelf-life duration with the interval the two dates
   span, allowing a one-day rounding difference and no more.
4. Compute the full shelf life in days, the days left at receipt, and their
   ratio; categorize the ratio as adequate, short or insufficient against the
   target and floor fractions, absorbing an exact boundary with a named
   tolerance rather than by moving the threshold.
5. Grade the recorded storage temperature and humidity envelope against the
   specified limits, and raise a finding when no envelope was delivered at all
   or when one arrives with no specified limit to grade it against.
6. Close with a single disposition: accept only when nothing was found, reject
   on a storage excursion or an insufficient remaining life, accept-with-actions
   otherwise, and report every finding that produced it.

## Pitfalls

- Accepting an expiry date with no manufacture date behind it. The expiry
  alone cannot be re-derived, re-verified after a storage excursion, or used
  to grant an extension later, so the lot becomes unauditable the moment the
  supplier's own record is out of reach.
- Writing the acceptance threshold in days. A fixed 90-day residue is most of
  the life of a primer and a rounding error on an elastomer; the threshold
  belongs on the fraction so one purchase-order clause covers both.
- Treating a single threshold as sufficient. Collapsing the target and the
  floor into one number either sends back usable material or takes in lots
  whose remaining window cannot carry the planned work.
- Reading an in-date lot as a compliant one. Dates and storage evidence answer
  different questions, and a thermal excursion consumes life the calendar
  never shows; an excursion is a reject even on a lot delivered fresh.
- Treating a missing storage record as a nominal one. Unknown is not nominal,
  and the finding is what forces the supplier to start recording.
- Relaxing the acceptance fraction to let an exactly-on-threshold lot through.
  The equality is a representation question handled by the tolerance inside
  the comparison; the procured threshold stays as specified.

## Behavior contract (gate 3)

The mandatory-item check, date-chain validation, declared-duration
cross-check, remaining-life arithmetic and grading, storage-envelope grading
and the disposition are exercised by the gate 3 contract test:
scripts/test_q7022_procurement_data_requirements.py against
scripts/q7022_procurement_data_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7022_procurement_data_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

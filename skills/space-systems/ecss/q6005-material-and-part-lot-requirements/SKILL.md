---
name: q6005-material-and-part-lot-requirements
description: "Determine whether a delivered batch of material or piece parts may enter hybrid manufacture under ECSS-Q-ST-60-05C clause 9.4: compute the batch age at receipt and the shelf life left against the planned time to use, test the observed storage temperatures against the declared storage regime, confirm the lot carries one manufacturing identity, check the lot documentation owed by that item category, and return release, conditional-release or quarantine with every failing condition named. Use when receiving or dispositioning a hybrid material or piece-part batch. Trigger: ecss, q-st-60-05c, hybrid-material-lot-acceptance, limited-life-shelf-life-remaining, hybrid-storage-temperature-excursion, piece-part-lot-identity, hybrid-lot-disposition."
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
  tags: [ecss, q-st-60-05-hybrid-materials-and-parts, q6005-material-and-part-lot-requirements, hybrid-material-lot-acceptance, limited-life-shelf-life-remaining, hybrid-storage-temperature-excursion, piece-part-lot-identity, hybrid-lot-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Delivered Material and Part Lot Acceptance (space-systems/ecss/q6005-material-and-part-lot-requirements)

Use when the task is dispositioning a delivered batch of material or piece
parts at goods-in under ECSS-Q-ST-60-05C clause 9.4 — deciding whether what
arrived may be booked into stores and drawn against a hybrid build, held under
a restriction, or stopped before it reaches the assembly line.

## Domain quick reference

- The conditions are batch conditions, not item conditions. A qualified
  adhesive from an approved supplier against an approved specification still
  arrives as a particular tub with a particular manufacture date and a
  particular transport history, and it is that batch which is either usable or
  not. The specification was graded before the order; this is the delivery.
- Shelf life is asked twice, and the two questions have different answers. Is
  the batch in date at receipt, and does what is left still reach the day it is
  planned to be used? A batch with six weeks left is perfectly in date and
  entirely useless to a build that starts in two months.
- The reserve fraction is the third question underneath those two. A batch
  arriving with a tenth of its declared life unspent is in date, may well cover
  the planned use, and is still not what the project thought it was buying —
  the restriction is what records that without pretending the material is bad.
- A cold-chain excursion is not recoverable. Retest measures the property today
  and says nothing about the ageing the excursion started, so an observed
  temperature outside the declared regime quarantines the batch rather than
  triggering more measurement. That is why the regime is taken from the
  specification and an undeclared regime cannot be graded at all.
- One manufacturing lot per batch is what lets the lot acceptance data speak
  for the material. Two lots in one container is two populations against one
  certificate; it is a refusal unless the order allowed for it, and where it
  was allowed it is a segregation restriction, never a clean release.
- The documentation owed depends on the item. Every batch owes a certificate of
  conformity, a lot identification record and a storage and handling record; an
  adhesive adds a certificate of analysis and a batch cure verification, a wire
  adds spool and breaking-load records, a substrate adds dimensional and
  adhesion records. A document that has not arrived is a condition that is
  unverified, and unverified is not met.
- Three dispositions exist because the downstream obligations differ. Release,
  conditional-release and quarantine carry different stores actions, and
  collapsing the middle one either blocks usable material or lets a short-dated
  batch into the racks with nothing recording why it must be used first.

## Workflow

1. Validate the batch: a reference, a known procured item category, real
   calendar manufacture and receipt dates, the lot identities, the declared
   storage regime with the temperatures observed, and the documents received.
   A limited-life category with no declared shelf life is an input error.
2. Compute the age at receipt and the life remaining, in days and as the
   fraction of the declared life still unspent.
3. Ask the cover question separately: does the remaining life reach the planned
   time to use?
4. Compare the observed temperature extremes with the window the declared
   regime holds, naming a floor breach and a ceiling breach separately.
5. Confirm a single manufacturing lot identity, or a permitted split.
6. Check the documentation the category owes, matching names insensitively to
   case and separator.
7. Sort the findings: an excursion, a missing document, an unpermitted split
   and an out-of-date batch quarantine; a permitted split, a life short of the
   planned use and a life below the reserve restrict.
8. Return the disposition with the life figures, the storage comparison, the
   lot breakdown and every failing condition named, then roll a delivery of
   several batches up into one goods-in view.

## Pitfalls

- Reading "in date" as "usable". In date is a statement about today; the build
  happens later, and the cover check is the one that matters to the plan.
- Treating a storage excursion as a retest case. The retest passes and the
  ageing clock still moved; the excursion is a quarantine, not a measurement
  problem.
- Grading against a regime nobody declared. An ambient default quietly passes
  every refrigerated material that was shipped warm, which is exactly the
  failure the regime exists to catch.
- Accepting a split batch because both lots are individually traceable.
  Traceability and single-lot homogeneity are separate conditions: the material
  can be perfectly identified and still be two populations against one
  certificate of analysis.
- Chasing a missing certificate of analysis as paperwork. Each document is the
  evidence for a condition, and the condition stays unverified until it lands.
- Collapsing conditional-release into release. A short-dated batch released
  without its restriction loses the one record that tells stores to issue it
  first, and it ages out on the shelf behind a fresher one.
- Applying one document list to every category. A bonding wire with no cure
  verification is complete; an adhesive with no cure verification is not.

## Behavior contract (gate 3)

The batch validation, shelf-life arithmetic at receipt and at point of use, the
reserve fraction, the storage-regime comparison, the single manufacturing lot
condition, the category-driven documentation check, the three-way disposition
and the goods-in roll-up are exercised by the gate 3 contract test:
scripts/test_q6005_material_and_part_lot_requirements.py against
scripts/q6005_material_and_part_lot_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_material_and_part_lot_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

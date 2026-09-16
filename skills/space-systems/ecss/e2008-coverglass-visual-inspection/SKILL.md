---
name: e2008-coverglass-visual-inspection
description: "Use when a coverglassed assembly has been examined and each item needs a screened disposition. Verify every coverglass fitted to a photovoltaic assembly against the assembly defect criteria of ECSS-E-ST-20-08C clause 5.5.3.2.6: compute how much of the active cell area the glass still covers and how much overhang an edge chip has left to work through, then disposition each edge chip, surface scratch, cavity or inclusion, coating blemish, crack and surface deposit as accept, clean-and-reinspect, refer-for-review or reject, add the accepted defects up against the cumulative area and count allowances, and hold the assembly open until every coverglass carries a record. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-6, coverglass-defect-criteria-screening, coverglass-edge-chip-allowance, coverglass-active-area-coverage, coverglass-inclusion-limits, per-coverglass-inspection-completeness."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-visual-inspection, coverglass-defect-criteria-screening, coverglass-edge-chip-allowance, coverglass-active-area-coverage, coverglass-inclusion-limits, per-coverglass-inspection-completeness, solar-cell-assembly-optical-defects]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Visual Inspection (space-systems/ecss/e2008-coverglass-visual-inspection)

Use when the task is the coverglass screen of ECSS-E-ST-20-08C clause
5.5.3.2.6 -- checking each coverglass on the assembly against the
defect criteria agreed for it, and keeping the assembly open until
every one of them has been looked at.

## Domain quick reference

- The screen is per item and exhaustive. A sampled coverglass check
  answers a different question from the one the clause asks, so the
  count of records is compared against the declared number of
  coverglasses and a short set leaves the assembly open no matter how
  clean the inspected ones were.
- Two judgements run per coverglass. The first is geometric: does the
  glass still sit over the active cell area, with an overhang on every
  edge. The second is the defect screen proper against the criteria.
- The overhang is not decoration. It is the distance an edge chip has
  to travel before it opens the cell to the environment, so the chip
  allowance is expressed as a fraction of the measured overhang rather
  than as an absolute number. A coverglass placed off-centre keeps its
  nominal size and loses the allowance on the tight side.
- Defect kinds separate by mechanism, not by appearance. A crack runs
  through the glass and grows under thermal cycling, so it rejects. An
  edge chip is bounded by the overhang. A scratch is bounded on width
  first -- a wide score line is a stress raiser, and its length only
  matters once the width is inside the limit. A cavity or inclusion is
  bounded on its largest dimension, a coating blemish on its area.
- A removable deposit is not a defect of the glass. It is cleaned and
  the coverglass is inspected again, and it does not count toward the
  permanent defect area; a deposit that will not come off stays in the
  optical path and goes to review.
- Small accepted defects still accumulate. A cumulative defect-area
  fraction and a count allowance per coverglass catch the item that
  passed every individual limit and is nevertheless covered in marks.

## Workflow

1. Take the declared coverglass count for the assembly and the
   inspection records. Reject a record set larger than the declared
   count, and report the shortfall when it is smaller.
2. For each coverglass, compute the coverage of the active cell area
   from the cell and glass dimensions and the placement offsets, and
   take the smallest of the four overhangs as the working margin.
3. Screen every defect against its own rule, using that margin for the
   edge-chip allowance, and record the reason whenever a defect leaves
   the accept band.
4. Take the worst disposition on the coverglass, then apply the
   coverage rule: an active area left uncovered beyond the allowance
   rejects the item whatever the defect list says.
5. Sum the permanent defect area, compare the fraction and the
   accepted-defect count against the per-coverglass allowances, and
   escalate to review when either is exceeded.
6. Roll up: the worst coverglass verdict, the identifiers that are not
   accepted, and the completeness flag. The assembly closes only when
   the record set is complete and nothing is outstanding.

## Pitfalls

- Sampling. The clause asks for every coverglass, and a sampled screen
  reports a verdict the evidence does not support.
- Judging an edge chip against a fixed millimetre limit. The number
  that matters is how much overhang is left at that edge, and an
  off-centre coverglass has less of it on one side than the drawing
  suggests.
- Screening defects and never checking placement. A perfectly clean
  coverglass that sits off its cell leaves active area exposed, and
  only the geometry catches it.
- Grading a scratch on length. Width decides whether the mark is a
  stress raiser in the glass; a short wide score is the worse of the
  pair.
- Counting a removable deposit as a permanent defect, or accepting the
  item without the re-inspection after cleaning. Neither records what
  the coverglass actually is.
- Accepting an item because every defect passed. The cumulative area
  fraction and the count allowance exist for exactly that case.
- Comparing a measurement with a derived allowance by bare arithmetic.
  The allowance is a product of a criteria value and a measured
  margin, so a measurement exactly on it can evaluate a few units in
  the last place above it; the comparison absorbs that representation
  error while the allowance stays untouched.

## Behavior contract (gate 3)

The coverage geometry, per-kind defect dispositioning, chip allowance
against the measured overhang, cumulative area and count allowances and
the assembly completeness rollup are exercised by the gate 3 contract
test: scripts/test_e2008_coverglass_visual_inspection.py against
scripts/e2008_coverglass_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

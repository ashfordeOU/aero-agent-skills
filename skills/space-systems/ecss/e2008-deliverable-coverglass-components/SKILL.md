---
name: e2008-deliverable-coverglass-components
description: "Use when a coverglass delivery lot, route record or inspection dossier has to be released. Audit a coverglass delivery batch by batch against the processing and inspection route clause 8.3.2 of ECSS-E-ST-20-08C fixes in the process document: resolve whether the cited document governs at the issue the glass was built to, name a step run that the document never declares, catch a declared step run out of the declared sequence, separate a per-coverglass screen from a sampled inspection and hold each sample against its floor, bracket how many pieces passed every screen rather than quoting one number, and weight the release share by pieces. Trigger: ecss, e-st-20-08c, coverglass-delivery-batch-disposition, coverglass-process-document-standing, coverglass-undeclared-route-step, coverglass-route-sequence-violation, coverglass-screen-versus-sample-mode, coverglass-deliverable-count-bracket."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-deliverable-coverglass-components, coverglass-delivery-batch-disposition, coverglass-process-document-standing, coverglass-undeclared-route-step, coverglass-route-sequence-violation, coverglass-screen-versus-sample-mode, coverglass-deliverable-count-bracket]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Deliverable Coverglass Components (space-systems/ecss/e2008-deliverable-coverglass-components)

Use when the task is the delivery rule of ECSS-E-ST-20-08C clause 8.3.2 --
whether the coverglasses being handed over were taken through the processing
and inspection route their process document fixes, and how many pieces that
actually releases.

## Domain quick reference

- What is delivered is not a quantity of glass. It is a population made by an
  ordered route the customer approved and released by the inspections that
  route calls for, so the build paperwork decides the delivery before a single
  piece is counted.
- Coverglasses arrive as batches -- a forming batch, a coating run, a cutting
  run -- each with its own route record and its own piece count. The release
  question is answered per batch, then weighted by the pieces each one carries.
  One bad batch of twenty pieces and one clean batch of two thousand is not
  half a delivery.
- Document standing has three outcomes, not two. An approved document at the
  issue the glass was built to governs. A draft or a withdrawn document governs
  nothing and its batch does not release at all. A superseded document, or an
  approved one at a different issue, governs enough to release under a written
  concession once the difference is dispositioned.
- A step used in the build and absent from the document is an undeclared
  process whatever its merits, and it takes the batch off document. The reverse
  -- a declared step this batch did not need -- is a note.
- Order is load-bearing for coated glass in a way it is not for a piece part. A
  coating laid down before the clean that was meant to precede it is a
  different article from the one the document describes, even though both
  routes list the same two steps in the same set.
- Inspection mode decides what a record is worth. A per-coverglass screen is
  run on every piece and removes the ones that fail; a sampled inspection is
  run on a few and speaks for the rest. A sample cannot discharge a screen, and
  a screen run on a sample is a screen that did not happen.
- The two modes also fail differently. Yield loss inside a screen is normal:
  the failed pieces simply are not delivered. A single failure inside a sample
  is not yield, it is evidence about the population the sample stood for, and
  it puts the whole batch in doubt.
- The sampling floor is worked out in integer arithmetic on purpose. A floor
  taken through a square root in floating point lands on different integers on
  different platforms exactly when the batch count is a perfect square.
- Counts alone do not settle how many pieces passed every screen. Two screens
  reporting two and five failures may have failed the same pieces or different
  ones, so the deliverable count is bracketed -- at most the smallest pass
  count, at least the batch less every failure and every coverage gap -- and
  the lower bound is what is released against.

## Workflow

1. Take the delivery as a list of batches, each carrying its identifier, its
   piece count, the process document it cites with the approved and built
   issues, the declared route, the route actually run, and its inspection
   records.
2. Resolve the document standing for each batch: governing at the built issue,
   governing off issue, or not governing.
3. Compare the route run against the route declared three ways: undeclared
   steps, declared steps not needed, and declared steps run out of sequence.
4. Grade each inspection record against the batch it was run on: check the mode
   is the one the inspection is owed in, check a screen covered every piece and
   a sample reached its integer sampling floor, and split failures into yield
   loss and sample evidence.
5. Name every owed inspection that no record carries a result for.
6. Bracket the deliverable piece count from the per-coverglass screens and
   report the bracket, the coverage gaps and the lower bound together.
7. Disposition the batch: a non-governing document, an undeclared or
   out-of-sequence step, a missing or wrong-mode inspection, a failed sample or
   an undersized sample withholds it; an off-issue document or a partial screen
   releases it under concession; anything else releases it.
8. Roll the delivery up on pieces, not on batches: total, released, share, the
   batches withheld, the batches under concession, the weakest batch and one
   verdict.

## Pitfalls

- Releasing on a travelling sheet that lists the inspections rather than
  records their results. A listed inspection with no result is a missing one.
- Accepting a draft process document because the route looks right. Nobody
  signed it, so nothing binds the supplier to keep building that way.
- Treating a superseded document as approved. It was approved once, which is
  exactly why the difference between the two issues has to be looked at.
- Reading the route as a set of steps. Coating before cleaning and cleaning
  before coating use the same two steps and do not make the same article.
- Waving through a step nobody declared. The step may be an improvement and it
  is still outside the process the customer qualified.
- Letting a sampled inspection discharge a per-coverglass screen. The sample
  never looked at the pieces that are about to ship.
- Reading a sample failure as yield. It is evidence about every piece the
  sample stood for, and removing the failed piece does not remove the evidence.
- Quoting one deliverable count from several screens. The failures may or may
  not overlap, and stating the optimistic number as fact over-releases the
  batch.
- Forgetting the pieces no screen ever recorded. They are neither passes nor
  failures, and counting them as either is a choice made by accident.
- Averaging batch dispositions instead of weighting them by pieces. A small bad
  batch and a large clean one are not an average.
- Comparing a release share with its threshold by bare arithmetic. Both are
  quotients of counts and a delivery exactly on the threshold can evaluate a
  few units in the last place under it; the comparison absorbs that while the
  threshold stays as written.

## Behavior contract (gate 3)

The document standing resolution, the three-way route comparison including the
sequence check, the integer sampling floor, per-coverglass versus sampled
inspection grading, the owed-inspection completeness check, deliverable count
bracketing, batch disposition and the piece-weighted delivery roll-up are
exercised by the gate 3 contract test:
scripts/test_e2008_deliverable_coverglass_components.py against
scripts/e2008_deliverable_coverglass_components_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_deliverable_coverglass_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

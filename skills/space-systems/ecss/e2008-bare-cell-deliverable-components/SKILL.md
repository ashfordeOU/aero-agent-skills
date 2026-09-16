---
name: e2008-bare-cell-deliverable-components
description: "Use when a bare-cell delivery batch is presented and the build and inspection records have to carry it. Audit a bare solar cell delivery sub-lot by sub-lot against the process identification document clause 7.1.2 of ECSS-E-ST-20-08C requires, confirming the cells were processed and inspected under it: resolve whether the cited document is approved and at the issue built to, refuse a build carrying a step the document never declares, separate a per-cell screen from a sampled inspection, bracket how many cells passed every screen rather than quoting one number, and weight the release share by cells. Trigger: ecss, e-st-20-08c, bare-cell-delivery-sub-lot-disposition, bare-cell-process-identification-document-standing, bare-cell-undeclared-process-step, bare-cell-screen-versus-sample-mode, bare-cell-deliverable-count-bracket, bare-cell-weighted-release-share."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-bare-cell-deliverable-components, bare-cell-delivery-sub-lot-disposition, bare-cell-process-identification-document-standing, bare-cell-undeclared-process-step, bare-cell-screen-versus-sample-mode, bare-cell-deliverable-count-bracket, bare-cell-weighted-release-share]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Bare Cell Deliverable Components (space-systems/ecss/e2008-bare-cell-deliverable-components)

Use when the task is the delivery rule of ECSS-E-ST-20-08C clause 7.1.2 --
whether the bare cells being handed over were processed and inspected under
the approved process identification document, and how many of them that
actually releases.

## Domain quick reference

- What is delivered is not a quantity of cells. It is a population made by the
  process the customer approved and inspected by the inspections that process
  calls for, so the build paperwork decides the delivery before any cell is
  counted.
- Bare cells arrive as sub-lots -- a wafer run, a coating run, a metallization
  run -- each with its own build record and its own cell count. The release
  question is answered per sub-lot, then weighted by the cells each one
  carries. A delivery of one bad sub-lot of twenty cells and one clean sub-lot
  of two thousand is not half released.
- Document standing has three outcomes, not two. An approved document at the
  issue the cells were built to governs. A draft or a withdrawn document
  governs nothing and its sub-lot does not release at all. A superseded
  document, or an approved one at a different issue, governs enough to release
  under a written concession once the difference is dispositioned.
- A process step used in the build and absent from the document is an
  undeclared process whatever its merits, and it takes the sub-lot off
  document. The reverse -- a declared step not used -- is a note; the document
  covers more than the build needed.
- Inspection mode is load-bearing. A per-cell screen is run on every cell and
  removes the ones that fail; a sampled inspection is run on a few and speaks
  for the rest. A sample cannot discharge a screen, and a screen run on a
  sample is a screen that did not happen.
- The two modes fail differently. Yield loss inside a screen is normal: the
  failed cells simply are not delivered. A single failure inside a sample is
  not yield, it is evidence about the population the sample stood for, and it
  puts the whole sub-lot in doubt.
- Counts alone do not determine how many cells passed every screen. Two
  screens reporting two and five failures may have failed the same cells or
  different ones, so the deliverable count is bracketed -- at most the smallest
  pass count, at least the cell count less every failure -- and the lower bound
  is what is released against. Cells with no screen record at all lower that
  bound further.

## Workflow

1. Take the delivery as a list of sub-lots, each carrying its identifier, its
   cell count, the process document it cites with the approved and built
   issues, the steps actually used, the steps the document declares, and its
   inspection records.
2. Resolve the document standing for each sub-lot: governing at the current
   issue, governing off issue, or not governing.
3. Compare the steps used against the steps declared. Name every undeclared
   step; list the declared-but-unused ones without penalty.
4. Grade each inspection record against the sub-lot it was run on: check the
   mode is the one the inspection is owed in, check a screen covered every
   cell and a sample reached its sampling floor, and split failures into yield
   loss and sample evidence.
5. Bracket the deliverable cell count from the per-cell screens and report the
   bracket, the unrecorded cells and the lower bound together.
6. Disposition the sub-lot: not-governing document, undeclared step, missing
   or wrong-mode inspection, a failed sample or an undersized sample withholds
   it; an off-issue document or a partial screen releases it under concession;
   anything else releases it.
7. Roll the delivery up on cells, not on sub-lots: total, released, share, the
   sub-lots withheld, the sub-lots under concession, and one verdict.

## Pitfalls

- Releasing on a travelling sheet that lists the inspections rather than
  records their results. A listed inspection with no result is a missing one.
- Accepting a draft process document because the content looks right. Nobody
  signed it, so nothing binds the supplier to keep building that way.
- Treating a superseded document as approved. It was approved once, which is
  exactly why the difference between the two issues has to be looked at.
- Waving through a process step nobody declared. The step may be an
  improvement and it is still outside the process the customer qualified.
- Letting a sampled inspection discharge a per-cell screen. The sample never
  looked at the cells that are about to ship.
- Reading a sample failure as yield. It is evidence about every cell the
  sample stood for, and removing the failed cell does not remove the evidence.
- Quoting one deliverable count from several screens. The failures may or may
  not overlap, and stating the optimistic number as fact over-releases the
  sub-lot.
- Forgetting the cells no screen ever recorded. They are neither passes nor
  failures, and counting them as either is a choice made by accident.
- Averaging sub-lot dispositions instead of weighting them by cells. A small
  bad sub-lot and a large clean one are not an average.
- Comparing a release share with its threshold by bare arithmetic. Both are
  quotients of counts and a delivery exactly on the threshold can evaluate a
  few units in the last place under it; the comparison absorbs that while the
  threshold stays as written.

## Behavior contract (gate 3)

The document standing resolution, process-step declaration coverage,
per-cell versus sampled inspection grading, sampling-floor check, deliverable
count bracketing, sub-lot disposition and the cell-weighted delivery rollup
are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_deliverable_components.py against
scripts/e2008_bare_cell_deliverable_components_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_deliverable_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

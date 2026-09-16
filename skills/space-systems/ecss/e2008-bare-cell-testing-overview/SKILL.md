---
name: e2008-bare-cell-testing-overview
description: "Use when a bare-cell test matrix, qualification schedule or batch sampling plan has to be graded. Evaluate a bare solar cell test programme against the two errands clause 7.1.1 of ECSS-E-ST-20-08C puts on it, qualification of the cell design and procurement of a delivery batch: hold each declared activity to the errand it serves, check the specimen kind that errand allows and refuse a destructive run on a cell meant for delivery, size each sample against a floor that grows with the batch for procurement and stays fixed for qualification, measure coverage per errand, and return one programme verdict. Trigger: ecss, e-st-20-08c, bare-solar-cell-test-programme, bare-cell-qualification-and-procurement-errands, bare-cell-batch-sampling-floor, bare-cell-test-specimen-eligibility, bare-cell-destructive-test-allocation, bare-cell-programme-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-bare-cell-testing-overview, bare-solar-cell-test-programme, bare-cell-qualification-and-procurement-errands, bare-cell-batch-sampling-floor, bare-cell-test-specimen-eligibility, bare-cell-destructive-test-allocation, bare-cell-programme-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Bare Cell Testing Overview (space-systems/ecss/e2008-bare-cell-testing-overview)

Use when the task is the bare-cell test programme of ECSS-E-ST-20-08C clause
7.1.1 -- the tests carried out to qualify a bare solar cell and the tests
carried out to procure a batch of them -- and the declared matrix has to be
graded rather than merely listed.

## Domain quick reference

- A bare cell is the cell before coverglass, interconnector or adhesive. Its
  test programme therefore says nothing about the assembly built from it, and
  an assembly-level result cannot be read back down onto the cell.
- The programme serves two errands that share a vocabulary and almost nothing
  else. Qualification asks whether this cell design, from this line, survives
  the mission; it is answered once per design and process baseline. Procurement
  asks whether the batch being bought is the same cell that was qualified; it
  is answered every batch. Reading a result across the two is the single most
  common way a programme looks complete and is not.
- The specimen follows the errand. A qualification answer needs cells drawn
  from the lot set aside for qualification, or witness cells built alongside
  them; a procurement answer needs cells sampled from the batch being bought.
  A cell destined for delivery is the product, not a test article, and the
  moment a destructive activity is pointed at one the deliverable is gone.
- Sample sizes scale differently per errand, and for a reason. A procurement
  sample speaks for a batch, so its floor grows with the batch. A qualification
  sample speaks for a design, so its floor is fixed and adding cells to it buys
  very little. Sizing both the same way over-samples one and under-samples the
  other.
- A sampling floor derived from a square root is computed in integers. The
  square root of a perfect square can land a hair under the exact root on one
  platform and exactly on it on another, which moves a floor by a whole cell
  and turns an adequate sample into a finding on one machine only.
- The environments -- humidity, thermal cycling, particle irradiation,
  ultraviolet exposure, reverse bias -- sit on the qualification side and
  consume their specimens. The measurements -- visual, dimensional, electrical
  performance, mass -- sit on both sides and do not.
- Coverage is per errand, never pooled. A programme can be complete for
  procurement and empty for qualification while showing a healthy total
  activity count, so the totals are reported separately and the shortfall is
  named by activity.

## Workflow

1. Take the batch size the programme is written against and the declared
   activity list, each activity carrying its errand, its specimen kind and its
   sample size.
2. Per activity, check the specimen kind against the errand: refuse a
   qualification answer read off a procurement sample, and refuse any activity
   pointed at a cell destined for delivery.
3. Derive the sample floor for that errand and batch, in integer arithmetic,
   and compare the declared sample with it. Report a sample larger than the
   batch separately from a sample under the floor -- they are different
   mistakes.
4. Mark each activity as required for its errand or supplementary, so an
   extra measurement is carried as an addition rather than mistaken for
   coverage of something else.
5. Count coverage per errand over that errand's own required set, crediting
   only activities that are themselves acceptable; an activity on the wrong
   specimen covers nothing.
6. Report the qualification share of the declared programme, so a matrix that
   is almost entirely batch measurement is visible as such.
7. Roll up: an unacceptable activity or an errand under its coverage threshold
   makes the programme not acceptable; supplementary activities alone make it
   acceptable with findings.

## Pitfalls

- Reading a qualification conclusion off a procurement sample. The sample was
  drawn to show a batch matches a design, and it cannot show the design was
  ever right.
- Running a destructive activity on cells that are going to be delivered. The
  test passes and the deliverable is consumed, which is why the specimen kind
  is checked before the sample size.
- Sizing a qualification sample from the batch. It speaks for a design, so
  scaling it with the purchase order adds cost and no evidence.
- Sizing a procurement sample from a fixed number. A small fixed sample stops
  being representative as soon as the batch grows.
- Computing a square-root sampling floor in floating point. On a perfect
  square the result can differ by one between platforms, and the sample that
  passed locally becomes a finding in CI.
- Pooling coverage across the two errands. A single completeness percentage
  hides an empty qualification column behind a full procurement one.
- Crediting an activity that was declared but placed on an ineligible
  specimen. It appears in the matrix, it consumed a specimen, and it covers
  nothing.
- Treating a supplementary measurement as coverage. It may be genuinely
  useful and it still does not discharge a required activity.
- Comparing a coverage share with its threshold by bare arithmetic. Both are
  ratios of small counts and a programme that is exactly at the threshold can
  evaluate a few units in the last place under it; the comparison absorbs that
  while the threshold stays as written.

## Behavior contract (gate 3)

The integer sampling floor, the per-errand sample policy, specimen
eligibility, the destructive-on-deliverable refusal, per-activity grading,
per-errand coverage, the qualification share and the programme rollup are
exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_testing_overview.py against
scripts/e2008_bare_cell_testing_overview_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2008_bare_cell_testing_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

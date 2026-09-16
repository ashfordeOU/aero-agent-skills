---
name: e2008-bare-cell-acceptance-general
description: "Use when a bare cell acceptance matrix, lot traveller set or sampling plan has to be reviewed. Assess whether the bare solar cell acceptance activity set of clause 7.3.1 of ECSS-E-ST-20-08C reaches both populations it owes: the cells being delivered and the cells the qualification campaign consumes. Separate the activities every cell carries from the ones drawn on a sample, grade each sampled activity on the fraction of its population actually reached, keep absence, non-execution and failure apart, catch a population left wholly untested, and return one lot verdict with ranked findings. Trigger: ecss, e-st-20-08c, bare-cell-acceptance-testing-general, bare-cell-delivery-population-acceptance, bare-cell-qualification-population-acceptance, bare-cell-sampled-activity-fraction, bare-cell-lot-acceptance-verdict, bare-cell-acceptance-record-state."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-bare-cell-acceptance-general, bare-cell-acceptance-testing-general, bare-cell-delivery-population-acceptance, bare-cell-qualification-population-acceptance, bare-cell-sampled-activity-fraction, bare-cell-lot-acceptance-verdict, bare-cell-acceptance-record-state]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells — Acceptance Testing, General (space-systems/ecss/e2008-bare-cell-acceptance-general)

Use when the task is clause 7.3.1 of ECSS-E-ST-20-08C: acceptance tests are
applied to the bare cells being delivered and to the bare cells used for
qualification. This leaf grades a lot record on whether both populations
carry the acceptance activity set, at the basis each activity is applied on.

## Domain quick reference

- The second population is the whole point of the clause. A qualification
  cell is easy to read as exempt -- it is not being shipped, so acceptance
  looks like somebody else's obligation. It is the reverse: a qualification
  result only means something if the cell it was produced on was itself a
  sound cell.
- An unaccepted cell that fails a thermal cycle has told nobody anything. The
  result cannot separate a process that does not hold from a cell that was
  defective before the campaign touched it, and the campaign is repeated.
- Bare cells differ from assemblies in how the work is applied. Visual
  inspection and illuminated electrical performance are carried by every cell;
  the dimensional check, the mass measurement and the contact adherence test
  are drawn on a sample. The basis decides what a missing record even means.
- A sampled activity is graded on the fraction of its population reached, not
  on any single cell. Grading it cell by cell reports nearly every cell as
  missing a record it never owed; grading an every-cell activity as a sample
  accepts thousands of cells on a handful.
- A failure found in a sample speaks for the lot rather than for the cell it
  was found on, which is why it is carried as a population finding and not
  folded into one cell's verdict.
- Absence, non-execution and failure are three different states. No record at
  all is the worst, because it cannot be dispositioned: nobody knows whether
  the work was skipped, lost or never scheduled. An activity recorded as not
  yet run is a schedule item. A recorded failure is known and can be
  dispositioned.
- Exemption is a population-level defect, not a cell-level one. One cell with
  a thin traveller is a paperwork problem; every cell in a population with an
  empty record is a decision somebody made, and it is reported as its own
  finding rather than as a run of individually incomplete cells.
- A dispositioned failure is a project position, not a default. Whether a
  failed cell leaves the lot open is read from policy, because both answers
  are legitimate and the wrong one silently accepts hardware.

## Workflow

1. Validate each cell: a unique identifier, one of the two populations, and
   acceptance records naming only activities this clause owes. Refuse an
   activity outside the acceptance set rather than counting it as coverage.
2. Grade each cell against the every-cell activities only: what has no record,
   what is recorded as not run, what failed and what passed. A cell never
   drawn into a sample is not missing anything.
3. Rank the cell verdict -- absent record first, then unrun, then failed -- so
   the lot report names the root cause before the consequence.
4. Grade each sampled activity over its population: how many cells were drawn,
   what fraction of the population that is against the declared minimum, and
   how many of the drawn cells failed.
5. Summarise each population: how many cells it holds, how many are clear,
   the cleared share against the policy minimum, and the sampled results.
6. Detect a population present in the lot whose cells carry no acceptance work
   at all, and a population absent from the lot altogether; report each as its
   own finding.
7. Report the lot: cells grouped by verdict, both population summaries, the
   weakest cell and every finding in rank order.

## Pitfalls

- Running the acceptance matrix over the delivery lot only. The qualification
  cells are inside the clause, and leaving them out is the single defect this
  leaf exists to catch.
- Grading a sampled activity cell by cell. Nearly every cell will look as
  though it is missing a record, and the genuinely undocumented cells are lost
  in the noise.
- Grading an every-cell activity as a sample. A lot of thousands then closes
  on a handful of visual inspections nobody agreed to substitute.
- Reading an empty acceptance record as a pass. A cell with no record has not
  been shown sound; it has been shown undocumented.
- Collapsing absence into failure. They are dispositioned by different people
  through different paperwork, so the verdict keeps them apart.
- Folding a sampled failure into one cell's verdict. The sample was drawn to
  speak for the population, so the finding belongs to the population.
- Assuming a failed cell closes the lot. Whether a dispositioned failure is
  carried is a project position read from policy, and assuming either answer
  produces a verdict the project did not agree to.
- Judging a sampled fraction or a cleared share that lands exactly on its
  declared minimum by bare arithmetic. Both are ratios of two cell counts, so
  a lot drawn to exactly the declared fraction can land a few units in the
  last place below it; the comparison absorbs that while the minimum stays as
  declared.

## Behavior contract (gate 3)

The cell record validation, the every-cell and sampled activity split, the
sampled fraction against the declared minimum, the four record states, the
ranked cell verdict, the per-population summaries, the wholly untested and
absent population detectors, the failure policy and the rolled-up lot verdict
are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_acceptance_general.py against
scripts/e2008_bare_cell_acceptance_general_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_bare_cell_acceptance_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

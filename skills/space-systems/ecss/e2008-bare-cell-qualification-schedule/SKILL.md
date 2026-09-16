---
name: e2008-bare-cell-qualification-schedule
description: "Use when a bare cell qualification flow, cell lot sizing or test sequence has to be assessed. Validate the production and test schedule of clause 7.4.2 of ECSS-E-ST-20-08C followed while qualifying a bare solar cell: confirm every required production, measurement, environmental and documentation step is declared, hold each step behind the steps it depends on rather than merely present in the list, walk the cell lot through the declared order so each step is checked against the cells still in the pool after the destructive steps ahead of it retired theirs, size the lot against a retest reserve, and rank the findings into one schedule verdict. Trigger: ecss, e-st-20-08c, bare-cell-qualification-schedule, bare-solar-cell-qualification-sequence, bare-cell-schedule-step-precedence, bare-cell-lot-sizing, bare-cell-destructive-test-placement."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-bare-cell-qualification-schedule, e-st-20-08c, bare-cell-qualification-schedule, bare-solar-cell-qualification-sequence, bare-cell-schedule-step-precedence, bare-cell-lot-sizing, bare-cell-destructive-test-placement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Bare Cell Qualification Schedule (space-systems/ecss/e2008-bare-cell-qualification-schedule)

Use when the task is clause 7.4.2 of ECSS-E-ST-20-08C: the production and
test schedule followed while a bare solar cell is qualified. This leaf
reads a declared sequence of steps and one identified cell lot, and
returns the steps that cannot run where they are placed, the steps nobody
declared, and the step at which the lot can no longer field a sample.

## Domain quick reference

- The schedule is about a bare cell, before any coverglass, interconnect
  or adhesive exists. Everything the sequence measures is a property of
  the cell itself, so a step that belongs to an assembly flow does not
  belong here and a step that establishes the cell baseline cannot be
  skipped.
- Order is the content of the schedule, not its presentation. An
  environmental exposure placed before the illuminated baseline leaves
  no before-and-after to read the degradation against, and a final
  inspection placed before the exposure it is meant to reveal is a
  signature on a blank page.
- Presence and position are separate questions. A step that appears in
  the list but sits ahead of what it depends on is not a covered step,
  and a plan reviewed by ticking names off a list passes that schedule
  every time.
- Marking comes before measurement. A number taken off an unmarked cell
  cannot be traced back to the cell it describes, so the whole lot
  becomes one anonymous population rather than a set of identified
  articles.
- The lot is a live pool, not a budget. Every step draws a sample; only
  the destructive steps and the irradiation retire what they drew. Two
  sequences that retire the same number of cells in total therefore run
  out at different steps.
- Sample size and consumption are different quantities. A step needs its
  whole sample available at once where it is placed, which a running
  total of consumption never shows.
- A reserve is held above the campaign. A lot sized exactly to
  consumption leaves nothing for the repeat that one anomalous cell
  forces, so the closing balance is compared against a declared retest
  reserve.
- The arms are ranked, not merged. An absent prerequisite is reported
  ahead of a misplaced step, and a misplaced step ahead of a sample
  shortfall, because enlarging a lot for a sequence still in the wrong
  order buys cells for a campaign nobody can run.

## Workflow

1. Read the declared sequence and the lot it starts with. Reject an
   unknown step, a repeated step or an empty sequence rather than
   grading a list nobody can run.
2. Index the declared positions and resolve each step's prerequisites
   into two separate lists: the ones absent from the sequence entirely
   and the ones placed after the step that needs them.
3. Walk the lot through the declared order, recording the opening
   balance, the sample drawn, the cells retired and the closing balance
   at every step, and the first step the lot cannot supply.
4. Compare the closing balance against the declared retest reserve.
5. Rank the arms into one step verdict: absent prerequisite first, then
   misplacement, then sample shortfall.
6. Roll the schedule up: name the steps nobody declared, group the rest
   by verdict, test that marking precedes the first measurement and that
   the report closes the sequence, report the declared share of the
   required step set, and return a verdict that is clean only when
   nothing is open.

## Pitfalls

- Grading a bare cell schedule with an assembly checklist. The coupon
  steps of an assembly qualification have no article to run on yet, and
  the cell baseline steps they omit are the ones this clause turns on.
- Sizing the lot against the largest single sample. Retirement
  accumulates along the sequence, so a lot that covers the widest step
  can still be short two cells by the time the last destructive test is
  reached.
- Summing the consumption instead of walking it. The total says whether
  the lot is big enough; only the walk says which step stops, and that
  is the step the procurement has to be timed against.
- Treating every step as consuming its sample. A visual inspection
  returns its cells to the pool and a pull test does not, and a schedule
  graded as though both consume is rejected for a shortage it does not
  have.
- Placing a destructive test ahead of the baseline measurements. The
  test still runs and the cells are still gone, but nothing was recorded
  about them first.
- Measuring before the lot is marked. The readings are real and belong
  to no identified cell, which no later step can repair.
- Merging the arms into one pass or fail. A schedule missing a step and
  a schedule holding all of them in the wrong order need different
  corrections, and one verdict asks for the same one twice.

## Behavior contract (gate 3)

The required step set, the prerequisite resolution into absent and late
lists, the cell walk with its per-step opening balance, sample draw and
retirement, the retest reserve, the ranked step verdict and the rolled-up
completeness, marking-before-measurement and report placement checks are
exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_qualification_schedule.py against
scripts/e2008_bare_cell_qualification_schedule_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_qualification_schedule.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

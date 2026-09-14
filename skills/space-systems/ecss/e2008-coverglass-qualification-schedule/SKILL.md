---
name: e2008-coverglass-qualification-schedule
description: "Use when a coverglass qualification plan, campaign window or dated test sequence has to be assessed. Validate the dated production and test schedule a coverglass qualification campaign runs on under ECSS-E-ST-20-08C clause 8.6.2: refuse an undated, repeated or unknown step, name the required step nobody declared, hold a step whose planned start falls before the end of the step it depends on rather than merely later in the list, catch an exposure compressed below its minimum dwell, walk the campaign window out to its finish date, and report the float left against the day the qualified coverglass is owed. Trigger: ecss, e-st-20-08c-clause-8-6-2, coverglass-qualification-schedule, coverglass-dated-step-precedence, coverglass-campaign-window, coverglass-environmental-dwell-duration, coverglass-qualification-milestone-float."
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
  tags: [ecss, e-st-20-08-coverglass-scope, e2008-coverglass-qualification-schedule, e-st-20-08c-clause-8-6-2, coverglass-qualification-schedule, coverglass-dated-step-precedence, coverglass-campaign-window, coverglass-environmental-dwell-duration, coverglass-qualification-milestone-float]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coverglasses -- Qualification Schedule (space-systems/ecss/e2008-coverglass-qualification-schedule)

Use when the task is clause 8.6.2 of ECSS-E-ST-20-08C: the dated
production and test schedule a coverglass qualification campaign is run
against. A list of steps in the right order is a sequence; a list of
steps carrying planned start and end dates is a schedule, and only the
second can be held against the day the qualified coverglass is owed.
This leaf reads the dated steps and one need date, and returns the steps
that cannot run where they are dated, the steps nobody declared, and how
much float is left at the end.

## Domain quick reference

- Dates are the content of this document, not its presentation. A step
  can sit fifth in the list and still be planned to start in week one,
  which a position-based order check passes every time.
- Precedence is a date question here. The step's planned start has to
  fall on or after the day its prerequisite finishes; two steps that
  overlap by a week are not sequenced, whatever the list implies.
- Presence and placement are separate arms. An undeclared prerequisite
  cannot be fixed by moving the step that needs it, so it is reported
  first and reported differently.
- An environmental exposure has a minimum dwell because the degradation
  it is meant to produce takes that long. An ultraviolet exposure
  compressed into a fortnight produces a coverglass that was in the
  chamber, not a coverglass that was exposed.
- The baseline has to close before the exposures open. A transmittance
  figure taken while the article is already in the chamber is not a
  before, and nothing measured afterwards can be read as a change.
- Every exposure has to close before the post-exposure measurements. The
  four exposures run in parallel, so the measurement waits on the latest
  of them, not on the one that happens to be listed last.
- The campaign end date is the maximum of the step end dates, not the
  end of the last step in the list. A long exposure started early can
  still be the step the campaign finishes on.
- Float is held above the need date, not consumed up to it. A campaign
  planned to finish on the day the coverglass is owed has no room for
  the repeat one anomalous article forces, so the closing date is
  compared against a declared reserve rather than against the milestone
  itself.
- Duration counts both end days. A step dated to a single day lasts one
  day, and an off-by-one here turns every dwell check into a near miss.

## Workflow

1. Read the campaign identifier and the date the qualified coverglass is
   owed, and refuse a plan that declares neither.
2. Read the declared steps: refuse an unknown step, a repeated step, an
   undated step, a date that is not a calendar date, and a step dated to
   end before it starts, rather than grading a schedule nobody can run.
3. Resolve each step's prerequisites into two separate lists: the ones
   absent from the schedule entirely, and the ones whose end date falls
   after the dependent step's start date.
4. Compare each step's planned duration against the minimum dwell its
   kind carries, counting both end days.
5. Compare each step's end date against the need date.
6. Rank the arms into one step verdict: absent prerequisite first, then
   a dated precedence break, then a short dwell, then a milestone
   overrun.
7. Build the campaign window from the earliest start and the latest end,
   and take the float from the campaign end to the need date.
8. Roll the campaign up: name the steps nobody declared, group the rest
   by verdict, report the declared share of the required step set and
   the arm to close first, and return a verdict that is runnable only
   when every step is declared, every step is clean and the float clears
   the declared reserve.

## Pitfalls

- Checking the order and not the dates. The sequence can be perfect on
  paper while three steps are planned to run the same week, and the
  clause is about the schedule, not the running order.
- Reading the campaign end off the last row. The last row is the last
  step listed, and a sixty-day exposure started in February can finish
  after a report scheduled for April.
- Compressing an exposure to recover schedule. The dwell is the test; a
  shortened one returns a result about a shorter exposure, and the
  campaign has spent the articles to learn nothing about the real one.
- Planning the baseline to overlap the exposure it baselines. There is
  then no before-and-after pair, and the degradation figure everything
  else rests on cannot be formed at all.
- Waiting on the wrong exposure. The post-exposure measurement depends
  on all four, and sequencing it behind the shortest one leaves articles
  still in a chamber when they are due on a bench.
- Planning to the need date exactly. Zero float is not a schedule risk
  to be managed later, it is a schedule that fails on the first repeat,
  and repeats are normal.
- Treating an absent step as a late step. Moving a step that was never
  declared is not a correction anybody can make, and the two findings go
  to different people.
- Merging the arms into one pass or fail. A missing step, an overlap and
  a short dwell need three different corrections, and one verdict asks
  for the same one three times.

## Behavior contract (gate 3)

The schedule policy validation, the required step map with its
prerequisites and minimum dwells, the dated step read with its
duplicate, unknown, undated and reversed-date refusals, the inclusive
duration, the prerequisite resolution into absent and late lists, the
campaign window, the milestone float, the ranked step verdict, the
worst-arm selection and the rolled-up campaign verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_coverglass_qualification_schedule.py against
scripts/e2008_coverglass_qualification_schedule_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_qualification_schedule.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

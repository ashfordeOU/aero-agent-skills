---
name: e2008-blocking-diode-production-schedule
description: "Use when a blocking diode qualification lot schedule, campaign window or late schedule revision is reviewed. Validate the dated production and test schedule ECSS-E-ST-20-08C clause 12.5.3 asks to be compiled before a blocking diode qualification lot starts: establish the schedule was issued ahead of the lot rather than written up afterwards, refuse an activity added once the lot was already running, date every production and test activity and refuse one that ends before it begins, hold a test activity booked ahead of the production it reports on, walk the campaign out to its finish date, and report the float left against the day the qualified diodes are owed. Trigger: ecss, e-st-20-08c, blocking-diode-production-schedule, blocking-diode-schedule-issue-chronology, blocking-diode-lot-start-date, blocking-diode-activity-phase-order, blocking-diode-campaign-window-float."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-production-schedule, blocking-diode-production-schedule, blocking-diode-schedule-issue-chronology, blocking-diode-lot-start-date, blocking-diode-activity-phase-order, blocking-diode-campaign-window-float]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Production Schedule (space-systems/ecss/e2008-blocking-diode-production-schedule)

Use when the task is clause 12.5.3 of ECSS-E-ST-20-08C: a dated schedule of
the production and testing a blocking diode qualification lot will go
through exists before that lot is started. A schedule written afterwards is
a record, and a record cannot be reviewed in advance of the work. This leaf
reads the schedule's own dates and its activity dates as two separate
things and returns whether the lot may be started against it.

## Domain quick reference

- The clause carries a chronology, not just a content list. The question
  is not only what the schedule says but when it came to say it.
- A schedule issued in good time can still grow. An activity recorded
  three weeks into the lot sits inside a document whose issue date is
  clean, so the activity record dates have to be read on their own.
- An activity that starts before the lot does is a dating error or a step
  taken outside the qualification lot. Either way the schedule does not
  describe the lot it claims to.
- Production and testing are two phases with one direction. A test
  activity starting before the last production activity ends is a test of
  an article that does not exist yet.
- Every activity needs both ends dated. An end date before a start date
  is not a tight plan, it is a typing error that will otherwise be
  arithmetically averaged into a campaign span.
- A campaign span and a milestone float are two different numbers. The
  span says how long the work takes; the float says whether it fits, and
  only the second involves the day the diodes are owed.
- Negative float is a finding, not a formatting problem. It is the number
  the schedule was compiled to produce.
- A phase booked nowhere is a silent hole. A schedule of four production
  activities and no testing reads as fully placed on every per-activity
  check.

## Workflow

1. Read the schedule header: its identifier, the diode type, the issue
   date, the lot start date and the day the qualified diodes are owed.
2. Settle the compilation question first: issue date against lot start
   date, and report how many days separate them in either direction.
3. Read the activities into start order, refusing a repeated identifier,
   an undated entry, an unrecognised phase and an end before a start.
4. Build the production window and the test window from the activities
   that declare each phase.
5. Grade each activity: was it recorded before the lot started, does it
   start after the lot starts, does a test activity sit clear of the
   production window, and does it finish by the milestone.
6. Rank the arms into one activity verdict: a late record first, then a
   start before the lot, then a phase inversion, then a milestone
   overrun.
7. Total the campaign window end to end and take the float to the day the
   diodes are owed, leaving it unset when no milestone was given.
8. Return the roll-up: activities grouped by verdict, the open ones, any
   phase booked nowhere, the two phase windows, the campaign span, the
   float, the placed share and the arm to close first.

## Pitfalls

- Checking only the schedule issue date. It is the first question and not
  the whole one, and a clean issue date hides every activity added later.
- Reading the activity list in the order it is written. Start order is
  what says which work comes first, and a list keyed on activity name
  hides a phase inversion completely.
- Treating a missing phase as nothing to grade. It is the loudest finding
  in the set and the one no per-activity loop will produce.
- Averaging a backwards activity into the campaign span. Refuse it at the
  read instead, so the span stays a number somebody can act on.
- Reporting the campaign span as if it answered the milestone question.
  It does not; only the float does.
- Merging an activity that starts early with one that was recorded late.
  The first is a dating problem inside the plan, the second is a plan
  that grew after the lot was running.
- Dropping the float when no milestone date was supplied. Unset and zero
  are different, and a zero reads as a schedule finishing exactly on time.

## Behavior contract (gate 3)

The schedule policy validation, the activity normalisation with its date
and phase refusals, the activity duration, the issue chronology against
the lot start date, the per-phase and campaign windows, the milestone
float, the ranked activity verdict, the worst-arm selection and the
schedule roll-up are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_production_schedule.py against
scripts/e2008_blocking_diode_production_schedule_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_production_schedule.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

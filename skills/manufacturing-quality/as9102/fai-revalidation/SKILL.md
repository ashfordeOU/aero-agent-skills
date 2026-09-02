---
name: fai-revalidation
description: "Use when you must schedule a first article inspection (FAI) revalidation per AS9102 practice: compute the revalidation due date from the last FAI date and the revalidation interval, check whether a process, tooling, drawing revision, location, or supplier change triggers a revalidation, and scope the characteristics to re-verify. Produces the revalidation status, the next revalidation date, and the re-verification scope that gate FAI currency. Trigger: fai revalidation, revalidation due date, last fai date, annual interval, revalidation frequency, change driven revalidation, revalidation scope."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9102
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9102
  tags: [fai-revalidation, revalidation-due-date, revalidation-interval, revalidation-frequency, revalidation-scope, last-fai-date, annual-revalidation, change-driven-revalidation, next-revalidation-date, as9102]
  version: 0.1.0
  author: Aero Agent Skills
---

# FAI Revalidation (manufacturing-quality/as9102/fai-revalidation)

Use when the task is scheduling a first article inspection (FAI)
revalidation per AS9102 practice: the revalidation due date comes
from the last FAI date plus the revalidation interval, a change can
pull the schedule earlier, and the re-validation re-verifies the
affected characteristics plus every key characteristic.

## Domain quick reference

- Time-driven revalidation: the due date is the last FAI date plus
  the revalidation interval; the default policy is annual (365
  days).
- revalidation_status returns due_date, days_remaining, and status:
  due on or past the due date, upcoming within the 60-day window
  before it, current otherwise.
- Change-driven revalidation: a process, tooling, drawing-revision,
  location, or supplier change triggers a revalidation; a
  part-number or material change calls for a new FAI instead; no
  change means time-driven only.
- next_revalidation_date takes the later of the time-driven due date
  and the change-driven date (change date plus the interval); an
  early change cannot pull the schedule earlier.
- revalidation_scope returns the characteristics to re-verify: the
  affected characteristics plus every key characteristic,
  deduplicated in order; key characteristics always stay in scope.
- AS9102 frames revalidation around the first article inspection
  practice; the schedule model here is a practical summary, not
  clause text.

## Workflow

1. Confirm the last FAI date and the revalidation interval; use
   revalidation_due_date for the time-driven due date.
2. Check the schedule with revalidation_status(last_fai_date, today);
   act on status due or upcoming.
3. When a change occurred, classify it with change_trigger_verdict:
   revalidation-required, new-fai-required, or not-triggered.
4. Combine the schedule with the change date using
   next_revalidation_date for the single next due date.
5. Scope the re-verification with revalidation_scope(affected,
   key_characteristics); key characteristics always stay in scope.
6. Record the due date and the scope in the revalidation plan.

## Pitfalls

- Zero or negative intervals: interval_days must be positive;
  revalidation_due_date raises ValueError otherwise.
- Treating a part number or material change as revalidation: those
  call for a new FAI, not a revalidation (change_trigger_verdict
  returns new-fai-required).
- Pulling the schedule earlier with an old change: a change date
  before the last FAI date cannot move the due date; the later date
  wins.
- Forgetting key characteristics: revalidation re-verifies the
  affected characteristics plus every key characteristic, even when
  the change list is empty.
- Non-date inputs: last_fai_date, today, and change_date must be
  datetime.date instances; strings raise ValueError.
- Reporting days remaining from a string date: compute the status
  with real date objects so the day arithmetic is exact.

## Behavior contract (gate 3)

The revalidation logic is exercised by the gate 3 contract test:
scripts/test_fai_revalidation.py against
scripts/fai_revalidation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fai_revalidation.py

## Compliance

- Standards referenced, not reproduced: AS9102 revalidation practice
  is summarized as a schedule and scope model, common aerospace
  first article practice per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

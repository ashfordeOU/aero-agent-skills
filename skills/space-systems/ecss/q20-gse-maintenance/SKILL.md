---
name: q20-gse-maintenance
description: "Maintain ground support equipment under ECSS-Q-ST-20C clause 5.8.9: measure each planned task against its own clock, calendar days or operating hours, report how much of every interval has been consumed and by how much a task has run past it, treat a task landing exactly on its interval as due rather than late, derive the reverification an intervention owes from the part it touched, name every recalibration or inspection still outstanding before the equipment goes back to work, and return the continued-readiness verdict. Use when GSE is due for maintenance or is coming out of it. Trigger: ecss, q-st-20c-clause-5-8-9, gse-maintenance-interval, gse-overdue-maintenance-task, gse-post-maintenance-recalibration, gse-continued-readiness-record, gse-return-to-service."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-gse-maintenance, gse-maintenance-interval, gse-overdue-maintenance-task, gse-post-maintenance-recalibration, gse-continued-readiness-record, gse-return-to-service]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS GSE Maintenance and Readiness (space-systems/ecss/q20-gse-maintenance)

Use when the task is the clause 5.8.9 maintenance of ground support equipment
in ECSS-Q-ST-20C: the equipment is on a planned maintenance schedule, somebody
has just been inside it, and the question is whether it may go back to holding
flight hardware.

## Domain quick reference

- A maintenance interval is measured on the clock the task was written
  against. A stand on a calendar interval and a pump on an operating-hours
  interval are both a year old and only one of them is due.
- The consumed fraction is worth more than a due flag. A task at 0.95 of its
  interval is the one to fold into next week's shutdown, and a boolean hides it.
- A task that lands exactly on its interval is due, not late. The distinction
  matters because an overdue safety-critical task is an event and a due one is
  a plan.
- What an intervention owes is decided by what it touched, not by how long it
  took. Open a measuring chain and it needs recalibrating; disturb a load path
  and it needs proving again; break a pressure boundary and it is re-tested.
- The moment of risk is the return to service. Equipment goes back to work when
  someone signs it off, and an outstanding recalibration is easiest to miss
  exactly then.
- Readiness has three inputs and one answer: nothing overdue, nothing owed from
  the last intervention, and a readiness record that is actually current.

## Workflow

1. Validate each planned task: a unique identifier, a basis from the closed
   vocabulary, a positive interval and a non-negative elapsed figure on the
   same clock.
2. Compute the consumed fraction and the overdue amount per task, resolving the
   exactly-on-interval case as due through a named tolerance.
3. Raise an overdue task with the amount and the basis, so the reader knows
   whether it is days or hours.
4. Raise a safety-critical task that has merely reached its interval, since
   that equipment is not run into its overdue period.
5. Derive the reverification set from the parts the interventions touched,
   collapsing two visits to one part into one reverification.
6. Name every derived reverification not yet completed.
7. Combine the findings with the state of the readiness record and return
   ready, ready-pending-record or not-ready.

## Pitfalls

- Running one clock across a mixed schedule. Calendar and operating-hour tasks
  drift apart the moment the equipment sits idle for a season.
- Reporting maintenance as due or not due. The fraction consumed is what lets
  a shutdown be planned instead of endured.
- Treating exactly-on-interval as overdue. It raises an event where a plan was
  wanted, and repeated often enough it teaches people to ignore the report.
- Deriving the post-maintenance work from the paperwork rather than the
  hardware. What was touched decides what is owed; the work order description
  frequently does not say.
- Returning equipment to service on a signature. The signature is the last
  chance to notice that the calibration owed since Tuesday never happened.
- Calling equipment ready with a stale readiness record. Nothing may be wrong
  with it, but nothing shows that either, and that is a different state.

## Behavior contract (gate 3)

The task validation, per-basis interval arithmetic, consumed fraction, the
exactly-on-interval due resolution, overdue and safety-critical findings, the
intervention-derived reverification set, outstanding reverification detection
and the three-way readiness verdict are exercised by the gate 3 contract test:
scripts/test_q20_gse_maintenance.py against
scripts/q20_gse_maintenance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_gse_maintenance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

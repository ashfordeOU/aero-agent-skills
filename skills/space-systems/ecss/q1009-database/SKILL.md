---
name: q1009-database
description: "Maintain the nonconformance database ECSS-Q-ST-10-09 clause 5.5.2 makes a project keep, and decide whether it is doing its job. Use when nonconformances are being raised on a programme and the register behind them has to be graded before a progress review or an audit: refuse a database never opened, check each row carries its identifier, raising day, affected item, category and status, take registration coverage against the count raised rather than the rows held, catch a status that moved backwards or a closure with no disposition or evidence behind it, name the open rows past their review age, test the retrieval keys a report is built on, and say whether periodic reporting is current. Trigger: ecss, q-st-10-09-clause-5-5-2, nonconformance-database-registration-coverage, nonconformance-status-tracking-regression, nonconformance-record-retrieval-keys, nonconformance-periodic-reporting-currency."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-database, q-st-10-09-clause-5-5-2, nonconformance-database-registration-coverage, nonconformance-status-tracking-regression, nonconformance-record-retrieval-keys, nonconformance-periodic-reporting-currency, nonconformance-open-record-review-age]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Nonconformance Database (space-systems/ecss/q1009-database)

Use when the task is clause 5.5.2 of ECSS-Q-ST-10-09: the project keeps
one database of the nonconformances raised against it, and the question
is whether that database registers everything, tracks status honestly,
and can still be retrieved from and reported out of.

## Domain quick reference

- A nonconformance the database does not hold did not happen as far as
  the programme can show. Coverage is therefore taken against the count
  of nonconformances raised, not against the count of rows present: a
  register can only be complete relative to something outside itself,
  and a register graded against its own contents is always complete.
- A row is registered when it is actionable. An identifier, a raising
  day, the affected item, the category and the current status are what a
  later reader needs, and a row missing any of them is carried as a gap
  rather than counted as a registration.
- Status is tracked, not stamped. A status behind the one the row
  already reached means two readers disagree about the same
  nonconformance, which is a tracking defect and not a content gap.
- A closure has to be auditable. A row marked closed with no
  disposition, no closure evidence, no closure day, or a closure day
  before the raising day, is a row nobody can check after the fact.
- Ageing is advisory, not disqualifying. An open row past the review age
  its category carries is a management flag on a database that is
  otherwise being maintained; a major nonconformance owes that review
  sooner than a minor one.
- Retrieval and reporting are functions of the database. The keys a
  report is built on — identifier, affected item, category, status,
  raising day, disposition — have to be retrievable, and a periodic
  report older than the reporting interval means the database stopped
  feeding the product assurance reporting it exists to feed.

## Workflow

1. Validate the maintenance policy first: the coverage the database
   owes, the reporting interval, the review ages for major and minor
   rows, and whether closure evidence is demanded. A policy that would
   review a major row later than a minor one is refused rather than
   used.
2. Validate the register: every row a mapping, recognised category and
   status values, whole non-negative day numbers, and no identifier
   registered twice. A blank field is a gap to be counted, not an error.
3. Take registration coverage as the complete rows over the count of
   nonconformances raised, and name the rows that are not complete. A
   raised count below the rows held is refused as a wrong count.
4. Take the status regressions and the closure defects across the
   register.
5. Take the retrieval gaps against the report keys, and test whether a
   periodic report was issued inside the interval.
6. Take the ages of the open rows and name the ones past the review age
   their category carries; carry them as advisories.
7. Close on one verdict in order: database absent, registration
   incomplete, status tracking broken, retrieval not supported,
   periodic reporting stale, or database maintained. Report the
   coverage, the incomplete rows, the regressions, the closure defects
   and the retrieval gaps alongside it.

## Pitfalls

- Grading coverage against the rows the database already holds. That
  number is one by construction and says nothing about the
  nonconformances raised and never entered.
- Counting a row with a blank affected item as registered. It is in the
  database and still cannot be acted on, which is the case the required
  fields exist to catch.
- Reading a closed status as a closed nonconformance. Closure without a
  disposition or evidence behind it is a status word, not a closure.
- Treating an overdue open row as a database defect. The database is
  recording the row correctly; the ageing is a finding against the
  project, and mixing the two hides a real registration gap.
- Reporting a bare verdict. The coverage, the named rows and the missing
  retrieval keys are what the corrective action turns on.

## Behavior contract (gate 3)

The policy validation, record and register validation, the required
field gaps, registration coverage against the count raised, the status
regressions, the closure defects, the open-row ageing, the retrieval
gaps, the reporting currency and the maintenance verdict are exercised
by the gate 3 contract test: scripts/test_q1009_database.py against
scripts/q1009_database_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q1009_database.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

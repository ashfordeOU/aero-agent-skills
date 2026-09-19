---
name: q7026-crimp-records
description: "Audit a set of crimping records for the completeness and traceability the records clause of ECSS-Q-ST-70-26C asks of them. Use when a harness dossier is assembled and every termination has to be answerable: check the mandatory fields are carried, resolve the tool identifier into the calibration register, resolve the operator against the certification window covering the date of the crimp rather than today, resolve both wire and contact lots into accepted receiving records, grade the periodic pull-test cadence across the set in date order, and grade the retention period. Trigger: ecss, q-st-70-26, crimp-record-completeness, crimp-lot-traceability-chain, crimp-tool-identifier-resolution, crimp-operator-date-validity, crimp-record-retention-period."
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
  tags: [ecss, q-st-70-26-crimping-scope, q7026-crimp-records, crimp-record-completeness, crimp-lot-traceability-chain, crimp-operator-date-validity, crimp-record-retention-period]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crimping — Records and Traceability (space-systems/ecss/q7026-crimp-records)

Use when the task is the records step of ECSS-Q-ST-70-26C — deciding
whether a crimping dossier actually answers for the terminations it
covers: what each entry carries, what each entry resolves into, and
how long it has to be kept.

## Domain quick reference

- A record is worth what it resolves into. A tool identifier that is
  not in the calibration register, an operator identifier that is not
  in the personnel register, and a lot number with no receiving
  record are text on a page rather than traceability.
- Certification is checked on the date of the crimp, not the date of
  the audit. An operator certified today may not have been certified
  the morning that harness was built, and that is the only question
  the dossier is being asked.
- A lot received but never accepted does not close the chain. The
  chain has to end in an accepted receiving record; ending it at an
  open receiving inspection just moves the question somewhere else.
- A missing field and an unresolved reference are different failures
  and go to different people. One is completed at the bench in an
  afternoon; the other is an investigation into what was actually
  used, so they are counted and reported apart.
- Periodic pull-test samples police a run, not an entry. The cadence
  is therefore graded across the record set in date order, and a
  sample arriving after more terminations than the interval allows
  leaves the ones in between unpoliced.
- The order the records were filed in is not the order they were
  made. Grading the cadence in list order can pass a dossier whose
  real chronology has a gap in it, so the set is sorted by crimp date
  first.
- Retention runs in calendar years from the crimp date and the last
  day of retention is still inside it. A record disposed of a day
  early is a finding whatever the arithmetic on a spreadsheet said.
- An unpoliced tail is a real gap. The last stretch of a run with no
  sample after it is exactly the population nobody checked.

## Workflow

1. Validate the policy — a positive pull-test interval and a positive
   retention period in years — and the registers the entries resolve
   into, rejecting an operator window that ends before it starts.
2. Validate each entry: identifier, ISO crimp date, tool, operator,
   contact lot, wire lot, a positive termination count, and a
   pull-test reference that may be genuinely absent.
3. List the missing mandatory fields first and stop there for that
   entry. An incomplete record cannot be resolved, and reporting
   unresolved references against it invents a second problem.
4. Resolve the tool identifier into the calibration register.
5. Resolve the operator and test the crimp date against the
   certification window, inclusive of both its ends.
6. Resolve both lot numbers, separating a lot with no receiving
   record from one received but not accepted.
7. Grade the pull-test cadence across the whole set in date order,
   naming the entry the gap closed at and reporting an unpoliced tail
   as an open run.
8. Grade retention per entry, then give the dossier verdict: rejected
   on any incomplete or unresolved entry, accepted with findings on a
   cadence gap or entries past retention, accepted otherwise.

## Pitfalls

- Checking the operator is certified now. The dossier is about work
  already done, so the window that matters is the one covering the
  crimp date.
- Accepting a lot number because it appears in the receiving log. It
  has to appear there with an accepted verdict.
- Grading the pull-test cadence entry by entry. The interval spans
  entries, so a per-entry check passes a dossier with a gap running
  straight through several of them.
- Grading the cadence in the order the pages were filed. Filing order
  is not chronology and it can hide the gap entirely.
- Merging missing fields with unresolved references into one count.
  They route to different people and the merged number tells neither
  of them what to do.
- Disposing of a record on the first day of its final year because a
  spreadsheet rounded the retention period down.

## Behavior contract (gate 3)

Policy and register validation, mandatory-field completeness with the
short-circuit on an incomplete entry, tool, operator-on-the-crimp-date
and lot resolution including the unaccepted-lot case, the calendar-year
retention boundary with its leap-day step, the date-ordered pull-test
cadence with its unpoliced tail and the dossier verdict are exercised
by the gate 3 contract test:
scripts/test_q7026_crimp_records.py against
scripts/q7026_crimp_records_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7026_crimp_records.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

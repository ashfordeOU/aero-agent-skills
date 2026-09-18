---
name: q1009-status-list-drd
description: "Validate or produce the NCR status list required by the normative data item of ECSS-Q-ST-10-09 Annex B. Use when a progress meeting or an audit needs the open and closed nonconformance reports as one register at a stated date: reconcile the list against the nonconformances the database holds rather than against itself, name the registered reports it omits and the rows the register cannot trace, catch a row closed with no disposition or closure day and an open row carrying one, group the counts by category, standing and disposition, and raise an open major report standing past its review age. Trigger: ecss, q-st-10-09-annex-b, ncr-status-list-register-reconciliation, ncr-status-list-entry-consistency, ncr-status-list-category-grouping, ncr-open-major-review-age."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-status-list-drd, q-st-10-09-annex-b, ncr-status-list-register-reconciliation, ncr-status-list-entry-consistency, ncr-status-list-category-grouping, ncr-open-major-review-age, ncr-status-list-disposition-standing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — NCR Status List DRD (space-systems/ecss/q1009-status-list-drd)

Use when the task is Annex B of ECSS-Q-ST-10-09: the open and closed
nonconformance reports have to be put out as one status list at a stated
date, and the question is whether that list reconciles to the register,
reads honestly row by row, and surfaces what a review meeting is for.

## Domain quick reference

- The list is reported against the database, not against itself.
  Coverage is taken over the nonconformances the register holds, so a
  list quietly omitting ten reports is short by ten however tidy its own
  rows look. A list graded on its own contents is always complete.
- A row the register cannot trace is the same defect from the other
  side. It is refused by default, and a project that keeps a deliberate
  local annex can allow it by policy rather than by silence.
- An entry has to be internally honest. Closed with no disposition, no
  closure day, or a closure day before the raising day is a row that
  cannot be read; open while carrying a closure day is the same defect
  inverted.
- The list is grouped, not just listed. The counts by category, by
  standing and by disposition are what a progress meeting reads, and
  they are derived from the rows rather than typed alongside them, so
  they cannot drift from the register they summarise.
- Ageing is what the list is read for. An open major report past its
  review age is the row the meeting exists to find, so it is a verdict
  of its own; an overdue minor is carried as an advisory, because
  treating both alike buries the one that matters.
- The as-of date is part of the data item. Every age on the list is
  taken from it, and a list with no reference or issue label cannot be
  cited by the minutes that read it.

## Workflow

1. Validate the data-item policy first: the entry coverage demanded,
   whether rows outside the register are tolerated, the review ages for
   major and minor reports, and how many overdue open majors may stand.
   A policy chasing a major later than a minor is refused rather than
   used.
2. Validate the list identity: a non-blank reference, a non-blank issue
   label and an as-of day. A list missing either label closes on not
   issued.
3. Validate every row: an identifier, a recognised category, standing,
   disposition and board, a raising day, and no report listed twice.
4. Reconcile against the register: take the entry coverage, name the
   registered reports the list omits, and name the rows the register
   does not hold.
5. Take the entry defects across the rows.
6. Group the counts by category, standing and disposition.
7. Take the ages of the open rows against the as-of day and separate the
   overdue majors from the overdue minors.
8. Close on one verdict in order: status list not issued, status list
   incomplete, entries inconsistent, open majors overdue, or status list
   accepted. Report the coverage, the omitted and untraceable rows, the
   defects and the grouped counts alongside it.

## Pitfalls

- Grading the list on the rows it already carries. That coverage is one
  by construction and says nothing about the reports left off it.
- Reading a closed standing as a closed report. Closed with no
  disposition recorded is a status word, and the list is where that
  shows up first.
- Reporting one ageing number for the whole list. A major standing open
  past its review age is a different finding from a minor doing the
  same, and one average hides both.
- Typing the summary counts alongside the table. Derived counts cannot
  disagree with the rows; typed ones always eventually do.
- Issuing the list with no as-of day. Every age on it is then unfounded,
  and two readers will compute different ones.

## Behavior contract (gate 3)

The policy validation, list identity validation, row validation, the
register reconciliation and entry coverage, the omitted and untraceable
rows, the entry defects, the grouped counts, the open-row ageing, the
overdue major separation and the status list verdict are exercised by
the gate 3 contract test: scripts/test_q1009_status_list_drd.py against
scripts/q1009_status_list_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q1009_status_list_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

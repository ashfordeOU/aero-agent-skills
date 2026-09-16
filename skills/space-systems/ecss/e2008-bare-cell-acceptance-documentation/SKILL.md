---
name: e2008-bare-cell-acceptance-documentation
description: "Use when an acceptance data package is about to be released with a cell lot. Audit the acceptance data package a bare solar cell lot is delivered against, the record set ECSS-E-ST-20-08C clause 7.3.3 sends acceptance results into: name the acceptance activity nobody wrote up, test each record for the fields that make it re-readable, refuse a record reporting on cells outside the delivered lot, find the delivered cell no activity reached, hold anything still sitting in draft at delivery, and rank the arms so a missing record outranks a thin one. Trigger: ecss, e-st-20-08c-clause-7-3-3, bare-cell-acceptance-record-completeness, bare-cell-acceptance-data-package-release, bare-cell-record-traceability-to-lot, bare-cell-acceptance-activity-coverage."
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
  tags: [ecss, e-st-20-08-bare-solar-cell-scope, e2008-bare-cell-acceptance-documentation, e-st-20-08c-clause-7-3-3, bare-cell-acceptance-record-completeness, bare-cell-acceptance-data-package-release, bare-cell-record-traceability-to-lot, bare-cell-acceptance-activity-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells -- Acceptance Documentation (space-systems/ecss/e2008-bare-cell-acceptance-documentation)

Use when the task is clause 7.3.3 of ECSS-E-ST-20-08C: the results of
bare-cell acceptance testing are carried into the documentation the lot
is delivered against. A test that was run and never written up is, to
everybody downstream, a test that was not run. This leaf reads the
acceptance data package, decides whether each record is a record, and
returns what stands between the lot and release.

## Domain quick reference

- Coverage and completeness are two different questions. An activity
  with no record at all is a hole in the package; a record missing its
  test conditions is a record nobody can re-read. They need different
  responses, so they are reported separately.
- A record has to say what it was taken under. Current and voltage
  without spectrum, temperature and incidence are numbers, not results,
  and nobody can compare them to the next lot or to the drawing.
- Calibration belongs in the record, not in a drawer. The equipment
  reference is what lets a result be re-derived years later, and it is
  the first field to go missing when a record is written from memory.
- A record naming cells outside the delivered lot is not weak evidence,
  it is evidence about something else. That outranks a thin record,
  because a thin record at least describes the right population.
- Coverage is per cell as well as per activity. Five activities can each
  have a record while one delivered cell appears in none of them, and
  the package still reads complete if only the activity list is checked.
- Draft is not delivered. A package released while its records sit
  unapproved has moved the approval step to after the point where
  somebody could still act on it.
- Two records can jointly cover one activity. Splitting a lot across
  test sessions is normal, so coverage is computed over the union of the
  records rather than demanding one record per activity.

## Workflow

1. Read the lot identifier and the delivered cell identifiers; the
   delivered list is the population every later question is asked about.
2. Read each record, refuse an activity the acceptance programme does
   not contain, and refuse a package that declares a record twice.
3. Audit each record against the required field set, treating an empty
   cell list, an empty conditions field and an empty calibration
   reference as missing rather than as present-but-blank.
4. Test each record's cell identifiers against the delivered lot and
   name anything foreign.
5. Rank each record: foreign cells first, then missing fields, then an
   approval still pending or withdrawn.
6. Build the per-activity cell coverage over the union of the records
   and name the delivered cells no record of that activity reached.
7. Return a package verdict that is releasable only when every activity
   is recorded, every record is complete and every delivered cell is
   reached, with all findings collected in one list.

## Pitfalls

- Counting records instead of activities. Five records can all describe
  the same activity, and the package then reports five results and four
  holes.
- Accepting a summary in place of the measured results. A statement
  that the lot passed is a conclusion; the clause sends the results
  themselves into the documentation, and the conclusion cannot be
  rebuilt from its own restatement.
- Checking activity coverage and stopping there. The delivered cell
  that appears in no record is invisible to an activity-level check and
  is exactly the cell that will be queried later.
- Treating an unapproved record as a paperwork detail. It is the one
  finding that can still be closed in minutes, and it is the one that
  stops the package the day it ships.
- Reading a foreign cell identifier as a typo and correcting it. The
  record may genuinely describe another lot, and silently rewriting the
  identifier destroys the only evidence that it did.
- Merging the arms into one pass or fail. A missing record and an
  unsigned record ask the supplier for very different work, and a merged
  verdict asks for the same one twice.

## Behavior contract (gate 3)

The required activity set, the required field set, the field audit, the
record traceability test, the approval state, the ranked record verdict,
the per-activity cell coverage and the package release verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_acceptance_documentation.py against
scripts/e2008_bare_cell_acceptance_documentation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_bare_cell_acceptance_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

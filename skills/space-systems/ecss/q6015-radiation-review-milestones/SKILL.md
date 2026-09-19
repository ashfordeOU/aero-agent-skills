---
name: q6015-radiation-review-milestones
description: "Assess whether the radiation analysis reporting reaches each project milestone review at the depth and on the date that review is owed. Use when the ECSS-Q-ST-60-15C clause 4.5 reporting obligation has to be planned or graded: read the depth an equipment category owes at a given review from the closed depth ladder, count working days back from the review date to turn that depth into a submission deadline, and grade every report separately on delivery, on depth against what was demanded, and on timeliness against its own deadline. Trigger: ecss, q-st-60-15c-clause-4-5, radiation-review-milestone-reporting, radiation-analysis-report-depth, equipment-radiation-category, review-submission-lead-time, milestone-reporting-completeness."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-radiation-review-milestones, q-st-60-15c-clause-4-5, radiation-review-milestone-reporting, radiation-analysis-report-depth, equipment-radiation-category, review-submission-lead-time, milestone-reporting-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Review Milestone Reporting (space-systems/ecss/q6015-radiation-review-milestones)

Use when the task is the reporting obligation of ECSS-Q-ST-60-15C clause 4.5
— deciding what radiation analysis each milestone review is owed for a given
equipment, when it has to be in the board's hands, and whether what was
actually delivered met both.

## Domain quick reference

- Reporting depth is a ladder, not a label. A summary, an assessment, a
  detailed analysis and a full verification dossier are ordered, so a deeper
  report always satisfies a shallower demand and a shallower one never
  satisfies a deeper demand. Grading depth is therefore a rank comparison, not
  a string match.
- The depth owed is a function of two things together: the equipment category
  and the review. A category carrying a radiation-critical function deepens
  earlier in the project; a tolerant one can still be at summary depth when a
  critical one is already at detailed analysis.
- Depth never decreases along the project for a given category. Once a review
  has been fed a detailed analysis, the next review is not satisfied by a
  summary of it.
- Timing is derived from depth, not set independently. A deeper report is
  longer and is owed more reading time, so the deadline is counted back from
  the review date in working days by depth — which is why a deep report for a
  critical equipment has an earlier deadline than a shallow one for the same
  review on the same date.
- Counting in working days matters. A twenty-working-day lead crosses four
  weekends, so a calendar-day count lands the deadline nearly a month wrong
  and always in the optimistic direction.
- Delivery, depth and timeliness are three separate answers. A report that
  arrived but was too shallow, and a report at the right depth that arrived
  after the deadline, are different failures needing different recovery, so
  the grading never collapses them into a single pass or fail.

## Workflow

1. Normalise the equipment category, the review and any declared depth
   against their closed sets; an unrecognised value is an input error rather
   than a default.
2. Read the depth owed from the category-by-review matrix.
3. Convert that depth into a lead time in working days and step back from the
   review date, skipping weekends, to obtain the submission deadline.
4. Grade delivery first: a review entry with neither a depth nor a date is a
   report that was never submitted, and a half-declared entry with one of the
   two is an input error, not an absent report.
5. Grade depth by rank, so an over-delivered report passes, and grade
   timeliness by date, treating a submission landing exactly on the deadline
   as on time.
6. Order the graded entries by project sequence, refuse a duplicate entry for
   the same review, and return compliant only when no finding was raised.

## Pitfalls

- Matching the delivered depth against the demanded one as text. The ladder is
  ordered; a full dossier delivered where an assessment was owed is a pass,
  and treating it as a mismatch generates a finding nobody should act on.
- Counting the lead time in calendar days. Weekends make a working-day lead
  substantially longer on the calendar, and the error always makes a late
  report look on time.
- Setting one submission deadline for a review and applying it to every
  equipment. Two boxes reviewed on the same day owe different depths and
  therefore different deadlines.
- Reading an absent report as a shallow one. A report that does not exist has
  no depth to grade, and folding it into the depth finding hides that nothing
  was delivered at all.
- Grading only the review being held. The reporting record is a sequence, and
  a missing earlier report still leaves the current board without the basis
  the current analysis was built on.

## Behavior contract (gate 3)

The category, review and depth normalisation, the depth matrix, the
working-day deadline arithmetic, the three independent submission grades and
the project-level reporting verdict are exercised by the gate 3 contract test:
scripts/test_q6015_radiation_review_milestones.py against
scripts/q6015_radiation_review_milestones_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6015_radiation_review_milestones.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

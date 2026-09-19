---
name: q20-qa-deliverables
description: "Plan and audit the quality assurance documents a project owes at each review from the mapping table of ECSS-Q-ST-20C Annex I: resolve the rows the declared scope actually turns on, separate a document reissued at every review in its window from one delivered twice, hold the maturity each review owes on the draft, issued and approved ladder, measure a submission against its lead time in days before the review date, score the review as the satisfied fraction of what it owed, and walk the sequence to the first review that does not clear the threshold. Use when a delivery schedule is built or a review data pack is audited. Trigger: ecss, q-st-20c-annex-i, qa-deliverables-per-review, qa-document-review-matrix, qa-document-maturity-ladder, qa-submission-lead-time, review-readiness-rollup."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-qa-deliverables, qa-deliverables-per-review, qa-document-review-matrix, qa-document-maturity-ladder, qa-submission-lead-time, qa-review-readiness-rollup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Quality Assurance Deliverables Per Review (space-systems/ecss/q20-qa-deliverables)

Use when the task is the Annex I mapping of ECSS-Q-ST-20C taken as a
delivery schedule: a project is planning which quality assurance document
reaches which review, or a review data pack has arrived and the question is
whether it carries what that review was owed.

## Domain quick reference

- The mapping is a schedule, not a list. Each row names the review a
  document is first owed at and the review by which it is approved, and the
  gap between the two is where the document matures. Reading the table as a
  flat list of documents loses the only information a planner needs.
- Two kinds of row behave differently in that gap. A plan is delivered once
  in draft and once approved and is silent in between; a status list is
  reissued at every review in its window, because its whole value is being
  current. Treating a status list as a one-shot delivery is how a project
  arrives at qualification with a nonconformance list from the design
  phase.
- Maturity is owed, not offered. A document arriving in draft at the review
  that owes it approved is a finding even though the document is present,
  and a document arriving approved early is not a finding at all.
- Scope decides which rows exist. A project with no software owes no
  software product assurance plan, and grading it against the full table
  manufactures findings that cannot be closed.
- A document is late when it arrives inside its lead time, not when it
  arrives after the review. The lead time exists so the reviewers can read
  it, and a data pack landing the day before is unread evidence.
- A document nobody asked for at this review is not a defect. It is listed
  as unplanned, because it usually means a row was read off the wrong line
  of the table, which is worth knowing while grading the rest.
- The useful programme-level answer is the first blocking review. A list of
  every gap across the sequence is a report; the earliest review that does
  not clear its threshold is a date.

## Workflow

1. Normalise the review, resolving a spelled-out name to its short form,
   and normalise the declared scope flags.
2. Resolve the rows the review owes for that scope, taking a recurring row
   at every review inside its window and a one-shot row only at its first
   and closing reviews.
3. Derive the maturity each row owes at that review from its position
   between first delivery and approval.
4. Normalise the submitted set, refusing a duplicated document and an
   unrecognised maturity, and list anything not on the schedule as
   unplanned rather than failing it.
5. Grade each owed row: missing, below the maturity owed, or inside its
   lead time when a review date is supplied.
6. Score the review as the satisfied fraction, compare with the threshold
   using a named tolerance, and walk the sequence to the first review that
   does not clear it.

## Pitfalls

- Delivering a status list once. The rows that recur are the ones whose
  content moves, and a current list is the entire point of them.
- Grading presence and ignoring maturity. A draft at the approval review is
  a present document and an unmet deliverable at the same time.
- Auditing against the whole table regardless of scope. Rows gated by
  software, procured items or ground support equipment produce
  uncloseable findings on a project that has none.
- Checking the submission date against the review date. The lead time is
  the check; arriving before the review and after the lead time is still
  evidence nobody read.
- Reporting every gap in the sequence. The first blocking review is the
  answer a schedule question wants; the rest of the list follows from it.

## Behavior contract (gate 3)

The review normalisation and sequence, the scope gating, the recurring
versus one-shot window rule, the maturity ladder, the ISO day arithmetic
behind the lead-time check, the readiness fraction with its threshold
tolerance and the first-blocking-review rollup are exercised by the gate 3
contract test: scripts/test_q20_qa_deliverables.py against
scripts/q20_qa_deliverables_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_qa_deliverables.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

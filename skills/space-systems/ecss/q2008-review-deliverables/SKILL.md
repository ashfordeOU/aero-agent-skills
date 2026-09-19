---
name: q2008-review-deliverables
description: "Plan the storage, handling and transportation deliverables of ECSS-Q-ST-20-08C Annex E against the reviews a project actually holds: anchor each deliverable to its listed review, re-anchor it to the nearest earlier held review when the project does not run that one, step the agreed lead back in working days with weekends skipped to get a submission due day, then grade each planned submission as on time, late or unplanned and separate what blocks a schedule from what is only advisory. Use when a document schedule is being built or contested. Trigger: ecss, q-st-20-08c, annex-e-deliverable-list, storage-handling-transport-deliverables, deliverable-review-anchoring, submission-lead-working-days, deliverable-schedule-slack."
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
  tags: [ecss, q-st-20-08-storage-handling-transport-scope, q2008-review-deliverables, annex-e-deliverable-list, deliverable-review-anchoring, submission-lead-working-days, review-milestone-reanchoring, transport-deliverable-slack]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Storage, Handling and Transport -- Deliverables per Review (space-systems/ecss/q2008-review-deliverables)

Use when the task is the Annex E deliverable schedule of ECSS-Q-ST-20-08C:
the storage, handling and transportation documents each have a review they
belong to, and the question is when each one is actually due on this
project and whether the plan in front of you meets those days.

## Domain quick reference

- Annex E anchors deliverables to a full review sequence. A project that
  merges or skips a review does not thereby lose the deliverable; it
  lands at the nearest earlier review the project does hold, which pulls
  it earlier, not later. Re-anchoring is reported because it changes a
  date somebody has already planned against.
- A deliverable listed against a review with no earlier held review has
  nowhere to land. That is a project-level problem -- the review plan and
  the document plan disagree about when the project starts -- and it
  blocks rather than silently defaulting to the first milestone.
- The due day is not the review day. The reviewers need the document in
  hand beforehand, so the due day is the review day stepped back by the
  agreed lead in working days, and stepping back in calendar days moves
  the deadline onto a weekend roughly two times in seven.
- Expected of every project and expected of some are different failures.
  A missing container qualification package stops a schedule; a missing
  long-term storage extension request is a note unless the project is
  actually storing long term.
- Slack is the useful output. Late by two days and late by two months are
  the same status and very different problems, so the schedule carries
  the signed day count as well as the verdict.

## Workflow

1. Normalise the project's held reviews with their days, refusing a
   duplicate and a set whose days run backwards through the sequence.
2. Normalise the planned submissions, refusing a document that is not on
   the Annex E list and a document planned twice.
3. Anchor each deliverable: its listed review when held, otherwise the
   nearest earlier held review, otherwise unanchored and blocking.
4. Step the lead back in working days from the anchor review day to get
   the due day, skipping weekends.
5. Grade the planned submission: on time, on time exactly on the due day,
   late with its slack, or not planned at all.
6. Order the result by due day and return the findings, split by whether
   the deliverable is expected of every project, with the decision.

## Pitfalls

- Dropping a deliverable because the project does not hold its review.
  The document was never tied to the review name; it was tied to the
  point in the project the review marks.
- Re-anchoring forward to the next held review. Later is the wrong
  direction: the deliverable exists to inform a decision, and a decision
  already taken cannot be informed.
- Counting the lead in calendar days. It puts due days on weekends and
  quietly shortens the working time available to the author.
- Reading a full on-time count as an accepted schedule. An unanchored
  deliverable has no due day at all and never appears in the late count.
- Treating every Annex E line as mandatory. The optional lines exist for
  projects that do the thing, and grading them as gaps hides the
  expected deliverable that is genuinely missing.

## Behavior contract (gate 3)

The review normalisation with its ordering check, the submission
normalisation, the anchoring and re-anchoring rule, the working-day lead
subtraction, the on-time, late and unplanned grading with slack, and the
severity split driving the schedule decision are exercised by the gate 3
contract test: scripts/test_q2008_review_deliverables.py against
scripts/q2008_review_deliverables_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2008_review_deliverables.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

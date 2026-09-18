---
name: q1009-ncr-drd
description: "Generate or validate a nonconformance report against the normative data item of ECSS-Q-ST-10-09 Annex A. Use when a nonconformance has been raised on a deliverable item and the report has to be graded before it goes to a review board or is closed out: grade it at the stage it has actually reached rather than against the closure blocks, add the content the proposed disposition path carries, whether acceptance justification, repair requalification, reinspection, scrap authorisation or supplier return, derive from the report whether the internal board settles it or the customer board has to see it, and refuse a customer route closed with no customer approval recorded. Trigger: ecss, q-st-10-09-annex-a, nonconformance-report-drd-content-blocks, nonconformance-disposition-path-content, nonconformance-review-board-routing, customer-nonconformance-review-board-approval."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-ncr-drd, q-st-10-09-annex-a, nonconformance-report-drd-content-blocks, nonconformance-disposition-path-content, nonconformance-review-board-routing, customer-nonconformance-review-board-approval, nonconformance-report-stage-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Nonconformance Report DRD (space-systems/ecss/q1009-ncr-drd)

Use when the task is Annex A of ECSS-Q-ST-10-09: a nonconformance has
been raised, and the report carrying it has to be written or graded —
on the blocks its stage owes, the blocks its disposition path brings,
and the board that has to settle it.

## Domain quick reference

- The report is filled in stages, not at once. At raising it says what
  was found, on what item, against which requirement and in what
  category; at the board it adds the cause, the proposed disposition and
  the justification; at closure it adds the implementation and
  verification record and the closing authority. Grading a report at
  raising against the closure blocks refuses every honest report.
- The disposition path brings its own content. Accepting an item as it
  stands and repairing it both leave the product off the requirement, so
  each owes a technical justification and the effect on interfaces and
  lifetime; rework owes its procedure and the reinspection that
  followed; scrap owes the authorisation and the segregation record; a
  return owes the supplier authorisation and the request raised on them.
- A block is filled when it points at something readable. A ticked box
  with no entry reference behind it is an unfilled block, and the
  coverage falls accordingly.
- The board follows the content, not the habit. A major nonconformance,
  a safety effect, or a disposition leaving the product off the
  requirement routes the report to the customer board; everything else
  is settled internally. The routing is derived, so it cannot be quietly
  downgraded on the way to the meeting.
- A customer board leaves a trace. A report closed on the customer route
  with no recorded customer approval is not closed, whatever its status
  field says — and that approval is owed at closure, not at the board,
  because it is the board's output.
- Stage coverage is the graded figure; the path and customer blocks are
  pass or fail. A relaxed coverage policy may tolerate an unfilled stage
  block as an advisory, and never tolerates a missing path block.

## Workflow

1. Validate the data-item policy first: the stage coverage demanded, the
   routing flags for a major nonconformance and a safety effect, and
   whether a customer approval record is required. A policy routing
   neither majors nor safety effects to the customer board is refused,
   because it leaves no customer route at all.
2. Validate the report identity: a recognised stage, a recognised
   category, a recognised disposition where one is proposed, a boolean
   safety effect, a non-blank identifier and a named affected item. A
   report with no identifier or no item closes on not raised.
3. Validate the content blocks: recognised names, no block twice, a
   boolean present flag and an entry reference that may be blank but is
   then read as unfilled.
4. Refuse to grade path content when the report has reached the board
   stage with no disposition proposed; that is the finding.
5. Derive the board from the category, the safety effect and the
   disposition, and take the blocks owed: the stage blocks, the path
   blocks, and the customer approval record at closure on a customer
   route.
6. Take the stage coverage and the overall coverage, and name the
   missing base, path and customer blocks separately.
7. Close on one verdict in order: report not raised, disposition not
   proposed, base content incomplete, disposition path content missing,
   customer approval missing, ready for the customer board, ready for
   the internal board, or complete for closure. Report the board, the
   owed blocks and the coverages alongside it.

## Pitfalls

- Grading a report at raising against the closure blocks. Every report
  fails that way, and the real gap at raising goes unnoticed.
- Treating the disposition as one more free-text field. Each path brings
  content with it, and the path blocks are what make the disposition
  reviewable rather than asserted.
- Settling a use-as-is internally because it is only one part. The
  product is off the requirement, which is the customer's call whatever
  the quantity.
- Asking for the customer approval record at the board. It is the
  board's output, so demanding it as an entry condition deadlocks the
  report.
- Reading a filled-in tick as content. A present block with no entry
  reference is what the coverage figure exists to catch.

## Behavior contract (gate 3)

The policy validation, report identity validation, block validation, the
stage block sets, the disposition path blocks, the customer approval
block at closure, the board routing, the stage and overall coverages,
the missing-block reporting and the report verdict are exercised by the
gate 3 contract test: scripts/test_q1009_ncr_drd.py against
scripts/q1009_ncr_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q1009_ncr_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

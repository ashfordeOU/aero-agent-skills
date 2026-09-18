---
name: q6005-approval-of-new-circuit-designs
description: "Plan the whole ECSS-Q-ST-60-05C clause 7.3.2 approval sequence for a hybrid circuit design with no qualified predecessor to build on, from design definition review through technology and parts selection, engineering model build, design verification testing, process identification, qualification lot manufacture, the qualification test programme and results evaluation, to the approval grant. Use when a new hybrid circuit type enters approval and the question is which stage may start now and how far the grant still sits. Compute the stages whose prerequisites are met, report any stage recorded ahead of its prerequisites, and hold the grant while a stage is open or failed. Trigger: ecss, q-st-60-hybrid-scope, new-hybrid-circuit-approval-sequence, hybrid-qualification-lot, hybrid-design-verification-testing, approval-stage-prerequisite, hybrid-approval-critical-path."
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
  tags: [ecss, q-st-60-hybrid-scope, q6005-approval-of-new-circuit-designs, new-hybrid-circuit-approval-sequence, hybrid-qualification-lot, hybrid-design-verification-testing, approval-stage-prerequisite, hybrid-approval-critical-path]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Approval of New Circuit Designs (space-systems/ecss/q6005-approval-of-new-circuit-designs)

Use when the task is the heaviest branch of ECSS-Q-ST-60-05C clause 7.3
-- the clause 7.3.2 sequence owed by a hybrid circuit design that has no
qualified predecessor to inherit from, and the question of which stage
may be worked now and how far the approval grant still is.

## Domain quick reference

- Clause 7.3.2 is where a design lands when none of the lighter routes
  are open: no approved predecessor, or one that carries nothing
  forward. Nothing is inherited, so the whole sequence is owed from the
  design definition review to the grant.
- The sequence is a dependency graph, not a list. Design verification
  testing and manufacturing process identification run on separate
  branches out of technology and parts selection, and both have to land
  before the qualification lot can be built.
- A stage whose prerequisites are not finished has not really started,
  however the schedule records it. A stage recorded complete or running
  ahead of its prerequisites is a defect in the record, and it outranks
  every other reading of the position.
- The grant stage is itself a stage with prerequisites -- the
  qualification results evaluation and the design verification testing.
  A grant recorded complete with the sequence behind it open is a record
  the approval does not stand on.
- A failed stage holds the grant rather than delaying it. Nothing behind
  a failure is legitimately complete, so a failure with downstream work
  recorded done is a broken sequence, not a held one.
- Remaining time is the longest chain still to run, not the sum of what
  is left. The process identification branch is shorter than the
  verification branch, so finishing it alone moves no date at all.
- Progress reported as a fraction of nominal effort is a planning
  figure. It answers how much has been done, never whether the grant can
  be issued -- that is a separate question with a separate verdict.

## Workflow

1. Declare a state for every stage -- not started, in progress, complete
   or failed. Reject an incomplete declaration: an undeclared stage is
   not started, not absent, and defaulting it hides an untouched stage
   behind a healthy-looking plan.
2. Check the record before reading it. List every stage recorded
   complete or in progress while one of its prerequisites is not
   complete, and treat that list as the first finding.
3. Compute the stages that may be worked now: those still open whose
   prerequisites are all complete. Expect more than one where the graph
   branches.
4. Compute the remaining critical path as the longest chain through the
   open stages, taking a per-stage remaining-days override where the
   project has one and the nominal duration otherwise.
5. Report progress as the share of nominal effort complete, separately
   from the verdict, so the two are never read as the same claim.
6. Decide the grant in priority order: a broken sequence first, then a
   failed stage, then a grant only when every stage is complete, and
   pending otherwise.

## Pitfalls

- Working the sequence as a straight list. Two branches open together
  after technology and parts selection, and a plan that serializes them
  books a longer approval than the design actually needs.
- Adding up the remaining stage durations. That overstates the date by
  the whole shorter branch; the answer is the longest remaining chain,
  which the branch durations decide between them.
- Reading a completed grant stage as an approval. It is a record like
  any other, and a grant standing on an open qualification evaluation is
  exactly the defect the prerequisite check exists to surface.
- Treating a failure as a schedule slip. It holds the grant, and any
  stage recorded complete behind it makes the record itself unsafe to
  read rather than merely late.
- Quoting the completion share as readiness for the grant. A sequence
  can be most of the way through nominal effort with the qualification
  test programme untouched, because the share weighs days and says
  nothing about which stages are still owed.
- Chasing the shorter branch because it is easier to close. Finishing
  manufacturing process identification on its own leaves the
  verification branch in charge and moves no date.

## Behavior contract (gate 3)

The stage-order check, state validation, prerequisite and
sequence-violation analysis, executable-stage selection, critical path,
completion share and the priority-ordered grant verdict are exercised by
the gate 3 contract test:
scripts/test_q6005_approval_of_new_circuit_designs.py against
scripts/q6005_approval_of_new_circuit_designs_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_approval_of_new_circuit_designs.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

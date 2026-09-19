---
name: e7041-suspending-and-resuming-the-file-copy-operations
description: "Determine what a suspend or resume directive does to each on-board file copy operation under ECSS-E-ST-70-41C clause 6.23.5.3. Use when the task is pausing one copy or the whole list for a pass, a reconfiguration or a power constraint, and then restarting it: allowing only a running operation to suspend and only a suspended one to resume, refusing both on a completed operation, separating a redundant directive from a refused one, holding the octets already moved so resumption continues rather than restarts, and refusing to move octets while suspended. Trigger: ecss, e-st-70-41c, pus-file-management, copy-operation-suspend-directive, copy-operation-resume-directive, suspend-all-file-copies, copy-progress-preserved-across-suspension, copy-operation-lifecycle-state."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-suspending-and-resuming-the-file-copy-operations, copy-operation-suspend-directive, copy-operation-resume-directive, suspend-all-file-copies, copy-progress-preserved-across-suspension, copy-operation-lifecycle-state]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Suspending and Resuming File Copy Operations (space-systems/ecss/e7041-suspending-and-resuming-the-file-copy-operations)

Use when the task is the suspension and resumption of file copy
operations of ECSS-E-ST-70-41C clause 6.23.5.3 -- the directives that
pause a copy the on-board service has already admitted, and the
directives that let it carry on from where it stopped.

## Domain quick reference

- Suspension is a lifecycle state on the operation, not a property of
  the subservice. Each entry is running, suspended or completed, and a
  suspend-all is a loop over entries, not a single switch that the
  entries then have to be interrogated against.
- Only a running operation can be suspended and only a suspended one
  can be resumed. The two directives are not symmetric switches; each
  has one legal predecessor state.
- A completed operation is out of reach of both directives. It has
  already delivered its file, so suspending it is meaningless and
  resuming it would have to invent work that no longer exists.
- A directive that changes nothing and a directive that could not be
  carried out are different results. Suspending an already-suspended
  copy is redundant and harmless; suspending a copy nobody holds means
  the ground is tracking an operation the spacecraft is not, and that
  needs to surface.
- Progress survives the pause. The octets already moved stay on the
  entry, so resumption picks up at the next octet. A resume that
  restarts the file wastes the downlink twice and, worse, looks like
  success.
- Nothing may move while suspended. A subservice that keeps writing
  through a suspension has not suspended anything, and the operator who
  asked for the pause has been told it happened.
- A list with entries left but nothing running is a distinct condition.
  It is not an error, but it is the state in which a forgotten
  suspend-all quietly stalls every transfer on board.

## Workflow

1. Validate each entry: a four-part copy key, a positive total, octets
   moved no greater than that total, and a known lifecycle state.
   Reject a list carrying the same key twice.
2. Read the directive: suspend or resume against one named key, or
   suspend-all or resume-all against the list. A single directive
   without a key, and an all-directive with one, are both input errors.
3. Resolve the key against the list. An unmatched key is refused with
   that reason, never absorbed as a no-op.
4. Apply the transition: running to suspended on suspend, suspended to
   running on resume.
5. Categorize the result as changed, redundant or refused, and carry
   the reason on the last two.
6. Leave the octets moved untouched by every transition, so resumption
   continues the same transfer.
7. Refuse an octet advance on a suspended or completed entry; allow it
   only on a running one, and complete the entry on its last octet.
8. Summarize the list by state with the octets still outstanding, and
   raise a finding when directives were refused, when they changed
   nothing, and when no uncompleted operation is left running.

## Pitfalls

- Holding suspension as one subservice-wide flag. A per-operation
  suspend then cannot be expressed, and a resume-all silently restarts
  copies that were paused individually for their own reasons.
- Resetting the octet count on resume. The transfer restarts from zero
  and the report still says the operation is progressing normally.
- Letting a suspended operation keep copying. The state says paused,
  the octets say otherwise, and only the second report reveals it.
- Treating a redundant directive as a failure, or a refused one as
  success. Both distort the picture the ground uses to decide the next
  directive.
- Allowing suspend or resume on a completed operation. It adds a
  transition out of a terminal state and makes the state machine
  unprovable.
- Reporting a fully suspended list as healthy because no directive was
  refused. Nothing being refused and nothing progressing are perfectly
  compatible, and that is the condition worth flagging.

## Behavior contract (gate 3)

The entry validation, duplicate key rejection, suspend and resume
transitions, completed-state refusal, redundant against refused
outcomes, progress preservation across a pause, the refusal to move
octets while suspended, the all-list directives and the campaign
summary are exercised by the gate 3 contract test:
scripts/test_e7041_suspending_and_resuming_the_file_copy_operations.py
against
scripts/e7041_suspending_and_resuming_the_file_copy_operations_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_suspending_and_resuming_the_file_copy_operations.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

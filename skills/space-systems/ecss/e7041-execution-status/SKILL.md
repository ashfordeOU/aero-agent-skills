---
name: e7041-execution-status
description: "Derive the execution status of an on-board control procedure from the facts the engine can observe, under ECSS-E-ST-70-41C clause 6.18.4.3. Use when the task is settling whether a procedure is aboard, idle, running, holding or finished, and if finished whether it completed or aborted: refusing a combination of facts that cannot happen, reconciling a status the ground still holds against the spacecraft, telling a held procedure that still owns its engine slot from a finished one that released it, and grouping a whole set. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, obcp-execution-status, obcp-execution-status-derivation, obcp-terminated-completed-versus-aborted, obcp-engine-slot-occupancy, obcp-ground-status-reconciliation."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-execution-status, obcp-execution-status, obcp-execution-status-derivation, obcp-terminated-completed-versus-aborted, obcp-engine-slot-occupancy, obcp-ground-status-reconciliation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Execution Status (space-systems/ecss/e7041-execution-status)

Use when the task is the execution status of ECSS-E-ST-70-41C clause
6.18.4.3 -- the single value that says where an on-board control
procedure stands, and whether the facts behind it could ever have been
true together.

## Domain quick reference

- Every procedure the spacecraft holds is in exactly one execution
  status at any moment, and that one value is what the ground reasons
  with. Six of them cover the ground: not loaded, loaded and inactive,
  active and running, active and suspended, terminated having
  completed, terminated having aborted.
- The status is a derived quantity, not a stored one. It follows from
  facts the engine can observe -- is it aboard, was it started, is it
  holding, did it finish, and on what terms. Storing it as a
  free-standing field is how a ground model ends up holding a value
  that its own facts contradict.
- Not loaded and loaded but idle look alike from a distance and are not
  the same finding. One says the procedure is not aboard and nothing
  can run it; the other says it is aboard, ready, and simply has not
  been activated.
- Completed and aborted are both terminal and are never
  interchangeable. A run that ended on its own terms and one cut short
  by command or fault produce the same absence of activity, and only
  the recorded reason tells them apart.
- A suspended procedure still owns its engine slot. It is not a cheap
  parking position: against a concurrency limit it costs exactly what a
  running one costs, and the slot comes back only on termination.
- Some combinations of facts are not statuses at all. Held but never
  started, finished but never started, running while not loaded,
  finished with no reason recorded -- each is a defect in whatever
  produced the record, and naming a status for it buries the defect.

## Workflow

1. Validate the facts: a non-empty id and genuine booleans. Reject an
   integer standing in for a flag; it reads as true and hides a field
   that was never set.
2. Collect every contradiction before deciding anything, and report all
   of them rather than the first. A record is usually wrong in more
   than one way.
3. Raise on a contradictory record instead of naming a status for it.
   The contradiction is the finding.
4. Derive in order: not aboard settles it; then finished, with the
   reason choosing completed or aborted; then holding; then started;
   otherwise loaded and inactive.
5. Group each derived status into absent, idle, executing or terminal
   when the question is about the fleet rather than one procedure.
6. Reconcile a status the ground still holds against the derived one,
   and report agreement at both the status and the category level -- a
   ground that has running where the truth is suspended is wrong in a
   different way from one that has running where the truth is finished.
7. Count engine slot demand from the derived statuses, counting held
   procedures, and compare against the concurrency limit. Demand
   exactly at the limit is full, not over.

## Pitfalls

- Storing the status instead of deriving it. The stored value survives
  the facts that justified it, and the disagreement surfaces as a
  command sent to a procedure that finished hours ago.
- Reading not loaded as idle. Activating something that is not aboard
  fails for a reason the operator did not plan for.
- Collapsing completed and aborted into finished. The whole operational
  content of a terminal status is which of the two it was.
- Treating a suspended procedure as having released its slot. The
  concurrency limit then reads free when it is not, and the next
  activation is refused by the engine rather than by the plan.
- Naming a status for an impossible record. A record that says held and
  never started has a defect upstream, and picking the nearest
  plausible status forwards the defect as a fact.
- Reporting only the first contradiction found. The second one is
  usually the one that explains the first.

## Behavior contract (gate 3)

The fact validation, boolean strictness, full contradiction set,
derivation order, completed-versus-aborted split, category grouping,
engine slot ownership of a held procedure, ground reconciliation at
both status and category level, fleet summary counts and the
concurrency-limit demand check are exercised by the gate 3 contract
test: scripts/test_e7041_execution_status.py against
scripts/e7041_execution_status_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e7041_execution_status.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

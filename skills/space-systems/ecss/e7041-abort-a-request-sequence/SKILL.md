---
name: e7041-abort-a-request-sequence
description: "Perform the abort of one executing request sequence under ECSS-E-ST-70-41C clause 6.21.5.7 and report honestly what it did and did not stop. Use when an operator wants a running sequence halted and the engine must decide accept or refuse: refusing an unknown or non-executing identifier rather than absorbing it, stopping at a request boundary without recalling requests already released, discarding the pending requests instead of deferring them, keeping the body loaded so it can be started again, refusing a second abort, and reporting the step reached with released and discarded counts. Trigger: ecss, e-st-70-41-packet-utilization-scope, request-sequence-abort, request-sequence-abort-boundary, request-sequence-discarded-requests, request-sequence-abort-report."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-abort-a-request-sequence, request-sequence-abort, request-sequence-abort-boundary, request-sequence-discarded-requests, request-sequence-abort-report]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Abort a Request Sequence (space-systems/ecss/e7041-abort-a-request-sequence)

Use when the task is the abort request of ECSS-E-ST-70-41C clause
6.21.5.7 -- stopping one sequence that is currently executing, with
the six normative items that clause places on what an abort is
entitled to change and what it must report.

## Domain quick reference

- An abort is reached for in a hurry, which is exactly why its limits
  have to be written down. Almost every intuition an operator brings
  to it is wrong in some detail that matters.
- It does not recall anything. Requests already released are running
  in their destination applications, and the sequence stopping has no
  effect on them whatsoever.
- It is not a pause. The pending requests are discarded, so there is
  no resumption point and nothing is waiting to be released later.
- It does not unload. The body stays in the store, which is what lets
  the sequence be activated again from its first request without a
  second uplink.
- It takes effect at a request boundary, so the step reached is a
  fact worth reporting: it is the dividing line between what the
  ground still has to clean up and what never happened.
- A sequence that is not executing is refused, and the refusal says
  which of the three it was -- never started, already aborted, or
  already finished. Those three call for different next actions.
- The count of released requests is the operationally important
  number in the report. It tells the ground how much recovery work the
  abort just created rather than avoided.

## Workflow

1. Normalize the store first and reject it outright on a duplicate
   identifier, a released count above the body length, a sequence
   executing while not loaded, an inactive sequence claiming released
   requests, or a completed one with requests still pending.
2. Resolve the requested identifier. An absent sequence is one
   refusal and no state is examined.
3. Refuse anything that is not executing, choosing the code that says
   which state it was actually in.
4. Split the body at the boundary reached: the released count is what
   has gone out, the remainder is what the abort discards.
5. Mark the sequence aborted, record the discarded count, leave the
   released count alone and keep the body loaded and reactivatable.
6. Close with the report -- sequence, step reached, released,
   discarded, body retained -- and raise a finding whenever requests
   had already been released, because those need their own recovery.

## Pitfalls

- Reporting an abort as though it undid the sequence. The released
  requests are already executing elsewhere and the ground reads a
  clean abort as nothing left to do.
- Rewinding the released count to zero on abort. The report then
  says nothing went out, which is the one number an operator needs to
  plan recovery from.
- Unloading the body along with the abort. Re-activating then needs a
  fresh uplink, which is the slowest possible response during the
  event that made the abort necessary.
- Treating an abort as a pause with a resumption point. Nothing is
  held, and a later resume request finds no state to resume into.
- Absorbing an abort of a sequence that was never running. The
  operator sees success, believes the wrong sequence was stopped, and
  the one actually misbehaving keeps going.
- Reporting a second abort as successful. The step reached is then the
  old one, and the ground concludes the sequence stopped twice at the
  same place rather than that the first abort already handled it.
- Collapsing not-started, already-aborted and already-completed into
  one refusal. Each needs a different next action and the service
  already knew which one applied.

## Behavior contract (gate 3)

The store normalization, identifier resolution, execution-state
refusal codes, boundary split into released and discarded, state
transition that retains the body, the released-count recovery finding
and the abort report are exercised by the gate 3 contract test:
scripts/test_e7041_abort_a_request_sequence.py against
scripts/e7041_abort_a_request_sequence_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_abort_a_request_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

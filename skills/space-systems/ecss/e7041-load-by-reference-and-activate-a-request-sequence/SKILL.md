---
name: e7041-load-by-reference-and-activate-a-request-sequence
description: "Execute the combined load-by-reference and activation request of ECSS-E-ST-70-41C clause 6.21.5.6 as one atomic act. Use when a request names a body the on-board repository already holds rather than carrying it inline, and the engine must both write it into a destination slot and start it: refusing an unresolvable reference before anything is written, never loading over a slot that is executing, verifying the landed copy against the source checksum before activation, rolling the load back whenever activation cannot proceed, applying the ordinary activation preconditions, and naming the step that failed. Trigger: ecss, e-st-70-41-packet-utilization-scope, request-sequence-load-by-reference-and-activate, request-sequence-load-and-activate-atomicity, request-sequence-copy-checksum-verification, request-sequence-load-rollback."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-load-by-reference-and-activate-a-request-sequence, request-sequence-load-by-reference-and-activate, request-sequence-load-and-activate-atomicity, request-sequence-copy-checksum-verification, request-sequence-load-rollback]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Load by Reference and Activate a Request Sequence (space-systems/ecss/e7041-load-by-reference-and-activate-a-request-sequence)

Use when the task is the combined request of ECSS-E-ST-70-41C clause
6.21.5.6 -- naming a sequence body the on-board repository already
holds, writing it into a destination slot and starting it in the same
request, with the six normative items that clause places on the act.

## Domain quick reference

- The plain load request carries the body inside it. This one carries
  a reference, so the body never crosses the uplink and the repository
  becomes part of the trust chain rather than the packet.
- A request that does two things can half-succeed. That is the whole
  reason this clause is separate from a plain activation: the failure
  modes live in the seam between the load and the start.
- An unresolvable reference is refused before anything is written. The
  destination slot must not be cleared in preparation for a body that
  turns out not to exist.
- A slot whose sequence is executing is never loaded over. The engine
  is mid-way through the old body, and replacing it underneath leaves
  a step counter pointing into requests from a different sequence.
- The copy is verified where it landed, against the source checksum,
  after the copy and before activation. Verifying the source proves
  only that the repository is healthy, which was never in doubt.
- Load and activate are atomic. If activation cannot proceed -- a
  damaged copy, a full engine -- the load is rolled back and the slot
  is left exactly as it was found.
- The refusal names the step. "Request failed" sends an operator to
  check the repository, the slot, the transfer and the engine in turn,
  when the service already knew which of the four it was.

## Workflow

1. Normalize the repository, the destination store, the request and
   the engine, rejecting a duplicate reference, a duplicate slot
   identifier, a slot executing while not loaded and a capacity below
   one before any step is attempted.
2. Resolve the reference. An absent body, or one carrying no requests,
   refuses at the resolve step and no later step is evaluated.
3. Evaluate the destination slot: it must exist, must not be
   executing, and must not already be under load from another request.
4. Compute what the copy in the slot actually lands on and compare it
   against the source checksum; a mismatch refuses at the verify step
   with no request released.
5. Apply the ordinary activation precondition -- a free execution slot
   in the engine -- and refuse at the activate step when there is none.
6. On acceptance, write the body, record the reference it came from
   and start at the first request; on any refusal, return the store
   untouched, mark the rollback, and emit one notification naming the
   failing step and every code it raised.

## Pitfalls

- Clearing the destination slot before the reference has resolved. A
  typo in the reference then destroys a loaded sequence that was doing
  no harm.
- Loading over an executing slot. The step counter survives the swap
  and the engine continues into requests from a body nobody activated.
- Verifying the source checksum rather than the landed copy. That
  proves the repository is intact and says nothing about the transfer,
  which is the only part that could have gone wrong.
- Leaving the load in place when activation is refused. The request
  reports failure, the slot quietly holds the new body, and the next
  activation of that slot runs something that arrived by accident.
- Treating a full engine as a reason to skip the load. The rollback
  exists so the two steps can be attempted honestly; skipping one to
  avoid undoing it makes the outcome depend on evaluation order.
- Reporting "request failed" without the step. Four independent
  subsystems then get investigated for a fault the service had already
  localized.
- Reusing a plain activation's notification for this request. It names
  no reference, so the ground cannot tell which repository body the
  slot was supposed to receive.

## Behavior contract (gate 3)

The repository, store, request and engine normalization, reference
resolution, destination-slot eligibility, landed-copy verification,
engine capacity at the activate step, per-step refusal grouping,
atomic apply and rollback, and the step-naming notification are
exercised by the gate 3 contract test:
scripts/test_e7041_load_by_reference_and_activate_a_request_sequence.py
against
scripts/e7041_load_by_reference_and_activate_a_request_sequence_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_load_by_reference_and_activate_a_request_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

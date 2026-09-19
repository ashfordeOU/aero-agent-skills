---
name: e7041-direct-load-a-request-sequence
description: "Simulate a direct load of a request sequence into the on-board sequence store under ECSS-E-ST-70-41C clause 6.21.5.2, and decide whether it is taken. Use when a single command carries both the sequence identifier and the whole ordered body inline: refusing a load over an identifier the store already holds rather than overwriting it, refusing an empty body, grading every carried request before anything is stored so one bad request fails the load, refusing a body that targets its own sequence, fitting the header-inclusive size to the free capacity, and leaving the store untouched on any refusal. Trigger: ecss, e-st-70-41-packet-utilization-scope, direct-load-request-sequence, request-sequencing-service, request-sequence-store-free-capacity, all-or-nothing-sequence-load, inline-carried-sequence-body."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-direct-load-a-request-sequence, direct-load-request-sequence, request-sequencing-service, request-sequence-store-free-capacity, all-or-nothing-sequence-load, inline-carried-sequence-body]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Direct-Load a Request Sequence (space-systems/ecss/e7041-direct-load-a-request-sequence)

Use when the task is the direct load of
ECSS-E-ST-70-41C clause 6.21.5.2 -- a single command that carries the
sequence identifier and the whole ordered body inline, with the six
normative items that clause places on accepting it and on what the
store looks like afterwards.

## Domain quick reference

- A direct load carries everything it needs. No file, no repository,
  no second command: the body arrives in the load packet, which is
  why the acceptance decision can be made entirely on arrival.
- A load over a held identifier is refused, not an overwrite. The
  ground that wanted a replacement has to unload first, so the store
  never silently swaps a procedure under an operator who believed the
  old one was still there.
- An empty body is a refusal, not an empty sequence. A sequence with
  nothing to run is a load that lost its content in transit far more
  often than it is a deliberate request.
- Every carried request is graded before anything is stored. Grading
  as they are stored leaves half a procedure behind when the fifth
  request turns out to be malformed.
- One unacceptable request fails the whole load. A partially loaded
  procedure is worse than no procedure, because it looks runnable.
- Size is measured with the headers, at the moment of the load. The
  free capacity is a live figure and the check has to use the one
  that holds when the load is applied, not a cached one.
- A body naming its own sequence is refused. The recursion has no
  bound on board, and discovering it at run time means discovering it
  with a full store.
- The load is all or nothing. On success the store holds exactly the
  carried requests in the carried order and the free capacity drops
  by the loaded size; on refusal nothing moved at all.

## Workflow

1. Normalize the load request into an identifier and a carried body,
   rejecting a load with no request list at all.
2. Normalize the store: held sizes and counts, used total and the
   free capacity that follows from the declared capacity.
3. Refuse immediately, but keep collecting reasons, when the
   identifier is already held.
4. Grade the whole carried body before touching the store: at least
   one request, each with an application identifier, a service type
   and subtype in range and a payload inside the packet limit, and
   none targeting the sequence being loaded.
5. Size the body with a header per request and compare it against
   the free capacity read from the store now.
6. Apply the load only when no reason was collected, otherwise return
   the store exactly as it arrived along with every reason at once.

## Pitfalls

- Overwriting a held sequence because the load looks like an update.
  The operator who is about to run the old procedure gets the new one.
- Storing requests as they are graded. The store then keeps the
  prefix of a procedure that was never accepted.
- Sizing the load from payloads alone. Each request also costs a
  header, so the store overfills against a check that said it fit.
- Checking the free capacity against a figure read before the store
  was normalized. Another load in the same pass has already spent it.
- Returning on the first refusal reason. The ground then fixes the
  identifier clash, re-sends, and discovers the capacity problem on
  the next pass instead of this one.
- Accepting an empty body as a sequence that does nothing. It is far
  more often a load whose content was lost on the way up.

## Behavior contract (gate 3)

The load-request normalization, the store and free-capacity model,
the already-held refusal, the whole-body grading with the position of
each finding, the self-reference refusal, the header-inclusive
capacity fit and the all-or-nothing application are exercised by the
gate 3 contract test:
scripts/test_e7041_direct_load_a_request_sequence.py against
scripts/e7041_direct_load_a_request_sequence_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_direct_load_a_request_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

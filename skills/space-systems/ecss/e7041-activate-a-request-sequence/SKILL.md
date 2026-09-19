---
name: e7041-activate-a-request-sequence
description: "Determine whether a stored request sequence may be activated under ECSS-E-ST-70-41C clause 6.21.5.5, and release its first request only once every precondition holds. Use when an activation request names a sequence and the on-board engine must decide accept or refuse: refusing an unknown identifier instead of running nothing, refusing a sequence still under load, refusing one already executing rather than interleaving a second run, checking the stored body against its checksum before anything reaches a destination, honouring the engine's concurrent-execution capacity, and emitting one notification that names the sequence and every reason. Trigger: ecss, e-st-70-41-packet-utilization-scope, request-sequence-activation, request-sequence-activation-preconditions, request-sequence-engine-capacity, request-sequence-activation-refusal-notification."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-activate-a-request-sequence, request-sequence-activation, request-sequence-activation-preconditions, request-sequence-engine-capacity, request-sequence-activation-refusal-notification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Activate a Request Sequence (space-systems/ecss/e7041-activate-a-request-sequence)

Use when the task is the activation request of ECSS-E-ST-70-41C clause
6.21.5.5 -- taking a request sequence the on-board store already holds
and starting it, with the six normative items that clause places on the
decision.

## Domain quick reference

- Loading and activating are different acts on the same object. A
  sequence can sit loaded for weeks without one of its requests ever
  reaching a destination application. Activation is the moment that
  changes, and it is the last cheap moment to refuse.
- An unknown identifier is a refusal, never an empty run. Silently
  succeeding on a sequence nobody holds looks identical on the ground
  to a sequence that ran and did nothing, and those two call for
  opposite responses.
- A sequence still under load has no defensible body. Half a sequence
  is not a shorter sequence; it is a sequence whose remaining requests
  are unknown to everyone including the engine.
- Activation verifies the stored body against its stored checksum.
  After the first request is released the damage is already outside the
  service, so this check is worth nothing done one step later.
- Already-executing is a refusal, not a restart. Interleaving a second
  run of the same sequence puts two step counters on one body and the
  destination application sees requests in an order nobody authored.
- Concurrent capacity belongs to the engine, not to the request. The
  request cannot raise it, and a request already holding a slot must
  not be charged for a second one.
- Every refusal carries the sequence identifier and all of its reasons
  at once. Reporting the first reason only forces the operator to
  rediscover the rest one activation attempt at a time.

## Workflow

1. Normalize the store first and reject it outright on a duplicate
   identifier, a load state that is not one of the three, a loaded
   sequence carrying no requests, an empty one carrying some, or a
   sequence executing while it is not fully loaded.
2. Normalize the engine and reject a capacity below one; an engine
   that can run nothing cannot be the reason an activation was refused.
3. Resolve the requested identifier against the store. An absent
   sequence yields exactly one refusal and the remaining checks are
   not attempted against a record that does not exist.
4. Evaluate the load state, the execution state, the body checksum and
   the free-slot count, collecting every refusal rather than returning
   on the first.
5. On acceptance, mark the sequence executing and set its step counter
   to the first request; on refusal, return the store untouched.
6. Close with the verdict, the refusal codes, the notification the
   ground receives, and the running total after the decision.

## Pitfalls

- Treating an unknown identifier as a no-op. The activation reports
  success, nothing runs, and the operator concludes the sequence was
  empty rather than absent.
- Activating a sequence that is still under load. The engine executes
  the part that arrived and stops, which reads on the ground as a
  sequence that completed.
- Restarting a running sequence instead of refusing. Two step counters
  advance over one body and the destination receives requests in an
  order the author never wrote.
- Verifying the body checksum after the first request is released. The
  check then reports damage that has already left the service.
- Charging an execution slot to a sequence that already holds one. A
  re-activation attempt is refused for capacity rather than for the
  real reason, which is that it is already executing.
- Returning on the first refusal. The operator fixes the load state,
  retries, and discovers the checksum problem on the second attempt
  that could have been reported on the first.
- Mutating the store while collecting refusals. A refused activation
  then leaves a half-started sequence behind that no later request
  knows how to clear.

## Behavior contract (gate 3)

The store and engine normalization, identifier resolution, load-state
and execution-state refusals, body-checksum verification, free-slot
accounting, refusal accumulation, state transition on acceptance and
untouched store on refusal are exercised by the gate 3 contract test:
scripts/test_e7041_activate_a_request_sequence.py against
scripts/e7041_activate_a_request_sequence_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_activate_a_request_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e7041-request-sequence
description: "Model the on-board request sequence of ECSS-E-ST-70-41C clause 6.21.4 and decide whether one is well formed, holdable and runnable. Use when reasoning about a named block of requests the ground fires with a single command: keeping the identifier unique in the sequence store, insisting on at least one request and treating the held order as part of the sequence, checking each request would stand alone, refusing a sequence that loads or runs itself, fitting the loaded size to the declared store capacity, policing the absent to loaded to executing lifecycle, and stopping a run at the first failing request. Trigger: ecss, e-st-70-41-packet-utilization-scope, on-board-request-sequence, request-sequencing-service, request-sequence-store-capacity, request-sequence-lifecycle, request-sequence-self-reference."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-request-sequence, on-board-request-sequence, request-sequencing-service, request-sequence-store-capacity, request-sequence-lifecycle, request-sequence-self-reference]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Request Sequence (space-systems/ecss/e7041-request-sequence)

Use when the task is the request sequence itself as defined by
ECSS-E-ST-70-41C clause 6.21.4 -- the named, ordered block of requests
the sequencing service holds, runs and releases, with the seven
normative items that clause places on its structure, its capacity and
its behaviour when a held request fails.

## Domain quick reference

- A request sequence is a unit, not a list. It is named, held, run
  and released whole, so everything the ground can do to it is
  addressed by the identifier rather than by the requests inside it.
- The order is the sequence. A block of requests reordered is a
  different procedure, which is why the order is validated and
  preserved rather than recovered from timestamps at run time.
- Each held request has to be one the application would accept on its
  own. A sequence is not a place where a malformed request becomes
  acceptable by being carried with valid company.
- A sequence that loads, unloads or runs itself is refused. The
  recursion has no bound on board and the store has no room to
  discover that at run time.
- Size is measured with the headers, because that is what the store
  actually spends. A capacity check against payload alone under-counts
  by a header per request and overfills the store.
- The lifecycle is small and closed: absent, loaded, executing, then
  loaded again or aborted. An out-of-lifecycle move is refused, not
  forced through to whatever state was asked for.
- A run stops at the first failure and says where. Continuing past a
  failed request runs the rest of a procedure whose preconditions the
  failure has just removed.
- Reporting the index it stopped at is what makes the failure
  recoverable. The ground can re-enter the procedure at that point
  instead of re-running the part that already succeeded.

## Workflow

1. Normalize each held request first: application identifier, service
   type and subtype in range, and a payload inside the packet limit.
2. Reject a sequence with no requests, and reject any held request
   that targets its own sequence through the sequencing service.
3. Compute the loaded size as the payload plus the header of every
   held request, and carry that with the sequence.
4. Normalize the store: unique identifiers, and a used total that the
   declared capacity can actually hold.
5. Assess a candidate sequence against the store: identifier not
   already held, and loaded size inside the free capacity.
6. Police every state change through the closed lifecycle, and run a
   sequence only from the loaded state.
7. Run the held requests in order, stopping at the first failure and
   returning the index, the count issued and the count left.

## Pitfalls

- Sizing a sequence from its payloads alone. Every request also costs
  a header, so the store fills before the capacity check says it will.
- Recovering the execution order from anything but the held order. A
  procedure reordered by an implementation detail is a new procedure.
- Continuing a run past a failed request. The rest of the sequence
  assumes an effect the failure prevented, and the damage is done
  before the ground sees the first failure report.
- Reporting only that a run failed. Without the index, recovery has
  to re-run requests that already succeeded.
- Allowing an executing sequence to be unloaded. The store frees a
  block that the running procedure is still reading out of.
- Letting a sequence hold a request that loads itself. Nothing on
  board bounds the recursion, and the fault appears as a full store
  rather than as the bad sequence that caused it.

## Behavior contract (gate 3)

The held-request normalization, the self-reference refusal, the
header-inclusive size, the store capacity check, the closed lifecycle
and the stop-at-first-failure run are exercised by the gate 3
contract test: scripts/test_e7041_request_sequence.py against
scripts/e7041_request_sequence_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e7041_request_sequence.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

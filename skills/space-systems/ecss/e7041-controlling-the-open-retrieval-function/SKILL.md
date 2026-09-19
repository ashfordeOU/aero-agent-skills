---
name: e7041-controlling-the-open-retrieval-function
description: "Model the open retrieval state machine of the on-board packet stores under ECSS-E-ST-70-41C clause 6.15.3.4. Use when a start, suspend, resume or abort goes to packet stores and the question is which of them accept it: opening a retrieval only where none is engaged, refusing a store already in a by-time-range retrieval, placing the cursor on the first packet at or after the start time, accepting a start beyond everything held, keeping overwrite protection across a suspension, and accepting a repeated abort as no change. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, open-retrieval-control, suspend-open-retrieval, open-retrieval-overwrite-protection, packet-store-retrieval-cursor."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-controlling-the-open-retrieval-function, open-retrieval-control, suspend-open-retrieval, open-retrieval-overwrite-protection, packet-store-retrieval-cursor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Controlling the Open Retrieval Function (space-systems/ecss/e7041-controlling-the-open-retrieval-function)

Use when the task is the open-retrieval control of ECSS-E-ST-70-41C
clause 6.15.3.4 -- starting, suspending, resuming and aborting the
retrieval that follows a packet store forward instead of reading a
closed window out of it, and the state each named store is left in.

## Domain quick reference

- An open retrieval has no end. It is positioned at a start time and
  then downlinks packets as they keep arriving, so it is a
  subscription to the store's future rather than a read of its past.
- Because it never ends on its own, it is durable state the store
  carries until the ground takes it away. Everything else in the
  clause follows from that.
- One cursor per store. A store cannot carry two open retrievals, and
  cannot carry an open retrieval alongside a by-time-range retrieval,
  so a start is refused on a store already engaged in either.
- The start time selects, it does not validate. The cursor lands on
  the first packet at or after it and the earlier packets are skipped;
  a start time past everything held is accepted and simply yields
  nothing until the next packet arrives.
- A circular store may not overwrite the packets from the cursor
  forward. Against that part of its content it behaves like a bounded
  store, and the packets it would have overwritten are lost at the
  input instead.
- Suspending does not release that protection. A suspended retrieval
  still pins its cursor, so a suspension left in place quietly turns a
  circular store into a bounded one and the store starts refusing new
  packets at the front.
- Abort is the only thing that releases the cursor, so abort is
  idempotent: on a store with no retrieval it is accepted and changes
  nothing, and a retry after a lost acknowledgement is not a fault.
- Suspend and resume are not idempotent, because each names a
  transition rather than a state. A resume on a running retrieval is
  refused rather than treated as a harmless repeat.

## Workflow

1. Normalize the held stores first: packets in non-decreasing storage
   time with no repeated identity, a known retrieval state, a cursor
   present exactly when a retrieval is open, and no store claiming
   both retrieval kinds at once.
2. Normalize each command: the action must be one of start, suspend,
   resume or abort, the store list must be non-empty and free of
   repeats, and only a start may carry a retrieval start time.
3. Walk the named stores in command order, rejecting a name the
   application does not hold for that store alone and continuing.
4. For a start, refuse a store already engaged in either retrieval
   kind, then place the cursor at the start time and record how many
   packets were skipped and how many are pending.
5. For suspend and resume, check the current state before moving it,
   and for abort clear the cursor and release the protection.
6. Assemble the per-store report -- retrieval state, cursor, protected
   packet count, range-retrieval flag -- and raise a finding for every
   store left suspended, because that is a protection nobody is using.

## Pitfalls

- Treating suspend as a release of the overwrite protection. The
  circular store then overwrites exactly the packets the ground
  suspended the retrieval to keep, and the hole is not marked.
- Leaving a store suspended indefinitely. The protection is still
  held, the store fills from the front, and new packets are refused by
  a store that reports plenty of capacity.
- Letting a second start re-position an open retrieval. The packets
  between the old cursor and the new one are never downlinked and
  nothing records that they were skipped.
- Allowing an open retrieval on a store already running a by-time-range
  retrieval. One cursor cannot serve both, and whichever wins produces
  a downlink that matches neither request.
- Refusing a start time past everything held. An open retrieval is
  meant to be armed ahead of an event, so that refusal breaks the
  clause's main use.
- Making abort a state-guarded transition. A retry after a lost
  acknowledgement then reports a fault on a store that is already in
  the state the operator wanted.
- Making resume idempotent to match abort. Resume names a transition
  from suspended, and accepting it on a running retrieval hides the
  fact that the ground's picture of the store is wrong.

## Behavior contract (gate 3)

The store and command normalization, cursor placement against the
start time, the start, suspend, resume and abort transitions with
their refusals, overwrite protection across a suspension, partial
failure over a multi-store command, the per-store report and the run
verdict are exercised by the gate 3 contract test:
scripts/test_e7041_controlling_the_open_retrieval_function.py against
scripts/e7041_controlling_the_open_retrieval_function_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_controlling_the_open_retrieval_function.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

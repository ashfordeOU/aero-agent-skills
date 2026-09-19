---
name: e7041-controlling-the-by-time-range-retrieval-function
description: "Determine what a by-time-range retrieval of an on-board packet store will actually cover under ECSS-E-ST-70-41C clause 6.15.3.5. Use when a start or abort of a bounded retrieval goes out and the requested window does not match what the store holds: rejecting an unordered window outright, refusing a store already engaged in either retrieval kind, selecting inclusively on both bounds, reporting a leading or trailing gap instead of a silent short read, and completing an empty window with no packets rather than a failure. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, by-time-range-retrieval-control, packet-store-retrieval-window, retrieval-window-coverage-gap, abort-by-time-range-retrieval."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-controlling-the-by-time-range-retrieval-function, by-time-range-retrieval-control, packet-store-retrieval-window, retrieval-window-coverage-gap, abort-by-time-range-retrieval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Controlling the By-Time-Range Retrieval Function (space-systems/ecss/e7041-controlling-the-by-time-range-retrieval-function)

Use when the task is the by-time-range retrieval control of
ECSS-E-ST-70-41C clause 6.15.3.5 -- starting and aborting the bounded
retrieval that reads a closed window out of a packet store, and
saying what the store can actually deliver against the window the
ground asked for.

## Domain quick reference

- A by-time-range retrieval terminates on its own. When the cursor
  passes the end time the store goes idle again, so abort exists for
  cutting a long read short rather than for ending it normally.
- The window is ordered. A start time at or after the end time is a
  malformed command, not a retrieval that returns nothing, because
  the two mean different things to the operator who sent it.
- Both bounds are inclusive. A packet stored exactly at the start time
  or exactly at the end time is inside the window, which is what makes
  a window built from an event time reproduce the same packets twice.
- One read cursor per store. A store already running a by-time-range
  retrieval refuses a second, and so does a store carrying an open
  retrieval, because neither request can be served half-way.
- The interesting case is a window the store does not fully hold. A
  store switched off for part of it, or a circular store that has
  already overwritten the front of it, still answers -- with the
  intersection, plus a statement of what was missing at each end.
- A gap is reported, never absorbed. Handing back fewer packets than
  the window implies, with nothing saying why, is how a data gap gets
  read as a quiet period on the spacecraft.
- An empty intersection completes with no packets. The store holding
  nothing in that window is a fact about the window, so it is an
  answer rather than a rejection.
- The covered span is measured on the packets delivered, not on the
  window requested. The two differ whenever there is a gap, and only
  the first one describes the data.

## Workflow

1. Normalize the held stores first: packets in non-decreasing storage
   time with no repeated identity, a known retrieval state, and no
   store claiming an open and a by-time-range retrieval at once.
2. Normalize each command, validating the window before anything else
   so an unordered or non-numeric bound fails as a malformed command
   rather than as an empty result.
3. Walk the named stores in command order, rejecting a name the
   application does not hold for that store alone and continuing.
4. For a start, refuse a store engaged in either retrieval kind, then
   select the packets inside the window with both bounds inclusive.
5. Work out the coverage from the selection and the span the store
   holds: complete, a leading gap, a trailing gap, both, or empty, and
   carry the covered span alongside the requested one.
6. Assemble the per-store report -- retrieval state and the window
   being served -- and close with the verdict, a finding for every
   partial or empty coverage, and every refusal named.

## Pitfalls

- Treating an unordered window as an empty retrieval. The operator who
  swapped two fields gets a clean "no packets" and concludes the store
  is empty over a period it is not.
- Making one bound exclusive. Two adjacent windows then either drop
  the packet on the seam or deliver it twice, and which one depends on
  an implementation detail nobody documented.
- Returning the intersection without saying it was an intersection.
  The missing packets look like a quiet spacecraft rather than a store
  that was switched off or had already wrapped.
- Refusing a window the store only partly holds. The part it does hold
  is usually the part that matters, and refusing it costs a pass.
- Measuring the covered span on the requested window. It then reads as
  full coverage for a retrieval that delivered a fraction of it.
- Allowing a by-time-range retrieval alongside an open one. One cursor
  cannot serve both, and the downlink that comes back matches neither
  request while appearing to answer both.
- Making abort a state-guarded transition. A retry after a lost
  acknowledgement then reports a fault against a store that is already
  idle, which is the state the operator wanted.

## Behavior contract (gate 3)

The window validation, store and command normalization, inclusive
selection on both bounds, the complete, leading-gap, trailing-gap,
both-gaps and empty coverage outcomes, the start and abort
transitions with their refusals, partial failure over a multi-store
command, the per-store report and the run verdict are exercised by
the gate 3 contract test:
scripts/test_e7041_controlling_the_by_time_range_retrieval_function.py
against
scripts/e7041_controlling_the_by_time_range_retrieval_function_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_controlling_the_by_time_range_retrieval_function.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

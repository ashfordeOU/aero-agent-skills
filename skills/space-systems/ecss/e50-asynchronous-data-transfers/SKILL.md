---
name: e50-asynchronous-data-transfers
description: "Evaluate whether an on-board network carries its asynchronous data transfers inside the time a synchronous schedule leaves free, per ECSS-E-ST-50C clause 5.7.1.4. Convert the spare window per control cycle into deliverable bits, decide whether the largest message fits one window or needs segmenting, compute the worst-case wait before a transfer starts and the cycles it takes to finish, then compare sustained capacity with the offered asynchronous rate. Use when adding file, housekeeping or payload traffic to a cyclic network. Trigger: ecss, e-st-50-communications, asynchronous-data-transfer, spare-window-capacity, asynchronous-message-segmentation, asynchronous-transfer-latency, asynchronous-starvation-check."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.7.1.4
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-asynchronous-data-transfers, spare-window-capacity, asynchronous-message-segmentation, asynchronous-transfer-latency, asynchronous-starvation-check, cyclic-schedule-leftovers]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Asynchronous Data Transfers (space-systems/ecss/e50-asynchronous-data-transfers)

Use when an on-board network already reserved for synchronous command and
control also has to carry transfers that arrive unannounced, under
ECSS-E-ST-50C clause 5.7.1.4 — file downloads, event reports and payload dumps
that have no slot of their own.

## Domain quick reference

- Asynchronous traffic lives in the leftovers and nowhere else. The
  spare window is the control cycle minus the synchronous reservation,
  and every latency and throughput figure for unscheduled traffic is a
  consequence of that one number.
- Capacity comes in two flavours and they answer different questions.
  The window capacity says whether one message fits in one go; the
  sustained capacity, the same window averaged over the cycle, says
  whether the offered stream keeps up at all. A design can pass one and
  fail the other.
- Segmentation is a real cost, not an implementation detail. A message
  larger than one window is cut across cycles, and each extra segment
  adds a whole cycle of waiting while the synchronous block runs, plus
  reassembly state at the far end.
- The worst-case start delay is the synchronous block itself. A
  transfer that becomes ready one instant after the window closed waits
  out the entire reservation before it gets anything, and that wait is
  charged before the first bit moves.
- A fully reserved cycle is not a slow network, it is a network with no
  asynchronous service at all. The right answer there is that no
  transfer can start, not a very large completion time.
- There are two ways to make a message fit one window, and both belong
  in the report: a longer spare window, which means giving back
  synchronous reservation, or a faster link. Which is available is a
  system decision and offering only one makes it for someone else.

## Workflow

1. State the control cycle, the synchronous reservation inside it, the
   link rate, the largest asynchronous message and its overhead. Refuse
   a reservation longer than its own cycle rather than clamping it —
   that contradiction belongs to the schedule upstream.
2. Compute the spare window, its capacity in bits, and the sustained
   capacity over the cycle.
3. Establish that the network offers the service its nodes are owed:
   an unscheduled path between every pair of attached nodes, whether or
   not anyone has yet named traffic to send over it. A zero spare
   window withholds that service from all of them; a missing path
   withholds it from the pair it belongs to. Stop on either and name
   which one it is, because segment counts and completion times would
   be arithmetic about a service that does not exist.
4. Compare sustained capacity with the offered asynchronous rate using
   a relative tolerance. A stream offered at exactly the capacity is
   served, not starved, on every build host.
5. Count the segments the largest message needs, snapping a division
   that lands on a whole number so a message sized to exactly fill one
   window stays a single segment.
6. Compute the worst-case completion: the synchronous block first, then
   a whole cycle for each segment but the last, then the remainder of
   the airtime.
7. Where the message needs segmenting, report both remedies with their
   numbers — the spare window it would take, and the link rate that
   delivers it inside the window already there. Where no offered rate
   was declared, say the result is latency only and carries no
   throughput claim.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.7.1.4a | 3 |

## Pitfalls

- Sizing asynchronous traffic against the link rate. The link rate is
  available only during the spare window; the number that matters is
  the window, and on a heavily scheduled cycle the two differ by an
  order of magnitude.
- Reporting the average throughput and stopping. A stream that keeps up
  on average can still contain a single message that no window can
  carry, and that message is the one that fails in flight.
- Forgetting the start delay. Airtime alone understates the worst case
  by the whole synchronous block, which on a tightly scheduled cycle is
  most of the answer.
- Counting a message that exactly fills a window as two segments. The
  division lands on a whole number, and an unguarded ceiling turns that
  into an extra cycle of latency on one build host and not another.
- Quoting a completion time for a cycle with no spare window. It
  implies a service the schedule does not provide.
- Spending the spare window without going back to the synchronous
  schedule. The two clauses share one cycle, and a remedy taken here is
  a reservation removed there.

## Behavior contract (gate 3)

Reservation validation including one longer than its cycle, the spare
window and both capacities, segmentation at and beyond the exact window
fit, the start delay, multi-cycle completion, the absent service when
nothing is spare, and the window and link-rate inverses checked against
the same model are exercised by the gate 3 contract test:
scripts/test_e50_asynchronous_data_transfers.py against
scripts/e50_asynchronous_data_transfers_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_e50_asynchronous_data_transfers.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

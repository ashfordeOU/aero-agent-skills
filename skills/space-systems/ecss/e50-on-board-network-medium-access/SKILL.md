---
name: e50-on-board-network-medium-access
description: "Determine the worst-case medium-access delay a node suffers on an on-board network, and whether that delay is bounded at all, per ECSS-E-ST-50C clause 5.7.1.5. Apply the arbitration actually used, whether time-slotted rounds, token rotation, fixed-priority bitwise arbitration or plain contention, compute the access delay each one allows, flag a scheme that gives no bound, and report medium utilisation with the node that waits longest. Use when choosing or reviewing an on-board bus arbitration scheme. Trigger: ecss, e-st-50-communications, onboard-network-medium-access, bus-arbitration-scheme, tdma-round-access-delay, token-rotation-time, fixed-priority-bus-arbitration, unbounded-contention-access."
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
  tags: [ecss, e-st-50-communications, e50-on-board-network-medium-access, bus-arbitration-scheme, tdma-round-access-delay, token-rotation-time, fixed-priority-bus-arbitration, unbounded-contention-access]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — On-Board Network Medium Access (space-systems/ecss/e50-on-board-network-medium-access)

Use when nodes share one on-board medium under ECSS-E-ST-50C clause 5.7.1.5 —
naming the arbitration that grants the medium, and stating the longest any
node can be kept off it.

## Domain quick reference

- The clause is about the grant, not the transfer. This is the wait
  before a node starts sending; what happens afterwards, across hops
  and against a deadline, is a separate question.
- Some schemes give a bound by construction. A time-slotted round makes
  collisions impossible and caps the wait at the rest of the round, so
  its bound falls out of the slot size and the node count and nothing
  else. A token caps the wait at one rotation less the node's own
  holding time, which makes the slowest node the one with the shortest
  frame.
- Fixed-priority bitwise arbitration resolves contention without a
  collision but not without a wait, and the wait is recursive: a node
  yields to one non-pre-emptable frame already on the wire, then to
  every higher-priority frame that arrives while it waits, which
  lengthens the wait and admits more. It is the fixed point of
  W = B + sum ceil(W/T_i)*C_i.
- Plain contention with random backoff has no bound at all. That is not
  a large number waiting to be computed, it is the absence of the
  guarantee this clause is about, and it has to be reported as such.
- A round sized on the average frame is a round one node cannot use.
  The uniform slot is set by the longest frame on the medium.
- Every scheme fails the same way at saturation. Once offered traffic
  reaches the capacity of the medium there is nothing left to arbitrate
  and no bound survives, whichever scheme is written in the design.

## Workflow

1. Name the arbitration scheme and refuse an unrecognised one rather
   than defaulting it. The clause exists because the scheme has to be
   stated, and a silent default answers with a guarantee nobody chose.
2. List the contending nodes with a frame size and a repetition period,
   in priority order where the arbitration uses one. Refuse two nodes
   under one name — a duplicate halves the load it should have added.
3. Compute medium utilisation with the framing overhead and guard time
   the medium actually charges, not payload bits alone.
4. Apply the scheme. Size a round on the longest frame and give every
   node the rest of the round; add up holding times and token passes
   for a rotation; iterate the arbitration fixed point per node for
   fixed priority, snapping a ceiling that lands on a whole number so
   the count does not depend on the build host.
5. Where a node's fixed point does not exist, name that node: it can be
   kept off the medium indefinitely, and that is a more specific
   finding than a load figure.
6. Report the worst node and its delay, and compare with the access
   budget using a relative tolerance so a design sized to exactly meet
   the budget passes everywhere.
7. Say what the input left out — a fixed-priority assessment with no
   blocking frame declared is missing the term that dominates the
   lowest-priority bound.

## Pitfalls

- Reporting a mean access delay. The clause asks what the medium
  guarantees, and a mean guarantees nothing; the number wanted is the
  worst case a node can be made to wait.
- Treating contention as merely slower. Backoff gives no bound, so a
  contended medium cannot carry traffic with an access requirement at
  any load, and quoting a typical figure for it hides exactly that.
- Sizing a time-slotted round on the average frame. One node then has a
  slot too short for its own frame, and the round does not work at all.
- Assuming the largest frame waits longest under a token. It is the
  other way round: the wait is a rotation less the node's own holding
  time, so the shortest frame waits longest.
- Counting each higher-priority node once under fixed priority. Past
  its period the node arrives again, and a single-activation sum
  understates every busy medium in the same direction.
- Leaving blocking out because the node is top priority. The highest
  priority node still waits for whatever non-pre-emptable frame is
  already on the wire.
- Quoting an arbitration bound on a saturated medium. Above capacity
  the arbitration has nothing to schedule and the number is fiction.

## Behavior contract (gate 3)

Scheme and node validation, framing overhead in the load, the round slot
and its access delay, token rotation and per-node wait, the fixed-priority
arbitration fixed point at each priority level and its non-existence
under saturation, the unbounded verdict for contention and for a starved
node, and the access-delay budget at and past its bound are exercised by
the gate 3 contract test:
scripts/test_e50_on_board_network_medium_access.py against
scripts/e50_on_board_network_medium_access_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_e50_on_board_network_medium_access.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

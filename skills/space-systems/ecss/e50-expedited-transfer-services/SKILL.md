---
name: e50-expedited-transfer-services
description: "Determine whether the expedited transfer service of an on-board network is real, under ECSS-E-ST-50C clause 5.7.2.3, where urgent traffic has to reach its destination ahead of the ordinary queue. Compute the worst case from what an urgent message actually waits for: the non-preemptable unit already on the wire, the other expedited traffic that may queue beside it, and its own transmission. Separate a path that misses its deadline from one that never stood the ordinary backlog aside at all, and invert the model for the largest tolerable unit and the link rate a deadline needs. Use when sizing urgent on-board traffic. Trigger: ecss, e-st-50-communications, on-board-network-expedited-transfer, expedited-traffic-precedence, non-preemptable-unit-blocking, urgent-message-worst-case-latency, expedited-deadline-margin."
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
  tags: [ecss, e-st-50-communications, e50-expedited-transfer-services, on-board-network-expedited-transfer, expedited-traffic-precedence, non-preemptable-unit-blocking, urgent-message-worst-case-latency, expedited-deadline-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — On-Board Network Expedited Transfer Services (space-systems/ecss/e50-expedited-transfer-services)

Use when urgent traffic on an on-board network is being sized against its
deadline, per ECSS-E-ST-50C clause 5.7.2.3 — whether the expedited service is
a precedence the network actually grants, or only a label on a queue.

## Domain quick reference

- Two things have to hold for the service to exist in fact. Expedited
  traffic goes ahead of ordinary traffic already queued, and the wait
  that is left is bounded. A design can be labelled expedited and
  satisfy neither.
- Precedence is the one that is checked least and costs most. Without
  it the whole ordinary backlog sits in front of the urgent message,
  and the backlog is typically two orders of magnitude larger than
  anything else in the sum.
- Precedence does not mean zero wait. A transfer unit already on the
  wire cannot be taken back, so an urgent message always waits for the
  largest non-preemptable unit the link can be carrying.
- The other expedited traffic is part of the worst case too. One urgent
  message is a latency; several urgent messages that can coincide are a
  queue, and sizing on one of them understates the others.
- The worst case is therefore blocking plus interference plus own
  transmission, all over the link rate, and it inverts two ways that a
  designer can act on: the largest non-preemptable unit the deadline
  tolerates, and the link rate the deadline needs.
- A missed deadline with a tolerable unit size of zero is not a framing
  problem. It says the deadline is out of reach even with instant
  preemption, and the only axis left is rate or contention.

## Workflow

1. State the urgent message in bits, the largest non-preemptable unit
   the link can be carrying, the link rate and the deadline.
2. List the other expedited messages that can be queued at the same
   moment, in bits. An empty list is a claim that none can coincide.
3. State the ordinary backlog, and state plainly whether the network
   grants expedited traffic precedence over it.
4. Sum the bits that go out before the message is delivered. Where
   precedence is absent, the ordinary backlog joins that sum.
5. Divide by the link rate for the worst case, and report the blocking,
   interference and own-transmission parts separately so the dominant
   term is visible.
6. Compare against the deadline with a relative tolerance. A worst case
   landing exactly on the deadline must come out met on every platform.
7. Report the verdict three ways — met, missed, or no precedence at all
   — and on a miss give both inverses with their numbers.

## Pitfalls

- Accepting a priority queue as an expedited service. Precedence has to
  be granted against traffic already queued; a priority that only
  orders new arrivals leaves the backlog in front.
- Sizing on the message alone. The message is usually the smallest of
  the three terms, and a design tuned on it moves the number that does
  not matter.
- Forgetting that the blocking unit is the largest one, not the average
  one. Worst case means the unlucky moment, and the average unit never
  happens when it matters.
- Ignoring expedited traffic contending with itself. Two urgent
  messages that can coincide each wait for the other, and a per-message
  budget sized in isolation is met by neither.
- Deciding the deadline with a bare inequality. Two arithmetically
  identical budgets can straddle the bound on different machines, so
  the verdict depends on the build host.
- Reporting only the faster link. Shrinking the non-preemptable unit is
  often the cheaper fix and is the same model read the other way.

## Behavior contract (gate 3)

Size, rate, deadline and peer-list validation, the precedence switch on
the ordinary backlog, the three-term worst case, the deadline verdict
with a tolerance at the bound, the three-way verdict including a path
with no precedence, and both inverses checked against the same model
are exercised by the gate 3 contract test:
scripts/test_e50_expedited_transfer_services.py against
scripts/e50_expedited_transfer_services_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_expedited_transfer_services.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

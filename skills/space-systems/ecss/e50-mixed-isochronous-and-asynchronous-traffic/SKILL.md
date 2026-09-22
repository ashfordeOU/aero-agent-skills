---
name: e50-mixed-isochronous-and-asynchronous-traffic
description: "Allocate one space communication link between isochronous flows that must arrive on a fixed cadence and asynchronous traffic that may wait, under ECSS-E-ST-50C clause 5.6.9: the periodic flows reserve capacity, the rest carries the best-effort load, and neither is allowed to destroy the other. Compute the reservation, the jitter a non-preemptible best-effort transfer injects into the cadence, the wait a best-effort unit sees behind it, and the segment size or link rate that restores both. Use when sharing a spacecraft link between real-time and bulk traffic. Trigger: ecss, e-st-50-communications, isochronous-asynchronous-link-sharing, isochronous-cadence-jitter, asynchronous-blocking-latency, link-slot-reservation, mixed-traffic-capacity-split."
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
    clause: 5.6.9
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-mixed-isochronous-and-asynchronous-traffic, isochronous-asynchronous-link-sharing, isochronous-cadence-jitter, asynchronous-blocking-latency, link-slot-reservation, mixed-traffic-capacity-split]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Mixed Isochronous and Asynchronous Traffic (space-systems/ecss/e50-mixed-isochronous-and-asynchronous-traffic)

Use when one space communication link has to carry traffic with a cadence and
traffic without one, per ECSS-E-ST-50C clause 5.6.9 — whether the design serves
both, and what it costs when it does not.

## Domain quick reference

- The obligation is symmetric. An isochronous flow that arrives late is
  lost even though it arrived; an asynchronous flow that never gets the
  link is lost even though it was never late. Protecting one by
  sacrificing the other is not a solution, it is a choice made silently.
- The reservation is a rate, and it is computed per flow. Each periodic
  flow costs its frame size over its period, and the sum is what comes
  off the link before best-effort traffic is scheduled at all.
- Jitter comes from the transfer already on the wire. On a link that
  cannot interrupt a transfer unit, a periodic frame can be held for the
  whole unit, so the cadence spread is the serialisation time of the
  largest best-effort unit — not a property of the periodic flow.
- That gives two independent remedies and both are arithmetic:
  segment the best-effort traffic until its unit serialises inside the
  jitter budget, or make the link preemptible so the wait is zero.
- Starvation is the other failure and it hides behind a healthy cadence.
  Once the reservation is paid, the best-effort load has to fit what is
  left; a link that meets every deadline while its bulk queue grows
  without bound passes a cadence-only check.

## Workflow

1. Declare each isochronous flow by name, period and frame size. A flow
   without a period is not isochronous, and sizing it as one hides the
   cadence it actually needs.
2. Reject a duplicate flow name. Two entries under one name are two
   teams sizing the same cadence, and the reservation silently doubles.
3. Sum the periodic rates into the reservation, and report it both as a
   rate and as a share of the link.
4. Subtract the reservation from the link to get the capacity available
   to best-effort traffic, floored at zero rather than reported negative.
5. Compute the cadence jitter from the largest best-effort transfer unit
   and whether the link can interrupt it. State the preemption
   assumption explicitly; it changes the answer to zero.
6. Compare the jitter with the cadence budget and the best-effort load
   with the spare capacity, both with a relative tolerance so a design
   sized exactly to a bound comes out compliant.
7. Where either fails, report the remedy as a number: the largest unit
   the jitter budget allows, and the link rate that carries both loads.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.9a | 6 |

## Pitfalls

- Sizing the reservation from the average of the periodic traffic
  without naming the flows. The total hides which cadence is expensive
  and which one could be relaxed.
- Treating jitter as a property of the periodic flow. It is imposed by
  the transfer the link is already sending, so the fix lives in the
  best-effort segment size, not in the periodic scheduler.
- Assuming preemption. A link that must finish a transfer unit before
  it can send anything else has a floor on cadence spread that no
  priority scheme removes.
- Declaring success on cadence alone. A link that meets every deadline
  and leaves the bulk queue growing has starved half the traffic it
  was asked to carry.
- Comparing jitter with its budget by a bare inequality. Two
  arithmetically identical designs can straddle the bound on different
  machines, and the verdict then depends on the build host.

## Behavior contract (gate 3)

Flow, rate, period and size validation, duplicate flow rejection, the
reservation and spare capacity, the preemptible and non-preemptible
blocking delay, the three-way verdict with a tolerance at the jitter and
capacity bounds, and the two sizing inverses checked against the same
model are exercised by the gate 3 contract test:
scripts/test_e50_mixed_isochronous_and_asynchronous_traffic.py against
scripts/e50_mixed_isochronous_and_asynchronous_traffic_logic.py
(stdlib unittest, offline).
Run:
python3 scripts/test_e50_mixed_isochronous_and_asynchronous_traffic.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e50-directionality
description: "Verify the declared directionality of a space link under ECSS-E-ST-50C Rev.2 clause 5.6.2. Use when the task is deciding whether a link declared forward-only, return-only or bidirectional carries every direction its allocated services need, whether a bidirectional link has stated simultaneous or alternating operation, whether a two-way service that needs both directions open at once has been placed on an alternating link, and whether the turnaround and propagation terms leave the two-way response time inside its allowance. Trigger: ecss, e-st-50c, space-link-directionality, forward-link-direction, return-link-direction, bidirectional-space-link, alternating-link-turnaround, two-way-response-time, service-direction-allocation."
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
    clause: 5.6.2
    items: [a]
    relation: implements
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.2
    items: [b]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications-scope, e50-directionality, space-link-directionality, bidirectional-space-link, alternating-link-turnaround, two-way-response-time, service-direction-allocation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Space Link Directionality (space-systems/ecss/e50-directionality)

Use when the task is the directionality statement of ECSS-E-ST-50C
Rev.2 clause 5.6.2 — declaring, for each space link of the mission,
which directions it carries and whether a bidirectional link runs its
two directions at the same time or alternately, then checking that the
services allocated to the link can live inside that declaration.

## Domain quick reference

- Each direction is a simplex channel and that is where the clause
  starts. A record declared bidirectional is shorthand for a pair of
  contra-flowing channels; each of them is graded on its own, and what
  the declaration adds on top of the pair is whether the two may carry
  traffic at the same instant. Reading a two-way link as one
  undifferentiated pipe is how a return service ends up assumed onto a
  forward path.
- Directionality is a property of the link, not of the service. A link
  is declared forward-only, return-only or bidirectional, and every
  service allocated to it has to find the direction it needs already
  there. A return service on a forward-only link is a declaration
  defect: the fix is either the declaration or the allocation, never a
  silent assumption that the return path exists.
- Services divide into three groups by the directions they consume.
  Telecommand delivery, authentication and commanding-in-the-blind are
  forward. Telemetry delivery, essential telemetry and
  telemetry-in-the-blind are return. Anything that closes a loop —
  two-way ranging, Doppler tracking, an isochronous relay, an
  acknowledged or retransmitting transfer — consumes both.
- A bidirectional declaration is incomplete until it says whether the
  two directions are simultaneous or alternating. The two are not
  interchangeable: an alternating link reuses one medium, so a
  measurement that needs both directions open at the same instant
  cannot be hosted on it at any turnaround speed.
- Turnaround is a timing cost, not a capability. The two-way response
  time of a simultaneous link is the round-trip propagation time; on an
  alternating link the responder pays a turnaround on each direction
  change and may also wait for its slot, so two turnarounds and the
  slot wait sit on top of the round trip.
- A direction declared but never used is worth reporting. It is
  normally a leftover allocation or a missing service, and it carries
  link resources — frequency, power, ground-station time — that the
  mission is paying for.

## Workflow

1. Enter every space link of the mission and grade each direction it
   carries as a simplex channel in its own right: a link declared
   bidirectional is a contra-flowing pair, and each side of that pair
   answers for the services put on it on its own, with the declaration
   saying on top of the pair whether the two sides may run at the same
   instant. A link may address one peer or several. Then validate
   each record: identifier, directionality, simultaneity statement,
   allocated services, propagation, turnaround and slot-wait times. An
   unknown directionality, an unknown service, a repeated service or a
   negative time is an input error, not a case to clamp.
2. Derive the directions the allocated services need and compare them
   with the directions the declaration carries. Name every service that
   needs a direction the link does not have.
3. Report any declared direction that no allocated service uses.
4. Check the simultaneity statement itself: a bidirectional link owes
   one, and a one-way link that carries one has been mis-declared.
5. Pick out the services that need both directions open at the same
   instant and refuse them on an alternating link.
6. Where a service keeps its data intact by answering on the link that
   flows the other way — a retransmission request, an acknowledgement —
   confirm that contra-flowing link is declared and that both ends
   carry its return traffic. The mechanism is owed support; it is not
   assumed into existence by the service that relies on it.
7. Compute the two-way response time — round trip alone when
   simultaneous, round trip plus two turnarounds plus the slot wait
   when alternating — and compare it with the allowance the services
   carry, absorbing representation error at the boundary with a named
   tolerance rather than by relaxing the allowance.
8. Aggregate across the link set: which links are bidirectional, which
   are one-way, and which carry findings.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.2a | 1 |
| ECSS-E-ST-50C Rev.2 5.6.2b | 6 |

## Pitfalls

- Reading a bidirectional declaration as permission for a simultaneous
  service. Alternating operation is bidirectional too, and the two-way
  measurements are exactly the services it cannot host.
- Costing an alternating link at the round-trip propagation time. The
  turnarounds are paid twice per exchange and the slot wait once, and
  on a short-propagation link they dominate the response time.
- Treating an unused declared direction as harmless. It is either a
  service that was never allocated or a resource the mission is buying
  and not using; both are worth surfacing before the design freezes.
- Fixing an unsupported service by widening the directionality on
  paper. The declaration has to follow the link that will actually be
  flown, so the allocation is what moves unless the link really is
  bidirectional.
- Relaxing the response-time allowance so an exact-equality case
  passes. The equality is a representation question, handled by the
  tolerance inside the comparison; the allowance stays as specified.

## Behavior contract (gate 3)

The link validation, direction derivation, unsupported-service and
idle-direction detection, simultaneity-declaration checks,
alternating-link response-time computation and allowance comparison are
exercised by the gate 3 contract test:
scripts/test_e50_directionality.py against
scripts/e50_directionality_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e50_directionality.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

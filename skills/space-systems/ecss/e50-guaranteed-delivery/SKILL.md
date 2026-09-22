---
name: e50-guaranteed-delivery
description: "Verify the guaranteed delivery service of a space data transfer protocol under ECSS-E-ST-50C clause 5.6.14.2, whose single normative item obliges the space link to carry every data unit handed to the service through to the far end and to keep the sending order, with no allowance for one that does not arrive. Replay a delivery trace and separate the losses from the duplicates from the reorderings, compound the per-attempt loss over the retransmissions to get the residual, derive the attempts a residual target needs, and report a service that drops units at all — silently or otherwise. Use when specifying or auditing an acknowledged transfer service. Trigger: ecss, e-st-50-communications, guaranteed-delivery-service, exactly-once-data-unit-delivery, in-order-delivery-verification, residual-loss-after-retransmission, delivery-failure-notification-to-sender."
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
    clause: 5.6.14.2
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-guaranteed-delivery, guaranteed-delivery-service, exactly-once-data-unit-delivery, in-order-delivery-verification, residual-loss-after-retransmission, delivery-failure-notification-to-sender]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Guaranteed Delivery (space-systems/ecss/e50-guaranteed-delivery)

Use when a space data transfer service claims to deliver everything handed
to it, per ECSS-E-ST-50C clause 5.6.14.2 — what a recorded delivery actually
shows, how much loss survives the retransmissions, and whether the sender
learns about the units that never arrived.

## Domain quick reference

- The item has two parts and no get-out. Every unit handed to the service
  arrives, and the order it was sent in survives the trip. A unit that
  never arrives fails the clause whether or not anybody was told, and a
  service that discards one after its last attempt has failed it even
  though the unit was genuinely undeliverable.
- The note beside the item widens the link, not the guarantee. The same
  link may carry lesser grades that promise neither arrival nor order;
  that is permission to offer them alongside, never permission for the
  guaranteed service to behave like one.
- Duplicate suppression is this leaf's addition, not the clause's. The
  item speaks to arrival and order and is silent on a unit that turns up
  twice, so exactly-once is something a project asks for; the check earns
  its place because a repeated telecommand is not a harmless
  retransmission at the application layer, and a service that cannot
  suppress the duplicate has pushed that problem to the payload.
- Out of order is not lost. A trace scan that reports a unit missing the
  moment a later one arrives produces a loss report full of units that
  turned up a moment afterwards, and the retransmissions it triggers make
  the delay worse.
- Residual loss compounds by multiplication over the attempts. Repeated
  multiplication is the honest way to compute it and to search for the
  attempt count a target needs, because it asks the same arithmetic
  question the same way each time.
- A per-unit residual is not a mission figure until the unit count is in.
  One unit in a million looks fine until the pass carries ten million
  units, and the conversation changes at that point.
- Notification is project practice layered on top, not relief from the
  item. Telling the sender a unit never made it is the least a service
  owes its user once it has failed, and giving up in silence is worse
  again — but the verdict against the clause was already settled by the
  unit that did not arrive, and no message afterwards reverses it.

## Workflow

1. State the transfer as the identifiers handed to the service, the
   identifiers delivered in the order they arrived, and whether the sender
   was notified of any failure.
2. Replay the delivery and separate three things: units never delivered,
   units delivered more than once, and units delivered out of the order
   they were sent.
3. Report every undelivered unit as a failure against the item, then read
   the notification flag beside it as a separate, project-level judgement
   on how the service behaved once it had failed: notified is bounded,
   silent is broken, and neither is the guarantee the clause asks for.
4. Compound the per-attempt loss probability over the attempts allowed to
   get the residual loss, using repeated multiplication rather than a
   power.
5. Compare the residual with the target using a relative tolerance, so a
   design landing exactly on the target is compliant on every build host.
6. Where the residual misses, report the attempt count that reaches it,
   found by multiplying attempt by attempt, and say plainly when no count
   does.
7. Scale the residual by the units in the transfer so the figure quoted is
   the one the mission will actually see.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.14.2a | 2 |

## Pitfalls

- Reading an out-of-order arrival as a loss. The unit is in flight, the
  retransmission it triggers is waste, and on a long round trip the
  retransmissions outnumber the real losses.
- Accepting duplicates as harmless. Exactly-once is a project addition
  rather than a clause obligation, but where a project has asked for it, a
  duplicated command is a different event at the application layer from a
  duplicated telemetry frame.
- Reading a notification as compliance. A service that gives up and says
  so has behaved better than one that gives up in silence and worse than
  one that delivered; the item is discharged by arrival and order, not by
  the quality of the apology.
- Quoting the per-unit residual as the mission figure. Multiply by the
  units in the transfer before the number is used in a risk argument.
- Raising the per-attempt loss to a power and comparing at the target.
  Repeated multiplication answers the same question without leaning on a
  power function whose last bit differs between platforms.

## Behavior contract (gate 3)

Trace validation, the loss, duplicate and reordering separation, the
notification reporting, the compounded residual, the attempt count that
reaches a target, acceptance exactly at the target and the per-transfer
scaling are exercised by the gate 3 contract test:
scripts/test_e50_guaranteed_delivery.py against
scripts/e50_guaranteed_delivery_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_guaranteed_delivery.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e50-guaranteed-delivery
description: "Verify the guaranteed delivery service of a space data transfer protocol under ECSS-E-ST-50C clause 5.6.14.2, whose single normative item asks that each data unit handed to the service reach the far end once, in the order it was sent, or that the sender be told it did not. Replay a delivery trace and separate the losses from the duplicates from the reorderings, compound the per-attempt loss over the retransmissions to get the residual, derive the attempts a residual target needs, and report a service that drops units silently. Use when specifying or auditing an acknowledged transfer service. Trigger: ecss, e-st-50-communications, guaranteed-delivery-service, exactly-once-data-unit-delivery, in-order-delivery-verification, residual-loss-after-retransmission, delivery-failure-notification-to-sender."
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

- The guarantee has three parts and a get-out. Once, in order, and not at
  all if the sender is told. A service that quietly discards a unit after
  its last attempt has broken the guarantee even though the unit was
  genuinely undeliverable.
- Duplicates break the guarantee as clearly as losses. A repeated
  telecommand is not a harmless retransmission at the application layer,
  and a service that cannot suppress the duplicate has pushed that problem
  to the payload.
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
- Notification is what makes a bounded service honest. A guarantee that
  cannot always be kept is acceptable; a guarantee that fails without
  saying so is what the clause is written against.

## Workflow

1. State the transfer as the identifiers handed to the service, the
   identifiers delivered in the order they arrived, and whether the sender
   was notified of any failure.
2. Replay the delivery and separate three things: units never delivered,
   units delivered more than once, and units delivered out of the order
   they were sent.
3. Report the undelivered units against the notification flag. Undelivered
   and notified is a bounded service; undelivered and silent is a broken
   guarantee.
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

## Pitfalls

- Reading an out-of-order arrival as a loss. The unit is in flight, the
  retransmission it triggers is waste, and on a long round trip the
  retransmissions outnumber the real losses.
- Accepting duplicates as harmless. Exactly once is part of the guarantee,
  and a duplicated command is a different event at the application layer
  from a duplicated telemetry frame.
- Treating a bounded retry count as a broken guarantee by itself. A
  service that gives up and says so has behaved correctly; the defect is
  giving up in silence.
- Quoting the per-unit residual as the mission figure. Multiply by the
  units in the transfer before the number is used in a risk argument.
- Raising the per-attempt loss to a power and comparing at the target.
  Repeated multiplication answers the same question without leaning on a
  power function whose last bit differs between platforms.

## Behavior contract (gate 3)

Trace validation, the loss, duplicate and reordering separation, the
notification obligation, the compounded residual, the attempt count that
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

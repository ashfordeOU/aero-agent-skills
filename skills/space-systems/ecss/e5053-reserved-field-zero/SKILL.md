---
name: e5053-reserved-field-zero
description: "Assess the reserved field that follows the protocol identifier in a SpaceWire CCSDS packet transfer under ECSS-E-ST-50-53C clause 5.5.4.2, keeping its two obligations on the parties they belong to: the sender writes zero and has no discretion, while the receiver ignores whatever the field holds and must not refuse delivery over it. Audit a run of received transfers for non-conformant senders without turning any of them into discards, and flag a receive path configured to reject on the field as the defect it is. Use when encoding or auditing SpaceWire transfer headers. Trigger: ecss, e-st-50-53c, spacewire-reserved-field, reserved-field-zero-fill, receiver-ignores-reserved-field, ccsds-transfer-encoding, sender-conformance-audit, forward-compatibility-reserved-bits."
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
  tags: [ecss, e-st-50-53-ccsds-packet-transfer, e5053-reserved-field-zero, spacewire-reserved-field, reserved-field-zero-fill, receiver-ignores-reserved-field, sender-conformance-audit, forward-compatibility-reserved-bits]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Reserved Field (space-systems/ecss/e5053-reserved-field-zero)

Use when the task is the reserved field of a SpaceWire packet carrying
the CCSDS packet transfer protocol, per ECSS-E-ST-50-53C clause 5.5.4.2
— what a sender puts in it, what a receiver does about what it finds
there, and why those are not the same rule.

## Domain quick reference

- The reserved field sits between the protocol identifier and the CCSDS
  Packet field. It carries nothing today; it exists so a later revision
  of the protocol has a defined place to put something without moving
  every field after it.
- Clause 5.5.4.2 carries two obligations on two different parties. The
  sender writes zero. The receiver ignores the contents. Both are
  needed, and each is useless without the other.
- The sender's obligation is what keeps the field usable later. If
  senders fill it with anything convenient, a future revision that
  assigns meaning to those bits finds a population of existing
  equipment already emitting noise into them, and the extension point
  is spent.
- The receiver's obligation is what makes deployment survivable. A
  receiver that refuses transfers over a non-zero reserved field is
  intolerant of exactly the senders it is required to interoperate
  with, and it will also reject conformant traffic from a later
  revision that does use the field.
- The consequence of that split is that one octet value produces two
  different verdicts depending on which side is asking. A non-zero
  value is a defect in the sender's build and an observation in the
  receiver's log, never a discard.

## Workflow

1. On the sending side, emit the field as zero of the declared width.
   There is no configuration and no parameter; the encoder returns a
   constant because the standard leaves nothing to decide.
2. Validate any observed field value as an octet before judging it. A
   value outside the octet range is a decoder defect upstream, not a
   non-conformant sender.
3. Judge the value against the role of the party asking. For a sender,
   anything other than zero is a finding naming both what was written
   and what is required.
4. For a receiver, return delivery in every case, and record a non-zero
   value as an observation about the sender's conformance rather than
   as a compliance failure of the receiving entity.
5. Across a run of received transfers, count the non-conformant ones
   and list the distinct non-zero values seen — repeated values point
   at one bad build, scattered values at uninitialised memory.
6. Where the receive path is configured to reject on this field, report
   that configuration itself as a finding, because refusing delivery
   over reserved contents is the receiving-side obligation inverted.

## Pitfalls

- Enforcing the sender's rule inside the receiver. It looks like strict
  compliance and is the opposite: the receiver has its own obligation,
  and it is to ignore the field.
- Using the field as spare space for a local extension. It is
  indistinguishable from a bad sender to everyone else on the link, and
  it is the first thing a future revision of the protocol will collide
  with.
- Recording a non-zero field and taking no further action. It is not a
  reason to discard, but it does identify a non-conformant sender, and
  an observation nobody counts is an observation nobody fixes.
- Assuming a non-zero value means data. Uninitialised buffer contents
  land in this field routinely, which is why the distinct values seen
  across a run are worth reporting — one repeated value is a build, a
  scatter is memory.
- Testing the field before knowing how the node was addressed. The
  reserved octet is located by counting past the address octets and the
  protocol identifier, and a path-addressed transfer arrives with its
  address octets already consumed.

## Behavior contract (gate 3)

The zero-fill encoder, octet validation, role-dependent verdicts, the
receiver's unconditional delivery and the sender-conformance audit are
exercised by the gate 3 contract test:
scripts/test_e5053_reserved_field_zero.py against
scripts/e5053_reserved_field_zero_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e5053_reserved_field_zero.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

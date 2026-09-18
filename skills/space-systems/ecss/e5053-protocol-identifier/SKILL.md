---
name: e5053-protocol-identifier
description: "Validate the protocol identifier field of a SpaceWire packet carrying the CCSDS packet transfer protocol under ECSS-E-ST-50-53C clause 5.5.4.1: confirm a sender wrote the assigned value and nothing else, and on the receiving side separate a transfer belonging to another protocol on the shared link, a zero announcing an extended identifier with further octets to read, and a value held back from assignment, so demultiplexing never reports other traffic as a fault. Use when encoding, demultiplexing or fault-finding SpaceWire protocol identifiers. Trigger: ecss, e-st-50-53c, spacewire-protocol-identifier, spacewire-protocol-demultiplex, extended-protocol-identifier, reserved-protocol-identifier, shared-spacewire-link, ccsds-transfer-encoding."
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
  tags: [ecss, e-st-50-53-ccsds-packet-transfer, e5053-protocol-identifier, spacewire-protocol-identifier, spacewire-protocol-demultiplex, extended-protocol-identifier, reserved-protocol-identifier, shared-spacewire-link]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Protocol Identifier (space-systems/ecss/e5053-protocol-identifier)

Use when the task is the protocol identifier field of a SpaceWire packet
carrying the CCSDS packet transfer protocol, per ECSS-E-ST-50-53C clause
5.5.4.1 — writing it on the sending side, and deciding what a received
value means on a link several protocols share.

## Domain quick reference

- The identifier sits immediately after the address octets and before
  the reserved octet. It is the only thing telling a receiving node
  which entity the rest of the transfer belongs to, so it is read
  before any payload field and cannot be inferred from the payload.
- One value is assigned to this protocol. Clause 5.5.4.1 gives the
  sender a single legal choice, which makes the sending-side check an
  equality and not a range test.
- The receiving side is a different question with a different answer
  set. A value assigned to another protocol is ordinary traffic on a
  shared link, not an error, and a receive path that reports it as one
  will bury real faults under routine noise.
- Zero is not a protocol; it announces that the real identifier is
  carried in the octets that follow. A receiver seeing it has to read
  further before it can decide anything, which is a third outcome
  distinct from both "mine" and "somebody else's".
- A band of values is held back from assignment. Seeing one is a
  genuine finding, because no entity owns it and the transfer therefore
  has no destination, which is exactly the case an "is it mine?" test
  collapses into a silent no.

## Workflow

1. Validate the field as a single octet; anything outside 0..255, or
   not an integer, is a decoding defect rather than an unknown protocol.
2. Categorize the value into one of the outcomes that matter: assigned
   to this protocol, extended identifier announced, assigned to another
   protocol, held back from assignment, or simply unassigned.
3. On the sending side, require the assigned value exactly. Report any
   other value as a sender defect naming both what was written and what
   this protocol carries.
4. On the receiving side, answer two questions separately: is this
   transfer mine, and is anything wrong. Another protocol's identifier
   answers no to the first and no to the second.
5. Where an extended identifier is announced, report how many further
   octets must be read before the demultiplexing decision can be made
   at all.
6. Return the category with the verdict, so a caller can route, park or
   raise on the same result without re-deriving the reasoning.

## Pitfalls

- Testing the received identifier for equality with the assigned value
  and treating every inequality as an error. That is the sending-side
  rule applied to the receiving side, and on a shared link it reports
  every other protocol as a fault.
- Reading zero as an unassigned or malformed value. It is a marker with
  a defined continuation, and a receiver that discards on it drops
  traffic that was correctly formed.
- Letting a held-back value pass as "not mine". No entity owns it, so
  nobody will report it, and a transfer that silently belongs to nobody
  is the hardest kind of fault to find later.
- Inferring the protocol from the shape of the payload when the
  identifier is unexpected. The identifier is the demultiplexer; a
  payload that looks like a space packet under another identifier is
  not this protocol's traffic.
- Placing the identifier by counting from the start of the transfer
  without knowing how the node was addressed. A path-addressed transfer
  arrives with its address octets already consumed, and counting from
  the wrong origin reads a payload octet as the identifier.

## Behavior contract (gate 3)

The octet validation, value categorization, sending-side equality rule,
receiving-side demultiplexing and extended-identifier continuation are
exercised by the gate 3 contract test:
scripts/test_e5053_protocol_identifier.py against
scripts/e5053_protocol_identifier_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e5053_protocol_identifier.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

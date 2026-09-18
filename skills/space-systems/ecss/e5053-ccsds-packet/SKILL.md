---
name: e5053-ccsds-packet
description: "Validate the CCSDS packet a SpaceWire transfer protocol carries and size the frame around it. Use when an ECSS-E-ST-50-53C clause 5.1.1 packet is built or read back: normalise the six primary-header fields, pack them into header bytes and unpack a capture back into the same record, turn the data-field size into the length field and back, size the packet and the frame that adds routing and the protocol byte, split a user datum too large for one data field into a grouped sequence, and check the counter advanced. Flags fill traffic carrying a grouped sequence or a secondary header, and a frame over the profile maximum. Trigger: ecss, e-st-50-53c, ccsds-space-packet-header, ccsds-packet-length-field, ccsds-grouping-flags, ccsds-sequence-counter-continuity, spacewire-protocol-identifier-byte, ccsds-idle-application-identifier."
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
  tags: [ecss, e-st-50-53-ccsds-packet-transfer-scope, e5053-ccsds-packet, ccsds-space-packet-header, ccsds-packet-length-field, ccsds-grouping-flags, ccsds-sequence-counter-continuity, spacewire-protocol-identifier-byte]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire — CCSDS Packet Transfer (space-systems/ecss/e5053-ccsds-packet)

Use when the task is the packet of ECSS-E-ST-50-53C clause 5.1.1 — the
space packet this transfer protocol carries across a SpaceWire link, and
whether a constructed or captured one has fields, lengths and a frame
that agree with each other.

## Domain quick reference

- The packet is a six-byte primary header followed by a data field. Six
  fields live in that header: version, direction, a secondary-header
  flag, the application process identifier, the grouping flags and the
  sequence counter, plus the length of the data field.
- The length field is off by one on purpose. It counts one less than the
  data field, which is why an empty data field cannot be expressed at
  all and why the largest is exactly sixty-four kilobytes. Reading it as
  a plain byte count is the most common capture-analysis error there is.
- The transfer protocol does not change the packet. It wraps it: routing
  bytes at the front, then one byte that names which protocol the rest
  of the frame belongs to, then the packet unchanged. A frame budget
  therefore has three parts, not one.
- Grouping flags describe a sequence, not a packet. A datum that fits in
  one data field is unsegmented; one that does not becomes a first part,
  any number of continuation parts and a last part, and the receiver
  reassembles on that pattern alone.
- The sequence counter is per application identifier and it wraps. A
  gap in it is the evidence that a packet was lost, so a receiver that
  does not track it cannot tell a dropped packet from a quiet source.
- Fill traffic is carried on its own application identifier. It exists
  to keep a channel busy, so it is unsegmented and has nothing that a
  secondary header would describe.

## Workflow

1. Normalise the field record and refuse the inputs that are errors: a
   version this protocol does not carry, an identifier past its field, a
   grouping value past its two bits, a counter past its fourteen, a data
   field that is empty or larger than the length field can express.
2. Pack the three header words in their bit positions, and confirm a
   captured header unpacks back to the same record — including being
   rejected when the captured version is not the one carried here.
3. Convert between the data-field size and the length field in both
   directions rather than writing the off-by-one at each call site.
4. Size the packet as header plus data field, and the frame as routing
   bytes plus the protocol byte plus the packet.
5. Split a user datum against the largest data field the profile allows,
   assigning first, continuation and last flags, and confirm the parts
   sum back to the datum.
6. Grade the packet: fill traffic that is grouped or declares a
   secondary header, a frame past the declared maximum, and a counter
   that did not advance by one from the previous packet on that
   identifier.

## Pitfalls

- Reading the length field as the data-field size. Every derived figure
  is then one byte short, and a reassembly that trusts it drops the last
  byte of every part.
- Budgeting a link from packet sizes alone. The routing bytes and the
  protocol byte are on the wire too, and with short packets they are a
  noticeable share of it.
- Treating the grouping flags as a per-packet attribute. They only mean
  anything as a sequence; a lone continuation part with no first part
  before it is a reassembly failure, not a standalone packet.
- Tracking one sequence counter for the whole link. The counter belongs
  to the application identifier, and a shared counter reports gaps that
  are only interleaving.
- Filling a channel with idle packets that carry a secondary header or a
  grouping flag. Fill traffic that looks like real traffic will be
  reassembled as real traffic somewhere downstream.

## Behavior contract (gate 3)

The field validation, primary-header packing and unpacking, length-field
conversion, packet and frame sizing, user-datum grouping, sequence-
counter continuity and the fill-traffic and frame-maximum grading are
exercised by the gate 3 contract test:
scripts/test_e5053_ccsds_packet.py against
scripts/e5053_ccsds_packet_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5053_ccsds_packet.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

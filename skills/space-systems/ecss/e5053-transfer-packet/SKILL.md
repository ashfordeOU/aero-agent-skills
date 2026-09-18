---
name: e5053-transfer-packet
description: "Implement the receiving side of the SpaceWire CCSDS packet transfer protocol at ECSS-E-ST-50-53C clause 5.5.3: refuse an abnormally terminated transfer before parsing it, strip the leading logical address when the node was addressed logically, read the protocol identifier and reserved octet, then hand exactly one whole CCSDS packet up to the user unchanged, while a transfer under another protocol identifier is passed to its own entity rather than discarded as an error. Use when writing or reviewing a SpaceWire receive path that delivers CCSDS packets. Trigger: ecss, e-st-50-53c, spacewire-transfer-indication, ccsds-packet-delivery, spacewire-protocol-demultiplex, spacewire-receive-path, logical-address-stripping, fragment-discard-rule."
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
  tags: [ecss, e-st-50-53-ccsds-packet-transfer, e5053-transfer-packet, spacewire-transfer-indication, ccsds-packet-delivery, spacewire-protocol-demultiplex, spacewire-receive-path, logical-address-stripping]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Transfer Packet (space-systems/ecss/e5053-transfer-packet)

Use when the task is the receiving side of the SpaceWire CCSDS packet
transfer protocol, per ECSS-E-ST-50-53C clause 5.5.3 — deciding whether
a received transfer produces a packet for the user, belongs to somebody
else, or dies where it is.

## Domain quick reference

- What arrives at the destination node is not what left the sender. A
  path-addressed transfer has had its address octets consumed one per
  hop by the routers, so the body starts at the protocol identifier; a
  logically addressed transfer still carries its address octet. The
  receive path has to know which case it is in before it reads a field.
- The terminator is checked first. A transfer the link abandoned holds
  a fragment whose header may parse perfectly, so parsing before
  checking the terminator is how fragments get delivered.
- The protocol identifier is a demultiplexer, not a validity check. An
  identifier belonging to another protocol means the transfer is not
  this entity's to deliver — it is handed on. Treating it as an error
  turns a correctly shared link into a fault report.
- The zero identifier is a special case within that: it announces an
  extended identifier carried in the octets after it, so it is never
  this protocol and never a malformed value either.
- What reaches the user is the CCSDS packet exactly as it was
  submitted. The entity adds nothing and removes nothing from it, which
  is what allows end-to-end checks applied by the sending application
  to still hold at the receiving one.

## Workflow

1. Take the transfer as the destination node sees it, together with the
   terminator the link reported and whether the node was addressed
   logically or by path.
2. Reject any transfer not terminated normally, with a reason naming
   the terminator rather than the content, and stop — no field of an
   abandoned transfer is trustworthy.
3. Strip the leading logical address octet when the node was addressed
   logically; leave a path-addressed body alone.
4. Read the protocol identifier and the reserved octet. A body too
   short to hold both is a framing defect and is discarded.
5. Where the identifier is not the one assigned to this protocol,
   return a not-this-protocol disposition with no finding raised: the
   transfer is somebody else's traffic, including the extended
   identifier case.
6. Assess the remaining octets as a CCSDS Packet field — declared
   length against octets present — and deliver the packet unchanged
   only when it is exactly one whole packet. Note a non-zero reserved
   octet as an observation, since the receiver ignores its contents
   rather than refusing delivery over it.

## Pitfalls

- Reading fields before the terminator. An abandoned transfer often
  carries a well-formed header, and the length arithmetic can agree by
  chance, so content checks do not catch what the terminator already
  told you.
- Assuming a leading address octet is always present. Path-addressed
  traffic arrives with none, and stripping an octet that is not there
  shifts every field by one and turns a good transfer into a protocol
  identifier of two.
- Discarding a transfer carrying another protocol identifier. A
  SpaceWire link is shared, and other protocols on it are normal
  traffic; the identifier selects the entity, it does not grade the
  packet.
- Refusing delivery because the reserved octet was not zero. The
  sender's obligation to zero it does not make the receiver's delivery
  conditional on it; the contents are ignored and the observation is
  recorded.
- Handing the user a repaired packet — repadded, realigned, or with its
  length field corrected. A packet that arrives different from the one
  submitted defeats every end-to-end check the application applied to
  it.

## Behavior contract (gate 3)

The terminator gate, address stripping, protocol demultiplexing, packet
field wholeness check and delivery decision are exercised by the gate 3
contract test: scripts/test_e5053_transfer_packet.py against
scripts/e5053_transfer_packet_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5053_transfer_packet.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

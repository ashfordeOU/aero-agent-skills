---
name: e5053-packet-field
description: "Validate the packet field that closes a packet transfer protocol data unit. Use when an ECSS-E-ST-50-53C clause 5.3.6 unit has to be checked against the packet it claims to carry: fix the field offset from the path length, read the six-octet primary header, take the declared total length from the header's own length count rather than from the transfer protocol, and compare it with the octets actually present. Report a complete packet, a truncation with its shortfall, an overrun with the trailing octets that belong to no packet, or a field beyond the link limit, then separate the single packet from anything following it. Trigger: ecss, e-st-50-53c, spacewire-packet-field, space-packet-primary-header, packet-field-truncation, packet-field-overrun, self-delimiting-packet-length."
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
  tags: [ecss, e-st-50-53-packet-transfer-scope, e5053-packet-field, spacewire-packet-field, space-packet-primary-header, packet-field-truncation, packet-field-overrun, self-delimiting-packet-length, packet-field-link-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Transfer — Packet Field (space-systems/ecss/e5053-packet-field)

Use when the task is the packet field of ECSS-E-ST-50-53C clause 5.3.6
-- the payload of the transfer, what it is allowed to hold, and how a
receiver decides whether what arrived is the whole of it.

## Domain quick reference

- The packet field is the last field of the unit. Nothing follows it, so
  the link's own end marker terminates it and the transfer protocol
  never writes a length of its own.
- The field carries one complete packet. Not a fragment awaiting a
  continuation, and not two packets concatenated to fill a unit, because
  neither can be recovered from a field that carries no count.
- The packet delimits itself. Its six-octet primary header ends with a
  length count of the data octets that follow, recorded one less than
  their number, so the declared total is the header plus that count plus
  one.
- The length comes from the packet, never from the field. A receiver
  that takes the arriving octet count as the packet length cannot tell a
  complete packet from a truncated one, because both fill the field
  exactly as far as they go.
- A field shorter than the header declares is a truncation, and the
  shortfall is the useful number: it says how much was lost, not merely
  that something was.
- A field longer than the header declares has trailing octets belonging
  to no packet. They are a second packet, a padding habit or a framing
  fault, and all three are reported the same way and not silently
  dropped.
- A field too short to hold even the primary header is a truncation of a
  different kind: the declared length cannot be read at all, so nothing
  about the packet can be reported.

## Workflow

1. Fix where the packet field begins from the number of path-address
   bytes, refusing a negative or non-integer path length.
2. Check the unit extends past that offset, and take everything from it
   to the end of the unit as the field.
3. Refuse a field too short to hold the six-octet primary header, and
   report that the declared length could not be read rather than
   guessing one.
4. Decode the header: the process identifier, the sequence flags and
   count, and the length count that makes the packet self-delimiting.
5. Compute the declared total from the header alone and compare it with
   the octets present: equal is complete, fewer is a truncation with a
   shortfall, more is an overrun with trailing octets.
6. Apply the link's maximum field size where one is stated, and report a
   field beyond it even when the packet inside is well formed.
7. Separate the single declared packet from anything that follows, and
   refuse to do so on a truncated field, which holds no complete packet.

## Pitfalls

- Taking the arriving octet count as the packet length. It agrees with
  the declared length exactly when nothing went wrong, so the check
  passes on every complete packet and on every truncated one too.
- Forgetting the bias in the length count. It records one less than the
  data octets, so reading it directly makes every packet one octet
  shorter than it is and every comparison off by one.
- Packing two packets into one field. There is no count to separate
  them, so the receiver delivers the first and the second becomes
  trailing octets that belong to nobody.
- Dropping trailing octets quietly. They are evidence of a framing
  fault or a sender that concatenates, and discarding them without a
  finding removes the only symptom.
- Reading the field at a fixed offset. Path-address bytes move it, so a
  hard-coded start reads the user application octet as the first header
  octet and decodes a plausible, wrong packet.

## Behavior contract (gate 3)

The offset computation, primary header decoding and encoding, declared
length derivation, truncation and overrun verdicts, link-limit check and
packet separation are exercised by the gate 3 contract test:
scripts/test_e5053_packet_field.py against
scripts/e5053_packet_field_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5053_packet_field.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

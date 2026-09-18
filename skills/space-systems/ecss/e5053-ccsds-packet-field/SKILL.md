---
name: e5053-ccsds-packet-field
description: "Verify that the CCSDS Packet field of a SpaceWire transfer holds exactly one whole space packet under ECSS-E-ST-50-53C clause 5.4.1.7: parse the six-octet primary header, derive the declared total length from the packet data length field, then compare it against the octets actually present so a truncated packet, a surplus tail, or a second packet stuffed into one transfer is caught before the receiver mis-frames the stream. Use when encapsulating, unpacking or debugging CCSDS packets carried over a SpaceWire link. Trigger: ecss, e-st-50-53c, spacewire-ccsds-packet-field, ccsds-space-packet-framing, packet-data-length-field, ccsds-primary-header, spacewire-data-field-occupancy, single-packet-per-transfer, truncated-space-packet."
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
  tags: [ecss, e-st-50-53-ccsds-packet-transfer, e5053-ccsds-packet-field, spacewire-ccsds-packet-field, ccsds-space-packet-framing, packet-data-length-field, ccsds-primary-header, single-packet-per-transfer]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — CCSDS Packet Field (space-systems/ecss/e5053-ccsds-packet-field)

Use when the task is the content of the CCSDS Packet field of a SpaceWire
packet carrying the CCSDS packet transfer protocol, per
ECSS-E-ST-50-53C clause 5.4.1.7 — deciding whether the field holds one
whole space packet and nothing else.

## Domain quick reference

- The encapsulating SpaceWire packet is a header of address and protocol
  octets followed by the CCSDS Packet field and the end-of-packet
  marker. The field is the payload slot, and clause 5.4.1.7 fixes what
  may sit in it: one complete space packet, not a fragment and not a
  batch.
- A space packet is self-describing. Its six-octet primary header ends
  with a 16-bit packet data length field that counts the octets of the
  data field minus one, so the declared total is six plus that field
  plus one. Nothing outside the packet needs to be consulted to know how
  long it should be.
- That makes the check arithmetic, not heuristic: declared total against
  octets present. Declared greater than present is a truncation;
  declared less than present is a surplus tail, which is usually the
  head of a second packet that the sender let run into the same
  transfer.
- Walking the field packet by packet separates those two cases. A field
  whose second span parses as a valid primary header is a batching
  defect; one whose remainder is shorter than a header is a framing
  defect. They have different senders and different fixes, so a single
  "bad length" verdict is not enough.
- The all-ones application process identifier is the idle pattern. Idle
  data reaching a user data transfer means fill has been routed as
  payload, which passes every length check and still corrupts the
  receiving application.

## Workflow

1. Validate the octet sequence: every element an integer in 0..255, and
   the field long enough to hold a primary header at all. A field
   shorter than six octets has no declared length to check against and
   is reported as such, not parsed.
2. Parse the primary header of the leading packet: version number,
   packet type, secondary header flag, application process identifier,
   sequence flags, sequence count and data length field.
3. Derive the declared total length and compare it with the octets
   present; record the surplus or the shortfall as a signed quantity so
   the report says which way the mismatch runs.
4. Walk the remainder of the field, parsing a header at each packet
   boundary, and count the spans found. More than one span is a
   batching finding; a final span shorter than a header is a fragment
   finding.
5. Assess the leading header for content defects that the length
   arithmetic cannot see: a packet version number that is not the one
   this protocol carries, and an idle application process identifier
   presented as user data.
6. Report compliant only when exactly one span was found, it is
   complete, and it ends at the last octet of the field.

## Pitfalls

- Reading the packet data length field as the total packet length. It
  counts the data field alone and is offset by one, so using it
  directly loses seven octets and turns every good packet into an
  apparent surplus-tail case.
- Accepting a field whose declared length is shorter than the octets
  present because the leading packet parsed cleanly. The leading packet
  being well-formed is exactly the condition under which a trailing
  fragment goes unnoticed; the field length must be consumed to the
  end.
- Treating a truncation and a second packet as the same defect. One is
  a link or buffer problem at the sender, the other is an encapsulation
  policy problem in the user application, and reporting both as a
  length mismatch sends the investigation to the wrong place.
- Letting idle fill through because it is structurally perfect. An idle
  application process identifier is a well-formed packet by every
  length rule and still is not user data.
- Assuming a field that is a multiple of some packet size holds one
  packet. Size coincidence is not framing; only the declared length of
  the header actually present decides where the packet ends.

## Behavior contract (gate 3)

The octet validation, primary-header parse, declared-length derivation,
field walk and occupancy verdict are exercised by the gate 3 contract
test: scripts/test_e5053_ccsds_packet_field.py against
scripts/e5053_ccsds_packet_field_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e5053_ccsds_packet_field.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

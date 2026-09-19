---
name: e7041-the-ccsds-space-packet-general
description: "Verify that the telemetry and telecommand crossing a space-to-ground interface are CCSDS space packets, under ECSS-E-ST-70-41C clause 7.4.2. Use when octets arriving on a link have to be identified before anything inside them is trusted: checking the packet version number first because a wrong one means these are not space packets at all, range-checking the application process identifier, sequence flags and sequence count, reading the data length field as one less than the data field it sizes, and reconciling the stated total with the octets present. Trigger: ecss, e-st-70-41c, ccsds-space-packet-container, six-octet-primary-header, packet-data-length-minus-one, application-process-identifier-range, packet-sequence-count-wrap, idle-apid-reserved-value."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-the-ccsds-space-packet-general, ccsds-space-packet-container, six-octet-primary-header, packet-data-length-minus-one, application-process-identifier-range, packet-sequence-count-wrap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — The CCSDS Space Packet, General (space-systems/ecss/e7041-the-ccsds-space-packet-general)

Use when the task is clause 7.4.2 of ECSS-E-ST-70-41C — the single
normative item that fixes what travels on the space-to-ground
interface, and therefore the container every other clause of the
standard is describing the contents of.

## Domain quick reference

- One sentence carries the whole interface: every telemetry report and
  every telecommand request crossing it is a CCSDS space packet.
  Nothing else is on the wire, so identifying the container correctly
  is the precondition for every service-level interpretation.
- The container is a six-octet primary header followed by a packet
  data field of at least one octet.
- The header divides into the packet version number over three bits,
  the packet type over one, the secondary header flag over one, the
  application process identifier over eleven, the sequence flags over
  two, the packet sequence count or name over fourteen, and the packet
  data length over sixteen.
- The version number is checked first and on its own. A value other
  than the supported one means these octets are not a space packet,
  and every field parsed after it is a coincidence.
- The data length field states the octet count of the data field minus
  one. The offset exists so sixteen bits can express a full
  65536-octet data field, and it is why a header-only packet has no
  representation at all: the smallest space packet is seven octets.
- The application process identifier says which on-board process the
  packet belongs to. Its all-ones value is reserved for idle packets,
  which fill a frame and carry no service.
- The sequence count is a per-process counter that wraps at its
  fourteen-bit span, so a gap is measured modulo that span and a wrap
  is not itself a gap.
- Type and direction have to agree. A telemetry-typed packet on the
  uplink is mislabelled rather than unusual, and the mislabelling
  survives every check that looks only inside the data field.

## Workflow

1. Take the six header octets as three big-endian words and split the
   fields by width before interpreting any of them.
2. Check the version number and stop there if it is not the supported
   one. Reporting a plausible application process identifier out of
   octets that are not a space packet is worse than reporting nothing.
3. Range-check each remaining field against its own width, refusing
   rather than masking; a masked value is a different packet that
   parses.
4. Convert the length field to a data-field size by adding one, and
   the whole packet size by adding the header on top.
5. Reconcile the stated total against the octets actually present. A
   disagreement is the finding that explains every downstream
   mis-parse.
6. Compare the type against the direction the packet was observed on,
   and the secondary header flag against whether the packet carries a
   service at all.
7. Where a previous count for the same application process is known,
   measure the gap modulo the counter span so a wrap reads as
   continuous and a repeat reads as a full-span jump.

## Pitfalls

- Parsing the rest of the header before the version number. Every
  field has a plausible value in arbitrary octets.
- Reading the length field as the data-field size. Everything after
  the packet is then located one octet early.
- Treating the sequence-count wrap as a gap. A long pass crosses it
  routinely and the false gaps bury the real ones.
- Masking an out-of-range field to make it fit. The packet then parses
  as a different, valid-looking one.
- Assuming the idle application process identifier is just another
  process. It carries no service, and decoding one as a service
  packet produces a report nothing generated.
- Checking the type without the direction. Both values are legal; only
  the pairing is wrong.

## Behavior contract (gate 3)

The length-field conversion in both directions, the version-first
refusal, per-field range checks, six-octet encode and decode round
trip, sequence-gap measurement across the counter wrap and the
whole-packet assessment against direction, service carriage and idle
reservation are exercised by the gate 3 contract test:
scripts/test_e7041_the_ccsds_space_packet_general.py against
scripts/e7041_the_ccsds_space_packet_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_the_ccsds_space_packet_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

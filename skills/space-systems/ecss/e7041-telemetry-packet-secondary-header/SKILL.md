---
name: e7041-telemetry-packet-secondary-header
description: "Validate the telemetry packet secondary header a PUS service builds under ECSS-E-ST-70-41C clause 7.4.3.1: resolve the mission-configured field set and widths into one contiguous octet-aligned layout, range-check the version number, the time reference status, the service type and message subtype identifiers, the destination identifier and the time field against the width each was given, pack and unpack to prove the layout carries the values, and follow the message type counter so a wrap, a repeat and a skip are told apart. Use when a ground system cannot decode a report, or when a new service header layout is being agreed. Trigger: ecss, e-st-70-41c, telemetry-packet-secondary-header, pus-version-number-field, message-type-counter-continuity, spacecraft-time-reference-status, secondary-header-octet-alignment, service-type-subtype-identifier."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-telemetry-packet-secondary-header, telemetry-packet-secondary-header, pus-version-number-field, message-type-counter-continuity, spacecraft-time-reference-status, secondary-header-octet-alignment, service-type-subtype-identifier]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Telemetry Packet Secondary Header (space-systems/ecss/e7041-telemetry-packet-secondary-header)

Use when the task is the telemetry packet secondary header of
ECSS-E-ST-70-41C clause 7.4.3.1 -- the twelve normative items that say
which fields sit between the packet primary header and the user data
field, how wide each one is, and what a receiver is entitled to assume
about the values it finds there.

## Domain quick reference

- The secondary header is what makes a telemetry packet a PUS report
  rather than an opaque frame payload. Without it the primary header
  gives an application process identifier and a length and nothing that
  says what the octets mean.
- Three fields are always there: the version number, the service type
  identifier and the message subtype identifier. Everything else --
  time reference status, message type counter, destination identifier,
  time field -- is a mission choice, and the choice is fixed for the
  mission rather than made packet by packet, because a receiver has to
  know the layout before it can read the first field.
- The service type and subtype pair is the routing key of the whole
  standard. Zero is not an allocated identifier in either, so a zero
  read out of either field means the packet was mis-framed, not that a
  service zero exists.
- Field widths are mission-configurable, and that is precisely where
  layouts go wrong. The user data field begins where the secondary
  header ends, so a field set whose widths sum to a number of bits that
  is not a multiple of eight leaves every subsequent octet offset
  ambiguous.
- The message type counter counts reports of one service type and
  subtype from one source. It is a modulo counter, so rolling over is
  normal traffic; the two events worth reporting are a repeat, which
  means a duplicated report, and a jump, which means one was lost.
  Reading a rollover as a jump manufactures a loss that did not happen.
- The time field records when the report was generated, and the time
  reference status says whether the on-board reference was synchronised
  when that stamp was taken. A stamp read without its status is a
  number of unknown provenance.

## Workflow

1. Resolve the layout: the three always-present fields, plus the
   optional fields the mission switched on, in the fixed wire order.
   Refuse an optional name that is not one, a name listed twice, and a
   width override for a field the mission left out.
2. Validate each width on its own -- positive, an integer, and inside
   the layout limit -- before summing anything.
3. Sum the layout and check octet alignment. Report a misaligned layout
   as the finding it is rather than rounding the length up.
4. Range-check every value against the width its own field was given,
   not against a nominal width, and refuse a zero service type or
   message subtype identifier.
5. Pack the values into the layout most significant field first and
   unpack them again. A round trip that does not return what went in
   means the layout and the values disagree.
6. Where a counter history is supplied, walk it as a modulo sequence:
   count the wraps, list the repeats, and size each gap by the number
   of reports it implies were lost.
7. Report the layout, its length in bits and whole octets, the
   service-subtype key, the counter assessment and every finding.

## Pitfalls

- Assuming the nominal widths. A mission that narrowed the destination
  identifier or widened the time field has a different header length,
  and a decoder built on the defaults will read every field after the
  changed one from the wrong offset.
- Rounding a misaligned layout up to the next octet. That hides the
  defect and puts the user data field one boundary away from where the
  sender put it.
- Reading a counter rollover as a lost report. The step from the top of
  the field to zero is one, and treating it as a huge negative jump
  turns ordinary traffic into a fabricated loss report.
- Treating a repeated counter value as a small gap. A repeat and a skip
  are different faults -- one duplicated a report, the other lost one
  -- and merging them into a single continuity number loses the only
  information that distinguishes them.
- Taking a generation time stamp without its reference status. The
  stamp is only as good as the synchronisation state behind it, and the
  status field exists because that state is not constant.
- Accepting a zero in the service type or subtype field as a real
  identifier. It is the signature of a mis-framed packet, and carrying
  it forward routes the report to a service that does not exist.

## Behavior contract (gate 3)

The layout resolution, width validation, octet-alignment check,
per-field range checking, pack/unpack round trip and modulo counter
continuity assessment are exercised by the gate 3 contract test:
scripts/test_e7041_telemetry_packet_secondary_header.py against
scripts/e7041_telemetry_packet_secondary_header_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_telemetry_packet_secondary_header.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

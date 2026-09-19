---
name: e7041-telemetry-user-data-field
description: "Compute the telemetry packet user data field a report subtype produces under ECSS-E-ST-70-41C clause 7.4.3.2: lay the message body parameters out in order with their bit offsets, add only the spare needed to reach the next octet boundary, append the packet error control field when the mission carries one, then derive the packet data field octets, the primary header length field that counts one less, and the whole packet size against the mission limit. Use when a report will not decode at the expected offset, or when a new report body is being sized. Trigger: ecss, e-st-70-41c, telemetry-user-data-field, message-body-parameter-layout, user-data-spare-alignment, packet-error-control-field, packet-data-length-field, report-packet-size-budget."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-telemetry-user-data-field, telemetry-user-data-field, message-body-parameter-layout, user-data-spare-alignment, packet-error-control-field, packet-data-length-field, report-packet-size-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Telemetry Packet User Data Field (space-systems/ecss/e7041-telemetry-user-data-field)

Use when the task is the telemetry packet user data field of
ECSS-E-ST-70-41C clause 7.4.3.2 -- the six normative items that say
what follows the secondary header, in what order, and how the packet
length a receiver reads relates to what the service actually put in.

## Domain quick reference

- The user data field holds three things in a fixed order: the message
  body of the report subtype, any spare needed to reach an octet
  boundary, and the packet error control field when the mission carries
  one. Nothing is inserted between them, so every offset in the body is
  computable from the body definition alone.
- The message body is defined per service type and subtype. Two reports
  of the same subtype have the same parameter set in the same order,
  which is what lets a ground system decode a report it has never seen
  an instance of.
- Spare exists for alignment and nothing else. It is therefore never a
  whole octet wide -- a body already on a boundary gets none, and a
  body seven bits past one gets one bit. Spare used as reserved space
  for a future parameter is a body definition change in disguise.
- The packet error control field, where a mission carries one, is
  always last, so it can cover everything before it. Its width is a
  mission constant, not a per-report choice.
- The packet data field is the secondary header plus the user data
  field. The length field in the primary header counts the octets of
  that data field less one, so a data field of one octet is expressed
  as zero and an empty data field cannot be expressed at all.
- Report size is a budget, not a formality. A body that grows past the
  packet limit does not truncate cleanly; it forces the service to
  split the report or the mission to raise the limit, and both are
  design decisions rather than encoder details.

## Workflow

1. Resolve the message body of the subtype into an ordered parameter
   list. Refuse a repeated parameter name, a blank name and a
   zero-width parameter, because each one silently changes the offsets
   of everything after it.
2. Give each parameter its bit offset, its octet and its bit within
   that octet, and note the ones that do not start on a boundary, so a
   decoder author knows where shifting is required.
3. Sum the body and compute the spare needed to reach the next octet
   boundary. Zero to seven bits is the only correct answer.
4. Append the error control field at its mission width when one is
   carried, and refuse an error control width supplied for a mission
   that has none.
5. Convert the user data field to whole octets, add the secondary
   header to get the packet data field, and derive the primary header
   length field as one less than that.
6. Add the primary header for the whole packet size and compare the
   data field against the mission limit.
7. Report every length, the parameters that straddle an octet, and each
   finding: an empty body, the spare that had to be added, an oversize
   packet.

## Pitfalls

- Padding the body to an octet with a whole spare octet. Spare is
  alignment only, and a full octet of it means the body definition is
  being extended rather than aligned.
- Putting the error control field before the spare. It then covers a
  different span than the receiver checks, and the check fails on
  correctly formed packets.
- Reading the length field as the packet data field size. It is one
  less, and off-by-one here shifts every packet boundary in a stream.
- Adding the primary header into the length field. The field counts the
  data field only; including the six header octets makes every packet
  read as longer than it is.
- Assuming an aligned body because every parameter looks like a whole
  number of octets. A single flag parameter early in the body puts
  every later parameter off the boundary, which is a decode cost even
  when the total still aligns.
- Truncating a body that outgrew the packet limit. The report then
  decodes as a shorter valid packet and the loss is invisible; the size
  finding has to reach the service designer.

## Behavior contract (gate 3)

The body layout resolution, parameter offsets, alignment spare, error
control placement, packet data field and length field derivation, and
the packet size limit check are exercised by the gate 3 contract test:
scripts/test_e7041_telemetry_user_data_field.py against
scripts/e7041_telemetry_user_data_field_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_telemetry_user_data_field.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e5053-eop-character
description: "Evaluate the end-of-packet marker that terminates a SpaceWire transfer carrying a CCSDS packet under ECSS-E-ST-50-53C clause 5.4.1.8: separate a normal terminator from an error terminator and from no terminator at all, decide deliver or discard from that marker before any payload is parsed, and grade a received sequence against a discard-ratio budget so a link that is up but shredding packets is visible. Use when receiving, discarding or fault-finding CCSDS transfers on a SpaceWire link. Trigger: ecss, e-st-50-53c, spacewire-eop-character, spacewire-eep-error-terminator, ccsds-transfer-discard-rule, spacewire-packet-truncation, link-discard-ratio, terminator-disposition."
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
  tags: [ecss, e-st-50-53-ccsds-packet-transfer, e5053-eop-character, spacewire-eop-character, spacewire-eep-error-terminator, ccsds-transfer-discard-rule, spacewire-packet-truncation, link-discard-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — EOP Character (space-systems/ecss/e5053-eop-character)

Use when the task is the terminator of a SpaceWire packet carrying the
CCSDS packet transfer protocol, per ECSS-E-ST-50-53C clause 5.4.1.8 —
deciding whether a received transfer may be handed to the user at all,
and what a run of bad terminators is telling you about the link.

## Domain quick reference

- A SpaceWire packet ends with a marker, not a length. The normal
  end-of-packet character says the sender finished where it meant to;
  the error end-of-packet character says the packet was abandoned in
  flight, by a disconnect, a parity error or a receiver that ran out of
  buffer.
- Clause 5.4.1.8 makes the marker the gate on delivery. Only a transfer
  ended by the normal marker carries a CCSDS packet the receiving entity
  may pass up. Anything else is a fragment, and a fragment is discarded
  rather than repaired — there is no retransmission or reassembly in
  this protocol to repair it with.
- A third case exists and is not the same as the error marker: no
  terminator at all, because the reception was cut off or the buffer
  filled before any marker arrived. The packet never ended, so its
  length is unknown rather than wrong.
- The marker is checked before the payload. A fragment can hold a
  structurally perfect primary header and a plausible length field;
  parsing it first invites the receiver to trust content from a packet
  that the link already declared broken.
- A marker census over many transfers is the diagnostic that a single
  transfer cannot give. A link that passes bit-error tests can still
  return an error terminator on a steady fraction of packets, and that
  fraction against a budget is what separates a working link from a
  degraded one.

## Workflow

1. Normalise the terminator reported by the link interface into one of
   three tokens — normal, error, or absent — accepting the spelled-out
   and lower-case spellings interfaces actually emit, and refusing any
   token that is neither.
2. Derive the disposition from the token alone, before touching the
   payload: normal delivers, error discards, absent discards.
3. Keep the reason alongside the disposition. The error terminator and
   the absent terminator both discard, but they point at different
   faults and must not collapse into one message.
4. Where the expected transfer length is known, compare it with what
   arrived. A short transfer that still carried a normal terminator is
   a sender framing defect, not a link fault, and is reported that way.
5. Over a received sequence, count each terminator kind, derive the
   discard ratio, and compare it with the acceptable budget.
6. Report the transfer deliverable only when the terminator was normal
   and no length discrepancy was raised against it.

## Pitfalls

- Parsing the payload before reading the terminator. The header of an
  abandoned packet parses perfectly often enough that content checks
  will pass and the fragment will be delivered.
- Folding the absent terminator into the error terminator. Both
  discard, so the verdict looks the same, and then the operator cannot
  tell a link that reports errors from a receiver that is running out
  of buffer.
- Trying to salvage the octets that arrived before an error terminator.
  The protocol has no reassembly; a partially received packet has no
  defined remainder and keeping it substitutes a guess for data.
- Reading a normal terminator as proof the transfer is whole. The
  marker says the sender stopped deliberately; it does not say the
  sender sent everything it should have, which is why the length
  comparison stays in the assessment.
- Grading a link on a single transfer. One error terminator is noise;
  a ratio against a budget over a run is the measurement, and it is the
  only one that distinguishes a degraded link from an unlucky packet.

## Behavior contract (gate 3)

The marker normalisation, disposition rule, length cross-check and
sequence grading are exercised by the gate 3 contract test:
scripts/test_e5053_eop_character.py against
scripts/e5053_eop_character_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5053_eop_character.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

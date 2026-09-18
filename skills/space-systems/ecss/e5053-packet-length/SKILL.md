---
name: e5053-packet-length
description: "Validate the packet length field of a CCSDS packet transfer protocol data unit carried over SpaceWire under ECSS-E-ST-50-53C clause 5.1.2: confirm the declared octet count fits the field width, separate a real declaration from the reserved not-declared encoding, derive the length the carried packet claims from its own primary header, compare all three against the octets actually received, and discard the transfer when they disagree instead of trusting one. Use when a receiving node has to decide where the carried packet ends. Trigger: ecss, e-st-50-53-spacewire-ccsds-scope, ccsds-packet-transfer-packet-length, declared-length-field, packet-length-mismatch, spacewire-packet-truncation, length-field-capacity, undeclared-packet-length."
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
  tags: [ecss, e-st-50-53-spacewire-ccsds-scope, e5053-packet-length, ccsds-packet-transfer-packet-length, declared-length-field, packet-length-mismatch, spacewire-packet-truncation, length-field-capacity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Packet Length (space-systems/ecss/e5053-packet-length)

Use when the task is the packet length field of the CCSDS packet transfer
protocol data unit of ECSS-E-ST-50-53C clause 5.1.2 — what the sending node
has to put in that field, and what a receiving node is allowed to conclude
from it about where the carried packet ends.

## Domain quick reference

- The length field introduces a carried CCSDS packet on a SpaceWire link.
  It states an octet count for that packet and nothing else: it does not
  cover the target address octets, the protocol identifier or any other
  field of the enclosing transfer, so a length checked against the whole
  received character stream will always look wrong.
- The field has a finite width. A packet whose octet count does not fit
  the width agreed for a link cannot be declared at all on that link; that
  is a link configuration problem to be raised, not a value to be
  truncated into the field.
- One encoding of the field is reserved to mean that no length is being
  declared. A transfer using it is still legal, but the receiving node has
  only the end of packet marker to tell it where the packet finished, so
  it can no longer detect a short delivery from the length field alone.
  That is a reduced-assurance mode, and worth recording as such.
- The carried packet carries its own length too. The CCSDS primary header
  states the packet data field length as one less than its octet count, so
  the packet's self-declared size is the primary header plus that field
  plus one. Two independent statements of the same size are a genuine
  cross-check, and they can disagree.
- Every quantity here is an integer octet count. Comparisons are exact,
  and there is no numerical tolerance to tune; a difference of one octet
  is a real difference on every host.

## Workflow

1. Validate the width of the length field for the link, then validate the
   declared value against the capacity that width gives. A value that
   overflows the field is an encoding error, refused at the source.
2. Decide whether the value is a declaration or the reserved not-declared
   encoding. Only a real declaration can be compared with anything.
3. Count the octets actually received for the carried packet, taking them
   either as octets or as a count already made by the reception layer.
4. Group the declaration against the received count: it agrees, it is
   short of what arrived, or it is longer than what arrived. A short
   declaration leaves trailing octets with no declared home; a long one
   means the packet was cut off in transit.
5. When the carried packet's own primary header field is available, derive
   the size the packet claims for itself and cross-check it against both
   the received count and the declared length, reporting each disagreement
   separately so the faulty statement can be identified.
6. Deliver the packet upward only when the category permits it and no
   cross-check finding stands; otherwise discard it. Record a
   not-declared transfer as a limitation, not as a pass with no caveat.

## Pitfalls

- Measuring the declared length against the whole received transfer rather
  than the carried packet. The address octets and protocol identifier sit
  outside what the field counts, and including them turns every correct
  declaration into an apparent overflow.
- Treating the reserved not-declared encoding as a length of zero. Zero
  octets is not a packet; the encoding says the sender declined to declare,
  and a receiver that compares it as a number will reject every such
  transfer.
- Trusting the declared length over the received octets when they
  disagree. The disagreement is the finding; picking one number and
  carrying on delivers either a truncated packet or one padded with
  whatever followed it on the link.
- Clamping an over-capacity value into the field. That silently produces a
  plausible small length for a large packet, which is far harder to find
  downstream than a refusal at the sending node.
- Assuming the carried packet's own header agrees with the length field
  because both were written by the same sender. They are produced by
  different layers, and the cross-check exists precisely because one can
  be built from stale metadata.

## Behavior contract (gate 3)

The field width and capacity checks, the not-declared encoding, big-endian
encode and decode, the carried-packet header derivation, the agreement
grouping and the deliver-or-discard decision are exercised by the gate 3
contract test: scripts/test_e5053_packet_length.py against
scripts/e5053_packet_length_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5053_packet_length.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

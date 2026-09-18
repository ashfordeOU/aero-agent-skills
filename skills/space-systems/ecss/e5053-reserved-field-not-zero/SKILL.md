---
name: e5053-reserved-field-not-zero
description: "Determine what a SpaceWire CCSDS packet transfer receiver does when the reserved octet after the protocol identifier is not zero, under ECSS-E-ST-50-53C clause 5.5.4.3: the transfer is not conformant with this revision of the protocol, so no packet is handed up and nothing partial reaches the user, and the condition is reported carrying the value actually seen rather than dropped into silence. Grade a received run so one repeated value reads as a peer built to another revision while a scatter of values reads as octets being corrupted. Use when writing or fault-finding a SpaceWire receive path. Trigger: ecss, e-st-50-53c, spacewire-reserved-field-not-zero, non-zero-reserved-octet, spacewire-transfer-discard, spacewire-protocol-revision-mismatch, spacewire-receive-error-reporting, ccsds-transfer-decoding."
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
  tags: [ecss, e-st-50-53-ccsds-packet-transfer, e5053-reserved-field-not-zero, spacewire-reserved-field-not-zero, non-zero-reserved-octet, spacewire-transfer-discard, spacewire-protocol-revision-mismatch, spacewire-receive-error-reporting]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Reserved Field Not Zero (space-systems/ecss/e5053-reserved-field-not-zero)

Use when a SpaceWire transfer carrying the CCSDS packet transfer protocol
arrives with something other than zero in the reserved octet, per
ECSS-E-ST-50-53C clause 5.5.4.3 — what the receiving entity does with that
transfer, and what it has to say about it afterwards.

## Domain quick reference

- The reserved octet sits between the protocol identifier and the CCSDS
  Packet field. This revision of the protocol defines exactly one value
  for it, and a transfer carrying any other value is a transfer this
  entity was not built to read.
- Clause 5.5.4.3 carries two obligations on the receiving side. The
  transfer is not processed as a conformant transfer of this revision,
  so no CCSDS packet is handed up from it. And the condition is
  reported, with the value that was seen.
- Not parsing the payload is the substance of the first obligation. A
  transfer built to a later revision may have fields this entity does
  not know are there, so the octets after the reserved field are not
  reliably a packet, and a partial or misread packet delivered upward
  is worse than nothing delivered at all.
- Carrying the observed value into the report is the substance of the
  second. A count of discards tells an operator the link is losing
  traffic; the value tells them whether the peer is a different build
  or the line is dropping bits.
- The neighbouring clause fixes what a SENDER writes into the field.
  That is a separate obligation on a separate party and this one does
  not restate it: here the value is evidence about a peer, and the
  verdict it drives is about this transfer.

## Workflow

1. Read the reserved octet before anything after it. The decision is
   taken from that field alone, and taking it first is what stops the
   payload being parsed at all.
2. Validate the value as an octet. Something outside the octet range is
   a decoder defect upstream, not a non-conformant peer, and it must
   not be laundered into a protocol finding.
3. Where the value is the one this revision defines, continue and hand
   the packet up unchanged.
4. Where it is anything else, end the transfer: return no packet, count
   the octets withheld, and do not attempt to frame them.
5. Emit the report with both numbers in it — the value seen and the
   value this revision defines — so the log line is diagnosable without
   the reader knowing the protocol by heart.
6. Across a run, separate the two causes. One value repeated across
   most of the run is a peer emitting another revision; several
   distinct values are corrupted octets; a single rare value is neither
   yet and is worth watching rather than escalating.

## Pitfalls

- Parsing the payload first and checking the reserved field afterwards.
  The check stops being a guard and becomes a comment, and a misframed
  packet has already been built by the time it runs.
- Delivering the part of the packet that looked well formed. A transfer
  from an unknown revision may carry fields this entity cannot see, so
  "looked well formed" is not a property anyone here can establish.
- Reporting only a discard count. The operator learns that traffic is
  being lost and nothing about why, and the two causes need opposite
  responses — a peer rebuild versus a link investigation.
- Treating an out-of-range value as a protocol event. Values above the
  octet range never came off the link; they came out of a decoder, and
  filing them as peer non-conformance sends the investigation to the
  wrong end of the cable.
- Enforcing the sending-side zero-fill rule from inside this path. That
  obligation belongs to the adjacent clause and to the other party, and
  folding the two together loses which one an observed value violated.

## Behavior contract (gate 3)

Octet validation, the discard-before-parse decision, the withheld
payload, the report naming both values, and the run-level split between
a peer revision and corruption are exercised by the gate 3 contract
test:
scripts/test_e5053_reserved_field_not_zero.py against
scripts/e5053_reserved_field_not_zero_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e5053_reserved_field_not_zero.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

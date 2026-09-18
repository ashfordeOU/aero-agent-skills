---
name: e5053-error-end-of-packet
description: "Implement the error-termination rule on the receiving side of the SpaceWire CCSDS packet transfer protocol at ECSS-E-ST-50-53C clause 5.5.4.4: a transfer ended by an error terminator is discarded whole, so no part of the partial packet reaches the user, and the discard is reported rather than absorbed into a counter nobody reads. Evaluate a received sequence for clustered error terminations so a fault in progress is separated from independent upsets, and from a link that is carrying signal while delivering nothing. Use when building or debugging a SpaceWire receive path. Trigger: ecss, e-st-50-53c, spacewire-error-end-of-packet, spacewire-eep-discard, partial-packet-suppression, spacewire-receive-error-reporting, consecutive-eep-burst, ccsds-transfer-decoding."
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
  tags: [ecss, e-st-50-53-ccsds-packet-transfer, e5053-error-end-of-packet, spacewire-error-end-of-packet, spacewire-eep-discard, partial-packet-suppression, spacewire-receive-error-reporting, consecutive-eep-burst]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire CCSDS Transfer — Error End of Packet (space-systems/ecss/e5053-error-end-of-packet)

Use when a SpaceWire transfer carrying a CCSDS packet ends with an error
terminator, per ECSS-E-ST-50-53C clause 5.5.4.4 — what the receiving entity
does with what already arrived, and what it owes the entity above it.

## Domain quick reference

- A transfer arriving on a SpaceWire link ends one of three ways: a
  normal terminator, an error terminator, or nothing at all. Only the
  first says the octets in hand are the whole of what was sent.
- Clause 5.5.4.4 carries two obligations. The error-terminated transfer
  is discarded whole. And the discard is reported.
- Discarding whole is not caution, it is the only defensible reading. An
  error terminator says the transfer was cut short by something the link
  layer detected; the octets already taken in are a prefix of unknown
  length, and a CCSDS packet header at the front of a prefix parses
  perfectly well while describing a packet that never arrived.
- Reporting is the obligation that is quietly dropped, because dropping
  it costs nothing visible. A receive path that discards silently and a
  receive path with no traffic on it present identically to the user:
  packets stop appearing, and nothing says why.
- An unterminated transfer is the same case wearing different clothes.
  Its extent is equally unknown, so it takes the same disposition, with
  its own report so the two are distinguishable afterwards.

## Workflow

1. Take the disposition from the terminator, before the payload is
   framed. Framing first produces a packet object that then has to be
   thrown away, and sooner or later one of them escapes.
2. Normalise the terminator to a known name and reject anything else.
   An unrecognised terminator is a defect in the layer below, not a
   protocol event to be graded here.
3. On a normal termination, deliver the octets as they stand.
4. On an error termination, deliver nothing, and record how many octets
   were taken in and thrown away — the count is what makes the loss
   quantifiable later.
5. Emit the report with that count in it. One line per discarded
   transfer, naming how it ended, is the minimum that lets an operator
   distinguish loss from silence.
6. Over a sequence, look at clustering as well as rate. Independent
   upsets scatter; several error terminations in a row are a fault in
   progress, and a majority discarded is a link that is up on paper and
   down from above.

## Pitfalls

- Delivering the prefix because its header parsed. The header describing
  a packet is not evidence the packet arrived; it is evidence the first
  six octets arrived.
- Counting discards without reporting them. The number exists, nobody
  reads it, and the fault is found by whoever notices their telemetry
  went quiet an hour ago.
- Treating an unterminated transfer as a lesser case. Nothing said it
  ended, so nothing says it is complete, and delivering it is the same
  mistake with a quieter cause.
- Grading a link on discard rate alone. The same rate spread evenly and
  clustered into one burst are different faults, and only the clustered
  one has a moment in time to correlate against.
- Retrying at this layer on an error terminator. The transfer is gone
  and this entity has no copy to resend; a retry belongs to whoever
  still holds the packet, which is above here.

## Behavior contract (gate 3)

Terminator normalisation, the discard-whole disposition, the suppressed
partial payload, the per-discard report, and the sequence-level split
between sporadic upsets, a clustered burst and a link delivering nothing
are exercised by the gate 3 contract test:
scripts/test_e5053_error_end_of_packet.py against
scripts/e5053_error_end_of_packet_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e5053_error_end_of_packet.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

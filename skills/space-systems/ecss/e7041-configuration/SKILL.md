---
name: e7041-configuration
description: "Compute the downlink configuration of a large packet transfer subservice under ECSS-E-ST-70-41C clause 6.13.3.1: derive the usable part data field from the telemetry packet limit and the part report overhead, count the parts the declared largest message needs, and weigh that count against the part sequence number field width and the transaction identifier namespace. Use when a downlink part size, a part number field width, a transaction identifier pool or a largest supported message size is being fixed or reviewed for a service 13 subservice. Refuses a report overhead that leaves no data room and a part size the packet limit cannot carry. Trigger: ecss, e-st-70-41c, pus-service-13, large-packet-transfer, downlink-part-size, part-sequence-number-width, large-message-transaction-identifier, largest-supported-message-size."
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
  tags: [ecss, e-st-70-41c, pus-service-13, e7041-configuration, large-packet-transfer, downlink-part-size, part-sequence-number-width, large-message-transaction-identifier, largest-supported-message-size]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Large Packet Transfer — Downlink Configuration (space-systems/ecss/e7041-configuration)

Use when the task is the configuration step of the large message downlink of
ECSS-E-ST-70-41C clause 6.13.3.1 — fixing the part data size, the part
sequence number field and the transaction identifier pool of a service 13
subservice, and showing that the largest message the on-board software intends
to send down can actually be numbered, buffered and carried by that
configuration.

## Domain quick reference

- The part data size is not a free parameter. A downlink part report is a
  telemetry packet: its data field has to hold the transaction identifier,
  the part sequence number and the packet housekeeping that surrounds them
  before a single octet of the large message fits. The usable part payload
  is the packet limit minus that overhead, and a configured part size above
  it is unimplementable rather than merely inefficient.
- The number of parts a message needs is a ceiling division, not a ratio. A
  message one octet past a part boundary costs a whole extra part, and it is
  that extra part that can push the transaction past the part sequence number
  field.
- The part sequence number field width sets a hard ceiling. Numbering from
  one, a field of b bits can address 2^b - 1 parts, so the largest message
  the configuration supports is that ceiling times the usable part payload,
  whatever the on-board store can hold.
- The transaction identifier pool is sized by concurrency, not by traffic.
  Identifiers are only reusable once a transaction has finished, so a pool
  smaller than the number of transactions the subservice is configured to run
  at once forces an identifier collision on a live downlink.
- A message that fits inside one part does not belong on this service at all;
  it is a single report, and routing it through the downlink process buys
  overhead and a transaction slot for nothing.

## Workflow

1. Validate the telemetry packet limit and the part report overhead as whole
   octet counts; an overhead that equals or exceeds the packet limit is an
   input error, not a zero-payload configuration.
2. Derive the usable part payload, then compare it with the configured part
   size. Carry the smaller of the two forward as the effective part size and
   record the difference as a finding rather than silently honouring a part
   size the packet cannot hold.
3. Count the parts the declared largest message needs at the effective part
   size by ceiling division, and note the octets the last part actually
   carries and how full it is.
4. Compute the ceiling of the part sequence number field and the largest
   message that ceiling and the effective part size jointly support.
5. Validate the transaction identifier pool: whole numbers inside the
   identifier field, no duplicates, and at least as many identifiers as the
   configured concurrent transaction count.
6. Report the effective part size, the part count, the last part occupancy,
   the supported message ceiling and every finding: an unusable part size, a
   message needing more parts than the field can number, a pool too small for
   the concurrency, or a message small enough to need no transfer at all.

## Pitfalls

- Configuring the part size from the packet limit and forgetting the part
  report overhead. The first downlink attempt then produces a packet one
  header longer than the link allows, and the defect surfaces in flight
  rather than in the configuration review.
- Sizing the part count with a plain division. Ceiling division is the rule,
  and the rounded-down answer hides exactly the boundary case where the part
  sequence number field overflows.
- Reading the part sequence number ceiling as 2^b. Numbering starts at one,
  so the usable ceiling is 2^b - 1 and a configuration sized on the larger
  number loses its last part.
- Sizing the transaction identifier pool from the message rate. Concurrency
  is what consumes identifiers; a fast series of sequential transfers can
  live on a single identifier while three concurrent ones cannot.
- Treating a part size above the usable payload as a rounding matter and
  clamping it silently. The clamp changes the part count and the supported
  message ceiling, so it has to be reported as a finding against the
  configuration that was submitted.

## Behavior contract (gate 3)

The overhead validation, usable payload derivation, ceiling part count, last
part occupancy, sequence field ceiling, identifier pool validation and the
assembled configuration assessment are exercised by the gate 3 contract test:
scripts/test_e7041_configuration.py against
scripts/e7041_configuration_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_configuration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

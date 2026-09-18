---
name: e7041-resources
description: "Size the on-board resources a large packet transfer downlink subservice reserves under ECSS-E-ST-70-41C clause 6.13.3.2: turn each queued large message into the whole parts it buffers, sweep the transaction timeline for the peak of simultaneous transactions and peak reserved octets, then admit or refuse each arrival against the declared transaction slots and buffer pool. Use when the number of simultaneous large message downlinks, the octets reserved per transaction or the buffer pool of a service 13 subservice has to be justified or reviewed. Refuses an unordered transaction interval and a zero slot count. Trigger: ecss, e-st-70-41c, pus-service-13, large-message-downlink-resources, concurrent-transaction-slots, downlink-buffer-pool, transaction-slot-admission, peak-reserved-octets."
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
  tags: [ecss, e-st-70-41c, pus-service-13, e7041-resources, large-message-downlink-resources, concurrent-transaction-slots, downlink-buffer-pool, transaction-slot-admission, peak-reserved-octets]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Large Packet Transfer — Downlink Resources (space-systems/ecss/e7041-resources)

Use when the task is the resource step of the large message downlink of
ECSS-E-ST-70-41C clause 6.13.3.2 — deciding how many simultaneous large
message transactions the subservice reserves capacity for, how many octets
each one holds while it is in progress, and whether a stated downlink demand
fits inside that declaration.

## Domain quick reference

- A downlink transaction is not free while it runs. From the moment its first
  part is generated until its last part leaves, it holds a transaction slot,
  a transaction identifier and the source data behind the parts still to be
  sent. The resource question is therefore about simultaneity, not about the
  total volume sent over an orbit.
- Reserved octets are counted in whole parts. The subservice reads and sends
  part-sized units, so a message that leaves a partly filled final part still
  reserves that whole part, and a resource budget built from raw message
  sizes is optimistic by up to one part per transaction.
- The peak is what sizes the subservice, and the peak is found by sweeping
  the transaction timeline, not by averaging. Two long transfers that merely
  touch at their ends never coexist; two short ones that overlap by a second
  do, and that second is the sizing case.
- A transaction that ends exactly when another begins hands over its slot
  cleanly. Treating that instant as an overlap inflates the slot count by one
  on every back-to-back schedule and hides the real peak elsewhere.
- Admission is ordered. When the declared resources are short, it matters
  which arrival is refused: the subservice admits in arrival order and the
  refusal falls on the transaction that finds no free slot or no free buffer,
  which is rarely the largest one.

## Workflow

1. Validate the declared resources: whole positive transaction slots, a whole
   positive buffer pool in octets and a positive part size.
2. Validate every demand entry: a positive message size and a transaction
   window whose end is not before its start.
3. Convert each message into its reserved footprint by rounding its size up
   to a whole number of parts.
4. Sweep the windows as an ordered event list, releasing a transaction before
   admitting one that starts at the same instant, and record the peak
   simultaneous transaction count and the peak reserved octets together with
   the instants at which they occur.
5. Replay the demand in arrival order against the declared slots and buffer
   pool, marking each transaction admitted or refused and naming which of the
   two resources was exhausted.
6. Report the peaks, the admission outcome and every finding: a peak
   transaction count above the declared slots, a peak reservation above the
   declared pool, or a single message whose footprint no empty pool can hold.

## Pitfalls

- Sizing the buffer pool from the largest message instead of from the peak of
  overlapping messages. One large transfer is the easy case; three medium
  ones in flight together is what exhausts the pool.
- Counting reserved octets from the message length. The final part is
  reserved whole, so the footprint is the part-rounded size and the
  difference is one part per concurrent transaction at the worst moment.
- Treating an end instant and a start instant at the same time as an overlap.
  The slot is released first, and the inflated count sends the sizing to the
  wrong transaction.
- Reporting only that the demand does not fit. The useful answer names which
  resource ran out first, because adding slots and adding buffer octets are
  different design changes with different costs.
- Assuming a refused transaction frees nothing. A refusal never reserves, so
  the transactions behind it in arrival order are assessed against the
  unchanged remaining resources rather than against a spent pool.

## Behavior contract (gate 3)

The resource validation, part-rounded footprint, timeline sweep, peak
detection, ordered admission and the assembled resource assessment are
exercised by the gate 3 contract test: scripts/test_e7041_resources.py
against scripts/e7041_resources_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_resources.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

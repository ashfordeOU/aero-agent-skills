---
name: e7041-packet-store
description: "Model what an on-board packet store does with each telemetry packet offered to it under ECSS-E-ST-70-41C clause 6.15.3.1. Use when the task is choosing between a bounded and a circular packet store, or explaining which packets a full one lost: tracking occupancy against capacity in octets, discarding while storage is switched off, holding the oldest record in a bounded store and overwriting it in a circular one, refusing an overwrite that would tear a hole in a retrieval the ground is still reading out, and reporting fill, losses and the oldest and newest packet held. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, on-board-packet-store, circular-packet-store-overwrite, bounded-packet-store-full, packet-store-storage-state, open-retrieval-overwrite-protection."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-packet-store, on-board-packet-store, circular-packet-store-overwrite, bounded-packet-store-full, packet-store-storage-state, open-retrieval-overwrite-protection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Packet Store (space-systems/ecss/e7041-packet-store)

Use when the task is the packet store of ECSS-E-ST-70-41C clause
6.15.3.1 -- the bounded region of on-board memory that holds telemetry
packets in arrival order until the ground can retrieve them, and the
decision it makes about each packet offered to it.

## Domain quick reference

- A packet store has four properties that decide everything: an
  identity, a capacity, a storage state that can be switched
  independently of every other store, and a type. The first three are
  bookkeeping; the type is the interesting one, because it only matters
  at the moment the store is full.
- A bounded store stops accepting when full. The oldest packets are
  kept and the newest are lost, which is the right choice when the
  beginning of the record is the part that matters -- the run-up to an
  anomaly, the opening seconds of a separation.
- A circular store keeps accepting and overwrites its oldest packets to
  make room. The newest are kept and the oldest are lost, which is the
  right choice when the current picture matters more than the history.
- Neither type is the safe default. Both lose data once the store fills
  and the ground has not emptied it; they differ only in which end of
  the record goes. A store type chosen without deciding which end is
  expendable is a choice made by accident.
- Switching storage off is not the same as emptying the store. Packets
  offered while storage is off are discarded, the content already held
  is untouched, and switching back on resumes at the same occupancy.
- An overwrite has to respect a retrieval in progress. Overwriting a
  packet the ground has not yet received hands it a record with an
  unmarked hole in the middle, so a circular store with an open
  retrieval behaves like a bounded one against the part still to be
  read out, and discards rather than tears.
- A packet larger than the whole capacity is an input error, not a full
  store. No amount of overwriting makes room for it, and reporting it
  as a fullness discard hides a sizing mistake.

## Workflow

1. Validate the store: a non-empty identity, a known type, a capacity
   of at least one octet, and a known storage state. Default the
   storage state to on only when the definition omits it.
2. Validate each packet and refuse outright one whose size exceeds the
   capacity, before any fullness or type reasoning.
3. If storage is off, discard the packet, count it, and leave the
   content alone.
4. If the packet fits in the free space, append it and stop -- the
   store type is irrelevant until the store is full.
5. If the store is full and bounded, discard the packet and count it.
6. If the store is full and circular, take the oldest packets one at a
   time until the new one fits. If the next one to take is still owed
   to an open retrieval, put back everything taken and discard the new
   packet instead.
7. After a successful overwrite, move the retrieval position back by
   the number of packets removed, so it still points at the same packet
   it did before.
8. Report capacity, occupancy, fill, packet count, oldest and newest
   packet, whether a retrieval is open, and the discard and overwrite
   counts separately -- they are different losses.

## Pitfalls

- Treating circular as the lossless type. It loses exactly as much as a
  bounded store does once full; it loses the other end.
- Counting an overwrite as a discard. A discard means the newest packet
  never landed; an overwrite means an older one was removed to make
  room, and an operator reading one number cannot tell which record has
  the gap.
- Overwriting through an open retrieval. The downlink carries no mark
  where the hole is, so the gap is found much later, if at all.
- Reading a disabled store as an empty one. Its content is intact and
  retrievable; only new packets are being turned away.
- Reporting an oversized packet as a fullness loss. It would be lost
  into an empty store too, and the finding is the packet size against
  the store sizing, not the traffic.
- Comparing a fill fraction against a capacity threshold with a strict
  inequality. Occupancy is exact in octets, so do the admission test on
  the integers and keep the fraction for reporting.

## Behavior contract (gate 3)

The definition validation, oversize refusal, storage-state discard,
bounded fullness discard, circular overwrite, open-retrieval overwrite
protection, retrieval-position adjustment and the per-store status
report are exercised by the gate 3 contract test:
scripts/test_e7041_packet_store.py against
scripts/e7041_packet_store_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_packet_store.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

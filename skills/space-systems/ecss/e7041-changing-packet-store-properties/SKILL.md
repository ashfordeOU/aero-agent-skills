---
name: e7041-changing-packet-store-properties
description: "Evaluate a request to change the properties of an on-board packet store under ECSS-E-ST-70-41C clause 6.15.3.9. Use when a telecommand resizes a store, switches it between bounded and circular or moves it to another virtual channel: refusing any change while storage is enabled or a retrieval is open, refusing a capacity below the octets already held or off the allocation block, requiring an empty store before the type changes, holding the sum of capacities inside the memory pool, and returning a per-item disposition so one rejected change never abandons the rest. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, packet-store-property-change, packet-store-resize, packet-store-type-change, packet-store-memory-pool, packet-store-change-preconditions."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-changing-packet-store-properties, packet-store-property-change, packet-store-resize, packet-store-type-change, packet-store-memory-pool, packet-store-change-preconditions]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Changing Packet Store Properties (space-systems/ecss/e7041-changing-packet-store-properties)

Use when the task is the packet store property change of
ECSS-E-ST-70-41C clause 6.15.3.9 -- the request that alters the
capacity, the type or the virtual channel of a store that already
exists and may already hold telemetry, and the preconditions that stop
it from destroying what is held.

## Domain quick reference

- A packet store carries an identity, a capacity in octets, a type
  that only matters when it fills, a virtual channel it is read out
  on, a storage state and a current occupancy. Clause 6.15.3.9 changes
  the middle three on a store already in the table; it does not create
  or delete one.
- Nothing changes while storage is enabled. A property change is not
  atomic against the packet that is arriving, and the store would end
  up sized one way and filled another. Disabling storage first is the
  operator's explicit statement that the store is quiet.
- Nothing changes while a retrieval is open. The ground is reading the
  record out against a layout it was told about; changing the capacity
  or the virtual channel under it hands it a truncated or misrouted
  read-out that looks like a downlink fault.
- A capacity below the octets already held is refused rather than
  performed with a silent truncation. The difference is telemetry the
  ground has not seen, and dropping it as a side effect of a sizing
  telecommand is the kind of loss nobody goes looking for.
- Capacity is allocated in whole blocks. A request that lands between
  blocks is a sizing mistake, not a value to round -- rounding up
  overruns the pool by an amount the operator never asked for, and
  rounding down loses part of the store they did.
- The type may only change on an empty store. Type decides which end
  of the record is expendable once the store fills; changing it under
  content captured on the other promise re-labels history.
- The stores share one memory pool. A growth is only affordable if the
  other stores leave room for it, so the check is against the pool
  total, not against the store in isolation.
- A request carries many changes and each is decided on its own. A
  change whose named properties already hold those values is rejected
  as a no-op, so the ground learns its request did nothing.

## Workflow

1. Normalize the store table: unique identifiers, block-aligned
   capacities, occupancy inside capacity, a known type, booleans for
   the storage and retrieval states. Reject a table that already
   commits more than the memory pool.
2. Validate each change item. It must name an existing identifier and
   at least one property; an item naming no property is malformed, not
   an empty success.
3. Refuse on the state preconditions first -- storage enabled, then
   retrieval open -- before looking at the values, so the disposition
   names the precondition the operator has to clear.
4. Check a new capacity against the configured range, the allocation
   block, the octets held, and the pool with this store's current
   commitment taken out.
5. Check a type change against occupancy; restating the current type
   is not a type change and must not trip the empty-store rule.
6. Reject an item whose every named property already holds that value.
7. Apply the accepted item, record exactly which properties moved, and
   carry on to the next item.
8. Report the table sorted by identifier with fill fraction, pool
   commitment and free pool octets.

## Pitfalls

- Rounding a capacity to the nearest block instead of rejecting it.
  Rounding up quietly takes pool octets from another store that will
  fail to grow later for reasons nobody can trace to this request.
- Truncating a store to the new capacity and reporting success. The
  lost octets are telemetry, and the disposition said accepted.
- Treating a restated type as a type change. The request that also
  moves the virtual channel then fails on a full store for a property
  it was not changing.
- Checking a growth against the pool without first removing the
  store's own current capacity from the committed total. The store is
  then charged twice and a change that fits is refused.
- Aborting the whole request at the first rejected change. The later
  items are independent stores, and the operator is left re-sending a
  request whose second half had already been valid.
- Reading a disabled store as a broken one and re-enabling it to make
  the change go through. Storage off is the precondition, not a fault.

## Behavior contract (gate 3)

The table normalization, the storage and retrieval preconditions, the
capacity range, block alignment, occupancy floor and pool ceiling, the
empty-store rule for a type change, the no-op rejection and the sorted
report are exercised by the gate 3 contract test:
scripts/test_e7041_changing_packet_store_properties.py
against
scripts/e7041_changing_packet_store_properties_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_changing_packet_store_properties.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e7041-managing-the-packet-stores
description: "Configure the on-board packet stores under ECSS-E-ST-70-41C clause 6.15.3.8: create, delete, resize, retype and move them between virtual channels. Use when a store set is being reshaped and the question is which commands the spacecraft may accept: requiring a store to be quiescent before any change, refusing a resize below current occupancy, refusing a retype on a store that still holds packets, holding the capacities inside the mass memory budget, rejecting a channel the craft does not have, and reporting the content lost with a deleted store. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, packet-store-management, resize-packet-store, packet-store-mass-memory-budget, packet-store-virtual-channel."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-managing-the-packet-stores, packet-store-management, resize-packet-store, packet-store-mass-memory-budget, packet-store-virtual-channel]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Managing the Packet Stores (space-systems/ecss/e7041-managing-the-packet-stores)

Use when the task is the packet store management of ECSS-E-ST-70-41C
clause 6.15.3.8 -- creating, deleting, resizing, retyping and
rechannelling the stores themselves rather than their contents, and
saying which of those a spacecraft in its current state may accept.

## Domain quick reference

- Everything here changes the store rather than what is in it. That
  is why the preconditions are heavier than the storage-control ones:
  a packet already inside the store, or a cursor already walking it,
  was admitted under the shape the command is about to change.
- Quiescence is the single precondition underneath all of it: storage
  function off and no retrieval engaged. Delete, resize, retype and
  rechannel all need it, and the rejection is the same in each case.
- A resize while storage is on loses whichever packets arrive during
  the change, and nothing in the downlink marks them. A retype while a
  retrieval is open changes the overwrite rule under the cursor.
- A resize below the current occupancy is refused. Accepting it would
  discard the overflow to make the number fit, which is a deletion the
  operator did not ask for.
- A retype needs the store empty, not just quiescent. Packets stored
  under the bounded rule would otherwise start living under the
  circular one, and the oldest of them become overwritable without
  anybody having decided that.
- The capacities are a shared budget. Mass memory is finite, so a
  create or a resize is checked against what every other store has
  already claimed, and the check excludes the store being resized so
  it is not measured against itself.
- Deleting a loaded store is allowed and reported. The content goes
  with the store, and the only protection the clause gives is that
  the loss is named rather than silent.
- A created store starts switched off and empty. It never inherits a
  storage state from the command that made it, so nothing can be
  recorded into a store before anybody has configured what it takes.
- A create failing on an identity already in use is a refusal, never
  a replacement. Replacing would delete a store, and its contents,
  under a command that says nothing about deleting.

## Workflow

1. Normalize the configuration first: every store with a positive
   capacity, an occupancy inside it, a known type and a channel the
   spacecraft has, no duplicate identity, and the capacities together
   inside the memory budget. An invalid configuration runs nothing.
2. Normalize each command against its own action, so a create carries
   type, capacity and channel, a resize carries a capacity, a retype
   carries a type and a rechannel carries a channel.
3. For a create, refuse an identity already in use, then a channel the
   craft lacks, then a capacity the budget cannot take, and otherwise
   add the store switched off and empty.
4. For everything else, refuse a store the application does not hold,
   then check quiescence before any action-specific rule.
5. Apply the action-specific rules: occupancy floor on a resize, empty
   store on a retype, a real channel on a rechannel, and the budget
   with the store's own current claim excluded on a resize.
6. Assemble the configuration report -- per store, plus allocated,
   free and utilisation against the budget -- and close with the
   verdict, every refusal named, and the content lost to a delete.

## Pitfalls

- Checking a resize against the budget without excluding the store's
  own current capacity. A store is then measured against itself and a
  resize that frees memory is refused for exceeding the budget.
- Resizing or retyping a store that is still storing. The packets
  arriving during the change are lost, and the loss is invisible
  because the store reports the new shape as if it had always had it.
- Allowing a resize below the occupancy. It looks like a configuration
  change and is actually a deletion, chosen by whichever end of the
  store the implementation happened to truncate.
- Retyping a store that holds packets. Packets admitted under the
  bounded rule become overwritable under the circular one, so the
  oldest part of a record can disappear after the command that was
  only supposed to change a label.
- Letting a create overwrite an existing store. The command says
  nothing about deleting, and a store full of an anomaly is gone.
- Deleting a loaded store without reporting what went with it. The
  capacity comes back and the record does not, and nothing says so.
- Giving a created store a storage state from the command. It then
  starts recording before its report types are configured, and stores
  whatever the default filter admits.
- Computing the report's allocated total from the input rather than
  from the resulting set. A refused create or delete then shows in the
  budget figures as though it had been applied.

## Behavior contract (gate 3)

The configuration and command normalization, the quiescence
precondition shared by delete, resize, retype and rechannel, the
occupancy floor on a resize, the empty-store rule on a retype, the
budget check with the store's own claim excluded, the channel check,
the create refusal on a used identity, the reported content loss on a
delete, the configuration report with its budget figures and the run
verdict are exercised by the gate 3 contract test:
scripts/test_e7041_managing_the_packet_stores.py against
scripts/e7041_managing_the_packet_stores_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_managing_the_packet_stores.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e7041-storage-control-definitions
description: "Maintain the storage-control definition store of the on-board storage and retrieval service under ECSS-E-ST-70-41C clause 6.15.4.2. Use when the task is which packet stores a generated report is written into: binding an application process, report type and message subtype selection to a named packet store, absorbing a narrower definition under a wider one inside the same store, treating the same selection in two stores as two deliberate on-board copies rather than a duplicate, holding per-store and total definition capacity, and answering coverage as a store set and a copy count. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, storage-control-definition-store, packet-store-selection-binding, storage-definition-absorption, on-board-copy-multiplicity, storage-definition-capacity."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-storage-control-definitions, storage-control-definition-store, packet-store-selection-binding, storage-definition-absorption, on-board-copy-multiplicity, storage-definition-capacity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Storage-Control Definitions (space-systems/ecss/e7041-storage-control-definitions)

Use when the task is the storage-control definition step of
ECSS-E-ST-70-41C clause 6.15.4.2 -- the list that binds telemetry
selections to named packet stores and so decides which reports the
on-board storage and retrieval service writes down, and into how many
places.

## Domain quick reference

- A storage-control definition is a pair: one packet store and one
  selection. The selection has three levels -- application process,
  then report type, then message subtype -- and the levels below the
  one named are implicit, so an application-process definition covers
  everything that process generates.
- The definition store is keyed by packet store first. That is the
  difference from the forwarding definition list, which has one
  real-time downlink and so answers yes or no. Here a report can be
  written into several stores, and the answer is a set.
- Two stores holding the same selection is a design, not a mistake. A
  long-term store on one virtual channel and a short circular store
  for the anomaly window deliberately keep the same reports, and the
  copy count is what the octet budget has to be multiplied by.
- Absorption is per store. Inside one store, adding a wider definition
  removes the narrower ones it covers, and adding a narrower one under
  an existing wider is rejected. Across stores there is no
  interaction whatever.
- An absorbing add does not spend capacity. It replaces the entries it
  swallows, so refusing it at a full definition store leaves the
  operator unable to do the one thing that frees room.
- An application process must be declared before it can be selected.
  The definition store does not gain a process by being told to store
  its reports, and a definition naming an undeclared process is a
  ground-segment typo more often than an intention.
- Definitions are the static picture. Whether a report actually lands
  also depends on the storage state of the store and the size of what
  is already held; the definition store only answers which stores are
  meant to take it.

## Workflow

1. Validate each definition: a named packet store, an application
   process in range, a report type when a subtype is named, values
   inside their ranges. A subtype without a report type is malformed.
2. Reject a definition naming a packet store the service does not
   hold, then one naming an undeclared application process, before
   touching the store.
3. Reject an exact duplicate inside the same packet store, and reject
   a selection a wider definition of that store already covers.
4. Otherwise collect the narrower definitions the new one covers,
   remove them, and add the new one; charge capacity only when nothing
   was absorbed.
5. For a delete, remove the exact selection from the named store, and
   reject a delete that names a narrower form of a definition held in
   its wider form. Drop a store that holds nothing.
6. Answer coverage by testing every store's definitions against the
   report and returning the sorted store list; the copy count is its
   length.
7. Report the definition store sorted by packet store and by selection
   with the wildcard levels first, and name the selections more than
   one store holds.

## Pitfalls

- Collapsing the same selection held by two stores into one entry. The
  second copy is the one the anomaly window depends on, and the octet
  budget silently halves.
- Charging capacity for an absorbing add. The store is full of the
  narrow entries the wide one would replace, so the only move that
  frees room is the one that gets refused.
- Answering coverage with a boolean. The caller then sizes the store
  for one copy of a report that is being written into three.
- Letting a wider definition and the narrower ones it covers coexist.
  A later delete of the narrow entry leaves the report still stored
  through the wide one while the ground believes it stopped.
- Creating a definition for an undeclared application process. The
  declared list is the service's own configuration, and extending it
  from a definition request is a change of scope.
- Reading an empty definition store as uninitialised and storing
  everything. A store that selects nothing is what a deliberate delete
  leaves behind.

## Behavior contract (gate 3)

The definition validation, packet store and application process
checks, absorption, duplicate and covered rejections, per-store and
total capacity, the multi-store coverage set and copy count, the
delete rules and the sorted report are exercised by the gate 3
contract test:
scripts/test_e7041_storage_control_definitions.py
against
scripts/e7041_storage_control_definitions_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_storage_control_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

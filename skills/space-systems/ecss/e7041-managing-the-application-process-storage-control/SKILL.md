---
name: e7041-managing-the-application-process-storage-control
description: "Manage the application-process storage-control configuration of the on-board storage and retrieval service under ECSS-E-ST-70-41C clause 6.15.4.4. Use when the task is deciding which telemetry each packet store writes down: holding one selection tree per store over application process, report type and message subtype, setting a wildcard against the specific entries it subsumes, refusing a partial deletion inside a wildcard, refusing an undefined store or an uncontrolled application process, and returning a per-item disposition so one rejected item never abandons the rest. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, application-process-storage-control, per-packet-store-selection-tree, storage-selection-wildcard, controlled-application-process-list, storage-request-item-disposition."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-managing-the-application-process-storage-control, application-process-storage-control, per-packet-store-selection-tree, storage-selection-wildcard, controlled-application-process-list, storage-request-item-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Application-Process Storage Control (space-systems/ecss/e7041-managing-the-application-process-storage-control)

Use when the task is the application-process storage-control
configuration of ECSS-E-ST-70-41C clause 6.15.4.4 -- the per-store
selection tree that decides which telemetry the on-board storage and
retrieval service writes down, and how an add or delete request
changes it.

## Domain quick reference

- Every packet store carries its own tree: application process, then
  report type, then message subtype. A store writes a report down only
  when its own tree selects it, so an empty tree stores nothing. That
  is a deliberate state, not an uninitialised one.
- The packet store sits above the tree, and that is the difference
  from the real-time forwarding configuration. There is one downlink
  but several stores, the trees are independent, and the same report
  selected by two of them is two on-board copies by design.
- Each level carries an implicit wildcard. An application process
  entry with no report types under it means every report type of that
  process; a report type entry with no subtypes means every subtype.
  The wildcard is a state, not a shorthand that expands, so a subtype
  defined on board later is still stored.
- A wildcard and the specific entries under it cannot coexist. If both
  were held, a later delete of the specific entry would leave the
  report still stored through the wildcard while the ground believed
  it had stopped. Setting a wildcard therefore clears what it subsumes
  and a specific entry beneath one is rejected, not absorbed.
- A wildcard cannot be partially deleted. Removing one subtype from an
  all-subtypes entry would make the service invent the complement set;
  the operator deletes the wildcard and adds back what they want.
- Only defined packet stores and controlled application processes may
  appear. A request naming either outside those lists is rejected at
  that item; the service does not acquire a store or a process by
  being asked about one.
- Capacity is per store. A store full of selections does not stop the
  next store taking the same selection, and the rejection has to name
  which store ran out.

## Workflow

1. Validate each item: a named packet store, an application process
   in range, a report type when a subtype is named, values inside
   their ranges. A subtype without a report type is malformed.
2. Reject an undefined packet store, then an uncontrolled application
   process, before touching the configuration.
3. For an add, walk that store's tree to the level the item names,
   creating intermediate entries. Set a wildcard by clearing what it
   subsumes; reject an entry a wider wildcard already covers and one
   already present.
4. Apply the per-store sizing limits as per-item rejections, so a
   request that overruns one store still lands its items in another.
5. For a delete, remove the named entry and everything below it.
   Reject an absent entry and any delete inside a wildcard. Drop the
   packet store key once its tree is empty.
6. Answer a storage question per store: the process wildcard first,
   then the report type wildcard, then the subtype set. Answer it
   across stores by collecting every store that says yes.
7. Report packet store, then application process, then report type,
   then subtype, sorted at every level.

## Pitfalls

- Carrying one tree for all stores because the forwarding clause has
  one. Every add then leaks into stores it was never meant to touch.
- Expanding a wildcard into the subtypes present when it is set. The
  expansion is a snapshot, and the subtype added on board next month
  is silently not stored.
- Collapsing the same selection in two stores into one entry. The
  second copy is usually the short circular store an investigation
  depends on.
- Aborting the whole request at the first rejected item. The later
  items usually name a different store and would have succeeded.
- Treating a per-store capacity rejection as a configuration-wide
  one. The operator re-sends against the same full store instead of
  the empty one next to it.
- Reading an empty tree as uninitialised and storing everything. It
  is what a deliberate delete leaves behind, and filling the store
  from that guess is how a downlink budget disappears.

## Behavior contract (gate 3)

The item validation, the packet store and controlled-process checks,
wildcard subsumption, the partial-delete refusal, per-store capacity,
the multi-store storage question and the sorted report are exercised
by the gate 3 contract test:
scripts/test_e7041_managing_the_application_process_storage_control.py
against
scripts/e7041_managing_the_application_process_storage_control_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_managing_the_application_process_storage_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

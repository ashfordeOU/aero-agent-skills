---
name: e7041-managing-the-housekeeping-parameter-report-storage
description: "Configure the housekeeping parameter report storage-control configuration of the on-board storage and retrieval service under ECSS-E-ST-70-41C clause 6.15.4.5. Use when the task is which housekeeping reports each packet store writes down, one structure at a time: adding and deleting structure identifiers per store and application process, refusing an identifier that process never defined, holding an all-structures wildcard against the entries it subsumes, and naming the selections a deleted structure definition left stale so they can be pruned. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, housekeeping-storage-control, housekeeping-structure-storage-selection, all-structures-storage-wildcard, stale-housekeeping-storage-selection, per-packet-store-housekeeping-copy."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-managing-the-housekeeping-parameter-report-storage, housekeeping-storage-control, housekeeping-structure-storage-selection, all-structures-storage-wildcard, stale-housekeeping-storage-selection, per-packet-store-housekeeping-copy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Housekeeping Parameter Report Storage Control (space-systems/ecss/e7041-managing-the-housekeeping-parameter-report-storage)

Use when the task is the housekeeping parameter report storage-control
configuration of ECSS-E-ST-70-41C clause 6.15.4.5 -- the per-structure
selection that decides which housekeeping reports each packet store
writes down, and what happens to it when the housekeeping definitions
move underneath.

## Domain quick reference

- The configuration is keyed three deep: packet store, then
  application process, then housekeeping structure identifier. A
  structure is written down by a store when that store's entry names
  it, or carries the all-structures wildcard for that process.
- A structure identifier only means something inside the application
  process that defined it. The same number under two processes names
  two unrelated reports, so every check is against the housekeeping
  definitions of that process, never against a global list.
- An identifier that process never defined is refused. It selects
  nothing, and accepting it would leave the ground believing a report
  is being captured that the spacecraft cannot generate.
- The all-structures wildcard follows the definitions rather than
  naming them. A structure defined on board after the wildcard was set
  is stored too, which is why the wildcard cannot be expanded into the
  identifiers present at the moment it is set.
- A wildcard and the explicit identifiers under it cannot coexist, and
  the wildcard cannot be partially deleted. The operator deletes the
  whole entry and adds back the structures they want.
- Definitions move. Deleting a structure definition leaves behind any
  selection that named it -- a stale selection that stores nothing,
  looks exactly like a working one, and comes back to life against the
  wrong report if the identifier is reused. Naming and pruning those
  is part of managing this configuration.
- The same structure in two stores is two copies on purpose. A store
  is refused a structure only on its own merits, and a full store does
  not stop the store beside it taking the same report.

## Workflow

1. Validate each item: a named packet store, an application process in
   range, and a structure identifier in range when one is given. No
   identifier means the all-structures wildcard for that process.
2. Reject an undefined packet store, then a process with no
   housekeeping definitions at all, then an identifier that process
   never defined.
3. For an add, set the wildcard by clearing the identifiers it
   subsumes; reject an identifier under an existing wildcard and one
   already held; apply the per-process capacity as a rejection.
4. For a delete, remove the named identifier, or the whole entry when
   none is named. Reject an absent identifier and any delete inside a
   wildcard. Drop the packet store key once its entries are gone.
5. Answer the storage question per store, and across stores by
   collecting every store that says yes.
6. Walk the configuration against the current housekeeping definitions
   to name the stale selections, ignoring wildcard entries, and prune
   them on request, reporting exactly what was removed.
7. Report packet store, then process, then identifier, sorted, and
   name the structures more than one store holds.

## Pitfalls

- Checking a structure identifier against a global list. The number
  that is valid under one application process is refused or, worse,
  accepted against the wrong report under another.
- Expanding the all-structures wildcard into today's identifiers. The
  structure defined next month is then silently not stored, which is
  the one case the wildcard existed to cover.
- Treating a stale selection as an error to reject at add time. It was
  valid when it was added; the definition went away afterwards, and
  only a sweep against the current definitions finds it.
- Pruning a wildcard entry as stale. It names no identifier, so it
  cannot be stale, and removing it stops housekeeping storage the
  operator never asked to stop.
- Collapsing the same structure held by two stores. The second copy is
  the one on the short circular store, and the octet budget halves
  without anyone noticing.
- Aborting the request at the first refused identifier. The rest of a
  housekeeping bring-up request is usually independent and valid.

## Behavior contract (gate 3)

The item validation, the definition check per application process, the
wildcard subsumption and partial-delete refusal, per-process capacity,
the multi-store copy list, stale-selection detection and pruning and
the sorted report are exercised by the gate 3 contract test:
scripts/test_e7041_managing_the_housekeeping_parameter_report_storage.py
against
scripts/e7041_managing_the_housekeeping_parameter_report_storage_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_managing_the_housekeeping_parameter_report_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

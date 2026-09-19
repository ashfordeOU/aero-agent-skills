---
name: e7041-controlling-the-packet-store-storage-function
description: "Manage the storage function of the on-board packet stores under ECSS-E-ST-70-41C clause 6.15.3.3. Use when an enable, a disable or a report-type change goes to several stores at once and the question is what each store ends up doing: switching storage per store, accepting an enable on a store already storing as a no-change, treating a store named twice in one command as malformed, failing for only the store the application does not hold while the rest still act, and refusing to delete a report type a store was never storing. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, packet-store-storage-control, enable-packet-store-storage, packet-store-report-type-list, multi-store-command-partial-failure."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-controlling-the-packet-store-storage-function, packet-store-storage-control, enable-packet-store-storage, packet-store-report-type-list, multi-store-command-partial-failure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Controlling the Packet Store Storage Function (space-systems/ecss/e7041-controlling-the-packet-store-storage-function)

Use when the task is the storage-function control of ECSS-E-ST-70-41C
clause 6.15.3.3 -- switching the storage function of named packet
stores on and off, changing the report types each store accepts, and
deciding what happens to the other stores when one of the names in the
command is wrong.

## Domain quick reference

- Two separate things decide whether a packet lands in a store: the
  store's storage function, which is a switch, and the store's report
  type list, which is a filter. A store can be switched on and store
  nothing because its type list is empty.
- The switch is per store. There is no global recording state, so a
  command that means "start recording" is a list of stores and every
  one of them succeeds or fails on its own.
- Partial failure is the whole point of the clause. A command naming
  nine stores where the fourth identifier is a typo enables eight of
  them and notifies one failure. It does not enable zero.
- An enable on a store already storing is a success, not an error.
  The operator asked for a state and got it; reporting a failure would
  make a retry after a lost acknowledgement look like a fault.
- The report type list is a set. Adding a type already present is a
  success that changes nothing; deleting a type that is absent is a
  failure for that type, because the operator's picture of the store
  disagrees with the store.
- A report-type change never touches the switch. Adding a type to a
  running store leaves it running, so the operator does not lose the
  packets arriving during the edit.
- A store named twice in one command is a malformed command rather
  than two outcomes. The second occurrence cannot be acted on
  independently of the first, so there is no honest per-store result
  to report for it.

## Workflow

1. Normalize the held stores first and reject the set outright on a
   duplicate store identity, an unknown storage status or a report
   type list that repeats a type. A store set that cannot be trusted
   produces no outcomes.
2. Normalize each command before touching anything: the action must be
   one of enable, disable, add types or delete types, the store list
   must be non-empty and free of repeats, and only the two type
   actions may carry report types.
3. Walk the named stores in command order. A name the application does
   not hold produces a rejection for that store and a notification,
   and the walk continues.
4. Apply the action to each store it does name, recording whether the
   store actually moved so an accepted no-change stays distinguishable
   from a real transition.
5. For a delete of report types, remove the ones the store holds and
   report the ones it did not, rather than failing the whole edit.
6. Assemble the resulting configuration -- storage status and type
   list per store, in store order, with the count of stores actually
   storing -- and close with the verdict plus every rejected pair of
   action and store.

## Pitfalls

- Rejecting the whole command on the first unknown store. The typo in
  the ninth identifier then costs eight recorders that nobody notices
  are off until the pass is over and the downlink is empty.
- Reporting an enable on an already-storing store as an error. The
  ground retries after a lost acknowledgement and gets a fault report
  for a spacecraft that is doing exactly what was asked.
- Silently dropping a rejection. Partial success is only safe when the
  part that failed is named; an unnotified failure is worse than a
  whole-command rejection because nobody is looking for it.
- Treating the report type list as a sequence rather than a set. The
  same type added twice then gets stored twice or removed once, and
  the store's behaviour depends on the command history.
- Stopping a running store to edit its type list. The packets that
  arrive during the edit are gone, and nothing in the downlink marks
  the gap.
- Expanding a store named twice into two independent outcomes. The
  second is not independent, so whatever it reports is invented.
- Computing the storing total from the command rather than from the
  resulting configuration. It then agrees with the intent instead of
  the state, and a partially rejected command reads as fully applied.

## Behavior contract (gate 3)

The store and command normalization, per-store switching with the
accepted-no-change outcome, report-type add and delete with the absent
type rejection, partial failure across a multi-store command, the
resulting configuration report and the run verdict are exercised by
the gate 3 contract test:
scripts/test_e7041_controlling_the_packet_store_storage_function.py
against
scripts/e7041_controlling_the_packet_store_storage_function_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_controlling_the_packet_store_storage_function.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

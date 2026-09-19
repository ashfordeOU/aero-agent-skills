---
name: e7041-report-the-status-of-each-packet-store
description: "Produce the status report covering every packet store the on-board application holds under ECSS-E-ST-70-41C clause 6.15.3.6. Use when the question is what the stores are doing rather than how they are configured: emitting one entry per store held with no identifier list accepted, carrying the storage function state and both retrieval states, deriving each activity from those three rather than from a stored field, surfacing a dormant store still holding packets, and carrying totals a receiver can check a truncated transfer against. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, packet-store-status-report, packet-store-storage-state, packet-store-retrieval-state, dormant-packet-store-content."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-report-the-status-of-each-packet-store, packet-store-status-report, packet-store-storage-state, packet-store-retrieval-state, dormant-packet-store-content]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Report the Status of Each Packet Store (space-systems/ecss/e7041-report-the-status-of-each-packet-store)

Use when the task is the status-reporting request of ECSS-E-ST-70-41C
clause 6.15.3.6 -- reporting, for every packet store the on-board
application holds, whether its storage function is on and whether a
retrieval is reading it out, with the four normative items that clause
places on the report.

## Domain quick reference

- This request and the configuration report answer different questions
  about the same objects. One says what the stores ARE -- capacity,
  type, virtual channel. This one says what they are DOING.
- It covers the whole set by construction. There is no identifier
  list, because an operator asking which recorders are running cannot
  be expected to name the one they forgot to switch on.
- Three states per store make the answer: the storage function, the
  open retrieval and the by-time-range retrieval. A store can be in
  any combination of storing and retrieving, including both at once.
- The activity is derived from those three, not stored. A stored
  activity field drifts away from the switches, and the report then
  carries the drift to the ground as the state of the spacecraft.
- A store carrying both retrieval kinds at once is not a status to
  report; it is an invalid store, because one read cursor cannot serve
  two requests, and it is rejected rather than described.
- A dormant store still holding packets is a legal state and a blind
  spot: nothing is writing to it and nothing is reading it out, so the
  content sits there until somebody notices. It is surfaced as a
  finding rather than left silent.
- Storage off with a suspended open retrieval is worse than dormant.
  The retrieval still pins the store against overwrite and nothing is
  draining it, so the store is doing neither job while holding the
  protection that stops another one starting.
- The totals -- store count and storing count -- exist so a receiver
  can detect a truncated transfer without knowing what the report
  should have contained.

## Workflow

1. Normalize the held stores first and reject the set outright on a
   duplicate identity, an unknown storage or retrieval state, a
   negative packet count, or a store claiming both retrieval kinds.
   An invalid set produces no report.
2. Derive each store's activity from the three states, taking the
   both-at-once case first so a store that is storing and retrieving
   is not reported as merely one of them.
3. Assemble one entry per store in held order, each carrying the
   identifier, the storage state, both retrieval states, the derived
   activity and the packet count.
4. Reconcile any declared activity against the derived one, and raise
   a finding for a dormant store holding packets and for storage off
   under a suspended retrieval.
5. Compute the store, storing and retrieving totals from the assembled
   entries rather than from the input.
6. Verify the assembled report against its own totals and close with
   the verdict plus the stores that were inconsistent.

## Pitfalls

- Reporting a stored activity field. It was written by whatever last
  updated it, and the ground takes it as the current state of the
  recorder.
- Reducing the three states to one. A store that is storing and being
  read out at the same time is the normal state during a pass, and
  flattening it hides whichever half the implementation dropped.
- Accepting an identifier list for this report. Narrowing it to the
  stores the requester already suspects defeats the only reason a
  whole-set status sweep exists.
- Describing a store that claims both retrieval kinds instead of
  rejecting it. Whatever status comes back is invented, because the
  state it describes cannot exist.
- Letting a dormant store holding packets pass silently. It is legal,
  it is also how a recorder full of an anomaly nobody downlinked ends
  up overwritten weeks later.
- Treating a suspended open retrieval as no retrieval. It still holds
  the overwrite protection, so the store is unavailable to a new
  retrieval while reporting nothing in progress.
- Computing the totals from the input rather than from the assembled
  entries. They then agree with the intent instead of the content, and
  a truncation passes the check that was added to catch it.

## Behavior contract (gate 3)

The store normalization, activity derivation across the four
combinations, declared versus derived reconciliation, the dormant and
suspended findings, whole-set assembly in held order, the totals and
the self-consistency check are exercised by the gate 3 contract test:
scripts/test_e7041_report_the_status_of_each_packet_store.py against
scripts/e7041_report_the_status_of_each_packet_store_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_report_the_status_of_each_packet_store.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

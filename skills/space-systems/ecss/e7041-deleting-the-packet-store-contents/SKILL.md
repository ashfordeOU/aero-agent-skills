---
name: e7041-deleting-the-packet-store-contents
description: "Execute the deletion of on-board packet store contents up to a named storage time under ECSS-E-ST-70-41C clause 6.15.3.7. Use when a recorder is being emptied after a pass and the question is what survives the cut: removing inclusively at the named time, refusing a store a by-time-range retrieval is walking, clamping the cut to an open retrieval cursor so unsent packets are kept and the clamp is reported, accepting a time older than everything held as an empty delete, and reporting the freed capacity and the new oldest packet. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, packet-store-content-deletion, delete-up-to-storage-time, deletion-clamped-by-open-retrieval, packet-store-freed-capacity."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-deleting-the-packet-store-contents, packet-store-content-deletion, delete-up-to-storage-time, deletion-clamped-by-open-retrieval, packet-store-freed-capacity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Deleting the Packet Store Contents (space-systems/ecss/e7041-deleting-the-packet-store-contents)

Use when the task is the content deletion of ECSS-E-ST-70-41C clause
6.15.3.7 -- throwing away everything a named packet store holds at or
before a given storage time, and deciding what the command must leave
alone because something is still reading it.

## Domain quick reference

- This is the only irreversible operation in the storage and retrieval
  service. Everything else can be re-sent, re-read or re-started; a
  deleted packet is gone and no later report will mention it.
- The cut is inclusive. The operator names the storage time of the
  last packet they have safely on the ground, so that packet is
  exactly the one that must go.
- A store being read by a by-time-range retrieval refuses the
  deletion. The retrieval is walking the region the command would
  remove, so there is no order of operations that gives both the
  deletion and the downlink what they were promised.
- A store being read by an open retrieval does not refuse. It deletes
  up to the retrieval's cursor and keeps what has not been sent, which
  is the useful answer during a pass -- but the caller is told the cut
  landed earlier than they asked for.
- A packet sitting exactly on the cursor is kept. It is the next one
  the retrieval will send, so it is unsent, and the clamp is on the
  unsent side of the boundary.
- Deleting nothing is a success. A named time older than everything
  held says something true about the store and does not need to be
  reported as a failure.
- The freed capacity and the new oldest packet go back with the
  result. Without them the ground cannot confirm the recorder is
  actually emptier, only that the command was accepted.
- Partial failure is per store. One name in the list being wrong, or
  one store being read out, must not stop the other recorders from
  being emptied.

## Workflow

1. Normalize the held stores first: packets in non-decreasing storage
   time with no repeated identity and a positive size, and no store
   claiming both retrieval kinds at once.
2. Normalize the command before touching anything, rejecting a
   non-finite or negative storage time and a store named twice.
3. Walk the named stores, rejecting a name the application does not
   hold for that store alone and continuing with the rest.
4. Refuse the deletion on a store a by-time-range retrieval is
   walking, leaving its content untouched and notifying the refusal.
5. Select the packets at or before the named time, then clamp the
   selection below any open retrieval cursor and record whether the
   clamp changed anything.
6. Remove the selected packets, then report the deleted count, the
   freed octets, the retained count and the new oldest storage time,
   and close with the verdict and every refusal named.

## Pitfalls

- Making the cut exclusive. The operator names the last packet they
  hold on the ground and it stays on board forever, so every delete
  leaves one more packet behind than the one before it.
- Deleting through an open retrieval's cursor. The ground is handed a
  downlink that stops mid-record, and nothing in the stream marks
  where the packets went.
- Refusing every deletion on a store under an open retrieval. An open
  retrieval runs for the whole pass, so the recorder never gets
  emptied and starts discarding at the input instead.
- Clamping at the cursor inclusively. The packet on the cursor is the
  next one to be sent, so deleting it produces the very gap the clamp
  exists to prevent.
- Reporting an empty delete as a failure. Operators then retry with a
  later time to make the error go away and delete data they meant to
  keep.
- Rejecting the whole command when one named store is busy. The other
  recorders stay full, and the next pass loses their new packets.
- Returning success without the freed capacity. The ground has no way
  to tell an accepted deletion from an effective one, which is the
  only thing it actually needed to know.

## Behavior contract (gate 3)

The store and command normalization, inclusive selection at the named
time, the by-time-range refusal, the open-retrieval clamp with the
packet on the cursor kept, the empty-delete success, the freed octets
and new oldest time, partial failure over a multi-store command, the
content report and the run verdict are exercised by the gate 3
contract test:
scripts/test_e7041_deleting_the_packet_store_contents.py against
scripts/e7041_deleting_the_packet_store_contents_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_deleting_the_packet_store_contents.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

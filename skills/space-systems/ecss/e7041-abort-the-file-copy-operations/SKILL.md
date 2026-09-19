---
name: e7041-abort-the-file-copy-operations
description: "Determine what aborting an on-board file copy operation leaves behind under ECSS-E-ST-70-41C clause 6.23.5.4. Use when the task is cancelling one copy or every copy at once and accounting for the wreckage: removing the entry from the copy operation list rather than parking it, deleting a partially written target file so no truncated file survives the cancellation, returning the octets already landed to the target repository free space, tallying the transfer effort that has to be spent again, and refusing an abort that names an operation the list never held. Trigger: ecss, e-st-70-41c, pus-file-management, file-copy-abort-directive, abort-all-file-copies, partial-target-file-deletion, aborted-copy-octet-reclaim, copy-operation-list-removal."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-abort-the-file-copy-operations, file-copy-abort-directive, abort-all-file-copies, partial-target-file-deletion, aborted-copy-octet-reclaim, copy-operation-list-removal]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Aborting File Copy Operations (space-systems/ecss/e7041-abort-the-file-copy-operations)

Use when the task is the abort of file copy operations of
ECSS-E-ST-70-41C clause 6.23.5.4 -- cancelling a copy the on-board
service is part way through, and deciding what happens to the entry,
to the half-written target file and to the space it was using.

## Domain quick reference

- An abort is terminal, not a third lifecycle state. The entry leaves
  the copy operation list; it is not parked as "aborted" for the ground
  to trip over on the next status report.
- Both live states abort. A suspended copy is as abortable as a running
  one, and a paused transfer is exactly the kind that gets cancelled.
- A completed copy is not in the list, so asking to abort it is a
  lookup failure, not a state refusal. Those two reasons point the
  operator at different mistakes.
- The interesting decision is the target file, not the entry. A target
  that received no octets was never created and needs nothing; a target
  that received some is a partial file, and leaving it is worse than
  leaving nothing because a later reader cannot tell it from a good
  one.
- Deleting the partial target and reclaiming its octets are the same
  action seen twice. The space accounting has to move with the
  deletion, or the target repository stays short by the abandoned
  octets until someone reboots it.
- Octets discarded are worth reporting separately from operations
  aborted. Two aborts can cost thirty octets or thirty megabytes of
  downlink time, and only the octet figure says which.
- Abort-all is a loop, not a special case. It has to produce one
  outcome per entry, because an operator needs to know which copies it
  actually caught.

## Workflow

1. Validate each entry: a four-part copy key, a positive total, octets
   moved strictly below that total, and a state of running or
   suspended. Reject a list holding the same key twice.
2. Read the directive: abort against one named key, or abort-all
   against the list. A single abort without a key, and an abort-all
   with one, are input errors.
3. Resolve the key. An unmatched key is refused with that reason and
   changes nothing, including the octet tallies.
4. Compute the disposition of the target before touching the list: no
   action when no octets landed, delete-partial-target with the octet
   count when some did.
5. Remove the entry from the list.
6. Return the reclaimed octets to the target repository's free space,
   refusing a repository the accounting does not know.
7. For abort-all, repeat per entry over a copy of the list so removal
   during the loop cannot skip an entry.
8. Report the aborted and refused counts, the octets discarded, the
   octets reclaimed, the partial targets deleted and the entries left,
   and raise a finding on each of those three conditions.

## Pitfalls

- Keeping an aborted entry in the list with an aborted flag. Every
  later count of active copies then has to remember to exclude it, and
  one place eventually will not.
- Leaving the partial target file in place. It has a plausible name and
  a wrong length, and nothing downstream marks it as incomplete.
- Deleting the partial file without returning its octets. The
  repository reports less free space than it has, and the next copy is
  refused for room that exists.
- Reporting a refused abort as a successful one. The ground believes a
  transfer it is still competing with has stopped.
- Counting operations and not octets. The cost of an abort is the
  transfer time to be spent again, which the entry count does not
  carry.
- Iterating the list itself while removing from it in an abort-all.
  Entries are skipped silently, and the outcome list is short without
  ever being wrong-looking.

## Behavior contract (gate 3)

The entry validation, duplicate key rejection, partial target
disposition, single and whole-list abort, list removal, octet reclaim
into the target repository, refusal of an unheld key, the abort tally
and the campaign findings are exercised by the gate 3 contract test:
scripts/test_e7041_abort_the_file_copy_operations.py against
scripts/e7041_abort_the_file_copy_operations_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_abort_the_file_copy_operations.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

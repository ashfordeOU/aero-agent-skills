---
name: e7041-on-board-file-attributes
description: "Assess the attributes of an on-board file under ECSS-E-ST-70-41C clause 6.23.3.4: validate the repository path, the file name, the current size, the allocated size and the lock status as one consistent record, derive the octets left inside the allocation and the occupancy, then decide whether a write of a given length or a delete is admissible against that record. Use when file size accounting, lock status handling or attribute reporting of an on-board file store is being designed or reviewed. Refuses a size past its allocation and a name carrying a path separator. Trigger: ecss, e-st-70-41c, pus-service-23, on-board-file-attributes, file-allocated-size, on-board-file-lock-status, file-occupancy-ratio, file-attribute-record."
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
  tags: [ecss, e-st-70-41c-scope, e7041-on-board-file-attributes, pus-service-23, on-board-file-management, file-allocated-size, on-board-file-lock-status, file-occupancy-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS PUS File Management — On-Board File Attributes (space-systems/ecss/e7041-on-board-file-attributes)

Use when the task is the attribute record of an on-board file of
ECSS-E-ST-70-41C clause 6.23.3.4 — what the record holds, when it is
self-consistent, and what it permits a write or a delete to do.

## Domain quick reference

- The record is five attributes read together: the repository the file
  sits in, the file name, the octets it currently holds, the octets it
  is allowed to grow to, and whether it is locked. Any four of them
  answer nothing on their own.
- The allocated size is a ceiling, not a hint. A current size above it
  is not a large file, it is an inconsistent record, and the right
  response is to refuse the record rather than to carry it forward and
  let a later write compute negative room.
- The lock is what makes a write or a delete inadmissible. It is not
  advisory and it is not a permission on the operator: an unlock is its
  own operation, and a request that would have succeeded on the same
  file unlocked is still refused while the lock is set.
- The room left is the allocation less the current size, and a write is
  admissible only when it fits that room exactly or with slack. A write
  that would land precisely on the allocation is admissible; it is the
  first octet past it that is not.
- Occupancy is a ratio, so a comparison against a near-full threshold
  absorbs representation error with a named tolerance. A file sitting
  exactly on the threshold counts as near full rather than falling
  either side of it depending on how the division rounded.
- The file name is one path component. A name carrying the path
  separator would silently reparent the file, which is why it is
  refused at the record rather than at the operation.

## Workflow

1. Validate the file name: non-empty, one component, no padding, within
   the model length limit.
2. Validate the repository path: rooted at the file store, no empty or
   padded component, no trailing separator.
3. Validate the record as a whole: a non-negative current size, a
   strictly positive allocation, a real boolean lock, and a size that
   does not exceed the allocation.
4. Derive the room left and the occupancy from the normalised record
   rather than from the raw input, so every derived number is computed
   on a record that has already been checked.
5. Decide a write: refuse on the lock first, then on the room, and
   report the size the file would reach when it is admissible.
6. Decide a delete: refuse on the lock, otherwise permit.
7. Summarise the store: totals, overall occupancy, the near-full files
   against the threshold, the locked files, and the files a pending
   write could not land on.

## Pitfalls

- Treating the allocation as advisory and letting the size pass it. Every
  derived number then goes wrong at once — the room left turns negative
  and the occupancy passes unity — and the first symptom appears far from
  the record that caused it.
- Checking the room before the lock. Both refuse the write, but the
  reason reported to the operator is then the wrong one, and a file that
  is merely full looks like a file that is locked.
- Refusing a write that exactly fills the allocation. The allocation is
  the size the file may reach, so the boundary write is the last
  admissible one, not the first inadmissible one.
- Comparing an occupancy against a threshold with a strict inequality. A
  file sitting exactly on the threshold then reports differently on two
  machines; the comparison needs the named tolerance.
- Allowing a path separator inside a file name. The name is one
  component; a separator inside it moves the file somewhere the
  repository path does not describe.

## Behavior contract (gate 3)

The name and repository path validation, record consistency check,
remaining room and occupancy derivation, write and delete admissibility,
lock handling and store summary are exercised by the gate 3 contract
test: scripts/test_e7041_on_board_file_attributes.py against
scripts/e7041_on_board_file_attributes_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_on_board_file_attributes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

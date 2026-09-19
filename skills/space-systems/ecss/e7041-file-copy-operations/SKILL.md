---
name: e7041-file-copy-operations
description: "Model the admission and the progress of an on-board file copy operation under ECSS-E-ST-70-41C clause 6.23.5.2. Use when the task is deciding whether a copy request may join the copy operation list, or explaining why one was turned away: confirming the source repository and file exist, the target repository is known and its file name still free, the destination has room for the whole file once the octets already in flight are counted, no identical pair is queued and the list has a spare entry, then moving octets until the file lands and the entry clears. Trigger: ecss, e-st-70-41c, pus-file-management, on-board-file-copy-operation, file-copy-operation-list, copy-source-target-repository, file-copy-duplicate-refusal, file-copy-target-room, file-copy-progress-octets."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-file-copy-operations, on-board-file-copy-operation, file-copy-operation-list, copy-source-target-repository, file-copy-duplicate-refusal, file-copy-target-room, file-copy-progress-octets]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — File Copy Operations (space-systems/ecss/e7041-file-copy-operations)

Use when the task is the file copy operations of ECSS-E-ST-70-41C clause
6.23.5.2 -- the on-board service that takes a request to duplicate a
file from one repository into another, decides whether that request can
become an entry in the copy operation list, and then moves the file
octet by octet until it lands.

## Domain quick reference

- A copy operation is named by four things, not two: the source
  repository, the source file, the target repository and the target
  file. Two of those four differing is enough to make a different
  operation, which is why the list is keyed on the whole quadruple.
- A copy is not a move. The source file is still there when the
  operation completes, so the space accounting only ever grows at the
  target end and a request that would be harmless as a move can still
  be refused for room.
- Free space at a target is derived from the capacity and the files
  held, never carried as a separate number. A stored free-space figure
  and a file list drift apart the first time anything writes without
  going through the accounting.
- Room has to be judged against the octets already in flight, not only
  against the files that have finished landing. Two copies admitted
  because each fits the empty target will both fail halfway when
  together they do not.
- Two operations writing the same target file name are a collision even
  when their sources differ. Whichever finishes last silently defines
  the content, so the second request is refused at admission rather
  than resolved at completion.
- A copy onto itself -- same repository, same file name -- is an input
  error. It is not a no-op to be absorbed quietly; it means the request
  was built wrong and the ground expects a file somewhere it will never
  appear.
- The copy operation list is bounded. Its fullness is a distinct
  refusal from a full target repository: one is a subservice resource,
  the other is storage, and an operator given a single "refused" cannot
  tell which to clear.

## Workflow

1. Validate the repositories: a positive capacity, named files with
   whole non-negative sizes, and a held total that does not already
   exceed the capacity.
2. Validate the request into a four-part copy key; a blank or padded
   repository or file name is an input error.
3. Confirm the source repository exists and holds the source file, and
   that the target repository exists.
4. Refuse a copy onto itself, and refuse a target file name that
   already exists in the target repository.
5. Refuse a request whose key is already in the list, and one whose
   target file name another queued operation is already writing.
6. Compare the source file size against the target free space less the
   octets already landed by running copies; refuse when it does not
   fit.
7. Refuse when the list already holds its capacity of entries, and give
   that refusal its own reason.
8. Admit the request as an entry carrying the total octets and zero
   moved, and advance it as octets are moved, refusing an advance that
   would overshoot the file size.
9. On the last octet, create the target file, drop the entry from the
   list, and leave the source untouched.
10. Report the list with per-entry progress, the accepted and refused
    requests of the campaign with their reasons, and the findings.

## Pitfalls

- Keying the list on the target path alone. Two different sources
  writing the same target then look like one operation, and the
  duplicate refusal never fires.
- Judging room against the target file list only. The octets of the
  copies already running are committed space; leaving them out admits
  a request that cannot finish.
- Collapsing every refusal into one message. A missing source file, a
  full target and a full operation list need three different actions
  from the ground, and one word for all three costs a pass.
- Creating the target file at admission. A file of the right name and
  the wrong length is worse than no file: a later reader cannot tell a
  copy in progress from a truncated one.
- Treating a copy onto itself as a harmless no-op. Absorbing it hides a
  malformed request that will keep being sent.
- Comparing progress as a float fraction against a threshold. Octets
  are exact integers; do the admission and completion tests on them and
  keep the fraction for the report only.

## Behavior contract (gate 3)

The repository validation, four-part keying, source and target
existence checks, copy-onto-itself refusal, duplicate and target
collision refusal, room-with-octets-in-flight check, list fullness
refusal, octet advance, completion and the campaign report are
exercised by the gate 3 contract test:
scripts/test_e7041_file_copy_operations.py against
scripts/e7041_file_copy_operations_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e7041_file_copy_operations.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

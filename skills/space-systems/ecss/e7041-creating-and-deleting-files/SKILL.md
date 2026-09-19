---
name: e7041-creating-and-deleting-files
description: "Validate the creation and deletion of on-board files under ECSS-E-ST-70-41C clause 6.23.4.1: replay a run of create and delete requests over a repository, refuse a duplicate file name, an allocation past the per-file ceiling or past the free space, a repository already at its file limit, a delete of an absent file, a locked file or a file held open by a transfer, and account the free space after every request. Use when the acceptance rules, free space accounting or refusal reporting of on-board file create and delete requests are being designed or reviewed. Trigger: ecss, e-st-70-41c, pus-service-23, on-board-file-creation, on-board-file-deletion, repository-free-space, locked-file-delete-refusal, duplicate-file-name-refusal."
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
  tags: [ecss, e-st-70-41c-scope, e7041-creating-and-deleting-files, pus-service-23, on-board-file-management, on-board-file-creation, on-board-file-deletion, repository-free-space]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS PUS File Management — Creating and Deleting Files (space-systems/ecss/e7041-creating-and-deleting-files)

Use when the task is the create and delete requests of the on-board file
management service of ECSS-E-ST-70-41C clause 6.23.4.1 — when each
request is accepted, on what stated condition it is refused, and what the
repository looks like afterwards.

## Domain quick reference

- A repository is bounded three ways at once: a total capacity, a
  ceiling on any single file, and a ceiling on the number of files it
  holds. A create request has to clear all three, and the one it fails
  on is the reason the operator needs to see.
- A create reserves an allocation, it does not write data. The free
  space of the repository therefore moves on the create, not on the
  first write, and an allocation that exactly consumes the remaining
  free space is admissible.
- A delete is refused on three stated conditions: the file is not there,
  it is locked, or it is held open by a transfer in progress. The last
  of these is the one most often missed, and it is the one whose absence
  corrupts a transfer rather than merely losing a file.
- A refused request changes nothing. The repository after a rejection is
  the repository before it, which is what lets a run of requests be
  replayed and each verdict read against the free space at that point.
- Order matters inside a run. A create that fails for want of space can
  succeed after a later delete frees it, so the same set of requests in
  two orders is two different outcomes and the run is evaluated in the
  order it is issued.
- The file name is one path component. A name carrying the path
  separator is refused as malformed input rather than accepted and
  reparented.

## Workflow

1. Validate the repository description: a rooted path, a positive
   capacity, a per-file ceiling that is not larger than the capacity, a
   positive file limit, and declared files that neither breach the
   per-file ceiling nor over-reserve the capacity.
2. Validate each request: a well-formed one-component file name, and for
   a create a strictly positive allocation. Malformed input is an error,
   not a refusal verdict.
3. Apply a create in this order: duplicate name, repository at its file
   limit, allocation past the per-file ceiling, allocation past the free
   space. Record the first condition it fails.
4. Give a new file a default state: unlocked and not held open.
5. Apply a delete in this order: absent, locked, held open by a
   transfer.
6. Replay the run in order, carrying the repository forward only on an
   accepted request, and record per request the verdict, the reason and
   the free space after it.
7. Report the opening and closing free space, the reserved octets, the
   surviving file names, the accepted and refused counts, and any
   finding, including a repository that has reached its file limit.

## Pitfalls

- Accounting the free space on the first write rather than on the
  create. Two creates then both appear to fit the same octets, and the
  repository over-commits its capacity.
- Checking only the capacity. A repository with plenty of free space can
  still refuse a create because it holds its maximum number of files or
  because the allocation is past the per-file ceiling.
- Letting a rejected request change the repository. A partially applied
  create leaves a reservation with no file behind it, and the free space
  never comes back.
- Deleting a file that a transfer is holding open. The file disappears
  underneath an active transfer, which is a worse failure than refusing
  the delete and is invisible until the transfer fails.
- Evaluating a run as a set. Requests are ordered, and a create refused
  for want of space may be exactly the one a later delete would have
  made room for.
- Reporting a generic failure for a refused request. The condition that
  refused it is the actionable part; a bare rejection tells the operator
  nothing about whether to free space, unlock, or rename.

## Behavior contract (gate 3)

The name validation, repository construction, reserved and free space
accounting, create acceptance order, delete refusal conditions, run
replay and final repository summary are exercised by the gate 3 contract
test: scripts/test_e7041_creating_and_deleting_files.py against
scripts/e7041_creating_and_deleting_files_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_creating_and_deleting_files.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

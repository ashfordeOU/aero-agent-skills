---
name: e7041-managing-directories
description: "Perform and adjudicate the four requests that change the shape of an on-board repository tree under ECSS-E-ST-70-41C clause 6.23.4.5. Use when a create, delete, rename or move against a spacecraft file system was refused and the operator needs the reason rather than a retry: refusing a delete of anything holding a file or a sub-repository because nothing on board is recoverable, separating a rename that changes the last segment from a move that changes the parent, re-pathing the whole subtree under either, catching a move into a target's own subtree before it detaches it, and enforcing the declared depth at the request. Trigger: ecss, e-st-70-41c, pus-file-management, on-board-repository-tree, create-sub-repository, delete-non-empty-repository, move-repository-subtree, repository-depth-limit."
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
  tags: [ecss, e-st-70-41-file-management-scope, e7041-managing-directories, on-board-repository-tree, create-sub-repository, delete-non-empty-repository, move-repository-subtree, repository-depth-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Managing Directories (space-systems/ecss/e7041-managing-directories)

Use when the task is the directory management of ECSS-E-ST-70-41C
clause 6.23.4.5 -- creating, deleting, renaming and moving the
sub-repositories of an on-board file system, where the happy path is
a dictionary insertion and the refusals are the whole subject.

## Domain quick reference

- Four requests act on structure rather than content: create a
  sub-repository under an existing parent, delete one, rename one in
  place, move one under a different parent.
- A delete is refused unless the target holds neither a file nor a
  sub-repository. There is no undo on board and no second copy, so
  the empty-only rule is the only thing that forces an operator to
  look inside before the content goes. A helpful recursive delete
  removes the guard entirely.
- The refusal has to say what was inside. "Not empty" sends the
  operator back to guess; two files and one sub-repository tells
  them what the next request is.
- A rename changes the last segment and keeps the parent. A move
  keeps the name and changes the parent. They are not the same
  request with different arguments, and each fails in a way the
  other cannot.
- Both re-path everything underneath. A subtree that keeps its old
  paths after its parent moved is a tree with two answers for one
  repository.
- A move into the target's own subtree is the one failure that
  corrupts rather than refuses: the subtree detaches from the root
  and nothing reaches it again. Catch it before applying, and note
  that moving a repository onto itself is the same defect.
- The root repository cannot be deleted, renamed or moved. It is the
  anchor every path is expressed against.
- Maximum depth is declared and enforced at the request. A create or
  a move that would exceed it is refused now, not discovered later by
  a path too long for the field that carries it.
- A move checks the depth of the deepest repository in the subtree,
  not of the repository being moved. Moving a shallow parent can push
  a grandchild past the cap.
- Name collisions span both kinds. A new sub-repository may not take
  the name of a file in the same parent, nor of a sibling.

## Workflow

1. Validate every segment and normalise every path before comparing
   anything; two spellings of one path are one repository.
2. Validate the tree: every non-root repository has its parent
   present, no duplicate file names, nothing past the declared depth.
3. For a create, resolve the parent, reject a name already used by a
   file or a sibling, then check the resulting depth and path length.
4. For a delete, refuse the root, refuse an unknown path, then refuse
   a non-empty target and report its file and sub-repository counts.
5. For a rename, refuse the root, accept a rename to the same name as
   a no-op, reject a sibling collision, and re-path the subtree.
6. For a move, refuse the root, resolve the destination parent,
   reject a destination inside the target's own subtree, reject a
   name collision, and only then check the deepest descendant against
   the depth cap.
7. Apply a plan step by step against the tree each step produced, and
   report applied and refused counts and the deepest depth reached.

## Pitfalls

- Recursively deleting to make a delete succeed. The refusal was the
  safety feature and the content is not recoverable.
- Reporting "not empty" without the counts. The operator reissues
  blind and the second refusal teaches nothing new.
- Treating a move as a rename with a path in it. The two collision
  checks are against different parents.
- Moving a subtree without re-pathing it. Half the tree answers to a
  parent that no longer exists.
- Allowing a move into the target's own subtree. The subtree is
  detached and nothing addresses it afterwards.
- Checking the depth of the moved repository instead of its deepest
  descendant. The cap is breached one level down.
- Testing containment on a raw string prefix. A sibling whose name
  begins with the target's name is dragged along.
- Applying a plan against the original tree each step. Later steps
  are then decided against a state that never existed.

## Behavior contract (gate 3)

The segment and path mechanics, whole-segment containment, tree and
parent validation, depth enforcement, create with file and sibling
collision checks, empty-only delete with its counts, root protection,
rename versus move with subtree re-pathing, the move-into-own-subtree
refusal, the deepest-descendant depth check and the step-by-step plan
report are exercised by the gate 3 contract test:
scripts/test_e7041_managing_directories.py against
scripts/e7041_managing_directories_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e7041_managing_directories.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

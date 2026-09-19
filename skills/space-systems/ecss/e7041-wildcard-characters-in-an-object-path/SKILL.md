---
name: e7041-wildcard-characters-in-an-object-path
description: "Evaluate an object path that carries a wildcard character under ECSS-E-ST-70-41C clause 6.23.3.3: split the path into its repository and directory components, accept the wildcard only as a whole component so it never spans a separator, expand the pattern over the object paths currently on board, and decide whether an operation that must address a single object may proceed on that expansion. Use when wildcard handling, path matching or fan-out limits of an on-board file management request are being designed or reviewed. Refuses a component mixing the wildcard with literal characters. Trigger: ecss, e-st-70-41c, pus-service-23, on-board-file-management, object-path-wildcard, wildcard-component-matching, object-path-expansion, single-object-file-operation."
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
  tags: [ecss, e-st-70-41c-scope, e7041-wildcard-characters-in-an-object-path, pus-service-23, on-board-file-management, object-path-wildcard, wildcard-component-matching, single-object-file-operation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS PUS File Management — Wildcards in an Object Path (space-systems/ecss/e7041-wildcard-characters-in-an-object-path)

Use when the task is the wildcard rule of the object path of
ECSS-E-ST-70-41C clause 6.23.3.3 — deciding what a wildcard in a file
management request stands for, which on-board objects the path then
addresses, and whether the requested operation may act on that set.

## Domain quick reference

- An object path names a repository, the directories beneath it and, for
  a file operation, the file. The wildcard, where the subservice
  declares one, stands for any value of one component of that path.
- The wildcard is a whole component. It does not span a separator, so a
  pattern matches only a candidate path with the same number of
  components: a wildcard in the file position does not reach into a
  subdirectory, and a wildcard in a directory position does not swallow
  the rest of the path.
- A component that mixes the wildcard with literal characters is not a
  partial match, it is a malformed component. Accepting it quietly
  introduces a second matching language that the flight side and the
  ground side will not implement identically.
- The wildcard character has to be tellable apart from a name. A name
  character or the path separator cannot serve as the wildcard, and a
  stored object whose own name carries the wildcard character is a
  contradiction the expansion refuses.
- Expansion is against the objects that exist right now. A wildcard that
  happens to resolve to exactly one object today resolves to more the
  moment another object is created, so a single-object operation issued
  through a wildcard is a standing hazard even when it succeeds once.
- Whether an expansion of more than one object is allowed at all depends
  on the operation, not on the path. An operation that must address a
  single object refuses a wider expansion; a fan-out operation is held
  instead to its declared limit.

## Workflow

1. Validate the declared wildcard character: one character, not the path
   separator, and not a character a name could contain.
2. Split the object path into components. Refuse an empty path, an empty
   component, a trailing separator, a padded component, and a path or
   component past the model limits.
3. Categorize each pattern component as the wildcard or a literal name,
   refusing any component that mixes the two.
4. Match the pattern against each candidate object path component by
   component, requiring equal component counts so the wildcard cannot
   cross a separator.
5. Expand the pattern over the objects on board and return the matches in
   a stable order.
6. Decide the request: accept a single-object operation only on exactly
   one match, hold a fan-out operation to its declared limit, and report
   a wildcard that resolved to a single object as a standing hazard.

## Pitfalls

- Letting the wildcard span separators. A pattern meant to address the
  files of one directory then reaches every file beneath it, and a
  delete issued that way removes objects nobody named.
- Supporting a partial wildcard inside a component. It looks convenient
  and it is the fastest way to have the ground expansion and the on-board
  expansion disagree about which objects a request covers.
- Comparing a pattern against a candidate of a different depth. Without
  the equal-component-count rule the match silently becomes a prefix
  match, which is a different operation.
- Reading a one-object expansion as a fully qualified path. The path is
  still a pattern; the set it addresses is a property of the file store
  at that instant, not of the request.
- Choosing a wildcard character a file name could contain. Every path
  then becomes ambiguous, and no validation downstream can recover the
  operator's intent.

## Behavior contract (gate 3)

The wildcard declaration check, path splitting, whole-component wildcard
rule, mixed-component refusal, equal-depth path matching, expansion over
the on-board objects and the single-object and fan-out decisions are
exercised by the gate 3 contract test:
scripts/test_e7041_wildcard_characters_in_an_object_path.py against
scripts/e7041_wildcard_characters_in_an_object_path_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_wildcard_characters_in_an_object_path.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

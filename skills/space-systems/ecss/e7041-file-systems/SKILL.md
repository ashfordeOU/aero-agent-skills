---
name: e7041-file-systems
description: "Define and audit the on-board file system model every other file management request is addressed against, under ECSS-E-ST-70-41C clause 6.23.5.1. Use when ground paths will not resolve against a spacecraft and the declaration itself is suspect: deciding flat against hierarchical, resolving an object only as a repository path plus a name within it, enforcing the declared separator, name charset, octet caps and depth at the identifier, and catching declarations that contradict themselves — flat with a depth above one, a separator inside the permitted charset, a depth unreachable within the path cap, or case-folded names that alias two ground objects onto one. Trigger: ecss, e-st-70-41c, pus-file-management, on-board-file-system-model, flat-versus-hierarchical-repository, repository-path-plus-file-name, file-name-octet-cap, case-insensitive-name-aliasing."
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
  tags: [ecss, e-st-70-41-file-management-scope, e7041-file-systems, on-board-file-system-model, flat-versus-hierarchical-repository, repository-path-plus-file-name, file-name-octet-cap, case-insensitive-name-aliasing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — File Systems (space-systems/ecss/e7041-file-systems)

Use when the task is the file system model of ECSS-E-ST-70-41C clause
6.23.5.1 -- two normative items, and every other request in the file
management service inherits both: what a file system is made of, and
how one object in it is named.

## Domain quick reference

- A file system is a set of repositories. A repository holds files
  and, when the file system is hierarchical, sub-repositories.
- An object is addressed by two things. A repository is a path; a
  file is that path plus a name within it. A name alone is not an
  address, because the same name in two repositories is two files.
- Flat or hierarchical is a property of the on-board implementation,
  not of the request. A flat system keeps every path to one segment.
  A ground tool that assumes nesting against a flat system builds
  paths that can never resolve, and the error surfaces as a missing
  repository rather than as the model mismatch it is.
- The declaration sets the limits every later request inherits: the
  separator, the permitted name characters, the name and path octet
  caps, the maximum depth, and whether names differ by case.
- A declaration can contradict itself, and that is worth catching
  before any path is built. Flat with a depth above one. Hierarchical
  with a depth of one. A separator that is also a permitted name
  character, so a legal name splits a path. A path cap too small for
  the declared depth even at one octet per segment. A path cap below
  the name cap.
- Caps are in octets, not characters. A name inside the character
  count can still exceed the field carrying it once encoded.
- Case folding is the quiet defect. A file system that does not
  distinguish case holds one object where a case-sensitive ground
  model holds two, so a create the ground believes is new overwrites
  something. Report the aliasing; it is never visible in a reply.
- Depth is checked against the effective depth, which a flat system
  pins at one whatever its declaration says.

## Workflow

1. Validate the declaration: known kind, a single-character
   non-control separator, positive depth and octet caps, a non-empty
   charset if one is given, a boolean case flag.
2. Derive the effective maximum depth -- one for a flat system, the
   declared value for a hierarchical one.
3. Audit the declaration for the self-contradictions above and
   report each as its own finding rather than one "invalid".
4. Split a path on the declared separator, rejecting an empty inner
   segment, and validate every segment as a name.
5. Resolve an object: reject a nested path on a flat system before
   the depth test, so the reason names the model and not the number.
6. Check each name and the whole path against the octet caps by
   encoded length, then the charset if one is declared.
7. Canonicalise the identifier through the case rule, and over a set
   of objects report how many distinct objects the resolved
   identifiers actually name.

## Pitfalls

- Addressing a file by name alone. It resolves against the wrong
  repository the first time two repositories share a name.
- Assuming hierarchy. Every nested path against a flat system fails,
  and the failure looks like a missing repository.
- Trusting a declaration because each field is individually legal.
  The contradictions are between fields.
- Measuring a name in characters. A multi-octet name passes the
  check and overruns the field.
- Treating a case-insensitive file system as merely inconvenient. It
  silently merges two ground objects into one.
- Testing depth against the declared value on a flat system. The
  effective depth is one and the declared number is the defect.
- Reporting one rejection reason for every failed identifier. The
  model mismatch, the depth, the octet caps and the charset send the
  operator to four different fixes.

## Behavior contract (gate 3)

The declaration validation, effective depth for flat and hierarchical
systems, the five self-contradiction findings, separator-driven split
and join, case-folding collision detection, repository versus file
identifiers, the flat-system nested-path rejection ahead of the depth
test, octet-measured caps, charset enforcement and the distinct versus
aliased object counts are exercised by the gate 3 contract test:
scripts/test_e7041_file_systems.py against
scripts/e7041_file_systems_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_file_systems.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e50-spacecraft-and-link-identification
description: "Validate that every spacecraft and every space link in a communications design is identified unambiguously, under ECSS-E-ST-50C clause 5.6.13.1. Check each spacecraft identifier fits the field width the chosen transfer frame version provides, is not the reserved all-ones pattern meaning no spacecraft, and collides with nothing else in its own namespace; check each link identity of spacecraft, direction and physical channel is unique; and report namespace headroom and the next assignable identifier. Use when assigning or reviewing spacecraft and link identifiers. Trigger: ecss, e-st-50-communications, spacecraft-identifier-assignment, space-link-identity-uniqueness, transfer-frame-version-identifier-width, reserved-all-ones-spacecraft-identifier, spacecraft-identifier-namespace-headroom."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.6.13.1
    items: [a]
    relation: implements
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-spacecraft-and-link-identification, spacecraft-identifier-assignment, space-link-identity-uniqueness, transfer-frame-version-identifier-width, reserved-all-ones-spacecraft-identifier, spacecraft-identifier-namespace-headroom]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Spacecraft and Link Identification (space-systems/ecss/e50-spacecraft-and-link-identification)

Use when spacecraft and space link identifiers are being assigned or reviewed,
per ECSS-E-ST-50C clause 5.6.13.1 — whether a receiving entity can say whose
data it holds and which link delivered it.

## Domain quick reference

- Unambiguous means three separate things, and a design can fail any one
  of them alone. The identifier fits the field it is carried in, it is
  not the reserved pattern, and nothing else in the same namespace has
  it.
- The field width comes from the transfer frame version, not from the
  mission. The same number is a legal identifier under one version and
  does not fit at all under another, so the version has to be settled
  before the numbers are handed out.
- The all-ones pattern is not an identifier. It means no spacecraft is
  identified, so a namespace planned against the raw field capacity runs
  out one spacecraft earlier than the plan says.
- A namespace is per frame version. Two spacecraft carrying the same
  number under different frame versions are distinguishable, and calling
  that a collision blocks an assignment that was fine.
- A link is not identified by its name. It is identified by the
  spacecraft it serves, the direction it runs in and the physical channel
  it occupies, and two links matching on all three cannot be told apart
  no matter what the schedule calls them.
- Headroom is part of the answer. A namespace with two identifiers left
  is a constraint on the next mission phase, and it is invisible unless
  the assessment reports it.

## Workflow

1. Settle the transfer frame version for each spacecraft first. It
   determines the field width, and every identifier check depends on it.
2. Declare each spacecraft with its name, frame version and identifier.
   Reject a float or a boolean rather than coercing it — a bit field
   holds integers, and a coerced value hides where it came from.
3. Check each identifier against the field: not negative, inside the
   width, and not the reserved all-ones pattern.
4. Group the identifiers by frame version and look for collisions inside
   each group only. A cross-namespace match is not a collision.
5. Declare each link with the spacecraft it serves, its direction and its
   physical channel, build the identity from those three, and name the
   frame field that carries it alongside the spacecraft identifier, so
   that a frame taken off a space-ground exchange on its own says which
   spacecraft it came from and which link brought it.
6. Report a link naming an undeclared spacecraft separately from a link
   identity collision. One is a missing declaration, the other is two
   links that cannot be told apart.
7. Report the remaining assignable identifiers per namespace, and give
   the lowest free one when a new assignment is needed. Raise on an
   exhausted namespace rather than returning the reserved pattern.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.6.13.1a | 5 |

## Pitfalls

- Planning a namespace against two to the width. The reserved all-ones
  pattern is not assignable, and the plan is one identifier optimistic
  from the start.
- Assigning identifiers before the frame version is fixed. A change of
  version narrows the field and silently invalidates part of the set.
- Treating the same number under two frame versions as a clash. They sit
  in different namespaces and are distinguishable.
- Identifying a link by the name on the schedule. Two links with
  different names and the same spacecraft, direction and channel are the
  same link as far as a receiver is concerned.
- Accepting a link that names a spacecraft nobody declared. It reads as a
  typo and is usually a segment that never got into the identifier plan.
- Returning something when the namespace is exhausted. A reserved pattern
  or an out-of-field value handed back as an assignment is worse than the
  error it replaced.

## Behavior contract (gate 3)

Frame version validation and field widths, capacity with the reserved
all-ones pattern excluded, identifier range and type checking, direction
and link normalisation, the three-part link identity, per-namespace
collision detection, undeclared-spacecraft links, duplicate names,
namespace headroom and the next assignable identifier with exhaustion
raising are exercised by the gate 3 contract test:
scripts/test_e50_spacecraft_and_link_identification.py against
scripts/e50_spacecraft_and_link_identification_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_e50_spacecraft_and_link_identification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

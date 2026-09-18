---
name: e50-telecommand-destination-identification
description: "Verify that every telecommand on a shared uplink names its recipient unambiguously under ECSS-E-ST-50C clause 5.4.10: check the spacecraft-identifier field width against the address space it provides, measure the minimum pairwise Hamming separation of the assigned identifiers and derive the bit errors that separation detects and corrects, confirm each command names a declared on-board application, and refuse an unset or beam-wide destination on a command never declared broadcast-safe. Use when a constellation identifier plan, a rideshare uplink or a command dictionary is reviewed. Trigger: ecss, e-st-50c-clause-5-4-10, telecommand-destination-identification, spacecraft-identifier-hamming-separation, telecommand-application-identifier, co-visible-constellation-addressing, broadcast-telecommand-safety."
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
  tags: [ecss, e-st-50-communications-scope, e50-telecommand-destination-identification, e-st-50c-clause-5-4-10, telecommand-destination-identification, spacecraft-identifier-hamming-separation, telecommand-application-identifier, co-visible-constellation-addressing, broadcast-telecommand-safety]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications -- Telecommand Destination Identification (space-systems/ecss/e50-telecommand-destination-identification)

Use when the task is clause 5.4.10 of ECSS-E-ST-50C: establishing that
a telecommand says which spacecraft, and which application inside it, is
meant to act. The failure guarded against is a command executed by the
wrong recipient -- a constellation neighbour, a rideshare companion, a
formation partner sitting in the same ground-station beam.

## Domain quick reference

- Uniqueness is not separation. Two identifiers that differ by one bit
  are unique and still one channel error apart, so a flipped bit turns a
  command for one spacecraft into a valid command for another. The
  quantity that matters is the minimum pairwise Hamming distance across
  the whole co-visible set.
- Separation converts directly into protection: a set separated by d
  bits always detects d-1 bit errors and always corrects the floor of
  (d-1)/2. Sequential numbering across a constellation gives d = 1,
  which detects nothing, and it is the default an identifier plan falls
  into when nobody measures it.
- Occupancy is the other half of the picture. A wide field with three
  assignments has room to space them out; a nearly full field cannot be
  given separation without widening the field, so the two numbers are
  read together when the plan is set rather than after launch.
- The spacecraft identifier alone does not finish the addressing. A
  command also names the on-board application that acts on it, and an
  application identifier not declared on board is as much a routing
  failure as a wrong spacecraft -- it simply fails inside the right
  spacecraft instead of outside it.
- A beam-wide destination is a deliberate decision, not a default. Time
  synchronisation legitimately goes to everything in the beam; a
  manoeuvre does not. Broadcast is therefore treated as a property the
  command has to declare, and an undeclared broadcast is a finding.

## Workflow

1. Validate the identifier field width and confirm every assigned
   identifier fits inside the address space that width provides.
2. Compute the minimum pairwise Hamming distance on exact integers,
   refusing a set in which an identifier appears twice.
3. Derive the detectable and correctable bit-error counts from that
   separation and compare the separation with the value the mission
   requires.
4. Validate the declared on-board applications: non-negative integers,
   no duplicates.
5. Evaluate each command: an unset spacecraft or application is
   ambiguous; a spacecraft identifier outside the assigned set is a
   routing error; an application identifier not declared on board is a
   routing error; a beam-wide destination is acceptable only when the
   command declares itself broadcast-safe.
6. Report the address-space use, the separation verdict, the ambiguous
   command names and a finding list naming each command and its problem.

## Pitfalls

- Treating a unique identifier set as a safe one. Uniqueness is what a
  database needs; separation is what a noisy channel needs, and
  sequential numbering satisfies the first while failing the second
  completely.
- Numbering a constellation one, two, three. That is the d = 1 case, and
  it is the single most common way a co-visible fleet ends up one bit
  flip from cross-commanding.
- Reading separation without occupancy. A separation target is only
  reachable while the field still has room; measured after the field is
  full, it is a finding with no available fix short of widening the
  frame.
- Letting an undeclared broadcast through because it worked in test. A
  single spacecraft on the pad accepts everything; the same command in a
  populated beam reaches every receiver in it.
- Stopping at the spacecraft identifier. An application identifier the
  on-board software does not declare drops the command inside the right
  spacecraft, which looks like a silent loss rather than a routing
  error.

## Behavior contract (gate 3)

The field-width validation, address-space sizing, Hamming separation,
detect and correct derivation, application validation and the per-command
destination verdicts are exercised by the gate 3 contract test:
scripts/test_e50_telecommand_destination_identification.py against
scripts/e50_telecommand_destination_identification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e50_telecommand_destination_identification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

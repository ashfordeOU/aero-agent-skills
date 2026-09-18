---
name: q40-02-generic-hazard-library
description: "Map a space system onto the generic-hazard library and hazard-register examples of the ECSS-Q-ST-40-02C informative annexes. Use when the task is seeding a hazard identification from declared system characteristics - stored pressure, propellant, pyrotechnics, high voltage, ionizing or laser sources, cryogens, moving mass, crew access, safety-critical command paths - instead of starting from an empty page, ranking each seeded candidate by how strongly those characteristics call it, naming the library groups nothing called, and grading every register record against the example field set so an entry missing its cause, effect, control or verification reference is caught before review. Trigger: ecss, q-st-40-02c, generic-hazard-library-seeding, hazard-register-record-fields, system-characteristic-hazard-mapping, annex-generic-hazard-groups, hazard-register-completeness."
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
  tags: [ecss, q-st-40-02-hazard-analysis-scope, q40-02-generic-hazard-library, generic-hazard-library-seeding, hazard-register-record-fields, system-characteristic-hazard-mapping, annex-generic-hazard-groups, hazard-register-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hazard Analysis — Generic Hazard Library and Register (space-systems/ecss/q40-02-generic-hazard-library)

Use when the task is the informative-annex side of ECSS-Q-ST-40-02C —
seeding a hazard identification from a generic library keyed to the
system's own characteristics, and grading the register records that
seeding is supposed to produce.

## Domain quick reference

- A generic library is a starting point, not an answer. Its job is to
  stop an identification session beginning on a blank page, where the
  hazards that get written down are the ones the people in the room
  happened to think of. What comes out of it is a candidate list that
  still has to be worked against the design.
- The library is keyed, not browsed. Each generic group names the
  system characteristics that call it — a pressurized vessel calls
  stored-energy release, a lithium cell calls thermal runaway, a
  safety-critical command path calls both electromagnetic interference
  and a software-commanded unsafe state. Seeding is a lookup on the
  characteristics the system declares.
- Call strength orders the candidate list. A group whose three keying
  characteristics are all present is called harder than one matched on
  a single characteristic, and that ordering is what makes a long
  candidate list workable rather than discouraging.
- One characteristic calls several groups, and that is the point. A
  high-energy battery calls electrical shock, thermal runaway and fire
  separately, because they have different causes, different controls
  and different verification evidence, and collapsing them into one
  entry loses two of the three.
- The groups nothing called are reported too. An absence in the
  register can mean the group does not apply or that nobody looked,
  and only a named uncalled list tells a reviewer which.
- A register record carries six things: identifier, group, cause,
  effect, control and verification reference. The cause and the
  verification reference are the two that go missing, because the
  first takes thought and the second does not exist yet when the
  record is written.

## Workflow

1. Validate the declared system characteristics against the ones the
   library keys on. An unrecognized characteristic is rejected rather
   than silently ignored, because a silently ignored characteristic
   seeds nothing and looks identical to an absent one.
2. Seed the candidate groups: raise a candidate for every group with at
   least one keying characteristic present, record which
   characteristics matched, and compute the call strength as the
   matched fraction of that group's keys.
3. Rank the candidates by call strength, breaking ties on the group
   name so the same system always produces the same ordered list.
4. Name the library groups that nothing called, and carry that list
   alongside the candidates.
5. Grade each register record field by field against the example field
   set, treating a blank string as missing, and flag a record whose
   group is not in the library.
6. Compare the seeded candidates against the register: a candidate with
   no record is the gap between a seeding session and a register, and
   it is reported by group name.

## Pitfalls

- Treating the library as the hazard list. It produces candidates keyed
  on characteristics; the design-specific hazards that no generic group
  anticipates are still found by walking the functions and operations.
- Browsing the library instead of keying it. Reading down a generic
  list and picking the plausible entries reproduces exactly the bias
  the library exists to remove.
- Collapsing several called groups into one register entry because they
  share a component. One battery calls shock, runaway and fire; each
  has its own cause, control and verification, and one entry can only
  carry one set.
- Reporting the seeded candidates without the uncalled groups. A
  reviewer cannot tell a group that does not apply from a group nobody
  considered, and those are very different states.
- Counting a register record as complete because it has prose in it. Six
  fields carry the record, and the cause and verification reference are
  routinely the blank ones.

## Behavior contract (gate 3)

The characteristic validation, library keying, call-strength ranking,
uncalled-group complement, register-record field grading and
candidate-to-register gap logic is exercised by the gate 3 contract test:
scripts/test_q40_02_generic_hazard_library.py against
scripts/q40_02_generic_hazard_library_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_02_generic_hazard_library.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

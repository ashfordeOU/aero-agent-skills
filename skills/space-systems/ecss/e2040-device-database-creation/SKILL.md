---
name: e2040-device-database-creation
description: "Build the repository of design inputs ECSS-E-ST-20-40C clause 5.4.4 requires before detailed design starts: hold every input under a category, a version and a state, fold the state spellings so a draft cannot read as released, report each detailed-design activity whose declared input the repository does not hold, report each activity reading an input that is draft, obsolete or superseded, demand a successor on a superseded entry, keep the entries nobody reads visible instead of pruning them, and compare readiness against the threshold so a value landing exactly on it passes. Use when the design input repository is assembled, audited or handed over. Trigger: ecss, e-st-20-electrical-scope, device-database-creation, design-input-repository, detailed-design-input-readiness, superseded-entry-successor, unstable-design-input."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-database-creation, device-database-creation, design-input-repository, detailed-design-input-readiness, superseded-entry-successor, unstable-design-input, orphan-design-input]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Design Database Creation (space-systems/ecss/e2040-device-database-creation)

Use when the task is the repository duty of ECSS-E-ST-20-40C clause
5.4.4 -- building and keeping the collection of inputs the detailed
design activities will read, and saying whether what the activities
declare they need is what the repository actually holds in a state they
can rely on.

## Domain quick reference

- The repository is a set of entries, each under a category, a version
  and a state. The category says what kind of input it is; the version
  says which one; the state says whether anything may be built on it.
  An entry missing any of the three cannot be read safely and the
  reader cannot tell which part is missing from the entry alone.
- Three states matter downstream: released, draft and obsolete, with
  superseded as the fourth for an entry a newer one replaces. A draft
  read as released is the defect this check exists for -- the activity
  proceeds, the input moves under it, and nothing in the activity
  record says the ground shifted.
- A superseded entry has to name its successor, and the successor has
  to be in the repository. A supersession pointing nowhere leaves the
  reader with an entry marked do-not-use and no instruction on what to
  use, which is worse than no marking.
- Demand comes from the detailed design activities, not from the
  repository. Each activity declares the inputs it reads, and an input
  declared but not held is a gap the repository cannot see by looking
  at itself.
- An entry nobody reads stays visible. It is either an input an
  activity forgot to declare or an input nothing needs, and both are
  worth knowing; pruning it silently destroys the evidence.
- Readiness is the fraction of declared input demands met by a
  released entry. A threshold met exactly is met, so the comparison
  absorbs representation error: a three-in-four landing on a 0.75
  threshold is a pass, and a strict comparison against a computed
  division is what turns a ready repository red.

## Workflow

1. Resolve every entry: unique identifier, category folded onto a
   recognised name, a version, a state and an optional successor.
   Refuse a repeated identifier or an unknown key as an input defect.
2. Report an entry carrying no version, and refuse a superseded entry
   with no successor or one naming an entry the repository lacks.
3. Resolve the detailed design activities and the inputs each declares
   it reads. Refuse a repeated activity identifier.
4. Report each declared input the repository does not hold.
5. Report each held input read by an activity while its state is
   draft, obsolete or superseded, naming the state.
6. Report each entry no activity declares, keeping it in the
   repository.
7. Compute readiness over the declared demands and compare it against
   the threshold, absorbing representation error and never widening
   the threshold itself.

## Pitfalls

- Reading the repository against itself. Completeness is set by what
  the detailed design activities declare they need, and a repository
  full of well-formed entries can still be missing the one input the
  first activity opens.
- Treating a draft as usable because it is present. Presence is not
  state, the activity cannot tell the difference at read time, and the
  input moves underneath work already done on it.
- Leaving a superseded entry without a successor. The reader is told
  not to use it and not told what to use instead, so the older entry
  gets used anyway.
- Pruning the entries nobody reads. They are the record of an input an
  activity forgot to declare, and removing them removes the only way
  that omission ever surfaces.
- Comparing a computed readiness fraction against its threshold with a
  strict inequality. A three-in-four division landing on 0.75 can sit
  a unit in the last place below it and fail a repository that is
  exactly ready.

## Behavior contract (gate 3)

The entry and activity resolution, category and state folding,
supersession check, missing-input and unstable-input detection,
orphan-entry reporting and the readiness-threshold comparison are
exercised by the gate 3 contract test:
scripts/test_e2040_device_database_creation.py against
scripts/e2040_device_database_creation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_database_creation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q6013-class-2-programmable-devices
description: "Use when a class 2 parts list carries a one time or reprogrammable part. Assess whether the programming and handling record of a programmable device meets what the intermediate assurance class of ECSS-Q-ST-60-13C clause 5.6.4 asks: sort the declared family into one time, reprogrammable non-volatile or reprogrammable volatile, derive the control set that category carries, name every required control the record leaves open, compare the programming cycles already spent against the rated endurance derated by its declared fraction, compare declared configuration retention against the mission duration scaled by its margin factor, and treat an exact equality as met in both. Trigger: ecss, q-st-60-13c-clause-5-6-4, class-two-programmable-device-handling, one-time-programmable-controls, reprogramming-endurance-derating, configuration-retention-margin, volatile-configuration-load-integrity, open-programming-record-control."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-2-programmable-devices, class-two-programmable-device-handling, one-time-programmable-controls, reprogramming-endurance-derating, configuration-retention-margin, volatile-configuration-load-integrity, open-programming-record-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Programmable Devices (space-systems/ecss/q6013-class-2-programmable-devices)

Use when the task is the clause 5.6.4 handling question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a class 2 parts
list carries a one time programmable or a reprogrammable device, a
programming record has been offered for it, and the question is which
controls that device actually owes and which of them the record leaves
open.

## Domain quick reference

- What holds the configuration decides the handling problem. A part
  written once, a part rewritten into non-volatile storage, and a part
  whose configuration is reloaded at every power-up fail in different
  ways, so they carry different control sets rather than one set with
  optional items.
- Some controls are common ground. Programming equipment calibration,
  configuration identification, verification after programming and
  electrostatic handling apply to every programmable part, because they
  protect the programming operation itself rather than the storage.
- A one time part gets its assurance before the write, not after. Blank
  verification, the programming yield record and the undertaking not to
  reprogram after acceptance are the controls that matter, because
  nothing about the configuration can be corrected afterwards.
- A reprogrammable part spends something every time it is written. The
  rated endurance is a manufacturer figure for a fresh part, and the
  programme is entitled to only the derated share of it before
  acceptance, so the cycles already spent are part of the record.
- Retention is a margin question, not a datasheet quote. The declared
  retention is compared against the mission duration scaled by a margin
  factor, and a part that holds exactly the scaled figure has met the
  requirement.
- A volatile-configuration part is never finished being programmed. It
  owes a load integrity check and a scrubbing provision, because the
  configuration it is running is reloaded rather than remembered.
- Open controls are graded, not just listed. One open control is a
  finding the programme can close; a record with several open at once is
  not a record with gaps, it is an absent one.

## Workflow

1. Read the declared device family and sort it into its handling
   category. An unknown family is an input error, not a part to guess
   at from the name.
2. Derive the required control set: the baseline every programmable part
   carries, plus the controls the category adds.
3. Normalise the declared controls against that set, refusing a name
   from another category and a repeated name, so a record cannot close a
   control the part never owed.
4. Take the open controls as the required set the record does not cover,
   and name each one against the category that asked for it.
5. For a one time part, read the reported programming operations: more
   than a single one contradicts the family the part was declared under
   and is reported as such.
6. For a reprogrammable part, take the cycle usage as the spent cycles
   over the rated endurance and compare it with the declared derating
   fraction, treating an exact equality as within the allowance.
7. For a reprogrammable part, scale the mission duration by the margin
   factor and compare the declared retention against it, again treating
   an exact equality as met, and report the retention margin.
8. Compare the open-control count with the declared allowance and return
   one verdict -- handling accepted, accepted with findings, or refused
   -- with the open controls, both ratios and every finding.

## Pitfalls

- Treating one time and reprogrammable parts as one population with a
  shared checklist. The controls that carry a one time part are spent
  before the write; the controls that carry a reprogrammable one run for
  the life of the configuration.
- Forgetting that a volatile-configuration part is reloaded in flight.
  Verifying the configuration once at programming says nothing about
  what the part is running three years later without a load integrity
  check and a scrubbing provision behind it.
- Quoting the rated endurance as the allowance. The rating is a figure
  for a fresh part under the manufacturer's conditions, and a programme
  that spends most of it in development arrives at acceptance with the
  margin already gone.
- Not counting the cycles spent before delivery. Engineering
  reprogramming is real endurance, and a record that starts the count at
  acceptance is measuring the wrong interval.
- Comparing retention with the mission duration and forgetting the
  factor. That passes a part with no margin at all, and the shortfall
  surfaces at the end of the mission, where nothing can be done.
- Loosening the derating fraction or the margin factor so a part that
  lands exactly on it passes. An exact equality is a representation
  question the comparisons already absorb; a part past the allowance is
  past it.
- Reporting a record with most controls open as a findings case. One
  open control is something the programme closes before the next review;
  a handful means there is no programming record yet.

## Behavior contract (gate 3)

The family categorisation, control-set derivation, declared-control
validation, open-control grading, one time programming contradiction,
endurance derating comparison, retention margin comparison and verdict
precedence are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_programmable_devices.py against
scripts/q6013_class_2_programmable_devices_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_programmable_devices.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e3301-general-design-requirements
description: "Assess a mechanism design against the general design requirements of ECSS-E-ST-33-01C clause 4.7.2. Use when the task is showing that a mechanism works in ground ambient and in thermal vacuum and survives its whole life cycle: normalising the handling, transport, test, storage, launch and orbit environments, reporting any phase never declared, bounding them into one enclosing envelope, comparing each phase temperature, pressure, humidity, random vibration and shock with the declared design capability, accumulating operating hours and actuation cycles including ground test against the qualified life, and confirming both operating demonstrations exist. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-general-design-requirements, mechanism-life-cycle-environments, mechanism-thermal-vacuum-operation, mechanism-ground-ambient-operation, mechanism-environment-envelope, mechanism-qualified-life-cycles."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-general-design-requirements, mechanism-general-design-requirements, mechanism-life-cycle-environments, mechanism-thermal-vacuum-operation, mechanism-ground-ambient-operation, mechanism-environment-envelope, mechanism-qualified-life-cycles]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — General Design Requirements (space-systems/ecss/e3301-general-design-requirements)

Use when the task is the clause 4.7.2 general design requirement of
ECSS-E-ST-33-01C — showing that a mechanism is designed to operate
both on the ground in air and in orbit in vacuum, and to come through
every environment its own life cycle puts it in.

## Domain quick reference

- Two operating demonstrations are required, not one. A mechanism that
  works in thermal vacuum and jams in ground ambient has failed the
  clause just as squarely as the reverse, because it will be operated
  in air during integration and acceptance long before it flies.
- The life cycle is six phases, not one flight profile: handling,
  transport, test, storage, launch and orbit. An undeclared phase is a
  coverage gap. Storage is the phase most often dropped, and it is the
  one that runs longest and takes the lubricant with it.
- The phases are bounded into a single enclosing envelope, but the
  envelope does not replace the per-phase comparison. A design can
  enclose the overall temperature span and still be short against one
  phase that pairs a moderate temperature with a load the envelope
  attributes to a different phase.
- Relative humidity is a quantity only where there is atmosphere to
  carry it. A humidity requirement declared for the orbit phase is an
  input defect, and a design capability that carries no humidity
  rating cannot be graded against a ground phase that declares one.
- Qualified life is consumed on the ground. Acceptance and
  qualification actuations, functional checks during integration and
  the cycles run in thermal vacuum all count against the same cycle
  budget as the mission, so the mission cycle count alone understates
  the duty.

## Workflow

1. Normalise every declared phase environment: ordered temperature and
   pressure ranges, optional humidity, random vibration, shock,
   duration and actuation cycles. An inverted range is an input error.
2. Compare the declared phase names with the mandatory life-cycle set
   and raise a coverage finding for each phase absent.
3. Bound all declared phases into an enclosing environment envelope,
   taking the worst dynamic level rather than a representative one.
4. Grade each phase against the design capability: temperature
   enclosure, pressure enclosure, humidity where the phase pressure
   can carry it, random vibration and shock level.
5. Accumulate the duty across the life cycle — operating hours and
   actuation cycles, ground activity included — and compare with the
   qualified life figures.
6. Confirm both the ground-ambient and the thermal-vacuum operating
   demonstration are declared, and report all findings together.

## Pitfalls

- Treating an undeclared phase as a benign one. Silence about storage
  or transport is a gap in the design case, not evidence that the
  phase is mild.
- Grading the envelope only. The envelope is a summary; a phase-level
  pairing of temperature and load can fail inside an envelope that
  passes.
- Counting only mission actuations against qualified life. Ground test
  cycles come out of the same budget and often dominate it for a
  mechanism with a low flight duty.
- Declaring a humidity requirement for a vacuum phase, or grading a
  ground humidity against a capability that was never rated for it.
  Both are input defects and are reported as such.
- Relaxing a capability bound to absorb an exact-equality case. A
  level sitting exactly on the capability is a representation
  question, handled by the tolerance inside the comparison.

## Behavior contract (gate 3)

The phase normalisation, mandatory-phase coverage, envelope bounding,
per-phase grading, cumulative duty against qualified life and the
operating-mode check are exercised by the gate 3 contract test:
scripts/test_e3301_general_design_requirements.py against
scripts/e3301_general_design_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3301_general_design_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

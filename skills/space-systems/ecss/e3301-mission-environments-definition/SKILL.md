---
name: e3301-mission-environments-definition
description: "Define the mission phases and the environment envelope that drive a mechanism design, per ECSS-E-ST-33-01C clause 4.3. Use when the design inputs have to be pinned down before any sizing starts: listing the phases with their durations, demanding a stated value in every environment category instead of reading a silent field as a zero, enveloping the thermal extremes, random vibration and shock while accumulating radiation dose and actuation cycles across the whole mission, raising each envelope to the level the design is proved at through the declared margins, and grading the stated design capability against what it has to survive. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-mission-phase-definition, mechanism-environment-envelope, mechanism-thermal-extremes, mechanism-random-vibration-level, mechanism-shock-srs-level, mechanism-life-cycle-factor, mechanism-radiation-design-margin."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-mission-environments-definition, mechanism-mission-phase-definition, mechanism-environment-envelope, mechanism-thermal-extremes, mechanism-random-vibration-level, mechanism-shock-srs-level, mechanism-life-cycle-factor, mechanism-radiation-design-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Mission and Environments Definition (space-systems/ecss/e3301-mission-environments-definition)

Use when the task is the design-input obligation of ECSS-E-ST-33-01C
clause 4.3 -- writing down the phases a mechanism passes through and,
in each of them, the environments that will drive the design.

## Domain quick reference

- Five categories are carried because each drives different hardware:
  thermal extremes drive materials and lubricant choice; random
  vibration drives the structure and the launch restraint; shock drives
  everything near a release device; accumulated radiation dose degrades
  polymers, greases and optics; and actuation cycles wear the
  tribological pairs out. Dropping one of the five is how a mechanism
  arrives at qualification with an environment nobody sized for.
- Two of the five accumulate and three envelope. The coldest cold, the
  hottest hot and the worst level are taken across phases; dose and
  cycles are summed over the whole mission. Enveloping a dose or
  summing a temperature are both wrong and both easy.
- A phase that leaves a category unstated has a gap in it, not a zero.
  An empty radiation field does not mean the phase is benign, it means
  nobody has written the number down, and an envelope taken over an
  unknown is not an envelope. The definition is refused until the field
  is filled.
- The driving phase is worth recording alongside the extreme. Knowing
  that the cold case comes from the eclipse and the shock case from
  separation is what lets a later trade argue about the right one.
- Qualification levels are the envelope raised by declared margins: a
  temperature margin in kelvin at both ends, a vibration margin in
  decibel, which is an amplitude factor of ten to the power of the
  decibel over twenty and not a percentage, a shock factor, a radiation
  design margin on dose, and a life factor on cycles.
- The decibel factor and the margin products are floating point, so a
  capability written to sit exactly on a qualification level can
  evaluate a hair under it. The comparison absorbs that; the level is
  never lowered to let a capability through.

## Workflow

1. List the mission phases in order with their durations, each one
   named and unique.
2. For each phase, check that all five categories carry a stated
   value. Report the gaps by phase and stop there -- an incomplete
   definition cannot be graded, and filling it is different work from
   fixing a shortfall.
3. Envelope the thermal extremes, the random vibration level and the
   shock level across phases, and record which phase drove each.
4. Accumulate radiation dose and actuation cycles over the whole
   mission rather than enveloping them.
5. Raise the envelope to qualification levels through the declared
   margins, converting the vibration margin from decibel to an
   amplitude factor and rounding the life cycles up to a whole test
   count.
6. Grade the declared design capability against each level, treating a
   value exactly on a level as meeting it, and report the shortfalls by
   name. With no capability declared, close with the envelope fixed and
   say that the comparison has not been made.

## Pitfalls

- Treating an empty field as a benign environment. A phase with no
  dose entry has not been shown to accumulate nothing; the number is
  simply absent, and carrying it as zero silently removes the phase
  from the radiation budget.
- Enveloping the quantities that accumulate. Taking the maximum
  per-phase dose instead of the sum understates the mission total by
  whatever the rest of the phases contribute, and the same mistake on
  cycles undersizes the life test.
- Converting a vibration margin in decibel as if it were a percentage
  or a power ratio. Three decibel on an amplitude is a factor of about
  1.41, not 1.03 and not 2.
- Sizing the life test on the mission cycles alone. The life factor
  exists because scatter in wear is wide, and a mechanism tested to
  exactly its mission count has demonstrated no life margin at all.
- Quoting an envelope with no driving phase attached. When the number
  is later challenged there is nothing to argue with, and a phase
  removed from the mission profile leaves a worst case that no longer
  has a source.
- Grading a capability that sits on the level with bare arithmetic.
  Margin products and a decibel factor are floating point, so a
  capability written to match a level exactly can read as a shortfall
  on one machine and a pass on another.

## Behavior contract (gate 3)

Category coverage, phase validation, the envelope and its driving
phases, the decibel conversion, qualification level build-up and the
capability verdict are exercised by the gate 3 contract test:
scripts/test_e3301_mission_environments_definition.py against
scripts/e3301_mission_environments_definition_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_mission_environments_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

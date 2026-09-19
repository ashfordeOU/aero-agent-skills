---
name: e31-mission-phase-thermal-environment-definition
description: "Define the mission-phase breakdown a thermal control subsystem is designed against under ECSS-E-ST-31 clause 4.1: enumerate every phase from ground handling and pre-launch through ascent, transfer, docking, operations, descent and post-landing, check the timeline for gaps and overlaps, then attach to each phase the environment inputs its role demands - sink temperature, solar flux, albedo, planetary infrared, aerothermal heating and conducted interface loads. Use when a phase list has to be built or audited before thermal analysis begins, and a phase that was never given an environment must be found before the design is sized around it. Trigger: ecss, e-st-31, tcs-mission-phase-definition, tcs-phase-timeline-coverage, tcs-thermal-environment-inputs, tcs-sink-temperature-envelope, tcs-aerothermal-phase-input, spacecraft-thermal-control."
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
  tags: [ecss, e-st-31-thermal-control-scope, e31-mission-phase-thermal-environment-definition, tcs-mission-phase-definition, tcs-phase-timeline-coverage, tcs-thermal-environment-inputs, tcs-sink-temperature-envelope, tcs-aerothermal-phase-input]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Mission-Phase Environment Definition (space-systems/ecss/e31-mission-phase-thermal-environment-definition)

Use when the task is the clause 4.1 step of ECSS-E-ST-31: producing the list
of mission phases the thermal control subsystem is designed against, and the
set of environment inputs each of those phases contributes, before any
analysis case is run.

## Domain quick reference

- The phase list starts on the ground, not at lift-off. Storage, transport,
  integration and pre-launch stand-by are phases with real thermal
  environments, and they are where hardware most often sees a condition
  nobody sized for — a purge that failed, a fairing on a hot pad.
- It also does not end at separation. Descent, entry, landing and
  post-landing recovery are phases for any returning element, and docking or
  berthing introduces a phase in which the environment is set by another
  vehicle rather than by the orbit.
- Different phase roles demand different inputs. An orbital phase needs solar
  flux, albedo and planetary infrared; an ascent or descent phase needs
  aerothermal heating; a ground phase needs an ambient and whatever
  conditioning the ground support equipment supplies. Carrying the orbital
  set into a ground phase produces an environment nobody can defend.
- A timeline with a gap is not a shorter mission — it is an unexamined
  interval. The hardware exists during that gap and is somewhere, at some
  temperature, and the gap is precisely where an unanalysed case hides.
- Overlapping phases are equally suspect. Two phases claiming the same wall
  clock usually means a phase was split and one half never had its
  environment updated, so the analysis silently runs two contradictory
  environments over the same interval.
- The sink temperature envelope over the whole mission, and the phase that
  drives each end of it, are the first two numbers the subsystem design is
  argued from. They fall out of the phase table, so the table must be
  complete before they are quoted.

## Workflow

1. Validate each phase: a name, a role drawn from the known catalogue, a
   start and an end with the end strictly after the start.
2. Sort by start time and walk the sequence, recording every gap between one
   phase ending and the next beginning, and every overlap.
3. Compare the set of roles present with the roles the mission profile
   requires, and record the missing ones. A returning element without a
   descent or post-landing phase is an incomplete list, not a short one.
4. For each phase, look up the environment inputs its role demands and record
   the ones that are absent. A key present but not a real number is an input
   error, not a missing input.
5. Reject an environment value that is physically impossible for its kind: a
   non-positive sink temperature, an albedo outside its closed unit interval,
   a negative flux.
6. Build the mission sink-temperature envelope from the phases that declare
   one, naming the phase at each end so the extreme is attributable.
7. Sum the covered duration and compare it with the span from first start to
   last end, so a timeline that looks complete but is not can be seen at a
   glance.
8. Report the phase table, the envelope, the coverage arithmetic and every
   finding, with the phases that are ready for analysis distinguished from
   the ones that are not.

## Pitfalls

- Starting the phase list at lift-off. Ground and pre-launch conditions are
  routinely the hot case for hardware inside a closed fairing.
- Forgetting the docked or berthed phase. Its environment is set by the
  partner vehicle's shadowing and its conducted interface, neither of which
  the free-flight orbital case contains.
- Applying the orbital environment set to an atmospheric phase. Solar flux
  and albedo are not the drivers during ascent; aerothermal heating is, and
  omitting it leaves the fairing and any exposed item unanalysed.
- Declaring a phase and leaving its environment table empty. An empty table
  is not a benign environment; downstream it becomes zero flux, which is a
  claim nobody made.
- Quoting a mission sink envelope from the orbital phases only. The extreme
  usually belongs to a ground, ascent or post-landing phase, and the envelope
  is then attributed to the wrong phase.
- Treating a timeline gap as slack. The item is still there and still
  exchanging heat; the gap is an interval with no analysis case behind it.

## Behavior contract (gate 3)

The phase validation, timeline gap and overlap detection, role coverage
check, per-role environment completeness, physical range checks, sink
envelope construction and coverage arithmetic are exercised by the gate 3
contract test:
scripts/test_e31_mission_phase_thermal_environment_definition.py against
scripts/e31_mission_phase_thermal_environment_definition_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_mission_phase_thermal_environment_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e20-command-criticality-assessment
description: "Use when rate the criticality of every spacecraft command under ECSS-E-ST-20C clause 4.1.3: categorize the worst-case effect of an inadvertent or erroneous execution at equipment level, evaluate reversibility and the available onboard recovery to determine an equipment criticality level, then confirm that level system wide by escalating any command that drives a single-string critical function or propagates across subsystems, bound any downgrade claimed from redundancy, and verify each retained level carries the protection it demands, such as arm-and-execute sequencing, command authentication or inhibit status telemetry. Trigger: ecss, e-st-20-electrical-scope, command-criticality-assessment, hazardous-command, arm-and-execute, command-authentication, equipment-level-criticality, system-level-confirmation, command-inhibit."
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
  tags: [ecss, e-st-20-electrical-scope, e20-command-criticality-assessment, hazardous-command, arm-and-execute, command-authentication, command-inhibit, equipment-level-criticality]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical & Electronic — Command Criticality Assessment (space-systems/ecss/e20-command-criticality-assessment)

Use when the task is the command criticality rating of ECSS-E-ST-20C
clause 4.1.3 -- rating each command from the worst-case effect of its
inadvertent or erroneous execution at equipment level, confirming that
rating against the system architecture the equipment sits in, and
checking the protection the retained rating demands.

## Domain quick reference

- Criticality is a property of the consequence, not of the command
  word. The starting point is the worst credible effect of executing
  the command when it was not wanted, or of executing it with a wrong
  parameter: from no effect, through degraded performance and loss of
  a redundant path, to loss of a function, loss of the mission, and
  loss of the vehicle or a safety consequence. Each effect carries a
  severity rank, and the rank sets the entry criticality level.
- Two modifiers act at equipment level. Irreversibility raises the
  level by one step: a command whose effect cannot be undone from the
  ground removes the recovery that would otherwise bound the
  consequence. Autonomous onboard recovery lowers it by one step,
  because the consequence is bounded without ground intervention.
  Ground-only recovery is not a downgrade -- it depends on a pass, a
  link and a reaction time that the assessment cannot assume.
- The equipment-level rating is a claim, not the answer. Clause 4.1.3
  requires it to be confirmed at system level, where the same command
  can be worse than its equipment view: it may drive a single-string
  critical function, or its effect may propagate across more than one
  subsystem. Both force an escalation the equipment view cannot see.
- A downgrade claimed from redundancy is the one direction that is
  bounded rather than applied. Redundancy only bounds a consequence if
  the redundant path exists and is not commanded by the same command
  word; and even a valid downgrade may not take a command whose effect
  reaches loss of a function below the mission-significant level.
- The retained level then sets the protection: verification of the
  command, arm-and-execute sequencing for the critical levels, and for
  a hazardous command also authentication and telemetry that reports
  the state of its inhibits.

## Workflow

1. Categorize the worst credible effect of each command's inadvertent
   or erroneous execution and take its severity rank. Reject an effect
   term that is not in the recognized set rather than guessing a rank.
2. Map the rank to the entry criticality level, then apply the
   equipment-level modifiers: raise one step for an irreversible
   command, lower one step for autonomous onboard recovery only.
3. Confirm the level system wide: escalate to at least the
   mission-critical level for a command driving a single-string
   critical function, and raise one step for a command whose effect
   propagates across two or more subsystems.
4. Bound any redundancy downgrade: reject it outright when the same
   command word drives the redundant path, allow at most one step, and
   never below mission-significant for a loss-of-function effect.
5. Check the protection set the retained level demands and list every
   protection that is missing.
6. Aggregate per level and per command. The command set is compliant
   only when no command is missing a protection its retained level
   demands; report the retained level next to the equipment-level
   claim so an escalation is visible, not silently absorbed.

## Pitfalls

- Rating a command from what it is for rather than from what it does
  when it arrives unwanted. A routine mode change on a payload can be
  a loss-of-vehicle command during a critical propulsive phase.
- Accepting the equipment-level rating as the answer. The equipment
  supplier cannot see the single-string function the unit feeds, so
  the system-level confirmation is where most escalations appear.
- Taking credit for redundancy that the same command word disables on
  both paths. A single command reaching both strings is a single point
  of failure wearing the label of a redundant one.
- Treating ground recovery as equivalent to autonomous recovery. A
  consequence bounded only by a ground pass is not bounded during the
  pass that was missed.
- Rating every command hazardous to be conservative. Protection that
  applies everywhere is dropped everywhere; the assessment has to
  discriminate for the arm-and-execute sequencing to mean anything.

## Behavior contract (gate 3)

The effect categorization, equipment-level rating, system-level
confirmation, redundancy-downgrade bounding and protection-check logic
is exercised by the gate 3 contract test:
`scripts/test_e20_command_criticality_assessment.py` against
`scripts/e20_command_criticality_assessment_logic.py` (stdlib
unittest, offline). Run:
python3 scripts/test_e20_command_criticality_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

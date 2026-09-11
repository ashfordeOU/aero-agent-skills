---
name: e1011-users-manual
description: "Use when define the users manual for a human-rated space system under ECSS-E-ST-10-11C §4.3.4: verify that all required HFE input sections are present (user population, task procedures, interface description, error recovery, mission-phase applicability, training requirements), validate each task procedure's steps against applicable mission phases, confirm that safety-critical steps carry a warning note, verify that every task procedure with safety-critical steps has a linked error-recovery entry, and check that user-population entries carry skill level, physical constraints, cognitive load limits, and operating language. Trigger: ecss, e-st-10-11c, e-st-10-system-scope, users-manual, hfe-inputs, task-procedures, error-recovery, human-factors-engineering."
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
  tags: [ecss, e-st-10-11c, e-st-10-system-scope, users-manual, hfe-inputs, task-procedures, error-recovery, human-factors-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Users Manual HFE Inputs (space-systems/ecss/e1011-users-manual)

Use when the task is to define the users manual for a human-rated space
system or product under ECSS-E-ST-10-11C §4.3.4 — assembling the required
HFE input sections, validating task procedure completeness, confirming that
safety-critical steps carry warnings and linked error-recovery entries, and
checking that user-population entries are fully attributed before the
document is accepted at a design review.

## Domain quick reference

- §4.3.4 requires the users manual to contain six HFE input sections:
  (1) **user-population** — who uses the system and their characteristics;
  (2) **task-procedures** — step-by-step instructions for each user task;
  (3) **interface-description** — description of displays, controls, and alarms;
  (4) **error-recovery** — recovery procedures for every safety-critical task;
  (5) **mission-phase-applicability** — which sections apply in each mission phase;
  (6) **training-requirements** — minimum preparation needed before system use.
  A manual missing any of these sections is incomplete for HFE compliance.
- A task procedure is a sequence of discrete steps, each carrying an action
  description and an optional warning note. A step is safety-critical when
  an error at that step could cause loss of life, loss of mission, or
  irreversible system damage. Every safety-critical step MUST carry a
  warning note; a step flagged safety-critical without one is a documentation
  defect that blocks the procedure from being accepted.
- Error-recovery entries are linked to task procedures by procedure ID. If
  a task procedure contains at least one safety-critical step it must have
  a corresponding error-recovery entry. The reverse — a non-safety-critical
  procedure with an error-recovery entry — is allowed but not required.
- User-population entries capture four mandatory attributes: skill level
  (novice / trained / expert), physical constraints, cognitive load limits,
  and operating language. An entry missing any attribute cannot be used to
  derive interface or training requirements — it is flagged incomplete.

## Workflow

1. Confirm the product boundary and identify every user role that will
   interact with the system. For each role, create a user-population entry
   carrying skill level (novice / trained / expert), physical constraints,
   cognitive load limits, and operating language. Flag any entry missing a
   mandatory attribute before proceeding.
2. Enumerate every task users must perform. For each task, create a
   task-procedure entry: assign a unique procedure ID, a description, at
   least one step, and one or more mission-phase tags. Reject a task
   procedure with no steps or with an unrecognised phase tag.
3. For each step in a task procedure, determine whether it is
   safety-critical. Safety-critical steps must carry a warning note. If a
   step is flagged safety-critical but its warning note field is empty or
   absent, record it as a documentation defect and do not mark the procedure
   complete.
4. For every task procedure that contains at least one safety-critical step,
   create a corresponding error-recovery entry (linked by procedure ID) with
   a non-empty recovery description. A safety-critical procedure with no
   linked recovery entry is non-compliant.
5. Produce the interface-description, mission-phase-applicability, and
   training-requirements sections. Verify they are present and non-empty.
   These sections are checked for presence at this level; their content is
   validated by the e1011-task and e1011-training-approach leaves respectively.
6. Run the gap check: all six required sections present, no incomplete
   user-population entries, no step defects, no uncovered safety-critical
   procedures. The manual is HFE-compliant when the gap list is empty.

## Pitfalls

- Including a user-population entry but leaving out the skill level
  attribute — without it, the interface and training requirements cannot
  be derived, and the entry must be treated as absent, not partial.
- Flagging a step as safety-critical without writing a warning note,
  reasoning that the criticality flag itself conveys the risk — the warning
  note is the operator-facing signal; the flag is a system metadata marker.
  Both must be present simultaneously.
- Assuming a non-safety-critical procedure needs no error recovery —
  coverage is mandatory only for safety-critical procedures, but omitting
  recovery guidance for high-frequency routine tasks is a judgement that
  must be made explicitly, not by default silence.
- Treating mission-phase-applicability as a single global tag for the whole
  manual — each task procedure carries its own phase tag; the section
  establishes which phases are in scope for the manual, while procedure-level
  tags express when each individual procedure applies.
- Marking the manual complete before all six sections have been populated
  and the gap list has been run — a manual accepted with an empty
  error-recovery section will pass structural review but fail HFE compliance
  audit at later gates.

## Behavior contract (gate 3)

The user-population validation, task-procedure step check, safety-critical
step / warning-note pairing, error-recovery cross-reference, and gap-list
logic are exercised by the gate 3 contract test:
scripts/test_e1011_users_manual.py against
scripts/e1011_users_manual_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_users_manual.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

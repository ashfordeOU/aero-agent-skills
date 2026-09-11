---
name: e1011-context-of-use
description: "Use when define the context-of-use description for a product or system as the foundational human-centred design (HCD) input under ECSS-E-ST-10-11C §4.2.2: identify the intended user population, the tasks they must perform, the physical and organisational environment, any relevant constraints, and the mission phases in which users interact with the system, then structure these elements into a reviewable context-of-use record that feeds subsequent HCD planning and human factors evaluation. Trigger: ecss, e-st-10-system-scope, context-of-use, human-centred-design, hcd, user-population, task-analysis, operational-environment, human-factors."
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
  tags: [ecss, e-st-10-system-scope, context-of-use, human-centred-design, hcd, user-population, task-analysis, operational-environment, human-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Context-of-Use Description (space-systems/ecss/e1011-context-of-use)

Use when the task is to define the context-of-use description for a
product or system as the primary HCD input under ECSS-E-ST-10-11C
§4.2.2 — identifying users, tasks, environments, and mission-phase
interactions, then assembling them into a structured record.

## Domain quick reference

- A context-of-use description covers four axes: (1) the **user
  population** (roles, experience levels, training background,
  cognitive and physical characteristics relevant to the interface),
  (2) the **tasks** users must perform (goal, steps, frequency,
  criticality, error tolerance), (3) the **physical environment**
  (workstation geometry, lighting, vibration, suit/glove constraints,
  communication latency), and (4) the **organisational environment**
  (crew size, shift structure, support chain, autonomy level,
  procedure authority).
- The context-of-use record is authored once per product/system and
  is updated when any of its four axes change materially. It is not a
  requirements document — it is a description that requirements and
  verification objectives are derived from.
- Mission phase scoping is mandatory: a context-of-use element that
  applies only during ascent differs from one that applies during
  on-orbit nominal operations. Each element carries an explicit phase
  tag; elements valid across all phases are tagged "all-phases".
- Completeness is verified against a checklist: every mandatory field
  (user role, task name, phase tag, environment category) must be
  populated. A record with any mandatory field missing is incomplete
  and must not be used as HCD input until corrected.

## Workflow

1. Gather the system's operational concept, mission profile, and any
   existing user-needs or human factors studies for the product in
   scope. Confirm the product boundary (what the user physically or
   cognitively touches) before starting.
2. Enumerate user roles. For each role record: role name, count of
   individuals in that role, minimum and maximum expected experience
   level (novice / trained / expert), training pathway, and any
   physical or cognitive constraints the interface must accommodate.
   A role with no training pathway on record is incomplete.
3. Enumerate tasks. For each task record: task name, goal statement,
   owning user role, triggering condition, nominal step count,
   frequency (per mission or per day), criticality (safety-critical /
   mission-critical / routine), maximum allowable error rate, and the
   mission phase(s) in which the task occurs. A task with no owning
   role or no phase tag is incomplete.
4. Enumerate environment elements. For each element record: category
   (physical or organisational), a description, and the mission
   phase(s) in which it applies. Physical elements cover workstation
   geometry, lighting levels, vibration/noise, pressurisation, and
   access constraints (suited operations, restricted reach envelope).
   Organisational elements cover crew complement, communication
   structure, procedure authority, and autonomy level.
5. Validate completeness: every user role has a training pathway; every
   task has an owning role and at least one phase tag; every
   environment element has a category and a phase tag. Collect all
   incomplete items into a gap list. The context-of-use record is
   ready for HCD planning only when the gap list is empty.
6. Produce the context-of-use record as a structured document with
   four named sections (User Population, Tasks, Physical Environment,
   Organisational Environment), each entry cross-referenced by role
   and phase. Include the gap list (empty = compliant) and the
   product/system boundary statement as a preamble.

## Pitfalls

- Describing only the nominal-operations context and omitting
  contingency or emergency phases — emergency tasks often impose the
  tightest human factors constraints and must be captured explicitly.
- Treating all user roles as interchangeable — roles differ in
  training, authority, and interface access; collapsing them loses
  the traceability needed for allocation of human factors requirements.
- Recording environment elements without phase tags — a constraint
  that exists only during EVA prep does not apply during on-orbit
  nominal, and unlabelled elements are silently applied everywhere,
  which can generate spurious or missed requirements.
- Marking the record complete before the gap list is checked — an
  incomplete context-of-use record will propagate missing information
  into HCD planning and human factors evaluation, compounding the
  defect downstream.
- Omitting the product boundary statement — without it, reviewers
  cannot determine which user actions fall within scope of this record
  and which belong to an adjacent system's context-of-use.

## Behavior contract (gate 3)

The user-population enumeration, task completeness check, environment
categorisation, phase-tag validation, and gap-list logic are exercised
by the gate 3 contract test: scripts/test_e1011_context_of_use.py
against scripts/e1011_context_of_use_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e1011_context_of_use.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

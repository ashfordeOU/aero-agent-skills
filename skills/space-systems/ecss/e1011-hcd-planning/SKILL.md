---
name: e1011-hcd-planning
description: "Use when plan the human-centred design (HCD) process for a space system or product under ECSS-E-ST-10-11C §4.4.1–4.4.2: identify every HCD activity required by Annex A (context-of-use analysis, user requirements specification, design solution, evaluation, implementation verification), assign each activity to an ECSS project phase (0 through F), allocate at minimum one HF specialist as the responsible party per activity, and confirm the resulting HCD plan covers all mandatory activities with no phase-order violations. Trigger: ecss, e-st-10-system-scope, hcd-planning, human-centred-design, hfe, hcd-plan, annex-a, project-phases, responsibilities."
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
  tags: [ecss, e-st-10-system-scope, hcd-planning, human-centred-design, hfe, annex-a, project-phases, responsibilities]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — HCD Planning (space-systems/ecss/e1011-hcd-planning)

Use when the task is to plan the human-centred design process for a
space system or product per ECSS-E-ST-10-11C §4.4.1–4.4.2 — producing
an HCD plan that names every required activity, maps each to an ECSS
project phase, and assigns at least one HF specialist as the responsible
party per activity.

## Domain quick reference

- ECSS-E-ST-10-11C §4.4.1 requires that an HCD plan be established at
  the outset of development; the plan must cover the entire product
  life cycle and be updated whenever project scope, schedule, or
  resources change materially.
- §4.4.2 and Annex A define the five mandatory HCD activity categories
  every plan must address: context-of-use analysis, user requirements
  specification, design solution, evaluation, and implementation
  verification. A plan missing any category is non-compliant.
- Each activity must be placed in one or more ECSS project phases
  (0 Mission Analysis → A Feasibility → B Preliminary Definition →
  C Detailed Definition → D Qualification and Production →
  E Utilisation → F Disposal). Phase ordering must respect the
  logical dependency chain: context analysis before requirements,
  requirements before design, design before evaluation.
- Responsibility assignment requires at minimum an HF specialist
  named for each activity; project manager, system engineer, and
  subsystem engineer may co-own activities but cannot substitute
  for the HF specialist role.
- Resources (budget, tool access, test-facility time) are noted per
  activity but are not validated by this leaf — they are tracked in
  the project management plan and referenced here as a completeness
  check item only.

## Workflow

1. List every candidate HCD activity the project will perform.
   Verify the list covers all five mandatory Annex A categories;
   reject a plan with any category absent before proceeding.
2. For each activity, record the target ECSS project phase or phases.
   Validate each phase identifier (0, A, B, C, D, E, F); reject any
   unrecognised identifier.
3. Enforce phase-order consistency across activity pairs: context-of-use
   analysis must be scheduled no later than user requirements
   specification; user requirements must be no later than design
   solution; design solution must be no later than evaluation.
   Flag any ordering violation as a planning error.
4. For each activity, record the responsible roles. Confirm at least
   one role is the HF specialist; flag activities where the HF
   specialist is absent. Reject roles not drawn from the recognised
   set (hf_specialist, project_manager, system_engineer,
   subsystem_engineer, test_engineer, operator).
5. Compute the schedule coverage map — which project phases contain
   at least one HCD activity — to confirm the plan spans the intended
   life-cycle range.
6. Produce the completeness summary: activity count, any missing
   mandatory activities, phases covered, and accumulated errors.
   An HCD plan is compliant only when the error list is empty.

## Pitfalls

- Omitting the context-of-use analysis because the system reuses a
  heritage design — §4.4.2 requires a fresh analysis for each new
  operational environment; heritage data is input, not a substitute.
- Assigning evaluation to a phase earlier than design solution —
  evaluation presupposes a design artefact to assess; scheduling it
  earlier produces a phantom activity with no subject matter.
- Treating "project manager" as the sole responsible party for an
  HCD activity — ECSS-E-ST-10-11C explicitly requires HF specialist
  involvement; managerial ownership does not fulfil the technical
  responsibility requirement.
- Leaving a mandatory activity with no phase assignment — an
  unscheduled activity cannot be resourced, reviewed, or baselined;
  the plan is incomplete until every activity has at least one phase.
- Locking the HCD plan at project kick-off and not updating it when
  the project phase changes — §4.4.1 requires the plan to remain
  current; a stale plan is treated as non-compliant at review gates.

## Behavior contract (gate 3)

The activity-completeness, phase-order, and responsibility-assignment
logic is exercised by the gate 3 contract test:
scripts/test_e1011_hcd_planning.py against
scripts/e1011_hcd_planning_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_hcd_planning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

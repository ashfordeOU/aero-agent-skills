---
name: e1024-planning
description: "Use when define the Interface Management Plan (IMP) for a space project under ECSS-E-ST-10C §5.1: establish IMP scope and purpose, assign team responsibilities for interface identification, documentation, review, approval, baseline, and change control, specify the IM process steps from identification through verification, schedule IM milestones against project lifecycle phases (phases 0 through F), and integrate the IMP with the System Engineering Plan (SEP) by linking the SEP IM section and confirming the IMP is listed as a required project deliverable. Apply also to audit an existing IMP for §5.1 completeness. Trigger: ecss, e-st-10-system-scope, interface-management, imp, sep, lifecycle-phases, responsibilities, process-definition, milestones, im-plan."
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
  tags: [ecss, e-st-10-system-scope, interface-management, imp, sep, lifecycle-phases, responsibilities, process-definition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Interface Management Planning (space-systems/ecss/e1024-planning)

Use when the task is defining or auditing the Interface Management Plan (IMP)
of a space project against the requirements of ECSS-E-ST-10C §5.1 — covering
plan scope and purpose, team responsibilities, the IM process definition,
lifecycle milestone scheduling, and integration with the System Engineering
Plan (SEP).

## Domain quick reference

- §5.1 requires the project to establish a documented IMP that defines the
  scope of interface management, names the responsible parties for each
  interface type, lays out the IM process steps, and schedules those steps
  against the project lifecycle phases.
- Interface types span at minimum: mechanical, electrical, thermal, data,
  RF, software, and operational interfaces. Each type must have an assigned
  responsible party; leaving any type without an owner is a §5.1 finding.
- The IM process must cover, in sequence: identify interfaces, document them
  in Interface Control Documents (ICDs), review the ICDs, approve and
  baseline them, control changes through the approved change process, and
  verify that the implemented interfaces conform to the baselined ICDs. A
  plan that omits any of these steps is incomplete.
- The IM schedule must tie IM milestones to lifecycle phases. At minimum,
  phases A (Feasibility), B (Preliminary Definition), C (Detailed
  Definition), and D (Qualification and Production) must each carry at
  least one IM milestone; an IMP that has no milestones in one of these
  phases is incomplete.
- The IMP must be integrated with the SEP: the SEP must reference its IM
  section, and the IMP must be listed as a required project deliverable in
  the SEP. An IMP that exists in isolation from the SEP does not satisfy
  §5.1.

## Workflow

1. Collect the candidate IMP document (or the inputs needed to draft one)
   and confirm the following mandatory fields are present: name, purpose,
   scope, responsibilities (keyed by interface type), process steps,
   schedule (keyed by lifecycle phase), and a SEP reference. Reject the
   plan and request the missing fields before continuing.
2. Check that the responsibility matrix covers all required interface types
   (mechanical, electrical, thermal, data, RF, software, operational) and
   that each type has a non-empty owner assignment. Flag every type with
   no owner.
3. Verify that the IM process step list includes, in any order: identify,
   document, review, approve, baseline, control, and verify. Flag every
   missing step; a plan with fewer than all seven steps cannot be baselined.
4. Check the IM schedule against the minimum required lifecycle phase
   coverage (phases A, B, C, D). For each required phase, confirm at least
   one milestone is listed. Flag phases with no milestones; flag phases
   listed with an empty milestone list separately, as the phase entry exists
   but carries no content.
5. Verify SEP integration by checking three conditions: the SEP reference
   field is non-empty, the SEP IM section is named, and the IMP is marked
   as a required deliverable in the SEP. Flag each condition that fails.
6. Aggregate all findings. The IMP is §5.1-compliant only when every check
   in steps 2 through 5 returns no findings. Produce a structured assessment
   report listing findings by category and a single compliant/non-compliant
   verdict.

## Pitfalls

- Treating a responsibility matrix entry with a blank owner string as
  assigned — an empty string is not an owner; the interface type is
  uncovered and must be flagged.
- Accepting a schedule that names a required lifecycle phase but provides
  an empty milestone list — the phase entry existing in the schedule does
  not satisfy the requirement; the milestone list must be non-empty.
- Treating the IMP as SEP-integrated when only the SEP reference field is
  filled — full integration requires the SEP reference, the SEP IM section
  name, and the deliverable listing flag; missing any one of the three is
  a finding.
- Skipping the process-step completeness check because the plan narrative
  describes the IM process in prose — the check requires each of the seven
  steps to appear explicitly; prose descriptions without step enumeration
  leave ambiguity about coverage.

## Behavior contract (gate 3)

The IMP-field validation, responsibility-matrix, process-completeness,
schedule-coverage, SEP-integration, and full-assessment logic are exercised
by the gate 3 contract test: scripts/test_e1024_planning.py against
scripts/e1024_planning_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1024_planning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e1011-mission-phases
description: "Use when map mission phases and identify human-in-the-loop activities for HFE requirements capture under ECSS-E-ST-10-11C §4.3.6: inventory each canonical phase (ground operations, launch, ascent, deployment, on-orbit checkout, nominal operations, contingency, disposal), categorize every operator or crew activity within each phase, flag phases with no human-in-the-loop coverage, flag critical activities lacking human oversight in safety-critical phases, and derive one HFE requirement per human-assigned activity to populate the requirements register. Trigger: ecss, e-st-10-system-scope, e-st-10-11c, human-factors, mission-phases, human-in-the-loop, hfe-requirements, operator-activities."
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
  tags: [ecss, e-st-10-system-scope, e-st-10-11c, human-factors, mission-phases, human-in-the-loop, hfe-requirements, operator-activities]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — Mission Phases (space-systems/ecss/e1011-mission-phases)

Use when the task is to map canonical mission phases and identify
human-in-the-loop activities within each phase for Human Factors Engineering
(HFE) requirements capture, following ECSS-E-ST-10-11C §4.3.6 — inventorying
operator and crew activities per phase, flagging gaps in human coverage, and
deriving one structured HFE requirement for each human-assigned activity.

## Domain quick reference

- ECSS-E-ST-10-11C §4.3.6 requires that the HFE assessment covers every
  mission phase in which a human operator or crew member is involved. The
  standard establishes eight canonical phases in lifecycle order: ground
  operations (pre-launch), launch, ascent, deployment/separation,
  on-orbit checkout, nominal operations, contingency/off-nominal operations,
  and disposal/decommissioning. Each programme must step through the full
  phase list and confirm which phases are within the HFE assessment scope.
- Within each in-scope phase, every human activity is catalogued by activity
  type (commanding, monitoring, maintenance, procedure execution, decision
  making, communication, emergency response, configuration) and by criticality
  (critical, routine, or monitoring-only). Activities without human involvement
  are recorded as automated but are not excluded from the inventory —
  automated activities in mandatory-human phases (launch, ascent, contingency)
  that carry critical criticality must be reviewed: the absence of human
  oversight is itself an HFE finding that requires disposition.
- Each human-in-the-loop activity maps to a primary HFE driver category
  (workload, cognitive, anthropometry, communication, or safety) that seeds
  the HFE requirements register. The mapping is deterministic: commanding
  and procedure-execution map to workload; monitoring and decision-making map
  to cognitive; maintenance maps to anthropometry; communication maps to
  communication; emergency-response maps to safety; configuration maps to
  workload.
- A phase with no human activities is flagged for scope confirmation — it may
  be intentionally out of scope (unmanned phase) or it may represent a gap in
  the activity inventory. The distinction must be documented before the HFE
  requirements register is baselined.

## Workflow

1. Enumerate the canonical phase list and confirm which phases are within the
   programme's HFE scope. Mark out-of-scope phases explicitly; do not silently
   drop them. Reject any phase token not drawn from the controlled vocabulary
   before continuing.
2. For each in-scope phase, collect every human and automated activity.
   Validate each activity's type and criticality against the controlled
   vocabularies; reject unrecognized tokens with an explicit error before the
   phase analysis proceeds.
3. Categorize each activity as human-in-the-loop or automated. For human
   activities, determine the primary HFE driver from the activity-type mapping.
   For automated activities in the mandatory-human phases (launch, ascent,
   contingency), flag any critical-criticality activity that lacks human
   oversight.
4. Derive one HFE requirement for each human-in-the-loop activity. Assign the
   structured requirement ID `HFE-<PHASE_CODE>-<ACTIVITY_ID>` and record the
   phase, activity identifier, HFE driver category, and criticality level.
5. After processing all activities, perform the per-phase coverage check: a
   phase that produced no HFE requirements (all activities automated) is
   flagged as a potential scope gap requiring scope-confirmation documentation.
6. Perform the completeness check across all canonical phases: any phase absent
   from the activity inventory is flagged as missing. A requirements register
   is ready for baselining only when both the per-phase coverage findings and
   the inventory-completeness findings are empty, or each finding has a
   documented disposition.

## Pitfalls

- Treating phases with no human activities as trivially compliant — an
  automated phase in a crewed programme may represent a missing activity
  inventory entry rather than a genuine autonomous segment, and the difference
  must be documented, not assumed.
- Failing to flag critical automated activities in mandatory-human phases
  (launch, ascent, contingency) — these phases carry heightened safety
  significance, and any critical task without a human check is an HFE risk
  that requires a formal disposition even if no HFE requirement is generated.
- Accepting free-text activity-type or criticality tokens without validation —
  uncontrolled tokens prevent consistent driver mapping and break downstream
  traceability into the HFE requirements register.
- Generating HFE requirements only for the phases the analyst remembers —
  stepping through the full canonical phase list programmatically ensures no
  phase is silently omitted from the assessment scope.
- Treating the per-phase coverage check as optional — a phase that yields zero
  HFE requirements is not automatically out of scope; the absence of
  requirements must be a deliberate, documented decision.

## Behavior contract (gate 3)

The phase-code validation, activity-type validation, criticality validation,
activity categorization, HFE-driver mapping, requirement-ID generation,
phase-analysis, completeness-check, and full-map logic is exercised by the
gate 3 contract test: scripts/test_e1011_mission_phases.py against
scripts/e1011_mission_phases_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_mission_phases.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

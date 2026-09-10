---
name: e10-phase-task-overview
description: "Use when checking per-phase system engineering task lists and outputs under ECSS-E-ST-10C: confirm the project's tasks for lifecycle phases 0 through F (mission analysis through disposal) are identified and tracked against the System Engineering Plan (SEP) deliverables. ECSS-E-ST-10C clause 4.3.3-4.3.9 gives the informative per-phase task overview. Trigger: ecss, e-st-10c, phase task, lifecycle phase, phase 0, phase A, phase B, phase C, phase D, phase E, phase F, systems engineering, 4.3.3, space systems engineering."
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
  tags: [ecss, e-st-10c, phase-task-overview, lifecycle, phase-0, phase-a, phase-b, phase-c, phase-d, phase-e, phase-f, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Per-Phase SE Task Overview (space-systems/ecss/e10-phase-task-overview)

Use when checking which system engineering tasks belong to each
project lifecycle phase under ECSS-E-ST-10C clause 4.3.3-4.3.9, and
whether the project is tracking them against SEP-driven deliverables.

## When to use

- Planning phase content: which SE tasks run in phase 0 (mission
  analysis) vs A (feasibility) vs B (definition) vs C/D (design and
  qualification) vs E (operations) vs F (disposal).
- Auditing a project plan against the generic per-phase task list.
- Preparing for a phase review when the phase task list must be
  complete and its outputs delivered.

## Domain quick reference

Generic per-phase SE task clusters (informative, E-ST-10C 4.3):

- Phase 0: mission needs capture, feasibility assessment, top-level
  requirement drafting.
- Phase A: system requirement definition, concept trade-off,
  preliminary specification tree.
- Phase B: preliminary design definition, requirement baseline
  freeze, interface definition.
- Phase C: detailed design definition, verification planning,
  requirement closure.
- Phase D: qualification test execution, acceptance test execution,
  as-built documentation.
- Phase E: in-orbit commissioning, operational maintenance support,
  anomaly resolution.
- Phase F: disposal execution, close-out reporting.

The concrete deliverable set is not fixed by this list alone: the
project's System Engineering Plan (SEP, clause 5.1) tailors it.

## Procedure

1. Run the offline test to confirm the module contract:
   `python3 scripts/test_e10_phase_task_overview.py`.
2. From Python:

```python
import e10_phase_task_overview_logic as pt
pt.tasks_for("B")   # tuple of SE tasks for phase B
```

3. Compare the returned task list with the project plan's phase
   content. Missing tasks are plan gaps to resolve before the phase
   review.

## Verification

- The offline unittest suite passes.
- Every phase 0 through F returns a non-empty task tuple.

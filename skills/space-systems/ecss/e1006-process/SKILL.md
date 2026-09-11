---
name: e1006-process
description: "Use when execute the Technical Specification establishment process under ECSS-E-ST-10C §5: advance through phase-0 preliminary TS tasks (F1.1–F1.4), verify that prerequisites are satisfied before starting each task, iterate requirements at each decomposition level until no open changes remain, then advance through phase-A TS tasks (F1.5–F1.10) and issue the phase-A Technical Specification. Trigger: ecss, e-st-10-system-scope, ts-establishment, technical-specification, phase-0, phase-a, requirements-iteration, decomposition, systems-engineering."
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
  tags: [ecss, e-st-10-system-scope, ts-establishment, technical-specification, requirements-iteration, decomposition, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Systems Engineering — TS Establishment Process (space-systems/ecss/e1006-process)

Use when the task is to execute the Technical Specification establishment
process of ECSS-E-ST-10C §5, advancing through the phase-0 preliminary
TS tasks (F1.1–F1.4) and the phase-A TS tasks (F1.5–F1.10), verifying
prerequisites at each step, and iterating requirements at each
decomposition level until the baseline is stable.

## Domain quick reference

- ECSS-E-ST-10C §5 divides the TS establishment process into two
  phases: phase-0 produces a preliminary Technical Specification through
  four tasks (F1.1–F1.4), and phase-A produces the phase-A Technical
  Specification through six tasks (F1.5–F1.10). Each task has explicit
  prerequisites that must be complete before the task may start; no task
  may be opened out of order.
- Phase-0 task sequence: (F1.1) establish mission context and top-level
  constraints; (F1.2) derive the initial system requirements from that
  context; (F1.3) perform the first-pass system decomposition and
  allocate requirements to each system element; (F1.4) document and
  issue the preliminary TS as the phase-0 output.
- Phase-A task sequence: (F1.5) refine the functional architecture and
  establish the functional baseline; (F1.6) allocate performance budgets
  to system elements; (F1.7) define interface requirements at element
  boundaries; (F1.8) conduct feasibility trade studies and record the
  selected approach; (F1.9) iterate requirements at each decomposition
  level until all open changes are resolved; (F1.10) issue the phase-A
  Technical Specification. Tasks F1.6, F1.7, and F1.8 may proceed
  concurrently after F1.5; F1.9 requires all three to be complete before
  it may start.
- Iteration at each decomposition level (task F1.9) is not complete
  until the open requirement change count at that level reaches zero.
  A level with even a single unresolved change blocks issuance of the
  phase-A TS. The absence of registered decomposition levels is not
  evidence of convergence — every level must be explicitly tracked.

## Workflow

1. Confirm phase-0 entry: verify that mission objectives, operational
   environment description, and top-level constraints are available as
   inputs before opening F1.1.
2. Execute F1.1 through F1.4 in prerequisite order. For each task,
   confirm its prerequisites are complete before opening it; use the
   blocking-task check to identify any outstanding dependencies.
3. On completion of F1.4, confirm the preliminary TS has been issued
   and baselined before opening any phase-A task.
4. Open F1.5 as the single gateway into phase-A. After F1.5 is
   complete, open F1.6, F1.7, and F1.8 concurrently; track each
   independently.
5. Open F1.9 only after F1.6, F1.7, and F1.8 are all marked complete.
   For each decomposition level, register an open requirement change
   count; iterate — revisiting allocations, interface definitions, and
   trade-study results as needed — until the count reaches zero at
   every registered level.
6. Open F1.10 only after F1.9 shows zero open changes at all
   decomposition levels. Issue the phase-A Technical Specification.
7. Perform a final status check: phase_0_complete and phase_a_complete
   must both be True, and all_levels_converged must be True (with at
   least one level registered), before declaring the TS establishment
   process complete.

## Pitfalls

- Opening a task before its prerequisites are complete — F1.2 without
  F1.1, F1.9 without all of F1.6, F1.7, and F1.8, F1.10 without F1.9.
  A prerequisite check must return True before any task is opened.
- Treating iteration convergence as optional — if any decomposition
  level carries unresolved requirement changes when F1.9 is declared
  done, the phase-A TS baseline is unstable and F1.10 must not be
  executed.
- Conflating phase-0 completion with phase-A readiness — F1.4 issues
  only a preliminary TS; all six phase-A tasks must follow before the
  process is complete.
- Skipping phase-0 and attempting to enter phase-A directly — the
  preliminary TS produced by F1.1–F1.4 is a required input to F1.5.
- Relying on an empty decomposition-level dict as proof of convergence
  — the module returns all_levels_converged as True by vacuous logic
  when no levels are registered; the correct approach is to register
  every level in use and confirm each reaches zero open changes before
  completing F1.9.

## Behavior contract (gate 3)

The task-validation, prerequisite-checking, iteration-convergence,
phase-completeness, and overall-status logic is exercised by the gate 3
contract test: scripts/test_e1006_process.py against
scripts/e1006_process_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1006_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

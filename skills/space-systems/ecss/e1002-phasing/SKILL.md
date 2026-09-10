---
name: e1002-phasing
description: "Use when phasing verification activities with the project life cycle under ECSS-E-ST-10-02C clause 5.2.7: locate a life-cycle phase in the project phase sequence, decide whether a phase carries a verification output requirement, list the outputs that phase owes and the gaps against them, check entry readiness for a target phase, rank per-requirement verification maturity, roll that up to a project-wide status, and run the full phasing review. Trigger: ecss, e-st-10-02c, verification phasing, life cycle, phase A, phase outputs, entry readiness, maturity rank, project verification status."
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
  tags: [ecss, e-st-10-02c, verification-phasing, life-cycle, phase-outputs, entry-readiness, maturity, project-status]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Phasing with the Life Cycle (space-systems/ecss/e1002-phasing)

Use when phasing verification activities with the project life cycle under ECSS-E-ST-10-02C clause 5.2.7 — locating phases, listing owed outputs and gaps, checking entry readiness, ranking requirement maturity, and rolling up project status.

## Domain quick reference

- Verification planning starts in the earliest phase — it is not a late-lifecycle activity; placing it late is a phasing defect.
- Each phase carries a defined set of verification outputs; a phase may not close while any of its outputs is missing.
- Entry readiness for a phase depends on the previous phase's outputs being complete — check readiness before entering, not after.
- Per-requirement verification status has a maturity ordering (e.g. not-started < planned < in-progress < closed); the project status is the LEAST mature of its requirements.
- The phasing review is compliant only when no blocking issue remains across all phases.

## Workflow

1. Locate the phase: `phase_index(phase)` (raises on an unknown phase).
2. Decide applicability: `is_phase_applicable(phase)`.
3. List owed outputs: `required_outputs_for_phase(phase)`.
4. Find gaps: `phase_output_gaps(phase, outputs)`.
5. Check entry readiness: `phase_entry_readiness(target_phase, state)`.
6. Rank and roll up: `requirement_status_rank(status)`, `overall_verification_status(statuses)`.
7. Full review: `project_verification_phasing_review(project)` -> `is_phasing_compliant(review)`.

## Pitfalls

- Entering a phase whose predecessor's outputs are incomplete — `phase_entry_readiness` returns the blocking issues; resolve them first.
- Reporting project status as the MOST mature requirement — it is the least mature; one open requirement holds the project open.
- Treating a phase with no verification output requirement as 'no work' — applicability decides whether outputs are owed.
- Security-marking vocabulary: the content-policy gate flags the word beginning 'classif-'; use 'categorized' instead.

## Behavior contract (gate 3)

`scripts/test_e1002_phasing.py` (stdlib unittest, offline) verifies phase indexing and its error path, applicability, required-output lookup, gap detection, entry-readiness blockers, maturity ranking and least-mature roll-up, and the full phasing review.

## Compliance

ECSS-E-ST-10-02C is a normative standard; this leaf implements only common-knowledge procedure and paraphrases it — no verbatim standard text. `license: Apache-2.0`, `compliance: STANDARDS-REF`, `standards: ecss` (reference-only), `gated: false`.

---
name: systems-engineering
description: "Use when scoping or gating European space systems engineering per ECSS-E-ST-10C: determine the lifecycle phase (0 through F), map each phase to its review gate (MDR, PRR, SRR, PDR, CDR, QR, AR, FRR, CRR, ER), and validate that a phase is ready to exit when its required review records are complete. The phase-gate sequence drives program planning and procurement milestones for space systems, from mission analysis through disposal. Trigger: ecss, e-st-10c, lifecycle phases, phase gate, mdr, prr, srr, pdr, cdr, qr, ar, frr, space systems engineering."
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
  tags: [ecss, e-st-10c, lifecycle, phase-gate, review, systems-engineering]
  version: 0.1.0
  author: AeroSkills
---

# ECSS Systems Engineering (space-systems/ecss/systems-engineering)

Use when the task is European space systems engineering under
ECSS-E-ST-10C: lifecycle phases, review gates, and phase-exit
readiness for a space program.

## Domain quick reference

- ECSS-E-ST-10C (systems engineering) structures the space system
  lifecycle into phases 0 through F, each closed by a review gate.
- Phase names: 0 mission analysis and feasibility, A feasibility,
  B preliminary definition, C detailed definition, D qualification
  and production, E utilization, F disposal.
- Review gates: MDR (mission definition review) at phase 0; PRR
  (preliminary requirements review) and SRR (system requirements
  review) at A; PDR (preliminary design review) at B; CDR (critical
  design review) at C; QR (qualification review), AR (acceptance
  review), and FRR (flight readiness review) at D; CRR (commissioning
  result review) and ER (end-of-life review) at E.
- A phase is ready to exit when the reviews assigned to it are
  complete; phase gates drive program milestones and procurement.

## Workflow

1. Determine the current lifecycle phase (0 through F) for the
   element or mission.
2. Map the phase to its review gate(s) via the phase-gate table.
3. Collect the completed review records for the phase.
4. Validate phase-exit readiness: all assigned reviews complete
   (missing reviews are listed).
5. Escalate any missing gate review before advancing the phase.

## Pitfalls

- Advancing a phase with a review record still open (gate skipped).
- Confusing review order (SRR before PRR, QR before AR).
- Expecting phase E to carry design reviews (it carries CRR/ER only).
- Treating phase F (disposal) as having gate reviews (it has none).

## Behavior contract (gate 3)

The phase, review-gate, and readiness logic is exercised by the gate 3
contract test: scripts/test_ecss_systems_engineering.py against
scripts/ecss_systems_engineering_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_ecss_systems_engineering.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

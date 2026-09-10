---
name: e10-technology
description: "Use when identifying critical technologies for a space project under ECSS-E-ST-10C clause 5.6.7, assessing their Technology Readiness Level (TRL) per E-AS-11 (ISO 16290), building the technology matrix, and defining the development plan that closes the gap to the TRL required for the project. Trigger: ecss, e-st-10c, technology plan, technology matrix, trl, technology readiness level, iso 16290, e-as-11, technology risk, critical technology, annex e, annex f."
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
  tags: [ecss, e-st-10c, technology-plan, technology-matrix, trl, iso-16290, technology-risk, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Technology Plan and Matrix (space-systems/ecss/e10-technology)

Use when the task is identifying critical technologies for a space
project under ECSS-E-ST-10C clause 5.6.7, assessing their Technology
Readiness Level (TRL) per E-AS-11 (ISO 16290), building the technology
matrix (Annex F content), and defining the development plan that
closes the gap to the TRL required for the project (Annex E content).

## Domain quick reference

- ECSS-E-ST-10C clause 5.6.7 requires the project to identify
  technologies that are critical to the project (not yet mature enough
  for the intended use), assess their current maturity, define the
  maturity required for the project, and plan the activities that
  close any gap, tracking the associated technology risk.
- Maturity is scored on the nine-level TRL scale defined by E-AS-11
  (ISO 16290), from TRL 1 (basic principles observed) through TRL 9
  (actual system flight proven through successful mission operations).
  A technology is critical only when its current TRL is below the TRL
  required for the project's intended use.
- The gap between current and required TRL drives technology risk:
  the larger the gap, the more schedule/cost/performance risk the
  immature technology carries, consistent with the project's technical
  risk process (M-ST-80, see the sibling e10-risk-mgmt leaf).
- This leaf scopes the assessment process: identifying critical
  technologies, scoring TRL gaps, and gating the technology plan on a
  defined development activity for every open gap. Producing the
  Technology Plan document to the Annex E DRD structure and the
  Technology Matrix document to the Annex F DRD structure are the
  sibling e10-tp-drd and e10-tech-matrix-drd leaves; this leaf supplies
  the assessed content those documents report.

## Workflow

1. For each candidate technology, record its description, current TRL
   (1-9, assessed per E-AS-11/ISO 16290 level definitions), the TRL
   required for the project's intended mission use, and the mission or
   sub-system it applies to.
2. Compute the TRL gap (required minus current, floored at zero) and
   classify technology risk from the gap: no gap is "none", a
   one-level gap is "low", a two-level gap is "medium", a gap of three
   or more levels is "high". A technology is critical only when the
   gap is greater than zero.
3. Enter every assessed technology into the technology matrix
   (status: identified for critical technologies, mature for the
   rest).
4. For each critical technology, define a development activity and a
   schedule to close the gap, and record it against the matrix entry
   (status: planned). This is the technology plan content.
5. As development proceeds and a technology is re-tested at a higher
   TRL, close the gap by recording the newly achieved TRL against a
   planned entry; recompute the gap and risk, and mark the entry
   mature once the required TRL is reached.
6. Check the matrix: the technology plan is ready only when every
   critical technology has a recorded development activity (status
   planned or later); do not baseline the plan with a critical
   technology still only "identified".

## Pitfalls

- Treating a technology as non-critical because it is in wide
  terrestrial use, without checking whether its TRL has actually been
  assessed for the project's intended (e.g. space, relevant
  environment) use — TRL is context-specific, not a technology's
  general reputation.
- Baselining the technology plan while a critical technology is still
  only "identified" with no recorded development activity — the gate
  is skipped.
- Recording an achieved TRL lower than the current TRL, or closing a
  gap on a technology that was never given a development plan.
- Confusing this leaf's technology maturity assessment with the
  broader project technical risk management process (identification,
  mitigation, residual tracking across the whole project) — see the
  sibling e10-risk-mgmt leaf (10C clause 5.6.8) — or with the Annex
  E/F document-structure leaves (e10-tp-drd, e10-tech-matrix-drd) that
  format this content into the DRD-mandated document layout.

## Behavior contract (gate 3)

The TRL validation, gap/risk scoring, development-plan gating, and
matrix-readiness logic is exercised by the gate 3 contract test:
scripts/test_e10_technology.py against
scripts/e10_technology_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_technology.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

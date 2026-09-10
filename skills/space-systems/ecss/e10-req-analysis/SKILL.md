---
name: e10-req-analysis
description: "Use when analysing customer or upper-level requirements to derive, generate, control and document the requirement set for a space system and for each lower level, per ECSS-E-ST-10C clause 5.2.1. Checks that every requirement traces to a customer requirement or an existing upper-level requirement (no orphans), carries identifying text and rationale (documented), and is under configuration control (released or baselined). Trigger: ecss, e-st-10c, requirement analysis, derive requirements, requirement derivation, requirement set, lower-level requirements, requirement control, 5.2.1."
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
  tags: [ecss, e-st-10c, requirement-analysis, requirement-derivation, traceability, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirement Analysis (space-systems/ecss/e10-req-analysis)

Use when the task is analysing customer or upper-level requirements
under ECSS-E-ST-10C clause 5.2.1: deriving, generating, controlling
and documenting the requirement set for the system and for each lower
level of the product tree.

## Domain quick reference

- ECSS-E-ST-10C §5.2.1 requires that customer/upper-level requirements
  are analysed and that a requirement set is produced for the system
  and for each lower level, and that this set is derived, generated,
  controlled, and documented.
- A requirement's origin is either "derived" (traced from analysis of
  an upper-level or customer requirement) or "generated" (added at
  this level to close a gap not directly implied by the upper level).
- Every requirement must trace, directly or through its parent chain,
  to a customer requirement; a requirement whose declared parent does
  not exist in the customer requirements or the requirement set is an
  orphan and breaks the derivation.
- "Controlled" means the requirement is under configuration control:
  released or baselined, not left in draft.
- "Documented" means the requirement carries identifying text and a
  rationale, not just an id.

## Workflow

1. Collect the customer/upper-level requirement ids that the system
   (or lower) level requirement set may trace to.
2. For each candidate requirement, record id, level, parent (its
   upper-level or customer requirement, or None for a customer-level
   requirement), text, rationale, origin (derived/generated), and
   control_status (draft/released/baselined).
3. Validate every requirement record (all fields present and
   non-empty, origin and control_status in the allowed sets).
4. Check derivation traceability across the whole set: every
   requirement's parent resolves to a customer requirement id or
   another requirement in the set (no orphans, no duplicate ids).
5. Check configuration-control readiness: every requirement is
   released or baselined before treating the set as controlled;
   list the ones still in draft.
6. Review level coverage (counts per level) to confirm the set spans
   the system level and each lower level in scope.

## Pitfalls

- A requirement recorded with a parent id that was never captured in
  the customer requirements or the requirement set (silent orphan).
- Treating a "draft" requirement as controlled because it has an id
  and text — control requires released or baselined.
- Requirement text copied from the parent with no rationale, which
  is documentation in form only.
- Duplicate requirement ids within the same level or across levels.

## Behavior contract (gate 3)

The validation, derivation-traceability, control-readiness, and
level-coverage logic is exercised by the gate 3 contract test:
scripts/test_e10_req_analysis.py against
scripts/e10_req_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_req_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

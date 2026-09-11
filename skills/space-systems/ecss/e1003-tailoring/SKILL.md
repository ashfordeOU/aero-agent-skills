---
name: e1003-tailoring
description: "Use when determine the tailoring profile of ECSS-E-ST-10-03C for a
  specific space project class (A–D) using the Annex D informative method: map each
  standard requirement to an applicability status (Applicable, Not Applicable,
  Tailored, or Conditional), assign verification methods, and produce a compliance
  matrix and a verification matrix. Apply when a project team must scope the system
  engineering requirements set to their mission category, justify deviations, and
  supply the matrices required by a review or product-assurance gate.
  Trigger: ecss, e-st-10-03c, tailoring, annex-d, compliance-matrix,
  verification-matrix, project-class, system-engineering, applicability."
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
  tags: [ecss, e-st-10-03c, tailoring, annex-d, compliance-matrix, verification-matrix, project-class]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering Tailoring — Annex D Method (space-systems/ecss/e1003-tailoring)

Use when the task is to determine the tailoring profile of ECSS-E-ST-10-03C for a
project, mapping each system-engineering requirement to an applicability status and
producing the compliance and verification matrices required for design reviews or
product-assurance gates.

## Domain quick reference

- ECSS-E-ST-10-03C Annex D (informative) provides a structured method for tailoring
  the standard's requirements to a project class. Project classes A through D reflect
  descending levels of mission criticality and complexity: Class A (flagship) carries
  the most stringent requirements set; Class D (small or commercial) carries the
  minimum mandatory set. The class is assigned per ECSS-M-ST-10C §4.
- Each requirement in the catalogue is given one of four applicability statuses:
  Applicable (A) — the requirement applies in full; Not Applicable (NA) — the
  requirement does not apply to this project class or mission type; Tailored (T) —
  the requirement applies in a modified form; Conditional (C) — the requirement
  applies only when certain project conditions hold. Tailored and Conditional
  entries must carry a documented rationale; the matrix is incomplete without it.
- The compliance matrix lists every catalogued requirement with its applicability
  status and rationale. The verification matrix lists only applicable requirements
  (status A, T, or C) and assigns at least one verification method — Test (T),
  Analysis (A), Inspection (I), or Review of Design (R) — to each.
- A requirement that is categorized as Not Applicable must not appear in the
  verification matrix; its presence would create a verification activity without a
  backing requirement, which review boards treat as a non-conformance.

## Workflow

1. Confirm the project class (A, B, C, or D) per the project's ECSS-M-ST-10C
   assignment. Reject any class value outside this set before proceeding; an
   unrecognised class has no defined tailoring profile.
2. Retrieve the default tailoring profile for that class from the Annex D catalogue.
   Each requirement has a default applicability status and a default set of
   verification methods for each project class.
3. Apply project-specific overrides: for each requirement the project team deviates
   from the default, record the revised applicability status, revised verification
   methods (where applicable), and a written rationale. Validate that each override
   uses a recognised applicability code and recognised verification method code.
4. Run the completeness check: every requirement with status A, T, or C must have at
   least one verification method assigned; every T or C entry must have a non-empty
   rationale. Resolve all findings before submitting the matrix to a gate.
5. Generate the compliance matrix from the completed tailoring matrix — one row per
   catalogue requirement, showing requirement ID, clause reference, title,
   applicability status, and rationale.
6. Generate the verification matrix from the same tailoring matrix — one row per
   applicable requirement (A/T/C only), showing requirement ID, clause reference,
   title, and assigned verification methods.
7. Submit both matrices to the project review or product-assurance gate. Report the
   count of Applicable, Not-Applicable, Tailored, and Conditional entries as a
   summary to support gate decision-making.

## Pitfalls

- Applying a single fixed applicability profile across all project classes — a
  Class D mission that adopts the full Class A set incurs avoidable engineering
  overhead; a Class A mission that adopts Class D defaults risks gaps at gates.
- Accepting a Tailored or Conditional status without a rationale — the matrix is
  contractually incomplete, and the completeness check exists to catch this before
  submission.
- Including a Not-Applicable requirement in the verification matrix as a precaution —
  this inflates the verification programme with activities that have no backing
  requirement; review boards will flag the mismatch.
- Treating the Annex D catalogue as exhaustive — it covers representative
  requirements; project-specific requirements derived from the mission (debris
  mitigation, payload-specific standards, export-control constraints) must be
  appended as additional rows before the matrices are finalised.

## Behavior contract (gate 3)

The project-class validation, tailoring-matrix construction, compliance-matrix
derivation, verification-matrix derivation, and completeness-check logic are exercised
by the gate 3 contract test: scripts/test_e1003_tailoring.py against
scripts/e1003_tailoring_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_tailoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e1002-pretailoring
description: "Use when apply the ECSS-E-ST-10-02C §6 pre-tailoring matrix to a space product type: determine the applicability level (applicable, recommended, optional, or not applicable) for each clause-5 verification requirement for the product category under assessment, identify every applicable requirement that must be covered, flag any applicable verification requirement absent from the project's captured requirement set, and produce the per-requirement applicability record for engineering review. Product categories cover space system, segment, equipment, and payload. Trigger: ecss, e-st-10-02c, pretailoring, verification-matrix, product-type, verification-requirements, clause-5, requirements-applicability."
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
  tags: [ecss, e-st-10-02c, pretailoring, verification-matrix, product-type, verification-requirements, clause-5, requirements-applicability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Pre-tailoring Matrix (space-systems/ecss/e1002-pretailoring)

Use when the task is applying the ECSS-E-ST-10-02C §6 pre-tailoring matrix
to a declared space product type — determining which clause-5 verification
requirements are applicable, recommended, optional, or not applicable for
that category, and checking the project's captured requirement set for
coverage gaps.

## Domain quick reference

- ECSS-E-ST-10-02C §6 defines a fixed pre-tailoring matrix that maps
  each clause-5 verification requirement to an applicability level for
  four product categories: space system (the complete, top-level space
  system), segment (space, ground, or launch segment within that system),
  equipment (unit or assembly at equipment level), and payload (science
  or mission payload).
- The four applicability levels are: applicable (the requirement must be
  complied with for this product type), recommended (the requirement
  should be included unless the project records a justified deviation),
  optional (a project decision to include or omit, not requiring a
  deviation rationale), and not_applicable (excluded for this product
  type; carrying it forward without justification is itself a finding).
- Pre-tailoring resolves applicability for the declared product type
  before project-specific tailoring adjusts individual requirements for
  risk, criticality, or programme constraints. Pre-tailoring output is
  the input to project-specific tailoring, not a substitute for it.
- A project's captured requirement set must contain every requirement
  whose applicability resolves to "applicable" for the declared product
  type. Requirements at "recommended" level that are omitted require a
  recorded justification. Requirements at "optional" or "not_applicable"
  that are included do not require justification, but any "not_applicable"
  requirement included without one is flagged as a scope anomaly.

## Workflow

1. Declare the space product type for the element under assessment:
   space_system, segment, equipment, or payload. Reject any product type
   outside the four recognized categories before proceeding.
2. Apply the §6 pre-tailoring matrix for that product type: retrieve the
   applicability level for each clause-5 verification requirement. The
   result is the resolved applicability record — one row per requirement.
3. Identify the applicable subset: all requirements whose resolved level
   is "applicable". These are mandatory for the declared product type and
   must each appear in the project's captured requirement set.
4. Check the project's captured requirement set against the applicable
   subset: flag every applicable requirement that is absent (a
   missing-applicable finding). Reject any captured requirement ID that
   is not recognized in the clause-5 set (an unknown-requirement finding).
5. Optionally check for scope anomalies: flag any captured requirement
   whose resolved level is "not_applicable" (a carried-forward-out-of-
   scope finding), since including it without justification is a
   pre-tailoring deviation.
6. Aggregate findings. Pre-tailoring is complete only when there are no
   missing-applicable findings and no unknown-requirement findings.
   Recommended-level omissions and scope anomalies are advisory findings
   that require recorded justification, not blockers.

## Pitfalls

- Skipping the product-type declaration and applying the matrix for the
  wrong category — the applicability levels differ substantially between
  space_system and equipment; using the wrong row understates or overstates
  mandatory scope.
- Treating a "recommended" level as either fully mandatory or fully
  optional — it sits between the two: it must be included unless the
  project records a specific deviation, which distinguishes it from an
  "optional" requirement that needs no justification to omit.
- Treating pre-tailoring as the final tailoring step — §6 pre-tailoring
  produces the starting applicable/recommended set for project-specific
  tailoring, which must then run separately to adjust for risk,
  criticality, and programme constraints under ECSS-S-ST-00-01.
- Accepting a captured set with unknown requirement IDs without raising
  a finding — an ID absent from the clause-5 set indicates either a
  transcription error or a reference to a requirement outside the matrix
  scope, both of which must be resolved before tailoring is considered
  complete.

## Behavior contract (gate 3)

The product-type validation, applicability lookup, full-matrix
application, and pretailoring-violations check logic is exercised by the
gate 3 contract test: scripts/test_e1002_pretailoring.py against
scripts/e1002_pretailoring_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_pretailoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

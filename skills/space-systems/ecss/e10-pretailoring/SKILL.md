---
name: e10-pretailoring
description: "Use when applying the ECSS-E-ST-10C clause 7 pre-tailoring matrix to a space project: for the project's declared space product type (e.g. space segment, ground segment, launch service segment element), determine which clause-5 system-engineering requirements are applicable, optional, or not applicable, before project-specific tailoring per ECSS-S-ST-00-01. Checks the matrix itself is complete and well-formed, and checks the project's carried-forward requirement clauses against the resolved applicability (missing mandatory clauses, out-of-scope clauses kept without justification, unknown clause ids). Trigger: ecss, e-st-10c, pre-tailoring, pretailoring matrix, tailoring matrix, product type, applicability, clause 7."
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
  tags: [ecss, e-st-10c, pre-tailoring, tailoring-matrix, product-type, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Pre-tailoring (space-systems/ecss/e10-pretailoring)

Use when the task is applying the ECSS-E-ST-10C clause 7 pre-tailoring
matrix: deciding, for the project's space product type, which of the
standard's clause-5 requirements apply, are optional, or do not apply,
before the project runs its own tailoring pass.

## Domain quick reference

- ECSS-E-ST-10C clause 7 pre-tailors the standard's requirements by
  space product type before a project applies its own project-specific
  tailoring (criticality, risk, budget) under ECSS-S-ST-00-01.
- A pre-tailoring matrix maps each clause id to a status per product
  type: applicable (mandatory for that product type), optional (a
  project decision to include or drop, recorded elsewhere), or
  not_applicable (excluded for that product type).
- Common space product type categories used for pre-tailoring are the
  space segment, the ground segment, and the launch service segment;
  a given project element declares which one it is.
- Pre-tailoring happens once, ahead of and independent from the
  project-specific tailoring step; a project must not skip pre-tailoring
  and jump straight to project-specific tailoring, because
  project-specific tailoring only adjusts the applicable/optional set
  pre-tailoring already produced, it does not decide product-type
  scope from scratch.
- Carrying forward a requirement whose clause is marked not_applicable
  for the declared product type, or dropping a clause marked
  applicable, without a recorded justification, breaks pre-tailoring.

## Workflow

1. Assemble the pre-tailoring matrix as a mapping of clause id to a
   per-product-type status (applicable/optional/not_applicable),
   covering every product type in scope for the programme.
2. Validate the matrix: every clause has an entry for every product
   type in scope, every status is one of the three allowed values, and
   no clause is missing or has an unrecognised product type key.
3. Declare the product type for the project element being tailored
   (space segment, ground segment, launch service segment, or another
   agreed category).
4. Resolve applicability for that product type: the set of applicable
   (mandatory), optional, and not-applicable clause ids.
5. Compare the project's carried-forward requirement clause ids against
   the resolved sets: flag applicable clauses with no carried-forward
   requirement (missing mandatory), carried-forward clauses that
   resolve to not_applicable (out-of-scope), and carried-forward clause
   ids absent from the matrix entirely (unknown clause).
6. Treat pre-tailoring as complete only when there are no missing
   mandatory, out-of-scope, or unknown-clause findings; only then hand
   the resolved applicable/optional set to project-specific tailoring.

## Pitfalls

- Reusing a pre-tailoring matrix built for one product type (e.g.
  ground segment) against a project element of a different product
  type (e.g. space segment) without re-resolving applicability.
- Treating an optional clause as either mandatory or excluded by
  default — optional clauses need an explicit project decision, not an
  assumption in either direction.
- Silently dropping an applicable (mandatory) clause instead of
  surfacing it as a missing-mandatory finding.
- Running project-specific tailoring against a matrix that has not
  been validated for completeness (a clause missing a product-type
  entry resolves to nothing and hides a scope decision).

## Behavior contract (gate 3)

The matrix-validation, applicability-resolution, and compliance-check
logic is exercised by the gate 3 contract test:
scripts/test_e10_pretailoring.py against
scripts/e10_pretailoring_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_pretailoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: structural-requirements-spec
description: "Use when define and document the structural functional and performance
  requirement baseline for a spacecraft or launch vehicle structure under ECSS-E-ST-32C
  clause 4: categorize each structural requirement as functional (stiffness, strength,
  stability, fracture control, buckling) or performance (margin of safety, design
  load, factor of safety, mass budget, deflection limit), verify the requirement set
  is complete with a threshold value and a verification method for each entry, compute
  Design Limit Loads from the mechanical environment specification by applying dynamic
  and quasi-static factors, derive Design Yield and Ultimate Loads by applying the
  applicable factors of safety, and flag any allowable exceedance or missing allowable
  entries. Trigger: ecss, e-st-32-structures-scope, structural-requirements,
  requirement-baseline, design-loads, margin-of-safety, factors-of-safety, stiffness,
  strength."
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
  tags: [ecss, e-st-32-structures-scope, structural-requirements, requirement-baseline, design-loads, margin-of-safety, factors-of-safety, stiffness, strength]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural Requirements Specification (space-systems/ecss/structural-requirements-spec)

Use when the task is to define and document the structural requirement baseline for a
spacecraft or launch vehicle structure per ECSS-E-ST-32C clause 4 — categorizing
structural requirements by type, computing design loads from the mechanical environment,
and verifying that every requirement is complete, consistent, and traceable.

## Domain quick reference

- ECSS-E-ST-32C clause 4 splits structural requirements into two groups: functional
  (what the structure must do — stiffness, strength, stability, buckling resistance,
  fracture control) and performance (how well it must do it — margin of safety,
  design load envelope, factor of safety, deflection limit, mass budget). Each
  requirement is placed into exactly one group before the baseline is assessed.
- Design Limit Load (DLL) is the upper-bound load the structure must sustain without
  permanent deformation. It is derived from the nominal mechanical environment load
  by applying a dynamic amplification factor and a quasi-static load factor. Both
  factors must be ≥ 1.0 (they amplify, never reduce, the environment load).
- Design Yield Load (DYL) and Design Ultimate Load (DUL) are derived from the DLL by
  multiplying by the yield and ultimate factors of safety respectively. The ultimate
  factor must be ≥ the yield factor. For metallic structures under ECSS-E-ST-32C the
  minimum ultimate factor of safety is 1.25 on DLL; fracture-critical and composite
  items carry higher factors per the standard's table.
- Margin of Safety (MoS) = allowable / applied − 1. A MoS > 0 is compliant; MoS ≤ 0
  is a finding. A surface or component with no allowable on record cannot be assessed
  and is itself a finding — the baseline is incomplete.
- Every requirement in the baseline must carry three fields: a threshold (the
  quantitative acceptance criterion), a verification method (analysis, test,
  inspection, similarity, or review), and a unique identifier. A requirement missing
  any of these fields is incomplete and must be resolved before the baseline is
  baselined.

## Workflow

1. Collect all candidate structural requirements from the system-level specification,
   the mechanical environment specification, and the interface control documents.
   Assign a unique identifier to each requirement if one is not already present.
2. Categorize each requirement as functional or performance. Reject any requirement
   whose type cannot be recognized and log it as an open item to be resolved with the
   responsible engineer.
3. For each requirement, confirm that a threshold value and a verification method are
   on record. Flag any requirement missing either field; do not include incomplete
   requirements in the compliant baseline count.
4. For each load case in the mechanical environment specification, compute the DLL
   from the nominal environment load by applying the dynamic and quasi-static factors.
   Then derive the DYL and DUL by applying the applicable factors of safety from
   ECSS-E-ST-32C clause 4 (or project-tailored values if agreed with the customer).
5. For each structural element or assembly, compute the MoS at the DUL using the
   material or component allowable. Flag any element where MoS ≤ 0 as a strength
   finding. Flag any element with no allowable on record as an incomplete baseline
   entry.
6. Aggregate all findings from steps 2–5. The requirement baseline is not ready for
   formal review until the finding list is empty and every requirement carries a
   threshold, a verification method, and a positive MoS against its governing load case.

## Pitfalls

- Applying the nominal environment load directly as the DLL without accounting for
  dynamic amplification. The environment specification gives the external excitation;
  the DLL adds the amplification factors on top — skipping them underestimates the
  design load.
- Using the same factor of safety for all materials and configurations. ECSS-E-ST-32C
  provides material-class-specific factors; composites, fracture-critical joints, and
  pressure vessels each carry requirements beyond the metallic-structure default.
- Treating a requirement with no threshold as "to be defined" and counting it as
  compliant. An undefined threshold means the requirement is unverifiable; it must be
  flagged as incomplete, not carried as a placeholder.
- Recording MoS > 0 at yield load only and not checking the ultimate load. The
  governing check for permanent deformation is at DYL; the governing check for rupture
  is at DUL. Both must pass independently.
- Closing the baseline with open-item requirements still in the list. Every requirement
  in a formal baseline must be complete; open items must be resolved or formally
  deferred with a risk acceptance before the baseline review.

## Behavior contract (gate 3)

The requirement categorization, design-load derivation, margin-of-safety computation,
and requirement-set validation logic is exercised by the gate 3 contract test:
scripts/test_structural_requirements_spec.py against
scripts/structural_requirements_spec_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_structural_requirements_spec.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

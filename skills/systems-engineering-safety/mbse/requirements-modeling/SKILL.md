---
name: requirements-modeling
description: "Use when you must model system requirements in a SysML requirements diagram for model-based systems engineering: define requirement stereotype attributes (id, text, kind, priority, source), connect requirements with derive, satisfy, verify, refine, and trace relationships, roll up verification status through the requirement tree, and screen requirement text for atomicity, vague terms, and verifiability gaps. Produces the requirement tree with its status rollup, the coverage gaps for unsatisfied and unverified requirements, and the quality screening verdict that gates the SysML model review. Trigger: requirements diagram, requirement stereotype, derive relationship, satisfy link, verify link, status rollup, vague terms, verifiability."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: mbse
  tags: [requirements-modeling, sysml-requirement-diagram, requirement-stereotype, requirement-tree, derive-relationship, satisfy-relationship, verify-relationship, trace-relationship, verification-status-rollup, vague-term-screening, requirement-atomicity, requirement-id-validation, requirement-verifiability, requirement-coverage]
  version: 0.1.0
  author: AeroSkills
---

# SysML Requirements Modeling (systems-engineering-safety/mbse/requirements-modeling)

Use when the task is modeling system requirements in a SysML
requirements diagram: defining requirement stereotype attributes,
building the derive and satisfy and verify relationships, rolling up
verification status through the requirement tree, and screening
requirement text for quality gaps.

## Domain quick reference

- Requirement stereotype: a SysML requirement is modeled with the
  requirement stereotype and carries attributes: id, text, kind
  (functional, performance, interface, constraint), priority, source.
- Relationships: derive (deriveReqt) links a derived requirement to its
  parent source; satisfy links a requirement to the design element that
  fulfills it; verify links a requirement to the verification artifact;
  refine and trace carry context through the model.
- Requirement id: a canonical id like SYS-001 or FC-0001 identifies
  the requirement in the tree and in trace reports; the format is
  checked before the model review.
- Atomicity: a requirement states exactly one shall clause; two shall
  clauses in one text are two requirements and are split before review.
- Verifiability: a requirement is verifiable when it has exactly one
  shall clause, no vague terms, and an assigned verification method
  (test, analysis, demonstration, or inspection).
- Vague terms: adequate, approximately, etc, suitable, and/or, as
  required, timely, minimize, and maximize make a requirement
  unverifiable because the acceptance bound is not measurable.
- Status roll-up: a parent requirement is verified only when every
  child in its requirement tree is verified; any failed child fails
  the parent; in-review children keep the parent in-review.
- Coverage: every requirement needs at least one satisfy link and one
  verify link; the coverage fraction is satisfied or verified
  requirements over the total, and the gaps are the unlinked ids.

## Workflow

1. Collect the requirements with their stereotype attributes and check
   every id with validate_requirement_id.
2. Screen the text: count_shall_clauses for atomicity, find_vague_terms
   for quality, and requirement_verifiability for the review verdict.
3. Build the relationship set: derive links from the parent tree,
   satisfy links to design elements, verify links to verification
   artifacts; check kinds with relationship_kind_valid and the derive
   chain with derive_chain_check.
4. Roll up verification status through the tree with
   rollup_verification_status.
5. Measure coverage with satisfy_coverage and verify_coverage and list
   the unsatisfied and unverified requirements.
6. Combine the measures with model_review_verdict and gate the SysML
   requirements model review on the verdict.

## Pitfalls

- Modeling two shall clauses as one requirement; atomicity is one
  clause per requirement, and the split happens before review.
- Forgetting the derive link when a child requirement is introduced;
  a derived requirement without a parent source is an orphan.
- Declaring a requirement verified while a child in its tree is
  in-review; roll-up only reports verified when every child is
  verified.
- Accepting vague wording; adequate and approximately have no
  measurable bound and the verification method cannot be applied.
- Counting coverage without listing gaps; a high fraction can still
  hide an unsatisfied safety requirement.
- Using a free-form id; the id format check keeps the trace reports
  and the requirement tree consistent.
- Treating a satisfy link as a verify link; satisfying design does
  not verify the requirement, and both links are required.

## Behavior contract (gate 3)

The requirements modeling logic is exercised by the gate 3 contract
test: scripts/test_requirements_modeling.py against
scripts/requirements_modeling_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_requirements_modeling.py

## Compliance

- Standards referenced, not reproduced: ARP4754A frames the
  requirements development and validation process that the SysML
  requirement model supports, and ARP4761A frames the derived
  requirements that flow from the safety assessment into the model;
  both are proprietary (SAE), summary-only per standards-map.yaml and
  brief 06. SysML requirement diagram semantics are common engineering
  knowledge.
- compliance: STANDARDS-REF, gated: false.

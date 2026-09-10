---
name: e10-req-verif-methods
description: "Use when every requirement in an ECSS-E-ST-10C requirements set needs a verification method (test, analysis, review-of-design, inspection) and a verification level (equipment, subsystem, element, segment, system) assigned before verification planning, consistent with E-ST-10-02 verification methods/levels and E-ST-10-03 testing. Trigger: verification method, review of design, ROD, verification level, test analysis inspection, verification matrix, E-ST-10-02, E-ST-10-03, requirement verification, ecss, e-st-10c."
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
  tags: [ecss, e-st-10c, verification-method, verification-level, review-of-design, requirements-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirement Verification Method & Level Assignment (space-systems/ecss/e10-req-verif-methods)

Use when the task is assigning a verification method and a verification
level to requirements under ECSS-E-ST-10C, ahead of detailed
verification planning (E-ST-10-02) and test planning (E-ST-10-03).

## Domain quick reference

- ECSS-E-ST-10C clause 5.2.3.4 requires that every requirement carry a
  verification method and a verification level as part of requirement
  engineering, before the detailed verification programme is planned
  under E-ST-10-02.
- Four verification methods (detailed in E-ST-10-02 clause 5.2.2): test
  (measurement under representative or controlled conditions), analysis
  (calculation, modelling, simulation, or similarity/heritage
  argument), review of design (examination of existing design or
  heritage records), inspection (visual or dimensional examination of a
  physical characteristic).
- Verification levels (E-ST-10-02 clause 5.2.3) run equipment,
  subsystem, element, segment, system. A requirement is normally
  verified at the level it is allocated to (see the sibling
  e10-req-allocation leaf), unless compliance is only observable once
  the element is integrated with its neighbours (an interface or
  emergent-behaviour requirement), in which case verification moves up
  one level.
- Safety-critical requirements should not be closed out by review of
  design alone; test is preferred when feasible, analysis is the
  fallback when it is not.

## Workflow

1. For each requirement, capture its verification-relevant attributes:
   characteristic category (physical, functional, design, or
   performance), whether test is feasible, whether existing design or
   heritage evidence already covers it, whether it is safety-critical,
   and the product-tree level it is allocated to.
2. Select the verification method by precedence: physical
   characteristic -> inspection; else safety-critical -> test if
   feasible, otherwise analysis; else existing heritage evidence ->
   review of design; else test if feasible; otherwise analysis.
3. Assign the verification level: default to the requirement's
   allocation level; bump one level up only for an interface or
   emergent-behaviour requirement whose compliance is only observable
   after integration (a system-level requirement stays at system).
4. Build the verification matrix: one (method, level) pair per
   requirement id, and confirm no requirement id from the input set is
   missing from the matrix -- clause 5.2.3.4 calls for a method and a
   level on every requirement, not a sample.
5. Before closing the assignment, re-check any manually overridden
   method against the safety-critical rule and flag violations (a
   safety-critical requirement overridden to review of design) for
   engineering disposition rather than silently accepting them.
6. Hand the matrix to the Verification Plan / VCD (E-ST-10-02 clause
   5.2.8) and to test planning (E-ST-10-03) for every requirement
   assigned the test method.

## Pitfalls

- Defaulting every requirement to test regardless of feasibility,
  driving unnecessary cost and schedule instead of using analysis or
  review of design where they are legitimate.
- Closing out a safety-critical requirement by review of design alone.
- Leaving an interface or emergent-behaviour requirement assigned at
  its component level instead of the integrated level where the
  interaction is actually observable.
- Dropping requirements from the matrix -- an incomplete matrix fails
  the "every requirement" mandate of clause 5.2.3.4 even if the
  requirements present are assigned correctly.

## Behavior contract (gate 3)

The method-selection, level-assignment, matrix-completeness, and
safety-override logic is exercised by the gate 3 contract test:
scripts/test_e10_req_verif_methods.py against
scripts/e10_req_verif_methods_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_req_verif_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

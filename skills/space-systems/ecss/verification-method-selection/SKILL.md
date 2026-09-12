---
name: verification-method-selection
description: "Use when select and agree the structural verification methods for each
  requirement in the programme under ECSS-E-ST-32C clause 4.6.1 and 4.6.2.1: assign
  each structural requirement to one or more of the four methods (analysis, test,
  review of design, inspection), confirm the method selected is appropriate for the
  requirement category, verify that mandatory methods are present where the standard
  requires them, and produce a coverage assessment showing method rationale across
  the full requirements register. Trigger: ecss, e-st-32-structures-scope,
  verification-method-selection, structural-analysis-method, structural-test-method,
  review-of-design, structural-inspection-method, verification-programme,
  structural-requirements."
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
  tags: [ecss, e-st-32-structures-scope, verification-method-selection, structural-analysis-method, structural-test-method, review-of-design, structural-inspection-method, verification-programme, structural-requirements]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural Verification — Method Selection (space-systems/ecss/verification-method-selection)

Use when the task is to select and agree the verification methods for
structural requirements under ECSS-E-ST-32C clause 4.6.1 and 4.6.2.1 —
assigning each requirement to one or more of the four recognized methods,
confirming the method is appropriate for the requirement category, and
producing a documented coverage assessment for the full verification
programme.

## Domain quick reference

- ECSS-E-ST-32C clause 4.6.1 requires that the verification programme
  identify, for every structural requirement, the method or methods by
  which compliance will be demonstrated before the programme begins.
  Clause 4.6.2.1 defines four recognized methods and the conditions
  under which each is appropriate.
- The four methods are: **Analysis (A)** — compliance demonstrated by
  computation or simulation using a qualified model; **Test (T)** —
  compliance demonstrated by physical measurement on a hardware item
  under controlled conditions; **Review of Design (RoD)** — compliance
  demonstrated by examining drawings, design documentation, or
  specifications; and **Inspection (I)** — compliance demonstrated by
  direct physical examination of the hardware.
- Each requirement category carries a set of acceptable methods and, in
  some cases, a mandatory method. Structural strength and stiffness
  requirements must include analysis; environmental qualification
  requirements must include test; workmanship requirements must include
  inspection. Assigning only an unacceptable method for a category is a
  coverage gap, not a conservative choice.
- Every requirement in the requirements register must carry at least one
  assigned method before the verification programme is considered
  adequate. A requirement with no assigned method is an uncovered
  requirement — a programme gap, not a deferred item.

## Workflow

1. Collect the full structural requirements register. For each
   requirement, identify its category (structural strength, structural
   stiffness, mass properties, interface geometry, functional
   performance, environmental qualification, or workmanship).
   Reject or flag any requirement whose category cannot be determined
   before proceeding to method selection.
2. For each requirement, select the method or combination of methods
   from the four recognized options (A, T, RoD, I) that will
   demonstrate compliance. Consult the acceptable-method table for the
   requirement category and confirm that every selected method appears
   in that table. If a proposed method is not listed for that category,
   flag it as an invalid assignment before recording it.
3. Check mandatory methods. Where the standard requires a specific
   method for a category (e.g., analysis for strength, test for
   environmental qualification, inspection for workmanship), confirm
   that method appears in the assignment. A mandatory method that is
   absent is a coverage finding, not a choice.
4. Record a rationale statement for each assignment, explaining why the
   selected method or combination is sufficient to demonstrate
   compliance for that specific requirement. The rationale is the
   justification record required by clause 4.6.1.
5. Assemble the programme-level coverage summary: total requirements,
   covered requirements (those with at least one valid method),
   uncovered requirements (those with no method), and invalid
   assignments (those using a method not acceptable for the category).
   The programme is adequate only when covered equals total and invalid
   assignments is zero.
6. Resolve every finding before the verification programme is submitted
   for agreement. An uncovered requirement or an invalid assignment must
   be corrected in the requirements register, not carried as a risk.

## Pitfalls

- Assigning a method without checking category acceptability — applying
  inspection to a structural strength requirement is not conservative,
  it is an invalid assignment that leaves the strength requirement
  without a compliant demonstration path.
- Treating "no method assigned yet" as a temporary state that can be
  resolved later — clause 4.6.1 requires method agreement before the
  programme begins; an unassigned requirement is a programme gap, not
  a planning placeholder.
- Omitting the mandatory method while adding optional ones — a strength
  requirement with only test assigned but no analysis is non-compliant
  under clause 4.6.2.1 even though test is an acceptable method for
  that category.
- Recording a rationale that simply restates the method name rather than
  explaining why it is sufficient for the specific requirement — the
  rationale must justify coverage, not describe the method.
- Conflating RoD and Inspection — review of design examines documents
  and drawings; inspection examines physical hardware. They are not
  interchangeable, and the correct one depends on what evidence is
  being produced.

## Behavior contract (gate 3)

The method acceptability, mandatory-method check, and programme-coverage
logic is exercised by the gate 3 contract test:
scripts/test_verification_method_selection.py against
scripts/verification_method_selection_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_verification_method_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

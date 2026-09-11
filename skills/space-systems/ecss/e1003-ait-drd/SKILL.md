---
name: e1003-ait-drd
description: "Use when validate an Assembly, Integration and Test (AIT) plan against the ECSS-E-ST-10C Annex A Document Requirements Definition: verify all required DRD sections are present (objectives, product tree, test campaign, schedule, facilities, responsibilities), confirm every test traces to at least one verifiable requirement, check that every product tree item carries at least one test assignment, and flag tests that need a special facility but carry no facility reference. Trigger: ecss, e-st-10c, e-st-10-system-scope, ait-plan, assembly-integration-test, drd, test-traceability, product-tree, facility-assignment."
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
  tags: [ecss, e-st-10c, e-st-10-system-scope, ait-plan, assembly-integration-test, drd, test-traceability, product-tree]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Systems Engineering — AIT Plan DRD (space-systems/ecss/e1003-ait-drd)

Use when the task is generating or validating an Assembly, Integration
and Test (AIT) plan against the Document Requirements Definition of
ECSS-E-ST-10C Annex A -- confirming required sections are present,
tracing every test to a verifiable requirement, verifying product tree
coverage, and checking that facility-dependent tests have a facility
reference on record.

## Domain quick reference

- The ECSS-E-ST-10C Annex A AIT DRD specifies what a conforming AIT
  plan must contain. Required sections are: objectives (scope and AIT
  strategy), product tree (the integration hierarchy from piece parts
  through equipment, subsystem, and system), test campaign (which tests
  at which level for each product tree item), schedule (AIT milestones
  and baseline), facilities (GSE and test infrastructure), and
  responsibilities (organisational roles for each AIT activity).
- Every test in the campaign must be traceable to at least one
  verifiable requirement from the applicable requirements baseline; a
  test with no requirement reference is untraceable and must be
  resolved before the plan is baselined.
- Every item in the product tree must be covered by at least one test
  at an appropriate integration level (piece_part, equipment,
  subsystem, or system). An uncovered item means either the test was
  omitted or the product tree was not updated after the campaign was
  defined.
- Tests that cannot be executed at the prime contractor's facilities
  (thermal-vacuum, vibration, EMC, etc.) must carry an explicit
  facility assignment; a test flagged as needing a special facility
  with no facility reference is a planning gap that blocks scheduling.

## Workflow

1. Collect the draft AIT plan document and its associated product tree,
   test list, and requirements baseline.
2. Check that all six required DRD sections are present and non-empty;
   record a missing-section finding for each absent or blank section.
3. For every test in the campaign, verify it references at least one
   requirement ID from the baseline; record an untraceable-test finding
   for each test with an empty requirements list.
4. Build the coverage map: for each product tree item, list the tests
   assigned to it; record an uncovered-item finding for every item with
   no tests assigned.
5. For every test marked as needing a special facility, confirm a
   facility name or identifier is on record; record an
   unassigned-facility finding for each test where the facility field
   is absent or blank.
6. Aggregate the four finding categories; the AIT plan satisfies the
   DRD only when all four lists are empty.

## Pitfalls

- Treating a section that exists but contains only a placeholder
  ("TBD", empty string) as present -- the DRD requires substantive
  content; the section check treats any falsy value as missing.
- Assuming a test is traceable because the test type is well-named --
  traceability requires an explicit requirements reference list, not
  an inferred connection from the test title.
- Marking a product tree item as covered because a related item at a
  different level has a test -- coverage is item-by-item; a parent item
  is not covered by its child's test, and a child item is not covered
  by its parent's test.
- Leaving the facility field blank for an environmental test on the
  grounds that "the facility will be determined later" -- the AIT plan
  baseline requires facility assignments to be resolved, not deferred.

## Behavior contract (gate 3)

The section-presence, traceability, coverage, and facility-assignment
logic is exercised by the gate 3 contract test:
scripts/test_e1003_ait_drd.py against scripts/e1003_ait_drd_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1003_ait_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

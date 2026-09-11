---
name: e1011-test-drd
description: "Use when generate and validate the Human Factors Engineering (HFE) test report against the ECSS-E-ST-10-11C Annex D Document Requirements Definition (DRD): confirm all mandatory sections are present and complete, verify participant counts meet the minimum for the test type (formative or summative), check that every finding is assigned a severity category (critical, major, or minor), confirm each finding has at least one linked recommendation, and verify that all planned test scenarios are represented in the execution record. Trigger: ecss, e-st-10-11c, hfe, human-factors, test-report, drd, findings, recommendations, usability-test."
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
  tags: [ecss, e-st-10-system-scope, hfe, human-factors, test-report, drd, findings, usability-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — HFE Test Report DRD Validation (space-systems/ecss/e1011-test-drd)

Use when the task is to generate or validate the Human Factors Engineering (HFE)
test report required by ECSS-E-ST-10-11C Annex D (normative): checking that the
report satisfies the DRD's mandatory section list, that participant counts meet the
minimum threshold for the test type, that every finding carries a severity category,
that each finding is linked to at least one recommendation, and that all planned
test scenarios appear in the execution record.

## Domain quick reference

- ECSS-E-ST-10-11C Annex D defines a normative DRD for the HFE test report, the
  document produced after each HFE evaluation event. The DRD specifies mandatory
  sections and content elements; a report submitted to a project review must satisfy
  all of them before it can be formally accepted.
- Mandatory sections are: document identification (title, issue, date, reference),
  objectives (what was being assessed and against which HFE requirements), test
  environment (facilities, simulations, or mockups used), participants (count,
  screening criteria, role summary), test scenarios (the tasks executed), results
  (quantitative metrics such as task completion rate, error count, time on task),
  findings (usability issues and non-conformances identified), and recommendations
  (corrective or improvement actions linked to findings).
- Findings are categorized by severity: critical (prevents task completion or
  creates a safety risk), major (significantly impairs task performance), or minor
  (causes inconvenience with limited mission impact). An unrecognized severity
  label is a non-conformance.
- Participant count minimums reflect accepted usability practice anchored in the
  HFE assessment process requirements of the standard: at least three participants
  for a formative evaluation (iterative design feedback during development) and at
  least five for a summative evaluation (final acceptance verification).
- Every finding must be traceable to at least one recommendation; a finding with
  no linked recommendation is an open action that blocks report closure.
- Scenario coverage: each scenario listed in the test plan must have a
  corresponding execution record in the report; an unexecuted planned scenario
  must be explicitly documented as a gap.

## Workflow

1. Verify the report contains all eight mandatory sections. Record each missing
   section by name before moving to content checks; a missing section is a
   DRD non-conformance regardless of what the remaining sections contain.
2. Confirm the test type is recognized (formative or summative) and that the
   participant count meets the corresponding minimum. An unrecognized test type
   or a below-minimum count is a non-conformance.
3. For each finding, confirm the severity is one of the three recognized levels
   (critical, major, minor). Findings with an unrecognized severity label are
   flagged individually.
4. Check finding-to-recommendation traceability: every finding identifier must
   appear as the target of at least one recommendation. List each unlinked
   finding identifier as an open action.
5. Check scenario coverage: compare the set of planned scenario identifiers to
   the set of executed scenario identifiers. Return each planned scenario that is
   absent from the execution record.
6. Aggregate all findings; the report is DRD-compliant only when all five
   violation lists (missing sections, participant violation, invalid severity
   findings, unlinked findings, uncovered scenarios) are empty.

## Pitfalls

- Accepting a report that lists all section headings but leaves content fields
  empty — a section heading without content fails the DRD just as badly as a
  missing section.
- Applying the summative minimum (five participants) to a formative evaluation —
  the two test types have different minimum thresholds; applying the higher bar
  to formative evaluations will reject valid iterative assessments.
- Treating a finding with severity "moderate" or "high" as equivalent to a
  recognized level — the DRD recognizes exactly critical, major, and minor;
  non-standard labels must be corrected, not carried forward.
- Counting a recommendation without an explicit finding reference as covering
  all findings — linkage is per finding identifier; a generic recommendation
  without a finding ID does not satisfy the traceability requirement.
- Marking scenario coverage satisfied when all scenarios were attempted but
  some were aborted — an aborted scenario must appear in the execution record
  with an explicit abort justification; it is not the same as a completed
  execution.

## Behavior contract (gate 3)

The mandatory-section check, participant count validation, finding severity
validation, finding-to-recommendation linkage check, and scenario coverage check
are exercised by the gate 3 contract test:
scripts/test_e1011_test_drd.py against scripts/e1011_test_drd_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1011_test_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

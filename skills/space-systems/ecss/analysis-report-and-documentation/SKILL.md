---
name: analysis-report-and-documentation
description: "Use when document or verify a structural analysis report under ECSS-E-ST-32C clause 5.2 or a Leak-Before-Break (LBB) report under clause 5.3.5: confirm the report covers every required section (objectives, applicable documents, model description, load cases, material properties, analysis methodology, results, margin of safety, and conclusions), compute the margin of safety from applied and allowable loads for each load case, check that each LBB report includes fracture toughness data, crack-growth curve, critical crack size, inspection intervals, and a leak-detection rationale, and flag any missing deliverable before the report is submitted. Trigger: ecss, e-st-32-structures-scope, structural-analysis-report, lbb-report, margin-of-safety, deliverable-verification, fracture-mechanics, leak-before-break."
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
  tags: [ecss, e-st-32-structures-scope, structural-analysis-report, lbb-report, margin-of-safety, deliverable-verification, fracture-mechanics, leak-before-break]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Analysis Report and Documentation (space-systems/ecss/analysis-report-and-documentation)

Use when the task is to document or verify a structural analysis report
under ECSS-E-ST-32C clause 5.2, or a Leak-Before-Break (LBB) report
under clause 5.3.5 -- checking section completeness, computing margin of
safety per load case, and confirming LBB-specific fracture mechanics
content before a report is accepted as a deliverable.

## Domain quick reference

- Clause 5.2 defines the required content of a structural analysis
  report: it must cover the analysis objectives and scope, the list of
  applicable documents, a description of the mathematical model (FEM or
  closed-form), the load cases analysed, the material data used, the
  analysis methodology (linear elastic, nonlinear, buckling, etc.),
  the numerical results (stresses, displacements, eigenvalues as
  applicable), a margin-of-safety table, and conclusions with a
  compliance statement. Every section must appear; a section may be
  marked not applicable only when a written justification is provided.
- Margin of safety (MS) is defined as MS = allowable / applied - 1.
  A value of exactly 0.0 is the structural limit; any value below 0.0
  is a non-compliance and must be resolved before the report is
  formally issued. The allowable and applied loads must each be
  positive and expressed in consistent units.
- Clause 5.3.5 covers the Leak-Before-Break (LBB) approach for
  pressurized lines and vessels where the design intent is that a
  through-wall crack leaks at a detectable rate before the crack
  reaches critical length and causes rupture. An LBB report supplements
  the structural analysis report for the affected component and must
  include: fracture toughness data for the material and operating
  temperature, a crack-growth curve (da/dN vs. stress-intensity range),
  the critical crack size at operating pressure, the inspection interval
  derived from integrating the crack-growth law from initial detectable
  crack to critical size (with appropriate safety factor), a pressure-
  cycle history driving fatigue crack growth, and a leak-detection
  rationale confirming that the chosen monitoring method can detect the
  leakage flow before the crack reaches critical length.
- An LBB qualification does not remove the structural margin-of-safety
  requirement for the uncracked cross-section; both checks are required
  concurrently for LBB-qualified hardware.

## Workflow

1. Determine the report type: structural analysis report (clause 5.2)
   or LBB report (clause 5.3.5). LBB reports always accompany a
   structural report for the same component; evaluate both when both
   are submitted.
2. For a structural analysis report, check that every required section
   is present in the document index: objectives, applicable_documents,
   model_description, load_cases, material_properties,
   analysis_methodology, results, margin_of_safety, conclusions. Flag
   each missing section as a non-compliance finding.
3. For each load case in the report, extract the allowable and applied
   load (or stress, or force -- in consistent units) and compute
   MS = allowable / applied - 1. Flag any load case with MS < 0.0.
   Flag any load case where the allowable or applied value is missing
   or non-positive as an input-data error.
4. For an LBB report, check that every required section is present:
   fracture_toughness, crack_growth_data, critical_crack_size,
   inspection_intervals, pressure_cycle_history,
   leak_detection_rationale. Flag each missing section.
5. Confirm that the LBB acceptance criterion is explicitly stated in
   the conclusions: the computed inspection interval must be shown to
   exceed the scheduled inspection interval by the required safety
   factor, and the detectable leak rate must be shown to exceed the
   minimum detectable threshold of the monitoring system.
6. Aggregate section-completeness findings and load-case findings per
   report. A report is compliant only when all required sections are
   present and all margin-of-safety values are >= 0.0.

## Pitfalls

- Confusing factor of safety with margin of safety: FS = allowable /
  applied whereas MS = FS - 1. Reporting FS >= 1 in a margin-of-safety
  column instead of MS >= 0 creates a misleading table that passes
  automated checks but violates the clause 5.2 format requirement.
- Treating a missing section as implicitly not applicable: clause 5.2
  requires every listed section to appear with either content or a
  documented N/A justification. Omitting the section entirely is a
  non-compliance finding even if the analysis type genuinely does not
  use that content.
- Issuing an LBB report without the accompanying structural analysis
  report for the uncracked cross-section: the LBB approach addresses
  the cracked condition only; the uncracked margin of safety is a
  separate and still mandatory check.
- Omitting the pressure-cycle history from an LBB report: without the
  cycle count and pressure amplitude, the crack-growth integration
  cannot be performed and the inspection interval has no quantitative
  basis.
- Using allowable or applied values in different unit systems within
  the same margin-of-safety table: the computation is dimensionally
  valid only when both quantities are expressed in identical units.

## Behavior contract (gate 3)

The section-completeness, margin-of-safety, and LBB-section logic is
exercised by the gate 3 contract test:
scripts/test_analysis_report_and_documentation.py against
scripts/analysis_report_and_documentation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_analysis_report_and_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

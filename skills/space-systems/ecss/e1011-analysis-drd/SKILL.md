---
name: e1011-analysis-drd
description: "Use when generate or validate an HFE analysis and simulation report per ECSS-E-ST-10-11C Annex B DRD: verify the document covers all required sections (task analysis, human performance requirements, workload assessment, error analysis, simulation activities, and verification evidence); check each task-analysis entry for mission phase, crew allocation, and time budget; confirm every simulation activity records its objective, participant count, scenario, and findings; assess workload distribution and flag when high-or-critical tasks exceed 30 percent of the total; and verify each error analysis item carries an identified mitigation with a valid probability estimate. Trigger: ecss, e-st-10-system-scope, hfe, human-factors-engineering, analysis-drd, simulation-report, task-analysis, workload-assessment."
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
  tags: [ecss, e-st-10-system-scope, hfe, human-factors-engineering, analysis-drd, simulation-report, task-analysis, workload-assessment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors Engineering — HFE Analysis and Simulation Report DRD (space-systems/ecss/e1011-analysis-drd)

Use when the task requires generating or validating an HFE analysis and
simulation report that must satisfy the Document Requirements Definition
in ECSS-E-ST-10-11C Annex B. The DRD defines the mandatory content
structure, the required analytical threads (task analysis, workload,
human error, simulation), and the evidence each thread must provide.

## Domain quick reference

- ECSS-E-ST-10-11C Annex B specifies a DRD for the HFE Analysis and
  Simulation Report. The report is normative output: it must be produced
  at agreed programme milestones and accepted by the responsible HFE
  authority before the design review gate can close.
- The report has nine required sections: scope, applicable documents,
  task analysis, human performance requirements, workload analysis,
  error analysis, simulation activities, verification evidence, and
  findings and recommendations. A report missing any section is
  incomplete and cannot be accepted as satisfying the DRD.
- Each task-analysis entry covers a single identifiable crew task within
  a named mission phase. Required fields are mission phase (from the
  ECSS-recognised phase set), task description, crew size, and allocated
  time (a positive duration). A task entry without all four fields is
  incomplete.
- Workload is assessed per task using one of four levels: low, medium,
  high, or critical. When high-or-critical tasks exceed 30 percent of
  the total task count, the workload distribution must be flagged for
  design review scrutiny — this threshold is derived from the HFE
  acceptance criterion in clause 5.3.
- Simulation activities document the test events used to gather
  objective performance data. Each entry must record a unique simulation
  identifier, objective, participant count (at least one), scenario
  description, and findings. Missing any of these makes the activity
  evidence inadmissible against the DRD.
- Error analysis items each identify an error type (omission, commission,
  timing, sequence, or extraneous act) and must carry a mitigation
  measure and a numeric probability in [0, 1]. Items without a
  mitigation or with an out-of-range probability are non-conforming.

## Workflow

1. Obtain the candidate report document and map its sections to the nine
   required DRD sections. Record every missing section as a structure
   gap; do not proceed to content checks for a section that is absent.
2. For each entry in the task-analysis section, confirm all four
   required fields are present, that the mission phase is one of the
   ECSS-recognised phases, and that the allocated time is a positive
   value. Record any deficient entries by index before moving on.
3. For each entry in the simulation-activities section, confirm the five
   required fields are present and that the participant count is a
   positive integer. Record deficient entries by index.
4. Extract the workload level from every task-analysis entry and compute
   the fraction of tasks at high or critical level. Flag the report when
   that fraction exceeds 0.30, and flag any entry whose workload level
   is not one of the four recognised values.
5. For each item in the error-analysis section, verify the error type is
   present, a mitigation is recorded and non-empty, and the probability
   is a numeric value in [0.0, 1.0]. Record each deficiency.
6. Aggregate all findings across sections; set the compliance verdict to
   true only when all five finding lists are empty and the workload
   distribution is not flagged.

## Pitfalls

- Treating a report with all nine section headings as structurally
  complete without checking that each section has substantive content:
  the DRD requires content, not headings. The logic here checks
  presence of the section key in the data model; the reviewer must
  separately confirm each populated section is non-trivial.
- Applying the 30 percent workload threshold to individual tasks rather
  than the population fraction: the threshold is a distribution check,
  not a per-task rule. A single critical task in a 20-task plan is
  5 percent — not flagged.
- Accepting a simulation activity whose participant count is listed as
  zero on the grounds that the activity was a desk review: DRD Annex B
  requires observable human performance data, which demands at least one
  participant. Desk reviews are separate evidence and cannot substitute.
- Reading an error-analysis item with no probability field as implicitly
  having probability zero: an absent probability means the analysis is
  incomplete, which is a non-conformance, not a conservative assumption.

## Behavior contract (gate 3)

The report-structure, task-analysis, simulation-activity, workload, and
error-analysis logic is exercised by the gate 3 contract test:
scripts/test_e1011_analysis_drd.py against
scripts/e1011_analysis_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_analysis_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

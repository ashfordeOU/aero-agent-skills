---
name: e1006-char-performance
description: "Use when verify each requirement in a system specification for performance content under ECSS-E-ST-10C §8.2.1: confirm each performance requirement carries quantified parameters — numeric value, engineering unit, and comparison operator — flag requirements with missing or unquantified performance data, and confirm that performance requirement types are recognized before assessment. Trigger: ecss, e-st-10-system-scope, performance-requirements, quantification, parameter-values, requirements-review, verification, system-specification."
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
  tags: [ecss, e-st-10-system-scope, performance-requirements, quantification, parameter-values, requirements-review, verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Requirement Performance Content Check (space-systems/ecss/e1006-char-performance)

Use when the task is to verify that each requirement in a system
specification carries adequate performance content under
ECSS-E-ST-10C §8.2.1 — checking that every performance requirement
contains at least one quantified parameter (numeric value, engineering
unit, and comparison operator), and flagging requirements where the
performance data is absent or incomplete.

## Domain quick reference

- Section 8.2.1 of the standard specifies that each requirement with
  performance content must express that content as a quantified
  parameter: a numeric threshold (or range), the engineering unit in
  which it is measured, and the comparison operator that defines the
  direction of compliance (at most, at least, equal to, or within a
  range). A requirement that names a performance attribute without a
  numeric value is treated as unquantified and is a finding.
- Requirement types are categorized into two groups before the
  content check: performance types (performance, timing, accuracy,
  capacity, throughput, efficiency, data_rate) require at least one
  quantified parameter; non-performance types (functional, interface,
  design_constraint, operational, safety) are not subject to the
  §8.2.1 quantification check. An unrecognized requirement type is
  rejected before it enters the assessment.
- A parameter is fully quantified when all three components are
  present: a numeric value (integer or floating-point), a non-empty
  engineering unit string, and a recognized comparison operator
  (leq, geq, eq, lt, gt, or range). Any missing component generates
  a separate finding so that the review pinpoints the gap precisely.

## Workflow

1. For each requirement in the specification, determine its category
   (performance or non_performance) from its type field. Reject any
   requirement with an unrecognized type before proceeding.
2. Skip non-performance requirements; they carry no §8.2.1
   quantification obligation.
3. For each performance requirement, confirm that at least one
   performance parameter is present in the record. A performance
   requirement with no parameters at all is flagged immediately
   without inspecting any individual parameter.
4. For each parameter in a performance requirement, verify all three
   components: numeric value, engineering unit, and comparison
   operator. Each missing component generates its own finding against
   that parameter and requirement identifier.
5. Collect all findings per requirement identifier. A requirement
   with an empty findings list satisfies §8.2.1 for this check; a
   requirement with any finding does not.
6. The aggregate review is compliant when every requirement in the
   set has an empty findings list.

## Pitfalls

- Passing a requirement that names a performance attribute (e.g.,
  "the system shall have high accuracy") without a numeric value —
  the §8.2.1 check requires a quantity, not a label; the missing
  value must be flagged, not treated as an implicit threshold.
- Treating a missing unit as acceptable when a numeric value is
  present — a dimensionless number is valid only for unitless
  quantities; any physically measured parameter requires an explicit
  unit string to be verifiable.
- Skipping the type categorization step and running the quantification
  check against functional or interface requirements — non-performance
  requirements are not subject to §8.2.1 and mixing them into the
  performance check inflates findings.
- Reading "no findings" as "no performance requirements exist" — an
  empty findings list means each performance requirement in the set
  is fully quantified, which is the correct result; it does not mean
  the set contains no performance requirements.

## Behavior contract (gate 3)

The requirement type categorization, parameter quantification, and
aggregate review logic is exercised by the gate 3 contract test:
scripts/test_e1006_char_performance.py against
scripts/e1006_char_performance_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e1006_char_performance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

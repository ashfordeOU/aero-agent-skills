---
name: drd-math-model
description: "Use when draft the Mathematical Model Description Document (MMDD) for a structural mathematical model under ECSS-E-ST-32C Annex I and clause 32-03: categorize the model as finite-element, analytical, or hybrid, verify all required MMDD documentation fields are present and non-empty, check eigenfrequency correlation against the ±5 % tolerance and modal assurance criterion (MAC) values against the minimum threshold, assess delivery-package completeness against the MMDD checklist, and flag any missing or non-conforming items before the model is released for use. Trigger: ecss, e-st-32-structures-scope, mathematical-model, mmdd, finite-element, fem, model-correlation, mac, eigenfrequency, model-delivery."
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
  tags: [ecss, e-st-32-structures-scope, mathematical-model, mmdd, finite-element, fem, model-correlation, mac, eigenfrequency, model-delivery]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Mathematical Model Description Document (space-systems/ecss/drd-math-model)

Use when the task is to draft the Mathematical Model Description
Document (MMDD) required by ECSS-E-ST-32C Annex I and clause 32-03
— verifying that the structural mathematical model is fully documented,
correlated against test evidence, and packaged for delivery.

## Domain quick reference

- Annex I of ECSS-E-ST-32C defines the data requirements for the MMDD:
  a structured document that accompanies a structural mathematical model
  (finite-element, analytical, or hybrid) through its life cycle from
  development through correlation and delivery.
- A model is categorized into one of three types: finite-element (a
  discretized stiffness/mass mesh solved by numerical methods),
  analytical (closed-form formulations for idealised geometry),
  or hybrid (a combination of both). Each type has distinct
  documentation obligations; determining the type is the first step.
- Model correlation is the quantitative check that the model's
  predictions match physical test measurements. For eigenfrequency
  correlation the predicted frequency must be within ±5 % of the
  measured value. For mode-shape correlation the Modal Assurance
  Criterion (MAC) between the predicted and measured mode vectors must
  meet or exceed 0.90. Correlation evidence must be cited in the MMDD
  by reference to the test report.
- The MMDD delivery package is distinct from the model file itself; it
  must include the MMDD document, the model file, a correlation report,
  a coordinate-system definition, a version identifier, and an
  interface description. A model whose delivery package is incomplete
  is not considered delivered.

## Workflow

1. Determine the model type from the modelling approach used and
   categorize it as FINITE_ELEMENT, ANALYTICAL, or HYBRID. Reject any
   type label that does not match these three categories before
   proceeding.
2. Check that every required MMDD documentation field is present and
   non-empty: model identifier, model type, fidelity level
   (LINEAR or NONLINEAR), coordinate-system definition flag,
   boundary-conditions description, loading-cases list, element-types
   list (or equivalent for analytical), material-properties completeness
   flag, degree-of-freedom count, and reference to the correlation test.
   Record each missing field as a finding.
3. For each correlated mode, verify eigenfrequency correlation: compute
   the percentage error between the predicted and measured natural
   frequency; flag the mode if the error exceeds ±5 %. For the same
   modes, verify the MAC value is at least 0.90; flag any mode below
   threshold. A model with flagged modes is not correlated.
4. Assess the delivery package: confirm that each mandatory delivery
   item (MMDD document, model file, correlation report, coordinate-system
   definition, version identifier, interface description) is present.
   Record each missing item as a delivery finding.
5. Aggregate results: a model achieves MMDD compliance only when
   the missing-fields list is empty, all correlation checks pass, and
   the delivery package is complete. Report each non-compliant category
   separately so the responsible engineer can resolve individual gaps
   without repeating passing checks.

## Pitfalls

- Treating an incomplete correlation test reference as an acceptable
  placeholder — the MMDD requires a concrete reference to the test
  report used for correlation, not a forward reference to a test not
  yet performed. A model correlated against a not-yet-issued test is
  not correlated.
- Using the model type label inconsistently between the MMDD and the
  delivery package — a finite-element model delivered with an
  analytical-type label will fail the type-consistency check during
  review even if the numeric results are correct.
- Accepting a MAC value below 0.90 by noting it applies to a mode
  that "does not contribute" — the threshold applies to every mode
  included in the correlation set; modes not expected to contribute
  should be excluded from the set before the check, not given a
  threshold waiver after.
- Omitting the coordinate-system definition from the delivery package
  on the basis that it is "obvious from the mesh" — the MMDD delivery
  requirement is explicit; the definition must appear as a named item
  in the package regardless of its apparent self-evidence.

## Behavior contract (gate 3)

The model-categorization, MMDD-field-validation, frequency-correlation,
MAC-correlation, and delivery-package-completeness logic is exercised by
the gate 3 contract test: scripts/test_drd_math_model.py against
scripts/drd_math_model_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_drd_math_model.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

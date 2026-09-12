---
name: drd-test-analysis-correlation
description: "Use when produce a test-analysis correlation report under ECSS-E-ST-32C
  Annex O (TAC DRD, also 32-11): compare each pre-test analysis prediction against
  the corresponding test measurement, compute the relative delta for every measured
  quantity (frequency, static deflection, stress, damping), evaluate mode-shape
  correlation via the Modal Assurance Criterion, apply the programme-specified
  acceptance thresholds to determine pass or fail for each prediction-measurement
  pair, identify any pairs that require model updating, and verify the TAC document
  contains all DRD-mandated content sections. Trigger: ecss, e-st-32-structures-scope,
  test-analysis-correlation, tac, frequency-correlation, mac, mode-shape,
  model-update, drd-tac, pre-test-prediction."
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
  tags: [ecss, e-st-32-structures-scope, test-analysis-correlation, tac, frequency-correlation, mac, mode-shape, model-update, drd-tac, pre-test-prediction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Test-Analysis Correlation DRD (space-systems/ecss/drd-test-analysis-correlation)

Use when the task is producing the test-analysis correlation report required by
ECSS-E-ST-32C Annex O — comparing pre-test analysis predictions against test
measurements for each measured quantity, applying correlation acceptance criteria,
identifying prediction-measurement pairs that require model updating, and confirming
the TAC document contains every DRD-mandated section.

## Domain quick reference

- ECSS-E-ST-32C Annex O and the companion section 32-11 define the content
  requirements (DRD) for the test-analysis correlation report. The report must
  address every measured quantity, document the pre-test prediction alongside the
  test result, and state a pass/fail assessment against the programme-agreed
  acceptance threshold.
- Measured quantities are categorized into five types: **frequency** (natural
  frequency of a structural mode), **mode_shape** (spatial deformation pattern
  of a mode, assessed via the Modal Assurance Criterion), **static_deflection**
  (displacement under a static load case), **stress** (surface strain-gauge
  derived stress), and **damping** (modal damping ratio). Each quantity type
  carries a separate default acceptance threshold; programme-specific criteria
  take precedence over the defaults.
- Correlation is quantified by a relative delta for scalar quantities:
  delta = |predicted − measured| / |measured|. A delta at or below the threshold
  is a pass; above is a fail and triggers a model update requirement. Mode-shape
  correlation uses the Modal Assurance Criterion (MAC), a dimensionless number
  from 0 (no correlation) to 1 (perfect correlation); a MAC value at or above
  the threshold (default 0.90) is a pass.
- A model update is required whenever any prediction-measurement pair fails its
  acceptance criterion. The updated model must be re-submitted for re-correlation
  before the TAC report can be accepted. When all pairs pass, the model is
  considered validated for the test load environment.

## Workflow

1. Inventory all pre-test analysis predictions and their corresponding test
   measurement results. Each entry must identify the quantity type, the predicted
   value, the measured value, and the applicable acceptance threshold. An entry
   with an unrecognized quantity type must be rejected before it enters the
   correlation assessment — an uncategorized quantity is a documentation gap.
2. For each frequency, static-deflection, stress, or damping entry, compute
   the relative delta: |predicted − measured| / |measured|. A zero measured value
   is undefined and must be flagged as an input error — do not substitute a
   near-zero value or silently skip the entry.
3. For each mode-shape entry, retrieve the MAC value computed from the test and
   analysis mode vectors. Confirm the MAC value is in [0, 1]; a value outside
   this range indicates an error in the MAC computation and must be rejected.
4. Apply the acceptance threshold to each entry. Compare delta ≤ threshold for
   scalar quantities, MAC ≥ threshold for mode shapes. Record a pass or fail
   status for every prediction-measurement pair.
5. Aggregate all entries into the correlation summary table. Any entry with a
   fail status requires a model update justification. If no entries fail, the
   model is validated for the tested load environment.
6. Determine whether a model update is required: the TAC report requires a
   model-update justification section whenever at least one entry has failed,
   even if the failure is subsequently resolved by a re-analysis.
7. Verify the TAC report document contains all DRD-mandated sections: scope,
   applicable documents, test configuration, analysis model description,
   pre-test predictions, test results, correlation assessment, model update
   justification, and conclusions. A missing section is a document compliance
   gap independent of the numeric correlation outcomes.

## Pitfalls

- Omitting the mode-shape correlation (MAC check) and relying solely on
  frequency correlation — two modes can match in frequency while being
  completely different shapes; a MAC check is required to confirm that
  the compared predictions and measurements refer to the same mode.
- Using the absolute difference rather than the relative delta for frequency
  correlation — a 5 Hz miss on a 10 Hz mode (50% error) looks small in
  absolute terms but is far outside any reasonable threshold; the relative
  delta normalises for mode frequency.
- Treating a measured value of zero as a valid denominator — a zero measurement
  makes the relative delta undefined; the entry must be flagged as an input
  error, not defaulted to 100% or silently passed.
- Accepting a MAC value above threshold on a single-mode pair and concluding
  global model validity — MAC is evaluated per mode pair; a high MAC on one
  mode does not imply agreement on other modes in the same frequency band.
- Skipping the model-update justification section when all entries pass — the
  DRD requires this section regardless of outcome; an empty or "not required"
  statement is the correct content, not a missing section.

## Behavior contract (gate 3)

The quantity categorization, relative-delta computation, MAC assessment,
per-pair correlation status, model-update determination, and DRD completeness
logic is exercised by the gate 3 contract test:
scripts/test_drd_test_analysis_correlation.py against
scripts/drd_test_analysis_correlation_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_drd_test_analysis_correlation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

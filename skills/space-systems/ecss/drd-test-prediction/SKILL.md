---
name: drd-test-prediction
description: "Use when prepare a structural test prediction report per ECSS-E-ST-32C Annex Q: determine predicted response quantities (displacement, load, stress, natural frequency) at each monitoring point for every test load case, derive safety-abort thresholds from scaled finite-element analysis outputs, verify that predicted peak responses fall within instrument measurement ranges, and establish the analysis-to-test correlation acceptance band for each monitored quantity. Trigger: ecss, e-st-32-structures-scope, test-prediction, drd, structural-test, monitoring-point, abort-threshold, test-correlation, calculix-linear, annex-q."
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
  tags: [ecss, e-st-32-structures-scope, test-prediction, drd, structural-test, monitoring-point, abort-threshold, test-correlation, calculix-linear, annex-q]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Test Prediction Report (space-systems/ecss/drd-test-prediction)

Use when the task is producing or reviewing the test prediction report (TP DRD)
for a structural test campaign under ECSS-E-ST-32C Annex Q — computing expected
structural responses at each monitoring point for every test load case, setting
safety-abort thresholds from finite-element predictions, checking that predicted
peak values are within instrument measurement capability, and defining the
analysis-to-test correlation acceptance band.

## Domain quick reference

- Annex Q defines the minimum content for a test prediction report (TP).
  The report must address every test case in the campaign (static proof,
  modal survey, random vibration, acoustic, shock, thermal cycling) and
  supply a predicted response at each monitoring point before the test
  begins.
- Predicted responses are derived from a linear finite-element model (e.g.,
  Calculix linear solver) at a unit load factor and then scaled to the
  actual test load factor. A test load factor of 1.0 represents the
  qualification or acceptance load level; factors above 1.0 are used for
  over-test margins, but must not exceed 2.0 under the E-ST-32C structural
  qualification envelope.
- A safety-abort threshold is set at a fixed margin above the predicted
  peak response (typically 20 % above peak). During the test, if a
  monitoring channel reaches its abort threshold the test must be halted.
  The margin factor must be greater than 1.0; values at or below 1.0 are
  not physically meaningful.
- Each monitoring point must be served by an instrument whose full-scale
  measurement range covers the predicted peak response. A prediction that
  exceeds the instrument range is a pre-test finding: either the instrument
  must be replaced with a higher-range sensor or the load level must be
  reduced.
- Correlation acceptance is the quantitative criterion against which
  measured test responses will later be compared in the test evaluation
  report (TE DRD). Each predicted quantity carries a band expressed as a
  percentage of the predicted value. A measured response that falls outside
  the band is an anomaly requiring formal disposition.

## Workflow

1. Collect the test specification (objectives, test cases, load factors,
   directions) and confirm that every load factor is in the range
   (0, 2.0] and that every load direction is a recognised structural axis
   or load type.
2. For each test case, retrieve the baseline finite-element predictions at
   unit load factor for every monitoring point and quantity (displacement,
   force, stress, natural frequency). Scale each baseline value by the
   test load factor to obtain the predicted peak response.
3. Compute the safety-abort threshold for each monitoring point in each
   test case: multiply the absolute predicted peak by the abort margin
   (default 1.20). Record the abort threshold in the report; it becomes
   an instrument channel limit setting before the test begins.
4. Check that the predicted peak response at each monitoring point is
   within the instrument's full-scale measurement range. Flag any
   monitoring-point/quantity pair whose predicted value exceeds the
   instrument range as a pre-test finding.
5. Define the correlation acceptance band for each quantity at each
   monitoring point (default ±10 % of the predicted value). Record the
   lower and upper bounds; these are the acceptance limits used in the
   subsequent test evaluation.
6. Aggregate all findings (invalid test cases, instrument overrange,
   missing instrument definitions) and confirm that no open findings
   remain before the test prediction report is approved.

## Pitfalls

- Applying the abort margin to the signed predicted value instead of its
  absolute magnitude — a negative displacement prediction gives a
  negative abort threshold that can never be reached, leaving the test
  without a meaningful halt criterion.
- Using a load factor of zero — a zero factor produces zero predictions
  and meaningless abort thresholds; it is not a valid test case and
  must be rejected before entering the prediction calculation.
- Omitting instrument-range checks and discovering the overrange
  condition only during the test, which forces a test abort and may
  damage the test article or its instrumentation.
- Setting the correlation band to 0 % or 100 % — a zero-width band
  makes the criterion impossible to meet in practice; a 100 % band
  accepts any measurement and provides no engineering assurance.
- Confusing the test prediction with the test evaluation: the prediction
  is written before the test using analysis outputs only; measured data
  does not appear until the evaluation phase covered by the TE DRD.

## Behavior contract (gate 3)

The test-case validation, linear FEM scaling, abort-threshold computation,
instrument-range check, and correlation-band logic are exercised by the
gate 3 contract test: scripts/test_drd_test_prediction.py against
scripts/drd_test_prediction_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_drd_test_prediction.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

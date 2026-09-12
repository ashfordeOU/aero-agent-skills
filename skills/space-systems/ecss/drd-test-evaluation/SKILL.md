---
name: drd-test-evaluation
description: "Use when evaluate test results against predictions for a structural test campaign under ECSS-E-ST-32C Annex P: verify each test objective is met, compare measured responses to predicted values within the approved tolerance, assess all anomalies encountered and confirm their disposition, check post-test article condition, and produce the pass/reject conclusion for the test evaluation report. The procedure covers static, dynamic, acoustic, and thermal test types. Trigger: ecss, e-st-32-structures-scope, test-evaluation, test-prediction, test-objectives, anomaly-disposition, test-article-condition, structural-test-campaign."
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
  tags: [ecss, e-st-32-structures-scope, test-evaluation, test-prediction, test-objectives, anomaly-disposition, test-article-condition, structural-test-campaign]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Test Evaluation Report (space-systems/ecss/drd-test-evaluation)

Use when the task is producing or reviewing the test evaluation report (TE DRD)
for a structural test campaign under ECSS-E-ST-32C Annex P — comparing observed
test outcomes to pre-defined objectives and predicted responses, resolving
anomalies, assessing post-test article condition, and recording the overall
pass/reject conclusion.

## Domain quick reference

- Annex P defines the minimum content for a test evaluation report (TE).
  The report covers every test event in the campaign (static proof, modal
  survey, random vibration, acoustic, shock, thermal cycling, etc.) and must
  address each test objective stated in the test specification.
- A test objective is a specific engineering requirement the test was designed
  to demonstrate. Each objective is assessed individually as met, not met, or
  partially met before an overall conclusion is drawn.
- Predicted values (frequencies, displacements, stresses, accelerations) are
  taken from the approved test prediction (TP DRD). Measured responses are
  compared against predictions within a defined tolerance band. Any measurement
  that falls outside the band must be recorded as a finding and given an
  engineering disposition before the test can be accepted.
- An anomaly is any unexpected event, hardware response, or procedural
  deviation that occurred during the test. Each anomaly receives a formal
  disposition: resolved (root cause identified, corrective action confirmed),
  waived (accepted as-is with justification), or open (unresolved — blocks
  acceptance until closed).
- Post-test article condition covers dimensional, functional, and visual
  inspection of the test article after the campaign. An article in acceptable
  condition shows no damage or degradation beyond the pre-agreed limits;
  conditional means accepted with qualification; not acceptable blocks the
  evaluation.

## Workflow

1. Retrieve the approved test specification and test prediction for the
   campaign. Identify every stated test objective and every predicted response
   parameter with its tolerance band.
2. For each test objective, assign one of three statuses: met (demonstrated
   with margin), not met (failed to demonstrate), or partial (demonstrated for
   a subset of conditions or load levels). Record the supporting evidence
   (channel ID, measurement value, timestamp).
3. For each predicted response parameter, compare the measured value to the
   prediction. Compute the relative deviation. Flag any parameter whose
   deviation exceeds the tolerance band as outside-prediction; record as
   within-prediction otherwise. Sum up counts in both bins.
4. List every anomaly logged during the test. Assign a disposition to each:
   resolved, waived, or open. An open anomaly blocks the overall evaluation
   — it must be closed before the report can reach an accepted conclusion.
5. Record the post-test article condition for each article in the campaign:
   acceptable, conditional, or not acceptable. A not-acceptable condition
   blocks acceptance.
6. Aggregate the findings from steps 2–5. If all objectives are met,
   no results fall outside prediction, no anomalies are open, and all
   article conditions are acceptable or conditional, the overall evaluation
   status is accepted. Any failing condition yields a rejected status with
   the finding list as supporting evidence.
7. Populate the TE DRD sections: scope and objective list, summary of test
   execution, objective-by-objective assessment table, prediction-vs-measurement
   table, anomaly log with dispositions, article condition record, and the
   overall evaluation conclusion with the responsible engineer's sign-off.

## Pitfalls

- Conflating "test completed" with "test objective met" — a test can run to
  completion while failing to demonstrate its stated requirement (e.g., load
  level was insufficient, instrumentation failed on the critical channel). The
  objective assessment must be made explicitly, not inferred from completion.
- Treating an open anomaly as minor and proceeding to an accepted conclusion
  — every open anomaly is a formal block. An anomaly without an engineering
  disposition cannot be treated as benign.
- Applying the tolerance band only to the peak response and ignoring frequency
  or phase deviations — for dynamic tests, the tolerance band covers the
  frequency of peak response as well as its amplitude; both must be within
  prediction.
- Omitting the post-test condition assessment for articles that showed no
  visible damage — the condition record is mandatory for every test article,
  not only for those with suspected damage.
- Carrying a predicted value from an intermediate analysis revision rather
  than the approved TP DRD — deviations measured against a superseded
  prediction are not traceable to the approval baseline and must be recomputed
  against the authorised document.

## Behavior contract (gate 3)

The objective assessment, prediction-comparison, anomaly-disposition, and
overall-evaluation logic is exercised by the gate 3 contract test:
scripts/test_drd_test_evaluation.py against
scripts/drd_test_evaluation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_drd_test_evaluation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Primary reference: ECSS-E-ST-32C Annex P (Test Evaluation DRD).

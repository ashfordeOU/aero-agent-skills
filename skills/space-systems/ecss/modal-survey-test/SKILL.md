---
name: modal-survey-test
description: "Use when execute a modal survey test on a spacecraft structural assembly
  to identify natural frequencies, damping ratios, and mode shapes; validate the
  finite element model by computing the Modal Assurance Criterion for each
  test-prediction mode pair and flagging pairs below the acceptance threshold;
  verify each identified frequency falls within the allowable tolerance of its
  predicted counterpart; confirm the measurement point configuration covers all
  target modes; and flag any damping estimate outside the physically plausible
  structural range or any target mode without a measured counterpart.
  Trigger: ecss, e-st-32-structures-scope, modal-survey-test, natural-frequency,
  mode-shape, mac, damping-ratio, frequency-response-function, fem-validation,
  model-correlation."
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
  tags: [ecss, e-st-32-structures-scope, modal-survey-test, natural-frequency, mode-shape, mac, damping-ratio, frequency-response-function]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Modal Survey Test (space-systems/ecss/modal-survey-test)

Use when the task is the experimental modal survey test defined under
ECSS-E-ST-32-11C clause 4.6.3.8: executing controlled excitation of a
spacecraft structural assembly, measuring frequency response functions,
extracting modal parameters, correlating identified modes with finite element
model predictions via the Modal Assurance Criterion, and confirming that all
target modes are covered within allowable frequency and shape tolerances.

## Domain quick reference

- A modal survey test applies a measurable input force (sine sweep, stepped
  sine, broadband random, or impact) to the test article and records the
  structural response at a sufficient number of measurement points to spatially
  resolve all target modes. The excitation method must be one of the four
  recognized types; anything else is an invalid test configuration.
- Modal parameters are extracted from the measured frequency response functions:
  natural frequency (Hz), viscous damping ratio (dimensionless), and mode shape
  (a vector of response amplitudes at each measurement point). Damping ratios for
  spacecraft structural modes typically fall in the range 0.1 % to 10 %;
  estimates outside that range indicate measurement error or data-processing
  problems and must be flagged.
- Finite element model (FEM) correlation uses the Modal Assurance Criterion (MAC)
  to compare each identified test mode shape against its predicted counterpart.
  MAC ranges from 0 (orthogonal, no correlation) to 1 (identical shapes).
  A MAC value below the acceptance threshold (typically 0.90) indicates that the
  two shapes do not represent the same physical mode and the mode pair is
  non-correlating. A MAC value at or above the threshold, combined with a
  measured natural frequency within the allowable tolerance of the FEM prediction
  (typically ±5 %), constitutes a passing mode-pair verdict.
- The measurement point configuration must be dense enough to distinguish all
  target modes from one another. The minimum number of measurement points is
  defined in the test specification; a test with fewer points than required cannot
  spatially resolve the target modes and is a configuration finding.
- Every target mode listed in the test specification must be identified in the
  test; any target mode without a measured counterpart is a coverage gap finding.

## Workflow

1. Confirm the excitation method is one of the four recognized types
   (sine_sweep, stepped_sine, broadband_random, impact); reject and flag any
   method not in that set before proceeding.
2. Verify the number of measurement points meets or exceeds the minimum required
   in the test specification; flag a deficient configuration as a measurement
   adequacy finding before the test is considered valid.
3. Extract the modal parameters for each identified mode from the measured
   frequency response functions: natural frequency (Hz), damping ratio, and mode
   shape vector.
4. For each identified mode and its FEM prediction counterpart, compute the MAC
   and compare the identified natural frequency against the predicted value using
   the allowable frequency tolerance. Record a mode-pair finding for any MAC below
   the threshold or any frequency deviation above the tolerance.
5. Check that every target mode in the test specification has at least one
   identified mode assigned to it; record a coverage gap for each target mode
   not matched.
6. Check that each extracted damping ratio is within the physically plausible
   range; flag any estimate outside that range as a damping anomaly.
7. Aggregate all findings (excitation, measurement, coverage, per-mode); the
   modal survey test is compliant only when all finding lists are empty.

## Pitfalls

- Accepting a mode pair as correlated on frequency match alone without computing
  the MAC — a predicted and identified mode can have nearly the same frequency
  but represent different physical deformation shapes if the structure has closely
  spaced modes; MAC is required to confirm shape correlation.
- Treating a MAC just below the threshold as a marginal pass — the threshold is a
  hard criterion; a result of 0.889 with a threshold of 0.90 is non-correlating,
  not marginal.
- Concluding that all target modes are covered because the count of identified
  modes equals the count of target modes — the match must be made mode-by-mode
  against the target mode identifier list; counting alone misses swapped or merged
  modes.
- Ignoring damping estimates at the physical boundary of the plausible range
  because they are technically within bounds — values near 0.1 % or approaching
  10 % warrant an engineering review, even if not formally flagged.
- Forgetting that a MAC of exactly 1.0 can only occur with identical shape
  vectors; any measurement noise or FEM discretization difference will produce
  values slightly below 1.0 on real data — this is expected, not a concern.

## Behavior contract (gate 3)

The excitation validation, MAC computation, frequency correlation, damping
plausibility, mode coverage, measurement adequacy, and full compliance logic
are exercised by the gate 3 contract test:
scripts/test_modal_survey_test.py against
scripts/modal_survey_test_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_modal_survey_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

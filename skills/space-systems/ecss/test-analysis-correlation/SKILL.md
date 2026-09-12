---
name: test-analysis-correlation
description: "Use when assess the correlation between measured structural dynamic
  properties from a modal survey test and finite-element model predictions, per
  ECSS-E-ST-32C and ECSS-E-ST-32-11: pair each measured natural frequency and
  mode shape to its analysis counterpart by Modal Assurance Criterion (MAC),
  check the paired frequency deviation against the accepted tolerance, verify
  the MAC value meets the acceptance threshold for mode-shape similarity, flag
  modes that remain unpaired or breach either criterion, and confirm no
  discrepancy is outstanding before the FE model is released for load analysis.
  Trigger: ecss, e-st-32-structures-scope, test-analysis-correlation,
  modal-survey, mac, frequency-deviation, mode-pairing, fem-updating,
  structural-dynamics."
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
  tags: [ecss, e-st-32-structures-scope, test-analysis-correlation, modal-survey, mac, frequency-deviation, fem-updating, structural-dynamics]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Test-Analysis Correlation (space-systems/ecss/test-analysis-correlation)

Use when the task is the test-analysis correlation (TAC) assessment required
by ECSS-E-ST-32C and ECSS-E-ST-32-11 — pairing measured modal survey results
against finite-element model (FEM) predictions, checking each pair against the
frequency-deviation tolerance and the Modal Assurance Criterion acceptance
threshold, and confirming the FE model is suitable for load analysis only when
all discrepancies have been resolved.

## Domain quick reference

- ECSS-E-ST-32C specifies the general structural requirements for space hardware;
  ECSS-E-ST-32-11 specifies how a modal survey assessment is planned, executed,
  and correlated with the structural FE model. TAC is the activity that links the
  two: it determines whether the model predicts the measured dynamic behaviour
  within accepted limits.
- Mode pairing associates each measured natural frequency and mode shape with its
  analysis counterpart. The Modal Assurance Criterion (MAC) is the primary pairing
  metric: MAC = (φ_test · φ_analysis)² / ((φ_test · φ_test)(φ_analysis · φ_analysis)),
  yielding a value in [0, 1] where 1.0 is perfect mode-shape agreement and 0.0
  indicates orthogonal (uncorrelated) shapes. A pair is accepted only when MAC
  meets or exceeds the project acceptance threshold (typically 0.90 for primary
  structural modes). A test mode for which no analysis mode reaches the MAC
  threshold remains unpaired and is a TAC discrepancy.
- Frequency deviation is checked only for paired modes: Δf/f_analysis =
  (f_test − f_analysis) / f_analysis. The deviation must satisfy |Δf/f_analysis|
  ≤ tolerance (typically ±5 % under ECSS-E-ST-32-11). A paired mode that exceeds
  the tolerance is a frequency correlation discrepancy.
- A TAC discrepancy — whether an unpaired mode, a frequency violation, or a MAC
  violation — must be dispositioned (model update, engineering justification, or
  re-test) before the FE model is approved for load analysis. No discrepancy may
  remain open at the model release gate.

## Workflow

1. Collect the modal survey outputs (measured natural frequencies in Hz and
   normalised real mode-shape vectors) and the FEM predictions (predicted natural
   frequencies and mode-shape vectors at the same degree-of-freedom set). Confirm
   every vector is normalised to a consistent reference before pairing begins.
2. Compute the MAC value for every test-mode / analysis-mode combination.
   Pair each test mode to the analysis mode with the highest MAC, provided that
   MAC meets the project acceptance threshold. Apply a greedy one-to-one matching:
   once an analysis mode is paired it cannot be re-used. A test mode whose best
   available candidate falls below the MAC threshold is recorded as unpaired.
3. For each successfully paired set, compute the frequency deviation
   (f_test − f_analysis) / f_analysis. Flag the pair as a frequency-correlation
   discrepancy when the absolute deviation exceeds the project frequency tolerance.
4. For each successfully paired set, check the MAC value against the acceptance
   threshold. Flag the pair as a MAC-correlation discrepancy when MAC falls below
   the threshold (this catches pairs that were accepted by the greedy algorithm at
   the threshold boundary but later reviewed against a stricter project criterion).
5. Aggregate all discrepancies: unpaired test modes, frequency violations, and MAC
   violations. A TAC review is compliant only when all three lists are empty.
6. For each discrepancy, prepare an engineering disposition: determine whether the
   FE model requires updating (mass, stiffness, or boundary condition adjustment),
   whether the measurement requires re-examination (sensor placement, signal
   processing artefact), or whether an engineering justification is sufficient.
   No disposition may be left open at the model release gate.

## Pitfalls

- Using MAC only for mode-shape acceptance and ignoring the frequency-deviation
  check — a pair with high MAC but a large frequency offset indicates a stiffness
  or mass error in the model that will propagate into load predictions.
- Using the absolute frequency difference (Hz) rather than the relative deviation
  — low-frequency modes have a much tighter absolute tolerance than high-frequency
  modes; the relative criterion is scale-invariant and is the ECSS-mandated form.
- Allowing many-to-one mode pairing — reusing an analysis mode for multiple test
  modes inflates the apparent correlation and hides mode confusion; the pairing
  must be one-to-one.
- Treating an unpaired test mode as a TAC pass by default — if the modal survey
  identified a mode that the FEM does not predict within the MAC threshold, the
  model is missing a structural mode, which is itself a discrepancy requiring
  disposition.
- Releasing the FE model for load analysis before all discrepancies are dispositioned —
  even a single open frequency or MAC violation invalidates the model release
  gate under ECSS-E-ST-32-11.

## Behavior contract (gate 3)

The frequency-deviation, MAC, mode-pairing, and violation-aggregation logic is
exercised by the gate 3 contract test: scripts/test_test_analysis_correlation.py
against scripts/test_analysis_correlation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_test_analysis_correlation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

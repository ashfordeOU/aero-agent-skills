---
name: e1011-verif-analysis
description: "Use when verify Human Factors Engineering (HFE) requirements by analysis or similarity under ECSS-E-ST-10-11 §4.11.2: select the applicable analysis method (task analysis, cognitive workload, workspace envelope, anthropometric analysis, or digital human model simulation), score heritage similarity against the target design to determine whether prior evidence transfers, run DHM simulations and compare joint angles, reach zones, crew forces, and visual fields against acceptance thresholds, and compile the mandatory analysis/simulation report per Annex B. Trigger: ecss, e-st-10-11, hfe, human-factors, verif-analysis, dhm, digital-human-model, similarity, annex-b, ergonomics."
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
  tags: [ecss, e-st-10-11, hfe, human-factors, verif-analysis, dhm, digital-human-model, similarity, annex-b, ergonomics]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS HFE — Verification by Analysis and Similarity (space-systems/ecss/e1011-verif-analysis)

Use when the task is verifying Human Factors Engineering requirements
by analysis or heritage similarity under ECSS-E-ST-10-11 §4.11.2,
including digital human model (DHM) simulation runs and compilation
of the analysis/simulation report (Annex B).

## Domain quick reference

- §4.11.2 permits three modes for HFE verification without a physical
  test article: (1) analytical methods (task analysis, cognitive
  workload assessment, workspace and reach envelope check,
  anthropometric dimension comparison), (2) heritage similarity
  (claiming credit from a previously verified design whose function,
  physical form, operating environment, and user population are
  sufficiently similar), and (3) DHM simulation (a three-dimensional
  digital human model that reproduces crew posture, joint loading,
  reach, and visual field in the design space). All three modes
  produce an analysis/simulation report whose structure is governed
  by Annex B.
- Similarity credit requires a scored comparison across four
  dimensions: function, physical form, operating environment, and
  user population. A design is considered sufficiently similar when
  all four dimensions together yield a composite score at or above
  the project-defined threshold (typically ≥ 0.80 on a normalised
  0–1 scale). Dimensions that fall short must be covered by
  additional analytical evidence.
- DHM simulation acceptance criteria cover four ergonomic parameters:
  joint angle deviation from neutral posture, crew reach zone
  compliance, maximum required force, and off-axis viewing angle.
  Each parameter has a project-defined limit; the DHM run must
  demonstrate compliance on all four simultaneously.
- Every analysis/simulation report must contain the core Annex B
  fields. Similarity reports add a heritage reference field;
  DHM reports add a DHM software and version field.

## Workflow

1. Select the analysis method or combination of methods appropriate
   to the HFE requirement being verified. Reject any method type not
   in the approved set before it is entered into the evidence record.
2. If a similarity claim is intended, gather dimension scores for
   function, physical form, operating environment, and user
   population. Compute the composite score. If the score is below
   the threshold, flag the deficit and require supplementary analysis
   for each underscoring dimension; do not proceed to credit the
   similarity claim until the gap is closed.
3. For each DHM simulation scenario, retrieve the four output metrics
   (joint angle deviation, reach zone flag, maximum force, visual
   angle). Compare each against its acceptance limit. Record a
   finding (pass or fail) per metric per scenario.
4. Draft the Annex B report. Confirm every mandatory core field is
   present. Add the heritage reference field if the report covers a
   similarity claim. Add the DHM software field if the report covers
   a DHM simulation. Flag any missing required field as an open action
   before the report is issued.
5. Aggregate all findings (per-dimension similarity, per-metric DHM,
   per-field report completeness) into an overall verification status.
   The requirement is considered verified only when no fail-severity
   finding remains open.

## Pitfalls

- Accepting a similarity claim on the basis of a single matching
  dimension (e.g. identical form factor) while the operating
  environment has changed significantly (e.g. suited vs. unsuited
  crew). All four dimensions must be scored; a single underscoring
  dimension is sufficient to deny heritage credit for that dimension.
- Running a DHM simulation to a single ergonomic metric (e.g. reach
  only) and treating that as full DHM compliance. All four metrics
  (joint angle, reach, force, visual field) must be evaluated in each
  relevant scenario.
- Issuing a report with missing Annex B fields under the assumption
  that the omitted data is implied by context. Each required field
  must be explicitly populated; an absent field is a reportable gap
  regardless of whether the information is available elsewhere.
- Conflating a passing composite similarity score with per-dimension
  compliance. A score above the threshold does not mask individual
  dimensions that scored very low — project procedure may impose a
  per-dimension floor as well.

## Behavior contract (gate 3)

The analysis-method selection, similarity scoring, DHM result
checking, and Annex B completeness logic are exercised by the gate 3
contract test:
scripts/test_e1011_verif_analysis.py against
scripts/e1011_verif_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_verif_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

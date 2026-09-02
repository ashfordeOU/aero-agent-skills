---
name: measurement-systems-analysis
description: "Use when you must evaluate an aerospace measurement system with a gage repeatability and reproducibility (Gage R and R) study: compute the equipment variation EV from the average range, the appraiser variation AV from the spread of appraiser averages, the combined GRR, the part-to-part variation PV, the total variation TV, the percent GRR against the acceptance criteria (under 10 percent acceptable, 10 to 30 percent conditional, over 30 percent unacceptable), and the number of distinct categories, and judge variable versus attribute gage studies and calibration versus MSA scope. Produces the study summary, the percent GRR verdict, and the distinct categories count that gate measurement system approval. Trigger: measurement systems analysis, gage r and r, repeatability, reproducibility, percent grr, distinct categories, gage study, measurement system."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [measurement-systems-analysis, gage-r-and-r, repeatability, reproducibility, percent-grr, distinct-categories, variable-gage-study, attribute-gage-study, equipment-variation, appraiser-variation]
  version: 0.1.0
  author: Aero Agent Skills
---

# Measurement Systems Analysis (manufacturing-quality/as9100/measurement-systems-analysis)

Use when the task is judging whether an aerospace measurement system
is adequate for its measurement task: operator-part trial data feeds
the range-based Gage R and R study, the percent GRR scores the system
against the acceptance bands, and the number of distinct categories
scores its resolving power.

## Domain quick reference

- Gage R and R splits measurement error into repeatability (equipment
  variation EV, the spread of repeated readings by one appraiser on
  one part) and reproducibility (appraiser variation AV, the spread of
  appraiser averages on the same parts).
- Range method: for each appraiser-part cell the range of the trials
  is R, the average of all cell ranges is rbar, and EV = K1 * rbar
  with K1 = 4.56 for 2 trials and 3.05 for 3 trials.
- AV = sqrt((K2 * xdiff)^2 - EV^2 / (trials * parts)) with xdiff the
  spread of the appraiser averages and K2 = 3.65 for 2 appraisers,
  2.70 for 3; a negative radicand clamps AV to zero, meaning the
  appraisers agree within equipment variation.
- GRR = sqrt(EV^2 + AV^2), part variation PV = K3 * Rp with Rp the
  spread of the part averages, total variation TV = sqrt(GRR^2 + PV^2).
- Percent GRR = 100 * GRR / TV. Acceptance criteria: under 10 percent
  the measurement system is acceptable, 10 to 30 percent is
  conditional (acceptable only for specific applications), over 30
  percent is unacceptable and the gage must be improved or replaced.
- Number of distinct categories ndc = floor(1.41 * PV / GRR); the
  common guidance is five or more categories for an adequate system.
- Variable gage studies use continuous readings; attribute gage
  studies use go/no-go or classification results and need agreement
  and Kappa analysis, not the range method.
- Calibration vs MSA: calibration verifies the instrument against a
  standard with traceability (see calibration-control); MSA quantifies
  how much of the observed variation comes from the measurement
  system itself.
- AS9100 frames monitoring and measuring resources as controlled and
  fit for purpose (paraphrase of clause 7.1.5 practice); the Gage R
  and R study is the common aerospace evidence that a gage is fit for
  its measurement task, summarized here without clause text.

## Workflow

1. Collect the operator-part measurement table: every appraiser
   measures every part with the same number of trials (2 or 3), the
   range method standard.
2. Build the measurements dict: appraiser name to a list of parts,
   each part a list of trial readings, with identical part and trial
   counts across appraisers.
3. Run the study with study_summary(measurements) to get EV, AV, GRR,
   PV, TV, the percentage contributions, and the ndc.
4. Read the percent GRR verdict from the summary, or score a percent
   directly with acceptance_verdict(grr_pct).
5. Judge resolving power with number_distinct_categories(pv, grr);
   five or more categories is the common adequacy threshold.
6. Validate inputs first: fewer than two appraisers, fewer than two
   parts, trial counts outside 2-3, inconsistent table dimensions, or
   negative readings raise ValueError.

## Pitfalls

- Routing control chart questions here: X-bar and R chart limits,
  process capability Cp/Cpk, and Western Electric rules belong to
  statistical-process-control; a gage study measures the measurement
  system, not the production process.
- Routing instrument calibration questions here: TAR, calibration due
  dates, out-of-tolerance recall, and traceability belong to
  calibration-control; MSA is about measurement system variation, not
  instrument calibration state.
- Routing root cause questions here: 8D, five whys, and corrective
  action plans belong to corrective-action; a high percent GRR
  explains why a process looks out of control but is not itself a
  root cause analysis.
- Treating an attribute gage study like a variable one: go/no-go
  results need agreement and Kappa analysis, not the range method.
- Reading the percent GRR bands off the wrong edge: under 10 is
  acceptable, exactly 10 to 30 is conditional, over 30 is
  unacceptable; 30.1 is not conditional.
- Reporting AV as zero without the clamp note: the range method
  clamps a negative radicand to zero, which means the appraisers
  agree within equipment variation, not that appraiser bias is absent.
- Dividing by zero total variation: a study where every reading is
  identical has no variation to decompose; the summary reports zero
  percent GRR and an acceptable verdict.
- Taking ndc at face value when GRR is zero: with no measurement
  error the ratio is undefined and the summary returns None.
- Confusing calibration with MSA: a calibrated instrument can still
  have poor repeatability or reproducibility; calibration is a
  precondition, not a substitute, for a gage study.

## Behavior contract (gate 3)

The Gage R and R logic is exercised by the gate 3 contract test:
scripts/test_measurement_systems_analysis.py against
scripts/measurement_systems_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_measurement_systems_analysis.py

## Compliance

- Standards referenced, not reproduced: AS9100 clause 7.1.5 frames
  monitoring and measuring resources; the range-method constants and
  the acceptance bands are common MSA methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

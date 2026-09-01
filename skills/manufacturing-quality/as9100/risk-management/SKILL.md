---
name: risk-management
description: "Assess and plan mitigation for aerospace quality risks per AS9100D operational risk management: compute FMEA risk priority numbers from severity, likelihood, and detection ratings, classify RPN bands, score the post-mitigation residual RPN from reduction credits, derive occurrence probability from production history, apply the 5x5 severity-likelihood risk matrix, and rank risks for mitigation priority with residual-risk acceptance checks. Produces the risk register entries, mitigation plan, and residual-risk verdicts that AS9100D 8.1.1 requires before production changes proceed. Use when the task is risk assessment, mitigation planning, or operational risk review rather than dispositioning an actual nonconformance or closing a CAPA. Trigger: risk management, risk assessment, mitigation planning, operational risk, RPN, FMEA, risk matrix, residual risk."
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
  tags: [risk-management, risk-assessment, mitigation-planning, operational-risk, risk-priority-number, risk-matrix, residual-risk, fmea, likelihood-rating, detection-rating]
  version: 0.1.0
  author: AeroSkills
---

# Risk Management (manufacturing-quality/as9100/risk-management)

Use when the task is AS9100D operational risk assessment and
mitigation planning: scoring potential failure modes before they
occur, building the risk register, prioritizing mitigation actions,
and demonstrating the residual risk is acceptable, rather than
reacting to a nonconformance that already happened.

## Domain quick reference

- FMEA risk priority number: RPN = S * L * D with severity,
  likelihood, and detection each rated 1-10. Worked: S = 8, L = 5,
  D = 3 gives RPN = 8 * 5 * 3 = 120; a better-detected mode with
  S = 6, L = 2, D = 2 gives 24. The product is nonlinear, so equal
  RPN steps are not equal risk steps.
- RPN bands: below 40 is low, 40-99 is medium, at or above 100 is
  high. Worked: RPN 25 is low, 60 is medium, 120 is high, and the
  boundaries are inclusive at the high side (100 is high, 40 is
  medium).
- Post-mitigation scoring: each action lowers severity, likelihood,
  or detection; the residual RPN is (S - dS) * (L - dL) * (D - dD).
  Worked: reductions of 2, 3, and 1 on S = 8, L = 5, D = 3 give
  (8 - 2) * (5 - 3) * (3 - 1) = 6 * 2 * 2 = 24.
- Risk reduction fraction: (before - after) / before. Worked: 120
  reduced to 24 is (120 - 24) / 120 = 0.8, an 80% risk reduction;
  a residual above the original gives a negative fraction, flagging
  an ineffective plan.
- Occurrence probability: occurrences / units produced grounds the
  likelihood rating in history. Worked: 3 failures in 10,000 units is
  3e-4 per unit, which maps to the low end of the likelihood scale.
- Residual risk acceptance: the residual RPN must meet the
  organization threshold. Worked: residual 24 against threshold 40 is
  acceptable; residual 60 against threshold 40 is not.
- 5x5 risk matrix: severity-likelihood product 15 or more is high, 6
  or more is medium, otherwise low. Worked: (4, 4) gives 16 = high,
  (3, 2) gives 6 = medium, (2, 2) gives 4 = low. The matrix ranks
  risks coarser than the RPN because it omits the detection axis.
- Mitigation priority: rank the register by RPN descending, ties
  broken by identifier, so the top entry is the first mitigation
  target. Worked: RPNs 120 (B), 50 (A), 20 (C) rank B, A, C.

## Workflow

1. Identify the failure modes for the process, product change, or
   operation under review and list them in the risk register with a
   unique identifier for each.
2. Rate severity, likelihood, and detection on the 1-10 FMEA scales
   and compute the RPN with risk_priority_number(); classify the band
   with risk_priority_classification() and the matrix band with
   risk_matrix_classification().
3. Ground the likelihood rating in evidence where history exists
   using occurrence_probability() from the production records.
4. Rank the register with rank_risks() to set mitigation-planning
   priority, and plan the highest RPN entries first.
5. Define mitigation actions with explicit reduction credits, score
   the residual RPN with mitigated_risk_priority_number(), and check
   the residual against the threshold with
   residual_risk_acceptable(); record the risk reduction fraction
   with risk_reduction_fraction() as close-out evidence.
6. Record the residual risk verdict and the responsible function's
   acceptance in the register, per AS9100D 8.1.1, before the change
   or process proceeds.

## Pitfalls

- Confusing this leaf with corrective-action: risk assessment is
  forward-looking (AS9100D 6.1 and 8.1.1) and scores potential
  failure modes; a CAPA reacts to an actual nonconformance with the
  8D workflow and root cause. A CAPA closure task routes to
  corrective-action, not here.
- Confusing with nonconformance-control: dispositioning a
  nonconforming part (rework, repair, scrap, use-as-is) is not risk
  assessment; the risk register covers future failure modes, the
  nonconformance record covers the part that already failed.
- Confusing with counterfeit-prevention: counterfeit scoring is one
  specific risk category with its own leaf and its own scoring
  scheme; general operational risk management covers all failure
  modes, counterfeit included.
- Confusing with supplier-control: supplier risk classification and
  delegated verification for external providers route to
  supplier-control; risk-management owns the full operational risk
  register across processes, not just procurement.
- Dropping the detection axis: RPN = S * L * D; reducing it to S * L
  misorders risks where poor detection lets a rare severe failure
  escape, which is exactly the case FMEA exists to catch.
- Claiming mitigation without re-scoring: a mitigation plan without a
  recomputed residual RPN is unverifiable; always run
  mitigated_risk_priority_number() and record the after value.
- Mixing the RPN bands with the matrix bands: the RPN bands (40 and
  100 on a three-axis product) and the 5x5 matrix bands (6 and 15 on
  a two-axis product) are different scales; never compare a band from
  one scheme with a band from the other.
- Accepting residual risk without evidence: the math check is only
  the numeric half; AS9100D 8.1.1 close-out requires the responsible
  function's recorded acceptance of the residual risk, with the
  reduction credits and the after-RPN on file.

## Behavior contract (gate 3)

The risk management math is exercised by the gate 3 contract test:
scripts/test_risk_management.py against
scripts/risk_management_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_risk_management.py

## Compliance

- Standards referenced, not reproduced: AS9100D clauses 6.1 (risks
  and opportunities) and 8.1.1 (operational risk) require risk
  assessment and mitigation planning for production operations; the
  RPN and risk-matrix practice above is common FMEA methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

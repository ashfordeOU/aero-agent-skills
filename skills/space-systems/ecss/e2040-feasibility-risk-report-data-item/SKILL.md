---
name: e2040-feasibility-risk-report-data-item
description: "Assess a device feasibility and risk report against the required contents of ECSS-E-ST-20-40C Annex F at the close of the definition phase. Use when the report has to show that each feasibility question is answered on evidence and that every risk behind it is scored, mitigated and stated as a residual: form the severity-by-likelihood magnitude of each risk before and after mitigation, band both into the declared risk categories, measure the reduction the mitigation actually buys, close a feasibility question only when its evidence exists and no linked residual sits above the accepted band, and compute the criticality-weighted feasibility confidence. Trigger: ecss, e-st-20-40-device-scope, e2040-feasibility-risk-report-data-item, feasibility-question-closure, risk-severity-likelihood-magnitude, residual-risk-banding, mitigation-reduction-credit, definition-phase-feasibility-confidence."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-feasibility-risk-report-data-item, feasibility-question-closure, risk-severity-likelihood-magnitude, residual-risk-banding, mitigation-reduction-credit, definition-phase-feasibility-confidence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Feasibility and Risk Report Data Item (space-systems/ecss/e2040-feasibility-risk-report-data-item)

Use when the task is the required contents of the feasibility and risk
report of ECSS-E-ST-20-40C Annex F -- the record produced during the
definition phase that says which questions about building the device are
still open, what each one risks, and what is left after the mitigation
the project intends to fund.

## Domain quick reference

- A risk is scored on two ordinal scales, severity and likelihood, each
  a whole index from 1 to 5. Their product is the **magnitude**, and the
  magnitude is banded into named categories by declared boundaries. The
  product is ordinal too: a magnitude of 12 is worse than one of 8, but
  it is not "1.5 times" anything.
- Every risk carries two scores: the **initial** one and the
  **residual** one after the mitigation is applied. A mitigation that
  moves neither index buys nothing, however much text it carries, and a
  residual worse than the initial is a bookkeeping error rather than a
  risk that grew.
- Mitigation normally moves likelihood; moving severity usually means
  changing the design, not adding an action. Both are permitted here,
  but the reduction credit is computed from the magnitudes so a plan
  claiming a category jump has to show the indices that produce it.
- A **feasibility question** is closed only on two conditions together:
  a named piece of evidence exists, and no risk linked to the question
  has a residual category above the accepted band. Evidence alone
  closes nothing while an unacceptable residual is still attached.
- Feasibility is reported as a **criticality-weighted confidence**, the
  closed weight over the total weight. Weighting is what stops a report
  closing nine minor questions and reading as 90 percent feasible while
  the question that decides the device stays open.

## Workflow

1. Check the report's section list against the required contents and
   name every absent section before scoring anything.
2. Validate the declared category bands: names in worsening order with
   strictly increasing upper magnitudes, the last band open-ended. A
   band set that overlaps or leaves a gap cannot categorize a risk.
3. Validate every risk: identifier, severity and likelihood as whole
   indices in range, and residual indices defaulting to the initial
   ones when the report declares no mitigation.
4. Form the initial and residual magnitudes, band both, and compute the
   reduction the mitigation buys as the magnitude difference; flag a
   residual above the initial as an inconsistent entry.
5. Validate every feasibility question: identifier, positive
   criticality weight, evidence reference, and the risks it depends on.
   Reject a link to a risk the register does not carry.
6. Close each question against both conditions and compute the
   criticality-weighted feasibility confidence over the question set.
7. Report the confidence against the required level, the count of risks
   in each residual band, and the open questions, unacceptable
   residuals and empty mitigations as separate findings.

## Pitfalls

- Averaging severity and likelihood instead of banding their product.
  An average turns a 5-by-1 and a 3-by-3 into the same number and
  erases the catastrophic-but-rare case the report exists to surface.
- Taking mitigation credit in the text but not in the indices. If the
  residual scores equal the initial ones, the report has recorded an
  intention, not a reduction, and the risk is still where it started.
- Closing a feasibility question on evidence while an unacceptable
  residual is still linked to it. Both conditions are required; the
  evidence answers the question, the residual says whether the answer
  survives.
- Reporting the count of open questions instead of their weight. Ten
  trivial open questions and one driving open question are very
  different feasibility positions and the same count.
- Treating the magnitude product as a ratio scale and computing a
  percentage reduction from it. The reduction is a movement between
  bands on an ordinal scale; report the indices that moved.

## Behavior contract (gate 3)

The section check, band validation, risk scoring and banding, mitigation
reduction, question-link validation, two-condition closure and the
criticality-weighted confidence are exercised by the gate 3 contract
test: scripts/test_e2040_feasibility_risk_report_data_item.py against
scripts/e2040_feasibility_risk_report_data_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_feasibility_risk_report_data_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

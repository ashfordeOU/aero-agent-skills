---
name: e10-req-risk-analysis
description: "Use when assessing the technical/requirement risk of a candidate or derived requirement during ECSS-E-ST-10C flow-down: determine likelihood x severity into a risk class, feed the project risk register, and gate baselining on a defined mitigation for medium-and-above risk consistent with M-ST-80. Trigger: ecss, e-st-10c, requirement risk, risk register, risk analysis, technical risk, mitigation, m-st-80, risk index, likelihood severity."
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
  tags: [ecss, e-st-10c, requirement-risk, risk-register, mitigation, m-st-80, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirement Risk Analysis (space-systems/ecss/e10-req-risk-analysis)

Use when the task is analysing the technical/requirement risk of a
candidate or derived requirement at a given flow-down level under
ECSS-E-ST-10C clause 5.2.3.3, feeding the project risk register, and
defining mitigation consistent with M-ST-80.

## Domain quick reference

- ECSS-E-ST-10C clause 5.2.3.3 requires each level of the requirement
  flow-down (customer TS through every lower-level TS) to analyse the
  technical/requirement risk of its requirements and enter the result
  in the project risk register.
- Risk is scored as likelihood x severity (each 1-5), consistent with
  the ECSS risk-management standard (M-ST-80): risk index bands into
  low (<=4), medium (5-9), high (10-16), very_high (17-25).
- Medium, high, and very_high risks require a defined mitigation
  before the requirement can be baselined; low risks may be logged and
  accepted (waived) without one.
- This leaf scopes requirement-level risk analysis only. Broader
  technical risk management across the whole project (identification,
  analysis, mitigation, residual-risk tracking) is the sibling
  e10-risk-mgmt leaf (10C clause 5.6.8).

## Workflow

1. For each requirement at the level under analysis, score likelihood
   and severity (1-5 each) and compute the risk index and risk class.
2. Enter the scored requirement into the project risk register with
   its description (status: identified).
3. If the risk class is medium, high, or very_high, define a
   mitigation and record it against the register entry (status:
   mitigated). If low, either leave it logged or waive it with a
   recorded rationale (status: waived).
4. Check the register for the level (or the whole flow-down): every
   entry requiring mitigation must be mitigated before the
   requirement baseline can proceed.
5. Carry residual/open risk forward; do not baseline a requirement
   with an open medium-and-above risk.

## Pitfalls

- Baselining a requirement while a medium-and-above risk is still
  only "identified" (no mitigation recorded) — the gate is skipped.
- Waiving a risk that requires mitigation instead of mitigating it
  (waiver is only valid for risks that do not require mitigation).
- Scoring likelihood or severity outside 1-5, or leaving the
  description blank so the register entry is not traceable to a
  rationale.
- Confusing this leaf's per-requirement risk analysis with the
  broader project technical risk management process (identification,
  mitigation, residual tracking across the whole project) — see the
  sibling e10-risk-mgmt leaf (10C clause 5.6.8).

## Behavior contract (gate 3)

The risk-scoring, register-entry, mitigation, and register-readiness
logic is exercised by the gate 3 contract test:
scripts/test_e10_req_risk_analysis.py against
scripts/e10_req_risk_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_req_risk_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

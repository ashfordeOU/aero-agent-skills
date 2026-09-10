---
name: e10-risk-mgmt
description: "Use when managing technical risk for a space project under ECSS-E-ST-10C clause 5.6.8: identify a risk, analyse it into a likelihood x severity risk class, plan and record mitigation actions for risks that require them, assess the residual risk left after mitigation, and escalate residual risk that remains above the acceptable band for formal acceptance, in coordination with the ECSS risk-management standard M-ST-80. Distinct from the sibling e10-req-risk-analysis leaf, which scores risk per individual requirement rather than tracking the project-wide risk register through mitigation, residual assessment, and acceptance. Trigger: ecss, e-st-10c, technical risk management, risk register, mitigation action, residual risk, risk acceptance, m-st-80, risk escalation."
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
  tags: [ecss, e-st-10c, technical-risk, risk-register, mitigation, residual-risk, m-st-80, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Technical Risk Management (space-systems/ecss/e10-risk-mgmt)

Use when the task is managing technical risk for a space project
under ECSS-E-ST-10C clause 5.6.8: identification, analysis,
mitigation, and residual-risk tracking across the project risk
register, in coordination with M-ST-80.

## Domain quick reference

- ECSS-E-ST-10C clause 5.6.8 requires system engineering to manage
  technical risk across the project: identify risks, analyse them,
  plan and track mitigation, and carry residual risk to closure or
  formal acceptance, in coordination with the ECSS risk-management
  standard (M-ST-80).
- Risk is scored as likelihood x severity (each 1-5), banded into low
  (<=4), medium (5-9), high (10-16), very_high (17-25), consistent
  with M-ST-80.
- Medium, high, and very_high risks require a recorded mitigation
  action; low risks close without one.
- After mitigation, the residual risk (likelihood x severity as it
  stands post-mitigation) is reassessed. Residual risk in the
  acceptable (low) band closes; residual risk still medium or above is
  escalated and needs a formal acceptance decision (rationale +
  accepting authority) before the register entry can close.
- This leaf scopes the project-wide risk-management process. Scoring
  the technical/requirement risk of one requirement at a flow-down
  level and feeding the register is the sibling e10-req-risk-analysis
  leaf (10C clause 5.2.3.3); that leaf does not track residual risk or
  escalation/acceptance.

## Workflow

1. Identify the risk: open a register entry with a risk_id, title,
   description, and category (status: identified).
2. Analyse the risk: score likelihood and severity (1-5 each) to get
   the risk index and class (status: analysed).
3. If the risk class requires mitigation (medium/high/very_high),
   define and record a mitigation action with an owner (status:
   mitigated). If low, close the entry directly with no mitigation
   step.
4. After the mitigation action is in place, assess the residual risk
   (likelihood x severity as mitigated). If the residual class is low,
   close the entry. If it is still medium or above, escalate it.
5. Resolve every escalated entry with a formal acceptance decision
   (rationale and accepting authority) before it can be treated as
   closed for milestone/gate purposes.
6. Check the register: it is ready only when every entry has reached
   a terminal status (closed or accepted); list and carry forward any
   entry still open.

## Pitfalls

- Closing a risk that requires mitigation without ever recording a
  mitigation action (skips the required step).
- Treating an escalated residual risk as closed without a recorded
  acceptance rationale and accepting authority.
- Re-analysing a risk that has already moved past 'identified'
  instead of carrying its existing score forward.
- Confusing this leaf's project-wide risk-management process
  (identification through mitigation, residual assessment, and
  acceptance) with the sibling e10-req-risk-analysis leaf's narrower
  per-requirement risk scoring (10C clause 5.2.3.3).

## Behavior contract (gate 3)

The identification, analysis, mitigation, residual-risk, and
acceptance logic is exercised by the gate 3 contract test:
scripts/test_e10_risk_mgmt.py against scripts/e10_risk_mgmt_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e10_risk_mgmt.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

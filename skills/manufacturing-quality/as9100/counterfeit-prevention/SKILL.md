---
name: counterfeit-prevention
description: "Use when you must plan counterfeit parts prevention for an aerospace procurement: score the counterfeit risk from the sourcing and verification controls in place, decide whether reporting is required, and confirm the procurement control set is complete per AS9100 practice. Produces the risk level, the reporting trigger, and the control completeness verdict that gate procurement release. Trigger: counterfeit prevention, counterfeit parts, procurement control, as9100, supply chain, incoming inspection."
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
  tags: [counterfeit-prevention, counterfeit-parts, procurement-control, supply-chain, incoming-inspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# AS9100 Counterfeit Prevention (manufacturing-quality/as9100/counterfeit-prevention)

Use when the task is counterfeit parts prevention planning:
procurement controls, risk scoring, and reporting triggers per
AS9100 practice.

## Domain quick reference

- AS9100 clause 8.1.4 requires counterfeit parts prevention:
  approved sources, verification of suspect items, and reporting
  of confirmed counterfeit parts.
- Core controls: authentic source, verification plan, approved
  distributor, and incoming inspection.
- Missing controls raise the counterfeit risk; confirmed or
  suspected counterfeit parts must be reported.
- A complete control set is the precondition for procurement
  release.

## Workflow

1. Collect the procurement controls in place.
2. Score the risk with counterfeit_risk.
3. Decide on reporting with reporting_required.
4. Confirm completeness with procurement_control_ok.
5. Gate procurement release on the verdicts.

## Pitfalls

- Treating an approved distributor list as a verification plan.
- Releasing procurement with fewer than the full control set.
- Skipping the reporting trigger on a medium or high risk item.

## Behavior contract (gate 3)

The risk, reporting, and completeness logic is exercised by the
gate 3 contract test: scripts/test_counterfeit_prevention.py
against scripts/counterfeit_prevention_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_counterfeit_prevention.py

## Compliance

- Standards referenced, not reproduced: AS9100 text is proprietary
  (IAQG/SAE); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.

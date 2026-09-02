---
name: operating-support-hazard-analysis
description: "Use when you must run or review the operating and support hazard analysis (O&SHA) for an aircraft or system per ARP4761A: identify hazards from operational scenarios and maintenance tasks, score each hazard on the severity by likelihood risk matrix, assign the risk index and acceptability band, and flag safety critical maintenance tasks for the hazard log. Produces the scored hazard register, the acceptability verdict per hazard, and the critical task list that feed the system safety assessment. Trigger: operating and support hazard analysis, O&SHA, maintenance hazard, ground operations hazard, risk matrix, hazard log, critical task."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [operating-support-hazard-analysis, oshsa, maintenance-hazard, ground-operations-hazard, risk-matrix-scoring, hazard-log, critical-task]
  version: 0.1.0
  author: Aero Agent Skills
---

# Operating and Support Hazard Analysis (systems-engineering-safety/arp4761a/operating-support-hazard-analysis)

Use when the task is the operating and support hazard analysis (O&SHA)
per ARP4761A: hazards from operational use and maintenance, risk
matrix scoring, and the critical task list for the hazard log.

## Domain quick reference

- O&SHA finds hazards tied to operational use and to maintenance of
  the aircraft or system, including ground handling tasks.
- Each hazard is scored by combining a severity category with a
  likelihood category on the risk matrix.
- The risk index maps to an acceptability band: unacceptable, acceptable
  with mitigation, or acceptable.
- A maintenance task is critical when it involves an unacceptable
  hazard, or is safety significant and involves a hazard that still
  needs mitigation.
- The scored hazards and critical tasks feed the system safety
  assessment and the hazard log.

## Workflow

1. Collect the operational scenarios and the maintenance task list.
2. Identify the hazards each scenario and task can produce.
3. Score every hazard with a severity and a likelihood category.
4. Compute the risk index and the acceptability band per hazard.
5. Flag the critical tasks and gate the hazard log update.

## Pitfalls

- Scoring a hazard without a likelihood category; the risk index needs
  both axes of the matrix.
- Using a severity or likelihood name outside the matrix categories;
  the scoring is undefined.
- Entering the same hazard twice in the log; each hazard keeps one id.
- Missing a safety significant task that touches a hazard outside the
  acceptable band; it must be flagged critical.

## Behavior contract (gate 3)

The risk matrix, register, and critical task logic is exercised by the
gate 3 contract test: scripts/test_operating_support_hazard_analysis.py
against scripts/operating_support_hazard_analysis_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_operating_support_hazard_analysis.py

## Compliance

- Standards referenced, not reproduced: ARP4761A text is proprietary
  (SAE); summary-only per standards-map.yaml. The risk matrix banding
  is common safety-analysis methodology.
- compliance: STANDARDS-REF, gated: false.

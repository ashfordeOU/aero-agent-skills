---
name: quality
description: "Use when scoping or preparing AS9100 aerospace quality management work: map an audit focus area to the aerospace clauses (operational risk, configuration management, product safety, counterfeit prevention, external providers, special processes), assemble the minimum audit evidence for each clause, and determine when a corrective action record closes a nonconformance. AS9100 is ISO 9001:2015 plus aerospace-specific requirements, so audits demonstrate the QMS against both. Trigger: AS9100 audit, quality management system, QMS, aerospace clause, audit evidence, counterfeit prevention, corrective action, nonconformance, special processes."
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
  tags: [as9100, qms, quality, audit, counterfeit-prevention, corrective-action]
  version: 0.1.0
  author: AeroSkills
---

# AS9100 Quality Management (manufacturing-quality/as9100/quality)

Use when the task is aerospace quality management per AS9100: clause
scoping, audit evidence, and corrective-action closure for the
aviation, space, and defense QMS.

## Domain quick reference

- AS9100 builds on ISO 9001:2015 and adds aerospace clauses:
  operational risk, configuration management, product safety,
  counterfeit prevention, external providers, and special processes.
- Audits demonstrate the QMS against the clauses with evidence
  artifacts; the evidence set is confirmed with the auditor's plan.
- A corrective action closes a nonconformance only when the record
  carries containment, root cause, and corrective action.
- Counterfeit prevention (8.1.4) and product safety (8.1.3) are the
  aerospace-specific focus areas auditors probe first.

## Workflow

1. Scope the audit or QMS improvement area.
2. Map the focus to the aerospace clause.
3. Assemble the minimum evidence artifacts for that clause.
4. Track nonconformances; close records only when containment, root
   cause, and corrective action are recorded.
5. Confirm the evidence set and closure criteria with the QMS
   documentation and the auditor's plan.

## Pitfalls

- Evidence without a clause mapping (no audit linkage).
- Closing a nonconformance with corrective action but no root cause.
- Counterfeit prevention reduced to a policy statement with no
  supplier declarations or quarantine records.
- Assuming AS9100 clauses without the ISO 9001:2015 base.

## Behavior contract (gate 3)

The clause-scoping, evidence, and corrective-action logic is exercised
by the gate 3 contract test: scripts/test_quality.py against
scripts/quality_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_quality.py

## Compliance

- Standards referenced, not reproduced: AS9100 text is proprietary
  (IAQG/SAE); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.

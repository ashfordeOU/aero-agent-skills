---
name: first-article-inspection
description: "Use when preparing or reviewing an AS9102 first article inspection (FAI) report: determine whether forms 1, 2, and 3 (part accountability, material and special processes, characteristic accountability) are present and acceptable, validate that all nonconformances are closed, classify the FAI as complete or not complete, and check whether a production change triggers a delta FAI. Also scope the characteristic accountability count against the measured population. Trigger: first article inspection, fai, as9102, form 1, form 2, form 3, part accountability, characteristic, delta fai, production."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9102
    reference-only: true
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9102
  tags: [as9102, fai, first-article-inspection, form-1, form-2, form-3, delta-fai]
  version: 0.1.0
  author: AeroSkills
---

# AS9102 First Article Inspection (manufacturing-quality/as9102/first-article-inspection)

Use when the task is an AS9102 first article inspection: form
completeness, delta FAI triggers, and characteristic accountability
for the aerospace production article.

## Domain quick reference

- AS9102 is the aerospace FAI standard (IAQG); the report has three
  forms: form 1 part accountability, form 2 material and special
  processes, form 3 characteristic accountability.
- An FAI is complete only when forms 1, 2, and 3 are all present,
  each is acceptable, and all nonconformances are closed.
- A delta FAI is required when the production article changes:
  design change affecting form, fit, or function; manufacturing
  source, process, tooling, or material change; or a two-year lapse
  since the last FAI.
- Characteristic accountability compares the measured characteristic
  population against the total defined on form 3; every design
  characteristic must be accounted for.

## Workflow

1. Collect the FAI report: forms 1, 2, and 3.
2. Check each form for presence and acceptability (part
   accountability, material and special processes, characteristic
   accountability).
3. Confirm all nonconformances are closed.
4. Classify the FAI as complete or not complete, listing the missing
   elements.
5. Check the production change history for delta FAI triggers, and
   verify the measured characteristic count covers the total.

## Pitfalls

- Declaring the FAI complete with a form absent (all three are
  required).
- Closing a form with open nonconformances (FAI stays not complete).
- Missing a delta FAI when the manufacturing source or process
  changed.
- Signing off characteristic accountability with measured count below
  the total population.

## Behavior contract (gate 3)

The completeness, delta-FAI, and accountability logic is exercised by
the gate 3 contract test: scripts/test_first_article_inspection.py
against scripts/first_article_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_first_article_inspection.py

## Compliance

- Standards referenced, not reproduced: AS9102/AS9100 text is
  proprietary (IAQG/SAE); summary-only per standards-map.yaml and
  brief 06.
- compliance: STANDARDS-REF, gated: false.

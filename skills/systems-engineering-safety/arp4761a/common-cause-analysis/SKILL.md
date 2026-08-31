---
name: common-cause-analysis
description: "Use when you must plan or review common cause analysis for a safety assessment per ARP4761A: score the zonal safety analysis items in a zone, check that the analysis set covers zonal, particular risk, and common mode analysis, and flag zones that need action. Produces the zone score and verdict, and the common cause analysis set completeness check. Trigger: common cause analysis, zonal safety analysis, particular risk analysis, common mode analysis, arp4761a, zsa."
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
  tags: [common-cause-analysis, zonal-safety-analysis, particular-risk-analysis, common-mode-analysis, zsa]
  version: 0.1.0
  author: AeroSkills
---

# ARP4761A Common Cause Analysis (systems-engineering-safety/arp4761a/common-cause-analysis)

Use when the task is common cause analysis per ARP4761A: zonal
safety scoring, analysis set completeness, and action flags.

## Domain quick reference

- Common cause analysis covers three studies: zonal safety
  analysis (ZSA), particular risk analysis (PRA), and common mode
  analysis (CMA).
- ZSA examines physical interference and environment hazards
  inside a zone; each item passes or fails.
- A zone with many failed items needs action before the safety
  assessment closes.
- The analysis set must cover all three studies for the common
  cause analysis to be complete.

## Workflow

1. Collect the zone hazard items with their pass-fail status.
2. Score the zone with zsa_zone_check.
3. Check the analysis set with cca_complete.
4. Flag reporting needs and revisit failed items.
5. Gate the safety assessment on zone verdicts and set
   completeness.

## Pitfalls

- Treating a zonal pass list as a completed common cause analysis.
- Missing the common mode study when the set claims coverage.
- Accepting a zone with multiple failed items without action.

## Behavior contract (gate 3)

The zone scoring and set completeness logic is exercised by the
gate 3 contract test: scripts/test_common_cause_analysis.py against
scripts/common_cause_analysis_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_common_cause_analysis.py

## Compliance

- Standards referenced, not reproduced: ARP4761A text is
  proprietary (SAE); summary-only per standards-map.yaml and
  brief 06.
- compliance: STANDARDS-REF, gated: false.

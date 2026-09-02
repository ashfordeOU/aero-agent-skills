---
name: zonal-safety-analysis
description: "Use when you must perform or review the zonal safety analysis per ARP4761A: identify the physical zones of the aircraft, classify each zonal hazard by severity, assess separation and containment between the zone sources and the protected components, confirm the zonal hazard checklist is complete, and produce the ZSA report for the safety assessment. The zonal safety analysis finds the hazards created by the zone contents and the external threats that enter the zone, and flags the zones that need action. Trigger: zonal safety analysis, zone identification, zonal hazard, hazard severity, separation, containment, fire zone, arp4761a, zsa."
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
  tags: [zonal-safety-analysis, zonal-hazard, zone-identification, hazard-severity, fire-zone, separation, containment, zsa, arp4761a]
  version: 0.1.0
  author: Aero Agent Skills
---

# ARP4761A Zonal Safety Analysis (systems-engineering-safety/arp4761a/zonal-safety-analysis)

Use when the task is the zonal safety analysis (ZSA) per ARP4761A:
zone identification, hazard severity classification, separation and
containment assessment, zonal hazard checklist completeness, and the
ZSA report that rolls the findings up for the safety assessment.

## Domain quick reference

- ZSA is one of the three common cause analyses in ARP4761A, next to
  particular risk analysis (PRA) and common mode analysis (CMA). It
  examines each physical zone of the aircraft: the components
  installed in the zone, the structure, the wiring, the plumbing, and
  the external threats that can enter the zone such as fire, fluid
  leaks, and impacts.
- Severity classes follow the ARP4761A ladder: minor (rank 1), major
  (2), hazardous (3), catastrophic (4). A zone with findings
  ['minor', 'major', 'hazardous'] rolls up to 'hazardous' (the
  highest severity present); an empty finding list rolls up to
  'none'.
- The zonal hazard checklist must be fully assessed before the zone
  can be accepted: 9 of 12 items assessed is 0.75 coverage and not
  complete; 12 of 12 is 1.0 and complete.
- Separation verdict: measured clearance at least the required gap is
  'ok' (50.0 mm against 50.0 mm required), any shortfall is 'action'
  (49.0 against 50.0).
- Containment verdict: barrier rating at least the hazard energy is
  'ok' (rating 3 against energy 2), otherwise 'action' (rating 2
  against energy 3).
- Report rollup (verified by the contract test): three zones with
  assessed/total 10/10, 8/10, 6/6 and severity rollups major,
  hazardous, none give total_zones 3, action_zones ['142', '143'],
  checklist coverage 24/26 (about 0.923), and verdict 'action'.

## Workflow

1. Identify the physical zones of the aircraft and the components in
   each zone (zone_identification in the logic module).
2. Classify the hazards in each zone by severity with
   severity_rank and zone_severity_rollup.
3. Assess separation between the zone components and the hazard
   sources with separation_verdict, and containment of the sources
   with containment_verdict.
4. Check the zonal hazard checklist completeness with
   checklist_coverage and checklist_complete.
5. Produce the ZSA report with zsa_report and gate the safety
   assessment on the zone verdicts and the checklist coverage.

## Pitfalls

- Confusing ZSA with the ARP4761A safety-assessment skill: severity
  here is categorized per physical zone content and external threats,
  not per failure condition in the FHA/PSSA/SSA sequence.
- Confusing ZSA with the whole common-cause-analysis skill: CCA
  covers ZSA, PRA, and CMA; a zonal pass list alone is not a
  completed common cause analysis.
- Rating the zone findings without the severity classification, so
  the rollup and the report verdict lose their basis.
- Forgetting the external threats that enter the zone (fire, fluid
  leaks, impacts) and assessing only the components inside it.
- Accepting a zone while checklist items remain unassessed (coverage
  below 1.0); an incomplete checklist is an open finding.
- Treating separation or containment as absolute when the verdict is
  'action' and the zone still needs mitigation before acceptance.
- Double counting a hazard already covered by the fault tree or the
  particular risk analysis without a cross-reference in the report.
- Reusing a zone definition across programs without re-identifying
  the zones, since zone boundaries depend on the installed
  configuration.

## Behavior contract (gate 3)

The severity classification, rollup, checklist coverage and
completeness, separation and containment verdicts, and report rollup
logic is exercised by the gate 3 contract test:
scripts/test_zonal_safety_analysis.py against
scripts/zonal_safety_analysis_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_zonal_safety_analysis.py

## Compliance

- Standards referenced, not reproduced: ARP4761A text is
  proprietary (SAE); summary-only per standards-map.yaml and
  brief 06.
- compliance: STANDARDS-REF, gated: false.

---
name: configuration-management
description: "Use when you must manage DO-178C software configuration: establish configuration baselines, record and process problem reports, control changes to baselined data, and maintain archive and recovery procedures for software lifecycle data. Determine when independent approval of changes applies, which is required at levels A and B, and gate software release on closed problem reports, a current baseline, and an archive capability. Trigger: DO-178C configuration management, configuration baselines, problem reports, change control, change control board, archive and recovery, software release."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
  - id: arp4754a
    reference-only: true
  - id: arp4761a
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do178c
  tags: [do-178c, configuration, baselines, changes, release]
  version: 0.1.0
  author: Aero Agent Skills
---

# DO-178C Configuration Management (avionics/do178c/configuration-management)

Use when the task is DO-178C configuration-management work: keeping the
software lifecycle data controlled, traceable, and recoverable.

## Domain quick reference

- Configuration management (DO-178C): baselines, problem reporting,
  change control, and archive/recovery of software lifecycle data.
- Baselines freeze a consistent set of lifecycle data; changes to
  baselined data are reviewed at every software level.
- Problem reports record defects and discrepancies; release requires
  them to be analyzed and closed.
- Levels A and B require independent approval of changes.
- Archive and recovery preserve the ability to reconstruct released
  software and its data.

## Workflow

1. Establish configuration baselines for software lifecycle data.
2. Record problem reports; analyze and close them.
3. Control changes to baselined data; levels A/B add independent
   approval.
4. Maintain archive and recovery procedures.
5. Gate release: current baseline, closed problem reports, archive
   capability in place.

## Pitfalls

- Releasing with open problem reports.
- Changes applied without review of baselined data.
- No archive/recovery path for released software.
- Missing independence for change approval at level A or B.

## Behavior contract (gate 3)

The baseline, change-control, and release-gate logic is exercised by the
gate 3 contract test: scripts/test_cm.py against scripts/cm_logic.py
(stdlib unittest, offline). Run: python3 scripts/test_cm.py

## Compliance

- Standards referenced, not reproduced: DO-178C / ARP4754A / ARP4761A text
  is proprietary (RTCA/SAE); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.

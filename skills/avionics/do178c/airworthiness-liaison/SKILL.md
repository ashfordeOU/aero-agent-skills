---
name: airworthiness-liaison
description: "Use when you must manage DO-178C airworthiness and certification liaison for an airborne software item: confirm the certification basis items with evidence, score stage-of-involvement audit readiness against the software level threshold, and track open liaison items to closure before authority audits. Produces the certification-basis coverage account, the SOI readiness verdict, and the open-item action flags that keep the certification plan on schedule. Trigger: airworthiness liaison, certification liaison, soi audit, certification basis, authority communication, audit readiness."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
  - id: arp4754a
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do178c
  tags: [airworthiness-liaison, certification-liaison, soi-audit, certification-basis, authority-communication, audit-readiness, certification, liaison]
  version: 0.1.0
  author: Aero Agent Skills
---

# DO-178C Airworthiness Liaison (avionics/do178c/airworthiness-liaison)

Use when the task is DO-178C airworthiness and certification liaison:
certification-basis coverage, SOI audit readiness, and open-item
tracking with the certification authority.

## Domain quick reference

- Certification basis: the airworthiness requirements the software
  item must satisfy (airworthiness regulations plus the accepted
  means of compliance); each basis item needs evidence.
- Stage-of-involvement (SOI) audits: the authority audits planning,
  development, verification, and configuration management artifacts;
  readiness is the fraction of required evidence that is present.
- Readiness thresholds are project-defined and scale with the
  software level: levels A and B demand full evidence, lower levels
  tolerate small gaps.
- Open liaison items (issue papers, audit findings) must close
  before the certification plan can complete.

## Workflow

1. Collect the certification basis items and their evidence status.
2. Build the coverage account with cert_basis_coverage.
3. Map required evidence to the software level and score SOI
   readiness with soi_readiness.
4. Track open liaison items with liaison_action.
5. Gate the next audit on readiness and open-item closure.

## Pitfalls

- Counting basis items without evidence as covered.
- Applying a level A readiness bar to level D work (and the reverse).
- Letting open items ride through audits unclosed.

## Behavior contract (gate 3)

The certification-basis, readiness, and action logic is exercised by
the gate 3 contract test: scripts/test_airworthiness_liaison.py
against scripts/airworthiness_liaison_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_airworthiness_liaison.py

## Compliance

- Standards referenced, not reproduced: DO-178C and ARP4754A text is
  proprietary (RTCA/SAE); summary-only per standards-map.yaml and
  brief 06. No objective tables or appendix text.
- compliance: STANDARDS-REF, gated: false.

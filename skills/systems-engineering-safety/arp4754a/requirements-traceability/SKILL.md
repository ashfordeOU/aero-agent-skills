---
name: requirements-traceability
description: "Use when planning or auditing requirements traceability per ARP4754A: determine closure status across SRATS, high-level requirements (HLR), low-level requirements (LLR), code, and test levels, list traceability gaps for a level, flag derived requirements, and compute the verified-closure ratio of the trace matrix. Bidirectional closure (each level traces down and back up) and open verification items drive the closed/open verdict; all logic is deterministic, offline stdlib. Trigger: traceability, requirements, closure, SRATS, high-level requirements, low-level requirements, derived requirements, verification, trace matrix."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4754a
  tags: [arp4754a, traceability, requirements-closure, srats, hlr, llr, derived-requirements, verification]
  version: 0.1.0
  author: AeroSkills
---

# ARP4754A Requirements Traceability (systems-engineering-safety/arp4754a/requirements-traceability)

Use when the task is requirements traceability per ARP4754A:
determining closure across the SRATS-to-test chain, listing
traceability gaps, flagging derived requirements, and measuring
verified-closure of the trace matrix.

## Domain quick reference

- ARP4754A development assurance runs on traceability: system
  requirements (SRATS) trace to high-level requirements (HLR), HLR
  trace to low-level requirements (LLR), LLR trace to code and test.
- Closure is bidirectional per level: every HLR has an incoming SRATS
  trace and an outgoing LLR trace; every LLR has an incoming HLR trace
  and an outgoing code or test trace.
- A traced pair with verification still open is an open verification
  item and keeps the closure status open.
- Derived requirements (requirements whose content is not directly
  traceable to a parent source) must be explicitly flagged.
- Verified-closure ratio = verified traces / total traces (0..1).

## Workflow

1. Collect the trace matrix as (from, to, verified) links.
2. Determine closure status and review the gap list.
3. Focus on one level (srats/hlr/llr/code/test) for triage.
4. Flag derived requirements explicitly.
5. Track the verified-closure ratio as evidence of closure progress.

## Pitfalls

- One-directional closure treated as closure (HLR down but no SRATS
  back-up).
- Verification status ignored (open items left in a 'closed' claim).
- Derived requirements unflagged and treated as top-level.
- Ratio reported without the gap list (a high ratio can still hide
  missing coverage).

## Behavior contract (gate 3)

The logic is exercised by the gate 3 contract test:
scripts/test_requirements_traceability.py against
scripts/requirements_traceability_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_requirements_traceability.py

## Compliance

- Standards referenced, not reproduced: ARP4754A / ARP4761A text is
  proprietary (SAE); summary-only per standards-map.yaml and brief 06.
- Revision note: ARP4754B (2023) supersedes ARP4754A; this skill keys
  to ARP4754A as the certification-baseline revision (FAA AC 20-174
  cites A); see standards-map.yaml arp4754a.revision_decision.
- compliance: STANDARDS-REF, gated: false.

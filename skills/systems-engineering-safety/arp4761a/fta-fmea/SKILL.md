---
name: fta-fmea
description: "Use when scoping or executing FTA (fault tree analysis) and FMEA (failure modes and effects analysis) per ARP4761A: compute minimal cut sets from AND/OR gate structures, check cut-set probability sanity against the top event probability, select the analysis set for an assurance level (FTA/FMEA always, CCA at levels A and B), and map FMEA failure-condition severity to development assurance levels. Pairs with ARP4754A development assurance; all logic is deterministic, offline stdlib. Trigger: fault tree, FTA, FMEA, FMECA, cut set, minimal cut set, failure modes, common cause, severity, probability."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [arp4761a, fta, fmea, fmeca, cut-set, minimal-cut-set, common-cause, severity, probability]
  version: 0.1.0
  author: AeroSkills
---

# ARP4761A FTA/FMEA (systems-engineering-safety/arp4761a/fta-fmea)

Use when the task is fault tree analysis or FMEA/FMECA work per
ARP4761A: deriving minimal cut sets, sanity-checking cut-set
probabilities, scoping the analysis set by assurance level, and
mapping failure-condition severity.

## Domain quick reference

- FTA models a top event as a tree of AND/OR gates over basic events;
  a minimal cut set is a smallest set of basic events whose joint
  occurrence forces the top event.
- OR gates union their children's cut sets; AND gates take the
  cartesian product, so each combination becomes one cut set.
- Cut-set probability is the product of its basic-event
  probabilities; a cut set more likely than the top event signals a
  modeling or probability error.
- FMEA catalogues failure modes and effects; severity classes map to
  development assurance levels: A = Catastrophic, B = Hazardous,
  C = Major, D = Minor, E = No safety effect.
- The analysis set scales with level: FTA and FMEA at every
  safety-significant level, CCA (ZSA/PRA/CMA) added at levels A and B.

## Workflow

1. Confirm the certification basis and the approved safety plan.
2. Build the fault tree structure (gate nodes with op AND/OR and
   children; leaves are basic events).
3. Derive minimal cut sets and check cut-set probability sanity
   against the top event probability.
4. Scope the analysis set per assurance level (FTA/FMEA, plus CCA at
   A/B).
5. Run FMEA and map failure-condition severities to levels.

## Pitfalls

- AND gates unioned instead of multiplied (missing combinations).
- Cut-set probabilities above the top event probability left
  unexplained (model or probability error).
- CCA dropped at levels A/B where common-cause analysis is expected.
- Severity mapped without the FHA-to-PSSA-to-SSA chain.

## Behavior contract (gate 3)

The logic is exercised by the gate 3 contract test:
scripts/test_fta_fmea.py against scripts/fta_fmea_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_fta_fmea.py

## Compliance

- Standards referenced, not reproduced: ARP4761A / ARP4754A text is
  proprietary (SAE); summary-only per standards-map.yaml and brief 06.
- Revision note: ARP4754B (2023) supersedes ARP4754A; this skill keys
  to ARP4754A as the certification-baseline revision (FAA AC 20-174
  cites A); see standards-map.yaml arp4754a.revision_decision.
- compliance: STANDARDS-REF, gated: false.

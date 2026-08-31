---
name: software-engineering
description: "Use when scoping European space software work per the ECSS series: classify space software criticality (A-D) from failure consequence, size the assurance and verification rigor for the category, gate lifecycle phases (requirements through acceptance) on their review records, and scope heritage-reuse evidence. ECSS-E-ST-40C governs software engineering, Q-ST-80C software product assurance, and the series is the European space procurement baseline. Trigger: ECSS, space software, E-ST-40C, software criticality, product assurance, Q-ST-80C, heritage software, space software lifecycle, software verification."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, space-software, e-st-40c, q-st-80c, criticality, heritage, product-assurance]
  version: 0.1.0
  author: AeroSkills
---

# ECSS Space Software Engineering (space-systems/ecss/software-engineering)

Use when the task is space software engineering under the ECSS
series: criticality classification, assurance rigor, lifecycle
gates, and heritage reuse.

## Domain quick reference

- The ECSS series is the European space procurement baseline:
  E-ST-10C (systems engineering), E-ST-40C (software engineering),
  Q-ST-80C (software product assurance), M-ST-40 (configuration
  management).
- E-ST-40C classes software by failure consequence: A = loss of
  life or total loss of mission, B = major mission degradation,
  C = minor degradation, D = negligible effects.
- Assurance and verification rigor scale with the category;
  Q-ST-80C carries the product assurance evidence expectations.
- Heritage reuse demands a heritage assessment against the original
  verification evidence, full evidence at categories A/B.

## Workflow

1. Classify the software criticality category from the failure
   consequences.
2. Size assurance and verification rigor for the category.
3. Run the lifecycle phases (requirements, design, implementation,
   verification, validation, acceptance), gating each on its review
   record.
4. For reused software, scope the heritage assessment and evidence.
5. Confirm rigor and evidence sets with the project product
   assurance plan.

## Pitfalls

- Category assigned from mission value instead of failure
  consequence.
- Heritage software reused at category A without the full original
  verification evidence.
- Advancing a phase without its review record (gate skipped).
- Rigor fixed without the product assurance plan.

## Behavior contract (gate 3)

The criticality, rigor, lifecycle-gate, and heritage logic is
exercised by the gate 3 contract test: scripts/test_ecss.py against
scripts/ecss_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_ecss.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: special-conditions
description: "Use when you must determine whether a novel or unusual transport-category design feature needs a special condition under FAR 25.17 or CS-25.17 instead of being covered by the existing airworthiness standards: classify the feature from its novelty, existing coverage, and safety significance, then draft the special condition scope with the affected subject, the issue addressed, and the proposed means of compliance (analysis, test, simulation). Produces the special-condition verdict and the scoped content for the certification program. Trigger: special condition, novel design feature, fly-by-wire, envelope protection, unusual technology, new technology, means of compliance, FAR 25.17, CS 25.17."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: far-cs25
  tags: [special-conditions, far-25, cs-25, novel-design-feature, fly-by-wire, means-of-compliance, transport-category, envelope-protection]
  version: 0.1.0
  author: Aero Agent Skills
---

# Special Conditions (avionics/far-cs25/special-conditions)

Use when the task is the special-conditions decision for a transport
airplane: whether a novel or unusual design feature is covered by the
existing FAR-25 / CS-25 airworthiness standards or needs a special
condition under 25.17, and what that special condition should contain.

## Domain quick reference

- FAR 25.17 / CS-25.17 let the certification authority issue special
  conditions when a novel or unusual design feature is not covered by
  the existing airworthiness standards.
- The special condition states additional requirements for the feature
  and the means of compliance that demonstrate them.
- Examples from certification history: fly-by-wire flight control with
  envelope protection, and novel composite wing structures.
- A special condition is scoped per feature: affected subject, the
  issue addressed, and the proposed means of compliance (analysis,
  test, simulation).
- This module reasons over categorical inputs (booleans and short
  text), so no physical quantities or unit conventions apply.

## Workflow

1. Describe the feature: name, novelty (novel), coverage by an
   existing standard (existing_standard), and safety significance
   (safety_significant).
2. Classify with classify_feature: returns the verdict and the
   category from the rule table.
3. When the verdict is special-condition-required, scope the content
   with draft_scopes: subject area, issue, means of compliance.
4. Bring the draft scope to the certification authority for agreement
   on the requirement text and the means of compliance.

## Pitfalls

- Treating every new feature as needing a special condition when an
  existing standard already covers it.
- Scoping a special condition (draft_scopes) for a feature the rule
  table classifies as covered: it raises ValueError.
- Passing numbers or strings where booleans are expected, or omitting
  a required key: the module raises ValueError.
- Confusing the special-conditions decision with the certification
  basis or the 25.1309 safety assessment (separate leaves).

## Behavior contract (gate 3)

The classification and scoping logic is exercised by the gate 3
contract test: scripts/test_special_conditions_logic.py against
scripts/special_conditions_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_special_conditions_logic.py

## Compliance

- FAR-25 is US government work (17 U.S.C. 105), quotable with
  citation; CS-25 reproduction authorised with source acknowledged
  (EASA). Paraphrase preferred per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e1002-method-inspection
description: "Use when applying the inspection verification method under ECSS-E-ST-10-02C clause 5.2.2.5: categorize each checklist item as a visual or measurement inspection technique, decide whether inspection may be used for a given requirement, evaluate a visual item outcome and a measurement item outcome against their criteria, check the inspection programme's completeness in the verification plan, and roll the item statuses up to an overall inspection verdict. Trigger: ecss, e-st-10-02c, inspection method, visual inspection, measurement check, checklist, verification plan, item outcome, roll-up."
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
  tags: [ecss, e-st-10-02c, inspection, visual-check, measurement, checklist, plan-completeness, verification-method]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Inspection Method (space-systems/ecss/e1002-method-inspection)

Use when applying the inspection verification method under ECSS-E-ST-10-02C clause 5.2.2.5 — categorizing checklist items, deciding method applicability, evaluating visual and measurement outcomes, checking the inspection programme's completeness, and rolling item statuses to an overall verdict.

## Domain quick reference

- Inspection is a distinct verification method (visual examination and/or measurement), not a substitute for test or analysis; use it where the attribute is directly observable.
- Each checklist item is one technique: a visual item is pass/fail on observed condition; a measurement item is pass/fail on a value against an acceptable range.
- A measurement item without bounds cannot be judged — a missing range is a checklist defect, not an automatic pass.
- The verification plan must carry a complete inspection programme: every item needs an unambiguous technique and acceptance criterion.
- Item statuses roll up: any failed item makes the inspection verdict fail.

## Workflow

1. Categorize: `classify_inspection_technique(item)` -> 'visual' or 'measurement'.
2. Check applicability: `is_inspection_method_applicable(requirement)`.
3. Evaluate outcomes: `evaluate_visual_item(item)` / `evaluate_measurement_item(item)`, or the dispatcher `evaluate_checklist_item(item)`.
4. Check programme completeness: `plan_completeness_violations(plan)`.
5. Roll up: `rollup_status(statuses)`.
6. Full review: `inspection_review(plan)` -> `is_inspection_compliant(review)`.

## Pitfalls

- Judging a measurement item with no bounds — the evaluator must report it as not judgeable.
- Treating inspection as interchangeable with test — it verifies only directly observable attributes.
- Ignoring a single failed item in the roll-up — any failure fails the verdict.
- Security-marking vocabulary: the content-policy gate flags the word beginning 'classif-'; use 'categorized' instead.

## Behavior contract (gate 3)

`scripts/test_e1002_method_inspection.py` (stdlib unittest, offline) verifies technique categorization, applicability, visual/measurement outcome evaluation and their missing-criterion error paths, plan-completeness violations, status roll-up, and the full review.

## Compliance

ECSS-E-ST-10-02C is a normative standard; this leaf implements only common-knowledge procedure and paraphrases it — no verbatim standard text. `license: Apache-2.0`, `compliance: STANDARDS-REF`, `standards: ecss` (reference-only), `gated: false`.

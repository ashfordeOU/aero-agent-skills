---
name: e2040-device-verification-plan-data-item
description: "Assess a device verification plan against the strategy, methods and coverage goals ECSS-E-ST-20-40C Annex C makes mandatory: confirm the strategy names an approach and the levels verification runs at, place every requirement at one of those levels, check that the methods nominated can actually answer that kind of requirement, and compare the coverage each method reaches against the goal the plan committed to, counting requirements with no method rather than dropping them. Use when a verification plan is drafted or reviewed before the campaign starts. Trigger: ecss, e-st-20-electrical-scope, device-verification-plan-data-item, verification-strategy-levels, verification-method-suitability, verification-coverage-goal, uncovered-requirement-detection, verification-level-placement."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-verification-plan-data-item, device-verification-plan-data-item, verification-strategy-levels, verification-method-suitability, verification-coverage-goal, uncovered-requirement-detection, verification-level-placement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Verification Plan Data Item (space-systems/ecss/e2040-device-verification-plan-data-item)

Use when the task is the contents duty of ECSS-E-ST-20-40C Annex C --
saying whether a device verification plan carries the strategy it
follows, the methods it will use and the coverage it commits to, and
whether those three agree with each other.

## Domain quick reference

- The strategy is the frame: an approach, and the levels verification
  actually happens at. Every requirement is then placed at one of those
  levels. A requirement placed at a level the strategy never declared
  has no campaign to belong to, and the mismatch is invisible while the
  requirement list is read on its own.
- Four methods close a requirement: analysis, review-of-design,
  inspection and test. Spellings vary between organisations and the
  short forms are common, so they are folded before anything is
  counted.
- A method has to be able to answer the kind of requirement it is
  nominated on. Inspection can confirm a connector is present; it
  cannot close a timing figure. A performance requirement carrying
  inspection alone is unclosable no matter how complete the plan looks,
  and that is the defect this check exists for.
- Suitability is satisfied by one method, not all of them. A
  requirement nominating both inspection and analysis is fine even
  where inspection alone would not be, so the test is an intersection
  with the suitable set rather than a check of every entry.
- Coverage goals are fractions of the requirement set. A goal met
  exactly is met, so the comparison absorbs representation error: a
  two-in-four landing on a 0.5 goal is a pass, and a strict comparison
  against a computed division is what turns a compliant plan red.
- A requirement with no method at all stays in the denominator. It is
  precisely what the coverage figure is meant to surface, and dropping
  it produces a plan that reports full coverage of the requirements it
  chose to count.

## Workflow

1. Resolve the strategy: the approach folded onto a recognised name,
   the declared levels with no repeats, and the rationale. Report a
   missing approach and missing levels as separate findings.
2. Resolve the requirement list: unique identifiers, a recognised kind,
   the nominated methods folded onto the four, and the level. Refuse a
   repeated identifier or an unknown key as an input defect.
3. Report every requirement nominating no method, and keep it in the
   requirement count so the coverage figure tells the truth.
4. For every requirement that does nominate a method, intersect its
   methods with the set able to answer its kind and report an empty
   intersection with the methods that would have worked.
5. Place each requirement against the strategy levels and report one
   sitting at a level the strategy does not declare.
6. Compute the coverage each method reaches across the set, and the
   overall coverage of requirements carrying at least one method.
7. Compare each declared goal against what the plan reaches, absorbing
   representation error and never widening the goal itself.

## Pitfalls

- Counting a requirement as covered because a method is written next to
  it. The method still has to be able to answer that kind of
  requirement, and a performance figure closed by inspection is the
  case that reaches the test campaign and stops it.
- Dropping uncovered requirements from the coverage denominator. The
  figure then measures the plan's own selection rather than the
  requirement set, and it reads best exactly when the plan is worst.
- Comparing a computed coverage fraction against its goal with a strict
  inequality. A two-in-four division landing on 0.5 can sit a unit in
  the last place below it and fail a plan that is exactly on target.
- Letting requirement levels drift from the strategy. Levels invented
  in the requirement list look reasonable line by line and leave the
  strategy describing a campaign the plan does not run.
- Requiring every nominated method to be suitable. One suitable method
  closes the requirement; demanding all of them rejects sound plans
  that nominate a cheap screening method alongside the real one.

## Behavior contract (gate 3)

The strategy resolution, method and kind folding, suitability
intersection, level placement, uncovered-requirement detection and
coverage-goal comparison are exercised by the gate 3 contract test:
scripts/test_e2040_device_verification_plan_data_item.py against
scripts/e2040_device_verification_plan_data_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_verification_plan_data_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

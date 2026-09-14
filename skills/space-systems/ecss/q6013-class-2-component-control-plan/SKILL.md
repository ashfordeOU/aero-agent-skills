---
name: q6013-class-2-component-control-plan
description: "Evaluate whether a component control plan holds the content the intermediate assurance class demands for commercial EEE parts bought under ECSS-Q-ST-60-13C clause 5.1.2.2: refuse a plan carrying no reference or issue, take each required subject in turn, treat a heading with no procedure behind it as absent, accept a subject carried by a higher-level document only where that pointer names a document and an issue, credit a referenced subject below one, compute the covered share and the depth-weighted completeness, name every absent, shallow and heading-only subject, and check customer notification and issue before the first procurement commitment. Use when a drafted plan has to become a coverage verdict. Trigger: ecss, q-st-60-13c-clause-5-1-2-2, class-two-component-control-plan, plan-subject-carried-by-reference, referenced-subject-depth-credit, component-control-plan-customer-notification, plan-issue-before-procurement-commitment, shallow-plan-subject-advisory."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-component-control-plan, class-two-component-control-plan, plan-subject-carried-by-reference, referenced-subject-depth-credit, component-control-plan-customer-notification, plan-issue-before-procurement-commitment, shallow-plan-subject-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Component Control Plan (space-systems/ecss/q6013-class-2-component-control-plan)

Use when the task is the clause 5.1.2.2 plan-content question of
ECSS-Q-ST-60-13C at the intermediate assurance class: a component
control plan has been drafted for the commercial EEE parts a programme
intends to buy, and the question is whether it holds what the class
requires it to hold.

## Domain quick reference

- The plan is the single document saying how commercial parts will be
  selected, sourced, evaluated and screened, derated, traced, replaced
  when obsolete and dispositioned when they fail. Each of those subjects
  is required at this class, and the plan is judged on whether it treats
  them, not on whether it is long.
- This class allows a subject to be carried by reference, which the
  class above does not. A plan may point at a higher-level project
  document instead of restating the rule, but only where the pointer
  names a document and an issue. A pointer with no issue points at
  whatever that document says today, which is not a rule.
- A referenced subject is treated and it is credited below one. The
  credit is what keeps a plan assembled entirely out of pointers from
  reading the same as one that writes its own rules, and the pair of
  figures is what a reviewer needs to see that.
- A subject named in a heading with nothing behind it is absent for this
  purpose. That is the most common way a plan reads complete and
  controls nothing: the contents page matches the required list while
  every section promises the subject will be addressed later.
- Depth is a declared review judgement, not a page count. It is recorded
  during plan review against the subject's own floor, and a subject
  landing exactly on that floor is admissible, the comparison tolerance
  being there to absorb representation error rather than to widen the
  floor.
- The weighted completeness runs over the full required subject list. A
  missing subject counts as nothing rather than dropping out of the
  average, so deleting a weak section can only lower the figure, which
  is the way round it has to be.
- Customer notification is the condition at this class rather than
  customer approval. The customer carries the residual risk of every
  commercial part bought under the plan, so a plan they were never told
  about is a plan they cannot price.
- Issue timing decides whether the plan controlled anything. A plan
  issued after the first procurement commitment documents choices
  already made, and no amount of subject coverage recovers the lots
  bought against no rule.

## Workflow

1. Validate the plan policy first: the covered share floor, the
   weighted completeness floor, the depth a subject must reach to count
   as treated, the credit a referenced subject earns and the marginal
   band. A completeness floor above the covered floor, a zero depth
   floor or credit, or a band wider than the floor is refused rather
   than used.
2. Validate the plan identity: a non-blank reference, a non-blank issue,
   and boolean notification and timing declarations. An absent plan, or
   one with a blank reference or issue, closes the assessment on plan
   not established.
3. Validate every declared subject: a recognised subject name, no
   duplicate, a depth in the unit interval, and either an in-plan
   procedure or a referenced document, never both.
4. Dispose each required subject as covered in the plan, covered by a
   referenced document, treated below the depth floor, stated without a
   procedure, or absent. Report all four failing lists in full rather
   than truncating at the first entry.
5. Take the covered share over the required subjects and the weighted
   completeness over the same denominator, crediting a referenced
   subject below one and a missing subject at nothing.
6. Compare both figures against their floors with a tolerance that
   absorbs representation error, then check customer notification and
   the issue against the first procurement commitment.
7. Report the covered share, the completeness, the absent, shallow and
   heading-only subjects, the referenced subjects, the weakest treated
   subject and its depth, and raise an advisory for every treated
   subject inside the marginal band. Close on one verdict: plan not
   established, subject coverage short, plan not notified to the
   customer, plan issued after procurement, or plan covers class two
   scope.

## Pitfalls

- Grading the plan on its contents page. A required subject heading with
  nothing behind it is the failure this clause exists to catch, so a
  heading without a procedure or a fully identified referenced document
  counts as absent.
- Accepting a pointer that names a document but no issue. The rule then
  changes whenever the other document is reissued, and the procurement
  made last quarter cannot be shown to have been made against anything.
- Crediting a referenced subject in full. Reference is permitted here
  and it is a thinner treatment than writing the rule, which is what the
  credit records; without it a plan of pure pointers scores as a plan.
- Averaging depth only over the sections that exist. Deleting a weak
  section would then raise the score, which is exactly backwards, so the
  denominator stays the full required subject list.
- Issuing the plan after the first lots are on order. The rules then
  describe purchases already made, and the parts bought against no rule
  stay in the build.

## Behavior contract (gate 3)

The policy validation, plan identity validation, subject validation, the
covered, referenced, shallow, heading-only and absent dispositions, the
covered share, the depth-weighted completeness, the weakest treated
subject, the customer notification and issue-timing checks, the marginal
advisories and the plan verdict are exercised by the gate 3 contract
test:
scripts/test_q6013_class_2_component_control_plan.py against
scripts/q6013_class_2_component_control_plan_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_component_control_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q6013-class-1-component-control-plan
description: "Assess whether a component control plan covers the scope the highest assurance class demands for commercial EEE parts under ECSS-Q-ST-60-13C clause 4.1.2.2: refuse a plan carrying no reference or issue, take each required subject in turn, treat a subject named without a procedure behind it as absent, compute the covered share and the depth-weighted completeness, name every missing and every shallow subject rather than the first, check customer approval and issue before the first procurement commitment, and flag a subject sitting just above the depth floor. Use when a drafted plan has to become a coverage verdict. Trigger: ecss, q-st-60-13c-clause-4-1-2-2, class-one-component-control-plan, component-control-plan-subject-coverage, commercial-part-plan-depth-weighting, component-control-plan-customer-approval, plan-issue-before-procurement-commitment, shallow-plan-subject-advisory."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-1-component-control-plan, class-one-component-control-plan, component-control-plan-subject-coverage, commercial-part-plan-depth-weighting, component-control-plan-customer-approval, plan-issue-before-procurement-commitment, shallow-plan-subject-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 1 Component Control Plan (space-systems/ecss/q6013-class-1-component-control-plan)

Use when the task is the clause 4.1.2.2 plan-scope question of
ECSS-Q-ST-60-13C at the highest assurance class: a component control
plan has been drafted for commercial EEE parts, and the question is
whether it covers what the class requires it to cover.

## Domain quick reference

- The plan is the single document that says how commercial parts will be
  selected, sourced, evaluated, screened, derated, traced, replaced when
  obsolete and dispositioned when they fail. At the highest assurance
  class each of those subjects is required, and the plan is judged on
  whether it treats them, not on whether it is long.
- A subject named in a heading with no procedure reference behind it is
  absent for this purpose. That is the single most common way a plan
  reads complete and controls nothing: the table of contents matches the
  required list while every section says the subject will be addressed
  later.
- Coverage and depth are two different numbers and both are reported.
  The covered share answers how many required subjects the plan treats
  properly; the depth-weighted completeness answers how thoroughly,
  counting a missing subject as nothing rather than omitting it from the
  average. A plan can score well on one and badly on the other, and the
  pair is what a reviewer needs.
- Depth is a declared review judgement, not a page count. It is recorded
  during plan review against the subject's own floor, and a subject
  landing exactly on its floor is admissible, the comparison tolerance
  being there to absorb representation error rather than to widen the
  floor.
- Customer approval is a condition of the plan at this class, not a
  courtesy copy. The customer carries the residual risk of a commercial
  part, so an unapproved plan is a draft whatever its coverage.
- Issue timing decides whether the plan controlled anything. A plan
  approved after the first procurement commitment documents choices
  already made, and no amount of subject coverage recovers the lots that
  were bought against no rule.
- The weakest subject and its depth are worth as much as the verdict. A
  plan clearing every floor by a hair and one clearing them comfortably
  carry the same word, and nobody can recover the difference later from
  the word alone.

## Workflow

1. Validate the plan policy first: the minimum covered share, the depth
   floor a subject must reach to count as treated, and the marginal band
   inside which a treated subject is still advised on. A share or floor
   above one, or a marginal band above the floor, is refused rather than
   used.
2. Validate the plan identity: a non-blank plan reference, a non-blank
   issue label, and boolean approval and timing declarations. An absent
   plan, or one with a blank reference, closes the assessment on plan
   not established.
3. Validate every declared subject record: a recognised subject name, no
   duplicate subject, a depth in the unit interval, and a procedure
   reference that may be blank but is then read as no procedure.
4. Decide each required subject: treated when it is declared, its depth
   reaches the floor, and a non-blank procedure reference stands behind
   it. Anything else is missing or shallow, and both lists are reported
   in full rather than truncated at the first entry.
5. Take the covered share over the required subjects and the
   depth-weighted completeness over the same denominator, counting a
   missing subject as zero depth so the average cannot be improved by
   deleting a section.
6. Compare the covered share against the policy floor with a tolerance
   that absorbs representation error, then check customer approval and
   issue before the first procurement commitment.
7. Report the covered share, the completeness, the missing and shallow
   subjects, the weakest treated subject and its depth, and raise an
   advisory for every treated subject inside the marginal band. Close on
   one verdict: plan not established, plan subject coverage short, plan
   not approved, plan issued after procurement, or plan covers class one
   scope.

## Pitfalls

- Grading the plan on its table of contents. A required subject heading
  with nothing behind it is the failure mode this clause exists to
  catch, so a heading without a procedure reference counts as missing.
- Averaging depth only over the sections that exist. Deleting a weak
  section would then raise the score, which is exactly backwards; the
  denominator stays the full required subject list.
- Treating customer approval as a distribution step. At this class the
  approval is what turns a draft into the plan, and coverage computed on
  an unapproved draft is a statement about a document nobody is bound
  by.
- Approving the plan after the first lots are on order. The rules then
  describe purchases already made, and the parts bought against no rule
  stay in the build.
- Reporting a bare pass. The covered share, the completeness and the
  weakest subject are what the next plan issue is compared against, and
  the verdict word carries none of them.

## Behavior contract (gate 3)

The policy validation, plan identity validation, subject validation,
the treated, missing and shallow decisions, the covered share, the
depth-weighted completeness, the weakest subject, the approval and
issue-timing checks, the marginal advisories and the plan verdict are
exercised by the gate 3 contract test:
scripts/test_q6013_class_1_component_control_plan.py against
scripts/q6013_class_1_component_control_plan_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_component_control_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

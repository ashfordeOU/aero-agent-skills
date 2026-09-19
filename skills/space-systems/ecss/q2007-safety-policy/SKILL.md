---
name: q2007-safety-policy
description: "Evaluate the documented safety policy and safety objectives of a space test centre under ECSS-Q-ST-20-07C clause 5.9.2: confirm the policy carries every required commitment, was approved at a level that binds resources, was communicated to personnel and is inside its review interval; then grade each objective as a measurable target with baseline, unit, direction, owner and due day, and score the progress and attainment actually reached. Use when a centre safety policy statement, its commitments or its safety objectives have to be assessed or drafted. Trigger: ecss, q-st-20-07c, test-centre-safety-policy, safety-policy-commitments, top-management-approval, policy-review-currency, safety-objective-target, safety-objective-attainment."
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
  tags: [ecss, q-st-20-test-centre-scope, q2007-safety-policy, test-centre-safety-policy, safety-policy-commitments, safety-objective-target, safety-objective-attainment, policy-review-currency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Safety Policy and Objectives (space-systems/ecss/q2007-safety-policy)

Use when the task is the safety-policy step of ECSS-Q-ST-20-07C clause 5.9.2
— deciding whether what a test centre has written down as its safety
commitments, and the targets it set itself against them, are the kind that
can actually be held to.

## Domain quick reference

- A safety policy is a set of commitments, not a sentiment. The commitments
  a centre has to make explicit are management accountability, compliance
  with the law, prevention of hazards, provision of resources, consultation
  of personnel, continual improvement and communication. A policy that omits
  one of them is not shorter; it is narrower, and the omission is always the
  commitment that would have cost something.
- Approval level is the load-bearing part. Resource provision and
  consultation can only be promised by the management that controls them, so
  a policy signed below that level promises what the signatory cannot give.
- A policy that has not reached the personnel governs nothing. Communication
  is a commitment in its own right and also the condition on which the rest
  of the commitments have effect.
- A review interval turns the policy into a maintained item. Inside the
  interval it is current, on the interval it is due, past it the centre can
  no longer claim the policy reflects the facility as it is now.
- An objective without a unit, a baseline and a direction is an aspiration.
  Direction matters because the same number is a pass for an increase target
  and a fail for a decrease one, and progress measured from the baseline is
  what distinguishes movement from noise.
- A target equal to its baseline asks for nothing and cannot be graded; it
  is an input error, not an easy objective. Movement away from the baseline
  is a finding even while the due day is still ahead.

## Workflow

1. Validate the policy: statement, commitment list, approving role, issue day
   and review interval are all required, and an unknown commitment token is
   an input error rather than an extra commitment.
2. Compute the missing commitments against the required set and report them
   by name, not as a count.
3. Grade the approval role against the levels that bind resources, and check
   the policy was communicated.
4. Grade the review currency as current, due or overdue from the issue day,
   the interval and today, on exact integer day arithmetic.
5. Validate each objective as measurable: metric, unit, baseline, target,
   direction, owner and due day, refusing a target that coincides with its
   baseline or contradicts its stated direction.
6. Grade each objective against its measured value: progress as the fraction
   of the baseline-to-target movement achieved, attainment with a named
   tolerance so a value exactly on target counts as met, and a regression
   when the value moved away from the baseline.
7. Aggregate: the attained fraction against the required fraction, unmet
   objectives past their due day, and the policy findings; the policy stands
   only when the finding list is empty.

## Pitfalls

- Reading a signed policy as an approved one. The question is which level
  signed it: a signature below the management that controls resources cannot
  commit the resource provision the policy states.
- Counting commitments instead of naming the missing ones. The count tells
  nobody which promise is absent, and the absent one is the actionable fact.
- Grading an objective on its raw value without its direction. The same
  measured number is met for an increase target and missed for a decrease
  one, and a direction-blind comparison silently inverts half the register.
- Setting a target at the current baseline so the objective is met on the
  day it is written. That is not a conservative objective; it is an
  unmeasurable one, and it has to be refused at validation.
- Treating progress above one as an error. Overshooting the target is normal
  and informative; what is a finding is progress below zero, which says the
  metric moved away from where the objective wanted it.
- Widening a required attainment to make an exact-equality case pass. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the requirement stays as specified.

## Behavior contract (gate 3)

The commitment completeness check, approval-level test, review-currency
arithmetic, objective validation, progress and attainment grading, regression
detection and overall policy verdict are exercised by the gate 3 contract
test:
scripts/test_q2007_safety_policy.py against
scripts/q2007_safety_policy_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_safety_policy.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

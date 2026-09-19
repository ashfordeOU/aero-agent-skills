---
name: q7004-acceptance-criteria
description: "Determine whether an item passed an ECSS thermal test by applying the criteria its own category carries. Use when the ECSS-Q-ST-70-04C evaluation clauses have to become a verdict: pick the criterion set for the category rather than one house list, judge presence criteria such as cracking or delamination apart from bounded ones such as mass loss or performance drift, return an unrecorded observation as undemonstrated instead of as a pass, surface any result the category never judged, and roll the criteria into accepted, rejected or not-demonstrated. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-test-acceptance-criteria, per-category-criterion-set, undemonstrated-criterion-handling, presence-versus-bounded-criterion, thermal-test-item-verdict."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-acceptance-criteria, thermal-test-acceptance-criteria, per-category-criterion-set, undemonstrated-criterion-handling, presence-versus-bounded-criterion, thermal-test-item-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Acceptance Criteria (space-systems/ecss/q7004-acceptance-criteria)

Use when the task is turning the ECSS-Q-ST-70-04C evaluation clauses into a
pass or fail for one item: which criteria that kind of item is actually
judged against, how each is decided, and what the answer is when an
observation was never taken.

## Domain quick reference

- Acceptance is a set, not a rule, and the set follows the category. A
  bonded item judged on cracking alone passes with an open bond line; an
  optical item judged on mass alone passes while it has gone hazy.
- Criteria come in two shapes and they are decided differently. A presence
  criterion is binary — a crack, a delamination, a functional failure is
  either there or it is not. A bounded criterion is a measurement against an
  allowance that is itself category-dependent.
- The same measurement can be a pass in one category and a failure in
  another. Quoting the number without the category it was judged in leaves
  the verdict unreproducible.
- An observation nobody took is not a pass. It comes back as undemonstrated,
  and the item verdict is undemonstrated too, which is a different state from
  accepted and from rejected.
- A rejection outranks an undemonstrated criterion. There is no point taking
  the missing observation once another criterion has already failed, but the
  gap still belongs in the report.
- An observation recorded for a criterion the category does not carry is a
  finding. Either the category is wrong or a real result went unjudged, and
  both cases need somebody to look.

## Workflow

1. Take the item category and read its criterion set from the policy. Refuse
   an unknown category rather than falling back to a default set.
2. For each criterion, find its observation. Absent means undemonstrated —
   never met, never failed.
3. Decide presence criteria on the boolean, and refuse a non-boolean rather
   than reading a free-text note as an absence.
4. Decide bounded criteria against the limit for this category, absorbing
   representation error so a value landing on the allowance is met.
5. Compare the observations supplied against the observations judged, and
   report the difference as unjudged results.
6. Roll up: rejected on any failure, undemonstrated on any gap, accepted only
   when every applicable criterion was actually shown to be met.

## Pitfalls

- Applying one criterion list to every item. It is the single defect that
  makes an acceptance statement look complete and prove nothing.
- Defaulting a missing observation to zero or to false. Both read as a pass
  and neither was measured; the report then claims evidence that does not
  exist.
- Judging a bounded criterion against the wrong category's allowance. The
  looser allowance always wins the argument and the tighter item ships.
- Testing a measurement against its allowance by bare arithmetic. A value
  constructed to sit on the allowance can land either side of it in the last
  place, so the comparison has to absorb that, not the allowance.
- Dropping the unjudged observations. They are the cheapest available
  evidence that the item was booked under the wrong category.
- Collapsing undemonstrated into rejected. It reads as a hardware problem
  when it is a records problem, and the retest that follows is the wrong
  retest.

## Behavior contract (gate 3)

The category criterion sets, presence and bounded criterion evaluation, the
undemonstrated branch, the category-dependent allowances with their boundary
handling, the unjudged-observation finding and the verdict roll-up are
exercised by the gate 3 contract test:
scripts/test_q7004_acceptance_criteria.py against
scripts/q7004_acceptance_criteria_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7004_acceptance_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

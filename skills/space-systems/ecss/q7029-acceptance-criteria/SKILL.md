---
name: q7029-acceptance-criteria
description: "Determine whether an offgassing test article passes under ECSS-Q-ST-70-29 by applying every acceptance criterion at once: the per-compound concentration limits, the caps that apply to a whole chemical class, the governing toxicity total, the odour verdict and the budget on unidentified peak area. Use when identification, quantification and assessment outputs must be combined into one accept or reject decision that names the governing criterion, and a compound with no published limit has to fail open rather than pass silently. Trigger: ecss, q-st-70-29, offgassing-acceptance-criteria, offgassing-compound-limit, offgassing-class-cap, offgassing-governing-criterion, offgassing-unidentified-budget, crew-compartment-offgassing."
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
  tags: [ecss, q-st-70-materials-scope, q7029-acceptance-criteria, offgassing-acceptance-criteria, offgassing-compound-limit, offgassing-class-cap, offgassing-governing-criterion, offgassing-unidentified-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Acceptance Criteria (space-systems/ecss/q7029-acceptance-criteria)

Use when the task is the acceptance step of ECSS-Q-ST-70-29: combining the
identification, quantification, toxicity and odour outputs of an offgassing
test into a single verdict on the article, together with the criterion that
governed it.

## Domain quick reference

- Acceptance is a conjunction, not an average. Every criterion has to be met;
  one exceeded compound is enough to reject the article regardless of how
  comfortable the other margins are. The interesting output is therefore not
  the verdict alone but which criterion governed it and by how much.
- Limits exist at two levels. A named compound has its own concentration
  limit, and the chemical class it belongs to has a cap on the sum of its
  members. A set of compounds each at ninety per cent of its own limit can
  still breach the class cap, which is precisely why the cap exists.
- Margin is reported as a utilisation, the ratio of the observed value to its
  limit. A utilisation at or below one meets the criterion; the governing
  criterion is the one with the highest utilisation, and it is the one to act
  on first.
- A reported compound with no limit in the applicable set is not a pass. It is
  an open item and it blocks acceptance until a limit is supplied or the
  compound is removed, because an absent limit is not a permissive one.
- The unidentified peak-area budget is an acceptance criterion in its own
  right. An article whose named products are all inside their limits but whose
  chromatogram is largely unaccounted for has not been shown to be acceptable.

## Workflow

1. Validate the limit sets: every compound limit and every class cap positive
   and finite, and every reported compound assigned to a class.
2. For each reported compound, compute its utilisation against its own limit.
   A compound with no limit produces an open item, never a utilisation of
   zero.
3. Sum the reported concentrations within each chemical class and compute the
   class utilisation against its cap.
4. Take the governing toxicity total from the toxicity assessment and compute
   its utilisation against the unit boundary.
5. Take the odour verdict as a pass or fail criterion; a panel that was not
   graded is an open item, not a pass.
6. Compute the unidentified-area utilisation against the declared budget.
7. Treat a utilisation sitting exactly on one as meeting the criterion,
   absorbing representation error with a named tolerance rather than by
   widening a limit.
8. Return the verdict, the governing criterion and its utilisation, every
   breached criterion and every open item.

## Pitfalls

- Stopping at the per-compound limits because each one passed. The class cap
  is the criterion that catches a family of compounds each individually
  comfortable, and it is the one most often skipped.
- Treating an unlimited compound as compliant. The absent limit is an open
  item; reading it as a pass converts missing information into an approval.
- Reporting only the verdict. Without the governing criterion and its
  utilisation, a reject gives the designer nothing to act on and a pass hides
  how little margin remained.
- Comparing the toxicity total against a per-compound limit. The total is
  already normalised to its boundary; dividing it again by a concentration
  limit produces a meaningless number that usually looks reassuring.
- Nudging a limit or a cap to absorb a value a hair above it. The tolerance in
  the comparison exists for representation error only; the limits themselves
  are fixed by the applicable set.

## Behavior contract (gate 3)

The limit-set validation, per-compound utilisation, class summation and cap
comparison, toxicity and odour criteria, unidentified-area budget, open-item
handling and governing-criterion selection are exercised by the gate 3
contract test: scripts/test_q7029_acceptance_criteria.py against
scripts/q7029_acceptance_criteria_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7029_acceptance_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q60-class-1-selection-general-requirements
description: "Assess whether a candidate Class 1 EEE part is ready to be taken to a procurement decision under ECSS-Q-ST-60C clause 4.2.1: declare every selection prerequisite as closed, open or not applicable, refuse a waiver on a blocking one, weight the prerequisites that still apply, compute a readiness index over them, list the blocking items left open, and name the single prerequisite worth closing next. Use when a project has to show the ground a Class 1 part choice stands on before the purchase order goes out. Trigger: ecss, q-st-60c-eee-selection-scope, class-1-part-selection-prerequisites, class-1-selection-readiness-index, component-control-plan-approval, declared-component-list-entry, class-1-procurement-authorization, blocking-selection-prerequisite."
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
  tags: [ecss, q-st-60c-eee-selection-scope, q60-class-1-selection-general-requirements, class-1-part-selection-prerequisites, class-1-selection-readiness-index, component-control-plan-approval, declared-component-list-entry, class-1-procurement-authorization, blocking-selection-prerequisite]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 1 Selection General Requirements (space-systems/ecss/q60-class-1-selection-general-requirements)

Use when the task is the overarching expectation of ECSS-Q-ST-60C
clause 4.2.1 -- what a project has to have settled before a Class 1
part choice is taken to a procurement decision, and how much of that
ground is actually in place.

## Domain quick reference

- A Class 1 selection decision is not a datasheet comparison. The
  choice is made against something: the environment the part will live
  in, the requirements it has to meet, the plan that governs how
  components are controlled, the list the choice is recorded on, and
  the quality level the build is aiming at. Those come first or the
  choice has nothing to be right about.
- The prerequisites do not hold equal parts of the decision and they do
  not cost the same to close, so each carries a weight. A readiness
  index over the weights says how much of the ground is in place; a
  bare count of open items does not.
- Some prerequisites are blocking. A selection taken without them is
  not an early decision, it is an unsupported one, and weight closed
  elsewhere does not buy it back. A blocking item still open is a stop,
  whatever the index reads.
- A prerequisite can genuinely not apply -- a part already sitting in a
  bonded store has no lead time to assess. That waiver needs a written
  justification and it leaves the denominator, so waiving an item never
  quietly improves the index. A blocking item cannot be waived at all.
- The useful output is not the verdict. It is the index, the blocking
  items still open, and the single next prerequisite worth closing --
  blocking first, then heaviest -- because that is the one that moves
  the decision furthest for the effort.
- The answer is a decision gate, not a part grade. It says whether the
  project may proceed to choose, not whether the candidate is good.

## Workflow

1. Name the candidate part and declare every prerequisite as closed,
   open or not applicable. An undeclared prerequisite is rejected
   rather than assumed open; silence is not a state.
2. Reject a waiver with no justification, and reject a waiver on a
   blocking prerequisite outright. The blocking set is the ground the
   decision stands on and it cannot be signed away.
3. Weight the prerequisites that still apply and compute the readiness
   index over them, so a light open item and a heavy one do not read
   the same.
4. List the blocking prerequisites still open. If there are any, the
   verdict is blocked whatever the index reads.
5. With no blocker open, compare the index with the threshold. An index
   sitting exactly on the threshold authorizes; the comparison absorbs
   representation error and the threshold is never lowered.
6. Close with the verdict, the waived items named in the open, and the
   single next prerequisite worth closing.

## Pitfalls

- Counting open items instead of weighting them. Eight prerequisites
  with one open is not one number -- an open mission environment and an
  open lead-time assessment are not the same distance from a decision.
- Letting a high index carry an open blocker. The index measures how
  much ground is in place; a blocking item measures whether there is
  ground at all, and no amount of the first substitutes for the second.
- Waiving a prerequisite to lift the index. A waiver removes the item
  from the numerator and the denominator together, so a real waiver is
  neutral; an item waived to make a number move is a defect.
- Treating an undeclared prerequisite as closed. An absent declaration
  is the commonest way a control plan goes missing from a selection
  file, so it is rejected rather than defaulted either way.
- Comparing the index with the threshold by bare arithmetic. The index
  is a quotient of two weight sums and the threshold is a decimal
  literal, so an index built to land exactly on the threshold can sit a
  few units in the last place below it; the comparison absorbs that
  while the threshold stays untouched.

## Behavior contract (gate 3)

The weight-table validation, state declaration, waiver rules, blocking
set, readiness index, threshold comparison, next-action ranking and
overall verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_1_selection_general_requirements.py against
scripts/q60_class_1_selection_general_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_1_selection_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

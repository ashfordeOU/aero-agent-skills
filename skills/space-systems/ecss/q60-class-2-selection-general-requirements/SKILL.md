---
name: q60-class-2-selection-general-requirements
description: "Assess whether a candidate Class 2 EEE part is ready to be taken to a procurement decision under clause 5.2.1 of ECSS-Q-ST-60C: declare every selection prerequisite as satisfied, open, tailored or not applicable, refuse tailoring on a blocking prerequisite and any tailoring without a rationale and an approval reference, weight what is still in force, credit a tailored item partially rather than fully, compute the readiness index, name the blocking items still open, and return the prerequisite worth closing next. Use when a project has to show the ground a Class 2 part choice stands on before the purchase order goes out. Trigger: ecss, q-st-60c, q60c2-selection-prerequisite-register, q60c2-selection-readiness-index, q60c2-selection-tailoring-credit, q60c2-blocking-selection-prerequisite."
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
  tags: [ecss, q-st-60c, q-st-60c-eee-class-2-selection-scope, q60-class-2-selection-general-requirements, q60c2-selection-prerequisite-register, q60c2-selection-readiness-index, q60c2-selection-tailoring-credit, q60c2-blocking-selection-prerequisite, q60c2-procurement-authorization-verdict, q60c2-next-prerequisite-to-close]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 2 Selection General Requirements (space-systems/ecss/q60-class-2-selection-general-requirements)

Use when the task is the overarching expectation of ECSS-Q-ST-60C clause 5.2.1:
what a project has to have settled before a Class 2 part choice is taken to a
procurement decision, and how much of that ground is actually in place.

## Domain quick reference

- A Class 2 selection decision is not a datasheet comparison. The choice is made
  against something: the environment the part will live in, the requirements it
  has to meet, the plan that governs how components are controlled, the list the
  choice is recorded on, and the quality level the build is aiming at. Those
  come first or the choice has nothing to be right about.
- The prerequisites do not hold equal parts of the decision and they do not cost
  the same to close, so each carries a weight. A readiness index over the
  weights says how much of the ground is in place; a bare count of open items
  does not.
- Class 2 admits a third state between met and open, and that is the whole
  difference from the stricter classes. A prerequisite can be tailored: met in a
  reduced form, against a written rationale and a named approval. Tailoring is
  partial ground, so it earns partial credit and stays in the denominator. A
  register where tailoring scores full marks is a register that reads as
  finished while half of it was negotiated.
- The blocking set is narrow on a Class 2 programme and what is in it is not
  negotiable. A blocking prerequisite cannot be tailored and cannot be declared
  inapplicable; a selection taken without one is not an early decision, it is an
  unsupported one, and weight closed elsewhere does not buy it back.
- A prerequisite can genuinely not apply — a part already sitting in a bonded
  store has no lead time to assess. That needs a written justification and it
  leaves the denominator, so declaring an item inapplicable never quietly
  improves the index.
- The useful output is not the verdict. It is the index, the blocking items
  still open, the tailoring on the record, and the single next prerequisite
  worth closing — blocking first, then heaviest — because that is the one that
  moves the decision furthest for the effort.

## Workflow

1. Validate the weight table: every prerequisite carries a finite, strictly
   positive weight, and the table cannot omit a blocking prerequisite.
2. Take a declaration for every weighted prerequisite. An undeclared
   prerequisite is rejected rather than assumed open; silence is not a state.
3. Refuse the states the clause does not admit: tailoring on a blocking
   prerequisite, inapplicability on a blocking prerequisite, tailoring without
   both a rationale and an approval reference, and inapplicability without a
   justification.
4. Weight the prerequisites still in force and compute the readiness index over
   them, crediting a satisfied item in full, a tailored item partially and an
   open item not at all.
5. Name the blocking prerequisites still open. If there are any, the verdict is
   blocked whatever the index reads.
6. With no blocker open, compare the index with the threshold. An index sitting
   exactly on the threshold authorizes; the comparison absorbs representation
   error and the threshold is never lowered. Say in the verdict whether the
   authorization rests on tailoring.
7. Close with the verdict, the tailored and inapplicable items named in the
   open, and the single next prerequisite worth closing.

## Pitfalls

- Counting open items instead of weighting them. Nine prerequisites with one
  open is not one number — an open mission environment and an open lead-time
  assessment are not the same distance from a decision.
- Crediting a tailored prerequisite in full. Tailoring is the Class 2 relief and
  it is partial by construction; scoring it as met erases the record of what was
  reduced, which is the only thing that makes tailoring reviewable later.
- Tailoring a blocking prerequisite because the schedule is tight. The blocking
  set is the ground the decision stands on and it cannot be signed away, which
  is why the register refuses to express it rather than reporting it.
- Letting a high index carry an open blocker. The index measures how much ground
  is in place; a blocking item measures whether there is ground at all, and no
  amount of the first substitutes for the second.
- Declaring a prerequisite inapplicable to lift the index. A genuine
  inapplicability leaves the numerator and the denominator together and is
  neutral; an item declared inapplicable to make a number move is a defect.
- Comparing the index with the threshold by bare arithmetic. The index is a
  quotient of two weight sums and the threshold is a decimal literal, so an
  index built to land exactly on the threshold can sit a few units in the last
  place below it; the comparison absorbs that while the threshold stays
  untouched.

## Behavior contract (gate 3)

The weight-table validation, state declaration, refusal of tailoring and
inapplicability on a blocking prerequisite, evidence requirements on both,
partial tailoring credit, weighted readiness index, blocking set, threshold
comparison, next-action ranking and overall verdict are exercised by the gate 3
contract test:
`scripts/test_q60_class_2_selection_general_requirements.py` against
`scripts/q60_class_2_selection_general_requirements_logic.py` (stdlib unittest,
offline). Run:
`python3 scripts/test_q60_class_2_selection_general_requirements.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

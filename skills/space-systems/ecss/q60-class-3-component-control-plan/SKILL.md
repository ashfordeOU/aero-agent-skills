---
name: q60-class-3-component-control-plan
description: "Prepare and grade the clause-by-clause compliance matrix a class 3 component control plan owes under ECSS-Q-ST-60C clause 6.1.2.2: order the applicable clauses numerically so 6.1.10 follows 6.1.9, refuse a row naming no readable clause or one outside the declared scope, require an implementing reference behind a stated compliance, a justification behind every departure and a customer agreement behind every non-compliance, name each clause left unanswered or answered twice with different states, judge completeness against its floor under a named tolerance, and raise a departure-share advisory. Use when a drafted class 3 plan has to become a submittable matrix. Trigger: ecss, q-st-60c-clause-6-1-2-2, class-3-plan-compliance-matrix, compliance-matrix-clause-ordering, unagreed-non-compliance-statement, matrix-completeness-floor, plan-departure-share-ceiling."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q60-class-3-component-control-plan, q-st-60c-clause-6-1-2-2, class-3-plan-compliance-matrix, compliance-matrix-clause-ordering, unagreed-non-compliance-statement, matrix-completeness-floor, plan-departure-share-ceiling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 3 — Component Control Plan Compliance Matrix (space-systems/ecss/q60-class-3-component-control-plan)

Use when the task is clause 6.1.2.2 of ECSS-Q-ST-60C: preparing the compliance
matrix a class 3 component control plan carries against the clauses of the
standard. This leaf turns a drafted matrix into a submittable one, or into the
list of rows that stop it being submitted.

## Domain quick reference

- Clause identifiers are numbers at every level, not text. Sorted as text,
  6.1.10 lands between 6.1.1 and 6.1.2 and a reviewer reads the matrix in an
  order the standard does not have.
- A matrix row is an answer, and an answer has a reference behind it. A row
  claiming compliance and pointing at no section of the plan asserts the state
  rather than showing where it was met.
- Every departure owes a reason in the row, not in a covering letter. A
  deviation, a non-compliance and a clause declared inapplicable are all
  departures, and each one is read by somebody who was not in the room.
- A clause declared inapplicable is the cheapest row to write and the easiest
  to get wrong. It needs a reason on the face of the matrix; it does not need
  an implementing reference, because nothing is being implemented.
- A non-compliance is not the project's to state alone. Without a recorded
  customer agreement the matrix cannot be submitted at all, which is a harder
  block than a clause the drafter has not reached yet.
- One clause answered twice with different states is worse than a clause
  answered once badly. The matrix contradicts itself and neither row can be
  relied on, so the clause counts as unanswered.
- A heavy departure share is an advisory, not a defect. Class 3 is allowed to
  depart; a plan departing nearly everywhere is a different plan, and the
  reviewer should see that as a shape rather than as a row-level error.

## Workflow

1. Put the declared applicable clauses into numeric clause order, rejecting a
   malformed or repeated identifier.
2. Group the matrix rows under the clause each answers, keeping rows that name
   no readable clause visible rather than dropping them.
3. Test each row: a readable clause inside the declared scope, a stated
   compliance state, an implementing reference behind a stated compliance, a
   justification behind every departure and a customer agreement behind every
   non-compliance.
4. Name every applicable clause the matrix never answers and every clause
   answered twice with different states.
5. Take completeness as the share of applicable clauses closed by a
   defect-free, unconflicted row and judge it against the floor under the
   stated tolerance.
6. Take the departure share over the rows that state anything and raise an
   advisory above the ceiling.
7. Return one disposition: matrix-ready, matrix-incomplete, or
   matrix-not-agreeable when a non-compliance carries no customer agreement.

## Pitfalls

- Sorting clause identifiers as text. The matrix reads plausibly and the tenth
  subclause sits four rows above where the reviewer expects it.
- Writing compliance with nothing behind it. The row states an intention, and
  at the review nobody can find the procedure it claims to implement.
- Putting the justification in the covering letter. The matrix is read on its
  own, and a departure with no reason in the row reads as an oversight.
- Declaring a clause inapplicable without saying why. It is the row most often
  right and the row most often used to make a subject disappear.
- Submitting a non-compliance the customer never agreed. The plan cannot be
  accepted, and the finding arrives after the procurement has started.
- Letting two rows state different things about one clause. Counting either of
  them as coverage makes a self-contradicting matrix read as complete.
- Promoting a heavy departure share into a row-level defect. The departures may
  each be sound, and burying the shape hides the rows that are actually wrong.

## Behavior contract (gate 3)

The numeric clause ordering, row-to-clause grouping, per-row defect tests, the
unanswered and conflicting clause lists, the unagreed non-compliance list,
matrix completeness against its floor, the departure share advisory and the
matrix disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_3_component_control_plan.py against
scripts/q60_class_3_component_control_plan_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_component_control_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

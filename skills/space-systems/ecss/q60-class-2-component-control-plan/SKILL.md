---
name: q60-class-2-component-control-plan
description: "Prepare and grade the compliance matrix a reliability Class 2 component control plan is assessed through under ECSS-Q-ST-60C clause 5.1.2.2: refuse a row with no identifier, clause reference or status, reject a clause outside the applicable set and a second row against one already answered, read a deviation with no justification or no approved disposition as open, treat an unjustified non-applicability as an unanswered clause, and return the weighted clause row coverage beside the compliance index. Use when a drafted plan has to become a clause-by-clause verdict. Trigger: ecss, q-st-60c-clause-5-1-2-2, reliability-class-2-component-control-plan, component-control-plan-compliance-matrix, compliance-matrix-clause-row-coverage, compliance-matrix-deviation-justification, compliance-matrix-tailoring-approval."
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
  tags: [ecss, q-st-60-eee-component-selection-scope, q60-class-2-component-control-plan, reliability-class-2-component-control-plan, component-control-plan-compliance-matrix, compliance-matrix-clause-row-coverage, compliance-matrix-deviation-justification, compliance-matrix-tailoring-approval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components -- Class 2 Component Control Plan Matrix (space-systems/ecss/q60-class-2-component-control-plan)

Use when the task is the clause 5.1.2.2 preparation question of
ECSS-Q-ST-60C at reliability Class 2: a component control plan has been
drafted, and what has to be produced or assessed is its compliance
matrix against the clauses of the standard, clause by clause.

## Domain quick reference

- The matrix is the plan's index of answers, not a contents page. Each
  applicable clause gets one row, that row carries a status, and the
  status is only believed when the row carries what the status obliges.
- A status has obligations attached to it. Claiming compliance obliges
  an evidence reference, because a claim with nothing behind it is a
  restatement of the clause. Claiming anything short of compliance
  obliges a justification and an approved disposition, because a
  deviation nobody agreed is not a deviation, it is a gap.
- Non-applicability is the most abused status in the matrix. A clause
  tailored out with a rationale and an approval is legitimate tailoring
  and leaves the grading entirely; one asserted with a blank rationale
  is an unanswered clause wearing a status, and is read that way.
- Coverage and compliance are two different numbers and both are needed.
  Coverage says how much of the applicable clause set carries an answer
  at all; the index says how good those answers are. A matrix can cover
  everything at half credit, or answer three clauses perfectly and leave
  the rest blank, and one number alone hides each case.
- Clauses do not weigh the same, so both figures are weighted. A weight
  is the programme's own statement of which clauses decide whether parts
  are controlled, and it keeps a row count from standing in for it.
- Tailoring leaves both sides of the index. Crediting a tailored clause
  flatters the plan and penalising it punishes legitimate tailoring, so
  an accepted non-applicability is removed from numerator and
  denominator together and reported separately.
- A row against a clause the matrix never declared applicable is not a
  bonus. It is evidence the applicable set and the matrix were built
  from different baselines, which is worth finding before issue.

## Workflow

1. Validate the applicable clause set: every reference is a dotted
   numeric path, every weight is strictly positive, and no clause is
   declared twice. An empty set is refused rather than graded.
2. Validate and dispose of each row. A row missing an identifier, a
   clause or a status cannot be read at all and stops there; a duplicate
   row identifier is a data error and is refused outright.
3. Refuse a malformed clause reference, an unrecognised status, a row
   against a clause outside the applicable set, and a second row against
   a clause already answered.
4. Apply the status obligations in severity order: justification first,
   then approval, then evidence, so the strongest missing item is the
   one the finding names.
5. Take the clause row coverage as the weighted share of applicable
   clauses carrying an accepted row, and name every clause left
   unanswered.
6. Take the compliance index as the weighted credit of the answered
   clauses over the clauses that still apply, removing accepted
   non-applicability from both sides, and refuse a matrix that tailored
   every clause out.
7. Compare both figures with their required levels, absorbing
   representation error at the boundary with a named tolerance, and
   close on one verdict: matrix ready for issue, or matrix incomplete,
   with the findings ranked most severe first.

## Pitfalls

- Filing a matrix whose rows restate the clauses. A row that says the
  plan complies and points at nothing is the defect the evidence
  reference exists to catch, and it passes any check that counts rows.
- Letting an unjustified non-applicability leave the grading. That is
  the cheapest way to reach a high index, and it is why the rationale
  and the approval are tested before the clause is removed.
- Reporting coverage alone. Every clause answered at partial compliance
  gives full coverage and a half index, and the coverage figure on its
  own reads as a finished matrix.
- Counting an unanswered clause out of the denominator. A clause with no
  row is not tailored out; it scores zero and stays in, or the index
  rises every time a row is deleted.
- Grading the clause count rather than the weights. A matrix answering
  every minor clause and none of the decisive ones counts well and
  controls nothing.

## Behavior contract (gate 3)

The applicable clause validation, clause reference and status
validation, row completeness and disposition, the status obligation
order, the weighted clause row coverage, the weighted compliance index
with tailoring removed from both sides, the open deviation list and the
matrix verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_2_component_control_plan.py against
scripts/q60_class_2_component_control_plan_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_component_control_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e10-design-general
description: "Use when conduct and document a product's design against its allocated Technical Requirements Specification under ECSS-E-ST-10C clause 5.4.1.1: confirm every allocated requirement is covered by at least one design definition item, confirm every design item traces back to a known requirement, and confirm every design decision records the alternatives considered, the option selected and the rationale for selecting it, then decide whether the product's design is complete for the assessment. Trigger: ecss, e-st-10-system-scope, design-definition, design-decision, technical-requirements-specification, requirement-coverage, design-traceability, design-rationale."
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
  tags: [ecss, e-st-10-system-scope, design-definition, design-decision, requirement-coverage, design-traceability, design-rationale]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — General Design Conduct (space-systems/ecss/e10-design-general)

Use when the task is to conduct a product's design so that it meets
its allocated Technical Requirements Specification under ECSS-E-ST-10C
clause 5.4.1.1, and to show that both the design definition and the
design decisions taken along the way are documented per product.

## Domain quick reference

- Coverage runs in two directions and each direction catches a
  different defect. Requirement-to-design coverage finds an allocated
  requirement that no design item implements. Design-to-requirement
  traceability finds a design item that implements nothing in the
  specification -- unrequested design work. Neither check substitutes
  for the other.
- A design item that references a requirement identifier outside the
  product's known set is a third, separate defect: not untraced, but
  traced to something that is not in this product's specification.
- A design decision is closed only when an alternative has been
  selected *and* a rationale is on record. A selection without a
  reason leaves the decision open, because the record exists to let a
  later reviewer re-derive the choice, not merely to name it.
- Every decision must carry at least one requirement identifier. A
  decision no requirement drove cannot be re-assessed when the
  specification changes, so it is flagged as untraceable independently
  of whether it is closed.
- Even a decision with one viable option records that option as its
  sole alternative -- the record is the evidence that the option space
  was examined, and an empty alternative list is an input error.
- Assessment is per product. Programme-wide requirement, design item
  and decision lists are filtered to the product under review before
  any check runs, so a requirement covered on a sibling product does
  not count as covered here.
- The design is complete only when all three finding categories are
  empty; strength in one never offsets a gap in another.

## Workflow

1. Filter the programme requirement, design item and design decision
   lists down to the product under assessment.
2. For each allocated requirement, confirm at least one design item
   references it; record an uncovered requirement otherwise.
3. For each design item, confirm it references at least one
   requirement, and that every identifier it references is in the
   product's known requirement set.
4. For each design decision, confirm it names the alternatives
   considered, records the selected alternative and its rationale, and
   traces to at least one requirement.
5. Aggregate the uncovered-requirement, unallocated-design-item and
   decision findings; the design is complete only when all are empty.

## Pitfalls

- Checking requirement coverage alone and calling the design
  traceable. That leaves design work no requirement asked for entirely
  invisible, which is the growth path for unqualified scope.
- Accepting a design item whose requirement reference is a typo. The
  item looks traced; only cross-checking each identifier against the
  product's known requirement set reveals it points nowhere.
- Closing a design decision on the strength of a selected alternative
  with no rationale recorded. The choice cannot be re-derived at the
  next review, so the decision is still open.
- Recording a decision with no alternatives because only one option
  was ever viable. The sole option is itself the alternative list, and
  its absence removes the evidence that the space was examined.
- Assessing against the programme-wide requirement list instead of the
  product's allocation, which reports requirements belonging to other
  products as uncovered and hides the ones that matter.

## Behavior contract (gate 3)

The decision-status, decision-violation, requirement-coverage,
design-item traceability and per-product aggregation logic is exercised
by the gate 3 contract test: scripts/test_e10_design_general.py against
scripts/e10_design_general_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_design_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q40-02-process-principles
description: "Define the hazard-analysis process for a space programme under ECSS-Q-40-02 and grade the definition: check the mandatory process elements are declared, that each analysis level carries a technique suited to that level rather than one borrowed from another, that the iterations are tied to the safety reviews so the analysis reaches the decisions it informs, that the documentation set leaves a hazard log traceable to requirements, and that update triggers keep it alive between reviews. Use when a hazard-analysis process is written or audited. Trigger: ecss, q-st-40-02, hazard-analysis-process-definition, hazard-analysis-technique-selection, hazard-analysis-safety-review-integration, hazard-log-traceability, hazard-analysis-update-triggers."
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
  tags: [ecss, q-st-40-02-hazard-analysis, q-st-40-02, q40-02-process-principles, hazard-analysis-process-definition, hazard-analysis-technique-selection, hazard-analysis-safety-review-integration, hazard-log-traceability, hazard-analysis-update-triggers]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hazard Analysis — Process Principles (space-systems/ecss/q40-02-process-principles)

Use when the task is the opening clauses of ECSS-Q-40-02: the hazard-analysis
concept, its role in the safety programme, the process overview, how it is
implemented and documented, and how it meets the safety reviews. The subject is
the process definition, not any one analysis run through it.

Related but not the same: the ARP4761A functional hazard assessment and the
operating and support hazard analysis are techniques, and this leaf is what
selects and sequences techniques like them. Reach for those when the task is to
run one; reach for this when the task is to define or audit the process.

## Domain quick reference

- A process definition is not an activity log. It has mandatory elements —
  scope, levels, technique selection, inputs, iteration points, documentation,
  review integration, update triggers — and a definition short of one of them
  still produces analyses. It just does not produce the same one twice.
- Technique suits level. A fault tree answers a system question and a
  functional hazard analysis answers a functional one; swapping them produces
  work that is not wrong so much as unusable at the level it was asked for.
- A technique can legitimately serve two levels. A criticality analysis reads
  at system and at subsystem, so the check is suitability, not exclusivity.
- Iteration is the point. An analysis tied to one review is a snapshot, and the
  reviews it misses take their decisions on nothing.
- The operational level has its own techniques and its own timing. Declaring it
  and then running no iteration where the operational baseline settles leaves
  the operational hazards discovered after the baseline is fixed.
- The documentation set is what survives the programme. A hazard log with no
  traceability to requirements cannot say which requirement controls a hazard,
  which is the question the next reviewer asks first.
- Update triggers are what keep the analysis alive between reviews. Without a
  design-change and an anomaly trigger the process is a one-off with a plan.

## Workflow

1. Validate the definition: identity, declared elements, analysis levels,
   technique table, iteration reviews, documentation set and update triggers,
   all from the known vocabularies.
2. Name the mandatory process elements the definition does not declare.
3. Check each declared level has at least one technique and that every
   technique chosen for it suits that level; report techniques selected for a
   level the process never declared.
4. Check the iterations reach the mandatory reviews, that there are at least
   two of them, and that a declared operational level reaches acceptance.
5. Check the documentation set carries the report, the hazard log and the
   traceability, and call out a log left without traceability in its own right.
6. Check the update triggers cover design change and anomaly, plus operational
   change wherever the operational level is declared.
7. Compute the element score for tracking, and grade: non-conformant on a
   missing element, an unsuited technique or a documentation gap;
   conformant-with-gaps when only reviews or triggers are thin; conformant
   otherwise.

## Pitfalls

- Auditing the analyses instead of the process. Good analyses can come out of
  an undefined process once, and the second team gets nothing.
- Selecting techniques by familiarity. The level asks the question and the
  technique has to be able to answer that question.
- Treating a technique that serves two levels as a defect. Suitability is the
  test, not exclusive assignment.
- Tying every iteration to the design reviews and none to acceptance, so
  operational hazards arrive after the operational baseline is fixed.
- Committing to a hazard log with no traceability to requirements, so nothing
  can say which requirement controls which hazard.
- Leaving the update triggers implicit. The analysis then ages quietly between
  reviews and nobody owns the moment it stopped being true.
- Reducing the audit to one score. The score is for tracking; the grade turns
  on which kind of gap it is.

## Behavior contract (gate 3)

The process-definition validation, the mandatory element set, the level-to-
technique suitability table including shared techniques and undeclared levels,
the review-integration rules with the operational special case, the
documentation set with its traceability consequence, the update triggers, the
element score and the conformant / conformant-with-gaps / non-conformant grade
are exercised by the gate 3 contract test:
scripts/test_q40_02_process_principles.py against
scripts/q40_02_process_principles_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_02_process_principles.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

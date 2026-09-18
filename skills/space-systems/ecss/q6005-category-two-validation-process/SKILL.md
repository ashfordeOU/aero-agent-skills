---
name: q6005-category-two-validation-process
description: "Plan the category two validation steps that qualify a hybrid source with no approved production line for use on one programme, and grade how far they have run: order the sequence from applicability review and supplier survey through element procurement review, validation lot build, lot testing and destructive physical analysis to the programme authority agreement, catch a step started before its prerequisite finished, take the longest remaining chain rather than the sum of outstanding work, and report the earliest the sequence can finish against the programme need date. Use when an unapproved hybrid source must be validated in time, or a validation earned on another programme is offered here. Trigger: ecss, q-st-60-05, category-two-hybrid-validation, unapproved-hybrid-supplier, hybrid-validation-lot-build, hybrid-validation-critical-chain, programme-authority-agreement, hybrid-validation-step-ordering."
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
  tags: [ecss, q-st-60-hybrid-procurement-scope, q6005-category-two-validation-process, category-two-hybrid-validation, unapproved-hybrid-supplier, hybrid-validation-lot-build, hybrid-validation-critical-chain, programme-authority-agreement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Category-Two Validation Process (space-systems/ecss/q6005-category-two-validation-process)

Use when the task is the category-two validation of ECSS-Q-ST-60-05 clause
6.3 — a hybrid supplier whose production line holds no approval has to be
qualified for use on one named programme, and the questions are which steps
are owed, in what order, whether they were actually run in that order, and
whether the whole sequence can close before the programme needs the parts.

## Domain quick reference

- The process is a dependency graph, not a checklist. The applicability
  review opens the survey and the element-procurement review; the lot build
  waits on both the process-identification audit and the element review; the
  test, the destructive analysis, the report review and the authority
  agreement then run in line. Two branches mean two ways to be late and only
  one of them sets the finish date.
- Time to close is the longest remaining chain, not the sum of the
  outstanding work. Adding the remaining steps together overstates the
  schedule by everything that runs in parallel, which makes an achievable
  validation look impossible and hides the branch that is actually driving.
- Finishing a step that is not on the driving chain does not move the finish
  date. That is not a reason to skip it — it is a reason not to report it as
  schedule recovery.
- A step reported started or finished while something it depends on is
  unfinished is a process defect, not progress. The lot built before the
  element-procurement review closed is the classic one: the build is real,
  the validation it feeds is not.
- The validation belongs to the programme it was run for. A supplier
  validated on another programme is not carried over by that record; the
  process is run again against this programme's applicability.
- The verdict order matters: a failed step dominates, then an ordering
  defect, then progress. A sequence with a broken order can be "all
  complete" and still not be a validation.

## Workflow

1. Prove the step registry is usable: every prerequisite known, nothing
   waiting on itself, no cycle, every duration a positive whole number.
2. Validate the declared state of every step — all steps present, every
   status one of the four recognised ones.
3. Look for ordering defects across the whole graph before grading progress,
   naming each unmet prerequisite separately.
4. Work out what remains per step: nothing for a finished step, the nominal
   duration otherwise, or an explicit remaining-days figure for a step
   already under way.
5. Take the longest remaining chain through the graph, and recover the chain
   itself so the driving branch can be named rather than inferred.
6. Date that chain from the start date and take the whole-day margin against
   the programme need date.
7. Roll up the verdict and emit the findings: failures, ordering defects, a
   validation held for another programme, a negative margin, or a process
   that has not been opened.

## Pitfalls

- Summing the outstanding steps to get the time to close. The parallel
  branches are counted twice and the validation is declared impossible
  against a programme date it would have met.
- Treating a validation from another programme as reusable. It is evidence
  about the supplier, not a validation for this programme, and the
  applicability review is exactly the step that decides the difference.
- Grading progress before checking order. A process where the lot build ran
  ahead of the element-procurement review can show a high completion count
  while the evidence chain underneath it is broken.
- Reporting an off-chain completion as schedule recovery. It shortens
  nothing; the finish date only moves when the driving chain moves.
- Taking "all steps complete" as the verdict without looking at how they were
  ordered. Completion and validity are different questions and this clause
  asks both.

## Behavior contract (gate 3)

The registry validation and topological order, step-state validation,
ordering-defect detection, remaining-work model with overrides, longest
remaining chain and its recovery, completion dating, programme margin,
cross-programme reuse test and verdict roll-up are exercised by the gate 3
contract test: scripts/test_q6005_category_two_validation_process.py against
scripts/q6005_category_two_validation_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_category_two_validation_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

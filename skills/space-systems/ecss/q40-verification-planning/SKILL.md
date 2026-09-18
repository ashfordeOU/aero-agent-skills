---
name: q40-verification-planning
description: "Plan safety verification under ECSS-Q-ST-40C: assign a method to each safety requirement — test, analysis, inspection, review of design, similarity — on the rule that rising severity withdraws the weaker methods, then check the assignment is supportable (analysis of a catastrophic requirement needs correlated test data behind it, similarity needs a named baseline item), that every requirement has a planned verification report, and that closure is planned no later than the review milestone its severity allows. Use when a safety verification plan is drafted or reviewed. Trigger: ecss, q-st-40c, safety-verification-planning, safety-verification-method-assignment, safety-verification-report-planning, safety-closure-milestone, verification-method-admissibility."
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
  tags: [ecss, q-st-40c-safety, q-st-40c, q40-verification-planning, safety-verification-planning, safety-verification-method-assignment, safety-verification-report-planning, safety-closure-milestone, verification-method-admissibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Safety — Verification Planning (space-systems/ecss/q40-verification-planning)

Use when the task is the verification engineering and planning clause of
ECSS-Q-ST-40C together with its methods and reports clause: a set of safety
requirements exists, each needs a method, and the plan has to say how and by
when each one closes.

## Domain quick reference

- Severity decides the admissible method set, not convenience. The weaker
  methods are withdrawn as severity rises, so a catastrophic requirement is
  carried by test or by analysis and by nothing else. The point is that a
  demonstration by similarity cannot underwrite a consequence nobody survives.
- Admissible is not the same as supportable. Analysis is admissible for a
  catastrophic requirement, but analysis standing alone is a model; it needs
  correlated test data behind it before it carries that severity.
- Similarity is an argument about a specific other item. Without a named
  baseline it is an assertion, and the reviewer has nothing to go and check.
- A verification with no planned report is an activity, not a verification.
  Nothing downstream can cite it and the hazard close-out has nothing to point
  at, so the missing report is a planning defect in its own right.
- Closure has a deadline set by severity, not by the schedule. A catastrophic
  requirement planned to close after qualification review is planned to close
  too late whatever its method, because the decision it feeds happens first.
- The method mix is worth reading as a whole. A plan carried overwhelmingly by
  review of design and inspection has usually assigned methods by cost.

## Workflow

1. Validate each requirement: identity, severity, method, planned closure
   milestone and report flag all present and from the known sets.
2. Look up the admissible method set for the severity and check the assigned
   method is in it.
3. Check the supporting conditions: correlated test data behind an analysis at
   catastrophic severity, a named baseline behind similarity.
4. Check a verification report is planned for the requirement.
5. Compare the planned closure milestone against the latest the severity
   allows, by position in the review sequence rather than by name.
6. Collect every finding per requirement rather than stopping at the first.
7. Roll up: method mix, coverage ratio, the open requirements, and whether any
   open requirement is catastrophic or critical.
8. Close: rejected when a severe requirement is open, acceptable-with-actions
   when only lesser ones are, acceptable otherwise.

## Pitfalls

- Assigning the method before the severity. The severity is the input to the
  choice; reading it afterwards only tells you the choice was wrong.
- Accepting an analysis at catastrophic severity because analysis is on the
  admissible list. The list says which methods may be used, not which
  evidence makes this one stand up.
- Recording similarity against a product family rather than an item. A family
  has no test history; a specific unit does.
- Treating the verification report as paperwork that follows. Nothing can cite
  an unreported verification, so the close-out stalls on it later.
- Reading closure milestones as names rather than as positions in a sequence.
  The comparison is ordinal and a plan that slips one review has slipped.
- Stopping at the first finding on a requirement, so the plan comes back three
  times having fixed one defect each round.
- Judging the plan by the coverage ratio alone. One open catastrophic
  requirement rejects a plan that is otherwise at ninety-nine percent.

## Behavior contract (gate 3)

The requirement validation, severity-to-method admissibility table, supporting
conditions for analysis and similarity, report planning check, closure
milestone ordering, coverage ratio and the acceptable / acceptable-with-actions
/ rejected disposition are exercised by the gate 3 contract test:
scripts/test_q40_verification_planning.py against
scripts/q40_verification_planning_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_verification_planning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

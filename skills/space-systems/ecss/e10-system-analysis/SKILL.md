---
name: e10-system-analysis
description: "Use when scoping and scheduling ECSS-E-ST-10C system analyses for a space project: classify a required system analysis as mission, functional, interface, environmental, or operational, determine which analysis types a given project phase requires, verify each analysis definition carries a non-empty objective and defined outputs, and check whether an analysis is scheduled early enough to feed the phase that first requires it. Trigger: ecss, e-st-10-system-scope, system-analysis, mission-analysis, functional-analysis, interface-analysis, environmental-analysis, operational-analysis, analysis-scheduling."
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
  tags: [ecss, e-st-10-system-scope, system-analysis, mission-analysis, functional-analysis, interface-analysis, environmental-analysis, operational-analysis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — System Analysis Scope and Schedule (space-systems/ecss/e10-system-analysis)

Use when the task is scoping and scheduling the system analyses required
by ECSS-E-ST-10C clause 5.3.1 -- categorizing each analysis by type
(mission, functional, interface, environmental, operational), confirming
its objective and outputs are defined, and checking that it is scheduled
early enough to feed the project phase that depends on it.

## Domain quick reference

- Clause 5.3.1 groups system analyses into five types, each with a
  distinct object of study: mission (does the concept meet the mission
  need across its operational scenarios), functional (do the allocated
  functions cover the required behavior without gaps or conflicts),
  interface (are the boundaries between elements/segments consistent and
  complete), environmental (does the design tolerate the induced and
  natural environments it will encounter), and operational (do the
  operations concept and procedures actually achieve the mission in the
  intended timeline). Every analysis instance is categorized into exactly
  one of these five types before it is scoped further.
- A project phase (feasibility, preliminary design, detailed design,
  verification) accumulates a required set of analysis types: feasibility
  needs at minimum a mission analysis; preliminary design adds functional
  and environmental; detailed design and verification add interface and
  operational. An analysis type is not "done" once scoped at its earliest
  phase -- it stays required through every later phase, refined as the
  design matures.
- Scoping an analysis means recording, at minimum, its objective (why the
  analysis is being run) and its defined outputs (what artifact or
  decision it produces); an analysis with either left blank has not
  actually been scoped, regardless of what type it is labeled.
- Scheduling an analysis means assigning it to the phase by which it must
  be complete. Each analysis type has an earliest phase that first
  requires it (e.g. mission analysis is required from feasibility
  onward); an analysis scheduled to complete later than that earliest
  phase cannot feed the decision it exists to support, and is a
  scheduling violation even if its objective and outputs are otherwise
  well defined.

## Workflow

1. For each candidate system analysis, categorize it as mission,
   functional, interface, environmental, or operational. Reject an
   unrecognized analysis type before it enters the review.
2. Confirm the analysis records a non-empty objective and a non-empty
   list of outputs; flag either omission independently -- one being
   present does not excuse the other being missing.
3. Confirm the analysis has a scheduled phase on record; flag its
   absence. If a scheduled phase is recorded, it must be one of the
   project's recognized phases -- reject an unrecognized phase value.
4. Compare the analysis's scheduled phase against the earliest phase
   that requires its type; flag the analysis if it is scheduled later
   than that earliest phase.
5. For the project's current phase, determine the full set of analysis
   types required by that phase (cumulative from all earlier phases)
   and compare it against the set of types actually scoped; flag any
   required type with no corresponding analysis on record.
6. Aggregate the per-analysis findings and the missing-analysis-type
   findings; the project's system analysis planning is not compliant
   until both are empty.

## Pitfalls

- Treating a required analysis type as satisfied because *an* analysis
  of that type exists somewhere in the plan, without checking that its
  objective and outputs are actually filled in -- an analysis entry
  with a type label and nothing else is not a scoped analysis.
- Scheduling an analysis for the same phase whose decision it is meant
  to inform rather than before it -- an analysis type's earliest
  required phase is the phase it must feed, so a completion date at
  that same phase is already too late for this leaf's check, which
  flags anything scheduled *later* than the earliest required phase and
  relies on programme scheduling discipline to place it appropriately
  ahead of that phase's start.
- Assuming a later project phase inherits compliance from an earlier one
  -- a required analysis type must still be checked at every later
  phase, since a design change can invalidate an analysis scoped
  earlier even though the type was originally satisfied.
- Silently dropping an analysis with an unrecognized type or an
  unrecognized scheduled phase instead of rejecting it -- a typo in
  either field should surface as an error, not disappear from the
  review.

## Behavior contract (gate 3)

The analysis-type categorization, objective/output completeness,
scheduling, and phase-coverage logic is exercised by the gate 3 contract
test: scripts/test_e10_system_analysis.py against
scripts/e10_system_analysis_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_system_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2040-device-validation-plan-consolidation
description: "Prepare the consolidated device validation plan ECSS-E-ST-20-40C 5.6.4 asks for at the end of layout: map every user need onto activities that demonstrate it, refuse an environment unable to demonstrate that kind of need such as endurance attempted on a bench, confirm the rigs and models each activity depends on will exist, and order the campaign so nothing runs before its prerequisite and no dependency loop survives. Use when the validation plan has to be finalised before the finished device is proven. Trigger: ecss, e-st-20-electrical-scope, device-validation-plan-consolidation, validation-environment-suitability, validation-need-coverage, validation-resource-availability, validation-schedule-dependency-loop, need-to-activity-traceability."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-validation-plan-consolidation, device-validation-plan-consolidation, validation-environment-suitability, validation-need-coverage, validation-resource-availability, validation-schedule-dependency-loop, need-to-activity-traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Layout — Validation Plan Consolidation (space-systems/ecss/e2040-device-validation-plan-consolidation)

Use when the task is the consolidation duty of ECSS-E-ST-20-40C 5.6.4 --
fixing, before the finished device exists, how each thing the device was
procured to do will actually be demonstrated on hardware.

## Domain quick reference

- Validation asks a different question from verification. Verification
  asks whether the device was built to the specification; validation asks
  whether the finished device does the job it was procured for, so the
  plan is organised around needs rather than around requirements.
- A need with no activity is the gap the plan exists to close, and it is
  invisible while the activity list is read on its own, because every
  activity in that list is perfectly legitimate.
- The environment decides what an activity can demonstrate. Endurance
  needs a system or flight-representative setup; a performance envelope
  needs at least a board; an operational procedure needs a system. Only a
  functional use case can be demonstrated anywhere.
- An activity in an environment that cannot demonstrate its need adds
  nothing to coverage however carefully it is written, so it is excluded
  from the numerator rather than counted and flagged.
- Resources are part of the plan. An activity depending on a rig that
  will not be built is a plan on paper and reads as complete.
- Order has to be executable. An activity sharing a slot with its
  prerequisite cannot run after it, and a dependency loop is the one
  defect that survives every per-activity check -- each activity in the
  loop looks perfectly ordered against its own predecessor.
- Activities merely stuck behind a loop are not in it. The finding names
  the ones that have to be re-ordered, not everything downstream.

## Workflow

1. Resolve the needs: unique identifiers and a recognised need kind.
2. Resolve the activities: unique identifiers, the need each
   demonstrates, a folded environment, the resources each consumes, the
   prerequisites and the schedule slot. Refuse a self-dependency, a
   repeated dependency and a negative slot.
3. Report activities pointing at a need the plan does not carry.
4. Test each activity's environment against its need kind and report the
   ones that cannot demonstrate it, naming the environments that could.
5. Report every resource an activity consumes that the plan does not list
   as available.
6. Report prerequisites outside the plan, and activities scheduled at or
   before something they depend on.
7. Detect dependency loops and name only the activities inside them.
8. Report needs left with no demonstrable activity, then compare
   consolidation coverage with the goal, absorbing an exact landing.

## Pitfalls

- Counting an activity as coverage because it names the need. If the
  environment cannot demonstrate that kind of need, the activity will run
  and prove nothing.
- Demonstrating endurance on a bench. The activity reads sensibly line by
  line and the campaign discovers the gap when the hardware is built.
- Reading the activity list instead of the need list. Every activity can
  be sound while a whole need has nobody assigned to it.
- Checking order only pairwise. Two activities can each be scheduled
  correctly against the other and still form a loop that never starts.
- Listing everything downstream of a loop as looped. The report then
  buries the two activities that actually have to be re-ordered.
- Failing a plan whose coverage lands exactly on its goal. A three-in-four
  division can sit a unit in the last place below the figure it is
  compared with.

## Behavior contract (gate 3)

The need-kind and environment folding, environment-suitability rule,
resource availability check, prerequisite ordering, dependency-loop
detection scoped to loop members and the coverage comparison with exact
goal landings are exercised by the gate 3 contract test:
scripts/test_e2040_device_validation_plan_consolidation.py against
scripts/e2040_device_validation_plan_consolidation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_validation_plan_consolidation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

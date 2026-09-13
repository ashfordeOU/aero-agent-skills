---
name: e2007-electromagnetic-effects-verification-plan
description: "Use when draft, review or audit the electromagnetic-effects verification-plan anchored at ECSS-E-ST-20-07C clause 5.1.2: confirm the plan carries every mandatory section, assign each electromagnetic-compatibility requirement family an admissible verification-method, reject a method substitution that records no tailoring-justification, require every measured activity to name its facility and its equipment-under-test configuration, order each activity against the plan baseline and its closure-milestone, size the activity schedule against the contingency window, and compute requirement-coverage before the plan is released for the compatibility campaign. Trigger: ecss, e-st-20-07c, electromagnetic-effects-verification-plan, emc-verification-planning, verification-method-assignment, tailoring-justification, equipment-under-test-configuration, closure-milestone-ordering, requirement-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-electromagnetic-effects-verification-plan, emc-verification-planning, verification-method-assignment, equipment-under-test-configuration, closure-milestone-ordering, requirement-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Electromagnetic Effects Verification Plan (space-systems/ecss/e2007-electromagnetic-effects-verification-plan)

Use when the task is the planning document of ECSS-E-ST-20-07C clause
5.1.2 -- the plan that directs every activity used to show
electromagnetic effects compliance, from the requirement-list through
the verification-method assigned to each requirement to the facility,
configuration and schedule in which the activity is run.

## Domain quick reference

- The plan is the directing document, not a results record: it fixes
  what is verified (the electromagnetic-compatibility requirement-list),
  how each requirement is closed (the assigned verification-method),
  where and on what hardware (facility plus equipment-under-test
  configuration), when (activity dates against programme milestones),
  and by whom (responsibility assignment). A plan missing any of those
  sections cannot direct the campaign and is not releasable.
- Verification-method admissibility is family-dependent. Emission and
  susceptibility families (radiated-emission, conducted-emission,
  radiated-susceptibility, conducted-susceptibility) are measured
  behaviours and are closed on hardware. Magnetic-moment,
  electrostatic-discharge, electromagnetic-radiation-hazard and
  lightning-protection families admit a modelled demonstration.
  Bonding-and-grounding is largely a build-state check and admits
  inspection or review-of-design. Any other pairing is a tailoring:
  admissible only when the plan records the justification for it.
- An activity carries a closure-milestone (SRR, PDR, CDR, QR, AR). The
  activity must start on or after the plan baseline date and must end
  on or before the date of the milestone at which its requirement is
  declared closed. An activity whose milestone carries no date in the
  plan schedule is unschedulable and is itself a finding.
- Requirement-coverage is the fraction of the requirement-list that at
  least one planned activity addresses in the matching family. An
  activity pointing at a requirement outside the list is an orphan; an
  activity whose family differs from its requirement's family does not
  count as coverage, because it exercises a different behaviour.
- Schedule feasibility compares the summed activity durations, inflated
  by the agreed schedule contingency, against the campaign window. A
  window exactly consumed is feasible; absorb the binary-representation
  error of the summed durations rather than widening the window.

## Workflow

1. Parse the plan outline and list the mandatory sections that are
   absent. Reject an outline that lists the same section twice -- that
   is a table-of-contents defect, not a coverage question.
2. Normalize every planned activity: identifier, requirement pointer,
   requirement family, verification-method, planned start date,
   duration in days, closure-milestone, facility and
   equipment-under-test configuration. Reject a malformed activity
   (absent key, non-positive or non-finite duration, unparseable date,
   unknown method, family or milestone) before it enters the assessment.
3. Check each assignment for admissibility against its family; when the
   method is outside the admissible set, accept it only if the activity
   records a tailoring-justification, otherwise raise the finding.
4. For every activity closed by measurement, confirm a named facility
   and a named equipment-under-test configuration; an unnamed facility
   or configuration makes the activity unrepeatable.
5. Build the coverage map from requirement-list to activities: report
   uncovered requirements, orphan activities, and activities whose
   family contradicts the family of the requirement they point at.
6. Order the schedule: flag an activity starting before the plan
   baseline, an activity ending after its closure-milestone date, and a
   closure-milestone with no date on record.
7. Sum the durations, apply the contingency fraction and compare with
   the campaign window; flag an infeasible schedule.
8. Aggregate. The plan is releasable only when the findings list is
   empty -- coverage alone is not release readiness.

## Pitfalls

- Reading a high coverage fraction as a releasable plan: a plan can
  cover every requirement and still be undirectable because the
  facility, the configuration or the closure-milestone date is absent.
- Accepting review-of-design or similarity against an emission or
  susceptibility family because the hardware schedule is tight -- that
  substitution is a tailoring and is only admissible with the
  justification recorded in the plan, not asserted in a review.
- Counting an activity as coverage when its family differs from the
  family of the requirement it points at; a conducted-emission run does
  not close a radiated-emission requirement.
- Treating an undated closure-milestone as harmless because the
  activity dates look reasonable -- without the milestone date nothing
  constrains the activity end, and the ordering check silently passes.
- Widening the campaign window so an exactly-consumed schedule reads
  feasible: the summed durations may land a few units in the last place
  above the window purely through binary representation. Absorb that in
  the comparison, never in the window.

## Behavior contract (gate 3)

The section-completeness, method-admissibility, activity-validation,
schedule-ordering, schedule-feasibility and requirement-coverage logic
is exercised by the gate 3 contract test:
scripts/test_e2007_electromagnetic_effects_verification_plan.py against
scripts/e2007_electromagnetic_effects_verification_plan_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_electromagnetic_effects_verification_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

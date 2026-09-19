---
name: e2040-preliminary-verification-validation-plans
description: "Assess the preliminary verification and validation strategy ECSS-E-ST-20-40C clause 5.2.4 asks for while the device is still being defined: give every requirement a provisional method and an article to run it on, keep that article inside the model set the development plan declares, give every validation objective an activity deep enough to answer it, keep validation objectives from being restated as verification lines, and report the maturity the two plans reach against the target the phase gate sets. Use when preliminary verification and validation plans are drafted or reviewed in the definition phase. Trigger: ecss, e-st-20-40-device-scope, preliminary-verification-validation-plans, provisional-verification-method, verification-model-allocation, validation-objective-activity, validation-depth-sufficiency, preliminary-plan-maturity."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-preliminary-verification-validation-plans, preliminary-verification-validation-plans, provisional-verification-method, verification-model-allocation, validation-objective-activity, validation-depth-sufficiency, preliminary-plan-maturity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Preliminary Verification and Validation Plans (space-systems/ecss/e2040-preliminary-verification-validation-plans)

Use when the task is the early-planning duty of ECSS-E-ST-20-40C clause
5.2.4 -- setting out, while the device is still being defined, how it
will later be verified and validated, and judging whether the two
preliminary plans are mature enough for the definition phase to close.

## Domain quick reference

- Preliminary does not mean provisional everywhere. Each requirement is
  expected to carry a method and an article it will run on; what stays
  open at this stage is the procedure, not the intention.
- The article matters as much as the method. A method with no model
  behind it cannot be costed, scheduled or built for, and the plan that
  omits it reads as complete right up to the point where the hardware
  list is drawn up.
- The model set is owned by the development plan. A verification entry
  naming an article the development plan never declares is a campaign
  planned on hardware nobody is building.
- Verification and validation answer different questions. Verification
  asks whether the device meets its requirements; validation asks
  whether those requirements were the right ones. An objective
  restated as a requirement line quietly deletes the second question.
- Validation activities have depth. A review can confirm an intention;
  only an end-to-end run or an operational demonstration can answer a
  mission-level objective, so the activity has to match the objective
  it is attached to.
- Maturity is two fractions, not one. Verification maturity is the
  share of requirements carrying both a method and a model; validation
  maturity is the share of objectives carrying an activity. Reporting
  one figure hides whichever plan is behind.
- Both fractions land exactly on their target. The comparison absorbs
  the representation error of a division instead of holding a phase
  open over the last bit.

## Workflow

1. Resolve the model set the development plan declares, folding
   repeats, and refuse an empty set.
2. Resolve the verification entries: unique requirement identifiers, a
   folded provisional method, the article, and the level. Refuse an
   unknown method rather than passing it through.
3. Report every requirement carrying no method, and every requirement
   carrying no article or naming one outside the declared model set.
4. Resolve the validation objectives: unique identifiers, the kind of
   need each answers, and the activities attached to them.
5. Report every objective with no activity, and every objective whose
   activities are all shallower than the kind of need it answers.
6. Report any objective identifier that also appears as a verification
   requirement, because the two plans are then describing the same line
   twice and only one question is being asked.
7. Compute verification maturity, validation maturity and the combined
   preliminary maturity, compare them against the phase-gate target
   absorbing representation error, and return the findings.

## Pitfalls

- Deferring the model allocation to the detailed plan. The allocation
  is what turns a method into a cost and a build, and the plan that
  leaves it out is the one that discovers at the design review that
  nothing was ordered.
- Allocating verification to an article the development plan does not
  build. Each document is internally consistent; the defect exists only
  in the gap between them, which is why the model set is passed in
  rather than inferred.
- Answering a mission-level objective with a document review. The
  review confirms that somebody intended the right thing, which is
  exactly the claim validation is supposed to test independently.
- Folding validation into the verification matrix. Every objective then
  has a tidy requirement row, the coverage figure goes up, and the
  question of whether the requirements were right is no longer asked
  by anyone.
- Reporting a single blended maturity figure. A verification plan at
  full maturity and a validation plan at none averages to something
  that looks like progress on both.

## Behavior contract (gate 3)

The model-set resolution, provisional method folding, model allocation
check, validation activity depth, verification and validation overlap
detection and the maturity comparison are exercised by the gate 3
contract test:
scripts/test_e2040_preliminary_verification_validation_plans.py against
scripts/e2040_preliminary_verification_validation_plans_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2040_preliminary_verification_validation_plans.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

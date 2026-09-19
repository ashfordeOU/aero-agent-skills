---
name: e2040-device-validation-plan-data-item
description: "Validate a device validation plan against the required contents of ECSS-E-ST-20-40C Annex D before the plan is released. Use when the plan has to show that every declared use case is covered by a validation activity carrying a stated approach and a measurable pass criterion: build the use-case-to-activity coverage matrix, compute the criticality-weighted coverage fraction, confirm each criterion carries a comparator, a finite bound and a unit, require a test-class activity behind a safety-driving use case that analysis alone cannot close, and report uncovered use cases, unmeasurable criteria and approach shortfalls. Trigger: ecss, e-st-20-40-device-scope, device-validation-plan-data-item, validation-use-case-coverage, validation-approach-adequacy, measurable-pass-criterion, criticality-weighted-coverage, validation-plan-drd."
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
  tags: [ecss, e-st-20-40-device-scope, e2040-device-validation-plan-data-item, validation-use-case-coverage, validation-approach-adequacy, measurable-pass-criterion, criticality-weighted-coverage, validation-plan-drd]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Device Validation Plan Data Item (space-systems/ecss/e2040-device-validation-plan-data-item)

Use when the task is the required contents of the device validation plan
of ECSS-E-ST-20-40C Annex D -- establishing that the plan states a
validation approach, enumerates the use cases the device is to be
validated against, and attaches a pass criterion to each validation
activity that a reviewer could later grade an outcome against.

## Domain quick reference

- A validation **use case** is a way the device is intended to be used,
  carried in the plan with an identifier and a criticality weight. The
  weight is what makes coverage a quantity rather than a tick: covering
  nine trivial use cases and missing the driving one is not 90 percent
  coverage of anything that matters.
- A validation **activity** names the approach it uses and the use cases
  it covers. The recognized approaches are test, demonstration,
  analysis, similarity and review-of-design. The first two produce an
  observation on the device; the last three produce an argument about
  it, and that distinction is what decides whether a safety-driving use
  case is closed.
- A **pass criterion** is measurable only when it carries all three of a
  comparator, a finite numeric bound and a unit. A criterion reading
  "behaves acceptably", or carrying a bound with a TBD unit, cannot be
  graded and is a content defect of the plan, not of the device.
- An **equality criterion** on a continuous quantity is never met
  exactly by a real measurement. It is measurable only when the plan
  also states the tolerance the equality is judged within.
- **Coverage** is computed over the use cases, not over the activities.
  A plan with many activities that all point at the same two use cases
  is a low-coverage plan however busy the activity list looks.

## Workflow

1. Check the plan's section list against the required contents and
   report each missing section by name; a plan that omits the use-case
   section cannot be assessed for coverage at all.
2. Validate every use case: an identifier, a positive criticality
   weight, and an explicit safety-driving flag. Reject a duplicate
   identifier rather than letting the later entry silently win.
3. Validate every activity: an identifier, a recognized approach, a
   non-empty list of covered use-case identifiers, and a pass criterion.
   Reject an activity that covers an identifier no use case declares --
   that is a dangling reference, not coverage.
4. Build the coverage matrix from use-case identifier to the activities
   that cover it, and compute the criticality-weighted coverage fraction
   as covered weight over total weight.
5. For each safety-driving use case, confirm at least one covering
   activity uses an observing approach. A safety-driving case held up by
   analysis and similarity alone is an approach shortfall.
6. Grade each pass criterion for measurability, and evaluate a supplied
   measured value against it when one is available, absorbing
   representation error at the bound with a named tolerance instead of
   loosening the bound.
7. Report the coverage fraction against the required threshold together
   with every uncovered use case, unmeasurable criterion and approach
   shortfall as separate findings.

## Pitfalls

- Counting activities instead of use cases. Coverage is a property of
  the use-case set; an activity count says nothing about what is left
  uncovered.
- Treating an unweighted use-case list as uniform. Absent weights are
  not equal weights -- they are a missing plan content, and assuming
  uniformity hides that the driving case was never assigned one.
- Accepting an equality pass criterion with no tolerance. It reads
  precise and is ungradeable, because no measurement of a continuous
  quantity lands exactly on a stated bound.
- Closing a safety-driving use case by similarity to an earlier device.
  Similarity is an argument about heritage, and the plan has to say
  which observation backs it before the case is covered.
- Relaxing the required coverage threshold to make a plan pass. An
  equality at the threshold is a representation question, handled by the
  tolerance inside the comparison; the required fraction stays as
  specified.

## Behavior contract (gate 3)

The section check, use-case and activity validation, coverage-matrix
construction, weighted coverage fraction, approach-shortfall detection,
criterion measurability grading and criterion evaluation are exercised
by the gate 3 contract test:
scripts/test_e2040_device_validation_plan_data_item.py against
scripts/e2040_device_validation_plan_data_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_validation_plan_data_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e3102-burst-pressure-test
description: "Determine whether the burst test of a two-phase heat transport item satisfies ECSS-E-ST-31-02C clause 5.6.7. Use when the task is forming the burst requirement from maximum design pressure and the minimum burst factor, correcting it for a test temperature whose material allowable differs from the design point, grading the ramp method and whether the article had already been through its life cycling, computing the achieved burst factor, and building the leak-before-burst case from hoop stress, fracture toughness, wall thickness and leak detectability. Trigger: ecss, e-st-31-02c, minimum-burst-factor, burst-test-ramp-method, leak-before-burst-evidence, critical-through-wall-crack-length, end-of-life-burst-article, burst-hazard-justification."
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
  tags: [ecss, e-st-31-02-two-phase-heat-transport-scope, e3102-burst-pressure-test, minimum-burst-factor, burst-test-ramp-method, leak-before-burst-evidence, critical-through-wall-crack-length, end-of-life-burst-article]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Burst Pressure Test (space-systems/ecss/e3102-burst-pressure-test)

Use when the task is the burst test of ECSS-E-ST-31-02C clause 5.6.7 --
what pressure the article has to survive, how it is taken there, which
article is taken there, and the separate argument that a flaw in the
pressure boundary announces itself by leaking rather than by running.

## Domain quick reference

- The burst requirement is the maximum design pressure times the minimum
  burst factor, corrected to the test temperature by the ratio of the
  material allowables when the test is not run at the design point. A
  factor at or below unity puts the burst requirement at or under the
  service pressure and is refused.
- Which article bursts decides what the number means. A burst on a
  pristine unit is an end-of-manufacture strength; the clause wants the
  strength that survives the life, so the burst article is the one that
  has already been through the pressure cycling. A high number from a
  fresh article is not the same evidence and should not be reported as
  though it were.
- Method carries a hazard dimension. A hydraulic ramp stores almost no
  energy in the fluid; a pneumatic ramp stores a great deal and fails
  violently, so a pneumatic burst needs a declared hazard justification
  before it counts as an acceptable method rather than as an
  improvisation.
- Leak-before-burst is a separate demonstration and it is not implied by
  a high burst pressure. It says that a growing flaw penetrates the wall
  and leaks while the through-wall crack is still shorter than the
  length at which it becomes unstable. The critical length follows from
  the fracture toughness and the hoop stress at the grading pressure,
  and is compared against the wall thickness.
- A leak nobody detects is not leak-before-burst. The through-wall leak
  has to exceed the detection threshold by a margin, otherwise the flaw
  leaks quietly and keeps growing toward the length that runs.
- Thin-wall hoop stress is an approximation with a validity condition.
  When the wall is not small against the radius the formula no longer
  applies, and the correct response is to refuse it rather than to
  report a number from it.

## Workflow

1. Validate the maximum design pressure and burst factor; refuse a
   factor at or below unity.
2. Form the burst requirement, applying the test-temperature correction
   when both material allowables are declared and refusing a
   half-declared correction.
3. Grade the actual burst pressure against the requirement and report
   the achieved burst factor alongside the verdict.
4. Normalise the ramp method, grade the article history, and require a
   hazard justification for a method that stores enough energy to need
   one.
5. Form the hoop stress at the grading pressure, refusing the thin-wall
   formula when the wall is not thin.
6. Form the critical through-wall crack length from the toughness and
   that stress, and grade it against the wall thickness at the declared
   length margin.
7. Grade the through-wall leak rate against the detection threshold at
   the detection margin.
8. Combine the three checks into one verdict and name every failed one.

## Pitfalls

- Reporting a burst on a pristine article as the qualification number.
  The life cycling is what the burst is supposed to have survived, and a
  fresh unit answers a question nobody asked.
- Treating a comfortable burst margin as leak-before-burst evidence. The
  two arguments use different inputs; a thick strong wall can be exactly
  the one whose critical crack length is shorter than its thickness.
- Comparing the critical crack length against the wrong dimension. It is
  the wall thickness the flaw has to penetrate, not the vessel diameter
  or the weld length.
- Forgetting detectability. A leak-before-burst case that ends at "it
  leaks" is incomplete; the leak has to be one the declared instrument
  finds, with margin, before growth continues.
- Applying thin-wall hoop stress to a thick-walled fitting. The formula
  understates the stress there and inflates the critical crack length,
  making the weakest part of the boundary look like the safest.
- Running a pneumatic burst because the rig was already plumbed for gas.
  The stored energy is the reason the method needs a justification, and
  an undeclared one is a finding independent of the pressure achieved.

## Behavior contract (gate 3)

The burst-factor validation, requirement formation with test-temperature
correction, achieved-factor computation, ramp-method and article-history
grading with the hazard case, thin-wall hoop stress with its validity
refusal, critical through-wall crack length, leak detectability margin
and the rolled-up verdict are exercised by the gate 3 contract test:
scripts/test_e3102_burst_pressure_test.py against
scripts/e3102_burst_pressure_test_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3102_burst_pressure_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

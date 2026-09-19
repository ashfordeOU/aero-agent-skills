---
name: e31-predictability-testability-flexibility-integration
description: "Assess whether a thermal control design is predictable, testable, robust to uncertainty and reachable at integration, against ECSS-E-ST-31C clauses 4.4.6 to 4.4.8. Use when a thermal design has to be judged on its properties rather than its predicted temperatures: weighting how much of the heat path is characterised by measurement instead of assumed, combining the uncertainty contributors and the parameter sensitivities into a bounding excursion and grading the widened prediction against the limit, measuring how much of the heater authority is still unspent, and finding every temperature reference point with no sensor and every item unreachable once the blankets close. Trigger: ecss, e-st-31-thermal-control-scope, thermal-design-predictability, thermal-model-uncertainty-allocation, thermal-reference-point-instrumentation, heater-authority-margin, thermal-hardware-accessibility, thermal-design-testability."
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
  tags: [ecss, e-st-31-thermal-control-scope, e31-predictability-testability-flexibility-integration, thermal-design-predictability, thermal-model-uncertainty-allocation, thermal-reference-point-instrumentation, heater-authority-margin, thermal-hardware-accessibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Predictability, Testability, Flexibility and Integration (space-systems/ecss/e31-predictability-testability-flexibility-integration)

Use when the task is grading a thermal control design against the design
properties of ECSS-E-ST-31C clauses 4.4.6 to 4.4.8 — whether its
performance can be predicted, whether the prediction can be tested,
whether it survives the uncertainty in its own inputs, and whether the
hardware can still be reached when the spacecraft is being built.

## Domain quick reference

- Predictability is a property of the heat path, not of the analyst. A
  design whose dominant couplings are measured interface conductances is
  predictable; one whose dominant couplings are handbook guesses is not,
  however precise the reported temperature looks. The honest metric
  weights each path by the conductance it carries, because a
  characterised path carrying a milliwatt per kelvin buys nothing.
- Uncertainty arrives two ways and they do not combine the same way.
  Independent random contributors combine as a root sum of squares; a
  swept design parameter with a declared range contributes a bounding
  excursion equal to the sensitivity times the half-range, and those
  excursions add. Reporting only the root sum of squares understates a
  design dominated by one badly known parameter.
- Testability means the quantity the model predicts is the quantity the
  test measures. A temperature reference point with no sensor cannot
  correlate the model at that point, and no amount of neighbouring
  sensors substitutes for it.
- Flexibility is unspent authority: heater power installed beyond what
  the cold case needs, and radiator area beyond what the hot case needs.
  Spent at delivery, both go negative during the first dissipation
  growth the payload asks for.
- Integration and accessibility are design properties with a deadline.
  An item that needs access after the blankets close, or that can only
  be removed by taking something else off, is a finding while it is
  still cheap to move.

## Workflow

1. Validate the heat-path list: each path needs a positive conductance
   and an explicit characterised flag; an empty list is an input error,
   not a perfectly predictable design.
2. Form the conductance-weighted characterised fraction and compare it
   with the declared predictability threshold.
3. Combine the independent uncertainty contributors as a root sum of
   squares, add the bounding excursions of the swept parameters, widen
   the nominal prediction by the total, and grade the widened value
   against the limit with a named boundary tolerance.
4. Compute the heater authority margin as unspent installed power over
   required power, and compare it with the declared flexibility
   threshold.
5. Cover the temperature reference points against the instrumented
   points, and raise one finding per uninstrumented reference point.
6. Walk the accessibility list and raise a finding for every item
   needing access after close-out and every item whose removal demands
   another item come off first.
7. Report the per-attribute verdicts, the combined uncertainty and every
   finding; the design is compliant only when no attribute raised one.

## Pitfalls

- Counting characterised heat paths by number. Ten characterised
  micro-couplings and one assumed main interface is an unpredictable
  design that scores ninety per cent unweighted.
- Reporting only the root-sum-square uncertainty. It is the right
  combination for independent random contributors and the wrong one for
  a parameter whose value is simply not known across a declared range.
- Treating a nearby sensor as covering a reference point. The model is
  correlated where the sensors are; an uninstrumented reference point
  stays uncorrelated whatever its neighbours read.
- Reading a positive heater margin at delivery as flexibility. The
  margin is the growth the design can still absorb, so it is measured
  against the required power, not against the installed power, and it
  is consumed by the first payload increase.
- Deferring accessibility to the integration team. By then the finding
  costs a blanket rework; during design it costs a bracket.
- Widening the limit to make an exact-equality prediction pass. The
  boundary case is a representation question handled by the tolerance
  inside the comparison, never by relaxing the limit.

## Behavior contract (gate 3)

Heat-path weighting, root-sum-square and bounding uncertainty
combination, widened-prediction grading, heater authority margin,
reference-point coverage and accessibility findings are exercised by the
gate 3 contract test:
scripts/test_e31_predictability_testability_flexibility_integration.py
against
scripts/e31_predictability_testability_flexibility_integration_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e31_predictability_testability_flexibility_integration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

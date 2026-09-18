---
name: q7002-test-report
description: "Document the conditions, results and uncertainties of a thermal-vacuum outgassing screening run in the reporting format of ECSS-Q-ST-70-02C, or grade a report already issued. Use when a run is finished and the record must state the material tested, the conditions achieved, the values obtained and their uncertainty. Checks identification to batch and processing state, grades every recorded condition against its window, pairs an out-of-window condition with a recorded deviation, combines the uncertainty components in quadrature, expands them by the declared coverage factor, and matches value resolution to uncertainty. Trigger: ecss, q-st-70-02, outgassing-test-report, outgassing-test-conditions-window, outgassing-uncertainty-budget, expanded-uncertainty-coverage-factor, out-of-window-test-deviation, outgassing-reporting-resolution."
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
  tags: [ecss, q-st-70-materials-outgassing-scope, q7002-test-report, outgassing-test-report, outgassing-test-conditions-window, outgassing-uncertainty-budget, expanded-uncertainty-coverage-factor, out-of-window-test-deviation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening — Test Report (space-systems/ecss/q7002-test-report)

Use when the task is the reporting step of the ECSS-Q-ST-70-02C
thermal-vacuum outgassing screening test — writing, or grading, the
record of the material tested, the conditions achieved, the values
obtained and their uncertainty.

## Domain quick reference

- Identification has to be tight enough for someone else to obtain the
  same material. A designation names a family; the batch or lot and the
  processing state name the thing that was actually in the chamber. Two
  specimens of the same adhesive cured differently are two materials as
  far as outgassing is concerned, and a report that cannot tell them
  apart cannot be reused.
- Conditions are reported as held, not as intended. Each has a shape:
  the preconditioning and bake temperatures and the collector
  temperature sit inside a window either side of a nominal, the
  preconditioning and test durations are floors, and the chamber
  pressure is a ceiling. Confusing a floor with a window passes a run
  that was cut short.
- A condition outside its window is reportable, not fatal — a material
  whose maximum use temperature sits under the screening temperature is
  legitimately baked lower. An out-of-window value with nothing on record
  explaining it is fatal, because the reader cannot tell a decision
  from a slip.
- Uncertainty components combine in quadrature into a combined standard
  uncertainty, and the expanded figure is that times the declared
  coverage factor. Both the components and the factor belong in the
  report: an expanded number alone cannot be recombined with anything
  else.
- Value and uncertainty are reported at the same resolution. A result
  rounded coarser than its own uncertainty discards the digits the
  uncertainty was computed for, and an uncertainty several decades finer
  than the reporting step is arithmetic no reader can use.

## Workflow

1. Check identification: report identifier, designation, manufacturer,
   batch or lot, processing state. A blank or absent field counts as missing.
2. Confirm every condition field carries a number, listing any that do
   not.
3. Grade each recorded condition against its own shape — window, floor
   or ceiling — absorbing representation error at the edge with a named
   tolerance rather than by widening the window.
4. Read the recorded deviations, each naming a condition and carrying a
   justification. Pair them with the out-of-window conditions: an
   unpaired out-of-window value and a deviation against an in-window
   value are each their own finding.
5. Check the result fields, including a whole-number specimen count at
   or above the replicate minimum of the method.
6. Combine the uncertainty components in quadrature, expand by the
   declared coverage factor, and refuse a factor outside the reportable
   range.
7. Compare the expanded uncertainty with the reported value and with the
   reporting step, raising a finding when the uncertainty swamps the
   value or sits far under the resolution the report is written at.
8. Emit the rounded reported values, the combined and expanded
   uncertainties, and every finding; the report is reportable only when
   no finding stands.

## Pitfalls

- Reporting the setpoints instead of the achieved conditions. A
  setpoint records the controller's instruction, and a report built from
  it cannot explain a result disagreeing with an earlier run.
- Treating the test duration as a window. It is a floor, and a run
  stopped early is not within tolerance of anything.
- Recording a deviation but leaving the condition at its nominal value,
  or the reverse. Either way the report and the run disagree, and the
  reader must trust one of them without being told which.
- Publishing an expanded uncertainty with no components and no coverage
  factor. Nothing downstream can recombine it, so every later budget
  must either re-derive it or guess.
- Rounding the result to the house resolution and the uncertainty to
  full precision. They describe the same measurement and are read
  together.

## Behavior contract (gate 3)

The completeness checks, condition-window grading, deviation pairing,
quadrature combination, coverage-factor expansion, resolution matching
and report aggregation are exercised by the gate 3 contract test:
scripts/test_q7002_test_report.py against
scripts/q7002_test_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7002_test_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

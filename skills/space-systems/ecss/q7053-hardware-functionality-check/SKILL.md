---
name: q7053-hardware-functionality-check
description: "Verify that an assembly still works after a sterilization-compatibility exposure, in the evaluation clauses of ECSS-Q-ST-70-53C. Use when post-exposure functional measurements exist and someone has to state whether the hardware's functions survived the process. Grades every parameter against its own one-sided or two-sided window, absorbs the instrument resolution at the bound instead of widening it, treats a repeated-actuation series as intermittent when any single actuation leaves the window while the mean stays inside, forms the actuation margin against the resisting load and its factor, weights the verdicts by criticality, and refuses to let a safety-critical loss pass behind a healthy index. Trigger: ecss, q-st-70-53-sterilization-compatibility-scope, post-sterilization-functional-integrity, functional-parameter-window, intermittent-actuation-detection, mechanism-actuation-margin, criticality-weighted-functional-index."
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
  tags: [ecss, q-st-70-53-sterilization-compatibility-scope, q7053-hardware-functionality-check, post-sterilization-functional-integrity, functional-parameter-window, intermittent-actuation-detection, mechanism-actuation-margin, criticality-weighted-functional-index]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Sterilization Compatibility — Hardware Functionality Check (space-systems/ecss/q7053-hardware-functionality-check)

Use when the task is the functional half of an ECSS-Q-ST-70-53C
compatibility evaluation — taking the post-exposure functional
measurements of an assembly and deciding whether the sterilization
process left it able to do its job.

## Domain quick reference

- A functional requirement is a window, and the window is not always
  two-sided. Insulation resistance has a floor only; leak rate has a
  ceiling only; an actuation time usually has both. A parameter graded
  against the wrong shape of window either fails a healthy unit or
  passes a dead one.
- A single post-exposure reading is not evidence for a mechanism. The
  failure mode a sterilization exposure produces in an assembly is
  usually intermittent — a swollen seal, a redeposited residue, a
  softened lubricant — so a repeated-actuation series is graded sample
  by sample, and one excursion is a finding even when the mean of the
  series sits comfortably inside the window.
- A mechanism is graded on margin, not on whether it moved. The
  available drive is compared with the resisting load multiplied by its
  required factor, and the margin is what is left over; a mechanism that
  actuates with no margin has already failed the evaluation.
- Criticality decides what an aggregate verdict is allowed to say. A
  weighted index is useful for ranking units against each other, but a
  safety-critical function outside its window is a reject no matter how
  good the index looks.
- A reading within the instrument resolution of a bound is not a
  breach. That is absorbed by the declared resolution of the
  measurement, which is different from widening the window.

## Workflow

1. Validate each function record: a name, a known criticality, at least
   one finite bound, a consistent min-max pair, a non-negative
   resolution, and either a single measured value or a non-empty series
   of repeated actuations.
2. Grade each sample against the window, treating a sample within the
   resolution of a bound as meeting that bound, and record the margin to
   the nearest bound.
3. Mark a series intermittent when its mean lies inside the window but
   at least one sample does not; report the worst sample.
4. Where a mechanism record carries a drive and a resisting load, form
   the actuation margin as the available drive over the resisting load
   times its factor, minus one, and require a non-negative result.
5. Weight each function by its criticality and form the functional
   index as the weighted share of functions that passed.
6. Set the overall verdict to reject whenever any safety-critical
   function failed, whenever any function is intermittent, or whenever
   the index falls under the declared threshold.
7. Report findings naming each failed function, each intermittent one,
   and each mechanism with a negative actuation margin.

## Pitfalls

- Grading a one-sided requirement with a two-sided band. An insulation
  resistance that rose is not a defect, and inventing a ceiling for it
  turns a healthy reading into a reject.
- Averaging a repeated-actuation series before grading it. The mean
  hides exactly the intermittency the exposure is most likely to have
  caused.
- Reporting that a mechanism actuated. Actuation without margin is a
  pass by luck; the margin against the factored resisting load is the
  graded quantity.
- Letting a weighted index overrule a safety-critical loss. The index
  ranks; it does not decide. A safety-critical function outside its
  window ends the evaluation.
- Widening a window to swallow a reading close to the bound. The
  instrument resolution is declared with the measurement and applied to
  the sample; the window stays as specified.

## Behavior contract (gate 3)

The record validation, one-sided and two-sided window grading,
resolution absorption, intermittency detection, actuation-margin
formation, criticality weighting and the safety-critical override are
exercised by the gate 3 contract test:
scripts/test_q7053_hardware_functionality_check.py against
scripts/q7053_hardware_functionality_check_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7053_hardware_functionality_check.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

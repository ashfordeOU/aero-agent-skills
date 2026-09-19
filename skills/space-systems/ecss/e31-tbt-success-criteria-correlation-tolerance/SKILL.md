---
name: e31-tbt-success-criteria-correlation-tolerance
description: "Determine whether a thermal balance test met its success criteria under ECSS-E-ST-31C clause 4.5.3.2. Use when predicted and measured temperatures are both in hand and the campaign needs a defendable verdict rather than a plot: applying the per-sensor correlation tolerance band, spending the exceedance budget by sensor weight instead of by headcount, grading the weighted bias and the spread separately so a model that is right on average and wrong everywhere still fails, and refusing an excluded sensor that carries no recorded reason. Trigger: ecss, e-st-31-thermal-control-scope, tbt-correlation-success-criteria, correlation-tolerance-band, correlation-exceedance-budget, weighted-correlation-bias, thermal-balance-test-sensor-exclusion, tbt-pass-fail-verdict."
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
  tags: [ecss, e-st-31-thermal-control-scope, e31-tbt-success-criteria-correlation-tolerance, tbt-correlation-success-criteria, correlation-tolerance-band, correlation-exceedance-budget, weighted-correlation-bias, thermal-balance-test-sensor-exclusion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Thermal Balance Test Success Criteria (space-systems/ecss/e31-tbt-success-criteria-correlation-tolerance)

Use when the task is turning a thermal balance test result into the
pass or fail verdict of ECSS-E-ST-31C clause 4.5.3.2 — the tolerance
the predicted temperatures have to sit inside, how much of the sensor
set is allowed outside it, and what has to be recorded before a sensor
is left out of the count.

## Domain quick reference

- The success criterion is a band, a budget and two statistics, and all
  four are separate gates. A result can sit inside the band everywhere
  and still fail on bias, or carry a perfect bias and fail on spread.
- The per-sensor band is the primary gate because it is the one the
  design margins were written against. A deviation inside the band is
  agreement; outside it, the model does not represent that location.
- The exceedance budget is spent by weight, not by headcount. Twenty
  structure sensors and two on the payload interface make a
  count-based budget meaningless: a failure at both critical locations
  costs the same as two structural outliers.
- Bias and spread say different things. A uniform offset points at a
  boundary condition, an environment or an absorbed flux; a large
  spread with no offset points at the conductive network. Collapsing
  the two into one number loses the diagnosis the criteria exist to
  produce.
- Exclusions are the part of the verdict most likely to be argued at
  review. A sensor left out needs a recorded reason, and the fraction
  of the set excluded is itself capped, because a criterion that any
  result can meet by dropping sensors is not a criterion.
- A verdict names which gate failed. Reporting only pass or fail throws
  away the single most useful output of the exercise.

## Workflow

1. Validate each sensor record: a name, a predicted and a measured
   absolute temperature, a positive weight where one is declared, and
   an explicit exclusion flag where the sensor is being left out.
2. Separate the excluded sensors from the graded ones, raising a
   finding for every exclusion with no recorded reason, and refuse a
   set where nothing is left to grade.
3. Check the excluded weight against the cap on how much of the set may
   be dropped.
4. Form each graded sensor's deviation as predicted minus measured, and
   mark it against the per-sensor tolerance band.
5. Spend the exceedance budget by weight: the weight outside the band
   over the total graded weight, compared with the budget using a named
   boundary tolerance.
6. Form the weighted bias and the weighted spread and compare each with
   its own allowance.
7. Report the verdict together with the gates that failed, the worst
   sensor and the full deviation list, so the reason survives into the
   test report.

## Pitfalls

- Grading only the mean deviation. A model fifteen kelvin high at one
  end and fifteen low at the other has no bias and no correlation, and
  a mean-only criterion passes it.
- Counting the exceedance budget by sensor number. The critical
  locations are always the minority, so a headcount budget is spent by
  whichever sensors happen to be numerous.
- Dropping the outliers first and grading afterwards. Every exclusion
  needs its reason in the record before the verdict, and the excluded
  fraction is capped for exactly this reason.
- Relaxing the band to absorb one stubborn sensor. The band came from
  the design margins; moving it moves the margin, which is a design
  change, not a test result.
- Reporting pass or fail alone. The gate that failed is the diagnosis:
  bias points at the boundary, spread points at the network, and a
  single-sensor breach points at that location's model.
- Widening a criterion to rescue an exact-equality case. The boundary
  is a representation question absorbed by the tolerance inside the
  comparison, never by moving the criterion.

## Behavior contract (gate 3)

Sensor validation, exclusion handling with its recorded-reason
requirement and excluded-weight cap, per-sensor band marking, weighted
exceedance budget, weighted bias and spread, and the gate-naming verdict
are exercised by the gate 3 contract test:
scripts/test_e31_tbt_success_criteria_correlation_tolerance.py against
scripts/e31_tbt_success_criteria_correlation_tolerance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_tbt_success_criteria_correlation_tolerance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

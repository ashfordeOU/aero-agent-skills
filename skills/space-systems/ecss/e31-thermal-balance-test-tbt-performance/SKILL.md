---
name: e31-thermal-balance-test-tbt-performance
description: "Define and grade the performance of a thermal balance test under ECSS-E-ST-31C clause 4.5.3.1 and its annex on test cases. Use when a thermal vacuum campaign needs its balance phases written down and run: checking the case set brackets the mission with a hot and a cold case, sizing the compensation heater power that makes a chamber shroud and a lamp bank reproduce the flight heat flow, deciding steady state from the measured drift rate over a long enough window rather than by eye, and covering every temperature reference point with a sensor accurate enough to grade it. Trigger: ecss, e-st-31-thermal-control-scope, thermal-balance-test-case-set, balance-heater-compensation-power, thermal-steady-state-drift-criterion, tbt-temperature-reference-point-sensor, thermal-vacuum-shroud-sink, tbt-instrumentation-accuracy."
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
  tags: [ecss, e-st-31-thermal-control-scope, e31-thermal-balance-test-tbt-performance, thermal-balance-test-case-set, balance-heater-compensation-power, thermal-steady-state-drift-criterion, tbt-temperature-reference-point-sensor, thermal-vacuum-shroud-sink]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Thermal Balance Test Performance (space-systems/ecss/e31-thermal-balance-test-tbt-performance)

Use when the task is specifying or running the thermal balance phases of
a thermal vacuum campaign under ECSS-E-ST-31C clause 4.5.3.1 and its
test-case annex — which balance cases are run, how much compensation
heater power each needs, when a case has actually reached steady state,
and which sensors have to be there for the case to be gradeable.

## Domain quick reference

- A balance test earns its name by bracketing the mission. One hot case
  and one cold case are the minimum, because a single case correlates
  the model at one point of a fourth-power curve and says nothing about
  the slope.
- The chamber is not the mission. A shroud at liquid-nitrogen
  temperature rejects more than the flight sink, and a lamp bank rarely
  matches the absorbed flux in both magnitude and distribution. The
  balance heaters exist to close that difference.
- The compensation power has two terms and they can oppose each other:
  the absorbed-flux shortfall the lamps do not deliver, and the extra
  rejection a colder shroud pulls out of the article. Adding only the
  first leaves a case that runs cold and correlates a model to the wrong
  boundary.
- Balance heaters can only add heat. A case whose compensation comes out
  negative cannot be run as configured; the shroud has to come up or the
  lamp power has to come down, and quietly clamping the demand at zero
  produces a case nobody can correlate against.
- Steady state is a measured drift rate over a declared window, not an
  impression from a strip chart. The slope of a least-squares fit over
  the window is the criterion, and a window shorter than declared cannot
  demonstrate it whatever the slope says.
- A temperature reference point without a sensor of adequate accuracy is
  not gradeable. A sensor whose accuracy is coarser than the correlation
  tolerance cannot resolve the quantity the test exists to produce.

## Workflow

1. Validate each declared case: a name, a hot or cold sense, a
   non-negative chamber sink, non-negative absorbed test flux and
   non-negative article dissipation.
2. Check the set brackets the mission: at least one hot case and one
   cold case, and no duplicate case names.
3. For each case, size the compensation heater power as the absorbed
   flux the lamps do not deliver plus the extra rejection of the colder
   shroud, and raise a finding when the result is negative instead of
   clamping it.
4. Compare each case's compensation demand with the installed balance
   heater capability and raise a finding on the shortfall.
5. For each case's temperature history, fit the drift rate over the
   declared window and declare steady state only when the window is long
   enough and every reference point's drift sits inside the criterion.
6. Cover the declared temperature reference points against the
   instrumentation, and raise a finding for a missing sensor and for a
   sensor whose accuracy is coarser than the grading needs.
7. Report the per-case compensation, the steady-state verdicts, the
   instrumentation findings and the overall test-readiness verdict.

## Pitfalls

- Running a single balance case. It correlates the model at one point
  and leaves the slope of the radiative curve untested, which is exactly
  the part the mission extremes depend on.
- Sizing compensation from the flux shortfall alone. The colder shroud
  term is often the larger of the two, and leaving it out lands the
  article well below the flight boundary.
- Clamping a negative compensation demand at zero. The case is
  infeasible as configured and the clamp hides it behind a heater
  setting that looks reasonable.
- Calling steady state from a short window. A slow mode still relaxing
  reads as a small slope over a few minutes and as a large one over an
  hour; the window length is part of the criterion.
- Grading the drift on the coldest sensor only. Steady state is a
  property of every reference point, and the last one to settle is the
  one that sets the dwell.
- Accepting a sensor coarser than the correlation tolerance. The test
  then cannot resolve the difference the correlation is about to be
  graded on.

## Behavior contract (gate 3)

Case validation and hot-cold bracketing, two-term compensation heater
sizing with its infeasibility refusal, least-squares drift rate with a
window-length guard, and reference-point coverage with sensor accuracy
are exercised by the gate 3 contract test:
scripts/test_e31_thermal_balance_test_tbt_performance.py against
scripts/e31_thermal_balance_test_tbt_performance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_thermal_balance_test_tbt_performance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

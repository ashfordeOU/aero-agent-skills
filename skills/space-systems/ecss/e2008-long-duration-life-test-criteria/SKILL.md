---
name: e2008-long-duration-life-test-criteria
description: "Assess whether the maximum power of a photovoltaic assembly stayed inside the two per cent degradation the ECSS-E-ST-20-08C clause 6.4.3.18.3 criterion allows across a whole long duration life test: translate every reading to the declared reference irradiance and cell temperature before differencing it, measure the fall against the initial reading of that same test, take the worst value anywhere in the series rather than the final one, admit a reading landing exactly on the limit, and report an excursion the end of the test recovered from. Use when sentencing or auditing a long duration life test result. Trigger: ecss, e-st-20-08c, clause-6-4-3-18-3, long-duration-life-test-criteria, maximum-power-degradation-limit, life-test-initial-reference-reading, reference-condition-power-correction, recovered-degradation-excursion."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-long-duration-life-test-criteria, long-duration-life-test-criteria, maximum-power-degradation-limit, life-test-initial-reference-reading, reference-condition-power-correction, recovered-degradation-excursion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Long Duration Life Test Criteria (space-systems/ecss/e2008-long-duration-life-test-criteria)

Use when the task is the clause 6.4.3.18.3 acceptance decision of
ECSS-E-ST-20-08C: a long duration life test has been run on a photovoltaic
assembly, and the maximum power degradation it recorded is admissible only
while it stays inside two per cent for the whole of that test.

## Domain quick reference

- The criterion is one number and one adverbial phrase, and the phrase is
  where campaigns lose it. Two per cent is the ceiling; across the whole test
  is the scope. An assembly that drops three per cent at four thousand hours
  and reads back at one and a half at eight thousand has been outside the
  criterion, whatever the last line of the table says.
- A recovery is itself a finding. Something reversible is moving in the
  article — moisture in an encapsulant, an interconnect making and breaking
  with temperature — and grading endpoints only converts the one measurement
  that showed it into a pass. The excursion is reported beside the verdict.
- Degradation is measured against the initial reading of this same test. A
  life test is a self-referencing measurement: the article is compared with
  itself, so a datasheet nominal or a subgroup average is the wrong
  denominator, and a missing initial reading closes the assessment rather
  than being substituted for.
- Readings have to be comparable before they can be differenced. Maximum
  power moves with irradiance and with cell temperature, so each reading is
  translated to the declared reference conditions first — the irradiance
  ratio and the linear power temperature coefficient. Differencing raw watts
  taken on a warm afternoon against watts taken on a cold morning reports the
  weather, not the article.
- The limit is a ceiling with the tie admissible: a reading landing exactly
  on two per cent is inside it, and that equality is a representation
  question handled by a named tolerance rather than by moving the limit.
- The limit, the reference conditions and the temperature coefficient are
  declared policy, not physical constants: a project substitutes its own, and
  a project that tightens the limit is tightening it for every reading in the
  series at once.

## Workflow

1. Validate every reading: a label, a non-negative elapsed hour, a positive
   power, a positive irradiance and a cell temperature. Refuse two readings
   sharing an elapsed hour, which means two articles have been folded into
   one series.
2. Translate each reading to the reference conditions through the irradiance
   ratio and the temperature coefficient, and refuse a reading so far off
   reference that the linear correction inverts.
3. Order the series in time and take the corrected power at zero elapsed
   hours as the reference. No reading there closes the assessment; an initial
   reading with nothing after it closes it too, because a criterion that
   holds across the test needs the test to have been measured across.
4. Compute the degradation of every reading against that reference.
5. Take the maximum over the whole series, and name the reading that carried
   it, breaking a tie on the earlier reading so the report is reproducible.
6. Compare with the limit, absorbing floating-point representation error at
   the boundary with a named tolerance rather than by relaxing the limit.
7. Report the verdict, the worst reading, the final degradation and any
   excursion the test later recovered from.

## Pitfalls

- Grading the last reading. The criterion holds across the whole test, so the
  final value is a report field, not the decision; an interior excursion
  fails the test even when the article ends inside the limit.
- Differencing uncorrected watts. Irradiance and cell temperature move
  maximum power by more than the two per cent being measured, so a series
  that was not translated to reference conditions cannot resolve the
  criterion at all.
- Measuring against a nominal. The denominator is the initial reading of this
  test on this article; a datasheet figure turns a life test into an
  acceptance test against the wrong population.
- Letting a recovery close the excursion. A reversible loss is a real
  behaviour of the article and the reason the intermediate measurements
  exist; it is reported, not smoothed away by the reading that followed it.
- Widening the limit for a value that landed exactly on it. The equality is a
  representation question, handled inside the comparison; the limit stays as
  the project declared it.

## Behavior contract (gate 3)

The reading validation, reference condition correction, series ordering,
initial reference selection, whole-series maximum degradation, limit
comparison and recovered excursion report are exercised by the gate 3
contract test: scripts/test_e2008_long_duration_life_test_criteria.py against
scripts/e2008_long_duration_life_test_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_long_duration_life_test_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

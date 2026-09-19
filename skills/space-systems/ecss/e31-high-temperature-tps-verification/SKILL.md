---
name: e31-high-temperature-tps-verification
description: "Verify high-temperature thermal protection items by the thermal tests and analyses agreed for them, per ECSS-E-ST-31C clause 4.5.2.3. Use when a nose cap, leading edge, flap or heatshield tile has to be shown adequate: derive the qualification temperature as predicted peak plus agreed margin and grade material capability against that, size the required thickness from recession rate, exposure and scatter plus insulation and manufacturing tolerance, grade the bondline against its own far lower limit, compare model with test as an absolute correlation error, and refuse analysis-only closure where a test was agreed. Trigger: ecss, e-st-31-thermal-control, e31-high-temperature-tps-verification, tps-qualification-temperature-margin, tps-bondline-temperature-limit, ablative-recession-thickness-allowance, tps-model-test-correlation-error, tps-verification-method-coverage."
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
  tags: [ecss, e-st-31-thermal-control, e31-high-temperature-tps-verification, tps-qualification-temperature-margin, tps-bondline-temperature-limit, ablative-recession-thickness-allowance, tps-model-test-correlation-error, tps-verification-method-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — High-Temperature Protection Verification (space-systems/ecss/e31-high-temperature-tps-verification)

Use when the task is the high-temperature step of ECSS-E-ST-31C clause
4.5.2.3 -- showing that a thermal protection item survives its predicted
environment, using the thermal tests and the thermal analyses that were
agreed for it rather than whichever of the two was cheapest to run.

## Domain quick reference

- Capability is graded against the qualification temperature, never against
  the prediction. The qualification temperature is the predicted peak plus
  the agreed margin, and a material that survives the prediction but not the
  qualification point has no margin at all.
- A protection item has two temperature limits and they are an order of
  magnitude apart. The surface capability is a material limit in the
  thousands of kelvin; the bondline limit is an adhesive or substrate limit
  a few hundred kelvin up. Passing the first says nothing about the second.
- Thickness is three separate allowances stacked, not one number: the
  recession sacrificed over the exposure, the insulation the bondline limit
  demands, and the manufacturing tolerance. Dropping any one of the three
  produces a part that is thin in a way no single check catches.
- Recession is a rate times an exposure duration times an agreed scatter
  factor. The scatter factor is never below unity; a plan that applies the
  nominal rate is sizing to the mean of a scattered population.
- Test and analysis are not interchangeable. An agreed test is not closed by
  an analysis, and an analysis that calls itself correlated needs a test to
  have been correlated against -- correlation with nothing is a label.
- Correlation is graded as an absolute temperature error against an agreed
  tolerance, in both directions. A model that under-predicts by 60 K is as
  uncorrelated as one that over-predicts by 60 K, even though the first one
  looks conservative on the plot.
- Margins here are differences and products of floats. A value landing
  exactly on its limit is absorbed by a named tolerance far below any
  thermocouple's resolution, not by loosening the limit.

## Workflow

1. List the protection items. For each, record predicted peak, agreed
   qualification margin, material capability, bondline limit and predicted
   bondline temperature, recession rate, exposure, scatter factor,
   insulation thickness, manufacturing tolerance and as-built thickness.
2. Record the agreed method set and the methods actually performed, plus the
   measured peak and correlation tolerance where a test was run.
3. Compute the qualification temperature and the capability margin over it.
4. Compute the recession allowance, stack it with insulation and tolerance
   into the required thickness, and take the as-built margin.
5. Take the bondline margin as limit minus predicted, separately from the
   surface check.
6. Where a test exists, take the absolute correlation error and grade it
   against the agreed tolerance.
7. Raise a finding for every agreed method not performed, and for a
   correlated analysis with no test behind it.
8. Roll the set up: verified fraction, and the item with the lowest
   capability margin as the driving item.

## Pitfalls

- Grading the material against the predicted peak. That is the temperature
  the item is expected to see, not the one it has to be qualified to.
- Passing an item on surface capability and never opening the bondline. The
  adhesive limit is hundreds of kelvin lower and is what actually fails.
- Sizing thickness on recession alone, or on insulation alone. The required
  thickness is the stack of recession, insulation and tolerance.
- Applying a nominal recession rate with no scatter factor, so the part is
  sized to the mean of a scattered material population.
- Closing an agreed thermal test with an analysis because the analysis
  agrees with the prediction. It agrees with itself.
- Calling an analysis correlated when no test result exists. The check has
  to look for the test, not for the word.
- Treating a correlation error as acceptable because the model was
  conservative. The tolerance is two-sided; an under-prediction of the same
  size is the same error.
- Using a strict comparison at the qualification point, the required
  thickness or the bondline limit. All three are float arithmetic, and a
  value on the boundary must read the same on every platform.

## Behavior contract (gate 3)

The qualification temperature derivation, capability margin and its
boundary case, recession allowance with its scatter floor, the three-part
thickness stack, the bondline margin, the two-sided correlation error and
its tolerance, method-coverage findings including the correlated-analysis
trap, and the set roll-up with its driving item are exercised by the gate 3
contract test: scripts/test_e31_high_temperature_tps_verification.py
against scripts/e31_high_temperature_tps_verification_logic.py (stdlib
unittest, offline). Boundary cases use assertAlmostEqual so a value on its
limit reads the same on every platform.
Run: python3 scripts/test_e31_high_temperature_tps_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

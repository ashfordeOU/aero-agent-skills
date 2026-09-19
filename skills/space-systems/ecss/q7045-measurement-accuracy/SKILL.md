---
name: q7045-measurement-accuracy
description: "Compute the measurement-uncertainty budget a mechanical test carries and decide whether it supports the property about to be reported. Use when the force, strain, displacement and temperature channels of a test under ECSS-Q-ST-70-45 have to be shown adequate: grade each channel against the limit that applies to it, keeping a relative limit relative and a temperature limit in kelvin, turn a digital step and a drift band into the standard uncertainties they contribute, double the diameter term on its way into an area, combine independent terms in quadrature, expand with a coverage factor, then name the dominant contributor. Trigger: ecss, q-st-70-45-mechanical-testing, tensile-measurement-uncertainty-budget, tensile-force-channel-accuracy-limit, tensile-strain-channel-accuracy-limit, tensile-stress-uncertainty-propagation, tensile-test-temperature-channel-accuracy."
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
  tags: [ecss, q-st-70-45-mechanical-testing, q7045-measurement-accuracy, tensile-measurement-uncertainty-budget, tensile-force-channel-accuracy-limit, tensile-strain-channel-accuracy-limit, tensile-stress-uncertainty-propagation, tensile-test-temperature-channel-accuracy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing — Measurement Accuracy (space-systems/ecss/q7045-measurement-accuracy)

Use when the task is the measurement-accuracy step of a mechanical test
under ECSS-Q-ST-70-45: the channels are working, and the question is how
much of the number they produce is the material and how much is the
instrumentation, expressed as an uncertainty the reported property has
to come in under.

## Domain quick reference

- The channels do not share one limit. Force, strain, displacement and
  gauge length carry a relative limit in percent of reading; the
  temperature channel carries an absolute one in kelvin, because two
  kelvin is two kelvin whether the soak sits at 100 K or at 900 K.
- A resolution is not an uncertainty. A reading quantised to a step is
  uniform across that step, so its standard uncertainty is the step over
  two root three -- rather less than the step, and rather less than half
  of it, which is where the two common mistakes land.
- A band quoted as plus or minus a half-width is also uniform, and
  contributes the half-width over root three. Mixing the two conversions
  up inflates a drift term by a factor of two.
- Geometry enters squared. A stress carries the force term and twice the
  diameter term, because the area goes as the square of the diameter; a
  modulus carries force, strain, gauge length and that doubled diameter
  together.
- Independent terms combine in quadrature, so a chain of small terms is
  much smaller than their arithmetic sum and one large term dominates
  everything beneath it. Naming that dominant contributor is what turns
  a budget into an action.

## Workflow

1. Grade every channel against the limit that applies to it, taking a
   relative error in percent and a temperature error in kelvin, and
   refuse a channel for which no limit has been declared.
2. Convert each declared resolution into a standard uncertainty over two
   root three, and each declared plus-or-minus band over root three.
3. Form the geometry term: double the relative diameter uncertainty to
   get the area, and do not halve it again because two diameters were
   averaged -- that is a separate correction.
4. Assemble the contribution set for the property being reported: force
   and area for a stress; force, strain, gauge length and area for a
   modulus; plus every resolution and drift term.
5. Combine the contributions in quadrature into a combined standard
   relative uncertainty, and expand it with a coverage factor held
   between one and three.
6. Name the largest single contribution so the budget says what to fix.
7. Compare the expanded figure with the target the property owes,
   absorbing an exact equality at the target as representation error,
   and support the property only when no channel finding stands either.

## Pitfalls

- Grading the temperature channel in percent. A relative limit on a
  soak temperature passes a large absolute error at high temperature and
  fails a negligible one near ambient.
- Using the resolution itself as its uncertainty. It over-states the
  budget by more than three times and pushes teams into buying accuracy
  they already had.
- Forgetting that the area term is doubled. A tenth of a percent on the
  diameter is two tenths on the stress, which is often the largest term
  in the whole budget on a small round specimen.
- Adding contributions arithmetically. Quadrature is what independence
  buys; summing instead quietly over-states the total until someone
  relaxes a real acceptance limit to make the number fit.
- Reporting a combined standard uncertainty as though it were expanded.
  The coverage factor has to be stated with the figure, or the reader
  compares a one-sigma number against a ninety-five percent target.

## Behavior contract (gate 3)

The per-channel grading, resolution and band conversions, quadrature
combination, area and modulus propagation, dominant-contributor
selection and the expanded-versus-target comparison are exercised by the
gate 3 contract test:
scripts/test_q7045_measurement_accuracy.py against
scripts/q7045_measurement_accuracy_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_measurement_accuracy.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

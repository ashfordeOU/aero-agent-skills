---
name: e20-eed-circuit-safety-margin-demonstration
description: "Use when verify the interference-safety-margin demonstrated for a critical circuit or an electro-explosive-device firing circuit under ECSS-E-ST-20C clause 6.4.2: read the separation the circuit category demands off the programme ladder, de-rate the declared no-fire-threshold to the demonstration value, convert an induced-current or an induced-radio-frequency-level onto the decibel scale with the field-quantity or energy-quantity law the measurement obeys, refuse paper-only evidence where the firing-circuit demands instrumented measurement on flight-representative hardware, confirm every mandated operating-condition was exercised, and report the governing worst-case-condition with the separation it showed. Trigger: ecss, e-st-20-electrical-scope, eed-circuit-safety-margin-demonstration, electro-explosive-device-firing-circuit, no-fire-threshold-derating, bridgewire-no-fire-power, instrumented-margin-evidence, mandated-operating-condition-coverage, governing-worst-case-condition."
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
  tags: [ecss, e-st-20-electrical-scope, e20-eed-circuit-safety-margin-demonstration, eed-circuit-safety-margin-demonstration, electro-explosive-device-firing-circuit, no-fire-threshold-derating, instrumented-margin-evidence, mandated-operating-condition-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- EED and Critical Circuit Margin Demonstration (space-systems/ecss/e20-eed-circuit-safety-margin-demonstration)

Use when the task is the clause 6.4.2 demonstration of ECSS-E-ST-20C --
showing, with evidence the clause admits, that a critical circuit and in
particular the firing circuit of an electro-explosive device keeps the
separation between what it can tolerate and what the electromagnetic
environment actually induces in it.

## Domain quick reference

- Demanding a separation and demonstrating it are two different jobs.
  The demand comes from the circuit's category and sits on the
  programme ladder: the firing circuit of an electro-explosive device
  carries the widest demand, a safety or mission critical circuit a
  narrower one, and a non critical circuit none at all. This leaf is
  the demonstration: the demand is an input, and what is graded is the
  evidence produced against it.
- The evidence a category admits is not the same everywhere. A firing
  circuit is demonstrated by instrumented measurement at the firing
  interface on flight-representative hardware and harness -- a paper
  argument or an appeal to a similar unit does not demonstrate it,
  because the coupling being measured lives in the routing, the
  bonding and the connector, none of which the paper carries. A safety
  or mission critical circuit can rest on measurement or on a computed
  argument. Grading only the number and never the evidence kind passes
  a firing circuit that nobody instrumented.
- The threshold the demonstration measures against is not the declared
  no-fire value. That value is brought down by the de-rating the
  programme applies before it becomes the demonstration threshold, so
  the separation is shown against the de-rated value and not against
  the raw one. Where the induced quantity is a radio-frequency power
  rather than a current, the no-fire current is carried across through
  the bridgewire resistance by the square law before the two are
  compared on one scale.
- The decibel conversion follows the quantity. A field quantity --
  an induced current, an induced voltage -- goes as twenty times the
  logarithm of the ratio; an energy quantity -- an induced power --
  goes as ten times. Using one law for both halves or doubles every
  separation reported.
- A separation is only meaningful next to the operating condition it
  was shown under. The mandated set for a firing circuit covers the
  keyed flight transmitters, the launch-site radiated environment, the
  worst-case harness routing and the connected ground support
  equipment; a condition that was never exercised is a gap in the
  demonstration, not a silent pass. The condition that governs is the
  one with the smallest separation, with the condition name as the
  tie-break so the answer does not depend on record order.
- A negative separation is a real and serious result: the induced
  level already sits above what the circuit tolerates. It is a
  finding, never an input error.

## Workflow

1. Normalise each circuit record: reject an empty identifier, an
   unknown category, an unknown evidence kind, an unknown induced
   quantity, a missing measurement list, a measurement with no
   operating condition, a repeated condition and a non-positive
   induced level. Reject a record that declares both a decibel
   threshold and a raw no-fire value, and one that declares neither.
2. Read the demanded separation for the circuit's category from the
   programme ladder, defaulting to the standard ladder when the
   project tailors nothing.
3. Check the evidence kind against what the category admits, and raise
   a finding where a firing circuit rests on anything but instrumented
   measurement.
4. Derive the demonstration threshold: de-rate the declared no-fire
   value, and where the comparison is on power, carry the no-fire
   current across through the bridgewire resistance first.
5. Compute the separation at every exercised condition with the law
   the induced quantity obeys, or as a straight difference when both
   levels are already on the decibel scale.
6. List the mandated operating conditions that were never exercised.
7. Take the governing condition as the smallest separation and compare
   it against the demand, absorbing the representation error a decibel
   difference carries.
8. The circuit is demonstrated only when the evidence kind, the
   condition coverage and the governing separation all hold.

## Pitfalls

- Demonstrating a firing circuit by similarity to a unit that flew
  before. The demand is on this harness, this routing and this
  bonding; the earlier unit demonstrates its own installation and
  nothing else.
- Measuring against the raw no-fire value. The de-rating is what turns
  a device parameter into a demonstration threshold, and skipping it
  reports a separation the circuit does not have.
- Applying the twenty-times law to an induced power, or the ten-times
  law to an induced current. Every separation in the report is then
  wrong by a factor of two in decibels, in whichever direction
  flatters the result.
- Reporting the mean or the first separation instead of the smallest.
  The demonstration is only as good as its worst exercised condition.
- Comparing the demonstrated separation against the demand with a bare
  greater-or-equal test. The separation is a difference of decibel
  levels and a case that sits exactly on the demand in engineering
  terms can land a few units in the last place below it: 33.3 less
  13.3 yields 19.999999999999996, not 20. Absorb that representation
  error in the comparison; never lower the demanded separation to make
  the case pass.
- Treating an unexercised condition as a pass because nothing was
  measured there. A condition nobody ran is the condition most likely
  to be the governing one.
- Reading a negative separation as a broken measurement. It says the
  environment already exceeds the circuit's tolerance, which is the
  most important result the demonstration can produce.

## Behavior contract (gate 3)

The category ladder lookup, evidence admissibility, no-fire de-rating,
bridgewire power conversion, quantity-dependent decibel laws,
per-condition separation, mandated-condition coverage, governing-case
selection, tolerance-absorbing demand comparison and the aggregate
review are exercised by the gate 3 contract test:
scripts/test_e20_eed_circuit_safety_margin_demonstration.py against
scripts/e20_eed_circuit_safety_margin_demonstration_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_eed_circuit_safety_margin_demonstration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

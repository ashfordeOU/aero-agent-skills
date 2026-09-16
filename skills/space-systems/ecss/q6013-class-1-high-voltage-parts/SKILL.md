---
name: q6013-class-1-high-voltage-parts
description: "Use when a high voltage or microwave commercial part has to be dispositioned. Evaluate whether a commercial part serving a high voltage or high power microwave function is fit for class 1 use under ECSS-Q-ST-60-13C clause 4.6.7: refuse an application with no manufacturer, part number or declared service category, hold applied voltage to its category derating ceiling with equality admissible under a named tolerance, judge the microwave power margin in decibels against a required floor, require a declared mitigation where an unsealed part stays energized through the low pressure discharge band, and name every absent category screening step. Trigger: ecss, q-st-60-13c-clause-4-6-7, class-1-high-voltage-part-application, high-voltage-derating-ceiling, microwave-multipaction-margin-db, corona-discharge-band-mitigation, high-voltage-conditioning-screening."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-high-voltage-parts, q-st-60-13c-clause-4-6-7, class-1-high-voltage-part-application, high-voltage-derating-ceiling, microwave-multipaction-margin-db, corona-discharge-band-mitigation, high-voltage-conditioning-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 Commercial Parts — High Voltage and High Power Microwave Parts (space-systems/ecss/q6013-class-1-high-voltage-parts)

Use when the task is the high voltage and high power microwave provision of
ECSS-Q-ST-60-13C clause 4.6.7 — the extra conditions a commercial electrical,
electronic and electromechanical part has to meet when the function it serves
puts it under high voltage stress or high radio-frequency power, at the
highest assurance level.

## Domain quick reference

- The two services are not one service. A high voltage part fails through its
  insulation and its surrounding gas; a high power microwave part fails
  through an electron avalanche between its own surfaces. They carry different
  ceilings and different screening, so the service category is declared first
  and everything downstream is read against it.
- Voltage derating here is a ratio, applied over rated, and the ceiling sits
  far below the rating because a part run near its rating ages its insulation
  rather than merely working hard. A part landing exactly on the ceiling is
  admissible; that equality is a representation question about two measured
  values, absorbed by a named tolerance rather than by moving the ceiling.
- A project may tighten the ceiling for its own reasons. It may not loosen it,
  so a declared ceiling wider than the category default is an input error and
  not a finding to be argued at the review.
- Microwave margin is stated in decibels because the quantity that matters is
  the ratio of the threshold power to the applied peak power, not their
  difference. A margin is derived from a logarithm, so an exactly-met floor
  again lands within representation error of the floor.
- Pressure is a schedule, not a state. A part that is safe in vacuum and safe
  at the pad can still sit in the band where a gas discharge starts most
  easily while it passes through it, so what matters is the pressures the part
  is energized at, and whether a sealed, encapsulated or pressurized
  construction, or being held de-energized, covers that passage.
- Screening for these parts adds steps the ordinary flow does not have:
  conditioning at voltage or at power, and a measurement that would see a
  discharge or an avalanche starting. An absent step is a coverage shortfall,
  not a step that passed.

## Workflow

1. Validate the part identity — manufacturer, part number and service
   category — and reject an unrecognized category rather than defaulting it.
2. Compute the applied-to-rated voltage ratio, apply the category ceiling or a
   tighter declared one, and take an exactly-met ceiling as admissible under
   the named tolerance.
3. For microwave service in vacuum, convert applied peak power and threshold
   power into a decibel margin and compare it with the required floor, again
   with the boundary taken under the tolerance. Record an absent power-margin
   assessment as its own finding.
4. Collect the pressures at which the part is energized, mark those inside the
   discharge-prone band, and require a recognized mitigation when any are
   marked.
5. Compare the declared screening steps with the steps the category requires
   and name each absent one.
6. Report the derating record, the power-margin record, the discharge record,
   the absent screening steps and a verdict carrying every finding.

## Pitfalls

- Carrying one derating ceiling across both services. The microwave and high
  voltage ceilings are set by different failure mechanisms, and forcing one
  onto the other either over-restricts a design or under-protects it.
- Loosening the ceiling to make an existing design close. A wider ceiling is
  an input error here; the design closes by lowering the applied stress or by
  selecting a higher rated part.
- Comparing powers in watts and calling the difference a margin. The mechanism
  responds to the ratio, so a margin quoted in watts hides how close a design
  actually is at low power and overstates it at high power.
- Reading pressure as a single number. A part qualified in vacuum and at sea
  level may still be energized through the band in between, which is exactly
  where a discharge is easiest to start.
- Treating an unrun screening step as a clean step. A part with no discharge
  measurement has no discharge findings, and that is a coverage shortfall that
  has to be named before any verdict is formed.
- Stopping at the first finding. The part engineer needs the whole list to
  plan one repeat round rather than discovering the next shortfall after it.

## Behavior contract (gate 3)

The identity and service-category validation, derating ratio and ceiling
comparison, decibel power margin, discharge-band exposure and mitigation
check, screening-step coverage and the overall fitness verdict are exercised
by the gate 3 contract test:
scripts/test_q6013_class_1_high_voltage_parts.py against
scripts/q6013_class_1_high_voltage_parts_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_1_high_voltage_parts.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

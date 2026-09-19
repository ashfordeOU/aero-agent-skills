---
name: e2021-recurrent-actuator-firing-targets
description: "Derive the firing figures a recurrent actuator product has to publish under ECSS-E-ST-20-21C clause 5.6.3: bound the measured population with the worst unit's all-fire current and the lowest unit's no-fire current, grade the separation those two leave for the firing and the inhibit circuit, size the drive current the design factor demands of the bus, and set the minimum actuation duration from the mechanism function time against the product floor. Use when a reusable actuator is being specified for more than one programme. Trigger: ecss, e-st-20-electrical-scope, recurrent-actuator-firing-targets, published-all-fire-current, population-no-fire-current, minimum-actuation-duration, firing-band-separation, firing-circuit-design-factor."
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
  tags: [ecss, e-st-20-electrical-scope, e2021-recurrent-actuator-firing-targets, recurrent-actuator-firing-targets, published-all-fire-current, population-no-fire-current, minimum-actuation-duration, firing-band-separation, firing-circuit-design-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuators — Recurrent Actuator Firing Targets (space-systems/ecss/e2021-recurrent-actuator-firing-targets)

Use when the task is the recommended-figure duty of ECSS-E-ST-20-21C
clause 5.6.3 -- fixing the all-fire current and the minimum actuation
duration a reusable actuator product publishes, so the same part can be
bought into the next programme without a fresh characterisation.

## Domain quick reference

- A recurrent product's published figures are population figures, not
  one unit's measurements. The published all-fire current is the
  HIGHEST all-fire seen across the lot, because a figure only the best
  unit meets is a measurement and not a specification. The published
  no-fire current is the LOWEST no-fire seen, read the same way from
  the safety side.
- The two published currents bound a band that two independent circuits
  have to fit inside. The firing circuit is designed above all-fire
  with a design factor so the worst unit still actuates at end of life
  and at cold bus; the inhibit and monitoring circuits are designed
  below no-fire so no credible stray current actuates the best unit. A
  population whose band is narrow leaves no room for either, and the
  fix is screening the lot, not shaving the factor.
- The design factor turns the published all-fire into a demand on the
  bus. That demand is what makes the product reusable or not: an
  actuator whose firing circuit needs more than the platform can source
  is a redesign, and the check belongs at catalogue time rather than at
  the first integration.
- The same design current can also run past the actuator's own maximum
  rating. All-fire and maximum rating are different figures, and a
  factor applied blindly can specify a firing circuit the part cannot
  survive.
- The minimum actuation duration is the mechanism function time carried
  with a margin factor, floored by a product minimum. The floor governs
  fast mechanisms, where the command and telemetry chain, not the
  mechanism, sets the shortest sensible command. A command shorter than
  the published minimum leaves the actuator part-actuated, which is the
  state neither the fired nor the unfired analysis covers.

## Workflow

1. Assemble the measured population, one entry per unit with its
   no-fire and all-fire current. Reject a unit whose no-fire is not
   strictly below its all-fire, and reject a repeated unit identifier,
   because both corrupt the bounds silently.
2. Take the published pair from the population: the highest all-fire
   and the lowest no-fire. Report the unit count alongside, since a
   bound taken from one unit is not a population bound.
3. Compute the separation ratio and name the regime. An insufficient
   band is a finding against the product, not against the programme
   that later buys it.
4. Size the required drive current from the published all-fire and the
   design factor, then compare it against what the bus can supply and
   against the actuator's own maximum current rating. Refuse a design
   factor below unity.
5. Set the recommended minimum actuation duration from the function
   time and the margin factor, floored by the product minimum, and
   record which of the two terms governs.
6. Grade any declared catalogue targets and any commanded duration
   against these derived figures, absorbing representation error in the
   comparison and never widening the target itself.

## Pitfalls

- Publishing the mean or the first article's all-fire current. Half the
  lot then sits above the published figure, and the firing circuit
  designed from it will not actuate those units at the cold end.
- Reading no-fire as "the current at which it does not fire". It is the
  current the product must tolerate WITHOUT actuating, so the bound
  comes from the most sensitive unit, never the most robust one.
- Trimming the design factor to make a marginal bus fit. The factor
  covers temperature, ageing and bus droop at the moment of firing; a
  narrow band is a screening problem and the factor is not where it is
  paid for.
- Applying the design factor without checking the part's maximum
  rating. The firing circuit can then be specified to deliver a current
  that damages the actuator it is meant to drive.
- Publishing the mechanism function time as the minimum actuation
  duration. The command has to carry a margin over it and never fall
  below the product floor, or a short command leaves the mechanism
  part-travelled with no defined end state.

## Behavior contract (gate 3)

The population bounding, separation grading, drive-current sizing,
duration floor, catalogue-target comparison and command-duration check
are exercised by the gate 3 contract test:
scripts/test_e2021_recurrent_actuator_firing_targets.py against
scripts/e2021_recurrent_actuator_firing_targets_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2021_recurrent_actuator_firing_targets.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

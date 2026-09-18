---
name: e2020-lcl-limitation-mode-rating-limits
description: "Evaluate whether an LCL or HLCL pass element stays inside its component ratings while it holds current limitation. Use when a limiter branch is assessed against ECSS-E-ST-20-20C clause 5.2.3.4.1: confirm the demand really drives limitation, take the voltage the element stands off and the limited current it carries, compute the dissipation and the energy over the trip-off delay, raise the junction through the transient thermal path, and compare current, voltage and junction against derated ratings and the pulse safe operating area boundary. Trigger: ecss, e-st-20-20c-clause-5-2-3-4-1, lcl-current-limitation-mode, pass-element-dissipation, trip-off-delay-energy, transient-junction-temperature-rise, pulse-safe-operating-area, power-component-derating-limits."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e2020-lcl-limitation-mode-rating-limits, lcl-current-limitation-mode, pass-element-dissipation, trip-off-delay-energy, transient-junction-temperature-rise, pulse-safe-operating-area, power-component-derating-limits]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply Interfaces -- Ratings in Current Limitation Mode (space-systems/ecss/e2020-lcl-limitation-mode-rating-limits)

Use when the task is clause 5.2.3.4.1 of ECSS-E-ST-20-20C -- the state a
latching current limiter or a heater latching current limiter enters
when the branch demands more than the limit. The pass element leaves
saturation, holds the current at the limit value, and stands off
whatever the load has pulled the output down by. It stays there for the
whole trip-off delay, and the clause is about what that does to the
part.

## Domain quick reference

- Switch mode and limitation mode are different duty cases for the same
  element. Saturated, it drops a fraction of a volt and dissipates
  almost nothing. In limitation it is a linear element carrying the
  full limited current with most of the bus across it, so the
  dissipation jumps by orders of magnitude for the length of the delay.
- The dissipation is the stood-off voltage times the limited current,
  and the energy is that power over the whole trip-off delay. The worst
  case is a hard short, where the output collapses and the element
  stands off the entire bus.
- The junction rise is not the steady-state one for a short event. A
  single-pole thermal path warms towards its steady resistance with a
  time constant, so a millisecond delay sees a small fraction of it and
  a multi-second delay sees effectively all of it. Using the steady
  figure for a short delay condemns a sound design; using it for a long
  one is the same error in the dangerous direction.
- Three ratings apply at once and none of them is the datasheet
  maximum. Current, voltage and junction temperature all carry a
  derating factor. The junction factor is applied to the allowed rise
  above the mounting reference rather than to a reading in degrees,
  because the rise is the physical quantity being limited.
- The safe operating area is a fourth limit and the one most often
  missed. At a given stood-off voltage the element has a
  pulse-duration-dependent current ceiling far below its d.c. rating,
  and a boundary drawn for one pulse length says nothing about another.
  A stood-off voltage outside the span of the curve in hand is a
  missing input, not a number to extrapolate.

## Workflow

1. Confirm the condition is a limitation event at all: a demand at or
   below the limit leaves the device in switch mode, and this
   assessment does not describe it.
2. Take the stood-off voltage as bus minus output, refusing an output
   above the bus, and multiply by the limited current for the
   dissipation.
3. Multiply by the trip-off delay for the energy the element absorbs
   before the device latches off.
4. Compute the thermal impedance the path presents for a pulse of that
   length, then the junction temperature above the mounting reference.
5. Derate the current and voltage ratings by their factors, and derate
   the allowed junction rise rather than the junction reading.
6. Compare the limited current, the stood-off voltage and the junction
   temperature against those three limits, absorbing representation
   error in each comparison without relaxing the limit.
7. Read the safe operating area boundary at the stood-off voltage for
   this pulse length and compare the limited current against it;
   report a voltage outside the curve span as a missing boundary.
8. Close with a verdict that stays open while any finding stands.

## Pitfalls

- Sizing the pass element from its switch-mode duty. The conduction
  loss in switch mode is milliwatts and the limitation-mode loss is
  tens of watts in the same part; only the second one sets the
  junction.
- Using the steady-state thermal resistance for a short trip-off
  delay. The part never reaches that rise, and the design gets
  rejected for a temperature it cannot arrive at.
- Using the same steady-state figure for a long delay without checking
  the time constant, which is the same mistake pointing the other way.
- Derating a junction temperature by multiplying the Celsius reading.
  The result depends on the unit the number happens to be written in;
  the factor belongs on the rise above the mounting reference.
- Reading a safe operating area boundary drawn for a different pulse
  length. The ceiling moves by a large factor between a millisecond
  and a second, and nothing on the plot says which one is in hand.
- Extrapolating the boundary past the end of the curve. Beyond the
  plotted span the limit is unknown, and an unknown limit is a
  finding, not a value.
- Comparing a computed dissipation or junction temperature against a
  ceiling by bare arithmetic. Both are products of floats that can land
  a few units in the last place either side of a limit written in
  another unit, so the comparison absorbs that error while the limit
  itself is never relaxed.

## Behavior contract (gate 3)

The mode decision, stood-off voltage, dissipation and energy, transient
thermal impedance, junction temperature, derated current, voltage and
junction limits, safe operating area span, coverage and boundary
interpolation are exercised by the gate 3 contract test:
scripts/test_e2020_lcl_limitation_mode_rating_limits.py against
scripts/e2020_lcl_limitation_mode_rating_limits_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_lcl_limitation_mode_rating_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

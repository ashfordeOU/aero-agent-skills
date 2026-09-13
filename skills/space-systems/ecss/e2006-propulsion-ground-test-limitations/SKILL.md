---
name: e2006-propulsion-ground-test-limitations
description: "Use when establish the vacuum-chamber effects that distort a ground firing of an electric-propulsion thruster and their influence on the measured results, under ECSS-E-ST-20-06C clause 11.3.1: derive the facility background-pressure from propellant mass-flow and pumping-speed, size the pumping-speed a target background-pressure demands, quantify the charge-exchange enhancement along the plume path, decide whether the chamber wall intercepts the divergence-cone, estimate back-sputtered wall-material deposition, categorize every effect into its facility family, and confirm each one carries a stated magnitude, a named influenced-quantity and either a correction-factor or a justified negligibility before the ground result is read as flight-representative. Trigger: ecss, e-st-20-electrical-scope, ground-test-limitations, vacuum-chamber-effects, background-pressure, charge-exchange-enhancement, back-sputtered-deposition, pumping-speed-sizing, facility-correction-factor."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-propulsion-ground-test-limitations, vacuum-chamber-effects, background-pressure, charge-exchange-enhancement, back-sputtered-deposition, facility-correction-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electric Propulsion — Ground Test Limitations (space-systems/ecss/e2006-propulsion-ground-test-limitations)

Use when the task is the clause 11.3.1 obligation of ECSS-E-ST-20-06C: a
ground firing of an electric-propulsion thruster happens inside a vacuum
chamber, the chamber changes what is measured, and the effects together with
their influence on the result have to be established before the measurement
is carried into the flight case.

## Domain quick reference

- Facility effects fall into four families that must each be covered, plus an
  optional thermal family. Pressure-driven effects come from the residual gas
  the pumps cannot remove (elevated background-pressure, charge-exchange
  enhancement). Wall-material effects come from the chamber surfaces
  themselves (back-sputtered wall-material, wall-erosion contamination).
  Electrical-boundary effects come from the chamber being a large grounded
  conductor (potential clamping of the article, an artificial current-return
  path that no free-flying spacecraft has). Geometric-truncation effects come
  from a finite chamber intercepting a plume that would otherwise expand
  without limit.
- Background-pressure is not a facility property in isolation: it is the
  propellant throughput divided by the pumping-speed at the operating
  temperature, so a higher mass-flow raises it linearly and a larger pump
  lowers it. The same relation inverted sizes the pumping-speed that a target
  background-pressure demands, which is how a facility is judged adequate for
  a given thruster before the campaign rather than after it.
- Charge-exchange enhancement follows from the residual-gas number-density,
  the exchange cross-section and the path length as an exponential attenuation
  law. It is the mechanism that makes a ground plume look broader and more
  charge-exchange-rich than the flight plume, so it is the effect most often
  mistaken for thruster behaviour.
- An effect is established only when three things are on record: its
  magnitude, the quantity it influences, and the disposition — either a
  correction-factor applied to the measurement or a justified statement that
  the relative influence is within the agreed negligibility tolerance.
  Naming an effect without a magnitude, or with a magnitude but no influenced
  quantity, is an open item, not a covered one.

## Workflow

1. Compute the facility background-pressure from propellant mass-flow,
   species mass, gas temperature and pumping-speed; compare it against the
   facility limit declared for the campaign, and where it exceeds, size the
   pumping-speed the limit would have demanded.
2. Derive the residual-gas number-density and the charge-exchange fraction
   over the plume path length at the exchange cross-section.
3. Check the geometry: project the plume divergence-cone at the axial
   distance to the wall and decide whether the cone is contained by the
   chamber radius or truncated by it; a cone whose edge exactly grazes the
   wall is contained.
4. Estimate the back-sputtered wall-material flux from beam current, sputter
   yield, target atom mass, the return fraction and the chamber radius.
5. Categorize every declared effect into its facility family and list the
   required families with no effect covering them.
6. For each effect check that magnitude, influenced-quantity and disposition
   are all present; accept a negligibility claim only when the relative
   influence is at or within the tolerance, and accept a correction only with
   a positive factor.
7. Apply the accepted correction-factors to the measured quantity; the ground
   result is flight-representative only when no family is uncovered and no
   effect is left uncorrected and non-negligible.

## Pitfalls

- Reporting a background-pressure measured with the thruster off. The number
  that matters is the operating-point pressure set by the propellant
  throughput against the pumping-speed, and a base pressure taken cold
  understates it by orders of magnitude.
- Treating the chamber wall as an innocuous boundary. It is a grounded
  conductor that clamps the article's potential and supplies a current-return
  path, so every potential and current measured against it is a facility
  artefact until the electrical-boundary effect is established.
- Declaring an effect "known" with a magnitude but no influenced-quantity.
  Clause 11.3.1 asks for the influence on the result, so a magnitude without
  the quantity it moves leaves the requirement open.
- Accepting a correction-factor of zero or a negative one to force agreement
  with a prediction: a correction scales a measurement, and a non-positive
  scale is a modelling error, rejected at input.
- Widening the negligibility tolerance so a marginal effect passes. A relative
  influence that equals the tolerance to within the named representation
  tolerance is accepted by absorbing floating-point error, never by moving the
  agreed limit.

## Behavior contract (gate 3)

The background-pressure, pumping-speed sizing, charge-exchange, wall
interception, back-sputtered deposition, effect categorization and
establishment logic is exercised by the gate 3 contract test:
scripts/test_e2006_propulsion_ground_test_limitations.py against
scripts/e2006_propulsion_ground_test_limitations_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_propulsion_ground_test_limitations.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

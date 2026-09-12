---
name: e20-radio-frequency-compatibility
description: "Use when verify that every antenna-connected unit on a spacecraft coexists with the rest of the vehicle against the mission performance criteria of ECSS-E-ST-20C clause 6.3.6: categorize each unit as transmitter, receiver or transceiver, propagate transmit power to a victim input through antenna-to-antenna isolation and front-end rejection, generate the intermodulation products of every emitter pair and report those landing inside the victim receive band, check the interference margin against the victim susceptibility threshold, and convert the summed coupled power into a noise-floor rise judged against the mission budget. Trigger: ecss, e-st-20c-clause-6-3-6, radio-frequency-compatibility, antenna-to-antenna-isolation, intermodulation-product-screening, receiver-susceptibility-threshold, noise-floor-degradation-budget, transmitter-filter-rejection."
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
  tags: [ecss, e-st-20-electrical-scope, e20-radio-frequency-compatibility, radio-frequency-compatibility, antenna-to-antenna-isolation, intermodulation-product-screening, receiver-susceptibility-threshold, noise-floor-degradation-budget, transmitter-filter-rejection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Radio Frequency Compatibility (space-systems/ecss/e20-radio-frequency-compatibility)

Use when the task is the clause 6.3.6 radio frequency compatibility
case of ECSS-E-ST-20C -- showing that every unit hanging off an antenna
can operate with every other one, and judging the result against what
the mission needs rather than against a generic emission limit.

## Domain quick reference

- Each antenna-connected unit carries one role: it puts power into an
  antenna, it takes power out of one, or it does both. The role decides
  which side of the assessment the unit can appear on. A unit that only
  transmits cannot be a victim, and a unit that only receives cannot be
  an aggressor; a scenario that places one on the wrong side is a
  finding about the scenario, and the numbers computed from it mean
  nothing.
- Power reaches a victim by two losses in series. Antenna-to-antenna
  isolation covers the path between the two apertures on the structure.
  Front-end rejection covers what the victim's own filtering removes at
  the aggressor's frequency. Both are losses, both subtract from the
  transmit power in decibels, and the result is the power actually
  presented at the victim input.
- Two aggressors present a third mechanism. Any pair of emitters
  produces intermodulation at integer combinations of their
  frequencies, and the combinations whose coefficients sum to a low
  order are the ones with enough energy to matter. A product landing
  inside the victim receive band cannot be filtered away by the victim,
  because it is already in band, so it is reported as a finding on the
  pair rather than on either emitter.
- Two judgements follow, and they answer different questions. The
  per-emitter interference margin is the distance between the victim
  susceptibility threshold and the power one aggressor delivers, and it
  asks whether any single unit disturbs the victim. The noise-floor
  rise is the decibel increase once every coupled contribution sums in
  linear power on top of the victim's own noise, and it asks whether
  the mission still closes. A set of emitters can each hold margin and
  still push the aggregate noise floor past the budget.
- The mission budget is what the clause judges against. A degradation
  of a fraction of a decibel is meaningful for a command receiver and
  irrelevant elsewhere, so the budget is carried per victim rather than
  fixed for the spacecraft.

## Workflow

1. Categorize the victim and every emitter, and reject a scenario
   where the victim cannot receive or an emitter cannot transmit.
2. For each emitter, subtract the antenna-to-antenna isolation and the
   victim front-end rejection from the transmit power to get the
   coupled power at the victim input.
3. Take the interference margin as the victim susceptibility threshold
   less that coupled power, and flag a margin below the requirement.
4. For every emitter pair, generate the intermodulation products up to
   the chosen order and keep those inside the victim receive band,
   edges included.
5. Sum all coupled contributions in linear power and convert to the
   decibel rise of the victim noise floor.
6. Compare the rise against the mission degradation budget for that
   victim and flag an exceedance.
7. Aggregate the role, coupling, intermodulation and performance
   findings; the victim is compatible only when all four lists are
   empty.

## Pitfalls

- Adding isolation as a gain because the interfering signal travels
  from a stronger unit. Isolation and rejection are both losses; a
  sign slip there moves the coupled power by twice the isolation and
  turns a comfortable case into an apparent catastrophe or the
  reverse.
- Judging each emitter against the susceptibility threshold and
  stopping there. The mission criterion is the aggregate noise floor,
  and a fleet of individually compliant emitters can still close the
  link budget out.
- Screening only the second-order difference. Odd higher-order products
  are the ones that habitually land in band on a spacecraft with a
  transmit and a receive band close together, and a screen that stops
  at order two will miss them.
- Ignoring a product that lands on a band edge. The edge is inside the
  band for this purpose, and a product frequency is built from
  multiples and sums that can land a few representation units on
  either side of an edge it physically sits on -- the equality is
  absorbed in the comparison rather than by widening the band.
- Treating a transceiver as one role. It is an aggressor and a victim
  in the same assessment, and leaving it out of one side hides half
  its coupling.
- Adding interference powers in decibels. Uncorrelated contributions
  sum in linear power; adding the decibel values produces a number
  with no physical meaning that is wrong by tens of decibels.

## Behavior contract (gate 3)

The role categorization, coupled-power, interference-margin,
intermodulation-product, band-screening and noise-floor-degradation
logic is exercised by the gate 3 contract test:
scripts/test_e20_radio_frequency_compatibility.py against
scripts/e20_radio_frequency_compatibility_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_radio_frequency_compatibility.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2001-discharge-and-event-definitions
description: "Use when determine whether an observation logged during a multipactor-qualification run of ECSS-E-ST-20-01C clause 8.5.1 is an event, a gas-discharge or true multipactor before any result is judged: confirm that at least one detection-channel crossed its declared trip-threshold, place the run in the high-vacuum-regime or the residual-gas-regime from the chamber-pressure reading, evaluate the frequency-gap-product against the susceptibility-band, weigh the power-threshold behaviour and the extinction-on-power-reduction against the pressure-sensitivity of the observation, and categorize every logged observation as multipactor, gas-discharge, undetermined-event or no-event so that no threshold-crossing is judged away unrecorded. Trigger: ecss, e-st-20-electrical-scope, e2001-discharge-and-event-definitions, multipactor-event-definition, gas-discharge-categorization, detection-channel-threshold-crossing, frequency-gap-product, high-vacuum-regime, undetermined-event."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-discharge-and-event-definitions, multipactor-event-definition, gas-discharge-categorization, detection-channel-threshold-crossing, frequency-gap-product, high-vacuum-regime]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Discharge and Event Definitions (space-systems/ecss/e2001-discharge-and-event-definitions)

Use when the task is judging the outcome of a multipactor-qualification run
against the term definitions recalled by ECSS-E-ST-20-01C clause 8.5.1 --
deciding, for every observation written into the run log, whether it is an
event, a gas-discharge, or true multipactor, before any pass or fail
statement about the unit is made.

## Domain quick reference

- The three terms are nested, not interchangeable. An *event* is the widest
  term: any excursion on a monitored detection-channel that reaches or
  crosses the trip-threshold declared for that channel in the procedure. It
  records that a deviation happened; it says nothing yet about the physics
  behind it.
- A *gas-discharge* is the sub-case in which the excursion is produced by
  ionisation of residual gas in the fixture -- a corona or arc path. Its
  signature is pressure-sensitivity: the excursion tracks the
  chamber-pressure reading, it appears once the fixture leaves the
  high-vacuum-regime (outgassing burst, incomplete pump-down, a leak), and
  reducing the drive alone does not reliably clear it.
- *Multipactor* is the sub-case in which the excursion is produced by
  resonant secondary-electron-multiplication between surfaces in vacuum. Its
  signature is a power-threshold: the excursion appears above an onset level,
  extinguishes when the drive is taken back below that onset, and returns at
  a repeatable onset level. It also needs the geometry to sit inside the
  susceptibility-band of the frequency-gap-product -- the product of drive
  frequency and gap dimension, handled here in GHz-mm.
- An observation that crosses a threshold but matches neither signature, or
  matches both at once, is an *undetermined-event*. It stays in the record as
  an event; it is never renamed to "no event" because the physics was not
  resolved.
- The chamber-pressure reading places the run in one of three regimes:
  high-vacuum (secondary-electron-multiplication is the credible mechanism),
  residual-gas (ionisation is the credible mechanism), and a transition band
  between them where both mechanisms are live and the discriminators decide.

## Workflow

1. Validate every observation before reading it: a non-empty identifier, a
   non-empty channel map with a numeric reading and a numeric trip-threshold
   per channel, a positive chamber-pressure, a positive drive frequency and a
   positive gap dimension, and boolean discriminator flags. Reject a
   malformed observation instead of guessing a default.
2. Collect the crossed channels. A reading at exactly its trip-threshold is a
   crossing -- readings summed from several sensor terms land a few units in
   the last place either side of the declared limit, so the comparison
   absorbs the representation error rather than moving the limit.
3. With no crossed channel the observation is *no-event*: nothing was
   detected and nothing is categorized. With one or more crossed channels the
   observation is an event, and stays one for the rest of the procedure.
4. Place the run in its pressure-regime from the chamber-pressure reading,
   and compute the frequency-gap-product from the drive frequency and the gap
   dimension; check it against the susceptibility-band.
5. Apply the two signatures. The multipactor signature needs the
   high-vacuum-regime or the transition band, a frequency-gap-product inside
   the susceptibility-band, extinction when the drive drops below the onset,
   and a repeatable onset. The gas-discharge signature needs
   pressure-sensitivity with the run outside the high-vacuum-regime. In the
   transition band both signatures can be met at once.
6. Categorize: exactly one signature met gives that category; neither met, or
   both met at once, gives *undetermined-event*. Record the reasons that
   drove the decision alongside the category.
7. Summarise the run: counts per category, the reportable events, and whether
   any undetermined-event remains. A run holding an undetermined-event is not
   ready to be judged -- the record is incomplete, not clean.

## Pitfalls

- Calling every excursion "a discharge" in the log. Clause 8.5.1 exists
  because the three words carry different evidential weight, and a
  gas-discharge attributed to the unit as multipactor caps the declared
  drive level for no reason -- while the reverse hides a real susceptibility.
- Reading "no multipactor signature" as "no event". The event is the
  threshold-crossing itself; failing to resolve its mechanism produces an
  undetermined-event, which is a finding that must survive into the report.
- Skipping the frequency-gap-product check because the excursion looked
  drive-dependent. A geometry far outside the susceptibility-band makes the
  multipactor reading implausible and points back at the fixture.
- Judging a transition-band run as if it were high-vacuum. Between the two
  regime limits both mechanisms are credible, so a single discriminator is
  not enough and the observation stays undetermined until conditions are
  tightened.
- Treating a channel reading that equals its trip-threshold as clean. The
  declared limit is inclusive; absorbing floating-point error is right,
  widening the limit is not.

## Behavior contract (gate 3)

The observation validation, threshold-crossing collection, pressure-regime
placement, frequency-gap-product band check, categorization and run-summary
logic is exercised by the gate 3 contract test:
scripts/test_e2001_discharge_and_event_definitions.py against
scripts/e2001_discharge_and_event_definitions_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_discharge_and_event_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

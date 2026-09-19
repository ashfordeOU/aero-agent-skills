---
name: q6015-single-event-effects-assurance
description: "Assess whether a part's single event susceptibility is survivable in its mission. Use when ECSS-Q-ST-60-15C clause 5.3 has to be applied to test data: separate recoverable upsets, transients and functional interrupts from the destructive latchup, burnout and gate rupture, read the integral flux at the part's linear-energy-transfer threshold, turn saturated cross-section and device count into an event rate against the system budget, and for a destructive event not excluded by threshold check the latchup current limiter trip level and speed or the burnout voltage derating. Trigger: ecss, q-st-60-15c-clause-5-3, single-event-effects-assurance, linear-energy-transfer-threshold, single-event-upset-rate-budget, single-event-latchup-current-limiter, single-event-burnout-derating, destructive-event-exclusion."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-single-event-effects-assurance, q-st-60-15c-clause-5-3, linear-energy-transfer-threshold, single-event-upset-rate-budget, single-event-latchup-current-limiter, single-event-burnout-derating, destructive-event-exclusion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Single Event Effects (space-systems/ecss/q6015-single-event-effects-assurance)

Use when the task is the single event part of ECSS-Q-ST-60-15C clause
5.3 — turning a part's linear-energy-transfer threshold and cross-
section into a statement about the mission, and deciding whether the
events that would destroy the part have actually been shut out.

## Domain quick reference

- Single event effects split by consequence, and the split decides the
  method. An upset, a transient or a functional interrupt costs time
  and data, so it is budgeted: a rate the system can carry. A latchup,
  a burnout or a gate rupture costs the part, so there is no rate low
  enough — it has to be excluded or stopped by hardware.
- The environment is an integral linear-energy-transfer spectrum: how
  many particles per area per second can deposit at least a given
  linear energy transfer. Its top point is the cut-off the tabulation
  was carried to, so a threshold above that point is exposed to
  nothing and the event is excluded on threshold alone.
- The recoverable rate is the integral flux at the threshold times the
  saturated cross-section times the number of devices. Mitigation does
  not move the threshold or the cross-section; error detection and
  correction, or a redundant arrangement, divides the rate the system
  sees, which is a different and weaker claim.
- Mitigation has to address the event it is put against. Error
  correction does nothing about a latchup, and a current limiter does
  nothing about an upset, so a mitigation of the wrong kind is a
  finding even when the arithmetic downstream of it looks healthy.
- A latchup current limiter is two requirements, not one. It has to
  trip below the current that destroys the part, and it has to detect
  and remove power inside the time the part survives the latched
  state. A limiter that meets one and not the other does not protect.
- A burnout or gate rupture is mitigated by derating: the applied
  voltage is held at or under the voltage the part was demonstrated
  safe at in test. Equality is compliance — the demonstrated voltage
  is a level that was shown safe, not a level that was shown to fail.

## Workflow

1. Validate the spectrum: at least two points, linear energy transfer
   strictly ascending, integral flux positive and strictly falling,
   and a total fall large enough that the tabulation has reached a
   cut-off rather than stopping mid-slope.
2. Validate each part-event: a known event type, a positive threshold,
   and for a recoverable event a positive saturated cross-section and
   an integer device count.
3. Compare the threshold with the environment cut-off. A threshold at
   or above it excludes the event; record the exclusion rather than
   carrying a zero rate forward silently.
4. For a recoverable event, read the integral flux at the threshold by
   log-log interpolation, refusing a threshold below the tabulated
   span, and form the rate per day over the device population.
5. Apply any declared reduction factor, then compare the rate with the
   budget, letting an exact equality pass under a named relative
   tolerance.
6. For a destructive event that was not excluded, require a mitigation
   of a kind that addresses it, then check that kind's own conditions:
   trip current below the destructive current and detection inside the
   survivable duration, or applied voltage at or under the
   demonstrated safe voltage.
7. Report per-event rate, exclusion, mitigation kind and findings, the
   summed recoverable rate, and one equipment verdict.

## Pitfalls

- Budgeting a destructive event. A latchup rate of one per decade is
  still a dead part; the destructive events are excluded or mitigated,
  never averaged into an availability figure.
- Reading the flux at the saturated cross-section's own linear energy
  transfer rather than at the threshold. The threshold is where events
  start; using the saturation point understates the rate heavily.
- Treating error correction as raising the threshold. It divides the
  rate the system sees and leaves the part exactly as susceptible,
  which matters the moment the correction itself is unavailable.
- Accepting a current limiter on its trip level alone. Tripping below
  the destructive current is worthless if it happens after the part
  has already been in latchup longer than it survives.
- Failing a derating that sits exactly on the demonstrated safe
  voltage. That level was shown safe; the equality is a representation
  question settled inside the comparison.
- Taking a threshold above the tabulated span as an error. Above the
  cut-off the environment supplies nothing, and that is the exclusion
  the analysis is looking for.

## Behavior contract (gate 3)

The spectrum validation including its cut-off check, log-log flux
interpolation, threshold exclusion at equality, event-rate arithmetic
with device count and reduction factor, the destructive and
recoverable grouping, mitigation-kind matching, latchup limiter trip
and timing checks, voltage derating at equality and the aggregation
are exercised by the gate 3 contract test:
scripts/test_q6015_single_event_effects_assurance.py against
scripts/q6015_single_event_effects_assurance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6015_single_event_effects_assurance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

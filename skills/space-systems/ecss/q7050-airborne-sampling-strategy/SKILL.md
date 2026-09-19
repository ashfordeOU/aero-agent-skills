---
name: q7050-airborne-sampling-strategy
description: "Design the airborne sampling strategy a cleanroom zone needs under ECSS-Q-ST-70-50C: size the sampling locations from the floor area or a supplied area table, derive the smallest single-sample volume that still collects a statistically useful particle count at the class limit, convert it into a duration at the counter flow rate, and total the air drawn and the occupancy time. Use when planning a monitoring run, defending a sample duration, or checking whether a high-flow counter has shortened a sample below usefulness. Trigger: ecss, q-st-70-50c, airborne-sampling-strategy, sampling-location-sizing, minimum-sample-volume, particle-counter-flow-rate, sampling-duration-derivation."
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
  tags: [ecss, q-st-70-50c-particle-contamination-monitoring, q-st-70-50c, q7050-airborne-sampling-strategy, airborne-sampling-strategy, sampling-location-sizing, minimum-sample-volume, particle-counter-flow-rate, sampling-duration-derivation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle Monitoring — Airborne Sampling Strategy (space-systems/ecss/q7050-airborne-sampling-strategy)

Use when the task is the sampling-strategy part of the airborne clause of
ECSS-Q-ST-70-50C: where in a zone the counter is placed, how much air each
location draws, at what flow rate, and therefore for how long.

## Domain quick reference

- Three quantities are locked to each other. Volume is what the statistics
  need, flow rate is what the instrument gives, and duration is the quotient;
  fixing any two fixes the third, so a strategy that states all three
  independently has an inconsistency waiting in it.
- Sample volume comes from the limit, not from habit. The cleaner the class,
  the fewer particles a litre holds, so a tight class needs far more air
  before the count is large enough for the reading to mean anything.
- That relation is inverse, and it surprises people. A loose class reaches
  the statistical target almost at once, which is why a floor volume exists:
  below it the sample is measuring the instrument's own behaviour.
- A duration floor exists for the same reason from the other side. A
  high-flow counter can draw the required volume in seconds, and a few
  seconds of air is a moment, not a condition, so the sample is held open.
- Location count scales with the square root of floor area. Some facilities
  carry their own area-to-location table instead; either way the operator can
  add locations and cannot remove the ones the area derived.
- A flow rate has a calibrated band. A counter run outside the band it was
  calibrated at reports a volume it did not draw, and every concentration
  computed from that volume inherits the error.
- The strategy costs occupancy. Air per location times locations gives the
  zone's total draw, and duration times locations gives the time the room is
  tied up, which is the number the schedule actually cares about.

## Workflow

1. Validate the floor area, the class limit at the considered size and the
   counter flow rate.
2. Size the locations: square-root rule by default, or the caller's
   area-to-location table where one exists, then apply the minimum and any
   operator increase.
3. Derive the smallest useful single-sample volume from the target particle
   count and the class limit, applying the floor volume where the class is
   loose enough to reach the target immediately.
4. Convert that volume into a duration at the flow rate, applying the
   duration floor where the counter reaches the volume too quickly.
5. Total the run: air drawn per location, air drawn for the zone, and the
   occupancy time the zone owes.
6. Report the findings: a flow rate outside the calibrated band, either floor
   having bound the sample, and an operator request that tried to cut the
   location count below the derived value.

## Pitfalls

- Fixing volume, flow and duration independently. They are one relation with
  two free parameters, and stating all three is how a strategy ends up asking
  for a sample its own numbers say is impossible.
- Reusing a sample volume across classes. A tighter class needs more air, not
  less, so carrying a volume over from a looser room understates the count
  and widens the uncertainty exactly where it matters most.
- Letting a high-flow counter set a few-second sample. The volume target is
  met, and the sample still describes one instant of a room whose condition
  moves with the work going on in it.
- Cutting locations to save time. The derived count is what lets a zone be
  described at all; dropping below it produces a number for a position rather
  than a statement about the room.
- Running a counter outside its calibrated flow band. The reported volume is
  then wrong, and every concentration derived from it is wrong by the same
  proportion with nothing in the data to show it.
- Planning a run without totalling occupancy. Duration times locations is the
  time the zone is unavailable, and a strategy that never computed it is the
  one that gets truncated on the day.

## Behavior contract (gate 3)

The area, limit and flow-rate validation, the square-root and table location
sizing, the statistically derived minimum sample volume with its floor, the
duration derivation with its floor, the zone totals and the strategy findings
are exercised by the gate 3 contract test:
scripts/test_q7050_airborne_sampling_strategy.py against
scripts/q7050_airborne_sampling_strategy_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7050_airborne_sampling_strategy.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

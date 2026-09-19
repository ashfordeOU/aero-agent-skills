---
name: q7050-cleanroom-classification
description: "Coordinate the airborne particle qualification of a cleanroom that hosts contamination-monitored flight hardware, sizing the ISO 14644-1 sample plan and the ISO 14644-2 re-qualification interval before the room is accepted. Use when a room of known floor area must be qualified to a target class at one or more reference particle sizes, and the sample location count, single-sample volume, sampling time and interval all have to be fixed and then graded against what the counter actually delivered. Derives the limit concentration per reference size, the minimum locations for the area, the volume needed to collect enough particles at the limit, and the per-location verdict. Trigger: ecss, q-st-70-50, iso-14644-1, iso-14644-2, cleanroom-airborne-particle-qualification, sample-location-count, single-sample-volume, room-requalification-interval, limit-particle-concentration."
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
  tags: [ecss, q-st-70-50-particle-contamination-monitoring-scope, q7050-cleanroom-classification, cleanroom-airborne-particle-qualification, sample-location-count, single-sample-volume, limit-particle-concentration, room-requalification-interval]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle Contamination Monitoring — Cleanroom Qualification Coordination (space-systems/ecss/q7050-cleanroom-classification)

Use when the task is the interface toward the facility side of particle
contamination monitoring: deciding what the airborne particle
qualification of the room has to consist of, and whether the campaign
that was run actually qualifies it for the hardware inside.

## Domain quick reference

- A room class is a statement about airborne concentration at a
  reference particle size. The allowed concentration falls steeply with
  size, so a room that holds its class at half a micrometre may be well
  outside it at five, and each reference size the programme cares about
  is a separate limit to be met.
- The number of sample locations is driven by the floor area, not by
  convenience or by how many probe positions the contractor owns. Too
  few locations do not produce an optimistic room, they produce a room
  whose class was never measured, because the spatial variation the
  location count exists to capture went unsampled.
- The single-sample volume is set by the limit itself. A sample must be
  large enough that a room sitting exactly at its limit would deliver a
  statistically meaningful number of particles; a small sample at a
  tight class counts a handful of particles and the verdict is
  dominated by counting noise. A volume floor and a minimum sampling
  time apply on top.
- Sampling time follows from volume and the counter flow rate. A flow
  rate quoted for a different probe, or a run cut short, delivers less
  volume than the plan and silently invalidates the location.
- Qualification is not a one-off. The interval before the room must be
  qualified again is shorter for the tighter classes, and a monitoring
  regime that lets the interval lapse leaves the hardware in a room
  with no current evidence.

## Workflow

1. Validate the room: floor area, target class, the reference particle
   sizes and the counter flow rate. A non-positive area, a negative
   class or a non-positive size is an input error, not a value to clamp.
2. Derive the limit concentration for each reference size from the
   target class, using the programme size exponent.
3. Determine the minimum number of sample locations for the floor area
   from the programme location table when one is supplied, and from the
   area square-root rule when it is not.
4. Size the single sample: the volume that would collect the required
   particle count at the tightest limit, raised to the volume floor,
   and the sampling time that volume needs at the counter flow rate,
   raised to the minimum time.
5. Grade every reported location: convert its counts and sampled volume
   into a concentration per reference size and compare with the limit,
   absorbing an equality at the limit with the named tolerance.
6. Check campaign coverage: locations reported against locations
   required, and each location's sampled volume against the required
   single-sample volume.
7. Check the re-qualification interval for the target class against the
   interval the facility operates on, and report the sample plan, the
   per-location verdicts and every finding.

## Pitfalls

- Sizing the sample plan on the room the operator expects rather than
  the class being claimed. The volume comes from the limit, so a
  tighter class needs a larger sample, and reusing a plan written for a
  looser room under-samples exactly where precision matters.
- Averaging the locations into one room concentration and comparing
  that with the limit. The location count exists because the room is
  not uniform; a single hot location is the finding, and an average
  buries it.
- Sampling fewer locations than the area requires and calling the
  campaign a pass. An unsampled region is not a compliant region, and
  the shortfall is a coverage finding in its own right.
- Treating a sample volume shortfall as a rounding matter. A location
  sampled below the required volume has a verdict built on too few
  particles, and the honest response is to re-run that location.
- Letting the re-qualification interval lapse because the last campaign
  passed comfortably. The interval is a property of the class, not of
  how good the last result looked.

## Behavior contract (gate 3)

The limit-concentration derivation, location-count rule, single-sample
volume and time sizing, per-location grading, coverage checks and
interval check are exercised by the gate 3 contract test:
scripts/test_q7050_cleanroom_classification.py against
scripts/q7050_cleanroom_classification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7050_cleanroom_classification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q7029-exposure-conditions
description: "Define the exposure conditions of an ECSS-Q-ST-70-29 offgassing run: fix the set-point temperature and its tolerance band, count the dwell from thermal stabilisation rather than from the moment the vessel was closed, and pin the environment as evacuated below a pressure ceiling or purged with dry nitrogen at an adequate flow and purity, then grade a recorded profile on effective in-band dwell, excursion count and peak deviation. Use when a conditioning run has to be specified before it starts or accepted after it, and a profile that dipped out of band mid-dwell must be judged rather than averaged away. Trigger: ecss, q-st-70-29, offgassing-exposure-conditions, offgassing-dwell-duration, offgassing-thermal-stabilisation, offgassing-vacuum-pressure-ceiling, offgassing-nitrogen-purge, offgassing-temperature-excursion, crew-compartment-offgassing."
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
  tags: [ecss, q-st-70-materials-scope, q7029-exposure-conditions, offgassing-exposure-conditions, offgassing-dwell-duration, offgassing-thermal-stabilisation, offgassing-vacuum-pressure-ceiling, offgassing-nitrogen-purge, offgassing-temperature-excursion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Exposure Conditions (space-systems/ecss/q7029-exposure-conditions)

Use when the task is the exposure step of ECSS-Q-ST-70-29: deciding, or
afterwards accepting, the temperature a specimen is held at, how long it is
held there, and the environment it is held in — so that the products the
collection and analysis steps see were driven off under conditions the report
can name.

## Domain quick reference

- Three quantities define the exposure and none of them substitutes for
  another: the set-point temperature, the dwell at that temperature, and the
  environment. A run held long enough at the wrong temperature is not a longer
  run, it is a different run.
- The dwell is counted from thermal stabilisation, not from the moment the
  vessel was closed. The ramp is heat-up of the vessel and the specimen, and
  crediting it inflates the exposure by exactly the time the specimen spent
  too cold to release the products of interest.
- The environment is either an evacuated vessel below a stated pressure
  ceiling, or a dry-nitrogen purge at a stated flow and purity. They are not
  interchangeable: a purge sweeps products to the trap continuously, a vacuum
  relies on the pressure difference, and the collection step is sized for one
  of them.
- A tolerance band is a band, not an average. A profile whose mean sits on the
  set point can still have spent hours below the band; the quantity that
  matters is time inside the band, and out-of-band intervals are subtracted
  rather than averaged out.
- Excursions are counted as well as summed. Many small dips and one long
  outage integrate to the same lost time but mean different things about the
  facility, so the record carries the count, the longest single excursion and
  the peak deviation alongside the total.
- An over-temperature excursion is not a conservative error. Above the
  set point a specimen can release products it would never release in service,
  or degrade in a way that changes what it releases afterwards, so a hot
  excursion is a finding in its own direction.

## Workflow

1. Validate the set point: a physically real temperature, a strictly positive
   tolerance, and a strictly positive required dwell.
2. Validate the environment. For an evacuated run, a positive pressure that is
   compared with the ceiling; for a purged run, a positive flow and a purity
   fraction inside its open interval. A missing field is an input error, an
   out-of-limit value is a finding.
3. Validate the recorded profile: at least two samples, strictly increasing
   time, real temperatures.
4. Find thermal stabilisation — the first sample inside the tolerance band.
   A profile that never enters the band has no dwell to credit.
5. Walk the intervals after stabilisation. An interval counts towards the
   effective dwell only when both of its endpoints are inside the band, so a
   dip is charged in full rather than smoothed by interpolation.
6. Group the out-of-band intervals into excursions, recording for each its
   duration, its direction and its peak deviation from the set point.
7. Compare the effective dwell with the required dwell, absorbing
   representation error at the boundary with a named tolerance rather than by
   shortening the requirement.
8. Report the verdict with every finding: short dwell, pressure above the
   ceiling, purge below flow or purity, hot excursion, and the stabilisation
   time itself when it consumed an unreasonable share of the run.

## Pitfalls

- Crediting the ramp. Counting the dwell from vessel close rather than from
  stabilisation is the single most common way an under-exposed run is signed
  off as complete.
- Averaging the profile against the set point. The mean can sit exactly on the
  set point while the specimen spent a third of the run below the band.
- Treating a nitrogen purge and a vacuum as the same exposure because the
  temperature and duration match. The transport mechanism differs, and so does
  the collection efficiency the analysis step assumes.
- Reporting only total out-of-band time. One four-hour outage and forty
  six-minute dips are not the same event; the count and the longest excursion
  belong in the record.
- Ignoring a hot excursion because the run was "at least hot enough". Over
  temperature changes what the specimen releases and can invalidate the run in
  the other direction.
- Relaxing the tolerance band after the fact so a marginal run passes. The
  band is part of the specification; an exact-equality case at the dwell
  boundary is a representation question handled inside the comparison.

## Behavior contract (gate 3)

The set-point validation, environment validation, stabilisation search,
in-band dwell accumulation, excursion grouping and the acceptance verdict are
exercised by the gate 3 contract test:
scripts/test_q7029_exposure_conditions.py against
scripts/q7029_exposure_conditions_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7029_exposure_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

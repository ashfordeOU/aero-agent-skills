---
name: q7031-environmental-conditions
description: "Assess the application environment before a coat is sprayed under ECSS-Q-ST-70-31C: grade booth air temperature and relative humidity against the paint system's declared window, derive the dew point from the Magnus relation and form the substrate dew-point margin, then convert an ISO 14644-1 cleanliness class into per-size airborne count limits and grade the measured counts. Holds a run whose air sits in window but whose hardware is cold enough to condense. Use when a spray-booth log, a substrate temperature reading or a particle count has to release or hold a paint application. Trigger: ecss, q-st-70-31c-paint-application, paint-application-environment-window, coating-substrate-dew-point-margin, paint-booth-airborne-cleanliness-class, spray-booth-humidity-limit, paint-application-release-hold."
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
  tags: [ecss, q-st-70-31c-paint-application-scope, q7031-environmental-conditions, paint-application-environment-window, coating-substrate-dew-point-margin, paint-booth-airborne-cleanliness-class, spray-booth-humidity-limit, paint-application-release-hold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paint Application -- Environmental Conditions (space-systems/ecss/q7031-environmental-conditions)

Use when the task is the application-environment control of ECSS-Q-ST-70-31C:
a coat is about to be applied to flight hardware and the question is whether
the booth air, the hardware itself and the airborne cleanliness of the area
are all inside the window the paint system's process document declares.

## Domain quick reference

- Three quantities govern the decision and they are not interchangeable: the
  booth air temperature, the temperature of the hardware being coated, and
  the relative humidity of the booth air. A log that records only air
  temperature cannot answer the question.
- The controlling humidity criterion is not the relative-humidity number but
  the dew-point margin at the substrate. Dew point follows from air
  temperature and relative humidity through the Magnus relation; the margin
  is the substrate temperature minus that dew point. Hardware that has come
  off a cold bench or out of a thermal chamber can carry a condensed film
  while the booth reads comfortably in window.
- Airborne cleanliness is expressed as an ISO 14644-1 class, which is a
  concentration law rather than a single number: the limit at a given
  particle size scales as the class decade times the size ratio raised to a
  fixed exponent. A class that passes at half a micron can fail at five
  microns, so the grading is done size by size against the measured counts.
- Solvent release depends on temperature, so an out-of-window run does not
  simply cure differently. Too cold and the film keeps solvent and stays
  soft; too warm and the surface skins over a wet layer, which is what
  produces the pinholes another leaf then has to disposition.
- The environment is a release decision, taken before the gun is triggered.
  Once the coat is on, an out-of-window record becomes a nonconformance that
  can only be dispositioned, and the cheapest disposition is usually a strip.

## Workflow

1. Validate the three readings and the two declared bands. A humidity outside
   nought to a hundred percent, or a temperature outside any plausible
   application range, is an instrument or transcription error, not a
   degenerate case to be clamped.
2. Grade booth air temperature against the declared temperature band and
   relative humidity against the declared humidity band, treating a reading
   exactly on a limit as inside it and absorbing representation error with a
   named tolerance rather than by widening the band.
3. Derive the dew point of the booth air and form the substrate dew-point
   margin. Compare it with the minimum margin the process document requires.
4. When an airborne-cleanliness class is declared, convert it into a
   concentration limit at each measured particle size and grade each size
   separately, keeping every breach as its own finding.
5. Return a single release-or-hold verdict together with the full list of
   findings, so the reason a run is held is visible without re-deriving it.

## Pitfalls

- Grading the booth and calling the part covered. Air temperature and
  substrate temperature are different measurements; the dew-point criterion
  belongs to the hardware, and a part colder than the air is the normal case
  after transport, not the exception.
- Reading relative humidity as the criterion. A high relative humidity in a
  warm booth over warm hardware can carry more margin than a modest one in a
  cool booth over cold hardware, because the margin is a temperature
  difference and not a percentage.
- Treating the ISO class as a pass token. The class is a per-size limit
  curve; checking only the smallest measured size hides a coarse-particle
  breach, which is the population that actually lands in a wet film.
- Widening the declared window to release a run that missed it. The window
  belongs to the paint system, not to the schedule; an out-of-window run is
  held, or applied and dispositioned as a nonconformance.
- Relaxing a limit to absorb a reading that landed exactly on it. Equality at
  a limit is a representation question, handled by the tolerance inside the
  comparison, and the declared value stays as specified.

## Behavior contract (gate 3)

The reading and band validation, the band grading, the Magnus dew-point
derivation, the substrate margin comparison, the ISO 14644-1 per-size limit
conversion and the combined release verdict are exercised by the gate 3
contract test:
scripts/test_q7031_environmental_conditions.py against
scripts/q7031_environmental_conditions_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7031_environmental_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q7050-airborne-particle-counting
description: "Evaluate airborne particle counting results against a cleanroom class under ECSS-Q-ST-70-50C, which carries the air grading over to the ISO 14644-1 concentration limits: derive the permitted concentration for the class and considered size, convert counted particles and sampled volume into the same unit, confirm the counter resolves the channel, then grade every location and report the worst. Use when reviewing a cleanroom monitoring run, dispositioning a location over its limit, or checking a counter report before it enters a contamination file. Trigger: ecss, q-st-70-50c, iso-14644-1-class-limit, airborne-particle-concentration, cleanroom-class-verification, particle-counter-channel-resolution, airborne-counting-location-grading."
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
  tags: [ecss, q-st-70-50c-particle-contamination-monitoring, q-st-70-50c, q7050-airborne-particle-counting, iso-14644-1-class-limit, airborne-particle-concentration, cleanroom-class-verification, particle-counter-channel-resolution, airborne-counting-location-grading]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle Monitoring — Airborne Particle Counting (space-systems/ecss/q7050-airborne-particle-counting)

Use when the task is the airborne clause of ECSS-Q-ST-70-50C: counting
particles in cleanroom air and grading the result against the class the zone
is declared to, which is stated through the ISO 14644-1 concentration limits.

## Domain quick reference

- The limit is a concentration, not a count. A counter reports particles seen
  in the volume it drew, so the reading only becomes comparable to a limit
  after the sampled volume divides it, and mixing a litre-based count with a
  cubic-metre-based limit is a factor of a thousand.
- The class limit is a curve, not a single number. It falls steeply with the
  considered size, so the same air passes at one micrometre and can fail at
  half a micrometre; naming the size is part of naming the limit.
- The class designation is a decade exponent. Moving one class number scales
  every limit on the curve by ten, which is why a zone downgraded by a single
  class is a far larger change than the number suggests.
- The relation is stated over a bounded size span. Outside it the particle
  size distribution has a different shape, so extrapolating the curve to a
  smaller or larger size invents a limit rather than reading one.
- Limits are reported to three significant figures, and that rounding belongs
  in decimal. Scaling by a power of ten to round is not correctly rounded and
  can move the last digit differently on different machines, which turns a
  boundary case into a platform-dependent verdict.
- A counter cannot report a channel below its smallest resolvable size. A
  report carrying a channel the instrument does not reach is an instrument
  finding, not a clean result, and it is invisible in the numbers themselves.
- Locations are graded individually, and the run is the worst of them. An
  average across locations hides the one position that failed, which is the
  position the air handler needs attention at.

## Workflow

1. Validate the class designation and the considered particle size, refusing
   a size outside the span the relation is stated over.
2. Derive the permitted concentration from the class exponent and the size
   ratio, rounded to three significant figures in decimal.
3. Convert each location's counted particles and sampled volume into a
   concentration per cubic metre, or take a concentration the counter already
   reports, but never mix the two units in one comparison.
4. Check the counter's smallest resolvable size against the considered size
   and raise an instrument finding when the channel is out of reach.
5. Grade each location, absorbing an exact equality at the limit with a
   relative tolerance rather than by relaxing the limit.
6. Report every location, the worst by utilisation, the failed locations and
   the findings, including a location sampled twice in one run.

## Pitfalls

- Comparing a raw count to a concentration limit. The sampled volume has to
  divide the count first, and the litre-to-cubic-metre step is where the
  factor of a thousand goes missing.
- Quoting a class without a size. The limit curve is steep, so a statement
  that a zone met its class carries no information until the considered size
  it was verified at is attached.
- Extrapolating the size relation past its stated span. The distribution
  shape changes at both ends, so a limit for a size outside the span has to
  be refused rather than computed.
- Rounding the limit by scaling with a power of ten. That path is not
  correctly rounded and moves the last significant digit on some machines, so
  a reading sitting on the boundary passes in one place and fails in another.
- Averaging the locations. The run is graded on its worst position, because
  an average lets a clean corner of the room carry a failing one.
- Accepting a channel the counter cannot resolve. The numbers look ordinary,
  and only the instrument's smallest resolvable size reveals that the channel
  was never measured at all.

## Behavior contract (gate 3)

The class and size validation, the decimal three-significant-figure limit
derivation, the count-to-concentration conversion, the channel-resolution
check, the at-limit tolerance and the per-location grading are exercised by
the gate 3 contract test:
scripts/test_q7050_airborne_particle_counting.py against
scripts/q7050_airborne_particle_counting_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7050_airborne_particle_counting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

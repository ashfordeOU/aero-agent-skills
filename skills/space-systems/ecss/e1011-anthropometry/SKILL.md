---
name: e1011-anthropometry
description: "Use when apply anthropometric and biomechanical reference data to spacecraft or habitat design under ECSS-E-ST-10-11C §4.5.1: determine the percentile range the design must accommodate (typically 5th–95th), interpolate body dimensions at the required percentile, check that every clearance and reach envelope covers the full target population, verify that required operator forces stay within the 5th-percentile strength limit, and apply microgravity spinal-unloading corrections to stature and seated-height before comparing with design envelopes. Trigger: ecss, e-st-10-system-scope, anthropometry, biomechanics, percentile, reach-envelope, strength-limit, microgravity-correction, human-factors, crew-provisions."
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
  tags: [ecss, e-st-10-system-scope, anthropometry, biomechanics, percentile, reach-envelope, strength-limit, microgravity-correction, human-factors, crew-provisions]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Anthropometry and Biomechanics (space-systems/ecss/e1011-anthropometry)

Use when the task is applying anthropometric and biomechanical reference
data to a crewed spacecraft or habitat design per ECSS-E-ST-10-11C §4.5.1
— verifying percentile accommodation, reach envelopes, strength limits,
and microgravity body-dimension corrections.

## Domain quick reference

- §4.5.1 requires the design team to select a target accommodation range
  (typically 5th–95th percentile of the operational crew population) and
  to verify that every physical interface (clearance, reach, force) covers
  that full range.
- Anthropometric dimensions (stature, arm length, shoulder width, seated
  height, etc.) are expressed as population percentile distributions.
  A design accommodates a percentile if the physical envelope includes
  that body dimension value. Linear interpolation between the 5th and 95th
  percentile reference values gives a working estimate for intermediate
  percentiles.
- Reach envelopes differ by direction (forward, side, overhead) and
  posture (suited, unsuited). The 5th-percentile functional reach is the
  limiting value for access-to-controls requirements: if the shortest-armed
  expected crew member cannot reach a control, the design fails.
- Strength limits follow the same worst-case rule: required operator forces
  (push, pull, torque) must not exceed the 5th-percentile capability of the
  population. Exceeding this threshold excludes the weakest crew members
  from operating the system unaided.
- Microgravity spinal unloading increases stature and seated height by
  approximately 3% relative to ground measurements. Ground-measured reference
  data for these dimensions must be corrected upward before comparing with
  overhead and seated-envelope design values.

## Workflow

1. Define the target population and percentile range (e.g., 5th–95th
   percentile of the ISS crew database). Record the reference 5th and 95th
   percentile values for each relevant body dimension from the authorised
   source (ECSS-E-ST-10-11C Annex or project-specific database).
2. For each physical clearance or envelope, check whether the design
   minimum accommodates the largest relevant body dimension (95th percentile)
   and the design maximum accommodates the smallest (5th percentile). Compute
   any shortfall at either end and flag it as a finding.
3. For each reach-critical control location, retrieve the 5th-percentile
   functional reach for the applicable direction (forward, side, overhead).
   Apply the microgravity correction if the dimension is stature- or
   seated-height-driven. Confirm that the 5th-percentile reach equals or
   exceeds the distance to the control; record the shortfall if not.
4. For each human-operated mechanism, identify the maximum required actuating
   force or torque. Confirm that this value does not exceed the 5th-percentile
   strength capability from the reference data. Flag any excess as a strength
   non-compliance.
5. Apply microgravity corrections: multiply stature and seated-height
   dimensions by 1.03 before comparing with overhead-clearance and workstation
   envelope limits. Leave arm length and other extremity dimensions uncorrected
   unless project-specific data shows otherwise.
6. Produce a compliance table: one row per interface, with design value,
   population limit, shortfall (zero if compliant), and pass/fail status.
   An interface is compliant only when every applicable check (clearance,
   reach, strength) shows zero shortfall.

## Pitfalls

- Using 50th-percentile values as the sole design driver — the 50th
  percentile is the median user, but the 5th and 95th are the binding limits.
  A design that fits the average may exclude a significant fraction of the crew.
- Omitting the microgravity stature correction when checking overhead
  clearances — crew members grow taller in orbit, so a ground-based envelope
  that looks acceptable on the ground can exceed its limit on-orbit.
- Treating reach and clearance as the same check — clearance requires the
  design to be large enough for the 95th-percentile body dimension, while
  reach requires the control to be close enough for the 5th-percentile arm.
  Conflating the two leads to design errors in opposite directions.
- Applying 5th-percentile strength as a positive force limit rather than
  checking the required force against it — if the required force exceeds
  the 5th-percentile capability, the smallest crew member cannot operate
  the mechanism, which is a non-compliance regardless of mean population
  capability.

## Behavior contract (gate 3)

The percentile interpolation, dimension accommodation, reach-envelope,
strength-limit, microgravity-correction, and accommodation-percentage logic
is exercised by the gate 3 contract test:
scripts/test_e1011_anthropometry.py against
scripts/e1011_anthropometry_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_anthropometry.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

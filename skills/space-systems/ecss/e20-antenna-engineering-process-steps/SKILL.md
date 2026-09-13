---
name: e20-antenna-engineering-process-steps
description: "Use when structure the antenna engineering steps of ECSS-E-ST-20C clause 7.2.1.2.2, from mission-transmission-reception-analysis through to the antenna design decision: validate that a step is entered only once its predecessors are complete and its entry data is on record, derive the antenna-gain that the required-effective-isotropic-radiated-power leaves after transmitter output and feeder-loss, turn the coverage footprint at the orbit altitude into an edge-of-coverage half-angle, convert that into the half-power-beamwidth and directivity the radiation pattern must hold, select the antenna concept the beamwidth and the beam count imply, and report which step the project may enter next. Trigger: ecss, e-st-20-electrical-scope, e20-antenna-engineering-process-steps, antenna-engineering-sequence, mission-transmission-reception-analysis, coverage-half-angle-derivation, half-power-beamwidth-derivation, antenna-concept-selection."
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
  tags: [ecss, e-st-20-electrical-scope, e20-antenna-engineering-process-steps, antenna-engineering-sequence, mission-transmission-reception-analysis, coverage-half-angle-derivation, half-power-beamwidth-derivation, antenna-concept-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Antenna Engineering Process Steps (space-systems/ecss/e20-antenna-engineering-process-steps)

Use when the task is the antenna engineering sequence of ECSS-E-ST-20C
clause 7.2.1.2.2 -- walking from the mission transmission and reception
analysis, through the requirements and the coverage the mission implies,
to the concept and the design decision, and proving at each step that
what it consumes already exists.

## Domain quick reference

- Clause 7.2.1.2.2 describes antenna engineering as an ordered sequence,
  not a set of parallel activities. The order used here is:
  mission-transmission-reception-analysis, then
  radio-frequency-requirement-derivation, then
  coverage-and-pattern-specification, then antenna-concept-selection,
  then accommodation-and-interface-definition, then the antenna design
  decision. A step is enterable only once every earlier step is complete
  and the data it consumes is on record; a step completed while an
  earlier one is open is a sequence finding, because its inputs were
  assumed rather than derived.
- The requirement step converts a link demand into an antenna demand.
  The antenna-gain a design must reach is what the required radiated
  power leaves once the transmitter output is credited and the feeder
  attenuation is paid: required radiated power minus transmitter output
  plus feeder attenuation. Raising the transmitter output or shortening
  the feeder run both relax the antenna.
- The coverage step converts geometry into a pattern. The footprint
  radius on the surface is a central angle at the body centre; the
  half-angle subtended at the spacecraft follows from that angle and the
  orbit altitude, and a footprint that reaches past the visible horizon
  is a geometry error rather than a wide beam. Twice the half-angle is
  the half-power-beamwidth the pattern must hold, and the directivity a
  symmetric beam of that width can reach falls as the square of the
  width.
- The concept step is a branch on the pattern, not a preference. More
  than one simultaneous beam, or a beam that must be repointed
  electronically, calls for an array whatever the width. Otherwise a
  narrow beam calls for a reflector, an intermediate beam for a horn,
  and a wide beam for a low-gain element. The boundaries between those
  bands are held exactly: a beamwidth that is physically on a boundary
  stays in the narrower band rather than drifting into the next one on
  a rounding error.
- A concept is only feasible if the beam that satisfies the coverage can
  also hold the gain the link demands. The achievable gain is the
  directivity of that beam reduced by the aperture efficiency; when the
  required gain sits above it, the coverage and the link contradict each
  other and one of them must move before the design decision is taken.

## Workflow

1. Normalise the list of completed steps and check the order: record a
   finding for any completed step whose predecessors are still open.
   Reject an unrecognised step name outright.
2. Identify the next step the project may enter, and list the entry data
   that step consumes but the project does not yet hold.
3. Derive the required antenna-gain from the required radiated power,
   the transmitter output and the feeder attenuation.
4. Convert the coverage footprint radius and the orbit altitude into the
   edge-of-coverage half-angle, rejecting a footprint that reaches past
   the horizon.
5. Double the half-angle into the half-power-beamwidth, and compute the
   directivity a symmetric beam of that width reaches.
6. Reduce that directivity by the aperture efficiency and hold the
   required antenna-gain against it; a required gain above the
   achievable gain is a finding against the coverage or the link, not a
   design task.
7. Select the antenna concept from the beamwidth, the beam count and the
   steering need, and report the next step together with every sequence,
   entry-data and feasibility finding. The design decision is enterable
   only when all three lists are empty.

## Pitfalls

- Running the coverage step before the requirement step because the
  geometry is known earlier. The pattern is specified against a gain the
  requirement step has not yet produced, and the beamwidth that comes
  out is unanchored.
- Treating the footprint radius as the half-angle at the spacecraft. The
  two differ by the whole orbit geometry -- at low altitude a modest
  footprint subtends a very wide angle, at geostationary altitude the
  same footprint is a narrow spot.
- Taking directivity as gain. The aperture efficiency sits between them,
  and a design sized on directivity is short by the efficiency loss on
  every link it supports.
- Selecting a reflector for a multi-beam payload because the single-beam
  width suggests one. Beam count and steering need decide the concept
  family before the width narrows it.
- Widening a concept-selection band to make a borderline beamwidth fall
  where the designer expected. The band edges are part of the engineering
  judgement; only the representation error of the arithmetic is absorbed.

## Behavior contract (gate 3)

The step validation, sequence-order check, entry-data check, next-step
selection, required-gain derivation, edge-of-coverage half-angle,
beamwidth and directivity conversion, achievable-gain feasibility,
concept selection and aggregate process review logic is exercised by the
gate 3 contract test:
scripts/test_e20_antenna_engineering_process_steps.py against
scripts/e20_antenna_engineering_process_steps_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_antenna_engineering_process_steps.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
